from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import hashlib, json, shutil

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[3]
SRC=PROJECT/'src/main/resources/assets/echopickaxe/textures/item/echo_pickaxe.png'
OUT=HERE/'drafts'
VAL=PROJECT/'artwork/validation/v0.1.12/structure-redesign'
OUT.mkdir(parents=True,exist_ok=True); VAL.mkdir(parents=True,exist_ok=True)
EXPECTED='296326965171A658F9CD40E0C9C42FB3ABF5B1094AF9EFB0005096061C1711F5'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest().upper()
if sha(SRC)!=EXPECTED: raise SystemExit(f'ordinary0 anchor mismatch {sha(SRC)}')
base=Image.open(SRC).convert('RGBA')
if base.size!=(64,64): raise SystemExit(f'expected 64x64, got {base.size}')

def bone_points(region):
 x0,y0,x1,y1=region; pts=[]
 for y in range(y0,y1):
  for x in range(x0,x1):
   r,g,b,a=base.getpixel((x,y))
   if a and r>170 and g>135 and b>110 and r-g<90: pts.append((x,y))
 return pts

def put(im, coords, color, allow_new=False):
 p=im.load()
 for x,y in coords:
  if not (0<=x<64 and 0<=y<64): raise ValueError((x,y))
  if p[x,y][3]==0 and not allow_new: raise ValueError(f'new alpha not planned: {(x,y)}')
  p[x,y]=(*color,255 if allow_new else p[x,y][3])

images={'ordinary0':base.copy()}
# Red resonance blade. Level I replaces all 43 pale pixels with an angular, two-plane red crystal.
red_region=(17,5,39,21); red_bones=bone_points(red_region)
red_i=base.copy();
red_outer={(21,6),(18,7),(19,7),(23,8),(24,9),(27,10),(29,11),(30,12),(31,13),(32,14),(32,15),(33,16),(33,17),(33,18)}
red_inner={(22,6),(23,6),(24,7),(25,7),(26,8),(27,9),(28,10),(29,10),(30,11),(31,12),(31,14),(32,16),(34,17)}
for pt in red_bones:
 if pt in red_outer: c=(255,116,112)       # sharp coral edge plane
 elif pt in red_inner: c=(101,13,28)       # cut shadow bevel
 else: c=(203,31,48)                       # saturated crystal face
 put(red_i,[pt],c)
# Sharpen the terminal tip without widening or rounding it.
put(red_i,[(18,7)],(83,8,21))
images['resonance1']=red_i

# Level II grows a stepped ridge into existing dark pixels on the blade's back/outer contour.
# The original leftmost tip stays dark and pointed. Cyan guide pixels immediately along the ridge are reassigned.
red_crest_dark={(21,5),(22,5),(23,5),(24,6),(25,6),(26,6),(27,7),(28,7),(29,8),(30,8),(30,9),(31,9),(31,10),(32,10),(32,11),(33,12),(33,13),(34,14)}
red_plate_main={(18,6),(19,6),(20,6),(18,8),(19,8),(20,8),(21,8),(22,8),(23,8),(24,9),(25,9),(26,10),(27,10),(28,11),(29,12),(30,12),(30,13),(31,14),(31,15),(32,16)}
red_ridge_highlights={(22,5),(25,6),(28,7),(30,8),(32,10),(33,12)}
red_ii=red_i.copy()
# A connected ruby slab fills the dark body immediately behind the complete bone-derived blade.
put(red_ii,red_crest_dark,(113,13,30))
put(red_ii,red_plate_main,(190,29,45))
# Bright main facets and deep seams form a stepped crystalline ridge; the terminal tip remains I's narrow point.
put(red_ii,red_ridge_highlights,(255,119,117))
put(red_ii,[(24,8),(27,9),(29,11),(30,12),(32,13)],(84,9,25))
images['resonance2']=red_ii

# One 13-pixel thin four-arm star (7x7 span). Diagonal cells stay dark to separate the arms.
star_center=(43,16)
star_arms=[(43,16),(43,15),(43,14),(43,13),(43,17),(43,18),(43,19),
           (42,16),(41,16),(40,16),(44,16),(45,16),(46,16)]
star_dark=[(42,15),(44,15),(42,17),(44,17),
           (41,14),(45,14),(41,18),(45,18),
           (40,13),(46,13),(40,19),(46,19)]
star=base.copy()
put(star,star_dark,(5,35,55))
put(star,[(43,16)],(255,255,248))
put(star,[(43,15),(43,17),(42,16),(44,16)],(206,248,255))
put(star,[(43,14),(43,13),(43,18),(43,19),(41,16),(40,16),(45,16),(46,16)],(126,218,246))
# Any original warm-bone pixels in the node not already on the cross become cool dark facets.
for pt in bone_points((39,13,47,21)):
 if base.getpixel(pt)[:3]!=(255,255,248) and pt not in star_arms:
  put(star,[pt],(18,84,112))
images['tuning1']=star

# Jade tail module. All 13 pale clasp pixels become deliberate shell/cradle facets.
tail_region=(4,49,17,59); tail_bones=bone_points(tail_region)
ext1=base.copy()
# Cut shell planes on the existing clasp, with no radial fill.
seat_shadow={(7,50),(6,51),(6,52),(9,54),(14,54),(13,55),(12,56),(11,57)}
seat_edge={(8,50),(7,51),(7,52),(13,56)}
for pt in tail_bones:
 if pt in seat_shadow: c=(12,83,48)
 elif pt in seat_edge: c=(39,160,79)
 else: c=(23,119,62)
 put(ext1,[pt],c)
# Angular jade setting and a clearly readable green iris with a vertical slit pupil.
# These explicit dark planes break the bone clasp's former circular reading.
put(ext1,[(6,50),(8,49),(8,51),(8,52),(12,55),(14,56),(10,57)],(4,48,30))
iris_ring=[(10,51),(9,52),(11,52),(9,53),(11,53),(9,54),(11,54),(9,55),(11,55),(10,56)]
put(ext1,iris_ring,(45,186,82))
put(ext1,[(11,52),(11,54),(10,51),(10,56)],(108,231,117))
put(ext1,[(9,52)],(212,255,182))
# Explicit 1x4 near-black pupil coordinates, written last so shell facets cannot cover them.
pupil=[(10,52),(10,53),(10,54),(10,55)]
put(ext1,pupil,(1,8,10))
put(ext1,[(9,52)],(226,255,195))
images['extension1']=ext1

# Level II adds two separated short cradle prongs and extra cut planes, leaving dark gaps.
ext2=ext1.copy()
put(ext2,[(5,51),(5,52),(15,54),(15,55)],(15,98,54))
put(ext2,[(5,50),(15,56)],(24,127,66),allow_new=True)
put(ext2,[(5,51),(15,54)],(52,177,89))
put(ext2,[(8,49),(9,49)],(14,90,55))
put(ext2,[(8,51),(14,56)],(35,142,73))
images['extension2']=ext2

# Level III adds a third upper cradle facet and a second iris layer around the stable slit pupil.
ext3=ext2.copy()
put(ext3,[(10,49),(11,49)],(19,112,64))
put(ext3,[(10,49)],(72,207,103))
put(ext3,[(8,52),(12,52),(8,54),(12,54)],(77,205,104))
put(ext3,[(11,51),(11,55)],(132,238,140))
put(ext3,[(9,51)],(191,255,176))
images['extension3']=ext3

# Purple split blade. The pale edge is fully converted into a continuous curved crystal wedge.
# The wedge thickens toward the inner side by 2-3 texels and ends in a single sharp tip.
purple_region=(48,20,61,36); purple_bones=bone_points(purple_region)
purple_palette={'shadow':(47,24,100),'deep':(77,39,143),'face':(135,79,194),'bright':(198,139,236),'glint':(235,207,255)}
purple_edge=[(50,22),(51,22),(52,23),(52,24),(54,25),(55,26),(56,27),(56,28),(57,29),(57,30),(59,31),(59,32),(59,33),(59,34)]
# A curved inner lobe grows from the blade body and tapers to a sharp inward point.
purple_lobe=[(53,27),(52,28),(53,28),(51,29),(52,29),(53,29),(52,30),(53,30),(54,31)]
split1=base.copy()
# Crystalline cross-section planes on the original bone edge.
for i,pt in enumerate(purple_bones):
 if pt in {(49,22),(50,23),(51,23),(50,24),(51,24),(51,25),(53,26),(54,27),(55,28),(56,29),(57,31),(58,32),(58,33)}: c=purple_palette['bright']
 elif pt in {(50,22),(52,25),(54,26),(55,27),(56,30),(57,32)}: c=purple_palette['shadow']
 else: c=purple_palette['face']
 put(split1,[pt],c)
# This is a solid material wedge, not an outline beam; dark backing and face planes keep depth.
for pt in purple_edge: put(split1,[pt],purple_palette['deep'])
for pt in [(51,22),(52,23),(55,26),(57,29),(58,31)]: put(split1,[pt],purple_palette['bright'])
put(split1,purple_lobe,purple_palette['face'],allow_new=True)
put(split1,[(52,28),(51,29),(52,30)],purple_palette['deep'],allow_new=True)
put(split1,[(53,28),(53,29),(53,30)],purple_palette['bright'])
put(split1,[(54,31)],purple_palette['glint'],allow_new=True)
# Terminal pixel stays dark-violet and sharp.
put(split1,[(59,34)],purple_palette['shadow'])
images['split1']=split1

# Level II cuts two separated inset facets into the back of the same continuous wedge.
split2=split1.copy()
segment_a=[(50,23),(51,24),(52,25)]
segment_b=[(54,26),(55,27),(56,28)]
put(split2,segment_a,(233,188,255))
put(split2,[(53,25)],purple_palette['shadow'])
put(split2,segment_b,(210,157,246))
put(split2,[(56,29)],purple_palette['shadow'])
# Facet breaks cross the two inset plates; the curved lobe remains a continuous sharp blade.
put(split2,[(52,29),(53,29)],(184,116,225))
images['split2']=split2

# Level III adds a third distal inset facet and a second bevel on the lobe.
split3=split2.copy()
segment_c=[(57,30),(58,31),(59,32)]
put(split3,segment_c,(238,211,255))
put(split3,[(58,30)],purple_palette['shadow'])
put(split3,[(51,29),(53,29),(54,31)],(222,176,249))
put(split3,[(59,33)],(217,168,246))
images['split3']=split3

# Master proof composes each of the four modules at its maximum tier.

master=base.copy(); mp=master.load()
for key in ('resonance2','split3','tuning1','extension3'):
 q=images[key].load()
 for y in range(64):
  for x in range(64):
   if q[x,y]!=base.getpixel((x,y)): mp[x,y]=q[x,y]
images['all_max']=master

# Store PNGs. Ordinary is always copied byte-for-byte.
for key,im in images.items():
 if key=='ordinary0': continue
 im.save(OUT/f'{key}.png',format='PNG',optimize=False)
shutil.copyfile(SRC,OUT/'ordinary0.png')

# Exact per-state diffs, hashes, module bone coverage and added/changed area.
regions={'resonance':{'xyxyHalfOpen':[17,5,39,21],'states':['resonance1','resonance2']},
         'tuning':{'xyxyHalfOpen':[39,13,47,21],'states':['tuning1']},
         'extension':{'xyxyHalfOpen':[4,49,17,59],'states':['extension1','extension2','extension3']},
         'split':{'xyxyHalfOpen':[48,20,61,36],'states':['split1','split2','split3']}}
manifest={'base':{'path':'ordinary0.png','sha256':EXPECTED,'bytes':(OUT/'ordinary0.png').stat().st_size,'size':[64,64]},
          'purpleStructure':{'description':'Continuous curved crystal wedge with a curved inner lobe projecting 2-3 native pixels; higher tiers add two then three separated inset facets.', 'innerLobeCoordinates':[list(q) for q in purple_lobe], 'I':'complete bone edge plus solid dark/mid/bright wedge', 'II':'two separated inset facets on the same continuous blade', 'III':'third distal inset facet and second lobe bevel'},
          'tierRule':'Every active I tier replaces all pale-bone pixels of its component; higher tiers change explicit facet/cradle/star structures, not percentage fills.',
          'jadePupilCoordinates':[list(q) for q in pupil],
          'moduleRegions':regions,'states':{}}
for module,spec in regions.items():
 x0,y0,x1,y1=spec['xyxyHalfOpen']; bone=bone_points((x0,y0,x1,y1))
 spec['paleBoneCoordinates']=[list(q) for q in bone]; spec['originalPaleBonePixelCount']=len(bone); spec['perTierBoneCoverage']={}
 for key in spec['states']:
  state=Image.open(OUT/f'{key}.png').convert('RGBA')
  cov=sum(state.getpixel(pt)!=base.getpixel(pt) for pt in bone)
  spec['perTierBoneCoverage'][key]={'covered':cov,'total':len(bone),'ratio':cov/len(bone) if bone else 1.0}
for key in images:
 im=Image.open(OUT/f'{key}.png').convert('RGBA'); diffs=[]; alpha=[]
 for y in range(64):
  for x in range(64):
   a=base.getpixel((x,y)); b=im.getpixel((x,y))
   if a!=b: diffs.append([x,y,list(b)])
   if a[3]!=b[3]: alpha.append([x,y,a[3],b[3]])
 manifest['states'][key]={'path':f'{key}.png','sha256':sha(OUT/f'{key}.png'),'bytes':(OUT/f'{key}.png').stat().st_size,
                          'size':[64,64],'changedPixelCount':len(diffs),'alphaChanges':alpha,'diffPixels':diffs}
# Module edit masks are the union of that module's active-tier diff coordinates.
for module,spec in regions.items():
 coords=set()
 for state_key in spec['states']:
  coords.update((pt[0],pt[1]) for pt in manifest['states'][state_key]['diffPixels'])
 spec['editCoordinates']=[list(q) for q in sorted(coords,key=lambda q:(q[1],q[0]))]
# Record relative tier geometry deltas for human review.
def pairwise_count(a,b):
 ia=Image.open(OUT/f'{a}.png').convert('RGBA'); ib=Image.open(OUT/f'{b}.png').convert('RGBA')
 return sum(ia.getpixel((x,y))!=ib.getpixel((x,y)) for y in range(64) for x in range(64))
manifest['tierToTierChangedPixelCounts']={'resonance1->resonance2':pairwise_count('resonance1','resonance2'),'split1->split2':pairwise_count('split1','split2'),'split2->split3':pairwise_count('split2','split3'),'extension1->extension2':pairwise_count('extension1','extension2'),'extension2->extension3':pairwise_count('extension2','extension3')}
(VAL/'pixel-diffs-and-hashes.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

# Readable 4x white/dark comparison panels.
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',19)
items=[('ordinary0','普通'),('resonance1','共振 I'),('resonance2','共振 II'),('split1','分频 I'),('split2','分频 II'),('split3','分频 III'),('tuning1','调谐 I'),('extension1','延展 I'),('extension2','延展 II'),('extension3','延展 III'),('all_max','全部满级')]
def sheet(fname,bg,scale=4,cols=4):
 cellw=260; cellh=340; rows=(len(items)+cols-1)//cols
 out=Image.new('RGB',(cols*cellw,rows*cellh),bg); d=ImageDraw.Draw(out)
 for i,(key,label) in enumerate(items):
  col=i%cols;row=i//cols;x=col*cellw+(cellw-64*scale)//2;y=row*cellh+4
  icon=Image.open(OUT/f'{key}.png').convert('RGBA').resize((64*scale,64*scale),Image.Resampling.NEAREST)
  out.paste(icon,(x,y),icon);d.text((col*cellw+cellw//2,y+64*scale+22),label,font=font,fill=(25,28,31) if bg==(255,255,255) else (243,245,247),anchor='mm')
 out.save(VAL/fname)
for bg,name in [((255,255,255),'tiers-white-4x.png'),((25,29,36),'tiers-dark-4x.png')]: sheet(name,bg)
# Actual 16/32 texture downsamples, nearest-upscaled only for convenient review.
for size in (16,32):
 cellw=220;cellh=185;cols=4;rows=(len(items)+cols-1)//cols
 out=Image.new('RGB',(cols*cellw,rows*cellh),(25,29,36));d=ImageDraw.Draw(out)
 for i,(key,label) in enumerate(items):
  col=i%cols;row=i//cols;x=col*cellw+(cellw-128)//2;y=row*cellh+4
  icon=Image.open(OUT/f'{key}.png').convert('RGBA').resize((size,size),Image.Resampling.NEAREST).resize((128,128),Image.Resampling.NEAREST)
  out.paste(icon,(x,y),icon);d.text((col*cellw+cellw//2,y+145),f'{label} {size}',font=font,fill=(242,244,247),anchor='mm')
 out.save(VAL/f'preview-{size}px.png')
print('ordinary0',EXPECTED,'bytes',(OUT/'ordinary0.png').stat().st_size)
print('written',', '.join(f'{k}:{manifest["states"][k]["changedPixelCount"]}' for k in images))
