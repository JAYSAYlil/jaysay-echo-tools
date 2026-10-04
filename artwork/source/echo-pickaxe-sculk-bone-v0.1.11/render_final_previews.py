"""Render concise user-facing views from the frozen v0.1.11 candidate."""
import importlib.util
import io
import json
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[3]
VAL=ROOT/'artwork/validation/v0.1.11'
CAND=VAL/'candidate/assets/echopickaxe'
JAR=ROOT/'jaysay-echo-tools-0.1.10.jar'
PREVIEW_HELPER=ROOT/'artwork/source/echo-pickaxe-unified-head-v0.1.6/build_unified_head_candidate.py'


def load_helper():
    spec=importlib.util.spec_from_file_location('v011_final_preview_helper',PREVIEW_HELPER)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod


def get_font(size):
    return ImageFont.truetype(r'C:\Windows\Fonts\msyh.ttc',size)


def composite(sprite,bg):
    tile=Image.new('RGBA',sprite.size,bg+(255,)); tile.alpha_composite(sprite); return tile.convert('RGB')


def candidate_face(helper,index,frame=0):
    base=Image.open(CAND/f'textures/item/echo_pickaxe_v{index:03d}.png').convert('RGBA')
    glow=Image.open(CAND/f'textures/item/echo_pickaxe_v{index:03d}_glow.png').convert('RGBA')
    model=json.loads((CAND/f'models/item/echo_pickaxe_v{index:03d}.json').read_text(encoding='utf-8'))
    return helper.frontface(base,glow,model,frame)


def main():
    VAL.mkdir(parents=True,exist_ok=True)
    helper=load_helper()
    with zipfile.ZipFile(JAR) as jar:
        ordinary=Image.open(io.BytesIO(jar.read('assets/echopickaxe/textures/item/echo_pickaxe.png'))).convert('RGBA')
    ordinary=ordinary.resize((64,64),Image.Resampling.NEAREST)
    states=[('普通未强化',ordinary),('调谐 I（v004）',candidate_face(helper,4)),
            ('分频 I（v008）',candidate_face(helper,8)),('全满级（v095）',candidate_face(helper,95))]
    scale,margin,label_h,cell_w,left_col=3,12,30,245,44
    icon=64*scale; cell_h=label_h+icon+10
    board=Image.new('RGB',(margin*2+left_col+4*cell_w,margin*2+2*cell_h),(239,242,245)); draw=ImageDraw.Draw(board)
    font=get_font(15); title_font=get_font(14)
    for row,bg in enumerate(((255,255,255),(24,30,38))):
        y=margin+row*cell_h
        draw.text((margin,y+4),'白底' if row==0 else '暗底',font=title_font,fill=(24,30,36))
        for col,(label,sprite) in enumerate(states):
            x=margin+left_col+col*cell_w
            draw.text((x+4,y+4),label,font=font,fill=(24,30,36))
            shown=sprite.resize((icon,icon),Image.Resampling.NEAREST)
            board.paste(composite(shown,bg),(x,y+label_h))
    board_path=VAL/'v0.1.11-final-four-states-white-dark.png'; board.save(board_path)

    gif_frames=[]
    for frame in range(16):
        face=candidate_face(helper,95,frame).resize((icon,icon),Image.Resampling.NEAREST)
        gif=Image.new('RGB',(icon*2+28,icon+42),(239,242,245)); d=ImageDraw.Draw(gif)
        d.text((10,5),'全满级 v095 · 白底',font=title_font,fill=(24,30,36))
        d.text((icon+18,5),'全满级 v095 · 暗底',font=title_font,fill=(24,30,36))
        gif.paste(composite(face,(255,255,255)),(0,26))
        gif.paste(composite(face,(24,30,38)),(icon+14,26))
        gif_frames.append(gif)
    gif_path=VAL/'v0.1.11-fullmax-glow-16frames.gif'
    gif_frames[0].save(gif_path,save_all=True,append_images=gif_frames[1:],duration=150,loop=0,disposal=2,optimize=False)
    print('Saved',board_path)
    print('Saved',gif_path)
    print('board size',board.size,'GIF frames',len(gif_frames),'duration=150ms/frame')


if __name__=='__main__': main()
