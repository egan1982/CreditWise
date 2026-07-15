# 代码保护方案合理性审计报告

> **审计日期**：2026-07-15
> **审计对象**：`docs/code-protection-plan.md`（v1.4，2026-07-14）
> **审计目标**：评估方案是否满足核心约束——"代码编译/加密后，仍可在新服务器上通过 Docker 离线部署"
> **审计结论**：**通过**（方案架构合理），附带 **5 个实施前必须补齐的衔接缺口** 和 **6 项独立确认的合理设计**

---

## 目录

- [1. 审计范围与方法](#1-审计范围与方法)
- [2. 总体结论](#2-总体结论)
- [3. 核心约束逐层验证](#3-核心约束逐层验证)
- [4. 合理设计确认清单](#4-合理设计确认清单)
- [5. 衔接缺口与修正建议](#5-衔接缺口与修正建议)
- [6. 未覆盖风险点](#6-未覆盖风险点)
- [7. 实施建议](#7-实施建议)

---

## 1. 审计范围与方法

### 1.1 审计范围

| 维度 | 覆盖内容 |
|------|----------|
| 被审文档 | `docs/code-protection-plan.md`（v1.1 → v1.4 全部修订历史） |
| 关联代码 | `docker/Dockerfile`、`docker/docker-compose.yml`、`scripts/prepare_offline.sh`、`scripts/deploy_offline.sh` |
| 关联文档 | `docs/cvm_deployment_test_plan.md`（第四轮测试记录）、`docs/user_management_module_design.md`（v1.3 用户管理模块评估） |
| 审计基准 | 分支 `main` @ `0a7f68b`（2026-07-15 最新状态） |

### 1.2 审计方法

1. **逐层穿透测试**：以"Docker 离线部署"为约束条件，逐一评估 Layer 1/2/3 对 `prepare_offline.sh` → `deploy_offline.sh` 全链路的影响。
2. **清单交叉验证**：对比文档中各代码块（`CORE_MODULES`、`DO_NOT_COMPILE`、`Dockerfile.compiled` COPY 清单、`KEEP_CLEAR`）之间的一致性。
3. **边界场景推演**：模拟"攻击者通过 `docker exec`/`docker save`/宿主机文件系统"三条路径尝试读取源码的结果。
4. **已有测试记录反向验证**：参考 `cvm_deployment_test_plan.md` 第四轮测试期间发现的 7 个真实 bug，评估方案的风险控制是否覆盖同类问题。

---

## 2. 总体结论

> **方案架构合理，核心约束"编译后仍可 Docker 离线部署"在技术上完全可实现。不需要推翻方案，但实施前必须补齐 5 个与现有部署体系的衔接缺口。**

| 评估维度 | 结论 | 证据 |
|:---|:---:|------|
| 三层架构合理性 | ✅ 通过 | 鉴权→编译→分发，层次清晰，每层可独立验证 |
| Cython 作为核心工具选择 | ✅ 通过 | 成本可控（2-3天）、保护效果显著（源码→二进制）、不破坏运行时 |
| 对 Docker 离线部署的兼容性 | ⚠️ 有条件通过 | 原理可行，但文档与现有脚本之间存在 5 个衔接缺口需补齐 |
| FastAPI 路由保护策略 | ✅ 通过 | `DO_NOT_COMPILE` 清单正确排除了所有路由装饰器文件 |
| 增量式实施原则 | ✅ 通过 | §2.4 的四步检查流程对持续开发项目可操作性强 |
| 安全性自我保护评估 | ✅ 通过 | 方案诚实说明了 Cython 真实效果（混淆而非加速）、Ed25519 的实际防护边界 |

---

## 3. 核心约束逐层验证

### 3.1 验证模型

本项目的 Docker 离线部署完整链路：

```
prepare_offline.sh（外网机器）                    deploy_offline.sh（内网服务器）
┌─────────────────────────────┐                  ┌──────────────────────────┐
│ 1. docker compose build     │                  │ 1. docker load < image   │
│    → Dockerfile 多阶段构建   │                  │ 2. 配置 .env / users.yaml │
│ 2. docker save → .tar       │  ──── tar.gz ──→ │ 3. docker compose up -d  │
│ 3. rsync source/ → bundle   │     (传输)        │ 4. curl /health          │
│ 4. tar.gz 压缩              │                  │                          │
└─────────────────────────────┘                  └──────────────────────────┘
```

### 3.2 Layer 1：入口鉴权

| 方案路径 | prepare 阶段影响 | deploy 阶段影响 | 离线部署兼容性 |
|----------|:---:|:---:|:---:|
| **默认轻量方案**（`deploy_guard.py` + `DEPLOY_APPROVAL_TOKEN`） | 需在 `.env` 中预埋 `DEPLOY_APPROVAL_TOKEN_EXPECTED`（1 行配置） | 部署时告知目标方 `DEPLOY_APPROVAL_TOKEN` 值即可 | ✅ **零额外操作** |
| **可选 Ed25519 License**（完整方案） | 公钥预埋在镜像中（无影响） | 需额外步骤：获取目标机指纹 → 签发 `license.lic` → 挂载到容器 | ⚠️ 增加部署步骤，与"build once, deploy many"模型存在张力 |

**审计判定**：默认轻量方案对离线部署**完全无影响**，Ed25519 方案会增加一次性的部署时手动步骤。建议坚持方案自身的推荐——默认走轻量路径，仅面向外部客户时升级。**此判定不变。**

### 3.3 Layer 2：Cython 核心编译

这是评估的核心。Cython 编译发生在 Docker 镜像构建阶段（`Dockerfile.compiled` Stage 1），产生的 `.so` 文件被 COPY 进 runtime 镜像，源码随即被删除。

| 评估项 | 结果 | 说明 |
|--------|:---:|------|
| 编译是否影响 `deploy_offline.sh` | ✅ **无影响** | `deploy_offline.sh` 只做 `docker load` + `docker compose up`，不关心容器内是 `.py` 还是 `.so` |
| 编译产物是否自包含于镜像 | ✅ **是** | `.so` 文件在镜像内部，`docker save`/`load` 自动携带 |
| bind mount 目录是否受影响 | ✅ **否** | `workspace/`、`config/`、`logs/` 等是运行时数据目录，与编译无关 |
| 前端代码是否被误编译 | ✅ **否** | 前端走独立 `frontend-builder` 阶段（Node.js），不在 Cython 编译范围内 |
| 超大文件（401KB）编译风险 | ⚠️ 有风险但已覆盖 | 文档 §4.7 已识别并提供了分阶段验证策略 |

**审计判定**：Layer 2 的设计对离线部署**本质兼容**——关键保护动作（编译+清理源码）全部封装在 Docker 构建流程内，deploy 端完全无感知。

### 3.4 Layer 3：分发封装

| 方案路径 | 与现有部署体系的关系 | 离线部署兼容性 |
|----------|------|:---:|
| **方案 A**：Docker 编译版镜像（`Dockerfile.compiled`） | 需与 `docker-compose.yml` / `prepare_offline.sh` 对接（**当前未连接**，见 §5.1） | ✅ 原理可兼容 |
| **方案 B**：离线部署包（`package_protected.sh`） | 独立于现有部署脚本，更适合非 Docker 场景 | ⚠️ 对 Docker 为主的项目实际使用概率低 |

**审计判定**：方案 A 是正确的方向，但文档中的 `Dockerfile.compiled` 与项目实际的 `docker-compose.yml` / `prepare_offline.sh` 之间**没有连接点**——这是最大实施风险。

---

## 4. 合理设计确认清单

以下 6 项设计点经独立审查确认为合理有效的：

| # | 设计点 | 文档位置 | 审计确认 |
|:-:|--------|:---:|------|
| 1 | **三层架构解耦**：鉴权/编译/分发独立可验证，任一层可单独启用/回滚 | §2.2 | ✅ 层次边界清晰 |
| 2 | **Cython 定位诚实**：明确标注"混淆为主、不保证提速"，避免预期偏差 | §4.1 | ✅ 避免了常见的"加密=加速"误解 |
| 3 | **`DO_NOT_COMPILE` 清单正确性**：`sop_api.py`（51路由）、`chat_api.py`（5）、`export_api.py`（2）、`admin_api.py`（2）、`file_api.py`（6）、`user_admin_api.py`（8）全部覆盖 | §4.3 | ✅ 含 v1.3 新增的 `user_admin_api.py` |
| 4 | **`KEEP_CLEAR` 完整性**：已包含 `API/main.py`、所有 `__init__.py`、`expert_mode/__init__.py` | §4.3 | ✅ 入口文件 + 包初始化文件均在保留清单 |
| 5 | **增量式实施原则**：编译是构建期动作而非代码库状态，已稳定/新开发模块异步推进，四步检查流程吸收了 `executor.py` PEP695 真实教训 | §2.4 | ✅ 适合持续开发项目 |
| 6 | **Ed25519 非对称方案的正确性**：私钥永不下发，客户端只有公钥，解决了初版 Fernet 对称加密的自证矛盾 | §3.1 | ✅ 加密方案设计正确 |

---

## 5. 衔接缺口与修正建议

### 5.1 缺口 #1（🔴 高优先级）：`prepare_offline.sh` 与 `Dockerfile.compiled` 未连接

**现状**：

```bash
# prepare_offline.sh:67-68（当前代码）
cd "$PROJECT_ROOT/docker"
docker compose build     # ← 使用 docker-compose.yml，其 build.dockerfile 指向 Dockerfile
```

**问题**：`docker-compose.yml` 的 `build.dockerfile: docker/Dockerfile` 指向标准 Dockerfile，无法切换到编译版。当前没有任何机制让 `prepare_offline.sh` 产出受保护镜像。

**修正**：

1. 新建 `docker/docker-compose.compiled.yml`，内容与 `docker-compose.yml` 完全相同，仅改一处：
   ```yaml
   build:
     context: ..
     dockerfile: docker/Dockerfile.compiled   # ← 唯一差异
   ```
2. `prepare_offline.sh` 增加 `--protected` 参数：
   ```bash
   # 受保护模式
   if [ "$PROTECTED_MODE" = "true" ]; then
       docker compose -f docker-compose.compiled.yml build
   else
       docker compose build
   fi
   ```

### 5.2 缺口 #2（🔴 高优先级）：离线包 `source/` 目录泄露源码

**现状**：`prepare_offline.sh` 的 rsync 打包整个项目目录，所有 `.py` 源码一并进入 `offline_bundle/source/`。

**风险**：部署方有宿主机文件系统访问权限时，可直接阅读 `source/` 中的明文 `.py`。

**修正**：在 `--protected` 模式下，rsync 打包后对 `source/` 中 `CORE_MODULES` 对应路径的 `.py` 文件执行删除，或改为仅复制运行时必需的目录（`config/`、`docker/`、`scripts/deploy_offline.sh` 等）而非全量 rsync。

### 5.3 缺口 #3（🔴 高优先级）：`Dockerfile.compiled` COPY/删除 清单硬编码

**现状对比**：

| 位置 | 文件数 | 内容 |
|------|:---:|------|
| 文档 `build_cython.py` 的 `CORE_MODULES`（§4.4） | **20 个** | 含 P2 可选模块（`AI_analysis_prompts.py`、`auth_middleware.py`、`user_service.py`、`user_migration_service.py`） |
| 文档 `Dockerfile.compiled` 的 COPY 阶段（§5.1.1） | **16 个** | 不含 P2 模块，逐文件 COPY |
| 文档 `Dockerfile.compiled` 的删除阶段（§5.1.1） | **16 个** | 与 COPY 清单一致，逐文件删除 |

**风险**：两份清单硬编码、不一致——编译了 20 个但只 COPY/删除 16 个，漏掉的 4 个文件编译产物不在镜像中，且源码残留。

**修正**：

1. `Dockerfile.compiled` 的 COPY 阶段改用目录级 COPY（`COPY deepanalyze/analysis/ ./` 等），而非逐个文件列出
2. 删除阶段改为 `python -c "from build_cython import CORE_MODULES; ..."` 动态获取清单

### 5.4 缺口 #4（🟡 中优先级）：缺少统一入口脚本

**现状**：方案涉及多个独立操作（编译 → 镜像构建 → 离线打包 → 验证），但没有顶层编排脚本。

**修正**：新增 `scripts/build_protected.sh`：

```bash
#!/bin/bash
# 一站式受保护离线部署包构建
# 1. 可选本地 Cython 试编译验证（仅开发调试用）
# 2. Docker 编译版镜像构建（docker compose -f docker-compose.compiled.yml build）
# 3. 离线包打包（复用 prepare_offline.sh --protected）
# 4. 端到端验证（解压 → deploy_offline.sh → curl 回归测试）
```

### 5.5 缺口 #5（🟡 中优先级）：验收标准未覆盖离线部署路径

**现状**：§6.2 验收标准中的"Docker 验证"仅覆盖 `docker run`，未覆盖离线部署端到端。

**修正**：§6.2 补充验收项：

| 测试项 | 标准 |
|--------|------|
| **Docker 离线部署验证**（v1.5 新增） | `prepare_offline.sh --protected` → 解压到隔离目录 → `deploy_offline.sh` → `curl /health` 200 → `curl /llm-manager/` 200 → `main.css` 大小正常 → `pytest` 通过 → 容器内 `find /app -name "rule_mining.py"` 无输出（确认源码已清理） |

---

## 6. 未覆盖风险点

以下风险点在方案设计中已覆盖，但审计确认其缓解措施需在实施中强制执行：

| # | 风险 | 方案覆盖位置 | 实施强制要求 |
|:-:|------|:---:|------|
| 1 | 超大文件（401KB）C 编译器限制 | §4.7.2 + §4.7.3 | 必须在 Docker 环境（非本地）按分阶段验证执行，不可跳过 |
| 2 | Python 版本绑定（`.so` 绑定 3.12） | §7.1 | Dockerfile.compiled 的 compiler 和 runtime 阶段必须用相同 Python 基础镜像 |
| 3 | 开发迭代中引入新语法导致编译失败 | §2.4.4（四步检查第④项，v1.4 新增） | 每次纳入编译清单前必须重新执行，不可复用历史审计结论 |
| 4 | `validators.py` eval() 沙箱逃逸 | §4.5 | Cython 编译不修复 eval() 安全问题，需先在代码层面加固 |
| 5 | 镜像分层中残留 .py 源码 | §5.1.1 删除步骤 | 必须确认 `COPY --from` 不会带入 compiler 阶段的 .py 中间文件 |

---

## 7. 实施建议

### 7.1 分支策略

```
main                      ← 稳定主干
  └─ feature/code-protection  ← 当前分支，代码保护开发（2026-07-15 创建）
```

### 7.2 交付物优先级排序

| 优先级 | 交付物 | 预估工时 | 依赖 |
|:---:|------|:---:|------|
| P0 | `build_cython.py`（Cython 编译脚本） | 0.5 天 | 无 |
| P0 | `docker/Dockerfile.compiled`（受保护版 Dockerfile） | 0.5 天 | `build_cython.py` |
| P0 | `API/deploy_guard.py`（轻量部署审批） | 0.2 天 | 无 |
| P1 | `docker/docker-compose.compiled.yml` | 0.1 天 | `Dockerfile.compiled` |
| P1 | `prepare_offline.sh` 增加 `--protected` 参数 | 0.3 天 | `docker-compose.compiled.yml` |
| P1 | 离线包 `source/` 源码清理 | 0.2 天 | 前端编译验证 |
| P2 | `scripts/build_protected.sh`（顶层入口） | 0.3 天 | 以上全部 |
| P2 | `docs/code-protection-plan.md` v1.5 修订 | 0.3 天 | 全部实施完成 |
| P3 | CI/CD 集成（`.github/workflows/build-protected.yml`） | 0.5 天 | 全部验证通过 |

### 7.3 验收流程

```
1. python build_cython.py --dry-run           # 确认编译范围
2. python build_cython.py --yes --replace     # 本地试编译（开发验证用）
3. pytest tests/ -x                           # 全量回归，失败即停
4. build_cython.py --clean                    # 恢复开发环境
5. prepare_offline.sh --protected             # Docker 构建 + 打包
6. [隔离目录] deploy_offline.sh               # 模拟内网部署
7. curl 全量功能回归                          # /health、首页、LLM Manager、API认证、main.css
8. docker exec find /app -name "rule_mining.py"  # 必须无输出（源码已清理）
```

---

*审计文档创建日期：2026-07-15*
*审计执行：基于 `docs/code-protection-plan.md` v1.4 + 项目代码 `main` @ `0a7f68b`*
*对应分支：`feature/code-protection`*
