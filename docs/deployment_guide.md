# CreditWise 部署指南

> 支持 Docker 部署（推荐）和非 Docker 手动部署，覆盖 Win/Mac/Linux 三个平台。

---

## 部署方式速览

| 方式 | 适用场景 | 平台 | 联网需求 |
|------|---------|------|:--:|
| Docker 在线部署 | 有外网访问的标准部署 | Linux | 是 |
| Docker 离线部署 | 内网无外网访问 | Linux | 否 |
| 非 Docker 手动部署 | Docker 不可用的环境 | Win/Mac/Linux | 否（离线包） |

---

## 一、Docker 在线部署（推荐）

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
2. 自动检查端口占用和磁盘空间
3. 自动安装 Docker（如未安装）
4. 配置环境变量和加密密钥
5. 构建镜像并启动服务

### 手动 Docker 启动

```bash
# 单用户模式
cd docker && docker-compose up -d

# 内网多用户模式
cd docker && ENABLE_AUTH=true docker-compose up -d
```

---

## 二、Docker 离线部署

### 2.1 在有外网的机器上准备离线包

```bash
chmod +x scripts/prepare_offline.sh
./scripts/prepare_offline.sh
```

产出：`creditwise_offline_bundle.tar.gz`

包含：
- `images/` — python:3.12-slim + node:18-slim Docker 镜像
- `wheels/` — 全部 Python 依赖的 wheel 文件
- `npm-cache/` — 前端 Node.js 依赖
- `tailwind/` — LLM Manager UI 静态资源

### 2.2 传输到内网服务器

```bash
scp creditwise_offline_bundle.tar.gz user@intranet-server:/opt/
ssh user@intranet-server
cd /opt && tar -xzf creditwise_offline_bundle.tar.gz
```

### 2.3 在内网服务器上部署

```bash
chmod +x scripts/deploy_offline.sh
./scripts/deploy_offline.sh
```

---

## 三、Docker 服务管理

```bash
# 查看日志
cd docker && docker-compose logs -f

# 停止服务
cd docker && docker-compose down

# 重启服务（单用户）
cd docker && docker-compose up -d

# 重启服务（多用户）
cd docker && ENABLE_AUTH=true docker-compose up -d
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

## 五、部署模式切换

通过在 `.env` 中设置 `ENABLE_AUTH`：
- `ENABLE_AUTH=false`（或不设置）：单用户模式，无需登录
- `ENABLE_AUTH=true`：内网多用户模式，Basic Auth 认证

多用户模式需额外配置 `config/users.yaml`：
1. 复制模板：`cp config/users.yaml.example config/users.yaml`
2. 生成密码哈希：`python scripts/hash_password.py <密码>`
3. 编辑 `config/users.yaml` 填入哈希值

---

## 六、端口说明

| 端口 | 服务 | 说明 |
|:----:|------|------|
| 8200 | 主服务 | API + 前端界面 + LLM Manager |
| 8100 | 文件服务 | 文件下载（报告、图表等） |

---

## 七、持久化数据

| 目录/文件 | 说明 |
|-----------|------|
| `workspace/` | 用户上传数据和分析结果 |
| `execution_states/` | SOP 任务执行状态 |
| `task_results/` | 任务结果缓存 |
| `logs/` | 运行日志 |
| `llm_manager.db` | LLM 渠道配置数据库 |
| `task_manager.db` | 任务历史数据库 |
| `config/users.yaml` | 用户账号配置（多用户模式） |
| `config/login_state.json` | 登录失败状态（重启保留） |

---

## 八、环境变量参考

| 变量 | 必需 | 默认值 | 说明 |
|------|:--:|--------|------|
| `ENABLE_AUTH` | 否 | `false` | 是否启用 Basic Auth |
| `LLM_MANAGER_ENCRYPTION_KEY` | 是 | — | Fernet 密钥，自动生成 |
| `API_HOST` | 否 | `0.0.0.0` | 监听地址 |
| `API_PORT` | 否 | `8200` | API 端口 |
| `CORS_ORIGINS` | 否 | — | CORS 允许的源 |
| `DEV_MODE` | 否 | `false` | 开发模式 |
| `LOG_LEVEL` | 否 | `INFO` | 日志级别 |
