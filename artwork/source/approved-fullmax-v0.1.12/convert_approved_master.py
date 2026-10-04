from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import hashlib, json, shutil
import numpy as np
from scipy.ndimage import label

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[2]
SOURCE=HERE/'approved-master-original.png'
OUT=HERE/'candidates'; VAL=PROJECT/'artwork/validation/approved-fullmax-v0.1.12'
OUT.mkdir(parents=True,exist_ok=True); VAL.mkdir(parents=True,exist_ok=True)
THRESHOLD=128
SIZES=(64,80,96,128)
def sha_bytes(b): return hashlib.sha256(b).hexdigest().upper()
def sha(path): return sha_bytes(path.read_bytes())
# The user's approved attachment is already saved byte-for-byte in this directory.
source_copy=SOURCE
if not source_copy.exists(): raise SystemExit(f'missing approved master: {source_copy}')
im=Image.open(source_copy).convert('RGBA'); src=np.asarray(im).copy(); h,w,_=src.shape
if w!=h: raise SystemExit(f'expected square source canvas, got {w}x{h}')
a=src[:,:,3]; rgb=src[:,:,:3]
mask=a>=THRESHOLD
labels,n=label(mask,np.ones((3,3),dtype=np.uint8)); counts=np.bincount(labels.ravel()); counts[0]=0
largest=int(counts.max()) if n else 0
main_label=int(np.argmax(counts)) if n else 0
clean=(labels==main_label) if n else np.zeros_like(mask)
if largest!=int(clean.sum()): raise SystemExit('largest-component calculation failed')
Image.fromarray((clean.astype(np.uint8)*255),'L').save(VAL/'clean-main-alpha-mask.png')
# Center-sample every target over the entire square source canvas: no crop, fit, palette change, or redraw.
indices={}
for size in SIZES:
 ix=np.floor((np.arange(size)+0.5)*w/size).astype(np.int32)
 iy=np.floor((np.arange(size)+0.5)*h/size).astype(np.int32)
 indices[size]={'x':ix.tolist(),'y':iy.tolist()}
 out=np.zeros((size,size,4),dtype=np.uint8)
 for oy,sy in enumerate(iy):
  for ox,sx in enumerate(ix):
   out[oy,ox,:3]=rgb[sy,sx]
   out[oy,ox,3]=255 if clean[sy,sx] else 0
 Image.fromarray(out,'RGBA').save(OUT/f'approved-fullmax-{size}.png',format='PNG',optimize=False)
source_sha=sha(source_copy)
alpha_counts={str(k):int(v) for k,v in zip(*np.unique(a,return_counts=True))}
threshold_reports={}
for t in (1,16,64,128,200,250,253,255):
 m=a>=t; lab,nn=label(m,np.ones((3,3),dtype=np.uint8)); cs=np.bincount(lab.ravel());cs[0]=0
 threshold_reports[str(t)]={'bbox':list(Image.fromarray((m.astype(np.uint8)*255),'L').getbbox() or []),'components8':int(nn),'largest8':int(cs.max()) if nn else 0,'pixels':int(m.sum())}
manifest={'source':{'path':'approved-master-original.png','originalPath':str(SOURCE),'sha256':source_sha,'bytes':source_copy.stat().st_size,'size':[w,h],'mode':'RGBA','format':'PNG','info':{k:(len(v) if isinstance(v,bytes) else v) for k,v in im.info.items()},'alphaLevelCounts':alpha_counts},
 'alphaCleaning':{'threshold':THRESHOLD,'comparison':'>=','connectivity':8,'componentsAtThreshold':int(n),'largestComponentPixels':largest,'bbox':list(Image.fromarray((clean.astype(np.uint8)*255),'L').getbbox() or []),'thresholdReports':threshold_reports,'note':'Source copy is byte-exact. Each candidate takes exact source RGB at its center sample and binary alpha from the largest >=128-alpha component.'},
 'gridAnalysis':{'visualEstimateSourcePixelsPerLogicalCell':[15,16],'logicalGridEstimate':'about 80 cells across the full 1254px square','primaryCandidate':80,'sourcePixelsPerPrimaryTexel':w/80,'method':'center-sample the full square canvas; no crop, stretch, palette quantization, reconstruction, or component edits.'},
 'sampling':{'method':'center','canvas':'whole source canvas','targets':{},'primarySize':80}}
for size in SIZES:
 p=OUT/f'approved-fullmax-{size}.png'
 manifest['sampling']['targets'][str(size)]={'path':str(Path('candidates')/p.name),'sha256':sha(p),'bytes':p.stat().st_size,'size':[size,size],'sampleXSourceIndices':indices[size]['x'],'sampleYSourceIndices':indices[size]['y']}
(VAL/'sampling-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',22)
def preview_sheet(fname,bg):
 margin=24; gap=20; scale=4; widths=[s*scale for s in SIZES]
 total=sum(widths)+gap*(len(SIZES)-1)+margin*2; height=600
 board=Image.new('RGB',(total,height),bg);d=ImageDraw.Draw(board);x=margin
 for s,wi in zip(SIZES,widths):
  sprite=Image.open(OUT/f'approved-fullmax-{s}.png').convert('RGBA').resize((wi,wi),Image.Resampling.NEAREST)
  y=(height-60-wi)//2; board.paste(sprite,(x,y),sprite)
  d.text((x+wi//2,y+wi+28),f'{s}×{s}',font=font,fill=(20,23,28) if bg==(255,255,255) else (244,246,249),anchor='mm')
  x+=wi+gap
 board.save(VAL/fname)
for bg,name in [((255,255,255),'resolution-comparison-white-4x.png'),((25,29,36),'resolution-comparison-dark-4x.png')]: preview_sheet(name,bg)
source=Image.open(source_copy).convert('RGBA');bg=Image.new('RGBA',source.size,(25,29,36,255));bg.alpha_composite(source);bg.convert('RGB').save(VAL/'approved-source-dark.png')
print('source',f'{w}x{h}','RGBA',source_sha)
print('alpha>=128',int(mask.sum()),'bbox',manifest['alphaCleaning']['bbox'],'components8',n,'largest',largest)
print('grid estimate 15-16 source px/logical cell; 80 sample step',w/80)
print('outputs',{str(s):sha(OUT/f'approved-fullmax-{s}.png') for s in SIZES})
