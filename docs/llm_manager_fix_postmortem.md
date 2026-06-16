# LLM Manager 部署修复过程与踩坑记录

> 时间跨度: 2026-06-15 09:00 ~ 2026-06-16 14:57
> 总 commit 数: 50+（含调试 commit）
> 最终有效 commit: **10** | 可清理无效 commit: **40+**

---

## 一、问题链路（5层，逐步揭露）

| 层级 | 现象 | 根因 | 引入 | 修复 commit |
|------|------|------|------|------|
| 第1层 | `/llm-manager/*` 全部 404 | `cors_origins` 变量删除但引用残留 → `create_app()` 崩溃 | `cbb8169` (6/12 安全加固) | `089ccc8` |
| 第2层 | API 请求失败 500 | 生产模式直接注册路由，跳过子应用 startup → `app.state.db_manager` 未初始化 | Phase 3 架构改造 | `e3c21bc` |
| 第3层 | `/llm-manager` 与 `/llm-manager/` 死循环 | Starlette mount 307 + 自定义 302 互跳 | Starlette 版本行为变化 | `ff8aff0` + `bbc206a` |
| 第4层 | 页面无样式（完全裸布局） | `<style>` 块整块删除后空 `{}` 规则覆盖 `main.css` 组件定义；脚本路径 `../shared/` 在 `/llm-manager/` 下解析失败 | Dockerfile sed 操作 | `67c3d1a` + `cc89b0e` |
| 第5层 | Tab 纵向、配置管理不自动加载、模型配置面板失效 | `nav-tabs` 等组件样式只在 `index.html <style>` 块定义，未迁移到 `styles/main.css`；JS 脚本相对路径 `../shared/` 在生产路径下 404 | index.html 设计缺陷 | `cc89b0e` |

---

## 二、修复全程时间线

### Phase 1: 紧急救火（6/15 09:00~12:35）— 13 commits

#### 第1波：StaticFiles 路由实验（09:00~09:16）
```
3491593 -> 17d1bf0 -> 20a4d79 -> 32dec96 -> 379a622 -> 85c0351
```
- **踩坑**：在子应用 mount 失败（第1层）未排查的情况下，去修静态文件路由
- **结果**：无效，根本问题未解决

#### 第2波：redirect 死循环修补（11:25~11:41）
```
c4e018e -> ad2d556 -> ff8aff0
```
- **结果**：修复了第3层，但第1层 cors_origins 仍在崩溃

#### 第3波：import 修复 + 真正根因（11:42~12:35）
```
0e4afc0 -> a4e2192 -> 6efa1fc(merge) -> 089ccc8
```
- `089ccc8`：**真正的第1层修复** — 移除 cors_origins 残留引用

**Phase 1 小结**：9 次尝试、4 小时。教训：应先检查容器日志确认 `create_app` 是否成功，而不是先修外围路由问题。

---

### Phase 2: 架构改造——Vite + Tailwind 离线编译方案（6/16 09:47~11:11）— 11 commits

目标：解决内网无法访问 CDN Tailwind 的问题

```
d708511 -> 878774a -> 38dee56 -> e157bd2 -> 6be270e -> 4e12c55
-> e77c93d -> d924966 -> 213d929 -> 0633b11 -> bdde44b -> 58e47cb
```

**核心踩坑**（导致全部无效）：
1. `node_modules/.bin/vite` 权限 `0644`（Windows 复制到 Linux volume 权限丢失），`npm run build` 静默失败
2. Vite `outDir: '../static'` 在 WORKDIR `/build-llm` 下输出到 `/static/`，但历史 COPY 路径写的是 `/build-llm/static/`
3. `--content` CLI 参数会**覆盖** `tailwind.config.js` 的 content 配置（导致扫描范围丢失）
4. Tailwind JIT 无法扫描 JS 字符串模板里的动态 class（`innerHTML += '<div class="...">'`）

**Phase 2 小结**：11 次迭代，全部失败。最终发现 CVM 有外网，短期改用 CDN 绕过。

---

### Phase 3: 清理 + 旧架构修复（6/16 12:00~12:30）— 5 commits

| Commit | 内容 | 有效 |
|--------|------|------|
| `bbc206a` | 清理 static/ 污染（569k行 node_modules 被意外 commit） | ✅ |
| `9693c46` | catch-all 路由缺 HTTPException 导入（500 修复） | ✅ |
| `e9f7a0f` | Dockerfile 简化：删 tailwindcss 编译步骤，CDN 模式 | ✅ |
| `e3c21bc` | 生产模式 startup 事件初始化 `app.state.db_manager`（修复第2层） | ✅ |

---

### Phase 4: 离线方案正确实现（6/16 12:30~14:15）— 14 commits

重新实现离线 Tailwind 编译，修复了 Phase 2 的所有踩坑：

| Commit | 内容 | 有效 |
|--------|------|------|
| `6aab2b0` | 统一修复所有部署方案的 tailwind/sed 路径（scandir/sed目标都错了） | ✅ |
| `6985942` | `.dockerignore` 排除 `node_modules/`（根因：Windows node_modules 在 Linux 下损坏） | ✅ |
| `3d05725` | tailwindcss 和 sed 目标统一为 `assets/index.html`（Vite 真正产物位置） | ✅ |
| `cc86e18` | `chmod` 和 `npm run build` 合并到同一 RUN 层（跨层 chmod 不生效） | ✅ |
| `0282342` | 不用 `--content` CLI 参数，让 tailwind.config.js 的 content 生效 | ✅ |
| `c8327d0` | `styles/main.css` 加 `@layer utilities` 显式保留动态 class | ✅ |
| `67c3d1a` | 删 `<style>` 整块（空 `{}` 覆盖 main.css）+ CSP 移除 localhost:8200 | ✅ |
| `c9783a5` | 所有部署方案的 sed 补充删除 CSP 硬编码 localhost | ✅ |
| 调试 commit | `94df750` `20a4ef5`（加 echo/ls 调试）`8d09b56`（safelist 方案，过大被回退） | ❌ |

---

### Phase 5: UI 问题修复（6/16 14:15~14:57）— 1 commit

| Commit | 内容 | 有效 |
|--------|------|------|
| `cc89b0e` | 三个 UI 问题一次性修复：① Tab 横向（`nav-tabs` 等迁移到 main.css）；② 加载中自动刷新（脚本路径改为 `/llm-manager/` 绝对路径）；③ 参数配置面板（同上） | ✅ |

---

## 三、最终方案架构

```
开发模式 (DEV_MODE=true):
  vite dev server (:3001) ──→ frontend/index.html + CDN Tailwind ✅

生产模式 (DEV_MODE=false, default):
  Docker Stage 1: npm install → npm run build → tailwindcss 编译
    ├── index.html <style> 整块删除（避免空规则覆盖）
    ├── CDN script 替换为 /llm-manager/assets/main.css
    ├── localhost:8200 从 CSP 移除（适配任意域名）
    └── scripts/ shared/ 复制到 /static/
  Runtime: main.py catch-all 路由 serve static/* 文件
    ├── startup 事件初始化 app.state.db_manager
    └── /llm-manager/{r:path} 提供所有静态资源
```

**关键设计决策**：
- `styles/main.css` 的 `@layer components` 包含所有组件样式，替代 `index.html <style>` 块
- 脚本路径使用绝对路径 `/llm-manager/scripts/main.js`，不依赖相对路径解析
- `styles/main.css` 的 `@layer utilities` 显式声明 JS 动态 class，绕过 Tailwind JIT 扫描限制

---

## 四、有效 commit 清单（按时间顺序）

| # | Hash | 说明 | 层级 |
|---|------|------|------|
| 1 | `089ccc8` | cors_origins 残留引用（第1层根因） | 1 |
| 2 | `ff8aff0` | 移除 sub-app mount 死循环 | 3 |
| 3 | `bbc206a` | 清理 static/ 污染 + .gitignore | 基础 |
| 4 | `9693c46` | catch-all 路由 HTTPException 导入 | 3 |
| 5 | `e9f7a0f` | Dockerfile 简化（过渡版） | 2 |
| 6 | `e3c21bc` | startup 初始化 db_manager（第2层） | 2 |
| 7 | `6aab2b0` | 统一 tailwind/sed/route 路径 | 4 |
| 8 | `6985942` | .dockerignore 排除 node_modules | 4 |
| 9 | `3d05725`→`cc86e18`→`0282342`→`c8327d0`→`67c3d1a`→`c9783a5` | 离线 Tailwind 完整实现链 | 4 |
| 10 | `cc89b0e` | UI 三问题修复（Tab/加载/面板） | 5 |

---

## 五、无效 commit 评估（是否可清理）

### 结论：**不建议删除，建议保留历史**

**原因**：
1. 这些 commit 已推送到工蜂（`origin`）和 GitHub（`github`）两个远端，删除会造成历史不一致
2. `git rebase -i` 或 `git filter-branch` 删除中间 commit 会重写所有后续 commit hash，破坏现有的引用和 tag
3. 这些 commit 是调试过程的真实记录，具有一定的文档价值

**可选的轻量化操作**（不修改 hash）：
```bash
# 如果需要干净历史，可以在新分支上 squash：
git checkout -b main-clean
git merge --squash main
git commit -m "feat: LLM Manager 完整修复（详见 docs/llm_manager_fix_postmortem.md）"
# 注意：这会创建新分支，不覆盖原 main
```

**无效 commit 分组（共 40+ 个）**：

| 类型 | Commits | 说明 |
|------|---------|------|
| 静态文件路由实验 | `3491593 17d1bf0 20a4d79 32dec96 379a622 85c0351 c4e018e ad2d556` | Phase 1 方向错误的尝试 |
| import 修复被覆盖 | `0e4afc0 a4e2192` | 后续被更完整的修复取代 |
| Docker tailwind 失败尝试 | `d708511 878774a 38dee56 e157bd2 6be270e 4e12c55 e77c93d d924966 213d929 0633b11 bdde44b` | Phase 2 全部失败 |
| 调试 commit | `94df750 20a4ef5` | 仅用于 debug，echo/ls 调试代码 |
| safelist 方案（被回退） | `8d09b56` | 生成 7MB CSS，规模过大 |
| 中间合并 | `087f311 6efa1fc` | 自动 merge commit |
| 过渡方案被取代 | `58e47cb bdde44b 0633b11` | 方向对但最终方案不同 |

---

## 六、核心教训

| 教训 | 说明 |
|------|------|
| **先检查日志，再修代码** | Phase 1 花 4 小时修路由，实际问题在 `create_app` 崩溃，容器日志一眼就能看到 |
| **Docker 路径用绝对路径** | `../static/` 相对路径 = `/static/`，与 `COPY /build-llm/static/` 是两个不同目录 |
| **Tailwind `--content` 参数会覆盖 config** | 应在 `tailwind.config.js` 配置 content，不用 CLI 参数 |
| **Windows→Linux 跨平台 node_modules 损坏** | volume mount 或 git 同步的 node_modules 在不同 OS 下损坏，`.dockerignore` 排除后重装 |
| **`<style> @apply` 的生产陷阱** | CDN Tailwind 在浏览器展开 `@apply`，但生产模式删掉 CDN 后，需要把这些 `@apply` 先编译成 CSS |
| **相对路径在 SPA 中的陷阱** | `../shared/` 在 `/llm-manager/` 路径下解析为 `/shared/`（不存在），始终用绝对路径 |

---

## 七、数据

| 指标 | 值 |
|------|-----|
| 总耗时 | ~2天（6/15 09:00 ~ 6/16 14:57） |
| 总 commit 数 | ~50 |
| 有效 commit | ~10（20%） |
| 无效 | ~40（80%） |
| 最终 main.css | 29.5KB（含完整组件 + 动态 utility） |
| 最终方案特性 | 完全离线可用、无 CDN 依赖、UI 与开发环境一致 |
