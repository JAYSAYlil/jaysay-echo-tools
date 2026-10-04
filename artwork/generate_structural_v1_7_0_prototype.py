from __future__ import annotations
import json, math
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path('.')
SRC = ROOT/'artwork/source/emissive-v1.6.0/base_textures'
BASE_MODELS = ROOT/'artwork/source/emissive-v1.6.0/base_models'
OUT = ROOT/'artwork/validation/v1.7.0/prototype'
OUT.mkdir(parents=True, exist_ok=True)
SIZE = 32
EYES = {
 'extension_crystal': {'frames':24,'ticks':4,'tier':1},
 'enhanced_extension_crystal': {'frames':32,'ticks':3,'tier':2},
 'enhanced_extension_crystal_2': {'frames':32,'ticks':3,'tier':3},
}
STAR = {'frames':24,'ticks':2}

def mask_eye(im):
 return {(x,y) for y in range(10,23) for x in range(10,22) if im.getpixel((x,y))[3] == 255}

def mask_star(im):
 pts=set()
 for y in range(2,29):
  for x in range(4,25):
   if im.getpixel((x,y))[3] != 255: continue
   dx,dy=x-15.5,y-15
   if abs(dx)<=1 and 2<=y<=28 or abs(dy)<=1 and 4<=x<=24 or abs(dx)+abs(dy)<=5:
    pts.add((x,y))
 return pts

def eye_state(name, frame):
 tier=EYES[name]['tier']
 if tier == 1:
  if frame <= 4: return (15,16,4,3,2,False,'look left')
  if frame <= 9: return (17,16,4,3,2,False,'look right')
  if frame <= 14: return (16,16,4,3,3,False,'center')
  if frame == 15: return (16,16,4,3,3,True,'blink')
  return (16,16,4,3,3,False,'quiet hold')
 if tier == 2:
  states=[((15,16,4,3,2,False),'left'),((16,15,4,3,2,False),'up'),((17,16,4,3,2,False),'right'),((16,17,4,3,2,False),'down'),((16,16,3,2,2,False),'iris contracts'),((16,16,4,3,2,False),'iris expands'),((16,16,4,3,2,False),'hold'),((16,16,4,3,2,True),'blink')]
  ix=min(7,frame//4)
  return (*states[ix][0],states[ix][1])
 # Tier III has a deliberate center lock, visible locator ticks, and release.
 if frame < 6: return (15,16,4,3,2,False,'scan left')
 if frame < 12: return (17,16,4,3,2,False,'scan right')
 if frame < 18: return (16,16,4,3,1,False,'lock narrow pupil')
 if frame < 24: return (16,16,4,3,1,False,'four locator ticks')
 if frame < 28: return (16,16,4,3,2,True,'blink release')
 return (16,16,4,3,3,False,'unlock')

def draw_eye_frame(base, mask, name, frame):
 out=Image.new('RGBA',(SIZE,SIZE),(0,0,0,0))
 # Keep every selected pixel opaque so the animated atlas has a fixed hard mask.
 tier=EYES[name]['tier']
 pupil_x,pupil_y,rx,ry,pupil_w,blink,label=eye_state(name,frame)
 # Tiers retain their source hues around the eye but have progressively cooler cores.
 palette={1:{'iris':(26,214,136),'rim':(18,133,103),'glint':(167,255,218)},
          2:{'iris':(40,222,176),'rim':(19,141,133),'glint':(190,255,239)},
          3:{'iris':(34,206,166),'rim':(17,118,122),'glint':(220,255,244)}}[tier]
 if tier == 2: palette['iris']=(34,204,208)
 if tier == 3: palette['iris']=(36,199,195)
 for x,y in mask:
  r,g,b,a=base.getpixel((x,y))
  color=(r,g,b)
  dx,dy=x-16,y-16
  # Fixed dark socket stays in place; the bright iris itself follows pupil_x/y.
  socket=((dx/5.0)**2+(dy/4.0)**2)<=1.0
  if socket:
   color=(5,30,42)
  else:
   color=tuple(round(c*0.68) for c in color)
  ix,iy=x-pupil_x,y-pupil_y
  iris_radius=2.65 if (tier==2 and 16<=frame<20) else 4.1
  iris_distance=abs(ix)*1.0+abs(iy)*1.12
  if iris_distance<=iris_radius:
   color=palette['rim'] if iris_distance>=iris_radius-1.1 else palette['iris']
  # Two-pixel-wide, five-pixel-tall dark slit, always centered in its moving iris.
  pleft=pupil_x-(pupil_w//2)
  pupil_height=1 if (tier==2 and 16<=frame<20) else 2
  if pleft<=x<pleft+pupil_w and abs(iy)<=pupil_height:
   color=(1,8,14)
  # The eye glint rides just above/left of the iris and never covers the pupil.
  if (x,y)==(pupil_x-2,pupil_y-2):
   color=palette['glint']
  if tier==3 and 18<=frame<24:
   # Four locator ticks surround the locked slit, all inside the iris.
   if (abs(ix)==3 and iy==0) or (abs(iy)==2 and ix==0): color=(92,252,225)
  if blink:
   # Eyelid closes across the fixed socket; alpha and outer contour remain fixed.
   if y==16 and 12<=x<=20: color=(27,217,173) if abs(dx)>1 else (1,8,14)
   elif 14<=y<=18: color=(5,30,42)
  out.putpixel((x,y),(*color,255))
 return out,label

def star_length(frame):
 # 24-frame breathing cross: compact, expand all four arms, hold, retract, quiet core.
 if frame <= 2: return 2.0,'compact core'
 if frame <= 8: return 2+(frame-2)*(12/6),'four arms extend'
 if frame <= 11: return 14.0,'full-length hold'
 if frame <= 17: return 14-(frame-11)*(12/6),'four arms retract'
 return 2.0,'quiet core'

def draw_star_frame(base,mask,frame):
 out=Image.new('RGBA',(SIZE,SIZE),(0,0,0,0))
 length,label=star_length(frame)
 cx,cy=15.5,15
 for x,y in mask:
  dx,dy=x-cx,y-cy
  vertical=abs(dy)>=abs(dx)
  distance=abs(dy) if vertical else abs(dx)
  # Only the expanding four-arm silhouette emits; central diamond is stable.
  active=distance<=length or abs(dx)+abs(dy)<=2.5
  if active:
   # Keep cyan-white star core and icy blue outer arm, below white clipping.
   level=max(0.0,min(1.0,(length-distance+1.4)/2.3))
   core=abs(dx)+abs(dy)<=2.5
   if core: rgb=(92,224,245)
   else:
    rgb=(round(25+61*level),round(107+116*level),round(157+81*level))
   if 1.7 < distance <= length and level>0.72: rgb=(143,231,247)
  else:
   rgb=(7,26,42) # collapsed RGB keeps mask/geometry fixed without a long lit bar
  out.putpixel((x,y),(*rgb,255))
 return out,label

def write_preview(name,base,mask,frames,ticks,kind):
 strip=Image.new('RGBA',(SIZE,SIZE*len(frames)),(0,0,0,0))
 composite=[]; labels=[]
 for i,(glow,label) in enumerate(frames):
  strip.alpha_composite(glow,(0,i*SIZE))
  img=base.copy()
  for x,y in mask: img.putpixel((x,y),glow.getpixel((x,y)))
  composite.append(img); labels.append(label)
 strip.save(OUT/f'{name}_glow.png')
 (OUT/f'{name}_glow.png.mcmeta').write_text(json.dumps({'animation':{'width':32,'height':32,'frametime':ticks,'frames':list(range(len(frames))),'interpolate':False}},indent=2)+'\n',encoding='utf-8')
 m=Image.new('RGBA',(32,32),(0,0,0,0))
 for x,y in mask:m.putpixel((x,y),(255,255,255,255))
 m.resize((256,256),Image.Resampling.NEAREST).save(OUT/f'{name}-mask.png')
 # Build an illustrative model beside the prototype only, starting from the 1.5.0 baseline.
 model=json.loads((BASE_MODELS/f'{name}.json').read_text(encoding='utf-8-sig'))
 model.setdefault('textures',{})['glow']=f'echopickaxe:item/{name}_glow'
 marked=set()
 for elem in model['elements']:
  north=elem['faces'].get('north')
  if not north: continue
  u,v=north['uv'][:2]
  xy=(round((u-.25)*2),round((v-.25)*2))
  if xy not in mask: continue
  marked.add(xy)
  for side in ('north','south'):
   face=elem['faces'][side]; face['texture']='#glow'; face['forge_data']={'block_light':15,'sky_light':15,'ambient_occlusion':False}
 if marked!=mask: raise RuntimeError(f'{name} model coordinate mismatch {len(marked)} != {len(mask)}')
 (OUT/'models').mkdir(exist_ok=True)
 (OUT/'models'/f'{name}.json').write_text(json.dumps(model,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 return composite,labels,len(marked)

all_frames={}; summary={}
for name,cfg in EYES.items():
 base=Image.open(SRC/f'{name}.png').convert('RGBA'); mask=mask_eye(base)
 frames=[draw_eye_frame(base,mask,name,i) for i in range(cfg['frames'])]
 composite,labels,points=write_preview(name,base,mask,frames,cfg['ticks'],'eye')
 all_frames[name]=(composite,cfg['frames']*cfg['ticks'],cfg['ticks'])
 summary[name]={'mask_pixels':len(mask),'faces':2*points,'frames':cfg['frames'],'frametime_ticks':cfg['ticks'],'cycle_ticks':cfg['frames']*cfg['ticks'],'states':sorted(set(labels))}

name='tuning_crystal'; cfg=STAR
base=Image.open(SRC/f'{name}.png').convert('RGBA'); mask=mask_star(base)
frames=[draw_star_frame(base,mask,i) for i in range(cfg['frames'])]
composite,labels,points=write_preview(name,base,mask,frames,cfg['ticks'],'star')
all_frames[name]=(composite,cfg['frames']*cfg['ticks'],cfg['ticks'])
summary[name]={'mask_pixels':len(mask),'faces':2*points,'frames':cfg['frames'],'frametime_ticks':cfg['ticks'],'cycle_ticks':cfg['frames']*cfg['ticks'],'states':sorted(set(labels))}

# Four-up animated preview, sampled at each Minecraft tick; 4.8s common eye cycle.
common_ticks=math.lcm(*(v[1] for v in all_frames.values()))
preview=[]
for tick in range(common_ticks):
 canvas=Image.new('RGB',(2*256+36,2*256+48),(42,47,55)); draw=ImageDraw.Draw(canvas)
 for i,(name,(frames,cycle,ticks)) in enumerate(all_frames.items()):
  idx=(tick//ticks)%len(frames)
  img=frames[idx].resize((256,256),Image.Resampling.NEAREST)
  x=12+(i%2)*274; y=24+(i//2)*274
  canvas.paste(img,(x,y),img)
  draw.text((x,y-16),name,fill='white')
 preview.append(canvas)
preview[0].save(OUT/'eye-star-prototype.gif',save_all=True,append_images=preview[1:],duration=50,loop=0,optimize=True,disposal=2)
# Four deliberately chosen action states per item with eye coordinates/labels.
phase_frames={
 'extension_crystal':[(0,'left pupil x15 y16'),(6,'right pupil x17 y16'),(12,'center pupil x16 y16'),(15,'blink frame 15')],
 'enhanced_extension_crystal':[(0,'left pupil x15 y16'),(8,'right pupil x17 y16'),(16,'iris contracts'),(28,'blink frame 28')],
 'enhanced_extension_crystal_2':[(0,'scan left x15 y16'),(6,'scan right x17 y16'),(12,'lock narrow x16 y16'),(18,'4 locator ticks')],
 'tuning_crystal':[(0,'compact core'),(6,'arms extend'),(12,'full hold'),(18,'retract')],
}
board=Image.new('RGB',(1270,4*320+5*24),(42,47,55)); d=ImageDraw.Draw(board)
for row,(name,(frames,cycle,ticks)) in enumerate(all_frames.items()):
 d.text((10,row*320+3),name,fill='white')
 for col,(frame_index,label) in enumerate(phase_frames[name]):
  im=frames[frame_index].resize((256,256),Image.Resampling.NEAREST)
  x=150+col*284; y=row*320+24
  board.paste(im,(x,y),im)
  d.text((x,y+258),f'f{frame_index}: {label}',fill=(205,218,228))
board.save(OUT/'eye-star-phases.png')
(OUT/'prototype-manifest.json').write_text(json.dumps({'source_textures':'artwork/source/emissive-v1.6.0/base_textures','writes_production_assets':False,'items':summary},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
print('GIF',OUT/'eye-star-prototype.gif','phase sheet',OUT/'eye-star-phases.png')
