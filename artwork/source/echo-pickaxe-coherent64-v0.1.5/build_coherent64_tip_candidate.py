"""Review-only hand-authored coherent native64 tip/head transition for 0.1.5."""
import io,json,hashlib,zipfile
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[3]
SRC=Path(__file__).resolve().parent
OUT=ROOT/'artwork/validation/v0.1.5/draft'
COMMON=ROOT/'artwork/source/approved-reference-oct03-64/common64-unupgraded.png'
COMMON_SHA='0322211B247FBFD8D96321DB29856FFD93AA8F430038C2275C36DEDE2670B95C'
JAR12=ROOT/'jaysay-echo-tools-0.1.2.jar';SHA12='7312AE7B54F3DAD998815B7C7BD601B65DB1BED23A21CC7AA8448E40E082F495'
JAR14=ROOT/'jaysay-echo-tools-0.1.4.jar';SHA14='9A3D6C0D9B5485C397117CBF00C00C31DA04A339838831231EC5C31B552D67AF'
PREFIX='assets/echopickaxe/'
DARK=(22,28,36)
SPANS={12:(18,25),13:(15,26),14:(13,27),15:(12,28),16:(10,28),17:(10,28),
       18:(10,23),19:(10,20),20:(10,16),21:(10,15),22:(11,14),23:(12,14)}

def sha(b):return hashlib.sha256(b).hexdigest().upper()
def read_png(data):return Image.open(io.BytesIO(data)).convert('RGBA')
def readjar(z,name):return read_png(z.read(PREFIX+name))
def alpha(im):return {(x,y) for y in range(im.height) for x in range(im.width) if im.getpixel((x,y))[3]}
def components(mask,diagonal=False):
 ds=[(-1,0),(1,0),(0,-1),(0,1)]+([(-1,-1),(-1,1),(1,-1),(1,1)] if diagonal else [])
 unseen=set(mask);sizes=[]
 while unseen:
  p=unseen.pop();stack=[p];n=0
  while stack:
   x,y=stack.pop();n+=1
   for dx,dy in ds:
    q=(x+dx,y+dy)
    if q in unseen:unseen.remove(q);stack.append(q)
  sizes.append(n)
 return sorted(sizes,reverse=True)
def load_components():
 p=json.loads((ROOT/'artwork/source/approved-reference-oct03-64/native64-component-map.json').read_text(encoding='utf-8'))
 return {n:{(x,y) for t in part['tiers'] for x,y,*_ in t['texels']} for n,part in p['components'].items()}
def nearest_local_dark(im,x,y):
 p=im.load(); options=[]
 for yy in range(max(0,y-6),min(64,y+7)):
  for xx in range(max(0,x-6),min(64,x+7)):
   r,g,b,a=p[xx,yy]
   if a and r<90 and g<130 and b<160 and not (r>g*1.4):
    options.append(((xx-x)**2+(yy-y)**2,yy,xx,(r,g,b,255)))
 return min(options)[3] if options else (0,15,22,255)
def render_hook(common):
 out=common.copy();dst=out.load(); native={}
 for y,(left,right) in SPANS.items():
  for x in range(left,right+1):
   native[(x,y)]=nearest_local_dark(common,x,y)
 # Small, shaped crystal planes break up the dark hook without changing its
 # frozen contour. These compact facets use only colors sampled from common64.
 facets={
  (24,13):(0,30,43,255),(25,14):(0,30,43,255),(24,15):(0,12,18,255),
  (22,16):(0,30,43,255),(21,17):(0,12,18,255),(20,18):(0,30,43,255),
  (18,18):(0,30,43,255),(17,19):(0,12,18,255),(15,20):(0,30,43,255),
  (13,21):(0,30,43,255),(12,22):(0,12,18,255),
 }
 native.update({p:c for p,c in facets.items() if p in native})
 # One irregular fissure with two short branches, visually continuous with the
 # head's cyan seams rather than a pair of parallel stripes.
 fissure=[(20,12),(19,13),(19,14),(18,15),(17,15),(16,16),(15,17),
          (14,18),(14,19),(13,20),(13,21),(12,22)]
 branches=[[(18,15),(18,14)],[(15,17),(15,18)]]
 cyan_mid=(0,142,154,255);cyan_bright=(0,203,216,255);cyan_deep=(0,131,159,255)
 for i,p in enumerate(fissure):
  if p in native:native[p]=cyan_bright if i in (0,5,10) else cyan_mid
 for branch in branches:
  for p in branch:
   if p in native:native[p]=cyan_deep
 # Preserve common64 color outside the authored patch; keep deliberate native64
 # shades inside it and add opaque texels where the old inner arc had been severed.
 for p,rgba in native.items():dst[p[0],p[1]]=rgba
 return out,set(native),native,fissure,branches,len(facets)

def draw_comp(im,bg):
 c=Image.new('RGBA',im.size,bg+(255,));c.alpha_composite(im);return c.convert('RGB')
def panel(states,scale,background,path):
 # Keep full object visible at each scale for silhouette review.
 crop=(0,0,64,64)
 w,h=crop[2]-crop[0],crop[3]-crop[1]
 sw,sh=w*scale,h*scale
 cw=max(190,sw+22);ch=sh+35
 board=Image.new('RGB',(16+cw*len(states),20+ch*2),(245,245,245));d=ImageDraw.Draw(board);font=ImageFont.load_default()
 for row,bg in enumerate(((255,255,255),DARK)):
  y=16+row*ch;d.text((4,y-11),'white background' if row==0 else 'dark background',fill=(12,14,17),font=font)
  for i,(label,img) in enumerate(states):
   x=8+i*cw;d.text((x+3,y),label,fill=(12,14,17),font=font)
   piece=img.crop(crop) if scale>1 else img
   rgb=draw_comp(piece,bg).resize((sw,sh),Image.Resampling.NEAREST)
   board.paste(rgb,(x+3,y+15))
 board.save(path)
def main():
 OUT.mkdir(parents=True,exist_ok=True)
 assert sha(COMMON.read_bytes())==COMMON_SHA and sha(JAR12.read_bytes())==SHA12 and sha(JAR14.read_bytes())==SHA14
 common=read_png(COMMON.read_bytes());assert common.size==(64,64)
 bare,hook_mask,hook_colors,fissure,branches,facet_count=render_hook(common)
 old_mask_image=read_png((ROOT/'artwork/validation/v0.1.4/artagentmask.png').read_bytes())
 old_mask=alpha(old_mask_image)
 comps=load_components()
 for module in ('frequency','tuning','extension'):
  assert not hook_mask&comps[module],f'hook overlaps {module} tier texels'
  assert not old_mask&comps[module],f'legacy cleanup intersects {module} tier texels'
 with zipfile.ZipFile(JAR12) as z12,zipfile.ZipFile(JAR14) as z14:
  old32=read_png(z12.read(PREFIX+'textures/item/echo_pickaxe.png')).resize((64,64),Image.Resampling.NEAREST)
  old_v24=readjar(z14,'textures/item/echo_pickaxe_v024.png');old_v31=readjar(z14,'textures/item/echo_pickaxe_v031.png')
  v24=old_v24.copy();v31=old_v31.copy()
  # Remove old coarse hook only where it differs from approved common64 inside the
  # historical tip area, then install the complete new native hook plus its bridge.
  observed_old_tip={p for p in old_mask if old_v31.getpixel(p)!=common.getpixel(p)}
  legacy_native={(x,y) for y in range(12,25) for x in range(8,29) if old32.getpixel((x,y))[3]}
  replacement=hook_mask | old_mask | observed_old_tip | legacy_native
  assert not replacement&comps['frequency'] and not replacement&comps['tuning'] and not replacement&comps['extension']
  for im in (v24,v31):
   px=im.load()
   for x,y in replacement:px[x,y]=bare.getpixel((x,y))
  bare.save(OUT/'bare-coherent64.png');v24.save(OUT/'frequency-III-tip-repaired.png')
  v31.save(OUT/'res0-v031-tip-repaired.png');readjar(z14,'textures/item/echo_pickaxe_v095.png').save(OUT/'resII-v095-unchanged.png')
  # Explicit source map and organic mask are only for this draft; no deployment.
  mm=Image.new('RGBA',(64,64),(0,0,0,0))
  for p in replacement:mm.putpixel(p,(255,190,45,255))
  mm.save(SRC/'replacement-mask-draft.png')
  states=[('bare common64',bare),('frequency III',v24),('res0 FIII/TI/EIII',v31),('resII full max',readjar(z14,'textures/item/echo_pickaxe_v095.png'))]
  for scale in (1,4,8):panel(states,scale,(255,255,255),OUT/f'coherent64-review-{scale}x-white-dark.png')
  doc={'schema':1,'status':'draft-for-root-review','baselineJarSha256':SHA14,'common64Sha256':COMMON_SHA,
    'design':'Full native64 hand-drawn dark sculk/cyan hook, following original downward-curved recognition while matching approved common64 grain. No old RGBA is copied; only silhouette coordinates guide the contour. Red is absent.',
    'rowSpans':{str(y):[lo,hi] for y,(lo,hi) in SPANS.items()},
    'replacementMask':'replacement-mask-draft.png','replacementMaskTexels':len(replacement),
    'hookDrawnTexels':len(hook_mask),'hookNewOpaqueTexels':sum(1 for p in hook_mask if not common.getpixel(p)[3]),
    'oldCoarseTipPixelsCleared':len(observed_old_tip),'old32ContourGuideOnly':len(legacy_native),
    'cyanFissurePath':[list(p) for p in fissure],'cyanBranches':[[list(p) for p in branch] for branch in branches],'facetPixels':facet_count,'moduleOverlap':{n:len(replacement&comps[n]) for n in ('frequency','tuning','extension')},
    'opaqueTexels':len(alpha(bare)),'fourConnectedComponents':components(alpha(bare)),'eightConnectedComponents':components(alpha(bare),True),
    'bridgeWidthByRow':{str(y):sum(1 for x in range(10,31) if (x,y) in alpha(bare)) for y in range(16,19)},
    'allOpaqueTexelRgba':[[x,y,list(bare.getpixel((x,y)))] for y in range(64) for x in range(64) if bare.getpixel((x,y))[3]]}
  (SRC/'coherent64-transition-map.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
  # Side-by-side close-up: rejected 0.1.4 seam vs common64 and the current hook,
  # with the repair area outlined in amber on candidate only.
  cur=Image.open(ROOT/'artwork/source/echo-pickaxe-native64-v0.1.4/ordinary-native64-approved.png').convert('RGBA')
  plate=Image.new('RGB',(3*280,310),(255,255,255));d=ImageDraw.Draw(plate);font=ImageFont.load_default()
  for i,(label,img) in enumerate([('0.1.4 old clipped hook',cur),('common64 body',common),('coherent64 hook draft',bare)]):
   x=i*280+8;d.text((x,5),label,fill=(0,0,0),font=font)
   crop=img.crop((8,7,38,27));plate.paste(draw_comp(crop,(255,255,255)).resize((240,160),Image.Resampling.NEAREST),(x,24))
   if i==2:d.rectangle((x+2*8,24+5*8,x+22*8,24+17*8),outline=(244,178,0),width=2)
  plate.save(OUT/'hook-gap-repair-closeup.png')
  print(f'PASS draft: replacement={len(replacement)}, hook={len(hook_mask)}, opaque={len(alpha(bare))}, components4/8={components(alpha(bare))}/{components(alpha(bare),True)}; files={OUT}')
if __name__=='__main__':main()
