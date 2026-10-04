"""Review-only faithful 32px study derived from the user-approved concept."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import json

ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path(__file__).resolve().parent
OUT = ROOT / "artwork/validation/v0.1.2/approved-reference-oct03"
OUT.mkdir(parents=True, exist_ok=True)
BASE = Image.open(ROOT / "src/main/resources/assets/echopickaxe/textures/item/echo_pickaxe.png").convert("RGBA")
assert BASE.size == (32, 32)

# Each tier adds/brightens a coherent crystal facet. Coordinates are native texels.
PALETTE = {
    "ink": (45, 9, 24, 255), "red_shadow": (101, 19, 37, 255), "red": (198, 38, 52, 255),
    "red_light": (245, 88, 78, 255), "warm": (255, 194, 143, 255),
    "violet_shadow": (54, 25, 82, 255), "violet": (128, 55, 180, 255),
    "violet_light": (192, 111, 225, 255), "violet_glint": (245, 207, 255, 255),
    "ice_shadow": (66, 115, 164, 255), "ice": (146, 208, 226, 255), "white": (242, 250, 255, 255),
    "green_shadow": (12, 73, 53, 255), "green": (24, 142, 87, 255),
    "green_light": (67, 204, 126, 255), "green_glint": (161, 255, 195, 255),
    "bone_shadow": (100, 113, 111, 255), "bone": (224, 222, 192, 255),
}

def rows(*spec):
    out = {}
    for y, row in spec:
        for x, color in enumerate(row):
            if color != ".": out[(x, y)] = color
    return out

# Red blade cap: broad stepped silhouette, dark cut edges and warm multifacet crown.
RED1 = {}
for y, xs in {4:{9:"ink",10:"red_shadow",11:"red",12:"red_light",13:"red",14:"red_shadow"},
              5:{8:"ink",9:"red_shadow",10:"red",11:"red_light",12:"red",13:"red_shadow"},
              6:{7:"ink",8:"red_shadow",9:"red",10:"red_light",11:"warm",12:"red_light",13:"red"},
              7:{7:"red_shadow",8:"red",9:"red_light",10:"warm",11:"red",12:"red_shadow"},
              8:{8:"red_shadow",9:"red",10:"red_light",11:"red",12:"red_shadow"},
              9:{9:"red_shadow",10:"red",11:"red_shadow"}}.items():
    RED1.update({(x,y):c for x,c in xs.items()})
RED2 = {(13,4):"red_shadow",(14,4):"ink",(13,5):"red",(14,5):"red_shadow",
        (12,6):"red_light",(13,6):"warm",(12,7):"red",(11,8):"red_shadow",
        (10,9):"red_light",(9,10):"warm",(8,11):"red",(7,12):"red_shadow"}
# Violet wrap follows the outer jaw as a continuous band, widening into large facets.
VIOLET1 = {(24,5):"violet_shadow",(25,5):"violet",(26,5):"violet_light",
 (25,6):"violet",(26,6):"violet_glint",(27,6):"violet_light",
 (26,7):"violet_shadow",(27,7):"violet",(28,7):"violet_light",
 (27,8):"violet",(28,8):"violet_glint",(28,9):"violet_light",
 (28,10):"violet_shadow",(29,10):"violet",(29,11):"violet_light",
 (29,12):"violet",(28,13):"violet_shadow",(29,13):"violet_light"}
VIOLET2 = {(23,4):"violet_shadow",(24,4):"violet",(25,4):"violet_light",
 (27,9):"violet_shadow",(28,11):"violet_glint",(30,12):"violet_shadow",
 (30,13):"violet",(30,14):"violet_light",(29,14):"violet_glint",
 (28,14):"violet",(27,15):"violet_shadow",(28,15):"violet_light",
 (27,16):"violet",(26,16):"violet_shadow"}
VIOLET3 = {(22,5):"violet_shadow",(23,5):"violet_light",(24,6):"violet_glint",
 (25,7):"violet_shadow",(26,8):"violet",(27,10):"violet_light",
 (28,12):"violet_shadow",(29,15):"violet_light",(28,16):"violet_glint"}
# Four-point ice star, with a distinct white core and blue cut facets.
STAR = {(19,7):"ice",(18,8):"ice_shadow",(19,8):"white",(20,8):"ice",
        (17,9):"ice",(18,9):"white",(19,9):"white",(20,9):"white",(21,9):"ice",
        (18,10):"ice",(19,10):"white",(20,10):"ice",(19,11):"ice_shadow"}
# Tail eye is an oval/lozenge on the handle end; tier II sets an iris, tier III adds claw brackets.
GREEN1 = {(3,25):"green_shadow",(4,25):"green",(5,25):"green_shadow",
 (2,26):"green_shadow",(3,26):"green",(4,26):"green_light",(5,26):"green",(6,26):"green_shadow",
 (2,27):"green",(3,27):"green_light",(4,27):"green_glint",(5,27):"green",(6,27):"green_shadow",
 (2,28):"green_shadow",(3,28):"green",(4,28):"green_light",(5,28):"green_shadow",
 (3,29):"green_shadow",(4,29):"green"}
GREEN2 = {(4,26):"ice",(4,27):"white",(5,27):"ice",(4,28):"green_light"}
GREEN3 = {(1,26):"bone_shadow",(2,25):"bone",(1,27):"bone",(6,25):"bone_shadow",
          (6,26):"bone",(7,27):"bone_shadow",(5,29):"bone",(4,30):"bone_shadow",
          (2,29):"bone_shadow",(3,30):"bone"}

LAYERS = {"resonance": [RED1, RED2], "frequency": [VIOLET1,VIOLET2,VIOLET3],
          "tuning": [STAR], "extension": [GREEN1,GREEN2,GREEN3]}
MAX = {"resonance":2,"frequency":3,"tuning":1,"extension":3}
STATES = [("Base",{}),("Resonance II",{"resonance":2}),("Frequency III",{"frequency":3}),
          ("Tuning I",{"tuning":1}),("Extension III",{"extension":3}),("All maximum",MAX)]

def render(levels):
    im = BASE.copy()
    # Palette overlays intentionally replace local detail only within approved material regions.
    for comp, max_level in MAX.items():
        for layer in LAYERS[comp][:levels.get(comp,0)]:
            for (x,y), color in layer.items(): im.putpixel((x,y), PALETTE[color])
    return im

def font(sz):
    return ImageFont.truetype("C:/Windows/Fonts/arial.ttf", sz)

def board(bg, mode, filename):
    cardw, cardh, margin = 250, 210, 18
    out=Image.new("RGB",(margin*2+cardw*3,margin*2+cardh*2),bg); d=ImageDraw.Draw(out)
    fg=(32,36,43) if sum(bg)>400 else (235,239,246)
    for i,(label,levels) in enumerate(STATES):
        x=margin+(i%3)*cardw; y=margin+(i//3)*cardh
        d.text((x+8,y+5),label,font=font(15),fill=fg)
        im=render(levels)
        im=im.resize((128,128),Image.Resampling.NEAREST) if mode=="32" else im.resize((16,16),Image.Resampling.NEAREST).resize((128,128),Image.Resampling.NEAREST)
        tile=Image.new("RGBA",im.size,(*bg,255)); tile.alpha_composite(im); out.paste(tile.convert("RGB"),(x+60,y+28))
        d.text((x+8,y+181),"32px source" if mode=="32" else "16px inventory",font=font(12),fill=fg)
    out.save(OUT/filename)

def main():
    SOURCE.mkdir(parents=True,exist_ok=True)
    for label,levels in STATES:
        render(levels).save(OUT/(label.lower().replace(" ","-")+"-32.png"))
    board((250,250,250),"32","six-states-white-32px.png")
    board((21,26,33),"32","six-states-dark-32px.png")
    board((250,250,250),"16","six-states-inventory-16px.png")
    # Selected concept and faithful native rendering as a direct visual review.
    concept=Image.open(ROOT/"artwork/source/echo-pickaxe-upgrades-v0.1.2/concept-full-upgrade-selected.png").convert("RGBA")
    # Tight alpha crop keeps the concept at its native pixel-art scale ratio.
    concept=concept.crop(concept.getchannel("A").getbbox()).resize((384,384),Image.Resampling.NEAREST)
    native=render(MAX).resize((384,384),Image.Resampling.NEAREST)
    comp=Image.new("RGBA",(820,440),(250,250,250,255)); d=ImageDraw.Draw(comp)
    d.text((22,8),"Approved concept",font=font(16),fill=(30,36,40));d.text((422,8),"32px study · nearest 12×",font=font(16),fill=(30,36,40))
    comp.alpha_composite(concept,(16,38)); comp.alpha_composite(native,(422,38)); comp.convert("RGB").save(OUT/"approved-concept-vs-32px-study.png")
    # A large native view shows whether the 32px design retains readable facets.
    render(MAX).resize((768,768),Image.Resampling.NEAREST).save(OUT/"all-maximum-native-32px-24x.png")
    record={"purpose":"User-approved concept faithful implementation study; review-only; no deployment.","base":"0.1.1 echo_pickaxe.png, unchanged","resolution":[32,32],"states":[{"name":n,"levels":l} for n,l in STATES],"layout":"Red left crystal cap with warm cut facets; violet wrapped right jaw; four-point ice star; green tail eye with bone claw brackets.","note":"Silhouette additions are confined to the original 32x32 canvas and may replace transparent edge texels. Existing display transforms and production code were not changed."}
    (OUT/"study-record.json").write_text(json.dumps(record,indent=2),encoding="utf-8")

if __name__=="__main__": main()
