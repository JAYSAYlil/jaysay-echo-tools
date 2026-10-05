# 上传材料包（CurseForge + Modrinth）

**版本速查**

| 项 | 值 |
| --- | --- |
| 正式包 | `jaysay-echo-tools-0.3.2.jar`（在项目根目录，`build/libs/` 里同名文件一致） |
| 大小 | 9,300,655 字节 |
| SHA-256 | `FEF68695D80A2C46390CB4D3AE2F6B01C18A1FDEE0A4822E71B4C2219F951193` |
| 版本号 | `0.3.2`（Release） |
| Minecraft | `1.20.1` |
| 加载器 | `Forge`（开发与验证用 47.4.21） |
| 环境 | 客户端 + 服务端（**两端都要装同一版本**，网络协议 4） |
| 名称 | `JaySay's Echo Tools` |
| 许可 | All Rights Reserved **+ 允许整合包收录** |

---

## 0. 文件用在哪里（一张表看懂）

| 文件 | 用到哪 |
| --- | --- |
| `jaysay-echo-tools-0.3.2.jar` | 两个平台的**文件上传** |
| `publish/curseforge-icon-400.png` | **CurseForge** 项目头像 |
| `publish/modrinth-icon-256.png` | **Modrinth** 项目图标（50 KB，限 256 KB 以内） |
| `publish/logo-128.png` | 仅记录用；128 图标已在 jar 内（游戏内模组列表显示） |
| `publish/modrinth/gallery/00-banner.png` | Modrinth **特色图**（画廊里设 featured）；CF 画廊第一张 |
| `publish/modrinth/gallery/01…07-*.png` | 两个平台画廊（CF 用 `publish/curseforge/gallery/` 同名副本） |
| `publish/modrinth/body.md` | Modrinth **正文**（英文 + 中文小节，整段复制） |
| `publish/modrinth/summary.txt` | Modrinth **Summary** 一句话 |
| `publish/modrinth/meta.json` | 字段备查（分类、许可证 ID、链接等） |
| `publish/curseforge/description-en.md` | CurseForge **英文描述** |
| `publish/curseforge/description-zh.md` | CurseForge **中文描述**（若界面支持多语言描述） |
| `publish/curseforge/summary.txt` | CurseForge **Summary** |
| `publish/curseforge/changelog-0.3.2-en.md` / `-zh.md` | 两个平台的**版本 changelog** |

---

## 1. Modrinth（约 6 分钟）

### 1.1 建项目

打开 <https://modrinth.com> → 右上头像 → **Create a project** → 类型选 **Mod**。逐字段：

| 字段 | 填什么 |
| --- | --- |
| Name | `JaySay's Echo Tools` |
| Slug / URL | 保持自动生成的 `jaysay-echo-tools`（**已确认未被占用**） |
| Summary | 复制 `publish/modrinth/summary.txt` 里那一句 |
| Project type | `Mod` |
| Categories | 勾 **Equipment**、**Adventure**、**Utility**、**Game Mechanics** |
| License | 下拉选 **All Rights Reserved**（其内部 ID 即 `LicenseRef-All-Rights-Reserved`） |
| Environment | **Client** 与 **Server** 都勾（两边都必须安装） |
| Source code URL | `https://github.com/JAYSAYlil/jaysay-echo-tools` |
| Issues URL | `https://github.com/JAYSAYlil/jaysay-echo-tools/issues` |
| Description / Body | 整个文件内容复制粘贴：`publish/modrinth/body.md` |
| Icon | 上传 `publish/modrinth-icon-256.png` |

### 1.2 上传版本

项目页 → **Versions** → **Create version**：

| 字段 | 填什么 |
| --- | --- |
| Version number | `0.3.2` |
| Name | `0.3.2`（可留空，自动用版本号） |
| Release channel | `Release` |
| Loaders | 勾 **Forge** |
| Game versions | 勾 **1.20.1** |
| Dependencies | 不需要（无前置模组） |
| File | 上传 `jaysay-echo-tools-0.3.2.jar` |
| Changelog | 复制 `publish/curseforge/changelog-0.3.2-en.md` |

### 1.3 画廊

项目页 → **Gallery** → 按 `00 → 07` 顺序上传 `publish/modrinth/gallery/` 里的图，
把 **00-banner.png 设为 Featured**（这就是项目页顶部那张宽幅图）。
每张图的标题/描述在下面第 4 节。

### 1.4 提交

检查无误 → **Submit for review** → 等审核（通常几小时到 1 天）。

---

## 2. CurseForge（约 5 分钟）

### 2.1 建项目

打开 <https://authors.curseforge.com/>（用 CurseForge 账号登录）→ **Create Project** → Game `Minecraft` / Project type `Mods`：

| 字段 | 填什么 |
| --- | --- |
| Project name | `JaySay's Echo Tools` |
| Summary | 复制 `publish/curseforge/summary.txt` |
| Category | `Equipment`、`Adventure` |
| Game version | `1.20.1` |
| Mod loader | `Forge` |
| Environment | `Client and Server` |
| License | `All Rights Reserved`，并把**允许整合包收录**设为允许 |
| Avatar | 上传 `publish/curseforge-icon-400.png` |
| Description | 复制 `publish/curseforge/description-en.md`（支持 Markdown；若可加中文描述，用 `description-zh.md`） |

> 界面上措辞可能略有差别（例如 "Include in modpacks" / "Allow distribution in modpacks"），意思一样，勾允许即可。

### 2.2 上传文件

项目页 → **Files** → **Upload File**：

| 字段 | 填什么 |
| --- | --- |
| File | `jaysay-echo-tools-0.3.2.jar` |
| Display name | `0.3.2` |
| Release type | `Release` |
| Game versions | 勾 Minecraft `1.20.1` + Forge `47.4.21` |
| Changelog | 复制 `publish/curseforge/changelog-0.3.2-en.md` |

### 2.3 画廊

项目页 → **Gallery** → 上传 `publish/curseforge/gallery/` 里的 8 张图（顺序同上，第一张就是门面图）。

### 2.4 提交

新项目和文件都会进审核（通常几小时到 1–2 天）。

---

## 3. 容易踩的坑

1. **Modrinth 的特色图不是单独字段**：它是画廊里 `featured=true` 的那张，所以务必先传 `00-banner.png` 并勾 featured，否则项目页顶部会空着。
2. **图标规格**：CF 要 400×400，Modrinth 要 256×256 且 ≤256 KB——用表里给的两个文件，别混用。
3. **许可两边都选 All Rights Reserved**；CF 还要额外勾"允许整合包"，Modrinth 不需要（LICENSE 文件里已写明允许整合包）。
4. **两端都要装**：Environment 一定勾 Client + Server，否则玩家以为服务端不用装，进服会因协议不匹配被拒。
5. **正文语言**：Modrinth 只有单一正文，我们的 `body.md` 已是"英文正文 + 中文小节"；CF 若支持多语言描述就中英各一份。
6. **别用 0.3.0 / 0.3.1 的 changelog**：那两个版本没公开发布，0.3.2 的 changelog 已包含它们的内容（旧文件已挪到 `publish/archive/changelogs/`）。
7. 上传前确认 jar 就是上面那串 SHA-256：`Get-FileHash jaysay-echo-tools-0.3.2.jar`。

---

## 4. 画廊图的标题与描述（复制用）

顺序即上传顺序，标题/描述两个平台都能填。

| 文件 | 标题 | 描述 |
| --- | --- | --- |
| 00-banner.png | JaySay's Echo Tools | A sculk-forged pickaxe that senses nearby ores and guides you with a luminous echo trail. |
| 01-dark-room-in-hand.png | Glows in the dark | The emissive parts stay lit with no shader pack and no OptiFine required. |
| 02-creative-tab-a.png | Its own creative tab | Pickaxe, smithing template, Echo Crystal and nine upgrade crystals. |
| 03-creative-tab-b.png | Upgrade crystals | Four upgrade paths, three levels each, applied on a smithing table. |
| 04-white-background.png | Clean pixel art | True 64px sprites with a fixed binary transparency mask. |
| 05-first-person-max-tier.png | Fully upgraded | Resonance II, Frequency III, Tuning I and Extension III on one pickaxe. |
| 06-upgrade-comparison.png | Every upgrade level | Base and all 95 upgrade models, side by side in the inventory. |
| 07-held-in-context.png | In hand | First- and third-person scales tuned for the 64px model. |

---

## 5. 需要换素材时

```powershell
.\tools\publish_modrinth.ps1 -Token "<mrp_...>" -DryRun   # 只想核对字段时用（不需要 token 也能跑到这里）
python publish/make_icon.py     # 重新生成图标（400 / 256 / 128）
python publish/make_banner.py   # 重新生成特色图与画廊副本
```
