from __future__ import annotations
import io, json, zipfile, math
from pathlib import Path
from PIL import Image, ImageDraw
ROOT = Path(__file__).resolve().parents[3]
JAR = ROOT / 'jaysay-echo-tools-1.6.0.jar'
OUT = ROOT / 'artwork/validation/v1.7.4'
CAND = OUT / 'candidate'
SRC = ROOT / 'artwork/source/structural-v1.7.4'
ASSET = 'assets/echopickaxe/'
ITEMS = ['echo_crystal','echo_pickaxe','echo_upgrade_smithing_template','enhanced_extension_crystal_2','enhanced_extension_crystal','enhanced_frequency_crystal_2','enhanced_frequency_crystal','enhanced_resonance_crystal','extension_crystal','frequency_crystal','resonance_crystal','tuning_crystal']
EXT_EYE = [(x,y) for x in (16,17,18) for y in range(14,18)]
TUNE_PATH = [(14,11),(14,10),(14,20),(14,21),(10,15),(9,15),(18,15),(19,15)]

def imread(raw): return Image.open(io.BytesIO(raw)).convert('RGBA')
def rawpng(im):
    b=io.BytesIO(); im.save(b,format='PNG',optimize=False); return b.getvalue()
def load_strip(raw):
    im=imread(raw)
    return [im.crop((0,y,32,y+32)) for y in range(0,im.height,32)]
def strip_bytes(frames):
    out=Image.new('RGBA',(32,32*len(frames)))
    for i,im in enumerate(frames): out.paste(im,(0,32*i))
    return rawpng(out)
def coord(face):
    uv=face.get('uv')
    if not uv: return None
    return (round((uv[0]-.25)*2), round((uv[1]-.25)*2))
def update_model(raw, glow_coords):
    d=json.loads(raw)
    d['textures']['glow']='echopickaxe:item/'+d['textures']['layer0'].split(':')[-1].split('/')[-1]+'_glow'
    d['textures']['particle']=d['textures'].get('particle','#layer0')
    for element in d['elements']:
        for side in ('north','south'):
            face=element.get('faces',{}).get(side)
            if face is None: continue
            xy=coord(face)
            if xy in glow_coords:
                face['texture']='#glow'
                face['forge_data']={'block_light':15,'sky_light':15,'ambient_occlusion':False}
            else:
                face['texture']='#layer0'
                face.pop('forge_data',None)
    return (json.dumps(d,indent=2,ensure_ascii=False)+'\n').encode()

def rgb_scale(rgb, mul): return tuple(max(0,min(255,round(v*mul))) for v in rgb)

def write_json(path,obj): path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

def make_ext(oldframes, base):
    path=set(EXT_EYE)
    oldmask=set()
    for f in oldframes:
        for y in range(32):
            for x in range(32):
                if f.getpixel((x,y))[3]: oldmask.add((x,y))
    glowframes=[]
    # Reproduce the 1.6.0 four-tick interpolated shimmer at every game tick, then
    # overlay the discrete eye position. This avoids interpolating/ghosting the pupil.
    for tick in range(192):
        old_index=(tick//4)%16
        next_index=(old_index+1)%16
        weight=(tick%4)/4
        cur,nxt=oldframes[old_index],oldframes[next_index]
        f=Image.new('RGBA',(32,32))
        for y in range(32):
            for x in range(32):
                a=cur.getpixel((x,y))[3]
                p=cur.getpixel((x,y)); q=nxt.getpixel((x,y))
                # Vanilla animation interpolation linearly blends channels and truncates to int.
                f.putpixel((x,y),tuple(int((1-weight)*p[c]+weight*q[c]) for c in range(3))+(a,))
        gaze_tick=tick%96
        pupil_x=16 if 27<=gaze_tick<39 else 18 if 69<=gaze_tick<81 else 17
        # Maintain the old shimmer outside the pupil path; make the whole 12-pixel
        # eye path opaque and restore its green backing from fixed same-row donors.
        for x,y in path:
            r,g,b,a=base.getpixel((x,y))
            f.putpixel((x,y),(r,g,b,255))
        refcols={14:18,15:18,16:18,17:16}
        for y in range(14,18):
            # Erase old pupil from its source column with the specified same-row crystal color.
            fill=base.getpixel((refcols[y],y))
            f.putpixel((17,y),fill)
            # Place the original 1x4 pupil at the moving x coordinate.
            pupil=base.getpixel((17,y))
            f.putpixel((pupil_x,y),pupil)
        glowframes.append(f)
    return glowframes, oldmask|path

def make_tuning(oldframes, base):
    # Keep every original frame and emissive coordinate. The additional tips are softly brightened in a
    # four-stage inward-to-tip ripple; no other RGB/alpha is touched.
    path=set(TUNE_PATH)
    frames=[]
    tip_groups=[[(14,11),(14,10)],[(14,20),(14,21)],[(10,15),(9,15)],[(18,15),(19,15)]]
    # 16-frame cycle aligns one-to-one with the 1.6.0 shimmer. Four arm waves take turns across the cycle.
    for i,old in enumerate(oldframes):
        f=old.copy()
        for j,group in enumerate(tip_groups):
            phase=(i-j*4)%16
            if phase in (2,3,4,5,6,7):
                # inner point first, outer point follows; short hold, then return to source color.
                active=[0] if phase in (2,3,7) else [0,1]
                for k in active:
                    x,y=group[k]
                    r,g,b,a=old.getpixel((x,y))
                    if a==0: r,g,b,a=base.getpixel((x,y))
                    # Subtle same-hue 12% glint relative to the original shimmer at this phase.
                    f.putpixel((x,y),(*rgb_scale((r,g,b),1.12),255))
            for x,y in group:
                if f.getpixel((x,y))[3]==0:
                    r,g,b,_=base.getpixel((x,y)); f.putpixel((x,y),(r,g,b,255))
        frames.append(f)
    return frames

def composite_item(base, glow):
    out=base.copy()
    for y in range(32):
        for x in range(32):
            p=glow.getpixel((x,y))
            if p[3]: out.putpixel((x,y),p)
    return out

def make_sheet(frames, path, base, cols=8, scale=12, bg=(57,62,72,255)):
    rows=math.ceil(len(frames)/cols); canvas=Image.new('RGBA',(cols*32*scale,rows*32*scale),bg)
    for i,im in enumerate(frames):
        x=(i%cols)*32*scale; y=(i//cols)*32*scale
        shown=composite_item(base,im)
        canvas.alpha_composite(shown.resize((32*scale,32*scale),Image.Resampling.NEAREST),(x,y))
    path.parent.mkdir(parents=True,exist_ok=True); canvas.convert('RGB').save(path)

def gif(frames,path,duration,base):
    bg=Image.new('RGBA',(32,32),(67,72,82,255))
    out=[]
    for im in frames:
        c=bg.copy(); c.alpha_composite(composite_item(base,im)); out.append(c.convert('P',palette=Image.Palette.ADAPTIVE))
    path.parent.mkdir(parents=True,exist_ok=True); out[0].save(path,save_all=True,append_images=out[1:],duration=duration,loop=0,disposal=2)

def interp_ticks(frames,ticks_per_frame):
    out=[]
    for i,cur in enumerate(frames):
        nxt=frames[(i+1)%len(frames)]
        for tick in range(ticks_per_frame):
            w=tick/ticks_per_frame
            f=Image.new('RGBA',(32,32))
            for y in range(32):
                for x in range(32):
                    p,q=cur.getpixel((x,y)),nxt.getpixel((x,y))
                    f.putpixel((x,y),tuple(int((1-w)*p[c]+w*q[c]) for c in range(3))+(p[3],))
            out.append(f)
    return out

with zipfile.ZipFile(JAR) as z:
    ext_base=imread(z.read(ASSET+'textures/item/extension_crystal.png'))
    tune_base=imread(z.read(ASSET+'textures/item/tuning_crystal.png'))
    ext_old=load_strip(z.read(ASSET+'textures/item/extension_crystal_glow.png'))
    tune_old=load_strip(z.read(ASSET+'textures/item/tuning_crystal_glow.png'))
    # Copy all 48 baseline resources exactly into candidate first.
    for name in ITEMS:
        for rel in (f'textures/item/{name}.png',f'textures/item/{name}_glow.png',f'textures/item/{name}_glow.png.mcmeta',f'models/item/{name}.json'):
            raw=z.read(ASSET+rel)
            dest=CAND/rel
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes(raw)
    extframes, extmask=make_ext(ext_old,ext_base)
    tuneframes=make_tuning(tune_old,tune_base)
    extmeta={'animation':{'width':32,'height':32,'frametime':1,'interpolate':False,'frames':list(range(192))}}
    tunemeta={'animation':{'width':32,'height':32,'frametime':6,'interpolate':True,'frames':list(range(16))}}
    (CAND/'textures/item/extension_crystal_glow.png').write_bytes(strip_bytes(extframes))
    write_json(CAND/'textures/item/extension_crystal_glow.png.mcmeta',extmeta)
    (CAND/'textures/item/tuning_crystal_glow.png').write_bytes(strip_bytes(tuneframes))
    write_json(CAND/'textures/item/tuning_crystal_glow.png.mcmeta',tunemeta)
    # Bind exactly the union glow mask on north/south faces only; all geometry/display retained from v1.6.0.
    ext_union=set()
    for f in extframes:
        for y in range(32):
            for x in range(32):
                if f.getpixel((x,y))[3]: ext_union.add((x,y))
    tune_union=set()
    for f in tuneframes:
        for y in range(32):
            for x in range(32):
                if f.getpixel((x,y))[3]: tune_union.add((x,y))
    for name,coords in [('extension_crystal',ext_union),('tuning_crystal',tune_union)]:
        p=CAND/f'models/item/{name}.json'
        with zipfile.ZipFile(JAR) as z: original=z.read(ASSET+f'models/item/{name}.json')
        p.write_bytes(update_model(original,coords))

# Explanatory source records and candidate previews.
eye_preview_indices=[0,26,27,38,39,68,69,80,81,95,96,122,123,134,135,164,165,176,177,191]
make_sheet([extframes[i] for i in eye_preview_indices],OUT/'extension-animation-1.7.4.png',ext_base,cols=5,scale=10)
make_sheet(tuneframes,OUT/'tuning-animation-1.7.4.png',tune_base,cols=4,scale=12)
gif(extframes,OUT/'extension-animation-1.7.4.gif',50,ext_base)
gif(interp_ticks(tuneframes,6),OUT/'tuning-animation-1.7.4.gif',50,tune_base)
# A coordinate diagram for exactly the proposed tuning additions.
zoom=Image.new('RGB',(32*20,32*20),(46,50,60)); draw=ImageDraw.Draw(zoom)
for y in range(32):
    for x in range(32):
        p=tune_base.getpixel((x,y))
        if p[3]: draw.rectangle((x*20,y*20,x*20+19,y*20+19),fill=p[:3])
for x,y in TUNE_PATH:
    draw.rectangle((x*20,y*20,x*20+19,y*20+19),outline=(255,80,55),width=2)
    draw.text((x*20+3,y*20+3),f'{x},{y}',fill=(255,255,90))
for x in range(32): draw.text((x*20+5,2),str(x),fill='white')
for y in range(32): draw.text((2,y*20+5),str(y),fill='white')
zoom.save(OUT/'tuning-glow-tip-coordinates-1.7.4.png')

# Manifest and prompt record.
manifest={'baseline':'jaysay-echo-tools-1.6.0.jar','candidate_only':True,'items':ITEMS,'byte_exact_baseline_items':[n for n in ITEMS if n not in ('extension_crystal','tuning_crystal')], 'all_base_textures_byte_exact':True,'extension':{'cycle_ticks':192,'frames':192,'frametime_ticks':1,'legacy_resample':'For each tick t, oldIndex=(t//4)%16, next=(oldIndex+1)%16, weight=(t%4)/4; RGB is the integer-truncated linear interpolation between those 1.6.0 frames, preserving current-frame alpha.','pupil_tick':'t mod 96','pupil_x':'16 when 27<=tick<39; 18 when 69<=tick<81; otherwise 17','pupil_y':[14,15,16,17],'pupil_rgba':'exact source x17 values','restoration_x':{'14':18,'15':18,'16':18,'17':16},'fixed_mask_union_pixels':len(ext_union),'interpolate':False},'tuning':{'cycle_ticks':96,'frames':16,'frametime_ticks':6,'original_glow_frames_preserved':True,'added_glow_coordinates':TUNE_PATH,'schedule':'Each arm ripples sequentially: inner point, both tips, inner-only return, then source RGB.','fixed_mask_union_pixels':len(tune_union),'interpolate':True},'tuning_coordinates':{'north':[[14,11],[14,10]],'south':[[14,20],[14,21]],'west':[[10,15],[9,15]],'east':[[18,15],[19,15]]}}
write_json(SRC/'manifest.json',manifest)
(SRC/'generation-notes.md').write_text('''# v1.7.4 视觉回退候选\n\n视觉基线严格取根目录 `jaysay-echo-tools-1.6.0.jar`。独立生成器从 JAR 按字节恢复全12项各自的 base PNG、glow PNG、mcmeta 和 item model，共48个候选文件。10项未改动资产及全部12张base PNG保持JAR原字节。仅 `extension_crystal`、`tuning_crystal` 的 glow/model/meta 发生差异。候选尚未部署。\n\n- 延展保留1.6.0原64tick glow shimmer的平滑RGB变化：按tick将16帧（4 ticks/frame、interpolate=true）线性预采样为192帧（1 tick/frame、interpolate=false），当前alpha不变。此举保留路径外的1.6颜色波动并避免瞳孔插值重影。原x17,y14..17的黑瞳以96tick慢周期在x16/17/18间停驻，不眨眼；固定alpha union包含12格眼部路径，RGB瞳色取原底图。中心补色按每行固定取自x18（y14-16）及x16（y17）。\n- 调谐保留1.6.0原16帧×6 ticks（96tick）并保留interpolate=true。依据原图像素坐标仅新增四臂端部8格：N(14,11)(14,10), S(14,20)(14,21), W(10,15)(9,15), E(18,15)(19,15)。四臂依次呈现内端→两端→内端→原状态的轻微同色反光；激活点以当帧原glow RGB（原本透明时用base RGB）提亮12%。\n- 两个候选model都从JAR原model重绑 north/south glow face，几何、UV、display保留；未新增元素/parent。\n- 预览GIF以50ms/tick合成完整底图与glow；PNG帧板是关键帧。四臂像素坐标为 `tuning-glow-tip-coordinates-1.7.4.png`。\n- 复现命令：在项目根目录运行 `python artwork/source/structural-v1.7.4/generate_visual_rollback.py`。\n''',encoding='utf-8')
print(json.dumps({'candidate':str(CAND),'files':sum(1 for p in CAND.rglob('*') if p.is_file()),'extension_union':len(ext_union),'tuning_union':len(tune_union),'tuning_new':TUNE_PATH,'gif_ext':str(OUT/'extension-animation-1.7.4.gif'),'gif_tune':str(OUT/'tuning-animation-1.7.4.gif')},ensure_ascii=False))
