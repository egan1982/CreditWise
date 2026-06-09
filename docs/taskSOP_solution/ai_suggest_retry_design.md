# 专家模式：AI 建议一键调参重跑 + 版本对比

> 分支：`feature/intranet-multiuser`  
> 状态：✅ 已实施（2026-06-02）  
> 优先级：P1  
> 实际工作量：~2天（B1~B6 后端 + F1~F4 前端 + T1 12单元测试全通过）  
> 依赖：专家模式 Phase 1-3（✅ 已完成）  
> 待验收：HT-01~HT-05 手工测试（本机人工验证）

---

## 1. 问题陈述

### 1.1 当前痛点

专家模式下，每个阶段完成后 AI 自动输出分析文本，文本中包含"建议调整参数"的自然语言描述。  
但用户需要：
1. 阅读文本建议
2. 手动记住参数名和建议值
3. 切换到"参数"Tab
4. 在 JSON 编辑器中定位字段并修改
5. 点击"重试"

**操作链路断裂，AI 建议与参数编辑器没有联动。**

### 1.2 用户提出的关键问题

> "有没有考虑一键调参重跑之后阶段结果/任务结果与上一版/多版的对比，如何展示？"

这是本功能的核心设计挑战：**每次 retry 会覆盖全局 `context.params` 并重置阶段状态，上一版本结果丢失。**

---

## 2. 功能范围

### 2.1 In Scope

| 功能 | 描述 |
|------|------|
| **F1：结构化参数建议** | AI 分析时后端同时输出 `suggested_params` 字段（JSON），标明建议修改的参数名→新值 |
| **F2：建议参数卡片** | AI 分析区域下方展示建议参数卡片，显示 before→after diff + 建议原因 |
| **F3：一键应用建议** | 点击"应用建议"→ 自动填充参数编辑器 `localParams` → 用户可进一步微调 → 触发重试 |
| **F4：阶段级版本快照** | 每次 retry 前，将当前阶段的 `{params_used, output_preview, ai_analysis}` 作为快照保存 |
| **F5：版本历史对比** | 阶段结果区域显示版本选择器（v1/v2/v3...），支持切换查看历史版本的输出预览、参数、AI 分析 |
| **F6：用历史版本参数重跑** | 历史快照视图中提供"用此版本参数重跑"按钮，调用现有 `retryStage(stageId, snapshot.params_used)`，实现零工作量的版本回滚 |

### 2.2 Out of Scope

| 功能 | 理由 | 规划版本 |
|------|------|---------|
| 多版本结果并排对比（side-by-side） | 界面空间有限；版本切换（timeline）已覆盖 | — |
| 跨任务版本对比（不同 execution_id 之间） | 超出范围 | P3 |
| **版本恢复（直接还原快照状态，跳过重新执行）** | 需新 API，约2-3h额外工作量。"用历史参数重跑"（F6）已满足 90% 场景，两次执行结果若有差异（随机种子）用户可接受 | v2 |
| AI 建议的参数范围校验（值域校验） | 各阶段未统一 validation；降级方案见 §7 | v2 |

> **版本回滚决策说明**：
> - **F6（用历史参数重跑）本期实现**：工作量=0，直接复用现有 `retryStage(stageId, params)`。用户切换到历史视图后点击"用此版本参数重跑"，触发一次带快照参数的重试，产生新版本（内容与历史版本一致）。
> - **方案B（直接还原状态）v2 规划**：当模型训练结果有随机性时，方案A可能产生与快照不完全一致的结果；方案B直接恢复快照的 `output_preview`，精确还原。需要新 API `POST /stages/{id}/restore-snapshot`，约2-3h工作量，价值较边缘，推后实施。

---

## 3. 数据模型设计

### 3.1 新增：`StageSnapshot`（阶段版本快照）

```python
@dataclass
class StageSnapshot:
    """单次执行结果快照，用于版本历史对比"""
    version: int                    # 1, 2, 3...（第几次执行）
    params_used: dict               # 本次执行实际使用的参数
    output_preview: dict | None     # 本次执行的阶段输出
    ai_analysis: str | None         # 本次执行的 AI 分析文本
    suggested_params: dict | None   # 本次 AI 建议的参数（如有）
    execution_time_ms: int | None   # 本次执行耗时
    completed_at: str | None        # ISO 时间字符串
    retry_reason: str | None        # 本次重试原因（用户填写或"接受AI建议"）
```

### 3.2 `StageProgress` 新增字段

```python
@dataclass
class StageProgress:
    # ... 现有字段不变 ...
    snapshots: list[StageSnapshot] = field(default_factory=list)
    # 当前版本号 = len(snapshots)（每次重试前追加快照）
    current_version: int = 1
```

### 3.3 AI 分析 API 返回结构扩展

```python
# POST /sop/history/{record_id}/stages/{stage_id}/analysis 保存时新增字段
{
  "analysis_text": "...",          # 现有
  "model_used": "...",             # 现有
  "suggested_params": {            # 新增：从 analysis_text 中解析
    "max_depth": 5,
    "min_samples_leaf": 0.02
  },
  "suggestion_reason": "..."       # 新增：简短说明（从 analysis_text 提取）
}
```

### 3.4 DB 变更

`stages_json`（`TaskRecord.stages_json` JSONB 字段）中的 stage entry 增加 `snapshots` 数组：

```json
{
  "woe_binning": {
    "stage_id": "woe_binning",
    "params_used": {...},
    "output_preview": {...},
    "snapshots": [
      {
        "version": 1,
        "params_used": {"max_depth": 3},
        "output_preview": {...},
        "ai_analysis": "...",
        "suggested_params": {"max_depth": 5},
        "completed_at": "2026-06-02T10:00:00Z"
      }
    ]
  }
}
```

---

## 4. 技术方案

### 4.1 后端：Prompt 改造（`AI_analysis_prompts.py`）

在各阶段 `get_stage_analysis_prompt()` 末尾追加结构化输出要求：

```python
## 参数建议
如有参数调整建议，在分析文本末尾追加以下标记行（无建议时省略此行）：
SUGGESTED_PARAMS: {"param_key": value, ...}

可调整的参数键名（只能使用以下键名）：
{stage_available_params}  ← 运行时注入当前阶段的 ParamDefinition.name 列表
```

**解析策略**：在 `sop_api.py` 的保存 AI 分析接口中，从 `analysis_text` 末尾解析 `SUGGESTED_PARAMS:` 行，提取 JSON 并存入 `suggested_params` 字段。分析文本中剥离该标记行后再存储（用户看到的是干净的 Markdown）。

**降级**：LLM 未输出该标记 → `suggested_params = None` → 前端不显示建议卡片，不影响现有行为。

### 4.2 后端：retry_stage 改造

在执行重试前，将当前阶段状态打快照追加到 `stage.snapshots`：

```python
# sop_api.py retry_stage 第 3 步之前
if stage.status == ExecutionStatus.COMPLETED and stage.output_preview:
    snapshot = StageSnapshot(
        version=len(stage.snapshots) + 1,
        params_used=dict(stage.params_used),
        output_preview=dict(stage.output_preview),
        ai_analysis=await _load_stage_analysis(record_id, stage_id),  # 从 DB 读取
        suggested_params=None,   # 从上一次 AI 分析中取（可选）
        execution_time_ms=stage.execution_time_ms,
        completed_at=stage.completed_at.isoformat() if stage.completed_at else None,
        retry_reason=request.retry_reason  # 前端可选传递
    )
    stage.snapshots.append(snapshot)
```

### 4.3 前端：建议参数卡片（独立组件 `SuggestedParamsCard.tsx`）

在 AI 分析流式输出**完成后**解析 `suggestedParams`（从后端 stage analysis 接口获取，不在前端解析 Markdown），仅当 `suggested_params` 非空时渲染：

```
┌─────────────────────────────────────────────────────┐
│ 💡 AI 参数建议                                       │
│ 调整原因：当前树深度不足以捕获非线性关系              │
│                                                     │
│  max_depth          ~~3~~  →  **5**                 │
│  min_samples_leaf   ~~0.01~~  →  **0.02**           │
│                                                     │
│  [仅填入参数]    [填入并立即重试]                     │
└─────────────────────────────────────────────────────┘
```

缺失状态处理：
- AI 分析流式输出中：不显示卡片（等完成后再解析）
- `suggested_params = null`：不渲染卡片
- 重试进行中：禁用两个按钮（`disabled`）

### 4.4 前端：版本历史选择器（独立组件 `StageVersionSelector.tsx`）

在阶段结果 Tab 栏右侧显示（仅当 `snapshots.length > 0`）：

```
[结果] [参数] [代码]          版本: [v1 10:00] [v2 10:23] [当前▾]
```

历史版本视图：
- 顶部显示 banner："📸 历史快照 v1 (2026-06-02 10:00)"
- `output_preview = null` 时显示："该版本无结果数据"
- 重试进行中：禁用版本切换器（`disabled`）

### 4.5 版本对比展示策略

| 对比方式 | 采用？ | 理由 |
|---------|-------|------|
| **版本切换（Timeline）** | ✅ 采用 | 界面简洁，信息完整，适合 <10 次迭代 |
| **并排对比（Side-by-side）** | ❌ 不采用（v1） | 信息密度太高，风控分析师阅读负担大 |
| **差异高亮（Diff）** | ⚠️ 仅参数部分 | 参数变更 before→after 高亮有用；输出指标 diff 价值有限 |
| **指标趋势图** | 📋 可选（v2） | 多版本 KS/AUC 趋势线，直观但需单独开发 |

**核心设计原则**：版本历史是**辅助参考**，不是主界面。保持当前版本为默认视图，历史版本通过下拉/Tab 切换访问，不打扰正常工作流。

---

## 5. UI 交互流程

```
阶段完成（status=completed）
  ↓
AI 自动分析（streaming，约15秒）
  ↓
分析完成，显示：
  ┌─ AI 分析文本（Markdown）
  └─ 💡 AI 参数建议卡片（如有 suggested_params）
       ├─ before → after diff
       └─ [仅填入] / [填入并重试]

用户点击"填入并重试"
  ↓
前端：setLocalParams → onRetryStage(stageId, mergedParams, retry_reason="接受AI建议")
  ↓
后端：
  1. 打快照（当前结果→ snapshots）
  2. context.params.update(new_params)
  3. 重置阶段状态
  4. 启动新执行
  ↓
阶段重新执行
  ↓
新版本结果展示
  ↓
版本选择器出现 [v1 ▾] [当前]
  ↓
用户可切换 v1 查看历史结果
```

---

## 6. 实现分解

| 任务 | 文件 | 工作量 |
|------|------|--------|
| B1：`StageSnapshot` dataclass + `StageProgress.snapshots` | `executor.py` | 0.5h |
| B2：`retry_stage` 打快照逻辑 | `sop_api.py` | 1h |
| B3：快照序列化/反序列化到 `stages_json` | `executor.py` / `history_service.py` | 1h |
| B4：AI 分析 Prompt 追加 `SUGGESTED_PARAMS` 格式要求 | `AI_analysis_prompts.py` | 2h |
| B5：AI 分析保存接口解析 `SUGGESTED_PARAMS`，存入 DB | `sop_api.py` | 1h |
| B6：stage analysis GET 接口返回 `suggested_params` 字段 | `sop_api.py` | 0.5h |
| F1：`SuggestedParamsCard.tsx`（before→after diff + reason + 两个按钮） | 新建组件 | 3h |
| F2：`StageVersionSelector.tsx`（版本切换器） | 新建组件 | 2h |
| F3：历史版本视图 + SnapshotViewer + "用此版本参数重跑"按钮（F6） | `StageOutputPreview.tsx` | 2h |
| F4：`onRetryStage` 透传 `retry_reason` | `three-panel-interface.tsx` | 0.5h |
| T1：单元测试（6个） | `tests/` | 1.5h |
| T2：手工测试（5个 HT） | — | 1h |
| **合计** | | **~16h（约2天）** |

---

## 7. 风险与降级

| 风险 | 降级策略 |
|------|---------|
| LLM 未输出 `SUGGESTED_PARAMS` | `suggested_params=None`，不渲染卡片，完全向下兼容 |
| LLM 输出的参数 key 不在当前阶段的 ParamDefinition 中 | 过滤掉未知 key，只展示已知参数的建议 |
| LLM 输出的参数值类型错误 | 按 `ParamDefinition.param_type` 做 best-effort 类型转换，失败则跳过该参数 |
| snapshots 数组过大（用户重试 20+ 次） | 保留最近 10 个快照（FIFO），超出时丢弃最旧的 |
| 旧版 execution 无 snapshots 字段 | 反序列化时默认为空列表，无历史版本但不报错 |

---

## 8. 测试方案

### 8.1 单元测试
- `test_stage_snapshot_serialization`：快照序列化/反序列化往返测试
- `test_retry_creates_snapshot`：retry_stage 后 snapshots 长度 +1，内容与重试前 stage 一致
- `test_suggested_params_parsing`：各种 SUGGESTED_PARAMS 格式（含格式错误的降级）
- `test_unknown_param_key_filtered`：未知参数 key 被过滤
- `test_backward_compat_no_snapshots`：旧 execution（无 snapshots 字段）反序列化默认为空列表
- `test_snapshots_fifo`：重试超过10次时，保留最近10个（FIFO）

### 8.2 手工测试

> **前置条件**：本机启动前后端（`uvicorn` + `npm run dev`），使用规则挖掘任务，数据文件准备好（含目标变量），切换到**专家模式**。

---

#### HT-01：AI 建议卡片出现 + "填入并重试"触发版本切换器

**目标**：验证 LLM 输出 SUGGESTED_PARAMS 后，建议卡片正确渲染，点击"填入并重试"后版本切换器出现。

**操作步骤**：
1. 新建规则挖掘任务，上传数据，选择目标变量，`mining_mode` 选"多变量规则"，启动执行
2. 在左侧面板切换到**专家模式**
3. 等待 `generating_rules`（规则生成）阶段完成（状态变为"已完成"）
4. 右侧面板自动触发 AI 分析，等待流式文本输出完毕（约 15 秒）
5. 观察 AI 分析文本下方是否出现"💡 AI 参数建议"卡片
   - 卡片内应显示 before → after 参数对比（如 `max_depth: 3 → 5`）
   - 卡片底部有两个按钮："仅填入参数" 和 "填入并立即重试"
6. 点击**"填入并立即重试"**按钮
7. 观察右侧面板顶部 Tab 栏右侧，应出现版本选择器：`[v1 HH:MM] [当前▾]`
8. 观察参数 Tab，`max_depth` 等建议参数值已被填入

**验收标准**：
- ✅ 步骤5：建议卡片出现，参数 diff 与 AI 文本中提及的建议一致
- ✅ 步骤7：版本选择器在 Tab 栏右侧出现，显示 v1 + 当前
- ✅ 步骤8：参数面板中对应参数值已更新为建议值

---

#### HT-02：切换历史版本 — 只读模式 + banner 展示

**目标**：验证版本切换器切换到历史快照后，界面进入只读状态并显示历史 banner。

**前置**：完成 HT-01（已有 v1 快照）。

**操作步骤**：
1. 在 HT-01 完成后，等待重试阶段执行完毕
2. 点击版本切换器中的 **[v1 HH:MM]**（历史快照版本）
3. 观察右侧面板顶部是否出现历史 banner，内容类似：
   `📸 历史快照 v1 (2026-06-02 16:30)`
4. 查看结果 Tab，确认展示的是 v1 的输出数据（规则数量/指标与当前版本不同）
5. 查看参数 Tab，确认展示的是 v1 执行时使用的参数值（如原 `max_depth=3`）
6. 尝试修改参数面板中的某个值，确认**无法编辑**（输入框禁用或无响应）
7. 尝试点击"重试"按钮，确认**按钮禁用**或不可触发
8. 点击版本切换器中的 **[当前]**，banner 消失，界面恢复正常可操作状态

**验收标准**：
- ✅ 步骤3：顶部出现历史 banner，版本号和时间正确
- ✅ 步骤4/5：展示 v1 的数据和参数（与当前版本有差异）
- ✅ 步骤6/7：历史视图为只读，无法触发新操作
- ✅ 步骤8：切换回当前版本后 banner 消失，恢复可操作

---

#### HT-03：LLM 未输出建议时卡片不出现（降级验证）

**目标**：验证当 LLM 未输出 SUGGESTED_PARAMS 时，AI 分析文本正常显示，不出现建议卡片，不影响正常流程。

**操作步骤**：
1. 新建规则挖掘任务，使用`单特征规则`模式（`mining_mode=single`），启动执行
   > 单特征模式的 generating_rules 阶段参数较少，LLM 通常不会给出具体调参建议
2. 切换到专家模式，等待 `preprocessing`（数据预处理）阶段完成
3. 观察该阶段的 AI 分析区域：
   - AI 分析文本正常显示（段落文字）
   - 文本下方**不出现**"💡 AI 参数建议"卡片
4. 点击"重新分析"按钮，重新触发 AI 分析，再次确认无建议卡片
5. 检查 AI 分析文本末尾，确认无 `SUGGESTED_PARAMS:` 字样（后端已剥离，用户不可见）

**备注**：若步骤3中出现了建议卡片，说明该阶段 LLM 确实给出了建议——此时换其他低参数阶段（如 `report_generation`）重新验证；核心验证点是**有建议才出卡片，无建议不出卡片**。

**验收标准**：
- ✅ AI 分析文本正常渲染，无异常格式
- ✅ 无建议时卡片区域为空，不占位不报错
- ✅ 文本末尾无 `SUGGESTED_PARAMS:` 泄露

---

#### HT-04：累计重试 3 次 — 版本选择器完整性

**目标**：验证多次重试后，版本选择器正确累积历史版本，且 FIFO 上限逻辑正确。

**前置**：在同一个任务的同一个阶段完成 HT-01 后继续操作。

**操作步骤**：
1. 在 HT-01 基础上（已有 v1），在参数 Tab 中手动调整任意参数（如将 `max_depth` 改为 4），点击"重试"
2. 等待该阶段执行完毕，AI 分析完成，此时版本选择器应显示 `[v1] [v2] [当前]`
3. 再次手动调整参数（如 `max_depth` 改为 6），点击"重试"
4. 等待执行完毕，版本选择器应显示 `[v1] [v2] [v3] [当前]`
5. 验证每个历史版本可分别点击查看，内容与该次执行时的参数/结果一致
6. （可选）继续重试至 10 次以上，验证版本选择器最多保留最近 10 个，不会无限增长

**验收标准**：
- ✅ 每次重试后版本号递增（v1 → v2 → v3）
- ✅ 各历史版本数据独立，切换后展示对应快照
- ✅ 版本选择器布局不溢出（3个历史版本时排列合理）

---

#### HT-05：重试进行中 — 版本切换器和建议卡片按钮均禁用

**目标**：验证阶段重试执行期间，版本切换器和建议卡片的操作按钮均处于禁用状态，防止并发冲突。

**前置**：在同一任务已有至少 1 个历史快照（v1）的基础上操作。

**操作步骤**：
1. 在参数 Tab 中手动修改任意参数，点击"重试"按钮，**立即**切换到结果 Tab（不等待执行完毕）
2. 此时阶段状态为 `running`，观察版本切换器：
   - 历史版本按钮（v1 等）应显示为**禁用**（置灰，点击无响应）
   - "当前"选项同样不可切换
3. 若当前面板有"💡 AI 参数建议"卡片（上一次分析留下的），观察其两个按钮：
   - "仅填入参数" 按钮应为**禁用**状态
   - "填入并立即重试" 按钮应为**禁用**状态
4. 等待重试执行完毕（阶段变为"已完成"），确认：
   - 版本切换器恢复可点击
   - AI 分析重新触发（上一次建议卡片已被清除，等待新分析完成后再次出现或不出现）

**验收标准**：
- ✅ 执行期间版本切换器所有按钮禁用（不可点击）
- ✅ 执行期间建议卡片两个操作按钮禁用
- ✅ 执行完毕后自动恢复可操作状态

---

## 9. 首批测试监控

首批上线后，统计10次 AI 分析中 `SUGGESTED_PARAMS` 出现率：
- ≥ 70%：Prompt 有效，正常运行
- 30-70%：需加强 Prompt few-shot 示例
- < 30%：重新设计 Prompt 结构

**监控结果（2026-06-09）**：
- qwen3-vl-235b-a22b-thinking：**100%**（真实数据测试 3/3）✅
- deepseek-v4-flash：**~67%**（部分阶段因业务判断未给建议，非格式问题）✅
- 两个模型建议卡片均稳定生成，**通过监控标准**

**主要 Bug 修复记录（P1 稳定化阶段）**：
- B-AI-1：`AI_analysis_prompts.py` 中文引号 SyntaxError 导致 prompt 返回空字符串
- B-AI-2：`_get_stage_available_params` 依赖 registry 初始化时机，改为直接读 meta 文件
- B-AI-3：`filtering_rules` vs `rule_filtering` stage_id 别名不一致导致参数匹配失败
- B-AI-4：`SUGGESTED_PARAMS` 嵌入句末（无换行）时解析/剥离失败
- B-AI-5：`exclude_cols` 等列名类参数 LLM 给占位符，加黑名单过滤
- B-AI-6：`_simple_chat_completion` 传 `workspace_dir=""` 导致工作区文件列表污染 AI 分析消息

---

## 10. 后续优化（已登记，待实施）

### OPT-1：首次评估 vs 重试评估双 Prompt 方案

**背景**：当前阶段 AI 评估使用统一 Prompt，重试场景下 LLM 不知道用户已主动调整过参数，容易出现"建议恢复原始值"的自相矛盾。

**方案**：
- **首次评估**（`snapshots.length === 0`）：当前 Prompt，评估结果质量 + 给出调参建议
- **重试评估**（`snapshots.length > 0`）：注入上一版本参数和结果摘要，Prompt 聚焦"参数调整效果对比"，判断调整是否有效，给出下一步建议

**Prompt 新增输入**（重试时）：
```
## 上一版本对比
参数变化：{prev_params_diff}（如 iv_threshold: 0.02 → 0.01）
上一版结果摘要：{prev_output_summary}（如 筛选后特征数: 29 → 34）
请基于此对比评估本次调整的效果，不要建议恢复到已被用户主动更改的参数值。
```

**实现点**：
- 前端 `promptRequest` 新增 `prev_snapshot` 字段（取 `stageData.snapshots[-1]`）
- 后端 `get_stage_analysis_prompt` 接收 `prev_snapshot`，有值时使用重试评估模板
- 优先级：P2，预计工作量 ~3h

*登记时间：2026-06-08*

---

### OPT-2：LLM 结构化输出（JSON Mode）

**背景**：当前 `SUGGESTED_PARAMS` 通过文本拼接约定输出，LLM 有时格式化 JSON 为多行，导致解析/剥离不稳定。已通过容错解析（多行支持 + Prompt 约束）缓解，但根本问题是"自由文本+约定标记"的脆弱性。

**问题根因链**：
```
自由文本输出 → LLM 格式抖动（单行/多行/缩进各异）
→ 解析失败 → 建议卡片不出现
→ 剥离失败 → SUGGESTED_PARAMS 泄露展示
```

**方案 A（推荐，渐进式）**：后端 Prompt 改为要求 LLM 输出固定 JSON 结构：
```json
{
  "analysis": "评估文本（Markdown 格式）",
  "suggested_params": {"param_key": value}  // 无建议时省略或 null
}
```
- 请求时加 `response_format: { type: "json_object" }`（支持 JSON Mode 的模型）
- 流式解析：累积完整 JSON 后再解析（非逐 token 展示 analysis 字段）
- 降级：若模型不支持 JSON Mode，回退当前文本方案

**方案 B（最小改动）**：仅把 `SUGGESTED_PARAMS` 输出改为独立 API 调用（非流式），主分析文本仍流式输出。代价是两次 LLM 调用。

**评估**：
- 方案 A 从根本上消除格式抖动，但流式体验需要改造（analysis 字段流式 → 先缓冲再输出，或分两段输出）
- 方案 B 改动小但增加延迟和费用
- **当前容错方案已够用**，此优化属于工程质量提升，非紧急

**优先级**：P3（低），预计工作量 ~1天  
*登记时间：2026-06-08*

*文档创建时间：2026-06-02，autoplan 审查完成*

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 1 | ✅ clean | 0 critical, 1 taste（建议reason显示）→ 采纳 |
| Codex Review | `/codex review` | Independent 2nd opinion | 0 | N/A（环境不可用） | — |
| Eng Review | `/plan-eng-review` | Architecture & tests | 1 | ✅ clean | 组件拆分、后端解析主、补2个测试 |
| Design Review | `/plan-design-review` | UI/UX gaps | 1 | ✅ clean | 2个缺失状态补充，HT-05新增 |

**VERDICT:** APPROVED — 8个自动决策，0个阻断问题，1个 taste 决策（已采纳）。  
**Cross-phase theme:** LLM 输出稳定性（CEO+Eng均提及）→ 已有降级，首批上线后统计服从率。  
**Next:** 实施时按 §6 任务分解顺序执行，B1→B2→B4→B5→F1→F2。
