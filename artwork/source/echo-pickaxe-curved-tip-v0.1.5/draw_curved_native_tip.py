"""Preview a native64 curved tip inside the exact legacy 32px silhouette."""
import hashlib,io,json,zipfile
from collections import Counter
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[3]
SRC=Path(__file__).resolve().parent
OUT=ROOT/'artwork/validation/v0.1.5/curved-tip-draft'
ORD=ROOT/'jaysay-echo-tools-0.1.2.jar'; ORD_SHA='7312AE7B54F3DAD998815B7C7BD601B65DB1BED23A21CC7AA8448E40E082F495'
BASE=ROOT/'jaysay-echo-tools-0.1.4.jar'; BASE_SHA='9A3D6C0D9B5485C397117CBF00C00C31DA04A339838831231EC5C31B552D67AF'
COMMON=ROOT/'artwork/source/approved-reference-oct03-64/common64-unupgraded.png'
COMPONENTS=ROOT/'artwork/source/approved-reference-oct03-64/native64-component-map.json'
PREFIX='assets/echopickaxe/'
REGION=(7,8,33,28) # x=7..32, y=8..27: hook + solid head transition into native body
DARK=(22,28,36)

def sha(b):return hashlib.sha256(b).hexdigest().upper()
def png(b):return Image.open(io.BytesIO(b)).convert('RGBA')
def asset(z,n):return png(z.read(PREFIX+n))
def luminance(c):return .2126*c[0]+.7152*c[1]+.0722*c[2]
def mask_pixels(im):return {(x,y) for y in range(im.height) for x in range(im.width) if im.getpixel((x,y))[3]}
def connected(mask,diagonal=False):
    left=set(mask);sizes=[];dirs=[(1,0),(-1,0),(0,1),(0,-1)]
    if diagonal:dirs += [(1,1),(1,-1),(-1,1),(-1,-1)]
    while left:
        q=[left.pop()];n=0
        while q:
            x,y=q.pop();n+=1
            for dx,dy in dirs:
                p=(x+dx,y+dy)
                if p in left:left.remove(p);q.append(p)
        sizes.append(n)
    return sorted(sizes,reverse=True)

def paint_tip(common,old32):
    # The legacy image supplies alpha only. Its RGB values are intentionally
    # never read or used to classify the native64 material.
    old_alpha=old32.getchannel('A').resize((64,64),Image.Resampling.NEAREST)
    out=common.copy();op=out.load();cp=common.load()
    mask={(x,y) for y in range(REGION[1],REGION[3]) for x in range(REGION[0],REGION[2])}
    # Use the approved body only as a source of native sculk colors. Every
    # opaque pixel in the 520-texel ROI is repainted; no common64 RGB block is
    # copied through, and legacy RGB is never examined.
    headcolors=Counter(cp[x,y][:3] for y in range(7,28) for x in range(17,43)
                       if cp[x,y][3] and cp[x,y][1]>cp[x,y][0] and cp[x,y][2]>cp[x,y][0]
                       and luminance(cp[x,y][:3])<145)
    palette=list(headcolors)
    def palette_near(target):return min(palette,key=lambda c:(sum((c[i]-target[i])**2 for i in range(3)),c))+(255,)
    bright_palette=[cp[x,y][:3] for y in range(7,28) for x in range(17,43)
                    if cp[x,y][3] and cp[x,y][1]>cp[x,y][0] and cp[x,y][2]>cp[x,y][0]
                    and 110<=luminance(cp[x,y][:3])<=220]
    def bright_near(target):return min(bright_palette,key=lambda c:(sum((c[i]-target[i])**2 for i in range(3)),c))+(255,)
    colors={
      'deep':palette_near((0,14,22)), 'edge':palette_near((0,24,35)),
      'shadow':palette_near((1,34,48)), 'base':palette_near((3,46,62)),
      'mid':palette_near((5,62,76)), 'facet':palette_near((7,78,88)),
      'ridge':palette_near((4,93,103)), 'crack':palette_near((5,112,126)),
      'crackHi':palette_near((14,123,137))}
    material=Image.new('RGBA',(64,64),(0,0,0,0));md=ImageDraw.Draw(material)
    # A dark body fill is split into directional, irregular planes. The two
    # broad head faces are broken by 1px seams and short 1-2px facets.
    for point in mask:
        x,y=point
        if old_alpha.getpixel(point):md.point((x,y),fill=colors['base'])
    md.polygon([(18,8),(24,8),(24,9),(22,10),(20,11),(18,11)],fill=colors['shadow'])
    md.polygon([(25,8),(32,8),(32,10),(30,10),(29,11),(27,11),(25,10)],fill=colors['mid'])
    md.polygon([(18,12),(22,11),(25,11),(26,12),(23,13),(21,14),(18,14)],fill=colors['facet'])
    md.polygon([(25,12),(28,11),(32,11),(32,14),(29,14),(27,15),(24,14)],fill=colors['shadow'])
    md.polygon([(12,14),(17,13),(20,14),(19,15),(17,16),(14,16),(12,15)],fill=colors['shadow'])
    md.polygon([(19,14),(22,14),(24,15),(22,16),(20,17),(17,17),(18,16)],fill=colors['mid'])
    md.polygon([(23,15),(27,14),(29,15),(27,16),(24,17),(22,17)],fill=colors['facet'])
    md.polygon([(10,16),(13,16),(15,17),(18,17),(20,18),(18,19),(15,19),(13,18),(10,18)],fill=colors['mid'])
    md.polygon([(10,19),(13,19),(15,20),(14,21),(12,22),(10,22)],fill=colors['shadow'])
    md.polygon([(15,19),(18,19),(20,18),(22,18),(22,19),(19,20),(17,21),(15,21)],fill=colors['facet'])
    md.polygon([(10,23),(13,22),(16,22),(17,23),(16,24),(10,24)],fill=colors['edge'])
    md.polygon([(20,8),(21,8),(21,10),(20,11),(19,11)],fill=colors['edge'])
    md.polygon([(26,10),(27,10),(27,12),(26,13),(25,13)],fill=colors['edge'])
    md.polygon([(20,15),(21,15),(21,17),(20,18),(19,18)],fill=colors['edge'])
    # Short, directional bevels subdivide each face instead of adding random
    # speckles. These narrow strokes follow the arch and curl into the hook.
    md.line([(24,8),(23,9),(22,10),(22,11)],fill=colors['edge'],width=1)
    md.line([(25,8),(24,9),(23,10)],fill=colors['facet'],width=1)
    md.line([(31,9),(30,10),(30,11)],fill=colors['edge'],width=1)
    md.line([(31,10),(30,11),(29,12)],fill=colors['ridge'],width=1)
    md.line([(19,9),(18,10),(18,11)],fill=colors['edge'],width=1)
    md.line([(17,12),(16,13),(15,14)],fill=colors['facet'],width=1)
    md.line([(21,13),(20,14),(20,15)],fill=colors['edge'],width=1)
    md.line([(24,15),(23,16),(22,16)],fill=colors['ridge'],width=1)
    md.line([(13,16),(14,17),(16,17)],fill=colors['edge'],width=1)
    md.line([(17,18),(18,18),(19,17)],fill=colors['ridge'],width=1)
    md.line([(19,19),(18,20),(17,20)],fill=colors['edge'],width=1)
    md.line([(11,20),(12,20),(13,19)],fill=colors['ridge'],width=1)
    # Paired micro-facets give each short plane an edge, a midtone and a
    # restrained lit pixel. Their repeated diagonal direction follows the
    # material grain rather than sprinkling isolated color noise.
    micro_facets=[
      ([(27,8),(26,9),(25,10)],'edge'), ([(28,8),(27,9),(26,10)],'facet'),
      ([(29,8),(28,9)],'ridge'), ([(30,9),(29,10),(28,11)],'edge'),
      ([(31,10),(30,11)],'facet'), ([(24,10),(23,11),(22,12)],'shadow'),
      ([(25,10),(24,11),(23,12)],'ridge'), ([(27,12),(26,13),(25,14)],'edge'),
      ([(28,12),(27,13)],'facet'), ([(23,13),(22,14),(21,15)],'shadow'),
      ([(24,14),(23,15),(22,16)],'ridge'), ([(18,13),(17,14),(16,15)],'edge'),
      ([(19,14),(18,15),(17,16)],'facet'), ([(15,15),(14,16),(13,17)],'shadow'),
      ([(16,16),(15,17),(14,18)],'ridge'), ([(20,16),(19,17),(18,18)],'edge'),
      ([(21,16),(20,17),(19,18)],'facet'), ([(16,19),(15,20),(14,21)],'shadow'),
      ([(17,19),(16,20),(15,21)],'ridge'), ([(13,21),(12,22),(11,23)],'edge')]
    for points,color_key in micro_facets:
        md.line(points,fill=colors[color_key],width=1)
    # A single angled fissure follows the curve and forks once; bright cyan
    # remains a sparse 1px accent in the same approved body palette.
    md.line([(29,8),(29,9),(28,10),(27,10)],fill=colors['ridge'],width=1)
    md.line([(23,11),(22,12),(21,12)],fill=colors['ridge'],width=1)
    md.line([(18,13),(17,14)],fill=colors['ridge'],width=1)
    md.line([(16,18),(17,18),(18,17)],fill=colors['ridge'],width=1)
    md.line([(12,22),(13,21)],fill=colors['ridge'],width=1)
    fissure=[(30,9),(29,10),(29,11),(28,11),(27,12),(26,12),(25,13),(24,13),
             (23,14),(22,14),(21,15),(20,15),(19,16),(18,16),(17,17),(16,18),
             (16,19),(15,20),(14,21)]
    md.line(fissure,fill=colors['crack'],width=1)
    md.point((27,12),fill=colors['crackHi']);md.point((21,15),fill=colors['crackHi'])
    md.line([(24,13),(24,14),(23,15)],fill=colors['crack'],width=1)
    md.line([(18,16),(17,15)],fill=colors['crack'],width=1)
    # Three restrained 1px cyan glints match the approved body crack palette
    # and follow the hook's bend; each sits beside the darker bevel strokes.
    cyan_glint=bright_near((8,170,182));cyan_glint_hi=bright_near((20,205,216))
    md.line([(14,22),(15,21),(16,20),(16,19)],fill=cyan_glint,width=1)
    md.line([(19,17),(20,16),(21,16),(22,15)],fill=cyan_glint_hi,width=1)
    md.line([(26,13),(27,12),(28,12),(29,11)],fill=cyan_glint,width=1)
    mp=material.load()
    for y in range(REGION[1],REGION[3]):
      for x in range(REGION[0],REGION[2]):
        if old_alpha.getpixel((x,y))==0:
            op[x,y]=(0,0,0,0);continue
        op[x,y]=mp[x,y]
    return out,old_alpha,mask,{'material':'all 520 ROI texels repainted from approved native common64 sculk palette',
      'fissure':fissure,'threeBodyMatchGlints':[[(14,22),(15,21),(16,20),(16,19)],
      [(19,17),(20,16),(21,16),(22,15)],[(26,13),(27,12),(28,12),(29,11)]],
      'legacyRgbRead':False}

def composite(im,bg):
    c=Image.new('RGBA',im.size,bg+(255,));c.alpha_composite(im);return c.convert('RGB')
def board(states,path,scale,crop=None):
    views=[]
    for label,im in states:
        v=im.crop(crop) if crop else im
        views.append((label,v.resize((v.width*scale,v.height*scale),Image.Resampling.NEAREST)))
    m=10;cw=max(v.width for _,v in views)+18;ch=max(v.height for _,v in views)+32
    out=Image.new('RGB',(m*2+cw*len(views),m*2+ch*2),(245,245,245));d=ImageDraw.Draw(out);font=ImageFont.load_default()
    for row,bg in enumerate(((255,255,255),DARK)):
        fg=(18,22,28) if row==0 else (240,242,247);y=m+row*ch
        for i,(label,v) in enumerate(views):
            x=m+i*cw;d.text((x+4,y),label,fill=fg,font=font);out.paste(composite(v,bg),(x+4,y+14))
    out.save(path)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    assert sha(ORD.read_bytes())==ORD_SHA and sha(BASE.read_bytes())==BASE_SHA
    common=png(COMMON.read_bytes());comp=json.loads(COMPONENTS.read_text(encoding='utf-8'))['components']
    module_union={name:{(x,y) for tier in item['tiers'] for x,y,*_ in tier['texels']} for name,item in comp.items()}
    # The replacement is constrained to the left hook/head bridge and may not
    # touch the crystal/star modules.
    x0,y0,x1,y1=REGION;mask={(x,y) for y in range(y0,y1) for x in range(x0,x1)}
    for name in ('frequency','tuning','extension'):
        assert not mask&module_union[name],f'replacement region intersects {name}'
    with zipfile.ZipFile(ORD) as oz,zipfile.ZipFile(BASE) as bz:
        ordinary=asset(oz,'textures/item/echo_pickaxe.png')
        bare,old64,mask,details=paint_tip(common,ordinary)
        v24=asset(bz,'textures/item/echo_pickaxe_v024.png')
        v31=asset(bz,'textures/item/echo_pickaxe_v031.png')
        v95=asset(bz,'textures/item/echo_pickaxe_v095.png')
        previews=[]
        for old in (v24,v31):
            new=old.copy();np=new.load();bp=bare.load()
            for x,y in mask:np[x,y]=bp[x,y]
            previews.append(new)
    ordinary64=ordinary.resize((64,64),Image.Resampling.NEAREST)
    bare.save(OUT/'bare-native64-tip-draft.png')
    previews[0].save(OUT/'frequency-III-only-native64-tip-draft.png')
    previews[1].save(OUT/'res0-v031-native64-tip-draft.png')
    board([('ordinary 32px ×2 outline',ordinary64),('frequency III only',previews[0]),
           ('res0 v031',previews[1]),('approved red resII v095',v95)],OUT/'curved-tip-whole-4x-white-dark.png',4)
    board([('ordinary 32px ×2 outline',ordinary64),('frequency III only',previews[0]),
           ('res0 v031',previews[1]),('approved red resII v095',v95)],OUT/'curved-tip-closeup-8x-white-dark.png',8,(7,8,32,27))
    mm=Image.new('RGBA',(64,64),(0,0,0,0))
    for x,y in mask:mm.putpixel((x,y),(255,180,30,255))
    mm.save(SRC/'replacement-transition-mask-draft.png')
    opaque=mask_pixels(bare)
    report={'status':'draft-for-root-review','ordinaryJarSha256':ORD_SHA,'res0BaselineJarSha256':BASE_SHA,
      'outlineSource':'ordinary 0.1.2 echo_pickaxe.png alpha resized nearest-neighbor 2x','regionXYxy':[x0,y0,x1-1,y1-1],
      'transitionMaskTexels':len(mask),'oldOrdinaryOpaqueTexelsInRegion':sum(old64.getpixel(p)>0 for p in mask),
      'opaqueTexels':len(opaque),'components4':connected(opaque),'components8':connected(opaque,True),
      'moduleOverlap':{n:len(mask&module_union[n]) for n in ('frequency','tuning','extension')},
      'artDirection':'Only legacy alpha defines the curved-tip outline. New pixels use dark cyan-black native common64 sculk facets and a fine cyan fissure; no legacy color classification is used.',
      'pixelDetails':details,'previews':['curved-tip-whole-4x-white-dark.png','curved-tip-closeup-8x-white-dark.png'],
      'candidateResourcesGenerated':False}
    (SRC/'tip-transition-map-draft.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'PASS draft; mask={len(mask)} tip alpha source exact old32 nearest2x; opaque={len(opaque)} components={connected(opaque)}; files={OUT}')

if __name__=='__main__':main()
