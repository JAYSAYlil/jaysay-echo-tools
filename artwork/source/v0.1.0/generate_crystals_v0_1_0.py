from __future__ import annotations
import json, math
from pathlib import Path
from PIL import Image, ImageDraw
ROOT=Path(__file__).resolve().parents[3]
SRC=ROOT/'artwork/source/v0.1.0'
CAND=ROOT/'artwork/validation/v0.1.0/crystals/candidate'
PRE=ROOT/'artwork/validation/v0.1.0/crystals'
ASSETS=ROOT/'src/main/resources/assets/echopickaxe'
RING=[(15,11),(14,12),(12,13),(12,14),(13,15),(13,16),(14,18),(15,19),(16,20),(17,19),(18,18),(19,17),(19,16),(18,15)]
CENTER=(14,15)
RAYS={
 'N':[(14,13),(14,12),(14,11)],
 'S':[(14,18),(14,19),(14,20)],
 'W':[(12,15),(11,15),(10,15)],
 'E':[(16,15),(17,15),(18,15)],
}
TUNE_MASK={CENTER}|{p for line in RAYS.values() for p in line}
ITEMS=['tuning_crystal','enhanced_extension_crystal_2']

def load(path): return Image.open(path).convert('RGBA')
def import_target_base(raw_path,dest):
 src=load(raw_path)
 hard=src.getchannel('A').point(lambda value:255 if value>=128 else 0)
 bbox=hard.getbbox(); crop=src.crop(bbox); height=28; width=round(crop.width*height/crop.height)
 scaled=crop.resize((width,height),Image.Resampling.NEAREST)
 canvas=Image.new('RGBA',(32,32),(0,0,0,0)); x0=(32-width)//2; y0=(32-height)//2
 for y in range(height):
  for x in range(width):
   r,g,b,a=scaled.getpixel((x,y)); canvas.putpixel((x0+x,y0+y),(r,g,b,255 if a>=128 else 0))
 dest.parent.mkdir(parents=True,exist_ok=True); canvas.save(dest,optimize=False)
 return {'raw_size':list(src.size),'bbox_alpha_ge128':list(bbox),'resized_nearest': [width,height],'offset':[x0,y0],'opaque_pixels':sum(a>0 for a in canvas.getchannel('A').getdata())}
def save_strip(frames,path):
 out=Image.new('RGBA',(32,32*len(frames)))
 for i,f in enumerate(frames): out.paste(f,(0,32*i))
 out.save(path,optimize=False)
def mult(rgb,factor): return tuple(max(0,min(255,round(c*factor))) for c in rgb)
def lerp(a,b,t): return tuple(round(a[k]*(1-t)+b[k]*t) for k in range(3))
def interp_frames(frames,per):
 out=[]
 for i,cur in enumerate(frames):
  nxt=frames[(i+1)%len(frames)]
  for k in range(per):
   t=k/per; f=Image.new('RGBA',(32,32))
   for y in range(32):
    for x in range(32):
     a=cur.getpixel((x,y)); b=nxt.getpixel((x,y))
     f.putpixel((x,y),(*lerp(a[:3],b[:3],t),a[3]))
   out.append(f)
 return out
def full_item(base,glow):
 f=base.copy()
 for y in range(32):
  for x in range(32):
   p=glow.getpixel((x,y))
   if p[3]: f.putpixel((x,y),p)
 return f
def write_meta(path,frame_count,ticks,interp):
 obj={'animation':{'width':32,'height':32,'frametime':ticks,'interpolate':interp,'frames':list(range(frame_count))}}
 path.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
def coord(face):
 uv=face.get('uv')
 if not uv:return None
 return (round((uv[0]-.25)*2),round((uv[1]-.25)*2))
def make_new_model(base,item,display,glow_mask):
 opaque={(x,y) for y in range(32) for x in range(32) if base.getpixel((x,y))[3]}
 elements=[]
 def uv(x,y):
  u=x/2+.25; v=y/2+.25; return [u,v,u,v]
 for x,y in sorted(opaque,key=lambda p:(p[1],p[0])):
  u=uv(x,y)
  faces={'north':{'texture':'#glow' if (x,y) in glow_mask else '#layer0','uv':u},'south':{'texture':'#glow' if (x,y) in glow_mask else '#layer0','uv':u}}
  if (x,y) in glow_mask:
   for s in ('north','south'): faces[s]['forge_data']={'block_light':15,'sky_light':15,'ambient_occlusion':False}
  for side,neighbor in [('west',(x-1,y)),('east',(x+1,y)),('up',(x,y-1)),('down',(x,y+1))]:
   if neighbor not in opaque: faces[side]={'texture':'#layer0','uv':u}
  elements.append({'from':[x/2,16-(y+1)/2,7.5],'to':[(x+1)/2,16-y/2,8.5],'shade':False,'faces':faces})
 return {'gui_light':'front','display':display,'textures':{'layer0':f'echopickaxe:item/{item}','particle':'#layer0','glow':f'echopickaxe:item/{item}_glow'},'ambientocclusion':False,'elements':elements}
def update_existing_model(path,item,glow_mask):
 d=json.loads(path.read_text(encoding='utf-8'))
 d['textures']['glow']=f'echopickaxe:item/{item}_glow'
 for e in d['elements']:
  for side in ('north','south'):
   face=e.get('faces',{}).get(side)
   if not face:continue
   xy=coord(face)
   if xy in glow_mask:
    face['texture']='#glow'; face['forge_data']={'block_light':15,'sky_light':15,'ambient_occlusion':False}
   else:
    face['texture']='#layer0'; face.pop('forge_data',None)
 return d
def write_model(path,data):
 path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def tuning_frames(base,oldframes):
 frames=[]
 white=(255,255,248); bright_center=tuple(min(255,c+8) for c in base.getpixel(CENTER)[:3]); mid=(104,216,231); low=(36,134,171)
 for fidx,old in enumerate(oldframes):
  # Preserve the whole current 1.7.5 glow frame byte-for-byte in RGBA outside the 13-texel star ROI.
  f=old.copy(); f.putpixel(CENTER,(*bright_center,255))
  if fidx<=2 or fidx>=13:
   # contracted: the new outer pixel is only a low cyan afterglow; the former tip softens,
   # and the white endpoint retreats one pixel inward.
   for _,line in RAYS.items():
    inner,old,outer=line
    f.putpixel(inner,(*white,255)); f.putpixel(old,(*mid,255)); f.putpixel(outer,(*low,255))
  elif fidx==3:
   for line in RAYS.values():
    inner,old,outer=line
    f.putpixel(inner,(*white,255)); f.putpixel(old,(*white,255)); f.putpixel(outer,(*mid,255))
  elif 4<=fidx<=7:
   # Fully expanded four-point white outline.
   for line in RAYS.values():
    for p in line: f.putpixel(p,(*white,255))
  elif 8<=fidx<=11:
   # Retain each original white ray but let only one outer endpoint flare at a time.
   outer_cyan=(205,241,248)
   for line in RAYS.values():
    inner,old,outer=line
    f.putpixel(inner,(*white,255)); f.putpixel(old,(*white,255)); f.putpixel(outer,(*outer_cyan,255))
   sparkle=list(RAYS.values())[fidx-8][2]
   f.putpixel(sparkle,(255,255,252,255))
  elif fidx==12:
   for line in RAYS.values():
    inner,old,outer=line
    f.putpixel(inner,(*white,255)); f.putpixel(old,(*white,255)); f.putpixel(outer,(*mid,255))
  else:
   # Retraction phase: maintain a medium-cyan tail instead of a dark/off frame.
   for line in RAYS.values():
    inner,old,outer=line
    f.putpixel(inner,(*white,255)); f.putpixel(old,(*mid,255)); f.putpixel(outer,(*low,255))
  frames.append(f)
 return frames
def extension_frames(base):
 frames=[]
 for i in range(16):
  f=Image.new('RGBA',(32,32),(0,0,0,0))
  active={RING[(i*len(RING)//16)%len(RING)],RING[(i*len(RING)//16+1)%len(RING)]}
  for p in RING:
   rgb=base.getpixel(p)[:3]
   if p in active: rgb=mult(rgb,1.18)
   f.putpixel(p,(*rgb,255))
  frames.append(f)
 return frames

def sheet(base,frames,path,cols=4,scale=12):
 rows=math.ceil(len(frames)/cols); board=Image.new('RGBA',(cols*32*scale,rows*32*scale),(60,64,72,255))
 for i,glow in enumerate(frames):
  tile=full_item(base,glow).resize((32*scale,32*scale),Image.Resampling.NEAREST)
  board.alpha_composite(tile,((i%cols)*32*scale,(i//cols)*32*scale))
 board.convert('RGB').save(path)
def labeled_phases(base,frames,indices,labels,path,scale=10,cols=3):
 tile=32*scale; label_h=28; rows=math.ceil(len(indices)/cols)
 board=Image.new('RGB',(cols*tile,rows*(tile+label_h)),(236,239,243)); d=ImageDraw.Draw(board)
 for j,(idx,label) in enumerate(zip(indices,labels)):
  x=(j%cols)*tile; y=(j//cols)*(tile+label_h)
  d.text((x+5,y+4),label,fill=(18,21,25))
  image=full_item(base,frames[idx]).resize((tile,tile),Image.Resampling.NEAREST)
  matte=Image.new('RGBA',(tile,tile),(63,67,76,255)); matte.alpha_composite(image)
  board.paste(matte.convert('RGB'),(x,y+label_h))
 board.save(path)
def gif(base,frames,path,ticks_per_frame=4):
 displays=[full_item(base,f) for f in interp_frames(frames,ticks_per_frame)]
 # Composite on neutral matte and export one preview frame per real game tick (50ms at 20tps).
 matte=Image.new('RGBA',(32,32),(64,68,76,255)); pages=[]
 for f in displays:
  m=matte.copy(); m.alpha_composite(f); pages.append(m.convert('P',palette=Image.Palette.ADAPTIVE))
 pages[0].save(path,save_all=True,append_images=pages[1:],duration=50,loop=0,disposal=2)

CAND.mkdir(parents=True,exist_ok=True)
import_info=import_target_base(SRC/'enhanced_extension_crystal_2-imagegen-raw-v2.png',CAND/'textures/item/enhanced_extension_crystal_2.png')
base_target=load(CAND/'textures/item/enhanced_extension_crystal_2.png')
base_tune=load(ASSETS/'textures/item/tuning_crystal.png')
old_tune_image=load(ASSETS/'textures/item/tuning_crystal_glow.png')
old_tune_frames=[old_tune_image.crop((0,y,32,y+32)) for y in range(0,old_tune_image.height,32)]
old_tune_meta=json.loads((ASSETS/'textures/item/tuning_crystal_glow.png.mcmeta').read_text(encoding='utf-8'))['animation']
old_tune_mask={(x,y) for y in range(32) for x in range(32) if old_tune_frames[0].getpixel((x,y))[3]}
assert all({(x,y) for y in range(32) for x in range(32) if f.getpixel((x,y))[3]}==old_tune_mask for f in old_tune_frames), 'baseline tuning glow mask must remain fixed'
assert base_target.size==base_tune.size==(32,32)
assert all(base_target.getpixel(p)[3] for p in RING), 'ring animation path must stay inside the hard-alpha sprite'
assert all(base_tune.getpixel(p)[3] for p in TUNE_MASK), 'tuning rays must stay inside the existing silhouette'
# Keep base PNGs exact for tuning; generated target base remains separate from production.
(CAND/'textures/item/tuning_crystal.png').write_bytes((ASSETS/'textures/item/tuning_crystal.png').read_bytes())
# Target animation: fixed-alpha ring mask, a two-pixel same-hue glint travels slowly along the green circuit.
ring_frames=extension_frames(base_target); save_strip(ring_frames,CAND/'textures/item/enhanced_extension_crystal_2_glow.png'); write_meta(CAND/'textures/item/enhanced_extension_crystal_2_glow.png.mcmeta',16,4,True)
# Tuning animation retains the baseline 16x6 ticks = 4.8 s; endpoints move by one existing opaque texel.
tune_frames=tuning_frames(base_tune,old_tune_frames); save_strip(tune_frames,CAND/'textures/item/tuning_crystal_glow.png'); (CAND/'textures/item/tuning_crystal_glow.png.mcmeta').write_bytes((ASSETS/'textures/item/tuning_crystal_glow.png.mcmeta').read_bytes())
# Models: new tier-two shape uses standard half-pixel boxes, center UVs, and silhouette-only side faces.
old_target_model=json.loads((ASSETS/'models/item/enhanced_extension_crystal_2.json').read_text(encoding='utf-8'))
new_model=make_new_model(base_target,'enhanced_extension_crystal_2',old_target_model['display'],set(RING))
write_model(CAND/'models/item/enhanced_extension_crystal_2.json',new_model)
# Tuning keeps existing model elements/display; only selected north/south faces gain fullbright metadata.
tune_mask_union=old_tune_mask|TUNE_MASK
tune_model=update_existing_model(ASSETS/'models/item/tuning_crystal.json','tuning_crystal',tune_mask_union)
write_model(CAND/'models/item/tuning_crystal.json',tune_model)
# Visual phases and tick-accurate animation previews.
sheet(base_target,ring_frames,PRE/'enhanced_extension_crystal_2-frames-v0.1.0.png',cols=4,scale=10); gif(base_target,ring_frames,PRE/'enhanced_extension_crystal_2-animation-v0.1.0.gif')
labeled_phases(base_target,ring_frames,[0,4,8,12],['frame 0 · highlight starts','frame 4 · glint travels','frame 8 · ring pulse','frame 12 · glint returns'],PRE/'enhanced_extension_crystal_2-keyframes-v0.1.0.png',scale=10,cols=2)
labeled_phases(base_tune,tune_frames,[0,3,6,8,12,14],['frame 0 · contracted','frame 3 · growing','frame 6 · expanded','frame 8 · north sparkle','frame 12 · retreating','frame 14 · cyan afterglow'],PRE/'tuning_crystal-phases-v0.1.0.png',scale=10,cols=3); gif(base_tune,tune_frames,PRE/'tuning_crystal-animation-v0.1.0.gif',ticks_per_frame=old_tune_meta['frametime'])
# Tuning coordinate proof: mark current white tips, retracted positions, and expanded tips.
coord=Image.new('RGB',(32*20,32*20),(44,48,58)); d=ImageDraw.Draw(coord)
for y in range(32):
 for x in range(32):
  q=base_tune.getpixel((x,y))
  if q[3]: d.rectangle((x*20,y*20,x*20+19,y*20+19),fill=q[:3])
for p in TUNE_MASK:
 x,y=p; color=(255,55,60) if p in [line[1] for line in RAYS.values()] else (255,215,40)
 d.rectangle((x*20,y*20,x*20+19,y*20+19),outline=color,width=2); d.text((x*20+2,y*20+2),f'{x},{y}',fill=(255,255,255))
for x in range(32): d.text((x*20+3,2),str(x),fill='white')
for y in range(32): d.text((2,y*20+3),str(y),fill='white')
coord.save(PRE/'tuning_crystal-ray-coordinates-v0.1.0.png')
# Family sheet shows exact 32 and true nearest 16 sizes for all three extension tiers.
family=Image.new('RGB',(3*192,420),(236,238,242)); draw=ImageDraw.Draw(family)
for col,name in enumerate(('extension_crystal','enhanced_extension_crystal','enhanced_extension_crystal_2')):
 src=ASSETS/'textures/item'/f'{name}.png' if name!='enhanced_extension_crystal_2' else CAND/'textures/item'/f'{name}.png'
 image=load(src)
 title=('基础','强化一阶','强化二阶')[col]
 draw.text((col*192+5,3),title+' 32px',fill=(20,22,26)); large=Image.new('RGBA',(192,192),(64,68,76,255)); large.alpha_composite(image.resize((192,192),Image.Resampling.NEAREST)); family.paste(large.convert('RGB'),(col*192,24))
 draw.text((col*192+5,222),title+' 真实16px',fill=(20,22,26)); small=image.resize((16,16),Image.Resampling.NEAREST).resize((192,192),Image.Resampling.NEAREST); sm=Image.new('RGBA',(192,192),(64,68,76,255)); sm.alpha_composite(small); family.paste(sm.convert('RGB'),(col*192,243))
family.save(PRE/'extension-family-32-and-16-v0.1.0.png')
# Record palette/path/mask metadata for independent review.
manifest={'version':'0.1.0','status':'candidate_only','items':{'tuning_crystal':{'base':'existing 1.7.5 base copied byte-exact','frames':len(old_tune_frames),'frametime_ticks':old_tune_meta['frametime'],'cycle_ticks':len(old_tune_frames)*old_tune_meta['frametime'],'interpolate':old_tune_meta.get('interpolate',False),'existing_glow_mask_pixels':len(old_tune_mask),'new_star_mask_pixels':len(TUNE_MASK),'combined_glow_mask_pixels':len(tune_mask_union),'old_glow_rgb_preserved_outside_star_roi':True,'center':CENTER,'rays':RAYS,'stages':{'contracted_frames':[0,1,2,13,14,15],'transition_out':[3],'expanded_frames':[4,5,6,7],'sparkle_frames':[8,9,10,11],'transition_in':[12]}},'enhanced_extension_crystal_2':{'base':'imagegen raw-v2 -> alpha bbox >=128 crop -> nearest 18x28 -> hard-alpha 32x32','raw_source':'artwork/source/v0.1.0/enhanced_extension_crystal_2-imagegen-raw-v2.png','import':import_info,'frames':16,'frametime_ticks':4,'cycle_ticks':64,'interpolate':True,'glow_mask_pixels':len(RING),'moving_highlight':'two adjacent emerald/cyan pixels progress around the center ring; mask and base crystal facets stay fixed'}}}
(SRC/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
(SRC/'generation-notes.md').write_text('''# 0.1.0 crystal asset candidates\n\nOnly `tuning_crystal` and `enhanced_extension_crystal_2` are in scope. Assets remain candidate-only under `artwork/validation/v0.1.0/crystals/candidate`; no production files are changed.\n\n`enhanced_extension_crystal_2` uses `artwork/source/v0.1.0/enhanced_extension_crystal_2-imagegen-raw-v2.png`, generated and edited through built-in image_gen with transparent background. The reproducible importer thresholds source alpha at 128 only to calculate its crop box, crops that bbox, nearest-neighbor scales the subject to 18x28, centers it at (7,2) on a 32x32 canvas, preserves RGB, and thresholds alpha to 0/255. The output has 251 opaque texels. `artwork/source/v0.1.0/design_prompt.md` records both prompts, reference roles, and built-in tool paths.\n\nThe new tier-two model uses the standard half-pixel per-opaque-texel mesh, center UV, north/south faces, and layer0 side faces only at the outer alpha boundary. It has no item/generated parent and reuses the previous model display transforms.\n\n`tuning_crystal` base PNG and all unchanged facets are copied byte-exact from the current production resource. Its original 1.7.5 glow strip (16 frames, 6 ticks/frame, 96 ticks / 4.8 seconds, interpolate=true) is the per-frame base. The center pixel (14,15) stays bright. Each existing ray has an inner/original/extended set: N (14,13)/(14,12)/(14,11), S (14,18)/(14,19)/(14,20), W (12,15)/(11,15)/(10,15), E (16,15)/(17,15)/(18,15). Contracted states show cyan tips and low-cyan outer afterglow; expanded states have all three white pixels; four sparkle frames move the white endpoint around the rays. The existing 132-pixel mask and every RGBA pixel outside the 13-pixel star ROI are preserved per frame; the fixed union mask has 141 pixels. New emissive faces bind only north/south with block/sky light 15 and ambient occlusion false.\n\n`enhanced_extension_crystal_2` glow uses a fixed 14-texel emerald/cyan circuit mask and advances a two-pixel same-hue highlight around the central ring. Its 16x4-tick cycle is 3.2 seconds; crystal facets and outer silhouette stay steady. Both glow strips have a fixed binary alpha mask and 16 frames.\n\nPreviews in `artwork/validation/v0.1.0/crystals/` include the three-tier 32/real-16px family comparison, tuning labeled phases and coordinate diagram, and per-item tick-sampled GIFs.\n''',encoding='utf-8')
print(json.dumps({'candidate_files':sum(p.is_file() for p in CAND.rglob('*')),'target_opaque':sum(1 for y in range(32) for x in range(32) if base_target.getpixel((x,y))[3]),'ring_mask':len(RING),'tuning_mask':len(TUNE_MASK),'candidate':str(CAND)},ensure_ascii=False))
