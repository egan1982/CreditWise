# CVM 新部署方案验证测试计划

> CVM 环境：`fjzheng@fjzheng.devcloud.woa.com:36000`，项目路径 `/data/CreditWise`

---

## 一、当前环境

| 维度 | 状态 |
|------|------|
| Git 分支 | `feature/intranet-multiuser` (commit `5f38226`，落后 main 7 commits) |
| Docker 容器 | `creditwise-api`（运行 10 天，镜像 `creditwise:latest` 1.5GB） |
| 端口 | 8200（API+前端） + 8100（文件下载服务） |
| 认证 | 已启用 Basic Auth |
| 用户 | admin, fjzheng（管理员）；sylarswwang, gurayzhang, laughingtan, webberwu（普通用户） |
| 数据 | `llm_manager.db` + `task_manager.db` + `workspace/` + `execution_states/` |
| 其他 | 同主机运行 AI_Trader 项目，端口不冲突 |

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

- [ ] 测试 1：Docker 单用户模式 — 无认证可访问，端口自检通过
- [ ] 测试 2：Docker 多用户 + service.sh — 401 保护，从 .env 读配置，6 用户正常
- [ ] 测试 3：离线 Docker 部署 — 端口/磁盘自检通过，服务健康
- [ ] 测试 4：非 Docker 手动部署 — Python/node 依赖检查，pip 安装，服务启动，401 保护
- [ ] 全部模式：8200+8100 双端口正常监听
- [ ] 全部模式：`curl /health` 返回 `{"status":"healthy"}`
