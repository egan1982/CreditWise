# CreditWise Docker 部署指南

## 快速开始

### 前置条件

- Docker 已安装
- Docker Compose 已安装
- **不需要 GPU**（使用外部 LLM API）

---

## 部署方式

### 方式一：私有化单用户（默认）

```bash
cd docker
docker-compose up -d
```

访问 `http://localhost:8200` 即可使用，无需登录。

### 方式二：内网多用户

```bash
# 1. 准备用户配置
cp config/users.yaml.example config/users.yaml

# 2. 生成密码哈希（在宿主机或容器内执行）
docker-compose run --rm creditwise python scripts/hash_password.py admin123

# 3. 编辑 config/users.yaml，填入哈希值

# 4. 启用认证启动
ENABLE_AUTH=true docker-compose up -d
```

访问 `http://<服务器IP>:8200`，浏览器弹出登录框。

---

## 端口说明

| 端口 | 服务 | 说明 |
|------|------|------|
| 8200 | FastAPI API + 前端 | 主服务端口 |
| 8100 | 文件下载服务 | 工作区文件下载 |

---

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `ENABLE_AUTH` | `false` | 启用 Basic Auth 认证 |
| `DEEPSEEK_API_KEY` | — | DeepSeek API 密钥 |
| `OPENAI_API_KEY` | — | OpenAI API 密钥 |
| `API_HOST` | `0.0.0.0` | 监听地址 |
| `API_PORT` | `8200` | API 端口 |
| `DEV_MODE` | `false` | 开发模式 |
| `CORS_ORIGINS` | — | CORS 允许的来源（生产模式一般不需要） |

---

## 持久化数据

以下目录通过 volume 挂载，容器重启不丢失：

| 宿主机路径 | 容器内路径 | 说明 |
|-----------|-----------|------|
| `./workspace/` | `/app/workspace/` | 用户上传的数据和生成的文件 |
| `./execution_states/` | `/app/execution_states/` | SOP 任务执行状态 |
| `./task_results/` | `/app/task_results/` | SOP 任务结果缓存 |
| `./logs/` | `/app/logs/` | 运行日志 |
| `./llm_manager.db` | `/app/llm_manager.db` | LLM 渠道配置 |
| `./task_manager.db` | `/app/task_manager.db` | 任务历史记录 |
| `./config/users.yaml` | `/app/config/users.yaml` | 用户账号（仅内网模式） |

---

## 常用命令

```bash
# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 重新构建镜像（代码更新后）
docker-compose build --no-cache
docker-compose up -d

# 进入容器调试
docker-compose exec creditwise bash

# 生成密码哈希
docker-compose run --rm creditwise python scripts/hash_password.py <密码>
```

---

## 镜像大小估算

| 组件 | 大小 |
|------|------|
| Python 3.12 基础镜像 | ~150MB |
| Python 依赖 | ~500MB |
| 前端构建产物 | ~50MB |
| 项目代码 | ~30MB |
| **总计** | **~730MB** |

---

*文档更新日期：2026-03-27*
