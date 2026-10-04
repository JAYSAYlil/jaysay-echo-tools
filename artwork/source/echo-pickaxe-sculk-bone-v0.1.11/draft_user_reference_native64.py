"""Four-state native64 visual draft rebuilt from the user's selected approved reference."""
import hashlib
import importlib.util
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
SRC = Path(__file__).resolve().parent
VAL = ROOT / 'artwork/validation/v0.1.11/draft'
APPROVED = ROOT / 'artwork/source/approved-reference-oct03-64'
APPROVED_BUILDER = APPROVED / 'build_approved64_variants.py'
REF_PATH = SRC / 'user-selected-reference.png'
REF_SHA = '451476DBE5AB5AF151BF6A829A9B09EC8E7873B7F6638CAAA7DBC95CE4C71ACF'
NORMALIZED = APPROVED / 'approved-reference-normalized64.png'
COMMON = APPROVED / 'common64-unupgraded.png'
BASELINE_JAR = ROOT / 'jaysay-echo-tools-0.1.10.jar'
BASELINE_SHA = '24E7807050FDB26C2A1C21F6854E9F391F9DAF42E86DBA8AB05A59D0546D20C0'
STATES = [(1, '延展I'), (2, '延展II'), (3, '延展III'), (4, '调谐I / res0'),
          (8, '分频I / res0'), (16, '分频II / res0'), (24, '分频III / res0'),
          (32, '仅共振I'), (64, '仅共振II'), (95, '全满级')]


def sha(data):
    return hashlib.sha256(data).hexdigest().upper()


def load_builder():
    spec = importlib.util.spec_from_file_location('approved64_v011_draft', APPROVED_BUILDER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def get_font(size):
    for path in (r'C:\Windows\Fonts\msyh.ttc', r'C:\Windows\Fonts\arial.ttf'):
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def composite(image, bg):
    tile = Image.new('RGBA', image.size, bg + (255,))
    tile.alpha_composite(image)
    return tile.convert('RGB')


def old_hook_shape(old_ordinary_upgrade):
    # Alpha only: retain the previously established curved plain-hook silhouette.
    return {(x, y) for y in range(13, 27) for x in range(8, 32)
            if old_ordinary_upgrade.getpixel((x, y))[3]}


def active_component_pixels(tiers, levels):
    active=set()
    for name,level in levels.items():
        for mask in tiers[name][:level]:
            active.update((i%64,i//64) for i,value in enumerate(mask.getdata()) if value)
    return active


def sculk_underlay_without_bone(common):
    """Remove only the bare right-blade bone from the common tier underlay."""
    result = common.copy()
    mask = set()
    for y in range(20, 38):
        for x in range(54, 61):
            r, g, b, a = common.getpixel((x, y))
            # Warm ivory/stone pixels only; cyan and dark facets are excluded.
            if a and r > 140 and g > 135 and b > 125 and r >= g - 12 and g >= b - 12:
                mask.add((x, y))
    for x, y in mask:
        sx, sy = 20 + ((x - 54) % 18), 30 + ((y - 20) % 17)
        sample = common.getpixel((sx, sy))
        if sample[3] and not (sample[0] > 140 and sample[1] > 135 and sample[2] > 125):
            result.putpixel((x, y), sample)
        else:
            result.putpixel((x, y), (7, 47, 62, 255))
    return result, mask


def color_res0_hook(sprite, common, old_shape, protected=()):
    result = sprite.copy()
    # Repaint the hook interior from approved native shaft grain; old 32px
    # contributes alpha only, never RGB, luminance, or material classes.
    for x, y in old_shape:
        if (x, y) in protected:
            continue
        sx, sy = 20 + ((x - 8) % 18), 30 + ((y - 13) % 17)
        sample = common.getpixel((sx, sy))
        if not sample[3]:
            neighbors = [(xx, yy) for yy in range(max(30, sy-2), min(47, sy+3))
                         for xx in range(max(20, sx-2), min(38, sx+3))
                         if common.getpixel((xx, yy))[3]]
            if neighbors: sample = common.getpixel(neighbors[0])
        result.putpixel((x, y), (sample[0], sample[1], sample[2], 255))
    # Tapered bone edge: a 2-texel irregular bevel, with warm shadow facets.
    # The old source contributes silhouette only; no old RGB/material is read.
    bone = {
        (17,17):(205,199,184),(16,18):(239,232,214),(15,18):(196,191,178),
        (16,19):(246,240,222),(15,19):(218,212,195),(14,19):(188,184,172),
        (15,20):(239,233,216),(14,20):(205,200,186),(13,20):(180,178,168),
        (14,21):(246,240,222),(13,21):(218,212,195),(12,21):(188,184,172),
        (13,22):(239,233,216),(12,22):(205,200,186),(11,22):(180,178,168),
        (12,23):(246,240,222),(11,23):(218,212,195),(10,23):(188,184,172),
        (11,24):(239,233,216),(10,24):(205,200,186),(9,24):(180,178,168),
    }
    for p, rgb in bone.items():
        if p not in protected and result.getpixel(p)[3]:
            result.putpixel(p, (*rgb, 255))
    # A fine branching sculk seam connects blade and head without a broad cyan patch.
    for p, rgb in { (13,16):(29,144,158), (12,17):(12,82,100),
                    (11,18):(24,134,149), (10,19):(10,77,94),
                    (10,20):(18,101,118), (10,21):(26,144,158),
                    (10,22):(12,82,100), (10,23):(20,122,139),
                    (14,15):(13,87,105), (15,15):(38,158,171),
                    (16,15):(12,77,95), (17,15):(18,107,124) }.items():
        if p not in protected and result.getpixel(p)[3]: result.putpixel(p, (*rgb, 255))
    # These two legacy interior pixels are detached from the restored curved head.
    for p in ((30,26),(31,26)):
        if p not in protected: result.putpixel(p,(0,0,0,0))
    return result


def refine_bare_head(sprite, common, active):
    result = sprite.copy()
    # Break up the coarse bare cap with native shaft grain (1:1 source texels),
    # rather than reusing the broad cyan head plane. Active modules stay exact.
    for y in range(7, 18):
        for x in range(20, 35):
            p = (x, y)
            if p in active or not result.getpixel(p)[3]:
                continue
            sx = 20 + ((x - 20) % 18)
            sy = 30 + ((y - 7) % 17)
            sample = common.getpixel((sx, sy))
            if sample[3]: result.putpixel(p, sample)
    # Two short, offset fracture branches tie the dark facets into the neck.
    for p, rgb in {(27,12):(20,121,139),(28,11):(42,177,185),
                   (29,11):(11,78,95),(30,12):(17,112,129),
                   (31,13):(9,65,81)}.items():
        if result.getpixel(p)[3] and p not in active:
            result.putpixel(p, (*rgb,255))
    return result


def refine_bare_right_tip(sprite, common):
    result = sprite.copy()
    # Repaint only the exposed, unupgraded shoulder and natural tip with native
    # dark facets and a narrow branching cyan seam; the purple module is untouched.
    for y in range(22, 32):
        for x in range(51, 59):
            if not result.getpixel((x,y))[3]:
                continue
            sx, sy = 20 + ((x - 51) % 18), 30 + ((y - 22) % 17)
            sample = common.getpixel((sx, sy))
            if sample[3]: result.putpixel((x,y), sample)
    for p,rgb in {(52,23):(8,56,73),(53,22):(18,102,119),
                   (54,22):(43,174,183),(55,23):(14,90,108),
                   (56,24):(19,128,143),(57,25):(9,68,85),
                   (57,26):(35,157,169)}.items():
        if result.getpixel(p)[3]: result.putpixel(p,(*rgb,255))
    bone = {
        (56,22):(219,213,198),(57,22):(239,233,218),
        (56,23):(199,195,183),(57,23):(230,224,209),
        (57,28):(227,221,205),(58,28):(193,190,178),
        (57,29):(243,237,220),(58,29):(210,205,191),
        (57,30):(228,222,207),(58,30):(185,184,173),
        (57,31):(238,232,215),(58,31):(207,202,188),
        (57,32):(223,217,201),(58,32):(184,183,172),
        (56,33):(234,228,211),(57,33):(197,194,182),
        (56,34):(222,216,200),(57,34):(185,183,172),
    }
    for p,rgb in bone.items():
        if result.getpixel(p)[3]: result.putpixel(p,(*rgb,255))
    return result


def refine_extension_zero_pommel(sprite, common):
    result=sprite.copy()
    # Trim the broad old terminal and redraw a compact round cap plus short
    # connector. This applies only while extension is inactive.
    for y in range(46,64):
        for x in range(3,20):
            if result.getpixel((x,y))[3]: result.putpixel((x,y),(0,0,0,0))
    disk={46:(15,17),47:(13,18),48:(10,17),49:(8,16),50:(7,15),
          51:(7,15),52:(8,14),53:(9,13),54:(10,12)}
    for y,(xmin,xmax) in disk.items():
        for x in range(xmin,xmax+1):
            if not result.getpixel((x,y))[3]: result.putpixel((x,y),(5,15,23,255))
            sx=20+((x-6)%18); sy=30+((y-47)%17)
            sample=common.getpixel((sx,sy))
            if sample[3]: result.putpixel((x,y),sample)
    # Restore the two native shaft texels removed by trimming the old terminal,
    # so the circular cap joins the handle without a transparent notch.
    for p in ((18,46),(19,46)):
        sample=common.getpixel(p)
        if sample[3]: result.putpixel(p,sample)
    core={(9,49):(2,47,61),(10,49):(4,97,111),(11,49):(3,48,63),(12,49):(2,54,68),
          (8,50):(3,84,101),(9,50):(7,181,192),(10,50):(2,103,119),(11,50):(4,76,92),(12,50):(3,56,70),
          (8,51):(2,54,69),(9,51):(1,123,139),(10,51):(3,72,86),(11,51):(2,47,61),(12,51):(8,78,91),
          (9,52):(5,84,99),(10,52):(2,48,63),(11,52):(4,65,79)}
    for p,rgb in core.items():
        if result.getpixel(p)[3]: result.putpixel(p,(*rgb,255))
    clasps={(9,47):(218,212,196),(10,47):(242,236,220),
            (16,49):(201,197,184),(17,50):(239,233,216),
            (8,52):(220,214,198),(9,53):(243,237,220)}
    for p,rgb in clasps.items():
        if result.getpixel(p)[3]: result.putpixel(p,(*rgb,255))
    return result


def render_grid(states, path, size):
    margin, label_h, gap = 12, 28, 10
    cell_w, cell_h = max(size + 16, 74), size + label_h + gap
    board = Image.new('RGB', (margin * 2 + len(states) * cell_w,
                              margin * 2 + 2 * cell_h), (240, 243, 246))
    draw = ImageDraw.Draw(board)
    font = get_font(14)
    for row, bg in enumerate(((255, 255, 255), (24, 30, 38))):
        y = margin + row * cell_h
        draw.text((margin, y + 2), '白底' if row == 0 else '暗底', font=font, fill=(25, 30, 36))
        for col, (label, sprite) in enumerate(states):
            x = margin + col * cell_w
            short_label = {1:'延展I',2:'延展II',3:'延展III',4:'调谐I',8:'分频I',
                           16:'分频II',24:'分频III',32:'共振I',64:'共振II',95:'全满级'}
            shown_label = short_label.get(STATES[col][0], label) if size <= 32 else label
            draw.text((x + 2, y + 2), shown_label, font=font, fill=(25, 30, 36))
            shown = sprite.resize((size, size), Image.Resampling.NEAREST)
            board.paste(composite(shown, bg), (x, y + label_h))
    board.save(path)


def render_zoom(states, path):
    crops = [((7, 5, 39, 31), '左尖 / 红强化替代骨刃'),
             ((43, 8, 64, 44), '右尖 / 紫强化替代骨刃'),
             ((3, 43, 22, 63), '柄末 / ext骨扣')]
    scale, margin, label_h = 8, 10, 26
    block_w = max((x1-x0) for (x0,y0,x1,y1),_ in crops)*scale
    strip_heights = [(y1-y0)*scale + 18 for (x0,y0,x1,y1),_ in crops]
    block_h = label_h + sum(strip_heights)
    cell_w, gap = block_w + 12, 10
    board = Image.new('RGB', (margin*2 + cell_w*len(states), margin*2 + 2*(block_h+gap)), (240,243,246))
    draw = ImageDraw.Draw(board)
    font = get_font(13)
    for row,bg in enumerate(((255,255,255),(24,30,38))):
        y0 = margin + row*(block_h+gap)
        for col,(state_label,sprite) in enumerate(states):
            x0 = margin + col*cell_w
            draw.text((x0+2,y0+2), state_label + (' 白' if row==0 else ' 暗'), font=font, fill=(25,30,36))
            yy = y0 + label_h
            for strip,((cx0,cy0,cx1,cy1),crop_label) in enumerate(crops):
                crop = sprite.crop((cx0,cy0,cx1,cy1)).resize(((cx1-cx0)*scale,(cy1-cy0)*scale), Image.Resampling.NEAREST)
                draw.text((x0+2,yy), crop_label, font=font, fill=(25,30,36))
                board.paste(composite(crop,bg),(x0,yy+15))
                yy += strip_heights[strip]
    board.save(path)


def main():
    VAL.mkdir(parents=True, exist_ok=True)
    ref_hash = sha(REF_PATH.read_bytes())
    if ref_hash != REF_SHA:
        raise RuntimeError(f'user-selected reference SHA mismatch: {ref_hash}')
    baseline_data = BASELINE_JAR.read_bytes()
    if sha(baseline_data) != BASELINE_SHA:
        raise RuntimeError('Pinned 0.1.10 outline-source JAR SHA mismatch')
    builder = load_builder()
    normalized = Image.open(NORMALIZED).convert('RGBA')
    common = Image.open(COMMON).convert('RGBA')
    tiers, component_masks, component_regions = builder.feature_masks(normalized)
    if normalized.size != (64,64) or common.size != (64,64):
        raise ValueError('Approved reference/common underlay must be native64.')
    previews = []
    reports = {}
    with __import__('zipfile').ZipFile(BASELINE_JAR) as archive:
        old_shape_source = Image.open(__import__('io').BytesIO(
            archive.read('assets/echopickaxe/textures/item/echo_pickaxe_v004.png'))).convert('RGBA')
        hook_shape = old_hook_shape(old_shape_source)
        for index,label in STATES:
            levels = dict(zip(builder.COMPONENTS, builder.levels_for(index)))
            state_underlay = common
            if levels['frequency'] > 0:
                state_underlay, removed_bone_mask = sculk_underlay_without_bone(common)
            else:
                removed_bone_mask = set()
            sprite = builder.state_sprite(normalized, state_underlay, tiers, levels)
            active = active_component_pixels(tiers, levels)
            if levels['resonance'] == 0:
                sprite = color_res0_hook(sprite, common, hook_shape, active)
                sprite = refine_bare_head(sprite, common, active)
            if levels['frequency'] == 0:
                sprite = refine_bare_right_tip(sprite, common)
            if levels['extension'] == 0:
                sprite = refine_extension_zero_pommel(sprite, common)
            if index == 95 and ImageChops.difference(sprite, normalized).getbbox():
                raise AssertionError('fullmax 095 must exactly match approved normalized reference')
            sprite.save(VAL / f'v{index:03d}-approved-reference-native64-draft.png')
            previews.append((label, sprite))
            reports[str(index)] = {'levels': levels, 'opaqueTexels': sum(1 for a in sprite.getchannel('A').getdata() if a),
                                   'matchesApprovedFullmax': index == 95,
                                   'res0HookUsesPinned010AlphaOnly': levels['resonance'] == 0,
                                   'rightBareBoneRemovedForFrequencyTier': sorted([list(p) for p in removed_bone_mask]),
                                   'activeTierTexels': {name: sum(1 for tier in tiers[name][:levels[name]]
                                                                  for value in tier.getdata() if value)
                                                        for name in builder.COMPONENTS}}
    render_grid(previews, VAL / 'v0.1.11-reference-tier-samples-native4x-white-dark.png', 256)
    render_grid(previews, VAL / 'v0.1.11-reference-tier-samples-32px-white-dark.png', 32)
    render_grid(previews, VAL / 'v0.1.11-reference-tier-samples-16px-white-dark.png', 16)
    render_zoom(previews, VAL / 'v0.1.11-reference-tier-samples-tips-pommel-8x-white-dark.png')
    manifest = {'status': 'reference-rebuild-visual-draft-only-awaiting-root-review',
                'baseReference': str(REF_PATH.relative_to(ROOT)).replace('\\','/'), 'baseReferenceSha256': ref_hash,
                'approvedNormalized64': str(NORMALIZED.relative_to(ROOT)).replace('\\','/'),
                'approvedNormalized64Sha256': sha(NORMALIZED.read_bytes()),
                'common64': str(COMMON.relative_to(ROOT)).replace('\\','/'), 'common64Sha256': sha(COMMON.read_bytes()),
                'approvedComponentBuilder': str(APPROVED_BUILDER.relative_to(ROOT)).replace('\\','/'),
                'hookOutlineSource': BASELINE_JAR.name, 'hookOutlineSourceSha256': BASELINE_SHA,
                'hookOutlineContract': 'Only v004 alpha coordinates are used to restore res0 curved-hook silhouette; old RGB is ignored. Res-positive red left component remains approved reference pixels.',
                'stateSprites': reports, 'fullmax095BytePixelExactToNormalized64': True,
                'scope': 'visual draft only; no candidate, src, build, or install changes',
                'previews': ['artwork/validation/v0.1.11/draft/v0.1.11-reference-tier-samples-native4x-white-dark.png',
                             'artwork/validation/v0.1.11/draft/v0.1.11-reference-tier-samples-32px-white-dark.png',
                             'artwork/validation/v0.1.11/draft/v0.1.11-reference-tier-samples-16px-white-dark.png',
                             'artwork/validation/v0.1.11/draft/v0.1.11-reference-tier-samples-tips-pommel-8x-white-dark.png']}
    (VAL / 'v0.1.11-reference-draft.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('PASS reference rebuild draft; no generated candidate or production resources changed.')
    print('user-selected reference SHA:', ref_hash)
    print('approved fullmax exact:', sha(NORMALIZED.read_bytes()))
    print('Draft:', VAL)


if __name__ == '__main__':
    main()
