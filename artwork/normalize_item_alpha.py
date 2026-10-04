"""Mechanically remove semitransparent antialias pixels from the three sprites.

RGB is copied unchanged. Alpha below 128 becomes 0; alpha at least 128 becomes
255. Exact source images are kept under artwork/source before conversion.
"""
from pathlib import Path
import shutil
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'src/main/resources/assets/echopickaxe/textures/item'
SOURCES = ROOT / 'artwork/source'
SOURCES.mkdir(parents=True, exist_ok=True)

for item in ('echo_pickaxe', 'echo_crystal', 'echo_upgrade_smithing_template'):
    path = ASSETS / f'{item}.png'
    backup = SOURCES / f'{item}-before-alpha-clean-32x32.png'
    if not backup.exists():
        shutil.copy2(path, backup)
    image = Image.open(path).convert('RGBA')
    pixels = list(image.getdata())
    cleaned = [(r, g, b, 255 if a >= 128 else 0) for r, g, b, a in pixels]
    changed = sum(old[3] != new[3] for old, new in zip(pixels, cleaned))
    image.putdata(cleaned)
    image.save(path)
    opaque = sum(alpha != 0 for _, _, _, alpha in cleaned)
    print(f'{item}: alpha-changed={changed}, opaque={opaque}, source={backup}')
