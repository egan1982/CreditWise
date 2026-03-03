"use client";

import React, { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  Pause,
  Square,
  RefreshCw,
  Search,
  Eye,
  Trash2,
  Download,
  ChevronLeft,
  ChevronRight,
  AlertCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";

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

interface TaskHistoryListProps {
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

const STATUS_CONFIG: Record<string, {
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  label: string;
}> = {
  pending: {
    icon: Clock,
    color: "text-gray-500",
    label: "等待中",
  },
  running: {
    icon: Loader2,
    color: "text-blue-500",
    label: "执行中",
  },
  completed: {
    icon: CheckCircle2,
    color: "text-green-500",
    label: "已完成",
  },
  failed: {
    icon: XCircle,
    color: "text-red-500",
    label: "失败",
  },
  stopped: {
    icon: Square,
    color: "text-yellow-500",
    label: "已停止",
  },
  paused: {
    icon: Pause,
    color: "text-yellow-500",
    label: "已暂停",
  },
  cancelled: {
    icon: XCircle,
    color: "text-gray-500",
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
// 状态徽章组件
// =============================================================================

function StatusBadge({ status }: { status: string }) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.pending;
  const Icon = config.icon;
  const isRunning = status === "running";

  return (
    <Badge
      variant="outline"
      className={cn("flex items-center gap-1 text-xs", config.color)}
    >
      <Icon className={cn("h-3 w-3", isRunning && "animate-spin")} />
      {config.label}
    </Badge>
  );
}

// =============================================================================
// 主组件
// =============================================================================

export function TaskHistoryList({
  onViewDetail,
  onLoadResult,
  className,
}: TaskHistoryListProps) {
  const [records, setRecords] = useState<TaskHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);

  // 过滤条件
  const [taskTypeFilter, setTaskTypeFilter] = useState<string>("all");
  const [categoryFilter, setCategoryFilter] = useState<string>("all"); // 任务类别筛选
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");

  // 删除确认
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [recordToDelete, setRecordToDelete] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  // 加载数据
  const loadRecords = async () => {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      params.set("limit", String(pageSize));
      params.set("offset", String((page - 1) * pageSize));

      if (taskTypeFilter !== "all") {
        params.set("task_type", taskTypeFilter);
      }
      if (categoryFilter !== "all") {
        params.set("task_category", categoryFilter);
      }
      if (statusFilter !== "all") {
        params.set("status", statusFilter);
      }

      const response = await fetch(`/api/sop/history?${params.toString()}`);
      if (!response.ok) {
        throw new Error("Failed to load history");
      }

      const data = await response.json();
      setRecords(data.records || []);
      setTotal(data.total || 0);
    } catch (err) {
      console.error("Failed to load history:", err);
      setError("加载历史记录失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRecords();
  }, [page, taskTypeFilter, categoryFilter, statusFilter]);

  // 删除记录
  const handleDelete = async () => {
    if (!recordToDelete) return;

    setDeleting(true);
    try {
      const response = await fetch(`/api/sop/history/${recordToDelete}`, {
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

  // 过滤后的记录（本地搜索）
  const filteredRecords = searchQuery
    ? records.filter(
        (r) =>
          r.record_id.includes(searchQuery) ||
          r.execution_id?.includes(searchQuery) ||
          r.message?.includes(searchQuery)
      )
    : records;

  return (
    <div className={cn("space-y-4", className)}>
      {/* 工具栏 */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          {/* 任务类型筛选 */}
          <Select value={taskTypeFilter} onValueChange={(value) => {
            setTaskTypeFilter(value);
            setCategoryFilter("all"); // 清空类别筛选
            setPage(1); // 重置到第一页
          }}>
            <SelectTrigger className="w-32 h-8 text-xs">
              <SelectValue placeholder="任务类型" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部类型</SelectItem>
              <SelectItem value="scorecard_dev">评分卡开发</SelectItem>
              <SelectItem value="rule_mining">规则挖掘</SelectItem>
              <SelectItem value="inference">AI对话</SelectItem>
            </SelectContent>
          </Select>

          {/* 任务类别筛选 */}
          <Select value={categoryFilter} onValueChange={(value) => {
            setCategoryFilter(value);
            setTaskTypeFilter("all"); // 清空类型筛选
            setPage(1); // 重置到第一页
          }}>
            <SelectTrigger className="w-24 h-8 text-xs">
              <SelectValue placeholder="类别" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部类别</SelectItem>
              <SelectItem value="sop">SOP任务</SelectItem>
              <SelectItem value="inference">AI对话</SelectItem>
            </SelectContent>
          </Select>

          {/* 状态筛选 */}
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-28 h-8 text-xs">
              <SelectValue placeholder="状态" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部状态</SelectItem>
              <SelectItem value="completed">已完成</SelectItem>
              <SelectItem value="failed">失败</SelectItem>
              <SelectItem value="running">执行中</SelectItem>
              <SelectItem value="stopped">已停止</SelectItem>
            </SelectContent>
          </Select>

          {/* 搜索框 */}
          <div className="relative">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-400" />
            <Input
              placeholder="搜索..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-7 h-8 w-40 text-xs"
            />
          </div>
        </div>

        {/* 刷新按钮 */}
        <Button
          variant="outline"
          size="sm"
          onClick={loadRecords}
          disabled={loading}
          className="h-8"
        >
          <RefreshCw className={cn("h-3.5 w-3.5 mr-1", loading && "animate-spin")} />
          刷新
        </Button>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400 text-sm">
          <AlertCircle className="h-4 w-4" />
          {error}
        </div>
      )}

      {/* 表格 */}
      <div className="border rounded-lg overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-gray-50 dark:bg-gray-900/50">
              <TableHead className="text-xs">任务类型</TableHead>
              <TableHead className="text-xs">状态</TableHead>
              <TableHead className="text-xs">进度</TableHead>
              <TableHead className="text-xs">开始时间</TableHead>
              <TableHead className="text-xs">耗时</TableHead>
              <TableHead className="text-xs text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-8">
                  <Loader2 className="h-5 w-5 animate-spin mx-auto text-gray-400" />
                  <span className="text-sm text-gray-500 mt-2 block">加载中...</span>
                </TableCell>
              </TableRow>
            ) : filteredRecords.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-8 text-gray-500">
                  暂无历史记录
                </TableCell>
              </TableRow>
            ) : (
              filteredRecords.map((record) => (
                <TableRow key={record.record_id} className="hover:bg-gray-50 dark:hover:bg-gray-900/30">
                  <TableCell className="text-xs font-medium">
                    {TASK_TYPE_LABELS[record.task_type] || record.task_type}
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={record.status} />
                  </TableCell>
                  <TableCell className="text-xs">
                    {Math.round(record.progress)}%
                  </TableCell>
                  <TableCell className="text-xs text-gray-500">
                    {formatDateTime(record.started_at || record.created_at)}
                  </TableCell>
                  <TableCell className="text-xs text-gray-500">
                    {formatDuration(record.duration_seconds)}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-1">
                      {/* 查看详情 */}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onViewDetail?.(record.record_id)}
                        className="h-7 w-7 p-0"
                        title="查看详情"
                      >
                        <Eye className="h-3.5 w-3.5" />
                      </Button>

                      {/* 删除 */}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setRecordToDelete(record.record_id);
                          setDeleteDialogOpen(true);
                        }}
                        className="h-7 w-7 p-0 text-red-500 hover:text-red-600"
                        title="删除"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* 分页 */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <span className="text-xs text-gray-500">
            共 {total} 条记录，第 {page}/{totalPages} 页
          </span>
          <div className="flex items-center gap-1">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1 || loading}
              className="h-7 w-7 p-0"
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages || loading}
              className="h-7 w-7 p-0"
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      {/* 删除确认对话框 */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>确认删除</DialogTitle>
            <DialogDescription>
              确定要删除这条历史记录吗？此操作不可撤销，相关的结果文件也将被删除。
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2 mt-4">
            <Button
              variant="outline"
              onClick={() => setDeleteDialogOpen(false)}
              disabled={deleting}
            >
              取消
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleting}
            >
              {deleting && <Loader2 className="h-4 w-4 mr-1 animate-spin" />}
              删除
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default TaskHistoryList;
