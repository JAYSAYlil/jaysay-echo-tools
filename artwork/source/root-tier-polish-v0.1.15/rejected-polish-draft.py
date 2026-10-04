"""Root-authored material polish; same silhouettes and tier boundaries as 0.1.14.

These native-coordinate facet paths are the artwork, not an automatic restyle.
Only resonance1, split1 and split2 are replaced. Everything else is copied intact.
"""
from pathlib import Path
import copy, hashlib, json, math
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SOURCE = ROOT / 'artwork/source/root-tier-v3/root-pixel-states.json'
EXPECTED = 'D412F62BD8C4AB5909E1EF36F22AFD1DDA79C920A7059576AA43B4A0EBEC31E9'
raw = SOURCE.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper() == EXPECTED
old = json.loads(raw)
data = copy.deepcopy(old)
base = old['states']['ordinary128']['pixelsRGBA']
TARGETS = ('resonance1', 'split1', 'split2')

def painter(name, background):
    canvas = Image.new('RGBA', (128, 128), background)
    return canvas, ImageDraw.Draw(canvas)

def apply_owned(name, canvas):
    original = old['states'][name]['pixelsRGBA']
    result = data['states'][name]['pixelsRGBA']
    for y in range(128):
        for x in range(128):
            # Same occupied art-owned texels. Preserve alpha, deletions, inactive
            # base and the existing part-to-shaft join without extending the tip.
            if original[y][x] != base[y][x] and original[y][x][3]:
                result[y][x] = list(canvas.getpixel((x,y)))

# Ruby I: a thin dark divider, one crimson face, a continuous narrow cutting
# bevel. A few short pale glints replace the broad white flecks. No upper tier.
ruby = {
    'outline': (45, 1, 12, 255), 'seam': (72, 1, 18, 255),
    'shadow': (111, 2, 27, 255), 'face': (174, 5, 41, 255),
    'red': (222, 12, 50, 255), 'light': (254, 57, 88, 255),
    'bevel': (255, 113, 139, 255), 'glint': (255, 192, 198, 255),
}
canvas, pen = painter('resonance1', ruby['outline'])
pen.polygon([(35,14),(39,13),(49,11),(56,11),(63,13),(67,16),
             (71,20),(74,25),(77,30),(79,34),(76,39),(74,40),
             (71,33),(68,27),(64,23),(60,20),(54,18),(47,17),(35,17)],
            fill=ruby['shadow'])
pen.polygon([(36,15),(43,14),(50,12),(56,13),(62,15),(66,18),
             (70,22),(73,27),(75,32),(77,35),(75,38),(72,32),
             (69,27),(66,23),(61,20),(56,18),(49,17),(41,16)],
            fill=ruby['face'])
pen.polygon([(40,14),(49,13),(55,14),(61,16),(65,19),(69,24),
             (73,30),(75,35),(74,36),(71,30),(68,26),(64,22),
             (59,19),(53,17),(46,15)], fill=ruby['red'])
pen.line([(35,15),(40,14),(47,14),(53,15),(59,17),(64,20),
          (67,23),(69,26),(71,29),(73,33),(75,36)],
         fill=ruby['light'], width=2)
pen.line([(35,15),(40,14),(47,14),(53,15),(59,17),(64,20),
          (67,23),(69,26),(71,29),(73,33),(75,36)],
         fill=ruby['bevel'], width=1)
pen.line([(44,14),(47,14)], fill=ruby['glint'], width=1)
pen.line([(62,19),(64,20)], fill=ruby['glint'], width=1)
pen.line([(72,31),(73,33)], fill=ruby['glint'], width=1)
pen.line([(49,11),(56,11),(63,13),(67,16),(71,20)],
         fill=ruby['seam'], width=1)
apply_owned('resonance1', canvas)

# Amethyst I is the same ivory bevel, shaped by one continuous leading highlight.
# II expands into a complete crystal face; the outline is still the ordinary arm.
# The extra inner hanging blade and the approved level-III art are untouched.
purple = {
    'outline': (25, 4, 43, 255), 'shadow': (47, 9, 76, 255),
    'deep': (66, 17, 106, 255), 'facet': (104, 30, 156, 255),
    'face': (144, 43, 202, 255), 'light': (184, 75, 231, 255),
    'bevel': (213, 128, 244, 255), 'glint': (244, 192, 252, 255),
}
edge = [(98,44),(99,45),(100,46),(101,47),(102,48),(103,49),
        (104,50),(105,51),(106,52),(107,53),(109,54),(110,55),
        (111,56),(111,57),(112,58),(113,59),(114,60),(115,61),
        (116,62),(117,63),(117,64),(117,65),(117,66),(117,67)]
canvas, pen = painter('split1', purple['shadow'])
pen.line([(x+1,y) for x,y in edge], fill=purple['face'], width=2)
pen.line(edge, fill=purple['bevel'], width=1)
pen.line([(x-1,y) for x,y in edge], fill=purple['facet'], width=1)
pen.line([(100,46),(102,48)], fill=purple['glint'], width=1)
pen.line([(109,54),(110,55)], fill=purple['glint'], width=1)
pen.line([(114,60),(115,61)], fill=purple['glint'], width=1)
pen.point((117,67), fill=purple['light'])
apply_owned('split1', canvas)

canvas, pen = painter('split2', purple['outline'])
pen.polygon([(98,42),(105,42),(110,44),(113,47),(116,50),(118,54),
             (118,57),(119,59),(119,67),(119,69),(117,69),(115,66),
             (114,62),(111,59),(108,55),(105,53),(102,50),(99,47)],
            fill=purple['shadow'])
pen.polygon([(101,43),(106,43),(111,46),(114,49),(116,53),(116,56),
             (118,59),(118,64),(118,68),(117,68),(116,63),(113,60),
             (110,56),(107,53),(104,50),(101,47)], fill=purple['facet'])
pen.polygon([(101,44),(105,44),(110,47),(112,50),(114,54),(115,57),
             (117,60),(118,64),(118,67),(117,66),(116,62),(113,59),
             (110,55),(107,52),(104,49),(102,46)], fill=purple['face'])
# A long narrow facet aligned to the curve, rather than row-wise source sampling.
pen.line([(103,44),(106,46),(109,49),(111,52),(113,56),
          (115,59),(117,63),(118,66)], fill=purple['light'], width=2)
pen.line(edge, fill=purple['bevel'], width=1)
pen.line([(101,46),(103,48)], fill=purple['glint'], width=1)
pen.line([(109,54),(110,55)], fill=purple['glint'], width=1)
pen.line([(114,60),(115,61)], fill=purple['glint'], width=1)
# Crisp cap and back facet terminate at the existing sculk joint.
pen.line([(101,43),(105,43),(109,45)], fill=purple['light'], width=1)
pen.line([(107,44),(111,47),(114,51),(116,55),(118,59)],
         fill=purple['deep'], width=1)
# Three inclined crystal facets share the same long bevel. Their sizes shrink
# towards the tip, giving a cut-stone surface without transverse stripe noise.
pen.polygon([(104,45),(107,46),(109,49),(107,48)], fill=purple['bevel'])
pen.polygon([(107,49),(110,51),(111,53),(109,52)], fill=purple['light'])
pen.polygon([(111,54),(113,55),(115,58),(113,57)], fill=purple['bevel'])
pen.polygon([(115,60),(116,60),(117,63),(116,62)], fill=purple['light'])
pen.line([(109,48),(111,51)], fill=purple['facet'], width=1)
pen.line([(113,54),(115,57)], fill=purple['facet'], width=1)
apply_owned('split2', canvas)

# Root-prescribed subtle glow follows the continuous new bevel. Only these three
# stages get updated FX; all higher stages and other parts retain their exact FX.
for name in TARGETS:
    pix = data['states'][name]['pixelsRGBA']
    points = []
    for y in range(128):
        for x in range(128):
            r,g,b,a = pix[y][x]
            if not a or pix[y][x] == base[y][x]:
                continue
            if name == 'resonance1':
                lit = r >= 210 and g >= 45 and r > g*1.2
                phase,amp,group = (x+y)*.17,.035,'ruby-cutting-facet'
            else:
                lit = b >= 200 and r >= 140
                phase,amp,group = (y-42)*.17,(.035 if name == 'split1' else .045),'amethyst-cutting-facet'
            if lit:
                points.append({'x':x,'y':y,'phaseRadians':round(phase,6),
                               'amplitude':amp,'stable':False,'group':group})
    data['states'][name]['glowPointEffects'] = points

audit = {'baselineRootPixelSha256':EXPECTED,'version':'0.1.15','states':{}}
for name,state in data['states'].items():
    before = old['states'][name]
    assert all(state['pixelsRGBA'][y][x][3] == before['pixelsRGBA'][y][x][3]
               for y in range(128) for x in range(128)), name+' alpha changed'
    diff = [[x,y] for y in range(128) for x in range(128)
            if state['pixelsRGBA'][y][x] != before['pixelsRGBA'][y][x]]
    if name not in TARGETS:
        assert state == before, name+' unexpectedly changed'
    audit['states'][name]={'changedPixels':len(diff),'alphaExact':True,
                           'wholeStateExact':state == before,'coordinates':diff}
data['version']='0.1.15'
data['status']='root-material-polish-for-review'
data['notes']='Root polish of resonance I and frequency I/II only. Same alpha and tier geometry. Continuous crystal bevel and coherent facets. Other states/FX unchanged.'
output=OUT/'root-pixel-states.json'
output.write_text(json.dumps(data,separators=(',',':'))+'\n',encoding='utf-8')
audit['rootPixelSha256']=hashlib.sha256(output.read_bytes()).hexdigest().upper()
(OUT/'polish-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(audit['rootPixelSha256'])
print({name:row['changedPixels'] for name,row in audit['states'].items()})
