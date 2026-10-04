"""Generate all 95 Echo Pickaxe appearance variants from the approved pixel map.

Default output is isolated under artwork/validation/v0.1.0/pickaxe/candidate.
Use --deploy only after the candidate audit has passed and deployment is approved.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import shutil
from pathlib import Path

from PIL import Image

from generate_candidates import (
    BASE_PATH,
    GLOW_PATH,
    PALETTE,
    RES_STUDS,
    FREQ_MARKS,
    TUNING_STAR,
    EXT_RING,
    EXT_CENTER,
    EXT_BONE_CORNERS,
    assert_source_pixels,
    make_base_variant,
    paint_map,
)

ROOT = Path(__file__).resolve().parents[3]
RESOURCES = ROOT / "src/main/resources/assets/echopickaxe"
CANDIDATE = ROOT / "artwork/validation/v0.1.0/pickaxe/candidate"
BASE_MODEL_PATH = RESOURCES / "models/item/echo_pickaxe.json"


def glow_variant(glow: Image.Image, paint: dict[tuple[int, int], tuple[int, int, int]]) -> Image.Image:
    assert glow.width == 32 and glow.height % 32 == 0
    frame_count = glow.height // 32
    out = Image.new("RGBA", glow.size, (0, 0, 0, 0))
    for frame in range(frame_count):
        layer = glow.crop((0, frame * 32, 32, (frame + 1) * 32))
        # Keep the 1.6 fissure animation byte-faithful; only the small new motifs
        # receive a restrained, deterministic brightness breath.
        phase = math.tau * frame / frame_count
        level = 0.92 + 0.08 * math.sin(phase)
        for (x, y), rgb in paint.items():
            shade = tuple(max(1, min(255, round(c * level))) for c in rgb)
            layer.putpixel((x, y), (*shade, 255))
        out.paste(layer, (0, frame * 32))
    return out


def item_model(base_model: dict, item_id: str, paint: dict) -> dict:
    model = copy.deepcopy(base_model)
    model["textures"]["layer0"] = f"echopickaxe:item/{item_id}"
    model["textures"]["glow"] = f"echopickaxe:item/{item_id}_glow"
    found: set[tuple[int, int]] = set()
    for element in model["elements"]:
        x = round(element["from"][0] * 2)
        y = round((16 - element["to"][1]) * 2)
        pos = (x, y)
        if pos not in paint:
            continue
        found.add(pos)
        for side in ("north", "south"):
            face = element["faces"][side]
            face["texture"] = "#glow"
            face["forge_data"] = {
                "block_light": 15,
                "sky_light": 15,
                "ambient_occlusion": False,
            }
    assert found == set(paint), (item_id, "missing pixel boxes", set(paint) - found)
    return model


def rgb_hash(image: Image.Image) -> str:
    return hashlib.sha256(image.tobytes()).hexdigest()


def generate(deploy: bool) -> dict:
    base = Image.open(BASE_PATH).convert("RGBA")
    glow = Image.open(GLOW_PATH).convert("RGBA")
    base_model = json.loads(BASE_MODEL_PATH.read_text(encoding="utf-8"))
    # Re-running after deployment must not propagate the base model's override
    # table into every generated child (which would recurse through 95 models).
    base_model.pop("overrides", None)
    assert base.size == (32, 32)
    opaque = {(x, y) for y in range(32) for x in range(32) if base.getpixel((x, y))[3] == 255}
    original_selected = {
        (round(element["from"][0] * 2), round((16 - element["to"][1]) * 2))
        for element in base_model["elements"]
        if element["faces"]["north"]["texture"] == "#glow"
    }
    assert {p for y in range(glow.height) for x in range(32) if glow.getpixel((x, y))[3] for p in [(x, y % 32)]} == original_selected

    out_models = CANDIDATE / "models/item"
    out_textures = CANDIDATE / "textures/item"
    out_models.mkdir(parents=True, exist_ok=True)
    out_textures.mkdir(parents=True, exist_ok=True)
    # Candidate audit compares the untouched item against the current release
    # baseline, so retain the original three base resources in the isolated set.
    shutil.copy2(BASE_PATH, out_textures / "echo_pickaxe.png")
    shutil.copy2(GLOW_PATH, out_textures / "echo_pickaxe_glow.png")
    shutil.copy2(GLOW_PATH.with_suffix(".png.mcmeta"), out_textures / "echo_pickaxe_glow.png.mcmeta")
    index_overrides = []
    manifest = []
    base_signatures: set[str] = set()
    for resonance in range(3):
        for frequency in range(4):
            for tuning in range(2):
                for extension in range(4):
                    index = resonance * 32 + frequency * 8 + tuning * 4 + extension
                    levels = (resonance, frequency, tuning, extension)
                    paint = paint_map(levels)
                    assert_source_pixels(base, paint)
                    rendered = make_base_variant(base, paint)
                    base_signatures.add(rendered.tobytes())
                    item_id = "echo_pickaxe" if index == 0 else f"echo_pickaxe_v{index:03d}"
                    if index == 0:
                        index_overrides.append(None)
                        continue
                    model = item_model(base_model, item_id, paint)
                    strip = glow_variant(glow, paint)
                    assert {
                        (x, y)
                        for y in range(32)
                        for x in range(32)
                        if strip.getpixel((x, y))[3]
                    } == original_selected | set(paint), (item_id, "emissive pixel mask mismatch")
                    base_file = out_textures / f"{item_id}.png"
                    glow_file = out_textures / f"{item_id}_glow.png"
                    model_file = out_models / f"{item_id}.json"
                    rendered.save(base_file)
                    strip.save(glow_file)
                    shutil.copy2(GLOW_PATH.with_suffix(".png.mcmeta"), glow_file.with_suffix(".png.mcmeta"))
                    model_file.write_text(json.dumps(model, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                    index_overrides.append({
                        "predicate": {"echopickaxe:upgrade_visual": index},
                        "model": f"echopickaxe:item/{item_id}",
                    })
                    manifest.append({
                        "index": index,
                        "levels": list(levels),
                        "model": f"models/item/{item_id}.json",
                        "baseSha256": hashlib.sha256(base_file.read_bytes()).hexdigest(),
                        "glowSha256": hashlib.sha256(glow_file.read_bytes()).hexdigest(),
                        "pixelSha256": rgb_hash(rendered),
                        "changedPixels": len(paint),
                        "emissivePixels": len(original_selected | set(paint)),
                    })
    assert len(manifest) == 95 and len(base_signatures) == 96

    base_with_overrides = copy.deepcopy(base_model)
    base_with_overrides["overrides"] = [v for v in index_overrides if v is not None]
    base_model_file = out_models / "echo_pickaxe.json"
    base_model_file.write_text(json.dumps(base_with_overrides, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    manifest_path = CANDIDATE / "variant-manifest.json"
    manifest_path.write_text(json.dumps({
        "schema": 1,
        "formula": "index = resonance*32 + frequency*8 + tuning*4 + extension",
        "levels": {"resonance": 2, "frequency": 3, "tuning": 1, "extension": 3},
        "baseline": "original 1.6.0 base art and emissive fissure strip; original no-upgrade item remains byte-exact",
        "counts": {"combinationsIncludingBase": 96, "variants": 95, "distinctBaseSprites": len(base_signatures)},
        "variants": manifest,
    }, indent=2) + "\n", encoding="utf-8")

    if deploy:
        deployed = []
        for source in (out_models, out_textures):
            rel = source.relative_to(CANDIDATE)
            target = RESOURCES / rel
            target.mkdir(parents=True, exist_ok=True)
            for file in source.rglob("*"):
                if file.is_file():
                    dest = target / file.relative_to(source)
                    shutil.copy2(file, dest)
                    deployed.append(str(dest.relative_to(RESOURCES)).replace("\\", "/"))
        print(f"DEPLOYED {len(deployed)} generated model/texture files under src/main/resources/assets/echopickaxe")
    print(f"PASS generated {len(manifest)} upgrade variants + base; {len(base_signatures)} unique sprites; max changed={max(v['changedPixels'] for v in manifest)}px")
    print(f"Candidate: {CANDIDATE}")
    return {"variants": len(manifest), "unique": len(base_signatures), "maxChanged": max(v["changedPixels"] for v in manifest)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--deploy", action="store_true", help="copy already-audited output into production resources")
    args = parser.parse_args()
    generate(args.deploy)
