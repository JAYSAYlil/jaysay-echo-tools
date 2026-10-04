"""Inspect installed 0.1.9 pickaxe ends and component bounds; no source writes."""
import hashlib
import importlib.util
import io
import json
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
OUT = ROOT / 'artwork/validation/v0.1.10/inspection'
PREFIX = 'assets/echopickaxe/'


def sha(data):
    return hashlib.sha256(data).hexdigest().upper()


def read_png(data):
    return Image.open(io.BytesIO(data)).convert('RGBA')


def load_helper(path):
    spec = importlib.util.spec_from_file_location('inspect_019_preview', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def font(size):
    for p in (r'C:\Windows\Fonts\msyh.ttc', r'C:\Windows\Fonts\arial.ttf'):
        if Path(p).is_file():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def composite(im, bg):
    base = Image.new('RGBA', im.size, bg + (255,))
    base.alpha_composite(im)
    return base.convert('RGB')


def save_board(states, path, crop=None, scale=4):
    if crop:
        w, h = crop[2] - crop[0], crop[3] - crop[1]
    else:
        w = h = 64
    sprite_w, sprite_h = w * scale, h * scale
    label_h, margin = 28, 10
    cell_w, cell_h = sprite_w + 12, sprite_h + label_h + 6
    board = Image.new('RGB', (margin * 2 + cell_w * len(states), margin * 2 + cell_h * 2), (239, 242, 245))
    draw = ImageDraw.Draw(board)
    label_font = font(14)
    for row, bg in enumerate(((255, 255, 255), (25, 30, 38))):
        y = margin + row * cell_h
        draw.text((4, y + 4), '白底' if row == 0 else '暗底', fill=(24, 28, 32), font=label_font)
        for col, (name, im) in enumerate(states):
            x = margin + col * cell_w
            draw.text((x + 2, y + 2), name, fill=(24, 28, 32), font=label_font)
            source = im.crop(crop) if crop else im
            enlarged = source.resize((sprite_w, sprite_h), Image.Resampling.NEAREST)
            board.paste(composite(enlarged, bg), (x, y + label_h))
    board.save(path)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    raw = JAR.read_bytes()
    ordinary_raw = ORDINARY.read_bytes()
    assert sha(raw) == JAR_SHA, '0.1.9 jar SHA mismatch'
    assert sha(ordinary_raw) == ORDINARY_SHA, '0.1.2 jar SHA mismatch'
    component_doc = json.loads(COMPONENTS.read_text(encoding='utf-8'))
    bounds = {}
    for name, spec in component_doc['components'].items():
        pixels = {(t[0], t[1]) for tier in spec['tiers'] for t in tier['texels']}
        bounds[name] = {'count': len(pixels), 'bbox': [min(x for x, y in pixels), min(y for x, y in pixels),
                                                         max(x for x, y in pixels), max(y for x, y in pixels)]}

    preview = load_helper(HELPER)
    states = []
    labels = [('普通0.1.2原版', None), ('res0分频III v024', 24), ('res0调谐I v004', 4),
              ('仅共振I v032', 32), ('res0延展III v003', 3), ('全满级 v095', 95)]
    with zipfile.ZipFile(io.BytesIO(ordinary_raw)) as old, zipfile.ZipFile(io.BytesIO(raw)) as archive:
        ordinary_sprite = read_png(old.read(PREFIX + 'textures/item/echo_pickaxe.png'))
        ordinary_glow = read_png(old.read(PREFIX + 'textures/item/echo_pickaxe_glow.png'))
        ordinary_model = json.loads(old.read(PREFIX + 'models/item/echo_pickaxe.json').decode('utf-8'))
        states.append((labels[0][0], preview.frontface(ordinary_sprite, ordinary_glow, ordinary_model, 0)))
        for label, index in labels[1:]:
            sprite = read_png(archive.read(PREFIX + f'textures/item/echo_pickaxe_v{index:03d}.png'))
            glow = read_png(archive.read(PREFIX + f'textures/item/echo_pickaxe_v{index:03d}_glow.png'))
            model = json.loads(archive.read(PREFIX + f'models/item/echo_pickaxe_v{index:03d}.json').decode('utf-8'))
            states.append((label, preview.frontface(sprite, glow, model, 0)))
        save_board(states, OUT / 'v0.1.9-installed-whole-white-dark.png', scale=4)
        # Crops deliberately retain the same logical texel scale across all states.
        save_board(states, OUT / 'v0.1.9-left-hook-and-transition-12x-white-dark.png', (5, 7, 35, 35), 12)
        save_board(states, OUT / 'v0.1.9-right-head-tip-full-10x-white-dark.png', (30, 7, 64, 39), 10)
        save_board(states, OUT / 'v0.1.9-whole-shaft-and-handle-8x-white-dark.png', (8, 26, 44, 63), 8)

    report = {
        'installedJar': JAR.name, 'installedJarSha256': JAR_SHA, 'installedJarBytes': len(raw),
        'ordinaryJar': ORDINARY.name, 'ordinaryJarSha256': ORDINARY_SHA,
        'componentMap': str(COMPONENTS.relative_to(ROOT)).replace('\\', '/'),
        'componentBounds': bounds,
        'inspection': {
            'leftHookTransition': 'x5..34,y7..34; 12x nearest logical texels, white/dark backgrounds',
            'rightHeadTip': 'x30..63,y7..38; 10x nearest logical texels, includes full right bone tip and overlaid component edges, white/dark backgrounds',
            'shaftHandle': 'x8..43,y26..62; 8x nearest logical texels, includes full handle from head-neck junction to ferrule, white/dark backgrounds',
            'states': [name for name, _ in labels],
        },
        'rangeRecommendation': {
            'res0LeftHook': 'indices 001..031 only; smooth angular transition and modest additional bone facets; leave res>=1 red hook bytes unchanged.',
            'rightDanglingTip': 'Natural right bone tip is present in all resonance states; refine exposed coarse pixels in all variants while preserving the resonance-red left head. Protect any component-map module texels that overlap the right tip.',
            'shaft': 'Redesign the whole diagonal shaft from the head-neck junction through handle and ferrule, including the long dark-blue body and cyan seam; keep the green extension eye/ring pixels exact while allowing adjacent bone clasp/connector texels to be reshaped.',
        },
    }
    (OUT / 'v0.1.9-ends-inspection-map.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('PASS inspection artifacts; baseline JAR hashes verified; no production files changed.')
    print(json.dumps(bounds, ensure_ascii=False))


if __name__ == '__main__':
    main()
