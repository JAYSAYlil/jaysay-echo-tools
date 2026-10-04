"""Freeze/build the v0.1.8 res0 native-edge candidate from pinned 0.1.7 assets."""
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
VAL = ROOT / 'artwork/validation/v0.1.8'
OUT = VAL / 'candidate'
PREFIX = 'assets/echopickaxe/'
BASELINE = ROOT / 'jaysay-echo-tools-0.1.7.jar'
BASELINE_SHA = 'A8DF7D5E282FC46487B6EBC0F3D6DFC1F13B2BF3C26CA9842F8BA716BFF92B24'
ORDINARY_JAR = ROOT / 'jaysay-echo-tools-0.1.2.jar'
ORDINARY_SHA = '7312AE7B54F3DAD998815B7C7BD601B65DB1BED23A21CC7AA8448E40E082F495'
COMMON = ROOT / 'artwork/source/approved-reference-oct03-64/common64-unupgraded.png'
COMMON_GLOW = ROOT / 'artwork/source/approved-reference-oct03-64/common64-glow.png'
COMPONENT_MAP = ROOT / 'artwork/source/approved-reference-oct03-64/native64-component-map.json'
MODEL_HELPERS = ROOT / 'artwork/source/approved-reference-oct03-64/build_approved64_variants.py'
DRAFT_SCRIPT = SRC / 'draft_native64_edge_refinement.py'
UNDERLAY_017 = ROOT / 'artwork/source/echo-pickaxe-unified-head-v0.1.7/native64-shaft-derived-underlay-v0.1.7.png'
MAP_017 = ROOT / 'artwork/source/echo-pickaxe-unified-head-v0.1.7/unified-head-map-v0.1.7.json'
UNDERLAY_PATH = SRC / 'native64-edge-underlay-v0.1.8.png'
MASK_PATH = SRC / 'native64-edge-edit-mask-v0.1.8.png'
MAP_PATH = SRC / 'native64-edge-map-v0.1.8.json'
MANIFEST_PATH = VAL / 'candidate-manifest-v0.1.8.json'
EDITED_INDICES = range(1, 32)
FRAME_COUNT = 16
SIDES = ('west', 'east', 'up', 'down')
SIDE_DIR = {'west': (-1, 0), 'east': (1, 0), 'up': (0, -1), 'down': (0, 1)}


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
        raise RuntimeError(f'Cannot import helper {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def opaque(image):
    return {(x, y) for y in range(image.height) for x in range(image.width) if image.getpixel((x, y))[3]}


def pos_of(element):
    return (round(element['from'][0] * 4), round((16 - element['to'][1]) * 4))


def index_elements(model):
    result = {}
    for element in model['elements']:
        p = pos_of(element)
        if p in result:
            raise ValueError(f'duplicate model element at {p}')
        result[p] = element
    return result


def update_model_preserving_geometry(old_model, expected_model, removed, added, alpha_changed):
    old_map, expected_map = index_elements(old_model), index_elements(expected_model)
    assert set(old_map) - set(removed) | set(added) == set(expected_map)
    sidewall_changes = []
    result = copy.deepcopy(old_model)
    new_elements = []
    for p, old_element in old_map.items():
        if p in removed:
            continue
        expected = expected_map[p]
        e = copy.deepcopy(old_element)
        assert e['from'] == expected['from'] and e['to'] == expected['to']
        assert e.get('shade') == expected.get('shade')
        # North/south keep exact texel-center UV and all other source fields;
        # only the glow/layer ownership and light tag may follow changed glow.
        for face_name in ('north', 'south'):
            face = e['faces'][face_name]
            target = expected['faces'][face_name]
            assert face.get('uv') == target.get('uv')
            for key in ('texture', 'forge_data'):
                if key in target:
                    face[key] = copy.deepcopy(target[key])
                else:
                    face.pop(key, None)
        # Existing sidewalls remain byte-structure-equivalent unless an alpha
        # add/remove on the neighboring texel changes whether the face is exposed.
        for side, (dx, dy) in SIDE_DIR.items():
            was, now = side in e['faces'], side in expected['faces']
            if was == now:
                if was:
                    assert e['faces'][side] == expected['faces'][side]
                continue
            neighbor = (p[0] + dx, p[1] + dy)
            assert neighbor in alpha_changed, f'nonlocal sidewall change at {p}/{side}'
            if now:
                e['faces'][side] = copy.deepcopy(expected['faces'][side])
                action = 'added'
            else:
                del e['faces'][side]
                action = 'removed'
            sidewall_changes.append({'pixel': list(p), 'face': side, 'change': action,
                                     'causedByAlphaAt': list(neighbor)})
        new_elements.append(e)
    for p in sorted(added, key=lambda q: (q[1], q[0])):
        # The approved helper supplies the native64 prism: .25 x .25 x 1.0 world units.
        element = copy.deepcopy(expected_map[p])
        assert element['from'][2] == 7.5 and element['to'][2] == 8.5
        assert element['to'][0] - element['from'][0] == .25
        assert element['to'][1] - element['from'][1] == .25
        new_elements.append(element)
    result['elements'] = new_elements
    assert set(index_elements(result)) == set(expected_map)
    return result, sidewall_changes


def frontface(sprite, glow, model, frame):
    result = sprite.copy()
    frame_size = sprite.width
    if sprite.width != sprite.height or glow.width != frame_size or glow.height % frame_size:
        raise ValueError(f'incompatible sprite/glow dimensions: {sprite.size}, {glow.size}')
    frame_image = glow.crop((0, frame * frame_size, frame_size, (frame + 1) * frame_size))
    dst = result.load()
    for element in model['elements']:
        if element['faces']['north']['texture'] != '#glow':
            continue
        scale = frame_size / 16
        x = round(element['from'][0] * scale)
        y = round((16 - element['to'][1]) * scale)
        rgba = frame_image.getpixel((x, y))
        if rgba[3]:
            dst[x, y] = rgba
    return result


def main():
    if (OUT / 'candidate-manifest-v0.1.8.json').exists():
        raise RuntimeError(f'Refusing to overwrite candidate directory: {OUT}')
    baseline_data, ordinary_data = BASELINE.read_bytes(), ORDINARY_JAR.read_bytes()
    assert sha(baseline_data) == BASELINE_SHA, 'pinned 0.1.7 JAR SHA mismatch'
    assert sha(ordinary_data) == ORDINARY_SHA, 'pinned 0.1.2 JAR SHA mismatch'
    draft = load_module(DRAFT_SCRIPT, 'native_edge_draft_v018')
    helper = load_module(MODEL_HELPERS, 'approved64_model_helpers_v018')
    previews_helper = load_module(ROOT / 'artwork/source/echo-pickaxe-unified-head-v0.1.6/build_unified_head_candidate.py',
                                  'preview_board_helpers_v018')
    common = Image.open(COMMON).convert('RGBA')
    common_glow = Image.open(COMMON_GLOW).convert('RGBA')
    old_underlay_data = UNDERLAY_017.read_bytes()
    old_underlay = png(old_underlay_data)
    old_map = json.loads(MAP_017.read_text(encoding='utf-8'))
    source_map = {(v[0], v[1]): (v[2], v[3]) for v in old_map['sourceCoordinatesAndRGBA']}
    module_data = json.loads(COMPONENT_MAP.read_text(encoding='utf-8'))['components']
    module_pixels = {(x, y) for name in ('frequency', 'tuning', 'extension')
                     for tier in module_data[name]['tiers'] for x, y, *_ in tier['texels']}
    source_for_color = dict(draft.FISSURE_BRIDGE)
    source_for_color.update(draft.CENTRAL_CYAN_SOURCES)

    with zipfile.ZipFile(io.BytesIO(baseline_data)) as base_zip, \
            zipfile.ZipFile(io.BytesIO(ordinary_data)) as ordinary_zip:
        prepared, alpha_removed, alpha_added, local_source_records, edge_source_records = {}, None, None, None, None
        for index in (24, 31):
            item = f'echo_pickaxe_v{index:03d}'
            baseline = png(base_zip.read(PREFIX + f'textures/item/{item}.png'))
            outlined, removed, added, local_sources, edge_sources = draft.apply_outline(baseline, old_underlay, common, source_map)
            final, central_records = draft.add_central_bridge(outlined, common, common_glow)
            if alpha_removed is None:
                alpha_removed, alpha_added = removed, added
                local_source_records, edge_source_records = local_sources, edge_sources
            else:
                assert removed == alpha_removed and added == alpha_added
                assert local_sources == local_source_records and edge_sources == edge_source_records
            assert not (set(removed) | set(added) | set(local_sources) | set(draft.CENTRAL_CYAN_SOURCES)) & module_pixels
            if index == 31:
                reference = png((VAL / 'draft-2/v031-native64-cyan-bridge-draft.png').read_bytes())
                assert all(final.getpixel((x, y)) == reference.getpixel((x, y))
                           for y in range(64) for x in range(64)), 'generator differs from reviewed v031 draft'
            prepared[index] = (baseline, final)

        base31, draft31 = prepared[31]
        edit_mask = {(x, y) for y in range(64) for x in range(64)
                     if base31.getpixel((x, y)) != draft31.getpixel((x, y))}
        assert alpha_removed == {p for p in edit_mask if base31.getpixel(p)[3] and not draft31.getpixel(p)[3]}
        assert alpha_added == {p for p in edit_mask if not base31.getpixel(p)[3] and draft31.getpixel(p)[3]}
        assert len(alpha_removed) == 10 and len(alpha_added) == 7
        assert len(draft.CENTRAL_CYAN_SOURCES) == 15
        assert set(draft.CENTRAL_CYAN_SOURCES) <= edit_mask
        assert not edit_mask & module_pixels

        underlay = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        mask_image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        for p in edit_mask:
            underlay.putpixel(p, draft31.getpixel(p))
            mask_image.putpixel(p, (255, 255, 255, 255))
        underlay_data, mask_data = png_bytes(underlay), png_bytes(mask_image)
        UNDERLAY_PATH.write_bytes(underlay_data)
        MASK_PATH.write_bytes(mask_data)

        # Each changed opaque base texel has a source-coordinate record. Deleted
        # alpha texels remain transparent in all edited glow frames.
        source_for_pixel = dict(local_source_records)
        source_for_pixel.update(draft.CENTRAL_CYAN_SOURCES)
        source_for_pixel.update(edge_source_records)
        source_frames = {}
        native_frames = []
        emit_inside = set()
        for f in range(FRAME_COUNT):
            frame = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
            for p in edit_mask:
                if draft31.getpixel(p)[3] == 0:
                    continue
                src = source_for_pixel.get(p)
                if src is None:
                    # RGB-only edits are explicitly mapped above; an unmapped
                    # changed opaque texel is a reviewable data error.
                    raise RuntimeError(f'changed opaque texel has no native source: {p}')
                rgba = common_glow.getpixel((src[0], src[1] + f * 64))
                if rgba[3]:
                    frame.putpixel(p, rgba)
                    emit_inside.add(p)
            native_frames.append(frame)
        for p, src in source_for_pixel.items():
            if p not in edit_mask or draft31.getpixel(p)[3] == 0:
                continue
            samples = [common_glow.getpixel((src[0], src[1] + f * 64)) for f in range(FRAME_COUNT)]
            assert len({v[3] for v in samples}) == 1, f'variable source glow alpha for {p}->{src}'
            source_frames[p] = samples
        assert all(opaque(frame) == emit_inside for frame in native_frames), 'new glow alpha changes across frames'

        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / PREFIX / 'models/item').mkdir(parents=True, exist_ok=True)
        (OUT / PREFIX / 'textures/item').mkdir(parents=True, exist_ok=True)
        candidate_resources, variant_records, previews = [], [], {}
        sidewall_report = None
        alpha_changed = alpha_removed | alpha_added
        for index in EDITED_INDICES:
            item = f'echo_pickaxe_v{index:03d}'
            base_rel = PREFIX + f'textures/item/{item}.png'
            glow_rel = PREFIX + f'textures/item/{item}_glow.png'
            model_rel = PREFIX + f'models/item/{item}.json'
            baseline_sprite_data = base_zip.read(base_rel)
            baseline_sprite = png(baseline_sprite_data)
            sprite = baseline_sprite.copy()
            for p in edit_mask:
                sprite.putpixel(p, underlay.getpixel(p))
            assert all(sprite.getpixel(p)[3] == baseline_sprite.getpixel(p)[3]
                       for p in edit_mask if p not in alpha_changed)
            assert all(sprite.getpixel((x, y)) == baseline_sprite.getpixel((x, y))
                       for y in range(64) for x in range(64) if (x, y) not in edit_mask)

            baseline_glow = png(base_zip.read(glow_rel))
            assert baseline_glow.size == (64, 1024)
            glow = baseline_glow.copy()
            for f, native_frame in enumerate(native_frames):
                frame = glow.crop((0, f * 64, 64, (f + 1) * 64))
                for p in edit_mask:
                    frame.putpixel(p, native_frame.getpixel(p))
                glow.paste(frame, (0, f * 64))
                before_frame = baseline_glow.crop((0, f * 64, 64, (f + 1) * 64))
                assert all(frame.getpixel((x, y)) == before_frame.getpixel((x, y))
                           for y in range(64) for x in range(64) if (x, y) not in edit_mask)
            assert all(opaque(glow.crop((0, f * 64, 64, (f + 1) * 64)))
                       == opaque(glow.crop((0, 0, 64, 64))) for f in range(FRAME_COUNT))

            lit = opaque(glow.crop((0, 0, 64, 64)))
            old_model = json.loads(base_zip.read(model_rel).decode('utf-8'))
            expected_model, _, expected_lit = helper.model_for_state(old_model, item, sprite, lit)
            helper.validate_model(sprite, expected_model, expected_lit, item)
            model, sidewall_changes = update_model_preserving_geometry(
                old_model, expected_model, alpha_removed, alpha_added, alpha_changed)
            helper.validate_model(sprite, model, expected_lit, item)
            if sidewall_report is None:
                sidewall_report = sidewall_changes
            else:
                assert sidewall_changes == sidewall_report
            assert model.get('overrides', []) == old_model.get('overrides', [])

            payloads = {model_rel: json_bytes(model), base_rel: png_bytes(sprite), glow_rel: png_bytes(glow)}
            hashes = {}
            for rel, data in payloads.items():
                target = OUT / Path(*PurePosixPath(rel).parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                record = {'path': rel, 'sha256': sha(data), 'bytes': len(data)}
                candidate_resources.append(record)
                hashes[rel.rsplit('/', 1)[-1]] = sha(data)
            variant_records.append({'index': index, 'levels': helper.levels_for(index),
                                    'opaqueTexels': len(opaque(sprite)), 'emissiveTexels': len(expected_lit),
                                    'sha256': hashes})
            if index in (24, 31):
                previews[index] = (sprite, glow, model)

        # Preview exact front-face model glow and four use states.
        ordinary_sprite = png(ordinary_zip.read(PREFIX + 'textures/item/echo_pickaxe.png'))
        ordinary_glow = png(ordinary_zip.read(PREFIX + 'textures/item/echo_pickaxe_glow.png'))
        ordinary_model = json.loads(ordinary_zip.read(PREFIX + 'models/item/echo_pickaxe.json').decode('utf-8'))
        red_sprite = png(base_zip.read(PREFIX + 'textures/item/echo_pickaxe_v095.png'))
        red_glow = png(base_zip.read(PREFIX + 'textures/item/echo_pickaxe_v095_glow.png'))
        red_model = json.loads(base_zip.read(PREFIX + 'models/item/echo_pickaxe_v095.json').decode('utf-8'))
        states = [
            ('普通0.1.2', frontface(ordinary_sprite, ordinary_glow, ordinary_model, 0)),
            ('分频III v024', frontface(*previews[24], 0)),
            ('无共振满级 v031', frontface(*previews[31], 0)),
            ('红共振II v095', frontface(red_sprite, red_glow, red_model, 0)),
        ]
        previews_helper.save_delivery_board(states, VAL / 'v0.1.8-delivery-four-state-white-dark.png')
        previews_helper.save_glow_board([('分频III v024', *previews[24]), ('无共振满级 v031', *previews[31])],
                                        VAL / 'v0.1.8-native-glow-frontface-white-dark-4frames.png')

    # Source-coordinate records include exact RGBA and all 16 sampled glow texels.
    source_kind = {}
    source_kind.update({p: 'approved common64 shaft fissure/facet' for p in draft.FISSURE_BRIDGE})
    source_kind.update({p: 'approved common64 shaft emissive crack bridge' for p in draft.CENTRAL_CYAN_SOURCES})
    source_kind.update({p: 'approved common64 shaft grain for refined alpha edge' for p in edge_source_records})
    pixel_records = []
    for x, y in sorted(edit_mask, key=lambda p: (p[1], p[0])):
        p = (x, y)
        src = source_for_pixel.get(p)
        pixel_records.append({
            'pixel': [x, y], 'baselineRGBA': list(base31.getpixel(p)), 'frozenRGBA': list(draft31.getpixel(p)),
            'change': 'deleted-alpha' if p in alpha_removed else ('added-alpha' if p in alpha_added else 'rgb'),
            'common64Source': list(src) if src else None,
            'sourceKind': source_kind.get(p),
            'sourceRGB': list(common.getpixel(src)) if src else None,
            'sourceGlowFramesRGBA': source_frames.get(p),
        })
    map_doc = {
        'schema': 3,
        'status': 'root-approved-visual-freeze-candidate-pending-independent-audit',
        'version': '0.1.8-native64-curved-edge-cyan-bridge',
        'baselineJar': BASELINE.name, 'baselineJarSha256': BASELINE_SHA,
        'ordinaryJar': ORDINARY_JAR.name, 'ordinaryJarSha256': ORDINARY_SHA,
        'outlineContract': 'The approved v0.1.8 outline is the frozen 0.1.7 alpha with exactly 10 opaque texels removed and 7 added. The old hook macro-curve and size are retained; no other res0 silhouette texel changes.',
        'alphaRemoved': [list(p) for p in sorted(alpha_removed,key=lambda p:(p[1],p[0]))],
        'alphaAdded': [list(p) for p in sorted(alpha_added,key=lambda p:(p[1],p[0]))],
        'alphaBefore': len(opaque(base31)), 'alphaAfter': len(opaque(draft31)),
        'underlay': str(UNDERLAY_PATH.relative_to(ROOT)).replace('\\','/'),
        'underlaySha256': sha(underlay_data),
        'editMask': str(MASK_PATH.relative_to(ROOT)).replace('\\','/'),
        'editMaskSha256': sha(mask_data), 'editMaskPixels': len(edit_mask),
        'frozenRGBAByPixel': pixel_records,
        'localFissureTexels': [list(p) for p in sorted(draft.FISSURE_BRIDGE)],
        'centralBridgeTexels': [list(p) for p in sorted(draft.CENTRAL_CYAN_SOURCES)],
        'centralBridgeContract': '15 native64 texels, one narrow natural bend with two small junctions, sampled from actual common64 shaft emissive cracks. Each pixel RGB and all 16 source glow-frame RGBA values are recorded; glow is not synthesized or attenuated.',
        'common64Sha256': sha(COMMON.read_bytes()), 'common64GlowSha256': sha(COMMON_GLOW.read_bytes()),
        'moduleOverlap': 0,
        'glowContract': 'Only exact editMask pixels are replaced in each baseline glow frame. Deleted alpha coordinates are transparent for every frame; added outline and cyan texels use their recorded common64-glow source coordinate; all glow outside editMask is identical to pinned 0.1.7. Per-pixel alpha is fixed across 16 frames; mcmeta is not changed.',
        'glowFrameCount': FRAME_COUNT, 'glowTicksPerFrame': 3,
        'glowPixelsInEditMask': len(emit_inside),
        'modelContract': 'Surviving prisms retain source geometry and texel-center UVs. Existing sidewalls change only when an adjacent alpha add/remove changes exposure. Added prisms come from build_approved64_variants.model_for_state and use x/y=.25, z=7.5..8.5. North/south glow ownership follows the frozen frame-0 glow mask.',
        'sidewallExposureChanges': sidewall_report,
        'candidateResourceCount': len(candidate_resources), 'changedVariantResourceCount': 93,
        'candidateResources': candidate_resources,
        'ordinaryResourcesIncluded': False, 'resonancePositiveResourcesIncluded': False,
        'productionChanged': False,
        'previews':['artwork/validation/v0.1.8/v0.1.8-delivery-four-state-white-dark.png',
                    'artwork/validation/v0.1.8/v0.1.8-native-glow-frontface-white-dark-4frames.png'],
    }
    map_bytes = json_bytes(map_doc); MAP_PATH.write_bytes(map_bytes)
    manifest = {
        'schema': 1, 'version':'0.1.8-native64-curved-edge-cyan-bridge-candidate',
        'status':'root-approved-visual-candidate-pending-independent-audit',
        'baselineJar':BASELINE.name,'baselineJarSha256':BASELINE_SHA,
        'changedVariantResources':93,'candidateResourceCount':len(candidate_resources),
        'editMask':str(MASK_PATH.relative_to(ROOT)).replace('\\','/'),'editMaskSha256':sha(mask_data),
        'underlay':str(UNDERLAY_PATH.relative_to(ROOT)).replace('\\','/'),'underlaySha256':sha(underlay_data),
        'frozenMap':str(MAP_PATH.relative_to(ROOT)).replace('\\','/'),'frozenMapSha256':sha(map_bytes),
        'variants':variant_records,'resources':candidate_resources,
        'ordinaryBaseResources':'not included; exact 0.1.2 resource quartet remains unchanged',
        'resonancePositiveResources':'not included; remain byte-identical to 0.1.7 baseline',
    }
    manifest_bytes=json_bytes(manifest)
    MANIFEST_PATH.write_bytes(manifest_bytes)
    (OUT/'candidate-manifest-v0.1.8.json').write_bytes(manifest_bytes)
    print(f'PASS candidate: 93 resources; variants=31; editMask={len(edit_mask)}; alpha -{len(alpha_removed)} +{len(alpha_added)}; bridge={len(draft.CENTRAL_CYAN_SOURCES)}; glowAlpha={len(emit_inside)}')
    print(f'Candidate: {OUT}')
    print(f'Mask SHA: {sha(mask_data)}')
    print(f'Underlay SHA: {sha(underlay_data)}')
    print(f'Map SHA: {sha(map_bytes)}')
    print(f'Manifest SHA: {sha(manifest_bytes)}')


if __name__ == '__main__':
    main()
