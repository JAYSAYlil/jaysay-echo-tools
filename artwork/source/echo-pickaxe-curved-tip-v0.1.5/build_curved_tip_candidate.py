"""Build isolated 0.1.5 native64 tip candidate from pinned 0.1.2/0.1.4 JARs."""
import copy,hashlib,importlib.util,io,json,math,shutil,zipfile
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[3]
SRC=Path(__file__).resolve().parent
OUT=ROOT/'artwork/validation/v0.1.5/curved-tip-candidate'
DRAFT=ROOT/'artwork/validation/v0.1.5/curved-tip-draft'
ORD=ROOT/'jaysay-echo-tools-0.1.2.jar';ORD_SHA='7312AE7B54F3DAD998815B7C7BD601B65DB1BED23A21CC7AA8448E40E082F495'
BASE=ROOT/'jaysay-echo-tools-0.1.4.jar';BASE_SHA='9A3D6C0D9B5485C397117CBF00C00C31DA04A339838831231EC5C31B552D67AF'
GEN=ROOT/'artwork/source/approved-reference-oct03-64/build_approved64_variants.py'
PREFIX='assets/echopickaxe/'
REGION=(7,8,33,28) # x7..32 / y8..27
REQUIRED={12:(21,30),13:(23,30),14:(25,30),15:(25,30),16:(27,30),17:(27,30)}
CONNECTION={'requiredOpaque':[[x,y] for y,(lo,hi) in REQUIRED.items() for x in range(lo,hi+1)],
  'anchors':[[[x,y] for y in range(20,24) for x in range(10,14)],
             [[x,10] for x in range(29,33)]],
  'crossSections':[{'name':f'bridge-row-y{y}','pixels':[[x,y] for x in range(lo,hi+1)]} for y,(lo,hi) in REQUIRED.items()],
  'minimumThicknessVoxels':2}
LIGHT={'block_light':15,'sky_light':15,'ambient_occlusion':False}

def sha(b):return hashlib.sha256(b).hexdigest().upper()
def png(b):return Image.open(io.BytesIO(b)).convert('RGBA')
def png_bytes(im):
    stream=io.BytesIO();im.save(stream,format='PNG',optimize=False);return stream.getvalue()
def jbytes(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
def asset(z,name):return png(z.read(PREFIX+name))
def mask_coords(im):return {(x,y) for y in range(im.height) for x in range(im.width) if im.getpixel((x,y))[3]}
def load_helper():
    spec=importlib.util.spec_from_file_location('approved64_curved_tip_helpers',GEN)
    if spec is None or spec.loader is None:raise RuntimeError('Cannot load 64px mesh helpers')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def get_font(size):
    for p in ('C:/Windows/Fonts/arial.ttf','C:/Windows/Fonts/segoeui.ttf'):
        if Path(p).exists():return ImageFont.truetype(p,size)
    return ImageFont.load_default()

def frontface(sprite,glow,model,frame):
    result=sprite.copy();fr=glow.crop((0,frame*64,64,(frame+1)*64));dst=result.load()
    for el in model['elements']:
        if el['faces']['north']['texture']!='#glow':continue
        x=round(el['from'][0]*4);y=round((16-el['to'][1])*4)
        if fr.getpixel((x,y))[3]:dst[x,y]=fr.getpixel((x,y))
    return result
def preview(states,path):
    frames=(0,4,8,12);labels=('frame 0','frame 4','frame 8','frame 12')
    width,height=880,650;board=Image.new('RGB',(width,height),(247,247,247));d=ImageDraw.Draw(board);font=ImageFont.load_default()
    for si,(name,sprite,glow,model) in enumerate(states):
      y0=8+si*320;d.text((8,y0),name,fill=(16,19,24),font=font)
      for row,bg in enumerate(((255,255,255),(22,28,36))):
        yy=y0+18+row*145;fg=(30,35,42) if row==0 else (238,242,247)
        d.text((8,yy),'white' if row==0 else 'dark',fill=fg,font=font)
        for col,f in enumerate(frames):
          x=50+col*205;d.text((x,yy),labels[col],fill=fg,font=font)
          rgba=Image.new('RGBA',(64,64),bg+(255,));rgba.alpha_composite(frontface(sprite,glow,model,f))
          board.paste(rgba.resize((128,128),Image.Resampling.NEAREST).convert('RGB'),(x,yy+16))
    board.save(path)

def main():
    if sha(ORD.read_bytes())!=ORD_SHA:raise RuntimeError('0.1.2 ordinary baseline SHA mismatch')
    if sha(BASE.read_bytes())!=BASE_SHA:raise RuntimeError('0.1.4 variant baseline SHA mismatch')
    if OUT.exists():
        manifest=OUT/'curved-tip-candidate.json'
        if not manifest.is_file():raise RuntimeError(f'Refusing to overwrite unrecognized candidate tree: {OUT}')
        prev=json.loads(manifest.read_text(encoding='utf-8'))
        if prev.get('baselineJarSha256')!=BASE_SHA:raise RuntimeError('Candidate tree baseline differs')
    bare=png((DRAFT/'bare-native64-tip-draft.png').read_bytes())
    mask_img=png((SRC/'replacement-transition-mask-draft.png').read_bytes())
    mask=mask_coords(mask_img)
    with zipfile.ZipFile(ORD) as oz:
        old32=png(oz.read(PREFIX+'textures/item/echo_pickaxe.png'))
    old64=old32.resize((64,64),Image.Resampling.NEAREST)
    assert bare.size==old64.size==(64,64)
    assert all(bare.getpixel((x,y))[3]==old64.getpixel((x,y))[3] for x,y in mask)
    for y,(lo,hi) in REQUIRED.items():
        assert all(bare.getpixel((x,y))[3]==255 for x in range(lo,hi+1)),(y,lo,hi)
    component_map=json.loads((ROOT/'artwork/source/approved-reference-oct03-64/native64-component-map.json').read_text(encoding='utf-8'))['components']
    for key in ('frequency','tuning','extension'):
        module={(x,y) for tier in component_map[key]['tiers'] for x,y,*_ in tier['texels']}
        if mask&module:raise RuntimeError(f'transition mask overlaps {key}: {sorted(mask&module)[:8]}')
    helper=load_helper(); texdir=OUT/PREFIX/'textures/item'; modeldir=OUT/PREFIX/'models/item'
    texdir.mkdir(parents=True,exist_ok=True);modeldir.mkdir(parents=True,exist_ok=True)
    records=[];ordinary_records=[];variants=[]
    with zipfile.ZipFile(ORD) as oz,zipfile.ZipFile(BASE) as bz:
        # Bare item remains the complete legacy 0.1.2 resource quartet.
        for rel in ('models/item/echo_pickaxe.json','textures/item/echo_pickaxe.png',
                    'textures/item/echo_pickaxe_glow.png','textures/item/echo_pickaxe_glow.png.mcmeta'):
            data=oz.read(PREFIX+rel);target=OUT/PREFIX/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
            rec={'path':PREFIX+rel,'sha256':sha(data),'bytes':len(data)};ordinary_records.append(rec);records.append(rec)
        base_glow=png((ROOT/'artwork/source/approved-reference-oct03-64/common64-glow.png').read_bytes())
        assert base_glow.size==(64,1024)
        tip_emit=set()
        for x,y in mask:
            r,g,b,a=bare.getpixel((x,y))
            if a and g>=100 and b>=110 and b>r*1.4 and max(g,b)>=120:tip_emit.add((x,y))
        expected={k for k in mask_coords(bare)}
        # Preserve all old alpha outside the replacement mask; identify the
        # finished plain texture's modeled opacity and its new cyan/crack emit.
        glow_frames=[]
        for f in range(16):
            factor=.82+.18*(.5+.5*math.sin(math.tau*f/16))
            frame=Image.new('RGBA',(64,64),(0,0,0,0));fp=frame.load()
            for x,y in tip_emit:
                r,g,b,a=bare.getpixel((x,y))
                if a:fp[x,y]=(round(r*factor),round(g*factor),round(b*factor),255)
            glow_frames.append(frame)
        bare_model=json.loads(oz.read(PREFIX+'models/item/echo_pickaxe.json').decode('utf-8'))
        # Bare geometry/resources stay byte-identical to 0.1.2. This record
        # describes the 64px res0 visual-only native layer for variant generation.
        preview_variants={}
        for index in range(1,32):
            item=f'echo_pickaxe_v{index:03d}'
            baseline_sprite=asset(bz,f'textures/item/{item}.png')
            sprite=baseline_sprite.copy();dst=sprite.load()
            for x,y in mask:dst[x,y]=bare.getpixel((x,y))
            assert all(sprite.getpixel((x,y))==baseline_sprite.getpixel((x,y)) for y in range(64) for x in range(64) if (x,y) not in mask),item
            oldstrip=asset(bz,f'textures/item/{item}_glow.png')
            assert oldstrip.size==(64,1024),(item,oldstrip.size)
            strip=oldstrip.copy()
            for f,frame in enumerate(glow_frames):
                old_frame=strip.crop((0,64*f,64,64*(f+1)));op=old_frame.load();fp=frame.load()
                for x,y in mask:op[x,y]=fp[x,y]
                strip.paste(old_frame,(0,64*f))
            assert all(strip.getpixel((x,y+64*f))==oldstrip.getpixel((x,y+64*f))
                       for f in range(16) for y in range(64) for x in range(64) if (x,y) not in mask),item
            # Keep original frame/tick metadata outside this 3-resource change.
            lit=mask_coords(strip.crop((0,0,64,64)))
            assert all(mask_coords(strip.crop((0,64*f,64,64*(f+1))))==lit for f in range(16)),item
            old_model=json.loads(bz.read(PREFIX+f'models/item/{item}.json').decode('utf-8'))
            model,opaque,model_lit=helper.model_for_state(old_model,item,sprite,lit)
            helper.validate_model(sprite,model,model_lit,item)
            # Keep vanilla state dispatch from the exact baseline model.
            if 'overrides' in old_model:model['overrides']=copy.deepcopy(old_model['overrides'])
            resources={f'models/item/{item}.json':jbytes(model),
                       f'textures/item/{item}.png':png_bytes(sprite),
                       f'textures/item/{item}_glow.png':png_bytes(strip)}
            hashes={}
            for rel,data in resources.items():
                path=OUT/PREFIX/rel;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
                record={'path':PREFIX+rel,'sha256':sha(data),'bytes':len(data)};records.append(record)
                hashes[rel.rsplit('/',1)[-1]]=sha(data)
            variants.append({'index':index,'levels':helper.levels_for(index),'opaqueTexels':len(opaque),
              'emissiveTexels':len(model_lit),'sha256':hashes})
            if index in (24,31):preview_variants[index]=(sprite,strip,model)
    for index,(sprite,strip,model) in preview_variants.items():
        preview_variants[index]=(sprite,strip,model)
    preview([(f'res0 v{idx:03d}',*preview_variants[idx]) for idx in (24,31)],
      ROOT/'artwork/validation/v0.1.5/curved-tip-native-glow-frontface-white-dark.png')
    # Freeze the reviewed alpha-only underlay and its exact replacement mask.
    shutil.copyfile(SRC/'replacement-transition-mask-draft.png',SRC/'replacement-transition-mask-v0.1.5.png')
    shutil.copyfile(DRAFT/'bare-native64-tip-draft.png',SRC/'native64-res0-tip-underlay.png')
    for mask_name in ('tip-mask-v0.1.5.png','edit-mask-v0.1.5.png','shared-mask-v0.1.5.png'):
        shutil.copyfile(SRC/'replacement-transition-mask-v0.1.5.png',SRC/mask_name)
    connection_map={'schema':1,'status':'root-approved-frozen','baselineJarSha256':BASE_SHA,
      'ordinaryShapeJarSha256':ORD_SHA,
      'replacementMaskSha256':sha((SRC/'replacement-transition-mask-v0.1.5.png').read_bytes()),**CONNECTION,
      'nativeRGBAWithinMask':[[x,y,list(bare.getpixel((x,y)))] for x,y in sorted(mask,key=lambda p:(p[1],p[0]))],
      'alphaBoundary':'Within all 520 ROI texels, candidate alpha must exactly equal ordinary 0.1.2 alpha resized nearest-neighbor 2x.'}
    (SRC/'connection-map-v0.1.5.json').write_bytes(jbytes(connection_map))
    approved_map={'schema':1,'status':'root-approved-frozen','baselineJarSha256':BASE_SHA,
      'ordinaryShapeJarSha256':ORD_SHA,'native64TipUnderlay':'native64-res0-tip-underlay.png',
      'native64TipUnderlaySha256':sha((SRC/'native64-res0-tip-underlay.png').read_bytes()),
      'replacementMask':'replacement-transition-mask-v0.1.5.png','replacementMaskSha256':sha((SRC/'replacement-transition-mask-v0.1.5.png').read_bytes()),
      'replacementMaskTexels':len(mask),'replacementRegionInclusive':[REGION[0],REGION[1],REGION[2]-1,REGION[3]-1],
      'outline':'Inside the full 520-texel transition mask, alpha exactly equals the 0.1.2 ordinary alpha nearest-neighbor 2x. Every opaque pixel in the mask is repainted as native64 sculk material, including common64 overlap pixels.',
      'materialSourceContract':'All RGBA inside the 520-texel mask is authored for this tip. Colors are selected from the approved common64 dark cyan-black sculk palette, then laid as directional 1px facets and three restrained curved cyan fissure segments; no common64 overlap RGB block is copied through.',
      'legacySourceContract':'The 0.1.2 ordinary texture is read only for its alpha silhouette, then nearest-neighbor resized 2x. Its RGB values, luminance, and material classes are never read or used.',
      **CONNECTION,
      'requiredOpaqueRows':{str(y):[lo,hi] for y,(lo,hi) in REQUIRED.items()},
      'moduleOverlap':{k:0 for k in ('frequency','tuning','extension')},
      'opaqueTexels':len(mask_coords(bare)),'tipEmissiveTexels':len(tip_emit),
      'nativeRGBAWithinMask':[[x,y,list(bare.getpixel((x,y)))] for x,y in sorted(mask,key=lambda p:(p[1],p[0]))],
      'tipFramePulse':'.82 + .18 * (.5 + .5 * sin(2πf/16)); 16 frames × 3 ticks; fixed alpha'}
    (SRC/'tip-transition-map-v0.1.5.json').write_bytes(jbytes(approved_map))
    record={'schema':1,'version':'0.1.5-curved-tip-candidate','status':'root-approved-candidate',
      'baselineJar':'jaysay-echo-tools-0.1.4.jar','baselineJarSha256':BASE_SHA,
      'ordinaryJar':'jaysay-echo-tools-0.1.2.jar','ordinaryJarSha256':ORD_SHA,
      'candidateResourceCount':len(records),'ordinaryResourcesByteExact0.1.2':ordinary_records,
      'changedVariantResources':93,'resonancePositiveResources':'resolve byte-identically from 0.1.4 baseline',
      'maskPath':str((SRC/'replacement-transition-mask-v0.1.5.png').relative_to(ROOT)).replace('\\','/'),
      'maskSha256':sha((SRC/'replacement-transition-mask-v0.1.5.png').read_bytes()),'maskTexels':len(mask),
      'tipMaskPath':str((SRC/'tip-mask-v0.1.5.png').relative_to(ROOT)).replace('\\','/'),
      'editMaskPath':str((SRC/'edit-mask-v0.1.5.png').relative_to(ROOT)).replace('\\','/'),
      'sharedMaskPath':str((SRC/'shared-mask-v0.1.5.png').relative_to(ROOT)).replace('\\','/'),
      'connectionMapPath':str((SRC/'connection-map-v0.1.5.json').relative_to(ROOT)).replace('\\','/'),
      'replacementRegionInclusive':[REGION[0],REGION[1],REGION[2]-1,REGION[3]-1],
      'outlineRule':'Across the full 520-texel ROI, alpha equals the 0.1.2 ordinary texture alpha nearest-neighbor 2x.',
      'materialRule':'Every opaque ROI pixel, including common64 overlap, is repainted with native64 common64-derived cyan-black sculk facets and three short curved bright fissures; no common64 RGB block is copied through.',
      'legacySourceContract':{'ordinaryJarSha256':ORD_SHA,'readChannel':'alpha only','resize':'nearest-neighbor 2x','rgbRead':False,'luminanceRead':False,'materialClassification':False},
      'requiredOpaqueRows':{str(y):[lo,hi] for y,(lo,hi) in REQUIRED.items()},
      **CONNECTION,
      'requiredOpaquePass':True,'moduleOverlap':{k:0 for k in ('frequency','tuning','extension')},
      'glowRule':'Inside mask, fixed-alpha 16-frame native64 cyan/crack emission selected from final RGB and pulsed by .82 + .18*(.5 + .5*sin(2πf/16)); pixels outside mask are copied per-frame from same 0.1.4 index.',
      'newTipEmissiveTexels':len(tip_emit),'common64GlowSha256':sha((ROOT/'artwork/source/approved-reference-oct03-64/common64-glow.png').read_bytes()),
      'tipUnderlayPath':str((SRC/'native64-res0-tip-underlay.png').relative_to(ROOT)).replace('\\','/'),
      'tipTextureSha256':sha((DRAFT/'bare-native64-tip-draft.png').read_bytes()),'tipTextureMap':str((SRC/'tip-transition-map-v0.1.5.json').relative_to(ROOT)).replace('\\','/'),
      'frontfacePreview':'artwork/validation/v0.1.5/curved-tip-native-glow-frontface-white-dark.png',
      'resources':records,'variants':variants}
    (OUT/'curved-tip-candidate.json').write_bytes(jbytes(record))
    print(f'PASS isolated candidate: {len(records)} files (4 exact bare + {len(variants)}×3 res0); mask={len(mask)}, new tip emit={len(tip_emit)}; out={OUT}')
    print('PASS 64px model geometry/UV/glow mapping, required bridge spans, fixed frame alpha; candidate does not deploy.')

if __name__=='__main__':main()
