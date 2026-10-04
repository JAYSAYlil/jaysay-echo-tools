"""Build the project icon set from the mod's own pickaxe art (no AI art, no external assets)."""
from PIL import Image, ImageDraw, ImageFilter
from pathlib import Path

root = Path(__file__).resolve().parents[1]
out = root / 'publish'
out.mkdir(exist_ok=True)
tex = root / 'src/main/resources/assets/echopickaxe/textures/item'

base = Image.open(tex / 'echo_pickaxe.png').convert('RGBA')
glow_sheet = Image.open(tex / 'echo_pickaxe_glow.png').convert('RGBA')
frame_h = glow_sheet.height // 16
glow = glow_sheet.crop((0, 0, glow_sheet.width, frame_h)).convert('RGBA')
assert base.size == glow.size, (base.size, glow.size)

sprite = base.copy()
sprite.alpha_composite(glow)

MASTER = 1024
canvas = Image.new('RGBA', (MASTER, MASTER), (10, 14, 18, 255))

# deep radial backdrop
backdrop = Image.new('RGBA', (MASTER, MASTER), (0, 0, 0, 0))
d = ImageDraw.Draw(backdrop)
cx = cy = MASTER // 2
for radius, color in ((460, (18, 60, 62, 190)), (330, (26, 96, 94, 170)), (210, (44, 150, 138, 130))):
    d.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=color)
backdrop = backdrop.filter(ImageFilter.GaussianBlur(90))
canvas.alpha_composite(backdrop)

# faint sculk-ish speckle so the icon is not a flat gradient
import random
random.seed(20261005)
speckle = Image.new('RGBA', (MASTER, MASTER), (0, 0, 0, 0))
sd = ImageDraw.Draw(speckle)
for _ in range(260):
    x = random.randrange(MASTER)
    y = random.randrange(MASTER)
    r = random.choice((3, 4, 5, 7))
    a = random.randint(10, 34)
    sd.ellipse((x - r, y - r, x + r, y + r), fill=(120, 220, 205, a))
speckle = speckle.filter(ImageFilter.GaussianBlur(2.5))
canvas.alpha_composite(speckle)

# vignette
vignette = Image.new('L', (MASTER, MASTER), 0)
vd = ImageDraw.Draw(vignette)
vd.ellipse((-MASTER // 5, -MASTER // 5, MASTER + MASTER // 5, MASTER + MASTER // 5), fill=255)
vignette = vignette.filter(ImageFilter.GaussianBlur(120))
canvas = Image.composite(canvas, Image.new('RGBA', (MASTER, MASTER), (6, 9, 12, 255)), vignette)

# soft cyan bloom behind the pickaxe
bloom = Image.new('RGBA', (MASTER, MASTER), (0, 0, 0, 0))
sprite_big = sprite.resize((MASTER * 4 // 5, MASTER * 4 // 5), Image.NEAREST)
ox = (MASTER - sprite_big.width) // 2
oy = (MASTER - sprite_big.height) // 2
bloom.paste((90, 240, 225, 90), (ox, oy, ox + sprite_big.width, oy + sprite_big.height), sprite_big)
canvas.alpha_composite(bloom.filter(ImageFilter.GaussianBlur(60)))
canvas.alpha_composite(sprite_big, (ox, oy))

targets = {
    'curseforge-icon-400.png': 400,
    'modrinth-icon-256.png': 256,
    'logo-128.png': 128,
    'logo-400.png': 400,
}
for name, size in targets.items():
    canvas.resize((size, size), Image.LANCZOS).save(out / name)
    print('wrote', out / name, size)

# the in-jar logo (mods.toml logoFile) lives at the jar root
canvas.resize((128, 128), Image.LANCZOS).save(root / 'src/main/resources/logo.png')
print('wrote', root / 'src/main/resources/logo.png', 128)
