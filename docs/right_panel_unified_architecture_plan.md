# Right Panel 统一架构优化计划

> 创建时间：2025-12-22  
> 状态：待实施  
> 优先级：中期优化  
> 前置依赖：Chat API 融合方案完成后

---

## 一、问题分析

### 1.1 当前架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Right Panel (Code 列)                            │
│                                                                         │
│  rightPanelMode 状态控制：                                              │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  "code" 模式 - 通用代码编辑器                                   │   │
│  │  ├─ 来源：点击 Chat 消息中的代码块                              │   │
│  │  ├─ 执行：调用 /execute/code API                                │   │
│  │  ├─ 组件：Monaco Editor (内联在 three-panel-interface.tsx)      │   │
│  │  └─ 状态：codeEditorContent, showCodeEditor, isExecutingCode    │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │  "preview" 模式 - SOP 阶段输出预览                              │   │
│  │  ├─ 来源：点击 SOP 阶段卡片                                     │   │
│  │  ├─ 功能：展示阶段结果 + 专家模式编辑                           │   │
│  │  └─ 组件：StageOutputPreview                                    │   │
│  │          ├─ StageCodeEditor (独立组件)                          │   │
│  │          ├─ StageParameterEditor                                │   │
│  │          └─ 各类数据可视化组件                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  "log" 模式（未完全实现）                                               │
│  └─ ExecutionLogPanel                                                  │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 识别的问题

#### 1.2.1 代码冗余

| 冗余项 | 位置1 | 位置2 | 影响 |
|--------|-------|-------|------|
| Monaco Editor 实例化 | `three-panel-interface.tsx` L3830-3860 | `StageCodeEditor.tsx` | 代码重复、维护成本高 |
| 代码执行函数 | `three-panel-interface.tsx` `executeCode()` | `StageCodeEditor.tsx` `executeCode()` | 逻辑重复 |
| 执行状态管理 | `isExecutingCode`, `codeExecutionResult` | `isExecuting`, `executionResult` | 状态分散 |

#### 1.2.2 架构问题

1. **职责不清**：`three-panel-interface.tsx` 同时承担布局和代码编辑逻辑
2. **状态分散**：代码编辑相关状态散落在主组件中
3. **扩展性差**：新增 Right Panel 模式需要修改主组件
4. **组件复用低**：`StageCodeEditor` 功能完善但未被复用

#### 1.2.3 用户体验问题

1. **模式切换不连贯**：从 "code" 切换到 "preview" 时，之前编辑的代码丢失
2. **上下文缺失**："code" 模式下无法关联 SOP 阶段信息
3. **结果展示不统一**：Chat 代码执行结果是纯文本，SOP 阶段结果是结构化可视化

---

## 二、优化目标

### 2.1 核心目标

1. **消除代码冗余**：统一代码编辑/执行组件
2. **清晰职责划分**：Right Panel 作为独立模块管理
3. **提升扩展性**：新增模式无需修改主组件
4. **改善用户体验**：模式切换保留上下文，结果展示统一

### 2.2 设计原则

- **单一职责**：每个组件只负责一件事
- **状态集中**：Right Panel 状态由专门的 Context/Store 管理
- **组件复用**：基础组件可在多个模式中复用
- **渐进增强**：保持向后兼容，逐步迁移

---

## 三、目标架构

### 3.1 架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    RightPanelProvider (Context)                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 状态管理：                                                      │   │
│  │ - mode: "empty" | "code" | "preview" | "result" | "log"         │   │
│  │ - codeContext: { code, language, source, stageId? }             │   │
│  │ - executionState: { isExecuting, result, error }                │   │
│  │ - previewContext: { stageId, stageName, outputPreview }         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        RightPanel (容器组件)                            │
│                                                                         │
│  根据 mode 渲染对应子组件：                                             │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  "empty"   → <EmptyState />                                     │   │
│  │  "code"    → <UnifiedCodeEditor />                              │   │
│  │  "preview" → <StageOutputPreview />                             │   │
│  │  "result"  → <ExecutionResultView />                            │   │
│  │  "log"     → <ExecutionLogPanel />                              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
            │ CodeEditor  │ │ ResultView  │ │ DataViz     │
            │ (基础组件)  │ │ (基础组件)  │ │ (基础组件)  │
            └─────────────┘ └─────────────┘ └─────────────┘
```

### 3.2 组件职责

| 组件 | 职责 | 复用场景 |
|------|------|---------|
| `RightPanelProvider` | 状态管理、跨组件通信 | 全局 |
| `RightPanel` | 模式路由、布局容器 | 全局 |
| `UnifiedCodeEditor` | 代码编辑/执行 | Chat 代码块、SOP 阶段代码 |
| `ExecutionResultView` | 执行结果展示 | Chat 执行结果、SOP 阶段结果 |
| `StageOutputPreview` | SOP 阶段预览（保留） | SOP 专用 |
| `EmptyState` | 空状态提示 | 初始状态 |

### 3.3 状态设计

```typescript
// types/rightPanel.ts

export type RightPanelMode = "empty" | "code" | "preview" | "result" | "log";

export interface CodeContext {
  code: string;
  language: string;
  source: "chat" | "sop" | "manual";  // 代码来源
  stageId?: string;                    // 关联的 SOP 阶段
  readOnly?: boolean;
}

export interface ExecutionState {
  isExecuting: boolean;
  result: string | null;
  error: string | null;
  executionId?: string;
}

export interface PreviewContext {
  stageId: string;
  stageName: string;
  status: string;
  outputPreview: Record<string, any> | null;
  stageData?: StageEditableData;
}

export interface RightPanelState {
  mode: RightPanelMode;
  codeContext: CodeContext | null;
  executionState: ExecutionState;
  previewContext: PreviewContext | null;
  
  // 历史记录（支持模式切换时保留上下文）
  history: {
    code?: CodeContext;
    preview?: PreviewContext;
  };
}

export interface RightPanelActions {
  setMode: (mode: RightPanelMode) => void;
  openCode: (context: CodeContext) => void;
  openPreview: (context: PreviewContext) => void;
  executeCode: (code: string, sessionId: string) => Promise<void>;
  clearPanel: () => void;
  goBack: () => void;  // 返回上一个模式
}
```

---

## 四、实施计划

### 4.1 阶段划分

```
Phase 1: 基础设施 (2-3天)
    │
    ├─ 创建 RightPanelProvider
    ├─ 创建类型定义
    └─ 创建 useRightPanel hook
    
Phase 2: 组件重构 (3-4天)
    │
    ├─ 创建 UnifiedCodeEditor
    ├─ 创建 ExecutionResultView
    ├─ 创建 RightPanel 容器
    └─ 重构 StageOutputPreview 适配新架构
    
Phase 3: 集成迁移 (2-3天)
    │
    ├─ 迁移 three-panel-interface.tsx
    ├─ 移除冗余代码
    └─ 更新相关调用点
    
Phase 4: 测试验证 (1-2天)
    │
    ├─ 功能回归测试
    ├─ 边界情况处理
    └─ 性能优化
```

### 4.2 详细任务

#### Phase 1: 基础设施

| 任务 | 文件 | 说明 |
|------|------|------|
| 1.1 创建类型定义 | `demo/chat/types/rightPanel.ts` | 定义所有类型接口 |
| 1.2 创建 Context | `demo/chat/contexts/RightPanelContext.tsx` | 状态管理 Provider |
| 1.3 创建 Hook | `demo/chat/hooks/useRightPanel.ts` | 封装常用操作 |
| 1.4 创建执行 Hook | `demo/chat/hooks/useCodeExecution.ts` | 统一代码执行逻辑 |

#### Phase 2: 组件重构

| 任务 | 文件 | 说明 |
|------|------|------|
| 2.1 创建 UnifiedCodeEditor | `demo/chat/components/right-panel/UnifiedCodeEditor.tsx` | 统一代码编辑器 |
| 2.2 创建 ExecutionResultView | `demo/chat/components/right-panel/ExecutionResultView.tsx` | 统一结果展示 |
| 2.3 创建 EmptyState | `demo/chat/components/right-panel/EmptyState.tsx` | 空状态组件 |
| 2.4 创建 RightPanel | `demo/chat/components/right-panel/RightPanel.tsx` | 容器组件 |
| 2.5 创建 index 导出 | `demo/chat/components/right-panel/index.ts` | 统一导出 |
| 2.6 适配 StageOutputPreview | `demo/chat/components/sop/StageOutputPreview.tsx` | 接入新 Context |

#### Phase 3: 集成迁移

| 任务 | 文件 | 说明 |
|------|------|------|
| 3.1 包装 Provider | `demo/chat/components/three-panel-interface.tsx` | 添加 RightPanelProvider |
| 3.2 替换 Right Panel | `demo/chat/components/three-panel-interface.tsx` | 使用新 RightPanel 组件 |
| 3.3 迁移代码块点击 | `demo/chat/components/three-panel-interface.tsx` | 使用 openCode() |
| 3.4 迁移阶段卡片点击 | `demo/chat/components/three-panel-interface.tsx` | 使用 openPreview() |
| 3.5 移除冗余状态 | `demo/chat/components/three-panel-interface.tsx` | 删除旧状态变量 |
| 3.6 移除冗余函数 | `demo/chat/components/three-panel-interface.tsx` | 删除旧 executeCode 等 |

#### Phase 4: 测试验证

| 任务 | 说明 |
|------|------|
| 4.1 Chat 代码块编辑测试 | 点击代码块 → 编辑 → 执行 → 查看结果 |
| 4.2 SOP 阶段预览测试 | 执行 SOP → 点击阶段 → 查看预览 → 编辑参数/代码 |
| 4.3 模式切换测试 | code ↔ preview 切换，验证上下文保留 |
| 4.4 边界情况测试 | 空代码、执行失败、网络错误等 |
| 4.5 性能测试 | 大代码块、频繁切换 |

---

## 五、关键代码示例

### 5.1 RightPanelContext

```typescript
// demo/chat/contexts/RightPanelContext.tsx

"use client";

import React, { createContext, useContext, useReducer, useCallback } from "react";
import { RightPanelState, RightPanelActions, RightPanelMode, CodeContext, PreviewContext } from "@/types/rightPanel";
import { getApiUrl, API_URLS } from "@/lib/config";

const initialState: RightPanelState = {
  mode: "empty",
  codeContext: null,
  executionState: {
    isExecuting: false,
    result: null,
    error: null,
  },
  previewContext: null,
  history: {},
};

type Action =
  | { type: "SET_MODE"; payload: RightPanelMode }
  | { type: "OPEN_CODE"; payload: CodeContext }
  | { type: "OPEN_PREVIEW"; payload: PreviewContext }
  | { type: "SET_EXECUTING"; payload: boolean }
  | { type: "SET_RESULT"; payload: { result?: string; error?: string } }
  | { type: "CLEAR" }
  | { type: "GO_BACK" };

function reducer(state: RightPanelState, action: Action): RightPanelState {
  switch (action.type) {
    case "SET_MODE":
      return { ...state, mode: action.payload };
    
    case "OPEN_CODE":
      return {
        ...state,
        mode: "code",
        codeContext: action.payload,
        history: { ...state.history, code: action.payload },
      };
    
    case "OPEN_PREVIEW":
      return {
        ...state,
        mode: "preview",
        previewContext: action.payload,
        history: { ...state.history, preview: action.payload },
      };
    
    case "SET_EXECUTING":
      return {
        ...state,
        executionState: { ...state.executionState, isExecuting: action.payload },
      };
    
    case "SET_RESULT":
      return {
        ...state,
        executionState: {
          ...state.executionState,
          isExecuting: false,
          result: action.payload.result || null,
          error: action.payload.error || null,
        },
      };
    
    case "CLEAR":
      return initialState;
    
    case "GO_BACK":
      // 返回上一个有内容的模式
      if (state.history.code && state.mode !== "code") {
        return { ...state, mode: "code", codeContext: state.history.code };
      }
      return { ...state, mode: "empty" };
    
    default:
      return state;
  }
}

const RightPanelContext = createContext<{
  state: RightPanelState;
  actions: RightPanelActions;
} | null>(null);

export function RightPanelProvider({ children, sessionId }: { children: React.ReactNode; sessionId: string }) {
  const [state, dispatch] = useReducer(reducer, initialState);

  const executeCode = useCallback(async (code: string) => {
    dispatch({ type: "SET_EXECUTING", payload: true });
    
    try {
      const response = await fetch(getApiUrl(API_URLS.EXECUTE_CODE), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code, session_id: sessionId }),
      });

      if (response.ok) {
        const data = await response.json();
        dispatch({ type: "SET_RESULT", payload: { result: data.output || data.result } });
      } else {
        dispatch({ type: "SET_RESULT", payload: { error: "Failed to execute code" } });
      }
    } catch (error) {
      dispatch({ type: "SET_RESULT", payload: { error: String(error) } });
    }
  }, [sessionId]);

  const actions: RightPanelActions = {
    setMode: (mode) => dispatch({ type: "SET_MODE", payload: mode }),
    openCode: (context) => dispatch({ type: "OPEN_CODE", payload: context }),
    openPreview: (context) => dispatch({ type: "OPEN_PREVIEW", payload: context }),
    executeCode,
    clearPanel: () => dispatch({ type: "CLEAR" }),
    goBack: () => dispatch({ type: "GO_BACK" }),
  };

  return (
    <RightPanelContext.Provider value={{ state, actions }}>
      {children}
    </RightPanelContext.Provider>
  );
}

export function useRightPanel() {
  const context = useContext(RightPanelContext);
  if (!context) {
    throw new Error("useRightPanel must be used within RightPanelProvider");
  }
  return context;
}
```

### 5.2 RightPanel 容器

```typescript
// demo/chat/components/right-panel/RightPanel.tsx

"use client";

import React from "react";
import { useRightPanel } from "@/contexts/RightPanelContext";
import { UnifiedCodeEditor } from "./UnifiedCodeEditor";
import { ExecutionResultView } from "./ExecutionResultView";
import { EmptyState } from "./EmptyState";
import { StageOutputPreview } from "../sop/StageOutputPreview";

interface RightPanelProps {
  sessionId: string;
  isDarkMode: boolean;
  // SOP 相关回调
  onRetryStage?: (stageId: string) => void;
  isExpertMode?: boolean;
}

export function RightPanel({ sessionId, isDarkMode, onRetryStage, isExpertMode }: RightPanelProps) {
  const { state, actions } = useRightPanel();

  switch (state.mode) {
    case "empty":
      return <EmptyState />;

    case "code":
      return (
        <UnifiedCodeEditor
          context={state.codeContext!}
          executionState={state.executionState}
          onExecute={(code) => actions.executeCode(code, sessionId)}
          onClose={() => actions.setMode("empty")}
          isDarkMode={isDarkMode}
        />
      );

    case "preview":
      return (
        <StageOutputPreview
          stageId={state.previewContext!.stageId}
          stageName={state.previewContext!.stageName}
          outputPreview={state.previewContext!.outputPreview}
          status={state.previewContext!.status}
          onBack={() => actions.goBack()}
          isExpertMode={isExpertMode}
          stageData={state.previewContext!.stageData}
          onRetryStage={onRetryStage}
          sessionId={sessionId}
          isDarkMode={isDarkMode}
        />
      );

    case "result":
      return (
        <ExecutionResultView
          result={state.executionState.result}
          error={state.executionState.error}
          onBack={() => actions.goBack()}
        />
      );

    default:
      return <EmptyState />;
  }
}
```

### 5.3 迁移后的调用方式

```typescript
// three-panel-interface.tsx 中的调用变化

// Before (旧方式)
const handleCodeBlockClick = (code: string) => {
  setCodeEditorContent(code);
  setShowCodeEditor(true);
};

// After (新方式)
const { actions } = useRightPanel();

const handleCodeBlockClick = (code: string, language: string) => {
  actions.openCode({
    code,
    language,
    source: "chat",
  });
};

// Before (旧方式)
const handleStageClick = (stageData: StageProgress) => {
  setSelectedStageId(stageData.stage_id);
  setSelectedStageData(stageData);
  setRightPanelMode("preview");
};

// After (新方式)
const handleStageClick = (stageData: StageProgress) => {
  actions.openPreview({
    stageId: stageData.stage_id,
    stageName: stageData.stage_name,
    status: stageData.status,
    outputPreview: stageData.output_preview,
    stageData: {
      params: stageData.params,
      params_meta: stageData.params_meta,
      code: stageData.code,
    },
  });
};
```

---

## 六、风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 迁移过程中功能回归 | 高 | 分阶段迁移，每阶段充分测试 |
| 状态管理复杂度增加 | 中 | 使用 TypeScript 严格类型检查 |
| 组件间通信问题 | 中 | 统一通过 Context，避免 prop drilling |
| 性能问题（频繁渲染） | 低 | 使用 useMemo/useCallback 优化 |

---

## 七、验收标准

### 7.1 功能验收

- [ ] Chat 代码块点击 → 打开编辑器 → 编辑 → 执行 → 显示结果
- [ ] SOP 阶段点击 → 显示预览 → 专家模式编辑 → 重试执行
- [ ] 模式切换时上下文保留（code ↔ preview）
- [ ] 返回操作正常工作
- [ ] 空状态正确显示

### 7.2 代码质量

- [ ] 无 TypeScript 类型错误
- [ ] 无 ESLint 警告
- [ ] 组件职责单一，代码可读
- [ ] 冗余代码已移除

### 7.3 性能指标

- [ ] 模式切换响应时间 < 100ms
- [ ] 代码编辑器加载时间 < 500ms
- [ ] 无内存泄漏

---

## 八、后续扩展

完成本次重构后，可轻松扩展以下功能：

1. **多标签页支持**：同时打开多个代码编辑器
2. **代码历史记录**：保存最近编辑的代码片段
3. **执行历史**：查看历史执行结果
4. **代码对比**：对比不同版本的代码
5. **协作编辑**：多人实时编辑（WebSocket）

---

## 九、参考资料

- 当前实现：`demo/chat/components/three-panel-interface.tsx`
- SOP 组件：`demo/chat/components/sop/`
- 代码编辑器：`demo/chat/components/sop/StageCodeEditor.tsx`
- API 配置：`demo/chat/lib/config.ts`
