"use client";

import React from "react";
import { cn } from "@/lib/utils";
import { InteractionMode } from "@/hooks/use-mode";

interface ModeSelectorProps {
  interactionMode: InteractionMode;
  onInteractionModeChange: (mode: InteractionMode) => void;
  disabled?: boolean;
  className?: string;
}

/**
 * 交互模式选择器组件
 * 
 * 提供交互模式的选择：
 * - 自动模式：系统自动执行所有阶段
 * - 专家模式：用户手动控制每个阶段
 * 
 * 注意：执行引擎统一使用 Pipeline（LLM SOP 执行模式已废弃）
 * LLM 作为智能入口（参数推断器），而非执行引擎
 */
export function ModeSelector({
  interactionMode,
  onInteractionModeChange,
  disabled = false,
  className,
}: ModeSelectorProps) {
  return (
    <div className={cn("space-y-4", className)}>
      {/* 交互模式 */}
      <div className="space-y-2">
        <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
          交互模式
        </label>
        <div className="flex gap-2">
          <button
            type="button"
            disabled={disabled}
            onClick={() => onInteractionModeChange("auto")}
            className={cn(
              "flex-1 px-4 py-2 rounded-lg border text-sm font-medium transition-all",
              interactionMode === "auto"
                ? "bg-green-50 border-green-500 text-green-700 dark:bg-green-900/30 dark:border-green-400 dark:text-green-300"
                : "bg-white border-gray-300 text-gray-700 hover:bg-gray-50 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700",
              disabled && "opacity-50 cursor-not-allowed"
            )}
          >
            <div className="flex items-center justify-center gap-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              <span>自动模式</span>
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              全自动执行
            </div>
          </button>
          
          <button
            type="button"
            disabled={disabled}
            onClick={() => onInteractionModeChange("expert")}
            className={cn(
              "flex-1 px-4 py-2 rounded-lg border text-sm font-medium transition-all",
              interactionMode === "expert"
                ? "bg-orange-50 border-orange-500 text-orange-700 dark:bg-orange-900/30 dark:border-orange-400 dark:text-orange-300"
                : "bg-white border-gray-300 text-gray-700 hover:bg-gray-50 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700",
              disabled && "opacity-50 cursor-not-allowed"
            )}
          >
            <div className="flex items-center justify-center gap-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              <span>专家模式</span>
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              手动控制阶段
            </div>
          </button>
        </div>
      </div>

      {/* 模式说明 */}
      <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg text-xs text-gray-600 dark:text-gray-400">
        {interactionMode === "auto" && (
          <p>使用 Pipeline 全自动执行所有阶段，适合标准化任务。</p>
        )}
        {interactionMode === "expert" && (
          <p>使用 Pipeline 执行，但可手动控制每个阶段的执行和参数调整。</p>
        )}
      </div>
    </div>
  );
}

export default ModeSelector;
