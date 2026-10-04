"""Native64 visual draft for the 0.1.10 hook, right blade and full haft."""
import hashlib
import importlib.util
import io
import json
import math
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
JAR = ROOT / 'jaysay-echo-tools-0.1.9.jar'
JAR_SHA = 'BB7136E6B343E7371A161E3A6D27A9A81311F9850C54FA0C6DA41FB17FA430B6'
ORDINARY = ROOT / 'jaysay-echo-tools-0.1.2.jar'
ORDINARY_SHA = '7312AE7B54F3DAD998815B7C7BD601B65DB1BED23A21CC7AA8448E40E082F495'
COMPONENTS = ROOT / 'artwork/source/approved-reference-oct03-64/native64-component-map.json'
HELPER = ROOT / 'artwork/source/echo-pickaxe-native-edge-v0.1.8/build_native_edge_candidate.py'
PREVIEW = ROOT / 'artwork/source/echo-pickaxe-unified-head-v0.1.6/build_unified_head_candidate.py'
OUT = ROOT / 'artwork/validation/v0.1.10/draft'
PREFIX = 'assets/echopickaxe/'

# Flatten the abrupt inward shelf into a sequence of short 1px steps. These
# coordinates are confined to the res0 left hook; resonance-positive heads stay intact.
LEFT_REMOVE = ({(x, 18) for x in range(17, 22)} | {(23, 18)} |
               {(x, 17) for x in range(18, 32)} |
               {(x, 16) for x in range(25, 30)} |
               {(x, 15) for x in range(29, 32)})
LEFT_ADD = set()
LEFT_BONE = {
    (16, 18): (176, 172, 159), (15, 19): (230, 224, 210),
    (14, 20): (193, 190, 176), (13, 21): (166, 164, 155),
    (12, 22): (215, 210, 196), (11, 23): (154, 155, 148),
}

# The natural right blade has a broad lower bone slab. Narrow its lower contour
# one native pixel at a time and facet only pixels not occupied by an upgrade overlay.
RIGHT_REMOVE = {(59, y) for y in range(31, 36)} | {(58, 34), (58, 35)}
RIGHT_FACETS = {
    # Break the remaining paired 2px cyan shoulder into a dark ridge and a
    # short, stepped vein. Keep its bright source hue; only split its broad face.
    (52, 20): (10, 35, 49), (53, 20): (4, 25, 38),
    (52, 21): (16, 57, 70), (53, 21): (6, 32, 45),
    (52, 22): (5, 35, 49), (53, 22): (1, 101, 111),
    (52, 23): (3, 29, 43), (53, 23): (0, 165, 172),
    (52, 24): (7, 42, 55), (53, 24): (3, 27, 41),
    (52, 25): (8, 38, 52), (53, 25): (4, 27, 41),
    (52, 26): (4, 29, 43), (53, 26): (14, 63, 75),
    (56, 21): (231, 225, 209), (56, 22): (221, 215, 201), (57, 22): (177, 175, 165),
    (56, 23): (188, 187, 178), (57, 23): (216, 210, 197),
    (54, 24): (8, 26, 39), (55, 24): (19, 48, 62), (56, 24): (11, 31, 45),
    (57, 24): (14, 48, 63), (58, 24): (8, 27, 38),
    (54, 25): (12, 34, 48), (55, 25): (22, 63, 78), (56, 25): (8, 23, 36),
    (57, 25): (17, 52, 66), (58, 25): (8, 28, 41),
    (54, 26): (12, 40, 55), (55, 26): (15, 55, 67), (56, 26): (8, 23, 36),
    (57, 26): (23, 95, 110), (58, 26): (8, 25, 38),
    (54, 27): (8, 22, 34), (55, 27): (22, 59, 74), (56, 27): (10, 32, 47),
    (57, 27): (23, 99, 112), (58, 27): (7, 22, 34),
    (56, 28): (10, 28, 41), (57, 28): (17, 47, 60), (58, 28): (125, 129, 123),
    (56, 29): (8, 24, 37), (57, 29): (19, 51, 64), (58, 29): (188, 187, 176),
    (56, 30): (12, 30, 43), (57, 30): (161, 160, 151), (58, 30): (76, 88, 91),
    (56, 31): (10, 27, 40), (57, 31): (207, 201, 187), (58, 31): (110, 117, 113),
    (56, 32): (12, 29, 42), (57, 32): (153, 154, 146), (58, 32): (18, 37, 48),
    (56, 33): (196, 191, 178), (57, 33): (62, 76, 82),
    (56, 34): (148, 149, 141), (57, 34): (16, 34, 44),
    (56, 35): (91, 101, 100), (57, 35): (7, 22, 34),
}

# Smooth dark facets for the full shaft, sampled in a native local frame rather
# than stretched/copied from a 32px sprite. Each row is a deliberate nonuniform facet map.
SHAFT_PATH = [(44, 18), (41, 21), (38, 24), (35, 27), (32, 30),
              (29, 33), (26, 36), (23, 39), (20, 42), (17, 45),
              (14, 48), (11, 51), (9, 53)]
FACET_ROWS = [
    'DdBbBdD', 'dDbBbdD', 'DdbMbdD', 'ddBdbdD', 'DdbbMdd', 'ddBbdDd',
    'DdbMbbD', 'dDbbBdd', 'ddBbMdd', 'DdbbBdD', 'dDbMbdD', 'DdBbMdd',
    'ddBbdDd', 'DdbMbbD', 'dDbbBdd', 'ddBbMdd', 'DdbbBdD', 'dDbMbdD',
    'DdBbMdd', 'ddBbdDd', 'DdbMbbD', 'dDbbBdd', 'ddBbMdd', 'DdbbBdD',
    'dDbMbdD', 'DdBbMdd', 'ddBbdDd', 'DdbMbbD', 'dDbbBdd', 'ddBbMdd',
    'DdbbBdD', 'dDbMbdD', 'DdBbMdd', 'ddBbdDd',
]
FACET_PALETTE = {
    'D': (5, 13, 23), 'd': (12, 26, 41), 'b': (19, 39, 55),
    'B': (27, 55, 71), 'M': (36, 71, 85),
}
CRACKS = [
    [(42, 20), (41, 21), (40, 22)],
    [(37, 25), (36, 26), (35, 27)],
    [(32, 30), (31, 31), (30, 32), (29, 33)],
    [(27, 35), (26, 36), (25, 37), (24, 38)],
    [(22, 40), (21, 41), (20, 42), (19, 43)],
    [(17, 45), (16, 46), (15, 47), (14, 48)],
    [(12, 50), (11, 51), (10, 52)],
]
BRANCHES = [(40, 22), (39, 23), (35, 27), (34, 26), (29, 33), (28, 34),
            (24, 38), (23, 39), (20, 42), (19, 41), (15, 47), (13, 49)]
CRACK_PALETTE = [(28, 139, 153), (45, 172, 181), (22, 105, 121), (56, 188, 191)]

# Two short bone cross-bands and a diagonal endcap. The lower silhouette closes
# toward the left-down shaft axis instead of hanging vertically as a white tooth.
GRIP_FACETS = {
    (14, 48): (149, 150, 141), (13, 49): (223, 218, 204), (12, 50): (126, 129, 121),
    (10, 51): (133, 136, 128), (9, 52): (228, 222, 207), (8, 53): (144, 146, 137),
    (8, 55): (33, 55, 69), (9, 55): (19, 40, 54), (10, 55): (12, 27, 40),
    (8, 56): (185, 180, 167), (9, 56): (226, 220, 205), (10, 56): (116, 121, 114),
    (7, 57): (165, 166, 157), (8, 57): (220, 215, 200), (9, 57): (65, 76, 79),
    (7, 58): (117, 122, 115), (8, 58): (168, 169, 158),
}
GRIP_REMOVE = {(6, 55), (7, 55), (7, 56), (7, 57), (11, 57),
               (9, 58), (10, 58), (11, 58), (9, 59), (10, 59), (11, 59), (10, 60), (11, 60)}
GRIP_ADD = {(7, 58)}

STATES = [(24, '分频III / res0'), (4, '调谐I / res0'), (32, '仅共振I'),
          (3, '延展III / res0'), (95, '全满级')]


def sha(data):
    return hashlib.sha256(data).hexdigest().upper()


def read_png(data):
    return Image.open(io.BytesIO(data)).convert('RGBA')


def load_helper(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def font(size):
    for path in (r'C:\Windows\Fonts\msyh.ttc', r'C:\Windows\Fonts\arial.ttf'):
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def composite(image, background):
    result = Image.new('RGBA', image.size, background + (255,))
    result.alpha_composite(image)
    return result.convert('RGB')


def active_module_pixels(index, component_doc):
    res = index // 32
    remainder = index % 32
    frequency, tuning, extension = remainder // 8, (remainder % 8) // 4, remainder % 4
    levels = {'resonance': res, 'frequency': frequency, 'tuning': tuning, 'extension': extension}
    active = set()
    for name, level in levels.items():
        for tier in component_doc['components'][name]['tiers']:
            if tier['level'] <= level:
                active.update((t[0], t[1]) for t in tier['texels'])
    return active


def nearest_path_position(x, y):
    best = None
    distance_before = 0.0
    for (x0, y0), (x1, y1) in zip(SHAFT_PATH, SHAFT_PATH[1:]):
        vx, vy = x1 - x0, y1 - y0
        length2 = vx * vx + vy * vy
        t = max(0.0, min(1.0, ((x - x0) * vx + (y - y0) * vy) / length2))
        px, py = x0 + t * vx, y0 + t * vy
        dx, dy = x - px, y - py
        dist = math.hypot(dx, dy)
        seg_len = math.sqrt(length2)
        along = distance_before + t * seg_len
        signed = (vx * dy - vy * dx) / seg_len
        if best is None or dist < best[0]:
            best = (dist, along, signed)
        distance_before += seg_len
    return best


def shaft_texture(x, y, active_modules):
    dist, along, signed = nearest_path_position(x, y)
    if dist > 3.1 or not (24 <= y <= 54) or x > 36 or (x, y) in active_modules:
        return None
    row = FACET_ROWS[int(round(along)) % len(FACET_ROWS)]
    u = max(-3, min(3, int(round(signed))))
    return FACET_PALETTE[row[u + 3]]


def edit_sprite(index, old, component_doc):
    out = old.copy()
    active = active_module_pixels(index, component_doc)
    edits, removed, added = set(), set(), set()
    is_res0 = 1 <= index <= 31

    if is_res0:
        for p in LEFT_REMOVE:
            if out.getpixel(p)[3]:
                out.putpixel(p, (0, 0, 0, 0)); removed.add(p); edits.add(p)
        for p in LEFT_ADD:
            if not out.getpixel(p)[3]:
                out.putpixel(p, (8, 19, 31, 255)); added.add(p); edits.add(p)
        for p, rgb in LEFT_BONE.items():
            if out.getpixel(p)[3] and p not in active:
                out.putpixel(p, (*rgb, 255)); edits.add(p)

    # Refine the right natural blade in every upgraded appearance. Active
    # component texels (including purple crystals) are left byte/pixel exact.
    for p in RIGHT_REMOVE:
        if p not in active and out.getpixel(p)[3]:
            out.putpixel(p, (0, 0, 0, 0)); removed.add(p); edits.add(p)
    for p, rgb in RIGHT_FACETS.items():
        if p not in active and out.getpixel(p)[3]:
            out.putpixel(p, (*rgb, 255)); edits.add(p)

    # Repaint the complete diagonal haft with layered dark-blue facets, then
    # draw a few broken fissure segments in its longitudinal grain.
    for y in range(24, 55):
        for x in range(5, 38):
            if not out.getpixel((x, y))[3] or (x, y) in active:
                continue
            rgb = shaft_texture(x, y, active)
            if rgb is not None:
                out.putpixel((x, y), (*rgb, 255)); edits.add((x, y))
    for path in CRACKS:
        for i, p in enumerate(path):
            if out.getpixel(p)[3] and p not in active:
                rgb = CRACK_PALETTE[(i + p[1]) % len(CRACK_PALETTE)]
                out.putpixel(p, (*rgb, 255)); edits.add(p)
    for i, p in enumerate(BRANCHES):
        if out.getpixel(p)[3] and p not in active:
            out.putpixel(p, (22, 91 + (i % 2) * 16, 105 + (i % 2) * 15, 255)); edits.add(p)

    # Reprofile the bottom edge into a short diagonal cap. The active eye/ring
    # map is protected, so extension variants retain every ornament texel.
    for p in GRIP_REMOVE:
        if p not in active and out.getpixel(p)[3]:
            out.putpixel(p, (0, 0, 0, 0)); removed.add(p); edits.add(p)
    for p in GRIP_ADD:
        if p not in active and not out.getpixel(p)[3]:
            out.putpixel(p, (12, 27, 40, 255)); added.add(p); edits.add(p)
    for p, rgb in GRIP_FACETS.items():
        if out.getpixel(p)[3] and p not in active:
            out.putpixel(p, (*rgb, 255)); edits.add(p)
    return out, edits, removed, added


def save_board(states, path, crop=None, scale=4):
    width, height = (crop[2] - crop[0], crop[3] - crop[1]) if crop else (64, 64)
    sprite_w, sprite_h, label_h, margin = width * scale, height * scale, 28, 10
    cell_w, cell_h = sprite_w + 12, sprite_h + label_h + 6
    board = Image.new('RGB', (margin * 2 + cell_w * len(states), margin * 2 + 2 * cell_h), (239, 242, 245))
    draw = ImageDraw.Draw(board)
    for row, bg in enumerate(((255, 255, 255), (24, 30, 38))):
        y = margin + row * cell_h
        draw.text((4, y + 4), '白底' if row == 0 else '暗底', font=font(14), fill=(25, 30, 36))
        for col, (label, image) in enumerate(states):
            x = margin + col * cell_w
            draw.text((x + 2, y + 2), label, font=font(14), fill=(25, 30, 36))
            source = image.crop(crop) if crop else image
            source = source.resize((sprite_w, sprite_h), Image.Resampling.NEAREST)
            board.paste(composite(source, bg), (x, y + label_h))
    board.save(path)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    jar_data, ordinary_data = JAR.read_bytes(), ORDINARY.read_bytes()
    assert sha(jar_data) == JAR_SHA and sha(ordinary_data) == ORDINARY_SHA
    component_doc = json.loads(COMPONENTS.read_text(encoding='utf-8'))
    geometry = load_helper(HELPER, 'geometry_ends_draft')
    preview = load_helper(PREVIEW, 'preview_ends_draft')
    old_states, new_states = [], []
    change_report = {}
    with zipfile.ZipFile(io.BytesIO(jar_data)) as archive, zipfile.ZipFile(io.BytesIO(ordinary_data)) as ordinary:
        for index, label in STATES:
            old = read_png(archive.read(PREFIX + f'textures/item/echo_pickaxe_v{index:03d}.png'))
            glow = read_png(archive.read(PREFIX + f'textures/item/echo_pickaxe_v{index:03d}_glow.png'))
            old_model = json.loads(archive.read(PREFIX + f'models/item/echo_pickaxe_v{index:03d}.json').decode('utf-8'))
            new, edits, removed, added = edit_sprite(index, old, component_doc)
            alpha_old, alpha_new = geometry.opaque(old), geometry.opaque(new)
            actual_removed, actual_added = alpha_old - alpha_new, alpha_new - alpha_old
            assert actual_removed == removed and actual_added == added
            lit = geometry.opaque(glow.crop((0, 0, 64, 64)))
            expected, _, expected_lit = load_helper(ROOT / 'artwork/source/approved-reference-oct03-64/build_approved64_variants.py', 'modelhelper_ends_draft').model_for_state(
                old_model, f'echo_pickaxe_v{index:03d}', new, lit)
            model, _ = geometry.update_model_preserving_geometry(old_model, expected, removed, added, removed | added)
            old_states.append((label + '｜原0.1.9', preview.frontface(old, glow, old_model, 0)))
            new_states.append((label + '｜新稿', preview.frontface(new, glow, model, 0)))
            new.save(OUT / f'v{index:03d}-0.1.10-native64-draft.png')
            change_report[str(index)] = {'rgbOrAlphaTexels': len(edits), 'alphaRemoved': sorted(map(list, removed)),
                                         'alphaAdded': sorted(map(list, added)),
                                         'activeComponentMaskProtected': True}
        ordinary_sprite = read_png(ordinary.read(PREFIX + 'textures/item/echo_pickaxe.png'))
        ordinary_glow = read_png(ordinary.read(PREFIX + 'textures/item/echo_pickaxe_glow.png'))
        ordinary_model = json.loads(ordinary.read(PREFIX + 'models/item/echo_pickaxe.json').decode('utf-8'))
        old_states.insert(0, ('普通0.1.2原版', preview.frontface(ordinary_sprite, ordinary_glow, ordinary_model, 0)))
        new_states.insert(0, ('普通0.1.2原版', preview.frontface(ordinary_sprite, ordinary_glow, ordinary_model, 0)))

    for name, states in (('whole', new_states),):
        save_board(states, OUT / 'v0.1.10-refined-ends-whole-white-dark.png', scale=4)
    for name, states in (('transition', new_states), ('transition-before', old_states)):
        save_board(states, OUT / f'v0.1.10-left-transition-{name}-12x-white-dark.png', (7, 8, 31, 29), 12)
    save_board(new_states, OUT / 'v0.1.10-right-tip-12x-white-dark.png', (51, 17, 64, 40), 12)
    save_board(old_states, OUT / 'v0.1.9-right-tip-before-12x-white-dark.png', (51, 17, 64, 40), 12)
    save_board(new_states, OUT / 'v0.1.10-whole-shaft-handle-8x-white-dark.png', (8, 24, 44, 63), 8)
    save_board(old_states, OUT / 'v0.1.9-whole-shaft-handle-before-8x-white-dark.png', (8, 24, 44, 63), 8)
    save_board(new_states, OUT / 'v0.1.10-bone-grip-endcap-12x-white-dark.png', (4, 45, 22, 63), 12)

    report = {
        'status': 'visual-draft-only-awaiting-root-review', 'baselineJar': JAR.name,
        'baselineJarSha256': JAR_SHA, 'ordinary012Sha256': ORDINARY_SHA,
        'designSummary': 'Keep the native curved outline; step the res0 hook inner turn, extend the bone facet edge, refine the exposed right blade in every state while preserving active crystal pixels, repaint the actual full-length shaft in dark layered sculk facets with narrow broken cyan veins, and close the butt as a short left-down ferrule cap with two slim bone cross-bands. Extension eye/ring overlay pixels remain exact.',
        'editScopes': {'leftHook': 'indices 001..031 only', 'rightBlade': 'indices 001..095, active resonance/frequency/tuning overlay texels protected per component map',
                       'shaftAndGrip': 'indices 001..095, component pixels protected by active tier; green eye/slanted ring exact'},
        'shaftPath': [list(p) for p in SHAFT_PATH],
        'removedAlpha': {'leftHook': sorted(map(list, LEFT_REMOVE)), 'rightBlade': sorted(map(list, RIGHT_REMOVE)),
                         'gripProfile': sorted(map(list, GRIP_REMOVE))},
        'addedAlpha': {'leftHook': sorted(map(list, LEFT_ADD))},
        'changeCounts': change_report,
        'previews': [f'artwork/validation/v0.1.10/draft/{p}' for p in (
            'v0.1.10-refined-ends-whole-white-dark.png',
            'v0.1.10-left-transition-transition-12x-white-dark.png',
            'v0.1.10-left-transition-transition-before-12x-white-dark.png',
            'v0.1.10-right-tip-12x-white-dark.png',
            'v0.1.9-right-tip-before-12x-white-dark.png',
            'v0.1.10-whole-shaft-handle-8x-white-dark.png',
            'v0.1.9-whole-shaft-handle-before-8x-white-dark.png',
            'v0.1.10-bone-grip-endcap-12x-white-dark.png')]}
    (OUT / 'v0.1.10-ends-draft-map.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('PASS 0.1.10 image draft; no candidate or production resources changed.')
    print('Draft states:', [i for i, _ in STATES], 'shaft path points:', len(SHAFT_PATH))
    print('Output:', OUT)


if __name__ == '__main__':
    main()
