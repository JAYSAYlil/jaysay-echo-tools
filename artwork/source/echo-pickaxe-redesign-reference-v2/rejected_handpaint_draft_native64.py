"""Static low-tier visual draft from the user-selected normalized 64px master."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import hashlib, importlib.util, json

ROOT=Path(__file__).resolve().parents[3]
SRC=Path(__file__).resolve().parent
OUT=ROOT/'artwork/validation/v0.1.11/redesign-v2'
REF_PATH=SRC/'user-reference.png'
APPROVED=ROOT/'artwork/source/approved-reference-oct03-64/build_approved64_variants.py'
REF_SHA='53192C7BB67E2721431F3448DF8E4AB962DAC6291FFA39B89BBB04323EEAF0F8'

def get_builder():
    spec=importlib.util.spec_from_file_location('reference_masks_only',APPROVED)
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def font(size):
    for p in (r'C:\Windows\Fonts\msyh.ttc',r'C:\Windows\Fonts\arial.ttf'):
        if Path(p).is_file(): return ImageFont.truetype(p,size)
    return ImageFont.load_default()

def flatten(im,bg):
    tile=Image.new('RGBA',im.size,(*bg,255)); tile.alpha_composite(im); return tile.convert('RGB')

def put(pix, points, color):
    for x,y in points:
        if pix[x,y][3]: pix[x,y]=(*color,255)

def paint_low_tier(reference, tiers):
    """Make the bare native64 component underlay; no source32 RGB/common-body sampling."""
    out=reference.copy(); p=out.load()
    # Clear only inactive module texels. Their replacement is native dark sculk material,
    # laid out as a few directional facets rather than a tile or a color-noise field.
    inactive=[]
    for c in ('resonance','frequency','extension'):
        for mask in tiers[c]:
            inactive.extend((i%64,i//64) for i,a in enumerate(mask.getdata()) if a)
    inactive=set(inactive)
    for x,y in inactive: p[x,y]=(4,25,33,255)
    # Intentional, irregular facet planes follow each part's form. They are broad
    # dark/mid planes with hand-placed edges, not repeated sampling or modulo texture.
    facets_img=Image.new('L',(64,64)); fd=ImageDraw.Draw(facets_img)
    facet_planes=[
      ([(19,7),(25,6),(30,7),(32,10),(27,11),(22,10)],(8,43,51)),
      ([(20,11),(24,11),(28,12),(31,14),(28,17),(24,16),(21,14)],(6,35,44)),
      ([(28,8),(33,8),(35,10),(33,12),(30,11)],(11,48,55)),
      ([(44,13),(48,12),(51,16),(52,20),(49,22),(46,19)],(8,40,49)),
      ([(49,21),(53,20),(56,24),(57,29),(54,31),(51,27)],(6,34,43)),
      ([(53,29),(57,28),(59,33),(60,38),(58,40),(55,36)],(9,44,52)),
      ([(8,47),(13,46),(17,49),(18,53),(16,57),(12,59),(8,56),(6,52)],(7,38,47)),
    ]
    for points,color in facet_planes:
        fd.polygon(points,fill=255)
        for yy in range(64):
            for xx in range(64):
                if facets_img.getpixel((xx,yy)) and (xx,yy) in inactive and p[xx,yy][3]:
                    p[xx,yy]=(*color,255)
        facets_img=Image.new('L',(64,64)); fd=ImageDraw.Draw(facets_img)

    # A few deliberate facets give the new bare hook volume. No old RGB, tiled shaft
    # sample, broad cyan fill, or noisy per-pixel perturbation is used.
    facets={
      (20,7):(12,54,62),(21,7):(8,39,48),(22,8):(18,69,75),
      (19,10):(7,45,53),(20,11):(14,59,67),(21,12):(8,39,48),
      (22,13):(13,56,64),(23,14):(7,43,51),(24,15):(12,51,59),
      (25,15):(5,32,40),(27,13):(11,52,60),(29,12):(7,37,45),
      (31,11):(13,58,66),(32,12):(5,31,39),(33,14):(10,48,56),
      (46,14):(12,53,61),(48,17):(7,36,44),(51,20):(13,54,61),
      (53,24):(8,41,49),(55,28):(12,50,58),(57,33):(7,37,45),
      (58,37):(11,48,56),(13,47):(8,40,48),(15,49):(12,53,61),
      (11,52):(5,30,38),(14,54):(9,45,52),(10,57):(12,52,59),
    }
    for (x,y),rgb in facets.items():
        if (x,y) in inactive and p[x,y][3]: p[x,y]=(*rgb,255)

    # Left unupgraded blade: a thin, warm bone edge follows a short curved sweep.
    left_bone={
      (18,8):(178,172,157),(19,8):(220,213,196),
      (18,9):(225,218,200),(19,9):(242,235,216),
      (19,10):(204,199,183),(20,10):(229,222,204),
      (20,11):(242,235,216),(21,11):(212,206,190),
      (20,12):(222,216,199),(21,12):(239,232,213),
      (21,13):(208,202,186),(22,13):(230,223,205),
      (22,14):(242,235,216),(23,14):(211,205,189),
      (23,15):(228,221,203),(24,15):(240,233,214),
      (24,16):(205,200,184),(25,16):(225,218,200),
    }
    for xy,rgb in left_bone.items():
        if xy in inactive and p[xy][3]: p[xy]=(*rgb,255)

    # Two short cyan fissure paths continue the reference's head direction without
    # raising the overall cyan density into a mesh.
    cyan={
      (25,8):(35,157,168),(26,9):(11,76,91),(27,10):(28,135,148),
      (28,10):(8,56,70),(29,11):(24,127,141),
      (35,21):(22,125,139),(36,22):(10,68,82),(37,22):(32,150,163),
      (38,23):(7,52,65),(39,24):(23,121,136),
    }
    for (x,y),rgb in cyan.items():
        if p[x,y][3] and (x,y) in inactive: p[x,y]=(*rgb,255)

    # Right bare tip has dark facets, a restrained inner seam, and a narrow bone edge.
    right_cyan={(48,20):(18,106,123),(49,21):(34,151,163),(50,22):(8,59,74),
                (51,24):(23,126,140),(52,25):(7,53,67),(54,28):(27,139,153),
                (55,30):(10,67,81),(56,32):(23,120,135)}
    for (x,y),rgb in right_cyan.items():
        if p[x,y][3] and (x,y) in inactive: p[x,y]=(*rgb,255)
    right_bone={(57,36):(183,177,161),(58,36):(225,218,201),
                (57,37):(239,232,214),(58,37):(211,205,188),
                (58,38):(231,224,206),(59,38):(196,190,175),
                (59,39):(239,232,214),(59,40):(211,205,188),
                (60,41):(231,224,206),(60,42):(178,173,158)}
    for (x,y),rgb in right_bone.items():
        if p[x,y][3] and (x,y) in inactive: p[x,y]=(*rgb,255)

    # Extension-zero tail: retain the reference's round terminal silhouette; replace
    # the green center with a dark teal circular core and only three separate clasps.
    core={}
    for y,xlo,xhi in ((48,11,14),(49,9,16),(50,8,16),(51,8,16),(52,8,16),
                      (53,9,15),(54,10,14),(55,11,13)):
        for x in range(xlo,xhi+1): core[(x,y)]=(4,37,47)
    for xy,rgb in {(10,49):(7,53,63),(12,49):(5,30,39),(9,50):(3,31,41),
                   (13,50):(8,47,54),(10,51):(6,47,56),(12,52):(3,29,38),
                   (11,53):(7,49,57),(12,54):(4,34,43)}.items(): core[xy]=rgb
    for (x,y),rgb in core.items():
        if p[x,y][3] and (x,y) in inactive: p[x,y]=(*rgb,255)
    tail_cyan={(10,49):(26,132,144),(11,50):(18,110,125),(10,52):(27,140,151)}
    for (x,y),rgb in tail_cyan.items():
        if p[x,y][3] and (x,y) in inactive: p[x,y]=(*rgb,255)
    clasps={(7,49):(208,202,186),(8,49):(235,228,209),(8,50):(199,193,178),
            (16,50):(216,209,191),(17,51):(236,229,210),(16,52):(198,192,177),
            (9,56):(210,204,188),(10,57):(234,227,208)}
    for (x,y),rgb in clasps.items():
        if p[x,y][3] and (x,y) in inactive: p[x,y]=(*rgb,255)

    # Active tuning star is restored from the exact master after underlay painting.
    for mask in tiers['tuning']:
        for i,a in enumerate(mask.getdata()):
            if a:
                x,y=i%64,i//64; p[x,y]=reference.getpixel((x,y))
    return out

def save_board(v004, v095):
    states=[('v004  调谐I',v004),('v095  全满级·原图',v095)]
    font_label=font(18); margin=14; cell=256; label=30; gap=12
    board=Image.new('RGB',(margin*2+2*cell+gap,margin*2+2*(label+cell+gap)),(238,241,244))
    d=ImageDraw.Draw(board)
    for row,bg in enumerate(((255,255,255),(25,31,39))):
        y0=margin+row*(label+cell+gap)
        for col,(title,sprite) in enumerate(states):
            x=margin+col*(cell+gap)
            d.text((x,y0+2),title,font=font_label,fill=(30,35,41))
            shown=sprite.resize((cell,cell),Image.Resampling.NEAREST)
            board.paste(flatten(shown,bg),(x,y0+label))
    board.save(OUT/'v004-v095-white-dark-4x.png')
    for index,sprite in ((4,v004),(95,v095)):
        sprite.save(OUT/f'v{index:03d}-native64.png')
        for size in (16,32): sprite.resize((size,size),Image.Resampling.NEAREST).save(OUT/f'v{index:03d}-{size}px.png')

def main():
    raw=Image.open(REF_PATH).convert('RGBA')
    digest=hashlib.sha256(REF_PATH.read_bytes()).hexdigest().upper()
    if digest!=REF_SHA: raise SystemExit(f'wrong selected master sha: {digest}')
    approved=Image.open(ROOT/'artwork/source/approved-reference-oct03-64/approved-reference-normalized64.png').convert('RGBA')
    if list(raw.getdata())!=list(approved.getdata()): raise SystemExit('selected master and approved normalized image differ')
    b=get_builder(); tiers,unions,sets=b.feature_masks(raw)
    v004=paint_low_tier(raw,tiers); v095=raw.copy()
    v004.save(OUT/'v004-tuning-only-native64.png')
    v095.save(OUT/'v095-fullmax-master-exact.png')
    save_board(v004,v095)
    changed=[(i%64,i//64) for i,(a,c) in enumerate(zip(raw.getdata(),v004.getdata())) if a!=c]
    doc={'referenceSha256':digest,'rgbaComparedToApprovedMaster':'exact','stateIndex':4,
         'levels':{'resonance':0,'frequency':0,'tuning':1,'extension':0},
         'changedTexelCount':len(changed),'fullmaxState':'direct pixel-exact copy of user-selected master',
         'ordinaryStateAndResourcesTouched':False,'candidateOrProductionTouched':False,
         'changedTexels':changed}
    (OUT/'v004-draft-map.json').write_text(json.dumps(doc,indent=2)+'\n',encoding='utf-8')
    print(OUT/'v004-v095-white-dark-4x.png')
    print(f'changed={len(changed)}; source={digest}')

if __name__=='__main__': main()
