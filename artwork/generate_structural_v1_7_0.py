from __future__ import annotations
import colorsys, json, math, shutil
from pathlib import Path
from PIL import Image, ImageDraw

ROOT=Path('.')
ASSET=ROOT/'src/main/resources/assets/echopickaxe'
TEXTURES=ASSET/'textures/item'
MODELS=ASSET/'models/item'
SOURCE=ROOT/'artwork/source/structural-v1.7.0'
SOURCE_BASE=ROOT/'artwork/source/emissive-v1.6.0/base_textures'
SOURCE_MODELS=ROOT/'artwork/source/emissive-v1.6.0/base_models'
VALID=ROOT/'artwork/validation/v1.7.0'
SIZE=32
CONFIG={
 'echo_pickaxe':{'frames':32,'ticks':3,'interp':False,'motion':'nodes-cracks-motes'},
 'echo_upgrade_smithing_template':{'frames':32,'ticks':3,'interp':False,'motion':'rune-write-erase'},
 'echo_crystal':{'frames':32,'ticks':3,'interp':True,'motion':'chip-flip-width'},
 'resonance_crystal':{'frames':32,'ticks':3,'interp':False,'motion':'double-heartbeat-branch-release'},
 'enhanced_resonance_crystal':{'frames':32,'ticks':3,'interp':False,'motion':'core-compression-branch-sparks-release'},
 'frequency_crystal':{'frames':32,'ticks':3,'interp':True,'motion':'triple-branch-grow-rejoin'},
 'enhanced_frequency_crystal':{'frames':32,'ticks':3,'interp':False,'motion':'two-motes-converge-bounce'},
 'enhanced_frequency_crystal_2':{'frames':32,'ticks':3,'interp':False,'motion':'three-motes-rune-scatter'},
 'extension_crystal':{'frames':24,'ticks':4,'interp':False,'motion':'eye-left-right-blink','tier':1},
 'enhanced_extension_crystal':{'frames':32,'ticks':3,'interp':False,'motion':'eye-cardinal-contract','tier':2},
 'enhanced_extension_crystal_2':{'frames':32,'ticks':3,'interp':False,'motion':'eye-lock-ticks-release','tier':3},
 'tuning_crystal':{'frames':24,'ticks':2,'interp':True,'motion':'star-cross-contract-extend'},
}
PALETTE={
 'cyan':(42,211,231),'ice':(79,222,245),'green':(37,214,140),'emerald':(37,225,144),
 'red':(242,43,38),'gold':(244,158,45),'purple':(186,78,244),'violet':(147,66,223),
 'darkcyan':(6,33,49),'darkgreen':(5,34,38),'darkred':(34,5,12),'darkpurple':(19,7,43),
}

def color_group(rgb):
 r,g,b=(v/255 for v in rgb); h,s,v=colorsys.rgb_to_hsv(r,g,b)
 if s<0.34 or v<0.25: return None
 if h<=0.055 or h>=0.965: return 'red'
 if 0.07<=h<0.20: return 'gold'
 if 0.20<=h<0.43: return 'green'
 if 0.43<=h<=0.67: return 'cyan'
 if 0.70<=h<=0.92: return 'purple'
 return None

def pixel_group(im,x,y):
 r,g,b,a=im.getpixel((x,y)); return color_group((r,g,b)) if a==255 else None

def circle_points(candidates,center,radius):
 cx,cy=center
 return {p for p in candidates if math.hypot(p[0]-cx,p[1]-cy)<=radius}

def nearest_cluster(candidates,center,count=8):
 if not candidates:return set()
 cx,cy=center
 return set(sorted(candidates,key=lambda p:(p[0]-cx)**2+(p[1]-cy)**2)[:count])

def distance_segment(x,y,a,b):
 ax,ay=a; bx,by=b; dx=bx-ax; dy=by-ay
 den=dx*dx+dy*dy
 u=0.0 if den==0 else max(0.0,min(1.0,((x-ax)*dx+(y-ay)*dy)/den))
 px,py=ax+u*dx,ay+u*dy
 return math.hypot(x-px,y-py),u

def make_frame(mask,color_fn):
 out=Image.new('RGBA',(SIZE,SIZE),(0,0,0,0))
 for x,y in mask: out.putpixel((x,y),(*color_fn(x,y),255))
 return out

def dim_source(base,x,y,factor=.20):
 rgb=base.getpixel((x,y))[:3]
 return tuple(max(1,min(255,round(c*factor))) for c in rgb)

def collect_mask(base,predicate):
 return {(x,y) for y in range(SIZE) for x in range(SIZE) if base.getpixel((x,y))[3]==255 and predicate(x,y,color_group(base.getpixel((x,y))[:3]))}

# Eye keyframe description & animation. Iris position follows the pupil so it stays enclosed.
def eye_state(name,f):
 tier=CONFIG[name]['tier']
 if tier==1:
  if f<=4:return {'x':15,'y':16,'w':2,'iris':4.1,'blink':False,'state':'look left'}
  if f<=9:return {'x':17,'y':16,'w':2,'iris':4.1,'blink':False,'state':'look right'}
  if f<=14:return {'x':16,'y':16,'w':2,'iris':4.1,'blink':False,'state':'center hold'}
  if f==15:return {'x':16,'y':16,'w':2,'iris':4.1,'blink':True,'state':'blink'}
  return {'x':16,'y':16,'w':2,'iris':4.1,'blink':False,'state':'quiet hold'}
 if tier==2:
  stages=[(15,16,2,4.1,'left'),(16,15,2,4.1,'up'),(17,16,2,4.1,'right'),(16,17,2,4.1,'down'),(16,16,1,2.65,'iris contracts'),(16,16,2,4.1,'iris expands'),(16,16,2,4.1,'hold'),(16,16,2,4.1,'blink')]
  x,y,w,r,state=stages[min(7,f//4)]
  return {'x':x,'y':y,'w':w,'iris':r,'blink':state=='blink','state':state}
 if f<6:return {'x':15,'y':16,'w':2,'iris':4.1,'blink':False,'state':'scan left'}
 if f<12:return {'x':17,'y':16,'w':2,'iris':4.1,'blink':False,'state':'scan right'}
 if f<18:return {'x':16,'y':16,'w':1,'iris':4.1,'blink':False,'state':'lock narrow pupil'}
 if f<24:return {'x':16,'y':16,'w':1,'iris':4.1,'blink':False,'state':'four locator ticks'}
 if f<28:return {'x':16,'y':16,'w':2,'iris':4.1,'blink':True,'state':'blink release'}
 return {'x':16,'y':16,'w':2,'iris':4.1,'blink':False,'state':'unlock'}

def eye_mask(base):
 return {(x,y) for y in range(10,23) for x in range(10,22) if base.getpixel((x,y))[3]==255}

def draw_eye(base,mask,name,f):
 st=eye_state(name,f); tier=CONFIG[name]['tier']; px,py=st['x'],st['y']
 palettes={1:((28,226,134),(11,117,91),(190,255,220)),2:((43,218,201),(11,125,126),(205,255,242)),3:((34,203,184),(10,109,117),(219,255,245))}
 iris,rim,glint=palettes[tier]; out=Image.new('RGBA',(SIZE,SIZE),(0,0,0,0))
 pleft=px-st['w']//2
 pupil_height=1 if tier==2 and st['state']=='iris contracts' else 2
 for x,y in mask:
  dx,dy=x-16,y-16
  socket=(dx/5.0)**2+(dy/4.0)**2<=1.0
  color=(4,27,40) if socket else dim_source(base,x,y,.24)
  ix,iy=x-px,y-py; d=abs(ix)+abs(iy)*1.12
  if d<=st['iris']:
   color=rim if d>=st['iris']-1.15 else iris
  if pleft<=x<pleft+st['w'] and abs(iy)<=pupil_height:
   color=(1,7,13)
  if (x,y)==(px-2,py-2): color=glint
  if tier==3 and st['state']=='four locator ticks':
   if (abs(ix)==3 and iy==0) or (abs(iy)==2 and ix==0):color=(94,249,225)
  if st['blink']:
   if y==16 and 12<=x<=20:color=(26,220,169) if abs(dx)>1 else (1,7,13)
   elif 14<=y<=18:color=(4,27,40)
  out.putpixel((x,y),(*color,255))
 return out,st

def star_mask(base):
 pts=set()
 for y in range(2,29):
  for x in range(4,25):
   if base.getpixel((x,y))[3]!=255:continue
   dx,dy=x-15.5,y-15
   if (abs(dx)<=1 and 2<=y<=28) or (abs(dy)<=1 and 4<=x<=24) or abs(dx)+abs(dy)<=5:pts.add((x,y))
 return pts

def star_length(f):
 if f<=2:return 2.0
 if f<=8:return 2+(f-2)*2.0
 if f<=11:return 14.0
 if f<=17:return 14-(f-11)*2.0
 return 2.0

def draw_star(base,mask,f):
 length=star_length(f); out=Image.new('RGBA',(SIZE,SIZE),(0,0,0,0)); cx,cy=15.5,15
 for x,y in mask:
  dx,dy=x-cx,y-cy; vertical=abs(dy)>=abs(dx); dist=abs(dy) if vertical else abs(dx)
  active=dist<=length or abs(dx)+abs(dy)<=2.5
  if active:
   level=max(0,min(1,(length-dist+1.4)/2.3)); core=abs(dx)+abs(dy)<=2.5
   rgb=(86,216,239) if core else (round(22+67*level),round(90+132*level),round(140+94*level))
   if 1.7<dist<=length and level>.72:rgb=(151,230,247)
  else:rgb=(5,22,37)
  out.putpixel((x,y),(*rgb,255))
 return out

def pixel_line_regions(mask):
 # Fixed cyan path groups along the diagonal tool handle; nearest real opaque source coordinates only.
 handle={p for p in mask if p[1]>=15 and p[0]<=16}
 head={p for p in mask if p[1]<=15 and p[0]>=8}
 node_centers=[(3,27),(6,23),(9,20),(12,16)]
 nodes=[nearest_cluster(handle,c,6) for c in node_centers]
 cracks=[nearest_cluster(head,(13,9),8),nearest_cluster(head,(21,10),8)]
 motes=[nearest_cluster(head,(8,8),4),nearest_cluster(head,(25,12),4)]
 return node_centers,nodes,cracks,motes

def frames_pickaxe(base):
 mask=collect_mask(base,lambda x,y,g:g=='cyan')
 centers,nodes,cracks,motes=pixel_line_regions(mask)
 frames=[]
 for f in range(32):
  def rgb(x,y):
   p=(x,y); color=dim_source(base,x,y,.15)
   if f<16:
    k=f//4
    if p in nodes[k] and f%4<=2:color=(45,207,224) if f%4==0 else (105,239,247)
   elif 16<=f<20:
    k=(f-16)//2
    if p in cracks[k]:color=(118,235,245) if f%2==0 else (40,195,220)
   elif 20<=f<24:
    # Both echo motes stay visible at once and advance independently.
    for j,path in enumerate(motes):
     ordered=sorted(path,key=lambda q:(q[1],q[0]))
     if ordered and p==ordered[(f-20+j*2)%len(ordered)]:
      color=(105,230,241) if j==0 else (80,196,239)
   return color
  frames.append(make_frame(mask,rgb))
 key=[{'frame':0,'state':'handle node 1 charges','node':0,'center':centers[0]}, {'frame':4,'state':'handle node 2 charges','node':1,'center':centers[1]}, {'frame':8,'state':'handle node 3 charges','node':2,'center':centers[2]}, {'frame':12,'state':'handle node 4 charges','node':3,'center':centers[3]}, {'frame':16,'state':'pick head crack A flashes','crack':'A'}, {'frame':18,'state':'pick head crack B flashes','crack':'B'}, {'frame':20,'state':'two echo motes pulse simultaneously','mote_centers':[[min(x for x,y in m),min(y for x,y in m)] for m in motes],'bright_points':[sorted(m,key=lambda q:(q[1],q[0]))[(0+j*2)%len(m)] for j,m in enumerate(motes)]}, {'frame':21,'state':'two echo motes move on separate paths','bright_points':[sorted(m,key=lambda q:(q[1],q[0]))[(1+j*2)%len(m)] for j,m in enumerate(motes)]}, {'frame':24,'state':'quiet interval'}]
 return mask,frames,key

def frames_template(base):
 mask=collect_mask(base,lambda x,y,g:g in ('cyan','green') and 8<=x<=24 and 8<=y<=24)
 spine=sorted([p for p in mask if abs(p[0]-16)<=2],key=lambda p:(p[1],p[0]))
 branch=sorted(mask-set(spine),key=lambda p:(abs(p[0]-16),p[1],p[0]))
 frames=[]; ns=len(spine); nb=len(branch)
 for f in range(32):
  if f<12: count=math.ceil(ns*(f+1)/12); lit=set(spine[:count])
  elif f<20: count=math.ceil(nb*(f-11)/8); lit=set(spine)|set(branch[:count])
  elif f<24: lit=set(mask)
  elif f<32:
   q=(f-24)/8
   keep_b=round(nb*(1-q)); keep_s=round(ns*(1-q))
   lit=set(spine[:keep_s])|set(branch[:keep_b])
  else:lit=set()
  frames.append(make_frame(mask,lambda x,y,lit=lit:(34,211,229) if (x,y) in lit else dim_source(base,x,y,.14)))
 key=[{'frame':0,'state':'central rune stroke begins','spine_lit':max(1,math.ceil(ns/12)),'spine_total':ns}, {'frame':11,'state':'central stroke complete','spine_lit':ns,'branches_lit':0}, {'frame':15,'state':'side rune branches write','branches_lit':round(nb*.5),'branches_total':nb}, {'frame':20,'state':'full rune hold','rune_pixels':len(mask)}, {'frame':28,'state':'reverse erase','remaining_fraction':.5}]
 return mask,frames,key

def frames_echo_chip(base):
 mask=collect_mask(base,lambda x,y,g:g in ('cyan','green') and 11<=x<=21 and 8<=y<=25)
 frames=[]; widths=[1,2,3,2,1,2,3,2]
 for f in range(32):
  stage=f//4; half=widths[stage]; side=-1 if stage%2==0 else 1
  def rgb(x,y):
   dx,dy=x-16,y-16
   # Source crack remains low and steady; the shard's diamond width flips every four frames.
   on_chip=abs(dy)<=4 and abs(dx)<=max(0.25,half*(1-abs(dy)/5))
   if on_chip:
    lit_side=(x-16)*side>=0
    if abs(dx)<.6 and abs(dy)<=1: return (117,231,243)
    return (45,199,222) if lit_side else (8,69,88)
   if abs(dx)<=1 and abs(dy)<=5:return (8,48,63)
   return dim_source(base,x,y,.28)
  frames.append(make_frame(mask,rgb))
 key=[{'frame':0,'state':'shard narrow; left facet lit','width_class':1,'bright_side':'left'}, {'frame':4,'state':'shard widens and flips','width_class':2,'bright_side':'right'}, {'frame':8,'state':'wide shard','width_class':3,'bright_side':'left'}, {'frame':12,'state':'flip to right facet','width_class':2,'bright_side':'right'}, {'frame':20,'state':'narrow shard','width_class':1,'bright_side':'left'}, {'frame':24,'state':'wide shard returns','width_class':3,'bright_side':'left'}]
 return mask,frames,key

def frames_resonance(base,enhanced=False):
 if enhanced:
  mask=collect_mask(base,lambda x,y,g:(g=='red') or (g in ('cyan','green') and 10<=x<=21 and 10<=y<=22))
  core={p for p in mask if pixel_group(base,*p) in ('cyan','green') and 10<=p[0]<=21 and 10<=p[1]<=22}
  red={p for p in mask if pixel_group(base,*p)=='red'}
  a=nearest_cluster({p for p in red if p[0]<16},(12,15),7)
  b=nearest_cluster({p for p in red if p[0]>16},(20,15),7)
  a=sorted(a,key=lambda p:(p[1],p[0])); b=sorted(b,key=lambda p:(p[1],p[0]))
  frames=[]
  for f in range(32):
   if f<8:radius=4.5-(f/7)*3.4
   elif f<14:radius=1.1
   elif f<21:radius=1.1
   elif f<28:radius=1.1+(f-21)*(3.4/6)
   else:radius=4.5
   def rgb(x,y):
    p=(x,y)
    if p in core:
     d=abs(x-16)+abs(y-16)
     if d<=radius:return (64,218,241) if f<14 or f>=21 else (145,246,248)
     return (4,42,54)
    if p in red:
     if 14<=f<21:
      source=a if f<17 else b
      ix=f-14 if f<17 else f-17
      active=source[min(ix,len(source)-1)] if source else None
      if p==active:return (245,165,54) if f%2 else (250,71,40)
     return (35,6,10)
    return dim_source(base,x,y,.16)
   frames.append(make_frame(mask,rgb))
  key=[{'frame':0,'state':'wide cyan core starts compression','core_radius':4.5}, {'frame':7,'state':'core compressed','core_radius':1.1}, {'frame':14,'state':'red branch A sparks','spark':list(a[0]) if a else None}, {'frame':17,'state':'red branch B sparks','spark':list(b[0]) if b else None}, {'frame':22,'state':'core releases outward','core_radius':1.7}, {'frame':28,'state':'quiet interval'}]
  return mask,frames,key
 mask=collect_mask(base,lambda x,y,g:g=='red')
 red=mask
 frames=[]
 for f in range(32):
  if f<=3:heart=1+f
  elif f<6:heart=0
  elif f<=9:heart=1+(f-6)
  else:heart=0
  branch=None; front=0
  if 10<=f<=13:branch='left';front=2+(f-10)*1.2
  elif 14<=f<=17:branch='right';front=2+(f-14)*1.2
  def rgb(x,y):
   p=(x,y); d=abs(x-16)+abs(y-16)
   if heart and d<=heart:return (246,54,39) if (x+y)%4 else (244,161,52)
   if branch:
    correct=(x<16) if branch=='left' else (x>16)
    radius=math.hypot(x-16,y-16)
    if correct and abs(radius-front)<=1.15:return (249,158,48) if (x+y)%3==0 else (240,45,37)
   return (31,5,12)
  frames.append(make_frame(mask,rgb))
 key=[{'frame':0,'state':'heartbeat one rises','heart_radius':1}, {'frame':3,'state':'heartbeat one peak','heart_radius':4}, {'frame':6,'state':'heartbeat two','heart_radius':1}, {'frame':9,'state':'heartbeat two peak','heart_radius':4}, {'frame':10,'state':'left red-gold branch wave','branch':'left'}, {'frame':14,'state':'right red-gold branch wave','branch':'right'}, {'frame':18,'state':'quiet interval'}]
 return mask,frames,key

def frames_frequency(base,enhanced=False,second=False):
 if not enhanced:
  stems=[((16,22),(16,17))]
  branches=[((16,17),(11,12)),((16,17),(16,9)),((16,17),(21,12))]
  segments=stems+branches
  area=lambda x,y: 9<=x<=23 and 8<=y<=24
  mask=collect_mask(base,lambda x,y,g:area(x,y) and min(distance_segment(x,y,*s)[0] for s in segments)<=1.65)
  frames=[]
  for f in range(32):
   if f<6:stem_len=.16+.84*f/5; branch_len=0
   elif f<14:stem_len=1; branch_len=(f-6)/7
   elif f<18:stem_len=1; branch_len=1
   elif f<26:stem_len=1; branch_len=max(.05,1-(f-18)/7)
   else:stem_len=max(.12,1-(f-26)/5); branch_len=0
   def rgb(x,y):
    best=min(((distance_segment(x,y,*s)[0],distance_segment(x,y,*s)[1],i) for i,s in enumerate(segments)),key=lambda z:z[0])
    d,u,i=best
    active=(i==0 and u<=stem_len and d<=1.55) or (i>0 and branch_len>0 and u<=branch_len and d<=1.45)
    if not active:return dim_source(base,x,y,.13)
    intensity=max(0,min(1,1-d/2))
    return (round(25+74*intensity),round(133+102*intensity),round(170+76*intensity))
   frames.append(make_frame(mask,rgb))
  key=[{'frame':0,'state':'single stem begins'}, {'frame':5,'state':'central ray reaches split'}, {'frame':6,'state':'three branches start','branch_length':0.0,'branch_count':3}, {'frame':10,'state':'three branches half-grown','branch_length':4/7,'branch_count':3}, {'frame':14,'state':'three full branches hold','branch_length':1.0,'branch_count':3}, {'frame':22,'state':'three branches rejoin','branch_length':3/7}, {'frame':28,'state':'single stem quiet'}]
  return mask,frames,key
 if second:
  starts=[(16,17)]*3; ends=[(12,12),(16,9),(20,12)]
  segments=list(zip(starts,ends))
  area=lambda x,y: 10<=x<=22 and 8<=y<=23
  mask=collect_mask(base,lambda x,y,g:area(x,y) and (min(distance_segment(x,y,*s)[0] for s in segments)<=1.8 or (abs(x-16)<=2 and abs(y-16)<=2)))
  symbol={(x,y) for y in range(14,19) for x in range(14,19) if abs(x-16)+abs(y-16)<=2 and base.getpixel((x,y))[3]==255}
  mask|=symbol
  frames=[]
  for f in range(32):
   if f<10:u=.88-.082*f; mode='converge'
   elif f<15:u=0.06;mode='symbol'
   elif f<26:u=.06+.078*(f-15);mode='scatter'
   else:u=1;mode='rest'
   def rgb(x,y):
    p=(x,y)
    if mode=='symbol' and p in symbol:return (106,233,248) if (x+y)%2 else (72,193,231)
    if mode in ('converge','scatter'):
     for i,s in enumerate(segments):
      d,t=distance_segment(x,y,*s)
      if d<=1.35 and abs(t-u)<=.17:
       return [(47,206,236),(127,219,249),(77,185,239)][i]
    return dim_source(base,x,y,.12)
   frames.append(make_frame(mask,rgb))
  key=[{'frame':0,'state':'three motes start at branches','u':.88,'branch_count':3}, {'frame':8,'state':'three motes converge','u':.224}, {'frame':10,'state':'three motes form central diamond rune','rune_pixels':len(symbol)}, {'frame':14,'state':'central rune hold'}, {'frame':20,'state':'three motes scatter','u':.45}, {'frame':26,'state':'quiet interval'}]
  return mask,frames,key
 # Enhanced frequency: two separate moving motes meet in center and spring apart.
 segments=[((16,18),(11,11)),((16,18),(21,11))]
 area=lambda x,y: 10<=x<=22 and 9<=y<=23
 mask=collect_mask(base,lambda x,y,g:area(x,y) and min(distance_segment(x,y,*s)[0] for s in segments)<=1.8)
 frames=[]
 for f in range(32):
  if f<10:u=.90-.082*f;mode='in'
  elif f<13:u=.06;mode='meet'
  elif f<23:u=.06+.084*(f-13);mode='out'
  else:u=1;mode='quiet'
  def rgb(x,y):
   if mode!='quiet':
    for i,s in enumerate(segments):
     d,t=distance_segment(x,y,*s)
     if d<=1.3 and abs(t-u)<=.17:
      if mode=='meet':return (128,242,247)
      return (49,204,231) if i==0 else (92,170,236)
   return dim_source(base,x,y,.12)
  frames.append(make_frame(mask,rgb))
 key=[{'frame':0,'state':'two separated branch motes','left_u':.9,'right_u':.9}, {'frame':8,'state':'two motes approach center','u':.244}, {'frame':10,'state':'two motes meet at center','u':.06}, {'frame':13,'state':'two motes bounce apart','u':.06}, {'frame':20,'state':'motes travel outward','u':.648}, {'frame':24,'state':'quiet interval'}]
 return mask,frames,key

def build_item(name,base):
 if name in ('extension_crystal','enhanced_extension_crystal','enhanced_extension_crystal_2'):
  mask=eye_mask(base); frames=[]; key=[]
  for f in range(CONFIG[name]['frames']):
   image,state=draw_eye(base,mask,name,f); frames.append(image)
   if name=='extension_crystal' and f in (0,6,12,15): key.append({'frame':f,'state':state['state'],'pupil_center':[state['x'],state['y']],'pupil_width':state['w'],'pupil_height':5,'iris_radius':state['iris'],'blink':state['blink']})
   elif name=='enhanced_extension_crystal' and f in (0,4,8,12,16,20,28): key.append({'frame':f,'state':state['state'],'pupil_center':[state['x'],state['y']],'pupil_width':state['w'],'pupil_height':3 if state['state']=='iris contracts' else 5,'iris_radius':state['iris'],'blink':state['blink']})
   elif name=='enhanced_extension_crystal_2' and f in (0,6,12,18,24,28): key.append({'frame':f,'state':state['state'],'pupil_center':[state['x'],state['y']],'pupil_width':state['w'],'pupil_height':5,'iris_radius':state['iris'],'blink':state['blink']})
  return mask,frames,key
 if name=='tuning_crystal':
  mask=star_mask(base); frames=[draw_star(base,mask,f) for f in range(24)]
  key=[{'frame':f,'state':s,'ray_length':star_length(f),'simultaneous_four_arms':True} for f,s in [(0,'compact core'),(6,'arms extending'),(8,'maximum length'),(11,'maximum hold'),(14,'retracting'),(17,'compact core')]]
  return mask,frames,key
 if name=='echo_pickaxe':return frames_pickaxe(base)
 if name=='echo_upgrade_smithing_template':return frames_template(base)
 if name=='echo_crystal':return frames_echo_chip(base)
 if name=='resonance_crystal':return frames_resonance(base,False)
 if name=='enhanced_resonance_crystal':return frames_resonance(base,True)
 if name=='frequency_crystal':return frames_frequency(base,False)
 if name=='enhanced_frequency_crystal':return frames_frequency(base,True,False)
 if name=='enhanced_frequency_crystal_2':return frames_frequency(base,True,True)
 raise ValueError(name)

def model_for(name,mask):
 baseline=json.loads((SOURCE_MODELS/f'{name}.json').read_text(encoding='utf-8-sig'))
 model=json.loads(json.dumps(baseline))
 model.setdefault('textures',{})['glow']=f'echopickaxe:item/{name}_glow'
 seen=set()
 for elem in model['elements']:
  face=elem['faces'].get('north')
  if not face:continue
  u,v=face['uv'][:2]; p=(round((u-.25)*2),round((v-.25)*2))
  if p not in mask:continue
  seen.add(p)
  for side in ('north','south'):
   data=elem['faces'][side]; data['texture']='#glow'
   data['forge_data']={'block_light':15,'sky_light':15,'ambient_occlusion':False}
 if seen!=mask:raise RuntimeError(f'{name} model misses coordinates {sorted(mask-seen)[:12]}')
 return model,len(seen)*2

def copy_1_6_snapshot(names):
 old_models=SOURCE/'base_models_1.6.0'; old_glow=SOURCE/'base_glow_1.6.0'; old_models.mkdir(parents=True,exist_ok=True);old_glow.mkdir(parents=True,exist_ok=True)
 for name in names:
  mod=MODELS/f'{name}.json'; snap=old_models/mod.name
  if mod.exists() and not snap.exists():shutil.copy2(mod,snap)
  for suffix in ('_glow.png','_glow.png.mcmeta'):
   p=TEXTURES/f'{name}{suffix}'; q=old_glow/p.name
   if p.exists() and not q.exists():shutil.copy2(p,q)

def export(name,base,mask,frames,config,key):
 strip=Image.new('RGBA',(SIZE,SIZE*len(frames)),(0,0,0,0))
 for i,frame in enumerate(frames):
  alpha=frame.getchannel('A')
  if set(alpha.getdata())-({0,255}):raise RuntimeError(f'{name}: alpha not binary in frame {i}')
  strip.alpha_composite(frame,(0,i*SIZE))
 strip.save(TEXTURES/f'{name}_glow.png',optimize=True)
 meta={'animation':{'width':SIZE,'height':SIZE,'frametime':config['ticks'],'interpolate':config['interp'],'frames':list(range(len(frames)))}}
 (TEXTURES/f'{name}_glow.png.mcmeta').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
 model,face_count=model_for(name,mask)
 (MODELS/f'{name}.json').write_text(json.dumps(model,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 return face_count

def phase_frames(name):
 return {
 'echo_pickaxe':[0,4,8,20], 'echo_upgrade_smithing_template':[0,10,20,28], 'echo_crystal':[0,8,16,24],
 'resonance_crystal':[0,3,7,14], 'enhanced_resonance_crystal':[0,7,15,22], 'frequency_crystal':[0,5,10,14],
 'enhanced_frequency_crystal':[0,8,10,18], 'enhanced_frequency_crystal_2':[0,8,11,20],
 'extension_crystal':[0,6,12,15], 'enhanced_extension_crystal':[0,8,16,28], 'enhanced_extension_crystal_2':[0,6,12,18], 'tuning_crystal':[0,6,8,17]
 }[name]

def compose_sprite(base,glow):
 im=base.copy()
 for y in range(SIZE):
  for x in range(SIZE):
   if glow.getpixel((x,y))[3]==255:im.putpixel((x,y),glow.getpixel((x,y)))
 return im

def main():
 names=list(CONFIG)
 VALID.mkdir(parents=True,exist_ok=True); SOURCE.mkdir(parents=True,exist_ok=True)
 copy_1_6_snapshot(names)
 manifest={'version':'1.7.0','frame_size':[SIZE,SIZE],'items':{},'backup_1_6':'artwork/source/structural-v1.7.0/base_models_1.6.0 + base_glow_1.6.0'}
 bases={}; masks={}; allframes={}; models_face_counts={}
 # Preserve and verify originals before any production output.
 for name in names:
  base=Image.open(SOURCE_BASE/f'{name}.png').convert('RGBA')
  if base.size!=(SIZE,SIZE):raise RuntimeError(f'{name} source is not 32x32')
  if set(base.getchannel('A').getdata())-({0,255}):raise RuntimeError(f'{name} source alpha is not binary')
  bases[name]=base
 for name,cfg in CONFIG.items():
  base=bases[name]; mask,frames,key=build_item(name,base)
  if not mask:raise RuntimeError(f'{name} empty mask')
  if any(base.getpixel(p)[3]!=255 for p in mask):raise RuntimeError(f'{name} mask enters transparent pixel')
  faces=export(name,base,mask,frames,cfg,key)
  masks[name]=mask;allframes[name]=frames;models_face_counts[name]=faces
  maskim=Image.new('RGBA',(32,32),(0,0,0,0))
  for x,y in mask:maskim.putpixel((x,y),(255,255,255,255))
  maskim.save(VALID/f'{name}-mask.png')
  groups={}
  for p in mask:
   g=pixel_group(base,*p) or 'structural'
   groups[g]=groups.get(g,0)+1
  frame_stats=[]
  for i,fr in enumerate(frames):
   pts=[p for p in mask if fr.getpixel(p)[3]==255]
   colors={fr.getpixel(p)[:3] for p in pts}
   frame_stats.append({'frame':i,'opaque_pixels':len(pts),'rgb_color_count':len(colors)})
  manifest['items'][name]={
   'motion':cfg['motion'],'mask_pixels':len(mask),'mask_percent':round(len(mask)*100/1024,2),
   'mask_coordinates':sorted([[x,y] for x,y in mask],key=lambda p:(p[1],p[0])),
   'palette_groups':groups,'frames':len(frames),'frametime_ticks':cfg['ticks'],
   'cycle_ticks':len(frames)*cfg['ticks'],'cycle_seconds':round(len(frames)*cfg['ticks']/20,2),
   'interpolate':cfg['interp'],'model_glow_faces':faces,'keyframes':key,
   'frame_signatures':frame_stats,
  }
  print(f'{name}: mask={len(mask)} faces={faces} frames={len(frames)} cycle={len(frames)*cfg["ticks"]*0.05:.2f}s interp={cfg["interp"]}')
 # 12-item masked-area overview.
 def mask_get(name):return Image.open(VALID/f'{name}-mask.png').convert('RGBA')
 sheet=Image.new('RGBA',(828,624),(46,51,59,255));
 for i,name in enumerate(names):
  x=12+(i%4)*204;y=12+(i//4)*204
  sheet.alpha_composite(mask_get(name).resize((192,192),Image.Resampling.NEAREST),(x,y))
 ImageDraw.Draw(sheet)
 sheet.save(VALID/'masks.png')
 # Animation preview sampled each game tick, blending RGB only where opted-in interpolate=true.
 cycle=math.lcm(*(len(allframes[n])*CONFIG[n]['ticks'] for n in names))
 gif=[]
 for tick in range(cycle):
  canvas=Image.new('RGB',(828,624),(46,51,59));d=ImageDraw.Draw(canvas)
  for i,name in enumerate(names):
   cfg=CONFIG[name];frames=allframes[name];idx=(tick//cfg['ticks'])%len(frames);nxt=(idx+1)%len(frames)
   glow=Image.blend(frames[idx],frames[nxt],(tick%cfg['ticks'])/cfg['ticks']) if cfg['interp'] else frames[idx]
   im=compose_sprite(bases[name],glow).resize((192,192),Image.Resampling.NEAREST)
   x=12+(i%4)*204;y=12+(i//4)*204
   canvas.paste(im,(x,y),im);d.text((x,y-9),name,fill='white')
  gif.append(canvas)
 gif[0].save(VALID/'emissive-items-preview.gif',save_all=True,append_images=gif[1:],duration=50,loop=0,optimize=True,disposal=2)
 # Chosen structural milestones, including nonuniform blink, node, motes, and ray-length events.
 cell=128;gap=10;left=150; row_h=174
 keyimg=Image.new('RGB',(left+4*(cell+gap),len(names)*row_h),(42,47,55)); dr=ImageDraw.Draw(keyimg)
 for row,name in enumerate(names):
  frames=allframes[name];samples=phase_frames(name);y=row*row_h
  dr.text((8,y+4),name,fill='white')
  for col,f in enumerate(samples):
   im=compose_sprite(bases[name],frames[f]).resize((cell,cell),Image.Resampling.NEAREST)
   x=left+col*(cell+gap);yy=y+20
   keyimg.paste(im,(x,yy),im)
   entry=manifest['items'][name];event=next((k['state'] for k in entry['keyframes'] if k['frame']==f),f'frame {f}')
   dr.text((x,yy+130),f'f{f} {event[:16]}',fill=(202,216,227))
 keyimg.save(VALID/'keyframes.png')
 (SOURCE/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 notes='''# Structural animation assets 1.7.0\n\nThe 1.6 base item PNGs are preserved as immutable inputs in `artwork/source/emissive-v1.6.0/base_textures/`; original 1.5 item models are the geometry/UV/display baseline in `artwork/source/emissive-v1.6.0/base_models/`. Before writing 1.7 resources, the generator snapshots the currently installed 1.6 models and glow strips to `base_models_1.6.0/` and `base_glow_1.6.0/`.\n\n`artwork/generate_structural_v1_7_0.py` writes 12 `*_glow.png` strips and `.mcmeta` files plus 12 models. It preserves base PNGs, model elements, UVs, display transforms, and side faces. Per-frame glow alpha is a fixed hard 0/255 mask over existing opaque coordinates. Only selected element north/south faces bind `#glow` with Forge block/sky light 15 and AO false; no parent, extra element, or overlay plane is introduced.\n\nThe three extension crystals use moving iris/pupil centers with tracked highlights, per-tier gaze/contract/blink/lock states. The tuning crystal animates one fixed union mask as a four-arm cross that contracts, expands simultaneously, holds, and retracts; bone-white shell pixels outside that cross remain on the base texture. Other items have distinct coordinate-driven actions recorded per-frame in `manifest.json`: sequential pickaxe handle nodes, paired crack flashes and motes; template rune stroke write/hold/erase; echo-crystal shard width/facet flip; resonance double beat and side releases; enhanced resonance core compression, branch sparks, and release; three-ray split/rejoin; two moving motes meeting/bouncing; three moving motes combining into a diamond rune and scattering.\n\nValidation artifacts: `artwork/validation/v1.7.0/keyframes.png` (selected phase sheet), `emissive-items-preview.gif` (one-tick playback with configured interpolation), `masks.png`, and individual mask PNGs. The preview lasts 96 ticks (4.8 seconds) and mirrors the per-item metadata. The exact imagegen motion reference and prompt are saved under this directory as `eye-star-motion-reference.png` and `design_prompt.md`; this reference did not become a game texture.\n'''
 (SOURCE/'generation-notes.md').write_text(notes,encoding='utf-8')
 print('Wrote',VALID/'emissive-items-preview.gif',VALID/'keyframes.png')

if __name__=='__main__':main()
