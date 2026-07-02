# 用户管理与数据隔离模块设计方案

> 创建时间: 2026-07-01 | 评审更新: 2026-07-02（autoplan CEO/Design/Eng 三阶段评审 + 6项品味决策已确认）
> 状态: ✅ **批次1、批次2均已开发完成并通过全部单元测试**（2026-07-02，详见§九/§十七）；用户管理与数据隔离模块整体开发完成
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
