"""Draw a v0.1.6 material-continuity draft from pinned source JARs only."""
import hashlib, io, json, zipfile
from collections import Counter
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
SRC = Path(__file__).resolve().parent
OUT = ROOT / 'artwork/validation/v0.1.6/unified-head-draft'
ORDINARY_JAR = ROOT / 'jaysay-echo-tools-0.1.2.jar'
ORDINARY_SHA = '7312AE7B54F3DAD998815B7C7BD601B65DB1BED23A21CC7AA8448E40E082F495'
BASELINE_JAR = ROOT / 'jaysay-echo-tools-0.1.5.jar'
BASELINE_SHA = 'CDDEE165380BA810B4C874F0E34C85645B85D8BEBE4D2EF72E1C00EF58DA8706'
COMMON_PATH = ROOT / 'artwork/source/approved-reference-oct03-64/common64-unupgraded.png'
MODULE_MAP = ROOT / 'artwork/source/approved-reference-oct03-64/native64-component-map.json'
SRC_RES = ROOT / 'src/main/resources/assets/echopickaxe'
DARK = (22, 28, 36)
SCALE = 8
CROP = (5, 4, 45, 42)  # full head, throat, and enough upper shaft to see continuity


def sha(data):
    return hashlib.sha256(data).hexdigest().upper()


def read_png(data):
    return Image.open(io.BytesIO(data)).convert('RGBA')


def rgba(path):
    return Image.open(path).convert('RGBA')


def pixels(im):
    return {(x, y) for y in range(im.height) for x in range(im.width) if im.getpixel((x, y))[3]}


def components(m):
    left = set(m)
    sizes = []
    while left:
        q = [left.pop()]
        n = 0
        while q:
            x, y = q.pop(); n += 1
            for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
                p = (x+dx, y+dy)
                if p in left:
                    left.remove(p); q.append(p)
        sizes.append(n)
    return sorted(sizes, reverse=True)


def dist2(a, b):
    return (a[0]-b[0])**2 + (a[1]-b[1])**2


def make_draft(old15, common, ordinary_alpha, modules):
    assert old15.size == common.size == ordinary_alpha.size == (64, 64)
    out = old15.copy()
    op, cp, ap = out.load(), common.load(), ordinary_alpha.load()
    old_tip_alpha = {(x, y) for y in range(8, 28) for x in range(7, 33)
                     if ap[x, y] == 255}

    # Preserve the complete 0.1.5 silhouette. The material mask grows along
    # the approved native head/neck alpha; its edge therefore follows the
    # tool, not a rectangular crop. Keep all active res0 upgrade modules intact.
    head_and_neck = {(x, y) for y in range(6, 42) for x in range(18, 43)
                     if cp[x, y][3] and old15.getpixel((x, y))[3]}
    hook_cells = {(x, y) for (x, y) in old_tip_alpha if old15.getpixel((x, y))[3]}
    material_mask = (head_and_neck | hook_cells) - modules

    common_opaque = pixels(common)
    hook_only = {p for p in hook_cells if p not in common_opaque}
    # Reuse the approved common64 material at native texel scale. Common-body
    # texels restore their exact multi-value facets. The extra legacy hook is
    # filled by a gentle curved nearest-texel mapping from the adjacent head;
    # the small shear prevents a straight copied stripe while retaining the
    # reference's actual face values, crack colors, and lighting.
    mapped = {}
    for x, y in sorted(hook_only, key=lambda p: (p[1], p[0])):
        sx = x + 16 + round((y - 20) / 4)
        sy = y - 7
        candidates = [(xx, yy) for yy in range(max(0, sy-5), min(64, sy+6))
                      for xx in range(max(0, sx-5), min(64, sx+6))
                      if (xx, yy) in common_opaque]
        if not candidates:
            raise RuntimeError(f'No native common64 source texel for hook pixel {(x,y)}')
        source = min(candidates, key=lambda p: (dist2(p, (sx, sy)), p[1], p[0]))
        mapped[(x, y)] = source

    for x, y in material_mask:
        if common.getpixel((x, y))[3]:
            op[x, y] = cp[x, y]
        elif (x, y) in mapped:
            r, g, b, _ = cp[mapped[(x, y)]]
            op[x, y] = (r, g, b, op[x, y][3])

    # Break two broad cyan planes with discontinuous 1px shadow cuts and let
    # a short fissure bridge the center shadow. Every paint color below is an
    # actual texel from the approved body palette, not a new synthetic swatch.
    ridge_dark = cp[35,12][:3] + (255,)
    ridge_mid = cp[34,12][:3] + (255,)
    crack_cyan = cp[33,12][:3] + (255,)
    crack_mid = cp[28,12][:3] + (255,)
    facet_cuts=[
      ([(30,8),(29,9)],ridge_dark), ([(27,10),(26,11)],ridge_mid),
      ([(12,18),(13,19)],ridge_dark), ([(14,20)],ridge_mid),
      ([(17,18),(18,17)],ridge_dark)]
    for points,color in facet_cuts:
        for p in points:
            if p in material_mask and op[p[0],p[1]][3]:op[p[0],p[1]]=color
    shadow_bridge=[(14,20),(15,19),(16,18),(17,18),(18,17),(19,16),(20,16)]
    for p in shadow_bridge:
        if p in material_mask and op[p[0],p[1]][3]:op[p[0],p[1]]=ridge_mid
    # A broken bright line uses only a few texels and shares the bridge path.
    for p,color in [((15,19),crack_mid),((18,17),crack_cyan),((20,16),crack_mid)]:
        if p in material_mask and op[p[0],p[1]][3]:op[p[0],p[1]]=color

    # Continuity facts retained for review and future mask design.
    assert {(x,y) for x,y in pixels(out)} == pixels(old15), 'draft changed the frozen 0.1.5 alpha silhouette'
    assert all(out.getpixel((x,y))[3] == old15.getpixel((x,y))[3] for x in range(64) for y in range(64))
    assert not material_mask & modules
    return out, material_mask, hook_only, mapped


def composite(im, bg):
    layer = Image.new('RGBA', im.size, bg + (255,))
    layer.alpha_composite(im)
    return layer.convert('RGB')


def panel_board(states, output, crop=None, scale=4):
    shown = []
    for label, image in states:
        part = image.crop(crop) if crop else image
        shown.append((label, part.resize((part.width*scale, part.height*scale), Image.Resampling.NEAREST)))
    margin, label_h = 10, 20
    cell_w = max(im.width for _, im in shown) + 16
    cell_h = max(im.height for _, im in shown) + label_h + 8
    board = Image.new('RGB', (margin*2 + cell_w*len(shown), margin*2 + cell_h*2), (246,246,246))
    draw = ImageDraw.Draw(board); font = ImageFont.load_default()
    for row, bg in enumerate(((255,255,255), DARK)):
        ink = (22,26,32) if row == 0 else (240,242,247)
        cy = margin + row*cell_h
        for col, (label, image) in enumerate(shown):
            cx = margin + col*cell_w
            draw.text((cx+3,cy),label,fill=ink,font=font)
            board.paste(composite(image,bg),(cx+3,cy+label_h))
    board.save(output)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    jar_bytes = ORDINARY_JAR.read_bytes()
    assert sha(jar_bytes) == ORDINARY_SHA
    with zipfile.ZipFile(io.BytesIO(jar_bytes)) as z:
        ordinary = read_png(z.read('assets/echopickaxe/textures/item/echo_pickaxe.png'))
    old_alpha = ordinary.getchannel('A').resize((64,64), Image.Resampling.NEAREST)
    baseline_bytes = BASELINE_JAR.read_bytes()
    assert sha(baseline_bytes) == BASELINE_SHA, 'pinned 0.1.5 baseline SHA mismatch'
    with zipfile.ZipFile(io.BytesIO(baseline_bytes)) as baseline:
        old15 = read_png(baseline.read('assets/echopickaxe/textures/item/echo_pickaxe_v031.png'))
    common = rgba(COMMON_PATH)
    component = json.loads(MODULE_MAP.read_text(encoding='utf-8'))['components']
    modules = {(x,y) for name in ('frequency','tuning','extension')
               for tier in component[name]['tiers'] for x,y,*_ in tier['texels']}
    draft, material_mask, hook_only, mapping = make_draft(old15,common,old_alpha,modules)

    # Other panels are inputs for comparison only; no resources are written.
    common_whole = common.copy()
    states=[('0.1.5 v031 (current)',old15),('0.1.6 material draft',draft),
            ('approved common64 body',common_whole),
            ('ordinary 0.1.2 32px ×2',ordinary.resize((64,64),Image.Resampling.NEAREST))]
    panel_board(states,OUT/'unified-head-whole-tool-white-dark.png',scale=4)
    panel_board(states,OUT/'unified-head-neck-8x-white-dark.png',crop=CROP,scale=SCALE)

    mm=Image.new('RGBA',(64,64),(0,0,0,0))
    for x,y in material_mask: mm.putpixel((x,y),(70,190,255,255))
    mm.save(OUT/'unified-head-material-mask-draft.png')
    report={'status':'visual-draft-only-root-review-pending','version':'0.1.6-unified-head-material',
      'currentRes0Source':'jaysay-echo-tools-0.1.5.jar; SHA-256 pinned to CDDEE165380BA810B4C874F0E34C85645B85D8BEBE4D2EF72E1C00EF58DA8706',
      'ordinaryAlphaSource':'0.1.2 ordinary PNG alpha only, nearest-neighbor 2x; no old RGB read',
      'approvedMaterialSource':'approved-reference-oct03-64/common64-unupgraded.png',
      'outlineRule':'All draft alpha pixels remain byte-pixel identical to current 0.1.5 res0 v031.',
      'materialRule':'Restore exact approved common64 texels across the complete head/neck native-alpha region; add legacy hook-only texels by curved native nearest-texel mapping from the adjacent common head. Break two broad cyan planes with short 1px body-palette shadow cuts and connect the center with a short broken crack bridge.',
      'previousRoi':[7,8,32,27],
      'proposedMaterialBounds':[min(x for x,y in material_mask),min(y for x,y in material_mask),
                                max(x for x,y in material_mask),max(y for x,y in material_mask)],
      'materialMaskPixels':len(material_mask),'hookOnlyTexels':len(hook_only),
      'sourceMapping':{'hookOnly':'sx=x+16+round((y-20)/4), sy=y-7; nearest opaque common64 texel within radius 5',
                       'mappedTexels':len(mapping),'mappingRecords':[[x,y,*mapping[(x,y)]] for x,y in sorted(mapping,key=lambda p:(p[1],p[0]))]},
      'activeModulesExcluded':['frequency','tuning','extension'],'alphaUnchanged':True,
      'previews':['unified-head-whole-tool-white-dark.png','unified-head-neck-8x-white-dark.png'],
      'maskDraft':'unified-head-material-mask-draft.png','candidateGenerated':False,'productionChanged':False}
    (OUT/'unified-head-draft-map.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    draft.save(OUT/'unified-head-v031-draft.png')
    print(f'PASS preview only: full alpha unchanged; mask={len(material_mask)} hook-only={len(hook_only)}; outputs={OUT}')


if __name__ == '__main__':
    main()
