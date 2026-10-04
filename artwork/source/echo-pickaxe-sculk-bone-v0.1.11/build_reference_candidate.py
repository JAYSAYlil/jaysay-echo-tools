"""Build isolated v0.1.11 native64 variants from the pinned approved reference."""
import hashlib
import importlib.util
import io
import json
import zipfile
from pathlib import Path, PurePosixPath

from PIL import Image, ImageChops, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
SRC = Path(__file__).resolve().parent
VAL = ROOT / 'artwork/validation/v0.1.11'
OUT = VAL / 'candidate'
JAR = ROOT / 'jaysay-echo-tools-0.1.10.jar'
JAR_SHA = '24E7807050FDB26C2A1C21F6854E9F391F9DAF42E86DBA8AB05A59D0546D20C0'
REF = SRC / 'user-selected-reference.png'
REF_SHA = '451476DBE5AB5AF151BF6A829A9B09EC8E7873B7F6638CAAA7DBC95CE4C71ACF'
NORMALIZED = ROOT / 'artwork/source/approved-reference-oct03-64/approved-reference-normalized64.png'
COMMON = ROOT / 'artwork/source/approved-reference-oct03-64/common64-unupgraded.png'
COMMON_GLOW = ROOT / 'artwork/source/approved-reference-oct03-64/common64-glow.png'
COMPONENT_MAP = ROOT / 'artwork/source/approved-reference-oct03-64/native64-component-map.json'
APPROVED_BUILDER = ROOT / 'artwork/source/approved-reference-oct03-64/build_approved64_variants.py'
GEOMETRY = ROOT / 'artwork/source/echo-pickaxe-native-edge-v0.1.8/build_native_edge_candidate.py'
PREVIEW = ROOT / 'artwork/source/echo-pickaxe-unified-head-v0.1.6/build_unified_head_candidate.py'
DRAFT = SRC / 'draft_user_reference_native64.py'
PREFIX = 'assets/echopickaxe/'
MASK_PATH = SRC / 'v0.1.11-base-edit-mask.png'
UNDERLAY_PATH = SRC / 'v0.1.11-frozen-underlay-v004.png'
MAP_PATH = SRC / 'v0.1.11-resource-map.json'
MANIFEST_PATH = SRC / 'v0.1.11-candidate-manifest.json'
INDICES = tuple(range(1, 96))
FRAMES = 16


def sha(data): return hashlib.sha256(data).hexdigest().upper()
def png_bytes(image):
    out = io.BytesIO(); image.save(out, format='PNG', optimize=False); return out.getvalue()
def json_bytes(value): return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
def read_png(data): return Image.open(io.BytesIO(data)).convert('RGBA')


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None: raise RuntimeError(f'Cannot load helper {path}')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


def paths_for(index):
    name = f'echo_pickaxe_v{index:03d}'
    return {'base': f'{PREFIX}textures/item/{name}.png',
            'glow': f'{PREFIX}textures/item/{name}_glow.png',
            'model': f'{PREFIX}models/item/{name}.json'}


def candidate_path(relative): return OUT / Path(*PurePosixPath(relative).parts)


def levels_for(index):
    return {'resonance': index // 32, 'frequency': (index % 32) // 8,
            'tuning': ((index % 32) % 8) // 4, 'extension': index % 4}


def active_pixels(tiers, levels, components):
    result = set()
    for name in components:
        for mask in tiers[name][:levels[name]]:
            result.update((i % 64, i // 64) for i, value in enumerate(mask.getdata()) if value)
    return result


def render_board(states, path, scale=3):
    margin, label_h, cell_w = 12, 25, 64 * scale + 18
    cell_h = 64 * scale + label_h + 8
    board = Image.new('RGB', (margin*2 + cell_w*len(states), margin*2 + 2*cell_h), (239,242,245))
    draw = ImageDraw.Draw(board)
    font = ImageFont.truetype(r'C:\Windows\Fonts\msyh.ttc', 13)
    for row, bg in enumerate(((255,255,255),(24,30,38))):
        y = margin + row*cell_h
        draw.text((margin, y+3), '白底' if row == 0 else '暗底', font=font, fill=(25,30,36))
        for col, (label, sprite) in enumerate(states):
            x = margin + col*cell_w
            draw.text((x+2,y+3), label, font=font, fill=(25,30,36))
            shown = sprite.resize((64*scale,64*scale), Image.Resampling.NEAREST)
            tile = Image.new('RGBA',shown.size,bg+(255,)); tile.alpha_composite(shown)
            board.paste(tile.convert('RGB'),(x,y+label_h))
    board.save(path)


def frontface(preview, sprite, glow, model, frame):
    return preview.frontface(sprite, glow, model, frame)


def main():
    if OUT.exists() and any(p.is_file() for p in OUT.rglob('*')):
        raise RuntimeError(f'Refusing to overwrite non-empty candidate: {OUT}')
    jar_bytes = JAR.read_bytes()
    if sha(jar_bytes) != JAR_SHA: raise RuntimeError('Pinned baseline JAR SHA mismatch')
    if sha(REF.read_bytes()) != REF_SHA: raise RuntimeError('User-selected reference SHA mismatch')
    normalized = Image.open(NORMALIZED).convert('RGBA')
    common = Image.open(COMMON).convert('RGBA')
    common_glow = Image.open(COMMON_GLOW).convert('RGBA')
    if normalized.size != (64,64) or common.size != (64,64) or common_glow.size != (64,1024):
        raise RuntimeError('Reference/common/glow dimensions mismatch')
    approved = load_module(APPROVED_BUILDER, 'v011_approved_builder')
    draft = load_module(DRAFT, 'v011_frozen_draft')
    geometry = load_module(GEOMETRY, 'v011_native_geometry')
    preview = load_module(PREVIEW, 'v011_frontface_preview')
    tiers, _, _ = approved.feature_masks(normalized)
    component_doc = json.loads(COMPONENT_MAP.read_text(encoding='utf-8'))
    module_emit = approved.emissive_masks(normalized, tiers)
    common_emit = {(x,y) for y in range(64) for x in range(64) if common_glow.getpixel((x,y))[3]}
    custom_left_emit = {(13,16),(11,18),(10,21),(10,23),(15,15),(20,16),(23,14)}
    custom_right_emit = {(53,22),(54,22),(56,24),(57,26)}
    custom_pommel_emit = {(9,50),(9,51),(10,51)}
    left_bone_mask={(17,17),(16,18),(15,18),(16,19),(15,19),(14,19),(15,20),(14,20),(13,20),
                    (14,21),(13,21),(12,21),(13,22),(12,22),(11,22),(12,23),(11,23),(10,23),
                    (11,24),(10,24),(9,24)}
    right_bone_mask={(56,22),(57,22),(56,23),(57,23),(57,28),(58,28),(57,29),(58,29),
                     (57,30),(58,30),(57,31),(58,31),(56,32),(57,32),(56,33),(57,33),
                     (56,34),(57,34),(56,35),(57,35)}
    pommel_bone_mask={(9,47),(10,47),(16,49),(17,50),(8,52),(9,53)}
    components = approved.COMPONENTS
    edit_mask = Image.new('RGBA',(64,64),(0,0,0,0))
    glow_mask = Image.new('RGBA',(64,64),(0,0,0,0))
    base_diff_union, added_union, removed_union = set(), set(), set()
    variants = {}
    state_faces = []
    state_frontfaces = []
    VAL.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    for sub in ('assets/echopickaxe/models/item','assets/echopickaxe/textures/item'):
        (OUT/sub).mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(io.BytesIO(jar_bytes)) as jar:
        ordinary_hook = read_png(jar.read(paths_for(4)['base']))
        # The shape source is the 0.1.10 res0 model's ordinary curved hook alpha;
        # RGB is never sampled from it.
        hook_shape = draft.old_hook_shape(ordinary_hook)
        for index in INDICES:
            levels = levels_for(index)
            state_underlay = common
            removed_underlay_bone = []
            if levels['frequency'] > 0:
                state_underlay, bone_mask = draft.sculk_underlay_without_bone(common)
                removed_underlay_bone = sorted([list(p) for p in bone_mask], key=lambda p:(p[1],p[0]))
            sprite = approved.state_sprite(normalized,state_underlay,tiers,levels)
            active = active_pixels(tiers,levels,components)
            approved_state = approved.state_sprite(normalized,common,tiers,levels)
            if levels['resonance'] == 0:
                sprite = draft.color_res0_hook(sprite,common,hook_shape,active)
                sprite = draft.refine_bare_head(sprite,common,active)
                for p in ((30,26),(31,26)):
                    if p not in active: sprite.putpixel(p,(0,0,0,0))
            if levels['frequency'] == 0:
                sprite = draft.refine_bare_right_tip(sprite,common)
            if levels['extension'] == 0:
                sprite = draft.refine_extension_zero_pommel(sprite,common)
            for p in active:
                if sprite.getpixel(p) != approved_state.getpixel(p):
                    raise RuntimeError(f'Active tier texel changed for v{index:03d} at {p}')

            paths = paths_for(index)
            old_base_bytes = jar.read(paths['base']); old_base = read_png(old_base_bytes)
            old_glow_bytes = jar.read(paths['glow']); old_glow = read_png(old_glow_bytes)
            old_model_bytes = jar.read(paths['model']); old_model = json.loads(old_model_bytes.decode('utf-8'))
            if old_glow.size != (64,1024): raise RuntimeError(f'Bad baseline glow size at {index}')
            base_changes = [(x,y,old_base.getpixel((x,y)),sprite.getpixel((x,y)))
                            for y in range(64) for x in range(64)
                            if old_base.getpixel((x,y)) != sprite.getpixel((x,y))]
            changed_pixels = {(x,y) for x,y,_,_ in base_changes}
            added = {(x,y) for y in range(64) for x in range(64)
                     if not old_base.getpixel((x,y))[3] and sprite.getpixel((x,y))[3]}
            removed = {(x,y) for y in range(64) for x in range(64)
                       if old_base.getpixel((x,y))[3] and not sprite.getpixel((x,y))[3]}
            base_diff_union |= changed_pixels; added_union |= added; removed_union |= removed
            for x,y in changed_pixels: edit_mask.putpixel((x,y),(255,255,255,255))

            glow_emit = set(common_emit)
            if levels['resonance'] == 0: glow_emit |= custom_left_emit
            if levels['frequency'] == 0: glow_emit |= custom_right_emit
            if levels['extension'] == 0: glow_emit |= custom_pommel_emit
            if levels['resonance'] == 0: glow_emit -= left_bone_mask
            if levels['frequency'] == 0: glow_emit -= right_bone_mask
            if levels['extension'] == 0: glow_emit -= pommel_bone_mask
            glow_emit &= {(x,y) for y in range(64) for x in range(64) if sprite.getpixel((x,y))[3]}
            glow, lit = approved.glow_strip(sprite,normalized,glow_emit,module_emit,levels)
            glow_frame_records=[]
            for y in range(64):
                for x in range(64):
                    if glow.getpixel((x,y))[3]: glow_mask.putpixel((x,y),(255,255,255,255))
            for frame in range(FRAMES):
                frame_diff=[]
                offset=frame*64
                for y in range(64):
                    for x in range(64):
                        before=old_glow.getpixel((x,y+offset))
                        after=glow.getpixel((x,y+offset))
                        if before != after: frame_diff.append([x,y,list(before),list(after)])
                alpha_mask=sorted([[x,y] for y in range(64) for x in range(64) if glow.getpixel((x,y+offset))[3]],key=lambda p:(p[1],p[0]))
                glow_frame_records.append({'frame':frame,'changedPixelCount':len(frame_diff),
                                           'changedRGBA':frame_diff,'alphaTexels':len(alpha_mask),
                                           'alphaMaskSha256':sha(json_bytes(alpha_mask))})

            expected_model, _, expected_lit = approved.model_for_state(
                old_model,f'echo_pickaxe_v{index:03d}',sprite,lit)
            model, sidewall_changes = geometry.update_model_preserving_geometry(old_model,expected_model,removed,added,removed|added)
            approved.validate_model(sprite,model,expected_lit,f'echo_pickaxe_v{index:03d}')
            if model.get('overrides',[]) != old_model.get('overrides',[]):
                raise RuntimeError(f'Predicate overrides changed for v{index:03d}')
            model_bytes = geometry.json_bytes(model)
            base_bytes, glow_bytes = png_bytes(sprite), png_bytes(glow)
            outputs={'base':base_bytes,'glow':glow_bytes,'model':model_bytes}
            resource_info={}
            for kind,data in outputs.items():
                rel=paths[kind]
                target=candidate_path(rel)
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(data)
                resource_info[kind]={'path':rel,'sha256':sha(data),'bytes':len(data),
                                     'baselineSha256':sha({'base':old_base_bytes,'glow':old_glow_bytes,'model':old_model_bytes}[kind]),
                                     'changed':data != {'base':old_base_bytes,'glow':old_glow_bytes,'model':old_model_bytes}[kind]}
            variants[str(index)]={
                'levels':levels,'resources':resource_info,
                'counts':{'baseChangedTexels':len(base_changes),'alphaAdded':len(added),'alphaRemoved':len(removed),
                          'glowLitTexels':len(lit),'modelElements':len(model['elements']),
                          'sidewallChanges':len(sidewall_changes)},
                'baseChangedPixels':[[x,y] for x,y,_,_ in base_changes],
                'baseRGBAChanges':[[x,y,list(before),list(after)] for x,y,before,after in base_changes],
                'alphaAdded':sorted([list(p) for p in added],key=lambda p:(p[1],p[0])),
                'alphaRemoved':sorted([list(p) for p in removed],key=lambda p:(p[1],p[0])),
                'modelSidewallChanges':sidewall_changes,
                'glowFrames':glow_frame_records,
                'glowLitCoordinates':sorted([list(p) for p in lit],key=lambda p:(p[1],p[0])),
                'frequencyBareBoneSourceMask':removed_underlay_bone,
                'activeComponentPixelCount':len(active),
                'fullmaxMatchesReference':index != 95 or ImageChops.difference(sprite,normalized).getbbox() is None}
            if index == 95 and ImageChops.difference(sprite,normalized).getbbox() is not None:
                raise RuntimeError('v095 must be pixel-exact to approved normalized64')
            if index in (1,2,3,4,8,16,24,32,64,95):
                label=f'v{index:03d} · R{levels["resonance"]} F{levels["frequency"]} T{levels["tuning"]} E{levels["extension"]}'
                state_faces.append((label,sprite))
                state_frontfaces.append((label,frontface(preview,sprite,glow,model,0)))

    mask_bytes=png_bytes(edit_mask); glow_mask_bytes=png_bytes(glow_mask)
    MASK_PATH.write_bytes(mask_bytes)
    (SRC/'v0.1.11-glow-mask.png').write_bytes(glow_mask_bytes)
    # Freeze v004 after all conditional treatment as the editable native64 underlay.
    underlay=Image.open(VAL/'draft/v004-approved-reference-native64-draft.png').convert('RGBA')
    underlay_bytes=png_bytes(underlay); UNDERLAY_PATH.write_bytes(underlay_bytes)
    render_board(state_faces,VAL/'v0.1.11-candidate-tier-states-native3x-white-dark.png',3)
    render_board(state_frontfaces,VAL/'v0.1.11-candidate-tier-states-frontface-frame0-white-dark.png',3)
    map_doc={
        'schema':1,'status':'frozen-candidate-awaiting-independent-audit','version':'0.1.11-user-selected-reference-native64',
        'baseline':{'jar':JAR.name,'sha256':JAR_SHA,'commit':'0f31d394d00b43a192b733f743c90645cc77ebb6'},
        'reference':{'path':str(REF.relative_to(ROOT)).replace('\\','/'),'sha256':sha(REF.read_bytes()),
                     'approvedNormalized64':str(NORMALIZED.relative_to(ROOT)).replace('\\','/'),
                     'approvedNormalized64Sha256':sha(NORMALIZED.read_bytes()),
                     'common64':str(COMMON.relative_to(ROOT)).replace('\\','/'),'common64Sha256':sha(COMMON.read_bytes())},
        'generator':{'draft':str(DRAFT.relative_to(ROOT)).replace('\\','/'),'sha256':sha(DRAFT.read_bytes()),
                     'builder':str(Path(__file__).relative_to(ROOT)).replace('\\','/'),'sha256Builder':sha(Path(__file__).read_bytes())},
        'scope':{'ordinaryResources':'indices 000 ordinary quartet are excluded and remain pinned 0.1.10 bytes',
                 'upgradedIndices':list(INDICES),'variantCount':len(INDICES),'allowedResourcesPerVariant':['base','glow','model'],
                 'otherItemsMetadataDataAndJava':'unchanged; not emitted to candidate',
                 'conditionalBladeBone':'resonance 0 left bone blade only; resonance >=1 uses approved red tier. frequency 0 right bone blade only; frequency >=1 uses sculk underlay and approved purple tiers.',
                 'extensionPommel':'extension 0 has a compact round sculk core and three separated bone clasps; extension >=1 keeps approved eye tiers.',
                 'activeTierPixels':'approved reference tier pixels are composited after underlay edits and remain exact; see activeComponentPixelCount and approved component map.'},
        'conditionalBoneMasks':{'leftRes0Blade':sorted([list(p) for p in left_bone_mask],key=lambda p:(p[1],p[0])),
                                'rightFrequency0Blade':sorted([list(p) for p in right_bone_mask],key=lambda p:(p[1],p[0])),
                                'extension0PommelClasps':sorted([list(p) for p in pommel_bone_mask],key=lambda p:(p[1],p[0])),
                                'frequencyPositiveUnderlayRemoved':sorted([list(p) for p in draft.sculk_underlay_without_bone(common)[1]],key=lambda p:(p[1],p[0]))},
        'componentMap':{'path':str(COMPONENT_MAP.relative_to(ROOT)).replace('\\','/'),'sha256':sha(COMPONENT_MAP.read_bytes())},
        'masks':{'baseEdit':{'path':str(MASK_PATH.relative_to(ROOT)).replace('\\','/'),'sha256':sha(mask_bytes),
                             'changedPixelsUnion':sum(1 for p in edit_mask.getdata() if p[3])},
                 'glowEmit':{'path':str((SRC/'v0.1.11-glow-mask.png').relative_to(ROOT)).replace('\\','/'),
                             'sha256':sha(glow_mask_bytes),'emissivePixels':sum(1 for p in glow_mask.getdata() if p[3])},
                 'frozenV004Underlay':{'path':str(UNDERLAY_PATH.relative_to(ROOT)).replace('\\','/'),'sha256':sha(underlay_bytes)}},
        'alphaPolicy':{'outlineSource':'pinned v004 alpha only; no source RGB/luminance/material sampling',
                       'perVariant':{str(i):{'added':v['alphaAdded'],'removed':v['alphaRemoved']} for i,v in variants.items()}},
        'glowPolicy':'16 frames, 3 ticks each, frame phase follows approved glow_strip pulse. Bone facets are not emissive. Native cyan seams/core use sparse approved body pulse; glow mask is fixed over time and constrained to opaque base texels.',
        'variants':variants,
        'previews':['artwork/validation/v0.1.11/v0.1.11-candidate-tier-states-native3x-white-dark.png',
                    'artwork/validation/v0.1.11/v0.1.11-candidate-tier-states-frontface-frame0-white-dark.png']}
    map_bytes=json_bytes(map_doc); MAP_PATH.write_bytes(map_bytes)
    all_resources=[v['resources'][kind] for v in variants.values() for kind in ('base','glow','model')]
    manifest={'schema':1,'status':'frozen-candidate-awaiting-independent-audit','baselineJar':JAR.name,
              'baselineJarSha256':JAR_SHA,'referenceSha256':sha(REF.read_bytes()),'approvedNormalized64Sha256':sha(NORMALIZED.read_bytes()),
              'upgradedIndices':list(INDICES),'upgradedVariantCount':len(INDICES),'resourceCount':len(all_resources),
              'changedResourceCount':sum(1 for r in all_resources if r['changed']),
              'candidateRoot':str(OUT.relative_to(ROOT)).replace('\\','/'),
              'map':str(MAP_PATH.relative_to(ROOT)).replace('\\','/'),'mapSha256':sha(map_bytes),
              'baseEditMask':map_doc['masks']['baseEdit'],'glowMask':map_doc['masks']['glowEmit'],
              'frozenUnderlay':map_doc['masks']['frozenV004Underlay'],
              'resources':all_resources,'productionChanged':False}
    manifest_bytes=json_bytes(manifest); MANIFEST_PATH.write_bytes(manifest_bytes)
    (OUT/'candidate-manifest.json').write_bytes(manifest_bytes)
    print(f'PASS candidate generated: variants={len(INDICES)} resources={len(all_resources)} changed={manifest["changedResourceCount"]}')
    print(f'baseline={JAR_SHA}; map={sha(map_bytes)}; manifest={sha(manifest_bytes)}; mask={sha(mask_bytes)}; glowMask={sha(glow_mask_bytes)}')
    print(f'candidate={OUT}')


if __name__ == '__main__': main()
