from __future__ import annotations

from pathlib import Path
from PIL import Image
import hashlib
import json
import math
import zipfile

ROOT = Path(__file__).resolve().parents[3]
ART = ROOT / 'artwork/source/approved-fullmax-v0.1.12'
TIERS = ART / 'tiers'
ANCHOR = ART / 'candidates/approved-fullmax-128.png'
PROOF = ROOT / 'artwork/validation/approved-fullmax-v0.1.12/tier-manifest.json'
VAL = ROOT / 'artwork/validation/v0.1.12/approved-fullmax'
OUT = VAL / 'candidate'
BASELINE = ROOT / 'jaysay-echo-tools-0.1.11.jar'
SRC = ROOT / 'src/main/resources/assets/echopickaxe'
ANCHOR_SHA256 = 'BE0F000D3B70B35E10984951A6B1E6DA66CD204381A22E3C8FB9399C23019B67'
BASELINE_SHA256 = '3480E7F761201D62F7FFBF7417BFF57DBA1EE02B8A4225C43622285266CD6234'

# Source proof names describe art parts; candidate manifest names match Java/JSON regions.
MODULE_MAP = {
    'resonance': ('redResonance', 'resonance'),
    'split': ('purpleFrequency', 'frequency'),
    'tuning': ('tuningStar', 'tuning'),
    'extension': ('greenExtension', 'extension'),
}
TIER_NAMES = {
    'resonance': {1: 'resonance1', 2: 'resonance2'},
    'split': {1: 'split1', 2: 'split2', 3: 'split3'},
    'tuning': {1: 'tuning1'},
    'extension': {1: 'extension1', 2: 'extension2', 3: 'extension3'},
}
GLOW_PHASE = {
    'cyanVeins': 0.0,
    'redResonance': math.pi / 2,
    'purpleFrequency': math.pi,
    'tuningStar': 3 * math.pi / 2,
    'greenExtension': 5 * math.pi / 2,
}
STATE_GLOW_KEYS = {
    'resonance': {1: 'resonance1', 2: 'resonance2'},
    'split': {1: 'split1', 2: 'split2', 3: 'split3'},
    'tuning': {1: 'tuning1'},
    'extension': {1: 'extension1', 2: 'extension2', 3: 'extension3'},
}

sha = lambda data: hashlib.sha256(data).hexdigest().upper()

def levels(index: int) -> dict[str, int]:
    return {'resonance': index // 32, 'frequency': (index % 32) // 8,
            'tuning': (index % 8) // 4, 'extension': index % 4}

def resource(path: str) -> str:
    return 'assets/echopickaxe/' + path

def points(coords, label: str) -> set[tuple[int, int]]:
    if not isinstance(coords, list):
        raise ValueError(f'{label}: expected a coordinate list in reviewed proof')
    result = set()
    for pair in coords:
        if not isinstance(pair, list) or len(pair) != 2:
            raise ValueError(f'{label}: malformed coordinate {pair!r}')
        x, y = map(int, pair)
        if not (0 <= x < 128 and 0 <= y < 128):
            raise ValueError(f'{label}: coordinate outside 128x128 texture: {(x, y)}')
        if (x, y) in result:
            raise ValueError(f'{label}: duplicate coordinate {(x, y)}')
        result.add((x, y))
    return result

def rgba_image(path: Path, size: tuple[int, int]) -> Image.Image:
    image = Image.open(path).convert('RGBA')
    if image.size != size:
        raise ValueError(f'{path}: expected {size}, got {image.size}')
    return image

def pixel_diff(base: Image.Image, layer: Image.Image) -> set[tuple[int, int]]:
    bp, lp = base.load(), layer.load()
    return {(x, y) for y in range(base.height) for x in range(base.width) if bp[x, y] != lp[x, y]}

def load_static_state(proof: dict, name: str) -> Image.Image:
    entry = proof.get('states', {}).get(name)
    if not isinstance(entry, dict) or not entry.get('path') or not entry.get('sha256'):
        raise RuntimeError(f'static proof is missing a path/hash for state {name}')
    path = (ROOT / entry['path']).resolve()
    if not path.is_file() or sha(path.read_bytes()) != entry['sha256'].upper():
        raise RuntimeError(f'{name}: static state path/hash does not match the frozen proof')
    return rgba_image(path, (128, 128))

def mask_coordinates(mapping: dict, module: str, tier_name: str) -> list:
    # Frozen source proof stores tier-first masks: masks[tier][module] = [[x,y], ...].
    tier = mapping.get(tier_name)
    value = tier.get(module) if isinstance(tier, dict) else None
    if value is None:
        raise RuntimeError(f'{tier_name}: missing explicit glow mask for {module}')
    return value

def level_state(index: int) -> dict[str, int]:
    return levels(index)

def selected_tiers(index: int) -> dict[str, tuple[str, int]]:
    value = level_state(index)
    return {name: (TIER_NAMES[name][value[lv]], value[lv])
            for name, (_, lv) in MODULE_MAP.items() if value[lv] > 0}

def png_bytes(image: Image.Image) -> bytes:
    import io
    output = io.BytesIO()
    image.save(output, format='PNG', optimize=False)
    return output.getvalue()

def metadata_bytes() -> bytes:
    data = {'animation': {'width': 128, 'height': 128, 'frametime': 3,
                          'interpolate': True, 'frames': [{'index': i} for i in range(16)]}}
    return (json.dumps(data, indent=2) + '\n').encode()

def make_model(old_bytes: bytes, alpha: set[tuple[int, int]], lit: set[tuple[int, int]]) -> bytes:
    model = json.loads(old_bytes.decode('utf-8'))
    elements = []
    cell = 16 / 128
    for x, y in sorted(alpha, key=lambda point: (point[1], point[0])):
        uv = [(x + .5) * cell, (y + .5) * cell, (x + .5) * cell, (y + .5) * cell]
        faces = {}
        for face in ('north', 'south'):
            value = {'uv': uv, 'texture': '#glow' if (x, y) in lit else '#layer0'}
            if (x, y) in lit:
                value['forge_data'] = {'block_light': 15, 'sky_light': 15, 'ambient_occlusion': False}
            faces[face] = value
        adjacent = {'west': (x-1, y), 'east': (x+1, y), 'up': (x, y-1), 'down': (x, y+1)}
        for face, neighbour in adjacent.items():
            if neighbour not in alpha:
                faces[face] = {'uv': uv, 'texture': '#layer0'}
        elements.append({'from': [x*cell, 16-(y+1)*cell, 7.5],
                         'to': [(x+1)*cell, 16-y*cell, 8.5],
                         'shade': False, 'faces': faces})
    model['elements'] = elements
    return (json.dumps(model, ensure_ascii=False, indent=2) + '\n').encode()

def main() -> None:
    if sha(BASELINE.read_bytes()) != BASELINE_SHA256:
        raise RuntimeError('pinned 0.1.11 baseline JAR SHA mismatch')
    if sha(ANCHOR.read_bytes()) != ANCHOR_SHA256:
        raise RuntimeError('user-approved 128px master SHA mismatch')
    ordinary_base = SRC / 'textures/item/echo_pickaxe.png'
    if sha(ordinary_base.read_bytes()) != '296326965171A658F9CD40E0C9C42FB3ABF5B1094AF9EFB0005096061C1711F5':
        raise RuntimeError('ordinary 64px anchor changed')
    if not PROOF.is_file():
        raise RuntimeError(f'static proof is not frozen yet: {PROOF}')
    if OUT.exists() and any(OUT.iterdir()):
        raise RuntimeError(f'candidate directory is not empty; refusing overwrite: {OUT}')
    proof_bytes = PROOF.read_bytes()
    if sha(proof_bytes) != '7C65AE5F361D2409F458827F74201D66860AA432BB844FCD27DBBA7754023A4B':
        raise RuntimeError('frozen source tier proof SHA mismatch')
    proof = json.loads(proof_bytes.decode('utf-8-sig'))

    neutral = load_static_state(proof, 'enhanced-neutral128')
    fullmax = load_static_state(proof, 'all_max')
    approved = rgba_image(ANCHOR, (128, 128))
    if fullmax.tobytes() != approved.tobytes():
        raise RuntimeError('static all_max is not pixel-exact with the user-approved 128px master')

    source_edit_masks = proof.get('moduleEditMasks')
    source_glow_masks = proof.get('moduleGlowMasks')
    source_stable_masks = proof.get('moduleGlowStableMasks')
    if set(source_edit_masks or {}) != set(MODULE_MAP):
        raise RuntimeError('frozen proof must define moduleEditMasks for resonance/split/tuning/extension')
    expected_glow_tiers = {name for tiers in TIER_NAMES.values() for name in tiers.values()}
    if set(source_glow_masks or {}) != expected_glow_tiers or set(source_stable_masks or {}) != expected_glow_tiers:
        raise RuntimeError('frozen proof must define animated and stable glow masks for every source tier')
    expected_source_modules = set(MODULE_MAP)
    tier_module = {tier_name: module for module, tiers in TIER_NAMES.items() for tier_name in tiers.values()}
    for tier_name in expected_glow_tiers:
        expected = {tier_module[tier_name]}
        if set(source_glow_masks[tier_name]) != expected or set(source_stable_masks[tier_name]) != expected:
            raise RuntimeError(f'{tier_name}: glow-mask map must list only its active source module')
    edit_masks = {module: points(source_edit_masks[module].get('coordinates'), f'{module} moduleEditMasks')
                  for module in MODULE_MAP}
    candidate_edit_masks = {candidate: sorted([list(p) for p in edit_masks[source]], key=lambda p:(p[1],p[0]))
                            for source, (candidate, _) in MODULE_MAP.items()}
    tier_images = {}
    tier_diffs = {}
    for module, tiers in TIER_NAMES.items():
        for level, name in tiers.items():
            image = load_static_state(proof, name)
            changed = pixel_diff(neutral, image)
            if not changed <= edit_masks[module]:
                raise RuntimeError(f'{name}: static tier changes outside its frozen moduleEditMask')
            tier_images[name] = image
            tier_diffs[name] = changed

    expected_mapping = {
        'resonance': [0, 1, 2], 'split': [0, 1, 2, 3],
        'tuning': [0, 1], 'extension': [0, 1, 2, 3],
        'candidateIndexFormula': 'resonance*32 + split*8 + tuning*4 + extension',
    }
    if proof.get('levelsMapping') != expected_mapping:
        raise RuntimeError('static proof must pin the existing 0..95 levels mapping exactly')
    anchor_glow = Image.open(SRC / 'textures/item/echo_pickaxe_glow.png').convert('RGBA')
    if anchor_glow.size != (64, 1024):
        raise RuntimeError('ordinary glow strip must remain the deployed 64x1024 resource')
    ordinary_glow_alpha = {(x, y) for y in range(64) for x in range(64) if anchor_glow.getpixel((x, y))[3] > 0}
    if not ordinary_glow_alpha:
        raise RuntimeError('ordinary glow alpha is empty')
    # The enhanced 128px source has its own cyan-vein locations; never reuse ordinary 64px coordinates.
    neutral_pixels = neutral.load()
    cyan_source = {(x, y) for y in range(128) for x in range(128)
                   if (lambda rgb: rgb[3] == 255 and rgb[0] <= 70 and rgb[1] >= 140
                       and rgb[2] >= 140 and rgb[1] >= rgb[0]*1.8 and rgb[2] >= rgb[0]*1.8)(neutral_pixels[x,y])}
    global_module_edit = set().union(*edit_masks.values())
    cyan_source -= global_module_edit
    if not cyan_source:
        raise RuntimeError('neutral128 contains no cyan texels after excluding edited module regions')

    OUT.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(BASELINE) as old:
        old_bases, old_glows, old_models, old_metas = {}, {}, {}, {}
        for index in range(96):
            stem = 'echo_pickaxe' if index == 0 else f'echo_pickaxe_v{index:03d}'
            prefix = 'assets/echopickaxe/'
            old_bases[index] = old.read(prefix + f'textures/item/{stem}.png')
            old_glows[index] = old.read(prefix + f'textures/item/{stem}_glow.png')
            old_models[index] = old.read(prefix + f'models/item/{stem}.json')
            old_metas[index] = old.read(prefix + f'textures/item/{stem}_glow.png.mcmeta')

        meta128 = metadata_bytes()
        rows, variants = [], {}
        def add(index: int, kind: str, path: str, data: bytes, baseline: bytes) -> None:
            target = OUT / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            rows.append({'index': index, 'kind': kind, 'path': path, 'sha256': sha(data),
                         'baselineSha256': sha(baseline), 'changed': data != baseline, 'bytes': len(data)})

        for index in range(96):
            stem = 'echo_pickaxe' if index == 0 else f'echo_pickaxe_v{index:03d}'
            paths = {
                'base': resource(f'textures/item/{stem}.png'),
                'glow': resource(f'textures/item/{stem}_glow.png'),
                'model': resource(f'models/item/{stem}.json'),
                'glowMetadata': resource(f'textures/item/{stem}_glow.png.mcmeta'),
            }
            if index == 0:
                base_bytes = ordinary_base.read_bytes()
                glow_bytes = (SRC / 'textures/item/echo_pickaxe_glow.png').read_bytes()
                model_bytes = (SRC / 'models/item/echo_pickaxe.json').read_bytes()
                meta_bytes = (SRC / 'textures/item/echo_pickaxe_glow.png.mcmeta').read_bytes()
                if (base_bytes, glow_bytes, model_bytes, meta_bytes) != (
                    old_bases[0], old_glows[0], old_models[0], old_metas[0]):
                    raise RuntimeError('ordinary index-0 quartet differs from the 0.1.11 baseline')
                for kind, path, data, before in (
                    ('base', paths['base'], base_bytes, old_bases[0]),
                    ('glow', paths['glow'], glow_bytes, old_glows[0]),
                    ('model', paths['model'], model_bytes, old_models[0]),
                    ('glowMetadata', paths['glowMetadata'], meta_bytes, old_metas[0]),
                ):
                    add(index, kind, path, data, before)
                empty = sorted([list(p) for p in ordinary_glow_alpha], key=lambda p:(p[1],p[0]))
                variants['0'] = {**paths, 'glowRegions': {
                    'cyanVeins': empty, 'redResonance': [], 'purpleFrequency': [], 'tuningStar': [], 'greenExtension': []}}
                continue

            sprite = neutral.copy()
            active_tier_names = selected_tiers(index)
            selected_diffs: dict[str, set[tuple[int,int]]] = {}
            written: dict[tuple[int,int], tuple[int,int,int,int]] = {}
            sp = sprite.load()
            for source_module, (candidate_module, level_key) in MODULE_MAP.items():
                level = levels(index)[level_key]
                if level == 0:
                    continue
                tier_name = STATE_GLOW_KEYS[source_module][level]
                tier = tier_images[tier_name].load()
                diff = tier_diffs[tier_name]
                selected_diffs[source_module] = diff
                for point in diff:
                    pixel = tier[point]
                    if point in written and written[point] != pixel:
                        raise RuntimeError(f'selected module tiers conflict at {point}')
                    written[point] = pixel
                    sp[point] = pixel

            # Highest state must reconstruct the approved mother image exactly.
            if index == 95 and sprite.tobytes() != approved.tobytes():
                raise RuntimeError('composed index 95 is not pixel-exact with approved-fullmax-128.png')
            alpha = {(x,y) for y in range(128) for x in range(128) if sp[x,y][3] > 0}
            if any(sp[x,y][3] not in (0,255) for y in range(128) for x in range(128)):
                raise RuntimeError(f'v{index:03d}: sprite alpha must be binary')

            groups = {}
            stable = {}
            candidate_cyan = cyan_source & alpha
            source_tiers = selected_tiers(index)
            for source_module, (candidate_module, _) in MODULE_MAP.items():
                if source_module not in source_tiers:
                    continue
                tier_name, _level = source_tiers[source_module]
                animated = points(mask_coordinates(source_glow_masks, source_module, tier_name),
                                  f'{tier_name} moduleGlowMasks')
                fixed = points(mask_coordinates(source_stable_masks, source_module, tier_name),
                               f'{tier_name} moduleGlowStableMasks')
                if animated & fixed:
                    raise RuntimeError(f'{tier_name}: animated and stable glow masks overlap')
                if not animated:
                    raise RuntimeError(f'{tier_name}: animated glow mask must contain selected facet/ridge points')
                if not (animated | fixed) <= alpha:
                    raise RuntimeError(f'{tier_name}: glow mask lies outside its variant alpha')
                groups[candidate_module] = animated | fixed
                stable[candidate_module] = fixed
            # Cyan is derived from neutral128 RGB, then excludes module regions and all selected facet masks.
            cyan = candidate_cyan - set().union(*groups.values()) if groups else candidate_cyan
            groups['cyanVeins'] = cyan
            all_lit = set().union(*groups.values())
            if not all_lit or not all_lit <= alpha:
                raise RuntimeError(f'v{index:03d}: emitted pixels must be nonempty and inside sprite alpha')

            strip = Image.new('RGBA', (128, 2048), (0,0,0,0))
            strip_pixels = strip.load()
            phases = GLOW_PHASE
            for frame in range(16):
                for group, coords in groups.items():
                    phase = phases[group]
                    for x, y in coords:
                        r, g, b, _ = sp[x,y]
                        factor = 1.0 if (x,y) in stable.get(group, set()) else 1.0 + 0.045 * math.sin(2*math.pi*frame/16 + phase)
                        strip_pixels[x, y + frame*128] = (max(0,min(255,round(r*factor))),
                                                           max(0,min(255,round(g*factor))),
                                                           max(0,min(255,round(b*factor))),255)
            litregions = {name: sorted([list(p) for p in coords], key=lambda p:(p[1],p[0]))
                          for name, coords in groups.items()}
            for name in ('redResonance','purpleFrequency','tuningStar','greenExtension'):
                litregions.setdefault(name, [])
            alpha_points = alpha
            model_bytes = make_model(old_models[index], alpha_points, all_lit)
            base_bytes = png_bytes(sprite)
            glow_bytes = png_bytes(strip)
            for kind, path, data, before in (
                ('base', paths['base'], base_bytes, old_bases[index]),
                ('glow', paths['glow'], glow_bytes, old_glows[index]),
                ('model', paths['model'], model_bytes, old_models[index]),
                ('glowMetadata', paths['glowMetadata'], meta128, old_metas[index]),
            ):
                add(index, kind, path, data, before)
            variants[str(index)] = {**paths, 'glowRegions': litregions}

    module_edit_masks = {candidate: candidate_edit_masks[candidate]
                         for candidate, _ in MODULE_MAP.values()}
    anchor_rel = ANCHOR.relative_to(ROOT).as_posix()
    proof_rel = PROOF.relative_to(ROOT).as_posix()
    manifest = {
        'schemaVersion': 1, 'status': 'frozen',
        'baseline': {'jar': 'jaysay-echo-tools-0.1.11.jar', 'sha256': BASELINE_SHA256},
        'plainAnchor': {'path': 'src/main/resources/assets/echopickaxe/textures/item/echo_pickaxe.png',
                        'sha256': '296326965171A658F9CD40E0C9C42FB3ABF5B1094AF9EFB0005096061C1711F5',
                        'index': 0, 'pixelExact': True},
        'fullmaxVisualTarget': {'path': anchor_rel, 'sha256': ANCHOR_SHA256, 'index': 95, 'pixelExact': True},
        'candidateMode': 'overlay',
        'moduleEditMasks': module_edit_masks,
        'moduleEditMasksSource': {'path': proof_rel, 'sha256': sha(proof_bytes)},
        'enhancedCyanMask': {
            'sourcePath': proof['states']['enhanced-neutral128']['path'],
            'sourceSha256': proof['states']['enhanced-neutral128']['sha256'],
            'selection': 'alpha==255 and r<=70 and g>=140 and b>=140 and g,b>=1.8*r; excludes union of moduleEditMasks',
            'coordinates': sorted([list(p) for p in cyan_source], key=lambda p:(p[1],p[0])),
            'count': len(cyan_source),
        },
        'geometry': {'pixelUnit': 0.125, 'z': [7.5, 8.5], 'modelCoverage': 'exact',
                     'preserveBaseModelOverrides': True, 'rebuildEveryStateOnOwnBaseAlpha': True},
        'glowContract': {'frames': 16, 'frameSize': 128, 'fixedAlpha': True,
                         'brightnessTolerance': 0.06, 'channelFloorTolerance': 4,
                         'frameTime': 3, 'interpolate': True},
        'resourceRows': rows, 'variants': variants,
        'sourceTierProofSha256': sha(proof_bytes),
        'levelsMapping': {str(i): levels(i) for i in range(96)},
    }
    (OUT / 'candidate-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(f'candidate generated: {len(rows)} resources, 96 states; fullmax index95 pixel-exact at 128x128; base alpha varies by state')

if __name__ == '__main__':
    main()
