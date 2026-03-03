"use client";

import React, { useState, useEffect, useRef } from "react";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  ChevronDown,
  ChevronUp,
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  Pause,
  Square,
  Play,
  SkipForward,
  Code,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { ExecutionStatus } from "@/lib/sopService";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

// =============================================================================
// 类型定义
// =============================================================================

interface StageConfig {
  icon: string;
  color: string;
  label: string;
}

interface StageData {
  stage_id: string;
  stage_name: string;
  status: string;
  progress: number;
  message: string;
  logs?: string[];
  code?: string;  // 阶段对应的Python伪代码
  output_preview?: Record<string, any>;  // 阶段输出预览
  execution_time_ms?: number | null;  // 阶段执行时间（毫秒）
  started_at?: string | null;  // 阶段开始时间
  completed_at?: string | null;  // 阶段完成时间
}

interface SopStageControllerProps {
  executionStatus: ExecutionStatus | null;
  taskId: string;
  onStageClick?: (stageId: string, stage: StageData) => void;
  onPause?: () => void;
  onStop?: () => void;
  onResume?: () => void;
  onSkipStage?: (stageId: string) => Promise<void>;  // 跳过阶段回调
  isPaused?: boolean;
  className?: string;
  // 专家模式相关
  isExpertMode?: boolean;
  // 布局控制
  showHeader?: boolean;  // 是否显示头部（进度条+控制按钮）
  showStages?: boolean;  // 是否显示阶段卡片列表
  // 阶段卡片容器的最大高度（用于可滚动区域）
  stagesMaxHeight?: string;
  // 是否为恢复的任务（已完成/暂停中），用于默认收起已完成阶段
  isRestoredTask?: boolean;
}

// =============================================================================
// 阶段配置
// =============================================================================

// 评分卡开发任务阶段配置
const scorecardStageConfigs: Record<string, StageConfig> = {
  data_loading: {
    icon: "📥",
    color: "bg-blue-50 border-blue-200 dark:bg-blue-950/30 dark:border-blue-800",
    label: "数据加载"
  },
  woe_binning: {
    icon: "📊",
    color: "bg-cyan-50 border-cyan-200 dark:bg-cyan-950/30 dark:border-cyan-800",
    label: "WOE分箱"
  },
  feature_selection: {
    icon: "🔍",
    color: "bg-purple-50 border-purple-200 dark:bg-purple-950/30 dark:border-purple-800",
    label: "特征筛选"
  },
  model_training: {
    icon: "🧠",
    color: "bg-orange-50 border-orange-200 dark:bg-orange-950/30 dark:border-orange-800",
    label: "模型训练"
  },
  score_scaling: {
    icon: "📐",
    color: "bg-green-50 border-green-200 dark:bg-green-950/30 dark:border-green-800",
    label: "评分转换"
  },
  model_evaluation: {
    icon: "📈",
    color: "bg-yellow-50 border-yellow-200 dark:bg-yellow-950/30 dark:border-yellow-800",
    label: "模型评估"
  },
  report_generation: {
    icon: "📋",
    color: "bg-gray-50 border-gray-200 dark:bg-gray-950/30 dark:border-gray-700",
    label: "报告生成"
  }
};

// 规则挖掘任务阶段配置
const ruleMiningStageConfigs: Record<string, StageConfig> = {
  preprocessing: {
    icon: "🔧",
    color: "bg-slate-50 border-slate-200 dark:bg-slate-950/30 dark:border-slate-800",
    label: "数据预处理"
  },
  feature_engineering: {
    icon: "⚙️",
    color: "bg-indigo-50 border-indigo-200 dark:bg-indigo-950/30 dark:border-indigo-800",
    label: "特征工程"
  },
  generating_rules: {
    icon: "🌲",
    color: "bg-emerald-50 border-emerald-200 dark:bg-emerald-950/30 dark:border-emerald-800",
    label: "规则生成"
  },
  // v2.0: 合并后的规则筛选阶段
  rule_filtering: {
    icon: "🔍",
    color: "bg-amber-50 border-amber-200 dark:bg-amber-950/30 dark:border-amber-800",
    label: "规则筛选"
  },
  filtering_rules: {
    icon: "🔍",
    color: "bg-amber-50 border-amber-200 dark:bg-amber-950/30 dark:border-amber-800",
    label: "规则筛选"
  },
  evaluating_rules: {
    icon: "📊",
    color: "bg-cyan-50 border-cyan-200 dark:bg-cyan-950/30 dark:border-cyan-800",
    label: "规则评估"
  },
  selecting_rules: {
    icon: "✅",
    color: "bg-green-50 border-green-200 dark:bg-green-950/30 dark:border-green-800",
    label: "最优选择"
  },
  report_generation: {
    icon: "📋",
    color: "bg-gray-50 border-gray-200 dark:bg-gray-950/30 dark:border-gray-700",
    label: "报告生成"
  }
};

// 根据任务类型获取阶段配置
function getStageConfigs(taskId: string): Record<string, StageConfig> {
  switch (taskId) {
    case "scorecard_dev":
      return scorecardStageConfigs;
    case "rule_mining":
      return ruleMiningStageConfigs;
    default:
      return {};
  }
}

// =============================================================================
// 状态徽章组件
// =============================================================================

function StatusBadge({ status }: { status: string }) {
  const variants: Record<string, { variant: "default" | "secondary" | "destructive" | "outline"; label: string }> = {
    pending: { variant: "secondary", label: "等待" },
    running: { variant: "default", label: "执行中" },
    completed: { variant: "outline", label: "完成" },
    failed: { variant: "destructive", label: "失败" },
    paused: { variant: "secondary", label: "已暂停" },
    stopped: { variant: "secondary", label: "已停止" },
    skipped: { variant: "secondary", label: "已跳过" },
  };

  const config = variants[status] || variants.pending;

  return (
    <Badge variant={config.variant} className="text-xs px-1.5 py-0">
      {config.label}
    </Badge>
  );
}

// 格式化执行时间（毫秒 -> 可读格式）
function formatExecutionTime(ms: number | null | undefined): string | null {
  if (ms == null || ms <= 0) return null;
  
  if (ms < 1000) {
    return `${ms}ms`;
  } else if (ms < 60000) {
    const seconds = (ms / 1000).toFixed(1);
    return `${seconds}s`;
  } else {
    const minutes = Math.floor(ms / 60000);
    const seconds = Math.round((ms % 60000) / 1000);
    return seconds > 0 ? `${minutes}m${seconds}s` : `${minutes}m`;
  }
}

// =============================================================================
// 单个阶段卡片组件
// =============================================================================

interface StageCardProps {
  stageId: string;
  stage: StageData;
  config: StageConfig;
  isActive: boolean;
  isCollapsed: boolean;
  onToggle: () => void;
  onClick?: () => void;
  // 专家模式跳过功能
  isExpertMode?: boolean;
  onSkip?: () => void;
  isSkipping?: boolean;
}

function StageCard({
  stageId,
  stage,
  config,
  isActive,
  isCollapsed,
  onToggle,
  onClick,
  isExpertMode = false,
  onSkip,
  isSkipping = false,
}: StageCardProps) {
  const isCompleted = stage.status === "completed";
  const isFailed = stage.status === "failed";
  const isRunning = stage.status === "running";
  const isPending = stage.status === "pending";
  const isSkipped = stage.status === "skipped";
  
  // 只有专家模式下、阶段处于pending状态时才能跳过
  const canSkip = isExpertMode && isPending && onSkip;

  return (
    <div
      className={cn(
        "border rounded-lg p-3 transition-all cursor-pointer",
        config.color,
        isActive && "ring-2 ring-blue-400 dark:ring-blue-500",
        isCompleted && "opacity-80",
        isSkipped && "opacity-60"
      )}
      onClick={onClick}
    >
      {/* 头部：图标、名称、状态、耗时 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-lg">{config.icon}</span>
          <span className="font-medium text-sm">{config.label}</span>
          <StatusBadge status={stage.status} />
          {/* 已完成阶段显示执行耗时，hover显示详细时间 */}
          {isCompleted && stage.execution_time_ms != null && (
            <TooltipProvider delayDuration={200}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <span className="text-xs text-gray-500 dark:text-gray-400 cursor-help">
                    {formatExecutionTime(stage.execution_time_ms)}
                  </span>
                </TooltipTrigger>
                <TooltipContent side="top" className="text-xs">
                  <div className="space-y-1">
                    {stage.started_at ? (
                      <div>开始: {new Date(stage.started_at).toLocaleTimeString()}</div>
                    ) : (
                      <div>开始: -</div>
                    )}
                    {stage.completed_at ? (
                      <div>完成: {new Date(stage.completed_at).toLocaleTimeString()}</div>
                    ) : (
                      <div>完成: -</div>
                    )}
                  </div>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
        </div>
        <div className="flex items-center gap-1">
          {/* 跳过按钮 - 专家模式下pending阶段显示 */}
          {canSkip && (
            <Button
              variant="ghost"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                onSkip();
              }}
              disabled={isSkipping}
              className="h-6 px-2 text-xs text-gray-500 hover:text-orange-600 hover:bg-orange-50 dark:hover:bg-orange-900/20"
              title="跳过此阶段"
            >
              {isSkipping ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <SkipForward className="h-3 w-3" />
              )}
              <span className="ml-1">跳过</span>
            </Button>
          )}
          <button
            onClick={(e) => {
              e.stopPropagation();
              onToggle();
            }}
            className="p-1 hover:bg-black/5 dark:hover:bg-white/5 rounded"
          >
            {isCollapsed ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronUp className="h-4 w-4" />
            )}
          </button>
        </div>
      </div>

      {/* 进度条 */}
      {isRunning && (
        <div className="mt-2">
          <Progress value={stage.progress} className="h-1.5" />
          <div className="flex items-center justify-between mt-1">
            <span className="text-xs text-gray-500 dark:text-gray-400 truncate max-w-[80%]">
              {stage.message || "处理中..."}
            </span>
            <span className="text-xs text-gray-500 dark:text-gray-400">
              {Math.round(stage.progress)}%
            </span>
          </div>
        </div>
      )}

      {/* 完成状态显示消息 */}
      {isCompleted && stage.message && (
        <div className="mt-2 text-xs text-gray-600 dark:text-gray-400 flex items-center gap-1">
          <CheckCircle2 className="h-3 w-3 text-green-500" />
          <span className="truncate">{stage.message}</span>
        </div>
      )}

      {/* 已跳过状态显示 */}
      {isSkipped && (
        <div className="mt-2 text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1">
          <SkipForward className="h-3 w-3" />
          <span>已跳过此阶段</span>
        </div>
      )}

      {/* 失败状态显示错误 */}
      {isFailed && stage.message && (
        <div className="mt-2 text-xs text-red-600 dark:text-red-400 flex items-center gap-1">
          <XCircle className="h-3 w-3" />
          <span className="truncate">{stage.message}</span>
        </div>
      )}

      {/* 可折叠日志区域 */}
      {!isCollapsed && stage.logs && stage.logs.length > 0 && (
        <div className="mt-2 text-xs text-gray-600 dark:text-gray-400 space-y-0.5 max-h-24 overflow-auto bg-black/5 dark:bg-white/5 rounded p-2">
          {stage.logs.slice(-10).map((log, i) => (
            <div key={i} className="font-mono">{log}</div>
          ))}
        </div>
      )}

      {/* 可折叠代码区域 - 阶段开始执行时显示 */}
      {!isCollapsed && stage.code && (
        <div className="mt-2">
          <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400 mb-1">
            <Code className="h-3 w-3" />
            <span>阶段伪代码</span>
          </div>
          <div className="text-xs font-mono bg-gray-900 dark:bg-gray-950 text-gray-100 rounded p-2 max-h-32 overflow-auto">
            <pre className="whitespace-pre-wrap break-words">{stage.code}</pre>
          </div>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// 主组件：SOP阶段控制器
// =============================================================================

/**
 * SOP阶段控制器组件
 * 
 * 用于Pipeline模式的阶段进度展示和控制。
 * 提供以下功能：
 * - 阶段进度展示（进度条+阶段卡片列表）
 * - 任务级控制（暂停/继续/停止）
 * - 阶段级控制（跳过，仅专家模式）
 * - 阶段详情查看（点击阶段卡片）
 */
export function SopStageController({
  executionStatus,
  taskId,
  onStageClick,
  onPause,
  onStop,
  onResume,
  onSkipStage,
  isPaused = false,
  className,
  isExpertMode = false,
  showHeader = true,
  showStages = true,
  stagesMaxHeight = "none",
  isRestoredTask = false,
}: SopStageControllerProps) {
  const [collapsedStages, setCollapsedStages] = useState<Set<string>>(new Set());
  const [skippingStage, setSkippingStage] = useState<string | null>(null);
  const stageConfigs = getStageConfigs(taskId);
  
  // 定义阶段顺序（根据任务类型）
  const stageOrder = taskId === "scorecard_dev" 
    ? ["data_loading", "woe_binning", "feature_selection", "model_training", "score_scaling", "model_evaluation", "report_generation"]
    : ["preprocessing", "feature_engineering", "generating_rules", "rule_filtering", "filtering_rules", "evaluating_rules", "selecting_rules", "report_generation"];

  // 记录上一次的阶段状态，用于检测状态变化
  const prevStageStatusRef = useRef<Record<string, string>>({});
  // 标记是否已完成初始化（避免重复初始化）
  const initializedRef = useRef(false);
  
  // 恢复任务时默认收起所有已完成的阶段
  useEffect(() => {
    if (!executionStatus?.stages || initializedRef.current) return;
    
    // 只在首次加载且是恢复的任务时默认收起已完成阶段
    if (isRestoredTask) {
      const completedStageIds = Object.entries(executionStatus.stages)
        .filter(([, stage]) => (stage as StageData).status === "completed")
        .map(([stageId]) => stageId);
      
      if (completedStageIds.length > 0) {
        setCollapsedStages(new Set(completedStageIds));
      }
    }
    
    initializedRef.current = true;
  }, [executionStatus?.stages, isRestoredTask]);
  
  // 记录上一次的任务状态
  const prevTaskStatusRef = useRef<string | undefined>(undefined);
  
  // 自动管理阶段展开/收起：执行中展开，完成后收起
  useEffect(() => {
    if (!executionStatus?.stages) return;
    
    const stages = executionStatus.stages;
    const prevStatus = prevStageStatusRef.current;
    const currentTaskStatus = executionStatus.status;
    const prevTaskStatus = prevTaskStatusRef.current;
    
    setCollapsedStages((prev) => {
      const next = new Set(prev);
      
      // 任务整体完成时，收起所有已完成的阶段
      if (currentTaskStatus === "completed" && prevTaskStatus !== "completed") {
        Object.entries(stages).forEach(([stageId, stage]) => {
          const stageData = stage as StageData;
          if (stageData.status === "completed") {
            next.add(stageId);
          }
        });
      } else {
        // 正常的阶段状态变化处理
        Object.entries(stages).forEach(([stageId, stage]) => {
          const stageData = stage as StageData;
          const currentStatus = stageData.status;
          const previousStatus = prevStatus[stageId];
          
          // 阶段开始执行时自动展开
          if (currentStatus === "running" && previousStatus !== "running") {
            next.delete(stageId);
          }
          
          // 阶段完成后自动收起（放宽条件：只要之前不是completed且现在是completed就收起）
          // 这样可以处理：running -> completed, paused -> completed, pending -> completed（缓存恢复）等情况
          if (currentStatus === "completed" && previousStatus !== "completed" && previousStatus !== undefined) {
            next.add(stageId);
          }
          
          // 更新记录的状态
          prevStatus[stageId] = currentStatus;
        });
      }
      
      return next;
    });
    
    prevStageStatusRef.current = prevStatus;
    prevTaskStatusRef.current = currentTaskStatus;
  }, [executionStatus?.stages, executionStatus?.status]);

  const toggleCollapse = (stageId: string) => {
    setCollapsedStages((prev) => {
      const next = new Set(prev);
      if (next.has(stageId)) {
        next.delete(stageId);
      } else {
        next.add(stageId);
      }
      return next;
    });
  };

  // 处理跳过阶段
  const handleSkipStage = async (stageId: string) => {
    if (!onSkipStage) return;
    setSkippingStage(stageId);
    try {
      await onSkipStage(stageId);
    } finally {
      setSkippingStage(null);
    }
  };

  if (!executionStatus) {
    return (
      <div className={cn("flex items-center justify-center p-8", className)}>
        <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
        <span className="ml-2 text-gray-500">加载中...</span>
      </div>
    );
  }

  const stages = executionStatus.stages || {};
  
  // 按照预定义的阶段顺序排序
  const stageEntries = Object.entries(stages)
    .sort(([, a], [, b]) => {
      const orderA = stageOrder.indexOf(a.stage_id || '');
      const orderB = stageOrder.indexOf(b.stage_id || '');
      // 如果不在预定义顺序中，放在最后
      if (orderA === -1 && orderB === -1) return 0;
      if (orderA === -1) return 1;
      if (orderB === -1) return -1;
      return orderA - orderB;
    });
  const isRunning = executionStatus.status === "running";
  const isCompleted = executionStatus.status === "completed";
  const isFailed = executionStatus.status === "failed";
  // 支持从props或status推断暂停状态
  const isPausedState = isPaused || executionStatus.status === "paused";

  // 获取最近完成的阶段名称（用于专家模式暂停提示）
  const getLastCompletedStageName = (): string | null => {
    const completedStages = stageEntries
      .filter(([, stage]) => (stage as StageData).status === "completed")
      .map(([stageId, stage]) => ({
        id: stageId,
        name: (stage as StageData).stage_name || stageConfigs[stageId]?.label || stageId
      }));
    return completedStages.length > 0 ? completedStages[completedStages.length - 1].name : null;
  };
  const lastCompletedStageName = isPausedState && isExpertMode ? getLastCompletedStageName() : null;

  return (
    <div className={cn("space-y-3", className)}>
      {/* 总体进度头部 - 专家模式暂停时显示橙色主题 */}
      {showHeader && (
        <>
          <div className={cn(
            "flex items-center justify-between p-3 rounded-lg border",
            isExpertMode && isPausedState 
              ? "bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-800"
              : "bg-gray-50 dark:bg-gray-900/50 border-gray-200 dark:border-gray-700"
          )}>
            <div className="flex items-center gap-3">
              {isRunning && !isPausedState && <Loader2 className="h-5 w-5 animate-spin text-blue-500" />}
              {isCompleted && <CheckCircle2 className="h-5 w-5 text-green-500" />}
              {isFailed && <XCircle className="h-5 w-5 text-red-500" />}
              {isPausedState && <Pause className={cn(
                "h-5 w-5",
                isExpertMode ? "text-orange-500" : "text-yellow-500"
              )} />}
              
              <div>
                <div className="font-medium text-sm flex items-center gap-2">
                  {taskId === "scorecard_dev" ? "评分卡开发" : "规则挖掘"}
                  {/* 专家模式暂停时显示提示标签 */}
                  {isExpertMode && isPausedState && (
                    <span className="text-xs px-1.5 py-0.5 rounded bg-orange-100 dark:bg-orange-800/50 text-orange-600 dark:text-orange-400">
                      {lastCompletedStageName ? `「${lastCompletedStageName}」阶段完成，等待操作` : "阶段完成，等待操作"}
                    </span>
                  )}
                </div>
                <div className={cn(
                  "text-xs",
                  isExpertMode && isPausedState 
                    ? "text-orange-600 dark:text-orange-400" 
                    : "text-gray-500"
                )}>
                  {isExpertMode && isPausedState 
                    ? "点击阶段查看结果，或点击「继续」执行下一阶段" 
                    : (isPausedState ? "任务已暂停" : (executionStatus.message || "准备中..."))}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {/* 进度百分比 */}
              <span className="text-sm font-medium">
                {Math.round(executionStatus.overall_progress)}%
              </span>

              {/* 控制按钮 */}
              {isRunning && !isPausedState && onPause && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={onPause}
                  className="h-7 px-2"
                >
                  <Pause className="h-3.5 w-3.5 mr-1" />
                  暂停
                </Button>
              )}
              {isPausedState && onResume && (
                <Button
                  size="sm"
                  onClick={onResume}
                  className={cn(
                    "h-7 px-2",
                    isExpertMode 
                      ? "bg-orange-600 hover:bg-orange-700 text-white" 
                      : ""
                  )}
                  variant={isExpertMode ? "default" : "outline"}
                >
                  <Play className="h-3.5 w-3.5 mr-1" />
                  继续
                </Button>
              )}
              {(isRunning || isPausedState) && onStop && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={onStop}
                  className="h-7 px-2 text-red-600 hover:text-red-700"
                >
                  <Square className="h-3.5 w-3.5 mr-1" />
                  停止
                </Button>
              )}
            </div>
          </div>

          {/* 总体进度条 */}
          <Progress 
            value={executionStatus.overall_progress} 
            className={cn(
              "h-2",
              isExpertMode && isPausedState && "[&>div]:bg-orange-500"
            )} 
          />
        </>
      )}

      {/* 阶段卡片列表 - 可滚动区域 */}
      {showStages && (
        <div 
          className="space-y-2 overflow-y-auto"
          style={{ maxHeight: stagesMaxHeight }}
        >
          {stageEntries.map(([stageId, stage]) => {
            const stageData = stage as StageData;
            const config = stageConfigs[stageId] || {
              icon: "⚙️",
              color: "bg-gray-50 border-gray-200 dark:bg-gray-950/30 dark:border-gray-700",
              label: stageData.stage_name || stageId,
            };
            const isActive = executionStatus.current_stage === stageId;

            return (
              <StageCard
                key={stageId}
                stageId={stageId}
                stage={stageData}
                config={config}
                isActive={isActive}
                isCollapsed={collapsedStages.has(stageId)}
                onToggle={() => toggleCollapse(stageId)}
                onClick={() => onStageClick?.(stageId, stageData)}
                isExpertMode={isExpertMode}
                onSkip={onSkipStage ? () => handleSkipStage(stageId) : undefined}
                isSkipping={skippingStage === stageId}
              />
            );
          })}

          {/* 时间信息：使用首个阶段开始时间和最后阶段完成时间 */}
          {(() => {
            // 计算首个阶段开始时间和最后阶段完成时间
            let firstStageStartTime: Date | null = null;
            let lastStageEndTime: Date | null = null;
            
            stageOrder.forEach(stageId => {
              const stage = executionStatus.stages[stageId];
              if (stage?.started_at) {
                const startTime = new Date(stage.started_at);
                if (!firstStageStartTime || startTime < firstStageStartTime) {
                  firstStageStartTime = startTime;
                }
              }
              if (stage?.completed_at) {
                const endTime = new Date(stage.completed_at);
                if (!lastStageEndTime || endTime > lastStageEndTime) {
                  lastStageEndTime = endTime;
                }
              }
            });
            
            // 如果没有阶段时间数据，回退到任务级别时间
            const displayStartTime = firstStageStartTime || (executionStatus.started_at ? new Date(executionStatus.started_at) : null);
            const displayEndTime = lastStageEndTime || (executionStatus.completed_at ? new Date(executionStatus.completed_at) : null);
            
            if (!displayStartTime) return null;
            
            return (
              <div className="flex items-center gap-4 text-xs text-gray-500 px-1">
                <span>
                  开始: {displayStartTime.toLocaleTimeString()}
                </span>
                {displayEndTime && (
                  <>
                    <span>
                      完成: {displayEndTime.toLocaleTimeString()}
                    </span>
                    <span className="font-medium text-gray-600 dark:text-gray-400">
                      总耗时: {formatExecutionTime(
                        displayEndTime.getTime() - displayStartTime.getTime()
                      )}
                    </span>
                  </>
                )}
              </div>
            );
          })()}
        </div>
      )}
    </div>
  );
}

// 向后兼容：保留旧名称的别名导出
export const PipelineStageCards = SopStageController;

export default SopStageController;
