# 部件结构参考

生成方式：内置 `image_gen`，编辑模式，透明背景。

输入：`src/main/resources/assets/echopickaxe/textures/item/echo_pickaxe.png`，原生 64×64 普通回响镐。

输出：`fullmax-structure-concept.png`，SHA-256 `1C5D3C12840ED36DED9B04D7CB16A3464EDE39D080BD3742E79BB752E9517C76`。

此图用于研究强化部件的晶面、锐刃、四角星与眼瞳结构。它不是游戏贴图；普通镐及公共柄身仍以已选原生 64×64 图为准。上一级 `enhanced-components` 静态稿已被用户否定，不得作为候选发布。

## 完整提示词

EDIT TARGET: the attached transparent native 64 by 64 Minecraft sculk pickaxe. Create ONE refined fully upgraded version on a transparent background as an enlarged nearest-neighbor pixel-art concept, no text, no grid or UI. Preserve the exact diagonal pose, long narrow shaft, dark teal sculk material, sparse connected cyan veins, hook-shaped curved left blade, short curved right blade, and small round pommel of the target. Do not change the body into another pickaxe. Use uniformly fine native 64x64 pixel granularity throughout: each pixel a clear square, crisp pixel edges, no smooth illustration, blur, gradients, antialiasing, bloom, glitter, or super-fine subpixels. Modify only four localized component regions integrated into existing pickaxe material. Left blade: replace ALL its ivory bone cutting edge with a complete saturated ruby-red crystal cutting blade, very sharp tapering hooked tip, clearly faceted ruby shadow bed, slender coral-pink cutting ridge, tiny pale-pink specular chips; enhance high tier with a narrow raised faceted crystal ridge along the upper blade, never a blunt bulky cap. Right blade: replace ALL ivory bone edge with complete amethyst violet crystal; three clean stepped faceted segments nested into the curved existing blade with fine dark separators, small lilac bevel highlights, never long hanging separate spikes or a string of beads. Original central junction: a SINGLE elegant icy cyan four-point star, narrow sharp tapered arms with conspicuously dark diagonal spaces around the arms, stable tiny icy-white center, clean slender tips; NOT a filled bright square, diamond, round blob, or a huge flash. Original small round shaft-end pommel: a detailed jade EYE relic, emerald beveled crystalline iris with a dark vertical pupil, small mint-green reflected glint, clean dark teal metal/crystal cradle and three SHORT well-separated jade support prongs following the original round contour; no ivory bone remains at the activated pommel, no white ring, no generic radial gradient blob, no unrelated big disk pasted onto shaft. KEEP each upgraded part the same pixel scale and connected physical material as the original body. Overall upgraded tool should be elegant, visibly richer than the base, readable at inventory size, sharp and coherent. The whole object must fit inside a single 64x64 logical grid with only modest component-local one-pixel contour refinements. Native pixel art game texture style, not a painted concept.

## 紫色刃口修订

`fullmax-purple-edge-concept.png`：用户否定；连续浅色锋线未形成所要求的实体刃口，不得用作最终结构。

`fullmax-purple-lobe-concept.png`：在用户认可的 `fullmax-structure-concept.png` 上局部加入紫晶实体弯刃，供原生纹理结构参考。该概念尚不代表已发布贴图。

### 实体刃片提示词

EDIT TARGET: Image 1 is the approved upgraded pixel-art pickaxe. Image 2 is ONLY a shape reference, the ordinary pickaxe, whose ivory blade regions are protruding physical cutting blades. Keep Image 1 as the complete target; do NOT replace it with Image 2. Make ONE small localized SHAPE ADDITION to the purple right blade of Image 1, then leave every other part unchanged. User specifically wants an extra piece of the silhouette as a blade, NOT a highlight stripe. Add a substantial, solid AMETHYST CUTTING BLADE LOBE projecting inward from the violet right-head crystal assembly into the empty angle between head and shaft. It should read as a hooked triangular/crescent blade, a little extra wedge of purple crystal, whose contour sticks out noticeably by about 2-3 existing square pixels. Echo the actual silhouette and physical beveled blade design of the red left blade in Image 1 and the ordinary ivory right cutting blade in Image 2. The added amethyst lobe must be seamlessly joined to the existing right violet blade: a dark plum back plane, a broad saturated violet face, and a narrow lilac beveled cutting facet. Have a clearly visible sharp projecting corner on its inner/left side and taper toward the lower tip, following the existing short curved pickaxe blade. Keep the existing three segmented amethyst facets on its outer/back side. Think carved crystal blade with mass and a sharp corner, NOT a thin glowing edge, white outline, laser beam, chain, floating gem, or long straight sword. Its cutting facet should be PURPLE/LILAC rather than white: sparse pale-violet highlight pixels only, matching the red blade's balanced facets. Keep this extra blade piece proportionate to the red blade's inward cutting lobe. Strictly preserve Image 1's red left blade, slim sharp icy four-point star, cyan sculk shaft texture, green eye pommel, object position, framing, all their original pixels and original transparency. Only the purple blade contour/material changes. Exactly same square pixel granularity and crisp game texture style, no antialiasing, no bloom, no blur.

## 用户最终选定（2026-10-04）

用户重新附上 `codex-clipboard-33ac2851-b4a3-41f5-9eaf-48166be5c04f.png`，明确表示这张设计已经很好，否定另行手绘部件。它与 `fullmax-purple-lobe-concept.png` 视觉一致，现在是满级外观母版，不再只是结构参考。

停止 `generate_nonpurple.py` 部件重画路径及其 drafts；这些稿不得成为最终候选。新的加工路径为 `artwork/source/approved-fullmax-v0.1.12/`：直接转换选定图，保留完整红色晶刃、凸出的紫晶实体刃口、四角星芒、绿眼与幽匿柄身；转换不得重新设计轮廓或用小色块替代原图材质。普通回响镐资源保持现版。
