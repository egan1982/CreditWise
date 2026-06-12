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

### 测试 2：切换多用户 + 恢复加密密钥

```bash
# ⚠️ 关键：新脚本生成的加密密钥与旧 llm_manager.db 不兼容
# 必须恢复旧 .env 中的 LLM_MANAGER_ENCRYPTION_KEY
cp /data/backup/.env .env
cp /data/backup/config/users.yaml config/

# 切换为多用户模式
sed -i 's/ENABLE_AUTH=.*/ENABLE_AUTH=true/' .env

# 用新的 service.sh 启动（验证从 .env 读取 ENABLE_AUTH）
./scripts/service.sh start
```

| 验证项 | 命令/方法 | 预期 |
|--------|----------|------|
| 登录弹窗 | 浏览器访问 | HTTP Basic Auth 弹窗 |
| admin 登录 | admin 密码 | 登录成功，可访问 /llm-manager |
| 普通用户登录 | sylarswwang 密码 | 登录成功，**不能**访问 /llm-manager（403） |
| 过期账户（如有） | — | 登录被拒 |

---

### 测试 3：多渠道配置验证

```bash
# 检查 LLM 渠道是否正常（API 密钥能否用旧加密密钥正确解密）
curl -s -u admin:<密码> http://localhost:8200/llm-manager/api/manage/channels | python3 -m json.tool | head -20

# 如果渠道不可用（解密失败），重新同步配置
./scripts/sync_model_configs.sh admin:<密码>
```

| 验证项 | 预期 |
|--------|------|
| local_deepseek 渠道 | 存在且状态为 active，model_name=deepseek-v4-flash |
| local_kimi 渠道 | 存在且状态为 active，model_name=kimi-k2.5 |

---

### 测试 4：`service.sh` 运维命令

```bash
./scripts/service.sh status     # 预期：显示容器运行中 + 健康检查通过
./scripts/service.sh restart    # 预期：从 .env 读取 ENABLE_AUTH=true（非硬编码）
./scripts/service.sh logs       # 预期：实时日志输出（Ctrl+C 退出）
./scripts/service.sh stop       # 预期：容器停止，端口释放
./scripts/service.sh start-noauth  # 预期：无认证模式启动
```

| 验证项 | 预期 |
|--------|------|
| restart 后 ENABLE_AUTH 正确 | 从 `.env` 读取，不硬编码 |
| status 健康检查 | 输出容器状态 + API Health: 正常 |
| stop 后端口 | 8200/8100 不再监听 |

---

### 测试 5：非 Docker 手动部署（`deploy_manual.sh`）

```bash
# 确保 Docker 服务已停止
sudo docker-compose -f docker/docker-compose.yml down

# 安装系统依赖（如未安装）
sudo apt-get install -y libgbm1 libnss3 libatk-bridge2.0-0 libxkbcommon0

./scripts/deploy_manual.sh
# 选择 [2] 内网多用户
```

| 验证项 | 命令/方法 | 预期 |
|--------|----------|------|
| 依赖检查 | 看脚本输出 | Python ≥ 3.10 ✓、Node ≥ 18 ✓、系统库 ✓ |
| 端口检查 | 看脚本输出 | 8200+8100 可用 |
| venv 创建 | `ls .venv/bin/python3` | 存在 |
| 健康检查 | `curl -s http://localhost:8200/health` | `{"status":"healthy"}` |
| 日志 | `tail -f logs/server.log` | 无 ERROR |

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

- [ ] 单用户模式：无认证直接访问
- [ ] 多用户模式：Basic Auth 弹窗，正确用户可登录
- [ ] admin 可访问 /llm-manager，普通用户不可（403）
- [ ] LLM 渠道配置正常可用
- [ ] service.sh 全套运维命令正常
- [ ] 非 Docker 部署可正常启动并通过健康检查
