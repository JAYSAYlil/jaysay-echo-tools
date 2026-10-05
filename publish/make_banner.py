"""Build the Modrinth banner and the shared gallery folder from the mod's own art."""
import shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

root = Path(__file__).resolve().parents[1]
tex = root / 'src/main/resources/assets/echopickaxe/textures/item'
out = root / 'publish/modrinth/gallery'
out.mkdir(parents=True, exist_ok=True)

W, H = 1280, 640
canvas = Image.new('RGBA', (W, H), (9, 13, 17, 255))

base = Image.open(tex / 'echo_pickaxe.png').convert('RGBA')
sheet = Image.open(tex / 'echo_pickaxe_glow.png').convert('RGBA')
frame_h = sheet.height // 16
glow = sheet.crop((0, 0, sheet.width, frame_h)).convert('RGBA')
sprite = base.copy()
sprite.alpha_composite(glow)

backdrop = Image.new('RGBA', (W, H), (0, 0, 0, 0))
d = ImageDraw.Draw(backdrop)
for radius, color in ((760, (16, 58, 60, 200)), (560, (24, 92, 90, 180)), (360, (40, 142, 132, 140))):
    d.ellipse((W // 2 - radius, H // 2 - radius, W // 2 + radius, H // 2 + radius), fill=color)
canvas.alpha_composite(backdrop.filter(ImageFilter.GaussianBlur(120)))

import random
random.seed(20261005)
speckle = Image.new('RGBA', (W, H), (0, 0, 0, 0))
sd = ImageDraw.Draw(speckle)
for _ in range(420):
    x, y = random.randrange(W), random.randrange(H)
    r = random.choice((3, 4, 6, 8))
    sd.ellipse((x - r, y - r, x + r, y + r), fill=(120, 220, 205, random.randint(10, 32)))
canvas.alpha_composite(speckle.filter(ImageFilter.GaussianBlur(3)))

SPRITE = 456
big = sprite.resize((SPRITE, SPRITE), Image.NEAREST)
sx, sy = 70, (H - SPRITE) // 2
bloom = Image.new('RGBA', (W, H), (0, 0, 0, 0))
bloom.paste((90, 240, 225, 95), (sx, sy, sx + SPRITE, sy + SPRITE), big)
canvas.alpha_composite(bloom.filter(ImageFilter.GaussianBlur(70)))
canvas.alpha_composite(big, (sx, sy))

def load_font(size, bold=False):
    for name in (('segoeuib.ttf' if bold else 'segoeui.ttf'), 'arialbd.ttf' if bold else 'arial.ttf'):
        p = Path('C:/Windows/Fonts') / name
        if p.is_file():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()

draw = ImageDraw.Draw(canvas)
x0 = 580
right = W - 56
title = "JaySay's Echo Tools"
title_size = 64
while title_size > 40 and draw.textlength(title, font=load_font(title_size, True)) > right - x0:
    title_size -= 2
title_font = load_font(title_size, True)
sub_font = load_font(30)
draw.text((x0, 208), title, font=title_font, fill=(226, 255, 250, 255))
draw.text((x0, 300), "Sculk-forged pickaxe that senses nearby ores", font=sub_font, fill=(150, 226, 214, 255))
draw.text((x0, 340), "and guides you with a luminous echo trail.", font=sub_font, fill=(150, 226, 214, 255))
draw.line((x0, 400, x0 + 470, 400), fill=(60, 140, 132, 160), width=3)
draw.text((x0, 424), "Minecraft 1.20.1  ·  Forge 47.x", font=load_font(30, True), fill=(96, 208, 196, 255))

canvas.convert('RGB').save(out / '00-banner.png')
print('banner:', out / '00-banner.png', canvas.size)

# gameplay gallery, in the order they should appear
shots = [
    ('01-dark-room-in-hand.png', 'echo-emissive-night-hands.png'),
    ('02-creative-tab-a.png', 'echo-emissive-night-gui-a.png'),
    ('03-creative-tab-b.png', 'echo-emissive-night-gui-b.png'),
    ('04-white-background.png', 'echo-emissive-white-enhanced-extension-crystal-2.png'),
    ('05-first-person-max-tier.png', 'echo-emissive-hand-first-right-max.png'),
    ('06-upgrade-comparison.png', 'echo-emissive-upgrade-gui-comparison.png'),
    ('07-held-in-context.png', 'echo-emissive-upgrade-max-held-context.png'),
]
src = root / 'artwork/validation/v0.3.2'
copied = []
for target, source in shots:
    s = src / source
    if not s.is_file():
        print('missing:', s)
        continue
    shutil.copy2(s, out / target)
    copied.append(target)
print('gallery images:', len(copied))
