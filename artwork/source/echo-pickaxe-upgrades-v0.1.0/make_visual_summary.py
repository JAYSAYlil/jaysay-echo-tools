"""Compose a compact, faithful animation preview from shipped item assets.

This is a read-only presentation helper. It reads production PNG/MCmeta data,
does not recolor or enlarge emission, and does not modify game resources.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
ASSETS = ROOT / "src/main/resources/assets/echopickaxe/textures/item"
OUT = ROOT / "artwork/validation/v0.1.0/visual-summary.gif"
ITEMS = [
    ("Tuning crystal", "tuning_crystal"),
    ("Extension crystal III", "enhanced_extension_crystal_2"),
    ("Fully upgraded pickaxe", "echo_pickaxe_v095"),
]
SCALE = 8
CELL_W = 272
CANVAS_H = 336


def font(size: int):
    for path in ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/segoeui.ttf"):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def load_animation(item_id: str):
    base_path = ASSETS / f"{item_id}.png"
    glow_path = ASSETS / f"{item_id}_glow.png"
    metadata = json.loads(glow_path.with_suffix(".png.mcmeta").read_text(encoding="utf-8"))["animation"]
    strip = Image.open(glow_path).convert("RGBA")
    base = Image.open(base_path).convert("RGBA")
    size = (metadata.get("width", 32), metadata.get("height", 32))
    assert size == (32, 32) and base.size == size and strip.width == 32 and strip.height % 32 == 0
    frame_count = strip.height // 32
    default_time = int(metadata.get("frametime", 1))
    frames = metadata.get("frames", list(range(frame_count)))
    sequence: list[tuple[Image.Image, int]] = []
    for entry in frames:
        if isinstance(entry, int):
            index, ticks = entry, default_time
        else:
            index, ticks = int(entry["index"]), int(entry.get("time", default_time))
        if not (0 <= index < frame_count and ticks > 0):
            raise ValueError(f"Invalid frame metadata for {item_id}: {entry}")
        sequence.append((strip.crop((0, index * 32, 32, (index + 1) * 32)), ticks))
    period = sum(ticks for _, ticks in sequence)
    return base, sequence, period, bool(metadata.get("interpolate", False))


def frame_at(sequence, period: int, interpolate: bool, tick: int) -> Image.Image:
    local_tick = tick % period
    elapsed = 0
    for index, (image, duration) in enumerate(sequence):
        if local_tick < elapsed + duration:
            if not interpolate or len(sequence) < 2:
                return image
            next_image = sequence[(index + 1) % len(sequence)][0]
            alpha = (local_tick - elapsed) / duration
            return Image.blend(image, next_image, alpha)
        elapsed += duration
    raise AssertionError("Animation frame lookup fell outside its period")


def render_at(tick: int, animations):
    canvas = Image.new("RGB", (CELL_W * len(ITEMS), CANVAS_H), (20, 25, 33))
    draw = ImageDraw.Draw(canvas)
    title_font = font(17)
    subtitle_font = font(12)
    for column, (title, item_id) in enumerate(ITEMS):
        base, sequence, period, interpolate = animations[item_id]
        glow = frame_at(sequence, period, interpolate, tick)
        composite = base.copy()
        composite.alpha_composite(glow)
        enlarged = composite.resize((32 * SCALE, 32 * SCALE), Image.Resampling.NEAREST)
        x = column * CELL_W
        draw.text((x + 14, 14), title, fill=(235, 240, 247), font=title_font)
        draw.text((x + 14, 38), item_id, fill=(145, 160, 179), font=subtitle_font)
        canvas.paste(enlarged.convert("RGB"), (x + (CELL_W - 32 * SCALE) // 2, 64))
    return canvas


def main():
    animations = {item_id: load_animation(item_id) for _, item_id in ITEMS}
    full_cycle = math.lcm(*(period for _, _, period, _ in animations.values()))
    frames = [render_at(tick, animations) for tick in range(full_cycle)]
    palette = frames[0].convert("P", palette=Image.Palette.ADAPTIVE, colors=256)
    paletted = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    paletted[0].save(
        OUT,
        save_all=True,
        append_images=paletted[1:],
        # Minecraft advances one animation tick every 50 ms.
        duration=50,
        loop=0,
        optimize=False,
        disposal=2,
    )
    print(f"PASS {OUT}: {len(frames)} timeline samples, {full_cycle} ticks, 3 original-asset composites")


if __name__ == "__main__":
    main()
