"""Review-only 0.1.5 cap recolor from the approved native64 resonance pixels."""
import hashlib, io, json, zipfile
from collections import Counter
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[3]
SRC=Path(__file__).resolve().parent
OUT=ROOT/'artwork/validation/v0.1.5/cap-reference-draft'
REF=ROOT/'artwork/source/approved-reference-oct03-64/approved-reference-normalized64.png'
COMMON=ROOT/'artwork/source/approved-reference-oct03-64/common64-unupgraded.png'
MAP=ROOT/'artwork/source/approved-reference-oct03-64/native64-component-map.json'
BASELINE=ROOT/'jaysay-echo-tools-0.1.4.jar'
BASELINE_SHA='9A3D6C0D9B5485C397117CBF00C00C31DA04A339838831231EC5C31B552D67AF'
PREFIX='assets/echopickaxe/'
DARK=(22,28,36)

def sha(data): return hashlib.sha256(data).hexdigest().upper()
def png(data): return Image.open(io.BytesIO(data)).convert('RGBA')
def asset(z,path): return png(z.read(PREFIX+path))
def lum(rgb): return .2126*rgb[0]+.7152*rgb[1]+.0722*rgb[2]
def compose(im,bg):
    layer=Image.new('RGBA',im.size,bg+(255,));layer.alpha_composite(im);return layer.convert('RGB')

def palette_from_head(common,cap):
    colors=Counter(common.getpixel((x,y)) for y in range(3,24) for x in range(13,40)
                   if common.getpixel((x,y))[3] and (x,y) not in cap)
    # Use only actual deep sculk, teal facet, and limited bright-cyan head colors.
    palette=[]
    for rgba,count in colors.items():
        r,g,b,a=rgba
        if a and b>=g*.78 and g>=r*.8 and lum(rgba[:3])<245:
            palette.append((rgba[:3],count))
    return sorted(palette,key=lambda item:(lum(item[0]),item[0]))

def remap_pixel(rgba,palette):
    # Preserve the mother cap's per-texel light/dark structure while substituting
    # colors from the real adjacent head palette. Slightly favor hue-rich teal at
    # equal brightness to avoid gray/ice-blue replacement highlights.
    source=lum(rgba[:3])
    return min(palette,key=lambda item:(abs(lum(item[0])-source),-item[1],item[0]))[0]+(255,)

def panel(states,path,scale,crop=None):
    shown=[]
    for name,im in states:
        view=im.crop(crop) if crop else im
        shown.append((name,view.resize((view.width*scale,view.height*scale),Image.Resampling.NEAREST)))
    margin=10;cw=max(v.width for _,v in shown)+18;ch=max(v.height for _,v in shown)+34
    board=Image.new('RGB',(margin*2+cw*len(shown),margin*2+ch*2),(245,245,245));draw=ImageDraw.Draw(board);font=ImageFont.load_default()
    for row,bg in enumerate(((255,255,255),DARK)):
        fg=(16,20,25) if row==0 else (238,242,247)
        y=margin+row*ch
        for i,(label,im) in enumerate(shown):
            x=margin+i*cw;draw.text((x+3,y),label,fill=fg,font=font)
            board.paste(compose(im,bg),(x+3,y+15))
    board.save(path)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    assert sha(BASELINE.read_bytes())==BASELINE_SHA
    reference=png(REF.read_bytes());common=png(COMMON.read_bytes())
    assert reference.size==common.size==(64,64)
    mapping=json.loads(MAP.read_text(encoding='utf-8'))
    cap={tuple(texel[:2]) for tier in mapping['components']['resonance']['tiers'] for texel in tier['texels']}
    cleanup_im=png((ROOT/'artwork/validation/v0.1.4/artagentmask.png').read_bytes())
    cleanup={(x,y) for y in range(64) for x in range(64) if cleanup_im.getpixel((x,y))[3]}
    palette=palette_from_head(common,cap)
    assert len(cap)==152 and palette
    bare=common.copy();bp=bare.load();rp=reference.load()
    for x,y in cap: bp[x,y]=remap_pixel(rp[x,y],palette)
    with zipfile.ZipFile(BASELINE) as z:
        old_plain=asset(z,'textures/item/echo_pickaxe.png')
        old_v31=asset(z,'textures/item/echo_pickaxe_v031.png')
        red_full=reference.copy()
        v31=old_v31.copy();vp=v31.load()
        # Clean the entire retired 0.1.4 tip footprint so no beige/cyan ghost
        # survives beside the new shared cap; its model shape is untouched.
        for x,y in cap|cleanup: vp[x,y]=bare.getpixel((x,y))
    bare.save(OUT/'bare-native64-source-matched.png')
    v31.save(OUT/'res0-v031-native64-source-matched.png')
    with zipfile.ZipFile(BASELINE) as z:
        v95=asset(z,'textures/item/echo_pickaxe_v095.png')
    hook=Image.open(ROOT/'artwork/validation/v0.1.5/draft/bare-coherent64.png').convert('RGBA')
    states=[('old 0.1.4 bare',old_plain),('rejected 0.1.5 hook',hook),
            ('new same-source teal cap',bare),('approved red cap',red_full)]
    panel(states,OUT/'cap-mother-review-whole-4x.png',4)
    panel(states,OUT/'cap-mother-review-closeup-8x.png',8,(14,3,39,24))
    family=[('new bare',bare),('res0 v031 same cap',v31),('approved resII v095',v95)]
    panel(family,OUT/'same-cap-family-4x-white-dark.png',4)
    panel([('new bare cap',bare)],OUT/'new-cap-closeup-8x-white-dark.png',8,(14,3,39,24))
    source_info={'status':'preview-only-awaiting-user-feedback; previous hand-drawn hook draft rejected','baselineJar':BASELINE.name,
      'baselineJarSha256':BASELINE_SHA,'mother':'approved-reference-normalized64.png','motherSha256':sha(REF.read_bytes()),
      'componentMap':'native64-component-map.json','component':'resonance all tiers, preserving every mother coordinate and alpha','capTexels':len(cap),'legacyTipCleanupTexels':len(cleanup),
      'method':'common64 body plus exact mother resonance-cap coordinates; recolor each cap pixel to nearest-luminance actual neighboring common64 head palette color; no outline/alpha edits','palette':[list(c)+[n] for c,n in palette],
      'v031PreviewCleanup':'replace cap union the historical 0.1.4 203-texel tip cleanup mask from new bare RGBA; retain module pixels outside that union',
      'outputs':['artwork/validation/v0.1.5/cap-reference-draft/bare-native64-source-matched.png','artwork/validation/v0.1.5/cap-reference-draft/res0-v031-native64-source-matched.png'],
      'previews':['artwork/validation/v0.1.5/cap-reference-draft/cap-mother-review-whole-4x.png','artwork/validation/v0.1.5/cap-reference-draft/cap-mother-review-closeup-8x.png','artwork/validation/v0.1.5/cap-reference-draft/same-cap-family-4x-white-dark.png','artwork/validation/v0.1.5/cap-reference-draft/new-cap-closeup-8x-white-dark.png']}
    (SRC/'recolor-method.json').write_text(json.dumps(source_info,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'PASS review-only cap={len(cap)} palette={len(palette)}; bare/v031 and whole/closeup previews: {OUT}')

if __name__=='__main__':main()
