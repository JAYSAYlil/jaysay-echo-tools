"""Build deterministic emissive animation strips for the 1.6.0 item set.

Base item PNGs are read-only inputs. This script writes *_glow.png strips,
their .mcmeta files, face-level Forge emission metadata in the item models,
and visual diagnostics under artwork/validation/v1.6.0.
"""
from __future__ import annotations

import colorsys
import json
import math
import shutil
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "src/main/resources/assets/echopickaxe"
TEXTURES = ASSETS / "textures/item"
MODELS = ASSETS / "models/item"
SOURCE = ROOT / "artwork/source/emissive-v1.6.0"
VALIDATION = ROOT / "artwork/validation/v1.6.0"
SIZE = 32
FRAME_COUNT = 16

# `kind` selects only existing saturated color pixels inside the hard alpha
# silhouette. White/bone-white highlights are intentionally excluded.
CONFIG = {
    "echo_pickaxe": {"kind": "cyan", "motion": "diagonal", "ticks": 3, "palette": "cyan"},
    "echo_upgrade_smithing_template": {"kind": "cyan_center", "motion": "pulse", "ticks": 4, "palette": "cyan"},
    "echo_crystal": {"kind": "cyan_center", "motion": "pulse", "ticks": 6, "palette": "ice"},
    "resonance_crystal": {"kind": "red", "motion": "branch", "ticks": 4, "palette": "red_gold"},
    "enhanced_resonance_crystal": {"kind": "red_cyan", "motion": "split", "ticks": 4, "palette": "red_cyan"},
    "frequency_crystal": {"kind": "purple", "motion": "branch", "ticks": 4, "palette": "purple_split"},
    "enhanced_frequency_crystal": {"kind": "purple_cyan", "motion": "split", "ticks": 4, "palette": "purple_cyan"},
    "enhanced_frequency_crystal_2": {"kind": "purple_cyan", "motion": "split", "ticks": 6, "palette": "purple_ice"},
    "extension_crystal": {"kind": "green_cyan", "motion": "upward", "ticks": 4, "palette": "ender"},
    "enhanced_extension_crystal": {"kind": "green_cyan", "motion": "upward_split", "ticks": 4, "palette": "ender_ice"},
    "enhanced_extension_crystal_2": {"kind": "green_cyan", "motion": "upward_split", "ticks": 6, "palette": "ender_bone"},
    "tuning_crystal": {"kind": "cyan", "motion": "four_arms", "ticks": 6, "palette": "ice"},
}

PALETTES = {
    "cyan": {"cyan": (36, 210, 226)},
    "ice": {"cyan": (74, 213, 238)},
    "red_gold": {"red": (246, 55, 38), "gold": (245, 158, 42)},
    "red_cyan": {"red": (246, 55, 38), "gold": (242, 151, 39), "cyan": (52, 202, 224)},
    "purple_split": {"purple": (176, 75, 239), "cyan": (42, 197, 220)},
    "purple_cyan": {"purple": (174, 72, 240), "cyan": (42, 202, 227)},
    "purple_ice": {"purple": (175, 76, 231), "cyan": (80, 205, 231)},
    "ender": {"green": (40, 212, 147), "cyan": (42, 194, 210)},
    "ender_ice": {"green": (38, 207, 142), "cyan": (66, 205, 229)},
    "ender_bone": {"green": (40, 205, 148), "cyan": (90, 203, 220)},
}


def hue_group(rgb: tuple[int, int, int]) -> str | None:
    r, g, b = (v / 255.0 for v in rgb)
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    # Remove sculk shadows and desaturated bone-white highlights from the mask.
    if s < 0.40 or v < 0.27:
        return None
    if h <= 0.075 or h >= 0.965:
        return "red"
    if 0.20 <= h < 0.455:
        return "green"
    if 0.455 <= h <= 0.625:
        return "cyan"
    if 0.69 <= h <= 0.91:
        return "purple"
    return None


def in_mask(item: str, kind: str, x: int, y: int, group: str | None) -> bool:
    if group is None:
        return False
    if kind == "cyan":
        return group == "cyan"
    if kind == "cyan_center":
        return group == "cyan" and 8 <= x <= 24 and 5 <= y <= 27
    if kind == "red":
        return group == "red" and 5 <= x <= 27 and 3 <= y <= 29
    if kind == "red_cyan":
        if group == "red":
            return 5 <= x <= 27 and 3 <= y <= 29
        return group == "cyan" and 10 <= x <= 22 and 7 <= y <= 26
    if kind == "purple":
        return group == "purple"
    if kind == "purple_cyan":
        if group == "purple":
            return True
        return group == "cyan" and 9 <= x <= 23 and 6 <= y <= 27
    if kind == "green_cyan":
        if group == "green":
            return True
        return group == "cyan" and 8 <= x <= 23 and 5 <= y <= 28
    raise ValueError(f"Unknown mask kind: {kind}")


def spatial_progress(points: list[tuple[int, int, str]], item: str, motion: str,
                     x: int, y: int, group: str) -> float:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    if motion == "diagonal":
        values = [px - py for px, py, _ in points]
        value = x - y
    elif motion in ("upward", "upward_split"):
        lo, hi = min(ys), max(ys)
        value = hi - y
        values = [hi - py for py in ys]
    elif motion in ("branch", "split"):
        cx, cy = 15.5, 19.0
        values = [math.hypot(px - cx, py - cy) for px, py, _ in points]
        value = math.hypot(x - cx, y - cy)
    else:
        values = []
        value = 0.0
    if values:
        lo, hi = min(values), max(values)
        return 0.0 if hi == lo else (value - lo) / (hi - lo)
    return 0.0


def pulse_value(item: str, config: dict, points: list[tuple[int, int, str]],
                x: int, y: int, group: str, frame: int) -> float:
    motion = config["motion"]
    phase = frame / FRAME_COUNT
    progress = spatial_progress(points, item, motion, x, y, group)
    if motion == "pulse":
        wave = 0.5 + 0.5 * math.sin(2 * math.pi * phase)
    elif motion in ("diagonal", "upward", "branch"):
        wave = 0.5 + 0.5 * math.cos(2 * math.pi * (phase - progress))
    elif motion == "split":
        offset = 0.5 if group in ("cyan", "green") else 0.0
        wave = 0.5 + 0.5 * math.cos(2 * math.pi * (phase - progress + offset))
    elif motion == "upward_split":
        offset = 0.30 if group in ("cyan",) else 0.0
        wave = 0.5 + 0.5 * math.cos(2 * math.pi * (phase - progress + offset))
    elif motion == "four_arms":
        dx, dy = x - 15.5, y - 15.5
        if abs(dx) > abs(dy):
            arm = 1 if dx > 0 else 3
        else:
            arm = 2 if dy > 0 else 0
        along = max(abs(dx), abs(dy)) / 15.5
        # One full four-arm scan per sprite cycle, each arm offset by a quarter.
        wave = 0.5 + 0.5 * math.cos(2 * math.pi * (phase - arm / 4 - along * 0.30))
    else:
        raise ValueError(f"Unknown motion: {motion}")
    return wave


def target_for(item: str, palette: str, group: str, x: int, y: int,
               strength: float) -> tuple[int, int, int]:
    choices = PALETTES[palette]
    if group == "red" and "gold" in choices:
        # Gold is a fixed minority vein; the animated wave makes it travel.
        target = choices["gold"] if (x + y) % 3 == 0 else choices["red"]
    elif group in choices:
        target = choices[group]
    elif group == "purple" and "cyan" in choices and x >= 16:
        target = choices["cyan"]
    elif group == "green" and "green" not in choices:
        target = choices.get("cyan", (40, 200, 205))
    else:
        target = next(iter(choices.values()))
    return target


def build_frame(base: Image.Image, points: list[tuple[int, int, str]],
                item: str, config: dict, frame: int) -> Image.Image:
    out = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    for x, y, group in points:
        wave = pulse_value(item, config, points, x, y, group, frame)
        mix = 0.12 + 0.28 * wave
        brightness = 0.50 + 0.55 * wave
        target = target_for(item, config["palette"], group, x, y, wave)
        source = base.getpixel((x, y))[:3]
        rgb = tuple(min(255, round((a * (1 - mix) + b * mix) * brightness))
                    for a, b in zip(source, target))
        out.putpixel((x, y), (*rgb, 255))
    return out


def attach_model_glow(item: str, selected: set[tuple[int, int]]) -> None:
    model_path = MODELS / f"{item}.json"
    backup = SOURCE / "base_models" / f"{item}.json"
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        shutil.copy2(model_path, backup)
    # Always rebuild from the pre-emissive baseline so narrower masks on
    # repeated runs cannot retain stale #glow bindings.
    model = json.loads(backup.read_text(encoding="utf-8-sig"))
    model["textures"]["glow"] = f"echopickaxe:item/{item}_glow"
    marked = set()
    for element in model["elements"]:
        face = element["faces"].get("north")
        if not face:
            continue
        u, v = face["uv"][:2]
        x, y = round((u - 0.25) * 2), round((v - 0.25) * 2)
        if (x, y) not in selected:
            continue
        marked.add((x, y))
        for direction in ("north", "south"):
            data = element["faces"][direction]
            data["texture"] = "#glow"
            data["forge_data"] = {
                "block_light": 15,
                "sky_light": 15,
                "ambient_occlusion": False,
            }
    if marked != selected:
        raise RuntimeError(f"{item}: model mask mismatch (missing={sorted(selected-marked)[:8]})")
    model_path.write_text(json.dumps(model, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def make_contact_sheet(items: list[str], image_for, output: Path,
                      scale: int = 6, columns: int = 4) -> None:
    pad = 12
    cell = SIZE * scale
    rows = math.ceil(len(items) / columns)
    sheet = Image.new("RGBA", (columns * cell + (columns + 1) * pad,
                                rows * cell + (rows + 1) * pad), (54, 58, 64, 255))
    for index, item in enumerate(items):
        x = pad + (index % columns) * (cell + pad)
        y = pad + (index // columns) * (cell + pad)
        sprite = image_for(item).resize((cell, cell), Image.Resampling.NEAREST)
        sheet.alpha_composite(sprite, (x, y))
    sheet.save(output)


def main() -> None:
    SOURCE.mkdir(parents=True, exist_ok=True)
    VALIDATION.mkdir(parents=True, exist_ok=True)
    names = list(CONFIG)
    base_backup_dir = SOURCE / "base_textures"
    base_backup_dir.mkdir(parents=True, exist_ok=True)
    for item in names:
        source_png = TEXTURES / f"{item}.png"
        backup_png = base_backup_dir / source_png.name
        if not backup_png.exists():
            shutil.copy2(source_png, backup_png)
    bases: dict[str, Image.Image] = {}
    masks: dict[str, list[tuple[int, int, str]]] = {}
    frames_by_item: dict[str, list[Image.Image]] = {}
    manifest = {"frame_count": FRAME_COUNT, "items": {}}

    for item, config in CONFIG.items():
        base = Image.open(TEXTURES / f"{item}.png").convert("RGBA")
        if base.size != (SIZE, SIZE):
            raise ValueError(f"{item}: expected 32x32 base sprite, got {base.size}")
        alphas = {p[3] for p in base.getdata()}
        if not alphas <= {0, 255}:
            raise ValueError(f"{item}: base texture has non-binary alpha {alphas}")
        selected = []
        for y in range(SIZE):
            for x in range(SIZE):
                r, g, b, a = base.getpixel((x, y))
                group = hue_group((r, g, b)) if a == 255 else None
                if in_mask(item, config["kind"], x, y, group):
                    # Split existing purple/green veins into two moving color bands.
                    if config["palette"] == "purple_split" and group == "purple" and x >= 16:
                        group = "cyan"
                    selected.append((x, y, group))
        if not selected:
            raise RuntimeError(f"{item}: empty glow mask")
        selected_set = {(x, y) for x, y, _ in selected}
        mask = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        for x, y, _ in selected:
            mask.putpixel((x, y), (255, 255, 255, 255))
        mask.save(VALIDATION / f"{item}-mask.png")

        generated = [build_frame(base, selected, item, config, frame) for frame in range(FRAME_COUNT)]
        strip = Image.new("RGBA", (SIZE, SIZE * FRAME_COUNT), (0, 0, 0, 0))
        for frame_index, frame_image in enumerate(generated):
            strip.alpha_composite(frame_image, (0, frame_index * SIZE))
        strip.save(TEXTURES / f"{item}_glow.png", optimize=True)
        (TEXTURES / f"{item}_glow.png.mcmeta").write_text(json.dumps({
            "animation": {
                "width": SIZE,
                "height": SIZE,
                "frametime": config["ticks"],
                "interpolate": True,
                "frames": list(range(FRAME_COUNT)),
            }
        }, indent=2) + "\n", encoding="utf-8")
        attach_model_glow(item, selected_set)

        bases[item] = base
        masks[item] = selected
        frames_by_item[item] = generated
        manifest["items"][item] = {
            "mask_pixels": len(selected),
            "mask_percent_of_sprite": round(100 * len(selected) / (SIZE * SIZE), 2),
            "mask_coordinates": [[x, y] for x, y, _ in selected],
            "palette_groups": {g: sum(p[2] == g for p in selected) for g in sorted({p[2] for p in selected})},
            "frame_count": FRAME_COUNT,
            "frametime_ticks": config["ticks"],
            "interpolate": True,
            "cycle_seconds": FRAME_COUNT * config["ticks"] / 20,
            "motion": config["motion"],
            "model_faces_glowing": 2 * len(selected),
        }

    def mask_image(item: str) -> Image.Image:
        return Image.open(VALIDATION / f"{item}-mask.png").convert("RGBA")

    def low_image(item: str) -> Image.Image:
        candidates = frames_by_item[item]
        values = [sum(p[0] + p[1] + p[2] for p in img.getdata()) for img in candidates]
        index = min(range(len(values)), key=values.__getitem__)
        out = bases[item].copy()
        for x, y, _ in masks[item]:
            out.putpixel((x, y), candidates[index].getpixel((x, y)))
        return out

    def peak_image(item: str) -> Image.Image:
        candidates = frames_by_item[item]
        values = [sum(p[0] + p[1] + p[2] for p in img.getdata()) for img in candidates]
        index = max(range(len(values)), key=values.__getitem__)
        out = bases[item].copy()
        for x, y, _ in masks[item]:
            out.putpixel((x, y), candidates[index].getpixel((x, y)))
        return out

    make_contact_sheet(names, mask_image, VALIDATION / "masks.png")
    low_sheet = Image.new("RGBA", (2 * (4 * SIZE * 6 + 5 * 12), 3 * SIZE * 6 + 4 * 12), (54, 58, 64, 255))
    # Two same-order 4x3 contact sheets (low level, then peak), side by side.
    for panel, picker in enumerate((low_image, peak_image)):
        for i, item in enumerate(names):
            pad, scale = 12, 6
            cell = SIZE * scale
            x = panel * (4 * cell + 5 * pad) + pad + (i % 4) * (cell + pad)
            y = pad + (i // 4) * (cell + pad)
            low_sheet.alpha_composite(picker(item).resize((cell, cell), Image.Resampling.NEAREST), (x, y))
    low_sheet.save(VALIDATION / "low-peak.png")

    # Align the preview timeline to actual mcmeta timing. Frame time is sampled
    # at one Minecraft tick; the 192-tick common period shows every loop repeat.
    tick_periods = [FRAME_COUNT * c["ticks"] for c in CONFIG.values()]
    common_ticks = math.lcm(*tick_periods)
    preview_frames = []
    for tick in range(common_ticks):
        canvas = Image.new("RGBA", (4 * SIZE * 6 + 5 * 12, 3 * SIZE * 6 + 4 * 12), (54, 58, 64, 255))
        for i, item in enumerate(names):
            config = CONFIG[item]
            index = (tick // config["ticks"]) % FRAME_COUNT
            next_index = (index + 1) % FRAME_COUNT
            interpolation = (tick % config["ticks"]) / config["ticks"]
            glow_frame = Image.blend(frames_by_item[item][index],
                                     frames_by_item[item][next_index], interpolation)
            image = bases[item].copy()
            for x, y, _ in masks[item]:
                image.putpixel((x, y), glow_frame.getpixel((x, y)))
            pad, scale = 12, 6
            x = pad + (i % 4) * (SIZE * scale + pad)
            y = pad + (i // 4) * (SIZE * scale + pad)
            canvas.alpha_composite(image.resize((SIZE * scale, SIZE * scale), Image.Resampling.NEAREST), (x, y))
        preview_frames.append(canvas.convert("RGB"))
    preview_frames[0].save(
        VALIDATION / "emissive-items-preview.gif",
        save_all=True,
        append_images=preview_frames[1:],
        duration=50,
        loop=0,
        optimize=True,
        disposal=2,
    )

    (SOURCE / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"period={common_ticks} ticks ({common_ticks / 20:.1f}s)")
    for item, entry in manifest["items"].items():
        print(f"{item}: mask={entry['mask_pixels']} ({entry['mask_percent_of_sprite']}%), "
              f"groups={entry['palette_groups']}, faces={entry['model_faces_glowing']}, "
              f"cycle={entry['cycle_seconds']:.1f}s")


if __name__ == "__main__":
    main()
