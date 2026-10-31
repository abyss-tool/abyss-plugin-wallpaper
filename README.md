<div align="center">

# 🖼 动态壁纸引擎

### WallpaperService 引擎：与主壳液态玻璃同源视觉的动态壁纸工坊。

[![Plugin CI](https://github.com/Ultra-Guru/abyss-plugin-wallpaper/actions/workflows/plugin-ci.yml/badge.svg?branch=main)](https://github.com/Ultra-Guru/abyss-plugin-wallpaper/actions/workflows/plugin-ci.yml)
![Version](https://img.shields.io/badge/version-0.1.0-7EC8FF)
![Category](https://img.shields.io/badge/分类-桌面-4FD8EB)
![Status](https://img.shields.io/badge/状态-框架预览-1A222D)

</div>

---

> 深渊工具（[Ultra-Guru/Abyss-Tools](https://github.com/Ultra-Guru/Abyss-Tools)）的桌面类大插件 —— 本仓库为**插件框架期骨架**：manifest / 补丁通道 / CI 门禁已就绪，插件本体按路线图实现。

## 插件信息

| 字段 | 值 |
| --- | --- |
| 插件 ID | `abyss-plugin-wallpaper` |
| 分类 | 桌面（desktop） |
| 版本 | v0.1.0（框架预览） |
| 最低宿主 | App v0.1.0 / HOST_API v1 |
| 仓库 | [Ultra-Guru/abyss-plugin-wallpaper](https://github.com/Ultra-Guru/abyss-plugin-wallpaper) |
| 补丁通道 | [`patches/index.json`](patches/index.json) |

## 权限需求

- 无静态权限（运行时按需申请）


## 安装

经深渊工具主壳「导航 → 插件 → 插件中心」安装（安装 AP 流水线：下载 →
SHA-256 校验 → 安装网关）。**APK 资产自 v0.2 发布流水线起发布** —— 当前
仓库发布 manifest 与补丁通道骨架。

## 补丁更新

- 通道：本仓库 `patches/index.json`（abyss-plugin-patches-v1）
- 引擎：主壳 `abyss-patch-v1` 数据补丁（下载 → SHA-256 → 备份 → 应用 → 失败回滚）
- 插件详情页实时展示补丁时间线

## 路线图

- [ ] v0.2 WallpaperService 骨架
- [ ] v0.3 玻璃材质壁纸
- [ ] v0.4 壁纸工坊市场

## 许可

受限许可（UGRL v1.0）：仅供个人学习与安全研究，禁止再分发与商业使用 —— 见 [LICENSE](LICENSE)。

---

## 补丁发布流水线

数据补丁（abyss-patch-v1）的发布已全自动：

1. **Actions → Patch Release → Run workflow**：填目标版本（如 `0.1.1`）与变更要点（多条用 `;` 分隔）；
2. 流水线自动：打包增量补丁（`tools/make_patch.py` —— 新 manifest 与 changelog 作为载荷，`plugin.json` / `CHANGELOG.md` 同步升版）→ 创建 `v*` Release 并上传 zip 资产（`tools/publish_patch.py`）→ 滚动 `patches/index.json` 补丁通道；
3. 宿主侧插件详情页「下载并应用补丁」即可增量消费：下载 → SHA-256 校验 → 备份 → 应用 → 失败自动回滚；
4. [Abyss-Plugins](https://github.com/Ultra-Guru/Abyss-Plugins) 索引聚合（每日 / 手动 Sync Index）自动把新版本汇入 `plugins.json`。
