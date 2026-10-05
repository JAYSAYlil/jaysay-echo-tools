# 上传指南：CurseForge + Modrinth

目标版本 **0.3.2**　正式包 `jaysay-echo-tools-0.3.2.jar`（9,300,655 字节）
SHA-256 `FEF68695D80A2C46390CB4D3AE2F6B01C18A1FDEE0A4822E71B4C2219F951193`

## 一、物料总表

| 物料 | 文件 | 用于 |
| --- | --- | --- |
| 项目图标 400×400 | `publish/curseforge-icon-400.png` | CurseForge 头像 |
| 项目图标 256×256 | `publish/modrinth-icon-256.png` | Modrinth 图标（限 256 KB，实际 50 KB） |
| jar 内图标 128×128 | `publish/logo-128.png`（已在 jar 内） | 游戏内模组列表 |
| 宽幅特色图 1280×640 | `publish/modrinth/gallery/00-banner.png` | Modrinth 项目页顶部；CF 画廊第一张 |
| 画廊截图 ×7 | `publish/modrinth/gallery/01..07-*.png` | 两个平台的画廊（CF 另有同名副本在 `publish/curseforge/gallery/`） |
| 英文简介（长） | `publish/curseforge/description-en.md` | CF 描述 / Modrinth 正文（已合并进 `publish/modrinth/body.md`） |
| 中文简介（长） | `publish/curseforge/description-zh.md` | CF 中文描述；Modrinth 正文末尾的中文小节 |
| Modrinth 正文 | `publish/modrinth/body.md` | 英文正文 + `---` + 中文说明，5,068 字符 |
| 更新日志 0.3.2 | `publish/curseforge/changelog-0.3.2-en.md` / `-zh.md` | 两个平台的版本 changelog |
| 平台字段表 | `publish/PUBLISH-CHECKLIST.md` | CF 建项目/传文件的逐字段对照 |
| Modrinth 元数据 | `publish/modrinth/meta.json` | 自动化脚本读取的全部字段 |
| 图标/特色图生成器 | `publish/make_icon.py`、`publish/make_banner.py` | 需要换风格时重跑 |

## 二、两个平台的关键差异

| | CurseForge | Modrinth |
| --- | --- | --- |
| 项目创建 | 网页，且新项目要过审核 | 网页或 API；可先建**草稿**再补版本 |
| 本机脚本可达性 | ❌ Cloudflare 拦非浏览器请求 | ✅ **完全可达**（实测 200） |
| 上传方式 | 网页手动（以后可接 CI） | 网页手动 **或** 一键脚本全自动 |
| 许可字段 | `All Rights Reserved` + 勾选允许整合包 | `LicenseRef-All-Rights-Reserved` |
| 正文语言 | 支持多语言描述 | 单正文；本仓库用"英文正文 + 中文小节" |
| 图标 | 400×400 | 256×256，≤256 KB |
| 特色图 | 画廊第一张 | 画廊中 `featured=true` 的那张 |

## 三、Modrinth

### 路线 A：一键自动（推荐）

1. 打开 <https://modrinth.com/settings/pats>，创建一个 PAT，勾选：
   **`PROJECT_CREATE`、`PROJECT_WRITE`、`VERSION_CREATE`**
2. 我把 token 写进环境变量或本地文件（不要贴聊天里），然后：

```powershell
.\tools\publish_modrinth.ps1 -Token "<mrp_...>" -DryRun   # 先校验，不发任何请求
.\tools\publish_modrinth.ps1 -Token "<mrp_...>"           # 正式发布
```

脚本会按顺序做：**创建草稿项目**（含图标与正文）→ **上传 0.3.2 版本**（forge / 1.20.1 / release / changelog）→ **逐张上传 8 张画廊图**（banner 标 featured）。
结束后产物在 <https://modrinth.com/mod/jaysay-echo-tools>，你检查无误后点 **Submit for review**（提交审核是人工一步，我不代按）。

已确认：`jaysay-echo-tools` 这个 slug 在 Modrinth 上**尚未被占用**。

### 路线 B：网页手动

1. <https://modrinth.com> 登录 → Create a project → 类型 `Mod`
2. 名称 `JaySay's Echo Tools`、summary 用 `publish/modrinth/meta.json` 里的 `summary`
3. 分类勾 `Equipment`、`Adventure`、`Utility`、`Game Mechanics`
4. 许可选 `All Rights Reserved`；环境勾 Client + Server
5. 正文粘贴 `publish/modrinth/body.md`
6. 上传图标 `publish/modrinth-icon-256.png`
7. 版本页：版本号 `0.3.2`、渠道 `Release`、加载器 `Forge`、游戏版本 `1.20.1`、文件 `jaysay-echo-tools-0.3.2.jar`、changelog 粘贴 `changelog-0.3.2-en.md`
8. 画廊按 `00→07` 顺序上传，把 00 设为 featured

## 四、CurseForge

本机脚本被 Cloudflare 挡（详见 `publish/PUBLISH-CHECKLIST.md` 第六节），走网页：

1. <https://authors.curseforge.com/> 登录 → Create Project → `Minecraft` / `Mods`
2. 字段全部照 `publish/PUBLISH-CHECKLIST.md` 的表格填（名称、summary、分类 Equipment+Adventure、1.20.1、Forge、Client and Server、All Rights Reserved + 允许整合包、图标 400×400、描述英文版）
3. 建好后进 Files → Upload File，传 `jaysay-echo-tools-0.3.2.jar`，版本 `1.20.1` + Forge `47.4.21`，changelog 粘贴 `changelog-0.3.2-en.md`
4. 画廊按 `publish/curseforge/gallery/` 顺序上传（第一张 banner 会被当作门面图）

## 五、以后每次发版

1. 改 `gradle.properties` 的版本 → `验收.bat --smoke` → `验收.bat --install`
2. 生成脱敏快照 → 公开仓库提交 → 打 tag → GitHub Release 附 jar
3. 写新版 `publish/curseforge/changelog-<版本>-en.md` 与 `-zh.md`
4. 更新 `publish/modrinth/meta.json` 的 `version` 段（版本号、文件、changelog 路径）
5. 跑 `tools/publish_modrinth.ps1` 自动发 Modrinth；CurseForge 走网页（或以后接 GitHub Actions）
