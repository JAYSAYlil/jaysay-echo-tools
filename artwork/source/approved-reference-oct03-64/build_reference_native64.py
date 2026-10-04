"""Create a review-only 64x64 native sprite sampled from the approved concept."""
from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path(__file__).resolve().parent
OUT = ROOT / "artwork/validation/v0.1.2/approved-reference-oct03-64"
REFERENCE = ROOT / "artwork/source/echo-pickaxe-upgrades-v0.1.2/concept-full-upgrade-selected.png"

def font(size):
    return ImageFont.truetype("C:/Windows/Fonts/arial.ttf", size)

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    source = Image.open(REFERENCE).convert("RGBA")
    bbox = source.getchannel("A").getbbox()
    crop = source.crop(bbox)
    # Preserve reference proportions and center it within one transparent texel of padding.
    available_w, available_h = 62, 62
    scale = min(available_w/crop.width, available_h/crop.height)
    size = (round(crop.width*scale), round(crop.height*scale))
    native = crop.resize(size, Image.Resampling.NEAREST)
    sprite = Image.new("RGBA", (64,64), (0,0,0,0))
    sprite.alpha_composite(native, ((64-size[0])//2, (64-size[1])//2))
    sprite.save(OUT / "echo-pickaxe-approved-native64.png")

    # Same exact 64px sprite on contrasting backgrounds. Nearest scaling exposes its texel grain.
    for name, bg in (("white",(250,250,250)),("dark",(19,24,31))):
        canvas=Image.new("RGB",(512,552),bg)
        d=ImageDraw.Draw(canvas)
        fg=(30,36,43) if name=="white" else (235,239,246)
        d.text((18,12),f"Approved concept · sampled native 64px · {name} background",font=font(16),fill=fg)
        shown=sprite.resize((512,512),Image.Resampling.NEAREST)
        layer=Image.new("RGBA",shown.size,(*bg,255)); layer.alpha_composite(shown)
        canvas.paste(layer.convert("RGB"),(0,40))
        canvas.save(OUT/f"native64-{name}-background.png")

    # The comparison pairs the selected reference with its exact nearest-sampled 64px output.
    display=crop.resize((384,384),Image.Resampling.NEAREST)
    rendered=sprite.resize((384,384),Image.Resampling.NEAREST)
    for name,bg in (("white",(250,250,250,255)),("dark",(19,24,31,255))):
        board=Image.new("RGBA",(800,430),bg); d=ImageDraw.Draw(board)
        fg=(30,36,43) if name=="white" else (235,239,246)
        d.text((18,10),"Approved visual source",font=font(16),fill=fg)
        d.text((414,10),"Native 64×64 sample",font=font(16),fill=fg)
        board.alpha_composite(display,(8,38)); board.alpha_composite(rendered,(408,38))
        board.convert("RGB").save(OUT/f"approved-concept-vs-native64-{name}.png")

    record={
        "purpose":"Review-only, faithful native-resolution sampling of the user's approved concept.",
        "approvedReference":"artwork/source/echo-pickaxe-upgrades-v0.1.2/concept-full-upgrade-selected.png",
        "sourceDimensions":list(source.size),"sourceAlphaBounds":list(bbox),
        "method":"Crop alpha bounds, preserve aspect ratio, nearest-neighbor sample to 62px maximum bounds, center on transparent 64x64 canvas.",
        "nativeDimensions":[64,64],"itemDisplayTransform":"unchanged / not included in this study",
        "features":"Full dark sculk textured body and cyan fissures from exact approved source; broad warm red multifacet crown with white glints; four separated purple jaw crystal segments; central four-point ice-white star; large green oval eye with visible pupil/highlight and three ivory claws.",
        "status":"visual review only; no production texture, Java, model, metadata, or 95-candidate files changed."
    }
    (OUT/"sampling-record.json").write_text(json.dumps(record,indent=2),encoding="utf-8")

if __name__=="__main__": main()
