"""Render all 96 variant states and comparison previews from candidate assets."""
from __future__ import annotations

import hashlib
import io
import json
import math
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path(__file__).resolve().parent
OUT = ROOT / "artwork/validation/v0.1.2/pickaxe/candidate"
TEXTURES = OUT / "textures/item"
OLD_JAR = ROOT / "jaysay-echo-tools-0.1.1.jar"
PREFIX = "assets/echopickaxe/textures/item/"
NAMES = ("R", "F", "T", "E")
LEVEL_MAX = (2, 3, 1, 3)


def font(size=10):
    for path in ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/segoeui.ttf"):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def levels_for(index):
    return (index // 32, (index % 32) // 8, (index % 8) // 4, index % 4)


def get_sprite(index):
    name = "echo_pickaxe.png" if index == 0 else f"echo_pickaxe_v{index:03d}.png"
    return Image.open(TEXTURES / name).convert("RGBA")


def caption(index):
    r, f, t, e = levels_for(index)
    return f"{index:03d} R{r}F{f}T{t}E{e}"


def all_states_board(background, scale, filename):
    cols, rows = 12, 8
    card_w, card_h = 88, 82
    margin = 10
    board = Image.new("RGB", (margin * 2 + cols * card_w, margin * 2 + rows * card_h), background)
    draw = ImageDraw.Draw(board)
    fg = (28, 34, 39) if sum(background) > 400 else (235, 239, 244)
    for index in range(96):
        col, row = index % cols, index // cols
        x, y = margin + col * card_w, margin + row * card_h
        sprite = get_sprite(index).resize((32 * scale, 32 * scale), Image.Resampling.NEAREST)
        draw.text((x + 2, y + 1), caption(index), fill=fg, font=font(9))
        tile = Image.new("RGBA", sprite.size, (*background, 255))
        tile.alpha_composite(sprite)
        board.paste(tile.convert("RGB"), (x + (card_w - sprite.width) // 2, y + 13))
    board.save(OUT / filename)


def old_new_comparison(background, filename):
    with zipfile.ZipFile(OLD_JAR) as jar:
        old_bytes = jar.read(PREFIX + "echo_pickaxe_v095.png")
        old_glow_bytes = jar.read(PREFIX + "echo_pickaxe_v095_glow.png")
    old = Image.open(io.BytesIO(old_bytes)).convert("RGBA")
    old_glow = Image.open(io.BytesIO(old_glow_bytes)).convert("RGBA").crop((0, 0, 32, 32))
    old.alpha_composite(old_glow)
    new = get_sprite(95)
    new_glow = Image.open(TEXTURES / "echo_pickaxe_v095_glow.png").convert("RGBA").crop((0, 0, 32, 32))
    new.alpha_composite(new_glow)
    tile_size, scale = (640, 400), 10
    board = Image.new("RGB", (tile_size[0] + 80, tile_size[1] + 88), background)
    draw = ImageDraw.Draw(board)
    fg = (28, 34, 39) if sum(background) > 400 else (235, 239, 244)
    draw.text((24, 18), "Previous (0.1.1) · all maximum", fill=fg, font=font(20))
    draw.text((360, 18), "Candidate (0.1.2) · all maximum", fill=fg, font=font(20))
    for im, x in ((old, 48), (new, 368)):
        scaled = im.resize((32 * scale, 32 * scale), Image.Resampling.NEAREST)
        tile = Image.new("RGBA", scaled.size, (*background, 255))
        tile.alpha_composite(scaled)
        board.paste(tile.convert("RGB"), (x, 58))
    board.save(OUT / filename)


def full_animation_gif():
    base = get_sprite(95)
    strip = Image.open(TEXTURES / "echo_pickaxe_v095_glow.png").convert("RGBA")
    if strip.size != (32, 512):
        raise ValueError(f"Unexpected candidate glow strip size {strip.size}")
    frames = [strip.crop((0, i * 32, 32, (i + 1) * 32)) for i in range(16)]
    samples = []
    for t in range(96):
        pos = (t / 3.0) % 16
        i0 = int(pos) % 16
        i1 = (i0 + 1) % 16
        layer = Image.blend(frames[i0], frames[i1], pos - int(pos))
        composed = base.copy()
        composed.alpha_composite(layer)
        bg = Image.new("RGBA", (32, 32), (20, 25, 31, 255))
        bg.alpha_composite(composed)
        samples.append(bg.resize((256, 256), Image.Resampling.NEAREST).convert("RGB"))
    samples[0].save(OUT / "full-upgrade-96tick-two-cycle-animation.gif", save_all=True,
                    append_images=samples[1:], duration=50, loop=0, disposal=2, optimize=False)


def main():
    if not (OUT / "variant-manifest.json").exists():
        raise FileNotFoundError("Run generate_variants.py first")
    manifest = json.loads((OUT / "variant-manifest.json").read_text(encoding="utf-8"))
    if manifest["variantCount"] != 95 or manifest["combinationsIncludingBase"] != 96:
        raise ValueError("Candidate manifest does not describe the full 96-state set")
    all_states_board((255, 255, 255), 2, "all-96-combinations-white-32px.png")
    all_states_board((20, 25, 31), 2, "all-96-combinations-dark-32px.png")
    all_states_board((255, 255, 255), 1, "all-96-combinations-inventory-16px.png")
    old_new_comparison((255, 255, 255), "previous-0.1.1-vs-full-upgrade-white.png")
    old_new_comparison((20, 25, 31), "previous-0.1.1-vs-full-upgrade-dark.png")
    full_animation_gif()
    record = {
        "reviewOnly": True,
        "source": "candidate/models and textures; no separate postprocessed preview map",
        "stateCount": 96,
        "unique32px": manifest["unique32px"],
        "unique16pxNearest": manifest["unique16pxNearest"],
        "animation": {"frames": 96, "frameDurationMs": 50, "cycles": 2,
                      "sourceTimeline": "16 frames × 3 ticks with interpolation"},
        "previews": ["all-96-combinations-white-32px.png", "all-96-combinations-dark-32px.png",
                     "all-96-combinations-inventory-16px.png", "previous-0.1.1-vs-full-upgrade-white.png",
                     "previous-0.1.1-vs-full-upgrade-dark.png", "full-upgrade-96tick-two-cycle-animation.gif"],
    }
    (OUT / "preview-record.json").write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("PASS all 96 states rendered at 32px and 16px; 0.1.1 comparison and 96×50ms two-cycle GIF saved.")
    print(f"Candidate previews: {OUT}")


if __name__ == "__main__":
    main()
