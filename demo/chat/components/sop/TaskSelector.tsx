"use client";

import React, { useState, useEffect } from "react";
import { Target, Loader2, ChevronRight } from "lucide-react";
import { sopService, TaskListItem } from "@/lib/sopService";
import { cn } from "@/lib/utils";

// 任务图标映射
const TASK_ICONS: Record<string, string> = {
  target: "🎯",
  chart: "📊",
  filter: "🔧",
  trending: "📈",
  default: "📋",
};

interface TaskSelectorProps {
  selectedTaskId: string | null;
  onTaskSelect: (taskId: string) => void;
  isExecuting?: boolean;
  className?: string;
}

export function TaskSelector({
  selectedTaskId,
  onTaskSelect,
  isExecuting = false,
  className,
}: TaskSelectorProps) {
  const [tasks, setTasks] = useState<TaskListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 加载可用任务列表
  useEffect(() => {
    const loadTasks = async () => {
      try {
        setLoading(true);
        setError(null);
        const taskList = await sopService.getAvailableTasks();
        setTasks(taskList);
      } catch (err) {
        console.error("Failed to load tasks:", err);
        setError("加载任务列表失败");
      } finally {
        setLoading(false);
      }
    };

    loadTasks();
  }, []);

  const getTaskIcon = (iconName: string) => {
    return TASK_ICONS[iconName] || TASK_ICONS.default;
  };

  if (loading) {
    return (
      <div className={cn("p-4", className)}>
        <div className="flex items-center gap-2 mb-3">
          <Target className="h-4 w-4 text-gray-500" />
          <span className="text-sm font-medium text-gray-600 dark:text-gray-400">
            TaskType
          </span>
        </div>
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={cn("p-4", className)}>
        <div className="flex items-center gap-2 mb-3">
          <Target className="h-4 w-4 text-gray-500" />
          <span className="text-sm font-medium text-gray-600 dark:text-gray-400">
            TaskType
          </span>
        </div>
        <div className="text-center py-4 text-sm text-red-500">{error}</div>
      </div>
    );
  }

  return (
    <div className={cn("flex flex-col", className)}>
      {/* 标题 */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-200 dark:border-gray-800">
        <Target className="h-4 w-4 text-gray-500" />
        <span className="text-sm font-medium text-gray-600 dark:text-gray-400">
          TaskType
        </span>
      </div>

      {/* 任务列表 */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {tasks.length === 0 ? (
          <div className="text-center py-4 text-sm text-gray-500">
            暂无可用任务
          </div>
        ) : (
          tasks.map((task) => {
            const isSelected = selectedTaskId === task.task_id;
            return (
              <button
                key={task.task_id}
                onClick={() => !isExecuting && onTaskSelect(task.task_id)}
                disabled={isExecuting}
                className={cn(
                  "w-full flex items-start gap-3 p-3 rounded-lg text-left transition-all duration-200",
                  isExecuting && "opacity-50 cursor-not-allowed",
                  isSelected
                    ? "bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800"
                    : "hover:bg-gray-50 dark:hover:bg-gray-900/50 border border-transparent"
                )}
              >
                {/* 图标 */}
                <div
                  className={cn(
                    "flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center text-lg",
                    isSelected
                      ? "bg-blue-100 dark:bg-blue-900/50"
                      : "bg-gray-100 dark:bg-gray-800"
                  )}
                >
                  {getTaskIcon(task.icon)}
                </div>

                {/* 内容 */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span
                      className={cn(
                        "font-medium text-sm",
                        isSelected
                          ? "text-blue-700 dark:text-blue-300"
                          : "text-gray-700 dark:text-gray-300"
                      )}
                    >
                      {task.task_name}
                    </span>
                    {isSelected && (
                      <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
                    )}
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 line-clamp-2">
                    {task.description}
                  </p>
                </div>

                {/* 箭头 */}
                <ChevronRight
                  className={cn(
                    "h-4 w-4 flex-shrink-0 mt-1 transition-transform",
                    isSelected
                      ? "text-blue-500 rotate-90"
                      : "text-gray-400"
                  )}
                />
              </button>
            );
          })
        )}
      </div>
    </div>
  );
}

export default TaskSelector;
