"""Static tier study derived only from the selected native 64px reference."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "artwork/source/echo-pickaxe-redesign-reference-v2"
OUT = ROOT / "artwork/validation/v0.1.11/redesign-v2/reference-master-final"
MASTER_PATH = SRC / "user-reference.png"
BUILDER_PATH = ROOT / "artwork/source/approved-reference-oct03-64/build_approved64_variants.py"
ORDINARY_PATH = ROOT / "src/main/resources/assets/echopickaxe/textures/item/echo_pickaxe.png"


def load_builder():
    spec = importlib.util.spec_from_file_location("approved64_masks_readonly", BUILDER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def mask_coords(mask):
    px = mask.load()
    return {(x, y) for y in range(64) for x in range(64) if px[x, y]}


def native_component_margins(tiers, ref, radius=1):
    """Attach one-pixel shaded/glint borders to their nearest authored tier."""
    alpha = ref.getchannel("A")
    expanded = {}
    for name, masks in tiers.items():
        cores = [mask_coords(m) for m in masks]
        owners = {}
        for tier_index, core in enumerate(cores):
            for x, y in core:
                for yy in range(max(0, y-radius), min(64, y+radius+1)):
                    for xx in range(max(0, x-radius), min(64, x+radius+1)):
                        if alpha.getpixel((xx, yy)) == 0 or max(abs(xx-x), abs(yy-y)) > radius:
                            continue
                        distance = (xx-x)**2 + (yy-y)**2
                        old = owners.get((xx, yy))
                        if old is None or (distance, tier_index) < old:
                            owners[(xx, yy)] = (distance, tier_index)
        groups = [set(core) for core in cores]
        for point, (_distance, index) in owners.items():
            groups[index].add(point)
        made=[]
        for group in groups:
            m=Image.new("L",(64,64)); mp=m.load()
            for x,y in group: mp[x,y]=255
            made.append(m)
        expanded[name]=made
    return expanded


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def is_dark_sculk(rgb):
    r, g, b = rgb
    # Keep the mother body's real blue/teal facet range, including subdued cyan.
    # Exclude only near-black silhouette pixels, bone, and activated module hues.
    return 22 <= max(rgb) <= 180 and r <= g + 28 and r <= b + 34 and not (g > r * 1.5 and b < g * .72)


def regional_sources(ref, forbidden, name):
    # Donor palette is drawn from the real native shaft facets, not ordinary art.
    p = ref.load()
    candidates = [(x, y) for y in range(24, 62) for x in range(8, 45)
                  if (x, y) not in forbidden and p[x, y][3] == 255 and is_dark_sculk(p[x, y][:3])]
    if not candidates:
        raise RuntimeError(f"No mother-image sculk donors for {name}")
    return candidates


def apply_underlay(state, ref, coords, sources, component):
    out, src = state.load(), ref.load()
    row_x = {}
    for y in sorted({y for _x,y in coords}):
        row_x[y] = sorted(x for x, yy in coords if yy == y)
    centers = {y: sum(xs) / len(xs) for y,xs in row_x.items() if xs}
    for x, y in coords:
        dx = x - centers.get(y, x)
        if component == "resonance":
            sy = round(36 + (y - 12) * .45)
            sx = round(64 - sy + dx * .72)
        elif component == "frequency":
            sy = round(29 + (y - 15) * .75)
            sx = round(64 - sy + dx * .68)
        elif component == "tuning":
            sy = round(36 + (y - 15) * .55)
            sx = round(64 - sy + dx * .65)
        else:
            sx, sy = round(17 + (x - 12) * .65), round(46 + (y - 53) * .65)
        # Sample the projected shaft row locally (at native texel scale). This keeps
        # its small dark/mid/cyan facets instead of collapsing a whole component onto
        # one nearest boundary donor.
        nearby = [q for q in sources if abs(q[0]-sx) <= 2 and abs(q[1]-sy) <= 2]
        pool = nearby or sources
        sx, sy = min(pool, key=lambda q: ((q[0]-sx)**2+(q[1]-sy)**2, q[1], q[0]))
        out[x, y] = (*src[sx, sy][:3], 255)


def body_cyan_palette(ref, forbidden):
    px = ref.load()
    vals = []
    for y in range(64):
        for x in range(64):
            r, g, b, a = px[x, y]
            if a and (x, y) not in forbidden and g > r * 1.8 and b > r * 1.6 and max(r, g, b) >= 90:
                vals.append((r, g, b))
    vals = list(dict.fromkeys(vals))
    return sorted(vals, key=lambda c: (max(c), c[1], c[2]))


def set_rgb(state, points, color):
    p = state.load()
    for x, y in points:
        if 0 <= x < 64 and 0 <= y < 64 and p[x, y][3]:
            p[x, y] = (*color, 255)


def draw_bare_blades(state, ref, res_mask, freq_mask, cyan, levels):
    # Small inset bone facets, discontinuous and confined to the two bare blades.
    bone = [(198, 193, 177), (226, 220, 201), (244, 238, 218)]
    left = [(21,10),(22,10),(22,11),(24,13),(25,13),(25,14),(27,15)]
    right = [(55,21),(56,21),(56,22),(58,29),(59,30),(59,31),(60,36),(60,37)]
    if levels["resonance"] == 0:
        for i, xy in enumerate(left):
            if xy in res_mask: set_rgb(state, [xy], bone[(i + 1) % len(bone)])
    if levels["frequency"] == 0:
        for i, xy in enumerate(right):
            if xy in freq_mask: set_rgb(state, [xy], bone[(i + 1) % len(bone)])
    # Only a few short native-size cyan joins continue existing mother-image veins.
    left_vein = [(28,8),(29,9),(30,9),(31,10),(32,10),(33,11)]
    right_vein = [(47,22),(48,23),(49,23),(50,24)]
    vein_colors = [(0,144,162),(0,174,186),(0,203,216),(0,156,175),(0,188,204)]
    for i, xy in enumerate(left_vein):
        if xy in res_mask:
            set_rgb(state, [xy], vein_colors[min(i, len(vein_colors)-1)])
    for i, xy in enumerate(right_vein):
        if xy in freq_mask:
            set_rgb(state, [xy], vein_colors[min(i+1, len(vein_colors)-1)])


def draw_extension_zero(state, ref, ext_coords, authored_ext_tiers, cyan):
    p = state.load()
    cx, cy = 12, 53
    # Recolor the mother eye's own rounded footprint into a faceted sculk/cyan core.
    eye_coords = set().union(*(mask_coords(m) for m in authored_ext_tiers[:2]))
    for x, y in eye_coords:
        if (x - cx) ** 2 + (y - cy) ** 2 > 18 or p[x, y][3] == 0:
            continue
        r, g, b, _ = ref.getpixel((x, y))
        lum = max(r, g, b)
        if (x, y) == (12, 52): c = (30, 157, 177)
        elif lum > 200: c = (4, 97, 118)
        elif g > r * 1.2: c = (2, min(155, int(g * .70)), min(178, int(g * .78 + b * .12)))
        else: c = (2, 48, 66)
        p[x, y] = (*c, 255)
    # Four separate short ivory clips are copied from the reference's own claw texels.
    claw = mask_coords(authored_ext_tiers[2])
    seeds = [(14, 46), (18, 50), (6, 54), (14, 58)]
    chosen = set()
    for sx, sy in seeds:
        nearby = sorted((q for q in claw if abs(q[0] - sx) + abs(q[1] - sy) <= 2),
                        key=lambda q: (abs(q[0] - sx) + abs(q[1] - sy), q[1], q[0]))
        chosen.update(nearby[:3])
    rp = ref.load()
    for x, y in chosen:
        if (x, y) in ext_coords:
            p[x, y] = rp[x, y]


def compose(ref, masks, authored_masks, levels, sources, cyan):
    state = ref.copy()
    unions = {name: set().union(*(mask_coords(mask) for mask in masks[name])) for name in masks}
    for name in ("resonance", "frequency", "tuning", "extension"):
        apply_underlay(state, ref, unions[name], sources[name], name)
    draw_bare_blades(state, ref, unions["resonance"], unions["frequency"], cyan, levels)
    if levels["extension"] == 0:
        draw_extension_zero(state, ref, unions["extension"], authored_masks["extension"], cyan)
    p, rp = state.load(), ref.load()
    for name, count in levels.items():
        for mask in masks[name][:count]:
            for x, y in mask_coords(mask):
                p[x, y] = rp[x, y]
    return state


def font(size):
    for path in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\arial.ttf"):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def board(cells, path, scale):
    margin, gap, label, sprite = 18, 18, 34, 64 * scale
    cols, rows = 5, (len(cells) + 4) // 5
    w = margin * 2 + cols * sprite + (cols - 1) * gap
    rowh = label + sprite + gap
    h = margin * 2 + rows * rowh
    out = Image.new("RGB", (w, h * 2), (235, 238, 241))
    d, f = ImageDraw.Draw(out), font(17)
    for theme, bg in enumerate(((255, 255, 255), (22, 27, 34))):
        for i, (title, image) in enumerate(cells):
            row, col = divmod(i, cols)
            x = margin + col * (sprite + gap)
            y = theme * h + margin + row * rowh
            d.text((x, y + 4), title, font=f, fill=(24, 30, 36) if theme == 0 else (235, 239, 243))
            shown = image.resize((sprite, sprite), Image.Resampling.NEAREST)
            tile = Image.new("RGBA", shown.size, (*bg, 255))
            tile.alpha_composite(shown)
            out.paste(tile.convert("RGB"), (x, y + label))
    out.save(path)


def small_board(cells, side, path):
    scale = 4
    margin, gap, label, sprite = 16, 12, 28, side * scale
    w = margin * 2 + 5 * sprite + 4 * gap
    hrow = label + sprite + gap
    out = Image.new("RGB", (w, margin * 2 + 2 * hrow), (235, 238, 241))
    d, f = ImageDraw.Draw(out), font(15)
    for theme, bg in enumerate(((255, 255, 255), (22, 27, 34))):
        for i, (title, im) in enumerate(cells):
            row, col = divmod(i, 5)
            x, y = margin + col * (sprite + gap), margin + theme * hrow + row * hrow
            d.text((x, y + 3), title, font=f, fill=(24, 30, 36) if theme == 0 else (235, 239, 243))
            shown = im.resize((side, side), Image.Resampling.NEAREST).resize((sprite, sprite), Image.Resampling.NEAREST)
            tile = Image.new("RGBA", shown.size, (*bg, 255)); tile.alpha_composite(shown)
            out.paste(tile.convert("RGB"), (x, y + label))
    out.save(path)


def main():
    SRC.mkdir(parents=True, exist_ok=True); OUT.mkdir(parents=True, exist_ok=True)
    ref = Image.open(MASTER_PATH).convert("RGBA")
    builder = load_builder()
    authored_tiers, _, authored_sets = builder.feature_masks(ref)
    if builder.residual_chromatic_features(ref, authored_sets) != {"red": [], "purple": [], "green": []}:
        raise RuntimeError("Feature masks leave residual chromatic module pixels")
    masks = native_component_margins(authored_tiers, ref, radius=1)
    sets = {k:set().union(*(mask_coords(m) for m in v)) for k,v in masks.items()}
    all_modules = set().union(*sets.values())
    sources = {k: regional_sources(ref, all_modules, k) for k in sets}
    cyan = body_cyan_palette(ref, all_modules)
    state_defs = [
        (4, "调谐 I", {"resonance":0,"frequency":0,"tuning":1,"extension":0}),
        (8, "分频 I", {"resonance":0,"frequency":1,"tuning":0,"extension":0}),
        (16, "分频 II", {"resonance":0,"frequency":2,"tuning":0,"extension":0}),
        (24, "分频 III", {"resonance":0,"frequency":3,"tuning":0,"extension":0}),
        (32, "共振 I", {"resonance":1,"frequency":0,"tuning":0,"extension":0}),
        (64, "共振 II", {"resonance":2,"frequency":0,"tuning":0,"extension":0}),
        (1, "延展 I", {"resonance":0,"frequency":0,"tuning":0,"extension":1}),
        (2, "延展 II", {"resonance":0,"frequency":0,"tuning":0,"extension":2}),
        (3, "延展 III", {"resonance":0,"frequency":0,"tuning":0,"extension":3}),
        (95, "全满级", {"resonance":2,"frequency":3,"tuning":1,"extension":3}),
    ]
    cells = []
    facts = []
    for index, name, levels in state_defs:
        im = compose(ref, masks, authored_tiers, levels, sources, cyan)
        if index == 95 and list(im.getdata()) != list(ref.getdata()):
            raise RuntimeError("All-max must equal the user master RGBA exactly")
        outpath = OUT / f"reference-master-v2-v{index:03d}-64.png"
        im.save(outpath)
        im.resize((32,32), Image.Resampling.NEAREST).save(OUT / f"reference-master-v2-v{index:03d}-32.png")
        im.resize((16,16), Image.Resampling.NEAREST).save(OUT / f"reference-master-v2-v{index:03d}-16.png")
        cells.append((f"v{index:03d} {name}", im))
        facts.append({"index":index,"name":name,"levels":levels,"sha256":sha(outpath)})
    original = ref.copy()
    ordinary = Image.open(ORDINARY_PATH).convert("RGBA")
    ordinary_label = ("普通未升级 32px", ordinary.resize((64,64), Image.Resampling.NEAREST))
    all_cells = [ordinary_label, ("母图原样 64px", original), *cells[:3], *cells[3:7], *cells[7:]]
    # Split 12 cells across 3 rows for a legible static tier/contact sheet.
    board(all_cells, OUT / "reference-master-v2-all-white-dark-4x.png", 4)
    # For compact state progression boards, five states per sheet with white and dark rows.
    board(cells[:5], OUT / "reference-master-v2-states-1-white-dark-4x.png", 4)
    board(cells[5:], OUT / "reference-master-v2-states-2-white-dark-4x.png", 4)
    small_board(cells, 32, OUT / "reference-master-v2-all-32px-white-dark.png")
    small_board(cells, 16, OUT / "reference-master-v2-all-16px-white-dark.png")
    ref.save(OUT / "user-reference-master-exact.png")
    record = {
        "status":"static reference-master redesign draft; no production assets modified",
        "master":"artwork/source/echo-pickaxe-redesign-reference-v2/user-reference.png",
        "masterSha256":sha(MASTER_PATH),
        "maskSource":"approved-reference-oct03-64/build_approved64_variants.py:feature_masks (read-only)",
        "generation":"Only master-native pixels and feature masks; inactive modules use nearest local dark-sculk donor RGB from the master outside all component masks. No old ordinary/source32 RGB, no tight draft/common_body, no random/tile texture.",
        "states":facts,
        "ordinary":"Read-only 32px comparison from current source resources; not changed or sampled for upgraded states.",
        "checks":{"v095RgbaExactMaster":True,"allStatesSameMasterAlpha":True,"allStatesAlphaBinary":True,"productionUntouched":True}
    }
    (OUT / "reference-master-v2-static-map.json").write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"out":str(OUT),"boards":["reference-master-v2-all-white-dark-4x.png","reference-master-v2-states-1-white-dark-4x.png","reference-master-v2-states-2-white-dark-4x.png","reference-master-v2-all-32px-white-dark.png","reference-master-v2-all-16px-white-dark.png"],"cyanPalette":cyan,"donors":{k:len(v) for k,v in sources.items()}},ensure_ascii=False))


if __name__ == "__main__":
    main()
