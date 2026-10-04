"""Mechanically apply root-authored lower-tier refinements to preview copies only."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[3]
SPEC_PATH=ROOT/'artwork/source/root-tier-refinements/refinement-spec.json'
PROOF_PATH=ROOT/'artwork/validation/base-preserving-upgrades-v0.1.13/tier-manifest.json'
ORDINARY64_PATH=ROOT/'src/main/resources/assets/echopickaxe/textures/item/echo_pickaxe.png'
SCALE=4
MODULE_STATE_NAMES={
    'resonance':['resonance1','resonance2'],
    'split':['split1','split2','split3'],
    'tuning':['tuning1'],
    'extension':['extension1','extension2','extension3'],
}
STATE_ORDER=['ordinary128','resonance1','resonance2','split1','split2','split3',
             'tuning1','extension1','extension2','extension3','all_max']
ALLOWED_PATCH_FIELDS={
    'target','source','module','description','copyRectanglesXYXYInclusive',
    'copyOriginalBonePixelsIn64RegionXYXYInclusive','limitToSourceModuleEdits',
    'paintPixelsRGBA',
}
ALLOWED_SPEC_FIELDS={'status','owner','baseDirectory','outputDirectory','intent','lockedStates',
                     'bonePalette','patches','animation','technicalExecutorMayNot'}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def safe_repo_path(value: str) -> Path:
    path=(ROOT/value).resolve()
    require(path==ROOT or ROOT in path.parents,f'path escapes repository: {value}')
    return path


def read_json(path: Path) -> tuple[dict,bytes]:
    data=path.read_bytes()
    return json.loads(data.decode('utf-8-sig')),data


def checked_image(path: Path, expected_sha: str, label: str, size=(128,128)) -> Image.Image:
    data=path.read_bytes()
    require(sha(data)==expected_sha.upper(),f'{label}: frozen input SHA mismatch')
    image=Image.open(path).convert('RGBA')
    require(image.size==size,f'{label}: expected {size}, got {image.size}')
    return image


def coords(raw, label: str) -> set[tuple[int,int]]:
    result=set()
    for value in raw:
        require(isinstance(value,list) and len(value)==2,f'{label}: malformed point {value!r}')
        point=(int(value[0]),int(value[1]))
        require(0<=point[0]<128 and 0<=point[1]<128,f'{label}: out-of-bounds point {point}')
        require(point not in result,f'{label}: duplicate point {point}')
        result.add(point)
    return result


def inclusive_rect(value, limit: int, label: str) -> tuple[int,int,int,int]:
    require(isinstance(value,list) and len(value)==4,f'{label}: expected inclusive [x0,y0,x1,y1]')
    x0,y0,x1,y1=(int(v) for v in value)
    require(0<=x0<=x1<limit and 0<=y0<=y1<limit,
            f'{label}: rectangle is out of {limit}x{limit} bounds: {value}')
    return x0,y0,x1,y1


def strict_int(value, label: str) -> int:
    require(type(value) is int,f'{label}: expected an integer (booleans are not accepted)')
    return value


def pixel_diff(before: Image.Image, after: Image.Image) -> set[tuple[int,int]]:
    a,b=before.load(),after.load()
    return {(x,y) for y in range(before.height) for x in range(before.width) if a[x,y]!=b[x,y]}


def write_png(image: Image.Image, path: Path) -> bytes:
    path.parent.mkdir(parents=True,exist_ok=True)
    image.save(path,format='PNG',optimize=False)
    return path.read_bytes()


def rgba_board_panel(image: Image.Image, background: tuple[int,int,int]) -> Image.Image:
    panel=Image.new('RGBA',image.size,(*background,255))
    panel.alpha_composite(image)
    return panel.convert('RGB').resize((image.width*SCALE,image.height*SCALE),Image.Resampling.NEAREST)


def save_whole_tool_board(states: list[str], originals: dict[str,Image.Image],
                          previews: dict[str,Image.Image], background_name: str,
                          background: tuple[int,int,int], path: Path) -> None:
    label_width=190; cell=128*SCALE; margin=12; header=48
    board=Image.new('RGB',(label_width+2*cell+3*margin,header+len(states)*(cell+margin)),background)
    draw=ImageDraw.Draw(board); text=(24,24,30) if background_name=='white' else (242,242,248)
    draw.text((margin,16),f'Root-authored refinement — whole tool — {background_name} background — 1 source pixel = {SCALE}px',fill=text)
    for row,name in enumerate(states):
        y=header+row*(cell+margin); draw.text((margin,y+cell//2-6),name,fill=text)
        for col,image in enumerate((originals[name],previews[name])):
            x=label_width+margin+col*(cell+margin)
            draw.text((x,y-11),'source' if col==0 else 'preview',fill=text)
            board.paste(rgba_board_panel(image,background),(x,y))
    path.parent.mkdir(parents=True,exist_ok=True)
    board.save(path,optimize=True)


def save_component_board(module: str, states: list[str], originals: dict[str,Image.Image],
                         previews: dict[str,Image.Image], mask: set[tuple[int,int]],
                         background_name: str, background: tuple[int,int,int], path: Path) -> list[int]:
    xmin=min(x for x,_ in mask); xmax=max(x for x,_ in mask)
    ymin=min(y for _,y in mask); ymax=max(y for _,y in mask)
    pad=2; x0=max(0,xmin-pad); x1=min(127,xmax+pad); y0=max(0,ymin-pad); y1=min(127,ymax+pad)
    width=(x1-x0+1)*SCALE; height=(y1-y0+1)*SCALE
    label_width=180; margin=12; header=48
    board=Image.new('RGB',(label_width+2*width+3*margin,header+len(states)*(height+margin)),background)
    draw=ImageDraw.Draw(board); text=(24,24,30) if background_name=='white' else (242,242,248)
    draw.text((margin,16),f'{module} component crop — {background_name} — scale {SCALE} — source / preview',fill=text)
    for row,name in enumerate(states):
        y=header+row*(height+margin); draw.text((margin,y+height//2-6),name,fill=text)
        for col,image in enumerate((originals[name],previews[name])):
            x=label_width+margin+col*(width+margin)
            crop=image.crop((x0,y0,x1+1,y1+1))
            panel=rgba_board_panel(crop,background)
            draw.text((x,y-11),'source' if col==0 else 'preview',fill=text)
            board.paste(panel,(x,y))
    path.parent.mkdir(parents=True,exist_ok=True)
    board.save(path,optimize=True)
    return [x0,y0,x1,y1]


def main() -> None:
    spec,spec_bytes=read_json(SPEC_PATH); proof,proof_bytes=read_json(PROOF_PATH)
    require(set(spec)==ALLOWED_SPEC_FIELDS,f'spec fields changed: {sorted(set(spec)^ALLOWED_SPEC_FIELDS)}')
    require(spec['status']=='local-refinement-preview-only' and spec['owner']=='root',
            'spec must remain root-owned preview-only instructions')
    require(proof['schema']=='base-preserving-upgrades-v0.1.13-v1','unexpected frozen proof schema')
    require(spec['baseDirectory']=='artwork/source/base-preserving-upgrades-v0.1.13',
            'refinement base directory differs from the specified 0.1.13 source')
    out= safe_repo_path(spec['outputDirectory'])
    require(not out.exists() or not any(out.iterdir()),f'refusing to overwrite nonempty preview directory: {out}')
    base_dir=safe_repo_path(spec['baseDirectory'])
    ordinary_entry=proof['ordinary128Base']
    ordinary128_path=safe_repo_path(ordinary_entry['path'])
    ordinary128=checked_image(ordinary128_path,ordinary_entry['sha256'],'ordinary128')
    ordinary_data=ORDINARY64_PATH.read_bytes()
    require(sha(ordinary_data)==proof['sourceOrdinary']['sha256'].upper(),'ordinary64 source SHA differs from frozen proof')
    ordinary64=Image.open(ORDINARY64_PATH).convert('RGBA')
    require(ordinary64.size==(64,64),'ordinary64 texture is not 64x64')
    require(ordinary64.resize((128,128),Image.Resampling.NEAREST).tobytes()==ordinary128.tobytes(),
            'ordinary128 does not match exact nearest-neighbor 2x ordinary64')

    locked=set(spec['lockedStates'])
    require(locked=={'ordinary128','resonance2','split3','extension3','tuning1','all_max'},
            'locked state set differs from the explicit root specification')
    originals={'ordinary128':ordinary128}
    source_hashes={'ordinary128':ordinary_entry['sha256'].upper()}
    for state,entry in proof['states'].items():
        if state not in STATE_ORDER:
            continue
        image_path=safe_repo_path(entry['path'])
        image=checked_image(image_path,entry['sha256'],state)
        originals[state]=image
        source_hashes[state]=entry['sha256'].upper()
    require(set(STATE_ORDER)<=set(originals),f'missing source states: {sorted(set(STATE_ORDER)-set(originals))}')

    palette={tuple(int(c) for c in color) for color in spec['bonePalette']}
    require(len(palette)==3 and all(len(color)==3 and all(0<=c<=255 for c in color) for color in palette),
            'bonePalette must contain exactly three explicit RGB colors')
    module_masks={module:coords(proof['moduleEditMasks'][module]['coordinates'],f'{module} moduleEditMask')
                  for module in MODULE_STATE_NAMES}
    previews={name:image.copy() for name,image in originals.items()}
    patches=spec['patches']; require(isinstance(patches,list),'patches must be a list')
    seen_targets=set(); patch_records=[]; changed_coords={}
    for patch in patches:
        require(set(patch)<=ALLOWED_PATCH_FIELDS,f'{patch.get("target","?")}: unknown patch fields')
        require({'target','source','module','description'}<=set(patch),f'patch lacks required fields: {patch}')
        target,source,module=patch['target'],patch['source'],patch['module']
        require(target in originals and source in originals,f'unknown target/source state: {target}/{source}')
        require(module in module_masks,f'unknown module: {module}')
        require(target not in locked and target not in seen_targets,f'target is locked or duplicated: {target}')
        require(source in locked,f'{source} must be a root-locked max source')
        seen_targets.add(target)
        before=previews[target].copy(); target_px=previews[target].load(); source_px=originals[source].load()
        original_target_px=originals[target].load()
        mask=module_masks[module]
        applied_rects=[]; clipped_rectangles=[]; actual_bone_parent_pixels=[]
        allowed_bone_children=set()

        for rect_i,raw_rect in enumerate(patch.get('copyRectanglesXYXYInclusive',[])):
            x0,y0,x1,y1=inclusive_rect(raw_rect,128,f'{target} copyRectangles[{rect_i}]')
            require(patch.get('limitToSourceModuleEdits') is True,
                    f'{target}: copyRectangles must explicitly enable source-mask limiting')
            applied=[]; clipped=[]
            for y in range(y0,y1+1):
                for x in range(x0,x1+1):
                    point=(x,y)
                    if point not in mask:
                        clipped.append([x,y]); continue
                    target_px[x,y]=source_px[x,y]; applied.append([x,y])
            applied_rects.append({'rect':raw_rect,'applied':len(applied),'coordinates':applied})
            clipped_rectangles.append({'rect':raw_rect,'coordinates':clipped})

        bone_rect=patch.get('copyOriginalBonePixelsIn64RegionXYXYInclusive')
        if bone_rect is not None:
            x0,y0,x1,y1=inclusive_rect(bone_rect,64,f'{target} original-bone region')
            for y in range(y0,y1+1):
                for x in range(x0,x1+1):
                    ordinary_pixel=ordinary64.getpixel((x,y))
                    if ordinary_pixel[3]!=255 or ordinary_pixel[:3] not in palette:
                        continue
                    actual_bone_parent_pixels.append([x,y])
                    for dy in (0,1):
                        for dx in (0,1):
                            nx,ny=2*x+dx,2*y+dy
                            allowed_bone_children.add((nx,ny))
                            target_px[nx,ny]=source_px[nx,ny]

        paint_entries=patch.get('paintPixelsRGBA',[])
        require(isinstance(paint_entries,list),f'{target}: paintPixelsRGBA must be a list')
        paint_records=[]; seen_paint_points=set()
        for paint_i,raw_paint in enumerate(paint_entries):
            label=f'{target} paintPixelsRGBA[{paint_i}]'
            require(isinstance(raw_paint,list) and len(raw_paint)==6,
                    f'{label}: expected [x,y,r,g,b,a]')
            values=[strict_int(v,label) for v in raw_paint]
            x,y,r,g,b,a=values
            require(0<=x<128 and 0<=y<128,f'{label}: coordinate outside 128x128: {(x,y)}')
            require(all(0<=v<=255 for v in (r,g,b,a)),f'{label}: RGBA values must be in 0..255')
            point=(x,y)
            require(point not in seen_paint_points,f'{label}: duplicate paint coordinate {point}')
            seen_paint_points.add(point)
            require(original_target_px[x,y][3]==255,
                    f'{label}: target pixel was not originally opaque at {point}')
            require(point in mask or point in allowed_bone_children,
                    f'{label}: coordinate is outside moduleEditMask and selected ordinary-bone children: {point}')
            before_rgba=target_px[x,y]
            after_rgba=(r,g,b,a)
            target_px[x,y]=after_rgba
            original_rgba=original_target_px[x,y]
            paint_records.append({'coordinate':[x,y],'rgba':list(after_rgba),
                                  'originalTargetRGBA':list(original_rgba),
                                  'beforeRGBA':list(before_rgba),'changed':before_rgba!=after_rgba,
                                  'changedFromOriginal':original_rgba!=after_rgba,
                                  'allowedBy':'moduleEditMask' if point in mask else 'ordinaryBoneChildren'})

        actual=pixel_diff(before,previews[target])
        changed=sorted(([x,y] for x,y in actual),key=lambda p:(p[1],p[0]))
        changed_coords[target]=changed
        patch_records.append({'target':target,'source':source,'module':module,'description':patch['description'],
                              'copyRectangles':applied_rects,'maskClippedRectangleCoordinates':clipped_rectangles,
                              'boneRegion64':bone_rect,'matchedOrdinaryBonePixels64':actual_bone_parent_pixels,
                              'paintPixelsRGBA':paint_records,
                              'paintPixelCount':len(paint_records),
                              'paintChangedPixelCount':sum(record['changed'] for record in paint_records),
                              'actualChangedCoordinateCount':len(changed),'actualChangedCoordinates128':changed})

    require(seen_targets=={p['target'] for p in patches},'patch target accounting mismatch')
    for state in locked:
        require(previews[state].tobytes()==originals[state].tobytes(),f'locked state changed: {state}')
    for state in ('ordinary128','resonance2','split3','extension3','tuning1','all_max'):
        require(previews[state].tobytes()==originals[state].tobytes(),f'root-locked PNG differs in pixels: {state}')

    if out.exists():
        require(not any(out.iterdir()),f'refusing to write into nonempty preview directory: {out}')
    out.mkdir(parents=True,exist_ok=True)
    preview_hashes={}
    for state in STATE_ORDER:
        target=out/f'{state}.png'
        if state in locked:
            src_entry=ordinary_entry if state=='ordinary128' else proof['states'][state]
            shutil.copyfile(safe_repo_path(src_entry['path']),target)
            data=target.read_bytes()
            require(sha(data)==source_hashes[state],f'locked preview copy is not byte exact: {state}')
        else:
            data=write_png(previews[state],target)
        preview_hashes[state]=sha(data)

    board_files=[]
    for background_name,background in (('dark',(22,24,34)),('white',(246,246,246))):
        path=out/f'whole-tool-before-after-{background_name}.png'
        save_whole_tool_board(STATE_ORDER,originals,previews,background_name,background,path)
        board_files.append({'path':path.relative_to(ROOT).as_posix(),'sha256':sha(path.read_bytes()),
                            'kind':'whole-tool-before-after','background':background_name,
                            'states':STATE_ORDER,'pixelScale':SCALE,'cellPixels':[128*SCALE,128*SCALE]})
        for module,state_names in MODULE_STATE_NAMES.items():
            path=out/f'{module}-component-before-after-{background_name}.png'
            bounds=save_component_board(module,state_names,originals,previews,module_masks[module],
                                        background_name,background,path)
            board_files.append({'path':path.relative_to(ROOT).as_posix(),'sha256':sha(path.read_bytes()),
                                'kind':'module-component-before-after','module':module,
                                'background':background_name,'states':state_names,
                                'cropBounds128':bounds,'pixelScale':SCALE,
                                'cellPixels':[(bounds[2]-bounds[0]+1)*SCALE,(bounds[3]-bounds[1]+1)*SCALE]})

    changed_path=out/'actual-changed-coordinates.json'
    changed_record={'coordinateSpace':'native-128-global-XY','states':changed_coords,'patches':patch_records}
    changed_path.write_text(json.dumps(changed_record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    manifest={'schema':'root-tier-refinement-preview-v1','status':'preview-only','owner':'root',
              'specPath':SPEC_PATH.relative_to(ROOT).as_posix(),'specSha256':sha(spec_bytes),
              'proofPath':PROOF_PATH.relative_to(ROOT).as_posix(),'proofSha256':sha(proof_bytes),
              'ordinary64Sha256':sha(ordinary_data),'ordinary128Sha256':sha(ordinary128_path.read_bytes()),
              'lockedStates':sorted(locked),'sourceStateSha256':source_hashes,
              'previewStateSha256':preview_hashes,'statePixelChanges':{name:len(points) for name,points in changed_coords.items()},
              'explicitPaintPixelCounts':{record['target']:record['paintPixelCount'] for record in patch_records},
              'explicitPaintChangedPixelCounts':{record['target']:record['paintChangedPixelCount'] for record in patch_records},
              'boards':board_files,'changedCoordinatesPath':changed_path.relative_to(ROOT).as_posix(),
              'notes':['Source tier PNGs were read-only.',
                       'copyRectangles were intersected with the frozen moduleEditMasks.',
                       'Bone-palette selection used exact ordinary64 RGB plus nearest2x child-coordinate mapping.',
                       'Explicit paintPixelsRGBA entries were range-checked and restricted to originally opaque module-mask or selected ordinary-bone child coordinates.',
                       'No new colors, silhouette, fill pixels, animations, candidates, builds, or installs were generated.']}
    manifest_path=out/'refinement-preview-manifest.json'
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'PASS preview-only compile: {len(patch_records)} root patches, {sum(len(v) for v in changed_coords.values())} actual changed texels; locked PNG byte identity confirmed')
    print(f'boards: {len(board_files)}; output: {out.relative_to(ROOT).as_posix()}')


if __name__=='__main__':
    main()
