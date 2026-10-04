"""Root reference correction after the user stopped the facet redraw.

I only adds a small native ruby tip patch to the released 0.1.14 face.
II copies the reference ruby contour at the reference's native coordinates.
No recoloring, warping, new highlights or individual row translations.
"""
from pathlib import Path
import copy, hashlib, json
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SOURCE = ROOT / 'artwork/source/root-tier-v3/root-pixel-states.json'
MASTER = ROOT / 'artwork/source/approved-fullmax-v0.1.12/candidates/approved-fullmax-128.png'
EXPECTED = 'D412F62BD8C4AB5909E1EF36F22AFD1DDA79C920A7059576AA43B4A0EBEC31E9'
raw = SOURCE.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper() == EXPECTED
old = json.loads(raw)
data = copy.deepcopy(old)
base = old['states']['ordinary128']['pixelsRGBA']
master = Image.open(MASTER).convert('RGBA')

# Only the front portion of the existing ruby I tip, from the released II palette.
tip_rows = {10:(39,44),11:(37,48),12:(36,48),13:(35,38)}
tip_patch=[]
for y,(lo,hi) in tip_rows.items():
    for x in range(lo,hi+1):
        c=old['states']['resonance2']['pixelsRGBA'][y][x]
        before=old['states']['resonance1']['pixelsRGBA'][y][x]
        if c[3] and c!=before:
            data['states']['resonance1']['pixelsRGBA'][y][x]=c[:]
            tip_patch.append([x,y])
# Complete the lower blade's upper arc with the native dark-divider band. It is
# one continuous border; the upper ruby tier stays inactive. The face beneath
# this divider is copied intact from the released I, not repainted.
divider=[(30,33,15),(34,38,14),(39,43,14),(44,55,12),(56,58,13),
         (59,61,15),(62,64,17),(65,66,19),(67,68,22),(69,71,26),(72,73,29)]
arc_patch=[]
for lo,hi,line in divider:
    for sx in range(lo,hi+1):
        for sy in range(line-2,line+1):
            x,y=sx+5,sy-1
            c=old['states']['resonance2']['pixelsRGBA'][y][x]
            before=data['states']['resonance1']['pixelsRGBA'][y][x]
            if c[3] and c[0]>max(c[1],c[2])*1.05 and c!=before:
                data['states']['resonance1']['pixelsRGBA'][y][x]=c[:]
                arc_patch.append([x,y])
# Close the notch between the added front cap and the divider's raised middle.
# These texels are still sampled from the released reference ruby, in place.
for y,lo,hi in [(9,43,49),(10,43,49)]:
    for x in range(lo,hi+1):
        c=old['states']['resonance2']['pixelsRGBA'][y][x]
        if c[3] and c[0]>max(c[1],c[2])*1.05 and c!=data['states']['resonance1']['pixelsRGBA'][y][x]:
            data['states']['resonance1']['pixelsRGBA'][y][x]=c[:]
            arc_patch.append([x,y])

# Complete native contour runs include pale facets, divider and backing; these
# are geometry boundaries, not a red-color threshold that clips white highlights.
# The old component was translated (+5,-1), changing its relation to the shaft.
rows={4:[(53,64)],5:[(53,64)],6:[(44,66)],7:[(44,66)],8:[(39,69)],
      9:[(39,71)],10:[(36,73)],11:[(34,73)],12:[(34,73)],13:[(32,75)],
      14:[(30,63),(72,75)],15:[(30,64),(72,75)],16:[(30,33),(44,65),(74,75)],
      17:[(30,31),(49,65),(74,76)],18:[(30,31),(49,65),(75,76)],
      19:[(52,66),(75,76)],20:[(52,66)],21:[(55,66)],22:[(58,68)],
      23:[(58,68)],24:[(60,68)],25:[(60,68)],26:[(61,71)],27:[(63,73)],
      28:[(63,73)],29:[(63,73)],30:[(63,73)],31:[(65,73)],32:[(65,74)],
      33:[(65,73)],34:[(67,75)],35:[(67,75)],36:[(67,71)],
      37:[(69,71)],38:[(69,71)],39:[(69,70)],40:[(69,70)]}
prior=old['states']['resonance2']['pixelsRGBA']
pix=copy.deepcopy(base)
for y in range(128):
    for x in range(128):
        if prior[y][x]!=base[y][x]: pix[y][x]=[0,0,0,0]
# The released deletion stencil belonged to the shifted blade. Keep the shaft
# joint, then use the reference's own sculk backing under the native ruby.
# Other modules retain their exact ordinary pixels and own their own boundaries.
protected=set()
for name in ['split1','split2','split3','tuning1','extension1','extension2','extension3']:
    other=old['states'][name]['pixelsRGBA']
    protected|={(x,y) for y in range(128) for x in range(128) if other[y][x]!=base[y][x]}
for y in range(11,35):
    for x in range(77,85): pix[y][x]=base[y][x][:]
joint_rows={**{y:(74,81) for y in range(11,14)},
            **{y:(64,81) for y in range(14,16)},
            **{y:(66,81) for y in range(16,19)},
            **{y:(67,81) for y in range(19,22)},
            **{y:(69,81) for y in range(22,26)},
            **{y:(72,81) for y in range(26,28)},
            **{y:(74,81) for y in range(28,32)},
            **{y:(75,81) for y in range(32,36)}}
joint_points=[]
for y,(lo,hi) in joint_rows.items():
    for x in range(lo,hi+1):
        if (x,y) in protected: continue
        c=list(master.getpixel((x,y)))
        pix[y][x]=c if c[3] else [0,0,0,0]
        joint_points.append([x,y])
reference_points=[]
for y,runs in rows.items():
    for lo,hi in runs:
        for x in range(lo,hi+1):
            c=list(master.getpixel((x,y)))
            pix[y][x]=c if c[3] else [0,0,0,0]
            reference_points.append([x,y])
data['states']['resonance2']['pixelsRGBA']=pix
data['componentBounds128']['resonance']=[28,0,85,43]

# Preserve the original I glow outside the small added tip. II keeps the same
# amplitude/timing and highlight-selection rule, in original native coordinates.
for name in ['resonance1','resonance2']:
    pix=data['states'][name]['pixelsRGBA']
    points=copy.deepcopy(old['states'][name]['glowPointEffects']) if name=='resonance1' else []
    existing={(p['x'],p['y']) for p in points}
    locations=tip_patch+arc_patch if name=='resonance1' else reference_points
    for x,y in locations:
        if (x,y) in existing: continue
        r,g,b,a=pix[y][x]
        if a and r>=140 and r>g*1.2:
            points.append({'x':x,'y':y,'phaseRadians':round((x+y)*.17,6),
                           'amplitude':.035 if name=='resonance1' else .05,
                           'stable':False,'group':'ruby-cutting-facet'})
    if name=='resonance2':
        used={(p['x'],p['y']) for p in points}
        for x,y in joint_points:
            r,g,b,a=pix[y][x]
            if ((x,y) not in used and pix[y][x]!=base[y][x]
                    and a and g>=90 and b>=110 and r<g*.6):
                points.append({'x':x,'y':y,'phaseRadians':round((x+y)*.17,6),
                               'amplitude':.03,'stable':False,'group':'sculk-joint-highlight'})
    data['states'][name]['glowPointEffects']=sorted(points,key=lambda p:(p['y'],p['x']))

maximum=copy.deepcopy(base)
for name in ['resonance2','split3','tuning1','extension3']:
    p=data['states'][name]['pixelsRGBA']
    for y in range(128):
        for x in range(128):
            if p[y][x]!=base[y][x]: maximum[y][x]=p[y][x][:]
data['states']['all_max']['pixelsRGBA']=maximum

audit={'version':'0.1.15','baselineRootPixelSha256':EXPECTED,
       'tipPatchCoordinates':tip_patch,'upperArcPatchCoordinates':arc_patch,
       'referenceRubyCoordinates':reference_points,
       'referenceJointCoordinates':joint_points,
       'rubyIIReferenceTranslation':[0,0],'rubyIIReferenceRgbaExact':True,'states':{}}
for name,state in data['states'].items():
    before=old['states'][name]
    changes=[[x,y] for y in range(128) for x in range(128)
             if state['pixelsRGBA'][y][x]!=before['pixelsRGBA'][y][x]]
    if name not in ['resonance1','resonance2','all_max']:
        assert state==before,name+' changed unexpectedly'
    audit['states'][name]={'changedPixels':len(changes),'wholeStateExact':state==before,
                           'coordinates':changes}
for x,y in reference_points:
    c=list(master.getpixel((x,y)))
    assert data['states']['resonance2']['pixelsRGBA'][y][x]==(c if c[3] else [0,0,0,0])
data['version']='0.1.15'
data['status']='root-reference-correction-for-review'
data['notes']='User stopped the facet redraw. Frequency I/II restored exactly. Ruby I keeps released face plus same-material tip and completed dark-divider upper arc. Ruby II copies native reference contour at original coordinates. Common ordinary body unchanged.'
output=OUT/'root-pixel-states.json'
output.write_text(json.dumps(data,separators=(',',':'))+'\n',encoding='utf-8')
audit['rootPixelSha256']=hashlib.sha256(output.read_bytes()).hexdigest().upper()
(OUT/'polish-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(audit['rootPixelSha256'])
print({name:row['changedPixels'] for name,row in audit['states'].items()})
