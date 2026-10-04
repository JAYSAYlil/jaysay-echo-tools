"""Review-only 0.1.3 repair for the left head tip while resonance is inactive.

The approved 0.1.2 generator remains immutable. This wrapper imports its native
64px composition logic, adds a fixed source-texture patch only to resonance=0
states, and writes an isolated candidate plus compact white/dark review boards.
"""
from __future__ import annotations

import importlib.util
import io
import json
import shutil
import zipfile
from functools import lru_cache
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path(__file__).resolve().parent
VALIDATION = ROOT / "artwork/validation/v0.1.3"
CANDIDATE = VALIDATION / "candidate"
ASSET_ROOT = CANDIDATE / "assets/echopickaxe"
GENERATOR = ROOT / "artwork/source/approved-reference-oct03-64/build_approved64_variants.py"
BASELINE_JAR = ROOT / "jaysay-echo-tools-0.1.2.jar"
BASELINE_SHA256 = "7312AE7B54F3DAD998815B7C7BD601B65DB1BED23A21CC7AA8448E40E082F495"
JAR_PREFIX = "assets/echopickaxe/"

# Pixel-space replacement mask on the 64x64 sprite. Polygon follows the original
# left blade point plus dark support, stopping before the central tuning star.
# Alpha=255 includes transparent source texels, so the prior ghost is erased.
# Every selected pixel is copied from the original 32px texture enlarged 2x NEAREST.
TIP_POLYGON = [(8, 12), (14, 11), (20, 13), (25, 16), (25, 20),
               (21, 24), (14, 25), (9, 22), (7, 17)]
TIP_MASK = Image.new("L", (64, 64), 0)
ImageDraw.Draw(TIP_MASK).polygon(TIP_POLYGON, fill=255)
TIP_COORDS = [(x, y) for y in range(64) for x in range(64) if TIP_MASK.getpixel((x, y))]


@lru_cache(maxsize=None)
def baseline_bytes(relative: str) -> bytes:
    with zipfile.ZipFile(BASELINE_JAR) as jar:
        return jar.read(JAR_PREFIX + relative)


def baseline_image(relative: str) -> Image.Image:
    return Image.open(io.BytesIO(baseline_bytes(relative))).convert("RGBA")


def load_generator():
    spec = importlib.util.spec_from_file_location("approved64_v012", GENERATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load historical generator: {GENERATOR}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Redirect every output into the new 0.1.3 source/validation directories.
    module.SOURCE = SOURCE
    return module


def patch_tip(sprite: Image.Image, ordinary64: Image.Image) -> Image.Image:
    """Copy the complete ordinary tip exactly, including transparent pixels."""
    out = sprite.copy()
    dst, ordinary = out.load(), ordinary64.load()
    for x, y in TIP_COORDS:
        dst[x, y] = ordinary[x, y]
    return out


def copy_tip_glow(strip: Image.Image, base_glow: Image.Image) -> Image.Image:
    out = strip.copy()
    dst = out.load()
    for frame in range(16):
        old_frame = base_glow.crop((0, 32 * frame, 32, 32 * (frame + 1))).resize(
            (64, 64), Image.Resampling.NEAREST
        )
        old = old_frame.load()
        for x, y in TIP_COORDS:
            dst[x, y + 64 * frame] = old[x, y]
    return out


def make_preview(candidate: Path, output: Path, background: tuple[int, int, int]):
    labels = [
        ("ordinary 32px", None),
        ("frequency III only", 24),
        ("tuning I only", 4),
        ("extension III only", 3),
        ("FIII + TI + EIII, R0", 31),
        ("all max, resonance II", 95),
    ]
    old_font = ImageFont.load_default()
    card_w, card_h, pad = 260, 260, 22
    canvas = Image.new("RGB", (3 * card_w + 4 * pad, 820), background)
    draw = ImageDraw.Draw(canvas)
    foreground = (245, 245, 245) if sum(background) < 300 else (25, 25, 25)
    for idx, (label, variant) in enumerate(labels):
        col, row = idx % 3, idx // 3
        x0, y0 = pad + col * card_w, 70 + pad + row * card_h
        draw.text((x0, y0 - 17), label, fill=foreground, font=old_font)
        if variant is None:
            image = baseline_image("textures/item/echo_pickaxe.png")
        elif variant >= 32:
            image = baseline_image(f"textures/item/echo_pickaxe_v{variant:03d}.png")
        else:
            # R0 states come from the fixed candidate; res>=1 is a byte-exact copy
            # of 0.1.2, so the visual is still the approved unchanged full maximum.
            image = Image.open(candidate / "assets/echopickaxe/textures/item" / f"echo_pickaxe_v{variant:03d}.png").convert("RGBA")
        image = image.resize((128, 128), Image.Resampling.NEAREST)
        card = Image.new("RGBA", (128, 128), background + (255,))
        card.alpha_composite(image)
        canvas.paste(card.convert("RGB"), (x0 + 56, y0 + 15))
    # Focused before/after comparison of the fully upgraded non-resonance state.
    y0 = 70 + 2 * pad + 2 * card_h
    draw.text((pad, y0), "res0 tip repair · previous → fixed", fill=foreground, font=old_font)
    for j, (label, image) in enumerate((
        ("previous 0.1.2", baseline_image("textures/item/echo_pickaxe_v031.png")),
        ("fixed 0.1.3", Image.open(candidate / "assets/echopickaxe/textures/item/echo_pickaxe_v031.png").convert("RGBA")),
    )):
        x0 = pad + 320 * j
        draw.text((x0, y0 + 20), label, fill=foreground, font=old_font)
        image = image.resize((128, 128), Image.Resampling.NEAREST)
        card = Image.new("RGBA", (128, 128), background + (255,))
        card.alpha_composite(image)
        canvas.paste(card.convert("RGB"), (x0 + 30, y0 + 38))
    canvas.save(output)


def make_spotlight(candidate: Path, output: Path):
    background = (255, 255, 255)
    labels = ["previous · res0", "fixed · res0", "unchanged · resonance II"]
    images = [
        baseline_image("textures/item/echo_pickaxe_v031.png"),
        Image.open(candidate / "assets/echopickaxe/textures/item/echo_pickaxe_v031.png").convert("RGBA"),
        baseline_image("textures/item/echo_pickaxe_v095.png"),
    ]
    card_w, card_h, pad = 226, 220, 14
    canvas = Image.new("RGB", (3 * card_w + 4 * pad, card_h + 2 * pad), background)
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    for i, (label, image) in enumerate(zip(labels, images)):
        x0 = pad + i * card_w
        draw.text((x0, pad), label, fill=(20, 20, 20), font=font)
        image = image.resize((160, 160), Image.Resampling.NEAREST)
        card = Image.new("RGBA", (160, 160), background + (255,))
        card.alpha_composite(image)
        canvas.paste(card.convert("RGB"), (x0 + 28, pad + 22))
    canvas.save(output)


def main():
    VALIDATION.mkdir(parents=True, exist_ok=True)
    jar_hash = __import__("hashlib").sha256(BASELINE_JAR.read_bytes()).hexdigest().upper()
    if jar_hash != BASELINE_SHA256:
        raise RuntimeError(f"Unexpected 0.1.2 baseline JAR SHA-256: {jar_hash}")
    # Preserve earlier scratch previews outside the focused candidate resource tree.
    if CANDIDATE.exists():
        for name in ("inspect-tip-before.png", "ordinary-tip-grid.png"):
            scratch = CANDIDATE / name
            if scratch.exists():
                destination = VALIDATION / name
                if not destination.exists():
                    shutil.move(str(scratch), str(destination))
    module = load_generator()
    raw, reference, normalized, alpha_stats = module.load_reference()
    tiers, unions, regions = module.feature_masks(normalized)
    mask_coords = set(TIP_COORDS)
    for component, texels in unions.items():
        overlap = mask_coords & texels
        if overlap:
            raise RuntimeError(f"Ordinary tip replacement mask overlaps {component} tier texels: {sorted(overlap)[:8]}")
    base32 = baseline_image("textures/item/echo_pickaxe.png")
    ordinary64 = base32.resize((64, 64), Image.Resampling.NEAREST)
    ordinary_glow = baseline_image("textures/item/echo_pickaxe_glow.png")
    ASSET_ROOT.mkdir(parents=True, exist_ok=True)
    models_dir = ASSET_ROOT / "models/item"
    textures_dir = ASSET_ROOT / "textures/item"
    models_dir.mkdir(parents=True, exist_ok=True)
    textures_dir.mkdir(parents=True, exist_ok=True)

    # Generate only the 31 changed res0 states. All other assets fall back to the
    # unchanged production tree while root reviews these isolated files.
    common = module.common_body(normalized, unions, base32)
    component_union = set().union(*(unions[c] for c in module.COMPONENTS))
    common_emit = module.body_emissive_mask(normalized, component_union)
    module_emit = module.emissive_masks(normalized, tiers)
    source_model = json.loads(baseline_bytes("models/item/echo_pickaxe.json").decode("utf-8"))
    manifest = {"version": "0.1.3-review-only", "baseVersion": "0.1.2", "changedIndices": [],
                "baselineJar": BASELINE_JAR.name, "baselineJarSha256": jar_hash,
                "resonanceLevel": 0, "changedResourcesPerIndex": ["model", "base", "glow"],
                "metadataByteIdentical": True, "ordinaryTipMask": "artwork/validation/v0.1.3/artagentmask.png",
                "assetsRoot": "artwork/validation/v0.1.3/candidate/assets/echopickaxe",
                "formula": "resonance*32+frequency*8+tuning*4+extension", "alphaNormalization": alpha_stats,
                "variants": []}
    for index in range(1, 32):
        levels_tuple = module.levels_for(index)
        levels = dict(zip(module.COMPONENTS, levels_tuple))
        if levels["resonance"] != 0:
            raise AssertionError(f"Unexpected resonance level at index {index}: {levels}")
        sprite = patch_tip(module.state_sprite(normalized, common, tiers, levels), ordinary64)
        glow, lit = module.glow_strip(sprite, normalized, common_emit, module_emit, levels)
        glow = copy_tip_glow(glow, ordinary_glow)
        lit = {(x, y) for y in range(64) for x in range(64) if glow.getpixel((x, y))[3]}
        item = f"echo_pickaxe_v{index:03d}"
        model, opaque, lit_model = module.model_for_state(source_model, item, sprite, lit)
        module.validate_model(sprite, model, lit_model, item)
        sprite_path = textures_dir / f"{item}.png"
        glow_path = textures_dir / f"{item}_glow.png"
        model_path = models_dir / f"{item}.json"
        sprite.save(sprite_path)
        glow.save(glow_path)
        model_path.write_text(json.dumps(model, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        baseline_meta = baseline_bytes(f"textures/item/{item}_glow.png.mcmeta")
        manifest["changedIndices"].append(index)
        manifest["variants"].append({"index": index, "levels": levels, "opaqueTexels": len(opaque),
            "emissiveTexels": len(lit_model), "metadataSource": f"0.1.2 jar:{JAR_PREFIX}textures/item/{item}_glow.png.mcmeta",
            "sha256": {"model": module.sha(model_path.read_bytes()), "base": module.sha(sprite_path.read_bytes()),
                       "glow": module.sha(glow_path.read_bytes()), "metadata": module.sha(baseline_meta)}})
    (CANDIDATE / "tip-repair-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Small six-state board on each background, with old/fixed res0 comparison.
    make_preview(CANDIDATE, VALIDATION / "tip-repair-white.png", (255, 255, 255))
    make_preview(CANDIDATE, VALIDATION / "tip-repair-dark.png", (20, 25, 31))
    make_spotlight(CANDIDATE, VALIDATION / "tip-repair-spotlight.png")
    mask_doc = {
        "version": "0.1.3-review-only",
        "ordinaryTipPatch64Polygon": TIP_POLYGON,
        "ordinaryTipPatch64Texels": len(TIP_COORDS),
        "sourceMapping": "32x32 texture/glow frame to 64x64 with nearest-neighbor 2x; same 16-world-unit sprite plane",
        "boundary": "source mask is binary; selected transparent texels erase prior silhouette; region edge follows the ordinary blade's dark support texels",
        "resonanceGate": "applied only to indices 001..031 (resonance 0); indices 032..095 retain the 0.1.2 red resonance appearances byte-for-byte",
        "tuningStarUntouched": True,
        "candidateChangedIndices": list(range(1, 32)),
        "fallbackUntouchedIndices": list(range(32, 96)),
    }
    (SOURCE / "tip-mask.json").write_text(json.dumps(mask_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (VALIDATION / "tip-repair-mask.json").write_text(json.dumps(mask_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    mask_image = Image.new("RGBA", (64, 64), (255, 255, 255, 0))
    for x, y in TIP_COORDS:
        mask_image.putpixel((x, y), (255, 255, 255, 255))
    mask_image.save(VALIDATION / "artagentmask.png")
    print(f"PASS: review-only candidate at {CANDIDATE}; res0 mask={len(TIP_COORDS)} texels; generated only indices 001..031; indices 032..095 untouched")
    print(f"Previews: {VALIDATION / 'tip-repair-white.png'}; {VALIDATION / 'tip-repair-dark.png'}")


if __name__ == "__main__":
    main()
