import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'src/main/resources/assets/echopickaxe'
DISPLAY_HANDHELD = {
    'thirdperson_righthand': {'rotation': [0, -90, 55], 'translation': [0, 4, 0.5], 'scale': [0.85, 0.85, 0.85]},
    'thirdperson_lefthand': {'rotation': [0, 90, -55], 'translation': [0, 4, 0.5], 'scale': [0.85, 0.85, 0.85]},
    'firstperson_righthand': {'rotation': [0, -90, 25], 'translation': [1.13, 3.2, 1.13], 'scale': [0.68, 0.68, 0.68]},
    'firstperson_lefthand': {'rotation': [0, 90, -25], 'translation': [1.13, 3.2, 1.13], 'scale': [0.68, 0.68, 0.68]},
}
DISPLAY_GENERATED = {
    'ground': {'rotation': [0, 0, 0], 'translation': [0, 2, 0], 'scale': [0.5, 0.5, 0.5]},
    'head': {'rotation': [0, 180, 0], 'translation': [0, 13, 7], 'scale': [1, 1, 1]},
    'thirdperson_righthand': {'rotation': [0, 0, 0], 'translation': [0, 3, 1], 'scale': [0.55, 0.55, 0.55]},
    'firstperson_righthand': {'rotation': [0, -90, 25], 'translation': [1.13, 3.2, 1.13], 'scale': [0.68, 0.68, 0.68]},
    'fixed': {'rotation': [0, 180, 0], 'scale': [1, 1, 1]},
}

DISPLAY_PICKAXE = {**DISPLAY_GENERATED, **DISPLAY_HANDHELD}

for item, display in [('echo_pickaxe', DISPLAY_PICKAXE), ('echo_crystal', DISPLAY_GENERATED), ('echo_upgrade_smithing_template', DISPLAY_GENERATED)]:
    texture = ASSETS / f'textures/item/{item}.png'
    model = ASSETS / f'models/item/{item}.json'
    im = Image.open(texture).convert('RGBA')
    w, h = im.size
    if w != 32 or h != 32:
        raise SystemExit(f'{item}: expected 32x32 sprite, found {w}x{h}')
    opaque = {(x, y) for y in range(h) for x in range(w) if im.getpixel((x, y))[3] != 0}
    elements = []

    def center_uv(x, y):
        u = x / 2 + 0.25
        v = y / 2 + 0.25
        return [u, v, u, v]

    edge_faces = 0
    for x, y in sorted(opaque, key=lambda p: (p[1], p[0])):
        uv = center_uv(x, y)
        faces = {
            'north': {'uv': uv, 'texture': '#layer0'},
            'south': {'uv': uv, 'texture': '#layer0'},
        }
        for face, neighbor in (
            ('west', (x - 1, y)), ('east', (x + 1, y)),
            ('up', (x, y - 1)), ('down', (x, y + 1)),
        ):
            if neighbor not in opaque:
                faces[face] = {'uv': uv, 'texture': '#layer0'}
                edge_faces += 1
        y0 = 16 - (y + 1) / 2
        y1 = 16 - y / 2
        elements.append({
            'from': [x / 2, y0, 7.5],
            'to': [(x + 1) / 2, y1, 8.5],
            'shade': False,
            'faces': faces,
        })

    # Do not inherit item/generated: ModelBakery treats its builtin/generated root
    # as a generation marker and replaces explicit elements from the alpha mask.
    result = {
        'gui_light': 'front',
        'display': display,
        'textures': {'layer0': f'echopickaxe:item/{item}', 'particle': '#layer0'},
        'ambientocclusion': False,
        'elements': elements,
    }
    model.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'{item}: opaque texels={len(opaque)}; per-texel elements={len(elements)}; silhouette faces={edge_faces}; model={model}')
