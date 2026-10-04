from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import hashlib, json

ROOT = Path(__file__).resolve().parents[3]
SRC = Path(__file__).resolve().parent
OUT = ROOT / 'artwork/validation/v0.1.11/redesign-v2'
REF = Image.open(SRC/'user-reference.png').convert('RGBA')
MASTER = Image.open(ROOT/'artwork/source/approved-reference-oct03-64/approved-reference-normalized64.png').convert('RGBA')
assert REF.size == MASTER.size == (64,64)
diff = [(i%64,i//64,a,b) for i,(a,b) in enumerate(zip(REF.getdata(),MASTER.getdata())) if a != b]
if diff: raise SystemExit(f'Pixel mismatch: {len(diff)}; first={diff[:5]}')

def font(size):
    for p in (r'C:\Windows\Fonts\msyh.ttc',r'C:\Windows\Fonts\arial.ttf'):
        if Path(p).exists(): return ImageFont.truetype(p,size)
    return ImageFont.load_default()

def comp(im,bg):
    x=Image.new('RGBA',im.size,(*bg,255)); x.alpha_composite(im); return x.convert('RGB')

def main():
    # One 8x full sprite, plus aligned native crops enlarged 8x for material reading.
    crops=[('头部与左钩',(6,3,41,31)),('右刃与接颈',(40,8,64,45)),('杆身',(9,25,43,52)),('尾部圆饰',(2,42,23,64))]
    scale=8; margin=18; labelh=32; gap=14
    w=margin*2+64*scale+gap+max((b[2]-b[0])*scale for _,b in crops)
    h=margin*2+labelh+64*scale+gap+sum(labelh+(b[3]-b[1])*scale for _,b in crops)
    board=Image.new('RGB',(w,h),(238,240,242)); d=ImageDraw.Draw(board); f=font(17)
    d.text((margin,8),'用户选定基准：原生64px总览（8×）与同倍率局部',font=f,fill=(25,32,38))
    y=margin+labelh
    whole=REF.resize((512,512),Image.Resampling.NEAREST)
    board.paste(comp(whole,(255,255,255)),(margin,y))
    xx=margin+512+gap
    d.text((xx,y),'透明背景像素观察',font=f,fill=(25,32,38)); yy=y+labelh
    for label,box in crops:
        d.text((xx,yy),label+'  ·  8×',font=f,fill=(25,32,38)); yy+=labelh
        crop=REF.crop(box).resize(((box[2]-box[0])*scale,(box[3]-box[1])*scale),Image.Resampling.NEAREST)
        board.paste(comp(crop,(255,255,255)),(xx,yy)); yy+=crop.height+gap
    path=OUT/'reference-material-inspection.png'; board.save(path)
    # Concise factual pixel/material analysis; observations are grounded in the approved master.
    p=REF.load(); opaque=[(x,y,p[x,y][:3]) for y in range(64) for x in range(64) if p[x,y][3]]
    cyan=lambda c:c[1]>c[0]*1.8 and c[2]>c[0]*1.8 and max(c[1],c[2])>90 and abs(c[1]-c[2])<80
    regions={'left_head':(8,5,39,28),'right_head':(43,17,61,37),'shaft':(14,27,44,50)}
    stats={}
    for name,(x0,y0,x1,y1) in regions.items():
        pix=[p[x,y][:3] for y in range(y0,y1+1) for x in range(x0,x1+1) if p[x,y][3]]
        stats[name]={'opaque':len(pix),'cyanLike':sum(cyan(c) for c in pix),'darkMaxChannelLe65':sum(max(c)<=65 for c in pix)}
    analysis='''# 选定基准的材质观察\n\n输入图已与 `approved-reference-normalized64.png` 做 RGBA 逐像素比较：64×64、0 个不同 texel；以后以该图作为整把强化镐的唯一底图。\n\n- **主体**：柄与头部以深蓝青、近黑的分面为主，明暗块沿镐身轴向延伸；像素边界本身承担切面，不依赖重复贴块。\n- **青脉**：亮青纹数量克制，主要是短而有方向的裂隙/节点，头颈与柄的留白暗面仍占主体；新增裸刃只延续少量走向，不把整片表面改成网纹。\n- **刃与模块**：红、紫、白星、绿眼各自占据清楚的小区域，边界靠相邻暗色切面衔接；裸态骨白只作为窄刃材质，触发相应升级后整段由红/紫模块替代。\n- **尾饰**：绿眼模块是圆形核心；无延展状态保留同尺度深青圆核并用少数分离骨扣点题，不画完整白环或垂牙。\n\n区域计数（用于对照，不代替视觉审查）：\n'''+json.dumps(stats,ensure_ascii=False,indent=2)+'\n'
    (SRC/'reference-material-analysis.md').write_text(analysis,encoding='utf-8')
    (OUT/'reference-pixel-check.json').write_text(json.dumps({'referenceSha256':hashlib.sha256((SRC/'user-reference.png').read_bytes()).hexdigest().upper(),'masterSha256':hashlib.sha256((ROOT/'artwork/source/approved-reference-oct03-64/approved-reference-normalized64.png').read_bytes()).hexdigest().upper(),'rgbaPixelDifferences':len(diff),'regionStats':stats},indent=2)+'\n',encoding='utf-8')
    print(path)
    print(f'RGBA pixel differences: {len(diff)}')

if __name__=='__main__': main()
