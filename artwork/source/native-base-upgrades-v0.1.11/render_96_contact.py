from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json
val=Path('artwork/validation/v0.1.11/native-base-upgrades')
cand=val/'candidate';manifest=json.loads((cand/'candidate-manifest.json').read_text(encoding='utf-8'))
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',15)
cols,tw,th=8,200,180
out=Image.new('RGB',(cols*tw,12*th),(246,247,248));d=ImageDraw.Draw(out)
for i in range(96):
 r=i//32;f=(i%32)//8;t=(i%8)//4;e=i%4
 col=i%cols;row=i//cols;x=col*tw+(tw-128)//2;y=row*th+2
 tex=Image.open(cand/manifest['variants'][str(i)]['base']).convert('RGBA').resize((128,128),Image.Resampling.NEAREST)
 out.paste(tex,(x,y),tex)
 cx=col*tw+tw//2
 d.text((cx,y+142),f'编号{i:03d} 共振{r} 分频{f}',font=font,fill=(22,26,32),anchor='mm')
 d.text((cx,y+162),f'调谐{t} 延展{e}',font=font,fill=(22,26,32),anchor='mm')
out.save(val/'candidate-96-states-contact.png')
