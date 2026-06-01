/**
 * SOP组件模块导出
 */

// 任务配置组件 - 统一使用TaskConfigPanel
export { TaskSelector } from "./TaskSelector";
export { TaskConfigPanel } from "./TaskConfigPanel";
export { TaskConfirmCard } from "./TaskConfirmCard";
export type { CardStatus } from "./TaskConfirmCard";
export { DynamicParamRenderer, ParamGroupRenderer, shouldShowParam } from "./DynamicParamRenderer";

// 旧配置面板组件已废弃并删除，由TaskConfigPanel统一替代
// - RuleMiningConfigPanel.tsx (已删除)
// - ScorecardConfigPanel.tsx (已删除)

// 模式选择组件
export { ModeSelector } from "./ModeSelector";
// 注意：EngineMode 已废弃，统一使用 Pipeline 执行引擎
// InteractionMode 现已移至 @/hooks/use-mode，保留导出以兼容历史代码
export type { InteractionMode } from "@/hooks/use-mode";

// 任务进度与执行组件
export { TaskProgress } from "./TaskProgress";
export { SopStageController, PipelineStageCards } from "./SopStageController";
export { ExecutionLogPanel, useExecutionLogs, createLogEntry } from "./ExecutionLogPanel";
export type { LogEntry, LogLevel } from "./ExecutionLogPanel";
export { StageCodePreview } from "./StageCodePreview";
export { StageOutputPreview } from "./StageOutputPreview";
export type { StageEditableData } from "./StageOutputPreview";
// 注意：buildOverallAnalysisPrompt 已迁移至后端 API/AI_analysis_prompts.py
// 前端通过 /v1/chat/analysis/prompt API 获取分析提示词

// Pipeline 代码展示组件（LLM+Pipeline 新架构）
export { PipelineCodePanel, usePipelineCodeBlocks } from "./PipelineCodePanel";
export type { CodeBlock, CodeBlockType, CodeBlockStatus, PipelineCodePanelProps } from "./PipelineCodePanel";

// 代码与参数编辑器组件（复用原项目Monaco Editor能力）
export { StageCodeEditor } from "./StageCodeEditor";
export type { StageCodeEditorProps, CodeExecutionResult } from "./StageCodeEditor";
export { StageParameterEditor } from "./StageParameterEditor";
export type { StageParameterEditorProps } from "./StageParameterEditor";
export { StageParamsForm } from "./StageParamsForm";
export type { StageParamsFormProps } from "./StageParamsForm";

// 任务结果组件
export { RuleMiningResults } from "./RuleMiningResults";
export { ScorecardResults } from "./ScorecardResults";

// 新增组件 (升级计划)
export { ModelStatisticsPanel } from "./ModelStatisticsPanel";
export { ScoreConverter } from "./ScoreConverter";
export { AmountAnalysisPanel } from "./AmountAnalysisPanel";
export { PriorRulesInput } from "./PriorRulesInput";

// 任务历史组件
export { TaskHistoryList } from "./TaskHistoryList";
export { TaskHistoryCompact } from "./TaskHistoryCompact";
export type { TaskHistoryCompactRef } from "./TaskHistoryCompact";
