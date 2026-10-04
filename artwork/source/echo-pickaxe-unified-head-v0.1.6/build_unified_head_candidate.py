"""Freeze and build the isolated v0.1.6 res0 unified-head candidate.

Writes only artwork/source and artwork/validation. It never deploys to src.
"""
import copy
import hashlib
import importlib.util
import io
import json
import math
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
SRC = Path(__file__).resolve().parent
VAL = ROOT / 'artwork/validation/v0.1.6'
OUT = VAL / 'candidate'
PREFIX = 'assets/echopickaxe/'
ORDINARY_JAR = ROOT / 'jaysay-echo-tools-0.1.2.jar'
ORDINARY_SHA = '7312AE7B54F3DAD998815B7C7BD601B65DB1BED23A21CC7AA8448E40E082F495'
BASELINE_JAR = ROOT / 'jaysay-echo-tools-0.1.5.jar'
BASELINE_SHA = 'CDDEE165380BA810B4C874F0E34C85645B85D8BEBE4D2EF72E1C00EF58DA8706'
DRAFT_SCRIPT = SRC / 'draw_unified_head_draft.py'
COMMON = ROOT / 'artwork/source/approved-reference-oct03-64/common64-unupgraded.png'
COMMON_GLOW = ROOT / 'artwork/source/approved-reference-oct03-64/common64-glow.png'
COMPONENT_MAP = ROOT / 'artwork/source/approved-reference-oct03-64/native64-component-map.json'
MODEL_HELPERS = ROOT / 'artwork/source/approved-reference-oct03-64/build_approved64_variants.py'
UNDERLAY_PATH = SRC / 'native64-unified-head-underlay-v0.1.6.png'
MASK_PATH = SRC / 'unified-head-edit-mask-v0.1.6.png'
MAP_PATH = SRC / 'unified-head-map-v0.1.6.json'
EDITED_INDICES = [i for i in range(1, 32)]
FRAMES = 16
NO_GLOW = {
    (30, 8), (29, 9), (27, 10), (26, 11),
    (12, 18), (13, 19), (14, 20), (17, 18),
    (16, 18), (19, 16), (14, 20),
}
EXPLICIT_FISSURE_GLOW = {(18, 17)}


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


def font(size=16):
    for path in ('C:/Windows/Fonts/msyh.ttc', 'C:/Windows/Fonts/simhei.ttf',
                 'C:/Windows/Fonts/arial.ttf'):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def composite(sprite, background):
    image = Image.new('RGBA', sprite.size, background + (255,))
    image.alpha_composite(sprite)
    return image.convert('RGB')


def save_delivery_board(states, path):
    scale = 4
    labels = [state[0] for state in states]
    sprite_px, label_h, margin = 64 * scale, 30, 12
    cell_w = sprite_px + 36
    cell_h = label_h + sprite_px + 12
    board = Image.new('RGB', (2 * margin + cell_w * 4, 2 * margin + cell_h * 2), (245, 246, 248))
    draw = ImageDraw.Draw(board)
    label_font, bg_font = font(14), font(13)
    for row, background in enumerate(((255, 255, 255), (22, 28, 36))):
        y = margin + row * cell_h
        # Caption/header strips retain the board's pale background in both rows.
        ink = (25, 30, 38)
        draw.text((margin, y), '白底' if row == 0 else '暗底', fill=ink, font=bg_font)
        for col, (label, sprite) in enumerate(states):
            x = margin + col * cell_w
            draw.text((x + 32, y), label, fill=ink, font=label_font)
            enlarged = sprite.resize((sprite_px, sprite_px), Image.Resampling.NEAREST)
            board.paste(composite(enlarged, background), (x + 18, y + label_h))
    board.save(path)


def save_glow_board(states, path):
    frame_ids = (0, 4, 8, 12)
    width, row_h, margin = 920, 170, 10
    board = Image.new('RGB', (width, margin * 2 + row_h * len(states) * 2), (245, 246, 248))
    draw = ImageDraw.Draw(board)
    title_font, label_font = font(14), font(12)
    for state_idx, (name, sprite, glow, model) in enumerate(states):
        for bg_idx, background in enumerate(((255, 255, 255), (22, 28, 36))):
            row = state_idx * 2 + bg_idx
            y = margin + row * row_h
            # Captions sit on the pale page background; only sprites use dark BG.
            ink = (25, 30, 38)
            draw.text((8, y), f'{name}｜' + ('白底' if bg_idx == 0 else '暗底'), fill=ink, font=title_font)
            for col, frame in enumerate(frame_ids):
                x = 72 + col * 210
                draw.text((x, y + 18), f'帧 {frame}', fill=ink, font=label_font)
                face = frontface(sprite, glow, model, frame)
                face = face.resize((128, 128), Image.Resampling.NEAREST)
                board.paste(composite(face, background), (x, y + 36))
    board.save(path)


def main():
    ordinary_bytes = ORDINARY_JAR.read_bytes()
    baseline_bytes = BASELINE_JAR.read_bytes()
    assert sha(ordinary_bytes) == ORDINARY_SHA, '0.1.2 ordinary baseline SHA mismatch'
    assert sha(baseline_bytes) == BASELINE_SHA, '0.1.5 baseline SHA mismatch'
    if OUT.exists() and any(OUT.iterdir()):
        manifest_path = OUT / 'candidate-manifest-v0.1.6.json'
        if not manifest_path.is_file():
            raise RuntimeError(f'Refusing to overwrite unrecognized candidate directory: {OUT}')
        previous = json.loads(manifest_path.read_text(encoding='utf-8'))
        if previous.get('baselineJarSha256') != BASELINE_SHA:
            raise RuntimeError('Existing candidate uses another baseline')

    draft_module = load_module(DRAFT_SCRIPT, 'unified_head_draft_v016')
    helper = load_module(MODEL_HELPERS, 'approved64_model_helpers_v016')
    with zipfile.ZipFile(io.BytesIO(ordinary_bytes)) as ordinary_zip, zipfile.ZipFile(io.BytesIO(baseline_bytes)) as base_zip:
        old_ordinary = read_png(ordinary_zip.read(PREFIX + 'textures/item/echo_pickaxe.png'))
        baseline_v031_bytes = base_zip.read(PREFIX + 'textures/item/echo_pickaxe_v031.png')
        old_v031 = read_png(baseline_v031_bytes)
        common = Image.open(COMMON).convert('RGBA')
        ordinary_alpha = old_ordinary.getchannel('A').resize((64, 64), Image.Resampling.NEAREST)
        component = json.loads(COMPONENT_MAP.read_text(encoding='utf-8'))['components']
        modules = {(x, y) for name in ('frequency', 'tuning', 'extension')
                   for tier in component[name]['tiers'] for x, y, *_ in tier['texels']}
        draft, material_mask, hook_only, mapping = draft_module.make_draft(
            old_v031, common, ordinary_alpha, modules)

        # Store only native underlay pixels in the approved editable region.
        # All other texels, including modules, stay transparent in this source.
        underlay = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        mask_image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        for x, y in material_mask:
            underlay.putpixel((x, y), draft.getpixel((x, y)))
            mask_image.putpixel((x, y), (255, 255, 255, 255))
        underlay_data, mask_data = png_bytes(underlay), png_bytes(mask_image)
        UNDERLAY_PATH.write_bytes(underlay_data)
        MASK_PATH.write_bytes(mask_data)

        common_glow = read_png(COMMON_GLOW.read_bytes())
        assert common_glow.size == (64, 1024)
        source_for = {p: (p if common.getpixel(p)[3] else mapping[p]) for p in material_mask}
        native_frames = []
        emit = set()
        for frame_id in range(FRAMES):
            src_frame = common_glow.crop((0, frame_id * 64, 64, (frame_id + 1) * 64))
            frame_image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
            for point, source_point in source_for.items():
                if point in NO_GLOW:
                    continue
                value = src_frame.getpixel(source_point)
                if value[3]:
                    frame_image.putpixel(point, value)
                    emit.add(point)
            factor = .82 + .18 * (.5 + .5 * math.sin(math.tau * frame_id / FRAMES))
            for x, y in EXPLICIT_FISSURE_GLOW:
                r, g, b, a = draft.getpixel((x, y))
                if a:
                    frame_image.putpixel((x, y), (round(r * factor), round(g * factor), round(b * factor), 255))
                    emit.add((x, y))
            native_frames.append(frame_image)
        assert all(image_pixels(frame) == emit for frame in native_frames), 'new glow alpha must remain fixed across 16 frames'

        candidate_records, variant_records = [], []
        previews = {}
        model_root = OUT / PREFIX / 'models/item'
        texture_root = OUT / PREFIX / 'textures/item'
        model_root.mkdir(parents=True, exist_ok=True)
        texture_root.mkdir(parents=True, exist_ok=True)
        for index in EDITED_INDICES:
            item = f'echo_pickaxe_v{index:03d}'
            baseline_sprite_bytes = base_zip.read(PREFIX + f'textures/item/{item}.png')
            baseline_sprite = read_png(baseline_sprite_bytes)
            sprite = baseline_sprite.copy()
            for x, y in material_mask:
                sprite.putpixel((x, y), underlay.getpixel((x, y)))
            assert all(sprite.getpixel((x, y)) == baseline_sprite.getpixel((x, y))
                       for y in range(64) for x in range(64) if (x, y) not in material_mask), item
            assert all(sprite.getpixel(p)[3] == baseline_sprite.getpixel(p)[3] for p in material_mask), item

            baseline_glow = read_png(base_zip.read(PREFIX + f'textures/item/{item}_glow.png'))
            assert baseline_glow.size == (64, 1024), (item, baseline_glow.size)
            glow = baseline_glow.copy()
            for f, frame_image in enumerate(native_frames):
                frame = glow.crop((0, 64 * f, 64, 64 * (f + 1)))
                for x, y in material_mask:
                    frame.putpixel((x, y), frame_image.getpixel((x, y)))
                glow.paste(frame, (0, 64 * f))
                original_frame = baseline_glow.crop((0, 64 * f, 64, 64 * (f + 1)))
                assert all(frame.getpixel((x, y)) == original_frame.getpixel((x, y))
                           for y in range(64) for x in range(64) if (x, y) not in material_mask), item

            lit = image_pixels(glow.crop((0, 0, 64, 64)))
            old_model = json.loads(base_zip.read(PREFIX + f'models/item/{item}.json').decode('utf-8'))
            model, opaque, model_lit = helper.model_for_state(old_model, item, sprite, lit)
            if 'overrides' in old_model:
                model['overrides'] = copy.deepcopy(old_model['overrides'])
            helper.validate_model(sprite, model, model_lit, item)

            resources = {
                PREFIX + f'models/item/{item}.json': json_bytes(model),
                PREFIX + f'textures/item/{item}.png': png_bytes(sprite),
                PREFIX + f'textures/item/{item}_glow.png': png_bytes(glow),
            }
            hashes = {}
            for rel, data in resources.items():
                target = OUT / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                record = {'path': rel, 'sha256': sha(data), 'bytes': len(data)}
                candidate_records.append(record)
                hashes[rel.rsplit('/', 1)[-1]] = sha(data)
            variant_records.append({'index': index, 'levels': helper.levels_for(index),
                                    'opaqueTexels': len(opaque), 'emissiveTexels': len(model_lit),
                                    'sha256': hashes})
            if index in (24, 31):
                previews[index] = (sprite, glow, model)

        # Build comparison imagery from actual front-face #glow composition.
        ordinary_model = json.loads(ordinary_zip.read(PREFIX + 'models/item/echo_pickaxe.json').decode('utf-8'))
        ordinary_glow = read_png(ordinary_zip.read(PREFIX + 'textures/item/echo_pickaxe_glow.png'))
        ordinary_face = frontface(old_ordinary, ordinary_glow, ordinary_model, 0)
        # The unmodified ordinary item is intentionally shown from its exact 0.1.2 base texture.
        baseline_095_sprite = read_png(base_zip.read(PREFIX + 'textures/item/echo_pickaxe_v095.png'))
        baseline_095_glow = read_png(base_zip.read(PREFIX + 'textures/item/echo_pickaxe_v095_glow.png'))
        baseline_095_model = json.loads(base_zip.read(PREFIX + 'models/item/echo_pickaxe_v095.json').decode('utf-8'))
        board_states = [
            ('普通原版', ordinary_face),
            ('分频 III', frontface(*previews[24], 0)),
            ('无共振满级', frontface(*previews[31], 0)),
            ('共振 II 满级', frontface(baseline_095_sprite, baseline_095_glow, baseline_095_model, 0)),
        ]
        save_delivery_board(board_states, VAL / 'v0.1.6-delivery-four-state-white-dark.png')
        # Four-frame front-face animation view of the two res0 candidates.
        save_glow_board([('分频 III（v024）', *previews[24]), ('无共振满级（v031）', *previews[31])],
                        VAL / 'v0.1.6-native-glow-frontface-white-dark-4frames.png')

    # Freeze mapping and RGB source contract with explicit hashes and full texels.
    mask_points = sorted(material_mask, key=lambda p: (p[1], p[0]))
    map_doc = {
        'schema': 1,
        'status': 'root-approved-frozen-candidate-pending-independent-audit',
        'version': '0.1.6-unified-head-native64',
        'baselineJar': BASELINE_JAR.name,
        'baselineJarSha256': BASELINE_SHA,
        'ordinaryShapeJar': ORDINARY_JAR.name,
        'ordinaryShapeJarSha256': ORDINARY_SHA,
        'underlay': UNDERLAY_PATH.name,
        'underlaySha256': sha(underlay_data),
        'editMask': MASK_PATH.name,
        'editMaskSha256': sha(mask_data),
        'editMaskPixels': len(material_mask),
        'frozenNativeRGBA': [[x, y, list(underlay.getpixel((x, y)))] for x, y in mask_points],
        'outlineContract': 'Every res0 candidate alpha pixel is exactly the corresponding pinned 0.1.5 res0 baseline pixel; only RGB may change inside the edit mask.',
        'underlaySourceContract': 'The underlay is a mask-only 64x64 RGBA source. Texels outside the edit mask, including all upgrade-module texels, are transparent and are never copied into candidate textures.',
        'materialSourceContract': 'Native color and cut-face structure derive from approved common64-unupgraded.png. Common opaque texels are restored at native scale; legacy-hook-only opaque texels use the recorded curved adjacent-head source mapping. The ordinary 0.1.2 PNG is read only for alpha silhouette construction; its RGB/luminance/material classes are not read.',
        'commonMaterialSha256': sha(COMMON.read_bytes()),
        'commonGlowSha256': sha(COMMON_GLOW.read_bytes()),
        'excludedModuleComponents': ['frequency', 'tuning', 'extension'],
        'excludedModuleTexels': len(modules),
        'activeModuleOverlapWithEditMask': 0,
        'materialMaskBoundsInclusive': [min(x for x, y in material_mask), min(y for x, y in material_mask),
                                        max(x for x, y in material_mask), max(y for x, y in material_mask)],
        'hookOnlyTexels': len(hook_only),
        'hookOnlySourceMapping': [[x, y, *mapping[(x, y)]] for x, y in sorted(hook_only, key=lambda p: (p[1], p[0]))],
        'glowContract': 'Inside mask, copy only the approved common64 sparse fissure glow at native coordinates (or recorded source-mapped hook coordinate), with the common 16-frame phase and RGB. Dark facet cuts are explicitly unlit; one short cyan fissure pixel is pulse-lit using the same restrained phase. Alpha is fixed across all 16 frames. Outside mask, every index and frame remains pixel-identical to its pinned 0.1.5 glow strip. Existing per-item mcmeta remains byte-identical and specifies the established 3-tick cadence.',
        'darkFacetTexelsForcedUnlit': [list(p) for p in sorted(NO_GLOW, key=lambda p: (p[1], p[0]))],
        'explicitFissureGlowTexels': [list(p) for p in sorted(EXPLICIT_FISSURE_GLOW)],
        'glowFrames': FRAMES,
        'glowTicksPerFrame': 3,
        'glowEmitPixelsInMask': len(emit),
        'candidateResourceCount': len(candidate_records),
        'changedVariantResources': 93,
        'ordinaryResourcesIncluded': False,
        'resonancePositiveResourcesIncluded': False,
        'previews': ['artwork/validation/v0.1.6/v0.1.6-delivery-four-state-white-dark.png',
                     'artwork/validation/v0.1.6/v0.1.6-native-glow-frontface-white-dark-4frames.png'],
        'candidateResources': candidate_records,
    }
    MAP_PATH.write_bytes(json_bytes(map_doc))
    candidate_manifest = {
        'schema': 1,
        'version': '0.1.6-unified-head-native64-candidate',
        'status': 'root-approved-candidate-pending-independent-audit',
        'baselineJar': BASELINE_JAR.name,
        'baselineJarSha256': BASELINE_SHA,
        'changedVariantResources': 93,
        'candidateResourceCount': len(candidate_records),
        'variants': variant_records,
        'editMask': str(MASK_PATH.relative_to(ROOT)).replace('\\', '/'),
        'editMaskSha256': sha(mask_data),
        'underlay': str(UNDERLAY_PATH.relative_to(ROOT)).replace('\\', '/'),
        'underlaySha256': sha(underlay_data),
        'frozenMap': str(MAP_PATH.relative_to(ROOT)).replace('\\', '/'),
        'frozenMapSha256': sha(MAP_PATH.read_bytes()),
        'resources': candidate_records,
        'ordinaryBaseResources': 'left to release restoration from exact 0.1.2 jar; no candidate base quartet written',
        'resonancePositiveResources': 'all 64 variants remain byte-identical to 0.1.5 baseline',
    }
    candidate_manifest_bytes = json_bytes(candidate_manifest)
    (OUT / 'candidate-manifest-v0.1.6.json').write_bytes(candidate_manifest_bytes)
    (VAL / 'candidate-manifest-v0.1.6.json').write_bytes(candidate_manifest_bytes)
    print(f'PASS isolated 0.1.6 candidate: {len(candidate_records)} resources; {len(variant_records)} res0 variants; mask={len(material_mask)}; emit={len(emit)}')
    print(f'Candidate: {OUT}')
    print(f'Edit mask: {MASK_PATH} sha256={sha(mask_data)}')
    print(f'Underlay: {UNDERLAY_PATH} sha256={sha(underlay_data)}')
    print(f'Frozen map: {MAP_PATH} sha256={sha(MAP_PATH.read_bytes())}')


if __name__ == '__main__':
    main()
