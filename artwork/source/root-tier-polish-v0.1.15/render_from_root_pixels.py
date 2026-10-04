"""Render root-authored 128x128 RGBA states without editing any pixel value.

Expected input: artwork/source/root-tier-polish-v0.1.15/root-pixel-states.json
The source file is read-only. Generated review PNGs and audit JSON are written
to artwork/validation/root-tier-polish-v0.1.15/rendered-final/ after the entire input validates.
"""
from __future__ import annotations

import hashlib
import argparse
import json
import re
from collections import deque
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
INPUT = ROOT / "artwork/source/root-tier-polish-v0.1.15/root-pixel-states.json"
DEFAULT_OUTPUT_RELATIVE = "artwork/validation/root-tier-polish-v0.1.15/rendered-final"
OUTPUT = ROOT / DEFAULT_OUTPUT_RELATIVE
ORDINARY64 = ROOT / "src/main/resources/assets/echopickaxe/textures/item/echo_pickaxe.png"
SHEET_SCALE = 2
CLOSEUP_SCALE = 6
MODULES = ("resonance", "split", "extension", "tuning")
MODULE_LABELS = {
    "resonance": "共振",
    "split": "分频",
    "extension": "延展",
    "tuning": "调谐",
}
DEFAULT_COMPONENT_BOUNDS128 = {
    # Fixed view windows from the established native128 tool layout; display-only,
    # never used to select, clip, paint, or validate artwork pixels.
    "resonance": (34, 84, 0, 41),
    "split": (93, 127, 41, 74),
    "extension": (10, 31, 94, 117),
    "tuning": (78, 96, 23, 42),
}
LEVEL_LABELS = ("未强化", "Ⅰ", "Ⅱ", "Ⅲ")
STATE_GRID = {
    "resonance": ("ordinary128", "resonance1", "resonance2", None),
    "split": ("ordinary128", "split1", "split2", "split3"),
    "extension": ("ordinary128", "extension1", "extension2", "extension3"),
    "tuning": ("ordinary128", "tuning1", None, None),
}
STATE_LABELS = {
    "ordinary128": "普通",
    "resonance1": "共振 Ⅰ", "resonance2": "共振 Ⅱ",
    "split1": "分频 Ⅰ", "split2": "分频 Ⅱ", "split3": "分频 Ⅲ",
    "extension1": "延展 Ⅰ", "extension2": "延展 Ⅱ", "extension3": "延展 Ⅲ",
    "tuning1": "调谐 Ⅰ", "all_max": "全满",
}
EXPECTED_STATES = set(STATE_LABELS)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def strict_int(value, label: str) -> int:
    require(type(value) is int, f"{label}: expected an integer")
    require(0 <= value <= 255, f"{label}: component outside 0..255: {value}")
    return value


def parse_state_pixels(state_name: str, state: dict) -> tuple[bytes, dict]:
    require(isinstance(state, dict), f"{state_name}: state entry must be an object")
    pixels = state.get("pixelsRGBA")
    require(isinstance(pixels, list) and len(pixels) == 128,
            f"{state_name}: pixelsRGBA must contain 128 rows")
    packed = bytearray()
    transparent_nonzero = []
    opaque = set()
    for y, row in enumerate(pixels):
        require(isinstance(row, list) and len(row) == 128,
                f"{state_name}: pixelsRGBA row {y} must contain 128 pixels")
        for x, rgba in enumerate(row):
            require(isinstance(rgba, list) and len(rgba) == 4,
                    f"{state_name}: pixel ({x},{y}) must be [r,g,b,a]")
            values = tuple(strict_int(v, f"{state_name} ({x},{y}) RGBA") for v in rgba)
            r, g, b, a = values
            if a == 0:
                if (r, g, b) != (0, 0, 0):
                    transparent_nonzero.append([x, y, r, g, b])
            else:
                opaque.add((x, y))
            packed.extend(values)
    require(not transparent_nonzero,
            f"{state_name}: transparent pixels must already have RGB zero; first points: {transparent_nonzero[:20]}")
    return bytes(packed), {"opaque": opaque, "transparentRgbNonzero": transparent_nonzero}


def connected_components(points: set[tuple[int, int]], diagonal: bool) -> list[int]:
    remaining = set(points)
    sizes = []
    if diagonal:
        offsets = ((-1,-1),(0,-1),(1,-1),(-1,0),(1,0),(-1,1),(0,1),(1,1))
    else:
        offsets = ((0,-1),(-1,0),(1,0),(0,1))
    while remaining:
        start = remaining.pop()
        queue = deque([start])
        size = 0
        while queue:
            x, y = queue.popleft()
            size += 1
            for dx, dy in offsets:
                neighbor = (x + dx, y + dy)
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    queue.append(neighbor)
        sizes.append(size)
    return sorted(sizes, reverse=True)


def chinese_font(size: int) -> ImageFont.ImageFont:
    for name in ("msyh.ttc", "msyhbd.ttc", "simhei.ttf"):
        path = Path("C:/Windows/Fonts") / name
        if path.is_file():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def composite_rgb(image: Image.Image, background: tuple[int, int, int]) -> Image.Image:
    panel = Image.new("RGBA", image.size, (*background, 255))
    panel.alpha_composite(image)
    return panel.convert("RGB")


def load_component_bounds(document: dict) -> dict[str, tuple[int, int, int, int]]:
    raw = document.get("componentBounds128")
    if raw is None:
        return dict(DEFAULT_COMPONENT_BOUNDS128)
    require(isinstance(raw, dict), "componentBounds128 must be an object of display-only crops")
    require(set(raw) == set(MODULES), "componentBounds128 must name resonance/split/extension/tuning exactly")
    bounds = {}
    for module, value in raw.items():
        require(isinstance(value, list) and len(value) == 4,
                f"{module}: componentBounds128 must be [x0,y0,x1,y1]")
        require(all(type(v) is int for v in value), f"{module}: bounds must be integers")
        x0, y0, x1, y1 = value
        require(0 <= x0 <= x1 < 128 and 0 <= y0 <= y1 < 128,
                f"{module}: component crop is outside the 128x128 image: {value}")
        bounds[module] = (x0, y0, x1, y1)
    return bounds


def make_level_boards(images: dict[str, Image.Image], background_name: str,
                      background: tuple[int, int, int], output: Path) -> None:
    cell = 128 * SHEET_SCALE
    left = 84
    margin = 10
    header = 70
    row_height = cell + margin
    width = left + margin + 4 * cell + 5 * margin
    height = header + 4 * row_height + cell + 3 * margin
    board = Image.new("RGB", (width, height), background)
    draw = ImageDraw.Draw(board)
    fg = (28, 30, 37) if background_name == "white" else (245, 246, 250)
    small = chinese_font(18)
    draw.text((margin, 14), f"强化阶段对照｜{background_name}底｜128 原图 ×2 最近邻", font=small, fill=fg)
    for col, label in enumerate(LEVEL_LABELS):
        x = left + margin + col * (cell + margin)
        draw.text((x + 4, 43), label, font=small, fill=fg)
    for row, module in enumerate(MODULES):
        y = header + row * row_height
        draw.text((margin, y + cell // 2 - 11), MODULE_LABELS[module], font=small, fill=fg)
        for col, state_name in enumerate(STATE_GRID[module]):
            x = left + margin + col * (cell + margin)
            if state_name is None:
                draw.text((x + cell // 2 - 6, y + cell // 2 - 11), "—", font=small, fill=fg)
                continue
            tile = composite_rgb(images[state_name], background).resize(
                (cell, cell), Image.Resampling.NEAREST)
            board.paste(tile, (x, y))
    max_y = header + 4 * row_height
    draw.text((margin, max_y + cell // 2 - 11), "全满", font=small, fill=fg)
    max_tile = composite_rgb(images["all_max"], background).resize((cell, cell), Image.Resampling.NEAREST)
    board.paste(max_tile, (left + margin, max_y))
    output.parent.mkdir(parents=True, exist_ok=True)
    board.save(output, format="PNG", optimize=False)


def make_state_board(images: dict[str, Image.Image], state_names: list[str],
                     background_name: str, background: tuple[int, int, int], output: Path) -> None:
    cell = 128 * SHEET_SCALE
    label_w = 140
    margin = 10
    header = 56
    board = Image.new("RGB", (label_w + cell + 3 * margin,
                               header + len(state_names) * (cell + margin)), background)
    draw = ImageDraw.Draw(board)
    fg = (28, 30, 37) if background_name == "white" else (245, 246, 250)
    font = chinese_font(18)
    draw.text((margin, 16), f"Root 像素态逐级预览｜{background_name}底｜像素无插值", font=font, fill=fg)
    for row, state_name in enumerate(state_names):
        y = header + row * (cell + margin)
        draw.text((margin, y + cell // 2 - 10), STATE_LABELS[state_name], font=font, fill=fg)
        tile = composite_rgb(images[state_name], background).resize((cell, cell), Image.Resampling.NEAREST)
        board.paste(tile, (label_w + margin, y))
    output.parent.mkdir(parents=True, exist_ok=True)
    board.save(output, format="PNG", optimize=False)


def make_component_board(images: dict[str, Image.Image], bounds: dict[str, tuple[int,int,int,int]],
                         module: str, state_names: list[str], background_name: str,
                         background: tuple[int, int, int], output: Path) -> None:
    x0, y0, x1, y1 = bounds[module]
    crop_size = ((x1 - x0 + 1) * CLOSEUP_SCALE, (y1 - y0 + 1) * CLOSEUP_SCALE)
    label_w = 130
    margin = 8
    header = 46
    board = Image.new("RGB", (label_w + crop_size[0] + 3 * margin,
                               header + len(state_names) * (crop_size[1] + margin)), background)
    draw = ImageDraw.Draw(board)
    fg = (28, 30, 37) if background_name == "white" else (245, 246, 250)
    font = chinese_font(18)
    draw.text((margin, 12), f"{MODULE_LABELS[module]}部件局部｜{background_name}底｜{CLOSEUP_SCALE}×", font=font, fill=fg)
    for row, state_name in enumerate(state_names):
        y = header + row * (crop_size[1] + margin)
        draw.text((margin, y + crop_size[1] // 2 - 10), STATE_LABELS[state_name], font=font, fill=fg)
        crop = images[state_name].crop((x0, y0, x1 + 1, y1 + 1))
        tile = composite_rgb(crop, background).resize(crop_size, Image.Resampling.NEAREST)
        board.paste(tile, (label_w + margin, y))
    output.parent.mkdir(parents=True, exist_ok=True)
    board.save(output, format="PNG", optimize=False)


def main() -> None:
    global OUTPUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=DEFAULT_OUTPUT_RELATIVE,
                        help="empty/nonexistent repository-relative output directory")
    args = parser.parse_args()
    requested_output = Path(args.output)
    require(not requested_output.is_absolute(), "--output must be repository-relative")
    OUTPUT = (ROOT / requested_output).resolve()
    require(OUTPUT == ROOT or ROOT in OUTPUT.parents, "--output escapes the repository")
    require(OUTPUT != INPUT.parent and INPUT.parent not in OUTPUT.parents,
            "--output may not overwrite the root-authored source directory")
    require(INPUT.is_file(), f"root pixel input not found: {INPUT}")
    raw = INPUT.read_bytes()
    document = json.loads(raw.decode("utf-8-sig"))
    require(isinstance(document, dict), "root-pixel-states.json must be an object")
    states = document.get("states")
    require(isinstance(states, dict), "root-pixel-states.json must contain a states object")
    require(set(states) == EXPECTED_STATES,
            f"state names differ from supported review set: missing={sorted(EXPECTED_STATES-set(states))}, extra={sorted(set(states)-EXPECTED_STATES)}")
    bounds = load_component_bounds(document)
    parsed: dict[str, bytes] = {}
    opaque_sets: dict[str, set[tuple[int,int]]] = {}
    glow_effects = {}
    for name, state in states.items():
        require(re.fullmatch(r"[A-Za-z0-9_-]+", name) is not None, f"unsafe state name: {name!r}")
        data, pixel_info = parse_state_pixels(name, state)
        parsed[name] = data
        opaque_sets[name] = pixel_info["opaque"]
        effects = state.get("glowPointEffects", [])
        require(isinstance(effects, (dict, list)), f"{name}: glowPointEffects must be an object or array")
        glow_effects[name] = effects

    base_name = document.get("ordinaryBaseState", "ordinary128")
    require(base_name in parsed, f"ordinaryBaseState does not identify an included state: {base_name}")
    ordinary_source_bytes = ORDINARY64.read_bytes()
    ordinary_source = Image.open(ORDINARY64).convert("RGBA")
    require(ordinary_source.size == (64, 64), "current ordinary texture must be 64x64")
    expected_ordinary = ordinary_source.resize((128, 128), Image.Resampling.NEAREST)
    expected_pixels = bytearray(expected_ordinary.tobytes())
    for offset in range(0, len(expected_pixels), 4):
        if expected_pixels[offset + 3] == 0:
            expected_pixels[offset:offset + 4] = b"\x00\x00\x00\x00"
    actual_ordinary = parsed[base_name]
    ordinary_diffs = []
    for i in range(0, len(actual_ordinary), 4):
        if actual_ordinary[i:i + 4] != expected_pixels[i:i + 4]:
            pixel_index = i // 4
            ordinary_diffs.append([pixel_index % 128, pixel_index // 128,
                                   list(actual_ordinary[i:i + 4]), list(expected_pixels[i:i + 4])])
    ordinary_report = {
        "sourcePath": ORDINARY64.relative_to(ROOT).as_posix(),
        "sourceFileSha256": digest(ordinary_source_bytes),
        "expectedMethod": "64x64 ordinary RGBA nearest-neighbor 2x; transparent RGB normalized only in comparison reference",
        "inputState": base_name,
        "pixelExact": not ordinary_diffs,
        "differentTexelCount": len(ordinary_diffs),
        "firstDifferences": ordinary_diffs[:64],
    }

    # Validate the optional external comparison before creating any output files.
    mother = document.get("motherReference")
    preflight_mother = None
    if mother is not None:
        require(isinstance(mother, dict), "motherReference must be an object")
        if "pixelsRGBA" in mother:
            preflight_mother, _ = parse_state_pixels("motherReference", mother)
        else:
            reference_path_value = mother.get("path")
            require(isinstance(reference_path_value, str), "motherReference requires pixelsRGBA or path")
            reference_path = (ROOT / reference_path_value).resolve()
            require(ROOT == reference_path or ROOT in reference_path.parents,
                    "motherReference path escapes repository")
            reference_bytes = reference_path.read_bytes()
            expected = mother.get("sha256")
            require(isinstance(expected, str) and digest(reference_bytes) == expected.upper(),
                    "motherReference PNG SHA256 does not match its declared hash")
            reference_image = Image.open(reference_path).convert("RGBA")
            require(reference_image.size == (128, 128), "motherReference PNG must be 128x128")

    require(not OUTPUT.exists() or not any(OUTPUT.iterdir()),
            f"refusing to overwrite a nonempty review directory: {OUTPUT}")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    images: dict[str, Image.Image] = {}
    state_report = {}
    for name in states:
        image = Image.frombytes("RGBA", (128, 128), parsed[name])
        path = OUTPUT / f"{name}.png"
        image.save(path, format="PNG", optimize=False)
        reread = Image.open(path).convert("RGBA")
        require(reread.tobytes() == parsed[name], f"{name}: output PNG did not preserve exact RGBA pixels")
        images[name] = image
        alpha_values = sorted({parsed[name][i] for i in range(3, len(parsed[name]), 4)})
        state_report[name] = {
            "rgbaBytesSha256": digest(parsed[name]),
            "pngSha256": digest(path.read_bytes()),
            "alphaValues": alpha_values,
            "opaqueTexels": len(opaque_sets[name]),
            "fourConnectedComponentSizes": connected_components(opaque_sets[name], diagonal=False),
            "eightConnectedComponentSizes": connected_components(opaque_sets[name], diagonal=True),
            "glowPointEffects": glow_effects[name],
        }

    base_path = OUTPUT / f"{base_name}.png"
    mother_report = {"provided": False, "comparison": "not supplied"}
    if mother is not None:
        if "pixelsRGBA" in mother:
            ref_image = Image.frombytes("RGBA", (128, 128), preflight_mother)
            ref_hash = digest(preflight_mother)
            reference_description = "root pixel JSON motherReference pixelsRGBA"
        else:
            reference_path_value = mother.get("path")
            reference_path = (ROOT / reference_path_value).resolve()
            ref_file = reference_path.read_bytes()
            ref_image = Image.open(reference_path).convert("RGBA")
            ref_hash = digest(ref_file)
            reference_description = reference_path.relative_to(ROOT).as_posix()
        compared_state = mother.get("state", "all_max")
        require(compared_state in images, f"motherReference.state is not in states: {compared_state}")
        a, b = images[compared_state].load(), ref_image.load()
        diff = [[x, y, list(a[x, y]), list(b[x, y])] for y in range(128) for x in range(128) if a[x, y] != b[x, y]]
        mother_report = {"provided": True, "reference": reference_description,
                         "referenceSha256": ref_hash, "comparedState": compared_state,
                         "pixelExact": not diff, "differentTexelCount": len(diff),
                         "firstDifferences": diff[:64]}

    state_order = ["ordinary128", "resonance1", "resonance2", "split1", "split2", "split3",
                   "tuning1", "extension1", "extension2", "extension3", "all_max"]
    generated = []
    for bg_name, bg in (("dark", (22, 24, 34)), ("white", (246, 246, 246))):
        whole_path = OUTPUT / f"all-states-{bg_name}.png"
        make_state_board(images, state_order, bg_name, bg, whole_path)
        generated.append(whole_path)
        compact_path = OUTPUT / f"compact-tiers-{bg_name}.png"
        make_level_boards(images, bg_name, bg, compact_path)
        generated.append(compact_path)
        for module, states_in_module in {
            "resonance": ["ordinary128", "resonance1", "resonance2"],
            "split": ["ordinary128", "split1", "split2", "split3"],
            "extension": ["ordinary128", "extension1", "extension2", "extension3"],
            "tuning": ["ordinary128", "tuning1"],
        }.items():
            close_path = OUTPUT / f"{module}-component-closeup-{bg_name}.png"
            make_component_board(images, bounds, module, states_in_module, bg_name, bg, close_path)
            generated.append(close_path)

    manifest = {
        "schema": "root-pixel-render-review-v1",
        "status": "review-only",
        "inputPath": INPUT.relative_to(ROOT).as_posix(),
        "inputSha256": digest(raw),
        "ordinaryBaseState": base_name,
        "ordinaryBasePngSha256": state_report[base_name]["pngSha256"],
        "ordinaryAgainstSource64": ordinary_report,
        "motherReference": mother_report,
        "componentBounds128": {k: list(v) for k, v in bounds.items()},
        "states": state_report,
        "generatedFiles": [
            {"path": p.relative_to(ROOT).as_posix(), "sha256": digest(p.read_bytes())}
            for p in generated
        ],
        "notes": [
            "Every state PNG is written from the exact input RGBA byte matrix and read back for pixel equality.",
            "Transparent pixels with nonzero RGB are rejected; no source pixel is normalized or repaired.",
            "Close-up boxes are display crops only and do not define masks or alter state pixels; absent boxes use established native128 view windows.",
            "No candidate, source integration, build, or install is performed.",
        ],
    }
    (OUTPUT / "render-audit.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                                                encoding="utf-8")
    print("PASS: exact root pixel rendering; no source values changed")
    print(f"input SHA256: {digest(raw)}")
    print(f"ordinary base ({base_name}) PNG SHA256: {state_report[base_name]['pngSha256']}")
    print(f"ordinary exact against current source 2x-nearest: {ordinary_report['pixelExact']} ({ordinary_report['differentTexelCount']} differing texels)")
    print("mother reference:", {k: mother_report.get(k) for k in
          ("provided", "referenceSha256", "comparedState", "pixelExact", "differentTexelCount")})
    print("opaque connectivity (4/8 component counts):", {
        name: (len(state_report[name]["fourConnectedComponentSizes"]),
               len(state_report[name]["eightConnectedComponentSizes"]))
        for name in state_order
    })
    print(f"review output: {OUTPUT.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
