"use client";

import React from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { AlertTriangle, ShieldAlert, Info, FileX } from "lucide-react";
import { cn } from "@/lib/utils";

// =============================================================================
// 类型定义
// =============================================================================

export type SensitiveLevel = "high" | "medium" | "low";

export interface SensitiveFinding {
  column: string;
  level: SensitiveLevel;
  rule_name: string;
  detection_method: string;
  hit_rate?: number;
  sample_values?: string[];
}

export interface SensitiveCheckResult {
  has_sensitive: boolean;
  max_level: SensitiveLevel | null;
  findings: SensitiveFinding[];
  summary: {
    high_count: number;
    medium_count: number;
    low_count: number;
    scanned_columns: number;
    scanned_rows: number;
  };
}

interface SensitiveCheckDialogProps {
  open: boolean;
  result: SensitiveCheckResult | null;
  fileName: string;
  onConfirm: () => void;   // 中危：用户确认继续
  onReselect: () => void;  // 高危/用户重选文件
}

// =============================================================================
// 工具函数
// =============================================================================

const LEVEL_CONFIG = {
  high: {
    label: "高危",
    color: "bg-red-100 text-red-800 border-red-200",
    badgeVariant: "destructive" as const,
    icon: ShieldAlert,
    iconColor: "text-red-600",
  },
  medium: {
    label: "中危",
    color: "bg-orange-100 text-orange-800 border-orange-200",
    badgeVariant: "outline" as const,
    icon: AlertTriangle,
    iconColor: "text-orange-500",
  },
  low: {
    label: "低危",
    color: "bg-blue-100 text-blue-800 border-blue-200",
    badgeVariant: "outline" as const,
    icon: Info,
    iconColor: "text-blue-500",
  },
};

// =============================================================================
// 组件
// =============================================================================

export function SensitiveCheckDialog({
  open,
  result,
  fileName,
  onConfirm,
  onReselect,
}: SensitiveCheckDialogProps) {
  if (!result || !result.has_sensitive) return null;

  const isHighDanger = result.max_level === "high";
  const isMediumDanger = result.max_level === "medium";

  return (
    <Dialog open={open} onOpenChange={() => {}}>
      <DialogContent
        className="max-w-lg"
        onPointerDownOutside={(e) => e.preventDefault()}
        onEscapeKeyDown={(e) => e.preventDefault()}
      >
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {isHighDanger ? (
              <ShieldAlert className="h-5 w-5 text-red-600" />
            ) : (
              <AlertTriangle className="h-5 w-5 text-orange-500" />
            )}
            {isHighDanger
              ? "检测到敏感个人信息，无法使用此数据集"
              : "检测到可能的个人信息字段"}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* 文件名 */}
          <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
            <FileX className="h-4 w-4" />
            <span className="font-mono">{fileName}</span>
          </div>

          {/* 主提示 */}
          {isHighDanger ? (
            <div className="rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 p-3 text-sm text-red-800 dark:text-red-300">
              以下字段包含敏感个人信息（个人信息保护法 §28），系统已阻止上传。请对数据集脱敏后重新上传。
            </div>
          ) : (
            <div className="rounded-lg bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 p-3 text-sm text-orange-800 dark:text-orange-300">
              以下字段可能包含个人信息。建议脱敏后使用，或确认该字段已脱敏/不含真实个人信息后继续。
            </div>
          )}

          {/* 检测结果列表 */}
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {result.findings.map((finding, idx) => {
              const cfg = LEVEL_CONFIG[finding.level];
              const Icon = cfg.icon;
              return (
                <div
                  key={idx}
                  className={cn(
                    "flex items-start gap-3 rounded-lg border p-3 text-sm",
                    cfg.color
                  )}
                >
                  <Icon className={cn("h-4 w-4 mt-0.5 shrink-0", cfg.iconColor)} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-mono font-medium truncate max-w-[180px]">
                        {finding.column}
                      </span>
                      <Badge variant={cfg.badgeVariant} className="text-xs shrink-0">
                        {finding.rule_name}
                      </Badge>
                      <span className="text-xs opacity-70 shrink-0">
                        {finding.detection_method === "column_name" ? "列名匹配" : `值扫描 ${((finding.hit_rate ?? 0) * 100).toFixed(0)}%`}
                      </span>
                    </div>
                    {finding.sample_values && finding.sample_values.length > 0 && (
                      <div className="mt-1 text-xs opacity-70 font-mono">
                        示例: {finding.sample_values.join(", ")}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* 脱敏建议（高危） */}
          {isHighDanger && (
            <div className="text-xs text-gray-500 dark:text-gray-400 space-y-1">
              <p className="font-medium">脱敏建议：</p>
              <ul className="list-disc list-inside space-y-0.5">
                {result.findings.some(f => f.rule_name === "身份证号") && (
                  <li>身份证号：替换为哈希值或内部 ID</li>
                )}
                {result.findings.some(f => f.rule_name === "手机号") && (
                  <li>手机号：保留前3位+后4位，中间替换为 ****</li>
                )}
                {result.findings.some(f => f.rule_name === "银行卡号") && (
                  <li>银行卡号：仅保留后4位</li>
                )}
                {result.findings.some(f => f.rule_name === "姓名") && (
                  <li>姓名：替换为匿名 ID 或随机代号</li>
                )}
              </ul>
            </div>
          )}

          {/* 扫描统计 */}
          <p className="text-xs text-gray-400">
            已扫描 {result.summary.scanned_columns} 列 × {result.summary.scanned_rows} 行样本
          </p>
        </div>

        <DialogFooter>
          {isHighDanger ? (
            // 高危：只有重新选择
            <Button variant="default" onClick={onReselect}>
              重新选择文件
            </Button>
          ) : (
            // 中危：可以确认继续或重新选择
            <>
              <Button variant="outline" onClick={onReselect}>
                重新选择文件
              </Button>
              <Button variant="default" onClick={onConfirm}>
                已脱敏，继续使用
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
