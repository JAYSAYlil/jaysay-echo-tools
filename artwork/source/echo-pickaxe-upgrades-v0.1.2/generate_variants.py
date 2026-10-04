"""Generate 95 isolated TConstruct-2-inspired Echo Pickaxe variants."""
from __future__ import annotations

import copy
import hashlib
import json
import math
import shutil
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path(__file__).resolve().parent
MAP_PATH = SOURCE / "native-pixel-map.json"
BASE_PATH = ROOT / "src/main/resources/assets/echopickaxe/textures/item/echo_pickaxe.png"
GLOW_PATH = ROOT / "src/main/resources/assets/echopickaxe/textures/item/echo_pickaxe_glow.png"
META_PATH = GLOW_PATH.with_suffix(".png.mcmeta")
MODEL_PATH = ROOT / "src/main/resources/assets/echopickaxe/models/item/echo_pickaxe.json"
OUT = ROOT / "artwork/validation/v0.1.2/pickaxe/candidate"
COMPONENTS = ("resonance", "frequency", "tuning", "extension")
LEVEL_LIMITS = (2, 3, 1, 3)
LIGHT = {"block_light": 15, "sky_light": 15, "ambient_occlusion": False}
ALPHA_NEIGHBORS = ((-1, 0), (1, 0), (0, -1), (0, 1))
SIDES = {"west": (-1, 0), "east": (1, 0), "up": (0, -1), "down": (0, 1)}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_inputs():
    data = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    base = Image.open(BASE_PATH).convert("RGBA")
    glow = Image.open(GLOW_PATH).convert("RGBA")
    meta = META_PATH.read_bytes()
    model = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    if base.size != (32, 32) or glow.size != (32, 512):
        raise ValueError(f"Unexpected source dimensions: base={base.size}, glow={glow.size}")
    if set(base.getchannel("A").getdata()) != {0, 255}:
        raise ValueError("Original source alpha must be binary")
    return data, base, glow, meta, model


def map_pixels(data: dict, levels: tuple[int, int, int, int]):
    """Return latest material assignment per native texel, tier order included."""
    paints: dict[tuple[int, int], tuple[str, str]] = {}
    for component, level in zip(COMPONENTS, levels):
        spec = data["components"][component]
        if not 0 <= level <= spec["maxLevel"]:
            raise ValueError(f"Out-of-range level for {component}: {level}")
        for tier in range(1, level + 1):
            for x, y, material in spec["tiers"][str(tier)]:
                pos = (x, y)
                if pos in paints and paints[pos][0] != component:
                    raise ValueError(f"Cross-component pixel overlap at {pos}")
                paints[pos] = (component, material)
    return paints


def validate_map(data: dict, base: Image.Image, source_model: dict):
    if set(data["components"]) != set(COMPONENTS):
        raise ValueError("Map must describe exactly the four existing modules")
    original = {(x, y) for y in range(32) for x in range(32) if base.getpixel((x, y))[3]}
    masks: dict[str, set[tuple[int, int]]] = {}
    added_by_module: dict[str, set[tuple[int, int]]] = {}
    used = set()
    for component, maximum in zip(COMPONENTS, LEVEL_LIMITS):
        spec = data["components"][component]
        if spec["maxLevel"] != maximum:
            raise ValueError(f"Incorrect maximum level for {component}")
        module_mask: set[tuple[int, int]] = set()
        module_added: set[tuple[int, int]] = set()
        for tier in range(1, maximum + 1):
            entries = spec["tiers"][str(tier)]
            if not entries:
                raise ValueError(f"Missing {component} tier {tier}")
            tier_emissive = False
            for x, y, material in entries:
                pos = (x, y)
                if not (0 <= x < 32 and 1 <= y <= 30):
                    raise ValueError(f"Mapped texel outside allowed canvas: {component} {tier} {pos}")
                if material not in data["palette"]:
                    raise ValueError(f"Unknown palette material {material}")
                if pos in used and pos not in module_mask:
                    raise ValueError(f"Module masks overlap at {pos}")
                module_mask.add(pos)
                if pos not in original:
                    module_added.add(pos)
                tier_emissive |= data["palette"][material]["emissive"]
            if not tier_emissive:
                raise ValueError(f"{component} tier {tier} has no independent emissive facet")
        added_by_module[component] = module_added
        masks[component] = module_mask
        used |= module_mask

    added = set().union(*added_by_module.values())
    if len(added) > 11:
        raise ValueError(f"Approved silhouette expansion is limited to 11 texels, got {len(added)}")
    for x, y in added:
        if not (1 <= x <= 30 and 1 <= y <= 30):
            raise ValueError(f"Added silhouette texel reaches image border: {(x, y)}")
        if not any((x + dx, y + dy) in original for dx, dy in ALPHA_NEIGHBORS):
            raise ValueError(f"Added silhouette texel must touch original alpha: {(x, y)}")

    for i, component in enumerate(COMPONENTS):
        for other in COMPONENTS[i + 1:]:
            if masks[component] & masks[other]:
                raise ValueError(f"Module masks overlap: {component}/{other}")

    if source_model.get("gui_light") != "front" or source_model.get("ambientocclusion") is not False:
        raise ValueError("Source model lighting/AO contract changed")
    if not source_model.get("display"):
        raise ValueError("Source model display transforms missing")
    return original, masks, added_by_module


def source_frames(glow: Image.Image):
    return [glow.crop((0, frame * 32, 32, (frame + 1) * 32)) for frame in range(16)]


def render_variant(data, base, glow, levels):
    paints = map_pixels(data, levels)
    sprite = base.copy()
    frames = source_frames(glow)
    for (x, y), (_, material) in paints.items():
        color = data["palette"][material]
        sprite.putpixel((x, y), (*color["rgb"], 255))
        for frame, layer in enumerate(frames):
            if color["emissive"]:
                phase = math.tau * frame / 16
                brightness = 0.82 + 0.18 * (0.5 + 0.5 * math.sin(phase))
                rgb = tuple(max(1, min(255, round(c * brightness))) for c in color["rgb"])
                layer.putpixel((x, y), (*rgb, 255))
            else:
                layer.putpixel((x, y), (0, 0, 0, 0))
    strip = Image.new("RGBA", (32, 512), (0, 0, 0, 0))
    for frame, layer in enumerate(frames):
        strip.paste(layer, (0, frame * 32))
    return sprite, strip, paints


def model_for_state(source_model, item_id, sprite, paints, base, original_glow_mask):
    """Rebuild every one-pixel box from output alpha so new exposed sides are exact."""
    model = copy.deepcopy(source_model)
    model.pop("parent", None)
    model.pop("overrides", None)
    model["gui_light"] = "front"
    model["ambientocclusion"] = False
    model["textures"] = {
        "layer0": f"echopickaxe:item/{item_id}",
        "glow": f"echopickaxe:item/{item_id}_glow",
        "particle": "#layer0",
    }
    opaque = {(x, y) for y in range(32) for x in range(32) if sprite.getpixel((x, y))[3]}
    original_opaque = {(x, y) for y in range(32) for x in range(32) if base.getpixel((x, y))[3]}
    added = opaque - original_opaque
    elements = []
    lit = set()
    for x, y in sorted(opaque, key=lambda p: (p[1], p[0])):
        material = paints.get((x, y), (None, None))[1]
        emissive = material.endswith("_glow") if material else (x, y) in original_glow_mask
        if emissive:
            lit.add((x, y))
        uv = [x / 2 + 0.25, y / 2 + 0.25, x / 2 + 0.25, y / 2 + 0.25]
        faces = {}
        for side in ("north", "south"):
            face = {"uv": uv.copy(), "texture": "#glow" if emissive else "#layer0"}
            if emissive:
                face["forge_data"] = copy.deepcopy(LIGHT)
            faces[side] = face
        for side, (dx, dy) in SIDES.items():
            if (x + dx, y + dy) not in opaque:
                faces[side] = {"uv": uv.copy(), "texture": "#layer0"}
        elements.append({
            "from": [x / 2, 16 - (y + 1) / 2, 7.5],
            "to": [(x + 1) / 2, 16 - y / 2, 8.5],
            "shade": False,
            "faces": faces,
        })
    model["elements"] = elements
    return model, opaque, lit


def validate_generated(data, base, source_glow, sprite, strip, model, paints, opaque, lit, item_id):
    """Check rebuilt pixel mesh, UV centers, glow face binding, and fissure preservation."""
    source_frames = globals()["source_frames"](source_glow)
    if not {(x, y) for y in range(32) for x in range(32) if sprite.getpixel((x, y))[3]} == opaque:
        raise ValueError(f"{item_id}: sprite alpha and generated model alpha disagree")
    model_pixels = set()
    expected_uv = {}
    for element in model["elements"]:
        x = round(element["from"][0] * 2)
        y = round((16 - element["to"][1]) * 2)
        pos = (x, y)
        if pos in model_pixels or pos not in opaque:
            raise ValueError(f"{item_id}: duplicate/missing geometry at {pos}")
        model_pixels.add(pos)
        if element["from"] != [x / 2, 16 - (y + 1) / 2, 7.5] or element["to"] != [(x + 1) / 2, 16 - y / 2, 8.5]:
            raise ValueError(f"{item_id}: incorrect half-unit texel prism at {pos}")
        uv = [x / 2 + 0.25, y / 2 + 0.25, x / 2 + 0.25, y / 2 + 0.25]
        required = {"north", "south"} | {d for d, (dx, dy) in SIDES.items() if (x + dx, y + dy) not in opaque}
        faces = element["faces"]
        if set(faces) != required:
            raise ValueError(f"{item_id}: exposed-wall set incorrect at {pos}")
        if faces["north"]["texture"] != faces["south"]["texture"]:
            raise ValueError(f"{item_id}: front/back texture mismatch at {pos}")
        for direction, face in faces.items():
            if face["uv"] != uv:
                raise ValueError(f"{item_id}: non-center UV at {pos} {direction}")
            if face["texture"] == "#glow":
                if direction not in ("north", "south") or face.get("forge_data") != LIGHT:
                    raise ValueError(f"{item_id}: glow face has incorrect lighting contract at {pos}")
            elif face["texture"] != "#layer0" or "forge_data" in face:
                raise ValueError(f"{item_id}: non-glow face carries emissive data at {pos}")
    if model_pixels != opaque:
        raise ValueError(f"{item_id}: model omits alpha pixels")
    model_lit = {(round(e["from"][0] * 2), round((16 - e["to"][1]) * 2))
                 for e in model["elements"] if e["faces"]["north"]["texture"] == "#glow"}
    if model_lit != lit:
        raise ValueError(f"{item_id}: glow map and model glow faces differ")
    animated_colors = {p: set() for p in lit & set(paints)}
    for frame in range(16):
        layer = strip.crop((0, frame * 32, 32, (frame + 1) * 32))
        frame_lit = {(x, y) for y in range(32) for x in range(32) if layer.getpixel((x, y))[3]}
        if frame_lit != lit:
            raise ValueError(f"{item_id}: glow alpha topology changed at animation frame {frame}")
        for y in range(32):
            for x in range(32):
                if (x, y) not in paints and layer.getpixel((x, y)) != source_frames[frame].getpixel((x, y)):
                    raise ValueError(f"{item_id}: original fissure frame changed outside modules at {(x, y)}")
        for p in animated_colors:
            animated_colors[p].add(layer.getpixel(p)[:3])
    if not animated_colors or not any(len(colors) > 1 for colors in animated_colors.values()):
        raise ValueError(f"{item_id}: no changed module highlight animates")


def main():
    data, base, glow, meta, source_model = load_inputs()
    original, module_masks, added_by_module = validate_map(data, base, source_model)
    original_glow_mask = {(x, y) for y in range(32) for x in range(32) if glow.getpixel((x, y))[3]}
    safe_parent = (ROOT / "artwork/validation/v0.1.2/pickaxe").resolve()
    out = OUT.resolve()
    if out != (safe_parent / "candidate").resolve() or safe_parent not in out.parents:
        raise RuntimeError(f"Refusing unexpected output path: {out}")
    if OUT.exists():
        shutil.rmtree(OUT)
    models_out, textures_out = OUT / "models/item", OUT / "textures/item"
    models_out.mkdir(parents=True)
    textures_out.mkdir(parents=True)

    # Keep base item assets byte-identical; only the candidate base model receives overrides.
    shutil.copy2(BASE_PATH, textures_out / "echo_pickaxe.png")
    shutil.copy2(GLOW_PATH, textures_out / "echo_pickaxe_glow.png")
    (textures_out / "echo_pickaxe_glow.png.mcmeta").write_bytes(meta)

    overrides, records = [], []
    large = {base.tobytes()}
    small = {base.resize((16, 16), Image.Resampling.NEAREST).tobytes()}
    grid_values = {}
    for resonance in range(3):
        for frequency in range(4):
            for tuning in range(2):
                for extension in range(4):
                    levels = (resonance, frequency, tuning, extension)
                    index = resonance * 32 + frequency * 8 + tuning * 4 + extension
                    grid_values[index] = levels
                    sprite, strip, paints = render_variant(data, base, glow, levels)
                    large.add(sprite.tobytes())
                    small.add(sprite.resize((16, 16), Image.Resampling.NEAREST).tobytes())
                    if index == 0:
                        continue
                    item_id = f"echo_pickaxe_v{index:03d}"
                    model, opaque, lit = model_for_state(source_model, item_id, sprite, paints, base, original_glow_mask)
                    model_path = models_out / f"{item_id}.json"
                    sprite_path = textures_out / f"{item_id}.png"
                    glow_path = textures_out / f"{item_id}_glow.png"
                    meta_path = glow_path.with_suffix(".png.mcmeta")
                    sprite.save(sprite_path)
                    strip.save(glow_path)
                    meta_path.write_bytes(meta)
                    model_path.write_text(json.dumps(model, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                    overrides.append({"predicate": {"echopickaxe:upgrade_visual": index}, "model": f"echopickaxe:item/{item_id}"})
                    records.append({
                        "index": index, "levels": {c: n for c, n in zip(COMPONENTS, levels)},
                        "changedPixels": len(paints), "addedAlphaPixels": len(opaque - original),
                        "emissivePixels": len(lit),
                        "sha256": {"model": sha256_bytes(model_path.read_bytes()),
                                   "sprite": sha256_bytes(sprite_path.read_bytes()),
                                   "glow": sha256_bytes(glow_path.read_bytes()),
                                   "meta": sha256_bytes(meta_path.read_bytes())},
                    })
    if (len(large), len(small)) != (96, 96):
        raise ValueError(f"Expected 96 unique full-size and 16px sprites, got {len(large)}/{len(small)}")
    base_model = copy.deepcopy(source_model)
    base_model["overrides"] = overrides
    (models_out / "echo_pickaxe.json").write_text(json.dumps(base_model, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    manifest = {
        "schema": 4, "version": "0.1.2", "reviewOnly": True,
        "formula": "index=resonance*32+frequency*8+tuning*4+extension",
        "variantCount": 95, "combinationsIncludingBase": 96,
        "unique32px": len(large), "unique16pxNearest": len(small),
        "sourceTexture": "src/main/resources/assets/echopickaxe/textures/item/echo_pickaxe.png (untouched baseline)",
        "styleReference": "Official Tinkers Construct 2 / Minecraft 1.12 overlays; material placement principles only, no copied pixels.",
        "nativeMap": "artwork/source/echo-pickaxe-upgrades-v0.1.2/native-pixel-map.json",
        "moduleMasks": {c: len(m) for c, m in module_masks.items()},
        "addedAlphaByModule": {c: sorted([list(p) for p in m]) for c, m in added_by_module.items()},
        "maxAddedAlpha": max(r["addedAlphaPixels"] for r in records),
        "animation": {"frames": 16, "ticksPerFrame": 3, "interpolate": True,
                      "modulePulse": "0.82 + 0.18 * (0.5 + 0.5*sin(2*pi*frame/16))"},
        "baseSha256": sha256_bytes(BASE_PATH.read_bytes()),
        "originalGlowMetaSha256": sha256_bytes(meta),
        "variants": records,
    }
    (OUT / "variant-manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with (OUT / "variant-sha256.csv").open("w", encoding="utf-8", newline="") as f:
        f.write("index,levels,model_sha256,sprite_sha256,glow_sha256,meta_sha256\n")
        for r in records:
            lv = r["levels"]
            f.write(f"{r['index']},R{lv['resonance']}-F{lv['frequency']}-T{lv['tuning']}-E{lv['extension']},"
                    f"{r['sha256']['model']},{r['sha256']['sprite']},{r['sha256']['glow']},{r['sha256']['meta']}\n")
    print(f"PASS 95 variants; 96 distinct at 32px and 16px; max added alpha={manifest['maxAddedAlpha']}; masks={manifest['moduleMasks']}")
    print(f"Candidate only: {OUT}")


if __name__ == "__main__":
    main()
