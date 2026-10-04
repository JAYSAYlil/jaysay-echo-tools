# 0.1.3 尖端修复资产源

`build_res0_tip_variants.py` 只生成 res0 索引 001–031 的模型、底图和发光图，作为发布前候选。普通镐底图、16 帧发光、模型基准与旧版对照全部从固定发行包 `jaysay-echo-tools-0.1.2.jar` 读取；生成前校验 SHA-256 为 `7312AE7B54F3DAD998815B7C7BD601B65DB1BED23A21CC7AA8448E40E082F495`。它只调用 0.1.2 的纯图片/模型组合函数，不调用旧生成器入口，不覆盖历史源目录。

`artwork/validation/v0.1.3/artagentmask.png` 是 64×64 RGBA 替换遮罩。alpha255 区域为多边形 `[(8,12),(14,11),(20,13),(25,16),(25,20),(21,24),(14,25),(9,22),(7,17)]`，共 203 个 texel；它包含源图透明坐标，用于擦除旧尖端残影。mask 内逐 RGBA texel 使用普通 32×32 底图和每个 32×32 发光帧的最近邻 2×采样，mask 外沿用相同索引的 0.1.2 图像。遮罩与四个强化模块的 tier texel 不相交。

```powershell
& 'C:\Users\<user>\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' 'artwork\source\approved-reference-oct03-64-v0.1.3\build_res0_tip_variants.py'
```

候选写入 `artwork/validation/v0.1.3/candidate/assets/echopickaxe/`。白/暗背景六态图和三态聚焦图写入同一验证目录。生成只更新候选文件，不复制到 `src`。
