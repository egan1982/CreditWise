# 用户管理与数据隔离模块设计方案

> 创建时间: 2026-07-01 | 评审更新: 2026-07-02（autoplan CEO/Design/Eng 三阶段评审 + 6项品味决策已确认）
> 状态: ✅ **批次1、批次2均已开发完成并通过全部单元测试**（2026-07-02，详见§九/§十七）；用户管理与数据隔离模块整体开发完成；批次2上线后另完成一轮部署链路加固（首个账户零配置自动创建 + fail-open/Docker挂载/部署脚本锁死隐患修复，详见§二十）
> 需求出处（文档引用）:
> - `docs/intranet_deployment_guide.md` §5「尚未完成的部署相关工作」+ §6「安全注意事项」数据隔离行
> - `docs/online_multiuser_deployment_assessment.md` §五「已知遗留问题」#2（任务历史未按用户隔离）、#5（workspace目录应基于登录用户名）
> - `docs/project_status_summary.md` 第18项
> **开发评审**: ✅ 已完成 autoplan 三阶段评审（CEO/Design/Eng，Claude subagent 独立双声道，Codex CLI 未安装故为 [subagent-only]）。详见文末「评审与决策审计记录」

---

## 📌 快速回顾（评审后更新）

本模块的核心特点：**既要修复数据隔离/越权安全问题，也要提供完整的 Web UI 账号管理能力**（管理员可通过前端界面新增/编辑/禁用账户、重置密码；普通用户可通过前端自助改密），彻底取代当前"编辑yaml+重启服务"的手工运维方式。

**关键变化（相对 2026-07-01 初版）**：
1. **按发布顺序拆分为两个批次**（CEO评审，仅影响上线时间先后，不影响设计完整性）：
   - **批次1（安全紧急，先行发布）**：workspace 身份隔离 + 越权修复 + 任务历史按用户过滤。~5.3天（原SSE鉴权修复项已撤销，见§1.3）。
   - **批次2（紧随其后发布）**：账号管理 Web UI（管理员新增/编辑/禁用/重置密码，普通用户自助改密），~5天。**完整正式设计，非参考草稿**。
2. **批次1身份隔离键实现方式简化**（CEO+Eng评审）：不新增 `owner_username` 字段，直接让 `session_id` 的值承载登录用户名；新增独立 `tab_id` 字段满足"多标签页区分"这一次要需求。
3. **批次1所有权校验方式简化**（Eng评审延伸）：后端一律从 `request.state.user.username` 派生身份，忽略客户端传入的 `session_id`/`owner` 参数。
4. **【已撤销】SSE鉴权洞**：开发阶段核实`/sop/status/{execution_id}/stream`从未实现（仅存于归档设计文档），原判断有误，已撤销该项专项修复，改为并入Phase 3常规所有权校验。
5. **批次2技术路线**：启动开发前先完成一次"评估集成`fastapi-users`库 vs 自建"的技术选型（TD3），本文档给出的是"自建"路径的完整设计（已具备实施细节），若选型结果改为引入`fastapi-users`，只需按其API重新映射本文档已确定的产品/交互决策（权限矩阵、密码告知机制等不变）。
6. **新建用户/重置密码告知机制**（TD4，批次2核心交互）：一次性明文展示 + 首次登录强制改密，两者都做。
7. **username字符集约束**（TD6）：`^[a-zA-Z0-9_-]+$`，批次2创建账户UI需据此做实时校验。

---

## 一、现状调研结论（代码库核实）

### 1.1 认证体系（已具备，可复用）
`API/auth_middleware.py` 的 `SimpleAuth`/`BasicAuthMiddleware` 已实现 Basic Auth + bcrypt + 角色区分 + 账户锁定 + `valid_until` 有效期校验。

⚠️ **关键缺口**：`request.state.user` 被设置后从未被业务路由读取用于所有权校验（批次1要解决）。

### 1.2 身份标识与数据隔离（核心缺陷，批次1解决）
- `session_id` 由前端纯随机生成（`three-panel-interface.tsx` 第203-210行），与登录用户名无关联，走 Query/Form 参数传递。
- 作为隔离键的位置：`get_session_workspace(session_id)` → `workspace/{session_id}/`；`task_records`/`execution_states` 表 `session_id` 字段（有索引 `idx_session_created`，非唯一）。
- `session_id` 实际调用面：`sop_api.py`（50+处引用）、`main.py`（8个 `/workspace/*` 路由）、`chat_api.py`、`file_api.py`、`export_api.py` 共5个文件——**Phase 3 工作量需按此规模重新估算**。
- `TaskHistoryService.list_records(session_id=...)` 中过滤是**可选**参数，无路由强制按当前登录用户过滤。

### 1.3 【已纠正】原TD5前提不成立：SSE端点实际不存在于代码库

⚠️ **2026-07-02 开发阶段核实纠正**：CEO评审曾指出 `/sop/status/{execution_id}/stream`（SSE推送）存在匿名订阅漏洞（TD5），据此决定纳入批次1修复。**开发时核实发现该前提不成立**：
- `/sop/status/{execution_id}/stream` **从未在代码库中实现**，仅出现在已归档的设计文档 `docs/archive/SOP_WebUI_Integration_design.md`（历史规划，未落地）。
- `API/sop_api.py` 实际只有 `@router.get("/status/{execution_id}")`（第919行，普通轮询接口），**不以`/stream`结尾**，因此不匹配 `auth_middleware.py` 的 `SSE_WHITELIST_PATTERNS` 白名单规则，本来就需要正常认证才能访问——**不存在"匿名可访问"的漏洞**。
- `SSE_WHITELIST_PATTERNS` 这条白名单规则是**死代码**（永远不会被匹配到任何真实路由），建议作为技术债清理，但不影响安全性（无害）。
- **真实存在、但性质不同的问题**：`/sop/status/{execution_id}` 已认证，但**缺少归属校验**——任何已登录用户可轮询任意 `execution_id` 的状态（不区分是否属于自己）。这是普通的水平越权问题，已并入 §五 Phase 3 的"受影响路由清单"统一处理，**不需要单独的SSE token机制**。



### 1.4 账号管理现状（批次2要解决）
`config/users.yaml` 纯手工维护：新增/改密均需人工编辑文件 + 运行 `hash_password.py` + 重启服务，**无任何 API/UI**。`scripts/hash_password.py` 是纯CLI工具，无自动化增删改流程。全局搜索无任何 `/auth/*`、`/admin/users` 等管理API；`API/admin_api.py` 已标注 `[ARCHIVED]` 且未注册。

---

## 二、范围与目标

### 2.1 批次1目标（安全紧急，先行发布）
1. 消除身份割裂：以登录用户名为唯一数据隔离维度，替代不可靠的随机 `session_id`。
2. 补齐所有权校验：杜绝水平越权访问他人 workspace/任务数据。
3. 修复已知SSE鉴权洞。
4. 平滑迁移：不丢失、不误合并现网已有的历史数据。

### 2.2 批次2目标（账号管理Web UI，紧随批次1发布）
1. **管理员可通过前端界面**完成账户全生命周期管理：新增、编辑角色/有效期、启用/禁用、重置密码——**彻底取代手工编辑yaml+重启**这一运维模式。
2. **普通用户可通过前端界面**自助修改密码、编辑个人信息（显示名/部门备注），无需联系管理员。
3. 严格的角色权限分层：管理员菜单/操作与普通用户菜单/操作在前端UI层和后端API层双重隔离。

### 2.3 In Scope / Out of Scope

| 范围 | 内容 | 批次 |
|------|------|:---:|
| ✅ | 身份隔离键统一、workspace按用户名隔离、所有权强制校验、任务历史按用户过滤、SSE鉴权修复、历史数据迁移、账户合并小工具 | 批次1 |
| ✅ | 账号存储（users表）、管理员Web UI全套账户CRUD、普通用户自助改密Web UI、权限矩阵、新用户密码告知机制 | 批次2 |
| ❌ | 用户自助注册 | 不做 |
| ❌ | LLM渠道按用户隔离/配额 | 不做（现状全局共享可接受） |
| ❌ | 引入JWT/OAuth等新认证协议 | 不做（维持Basic Auth） |
| ❌ | 单用户模式（`ENABLE_AUTH=false`）下的任何改动 | 不适用，见2.4 |

### 2.4 部署模式适用范围：批次1和批次2均只适用于多用户模式（`ENABLE_AUTH=true`）
单用户模式下无登录态，本模块整体不生效，判断依据见 `API/main.py` L116-134 的 `ENABLE_AUTH` 判断逻辑。`/auth/mode` 探测接口（供前端判断是否隐藏账户相关菜单）属于批次2交付物。

### 2.5 username 字符集约束（TD2衍生决策，TD6已确认）

批次1决定"session_id直接承载username"（见§三），引入一个约束：**username 必须同时满足 workspace 目录名的安全字符集**：

```
^[a-zA-Z0-9_-]+$
```

| 场景 | 是否支持 |
|------|:---:|
| `zhangsan` / `analyst01` / 拼音/工号风格 | ✅ |
| 中文名（如"张三"） | ❌ |
| 邮箱格式登录名（如`zhang.san@company.com`） | ❌ |
| 含空格的名字 | ❌ |

**已确认（TD6）**：接受该约束，不引入额外的目录安全slug映射层。批次2创建账户UI需在用户名输入框做实时校验+提示"仅支持英文字母、数字、下划线、连字符，建议使用拼音或工号"，并同步写入 `intranet_deployment_guide.md` §3.3 用户命名规范。

---

# 第一部分：批次1 — Workspace身份隔离与越权修复

## 三、批次1 核心设计决策

| 决策项 | 方案 | 理由 |
|--------|------|------|
| **身份隔离键实现** | `session_id` 的值直接改为登录用户名，**不新增** `owner_username` 字段。衍生约束见§2.5 | 省去新表列+双轨过滤逻辑，减少50+调用点改造复杂度 |
| **多标签页区分需求** | 新增独立 `tab_id`（前端 `sessionStorage`，随机生成，仅用于UI层区分，不参与数据隔离判断） | 把"识别标签页"与"数据归属"彻底解耦 |
| **所有权校验实现** | 后端认证通过后，业务逻辑一律从 `request.state.user.username` **派生** `session_id`/workspace路径，**忽略/拒绝**客户端传入的 `session_id`/`username`/`owner` 参数；admin查看指定用户数据走单独的 `/admin/workspace/{username}/*` 命名空间 | 消除"比较是否一致"这一易错逻辑，从架构根源杜绝绕过空间 |
| **~~SSE鉴权~~（已撤销，见§1.3）** | ~~原计划为SSE端点加token校验~~ → **该端点不存在于代码库，无需修复**；`/sop/status/{execution_id}`（实际的轮询接口）并入下方"所有权校验实现"统一处理 | 开发阶段核实纠正，见§1.3 |
| **迁移策略** | 用户自助认领（登录后检测本地残留旧`sessionId`，一键关联）为**主路径**；admin人工映射为兜底，仅处理用户已清缓存、无法自证的残留数据 | 用户自证归属错误率远低于admin猜测 |
| **迁移原子性** | 脚本按"先回填/重命名DB记录 → 再移动文件目录 → 写入进度记录"固定顺序执行，支持中断后从进度记录恢复 | 避免文件/DB不一致，保证真正幂等 |
| **账户重名冲突** | `POST /admin/users`创建时，若`username`已存在但`enabled=0`，返回409并提示"请通过编辑接口的启用操作复活" | 避免IntegrityError未捕获导致500 |
| **username 是否可自助修改** | 不可以。改名走管理员软删除旧账户+创建新账户，配套「账户合并」小工具转移历史数据 | `username`深度绑定workspace目录名，允许改名引入级联重命名风险 |

## 四、批次1 数据模型变更

### 4.1 无需新增数据库表或字段
身份隔离键直接复用现有 `session_id` 字段（取值语义变化），批次1**不需要ALTER TABLE，不需要新建users表**（账号存储属于批次2）。

### 4.2 前端新增字段（仅本地存储）
```
localStorage["sessionId"]   ← 登录后由 /auth/me 返回的 username 填充，不再是随机字符串
sessionStorage["tabId"]     ← 新增，纯随机生成，仅用于UI层区分多标签页，不传给后端做隔离判断
```

### 4.3 workspace 目录结构调整
```
workspace/
├─ {username}/              ← 与 session_id（=username后）一致，无需额外映射层
│   ├─ credit_data.csv
│   └─ generated/
└─ _legacy/                 ← 迁移后旧 session_随机ID 目录归档于此（迁移脚本移动，非删除）
    └─ session_1711782000_a1b2c/
```

### 4.4 ~~SSE短期token~~（已撤销）
原计划为`/sop/status/{execution_id}/stream`设计HMAC签名token机制；开发阶段核实该端点从未实现（见§1.3），此设计不再需要。如未来真正实现SSE推送功能，可复用此处思路（无状态HMAC签名，TTL短周期）。

## 五、批次1 API设计

| 方法 | 路径 | 权限 | 说明 |
|------|------|:----:|------|
| GET | `/auth/me` | 已登录 | 返回当前用户 `username`（批次1最小实现，供前端设置`session_id`用） |
| POST | `/workspace/claim-legacy-session` | 已登录 | 用户自助认领：body传旧session_id，校验目录存在后执行迁移 |
| （既有）`/workspace/*`、`/sop/*`等路由（含 `/sop/status/{execution_id}` 轮询接口） | 已登录 | 后端强制从 `request.state.user.username` 派生身份，忽略客户端传入参数；admin查看他人数据走 `/admin/workspace/{username}/*` |

**关键改动点**：
- `API/utils.py::get_session_workspace` 调用方一律改为传入 `request.state.user.username`。
- `TaskHistoryService.list_records()` 增加强制参数 `current_user`：非admin时无条件加 `WHERE session_id = current_user`；admin默认查全部。
- `API/sop_api.py::get_task_status`（第919行，`/sop/status/{execution_id}` 轮询接口）需增加归属校验：根据`execution_id`查出其`session_id`，与`request.state.user.username`不一致且非admin时返回403。
- 受影响文件清单（Phase 3前置交付物）：`main.py`（8处）、`sop_api.py`（50+处，含`get_task_status`）、`chat_api.py`、`file_api.py`、`export_api.py`。
- 技术债清理（可选，不影响功能）：`auth_middleware.py`的`SSE_WHITELIST_PATTERNS`是死代码（对应路由从未实现），可评估是否删除。

## 六、批次1 数据迁移方案

新增 `scripts/migrate_user_isolation.py`：

1. **用户自助认领（主路径）**：登录后前端检测本地`localStorage["sessionId"]`是否为旧随机格式（`session_\d+_\w+`）且与当前用户名不同，若是则展示提示条"检测到本机历史会话`session_xxx`，是否关联到当前账户？"，确认后调用 `POST /workspace/claim-legacy-session`。
2. **admin人工映射（兜底）**：仅处理用户已清缓存、无法自证的残留目录。生成CSV报表供人工比对填写映射文件。
3. **执行顺序**（保证幂等与中断恢复）：①先执行DB更新 `UPDATE task_records SET session_id={username} WHERE session_id={old_id}` ②再移动`workspace/{old_id}/`到`workspace/{username}/`（同名文件加时间戳后缀）③写入本地进度文件标记完成。重跑脚本先读进度文件，跳过已完成项。
4. **未映射数据**：保留在`_legacy/`，仅admin可见，按需人工后续处理。

> 迁移脚本默认dry-run，需显式`--apply`才真正执行。

## 七、账户合并小工具

供改名场景使用：admin可将旧`session_id`（=旧username）名下的`task_records`/`execution_states`/workspace目录，批量转移到新username名下（在批次2的Admin用户管理页面提供入口，见§十六）。

## 八、批次1 安全考虑（对齐`security_rules`）

| 检查项 | 措施 |
|--------|------|
| **AuthZ（重点）** | 所有权判断不基于"比较客户端参数与认证身份是否一致"，而是直接用认证身份覆盖/派生 |
| ~~SSE鉴权洞~~ | 已撤销，见§1.3（该端点不存在于代码库，原判断有误） |
| 路径遍历 | `username`沿用现有`validate_session_id`白名单正则校验 |
| 迁移脚本安全 | 默认dry-run；DB优先+移动（非删除）+进度记录支持中断恢复 |
| 审计 | 账户合并操作、用户自助认领操作均写入`logs/` |

## 九、批次1 Phase划分与工作量估算

> ✅ **2026-07-02 批次1全部Phase已完成开发并通过测试验证**（下表状态列为实际完成情况）

| Phase | 内容 | 工作量 | 状态 |
|:-----:|------|:------:|:---:|
| 1 | 身份统一：前端登录后用username填充session_id + tab_id + 后端从认证身份派生身份 | ~1天 | ✅ 完成 |
| 2 | ~~SSE鉴权修复~~（已撤销，端点不存在，见§1.3）——工作量归还 | ~0天 | ✅ 已撤销 |
| 3 | 所有权强制落地：梳理并改造全部受影响路由（含`get_task_status`归属校验，先产出受影响路由清单，再逐条改造+单测） | ~2天 | ✅ 完成（实际27处：`main.py`10个workspace路由+`sop_api.py`19个execution_id端点+7个入口session_id派生） |
| 4 | 任务历史按用户过滤 | ~0.5天 | ✅ 完成（`list_task_history`强制过滤+13个record_id端点所有权校验+批量删除越权剔除） |
| 5 | 数据迁移：自助认领接口 + admin映射兜底脚本 | ~1天 | ✅ 完成（`POST /workspace/claim-legacy-session` + `scripts/migrate_user_isolation.py`） |
| 6 | 账户合并小工具后端逻辑 | ~0.3天 | ✅ 完成（`merge_user_data`服务 + `POST /admin/users/merge`） |
| 7 | 文档同步 + 回归测试 | ~0.5天 | ✅ 完成（本节+§十一+部署文档同步，回归测试见下） |
| **合计** | | **~5.3天** | **全部完成** |

### 9.1 实施清单（新增/修改文件）

| 文件 | 改动内容 |
|------|---------|
| `API/main.py` | `/auth/me`；10个workspace/export路由所有权改造；`/workspace/claim-legacy-session`；`/admin/users/merge` |
| `API/sop_api.py` | 共享helper `_enforce_execution_ownership`/`_enforce_record_ownership`；19个execution_id端点+13个record_id端点所有权校验；7个入口session_id派生；`list_executions`/`list_task_history`强制过滤 |
| `API/utils.py` | `resolve_owned_session_id`、`enforce_path_ownership` |
| `API/auth_middleware.py` | `ADMIN_ONLY_PREFIXES`新增`/admin/`前缀 |
| `deepanalyze/analysis/task_SOP/executor.py` | `get_execution_status`/`get_execution_result`返回值补充`session_id`字段（开发中发现的既有bug，一并修复） |
| `deepanalyze/core/task_manager/user_migration_service.py` | 新增：`is_legacy_session_id`、`merge_user_data`（迁移/合并共用核心逻辑） |
| `scripts/migrate_user_isolation.py` | 新增：admin批量迁移CLI（扫描报表 + 映射执行 + 进度恢复 + 未映射归档） |
| `three-panel-interface.tsx` | session_id改为从`/auth/me`获取的用户名；新增`tabId` |
| `tests/test_user_management_phase1.py` | 24项单测（Phase1/3） |
| `tests/test_user_management_phase5_6.py` | 14项单测（Phase5/6） |

### 9.2 已知未覆盖项（诚实标注，非阻塞）

| 项目 | 说明 | 风险 |
|------|------|------|
| `GET /sop/statistics` | 全局聚合统计未按用户过滤（底层`get_statistics()`不支持session_id参数，需改DB层） | 低——仅暴露计数，无具体业务内容 |
| `GET /sop/cache/stats`、`POST /sop/cache/clear` | 系统级缓存管理，未做所有权/权限区分 | 低——非业务数据 |
| "用户自助认领前校验从未认领过其他session" | 简化为"仅允许认领旧格式随机ID"（`is_legacy_session_id`），未实现"每用户仅可认领一次"的状态跟踪 | 低——旧格式ID天然不会与其他真实用户名冲突 |

## 十、批次1 风险与回滚

| 风险 | 应对 |
|------|------|
| 用户自助认领误关联他人session | 认领前校验目标目录真实存在且当前用户从未认领过其他session；操作写审计日志 |
| 所有权校验遗漏某个路由 | Phase 3前置产出"受影响路由清单"，逐条改造+单测（伪造他人身份应403） |
| 迁移脚本中断 | DB优先+进度记录机制保证可从中断点恢复 |
| ~~SSE token被截获重放~~ | 已撤销，见§1.3 |

## 十一、批次1 验收标准

1. 单元测试：所有权校验（伪造他人身份应403，含`/sop/status/{execution_id}`轮询接口）、迁移脚本幂等性。
2. 手工测试：同账号更换终端登录能看到历史文件/任务；非admin无法越权访问任意execution_id的状态/workspace文件。
3. 迁移验证：抽样对比迁移前后文件数量与任务记录数一致。

---

# 第二部分：批次2 — 账号管理 Web UI（完整正式设计）

> **TD3 评估结论（2026-07-02，Phase 8 已完成）**：✅ **确定自建**，不引入 `fastapi-users`。理由：①该库核心围绕 JWT/Cookie 认证设计，与项目已锁定的"维持 Basic Auth"决策直接冲突；②强制 UUID 主键，与批次1已把`session_id`直接等同于`username`的身份派生设计冲突，引入需推倒重做批次1；③账户锁定/`valid_until`/一次性密码展示（TD4）等本项目核心需求该库均无内置支持，迁移后仍需自己实现，不节省工作量；④迁移成本（重写认证中间件+前端登录方式+批次1身份模型）远超自建路径的~5天估算。**以下设计即为最终路线**，不再是"假设"。

## 十二、批次2 权限矩阵（字段级 + 菜单级）

| 功能/字段 | 普通用户（自助） | 管理员 |
|-----------|:---:|:---:|
| 修改自己的密码 | ✅ | ✅ |
| 修改自己的显示名/昵称、部门备注 | ✅ | ✅ |
| 修改自己的`username`（登录名） | ❌ 不支持 | ❌ 同样不支持自助改名，需走账户重建+账户合并（见§七） |
| 查看「用户管理」菜单入口 | ❌ 不可见 | ✅ |
| 新增账户 | ❌ | ✅ |
| 修改任意用户角色（admin/user） | ❌ | ✅ |
| 设定/修改任意用户有效期`valid_until` | ❌ | ✅ |
| 启用/禁用（软删除）任意账户 | ❌ | ✅ |
| 重置任意用户密码 | ❌ | ✅ |
| 查看全部用户列表 | ❌ | ✅ |
| 查看自己/他人的任务历史 | 仅自己 | 全部（含"查看指定用户"过滤） |
| 查看自己/他人的workspace文件 | 仅自己 | 全部 |
| 账户合并（旧数据转移到新用户名下） | ❌ | ✅ |

> 前端菜单渲染依据`/auth/me`返回的`role`字段做条件渲染；后端每个admin接口均**独立**做`role=='admin'`校验（不可仅依赖前端隐藏菜单），避免"前端隐藏但接口未校验"导致的越权。

## 十三、批次2 数据模型：新增 `users` 表

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(64) UNIQUE NOT NULL,   -- 登录名，创建后不可变更，需符合^[a-zA-Z0-9_-]+$（TD6）
    display_name VARCHAR(64),               -- 显示名/昵称，用户可自助编辑，非唯一
    password_hash VARCHAR(128) NOT NULL,    -- bcrypt
    role VARCHAR(16) NOT NULL DEFAULT 'user',  -- admin | user，仅admin可编辑
    org VARCHAR(128),                        -- 部门备注，用户可自助编辑
    description TEXT,                        -- 备注，用户可自助编辑
    valid_until DATE,                        -- NULL = 永久有效
    enabled BOOLEAN NOT NULL DEFAULT 1,      -- 软禁用，替代物理删除
    must_change_password BOOLEAN NOT NULL DEFAULT 0,  -- TD4：新建账户强制首次登录改密标记
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(64)                   -- 审计：记录操作人
);
```

- 迁移脚本一次性读取`config/users.yaml`导入本表；导入后`users.yaml`仅作为灾备/离线场景兜底保留，正常运行时以数据库为准。
- 删除账户改为`enabled=0`软禁用（避免历史`task_records.session_id`外键悬空）。

## 十四、批次2 API设计

| 方法 | 路径 | 权限 | 说明 |
|------|------|:----:|------|
| GET | `/auth/me` | 已登录 | 补充返回`display_name/role/org/description/valid_until/must_change_password` |
| GET | `/auth/mode` | 无（认证白名单） | 返回`{"auth_enabled": true/false}`，供前端判断是否渲染登录/账户相关UI |
| PUT | `/auth/profile` | 已登录（自助） | Body仅接受`display_name/org/description`；后端显式忽略body中出现的`username/role/valid_until/enabled`字段 |
| POST | `/auth/change-password` | 已登录（自助） | Body: `old_password, new_password`；校验旧密码后bcrypt重新哈希 |
| GET | `/admin/users` | **admin** | 分页列出所有账户 |
| POST | `/admin/users` | **admin** | 创建账户：后端生成随机密码并一次性返回明文（TD4）+ `must_change_password=true`；`username`创建后不可变更 |
| PUT | `/admin/users/{username}` | **admin** | 编辑角色/org/description/valid_until/enabled（不支持改`username`） |
| POST | `/admin/users/{username}/reset-password` | **admin** | 重置任意用户密码：同样生成随机密码一次性返回明文 + 设置`must_change_password=true`（TD4） |
| DELETE | `/admin/users/{username}` | **admin** | 软删除（`enabled=0`），不物理删除 |
| POST | `/admin/users/merge` | **admin** | 账户合并（§七）：body传`{from_username, to_username}`，把旧账户名下数据批量转移到新账户名下 |

> **密码哈希已全面集成**：以上所有创建/改密/重置接口均在后端内部完成`bcrypt.hashpw()`哈希，接口只接受明文密码，管理员/用户不再需要接触`scripts/hash_password.py`命令行。该脚本仅保留用于批次2的一次性yaml导入迁移脚本内部调用，及极端灾备场景兜底。

## 十五、批次2 前端设计

### 15.0 入口位置（Pass 1 信息架构，评审补充，已与用户确认）

**现状核实**：三列式布局（`three-panel-interface.tsx`）没有全局顶部导航栏。中列Header（`Assistant` 标题 + `自动折叠`开关 + 主题切换🌙按钮，L3823-3876）**无条件渲染**，不随对话/SOP任务/历史等视图状态变化；右侧`flex`容器目前只有1个主题切换按钮，横向空间富余。相比之下，右列内容完全由`rightPanelMode`（`code`/`log`/`preview`三态）决定，顶部工具栏结构随视图变化，不适合承载全局性的身份入口。

**已确认决策**：**不新增一整行**，在中列Header现有的右侧`flex items-center gap-1`容器内，紧邻主题切换🌙按钮处新增一个头像/身份菜单按钮（左右顺序不敏感，实现时任选）。

```
┌──────────────────────────────────────────────────┬─────────────────┐
│ 中列Header：Assistant 自动折叠[⚪] ... [👤▾][🌙]   │  右列(Code/Log/  │
│                          ↑新增头像菜单，紧邻主题按钮 │   Preview 三态) │
├──────────────────────────────────────────────────┼─────────────────┤
│              （中列主体内容...）                    │  （右列主体内容） │
└──────────────────────────────────────────────────┴─────────────────┘
```

点击头像展开下拉菜单：
```
┌─────────────────────┐
│ 账户设置              │ ← 所有角色（改密码、编辑个人信息）
│ 用户管理              │ ← 仅admin，跳转独立页面 /user-manager
│ LLM渠道管理           │ ← 仅admin，跳转 /llm-manager（复用同一入口，解决现有该页面在主界面内无导航链接的遗留问题）
├─────────────────────┤
│ 退出登录              │
└─────────────────────┘
```

**「用户管理」不嵌入三列工作区**，而是像`/llm-manager`一样做成独立页面（`/user-manager`），与现有产品架构一致（重型管理功能=独立页面，工作区只放分析任务相关内容）。

**单用户模式**：`/auth/mode`返回`auth_enabled=false`时，`[👤▾]`头像菜单按钮不渲染，中列Header其余部分（Assistant标题/自动折叠开关/主题切换🌙）不受影响，正常显示。

### 15.1 菜单差异化（对应§十二权限矩阵）

| 角色 | 可见菜单 | 菜单内可操作项 |
|------|---------|---------------|
| 普通用户 | 「账户设置」（个人） | 修改密码（首屏/优先展示）；编辑显示名/部门备注/描述；username只读展示 |
| 管理员 | 「账户设置」（同上）+ 「用户管理」（新增管理页面，参考`LLM Manager`管理页风格） | 「用户管理」页：新建用户、编辑角色/有效期/启用禁用、重置密码、账户合并、查看全部账户列表 |

`/auth/mode`探测：前端启动时调用一次，`auth_enabled=false`时完全不渲染登录框、账户设置、用户管理等全部相关UI（单用户模式下不适用，见§2.4）。

### 15.2 「账户设置」弹窗（所有角色通用，仅编辑自己）
- **改密码分区排在最前**（高频操作优先，Design评审发现）：旧密码 + 新密码 + 确认新密码 → `POST /auth/change-password`
- 个人信息编辑区（次要位置）：显示名、部门备注、描述 → `PUT /auth/profile`
- username只读灰色展示，注明"登录名创建后不可修改"

**改密码成功后的交互**（Design评审critical发现，已定案）：前端立即用新密码更新本地`localStorage`凭证（`saveAuth`），无感衔接，**不强制重新登录**；Toast提示"密码已更新"。

### 15.3 Admin「用户管理」页面
- 用户列表表格：用户名/显示名/角色/部门/**有效期（临期≤7天黄色高亮，已过期红色高亮）**/状态
- 新建用户弹窗：用户名（一次性输入，实时校验`^[a-zA-Z0-9_-]+$`）、角色下拉、有效期日期选择、启用/禁用开关。**不要求管理员手输密码**——保存后系统自动生成随机密码
- 编辑用户弹窗：角色/部门/有效期/启用禁用，username只读
- 「重置密码」按钮 → 调用reset-password接口
- 「合并账户」按钮 → 选择旧账户+新账户，调用merge接口

**新建用户/重置密码成功后的交互**（TD4，Design评审critical发现，已定案）：
```
管理员点保存 → 后端生成随机密码 → 成功弹窗一次性明文展示：
"用户已创建，初始密码：xxxxxx（此密码不会再次显示，请通过安全渠道告知该用户）"
                    ↓
新用户首次登录成功 → 前端检测must_change_password=true → 强制弹出改密弹窗（无法取消/关闭）
                    ↓
改密成功 → 清除must_change_password标记 → 自动同步本地凭证 → 进入主界面
```

### 15.4 交互状态与错误处理规范（Design评审发现，统一执行）
| 场景 | 处理方式 |
|------|---------|
| 用户名重复 | `POST /admin/users`返回409，前端在用户名输入框下方内联展示"该用户名已存在" |
| 各表单保存中/提交中 | 复用现有`ModelConfigModal.tsx`的loading/saving双态（按钮disabled+Loader2），不新建一套视觉规范 |
| 保存成功 | Toast提示 + 弹窗自动关闭 + 列表原地刷新（不整页reload） |
| 403越权响应 | 前端全局拦截统一处理，不逐个组件各自处理 |
| 密码强度 | 最小长度8位的简单校验，前端实时提示，不引入复杂强度评分器 |

### 15.5 设计系统对齐结论（Design Review Pass 5）

**核查结果**：项目内不存在 `DESIGN.md`，无正式设计系统文档。

**结论（机械决策，M16）**：本次不额外触发 `/design-consultation` 去补建一份全局设计系统——本模块只是内部管理工具的一个功能点，不是产品级UI改版，为一个功能单独建一份DESIGN.md投入产出不成比例。转而遵循"复用现有UI组件库风格"这一通用原则（已在§15.4体现：统一复用`ModelConfigModal.tsx`的loading/saving双态和Toast风格，表格风格参考`TaskHistoryCompact.tsx`的Badge色块规范）。若后续项目整体决定建立DESIGN.md，本模块届时按新规范回溯校准即可。

### 15.6 响应式与无障碍规范（Design Review Pass 6，评审时完全缺失，本次补齐）

**目标平台判断**：内网团队管理工具，桌面浏览器为主要使用场景，但需保证平板/窄屏下不崩溃、可基本操作（而非做移动端深度优化）。

**响应式规范**：

| 组件 | 桌面（≥1024px） | 平板（768-1023px） | 手机（<768px） |
|------|------|------|------|
| Admin用户管理页表格 | 完整表格，全部列可见 | 表格容器 `overflow-x: auto` 横向滚动，列不折叠 | 表格转为卡片列表：每个用户一张卡片，核心字段（用户名/角色/状态）常显，次要字段（部门/有效期）点击展开 |
| 账户设置/新建用户/编辑用户弹窗 | 居中弹窗，最大宽度480px | 同桌面，居中弹窗 | 全屏 bottom-sheet（占满宽度，从底部滑出），避免小屏幕表单被挤压变形 |
| 一次性密码展示弹窗 | 居中弹窗 | 同桌面 | 全屏展示，密码文本足够大（≥18px）方便截图 |

**无障碍（Accessibility）规范**：

| 维度 | 具体要求 |
|------|---------|
| 键盘导航 | 所有表单输入框/按钮遵循自然Tab顺序；弹窗打开时焦点自动移到第一个输入框；`Esc`键关闭弹窗——**唯一例外**：`must_change_password`强制改密弹窗禁止`Esc`关闭（业务上要求必须改密才能继续） |
| ARIA标注 | 表格加`role="table"`+对应`aria-label`；弹窗加`role="dialog"` `aria-modal="true"` `aria-labelledby`指向弹窗标题 |
| 触摸目标尺寸 | 所有可点击元素（含表格行内"编辑"/"重置密码"/"禁用"图标按钮）最小44×44px点击热区，图标类操作按钮需加padding达标 |
| 颜色对比度与色盲友好 | `valid_until`临期/过期高亮标签的文字与背景对比度需满足WCAG AA标准（≥4.5:1）；**不能仅靠颜色区分状态**，需搭配文字（"7天后过期"/"已过期"）或图标，避免色盲用户无法识别 |
| 表单错误提示 | 不能仅用红色边框标识错误，需搭配文字说明（如"该用户名已存在"），保证屏幕阅读器可读出错误原因 |

## 十六、批次2 安全考虑

| 检查项 | 措施 |
|--------|------|
| 密码传输 | **硬性前置条件**：启用自助改密/管理员改密/重置密码这几个接口前，必须确认部署环境已启用HTTPS（或可信内网+二层防护），否则不允许上线这几个接口。写入`intranet_deployment_guide.md`部署检查清单 |
| 密码存储 | bcrypt哈希，新增API不接受前端直传哈希，仅接受明文密码由后端加盐哈希 |
| 一次性密码展示 | 仅在创建/重置成功的响应中一次性返回明文，不做任何持久化存储或日志记录明文密码 |
| 改密暴力破解防护（M19） | `/auth/change-password`旧密码校验失败复用`SimpleAuth`现有账户锁定机制（按username计数），超`max_login_failures`次同样锁定该账户 |
| admin账户恢复（M18） | 不做UI内"忘记密码"流程；极端场景（admin账户锁死/密码丢失）由ops直接操作数据库恢复，写入运维手册 |
| 账户重名冲突 | username已存在且`enabled=0`时返回409+指引，不允许物理层面IntegrityError泄露内部结构 |
| 审计 | `users`表`created_by`字段；账户创建/禁用/改密/合并操作写入`logs/`，记录操作人+时间+目标账户 |

## 十七、批次2 Phase划分与工作量估算（紧随批次1发布）

| Phase | 内容 | 工作量 | 状态 |
|:-----:|------|:------:|:---:|
| 8 | Build vs Buy评估：`fastapi-users`可行性调研 + 结论 | ~0.5天 | ✅ 已完成（2026-07-02，结论：自建） |
| 9 | 数据模型：`users`表设计 + yaml导入脚本 | ~0.5天 | ✅ 已完成（2026-07-02）：`User`模型+`UserService`（CRUD/密码校验/软删除/yaml导入）+`scripts/migrate_users_yaml_to_db.py`，单测28项全通过 |
| 10 | 账号管理API：`/auth/me`补充字段、`/auth/profile`、`/auth/change-password`、`/admin/users`全套CRUD、reset-password、merge | ~1.5天 | ✅ 已完成（2026-07-02）：`API/user_admin_api.py`新增8个端点+`SimpleAuth`数据源动态切换（DB优先/yaml兜底）+`/auth/me`补充字段，单测24项全通过 |
| 11 | 前端：账户设置弹窗、Admin用户管理页面、`/auth/mode`探测、菜单差异化、交互状态规范 | ~2天 | ✅ 已完成（2026-07-02）：新增`hooks/use-auth-info.ts`（`/auth/mode`+`/auth/me`统一探测）、`AccountSettingsDialog.tsx`（改密+个人信息，含强制改密模式）、`UserManagerPage.tsx`+`/user-manager`路由（用户列表/新建/编辑/重置密码/合并账户/一次性密码展示/有效期临期高亮）；`three-panel-interface.tsx`中列Header新增头像身份菜单（账户设置/用户管理/LLM渠道管理/退出登录，按`role`差异化） |
| 12 | 回归测试 + 文档同步（`intranet_deployment_guide.md`/`user_manual.md`） | ~0.5天 | ✅ 已完成（2026-07-02）：后端全量回归90项全通过无新增失败；`intranet_deployment_guide.md`§3.3、`user_manual.md`§3.1/§3.2 已改为以 Web UI 为主路径描述，`users.yaml`降级为迁移前/灾备兜底说明；同步修正`migrate_users_yaml_to_db.py`docstring中Phase10已完成后过时的表述 |
| **合计** | | **~5天** | ✅ **批次2全部12个Phase已完成（2026-07-02）** |

## 十八、批次2 验收标准

1. 单元测试：权限矩阵校验（普通用户调用admin接口应403）、用户名重名冲突处理、密码强度校验。
2. 手工测试：管理员通过UI完成新建/编辑/禁用/重置密码全流程，无需接触命令行；新用户首次登录被强制改密；普通用户自助改密后无需重新登录。
3. 安全测试：确认部署环境HTTPS前置条件已在文档中明确。

---

## 十九、6个月后复查机制

约定批次2上线后6个月复查：
- 批次1的身份隔离/越权修复是否稳定运行、有无绕过事件
- 批次2的账号管理Web UI实际使用频率（是否真的替代了手工编辑yaml），据此判断是否需要进一步优化

---

## 二十、批次2 补充加固：首个账户零配置自动创建（2026-07-02）

### 背景

批次2上线后进行部署链路复核时发现：`ENABLE_AUTH=true`是`docker-compose.yml`/`Dockerfile`的**既有默认值**（即"新部署默认多用户"），但首个admin账户创建此前一直依赖人工步骤（编辑`users.yaml`或跑`migrate_users_yaml_to_db.py`）。复核过程中发现并修复了三个串联的问题：

| # | 问题 | 影响 | 修复 |
|---|------|------|------|
| 1 | **fail-open**：`ENABLE_AUTH=true`但零账户时，`SimpleAuth()`抛`FileNotFoundError`，`API/main.py`捕获后仅打日志、不挂载鉴权中间件，服务**静默降级为无鉴权**对外运行 | 高——运维忘记bootstrap不会感知到，系统实际处于不设防状态 | 在构造`SimpleAuth()`前新增`_ensure_bootstrap_admin_if_empty()`：检测到真正的零账户状态时自动创建随机密码admin账户（`must_change_password=true`），从根上消除该状态的出现 |
| 2 | **Docker bind mount 陷阱**：`docker-compose.yml`原挂载单文件`../config/users.yaml:/app/config/users.yaml`，宿主机文件不存在时 Docker 会创建同名空目录兜底，导致`open()`抛`IsADirectoryError`而非约定的`FileNotFoundError`，绕过上述修复的异常类型判断 | 高——Docker部署场景下问题1的修复会被这个新问题重新绕过 | ① `auth_middleware.py::_find_config_path()`改用`is_file()`而非`exists()`判断，空目录不再被误判为"配置已存在"；② `docker-compose.yml`改为挂载整个`../config:/app/config`目录，从根上避免"挂载不存在的单文件"这一Docker行为触发 |
| 3 | **`deploy_linux.sh`遗留占位哈希**：脚本无论运维选"现在编辑"还是"暂不编辑"，都无条件把`users.yaml.example`（含`PLACEHOLDER`占位哈希）复制为`users.yaml`。选择"暂不编辑"时，这份yaml会被自动兜底逻辑误判为"已配置账户"从而跳过创建，而占位哈希本身无法通过任何密码验证——**最终系统没有任何账户能登录，永久锁死** | 严重——比问题1（无鉴权）更差，是完全不可用 | 改为交互二选一：仅当运维明确选择"手动配置"才创建并打开编辑器；选择默认项（自动生成）时完全不创建该文件，交给问题1的自动兜底逻辑处理 |

### 新增/修改文件

| 文件 | 改动 |
|------|------|
| `API/main.py` | 新增`_generate_bootstrap_password()`、`_ensure_bootstrap_admin_if_empty()`、`_print_bootstrap_admin_banner()`；在`ENABLE_AUTH=true`分支挂载`SimpleAuth`前调用 |
| `API/auth_middleware.py` | `_find_config_path()`的`p.exists()`→`p.is_file()` |
| `docker/docker-compose.yml` | 用户配置挂载改为整目录；顶部注释更新首次使用说明；`ENABLE_AUTH`注释订正（原写"默认关闭"与实际默认值`true`矛盾） |
| `scripts/deploy_linux.sh` | `[3]`步骤改为交互二选一（自动生成 / 手动配置），消除占位哈希锁死隐患；部署完成提示补充"查看一次性密码"引导 |
| `scripts/service.sh` | 修复`start`/`start-noauth`两处"未显式export ENABLE_AUTH导致compose级默认值`true`覆盖预期值"的逻辑缺口；帮助文本同步 |
| `scripts/init_admin.py`（本次会话新建） | 手动/进阶场景仍可用：自定义初始用户名、应急重置密码（`--reset-if-exists`）、CI固定密码场景；docstring已注明与自动兜底的关系 |
| `conftest.py` | 新增`os.environ["ENABLE_AUTH"]="false"`强制覆盖：测试会话不应受开发者本机真实`.env`里`ENABLE_AUTH`取值影响（此前因手动把本机`.env`改为`true`用于人工测试，导致31个假定默认无鉴权的既有测试意外收到401，被此修复消除） |

### 验证

- 隔离临时数据库（`TASK_MANAGER_DB_URL`指向临时文件）验证`_ensure_bootstrap_admin_if_empty()`：首次调用创建账户并返回明文密码，二次调用因已有账户返回`None`（幂等，不覆盖）
- 后端全量回归（Phase1/5_6/9/10共90项）：修复`auth_middleware.py`与`conftest.py`后全部通过，无新增失败
- `docker-compose.yml`用`yaml.safe_load`校验语法合法，`volumes`列表确认已改为目录挂载

### 已知局限（未覆盖，留待后续）

- 未在真实Docker环境里实测"bind mount空目录→IsADirectoryError"这条路径本身（本地开发环境是Windows，未安装Docker），修复基于对Docker bind mount行为的既有认知与`is_file()`语义的代码级验证，建议在Linux CVM实际部署一次全新环境验证
- 自动生成的一次性密码只打印到启动日志，未提供"写入本地文件供无终端访问场景读取"的第二通道；若部署环境的容器日志被立即清空/不可查看，会导致取不到初始密码（届时可用`scripts/init_admin.py --reset-if-exists`应急重置）

### 二十一、批次2 GUI 首测发现问题（2026-07-02，用户实测反馈）

用户在真实浏览器里首次走"登录→改密→保存个人信息"流程时报告两个问题，追查后发现并修复：

| # | 问题现象 | 根因 | 修复 |
|---|---|---|---|
| 1 | 点击"确认修改/保存"后弹出**浏览器原生**账号密码框，且卡死无法交互 | 后端401响应统一带`WWW-Authenticate: Basic`头，浏览器网络层在JS处理响应之前就抢先弹出原生认证框，打断了前端自己实现的`authFetch`→`LoginDialog`重试流程（部分内嵌WebView环境下该原生框还会卡死） | `auth_middleware.py::BasicAuthMiddleware.dispatch`：仅对真实页面导航（`Accept: text/html`）保留`WWW-Authenticate`头，AJAX/fetch请求（前端所有API调用）不再带该头，交由自定义`LoginDialog`处理 |
| 2 | （排查过程中发现，非用户直接报告）测试锁定态污染真实环境 | `tests/test_auth_middleware.py`里`TestAccountLockout`故意连续失败登录触发锁定，但`_get_state_path()`硬编码指向真实项目`config/login_state.json`，未做隔离——不仅导致同一进程内后续测试意外收到429（已复现），本机反复跑测试期间也可能把真实"admin"账户凭空锁定 | `app_with_auth`测试fixture新增`monkeypatch.setattr(auth_mod, "_get_state_path", ...)`，与已有的`_find_config_path`隔离方式保持一致，锁定状态落在`tmp_path` |

同时补充两项UI体验优化：
- `AccountSettingsDialog.tsx`三个密码输入框新增"小眼睛"明文/密文切换（`Eye`/`EyeOff`图标，默认隐藏）
- 确认"登录名创建后不可修改"为既定设计（包括admin账户本身），不是bug：用户名是账户的持久化标识，允许改名会牵扯所有历史数据归属，产品设计上改名场景走"合并账户"功能而非直接改用户名

**验证**：`tests/test_auth_middleware.py`（含2个更新+1个隔离修复）25项全通过；追加`test_no_auth_header_html_navigation_has_www_authenticate`锁定"真实页面导航仍保留原生认证"的预期行为，避免后续误改。全量回归（含Phase1/5_6/9/10）持续保持全绿。

**已知局限**：上述WWW-Authenticate修复未能在真实浏览器里复测（无法直接操作用户的浏览器），已重启本机开发后端加载修复，待用户下次操作反馈确认。

### 二十二、LLM Manager 前端从未适配多用户模式（2026-07-02，用户实测反馈）

修复§二十一后，用户反馈"LLM渠道管理"跳转地址本身有误（`three-panel-interface.tsx`硬编码`window.location.href="/llm-manager"`，开发模式下3000端口没有这个路由，应按端口区分跳到3001或`${origin}/llm-manager`）；修正跳转地址后，暴露出一个更根本的问题：

**根因**：`llm_manager_integrated/frontend/scripts/main.js`等原生JS前端代码里的所有`fetch()`调用，**从未实现过任何Basic Auth凭证注入逻辑**——这套前端是在批次1/2开发之前就已存在的遗留代码，从未适配过`ENABLE_AUTH=true`场景。多用户模式下，这些请求全部收到401（且不带`Authorization`头，也没有页面级重试机制），表现为渠道列表卡在"加载中"、各Tab点击无响应——与最初排查"main.js 404"时的症状完全一样，但这次是认证问题而非路由缺失问题（两次症状撞脸纯属巧合，均指向同一个用户体验现象）。

**修复**：
1. `API/auth_middleware.py`的`AUTH_WHITELIST`新增`/llm-manager/scripts`、`/llm-manager/shared`两个前缀——`<script src>`/`<link>`标签加载静态资源不会带认证头，必须放行，否则连"负责登录的脚本"本身都加载不了（鸡生蛋问题）
2. 新建`llm_manager_integrated/frontend/shared/js/auth.js`：vanilla JS实现的全局`fetch`拦截器，从`localStorage`（key复用`creditwise_auth`，与`demo/chat`一致）注入凭证，401时弹出自定义登录框（非浏览器原生，避免§二十一同样的卡死问题）重试一次。必须在`index.html`里排在其他脚本**之前**加载
3. `index.html`新增该脚本的`<script>`标签

**架构影响**：生产同源部署（`demo/chat`和LLM Manager同源，都在8200）下，两个前端共享`creditwise_auth`这份localStorage凭证，用户在主界面登录后点开「LLM渠道管理」**不需要**再登录一次；开发模式下3000/3001是不同origin，localStorage天然隔离，需要在LLM Manager里单独登录一次——这是可接受的开发环境体验差异，不是bug。

**顺带发现的独立问题（生产环境，未修复，记录留待后续）**：`llm_manager_integrated/api/app.py::create_app`的生产模式SPA路由`serve_spa`，对于非`api/`、非`static/`前缀的所有路径（包括`scripts/main.js`、`shared/js/*.js`）统一返回**index.html的HTML内容**而不是真实的静态文件本身——即使Dockerfile构建时已经把`scripts/`、`shared/`目录复制到了`static_dir`同级位置，磁盘上文件是真实存在的，只是`serve_spa`没有检查这些子路径下是否有对应真实文件、直接fallback到HTML响应。这意味着**生产部署同样会复现"main.js加载失败→配置页面卡死"**，只是本次修复的两个问题都是开发模式路径，未触发这个生产模式的路由bug。因本机无Docker环境，未做实际验证，建议下次生产部署前专项修复：让`serve_spa`在fallback到index.html之前，先检查`static_dir / full_path`是否为真实存在的文件，存在则直接`FileResponse`返回。

**验证**：`curl`直接测试（无认证）`/llm-manager/scripts/main.js`、`/llm-manager/shared/js/auth.js`经3001代理均返回200（白名单生效）；`/llm-manager/api/manage/channels`无认证返回401（未被误放行，鉴权仍然生效）。用户已在真实浏览器（`localhost:3001`开发模式）实测确认：自定义登录框正常弹出（非原生弹窗）、输入`admin`凭证后弹窗消失、渠道列表与各Tab恢复正常——修复生效，问题闭环。

### 二十三、并发401登录去重缺失导致Files/TaskType永久卡在加载中（2026-07-02，用户实测反馈）

修复§二十一/§二十二后，用户报告新建的普通用户`fjzheng`首次登录改密、再次登录成功后，主界面Files文件树和TaskType任务列表区域一直显示"Loading..."/转圈，永不结束；追查后发现该问题**与账户类型无关**——用同一浏览器复测admin账户后同样复现，确认是通用并发缺陷而非该用户账户状态异常（已核实`fjzheng`在数据库中`enabled/must_change_password/valid_until`等字段均正常，`login_state.json`锁定计数为0）。

**根因**：页面加载时`loadWorkspaceFiles`/`loadWorkspaceTree`/`TaskSelector`的`getAvailableTasks`等多个接口几乎同时通过`authFetch`发起请求。一旦当前凭证失效（如刚改完密码、浏览器缓存的旧凭证过期），这些请求会**同时**收到401，各自独立调用`promptLogin()`→`LoginDialog.tsx`注册的回调。但`LoginDialog.tsx`内部只用一个共享的`resolveRef`存放"登录成功后要通知谁"，每次新调用都会**覆盖**上一次的`resolveRef`——最终只有最后一次调用会在用户提交登录表单后收到`resolve`，其余更早发起的`authFetch`调用永远等不到结果，对应的`await`永久挂起。这解释了为什么现象是"部分区域永久Loading"而不是"抛错重试"：请求本身没有失败，只是卡在等待一个永远不会到来的登录结果上，且这个挂起状态在用户随后成功登录之后也不会自愈（那些"掉队"的Promise早已错过了唯一一次`resolve`机会）。

**修复**：`demo/chat/lib/config.ts`的`promptLogin()`新增模块级`_pendingLoginPromise`去重——并发调用共享同一个pending Promise，只触发一次`_loginCallback()`（即只弹一次`LoginDialog`），全部等待者拿到同一个登录结果后各自继续重试自己的原始请求。这是纯前端修复，Next.js dev server热更新即可生效，无需重启后端。

同时对`llm_manager_integrated/frontend/shared/js/auth.js`应用了同样的修复（该文件的`_pendingResolve`是完全相同的单槛位设计缺陷，§二十二上线时因场景恰好是单一请求触发未被暴露，此次一并加固，避免同类并发场景下复现）。

**已知局限**：`LoginDialog.tsx`内部`resolveRef`本身的单槛位设计未改动——修复是在上游`promptLogin()`做去重，从根源保证不会有第二次并发调用穿透到`LoginDialog`，而不是让`resolveRef`自身支持多路等待者。这是更小侵入性的修复方式，但意味着如果未来有其他调用路径绕过`promptLogin()`直接调用`registerLoginCallback`注册的回调，仍可能触发同样的覆盖问题——目前代码库中`_loginCallback`只被`promptLogin()`这一处调用，风险可控。

---

### 二十四、跨域裸fetch调用未注入认证凭证，导致历史记录等模块加载失败（2026-07-02，用户实测反馈）

修复§二十三后，Files/TaskType恢复正常，但用户报告历史记录列表显示"加载失败"，并追问单用户模式下明明有记录，多用户模式下admin账户是否也看不到——排查后确认**这不是数据问题**（直接调用`TaskHistoryService.list_records(session_id="admin"/"fjzheng")`验证均正常返回，无异常，只是这两个新账户目前确实还没有在其名下执行过任务，`total=0`符合预期），是纯前端的认证注入缺口。

**根因**：`demo/chat/components/sop/TaskHistoryCompact.tsx`等十余处调用点（历史记录列表/删除/批量删除、报告导出、文档预检、workspace文件预检等）用的是**裸`fetch(getApiUrl(...))`**而非`authFetch(...)`。`lib/config.ts`里为裸fetch兜底的全局拦截器，此前判断"是否需要注入凭证"的依据是`isSameOrigin`（相对路径或与当前页面同源）——但`getApiUrl()`在开发模式（Next.js 3000 + 后端8200）下返回的是**跨域**绝对地址（`getBaseUrl()`），不满足`isSameOrigin`，于是这些裸fetch请求完全不带认证头直接发出，收到401后各调用点自己的`if (!response.ok) throw ...`逻辑就直接判定"加载失败"，没有走登录重试。生产同源部署（3000/8200合一）下天然满足同源判断，不会触发；单用户模式下无需认证，也不会触发——这解释了为什么这个缺口这么久没被发现。

**修复**：不逐个改造十余处调用点，而是从根上加固全局拦截器（`lib/config.ts`）：
1. "信任的后端"判定从`isSameOrigin`扩大为`isTrustedBackend`——相对路径 / 与当前页面同源 / **与`getBaseUrl()`同源**（即`getApiUrl()`实际会请求到的地址，无论是否与当前页面同源）
2. 给这个全局拦截器补上与`authFetch`一致的401重试能力：命中信任后端且收到401时，清除失效凭证→弹登录框（复用§二十三刚修复的并发去重`promptLogin()`）→用新凭证重试一次；用户取消则原样返回401
3. 为避免和`authFetch`自身的401重试逻辑重复弹两次登录框，拦截器对"请求已自带`Authorization`头"（即`authFetch`发出的、且本地已有缓存凭证的调用）的情况不做二次介入，交还给`authFetch`自己处理

这样修复后，所有裸`fetch(getApiUrl(...))`调用点（无论今后新增多少）都能自动获得凭证注入+401登录重试能力，无需每个调用点都记得改用`authFetch`。

**已知局限**：极端边界场景下（首次打开页面、`localStorage`里还完全没有任何缓存凭证、且用户在第一次弹窗时点了取消）——`authFetch`调用会先经过拦截器的401重试尝试一次（因为此时请求还没有`Authorization`头），若用户取消导致仍是401，`authFetch`自身的401判断会再触发一次登录弹窗，即会连续弹两次登录框。这是可接受的极小概率边界体验瑕疵（只在"从未登录过 + 主动取消"这一组合条件下出现一次），不影响本次要修复的核心问题，暂不做进一步处理。

### 二十五、多用户数据隔离功能覆盖面梳理（2026-07-02，用户实测追问）

用户在实测中发现：admin登录多用户模式后，能在「历史记录」列表里看到单用户模式遗留的2条旧记录，但Files面板却看不到同期上传的旧文档，进而追问"数据隔离功能只体现在Files区域吗？"。梳理§五已有设计并结合代码复核，确认隔离机制覆盖面比Files更广，但存在一处需要明确记录的**实现不一致**。

#### 隔离覆盖面全貌

| 功能模块 | 端点 | 非admin | admin |
|---|---|---|---|
| 工作区文件/目录（浏览/上传/删除/移动/下载） | `/workspace/*` | `resolve_owned_session_id`强制派生为自己用户名，忽略客户端传参 | 豁免，**但按客户端传参**（`API/utils.py::resolve_owned_session_id`admin分支：`return session_id`原样返回） |
| 任务执行状态/暂停/停止/恢复/结果 | `/sop/status`等19个execution_id端点 | `_enforce_execution_ownership`：非自己名下的execution_id → 403 | 豁免 |
| 单条历史记录详情/结果/删除 | 13个record_id端点 | `_enforce_record_ownership`：非自己名下的record_id → 403 | 豁免 |
| 历史记录**列表** | `GET /sop/history` | 强制`WHERE session_id=自己` | 豁免**且默认不加任何过滤**——查全部用户的记录（§五原文：`TaskHistoryService.list_records()` 增加强制参数 `current_user`：非admin时无条件加 `WHERE session_id = current_user`；**admin默认查全部**） |

#### 已识别的不一致（非bug，是设计遗留的功能空缺）

除历史记录列表外，其余所有端点对admin的"豁免"都停留在**后端权限层面允许**（可以传参访问任意用户数据），但**前端从未提供对应UI**——`three-panel-interface.tsx`里Files/Tree面板始终只会用"当前登录用户名"作为`session_id`发起请求，没有"管理员按用户名/session_id浏览指定工作区"的入口。因此：

- **历史记录列表**：因为该端点是唯一"默认不过滤、直接查全部"的实现，admin不需要任何额外UI操作就能看到所有session（含单用户模式遗留session）的记录——这是该端点独有的实现方式，其他端点均非如此。
- **Files/Tree面板**：始终受限于前端传递的`session_id`（=登录用户名），旧的单用户模式随机session目录下的文件**未被删除，仍在磁盘`workspace/{旧随机ID}/`**，但当前没有任何UI能让admin主动查看它——即便后端权限层面是允许的。

这导致用户体感上的困惑："同样是admin账户，为什么历史记录能看到旧数据，文件却看不到"——根源是两个端点对"admin默认要不要看别人的东西"采取了不同的默认行为（一个默认查全部不设防，其余默认收窄到自己、需要显式传参才能看别人），而配套支持"显式传参看别人"的UI从未补上。

#### 后续处理选项（已与用户讨论，暂未决定/实施）

1. 补一个"管理员按用户名/session_id浏览指定工作区"的管理入口，让admin能主动查看任意用户（含旧遗留session）的文件，与历史记录列表的"全量可见"能力对齐
2. 使用已有的`/workspace/claim-legacy-session`（用户自助认领）或`scripts/migrate_user_isolation.py`（管理员批量迁移）把旧随机session的数据正式迁移/合并到某个真实账户名下，使其自然出现在该账户的正常视图里，不需要额外UI

两个选项互不排斥，可按需选择或都不做（当前旧数据本身没有丢失风险，只是"看不看得到"的UI能力空缺）。

---

### 二十六、管理员浏览指定工作区（只读）功能实现（2026-07-02）

针对§二十五发现的"admin后端权限已允许查看任意session，但前端无发现/切换入口"这一空缺，实现了最小风险版本：**只读浏览**，不支持在浏览他人工作区时上传/删除/移动。

**后端（新增，无需改动既有鉴权逻辑）**：
- `GET /admin/workspace/sessions`（`API/main.py`）：admin专属（复用中间件已有的`ADMIN_ONLY_PREFIXES`对`/admin/`前缀的拦截，无需新增校验代码），扫描`workspace/`目录下所有子目录，返回`session_id`、`is_registered_user`（是否对应数据库中的真实账户，用于前端区分正常账户与遗留旧随机session）、`file_count`（递归计数，设5000上限防止超大目录拖慢接口）、`last_modified`。
- `/workspace/files`、`/workspace/tree`等既有端点**未做任何改动**——`resolve_owned_session_id`对admin角色本就"按客户端传参"放行，本次只是让前端能够利用这个已有能力。

**前端（`demo/chat/components/three-panel-interface.tsx`）**：
- 新增`adminViewSessionId`（默认`null`）+ `workspaceSessionId = adminViewSessionId || sessionId`：Files/Tree面板的读取从`sessionId`改为`workspaceSessionId`，任务执行/聊天等其他所有功能继续使用`sessionId`（管理员自己的真实身份），**互不影响**——浏览他人工作区不会影响admin自己发起新任务时的数据归属。
- Files面板标题栏新增仅admin可见的`<select>`下拉（"我的工作区" + 拉取自`/admin/workspace/sessions`的列表，标注"（旧会话）"和文件数），切换后触发`workspaceSessionId`变化 → 自动重新加载Files/Tree。
- **只读保护**（`isBrowsingOtherWorkspace = adminViewSessionId不为null且不等于sessionId`）：
  - `deleteFile`/`deleteDir`/`moveToDir`/`uploadToDir`四个写操作函数入口处统一拦截，浏览他人工作区时直接toast提示并返回，不发起请求（即使有遗漏的按钮未隐藏，最坏情况也只是"点了没反应+提示"，不会真正执行到破坏性请求）
  - 拖拽上传区、"全选"/"批量删除"按钮在浏览他人工作区时直接隐藏
  - 顶部新增橙色提示条"正在浏览「X」的工作区（管理员视角，只读）" + "返回我的工作区"按钮

**已知局限**：
- 文件树右键菜单里的删除/移动菜单项本身未做隐藏（未逐一排查Row组件的context menu渲染条件），依赖上述函数级guard兜底拦截，体验上"按钮还在但点了没用"，非最优但安全
- 未做真实浏览器端到端验证（本次改动后台通过curl确认路由已注册且鉴权正常返回401，前端逻辑基于代码审查，未在浏览器中实际点击验证下拉切换效果），需要用户实测确认

### 二十七、普通用户验收发现的3个问题（2026-07-02，用户实测反馈）

用户完成"普通用户视角"4项验证后，反馈3个问题，逐一定位修复：

#### 1. 普通用户看不到admin配置的模型渠道（"无可用配置"）—— 权限粒度错误，已修复

**根因**：`demo/chat/components/ModelSelector.tsx`（聊天界面底部的模型选择下拉框）请求`GET /llm-manager/api/manage/channels/active-configs`，该接口后端注释明确写着"获取所有激活渠道的配置（**用于三列式前端选择**）"——即设计上本就该让所有登录用户可用，而非管理专属。但因为它挂在`/llm-manager/api/manage/`路由前缀下，被`API/auth_middleware.py`的`ADMIN_ONLY_PREFIXES`整体按前缀拦截成"仅admin可访问"，非admin请求直接403，前端表现为"无可用配置"（管理员本人不受影响，因为管理员当然满足admin校验）。

**修复**：`auth_middleware.py`新增`ADMIN_PREFIX_EXCEPTIONS`精确路径例外表，`_is_admin_route()`先检查例外表再匹配前缀，把`/llm-manager/api/manage/channels/active-configs`从admin-only中摘出来（该接口仍需要登录，只是不再要求admin角色）；前缀下其余真正的管理操作（创建/编辑/删除渠道等）不受影响，仍然admin-only。`tests/test_auth_middleware.py`25项回归全通过；curl验证：无认证访问该接口仍返回401（未被误放行为完全公开），符合"仍需登录，只是不要求admin角色"的预期。

#### 2. 刷新页面后，头像按钮/TaskType卡片要等几秒才出现 —— 部分修复（消除一处真实冗余请求）

用户观察：三列式界面里纯静态的按钮（背景切换等）刷新后立即可见，而依赖网络请求的头像按钮（`useAuthInfo()`探测`/auth/mode`+`/auth/me`）和TaskType任务卡片（`/sop/tasks`）刷新后有明显延迟——这符合"依赖网络请求的UI必然慢于纯静态UI"的预期，但排查发现一处可优化的真实冗余：

- **发现的冗余**：`three-panel-interface.tsx`组件内部，早前批次1为了给`sessionId`做用户名覆盖，独立发起了一次`/auth/me`请求；而同一组件后来（批次2）又调用了`useAuthInfo()`这个hook，hook内部**又**发了一次`/auth/me`——同一个组件、同一次页面加载，实际发出了两次内容完全相同的`/auth/me`请求。此前的设计文档（§十五附近）曾把这个重复标注为"可接受的保守取舍"，但既然用户已经实测感知到延迟，这次一并优化掉。
- **修复**：`three-panel-interface.tsx`的`sessionId`用户名覆盖逻辑改为直接复用同组件内`useAuthInfo()`的`authInfo.user`结果（新增一个`useEffect`监听`authInfo.user?.username`变化），不再自己单独发起第二次`/auth/me`；`use-auth-info.ts`内部`/auth/mode`与`/auth/me`两个请求语义上互不依赖，原实现串行`await`，改为`Promise.all`并行发起，减少一次网络往返的等待时间。
- **TaskType卡片延迟**：复核`GET /sop/tasks`后端实现，任务定义走的是内存中的`registry`单例（非每次请求都重新扫描磁盘/解析YAML），接口本身逻辑很轻量，不是这个接口"慢"；更可能的原因是页面刷新时会同时打出一批请求（`/auth/mode`、`/auth/me`、`/workspace/files`、`/workspace/tree`、`/sop/tasks`、`/sop/history`，管理员还多一个`/admin/workspace/sessions`），若干个请求同时抢占后端处理顺序，靠后处理的请求自然感觉"更慢"。本次未对后端并发处理能力做进一步改造（属于更大范围的性能优化，超出本次问题排查范围），仅完成了上述"减少总请求数量"这一步。

**已知局限**：此项修复只是"减少了两个请求变一个请求+两个串行变并行"，能缓解但不能完全消除延迟感——如果用户实测后觉得改善不明显，需要进一步排查是否是后端并发处理瓶颈（如同步阻塞的DB调用占用了事件循环），这需要更大范围的性能剖析，暂未展开。

### 二十八、根治性能瓶颈：bcrypt密码校验阻塞事件循环（2026-07-02）

§二十七的优化（减少重复请求+并行化）用户实测后反馈"快了一些但仍有明显延迟"，进一步排查找到了更根本的瓶颈。

**根因**：`API/auth_middleware.py::BasicAuthMiddleware.dispatch()`里，`user = self.auth.authenticate(request)`是**同步阻塞调用**，内部链路`authenticate()`→`_verify_db()`→`UserService.verify_password()`→`bcrypt.checkpw()`。bcrypt是刻意设计得"慢"的哈希算法（抵御暴力破解），单次校验通常耗时几十到一两百毫秒。Basic Auth协议本身无状态，**每一次HTTP请求都要重新携带凭证、重新做一次bcrypt校验**（不是登录时校验一次就完，而是所有需要认证的接口每次调用都要过一遍）。此前这个同步调用直接跑在FastAPI/Starlette的asyncio事件循环线程上，会完整阻塞整个事件循环——而后端是单进程单事件循环（`python API/main.py`直接启动，没有配置多worker）。

页面刷新时前端会几乎同时打出六到十个左右需要认证的请求（`/auth/me`、`/workspace/files`、`/workspace/tree`、`/sop/tasks`、`/sop/history`、渠道列表，管理员还多一个`/admin/workspace/sessions`）。这些请求的bcrypt校验被迫在同一条事件循环线程上排队串行执行——这才是用户反馈"多个互不相关的区域都要等几秒才出来"的**主要瓶颈来源**，而不是网络延迟、也不是§二十七排查时怀疑的"业务逻辑本身慢"（`/sop/tasks`等接口的业务逻辑本身确实很轻量，冤枉了它们）。

**修复**：`dispatch()`里改为`user = await run_in_threadpool(self.auth.authenticate, request)`（`starlette.concurrency.run_in_threadpool`）。bcrypt底层C扩展计算期间会释放GIL，扔进线程池后，多个并发请求的bcrypt校验可以在不同线程上真正并行执行，不再互相排队阻塞事件循环。

**验证**：`tests/test_auth_middleware.py`25项回归全通过（含`run_in_threadpool`包装后异常仍能正确传播到外层`except HTTPException`分支的验证）。

**已知局限**：
- bcrypt本身的耗时是安全特性（cost factor决定了暴力破解的难度），这次修复解决的是"多个请求互相排队等待"，不是让单次校验本身变快——单个请求的绝对延迟不会有明显变化，但N个并发请求的**总感知延迟**应该从"接近N倍单次耗时"降到"接近1倍单次耗时"，这是本次优化的收益来源
- 未做真实压测/浏览器端到端计时对比（只做了单测回归+服务健康检查），效果需要用户实测确认
- 如果修复后延迟依然明显，需要考虑：① 是否还有其他同步阻塞点（如SQLAlchemy同步session在事件循环里跑DB查询）；② 是否要引入连接级/短TTL的凭证校验结果缓存（如"同一浏览器session内5分钟内不用每次都重新bcrypt"），后者涉及架构改动，暂不在本次范围内

### 二十九、登录弹窗"盲存凭证"+账户锁定状态未随admin重置密码清除（2026-07-02，用户实测反馈）

用户报告两个现象：①输错密码登录不会提示错误，会"进入页面"，但各区域各自显示"加载失败"；②`fjzheng`改密后登不上，admin重置密码后用新密码依然登不上，界面表现和①一样。排查确认是两个独立但相关的根因。

#### 根因1：登录弹窗从不校验凭证，"盲存"后就关闭

`demo/chat/components/LoginDialog.tsx`与`llm_manager_integrated/frontend/shared/js/auth.js`的登录表单提交逻辑，此前只是把输入框内容`btoa`编码后存进`localStorage`就立即关闭弹窗、resolve——**从不会真正拿这份凭证去后端验证对不对**。无论密码对错、账户是否被锁定，弹窗体验上都是"顺利登录成功"，真正的失败只会在稍后某个业务请求收到401/429时才暴露，且暴露方式是各个组件各自的通用错误文案（"加载失败"/"加载任务列表失败"），完全看不出"是密码错、还是账户被锁、还是网络问题"。

**修复**：两处登录表单提交时改为先用刚输入的凭证主动请求一次`/auth/me`（不经过`authFetch`/全局拦截器的401重试逻辑，避免互相干扰），根据响应区分：
- `401` → 弹窗内展示"用户名或密码错误"，不关闭，允许重新输入
- `429` → 展示后端返回的具体`detail`（含剩余锁定时长，如"账户已锁定，请15分钟后重试"）
- 其他非2xx → 展示"登录失败（HTTP xxx），请重试"
- 仅`200`时才真正保存凭证并关闭弹窗

#### 根因2：admin重置密码接口从未清除账户锁定状态

排查`fjzheng`具体状态：`config/login_state.json`显示`{"count": 6, "last_failure": ...}`——已超过默认阈值5次，处于15分钟锁定窗口内（测算时还剩约7分钟）。`API/auth_middleware.py::SimpleAuth._is_locked()`的锁定判断**先于**密码校验执行，且只看失败次数+时间窗口，与密码是否正确无关。对比发现：自助改密接口`/auth/change-password`早就有`auth._reset_failures(username)`清锁逻辑（校验旧密码通过后清除），但管理员代重置密码接口`/admin/users/{username}/reset-password`**从未做这个处理**——admin重置完密码，用户拿着全新正确密码登录，依然会被锁定状态拦下，且不会因为密码已被admin重置而提前解除，只能傻等锁定窗口自然过期。

**修复**：`API/user_admin_api.py::reset_user_password`在设置新密码后，追加调用`auth._reset_failures(username)`清除锁定计数——admin已经通过管理页面验证过身份并主动重置密码，没有安全理由继续保留锁定状态。

**验证**：`tests/test_auth_middleware.py`+`test_user_management_phase9.py`+`test_user_management_phase10.py`共约80项回归全通过。未做真实浏览器端到端验证（登录弹窗的分支逻辑基于代码审查，锁定清除逻辑基于代码审查+现有单测覆盖，未实际复现"锁定中→admin重置→立即登录成功"这一真实链路），需要用户实测确认。

补充说明：`fjzheng`当前的锁定状态是修复代码上线**之前**产生的历史数据，本次代码修复只对"以后再发生的重置密码操作"生效，不会追溯清除已有的锁定记录。为免用户继续等待剩余锁定时间，本次直接手动编辑`config/login_state.json`将`fjzheng`的`count`/`last_failure`重置为`0`，并重启了后端使内存中的锁定状态重新从磁盘加载（`SimpleAuth`只在启动时`_load_failures()`一次，不改文件本身不会生效）——此后`fjzheng`应可立即用admin重置的新密码登录，不需要等待。

### 三十、强制改密弹窗"不知道旧密码"死锁场景补一个逃生出口（2026-07-02，用户实测反馈）

修复§二十九后，用户刷新3000页面直接弹出`fjzheng`账户的强制改密弹窗（因为浏览器`localStorage`里保存的凭证正是`fjzheng`，且其`must_change_password=true`），但用户没有保存admin重置给的那个一次性初始密码，而"确认修改"必须先填对旧密码——**弹窗按§15.6无障碍规范设计成"无法通过Esc/点击遮罩/右上角❌关闭"，此前也没有任何其他退出方式**，用户被完全卡死：改不了密码（不知道旧密码），也退不出这个弹窗（唯一能用的技术手段是打开浏览器控制台手动清`localStorage`，普通用户不会操作）。

**修复**：`AccountSettingsDialog.tsx`在`forceMode`下的按钮行新增"忘记旧密码？退出登录"链接按钮（与"确认修改"同排，左侧次要位置，不影响"先改密才能继续使用"这个核心约束——只是把"继续使用当前账户"的死路，换成"退出去登录别的账户/等admin再给一次密码"这条活路）。点击后清除本地凭证并刷新页面，回到未登录状态，此时弹出的是普通登录框（可取消），不再是强制改密框。

**已知局限**：未做真实浏览器点击验证（基于代码审查），且没有同步给LLM Manager那一侧加类似逃生出口——LLM Manager目前没有强制改密这个功能/UI，`must_change_password`是`demo/chat`主应用独有的概念，不适用。

### 三十一、「用户管理」重置密码按钮补充二次确认（2026-07-03）

用户反馈：点击用户列表「重置密码」（钥匙图标）按钮会立即执行，没有任何确认步骤。相比"禁用/启用"（可逆，点第二次即可撤销），重置密码是不可逆操作——旧密码立即失效，被误触的用户需要重新拿一次性新密码登录，代价更高。

**修复**：`UserManagerPage.tsx`新增`resetConfirmRow`状态，钥匙按钮点击后先弹出`AlertDialog`二次确认（复用项目里已有的shadcn `alert-dialog`组件，与`three-panel-interface.tsx`里"批量删除文件"确认弹窗风格一致），文案明确提示"旧密码会立即失效"+"此操作不可撤销"，用户点击"确认重置"后才真正调用`handleResetPassword`。纯前端改动，无需重启后端。

### 三十二、过期/禁用账户使用正确密码登录时误报"用户名或密码错误"（2026-07-03，用户实测反馈）

用户在验证第13项（有效期高亮）时发现：账户过期后即使输入完全正确的密码登录，弹窗提示的仍是"用户名或密码错误"；随后追问确认第14项（禁用/启用）同样复现——禁用账户输入正确密码登录，提示也是"用户名或密码错误"。

**根因**：`UserService.verify_password()`（DB模式）与`SimpleAuth._verify_yaml()`（yaml模式）对"密码错误""账户不存在""已禁用""已过期(`valid_until`)"这四种失败原因统一返回`None`，`SimpleAuth.authenticate()`据此统一抛出401 + `detail="Invalid credentials"`；`LoginDialog.tsx`/`auth.js`的登录弹窗（§二十九新增的登录前预检）收到401后又统一硬编码展示"用户名或密码错误"，完全不区分具体原因。对密码确实错误的场景这个提示没问题，但对"密码对、账户状态有问题"这两种场景，会强烈误导用户以为自己记错了密码，可能导致反复重试甚至触发§二十九修复的连续失败锁定。

**修复**（涉及后端+前端，两处登录框同步修复）：

1. **后端新增"登录失败具体原因"判定**，且严格限定安全边界——只有当密码校验本身通过时才区分具体原因，密码错误或账户不存在统一归类为`invalid_credentials`，避免向尚未持有正确密码的攻击者泄露账户是否存在/是否被禁用/是否过期这些状态信息（与既有的防时序攻击设计目标一致，不构成新的信息泄露面）：
   - `UserService.get_login_failure_reason()`（DB模式）：重新执行一次bcrypt校验，密码匹配后再判断`enabled`/`valid_until`，返回`"invalid_credentials"|"disabled"|"expired"`
   - `SimpleAuth._get_yaml_failure_reason()`（yaml模式）：同等逻辑（yaml无禁用概念，只判断过期）
   - `SimpleAuth._get_failure_reason()`：按当前数据源（DB优先/yaml兜底）分发到上述两者
2. **`SimpleAuth.authenticate()`改造**：`self.verify()`失败后，调用`_get_failure_reason()`区分处理——`disabled`/`expired`时返回**403**（而非401）+ 对应中文detail（"账号已被禁用，请联系管理员"/"账号已过期，请联系管理员"），且**不计入登录失败次数**（密码本身是对的，不属于"猜密码"行为，不应消耗§十九的5次失败锁定额度）；真正的密码错误仍走原有401流程，行为不变
3. **前端两处登录框**（`LoginDialog.tsx`、`auth.js`）：登录预检的错误处理从"401/429分别硬编码/半硬编码文案"统一改为读取响应体`detail`字段展示，仅对401单独保留中文兜底文案（因为401场景后端detail是内部通用英文文本`"Invalid credentials"`，不适合直接展示给用户）；403（新增）和429（已有）直接展示后端返回的中文detail

**验证**：`tests/test_auth_middleware.py`+`test_user_management_phase9.py`+`test_user_management_phase10.py`共77项回归全通过。后端已重启生效。

**已知局限**：
- 全局fetch拦截器（`config.ts`/`auth.js`）的401自动重登录重试逻辑不处理403——即已登录会话中途账户被禁用/过期这种边缘场景（如admin在用户使用过程中把其禁用），后续业务请求会直接收到403并按各自的通用错误处理展示（不会弹登录框重试，因为重试无意义），这是合理行为但未做专门的用户提示优化，暂不在本次范围内
- 未做真实浏览器端到端验证（基于代码审查+现有单测覆盖），需要用户实测确认——即用管理员对某测试账户设置一个已过去的`valid_until`（或禁用该账户），用该账户**正确密码**登录，应看到"账号已过期/已被禁用，请联系管理员"而非"用户名或密码错误"

---

## 评审与决策审计记录

### autoplan 执行说明
本文档已通过 autoplan 方法论完成 CEO → Design → Eng 三阶段独立评审（Claude subagent 独立双声道，未见Codex CLI，标记`[subagent-only]`）。因本项目未使用git分支/PR工作流、未安装`gh`/`codex` CLI，评审过程未接入gstack的bash持久化/审计基础设施，仅遵循其评审方法论产出本文档内容。

### 机械性决策（自动决定，遵循6大原则）

| # | 决策 | 依据原则 |
|---|------|---------|
| M1 | 改密成功后自动同步本地凭证，不等401才弹登录框 | 显式优于巧妙 |
| M2 | 用户名重复返回明确错误码+前端内联提示 | 显式优于巧妙 |
| M3 | 复用现有`ModelConfigModal`的loading/saving双态与Toast风格 | DRY |
| M4 | 403统一走前端全局拦截处理 | 显式优于巧妙 |
| M5 | 用户管理表格给`valid_until`临期/过期账户加视觉高亮 | 完整性 |
| M6 | 用户名前端正则实时校验 | 完整性 |
| M7 | 账户设置弹窗内"改密码"排在"个人信息编辑"之前 | 完整性 |
| M8 | 新建用户名与已软删除账户重名返回409+指引 | 完整性，杜绝边界失败 |
| M9 | 迁移脚本"先回填DB再移动文件"+持久化进度记录 | 完整性，工程严谨 |
| M10 | 迁移优先走"用户自助认领"，admin映射降级为兜底 | 完整性，错误率更低 |
| M11 | Phase 3补"受影响路由清单"交付物，重估工作量（1.5天→2天） | 煮沸湖泊，诚实估算 |
| M12 | HTTPS作为启用密码相关功能的硬性前置条件 | 完整性，低成本止损 |
| M13 | 增加"账户合并"功能（§七+§十五.3） | 完整性，成本极低 |
| M14 | 增加"6个月后复查"机制 | 长期debt防范 |
| M15 | 所有权校验：从认证身份派生，忽略客户端参数，admin走独立命名空间 | 显式优于巧妙 |
| M16 | 无DESIGN.md，不额外触发`/design-consultation`建系统，复用现有组件风格（Design Review Pass 5结论） | 煮沸湖泊需权衡投入产出，功能级复用优先 |
| M17 | 身份菜单入口位置：中列Header内、紧邻主题切换🌙按钮，不新增一整行；「用户管理」「LLM渠道管理」通过该菜单跳转独立页面 | Pass 1信息架构，与用户讨论确认（中列Header无条件渲染更稳定，右列因三态视图不适合承载全局入口） |
| M18 | admin账户锁死恢复（break-glass）：不做UI/API内的"忘记密码"流程，沿用现状——ops直接用`hash_password.py`生成哈希后SQL更新`users`表；写入运维手册作为兜底方案 | 内网<10人场景已有服务器直接访问权限，无需为极端情况建专门UI |
| M19 | `/auth/change-password`旧密码校验复用`SimpleAuth`现有的`max_login_failures`/锁定机制（按username计数），防止该接口被用来暴力破解旧密码 | DRY复用现有机制；AuthZ完整性，此前方案遗漏 |
| M20 | 开发阶段核实发现`/sop/status/{execution_id}/stream`从未实现（TD5前提有误），撤销SSE专项修复，将`get_task_status`归属校验并入Phase 3常规范围，Phase划分工作量5.8天→5.3天 | 诚实修正，代码事实优先于评审文档假设 |

### 品味决策（用户确认）

| # | 决策项 | 最终选择 |
|---|--------|---------|
| TD1 | 项目拆分 | ✅ 按**发布顺序**拆分为批次1（隔离越权修复，先行）+批次2（账号管理Web UI，紧随）；两者均为完整正式设计 |
| TD2 | 身份隔离键实现 | ✅ session_id直接承载username，新增独立tab_id |
| TD3 | Build vs Buy | ✅ **已评估完成（2026-07-02）**：确定自建，不引入`fastapi-users`（核心冲突：该库强制JWT/Cookie认证+UUID主键，与已锁定的"维持Basic Auth"决策及批次1"session_id=username"身份模型直接冲突，迁移成本远超自建） |
| TD4 | 新密码告知机制 | ✅ 一次性明文展示 + 首次登录强制改密（两者都做） |
| TD5 | SSE鉴权洞 | ⚠️ **已撤销**（2026-07-02开发阶段核实）：`/sop/status/{execution_id}/stream`从未在代码库实现，仅存于已归档设计文档，原CEO评审判断基于过时文档误判。实际存在的是`/sop/status/{execution_id}`轮询接口缺少归属校验，已并入Phase 3常规所有权校验范围 |
| TD6 | username字符集约束 | ✅ 接受约束：`^[a-zA-Z0-9_-]+$`，创建账户时用拼音/工号风格命名 |

### 修正记录
- 2026-07-02：用户指出"批次2账号管理UI是本模块核心特点之一，不应降级为附录/参考"——已将批次2设计从「附录A」提升为正式主体章节（§十二~§十八），恢复完整用户表schema、全套API、前端交互细节，移除所有弱化措辞。TD1的含义澄清为"仅影响发布顺序，不影响设计完整性"。
- 2026-07-02（开发阶段）：核实代码库发现`/sop/status/{execution_id}/stream`从未实现（仅存于归档设计文档），TD5"SSE鉴权洞"的前提不成立，已撤销该项修复（stream-token接口、HMAC签名、Phase 2），改为将实际存在的`/sop/status/{execution_id}`轮询接口归属校验并入Phase 3常规范围，工作量估算5.8天→5.3天。

### 不在本次范围（NOT in scope）
- 引入JWT/OAuth等新认证协议（维持Basic Auth）
- LLM渠道按用户隔离/配额
- 用户自助注册
- 单用户模式（`ENABLE_AUTH=false`）下的任何改动
