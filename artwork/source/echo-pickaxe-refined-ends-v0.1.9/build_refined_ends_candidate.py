"""Build the frozen preview candidate from pinned 0.1.8 and 0.1.2 jars."""
import copy
import hashlib
import importlib.util
import io
import json
import zipfile
from pathlib import Path, PurePosixPath

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
SRC = Path(__file__).resolve().parent
VAL = ROOT / 'artwork/validation/v0.1.9'
OUT = VAL / 'refined-ends-candidate'
JAR = ROOT / 'jaysay-echo-tools-0.1.8.jar'
JAR_SHA = 'BF962BA4F64395EDA4227B9C1B9CB7437B800B468DFE8EED7A24FAAEEDC07778'
ORDINARY_JAR = ROOT / 'jaysay-echo-tools-0.1.2.jar'
ORDINARY_SHA = '7312AE7B54F3DAD998815B7C7BD601B65DB1BED23A21CC7AA8448E40E082F495'
PREFIX = 'assets/echopickaxe/'
ASSET = PREFIX + 'textures/item/echo_pickaxe_v{:03d}{}.png'
MODEL = PREFIX + 'models/item/echo_pickaxe_v{:03d}.json'
MODEL_HELPER = ROOT / 'artwork/source/approved-reference-oct03-64/build_approved64_variants.py'
GEOMETRY_HELPER = ROOT / 'artwork/source/echo-pickaxe-native-edge-v0.1.8/build_native_edge_candidate.py'
PREVIEW_HELPER = ROOT / 'artwork/source/echo-pickaxe-unified-head-v0.1.6/build_unified_head_candidate.py'
DRAFT_SCRIPT = SRC / 'draft_refined_ends.py'
MASK_PATH = SRC / 'refined-ends-edit-mask-v0.1.9.png'
UNDERLAY_PATH = SRC / 'refined-ends-native64-underlay-v0.1.9.png'
MAP_PATH = SRC / 'refined-ends-map-v0.1.9.json'
MANIFEST_PATH = OUT / 'candidate-manifest-v0.1.9.json'
FRAME_COUNT = 16
RES0_TIP = tuple(range(1, 32))
EXT0_END = tuple(range(4, 32, 4)) + tuple(range(32, 96, 4))
EDITED = tuple(sorted(set(RES0_TIP) | set(EXT0_END)))


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


def source_paths(index):
    return {'base': ASSET.format(index, ''),
            'glow': ASSET.format(index, '_glow'),
            'model': MODEL.format(index)}


def candidate_path(rel):
    return OUT / Path(*PurePosixPath(rel).parts)


def load_font(size):
    for path in (r'C:\Windows\Fonts\msyh.ttc', r'C:\Windows\Fonts\arial.ttf'):
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def composite(image, background):
    result = Image.new('RGBA', image.size, background + (255,))
    result.alpha_composite(image)
    return result.convert('RGB')


def make_candidate_sprite(index, baseline, draft):
    result = baseline.copy()
    removed, added = set(), set()
    tip = index in RES0_TIP
    handle = index in EXT0_END
    if tip:
        result, removed, added = draft.tip_changes(result)
    if handle:
        result = draft.handle_changes(result)
    return result, removed, added, tip, handle


def remap_glow(old_base, new_base, old_glow, removed, added, tip, handle, draft):
    result = old_glow.copy()
    edited = set()
    if tip:
        edited.update(draft.TIP_ROW_END and draft.TIP_BONE_FACETS)
        # The alpha geometry deltas and RGB facets are explicit; rows removed
        # from the sprite are separately cleared in every glow frame.
        edited.update(draft.TIP_BONE_FACETS)
    if handle:
        edited.update(draft.HANDLE_FACETS)
    edited.update(removed | added)
    for frame in range(FRAME_COUNT):
        y_offset = frame * 64
        for x, y in edited:
            old_rgba = old_base.getpixel((x, y))
            new_rgba = new_base.getpixel((x, y))
            glow_rgba = result.getpixel((x, y + y_offset))
            if not new_rgba[3]:
                result.putpixel((x, y + y_offset), (0, 0, 0, 0))
            elif not old_rgba[3]:
                # Newly opaque dark edge pixels remain unlit; no emissive area
                # is invented by the contour refinement.
                result.putpixel((x, y + y_offset), (0, 0, 0, 0))
            elif glow_rgba[3]:
                # Preserve each frame's alpha and pulse phase while carrying
                # the native base-color adjustment into the existing emission.
                rgb = tuple(max(0, min(255, glow_rgba[c] + new_rgba[c] - old_rgba[c]))
                            for c in range(3))
                result.putpixel((x, y + y_offset), (*rgb, glow_rgba[3]))
    return result, edited


def draw_delivery_board(states, path):
    scale, cell_w, label_h, gap = 3, 212, 28, 10
    sprite_size = 64 * scale
    cell_h = sprite_size + label_h + gap
    margin = 12
    columns = len(states)
    board = Image.new('RGB', (margin * 2 + columns * cell_w, margin * 2 + 2 * cell_h), (243, 245, 247))
    draw = ImageDraw.Draw(board)
    title_font, row_font = load_font(14), load_font(13)
    for row, bg in enumerate(((255, 255, 255), (23, 29, 37))):
        y = margin + row * cell_h
        draw.text((margin, y), '白底' if row == 0 else '暗底', fill=(25, 30, 36), font=row_font)
        for col, (label, image) in enumerate(states):
            x = margin + col * cell_w
            draw.text((x + 3, y), label, fill=(25, 30, 36), font=title_font)
            enlarged = image.resize((sprite_size, sprite_size), Image.Resampling.NEAREST)
            board.paste(composite(enlarged, bg), (x, y + label_h))
    board.save(path)


def draw_glow_frames(states, path):
    """All 16 actual mesh/glow front faces, in white and dark rows."""
    scale, margin, label_h = 2, 10, 25
    sprite_size = 64 * scale
    col_w, row_h = sprite_size + 6, sprite_size + label_h + 4
    board = Image.new('RGB', (margin * 2 + col_w * FRAME_COUNT,
                              margin * 2 + row_h * len(states) * 2), (244, 246, 248))
    draw = ImageDraw.Draw(board)
    font = load_font(13)
    for state_idx, (name, sprite, glow, model) in enumerate(states):
        for bg_idx, bg in enumerate(((255, 255, 255), (23, 29, 37))):
            row = state_idx * 2 + bg_idx
            y = margin + row * row_h
            draw.text((4, y + 3), f'{name} {"白" if bg_idx == 0 else "暗"}', fill=(25, 30, 36), font=font)
            for frame in range(FRAME_COUNT):
                x = margin + frame * col_w
                draw.text((x + 2, y + 3), str(frame), fill=(25, 30, 36), font=font)
                face = load_module(PREVIEW_HELPER, 'preview_helper_render_glow').frontface(sprite, glow, model, frame)
                face = face.resize((sprite_size, sprite_size), Image.Resampling.NEAREST)
                board.paste(composite(face, bg), (x, y + label_h))
    board.save(path)


def build():
    if OUT.exists() and any(OUT.iterdir()):
        raise RuntimeError(f'Refusing to overwrite existing independent candidate: {OUT}')
    baseline_data, ordinary_data = JAR.read_bytes(), ORDINARY_JAR.read_bytes()
    assert sha(baseline_data) == JAR_SHA, 'pinned 0.1.8 baseline SHA mismatch'
    assert sha(ordinary_data) == ORDINARY_SHA, 'pinned 0.1.2 ordinary SHA mismatch'
    draft = load_module(DRAFT_SCRIPT, 'refined_ends_draft_candidate')
    model_helper = load_module(MODEL_HELPER, 'approved64_refined_ends')
    geometry = load_module(GEOMETRY_HELPER, 'native64_geometry_refined_ends')
    preview = load_module(PREVIEW_HELPER, 'native64_preview_refined_ends')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / PREFIX / 'models/item').mkdir(parents=True, exist_ok=True)
    (OUT / PREFIX / 'textures/item').mkdir(parents=True, exist_ok=True)

    records, unchanged = [], []
    variant_records = []
    underlay = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    mask = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    preview_states, glow_states = {}, {}
    sidewall_records = {}
    exact_edits_by_variant = {}
    output_data = {}

    with zipfile.ZipFile(io.BytesIO(baseline_data)) as baseline, zipfile.ZipFile(io.BytesIO(ordinary_data)) as ordinary:
        representative = read_png(baseline.read(ASSET.format(31, '')))
        representative_new, tip_removed, tip_added, _, _ = make_candidate_sprite(31, representative, draft)
        tip_changed = {p for p in ((x, y) for y in range(64) for x in range(64))
                       if representative.getpixel(p) != representative_new.getpixel(p)}
        assert tip_changed
        handle_probe = read_png(baseline.read(ASSET.format(24, '')))
        handle_probe_new = draft.handle_changes(handle_probe)
        handle_changed = {p for p in ((x, y) for y in range(64) for x in range(64))
                          if handle_probe.getpixel(p) != handle_probe_new.getpixel(p)}
        union_mask = tip_changed | handle_changed
        for p in union_mask:
            mask.putpixel(p, (255, 255, 255, 255))
        for p in tip_changed:
            underlay.putpixel(p, representative_new.getpixel(p))
        for p in handle_changed:
            underlay.putpixel(p, handle_probe_new.getpixel(p))

        for index in EDITED:
            paths = source_paths(index)
            old_base_data = baseline.read(paths['base'])
            old_base = read_png(old_base_data)
            new_base, tip_removed_now, tip_added_now, tip, handle = make_candidate_sprite(index, old_base, draft)
            old_opaque = geometry.opaque(old_base)
            new_opaque = geometry.opaque(new_base)
            removed, added = old_opaque - new_opaque, new_opaque - old_opaque
            changed_base_pixels = {p for p in union_mask if old_base.getpixel(p) != new_base.getpixel(p)}
            assert changed_base_pixels, index
            if tip:
                assert tip_removed_now == tip_removed and tip_added_now == tip_added
            else:
                assert not tip_removed_now and not tip_added_now
            old_glow_data = baseline.read(paths['glow'])
            old_glow = read_png(old_glow_data)
            assert old_glow.size == (64, 1024)
            new_glow, glow_edit_coords = remap_glow(old_base, new_base, old_glow, removed, added, tip, handle, draft)
            assert new_glow.size == (64, 1024)
            # The fixed 16-frame alpha is tied to the final silhouette and no
            # glow pixel is allowed outside the exact editable RGB/outline mask.
            for frame in range(FRAME_COUNT):
                old_frame = old_glow.crop((0, frame * 64, 64, (frame + 1) * 64))
                new_frame = new_glow.crop((0, frame * 64, 64, (frame + 1) * 64))
                assert all(new_frame.getpixel(p)[3] == 0 for p in removed | added)
                assert all(new_frame.getpixel(p) == old_frame.getpixel(p)
                           for p in ((x, y) for y in range(64) for x in range(64) if p_not_in_mask((x, y), union_mask)))
                assert all((new_frame.getpixel(p)[3] == old_frame.getpixel(p)[3])
                           for p in changed_base_pixels if p not in removed | added)

            old_model_data = baseline.read(paths['model'])
            old_model = json.loads(old_model_data.decode('utf-8'))
            new_frame0 = new_glow.crop((0, 0, 64, 64))
            lit = geometry.opaque(new_frame0)
            expected_model, _, expected_lit = model_helper.model_for_state(old_model, f'echo_pickaxe_v{index:03d}', new_base, lit)
            model_helper.validate_model(new_base, expected_model, expected_lit, f'echo_pickaxe_v{index:03d}')
            model, sidewall_changes = geometry.update_model_preserving_geometry(
                old_model, expected_model, removed, added, removed | added)
            model_helper.validate_model(new_base, model, expected_lit, f'echo_pickaxe_v{index:03d}')
            assert model.get('overrides', []) == old_model.get('overrides', [])
            sidewall_records[str(index)] = sidewall_changes

            new_base_data = png_bytes(new_base)
            new_glow_data = png_bytes(new_glow)
            new_model_data = geometry.json_bytes(model)
            item_records = {}
            for kind, data, old_data in (('base', new_base_data, old_base_data),
                                         ('model', new_model_data, old_model_data),
                                         ('glow', new_glow_data, old_glow_data)):
                rel = paths[kind]
                if data == old_data:
                    unchanged.append({'path': rel, 'sha256': sha(old_data), 'bytes': len(old_data),
                                      'status': 'byte-identical-to-pinned-0.1.8'})
                else:
                    candidate_path(rel).write_bytes(data)
                    record = {'path': rel, 'sha256': sha(data), 'bytes': len(data),
                              'baselineSha256': sha(old_data), 'kind': kind, 'index': index}
                    records.append(record)
                    item_records[kind] = record
                output_data[rel] = data

            exact_edits_by_variant[str(index)] = {
                'baseChangedTexels': sorted([list(p) for p in changed_base_pixels], key=lambda q: (q[1], q[0])),
                'tipOutlineRemoved': sorted([list(p) for p in removed], key=lambda q: (q[1], q[0])),
                'tipOutlineAdded': sorted([list(p) for p in added], key=lambda q: (q[1], q[0])),
                'glowChangedTexelsByFrame': {
                    str(frame): sorted([list(p) for p in ((x, y) for y in range(64) for x in range(64))
                                        if new_glow.getpixel((p[0], p[1] + frame * 64)) != old_glow.getpixel((p[0], p[1] + frame * 64))],
                                       key=lambda q: (q[1], q[0]))
                    for frame in range(FRAME_COUNT)
                },
                'resources': item_records,
            }
            variant_records.append({'index': index, 'tipApplied': tip, 'handleEndApplied': handle,
                                    'baseSha256': sha(new_base_data), 'glowSha256': sha(new_glow_data),
                                    'modelSha256': sha(new_model_data), 'changedBaseTexels': len(changed_base_pixels),
                                    'glowPixelsChanged': sum(1 for y in range(1024) for x in range(64)
                                                             if old_glow.getpixel((x, y)) != new_glow.getpixel((x, y))),
                                    'outlineRemoved': len(removed), 'outlineAdded': len(added)})
            if index in (24, 4, 32, 3, 31, 95):
                preview_states[index] = (new_base, new_glow, model)
            if index in (24, 32):
                glow_states[index] = (new_base, new_glow, model)

        mask_data, underlay_data = png_bytes(mask), png_bytes(underlay)
        MASK_PATH.write_bytes(mask_data)
        UNDERLAY_PATH.write_bytes(underlay_data)

        ordinary_sprite = read_png(ordinary.read(PREFIX + 'textures/item/echo_pickaxe.png'))
        ordinary_glow = read_png(ordinary.read(PREFIX + 'textures/item/echo_pickaxe_glow.png'))
        ordinary_model = json.loads(ordinary.read(PREFIX + 'models/item/echo_pickaxe.json').decode('utf-8'))
        state_info = [('普通原版 0.1.2', None), ('分频III / 无共振 v024', 24),
                      ('调谐I / 无共振 v004', 4), ('仅共振I v032', 32),
                      ('延展III / 无共振 v003', 3), ('全满级 v095', 95)]
        state_images = []
        for label, index in state_info:
            if index is None:
                sprite, glow, model = ordinary_sprite, ordinary_glow, ordinary_model
            elif index not in preview_states:
                sprite = read_png(baseline.read(ASSET.format(index, '')))
                glow = read_png(baseline.read(ASSET.format(index, '_glow')))
                model = json.loads(baseline.read(MODEL.format(index)).decode('utf-8'))
            else:
                sprite, glow, model = preview_states[index]
            state_images.append((label, preview.frontface(sprite, glow, model, 0)))
        draw_delivery_board(state_images, VAL / 'v0.1.9-refined-ends-candidate-four-state-white-dark.png')
        draw_glow_frames([('分频III v024', *glow_states[24]), ('红共振I v032', *glow_states[32])],
                         VAL / 'v0.1.9-refined-ends-actual-glow-16frames-white-dark.png')

    scope_path_records = {}
    for index in EDITED:
        scope_path_records[str(index)] = source_paths(index)

    map_doc = {
        'schema': 4,
        'status': 'root-approved-refined-ends-draft-candidate-pending-independent-scope-audit',
        'version': '0.1.9-refined-hook-and-ext0-ferrule',
        'baselineJar': JAR.name, 'baselineJarSha256': JAR_SHA,
        'ordinary012Jar': ORDINARY_JAR.name, 'ordinary012JarSha256': ORDINARY_SHA,
        'editMask': str(MASK_PATH.relative_to(ROOT)).replace('\\', '/'),
        'editMaskSha256': sha(MASK_PATH.read_bytes()), 'editMaskPixels': sum(1 for y in range(64) for x in range(64) if mask.getpixel((x, y))[3]),
        'underlay': str(UNDERLAY_PATH.relative_to(ROOT)).replace('\\', '/'),
        'underlaySha256': sha(UNDERLAY_PATH.read_bytes()),
        'design': {'hookScope': 'indices 001..031 only; narrowed curve rows and two connected terminal texels, small bone facet, 64x64 native pixels.',
                   'handleScope': 'extension=0 only, indices 004..028 by 4 and 032..092 by 4; refined gray-blue ferrule planes, interrupted narrow cyan seam, faceted bone inset, terminal taper.',
                   'protected': 'ordinary 0.1.2 quartet; indices 032..095 hook appearance; all extension I/II/III eye, pupil, ring and overlay pixels; other body, modules, items, metadata, Java/data.',
                   'tipRowsFinalRightEdge': {str(k): v for k, v in draft.TIP_ROW_END.items()},
                   'tipAlphaRemoved': sorted([list(p) for p in tip_removed], key=lambda q: (q[1], q[0])),
                   'tipAlphaAdded': sorted([list(p) for p in tip_added], key=lambda q: (q[1], q[0])),
                   'tipBoneFacets': [{'pixel': list(p), 'rgba': [*rgb, 255]} for p, rgb in sorted(draft.TIP_BONE_FACETS.items())],
                   'handleAlphaRemoved': sorted([list(p) for p in draft.HANDLE_REMOVE]),
                   'handleAlphaAdded': sorted([list(p) for p in draft.HANDLE_ADD]),
                   'handleFacets': [{'pixel': list(p), 'rgba': [*rgb, 255]} for p, rgb in sorted(draft.HANDLE_FACETS.items())]},
        'perVariantExactDiff': exact_edits_by_variant,
        'resourcePathsByVariant': scope_path_records,
        'modelContract': 'Prism geometry and UV are generated by the approved native64 helper; surviving north/south and unchanged sidewalls remain preserved. Local alpha additions/removals update element and neighbor sidewalls only.',
        'glowContract': '16 frames x 3 ticks. Existing emissive alpha and pulse phase remain fixed on surviving pixels; frame RGB carries the native base-color delta. Removed-alpha pixels are cleared in every frame; added dark contour pixels do not create new glow. All texels outside the variant-specific base edit mask remain pixel-exact to 0.1.8.',
        'sidewallChangesByIndex': sidewall_records,
        'resourceCounts': {'allowedVariantIndices': len(EDITED), 'allowedPaths': len(EDITED) * 3,
                           'changedResources': len(records), 'byteIdenticalBaselineResources': len(unchanged)},
        'previews': ['artwork/validation/v0.1.9/refined-ends-candidate-four-state-white-dark.png',
                     'artwork/validation/v0.1.9/refined-ends-actual-glow-16frames-white-dark.png'],
    }
    MAP_PATH.write_bytes(json_bytes(map_doc))
    manifest = {'schema': 2, 'version': '0.1.9-refined-ends-candidate',
                'status': 'root-approved-draft-frozen-awaiting-independent-scope-audit',
                'baselineJar': JAR.name, 'baselineJarSha256': JAR_SHA,
                'ordinary012Jar': ORDINARY_JAR.name, 'ordinary012JarSha256': ORDINARY_SHA,
                'editedIndices': list(EDITED), 'allowedResourceCount': len(EDITED) * 3,
                'changedResourceCount': len(records), 'byteIdenticalResourceCount': len(unchanged),
                'editMask': str(MASK_PATH.relative_to(ROOT)).replace('\\', '/'),
                'editMaskSha256': sha(MASK_PATH.read_bytes()),
                'underlay': str(UNDERLAY_PATH.relative_to(ROOT)).replace('\\', '/'),
                'underlaySha256': sha(UNDERLAY_PATH.read_bytes()),
                'map': str(MAP_PATH.relative_to(ROOT)).replace('\\', '/'),
                'mapSha256': sha(MAP_PATH.read_bytes()),
                'resources': records, 'unchanged': unchanged, 'variants': variant_records,
                'productionChanged': False}
    manifest_data = json_bytes(manifest)
    MANIFEST_PATH.write_bytes(manifest_data)
    (SRC / 'refined-ends-manifest-v0.1.9.json').write_bytes(manifest_data)
    print(f'PASS refined-ends candidate: variants={len(EDITED)}, paths={len(EDITED)*3}, changed={len(records)}, identical={len(unchanged)}')
    print(f'edit mask={map_doc["editMaskPixels"]}; source={JAR.name} ({JAR_SHA})')
    print(f'mask SHA {manifest["editMaskSha256"]}; underlay SHA {manifest["underlaySha256"]}; map SHA {manifest["mapSha256"]}; manifest SHA {sha(manifest_data)}')


def p_not_in_mask(point, mask_set):
    return point not in mask_set


if __name__ == '__main__':
    build()
