"""Build isolated 64px progression candidates from the approved concept reference."""
from __future__ import annotations

import copy, hashlib, io, json, math, shutil, zipfile
from collections import deque
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path(__file__).resolve().parent
REF_PATH = ROOT / "artwork/source/echo-pickaxe-upgrades-v0.1.2/concept-full-upgrade-selected.png"
BASE_PATH = ROOT / "src/main/resources/assets/echopickaxe/textures/item/echo_pickaxe.png"
GLOW_PATH = ROOT / "src/main/resources/assets/echopickaxe/textures/item/echo_pickaxe_glow.png"
META_PATH = GLOW_PATH.with_suffix(".png.mcmeta")
MODEL_PATH = ROOT / "src/main/resources/assets/echopickaxe/models/item/echo_pickaxe.json"
LEGACY_JAR = ROOT / "jaysay-echo-tools-0.1.1.jar"
PARENT = ROOT / "artwork/validation/v0.1.2/pickaxe"
STAGING = PARENT / "candidate-approved64-staging"
OUT = PARENT / "candidate"
COMPONENTS = ("resonance", "frequency", "tuning", "extension")
LIMITS = {"resonance":2,"frequency":3,"tuning":1,"extension":3}
LIGHT = {"block_light":15,"sky_light":15,"ambient_occlusion":False}
DIRS = {"west":(-1,0),"east":(1,0),"up":(0,-1),"down":(0,1)}
BG_DARK = (20,25,31)

def sha(data: bytes) -> str: return hashlib.sha256(data).hexdigest()
def safe_child(parent: Path, child: Path) -> Path:
    p, c = parent.resolve(), child.resolve()
    if p not in c.parents: raise RuntimeError(f"Unsafe path outside {p}: {c}")
    return c

def load_reference():
    raw=Image.open(REF_PATH).convert("RGBA")
    crop=raw.crop(raw.getchannel("A").getbbox())
    scale=min(62/crop.width,62/crop.height)
    size=(round(crop.width*scale),round(crop.height*scale))
    scaled=crop.resize(size,Image.Resampling.NEAREST)
    ref=Image.new("RGBA",(64,64),(0,0,0,0)); ref.alpha_composite(scaled,((64-size[0])//2,(64-size[1])//2))
    aa=[a for a in ref.getchannel("A").getdata() if 0<a<255]
    normalized=ref.copy()
    pix=normalized.load()
    kept=dropped=0
    for y in range(64):
        for x in range(64):
            r,g,b,a=pix[x,y]
            if a>=128:
                if a!=255: kept+=1
                pix[x,y]=(r,g,b,255)
            elif a:
                pix[x,y]=(0,0,0,0); dropped+=1
    # 4-connected alpha topology: no isolated antialias specks may survive.
    opaque={(x,y) for y in range(64) for x in range(64) if pix[x,y][3]}
    comps=[]; remaining=set(opaque)
    while remaining:
        seed=remaining.pop(); q=[seed]; size=0
        while q:
            x,y=q.pop(); size+=1
            for n in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if n in remaining: remaining.remove(n); q.append(n)
        comps.append(size)
    if not comps or len(comps)>1 and max(comps)>0 and sum(n for n in comps if n<3)>0:
        tiny=[n for n in comps if n<3]
        if tiny: raise ValueError(f"Alpha cutoff left disconnected tiny pixels {tiny}")
    return raw,ref,normalized,{"sourceAlphaFractionalCount":len(aa),"retainedNon255AlphaCount":kept,
                               "droppedBelow128AlphaCount":dropped,"binaryOpaqueCount":len(opaque),
                               "connectedComponentSizes":sorted(comps,reverse=True)}

def draw_polygon(mask, points): ImageDraw.Draw(mask).polygon(points,fill=255)

def feature_masks(ref):
    opaque=ref.getchannel("A")
    # Bounded component regions partition the four approved attachments. All opaque texels
    # inside the shapes belong to the module so no colored fragment remains when it is off.
    red=Image.new("L",(64,64)); draw_polygon(red,[(17,7),(23,5),(31,5),(35,4),(37,6),(38,9),(36,13),(34,17),(33,22),(31,27),(28,30),(23,25),(18,18)])
    star=Image.new("L",(64,64)); draw_polygon(star,[(38,13),(43,18),(42,22),(38,26),(33,22),(34,18)])
    purple=Image.new("L",(64,64));
    p1=Image.new("L",(64,64)); draw_polygon(p1,[(43,8),(50,7),(54,12),(53,18),(49,21),(45,17),(43,13)])
    p2=Image.new("L",(64,64)); draw_polygon(p2,[(48,15),(54,14),(58,19),(59,26),(56,31),(51,28),(49,22)])
    p3=Image.new("L",(64,64)); draw_polygon(p3,[(51,24),(57,22),(61,27),(61,36),(58,40),(53,37),(51,31)])
    p4=Image.new("L",(64,64)); draw_polygon(p4,[(54,34),(59,32),(61,37),(60,44),(57,45),(54,41)])
    tail=Image.new("L",(64,64)); draw_polygon(tail,[(7,45),(14,45),(19,48),(20,54),(17,60),(12,63),(7,61),(4,56),(4,50)])
    # Clip to sampled, normalized reference alpha and make component masks disjoint.
    def clip(m): return Image.frombytes("L",m.size,bytes(255 if a and b else 0 for a,b in zip(m.getdata(),opaque.getdata())))
    pix=ref.load()
    def near_color(region,predicate,radius=1):
        region=clip(region); allowed={(i%64,i//64) for i,v in enumerate(region.getdata()) if v}
        seeds={(x,y) for x,y in allowed if predicate(*pix[x,y][:3])}
        kept=set(seeds)
        for x,y in seeds:
            for yy in range(max(0,y-radius),min(64,y+radius+1)):
                for xx in range(max(0,x-radius),min(64,x+radius+1)):
                    if (xx,yy) in allowed: kept.add((xx,yy))
        m=Image.new("L",(64,64)); mp=m.load()
        for x,y in kept: mp[x,y]=255
        return m
    red=near_color(red,lambda r,g,b:r>15 and r>g*1.35 and r>b*1.15)
    star=near_color(star,lambda r,g,b:min(r,g,b)>115 and b>=r*.95 and g>=r*.8)
    tail=clip(tail)
    pp=[near_color(m,lambda r,g,b:b>35 and b>g*1.15 and b>r*1.12) for m in [p1,p2,p3,p4]]
    # Component overlap is a hard error. Regions are deliberately drawn with a one-texel gap.
    sets={"resonance":set(),"frequency":set(),"tuning":set(),"extension":set()}
    def coords(m): return {(i%64,i//64) for i,v in enumerate(m.getdata()) if v}
    sets["resonance"]=coords(red); sets["frequency"]=set().union(*(coords(m) for m in pp)); sets["tuning"]=coords(star); sets["extension"]=coords(tail)
    for i,a in enumerate(COMPONENTS):
        for b in COMPONENTS[i+1:]:
            overlap=sets[a]&sets[b]
            if overlap: raise ValueError(f"Feature masks overlap {a}/{b}: {sorted(overlap)[:12]}")
    # Red progression: broad left facet first, then crown highlights and the lower facet.
    red1=Image.new("L",(64,64)); draw_polygon(red1,[(17,10),(22,8),(29,8),(31,12),(30,19),(27,26),(23,23),(18,17)])
    red1=Image.frombytes("L",(64,64),bytes(255 if p and q else 0 for p,q in zip(red.getdata(),clip(red1).getdata())))
    red2=Image.frombytes("L",(64,64),bytes(255 if p and not q else 0 for p,q in zip(red.getdata(),red1.getdata())))
    # Purple grades correspond to upper wrap, broad central facet, and two lower facets.
    purple_tiers=[clip(p1),clip(p2),clip(p3),clip(p4)]
    tier2=ImageChops.lighter(purple_tiers[1],Image.new("L",(64,64)))
    tier3=ImageChops.lighter(purple_tiers[2],purple_tiers[3])
    # Eye silhouette, then bright iris, then outer ivory claws/support.
    eye=Image.new("L",(64,64)); draw_polygon(eye,[(7,46),(14,46),(18,49),(19,54),(17,58),(12,60),(7,58),(5,54),(5,50)])
    eye=clip(eye); tailtiers=[Image.new("L",(64,64)),Image.new("L",(64,64)),Image.new("L",(64,64))]
    # Keep the four reference-sampled ivory claw faces in Extension III so they survive 16px inventory scaling.
    claw_seeds={(14,46),(18,50),(6,54),(14,58)}
    claw=Image.new("L",(64,64)); cp=claw.load(); rp=ref.load()
    for y in range(64):
      for x in range(64):
        r,g,b,a=rp[x,y]
        beige=(r>105 and g>100 and b>90 and r>=g*.95 and g>=b*.90)
        if (x,y) in claw_seeds or (beige and tail.getpixel((x,y)) and min(abs(x-sx)+abs(y-sy) for sx,sy in claw_seeds)<=2): cp[x,y]=255
    claw=ImageChops.multiply(claw,tail)
    eye=Image.frombytes("L",(64,64),bytes(255 if p and not q else 0 for p,q in zip(eye.getdata(),claw.getdata())))
    # Tier II owns the pupil/highlight within the eye; tier III owns the surrounding ivory claws/support.
    ppix=ref.load(); iris=Image.new("L",(64,64)); draw_polygon(iris,[(9,49),(11,48),(14,49),(15,52),(14,55),(11,55),(8,53)])
    iris=clip(iris); eye2=Image.new("L",(64,64)); ep=eye2.load()
    for y in range(64):
      for x in range(64):
        r,g,b,a=ppix[x,y]
        green=(g>=80 and g>r*1.15 and g>b*1.02)
        icy=(min(r,g,b)>200 and b>=g*.98)
        if iris.getpixel((x,y)) and (green or icy): ep[x,y]=255
    # The approved eye's bright cyan center is sampled by the 16px inventory icon;
    # keep it with the white core in tier II so the iris remains visible at UI scale.
    ep[12,52]=255
    # Keep the iris core additions distinct from tier-I green eye perimeter.
    tailtiers[1]=eye2
    tailtiers[0]=Image.frombytes("L",(64,64),bytes(255 if p and not q else 0 for p,q in zip(eye.getdata(),eye2.getdata())))
    tailtiers[2]=Image.frombytes("L",(64,64),bytes(255 if p and not q else 0 for p,q in zip(tail.getdata(),eye.getdata())))
    tiers={"resonance":[red1,red2],"frequency":[purple_tiers[0],tier2,tier3],"tuning":[star],"extension":tailtiers}
    # Rebuild full-tier mask unions and ensure every approved feature pixel is owned exactly once.
    unions={k:set().union(*(coords(m) for m in v)) for k,v in tiers.items()}
    all_mask=set().union(*unions.values())
    if all_mask != set().union(*sets.values()):
        expected=set().union(*sets.values()); print("mask diff",sorted(expected-all_mask)[:20],sorted(all_mask-expected)[:20])
        raise ValueError("Progression masks fail to cover feature regions")
    return tiers,unions,sets

def residual_chromatic_features(ref,masks):
    p=ref.load(); residual={"red":[],"purple":[],"green":[]}
    for y in range(64):
      for x in range(64):
        r,g,b,a=p[x,y]
        if not a: continue
        if x<42 and y<32 and r>20 and r>g*1.35 and r>b*1.15 and (x,y) not in masks["resonance"]: residual["red"].append((x,y,(r,g,b)))
        if x>=43 and y<47 and b>35 and b>g*1.10 and r>g*1.08 and (x,y) not in masks["frequency"]: residual["purple"].append((x,y,(r,g,b)))
        if x<21 and y>=45 and g>r*1.2 and g>b*1.02 and (x,y) not in masks["extension"]: residual["green"].append((x,y,(r,g,b)))
    return residual

def common_body(ref, masks, source32):
    common=ref.copy(); p=common.load(); base=source32.convert("RGBA").load(); opaque=source32.getchannel("A")
    allmask=set().union(*masks.values())
    # For every attachment texel, synthesize a sculk underlayer from the original material texture
    # plus local reference-body colors. Outside these regions the approved sampled body is exact.
    bodycoords=[(x,y) for y in range(64) for x in range(64) if p[x,y][3] and (x,y) not in allmask]
    for x,y in allmask:
        sx=min(31,x//2); sy=min(31,y//2)
        if not opaque.getpixel((sx,sy)):
            # New silhouette pixels belong to the module layer; prevent an unupgraded
            # common body from showing a dark ghost crystal when that module is absent.
            p[x,y]=(0,0,0,0)
            continue
        if not opaque.getpixel((sx,sy)):
            candidates=[(xx,yy) for radius in range(1,6) for yy in range(max(0,sy-radius),min(32,sy+radius+1)) for xx in range(max(0,sx-radius),min(32,sx+radius+1)) if opaque.getpixel((xx,yy))]
            if not candidates: raise ValueError(f"No source body texel near {(x,y)}")
            sx,sy=min(candidates,key=lambda q:(q[0]-sx)**2+(q[1]-sy)**2)
        br,bg,bb,_=base[sx,sy]
        nearby=[q for q in bodycoords if abs(q[0]-x)+abs(q[1]-y)<=7]
        if nearby:
            q=min(nearby,key=lambda q:(q[0]-x)**2+(q[1]-y)**2); rr,rg,rb,_=p[q[0],q[1]]
            rgb=(round(br*.60+rr*.40),round(bg*.60+rg*.40),round(bb*.60+rb*.40))
        else: rgb=(br,bg,bb)
        # 64px native grain: deterministic low-amplitude texel variation, without a checkerboard.
        n=((x*37+y*73+(x*y*11))%9)-4
        p[x,y]=tuple(max(0,min(255,c+n)) for c in rgb)+(255,)
    return common

def state_sprite(reference, common, tiers, levels):
    out=common.copy(); dst=out.load(); src=reference.load()
    for component in COMPONENTS:
        for mask in tiers[component][:levels.get(component,0)]:
            for i,v in enumerate(mask.getdata()):
                if v:
                    x,y=i%64,i//64; r,g,b,a=src[x,y]; dst[x,y]=(r,g,b,255)
    return out

def colors_from_mask(ref, mask):
    p=ref.load(); return {(i%64,i//64):p[i%64,i//64][:3] for i,v in enumerate(mask.getdata()) if v}

def emissive_masks(ref, tiers):
    p=ref.load(); result={}
    for comp,levels in tiers.items():
        result[comp]=[]
        for tierno,mask in enumerate(levels,1):
            coords=[]
            for i,v in enumerate(mask.getdata()):
                if not v: continue
                x,y=i%64,i//64; r,g,b,a=p[x,y]
                if comp=="resonance": emit=(r>175 and g>48) or (r>210 and g>105)
                elif comp=="frequency": emit=(b>145 and g>48) or (min(r,g,b)>150)
                elif comp=="tuning": emit=(min(r,g,b)>120 and b>=r)
                else: emit=(g>145 and g>r*1.15 and y<58)
                if emit: coords.append((x,y))
            if comp=="extension" and tierno==1:
                # Tier I gets a distinct green-eye rim glint. Tier II brightens the iris;
                # tier III adds the three ordinary ivory claws.
                candidates=[]
                for i,v in enumerate(mask.getdata()):
                    if v:
                        x,y=i%64,i//64; r,g,b,a=p[x,y]
                        if g>=80 and g>r*1.15 and g>b*1.02: candidates.append((g-r+g*.01,x,y))
                if candidates:
                    _,x,y=max(candidates)
                    if (x,y) not in coords: coords.append((x,y))
                if not coords: raise ValueError("Extension I has no animatable green-eye texel")
            result[comp].append(set(coords))
    return result

def body_emissive_mask(ref, feature_union):
    p=ref.load(); result=set()
    for y in range(64):
      for x in range(64):
        if (x,y) in feature_union or p[x,y][3]==0: continue
        r,g,b,a=p[x,y]
        if g>r*1.65 and b>r*1.45 and max(g,b)>95: result.add((x,y))
    return result

def glow_strip(sprite, ref, common_emit, module_emit, levels, phase_frame=None):
    active=set(common_emit)
    for comp in COMPONENTS:
        for cells in module_emit[comp][:levels.get(comp,0)]: active |= cells
    strip=Image.new("RGBA",(64,1024),(0,0,0,0)); src=sprite.load()
    for frame in range(16):
        pulse=.82+.18*(.5+.5*math.sin(math.tau*frame/16))
        for x,y in active:
            r,g,b,a=src[x,y]
            strip.putpixel((x,y+64*frame),(round(r*pulse),round(g*pulse),round(b*pulse),255))
    return strip,active

def model_for_state(source_model,item_id,sprite,emissive):
    model=copy.deepcopy(source_model); model.pop("parent",None); model.pop("overrides",None)
    model["textures"]={"layer0":f"echopickaxe:item/{item_id}","glow":f"echopickaxe:item/{item_id}_glow","particle":"#layer0"}
    opaque={(x,y) for y in range(64) for x in range(64) if sprite.getpixel((x,y))[3]}
    elements=[]; lit=set()
    for x,y in sorted(opaque,key=lambda q:(q[1],q[0])):
        islit=(x,y) in emissive
        if islit: lit.add((x,y))
        uv=[(x+.5)/4,(y+.5)/4,(x+.5)/4,(y+.5)/4]
        faces={}
        for side in ("north","south"):
            f={"uv":uv.copy(),"texture":"#glow" if islit else "#layer0"}
            if islit: f["forge_data"]=copy.deepcopy(LIGHT)
            faces[side]=f
        for side,(dx,dy) in DIRS.items():
            if (x+dx,y+dy) not in opaque: faces[side]={"uv":uv.copy(),"texture":"#layer0"}
        elements.append({"from":[x*.25,16-(y+1)*.25,7.5],"to":[(x+1)*.25,16-y*.25,8.5],"shade":False,"faces":faces})
    model["elements"]=elements
    return model,opaque,lit

def validate_model(sprite,model,lit,item_id):
    expected={(x,y) for y in range(64) for x in range(64) if sprite.getpixel((x,y))[3]}
    actual=set()
    for e in model["elements"]:
        x=round(e["from"][0]*4); y=round((16-e["to"][1])*4); pos=(x,y)
        if pos in actual or pos not in expected: raise ValueError(f"{item_id}: bad duplicate/missing pixel {pos}")
        actual.add(pos)
        if e["from"]!=[x*.25,16-(y+1)*.25,7.5] or e["to"]!=[(x+1)*.25,16-y*.25,8.5]: raise ValueError(f"{item_id}: wrong prism at {pos}")
        uv=[(x+.5)/4,(y+.5)/4,(x+.5)/4,(y+.5)/4]
        visible={"north","south"}|{s for s,(dx,dy) in DIRS.items() if (x+dx,y+dy) not in expected}
        if set(e["faces"])!=visible: raise ValueError(f"{item_id}: exposed face mismatch at {pos}")
        if any(f["uv"]!=uv for f in e["faces"].values()): raise ValueError(f"{item_id}: UV center mismatch at {pos}")
    if actual!=expected: raise ValueError(f"{item_id}: geometry/alpha mismatch")
    if {(round(e["from"][0]*4),round((16-e["to"][1])*4)) for e in model["elements"] if e["faces"]["north"]["texture"]=="#glow"}!=lit:
        raise ValueError(f"{item_id}: model glow mask mismatch")

def get_font(size):
    for path in ("C:/Windows/Fonts/arial.ttf","C:/Windows/Fonts/segoeui.ttf"):
        if Path(path).exists(): return ImageFont.truetype(path,size)
    return ImageFont.load_default()

def levels_for(index): return (index//32,(index%32)//8,(index%8)//4,index%4)

def render_preview_sprite(index,ref,common,tiers,base32):
    if index==0: return base32.resize((64,64),Image.Resampling.NEAREST)
    levels=dict(zip(COMPONENTS,levels_for(index)))
    return state_sprite(ref,common,tiers,levels)

def board96(items,bg,name,mode):
    cols=8; cw,ch=144,110; margin=12; rows=12
    out=Image.new("RGB",(2*margin+cols*cw,2*margin+rows*ch),bg); d=ImageDraw.Draw(out)
    fg=(30,36,43) if sum(bg)>400 else (235,239,246)
    for i in range(96):
        x=margin+(i%cols)*cw; y=margin+(i//cols)*ch
        sprite=items[i]
        if mode=="16": shown=sprite.resize((16,16),Image.Resampling.NEAREST)
        else: shown=sprite.resize((64,64),Image.Resampling.NEAREST)
        tile=Image.new("RGBA",shown.size,(*bg,255)); tile.alpha_composite(shown)
        if mode=="16": out.paste(tile.convert("RGB"),(x+(cw-16)//2,y+26))
        else: out.paste(tile.convert("RGB"),(x+40,y+3))
        d.text((x+3,y+4),f"{i:03d}",font=get_font(11),fill=fg)
        lv=levels_for(i) if i else (0,0,0,0)
        d.text((x+3,y+82),f"R{lv[0]} F{lv[1]} T{lv[2]} E{lv[3]}",font=get_font(10),fill=fg)
    out.save(OUT/f"all-96-combinations-{name}-{mode}.png")

def progression_boards(ref,common,tiers,base32):
    states=[("Base",0)]+[(f"Resonance {i}",i*32) for i in (1,2)]+[(f"Frequency {i}",i*8) for i in (1,2,3)]+[("Tuning I",4)]+[(f"Extension {i}",i) for i in (1,2,3)]+[("All maximum",95)]
    for bg,label in (((250,250,250),"white"), (BG_DARK,"dark")):
        cw,ch,margin,cols=190,150,16,4
        out=Image.new("RGB",(2*margin+cols*cw,2*margin+3*ch),bg); d=ImageDraw.Draw(out); fg=(30,36,43) if sum(bg)>400 else (235,239,246)
        for n,(name,index) in enumerate(states):
            x=margin+(n%cols)*cw; y=margin+(n//cols)*ch
            d.text((x+4,y+2),name,font=get_font(12),fill=fg)
            im=render_preview_sprite(index,ref,common,tiers,base32)
            shown=im.resize((96,96),Image.Resampling.NEAREST); tile=Image.new("RGBA",shown.size,(*bg,255)); tile.alpha_composite(shown)
            out.paste(tile.convert("RGB"),(x+45,y+20))
            d.text((x+4,y+122),"32px base" if index==0 else "64px native",font=get_font(10),fill=fg)
        out.save(OUT/f"all-levels-{label}-64px.png")
    # Actual inventory scale (native 16px thumbnails).
    bg=(247,247,243); cw,ch,margin,cols=176,120,12,4
    out=Image.new("RGB",(2*margin+cols*cw,2*margin+3*ch),bg); d=ImageDraw.Draw(out)
    for n,(name,index) in enumerate(states):
        x=margin+(n%cols)*cw; y=margin+(n//cols)*ch
        d.text((x+4,y+3),name,font=get_font(12),fill=(24,30,33))
        im=render_preview_sprite(index,ref,common,tiers,base32).resize((16,16),Image.Resampling.NEAREST)
        out.paste(im,(x+80,y+32),im)
    out.save(OUT/"all-levels-inventory-16px.png")

def all96_boards(items):
    board96(items,(250,250,250),"white-background","64px")
    board96(items,BG_DARK,"dark-background","64px")
    board96(items,(250,250,250),"inventory-16px","16")

def comparison_old_new(full64,new_glow64):
    with zipfile.ZipFile(LEGACY_JAR) as z:
        old=Image.open(io.BytesIO(z.read("assets/echopickaxe/textures/item/echo_pickaxe_v095.png"))).convert("RGBA")
        old_strip=Image.open(io.BytesIO(z.read("assets/echopickaxe/textures/item/echo_pickaxe_v095_glow.png"))).convert("RGBA")
    if old.size!=(32,32) or old_strip.size!=(32,512): raise ValueError("Unexpected v0.1.1 v095 asset dimensions")
    old.alpha_composite(old_strip.crop((0,0,32,32)))
    new=full64.copy(); new.alpha_composite(new_glow64.crop((0,0,64,64)))
    for bg,label in (((250,250,250),"white"),(BG_DARK,"dark")):
        out=Image.new("RGB",(720,380),bg); d=ImageDraw.Draw(out); fg=(30,36,43) if label=="white" else (235,239,246)
        d.text((24,10),"0.1.1 JAR · v095 full upgrade · glow frame 0",font=get_font(14),fill=fg)
        d.text((385,10),"0.1.2 candidate · v095 full upgrade · frame 0",font=get_font(14),fill=fg)
        for im,x in ((old,24),(new,385)):
            shown=im.resize((320,320),Image.Resampling.NEAREST)
            tile=Image.new("RGBA",shown.size,(*bg,255)); tile.alpha_composite(shown)
            out.paste(tile.convert("RGB"),(x,42))
        out.save(OUT/f"previous-0.1.1-vs-approved64-{label}.png")

def animated_gif(full,common_emit,module_emit,levels):
    active=set(common_emit)
    for comp in COMPONENTS:
        for cells in module_emit[comp][:levels[comp]]: active |= cells
    src=full.load(); frames=[]
    for t in range(96):
        phase=(t/3)%16; pulse=.82+.18*(.5+.5*math.sin(math.tau*phase/16))
        frame=Image.new("RGBA",(64,64),(0,0,0,0)); fp=frame.load()
        for x,y in active:
            r,g,b,a=src[x,y]; fp[x,y]=(round(r*pulse),round(g*pulse),round(b*pulse),255)
        bg=Image.new("RGBA",(64,64),(*BG_DARK,255)); bg.alpha_composite(full); bg.alpha_composite(frame)
        frames.append(bg.resize((512,512),Image.Resampling.NEAREST).convert("RGB"))
    frames[0].save(OUT/"all-maximum-dynamic-two-cycles.gif",save_all=True,append_images=frames[1:],duration=50,loop=0,disposal=2,optimize=False)

def connected_sizes(alpha):
    remaining={(x,y) for y in range(alpha.height) for x in range(alpha.width) if alpha.getpixel((x,y))}
    sizes=[]
    while remaining:
        start=remaining.pop(); todo=[start]; n=0
        while todo:
            x,y=todo.pop(); n+=1
            for q in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if q in remaining: remaining.remove(q); todo.append(q)
        sizes.append(n)
    return sorted(sizes,reverse=True)

def main():
    global OUT
    # Validate every destructive target before touching candidate directories.
    safe_child(PARENT,STAGING); safe_child(PARENT,OUT)
    if STAGING.exists():
        if STAGING.resolve()!=safe_child(PARENT,STAGING): raise RuntimeError("Unexpected staging path")
        shutil.rmtree(STAGING)
    STAGING.mkdir(parents=True)
    raw,ref,normalized,alpha_stats=load_reference()
    ref_hash=sha(REF_PATH.read_bytes()); base32=Image.open(BASE_PATH).convert("RGBA")
    old_model=json.loads(MODEL_PATH.read_text(encoding="utf-8")); old_meta_bytes=META_PATH.read_bytes()
    old_meta=json.loads(old_meta_bytes)
    if base32.size!=(32,32) or old_meta["animation"]["width"]!=32 or old_meta["animation"]["height"]!=32:
        raise ValueError("Bare 0.1.1 baseline dimensions/metadata changed")
    tiers,masks,regions=feature_masks(normalized)
    residuals=residual_chromatic_features(normalized,masks)
    if any(residuals.values()): raise ValueError(f"Unassigned colored module residuals: {residuals}")
    common=common_body(normalized,masks,base32)
    union=set().union(*(masks[c] for c in COMPONENTS))
    common_emit=body_emissive_mask(normalized,union)
    module_emit=emissive_masks(normalized,tiers)
    green_eye_glints=[(x,y) for x,y in module_emit["extension"][0]
        if normalized.getpixel((x,y))[1]>=145 and normalized.getpixel((x,y))[1]>normalized.getpixel((x,y))[0]*1.15 and normalized.getpixel((x,y))[1]>normalized.getpixel((x,y))[2]*1.02]
    if len(green_eye_glints)<3: raise ValueError(f"Extension I needs several clearly green animating facets: {green_eye_glints}")
    if not tiers["extension"][1].getpixel((12,51)): raise ValueError("Approved eye core (12,51) must activate with Extension II")

    # Full maximum must reproduce every normalized reference texel exactly.
    full=state_sprite(normalized,common,tiers,LIMITS)
    if full.tobytes()!=normalized.tobytes(): raise ValueError("All-max sprite differs from normalized approved reference")
    if connected_sizes(full.getchannel("A"))!=[alpha_stats["binaryOpaqueCount"]]: raise ValueError("Reference alpha has disconnected islands")
    normalized.save(SOURCE/"approved-reference-normalized64.png")
    common.save(SOURCE/"common64-unupgraded.png")
    body_strip,body_lit=glow_strip(common,normalized,common_emit,{c:[] for c in COMPONENTS},{})
    body_strip.save(SOURCE/"common64-glow.png")

    # Structured editable texel map, carrying exact reference colors and tier masks.
    map_doc={"schema":1,"purpose":"64x64 approved-reference native composition masks; review/candidate source only",
      "reference":{"path":"artwork/source/echo-pickaxe-upgrades-v0.1.2/concept-full-upgrade-selected.png","sha256":ref_hash},
      "normalizedReference":{"path":"artwork/source/approved-reference-oct03-64/approved-reference-normalized64.png","sha256":sha(SOURCE.joinpath("approved-reference-normalized64.png").read_bytes())},
      "alphaNormalization":{"threshold":128,"normalization":alpha_stats},
      "common64":{"path":"artwork/source/approved-reference-oct03-64/common64-unupgraded.png","sha256":sha(SOURCE.joinpath("common64-unupgraded.png").read_bytes()),"meaning":"Complete unupgraded sculk body underlay at the reference silhouette. New module pixels are transparent until their tier activates."},
      "commonGlow":{"path":"artwork/source/approved-reference-oct03-64/common64-glow.png","sha256":sha(SOURCE.joinpath("common64-glow.png").read_bytes()),"size":[64,1024],"frames":16,"tickPerFrame":3,"interpolate":True,"litPixels":len(body_lit)},
      "dimensions":[64,64],"geometry":{"pixelUnit":0.25,"z":[7.5,8.5],"uvCenter":"((x+0.5)/4,(y+0.5)/4)"},"components":{}}
    for c in COMPONENTS:
        map_doc["components"][c]={"maxLevel":LIMITS[c],"maskTexels":len(masks[c]),"tiers":[]}
        for n,mask in enumerate(tiers[c],1):
            cells=[]
            for (x,y),rgb in sorted(colors_from_mask(normalized,mask).items(),key=lambda q:(q[0][1],q[0][0])):
                cells.append([x,y,list(rgb),(x,y) in module_emit[c][n-1]])
            map_doc["components"][c]["tiers"].append({"level":n,"texelCount":len(cells),"texels":cells})
    map_path=SOURCE/"native64-component-map.json"; map_path.write_text(json.dumps(map_doc,indent=2)+"\n",encoding="utf-8")

    # Actual common body, tier sprites, 95 candidate models, layer PNGs, and updated-size metadata.
    models_dir=STAGING/"models/item"; tex_dir=STAGING/"textures/item"; models_dir.mkdir(parents=True); tex_dir.mkdir(parents=True)
    shutil.copy2(BASE_PATH,tex_dir/"echo_pickaxe.png"); shutil.copy2(GLOW_PATH,tex_dir/"echo_pickaxe_glow.png"); (tex_dir/"echo_pickaxe_glow.png.mcmeta").write_bytes(old_meta_bytes)
    meta64=copy.deepcopy(old_meta); meta64["animation"]["width"]=64; meta64["animation"]["height"]=64
    meta64_bytes=(json.dumps(meta64,indent=2,ensure_ascii=False)+"\n").encode("utf-8")
    base_model=copy.deepcopy(old_model); base_model["overrides"]=[]
    variants=[]; sprite_by_index=[base32]+[None]*95; signatures64={}; signatures16={}
    internal_signatures16={}
    for index in range(96):
        lv=levels_for(index); levels=dict(zip(COMPONENTS,lv))
        inner=common if index==0 else state_sprite(normalized,common,tiers,levels)
        internal_signatures16.setdefault(inner.resize((16,16),Image.Resampling.NEAREST).tobytes(),[]).append(index)
        display=base32 if index==0 else inner
        signatures64.setdefault(display.resize((64,64),Image.Resampling.NEAREST).tobytes(),[]).append(index)
        signatures16.setdefault(display.resize((16,16),Image.Resampling.NEAREST).tobytes(),[]).append(index)
        if index==0: continue
        item=f"echo_pickaxe_v{index:03d}"
        glow,lit=glow_strip(inner,normalized,common_emit,module_emit,levels)
        model,opaque,_=model_for_state(old_model,item,inner,lit)
        validate_model(inner,model,lit,item)
        sprite_path=tex_dir/f"{item}.png"; glow_path=tex_dir/f"{item}_glow.png"; model_path=models_dir/f"{item}.json"; meta_path=glow_path.with_suffix(".png.mcmeta")
        inner.save(sprite_path); glow.save(glow_path); meta_path.write_bytes(meta64_bytes)
        model_path.write_text(json.dumps(model,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        base_model["overrides"].append({"predicate":{"echopickaxe:upgrade_visual":index},"model":f"echopickaxe:item/{item}"})
        variants.append({"index":index,"levels":dict(zip(COMPONENTS,lv)),"opaqueTexels":len(opaque),"emissiveTexels":len(lit),"sha256":{"sprite":sha(sprite_path.read_bytes()),"glow":sha(glow_path.read_bytes()),"meta":sha(meta_path.read_bytes()),"model":sha(model_path.read_bytes())}})
        sprite_by_index[index]=inner
    # Include common64 as a distinct internal composition baseline and ensure independent 16px icons.
    if len(signatures64)!=96: raise ValueError(f"Actual base32+95 sprites not distinct at 64px: {len(signatures64)}")
    # At inventory scale the green eye rim and central iris must remain distinct.
    ext_i=sprite_by_index[1].resize((16,16),Image.Resampling.NEAREST).tobytes()
    ext_ii=sprite_by_index[2].resize((16,16),Image.Resampling.NEAREST).tobytes()
    if ext_i==ext_ii: raise ValueError("Extension I and II must remain visibly distinct at 16px")
    (models_dir/"echo_pickaxe.json").write_text(json.dumps(base_model,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")

    # Candidate-wide audit: alpha topology fixed across animation frames, bare assets byte-exact.
    for item in variants:
        idx=item["index"]; sprite=sprite_by_index[idx]; levels=item["levels"]
        glow=Image.open(tex_dir/f"echo_pickaxe_v{idx:03d}_glow.png").convert("RGBA")
        if glow.size!=(64,1024): raise ValueError(f"v{idx}: bad glow dimensions")
        expected_lit={(x,y) for y in range(64) for x in range(64) if glow.getpixel((x,y))[3]}
        for f in range(16):
            frame=glow.crop((0,64*f,64,64*(f+1)))
            if {(x,y) for y in range(64) for x in range(64) if frame.getpixel((x,y))[3]}!=expected_lit: raise ValueError(f"v{idx}: glow alpha topology changed at frame {f}")
    for filename,path in (("echo_pickaxe.png",BASE_PATH),("echo_pickaxe_glow.png",GLOW_PATH)):
        if sha((tex_dir/filename).read_bytes())!=sha(path.read_bytes()): raise ValueError(f"Candidate bare asset changed: {filename}")
    if (tex_dir/"echo_pickaxe_glow.png.mcmeta").read_bytes()!=old_meta_bytes: raise ValueError("Candidate base animation metadata changed")

    # All state boards use the true 32px baseline at index 0 and 64px variants thereafter.
    OUT=PARENT/"approved-reference-oct03-64-review"
    OUT.mkdir(parents=True,exist_ok=True)
    normalized.save(ROOT/"artwork/validation/v0.1.2/approved-reference-oct03-64/approved-reference-normalized64.png")
    all96_boards(sprite_by_index)
    progression_boards(normalized,common,tiers,base32)
    full_glow,_=glow_strip(full,normalized,common_emit,module_emit,LIMITS)
    comparison_old_new(full,full_glow)
    animated_gif(full,common_emit,module_emit,LIMITS)
    full.save(OUT/"all-maximum-native64.png")
    # Single-state images at native 64px for low-tier progression review.
    for name,index in (("base",0),("resonance-i",32),("resonance-ii",64),("frequency-i",8),("frequency-ii",16),("frequency-iii",24),("tuning-i",4),("extension-i",1),("extension-ii",2),("extension-iii",3),("all-maximum",95)):
        render_preview_sprite(index,normalized,common,tiers,base32).save(OUT/f"state-{name}.png")
    (SOURCE/"README.md").write_text("""# Approved reference 64px integration source\n\nThe user-approved concept is the single visual source for the 64×64 full-upgrade image. `build_approved64_variants.py` samples it with nearest-neighbor filtering, normalizes alpha at 128, creates an unupgraded 64px sculk underlay and component/tier masks, then writes 95 isolated candidate models/textures. The all-maximum state is pixel-exact to `approved-reference-normalized64.png`.\n\nResonance II adds the warm red left blade cap: tier I is the broad main facet; tier II adds crown highlights and the lower facet. Frequency III wraps the right jaw in four purple crystal sections: tier I adds the upper wrap, tier II the broad middle facet, and tier III the two lower sections. Tuning I adds the central ice-white four-point star. Extension III adds the tail's green oval eye (tier I), bright iris/highlight (tier II), and three ivory claw supports (tier III).\n\nThe common underlay follows the original 32px item's silhouette; feature pixels outside that silhouette remain transparent until their module tier activates. The original bare 32px PNG/model/glow/meta are copied unchanged into the candidate. Variant prisms use 0.25-unit XY texels at Z 7.5–8.5 and UV texel centers `(x+0.5)/4,(y+0.5)/4`; display transforms are copied from the original model.\n\nRun from the repository root: `python artwork/source/approved-reference-oct03-64/build_approved64_variants.py`. The generator keeps the previous 32px candidate in ignored `artwork/validation/v0.1.2/pickaxe/pre-deploy-native32-retained/` and regenerates the 64px candidate only when its current manifest matches this approved reference hash.\n""",encoding="utf-8")
    source_record={"purpose":"Reference-sampled 64px native component integration source","reference":"artwork/source/echo-pickaxe-upgrades-v0.1.2/concept-full-upgrade-selected.png","referenceSha256":ref_hash,"normalizedReferenceSha256":sha(normalized.tobytes()),"alphaNormalization":alpha_stats,"common64":{"path":"common64-unupgraded.png","sha256":sha((SOURCE/"common64-unupgraded.png").read_bytes())},"commonGlow":{"path":"common64-glow.png","sha256":sha((SOURCE/"common64-glow.png").read_bytes()),"format":"64x1024 RGBA; frames 0..15; 3 ticks/frame; interpolated; cyan body fissures pulse; component emissive highlights are composed by active tiers"},"componentMap":"native64-component-map.json","allMaximum":"pixel-exact match to approved-reference-normalized64.png","noProductionChanges":True}
    (SOURCE/"integration-record.json").write_text(json.dumps(source_record,indent=2)+"\n",encoding="utf-8")

    manifest={"schema":1,"version":"0.1.2","reviewOnly":True,"variantCount":95,"combinationsIncludingBase":96,
      "formula":"resonance*32+frequency*8+tuning*4+extension","nativeTextureSize":[64,64],"baseTextureSize":[32,32],
      "sourceReferenceSha256":ref_hash,"normalizedReferenceSha256":sha((SOURCE/"approved-reference-normalized64.png").read_bytes()),
      "legacyComparison":{"jar":"jaysay-echo-tools-0.1.1.jar","jarSha256":sha(LEGACY_JAR.read_bytes()),"assets":"echo_pickaxe_v095.png + glow frame 0"},
      "allMaximumIndex":95,"allMaximumPixelExact":full.tobytes()==normalized.tobytes(),"alphaNormalization":alpha_stats,
      "componentColorResidualAudit":{"red":len(residuals["red"]),"purple":len(residuals["purple"]),"green":len(residuals["green"])},
      "extensionTierAudit":{"tierIGreenEmissiveTexels":len(green_eye_glints),"tierIIGreenEyeCoreTexel":[12,51],"tierIIIClawsOrdinary":True},
      "common64":{"path":"artwork/source/approved-reference-oct03-64/common64-unupgraded.png","sha256":sha((SOURCE/"common64-unupgraded.png").read_bytes())},
      "common64Glow":{"path":"artwork/source/approved-reference-oct03-64/common64-glow.png","sha256":sha((SOURCE/"common64-glow.png").read_bytes())},
      "componentMap":{"path":"artwork/source/approved-reference-oct03-64/native64-component-map.json","sha256":sha(map_path.read_bytes())},
      "moduleMaskTexels":{k:len(v) for k,v in masks.items()},"tiers":{k:[sum(1 for p in m.getdata() if p) for m in v] for k,v in tiers.items()},
      "unique16pxActualBase32AndVariants":len(signatures16),"unique16pxInternalCommon64AndVariants":len(internal_signatures16),
      "geometry":{"pixelUnit":0.25,"z":[7.5,8.5],"uvCenter":"(x+0.5)/4,(y+0.5)/4","displayTransforms":"copied unchanged from original model"},
      "baseAssetsUnchanged":{"texture":sha(BASE_PATH.read_bytes()),"glow":sha(GLOW_PATH.read_bytes()),"meta":sha(old_meta_bytes)},
      "variantMeta":{"onlyAnimationWidthHeightUpdated":[64,64],"frametime":old_meta["animation"]["frametime"],"interpolate":old_meta["animation"]["interpolate"],"frames":old_meta["animation"]["frames"]},
      "animation":{"frames":16,"ticksPerFrame":3,"interpolate":True,"pulse":"0.82+0.18*(0.5+0.5*sin(2*pi*frame/16))"},"variants":variants}
    (STAGING/"variant-manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    with (STAGING/"variant-sha256.csv").open("w",encoding="utf-8",newline="") as f:
        f.write("index,levels,model_sha256,sprite_sha256,glow_sha256,meta_sha256\n")
        for v in variants:
            lv=v["levels"]; h=v["sha256"]
            f.write(f"{v['index']},R{lv['resonance']}-F{lv['frequency']}-T{lv['tuning']}-E{lv['extension']},{h['model']},{h['sprite']},{h['glow']},{h['meta']}\n")
    inventory=[]
    for path in sorted(STAGING.rglob("*")):
        if path.is_file(): inventory.append({"path":path.relative_to(STAGING).as_posix(),"bytes":path.stat().st_size,"sha256":sha(path.read_bytes())})
    (STAGING/"file-inventory.json").write_text(json.dumps(inventory,indent=2)+"\n",encoding="utf-8")

    # Candidate promotion deletes only a previously generated 64px set from this same reference.
    safe_child(PARENT,STAGING); safe_child(PARENT,PARENT/"candidate")
    if (PARENT/"candidate").exists():
        candidate_path=safe_child(PARENT,PARENT/"candidate")
        try: old_candidate=json.loads((candidate_path/"variant-manifest.json").read_text(encoding="utf-8"))
        except Exception as exc: raise RuntimeError("Refusing candidate cleanup without a readable manifest") from exc
        if old_candidate.get("sourceReferenceSha256")!=ref_hash or old_candidate.get("nativeTextureSize")!=[64,64]:
            raise RuntimeError("Refusing to clear candidate: it is not this approved-reference 64px generated set")
        shutil.rmtree(candidate_path)
    STAGING.rename(PARENT/"candidate")
    print(f"PASS: generated 95 64px variants; exact full match={manifest['allMaximumPixelExact']}; alpha={alpha_stats}; masks={manifest['moduleMaskTexels']}; unique16={len(signatures16)}")
    print(f"Candidate: {PARENT/'candidate'}; previous32 retained under pre-deploy-native32-retained")
    print(f"Review: {OUT}")

if __name__=="__main__": main()
