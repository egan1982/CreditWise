"use client";

import React, { useEffect, useState, useRef } from "react";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Target,
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  X,
} from "lucide-react";
import { sopService, ExecutionStatus } from "@/lib/sopService";
import { cn } from "@/lib/utils";

// 阶段顺序定义（根据任务类型）
const stageOrder = (taskId: string) => 
  taskId === "scorecard_dev" 
    ? ["data_loading", "woe_binning", "feature_selection", "model_training", "score_scaling", "model_evaluation", "report_generation"]
    : ["preprocessing", "feature_engineering", "generating_rules", "rule_filtering", "filtering_rules", "evaluating_rules", "selecting_rules", "report_generation"];

interface TaskProgressProps {
  executionId: string;
  taskId?: string;
  taskName?: string;
  onComplete?: (status: ExecutionStatus) => void;
  onClose?: () => void;
  onStatusUpdate?: (status: ExecutionStatus) => void;  // Phase 3: 状态更新回调
  pollTrigger?: number;  // 改变此值会重启轮询（用于 paused 停止后的恢复/重试/跳过操作）
  className?: string;
}

// 规则挖掘阶段名称 (v2.0: 合并 filtering_rules + evaluating_rules 为 rule_filtering)
const RULE_MINING_STAGES: Record<string, string> = {
  preprocessing: "数据预处理",
  feature_engineering: "特征工程",
  generating_rules: "规则生成",
  rule_filtering: "规则筛选",
  filtering_rules: "规则筛选",  // 兼容旧阶段名
  evaluating_rules: "规则评估",  // 兼容旧阶段名
  selecting_rules: "最优选择",
  report_generation: "报告生成",
};

// 评分卡开发阶段名称
const SCORECARD_STAGES: Record<string, string> = {
  data_loading: "数据加载",
  woe_binning: "WOE分箱",
  feature_selection: "特征筛选",
  model_training: "模型训练",
  score_scaling: "评分转换",
  model_evaluation: "模型评估",
  report_generation: "报告生成",
};

// 任务名称映射
const TASK_NAMES: Record<string, string> = {
  rule_mining: "规则挖掘",
  scorecard_dev: "评分卡开发",
};

// 根据任务ID获取阶段名称映射
const getStageNames = (taskId?: string): Record<string, string> => {
  if (taskId === "scorecard_dev") {
    return SCORECARD_STAGES;
  }
  return RULE_MINING_STAGES;
};

export function TaskProgress({
  executionId,
  taskId,
  taskName,
  onComplete,
  onClose,
  onStatusUpdate,
  pollTrigger,
  className,
}: TaskProgressProps) {
  // 根据taskId获取默认任务名称
  const displayTaskName = taskName || TASK_NAMES[taskId || ""] || "规则挖掘";
  const stageNames = getStageNames(taskId);
  const [status, setStatus] = useState<ExecutionStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  // 使用ref存储回调函数，避免依赖变化导致重复轮询
  const onCompleteRef = useRef(onComplete);
  const onStatusUpdateRef = useRef(onStatusUpdate);
  
  // 更新ref
  useEffect(() => {
    onCompleteRef.current = onComplete;
    onStatusUpdateRef.current = onStatusUpdate;
  }, [onComplete, onStatusUpdate]);

  // 轮询任务状态
  useEffect(() => {
    if (!executionId) return;

    let isMounted = true;
    let pollTimeout: NodeJS.Timeout | null = null;
    let lastStatus: string | null = null;  // 跟踪上一次状态，用于检测状态变化
    let pausedStableCount = 0;  // 连续检测到 paused 的次数，用于判断状态稳定

    const pollStatus = async () => {
      try {
        const currentStatus = await sopService.getExecutionStatus(executionId);
        if (!isMounted) return;
        
        // 检测状态变化：从 paused 变为 running 时，需要立即快速轮询
        const statusChanged = lastStatus !== null && lastStatus !== currentStatus.status;
        lastStatus = currentStatus.status;
        
        setStatus(currentStatus);
        
        // Phase 3: 调用状态更新回调（使用ref避免依赖问题）
        onStatusUpdateRef.current?.(currentStatus);

        if (
          currentStatus.status === "completed" ||
          currentStatus.status === "failed"
        ) {
          // 任务结束，立即清除已调度的轮询，防止404错误
          if (pollTimeout) {
            clearTimeout(pollTimeout);
            pollTimeout = null;
          }
          onCompleteRef.current?.(currentStatus);
          return;
        }
        
        // 根据状态动态调整轮询间隔
        let nextInterval = 500; // 默认500ms（更快的基础轮询）
        
        if (currentStatus.status === "running") {
          pausedStableCount = 0;  // 重置 paused 稳定计数
          // 运行时更频繁轮询
          const runningStages = Object.values(currentStatus.stages).filter(s => s.status === "running");
          if (runningStages.length > 0) {
            const maxProgress = Math.max(...runningStages.map(s => s.progress || 0));
            // 进度超过90%时极快轮询（200ms），80-90%时快速轮询（300ms）
            if (maxProgress > 90) {
              nextInterval = 200;
            } else if (maxProgress > 80) {
              nextInterval = 300;
            } else if (maxProgress > 50) {
              nextInterval = 400;
            } else {
              nextInterval = 500;
            }
          } else {
            // 任务running但没有running阶段：可能是阶段刚完成，快速轮询以捕获下一个阶段
            nextInterval = 300;
          }
          
          // 状态刚从paused变为running时，使用最快轮询
          if (statusChanged && lastStatus === "paused") {
            nextInterval = 200;
          }
        } else if (currentStatus.status === "paused") {
          pausedStableCount++;
          if (pausedStableCount >= 3) {
            // 连续3次检测到 paused，状态已稳定，停止轮询
            // 后续通过 pollTrigger 变化重启（用户点击继续/重试/跳过时触发）
            console.log("[TaskProgress] Paused state stable, stopping poll. Use pollTrigger to restart.");
            return; // 不再调度下一次轮询
          }
          nextInterval = 600; // paused 确认间隔，给 resume 信号传递留出时间窗口
        }
        
        // 继续下一次轮询
        if (isMounted) {
          pollTimeout = setTimeout(pollStatus, nextInterval);
        }
      } catch (err: any) {
        console.error("Failed to poll status:", err, "message:", err?.message);
        if (isMounted) {
          // 检查是否为404错误（执行记录不存在）
          const is404 = err?.message?.includes("404") || 
                        err?.response?.status === 404 ||
                        err?.status === 404;
          
          if (is404) {
            // 执行记录不存在，停止轮询并通知父组件
            setError("任务记录已不存在");
            onCompleteRef.current?.({
              execution_id: executionId,
              task_id: "",
              status: "failed",
              current_stage: "",
              overall_progress: 0,
              message: "任务记录已不存在（后端可能已重启）",
              started_at: null,
              completed_at: null,
              stages: {},
            });
            return; // 停止轮询
          }
          
          setError("获取任务状态失败");
          // 其他错误继续轮询，但使用较长间隔
          pollTimeout = setTimeout(pollStatus, 3000);
        }
      }
    };

    // 立即获取一次
    pollStatus();

    return () => {
      isMounted = false;
      if (pollTimeout) {
        clearTimeout(pollTimeout);
      }
    };
  }, [executionId, pollTrigger]);  // 添加 pollTrigger 依赖：变化时重启轮询

  const getStatusIcon = () => {
    if (!status) return <Loader2 className="h-4 w-4 animate-spin" />;

    switch (status.status) {
      case "pending":
        return <Clock className="h-4 w-4 text-yellow-500" />;
      case "running":
        return <Loader2 className="h-4 w-4 animate-spin text-blue-500" />;
      case "completed":
        return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case "failed":
        return <XCircle className="h-4 w-4 text-red-500" />;
      default:
        return <Target className="h-4 w-4" />;
    }
  };

  const getStatusBadge = () => {
    if (!status) return null;

    const variants: Record<string, { variant: "default" | "secondary" | "destructive" | "outline"; label: string }> = {
      pending: { variant: "secondary", label: "等待中" },
      running: { variant: "default", label: "执行中" },
      completed: { variant: "outline", label: "已完成" },
      failed: { variant: "destructive", label: "失败" },
      cancelled: { variant: "secondary", label: "已取消" },
    };

    const config = variants[status.status] || variants.pending;

    return (
      <Badge variant={config.variant} className="text-xs">
        {config.label}
      </Badge>
    );
  };

  const getStageName = (stageId: string) => {
    return stageNames[stageId] || stageId;
  };

  if (error) {
    return (
      <div
        className={cn(
          "flex items-center justify-between p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800",
          className
        )}
      >
        <div className="flex items-center gap-2 text-red-600 dark:text-red-400">
          <XCircle className="h-4 w-4" />
          <span className="text-sm">{error}</span>
        </div>
        {onClose && (
          <Button variant="ghost" size="sm" onClick={onClose} className="h-6 w-6 p-0">
            <X className="h-4 w-4" />
          </Button>
        )}
      </div>
    );
  }

  return (
    <div
      className={cn(
        "p-3 rounded-lg border transition-colors",
        status?.status === "completed"
          ? "bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800"
          : status?.status === "failed"
          ? "bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800"
          : "bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800",
        className
      )}
    >
      {/* 头部 */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {getStatusIcon()}
          <span className="font-medium text-sm">{displayTaskName}</span>
          {getStatusBadge()}
        </div>
        {onClose && (status?.status === "completed" || status?.status === "failed") && (
          <Button variant="ghost" size="sm" onClick={onClose} className="h-6 w-6 p-0">
            <X className="h-4 w-4" />
          </Button>
        )}
      </div>

      {/* 进度条 */}
      <div className="space-y-1">
        <div className="flex items-center justify-between text-xs text-gray-600 dark:text-gray-400">
          <span>
            {status?.current_stage
              ? `阶段: ${getStageName(status.current_stage)}`
              : "准备中..."}
          </span>
          <span>{Math.round(status?.overall_progress || 0)}%</span>
        </div>
        <Progress
          value={status?.overall_progress || 0}
          className={cn(
            "h-2",
            status?.status === "completed" && "[&>div]:bg-green-500",
            status?.status === "failed" && "[&>div]:bg-red-500"
          )}
        />
      </div>

      {/* 阶段列表 */}
      {status?.stages && Object.keys(status.stages).length > 0 && (
        <div className="mt-3 space-y-1.5">
          <div className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">
            工作流阶段:
          </div>
          <div className="grid grid-cols-2 gap-1.5">
            {(() => {
            // 按照预定义的阶段顺序排序
            const order = stageOrder(status.task_id || status.taskId);
            const stageEntries = Object.entries(status.stages)
              .sort(([, a], [, b]) => {
                const orderA = order.indexOf(a.stage_id || '');
                const orderB = order.indexOf(b.stage_id || '');
                // 如果不在预定义顺序中，放在最后
                if (orderA === -1 && orderB === -1) return 0;
                if (orderA === -1) return 1;
                if (orderB === -1) return -1;
                return orderA - orderB;
              });

            return stageEntries.map(([stageId, stage]) => {
              const stageData = stage as {
                stage_id: string;
                stage_name: string;
                status: string;
                progress: number;
                message: string;
              };
              const isActive = status.current_stage === stageId;
              const isCompleted = stageData.status === "completed";
              const isFailed = stageData.status === "failed";
              
              return (
                <div
                  key={stageId}
                  className={cn(
                    "flex items-center gap-1.5 px-2 py-1 rounded text-xs",
                    isActive && "bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300",
                    isCompleted && !isActive && "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300",
                    isFailed && "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300",
                    !isActive && !isCompleted && !isFailed && "bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400"
                  )}
                >
                  {isCompleted ? (
                    <CheckCircle2 className="h-3 w-3 flex-shrink-0" />
                  ) : isActive ? (
                    <Loader2 className="h-3 w-3 animate-spin flex-shrink-0" />
                  ) : isFailed ? (
                    <XCircle className="h-3 w-3 flex-shrink-0" />
                  ) : (
                    <Clock className="h-3 w-3 flex-shrink-0" />
                  )}
                  <span className="truncate">{stageData.stage_name || getStageName(stageId)}</span>
                </div>
              );
            });
          })()}
          </div>
        </div>
      )}

      {/* 消息 */}
      {status?.message && (
        <p className="mt-2 text-xs text-gray-600 dark:text-gray-400 line-clamp-2">
          {status.message}
        </p>
      )}

      {/* 时间信息：使用首个阶段开始时间和最后阶段完成时间 */}
      {(() => {
        if (!status?.stages) {
          // 没有阶段数据，使用任务级别时间
          if (!status?.started_at) return null;
          return (
            <div className="mt-2 flex items-center gap-4 text-xs text-gray-500">
              <span>
                开始: {new Date(status.started_at).toLocaleTimeString()}
              </span>
              {status.completed_at && (
                <>
                  <span>
                    完成: {new Date(status.completed_at).toLocaleTimeString()}
                  </span>
                  <span className="font-medium text-gray-600 dark:text-gray-400">
                    总耗时: {(() => {
                      const ms = new Date(status.completed_at).getTime() - new Date(status.started_at).getTime();
                      if (ms < 1000) return `${ms}ms`;
                      if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
                      const minutes = Math.floor(ms / 60000);
                      const seconds = Math.round((ms % 60000) / 1000);
                      return `${minutes}m${seconds}s`;
                    })()}
                  </span>
                </>
              )}
            </div>
          );
        }
        
        // 计算首个阶段开始时间和最后阶段完成时间
        let firstStageStartTime: Date | null = null;
        let lastStageEndTime: Date | null = null;
        
        Object.values(status.stages).forEach((stage: any) => {
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
        const displayStartTime = firstStageStartTime || (status.started_at ? new Date(status.started_at) : null);
        const displayEndTime = lastStageEndTime || (status.completed_at ? new Date(status.completed_at) : null);
        
        if (!displayStartTime) return null;
        
        const formatTime = (ms: number) => {
          if (ms < 1000) return `${ms}ms`;
          if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
          const minutes = Math.floor(ms / 60000);
          const seconds = Math.round((ms % 60000) / 1000);
          return `${minutes}m${seconds}s`;
        };
        
        return (
          <div className="mt-2 flex items-center gap-4 text-xs text-gray-500">
            <span>
              开始: {displayStartTime.toLocaleTimeString()}
            </span>
            {displayEndTime && (
              <>
                <span>
                  完成: {displayEndTime.toLocaleTimeString()}
                </span>
                <span className="font-medium text-gray-600 dark:text-gray-400">
                  总耗时: {formatTime(displayEndTime.getTime() - displayStartTime.getTime())}
                </span>
              </>
            )}
          </div>
        );
      })()}
    </div>
  );
}

export default TaskProgress;
