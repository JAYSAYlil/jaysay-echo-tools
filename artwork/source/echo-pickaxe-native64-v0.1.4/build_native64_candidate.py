"""Generate the isolated 0.1.4 candidate from root-approved native64 artwork.

Reads only the SHA-pinned 0.1.3 baseline for legacy states, and writes only the
v0.1.4 candidate tree. It never deploys or edits game code/version metadata.
"""
from __future__ import annotations
import copy, hashlib, importlib.util, io, json, shutil, zipfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[3]
SOURCE=Path(__file__).resolve().parent
RECORD=ROOT/'artwork/validation/v0.1.4'
BASELINE=ROOT/'jaysay-echo-tools-0.1.3.jar'
BASELINE_SHA='3D0F7B94EDBD09776D9891986354952CF1615B32305866C63FEEB7ED71F9D80D'
ORDINARY_JAR=ROOT/'jaysay-echo-tools-0.1.2.jar'
ORDINARY_SHA='7312AE7B54F3DAD998815B7C7BD601B65DB1BED23A21CC7AA8448E40E082F495'
MAP=SOURCE/'native64-tip-map.json'
PLAIN=SOURCE/'ordinary-native64-approved.png'
MASK=RECORD/'artagentmask.png'
OUT=RECORD/'candidate'
PREFIX='assets/echopickaxe/'
GENERATOR=ROOT/'artwork/source/approved-reference-oct03-64/build_approved64_variants.py'


def sha(data:bytes)->str:return hashlib.sha256(data).hexdigest().upper()
def asset(z:zipfile.ZipFile,relative:str)->bytes:return z.read(PREFIX+relative)
def png_bytes(im:Image.Image)->bytes:
    stream=io.BytesIO(); im.save(stream,format='PNG',optimize=False); return stream.getvalue()
def load_helper():
    spec=importlib.util.spec_from_file_location('approved64_model_helpers',GENERATOR)
    if spec is None or spec.loader is None: raise RuntimeError(f'Cannot load geometry helpers: {GENERATOR}')
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
def image_bytes(data:bytes)->Image.Image:return Image.open(io.BytesIO(data)).convert('RGBA')
def mask_coords(im:Image.Image)->set[tuple[int,int]]:
    if im.size!=(64,64):raise ValueError(f'mask must be 64x64, got {im.size}')
    return {(x,y) for y in range(64) for x in range(64) if im.getpixel((x,y))[3]}
def frame(im:Image.Image,i:int,size:int=64)->Image.Image:return im.crop((0,i*size,size,(i+1)*size))
def paste_frame(strip:Image.Image,i:int,img:Image.Image)->None:strip.paste(img,(0,i*64))
def json_bytes(value)->bytes:return (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8')

def main():
    if sha(BASELINE.read_bytes())!=BASELINE_SHA:raise RuntimeError('0.1.3 baseline JAR SHA mismatch')
    if sha(ORDINARY_JAR.read_bytes())!=ORDINARY_SHA:raise RuntimeError('0.1.2 ordinary JAR SHA mismatch')
    # The approved renderer deterministically refreshes the source PNG, explicit
    # RGBA map, and root-review boards from the pinned original art.
    render_path=SOURCE/'render_native64_draft.py'
    spec=importlib.util.spec_from_file_location('native64_approved_renderer',render_path)
    if spec is None or spec.loader is None:raise RuntimeError('Cannot load native64 renderer')
    render=importlib.util.module_from_spec(spec);spec.loader.exec_module(render);render.main()
    mapping=json.loads(MAP.read_text(encoding='utf-8-sig'))
    if mapping.get('status')!='root-approved' or mapping.get('rootApproved') is not True:raise RuntimeError('Native64 map is not approved')
    plain_bytes=PLAIN.read_bytes()
    if sha(plain_bytes)!=mapping.get('nativeTextureSha256'):raise RuntimeError('Approved native64 texture SHA differs from map')
    plain=image_bytes(plain_bytes)
    if plain.size!=(64,64):raise RuntimeError('Approved native64 image must be 64x64')
    listed={(x,y):tuple(rgba) for x,y,rgba in mapping['explicitOpaqueRgbaTexels']}
    assert len(listed)==1196 and all(plain.getpixel(p)==rgba for p,rgba in listed.items())
    with zipfile.ZipFile(ORDINARY_JAR) as ordinary_jar:
        original=image_bytes(ordinary_jar.read(PREFIX+'textures/item/echo_pickaxe.png'))
    assert original.size==(32,32)
    old_nearest=original.resize((64,64),Image.Resampling.NEAREST)
    assert plain.getchannel('A').tobytes()==old_nearest.getchannel('A').tobytes()
    assert len(mask_coords(image_bytes(MASK.read_bytes())))==203
    mask_img=image_bytes(MASK.read_bytes()); mask=mask_coords(mask_img)
    module_map=json.loads((ROOT/'artwork/source/approved-reference-oct03-64/native64-component-map.json').read_text(encoding='utf-8'))
    for component in ('frequency','tuning','extension'):
        protected={(x,y) for tier in module_map['components'][component]['tiers'] for x,y,*_ in tier['texels']}
        if mask&protected:raise RuntimeError(f'tip mask overlaps {component}: {sorted(mask&protected)[:8]}')
    if OUT.parent.resolve()!=RECORD.resolve() or OUT.name!='candidate':
        raise RuntimeError(f'Candidate path escaped the versioned validation directory: {OUT.resolve()}')
    if OUT.exists():
        manifest_path=OUT/'native64-candidate.json'
        if not manifest_path.is_file():raise RuntimeError(f'Refusing to overwrite unrecognized candidate tree: {OUT.resolve()}')
        previous=json.loads(manifest_path.read_text(encoding='utf-8-sig'))
        if previous.get('baselineJarSha256')!=BASELINE_SHA or previous.get('status') not in (
                'isolated-candidate-root-review-pending','isolated-candidate-awaiting-root-review'):
            raise RuntimeError('Refusing to update candidate not generated from the pinned 0.1.3 baseline')
    model_dir=OUT/'assets/echopickaxe/models/item'; texture_dir=OUT/'assets/echopickaxe/textures/item'
    model_dir.mkdir(parents=True,exist_ok=True); texture_dir.mkdir(parents=True,exist_ok=True)
    helper=load_helper(); resource_records=[]
    with zipfile.ZipFile(BASELINE) as baseline:
        old_model=json.loads(asset(baseline,'models/item/echo_pickaxe.json').decode('utf-8'))
        meta=json.loads(asset(baseline,'textures/item/echo_pickaxe_glow.png.mcmeta').decode('utf-8'))
        meta['animation']['width']=64;meta['animation']['height']=64
        bare_old_glow=image_bytes(asset(baseline,'textures/item/echo_pickaxe_glow.png'))
        assert bare_old_glow.size==(32,512)
        base_glow=Image.new('RGBA',(64,1024),(0,0,0,0))
        for i in range(16):
            old_frame=frame(bare_old_glow,i,32).resize((64,64),Image.Resampling.NEAREST)
            native_frame=Image.new('RGBA',(64,64),(0,0,0,0)); dst=native_frame.load()
            for y in range(64):
                for x in range(64):
                    native=plain.getpixel((x,y)); old_plain=old_nearest.getpixel((x,y)); old_lit=old_frame.getpixel((x,y))
                    # Preserve the original alpha and animation exactly. Apply the
                    # old glow-minus-old-base color delta to refined native texels;
                    # unchanged source colors therefore retain their old glow RGB.
                    if old_lit[3]:
                        rgb=tuple(max(0,min(255,native[c]+old_lit[c]-old_plain[c])) for c in range(3))
                    else: rgb=old_lit[:3]
                    dst[x,y]=rgb+(old_lit[3],)
            paste_frame(base_glow,i,native_frame)
        base_lit=mask_coords(frame(base_glow,0))
        assert all(mask_coords(frame(base_glow,i))==base_lit for i in range(16))
        bare_model,_,bare_model_lit=helper.model_for_state(old_model,'echo_pickaxe',plain,base_lit)
        bare_model['overrides']=copy.deepcopy(old_model.get('overrides',[]))
        helper.validate_model(plain,bare_model,bare_model_lit,'echo_pickaxe')
        written={
          'models/item/echo_pickaxe.json':json_bytes(bare_model),
          'textures/item/echo_pickaxe.png':plain_bytes,
          'textures/item/echo_pickaxe_glow.png':png_bytes(base_glow),
          'textures/item/echo_pickaxe_glow.png.mcmeta':json_bytes(meta),
        }
        for rel,data in written.items():
            path=OUT/PREFIX/rel;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
            resource_records.append({'path':(PREFIX+rel),'bytes':len(data),'sha256':sha(data)})
        variants=[]
        # Formula: res*32 + frequency*8 + tuning*4 + extension. Index 0 is bare.
        for index in range(1,32):
            item=f'echo_pickaxe_v{index:03d}'
            old_sprite=image_bytes(asset(baseline,f'textures/item/{item}.png'))
            old_glow=image_bytes(asset(baseline,f'textures/item/{item}_glow.png'))
            assert old_sprite.size==(64,64) and old_glow.size==(64,1024)
            sprite=old_sprite.copy();dst=sprite.load()
            for x,y in mask:dst[x,y]=plain.getpixel((x,y))
            glow=old_glow.copy()
            for i in range(16):
                base_frame=frame(base_glow,i); old_frame=frame(old_glow,i); out_frame=old_frame.copy();outpx=out_frame.load()
                for x,y in mask:outpx[x,y]=base_frame.getpixel((x,y))
                paste_frame(glow,i,out_frame)
            lit=mask_coords(frame(glow,0))
            assert all(mask_coords(frame(glow,i))==lit for i in range(16)),(item,'glow alpha changes by frame')
            old_variant_model=json.loads(asset(baseline,f'models/item/{item}.json').decode('utf-8'))
            model,opaque,model_lit=helper.model_for_state(old_variant_model,item,sprite,lit)
            helper.validate_model(sprite,model,model_lit,item)
            paths={
              f'models/item/{item}.json':json_bytes(model),
              f'textures/item/{item}.png':png_bytes(sprite),
              f'textures/item/{item}_glow.png':png_bytes(glow),
            }
            hashes={}
            for rel,data in paths.items():
                path=OUT/PREFIX/rel;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
                hashes[rel.rsplit('/',1)[-1]]=sha(data)
                resource_records.append({'path':PREFIX+rel,'bytes':len(data),'sha256':sha(data)})
            resonance,freq,tune,ext=helper.levels_for(index)
            variants.append({'index':index,'levels':{'resonance':resonance,'frequency':freq,'tuning':tune,'extension':ext},
              'opaqueTexels':len(opaque),'emissiveTexels':len(model_lit),'sha256':hashes})
        original32=original
        res0= image_bytes((OUT/(PREFIX+'textures/item/echo_pickaxe_v031.png')).read_bytes())
        with zipfile.ZipFile(BASELINE) as old:
            res95=image_bytes(asset(old,'textures/item/echo_pickaxe_v095.png'))
        create_review_board(original32.resize((64,64),Image.Resampling.NEAREST),plain,res0,res95,RECORD/'native64-final-comparison-white.png')
        create_glow_review_board(bare_old_glow,base_glow,RECORD/'native64-glow-frames-white-dark.png')
        v031_sprite=image_bytes((OUT/(PREFIX+'textures/item/echo_pickaxe_v031.png')).read_bytes())
        v031_glow=image_bytes((OUT/(PREFIX+'textures/item/echo_pickaxe_v031_glow.png')).read_bytes())
        v031_model=json.loads((OUT/(PREFIX+'models/item/echo_pickaxe_v031.json')).read_text(encoding='utf-8'))
        create_frontface_glow_preview(plain,base_glow,bare_model,v031_sprite,v031_glow,v031_model,
          RECORD/'native64-frontface-glow-white-dark.png')
    manifest={'schema':1,'version':'0.1.4-candidate','status':'isolated-candidate-awaiting-root-review',
      'baselineJar':BASELINE.name,'baselineJarSha256':BASELINE_SHA,'ordinaryShapeJar':ORDINARY_JAR.name,
      'ordinaryShapePngSha256':mapping['ordinaryPngSha256'],'nativeTexture':str(PLAIN.relative_to(ROOT)).replace('\\','/'),
      'nativeTextureSha256':sha(plain_bytes),'nativeMap':str(MAP.relative_to(ROOT)).replace('\\','/'),
      'nativeMapSha256':sha(MAP.read_bytes()),'tipMask':str(MASK.relative_to(ROOT)).replace('\\','/'),
      'tipMaskSha256':sha(MASK.read_bytes()),'tipMaskTexels':len(mask),'baseTextureSize':[64,64],
      'baseGlowSize':[64,1024],'glowFrames':16,'frametime':3,'baseMetaOnlyWidthHeightChanged':True,
      'baseGlowMethod':'per-frame old 32px glow nearest2x alpha and color delta: clamp(native64 RGB + oldGlow64 RGB - oldPlain64 RGB); transparent glow RGB preserved',
      'res0VariantCount':len(variants),'resonancePositiveResourcesCopiedByteForByte':True,
      'allowedResourceCount':97,'resources':resource_records,'variants':variants}
    (OUT/'native64-candidate.json').write_bytes(json_bytes(manifest))
    print(f'PASS: isolated candidate written to {OUT} ({len(resource_records)} resource files)')
    print(f'PASS: base outline locked to ordinary 32px x2; 1196 explicit native RGBA texels; mask={len(mask)} texels')
    print(f'PASS: 31 res=0 variants patch mask only; untouched assets resolve from fixed 0.1.3 baseline')

def create_review_board(oldplain,plain,v031,v095,path):
    items=[('0.1.2 ordinary · 2×',oldplain),('new native64 ordinary',plain),('res0 FIII/TI/EIII',v031),('resII full max · unchanged',v095)]
    width,height=880,205; board=Image.new('RGB',(width,height),(255,255,255));draw=ImageDraw.Draw(board)
    font=ImageFont.load_default(); card_w=215; scale=2; shown=128
    for i,(label,sprite) in enumerate(items):
        x=8+i*card_w
        draw.text((x+4,12),label,fill=(15,18,22),font=font)
        rgba=Image.new('RGBA',(64,64),(255,255,255,255));rgba.alpha_composite(sprite)
        board.paste(rgba.resize((shown,shown),Image.Resampling.NEAREST).convert('RGB'),(x+4,38))
    board.save(path)

def create_glow_review_board(old_glow,new_glow,path):
    old0=frame(old_glow,0,32).resize((64,64),Image.Resampling.NEAREST)
    items=[('old 32px frame 0 ×2',old0),('new frame 0',frame(new_glow,0)),
           ('new frame 4',frame(new_glow,4)),('new frame 8',frame(new_glow,8))]
    width,height=880,430;board=Image.new('RGB',(width,height),(255,255,255));draw=ImageDraw.Draw(board);font=ImageFont.load_default()
    for row,bg in enumerate(((255,255,255),(22,28,36))):
        y0=10+row*210
        for i,(label,sprite) in enumerate(items):
            x=8+i*215;draw.text((x+4,y0),label,fill=(12,16,22) if row==0 else (235,240,245),font=font)
            shown=Image.new('RGBA',(64,64),bg+(255,));shown.alpha_composite(sprite)
            board.paste(shown.resize((128,128),Image.Resampling.NEAREST).convert('RGB'),(x+4,y0+18))
    board.save(path)

def frontface_frame(sprite,glow,model,frame_index):
    composed=sprite.copy(); glow_frame=frame(glow,frame_index)
    for element in model['elements']:
        if element['faces']['north']['texture']!='#glow':continue
        x=round(element['from'][0]*4);y=round((16-element['to'][1])*4)
        rgba=glow_frame.getpixel((x,y))
        if rgba[3]:composed.putpixel((x,y),rgba)
    return composed

def create_frontface_glow_preview(plain,base_glow,base_model,v031_sprite,v031_glow,v031_model,path):
    frames=(0,4,8,12); labels=('frame 0','frame 4','frame 8','frame 12')
    states=[('ordinary native64',plain,base_glow,base_model),
            ('res0 FIII/TI/EIII',v031_sprite,v031_glow,v031_model)]
    width,height=880,650;board=Image.new('RGB',(width,height),(255,255,255));draw=ImageDraw.Draw(board);font=ImageFont.load_default()
    for state_index,(state,sprite,glow,model) in enumerate(states):
        section_y=8+state_index*320;draw.text((8,section_y),state,fill=(16,19,24),font=font)
        for bg_row,bg in enumerate(((255,255,255),(22,28,36))):
            y0=section_y+18+bg_row*145
            draw.text((8,y0), 'white' if bg_row==0 else 'dark',
                      fill=(30,35,42) if bg_row==0 else (238,242,247),font=font)
            for col,frame_index in enumerate(frames):
                x=50+col*205
                draw.text((x,y0),labels[col],fill=(30,35,42) if bg_row==0 else (238,242,247),font=font)
                composited=Image.new('RGBA',(64,64),bg+(255,))
                composited.alpha_composite(frontface_frame(sprite,glow,model,frame_index))
                board.paste(composited.resize((128,128),Image.Resampling.NEAREST).convert('RGB'),(x,y0+16))
    board.save(path)

if __name__=='__main__':main()
