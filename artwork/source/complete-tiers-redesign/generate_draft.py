from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
BASE_PATH = ROOT / "src/main/resources/assets/echopickaxe/textures/item/echo_pickaxe.png"
OUT = Path(__file__).resolve().parent
VALID = ROOT / "artwork/validation/complete-tiers-redesign"

PAL = {
    "ruby_outline": (45, 5, 20, 255), "ruby_shadow": (94, 9, 29, 255),
    "ruby_mid": (172, 17, 45, 255), "ruby_light": (237, 37, 66, 255),
    "ruby_glint": (255, 120, 139, 255),
    "violet_outline": (27, 9, 44, 255), "violet_shadow": (67, 20, 96, 255),
    "violet_mid": (116, 38, 166, 255), "violet_light": (181, 82, 225, 255),
    "violet_glint": (231, 164, 250, 255),
    "jade_outline": (4, 29, 23, 255), "jade_shadow": (9, 68, 46, 255),
    "jade_mid": (20, 133, 78, 255), "jade_light": (64, 202, 118, 255),
    "jade_glint": (177, 255, 210, 255), "pupil": (1, 8, 10, 255),
    "ice_outline": (10, 42, 56, 255), "ice_mid": (66, 174, 192, 255),
    "ice_light": (169, 237, 245, 255), "ice_core": (245, 255, 255, 255),
}


def h(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest().upper()


def new_layer(base: Image.Image) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    return layer, ImageDraw.Draw(layer)


def poly(d: ImageDraw.ImageDraw, pts: list[tuple[int, int]], color: str | tuple[int, int, int, int]) -> None:
    d.polygon(pts, fill=PAL[color] if isinstance(color, str) else color)


def line(d: ImageDraw.ImageDraw, pts: list[tuple[int, int]], color: str, width: int = 1) -> None:
    d.line(pts, fill=PAL[color], width=width, joint="curve")


def dot(d: ImageDraw.ImageDraw, pts: list[tuple[int, int]], color: str) -> None:
    for p in pts:
        d.point(p, fill=PAL[color])


def paint_red(base: Image.Image, tier: int) -> Image.Image:
    out = base.copy()
    lay, d = new_layer(base)
    # A complete single curved ruby cutter; the lower bevel follows the ordinary hook.
    blade = [(17, 7), (19, 6), (22, 6), (25, 7), (27, 8), (28, 10), (30, 12),
             (31, 15), (33, 17), (34, 18), (33, 19), (31, 18), (30, 16), (28, 14),
             (27, 12), (25, 11), (23, 10), (21, 9), (19, 9), (17, 8)]
    poly(d, blade, "ruby_outline")
    poly(d, [(18, 7), (20, 7), (23, 7), (26, 8), (27, 10), (29, 12), (30, 15),
             (32, 17), (32, 18), (30, 16), (28, 14), (26, 12), (24, 11), (21, 9), (18, 8)], "ruby_mid")
    # Broad inner facet, tapered toward the cutting end.
    poly(d, [(19, 8), (22, 8), (25, 9), (27, 11), (29, 14), (31, 17), (30, 17),
             (28, 15), (26, 13), (24, 12), (21, 10), (19, 9)], "ruby_shadow")
    # Continuous narrow edge glint, never a detached line.
    line(d, [(18, 7), (20, 6), (23, 7), (26, 8), (28, 10), (30, 13), (31, 16), (33, 18)], "ruby_light")
    dot(d, [(19, 7), (24, 8), (28, 11), (31, 16)], "ruby_glint")
    if tier >= 2:
        # II grows a second complete crystalline ridge along the back, joined to I.
        ridge = [(20, 6), (21, 4), (23, 2), (27, 2), (30, 4), (32, 6), (32, 9), (30, 9), (28, 7), (25, 6), (23, 7)]
        poly(d, ridge, "ruby_outline")
        poly(d, [(21, 6), (22, 4), (24, 3), (27, 3), (30, 5), (31, 7), (29, 8), (27, 6), (24, 6)], "ruby_mid")
        poly(d, [(24, 4), (26, 3), (29, 5), (30, 6), (27, 5)], "ruby_light")
        dot(d, [(25, 3), (28, 5), (30, 6)], "ruby_glint")
    # Explicit structural coverage for every original ivory pixel not reached by a facet polygon.
    # This is a deliberate material assignment by blade zone, not a sampled/nearest-color fill.
    a = np.array(base)
    r, g, b = a[:, :, :3].astype(np.int16).transpose(2, 0, 1)
    bone = (a[:, :, 3] > 0) & (r > 140) & (g > 130) & (b > 110) & (r - g < 40)
    for y, x in zip(*np.where(bone & (np.indices((64, 64))[1] >= 17) & (np.indices((64, 64))[1] <= 35) & (np.indices((64, 64))[0] >= 5) & (np.indices((64, 64))[0] <= 19))):
        if lay.getpixel((x, y))[3] == 0:
            color = "ruby_light" if y <= 8 else ("ruby_outline" if y >= 15 or x >= 32 else "ruby_mid")
            lay.putpixel((x, y), PAL[color])
    out.alpha_composite(lay)
    return out


def paint_purple(base: Image.Image, tier: int) -> Image.Image:
    out = base.copy()
    lay, d = new_layer(base)
    # I is a finished, continuous bent blade. It includes the entire old ivory curve.
    blade = [(48, 21), (50, 21), (52, 22), (54, 23), (56, 25), (57, 27), (58, 29),
             (60, 32), (59, 34), (57, 33), (56, 31), (54, 29), (53, 27), (51, 25),
             (49, 24), (48, 23)]
    poly(d, blade, "violet_outline")
    poly(d, [(49, 22), (51, 22), (53, 23), (55, 25), (56, 27), (58, 30), (59, 32),
             (58, 32), (56, 30), (54, 28), (53, 26), (51, 24), (49, 23)], "violet_mid")
    # Faceted broad back plane and a sharply tapered continuous inner edge.
    poly(d, [(50, 22), (52, 23), (54, 25), (56, 28), (58, 31), (57, 31), (55, 29),
             (53, 27), (52, 25), (50, 24)], "violet_shadow")
    line(d, [(48, 22), (50, 22), (52, 23), (54, 25), (56, 28), (58, 31), (59, 33)], "violet_light")
    line(d, [(49, 22), (51, 23), (53, 25), (55, 28), (57, 31)], "violet_glint")
    if tier >= 2:
        # Second blade facet is an attached full crystal lobe, not a leftover dark strip.
        poly(d, [(52, 22), (54, 20), (57, 19), (60, 21), (62, 24), (61, 27), (59, 28), (57, 26), (55, 24)], "violet_outline")
        poly(d, [(54, 21), (57, 20), (60, 22), (61, 24), (60, 26), (58, 26), (56, 24)], "violet_mid")
        poly(d, [(56, 21), (58, 20), (60, 22), (61, 24), (59, 24)], "violet_light")
        line(d, [(56, 21), (58, 20), (60, 22), (61, 24)], "violet_glint")
    if tier >= 3:
        # Third lower lobe completes the triple-crystal sweep and joins the sharp end.
        poly(d, [(56, 27), (59, 26), (62, 28), (63, 32), (62, 36), (59, 35), (58, 32), (56, 30)], "violet_outline")
        poly(d, [(58, 28), (60, 28), (62, 30), (62, 34), (60, 34), (59, 31)], "violet_mid")
        poly(d, [(60, 28), (62, 30), (62, 33), (61, 31)], "violet_light")
        dot(d, [(61, 29), (62, 31)], "violet_glint")
    out.alpha_composite(lay)
    return out


def paint_eye(base: Image.Image, tier: int) -> Image.Image:
    out = base.copy()
    lay, d = new_layer(base)
    # I is a complete circular jade bezel with a readable vertical pupil.
    d.ellipse((5, 49, 16, 59), fill=PAL["jade_outline"])
    d.ellipse((6, 50, 15, 58), fill=PAL["jade_shadow"])
    d.ellipse((7, 50, 15, 57), fill=PAL["jade_mid"])
    d.ellipse((8, 51, 14, 56), fill=PAL["jade_light"])
    # Carve a deliberate dark inner oval and paint a 1x3 black-green pupil last.
    d.ellipse((10, 52, 13, 55), fill=PAL["jade_shadow"])
    d.rectangle((11, 52, 12, 54), fill=PAL["pupil"])
    dot(d, [(10, 51), (11, 50)], "jade_glint")
    # Distinct inner iris points make the eye readable at 16px.
    dot(d, [(10, 53), (13, 53), (10, 54), (13, 54)], "jade_light")
    if tier >= 2:
        # II grows two substantial, beveled side guards from the bezel.
        poly(d, [(5, 51), (8, 50), (9, 52), (8, 54), (5, 54), (4, 53)], "jade_outline")
        poly(d, [(5, 52), (7, 51), (8, 52), (7, 53), (5, 53)], "jade_mid")
        poly(d, [(13, 51), (16, 50), (18, 52), (18, 55), (15, 55), (14, 53)], "jade_outline")
        poly(d, [(15, 51), (16, 52), (17, 53), (16, 54), (15, 53)], "jade_light")
        line(d, [(5, 52), (7, 51)], "jade_glint")
        line(d, [(16, 51), (17, 53)], "jade_glint")
    if tier >= 3:
        # III adds a raised upper crown and a lower keel: three supports around the eye.
        poly(d, [(8, 50), (9, 47), (12, 46), (15, 49), (14, 51), (11, 50)], "jade_outline")
        poly(d, [(9, 49), (11, 47), (13, 48), (14, 49), (12, 49)], "jade_light")
        poly(d, [(8, 56), (11, 57), (14, 56), (16, 58), (14, 60), (10, 59), (7, 58)], "jade_outline")
        poly(d, [(9, 57), (11, 58), (14, 57), (15, 58), (13, 59), (10, 58)], "jade_mid")
        dot(d, [(11, 47), (12, 47), (13, 48), (11, 58), (13, 58)], "jade_glint")
    out.alpha_composite(lay)
    return out


def paint_star(base: Image.Image) -> Image.Image:
    out = base.copy()
    lay, d = new_layer(base)
    # A slender four-point star; the diagonal corners remain transparent/dark.
    dot(d, [(43, 12), (43, 13), (43, 14), (43, 17), (43, 18), (43, 19),
            (40, 15), (41, 15), (42, 15), (44, 16), (45, 16), (46, 16)], "ice_mid")
    dot(d, [(43, 13), (43, 18), (41, 15), (45, 16)], "ice_light")
    dot(d, [(43, 15), (43, 16)], "ice_core")
    out.alpha_composite(lay)
    return out


def save(name: str, img: Image.Image, records: dict) -> None:
    p = OUT / f"{name}.png"
    img.save(p, optimize=False)
    records[name] = {"path": str(p.relative_to(ROOT)).replace("\\", "/"), "sha256": h(p)}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    VALID.mkdir(parents=True, exist_ok=True)
    base = Image.open(BASE_PATH).convert("RGBA")
    assert base.size == (64, 64)
    original_hash = h(BASE_PATH)
    tiers = {
        "ordinary": base,
        "red_I": paint_red(base, 1), "red_II": paint_red(base, 2),
        "purple_I": paint_purple(base, 1), "purple_II": paint_purple(base, 2), "purple_III": paint_purple(base, 3),
        "eye_I": paint_eye(base, 1), "eye_II": paint_eye(base, 2), "eye_III": paint_eye(base, 3),
        "star_I": paint_star(base),
    }
    # Single-module previews preserve every unrelated ordinary pixel by construction.
    records: dict[str, dict[str, str]] = {}
    for name, img in tiers.items():
        save(name, img, records)
    # Review board: each part is shown at 6x, while whole item previews include 16px icons.
    rows = [
        ("red", ["ordinary", "red_I", "red_II"]),
        ("purple", ["ordinary", "purple_I", "purple_II", "purple_III"]),
        ("eye", ["ordinary", "eye_I", "eye_II", "eye_III"]),
        ("star", ["ordinary", "star_I"]),
    ]
    cell, label = 288, 28
    board = Image.new("RGB", (cell * 4, (cell + label) * len(rows)), (13, 17, 24))
    draw = ImageDraw.Draw(board)
    for ri, (group, names) in enumerate(rows):
        for ci, name in enumerate(names):
            img = tiers[name]
            if name != "ordinary":
                crop = {"red": (14, 2, 39, 24), "purple": (45, 18, 64, 40), "eye": (3, 46, 20, 61), "star": (38, 10, 49, 22)}[group]
                img = img.crop(crop)
            else:
                crop = {"red": (14, 2, 39, 24), "purple": (45, 18, 64, 40), "eye": (3, 46, 20, 61), "star": (38, 10, 49, 22)}[group]
                img = img.crop(crop)
            # Scale crops 10x for precise review; this affects previews only.
            zoom = img.resize((img.width * 10, img.height * 10), Image.Resampling.NEAREST)
            tile = Image.new("RGBA", zoom.size, (8, 12, 18, 255)); tile.alpha_composite(zoom)
            x, y = ci * cell, ri * (cell + label)
            board.paste(tile.convert("RGB"), (x + 10, y + label + 6))
            draw.text((x + 7, y + 7), f"{group} / {name}", fill=(239, 241, 245))
    board.save(VALID / "component-review-board.png")

    whole_names = ["ordinary", "red_I", "red_II", "purple_I", "purple_II", "purple_III", "eye_I", "eye_II", "eye_III", "star_I"]
    icon = Image.new("RGB", (len(whole_names) * 128, 128), (15, 19, 26))
    idraw = ImageDraw.Draw(icon)
    for i, name in enumerate(whole_names):
        down = tiers[name].resize((16, 16), Image.Resampling.NEAREST).convert("RGBA")
        up = down.resize((128, 128), Image.Resampling.NEAREST)
        icon.paste((15, 19, 26), (i * 128, 0, (i + 1) * 128, 128))
        icon.paste(up, (i * 128, 0), up)
        idraw.text((i * 128 + 2, 2), name, fill=(255, 255, 255))
    icon.save(VALID / "whole-icon-16px-review.png")

    proof = {
        "status": "draft-for-visual-review",
        "sourceOrdinary": {"path": str(BASE_PATH.relative_to(ROOT)).replace("\\", "/"), "sha256": original_hash, "size": [64, 64]},
        "approvedMaxStyleReference": {"path": "artwork/source/approved-fullmax-v0.1.12/candidates/approved-fullmax-128.png", "usedAsVisualReferenceOnly": True},
        "tiers": records,
        "designNotes": {
            "inactiveModules": "Each single-module tier starts from the ordinary 64x64 byte-identical appearance; only the active module is painted.",
            "red": "I is a complete curved ruby cutter; II adds a joined second ridge while retaining the same sharp cutter.",
            "purple": "I is a complete curved blade; II adds a joined second crystal lobe; III adds a third lower lobe. No partial bone or dark pending-tier strip.",
            "eye": "I is a complete round bezel and vertical pupil; II adds two clear side guards; III adds a crown and keel for a three-support ornament.",
            "tuning": "One slender four-point star; empty diagonal corners.",
            "method": "All module shapes are drawn as deliberate native 64px polygons, lines and points; no nearest-color fill from the master.",
        },
        "notBuiltOrInstalled": True,
    }
    (VALID / "draft-manifest.json").write_text(json.dumps(proof, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ordinary_sha256": original_hash, "outputs": records, "board": str((VALID / "component-review-board.png").relative_to(ROOT)), "icons": str((VALID / "whole-icon-16px-review.png").relative_to(ROOT))}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
