"""Import the design-only imagegen raster into a nearest-neighbor native64 review sprite."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import hashlib,json

ROOT=Path(__file__).resolve().parents[3]
SRC=Path(__file__).resolve().parent
OUT=ROOT/'artwork/validation/v0.1.11/redesign-v2'
RAW=SRC/'imagegen-v004-tight-raw.png'
MASTER=SRC/'user-reference.png'

def font(size):
    for p in (r'C:\Windows\Fonts\msyh.ttc',r'C:\Windows\Fonts\arial.ttf'):
        if Path(p).is_file(): return ImageFont.truetype(p,size)
    return ImageFont.load_default()

def composite(im,bg):
    tile=Image.new('RGBA',im.size,(*bg,255)); tile.alpha_composite(im); return tile.convert('RGB')

def main():
    raw=Image.open(RAW).convert('RGBA')
    crop=raw.crop(raw.getchannel('A').getbbox())
    # Preserve the full silhouette and its transparent background in a square canvas.
    side=max(crop.size); square=Image.new('RGBA',(side,side),(0,0,0,0))
    square.alpha_composite(crop,((side-crop.width)//2,(side-crop.height)//2))
    draft=square.resize((64,64),Image.Resampling.NEAREST)
    master=Image.open(MASTER).convert('RGBA')
    # Binary alpha and a small no-dither palette make the native64 read meaningful.
    # Keep the raw and unquantized derivative separately for comparison.
    dp=draft.load()
    for y in range(64):
        for x in range(64):
            if dp[x,y][3]<128: dp[x,y]=(0,0,0,0)
            else: dp[x,y]=(*dp[x,y][:3],255)
    draft.save(OUT/'imagegen-v004-tight-derived64-unquantized.png')
    pal=draft.convert('RGB').quantize(colors=28,method=Image.Quantize.MEDIANCUT,dither=Image.Dither.NONE).convert('RGB')
    quant=Image.new('RGBA',(64,64),(0,0,0,0)); quant.alpha_composite(pal.convert('RGBA'))
    qpx=quant.load()
    for y in range(64):
        for x in range(64):
            if draft.getpixel((x,y))[3]==0: qpx[x,y]=(0,0,0,0)
            else: qpx[x,y]=(*qpx[x,y][:3],255)
    quant.save(OUT/'imagegen-v004-tight-derived64.png')
    for size in (16,32): quant.resize((size,size),Image.Resampling.NEAREST).save(OUT/f'imagegen-v004-tight-derived{size}.png')
    # Readability plate at actual 64, 32 and 16 pixels on both backgrounds.
    sizes=[(64,4),(32,4),(16,8)]
    gap=18; label_h=28; margin=14
    positions=[]; cursor=margin
    for s,scale in sizes:
        positions.append(cursor); cursor+=s*scale+gap
    w=cursor-gap+margin
    h=margin*2+2*(label_h+256+gap)
    board=Image.new('RGB',(w,h),(237,240,243)); d=ImageDraw.Draw(board); f=font(16)
    for row,bg in enumerate(((255,255,255),(24,30,38))):
        y=margin+row*(label_h+256+gap)
        for col,(s,scale) in enumerate(sizes):
            x=positions[col]
            d.text((x,y+2),f'{s}px • {"白底" if row==0 else "暗底"}',font=f,fill=(25,32,38))
            im=quant.resize((s,s),Image.Resampling.NEAREST).resize((s*scale,s*scale),Image.Resampling.NEAREST)
            board.paste(composite(im,bg),(x,y+label_h))
    board.save(OUT/'imagegen-v004-tight-64-32-16-readability.png')
    # Compare the design-only conversion with the exact master, without modifying either.
    cmp=Image.new('RGB',(4*256+3*14,2*(256+42)+14),(237,240,243)); d=ImageDraw.Draw(cmp)
    cells=[('母图 fullmax',master),('AI参考转64，28色草稿',quant)]
    for row,bg in enumerate(((255,255,255),(24,30,38))):
        y=14+row*298
        for col,(label,im) in enumerate(cells):
            x=14+col*270; d.text((x,y+2),label,font=f,fill=(25,32,38))
            cmp.paste(composite(im.resize((256,256),Image.Resampling.NEAREST),bg),(x,y+28))
    cmp.save(OUT/'imagegen-v004-tight-vs-master-white-dark-4x.png')
    (OUT/'imagegen-import-record.json').write_text(json.dumps({
      'rawSha256':hashlib.sha256(RAW.read_bytes()).hexdigest().upper(),
      'sourceMasterSha256':hashlib.sha256(MASTER.read_bytes()).hexdigest().upper(),
      'rawSize':list(raw.size),'alphaCrop':list(raw.getchannel('A').getbbox()),
      'operation':'alpha-bbox crop; transparent square pad; NEAREST resize to 64x64; alpha threshold 128; no-dither 28-color quantization; derived 16/32 views use NEAREST',
      'productionAsset':False,'imagegenSource':'artwork/source/echo-pickaxe-redesign-reference-v2/imagegen-v004-tight-raw.png'
    },indent=2)+'\n',encoding='utf-8')
    print(OUT/'imagegen-v004-tight-vs-master-white-dark-4x.png')

if __name__=='__main__': main()
