from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import hashlib, json, shutil

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
SRC = PROJECT / 'src/main/resources/assets/echopickaxe/textures/item/echo_pickaxe.png'
VAL = PROJECT / 'artwork/validation/v0.1.12/enhanced-components'
EXPECTED = '296326965171A658F9CD40E0C9C42FB3ABF5B1094AF9EFB0005096061C1711F5'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()

if sha(SRC) != EXPECTED:
    raise SystemExit(f'ordinary0 anchor mismatch: {sha(SRC)}')
base = Image.open(SRC).convert('RGBA')
if base.size != (64, 64):
    raise SystemExit(f'expected 64x64 base, got {base.size}')

def bone_pixels(region):
    x0,y0,x1,y1=region; pts=[]
    for y in range(y0,y1):
        for x in range(x0,x1):
            r,g,b,a=base.getpixel((x,y))
            if a and r>170 and g>135 and b>110 and r-g<90: pts.append((x,y))
    return pts

def facet_mask(region):
    """Bone blade plus its adjacent dark interior pixels; never touch transparent outline/highlights."""
    bones=bone_pixels(region); bm=set(bones); candidates=set(bm)
    for x,y in bones:
        for dy in (-1,0,1):
            for dx in (-1,0,1):
                xx,yy=x+dx,y+dy
                if xx<0 or yy<0 or xx>=64 or yy>=64 or (xx,yy) in bm: continue
                r,g,b,a=base.getpixel((xx,yy))
                # Existing dark body pixels only: preserve cyan circuitry, pale outlines, and empty silhouette.
                if a and max(r,g,b)<=115 and sum(base.getpixel((xx+ox,yy+oy))[3]>0 for oy in (-1,0,1) for ox in (-1,0,1) if 0<=xx+ox<64 and 0<=yy+oy<64)>=6: candidates.add((xx,yy))
    return sorted(candidates,key=lambda q:(q[1],q[0]))

def crystal_variant(region, palette, extra_fraction):
    im=base.copy(); px=im.load(); coords=facet_mask(region); bones=set(bone_pixels(region))
    extras=[q for q in coords if q not in bones]; n=round(len(extras)*extra_fraction)
    # Every tier replaces the complete pale blade. Higher tiers add only adjacent dark crystal facets.
    chosen=sorted(bones)+extras[:n]
    for i,(x,y) in enumerate(chosen):
        r,g,b,a=base.getpixel((x,y)); is_bone=(r>170 and g>135 and b>110 and r-g<90)
        # Rich shadow bed on the former pale facet, saturated face on its inner dark extension.

        if is_bone: color=palette[2 if (x+y)%3 else 3]
        else:
            # Alternating bevel planes create a crisp faceted crystal bed under the colored blade.
            color=palette[0] if (x+y)%3 else palette[1]
        px[x,y]=(*color,a)
    return im

red=[(48,11,20),(126,24,31),(207,49,51),(255,121,105),(255,173,159)]
purple=[(25,17,57),(59,35,112),(116,68,179),(185,127,225),(237,206,255)]
images={'ordinary0':base.copy()}
for name,f in [('resonance1',0.0),('resonance2',1.0)]: images[name]=crystal_variant((17,5,39,21),red,f)
for name,f in [('split1',0.0),('split2',.55),('split3',1.0)]: images[name]=crystal_variant((48,20,61,36),purple,f)
# Tiny hue-tinted edge glints; each point is inside the module's existing opaque crystal mask.
def add_glints(key, coords, color):
    im=images[key].copy(); p=im.load()
    for x,y in coords:
        if p[x,y][3]: p[x,y]=(*color,p[x,y][3])
    images[key]=im
red_glints=[(25,7),(29,10),(33,15)]
for key,coords in [('resonance1',red_glints[:1]),('resonance2',red_glints)]: add_glints(key,coords,red[4])
purple_glints=[(51,24),(55,28),(58,32)]
for key,coords in [('split1',purple_glints[:1]),('split2',purple_glints[:2]),('split3',purple_glints)]: add_glints(key,coords,purple[4])
# Four-point ice star at the original node, with one luminous center and fine cardinal tips.
im=base.copy();p=im.load()
star=[((41,15),(103,215,233)),((42,14),(183,246,255)),((42,15),(255,255,246)),((43,15),(216,251,255)),((42,16),(158,231,249)),((41,14),(135,222,245)),((43,14),(167,237,255)),((41,16),(126,216,240)),((43,16),(154,226,245)),((42,13),(195,242,255)),((42,17),(174,231,250)),((40,15),(121,215,236)),((44,15),(151,229,249))]
for (x,y),c in star:
    if p[x,y][3]: p[x,y]=(*c,p[x,y][3])
# Convert every pale bone pixel in the central node footprint into an icy star facet.
for x,y in bone_pixels((39,13,47,20)):
    if p[x,y][3]: p[x,y]=(183,238,252,p[x,y][3])
images['tuning1']=im
# Green jade eye uses the existing cyan tail crystal and nearby dark facets; clasp pixels stay untouched.
im=base.copy();p=im.load();pts=[]
for y in range(50,59):
    for x in range(5,16):
        r,g,b,a=base.getpixel((x,y))
        if a and g>r*1.12 and b>r*1.08 and g>55: pts.append((x,y,(r,g,b,a)))
# The green upgrade owns the complete circular tail module, including its pale bone clasp/guard.
jade=set((x,y) for x,y,_ in pts) | set(bone_pixels((4,49,16,59)))
for x,y,_ in pts:
    for dy in (-1,0,1):
        for dx in (-1,0,1):
            xx,yy=x+dx,y+dy
            if 0<=xx<64 and 0<=yy<64 and base.getpixel((xx,yy))[3]:
                r,g,b,a=base.getpixel((xx,yy))
                if max(r,g,b)<145 and not (r>g*1.2 and r>b*1.1): jade.add((xx,yy))
jade_order=sorted(jade,key=lambda q:(abs(q[0]-10)+abs(q[1]-54),q[1],q[0]))
def jade_variant(level):
    im=base.copy(); p=im.load(); fraction={1:.48,2:.77,3:1.0}[level]
    bones=set(bone_pixels((4,49,16,59))); extras=[q for q in jade_order if q not in bones]
    coords=sorted(bones)+(extras if level==1 else extras[:max(1,round(len(extras)*fraction))])
    for x,y in coords:
        d=abs(x-10)+abs(y-54); r,g,b,a=base.getpixel((x,y))
        if d==0: c=(230,255,206) if level==3 else (143,247,164) if level==2 else (106,222,139)
        elif d<=1: c=(100,224,132) if level>=2 else (44,167,94)
        elif d<=3: c=(31,151,86) if level>=2 else (17,111,67)
        else: c=(10,77,53)
        p[x,y]=(*c,a)
    return im
for level in (1,2,3): images[f'extension{level}']=jade_variant(level)
# All max combines separate localized upgrade diffs from base.
combo=base.copy();p=combo.load()
for key in ('resonance2','split3','tuning1','extension3'):
    q=images[key].load()
    for y in range(64):
        for x in range(64):
            if q[x,y]!=base.getpixel((x,y)): p[x,y]=q[x,y]
images['all_max']=combo
# Store all images except ordinary0 first; that one is copied byte-for-byte last.
for key,im in images.items():
    if key!='ordinary0': im.save(ROOT/f'{key}.png',format='PNG',optimize=False)
shutil.copyfile(SRC,ROOT/'ordinary0.png')
assert sha(ROOT/'ordinary0.png')==EXPECTED

# Per-state exact pixel masks relative to ordinary0 and content hashes.
manifest={'base':{'path':'ordinary0.png','sha256':EXPECTED,'bytes':(ROOT/'ordinary0.png').stat().st_size,'size':[64,64]},'states':{}}
manifest['moduleReplacementRegions']={
 'resonance':{'xyxyHalfOpen':[17,5,39,21],'states':['resonance1','resonance2']},
 'split':{'xyxyHalfOpen':[48,20,61,36],'states':['split1','split2','split3']},
 'tuning':{'xyxyHalfOpen':[39,13,47,20],'states':['tuning1']},
 'extension':{'xyxyHalfOpen':[4,49,16,59],'states':['extension1','extension2','extension3']}
}
manifest['tierRule']='At level I, recolor every original pale-bone pixel in the moduleReplacementRegions; higher levels add facets only within the existing opaque silhouette.'
for module,spec in manifest['moduleReplacementRegions'].items():
    x0,y0,x1,y1=spec['xyxyHalfOpen']; original=[]
    for y in range(y0,y1):
        for x in range(x0,x1):
            r,g,b,a=base.getpixel((x,y))
            if a and r>170 and g>135 and b>110 and r-g<90: original.append((x,y))
    spec['originalPaleBonePixelCount']=len(original); spec['paleBoneCoordinates']=[list(q) for q in original]; spec['perTierBoneCoverage']={}
    for state_key in spec['states']:
        state=Image.open(ROOT/f'{state_key}.png').convert('RGBA')
        covered=sum(state.getpixel(q)!=base.getpixel(q) for q in original)
        spec['perTierBoneCoverage'][state_key]={'covered':covered,'total':len(original),'ratio':1.0 if not original else covered/len(original)}
for key in images:
    path=ROOT/f'{key}.png'; state=Image.open(path).convert('RGBA')
    diffs=[]
    for y in range(64):
        for x in range(64):
            a=base.getpixel((x,y));b=state.getpixel((x,y))
            if a!=b: diffs.append([x,y,list(b)])
    manifest['states'][key]={'path':path.name,'sha256':sha(path),'bytes':path.stat().st_size,'size':[64,64],'changedPixelCount':len(diffs),'diffPixels':diffs}
(VAL/'pixel-diffs-and-hashes.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

# Native 4x preview of all ten states in two rows of five, white and dark backgrounds.
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',21)
keys=['ordinary0','resonance1','resonance2','split1','split2','split3','tuning1','extension1','extension2','extension3']
labels=['普通','共振 I','共振 II','分频 I','分频 II','分频 III','调谐 I','延展 I','延展 II','延展 III']
def sheet(path,bg,chosen,cols,scale,cellw,cellh):
    rows=(len(chosen)+cols-1)//cols; out=Image.new('RGB',(cols*cellw,rows*cellh),bg);d=ImageDraw.Draw(out)
    for i,(key,label) in enumerate(chosen):
        col=i%cols;row=i//cols;x=col*cellw+(cellw-64*scale)//2;y=row*cellh+6
        icon=Image.open(ROOT/f'{key}.png').convert('RGBA').resize((64*scale,64*scale),Image.Resampling.NEAREST)
        out.paste(icon,(x,y),icon)
        d.text((col*cellw+cellw//2,y+64*scale+22),label,font=font,fill=(22,26,30) if bg==(255,255,255) else (242,244,246),anchor='mm')
    out.save(VAL/path)
all_states=list(zip(keys,labels))
for bg,name in [((255,255,255),'big-preview-white-4x.png'),((25,29,36),'big-preview-dark-4x.png')]: sheet(name,bg,all_states,5,4,240,340)
six=[('ordinary0','普通'),('resonance2','共振 II'),('split3','分频 III'),('tuning1','调谐 I'),('extension3','延展 III'),('all_max','全最高级')]
for bg,name in [((255,255,255),'six-state-white-4x.png'),((25,29,36),'six-state-dark-4x.png')]: sheet(name,bg,six,3,4,300,320)
# Show downsampling at true 16/32 texture resolutions, enlarged nearest-neighbour for legibility.
font2=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',18)
for size in (16,32):
    out=Image.new('RGB',(1200,360),(25,29,36));d=ImageDraw.Draw(out)
    for i,(key,label) in enumerate(all_states):
        col=i%5;row=i//5;x=col*240+56;y=row*180+4
        icon=Image.open(ROOT/f'{key}.png').convert('RGBA').resize((size,size),Image.Resampling.NEAREST).resize((128,128),Image.Resampling.NEAREST)
        out.paste(icon,(x,y),icon);d.text((x+64,y+139),f'{label} {size}',font=font2,fill=(240,242,245),anchor='mm')
    out.save(VAL/f'preview-{size}px.png')
print('base',EXPECTED,'bytes', (ROOT/'ordinary0.png').stat().st_size)
