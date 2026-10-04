"""Rebuild the approved v0.1.7 res0 texture/model candidate from pinned jars.

This writes only artwork/source and artwork/validation. It never deploys to src.
"""
import copy
import hashlib
import importlib.util
import io
import json
import math
import zipfile
from pathlib import Path, PurePosixPath

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
SRC = Path(__file__).resolve().parent
VAL = ROOT / 'artwork/validation/v0.1.7'
OUT = VAL / 'candidate'
PREFIX = 'assets/echopickaxe/'
BASELINE_JAR = ROOT / 'jaysay-echo-tools-0.1.6.jar'
BASELINE_SHA = 'AE44F1DD5D70562301AFE5DAB55B56F4E07ED1291F4FC8A00E0A400C0697A8C4'
ORDINARY_JAR = ROOT / 'jaysay-echo-tools-0.1.2.jar'
ORDINARY_SHA = '7312AE7B54F3DAD998815B7C7BD601B65DB1BED23A21CC7AA8448E40E082F495'
COMMON = ROOT / 'artwork/source/approved-reference-oct03-64/common64-unupgraded.png'
COMMON_GLOW = ROOT / 'artwork/source/approved-reference-oct03-64/common64-glow.png'
COMPONENT_MAP = ROOT / 'artwork/source/approved-reference-oct03-64/native64-component-map.json'
MODEL_HELPERS = ROOT / 'artwork/source/approved-reference-oct03-64/build_approved64_variants.py'
PREVIEW_HELPERS = ROOT / 'artwork/source/echo-pickaxe-unified-head-v0.1.6/build_unified_head_candidate.py'
DRAFT_SCRIPT = SRC / 'draft_unified_material.py'
UNDERLAY_PATH = SRC / 'native64-shaft-derived-underlay-v0.1.7.png'
MASK_PATH = SRC / 'unified-head-repaint-mask-v0.1.7.png'
MAP_PATH = SRC / 'unified-head-map-v0.1.7.json'
MANIFEST_PATH = VAL / 'candidate-manifest-v0.1.7.json'
FRAME_IDS = (0, 4, 8, 12)
NO_GLOW = {(27, 10), (29, 11), (28, 13)}
EDITED_INDICES = list(range(1, 32))


def sha(data):
    return hashlib.sha256(data).hexdigest().upper()


def read_png(data):
    return Image.open(io.BytesIO(data)).convert('RGBA')


def png_bytes(image):
    stream = io.BytesIO()
    image.save(stream, format='PNG', optimize=False)
    return stream.getvalue()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def image_pixels(image):
    return {(x, y) for y in range(image.height) for x in range(image.width)
            if image.getpixel((x, y))[3]}


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'Cannot load helper: {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def frontface(sprite, glow, model, frame):
    result = sprite.copy()
    size = sprite.width
    frame_image = glow.crop((0, frame * size, size, (frame + 1) * size))
    dst = result.load()
    pixels_per_world_unit = size / 16
    for element in model['elements']:
        if element['faces']['north']['texture'] != '#glow':
            continue
        x = round(element['from'][0] * pixels_per_world_unit)
        y = round((16 - element['to'][1]) * pixels_per_world_unit)
        rgba = frame_image.getpixel((x, y))
        if rgba[3]:
            dst[x, y] = rgba
    return result


def main():
    if OUT.exists() and any(OUT.iterdir()):
        existing = {p.relative_to(OUT).as_posix() for p in OUT.rglob('*') if p.is_file()}
        expected = set()
        for index in EDITED_INDICES:
            item = f'echo_pickaxe_v{index:03d}'
            expected.update({
                f'{PREFIX}models/item/{item}.json',
                f'{PREFIX}textures/item/{item}.png',
                f'{PREFIX}textures/item/{item}_glow.png',
            })
        if not existing or not existing <= expected:
            raise RuntimeError(f'Refusing to overwrite unrecognized candidate contents: {OUT}')
    baseline_bytes = BASELINE_JAR.read_bytes()
    ordinary_bytes = ORDINARY_JAR.read_bytes()
    assert sha(baseline_bytes) == BASELINE_SHA, 'pinned 0.1.6 JAR SHA mismatch'
    assert sha(ordinary_bytes) == ORDINARY_SHA, 'pinned 0.1.2 JAR SHA mismatch'

    draft = load_module(DRAFT_SCRIPT, 'unified_material_draft_v017')
    helper = load_module(MODEL_HELPERS, 'approved64_model_helpers_v017')
    previews_helper = load_module(PREVIEW_HELPERS, 'candidate_preview_helpers_v016')
    common = Image.open(COMMON).convert('RGBA')
    common_glow = Image.open(COMMON_GLOW).convert('RGBA')
    assert common.size == (64, 64) and common_glow.size == (64, 1024)
    with zipfile.ZipFile(io.BytesIO(baseline_bytes)) as base_zip, \
            zipfile.ZipFile(io.BytesIO(ordinary_bytes)) as ordinary_zip:
        baseline_images, baseline_hashes = {}, {}
        for index in (24, 31):
            item = f'echo_pickaxe_v{index:03d}'
            rel = PREFIX + f'textures/item/{item}.png'
            data = base_zip.read(rel)
            baseline_images[index] = read_png(data)
            baseline_hashes[str(index)] = sha(data)

        mask_image_016 = Image.open(SRC.parent / 'echo-pickaxe-unified-head-v0.1.6/unified-head-edit-mask-v0.1.6.png').convert('RGBA')
        parent_mask = {(x, y) for y in range(64) for x in range(64) if mask_image_016.getpixel((x, y))[3]}
        module_map = json.loads(COMPONENT_MAP.read_text(encoding='utf-8'))['components']
        module_pixels = {(x, y) for name in ('frequency', 'tuning', 'extension')
                         for tier in module_map[name]['tiers'] for x, y, *_ in tier['texels']}
        draft24, source24, edit24 = draft.recolor_variant(baseline_images[24], parent_mask, common)
        draft31, source31, edit31 = draft.recolor_variant(baseline_images[31], parent_mask, common)
        assert edit24 == edit31 and source24 == source31
        edit_mask = edit31
        assert edit_mask and edit_mask <= parent_mask
        assert not edit_mask & module_pixels
        assert all(draft31.getpixel(p)[3] == baseline_images[31].getpixel(p)[3] for p in edit_mask)

        # Frozen editable underlay and exact alpha mask are limited to actual v0.1.7 edits.
        underlay = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        mask_image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        for point in edit_mask:
            underlay.putpixel(point, draft31.getpixel(point))
            mask_image.putpixel(point, (255, 255, 255, 255))
        underlay_data, mask_data = png_bytes(underlay), png_bytes(mask_image)
        UNDERLAY_PATH.write_bytes(underlay_data)
        MASK_PATH.write_bytes(mask_data)
        draft24.save(VAL / 'draft-4/v024-native64-draft.png')
        draft31.save(VAL / 'draft-4/v031-native64-draft.png')

        # Build the common shaft-derived sparse glow. All coordinates are 1:1 source texels.
        source_for = {point: source31[point] for point in edit_mask}
        native_frames = []
        emit = set()
        for frame_id in range(16):
            source_frame = common_glow.crop((0, frame_id * 64, 64, (frame_id + 1) * 64))
            frame = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
            for point, source_point in source_for.items():
                if point in NO_GLOW:
                    continue
                rgba = source_frame.getpixel(source_point)
                if rgba[3]:
                    frame.putpixel(point, rgba)
                    emit.add(point)
            native_frames.append(frame)
        assert all(image_pixels(frame) == emit for frame in native_frames), 'source glow alpha must be fixed across 16 frames'
        assert not emit & NO_GLOW

        OUT.mkdir(parents=True, exist_ok=True)
        models_dir = OUT / PREFIX / 'models/item'
        textures_dir = OUT / PREFIX / 'textures/item'
        models_dir.mkdir(parents=True, exist_ok=True)
        textures_dir.mkdir(parents=True, exist_ok=True)
        records, variants = [], []
        previews = {}
        for index in EDITED_INDICES:
            item = f'echo_pickaxe_v{index:03d}'
            base_rel = PREFIX + f'textures/item/{item}.png'
            glow_rel = PREFIX + f'textures/item/{item}_glow.png'
            model_rel = PREFIX + f'models/item/{item}.json'
            baseline_sprite_bytes = base_zip.read(base_rel)
            baseline_sprite = read_png(baseline_sprite_bytes)
            sprite = baseline_sprite.copy()
            for point in edit_mask:
                sprite.putpixel(point, underlay.getpixel(point))
            assert all(sprite.getpixel(p)[3] == baseline_sprite.getpixel(p)[3] for p in edit_mask)
            assert all(sprite.getpixel((x, y)) == baseline_sprite.getpixel((x, y))
                       for y in range(64) for x in range(64) if (x, y) not in edit_mask)

            baseline_glow = read_png(base_zip.read(glow_rel))
            assert baseline_glow.size == (64, 1024)
            glow = baseline_glow.copy()
            for frame_id, source_frame in enumerate(native_frames):
                frame = glow.crop((0, frame_id * 64, 64, (frame_id + 1) * 64))
                for x, y in edit_mask:
                    frame.putpixel((x, y), source_frame.getpixel((x, y)))
                glow.paste(frame, (0, frame_id * 64))
                old_frame = baseline_glow.crop((0, frame_id * 64, 64, (frame_id + 1) * 64))
                assert all(frame.getpixel((x, y)) == old_frame.getpixel((x, y))
                           for y in range(64) for x in range(64) if (x, y) not in edit_mask)
            assert glow.size == (64, 1024)

            lit = image_pixels(glow.crop((0, 0, 64, 64)))
            old_model = json.loads(base_zip.read(model_rel).decode('utf-8'))
            model, opaque, model_lit = helper.model_for_state(old_model, item, sprite, lit)
            if 'overrides' in old_model:
                model['overrides'] = copy.deepcopy(old_model['overrides'])
            helper.validate_model(sprite, model, model_lit, item)
            assert len(opaque) == sum(1 for y in range(64) for x in range(64) if sprite.getpixel((x, y))[3])

            payloads = {model_rel: json_bytes(model), base_rel: png_bytes(sprite), glow_rel: png_bytes(glow)}
            by_name = {}
            for rel, data in payloads.items():
                path = OUT / Path(*PurePosixPath(rel).parts)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
                record = {'path': rel, 'sha256': sha(data), 'bytes': len(data)}
                records.append(record)
                by_name[rel.rsplit('/', 1)[-1]] = sha(data)
            variants.append({'index': index, 'levels': helper.levels_for(index),
                              'opaqueTexels': len(opaque), 'emissiveTexels': len(model_lit),
                              'sha256': by_name})
            if index in (24, 31):
                previews[index] = (sprite, glow, model)

        # Preview board: actual model #glow front-face composition, not sparse glow overlay.
        ordinary_sprite = read_png(ordinary_zip.read(PREFIX + 'textures/item/echo_pickaxe.png'))
        ordinary_glow = read_png(ordinary_zip.read(PREFIX + 'textures/item/echo_pickaxe_glow.png'))
        ordinary_model = json.loads(ordinary_zip.read(PREFIX + 'models/item/echo_pickaxe.json').decode('utf-8'))
        red_sprite = read_png(base_zip.read(PREFIX + 'textures/item/echo_pickaxe_v095.png'))
        red_glow = read_png(base_zip.read(PREFIX + 'textures/item/echo_pickaxe_v095_glow.png'))
        red_model = json.loads(base_zip.read(PREFIX + 'models/item/echo_pickaxe_v095.json').decode('utf-8'))
        board_states = [
            ('普通原版 0.1.2', frontface(ordinary_sprite, ordinary_glow, ordinary_model, 0)),
            ('分频 III（v024）', frontface(*previews[24], 0)),
            ('共振0 满级（v031）', frontface(*previews[31], 0)),
            ('红色共振 II 满级（v095）', frontface(red_sprite, red_glow, red_model, 0)),
        ]
        previews_helper.save_delivery_board(board_states, VAL / 'v0.1.7-delivery-four-state-white-dark.png')
        previews_helper.save_glow_board([('分频 III（v024）', *previews[24]), ('共振0 满级（v031）', *previews[31])],
                                        VAL / 'v0.1.7-native-glow-frontface-white-dark-4frames.png')

    # Save complete source-coordinate and frozen-pixel evidence beside the generator.
    points = sorted(edit_mask, key=lambda p: (p[1], p[0]))
    bounds = [min(x for x, y in edit_mask), min(y for x, y in edit_mask),
              max(x for x, y in edit_mask), max(y for x, y in edit_mask)]
    source_map = [[x, y, *source_for[(x, y)], list(underlay.getpixel((x, y)))] for x, y in points]
    map_doc = {
        'schema': 2,
        'status': 'root-approved-visual-freeze-candidate-pending-independent-audit',
        'version': '0.1.7-shaft-matched-native64-res0',
        'baselineJar': BASELINE_JAR.name,
        'baselineJarSha256': BASELINE_SHA,
        'ordinaryReferenceJar': ORDINARY_JAR.name,
        'ordinaryReferenceJarSha256': ORDINARY_SHA,
        'sourceGenerator': str(DRAFT_SCRIPT.relative_to(ROOT)).replace('\\', '/'),
        'candidateBuilder': str((SRC / 'build_unified_head_candidate.py').relative_to(ROOT)).replace('\\', '/'),
        'underlay': str(UNDERLAY_PATH.relative_to(ROOT)).replace('\\', '/'),
        'underlaySha256': sha(underlay_data),
        'editMask': str(MASK_PATH.relative_to(ROOT)).replace('\\', '/'),
        'editMaskSha256': sha(mask_data),
        'editMaskPixels': len(edit_mask),
        'editMaskBoundsInclusive': bounds,
        'baselineRes0Images': baseline_hashes,
        'alphaContract': 'For every res0 image, alpha remains byte-pixel-identical to the pinned 0.1.6 JAR. The ordinary unupgraded 0.1.2 resource quartet is outside this candidate and remains release-owned.',
        'materialContract': 'Every edited RGB texel is sampled at native 1:1 scale from approved common64 shaft ROI via explicit sourceCoordinates below. No old 32px RGB/luminance/material classification is read. Three root-approved dark microfacets are embedded in the generator and source map.',
        'microfacets': [{'destination': list(dst), 'shaftSource': list(src), 'rgba': list(underlay.getpixel(dst)), 'glow': 'forced transparent in all frames'} for dst, src in draft.MICROFACET_SOURCE_PAIRS],
        'shaftMaterialPath': str(COMMON.relative_to(ROOT)).replace('\\', '/'),
        'shaftMaterialSha256': sha(COMMON.read_bytes()),
        'shaftGlowPath': str(COMMON_GLOW.relative_to(ROOT)).replace('\\', '/'),
        'shaftGlowSha256': sha(COMMON_GLOW.read_bytes()),
        'sourceCoordinateRule': 'Ordinary edit points map to destination+(10,22) when opaque within shaft ROI [18,28,38,48], else nearest opaque point in that ROI by integer pixel distance. The three frozen microfacets override that coordinate with their explicitly listed shaft source.',
        'sourceCoordinatesAndRGBA': source_map,
        'glowContract': 'For each edited texel and each frame, copy the corresponding common64-glow RGBA at its recorded source coordinate. Three microfacet texels are forced transparent. No brightness threshold or additional emission is synthesized. The 16-frame source phase is retained; mcmeta remains sourced byte-for-byte from pinned 0.1.6 and is not a candidate file.',
        'glowFrames': 16,
        'glowTicksPerFrame': 3,
        'emissiveTexelsInEditedMask': len(emit),
        'glowEditedMaskOutsideContract': 'Every pixel outside the 251-texel edit mask remains exactly equal to its matching pinned 0.1.6 glow frame for every res0 index.',
        'modulePixelsTouched': 0,
        'repaintMaskOutsideNeckBody': True,
        'candidateResourceCount': len(records),
        'changedVariantResourceCount': 93,
        'changedVariants': EDITED_INDICES,
        'ordinaryResourcesIncluded': False,
        'resonancePositiveResourcesIncluded': False,
        'candidateResources': records,
        'previews': [
            'artwork/validation/v0.1.7/v0.1.7-delivery-four-state-white-dark.png',
            'artwork/validation/v0.1.7/v0.1.7-native-glow-frontface-white-dark-4frames.png'],
    }
    map_bytes = json_bytes(map_doc)
    MAP_PATH.write_bytes(map_bytes)
    manifest = {
        'schema': 1,
        'version': '0.1.7-shaft-matched-native64-res0-candidate',
        'status': 'root-approved-visual-candidate-pending-independent-audit',
        'baselineJar': BASELINE_JAR.name,
        'baselineJarSha256': BASELINE_SHA,
        'changedVariantResources': 93,
        'candidateResourceCount': len(records),
        'variants': variants,
        'editMask': str(MASK_PATH.relative_to(ROOT)).replace('\\', '/'),
        'editMaskSha256': sha(mask_data),
        'underlay': str(UNDERLAY_PATH.relative_to(ROOT)).replace('\\', '/'),
        'underlaySha256': sha(underlay_data),
        'frozenMap': str(MAP_PATH.relative_to(ROOT)).replace('\\', '/'),
        'frozenMapSha256': sha(map_bytes),
        'resources': records,
        'ordinaryBaseResources': 'not included; release must restore exact 0.1.2 quartet',
        'resonancePositiveResources': 'not included; pinned 0.1.6 resources remain byte-identical',
    }
    manifest_bytes = json_bytes(manifest)
    MANIFEST_PATH.write_bytes(manifest_bytes)
    (OUT / 'candidate-manifest-v0.1.7.json').write_bytes(manifest_bytes)
    print(f'PASS v0.1.7 candidate: {len(records)} resources; {len(EDITED_INDICES)} variants; mask={len(edit_mask)}; glow pixels={len(emit)}; baseline={BASELINE_SHA}')
    print(f'Candidate: {OUT}')
    print(f'Mask: {MASK_PATH} sha256={sha(mask_data)}')
    print(f'Underlay: {UNDERLAY_PATH} sha256={sha(underlay_data)}')
    print(f'Map: {MAP_PATH} sha256={sha(map_bytes)}')
    print(f'Manifest: {MANIFEST_PATH} sha256={sha(manifest_bytes)}')


if __name__ == '__main__':
    main()
