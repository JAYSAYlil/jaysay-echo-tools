"""Create preview-only 0.1.9 sharpened-tip drafts from the pinned 0.1.8 JAR."""
import hashlib
import io
import json
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
JAR = ROOT / 'jaysay-echo-tools-0.1.8.jar'
JAR_SHA = 'BF962BA4F64395EDA4227B9C1B9CB7437B800B468DFE8EED7A24FAAEEDC07778'
OUT = ROOT / 'artwork/validation/v0.1.9/draft'
ASSET = 'assets/echopickaxe/textures/item/echo_pickaxe_v{:03d}.png'

# Taper: row 24 narrows from four to three pixels, row 25 is shifted left
# into two pixels, and a single connected texel extends the point by one.
REMOVED = {(13, 24), (12, 25)}
ADDED = {(10, 25), (10, 26)}
# Every new/refined color is sampled from the existing 0.1.8 v031 haft texture;
# the sample coordinates and final colors are frozen below for review.
BODY_SAMPLES = {
    (10, 24): (24, 38),
    (11, 24): (24, 37),  # one subdued cyan facet, not a white edge
    (12, 24): (28, 36),
    (10, 25): (25, 37),
    (11, 25): (24, 38),
    (10, 26): (25, 38),
}
EDIT_PIXELS = REMOVED | ADDED | set(BODY_SAMPLES)


def sha(data):
    return hashlib.sha256(data).hexdigest().upper()


def rgba_from_jar(archive, path):
    return Image.open(io.BytesIO(archive.read(path))).convert('RGBA')


def load_font(size):
    for path in (r'C:\Windows\Fonts\msyh.ttc', r'C:\Windows\Fonts\arial.ttf'):
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def apply(sprite, shaft):
    result = sprite.copy()
    for x, y in REMOVED:
        result.putpixel((x, y), (0, 0, 0, 0))
    for p, src in BODY_SAMPLES.items():
        sample = shaft.getpixel(src)
        if sample[3] != 255:
            raise AssertionError(f'nonopaque body sample {src}: {sample}')
        result.putpixel(p, sample)
    for x, y in ADDED:
        assert result.getpixel((x, y))[3] == 255
    for p in REMOVED:
        assert result.getpixel(p)[3] == 0
    return result


def draw_card(canvas, sprite, box, title, bg):
    x, y, w, h = box
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((x, y, x + w, y + h), fill=bg)
    draw.text((x + 8, y + 6), title, font=load_font(18), fill=(20, 23, 27) if bg == 'white' else (235, 239, 242))
    scaled = sprite.resize((256, 256), Image.Resampling.NEAREST)
    canvas.paste(scaled, (x + (w - 256) // 2, y + 34), scaled)


def save_full_board(before_by_index, after_by_index):
    card_w, card_h = 312, 326
    width, height = 4 * card_w, 2 * card_h
    out = Image.new('RGB', (width, height), (225, 228, 231))
    cards = [
        (before_by_index[24], '分频III v024 / 原版'),
        (after_by_index[24], '分频III v024 / 收尖草稿'),
        (before_by_index[31], '无共振满级 v031 / 原版'),
        (after_by_index[31], '无共振满级 v031 / 收尖草稿'),
    ]
    for row, bg in enumerate(('white', (25, 30, 37))):
        for col, (sprite, label) in enumerate(cards):
            draw_card(out, sprite, (col * card_w, row * card_h, card_w, card_h), label, bg)
    out.save(OUT / 'v0.1.9-whole-white-dark-before-after.png')


def save_head_board(before, after):
    crop_box = (5, 4, 39, 31)
    width, height = 656, 456
    out = Image.new('RGB', (width, height), (230, 233, 236))
    draw = ImageDraw.Draw(out)
    for row, bg in enumerate(('white', (25, 30, 37))):
        for col, (sprite, label) in enumerate(((before, 'v031 原稿'), (after, 'v031 收尖草稿'))):
            x, y = col * 328, row * 228
            draw.rectangle((x, y, x + 327, y + 227), fill=bg)
            ink = (20, 23, 27) if bg == 'white' else (235, 239, 242)
            draw.text((x + 9, y + 7), label + ' · 头颈 8×', font=load_font(17), fill=ink)
            crop = sprite.crop(crop_box).resize((272, 216), Image.Resampling.NEAREST)
            out.paste(crop, (x + 28, y + 35), crop)
    out.save(OUT / 'v0.1.9-head-neck-8x-white-dark.png')


def save_tip_board(before, after, shaft):
    # Exact native pixels enlarged 16x: before/after and actual same-texture body.
    crop_box = (8, 20, 20, 28)
    tip_before = before.crop(crop_box).resize((192, 128), Image.Resampling.NEAREST)
    tip_after = after.crop(crop_box).resize((192, 128), Image.Resampling.NEAREST)
    shaft_crop = shaft.crop((24, 35, 36, 43)).resize((192, 128), Image.Resampling.NEAREST)
    out = Image.new('RGB', (720, 200), (26, 30, 36))
    draw = ImageDraw.Draw(out)
    panels = ((tip_before, '旧末端 · 原生像素 16×'), (tip_after, '收尖草稿 · 原生像素 16×'), (shaft_crop, '杆身材质 · 原生像素 16×'))
    for i, (im, title) in enumerate(panels):
        x = i * 240
        draw.text((x + 12, 8), title, font=load_font(16), fill=(240, 243, 245))
        out.paste(im, (x + 20, 48), im)
    out.save(OUT / 'v0.1.9-tip-end-16x-before-after.png')


def save_native(before_by_index, after_by_index):
    for index in (24, 31):
        before_by_index[index].save(OUT / f'v{index:03d}-0.1.8-native64.png')
        after_by_index[index].save(OUT / f'v{index:03d}-0.1.9-tip-draft-native64.png')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    jar_bytes = JAR.read_bytes()
    if sha(jar_bytes) != JAR_SHA:
        raise RuntimeError('Pinned 0.1.8 JAR hash mismatch')
    with zipfile.ZipFile(io.BytesIO(jar_bytes)) as archive:
        shaft = rgba_from_jar(archive, ASSET.format(31))
        before_by_index, after_by_index = {}, {}
        for index in (24, 31):
            before = rgba_from_jar(archive, ASSET.format(index))
            after = apply(before, shaft)
            before_by_index[index], after_by_index[index] = before, after
            before_by_index[index].save(OUT / f'v{index:03d}-0.1.8-native64.png')
            after_by_index[index].save(OUT / f'v{index:03d}-0.1.9-tip-draft-native64.png')
        save_full_board(before_by_index, after_by_index)
        save_head_board(before_by_index[31], after_by_index[31])
        save_tip_board(before_by_index[31], after_by_index[31], shaft)
    record = {
        'status': 'preview-only-awaiting-root-visual-review',
        'baselineJar': JAR.name,
        'baselineJarSha256': JAR_SHA,
        'scope': 'Only the hooked terminal edge; no candidate/model/glow changes generated in this draft stage.',
        'outlineRemoved': [list(p) for p in sorted(REMOVED)],
        'outlineAdded': [list(p) for p in sorted(ADDED)],
        'colorSamplesFromV031Shaft': [{'target': list(p), 'source': list(src), 'rgba': list(shaft.getpixel(src))}
                                       for p, src in sorted(BODY_SAMPLES.items())],
        'editTexels': len(EDIT_PIXELS),
        'previews': [
            'artwork/validation/v0.1.9/draft/v0.1.9-whole-white-dark-before-after.png',
            'artwork/validation/v0.1.9/draft/v0.1.9-head-neck-8x-white-dark.png',
            'artwork/validation/v0.1.9/draft/v0.1.9-tip-end-16x-before-after.png',
        ],
    }
    (OUT / 'tip-draft-map-v0.1.9.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"PASS preview drafts; local outline removed={len(REMOVED)}, added={len(ADDED)}, recolored={len(BODY_SAMPLES)}")
    for path in sorted(OUT.glob('*')):
        if path.is_file():
            print(path.relative_to(ROOT).as_posix(), sha(path.read_bytes()))


if __name__ == '__main__':
    main()
