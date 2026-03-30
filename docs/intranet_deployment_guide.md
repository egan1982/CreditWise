# CreditWise 内网多用户部署指南

> 分支：`feature/intranet-multiuser`  
> 版本：v1.0.0-beta.1  
> 适用场景：内网 <5 人测试使用

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
| `/health`, `/docs` | 无 | 无 |
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
  3. 重启服务生效
```

不支持用户自助注册和自行修改密码（<5 人场景无需此功能）。

---

## 4. 部署步骤

### 4.1 环境准备

| 依赖 | 版本 | 说明 |
|------|------|------|
| Python | 3.8+ | 后端 |
| Node.js | 16+ | 仅构建前端时需要 |
| 端口 8200 | 开放 | API 服务 |
| 端口 8100 | 开放 | 文件下载服务 |

### 4.2 部署流程

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
| 前端生产构建配置 | ❌ | P0 | `npm run build` + FastAPI 提供静态文件 |
| 生产启动脚本 | ❌ | P0 | `start_production.ps1` |
| 跨平台启动脚本 | ❌ | P1 | Linux/Mac 版 |
| 一键打包脚本 | ❌ | P1 | 含依赖的部署包 |
| 用户自助改密码 | ❌ | P2 | `/auth/change-password` API |

---

## 6. 安全注意事项

| 项目 | 当前状态 | 风险等级 | 说明 |
|------|---------|:--------:|------|
| 传输加密 (HTTPS) | ❌ 未配置 | 中 | 内网可接受，密码以 Base64 明文传输 |
| 密码存储 | ✅ bcrypt 哈希 | 低 | 即使泄露也不可逆 |
| 暴力破解防护 | ✅ 账户锁定 | 低 | 5 次失败锁定 15 分钟 |
| 数据隔离 | ⚠️ 按 session_id | 中 | 非强制绑定用户，但实际不会冲突 |
| LLM API Key | ✅ admin-only | 低 | 普通用户无法访问管理接口 |

---

*文档创建日期：2026-03-27*  
*对应分支：feature/intranet-multiuser*
