"""Generate the 0.1.15 candidate only after root freezes and approves static source.

This script deliberately has no implicit first-run behavior: the frozen proof,
root approval record, pinned 0.1.14 baseline, and empty output directory are gates.
"""
from __future__ import annotations

import hashlib
import json
import math
import zipfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
ART = ROOT / 'artwork/source/root-tier-polish-v0.1.15'
PROOF = ROOT / 'artwork/validation/v0.1.15/root-tier-polish/tier-manifest.json'
APPROVAL = ROOT / 'artwork/validation/v0.1.15/root-tier-polish/static-approval.json'
VAL = ROOT / 'artwork/validation/v0.1.15/root-tier-polish'
OUT = VAL / 'candidate'
BASELINE = ROOT / 'jaysay-echo-tools-0.1.14.jar'
SRC = ROOT / 'src/main/resources/assets/echopickaxe'
BASELINE_SHA256 = '43D8B35550E6A30B506D51E8718168EEF6C29D5F3288C17EFDF5C9E00CA62B28'
MODULE_MAP = {
    'resonance': ('redResonance', 'resonance'),
    'split': ('purpleFrequency', 'split'),
    'tuning': ('tuningStar', 'tuning'),
    'extension': ('greenExtension', 'extension'),
}
MODULE_BOUNDS = {}
TIERS = {
    'resonance': {1:'resonance1',2:'resonance2'},
    'split': {1:'split1',2:'split2',3:'split3'},
    'tuning': {1:'tuning1'},
    'extension': {1:'extension1',2:'extension2',3:'extension3'},
}
ORDINARY_BASE_SHA256 = '296326965171A658F9CD40E0C9C42FB3ABF5B1094AF9EFB0005096061C1711F5'


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def levels(index: int) -> dict[str,int]:
    return {'resonance':index//32,'split':(index%32)//8,'tuning':(index%8)//4,'extension':index%4}


def rel(path: str) -> str:
    return 'assets/echopickaxe/' + path


def points(raw, label: str) -> set[tuple[int,int]]:
    if not isinstance(raw,list):
        raise ValueError(f'{label}: expected a coordinate array')
    result=set()
    for pair in raw:
        if not isinstance(pair,list) or len(pair)!=2:
            raise ValueError(f'{label}: invalid coordinate {pair!r}')
        p=(int(pair[0]),int(pair[1]))
        if not (0<=p[0]<128 and 0<=p[1]<128) or p in result:
            raise ValueError(f'{label}: out-of-bounds or duplicate coordinate {p}')
        result.add(p)
    return result


def image(path: Path, size=(128,128)) -> Image.Image:
    value=Image.open(path).convert('RGBA')
    if value.size != size:
        raise ValueError(f'{path}: expected {size}, got {value.size}')
    return value


def proof_image(proof: dict, name: str, size=(128,128)) -> Image.Image:
    entry=proof['states'][name]
    path=(ROOT/entry['path']).resolve()
    if not path.is_file() or sha(path.read_bytes()) != entry['sha256'].upper():
        raise RuntimeError(f'{name}: frozen source path/hash mismatch')
    return image(path,size)


def proof_entry_image(entry: dict, label: str, size=(128,128)) -> Image.Image:
    path=(ROOT/entry['path']).resolve()
    if not path.is_file() or sha(path.read_bytes())!=entry['sha256'].upper():
        raise RuntimeError(f'{label}: frozen source path/hash mismatch')
    return image(path,size)


def diff(a: Image.Image,b: Image.Image) -> set[tuple[int,int]]:
    ap,bp=a.load(),b.load()
    return {(x,y) for y in range(a.height) for x in range(a.width) if ap[x,y]!=bp[x,y]}


def state_tiers(index: int) -> dict[str,str]:
    lv=levels(index)
    return {module:TIERS[module][lv[key]] for module,(_,key) in MODULE_MAP.items() if lv[key]>0}


def fixed_point_fx(proof: dict, tier: str, module: str,
                   animated: set[tuple[int,int]]) -> dict[tuple[int,int],tuple[float,float]]:
    raw_phase=proof['moduleGlowPhaseRadians'][tier][module]
    raw_amplitude=proof['moduleGlowAmplitude'][tier][module]
    phases={tuple(map(int,key.split(','))):float(value) for key,value in raw_phase.items()}
    amplitudes={tuple(map(int,key.split(','))):float(value) for key,value in raw_amplitude.items()}
    if set(phases)!=animated or set(amplitudes)!=animated:
        raise RuntimeError(f'{tier}: fixed phase/amplitude keys must exactly match dynamic glow points')
    if any(not math.isfinite(value) for value in phases.values()):
        raise RuntimeError(f'{tier}: phase map contains non-finite values')
    if any(not math.isfinite(value) or not 0.0<=value<=0.06 for value in amplitudes.values()):
        raise RuntimeError(f'{tier}: point amplitudes must be in [0, 0.06]')
    stable={tuple(p) for p in proof['moduleGlowStableMasks'][tier][module]}
    records=proof['moduleGlowPoints'][tier][module]
    record_map={}
    for item in records:
        point=(int(item['x']),int(item['y']))
        if point in record_map or not isinstance(item.get('group'),str) or not item['group']:
            raise RuntimeError(f'{tier}: malformed or duplicate moduleGlowPoints record {point}')
        record_map[point]=item
    if set(record_map)!=animated|stable:
        raise RuntimeError(f'{tier}: moduleGlowPoints do not exactly cover animated and stable masks')
    for point,item in record_map.items():
        if bool(item['stable']) != (point in stable):
            raise RuntimeError(f'{tier}: point stable flag disagrees with stable mask at {point}')
        if point in stable:
            if float(item['phaseRadians'])!=0.0 or float(item['amplitude'])!=0.0:
                raise RuntimeError(f'{tier}: stable point must have zero phase/amplitude')
        elif (float(item['phaseRadians']),float(item['amplitude']))!=(phases[point],amplitudes[point]):
            raise RuntimeError(f'{tier}: point record disagrees with fixed phase/amplitude map at {point}')
    return {point:(phases[point],amplitudes[point]) for point in animated}


def in_scope(points: set[tuple[int,int]], module: str) -> bool:
    x0,y0,x1,y1=MODULE_BOUNDS[module]
    return all(x0<=x<=x1 and y0<=y<=y1 for x,y in points)


def nearest_double(img: Image.Image) -> Image.Image:
    if img.size != (64,64):
        raise ValueError(f'ordinary anchor must remain 64x64, got {img.size}')
    result=img.resize((128,128),Image.Resampling.NEAREST)
    px=result.load()
    for y in range(128):
        for x in range(128):
            if px[x,y][3]==0:
                px[x,y]=(0,0,0,0)
    return result


def static_review_gate(proof: dict, proof_bytes: bytes, approval: dict) -> None:
    if sha(proof_bytes) != approval.get('staticProofSha256','').upper():
        raise RuntimeError('static approval does not pin this exact source proof hash')
    if approval.get('status') != 'approved' or approval.get('reviewedBy') != 'root':
        raise RuntimeError('root has not approved this frozen static proof')
    if proof.get('schema')!='root-pixel-states-v0.1.15-v1':
        raise RuntimeError('unexpected root-pixel 0.1.15 tier-manifest schema')
    allmax=proof['states']['all_max']
    if sha((ROOT/allmax['path']).read_bytes())!=approval.get('approvedAllMaxSha256','').upper():
        raise RuntimeError('root approval does not pin the all_max source image')
    expected={tier for module_tiers in TIERS.values() for tier in module_tiers.values()}
    if not expected.issubset(proof.get('states',{})):
        raise RuntimeError('tier manifest is missing one or more frozen source states')


def png_bytes(img: Image.Image) -> bytes:
    from io import BytesIO
    stream=BytesIO(); img.save(stream,format='PNG',optimize=False); return stream.getvalue()


def animation_metadata(width=128) -> bytes:
    data={'animation':{'width':width,'height':width,'frametime':3,'interpolate':True,
                       'frames':[{'index':i} for i in range(16)]}}
    return (json.dumps(data,indent=2)+'\n').encode()


def make_model(old_bytes: bytes, alpha: set[tuple[int,int]], lit: set[tuple[int,int]]) -> bytes:
    model=json.loads(old_bytes.decode('utf-8'))
    cell=16/128; elements=[]
    for x,y in sorted(alpha,key=lambda p:(p[1],p[0])):
        uv=[(x+.5)*cell,(y+.5)*cell,(x+.5)*cell,(y+.5)*cell]
        faces={}
        for side in ('north','south'):
            face={'uv':uv,'texture':'#glow' if (x,y) in lit else '#layer0'}
            if (x,y) in lit:
                face['forge_data']={'block_light':15,'sky_light':15,'ambient_occlusion':False}
            faces[side]=face
        for side,q in {'west':(x-1,y),'east':(x+1,y),'up':(x,y-1),'down':(x,y+1)}.items():
            if q not in alpha: faces[side]={'uv':uv,'texture':'#layer0'}
        elements.append({'from':[x*cell,16-(y+1)*cell,7.5],
                         'to':[(x+1)*cell,16-y*cell,8.5],'shade':False,'faces':faces})
    model['elements']=elements
    return (json.dumps(model,ensure_ascii=False,indent=2)+'\n').encode()


def main() -> None:
    if not BASELINE.is_file() or sha(BASELINE.read_bytes()) != BASELINE_SHA256:
        raise RuntimeError('installed 0.1.14 baseline JAR hash mismatch')
    if not PROOF.is_file() or not APPROVAL.is_file():
        raise RuntimeError('0.1.15 source proof and root static approval must exist before candidate generation')
    proof_bytes=PROOF.read_bytes(); proof=json.loads(proof_bytes.decode('utf-8-sig'))
    approval=json.loads(APPROVAL.read_text(encoding='utf-8-sig'))
    if proof.get('schema')!='root-pixel-states-v0.1.15-v1' or proof.get('status')!='frozen':
        raise RuntimeError('unexpected or stale root-pixel 0.1.15 tier-manifest')
    if approval.get('rootPixelStates',{}).get('sha256','').upper()!=proof.get('sourceRootPixelStates',{}).get('sha256','').upper():
        raise RuntimeError('root approval is for another root pixel JSON')
    if approval.get('renderedPreview',{}).get('auditSha256','').upper()!=proof.get('renderAudit',{}).get('sha256','').upper():
        raise RuntimeError('root approval pins another rendered preview audit')
    static_review_gate(proof,proof_bytes,approval)
    MODULE_BOUNDS.update({module:tuple(bounds) for module,bounds in proof['componentBounds128'].items()})
    if set(MODULE_BOUNDS)!=set(MODULE_MAP):
        raise RuntimeError('root proof component bounds do not exactly cover all four modules')
    if proof.get('levelsMapping') != {
        'resonance':[0,1,2],'split':[0,1,2,3],'tuning':[0,1],'extension':[0,1,2,3],
        'candidateIndexFormula':'resonance*32 + split*8 + tuning*4 + extension'}:
        raise RuntimeError('0..95 item index/level mapping changed')
    if OUT.exists() and any(OUT.iterdir()):
        raise RuntimeError(f'refusing to overwrite candidate output {OUT}')

    with zipfile.ZipFile(BASELINE) as old:
        ordinary={kind:old.read(path) for kind,path in (
            ('base',rel('textures/item/echo_pickaxe.png')),
            ('glow',rel('textures/item/echo_pickaxe_glow.png')),
            ('model',rel('models/item/echo_pickaxe.json')),
            ('glowMetadata',rel('textures/item/echo_pickaxe_glow.png.mcmeta')))}
        ordinary_source={kind:(SRC/path.split('assets/echopickaxe/')[1]).read_bytes()
                         for kind,path in (
            ('base',rel('textures/item/echo_pickaxe.png')),
            ('glow',rel('textures/item/echo_pickaxe_glow.png')),
            ('model',rel('models/item/echo_pickaxe.json')),
            ('glowMetadata',rel('textures/item/echo_pickaxe_glow.png.mcmeta')))}
        if ordinary_source != ordinary:
            raise RuntimeError('ordinary index-0 quartet differs from installed 0.1.14 baseline')
        ordinary64=image(SRC/'textures/item/echo_pickaxe.png',(64,64))
        if sha(ordinary_source['base']) != ORDINARY_BASE_SHA256:
            raise RuntimeError('ordinary64 visual anchor hash changed')
        base128=nearest_double(ordinary64)
        proof_base=proof_entry_image(proof['ordinary128Base'],'ordinary128Base')
        if proof_base.tobytes()!=base128.tobytes():
            raise RuntimeError('proof ordinaryBase128 is not an exact 2x nearest-neighbor upscale of ordinary64')

        part_masks={module:points(proof['moduleEditMasks'][module]['coordinates'],f'{module} moduleEditMask')
                    for module in MODULE_MAP}
        for module,mask in part_masks.items():
            if not in_scope(mask,module):
                raise RuntimeError(f'{module}: moduleEditMask escapes the independently approved component bounds')
        part_union=set().union(*part_masks.values())
        if sum(map(len,part_masks.values())) != len(part_union):
            raise RuntimeError('modulePartMasks overlap; proof must disambiguate component ownership before building')
        tier_images={}; tier_masks={}
        for module,tiers in TIERS.items():
            for tier in tiers.values():
                state=proof_image(proof,tier)
                mask=points(proof['moduleTierMasks'][tier][module]['coordinates'],f'{tier} overlay mask')
                changed=diff(base128,state)
                if changed != mask:
                    raise RuntimeError(f'{tier}: source tier mask must exactly equal all RGBA diffs from ordinaryBase128')
                if not changed <= part_masks[module]:
                    raise RuntimeError(f'{tier}: source edits escape the owning module part mask')
                if not in_scope(changed,module):
                    raise RuntimeError(f'{tier}: source diff escapes independently approved component bounds')
                tier_images[tier]=state; tier_masks[tier]=mask

        allmax=proof_image(proof,'all_max')
        # Prove root-approved all_max is exactly the active-module composition, not a whole-image reference redraw.
        composite=base128.copy(); cp=composite.load()
        for module,tiers in TIERS.items():
            tier=tiers[max(tiers)]; layer=tier_images[tier].load()
            for p in tier_masks[tier]: cp[p]=layer[p]
        if composite.tobytes()!=allmax.tobytes():
            raise RuntimeError('all_max static source is not exactly ordinaryBase128 plus active module overlays')

        # Preserve the ordinary animation by nearest-neighbor scaling each 64px frame.
        ordinary_glow=Image.open(SRC/'textures/item/echo_pickaxe_glow.png').convert('RGBA')
        if ordinary_glow.size!=(64,1024): raise RuntimeError('ordinary glow atlas must be 16 frames of 64x64')
        glow_meta=json.loads((SRC/'textures/item/echo_pickaxe_glow.png.mcmeta').read_text(encoding='utf-8-sig'))['animation']
        if glow_meta.get('width',64)!=64 or glow_meta.get('height',64)!=64:
            raise RuntimeError('ordinary glow metadata must define 64x64 frames')
        ordinary_frames=[]
        for frame in range(16):
            crop=ordinary_glow.crop((0,frame*64,64,(frame+1)*64))
            ordinary_frames.append(crop.resize((128,128),Image.Resampling.NEAREST))
        base_glow_alpha={(x,y) for y in range(128) for x in range(128)
                         if ordinary_frames[0].getpixel((x,y))[3]>0}
        if any({(x,y) for y in range(128) for x in range(128) if f.getpixel((x,y))[3]>0} != base_glow_alpha
               for f in ordinary_frames[1:]):
            raise RuntimeError('ordinary glow alpha is not fixed across its 16 frames')

        OUT.mkdir(parents=True,exist_ok=True)
        rows=[]; variants={}
        def add(index,kind,path,data,before):
            target=OUT/path; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(data)
            rows.append({'index':index,'kind':kind,'path':path,'sha256':sha(data),
                         'baselineSha256':sha(before),'changed':data!=before,'bytes':len(data)})

        for index in range(96):
            stem='echo_pickaxe' if index==0 else f'echo_pickaxe_v{index:03d}'
            paths={'base':rel(f'textures/item/{stem}.png'),'glow':rel(f'textures/item/{stem}_glow.png'),
                   'glowMetadata':rel(f'textures/item/{stem}_glow.png.mcmeta'),
                   'model':rel(f'models/item/{stem}.json')}
            before={kind:old.read(path) for kind,path in paths.items()}
            if index==0:
                for kind,data in ordinary.items(): add(0,kind,paths[kind],data,before[kind])
                continue
            sprite=base128.copy(); sp=sprite.load(); selected=state_tiers(index); active_masks={}
            for module,tier in selected.items():
                layer=tier_images[tier].load(); mask=tier_masks[tier]; active_masks[module]=mask
                for p in mask: sp[p]=layer[p]
            if index==95 and sprite.tobytes()!=allmax.tobytes():
                raise RuntimeError('index95 composition differs from root-approved all_max static source')
            alpha={(x,y) for y in range(128) for x in range(128) if sp[x,y][3]>0}
            if any(sp[x,y][3] not in (0,255) for y in range(128) for x in range(128)):
                raise RuntimeError(f'{stem}: alpha must be binary')

            # Base-body cyan glow is the ordinary 64px strip scaled 2x; only currently
            # active module edits replace these texels with the tier's own facet glow.
            active_edit=set().union(*active_masks.values()) if active_masks else set()
            retained_base_glow=base_glow_alpha-active_edit
            if not retained_base_glow<=alpha:
                raise RuntimeError(f'{stem}: retained ordinary nearest-2x glow leaves sprite alpha')
            groups={'cyanVeins':retained_base_glow}
            stable={}
            fx_by_module={}
            point_records={}
            for module,tier in selected.items():
                anim=points(proof['moduleGlowMasks'][tier][module],f'{tier} moduleGlowMasks')
                fixed=points(proof['moduleGlowStableMasks'][tier][module],f'{tier} stable glow masks')
                if not anim or anim&fixed or not (anim|fixed)<=active_masks[module] or not (anim|fixed)<=alpha:
                    raise RuntimeError(f'{tier}: glow coordinates must be active-tier pixels on the sprite alpha')
                fx_by_module[module]=fixed_point_fx(proof,tier,module,anim)
                point_records[MODULE_MAP[module][0]]=[dict(item) for item in proof['moduleGlowPoints'][tier][module]]
                groups[MODULE_MAP[module][0]]=anim|fixed; stable[MODULE_MAP[module][0]]=fixed
            if any(groups[a]&groups[b] for i,a in enumerate(groups) for b in list(groups)[i+1:]):
                raise RuntimeError(f'{stem}: body cyan and module glow groups overlap')
            for key,_ in MODULE_MAP.values(): groups.setdefault(key,set())
            lit=set().union(*groups.values())
            strip=Image.new('RGBA',(128,2048),(0,0,0,0)); gp=strip.load(); sp=sprite.load()
            for frame in range(16):
                base_frame=ordinary_frames[frame].load()
                for y in range(128):
                    for x in range(128):
                        if (x,y) not in active_edit:
                            gp[x,y+frame*128]=base_frame[x,y]
                for module,tier in selected.items():
                    key=MODULE_MAP[module][0]
                    for x,y in groups[key]:
                        r,g,b,_=sp[x,y]
                        if (x,y) in stable[key]:
                            factor=1.0
                        else:
                            phase,amplitude=fx_by_module[module][(x,y)]
                            factor=1.0+amplitude*math.sin(2*math.pi*frame/16+phase)
                        gp[x,y+frame*128]=(max(0,min(255,round(r*factor))),
                                           max(0,min(255,round(g*factor))),
                                           max(0,min(255,round(b*factor))),255)
            model=make_model(before['model'],alpha,lit)
            generated={'base':png_bytes(sprite),'glow':png_bytes(strip),
                       'glowMetadata':animation_metadata(128),'model':model}
            if levels(index)['resonance'] == 0:
                # No resonance polish can affect these 31 variants; retain the
                # complete baseline resource bytes rather than reserializing them.
                generated = before
            for kind,data in generated.items(): add(index,kind,paths[kind],data,before[kind])
            variants[str(index)]={**paths,'glowRegions':{k:[list(p) for p in sorted(v,key=lambda q:(q[1],q[0]))]
                                                         for k,v in groups.items()},
                                  'glowPointEffects':point_records}

    manifest={
        'schemaVersion':1,'status':'frozen','version':'0.1.15',
        'baseline':{'jar':'jaysay-echo-tools-0.1.14.jar','sha256':BASELINE_SHA256},
        'ordinary0':{'byteExact':True,'sha256':sha(ordinary['base'])},
        'ordinaryBase128':{'derivedFrom':'ordinary0 64x64','resampling':'nearest-2x','sha256':sha(png_bytes(base128))},
        'approvedAllMaxStatic':{'sourcePath':proof['states']['all_max']['path'],
                                'sourceSha256':proof['states']['all_max']['sha256'],
                                'index':95,'pixelExact':True},
        'candidateMode':'ordinary-base-plus-active-module-overlays',
        'staticProof':{'path':PROOF.relative_to(ROOT).as_posix(),'sha256':sha(proof_bytes),
                       'approvalPath':APPROVAL.relative_to(ROOT).as_posix(),'approvalSha256':sha(APPROVAL.read_bytes())},
        'modulePartMasks':{m:sorted([list(p) for p in part_masks[m]],key=lambda q:(q[1],q[0])) for m in MODULE_MAP},
        'geometry':{'pixelUnit':0.125,'z':[7.5,8.5],'modelCoverage':'each-state-own-alpha','preserveBaseModelOverrides':True},
        'glowContract':{'frames':16,'frameSize':128,'fixedAlpha':True,'brightnessTolerance':0.06,'frameTime':3,'interpolate':True},
        'resourceRows':rows,'variants':variants,
        'levelsMapping':{str(i):levels(i) for i in range(96)},
    }
    (OUT/'candidate-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'candidate generated: {len(rows)} resource rows; 0.1.15 is not built or installed by this script')


if __name__=='__main__':
    main()
