"""Deterministic, preview-only Echo Pickaxe upgrade pixel placements.

Production source is the byte-exact 1.6.0 sprite/glow strip. This first pass
renders the standalone progression candidates for review; it does not deploy
resources into src/main/resources.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
BASE_PATH = ROOT / "artwork/source/emissive-v1.6.0/base_textures/echo_pickaxe.png"
GLOW_PATH = ROOT / "artwork/source/structural-v1.7.0/base_glow_1.6.0/echo_pickaxe_glow.png"
OUT = ROOT / "artwork/validation/v0.1.0/pickaxe/candidate"
OUT.mkdir(parents=True, exist_ok=True)

# Every coordinate is an existing opaque pixel in the 1.6 base texture.
RES_STUDS = [
    [(15, 13), (15, 14)],
    [(15, 15), (15, 16)],
]
FREQ_MARKS = [
    [(11, 21)],
    [(9, 23)],
    [(5, 23)],
]
TUNING_STAR = [(19, 9), (19, 7), (19, 11), (17, 9), (21, 9)]
# The four cardinal marks are the 1.6:1 source texels retained by the 16px
# nearest-neighbour UI preview; the surrounding 32px texture still reads as a
# compact pommel ring without changing its alpha silhouette.
EXT_RING = [(3, 25), (1, 27), (5, 27), (3, 29)]
EXT_CENTER = [(3, 27)]
EXT_BONE_CORNERS = [(4, 26), (2, 28)]

PALETTE = {
    "res": [(225, 78, 67), (248, 126, 93)],
    "freq": [(164, 87, 213), (208, 117, 244)],
    "tune": [(129, 227, 244), (226, 252, 255)],
    "ext": [(31, 159, 100), (66, 221, 139)],
    "ext_core": (81, 224, 239),
    "bone": (224, 220, 207),
}

STATES = [
    ("base-0", (0, 0, 0, 0)),
    ("resonance-I", (1, 0, 0, 0)),
    ("resonance-II", (2, 0, 0, 0)),
    ("frequency-I", (0, 1, 0, 0)),
    ("frequency-II", (0, 2, 0, 0)),
    ("frequency-III", (0, 3, 0, 0)),
    ("tuning-I", (0, 0, 1, 0)),
    ("extension-I", (0, 0, 0, 1)),
    ("extension-II", (0, 0, 0, 2)),
    ("extension-III", (0, 0, 0, 3)),
    ("all-max", (2, 3, 1, 3)),
]


def paint_map(levels: tuple[int, int, int, int]) -> dict[tuple[int, int], tuple[int, int, int]]:
    res, freq, tune, ext = levels
    result: dict[tuple[int, int], tuple[int, int, int]] = {}

    def add(points, colors):
        for i, point in enumerate(points):
            result[point] = colors[i % len(colors)]

    for tier in range(res):
        add(RES_STUDS[tier], PALETTE["res"])
    for tier in range(freq):
        add(FREQ_MARKS[tier], PALETTE["freq"])
    if tune:
        add(TUNING_STAR, PALETTE["tune"])
    if ext:
        add(EXT_RING, PALETTE["ext"])
    if ext >= 2:
        add(EXT_CENTER, [PALETTE["ext_core"]])
    if ext >= 3:
        add(EXT_BONE_CORNERS, [PALETTE["bone"]])
    return result


def assert_source_pixels(base: Image.Image, paint: dict) -> None:
    assert base.size == (32, 32)
    assert set(base.getchannel("A").getdata()) == {0, 255}
    opaque = {(x, y) for y in range(32) for x in range(32) if base.getpixel((x, y))[3] == 255}
    assert set(paint) <= opaque, f"New motif falls outside original silhouette: {set(paint) - opaque}"


def make_base_variant(base: Image.Image, paint: dict) -> Image.Image:
    image = base.copy()
    for (x, y), color in paint.items():
        image.putpixel((x, y), (*color, 255))
    return image


def make_glow_variant(glow: Image.Image, paint: dict) -> Image.Image:
    assert glow.size == (32, 512), glow.size
    output = Image.new("RGBA", glow.size, (0, 0, 0, 0))
    for frame in range(16):
        layer = glow.crop((0, frame * 32, 32, (frame + 1) * 32))
        phase = 2 * math.pi * frame / 16
        level = 0.92 + 0.08 * math.sin(phase)
        for (x, y), rgb in paint.items():
            shade = tuple(max(1, min(255, round(c * level))) for c in rgb)
            layer.putpixel((x, y), (*shade, 255))
        output.paste(layer, (0, frame * 32))
    return output


def label_font(size=18):
    for candidate in ["C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/segoeui.ttf"]:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def main():
    base = Image.open(BASE_PATH).convert("RGBA")
    glow = Image.open(GLOW_PATH).convert("RGBA")
    names = []
    canvas = Image.new("RGB", (470, len(STATES) * 180 + 18), (24, 30, 39))
    draw = ImageDraw.Draw(canvas)
    font = label_font()
    for index, (name, levels) in enumerate(STATES):
        paint = paint_map(levels)
        assert_source_pixels(base, paint)
        sprite = make_base_variant(base, paint)
        animated_glow = make_glow_variant(glow, paint)
        sprite_path = OUT / f"{name}-32.png"
        small_path = OUT / f"{name}-16.png"
        glow_path = OUT / f"{name}-glow-16frames.png"
        sprite.save(sprite_path)
        sprite.resize((16, 16), Image.Resampling.NEAREST).save(small_path)
        animated_glow.save(glow_path)
        # Both render at the same displayed scale: 32-texel and actual 16-texel previews.
        y = 12 + index * 180
        draw.text((12, y), f"{name}  levels={levels}  changed={len(paint)}px", fill=(236, 239, 243), font=font)
        large32 = sprite.resize((128, 128), Image.Resampling.NEAREST)
        large16 = sprite.resize((16, 16), Image.Resampling.NEAREST).resize((128, 128), Image.Resampling.NEAREST)
        canvas.paste(large32.convert("RGB"), (12, y + 30))
        canvas.paste(large16.convert("RGB"), (190, y + 30))
        draw.text((12, y + 160), "32x32 texture", fill=(179, 190, 205), font=label_font(13))
        draw.text((190, y + 160), "16x16 nearest UI", fill=(179, 190, 205), font=label_font(13))
        names.append({"name": name, "levels": levels, "changedPixels": len(paint), "pixels": [list(p) for p in sorted(paint)]})
    canvas.save(OUT / "single-and-full-upgrade-comparison-32-16.png")
    # Compact landscape board for quick human comparison of no upgrade, each
    # attribute at its maximum, and their combined end state.
    compact_states = [
        ("Original", (0, 0, 0, 0)),
        ("Resonance II", (2, 0, 0, 0)),
        ("Frequency III", (0, 3, 0, 0)),
        ("Tuning I", (0, 0, 1, 0)),
        ("Extension III", (0, 0, 0, 3)),
        ("All maximum", (2, 3, 1, 3)),
    ]
    card_w, card_h = 180, 220
    compact = Image.new("RGB", (card_w * len(compact_states), card_h), (27, 32, 41))
    compact_draw = ImageDraw.Draw(compact)
    compact_font = label_font(15)
    for i, (label, levels) in enumerate(compact_states):
        sprite = make_base_variant(base, paint_map(levels))
        x0 = i * card_w
        compact_draw.text((x0 + 9, 10), label, fill=(236, 239, 243), font=compact_font)
        scaled = sprite.resize((128, 128), Image.Resampling.NEAREST)
        compact.paste(scaled.convert("RGB"), (x0 + 26, 42))
        compact_draw.text((x0 + 9, 184), f"R{levels[0]} F{levels[1]} T{levels[2]} E{levels[3]}", fill=(179, 190, 205), font=compact_font)
    compact.save(OUT.parent / "approved-attribute-and-fullmax-preview.png")
    (OUT / "candidate-manifest.json").write_text(json.dumps({
        "baseline": "1.6.0 base; byte-exact preserved outside named motif cells",
        "states": names,
        "note": "Preview only; no production resources written. Full 96-combination generator waits for root approval.",
    }, indent=2), encoding="utf-8")
    print(f"PASS {len(STATES)} preview states; silhouette unchanged; max motif pixels={max(x['changedPixels'] for x in names)}")


if __name__ == "__main__":
    main()
