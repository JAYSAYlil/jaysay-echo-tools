from pathlib import Path
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[3]
ITEM='enhanced_extension_crystal_2'
CAND=ROOT/'artwork/validation/v0.1.1/crystals/candidate/textures/item'
PREV=ROOT/'artwork/validation/v0.1.1/crystals'
PROD=ROOT/'src/main/resources/assets/echopickaxe/textures/item'
OLD=ROOT/'artwork/validation/v0.1.1/crystals/old-tier2-0.1.0.png'
BG=(72,76,82,255)

def card(path,label,downsample=False):
    im=Image.open(path).convert('RGBA')
    if downsample: im=im.resize((16,16),Image.Resampling.NEAREST).resize((128,128),Image.Resampling.NEAREST)
    else: im=im.resize((256,256),Image.Resampling.NEAREST)
    panel=Image.new('RGBA',(276,290),BG)
    panel.alpha_composite(im,((276-im.width)//2,4))
    ImageDraw.Draw(panel).text((6,270),label,fill='white')
    return panel

def compare():
    items=[('extension_crystal','Base',False),('enhanced_extension_crystal','Tier I',False),('old-tier2-0.1.0','Old Tier II',False),(ITEM,'New Tier II',True)]
    for down,label in [(False,'32px'),(True,'16px actual nearest')]:
        panels=[card((CAND/(name+'.png') if is_candidate else (OLD if name=='old-tier2-0.1.0' else PROD/(name+'.png'))),title,down) for name,title,is_candidate in items]
        sheet=Image.new('RGBA',(len(panels)*276,320),BG)
        for i,p in enumerate(panels): sheet.alpha_composite(p,(i*276,28))
        ImageDraw.Draw(sheet).text((8,6),label,fill='white')
        out=PREV/('family-'+('16' if down else '32')+'-v0.1.1.png')
        out.parent.mkdir(parents=True,exist_ok=True); sheet.save(out)
    old=card(OLD,'0.1.0 old')
    new=card(CAND/(ITEM+'.png'),'0.1.1 candidate')
    sheet=Image.new('RGBA',(552,300),BG); sheet.alpha_composite(old,(0,0)); sheet.alpha_composite(new,(276,0))
    sheet.save(PREV/'old-new-32-v0.1.1.png')

def animate():
    base=Image.open(CAND/(ITEM+'.png')).convert('RGBA')
    glow=Image.open(CAND/(ITEM+'_glow.png')).convert('RGBA')
    frames=[]
    raw_frames=[glow.crop((0,i*32,32,(i+1)*32)) for i in range(16)]
    for tick in range(64):
        i=tick//4; j=(i+1)%16; w=(tick%4)/4
        src0,src1=raw_frames[i].load(),raw_frames[j].load()
        interp=Image.new('RGBA',(32,32)); ip=interp.load()
        for y in range(32):
            for x in range(32):
                a=src0[x,y]; b=src1[x,y]
                ip[x,y]=(int(a[0]*(1-w)+b[0]*w),int(a[1]*(1-w)+b[1]*w),int(a[2]*(1-w)+b[2]*w),a[3])
        frame=Image.new('RGBA',(32,32),BG); frame.alpha_composite(base)
        frame.alpha_composite(interp)
        frames.append(frame.resize((256,256),Image.Resampling.NEAREST).convert('RGB'))
    frames[0].save(PREV/(ITEM+'-animation-v0.1.1.gif'),save_all=True,append_images=frames[1:],duration=50,loop=0,optimize=False)

if __name__=='__main__':
    compare(); animate()
