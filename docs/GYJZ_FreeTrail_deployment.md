# GYJZ FreeTrail 部署操作指南

> **适用版本**：`feature/GYJZ_FreeTrail` 分支加密纯代码包  
> **试用截止**：2026-10-31  
> **目标环境**：Linux 内网服务器（无外网访问）

---

## 前置条件

| 角色 | 机器 | 条件 |
|------|------|------|
| 接收方 IT 人员 | 可联网电脑（Windows / Mac / Linux） | 安装 Docker |
| 目标服务器 | 内网 Linux 服务器（无外网） | 安装 Docker + Docker Compose |

### Docker 安装指引

- **Windows**：下载 [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)，安装后启动 Docker Desktop，右下角系统托盘 Docker 图标显示 "Engine running" 即可。另需安装 [Git for Windows](https://git-scm.com/download/win)（提供 Git Bash 终端，用于执行 `.sh` 脚本）。后续所有命令在 **Git Bash** 中执行，不要使用 CMD 或 PowerShell。
- **Mac**：下载 [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/)（Apple Silicon 选 Apple Chip 版本，Intel 选 Intel Chip 版本）
- **Linux**：
  ```bash
  curl -fsSL https://get.docker.com | sudo bash
  sudo systemctl enable --now docker
  sudo usermod -aG docker $USER   # 需重新登录生效
  ```

> 验证安装：`docker --version` 输出 24.x 或以上即可。

---

## 一、邮件接收

> 收到 `creditwise_protected_src_GYJZ_FreeTrail.tar.gz`（约 31MB）后保存到可联网电脑的本地目录。

---

## 二、可联网电脑：构建 Docker 离线包

> 以下步骤在**可联网电脑**上操作。
>
> - **Windows**：安装 [Git for Windows](https://git-scm.com/download/win)（自带 Git Bash 终端），在 Git Bash 中执行以下命令
> - **Mac**：打开「终端」应用
> - **Linux**：打开系统终端

### 步骤 1：解压纯代码包

```bash
# Linux / Mac
tar -xzf creditwise_protected_src_GYJZ_FreeTrail.tar.gz

# Windows（Git Bash 终端）
tar -xzf creditwise_protected_src_GYJZ_FreeTrail.tar.gz
```

解压后目录结构：
```
dist_protected/
├── scripts/
│   └── setup_protected.sh    ← 下一步要执行的一键构建脚本
├── docker/
│   └── docker-compose.yml    ← compose 配置
├── deepanalyze/              ← 已编译的加密算法（.so）
├── API/                      ← Web 服务入口
├── llm_manager_integrated/   ← LLM 管理前端 + 后端
├── demo/                     ← 主前端
└── ...                       ← 其他运行时文件
```

### 步骤 2：执行 setup_protected.sh --build

```bash
cd dist_protected
chmod +x scripts/setup_protected.sh
./scripts/setup_protected.sh --build
```

脚本自动完成：
1. 创建 `.env`（环境变量配置）
2. 生成加密密钥（LLM Manager 渠道 API Key 存储所需）
3. 预创建 `task_manager.db` / `llm_manager.db`
4. 对齐 Dockerfile Python 版本（3.12 → 3.11）
5. `docker compose build`（构建镜像，约 5-10 分钟，需外网拉取基础镜像）
6. `docker save`（导出镜像为 tar 文件）
7. 打包为 `creditwise_offline_YYYYMMDD_HHMMSS.tar.gz`

> 构建完成后，终端输出离线包文件名，例如 `creditwise_offline_20260716_173045.tar.gz`。

---

## 三、上传至内网服务器

> 线下传输方式任选：U 盘 / 移动硬盘 / 内网共享文件夹 / SCP 等。

```bash
# SCP 示例（内网可通时）
scp creditwise_offline_YYYYMMDD_HHMMSS.tar.gz user@内网服务器IP:/opt/

# 或通过 U 盘直接拷贝到服务器目录
```

---

## 四、内网 Linux 服务器：部署

> 以下步骤在**内网 Linux 服务器**上操作。以下以解压到 `/opt/CreditWise` 为例。

### 步骤 1：解压离线包

```bash
mkdir -p /opt/CreditWise
tar -xzf /opt/creditwise_offline_YYYYMMDD_HHMMSS.tar.gz -C /opt/CreditWise/
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
    │   └── deploy_offline.sh        ← 部署脚本
    ├── config/
    │   └── users.yaml.example       ← 用户配置模板
    └── .env                         ← 环境变量
```

### 步骤 2：执行部署脚本

```bash
cd /opt/CreditWise/source
chmod +x scripts/deploy_offline.sh
./scripts/deploy_offline.sh
```

脚本交互提示：
```
[2/4] 选择部署模式
  [1] 单用户模式 — 无需登录认证
  [2] 内网多用户 — Basic Auth 认证

请选择 [1/2] (默认: 2):    ← 输入 2 或直接回车（试用版必须选择此模式）
```

脚本自动完成：
1. `docker load`（加载镜像，无需外网）
2. 交互式选择部署模式
3. 配置环境变量
4. `docker compose up -d`（启动服务，**不执行 build**）

### 步骤 3：验证服务状态

```bash
# 检查容器是否运行
docker ps | grep creditwise

# 健康检查
curl http://localhost:8200/health
# 正常输出: {"status":"healthy"}

# 查看初始 admin 密码（也可以直接用 admin123）
docker logs creditwise-api 2>&1 | grep "首次启动" -A4
```

---

## 五、admin 首次登录

| 项目 | 值 |
|------|------|
| 浏览器访问 | `http://<服务器IP>:8200` |
| 用户名 | `admin` |
| 初始密码 | `admin123` |

> 首次登录会被强制要求修改密码。修改后使用新密码重新登录。

---

## 六、配置 LLM Manager（渠道管理）

1. 登录后进入「LLM Manager」页面
2. 点击「新建渠道」，填写以下信息：

| 字段 | 说明 | 示例 |
|------|------|------|
| 渠道名称 | 自定义标识 | `DeepSeek-Prod` |
| 渠道类型 | 选择对应的 API 类型 | `openai` / `deepseek` / `custom` |
| 基础 URL | API 端点地址 | `https://api.deepseek.com/v1` |
| API Key | 平台分配的密钥 | `sk-xxxx...` |
| 模型 | 模型名称 | `deepseek-chat` |

3. 点击「测试」验证连通性
4. 点击「保存」

> 如有多个渠道，重复以上步骤。配置完成后可进入 SOP 任务页执行评分卡 / 规则挖掘。

---

## 七、创建终端用户

1. admin 登录后，点击右上角头像菜单 →「用户管理」
2. 点击「新建用户」
3. 填写用户信息：

| 字段 | 说明 |
|------|------|
| 用户名 | 登录名（英文），如 `zhangsan` |
| 角色 | 普通用户选 `user`，管理员选 `admin` |
| 部门 | 可选，如 `风控部` |
| 有效期 | 试用版统一截止 2026-10-31（已锁定，无需填写） |

4. 点击「保存」，系统弹出一次性初始密码（请记录后告知对应用户）
5. 重复以上步骤创建所有需要的用户

> 终端用户首次登录后会被强制修改密码。后续可在「账户设置」中自助改密。

---

## 八、终端用户操作指南

用户 → 浏览器访问 http://<服务器IP>:8200 → 登录 → 进入系统。所有用户共享 LLM 渠道配置，SOP 任务各自独立执行。

### 8.1 界面总览

系统三列式布局：

| 左列（导航） | 中列（主内容） | 右列（详情） |
|------|------|------|
| 上传文件 | AI 对话 | 代码执行输出 |
| TaskType 选择 | SOP 任务结果 | 阶段结果预览 |
| 交互模式切换 | 模型选择器（底部） | 结果可视化 |
| 历史任务 | | AI 分析建议 |

### 8.2 上传数据文件

左列顶部点击 📎 按钮或拖拽文件上传。支持 CSV（`.csv`）、Excel（`.xlsx`/`.xls`）。上传后系统自动检测列类型和统计基本信息。

### 8.3 选择模型

中列底部下拉菜单选择 LLM 渠道（管理员在 LLM Manager 中配置）。普通对话和 SOP 任务均使用选中的模型。

---

### 8.4 规则挖掘任务

**方式一：自然语言启动（推荐）**

在左列 TaskType 选择「规则挖掘」，中列对话区输入描述，系统自动识别意图并提取参数：

> 💬 "帮我做规则挖掘，目标变量是 is_default，分箱用决策树方法，最多选 5 条规则"

系统识别到规则挖掘意图后弹窗确认参数，确认无误后点击「开始执行」。

**方式二：手动配置启动**

左列 TaskType 选择「规则挖掘」后，在参数配置面板中手动填写各项参数。

**关键参数（其他保留默认值即可）**：

| 参数 | 说明 | 推荐值 |
|------|------|--------|
| target_col | 好坏标签列名 | 必填 |
| mining_mode | single=单变量规则 / multi=多变量组合 | multi |
| n_vars | 每条规则最多包含几个特征 | 3 |
| max_hit_rate_filter | 单条规则最高命中率 | 0.03（3%） |

> 点击参数面板中 📖 图标可查看完整流程说明和推荐参数组合。

---

### 8.5 评分卡开发任务

**方式一：自然语言启动（推荐）**

左列 TaskType 选择「评分卡开发」：

> 💬 "做评分卡，目标变量是 is_bad，base_score 设为 600，PDO 设为 50"

**方式二：手动配置启动**

在参数配置面板中手动填写。

**关键参数**：

| 参数 | 说明 | 推荐值 |
|------|------|--------|
| target_col | 好坏标签列名 | 必填 |
| test_ratio | 测试集占比 | 0.3（30%） |
| bin_method | 分箱方法：tree/chi2/quantile | tree |
| base_score | 基准分 | 600 |
| pdo | odds 翻倍时分数变化量 | 50 |

---

### 8.6 交互模式

左列可选择两种模式：

| 模式 | 说明 |
|------|------|
| 全自动 | 一键执行到底，不暂停 |
| 专家模式 | 每个阶段完成后暂停，可审核结果后决定：<br>✅继续 / 🔄重试（修改参数后从当前阶段重跑）/ ⏸️暂缓处理 |

专家模式下，每个阶段完成后系统自动调用 AI 分析产出，生成参数优化建议（采纳/忽略）。

---

### 8.7 执行进度与结果导出

各阶段依次执行，状态图标：

| 图标 | 含义 |
|:--:|------|
| 🔵 | 正在执行 |
| ⚪ | 等待执行 |
| ✅ | 已完成 |
| ❌ | 执行失败 |

任务完成后，顶部工具栏可导出：
- **Excel** — 规则表 / 评分卡表 + 参数汇总
- **HTML** — 可视化报告（含 KS/AUC 等评估图表）
- **Word** — 正式报告文档

左侧「历史任务」可查看和加载过往任务结果。

---

## 九、服务管理命令

```bash
# 查看服务状态
cd /opt/CreditWise/source && docker compose ps

# 停止服务
docker compose -f docker/docker-compose.yml down

# 启动服务
docker compose -f docker/docker-compose.yml up -d

# 查看日志
docker logs -f creditwise-api

# 重启服务
docker compose -f docker/docker-compose.yml restart
```
