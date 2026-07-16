# CreditWise 内网多用户部署指南

> 分支：`main`  
> 版本：v1.7.0  
> 适用场景：内网 <5 人测试使用  
> 更新：v1.7（2026-07-03，CVM第四轮部署测试）认证方案从标准 `Basic` 升级为自定义方案名 `CWAuth`（编码方式不变），根治"生产模式退出登录无法切换账号"问题（浏览器不再对认证凭证做原生缓存/自动重发）；`/`、`/llm-manager`、`/llm-manager/` 页面壳子改为公开可加载（无需登录即可看到界面，真正的数据/管理权限仍在API层强制校验），配合修复账户锁定计数器并发竞态问题，详见 §3.1、§3.2；v1.6 首个管理员账户支持零配置自动创建（容器/服务首次启动默认使用固定密码 `admin123`，首次登录强制改密），修复部署脚本"暂不编辑yaml却留下占位哈希导致永久锁死"的隐患，Docker 用户配置改为整目录挂载避免路径被误建为目录，详见 §3.3；v1.5 账户管理迁移至 SQLite + Web UI（管理员可通过前端新建/编辑/禁用/重置密码，用户可自助改密），`users.yaml` 降级为迁移前/灾备兜底文件；v1.3 新增账户有效期（valid_until）配置指引，补充用户配置字段说明和运维命令

---

## 1. 多用户使用流程

```
内网 PC（用户A）                    部署服务器（内网服务器）
┌──────────────────┐              ┌─────────────────────────────────────┐
│ 浏览器打开        │              │  CreditWise 服务（单机部署）          │
│ http://10.x.x.x:8200           │                                     │
│                  │   ──────→    │  FastAPI (:8200)                    │
│ 弹出登录框        │              │    ├─ Basic Auth 中间件              │
│ 输入 test1/密码   │              │    ├─ Chat API (/v1/chat/*)         │
│                  │   ←──────    │    ├─ SOP API (/sop/*)              │
│ 进入主界面        │              │    ├─ Workspace API (/workspace/*)  │
└──────────────────┘              │    ├─ LLM Manager (仅 admin)        │
                                  │    └─ 静态前端文件                    │
┌──────────────────┐              │                                     │
│ 内网 PC（用户B）   │              │  HTTP 文件服务器 (:8100)             │
│ 浏览器打开        │   ──────→    │                                     │
│ 输入 test2/密码   │              └─────────────────────────────────────┘
└──────────────────┘                       │
                                           ▼
                                    外部 LLM API
                                   （DeepSeek/OpenAI/...）
```

### 使用方式

1. 所有用户访问 **同一个 URL**（如 `http://10.x.x.x:8200`）
2. 页面壳子直接加载（`/`、`/llm-manager` 已公开，无需登录即可看到界面），加载完成后自动弹出**自定义登录对话框**（非浏览器原生弹窗，见 §3.1）→ 输入各自账号密码
3. 登录后各自独立使用，通过登录用户名区分数据
4. 点击"退出登录"会清空本地凭证并可立即切换到另一账号重新登录（v1.7 修复：此前因浏览器对标准 Basic Auth 的原生缓存机制，退出登录后仍会自动用旧账号重新登录，v1.7 起认证方案升级为自定义 `CWAuth` 后不再有此问题）

### 角色权限

| 角色 | Chat/SOP | 工作区 | LLM Manager 管理 |
|------|----------|--------|-----------------|
| **admin** | ✅ | ✅ | ✅ 可配置渠道/API Key |
| **user** | ✅ | ✅ | ❌ 只能使用已配好的渠道 |

---

## 2. 数据存储架构

### 2.1 服务器端存储

```
DeepAnalyze/
├─ workspace/                          ← 【用户数据根目录】
│   ├─ session_1711782000_a1b2c/       ← 用户 A 的 session
│   │   ├─ credit_data.csv             ← 上传的数据集
│   │   ├─ generated/                  ← AI 生成的报告/图表
│   │   │   ├─ Report_20260327.md
│   │   │   └─ feature_importance.png
│   │   └─ (代码执行产生的中间文件)
│   │
│   └─ session_1711783000_x9y8z/       ← 用户 B 的 session
│       ├─ loan_sample.xlsx
│       └─ generated/
│
├─ execution_states/                   ← 【SOP 执行状态】
│   └─ exec-abc123.json               ← Pipeline 各阶段进度快照
│
├─ task_results/                       ← 【SOP 任务结果缓存】
│   └─ exec-abc123/
│       ├─ preprocessing.pkl           ← 阶段输出
│       ├─ rule_mining.pkl
│       └─ report.pkl
│
├─ task_manager.db                     ← 【SQLite】任务历史/统计
├─ llm_manager.db                      ← 【SQLite】LLM 渠道配置/API 日志
├─ logs/                               ← 【运行日志】
└─ config/
    └─ users.yaml                      ← 【用户账号】（不入 Git）
```

### 2.2 数据归属明细

| 数据类型 | 存储位置 | 隔离方式 | 说明 |
|---------|---------|---------|------|
| 上传的数据集 | `workspace/{session_id}/` | 按 session_id | 每个 session 独立目录 |
| AI 生成的文件 | `workspace/{session_id}/generated/` | 按 session_id | 报告/图表/代码输出 |
| SOP 执行状态 | `execution_states/{exec_id}.json` | 按 execution_id | 每个任务一个文件 |
| SOP 阶段数据 | `task_results/{exec_id}/` | 按 execution_id | 各阶段 pkl 文件 |
| 任务历史记录 | `task_manager.db` | 按 session_id 字段 | SQLite 共享库 |
| LLM 渠道配置 | `llm_manager.db` | 不隔离 | admin 配置，全员共享使用 |
| API 调用日志 | `llm_manager.db` | 不隔离 | 全局记录 |

### 2.3 用户 PC 端存储（浏览器）

| 数据 | 存储方式 | 持久性 |
|------|---------|--------|
| session_id | localStorage | ✅ 持久（除非手动清除） |
| UI 偏好（主题、面板折叠） | localStorage | ✅ 持久 |
| 选中的模型配置 ID | localStorage | ✅ 持久 |
| 聊天消息 | React state（内存） | ❌ 刷新页面即丢失 |
| Basic Auth 凭证 | 浏览器内存缓存 | ❌ 关闭浏览器即清除 |

> **结论：用户 PC 端不存储任何业务数据。** 数据集、任务结果、报告等全部在服务器端。浏览器仅存储 session 标识和 UI 偏好。

---

## 3. 认证机制

### 3.1 架构

> **v1.7 更新（2026-07-03，CVM第四轮部署测试）**：认证方案从标准 HTTP `Basic` 升级为自定义方案名 `CWAuth`（Authorization 头格式为 `CWAuth <base64(username:password)>`，编码方式不变，仅方案前缀词不同）。
>
> **根因回顾**：标准 `Basic` 方案存在浏览器**协议层面**的原生缓存/自动重发机制——只要浏览器曾用 `Basic` 凭证登录成功过一次，之后会对该域名下所有请求自动重新附带这份缓存凭证，前端 JS 的 `clearAuth()` 清 localStorage 对浏览器这份原生缓存完全无效，导致"退出登录"后浏览器仍自动用旧账号重新登录，无法切换账号（浏览器无痕/隐私窗口经实测也不可靠）。
>
> **修复方式**：浏览器只对它"认识"的方案（`Basic`/`Digest`/`NTLM`/`Negotiate`）做缓存和自动注入，自定义方案名对浏览器只是一个不透明字符串，不会有任何缓存/自动重发行为——凭证是否发送、发送什么值完全由前端 JS 决定。同时把 `/`、`/llm-manager`、`/llm-manager/` 三个页面壳子路径纳入认证白名单（页面本身不含用户数据，公开加载无安全风险），认证完全交给页面加载完成后主动发起的 `/auth/me` 探测 + 自定义登录对话框处理，不再触发浏览器原生认证弹窗。**数据/管理 API 的认证与权限校验边界完全不受影响**，仍在后端中间件强制拦截。

```
请求 → CWAuth 认证中间件 → 角色检查 → 路由处理
            │
     ┌──────▼──────┐
     │ users.yaml   │  bcrypt 哈希密码
     │ (服务器本地)   │  max_failures=5, lockout=15min
     └─────────────┘
```

### 3.2 路由权限表

| 路由 | 认证要求 | 角色要求 |
|------|---------|---------|
| `/` (首页 HTML 壳子) | **无**（v1.7起公开白名单，页面本身不含用户数据） | 无 |
| `/llm-manager`, `/llm-manager/` (管理页面壳子) | **无**（v1.7起公开白名单；非admin用户能打开页面，但调用下方admin专属API会收到403，前端已做友好提示） | 无（页面壳子本身） |
| `/favicon.ico` | 无（精确匹配白名单） | 无 |
| `/health`, `/docs` | 无 | 无 |
| `/_next/*` (前端静态资源) | 无 | 无 |
| `/sop/status/*/stream` (SSE) | 无 | 无 |
| `/v1/chat/*` | 需登录 | 任意角色 |
| `/sop/*`（非 SSE） | 需登录 | 任意角色 |
| `/workspace/*` | 需登录 | 任意角色 |
| `/llm-manager/api/proxy/*` | 需登录 | 任意角色 |
| `/llm-manager/api/models` | 需登录 | 任意角色 |
| `/llm-manager/api/manage/*` | 需登录 | **admin** |
| `/llm-manager/api/logs/*` | 需登录 | **admin** |
| `/llm-manager/api/monitoring/*` | 需登录 | **admin** |

### 3.3 用户管理

> **v1.5 更新（2026-07-02）**：账户存储已从 `config/users.yaml` 迁移至 SQLite `users` 表，管理员可通过前端「用户管理」页面（登录后点击头像菜单 → 用户管理）完成账户全生命周期管理，**不再需要编辑 yaml + 重启服务**。以下描述 Web UI 主路径，`users.yaml` 仅作为迁移前存量账户/灾备兜底文件保留。
>
> **v1.6 更新（2026-07-02）**：首个管理员账户创建已实现**零配置自动兜底**——容器/服务首次以 `ENABLE_AUTH=true` 启动时，若检测到数据库0账户且 `config/users.yaml` 也不存在/未配置，会自动创建 admin 账户（默认密码 `admin123`，首次登录强制改密），无需再手动跑迁移脚本或编辑 yaml 才能登录。可通过环境变量 `BOOTSTRAP_ADMIN_PASSWORD` 自定义初始密码。见下方"首个管理员账户从哪来"。

**首个管理员账户从哪来**（新增，取代下方旧的"存量账户迁移"作为默认路径）：

```
服务首次以 ENABLE_AUTH=true 启动
  → 检测到 users 表 0 账户 且 config/users.yaml 不存在/未配置任何账户
  → 自动创建 admin 账户（默认密码 admin123，must_change_password=true）
  → 密码打印到启动日志（docker compose logs 可查看），也可通过环境变量
    BOOTSTRAP_ADMIN_PASSWORD 自定义
  → 管理员使用 admin123 登录 → 强制改密 → 通过 Web UI 建其他账户
```

只有以下场景才需要用到传统的 `config/users.yaml` + `scripts/migrate_users_yaml_to_db.py` 路径：
- 从 v1.5 及更早版本升级，本来就已经在用 `users.yaml` 维护账户（见下方"存量账户迁移"）
- 首次部署时希望自定义初始账户名，或一次性预置多个账户（而非部署后再逐个用 Web UI 建）

**Web UI 主路径**（推荐，日常新增账户统一走这里）：

```
新用户想使用 → 管理员登录 → 点击头像菜单「用户管理」 → 「新建用户」
  → 填写用户名/角色/部门/有效期（密码无需手输，系统自动生成）
  → 保存后一次性弹窗展示初始密码，管理员通过安全渠道告知新用户
  → 新用户首次登录后会被强制要求修改密码
```

普通用户可通过头像菜单「账户设置」自助修改密码/编辑显示名与部门备注，无需再联系管理员。

管理员在「用户管理」页面还可：编辑角色/有效期/启用禁用、重置任意用户密码、合并账户（改名场景，把旧账户历史数据转移到新账户名下）。

> ⚠️ **安全前置条件**：启用自助改密/管理员改密/重置密码等接口前，必须确认部署环境已启用 HTTPS（或可信内网+二层防护），否则密码将以明文暴露在网络传输中的风险与 Basic Auth 凭证一致，详见 `docs/user_management_module_design.md` §十六。

**存量账户迁移**（从 v1.5 及更早版本升级、本来就在用 `users.yaml` 时执行一次；全新部署无需此步骤）：

```bash
python scripts/migrate_users_yaml_to_db.py --dry-run   # 预览
python scripts/migrate_users_yaml_to_db.py              # 确认无误后实际写入
```

迁移后 `users` 表内有记录即自动切换为数据库鉴权（无需重启服务，下次登录请求即生效）；若尚未执行迁移或数据库不可用，会自动回退到 `config/users.yaml`（兼容旧部署，见下方字段说明）。

#### users.yaml 字段说明（迁移前 / 灾备兜底场景）

```yaml
users:
  - username: admin               # 登录用户名（唯一）
    password_hash: "$2b$12$..."   # bcrypt 哈希，用 scripts/hash_password.py 生成
    role: admin                   # 角色：admin（管理员）或 user（普通用户）
    org: "部门名称"                # 所属部门，仅描述用，不影响权限
    description: "说明文字"       # 备注，方便管理员识别
    valid_until: ""               # 账户到期日 YYYY-MM-DD，留空=永久有效

  - username: user1
    password_hash: "$2b$12$..."
    role: user
    org: "CSIG-SPD"
    description: "外部合作用户，有效期至年底"
    valid_until: "2026-12-31"     # 到期后登录返回 401，无需手动删除账户

settings:
  max_login_failures: 5           # 连续失败次数限制（超出后锁定）
  lockout_duration_minutes: 15    # 锁定时长（分钟）
```

#### valid_until 有效期规则

| valid_until 值 | 行为 |
|----------------|------|
| 空字符串 `""` | 永久有效（admin 账户推荐） |
| 未来日期，如 `2026-12-31` | 到期日当天仍可登录，次日起 401 |
| 过去日期 | 立即拒绝，返回 401 |
| 格式错误（非 YYYY-MM-DD） | 保守拒绝，返回 401，并在日志输出 ERROR |

> **注意**：`users.yaml` 仅在尚未执行迁移脚本，或数据库不可用时的回退场景下生效。修改该文件后无需重建镜像，**只需重启容器**即可生效：
> ```bash
> sudo docker restart creditwise-api
> ```
> 已迁移到数据库鉴权后，账户变更请优先使用「用户管理」Web UI（无需重启服务，实时生效）。

---

## 4. 部署步骤

### 4.1 方式一：Docker 部署（推荐）

> 一键部署脚本 `deploy_linux.sh` 已自动化处理所有前置条件，包括 Docker 安装、数据库文件预创建、加密密钥自动生成等。

#### 环境要求

| 依赖 | 版本 | 说明 |
|------|------|------|
| Linux CVM | CentOS/Ubuntu/Debian | 有 root 或 sudo 权限 |
| 端口 8200 | 开放 | API + 前端 |
| 端口 8100 | 开放 | 文件下载服务 |

> Docker 和 Docker Compose 如未安装，部署脚本会自动安装。

#### 部署流程

```bash
# ① 获取代码
git clone <仓库地址>
cd CreditWise
git checkout feature/intranet-multiuser

# ② 一键部署（7步全自动）
chmod +x scripts/deploy_linux.sh
./scripts/deploy_linux.sh
```

部署脚本自动完成以下 7 步：

| 步骤 | 内容 | 说明 |
|------|------|------|
| [1/7] | 检查/安装 Docker | 自动检测并安装 Docker + Compose |
| [2/7] | 检查用户配置 | 多用户模式下交互式二选一：**[1] 自动生成初始admin账户**（默认推荐，容器启动后从日志查看一次性密码）或 **[2] 手动配置** `users.yaml`（适合需要自定义账户名/预置多账户的场景） |
| [3/7] | 检查环境配置 | 从 `.env.example` 创建 `.env`，**自动生成加密密钥** |
| [4/7] | 预创建数据库文件 | `touch llm_manager.db task_manager.db`（避免 Docker 创建为目录） |
| [5/7] | 构建 Docker 镜像 | 首次约 5-10 分钟 |
| [6/7] | 启动服务 | `ENABLE_AUTH=true docker-compose up -d` |
| [7/7] | 健康检查验证 | 最多等待 30 秒确认服务启动 |

> ⚠️ **历史坑位（已修复，2026-07-02）**：旧版脚本无论运维是否选择"现在编辑"，都会无条件把 `users.yaml.example` 复制为 `users.yaml`（含 `PLACEHOLDER` 占位哈希）。若选择"暂不编辑"，这份带占位哈希的 yaml 会被系统误判为"已配置账户"从而不再自动创建兜底账户，而占位哈希本身又无法通过任何密码验证——最终导致系统没有任何账户能登录（永久锁死）。现已修正为：只有明确选择"手动配置"才会创建该文件，否则完全跳过，交由下方的自动兜底逻辑处理。

#### 部署后需手动完成

| 任务 | 命令 | 是否必须 |
|------|------|:--------:|
| 首个管理员账号 | **默认全自动**：容器首次启动检测到零账户时，自动创建 admin 账户（默认密码 `admin123`，首次登录强制改密）。可通过环境变量 `BOOTSTRAP_ADMIN_PASSWORD` 自定义。仅当部署时在 [2/7] 步骤选择了"手动配置"才需要自行编辑 `config/users.yaml` 或运行 `scripts/init_admin.py`（详见 §3.3、`docs/user_management_module_design.md` §二十） | ⭕ 自动完成，通常无需手动干预 |
| 创建 LLM 渠道 | 通过 LLM Manager 页面或 API 创建 | ✅ 必须 |
| 同步模型参数配置 | `./scripts/sync_model_configs.sh <用户名:密码>` | 可选 |

#### 日常运维

> **命令前置说明**：以下命令需要在项目 `docker/` 目录下执行，且通常需要 `sudo`。

```bash
cd /data/CreditWise/docker

# 查看状态
sudo docker compose ps

# 查看实时日志
sudo docker compose logs -f --tail 50

# 代码更新后重建（更新了 Python/前端代码时执行）
cd /data/CreditWise && git pull
cd docker && sudo docker compose build && sudo ENABLE_AUTH=true docker compose up -d

# 仅更新用户配置（users.yaml 改动，无需 rebuild）
# 直接编辑 /data/CreditWise/config/users.yaml，然后：
sudo docker restart creditwise-api

# 停止服务
sudo docker compose down

# 清理旧镜像（重建后释放磁盘）
sudo docker image prune -f
```

> **兼容说明**：`docker compose`（插件式，Docker 23+）与 `docker-compose`（独立二进制，旧版）等效。
> 当前 CVM 使用 Docker 28.x，只有 `docker compose` 插件，无独立 `docker-compose` 命令。
> Docker 28.x 下 `docker-compose.yml` 中的 `version: '3.8'` 字段会触发废弃警告（不影响运行，可忽略）。

#### 部署脚本自动处理的已知坑

以下问题已在 `deploy_linux.sh` 中自动解决，无需手动干预：

| 问题 | 原因 | 脚本处理方式 |
|------|------|-------------|
| `llm_manager.db` 被创建为目录 | Docker bind mount 对不存在的文件默认创建为目录 | 步骤 [4/7] 自动 `touch` 预创建空文件 |
| `LLM_MANAGER_ENCRYPTION_KEY` 为空导致启动失败 | `.env` 不入 Git，clone 后无此配置 | 步骤 [3/7] 自动生成 Fernet 密钥写入 `.env` |
| `.env` 文件不存在 | 被 `.gitignore` 忽略 | 步骤 [3/7] 自动从 `.env.example` 创建 |

---

### 4.2 方式二：手动部署（不使用 Docker）

#### 环境准备

| 依赖 | 版本 | 说明 |
|------|------|------|
| Python | 3.8+ | 后端 |
| Node.js | 16+ | 仅构建前端时需要 |
| 端口 8200 | 开放 | API 服务 |
| 端口 8100 | 开放 | 文件下载服务 |

#### 部署流程

```bash
# ① 拷贝项目到服务器
git clone <仓库地址>
cd DeepAnalyze
git checkout feature/intranet-multiuser

# ② 安装 Python 依赖
python -m venv .venv
.venv/Scripts/activate    # Windows
# source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# ③ 构建前端（生产模式）
cd demo/chat
npm install
npm run build
cd ../..

# ④ 配置用户账号
copy config\users.yaml.example config\users.yaml
python scripts/hash_password.py admin123     # 生成 admin 密码哈希
python scripts/hash_password.py test123      # 生成 user 密码哈希
# 将哈希值填入 config/users.yaml

# ⑤ 配置 LLM API Key
# 编辑 .env 文件或通过 LLM Manager 页面配置

# ⑥ 启动服务
$env:ENABLE_AUTH = "true"       # 启用认证
$env:DEV_MODE = "false"         # 生产模式
$env:API_HOST = "0.0.0.0"       # 允许外部访问
python -m uvicorn API.main:create_app --factory --host 0.0.0.0 --port 8200
```

### 4.3 生产 vs 开发模式

| | 开发模式 | 生产模式 |
|---|---|---|
| 前端 | Next.js dev server (:3000) | FastAPI 提供构建后的静态文件 |
| 端口 | 3000 + 3001 + 8200 + 8100 | **仅 8200 + 8100** |
| 跨域 | 有（两个端口） | 无（同源） |
| `DEV_MODE` | `true` | `false` |
| `ENABLE_AUTH` | 可选 | `true` |

### 4.4 开放端口说明

| 端口 | 服务 | 是否需要对外开放 |
|------|------|:---------------:|
| 8200 | FastAPI API + 前端 | ✅ 必须 |
| 8100 | 文件下载服务 | ✅ 必须 |
| 3000 | Next.js dev | ❌ 仅开发 |
| 3001 | Vite dev | ❌ 仅开发 |

---

## 5. 尚未完成的部署相关工作

| 任务 | 状态 | 优先级 | 说明 |
|------|------|:------:|------|
| ~~前端生产构建配置~~ | ✅ | ~~P0~~ | Docker 多阶段构建自动完成 |
| ~~生产启动脚本~~ | ✅ | ~~P0~~ | `scripts/deploy_linux.sh`（7步自动化） |
| ~~跨平台启动脚本~~ | ✅ | ~~P1~~ | Docker 方式天然跨平台 |
| ~~一键打包脚本~~ | ✅ | ~~P1~~ | Docker 镜像即部署包 |
| ~~双重登录问题~~ | ✅ | ~~P0~~ | v1.5 白名单雏形已修复大部分场景；**v1.7（2026-07-03）彻底根治**：认证方案从标准 `Basic` 升级为自定义 `CWAuth`，解决"生产模式退出登录后浏览器自动用旧账号重新登录"的架构级问题（浏览器原生Basic Auth缓存机制导致），详见 §3.1、`docs/cvm_deployment_test_plan.md` 第四轮 |
| workspace 基于用户名隔离 | ✅ | ~~P1~~ | **已完成（2026-07-02）**：`session_id` 前端改为从 `/auth/me` 获取的登录用户名；后端全部相关路由（workspace/*、sop/*，共27处）强制从认证身份派生所有权，忽略客户端传参；新增自助认领旧会话接口 `POST /workspace/claim-legacy-session` + admin批量迁移脚本 `scripts/migrate_user_isolation.py`。详见 `docs/user_management_module_design.md` |
| 用户自助改密码 | ❌ | P2 | `/auth/change-password` API（属批次2账号管理Web UI范围，设计已定稿待排期，详见`docs/user_management_module_design.md`§十四） |
| ~~Tailwind CSS 本地化~~ | ✅ | ~~P3~~ | Docker 构建阶段自动完成 Tailwind 离线编译 + CDN 替换，内网无需外网访问 |
| 任务历史按用户隔离 | ✅ | ~~P3~~ | **已完成（2026-07-02）**：`/sop/history`列表强制按登录用户过滤，13个记录详情/分析端点所有权校验，批量删除自动剔除越权记录 |
| ~~账户锁定计数器并发竞态~~ | ✅ | ~~P2~~ | **已修复（2026-07-03）**：`_failure_tracker`加锁保证原子性 + 同一份凭证短时间窗口内去重，避免浏览器缓存的失效凭证被并发后台请求误判成多次"主动输错密码"提前触发锁定，详见 `docs/cvm_deployment_test_plan.md` 第四轮 |
| `deploy_manual.sh` 依赖检测硬编码 `dpkg` | ❌ | P4（低） | RPM系发行版（CentOS/RHEL/TencentOS等）下检测静默失效，仅影响非Docker手动部署路径；建议改为先探测`/etc/os-release`分支处理，详见`docs/project_status_summary.md`第20项 |

---

## 6. 安全注意事项

| 项目 | 当前状态 | 风险等级 | 说明 |
|------|---------|:--------:|------|
| 传输加密 (HTTPS) | ❌ 未配置 | 中 | 内网可接受，密码以 Base64 明文传输 |
| 密码存储 | ✅ bcrypt 哈希 | 低 | 即使泄露也不可逆 |
| 暴力破解防护 | ✅ 账户锁定 | 低 | 5 次失败锁定 15 分钟；**v1.7修复**：加锁+同凭证去重，避免并发误锁定的同时不削弱真实暴力破解防护（不同密码仍正常分别计数） |
| 认证方案 | ✅ 自定义 `CWAuth` | 低 | v1.7起从标准 `Basic` 升级，避免浏览器对认证凭证的原生缓存/自动重发导致"退出登录"失效，详见 §3.1 |
| 账户有效期 | ✅ valid_until 字段 | 低 | 过期账户自动拒绝，无需手动删除；格式错误保守拒绝 |
| 密码传输 | ⚠️ 依赖 HTTPS/内网 | 中 | 自助改密/管理员改密/重置密码上线前必须确认 HTTPS 或可信内网+二层防护，见 §3.3 |
| 数据隔离 | ✅ 按登录用户名 | 低 | **已修复（2026-07-02）**：`session_id`统一为登录用户名，后端从认证身份强制派生，不再信任客户端传参；详见`docs/user_management_module_design.md` |
| LLM API Key | ✅ admin-only（API层） | 低 | 页面壳子`/llm-manager`已公开（v1.7），但具体管理API（`/manage/*`等）仍强制admin校验，普通用户调用会收到403+友好提示，无法实际访问密钥/渠道配置 |

---

*文档创建日期：2026-03-27*  
*v1.1 更新日期：2026-03-31*  
*v1.2 更新日期：2026-04-09（修复双重登录、新增 workspace 用户名隔离 TODO）*  
*v1.3 更新日期：2026-06-01（新增 valid_until 账户有效期指引；补充 §3.3 字段说明和重启生效说明；日常运维命令补充 sudo；补充 docker compose 兼容说明）*  
*v1.5 更新日期：2026-07-02（账户存储迁移至 SQLite + 新增「用户管理」Web UI 与自助改密，`users.yaml` 降级为迁移前/灾备兜底文件；详见 `docs/user_management_module_design.md`）*  
*v1.6 更新日期：2026-07-02（首个管理员账户零配置自动创建；修复 `deploy_linux.sh` 遗留占位哈希yaml导致永久锁死的隐患；`docker-compose.yml` 用户配置改为整目录挂载；详见 `docs/user_management_module_design.md` §二十）*  
*v1.7 更新日期：2026-07-03（CVM第四轮部署测试：认证方案从标准`Basic`升级为自定义`CWAuth`，根治退出登录无法切换账号问题；`/`、`/llm-manager`页面壳子改为公开白名单；修复账户锁定计数器并发竞态+误锁定；四种部署方式——Docker单用户/非Docker手动多用户/Docker离线/Docker在线多用户常驻——全部测试通过；详见 `docs/cvm_deployment_test_plan.md` 第四轮）*  
*对应分支：main*
