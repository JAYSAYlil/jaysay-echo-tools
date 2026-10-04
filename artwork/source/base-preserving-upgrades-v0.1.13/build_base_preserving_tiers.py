from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
ORDINARY_PATH = ROOT / "src/main/resources/assets/echopickaxe/textures/item/echo_pickaxe.png"
ANCHOR_PATH = ROOT / "artwork/source/approved-fullmax-v0.1.12/candidates/approved-fullmax-128.png"
OUT = Path(__file__).resolve().parent
VALID = ROOT / "artwork/validation/base-preserving-upgrades-v0.1.13"

EXPECTED_ORDINARY_SHA = "296326965171A658F9CD40E0C9C42FB3ABF5B1094AF9EFB0005096061C1711F5"
EXPECTED_ANCHOR_SHA = "BE0F000D3B70B35E10984951A6B1E6DA66CD204381A22E3C8FB9399C23019B67"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest().upper()


def dilate(mask: np.ndarray, steps: int = 1) -> np.ndarray:
    result = mask.copy()
    h, w = result.shape
    for _ in range(steps):
        padded = np.pad(result, 1)
        expanded = np.zeros_like(result)
        for dy in range(3):
            for dx in range(3):
                expanded |= padded[dy:dy + h, dx:dx + w]
        result = expanded
    return result


def coords(mask: np.ndarray) -> list[list[int]]:
    ys, xs = np.where(mask)
    return [[int(x), int(y)] for x, y in zip(xs, ys)]


def apply_component(base: np.ndarray, source: np.ndarray, source_mask: np.ndarray,
                    bone_mask: np.ndarray, offset: tuple[int, int], forbidden: np.ndarray | None = None,
                    fill_mask: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Replace the base bone with nearest approved material samples and add only source component pixels."""
    dx, dy = offset
    ys, xs = np.where(source_mask)
    if forbidden is None:
        forbidden = np.zeros((128, 128), dtype=bool)
    shifted = [(int(x + dx), int(y + dy), int(x), int(y)) for x, y in zip(xs, ys)
               if 0 <= x + dx < 128 and 0 <= y + dy < 128 and not forbidden[y + dy, x + dx]]
    out = base.copy()
    bx, by = np.where(bone_mask)
    for y, x in zip(bx, by):
        out[y, x] = (0, 0, 0, 0)
    if not shifted:
        return out, bone_mask.copy()
    sx = np.array([p[0] for p in shifted], dtype=np.int32)
    sy = np.array([p[1] for p in shifted], dtype=np.int32)
    ox = np.array([p[2] for p in shifted], dtype=np.int32)
    oy = np.array([p[3] for p in shifted], dtype=np.int32)
    for tx, ty, x, y in shifted:
        out[ty, tx] = source[y, x]
    # Bone coverage may sample the whole approved facet set so partial tiers retain
    # the source's cut planes instead of becoming one flat fallback color.
    sample_mask = source_mask if fill_mask is None else fill_mask
    fy, fx = np.where(sample_mask)
    fshifted = [(int(x + dx), int(y + dy), int(x), int(y)) for x, y in zip(fx, fy)
                if 0 <= x + dx < 128 and 0 <= y + dy < 128 and not forbidden[y + dy, x + dx]]
    if not fshifted:
        fshifted = shifted
    sx = np.array([p[0] for p in fshifted], dtype=np.int32)
    sy = np.array([p[1] for p in fshifted], dtype=np.int32)
    ox = np.array([p[2] for p in fshifted], dtype=np.int32)
    oy = np.array([p[3] for p in fshifted], dtype=np.int32)
    for y, x in zip(bx, by):
        if 0 <= y - dy < 128 and 0 <= x - dx < 128 and source_mask[y - dy, x - dx]:
            continue
        j = int(np.argmin((sx - x) ** 2 + (sy - y) ** 2))
        out[y, x] = source[oy[j], ox[j]]
    module_mask = bone_mask.copy()
    for tx, ty, _, _ in shifted:
        module_mask[ty, tx] = True
    return out, module_mask


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    VALID.mkdir(parents=True, exist_ok=True)
    assert sha(ORDINARY_PATH) == EXPECTED_ORDINARY_SHA, "ordinary 64 source changed"
    assert sha(ANCHOR_PATH) == EXPECTED_ANCHOR_SHA, "approved 128 anchor changed"
    ordinary64 = Image.open(ORDINARY_PATH).convert("RGBA")
    master = np.array(Image.open(ANCHOR_PATH).convert("RGBA"), dtype=np.uint8)
    base_img = ordinary64.resize((128, 128), Image.Resampling.NEAREST)
    base = np.array(base_img, dtype=np.uint8)
    orig = np.array(ordinary64, dtype=np.uint8)
    h, w = 128, 128
    assert orig.shape[:2] == (64, 64)
    yy64, xx64 = np.mgrid[:64, :64]
    yy, xx = np.mgrid[:128, :128]
    p = orig[:, :, :3].astype(np.int16)
    r64, g64, b64 = p[:, :, 0], p[:, :, 1], p[:, :, 2]
    bone64 = (orig[:, :, 3] > 0) & (r64 > 140) & (g64 > 130) & (b64 > 110) & (r64 - g64 < 40)
    bone_regions = {
        "resonance": (xx64 >= 17) & (xx64 <= 35) & (yy64 >= 5) & (yy64 <= 19),
        "split": (xx64 >= 48) & (xx64 <= 59) & (yy64 >= 21) & (yy64 <= 33),
        "tuning": (xx64 >= 39) & (xx64 <= 47) & (yy64 >= 13) & (yy64 <= 20),
        "extension": (xx64 >= 5) & (xx64 <= 15) & (yy64 >= 49) & (yy64 <= 58),
    }
    expected_bones = {"resonance": 43, "split": 21, "tuning": 6, "extension": 13}
    bone_masks64 = {k: bone64 & region for k, region in bone_regions.items()}
    for key, mask in bone_masks64.items():
        assert int(mask.sum()) == expected_bones[key], (key, int(mask.sum()))
    bone_masks = {k: np.repeat(np.repeat(mask, 2, axis=0), 2, axis=1) for k, mask in bone_masks64.items()}

    rgb = master[:, :, :3].astype(np.int32)
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    opaque = master[:, :, 3] > 0

    # Tight source-pixel component masks are material-derived; no master shaft/head pixels are copied.
    raw_red = opaque & (xx >= 25) & (xx <= 82) & (yy >= 2) & (yy <= 42) & (r >= 36) & (r > g * 1.25) & (r > b * 1.08)
    red_neighbor = dilate(raw_red, 1) & opaque & (xx >= 25) & (xx <= 82) & (yy >= 2) & (yy <= 42) & (r > g) & (r > b * 0.82)
    red_all = raw_red | red_neighbor
    # The source crop contains one detached red tail and a single abrupt upper spike.
    # Exclude those crop remnants while preserving the connected hooked cutting edge.
    red_all &= ~((xx >= 70) & (xx <= 77) & (yy >= 12) & (yy <= 21))
    red_thin = red_all & ((yy >= 14) | (xx <= 44))
    red_thin &= ~(((xx >= 45) & (yy <= 7)) | ((xx == 44) & (yy <= 7)))
    red_offset = (6, -1)

    raw_purple = opaque & (xx >= 94) & (xx <= 126) & (yy >= 44) & (yy <= 76) & (b >= 55) & (b > g * 1.24) & (r > g * 1.10) & (b > r * 0.96)
    purple_near = dilate(raw_purple, 2)
    pale_purple = purple_near & opaque & (xx >= 94) & (xx <= 126) & (yy >= 44) & (yy <= 76) & (np.min(rgb, axis=2) >= 148) & (b >= g * 0.85) & (r >= g * 0.78)
    purple_all = raw_purple | pale_purple
    # One detached dark-purple crop speck in the anchor is outside the blade lobe.
    purple_all &= ~((xx == 122) & (yy == 58))
    purple_facet1 = purple_all & (xx <= 111)
    purple_facet2 = purple_all & (xx >= 112) & (xx <= 118)
    purple_facet3 = purple_all & (xx >= 119)
    purple_offset = (1, -3)

    raw_star = opaque & (xx >= 87) & (xx <= 97) & (yy >= 28) & (yy <= 43) & (np.max(rgb, axis=2) >= 128) & (b >= g * 0.72)
    star_offset = (-3, -3)

    raw_green = opaque & (xx >= 8) & (xx <= 30) & (yy >= 102) & (yy <= 124) & (g >= 42) & (g > r * 1.14) & (g > b * 0.94)
    green_near = dilate(raw_green, 1)
    iris_white = opaque & (xx >= 15) & (xx <= 23) & (yy >= 108) & (yy <= 115) & (np.min(rgb, axis=2) >= 150)
    pupil = opaque & (xx >= 17) & (xx <= 21) & (yy >= 108) & (yy <= 117) & (np.max(rgb, axis=2) <= 18)
    teal_support = opaque & (xx >= 10) & (xx <= 28) & (yy >= 102) & (yy <= 120) & (g >= 82) & (b >= 82) & (g > r * 1.7) & (b > r * 1.45)
    green_all = raw_green | (green_near & iris_white) | pupil | teal_support
    eye_core = green_all & (xx >= 14) & (xx <= 24) & (yy >= 107) & (yy <= 119)
    eye_core |= iris_white | pupil
    # II exposes lower left/right cradle arms; III adds the remaining upper and lower source
    # cradle pixels, creating the third upper support rather than merely brightening II.
    eye_sides = green_all & (((xx >= 10) & (xx <= 14)) | ((xx >= 24) & (xx <= 28))) & (yy >= 109) & (yy <= 119)
    eye_upper = green_all & ~eye_core & ~eye_sides
    extension_offset = (1, -6)

    # Distinct activation tiers use the approved source's native structural regions.
    specs = {
        "resonance1": ("resonance", red_thin, red_offset),
        "resonance2": ("resonance", red_all, red_offset),
        "split1": ("split", purple_facet1, purple_offset),
        "split2": ("split", purple_facet1 | purple_facet2, purple_offset),
        "split3": ("split", purple_all, purple_offset),
        "tuning1": ("tuning", raw_star, star_offset),
        "extension1": ("extension", eye_core, extension_offset),
        "extension2": ("extension", eye_core | eye_sides, extension_offset),
        "extension3": ("extension", green_all, extension_offset),
    }
    source_masks = {"resonance": red_all, "split": purple_all, "tuning": raw_star, "extension": green_all}
    offsets = {"resonance": red_offset, "split": purple_offset, "tuning": star_offset, "extension": extension_offset}

    def get_source(tier: str, module: str, stage_mask: np.ndarray) -> np.ndarray:
        material = master.copy()
        if module == "resonance" and tier == "resonance1":
            # The active I crystal is the sharp thin cutter; upper-back plate facets stay in
            # dark ruby sculk shadow until II grows the full source ridge.
            ridge = red_all & ~red_thin
            dark_ruby = np.array([70, 7, 25], dtype=np.uint8)
            material[ridge, :3] = dark_ruby
        return material

    states: dict[str, tuple[np.ndarray, str, np.ndarray]] = {}
    module_edit_masks: dict[str, np.ndarray] = {}
    for tier, (module, stage_mask, offset) in specs.items():
        material_source = get_source(tier, module, stage_mask)
        forbidden = np.logical_or.reduce([m for k, m in bone_masks.items() if k != module])
        tier_base, edit = apply_component(base, material_source, stage_mask, bone_masks[module], offset, forbidden,
                                          fill_mask=purple_all if module == "split" else None)
        states[tier] = (tier_base, module, edit)
        module_edit_masks[module] = edit if module not in module_edit_masks else module_edit_masks[module] | edit

    # Single star has no tiers; all_max is ordinary128 plus each module's maximum component layer.
    composed = base.copy()
    for key in ("resonance2", "split3", "tuning1", "extension3"):
        image, module, mask = states[key]
        composed[mask] = image[mask]
        module_edit_masks[module] = mask if module not in module_edit_masks else module_edit_masks[module] | mask
    states["all_max"] = (composed.copy(), "all", np.logical_or.reduce(list(module_edit_masks.values())))

    # Every inactive component and common body must remain exactly ordinary128.
    for tier, (image, module, edit) in states.items():
        if module == "all":
            allowed = np.logical_or.reduce(list(module_edit_masks.values()))
        else:
            allowed = edit
        diff = np.any(image != base, axis=2)
        assert not np.any(diff & ~allowed), f"{tier}: changed pixels outside the active module mask"
        if module != "all":
            for other, bone in bone_masks.items():
                if other != module:
                    assert np.array_equal(image[bone], base[bone]), f"{tier}: inactive {other} bone changed"
            assert np.array_equal(image[~allowed], base[~allowed]), f"{tier}: inactive/common body differs from ordinary"
            # Every old bone texel in the active module is opaque and no longer an ivory/bone pixel.
            assert np.all(image[bone_masks[module], 3] == 255)

    assert np.array_equal(states["all_max"][0], composed)
    assert np.array_equal(composed[~np.logical_or.reduce(list(module_edit_masks.values()))], base[~np.logical_or.reduce(list(module_edit_masks.values()))])

    # Save ordinary base, independent single-upgrade states, and composited all-max.
    Image.fromarray(base, "RGBA").save(OUT / "ordinary128.png", optimize=False)
    hashes = {}
    state_records = {}
    for name, (image, module, edit) in states.items():
        path = OUT / f"{name}.png"
        Image.fromarray(image, "RGBA").save(path, optimize=False)
        hashes[name] = sha(path)
        state_records[name] = {"path": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": hashes[name], "module": module, "changedTexels": int(np.any(image != base, axis=2).sum()), "activeModuleMaskTexels": int(edit.sum()), "inactiveBasePixelExact": None if module == "all" else True}
    base_hash = sha(OUT / "ordinary128.png")

    # Global edit masks are union coordinates from the actual maximum overlays, relative to ordinary128.
    max_module_states = {"resonance": "resonance2", "split": "split3", "tuning": "tuning1", "extension": "extension3"}
    global_masks = {}
    for module, tier in max_module_states.items():
        image = states[tier][0]
        diff = np.any(image != base, axis=2)
        global_masks[module] = {"coordinates": coords(diff), "count": int(diff.sum())}

    # Glow candidates are source highlight texels only; phase/motion generation remains with release.
    glow = {}
    stable = {}
    module_tier_masks = {}
    def shifted_coords(mask: np.ndarray, offset: tuple[int, int], forbidden: np.ndarray | None = None) -> list[list[int]]:
        dx, dy = offset
        moved = np.zeros_like(mask)
        if forbidden is None:
            forbidden = np.zeros_like(mask)
        ys, xs = np.where(mask)
        for x, y in zip(xs, ys):
            tx, ty = int(x + dx), int(y + dy)
            if 0 <= tx < 128 and 0 <= ty < 128 and not forbidden[ty, tx]:
                moved[ty, tx] = True
        return coords(moved)
    def stable_phase(module: str, x: int, y: int) -> float:
        # Absolute output coordinates and module-specific grouping make the phase invariant
        # when unrelated upgrades are enabled or disabled.
        if module == "resonance":
            return round(((x + 2 * y) % 16) * (2 * np.pi / 16), 6)
        if module == "split":
            facet = 0 if x <= 112 else (1 if x <= 119 else 2)
            return round((facet * (2 * np.pi / 3) + (y % 4) * (np.pi / 12)) % (2 * np.pi), 6)
        if module == "tuning":
            # Four arms/tips use fixed cardinal phases; the 2x2 stable core is excluded.
            dx, dy = x - 86, y - 32
            angle = float(np.arctan2(dy, dx))
            return round(angle % (2 * np.pi), 6)
        group = 0 if x < 22 else (1 if x > 24 else 2)
        return round((group * (2 * np.pi / 3) + (y % 3) * (np.pi / 18)) % (2 * np.pi), 6)
    for tier, (module, stage_mask, _) in specs.items():
        rr, gg, bb = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
        if module == "resonance":
            selected = stage_mask & (rr >= 180) & (gg >= 40)
            fixed = np.zeros_like(stage_mask)
        elif module == "split":
            selected = stage_mask & (gg >= 120) & (bb >= 190)
            fixed = np.zeros_like(stage_mask)
        elif module == "tuning":
            selected = stage_mask & (gg >= 170) & (bb >= 180)
            fixed = selected & (xx >= 88) & (xx <= 89) & (yy >= 34) & (yy <= 35)
            selected &= ~fixed
        else:
            selected = stage_mask & (gg >= 160) & (rr >= 35) & ~pupil
            fixed = selected & iris_white & (np.min(rgb, axis=2) >= 190)
            selected &= ~fixed
        offset = offsets[module]
        forbidden = np.logical_or.reduce([m for k, m in bone_masks.items() if k != module])
        glow[tier] = {module: shifted_coords(selected, offset, forbidden)}
        stable[tier] = {module: shifted_coords(fixed, offset, forbidden)}
        module_tier_masks[tier] = {module: {"coordinates": coords(states[tier][2]), "count": int(states[tier][2].sum())}}

    glow_phases = {}
    glow_amplitudes = {}
    glow_points = {}
    for tier, by_module in glow.items():
        module = next(iter(by_module))
        points = by_module[module]
        phase_map = {f"{x},{y}": stable_phase(module, x, y) for x, y in points}
        amp = 0.04 if module in ("tuning", "extension") else 0.05
        amp_map = {f"{x},{y}": amp for x, y in points}
        glow_phases[tier] = {module: phase_map}
        glow_amplitudes[tier] = {module: amp_map}
        def point_group(px: int, py: int) -> str:
            if module == "resonance": return "blade-arc"
            if module == "split": return "facet-1" if px <= 112 else ("facet-2" if px <= 119 else "facet-3")
            if module == "tuning":
                dx, dy = px - 86, py - 32
                return "north-tip" if dy < 0 else ("south-tip" if dy > 0 else ("west-tip" if dx < 0 else "east-tip"))
            return "left-prong" if px < 22 else ("right-prong" if px > 24 else "upper-facet")
        glow_points[tier] = {module: [
            {"x": x, "y": y, "phaseRadians": phase_map[f"{x},{y}"], "amplitude": amp_map[f"{x},{y}"], "stable": False, "group": point_group(x, y)}
            for x, y in points
        ]}
        stable_points = stable[tier][module]
        if stable_points:
            glow_points[tier][module].extend(
                {"x": x, "y": y, "phaseRadians": 0.0, "amplitude": 0.0, "stable": True,
                 "group": "star-core" if module == "tuning" else "iris-core"}
                for x, y in stable_points
            )

    manifest = {
        "schema": "base-preserving-upgrades-v0.1.13-v1",
        "status": "frozen",
        "sourceOrdinary": {"path": str(ORDINARY_PATH.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(ORDINARY_PATH), "size": [64, 64]},
        "sourceApprovedFullmax": {"path": str(ANCHOR_PATH.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(ANCHOR_PATH), "size": [128, 128], "usedOnlyForComponentPixels": True},
        "ordinary128Base": {"path": str((OUT / "ordinary128.png").relative_to(ROOT)).replace("\\", "/"), "sha256": base_hash, "method": "nearest-neighbor 2x of ordinary64"},
        "componentAlignment": {
            "method": "native 128 master component pixel masks, translated only to align to doubled ordinary64 component centers; source colors/shape kept; no source body copied",
            "offsetsXY": {"resonance": list(red_offset), "split": list(purple_offset), "tuning": list(star_offset), "extension": list(extension_offset)},
            "ordinaryBoneCounts64": expected_bones,
        },
        "levelsMapping": {"resonance": [0, 1, 2], "split": [0, 1, 2, 3], "tuning": [0, 1], "extension": [0, 1, 2, 3], "candidateIndexFormula": "resonance*32 + split*8 + tuning*4 + extension"},
        "states": state_records,
        "moduleEditMasks": global_masks,
        "moduleTierMasks": module_tier_masks,
        "moduleGlowMasks": glow,
        "moduleGlowStableMasks": stable,
        "moduleGlowPhaseRadians": glow_phases,
        "moduleGlowAmplitude": glow_amplitudes,
        "moduleGlowPoints": glow_points,
        "pupilCoordinatesInAnchor": coords(pupil),
        "pupilCoordinatesInOutput": shifted_coords(pupil, extension_offset),
        "glowStyle": {"frames": 16, "ticksPerFrame": 3, "maximumRgbAmplitude": 0.06, "alphaChanges": False, "fixedGroupPhaseMap": True, "moduleNotes": {"resonance": "slow phase gradient along the cutting edge", "split": "facet groups pulse out of phase", "tuning": "four tips pulse lightly; 2x2 star core remains stable", "extension": "iris and black vertical pupil remain stable; outer prongs/facets pulse lightly"}, "inactiveModuleGlow": "Preserve ordinaryBase128 normal64 glow pixels via exact nearest-neighbor 2x; this artwork manifest defines only newly selected upgrade masks."},
        "compositionProof": {"source": "ordinary128Base", "components": list(max_module_states.items()), "allMaxSHA256": hashes["all_max"], "ordinaryBaseOutsideActiveModulesExact": True, "allInactivePartsInSingleModuleStatesExact": True},
        "alphaPolicy": "Unchanged ordinary base alpha outside active module masks; active masks use source component texels plus covered old bone; no build/install performed.",
    }
    (VALID / "tier-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    order = ["ordinary128", "resonance1", "resonance2", "split1", "split2", "split3", "extension1", "extension2", "extension3", "tuning1", "all_max"]
    cell, label, cols = 384, 28, 4
    rows = (len(order) + cols - 1) // cols
    board = Image.new("RGB", (cols * cell, rows * (cell + label)), (15, 19, 26))
    draw = ImageDraw.Draw(board)
    for i, name in enumerate(order):
        row, col = divmod(i, cols)
        path = OUT / ("ordinary128.png" if name == "ordinary128" else f"{name}.png")
        img = Image.open(path).convert("RGBA").resize((cell, cell), Image.Resampling.NEAREST)
        bg = Image.new("RGBA", img.size, (13, 17, 24, 255)); bg.alpha_composite(img)
        x, y = col * cell, row * (cell + label)
        board.paste(bg.convert("RGB"), (x, y + label)); draw.text((x + 7, y + 7), name, fill=(245, 245, 240))
    board.save(VALID / "tiers-dark-3x.png")
    white = Image.new("RGB", board.size, (237, 238, 240)); draww = ImageDraw.Draw(white)
    for i, name in enumerate(order):
        row, col = divmod(i, cols)
        path = OUT / ("ordinary128.png" if name == "ordinary128" else f"{name}.png")
        img = Image.open(path).convert("RGBA").resize((cell, cell), Image.Resampling.NEAREST)
        bg = Image.new("RGBA", img.size, (248, 249, 251, 255)); bg.alpha_composite(img)
        x, y = col * cell, row * (cell + label)
        white.paste(bg.convert("RGB"), (x, y + label)); draww.text((x + 7, y + 7), name, fill=(25, 27, 31))
    white.save(VALID / "tiers-white-3x.png")

    # Current-version component close-ups for human review (never a source asset).
    zoom_rows = [
        ("red", (29, 0, 88, 47), ["ordinary128", "resonance1", "resonance2", "all_max"]),
        ("purple", (89, 37, 128, 80), ["ordinary128", "split1", "split2", "split3"]),
        ("eye", (7, 96, 35, 127), ["ordinary128", "extension1", "extension2", "extension3"]),
    ]
    panel_w, panel_h, zoom_label = 520, 410, 26
    zoom = Image.new("RGB", (panel_w * 4, (panel_h + zoom_label) * len(zoom_rows)), (14, 18, 25))
    zd = ImageDraw.Draw(zoom)
    for row, (component, crop_box, names) in enumerate(zoom_rows):
        for col, name in enumerate(names):
            path = OUT / ("ordinary128.png" if name == "ordinary128" else f"{name}.png")
            im = Image.open(path).convert("RGBA").crop(crop_box)
            scale = max(1, min(10, (panel_w - 18) // im.width, (panel_h - 16) // im.height))
            im = im.resize((im.width * scale, im.height * scale), Image.Resampling.NEAREST)
            tile = Image.new("RGBA", im.size, (9, 13, 19, 255)); tile.alpha_composite(im)
            x, y = col * panel_w, row * (panel_h + zoom_label)
            zoom.paste(tile.convert("RGB"), (x + (panel_w - im.width) // 2, y + zoom_label + (panel_h - im.height) // 2))
            zd.text((x + 7, y + 6), f"{component}: {name}", fill=(240, 241, 244))
    zoom.save(VALID / "component-zoom.png")

    print(json.dumps({"ordinary_sha": sha(ORDINARY_PATH), "anchor_sha": sha(ANCHOR_PATH), "base128_sha": base_hash,
                      "boneCounts": {k: int(v.sum()) for k, v in bone_masks64.items()}, "offsets": manifest["componentAlignment"]["offsetsXY"],
                      "states": {k: {"sha": v["sha256"], "changed": v["changedTexels"]} for k, v in state_records.items()},
                      "moduleMaskCounts": {k: v["count"] for k, v in global_masks.items()},
                      "glowCounts": {k: len(v[next(iter(v))]) for k, v in glow.items()},
                      "stableCounts": {k: len(v[next(iter(v))]) for k, v in stable.items()}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
