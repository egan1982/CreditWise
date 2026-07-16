# DeepAnalyze (CreditWise) 代码保护方案

> **版本**: 1.6（CVM Docker 离线部署 + 纯代码包端到端验证通过，16 项实施问题已修复）
> **日期**: 2026-07-16
> **目标**: 避免源代码直接在新服务器/PC 上部署，保护核心风控算法知识产权
> **v1.1 修正摘要**: 1) 更正 exec/eval 风险模块识别（executor.py 无风险可编译，validators.py 才是真实风险点）；2) License 机制由对称加密（Fernet，存在自证矛盾）改为非对称签名（Ed25519）；3) 机器指纹改为绑定宿主机 machine-id，避免 Docker 容器重建导致指纹漂移；4) 明确排除含 FastAPI 路由装饰器的模块，避免破坏 OpenAPI/依赖注入；5) 修复 Dockerfile 中 `.pyd` 在 Linux 阶段不存在、源码未被清理、`input()` 交互确认在 RUN 阶段静默失效等实操 bug；6) 澄清 Cython 未加类型标注时的真实性能/保护效果，避免预期偏差。
> **v1.2 修正摘要**: 1) 重新评估机器指纹绑定的必要性 —— 若部署场景是"内部多服务器/PC"而非"交付给不受控的外部客户"，**默认降级为轻量方案**（部署审批 + 环境变量开关），Ed25519 签名+机器指纹绑定保留作为面向外部客户场景的可选升级项，见 §3.0；2) 基于实际代码扫描核实 Cython 兼容性风险：待编译文件不涉及 `match/case`、walrus、PEP604 联合类型、`inspect.signature` 反射、pickle/多进程序列化，风险低于预期；但存在超大单文件（400KB+）触发 C 编译器限制的真实风险，新增"分阶段验证"实施策略，见 §4.7。
> **v1.3 修正摘要**（2026-07-07，用户管理模块上线后的增量评估，**不改变分层架构/主线策略**）：1) 新增 `API/user_admin_api.py`（含8处 `@router.*` 路由装饰器）纳入 `DO_NOT_COMPILE`，原理与 `sop_api.py` 等同——编译会破坏 OpenAPI/依赖注入，见 §1.5、§4.3；2) 认证/账户基础设施三个文件（`auth_middleware.py`、`user_service.py`、`user_migration_service.py`，均无路由装饰器/无 eval/exec）评估为**可选编译**，归入 P2 分组，理由和取舍见 §1.5；3) 明确结论：用户管理模块属于"认证基础设施"，不涉及本方案原定位保护的"核心风控算法IP"，**Layer2 已有编译清单（14个核心算法/报告引擎文件）无需变更**。
> **v1.4 修正摘要**（2026-07-14，回答"项目仍在开发中，能否先处理已开发内容再追加新功能"）：1) 新增 §2.4"增量式实施原则"，明确编译/保护是**构建期动作而非代码库状态**，已稳定模块与新开发模块可以异步推进，无需绑定处理；2) 新增"增量评估四步检查"（§2.4.4）作为纳入新模块前的常态化流程，其中第④项（新 Python 版本专属语法检查）直接源于真实教训：`executor.py` 在 §1.4 被判定"无风险可编译"后，2026-07-03 的一次开发提交在其中引入了 PEP 695 `type` 语句（Python 3.12+ 语法），导致 Python 3.10/3.11 环境下 `SyntaxError`（已修复为改用 `Union`），证明"审计一次≠永久结论"，任何持续开发的模块纳入编译清单前都要重新走一遍四步检查。
> **v1.5 修正摘要**（2026-07-15，落地 `docs/code-protection-audit.md` 四轮审计 §10.5 最终清单的 9 项发现，**本版起 Dockerfile/build_cython.py/离线部署脚本均给出可直接落地的完整代码，不再是纯设计草稿**）：
> 1. **[根因修正]** 将 `CORE_MODULES` 拆分为"默认编译"（P0+P1，14 个核心算法文件，与 Dockerfile COPY 范围严格对齐）和 `OPTIONAL_P2_MODULES`（`AI_analysis_prompts.py`/`auth_middleware.py`/`user_service.py`/`user_migration_service.py`，需显式 `--include-p2` 且扩展 Dockerfile COPY 范围才编译），根治审计发现的"P2 文件在默认路径下必然静默 SKIP、源码残留却无告警"问题（Gap #3，见 §4.3/§4.4）；
> 2. **[新增]** `build_cython.py` 编译完成后输出 `compiled_files.txt` 清单文件，SKIP 文件同时输出到 stderr 告警；`Dockerfile.compiled` 改为目录级 COPY + 按清单文件删除源码，不再逐文件硬编码（Gap #3）；
> 3. **[新增]** `docker/docker-compose.compiled.yml` + `prepare_offline.sh --protected` 参数，打通"编译版镜像构建 → 离线包打包"的连接点（Gap #1）；
> 4. **[新增]** `--protected` 模式下离线包改为"最小运行时文件集"复制（不再 rsync 全量源码后事后删除），从源头消除 `source/` 目录明文源码泄露（Gap #2，已确认这是当前**唯一实际存在、且已确认成立**的源码泄露路径）；
> 5. **[新增]** `KEEP_CLEAR` 补充 `API/deploy_guard.py`、`API/license_validator.py`（此前未被任何清单覆盖，见 Gap A）；
> 6. **[新增]** `Dockerfile.compiled` 增加 `RUN find /app -name "*.py.bak" -delete` 防御性清理（Gap B）；
> 7. **[新增]** `scripts/build_protected.sh` 统一入口脚本，串联编译→构建→打包→验证全流程；
> 8. **[新增]** §6.2 补充离线部署端到端验收项。
> 完整审计溯源见 `docs/code-protection-audit.md` §10.5-§10.6。

> **v1.6 修正摘要**（2026-07-16，CVM Docker 离线部署 + 纯代码包端到端验证，**16 项实施问题在测试中发现并修复**）：
> 
> **编译相关**（3 项）：
> 1. Dockerfile.compiled `.so` glob 前缀冲突——`rule_mining*.so` 同时匹配 `rule_mining_meta.so`，改为 `{base}.*.so`
> 2. `build_cython.py` `clean_all()` 排除 `.venv/` 目录（`rglob` 范围过宽误删虚拟环境）
> 3. `replace_py_files`/`restore_py_files` 修复 `pathlib.with_suffix` 对 `.py.bak` 双后缀问题
> 
> **部署脚本**（5 项）：
> 4. `prepare_offline.sh --protected` 修复 scripts 双层嵌套（`cp -r scripts/`→`cp -r scripts/.`）
> 5. `deploy_offline.sh` 相对路径改写为绝对路径（Docker Compose 版本间解析不一致，可致跨项目目录污染）
> 6. `deploy_offline.sh` 不再自动创建 `users.yaml`（含占位符哈希阻塞 v1.6 零配置引导）
> 7. `deploy_offline.sh` 空 `if` 块语法错误（Bash 不允许 `then/fi` 间仅含注释）
> 8. 新增 `scripts/setup_protected.sh`——纯代码包首次部署一键初始化（`.env`、加密密钥、`.db` 预创建、Dockerfile 版本对齐）
> 
> **LLM Manager**（2 项）：
> 9. `test-via-proxy` 改为直接查 DB（废弃的 `/api/models` 被认证中间件拦截返回 401）
> 10. `create_channel` logger 提前定义（修复 `UnboundLocalError`）
> 
> **产品体验**（3 项）：
> 11. admin 初始密码改为固定 `admin123`（随机密码需 `docker logs` 查看体验差，保留 `BOOTSTRAP_ADMIN_PASSWORD` 环境变量覆盖）
> 12. `deployment_guide.md` 标注预编译包 Python 版本绑定（当前 3.11）
> 13. 同步更新 `intranet_deployment_guide.md`、`user_manual.md`、`user_management_module_design.md` 相关描述
> 
> **新增工具**（3 项）：
> 14. `--output-dir` 模式——编译 `.pyd/.so` 到独立目录，源码无损（用于本地编译后部署）
> 15. MinGW-w64 便携编译器自动检测（Windows 无 MSVC 时回退，见 §4.4）
> 16. `scripts/mingw_env_setup.ps1`——便携式 MinGW 环境变量配置
> 
> 完整实施记录见本分支 commit 历史 `ac9074c..64067bf`。

---

## 目录

- [1. 项目现状分析](#1-项目现状分析)
- [2. 保护目标与分层策略](#2-保护目标与分层策略)
  - [2.4 增量式实施原则](#24-增量式实施原则应对持续开发中的项目2026-07-14-新增)
- [3. Layer 1：入口鉴权](#3-layer-1入口鉴权)
- [4. Layer 2：Cython 核心编译](#4-layer-2cython-核心编译)
- [5. Layer 3：分发封装](#5-layer-3分发封装)
  - [5.1 Docker 编译版镜像](#51-方案-adocker-编译版镜像推荐)
  - [5.2 离线部署包 --protected](#52-离线部署包prepare_offlinesh---protectedv15-重写修正-gap-1--gap-2)
  - [5.4 统一入口脚本](#54-统一入口脚本scriptsbuild_protectedshv15-新增修正-gap-4)
- [6. 实施路线](#6-实施路线)
- [7. 风险与注意事项](#7-风险与注意事项)
- [8. 附录](#8-附录)

---

## 1. 项目现状分析

### 1.1 项目概览

| 属性 | 值 |
|------|-----|
| 项目名 | `deepanalyze-creditwise` |
| 版本 | `1.0.0-beta.1` |
| 定位 | AI 驱动的信贷风控智能分析平台 |
| 构建系统 | Hatchling + setuptools (wheel 包) |
| 部署方式 | 源码部署 / Docker 镜像 |
| 分发现状 | 纯 Python 源码，无加密/混淆措施 |

### 1.2 技术栈

```
┌────────────────────────────────────────────────────┐
│  前端: Next.js 14 + React 18 (静态导出 output:export) │
│  后端: Python FastAPI + uvicorn                      │
│  数据: pandas, numpy, scipy, scikit-learn            │
│  风控: scorecardpy==0.1.9.7 (固定版本)               │
│  报告: openpyxl, python-docx, plotly, kaleido        │
│  LLM:  openai SDK (多供应商兼容)                     │
│  数据库: SQLAlchemy + SQLite                         │
│  容器: Docker 多阶段构建                              │
└────────────────────────────────────────────────────┘
```

### 1.3 代码规模

| 维度 | 数值 |
|------|------|
| Python 源文件 | **73 个** (API: 23 + deepanalyze: 50) |
| Python 源码总量 | **~2.8 MB** |
| 前端文件 | ~358 个 |

### 1.4 核心资产（需重点保护的文件）

| 优先级 | 文件 | 大小 | 说明 |
|:---:|------|------|------|
| ★★★ | `deepanalyze/analysis/task_SOP/rule_mining.py` | 401 KB | 规则挖掘核心算法（最大文件） |
| ★★★ | `deepanalyze/analysis/task_SOP/scorecard_development.py` | 286 KB | 评分卡开发核心算法 |
| ★★★ | `deepanalyze/analysis/excel_report.py` | 226 KB | Excel 报告生成引擎 |
| ★★☆ | `deepanalyze/analysis/word_report.py` | 144 KB | Word 报告生成引擎 |
| ★★☆ | `deepanalyze/analysis/html_report.py` | 176 KB | HTML 报告生成引擎 |
| ★★☆ | `deepanalyze/analysis/markdown_report.py` | 120 KB | Markdown 报告生成引擎 |
| ★★☆ | `deepanalyze/analysis/preprocessing.py` | 60 KB | 数据预处理引擎 |
| ★★☆ | `deepanalyze/analysis/task_SOP/executor.py` | 109 KB | SOP 执行引擎（**已核实：无 exec/eval，可安全编译**） |
| ★☆☆ | `deepanalyze/analysis/task_SOP/validators.py` | 46 KB | 规则/评分卡验证器（**含 `eval(rule_expr, safe_globals)`，真正的动态执行风险点**） |
| ★☆☆ | `API/sop_api.py` | 187 KB | SOP 任务管理 API（**含 51 处 FastAPI 路由装饰器，不建议 Cython 编译**） |
| ★☆☆ | `API/AI_analysis_prompts.py` | 135 KB | AI 分析提示词模板 |
| ★☆☆ | `API/chat_api.py` | 94 KB | Chat API 路由（**含 5 处路由装饰器，不建议编译**） |

> **审计更正说明**（2026-07-01 复核）：
> 1. 经代码扫描确认 `executor.py` **不含**任何 `exec()`/`eval()` 调用，此前的风险判定有误，现已重新分类为可编译模块。
> 2. 真正含 `eval()` 的文件是 `validators.py`（第 40 行 `eval(rule_expr, safe_globals)`），虽然通过 `safe_globals={'__builtins__': {}}` 做了部分沙箱化，但对象方法调用未受限，仍存在理论沙箱逃逸风险，应作为编译决策的重点审计对象。
> 3. `rule_mining.py` 已在源码层面完成安全加固：内部通过 `_safe_eval_rule()` 使用 `pd.eval()` 替代裸 `eval()`（源码注释标明 "Use safe rule evaluation instead of eval()"），说明该文件本身不存在动态执行风险，可直接编译。
> 4. `sop_api.py` / `chat_api.py` / `export_api.py` 含 FastAPI 路由装饰器，FastAPI 的 OpenAPI 生成和依赖注入依赖运行时函数签名反射，Cython 编译（尤其 `binding=False`）会破坏其功能，**不建议对这些文件做 Cython 编译**，详见 §4.3 `DO_NOT_COMPILE`。

### 1.5 用户管理模块新增文件评估（2026-07-07 补充，回答"新增用户管理大模块后本方案是否需要重新制定"）

> **结论先行**：**不需要重新制定/推翻本方案**。用户管理模块（账户 CRUD、SQLite 存储、CWAuth 认证、登录锁定）解决的是"认证基础设施"问题，与本方案原定位保护的"核心风控算法知识产权"（评分卡开发、规则挖掘等 §1.4 核心资产）是两类不同性质的资产，**Layer 2 已有的 14 个核心算法/报告引擎编译清单完全不受影响，无需变更**。仅需对新增文件做一次增量分类，结论如下：

| 新增/大幅扩充的文件 | 大小 | FastAPI 路由装饰器 | `eval`/`exec` | 分类结论 |
|---|---:|:---:|:---:|---|
| `API/user_admin_api.py`（批次2 Phase10 新增） | 13.7 KB | **8 处**（`/auth/*` + `/admin/users*`） | 无 | **必须归入 `DO_NOT_COMPILE`**——与 `sop_api.py`/`chat_api.py` 同理，编译会破坏 OpenAPI 生成/依赖注入 |
| `API/auth_middleware.py`（本次 CWAuth 改造 + 锁定并发修复后由 ~15KB 扩至 37.4 KB） | 37.4 KB | 0 处（是中间件类，非路由文件） | 无 | 编译**技术上安全**，但内容是认证中间件（bcrypt 密码校验、锁定阈值、CWAuth 方案实现），不属于"风控算法IP"——**评估为可选编译**，见下方取舍说明 |
| `deepanalyze/core/task_manager/user_service.py`（批次2 Phase9/10 新增） | 19.7 KB | 0 处 | 无 | 账户 CRUD 服务（bcrypt 哈希、用户名校验），非算法逻辑——**评估为可选编译** |
| `deepanalyze/core/task_manager/user_migration_service.py`（批次1 新增） | 6.9 KB | 0 处 | 无 | yaml→SQLite 迁移脚本，一次性工具属性更强——**评估为可选编译，优先级最低** |

**是否要把 `auth_middleware.py`/`user_service.py`/`user_migration_service.py` 纳入实际编译，取决于你对"认证实现细节是否算需要保密的资产"的判断**（例如：账户锁定的具体阈值/去重窗口、CWAuth 方案名、bcrypt 参数——这些泄露的后果是"更容易研究绕过认证的手法"，而非"核心算法被复制"，性质与 §1.4 的算法文件不同）。由于三者均无路由装饰器/无动态执行风险，编译**没有技术副作用**。

> ⚠️ **v1.5 修正（2026-07-15，源自审计 Gap #3）**：v1.3/v1.4 曾把这三个 P2 文件直接放进 `build_cython.py` 的 `CORE_MODULES` 列表（即"默认路径会编译，但 `Dockerfile.compiled` 的 COPY 阶段没有把它们复制进 compiler stage"），导致默认执行 `python build_cython.py --yes --replace` 时这些文件会静默命中 `⚠ SKIP: 文件不存在` 分支——**不报错、不编译、源码也不会被清理**，实际保护效果为零且没有任何告警。现修正为**独立的 `OPTIONAL_P2_MODULES` 列表**，默认不编译（无需你决策，直接安全跳过且有日志提示），仅当你主动执行 `--include-p2` 并同步扩展 `Dockerfile.compiled` 的 COPY 范围（见 §5.1.1）时才会被编译。这样"是否编译 P2"的决策显式化，不再依赖"恰好没被复制进 compiler stage"这种隐式行为。详见 §4.3/§4.4。

---

## 2. 保护目标与分层策略

### 2.1 保护目标

| 目标 | 描述 |
|------|------|
| **防"随手部署"** | 源码被拷贝到新机器后无法直接运行 |
| **防"源码阅读"** | 核心算法逻辑编译为二进制，无法直接阅读 |
| **防"随意复制"** | 分发产物与机器绑定，不可复制到其他服务器 |
| **不防"逆向工程"** | 无法做到绝对安全，目标是将逆向成本提升到远超重新开发的成本 |

### 2.2 三层防护架构

```
┌────────────────────────────────────────────────────┐
│                                                    │
│  Layer 1: 入口鉴权 ─ 防"顺手部署"（默认轻量方案，见 §3.0）│
│  ├─ [默认] 部署审批 + 环境变量开关                    │
│  ├─ [可选升级] 机器指纹绑定 + Ed25519 License 签名     │
│  └─ 过期时间控制                                    │
│                                                    │
│  Layer 2: 核心编译 ─ 防"源码泄漏"                    │
│  ├─ Cython .py → .pyd / .so                        │
│  ├─ 保留入口 .py 文件（可维护性）                     │
│  └─ 例外处理：动态执行模块保留明文                     │
│                                                    │
│  Layer 3: 分发封装 ─ 防"随意复制"                    │
│  ├─ Docker 编译版镜像                                │
│  ├─ 离线部署包（不包含源码）                           │
│  └─ CI/CD 自动构建流水线                             │
│                                                    │
└────────────────────────────────────────────────────┘
```

### 2.3 方案对比总览

| 方案 | 保护强度 | 性能影响 | 实施成本 | 维护成本 |
|------|:---:|:---:|:---:|:---:|
| 入口鉴权 | ★★☆☆☆ | → 无影响 | 0.5 天 | 低 |
| Cython 编译（无类型标注） | ★★★☆☆ | → 基本持平，不保证提速 | 2-3 天 | 中 |
| Nuitka 编译 | ★★★★☆ | → 持平 | 3-5 天 | 高 |
| PyArmor 加密 | ★★★☆☆ | ↓ 降低 5-15% | 1 天 | 低 |
| PyInstaller 打包 | ★★☆☆☆ | → 持平 | 1-2 天 | 中 |
| Docker 镜像 | ★★☆☆☆ | → 持平 | 0.5 天 | 低 |

> **推荐组合**: Layer 1 (Ed25519 签名) + Layer 2 (Cython) + Layer 3 → 综合保护强度 ★★★★☆（显著提高逆向门槛，非绝对不可破解）
> **性能说明**：以上 Cython 评级基于"直接编译现有 .py，不添加 `cdef` 类型标注"的现实场景 —— 该场景下 Cython 的核心价值是**混淆**而非加速，"提升 10-30%"的说法只在补充类型标注后才成立，对 401KB/286KB 级别的大文件手工加标注不现实，故本方案不将性能提升作为验收指标。

### 2.4 增量式实施原则（应对持续开发中的项目，2026-07-14 新增）

> **背景**：本项目仍在高频迭代（如 v1.3 记录的用户管理模块上线、`executor.py` 因新增语法引发的兼容性 bug），"代码保护"不能假设成一次性、终态的动作。本节回答一个反复会遇到的问题：**已开发稳定的模块可以先纳入编译/保护清单，新增功能模块延后处理，两者异步推进**——这是被允许且推荐的做法，原因和操作规范如下。

#### 2.4.1 核心认知：加密/编译是构建期动作，不是代码库的"状态"

`build_cython.py` 里的 `CORE_MODULES`/`DYNAMIC_MODULES`/`DO_NOT_COMPILE` 只是**构建时清单**，`--replace` 只在打包部署物（Docker 镜像/离线包）的那一刻执行一次；**源码仓库本身永远保持 `.py` 明文、可正常开发调试**。因此"先处理已开发内容，再追加新功能"不存在技术障碍，真正要解决的是"一个模块什么时候该被纳入编译清单"的判断问题。已编译模块之后如果还要改逻辑，标准流程是：

```
python build_cython.py --restore   # 恢复该模块为 .py，正常开发调试
...在 .py 上完成开发/修复/测试...
python build_cython.py --replace   # 确认稳定后，重新纳入编译，下次构建生效
```

#### 2.4.2 判断标准：什么样的模块可以进入编译/保护清单

| 标准 | 说明 |
|------|------|
| **稳定期** | 近 3-4 周只有零星小修复，没有功能性变更 commit |
| **接口定型** | 对外函数签名/类结构基本不再变动 |
| **属于核心 IP** | 优先编译算法核心/报告引擎类（§1.4）；认证、管理等基础设施类（如 §1.5 的用户管理模块）可长期留在"P2 可选"甚至不编译 |
| **有测试覆盖** | 编译后能靠 `pytest` 快速验证功能一致性，而非人工回归 |

#### 2.4.3 操作节奏

```
已稳定的核心算法模块（§4.3 CORE_MODULES 现有 14 个文件）
  └─ 可以现在就按 §4.7.3 分阶段验证策略推进编译

正在开发的新功能模块（如某次迭代新增的功能）
  └─ 先归入"观察期"，不纳入编译清单
  └─ 上线运行 3-4 周、无重大 bug 后，走一次"增量评估四步检查"（见 §2.4.4）
  └─ 通过检查后才追加进编译清单，下一次构建部署物时生效——
     不需要重新走一遍全量的§4.7.3分阶段验证，只需单独验证新增的这一个/几个文件
```

#### 2.4.4 增量评估四步检查（每次纳入新模块前必须重新执行，不可复用旧结论）

`executor.py` 曾在 §1.4/§4.3 被审计判定"无风险可编译"，但后续开发中被追加了 PEP 695 `type` 语句（Python 3.12+ 语法），导致低版本 Python 直接 `SyntaxError`——这说明**"审计一次 = 永久结论"是错误假设**，只要模块还在持续开发，必须在每次纳入编译清单前重新走一遍检查：

```
① 有无 FastAPI 路由装饰器（@router.*）      → 决定能否编译，见 §4.3 DO_NOT_COMPILE
② 有无新增的 eval()/exec()                  → 决定安全审计范围，见 §4.5
③ 有无 dataclass/Enum/__slots__ 等已知陷阱语法 → 结合 §4.4 annotation_typing=False 评估
④ 有无新 Python 版本专属语法（match/case、walrus、PEP604 联合类型、PEP695 type 语句等）
   → 这一项是 v1.4 新增的常态化检查项，直接源于 executor.py 的真实教训
```

四步检查全部通过才追加进 `CORE_MODULES`；任一项未通过，归入 `DO_NOT_COMPILE` 或延后到下个观察周期重新评估。

#### 2.4.5 需要避免的反模式

- ❌ 为了"赶紧上保护"，把还在改的模块强行编译 —— 会导致改一次 bug 就要重新编译一次，拖慢日常开发和调试
- ❌ 把整个仓库的编译状态和开发分支绑死 —— 编译只应发生在 CI/发布流水线，开发分支永远保持纯 `.py`
- ❌ 审计一次就当作永久结论 —— 每次纳入新模块前必须重新走一遍 §2.4.4 的四步检查（`executor.py` 已用真实 bug 证明了这一点）
- ❌ 新旧模块必须同步处理 —— 已稳定模块和新开发模块完全可以异步推进，没有绑定关系

---

## 3. Layer 1：入口鉴权

### 3.0 是否需要机器指纹绑定？（决策前置，先判断再选方案）

> **结论先行**：本项目当前场景（内部多服务器/PC 部署，防止源码随意扩散）下，**机器指纹绑定大概率不是必要项**，建议默认采用轻量方案；仅当未来交付给不受你控制的外部客户/供应商时，才升级为 §3.1-§3.5 的 Ed25519 签名 + 机器指纹方案。

**判断依据**：

| 场景 | 特征 | 是否需要机器指纹绑定 |
|------|------|:---:|
| 内部治理场景（同组织多服务器/员工 PC） | 你自己能控制部署渠道，谁能拿到部署包由你决定 | ❌ 不必要 —— Cython 编译 + Docker 镜像已解决"无源码可看"，控制**分发渠道**本身即是主要防线 |
| 外部客户/供应商托管场景 | 部署包交给你无法控制的第三方基础设施运行 | ✅ 有必要，走 §3.1-§3.5 的完整方案 |

**机器指纹绑定的真实隐性成本**（决策前应纳入考量）：

```
├─ 密钥对生成与保管流程（私钥丢失 = 所有已发 license 需重新签发）
├─ 每次客户机器变更（换硬盘/云主机迁移/K8s 弹性扩容）都要走一遍
│   "获取新指纹 → 提交申请 → 重新签发" 流程
├─ Docker/K8s 多副本部署时，各 Pod 拿到的宿主机指纹需额外设计聚合策略
└─ 客户正常运维操作（比如服务器搬迁）会意外触发"授权失败"，增加支持成本
```

**默认轻量方案（推荐起点）**：

```python
# API/deploy_guard.py —— 轻量部署审批开关，替代完整机器指纹绑定
"""
不做强绑定，只做"部署需要经过你知情"的软控制。
适用于：内部多服务器/PC 部署，防止源码被随意复制运行，而非防范外部商业窃取。
"""
import os

def check_deploy_approved() -> bool:
    """
    启动时校验部署审批标记。
    你只需为每次新部署下发一个 DEPLOY_TOKEN（可以是简单的约定字符串/短期有效码），
    不涉及密钥管理、机器指纹采集等复杂度。
    """
    expected = os.environ.get("DEPLOY_APPROVAL_TOKEN_EXPECTED", "")
    actual = os.environ.get("DEPLOY_APPROVAL_TOKEN", "")
    if not expected:
        # 未配置期望值 → 视为不启用审批门槛（开发环境）
        return True
    return actual == expected
```

集成方式与 §3.3 相同（在 `create_app()` 最前面调用 `check_deploy_approved()`），**实施成本从 2-3 天降到 1-2 小时**，且不引入密钥管理、machine-id 挂载等运维负担。

**升级路径**：若未来确定要对外交付给不受控的客户，届时再启用下方 §3.1-§3.5 的完整 Ed25519 签名 + 机器指纹方案，两者可以平滑切换（`license_validator.py` 与 `deploy_guard.py` 可以并存，按 `LICENSE_PUBLIC_KEY` 是否配置自动决定走哪套逻辑）。

---

### 3.1 设计原理（完整方案 —— 面向外部客户交付场景，按需启用）

应用启动时，采集当前机器的唯一特征码，与授权文件 `license.lic` 进行**签名验证**。校验不通过则拒绝启动。

> ⚠️ **架构修正说明（2026-07-01）**：初版方案使用 `Fernet` 对称加密实现 License 校验，存在根本性缺陷 —— 对称加密要求客户端持有与签发端相同的密钥才能完成解密校验，这意味着客户端环境变量中必然存在可用于**自行签发任意 license** 的密钥，完全失去保护意义。现修正为**非对称签名方案（Ed25519）**：
> - 你保留私钥（`private_key.pem`，永不下发，仅用于签发 license）
> - 客户端仅内置公钥（`PUBLIC_KEY`，可以安全公开，只能验签、不能签发新 license）
>
> 同时，机器指纹采集方式也做了修正：原方案基于 `platform.node()` / MAC 地址等容器内部信息，在 Docker 分发场景下**每次容器重建指纹都会变化**（Docker 虚拟网卡、随机 hostname），导致合法客户被拒绝启动。修正为**优先读取挂载自宿主机的 `/etc/machine-id`**，仅在该文件不存在时才回退到进程内特征采集。

### 3.2 授权验证器（Ed25519 签名版）

```python
# API/license_validator.py
"""
机器授权验证器（非对称签名版）—— 防止源码被拷贝到未授权机器上运行

设计要点：
1. 使用 Ed25519 签名算法：私钥仅在签发端（你的安全环境）持有，
   客户端只内置公钥，公钥泄露不影响安全性（无法用公钥伪造签名）。
2. 机器指纹优先绑定宿主机 /etc/machine-id（需在 Docker 中以只读方式挂载），
   避免容器重建导致指纹漂移；本地/非容器部署回退到进程内特征采集。
"""

import base64
import hashlib
import json
import os
import platform
import socket
import uuid
from datetime import datetime
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

# 客户端内置公钥（可安全公开，仅用于验签，无法伪造新 license）
# 由 scripts/license_signer.py --genkey 生成密钥对时输出，替换为你自己的公钥
_PUBLIC_KEY_B64 = os.environ.get("LICENSE_PUBLIC_KEY", "")

_LICENSE_PATH = Path(__file__).parent.parent / "license.lic"

# Docker 部署时，需在 docker run / compose 中以只读方式挂载宿主机 machine-id：
#   -v /etc/machine-id:/etc/host-machine-id:ro
_HOST_MACHINE_ID_PATH = Path("/etc/host-machine-id")   # 容器内挂载点
_LOCAL_MACHINE_ID_PATH = Path("/etc/machine-id")        # 非容器部署（Linux）


def get_machine_fingerprint() -> str:
    """
    采集机器唯一指纹。
    优先级：宿主机挂载的 machine-id > 本机 machine-id > 进程内特征采集（回退，稳定性较弱）
    """
    for p in (_HOST_MACHINE_ID_PATH, _LOCAL_MACHINE_ID_PATH):
        if p.exists():
            raw = p.read_text().strip()
            return hashlib.sha256(raw.encode()).hexdigest()[:16]

    # 回退方案：仅适用于非 Docker 的直接部署场景，Docker 场景务必挂载 machine-id
    components = [platform.node(), socket.gethostname(), str(uuid.getnode())]
    raw = "|".join(components)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def validate_license(license_path: Path | None = None) -> bool:
    """
    验证当前机器的授权文件（签名 + 机器指纹 + 过期时间）。

    Returns:
        True: 授权有效，允许启动
        False: 授权无效、过期或签名不匹配
    """
    path = license_path or _LICENSE_PATH

    if not _PUBLIC_KEY_B64:
        # 未配置公钥 → 跳过验证（仅限开发环境，生产环境务必配置）
        return True

    if not path.exists():
        print("[LICENSE] 授权文件不存在，拒绝启动")
        return False

    try:
        raw = json.loads(path.read_text())
        payload_bytes = base64.b64decode(raw["payload"])
        signature = base64.b64decode(raw["signature"])

        public_key = Ed25519PublicKey.from_public_bytes(
            base64.b64decode(_PUBLIC_KEY_B64)
        )
        # 签名验证：只有持有私钥的签发端才能生成有效签名
        public_key.verify(signature, payload_bytes)

        payload = json.loads(payload_bytes)

        current_id = get_machine_fingerprint()
        if payload["machine_id"] != current_id:
            print(f"[LICENSE] 机器指纹不匹配: {current_id} != {payload['machine_id']}")
            return False

        expire_at = datetime.strptime(payload["expire_at"], "%Y-%m-%d")
        if datetime.now() > expire_at:
            print(f"[LICENSE] 授权已过期: {payload['expire_at']}")
            return False

        print(f"[LICENSE] 授权验证通过，有效期至 {payload['expire_at']}")
        return True

    except InvalidSignature:
        print("[LICENSE] 签名验证失败，license 文件被篡改或伪造")
        return False
    except Exception as e:
        print(f"[LICENSE] 验证异常: {e}")
        return False
```

### 3.2.1 签发端：密钥对生成 + License 签发（仅在你的安全环境运行）

```python
# scripts/license_signer.py —— 不要包含在任何分发产物中
"""
仅在签发方（你自己的安全环境）运行，用于：
1. 一次性生成 Ed25519 密钥对
2. 为客户机器签发 license.lic
"""
import base64
import json
import sys
from datetime import datetime
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

PRIVATE_KEY_PATH = Path("private_key.pem")  # 妥善保管，切勿上传/分发


def generate_keypair():
    """首次使用时生成密钥对，公钥用于配置客户端 LICENSE_PUBLIC_KEY"""
    private_key = Ed25519PrivateKey.generate()
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    PRIVATE_KEY_PATH.write_bytes(pem)

    public_key = private_key.public_key()
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    print("私钥已保存到:", PRIVATE_KEY_PATH)
    print("公钥 (配置为客户端 LICENSE_PUBLIC_KEY 环境变量):")
    print(base64.b64encode(public_bytes).decode())


def sign_license(machine_id: str, expire_date: str) -> dict:
    """为指定机器指纹签发 license"""
    private_key = Ed25519PrivateKey.from_private_bytes(
        serialization.load_pem_private_key(
            PRIVATE_KEY_PATH.read_bytes(), password=None
        ).private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    payload = {
        "machine_id": machine_id,
        "expire_at": expire_date,
        "issued_at": datetime.now().isoformat()[:10],
    }
    payload_bytes = json.dumps(payload, ensure_ascii=False).encode()
    signature = private_key.sign(payload_bytes)
    return {
        "payload": base64.b64encode(payload_bytes).decode(),
        "signature": base64.b64encode(signature).decode(),
    }


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "--genkey":
        generate_keypair()
        sys.exit(0)

    machine_id, expire = sys.argv[1], sys.argv[2]
    license_data = sign_license(machine_id, expire)
    Path("license.lic").write_text(json.dumps(license_data, ensure_ascii=False))
    print("license.lic 已生成")
```

### 3.3 集成到启动流程

在 `API/main.py` 的 `create_app()` 中添加：

```python
# API/main.py - 在 create_app() 最前面调用
from API.license_validator import validate_license

def create_app():
    # === 授权验证（最先执行）===
    if not validate_license():
        raise RuntimeError(
            "License validation failed. "
            "Please contact the vendor for a valid license file."
        )
    # ... 原有启动逻辑
```

### 3.4 授权生成流程（客户端获取机器指纹 → 签发端签发）

```bash
# 客户端（新机器）：获取机器指纹并发给你
python -c "from API.license_validator import get_machine_fingerprint; print(get_machine_fingerprint())"

# 你的安全环境：首次使用先生成密钥对（仅需一次，公钥固化到部署镜像/环境变量）
python scripts/license_signer.py --genkey

# 你的安全环境：为客户机器签发 license
python scripts/license_signer.py <客户机器指纹> 2026-12-31
# 生成 license.lic，通过安全渠道（非明文邮件）发给客户，客户放置到项目根目录
```

### 3.5 使用流程（Docker 场景）

```
                 你的安全环境                              客户服务器 (Docker)
              ┌──────────────┐                       ┌───────────────────────┐
              │ 1. 首次 --genkey │                    │ 2. docker run 时挂载    │
              │   得到 私钥/公钥  │                    │    -v /etc/machine-id: │
              │                │                     │      /etc/host-        │
              │ 3. 公钥内置到    │  部署镜像预置公钥 →   │      machine-id:ro     │
              │   LICENSE_PUBLIC │                     │                       │
              │   _KEY 环境变量  │                    │ 4. 获取容器内可见的      │
              │                │  ← 宿主机指纹 ←       │    host-machine-id 指纹 │
              │ 5. 签发 license  │                     │                        │
              │   .lic (私钥签名) │  → license.lic →    │ 6. 放置到项目根目录/     │
              └──────────────┘   挂载进容器            │    挂载点，启动时验签    │
                                                       └───────────────────────┘
```

> ⚠️ **关键**：Docker 部署时必须在 `docker run`/`docker-compose.yml` 中显式挂载宿主机 `/etc/machine-id` 到容器内的 `/etc/host-machine-id`（只读），否则会回退到容器内部特征（随容器重建而变化），导致 license 频繁失效。示例：
> ```yaml
> # docker-compose.yml
> services:
>   deepanalyze:
>     volumes:
>       - /etc/machine-id:/etc/host-machine-id:ro
> ```

---

## 4. Layer 2：Cython 核心编译

### 4.1 原理与真实效果说明

Cython 将 Python 代码编译为 C 语言，再编译为 CPython 扩展模块（`.pyd` on Windows / `.so` on Linux/macOS）。

> ⚠️ **重要澄清（避免预期偏差）**：
> - **关于性能**：若不为代码添加 `cdef`/`cpdef` 类型标注（对 401KB/286KB 这种大文件手工添加不现实），Cython 编译的实际效果**主要是混淆，而非提速**。原方案中"性能提升 10-30%"的表述仅适用于添加了类型标注的场景，未标注的直接编译版本性能提升有限甚至可忽略，请勿以此作为立项理由。
> - **关于保护强度**：Cython 编译产物比 `.pyc` 更难逆向，但**并非不可逆向**——存在针对 `.so`/`.pyd` 的字符串常量提取、控制流分析等逆向手段，专业人员仍可能还原部分业务逻辑（尤其是调用的库名、字符串常量、异常信息）。更准确的定位是"**显著提高逆向门槛和成本**"，而非"极难逆向"。

### 4.2 模块分级

| 级别 | 操作 | 模块数量 | 说明 |
|:---:|------|:---:|------|
| **默认编译** | `.py` → `.pyd/.so` | 14 个 | 核心算法+报告引擎（含修正后的 `executor.py`），`Dockerfile.compiled` COPY 范围与此严格对齐，见 §4.3 `CORE_MODULES` |
| **可选编译（P2）** | 需显式 `--include-p2` 才编译 | 4 个 | 认证/账户基础设施类，见 §4.3 `OPTIONAL_P2_MODULES`（v1.5 修正，不再混入默认编译清单） |
| **保留** | 保留 `.py` | ~11 个 | 入口文件、`__init__.py`、`deploy_guard.py`/`license_validator.py`（v1.5 新增）、**含 FastAPI 路由装饰器的 API 模块**（见 §4.3 `DO_NOT_COMPILE`） |
| **待审计** | 需人工审计后决定 | 1 个 | `validators.py`（含真实 `eval()` 调用，见 §4.5 更正） |

### 4.3 编译清单（v1.5 修正：P0/P1 与 P2 拆分为独立清单）

> **v1.5 变更说明**：审计（`code-protection-audit.md` §10.2/§10.5 Gap #3）发现 v1.3/v1.4 把 4 个 P2 文件混入 `CORE_MODULES`，但 `Dockerfile.compiled` 的 COPY 阶段从未把这些文件复制进 compiler stage，导致默认执行编译命令时这些文件必然静默 SKIP、源码残留、且无任何告警。v1.5 起将 P0/P1（真正默认编译、且 Dockerfile 已覆盖 COPY 范围的文件）与 P2（需显式选择、且需要你自行扩展 Dockerfile COPY 范围）拆分为两个独立清单，避免隐式行为。

#### 默认编译的模块（P0 + P1，`Dockerfile.compiled` §5.1.1 的 COPY 范围与此列表严格一一对应）

```python
CORE_MODULES = [
    # P0: 核心风控算法（最高优先级）
    "deepanalyze/analysis/task_SOP/rule_mining.py",           # 401 KB - 已确认无 eval/exec
    "deepanalyze/analysis/task_SOP/scorecard_development.py", # 286 KB
    "deepanalyze/analysis/task_SOP/rule_mining_meta.py",      #  39 KB
    "deepanalyze/analysis/task_SOP/scorecard_meta.py",        #  31 KB
    "deepanalyze/analysis/task_SOP/executor.py",              # 109 KB - 已复核，无 eval/exec，可编译

    # P1: 报告引擎
    "deepanalyze/analysis/excel_report.py",                    # 226 KB
    "deepanalyze/analysis/html_report.py",                    # 176 KB
    "deepanalyze/analysis/word_report.py",                    # 144 KB
    "deepanalyze/analysis/markdown_report.py",                # 120 KB

    # P1: 数据分析引擎
    "deepanalyze/analysis/preprocessing.py",                  #  60 KB
    "deepanalyze/analysis/statistical_model.py",              #  17 KB
    "deepanalyze/analysis/feature_correlation.py",            #  10 KB
    "deepanalyze/analysis/iv_analysis.py",                    #   8 KB
    "deepanalyze/analysis/woe.py",                            #   8 KB
    "deepanalyze/analysis/feature_binning.py",                #   7 KB
    "deepanalyze/analysis/score_transformer.py",              #  10 KB
]
```

#### 可选编译的模块（P2，需 `--include-p2` 显式启用，且需同步扩展 Dockerfile COPY 范围）

```python
# 这 4 个文件不属于"核心风控算法IP"（性质见 §1.5），默认不编译。
# 若决定编译，除了加 --include-p2 参数，还必须在 Dockerfile.compiled 的
# compiler 阶段补充对应的 COPY 语句（API/ 与 deepanalyze/core/task_manager/
# 两个目录默认不会被复制进 compiler stage），否则会重新触发 Gap #3 同类问题。
OPTIONAL_P2_MODULES = [
    "API/AI_analysis_prompts.py",                               #  135 KB - 无路由装饰器，纯提示词模板
    "API/auth_middleware.py",                                   #   37 KB - 认证中间件，无路由装饰器
    "deepanalyze/core/task_manager/user_service.py",             #   20 KB - 账户 CRUD 服务
    "deepanalyze/core/task_manager/user_migration_service.py",   #    7 KB - 一次性迁移脚本
]
```

#### 需要编译的模块（历史别名，供旧脚本/文档兼容引用）

上面两个列表合计即为 v1.4 及更早版本中提到的"P0+P1+P2 共 18 个模块"，v1.5 起不再以单一列表形式暴露，避免默认命令无差别混入 P2。

#### 保留明文的模块

```python
KEEP_CLEAR = [
    "API/main.py",                                    # FastAPI 启动入口
    "API/__init__.py",
    "API/deploy_guard.py",                            # v1.5新增：轻量部署审批开关，见§3.0
    "API/license_validator.py",                       # v1.5新增：Ed25519授权验证器，见§3.1-§3.5
    "deepanalyze/__init__.py",
    "deepanalyze/analysis/__init__.py",
    "deepanalyze/analysis/task_SOP/__init__.py",
    "deepanalyze/analysis/data_validator/__init__.py",
    "deepanalyze/core/__init__.py",
    "deepanalyze/core/task_manager/__init__.py",
    "deepanalyze/analysis/task_SOP/expert_mode/__init__.py",
]
```

> ⚠️ **v1.5 修正（源自审计 Gap A）**：`deploy_guard.py`/`license_validator.py` 此前未被 `CORE_MODULES`/`KEEP_CLEAR`/`DO_NOT_COMPILE` 任何清单覆盖。这两个文件承载 Layer 1 的鉴权逻辑，若以裸源码留在镜像里且被外部读取，攻击者可直接看到"环境变量匹配即可绕过审批"的实现细节，削弱 Layer 1 的实际防护效果。现显式归入 `KEEP_CLEAR`（暂不编译，因两者体量小且与 `main.py` 启动流程强耦合，编译收益低于维护成本；`license_validator.py` 未来若确认稳定可按 §2.4 增量评估流程移入编译清单）。

#### 待审计的模块（含真实动态执行风险，需人工确认）

```python
DYNAMIC_MODULES = [
    "deepanalyze/analysis/task_SOP/validators.py",   # 46KB - 含 eval(rule_expr, safe_globals)
    # 注：executor.py 经复核不含 exec/eval，已移入 CORE_MODULES（可直接编译）
]
```

#### 不建议编译的模块（FastAPI 路由，编译会破坏运行时功能）

```python
# 原方案 OPTIONAL_MODULES 中的 API 层文件含 FastAPI 路由装饰器：
#   sop_api.py (51 处 @router.*) / chat_api.py (5 处) / export_api.py (2 处)
# FastAPI 的 OpenAPI schema 生成与依赖注入依赖 inspect.signature() 反射函数签名，
# Cython 编译（尤其 binding=False）会导致签名信息丢失，引发路由参数校验失败、
# /docs 文档生成异常等问题。因此这些文件应保留为 .py，不纳入编译范围。
# （v1.3新增）user_admin_api.py 是用户管理模块批次2 Phase10新增的路由文件（8 处
# @router.*：/auth/mode、/auth/profile、/auth/change-password、/admin/users*），
# 同理不建议编译，详见 §1.5。
DO_NOT_COMPILE = [
    "API/sop_api.py",
    "API/chat_api.py",
    "API/export_api.py",
    "API/admin_api.py",
    "API/file_api.py",
    "API/user_admin_api.py",
]
```

### 4.4 Cython 编译脚本（v1.5：拆分 P2 + 输出清单文件 + SKIP 告警）

```python
# build_cython.py (放置于项目根目录)
"""
Cython 编译脚本
用法:
    python build_cython.py                    # 编译默认模块（P0+P1，14个核心算法文件）
    python build_cython.py --include-p2       # 额外编译 P2 可选模块（需同步扩展 Dockerfile COPY 范围，见 §5.1.1）
    python build_cython.py --all               # 编译 P0+P1 + 待审计模块（validators.py），不含 P2
    python build_cython.py --all --include-p2  # 编译全部（P0+P1+P2+待审计）
    python build_cython.py --dry-run           # 预览将编译的模块
    python build_cython.py --clean             # 清理所有编译产物
    python build_cython.py --replace           # 编译后用 .pyd/.so 替换 .py

v1.5 变更（源自 docs/code-protection-audit.md §10.5 Gap #3）:
    - CORE_MODULES 不再包含 P2 文件，避免默认路径下的隐式静默失败
    - P2 文件改为独立的 OPTIONAL_P2_MODULES，需 --include-p2 显式启用
    - 编译完成后输出 compiled_files.txt 清单文件，供 Dockerfile 按清单删除源码（见 §5.1.1）
    - 文件不存在时的 SKIP 分支同时输出到 stderr，确保非交互环境（CI/Docker）也能感知
"""
import os
import sys
import shutil
import argparse
from pathlib import Path
from Cython.Build import cythonize
from setuptools import Extension, setup

ROOT = Path(__file__).parent
BUILD_DIR = "build_cython"
MANIFEST_PATH = ROOT / "compiled_files.txt"

# === 模块清单 ===

# 默认编译（P0+P1）：Dockerfile.compiled §5.1.1 的 compiler 阶段 COPY 范围与此列表严格一一对应
CORE_MODULES = [
    # P0: 核心风控算法
    "deepanalyze/analysis/task_SOP/rule_mining.py",
    "deepanalyze/analysis/task_SOP/scorecard_development.py",
    "deepanalyze/analysis/task_SOP/rule_mining_meta.py",
    "deepanalyze/analysis/task_SOP/scorecard_meta.py",
    "deepanalyze/analysis/task_SOP/executor.py",   # 已复核：无 exec/eval，可编译
    # P1: 报告引擎
    "deepanalyze/analysis/excel_report.py",
    "deepanalyze/analysis/html_report.py",
    "deepanalyze/analysis/word_report.py",
    "deepanalyze/analysis/markdown_report.py",
    # P1: 数据分析引擎
    "deepanalyze/analysis/preprocessing.py",
    "deepanalyze/analysis/statistical_model.py",
    "deepanalyze/analysis/feature_correlation.py",
    "deepanalyze/analysis/iv_analysis.py",
    "deepanalyze/analysis/woe.py",
    "deepanalyze/analysis/feature_binning.py",
    "deepanalyze/analysis/score_transformer.py",
]

# 可选编译（P2）：认证/账户基础设施，性质说明见 §1.5。
# v1.5 起从 CORE_MODULES 中独立出来，默认不编译。
# ⚠️ 若启用 --include-p2，必须同步在 Dockerfile.compiled 的 compiler 阶段补充
#    COPY API/ 与 COPY deepanalyze/core/task_manager/ ，否则会重新触发 Gap #3
#    同类问题（源文件不在 compiler stage → SKIP → 源码残留但保护效果为零）。
OPTIONAL_P2_MODULES = [
    "API/AI_analysis_prompts.py",
    "API/auth_middleware.py",
    "deepanalyze/core/task_manager/user_service.py",
    "deepanalyze/core/task_manager/user_migration_service.py",
]

# 含真实 eval() 动态执行风险，需先审计 safe_globals 沙箱是否可靠，再决定是否编译
DYNAMIC_MODULES = [
    "deepanalyze/analysis/task_SOP/validators.py",
]

# 明确不建议编译：含 FastAPI 路由装饰器，Cython 编译会破坏
# inspect.signature() 反射，导致 OpenAPI 生成/依赖注入异常
DO_NOT_COMPILE = [
    "API/sop_api.py",        # 51 处 @router.*
    "API/chat_api.py",       # 5 处 @router.*
    "API/export_api.py",     # 2 处 @router.*
    "API/admin_api.py",      # 2 处 @router.*
    "API/file_api.py",       # 6 处 @router.*
    "API/user_admin_api.py", # 8 处 @router.*（v1.3新增，用户管理模块批次2 Phase10）
]

# v1.5 新增：不参与编译，但需要在镜像中保留明文（Layer 1 鉴权逻辑，见 §4.3 KEEP_CLEAR 说明）
KEEP_CLEAR = [
    "API/main.py",
    "API/__init__.py",
    "API/deploy_guard.py",
    "API/license_validator.py",
    "deepanalyze/__init__.py",
    "deepanalyze/analysis/__init__.py",
    "deepanalyze/analysis/task_SOP/__init__.py",
    "deepanalyze/analysis/data_validator/__init__.py",
    "deepanalyze/core/__init__.py",
    "deepanalyze/core/task_manager/__init__.py",
    "deepanalyze/analysis/task_SOP/expert_mode/__init__.py",
]


def build_extensions(modules: list[str]) -> list[str]:
    """
    编译指定模块为 C 扩展（原地构建）。
    返回实际成功进入编译流程的模块列表（用于生成清单文件）。
    """
    extensions = []
    actually_compiled = []
    skipped = []

    for mod_path in modules:
        p = Path(mod_path)
        if not p.exists():
            skipped.append(mod_path)
            continue

        module_name = str(p.with_suffix("")).replace("/", ".").replace("\\", ".")
        extensions.append(
            Extension(
                module_name,
                [mod_path],
                extra_compile_args=["-O2"],
            )
        )
        actually_compiled.append(mod_path)

    # v1.5: SKIP 文件必须同时输出到 stderr，确保 CI/Docker 等非交互环境能感知
    # （此前版本只 print 到 stdout，Dockerfile RUN 步骤容易忽略这条日志）
    if skipped:
        for mod_path in skipped:
            print(f"  ⚠ SKIP: {mod_path} (文件不存在，未被编译，源码不会被清理)", file=sys.stderr)
        print(
            f"\n⚠⚠⚠ 警告: {len(skipped)} 个模块因文件不存在被跳过，"
            f"若这些模块本应被编译，请检查是否需要扩展 COPY 范围（常见于 P2 模块，见 §4.3）",
            file=sys.stderr,
        )

    if not extensions:
        print("没有需要编译的模块")
        return actually_compiled

    print(f"\n开始编译 {len(extensions)} 个模块...\n")
    setup(
        name="deepanalyze_compiled",
        ext_modules=cythonize(
            extensions,
            language_level="3",
            build_dir=BUILD_DIR,
            compiler_directives={
                "binding": False,          # 不暴露 C 函数签名
                "embedsignature": False,   # 不嵌入 Python 函数签名
                "always_allow_keywords": True,
                "annotation_typing": False,
            },
        ),
        script_args=["build_ext", "--inplace"],
        zip_safe=False,
    )
    return actually_compiled


def write_compiled_manifest(modules: list[str]) -> None:
    """
    v1.5 新增：将实际编译成功的模块列表写入 compiled_files.txt。
    Dockerfile.compiled 的 runtime 阶段据此清单删除对应源码，
    避免 §5.1.1 中逐文件硬编码删除清单与 CORE_MODULES 脱节（Gap #3）。
    """
    MANIFEST_PATH.write_text("\n".join(modules), encoding="utf-8")
    print(f"\n✓ 编译清单已写入: {MANIFEST_PATH} ({len(modules)} 个文件)")


def replace_py_files(modules: list[str]) -> None:
    """编译完成后，将原 .py 重命名为 .py.bak（.pyd/.so 自动优先加载）"""
    for mod_path in modules:
        p = Path(mod_path)
        bak = p.with_suffix(".py.bak")
        if p.exists():
            p.rename(bak)
            print(f"  ✓ BAK: {mod_path} -> {bak.name}")


def restore_py_files(modules: list[str]) -> None:
    """恢复 .py.bak → .py（用于开发调试）"""
    for mod_path in modules:
        p = Path(mod_path)
        bak = p.with_suffix(".py.bak")
        if bak.exists():
            bak.rename(p)
            print(f"  ✓ RESTORE: {bak.name} -> {mod_path}")


def clean_all() -> None:
    """清理所有编译产物"""
    # 删除编译中间文件
    patterns = ["*.pyd", "*.so", "*.c", "*.html"]
    for pattern in patterns:
        for f in ROOT.rglob(pattern):
            f.unlink()
            print(f"  DEL: {f}")

    # 删除构建目录
    for d in [BUILD_DIR, "build"]:
        p = ROOT / d
        if p.exists() and p.is_dir():
            shutil.rmtree(p)
            print(f"  DEL: {p}/")

    # 删除清单文件
    if MANIFEST_PATH.exists():
        MANIFEST_PATH.unlink()
        print(f"  DEL: {MANIFEST_PATH}")

    # 恢复 .py.bak
    for bak in ROOT.rglob("*.py.bak"):
        py_file = bak.with_suffix("")
        if not py_file.exists():
            bak.rename(py_file)
            print(f"  RESTORE: {bak} -> {py_file}")


def print_summary(modules: list[str]) -> None:
    """打印编译预览"""
    total = 0
    for m in modules:
        p = Path(m)
        if p.exists():
            size = p.stat().st_size / 1024
            total += size
            flag = "🔴" if m in DYNAMIC_MODULES else ("🟠" if m in OPTIONAL_P2_MODULES else "🟢")
            print(f"  {flag} {m} ({size:.0f} KB)")
        else:
            print(f"  ⚠ {m} (文件不存在，将被 SKIP)")
    print(f"\n 总计: {len(modules)} 个模块, {total:.0f} KB")

    dynamic_included = any(m in modules for m in DYNAMIC_MODULES)
    if dynamic_included:
        print("\n  ⚠ 警告: 包含动态执行模块，请确保已审计 exec()/eval() 调用")

    p2_included = any(m in modules for m in OPTIONAL_P2_MODULES)
    if p2_included:
        print(
            "\n  🟠 提示: 包含 P2 可选模块，请确认 Dockerfile.compiled 的 compiler 阶段"
            "已扩展 COPY 范围（COPY API/ 与 COPY deepanalyze/core/task_manager/），"
            "否则这些文件会因源文件不存在被 SKIP"
        )


def main():
    parser = argparse.ArgumentParser(description="DeepAnalyze Cython 编译工具")
    parser.add_argument(
        "--all", action="store_true",
        help="编译核心模块 + 待审计模块（validators.py）；不含 P2，也不会编译 DO_NOT_COMPILE 中的 FastAPI 路由文件"
    )
    parser.add_argument(
        "--include-p2", action="store_true",
        help="额外编译 OPTIONAL_P2_MODULES（需同步扩展 Dockerfile COPY 范围，见 §4.3/§5.1.1）"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="仅预览编译范围，不实际编译"
    )
    parser.add_argument(
        "--clean", action="store_true",
        help="清理所有编译产物和中间文件"
    )
    parser.add_argument(
        "--replace", action="store_true",
        help="编译后用 .pyd/.so 替换原 .py 文件"
    )
    parser.add_argument(
        "--restore", action="store_true",
        help="恢复 .py.bak -> .py"
    )
    parser.add_argument(
        "--yes", "-y", action="store_true",
        help="跳过交互确认，用于 CI/Docker 等非交互环境（无 stdin 时 input() 会静默判定为取消，"
             "导致 Dockerfile 中 RUN python build_cython.py 看似成功但实际未编译任何模块）"
    )
    args = parser.parse_args()

    # 处理清理/恢复操作
    if args.clean:
        print("清理所有编译产物...")
        clean_all()
        return

    # 确定编译范围
    modules = CORE_MODULES.copy()
    if args.all:
        modules += DYNAMIC_MODULES
    if args.include_p2:
        modules += OPTIONAL_P2_MODULES

    if args.restore:
        print("恢复 .py 源文件...")
        restore_py_files(modules)
        return

    if args.dry_run:
        print(f"=== 编译预览 ({len(modules)} 个模块) ===\n")
        print_summary(modules)
        return

    print(f"=== DeepAnalyze Cython 编译 ({len(modules)} 个模块) ===\n")
    print_summary(modules)

    # 提示未包含的模块
    excluded_dynamic = [m for m in DYNAMIC_MODULES if m not in modules]
    if excluded_dynamic:
        print(f"\n未包含 {len(excluded_dynamic)} 个待审计模块 (使用 --all 编译，仍需先完成 eval() 沙箱审计):")
        for m in excluded_dynamic:
            print(f"  🔴 {m}")
    excluded_p2 = [m for m in OPTIONAL_P2_MODULES if m not in modules]
    if excluded_p2:
        print(f"\n未包含 {len(excluded_p2)} 个 P2 可选模块 (使用 --include-p2 编译):")
        for m in excluded_p2:
            print(f"  🟠 {m}")
    print(f"\n以下模块因含 FastAPI 路由装饰器，任何模式下都不会被编译: {len(DO_NOT_COMPILE)} 个")

    confirm = "y" if args.yes else input("\n确认编译? [y/N] ")
    if confirm.lower() != "y":
        print("已取消")
        return

    # 执行编译，获取实际成功编译的文件列表
    actually_compiled = build_extensions(modules)

    # v1.5 新增：写入清单文件，供 Dockerfile 按清单删除源码
    if actually_compiled:
        write_compiled_manifest(actually_compiled)

    # 可选：替换源文件
    if args.replace:
        replace_py_files(actually_compiled)
        print("\n✓ 源码已替换为编译产物")
    else:
        print("\n✓ 编译完成（源文件保留）")
        print("  提示: 使用 --replace 参数可将 .py 替换为编译产物")


if __name__ == "__main__":
    main()
```

### 4.5 validators.py 动态执行审计（已更正审计对象）

已通过 `rg -n "exec\(|eval\(" deepanalyze/analysis/task_SOP/executor.py` 复核，`executor.py` **不含** 任何 exec/eval 调用，已移入可编译清单。真正需要审计的是 `validators.py`：

```bash
rg -n "eval\(" deepanalyze/analysis/task_SOP/validators.py
# 命中: validators.py:40  result = eval(rule_expr, safe_globals)
# safe_globals = {'__builtins__': {}, 'df': df, 'pd': pd, 'np': np}
```

**审计结论**：`rule_expr` 来自评分卡/规则 JSON 配置（非用户直接输入的自由文本），且 `__builtins__` 已清空，风险主要来自"对象方法链沙箱逃逸"（如通过 `df.__class__.__mro__[...]` 等经典技巧访问受限对象），概率较低但存在理论可能。

**处理策略**：

| 场景 | 处理方式 |
|------|----------|
| `rule_expr` 仅来自内部生成/配置文件，不接受终端用户直接输入 | ✅ 风险可接受，可编译（Cython 编译不改变 `eval()` 本身的运行时行为，只是把调用它的字节码变成 C 代码） |
| `rule_expr` 存在任何来自前端用户输入的路径 | ❌ 应先将 `eval()` 替换为 `ast.literal_eval` 或表达式白名单解析器（类似 `rule_mining.py` 已做的 `_safe_eval_rule` 改造），而不是依赖 Cython 编译掩盖问题 |

> 💡 需要强调：**Cython 编译本身不会修复 `eval()` 的安全问题**，它只是让"调用 eval 的代码"更难被阅读，不改变 `eval()` 执行时的沙箱逃逸风险。若 `validators.py` 存在用户输入路径，应在代码层面修复（参考 `rule_mining.py` 的 `_safe_eval_rule` 模式），而非仅通过编译掩盖。

### 4.6 环境要求

| 系统 | 编译器 | 安装 |
|------|--------|------|
| **Windows** | Visual Studio Build Tools (MSVC) | `winget install Microsoft.VisualStudio.2022.BuildTools` |
| **Linux** | GCC | `apt install build-essential python3-dev` |
| **macOS** | Xcode CLT | `xcode-select --install` |

安装 Cython：

```bash
pip install cython
```

### 4.7 兼容性核实结果与分阶段验证策略

#### 4.7.1 已核实：不构成风险的兼容性陷阱

对 `CORE_MODULES` 清单中的文件做了实际代码扫描，排除了以下常见 Cython 兼容性陷阱：

| 检查项 | 结果 | 影响 |
|--------|:---:|------|
| PEP 604 联合类型语法 `X \| Y` | 0 处 | 代码用 `Optional[X]`/`Union`，兼容性好 |
| `match/case` 语句 | 0 处 | 无需担心新语法支持问题 |
| walrus 操作符 `:=` | 0 处 | 同上 |
| `inspect.signature()` / `functools.wraps` 反射 | 0 处（deepanalyze/ 目录） | `binding=False` 不会破坏这些模块自身的运行时反射逻辑 |
| `pickle`/`joblib`/`multiprocessing` 序列化 | 0 处 | 排除"Cython 扩展类型无法被序列化/跨进程传递"的经典陷阱 |
| 测试中 `mock.patch(...)`（如 `test_llm_pipeline_integration.py` 对 `executor.SOPExecutor`） | 存在但未用 `autospec=True` | 属于模块级属性替换，Cython 编译后的模块字典机制与普通 Python 模块一致，一般仍可正常工作 |

#### 4.7.2 真实存在、需要处理的风险

| 风险 | 说明 | 应对 |
|------|------|------|
| **超大单文件触及 C 编译器限制** | `rule_mining.py`（401KB）、`scorecard_development.py`（286KB）转译后的 `.c` 文件可能膨胀到 1-4MB，曾有社区反馈此量级文件会导致 MSVC 报 `C1076 内部堆限制`，或 GCC 编译耗时暴涨至十几分钟、内存占用飙升数 GB | 采用下方 §4.7.3 分阶段验证，若编译失败/超时，考虑先拆分该文件为多个子模块 |
| **新 Python 版本专属语法随开发迭代引入**（新增，v1.4，已有真实案例） | `executor.py` 在 §1.4 被判定"无风险可编译"后，2026-07-03 的开发提交在其中引入了 PEP 695 `type` 语句（Python 3.12+ 语法），导致部署环境 Python 3.10/3.11 下 `SyntaxError`，Chat/SOP API 直接加载失败（已修复为改用 `Union`）——这证明持续开发中的模块，其兼容性审计结论会随代码变更失效 | 纳入编译清单前必须重新走 §2.4.4 增量评估四步检查，不可复用历史审计结论 |
| **`@dataclass`/`Enum`/`__slots__` 大量使用**（18/22 个待编译文件涉及） | Cython 在 `annotation_typing=True`（默认值）时可能把 dataclass 字段类型注解误判为 `cdef` 声明，导致字段异常 | 编译脚本已设置 `annotation_typing: False`（见 §4.4），需在编译后针对性跑一遍涉及 dataclass 的单测确认 |
| **便携式开发环境可能缺少 C 编译器** | 当前 `portable-dev-env` 是便携式 Python 环境，未必预装 MSVC/GCC | 需按 §4.6 单独安装编译工具链，或统一在 Docker（Linux + GCC）里完成编译，避免在本机便携环境折腾 MSVC |

#### 4.7.3 分阶段验证策略（不要一次性全量编译）

```
第一步（试点）：先编译 1 个中等体量、无 dataclass 的文件（如 woe.py，8KB）
                验证：能否正常编译、正常 import、pytest 通过
                命令：python build_cython.py --dry-run  # 先确认范围
                     （临时修改 CORE_MODULES 只保留 woe.py 试跑一次）

第二步（验证大文件）：单独试编译 rule_mining.py（401KB，清单中最大文件）
                重点观察：编译耗时是否异常（>5 分钟需警惕）、
                         是否报编译器堆内存/内部限制错误
                若失败 → 将该文件拆分为 2-3 个子模块后再编译，
                         不要强行调整编译器参数掩盖问题

第三步（批量）：试点通过后，按 P0 → P1 顺序批量编译剩余文件

第四步（CI 强制关卡）：在 CI 中加入以下步骤，任何一步失败即阻断发布
    1. python build_cython.py --yes --replace
    2. python -c "import deepanalyze.analysis.task_SOP.rule_mining"  # 全量 import 烟雾测试
    3. pytest tests/ -x                                              # 全量测试，失败即停
```

> 💡 分阶段验证的核心价值：把"编译失败/兼容性问题"的发现时机从"生产部署后"提前到"CI 流水线里"，避免一次性编译 14 个文件后才发现某个大文件编译失败，导致整体排期不可控。

---

## 5. Layer 3：分发封装

### 5.1 方案 A：Docker 编译版镜像（推荐）

#### 5.1.1 多阶段 Dockerfile（v1.5：目录级 COPY + 清单文件删除源码，与真实 `docker/Dockerfile` 结构对齐）

> **v1.5 变更说明**（源自 `docs/code-protection-audit.md` §10.5 Gap #3）：v1.4 版本逐文件 `COPY` + 逐文件硬编码删除清单，与 `build_cython.py` 的 `CORE_MODULES` 脱节，两份清单不一致时会静默漏删源码。v1.5 改为：compiler 阶段按目录整体 COPY（覆盖 P0+P1+P2 全部潜在编译对象），`build_cython.py` 编译完成后输出 `compiled_files.txt`，runtime 阶段读取该清单删除对应源码——**清单以 `build_cython.py` 的实际执行结果为唯一真相来源，不再有第二份手工维护的清单**。同时对齐了真实 `docker/Dockerfile`（见上方）的结构（kaleido 依赖库列表、`API/main.py` 作为 CMD、LLM Manager 静态资源目录结构等），确保 `docker-compose.compiled.yml`（见 §5.1.3）可以直接复用现有 `docker-compose.yml` 的其余配置。

```dockerfile
# docker/Dockerfile.compiled
# 与 docker/Dockerfile 结构基本一致，仅新增 Stage 1（Cython 编译）
# 及运行时阶段对编译产物的替换逻辑。两份 Dockerfile 的系统依赖/前端构建/
# CMD 均保持一致，便于后续维护时同步修改。

# === Stage 1: Cython 编译阶段（v1.5 新增）===
FROM python:3.12-slim AS compiler
WORKDIR /build

RUN pip install --no-cache-dir cython setuptools

# 目录级复制：覆盖 CORE_MODULES(P0+P1) + OPTIONAL_P2_MODULES 的全部潜在来源目录，
# 不再逐文件列出，避免与 build_cython.py 的清单脱节。
# 若 build_cython.py 新增了其他目录下的编译对象，需同步在此补充 COPY。
COPY deepanalyze/ /build/deepanalyze/
COPY API/ /build/API/
COPY build_cython.py /build/

# 默认只编译 P0+P1（不加 --include-p2）。
# 若要编译 P2，改为: RUN python build_cython.py --yes --replace --include-p2
# 必须带 --yes（非交互环境，否则 input() 会静默判定为取消）
# 必须带 --replace（确保 .py 不留在 build 产物目录中，避免 .py.bak 残留风险见下方防御性清理）
RUN python build_cython.py --yes --replace

# === Stage 2: 前端构建阶段（Next.js 主前端）===
FROM node:18-slim AS frontend-builder
WORKDIR /build
COPY demo/chat/package.json demo/chat/package-lock.json* ./
RUN npm install --production=false
COPY demo/chat/ ./
RUN npm run build

# === Stage 3: LLM Manager 前端构建（Vite + Tailwind）===
FROM node:18-slim AS llm-manager-builder
WORKDIR /build-llm
COPY llm_manager_integrated/frontend/package.json llm_manager_integrated/frontend/package-lock.json* /build-llm/
RUN npm install --production=false
COPY llm_manager_integrated/frontend/ /build-llm/
RUN chmod +x node_modules/.bin/vite node_modules/.bin/tailwindcss 2>/dev/null || true && \
    npm run build && \
    ./node_modules/.bin/tailwindcss \
        -i ./styles/main.css \
        -o /static/assets/main.css \
        --minify && \
    sed -i 's|<script src="https://cdn.tailwindcss.com[^"]*"></script>|<link rel="stylesheet" href="/llm-manager/assets/main.css">|' /static/assets/index.html && \
    sed -i 's| https://cdn.tailwindcss.com||g' /static/assets/index.html && \
    sed -i 's|http://localhost:8200 ||g' /static/assets/index.html && \
    sed -i '/<style>/,/<\/style>/d' /static/assets/index.html && \
    cp -r scripts /static/ && \
    cp -r shared /static/

# === Stage 4: 运行时镜像 ===
FROM python:3.12-slim
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    API_HOST=0.0.0.0 \
    API_PORT=8200 \
    DEV_MODE=false \
    ENABLE_AUTH=true

WORKDIR /app

# 系统依赖（与真实 docker/Dockerfile 保持一致：kaleido/Chromium 渲染依赖 + 中文字体）
RUN apt-get update && apt-get install -y \
    git curl \
    fonts-wqy-zenhei \
    libgbm1 libnss3 libnspr4 libatk-bridge2.0-0 libatk1.0-0 libasound2 \
    libxcomposite1 libxdamage1 libxrandr2 libxkbcommon0 libpango-1.0-0 libcups2 \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
ARG OFFLINE_MODE=false
COPY requirements.txt .
COPY docker/.offline_wheels/ /tmp/offline_wheels/
RUN pip install --upgrade pip && \
    if [ "$OFFLINE_MODE" = "true" ] && ls /tmp/offline_wheels/*.whl >/dev/null 2>&1; then \
        pip install --no-index --find-links=/tmp/offline_wheels -r requirements.txt; \
    else \
        pip install -r requirements.txt; \
    fi

# 复制项目代码（从构建上下文，含全部原始 .py 源码——下面会按清单删除已编译部分）
COPY API/ ./API/
COPY deepanalyze/ ./deepanalyze/
COPY llm_manager_integrated/ ./llm_manager_integrated/
COPY scripts/ ./scripts/
COPY config/users.yaml.example ./config/users.yaml.example
COPY build_cython.py ./

# 复制编译产物（compiler 阶段基于 Linux 镜像，只产生 .so；Windows 目标环境
# 需在 Windows 编译环境单独执行并另行处理 .pyd，本 Dockerfile 不覆盖该场景）
COPY --from=compiler /build/deepanalyze/ /tmp/compiled/deepanalyze/
COPY --from=compiler /build/API/ /tmp/compiled/API/
COPY --from=compiler /build/compiled_files.txt /tmp/compiled_files.txt

# v1.5 核心修正：按 compiled_files.txt 清单（build_cython.py 的实际编译结果，
# 而非手工维护的第二份清单）执行"复制 .so + 删除对应 .py 源码"，
# 确保编译清单与清理清单永远一致（根治 Gap #3）
RUN python - <<'EOF'
import shutil
from pathlib import Path

manifest = Path("/tmp/compiled_files.txt").read_text().strip().splitlines()
compiled_root = Path("/tmp/compiled")
app_root = Path("/app")

for rel_path in manifest:
    rel_path = rel_path.strip()
    if not rel_path:
        continue
    so_path = compiled_root / (rel_path[:-3] + ".so")  # xxx.py -> xxx.so（同名同目录）
    dest_py = app_root / rel_path
    dest_so = app_root / (rel_path[:-3] + ".so")

    if so_path.exists():
        dest_so.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(so_path, dest_so)
        print(f"copied .so: {dest_so}")
    else:
        print(f"WARNING: expected .so not found for {rel_path}, skip copy (source will remain, protection NOT applied for this file)")
        continue

    if dest_py.exists():
        dest_py.unlink()
        print(f"removed source: {dest_py}")

# 清理临时目录
shutil.rmtree("/tmp/compiled", ignore_errors=True)
Path("/tmp/compiled_files.txt").unlink(missing_ok=True)
EOF

# v1.5 新增（源自审计 Gap B）：防御性清理 .py.bak，即便当前设计下不应残留，
# 也不依赖"COPY 阶段天然隔离"这一隐式假设
RUN find /app -name "*.py.bak" -delete

# 复制前端构建产物
COPY --from=frontend-builder /build/dist ./demo/chat/dist
COPY --from=llm-manager-builder /static/ ./llm_manager_integrated/static/

# 创建必要的目录
RUN mkdir -p workspace execution_states task_results logs config

# 清理编译中间文件
RUN find /app -name "*.pyc" -delete \
    && find /app -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true \
    && rm -f /app/build_cython.py

EXPOSE 8200 8100

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8200/health || exit 1

CMD ["python", "API/main.py"]
```

#### 5.1.2 构建命令

```bash
# 构建编译版镜像（本地直接构建，用于开发验证）
docker build -f docker/Dockerfile.compiled -t creditwise:protected .

# 导出镜像（用于离线分发）
docker save creditwise:protected | gzip > creditwise_protected.tar.gz

# 客户侧加载（沿用真实项目现有的启动方式，见 §5.1.3 docker-compose.compiled.yml）
docker load < creditwise_protected.tar.gz
```

#### 5.1.3 docker-compose.compiled.yml（v1.5 新增，衔接真实 `docker-compose.yml`，修正 Gap #1）

> **问题背景**：真实项目的 `docker/docker-compose.yml` 中 `build.dockerfile` 硬编码指向 `docker/Dockerfile`（标准版），`prepare_offline.sh` 调用 `docker compose build` 时永远构建的是未编译的标准镜像——`Dockerfile.compiled` 此前无法被任何现有脚本触达。新增 `docker-compose.compiled.yml`，与 `docker-compose.yml` 内容完全一致，仅替换 `dockerfile` 字段，供 `prepare_offline.sh --protected` 模式调用（见 §5.2）。

```yaml
# docker/docker-compose.compiled.yml
# 与 docker/docker-compose.yml 完全一致，仅 build.dockerfile 指向编译版
# 其余 env_file/volumes/environment/healthcheck 配置保持同步，
# 修改 docker-compose.yml 时请同步检查本文件是否需要更新。
services:
  creditwise:
    build:
      context: ..
      dockerfile: docker/Dockerfile.compiled   # ← 唯一差异
      args:
        - OFFLINE_MODE=${OFFLINE_MODE:-false}
    image: creditwise:protected                 # ← 镜像 tag 区分于标准版
    container_name: creditwise-api

    env_file:
      - ../.env

    ports:
      - "8200:8200"
      - "8100:8100"

    volumes:
      - ../workspace:/app/workspace
      - ../execution_states:/app/execution_states
      - ../task_results:/app/task_results
      - ../logs:/app/logs
      - ../llm_manager.db:/app/llm_manager.db
      - ../task_manager.db:/app/task_manager.db
      - ../config:/app/config
      - ../.env:/app/.env

    environment:
      - API_HOST=0.0.0.0
      - API_PORT=8200
      - DEV_MODE=false
      - ENABLE_AUTH=${ENABLE_AUTH:-true}
      - CORS_ORIGINS=${CORS_ORIGINS:-}
      # v1.5 新增：Layer 1 默认轻量部署审批（见 §3.0），留空则不启用审批门槛
      - DEPLOY_APPROVAL_TOKEN_EXPECTED=${DEPLOY_APPROVAL_TOKEN_EXPECTED:-}
      - DEPLOY_APPROVAL_TOKEN=${DEPLOY_APPROVAL_TOKEN:-}
      # v1.5 新增：Layer 1 可选完整方案（面向外部客户，见 §3.1），默认不配置即跳过验证
      - LICENSE_PUBLIC_KEY=${LICENSE_PUBLIC_KEY:-}

    restart: unless-stopped

    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8200/health"]
      interval: 30s
      timeout: 10s
      start_period: 15s
      retries: 3
```

### 5.2 离线部署包：`prepare_offline.sh --protected`（v1.5 重写，修正 Gap #1 + Gap #2）

> **v1.5 变更说明**：v1.4 及更早版本的 §5.2 是一个独立的、与真实项目脚本无关的 `package_protected.sh` 草稿，未考虑项目已有 `prepare_offline.sh`/`deploy_offline.sh` 的真实工作流程（见 `code-protection-audit.md` §10.4 的事实核查）。v1.5 改为直接在真实 `scripts/prepare_offline.sh` 上新增 `--protected` 参数，两个模式共享同一套流程骨架，仅在"构建哪个 compose 文件"和"打包哪些源码文件"两处分叉。

#### 5.2.1 对 `prepare_offline.sh` 的增量修改

在现有 `scripts/prepare_offline.sh` 基础上做以下修改（新增部分以 `# v1.5 新增` 标注，其余保持不变）：

```bash
#!/bin/bash
# =============================================================================
# CreditWise 离线部署 — 准备脚本（在有外网的机器上执行）
#
# 用法：
#   ./scripts/prepare_offline.sh              # 标准模式（现有行为，不变）
#   ./scripts/prepare_offline.sh --protected   # v1.5 新增：受保护模式
#                                                 （Cython 编译 + 最小文件集打包）
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BUNDLE_DIR="$PROJECT_ROOT/offline_bundle"

# v1.5 新增：--protected 参数解析
PROTECTED_MODE=false
if [ "$1" = "--protected" ]; then
    PROTECTED_MODE=true
fi

if [ "$PROTECTED_MODE" = "true" ]; then
    IMAGE_NAME="creditwise:protected"
    COMPOSE_FILE="docker-compose.compiled.yml"
    echo "============================================================"
    echo " CreditWise 离线部署 — 准备离线包 [受保护模式]"
    echo "============================================================"
else
    IMAGE_NAME="creditwise:latest"
    COMPOSE_FILE="docker-compose.yml"
    echo "============================================================"
    echo " CreditWise 离线部署 — 准备离线包"
    echo "============================================================"
fi
echo ""
echo "此脚本将在当前机器上构建完整 Docker 镜像，打包后传输到内网服务器。"
echo "预计耗时 5-15 分钟（取决于网络和机器性能）。"
echo ""

# 前置检查（不变）
if ! command -v docker &>/dev/null; then
    echo -e "${RED}Docker 未安装，请先安装 Docker${NC}"
    exit 1
fi
if ! docker info &>/dev/null; then
    echo -e "${RED}Docker daemon 未运行，请先启动 Docker${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker 可用: $(docker --version)${NC}"
echo ""

if [ -d "$BUNDLE_DIR" ]; then
    echo -e "${YELLOW}清理旧的 offline_bundle/ ...${NC}"
    rm -rf "$BUNDLE_DIR"
fi
mkdir -p "$BUNDLE_DIR/images"

# =============================================================================
# [1/4] 构建完整 Docker 镜像
# =============================================================================
echo -e "${GREEN}[1/4] 构建完整 Docker 镜像${NC}"
if [ "$PROTECTED_MODE" = "true" ]; then
    echo "  [受保护模式] 核心算法将在构建阶段编译为 .so，源码不进入镜像"
fi
echo "  包含：前端编译（Next.js + Vite + Tailwind）+ Python 依赖安装"
echo ""

cd "$PROJECT_ROOT/docker"
docker compose -f "$COMPOSE_FILE" build   # v1.5 修改：按模式选择 compose 文件

echo ""
echo -e "${GREEN}  ✅ Docker 镜像构建完成${NC}"
echo "  镜像: $IMAGE_NAME ($(docker image inspect $IMAGE_NAME --format='{{.Size}}' 2>/dev/null | awk '{printf "%.0fMB", $1/1024/1024}') )"
echo ""

# =============================================================================
# [2/4] 导出 Docker 镜像
# =============================================================================
echo -e "${GREEN}[2/4] 导出 Docker 镜像为 tar 文件${NC}"
IMAGE_TAR="$BUNDLE_DIR/images/creditwise-latest.tar"
docker save "$IMAGE_NAME" -o "$IMAGE_TAR"
IMAGE_SIZE=$(du -sh "$IMAGE_TAR" | cut -f1)
echo -e "${GREEN}  ✅ 镜像导出完成: ${IMAGE_SIZE}${NC}"
echo ""

# =============================================================================
# [3/4] 打包运行时文件（v1.5：受保护模式改为最小文件集，修正 Gap #2）
# =============================================================================
echo -e "${GREEN}[3/4] 打包运行时文件${NC}"
SOURCE_DIR="$BUNDLE_DIR/source"
mkdir -p "$SOURCE_DIR"

if [ "$PROTECTED_MODE" = "true" ]; then
    # v1.5 新增：受保护模式不 rsync 全量项目源码。
    # 核实依据（code-protection-audit.md §10.4/§9.5）：deploy_offline.sh 运行时
    # 完全不读取 source/ 下的 .py 文件——容器启动用的是镜像内 /app/，不是宿主机
    # source/。因此只需复制 deploy_offline.sh 实际依赖的最小文件集：
    echo "  [受保护模式] 仅复制运行时必需文件（不含 .py 源码），从源头消除泄露面"
    mkdir -p "$SOURCE_DIR/docker" "$SOURCE_DIR/scripts" "$SOURCE_DIR/config"
    # v1.5 重命名为 docker-compose.yml：deploy_offline.sh 第162行执行不带 -f 参数的
    # `docker compose up -d`，按 Docker Compose 约定读取当前目录固定文件名，
    # 重命名比改造 deploy_offline.sh 本身风险更低（见 §5.2.2）
    cp "$PROJECT_ROOT/docker/$COMPOSE_FILE" "$SOURCE_DIR/docker/docker-compose.yml"
    cp -r "$PROJECT_ROOT/scripts/" "$SOURCE_DIR/scripts/"
    cp "$PROJECT_ROOT/config/users.yaml.example" "$SOURCE_DIR/config/" 2>/dev/null || true
    if [ -f "$PROJECT_ROOT/.env.example" ]; then
        cp "$PROJECT_ROOT/.env.example" "$SOURCE_DIR/.env"
    fi
else
    # 标准模式：保持原有全量 rsync 行为不变
    rsync -a \
        --exclude='.git' \
        --exclude='node_modules' \
        --exclude='.next' \
        --exclude='workspace' \
        --exclude='execution_states' \
        --exclude='task_results' \
        --exclude='logs' \
        --exclude='*.db' \
        --exclude='.env' \
        --exclude='offline_bundle' \
        --exclude='creditwise_offline_bundle*' \
        --exclude='.DS_Store' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='deepanalyze/SkyRL' \
        --exclude='deepanalyze/ms-swift' \
        --exclude='playground' \
        --exclude='graphiti-ui' \
        --exclude='.omo' \
        "$PROJECT_ROOT/" "$SOURCE_DIR/"
    if [ -f "$SOURCE_DIR/.env.example" ]; then
        cp "$SOURCE_DIR/.env.example" "$SOURCE_DIR/.env" 2>/dev/null || true
    fi
    if [ -f "$SOURCE_DIR/config/users.yaml.example" ]; then
        cp "$SOURCE_DIR/config/users.yaml.example" "$SOURCE_DIR/config/users.yaml" 2>/dev/null || true
    fi
fi

# 确保运行时需要的目录存在（两种模式都需要）
mkdir -p "$SOURCE_DIR"/{workspace,execution_states,task_results,logs,config}
touch "$SOURCE_DIR/llm_manager.db" "$SOURCE_DIR/task_manager.db"

SOURCE_SIZE=$(du -sh "$SOURCE_DIR" | cut -f1)
echo -e "${GREEN}  ✅ 运行时文件打包完成: ${SOURCE_SIZE}${NC}"
if [ "$PROTECTED_MODE" = "true" ]; then
    echo "  （标准模式下 source/ 通常数十MB含全部源码；受保护模式应仅为数百KB级别，"
    echo "   若本次大小明显偏大，请检查是否误复制了源码目录）"
fi
echo ""

# =============================================================================
# [4/4] 生成离线包
# =============================================================================
echo -e "${GREEN}[4/4] 生成离线部署包${NC}"
ARCHIVE_NAME="creditwise_offline_bundle.tar.gz"
if [ "$PROTECTED_MODE" = "true" ]; then
    ARCHIVE_NAME="creditwise_offline_bundle_protected.tar.gz"
fi
cd "$PROJECT_ROOT"
tar -czf "$ARCHIVE_NAME" offline_bundle/
ARCHIVE_SIZE=$(du -sh "$ARCHIVE_NAME" | cut -f1)
rm -rf "$BUNDLE_DIR"

echo ""
echo "============================================================"
echo -e "${GREEN} 离线包准备完成！${NC}"
echo "============================================================"
echo " 文件: $PROJECT_ROOT/$ARCHIVE_NAME"
echo " 大小: $ARCHIVE_SIZE"
echo ""
echo " 下一步:"
echo "   1. 将 $ARCHIVE_NAME 传输到内网服务器（U盘/SCP）"
echo "   2. tar -xzf $ARCHIVE_NAME && cd offline_bundle/source"
echo "   3. chmod +x scripts/deploy_offline.sh && ./scripts/deploy_offline.sh"
echo "============================================================"
```

#### 5.2.2 `deploy_offline.sh` 是否需要修改

**核实结论（`code-protection-audit.md` §10.3/§9.5，本次已进一步核实 `deploy_offline.sh` 具体实现）**：`deploy_offline.sh` 只依赖 `docker/docker-compose*.yml`、`.env`、`config/`、`scripts/`、镜像 tar 包，完全不读取 `.py` 源文件，**因此 `deploy_offline.sh` 的部署逻辑本身不需要修改**——这正是 Layer 2/3 设计"deploy 端完全无感知"的体现。

但需要处理一个文件命名衔接问题：`deploy_offline.sh` 第 162 行执行的是不带 `-f` 参数的 `docker compose up -d`，按 Docker Compose 约定会读取当前目录下固定文件名 `docker-compose.yml`。而受保护模式打包进 `source/docker/` 的是 `docker-compose.compiled.yml`（不同文件名）。**因此需在 §5.2.1 的 `prepare_offline.sh --protected` 打包步骤中，将 `docker-compose.compiled.yml` 复制后重命名为 `docker-compose.yml`**（已在下方 §5.2.1 代码中体现该重命名逻辑），而不是改动 `deploy_offline.sh` 本身，改动面更小、风险更低。

### 5.3 纯代码包部署：`build_cython.py --output-dir` + `scripts/setup_protected.sh`（v1.6 新增）

> **适用场景**：编译机（Linux）上产出预编译代码包（~31MB），通过邮件/网盘发给目标服务器，目标服务器通过 Docker 部署。

#### 5.3.1 编译机产出

```bash
# 在 Linux 编译机（如 CVM）上执行
pip install cython
python build_cython.py --output-dir dist_protected

# 复制完整项目到 dist_protected/，删除已编译的 .py 源码
rsync -a --exclude='.git' --exclude='node_modules' ... . dist_protected/
cd dist_protected && xargs -a compiled_files.txt rm -f

# 打包（约 31MB，16 个 .so + 前端源码 + 配置文件）
tar -czf creditwise_protected_src.tar.gz dist_protected/
```

> ⚠️ `.so` 绑定编译时 Python 版本（当前 3.11），详见 `docs/deployment_guide.md` 环境要求。

#### 5.3.2 目标服务器部署（一键流程）

```bash
tar -xzf creditwise_protected_src.tar.gz
cd dist_protected
chmod +x scripts/setup_protected.sh

# 一键初始化：.env + 加密密钥 + .db 预创建 + Dockerfile 版本对齐 + 清理 users.yaml
./scripts/setup_protected.sh

# 构建 + 启动
docker compose -f docker/docker-compose.yml up -d

# 登录 admin/admin123（首次登录强制改密）
```

`setup_protected.sh` 自动处理：
- 创建 `.env`（`ENABLE_AUTH=true`）
- 生成 `LLM_MANAGER_ENCRYPTION_KEY`（渠道 API Key 加密存储必需）
- `touch task_manager.db` / `llm_manager.db`（防止 Docker bind mount 创建为目录）
- 修复 Dockerfile Python 版本（编译用 3.11，自动将 Dockerfile 的 3.12→3.11）
- 删除 `config/users.yaml`（含占位符哈希会阻塞 admin 零配置自动引导）

### 5.4 统一入口脚本：`scripts/build_protected.sh`（v1.5 新增，修正 Gap #4）

> 前述 §4.4（编译）、§5.1（镜像构建）、§5.2（离线打包）是三个独立操作，实施时容易遗漏步骤或执行顺序出错。新增顶层编排脚本，串联"本地试编译验证 → Docker 镜像构建 → 离线打包 → 端到端验证"全流程，作为开发/发布时的唯一入口。

```bash
#!/bin/bash
# scripts/build_protected.sh
# 一站式受保护离线部署包构建 + 端到端验证
#
# 用法：
#   ./scripts/build_protected.sh              # 完整流程：编译验证 → 镜像构建 → 打包 → 端到端验证
#   ./scripts/build_protected.sh --skip-verify # 跳过第4步端到端验证（仅用于快速迭代调试）

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SKIP_VERIFY=false
[ "$1" = "--skip-verify" ] && SKIP_VERIFY=true

cd "$PROJECT_ROOT"

echo "============================================================"
echo " CreditWise 受保护部署包 — 一站式构建"
echo "============================================================"

# =============================================================================
# [1/4] 本地 Cython 试编译验证（仅开发调试用，不影响最终镜像内容——
#       镜像内的编译在 Docker Stage 1 内独立完成，见 §5.1.1）
# =============================================================================
echo -e "${GREEN}[1/4] 本地试编译验证${NC}"
python build_cython.py --dry-run
echo -e "${YELLOW}  提示: 上方为编译范围预览，如需实际本地试编译请手动执行:${NC}"
echo "    python build_cython.py --yes --replace"
echo "    pytest tests/ -x"
echo "    python build_cython.py --clean   # 验证完毕后恢复开发环境"
echo ""
read -p "是否已完成本地试编译验证（或确认跳过）？按回车继续..."

# =============================================================================
# [2/4] Docker 编译版镜像构建 + 离线打包
# =============================================================================
echo -e "${GREEN}[2/4] 构建受保护离线部署包${NC}"
chmod +x scripts/prepare_offline.sh
./scripts/prepare_offline.sh --protected

# =============================================================================
# [3/4] 源码清理自检（镜像内验证，防止 Gap #3/#2 类问题回归）
# =============================================================================
echo -e "${GREEN}[3/4] 镜像源码清理自检${NC}"
FOUND=$(docker run --rm creditwise:protected find /app -name "rule_mining.py" 2>/dev/null || true)
if [ -n "$FOUND" ]; then
    echo -e "${RED}  ✗ 失败: 镜像内仍残留 rule_mining.py 源码，保护未生效${NC}"
    exit 1
fi
echo -e "${GREEN}  ✓ 核心算法源码已确认清理${NC}"

BAK_FOUND=$(docker run --rm creditwise:protected find /app -name "*.py.bak" 2>/dev/null || true)
if [ -n "$BAK_FOUND" ]; then
    echo -e "${RED}  ✗ 失败: 镜像内残留 .py.bak 文件（Gap B 回归）${NC}"
    exit 1
fi
echo -e "${GREEN}  ✓ .py.bak 清理确认通过${NC}"

# =============================================================================
# [4/4] 离线部署端到端验证（模拟内网服务器，见 §6.2 验收标准）
# =============================================================================
if [ "$SKIP_VERIFY" = "true" ]; then
    echo -e "${YELLOW}[4/4] 跳过端到端验证 (--skip-verify)${NC}"
else
    echo -e "${GREEN}[4/4] 离线部署端到端验证${NC}"
    VERIFY_DIR="/tmp/creditwise_verify_$(date +%s)"
    mkdir -p "$VERIFY_DIR"
    tar -xzf creditwise_offline_bundle_protected.tar.gz -C "$VERIFY_DIR"
    cd "$VERIFY_DIR/offline_bundle/source"
    chmod +x scripts/deploy_offline.sh
    ./scripts/deploy_offline.sh

    sleep 5
    HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8200/health || echo "000")
    if [ "$HEALTH" != "200" ]; then
        echo -e "${RED}  ✗ 失败: /health 返回 $HEALTH${NC}"
        exit 1
    fi
    echo -e "${GREEN}  ✓ /health 200${NC}"

    LLM_MGR=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8200/llm-manager/ || echo "000")
    echo -e "${GREEN}  ✓ /llm-manager/ 返回 $LLM_MGR${NC}"

    cd "$PROJECT_ROOT"
    rm -rf "$VERIFY_DIR"
fi

echo ""
echo "============================================================"
echo -e "${GREEN} 受保护部署包构建 + 验证全部完成${NC}"
echo "============================================================"
echo " 产出: $PROJECT_ROOT/creditwise_offline_bundle_protected.tar.gz"
echo "============================================================"
```

### 5.5 CI/CD 集成

```yaml
# .github/workflows/build-protected.yml (示例)
name: Build Protected Image

on:
  workflow_dispatch:
    inputs:
      version:
        description: '版本号'
        required: true

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build Docker Image
        run: |
          docker build -f docker/Dockerfile.compiled \
            -t ghcr.io/your-org/deepanalyze:${{ inputs.version }}-protected .

      - name: Push to Registry
        run: |
          docker push ghcr.io/your-org/deepanalyze:${{ inputs.version }}-protected
```

---

## 6. 实施路线

### 6.1 时间线（v1.5：新增 Layer 3 衔接工作，共 6 天）

```
第 1 天 (0.5 天，默认路径)
├─ [✓] 实现 API/deploy_guard.py（轻量部署审批开关，见 §3.0）
├─ [✓] 在 API/main.py 集成 check_deploy_approved()
├─ [ ] （可选，仅面向外部客户场景）实现 Ed25519 版 license_validator.py，见 §3.1-§3.5
└─ [✓] 审计 validators.py 中的 eval() 沙箱是否存在用户输入路径

第 2 天 (0.5 天，Cython 试点)
├─ [✓] 安装 Cython + 编译工具链（建议直接在 Docker/Linux 环境完成，规避 Windows MSVC 配置）
├─ [✓] 试点编译 1 个小文件（woe.py）验证工具链可用
├─ [✓] 试点编译最大文件 rule_mining.py，观察耗时/内存/编译器报错（见 §4.7.3）
└─ [ ] 若大文件编译失败 → 评估拆分方案，此项可能增加 0.5-1 天

第 3-4 天 (1.5-2 天，批量编译)
├─ [✓] 创建 build_cython.py（含 v1.5 的 compiled_files.txt 清单机制，见 §4.4）
├─ [✓] 编译 P0 模块（rule_mining + scorecard_development + executor）
├─ [✓] 编译 P1 模块（报告引擎 + 数据分析引擎）
├─ [✓] 全量 import 烟雾测试 + pytest 全跑（见 §4.7.3 第四步）
├─ [✓] 修复编译兼容性问题
└─ [✓] 性能基准测试（如实记录：未加类型标注时性能提升可能不明显）

第 5 天 (1 天，Layer 3 衔接——v1.5 新增，修正 Gap #1/#2/#3/#4)
├─ [✓] 创建 docker/Dockerfile.compiled（目录级 COPY + 按清单删除源码，见 §5.1.1）
├─ [✓] 创建 docker/docker-compose.compiled.yml（打通与真实 docker-compose.yml 的对接，见 §5.1.3）
├─ [✓] 修改 scripts/prepare_offline.sh 增加 --protected 参数（最小文件集打包，见 §5.2.1）
├─ [✓] 创建 scripts/build_protected.sh 统一入口脚本（见 §5.4）
├─ [✓] 构建受保护镜像，验证 docker exec find 确认源码已清理
└─ [✓] 验证 .py.bak 无残留（Gap B 自检）

第 6 天 (0.5-1 天，端到端验证与收尾)
├─ [✓] 执行 ./scripts/build_protected.sh 全流程验证（模拟内网部署，见 §6.2）
├─ [✓] curl 全量功能回归（/health、首页、LLM Manager、main.css、API 认证）
├─ [✓] 编写部署文档
└─ [✓] 清理开发环境中的编译产物
```

### 6.2 验收标准

| 测试项 | 标准 |
|--------|------|
| **功能完整性** | 所有现有 pytest 测试通过 |
| **授权验证（默认轻量方案）** | 无 `DEPLOY_APPROVAL_TOKEN` 或不匹配 → 拒绝启动 |
| **授权验证（可选完整方案，面向外部客户时）** | 无 license.lic → 拒绝启动；过期/机器指纹不匹配/签名被篡改 → 均拒绝启动 |
| **编译验证** | 核心 .py 文件已被 .pyd/.so 替代，且构建产物中不再残留对应源码（验证 `find /app -name "rule_mining.py"` 为空） |
| **编译稳定性** | 401KB/286KB 大文件试点编译能在合理时间内（建议 <5 分钟）成功完成，无编译器堆内存报错 |
| **性能基准** | API 响应时间无明显衰退（未加类型标注的 Cython 编译不保证提速，只需确认不劣化） |
| **Docker 验证** | `docker run` 可正常启动，前端可访问，FastAPI `/docs` 页面正常渲染（验证 API 层未被误编译） |
| **`.py.bak` 清理验证**（v1.5 新增，Gap B） | `docker exec <container> find /app -name "*.py.bak"` 无输出 |
| **P2 编译一致性验证**（v1.5 新增，Gap #3） | 若使用 `--include-p2` 编译，需确认 `Dockerfile.compiled` 的 compiler 阶段已同步扩展 COPY 范围，编译日志中不应出现 P2 文件的 `⚠ SKIP` 告警 |
| **Docker 离线部署端到端验证**（v1.5 新增，Gap #1/#2/#5） | `./scripts/prepare_offline.sh --protected` → 解压到隔离目录 → `deploy_offline.sh` → `curl /health` 200 → `curl /llm-manager/` 200 → `main.css` 大小正常 → `pytest` 通过 → 容器内 `find /app -name "rule_mining.py"` 无输出 → **解压后的 `source/` 目录大小应为数百 KB 级别（不含任何 `.py` 源码），而非标准模式下的数十 MB** |
| **回滚能力** | `python build_cython.py --clean` 可恢复开发环境 |

### 6.3 回滚方案

```bash
# 如编译后出现问题，一键回滚
python build_cython.py --clean     # 清理编译产物，恢复 .py 文件
git checkout .                      # 恢复原始源码
```

---

## 7. 风险与注意事项

### 7.1 技术风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| **Cython 版本兼容性** | 编译产物绑定特定 Python 版本（如 3.12） | 对齐目标部署环境的 Python 版本 |
| **超大单文件触及 C 编译器限制**（新增，v1.2） | 401KB/286KB 文件转译后可能导致 MSVC/GCC 报堆内存/内部限制错误，或编译耗时暴涨 | 采用 §4.7.3 分阶段验证策略，先试点大文件，失败则拆分 |
| **P2 编译清单与 Dockerfile COPY 范围脱节**（新增，v1.5，源自审计 Gap #3） | 若启用 `--include-p2` 但忘记同步扩展 `Dockerfile.compiled` 的 COPY 范围，P2 文件会静默 SKIP、源码残留、保护失效 | `build_cython.py` 已改为 stderr 告警 + 输出 `compiled_files.txt`，Dockerfile 按清单删除而非硬编码，见 §4.4/§5.1.1；验收时检查编译日志无 P2 相关 SKIP 告警 |
| **离线包 `source/` 目录源码泄露**（新增，v1.5，源自审计 Gap #2，已确认是当前唯一真实存在的泄露路径） | `prepare_offline.sh` 标准模式 rsync 全量项目源码，`.py` 明文可读，无需宿主机权限即可从离线包直接提取 | `--protected` 模式改为最小文件集复制，见 §5.2.1；验收时检查 `source/` 目录大小应为数百 KB 级别 |
| **C 扩展冲突** | `scorecardpy`、`numpy` 等 C 扩展可能冲突 | 第三方库不编译，只编译自有代码 |
| **eval() 沙箱逃逸（validators.py）** | Cython 编译不会修复 `eval()` 本身的安全问题 | 需在代码层面审计/加固 `safe_globals` 沙箱，而非依赖编译掩盖 |
| **FastAPI 反射依赖** | 编译 `sop_api.py` 等路由文件会破坏 OpenAPI/依赖注入 | 严格执行 `DO_NOT_COMPILE` 清单，不编译任何含 `@router.*` 的文件 |
| **性能预期偏差** | 未加类型标注的 Cython 编译主要提供混淆，不保证提速 | 验收时不以性能提升为达标条件，只需不劣化 |
| **License 对称密钥泄露风险** | 若走 §3.1 完整方案且误用对称加密，密钥泄露=保护失效 | 采用 §3.1 的 Ed25519 非对称签名方案（默认轻量方案 §3.0 不涉及此风险） |
| **容器指纹漂移**（仅适用于走完整方案时） | 容器重建导致 Docker 内机器指纹变化 | 挂载宿主机 `/etc/machine-id`，见 §3.5 |
| **`.py.bak` 潜在残留**（新增，v1.5，源自审计 Gap B） | 若未来 Dockerfile 重构改变 COPY 顺序/来源，编译中间产物 `.py.bak` 可能意外进入镜像 | `Dockerfile.compiled` 增加 `RUN find /app -name "*.py.bak" -delete` 防御性清理，见 §5.1.1 |
| **Traceback 可读性** | 编译后堆栈跟踪不显示源码行号 | 开发环境保留 `.py`，部署版本另备调试工具 |
| **kaleido 硬依赖** | 图表渲染需系统级 Chromium 共享库 | Docker 镜像中预装好依赖 |
| **`.so` glob 前缀冲突**（v1.6 已修复） | `rule_mining*.so` glob 同时匹配 `rule_mining_meta.so`，导致 401KB 最大核心模块丢失、SOP API 加载失败 | 改用 `{base}.*.so` 精确 glob（`rule_mining.*.so` 不匹配 `rule_mining_meta.*.so`） |
| **纯代码包 Python 版本绑定**（v1.6 新增） | `.so` 编译于 CVM Python 3.11，目标服务器必须对齐。Docker 离线包无此问题（Stage1/3 同基础镜像） | `deployment_guide.md` 标注版本要求；`setup_protected.sh` 自动对齐 Dockerfile 版本 |
| **Docker bind mount `.db` 目录化**（v1.6 新增） | 部署前 `task_manager.db` 不存在时，Docker 在 bind mount 路径创建空目录而非文件，SQLite 报 `unable to open database file` | `setup_protected.sh` 启动前 `touch` 预创建 `.db` 文件 |
| **`.env` 缺加密密钥**（v1.6 新增） | 纯代码包未运行部署脚本，`.env` 中无 `LLM_MANAGER_ENCRYPTION_KEY`，渠道创建报 `undefined` | `setup_protected.sh` 自动生成并写入；Docker 离线包由 `deploy_offline.sh` 自动生成 |
| **`deploy_offline.sh` 空 `if` 块**（v1.6 已修复） | Bash 不允许 `then/fi` 间仅含注释，移除 `users.yaml` 创建逻辑后遗留空块导致语法错误 | 添加 `:`（空操作）占位命令 |
| **`deploy_offline.sh` 相对路径跨项目污染**（v1.6 已修复） | Docker Compose 不同版本对 `volumes` 相对路径解析行为不一致，手动部署时可能挂载到其他项目的旧数据库 | `sed` 将 compose 文件中 `../` 替换为 `$PROJECT_ROOT/` 绝对路径 |
| **`channels.py` logger 未定义**（v1.6 已修复） | `create_channel` 中 `logger` 在内部 `except` 块才定义，外部 `except` 触发 `UnboundLocalError` | `logger` 提到函数顶部统一初始化 |

### 7.2 运营风险

| 风险 | 缓解措施 |
|------|----------|
| `DEPLOY_APPROVAL_TOKEN` 泄露（默认轻量方案） | 每次部署更换 token，不复用；仅作软控制，不承担强安全职责 |
| License 私钥泄露（仅走 §3.1 完整方案时） | 私钥仅存于签发端安全环境，使用环境变量注入公钥，不在代码仓库中存储 |
| 多客户授权管理混乱（仅走完整方案时） | 建立授权记录表，每台机器唯一 license |
| 客户机器变更导致授权失效（仅走完整方案时） | 提供 reissue 流程，旧 license 立即作废 |
| 开发/调试体验下降 | CI/CD 仅对 release 分支执行编译，开发分支保留源码 |

### 7.3 法律与合规

- ✅ 代码加密/编译系保护自有知识产权，属合法行为
- ✅ 不涉及第三方库的二次修改/重分发问题
- ⚠️ 确保编译方案不违反 `scorecardpy`、`scikit-learn` 等第三方库的 BSD/MIT 许可证
- ⚠️ 如涉及出海/出口管制，确认加密方案符合当地法规

---

## 8. 附录

### 8.1 文件清单

| 新增/修改文件 | 用途 |
|----------|------|
| `build_cython.py` | Cython 编译脚本（v1.5：拆分 P2 清单 + 输出 `compiled_files.txt`） |
| `API/deploy_guard.py` | **[默认]** 轻量部署审批开关（见 §3.0），v1.5 起归入 `KEEP_CLEAR` |
| `API/license_validator.py` | **[可选，面向外部客户]** 机器授权验证器（Ed25519 签名验证），v1.5 起归入 `KEEP_CLEAR` |
| `scripts/license_signer.py` | **[可选]** 密钥对生成 + 授权文件签发（仅在签发端使用，不随产品分发） |
| `docker/Dockerfile.compiled` | 编译版 Docker 镜像构建文件（v1.5：目录级 COPY + 按 `compiled_files.txt` 清单删除源码） |
| `docker/docker-compose.compiled.yml` | **[v1.5 新增]** 与真实 `docker-compose.yml` 对接，供 `prepare_offline.sh --protected` 调用 |
| `scripts/prepare_offline.sh` | **[v1.5 修改]** 增加 `--protected` 参数（最小文件集打包，见 §5.2.1），非 `--protected` 模式保持原有行为不变 |
| `scripts/build_protected.sh` | **[v1.5 新增]** 统一入口脚本，串联编译→构建→打包→端到端验证全流程（见 §5.4） |
| `scripts/setup_protected.sh` | **[v1.6 新增]** 纯代码包首次部署一键初始化（`.env`、加密密钥、`.db` 预创建、Dockerfile 版本对齐），见 §5.3 |
| `scripts/mingw_env_setup.ps1` | **[v1.6 新增]** Windows 便携式 MinGW-w64 环境变量配置脚本 |
| `docs/code-protection-plan.md` | 本文档 |
| `docs/code-protection-audit.md` | 四轮审计报告，本文档 v1.6 的全部变更均可溯源至 `feature/code-protection` 分支 commit 历史 |

### 8.2 常用命令速查

```bash
# === Cython 编译（建议按 §4.7.3 分阶段执行，不要一次性 --all）===
python build_cython.py --dry-run              # 预览编译范围（P0+P1）
python build_cython.py --yes                   # 编译 P0+P1（非交互）
python build_cython.py --all --yes             # 额外编译待审计模块（validators.py）
python build_cython.py --include-p2 --yes      # 额外编译 P2（需已扩展 Dockerfile COPY 范围）
python build_cython.py --yes --replace         # 编译后用产物替换 .py，并输出 compiled_files.txt
python build_cython.py --output-dir dist_protected  # v1.6: 输出到独立目录，源码无损
python build_cython.py --clean                 # 清理所有编译产物，恢复 .py
python build_cython.py --restore                # 恢复 .py.bak → .py

# === 默认轻量部署审批（§3.0）===
export DEPLOY_APPROVAL_TOKEN_EXPECTED="<本次部署约定的 token>"   # 部署环境配置
export DEPLOY_APPROVAL_TOKEN="<发给部署方的 token>"              # 需匹配才能启动

# === 授权管理（可选，仅面向外部客户场景，在签发端安全环境执行）===
python scripts/license_signer.py --genkey                    # 首次生成密钥对
python scripts/license_signer.py <machine-id> 2026-12-31     # 为客户机器签发 license.lic

# === 客户端：获取机器指纹（仅可选完整方案需要，发给签发方）===
python -c "from API.license_validator import get_machine_fingerprint; print(get_machine_fingerprint())"

# === Docker 构建（本地开发验证）===
docker build -f docker/Dockerfile.compiled -t creditwise:protected .
docker save creditwise:protected | gzip > creditwise_protected.tar.gz

# === 离线部署包构建（v1.5 新增，推荐用统一入口脚本）===
./scripts/build_protected.sh                # 完整流程：编译验证 → 镜像构建 → 打包 → 端到端验证
./scripts/build_protected.sh --skip-verify  # 跳过第4步端到端验证，用于快速迭代调试
# 或单独调用：
./scripts/prepare_offline.sh --protected    # 仅构建受保护离线包，不做端到端验证

# === 纯代码包部署（v1.6 新增，见 §5.3）===
python build_cython.py --output-dir dist_protected   # 编译 .so 到独立目录
cd dist_protected && ./scripts/setup_protected.sh    # 一键初始化环境
docker compose -f docker/docker-compose.yml up -d     # Docker 部署启动

# === 测试验证（§4.7.3 CI 强制关卡 + §6.2 验收标准）===
pytest tests/                                                         # 运行测试套件
python -c "from deepanalyze.analysis.task_SOP.rule_mining import *"   # 验证导入
docker run --rm creditwise:protected find /app -name "rule_mining.py" # 应无输出（源码已清理）
docker run --rm creditwise:protected find /app -name "*.py.bak"       # 应无输出（Gap B 自检）
```

### 8.3 参考资料

- [Cython 官方文档](https://cython.readthedocs.io/)
- [Cython 编译指令参考](https://cython.readthedocs.io/en/latest/src/userguide/source_files_and_compilation.html)
- [cryptography Ed25519 签名](https://cryptography.io/en/latest/hazmat/primitives/asymmetric/ed25519/)
- [Python 导入机制：.pyd/.so 优先级](https://docs.python.org/3/reference/import.html)
- `docs/code-protection-audit.md` —— 四轮审计全过程，本文档 v1.5 的每一项变更均可在其 §10.5 最终清单中找到对应发现项

---

> **总结**：默认方案为"轻量部署审批（§3.0） + Cython 编译核心算法（不含 FastAPI 路由，§4）+ Docker 分发全链路衔接（§5）"，预计 **5-6 天**完成实施（较 v1.4 增加约 1-2 天，用于落地 §5.1-§5.4 的 Layer 3 衔接工作）。若未来需要交付给不受控的外部客户，可平滑升级为"Ed25519 签名 + 机器指纹绑定（§3.1-§3.5）"的完整方案，额外增加约 1 天工作量。**需明确认知边界**：本方案不追求"绝对不可破解"，实际效果是显著提高逆向成本（而非"极难逆向"），性能收益也非必然（未做类型标注时主要是混淆而非加速），Cython 编译大文件存在真实的编译器兼容性风险，务必按 §4.7.3 分阶段验证再批量推进。**v1.5 的核心变化**：此前版本的 Layer 3（§5）内容与项目真实部署脚本（`prepare_offline.sh`/`deploy_offline.sh`）完全脱节，本版本已对齐真实脚本结构，可直接据此开发，不再需要额外的方案落地设计工作。
