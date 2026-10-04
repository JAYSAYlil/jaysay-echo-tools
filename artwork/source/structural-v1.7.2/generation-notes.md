# 延展之晶细瞳微动 1.7.2（已部署并冻结）

本候选只改变 `extension_crystal` 的发光strip和模型贴图绑定：原图中央有一条明确的黑色竖瞳，源坐标 x=17、y=14..17，RGB 为 #030E21、#011423、#03091A、#030B1B。原始ROI放大及网格坐标图见 `artwork/validation/v1.7.2/eye-source-roi.png`；三态横向对照见 `pupil-left-center-right.png`。

动画保留原4像素高、1像素宽瞳孔，x=17中央停留24/32帧，其余左右各偏移1像素4帧，再回中；不眨眼、不新增高光、不绘制虹膜。原x=17列空出时，四行始终固定用原图同一行的绿色虹膜/切面RGB补回：y14、y15、y16取x18，y17取x16；不随视线方向切换，避免扩大y14/x16白亮面与y17/x18骨白高光。瞳孔目标列始终复制原x17的4个暗色RGB；目的只是露出原底图相邻材质，不改轮廓、alpha、UV或元素几何。glow alpha固定在原1.7.1 mask与x=16..18/y=14..17不透明路径的并集（46像素），每帧仍为0/255。发光正反面沿用Forge lightmap配置。

两件强化版在中心ROI没有同样清楚的连续黑色竖瞳；按任务要求不强加新瞳孔，也不改它们的行为。候选中的 `enhanced_extension_crystal` 与 `_2` 的模型、glow PNG、mcmeta是从冻结1.7.1快照逐字节复制。其余九件完全未触碰。经根节点批准，已只将基础延展之晶的模型、glow PNG、mcmeta部署到正式资源目录并冻结；其它11个物品资源和原始PNG均未改。

生成器 `artwork/generate_structural_v1_7_2.py`；候选文件在 `artwork/validation/v1.7.2/candidate/`。`extension-pupil-motion.gif` 每状态150ms（3 ticks），循环4.8秒；`manifest.json` 列出原瞳坐标、左右/中央帧范围、填回颜色策略和不变项。

