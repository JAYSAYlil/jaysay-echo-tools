"""Compose static tier studies on the reviewed tight-derived64 body; no production output."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import zipfile, json, hashlib

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'artwork/validation/v0.1.11/redesign-v2'
BASE=OUT/'imagegen-v004-tight-derived64.png'
JAR=ROOT/'jaysay-echo-tools-0.1.10.jar'
SRC_ORD='src/main/resources/assets/echopickaxe/textures/item/echo_pickaxe.png'

def font(size):
    for p in (r'C:\Windows\Fonts\msyh.ttc',r'C:\Windows\Fonts\arial.ttf'):
        if Path(p).is_file(): return ImageFont.truetype(p,size)
    return ImageFont.load_default()

def bone(rgb):
    r,g,b=rgb
    return r>=160 and g>=150 and b>=130 and r>=g-20 and g>=b-24

def pixels_in_box(im,box):
    p=im.load(); x0,y0,x1,y1=box
    return {(x,y) for y in range(y0,y1) for x in range(x0,x1) if p[x,y][3]}

def fill_pixel(p,x,y,rgb):
    if 0<=x<64 and 0<=y<64 and p[x,y][3]: p[x,y]=(*rgb,255)

def draw_runs(p,rows,colors):
    for y,(x0,x1) in rows.items():
        for x in range(x0,x1+1): fill_pixel(p,x,y,colors)

def draw_facets(image,planes):
    p=image.load()
    for points,color in planes:
        mask=Image.new('L',(64,64)); ImageDraw.Draw(mask).polygon(points,fill=255)
        for y in range(64):
            for x in range(64):
                if mask.getpixel((x,y)): fill_pixel(p,x,y,color)

def remove_star(state, star_coords):
    out=state.copy(); p=out.load(); base=state.load()
    # The tight redraw keeps the same star socket but raster bounds can move a ray
    # one texel; include the socket's pale rays while excluding cyan veins.
    coords=set(star_coords)
    for y in range(11,22):
        for x in range(35,46):
            r,g,b,a=base[x,y]
            if a and min(r,g,b)>135 and b>=r*.92 and g>=r*.78:
                coords.add((x,y))
    for x,y in coords:
        candidates=[]
        for r in range(1,4):
            for yy in range(max(0,y-r),min(64,y+r+1)):
                for xx in range(max(0,x-r),min(64,x+r+1)):
                    if max(abs(xx-x),abs(yy-y))!=r or not base[xx,yy][3]: continue
                    rr,gg,bb,_=base[xx,yy]
                    if rr<100 and gg<130 and bb<150: candidates.append((xx,yy,(rr,gg,bb)))
            if candidates: break
        if candidates:
            sx,sy,rgb=min(candidates,key=lambda q:(q[0]-x)**2+(q[1]-y)**2)
            p[x,y]=(*rgb,255)
    return out

def make_states(base,star_coords):
    # Tier masks are hand-positioned on the tight64 layout, not pasted from old master masks.
    # v004 remains the exact accepted no-res/no-freq/no-extension body.
    v004=base.copy()
    left_bone={xy for xy in pixels_in_box(base,(5,4,35,27)) if bone(base.getpixel(xy)[:3])}
    right_bone={xy for xy in pixels_in_box(base,(50,15,64,45)) if bone(base.getpixel(xy)[:3])}
    tail_bone={xy for xy in pixels_in_box(base,(4,43,21,63)) if bone(base.getpixel(xy)[:3])}
    # Resonance I overlays a compact red facet set where the bare curved left blade sits.
    res=v004.copy(); rp=res.load()
    for x,y in left_bone: fill_pixel(rp,x,y,(79,5,23))
    red_rows={6:(28,32),7:(26,34),8:(23,33),9:(21,31),10:(20,29),11:(20,27),
              12:(21,26),13:(22,27),14:(24,29),15:(26,30),16:(28,31),17:(30,32)}
    draw_runs(rp,red_rows,(78,5,23))
    draw_facets(res,[
      ([(27,6),(32,6),(34,8),(30,9),(26,8)],(210,21,47)),
      ([(23,8),(29,8),(32,10),(28,12),(22,11)],(132,9,31)),
      ([(20,11),(25,10),(28,12),(27,15),(23,15),(20,13)],(177,17,40)),
      ([(29,9),(31,8),(30,10)],(255,112,91)),
    ])

    # Frequency I replaces the full exposed bone edge with a short purple sculk-crystal blade.
    freq=v004.copy(); fp=freq.load()
    for x,y in right_bone: fill_pixel(fp,x,y,(36,15,70))
    purple_rows={19:(54,56),20:(54,57),21:(55,58),22:(55,59),23:(56,60),24:(56,60),
                 25:(57,61),26:(57,61),27:(58,62),28:(58,62),29:(59,62),30:(59,62),
                 31:(60,62),32:(60,62),33:(60,62),34:(60,62),35:(60,62),36:(60,62),
                 37:(60,62),38:(60,62),39:(60,62),40:(60,62),41:(61,62),42:(61,62)}
    draw_runs(fp,purple_rows,(45,15,79))
    draw_facets(freq,[
      ([(55,20),(58,21),(60,25),(57,25)],(111,41,166)),
      ([(57,25),(60,26),(62,31),(59,33)],(153,67,205)),
      ([(60,31),(62,32),(62,38),(61,40)],(93,31,143)),
      ([(57,22),(58,23),(58,24)],(223,163,247)),
    ])

    # Full state uses the same tight64 body/head/shaft, overlays both blades and a green
    # round ext core at the same reference-sized tail socket; the central star is unchanged.
    full=res.copy(); fp=full.load()
    for x,y in right_bone: fill_pixel(fp,x,y,(36,15,70))
    draw_runs(fp,purple_rows,(45,15,79))
    draw_facets(full,[
      ([(55,20),(58,21),(60,25),(57,25)],(111,41,166)),
      ([(57,25),(60,26),(62,31),(59,33)],(153,67,205)),
      ([(60,31),(62,32),(62,38),(61,40)],(93,31,143)),
      ([(57,22),(58,23),(58,24)],(223,163,247)),
    ])
    # Recolor a compact circular core, leaving the three separate bone clasps around it.
    cx,cy=11,52
    for y in range(47,59):
        for x in range(5,19):
            if (x-cx)**2+(y-cy)**2<=25 and (x,y) not in tail_bone:
                if base.getpixel((x,y))[3]:
                    d=(x-cx)**2+(y-cy)**2
                    rgb=(2,71,58) if d<=10 else (1,43,45)
                    fill_pixel(fp,x,y,rgb)
    # Four restrained green facets, with the eye at the master socket center.
    for xy,c in { (10,50):(4,111,83),(11,50):(7,177,126),(12,51):(11,219,157),
                  (10,52):(5,144,108),(11,52):(11,237,181),(12,53):(3,114,88),
                  (10,54):(4,75,67),(11,54):(5,136,103) }.items(): fill_pixel(fp,*xy,c)
    # Bone clasps remain short and separated; no continuous ring.
    for x,y in tail_bone:
        if base.getpixel((x,y))[3]: fill_pixel(fp,x,y,(199,191,174))
    return v004,freq,res,full,{'leftBoneMask':sorted(left_bone),'rightBoneMask':sorted(right_bone),
                               'tailBoneMask':sorted(tail_bone)}

def composite(im,bg):
    tile=Image.new('RGBA',im.size,(*bg,255)); tile.alpha_composite(im); return tile.convert('RGB')

def load_ordinary():
    # Read-only 32px comparison from current source; never modified by this script.
    im=Image.open(ROOT/SRC_ORD).convert('RGBA')
    if im.size!=(32,32): raise RuntimeError(f'ordinary preview is {im.size}, expected 32x32')
    return im

def save_board(states,ordinary):
    # Four-upgrader states plus untouched ordinary; fixed separate widths avoid overlap.
    font_label=font(16); margin=14; gap=12; labels=30
    cells=[('普通未改 32px',ordinary,32),*[(title,im,64) for title,im in states]]
    widths=[s*4 for _,_,s in cells]; xs=[]; cur=margin
    for w in widths: xs.append(cur); cur+=w+gap
    w=cur-gap+margin; row_h=labels+256+gap; h=margin*2+2*row_h
    board=Image.new('RGB',(w,h),(237,240,243)); d=ImageDraw.Draw(board)
    for row,bg in enumerate(((255,255,255),(24,30,38))):
        y=margin+row*row_h
        for i,(title,im,size) in enumerate(cells):
            x=xs[i]; d.text((x,y+2),title,font=font_label,fill=(25,31,38))
            shown=im.resize((size*4,size*4),Image.Resampling.NEAREST)
            board.paste(composite(shown,bg),(x,y+labels))
    board.save(OUT/'v2-tier-draft-white-dark-4x.png')
    for i,(title,im,size) in enumerate(cells[1:]):
        index=(4,8,32,95)[i]
        im.save(OUT/f'v2-v{index:03d}-native64.png')
        for side in (16,32): im.resize((side,side),Image.Resampling.NEAREST).save(OUT/f'v2-v{index:03d}-{side}px.png')

def main():
    base=Image.open(BASE).convert('RGBA')
    if base.size!=(64,64): raise SystemExit('tight source is not 64x64')
    # The unchanged tuning star remains in v004 and fullmax only.
    spec=__import__('importlib.util').util.spec_from_file_location('approved_masks_for_socket','artwork/source/approved-reference-oct03-64/build_approved64_variants.py')
    b=__import__('importlib.util').util.module_from_spec(spec); spec.loader.exec_module(b)
    ref=Image.open(ROOT/'artwork/source/approved-reference-oct03-64/approved-reference-normalized64.png').convert('RGBA')
    tiers,_,_=b.feature_masks(ref)
    star_coords={(i%64,i//64) for i,v in enumerate(tiers['tuning'][0].getdata()) if v}
    base_no_star=remove_star(base,star_coords)
    states=make_states(base,star_coords)
    v004,freq,res,full,masks=states
    freq=remove_star(freq,star_coords); res=remove_star(res,star_coords)
    ordinary=load_ordinary()
    save_board([('v004 调谐I',v004),('v008 分频I',freq),('v032 共振I',res),('v095 全满级',full)],ordinary)
    for name,im in [('v004',v004),('v008',freq),('v032',res),('v095',full)]:
        im.save(OUT/f'v2-{name}-native64.png')
    (OUT/'v2-state-compose-map.json').write_text(json.dumps({
      'baselineBody':'tight-derived64, shared exactly across v004/v008/v032/v095 before the explicit tier overlays',
      'referenceMaster':'user-reference.png; tight raw is a design-derived native64 source; no old common32/source32 RGB used',
      'states':{'v004':{'resonance':0,'frequency':0,'tuning':1,'extension':0},'v008':{'resonance':0,'frequency':1,'tuning':0,'extension':0},'v032':{'resonance':1,'frequency':0,'tuning':0,'extension':0},'v095':{'resonance':2,'frequency':3,'tuning':1,'extension':3}},
      'ordinaryPreviewOnly':'32px from src; no ordinary resource changed',
      'boneMasks':masks,'productionAssetsChanged':False
    },indent=2)+'\n',encoding='utf-8')
    print(OUT/'v2-tier-draft-white-dark-4x.png')

if __name__=='__main__': main()
