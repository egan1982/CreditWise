# useAIAnalysis Hook 重构设计

> 分支：`feature/intranet-multiuser`
> 状态：📋 草稿（待 autoplan 审查）
> 优先级：P1（技术债，阻塞 HT 验证）
> 工作量估算：1天

---

## 1. 问题陈述

### 1.1 现状

`StageOutputPreview.tsx`（5000+ 行）中 AI 分析状态管理有 **19 个 Phase 的补丁叠加**，4 个关键 state 分散在 6 个不同的 effect 和回调中被设置：

| State | 设置位置（6处） |
|-------|--------------|
| `aiAnalysis` | useState 初始化、initialLoad effect、stageId 变更 effect、recordId 变更 effect、status→running effect、流式输出、重试回调 |
| `hasTriggeredAnalysis` | 同上 6 处 |
| `suggestedParams` | fetchAnalysisFromAPI 所有调用点、流式完成后 |
| `isLoadingCachedAnalysis` | 所有异步加载入口 |

### 1.2 根本问题

触发 AI 分析的条件：
```
status=completed && !hasTriggeredAnalysis && !aiAnalysis && !isLoadingCachedAnalysis
```

任何一个 effect 执行顺序不符合预期（React 时序），就会导致：
- 要么不触发（重试后 AI 评估不重新生成）
- 要么用旧数据触发（切换阶段后显示上一版 AI 分析）
- 要么 suggestedParams 丢失（切换后建议卡片消失）

### 1.3 直接诱因

本次实现 `ai_suggest_retry` 功能时，新增了：
- `retryPendingOutputRef`（等待新 outputPreview）
- `suggested_params` 的多处恢复逻辑
- 重试回调里的清除/删除逻辑

与原有 19 个 Phase 的状态管理产生了复杂的时序冲突。

---

## 2. 解决方案

### 2.1 提取 `useAIAnalysis` hook

将所有 AI 分析相关的 state + effect + 回调提取为一个独立 hook：

```typescript
// demo/chat/hooks/useAIAnalysis.ts

interface UseAIAnalysisOptions {
  recordId: string | undefined;
  stageId: string;
  status: string;            // "pending" | "running" | "completed" | "failed"
  outputPreview: any;
  isExpertMode: boolean;
  selectedModel: string;
  taskType?: string;
  stageData?: any;
  taskResult?: any;
  onRetryStage?: Function;
}

interface UseAIAnalysisReturn {
  // 状态
  aiAnalysis: string;
  suggestedParams: Record<string, unknown> | null;
  isAnalyzing: boolean;
  isLoadingCachedAnalysis: boolean;
  
  // 操作
  performAnalysis: () => void;       // 手动触发（重新分析按钮）
  clearAndReset: () => void;         // 重试前调用（清 state + cache）
  
  // 快照相关
  getSnapshotAnalysis: (snapshot: StageSnapshot) => string | null;
}

export function useAIAnalysis(options: UseAIAnalysisOptions): UseAIAnalysisReturn
```

### 2.2 状态机（明确的单向流）

```
IDLE
  ↓ (status=completed + isExpertMode + !triggered)
LOADING_CACHE
  ↓ (API有数据) → READY (aiAnalysis=cached, suggestedParams=restored)
  ↓ (API无数据) → TRIGGERING
TRIGGERING
  ↓ (300ms delay)
ANALYZING (streaming)
  ↓ (完成)
READY (aiAnalysis=clean, suggestedParams=parsed)

重试发生：
READY → IDLE (clearAndReset 调用)
  注意：清除顺序：先触发 retryStage（后端打快照），再清 state
```

### 2.3 核心设计原则

1. **状态单一来源**：所有 AI 分析 state 只在 hook 内部修改
2. **明确的生命周期**：`status → running` 时自动进入 IDLE，不需要外部主动清除
3. **加载优先于触发**：LOADING_CACHE 阶段阻塞 TRIGGERING，杜绝竞态
4. **`running` 时不加载**：阶段执行中跳过所有加载逻辑
5. **不删 DB**：重试时只清 sessionStorage，DB 旧分析由后端快照保存

### 2.4 快照 AI 分析展示

历史快照的 `ai_analysis` 字段直接从 snapshot 对象读取，不需要经过 hook 的状态机：

```typescript
// StageOutputPreview.tsx
const displayedAnalysis = activeSnapshot
  ? activeSnapshot.ai_analysis    // 快照：直接读字段
  : aiAnalysis;                   // 当前：hook 管理
```

---

## 3. 实现分解

| 任务 | 文件 | 工作量 |
|------|------|--------|
| B1：后端单元测试（SUGGESTED_PARAMS 解析/剥离/快照/GET接口） | `tests/test_ai_suggest_retry.py` | 2h |
| F1：创建 `useAIAnalysis.ts` hook（状态机 + 所有 effect） | `demo/chat/hooks/useAIAnalysis.ts` | 3h |
| F2：`StageOutputPreview.tsx` 替换为使用 hook（移除原有散落 state/effect） | `demo/chat/components/sop/StageOutputPreview.tsx` | 2h |
| F3：`SuggestedParamsCard` 的重试回调使用 `clearAndReset` | `demo/chat/components/sop/SuggestedParamsCard.tsx` | 0.5h |
| T1：TypeScript 编译通过 + lint 零报错 | — | 0.5h |
| T2：整理目视验证清单（HT-01~05 + 回归） | — | 0.5h |
| **合计** | | **~8.5h（约1天）** |

---

## 4. 不在范围内

| 项目 | 原因 |
|------|------|
| StageOutputPreview.tsx 整体重构 | 只提取 AI 分析相关 state，不动其他逻辑 |
| 版本选择器/快照展示逻辑 | 已正确工作，不纳入 |
| 后端 API 改动 | 后端逻辑已稳定（快照、解析、参数注入） |

---

## 5. 风险

| 风险 | 缓解 |
|------|------|
| hook 提取遗漏某个 effect | 先写测试（B1），hook 实现对齐测试 |
| StageOutputPreview 依赖内部 state | 逐步替换，TypeScript 编译兜底 |
| 快照展示的 `ai_analysis` 路径变化 | 单独处理，不经过 hook |
