from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path(__file__).resolve().parent / "candidates" / "approved-fullmax-128.png"
OUT = Path(__file__).resolve().parent / "tiers"
VALID = ROOT / "artwork" / "validation" / "approved-fullmax-v0.1.12"
ORDINARY = ROOT / "artwork" / "source" / "native-base-upgrades-v0.1.11" / "ordinary0.png"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def pack(mask: np.ndarray) -> list[list[int]]:
    ys, xs = np.where(mask)
    return [[int(x), int(y)] for x, y in zip(xs, ys)]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    VALID.mkdir(parents=True, exist_ok=True)
    master_img = Image.open(SOURCE).convert("RGBA")
    master = np.array(master_img, dtype=np.uint8)
    h, w = master.shape[:2]
    assert (w, h) == (128, 128)
    rgb = master[:, :, :3].astype(np.int16)
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    opaque = master[:, :, 3] > 0
    yy, xx = np.mgrid[:h, :w]

    # Component masks come only from master pixels and tight component bounds.
    ruby = opaque & (xx >= 28) & (xx <= 81) & (yy >= 3) & (yy <= 41) & (r > 42) & (r > g * 1.34) & (r > b * 1.12)
    violet = opaque & (xx >= 94) & (xx <= 126) & (yy >= 44) & (yy <= 76) & (b > 64) & (b > g * 1.28) & (r > g * 1.12) & (b > r * 1.02)
    # Include pale source facets immediately adjacent to the violet crystal pixels so every
    # active split tier has a complete purple material blade instead of leftover ivory.
    violet_near = violet.copy()
    for _ in range(2):
        padded = np.pad(violet_near, 1)
        expanded = np.zeros_like(violet_near)
        for dy in range(3):
            for dx in range(3):
                expanded |= padded[dy:dy + h, dx:dx + w]
        violet_near = expanded
    pale_violet_facet = violet_near & opaque & (xx >= 94) & (xx <= 126) & (yy >= 44) & (yy <= 76) & (np.min(rgb, axis=2) >= 150) & (b >= g * 0.88) & (r >= g * 0.82)
    purple_module = violet | pale_violet_facet
    jade = opaque & (xx >= 8) & (xx <= 30) & (yy >= 102) & (yy <= 124) & (g > 42) & (g > r * 1.15) & (g > b * 0.95)
    # The star's bright icy cross is tightly bounded; ambient cyan sculk remains shared body.
    star = opaque & (xx >= 87) & (xx <= 97) & (yy >= 28) & (yy <= 43) & (np.maximum(np.maximum(r, g), b) >= 128) & (b >= g * 0.72)

    # Include near-white iris pixels, but keep the black pupil as a separate stable feature.
    iris_white = opaque & (xx >= 15) & (xx <= 23) & (yy >= 108) & (yy <= 114) & (np.minimum(np.minimum(r, g), b) >= 150)
    pupil = opaque & (xx >= 17) & (xx <= 21) & (yy >= 108) & (yy <= 117) & (np.maximum(np.maximum(r, g), b) <= 18)
    eye_core = (jade & (xx >= 14) & (xx <= 25) & (yy >= 106) & (yy <= 119)) | iris_white
    # The approved master includes two short blue-green cradle facets beside the eye and
    # a third upper connector facet. Lower tiers mute these original pixels; upper tiers
    # reveal them in place without drawing or moving any texels.
    bright_teal = opaque & (g >= 82) & (b >= 82) & (g > r * 1.7) & (b > r * 1.45)
    eye_support_left = bright_teal & (xx >= 10) & (xx <= 14) & (yy >= 106) & (yy <= 118)
    eye_support_right = bright_teal & (xx >= 24) & (xx <= 28) & (yy >= 106) & (yy <= 118)
    eye_support_upper = bright_teal & (xx >= 11) & (xx <= 15) & (yy >= 102) & (yy <= 107)
    eye_support_upper_right = bright_teal & (xx >= 24) & (xx <= 28) & (yy >= 102) & (yy <= 107)
    eye_support = ((jade | iris_white) & ~eye_core) | eye_support_left | eye_support_right | eye_support_upper | eye_support_upper_right
    # Protect the pupil from all painting/recoloring, including neutralization.
    eye_core &= ~pupil
    eye_support &= ~pupil

    # The ruby upper-back stepped ridge is exposed at tier II; tier I retains the full sharp blade.
    ruby_ridge = ruby & (xx >= 45) & (xx <= 72) & (yy <= 8)
    # Frequency tiers reveal the same curved blade first, then two outer facet bands.
    violet_i = violet & (xx <= 111)
    violet_ii = violet & (xx >= 112) & (xx <= 118)
    violet_iii = violet & (xx >= 119)
    # The eye pupil and iris are tier I; separate cradle/support facets appear in II and III.
    jade_core = eye_core | pupil
    jade_support_ii = eye_support_left | eye_support_right | (eye_support & (xx <= 25) & (yy >= 106) & (yy <= 120))
    jade_support_iii = eye_support_upper | eye_support_upper_right | (eye_support & ~jade_support_ii)

    jade_module = jade | iris_white | pupil | eye_support_left | eye_support_right | eye_support_upper | eye_support_upper_right
    modules = {"resonance": ruby, "split": purple_module, "tuning": star, "extension": jade_module}
    neutral = master.copy()

    # Resolve sculk/ivory fallback from the already shipped ordinary native texture palette.
    old = np.array(Image.open(ORDINARY).convert("RGBA"), dtype=np.uint8)
    old_colors = old[old[:, :, 3] > 0, :3]
    # Bone colors are the three high-value neutral colors; the rest are sculk/cyan body.
    bone_palette = np.array([[251, 245, 225], [242, 228, 196], [198, 187, 154]], dtype=np.int16)
    sculk_palette = np.array([[0, 14, 22], [0, 19, 29], [0, 42, 55], [3, 60, 75], [0, 85, 102], [1, 115, 131]], dtype=np.int16)

    def fallback(mask: np.ndarray, prefer_bone: np.ndarray | None = None, force_sculk: np.ndarray | None = None) -> None:
        if prefer_bone is None:
            prefer_bone = np.zeros((h, w), dtype=bool)
        if force_sculk is None:
            force_sculk = np.zeros((h, w), dtype=bool)
        for y, x in zip(*np.where(mask)):
            src = rgb[y, x]
            # Preserve a dark outline/facet cut as sculk; turn the bright material face to ivory.
            is_bone = bool(not force_sculk[y, x] and (prefer_bone[y, x] or int(src.max()) >= 115))
            palette = bone_palette if is_bone else sculk_palette
            delta = palette.astype(np.int32) - src.astype(np.int32)
            ix = int(np.argmin((delta * delta).sum(axis=1)))
            neutral[y, x, :3] = palette[ix].astype(np.uint8)
            neutral[y, x, 3] = 255

    # The neutral enhanced head is still from the 128 master; only component material pixels change.
    fallback(ruby, prefer_bone=(yy >= 17), force_sculk=ruby_ridge)
    fallback(purple_module, prefer_bone=(yy >= 54))
    fallback(star, prefer_bone=(yy >= 33))
    fallback(jade_module, prefer_bone=eye_core, force_sculk=eye_support)
    # Pupil is a dark sculk inset while inactive and remains untouched in every active tier.
    for y, x in zip(*np.where(pupil)):
        neutral[y, x, :3] = np.array([1, 8, 12], dtype=np.uint8)
        neutral[y, x, 3] = 255

    def make_state(name: str, active: dict[str, np.ndarray]) -> tuple[Path, np.ndarray]:
        result = neutral.copy()
        # Red tier I keeps the entire sharp blade in ruby and only darkens its upper-back
        # ridge; it never cuts a rectangular hole out of the blade.
        if name == "resonance1":
            ruby_palette = np.array([[44, 5, 18], [86, 8, 28], [132, 10, 37]], dtype=np.int32)
            for y, x in zip(*np.where(ruby_ridge)):
                src = rgb[y, x].astype(np.int32)
                delta = ruby_palette - src
                idx = int(np.argmin((delta * delta).sum(axis=1)))
                result[y, x, :3] = np.clip(ruby_palette[idx], 0, 255).astype(np.uint8)
                result[y, x, 3] = 255
        # Purple tier I restores the whole curved blade as dark/mid purple material, then
        # reveals its first native facet. Tier II reveals the second facet; III restores all
        # original source texels in the module region exactly.
        if name in ("split1", "split2", "split3"):
            palette = np.array([[42, 12, 68], [74, 20, 116], [112, 34, 168], [150, 57, 205], [192, 116, 234]], dtype=np.int16)
            for y, x in zip(*np.where(purple_module)):
                lum = int(rgb[y, x].mean())
                idx = min(4, max(0, int((lum - 35) / 48)))
                result[y, x, :3] = palette[idx].astype(np.uint8)
                result[y, x, 3] = 255
            first_facet = violet & (xx <= 111)
            second_facet = violet & (xx >= 112) & (xx <= 118)
            if name in ("split1", "split2"):
                result[first_facet] = master[first_facet]
            if name == "split2":
                result[second_facet] = master[second_facet]
            if name == "split3":
                result[purple_module] = master[purple_module]
        for module, mask in active.items():
            # Restore exact approved-master RGBA on exposed native facets.
            if module != "split":
                result[mask] = master[mask]
        path = OUT / f"{name}.png"
        Image.fromarray(result, "RGBA").save(path, optimize=False)
        return path, result

    states: dict[str, tuple[Path, np.ndarray, dict[str, int]]] = {}
    specs = {
        "enhanced-neutral128": {},
        "resonance1": {"resonance": ruby & ~ruby_ridge},
        "resonance2": {"resonance": ruby},
        "split1": {"split": violet_i},
        "split2": {"split": violet_i | violet_ii},
        "split3": {"split": violet_i | violet_ii | violet_iii},
        "tuning1": {"tuning": star},
        "extension1": {"extension": jade_core},
        "extension2": {"extension": jade_core | jade_support_ii},
        "extension3": {"extension": jade_core | jade_support_ii | jade_support_iii},
    }
    for name, active in specs.items():
        path, image = make_state(name, active)
        active_by_module = {module: int(mask.sum()) for module, mask in active.items()}
        states[name] = (path, image, active_by_module)

    # Build four-module combination order expected by candidate index: R bits, split, tuning, extension.
    full_path = OUT / "all_max.png"
    Image.fromarray(master, "RGBA").save(full_path, optimize=False)
    assert np.array_equal(np.array(Image.open(full_path).convert("RGBA")), master), "all_max must be pixel-exact master"
    assert sha(full_path) == sha(SOURCE), "all_max file bytes should preserve anchor PNG exactly"
    # Store byte-for-byte copy as well: PNG re-encoding is allowed to differ byte-wise, but pixel bytes may not.
    full_path.write_bytes(SOURCE.read_bytes())
    assert sha(full_path) == sha(SOURCE)

    # Derive global per-module edit masks relative to neutral enhanced base.
    neutral_arr = states["enhanced-neutral128"][1]
    edit_masks: dict[str, list[list[int]]] = {}
    for module, target in modules.items():
        edit = np.any(neutral_arr != master, axis=2) & target
        edit_masks[module] = pack(edit)

    # Glow selections use only approved source highlights; pupil excluded; only the star core
    # and eye catchlight are stable, while tips/facets are phase-pulsed by the release builder.
    glow_masks: dict[str, dict[str, list[list[int]]]] = {}
    stable_masks: dict[str, dict[str, list[list[int]]]] = {}
    for tiername, active in specs.items():
        if not active:
            continue
        selected: dict[str, list[list[int]]] = {}
        stable: dict[str, list[list[int]]] = {}
        for module, mask in active.items():
            source_rgb = master[:, :, :3]
            if module == "resonance":
                bright = mask & (r >= 180) & (g >= 40)
                stable[module] = []
                selected[module] = pack(bright)
            elif module == "split":
                bright = mask & (g >= 120) & (b >= 190)
                stable[module] = []
                selected[module] = pack(bright)
            elif module == "tuning":
                bright = mask & (g >= 170) & (b >= 180)
                core = bright & (xx >= 91) & (xx <= 92) & (yy >= 35) & (yy <= 36)
                stable[module] = pack(core)
                selected[module] = pack(bright & ~core)
            elif module == "extension":
                bright = mask & (g >= 160) & (r >= 35) & ~pupil
                eye_bright = bright & iris_white & (np.min(source_rgb, axis=2) >= 190)
                stable[module] = pack(eye_bright)
                selected[module] = pack(bright & ~eye_bright)
        glow_masks[tiername] = selected
        stable_masks[tiername] = stable

    # Per-state hashes, diff coordinate counts, active replacement coverage and explicit level mapping.
    manifest_states: dict[str, dict] = {}
    for name, (path, image, active_counts) in states.items():
        diff = np.any(image != master, axis=2)
        # Per-module retained facet coverage is exact and based on these mask rules.
        manifest_states[name] = {
            "path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "sha256": sha(path),
            "diffPixelsFromAllMax": int(diff.sum()),
            "activeRestoredPixels": active_counts,
        }
    full_image = np.array(Image.open(full_path).convert("RGBA"))
    manifest_states["all_max"] = {
        "path": str(full_path.relative_to(ROOT)).replace("\\", "/"),
        "sha256": sha(full_path),
        "diffPixelsFromAllMax": int(np.any(full_image != master, axis=2).sum()),
        "pixelExactAnchor": bool(np.array_equal(full_image, master)),
        "activeRestoredPixels": {k: int(v.sum()) for k, v in modules.items()},
    }
    facet_masks = {
        "resonance": {"ridge": pack(ruby_ridge)},
        "split": {"facet1": pack(violet_i), "facet2": pack(violet_ii), "facet3": pack(violet_iii)},
        "tuning": {"tips": pack(star & ~((np.abs(xx - 92) <= 1) & (np.abs(yy - 36) <= 1)))},
        "extension": {"irisPupilCradle": pack(jade_core), "sideSupports": pack(jade_support_ii), "upperSupport": pack(jade_support_iii)},
    }
    module_tier_masks = {
        "resonance1": {"resonance": pack(ruby)}, "resonance2": {"resonance": pack(ruby)},
        "split1": {"split": pack(purple_module)}, "split2": {"split": pack(purple_module)}, "split3": {"split": pack(purple_module)},
        "tuning1": {"tuning": pack(star)},
        "extension1": {"extension": pack(jade_core)}, "extension2": {"extension": pack(jade_core | jade_support_ii)}, "extension3": {"extension": pack(jade_core | jade_support_ii | jade_support_iii)},
    }
    # Verify composition from the neutral 128 base and the four maximum single-module states.
    composed = neutral_arr.copy()
    maximum_state = {"resonance": "resonance2", "split": "split3", "tuning": "tuning1", "extension": "extension3"}
    for module, tier_name in maximum_state.items():
        overlay = states[tier_name][1]
        composed[modules[module]] = overlay[modules[module]]
    compose_pixel_exact = bool(np.array_equal(composed, master))
    assert compose_pixel_exact, "neutral base + four max modules must reproduce the approved fullmax pixels exactly"

    manifest = {
        "schema": "approved-fullmax-v0.1.12-tier-derivation-v1",
        "anchor": {"path": str(SOURCE.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(SOURCE), "size": [128, 128]},
        "ordinary0": {"path": str(ORDINARY.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(ORDINARY), "usedOnlyForNeutralPalette": True},
        "neutralEnhancedBase": manifest_states["enhanced-neutral128"],
        "stateFileDirectory": str(OUT.relative_to(ROOT)).replace("\\", "/"),
        "levelsMapping": {"resonance": [0, 1, 2], "split": [0, 1, 2, 3], "tuning": [0, 1], "extension": [0, 1, 2, 3], "candidateIndexFormula": "resonance*32 + split*8 + tuning*4 + extension"},
        "moduleEditMasks": {k: {"coordinates": v, "count": len(v)} for k, v in edit_masks.items()},
        "moduleTierMasks": module_tier_masks,
        "tierFacetMasks": facet_masks,
        "moduleGlowMasks": glow_masks,
        "moduleGlowStableMasks": stable_masks,
        "composeProof": {"method": "neutralEnhancedBase + maximum single-module states, applied only under each moduleEditMask", "pixelExactAnchor": compose_pixel_exact, "sha256": sha(full_path)},
        "states": manifest_states,
        "maskSources": {"resonance": "anchor RGB red-hue texels in tight bbox; tier1 preserves complete blade and remaps only the crest ridge to dark ruby", "split": "anchor RGB violet texels plus adjacent pale facets inside the tight lobe bounds; tier1 turns every module texel into purple material and reveals the first native facet, tier2 adds a second facet, tier3 restores the complete master region", "tuning": "anchor bright icy cross texels in tight bbox", "extension": "anchor jade hue plus pale iris and locally bounded side/upper teal cradle facets; pupil is explicitly excluded from fallback painting and restored identically at every active tier"},
        "alphaPolicy": "All states preserve the anchor 128x128 canvas and opaque/transparent silhouette; no external pixels were added.",
    }
    (VALID / "tier-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    # Tier overview on dark board, nearest-neighbor 4x, labels intentionally compact.
    order = ["enhanced-neutral128", "resonance1", "resonance2", "split1", "split2", "split3", "tuning1", "extension1", "extension2", "extension3", "all_max"]
    cell = 512
    label = 32
    cols = 4
    rows = (len(order) + cols - 1) // cols
    board = Image.new("RGB", (cols * cell, rows * (cell + label)), (16, 20, 29))
    draw = ImageDraw.Draw(board)
    for idx, name in enumerate(order):
        row, col = divmod(idx, cols)
        img = Image.open(OUT / f"{name}.png").convert("RGBA").resize((cell, cell), Image.Resampling.NEAREST)
        bg = Image.new("RGBA", img.size, (13, 17, 24, 255))
        bg.alpha_composite(img)
        x, y = col * cell, row * (cell + label)
        board.paste(bg.convert("RGB"), (x, y + label))
        draw.text((x + 8, y + 8), name, fill=(245, 245, 238))
    board.save(VALID / "tier-overview-dark-4x.png")

    # White background visual counterpart.
    white = Image.new("RGB", board.size, (238, 239, 242))
    for idx, name in enumerate(order):
        row, col = divmod(idx, cols)
        img = Image.open(OUT / f"{name}.png").convert("RGBA").resize((cell, cell), Image.Resampling.NEAREST)
        bg = Image.new("RGBA", img.size, (246, 247, 249, 255))
        bg.alpha_composite(img)
        x, y = col * cell, row * (cell + label)
        white.paste(bg.convert("RGB"), (x, y + label))
        ImageDraw.Draw(white).text((x + 8, y + 8), name, fill=(28, 30, 34))
    white.save(VALID / "tier-overview-white-4x.png")

    # Separate comparison of allmax vs neutral and selected component tiers, enlarged 8x.
    compare = ["enhanced-neutral128", "resonance1", "resonance2", "split1", "split2", "split3", "extension1", "extension2", "extension3", "all_max"]
    zoom = Image.new("RGB", (4 * 512, 3 * (512 + 32)), (16, 20, 29))
    d = ImageDraw.Draw(zoom)
    for idx, name in enumerate(compare):
        row, col = divmod(idx, 4)
        img = Image.open(OUT / f"{name}.png").convert("RGBA").resize((512, 512), Image.Resampling.NEAREST)
        bg = Image.new("RGBA", img.size, (13, 17, 24, 255)); bg.alpha_composite(img)
        x, y = col * 512, row * 544
        zoom.paste(bg.convert("RGB"), (x, y + 32)); d.text((x + 8, y + 8), name, fill="white")
    zoom.save(VALID / "tier-compare-dark-4x.png")

    print(json.dumps({"anchor_sha256": sha(SOURCE), "all_max_sha256": sha(full_path), "all_max_exact": True, "composed_max_exact": compose_pixel_exact, "states": {k: {"sha256": sha(v[0]), "active": v[2]} for k, v in states.items()}, "editMaskCounts": {k: len(v) for k, v in edit_masks.items()}, "glowCounts": {k: {m: len(c) for m, c in vals.items()} for k, vals in glow_masks.items()}, "stableCounts": {k: {m: len(c) for m, c in vals.items()} for k, vals in stable_masks.items()}, "pupilCoords": pack(pupil)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
