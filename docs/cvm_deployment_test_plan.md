# CVM 新部署方案验证测试计划

> CVM 环境：`fjzheng@fjzheng.devcloud.woa.com:36000`，项目路径 `/data/CreditWise`

---

## 一、当前环境

> 2026-07-03 更新（第四轮测试后）：分支已合并至 `main`，认证方案已从标准 `Basic` 升级为自定义 `CWAuth`（详见第四轮测试记录），CVM当前以 **Docker在线多用户模式**（`docker compose up -d`，`restart: unless-stopped`）长期常驻运行，作为最终生产状态。

| 维度 | 状态（2026-07-03） |
|------|------|
| Git 分支 | `main`（第四轮测试期间已合并，不再有 `feature/intranet-multiuser` 独立分支） |
| Docker 容器 | `creditwise-api`（Docker在线多用户模式常驻，`restart: unless-stopped`，镜像 `creditwise:latest` ~1.48GB） |
| 端口 | 8200（API+前端） + 8100（文件下载服务） |
| 认证 | 已启用，认证方案为自定义 `CWAuth`（非标准 `Basic`，浏览器不会弹原生登录框，见第四轮测试记录） |
| 用户 | admin, fjzheng（管理员）；sylarswwang, gurayzhang, laughingtan, webberwu（普通用户） |
| 数据 | `llm_manager.db` + `task_manager.db` + `workspace/` + `execution_states/` |
| 其他 | 同主机运行 AI_Trader 项目，端口不冲突 |

<details>
<summary>历史环境状态（第一~三轮测试时，2026-06-12~16，已过时，仅存档）</summary>

| 维度 | 状态 |
|------|------|
| Git 分支 | `feature/intranet-multiuser` (commit `5f38226`，落后 main 7 commits) |
| Docker 容器 | `creditwise-api`（运行 10 天，镜像 `creditwise:latest` 1.5GB） |
| 认证 | 已启用 Basic Auth（标准方案，第四轮测试期间升级为 CWAuth） |

</details>

---

## 二、待验证的新部署脚本

| 脚本 | 验证点 |
|------|--------|
| `deploy_linux.sh` | Docker 在线部署 + 交互式模式选择（单用户/多用户） |
| `deploy_offline.sh` | Docker 离线部署 |
| `deploy_manual.sh` | Linux 非 Docker 手动部署 |
| `service.sh` | Docker 服务管理（启动/停止/重启/状态/日志），从 `.env` 读取 `ENABLE_AUTH` |
| `sync_model_configs.sh` | LLM 渠道配置同步 |

---

## 三、测试步骤

### 测试 0：备份

```bash
cd /data/CreditWise

# 创建备份目录
mkdir -p /data/backup_$(date +%Y%m%d)

# 备份关键文件
cp .env /data/backup/                    # 加密密钥（⚠️ 丢失则渠道 API 密钥不可恢复）
cp -r config/ /data/backup/              # users.yaml（用户密码哈希）
cp llm_manager.db /data/backup/          # LLM 渠道配置数据库
cp task_manager.db /data/backup/ 2>/dev/null

# 停止旧服务
sudo docker-compose -f docker/docker-compose.yml down

# Git 更新到最新 main（含全部新部署脚本）
git fetch origin
git checkout main
git pull origin main
```

---

### 测试 1：Docker 单用户模式（`deploy_linux.sh` 选项 1）

```bash
./scripts/deploy_linux.sh
# 选择 [1] 单用户模式
```

| 验证项 | 命令/方法 | 预期 |
|--------|----------|------|
| 端口监听 | `ss -tlnp \| grep -E '8200\|8100'` | 两个端口 LISTEN |
| 健康检查 | `curl -s http://localhost:8200/health` | `{"status":"healthy"}` |
| 无需认证 | 浏览器打开 `http://21.214.50.220:8200` | 直接进入，无登录弹窗 |
| ENABLE_AUTH | `grep ENABLE_AUTH .env` | `ENABLE_AUTH=false` |
| 自检功能 | 看脚本输出 | 端口检查 ✓、磁盘检查 ✓、Docker 检查 ✓ |

**验证通过后执行**：
```bash
./scripts/service.sh stop
```

---

### 测试 3：离线 Docker 部署（`deploy_offline.sh`）

**前置**：先在外网机器执行 `prepare_offline.sh` 生成离线包，或直接用已构建的镜像（测试 1 已生成了 `creditwise:latest`）。

```bash
cd /data/CreditWise
sudo docker compose -f docker/docker-compose.yml down

# 无离线包时，用已构建的本地镜像模拟离线部署
./scripts/deploy_offline.sh
# 选择 [2] 内网多用户
```

| 验证项 | 预期 |
|--------|------|
| 离线包检测 | 如无 `offline_bundle/`，提示先准备离线包 |
| 镜像加载 | 如离线包中有镜像，成功加载 |
| Docker 环境检查 | ✓ |
| 端口检查 | 8200+8100 可用 |
| 磁盘检查 | ≥2GB |
| 服务启动 | 健康检查通过 |

---

### 测试 4：非 Docker 手动部署（`deploy_manual.sh`）

```bash
cd /data/CreditWise

# 停止 Docker 容器释放端口
sudo docker compose -f docker/docker-compose.yml down

# 确保系统依赖已安装
sudo apt-get install -y libgbm1 libnss3 libatk-bridge2.0-0 libxkbcommon0 2>/dev/null

./scripts/deploy_manual.sh
# 选择 [2] 内网多用户
```

| 验证项 | 命令/方法 | 预期 |
|--------|----------|------|
| Python 版本 | 看脚本输出 | ≥ 3.10 |
| Node.js 版本 | 看脚本输出 | ≥ 18（如需前端构建） |
| 系统库检查 | 看脚本输出 | kaleido/Chromium 依赖已安装 |
| 端口检查 | 看脚本输出 | 8200+8100 可用 |
| venv 创建 | `ls .venv/bin/python3` | 存在 |
| pip 依赖安装 | 看脚本输出 | 27 个包安装成功 |
| 前端构建 | 看脚本输出 | Next.js build 成功（如有 Node） |
| 密钥生成 | `grep LLM_MANAGER_ENCRYPTION_KEY .env` | 已生成 |
| ENABLE_AUTH | `grep ENABLE_AUTH .env` | ENABLE_AUTH=true |
| 服务启动 | `curl -s http://localhost:8200/health` | `{"status":"healthy"}` |
| 认证生效 | `curl -s -o /dev/null -w '%{http_code}' http://localhost:8200/v1/chat/completions` | 401 |
| 日志 | `tail logs/server.log` | 无 ERROR |

**测试完成后恢复 Docker**：
```bash
kill $(cat .app_pids.txt) 2>/dev/null
rm -f .app_pids.txt
cp /data/backup_20260612/.env .env
cp /data/backup_20260612/config/users.yaml config/
echo "ENABLE_AUTH=true" >> .env
sudo bash scripts/service.sh start
```

---

## 三、测试 5：清理与恢复

```bash
cd /data/CreditWise
sudo bash scripts/service.sh stop

# 恢复备份配置
cp /data/backup_20260612/.env .env
cp /data/backup_20260612/config/users.yaml config/
echo "ENABLE_AUTH=true" >> .env

# 重新构建并启动（使用最新代码）
git pull origin main
sudo bash scripts/deploy_linux.sh  # 选 [2] 内网多用户
```

---

## 四、⚠️ 关键注意事项

### 加密密钥与数据库兼容性

```
旧部署: 旧密钥 → 旧 llm_manager.db 中的 API 密钥可解密 ✅

新脚本部署: 新密钥 → 旧 llm_manager.db 中的 API 密钥无法解密 ❌
              ↓
              渠道 API 调用失败，LLM 不可用

正确流程: 新脚本部署 → 恢复旧 .env（含旧密钥）→ 渠道正常 ✅
         或: 新脚本部署 → 重新同步渠道配置（sync_model_configs.sh）→ 渠道正常 ✅
```

### 数据保留策略

| 文件 | 保留 | 原因 |
|------|:--:|------|
| `.env` 中的加密密钥 | ✅ | 旧渠道 API 密钥用此密钥加密 |
| `config/users.yaml` | ✅ | 含真实 bcrypt 密码哈希 |
| `llm_manager.db` | ✅ | 渠道配置、模型参数 |
| `task_manager.db` | 可选 | 历史任务记录 |
| `workspace/` | 可选 | 用户上传的数据文件 |
| `execution_states/` | 可选 | 任务执行中间状态 |

### 验证通过标准

> 以下为第一~三轮测试（2026-06-12~16）的历史清单；第四轮（2026-07-03）四种部署方式全部通过的清单见下方。

- [x] 测试 1：Docker 单用户模式 — 无认证可访问，端口自检通过
- [x] 测试 2：Docker 多用户 + service.sh — 401 保护，从 .env 读配置，6 用户正常
- [x] 测试 3：离线 Docker 部署 — 端口/磁盘自检通过，服务健康（Docker Py3.12 wheels）
- [x] 测试 4：非 Docker 手动部署 — Python/node 依赖检查，pip 安装，服务启动，401 保护
- [x] 全部模式：8200+8100 双端口正常监听
- [x] 全部模式：`curl /health` 返回 `{"status":"healthy"}`
- [x] LLM Manager UI：样式正常，Tab 横向，数据自动加载，模型配置面板可用（第二轮 6/16）

### 第四轮（2026-07-03）验证通过标准

- [x] 测试1：Docker单用户模式 — 无认证访问，浏览器验证通过
- [x] 测试2：非Docker手动部署（多用户） — CSS/DEV_MODE/PEP695 三个bug修复后全部通过，浏览器验证通过
- [x] 测试3：Docker离线部署 — 完整走通"构建→打包→解压→加载→部署"全流程，`.next`误打包修复后重新完整验证一遍
- [x] 测试4：Docker在线多用户部署（CVM最终常驻状态） — 真实6账户迁移，浏览器人工验证登录/退出登录切账号/`/llm-manager`页面全部通过
- [x] 生产模式退出登录无法切换账号（架构级问题）— 已通过CWAuth认证方案改造根治
- [x] 账户锁定并发竞态+误锁定 — 已修复并验证（并发同凭证不误锁，不同凭证暴力破解防护不受影响）
- [x] LLM Manager 403无权限提示 — 已修复，非admin用户看到明确提示而非卡在加载中

---

## 五、实测结果记录

### 第一轮测试（2026-06-12 | 代码版本 `0557956`）

| 测试 | 结果 | 耗时 | 关键发现 |
|------|:--:|------|------|
| 测试 1：Docker 单用户 | ✅ | ~2min | 环境自检（端口/磁盘/Docker）全部通过 |
| 测试 2：Docker 多用户 + service.sh | ✅ | ~1min | `.env` 中 `ENABLE_AUTH=true` 被正确读取；401 保护生效 |
| 测试 3：离线 Docker（清缓存） | ✅ | ~3min | 发现并修复：①Docker Compose v1→v2 ②Py3.11→3.12 wheel 版本匹配 |
| 测试 4：非 Docker 手动部署 | ✅ | ~3min | Node.js 未安装时正确跳过前端构建；kaleido 系统库缺失警告正常 |

### 第一轮测试中修复的问题

| 问题 | 修复 | Commit |
|------|------|--------|
| CVM 上 `docker-compose` v1 命令不存在 | 3 个脚本 `docker-compose` → `docker compose` + 移除 compose.yml `version` 字段 | `df2ee15` |
| `prepare_offline.sh` 用宿主 Python 3.11 下载 wheel，Docker 镜像 Python 3.12 不兼容 | 改用 `docker run python:3.12-slim pip download` | `0557956` |
| Dockerfile `COPY \|\| true` 语法无效 | 改用 `.offline_wheels/` 空目录 + `OFFLINE_MODE` build-arg | `d5d549b` → `e2942fe` |

---

### 第二轮测试（2026-06-16 | 代码版本 `cc89b0e`）

> 重新测试背景：LLM Manager 部署修复（含 Tailwind 离线编译、API 500、UI 三问题）

| 测试 | 结果 | 验证方法 | 关键发现 |
|------|:--:|------|------|
| **测试1：Docker 多用户模式** | ✅ | `curl /health` → 200；`POST /v1/chat` 无认证 → 401；`/llm-manager/` → 200；`/llm-manager/api/manage/channels` → 200 | `ENABLE_AUTH` 需通过 `ENABLE_AUTH=true docker compose up` 传入，而非仅写 `.env` |
| **测试3：离线 Docker 逻辑验证** | ✅ | 检查 `deploy_offline.sh` 无 `llm-manager-static/` 时的处理逻辑 | 正确跳过并依赖 Dockerfile Stage1 编译；需重新执行 `prepare_offline.sh` 更新离线包 |
| **测试4：非 Docker 前端编译验证** | ✅ | CVM 无系统级 Node.js，`deploy_manual.sh` `HAS_NODE=false` 正确跳过 | 与预期一致 |
| **LLM Manager UI 验证** | ✅ | 浏览器访问 `fjzheng.devcloud.woa.com:8200/llm-manager/` | 样式正常；Tab 横向排列；数据自动加载；模型配置面板可打开 |

### 第二轮测试发现的问题与修复

| 问题 | 根因 | 修复 Commit |
|------|------|--------|
| LLM Manager 页面 404 | `cors_origins` 残留引用导致 `create_app()` 崩溃 | `089ccc8` |
| API 请求 500 | 生产模式跳过子应用 startup，`app.state.db_manager` 未初始化 | `e3c21bc` |
| 页面无样式（完全裸布局） | `<style>` 空规则块覆盖 `main.css` 组件定义 | `67c3d1a` |
| Tab 纵向排列 | `nav-tabs` 等样式未迁移到 `styles/main.css` | `cc89b0e` |
| 配置管理不自动加载 | 脚本路径 `../shared/` 在 `/llm-manager/` 路径下 404 | `cc89b0e` |
| 模型配置面板失效 | 同上，`model-config.js` 未加载 | `cc89b0e` |
| 离线编译 CSS 不完整 | `--content` CLI 参数覆盖 `tailwind.config.js`；Windows node_modules 在 Linux 损坏 | `6985942` + `0282342` |

### ⚠️ 第二轮测试补充发现

**`ENABLE_AUTH` 传入方式**：`docker-compose.yml` 中 `ENABLE_AUTH=${ENABLE_AUTH:-false}` 要求在执行 `docker compose up` 时通过 shell 环境变量传入，`.env` 文件中的值不会被 docker compose 的 `${VAR:-default}` 语法读取。

正确用法：
```bash
ENABLE_AUTH=true docker compose -f docker/docker-compose.yml up -d
# 或使用 service.sh（从 .env 读取后传给 docker compose）
sudo bash scripts/service.sh start
```

---

### 第三轮测试（2026-06-16 | 代码版本 `b67a479`）

> 测试目标：Windows 非 Docker 一键部署脚本 `deploy_manual.ps1` 端到端测试  
> **注意**：前两轮 CVM 测试仅覆盖了 Linux Docker 和 `deploy_manual.sh`（Linux），`deploy_manual.ps1`（Windows）从未被实际执行过，导致3个语法 Bug 在生产前未被发现。

#### 测试 5：Windows deploy_manual.ps1（单用户模式）

**环境**：Windows 11 + PowerShell Core，项目路径 `C:\Users\fjzheng\portable-dev-env\workspace\CreditWise`

```powershell
cd "C:\Users\fjzheng\portable-dev-env\workspace\CreditWise"
git pull origin main
.\scripts\deploy_manual.ps1
# 选择 [1] 单用户模式
```

| 验证项 | 验证方法 | 预期 |
|--------|----------|------|
| 脚本语法检查 | PowerShell 解析无错误 | 无 ParserError |
| Python 版本检测 | 脚本输出 | Python 3.10+ 检出成功 |
| Node.js 版本检测 | 脚本输出 | Node.js 18+ 检出成功 |
| 端口占用检查 | 脚本输出 | 8200, 8100 可用 |
| 磁盘空间检查 | 脚本输出 | ≥2GB |
| venv 创建 | `Test-Path .venv\Scripts\python.exe` | 存在 |
| pip 依赖安装 | 脚本输出 | 全部安装成功 |
| 前端构建 | `Test-Path demo\chat\dist\index.html` | 存在 |
| .env 生成 | `Test-Path .env` + 含 `LLM_MANAGER_ENCRYPTION_KEY` | 存在且密钥已设置 |
| ENABLE_AUTH 值 | `Select-String 'ENABLE_AUTH' .env` | `ENABLE_AUTH=false` |
| 服务启动 | `curl http://localhost:8200/health` | 200 OK |
| 主界面 | 浏览器 `http://localhost:8200` | 可访问 |
| LLM Manager UI | 浏览器 `http://localhost:8200/llm-manager` | 可访问，样式正常 |

**实测结果**（共 12 轮迭代，最终通过）：

| 轮次 | 结果 | 发现问题 |
|:--:|:--:|------|
| 1 | ❌ | Python `exit(0 if ...)` 三元式被 PS 误解析 |
| 2 | ❌ | Fernet 密钥 `=` 在 `-replace` 中被截断 |
| 3 | ❌ | `-match` 正则中单引号在 git clone 后编码损坏 |
| 4 | ❌ | 中文乱码（`write_to_file` 无 UTF-8 BOM） |
| 5 | ❌ | PS 5.1 不兼容 `?.` `??` 运算符 |
| 6 | ❌ | Microsoft Store Python 假入口 → 脚本终止 |
| 7 | ❌ | `venv` 不可用（精简版 Python）→ 无回退 |
| 8 | ❌ | `f-string` 双引号转义链损坏 |
| 9 | ❌ | 端口占用直接退出，无清理选项 |
| 10 | ❌ | 前端 `authFetch` 无条件弹登录框（Bug） |
| 11 | ❌ | LLM Manager 前端未构建 → `/llm-manager` 404 |
| 12 | ✅ | 全部通过：单机部署 + SOP 任务执行成功 |

**验证通过项**：主界面 ✅ | LLM Manager ✅ | 渠道激活 ✅ | SOP 任务执行 ✅ | 端口/磁盘自检 ✅

**修复记录**（共 10 个 commit）：

| 问题 | 根因 | 修复 Commit |
|------|------|--------|
| Python 检测 ParserError | `exit(0 if ...)` PS 误解析 | `0cf8992`: 数字比较 |
| 硬编码路径 | `portable-dev-env` 不通用 | `b67a479`: 纯 PATH 检测 |
| 加密密钥 `-replace` | `=` 号截断 | `b67a479`: 逐行读写 |
| `-match` 正则解析失败 | 单引号编码损坏 | `39e34b3`: `StartsWith()` |
| PS 5.1 兼容 | `?.` `??` 语法 | `b67a479`: `if/else` |
| MS Store 假入口 | `Python.exe` 占位符 | `b67a479`: 跳过 WindowsApps |
| `venv` 不可用 | 精简版 Python | `e3c39ab`: `virtualenv` 回退 |
| f-string 引号损坏 | PS 转义链出错 | `e3c39ab`: `str()` 拼接 |
| 端口占用 | 无清理 | `e3c39ab`: 交互式 kill |
| `$env:ENABLE_AUTH` 未设置 | 终端残留覆盖 `.env` | `ba7581c`: 显式设置 |
| `authFetch` 无条件弹窗 | 无凭证即弹登录 | `cf606f8`: 仅 401 触发 |
| LLM Manager 未构建 | 部署脚本漏写 | `918d8f2`: 补充 Vite 构建 |
| LF 换行 PS 5.1 不兼容 | `write_to_file` 写 LF | 文档：要求 `pwsh 7+` |

---

### 第四轮测试（2026-07-03 | 代码版本从 `12b3cb7` 起至本轮结束）

> 测试目标：CVM 重新部署测试，**四种部署方式全部覆盖**——Docker单用户模式、非Docker手动多用户部署、Docker离线部署、Docker在线多用户部署（作为CVM最终常驻状态，迁移6个存量真实账户）。测试前先清理CVM残留的testuser测试账户、备份关键配置、拉取main最新代码。

#### 测试总览

| 测试 | 结果 | 说明 |
|------|:--:|------|
| 测试1：Docker单用户模式 | ✅ | `ENABLE_AUTH=false`，无认证直接访问，浏览器验证通过 |
| 测试2：非Docker手动部署（多用户） | ✅ | 期间发现并修复 `executor.py` PEP695语法兼容性 + `deploy_manual.sh` 缺 `DEV_MODE=false` + Tailwind `--content` 覆盖config导致CSS残缺（4KB→29KB） |
| 测试3：Docker离线部署 | ✅ | `prepare_offline.sh`（构建镜像+打包源码）→ 隔离目录解压 → `deploy_offline.sh`（仅`docker load`+`compose up`，不触发build）→ 功能验证；期间发现并修复离线包误打包 `.next` 缓存（~240MB），修复后重新完整跑通一遍全流程验证 |
| 测试4：Docker在线多用户部署（CVM最终常驻状态） | ✅ | `/data/CreditWise` 真实生产目录直接 `docker compose up -d`，挂载真实 `.env`/`config/users.yaml`（6个真实账户）/数据库，`restart: unless-stopped`；浏览器人工验证登录、退出登录切账号、`/llm-manager`页面全部通过 |

#### 测试期间发现并修复的问题（共7个，均已提交推送）

| # | 问题 | 根因 | 修复 | Commit |
|:-:|------|------|------|--------|
| 1 | `executor.py` PEP695类型语法在CVM Python版本下语法错误 | 目标机Python版本低于PEP695（3.12）要求 | 改用兼容写法 | （测试2早期） |
| 2 | `deploy_manual.sh` 缺少 `DEV_MODE=false` | 脚本未显式设置，容器默认走开发模式逻辑 | 补充环境变量设置 | （测试2） |
| 3 | `deploy_manual.sh` 编译产物CSS只有4KB（应~29KB），LLM Manager页面无样式 | Tailwind CLI `--content` 参数**完全覆盖**（非合并）`tailwind.config.js`里更完整的content配置，此前`docker/Dockerfile`同类问题已于`0282342`修复，但`deploy_manual.sh`独立维护一份构建逻辑未同步 | 去掉硬编码的 `--content` 参数，改为读取 `tailwind.config.js` | 本轮部署脚本修复 |
| 4 | **生产模式下退出登录无法切换账号**（架构级问题，详见下方专项说明） | 浏览器对标准 `Basic` 认证方案的原生缓存/自动重发是协议层行为 | 认证方案从 `Basic` 改为自定义 `CWAuth` | `870cf91`（+前置的白名单调整 `04b21ad`） |
| 5 | LLM Manager前端非admin用户遇403无明确提示（卡在"加载中"） | `/llm-manager`页面壳子公开后，非admin调用管理API会403，但前端统一走 `alert()`，未做403专门识别 | 四个数据加载函数新增403识别，展示"🔒无权限访问"提示 | `12b3cb7` |
| 6 | `prepare_offline.sh` 误打包 `demo/chat/.next`（Next.js本地构建缓存，~240MB） | rsync排除列表遗漏`.next`；离线部署走Dockerfile多阶段构建，完全不依赖这份本地缓存 | 新增 `--exclude='.next'` | `911edc7` |
| 7 | 账户锁定计数器并发竞态，导致浏览器缓存的失效凭证被误判成多次"主动输错密码"提前触发锁定 | `_failure_tracker`无锁保护，多线程读写竞态；全局fetch拦截器把同一份缓存凭证并发附加到多个后台请求，各自独立计入失败 | ①加`threading.Lock`保证原子性；②同一凭证2秒窗口内去重，不同密码仍正常计数 | `5199715` |

#### 专项说明：生产模式"退出登录无法切换账号"问题的完整排查过程

这是本轮测试中**排查耗时最长、涉及改动最深**的问题，分两步才彻底解决：

1. **现象**：CVM等同源生产部署下，用户点"退出登录"（清localStorage+刷新页面）后，浏览器仍自动用原账号登录，无法切换到另一账号；浏览器无痕窗口经实测也不可靠。

2. **第一步修复（不充分）**：把 `/`、`/llm-manager`、`/llm-manager/` 三个页面壳子纳入认证白名单，公开可加载，鉴权改为页面加载后的AJAX探测（`/auth/me`）+自定义登录框。**CVM实测用户浏览器仍复现问题**。

3. **排查发现真正根因**：浏览器对标准 `Basic` 认证方案有**协议层面**的原生缓存/自动重发机制——只要浏览器历史上（哪怕是本次修复上线前）曾用 `Basic` 凭证认证成功过一次，之后会对该域名下**所有**请求（包括JS未显式设置`Authorization`头的AJAX调用）自动注入缓存凭证，仅去掉页面壳子的401挑战头无法清除已经被浏览器缓存的旧凭证。

4. **第二步修复（真正根治）**：认证方案从标准 `Basic` 改为自定义方案名 `CWAuth`（编码方式不变，仍是`base64("user:pass")`，只改`Authorization`头的方案前缀词）。浏览器只对它"认识"的方案（`Basic`/`Digest`/`NTLM`/`Negotiate`）做缓存+自动注入，自定义方案名对浏览器只是不透明字符串——即使浏览器仍留有旧`Basic`缓存并继续自动重发，后端也只认`CWAuth`前缀，旧凭证被直接判定无效。涉及改动：`API/auth_middleware.py`、`demo/chat/lib/config.ts`、`demo/chat/components/LoginDialog.tsx`、`llm_manager_integrated/frontend/shared/js/auth.js`。

5. **修复过程中的衍生小坑**：`llm_manager_integrated/frontend/shared/js/auth.js`全局fetch拦截器里有一处 `"Basic " + auth` 首次改造时漏改（另外两处改了），导致"主界面登录后点开LLM渠道管理仍反复要求登录"，后续单独修复补齐。另有静态资源（`auth.js`/`main.js`）缺少 `Cache-Control` 头，导致浏览器复用了改造前的旧版本文件，顺手加了 `Cache-Control: no-cache`。

6. **验证结论**：此修复**不会**重新引入"首屏JS未加载完前怎么鉴权"的历史顾虑——原设计前提"首页导航需要认证保护"被移除（页面壳子本身不含敏感数据，公开加载无风险），真正的身份判断动作发生在JS加载完成后主动发起的`/auth/me`探测，此时自定义登录框已可用。

#### 测试3（离线部署）完整流程验证记录

由于离线部署的"真实场景"是外网机器构建、内网机器部署两台不同机器，本次测试用**同一台CVM分别扮演两个角色**验证（该机器本身有外网访问能力，`prepare_offline.sh`第1步`docker compose build`本身需要外网这一事实也确认了这一点）：

```
1. [外网角色] cd /data/CreditWise && bash scripts/prepare_offline.sh
   → 构建完整Docker镜像 → docker save导出tar → rsync打包source/ → tar.gz压缩
   → 产出 creditwise_offline_bundle.tar.gz（~650-700MB）

2. [传输模拟] 解压到全新隔离目录（非/data/CreditWise生产目录，避免碰生产数据）
   mkdir /data/offline_deploy_testN && tar -xzf .../creditwise_offline_bundle.tar.gz

3. [内网角色] cd offline_bundle/source && bash scripts/deploy_offline.sh
   → docker load加载镜像（验证：全程无docker compose build被触发）
   → 交互选择部署模式（2=多用户）
   → 生成.env（自动生成加密密钥）+ docker compose up -d
   → 健康检查通过

4. 复制真实config/users.yaml（只读复制，不改动生产文件）到隔离目录，重启容器验证真实账户登录

5. curl全面验证：/health、/（白名单200）、/llm-manager/（200）、main.css大小、
   /workspace/files（401）、旧Basic方案（401，确认CWAuth生效）

6. 测试完成后 docker compose down + 清理隔离目录，不影响生产
```

`.next`误打包问题修复后，**完整重跑了一遍上述全部6步**，确认：`demo`目录从248M降至5.6M、离线包体积减少约57MB（压缩后）、所有功能验证项依然全部通过。

---
