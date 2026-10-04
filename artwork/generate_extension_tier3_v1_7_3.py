from pathlib import Path
import json
from PIL import Image,ImageDraw

ROOT=Path('.')
NAME='enhanced_extension_crystal_2'
SOURCE=ROOT/'artwork/source/structural-v1.7.3'
BASE17=SOURCE/'base_1.7.2'
OUT=ROOT/'artwork/validation/v1.7.3/candidate'
TEX=OUT/'textures/item'; MODELS=OUT/'models/item'; VALID=ROOT/'artwork/validation/v1.7.3'
SIZE=32
GLOW_GROUPS=[[(12,16),(13,15)],[(18,15),(19,16)],[(18,17),(18,18)],[(13,17),(13,18)]]
GLOW_PIXELS=[p for group in GLOW_GROUPS for p in group]
FRAME_COUNT=16; FRAME_TICKS=6

def luminance(rgb):return .2126*rgb[0]+.7152*rgb[1]+.0722*rgb[2]
def brighten_same_hue(rgb,factor=1.08):return tuple(min(255,round(c*factor)) for c in rgb)

def source_base():
    # Fully reproduce the approved source import: threshold source alpha to find the tight
    # object bounds, nearest resize to 18x28 at preserved aspect, center on transparent 32px.
    original=Image.open(SOURCE/f'{NAME}-imagegen.png').convert('RGBA')
    source_alpha=original.getchannel('A').point(lambda v:255 if v>=128 else 0)
    bbox=source_alpha.getbbox()
    if bbox is None: raise RuntimeError('generated source has no opaque pixels')
    crop=original.crop(bbox)
    out_h=28;out_w=round(crop.width*out_h/crop.height)
    scaled=crop.resize((out_w,out_h),Image.Resampling.NEAREST)
    scaled.putalpha(scaled.getchannel('A').point(lambda v:255 if v>=128 else 0))
    im=Image.new('RGBA',(32,32),(0,0,0,0))
    offset=((32-out_w)//2,2)
    im.alpha_composite(scaled,offset)
    im.putalpha(im.getchannel('A').point(lambda v:255 if v>=128 else 0))
    p=TEX/f'{NAME}.png';im.save(p,optimize=False)
    if im.size!=(32,32):raise RuntimeError('candidate base must be 32x32')
    if set(im.getchannel('A').getdata())-{0,255}:raise RuntimeError('base alpha is not binary')
    opaque={(x,y) for y in range(32) for x in range(32) if im.getpixel((x,y))[3]==255}
    for q in GLOW_PIXELS:
        if q not in opaque:raise RuntimeError(f'glow point is transparent: {q}')
    if len(GLOW_PIXELS)*2>=len(opaque):raise RuntimeError('glow selection should be less than half the opaque pixels')
    return im,opaque

def frames(base):
    mask=set(GLOW_PIXELS);out=[]
    # Four ring locations in a slow, quiet, same-hue reflection orbit.
    route=[(12,16),(13,15),(18,15),(19,16),(18,17),(18,18),(17,19),(13,18)]
    for f in range(FRAME_COUNT):
        im=Image.new('RGBA',(32,32),(0,0,0,0))
        for p in mask:im.putpixel(p,(*base.getpixel(p)[:3],255))
        group=(f//4)%len(GLOW_GROUPS)
        active=GLOW_GROUPS[group]
        primary=active[(f//2)%2];secondary=active[1-(f//2)%2]
        im.putpixel(primary,(*brighten_same_hue(base.getpixel(primary)[:3],1.12),255))
        im.putpixel(secondary,(*brighten_same_hue(base.getpixel(secondary)[:3],1.04),255))
        out.append(im)
    return mask,out,route

def pixel_uv(x,y):
    uvx=x/2+.25;uvy=y/2+.25
    return [uvx,uvy,uvx,uvy]
def build_model(base,opaque,mask):
    old=json.loads((BASE17/'models/item'/f'{NAME}.json').read_text(encoding='utf-8-sig'))
    display=old.get('display',{})
    elems=[]
    for x,y in sorted(opaque,key=lambda p:(p[1],p[0])):
        u,v=x/2+.25,y/2+.25
        face_tex='#glow' if (x,y) in mask else '#layer0'
        faces={}
        for side in ('north','south'):
            d={'texture':face_tex,'uv':[u,v,u,v]}
            if (x,y) in mask:d['forge_data']={'block_light':15,'sky_light':15,'ambient_occlusion':False}
            faces[side]=d
        # Keep side walls only on the silhouette boundary; sides always use the base texture.
        if x==0 or base.getpixel((x-1,y))[3]==0:faces['west']={'texture':'#layer0','uv':[u,v,u,v]}
        if x==31 or base.getpixel((x+1,y))[3]==0:faces['east']={'texture':'#layer0','uv':[u,v,u,v]}
        if y==0 or base.getpixel((x,y-1))[3]==0:faces['up']={'texture':'#layer0','uv':[u,v,u,v]}
        if y==31 or base.getpixel((x,y+1))[3]==0:faces['down']={'texture':'#layer0','uv':[u,v,u,v]}
        elems.append({'from':[x/2,16-(y+1)/2,7.5],'to':[(x+1)/2,16-y/2,8.5],'faces':faces,'shade':False})
    return {'gui_light':'front','display':display,'textures':{'layer0':f'echopickaxe:item/{NAME}','glow':f'echopickaxe:item/{NAME}_glow'},'ambientocclusion':False,'elements':elems}

def composite(base,glow):
    im=base.copy()
    for y in range(32):
      for x in range(32):
       if glow.getpixel((x,y))[3]:im.putpixel((x,y),glow.getpixel((x,y)))
    return im

def main():
    TEX.mkdir(parents=True,exist_ok=True);MODELS.mkdir(parents=True,exist_ok=True);VALID.mkdir(parents=True,exist_ok=True)
    base,opaque=source_base();mask,fs,route=frames(base)
    strip=Image.new('RGBA',(32,32*FRAME_COUNT),(0,0,0,0))
    for i,fr in enumerate(fs):
        assert set(fr.getchannel('A').getdata())<={0,255}
        strip.alpha_composite(fr,(0,32*i))
    strip.save(TEX/f'{NAME}_glow.png',optimize=True)
    meta={'animation':{'width':32,'height':32,'frametime':FRAME_TICKS,'interpolate':False,'frames':list(range(FRAME_COUNT))}}
    (TEX/f'{NAME}_glow.png.mcmeta').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
    model=build_model(base,opaque,mask)
    (MODELS/f'{NAME}.json').write_text(json.dumps(model,indent=2)+'\n',encoding='utf-8')
    # Low/peak frame examples and one-item cycle preview.
    labels=[('base, no glow',None),('reflection peak 1',0),('reflection peak 2',4),('reflection peak 3',8),('reflection peak 4',12)]
    sheet=Image.new('RGB',(5*224,275),(42,47,55));d=ImageDraw.Draw(sheet)
    for i,(label,f) in enumerate(labels):
        im=(base.copy() if f is None else composite(base,fs[f])).resize((192,192),Image.Resampling.NEAREST);x=i*224+16;y=20
        sheet.paste(im,(x,y),im);d.text((x,y+198),label,fill='white')
    sheet.save(VALID/'glow-frames.png')
    gif=[]
    for fr in fs:
        rgba=composite(base,fr).resize((384,384),Image.Resampling.NEAREST); im=Image.new('RGB',(384,384),(42,47,55)); im.paste(rgba,(0,0),rgba.getchannel('A'));gif.append(im)
    gif[0].save(VALID/'enhanced-extension-crystal-2-cycle.gif',save_all=True,append_images=gif[1:],duration=300,loop=0,optimize=True,disposal=2)
    # Compare frozen old icon with new at 32px nearest and both at 16px nearest.
    old=Image.open(BASE17/'textures/item'/f'{NAME}.png').convert('RGBA')
    compare=Image.new('RGB',(4*250,300),(42,47,55));d=ImageDraw.Draw(compare)
    for i,(label,im) in enumerate([('old v1.7.2 32px',old),('new v1.7.3 32px',base),('old v1.7.2 16px',old.resize((16,16),Image.Resampling.NEAREST)),('new v1.7.3 16px',base.resize((16,16),Image.Resampling.NEAREST))]):
        disp=im.resize((208,208),Image.Resampling.NEAREST);x=i*250+21;y=25;compare.paste(disp,(x,y),disp);d.text((x,y+213),label,fill='white')
    compare.save(VALID/'old-new-32-16.png')
    manifest={'version':'1.7.3-candidate','target':NAME,'base_size':[32,32],'base_alpha_values':[0,255],'opaque_pixels':len(opaque),'opaque_bbox':list(base.getchannel('A').getbbox()),'transparent_margin_pixels':{'top':2,'bottom':2,'left':7,'right':7},'glow_pixels':len(mask),'glow_coordinates':[list(p) for p in sorted(mask,key=lambda p:(p[1],p[0]))],'glow_groups':[[list(p) for p in g] for g in GLOW_GROUPS],'glow_fraction':round(len(mask)/len(opaque),4),'glow_method':'same-hue source RGB; moving 2-pixel ring reflection: primary +12%, adjacent companion +4%; no darkening','frames':FRAME_COUNT,'frametime_ticks':FRAME_TICKS,'cycle_ticks':FRAME_COUNT*FRAME_TICKS,'cycle_seconds':FRAME_COUNT*FRAME_TICKS/20,'interpolate':False,'geometry':'one 0.5x0.5 pixel box per opaque pixel; from=[x/2,16-(y+1)/2,7.5], to=[(x+1)/2,16-y/2,8.5]; center UV=[x/2+.25,y/2+.25] on every face; north/south all pixels; only silhouette boundary side faces layer0; selected north/south glow pairs fullbright 15/15 AO false','display_from':'artwork/source/structural-v1.7.3/base_1.7.2/models/item/enhanced_extension_crystal_2.json','other_items':'unchanged; only this target is included in candidate'}
    (SOURCE/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'generated candidate: opaque={len(opaque)}, glow={len(mask)}, elements={len(model["elements"])}; bbox={base.getchannel("A").getbbox()}')

if __name__=='__main__':main()

