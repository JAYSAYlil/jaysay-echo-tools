from pathlib import Path
from PIL import Image,ImageDraw
root=Path.cwd(); raw=root/'artwork/source/v0.1.0/enhanced_extension_crystal_2-imagegen-raw-v2.png'; out=root/'artwork/validation/v0.1.0/crystals/candidate/textures/item/enhanced_extension_crystal_2.png'; val=out.parents[2]
im=Image.open(raw).convert('RGBA'); alpha=im.getchannel('A'); bbox=alpha.point(lambda a:255 if a>=128 else 0).getbbox(); crop=im.crop(bbox); target_h=28; target_w=round(crop.width*target_h/crop.height); resized=crop.resize((target_w,target_h),Image.Resampling.NEAREST)
# Keep generated RGB unchanged; hard-threshold only alpha. Center with >=2px clear edge margin.
px=(32-target_w)//2; py=(32-target_h)//2
canvas=Image.new('RGBA',(32,32),(0,0,0,0))
for y in range(target_h):
 for x in range(target_w):
  r,g,b,a=resized.getpixel((x,y)); canvas.putpixel((px+x,py+y),(r,g,b,255 if a>=128 else 0))
out.parent.mkdir(parents=True,exist_ok=True); canvas.save(out,optimize=False)
old=Image.open(root/'src/main/resources/assets/echopickaxe/textures/item/enhanced_extension_crystal_2.png').convert('RGBA')
# Meaningful 16px version is a true nearest reduction of the final 32px icon.
small=canvas.resize((16,16),Image.Resampling.NEAREST)
# Comparison sheet with transparent checker, exact dimensions shown by panel labels.
cell=192; sheet=Image.new('RGB',(cell*4,cell+48),(239,240,242)); d=ImageDraw.Draw(sheet)
def panel(img,idx,label):
 x=idx*cell; d.text((x+8,8),label,fill=(20,22,26)); tile=Image.new('RGBA',(cell,cell),(70,74,82,255));
 if img.size==(32,32): scaled=img.resize((cell,cell),Image.Resampling.NEAREST)
 else: scaled=img.resize((cell,cell),Image.Resampling.NEAREST)
 tile.alpha_composite(scaled); sheet.paste(tile.convert('RGB'),(x,40))
panel(old,0,'old 32x32 (display enlarged)'); panel(canvas,1,'candidate 32x32 (display enlarged)'); panel(small,2,'candidate 16x16 actual pixels'); panel(small.resize((32,32),Image.Resampling.NEAREST),3,'candidate 16px shown x2')
sheet.save(root/'artwork/validation/v0.1.0/crystals/old-new-32-16.png')
print({'source_size':im.size,'source_bbox_alpha_ge128':bbox,'crop_size':crop.size,'scaled_size':(target_w,target_h),'offset':(px,py),'final_alpha_values':sorted(set(canvas.getchannel('A').getdata())),'opaque_pixels':sum(a>0 for a in canvas.getchannel('A').getdata()),'output':str(out)})
