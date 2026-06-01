# CreditWise 内网多用户部署指南

> 分支：`feature/intranet-multiuser`  
> 版本：v1.3.0  
> 适用场景：内网 <5 人测试使用  
> 更新：v1.3 新增账户有效期（valid_until）配置指引，补充用户配置字段说明和运维命令

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
2. 浏览器弹出 Basic Auth 登录框 → 输入各自账号密码
3. 登录后各自独立使用，通过 `session_id` 区分数据
4. 关闭浏览器后凭证清除，下次访问需重新登录

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

```
请求 → Basic Auth 中间件 → 角色检查 → 路由处理
            │
     ┌──────▼──────┐
     │ users.yaml   │  bcrypt 哈希密码
     │ (服务器本地)   │  max_failures=5, lockout=15min
     └─────────────┘
```

### 3.2 路由权限表

| 路由 | 认证要求 | 角色要求 |
|------|---------|---------|
| `/` (首页 HTML), `/favicon.ico` | 无（精确匹配白名单） | 无 |
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
| `/llm-manager/` (管理页面) | 需登录 | **admin** |

### 3.3 用户管理

当前采用**管理员手动维护**模式：

```
新用户想使用 → 线下联系管理员 → 管理员执行：
  1. python scripts/hash_password.py <密码>
  2. 编辑 config/users.yaml 添加用户
  3. 重启服务生效（sudo docker restart creditwise-api）
```

不支持用户自助注册和自行修改密码（<5 人场景无需此功能）。

#### users.yaml 字段说明

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

> **注意**：修改 `users.yaml` 后无需重建镜像，**只需重启容器**即可生效：
> ```bash
> sudo docker restart creditwise-api
> ```

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
| [2/7] | 检查用户配置 | 从 `users.yaml.example` 创建 `users.yaml`，**交互式询问是否编辑** |
| [3/7] | 检查环境配置 | 从 `.env.example` 创建 `.env`，**自动生成加密密钥** |
| [4/7] | 预创建数据库文件 | `touch llm_manager.db task_manager.db`（避免 Docker 创建为目录） |
| [5/7] | 构建 Docker 镜像 | 首次约 5-10 分钟 |
| [6/7] | 启动服务 | `ENABLE_AUTH=true docker-compose up -d` |
| [7/7] | 健康检查验证 | 最多等待 30 秒确认服务启动 |

#### 部署后需手动完成

| 任务 | 命令 | 是否必须 |
|------|------|:--------:|
| 配置用户账号密码 | 编辑 `config/users.yaml`，用 `scripts/hash_password.py` 生成密码哈希（详见 §3.3） | ✅ 必须 |
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
| ~~双重登录问题~~ | ✅ | ~~P0~~ | v1.5 已修复：`/` 和 `/favicon.ico` 加入精确匹配白名单，认证统一由前端 `authFetch` 处理（commit `55fcbc5`） |
| workspace 基于用户名隔离 | ❌ | **P1** | 将 workspace 目录从 `session_随机ID` 改为登录用户名，解决同账号不同终端/清缓存后文件"丢失"问题 |
| 用户自助改密码 | ❌ | P2 | `/auth/change-password` API |
| Tailwind CSS 本地化 | ❌ | P3 | LLM Manager UI 依赖外网 CDN，内网样式缺失 |
| 任务历史按用户隔离 | ❌ | P3 | 当前所有用户共享任务历史列表 |

---

## 6. 安全注意事项

| 项目 | 当前状态 | 风险等级 | 说明 |
|------|---------|:--------:|------|
| 传输加密 (HTTPS) | ❌ 未配置 | 中 | 内网可接受，密码以 Base64 明文传输 |
| 密码存储 | ✅ bcrypt 哈希 | 低 | 即使泄露也不可逆 |
| 暴力破解防护 | ✅ 账户锁定 | 低 | 5 次失败锁定 15 分钟 |
| 账户有效期 | ✅ valid_until 字段 | 低 | 过期账户自动拒绝，无需手动删除；格式错误保守拒绝 |
| 数据隔离 | ⚠️ 按 session_id | 中 | 非强制绑定用户，不同终端/清缓存后会生成新 sessionId 导致文件"丢失"。**TODO：改为基于登录用户名隔离** |
| LLM API Key | ✅ admin-only | 低 | 普通用户无法访问管理接口 |

---

*文档创建日期：2026-03-27*  
*v1.1 更新日期：2026-03-31*  
*v1.2 更新日期：2026-04-09（修复双重登录、新增 workspace 用户名隔离 TODO）*  
*v1.3 更新日期：2026-06-01（新增 valid_until 账户有效期指引；补充 §3.3 字段说明和重启生效说明；日常运维命令补充 sudo；补充 docker compose 兼容说明）*  
*对应分支：feature/intranet-multiuser*
