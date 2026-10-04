from pathlib import Path
import json, shutil
from PIL import Image, ImageDraw

ROOT=Path('.')
NAMES=['extension_crystal','enhanced_extension_crystal','enhanced_extension_crystal_2']
BASE=ROOT/'artwork/source/emissive-v1.6.0/base_textures'
BASE17=ROOT/'artwork/source/structural-v1.7.2/base_1.7.1'
OUT=ROOT/'artwork/validation/v1.7.2/candidate'
TEXT=OUT/'textures/item'; MODELS=OUT/'models/item'; VALID=ROOT/'artwork/validation/v1.7.2'
SIZE=32; FRAMES=32; TICKS=3

# Carefully verified source pupil: four dark pixels at x=17, y=14..17.
PUPIL_X=17
PUPIL_YS=[14,15,16,17]
PUPIL_RGB_EXPECTED=[(3,14,33),(1,20,35),(3,9,26),(3,11,27)]

def read_base():
    im=Image.open(BASE/'extension_crystal.png').convert('RGBA')
    actual=[im.getpixel((PUPIL_X,y))[:3] for y in PUPIL_YS]
    if actual!=PUPIL_RGB_EXPECTED: raise RuntimeError(f'original pupil changed: {actual}')
    return im

def model_for(mask):
    path=BASE17/'models/item/extension_crystal.json'
    model=json.loads(path.read_text(encoding='utf-8-sig'))
    model.setdefault('textures',{})['glow']='echopickaxe:item/extension_crystal_glow'
    found=set()
    for el in model.get('elements',[]):
        face=el.get('faces',{}).get('north')
        if not face: continue
        u,v=face['uv'][:2]; p=(round((u-.25)*2),round((v-.25)*2))
        if p not in mask: continue
        found.add(p)
        for side in ('north','south'):
            el['faces'][side]['texture']='#glow'
            el['faces'][side]['forge_data']={'block_light':15,'sky_light':15,'ambient_occlusion':False}
    if found!=mask: raise RuntimeError(f'model missing opacity pixel coordinates: {sorted(mask-found)}')
    return model,len(found)*2

def pupil_x_for_frame(f):
    # Centered for 24/32 frames; two gentle one-pixel excursions, held briefly.
    if 9<=f<=12:return 16
    if 23<=f<=26:return 18
    return 17

def make_frame(base,mask,f):
    xnew=pupil_x_for_frame(f)
    frame=Image.new('RGBA',(SIZE,SIZE),(0,0,0,0))
    for p in mask: frame.putpixel(p,(*base.getpixel(p)[:3],255))
    if xnew!=PUPIL_X:
        # Refill the vacated center column with a fixed same-row green/facet source,
        # avoiding the pale highlight at x18/y17 and white highlight at x16/y14.
        refill_sources={14:18,15:18,16:18,17:16}
        for y in PUPIL_YS:
            refill=base.getpixel((refill_sources[y],y))[:3]
            frame.putpixel((PUPIL_X,y),(*refill,255))
            pupil=base.getpixel((PUPIL_X,y))[:3]
            frame.putpixel((xnew,y),(*pupil,255))
    return frame

def base_manifest_mask():
    old=json.loads((ROOT/'artwork/source/structural-v1.7.1/manifest.json').read_text(encoding='utf-8-sig'))
    return {tuple(p) for p in old['items']['extension_crystal']['mask_coordinates']}

def main():
    TEXT.mkdir(parents=True,exist_ok=True); MODELS.mkdir(parents=True,exist_ok=True)
    # Keep the two enhanced tiers byte-for-byte identical to frozen 1.7.1.
    for name in NAMES[1:]:
        for suffix in ('.json',): shutil.copy2(BASE17/'models/item'/f'{name}{suffix}',MODELS/f'{name}{suffix}')
        for suffix in ('_glow.png','_glow.png.mcmeta'):
            shutil.copy2(BASE17/'textures/item'/f'{name}{suffix}',TEXT/f'{name}{suffix}')
    base=read_base()
    oldmask=base_manifest_mask()
    pupil_path={(x,y) for x in (16,17,18) for y in PUPIL_YS}
    mask=oldmask|pupil_path
    if any(base.getpixel(p)[3]!=255 for p in mask): raise RuntimeError('glow mask contains transparency')
    fs=[make_frame(base,mask,f) for f in range(FRAMES)]
    strip=Image.new('RGBA',(SIZE,SIZE*FRAMES),(0,0,0,0))
    for i,fr in enumerate(fs):
        if set(fr.getchannel('A').getdata())-({0,255}): raise RuntimeError('non-binary alpha')
        strip.alpha_composite(fr,(0,i*SIZE))
    strip.save(TEXT/'extension_crystal_glow.png',optimize=True)
    meta={'animation':{'width':32,'height':32,'frametime':TICKS,'interpolate':False,'frames':list(range(FRAMES))}}
    (TEXT/'extension_crystal_glow.png.mcmeta').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
    model,count=model_for(mask)
    (MODELS/'extension_crystal.json').write_text(json.dumps(model,indent=2)+'\n',encoding='utf-8')
    manifest={'version':'1.7.2-candidate','scope':'extension_crystal only; two enhanced extension assets are exact 1.7.1 copies','source_png':'artwork/source/emissive-v1.6.0/base_textures/extension_crystal.png','base_snapshot':'artwork/source/structural-v1.7.2/base_1.7.1','original_pupil':{'x':17,'y':[14,15,16,17],'rgb':[list(c) for c in PUPIL_RGB_EXPECTED]},'motion':{'frames':32,'frametime_ticks':3,'cycle_ticks':96,'center_x':17,'left_x':16,'right_x':18,'center_frames':24,'left_frames':[9,10,11,12],'right_frames':[23,24,25,26],'pupil_height':4,'pupil_width':1,'interpolate':False,'blink':False,'iris_redrawn':False,'new_highlights':False,'vacated_center_fill':'fixed per-row source colors independent of gaze: y14=x18, y15=x18, y16=x18, y17=x16; avoids extending pale highlights'},'mask_pixels':len(mask),'mask_coordinates':[list(p) for p in sorted(mask,key=lambda p:(p[1],p[0]))],'model_faces':count,'unchanged_items':{n:'candidate files copied byte-for-byte from 1.7.1 snapshot' for n in NAMES[1:]}}
    (ROOT/'artwork/source/structural-v1.7.2/manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    # A small, labeled center/left/right triptych.
    trip=Image.new('RGB',(3*320,370),(40,45,54)); d=ImageDraw.Draw(trip)
    sample=[('left',10),('center',0),('right',24)]
    for i,(label,f) in enumerate(sample):
        im=Image.open(BASE/'extension_crystal.png').convert('RGBA')
        fr=fs[f]
        for y in range(32):
          for x in range(32):
            if fr.getpixel((x,y))[3]:im.putpixel((x,y),fr.getpixel((x,y)))
        crop=im.crop((10,10,23,23)).resize((320,320),Image.Resampling.NEAREST)
        trip.paste(crop,(i*320,24)); d.text((i*320,4),f'{label} pupil x={pupil_x_for_frame(f)} (frame {f})',fill='white')
    trip.save(VALID/'pupil-left-center-right.png')
    # Full three-item GIF; updated basic tier, frozen 1.7.1 upper tiers.
    gif=[]
    for f in range(FRAMES):
        canvas=Image.new('RGB',(600,600),(40,45,54));d=ImageDraw.Draw(canvas)
        for i,name in enumerate(NAMES):
            if name=='extension_crystal':
                im=Image.open(BASE/'extension_crystal.png').convert('RGBA'); fr=fs[f]
                for y in range(32):
                  for x in range(32):
                    if fr.getpixel((x,y))[3]: im.putpixel((x,y),fr.getpixel((x,y)))
            else: im=Image.open(BASE/f'{name}.png').convert('RGBA')
            im=im.resize((256,256),Image.Resampling.NEAREST); x=172;y=8+i*196
            canvas.paste(im,(x,y),im); d.text((8,y+100),name,fill='white')
        gif.append(canvas)
    gif[0].save(VALID/'extension-pupil-motion.gif',save_all=True,append_images=gif[1:],duration=150,loop=0,optimize=True,disposal=2)
    print(f'candidate extension only: pupil x=16/17/18, mask={len(mask)} pixels, {count} faces')

if __name__=='__main__':main()
