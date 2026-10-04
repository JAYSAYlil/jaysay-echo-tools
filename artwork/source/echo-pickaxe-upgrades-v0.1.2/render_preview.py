"""Render six native-pixel TConstruct-2-inspired material studies; never deploy."""
from __future__ import annotations

import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import math

ROOT = Path(__file__).resolve().parents[3]
DRAFT = Path(__file__).resolve().parent
OUT = ROOT / "artwork/validation/v0.1.2/tconstruct2-preview"
MAP_PATH = DRAFT / "native-pixel-map.json"
BASE_PATH = ROOT / "src/main/resources/assets/echopickaxe/textures/item/echo_pickaxe.png"
COMPONENTS = ("resonance", "frequency", "tuning", "extension")
ADDED_ALPHA = {
    "resonance": {(4, 8), (4, 9)},
    "frequency": {(30, y) for y in range(11, 16)},
    "extension": {(6, 27), (6, 28), (6, 29), (5, 30)},
}
ALLOWED_ADDED = set().union(*ADDED_ALPHA.values())
MAX_LEVELS = {"resonance": 2, "frequency": 3, "tuning": 1, "extension": 3}
STATES = (
    ("Base", {}),
    ("Resonance II", {"resonance": 2}),
    ("Frequency III", {"frequency": 3}),
    ("Tuning I", {"tuning": 1}),
    ("Extension III", {"extension": 3}),
    ("All maximum", MAX_LEVELS),
)
LEVEL_STATES = [
    ("Base", {}),
    ("Resonance I", {"resonance": 1}),
    ("Resonance II", {"resonance": 2}),
    ("Frequency I", {"frequency": 1}),
    ("Frequency II", {"frequency": 2}),
    ("Frequency III", {"frequency": 3}),
    ("Tuning I", {"tuning": 1}),
    ("Extension I", {"extension": 1}),
    ("Extension II", {"extension": 2}),
    ("Extension III", {"extension": 3}),
    ("All maximum", MAX_LEVELS),
]

data = json.loads(MAP_PATH.read_text(encoding="utf-8-sig"))
palette = data["palette"]
base = Image.open(BASE_PATH).convert("RGBA")
assert base.size == (32, 32)


def paints_for(levels):
    paints = {}
    owners = {}
    for component in COMPONENTS:
        level = levels.get(component, 0)
        for tier in range(1, level + 1):
            for x, y, material in data["components"][component]["tiers"][str(tier)]:
                key = (x, y)
                if key in owners and owners[key] != component:
                    raise ValueError(f"Module overlap at {key}: {owners[key]} / {component}")
                owners[key] = component
                paints[key] = (component, material)
    return paints


def render(levels):
    sprite = base.copy()
    paints = paints_for(levels)
    for (x, y), (_, material) in paints.items():
        if base.getpixel((x, y))[3] != 255 and (x, y) not in ALLOWED_ADDED:
            raise ValueError(f"Attempt to paint outside original plus approved local alpha {(x, y)}")
        sprite.putpixel((x, y), (*palette[material]["rgb"], 255))
    return sprite, paints


def render_expanded(levels):
    """Expanded-alpha preview uses the explicitly mapped one-pixel additions."""
    return render(levels)[0]


def expanded_board(bg, filename):
    cols, rows = 3, 2
    card_w, card_h, margin = 240, 194, 20
    board = Image.new("RGB", (margin * 2 + cols * card_w, margin * 2 + rows * card_h), bg)
    draw = ImageDraw.Draw(board)
    font = get_font(15)
    for i, (name, levels) in enumerate(STATES):
        col, row = i % cols, i // cols
        x, y = margin + col * card_w, margin + row * card_h
        foreground = (30, 36, 40) if sum(bg) > 400 else (235, 239, 244)
        draw.text((x + 8, y + 4), name, fill=foreground, font=font)
        shown = render_expanded(levels).resize((128, 128), Image.Resampling.NEAREST)
        tile = Image.new("RGBA", shown.size, (*bg, 255))
        tile.alpha_composite(shown)
        board.paste(tile.convert("RGB"), (x + 56, y + 28))
        draw.text((x + 8, y + 164), "preview only: blade ends +1px", fill=foreground, font=get_font(12))
    board.save(OUT / filename)

def validate():
    if set(base.getchannel("A").getdata()) != {0, 255}:
        raise ValueError("Expected binary-alpha source texture")
    masks = {}
    for component, cap in MAX_LEVELS.items():
        union = set()
        for tier in range(1, cap + 1):
            entries = data["components"][component]["tiers"][str(tier)]
            if not entries:
                raise ValueError(f"Missing {component} tier {tier}")
            if tier == 1 and not any(palette[m]["emissive"] for _, _, m in entries):
                raise ValueError(f"{component} tier I has no emissive facet")
            for x, y, material in entries:
                if not (0 <= x < 32 and 0 <= y < 32):
                    raise ValueError(f"Out-of-range pixel {(x, y)}")
                if base.getpixel((x, y))[3] != 255 and (x, y) not in ALLOWED_ADDED:
                    raise ValueError(f"Mapped pixel outside original+approved alpha: {component} tier {tier} {(x, y)}")
                union.add((x, y))
        masks[component] = union
    names = list(masks)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            overlap = masks[a] & masks[b]
            if overlap:
                raise ValueError(f"Component masks overlap: {a}/{b} at {sorted(overlap)}")
    for x, y in ALLOWED_ADDED:
        if base.getpixel((x, y))[3] == 255 or not any(base.getpixel((nx, ny))[3] == 255 for nx, ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)) if 0 <= nx < 32 and 0 <= ny < 32):
            raise ValueError(f"New alpha must be one pixel from original opaque silhouette: {(x,y)}")
    if any(y == 31 for _, y in ALLOWED_ADDED):
        raise ValueError("New alpha cannot extend handle length into bottom canvas row")
    for name, levels in STATES:
        render(levels)
    # Every shown single-tier state must survive nearest-neighbor inventory downsampling distinctly.
    signatures = [render(levels)[0].resize((16, 16), Image.Resampling.NEAREST).tobytes() for _, levels in LEVEL_STATES]
    if len(set(signatures)) != len(signatures):
        raise ValueError("Two progression states collapse to the same 16px inventory sprite")
    return masks


def get_font(size=16):
    for path in ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/segoeui.ttf"):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def card_board(bg, size_mode, suffix):
    cols, rows = 3, 2
    card_w, card_h, margin = 240, 194, 20
    board = Image.new("RGB", (margin * 2 + cols * card_w, margin * 2 + rows * card_h), bg)
    draw = ImageDraw.Draw(board)
    font = get_font(15)
    for i, (name, levels) in enumerate(STATES):
        col, row = i % cols, i // cols
        x, y = margin + col * card_w, margin + row * card_h
        foreground = (30, 36, 40) if sum(bg) > 400 else (235, 239, 244)
        draw.text((x + 8, y + 4), name, fill=foreground, font=font)
        sprite, _ = render(levels)
        if size_mode == "source32":
            shown = sprite.resize((128, 128), Image.Resampling.NEAREST)
        else:
            shown = sprite.resize((16, 16), Image.Resampling.NEAREST).resize((128, 128), Image.Resampling.NEAREST)
        tile = Image.new("RGBA", shown.size, (*bg, 255))
        tile.alpha_composite(shown)
        board.paste(tile.convert("RGB"), (x + 56, y + 28))
        caption = "32px source ×4" if size_mode == "source32" else "16px inventory ×8 nearest"
        draw.text((x + 8, y + 164), caption, fill=foreground, font=get_font(12))
    board.save(OUT / suffix)


def grade_board(bg, size_mode, filename):
    cols, card_w, card_h, margin = 4, 190, 170, 16
    rows = (len(LEVEL_STATES) + cols - 1) // cols
    board = Image.new("RGB", (margin * 2 + cols * card_w, margin * 2 + rows * card_h), bg)
    draw = ImageDraw.Draw(board)
    fg = (30, 36, 40) if sum(bg) > 400 else (235, 239, 244)
    for i, (name, levels) in enumerate(LEVEL_STATES):
        col, row = i % cols, i // cols
        x, y = margin + col * card_w, margin + row * card_h
        draw.text((x + 4, y + 3), name, fill=fg, font=get_font(13))
        sprite = render(levels)[0]
        if size_mode == "source32":
            shown = sprite.resize((96, 96), Image.Resampling.NEAREST)
            caption = "32px ×3"
        else:
            shown = sprite.resize((16, 16), Image.Resampling.NEAREST).resize((96, 96), Image.Resampling.NEAREST)
            caption = "16px inventory ×6 NN"
        tile = Image.new("RGBA", shown.size, (*bg, 255))
        tile.alpha_composite(shown)
        board.paste(tile.convert("RGB"), (x + 44, y + 24))
        draw.text((x + 4, y + 136), caption, fill=fg, font=get_font(11))
    board.save(OUT / filename)


def full_animation_gif():
    """96 samples ×50ms = two 16×3tick cycles, including interpolated base glow."""
    base_glow_path = ROOT / "src/main/resources/assets/echopickaxe/textures/item/echo_pickaxe_glow.png"
    glow_sheet = Image.open(base_glow_path).convert("RGBA")
    if glow_sheet.size != (32, 512):
        raise ValueError(f"Unexpected original glow sheet size {glow_sheet.size}")
    glow_frames = [glow_sheet.crop((0, i * 32, 32, (i + 1) * 32)) for i in range(16)]
    full_base, paints = render(MAX_LEVELS)
    emissive_cells = []
    for (x, y), (_, material) in paints.items():
        if palette[material]["emissive"]:
            emissive_cells.append((x, y, palette[material]["rgb"]))
    samples = []
    bg = Image.new("RGBA", (32, 32), (20, 25, 31, 255))
    for t in range(96):
        phase = (t / 3.0) % 16
        i0 = int(phase) % 16
        i1 = (i0 + 1) % 16
        frac = phase - int(phase)
        glow = Image.blend(glow_frames[i0], glow_frames[i1], frac)
        frame = full_base.copy()
        frame.alpha_composite(glow)
        pulse = 0.80 + 0.20 * (0.5 + 0.5 * math.sin(2 * math.pi * phase / 16))
        for x, y, rgb in emissive_cells:
            color = tuple(round(channel * pulse) for channel in rgb)
            frame.putpixel((x, y), (*color, 255))
        bg.alpha_composite(frame)
        samples.append(bg.resize((256, 256), Image.Resampling.NEAREST).convert("RGB"))
        bg = Image.new("RGBA", (32, 32), (20, 25, 31, 255))
    samples[0].save(OUT / "all-maximum-dynamic-two-cycles.gif", save_all=True, append_images=samples[1:], duration=50, loop=0, disposal=2, optimize=False)

def inventory_actual():
    # Exact 16px rendered sprites in a roomy neutral sheet; no enlargement.
    cols, card_w, card_h = 3, 112, 64
    board = Image.new("RGBA", (cols * card_w, 2 * card_h), (247, 247, 243, 255))
    draw = ImageDraw.Draw(board)
    for i, (name, levels) in enumerate(STATES):
        x, y = (i % cols) * card_w, (i // cols) * card_h
        draw.text((x + 2, y + 2), name, fill=(24, 30, 33), font=get_font(10))
        sprite, _ = render(levels)
        icon = sprite.resize((16, 16), Image.Resampling.NEAREST)
        board.alpha_composite(icon, (x + 48, y + 25))
    board.convert("RGB").save(OUT / "inventory-size-actual-16px.png")


def main():
    masks = validate()
    OUT.mkdir(parents=True, exist_ok=True)
    card_board((255, 255, 255), "source32", "white-background-32px.png")
    grade_board((255,255,255), "source32", "all-levels-white-32px.png")
    card_board((20, 25, 31), "source32", "dark-background-32px.png")
    grade_board((20,25,31), "source32", "all-levels-dark-32px.png")
    grade_board((255,255,255), "inventory16", "all-levels-inventory-16px.png")
    card_board((255, 255, 255), "inventory16", "inventory-size-nearest-preview.png")
    expanded_board((255, 255, 255), "blade-end-expansion-white.png")
    expanded_board((20, 25, 31), "blade-end-expansion-dark.png")
    inventory_actual()
    full_animation_gif()

    # Separate transparent native-size sprites make the per-state mapping inspectable.
    sprites = OUT / "states-32px"
    sprites.mkdir(parents=True, exist_ok=True)
    for name, levels in STATES:
        sprite, _ = render(levels)
        sprite.save(sprites / (name.lower().replace(" ", "-") + ".png"))
    (OUT / "preview-record.json").write_text(json.dumps({
        "purpose": "Six-state and full progression concept candidate only; not a production texture set.",
        "sourceTexture": "src/main/resources/assets/echopickaxe/textures/item/echo_pickaxe.png (unchanged original 0.1.1)",
        "nativeMap": "artwork/source/echo-pickaxe-upgrades-tconstruct2-draft/native-pixel-map.json",
        "states": [{"name": name, "levels": levels} for name, levels in STATES],
        "originalAlphaOnly": True,
        "maskPixels": {k: len(v) for k, v in masks.items()},
        "referenceUse": "Tinkers Construct 2 / 1.12 official overlay comparison used only for localized material integration and faceted motif cues; no pixels copied.",
        "renderViews": ["white-background-32px.png", "dark-background-32px.png", "inventory-size-nearest-preview.png", "inventory-size-actual-16px.png", "all-levels-white-32px.png", "all-levels-dark-32px.png", "all-levels-inventory-16px.png", "all-maximum-dynamic-two-cycles.gif", "blade-end-expansion-white.png", "blade-end-expansion-dark.png"]
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PASS six states + {len(LEVEL_STATES)} progression states; masks={ {k:len(v) for k,v in masks.items()} }; approved local alpha additions={len(ALLOWED_ADDED)}; output={OUT}")


if __name__ == "__main__":
    main()
