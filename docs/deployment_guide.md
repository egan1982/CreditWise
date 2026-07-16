# CreditWise 部署指南

> 支持 Docker 部署（推荐）和非 Docker 手动部署，覆盖 Win/Mac/Linux 三个平台。

---

## 部署方式速览

| 方式 | 适用场景 | 平台 | 联网需求 |
|------|---------|------|:--:|
| Docker 在线部署 | 有外网访问的标准部署 | Linux | 是 |
| Docker 离线部署 | 内网无外网访问 | Linux | 否 |
| 非 Docker 手动部署 | Docker 不可用的环境 | Win/Mac/Linux | 否（离线包） |

> **默认部署模式为多用户**（`ENABLE_AUTH=true`），所有页面均需登录。单用户模式需显式设置 `ENABLE_AUTH=false`。

---

## 零、服务器环境要求

### 硬件配置

| 资源 | 最低配置 | 推荐配置 | 说明 |
|------|:-------:|:-------:|------|
| **CPU** | 2 核 | 4 核+ | SOP 任务（规则挖掘/评分卡）计算密集，多核可并行处理多个任务 |
| **内存** | 4 GB | 8 GB+ | kaleido/Chromium 渲染图表约占 500MB，大数据集（>50 万行）分析约需 2-4 GB |
| **磁盘** | 20 GB | 50 GB+ | Docker 镜像约 3-4 GB，用户上传数据、任务结果、日志随时间增长 |
| **网络** | 内网互通 | — | 生产模式前后端同进程无需额外网络要求；外网访问仅用于 LLM API 调用 |

> 💡 **典型场景参考**：腾讯云标准型 S5 `2核4GB` 满足轻量使用（≤10 人并发，数据集 ≤10 万行）；`4核8GB` 支持中等规模（≤50 人，数据集 ≤100 万行）。

### 软件环境

| 软件 | 版本要求 | 说明 |
|------|---------|------|
| **操作系统** | Linux（CentOS 7+ / Ubuntu 18.04+ / Debian 10+）| 推荐 Ubuntu 20.04 LTS |
| **Docker** | 20.10+ | 在线部署时由脚本自动安装 |
| **Docker Compose** | 2.0+（Compose V2）| 使用 `docker compose`（无连字符）语法 |
| **Python** | 3.10 – 3.12 | 非 Docker 部署时需手动安装；Docker 镜像内置 3.12。<br>**预编译代码包当前版本绑定 Python 3.11**（`.so` 编译产物绑定编译时版本），如需其他版本请联系编译方 |
| **Node.js** | 18+ | 仅开发模式或手动重新构建前端时需要；Docker 构建阶段已包含 |
| **PowerShell** | 7.0+ (pwsh) | Windows 非 Docker 部署必需；系统自带的 Windows PowerShell 5.1 **无法运行部署脚本**（Git 仓库文件为 LF 换行，5.1 不兼容） |
| **开放端口** | 8200、8100 | 8200 主服务，8100 文件下载服务；需在云服务器安全组中放行 |

### CPU 架构

| 架构 | 支持情况 |
|------|:-------:|
| x86_64 (amd64) | ✅ 完全支持，推荐 |
| ARM64 (aarch64) | ⚠️ 有已知阻塞点，详见[第十节](#十服务器架构兼容性) |

---



### 前置条件
- Linux（CentOS 7+ / Ubuntu 18.04+ / Debian 10+）
- Root 或 sudo 权限
- 外网访问（拉取 Docker 镜像 + pip/npm 依赖）

### 步骤

```bash
chmod +x scripts/deploy_linux.sh
./scripts/deploy_linux.sh
```

脚本会交互式引导：
1. 选择部署模式（单用户 / 内网多用户）
2. 自动检查端口占用和磁盘空间（≥2GB）
3. 自动安装 Docker（如未安装）
4. 配置环境变量和加密密钥
5. 构建镜像并启动服务（包含 LLM Manager 前端 Tailwind CSS 离线编译）

### 手动 Docker 启动

```bash
# 默认多用户模式
cd docker && docker compose up -d

# 单用户模式（如不需要认证）
ENABLE_AUTH=false docker compose up -d
```

> ⚠️ **部署后必须操作**：`config/users.yaml` 初始为占位符密码。生成真实哈希替换后才能登录：
> ```bash
> docker run --rm creditwise:latest python scripts/hash_password.py <密码>
> ```

# 内网多用户模式（Basic Auth）
cd docker && ENABLE_AUTH=true docker compose up -d
```

---

## 二、Docker 离线部署

> 核心思路：在有外网的机器上构建完整 Docker 镜像（含前端编译 + Python 依赖），导出镜像 + 打包源码。内网服务器只需 `docker load` + `docker compose up`，**无需 build**。
>
> **⚠️ 试用版（GYJZ FreeTrail）：必须选择内网多用户模式（`deploy_offline.sh` 选项 [2]）。单用户模式跳过认证，试用期限制将不生效。**

### 环境要求对照

| | 联网编译机 | 无外网目标服务器 |
|------|:--:|:--:|
| 需要外网？ | ✅ 必须（拉基础镜像 + pip install） | ❌ 不需要 |
| 需要 Docker？ | ✅ | ✅ |
| 需要 Python/GCC/Cython？ | ❌ 编译全部在 Docker 容器内完成 | ❌ |
| 需要 Node.js？ | ❌ 前端构建在容器内完成 | ❌ |
| 部署命令 | `prepare_offline.sh [--protected]` | `deploy_offline.sh` |

> **关键**：编译机除 Docker 外不需要安装任何编译工具——Cython 编译、前端 `npm build`、Python 依赖安装全部在 `Dockerfile` 构建阶段自动完成。

### 2.1 在有外网的机器上准备离线包

```bash
chmod +x scripts/prepare_offline.sh
./scripts/prepare_offline.sh
```

脚本自动完成：
1. 构建完整 Docker 镜像（`docker compose build`，含前端编译 + Python 依赖安装）
2. 导出镜像为 tar 文件（`docker save`）
3. 打包项目源码（排除 `.git`、`node_modules`、`workspace` 等运行时文件）
4. 生成 `creditwise_offline_bundle.tar.gz`（约 500MB）

产出：`creditwise_offline_bundle.tar.gz`

包含：
- `images/creditwise-latest.tar` — 完整构建好的 Docker 镜像（含前端 + 后端 + 所有依赖）
- `source/` — 项目源码 + 运行配置（`docker-compose.yml`、`.env`、`config/` 等）

### 2.2 传输到内网服务器并解压

离线包解压后结构（假设部署到 `/opt/CreditWise`）：

```bash
# 传输（U 盘 / SCP / 内网中转）
scp creditwise_offline_bundle.tar.gz user@intranet-server:/opt/

# 解压
ssh user@intranet-server
mkdir -p /opt/CreditWise
tar -xzf /opt/creditwise_offline_bundle.tar.gz -C /opt/CreditWise/
```

解压后 `/opt/CreditWise/` 目录结构：

```
/opt/CreditWise/
├── images/
│   └── creditwise-latest.tar        ← 预构建的 Docker 镜像
└── source/
    ├── docker/
    │   └── docker-compose.yml       ← compose 配置文件
    ├── scripts/
    │   └── deploy_offline.sh        ← 部署脚本（在此目录下执行）
    ├── config/
    │   └── users.yaml.example       ← 用户配置模板
    └── .env                         ← 环境变量
```

> `deploy_offline.sh` 通过脚本自身路径动态发现 `images/` 和 `docker-compose.yml`，不依赖父目录名称。

### 2.3 在内网服务器上部署

```bash
cd /opt/CreditWise/source
chmod +x scripts/deploy_offline.sh
./scripts/deploy_offline.sh
```

脚本自动完成：
1. 加载 Docker 镜像（`docker load`）
2. 交互式选择部署模式（单用户 / 内网多用户）
3. 配置环境（`.env`、加密密钥）
4. 启动服务（`docker compose up -d`，**不执行 build**）

> **首次登录**：首个 admin 账户由零配置自动引导生成（默认密码 `admin123`，首次登录强制改密），无需手动编辑 yaml。可通过环境变量 `BOOTSTRAP_ADMIN_PASSWORD` 自定义初始密码。

#### 预编译代码包场景（加密版本）

若收到的离线包是基于预编译代码包（约 31MB）生成的，部署方先在有外网的机器上执行：

```bash
tar -xzf creditwise_protected_src.tar.gz
cd dist_protected
./scripts/setup_protected.sh --build   # 初始化 + docker build + docker save + 打包
# → 产出 creditwise_offline_xxx.tar.gz
```

然后将产出文件传至目标无外网服务器，按上方常规离线部署流程操作。

---

## 三、Docker 服务管理

推荐使用 `service.sh` 统一管理，它会自动从 `.env` 读取 `ENABLE_AUTH` 等配置：

```bash
./scripts/service.sh start          # 启动（读取 .env 中的 ENABLE_AUTH）
./scripts/service.sh start-noauth   # 强制无认证模式启动
./scripts/service.sh stop           # 停止
./scripts/service.sh restart        # 重启
./scripts/service.sh status         # 查看状态 + 健康检查
./scripts/service.sh logs           # 实时日志（Ctrl+C 退出）
./scripts/service.sh hash <密码>    # 生成 bcrypt 密码哈希（多用户模式添加用户用）

---

## 四、部署后操作：创建终端用户

### 4.1 管理员首次登录

部署成功后，首个管理员账户由系统零配置自动引导生成：

| 项目 | 值 |
|------|------|
| 用户名 | admin |
| 初始密码 | admin123（首次登录强制改密） |
| 自定义密码 | 通过环境变量 `BOOTSTRAP_ADMIN_PASSWORD` 覆盖 |

### 4.2 通过 Web UI 创建终端用户

> 账户管理已完全迁移到 Web UI，无需编辑配置文件或重启服务。

```
管理员登录 → 点击右上角头像菜单 → 「用户管理」 → 「新建用户」
  → 填写用户名、角色（admin/user）、部门（可选）、有效期（可选）
  → 保存后系统自动生成随机初始密码，弹窗一次性展示
  → 管理员通过安全渠道（口头/内网通讯）将密码告知新用户
  → 新用户首次登录后会被强制要求修改密码
```

管理员在「用户管理」页面还可：
- 编辑用户角色、部门、有效期
- 启用/禁用账户
- 重置任意用户密码
- 合并账户（改名场景，旧账户历史数据迁移到新账户名）

普通用户可通过头像菜单「账户设置」自助修改密码、编辑显示名与部门备注。

### 4.3 多用户使用流程

```
终端用户 → 浏览器访问 http://<服务器IP>:8200
        → 输入分配的用户名 + 一次性密码
        → 强制修改密码
        → 进入系统（LLM Manager 配置渠道、执行风控任务）
```

> 所有用户共享同一套 LLM 渠道配置和 SOP 任务引擎，权限由角色控制（admin 可管理用户/渠道，user 仅可执行任务）。

```

也可以直接使用 `docker compose`（注意 `ENABLE_AUTH` 需显式传入）：

```bash
# 查看日志
cd docker && docker compose logs -f

# 停止服务
cd docker && docker compose down

# 重启服务（读取 .env 中 ENABLE_AUTH 变量）
cd docker && ENABLE_AUTH=true docker compose up -d
```

---

## 四、非 Docker 手动部署

### 4.1 Linux / macOS

```bash
chmod +x scripts/deploy_manual.sh
./scripts/deploy_manual.sh
```

系统依赖（Linux kaleido/Chromium）：

```bash
# Debian/Ubuntu
sudo apt-get install -y \
    libgbm1 libnss3 libnspr4 libatk-bridge2.0-0 \
    libatk1.0-0 libasound2 libxcomposite1 libxdamage1 \
    libxrandr2 libxkbcommon0 libpango-1.0-0 libcups2

# macOS（无需额外依赖，Chromium 已内置）
```

> 注意：Node.js 未安装时，脚本会自动跳过 LLM Manager 前端构建，使用已有的预编译产物（如有）。如需完整 UI，需提前安装 Node.js 18+。

### 4.2 Windows

```powershell
.\scripts\deploy_manual.ps1
```

需要 Visual C++ 运行时（Windows 10+ 通常已安装）。

### 4.3 手动启动（最小化）

```bash
# 创建虚拟环境
python3 -m venv .venv && source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置
cp .env.example .env
# 编辑 .env：设置 ENABLE_AUTH、LLM_MANAGER_ENCRYPTION_KEY 等

# 启动
python API/main.py

# 访问：http://localhost:8200
```

---

## 五、生产环境运维（启停服务）

### 5.1 Docker 部署

```bash
# 通用命令
./scripts/service.sh start          # 启动（开启认证，读取 .env）
./scripts/service.sh start-noauth   # 启动（关闭认证）
./scripts/service.sh stop           # 停止
./scripts/service.sh restart        # 重启
./scripts/service.sh status         # 查看状态 + 健康检查
./scripts/service.sh logs           # 实时日志（Ctrl+C 退出）
```

### 5.2 非 Docker 部署（Windows）

```powershell
.\scripts\start_prod.ps1   # 启动生产服务（DEV_MODE=false, 0.0.0.0:8200）
.\scripts\stop_prod.ps1    # 停止服务

# 查看日志
Get-Content logs\server.log -Tail 50
```

### 5.3 非 Docker 部署（Linux/macOS）

```bash
# 启动（后台运行，日志写入 logs/server.log）
nohup python API/main.py > logs/server.log 2>&1 &
echo $! > .app_pids.txt

# 停止
kill $(cat .app_pids.txt) 2>/dev/null
rm -f .app_pids.txt

# 查看日志
tail -f logs/server.log
```

### 5.4 访问地址

| 模式 | 地址 |
|------|------|
| 生产（DEV_MODE=false） | `http://<服务器IP>:8200` |
| LLM Manager 管理 | `http://<服务器IP>:8200/llm-manager` |
| 健康检查 | `http://<服务器IP>:8200/health` |
| API 文档 | `http://<服务器IP>:8200/docs` |

---

## 六、部署模式切换

### ENABLE_AUTH 说明

> ⚠️ **重要**：Docker 部署时，`ENABLE_AUTH` 需要在执行 `docker compose up` 时作为 shell 环境变量传入，`.env` 文件中的值**不会**被 `docker-compose.yml` 的 `${ENABLE_AUTH:-false}` 语法自动读取。
>
> 推荐使用 `./scripts/service.sh start` —— 该脚本会自动从 `.env` 读取并正确传递。

| `ENABLE_AUTH` | 模式 | 说明 |
|:---:|------|------|
| `true`（默认） | 内网多用户 | Basic Auth 认证，适合团队 |
| `false` | 单用户 | 无需登录，适合个人使用 |

### 多用户模式配置 users.yaml

```bash
# 1. 复制模板
cp config/users.yaml.example config/users.yaml

# 2. 生成密码哈希
./scripts/service.sh hash <密码>
# 或：python scripts/hash_password.py <密码>

# 3. 编辑 config/users.yaml 填入哈希值
```

> 📖 详细的用户管理说明（角色、有效期、账户锁定、运维命令）参见 `docs/intranet_deployment_guide.md` §3.3

---

## 七、端口说明

| 端口 | 服务 | 说明 |
|:----:|------|------|
| 8200 | 主服务 | API + 前端界面 + LLM Manager |
| 8100 | 文件服务 | 文件下载（报告、图表等） |

---

## 八、持久化数据

以下目录/文件在容器重启或重新部署后**需手动保留**：

| 目录/文件 | 说明 | Docker volume |
|-----------|------|:--:|
| `workspace/` | 用户上传数据和分析结果 | ✅ |
| `execution_states/` | SOP 任务执行状态 | ✅ |
| `task_results/` | 任务结果缓存 | ✅ |
| `logs/` | 运行日志 | ✅ |
| `llm_manager.db` | LLM 渠道配置数据库 | ✅ |
| `task_manager.db` | 任务历史数据库 | ✅ |
| `config/users.yaml` | 用户账号配置（多用户模式） | ✅ |
| `.env` | 加密密钥（⚠️ 丢失则 llm_manager.db 中的 API 密钥不可解密） | ✅ |

> ⚠️ **加密密钥警告**：`.env` 中的 `LLM_MANAGER_ENCRYPTION_KEY` 是 LLM 渠道 API 密钥的加密密钥。重新部署时若更换密钥，已存储的 API 密钥将无法解密，需重新配置所有渠道。

---

## 九、环境变量参考

| 变量 | 必需 | 默认值 | 说明 |
|------|:--:|--------|------|
| `ENABLE_AUTH` | 否 | `false` | 是否启用 Basic Auth（见第六节） |
| `LLM_MANAGER_ENCRYPTION_KEY` | 是 | 自动生成 | Fernet 密钥，加密渠道 API Key |
| `API_HOST` | 否 | `0.0.0.0` | 监听地址 |
| `API_PORT` | 否 | `8200` | API 端口 |
| `DEV_MODE` | 否 | `false` | 开发模式（Docker 默认 false） |
| `CORS_ORIGINS` | 否 | — | CORS 允许的源（生产模式同源无需配置） |
| `LOG_LEVEL` | 否 | `INFO` | 日志级别 |

---

## 十、服务器架构兼容性

| 架构 | 代表机型 | 兼容性 | 说明 |
|------|---------|:------:|------|
| **x86_64 (amd64)** | 腾讯云标准型、AWS EC2 默认、阿里云通用型 | ✅ 完全兼容 | 当前生产验证环境，推荐 |
| **ARM64 (aarch64)** | 腾讯云 ARM 型、AWS Graviton、阿里云倚天 | ⚠️ 有阻塞点 | 见下方说明 |

### ARM64 已知阻塞点

`requirements.txt` 中固定了 `kaleido==0.2.1`，该版本内置预编译的 Chromium 二进制，**PyPI 上没有 ARM64 wheel**，在 ARM64 服务器上构建镜像时 `pip install` 会失败，导致 Word/HTML 报告中所有图表（ROC、KS、评分分布等）无法生成。

**当前建议**：生产部署请使用 x86_64 架构的云服务器实例。

> 如有迁移至 ARM64 的需求，需升级 `kaleido` 至 1.x（改为依赖系统 Chromium）并适配相关 API 调用，预计工作量约 0.5 天。


LLM Manager（`/llm-manager`）的前端在不同模式下行为不同：

| 模式 | 说明 |
|------|------|
| 开发模式（`DEV_MODE=true`） | 前端由 Vite Dev Server（`:3001`）提供，热更新。需在 `llm_manager_integrated/frontend/` 运行 `npm run dev` |
| 生产模式（`DEV_MODE=false`，默认） | 前端静态文件在 Docker 构建阶段由 Tailwind CSS 离线编译，完全不依赖 CDN，内网可用 |

Docker 构建阶段的前端处理流程：
1. `npm run build` — Vite 构建，输出到 `static/assets/`
2. `tailwindcss` — 编译 `styles/main.css`，输出 `static/assets/main.css`（离线 CSS）
3. `sed` — 替换 CDN 引用为本地路径，删除内联 `<style>` 块，修正 CSP
