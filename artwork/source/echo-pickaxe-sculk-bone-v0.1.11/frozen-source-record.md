# 0.1.11 冻结来源记录

- 唯一用户指定参照：`user-selected-reference.png`，SHA-256 `451476DBE5AB5AF151BF6A829A9B09EC8E7873B7F6638CAAA7DBC95CE4C71ACF`。
- 64px 全强化参照：`approved-reference-normalized64.png`，SHA-256 `DF9D2F90A3E1BE1CA03B065BAB73D42A371231B1B46C9FCB847A3629EDA68097`。v095 候选纹理与其像素完全一致。
- 固定输入包：`jaysay-echo-tools-0.1.10.jar`，SHA-256 `24E7807050FDB26C2A1C21F6854E9F391F9DAF42E86DBA8AB05A59D0546D20C0`。
- 重绘器 `draft_user_reference_native64.py` SHA-256 `2ECA1106E157BB84BBE6BD118E0758B7FBA52FC72E6CEE74BBA16039E1B15F6A`；候选生成器 `build_reference_candidate.py` SHA-256 `64F75FEB40775A1E4ABBE11F179DDEC0F1E02D31FD02C21125693E94C7891A55`。
- 旧普通镐来源只读取 v004 的 alpha 恢复弯钩外形；不读取旧 RGB、亮度或材料分类。共振 0 显示青黑细切面、窄青裂纹和骨质刃；共振等级大于 0 时由批准的红部件替代骨刃。分频 0 显示原生青黑右刃与骨质刃；分频等级大于 0 时先从裸底层移除骨质，再叠批准的紫色部件。ext 0 使用深青圆核和三处分离骨扣；ext 大于 0 保持批准的绿色部件。骨质像素不发光。
- 被用户否定的 `sculk-bone-imagegen-reference.png` 及其 `imagegen-prompt.md` 仅作为历史记录保留，明确标记为 rejected；不进入生成器、候选或发布输入。当前参照是用户指定的 `user-selected-reference.png`。
- 冻结资源映射 `v0.1.11-resource-map.json` SHA-256 `BDE0DA7921BF3F070B2A6AD0DDD7F22440BA9B285A5C569CA3A9252ED48BF39E`；候选清单 `v0.1.11-candidate-manifest.json` SHA-256 `944B6837CC5085692E9D1DF05DBDAC8C0CE121AD7E109C07B8948952D30D74A6`。资源候选位于 `artwork/validation/v0.1.11/candidate/`，覆盖升级索引 001–095 的 base、glow、model；普通 quartet、metadata、其他物品、数据和 Java 不在候选内。
- 编辑 mask `v0.1.11-base-edit-mask.png` SHA-256 `F2D6BFA50D7BA886336D6C8FC184407ADE9AC9BF30EFEC5E426F993B5CC20C69`；glow mask `v0.1.11-glow-mask.png` SHA-256 `A01AE9783B942C22B8EF50C234A058333DA18956EF37186ED92F42CA7C8E84E1`；冻结 v004 underlay `v0.1.11-frozen-underlay-v004.png` SHA-256 `90A2CE3230EFA89C870FB39D462C1749D9D339764AD770F38A65FB4B7E159665`。
- 重现：从项目根目录依次运行 `python artwork/source/echo-pickaxe-sculk-bone-v0.1.11/draft_user_reference_native64.py` 与 `python artwork/source/echo-pickaxe-sculk-bone-v0.1.11/build_reference_candidate.py`。只读部署预检为 `python artwork/source/echo-pickaxe-sculk-bone-v0.1.11/deploy_reference_candidate.py`；当前未执行 `--apply`，生产资源仍为 0.1.10。
