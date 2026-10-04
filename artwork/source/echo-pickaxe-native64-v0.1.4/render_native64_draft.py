"""Review-only native64 texture draft. Does not generate game resources or deploy."""
from __future__ import annotations
import hashlib, io, json, zipfile
from pathlib import Path
from collections import Counter
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[3]
SOURCE=Path(__file__).resolve().parent
JAR12=ROOT/'jaysay-echo-tools-0.1.2.jar'
JAR13=ROOT/'jaysay-echo-tools-0.1.3.jar'
JAR12_SHA='7312AE7B54F3DAD998815B7C7BD601B65DB1BED23A21CC7AA8448E40E082F495'
JAR13_SHA='3D0F7B94EDBD09776D9891986354952CF1615B32305866C63FEEB7ED71F9D80D'
ORDINARY_PNG_SHA='C1F7A1F94009E274F369DA857777E2BD32F77EF951427AB38E6160CC1BE7DBEB'
COMMON64=ROOT/'artwork/source/approved-reference-oct03-64/common64-unupgraded.png'
COMMON64_SHA='0322211B247FBFD8D96321DB29856FFD93AA8F430038C2275C36DEDE2670B95C'
MASK13=ROOT/'artwork/validation/v0.1.3/artagentmask.png'
OUT=ROOT/'artwork/validation/v0.1.4/draft'
PREFIX='assets/echopickaxe/'


def digest(data): return hashlib.sha256(data).hexdigest().upper()
def image_from_jar(jar,name): return Image.open(io.BytesIO(jar.read(PREFIX+name))).convert('RGBA')
def mat_class(rgb):
    r,g,b=rgb
    if r>95 and g>85 and b>75 and abs(r-g)<45 and abs(g-b)<60: return 'ivory'
    if g>r*1.35 and b>g*1.05: return 'vein'
    return 'sculk'


def main():
    assert digest(JAR12.read_bytes())==JAR12_SHA
    assert digest(JAR13.read_bytes())==JAR13_SHA
    assert digest(COMMON64.read_bytes())==COMMON64_SHA
    with zipfile.ZipFile(JAR12) as z12, zipfile.ZipFile(JAR13) as z13:
        ordinary_bytes=z12.read(PREFIX+'textures/item/echo_pickaxe.png')
        assert digest(ordinary_bytes)==ORDINARY_PNG_SHA
        ordinary=Image.open(io.BytesIO(ordinary_bytes)).convert('RGBA')
        assert ordinary.size==(32,32)
        old64=ordinary.resize((64,64),Image.Resampling.NEAREST)
        shape={(x,y) for y in range(64) for x in range(64) if old64.getpixel((x,y))[3]}
        assert sum(1 for p in ordinary.getdata() if p[3])==299 and len(shape)==1196
        # Preserve old ivory placement and broad brightness. Refine only old
        # sculk/vein fields with crisp, directional one-pixel facets at existing
        # same-material shade boundaries. The approved64 file is palette/grain
        # reference only; no spatial motifs are transplanted.
        src=ordinary.load()
        plain=Image.new('RGBA',(64,64),(0,0,0,0)); dst=plain.load()
        def pixel32(x,y):
            return src[x,y] if 0<=x<32 and 0<=y<32 else (0,0,0,0)
        for y in range(64):
            for x in range(64):
                sx,sy=x//2,y//2; base=pixel32(sx,sy)
                if base[3]==0: continue
                cls=mat_class(base[:3])
                if cls=='ivory':
                    dst[x,y]=base
                    continue
                lum=lambda q: 0.2126*q[0]+0.7152*q[1]+0.0722*q[2]
                neighbors=[('left',pixel32(sx-1,sy)),('right',pixel32(sx+1,sy)),
                           ('up',pixel32(sx,sy-1)),('down',pixel32(sx,sy+1))]
                neighbors=[(direction,q) for direction,q in neighbors
                           if q[3] and mat_class(q[:3])==cls and abs(lum(q)-lum(base))>=12]
                direction,face=max(neighbors,key=lambda pair:(abs(lum(pair[1])-lum(base)),pair[0])) if neighbors else (None,None)
                toward_face=(direction is not None and lum(face)>lum(base))
                for dy in range(2):
                    for dx in range(2):
                        facing=(direction=='right' and dx==1) or (direction=='left' and dx==0) or (direction=='down' and dy==1) or (direction=='up' and dy==0)
                        if facing:
                            # Shade transitions lean toward the adjacent facet;
                            # keep the source vein/sculk hue and limit contrast.
                            amount=0.24 if toward_face else 0.20
                            rgb=tuple(round(base[i]*(1-amount)+face[i]*amount) for i in range(3))
                        else: rgb=base[:3]
                        dst[sx*2+dx,sy*2+dy]=rgb+(255,)
        ivory64={(x*2+dx,y*2+dy) for y in range(32) for x in range(32)
                 if src[x,y][3] and mat_class(src[x,y][:3])=='ivory'
                 for dx in range(2) for dy in range(2)}
        # Three native-resolution bevel paths follow only existing ivory material:
        # the small hooked tip, outer blade edge, and pommel. These are thin and
        # continuous across old 2x2 boundaries; the broad ivory mass stays in place.
        ivory_paths={
          'tip_highlight':[(10,16),(11,17),(11,18),(12,19),(12,20),(13,21)],
          'tip_shadow':[(10,17),(10,19),(12,18),(13,20),(12,22)],
          'blade_highlight':[(57,20),(57,21),(57,22),(57,23),(57,24),(58,28),(59,29),(57,30),(57,31),(57,32),(56,33),(56,34)],
          'blade_shadow':[(56,24),(56,25),(58,30),(58,31),(56,32),(56,33),(57,34),(57,35)],
          'pommel_highlight':[(4,52),(5,52),(6,53),(7,53),(8,54),(8,55),(9,56),(9,57)],
          'pommel_shadow':[(4,53),(6,52),(7,52),(2,54),(3,55),(8,56),(8,57),(8,58)],
        }
        ivory_colors={'tip_highlight':(238,234,224,255),'blade_highlight':(238,234,224,255),
                      'pommel_highlight':(238,234,224,255),'tip_shadow':(184,180,170,255),
                      'blade_shadow':(184,180,170,255),'pommel_shadow':(184,180,170,255)}
        for role,coords in ivory_paths.items():
            for px,py in coords:
                if (px,py) not in ivory64:
                    raise AssertionError(f'{role} leaves old ivory mask at {(px,py)}')
                dst[px,py]=ivory_colors[role]
        facets=ivory_paths; pommel={k:v for k,v in ivory_paths.items() if k.startswith('pommel_')}
        if {(x,y) for y in range(64) for x in range(64) if dst[x,y][3]}!=shape:
            raise AssertionError('New plain64 silhouette differs from locked ordinary alpha x2')

        coarse31=image_from_jar(z13,'textures/item/echo_pickaxe_v031.png')
        new31=coarse31.copy(); newpix=new31.load(); m=Image.open(MASK13).convert('RGBA')
        for y in range(64):
            for x in range(64):
                if m.getpixel((x,y))[3]:newpix[x,y]=dst[x,y]
        full95=image_from_jar(z13,'textures/item/echo_pickaxe_v095.png')

        OUT.mkdir(parents=True,exist_ok=True)
        approved_png=SOURCE/'ordinary-native64-approved.png'
        plain.save(approved_png)
        old64.save(OUT/'plain32-on-64-canvas.png')
        plain.save(OUT/'plain64-native-draft.png')
        coarse31.save(OUT/'res0-v031-0.1.3-coarse.png')
        new31.save(OUT/'res0-v031-native64-tip-draft.png')
        full95.save(OUT/'resII-v095-approved-unchanged.png')
        rgba_map=[[x,y,list(dst[x,y])] for y in range(64) for x in range(64) if dst[x,y][3]]
        mapdoc={'schema':1,'status':'root-approved','title':'Original ordinary pickaxe silhouette with native64 material refinement',
          'shapeSource':'0.1.2 ordinary PNG alpha, nearest-neighbor 2x only','ordinaryPngSha256':ORDINARY_PNG_SHA,
          'ordinaryOpaque32':299,'nativeOpaque64':len(shape),'nativeTexture':'ordinary-native64-approved.png',
          'nativeTextureSha256':hashlib.sha256(approved_png.read_bytes()).hexdigest().upper(),
          'materialMethod':'Keep old 32px local sculk/cyan distribution. Split same-material shade boundaries into directed 1px facets. Within old ivory mask, add a few restrained continuous 1px highlight/shadow cuts; no new ivory area. No stochastic noise or common64 spatial projection.',
          'ivoryPathsNative64':facets,'explicitOpaqueRgbaTexels':rgba_map,
          'rootApproved':True,'aiConceptUsed':False}
        (SOURCE/'native64-tip-map.json').write_text(json.dumps(mapdoc,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        (OUT/'native64-draft-map.json').write_text(json.dumps({k:v for k,v in mapdoc.items() if k!='explicitOpaqueRgbaTexels'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        make_boards(old64,plain,coarse31,new31,full95,OUT)
        print(f'PASS: draft plain alpha exactly matches locked 0.1.2 silhouette: 299→{len(shape)}; output={OUT}')


def composite(sprite,bg):
    out=Image.new('RGBA',sprite.size,bg+(255,));out.alpha_composite(sprite);return out.convert('RGB')

def make_boards(old64,plain,coarse31,new31,full95,out):
    states=[('plain32 → same 64 outline',old64),('plain64 native grain draft',plain),
      ('old coarse res0 v031',coarse31),('new res0 v031 tip draft',new31),('approved resII v095 unchanged',full95)]
    bg=(255,255,255); card=512; pad=20; top=48
    canvas=Image.new('RGB',(3*card+4*pad,2*card+3*pad+top),bg);d=ImageDraw.Draw(canvas);font=ImageFont.load_default()
    for i,(label,img) in enumerate(states):
      col=i%3;row=i//3;x=pad+col*(card+pad);y=top+pad+row*(card+pad)
      d.text((x,y-16),label,fill=(10,10,10),font=font)
      canvas.paste(composite(img.resize((512,512),Image.Resampling.NEAREST),bg),(x,y))
    canvas.save(out/'native64-review-8x.png')
    # Pixel-size comparison that exposes whether 1px grain survives downsampling.
    board=Image.new('RGB',(5*180,2*150+44),bg);d=ImageDraw.Draw(board)
    for row,size in enumerate((16,32)):
      y0=24+row*150
      d.text((4,y0-14),f'{size}px inventory render',fill=(0,0,0),font=font)
      for i,(label,img) in enumerate(states):
        x0=i*180+4
        d.text((x0,y0),label[:22],fill=(0,0,0),font=font)
        scaled=img.resize((size,size),Image.Resampling.NEAREST)
        zoom=128 if size==16 else 128
        board.paste(composite(scaled.resize((zoom,zoom),Image.Resampling.NEAREST),bg),(x0,y0+16))
    board.save(out/'native64-review-inventory-16-32.png')

if __name__=='__main__':main()
