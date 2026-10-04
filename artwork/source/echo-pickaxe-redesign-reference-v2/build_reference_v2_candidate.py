"""Build the frozen 0.1.11 image-one-based native64 upgrade candidate."""
from __future__ import annotations

import copy, hashlib, importlib.util, json, math, shutil, zipfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path(__file__).resolve().parent
DESIGN = ROOT / "artwork/validation/v0.1.11/redesign-v2/base1-tier-design"
RECORD = ROOT / "artwork/validation/v0.1.11/reference-master-final"
PLAIN_MANIFEST = RECORD / "plain-index0-candidate-manifest.json"
PLAIN_CANDIDATE = RECORD / "candidate/plain-index0"
BASELINE = ROOT / "jaysay-echo-tools-0.1.10.jar"
BASELINE_SHA = "24E7807050FDB26C2A1C21F6854E9F391F9DAF42E86DBA8AB05A59D0546D20C0"
BASE = ROOT / "artwork/validation/v0.1.11/redesign-v2/imagegen-v004-derived64.png"
MASTER = SOURCE / "user-reference.png"
TARGET = RECORD / "candidate/complete"
MANIFEST = TARGET / "candidate-manifest.json"
BUILDER_PATH = ROOT / "artwork/source/approved-reference-oct03-64/build_approved64_variants.py"
FRAME_COUNT = 16
FRAME_SIZE = 64
COMPONENTS = ("resonance", "frequency", "tuning", "extension")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def import_builder():
    spec = importlib.util.spec_from_file_location("approved_native64_helpers", BUILDER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def import_composer():
    path = SOURCE / "compose_from_base1_tiers.py"
    spec = importlib.util.spec_from_file_location("base1_tier_composer", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def levels_for(index: int) -> dict[str, int]:
    return {"resonance": index // 32, "frequency": (index % 32) // 8,
            "tuning": (index % 8) // 4, "extension": index % 4}


def connected4(im: Image.Image) -> bool:
    points = {(x, y) for y in range(64) for x in range(64) if im.getpixel((x, y))[3]}
    if not points:
        return False
    seen = {next(iter(points))}
    todo = list(seen)
    while todo:
        x, y = todo.pop()
        for q in ((x-1, y), (x+1, y), (x, y-1), (x, y+1)):
            if q in points and q not in seen:
                seen.add(q)
                todo.append(q)
    return seen == points


def coords(mask: Image.Image) -> set[tuple[int, int]]:
    p = mask.load()
    return {(x, y) for y in range(64) for x in range(64) if p[x, y]}


def select_glow_regions(sprite: Image.Image, levels: dict[str, int], base_cyan: set[tuple[int, int]], masks):
    p = sprite.load()
    regions = {"cyanVeins": set(base_cyan), "redResonance": set(), "purpleFrequency": set(),
               "tuningStar": set(), "greenExtension": set()}
    if levels["resonance"]:
        for y in range(4, 22):
            for x in range(14, 42):
                r, g, b, a = p[x, y]
                if a and r > 80 and r > g * 1.32 and r > b * 1.08:
                    regions["redResonance"].add((x, y))
    if levels["frequency"]:
        for y in range(15, 45):
            for x in range(42, 64):
                r, g, b, a = p[x, y]
                if a and b > 85 and b > r * 1.25 and b > g * 1.05:
                    regions["purpleFrequency"].add((x, y))
    if levels["tuning"]:
        for x, y in masks["star"]:
            r, g, b, a = p[x, y]
            if a and max(r, g, b) >= 145:
                regions["tuningStar"].add((x, y))
    if levels["extension"]:
        for y in range(45, 63):
            for x in range(4, 21):
                r, g, b, a = p[x, y]
                if a and g > 65 and g > r * 1.3 and g > b * 0.88:
                    regions["greenExtension"].add((x, y))
    active = {"cyanVeins": True, "redResonance": levels["resonance"] > 0,
              "purpleFrequency": levels["frequency"] > 0, "tuningStar": levels["tuning"] > 0,
              "greenExtension": levels["extension"] > 0}
    for name, points in regions.items():
        if active[name] and not points:
            raise ValueError(f"index levels {levels}: no glow texels for {name}")
        if not active[name] and points:
            raise ValueError(f"index levels {levels}: inactive {name} must have empty glow region")
    return regions


def make_glow(sprite: Image.Image, regions: dict[str, set[tuple[int, int]]]):
    phases = {"cyanVeins": 0.0, "redResonance": 0.85, "purpleFrequency": 1.7,
              "tuningStar": 2.5, "greenExtension": 3.25}
    phase_for = {}
    for group, points in regions.items():
        for n, xy in enumerate(sorted(points, key=lambda q: (q[1], q[0]))):
            phase_for[xy] = phases[group] + (n % 5) * 0.11
    strip = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE * FRAME_COUNT), (0, 0, 0, 0))
    sp, gp = sprite.load(), strip.load()
    for frame in range(FRAME_COUNT):
        for (x, y), phase in phase_for.items():
            r, g, b, _ = sp[x, y]
            factor = 1.0 + 0.045 * math.sin(math.tau * frame / FRAME_COUNT + phase)
            gp[x, y + frame * FRAME_SIZE] = (round(r * factor), round(g * factor), round(b * factor), 255)
    return strip, set(phase_for)


def save_board(states, output: Path, scale=4, dark=False):
    margin, gap, label, cols = 20, 18, 30, 3
    tile = 64 * scale
    rows = (len(states) + cols - 1) // cols
    width = margin * 2 + cols * tile + (cols - 1) * gap
    height = margin * 2 + rows * (label + tile + gap)
    bg = (23, 28, 34) if dark else (250, 250, 248)
    fg = (239, 243, 247) if dark else (28, 33, 37)
    out = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(out)
    fontpath = Path("C:/Windows/Fonts/msyh.ttc")
    font = ImageFont.truetype(fontpath, 19) if fontpath.exists() else ImageFont.load_default()
    for i, (name, sprite) in enumerate(states):
        row, col = divmod(i, cols)
        x, y = margin + col * (tile + gap), margin + row * (label + tile + gap)
        draw.text((x, y), name, font=font, fill=fg)
        shown = sprite.resize((tile, tile), Image.Resampling.NEAREST)
        tileimg = Image.new("RGBA", shown.size, (*bg, 255))
        tileimg.alpha_composite(shown)
        out.paste(tileimg.convert("RGB"), (x, y + label))
    out.save(output)


def render_all95(states):
    output = RECORD / "all-95-upgrade-states-thumbnails.png"
    bg = (248, 248, 245)
    cell_w, cell_h, margin, cols = 112, 116, 16, 8
    out = Image.new("RGB", (margin * 2 + cols * cell_w, margin * 2 + 12 * cell_h), bg)
    draw = ImageDraw.Draw(out)
    fontpath = Path("C:/Windows/Fonts/arial.ttf")
    font = ImageFont.truetype(fontpath, 12) if fontpath.exists() else ImageFont.load_default()
    for index in range(1, 96):
        sprite = states[index]
        col, row = (index - 1) % cols, (index - 1) // cols
        x, y = margin + col * cell_w, margin + row * cell_h
        thumb = sprite.resize((64, 64), Image.Resampling.NEAREST)
        tile = Image.new("RGBA", thumb.size, (*bg, 255)); tile.alpha_composite(thumb)
        out.paste(tile.convert("RGB"), (x + 22, y))
        lv = levels_for(index)
        draw.text((x + 4, y + 68), f"{index:03d}  R{lv['resonance']} F{lv['frequency']} T{lv['tuning']} E{lv['extension']}",
                  font=font, fill=(30, 35, 40))
    out.save(output)
    return output


def make_gif(sprite: Image.Image, glow: Image.Image, output: Path):
    frames = []
    for frame in range(FRAME_COUNT):
        canvas = Image.new("RGBA", (64, 64), (255, 255, 255, 255))
        canvas.alpha_composite(sprite)
        fg = glow.crop((0, frame * 64, 64, (frame + 1) * 64))
        # The model's front face samples glow in place of the base material.
        lit = fg.getchannel("A")
        canvas.paste(fg, (0, 0), lit)
        frames.append(canvas.resize((256, 256), Image.Resampling.NEAREST).convert("P", palette=Image.Palette.ADAPTIVE))
    frames[0].save(output, save_all=True, append_images=frames[1:], duration=125, loop=0, optimize=False)


def main():
    helper = import_builder()
    composer = import_composer()
    base = Image.open(BASE).convert("RGBA")
    master = Image.open(MASTER).convert("RGBA")
    tiers, _, _ = helper.feature_masks(master)
    masks = {"star": coords(tiers["tuning"][0])}
    plain_manifest = json.loads(PLAIN_MANIFEST.read_text(encoding="utf-8"))
    # The index-zero glow footprint is already approved and deployed. It anchors
    # the common native64 emissive vein map for all upgraded states.
    base_cyan = {tuple(p) for p in plain_manifest["plainGlowMask"]["pixels"]}
    TARGET.mkdir(parents=True, exist_ok=True)
    resources_dir = TARGET / "assets"
    if resources_dir.exists():
        shutil.rmtree(resources_dir)
    shutil.copytree(PLAIN_CANDIDATE / "assets", resources_dir)

    old_models = {}
    rows = [dict(row) for row in plain_manifest["resourceRows"]]
    variants = {"0": {"base": "assets/echopickaxe/textures/item/echo_pickaxe.png",
                      "glow": "assets/echopickaxe/textures/item/echo_pickaxe_glow.png",
                      "model": "assets/echopickaxe/models/item/echo_pickaxe.json",
                      "glowMetadata": "assets/echopickaxe/textures/item/echo_pickaxe_glow.png.mcmeta",
                      "glowRegions": {"cyanVeins": plain_manifest["plainGlowMask"]["pixels"],
                                      "redResonance": [], "purpleFrequency": [], "tuningStar": [], "greenExtension": []}}}
    images = {0: base.copy()}; glows = {}
    with zipfile.ZipFile(BASELINE) as jar:
        for index in range(1, 96):
            level = levels_for(index)
            sprite = composer.compose(base.copy(), master, level, masks["star"])
            if not connected4(sprite):
                raise RuntimeError(f"v{index:03d}: disconnected alpha in composed sprite")
            regions = select_glow_regions(sprite, level, base_cyan, masks)
            glow, lit = make_glow(sprite, regions)
            item_id = f"echo_pickaxe_v{index:03d}"
            stem = f"echo_pickaxe_v{index:03d}"
            base_rel = f"assets/echopickaxe/textures/item/{stem}.png"
            glow_rel = f"assets/echopickaxe/textures/item/{stem}_glow.png"
            model_rel = f"assets/echopickaxe/models/item/{stem}.json"
            old_base = jar.read(base_rel); old_glow = jar.read(glow_rel); old_model = jar.read(model_rel)
            source_model = json.loads(old_model)
            model, _, model_lit = helper.model_for_state(source_model, item_id, sprite, lit)
            helper.validate_model(sprite, model, model_lit, item_id)
            payloads = {
                base_rel: (sprite, "base", base_rel, old_base),
                glow_rel: (glow, "glow", glow_rel, old_glow),
                model_rel: (json.dumps(model, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), "model", model_rel, old_model),
            }
            for rel, (value, kind, _, old_bytes) in payloads.items():
                data = value if isinstance(value, bytes) else _png_bytes(value)
                dest = TARGET.joinpath(*rel.split("/")); dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes(data)
                rows.append({"index": index, "kind": kind, "path": rel, "sha256": sha(data),
                             "bytes": len(data), "baselineSha256": sha(old_bytes), "changed": data != old_bytes})
            variants[str(index)] = {"base": base_rel, "glow": glow_rel, "model": model_rel,
                                    "glowRegions": {name: [list(p) for p in sorted(points, key=lambda q:(q[1],q[0]))]
                                                    for name, points in regions.items()}}
            images[index] = sprite; glows[index] = glow
    # Make index-zero preview compositing use its already deployed real resources.
    zero_glow_path = PLAIN_CANDIDATE / "assets/echopickaxe/textures/item/echo_pickaxe_glow.png"
    glows[0] = Image.open(zero_glow_path).convert("RGBA")
    manifest = {
        "schemaVersion": 1, "status": "frozen", "version": "0.1.11",
        "baseline": {"jar": "jaysay-echo-tools-0.1.10.jar", "sha256": BASELINE_SHA},
        "plainAnchor": {"path": "artwork/validation/v0.1.11/redesign-v2/imagegen-v004-derived64.png",
                        "sha256": sha(BASE.read_bytes()), "index": 0, "pixelExact": True},
        "fullmaxVisualTarget": {"path": "artwork/source/echo-pickaxe-redesign-reference-v2/user-reference.png",
                                "sha256": sha(MASTER.read_bytes()), "index": 95, "pixelExact": False},
        "candidateMode": "overlay",
        "geometry": {"pixelUnit": 0.25, "z": [7.5, 8.5], "modelCoverage": "exact", "preserveBaseModelOverrides": True},
        "glowContract": {"frames": 16, "frameSize": 64, "fixedAlpha": True, "brightnessTolerance": 0.06,
                         "channelFloorTolerance": 4, "frameTime": 3, "interpolate": True},
        "resourceRows": rows, "variants": variants,
        "plainDesign": "ordinary回响镐：imagegen-v004-derived64 selected image, pixel exact; source proof and four deployed resources are pinned.",
        "fullmaxDesign": "全部满级：image-one shared body with image-two component facets as visual reference; not pixel exact to image two."
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # Chinese user-facing level board: no debug-only vNNN labels.
    showcase = [("普通回响镐", images[0]), ("调谐 I", images[4]), ("分频 I", images[8]),
                ("共振 I", images[32]), ("延展 I", images[1]), ("全部满级", images[95])]
    save_board(showcase, RECORD / "reference-v2-six-states-white.png", dark=False)
    save_board(showcase, RECORD / "reference-v2-six-states-dark.png", dark=True)
    render_all95(images)
    # Fullmax preview uses actual model face material replacement via the glow strip.
    make_gif(images[95], glows[95], RECORD / "reference-v2-fullmax-16frames.gif")
    print(f"candidate: {TARGET}")
    print(f"manifest: {MANIFEST}")
    print(f"rows={len(rows)} variants={len(variants)} states={len(images)}")
    print(f"ordinary selected exact SHA: {manifest['plainAnchor']['sha256']}")
    print(f"fullmax design SHA: {sha(_png_bytes(images[95]))}")


def _png_bytes(im: Image.Image) -> bytes:
    import io
    stream = io.BytesIO()
    im.save(stream, format="PNG", optimize=False)
    return stream.getvalue()


if __name__ == "__main__":
    main()
