# 1.7.1 材质精修（已部署并冻结）

本轮目标是把 1.7.0 的大幅结构动作收回到原有材质上，只移动很小的同色反光点。原始 32×32 PNG 来自 `artwork/source/emissive-v1.6.0/base_textures/`；1.7.0 对照纹理、模型快照保存在本目录 `base_glow_1.7.0/`、`base_models_1.7.0/`。生成脚本为 `artwork/generate_structural_v1_7_1.py`，不依赖图像生成模型；颜色均由原 PNG RGB 逐点派生。

经根节点审核，候选贴图、mcmeta、模型已同步到 `src/main/resources/assets/echopickaxe/` 并冻结。候选副本仍保存在 `artwork/validation/v1.7.1/candidate/` 供对照。所有不活动像素在每一帧都保留源 PNG RGB；活动反光点在相同色相上约提升 10%，没有暗化或重画原像素。没有深色瞳孔例外。基础延展仅作水平/斜向的一像素反光漂移，强化版斜向短驻留，二阶短暂居中后纵向释放；这些仅是局部反光运动，不表示重绘眼睛、瞳孔或虹膜。延展发光 mask 分别缩至40、46、37个中心像素；调谐沿细十字臂的55个像素移动小高光。其余八件仍以原始 1.6 mask 为几何范围，始终显示底图而非黑底/擦除效果。

每件32帧，普通帧时3 ticks（4.8秒周期）；调谐2 ticks（3.2秒周期）；不插值，避免离散小高光拖影。透明 mask 各帧固定，alpha 只有0/255。模型从1.5.0基线重建，仅north/south发光面使用glow纹理及Forge block/sky light=15、ambient occlusion=false；模型几何、UV、display、其他面未改动。

审阅材料：`artwork/validation/v1.7.1/extreme-comparison.png` 并列展示原图、1.7.0最暗帧、1.7.1最暗帧、1.7.1最亮帧；`emissive-items-preview.gif` 的帧按50ms（每tick）播放，普通物品覆盖96 ticks/4.8秒，调谐自身周期为64 ticks/3.2秒；`keyframes.png` 为关键帧总表，`eye-keyframes-closeup.png` 放大显示延展三阶局部反光路径。`tone-audit.json` 记录全图最低/最高亮度比和被压暗细节数；统计仅对原图不透明像素计入亮度，忽略透明像素的RGB。`audit_resources.py` 验证了12件模型与1.5.0发行包的几何/UV/显示一致、基图未变、mask固定且alpha二值；`audit_tone.py` 验证整图最低亮度和细节保留。
