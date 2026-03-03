"use client";

import React, { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  ChevronDown,
  ChevronUp,
  Terminal,
  Info,
  AlertTriangle,
  AlertCircle,
  CheckCircle2,
  Clock,
  Trash2,
  Download,
  Filter,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";

// =============================================================================
// 类型定义
// =============================================================================

export type LogLevel = "debug" | "info" | "warning" | "error" | "success";

export interface LogEntry {
  id: string;
  timestamp: Date;
  level: LogLevel;
  stage?: string;
  message: string;
  details?: string;
}

interface ExecutionLogPanelProps {
  logs: LogEntry[];
  isExpanded?: boolean;
  onToggleExpand?: () => void;
  onClear?: () => void;
  maxHeight?: number;
  className?: string;
  title?: string;
  showTimestamp?: boolean;
  showStage?: boolean;
  autoScroll?: boolean;
}

// =============================================================================
// 日志级别配置
// =============================================================================

const LOG_LEVEL_CONFIG: Record<LogLevel, {
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  bgColor: string;
  label: string;
}> = {
  debug: {
    icon: Terminal,
    color: "text-gray-500 dark:text-gray-400",
    bgColor: "bg-gray-50 dark:bg-gray-900/30",
    label: "调试",
  },
  info: {
    icon: Info,
    color: "text-blue-600 dark:text-blue-400",
    bgColor: "bg-blue-50 dark:bg-blue-900/20",
    label: "信息",
  },
  warning: {
    icon: AlertTriangle,
    color: "text-yellow-600 dark:text-yellow-400",
    bgColor: "bg-yellow-50 dark:bg-yellow-900/20",
    label: "警告",
  },
  error: {
    icon: AlertCircle,
    color: "text-red-600 dark:text-red-400",
    bgColor: "bg-red-50 dark:bg-red-900/20",
    label: "错误",
  },
  success: {
    icon: CheckCircle2,
    color: "text-green-600 dark:text-green-400",
    bgColor: "bg-green-50 dark:bg-green-900/20",
    label: "成功",
  },
};

// =============================================================================
// 单条日志组件
// =============================================================================

interface LogEntryItemProps {
  entry: LogEntry;
  showTimestamp: boolean;
  showStage: boolean;
  isExpanded: boolean;
  onToggle: () => void;
}

function LogEntryItem({
  entry,
  showTimestamp,
  showStage,
  isExpanded,
  onToggle,
}: LogEntryItemProps) {
  const config = LOG_LEVEL_CONFIG[entry.level];
  const Icon = config.icon;
  const hasDetails = !!entry.details;

  return (
    <div
      className={cn(
        "px-2 py-1.5 border-b border-gray-100 dark:border-gray-800 last:border-0",
        hasDetails && "cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-900/50"
      )}
      onClick={hasDetails ? onToggle : undefined}
    >
      <div className="flex items-start gap-2">
        {/* 图标 */}
        <Icon className={cn("h-3.5 w-3.5 mt-0.5 flex-shrink-0", config.color)} />

        {/* 时间戳 */}
        {showTimestamp && (
          <span className="text-xs text-gray-400 font-mono flex-shrink-0">
            {entry.timestamp.toLocaleTimeString("zh-CN", {
              hour: "2-digit",
              minute: "2-digit",
              second: "2-digit",
            })}
          </span>
        )}

        {/* 阶段标签 */}
        {showStage && entry.stage && (
          <Badge variant="outline" className="text-[10px] px-1 py-0 h-4 flex-shrink-0">
            {entry.stage}
          </Badge>
        )}

        {/* 消息内容 */}
        <span className={cn("text-xs flex-1", config.color)}>
          {entry.message}
        </span>

        {/* 展开/折叠指示器 */}
        {hasDetails && (
          <span className="flex-shrink-0">
            {isExpanded ? (
              <ChevronUp className="h-3 w-3 text-gray-400" />
            ) : (
              <ChevronDown className="h-3 w-3 text-gray-400" />
            )}
          </span>
        )}
      </div>

      {/* 详情展开区域 */}
      {hasDetails && isExpanded && (
        <div className="mt-1.5 ml-5 p-2 bg-gray-50 dark:bg-gray-900/50 rounded text-xs font-mono text-gray-600 dark:text-gray-400 whitespace-pre-wrap break-all">
          {entry.details}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// 日志过滤器组件
// =============================================================================

interface LogFilterProps {
  activeFilters: Set<LogLevel>;
  onToggleFilter: (level: LogLevel) => void;
  onClearFilters: () => void;
  logCounts: Record<LogLevel, number>;
}

function LogFilter({
  activeFilters,
  onToggleFilter,
  onClearFilters,
  logCounts,
}: LogFilterProps) {
  const levels: LogLevel[] = ["debug", "info", "warning", "error", "success"];

  return (
    <div className="flex items-center gap-1 px-2 py-1.5 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
      <Filter className="h-3.5 w-3.5 text-gray-400 mr-1" />
      {levels.map((level) => {
        const config = LOG_LEVEL_CONFIG[level];
        const count = logCounts[level] || 0;
        const isActive = activeFilters.has(level);

        return (
          <button
            key={level}
            onClick={() => onToggleFilter(level)}
            className={cn(
              "flex items-center gap-0.5 px-1.5 py-0.5 rounded text-xs transition-colors",
              isActive
                ? config.bgColor
                : "bg-transparent hover:bg-gray-100 dark:hover:bg-gray-800"
            )}
          >
            <span className={cn(isActive ? config.color : "text-gray-400")}>
              {config.label}
            </span>
            {count > 0 && (
              <span className="text-[10px] text-gray-400">({count})</span>
            )}
          </button>
        );
      })}
      {activeFilters.size > 0 && (
        <button
          onClick={onClearFilters}
          className="ml-1 p-0.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
          title="清除过滤"
        >
          <X className="h-3 w-3 text-gray-400" />
        </button>
      )}
    </div>
  );
}

// =============================================================================
// 主组件
// =============================================================================

export function ExecutionLogPanel({
  logs,
  isExpanded = true,
  onToggleExpand,
  onClear,
  maxHeight = 300,
  className,
  title = "执行日志",
  showTimestamp = true,
  showStage = true,
  autoScroll = true,
}: ExecutionLogPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [expandedEntries, setExpandedEntries] = useState<Set<string>>(new Set());
  const [activeFilters, setActiveFilters] = useState<Set<LogLevel>>(new Set());
  const [showFilter, setShowFilter] = useState(false);

  // 自动滚动到底部
  useEffect(() => {
    if (autoScroll && scrollRef.current && isExpanded) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs, autoScroll, isExpanded]);

  // 切换单条日志的展开状态
  const toggleEntry = (id: string) => {
    setExpandedEntries((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  // 切换过滤器
  const toggleFilter = (level: LogLevel) => {
    setActiveFilters((prev) => {
      const next = new Set(prev);
      if (next.has(level)) {
        next.delete(level);
      } else {
        next.add(level);
      }
      return next;
    });
  };

  // 清除过滤器
  const clearFilters = () => {
    setActiveFilters(new Set());
  };

  // 计算每个级别的日志数量
  const logCounts = logs.reduce((acc, log) => {
    acc[log.level] = (acc[log.level] || 0) + 1;
    return acc;
  }, {} as Record<LogLevel, number>);

  // 过滤日志
  const filteredLogs = activeFilters.size > 0
    ? logs.filter((log) => activeFilters.has(log.level))
    : logs;

  // 导出日志
  const exportLogs = () => {
    const content = logs
      .map(
        (log) =>
          `[${log.timestamp.toISOString()}] [${log.level.toUpperCase()}]${
            log.stage ? ` [${log.stage}]` : ""
          } ${log.message}${log.details ? `\n${log.details}` : ""}`
      )
      .join("\n");

    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `execution-log-${new Date().toISOString().slice(0, 10)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div
      className={cn(
        "border rounded-lg overflow-hidden bg-white dark:bg-gray-950",
        className
      )}
    >
      {/* 头部 */}
      <div className="flex items-center justify-between px-3 py-2 bg-gray-50 dark:bg-gray-900/50 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2">
          <Terminal className="h-4 w-4 text-gray-500" />
          <span className="font-medium text-sm">{title}</span>
          <Badge variant="secondary" className="text-xs">
            {filteredLogs.length}
            {activeFilters.size > 0 && `/${logs.length}`}
          </Badge>
        </div>

        <div className="flex items-center gap-1">
          {/* 过滤器切换 */}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowFilter(!showFilter)}
            className={cn("h-6 w-6 p-0", showFilter && "bg-gray-200 dark:bg-gray-700")}
            title="过滤"
          >
            <Filter className="h-3.5 w-3.5" />
          </Button>

          {/* 导出按钮 */}
          <Button
            variant="ghost"
            size="sm"
            onClick={exportLogs}
            className="h-6 w-6 p-0"
            title="导出日志"
            disabled={logs.length === 0}
          >
            <Download className="h-3.5 w-3.5" />
          </Button>

          {/* 清除按钮 */}
          {onClear && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onClear}
              className="h-6 w-6 p-0"
              title="清除日志"
              disabled={logs.length === 0}
            >
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          )}

          {/* 展开/折叠按钮 */}
          {onToggleExpand && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onToggleExpand}
              className="h-6 w-6 p-0"
              title={isExpanded ? "折叠" : "展开"}
            >
              {isExpanded ? (
                <ChevronUp className="h-3.5 w-3.5" />
              ) : (
                <ChevronDown className="h-3.5 w-3.5" />
              )}
            </Button>
          )}
        </div>
      </div>

      {/* 过滤器栏 */}
      {showFilter && (
        <LogFilter
          activeFilters={activeFilters}
          onToggleFilter={toggleFilter}
          onClearFilters={clearFilters}
          logCounts={logCounts}
        />
      )}

      {/* 日志内容 */}
      {isExpanded && (
        <div
          ref={scrollRef}
          className="overflow-auto"
          style={{ maxHeight: `${maxHeight}px` }}
        >
          {filteredLogs.length === 0 ? (
            <div className="flex items-center justify-center py-8 text-gray-400 text-sm">
              <Clock className="h-4 w-4 mr-2" />
              暂无日志
            </div>
          ) : (
            filteredLogs.map((entry) => (
              <LogEntryItem
                key={entry.id}
                entry={entry}
                showTimestamp={showTimestamp}
                showStage={showStage}
                isExpanded={expandedEntries.has(entry.id)}
                onToggle={() => toggleEntry(entry.id)}
              />
            ))
          )}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// 日志工具函数
// =============================================================================

let logIdCounter = 0;

export function createLogEntry(
  level: LogLevel,
  message: string,
  stage?: string,
  details?: string
): LogEntry {
  return {
    id: `log-${Date.now()}-${++logIdCounter}`,
    timestamp: new Date(),
    level,
    stage,
    message,
    details,
  };
}

export function useExecutionLogs(maxLogs = 500) {
  const [logs, setLogs] = useState<LogEntry[]>([]);

  const addLog = (
    level: LogLevel,
    message: string,
    stage?: string,
    details?: string
  ) => {
    setLogs((prev) => {
      const newLogs = [...prev, createLogEntry(level, message, stage, details)];
      // 限制日志数量
      if (newLogs.length > maxLogs) {
        return newLogs.slice(-maxLogs);
      }
      return newLogs;
    });
  };

  const clearLogs = () => {
    setLogs([]);
  };

  const debug = (message: string, stage?: string, details?: string) =>
    addLog("debug", message, stage, details);
  const info = (message: string, stage?: string, details?: string) =>
    addLog("info", message, stage, details);
  const warning = (message: string, stage?: string, details?: string) =>
    addLog("warning", message, stage, details);
  const error = (message: string, stage?: string, details?: string) =>
    addLog("error", message, stage, details);
  const success = (message: string, stage?: string, details?: string) =>
    addLog("success", message, stage, details);

  return {
    logs,
    addLog,
    clearLogs,
    debug,
    info,
    warning,
    error,
    success,
  };
}

export default ExecutionLogPanel;
