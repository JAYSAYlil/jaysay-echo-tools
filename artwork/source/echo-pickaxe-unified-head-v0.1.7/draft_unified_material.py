"""Preview-only v0.1.7: recolor the res0 head/tip from real common64 shaft grain."""
import hashlib
import io
import json
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
SRC = Path(__file__).resolve().parent
OUT = ROOT / 'artwork/validation/v0.1.7/draft-4'
BASELINE_JAR = ROOT / 'jaysay-echo-tools-0.1.6.jar'
BASELINE_SHA = 'AE44F1DD5D70562301AFE5DAB55B56F4E07ED1291F4FC8A00E0A400C0697A8C4'
MASK_PATH = ROOT / 'artwork/source/echo-pickaxe-unified-head-v0.1.6/unified-head-edit-mask-v0.1.6.png'
SHAFT_PATH = ROOT / 'artwork/source/approved-reference-oct03-64/common64-unupgraded.png'
SHAFT_GLOW_PATH = ROOT / 'artwork/source/approved-reference-oct03-64/common64-glow.png'
ORDINARY_JAR = ROOT / 'jaysay-echo-tools-0.1.2.jar'
ORDINARY_SHA = '7312AE7B54F3DAD998815B7C7BD601B65DB1BED23A21CC7AA8448E40E082F495'
SHAFT_ROI = (18, 28, 39, 49)  # pixels around the real diagonal common64 shaft and its two fissures
HEAD_CROP = (5, 4, 47, 43)
TIP_CROP = (7, 7, 34, 30)
DARK_BG = (22, 28, 36)

SAMPLE_OFFSET = (10, 22)
MICROFACET_SOURCE_PAIRS = [((27, 10), (26, 36)), ((29, 11), (27, 38)), ((28, 13), (28, 39))]


def sha(data):
    return hashlib.sha256(data).hexdigest().upper()


def rgba(path):
    return Image.open(path).convert('RGBA')


def px_pixels(image):
    return {(x, y) for y in range(image.height) for x in range(image.width)
            if image.getpixel((x, y))[3] == 255}


def nearest(items, point, radius=None):
    x, y = point
    candidates = [(q, (q[0] - x) ** 2 + (q[1] - y) ** 2) for q in items]
    if radius is not None:
        candidates = [(q, d) for q, d in candidates if d <= radius * radius]
    if not candidates:
        candidates = [(q, (q[0] - x) ** 2 + (q[1] - y) ** 2) for q in items]
    return min(candidates, key=lambda item: (item[1], item[0][1], item[0][0]))[0]


def recolor_variant(base, mask, shaft):
    out = base.copy()
    x0, y0, x1, y1 = SHAFT_ROI
    shaft_pixels = {(x, y) for y in range(y0, y1) for x in range(x0, x1)
                    if shaft.getpixel((x, y))[3] == 255}
    # Repaint only the hook and the old upper cyan head planes. The lower neck/shaft
    # and the original right-side head textures remain the approved 0.1.6 pixels.
    edit_points = {p for p in mask if (p[1] < 24 and p[0] < 30)
                   or (p[1] < 15 and p[0] <= 31)}
    source_records = {}
    for x, y in sorted(edit_points, key=lambda p: (p[1], p[0])):
        # Same 1:1 native texel scale and orientation as the diagonal real shaft.
        # If the translated shaft coordinate is transparent/outside the ROI, use
        # the nearest opaque shaft texel at native pixel distance, with no resizing.
        target = (x + SAMPLE_OFFSET[0], y + SAMPLE_OFFSET[1])
        source_pixel = target if target in shaft_pixels else nearest(shaft_pixels, target)
        out.putpixel((x, y), shaft.getpixel(source_pixel))
        source_records[(x, y)] = source_pixel

    # Root-approved draft-3 microfacets: three deliberately low-value texels
    # copied 1:1 from a dark, multilevel patch on the actual common64 shaft.
    # They break the broad central near-black face without adding glow/cracks.
    for dst, source_pixel in MICROFACET_SOURCE_PAIRS:
        assert dst in edit_points and source_pixel in shaft_pixels
        color = shaft.getpixel(source_pixel)
        assert color[3] == 255 and max(color[:3]) < 80
        out.putpixel(dst, color)
        source_records[dst] = source_pixel

    assert all(out.getpixel((x, y))[3] == base.getpixel((x, y))[3]
               for y in range(64) for x in range(64))
    assert all(out.getpixel((x, y)) == base.getpixel((x, y))
               for y in range(64) for x in range(64) if (x, y) not in edit_points)
    return out, source_records, edit_points


def font(size):
    path = Path('C:/Windows/Fonts/msyh.ttc')
    return ImageFont.truetype(str(path), size) if path.exists() else ImageFont.load_default()


def composite(image, background):
    layer = Image.new('RGBA', image.size, background + (255,))
    layer.alpha_composite(image)
    return layer.convert('RGB')


def save_states(states, output, crop=None, scale=4):
    margin, gap, header = 12, 12, 26
    shown = []
    for label, image in states:
        part = image.crop(crop) if crop else image
        part = part.resize((part.width * scale, part.height * scale), Image.Resampling.NEAREST)
        shown.append((label, part))
    cellw = max(image.width for _, image in shown) + 12
    cellh = header + max(image.height for _, image in shown) + 8
    board = Image.new('RGB', (margin * 2 + 4 * cellw + 3 * gap, margin * 2 + 2 * cellh), (242, 244, 247))
    draw = ImageDraw.Draw(board)
    f = font(13)
    for row, bg in enumerate(((255, 255, 255), DARK_BG)):
        y = margin + row * cellh
        for col, (label, image) in enumerate(shown):
            x = margin + col * (cellw + gap)
            draw.text((x + 2, y), label + ('｜白底' if row == 0 else '｜暗底'), fill=(25, 30, 38), font=f)
            board.paste(composite(image, bg), (x + 2, y + header))
    board.save(output)


def save_tip_shaft(tip, shaft, output):
    scale, margin, titleh = 8, 12, 32
    tip_image = tip.crop(TIP_CROP).resize(((TIP_CROP[2] - TIP_CROP[0]) * scale,
                                           (TIP_CROP[3] - TIP_CROP[1]) * scale), Image.Resampling.NEAREST)
    shaft_image = shaft.crop(SHAFT_ROI).resize(((SHAFT_ROI[2] - SHAFT_ROI[0]) * scale,
                                                (SHAFT_ROI[3] - SHAFT_ROI[1]) * scale), Image.Resampling.NEAREST)
    gap = 20
    cellw = max(tip_image.width, shaft_image.width) + 8
    cellh = titleh + max(tip_image.height, shaft_image.height) + 8
    board = Image.new('RGB', (margin * 2 + 2 * cellw + gap, margin * 2 + 2 * cellh), (242, 244, 247))
    d, f = ImageDraw.Draw(board), font(13)
    for row, bg in enumerate(((255, 255, 255), DARK_BG)):
        y = margin + row * cellh
        for col, (label, image) in enumerate((('v0.1.7 弯尖 / 头沿', tip_image), ('common64 杆身实像素', shaft_image))):
            x = margin + col * (cellw + gap)
            d.text((x, y), label + ('｜白底' if row == 0 else '｜暗底'), fill=(25, 30, 38), font=f)
            board.paste(composite(image, bg), (x, y + titleh))
    board.save(output)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    baseline_bytes = BASELINE_JAR.read_bytes()
    assert sha(baseline_bytes) == BASELINE_SHA, 'pinned 0.1.6 JAR SHA mismatch'
    base_images, hashes = {}, {}
    with zipfile.ZipFile(io.BytesIO(baseline_bytes)) as archive:
        for index in (24, 31):
            item = f'echo_pickaxe_v{index:03d}'
            data = archive.read(f'assets/echopickaxe/textures/item/{item}.png')
            base_images[index] = Image.open(io.BytesIO(data)).convert('RGBA')
            hashes[str(index)] = sha(data)

    mask_image = rgba(MASK_PATH)
    mask = px_pixels(mask_image)
    shaft = rgba(SHAFT_PATH)
    assert shaft.size == (64, 64)
    v024, map024, edit24 = recolor_variant(base_images[24], mask, shaft)
    v031, map031, edit31 = recolor_variant(base_images[31], mask, shaft)

    # Save native editable previews only; no candidate tree, models, or glow resources.
    v024.save(OUT / 'v024-native64-draft.png')
    v031.save(OUT / 'v031-native64-draft.png')
    before_after = [
        ('旧0.1.6 v024', base_images[24]), ('新稿 v024', v024),
        ('旧0.1.6 v031', base_images[31]), ('新稿 v031', v031),
    ]
    save_states(before_after, OUT / 'v031-v024-whole-tool-white-dark.png', scale=4)
    save_states(before_after, OUT / 'v031-v024-head-neck-8x-white-dark.png', crop=HEAD_CROP, scale=8)
    save_tip_shaft(v031, shaft, OUT / 'v017-tip-vs-shaft-8x-white-dark.png')

    # Minimal reproducible visual note: only upper hook/head RGB changes. Keep the
    # native 0.1.6 body facets below and to the right as the continuation reference.
    map_doc = {
        'status': 'visual-draft-only-awaiting-root-review',
        'version': '0.1.7-unified-dark-shaft-material',
        'baseline': 'pinned jaysay-echo-tools-0.1.6.jar; no candidate-tree or production-src reads',
        'baselineJar': BASELINE_JAR.name,
        'baselineJarSha256': BASELINE_SHA,
        'ordinaryOutlineRule': 'The full deployed 0.1.6 v031/v024 alpha is unchanged. Color changes are a subset of its frozen 608-texel mask.',
        'editMask': 'artwork/source/echo-pickaxe-unified-head-v0.1.6/unified-head-edit-mask-v0.1.6.png',
        'editMaskSha256': sha(MASK_PATH.read_bytes()),
        'editMaskPixels': len(mask),
        'shaftSource': 'artwork/source/approved-reference-oct03-64/common64-unupgraded.png',
        'shaftSourceRoiInclusive': [SHAFT_ROI[0], SHAFT_ROI[1], SHAFT_ROI[2] - 1, SHAFT_ROI[3] - 1],
        'shaftSourceRoiStyle': 'actual 64px body diagonal with deep near-black blue base, small irregular dark facets, and two narrow cyan fissures',
        'materialPlan': 'Repaint only the old curved hook and upper broad cyan planes from the actual common64 shaft patch at 1:1 texel scale, including its original dark cuts and bright fissure pixels at native RGB. The short shaft patch is translated along the same lower-left to upper-right grain direction; opaque source texels are used directly, and transparent positions use the nearest opaque texel from that same real shaft ROI. No stretch, luminance remap, random noise, handcrafted attenuated cyan, or old 32px RGB.',
        'sampleMappingRule': 'destination(x,y) -> common64 shaft(x+10,y+22) if that coordinate is opaque inside the shaft ROI; otherwise nearest opaque texel in the same ROI, by integer pixel distance. No interpolation or scale change.',
        'preservedZones': ['all material-mask texels y>=24 are exact 0.1.6 RGB', 'all material-mask texels x>=30 and y>=15 are exact 0.1.6 RGB'],
        'editedTexels': len(edit31),
        'repaintBoundsInclusive': [min(x for x, y in edit31), min(y for x, y in edit31),
                                   max(x for x, y in edit31), max(y for x, y in edit31)],
        'rgbaSourceRecordsV031': [[x, y, *map031[(x, y)], list(v031.getpixel((x, y)))] for x, y in sorted(edit31, key=lambda p: (p[1], p[0]))],
        'rgbaSourceRecordsV024': [[x, y, *map024[(x, y)], list(v024.getpixel((x, y)))] for x, y in sorted(edit24, key=lambda p: (p[1], p[0]))],
        'rootApprovedDarkMicrofacets': [{'destination': list(dst), 'shaftSource': list(src), 'rgba': list(v031.getpixel(dst)), 'glow': 'forced transparent for all 16 frames'} for dst, src in MICROFACET_SOURCE_PAIRS],
        'editedTexelsMatchAcrossStates': edit24 == edit31,
        'sourceVariantSha256': hashes,
        'modulePixelsTouched': 0,
        'alphaUnchanged': True,
        'candidateGenerated': False,
        'productionChanged': False,
        'previews': ['v031-v024-whole-tool-white-dark.png', 'v031-v024-head-neck-8x-white-dark.png',
                     'v017-tip-vs-shaft-8x-white-dark.png', 'v024-native64-draft.png', 'v031-native64-draft.png'],
    }
    (OUT / 'v0.1.7-draft-map.json').write_text(json.dumps(map_doc, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'PASS preview-only v0.1.7: 64x64 alpha exact; mask={len(mask)}, edited={len(edit31)}, direct shaft samples={sum(1 for p in edit31 if map031[p] == (p[0] + SAMPLE_OFFSET[0], p[1] + SAMPLE_OFFSET[1]))}; out={OUT}')


if __name__ == '__main__':
    main()
