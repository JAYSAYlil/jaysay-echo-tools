from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import hashlib, json, shutil

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
SRC = PROJECT / 'src/main/resources/assets/echopickaxe/textures/item/echo_pickaxe.png'
VAL = PROJECT / 'artwork/validation/v0.1.11/native-base-upgrades'
EXPECTED = '296326965171A658F9CD40E0C9C42FB3ABF5B1094AF9EFB0005096061C1711F5'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()

if sha(SRC) != EXPECTED:
    raise SystemExit(f'ordinary0 anchor mismatch: {sha(SRC)}')
base = Image.open(SRC).convert('RGBA')
if base.size != (64, 64):
    raise SystemExit(f'expected 64x64 base, got {base.size}')

def recolor(region, palette, fraction):
    im = base.copy(); px = im.load(); x0,y0,x1,y1 = region; pts=[]
    for y in range(y0,y1):
        for x in range(x0,x1):
            r,g,b,a=px[x,y]
            if a and r>170 and g>135 and b>110 and r-g<90:
                pts.append((x,y,(r,g,b,a)))
    pts.sort(key=lambda q:(q[1],q[0])); n=round(len(pts)*fraction)
    for i,(x,y,o) in enumerate(pts[:n]):
        c=palette[i%len(palette)]; s=max(.58,min(1.08,(sum(o[:3])/3)/205))
        px[x,y]=(*(int(v*s) for v in c),o[3])
    return im

red=[(115,25,31),(176,43,44),(229,82,74),(255,160,140)]
purple=[(55,36,112),(93,62,163),(154,112,208),(216,184,242)]
images={'ordinary0':base.copy()}
for name,f in [('resonance1',.66),('resonance2',1.0)]: images[name]=recolor((20,5,39,21),red,f)
for name,f in [('split1',.55),('split2',.78),('split3',1.0)]: images[name]=recolor((48,20,61,36),purple,f)
# One star at the original central node; only existing opaque pixels can change.
im=base.copy();p=im.load()
for x,y,c in [(41,15,(111,245,250,255)),(42,14,(170,247,255,255)),(42,15,(255,255,244,255)),(43,15,(190,249,255,255)),(42,16,(132,232,244,255))]:
    if p[x,y][3]: p[x,y]=c
images['tuning1']=im
# Recolor the original tail crystal's existing cyan facets, retaining its pale bone clasp and alpha silhouette.
im=base.copy();p=im.load();pts=[]
for y in range(50,59):
    for x in range(5,16):
        r,g,b,a=p[x,y]
        if a and g>r*1.12 and b>r*1.08 and g>55: pts.append((x,y,(r,g,b,a)))
for x,y,o in pts:
    dist=abs(x-10)+abs(y-54)
    c=(128,226,151) if dist<=1 else (45,177,103) if dist<=3 else (12,104,68)
    p[x,y]=(*c,o[3])
for (x,y),c in [((10,54),(199,255,190)),((9,54),(91,220,135)),((10,53),(112,232,145))]:
    if p[x,y][3] and base.getpixel((x,y))[1]>base.getpixel((x,y))[0]*1.1: p[x,y]=(*c,255)
images['extension3']=im
# Earlier extension stages blend fewer of the same pre-existing eligible pixels.
for level,fraction in [(1,.42),(2,.72)]:
    im=base.copy();p=im.load(); n=round(len(pts)*fraction)
    for i,(x,y,o) in enumerate(pts[:n]):
        dist=abs(x-10)+abs(y-54); c=(90,197,125) if dist<=2 else (17,118,75)
        p[x,y]=(*c,o[3])
    images[f'extension{level}']=im
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
