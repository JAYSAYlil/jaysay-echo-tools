# 1.1.0 物品贴图来源

三张贴图使用内置 `image_gen` 生成，保留原始透明 PNG 于 `artwork/source/`，用 Windows System.Drawing 的 `NearestNeighbor` 插值缩至 32×32 RGBA，作为 `src/main/resources/assets/echopickaxe/textures/item/` 下的游戏贴图。生成源图为 1254×1254；缩放后检查透明角 alpha 为 0，并目视确认轮廓与像素格。

## 回响镐

Prompt: `Minecraft Java Edition item texture, transparent PNG. One standalone echo pickaxe, side view. Handle diagonally from bottom-left to top-right, clear horizontal head. Deep navy-black sculk stone and dark blue handle, angular vivid cyan cracks, a few bone-white chipped accents. Authentic Minecraft vanilla pixel-art style with hard square pixels, 32×32 logical grid, readable silhouette, flat game-icon shading. No scene, UI, labels, border, antialiasing, or cast shadow.`

## 回响之晶

Prompt: `Minecraft Java Edition item texture, transparent PNG. One compact jagged Echo Crystal shard with a refined faceted silhouette, dark navy-black sculk base, bright cyan fracture through the core, a few tiny bone-white facets. Clearly distinct from the vanilla echo shard. Crisp vanilla Minecraft pixel art on a 16×16 logical grid, limited palette, flat icon shading. No environment, UI, lettering, border, glow haze, antialiasing, or cast shadow.`

## 回响锻造模板

Prompt: `Minecraft Java Edition item texture, transparent PNG. One standalone Echo Smithing Template sprite in a recognizable compact smithing-template cutout silhouette. Pale bone outline, dark sculk-blue center, one small cyan echo crack/rune in the middle. Crisp vanilla Minecraft pixel art on a 16×16 logical grid, flat icon shading. Clearly a reusable crafting template, not a crystal or pickaxe. No environment, UI, text, border, glow haze, antialiasing, or cast shadow.`

## 1.2.1 回响镐透明度与模型处理

实机手持近景发现 32×32 贴图含半透明抗锯齿值：720 像素 alpha=0，只有 3 个像素 alpha=255；另有 5 个 alpha 为 1、2、3、22、72 的低透明度噪点，296 个像素 alpha 为 233–254。保留处理前 32×32 PNG 于 `source/echo_pickaxe-before-alpha-clean-32x32.png`；游戏贴图只做 alpha 归一化（低于 128 置 0，其余非零置 255），不改变 RGB 和轮廓。处理后直方图为 alpha=0 共 725 像素、alpha=255 共 299 像素。

alpha 归一化单独实测并未消除边缝。最终手持模型由 `generate_pickaxe_model.py` 生成：一张完整正反面贴图层承载 sprite，外轮廓通过 edge-only elements 挤出，侧面 UV 采样实体像素中心，避免对内部像素边界生成侧面。生成图像的内容未被重绘或放大。
