"use client";

/**
 * StageVersionSelector — 阶段版本历史选择器（下拉形式）
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

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    onChange(val === "current" ? null : Number(val));
  };

  const selectValue = selectedVersion === null ? "current" : String(selectedVersion);

  return (
    <div className="flex items-center gap-1 ml-auto shrink-0">
      <History className="h-3 w-3 text-gray-400 shrink-0" />
      <span className="text-[10px] text-gray-400">版本:</span>
      <select
        value={selectValue}
        onChange={handleChange}
        disabled={disabled}
        className={`text-[10px] rounded border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-1 py-0.5 text-gray-700 dark:text-gray-300 focus:outline-none focus:ring-1 focus:ring-blue-400 ${
          disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"
        } ${
          selectedVersion !== null
            ? "text-blue-700 dark:text-blue-300 font-semibold border-blue-300 dark:border-blue-700"
            : ""
        }`}
      >
        {snapshots.map((s) => (
          <option key={s.version} value={String(s.version)}>
            v{s.version}{s.completed_at ? ` ${formatTime(s.completed_at)}` : ""}
            {s.retry_reason ? ` · ${s.retry_reason}` : ""}
          </option>
        ))}
        <option value="current">当前</option>
      </select>
    </div>
  );
}
