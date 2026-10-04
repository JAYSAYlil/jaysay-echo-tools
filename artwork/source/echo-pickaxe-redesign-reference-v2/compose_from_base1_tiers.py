"""Static tier sprites: imagegen-derived64 base -> selected full-upgrade master."""
from __future__ import annotations
import hashlib, importlib.util, json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[3]
SRC=ROOT/'artwork/source/echo-pickaxe-redesign-reference-v2'
OUT=ROOT/'artwork/validation/v0.1.11/redesign-v2/base1-tier-design'
BASE=ROOT/'artwork/validation/v0.1.11/redesign-v2/imagegen-v004-derived64.png'
MASTER=SRC/'user-reference.png'
ORDINARY=ROOT/'src/main/resources/assets/echopickaxe/textures/item/echo_pickaxe.png'
BUILDER=ROOT/'artwork/source/approved-reference-oct03-64/build_approved64_variants.py'

def load_builder():
    sp=importlib.util.spec_from_file_location('approved_masks_readonly',BUILDER); m=importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest().upper()
def coords(mask):
    p=mask.load(); return {(x,y) for y in range(64) for x in range(64) if p[x,y]}
def opaque(im,x,y): return 0<=x<64 and 0<=y<64 and im.getpixel((x,y))[3]>0
def font(sz):
    for f in (r'C:\Windows\Fonts\msyh.ttc',r'C:\Windows\Fonts\arial.ttf'):
        if Path(f).exists(): return ImageFont.truetype(f,sz)
    return ImageFont.load_default()
def put(im,points,color,master=None):
    p=im.load()
    for x,y in points:
        if opaque(im,x,y) or (master is not None and opaque(master,x,y)): p[x,y]=(*color,255)
def rows(im,table,color,master=None):
    for y,(x0,x1) in table.items(): put(im,[(x,y) for x in range(x0,x1+1)],color,master)
def poly(im,pts,color,master=None):
    mask=Image.new('L',(64,64)); ImageDraw.Draw(mask).polygon(pts,fill=255)
    put(im,coords(mask),color,master)

def sampled_dark(base,exclude,point):
    p=base.load(); x0,y0=point
    candidates=[(x,y) for y in range(64) for x in range(64) if (x,y) not in exclude and opaque(base,x,y)
                and max(p[x,y][:3])<125 and p[x,y][0]<p[x,y][1]+24 and p[x,y][0]<p[x,y][2]+28]
    if not candidates: return (0,28,38)
    sx,sy=min(candidates,key=lambda q:((q[0]-x0)**2+(q[1]-y0)**2,q[1],q[0]))
    return p[sx,sy][:3]

def paint_red(im,level,master,source_tiers):
    # Local native64 crescent facets follow image one's existing hooked blade.
    body={6:(26,30),7:(22,33),8:(19,34),9:(17,34),10:(17,32),11:(18,30),12:(20,29),13:(22,29)}
    if level>=2: body.update({5:(29,35),6:(24,36),14:(24,31),15:(26,33),16:(28,34),17:(30,34)})
    rows(im,body,(84,5,24),master)
    poly(im,[(19,8),(24,6),(30,7),(33,10),(29,12),(24,12),(20,11)],(148,7,34),master)
    poly(im,[(18,9),(21,8),(24,9),(24,11),(21,12),(18,11)],(205,18,46),master)
    poly(im,[(22,11),(28,10),(31,12),(28,15),(24,15),(21,13)],(111,4,26),master)
    for xy,c in { (19,8):(255,218,184),(20,8):(255,91,82),(25,7):(229,34,54),(29,8):(255,75,71),(31,9):(253,42,61) }.items(): put(im,[xy],c,master)
    if level>=2:
        poly(im,[(28,5),(34,5),(37,7),(36,10),(32,11),(29,9)],(175,8,37),master)
        poly(im,[(25,13),(30,12),(34,13),(33,17),(29,18),(26,16)],(136,6,32),master)
        poly(im,[(28,6),(32,5),(35,7),(33,9),(29,9)],(226,28,50),master)
        for xy,c in { (33,6):(255,219,184),(35,7):(255,103,78),(31,15):(221,35,54) }.items(): put(im,[xy],c,master)
    # Transfer actual mother-crystal faceting through a local normalized mapping;
    # the receiving silhouette is image-one's blade, not the mother mask crop.
    source=set().union(*(coords(m) for m in source_tiers[:level]))
    target={(x,y) for y in range(5,19) for x in range(16,39) if opaque(im,x,y)
            and im.getpixel((x,y))[0]>im.getpixel((x,y))[1]*1.35}
    map_facets(im,master,target,source)

def paint_purple(im,level,master,source_tiers):
    stages=[
      {18:(47,51),19:(47,52),20:(48,53),21:(49,54),22:(50,55),23:(51,56)},
      {23:(50,56),24:(51,57),25:(52,58),26:(53,59),27:(54,60),28:(55,60),29:(56,61)},
      {29:(55,61),30:(56,62),31:(57,62),32:(58,62),33:(59,62),34:(60,62),35:(60,62),36:(61,62),37:(61,62),38:(61,62),39:(61,62),40:(61,62),41:(61,62),42:(61,62)}]
    for n in range(level):
        rows(im,stages[n],(42,13,76),master)
        # One long plane plus a narrower light facet gives each shell volume.
        for y,(x0,x1) in stages[n].items():
            mid=(x0+x1)//2
            put(im,[(mid,y)],(116,39,171),master)
        facets=[(49,18),(52,23),(57,29)]
        highlights=[(49,18),(53,24),(58,30)]
        glints=[(49,18),(53,24),(59,31)]
        if n<len(facets):
            x,y=facets[n]; put(im,[(x,y)],(177,78,219),master)
        if n<len(highlights):
            x,y=highlights[n]; put(im,[(x,y)],(222,135,242),master)
        if n<len(glints):
            x,y=glints[n]; put(im,[(x,y)],(255,231,255),master)
    active_sources=set().union(*(coords(m) for m in source_tiers[:level]))
    target={(x,y) for y in range(15,44) for x in range(44,64) if opaque(im,x,y)
            and im.getpixel((x,y))[2]>im.getpixel((x,y))[0]*1.35}
    map_facets(im,master,target,active_sources)

def map_facets(target_im,source_im,target_coords,source_coords):
    if not target_coords or not source_coords: return
    tx0=min(x for x,y in target_coords); tx1=max(x for x,y in target_coords)
    ty0=min(y for x,y in target_coords); ty1=max(y for x,y in target_coords)
    sx0=min(x for x,y in source_coords); sx1=max(x for x,y in source_coords)
    sy0=min(y for x,y in source_coords); sy1=max(y for x,y in source_coords)
    sp=source_im.load(); tp=target_im.load()
    for x,y in target_coords:
        u=0 if tx1==tx0 else (x-tx0)/(tx1-tx0); v=0 if ty1==ty0 else (y-ty0)/(ty1-ty0)
        sx=sx0+u*(sx1-sx0); sy=sy0+v*(sy1-sy0)
        q=min(source_coords,key=lambda p:((p[0]-sx)**2+(p[1]-sy)**2,abs(p[0]-sx)+abs(p[1]-sy),p[1],p[0]))
        if tp[x,y][3] or sp[q[0],q[1]][3]: tp[x,y]=sp[q[0],q[1]]

def paint_star(im,star,master):
    p,mp=im.load(),master.load()
    for x,y in star:
        if opaque(im,x,y) or opaque(master,x,y): p[x,y]=mp[x,y]

def bone_recolor(im,base,region,exclude):
    p,bp=im.load(),base.load()
    for x,y in region:
        r,g,b,a=bp[x,y]
        if not a or not (r>125 and g>112 and b>95 and r>=g*.94 and g>=b*.90): continue
        color=sampled_dark(base,exclude,(x,y)); p[x,y]=(*color,255)

def paint_extension(im,base,master,level):
    cx,cy=10,54; p,bp=im.load(),base.load()
    # Convert the base's cyan pommel in place; preserve its faceted value map.
    for y in range(48,59):
      for x in range(5,16):
        if (x-cx)**2+(y-cy)**2>28 or not opaque(im,x,y): continue
        r,g,b,a=bp[x,y]
        if g>r*1.25 and b>r*1.2:
            shade=max(g,b)
            if shade>205: c=(23,132,99) if level==1 else (31,178,118)
            elif shade>140: c=(8,106,80) if level==1 else (10,145,97)
            else: c=(4,61,55)
            p[x,y]=(*c,255)
    if level>=2:
        for xy,c in { (9,52):(22,153,101),(10,52):(40,192,132),(9,53):(8,119,81),
                      (10,53):(220,250,226),(11,53):(37,211,144),(10,54):(9,131,89),
                      (11,54):(13,157,103) }.items(): put(im,[xy],c,master)
    if level>=3:
        for y in range(45,62):
          for x in range(4,20):
            if opaque(master,x,y) and (x-cx)**2+(y-cy)**2<=38 and not opaque(im,x,y):
                p[x,y]=master.getpixel((x,y))
        # Add four short separated bone clips within the existing native alpha.
        ivory=(233,226,207); shade=(172,169,151)
        for group in [[(7,50),(8,50)],[(13,50),(14,51)],[(6,54),(7,55)],[(12,58),(13,58)]]:
            for i,xy in enumerate(group): put(im,[xy],ivory if i==0 else shade,master)

def compose(base,master,levels,star):
    # All levels share image one's body; active components grow locally toward
    # image two's module facets and shapes, avoiding a last-step whole-sprite swap.
    im=base.copy(); p=im.load(); bp=base.load()
    bone_palette=[(198,193,177),(226,220,201),(244,238,218)]
    left_region={(x,y) for y in range(5,25) for x in range(15,38)}
    right_region={(x,y) for y in range(16,44) for x in range(45,64)}
    excluded=left_region|right_region
    if levels['resonance']>=1:
        bone_recolor(im,base,left_region,set())
        builder=load_builder(); ref_tiers,_,_=builder.feature_masks(master)
        paint_red(im,levels['resonance'],master,ref_tiers['resonance'])
    if levels['frequency']>=1:
        bone_recolor(im,base,right_region,set())
        builder=load_builder(); ref_tiers,_,_=builder.feature_masks(master)
        paint_purple(im,levels['frequency'],master,ref_tiers['frequency'])
    if levels['tuning']>=1: paint_star(im,star,master)
    if levels['extension']>=1: paint_extension(im,base,master,levels['extension'])
    return im

def board(cells,path,scale=4):
    margin,gap,label=16,16,28; tile=64*scale; cols=5; rows_n=(len(cells)+4)//5
    w=margin*2+cols*tile+(cols-1)*gap; h=margin*2+rows_n*(label+tile+gap)
    out=Image.new('RGB',(w,h*2),(235,238,241)); d=ImageDraw.Draw(out); f=font(16)
    for theme,bg in enumerate(((255,255,255),(22,27,34))):
      for i,(name,im) in enumerate(cells):
        row,col=divmod(i,cols); x=margin+col*(tile+gap); y=theme*h+margin+row*(label+tile+gap)
        d.text((x,y+2),name,font=f,fill=(25,30,36) if theme==0 else (235,239,243))
        show=im.resize((tile,tile),Image.Resampling.NEAREST); tileimg=Image.new('RGBA',show.size,(*bg,255)); tileimg.alpha_composite(show); out.paste(tileimg.convert('RGB'),(x,y+label))
    out.save(path)

def make_small_board(cells,side,path):
    margin,gap,label,scale=16,12,25,4; tile=side*scale; cols=5; rows_n=(len(cells)+4)//5
    w=margin*2+cols*tile+(cols-1)*gap; h=margin*2+rows_n*(label+tile+gap)
    out=Image.new('RGB',(w,h*2),(235,238,241)); d=ImageDraw.Draw(out); f=font(14)
    for theme,bg in enumerate(((255,255,255),(22,27,34))):
      for i,(name,im) in enumerate(cells):
        row,col=divmod(i,cols); x=margin+col*(tile+gap); y=theme*h+margin+row*(label+tile+gap)
        d.text((x,y+2),name,font=f,fill=(25,30,36) if theme==0 else (235,239,243))
        show=im.resize((side,side),Image.Resampling.NEAREST).resize((tile,tile),Image.Resampling.NEAREST); ti=Image.new('RGBA',show.size,(*bg,255)); ti.alpha_composite(show); out.paste(ti.convert('RGB'),(x,y+label))
    out.save(path)

def alpha_component_count(im):
    remaining={(x,y) for y in range(64) for x in range(64) if im.getpixel((x,y))[3]}
    count=0
    while remaining:
      count+=1; stack=[remaining.pop()]
      while stack:
        x,y=stack.pop()
        for q in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
          if q in remaining: remaining.remove(q); stack.append(q)
    return count

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    base=Image.open(BASE).convert('RGBA'); master=Image.open(MASTER).convert('RGBA')
    builder=load_builder(); tiers,_,_=builder.feature_masks(master); star=coords(tiers['tuning'][0])
    states=[
      (0,'普通原版',{ 'resonance':0,'frequency':0,'tuning':0,'extension':0}),
      (4,'调谐 I',{'resonance':0,'frequency':0,'tuning':1,'extension':0}),
      (8,'分频 I',{'resonance':0,'frequency':1,'tuning':0,'extension':0}),
      (16,'分频 II',{'resonance':0,'frequency':2,'tuning':0,'extension':0}),
      (24,'分频 III',{'resonance':0,'frequency':3,'tuning':0,'extension':0}),
      (32,'共振 I',{'resonance':1,'frequency':0,'tuning':0,'extension':0}),
      (64,'共振 II',{'resonance':2,'frequency':0,'tuning':0,'extension':0}),
      (1,'延展 I',{'resonance':0,'frequency':0,'tuning':0,'extension':1}),
      (2,'延展 II',{'resonance':0,'frequency':0,'tuning':0,'extension':2}),
      (3,'延展 III',{'resonance':0,'frequency':0,'tuning':0,'extension':3}),
      (87,'近满级：分频II',{'resonance':2,'frequency':2,'tuning':1,'extension':3}),
      (91,'近满级：未调谐',{'resonance':2,'frequency':3,'tuning':0,'extension':3}),
      (94,'近满级：延展II',{'resonance':2,'frequency':3,'tuning':1,'extension':2}),
      (95,'全满级设计',{'resonance':2,'frequency':3,'tuning':1,'extension':3}),
    ]
    cells=[]; records=[]
    for index,name,levels in states:
      im=base.copy() if index==0 else compose(base,master,levels,star)
      if alpha_component_count(im)!=1: raise RuntimeError(f'v{index:03d} has disconnected alpha')
      im.save(OUT/f'base1-v{index:03d}-64.png')
      im.resize((32,32),Image.Resampling.NEAREST).save(OUT/f'base1-v{index:03d}-32.png')
      im.resize((16,16),Image.Resampling.NEAREST).save(OUT/f'base1-v{index:03d}-16.png')
      cells.append((f'v{index:03d} {name}',im)); records.append({'index':index,'name':name,'levels':levels,'sha256':hashlib.sha256((OUT/f'base1-v{index:03d}-64.png').read_bytes()).hexdigest().upper()})
    cells.append(('强化母图参考',master.copy()))
    board(cells,OUT/'base1-tier-progression-white-dark-4x.png')
    make_small_board(cells,32,OUT/'base1-tier-progression-32px-white-dark.png')
    make_small_board(cells,16,OUT/'base1-tier-progression-16px-white-dark.png')
    record={'status':'static redesign draft only; production untouched','ordinaryBase':'imagegen-v004-derived64.png; v000 RGBA exact','fullmax':'native64 module-complete image-one design, guided by user-reference.png','ordinaryBaseSha256':hashlib.sha256(BASE.read_bytes()).hexdigest().upper(),'referenceSha256':hashlib.sha256(MASTER.read_bytes()).hexdigest().upper(),'states':records,'note':'All nonzero tiers share image-one body and shaft. Red/purple facets are sampled from image two and redrawn into image-one blade shapes; local alpha grows along the right blade and pommel at higher tiers. Full design retains image-one common body to avoid a whole-sprite switch. No ordinary/source32 texture is sampled.'}
    (OUT/'base1-tier-design-map.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(OUT/'base1-tier-progression-white-dark-4x.png')

if __name__=='__main__':main()
