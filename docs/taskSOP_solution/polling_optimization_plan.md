# 任务状态轮询优化方案

> 创建时间：2026-01-14  
> 状态：待实施（临时方案已部署）

## 1. 问题背景

### 1.1 现象描述

任务暂停时，前端持续轮询后端状态接口，导致：
1. 终端日志快速刷新，难以定位关键信息
2. 用户无法复制终端内容进行调试
3. 即使状态已稳定，仍持续消耗网络和计算资源

### 1.2 触发场景

- 专家模式下阶段完成后自动暂停
- 用户手动暂停任务
- 页面刷新后加载暂停状态的历史任务

## 2. 分析过程

### 2.1 轮询机制作用分析

| 作用 | 说明 | 是否必需 |
|------|------|---------|
| 阶段状态及时更新 | 检测 pending → running → paused → completed | ✅ 必需 |
| 进度追踪 | 长时间阶段的实时进度反馈 | ✅ 必需（running时） |
| 错误检测 | 快速发现任务失败/异常 | ✅ 必需 |
| 用户交互响应 | 专家模式暂停等待确认 | ⚠️ paused后可停止 |

### 2.2 不同状态的轮询需求

| 状态 | 轮询需求 | 建议间隔 | 理由 |
|------|---------|---------|------|
| running | 高频 | 200-500ms | 追踪进度，及时响应完成 |
| paused | 低频/可停止 | 5000ms或停止 | 状态稳定，等待用户操作 |
| completed | 停止 | - | 无需更新 |
| failed | 停止 | - | 无需更新 |

### 2.3 场景影响分析

通过代码分析，识别出所有涉及轮询的场景：

| # | 场景 | 触发函数 | 当前行为 | 优化后影响 |
|---|------|---------|---------|-----------|
| 1 | 新任务启动 | `handleSOPExecute` | 设置 executionId，启动轮询 | ✅ 无影响（running状态正常轮询） |
| 2 | 任务正常完成 | `handleSOPComplete` | 清除 executionId，停止轮询 | ✅ 无影响（已有停止逻辑） |
| 3 | 任务执行中暂停 | 专家模式阶段完成 | 状态变 paused，轮询继续 | ⚠️ 需处理：状态稳定后停止 |
| 4 | 暂停后继续 | `handleResumeExecution` | 调用 resume API | ⚠️ 需处理：重启轮询 |
| 5 | 暂停后重试阶段 | `onRetryStage` | 调用 retryStage API | ⚠️ 需处理：重启轮询 |
| 6 | 页面刷新后加载暂停任务 | `handleViewTaskDetail` | 设置 executionId，启动轮询 | ⚠️ 需处理：状态稳定后停止 |
| 7 | 切换查看其他任务 | `handleViewTaskDetail` | 清除旧 executionId，设置新的 | ✅ 无影响（executionId变化触发新轮询） |
| 8 | 关闭任务详情 | `handleCloseResults` | 清除 executionId | ✅ 无影响 |
| 9 | 返回任务列表 | `handleBackToTaskList` | 清除 executionId | ✅ 无影响 |
| 10 | 跳过阶段 | `handleSkipStage` | 调用 skip API | ⚠️ 需处理：跳过后状态可能变化 |
| 11 | 聊天中确认任务 | `handleConfirmTask` | 设置 executionId，启动轮询 | ✅ 无影响（同场景1） |

### 2.4 关键问题识别

**问题**：轮询一旦停止，只有 `executionId` 变化才会重启 useEffect。

**场景 4/5/10 的问题**：
- 用户点击"继续/重试/跳过"后，`executionId` 不变
- 如果轮询已停止，无法自动感知后端状态变化
- 需要额外机制来重启轮询

## 3. 解决方案

### 3.1 方案设计

**核心思路**：
```
paused状态 → 快速轮询直到状态同步完成 → 停止轮询 → 等待用户操作 → 重启轮询
```

**实现机制**：通过 `pollTrigger` prop 控制轮询重启

### 3.2 TaskProgress.tsx 修改

```typescript
interface TaskProgressProps {
  // ... 现有 props
  pollTrigger?: number; // 改变此值会重启轮询
}

useEffect(() => {
  let pausedStableCount = 0; // 连续检测到 paused 的次数
  
  const pollStatus = async () => {
    const currentStatus = await sopService.getExecutionStatus(executionId);
    
    // ... 现有状态处理逻辑 ...
    
    if (currentStatus.status === "paused") {
      pausedStableCount++;
      if (pausedStableCount >= 2) {
        // 连续2次检测到 paused，状态已稳定，停止轮询
        console.log("[TaskProgress] Paused state stable, stopping poll");
        return; // 不再调度下一次轮询
      }
      nextInterval = 500; // 快速确认一次
    } else {
      pausedStableCount = 0; // 重置计数
    }
    
    // 继续下一次轮询
    if (isMounted) {
      pollTimeout = setTimeout(pollStatus, nextInterval);
    }
  };
  
  pollStatus();
  
  return () => { /* cleanup */ };
}, [executionId, pollTrigger]); // 添加 pollTrigger 依赖
```

### 3.3 three-panel-interface.tsx 修改

```typescript
// 新增状态
const [pollTrigger, setPollTrigger] = useState(0);

// 重启轮询函数
const restartPolling = () => setPollTrigger(prev => prev + 1);

// 场景4：继续执行
const handleResumeExecution = async () => {
  await sopService.resumeExecution(currentExecutionId);
  restartPolling(); // 重启轮询
  // ... 其他逻辑
};

// 场景5：重试阶段
onRetryStage={async (stageId) => {
  await sopService.retryStage(currentExecutionId, stageId);
  restartPolling(); // 重启轮询
}}

// 场景10：跳过阶段
const handleSkipStage = async (stageId: string) => {
  await sopService.skipStage(currentExecutionId, stageId);
  restartPolling(); // 重启轮询
  // ... 其他逻辑
};

// TaskProgress 组件
<TaskProgress
  executionId={currentExecutionId}
  pollTrigger={pollTrigger}  // 新增
  taskId={sopExecutionStatus?.task_id || selectedTaskId || undefined}
  onComplete={handleSOPComplete}
  onClose={handleCloseProgress}
  onStatusUpdate={handleSOPStatusUpdate}
/>
```

## 4. 风险评估

| 风险 | 等级 | 说明 | 缓解措施 |
|------|------|------|---------|
| 轮询停止后无法恢复 | 🟡 中 | 用户操作后无法感知状态 | 通过 pollTrigger 机制解决 |
| 遗漏需要重启轮询的场景 | 🟡 中 | 某些操作后轮询未重启 | 已全面分析，覆盖4个场景 |
| 状态稳定判断不准确 | 🟢 低 | 误判导致提前停止 | 连续2次检测，500ms间隔 |
| 与现有逻辑冲突 | 🟢 低 | 破坏现有功能 | 只增加停止/重启逻辑 |

## 5. 实施计划

### 5.1 进度跟踪

- [x] 问题分析和方案设计
- [x] paused 状态轮询间隔设为 5000ms（临时方案）
- [x] **决策确认：采用方案A（完整实现）**
- [ ] 实现 pollTrigger 机制（TaskProgress.tsx）
- [ ] 实现状态稳定后停止轮询（TaskProgress.tsx）
- [ ] 在用户操作处调用 restartPolling（three-panel-interface.tsx）
- [ ] 测试验证

### 5.2 测试用例

1. **场景3测试**：专家模式执行 → 阶段完成暂停 → 验证轮询停止
2. **场景4测试**：暂停状态 → 点击继续 → 验证轮询重启 → 状态正确更新
3. **场景5测试**：暂停状态 → 重试阶段 → 验证轮询重启 → 状态正确更新
6. **场景6测试**：页面刷新 → 加载暂停任务 → 验证轮询停止
7. **场景10测试**：暂停状态 → 跳过阶段 → 验证轮询重启

## 6. 相关文件

| 文件 | 修改内容 |
|------|---------|
| `demo/chat/components/sop/TaskProgress.tsx` | 添加 pollTrigger prop，实现状态稳定停止 |
| `demo/chat/components/three-panel-interface.tsx` | 添加 pollTrigger state，在操作处调用 restartPolling |
