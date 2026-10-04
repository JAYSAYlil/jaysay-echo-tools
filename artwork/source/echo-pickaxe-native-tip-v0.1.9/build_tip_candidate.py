"""Freeze the approved tiny v0.1.9 tip edit from the pinned v0.1.8 JAR."""
import copy
import hashlib
import importlib.util
import io
import json
import zipfile
from pathlib import Path, PurePosixPath

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
SRC = Path(__file__).resolve().parent
VAL = ROOT / 'artwork/validation/v0.1.9'
OUT = VAL / 'candidate'
JAR = ROOT / 'jaysay-echo-tools-0.1.8.jar'
JAR_SHA = 'BF962BA4F64395EDA4227B9C1B9CB7437B800B468DFE8EED7A24FAAEEDC07778'
ORDINARY_JAR = ROOT / 'jaysay-echo-tools-0.1.2.jar'
ORDINARY_SHA = '7312AE7B54F3DAD998815B7C7BD601B65DB1BED23A21CC7AA8448E40E082F495'
PREFIX = 'assets/echopickaxe/'
HELPER_PATH = ROOT / 'artwork/source/approved-reference-oct03-64/build_approved64_variants.py'
V018_BUILDER = ROOT / 'artwork/source/echo-pickaxe-native-edge-v0.1.8/build_native_edge_candidate.py'
PREVIEW_HELPER = ROOT / 'artwork/source/echo-pickaxe-unified-head-v0.1.6/build_unified_head_candidate.py'
MASK_PATH = SRC / 'native64-tip-edit-mask-v0.1.9.png'
UNDERLAY_PATH = SRC / 'native64-tip-underlay-v0.1.9.png'
MAP_PATH = SRC / 'native64-tip-map-v0.1.9.json'
MANIFEST_PATH = VAL / 'candidate-manifest-v0.1.9.json'
EDITED_INDICES = range(1, 32)
FRAME_COUNT = 16

# Approved minimal sharpening: preserve the old hook silhouette overall, narrow
# its terminal by two texels and extend only one texel down-left.
REMOVED = {(13, 24), (12, 25)}
ADDED = {(10, 25), (10, 26)}
BODY_SAMPLES = {
    (10, 24): (24, 38),
    (11, 24): (24, 37),
    (12, 24): (28, 36),
    (10, 25): (25, 37),
    (11, 25): (24, 38),
    (10, 26): (25, 38),
}
EDIT_MASK = REMOVED | ADDED | set(BODY_SAMPLES)


def sha(data):
    return hashlib.sha256(data).hexdigest().upper()


def png(data):
    return Image.open(io.BytesIO(data)).convert('RGBA')


def png_bytes(image):
    stream = io.BytesIO()
    image.save(stream, format='PNG', optimize=False)
    return stream.getvalue()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'Cannot load helper: {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def allowed_paths():
    return {f'{PREFIX}{folder}/item/echo_pickaxe_v{i:03d}{suffix}'
            for i in EDITED_INDICES
            for folder, suffix in (('models', '.json'), ('textures', '.png'), ('textures', '_glow.png'))}


def source_name(index, kind):
    item = f'echo_pickaxe_v{index:03d}'
    return PREFIX + ('textures/item/' + item + ('.png' if kind == 'base' else '_glow.png')
                     if kind in ('base', 'glow') else 'models/item/' + item + '.json')


def make_sprite(baseline, v031_source):
    result = baseline.copy()
    for p in REMOVED:
        result.putpixel(p, (0, 0, 0, 0))
    for p, source in BODY_SAMPLES.items():
        sample = v031_source.getpixel(source)
        assert sample[3] == 255, (p, source, sample)
        result.putpixel(p, sample)
    return result


def build():
    if (OUT / 'candidate-manifest-v0.1.9.json').exists():
        raise RuntimeError(f'Refusing to overwrite candidate: {OUT}')
    jar_bytes = JAR.read_bytes()
    ordinary_bytes = ORDINARY_JAR.read_bytes()
    assert sha(jar_bytes) == JAR_SHA, 'pinned 0.1.8 JAR SHA mismatch'
    assert sha(ordinary_bytes) == ORDINARY_SHA, 'pinned 0.1.2 JAR SHA mismatch'
    model_helper = load_module(HELPER_PATH, 'approved64_helpers_v019')
    v018 = load_module(V018_BUILDER, 'v018_shared_model_helpers')
    preview = load_module(PREVIEW_HELPER, 'preview_helpers_v019')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / PREFIX / 'models/item').mkdir(parents=True, exist_ok=True)
    (OUT / PREFIX / 'textures/item').mkdir(parents=True, exist_ok=True)

    underlay = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    mask = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    base31 = final31 = None
    resource_records, unchanged_glow_records, variant_records = [], [], []
    preview_data = {}
    sidewall_report = None
    no_glow_changes = True

    with zipfile.ZipFile(io.BytesIO(jar_bytes)) as jar, zipfile.ZipFile(io.BytesIO(ordinary_bytes)) as ordinary:
        source31 = png(jar.read(source_name(31, 'base')))
        for p in EDIT_MASK:
            underlay.putpixel(p, (0, 0, 0, 0))
            mask.putpixel(p, (255, 255, 255, 255))
        # Underlay is finalized from the representative image; variants share these pixels.
        for index in EDITED_INDICES:
            item = f'echo_pickaxe_v{index:03d}'
            base_rel = source_name(index, 'base')
            glow_rel = source_name(index, 'glow')
            model_rel = source_name(index, 'model')
            old_base_data = jar.read(base_rel)
            old_sprite = png(old_base_data)
            sprite = make_sprite(old_sprite, source31)
            assert all(old_sprite.getpixel(p) == source31.getpixel(p) for p in EDIT_MASK if p not in ADDED | REMOVED), index
            assert {p for p in EDIT_MASK if old_sprite.getpixel(p)[3] and sprite.getpixel(p)[3] == 0} == REMOVED
            assert {p for p in EDIT_MASK if not old_sprite.getpixel(p)[3] and sprite.getpixel(p)[3]} == ADDED
            assert all(sprite.getpixel(p) == make_sprite(source31, source31).getpixel(p) for p in EDIT_MASK)
            if index == 31:
                base31, final31 = old_sprite, sprite
                for p in EDIT_MASK:
                    underlay.putpixel(p, sprite.getpixel(p))

            old_glow_data = jar.read(glow_rel)
            old_glow = png(old_glow_data)
            assert old_glow.size == (64, 1024)
            for f in range(FRAME_COUNT):
                glow_frame = old_glow.crop((0, f * 64, 64, (f + 1) * 64))
                assert all(glow_frame.getpixel(p)[3] == 0 for p in REMOVED | ADDED)
            # All sharpened edge pixels are nonemissive in the pinned baseline, so
            # keep its animated strip byte-for-byte rather than re-encode it.
            assert all(old_glow.getpixel((x, y + f * 64))[3] == 0
                       for x, y in EDIT_MASK for f in range(FRAME_COUNT))

            old_model = json.loads(jar.read(model_rel).decode('utf-8'))
            lit = v018.opaque(old_glow.crop((0, 0, 64, 64)))
            expected_model, _, expected_lit = model_helper.model_for_state(old_model, item, sprite, lit)
            model_helper.validate_model(sprite, expected_model, expected_lit, item)
            model, sidewall_changes = v018.update_model_preserving_geometry(
                old_model, expected_model, REMOVED, ADDED, REMOVED | ADDED)
            model_helper.validate_model(sprite, model, expected_lit, item)
            assert model.get('overrides', []) == old_model.get('overrides', [])
            if sidewall_report is None:
                sidewall_report = sidewall_changes
            else:
                assert sidewall_changes == sidewall_report

            new_base_data = png_bytes(sprite)
            new_model_data = json_bytes(model)
            for rel, data in ((base_rel, new_base_data), (model_rel, new_model_data)):
                target = OUT / Path(*PurePosixPath(rel).parts)
                target.write_bytes(data)
                resource_records.append({'path': rel, 'sha256': sha(data), 'bytes': len(data),
                                         'baselineSha256': sha(jar.read(rel))})
            unchanged_glow_records.append({'path': glow_rel, 'sha256': sha(old_glow_data),
                                           'bytes': len(old_glow_data), 'status': 'byte-identical-to-baseline'})
            variant_records.append({'index': index, 'baseSha256': sha(new_base_data),
                                    'modelSha256': sha(new_model_data), 'glowSha256': sha(old_glow_data),
                                    'emissiveTexels': len(expected_lit)})
            if index in (24, 31):
                preview_data[index] = (sprite, old_glow, model)

        underlay_data, mask_data = png_bytes(underlay), png_bytes(mask)
        UNDERLAY_PATH.write_bytes(underlay_data)
        MASK_PATH.write_bytes(mask_data)
        assert base31 is not None and final31 is not None
        assert {p for p in EDIT_MASK if base31.getpixel(p) != final31.getpixel(p)} == EDIT_MASK
        assert no_glow_changes

        ordinary_sprite = png(ordinary.read(PREFIX + 'textures/item/echo_pickaxe.png'))
        ordinary_glow = png(ordinary.read(PREFIX + 'textures/item/echo_pickaxe_glow.png'))
        ordinary_model = json.loads(ordinary.read(PREFIX + 'models/item/echo_pickaxe.json').decode('utf-8'))
        red_sprite = png(jar.read(PREFIX + 'textures/item/echo_pickaxe_v095.png'))
        red_glow = png(jar.read(PREFIX + 'textures/item/echo_pickaxe_v095_glow.png'))
        red_model = json.loads(jar.read(PREFIX + 'models/item/echo_pickaxe_v095.json').decode('utf-8'))
        states = [
            ('普通0.1.2', v018.frontface(ordinary_sprite, ordinary_glow, ordinary_model, 0)),
            ('分频III v024', v018.frontface(*preview_data[24], 0)),
            ('无共振满级 v031', v018.frontface(*preview_data[31], 0)),
            ('红共振II v095', v018.frontface(red_sprite, red_glow, red_model, 0)),
        ]
        preview.save_delivery_board(states, VAL / 'v0.1.9-delivery-four-state-white-dark.png')
        preview.save_glow_board([('分频III v024', *preview_data[24]), ('无共振满级 v031', *preview_data[31])],
                                VAL / 'v0.1.9-tip-native-glow-frontface-white-dark-4frames.png')

    sample_records = []
    for target, source in sorted(BODY_SAMPLES.items()):
        rgba = list(source31.getpixel(source))
        sample_records.append({'target': list(target), 'sourceV031Shaft': list(source), 'sourceRGBA': rgba,
                               'sourceGlowFramesAlpha': [0] * FRAME_COUNT})
    pixels = []
    for p in sorted(EDIT_MASK, key=lambda q: (q[1], q[0])):
        pixels.append({'pixel': list(p), 'baselineRGBA': list(base31.getpixel(p)),
                       'frozenRGBA': list(final31.getpixel(p)),
                       'change': 'removed-alpha' if p in REMOVED else ('added-alpha' if p in ADDED else 'rgb-only'),
                       'emissiveSource': None if final31.getpixel(p)[3] == 0 else 'pinned v0.1.8 frame unchanged; alpha 0'})
    map_doc = {
        'schema': 3,
        'status': 'root-approved-tip-draft-frozen-candidate-pending-audit',
        'version': '0.1.9-native64-tip-sharpening',
        'baselineJar': JAR.name, 'baselineJarSha256': JAR_SHA,
        'editMask': str(MASK_PATH.relative_to(ROOT)).replace('\\', '/'),
        'editMaskSha256': sha(mask_data), 'editMaskPixels': len(EDIT_MASK),
        'underlay': str(UNDERLAY_PATH.relative_to(ROOT)).replace('\\', '/'),
        'underlaySha256': sha(underlay_data),
        'outline': {'removed': [list(p) for p in sorted(REMOVED)], 'added': [list(p) for p in sorted(ADDED)],
                    'fourConnected': True, 'extensionTexels': 1, 'description': 'Row 24 narrows to three texels; row 25 shifts to two; row 26 ends in one connected texel.'},
        'nativeBodyColorSamples': sample_records,
        'frozenRGBAByPixel': pixels,
        'glowContract': 'No edited tip texel emits in any of 16 pinned baseline frames. All 31 res0 glow strips are kept byte-identical; no emission is added to the sharpened edge.',
        'modelContract': 'Exactly two elements removed and two added. Added prisms are helper-generated native64 .25 x .25 x 1.0 units (Z 7.5..8.5); survivors preserve geometry and texel-center UV. Sidewall visibility changes follow only adjacent alpha add/remove.',
        'sidewallExposureChanges': sidewall_report,
        'resourceCounts': {'changed': len(resource_records), 'byteIdenticalGlow': len(unchanged_glow_records),
                           'allowedTotal': len(resource_records) + len(unchanged_glow_records)},
        'ordinary012': 'Not included; exact original resource quartet retained.',
        'resonancePositive': 'Not included; remains byte-identical to pinned 0.1.8.',
        'unchangedGlow': unchanged_glow_records,
        'previews': ['artwork/validation/v0.1.9/v0.1.9-delivery-four-state-white-dark.png',
                     'artwork/validation/v0.1.9/v0.1.9-tip-native-glow-frontface-white-dark-4frames.png'],
    }
    map_data = json_bytes(map_doc)
    MAP_PATH.write_bytes(map_data)
    manifest = {
        'schema': 1, 'version': '0.1.9-native64-tip-sharpening-candidate',
        'status': 'root-approved-draft-frozen-awaiting-independent-audit',
        'baselineJar': JAR.name, 'baselineJarSha256': JAR_SHA,
        'allowedResourceCount': len(allowed_paths()), 'changedResourceCount': len(resource_records),
        'unchangedResourceCount': len(unchanged_glow_records),
        'editMask': str(MASK_PATH.relative_to(ROOT)).replace('\\', '/'), 'editMaskSha256': sha(mask_data),
        'underlay': str(UNDERLAY_PATH.relative_to(ROOT)).replace('\\', '/'), 'underlaySha256': sha(underlay_data),
        'map': str(MAP_PATH.relative_to(ROOT)).replace('\\', '/'), 'mapSha256': sha(map_data),
        'resources': resource_records, 'unchanged': unchanged_glow_records, 'variants': variant_records,
        'productionChanged': False,
    }
    manifest_data = json_bytes(manifest)
    MANIFEST_PATH.write_bytes(manifest_data)
    (OUT / 'candidate-manifest-v0.1.9.json').write_bytes(manifest_data)
    print(f'PASS candidate: allowed={len(allowed_paths())}, changed={len(resource_records)}, unchangedGlow={len(unchanged_glow_records)}')
    print(f'editMask={len(EDIT_MASK)}; alpha -{len(REMOVED)} +{len(ADDED)}; model sidewall changes={len(sidewall_report)}')
    print(f'mask SHA {sha(mask_data)}; underlay SHA {sha(underlay_data)}; map SHA {sha(map_data)}; manifest SHA {sha(manifest_data)}')


if __name__ == '__main__':
    build()
