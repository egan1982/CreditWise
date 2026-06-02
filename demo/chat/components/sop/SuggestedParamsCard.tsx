"use client";

/**
 * SuggestedParamsCard — AI 参数建议卡片
 *
 * 在专家模式阶段 AI 分析完成后展示，显示 AI 建议的参数变更（before → after diff）。
 * 提供两个操作：仅填入参数 / 填入并立即重试。
 */

import React from "react";
import { Lightbulb, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";

export interface SuggestedParamsCardProps {
  /** AI 建议的参数字典 {paramKey: newValue} */
  suggestedParams: Record<string, unknown>;
  /** 当前阶段实际使用的参数（用于显示 before 值） */
  currentParams: Record<string, unknown>;
  /** 是否正在重试中（禁用按钮） */
  isRetrying?: boolean;
  /** 仅填入参数回调（不触发重试）*/
  onApplyOnly: (mergedParams: Record<string, unknown>) => void;
  /** 填入并立即重试回调 */
  onApplyAndRetry: (mergedParams: Record<string, unknown>) => void;
}

function formatValue(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "boolean") return v ? "true" : "false";
  return String(v);
}

export function SuggestedParamsCard({
  suggestedParams,
  currentParams,
  isRetrying = false,
  onApplyOnly,
  onApplyAndRetry,
}: SuggestedParamsCardProps) {
  const entries = Object.entries(suggestedParams);
  if (entries.length === 0) return null;

  const mergedParams = { ...currentParams, ...suggestedParams };

  return (
    <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/20 p-3">
      {/* 标题 */}
      <div className="flex items-center gap-1.5 mb-2">
        <Lightbulb className="h-3.5 w-3.5 text-amber-500 shrink-0" />
        <span className="text-xs font-semibold text-amber-700 dark:text-amber-400">
          AI 参数建议
        </span>
      </div>

      {/* before → after diff 列表 */}
      <div className="space-y-1 mb-3">
        {entries.map(([key, newVal]) => {
          const oldVal = currentParams[key];
          const unchanged = String(oldVal) === String(newVal);
          return (
            <div key={key} className="flex items-center gap-2 text-xs">
              <span className="font-mono text-gray-600 dark:text-gray-400 min-w-[120px] truncate">
                {key}
              </span>
              {unchanged ? (
                <span className="text-gray-400">{formatValue(newVal)}</span>
              ) : (
                <>
                  <span className="text-gray-400 line-through">
                    {formatValue(oldVal)}
                  </span>
                  <ArrowRight className="h-3 w-3 text-amber-500 shrink-0" />
                  <span className="font-semibold text-green-600 dark:text-green-400">
                    {formatValue(newVal)}
                  </span>
                </>
              )}
            </div>
          );
        })}
      </div>

      {/* 操作按钮 */}
      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          className="h-6 px-2 text-xs"
          disabled={isRetrying}
          onClick={() => onApplyOnly(mergedParams)}
        >
          仅填入参数
        </Button>
        <Button
          size="sm"
          className="h-6 px-2 text-xs bg-amber-500 hover:bg-amber-600 text-white"
          disabled={isRetrying}
          onClick={() => onApplyAndRetry(mergedParams)}
        >
          填入并立即重试
        </Button>
      </div>
    </div>
  );
}
