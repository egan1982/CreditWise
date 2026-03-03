# 任务管理模块测试分析报告

> 生成时间: 2025-01-05
> 对应文档: docs/taskSOP_solution/task_management_module_wip.md
> 对应阶段: Phase 5 - 测试与文档

---

## 1. 测试覆盖范围

根据验收标准（第9节），测试应覆盖以下功能：

### 1.1 任务控制功能 (9.1.1)
- ✅ 可以暂停正在执行的任务
- ✅ 暂停后任务状态变为 `paused`
- ✅ 可以恢复已暂停的任务
- ⚠️ **恢复后任务从暂停点继续执行** (待验证)
- ✅ 可以停止正在执行的任务
- ✅ 停止后任务状态变为 `stopped`
- ⚠️ **暂停/停止在当前阶段完成后生效（<5秒响应）** (待验证)

### 1.2 记录管理功能 (9.1.2)
- ✅ 任务开始时自动创建执行记录
- ✅ 任务完成/失败/停止时记录状态正确更新
- ✅ 任务参数、输入摘要、输出摘要正确保存
- ✅ 完整结果正确保存到文件系统
- ✅ 可以删除历史记录

### 1.3 历史查询功能 (9.1.3)
- ✅ 可以按任务类型筛选
- ✅ 可以按状态筛选
- ✅ 可以按时间范围筛选
- ✅ 分页查询正常工作
- ✅ 可以加载历史任务的完整结果
- ✅ 统计信息正确

### 1.4 性能验收 (9.2)
- ⚠️ **数据库写入 < 100ms** (待验证)
- ⚠️ **1000条记录查询 < 500ms** (待验证)
- ⚠️ **暂停/停止响应 < 5秒** (待验证)
- ⚠️ **结果文件保存/加载 < 1秒（10MB以内）** (待验证)

### 1.5 兼容性验收 (9.3)
- ✅ 现有 Pipeline 模式正常工作
- ✅ 现有 API 接口无回退
- ⚠️ **不影响未使用任务管理功能的任务** (待验证)

---

## 2. 已发现的问题

### 2.1 恢复功能问题（已修复）

**问题描述**：
- 恢复暂停任务时，任务从头开始执行，而不是从暂停阶段继续
- 原因：`get_cached_state_for_retry` 要求重试阶段本身的检查点必须存在

**修复方案**：
```python
# persistent_store.py (第886-899行)
# 修复前：要求 retry_stage 的检查点存在
if retry_stage_index is None:
    logger.warning(f"Retry stage not found: {retry_stage_id}")
    return None

# 修复后：使用最后已完成阶段的 index + 1
if retry_stage_index is None:
    max_completed_index = -1
    for cp in checkpoints:
        if cp["stage_status"] == "completed" and cp["stage_index"] > max_completed_index:
            max_completed_index = cp["stage_index"]
    
    if max_completed_index >= 0:
        retry_stage_index = max_completed_index + 1
        logger.info(f"Retry stage {retry_stage_id} not found in checkpoints, using index {retry_stage_index}")
    else:
        logger.warning(f"No completed checkpoints found, cannot load cached state")
        return None
```

**影响范围**：
- 规则挖掘任务（专家模式暂停/恢复）
- 评分卡开发任务（专家模式暂停/恢复）
- 所有使用 Pipeline 重试逻辑的任务

**验证方法**：
```python
# 测试用例：test_resume_bug.py::test_cached_state_fix()
def test_cached_state_fix():
    """
    场景：
    1. preprocessing 阶段完成（有检查点）
    2. feature_engineering 阶段还没执行（无检查点）
    3. 调用 get_cached_state_for_retry(execution_id, "feature_engineering")

    期望：
    - 不应该返回 None
    - 应该返回包含 preprocessing 阶段输出的缓存
    """
    # 实现见 tests/test_resume_bug.py
```

---

### 2.2 状态转换时机问题（已修复）

**问题描述**：
- `_run_task` 方法开始时立即设置 `context.status = ExecutionStatus.RUNNING`
- 导致恢复逻辑判断失败（因为状态不再是 PAUSED）
- `start_from_stage` 被设置为 None，任务从头开始

**修复方案**：
```python
# executor.py (第680-690行)
# 修复前：立即修改状态
context.status = ExecutionStatus.RUNNING
context.started_at = datetime.now()

# 修复后：先保存原始状态，延迟修改
original_status = context.status
is_resuming_from_pause = (original_status == ExecutionStatus.PAUSED)

# 设置启动时间
context.started_at = datetime.now()

# 在恢复逻辑判断完成后才设置状态为 RUNNING
if is_resuming_from_pause and start_from_stage:
    # 更新状态为 RUNNING，避免再次触发暂停逻辑
    context.status = ExecutionStatus.RUNNING
    context.message = "任务已恢复执行"
    ExecutionStore.update(context)
else:
    # 非恢复任务，设置状态为 RUNNING
    if context.status != ExecutionStatus.RUNNING:
        context.status = ExecutionStatus.RUNNING
        context.message = "任务正在执行"
        ExecutionStore.update(context)
```

**影响范围**：
- 所有暂停/恢复场景

**验证方法**：
```python
# 测试用例：test_resume_bug.py::test_executor_resume_logic()
def test_executor_resume_logic():
    """
    场景：
    1. context 初始状态为 PAUSED，current_stage 为 "preprocessing"
    2. preprocessing 阶段已完成
    3. 恢复逻辑检查状态

    期望：
    - 在状态判断完成前，status 应该是 PAUSED
    - 恢复逻辑应该设置 start_from_stage = "feature_engineering"
    - 在恢复逻辑完成后，status 才变为 RUNNING
    """
    # 实现见 tests/test_resume_bug.py
```

---

## 3. 待测试的关键场景

### 3.1 专家模式暂停/恢复（最高优先级）

**场景描述**：
```
1. 新建规则挖掘任务（专家模式）
2. 执行到 preprocessing 阶段完成
3. 专家模式自动暂停
4. 点击"继续"
5. 期望：从 feature_engineering 阶段继续，不重复执行 preprocessing
```

**关键验证点**：
- ✅ 恢复 API 正确返回 200
- ✅ 后台任务正确启动
- ⚠️ **从持久化存储加载 context** (关键)
- ⚠️ **识别 PAUSED 状态** (关键)
- ⚠️ **计算 start_from_stage = "feature_engineering"** (关键)
- ⚠️ **加载预处理阶段的缓存数据** (关键)
- ⚠️ **跳过 preprocessing 阶段** (关键)
- ⚠️ **从 feature_engineering 阶段开始执行** (关键)
- ⚠️ **不触发 preprocessing 的专家模式暂停** (关键)
- ⚠️ **总进度保持在 14% 左右** (2/14 阶段)

**日志关键点**：
```
✅ [Resume] Loading context from persistent storage for resume
✅ [Resume] Loaded and restored context: status=ExecutionStatus.PAUSED, current_stage=preprocessing
✅ [SOP] Original status: ExecutionStatus.PAUSED, is_resuming_from_pause: True
✅ [SOP] Task is paused with current_stage: preprocessing
✅ [SOP] Paused stage preprocessing completed, resuming from next stage: feature_engineering
✅ [SOP] Updated context status to RUNNING for resumable execution
✅ [Pipeline] Restoring from cached state, skipping to stage: feature_engineering
✅ [Pipeline] Loaded cached state for resume
✅ [Pipeline] Stage preprocessing completed (before retry stage, skipping pause)
```

**可能的问题**：
1. ❌ 缓存加载失败（`cached_state = None`）
   - 原因：`get_cached_state_for_retry` 返回 None
   - 修复：已修复（见 2.1）

2. ❌ 状态判断失败
   - 原因：`context.status` 过早变为 RUNNING
   - 修复：已修复（见 2.2）

3. ❌ Pipeline 仍然执行 preprocessing
   - 原因：`should_skip_stage('preprocessing')` 返回 False
   - 可能原因：
     - `retry_start_idx` 计算错误
     - `cached_state` 加载失败
     - Pipeline 判断逻辑错误

4. ❌ 仍然触发 preprocessing 的专家模式暂停
   - 原因：`is_before_retry_stage('preprocessing')` 返回 False
   - 可能原因：
     - `retry_start_idx` 计算错误
     - `_skip_expert_pause` 标记未正确传递

---

### 3.2 跨后端重启恢复（中等优先级）

**场景描述**：
```
1. 新建任务并执行到某个阶段
2. 暂停任务
3. 重启后端服务
4. 点击"继续"
5. 期望：任务能正常恢复并继续执行
```

**关键验证点**：
- ✅ `ExecutionStore` 内存缓存被清空（重启后）
- ⚠️ **从持久化存储加载 context** (关键)
- ⚠️ **context 状态正确恢复** (关键)
- ⚠️ **阶段进度正确恢复** (关键)
- ⚠️ **数据正确加载** (关键)

**可能的问题**：
1. ❌ ExecutionStore 为空，context 无法加载
   - 原因：`ExecutionStore.get(execution_id)` 返回 None
   - 解决方案：`resume_execution` API 中强制从持久化存储加载

2. ❌ 数据丢失
   - 原因：`context.data` 为 None
   - 解决方案：从 `context.file_path` 重新加载数据

---

### 3.3 历史任务详情查看（中等优先级）

**场景描述**：
```
1. 执行一个任务（已完成或暂停）
2. 等待一段时间
3. 从历史记录列表点击该任务
4. 期望：能正确显示任务详情（参数、阶段进度、输出等）
```

**关键验证点**：
- ✅ 任务列表能正确显示该任务
- ⚠️ **任务详情能正确加载** (关键)
- ⚠️ **阶段输出预览能正确显示** (关键)
- ⚠️ **参数 tab 能正确显示** (关键)

**可能的问题**：
1. ❌ ExecutionStore 中找不到 context
   - 原因：任务完成后 context 被清理
   - 解决方案：使用持久化存储加载

2. ❌ 阶段输出预览丢失
   - 原因：`output_preview` 未正确保存或加载
   - 解决方案：确保 `output_preview` 保存到数据库和文件系统

---

### 3.4 多次暂停/恢复（低优先级）

**场景描述**：
```
1. 启动任务
2. 阶段1完成后暂停
3. 恢复
4. 阶段2完成后暂停
5. 再次恢复
6. 期望：每次都能正确从暂停点继续
```

**关键验证点**：
- ⚠️ **每次恢复都能正确设置 start_from_stage** (关键)
- ⚠️ **缓存状态能正确累积** (关键)
- ⚠️ **不重复执行已完成阶段** (关键)

---

## 4. 静态代码分析

### 4.1 恢复逻辑流程分析

**流程图**：
```
用户点击"继续"
    ↓
resume_execution API
    ↓
验证任务状态（必须是 paused）
    ↓
从持久化存储加载 context ← 关键步骤
    ↓
ExecutionStore.update(context)
    ↓
检查是否有正在运行的执行器
    ↓
如果没有，启动新的执行器
    ↓
executor.execute_async(..., execution_id=execution_id)
    ↓
execute_async 检查是否有现有 context
    ↓
找到已恢复的 context（来自 resume_execution）
    ↓
await asyncio.to_thread(self._run_task, context)
    ↓
_run_task:
    ├─ 保存原始状态（original_status）
    ├─ 检查是否从暂停恢复
    ├─ 如果是 PAUSED：
    │   ├─ 检查 current_stage 是否完成
    │   ├─ 如果完成：设置 start_from_stage = 下一个阶段
    │   └─ 如果未完成：设置 start_from_stage = current_stage
    └─ 设置状态为 RUNNING（在恢复逻辑完成后）
    ↓
Pipeline 执行：
    ├─ 加载缓存状态（cached_state）
    ├─ 判断 should_skip_stage
    ├─ 如果是重试阶段之前的阶段：跳过
    └─ 从 start_from_stage 开始执行
```

**关键点分析**：

1. **resume_execution API 的 context 加载**
   ```python
   # sop_api.py (第1777-1791行)
   context = PersistentExecutionStore.load_full_state(execution_id)
   ExecutionStore.update(context)  # 更新到内存存储
   ```
   ✅ 逻辑正确

2. **execute_async 的 context 获取**
   ```python
   # executor.py (第602-603行)
   if execution_id:
       context = ExecutionStore.get(execution_id)  # 从内存获取
   ```
   ✅ 逻辑正确（会获取到 resume_execution 设置的 context）

3. **_run_task 的恢复逻辑**
   ```python
   # executor.py (第858-911行)
   if context.status == ExecutionStatus.PAUSED and context.current_stage:
       paused_stage = context.stages.get(context.current_stage)
       if paused_stage and paused_stage.status == ExecutionStatus.COMPLETED:
           # 从下一个阶段开始
           start_from_stage = stage_order[paused_idx + 1]
   ```
   ✅ 逻辑正确（修复后）

4. **Pipeline 的缓存加载**
   ```python
   # rule_mining.py (第4307-4336行)
   if cached_state and start_from_stage and retry_start_idx > 0:
       df_processed = cached_state["df_processed"]
       results.update(cached_state["results"])
   ```
   ✅ 逻辑正确（如果缓存加载成功）

5. **Pipeline 的阶段跳过**
   ```python
   # rule_mining.py (第4338-4358行)
   def should_skip_stage(stage_id):
       return stage_idx < retry_start_idx
   ```
   ✅ 逻辑正确

**潜在问题**：

1. ❌ **问题：Pipeline 判断重试模式时，`retry_start_idx` 可能错误**
   ```python
   # rule_mining.py (第4295-4302行)
   retry_start_idx = -1
   if start_from_stage:
       if start_from_stage in stage_order:
           retry_start_idx = stage_order.index(start_from_stage)
       else:
           logger.warning(f"[Pipeline] Unknown start_from_stage: {start_from_stage}")
   ```
   ⚠️ **如果 `start_from_stage` 不在 `stage_order` 中，`retry_start_idx` 保持为 -1**
   ⚠️ **这会导致 `should_skip_stage` 始终返回 False**

   **原因**：
   - 规则挖掘的 `stage_order` 可能和实际执行的阶段ID不一致
   - 或者 `start_from_stage` 的值有问题

   **解决方案**：
   ```python
   # 添加调试日志
   logger.info(f"[Pipeline] start_from_stage: {start_from_stage}, stage_order: {stage_order}")
   logger.info(f"[Pipeline] retry_start_idx: {retry_start_idx}")
   ```

2. ❌ **问题：`cached_state` 加载可能失败**
   ```python
   # executor.py (第914-922行)
   cached_state = PersistentExecutionStore.get_cached_state_for_retry(
       context.execution_id, start_from_stage
   )
   if cached_state:
       logger.info(f"[SOP] Loaded cached state for resume")
   ```
   ⚠️ **如果 `cached_state` 为 None，Pipeline 会从头开始执行**

   **原因**：
   - `get_cached_state_for_retry` 返回 None
   - 已经修复（见 2.1）

---

### 4.2 Pipeline 重试逻辑分析

**Pipeline 阶段顺序（规则挖掘）**：
```python
stage_order = [
    'preprocessing',         # 0
    'feature_engineering',   # 1
    'generating_rules',      # 2
    'rule_filtering',        # 3 (合并原 filtering_rules + evaluating_rules)
    'selecting_rules',       # 4
    'report_generation'      # 5
]
```

**恢复场景**：
```
场景：preprocessing 完成，feature_engineering 未执行
- start_from_stage = "feature_engineering"
- retry_start_idx = 1
- 应该跳过的阶段：index < 1，即 preprocessing (index=0)
```

**Pipeline 判断逻辑**：
```python
# rule_mining.py (第4338-4348行)
def should_skip_stage(stage_id):
    if retry_start_idx < 0:
        return False  # 没有重试，不跳过
    if not cached_state:
        return False  # 没有缓存，不跳过
    if stage_id not in stage_order:
        return False
    stage_idx = stage_order.index(stage_id)
    return stage_idx < retry_start_idx  # 小于重试阶段的索引
```

**验证**：
- `should_skip_stage('preprocessing')`:
  - `stage_idx = 0`
  - `retry_start_idx = 1`
  - `0 < 1` → **True** ✅

- `should_skip_stage('feature_engineering')`:
  - `stage_idx = 1`
  - `retry_start_idx = 1`
  - `1 < 1` → **False** ✅

- `should_skip_stage('generating_rules')`:
  - `stage_idx = 2`
  - `retry_start_idx = 1`
  - `2 < 1` → **False** ✅

**结论**：逻辑正确 ✅

---

### 4.3 专家模式暂停逻辑分析

**专家模式暂停触发**：
```python
# executor.py (第1050-1080行)
def _check_expert_mode_pause(self, context, stage_id):
    if context.interaction_mode != "expert":
        return False
    
    stage = context.stages.get(stage_id)
    if stage and stage.status == ExecutionStatus.COMPLETED:
        # 检查是否在重试阶段之前
        if not hasattr(context, '_executed_retry_stages'):
            return True
        
        if stage_id not in context._executed_retry_stages:
            return True
    
    return False
```

**跳过专家模式暂停的标记**：
```python
# rule_mining.py (第4371-4377行)
if is_before_retry_stage(stage_id) and progress >= 100:
    if output_preview is None:
        output_preview = {}
    output_preview['_skip_expert_pause'] = True  # 添加标记
    logger.info(f"[Pipeline] Stage {stage_id} completed (before retry stage, skipping pause)")
```

**问题分析**：
1. ❌ **问题：`_executed_retry_stages` 可能未正确设置**
   - 修复后的代码应该在恢复逻辑中设置
   - 需要验证是否正确设置

2. ❌ **问题：`output_preview['_skip_expert_pause']` 标记可能未传递**
   - 需要验证标记是否正确传递到 `_check_expert_mode_pause`
   - 需要验证 `_check_expert_mode_pause` 是否正确处理标记

---

## 5. 测试建议

### 5.1 立即测试（高优先级）

1. **专家模式暂停/恢复**
   ```bash
   # 1. 重启后端
   # 2. 新建规则挖掘任务（专家模式）
   # 3. 等待 preprocessing 完成
   # 4. 点击"继续"
   # 5. 观察日志和行为
   ```

   **关键日志**：
   ```
   [Resume] Loaded and restored context: exec-xxx, status=ExecutionStatus.PAUSED
   [SOP] Original status: ExecutionStatus.PAUSED, is_resuming_from_pause: True
   [SOP] Paused stage preprocessing completed, resuming from next stage: feature_engineering
   [Pipeline] Restoring from cached state, skipping to stage: feature_engineering
   [Pipeline] Stage preprocessing completed (before retry stage, skipping pause)
   ```

   **验证点**：
   - ✅ 是否跳过 preprocessing
   - ✅ 是否从 feature_engineering 开始
   - ✅ 是否不触发暂停
   - ✅ 总进度是否保持在 14% 左右

2. **跨后端重启恢复**
   ```bash
   # 1. 启动任务并暂停
   # 2. 重启后端
   # 3. 点击"继续"
   # 4. 观察是否能恢复
   ```

### 5.2 性能测试（中优先级）

1. **数据库写入性能**
2. **数据库查询性能**
3. **结果文件保存/加载性能**

### 5.3 兼容性测试（低优先级）

1. **不使用任务管理的任务**
2. **旧格式记录的兼容性**
3. **多种任务类型的支持**

---

## 6. 总结

### 6.1 已修复的问题
1. ✅ `get_cached_state_for_retry` 当重试阶段不存在时返回 None
2. ✅ `_run_task` 过早修改状态导致恢复逻辑失败

### 6.2 待验证的问题
1. ⚠️ 专家模式暂停/恢复的完整流程
2. ⚠️ Pipeline 重试逻辑的 `retry_start_idx` 计算
3. ⚠️ 专家模式暂停跳过标记的传递和处理
4. ⚠️ 跨后端重启恢复

### 6.3 建议的测试方案
1. 创建完整的集成测试（`test_task_manager_complete.py`）
2. 添加详细的调试日志
3. 使用静态代码分析工具（如 mypy, pylint）
4. 实现自动化测试脚本

---

## 7. 附录

### 7.1 相关文件
- `deepanalyze/core/task_manager/persistent_store.py` - 持久化存储
- `deepanalyze/analysis/task_SOP/executor.py` - 执行器
- `deepanalyze/analysis/task_SOP/rule_mining.py` - 规则挖掘 Pipeline
- `API/sop_api.py` - API 接口

### 7.2 相关函数
- `PersistentExecutionStore.get_cached_state_for_retry()` - 获取重试缓存
- `SOPExecutor._run_task()` - 任务执行
- `RuleMiningPipeline.__call__()` - Pipeline 执行
- `resume_execution()` - 恢复 API

### 7.3 相关类
- `ExecutionContext` - 执行上下文
- `ExecutionStatus` - 执行状态
- `TaskStatus` - 任务状态
- `StageProgress` - 阶段进度
