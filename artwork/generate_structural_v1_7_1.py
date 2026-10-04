from pathlib import Path
import json, math, shutil
from PIL import Image, ImageDraw

ROOT=Path('.')
BASE=ROOT/'artwork/source/emissive-v1.6.0/base_textures'
BASEMODELS=ROOT/'artwork/source/emissive-v1.6.0/base_models'
MASKMAN=json.loads((ROOT/'artwork/source/emissive-v1.6.0/manifest.json').read_text(encoding='utf-8-sig'))
OLD=ROOT/'artwork/source/structural-v1.7.1/base_glow_1.7.0'
OLDGEN=ROOT/'artwork/source/structural-v1.7.0/manifest.json'
V17=ROOT/'artwork/source/structural-v1.7.0/manifest.json'
SRC=ROOT/'artwork/source/structural-v1.7.1'
VAL=ROOT/'artwork/validation/v1.7.1'
OUT=VAL/'candidate'; TEX=OUT/'textures/item'; MOD=OUT/'models/item'
NAMES=list(MASKMAN['items'])
COUNT=32; SIZE=32
TICKS={n:3 for n in NAMES}; TICKS['tuning_crystal']=2

if not (SRC/'manifest.json').exists():
    SRC.mkdir(parents=True,exist_ok=True)
    (SRC/'base_models_1.7.0').mkdir(exist_ok=True); (SRC/'base_glow_1.7.0').mkdir(exist_ok=True)
    active=ROOT/'src/main/resources/assets/echopickaxe'
    for n in NAMES:
        for src,dst in [(active/'models/item'/f'{n}.json',SRC/'base_models_1.7.0'/f'{n}.json'),
                        (active/'textures/item'/f'{n}_glow.png',SRC/'base_glow_1.7.0'/f'{n}_glow.png'),
                        (active/'textures/item'/f'{n}_glow.png.mcmeta',SRC/'base_glow_1.7.0'/f'{n}_glow.png.mcmeta')]:
            if src.exists() and not dst.exists(): shutil.copy2(src,dst)

def luma(rgb): return .2126*rgb[0]+.7152*rgb[1]+.0722*rgb[2]
def dist(a,b):return math.hypot(a[0]-b[0],a[1]-b[1])
def nearest(mask,p): return min(mask,key=lambda q:dist(q,p))
def route(mask, pts): return [nearest(mask,p) for p in pts]
def brighten(rgb, amount=.10, tint=None):
    # Primary glint rises by 8–10% in the same hue; optional nearby reflection caps at 4%.
    if tint is None: return tuple(max(0,min(255,round(c*(1+amount)))) for c in rgb)
    return tuple(max(0,min(255,round(c*(1-amount)+t*amount))) for c,t in zip(rgb,tint))
def make_mask(name,base):
    mask={tuple(p) for p in MASKMAN['items'][name]['mask_coordinates']}
    if name.startswith('extension_crystal') or name.startswith('enhanced_extension_crystal'):
        mask={p for p in mask if 11<=p[0]<=21 and 11<=p[1]<=22 and abs(p[0]-16)+abs(p[1]-16)<=7}
    if name=='tuning_crystal':
        mask={p for p in mask if abs(p[0]-15.5)<=1 or abs(p[1]-15)<=1}
    mask={p for p in mask if base.getpixel(p)[3]==255}
    return mask

def animation(name,base,mask):
    frames=[]; keys=[]; pivots=[]
    if name=='echo_pickaxe':
        pivots=route(mask,[(4,27),(7,23),(10,20),(13,16),(15,12),(20,10),(25,12)])
        events=[('handle node',pivots[:4]),('head crack',pivots[4:6]),('echo motes',pivots[5:7])]
    elif name=='echo_upgrade_smithing_template':
        pts=route(mask,[(15,10),(16,12),(16,14),(15,16),(14,18),(16,20),(18,18),(18,15),(17,13)])
        events=[('engraved rune glint',pts)]
    elif name=='echo_crystal':
        pts=route(mask,[(14,14),(16,13),(18,15),(17,18),(14,17),(13,15)])
        events=[('facet reflection',pts)]
    elif name in ('resonance_crystal','enhanced_resonance_crystal'):
        pts=route(mask,[(15,15),(16,15),(17,15),(14,14),(12,13),(19,15),(21,13)])
        events=[('double core beat',pts[:3]),('branch spark',pts[3:])]
    elif name.startswith('frequency_crystal') or name.startswith('enhanced_frequency_crystal'):
        pts=route(mask,[(16,20),(16,18),(15,16),(12,13),(16,13),(20,13),(16,10),(13,17),(19,17)])
        events=[('branch motes',pts)]
    elif name in ('extension_crystal','enhanced_extension_crystal','enhanced_extension_crystal_2'):
        tier=1 if name=='extension_crystal' else (2 if name=='enhanced_extension_crystal' else 3)
        target={1:[(15,16),(16,17),(16,16)],2:[(14,16),(15,17),(15,18)],3:[(17,16),(17,17),(17,18)]}[tier]
        pts=[p for p in target if p in mask]
        if len(pts)!=3: raise RuntimeError(f'{name} eye reflection anchors missing: {target}')
        events=[({1:'subtle horizontal/diagonal 1px reflection drift; no pupil redraw',2:'diagonal 1px reflection drift with short holds; no pupil redraw',3:'short central reflection lock then 1px vertical release; no pupil redraw'}[tier],pts)]
    elif name=='tuning_crystal':
        pts=route(mask,[(15,15),(15,12),(15,8),(15,5),(15,18),(15,23),(12,15),(8,15),(5,15),(18,15),(22,15),(24,15)])
        events=[('four fine-arm traveling glints',pts)]
    else: raise ValueError(name)
    for f in range(COUNT):
        im=Image.new('RGBA',(SIZE,SIZE),(0,0,0,0))
        for p in mask: im.putpixel(p,(*base.getpixel(p)[:3],255))
        active=[]
        if name=='echo_pickaxe':
            if f<12: active=[pivots[(f//3)%4]]
            elif 12<=f<18: active=[pivots[4+(f//3)%2]]
            elif 18<=f<24: active=[pivots[5+(f//3)%2],pivots[4+(f//3)%2]]
        elif name=='echo_upgrade_smithing_template': active=[events[0][1][(f//3)%len(events[0][1])]]
        elif name=='echo_crystal': active=[events[0][1][(f//4)%len(events[0][1])]]
        elif name=='resonance_crystal':
            if f in (2,3,8,9): active=[events[0][1][0 if f<6 else 2]]
            elif 12<=f<20: active=[events[1][1][(f//2-6)%len(events[1][1])]]
        elif name=='enhanced_resonance_crystal':
            if f in (3,4,10,11): active=[events[0][1][f%3]]
            elif 14<=f<22: active=[events[1][1][(f//2-7)%len(events[1][1])]]
        elif name=='frequency_crystal':
            active=[events[0][1][(f//3)%len(events[0][1])]]
        elif name=='enhanced_frequency_crystal':
            active=[events[0][1][(f//2)%4],events[0][1][4+((f//2+2)%4)]]
        elif name=='enhanced_frequency_crystal_2':
            active=[events[0][1][(f//2)%len(events[0][1])],events[0][1][(f//2+3)%len(events[0][1])],events[0][1][(f//2+6)%len(events[0][1])]]
        elif name=='extension_crystal':
            active=[events[0][1][0 if f<8 else (2 if f<16 else 1)]]
        elif name=='enhanced_extension_crystal':
            active=[events[0][1][0 if f<8 else (1 if f<16 else (2 if f<24 else 0))]]
        elif name=='enhanced_extension_crystal_2':
            active=[events[0][1][1 if f<12 else (2 if f<20 else 1)]]
        elif name=='tuning_crystal':
            q=(f//3)%3
            idxs=[(q+i*3)%len(events[0][1]) for i in range(4)]
            active=[events[0][1][i] for i in idxs]
        for p in set(active):
            rgb=base.getpixel(p)[:3]
            # Fixed source hue; highlight is local and capped at ~10% channel mix.
            im.putpixel(p,(*brighten(rgb,.10),255))
        frames.append(im)
    for f in range(COUNT):
        if f in (0,4,8,12,16,20,24,28):
            keys.append({'frame':f,'active_glint_coordinates':[list(p) for p in active_at(name,f,events,pivots)],'eye_motion':('reflection only; source pupil not redrawn' if 'extension_crystal' in name else None)})
    return frames,keys,events,pivots

def active_at(name,f,events,pivots):
    # Mirrors animation's small highlight schedule for auditable key coordinates.
    if name=='echo_pickaxe':
        if f<12:return [pivots[(f//3)%4]]
        if f<18:return [pivots[4+(f//3)%2]]
        if f<24:return [pivots[5+(f//3)%2],pivots[4+(f//3)%2]]
        return []
    pts=events[0][1]
    if name=='echo_upgrade_smithing_template':return [pts[(f//3)%len(pts)]]
    if name=='echo_crystal':return [pts[(f//4)%len(pts)]]
    if name=='resonance_crystal':return [events[0][1][0 if f<6 else 2]] if f in (2,3,8,9) else ( [events[1][1][(f//2-6)%len(events[1][1])]] if 12<=f<20 else [])
    if name=='enhanced_resonance_crystal':return [events[0][1][f%3]] if f in (3,4,10,11) else ([events[1][1][(f//2-7)%len(events[1][1])]] if 14<=f<22 else [])
    if name=='frequency_crystal':return [pts[(f//3)%len(pts)]]
    if name=='enhanced_frequency_crystal':return [pts[(f//2)%4],pts[4+((f//2+2)%4)]]
    if name=='enhanced_frequency_crystal_2':return [pts[(f//2)%len(pts)],pts[(f//2+3)%len(pts)],pts[(f//2+6)%len(pts)]]
    if name=='extension_crystal':return [pts[0 if f<8 else (2 if f<16 else 1)]]
    if name=='enhanced_extension_crystal':return [pts[0 if f<8 else (1 if f<16 else (2 if f<24 else 0))]]
    if name=='enhanced_extension_crystal_2':return [pts[1 if f<12 else (2 if f<20 else 1)]]
    if name=='tuning_crystal':return [pts[((f//3)%3+i*3)%len(pts)] for i in range(4)]
    return []

def build_model(name,mask):
    model=json.loads((BASEMODELS/f'{name}.json').read_text(encoding='utf-8-sig'))
    model.setdefault('textures',{})['glow']=f'echopickaxe:item/{name}_glow'
    seen=set()
    for el in model.get('elements',[]):
        face=el.get('faces',{}).get('north')
        if not face:continue
        u,v=face['uv'][:2]; p=(round((u-.25)*2),round((v-.25)*2))
        if p not in mask:continue
        seen.add(p)
        for side in ('north','south'):
            el['faces'][side]['texture']='#glow'
            el['faces'][side]['forge_data']={'block_light':15,'sky_light':15,'ambient_occlusion':False}
    if seen!=mask:raise RuntimeError(f'{name} missing model pixels {sorted(mask-seen)}')
    return model,len(seen)*2

def compose(base,glow):
    out=base.copy()
    for y in range(32):
      for x in range(32):
        if glow.getpixel((x,y))[3]:out.putpixel((x,y),glow.getpixel((x,y)))
    return out

def main():
    TEX.mkdir(parents=True,exist_ok=True);MOD.mkdir(parents=True,exist_ok=True);VAL.mkdir(parents=True,exist_ok=True)
    old_manifest=json.loads(OLDGEN.read_text(encoding='utf-8-sig'))
    result={'version':'1.7.1-candidate','input_base':'artwork/source/emissive-v1.6.0/base_textures','baseline_model':'artwork/source/emissive-v1.6.0/base_models','rgb_change_policy':'all inactive pixels exact source RGB; active glints source hue, max 10% hue mix +4% source lift; dark eye exceptions: none','items':{}}
    allframes={}; bases={}; masks={}
    for name in NAMES:
      base=Image.open(BASE/f'{name}.png').convert('RGBA'); bases[name]=base
      mask=make_mask(name,base); masks[name]=mask
      frames,keys,events,pivots=animation(name,base,mask);allframes[name]=frames
      strip=Image.new('RGBA',(32,32*COUNT),(0,0,0,0))
      for i,im in enumerate(frames):
        if set(im.getchannel('A').getdata())-({0,255}):raise ValueError(name+' nonbinary alpha')
        strip.alpha_composite(im,(0,32*i))
      strip.save(TEX/f'{name}_glow.png',optimize=True)
      meta={'animation':{'width':32,'height':32,'frametime':TICKS[name],'interpolate':False,'frames':list(range(COUNT))}}
      (TEX/f'{name}_glow.png.mcmeta').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
      model,faces=build_model(name,mask);(MOD/f'{name}.json').write_text(json.dumps(model,indent=2)+'\n',encoding='utf-8')
      dark=min(range(COUNT),key=lambda f:sum(luma(frames[f].getpixel(p)[:3]) for p in mask))
      light=max(range(COUNT),key=lambda f:sum(luma(frames[f].getpixel(p)[:3]) for p in mask))
      result['items'][name]={'mask_pixels':len(mask),'mask_coordinates':[list(p) for p in sorted(mask,key=lambda p:(p[1],p[0]))],'faces':faces,'frames':COUNT,'frametime_ticks':TICKS[name],'cycle_ticks':COUNT*TICKS[name],'interpolate':False,'darkest_frame':dark,'brightest_frame':light,'keyframes':keys,'actions':events,'moved_points_only':True}
    (SRC/'manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    # Per item masks and all-item composite animation, tick-sampled (96 ticks total).
    for n,m in masks.items():
      im=Image.new('RGBA',(32,32),(0,0,0,0))
      for p in m:im.putpixel(p,(255,255,255,255))
      im.resize((256,256),Image.Resampling.NEAREST).save(VAL/f'{n}-mask.png')
    gif=[]
    for tick in range(96):
      canvas=Image.new('RGB',(828,624),(46,51,59));d=ImageDraw.Draw(canvas)
      for i,n in enumerate(NAMES):
        f=(tick//TICKS[n])%COUNT;im=compose(bases[n],allframes[n][f]).resize((192,192),Image.Resampling.NEAREST)
        x=12+(i%4)*204;y=12+(i//4)*204;canvas.paste(im,(x,y),im);d.text((x,y-9),n,fill='white')
      gif.append(canvas)
    gif[0].save(VAL/'emissive-items-preview.gif',save_all=True,append_images=gif[1:],duration=50,loop=0,optimize=True,disposal=2)
    # Keyframe sheet, including eye glance, tuning contraction and item-specific events.
    keyimg=Image.new('RGB',(4*172+150,len(NAMES)*174),(42,47,55));dr=ImageDraw.Draw(keyimg)
    picks={'echo_pickaxe':[0,6,15,21],'echo_upgrade_smithing_template':[0,9,18,27],'echo_crystal':[0,8,16,24], 'resonance_crystal':[0,3,13,20], 'enhanced_resonance_crystal':[0,4,15,22], 'frequency_crystal':[0,9,18,27], 'enhanced_frequency_crystal':[0,6,15,24], 'enhanced_frequency_crystal_2':[0,9,18,27], 'extension_crystal':[0,8,16,24], 'enhanced_extension_crystal':[0,8,16,24], 'enhanced_extension_crystal_2':[0,12,20,28], 'tuning_crystal':[0,6,15,24]}
    for row,n in enumerate(NAMES):
      dr.text((8,row*174+4),n,fill='white')
      for col,f in enumerate(picks[n]):
        im=compose(bases[n],allframes[n][f]).resize((160,160),Image.Resampling.NEAREST);x=150+col*172;y=row*174+12
        keyimg.paste(im,(x,y),im);dr.text((x,y+161),f'f{f}',fill=(220,225,230))
    keyimg.save(VAL/'keyframes.png')
    # Original vs old/new extremes 4-panel comparison; old frame luma computed from old 1.7 glow strips.
    panel=192;gap=12;w=4*panel+5*gap;h=len(NAMES)*(panel+42)+gap
    compare=Image.new('RGB',(w,h),(42,47,55));d=ImageDraw.Draw(compare)
    for row,n in enumerate(NAMES):
      base=bases[n];mask=masks[n]
      oldpath=OLD/f'{n}_glow.png'; old=Image.open(oldpath).convert('RGBA'); oframes=[old.crop((0,y,32,y+32)) for y in range(0,old.height,32)]
      def score(im):return sum(luma(im.getpixel(p)[:3]) for p in mask)
      od=min(range(len(oframes)),key=lambda f:score(oframes[f])); nd=min(range(COUNT),key=lambda f:score(allframes[n][f]));nb=max(range(COUNT),key=lambda f:score(allframes[n][f]))
      cells=[base,compose(base,oframes[od]),compose(base,allframes[n][nd]),compose(base,allframes[n][nb])]
      labels=['original',f'1.7.0 darkest f{od}',f'1.7.1 darkest f{nd}',f'1.7.1 brightest f{nb}']
      yy=gap+row*(panel+42)
      for col,(im,label) in enumerate(zip(cells,labels)):
        xx=gap+col*(panel+gap);compare.paste(im.resize((panel,panel),Image.Resampling.NEAREST),(xx,yy));d.text((xx,yy+panel+2),label,fill='white')
    compare.save(VAL/'extreme-comparison.png')
    # Quantitative per-pixel original RGB retention audit.
    aud=[]
    for n in NAMES:
      b=bases[n];fr=allframes[n];bright_orig=[p for p in masks[n] if luma(b.getpixel(p)[:3])>=170]
      fmin=min(range(COUNT),key=lambda f:sum(luma(fr[f].getpixel(p)[:3]) for p in masks[n]))
      ratios=[luma(fr[fmin].getpixel(p)[:3])/max(1,luma(b.getpixel(p)[:3])) for p in bright_orig]
      aud.append({'item':n,'mask_pixels':len(masks[n]),'darkest_frame':fmin,'mean_mask_luma_ratio':round(sum(luma(fr[fmin].getpixel(p)[:3]) for p in masks[n])/max(1,sum(luma(b.getpixel(p)[:3]) for p in masks[n])),4),'bright_detail_min_ratio':round(min(ratios,default=1),4),'bright_detail_below_88pct':sum(r<.88 for r in ratios),'alpha_values':sorted(set(fr[fmin].getchannel('A').getdata()))})
    (VAL/'tone-audit.json').write_text(json.dumps(aud,indent=2)+'\n',encoding='utf-8')
    print('candidate generated',len(NAMES),'items; comparison:',VAL/'extreme-comparison.png')
    print(json.dumps(aud,indent=2))

if __name__=='__main__':main()



