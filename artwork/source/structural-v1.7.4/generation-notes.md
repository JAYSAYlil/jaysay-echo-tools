# v1.7.4 视觉回退候选

视觉基线严格取根目录 `jaysay-echo-tools-1.6.0.jar`。独立生成器从 JAR 按字节恢复全12项各自的 base PNG、glow PNG、mcmeta 和 item model，共48个候选文件。10项未改动资产及全部12张base PNG保持JAR原字节。仅 `extension_crystal`、`tuning_crystal` 的 glow/model/meta 发生差异。候选已通过根节点独立审计并部署冻结。部署前生产态另存于 `artwork/validation/v1.7.4/pre-deploy-1.7.3/assets/echopickaxe`；历史 `artwork/source/structural-v1.7.3` 保持原样。部署SHA-256记录见 `artwork/validation/v1.7.4/deployment-hashes.json`。

- 延展保留1.6.0原64tick glow shimmer的平滑RGB变化：按tick将16帧（4 ticks/frame、interpolate=true）线性预采样为192帧（1 tick/frame、interpolate=false），当前alpha不变。此举保留路径外的1.6颜色波动并避免瞳孔插值重影。原x17,y14..17的黑瞳以96tick慢周期在x16/17/18间停驻，不眨眼；固定alpha union包含12格眼部路径，RGB瞳色取原底图。中心补色按每行固定取自x18（y14-16）及x16（y17）。
- 调谐保留1.6.0原16帧×6 ticks（96tick）并保留interpolate=true。依据原图像素坐标仅新增四臂端部8格：N(14,11)(14,10), S(14,20)(14,21), W(10,15)(9,15), E(18,15)(19,15)。四臂依次呈现内端→两端→内端→原状态的轻微同色反光；激活点以当帧原glow RGB（原本透明时用base RGB）提亮12%。
- 两个候选model都从JAR原model重绑 north/south glow face，几何、UV、display保留；未新增元素/parent。
- 预览GIF以50ms/tick合成完整底图与glow；PNG帧板是关键帧。四臂像素坐标为 `tuning-glow-tip-coordinates-1.7.4.png`。
- 复现命令：在项目根目录运行 `python artwork/source/structural-v1.7.4/generate_visual_rollback.py`。
