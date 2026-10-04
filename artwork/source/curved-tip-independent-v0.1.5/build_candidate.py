from pathlib import Path
from PIL import Image, ImageDraw
import json

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
BASE = PROJECT / 'artwork/source/approved-reference-oct03-64/common64-unupgraded.png'
OUT = HERE / 'curved-tip-native64.png'
MASK = HERE / 'old-curved-alpha-overlay-mask.png'
QA = PROJECT / 'artwork/validation/v0.1.5/independent-draft'
PALETTE = {
    'deep': (3,25,37,255), 'shadow': (5,40,54,255), 'teal': (5,67,78,255),
    'mid': (7,91,101,255), 'cyan': (17,174,184,255), 'glint': (74,223,228,255),
    'bone': (223,218,193,255), 'bonehi': (246,241,220,255),
}

def checker(im):
    bg = Image.new('RGBA', (64,64), (255,255,255,255)); d=ImageDraw.Draw(bg)
    for y in range(0,64,8):
        for x in range(0,64,8):
            if (x//8+y//8)%2: d.rectangle((x,y,x+7,y+7), fill=(45,52,62,255))
    bg.alpha_composite(im)
    return bg.resize((256,256), Image.Resampling.NEAREST)

base = Image.open(BASE).convert('RGBA')
old = Image.open(HERE/'old32.png').convert('RGBA').resize((64,64), Image.Resampling.NEAREST)
out=base.copy(); bp=base.load(); px=out.load(); op=old.load()
mask=Image.new('L',(64,64)); mp=mask.load(); added=[]
for y in range(8,27):
    for x in range(7,31):
        mp[x,y] = 255 if op[x,y][3] else 0
        if not op[x,y][3]: px[x,y]=(0,0,0,0)
        elif bp[x,y][3]==0: added.append((x,y))
for x,y in added:
    rgb=op[x,y][:3]; pale=min(rgb)>150
    if pale: col=PALETTE['bone'] if (x+y)%3 else PALETTE['bonehi']
    else:
        lum=sum(rgb)//3
        col=PALETTE['deep'] if lum<45 else PALETTE['shadow'] if lum<100 else PALETTE['teal'] if lum<155 else PALETTE['mid']
        if (x*7+y*11)%17==0: col=PALETTE['cyan']
        if (x*13+y*5)%47==0: col=PALETTE['glint']
    px[x,y]=col
for y in range(8,27):
    for x in range(7,31):
        if mp[x,y] and op[x,y][3] and min(op[x,y][:3])>150 and bp[x,y][3]:
            px[x,y]=PALETTE['bonehi'] if (x+y)%3==0 else PALETTE['bone']
out.save(OUT); mask.save(MASK)
QA.mkdir(parents=True,exist_ok=True)
checker(out).save(QA/'curved-tip-native64-whole-4x-checker.png')
checker(old).save(QA/'bare-reference-nearest-whole-4x-checker.png')
pair=Image.new('RGBA',(512,256),(30,30,34,255)); pair.alpha_composite(checker(old),(0,0)); pair.alpha_composite(checker(out),(256,0)); pair.convert('RGB').save(QA/'comparison-bare-left-native-right.png')
checker(out).crop((28,32,124,108)).resize((192,152),Image.Resampling.NEAREST).save(QA/'curved-tip-native-closeup-8x.png')
maskvis=Image.new('RGBA',(64,64),(20,24,31,255)); white=Image.new('RGBA',(64,64),(245,244,236,255)); white.putalpha(mask); maskvis.alpha_composite(white)
maskvis.crop((7,8,31,27)).resize((192,152),Image.Resampling.NEAREST).save(QA/'old-curved-alpha-overlay-closeup-8x.png')
