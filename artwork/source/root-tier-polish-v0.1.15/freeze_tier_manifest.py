"""Freeze root-pixel-states v0.1.15 data into a hash-pinned technical proof.

This only writes the versioned proof and its explicit root approval record.
It does not modify root-authored pixel JSON or render assets.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
INPUT = ROOT / "artwork/source/root-tier-polish-v0.1.15/root-pixel-states.json"
BASE_INPUT = ROOT / "artwork/source/root-tier-v3/root-pixel-states.json"
RENDER_DIR = ROOT / "artwork/validation/root-tier-polish-v0.1.15/reference-final-fx"
RENDER_AUDIT = RENDER_DIR / "render-audit.json"
OUTPUT_DIR = ROOT / "artwork/validation/v0.1.15/root-tier-polish"
BASE_INPUT_SHA256 = "D412F62BD8C4AB5909E1EF36F22AFD1DDA79C920A7059576AA43B4A0EBEC31E9"
BASELINE_JAR_SHA256 = "43D8B35550E6A30B506D51E8718168EEF6C29D5F3288C17EFDF5C9E00CA62B28"
BASELINE_JAR = "jaysay-echo-tools-0.1.14.jar"
MOTHER_SHA256 = "BE0F000D3B70B35E10984951A6B1E6DA66CD204381A22E3C8FB9399C23019B67"
POLISH_AUDIT = INPUT.parent / "polish-audit.json"
POLISHED_STATES = {"resonance1", "resonance2", "all_max"}
MODULE_TIERS = {
    "resonance": ["resonance1", "resonance2"],
    "split": ["split1", "split2", "split3"],
    "tuning": ["tuning1"],
    "extension": ["extension1", "extension2", "extension3"],
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def load_image(path: Path) -> Image.Image:
    image = Image.open(path).convert("RGBA")
    if image.size != (128, 128):
        raise ValueError(f"{path}: expected a 128x128 PNG")
    return image


def alpha_components(image: Image.Image, diagonal: bool) -> list[int]:
    remaining = {(x, y) for y in range(128) for x in range(128)
                 if image.getpixel((x, y))[3] > 0}
    offsets = ((-1,-1),(0,-1),(1,-1),(-1,0),(1,0),(-1,1),(0,1),(1,1)) if diagonal else ((0,-1),(-1,0),(1,0),(0,1))
    sizes = []
    while remaining:
        stack = [remaining.pop()]
        size = 0
        while stack:
            x, y = stack.pop()
            size += 1
            for dx, dy in offsets:
                p = (x + dx, y + dy)
                if p in remaining:
                    remaining.remove(p)
                    stack.append(p)
        sizes.append(size)
    return sorted(sizes, reverse=True)


def assert_polish_scope(source: dict, baseline: dict, polish: dict, mother_path: Path) -> dict:
    expected = set(baseline["states"])
    if set(source.get("states", {})) != expected:
        raise RuntimeError("0.1.15 must retain the complete baseline state set")
    if POLISHED_STATES - expected:
        raise RuntimeError("baseline pixel source lacks one of the three target states")
    for name in sorted(expected - POLISHED_STATES):
        if source["states"][name].get("pixelsRGBA") != baseline["states"][name].get("pixelsRGBA"):
            raise RuntimeError(f"{name}: non-target RGBA differs from frozen 0.1.14 pixels")
        if source["states"][name].get("glowPointEffects") != baseline["states"][name].get("glowPointEffects"):
            raise RuntimeError(f"{name}: non-target glowPointEffects differs from frozen 0.1.14 effects")
    if polish.get("version") != "0.1.15" or polish.get("baselineRootPixelSha256") != BASE_INPUT_SHA256:
        raise RuntimeError("polish audit does not pin the 0.1.14 root baseline")
    if polish.get("rootPixelSha256") != sha(INPUT.read_bytes()):
        raise RuntimeError("polish audit does not pin the final root pixel JSON")
    expected_counts = {"resonance1": 87, "resonance2": 975, "all_max": 975}
    diff_sets = {}
    for name in sorted(POLISHED_STATES):
        old_rows = baseline["states"][name]["pixelsRGBA"]
        new_rows = source["states"][name]["pixelsRGBA"]
        if len(old_rows) != 128 or len(new_rows) != 128:
            raise RuntimeError(f"{name}: expected 128x128 state")
        actual = {(x, y) for y in range(128) for x in range(128)
                  if old_rows[y][x] != new_rows[y][x]}
        record = polish.get("states", {}).get(name)
        if not isinstance(record, dict):
            raise RuntimeError(f"polish audit lacks state record {name}")
        listed_raw = record.get("coordinates", [])
        listed = {tuple(point) for point in listed_raw}
        if len(listed) != len(listed_raw) or listed != actual:
            raise RuntimeError(f"{name}: polish-audit coordinates do not exactly match RGBA diff")
        if len(actual) != expected_counts[name] or record.get("changedPixels") != expected_counts[name]:
            raise RuntimeError(f"{name}: expected exactly {expected_counts[name]} changed texels")
        diff_sets[name] = actual
    tip_arc_raw = polish.get("tipPatchCoordinates", []) + polish.get("upperArcPatchCoordinates", [])
    tip_arc = [tuple(p) for p in tip_arc_raw]
    if len(set(tip_arc)) != len(tip_arc) or set(tip_arc) != diff_sets["resonance1"]:
        raise RuntimeError("resonance1 diff is not exactly the root-recorded tip plus upper arc")
    if diff_sets["all_max"] != diff_sets["resonance2"]:
        raise RuntimeError("all_max diff coordinates must exactly equal resonance2 diff coordinates")
    all_rows = source["states"]["all_max"]["pixelsRGBA"]
    base_all_rows = baseline["states"]["all_max"]["pixelsRGBA"]
    red2_rows = source["states"]["resonance2"]["pixelsRGBA"]
    for y in range(128):
        for x in range(128):
            expected = red2_rows[y][x] if (x, y) in diff_sets["resonance2"] else base_all_rows[y][x]
            if all_rows[y][x] != expected:
                raise RuntimeError(f"all_max contains a change outside the resonance2 patch at {(x, y)}")
    if polish.get("rubyIIReferenceTranslation") != [0, 0] or polish.get("rubyIIReferenceRgbaExact") is not True:
        raise RuntimeError("root reference proof must be exact at the original coordinates")
    mother = Image.open(mother_path).convert("RGBA")
    rows = source["states"]["resonance2"]["pixelsRGBA"]
    for field in ("referenceRubyCoordinates", "referenceJointCoordinates"):
        points = polish.get(field)
        if not isinstance(points, list) or not points:
            raise RuntimeError(f"polish audit lacks {field}")
        for point in points:
            x, y = point
            if not (0 <= x < 128 and 0 <= y < 128) or tuple(rows[y][x]) != mother.getpixel((x, y)):
                raise RuntimeError(f"resonance2 {field} mismatch at {(x, y)}")
    return {"expectedChangedTexels": expected_counts, "tipAndUpperArcTexels": len(tip_arc),
            "resonance2ReferenceRubyPoints": len(polish["referenceRubyCoordinates"]),
            "resonance2ReferenceJointPoints": len(polish["referenceJointCoordinates"]),
            "allMaxEqualsResonance2DiffSet": True, "targetAlphaExact": False}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-input-sha256", required=True,
                        help="exact root-provided SHA gate; no approval is generated by this tool")
    args = parser.parse_args()
    expected_input = args.expected_input_sha256.upper()
    if len(expected_input) != 64 or any(c not in "0123456789ABCDEF" for c in expected_input):
        raise RuntimeError("expected input SHA-256 must be 64 hexadecimal characters")
    raw = INPUT.read_bytes()
    if sha(raw) != expected_input:
        raise RuntimeError("root-pixel-states SHA differs from the explicit root-provided SHA gate")
    source = json.loads(raw.decode("utf-8-sig"))
    baseline_raw = BASE_INPUT.read_bytes()
    if sha(baseline_raw) != BASE_INPUT_SHA256:
        raise RuntimeError("frozen 0.1.14 root pixel baseline hash mismatch")
    baseline = json.loads(baseline_raw.decode("utf-8-sig"))
    polish_raw = POLISH_AUDIT.read_bytes()
    polish = json.loads(polish_raw.decode("utf-8-sig"))
    mother = source["motherReference"]
    mother_path = (ROOT / mother["path"]).resolve()
    if sha(mother_path.read_bytes()) != MOTHER_SHA256:
        raise RuntimeError("pinned approved fullmax mother reference hash mismatch")
    polish_scope_audit = assert_polish_scope(source, baseline, polish, mother_path)
    render_bytes = RENDER_AUDIT.read_bytes()
    render = json.loads(render_bytes.decode("utf-8-sig"))
    if render.get("inputSha256") != expected_input:
        raise RuntimeError("reference-final-fx audit does not pin the explicitly authorized root pixel JSON")
    if not render.get("ordinaryAgainstSource64", {}).get("pixelExact"):
        raise RuntimeError("reference-final-fx ordinary image is not exact against ordinary 2x nearest")
    if set(source.get("states", {})) != {
        "ordinary128", "resonance1", "resonance2", "split1", "split2", "split3",
        "tuning1", "extension1", "extension2", "extension3", "all_max",
    }:
        raise RuntimeError("root pixel source has an unexpected state set")
    bounds = source.get("componentBounds128")
    if not isinstance(bounds, dict) or set(bounds) != set(MODULE_TIERS):
        raise RuntimeError("root componentBounds128 must cover the four modules")

    base_path = RENDER_DIR / "ordinary128.png"
    base_data = base_path.read_bytes()
    base = load_image(base_path)
    if sha(base_data) != render["states"]["ordinary128"]["pngSha256"]:
        raise RuntimeError("ordinary128 preview hash differs from reference-final-fx audit")
    images = {"ordinary128": base}
    states = {}
    tier_masks = {}
    module_masks = {}
    glow_masks = {}
    stable_masks = {}
    phase_maps = {}
    amplitude_maps = {}
    glow_records = {}
    fx_audit = {}
    alpha_audit = {}

    for module, tiers in MODULE_TIERS.items():
        x0, y0, x1, y1 = bounds[module]
        if not all(type(n) is int for n in bounds[module]) or not (0 <= x0 <= x1 < 128 and 0 <= y0 <= y1 < 128):
            raise RuntimeError(f"{module}: invalid XYXY component bounds {bounds[module]}")
        union = set()
        for tier in tiers:
            source_state = source["states"][tier]
            if source_state.get("module") != module:
                raise RuntimeError(f"{tier}: source module label mismatch")
            image_path = RENDER_DIR / f"{tier}.png"
            data = image_path.read_bytes()
            image = load_image(image_path)
            if sha(data) != render["states"][tier]["pngSha256"]:
                raise RuntimeError(f"{tier}: PNG hash differs from reference-final-fx audit")
            expected = bytes(value for row in source_state["pixelsRGBA"] for rgba in row for value in rgba)
            if image.tobytes() != expected:
                raise RuntimeError(f"{tier}: rendered pixels differ from root JSON")
            base_px, img_px = base.load(), image.load()
            diffs = {(x, y) for y in range(128) for x in range(128) if base_px[x, y] != img_px[x, y]}
            outside = sorted((x, y) for x, y in diffs if not (x0 <= x <= x1 and y0 <= y <= y1))
            if outside:
                raise RuntimeError(f"{tier}: diff escapes root bounds, first coordinates: {outside[:32]}")
            alpha_values = sorted({img_px[x, y][3] for y in range(128) for x in range(128)})
            if not set(alpha_values) <= {0, 255}:
                raise RuntimeError(f"{tier}: alpha is not binary: {alpha_values}")
            coords = [[x, y] for x, y in sorted(diffs, key=lambda p: (p[1], p[0]))]
            tier_masks[tier] = {module: {"coordinates": coords, "count": len(coords)}}
            union.update(diffs)
            images[tier] = image
            states[tier] = {
                "path": f"artwork/validation/root-tier-polish-v0.1.15/reference-final-fx/{tier}.png",
                "sha256": sha(data), "module": module, "changedTexels": len(diffs),
                "activeModuleMaskTexels": len(diffs), "inactiveBasePixelExact": True,
                "alphaValues": alpha_values,
                "opaqueTexels": sum(1 for y in range(128) for x in range(128) if img_px[x, y][3] == 255),
            }
            alpha_audit[tier] = render["states"][tier]

            dynamic, stable, phases, amplitudes, seen = [], [], {}, {}, set()
            effects = source_state["glowPointEffects"]
            for i, record in enumerate(effects):
                x, y = record["x"], record["y"]
                point = (x, y)
                if type(x) is not int or type(y) is not int or not (0 <= x < 128 and 0 <= y < 128):
                    raise RuntimeError(f"{tier} glowPointEffects[{i}]: invalid coordinate {point}")
                if point in seen:
                    raise RuntimeError(f"{tier} glowPointEffects[{i}]: duplicate coordinate {point}")
                seen.add(point)
                phase, amplitude, is_stable = float(record["phaseRadians"]), float(record["amplitude"]), record["stable"]
                if not isinstance(is_stable, bool) or not math.isfinite(phase) or not math.isfinite(amplitude) or not 0 <= amplitude <= 0.06:
                    raise RuntimeError(f"{tier} glowPointEffects[{i}]: invalid phase/amplitude/stable")
                if not isinstance(record.get("group"), str) or not record["group"]:
                    raise RuntimeError(f"{tier} glowPointEffects[{i}]: missing group")
                if img_px[x, y][3] != 255 or point not in diffs:
                    raise RuntimeError(f"{tier} glowPointEffects[{i}]: point must be an opaque texel in its exact tier diff: {point}")
                if is_stable:
                    if phase != 0 or amplitude != 0:
                        raise RuntimeError(f"{tier} stable point {point} has nonzero effect")
                    stable.append([x, y])
                else:
                    dynamic.append([x, y])
                    phases[f"{x},{y}"] = phase
                    amplitudes[f"{x},{y}"] = amplitude
            glow_masks[tier] = {module: dynamic}
            stable_masks[tier] = {module: stable}
            phase_maps[tier] = {module: phases}
            amplitude_maps[tier] = {module: amplitudes}
            glow_records[tier] = {module: copy.deepcopy(effects)}
            fx_audit[tier] = {
                "pointCount": len(effects), "dynamicCount": len(dynamic),
                "stableCount": len(stable),
                "maximumAmplitude": max((float(point["amplitude"]) for point in effects), default=0.0),
            }
        module_masks[module] = {
            "coordinates": [[x, y] for x, y in sorted(union, key=lambda p: (p[1], p[0]))],
            "count": len(union),
        }

    all_max_path = RENDER_DIR / "all_max.png"
    all_max_data = all_max_path.read_bytes()
    all_max = load_image(all_max_path)
    if sha(all_max_data) != render["states"]["all_max"]["pngSha256"]:
        raise RuntimeError("all_max hash differs from reference-final-fx audit")
    states["all_max"] = {
        "path": "artwork/validation/root-tier-polish-v0.1.15/reference-final-fx/all_max.png",
        "sha256": sha(all_max_data), "module": "all", "changedTexels": 0,
        "activeModuleMaskTexels": 0, "inactiveBasePixelExact": None,
        "alphaValues": render["states"]["all_max"]["alphaValues"],
        "opaqueTexels": render["states"]["all_max"]["opaqueTexels"],
    }
    all_diff = {(x, y) for y in range(128) for x in range(128) if base.getpixel((x, y)) != all_max.getpixel((x, y))}
    module_union = set()
    top_tier_union = set()
    for module in MODULE_TIERS:
        mask = set(map(tuple, module_masks[module]["coordinates"]))
        if module_union & mask:
            raise RuntimeError(f"module edit masks overlap at {sorted(module_union & mask)[:24]}")
        module_union |= mask
        top_mask = set(map(tuple, tier_masks[MODULE_TIERS[module][-1]][module]["coordinates"]))
        if top_tier_union & top_mask:
            raise RuntimeError(f"top-tier module masks overlap at {sorted(top_tier_union & top_mask)[:24]}")
        top_tier_union |= top_mask
    composed = base.copy()
    composed_px = composed.load()
    for module, tiers in MODULE_TIERS.items():
        top = images[tiers[-1]].load()
        for x, y in tier_masks[tiers[-1]][module]["coordinates"]:
            composed_px[x, y] = top[x, y]
    if composed.tobytes() != all_max.tobytes() or all_diff != top_tier_union:
        raise RuntimeError("all_max is not exact final-tier composition or highest-tier module mask union")
    states["all_max"]["changedTexels"] = len(all_diff)
    states["all_max"]["activeModuleMaskTexels"] = len(module_union)

    source_ordinary = ROOT / "src/main/resources/assets/echopickaxe/textures/item/echo_pickaxe.png"
    ordinary_bytes = source_ordinary.read_bytes()
    mother = source["motherReference"]
    mother_path = (ROOT / mother["path"]).resolve()
    if sha(mother_path.read_bytes()) != mother["sha256"].upper():
        raise RuntimeError("mother reference hash mismatch")
    for name in ["ordinary128", *[t for group in MODULE_TIERS.values() for t in group], "all_max"]:
        stats = render["states"][name]
        alpha_audit[name] = stats
        if len(stats["fourConnectedComponentSizes"]) != 1 or len(stats["eightConnectedComponentSizes"]) != 1:
            raise RuntimeError(f"{name}: sprite alpha is disconnected")

    proof = {
        "schema": "root-pixel-states-v0.1.15-v1", "status": "frozen", "version": "0.1.15",
        "sourceOrdinary": {"path": "src/main/resources/assets/echopickaxe/textures/item/echo_pickaxe.png",
                           "sha256": sha(ordinary_bytes), "size": len(ordinary_bytes)},
        "sourceRootPixelStates": {"path": "artwork/source/root-tier-polish-v0.1.15/root-pixel-states.json",
                                  "sha256": sha(raw), "coordinateSpace": source["coordinateSpace"]},
        "baselineRootPixelStates": {"path": "artwork/source/root-tier-v3/root-pixel-states.json",
                                     "sha256": sha(baseline_raw), "unchangedStates": sorted(set(baseline["states"]) - POLISHED_STATES),
                                     "polishedStates": sorted(POLISHED_STATES), "targetAlphaExact": False,
                                     "jar": BASELINE_JAR, "jarSha256": BASELINE_JAR_SHA256},
        "renderAudit": {"path": "artwork/validation/root-tier-polish-v0.1.15/reference-final-fx/render-audit.json",
                        "sha256": sha(render_bytes),
                        "ordinaryBaseExact": render["ordinaryAgainstSource64"]["pixelExact"],
                        "motherReference": render["motherReference"]},
        "motherReference": copy.deepcopy(mother),
        "ordinary128Base": {"path": "artwork/validation/root-tier-polish-v0.1.15/reference-final-fx/ordinary128.png",
                            "sha256": sha(base_data), "method": "root pixels; exact nearest-2x ordinary comparison"},
        "componentBounds128": copy.deepcopy(bounds),
        "levelsMapping": {"resonance": [0, 1, 2], "split": [0, 1, 2, 3], "tuning": [0, 1],
                          "extension": [0, 1, 2, 3],
                          "candidateIndexFormula": "resonance*32 + split*8 + tuning*4 + extension"},
        "states": states, "moduleEditMasks": module_masks, "moduleTierMasks": tier_masks,
        "moduleGlowMasks": glow_masks, "moduleGlowStableMasks": stable_masks,
        "moduleGlowPhaseRadians": phase_maps, "moduleGlowAmplitude": amplitude_maps,
        "moduleGlowPoints": glow_records,
        "polishScope": {"optimizedStates": sorted(POLISHED_STATES),
                        "unchangedStates": sorted(set(baseline["states"]) - POLISHED_STATES),
                        "targetAlphaExact": False, "nonTargetRgbaAndFxExact": True,
                        "scopeAudit": polish_scope_audit,
                        "polishAudit": {"path": "artwork/source/root-tier-polish-v0.1.15/polish-audit.json",
                                        "sha256": sha(polish_raw)}},
        "glowStyle": {"frames": source["frames"], "ticksPerFrame": source["ticksPerFrame"],
                      "interpolate": True, "maximumRgbAmplitude": 0.06, "alphaChanges": False,
                      "phaseSource": "root-pixel-states.json states[*].glowPointEffects",
                      "inactiveModuleGlow": "exact ordinary glow nearest-2x outside the current active edit union"},
        "compositionProof": {"source": "ordinary128", "allMaxSHA256": sha(all_max_data),
                             "allMaxEqualsFinalTierOverlayComposition": True,
                             "moduleMasksPairwiseDisjoint": True,
                             "allMaxDiffEqualsHighestTierMaskUnion": True},
        "alphaPolicy": "Each sprite uses exact root-authored alpha; active deletions are removed from inherited ordinary glow; models cover each sprite's own alpha.",
        "integrityAudit": {"alphaAndConnectivity": alpha_audit, "glowPointAudit": fx_audit,
                           "moduleBoundsXYXYInclusive": bounds,
                           "ordinaryExact": render["ordinaryAgainstSource64"]["pixelExact"],
                           "motherMaxComparison": render["motherReference"]},
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    proof_path = OUTPUT_DIR / "tier-manifest.json"
    if proof_path.exists():
        raise RuntimeError("tier-manifest already exists; refusing to overwrite frozen proof")
    proof_bytes = (json.dumps(proof, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    proof_path.write_bytes(proof_bytes)
    print(f"proof SHA256: {sha(proof_bytes)}")
    print(f"root pixel SHA256: {sha(raw)}")
    print(f"all_max SHA256: {sha(all_max_data)}")
    print("no static approval was generated; await root review and explicit approval record")
    print("module union sizes:", {m: v["count"] for m, v in module_masks.items()})
    print("tier diff sizes:", {s: v["changedTexels"] for s, v in states.items()})
    print("FX counts:", {s: (v["pointCount"], v["dynamicCount"], v["stableCount"])
                        for s, v in fx_audit.items()})


if __name__ == "__main__":
    main()
