/**
 * 轻量任务确认卡片
 * 
 * 当 LLM 检测到用户消息匹配 SOP 任务时，展示简洁的任务简介供用户确认：
 * - pending: 展示任务描述 + [使用此任务] / [继续对话] 按钮
 * - confirmed: 绿色边框 + "✅ 已进入任务配置"
 * - dismissed: 灰色半透明 + "已跳过"
 * 
 * 替代原 TaskParamCard (~1300行) 的职责。
 */

"use client";

import React, { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  CheckCircle2,
  XCircle,
  Loader2,
  ArrowRight,
  MessageSquare,
  AlertCircle,
} from "lucide-react";
import { sopService, TaskMeta } from "@/lib/sopService";

// =============================================================================
// 类型定义
// =============================================================================

export type CardStatus = "pending" | "confirmed" | "dismissed";

export interface TaskConfirmCardProps {
  /** 任务类型 ID（从 isTaskParamJson 解析得到） */
  taskType: string;
  /** LLM 提取的参数（传递给 ConfigPanel 预填） */
  extractedParams?: Record<string, any>;
  /** 用户点击 "使用此任务" */
  onConfirm: (taskType: string, extractedParams?: Record<string, any>) => void;
  /** 用户点击 "继续对话" */
  onDismiss: (taskType: string) => void;
  /** 卡片状态（由父组件管理） */
  status: CardStatus;
}

// 任务图标映射
const TASK_ICON_MAP: Record<string, string> = {
  "scorecard_development": "📊",
  "rule_mining": "🔍",
};

// =============================================================================
// 主组件
// =============================================================================

export function TaskConfirmCard({
  taskType,
  extractedParams,
  onConfirm,
  onDismiss,
  status,
}: TaskConfirmCardProps) {
  const [taskMeta, setTaskMeta] = useState<TaskMeta | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  // 加载任务元数据
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(false);

    sopService
      .getTaskDefinition(taskType)
      .then((meta) => {
        if (!cancelled) {
          setTaskMeta(meta);
          setLoading(false);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError(true);
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [taskType]);

  // === confirmed 状态 ===
  if (status === "confirmed") {
    return (
      <Card className="border-green-300 dark:border-green-700 bg-green-50/50 dark:bg-green-950/20">
        <CardContent className="py-3 px-4 flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-400 shrink-0" />
          <span className="text-sm text-green-700 dark:text-green-300">
            ✅ 已进入任务配置 —{" "}
            <span className="font-medium">
              {taskMeta?.task_name || taskType}
            </span>
          </span>
        </CardContent>
      </Card>
    );
  }

  // === dismissed 状态 ===
  if (status === "dismissed") {
    return (
      <Card className="border-gray-200 dark:border-gray-700 opacity-60">
        <CardContent className="py-3 px-4 flex items-center gap-2">
          <XCircle className="h-4 w-4 text-gray-400 shrink-0" />
          <span className="text-sm text-gray-500 dark:text-gray-400">
            已跳过 —{" "}
            <span className="font-medium">
              {taskMeta?.task_name || taskType}
            </span>
          </span>
        </CardContent>
      </Card>
    );
  }

  // === loading 状态 ===
  if (loading) {
    return (
      <Card className="border-blue-200 dark:border-blue-800">
        <CardContent className="py-4 px-4">
          <div className="flex items-center gap-3">
            <Loader2 className="h-5 w-5 text-blue-500 animate-spin shrink-0" />
            <div className="space-y-2 flex-1">
              <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded animate-pulse w-1/3" />
              <div className="h-3 bg-gray-100 dark:bg-gray-800 rounded animate-pulse w-2/3" />
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // === error 状态（最小卡片，用 taskType 字符串展示） ===
  if (error || !taskMeta) {
    return (
      <Card className="border-orange-200 dark:border-orange-800">
        <CardContent className="py-3 px-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-orange-500 shrink-0" />
              <div>
                <div className="text-sm font-medium">
                  检测到可能的 SOP 任务
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                  任务类型: {taskType}（详情加载失败）
                </div>
              </div>
            </div>
            <div className="flex gap-2 shrink-0">
              <Button
                variant="outline"
                size="sm"
                onClick={() => onDismiss(taskType)}
              >
                <MessageSquare className="h-3.5 w-3.5 mr-1" />
                继续对话
              </Button>
              <Button
                size="sm"
                onClick={() => onConfirm(taskType, extractedParams)}
              >
                <ArrowRight className="h-3.5 w-3.5 mr-1" />
                使用此任务
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // === pending 状态（正常卡片） ===
  const icon = TASK_ICON_MAP[taskType] || taskMeta.icon || "📋";
  const stagesPreview = taskMeta.stages
    ?.slice(0, 5)
    .map((s) => s.name)
    .join(" → ");
  const hasMoreStages = (taskMeta.stages?.length || 0) > 5;

  return (
    <Card className="border-blue-200 dark:border-blue-800 bg-blue-50/30 dark:bg-blue-950/10">
      <CardHeader className="py-3 px-4 pb-0">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <span className="text-lg">{icon}</span>
            <div>
              <CardTitle className="text-sm font-semibold">
                检测到可能匹配的 SOP 任务
              </CardTitle>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent className="py-3 px-4 space-y-3">
        {/* 任务名称和描述 */}
        <div>
          <div className="text-base font-medium text-gray-900 dark:text-gray-100">
            【{taskMeta.task_name}】
          </div>
          <div className="text-sm text-gray-600 dark:text-gray-400 mt-1 leading-relaxed">
            {taskMeta.description}
          </div>
        </div>

        {/* 阶段预览 */}
        {stagesPreview && (
          <div className="text-xs text-gray-500 dark:text-gray-400 bg-white/60 dark:bg-gray-800/40 rounded-md px-3 py-2">
            <span className="font-medium text-gray-600 dark:text-gray-300">
              流程阶段：
            </span>
            {stagesPreview}
            {hasMoreStages && ` … 等 ${taskMeta.stages?.length} 个阶段`}
          </div>
        )}

        {/* 预计时间 */}
        {taskMeta.estimated_time && (
          <div className="text-xs text-gray-500 dark:text-gray-400">
            预计耗时：{taskMeta.estimated_time}
          </div>
        )}

        {/* 操作按钮 */}
        <div className="flex gap-2 pt-1">
          <Button
            variant="outline"
            size="sm"
            className="text-gray-600 dark:text-gray-400"
            onClick={() => onDismiss(taskType)}
          >
            <MessageSquare className="h-3.5 w-3.5 mr-1" />
            继续对话
          </Button>
          <Button
            size="sm"
            className="bg-blue-600 hover:bg-blue-700 text-white"
            onClick={() => onConfirm(taskType, extractedParams)}
          >
            <ArrowRight className="h-3.5 w-3.5 mr-1" />
            使用此任务
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export default TaskConfirmCard;
