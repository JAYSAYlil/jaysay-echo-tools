"""Full-tier static overlay study on the accepted tight-derived64 body."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'artwork/validation/v0.1.11/redesign-v2'
BASE=OUT/'imagegen-v004-tight-derived64.png'
MASTER=ROOT/'artwork/source/echo-pickaxe-redesign-reference-v2/user-reference.png'

def font(size):
    for p in (r'C:\Windows\Fonts\msyh.ttc',r'C:\Windows\Fonts\arial.ttf'):
        if Path(p).is_file(): return ImageFont.truetype(p,size)
    return ImageFont.load_default()

def setpix(p,x,y,color):
    if 0<=x<64 and 0<=y<64 and p[x,y][3]: p[x,y]=(*color,255)

def spans(p,rows,color):
    for y,(x0,x1) in rows.items():
        for x in range(x0,x1+1): setpix(p,x,y,color)

def poly(im,points,color):
    mask=Image.new('L',(64,64)); ImageDraw.Draw(mask).polygon(points,fill=255); p=im.load()
    for y in range(64):
        for x in range(64):
            if mask.getpixel((x,y)): setpix(p,x,y,color)

def red_overlay(im,level):
    p=im.load()
    # Remove the complete exposed bone edge in the left-blade socket before drawing
    # the active resonance crystal; no bare bone may remain under res>=1.
    for y in range(5,23):
        for x in range(19,35):
            r,g,b,a=p[x,y]
            if a and r>=160 and g>=150 and b>=130 and r>=g-20 and g>=b-24:
                p[x,y]=(65,6,23,255)
    # Level I covers the current tight64 left blade (not the old normalized-red mask).
    # This is about 60 native texels across the curved blade's existing alpha.
    level1={6:(28,34),7:(25,34),8:(22,34),9:(20,33),10:(19,33),
            11:(19,32),12:(20,32),13:(26,34),14:(27,34),15:(28,34)}
    spans(p,level1,(77,5,23))
    # Two clearly separated facets and a short warm crown glint; preserve a dark
    # ruby fracture between them instead of one flat red triangle.
    poly(im,[(25,6),(31,6),(34,9),(31,11),(27,10),(23,9)],(179,17,41))
    poly(im,[(20,9),(25,9),(29,12),(28,14),(24,14),(20,12)],(132,8,31))
    poly(im,[(30,11),(33,10),(34,13),(32,15),(30,14)],(90,2,25))
    poly(im,[(25,7),(29,7),(31,9),(28,10),(24,9)],(205,12,49))
    poly(im,[(27,9),(28,10),(27,11),(26,10)],(25,0,12))
    poly(im,[(26,11),(27,12),(28,13)],(25,0,12))
    for xy,c in {(29,7):(255,73,68),(30,8):(255,218,184),(25,8):(238,53,63),
                 (21,10):(255,218,184),(22,9):(245,154,117),(31,12):(125,4,29)}.items(): setpix(p,*xy,c)
    if level>=2:
        # Level II adds a connected lower facet and two small crown reflections.
        spans(p,{16:(29,34),17:(30,34),18:(31,34),19:(31,34),20:(32,34)},(83,5,26))
        poly(im,[(29,11),(33,10),(35,12),(33,15),(30,15)],(153,10,35))
        poly(im,[(31,15),(34,14),(35,16),(33,18),(31,17)],(83,5,26))
        for xy,c in {(32,11):(236,39,56),(33,12):(251,91,83),(31,16):(255,112,84)}.items(): setpix(p,*xy,c)
    return im

def purple_overlay(im,level):
    p=im.load()
    # Remove the bare bone edge first. Crystal facets then occupy the actual new right
    # blade shoulder/arc; every module texel is constrained to the reviewed body alpha.
    for y in range(13,45):
        for x in range(47,64):
            r,g,b,a=p[x,y]
            if a and r>=160 and g>=150 and b>=130 and r>=g-20 and g>=b-24:
                p[x,y]=(4,26,35,255)
    segments=[
      # Frequency I: two small, separated upper crystal faces.
      {15:(49,50),16:(49,51),17:(50,51)},
      {20:(52,53),21:(52,55),22:(53,56),23:(54,56)},
      # Frequency II: a larger central shell separated by 3 sculk texels.
      {27:(55,57),28:(54,58),29:(55,59),30:(57,60)},
      # Frequency III: a tapering lower blade segment; 4 dark body rows remain above it.
      {35:(58,60),36:(59,61),37:(59,61),38:(60,61),39:(60,62),
       40:(61,62),41:(61,62),42:(61,62),43:(61,62)},
    ]
    segment_colors=[(43,13,76),(43,13,76),(43,13,76),(43,13,76)]
    coords=[]
    for i,rows in enumerate(segments[:level+1]):
        for y,(x0,x1) in rows.items():
            for x in range(x0,x1+1):
                if p[x,y][3]: p[x,y]=(*segment_colors[i],255); coords.append((i,x,y))
    # Three contrasting planes and restrained jewel glints within each discrete shell.
    facets={
      (0,49,15):(133,41,183),(0,50,16):(191,82,224),(0,51,17):(73,22,117),
      (1,53,20):(102,32,157),(1,54,21):(177,81,224),(1,55,22):(94,28,145),
      (2,55,28):(99,30,151),(2,57,28):(174,74,220),(2,58,29):(211,112,241),
      (2,59,30):(103,33,157),(3,59,36):(106,32,158),(3,60,37):(175,76,220),
      (3,61,40):(197,103,234),
    }
    coordset={(i,x,y) for i,x,y in coords}
    for key,c in facets.items():
        if key in coordset: setpix(p,key[1],key[2],c)
    glints={(0,49,15):(250,226,255),(1,53,20):(249,221,255),
            (2,57,28):(252,227,255),(3,60,37):(249,214,255)}
    for key,c in glints.items():
        if key in coordset: setpix(p,key[1],key[2],c)
    return im

def green_extension(im):
    p=im.load(); cx,cy=12,53
    clasps={(x,y) for y,lo,hi in [(47,13,15),(48,13,15),(49,13,15),
                                  (51,6,7),(52,6,7),(53,6,7),
                                  (51,16,17),(52,16,17),(53,16,17),
                                  (57,12,14),(58,12,14),(59,12,14)] for x in range(lo,hi+1)}
    # Hue-map the existing cyan facet pattern into emerald while retaining each source
    # pixel's value contrast and facet boundaries; no flat green disk is painted.
    for y in range(47,60):
        for x in range(5,20):
            if (x-cx)**2+(y-cy)**2<=30 and (x,y) not in clasps and p[x,y][3]:
                r,g,b,_=p[x,y]
                p[x,y]=(max(1,round(r*.12)),min(255,round(g*.78+b*.20)),min(160,round(g*.12+b*.32)),255)
    # The source core's cyan node becomes a clear ivory-green eye; keep the glint small.
    for xy,c in {(11,51):(9,145,103),(12,51):(39,205,148),(11,52):(14,176,126),
                 (12,52):(193,246,220),(13,52):(27,211,153),(12,53):(7,137,102),
                 (12,54):(4,81,65)}.items(): setpix(p,*xy,c)
    # Preserve the four existing separated ivory clasps exactly from the tight base.
    return im

def board(full,master):
    label=30; margin=14; gap=18; scale=5; tile=64*scale
    w=margin*2+2*tile+gap; h=margin*2+2*(label+tile+gap)
    out=Image.new('RGB',(w,h),(237,240,243)); d=ImageDraw.Draw(out); f=font(17)
    for row,bg in enumerate(((255,255,255),(24,30,38))):
        y=margin+row*(label+tile+gap)
        for col,(name,im) in enumerate((('tight body + 手绘模块 v095',full),('用户母图 v095',master))):
            x=margin+col*(tile+gap); d.text((x,y+3),name,font=f,fill=(25,31,38))
            shown=im.resize((tile,tile),Image.Resampling.NEAREST)
            bgim=Image.new('RGBA',shown.size,(*bg,255)); bgim.alpha_composite(shown)
            out.paste(bgim.convert('RGB'),(x,y+label))
    out.save(OUT/'v2-v095-vs-master-white-dark-5x.png')

def tier_board(states,ordinary):
    cells=[('普通未改 32px',ordinary,32),*[(name,im,64) for name,im in states]]
    margin=14; gap=12; label=30; widths=[size*4 for _,_,size in cells]
    xs=[]; cursor=margin
    for w in widths: xs.append(cursor); cursor+=w+gap
    width=cursor-gap+margin; row_h=label+256+gap
    out=Image.new('RGB',(width,margin*2+2*row_h),(237,240,243)); d=ImageDraw.Draw(out); f=font(16)
    for row,bg in enumerate(((255,255,255),(24,30,38))):
        y=margin+row*row_h
        for i,(name,im,size) in enumerate(cells):
            d.text((xs[i],y+2),name,font=f,fill=(25,31,38))
            small=im.resize((size*4,size*4),Image.Resampling.NEAREST)
            tile=Image.new('RGBA',small.size,(*bg,255)); tile.alpha_composite(small)
            out.paste(tile.convert('RGB'),(xs[i],y+label))
    out.save(OUT/'v2-tier-draft-white-dark-4x.png')

def main():
    base=Image.open(BASE).convert('RGBA'); master=Image.open(MASTER).convert('RGBA')
    full=red_overlay(base.copy(),2)
    full=purple_overlay(full,3)
    full=green_extension(full)
    full.save(OUT/'v2-v095-native64.png')
    full.resize((32,32),Image.Resampling.NEAREST).save(OUT/'v2-v095-32px.png')
    board(full,master)
    # Compose a compact real-state board from the same exact underlay.
    from importlib.util import spec_from_file_location,module_from_spec
    helper_path=Path(__file__).resolve().parent/'draft_tiers_from_tight.py'
    spec=spec_from_file_location('tight_tier_helpers',helper_path); helper=module_from_spec(spec); spec.loader.exec_module(helper)
    builder_path=ROOT/'artwork/source/approved-reference-oct03-64/build_approved64_variants.py'
    spec=spec_from_file_location('master_star_socket',builder_path); builder=module_from_spec(spec); spec.loader.exec_module(builder)
    ref=Image.open(ROOT/'artwork/source/approved-reference-oct03-64/approved-reference-normalized64.png').convert('RGBA')
    tiers,_,_=builder.feature_masks(ref)
    star={(i%64,i//64) for i,v in enumerate(tiers['tuning'][0].getdata()) if v}
    v008=helper.remove_star(purple_overlay(base.copy(),1),star)
    v032=helper.remove_star(red_overlay(base.copy(),1),star)
    v004=base.copy()
    ordinary=helper.load_ordinary()
    tier_states=[('v004 调谐I',v004),('v008 分频I',v008),('v032 共振I',v032),('v095 全满级',full)]
    tier_board(tier_states,ordinary)
    for index,im in ((4,v004),(8,v008),(32,v032),(95,full)):
        im.save(OUT/f'v2-v{index:03d}-native64.png')
        for side in (16,32): im.resize((side,side),Image.Resampling.NEAREST).save(OUT/f'v2-v{index:03d}-{side}px.png')
    (OUT/'v2-v095-component-note.json').write_text(json.dumps({
      'base':'imagegen-v004-tight-derived64.png; same underlying body retained',
      'modules':'native64 hand-painted tier facets placed using actual tight alpha coordinates',
      'ordinaryAndProductionChanged':False,
      'status':'static draft only; awaiting visual review'
    },indent=2)+'\n',encoding='utf-8')
    print(OUT/'v2-v095-vs-master-white-dark-5x.png')

if __name__=='__main__':main()
