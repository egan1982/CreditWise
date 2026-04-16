"use client";

import { getApiUrl } from "@/lib/config";
import React, { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  Pause,
  Square,
  RefreshCw,
  Eye,
  Trash2,
  Download,
  ChevronLeft,
  ChevronRight,
  AlertCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Checkbox } from "@/components/ui/checkbox";

// =============================================================================
// 类型定义
// =============================================================================

interface TaskHistoryItem {
  record_id: string;
  task_type: string;
  task_category: string;
  execution_id: string | null;
  session_id: string | null;
  interaction_mode: string;
  status: string;
  progress: number;
  current_stage: string | null;
  message: string | null;
  created_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  duration_seconds: number | null;
}

interface TaskHistoryCompactProps {
  onViewDetail?: (recordId: string) => void;
  onLoadResult?: (recordId: string) => void;
  className?: string;
}

// =============================================================================
// 任务类型和状态配置
// =============================================================================

const TASK_TYPE_LABELS: Record<string, string> = {
  // SOP 任务类型
  scorecard_dev: "评分卡开发",
  rule_mining: "规则挖掘",
  // 推理任务类型（普通AI对话）
  inference: "AI对话",
  chat: "AI对话",
};

const TASK_TYPE_ICONS: Record<string, string> = {
  // SOP 任务类型
  scorecard_dev: "📊",
  rule_mining: "🔍",
  // 推理任务类型（普通AI对话）
  inference: "💬",
  chat: "💬",
};

const STATUS_CONFIG: Record<string, {
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  bgColor: string;
  label: string;
}> = {
  pending: {
    icon: Clock,
    color: "text-gray-500",
    bgColor: "bg-gray-100 dark:bg-gray-800",
    label: "等待中",
  },
  running: {
    icon: Loader2,
    color: "text-blue-500",
    bgColor: "bg-blue-50 dark:bg-blue-900/20",
    label: "执行中",
  },
  completed: {
    icon: CheckCircle2,
    color: "text-green-500",
    bgColor: "bg-green-50 dark:bg-green-900/20",
    label: "已完成",
  },
  failed: {
    icon: XCircle,
    color: "text-red-500",
    bgColor: "bg-red-50 dark:bg-red-900/20",
    label: "失败",
  },
  stopped: {
    icon: Square,
    color: "text-yellow-500",
    bgColor: "bg-yellow-50 dark:bg-yellow-900/20",
    label: "已停止",
  },
  paused: {
    icon: Pause,
    color: "text-yellow-500",
    bgColor: "bg-yellow-50 dark:bg-yellow-900/20",
    label: "已暂停",
  },
  cancelled: {
    icon: XCircle,
    color: "text-gray-500",
    bgColor: "bg-gray-100 dark:bg-gray-800",
    label: "已取消",
  },
};

// =============================================================================
// 工具函数
// =============================================================================

function formatDuration(seconds: number | null): string {
  if (seconds === null || seconds === undefined) return "-";
  if (seconds < 60) return `${Math.round(seconds)}秒`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}分${Math.round(seconds % 60)}秒`;
  return `${Math.floor(seconds / 3600)}时${Math.floor((seconds % 3600) / 60)}分`;
}

function formatDateTime(isoString: string | null): string {
  if (!isoString) return "-";
  const date = new Date(isoString);
  return date.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// =============================================================================
// 紧凑型任务卡片组件
// =============================================================================

function TaskCard({
  record,
  onViewDetail,
  onLoadResult,
  onDelete,
  selectMode,
  selected,
  onSelect,
}: {
  record: TaskHistoryItem;
  onViewDetail?: (recordId: string) => void;
  onLoadResult?: (recordId: string) => void;
  onDelete?: (recordId: string) => void;
  selectMode?: boolean;
  selected?: boolean;
  onSelect?: (recordId: string, checked: boolean) => void;
}) {
  const statusConfig = STATUS_CONFIG[record.status] || STATUS_CONFIG.pending;
  const StatusIcon = statusConfig.icon;
  const isRunning = record.status === "running";
  const taskIcon = TASK_TYPE_ICONS[record.task_type] || "📋";
  const taskLabel = TASK_TYPE_LABELS[record.task_type] || record.task_type;

  return (
    <div className={cn(
      "px-3 py-2 rounded-md border border-gray-200 dark:border-gray-700",
      "hover:border-gray-300 dark:hover:border-gray-600 transition-colors",
      "bg-white dark:bg-gray-800/50",
      selected && "border-blue-400 dark:border-blue-500 bg-blue-50/50 dark:bg-blue-900/10"
    )}>
      {/* 单行布局：Checkbox + 任务信息 + 状态 + 操作 */}
      <div className="flex items-center justify-between gap-2">
        {/* 左侧：Checkbox + 任务类型 + 时间 + 进度 */}
        <div className="flex items-center gap-2 min-w-0 flex-1">
          {/* 多选 Checkbox */}
          {selectMode && (
            <Checkbox
              checked={selected}
              onCheckedChange={(checked) => onSelect?.(record.record_id, !!checked)}
              disabled={record.status === "running"}
              className="shrink-0 border-gray-400 dark:border-gray-400"
            />
          )}
          {/* 任务类型 */}
          <div className="flex items-center gap-1 shrink-0">
            <span className="text-xs">{taskIcon}</span>
            <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
              {taskLabel}
            </span>
          </div>
          
          {/* 分隔符 */}
          <div className="w-px h-3 bg-gray-300 dark:bg-gray-600 shrink-0" />
          
          {/* 时间信息 */}
          <span className="text-[10px] text-gray-500 dark:text-gray-400 shrink-0">
            {formatDateTime(record.started_at || record.created_at)}
          </span>
          
          {/* 进度 */}
          <span className="text-[10px] font-medium text-gray-600 dark:text-gray-400 shrink-0">
            {Math.round(record.progress)}%
          </span>
        </div>

        {/* 中间：状态标签 */}
        <Badge
          variant="outline"
          className={cn(
            "flex items-center gap-1 text-[10px] px-1.5 py-0.5 shrink-0",
            statusConfig.color,
            statusConfig.bgColor
          )}
        >
          <StatusIcon className={cn("h-2.5 w-2.5", isRunning && "animate-spin")} />
          {statusConfig.label}
        </Badge>

        {/* 右侧：操作按钮 */}
        <div className="flex items-center gap-0.5 shrink-0">
          {/* 查看详情 */}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onViewDetail?.(record.record_id)}
            className="h-5 w-5 p-0 hover:bg-gray-100 dark:hover:bg-gray-700"
            title="查看详情"
          >
            <Eye className="h-2.5 w-2.5 text-gray-500" />
          </Button>

          {/* 删除 */}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onDelete?.(record.record_id)}
            className="h-5 w-5 p-0 hover:bg-red-50 dark:hover:bg-red-900/20"
            title="删除"
          >
            <Trash2 className="h-2.5 w-2.5 text-red-400 hover:text-red-500" />
          </Button>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// 主组件
// =============================================================================

export function TaskHistoryCompact({
  onViewDetail,
  onLoadResult,
  className,
}: TaskHistoryCompactProps) {
  const [records, setRecords] = useState<TaskHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(8); // 紧凑模式单行布局，每页显示8条
  const [categoryFilter, setCategoryFilter] = useState<string>("all"); // 任务类别筛选

  // 删除确认
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [recordToDelete, setRecordToDelete] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  // 多选/批量删除（Phase 25）
  const [selectMode, setSelectMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [batchDeleteDialogOpen, setBatchDeleteDialogOpen] = useState(false);
  const [cleanupFiles, setCleanupFiles] = useState(true);

  // 可选中的记录（排除运行中的）
  const selectableRecords = records.filter(r => r.status !== "running");

  const handleToggleSelect = (recordId: string, checked: boolean) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (checked) next.add(recordId);
      else next.delete(recordId);
      return next;
    });
  };

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedIds(new Set(selectableRecords.map(r => r.record_id)));
    } else {
      setSelectedIds(new Set());
    }
  };

  const handleExitSelectMode = () => {
    setSelectMode(false);
    setSelectedIds(new Set());
  };

  const handleBatchDelete = async () => {
    if (selectedIds.size === 0) return;
    setDeleting(true);
    try {
      const response = await fetch(getApiUrl("/sop/history/batch-delete"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          record_ids: Array.from(selectedIds),
          cleanup_files: cleanupFiles,
        }),
      });
      if (!response.ok) throw new Error("批量删除失败");
      await loadRecords();
      setBatchDeleteDialogOpen(false);
      setSelectedIds(new Set());
      setSelectMode(false);
    } catch (err) {
      console.error("Batch delete failed:", err);
      setError("批量删除失败");
    } finally {
      setDeleting(false);
    }
  };

  // 加载数据
  const loadRecords = async () => {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      params.set("limit", String(pageSize));
      params.set("offset", String((page - 1) * pageSize));

      // 添加任务类别筛选
      if (categoryFilter !== "all") {
        params.set("task_category", categoryFilter);
      }

      const response = await fetch(getApiUrl(`/sop/history?${params.toString()}`));
      if (!response.ok) {
        throw new Error("Failed to load history");
      }

      const data = await response.json();
      setRecords(data.records || []);
      setTotal(data.total || 0);
    } catch (err) {
      console.error("Failed to load history:", err);
      setError("加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRecords();
  }, [page, categoryFilter]);

  // 删除记录
  const handleDelete = async () => {
    if (!recordToDelete) return;

    setDeleting(true);
    try {
      const response = await fetch(getApiUrl(`/sop/history/${recordToDelete}`), {
        method: "DELETE",
      });

      if (!response.ok) {
        throw new Error("Failed to delete record");
      }

      // 刷新列表
      await loadRecords();
      setDeleteDialogOpen(false);
      setRecordToDelete(null);
    } catch (err) {
      console.error("Failed to delete:", err);
      setError("删除失败");
    } finally {
      setDeleting(false);
    }
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className={cn("flex flex-col", className)}>
      {/* 头部：标题 + 筛选 + 多选 + 刷新 */}
      <div className="flex items-center justify-between gap-2 px-3 py-2 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-gray-600 dark:text-gray-400">
            历史记录 ({total})
          </span>
          {/* 任务类别筛选 */}
          <Select value={categoryFilter} onValueChange={(value) => {
            setCategoryFilter(value);
            setPage(1); // 重置到第一页
          }}>
            <SelectTrigger className="h-6 w-20 text-[10px]">
              <SelectValue placeholder="全部" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部</SelectItem>
              <SelectItem value="sop">SOP任务</SelectItem>
              <SelectItem value="inference">AI对话</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="flex items-center gap-1">
          {/* 多选切换按钮 */}
          {!selectMode ? (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSelectMode(true)}
              disabled={loading || records.length === 0}
              className="h-6 px-1.5 text-[10px]"
              title="批量选择"
            >
              <Checkbox className="h-3 w-3 mr-0.5 pointer-events-none border-gray-400 dark:border-gray-400" />
              多选
            </Button>
          ) : (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleExitSelectMode}
              className="h-6 px-1.5 text-[10px] text-gray-500"
            >
              取消
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={loadRecords}
            disabled={loading}
            className="h-6 w-6 p-0 shrink-0"
          >
            <RefreshCw className={cn("h-3 w-3", loading && "animate-spin")} />
          </Button>
        </div>
      </div>

      {/* 批量操作栏（多选模式下显示） */}
      {selectMode && (
        <div className="flex items-center justify-between gap-2 px-3 py-1.5 bg-blue-50 dark:bg-blue-900/20 border-b border-blue-200 dark:border-blue-800">
          <div className="flex items-center gap-2">
            <Checkbox
              checked={selectedIds.size > 0 && selectedIds.size === selectableRecords.length}
              onCheckedChange={(checked) => handleSelectAll(!!checked)}
              className="h-3.5 w-3.5 border-gray-400 dark:border-gray-400"
            />
            <span className="text-[10px] text-blue-700 dark:text-blue-300">
              {selectedIds.size > 0 ? `已选 ${selectedIds.size} 条` : "全选"}
            </span>
          </div>
          {selectedIds.size > 0 && (
            <Button
              variant="destructive"
              size="sm"
              onClick={() => setBatchDeleteDialogOpen(true)}
              className="h-6 px-2 text-[10px]"
            >
              <Trash2 className="h-3 w-3 mr-0.5" />
              删除 ({selectedIds.size})
            </Button>
          )}
        </div>
      )}

      {/* 内容区 */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
        {/* 错误提示 */}
        {error && (
          <div className="flex items-center gap-1.5 p-2 bg-red-50 dark:bg-red-900/20 rounded text-red-600 dark:text-red-400 text-xs">
            <AlertCircle className="h-3 w-3" />
            {error}
          </div>
        )}

        {/* 加载中 */}
        {loading ? (
          <div className="flex flex-col items-center justify-center py-8">
            <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
            <span className="text-xs text-gray-500 mt-2">加载中...</span>
          </div>
        ) : records.length === 0 ? (
          <div className="text-center py-8 text-xs text-gray-500">
            暂无历史记录
          </div>
        ) : (
          records.map((record) => (
            <TaskCard
              key={record.record_id}
              record={record}
              onViewDetail={onViewDetail}
              onLoadResult={onLoadResult}
              onDelete={(id) => {
                setRecordToDelete(id);
                setDeleteDialogOpen(true);
              }}
              selectMode={selectMode}
              selected={selectedIds.has(record.record_id)}
              onSelect={handleToggleSelect}
            />
          ))
        )}
      </div>

      {/* 分页 */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between px-3 py-2 border-t border-gray-200 dark:border-gray-700">
          <span className="text-[10px] text-gray-500">
            {page}/{totalPages}
          </span>
          <div className="flex items-center gap-1">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1 || loading}
              className="h-6 w-6 p-0"
            >
              <ChevronLeft className="h-3 w-3" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages || loading}
              className="h-6 w-6 p-0"
            >
              <ChevronRight className="h-3 w-3" />
            </Button>
          </div>
        </div>
      )}

      {/* 删除确认对话框 */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent className="sm:max-w-[360px]">
          <DialogHeader>
            <DialogTitle className="text-base">确认删除</DialogTitle>
            <DialogDescription className="text-sm">
              确定要删除这条历史记录吗？此操作不可撤销。
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2 mt-4">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setDeleteDialogOpen(false)}
              disabled={deleting}
            >
              取消
            </Button>
            <Button
              variant="destructive"
              size="sm"
              onClick={handleDelete}
              disabled={deleting}
            >
              {deleting && <Loader2 className="h-3 w-3 mr-1 animate-spin" />}
              删除
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* 批量删除确认对话框（Phase 25） */}
      <Dialog open={batchDeleteDialogOpen} onOpenChange={setBatchDeleteDialogOpen}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle className="text-base">确认批量删除</DialogTitle>
            <DialogDescription className="text-sm">
              确定要删除选中的 {selectedIds.size} 条历史记录吗？此操作不可恢复。
            </DialogDescription>
          </DialogHeader>
          <div className="mt-2">
            <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
              <Checkbox
                checked={cleanupFiles}
                onCheckedChange={(checked) => setCleanupFiles(!!checked)}
              />
              同时删除任务产生的阶段数据文件（推荐）
            </label>
          </div>
          <div className="flex justify-end gap-2 mt-4">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setBatchDeleteDialogOpen(false)}
              disabled={deleting}
            >
              取消
            </Button>
            <Button
              variant="destructive"
              size="sm"
              onClick={handleBatchDelete}
              disabled={deleting}
            >
              {deleting && <Loader2 className="h-3 w-3 mr-1 animate-spin" />}
              删除 {selectedIds.size} 条
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default TaskHistoryCompact;
