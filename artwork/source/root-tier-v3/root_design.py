"""Root-authored native pixel artwork. Technical executor must not alter its pixels."""
from pathlib import Path
import json, math, hashlib
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
ordinary = Image.open(ROOT/'src/main/resources/assets/echopickaxe/textures/item/echo_pickaxe.png').convert('RGBA').resize((128,128),Image.Resampling.NEAREST)
master_path = ROOT/'artwork/source/approved-fullmax-v0.1.12/candidates/approved-fullmax-128.png'
master = Image.open(master_path).convert('RGBA')
base = [[list(ordinary.getpixel((x,y))) if ordinary.getpixel((x,y))[3] else [0,0,0,0] for x in range(128)] for y in range(128)]
def sample(x,y):
    c=list(master.getpixel((x,y)))
    return c if c[3] else [0,0,0,0]
def copybase(): return [[c[:] for c in row] for row in base]
def rect(x0,y0,x1,y1): return {(x,y) for y in range(y0,y1+1) for x in range(x0,x1+1)}
bone_palette={(198,187,154),(242,228,196),(251,245,225)}
regions={'resonance':(17,5,35,19),'split':(48,21,59,33),'tuning':(39,13,47,20),'extension':(5,49,15,58)}
bones={}
for mod,(x0,y0,x1,y1) in regions.items():
    bones[mod]={(x,y) for x,y in rect(x0*2,y0*2,x1*2+1,y1*2+1) if tuple(base[y][x][:3]) in bone_palette}
states={}; owners={}; fx={}
def save(name,mod,pixels,owner):
    states[name]={'module':mod,'pixelsRGBA':pixels,'glowPointEffects':[]}
    owners[mod]=owners.get(mod,set())|owner
def protect(mod,points):
    return points-set().union(*(v for k,v in bones.items() if k!=mod))

# Red: replace whole occupied old blade, including shadow backing. Native reference
# supplies all faces; I has one uninterrupted arch, II adds its raised back ridge.
red_owner=set()
for y in range(2,42):
    lo,hi=(33,78) if y<=12 else (33,82) if y<=19 else (45,73) if y<=25 else (57,79) if y<=32 else (67,81)
    red_owner|={(x,y) for x in range(lo,hi+1) if base[y][x][3]}
red_owner|=bones['resonance']
red_owner|={(64,33),(64,34),(64,35),(65,33),(65,34),(65,35),(66,38),(66,39)}
red_rows={4:[(53,64)],5:[(53,64)],6:[(44,66)],7:[(44,66)],8:[(39,69)],9:[(39,71)],10:[(36,73)],11:[(34,73)],12:[(34,73)],13:[(32,75)],14:[(30,63),(72,75)],15:[(30,64),(72,75)],16:[(30,33),(44,65),(74,75)],17:[(30,31),(49,65),(74,76)],18:[(30,31),(49,65),(75,76)],19:[(52,66),(75,76)],20:[(52,66)],21:[(55,66)],22:[(58,68)],23:[(58,68)],24:[(60,68)],25:[(60,68)],26:[(61,71)],27:[(63,73)],28:[(63,73)],29:[(63,73)],30:[(63,73)],31:[(65,73)],32:[(65,74)],33:[(65,73)],34:[(67,75)],35:[(67,75)],36:[(67,71)],37:[(69,71)],38:[(69,71)],39:[(69,70)],40:[(69,70)]}
for tier in (1,2):
    divider=[(30,33,15),(34,38,14),(39,43,14),(44,55,12),(56,58,13),(59,61,15),(62,64,17),(65,66,19),(67,68,22),(69,71,26),(72,73,29),(74,76,34)]
    def lower_face(sx,sy):
        return sy>=next((line for a,z,line in divider if a<=sx<=z),43)
    owned=red_owner if tier==2 else {(x,y) for x,y in red_owner if lower_face(x-5,y+1)}|bones['resonance']
    pix=copybase(); owner=protect('resonance',owned)
    for x,y in owner: pix[y][x]=[0,0,0,0]
    for sy,runs in red_rows.items():
        for lo,hi in runs:
            for sx in range(lo,hi+1):
                # I stops at the native dark-red divider; only the lower blade exists.
                if tier==1 and not lower_face(sx,sy): continue
                tx,ty=sx+5,sy-1
                if (tx,ty) in set().union(bones['split'],bones['tuning'],bones['extension']): continue
                pix[ty][tx]=sample(sx,sy); owner.add((tx,ty))
    save('resonance'+str(tier),'resonance',pix,owner)

# Frequency I: only the original ivory cutting edge changes to violet crystal.
violet={'d':[38,7,70,255],'s':[67,21,112,255],'m':[104,34,163,255],'v':[173,68,253,255],'l':[233,154,250,255]}
edge=[(49,22,'mvlv'),(50,23,'vlmv'),(51,23,'msvd'),(50,24,'lvvm'),(51,24,'vsmd'),(51,25,'lvvm'),(52,25,'mvls'),(53,25,'vsmd'),(53,26,'lvvm'),(54,26,'vsmd'),(54,27,'lvvm'),(55,27,'vsmd'),(55,28,'lvvm'),(55,29,'vlmv'),(56,29,'vsmd'),(56,30,'lvvm'),(57,30,'vsmd'),(57,31,'lvvm'),(58,31,'vsmd'),(58,32,'lvvm'),(58,33,'vlmd')]
pix=copybase()
# A continuous bevel, rather than alternating isolated lavender dots. All four
# shades are picked verbatim from the reference's main amethyst cutting facet.
for y in range(44,68):
    xs=sorted(x for x,by in bones['split'] if by==y)
    glint=sample(102,54) if y%2==0 else sample(107,57)
    face=sample(106,54) if y%2==0 else sample(106,55)
    shadow=sample(104,55)
    outline=sample(101,55)
    bevel=([glint,face] if len(xs)==2 else [outline,glint,face,shadow] if len(xs)==4 else [outline,glint,face,sample(102,64),face,shadow])
    for i,x in enumerate(xs):
        pix[y][x]=bevel[i][:]
save('split1','split',pix,bones['split'])
# II is the complete primary hooked amethyst blade, III adds the second lower blade.
purple_owner=protect('split',rect(95,42,127,75))
for tier in (2,3):
    pix=copybase(); owner=purple_owner.copy()
    for x,y in owner: pix[y][x]=[0,0,0,0]
    if tier==2:
        # II preserves the ordinary arm's silhouette exactly. Every occupied texel
        # is amethyst, including its backing. Only III receives the added blade.
        for y in range(42,76):
            xs=sorted(x for x in range(95,128) if base[y][x][3])
            sy=min(75,y+3)
            lo,hi=(110,117) if sy<=48 else (112,120) if sy<=53 else (113,123) if sy<=58 else (114,122) if sy<=64 else (117,123) if sy<=70 else (120,123)
            for i,x in enumerate(xs):
                sx=lo+round(i*(hi-lo)/max(1,len(xs)-1))
                c=sample(sx,sy)
                # Material projection owns every texel. Native violet shadow fills
                # sampling outside the reference facet, never old teal backing.
                r,g,b,a=c
                pix[y][x]=c if a and b>g*1.15 and r>g*1.05 else sample(107,60)
        save('split2','split',pix,owner)
        continue
    primary_rows={45:(102,106),46:(102,106),47:(94,110),48:(94,110),49:(94,110),50:(96,110),51:(96,110),52:(97,110),53:(97,110),54:(99,110),55:(99,110),56:(99,110),57:(99,110),58:(101,108),59:(101,108),60:(101,108),61:(101,108),62:(101,108),63:(101,108),64:(101,106),65:(101,106),66:(101,104),67:(99,103),68:(99,102),69:(99,102),70:(99,100)}
    for sy in range(45,76):
        lo,hi=primary_rows.get(sy,(0,-1)) if tier==2 else (94,127)
        for sx in range(lo,hi+1):
            tx,ty=sx+1,sy-3
            if tx>=128: continue
            if (tx,ty) not in owner: continue
            # Whole source texels, dark outlines included; no color-threshold mask.
            pix[ty][tx]=sample(sx,sy)
    save('split'+str(tier),'split',pix,owner)

# Tuning: all four long arms and the surrounding cold-blue facet of the reference.
star_rows={27:(88,90),28:(88,90),29:(88,90),30:(88,90),31:(87,91),32:(86,93),33:(85,94),34:(84,95),35:(82,97),36:(84,95),37:(86,93),38:(86,93),39:(88,91),40:(88,90),41:(88,90),42:(88,90),43:(88,90)}
star_owner=bones['tuning'].copy(); pix=copybase()
for sx,sy in [(x+2,y+3) for x,y in star_owner]: pix[sy-3][sx-2]=sample(sx,sy)
for sy,(lo,hi) in star_rows.items():
    for sx in range(lo,hi+1):
        tx,ty=sx-2,sy-3
        pix[ty][tx]=sample(sx,sy); star_owner.add((tx,ty))
save('tuning1','tuning',pix,star_owner)

# Extension has visibly different construction: a small inset eye, a full eye in
# a complete socket, then the reference's external upper/lateral/lower guards.
eye_owner=protect('extension',rect(10,97,32,118))
for tier in (1,2,3):
    pix=copybase(); owner=eye_owner.copy()
    for x,y in owner: pix[y][x]=[0,0,0,0]
    if tier==1:
        # Compact approved iris with its own native dark edge; no invented housing.
        for y in range(100,113):
            for x in range(14,27):
                sx=14+round((x-14)*13/12); sy=107+round((y-100)*12/12)
                pix[y][x]=sample(sx,sy)
        # Native reference shaft seat, verbatim, connects the compact inset eye.
        for y in range(97,102):
            for x in range(25,30):
                if base[y][x][3]: pix[y][x]=sample(x-1,y+6)
    else:
        for sy in range(103,124):
            for sx in range(9,32):
                tx,ty=sx+1,sy-6
                if (tx,ty) not in owner: continue
                if tier==2 and (sx<12 or sx>28 or sy<107 or sy>120):
                    continue
                pix[ty][tx]=sample(sx,sy)
        if tier==2:
            for y in range(97,102):
                for x in range(25,30):
                    if base[y][x][3]: pix[y][x]=sample(x-1,y+6)
    save('extension'+str(tier),'extension',pix,owner)

# Art-owner boundaries must be disjoint; state changes own their exact native pixels.
changes={}
for name,state in states.items():
    changes[name]={(x,y) for y in range(128) for x in range(128) if state['pixelsRGBA'][y][x]!=base[y][x]}
maximum=copybase()
for name in ['resonance2','split3','tuning1','extension3']:
    for x,y in changes[name]: maximum[y][x]=states[name]['pixelsRGBA'][y][x][:]
states['all_max']={'module':'all','pixelsRGBA':maximum,'glowPointEffects':[]}
states['ordinary128']={'module':'ordinary','pixelsRGBA':base,'glowPointEffects':[]}

# Root-selected illumination on native facet highlights. Backing remains unlit.
for name,state in states.items():
    mod=state['module']
    if mod in ('all','ordinary'): continue
    points=[]
    for x,y in sorted(changes[name],key=lambda p:(p[1],p[0])):
        r,g,b,a=state['pixelsRGBA'][y][x]
        if a==0: continue
        if mod=='resonance': chosen=r>=140 and r>g*1.2; phase=(x+y)*.17; amp=.035 if name.endswith('1') else .05; group='ruby-cutting-facet'
        elif mod=='split': chosen=b>=160 and r>=120; phase=(y-42)*.17; amp=.035 if name.endswith('1') else .045 if name.endswith('2') else .05; group='amethyst-cutting-facet'
        elif mod=='tuning': chosen=g>=135 and b>=160; phase=math.atan2(y-32,x-87); amp=.045; group='star-arm'
        else: chosen=g>=100 and g>r*1.12; phase=math.atan2(y-107,x-21); amp=.025 if name.endswith('1') else .035 if name.endswith('2') else .045; group='jade-facet'
        if chosen:
            stable=(mod=='tuning' and abs(x-87)<=1 and abs(y-32)<=1) or (mod=='extension' and 17<=x<=26 and 101<=y<=113)
            points.append({'x':x,'y':y,'phaseRadians':0.0 if stable else round(phase,6),'amplitude':0.0 if stable else amp,'stable':stable,'group':group})
    state['glowPointEffects']=points

data={'owner':'root','status':'visual-preview-only','version':'0.1.14','coordinateSpace':'native-128-XY','frames':16,'ticksPerFrame':3,'componentBounds128':{'resonance':[32,0,85,43],'split':[93,39,127,77],'tuning':[77,23,100,45],'extension':[9,95,34,120]},'motherReference':{'path':master_path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(master_path.read_bytes()).hexdigest().upper()},'states':states,'notes':'User correction: I violet edge only, II primary blade entirely replaced, III second lower blade. Whole dark backing/outline replacement; complete cardinal star; small inset eye / full socket / external guards.'}
(OUT/'root-pixel-states.json').write_text(json.dumps(data,separators=(',',':'))+'\n',encoding='utf-8')
for a,pa in owners.items():
    for b,pb in owners.items():
        if a<b and pa&pb: print('OWNER OVERLAP',a,b,len(pa&pb),sorted(pa&pb)[:15])
print('Root-authored native state data:',len(states),'states')
