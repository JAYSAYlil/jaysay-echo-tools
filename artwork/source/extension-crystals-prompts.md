# 延展晶体图标源记录

三件图标分别由内建 `image_gen__imagegen` 单独生成；每次均以 `artwork/source/echo_crystal-imagegen.png` 与 `artwork/source/crystal_items-imagegen.png` 为参考，`transparent_background=true`。最终原图均为 1254×1254 RGBA PNG。探索阶段另有一张三格草稿和若干旧青蓝草图；它们未用于最终贴图，最终采用下列三张独立原图。

## extension_crystal

源图：`extension_crystal-imagegen.png`

最终提示词：

> Use case: Minecraft Java 1.20.1 Forge inventory icon. Design one isolated pixel-art extension crystal whose ingredient identity is an ENDER EYE. A compact crystalline eye-core in a dark sculk teal-black shard, with a clearly visible ender-green ring or orbital band circling its central crystal, suggesting long-distance reach/teleportation. Green/turquoise eye ring is the defining color and motif; do not make it blue-cyan dominant. Handmade Minecraft pixel art matching the supplied crystal references: stepped angular shard silhouette, small crisp square pixels, dark navy sculk border, luminous emerald-teal ring and inner green facets, restrained pale glints. Centered, compact, front view, substantial transparent margin. True transparent background. No backdrop, no aura, no glow, no halo, no gradients, no blur, no cast shadow, no frame, no text, no labels, no watermark, no extra objects.

## enhanced_extension_crystal

源图：`enhanced_extension_crystal-imagegen.png`

最终提示词：

> Use case: Minecraft Java 1.20.1 Forge inventory icon. Design one isolated enhanced extension crystal, first upgrade tier of an ender-eye ring crystal. Retain a dark sculk teal-black compact angular crystal silhouette and an obvious ender-green orbital ring around its core (distance/reach motif), but make the central core distinctly diamond pale-cyan/ice-aqua with brighter cyan facets. Keep green ring clearly visible around the pale cyan core. Handmade Minecraft pixel art matching the supplied references: stepped square pixel clusters, crisp edges, dark navy outline, carefully shaded solid facets. Centered, front-facing with transparent margin. True transparent background. No backdrop, no aura, no glow, no halo, no gradient, no blur, no cast shadow, no frame, no text, no labels, no watermark, no extra objects.

## enhanced_extension_crystal_2

源图：`enhanced_extension_crystal_2-imagegen.png`

最终提示词：

> Use case: Minecraft Java 1.20.1 Forge inventory icon. Design one isolated second-tier enhanced extension crystal, the most complete advanced version of the same ender-eye ring crystal family. Dark sculk teal-black angular shard, distinct emerald/ender-green orbital ring around its core, expanded and more complete bone-white crystalline plates/facets with a pale cyan center. Strong visual progression: more layered and fully formed crystal planes than the first tier, with bone-white facets prominently covering a larger area while the green ring remains recognizable. Handmade Minecraft pixel art matching the supplied references, small square pixels, hard crisp stepped edges, solid-color shading. Centered compact front view and transparent margin. True transparent background. No backdrop, no aura, no glow, no halo, no gradient, no blur, no cast shadow, no frame, no text, no labels, no watermark, no extra objects.

## 导出约定

每张独立原图整体最近邻缩放到 32×32；采样 RGB 不作修改，alpha 按 `>=128` 转 255、低于 128 转 0。JSON 从 `echo_crystal.json` 复制 display 参数；`gui_light=front`、particle 指向 `#layer0`，不设任何 `parent`。每个 alpha=255 纹素对应一个厚度 1 的前后 quad，UV 使用纹素中心；仅外轮廓增加侧面，并关闭 shade。
