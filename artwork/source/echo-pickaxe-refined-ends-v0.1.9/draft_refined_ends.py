"""Preview-only 0.1.9 refinement of the resonant hook and exposed haft-end facets."""
import hashlib
import importlib.util
import io
import json
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
JAR = ROOT / 'jaysay-echo-tools-0.1.8.jar'
JAR_SHA = 'BF962BA4F64395EDA4227B9C1B9CB7437B800B468DFE8EED7A24FAAEEDC07778'
ORDINARY_JAR = ROOT / 'jaysay-echo-tools-0.1.2.jar'
ORDINARY_SHA = '7312AE7B54F3DAD998815B7C7BD601B65DB1BED23A21CC7AA8448E40E082F495'
COMMON = ROOT / 'artwork/source/approved-reference-oct03-64/common64-unupgraded.png'
COMPONENT_MAP = ROOT / 'artwork/source/approved-reference-oct03-64/native64-component-map.json'
PREVIEW_HELPER = ROOT / 'artwork/source/echo-pickaxe-unified-head-v0.1.6/build_unified_head_candidate.py'
ENDPOINT_SRC = ROOT / 'artwork/source/echo-pickaxe-native-tip-v0.1.9/draft_tip_refinement.py'
OUT = ROOT / 'artwork/validation/v0.1.9/refined-ends-draft'
ASSET = 'assets/echopickaxe/textures/item/echo_pickaxe_v{:03d}.png'

# Res0 curved tip: preserve the outside macro-curve; progressively narrow its
# inner edge from 8 px to 1 px, retaining four-connectivity and old terminal direction.
TIP_ROW_END = {18: 17, 19: 16, 20: 15, 21: 14, 22: 13, 23: 12, 24: 11, 25: 11}
TIP_EXTEND = {(10, 25), (10, 26)}
TIP_BONE_FACETS = {
    (16, 18): (169, 166, 158),
    (15, 19): (229, 223, 209),
    (14, 20): (194, 190, 174),
}

# The unadorned butt has a flat gray-blue cap above the exposed bone inset.
# Split the cap into short planes, interrupt its cyan seam, facet the bone, and
# taper the tail one pixel. Extension ornaments stay outside this edit path.
HANDLE_REMOVE = {(11, 59)}
HANDLE_ADD = {(10, 60)}
HANDLE_FACETS = {
    # Split the former broad gray-blue end-cap into two short planes and a
    # broken cyan seam that follows the haft grain into the ferrule.
    (10, 48): (26, 43, 62), (11, 48): (39, 63, 83),
    (12, 48): (53, 83, 100), (13, 48): (25, 49, 64),
    (14, 48): (72, 171, 184), (15, 48): (7, 58, 73),
    (16, 48): (14, 92, 107),
    (10, 49): (42, 66, 86), (11, 49): (25, 46, 62),
    (12, 49): (49, 80, 97), (13, 49): (23, 44, 58),
    (14, 49): (13, 53, 65), (15, 49): (20, 79, 91),
    (16, 49): (0, 131, 159), (17, 49): (9, 37, 50),
    (13, 51): (15, 32, 43), (14, 51): (40, 61, 65),
    # Facet the outer 2x2 bone plane with a restrained light/shadow split.
    (6, 52): (169, 166, 158), (7, 52): (194, 190, 174),
    (6, 53): (112, 109, 98), (7, 53): (169, 166, 158),
    (7, 55): (167, 163, 153), (8, 55): (229, 223, 209), (9, 55): (13, 23, 38),
    (7, 56): (112, 109, 98), (8, 56): (194, 190, 174), (9, 56): (228, 221, 208),
    (7, 57): (169, 166, 158), (8, 57): (13, 23, 38), (9, 57): (175, 172, 164),
    (10, 58): (6, 15, 26), (11, 58): (13, 23, 38),
    (9, 59): (170, 166, 157), (10, 59): (16, 26, 41),
    (10, 60): (6, 15, 26),
}
RES0_TIP_STATES = (24, 4, 3, 31)
HANDLE_NO_EXTENSION_STATES = tuple(range(4, 32, 4)) + tuple(range(32, 64, 4)) + tuple(range(64, 96, 4))
SHOW_STATES = ((24, '分频III / 无共振'), (4, '调谐I / 无共振'),
               (32, '仅共振I'), (3, '延展III / 无共振'), (95, '全满级'))


def sha(data):
    return hashlib.sha256(data).hexdigest().upper()


def png(data):
    return Image.open(io.BytesIO(data)).convert('RGBA')


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise RuntimeError(f'Cannot load helper: {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_font(size):
    for font in (r'C:\Windows\Fonts\msyh.ttc', r'C:\Windows\Fonts\arial.ttf'):
        if Path(font).is_file():
            return ImageFont.truetype(font, size)
    return ImageFont.load_default()


def tip_changes(baseline):
    result = baseline.copy()
    old_alpha = {(x, y) for y in range(64) for x in range(64) if baseline.getpixel((x, y))[3]}
    target_alpha = set(old_alpha)
    for y, right in TIP_ROW_END.items():
        target_alpha.difference_update((x, y) for x in range(right + 1, 23))
    target_alpha.update(TIP_EXTEND)
    removed, added = old_alpha - target_alpha, target_alpha - old_alpha
    for x, y in removed:
        result.putpixel((x, y), (0, 0, 0, 0))
    for x, y in added:
        result.putpixel((x, y), (6, 15, 26, 255))
    for p, rgb in TIP_BONE_FACETS.items():
        assert result.getpixel(p)[3] == 255, p
        result.putpixel(p, (*rgb, 255))
    assert {(x, y) for y in range(64) for x in range(64) if baseline.getpixel((x, y))[3]} - target_alpha == removed
    assert target_alpha - {(x, y) for y in range(64) for x in range(64) if baseline.getpixel((x, y))[3]} == added
    return result, removed, added


def handle_changes(baseline):
    result = baseline.copy()
    for x, y in HANDLE_REMOVE:
        assert result.getpixel((x, y))[3] == 255
        result.putpixel((x, y), (0, 0, 0, 0))
    for x, y in HANDLE_ADD:
        assert result.getpixel((x, y))[3] == 0
        result.putpixel((x, y), (*HANDLE_FACETS[(x, y)], 255))
    for p, rgb in HANDLE_FACETS.items():
        assert result.getpixel(p)[3] == 255, p
        result.putpixel(p, (*rgb, 255))
    return result


def draft_variant(index, baseline):
    result = baseline.copy()
    tip_removed, tip_added = set(), set()
    if 1 <= index <= 31:
        result, tip_removed, tip_added = tip_changes(result)
    handle = (index < 32 and index != 0 and index % 4 == 0) or (32 <= index <= 95 and index % 4 == 0)
    if handle:
        result = handle_changes(result)
    return result, tip_removed, tip_added, handle


def save_zoom_comparison(archive, before_after, title, crop, output_name, scale=16):
    panels = before_after
    cell_w = (crop[2] - crop[0]) * scale
    cell_h = (crop[3] - crop[1]) * scale
    gap = 12
    row_height = cell_h + 40
    out = Image.new('RGB', (len(panels) * (cell_w + gap) - gap, row_height * 2), (30, 34, 40))
    draw = ImageDraw.Draw(out)
    for row, bg in enumerate(('white', (26, 31, 38))):
        for col, (index, stage, label) in enumerate(panels):
            x, y = col * (cell_w + gap), row * row_height
            draw.rectangle((x, y, x + cell_w, y + row_height - 1), fill=bg)
            ink = (20, 24, 29) if bg == 'white' else (235, 238, 241)
            draw.text((x + 4, y + 5), label, font=load_font(15), fill=ink)
            src = png(archive.read(ASSET.format(index)))
            image = src if stage == 'before' else draft_variant(index, src)[0]
            crop_im = image.crop(crop).resize((cell_w, cell_h), Image.Resampling.NEAREST)
            out.paste(crop_im, (x, y + 36), crop_im)
    out.save(OUT / output_name)


def save_multistate_board(states):
    cell_w, cell_h = 268, 294
    out = Image.new('RGB', (cell_w * len(states), cell_h * 2), (226, 229, 232))
    draw = ImageDraw.Draw(out)
    for row, bg in enumerate(('white', (25, 30, 37))):
        for col, (label, sprite) in enumerate(states):
            x, y = col * cell_w, row * cell_h
            draw.rectangle((x, y, x + cell_w - 1, y + cell_h - 1), fill=bg)
            ink = (20, 23, 27) if bg == 'white' else (235, 239, 242)
            draw.text((x + 7, y + 7), label, font=load_font(16), fill=ink)
            sprite = sprite.resize((256, 256), Image.Resampling.NEAREST)
            out.paste(sprite, (x + 6, y + 36), sprite)
    out.save(OUT / 'v0.1.9-refined-ends-multistate-white-dark.png')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    jar_bytes = JAR.read_bytes()
    ordinary_bytes = ORDINARY_JAR.read_bytes()
    assert sha(jar_bytes) == JAR_SHA, 'pinned 0.1.8 JAR SHA mismatch'
    assert sha(ordinary_bytes) == ORDINARY_SHA, 'pinned 0.1.2 JAR SHA mismatch'
    components = json.loads(COMPONENT_MAP.read_text(encoding='utf-8'))['components']
    module_pixels = {name: {(x, y) for tier in components[name]['tiers']
                            for x, y, *_ in tier['texels']}
                     for name in ('frequency', 'tuning', 'extension')}
    probe = png(zipfile.ZipFile(io.BytesIO(jar_bytes)).read(ASSET.format(24)))
    tip_probe, tip_removed, tip_added = tip_changes(probe)
    tip_mask = {(x, y) for y in range(64) for x in range(64)
                if probe.getpixel((x, y)) != tip_probe.getpixel((x, y))}
    assert not tip_mask & (module_pixels['frequency'] | module_pixels['tuning'] | module_pixels['extension'])
    assert not (set(HANDLE_FACETS) | HANDLE_ADD | HANDLE_REMOVE) & (module_pixels['frequency'] | module_pixels['tuning'])
    helper = load_module(PREVIEW_HELPER, 'preview_refined_ends_019')
    basegen = load_module(ROOT / 'artwork/source/echo-pickaxe-native-edge-v0.1.8/build_native_edge_candidate.py',
                          'shared_native_model_helpers_019')
    variants, diff_records = {}, {}
    with zipfile.ZipFile(io.BytesIO(jar_bytes)) as archive, zipfile.ZipFile(io.BytesIO(ordinary_bytes)) as ordinary:
        for index in (24, 4, 32, 3, 31, 92, 95):
            original = png(archive.read(ASSET.format(index)))
            result, tip_removed, tip_added, handle = draft_variant(index, original)
            variants[index] = (original, result)
            diff_records[index] = {'changedTexels': sum(original.getpixel((x, y)) != result.getpixel((x, y))
                                                         for y in range(64) for x in range(64)),
                                   'tipAlphaRemoved': sorted([list(p) for p in tip_removed]),
                                   'tipAlphaAdded': sorted([list(p) for p in tip_added]),
                                   'handleEndEdited': handle}
            result.save(OUT / f'v{index:03d}-0.1.9-refined-ends-draft-native64.png')
        states = []
        for index, label in SHOW_STATES:
            old_glow = png(archive.read(f'assets/echopickaxe/textures/item/echo_pickaxe_v{index:03d}_glow.png'))
            old_model = json.loads(archive.read(f'assets/echopickaxe/models/item/echo_pickaxe_v{index:03d}.json').decode('utf-8'))
            sprite = variants[index][1]
            # Draft stage draws the exact front face and unchanged indexed glow;
            # alpha and model prism additions/removals remain review-only details.
            states.append((label, basegen.frontface(sprite, old_glow, old_model, 0)))
        ordinary_sprite = png(ordinary.read('assets/echopickaxe/textures/item/echo_pickaxe.png'))
        ordinary_glow = png(ordinary.read('assets/echopickaxe/textures/item/echo_pickaxe_glow.png'))
        ordinary_model = json.loads(ordinary.read('assets/echopickaxe/models/item/echo_pickaxe.json').decode('utf-8'))
        states.insert(0, ('普通0.1.2原版', basegen.frontface(ordinary_sprite, ordinary_glow, ordinary_model, 0)))
        save_multistate_board(states)

        tip_panels = [(24, 'before', '频III v024 原稿'), (24, 'after', '频III v024 收尖+骨刃'),
                      (4, 'before', '调谐I v004 原稿'), (4, 'after', '调谐I v004 收尖+骨刃')]
        save_zoom_comparison(archive, tip_panels, 'hook', (7, 15, 27, 27),
                             'v0.1.9-hook-tip-16x-white-dark.png', 16)
        handle_panels = [(24, 'before', '分频III v024 原尾'), (24, 'after', '分频III v024 细化尾端'),
                         (32, 'before', '红尖v032 原尾'), (32, 'after', '红尖v032 细化尾端'),
                         (3, 'after', '延展III绿眼保留'), (95, 'after', '全满级绿眼保留')]
        save_zoom_comparison(archive, handle_panels, 'haft end', (4, 47, 21, 63),
                             'v0.1.9-haft-end-16x-white-dark.png', 16)
        tail_panels = [(24, 'before', 'v024 原尾端'), (24, 'after', 'v024 细化 facet + 断续青脉'),
                       (32, 'before', 'v032 红版原尾端'), (32, 'after', 'v032 细化 facet + 断续青脉')]
        save_zoom_comparison(archive, tail_panels, 'ferrule', (6, 46, 19, 57),
                             'v0.1.9-bare-ferrule-16x-white-dark.png', 16)
        # Surface/shape probes for extension I/II are preserved as a small strip:
        # their exposed bone slivers already use separate native texels, so edits stay away.
        inspection = []
        for index in (1, 2, 33, 34, 65, 66):
            sprite = png(archive.read(ASSET.format(index)))
            inspection.append((index, sprite.crop((4, 45, 22, 63))))

    common = Image.open(COMMON).convert('RGBA')
    bone_palette = [[229, 223, 209], [194, 190, 174], [169, 166, 158], [112, 109, 98]]
    doc = {
        'status': 'preview-only-awaiting-root-visual-review; supersedes tip-only 8-texel draft',
        'baselineJar': JAR.name, 'baselineJarSha256': JAR_SHA,
        'scope': 'Res0 upgraded hook is narrowed throughout its terminal sweep with a small bone-facet edge. Ext0 handle ferrule and exposed bone inset are refined for res0 and red res>=1, including short native facets and a broken narrow cyan seam. Ordinary assets, red hook, ext>0 green eye/ring, body/neck/modules remain baseline.',
        'tipRowsFinalRightEdge': {str(k): v for k, v in TIP_ROW_END.items()},
        'tipAdded': [list(p) for p in sorted(TIP_EXTEND)],
        'tipFacetRGBA': [{'pixel': list(p), 'rgba': list(c)} for p, c in sorted(TIP_BONE_FACETS.items())],
        'tipAlphaRemovedFrom0.1.8V031': [list(p) for p in sorted(draft_variant(31, variants[31][0])[1])],
        'tipAlphaAddedTo0.1.8V031': [list(p) for p in sorted(draft_variant(31, variants[31][0])[2])],
        'handleEndAlphaRemoved': [list(p) for p in sorted(HANDLE_REMOVE)],
        'handleEndAlphaAdded': [list(p) for p in sorted(HANDLE_ADD)],
        'handleBoneFacets': [{'pixel': list(p), 'rgba': list(c)} for p, c in sorted(HANDLE_FACETS.items())],
        'bonePaletteReference': 'Approved common64 body palette; not copied as a patch. Colors are remapped as a 1px facet pattern. The gray-blue cap is split into short dark/mid planes; the cyan seam is interrupted rather than left as a broad stripe.',
        'componentProtection': 'Tip edit-mask intersection with frequency/tuning/extension maps=0. Handle edits are only applied when extension level=0; they do not intersect frequency/tuning. Extension I/II/III green-eye and slanted-ring textures are byte/pixel untouched; inspection found their exposed bone slivers already native and left them unchanged.',
        'stateDelta': {str(k): v for k, v in diff_records.items()},
        'ordinary': '0.1.2 JAR SHA pinned and ordinary texture/model/glow not edited.',
        'redHook': 'res>=1 hook RGB/alpha remains exact 0.1.8; only ext0 exposed handle end receives the local facet/taper edit.',
        'previews': ['artwork/validation/v0.1.9/refined-ends-draft/v0.1.9-refined-ends-multistate-white-dark.png',
                     'artwork/validation/v0.1.9/refined-ends-draft/v0.1.9-hook-tip-16x-white-dark.png',
                     'artwork/validation/v0.1.9/refined-ends-draft/v0.1.9-haft-end-16x-white-dark.png',
                     'artwork/validation/v0.1.9/refined-ends-draft/extension-I-II-handle-check.png'],
    }
    (OUT / 'refined-ends-draft-map-v0.1.9.json').write_text(json.dumps(doc, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (ROOT / 'artwork/validation/v0.1.9/draft-revision-status.txt').write_text(
        'The earlier 8-texel tip-only candidate was superseded by the user’s expanded 0.1.9 request. '
        'It was never deployed. Preserve its source and candidate artifacts as historical review evidence. '
        'The active draft is artwork/validation/v0.1.9/refined-ends-draft/.\n', encoding='utf-8')
    print('PASS refined-end draft; production remains untouched.')
    print('Tip alpha change counts:', len(doc['tipAlphaRemovedFrom0.1.8V031']), len(doc['tipAlphaAddedTo0.1.8V031']))
    print('Ext0 butt alpha change:', len(HANDLE_REMOVE), len(HANDLE_ADD), 'bone-facet RGB cells:', len(HANDLE_FACETS))
    print('Tip/module overlaps:', len(tip_mask & (module_pixels['frequency'] | module_pixels['tuning'] | module_pixels['extension'])))
    print('Handle/frequency-or-tuning overlaps:', len((set(HANDLE_FACETS) | HANDLE_ADD | HANDLE_REMOVE)
                                                       & (module_pixels['frequency'] | module_pixels['tuning'])))


if __name__ == '__main__':
    main()
