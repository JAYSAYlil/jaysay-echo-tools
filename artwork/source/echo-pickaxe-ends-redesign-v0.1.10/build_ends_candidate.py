"""Build the 0.1.10 refined head/shaft candidate from the pinned 0.1.9 JAR."""
import hashlib
import importlib.util
import io
import json
import zipfile
from pathlib import Path, PurePosixPath

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
SRC = Path(__file__).resolve().parent
VAL = ROOT / 'artwork/validation/v0.1.10'
OUT = VAL / 'refined-ends-candidate'
JAR = ROOT / 'jaysay-echo-tools-0.1.9.jar'
JAR_SHA = 'BB7136E6B343E7371A161E3A6D27A9A81311F9850C54FA0C6DA41FB17FA430B6'
PREFIX = 'assets/echopickaxe/'
ASSET = PREFIX + 'textures/item/echo_pickaxe_v{:03d}{}.png'
MODEL = PREFIX + 'models/item/echo_pickaxe_v{:03d}.json'
DRAFT_SCRIPT = SRC / 'draw_ends_draft.py'
MODEL_HELPER = ROOT / 'artwork/source/approved-reference-oct03-64/build_approved64_variants.py'
GEOMETRY_HELPER = ROOT / 'artwork/source/echo-pickaxe-native-edge-v0.1.8/build_native_edge_candidate.py'
PREVIEW_HELPER = ROOT / 'artwork/source/echo-pickaxe-unified-head-v0.1.6/build_unified_head_candidate.py'
COMPONENTS = ROOT / 'artwork/source/approved-reference-oct03-64/native64-component-map.json'
MASK_PATH = SRC / 'v0.1.10-any-variant-edit-mask.png'
MAP_PATH = SRC / 'v0.1.10-resource-map.json'
MANIFEST_PATH = OUT / 'candidate-manifest-v0.1.10.json'
FRAME_COUNT = 16
EDITED = tuple(range(1, 96))
ALL_PIXELS = tuple((x, y) for y in range(64) for x in range(64))


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


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'Cannot import helper: {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def resource_paths(index):
    stem = f'echo_pickaxe_v{index:03d}'
    return {'base': ASSET.format(index, ''), 'glow': ASSET.format(index, '_glow'), 'model': MODEL.format(index)}


def candidate_path(rel):
    return OUT / Path(*PurePosixPath(rel).parts)


def font(size):
    for path in (r'C:\Windows\Fonts\msyh.ttc', r'C:\Windows\Fonts\arial.ttf'):
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def composite(image, background):
    target = Image.new('RGBA', image.size, background + (255,))
    target.alpha_composite(image)
    return target.convert('RGB')


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


def draw_delivery_board(states, path):
    scale, cell_w, label_h, gap, margin = 3, 212, 28, 10, 12
    sprite_size = 64 * scale
    cell_h = sprite_size + label_h + gap
    board = Image.new('RGB', (margin * 2 + len(states) * cell_w, margin * 2 + 2 * cell_h), (243, 245, 247))
    draw = ImageDraw.Draw(board)
    f = font(14)
    for row, bg in enumerate(((255, 255, 255), (23, 29, 37))):
        y = margin + row * cell_h
        draw.text((margin, y), '白底' if row == 0 else '暗底', fill=(25, 30, 36), font=f)
        for col, (label, face) in enumerate(states):
            x = margin + col * cell_w
            draw.text((x + 3, y), label, fill=(25, 30, 36), font=f)
            face = face.resize((sprite_size, sprite_size), Image.Resampling.NEAREST)
            board.paste(composite(face, bg), (x, y + label_h))
    board.save(path)


def draw_actual_glow(states, path):
    scale, margin, label_h = 2, 10, 25
    sprite_size = 64 * scale
    col_w, row_h = sprite_size + 6, sprite_size + label_h + 4
    board = Image.new('RGB', (margin * 2 + col_w * FRAME_COUNT,
                              margin * 2 + row_h * len(states) * 2), (244, 246, 248))
    draw = ImageDraw.Draw(board)
    f = font(13)
    preview = load_module(PREVIEW_HELPER, 'ends10_glow_preview')
    for state_idx, (name, sprite, glow, model) in enumerate(states):
        for bg_idx, bg in enumerate(((255, 255, 255), (23, 29, 37))):
            row = state_idx * 2 + bg_idx
            y = margin + row * row_h
            draw.text((4, y + 3), f'{name} {"白" if bg_idx == 0 else "暗"}', fill=(25, 30, 36), font=f)
            for frame in range(FRAME_COUNT):
                x = margin + frame * col_w
                draw.text((x + 2, y + 3), str(frame), fill=(25, 30, 36), font=f)
                face = preview.frontface(sprite, glow, model, frame)
                face = face.resize((sprite_size, sprite_size), Image.Resampling.NEAREST)
                board.paste(composite(face, bg), (x, y + label_h))
    board.save(path)


def exact_changes(old, new):
    return [(x, y, old.getpixel((x, y)), new.getpixel((x, y)))
            for x, y in ALL_PIXELS if old.getpixel((x, y)) != new.getpixel((x, y))]


def change_records(changes):
    return [{'pixel': [x, y], 'before': list(before), 'after': list(after)}
            for x, y, before, after in changes]


def make_glow(old_base, new_base, old_glow, changed, removed, added):
    glow = old_glow.copy()
    per_frame = {}
    for frame in range(FRAME_COUNT):
        offset = frame * 64
        frame_changes = []
        for x, y in changed:
            old_rgba = old_base.getpixel((x, y))
            new_rgba = new_base.getpixel((x, y))
            before = glow.getpixel((x, y + offset))
            if (x, y) in removed or not new_rgba[3]:
                after = (0, 0, 0, 0)
            elif (x, y) in added or not old_rgba[3]:
                # New contour texels inherit no emission unless the pinned source
                # had an actual emitter at this same texel (it cannot if transparent).
                after = (0, 0, 0, 0)
            elif before[3]:
                rgb = tuple(max(0, min(255, before[c] + new_rgba[c] - old_rgba[c])) for c in range(3))
                after = (*rgb, before[3])
            else:
                after = before
            if after != before:
                glow.putpixel((x, y + offset), after)
                frame_changes.append((x, y, before, after))
        per_frame[str(frame)] = frame_changes
    return glow, per_frame


def main():
    if OUT.exists() and any(path.is_file() for path in OUT.rglob('*')):
        raise RuntimeError(f'Refusing to overwrite existing candidate: {OUT}')
    jar_data = JAR.read_bytes()
    assert sha(jar_data) == JAR_SHA, 'pinned 0.1.9 JAR SHA mismatch'
    component_doc = json.loads(COMPONENTS.read_text(encoding='utf-8'))
    draft = load_module(DRAFT_SCRIPT, 'ends10_frozen_draft')
    model_helper = load_module(MODEL_HELPER, 'ends10_model_helper')
    geometry = load_module(GEOMETRY_HELPER, 'ends10_geometry_helper')
    preview = load_module(PREVIEW_HELPER, 'ends10_preview_helper')

    OUT.mkdir(parents=True, exist_ok=True)
    for sub in ('models/item', 'textures/item'):
        (OUT / PREFIX / sub).mkdir(parents=True, exist_ok=True)
    records, unchanged = [], []
    variant_records = []
    exact_diffs = {}
    resource_paths_by_variant = {}
    protected_components = {}
    sidewalls_by_variant = {}
    preview_states = {}
    glow_states = {}
    any_edit_mask = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    underlay = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    reference_index = 4

    with zipfile.ZipFile(io.BytesIO(jar_data)) as baseline:
        for index in EDITED:
            paths = resource_paths(index)
            old_base_data = baseline.read(paths['base'])
            old_base = read_png(old_base_data)
            new_base, draft_touched, removed, added = draft.edit_sprite(index, old_base, component_doc)
            base_changes = exact_changes(old_base, new_base)
            edited_pixels = set((x, y) for x, y, _, _ in base_changes)
            assert edited_pixels <= draft_touched, index
            assert set(removed) == {p for p in geometry.opaque(old_base) - geometry.opaque(new_base)}
            assert set(added) == {p for p in geometry.opaque(new_base) - geometry.opaque(old_base)}
            active = active_module_pixels(index, component_doc)
            assert not (set((x, y) for x, y, _, _ in base_changes) & active), f'active module pixel edited: {index}'
            for x, y, _, _ in base_changes:
                any_edit_mask.putpixel((x, y), (255, 255, 255, 255))

            old_glow_data = baseline.read(paths['glow'])
            old_glow = read_png(old_glow_data)
            assert old_glow.size == (64, 1024), (index, old_glow.size)
            new_glow, glow_by_frame = make_glow(old_base, new_base, old_glow, edited_pixels, removed, added)
            assert new_glow.size == (64, 1024)
            for frame in range(FRAME_COUNT):
                old_frame = old_glow.crop((0, frame * 64, 64, (frame + 1) * 64))
                new_frame = new_glow.crop((0, frame * 64, 64, (frame + 1) * 64))
                for p in ALL_PIXELS:
                    if p not in edited_pixels:
                        assert new_frame.getpixel(p) == old_frame.getpixel(p), (index, frame, p)
                assert all(new_frame.getpixel(p)[3] == old_frame.getpixel(p)[3]
                           for p in edited_pixels if p not in removed | added)
                assert all(new_frame.getpixel(p)[3] == 0 for p in removed | added)
                assert all(new_frame.getpixel(p)[3] == 0 or new_base.getpixel(p)[3]
                           for p in ALL_PIXELS)

            old_model_data = baseline.read(paths['model'])
            old_model = json.loads(old_model_data.decode('utf-8'))
            lit = geometry.opaque(new_glow.crop((0, 0, 64, 64)))
            expected_model, _, expected_lit = model_helper.model_for_state(
                old_model, f'echo_pickaxe_v{index:03d}', new_base, lit)
            model_helper.validate_model(new_base, expected_model, expected_lit, f'echo_pickaxe_v{index:03d}')
            model, sidewall_changes = geometry.update_model_preserving_geometry(
                old_model, expected_model, removed, added, removed | added)
            model_helper.validate_model(new_base, model, expected_lit, f'echo_pickaxe_v{index:03d}')
            assert model.get('overrides', []) == old_model.get('overrides', [])
            sidewalls_by_variant[str(index)] = sidewall_changes

            new_base_data = png_bytes(new_base)
            new_glow_data = png_bytes(new_glow)
            new_model_data = geometry.json_bytes(model)
            changed_kinds = {}
            for kind, data, old_data in (('base', new_base_data, old_base_data),
                                         ('glow', new_glow_data, old_glow_data),
                                         ('model', new_model_data, old_model_data)):
                rel = paths[kind]
                if data == old_data:
                    unchanged.append({'path': rel, 'sha256': sha(old_data), 'bytes': len(old_data),
                                      'status': 'byte-identical-to-pinned-0.1.9'})
                else:
                    candidate_path(rel).write_bytes(data)
                    record = {'path': rel, 'sha256': sha(data), 'bytes': len(data),
                              'baselineSha256': sha(old_data), 'kind': kind, 'index': index}
                    records.append(record)
                    changed_kinds[kind] = record

            exact_diffs[str(index)] = {
                'baseRGBA': change_records(base_changes),
                'outlineRemoved': sorted([list(p) for p in removed], key=lambda p: (p[1], p[0])),
                'outlineAdded': sorted([list(p) for p in added], key=lambda p: (p[1], p[0])),
                'glowRGBAByFrame': {frame: change_records(changes) for frame, changes in glow_by_frame.items()},
                'model': {'northSouthGlowTexels': sorted([list(p) for p in lit], key=lambda p: (p[1], p[0])),
                          'sidewallChanges': sidewall_changes},
                'resources': changed_kinds,
            }
            levels = {'resonance': index // 32, 'frequency': (index % 32) // 8,
                      'tuning': ((index % 32) % 8) // 4, 'extension': index % 4}
            variant_records.append({'index': index, 'levels': levels,
                                    'baseSha256': sha(new_base_data), 'glowSha256': sha(new_glow_data),
                                    'modelSha256': sha(new_model_data), 'baseChangedTexels': len(base_changes),
                                    'outlineRemoved': len(removed), 'outlineAdded': len(added),
                                    'glowChangedPixels': sum(map(len, glow_by_frame.values())),
                                    'activeComponentPixelsProtected': len(active),
                                    'changedResources': sorted(changed_kinds)})
            resource_paths_by_variant[str(index)] = paths
            protected_components[str(index)] = {'levels': levels,
                'pixels': sorted([list(p) for p in active], key=lambda p: (p[1], p[0]))}
            if index in (24, 4, 32, 3, 95):
                preview_states[index] = (new_base, new_glow, model)
            if index in (24, 32, 4, 3, 95):
                glow_states[index] = (new_base, new_glow, model)
            if index == reference_index:
                for x, y in edited_pixels:
                    underlay.putpixel((x, y), new_base.getpixel((x, y)))

        mask_data, underlay_data = png_bytes(any_edit_mask), png_bytes(underlay)
        MASK_PATH.write_bytes(mask_data)
        (SRC / 'v0.1.10-frozen-underlay-index004.png').write_bytes(underlay_data)

        state_labels = [('分频III / res0 v024', 24), ('调谐I / res0 v004', 4),
                        ('仅共振I v032', 32), ('延展III / res0 v003', 3), ('全满级 v095', 95)]
        state_faces = [(label, preview.frontface(*preview_states[index], 0)) for label, index in state_labels]
        draw_delivery_board(state_faces, VAL / 'v0.1.10-candidate-five-state-white-dark.png')
        draw_actual_glow([(f'v{index:03d}', *glow_states[index]) for index in (24, 4, 32, 3, 95)],
                         VAL / 'v0.1.10-candidate-actual-glow-16frames-white-dark.png')

    map_doc = {
        'schema': 5,
        'status': 'root-visual-approved-candidate-awaiting-independent-audit',
        'version': '0.1.10-refined-hook-right-blade-full-shaft',
        'baselineJar': JAR.name, 'baselineJarSha256': JAR_SHA,
        'generator': str(DRAFT_SCRIPT.relative_to(ROOT)).replace('\\', '/'),
        'generatorSha256': sha(DRAFT_SCRIPT.read_bytes()),
        'editMask': str(MASK_PATH.relative_to(ROOT)).replace('\\', '/'),
        'editMaskMeaning': 'Union of pixels changed in at least one upgraded variant; per-variant exact changes are in perVariantExactDiff.',
        'editMaskSha256': sha(mask_data), 'editMaskPixels': sum(1 for p in ALL_PIXELS if any_edit_mask.getpixel(p)[3]),
        'underlay': str((SRC / 'v0.1.10-frozen-underlay-index004.png').relative_to(ROOT)).replace('\\', '/'),
        'underlayMeaning': 'Frozen native RGBA from v004 at all changed coordinates for a representative res0 view; exact per-index RGBA is authoritative.',
        'underlaySha256': sha(underlay_data),
        'scope': {'ordinary012': 'all four ordinary resources are excluded and remain sourced from installed 0.1.2 release',
                  'upgradedIndices': list(EDITED), 'count': len(EDITED),
                  'leftHook': 'resonance=0 only; outline/resculpt and bone facets from v0.1.10 draft; resonance-positive left hooks preserved',
                  'rightBlade': 'all upgraded indices where texels are exposed; active module map texels are untouched',
                  'shaftAndGrip': 'all upgraded indices; full shaft/haft facets, two bone bands, diagonal endcap; active module pixels protected',
                  'protected': 'all active resonance/frequency/tuning/extension component texels per variant; all ordinary resources; all non-upgrade items/data/Java/metadata'},
        'sourceMap': {'componentMap': str(COMPONENTS.relative_to(ROOT)).replace('\\', '/'),
                      'componentMapSha256': sha(COMPONENTS.read_bytes()),
                      'activeModuleProtectedPixelsByVariant': protected_components},
        'perVariantExactDiff': exact_diffs,
        'resourcePathsByVariant': resource_paths_by_variant,
        'sidewallChangesByVariant': sidewalls_by_variant,
        'modelContract': 'Native64 prism geometry/UV is generated from the approved helper. North/south light ownership follows the actual frame-0 glow mask. Surviving prism placement and unchanged sidewalls retain baseline values; alpha additions/removals update only affected elements and adjacent sidewalls.',
        'glowContract': '16 frames at 3 ticks each. Existing emissive alpha and phase are retained on surviving changed texels while RGB follows the new base facet; removed/new silhouette texels are cleared in all frames. Glow RGBA outside each variant exact edit mask is byte-pixel identical to pinned 0.1.9.',
        'resourceCounts': {'upgradedVariants': len(EDITED), 'allowedPaths': len(EDITED) * 3,
                           'changedResources': len(records), 'byteIdenticalResources': len(unchanged)},
        'previews': ['artwork/validation/v0.1.10/v0.1.10-candidate-five-state-white-dark.png',
                     'artwork/validation/v0.1.10/v0.1.10-candidate-actual-glow-16frames-white-dark.png']}
    map_bytes = json_bytes(map_doc)
    MAP_PATH.write_bytes(map_bytes)

    manifest = {'schema': 1, 'version': '0.1.10-refined-ends-candidate',
                'status': 'root-visual-approved-awaiting-independent-resource-audit',
                'baselineJar': JAR.name, 'baselineJarSha256': JAR_SHA,
                'editedIndices': list(EDITED), 'allowedResourceCount': len(EDITED) * 3,
                'changedResourceCount': len(records), 'byteIdenticalResourceCount': len(unchanged),
                'editMask': str(MASK_PATH.relative_to(ROOT)).replace('\\', '/'), 'editMaskSha256': sha(mask_data),
                'underlay': map_doc['underlay'], 'underlaySha256': sha(underlay_data),
                'map': str(MAP_PATH.relative_to(ROOT)).replace('\\', '/'), 'mapSha256': sha(map_bytes),
                'resources': records, 'unchanged': unchanged, 'variants': variant_records,
                'productionChanged': False}
    manifest_data = json_bytes(manifest)
    MANIFEST_PATH.write_bytes(manifest_data)
    (SRC / 'candidate-manifest-v0.1.10.json').write_bytes(manifest_data)
    print(f'PASS v0.1.10 candidate: upgraded={len(EDITED)}, allowed={len(EDITED)*3}, changed={len(records)}, identical={len(unchanged)}')
    print(f'mask pixels={map_doc["editMaskPixels"]}; baseline={JAR.name} ({JAR_SHA})')
    print(f'mask SHA={sha(mask_data)}; underlay SHA={sha(underlay_data)}; map SHA={sha(map_bytes)}; manifest SHA={sha(manifest_data)}')
    print(f'candidate={OUT}')


if __name__ == '__main__':
    main()
