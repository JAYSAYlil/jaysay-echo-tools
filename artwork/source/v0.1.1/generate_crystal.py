from __future__ import annotations

import json
import math
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "artwork/source/v0.1.1/enhanced_extension_crystal_2-imagegen-raw-v2.png"
OUT = ROOT / "artwork/validation/v0.1.1/crystals/candidate"
PROD = ROOT / "src/main/resources/assets/echopickaxe"
SIZE = 32
ITEM = "enhanced_extension_crystal_2"

def save_png(image, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", optimize=False)

def import_base():
    raw = Image.open(SRC).convert("RGBA")
    alpha = raw.getchannel("A")
    bbox = alpha.point(lambda a: 255 if a >= 128 else 0).getbbox()
    subject = raw.crop(bbox)
    h = 28
    w = max(1, round(subject.width * h / subject.height))
    subject = subject.resize((w, h), Image.Resampling.NEAREST)
    canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    x0, y0 = (SIZE-w)//2, 2
    # Preserve sampled RGB exactly; only canonicalize alpha to hard 0/255.
    pix = subject.load()
    for y in range(h):
        for x in range(w):
            r,g,b,a = pix[x,y]
            canvas.putpixel((x0+x,y0+y),(r,g,b,255 if a >= 128 else 0))
    return canvas, {"raw_size": list(raw.size), "alpha_bbox_ge128": list(bbox),
                    "nearest_size": [w,h], "offset": [x0,y0],
                    "opaque_pixels": sum(1 for p in canvas.getdata() if p[3] == 255)}

def build_glow(base):
    pixels = base.load()
    ring = []
    for y in range(SIZE):
        for x in range(SIZE):
            r,g,b,a = pixels[x,y]
            # Emerald/mint arc only; excludes cyan core and pale guard pixels.
            if a == 255 and g >= 105 and g >= r*1.35 and g >= b*1.12 and r <= 150:
                ring.append((x,y))
    if len(ring) < 12:
        raise RuntimeError(f"Expected a readable emerald orbit, found only {len(ring)} pixels")
    cx = sum(x for x,y in ring)/len(ring); cy = sum(y for x,y in ring)/len(ring)
    ring.sort(key=lambda p: math.atan2(p[1]-cy,p[0]-cx))
    frames=[]
    for i in range(16):
        frame=Image.new("RGBA",(SIZE,SIZE),(0,0,0,0)); fp=frame.load()
        for x,y in ring:
            r,g,b,_=pixels[x,y]
            fp[x,y]=(min(255,round(r*1.035)),min(255,round(g*1.035)),min(255,round(b*1.035)),255)
        # A small two-pixel specular highlight travels around the diagonal ring.
        start=(i*max(1,len(ring)//16))%len(ring)
        for j in range(2):
            x,y=ring[(start+j)%len(ring)]; r,g,b,_=pixels[x,y]
            fp[x,y]=(min(255,round(r*1.14)),min(255,round(g*1.14)),min(255,round(b*1.14)),255)
        frames.append(frame)
    return ring,frames

def face(tex, glow=False):
    f={"uv":tex,"texture":"#glow" if glow else "#layer0","tintindex":-1}
    if glow:
        f["forge_data"]={"block_light":15,"sky_light":15,"ambient_occlusion":False}
    return f

def build_model(base, mask):
    alpha=base.getchannel("A"); p=alpha.load(); elements=[]
    disp_model=json.loads((PROD/"models/item"/(ITEM+".json")).read_text(encoding="utf-8"))
    display=disp_model.get("display",{})
    for y in range(SIZE):
        for x in range(SIZE):
            if p[x,y] != 255: continue
            u,v=x/2+0.25,y/2+0.25; uv=[u,v,u,v]
            isglow=(x,y) in mask
            faces={"north":face(uv,isglow),"south":face(uv,isglow)}
            # Only exposed silhouette sides receive base texture faces.
            if x==0 or p[x-1,y]!=255: faces["west"]=face(uv)
            if x==SIZE-1 or p[x+1,y]!=255: faces["east"]=face(uv)
            if y==0 or p[x,y-1]!=255: faces["up"]=face(uv)
            if y==SIZE-1 or p[x,y+1]!=255: faces["down"]=face(uv)
            elements.append({"from":[x/2,16-(y+1)/2,7.5],"to":[(x+1)/2,16-y/2,8.5],"shade":False,"faces":faces})
    return {"gui_light":"front","ambientocclusion":False,"display":display,
            "textures":{"layer0":f"echopickaxe:item/{ITEM}","glow":f"echopickaxe:item/{ITEM}_glow","particle":"#layer0"},
            "elements":elements}

def main():
    base,import_info=import_base(); ring,frames=build_glow(base)
    d=OUT/"textures/item"; save_png(base,d/(ITEM+".png"))
    strip=Image.new("RGBA",(SIZE,SIZE*len(frames)))
    for i,fr in enumerate(frames): strip.paste(fr,(0,i*SIZE))
    save_png(strip,d/(ITEM+"_glow.png"))
    meta={"animation":{"width":SIZE,"height":SIZE,"frametime":4,"interpolate":True,"frames":list(range(16))}}
    (d/(ITEM+"_glow.png.mcmeta")).write_text(json.dumps(meta,indent=2)+"\n",encoding="utf-8")
    model=build_model(base,set(ring)); m=OUT/"models/item"/(ITEM+".json"); m.parent.mkdir(parents=True,exist_ok=True); m.write_text(json.dumps(model,indent=2)+"\n",encoding="utf-8")
    info={"version":"0.1.1","status":"candidate_only","item":ITEM,"import":import_info,
          "opaque_pixels":import_info["opaque_pixels"],"ring_mask_pixels":len(ring),"frames":16,"frametime_ticks":4,"cycle_ticks":64,"interpolate":True,
          "glow":"Fixed hard-alpha mask on emerald orbit; 2 adjacent same-hue highlights move around ring; selected pixels 1.035x baseline, active glints 1.14x.",
          "model":"One half-pixel box per opaque texel, center UV; north/south glow faces fullbright with AO disabled; silhouette boundary side faces use base; no parent; existing display transforms retained."}
    (ROOT/"artwork/validation/v0.1.1/crystals/candidate-manifest.json").write_text(json.dumps(info,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(info))

if __name__=="__main__": main()
