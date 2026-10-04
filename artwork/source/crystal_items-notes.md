六枚晶体物品图标

源图：crystal_items-imagegen.png（imagegen 生成的 1536×1024 RGBA 3×2 sprite sheet），生成时参考了 ../echo_crystal-imagegen.png 的幽匿青黑像素风格。

格子顺序（从左到右、从上到下）：resonance_crystal（红石红）、enhanced_resonance_crystal（红石红与青白晶核）、frequency_crystal（紫水晶紫）、enhanced_frequency_crystal（紫青）、enhanced_frequency_crystal_2（紫青与骨白晶面）、tuning_crystal（下界之星白青星核）。

导出方式：每格按 512×512 裁切，最近邻缩放为 32×32；保留采样 RGB，仅将 alpha 按 >=128 设为 255、其余设为 0。模型按不透明纹素各生成一个前后 quad，并仅为外轮廓补侧面；没有继承 item/generated。
