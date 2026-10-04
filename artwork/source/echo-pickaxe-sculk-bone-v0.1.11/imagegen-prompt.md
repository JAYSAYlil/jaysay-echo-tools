# 0.1.11 幽匿骨质外观参照

**已被用户否定，禁止用于候选生成或部署。** 用户后续指定 `user-selected-reference.png` 为唯一视觉基准，要求脉络保持该图的疏密；骨白用于未装对应强化的部位，强化部件替代该处骨白；柄尾骨白为局部扣片而非环绕圆框。此文件与生成图仅保留为废弃方案记录。

使用 built-in `image_gen` 编辑原先用户认可的全强化外观，作为 Luna 制作游戏纹理的视觉参照。生成图并非直接发布的游戏纹理。

- 输入：`artwork/source/echo-pickaxe-upgrades-v0.1.2/concept-full-upgrade-selected.png`
- 输出：`artwork/source/echo-pickaxe-sculk-bone-v0.1.11/sculk-bone-imagegen-reference.png`
- 输出 SHA-256：`756EFF6D18EB4361C0354421619FFB8F3BFFA1334699851079F74A4E2920468E`
- 透明背景：true。
- 用户最新要求：镐全身布满细颗粒青色幽匿脉络；两端镐尖明确呈现白色骨质；镐柄末端为圆形装饰且有白色骨质。旧版本的少量骨白点缀、短楔封帽方案已被否定。

完整生成提示词：

> Use case: precise-object-edit. Asset: pixel-art Minecraft sculk-themed pickaxe concept reference for a mod. Edit the supplied reference pickaxe and preserve its diagonal orientation, slim overall pickaxe proportions, head silhouette, red resonance ornament at the left blade, purple amethyst frequency ornament on the right blade, central four-point pale blue star, and emerald eye jewel at the handle end. REQUIRED visible changes: (1) Replace the sparse cyan cracks with many fine, bright turquoise sculk vein branches distributed across the ENTIRE dark teal head AND ENTIRE shaft, connecting naturally from the head down to the pommel. Keep dark teal between veins; branch veins are crisp one-pixel-width at a unified fine pixel grid, NOT big blue blocks, NOT a single blue strip, NOT small isolated dots. (2) BOTH terminal pickaxe tips have unmistakable substantial ivory bone blade material. Give the leftmost tip a bone-white sharpened segment edged onto the red upgraded blade; give the rightmost downward tip a bone-white sharpened segment extending from the purple upgraded blade. These must read clearly as bone-white tips in a small game icon, not merely one highlight pixel. Bone colors use warm ivory, creamy white and restrained gray shadows like vanilla Minecraft sculk catalyst/sculk shrieker bones. (3) Replace the irregular oval handle-end pendant with a clearly ROUND circular pommel, centered on the shaft axis. Retain the green eye in the middle, but surround it with a substantial continuous bone-white circular rim, dark-teal inset and a little turquoise veining. Connect the circle solidly to the shaft, do not add a dangling hook or spike. Roundness is important, not a diamond or long oval. All surfaces must share the same crisp fine pixel scale. True pixel art with hard square pixels, no gradients, no antialiasing, no blur, no photorealism, no 3D scene, no glow bloom outside the shape. Single pickaxe centered, entirety visible with small margins, transparent background, no labels or text.
