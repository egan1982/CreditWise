"use client";

import React from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { DollarSign, TrendingUp, PieChart, Info, BarChart3, Percent } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

// TypeScript interfaces
interface RuleAmountMetrics {
  rule: string;
  hit_amount: number;
  hit_amount_pct: number;
  bad_amount: number;
  bad_amount_pct: number;
  amount_bad_rate: number;
  amount_lift: number;
  avg_amount_per_hit?: number;
}

interface AmountAnalysis {
  total_amount: number;
  total_bad_amount: number;
  overall_amount_bad_rate?: number;
  rules_amount: RuleAmountMetrics[];
  cumulative: {
    cum_hit_amount: number;
    cum_bad_amount: number;
    amount_recall: number;
    cum_amount_bad_rate?: number;
    cum_amount_lift?: number;
  };
}

interface AmountAnalysisPanelProps {
  analysis: AmountAnalysis | null;
  className?: string;
}

// Format currency
function formatCurrency(value: number | null | undefined): string {
  if (value === null || value === undefined || isNaN(value)) return "N/A";
  return `¥${value.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

// Format percentage
function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined || isNaN(value)) return "N/A";
  return `${(value * 100).toFixed(2)}%`;
}

// Get lift color class
function getLiftColor(lift: number): string {
  if (lift >= 2) return "text-green-600 font-bold";
  if (lift >= 1.5) return "text-green-500";
  if (lift >= 1) return "text-yellow-600";
  return "text-red-500";
}

export function AmountAnalysisPanel({ analysis, className }: AmountAnalysisPanelProps) {
  if (!analysis) {
    return (
      <Card className={cn("w-full", className)}>
        <CardContent className="pt-6">
          <p className="text-center text-muted-foreground">
            金额分析数据不可用
          </p>
          <p className="text-center text-xs text-muted-foreground mt-2">
            请在任务配置中指定金额列以启用金额维度分析
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className={cn("space-y-4", className)}>
      {/* Summary Cards - 3x2 layout */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {/* Row 1: Total metrics */}
        <Card>
          <CardContent className="pt-3 pb-2">
            <div className="flex items-center gap-2 text-muted-foreground text-xs mb-1">
              <DollarSign className="h-3 w-3" />
              总金额
            </div>
            <div className="text-base font-bold">
              {formatCurrency(analysis.total_amount)}
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="pt-3 pb-2">
            <div className="flex items-center gap-2 text-muted-foreground text-xs mb-1">
              <DollarSign className="h-3 w-3 text-red-500" />
              总坏账金额
            </div>
            <div className="text-base font-bold text-red-600">
              {formatCurrency(analysis.total_bad_amount)}
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="pt-3 pb-2">
            <div className="flex items-center gap-2 text-muted-foreground text-xs mb-1">
              <PieChart className="h-3 w-3" />
              累计命中金额
            </div>
            <div className="text-base font-bold">
              {formatCurrency(analysis.cumulative?.cum_hit_amount)}
            </div>
          </CardContent>
        </Card>

        {/* Row 2: Rate metrics */}
        <Card>
          <CardContent className="pt-3 pb-2">
            <div className="flex items-center gap-2 text-muted-foreground text-xs mb-1">
              <Percent className="h-3 w-3 text-orange-500" />
              样本金额坏账率
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger>
                    <Info className="h-3 w-3" />
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>总坏账金额 / 总金额（基准线）</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
            <div className="text-base font-bold text-orange-600">
              {formatPercent(analysis.overall_amount_bad_rate)}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-3 pb-2">
            <div className="flex items-center gap-2 text-muted-foreground text-xs mb-1">
              <TrendingUp className="h-3 w-3" />
              金额累计召回率
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger>
                    <Info className="h-3 w-3" />
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>规则命中的坏账金额占总坏账金额的比例</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
            <div className="text-base font-bold text-green-600">
              {formatPercent(analysis.cumulative?.amount_recall)}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-3 pb-2">
            <div className="flex items-center gap-2 text-muted-foreground text-xs mb-1">
              <BarChart3 className="h-3 w-3 text-purple-500" />
              金额累计提升度
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger>
                    <Info className="h-3 w-3" />
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>累计金额坏账率 / 样本金额坏账率</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
            <div className="text-base font-bold text-purple-600">
              {analysis.cumulative?.cum_amount_lift != null
                ? `${analysis.cumulative.cum_amount_lift.toFixed(2)}x`
                : "N/A"}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Rules Amount Detail Table */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            规则金额明细
            <Badge variant="outline" className="text-xs font-normal">
              {analysis.rules_amount?.length || 0} 条规则
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="min-w-[200px]">规则</TableHead>
                  <TableHead className="text-right">命中金额</TableHead>
                  <TableHead className="text-right">金额占比</TableHead>
                  <TableHead className="text-right">坏账金额</TableHead>
                  <TableHead className="text-right">坏账占比</TableHead>
                  <TableHead className="text-right">金额坏账率</TableHead>
                  <TableHead className="text-right">
                    金额Lift
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger>
                          <Info className="h-3 w-3 ml-1 inline" />
                        </TooltipTrigger>
                        <TooltipContent>
                          <p>金额维度的提升度</p>
                          <p>= 规则金额坏账率 / 整体金额坏账率</p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {analysis.rules_amount?.map((row, index) => (
                  <TableRow key={index}>
                    <TableCell className="font-mono text-xs max-w-[300px] truncate" title={row.rule}>
                      {row.rule}
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {formatCurrency(row.hit_amount)}
                    </TableCell>
                    <TableCell className="text-right font-mono text-muted-foreground">
                      {formatPercent(row.hit_amount_pct)}
                    </TableCell>
                    <TableCell className="text-right font-mono text-red-600">
                      {formatCurrency(row.bad_amount)}
                    </TableCell>
                    <TableCell className="text-right font-mono text-muted-foreground">
                      {formatPercent(row.bad_amount_pct)}
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {formatPercent(row.amount_bad_rate)}
                    </TableCell>
                    <TableCell className={cn("text-right font-mono", getLiftColor(row.amount_lift))}>
                      {row.amount_lift?.toFixed(2) || "N/A"}
                    </TableCell>
                  </TableRow>
                ))}
                
                {/* Cumulative Row */}
                {analysis.cumulative && (
                  <TableRow className="bg-muted/50 font-medium">
                    <TableCell>累计</TableCell>
                    <TableCell className="text-right font-mono">
                      {formatCurrency(analysis.cumulative.cum_hit_amount)}
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {formatPercent(analysis.cumulative.cum_hit_amount / analysis.total_amount)}
                    </TableCell>
                    <TableCell className="text-right font-mono text-red-600">
                      {formatCurrency(analysis.cumulative.cum_bad_amount)}
                    </TableCell>
                    <TableCell className="text-right font-mono text-green-600">
                      {formatPercent(analysis.cumulative.amount_recall)}
                    </TableCell>
                    <TableCell className="text-right">-</TableCell>
                    <TableCell className="text-right">-</TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default AmountAnalysisPanel;
