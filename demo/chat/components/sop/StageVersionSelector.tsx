"use client";

/**
 * StageVersionSelector — 阶段版本历史选择器
 *
 * 展示在阶段结果 Tab 栏右侧（仅当有历史快照时）。
 * 支持切换查看历史版本的输出、参数和 AI 分析。
 */

import React from "react";
import { History } from "lucide-react";

export interface StageSnapshotMeta {
  version: number;
  completed_at: string | null;
  params_used: Record<string, unknown>;
  output_preview: Record<string, unknown> | null;
  ai_analysis: string | null;
  suggested_params: Record<string, unknown> | null;
  execution_time_ms: number | null;
  retry_reason: string | null;
}

export interface StageVersionSelectorProps {
  snapshots: StageSnapshotMeta[];
  /** null 表示当前版本 */
  selectedVersion: number | null;
  onChange: (version: number | null) => void;
  /** 正在重试时禁用切换 */
  disabled?: boolean;
}

function formatTime(iso: string | null): string {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
}

export function StageVersionSelector({
  snapshots,
  selectedVersion,
  onChange,
  disabled = false,
}: StageVersionSelectorProps) {
  if (!snapshots || snapshots.length === 0) return null;

  return (
    <div className="flex items-center gap-1 ml-auto">
      <History className="h-3 w-3 text-gray-400 shrink-0" />
      <span className="text-[10px] text-gray-400 mr-0.5">版本:</span>
      {snapshots.map((s) => (
        <button
          key={s.version}
          disabled={disabled}
          onClick={() => onChange(s.version)}
          className={`px-1.5 py-0.5 rounded text-[10px] transition-colors ${
            selectedVersion === s.version
              ? "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300 font-semibold"
              : "text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800"
          } ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
        >
          v{s.version}
          {s.completed_at ? ` ${formatTime(s.completed_at)}` : ""}
        </button>
      ))}
      <button
        disabled={disabled}
        onClick={() => onChange(null)}
        className={`px-1.5 py-0.5 rounded text-[10px] transition-colors ${
          selectedVersion === null
            ? "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300 font-semibold"
            : "text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800"
        } ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
      >
        当前
      </button>
    </div>
  );
}
