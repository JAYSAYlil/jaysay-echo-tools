from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[3]
im=Image.open(ROOT/'artwork/validation/v0.1.11/redesign-v2/imagegen-v004-tight-derived64.png').convert('RGBA')
p=im.load()
for y in range(64):
    xs=[x for x in range(64) if p[x,y][3]]
    if xs: print(y,min(xs),max(xs),[x for x in xs if p[x,y][0]>170 and p[x,y][1]>155 and p[x,y][2]>140])
