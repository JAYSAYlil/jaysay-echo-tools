from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[3]
p=Image.open(ROOT/'artwork/validation/v0.1.11/redesign-v2/imagegen-v004-tight-derived64.png').convert('RGBA').load()
for y in range(64):
    chars=[]
    for x in range(64):
        r,g,b,a=p[x,y]
        if not a:c=' '
        elif r>170 and g>155 and b>140 and abs(r-g)<55:c='W'
        elif g>r*1.65 and g>b*1.05 and g>75:c='G'
        elif b>r*1.65 and b>g*1.15 and b>60:c='P'
        elif g>r*1.7 and b>r*1.7 and max(g,b)>100:c='C'
        elif max(r,g,b)<45:c='.'
        else:c='o'
        chars.append(c)
    line=''.join(chars).rstrip()
    if line.strip(): print(f'{y:02d} {line}')
