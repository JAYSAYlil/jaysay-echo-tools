from pathlib import Path
from PIL import Image
import hashlib, json, math, zipfile

ROOT=Path(__file__).resolve().parents[3]
ART=ROOT/'artwork/source/enhanced-components-v0.1.12'
VAL=ROOT/'artwork/validation/v0.1.12/enhanced-components'
OUT=VAL/'candidate'
BASELINE=ROOT/'jaysay-echo-tools-0.1.11.jar'
SRC=ROOT/'src/main/resources/assets/echopickaxe'
ANCHOR='296326965171A658F9CD40E0C9C42FB3ABF5B1094AF9EFB0005096061C1711F5'
JAR_SHA='3480E7F761201D62F7FFBF7417BFF57DBA1EE02B8A4225C43622285266CD6234'
COMPONENTS=('redResonance','purpleFrequency','tuningStar','greenExtension')
STATIC={'redResonance':['resonance1','resonance2'],'purpleFrequency':['split1','split2','split3'],'tuningStar':['tuning1'],'greenExtension':['extension1','extension2','extension3']}
REGION_BY_COMPONENT={'resonance':'redResonance','frequency':'purpleFrequency','tuning':'tuningStar','extension':'greenExtension'}

sha=lambda b:hashlib.sha256(b).hexdigest().upper()
def levels(i): return {'resonance':i//32,'frequency':(i%32)//8,'tuning':(i%8)//4,'extension':i%4}
def read_png(b):
 import io
 return Image.open(io.BytesIO(b)).convert('RGBA')
def png_bytes(im):
 import io
 b=io.BytesIO();im.save(b,format='PNG',optimize=False);return b.getvalue()
def resource(path): return 'assets/echopickaxe/'+path

def main():
 if sha(BASELINE.read_bytes())!=JAR_SHA: raise RuntimeError('baseline jar SHA mismatch')
 plain_path=SRC/'textures/item/echo_pickaxe.png'
 if sha(plain_path.read_bytes())!=ANCHOR: raise RuntimeError('ordinary anchor SHA mismatch')
 if OUT.exists() and any(OUT.iterdir()): raise RuntimeError('candidate already contains files; refusing overwrite')
 OUT.mkdir(parents=True,exist_ok=True)
 base=Image.open(ART/'ordinary0.png').convert('RGBA')
 base_alpha={(x,y) for y in range(64) for x in range(64) if base.getpixel((x,y))[3]}
 if len(base_alpha)!=768: raise RuntimeError(f'ordinary alpha expected 768, got {len(base_alpha)}')
 # Capture independent static diff masks once; composition only paints these exact coordinates.
 tier_imgs={n:Image.open(ART/f'{n}.png').convert('RGBA') for names in STATIC.values() for n in names}
 tier_masks={n:{(x,y) for y in range(64) for x in range(64) if tier_imgs[n].getpixel((x,y))!=base.getpixel((x,y))} for n in tier_imgs}
 all_module_masks={k:set().union(*(tier_masks[n] for n in names)) for k,names in STATIC.items()}
 # Cyan emissive veins follow ordinary deployed glow alpha, with module texels assigned only to their own groups.
 glow0=Image.open(SRC/'textures/item/echo_pickaxe_glow.png').convert('RGBA')
 cyan={(x,y) for y in range(64) for x in range(64) if glow0.getpixel((x,y))[3] and base.getpixel((x,y))[3] and all((x,y) not in m for m in all_module_masks.values())}
 if not cyan: raise RuntimeError('no ordinary cyan emissive texels')
 with zipfile.ZipFile(BASELINE) as z:
  base_glow_meta=z.read('assets/echopickaxe/textures/item/echo_pickaxe_glow.png.mcmeta')
  old_bases={}; old_glows={}; old_models={}; old_meta={}
  for i in range(96):
   stem='echo_pickaxe' if i==0 else f'echo_pickaxe_v{i:03d}'
   old_bases[i]=z.read(f'assets/echopickaxe/textures/item/{stem}.png')
   old_glows[i]=z.read(f'assets/echopickaxe/textures/item/{stem}_glow.png')
   old_models[i]=z.read(f'assets/echopickaxe/models/item/{stem}.json')
  # Index-0 candidate content comes from the accepted native64 source, while baselineSha256 pins the 0.1.11 JAR.
  old_meta[resource('textures/item/echo_pickaxe_glow.png.mcmeta')]=base_glow_meta
  meta={'animation':{'width':64,'height':64,'frametime':3,'interpolate':True,'frames':[{'index':i} for i in range(16)]}}
  meta_bytes=(json.dumps(meta,indent=2)+'\n').encode()
  variants={}; rows=[]; changed_files={}
  # baseline hashes use JAR entries for resource rows use the deployed 0.1.11 JAR, including ordinary index 0.
  def add_resource(i,kind,path,data,old_data):
   target=OUT/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
   old_hash=sha(old_data); new_hash=sha(data)
   rows.append({'index':i,'kind':kind,'path':path,'sha256':new_hash,'baselineSha256':old_hash,'changed':new_hash!=old_hash})
  for i in range(96):
   lv=levels(i); sprite=base.copy(); component_regions={n:[] for n in ('cyanVeins','redResonance','purpleFrequency','tuningStar','greenExtension')}
   stem='echo_pickaxe' if i==0 else f'echo_pickaxe_v{i:03d}'
   if i==0:
    # Index 0 is a byte-exact preservation row for the four already deployed ordinary resources.
    ordinary_base=plain_path.read_bytes()
    ordinary_glow=(SRC/'textures/item/echo_pickaxe_glow.png').read_bytes()
    ordinary_model=(SRC/'models/item/echo_pickaxe.json').read_bytes()
    ordinary_meta=(SRC/'textures/item/echo_pickaxe_glow.png.mcmeta').read_bytes()
    ordinary_lit={(x,y) for y in range(64) for x in range(64) if glow0.getpixel((x,y))[3]}
    component_regions['cyanVeins']=sorted([list(p) for p in ordinary_lit],key=lambda p:(p[1],p[0]))
    bp=resource('textures/item/echo_pickaxe.png');gp=resource('textures/item/echo_pickaxe_glow.png');mp=resource('models/item/echo_pickaxe.json');metap=resource('textures/item/echo_pickaxe_glow.png.mcmeta')
    add_resource(0,'base',bp,ordinary_base,old_bases[0]);add_resource(0,'glow',gp,ordinary_glow,old_glows[0]);add_resource(0,'model',mp,ordinary_model,old_models[0]);add_resource(0,'glowMetadata',metap,ordinary_meta,base_glow_meta)
    variants['0']={'base':bp,'glow':gp,'model':mp,'glowMetadata':metap,'glowRegions':component_regions}
    continue
   component_regions['cyanVeins']=sorted([list(p) for p in cyan],key=lambda p:(p[1],p[0]))
   active=[]
   for ckey,lname in [('resonance','redResonance'),('frequency','purpleFrequency'),('tuning','tuningStar'),('extension','greenExtension')]:
    level=lv[ckey]
    if level<=0: continue
    selected_name=STATIC[lname][level-1]; mask=tier_masks[selected_name]; tier=tier_imgs[selected_name]; active.append((lname,mask))
    component_regions[lname]=sorted([list(p) for p in mask],key=lambda p:(p[1],p[0]))
    sp=sprite.load();tp=tier.load()
    for x,y in mask: sp[x,y]=tp[x,y]
   if any(sprite.getpixel((x,y))[3]!=base.getpixel((x,y))[3] for y in range(64) for x in range(64)): raise RuntimeError(f'alpha changed at {i}')
   lit=set(cyan)
   for _,mask in active: lit|=mask
   # Animated RGB pulse is group-scoped, with a 4.5% amplitude cap and identical binary alpha on all 16 frames.
   strip=Image.new('RGBA',(64,1024),(0,0,0,0)); pulse_period=[1.0,.982,.955,.968,.993,1.032,1.045,1.018,.982,.955,.968,.993,1.032,1.045,1.018,1.0]
   group_points={'cyanVeins':set(cyan)}
   for name,mask in active: group_points[name]=mask
   groups=list(group_points)
   for f,factor in enumerate(pulse_period):
    frame=Image.new('RGBA',(64,64),(0,0,0,0));fp=frame.load();sp=sprite.load()
    for group,points in group_points.items():
     phase=(groups.index(group)%4)*math.pi/2
     local=1.0+0.045*math.sin(2*math.pi*f/16+phase)
     for x,y in points:
      r,g,b,_=sp[x,y]
      fp[x,y]=(max(0,min(255,round(r*local))),max(0,min(255,round(g*local))),max(0,min(255,round(b*local))),255)
    strip.paste(frame,(0,f*64))
   # Rebuild exact opaque-texel prism mesh from the common native64 alpha for every state.
   model=json.loads(old_models[i].decode('utf-8')); elems=[]
   for x,y in sorted(base_alpha,key=lambda p:(p[1],p[0])):
    uv=[(x+.5)/4,(y+.5)/4,(x+.5)/4,(y+.5)/4]
    faces={}
    for face in ('north','south'):
     obj={'uv':uv,'texture':'#glow' if (x,y) in lit else '#layer0'}
     if (x,y) in lit: obj['forge_data']={'block_light':15,'sky_light':15,'ambient_occlusion':False}
     faces[face]=obj
    neighbors={'west':(x-1,y),'east':(x+1,y),'up':(x,y-1),'down':(x,y+1)}
    for face,pt in neighbors.items():
     if pt not in base_alpha: faces[face]={'uv':uv,'texture':'#layer0'}
    elems.append({'from':[x*.25,16-(y+1)*.25,7.5],'to':[(x+1)*.25,16-y*.25,8.5],'shade':False,'faces':faces})
   model['elements']=elems; model_bytes=(json.dumps(model,ensure_ascii=False,indent=2)+'\n').encode()
   bp=resource(f'textures/item/{stem}.png');gp=resource(f'textures/item/{stem}_glow.png');mp=resource(f'models/item/{stem}.json')
   add_resource(i,'base',bp,png_bytes(sprite),old_bases[i]);add_resource(i,'glow',gp,png_bytes(strip),old_glows[i]);add_resource(i,'model',mp,model_bytes,old_models[i])
   variants[str(i)]={'base':bp,'glow':gp,'model':mp,'glowRegions':component_regions}
  manifest={'schemaVersion':1,'status':'frozen','baseline':{'jar':'jaysay-echo-tools-0.1.11.jar','sha256':JAR_SHA},'plainAnchor':{'path':'src/main/resources/assets/echopickaxe/textures/item/echo_pickaxe.png','sha256':ANCHOR,'index':0,'pixelExact':True},'fullmaxVisualTarget':{'path':'artwork/source/enhanced-components-v0.1.12/all_max.png','sha256':sha((ART/'all_max.png').read_bytes()),'index':95,'pixelExact':False},'candidateMode':'overlay','geometry':{'pixelUnit':0.25,'z':[7.5,8.5],'modelCoverage':'exact','preserveBaseModelOverrides':True,'ordinaryMeshMayDifferFrom32pxBaseline':True,'rebuildEveryStateOnOrdinaryNative64Alpha':True},'glowContract':{'frames':16,'frameSize':64,'fixedAlpha':True,'brightnessTolerance':0.06,'channelFloorTolerance':4,'frameTime':3,'interpolate':True},'resourceRows':rows,'variants':variants}
  (OUT/'candidate-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(f'candidate generated: {len(rows)} resources; {len(variants)} states; {len(base_alpha)} base pixels')

if __name__=='__main__':main()
