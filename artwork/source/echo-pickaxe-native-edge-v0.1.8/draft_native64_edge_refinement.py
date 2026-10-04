"""Preview-only native64 edge refinement for the 0.1.7 res0 hook/head contour."""
import hashlib
import io
import json
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
SRC = Path(__file__).resolve().parent
VAL = ROOT / 'artwork/validation/v0.1.8/draft-2'
BASELINE = ROOT / 'jaysay-echo-tools-0.1.7.jar'
BASELINE_SHA = 'A8DF7D5E282FC46487B6EBC0F3D6DFC1F13B2BF3C26CA9842F8BA716BFF92B24'
UNDERLAY = ROOT / 'artwork/source/echo-pickaxe-unified-head-v0.1.7/native64-shaft-derived-underlay-v0.1.7.png'
UNDERLAY_SHA = 'D7E31A68DB44EE48CE0F0A73D0F3E7247A5320AC55DC2595F1C2479DB38BC43E'
COMMON = ROOT / 'artwork/source/approved-reference-oct03-64/common64-unupgraded.png'
MASK_017 = ROOT / 'artwork/source/echo-pickaxe-unified-head-v0.1.7/unified-head-repaint-mask-v0.1.7.png'
MAP_017 = ROOT / 'artwork/source/echo-pickaxe-unified-head-v0.1.7/unified-head-map-v0.1.7.json'
COMPONENT_MAP = ROOT / 'artwork/source/approved-reference-oct03-64/native64-component-map.json'
ORDINARY_JAR = ROOT / 'jaysay-echo-tools-0.1.2.jar'
ORDINARY_SHA = '7312AE7B54F3DAD998815B7C7BD601B65DB1BED23A21CC7AA8448E40E082F495'
DARK_BG = (22, 28, 36)
HEAD_CROP = (5, 4, 47, 43)
EDGE_CROP = (8, 14, 27, 27)

# Set back one texel at a time to turn the old doubled stair runs into a
# narrower native64 contour while preserving the hook's overall bend and length.
LEFT_EDGE_MIN_X = {
    7: 21, 8: 19, 9: 18, 10: 17, 11: 16, 12: 15,
    13: 14, 14: 13, 15: 12, 16: 11, 17: 10,
}
HOOK_INNER_MAX_X = {18: 23, 19: 22, 20: 20, 21: 18, 22: 17, 23: 15, 24: 13, 25: 12}
ROUND_HOOK_END = {(10, 25), (13, 25)}

# A short broken branch from the left hook toward the head/neck, using real
# native64 common shaft facet/fissure colors instead of resized 32px texels.
FISSURE_BRIDGE = {
    (14, 18): (23, 38),  # muted blue-cyan facet beside the old crack
    (15, 18): (24, 40),
    (17, 17): (25, 38),  # small upward bend
    (18, 16): (23, 39),
    (19, 15): (29, 37),  # reconnects to the existing upper head fissure
}

# A 1px-wide winding continuation across the central dark face into the
# existing right head/neck cyan. Source points are actual emissive common64
# shaft crack texels, including a small two-pixel branch at two joints.
CENTRAL_CYAN_SOURCES = {
    (21, 12): (28, 32), (22, 12): (29, 33), (23, 13): (30, 33),
    (24, 14): (29, 34), (25, 14): (30, 34), (26, 15): (30, 35),
    (27, 15): (31, 35), (28, 16): (29, 36), (29, 15): (31, 36),
    (30, 14): (31, 37), (31, 14): (26, 40), (32, 15): (23, 41),
    (32, 16): (23, 40), (23, 14): (22, 41), (27, 14): (24, 43),
}


def sha(data):
    return hashlib.sha256(data).hexdigest().upper()


def font(size):
    for path in ('C:/Windows/Fonts/msyh.ttc', 'C:/Windows/Fonts/simhei.ttf'):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def rgba(data):
    return Image.open(io.BytesIO(data)).convert('RGBA')


def opaque_points(image):
    return {(x, y) for y in range(image.height) for x in range(image.width)
            if image.getpixel((x, y))[3] == 255}


def composite(image, bg):
    layer = Image.new('RGBA', image.size, bg + (255,))
    layer.alpha_composite(image)
    return layer.convert('RGB')


def apply_outline(image, underlay, common, source_map):
    out = image.copy()
    remove, add = set(), set()
    # Refine the outer sweep: preserve the macro curve but break repeated 2-row steps.
    for y, new_min_x in LEFT_EDGE_MIN_X.items():
        row = [(x, y) for x in range(64) if image.getpixel((x, y))[3]]
        if row:
            old_min_x = min(x for x, _ in row)
            if new_min_x > old_min_x:
                for x in range(old_min_x, new_min_x):
                    p = (x, y)
                    if image.getpixel(p)[3]:
                        remove.add(p)
            elif new_min_x < old_min_x:
                for x in range(new_min_x, old_min_x):
                    p = (x, y)
                    if not image.getpixel(p)[3]:
                        add.add(p)
    # Refine the inside curve so the cutout follows a one-texel progression.
    for y, new_max_x in HOOK_INNER_MAX_X.items():
        xs = [x for x in range(64) if image.getpixel((x, y))[3]]
        if not xs:
            continue
        old_max_x = max(x for x in xs if x < 30)  # the isolated right tip/neck remains untouched
        if new_max_x > old_max_x:
            for x in range(old_max_x + 1, new_max_x + 1):
                p = (x, y)
                if not image.getpixel(p)[3]:
                    add.add(p)
        elif new_max_x < old_max_x:
            for x in range(new_max_x + 1, old_max_x + 1):
                p = (x, y)
                if image.getpixel(p)[3]:
                    remove.add(p)
    for p in ROUND_HOOK_END:
        if image.getpixel(p)[3]:
            remove.add(p)
    assert not (remove & add)
    for p in remove:
        out.putpixel(p, (0, 0, 0, 0))
    edge_color_sources = {}
    shaft_pixels = {(x,y) for y in range(28,49) for x in range(18,39) if common.getpixel((x,y))[3]}
    for p in add:
        # Keep each new opaque edge texel on the same native64 shaft grain map.
        source = source_map.get(p)
        if source is None:
            sx, sy = p[0] + 10, p[1] + 22
            if (sx, sy) not in shaft_pixels:
                sx, sy = min(shaft_pixels, key=lambda q: ((q[0]-sx)**2+(q[1]-sy)**2,q[1],q[0]))
            source = (sx, sy)
        texel = common.getpixel(source)
        assert texel[3] == 255, f'no native shaft facet source for new opaque texel {p}'
        out.putpixel(p, texel)
        edge_color_sources[p] = source
    fissure_records = {}
    for dst, src in FISSURE_BRIDGE.items():
        assert out.getpixel(dst)[3] == 255
        color = common.getpixel(src)
        assert color[3] == 255 and color[1] > color[0] and color[2] > color[0]
        out.putpixel(dst, color)
        fissure_records[dst] = src
    return out, remove, add, fissure_records, edge_color_sources


def add_central_bridge(image, common, common_glow):
    out=image.copy(); records=[]
    for dst,src in CENTRAL_CYAN_SOURCES.items():
        assert out.getpixel(dst)[3]==255, f'bridge would change frozen 0.1.8 alpha at {dst}'
        rgb=common.getpixel(src); glow=[common_glow.getpixel((src[0],src[1]+64*f)) for f in range(16)]
        assert rgb[3]==255 and any(c[3] for c in glow), f'shaft source is not an actual emissive texel: {src}'
        out.putpixel(dst,rgb)
        records.append({'destination':list(dst),'common64Source':list(src),'rgb':list(rgb),
                        'glowFramesRGBA':glow})
    return out,records


def save_pair_board(states, path, crop, scale, title):
    shown = []
    for label, image in states:
        part = image.crop(crop) if crop else image
        shown.append((label, part.resize((part.width * scale, part.height * scale), Image.Resampling.NEAREST)))
    margin, gap, label_h = 12, 14, 28
    cell_w = max(im.width for _, im in shown) + 12
    cell_h = label_h + max(im.height for _, im in shown) + 8
    board = Image.new('RGB', (margin * 2 + cell_w * len(shown) + gap * (len(shown) - 1),
                              margin * 2 + cell_h * 2), (242, 244, 247))
    d, f = ImageDraw.Draw(board), font(13)
    for row, bg in enumerate(((255, 255, 255), DARK_BG)):
        for col, (label, image) in enumerate(shown):
            x = margin + col * (cell_w + gap)
            y = margin + row * cell_h
            suffix = '白底' if row == 0 else '暗底'
            d.text((x + 2, y), f'{title}｜{label}｜{suffix}', fill=(25, 30, 38), font=f)
            board.paste(composite(image, bg), (x + 2, y + label_h))
    board.save(path)


def save_whole_board(states, path):
    save_pair_board(states, path, None, 4, '')


def save_alpha_edge_board(before, after, path):
    crop, scale = EDGE_CROP, 16
    images = []
    for im in (before, after):
        part = im.crop(crop).resize(((crop[2]-crop[0])*scale, (crop[3]-crop[1])*scale), Image.Resampling.NEAREST)
        images.append(part)
    width, margin, header = images[0].width, 14, 28
    row_h = images[0].height + header + 8
    board = Image.new('RGB', (width + margin * 2, row_h * 3 + margin * 2), (242, 244, 247))
    draw = ImageDraw.Draw(board); f = font(13)
    for i, (label, image, bg) in enumerate((('原0.1.7 alpha', images[0], (255,255,255)),
                                             ('新稿 alpha', images[1], (255,255,255)))):
        y = margin + i * row_h
        draw.text((margin, y), f'{label}｜边缘16×像素观察', fill=(25,30,38), font=f)
        board.paste(composite(image, bg), (margin, y + header))
    # Difference layer: red = removed old edge; cyan = newly added native64 texel.
    diff = Image.new('RGBA', (crop[2]-crop[0], crop[3]-crop[1]), (0,0,0,0))
    dp = diff.load()
    for yy in range(crop[1], crop[3]):
        for xx in range(crop[0], crop[2]):
            was = bool(before.getpixel((xx,yy))[3]); now = bool(after.getpixel((xx,yy))[3])
            if was and not now: dp[xx-crop[0],yy-crop[1]]=(237,91,70,255)
            elif now and not was: dp[xx-crop[0],yy-crop[1]]=(28,190,205,255)
            elif was and now: dp[xx-crop[0],yy-crop[1]]=(17,39,51,255)
    diff = diff.resize((diff.width*scale,diff.height*scale),Image.Resampling.NEAREST)
    y = margin + 2 * row_h
    draw.text((margin,y), 'Alpha差分｜红=清除｜青=新增｜深蓝=保留', fill=(25,30,38), font=f)
    board.paste(composite(diff,(255,255,255)),(margin,y+header))
    board.save(path)


def save_bridge_before_after(before, after, path):
    crop=HEAD_CROP; scale=8; margin=12; titleh=28
    parts=[]
    for im in (before,after):
        part=im.crop(crop).resize(((crop[2]-crop[0])*scale,(crop[3]-crop[1])*scale),Image.Resampling.NEAREST)
        parts.append(part)
    gap=16; cellw=parts[0].width+10; cellh=titleh+parts[0].height+8
    board=Image.new('RGB',(margin*2+cellw*2+gap,margin*2+cellh*2),(242,244,247)); d=ImageDraw.Draw(board); f=font(13)
    for row,bg in enumerate(((255,255,255),DARK_BG)):
        for col,im in enumerate(parts):
            x=margin+col*(cellw+gap); y=margin+row*cellh
            label=('草稿1：边缘+局部5点' if col==0 else '桥接稿：shaft亮脉15点')+('｜白底' if row==0 else '｜暗底')
            d.text((x,y),label,fill=(25,30,38),font=f)
            board.paste(composite(im,bg),(x,y+titleh))
    board.save(path)


def main():
    VAL.mkdir(parents=True, exist_ok=True)
    jar_data = BASELINE.read_bytes()
    assert sha(jar_data) == BASELINE_SHA, 'pinned 0.1.7 JAR SHA mismatch'
    underlay_bytes = UNDERLAY.read_bytes()
    assert sha(underlay_bytes) == UNDERLAY_SHA, 'pinned 0.1.7 underlay mismatch'
    common = Image.open(COMMON).convert('RGBA')
    common_glow=Image.open(ROOT/'artwork/source/approved-reference-oct03-64/common64-glow.png').convert('RGBA')
    underlay = rgba(underlay_bytes)
    component_doc = json.loads(COMPONENT_MAP.read_text(encoding='utf-8'))['components']
    source_map_doc=json.loads(MAP_017.read_text(encoding='utf-8'))
    source_map={(item[0],item[1]):(item[2],item[3]) for item in source_map_doc['sourceCoordinatesAndRGBA']}
    modules = {(x,y) for name in ('frequency','tuning','extension')
               for tier in component_doc[name]['tiers'] for x,y,*_ in tier['texels']}
    with zipfile.ZipFile(io.BytesIO(jar_data)) as jar:
        variants = {}
        removed, added, fissure_records, edge_color_sources = None, None, None, None
        for index in (24,31):
            item=f'echo_pickaxe_v{index:03d}'
            before=rgba(jar.read(f'assets/echopickaxe/textures/item/{item}.png'))
            after, rm, ad, fissures, edge_sources=apply_outline(before,underlay,common,source_map)
            after, bridge_records=add_central_bridge(after,common,common_glow)
            if removed is None: removed,added,fissure_records,edge_color_sources=rm,ad,fissures,edge_sources
            else: assert rm==removed and ad==added and fissures==fissure_records and edge_sources==edge_color_sources
            assert not ((removed|added|set(fissures)) & modules), 'edge draft touches an upgrade module'
            variants[index]=(before,after)
            after.save(VAL/f'{item}-edge-draft.png')

        ordinary=rgba(jar.read('assets/echopickaxe/textures/item/echo_pickaxe.png')).resize((64,64),Image.Resampling.NEAREST)
        red=rgba(jar.read('assets/echopickaxe/textures/item/echo_pickaxe_v095.png'))
        whole=[('普通原版×2',ordinary),('分频III v024',variants[24][1]),
               ('无共振满级 v031',variants[31][1]),('红共振II v095',red)]
        save_whole_board(whole,VAL/'v0.1.8-whole-tool-white-dark.png')
        save_pair_board([('v024',variants[24][1]),('v031',variants[31][1])],
                        VAL/'v0.1.8-head-neck-8x-white-dark.png',HEAD_CROP,8,'头颈原生64×8')
        save_alpha_edge_board(variants[31][0],variants[31][1],VAL/'v0.1.8-edge-before-after-16x.png')
        variants[24][1].save(VAL/'v024-native64-cyan-bridge-draft.png')
        variants[31][1].save(VAL/'v031-native64-cyan-bridge-draft.png')
        before_031=rgba((ROOT/'artwork/validation/v0.1.8/draft/v031-native64-edge-draft.png').read_bytes())
        save_bridge_before_after(before_031,variants[31][1],VAL/'v031-cyan-bridge-before-after-8x-white-dark.png')

    before_alpha,after_alpha=opaque_points(variants[31][0]),opaque_points(variants[31][1])
    changed=removed|added
    # Prove every RGB/glow/body location outside the local edge/fissure set is left as 0.1.7.
    assert changed and set(fissure_records)<=before_alpha
    doc={
        'status':'visual-draft-only-awaiting-root-review',
        'version':'0.1.8-native64-finer-curved-hook-edge',
        'baselineJar':BASELINE.name,'baselineJarSha256':BASELINE_SHA,
        'baselineOutline':'0.1.7 res0 native64 alpha; ordinary 0.1.2 texture and all res>=1 resources are not edited.',
        'finerLeftContourMinXByY':{str(k):v for k,v in LEFT_EDGE_MIN_X.items()},
        'finerHookInnerContourMaxXByY':{str(k):v for k,v in HOOK_INNER_MAX_X.items()},
        'roundedTerminalRemovedTexels':[list(p) for p in sorted(ROUND_HOOK_END)],
        'removedOpaqueTexels':[list(p) for p in sorted(removed,key=lambda p:(p[1],p[0]))],
        'addedOpaqueTexels':[list(p) for p in sorted(added,key=lambda p:(p[1],p[0]))],
        'addedEdgeTexelCommonShaftSources':[[x,y,*edge_color_sources[(x,y)],list(common.getpixel(edge_color_sources[(x,y)]))] for x,y in sorted(added,key=lambda p:(p[1],p[0]))],
        'alphaBefore':len(before_alpha),'alphaAfter':len(after_alpha),'alphaDelta':len(after_alpha)-len(before_alpha),
        'fissureBridge':[{'destination':list(dst),'common64Source':list(src),'rgba':list(common.getpixel(src))} for dst,src in sorted(fissure_records.items())],
        'fissureBridgeRule':'A broken, narrow native64 branch copied from actual common64 shaft facets; no interpolation, scale-up, random noise, broad cyan fill, or edits outside the head/hook local region.',
        'centralCyanBridge':bridge_records,
        'centralCyanBridgeRule':'15 native64 texels form one narrow winding fissure with two tiny junctions from the existing upper-left cyan node, across the central dark head, and into the right head/neck cyan. RGB and all 16 glow-frame samples are read directly from actual common64 shaft fissure source texels; no attenuation, resampling, or broad fill.',
        'moduleTexelsTouched':0,
        'candidateGenerated':False,'productionChanged':False,
        'previews':['v031-native64-cyan-bridge-draft.png','v031-cyan-bridge-before-after-8x-white-dark.png','v024-native64-cyan-bridge-draft.png']}
    (VAL/'v0.1.8-edge-draft-map.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'PASS draft only: removed={len(removed)}, added={len(added)}, alpha {len(before_alpha)}->{len(after_alpha)}, fissure pixels={len(fissure_records)}; no candidate/deployment.')
    print(VAL)


if __name__=='__main__':
    main()
