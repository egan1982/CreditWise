# 暂停/恢复功能测试指南

> 目的：验证修复后的暂停/恢复功能是否正常工作
> 日期: 2025-01-05

---

## 1. 测试前准备

### 1.1 重启后端服务

```bash
# 停止当前运行的后端服务
# 然后重新启动
cd c:\Users\fjzheng\portable-dev-env\workspace\DeepAnalyze
python main.py
```

### 1.2 准备测试数据

使用现有的测试数据文件：
- `starrel_train.csv`

### 1.3 打开浏览器

访问 DeepAnalyze 前端页面（通常是 http://localhost:3000）

---

## 2. 测试步骤

### 2.1 新建规则挖掘任务（专家模式）

1. 点击"规则挖掘"任务
2. 选择"专家模式"
3. 配置参数：
   ```
   - 目标列: label
   - 最小提升度: 3.5
   - 最大命中率过滤: 0.03
   - 最大命中率选择: 0.2
   - 启用特征工程: true
   - 挖掘模式: multi
   - 分箱数: 10
   - 分箱方法: quantile
   ```
4. 点击"开始执行"

### 2.2 等待预处理阶段完成

1. 观察任务进度
2. 等待"数据预处理"阶段完成（进度达到约 14%）
3. **期望**：任务自动暂停（专家模式）

### 2.3 验证暂停状态

检查以下内容：
- ✅ 任务状态显示为"已暂停"
- ✅ 总进度约 14%（2/14 阶段）
- ✅ 当前阶段为"特征工程"（等待中）
- ✅ "数据预处理"阶段状态为"已完成"
- ✅ 点击"数据预处理"阶段，能看到输出预览

### 2.4 点击"继续"

1. 点击任务卡片上的"继续"按钮
2. 观察任务行为

### 2.5 观察关键日志

在终端中查找以下关键日志：

#### A. 恢复 API 日志
```
[Resume] Resume request received for execution: exec-xxx
[Resume] Task is paused, record: rec-xxx
[Resume] Loading context from persistent storage for resume: exec-xxx
[Resume] Loaded and restored context: exec-xxx, status=ExecutionStatus.PAUSED, current_stage=preprocessing
```

#### B. Executor 恢复日志
```
[SOP] Original status: ExecutionStatus.PAUSED, is_resuming_from_pause: True
[SOP] Task is paused with current_stage: preprocessing
[SOP] Paused stage preprocessing completed, resuming from next stage: feature_engineering
[SOP] Added feature_engineering to _executed_retry_stages for resume
[SOP] Updated context status to RUNNING for resumable execution: exec-xxx
[SOP] Loaded cached state for resume: ['stage_outputs', 'results', 'df_processed', 'last_completed_stage']
[SOP] Cached stage_outputs keys: ['preprocessing']
[SOP] Last completed stage: preprocessing
```

#### C. Pipeline 恢复日志
```
[Pipeline] Stage retry mode: starting from feature_engineering (index=1)
[Pipeline] Restoring from cached state, skipping to stage: feature_engineering
[Pipeline] retry_start_idx=1, stage_order=['preprocessing', 'feature_engineering', ...]
[Pipeline] Restoring stage_outputs: ['preprocessing']
[Pipeline] Processing stage_output for preprocessing, keys: [...]
[Pipeline] Restored output_preview for stage: preprocessing, has _skip_expert_pause: False
[Pipeline] Restored df_processed: 23349 rows, 85 cols
[Pipeline] Restored results keys: [...]
```

#### D. 阶段跳过日志
```
[Pipeline] should_skip_stage(preprocessing): True (stage_idx=0, retry_start_idx=1)
[Pipeline] Skipping preprocessing stage (using cached data), restoring output_preview
[Pipeline] Using restored output_preview for preprocessing, keys: [...]
```

#### E. 专家模式暂停跳过日志
```
[Expert Mode] Stage preprocessing has _skip_expert_pause flag, skipping pause
```

#### F. 特征工程阶段开始
```
[Pipeline] should_skip_stage(feature_engineering): False (stage_idx=1, retry_start_idx=1)
[Pipeline] Stage feature_engineering starting...
```

---

## 3. 验证点

### 3.1 功能验证

| 验证点 | 期望行为 | 实际行为 | 结果 |
|---------|---------|---------|------|
| 恢复 API 正常返回 | HTTP 200 | | ⬜ |
| 后台任务启动 | 无错误 | | ⬜ |
| 从持久化存储加载 context | 日志显示 | | ⬜ |
| 识别 PAUSED 状态 | 日志显示 | | ⬜ |
| 计算 start_from_stage | feature_engineering | | ⬜ |
| 加载预处理阶段的缓存 | 日志显示 | | ⬜ |
| 跳过 preprocessing 阶段 | 日志显示 | | ⬜ |
| 不触发 preprocessing 暂停 | 日志显示 | | ⬜ |
| 从 feature_engineering 开始 | 日志显示 | | ⬜ |
| 总进度保持在 14% | 进度条显示 | | ⬜ |
| feature_engineering 执行 | 阶段进度变化 | | ⬜ |

### 3.2 日志验证

| 关键日志 | 是否存在 | 结果 |
|---------|---------|------|
| `[SOP] Original status: ExecutionStatus.PAUSED` | | ⬜ |
| `[SOP] resuming from next stage: feature_engineering` | | ⬜ |
| `[SOP] Added feature_engineering to _executed_retry_stages` | | ⬜ |
| `[SOP] Loaded cached state for resume` | | ⬜ |
| `[Pipeline] Restoring from cached state` | | ⬜ |
| `[Pipeline] should_skip_stage(preprocessing): True` | | ⬜ |
| `[Pipeline] Skipping preprocessing stage` | | ⬜ |
| `[Expert Mode] Stage preprocessing has _skip_expert_pause flag` | | ⬜ |
| `[Pipeline] should_skip_stage(feature_engineering): False` | | ⬜ |

---

## 4. 可能的问题和解决方案

### 4.1 问题：恢复后仍然执行 preprocessing

**现象**：
- 日志显示 `[Pipeline] should_skip_stage(preprocessing): False`
- 任务仍然执行 preprocessing 阶段

**可能原因**：
1. `retry_start_idx` 计算错误
2. `cached_state` 加载失败
3. `stage_order` 定义不正确

**解决方案**：
检查日志中：
- `[Pipeline] retry_start_idx=?` 应该是 1
- `[SOP] Loaded cached state for resume` 应该存在
- `[Pipeline] stage_order` 应该包含 `feature_engineering`

### 4.2 问题：仍然触发 preprocessing 暂停

**现象**：
- 跳过 preprocessing 后，仍然触发专家模式暂停

**可能原因**：
1. `_skip_expert_pause` 标记未正确添加
2. `_executed_retry_stages` 未正确设置
3. 标记传递失败

**解决方案**：
检查日志中：
- `[Pipeline] Using restored output_preview for preprocessing` 应该存在
- `[Expert Mode] Stage preprocessing has _skip_expert_pause flag` 应该存在
- `[SOP] Added feature_engineering to _executed_retry_stages` 应该存在

### 4.3 问题：总进度回退到 2%

**现象**：
- 恢复后总进度从 14% 回退到 2%

**可能原因**：
1. `preprocessing` 阶段被重新执行
2. 进度计算错误
3. 阶段权重问题

**解决方案**：
检查日志中：
- `[Pipeline] Skipping preprocessing stage` 应该存在（表示跳过）
- `[Pipeline] Stage preprocessing starting...` 不应该存在（表示未执行）

---

## 5. 测试结果记录

### 5.1 测试环境

- 后端版本: [填写]
- 前端版本: [填写]
- 数据文件: starrel_train.csv
- 测试时间: [填写]

### 5.2 测试结果

#### 测试1: 专家模式暂停/恢复

| 项目 | 结果 | 备注 |
|------|------|------|
| 恢复 API | ✅ / ❌ | |
| 从持久化加载 | ✅ / ❌ | |
| 状态识别 | ✅ / ❌ | |
| start_from_stage | ✅ / ❌ | |
| 缓存加载 | ✅ / ❌ | |
| 跳过 preprocessing | ✅ / ❌ | |
| 不触发暂停 | ✅ / ❌ | |
| 从 feature_engineering 开始 | ✅ / ❌ | |
| 总进度保持 | ✅ / ❌ | |

#### 测试2: 跨后端重启恢复

| 项目 | 结果 | 备注 |
|------|------|------|
| 重启后恢复 | ✅ / ❌ | |
| 状态保持 | ✅ / ❌ | |
| 数据加载 | ✅ / ❌ | |
| 继续执行 | ✅ / ❌ | |

---

## 6. 测试完成后的清理

### 6.1 清理测试数据

```bash
# 可选：删除测试生成的临时文件
# 保留执行状态用于后续分析
```

### 6.2 保存测试日志

```bash
# 保存测试日志用于问题分析
# 重点关注：
# - 恢复相关的日志
# - Pipeline 执行相关的日志
# - 专家模式暂停相关的日志
```

---

## 7. 联系方式

如有问题，请联系：
- 问题报告：在项目的 Issue 中提交
- 技术支持：联系开发团队

---

**测试指南版本**: 1.0
**创建日期**: 2025-01-05
