"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { SuggestedParamsCard } from "./SuggestedParamsCard";
import { StageVersionSelector } from "./StageVersionSelector";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  ChevronLeft,
  ChevronRight,
  Database,
  BarChart3,
  Filter,
  Brain,
  Target,
  FileText,
  CheckCircle2,
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  Settings,
  Code2,
  RotateCcw,
  Sparkles,
  Loader2,
  ChevronDown,
  ChevronUp,
  Download,
} from "lucide-react";
import { cn, unwrapData } from "@/lib/utils";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Cell, Tooltip as RechartsTooltip } from "recharts";
import { StageCodeEditor } from "./StageCodeEditor";
import { StageParameterEditor } from "./StageParameterEditor";
import { StageParamsForm } from "./StageParamsForm";
import { ParamMeta, DataColumn } from "@/lib/sopService";
import { getApiUrl } from "@/lib/config";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// =============================================================================
// 类型定义
// =============================================================================

// AI 分析结果缓存工具
// Phase 7: 优先使用后端 API 持久化，sessionStorage 作为降级方案
// Phase 9: 使用 recordId（任务记录ID）而不是 sessionId 来区分不同任务的缓存
//          这样每个任务的AI分析缓存是独立的，不会在不同任务之间共享
const AI_ANALYSIS_CACHE_PREFIX = "ai_analysis_cache:";

// 生成缓存键（用于 sessionStorage 降级）
// 使用 recordId 作为任务标识，确保不同任务的缓存独立
function getAnalysisCacheKey(recordId: string, stageId: string): string {
  return `${AI_ANALYSIS_CACHE_PREFIX}${recordId}:${stageId}`;
}

// 从缓存获取分析结果
function getCachedAnalysis(recordId: string, stageId: string): string | null {
  if (typeof window === "undefined" || !recordId) return null;
  try {
    const key = getAnalysisCacheKey(recordId, stageId);
    return sessionStorage.getItem(key);
  } catch {
    return null;
  }
}

// 保存分析结果到缓存
function setCachedAnalysis(recordId: string, stageId: string, analysis: string): void {
  if (typeof window === "undefined" || !recordId) return;
  try {
    const key = getAnalysisCacheKey(recordId, stageId);
    sessionStorage.setItem(key, analysis);
  } catch {
    // sessionStorage 可能已满或不可用，忽略错误
  }
}

// 删除缓存的分析结果
function deleteCachedAnalysis(recordId: string, stageId: string): void {
  if (typeof window === "undefined" || !recordId) return;
  try {
    const key = getAnalysisCacheKey(recordId, stageId);
    sessionStorage.removeItem(key);
  } catch {
    // 忽略错误
  }
}

// =============================================================================
// Phase 7: 后端 API 持久化函数
// =============================================================================

// 从后端 API 获取分析结果
async function fetchAnalysisFromAPI(
  recordId: string,
  stageId: string
): Promise<{ analysis_text: string; model_used: string | null } | null> {
  try {
    const response = await fetch(
      getApiUrl(`/sop/history/${recordId}/stages/${stageId}/analysis`)
    );
    if (!response.ok) return null;
    const data = await response.json();
    return data.analysis || null;
  } catch {
    return null;
  }
}

// 保存分析结果到后端 API，返回解析到的 suggested_params（如有）
async function saveAnalysisToAPI(
  recordId: string,
  stageId: string,
  analysisText: string,
  modelUsed?: string
): Promise<{ success: boolean; suggested_params?: Record<string, unknown> | null }> {
  try {
    const response = await fetch(
      getApiUrl(`/sop/history/${recordId}/stages/${stageId}/analysis`),
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          analysis_text: analysisText,
          model_used: modelUsed || null,
        }),
      }
    );
    if (!response.ok) return { success: false };
    const data = await response.json();
    return { success: true, suggested_params: data.suggested_params ?? null };
  } catch {
    return { success: false };
  }
}

// 删除后端 API 的分析结果
async function deleteAnalysisFromAPI(
  recordId: string,
  stageId: string
): Promise<boolean> {
  try {
    const response = await fetch(
      getApiUrl(`/sop/history/${recordId}/stages/${stageId}/analysis`),
      { method: "DELETE" }
    );
    return response.ok;
  } catch {
    return false;
  }
}

// =============================================================================
// 构建任务整体分析的提示词（已迁移至后端 AI_analysis_prompts.py）
// Phase 22: 前端仅通过 /v1/chat/analysis/prompt API 获取，此处保留类型导出
// =============================================================================

// 阶段数据接口（用于编辑功能）
export interface StageEditableData {
  params?: Record<string, any>;
  params_meta?: ParamMeta[];  // 参数元数据（用于渲染可视化表单）
  code?: string;
}

interface StageOutputPreviewProps {
  stageId: string;
  stageName: string;
  outputPreview: Record<string, any> | null;
  status?: string;
  onBack?: () => void;
  className?: string;
  // 专家模式相关属性
  /** 是否为专家模式 */
  isExpertMode?: boolean;
  /** 阶段可编辑数据 */
  stageData?: StageEditableData;
  /** 编辑参数回调 - 传递阶段ID和修改后的参数 */
  onEditParams?: (stageId: string, params: Record<string, any>) => void;
  /** 编辑代码回调 */
  onEditCode?: (stageId: string) => void;
  /** 重试阶段回调 - params 是要重试时使用的新参数，retry_reason 是重试原因 */
  onRetryStage?: (stageId: string, params?: Record<string, any>, retry_reason?: string) => void;
  /** 会话ID（用于代码执行和 sessionStorage 降级缓存） */
  sessionId?: string;
  /** 任务记录ID（用于后端 API 持久化 AI 分析，Phase 7） */
  recordId?: string;
  /** 深色模式 */
  isDarkMode?: boolean;
  /** 阶段执行时间（毫秒） */
  executionTimeMs?: number | null;
  /** 当前选择的模型（用于AI分析） */
  selectedModel?: string;
  /** 模型配置参数（用于AI分析，从用户选择的配置中读取） */
  modelConfig?: {
    temperature?: number;
    frequency_penalty?: number;
    presence_penalty?: number;
  };
  // 自动模式 AI 分析（外部传入，用于任务级别的整体分析）
  /** 外部传入的 AI 分析结果（自动模式使用） */
  externalAiAnalysis?: string | null;
  /** 外部 AI 分析是否正在进行中 */
  isExternalAnalyzing?: boolean;
  /** 外部 AI 分析重新分析回调 */
  onExternalReanalyze?: () => void;
  /** 任务使用的数据文件路径（用于加载正确的数据列） */
  dataFilePath?: string;
  /** 数据列列表（用于参数表单中的列选择控件） */
  columns?: DataColumn[];
  /** 列加载中 */
  columnsLoading?: boolean;
  // 专家模式最后阶段整体分析所需（Phase 20）
  /** 是否为最后一个阶段（用于专家模式下生成整体任务分析） */
  isLastStage?: boolean;
  /** 任务类型（scorecard_dev 或 rule_mining） */
  taskType?: string;
  /** 任务最终结果数据（用于专家模式最后阶段整体分析） */
  taskResult?: Record<string, any> | null;
  /** 阶段历史快照列表（来自 stages[stageId].snapshots） */
  snapshots?: import("./StageVersionSelector").StageSnapshotMeta[];
}

// =============================================================================
// 数据加载阶段预览
// =============================================================================

function DataLoadingPreview({ data, taskType }: { data: Record<string, any>; taskType?: string }) {
  // 解析排除变量报告
  const autoExcludeReport = data.auto_exclude_report || {};
  const userSpecified = autoExcludeReport.user_specified || [];
  const autoDetected = autoExcludeReport.auto_detected || {};
  const totalExcluded = autoExcludeReport.total_excluded || [];
  
  // 合并自动检测的各类列
  const idCols = autoDetected.id_cols || [];
  const timeCols = autoDetected.time_cols || [];
  const sampleTypeCols = autoDetected.sample_type_cols || [];
  const highCardinalityCols = autoDetected.high_cardinality_cols || [];
  
  // 解析特殊值替换信息
  const specialValueInfo = data.special_value_info || {};
  const specialValues = specialValueInfo.special_values || [];
  const affectedFeatures = specialValueInfo.affected_features || 0;
  const totalReplaced = specialValueInfo.total_replaced || 0;
  
  // 解析缺失率摘要
  const missingSummary = data.missing_summary || {};
  const missingDistribution = missingSummary.distribution || {};
  const highMissingFeatures = missingSummary.high_missing_features || [];
  
  // 解析衍生特征信息
  const derivedFeatures = data.derived_features || {};
  const onehotCount = derivedFeatures.onehot_count || 0;
  const datetimeCount = derivedFeatures.datetime_count || 0;
  const textCount = derivedFeatures.text_count || 0;
  const totalDerived = derivedFeatures.total_derived || 0;
  
  return (
    <div className="space-y-4">
      {/* 数据概览 */}
      <div className="grid grid-cols-2 gap-3">
        <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
          <div className="text-2xl font-bold text-blue-600">{data.rows?.toLocaleString() || "-"}</div>
          <div className="text-xs text-gray-500">总行数</div>
        </div>
        <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
          <div className="text-2xl font-bold text-green-600">
            {data.feature_count || data.columns || "-"}
            {/* 显示var_filter计算过程：49 = 81 - 32，每个数字带含义说明 */}
            {data.var_filter_result && data.var_filter_result.removed_features?.length > 0 && (
              <span className="text-sm font-normal text-gray-400 ml-1">
                = <span className="text-gray-600">{data.var_filter_result.input_features}</span>
                <span className="text-[10px] text-gray-400 mx-0.5">原始</span>
                - <span className="text-gray-600">{data.var_filter_result.removed_features.length}</span>
                <span className="text-[10px] text-gray-400 ml-0.5">移除</span>
              </span>
            )}
            {totalDerived > 0 && (
              <span className="text-base font-normal text-cyan-600 ml-1">
                (+{totalDerived})
              </span>
            )}
          </div>
          <div className="text-xs text-gray-500">
            {data.var_filter_result && data.var_filter_result.removed_features?.length > 0 
              ? "特征数 (var_filter后)" 
              : totalDerived > 0 ? "原始特征（+衍生）" : "特征数"}
          </div>
        </div>
        <div className="p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
          <div className="text-2xl font-bold text-yellow-600">{data.missing_rate !== undefined && data.missing_rate !== null ? `${(data.missing_rate * 100).toFixed(1)}%` : "-"}</div>
          <div className="text-xs text-gray-500">平均缺失率</div>
        </div>
        <div className="p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
          <div className="text-2xl font-bold text-purple-600">{data.target_rate ? `${(data.target_rate * 100).toFixed(2)}%` : "-"}</div>
          <div className="text-xs text-gray-500">坏账率</div>
        </div>
      </div>

      {/* P2-6: 类别不平衡分析卡片 */}
      {data.imbalance_analysis && data.imbalance_analysis.severity !== "无" && (
        <div className={cn(
          "p-3 rounded-lg border",
          data.imbalance_analysis.applied_strategy === 'none' && data.imbalance_analysis.severity !== "无"
            ? "bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800"
            : "bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800"
        )}>
          <div className="flex items-center justify-between mb-1.5">
            <div className="text-sm font-medium flex items-center gap-1.5">
              <span>⚖️ 类别不平衡分析</span>
              <Badge variant="outline" className={cn("text-[10px]", {
                "border-yellow-400 text-yellow-700": data.imbalance_analysis.severity === "轻度",
                "border-orange-400 text-orange-700": data.imbalance_analysis.severity === "中度",
                "border-red-400 text-red-700": data.imbalance_analysis.severity === "重度" || data.imbalance_analysis.severity === "极端",
              })}>
                {data.imbalance_analysis.severity}
              </Badge>
            </div>
          </div>
          <div className="grid grid-cols-3 gap-2 text-xs">
            <div className="text-center p-1.5 bg-white/60 dark:bg-gray-800/40 rounded">
              <div className="font-bold">{data.imbalance_analysis.imbalance_ratio}</div>
              <div className="text-gray-500">好:坏比例</div>
            </div>
            <div className="text-center p-1.5 bg-white/60 dark:bg-gray-800/40 rounded">
              <div className="font-bold">{data.imbalance_analysis.applied_strategy === 'class_weight' ? '类别加权' : '不处理'}</div>
              <div className="text-gray-500">应用策略</div>
            </div>
            <div className="text-center p-1.5 bg-white/60 dark:bg-gray-800/40 rounded">
              <div className="font-bold">{data.imbalance_analysis.user_strategy === 'auto' ? '自动' : data.imbalance_analysis.user_strategy}</div>
              <div className="text-gray-500">用户选择</div>
            </div>
          </div>
          {data.imbalance_analysis.applied_strategy === 'none' && (data.imbalance_analysis.severity === "中度" || data.imbalance_analysis.severity === "重度" || data.imbalance_analysis.severity === "极端") && (
            <div className="mt-2 text-xs text-amber-600 dark:text-amber-400 flex items-center gap-1">
              <AlertTriangle className="h-3 w-3" />
              建议启用类别不平衡处理（调整参数为"自动选择"或"类别加权"）
            </div>
          )}
        </div>
      )}

      {/* 数据划分配置 - 评分卡任务特有，展示影响后续阶段的关键参数 */}
      {/* 只有存在 var_filter_result（数据质量筛选结果）时才显示，这是评分卡任务的特征 */}
      {data.var_filter_result?.missing_limit !== undefined && (
        <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
          <div className="text-sm font-medium mb-2">数据划分配置</div>
          <div className="grid grid-cols-3 gap-2 text-xs">
            <div className="text-center p-2 bg-white dark:bg-gray-800 rounded">
              <div className="font-medium text-blue-600">缺失率阈值</div>
              <div className="text-gray-600">
                {`${(data.var_filter_result.missing_limit * 100).toFixed(0)}%`}
              </div>
            </div>
            <div className="text-center p-2 bg-white dark:bg-gray-800 rounded">
              <div className="font-medium text-blue-600">测试集</div>
              <div className="text-gray-600">
                {data.split_info?.test_ratio !== undefined
                  ? `${(data.split_info.test_ratio * 100).toFixed(0)}%`
                  : data.split_info?.test && data.rows
                    ? `${((data.split_info.test / data.rows) * 100).toFixed(0)}%`
                    : "-"}
              </div>
            </div>
            <div className="text-center p-2 bg-white dark:bg-gray-800 rounded">
              <div className="font-medium text-blue-600">OOT验证集</div>
              <div className="text-gray-600">
                {typeof data.split_info?.oot === 'number' && data.rows
                  ? data.split_info.oot > 0
                    ? `${((data.split_info.oot / data.rows) * 100).toFixed(0)}%`
                    : "0%"
                  : "-"}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 特殊值替换信息 */}
      {totalReplaced > 0 && (
        <div className="p-3 bg-indigo-50 dark:bg-indigo-900/20 rounded-lg border border-indigo-200 dark:border-indigo-800">
          <div className="text-sm font-medium mb-2 text-indigo-700 dark:text-indigo-300">
            特殊缺失值处理
          </div>
          <div className="text-xs space-y-1">
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">识别值:</span>
              <span className="font-mono text-indigo-600 dark:text-indigo-400">
                {specialValues.slice(0, 5).join(", ")}{specialValues.length > 5 ? "..." : ""}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">受影响特征:</span>
              <span className="font-medium">{affectedFeatures}个</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">替换记录数:</span>
              <span className="font-medium">{totalReplaced.toLocaleString()}条</span>
            </div>
          </div>
        </div>
      )}

      {/* 缺失率详情 */}
      {missingSummary.total_features > 0 && (
        <div className="p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg border border-yellow-200 dark:border-yellow-800">
          <div className="text-sm font-medium mb-2 text-yellow-700 dark:text-yellow-300">
            缺失率分布
          </div>
          <div className="grid grid-cols-5 gap-2 text-xs mb-2">
            <div className="text-center">
              <div className="font-bold text-green-600">{missingDistribution.no_missing || 0}</div>
              <div className="text-gray-500">无缺失</div>
            </div>
            <div className="text-center">
              <div className="font-bold text-blue-600">{missingDistribution.low || 0}</div>
              <div className="text-gray-500">0-10%</div>
            </div>
            <div className="text-center">
              <div className="font-bold text-yellow-600">{missingDistribution.medium || 0}</div>
              <div className="text-gray-500">10-30%</div>
            </div>
            <div className="text-center">
              <div className="font-bold text-orange-600">{missingDistribution.high || 0}</div>
              <div className="text-gray-500">30-50%</div>
            </div>
            <div className="text-center">
              <div className="font-bold text-red-600">{missingDistribution.very_high || 0}</div>
              <div className="text-gray-500">&gt;50%</div>
            </div>
          </div>
          {highMissingFeatures.length > 0 && (
            <div className="mt-2 pt-2 border-t border-yellow-200 dark:border-yellow-700">
              <div className="text-xs text-gray-500 mb-1">高缺失率特征 (&gt;30%):</div>
              <div className="flex flex-wrap gap-1">
                {highMissingFeatures.slice(0, 5).map((f: any, i: number) => (
                  <span key={i} className="px-1.5 py-0.5 bg-yellow-100 dark:bg-yellow-800/50 rounded text-xs">
                    {f.variable}: {(f.missing_rate * 100).toFixed(1)}%
                  </span>
                ))}
                {highMissingFeatures.length > 5 && (
                  <span className="text-xs text-gray-500">+{highMissingFeatures.length - 5}个</span>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* 数据集划分 - 优化展示 */}
      {data.split_info && (
        <div className="p-3 bg-indigo-50 dark:bg-indigo-900/20 rounded-lg border border-indigo-200 dark:border-indigo-800">
          <div className="text-sm font-medium mb-2 text-indigo-700 dark:text-indigo-300">数据集划分</div>
          <div className="grid grid-cols-3 gap-2 text-xs">
            <div className="text-center p-2 bg-indigo-100 dark:bg-indigo-800/30 rounded">
              <div className="font-bold text-indigo-600">{data.split_info.train?.toLocaleString() || "-"}</div>
              <div className="text-gray-500">训练集</div>
              {/* 评分卡任务特有：展示训练集坏账率 */}
              {typeof data.split_info.train_target_rate === 'number' && (
                <div className="text-orange-500 text-[10px] mt-0.5">坏账率 {(data.split_info.train_target_rate * 100).toFixed(2)}%</div>
              )}
            </div>
            <div className="text-center p-2 bg-indigo-100 dark:bg-indigo-800/30 rounded">
              <div className="font-bold text-indigo-600">{data.split_info.test?.toLocaleString() || "-"}</div>
              <div className="text-gray-500">测试集</div>
              {/* 评分卡任务特有：展示测试集坏账率 */}
              {typeof data.split_info.test_target_rate === 'number' && (
                <div className="text-orange-500 text-[10px] mt-0.5">坏账率 {(data.split_info.test_target_rate * 100).toFixed(2)}%</div>
              )}
            </div>
            {/* 评分卡任务特有：OOT验证集始终展示（包括0，表示未指定划分OOT的可选列） */}
            {typeof data.split_info.oot === 'number' && (
              <div className="text-center p-2 bg-indigo-100 dark:bg-indigo-800/30 rounded">
                <div className="font-bold text-indigo-600">{data.split_info.oot.toLocaleString()}</div>
                <div className="text-gray-500">OOT验证集</div>
                {/* 评分卡任务特有：展示OOT集坏账率（如果有OOT样本） */}
                {typeof data.split_info.oot_target_rate === 'number' && (
                  <div className="text-orange-500 text-[10px] mt-0.5">坏账率 {(data.split_info.oot_target_rate * 100).toFixed(2)}%</div>
                )}
                {data.split_info.oot === 0 && (
                  <div className="text-gray-400 text-[10px] mt-0.5">未划分</div>
                )}
              </div>
            )}
          </div>
          {data.split_info.split_method && (
            <div className="mt-2 text-xs text-gray-500">
              {/* 如果有详细划分信息，分别展示；否则使用简要描述 */}
              {data.split_info.split_details ? (
                <div className="space-y-0.5">
                  <div>划分方式:</div>
                  <div className="ml-2 text-gray-400">
                    • 训练集/测试集: {data.split_info.split_details.train_test}
                  </div>
                  <div className="ml-2 text-gray-400">
                    • OOT验证集: {data.split_info.split_details.oot}
                  </div>
                </div>
              ) : (
                <>
                  划分方式: {data.split_info.split_method === 'sample_type_col' ? '样本类型列' : 
                            data.split_info.split_method === 'time' ? '时间划分' : 
                            data.split_info.split_method === 'random' ? `随机划分 (${(data.split_info.test_ratio * 100).toFixed(0)}%)` : 
                            data.split_info.split_method_desc || data.split_info.split_method}
                </>
              )}
            </div>
          )}
        </div>
      )}

      {/* 时间范围信息（始终显示，评分卡和规则挖掘任务通用） */}
      <div className="p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg border border-purple-200 dark:border-purple-800">
        <div className="text-sm font-medium mb-2 text-purple-700 dark:text-purple-300">
          时间范围
          {data.time_range_info?.column && (
            <span className="text-xs font-normal text-gray-500 ml-1">({data.time_range_info.column})</span>
          )}
        </div>
        {/* 根据是否有 OOT 字段决定显示2列还是3列（评分卡3列，规则挖掘2列） */}
        <div className={`grid ${data.time_range_info?.oot !== undefined ? 'grid-cols-3' : 'grid-cols-2'} gap-2 text-xs`}>
          {/* 训练集时间范围 */}
          <div className="text-center p-2 bg-purple-100 dark:bg-purple-800/30 rounded">
            <div className="text-gray-500 mb-1">训练集</div>
            {data.time_range_info?.train ? (
              <>
                <div className="font-medium text-purple-600">{data.time_range_info.train.min}</div>
                <div className="text-gray-400 text-[10px]">至</div>
                <div className="font-medium text-purple-600">{data.time_range_info.train.max}</div>
              </>
            ) : (
              <div className="text-gray-400">-</div>
            )}
          </div>
          {/* 测试集时间范围 */}
          <div className="text-center p-2 bg-purple-100 dark:bg-purple-800/30 rounded">
            <div className="text-gray-500 mb-1">测试集</div>
            {data.time_range_info?.test ? (
              <>
                <div className="font-medium text-purple-600">{data.time_range_info.test.min}</div>
                <div className="text-gray-400 text-[10px]">至</div>
                <div className="font-medium text-purple-600">{data.time_range_info.test.max}</div>
              </>
            ) : (
              <div className="text-gray-400">-</div>
            )}
          </div>
          {/* OOT集时间范围（仅评分卡任务显示） */}
          {data.time_range_info?.oot !== undefined && (
            <div className="text-center p-2 bg-purple-100 dark:bg-purple-800/30 rounded">
              <div className="text-gray-500 mb-1">OOT验证集</div>
              {data.time_range_info.oot ? (
                <>
                  <div className="font-medium text-purple-600">{data.time_range_info.oot.min}</div>
                  <div className="text-gray-400 text-[10px]">至</div>
                  <div className="font-medium text-purple-600">{data.time_range_info.oot.max}</div>
                </>
              ) : (
                <div className="text-gray-400">未划分</div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* var_filter数据质量筛选结果（参考scorecardpy库设计） */}
      {data.var_filter_result && data.var_filter_result.removed_features?.length > 0 && (
        <div className="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
          <div className="text-sm font-medium mb-2 text-red-700 dark:text-red-300">
            数据质量筛选 (var_filter)
          </div>
          <div className="text-xs space-y-2">
            {/* 筛选摘要 */}
            <div className="flex justify-between items-center pb-2 border-b border-red-200 dark:border-red-700">
              <span className="text-gray-600 dark:text-gray-400">
                特征数: {data.var_filter_result.input_features} → {data.var_filter_result.output_features}
              </span>
              <span className="font-medium text-red-600">
                移除 {data.var_filter_result.removed_features.length} 个
              </span>
            </div>
            
            {/* 高缺失率移除 */}
            {data.var_filter_result.removed_by_missing?.length > 0 && (
              <div>
                <div className="text-gray-500 mb-1">
                  高缺失率 (≥{(data.var_filter_result.missing_limit * 100).toFixed(0)}%): {data.var_filter_result.removed_by_missing.length}个
                </div>
                <div className="flex flex-wrap gap-1">
                  {data.var_filter_result.removed_by_missing.slice(0, 5).map((f: any, i: number) => (
                    <span key={i} className="px-1.5 py-0.5 bg-red-100 dark:bg-red-800/50 rounded text-[10px]">
                      {f.feature}: {(f.missing_rate * 100).toFixed(1)}%
                    </span>
                  ))}
                  {data.var_filter_result.removed_by_missing.length > 5 && (
                    <span className="text-[10px] text-gray-500">
                      +{data.var_filter_result.removed_by_missing.length - 5}个
                    </span>
                  )}
                </div>
              </div>
            )}
            
            {/* 高同值率移除 */}
            {data.var_filter_result.removed_by_identical?.length > 0 && (
              <div>
                <div className="text-gray-500 mb-1">
                  高同值率 (≥{(data.var_filter_result.identical_limit * 100).toFixed(0)}%): {data.var_filter_result.removed_by_identical.length}个
                </div>
                <div className="flex flex-wrap gap-1">
                  {data.var_filter_result.removed_by_identical.slice(0, 5).map((f: any, i: number) => (
                    <span key={i} className="px-1.5 py-0.5 bg-red-100 dark:bg-red-800/50 rounded text-[10px]">
                      {f.feature}: {(f.identical_rate * 100).toFixed(1)}%
                    </span>
                  ))}
                  {data.var_filter_result.removed_by_identical.length > 5 && (
                    <span className="text-[10px] text-gray-500">
                      +{data.var_filter_result.removed_by_identical.length - 5}个
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 异常值检测（在var_filter筛选后的特征上执行，仅检测不移除） */}
      {data.outlier_count !== undefined && (
        <div className="flex items-center gap-2 text-sm p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg border border-yellow-200 dark:border-yellow-800">
          {data.outlier_count > 0 ? (
            <>
              <AlertTriangle className="h-4 w-4 text-yellow-500 flex-shrink-0" />
              <span>
                检测到 <span className="font-medium text-yellow-700">{data.outlier_count}</span> 个特征存在异常值 
                <span className="text-gray-400 text-xs ml-1">
                  (基于1.5倍IQR标准，仅检测不移除{taskType === "scorecard_dev" ? "，WOE分箱会自动处理" : ""})
                </span>
              </span>
            </>
          ) : (
            <>
              <CheckCircle2 className="h-4 w-4 text-green-500 flex-shrink-0" />
              <span>未检测到明显异常值 <span className="text-gray-400 text-xs">(基于1.5倍IQR标准)</span></span>
            </>
          )}
        </div>
      )}

      {/* 衍生特征信息 */}
      {totalDerived > 0 && (
        <div className="p-3 bg-cyan-50 dark:bg-cyan-900/20 rounded-lg border border-cyan-200 dark:border-cyan-800">
          <div className="text-sm font-medium mb-2 text-cyan-700 dark:text-cyan-300">
            衍生特征 ({totalDerived}个)
          </div>
          <div className="space-y-1 text-xs">
            {onehotCount > 0 && (
              <div>
                <span className="text-gray-500">One-Hot编码: </span>
                <span className="font-medium text-cyan-600 dark:text-cyan-400">+{onehotCount}个特征</span>
              </div>
            )}
            {datetimeCount > 0 && (
              <div>
                <span className="text-gray-500">日期时间衍生: </span>
                <span className="font-medium text-cyan-600 dark:text-cyan-400">+{datetimeCount}个特征</span>
              </div>
            )}
            {textCount > 0 && (
              <div>
                <span className="text-gray-500">文本衍生: </span>
                <span className="font-medium text-cyan-600 dark:text-cyan-400">+{textCount}个特征</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 排除变量信息 */}
      {(totalExcluded.length > 0 || Object.keys(autoDetected).length > 0) && (
        <div className="p-3 bg-orange-50 dark:bg-orange-900/20 rounded-lg border border-orange-200 dark:border-orange-800">
          <div className="text-sm font-medium mb-2 text-orange-700 dark:text-orange-300">
            排除变量 ({totalExcluded.length}个)
          </div>
          <div className="space-y-2 text-xs">
            {/* 用户指定的排除列 */}
            {userSpecified.length > 0 && (
              <div>
                <span className="text-gray-500">用户指定: </span>
                <span className="font-medium text-orange-600 dark:text-orange-400">
                  {userSpecified.join(", ")}
                </span>
              </div>
            )}
            {/* 自动识别的列 - 始终展示各类别数量（与"样本与特征"tab保持一致） */}
            {Object.keys(autoDetected).length > 0 && (
              <div>
                <span className="text-gray-500">自动识别:</span>
                <div className="space-y-1 mt-1 ml-2">
                  {Object.entries(autoDetected).map(([reason, vars]: [string, unknown]) => (
                    <div key={reason} className="flex items-center gap-2">
                      <span className="text-gray-500">{reason}:</span>
                      <span className="font-medium">{Array.isArray(vars) ? vars.length : 0}个</span>
                      {Array.isArray(vars) && vars.length > 0 && (
                        <span className="text-gray-400">({vars.slice(0, 3).join(", ")}{vars.length > 3 ? "..." : ""})</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// WOE分箱阶段预览
// =============================================================================

function WoeBinningPreview({ data }: { data: Record<string, any> }) {
  const [isExpanded, setIsExpanded] = React.useState(false);
  const ivTable = data.iv_table || [];
  const totalCount = ivTable.length;
  const displayCount = isExpanded ? totalCount : Math.min(10, totalCount);
  const displayFeatures = ivTable.slice(0, displayCount);
  const hasMore = totalCount > 10;

  return (
    <div className="space-y-4">
      {/* IV统计 */}
      <div className="grid grid-cols-3 gap-3">
        <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
          <div className="text-xl font-bold text-blue-600">
            {data.total_features || "-"}
            {/* 显示WOE分箱过滤计算过程：43 = 49 - 6，每个数字带含义说明 */}
            {data.woe_filtered && data.woe_filtered.count > 0 && data.input_features && (
              <span className="text-sm font-normal text-gray-400 ml-1">
                = <span className="text-gray-600">{data.input_features}</span>
                <span className="text-[10px] text-gray-400 mx-0.5">输入</span>
                - <span className="text-gray-600">{data.woe_filtered.count}</span>
                <span className="text-[10px] text-gray-400 ml-0.5">过滤</span>
              </span>
            )}
          </div>
          <div className="text-xs text-gray-500">
            {data.woe_filtered && data.woe_filtered.count > 0 
              ? "分箱特征数 (woe_filtered后)" 
              : "分箱特征数"}
          </div>
        </div>
        <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
          <div className="text-xl font-bold text-green-600">{data.iv_range?.max?.toFixed(3) || "-"}</div>
          <div className="text-xs text-gray-500">最大IV</div>
        </div>
        <div className="p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
          <div className="text-xl font-bold text-yellow-600">{data.iv_range?.min?.toFixed(3) || "-"}</div>
          <div className="text-xs text-gray-500">最小IV</div>
        </div>
      </div>


      {/* IV分布统计（简洁单行方案，与规则挖掘任务保持一致） */}
      {data.iv_distribution && (
        <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
          <div className="text-sm font-medium mb-2">
            IV分布统计
            {data.iv_threshold && (
              <span className="text-xs text-gray-500 ml-2">
                (阈值: {typeof data.iv_threshold === 'object' 
                  ? `${data.iv_threshold.lower ?? 0.02} - ${data.iv_threshold.upper ?? 1}` 
                  : data.iv_threshold})
              </span>
            )}
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="flex justify-between">
              <span className="text-green-600">强 (IV≥0.1)</span>
              <span className="font-medium">{data.iv_distribution.strong || 0}个</span>
            </div>
            <div className="flex justify-between">
              <span className="text-blue-600">中强 (0.05-0.1)</span>
              <span className="font-medium">{data.iv_distribution.medium_strong || 0}个</span>
            </div>
            <div className="flex justify-between">
              <span className="text-yellow-600">中 (0.02-0.05)</span>
              <span className="font-medium">{data.iv_distribution.medium || 0}个</span>
            </div>
            <div className="flex justify-between">
              <span className="text-red-600">弱 (IV&lt;0.02)</span>
              <span className="font-medium">{data.iv_distribution.weak || 0}个</span>
            </div>
          </div>
        </div>
      )}

      {/* WOE分箱过程中过滤的特征（预先过滤+分箱过滤） */}
      {data.woe_filtered && data.woe_filtered.count > 0 && (
        <div className="p-3 bg-orange-50 dark:bg-orange-900/20 rounded-lg border border-orange-200 dark:border-orange-800">
          <div className="text-sm font-medium mb-2 text-orange-700 dark:text-orange-300">
            分箱过程过滤 (woe_filtered)
          </div>
          <div className="text-xs space-y-1">
            <div className="flex justify-between items-center">
              <span className="text-gray-600 dark:text-gray-400">
                输入特征: {data.input_features} → 输出特征: {data.total_features}
              </span>
              <span className="font-medium text-orange-600">
                过滤 {data.woe_filtered.count} 个
              </span>
            </div>
            <div className="text-gray-500">
              原因: {data.woe_filtered.reason}
            </div>
            {data.woe_filtered.features?.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-1">
                {data.woe_filtered.features.map((f: string, i: number) => (
                  <span key={i} className="px-1.5 py-0.5 bg-orange-100 dark:bg-orange-800/50 rounded text-[10px]">
                    {f}
                  </span>
                ))}
                {data.woe_filtered.count > data.woe_filtered.features.length && (
                  <span className="text-[10px] text-gray-500">
                    +{data.woe_filtered.count - data.woe_filtered.features.length}个
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* 低IV提示（如果有） */}
      {data.low_iv_count > 0 && data.note && (
        <div className="text-xs text-yellow-600 bg-yellow-50 dark:bg-yellow-900/20 p-2 rounded">
          {data.note}
        </div>
      )}

      {/* IV表格（支持展开/收起） */}
      {displayFeatures.length > 0 && (
        <div>
          <div className="text-sm font-medium mb-2 flex items-center justify-between">
            <span>IV值 {isExpanded ? `全部 (${totalCount})` : `Top 10`}</span>
            {hasMore && (
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1"
              >
                {isExpanded ? (
                  <>收起 <ChevronUp className="w-3 h-3" /></>
                ) : (
                  <>展开全部 ({totalCount - 10}+) <ChevronDown className="w-3 h-3" /></>
                )}
              </button>
            )}
          </div>
          <div className={isExpanded && totalCount > 20 ? "max-h-[400px] overflow-y-auto" : ""}>
            <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs">特征</TableHead>
                    <TableHead className="text-xs text-right">IV</TableHead>
                    <TableHead className="text-xs text-center">单调性</TableHead>
                    {/* 分箱数 */}
                    {displayFeatures[0]?.n_bins !== undefined && (
                      <TableHead className="text-xs text-center">分箱</TableHead>
                    )}
                  </TableRow>
                </TableHeader>
              <TableBody>
                {displayFeatures.map((item: any, i: number) => (
                  <TableRow key={i} className={item.low_iv ? "bg-red-50/50 dark:bg-red-900/10" : ""}>
                    <TableCell className="text-xs font-mono truncate max-w-[150px]" title={item.feature}>
                      {item.feature}
                      {item.low_iv && <span className="text-red-500 ml-1">*</span>}
                    </TableCell>
                    <TableCell className="text-xs text-right font-medium">{item.iv?.toFixed(4)}</TableCell>
                    <TableCell className="text-xs text-center">
                      {item.monotonic ? (
                        <Badge variant="outline" className="text-green-600 text-[10px]">单调</Badge>
                      ) : (
                        <Badge variant="outline" className="text-yellow-600 text-[10px]">非单调</Badge>
                      )}
                    </TableCell>
                    {item.n_bins !== undefined && (
                      <TableCell className="text-xs text-center">{item.n_bins}</TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          {/* 低IV标记说明 */}
          {data.low_iv_count > 0 && (
            <div className="text-[10px] text-gray-500 mt-1">
              * 标记为低IV变量（IV &lt; {typeof data.iv_threshold === 'object' ? data.iv_threshold.lower : (data.iv_threshold || 0.02)}），将在特征筛选阶段处理
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// 特征筛选阶段预览（优化版 - 行业标准展示）
// =============================================================================

function FeatureSelectionPreview({ data }: { data: Record<string, any> }) {
  // 计算缺失率筛选后的特征数
  const afterMissingFilterCount = data.missing_filter_stats 
    ? (data.before_count || 0) - (data.missing_filter_stats.removed_count || 0)
    : data.before_count;
  
  // 使用新的多步骤流程数据（如果有）
  const selectionFlow = data.selection_flow || [];
  const thresholdConfig = data.threshold_config;
  const allFeaturesDetail = data.all_features_detail || [];
  
  // CSV下载函数：特征筛选明细表
  const downloadFeatureSelectionCSV = () => {
    if (!allFeaturesDetail || allFeaturesDetail.length === 0) return;
    
    const headers = [
      '序号', '特征名称', 'IV值', 'IV等级', '相关性(最大)', '相关特征', 
      'VIF', '缺失率', '分箱数', '坏账率范围', '筛选状态', '筛除原因'
    ];
    
    const rows = allFeaturesDetail.map((f: any, idx: number) => [
      idx + 1,
      f.feature,
      f.iv?.toFixed(4) ?? '',
      f.iv_level ?? '',
      f.max_corr?.toFixed(4) ?? '',
      f.corr_feature ?? '',
      f.vif?.toFixed(2) ?? '',
      f.missing_rate != null ? `${(f.missing_rate * 100).toFixed(1)}%` : '',
      f.n_bins ?? '',
      f.bad_rate_range ?? '',
      f.status ?? '',
      f.remove_reason ?? ''
    ]);
    
    const BOM = '\uFEFF';
    const csvContent = BOM + [
      headers.join(','),
      ...rows.map((row: any[]) => row.map((cell: any) => 
        typeof cell === 'string' && (cell.includes(',') || cell.includes('"')) 
          ? `"${cell.replace(/"/g, '""')}"` : cell
      ).join(','))
    ].join('\n');
    
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `feature_selection_detail_${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };
  
  // CSV下载函数：分箱明细表
  const downloadBinningDetailCSV = () => {
    if (!allFeaturesDetail || allFeaturesDetail.length === 0) return;
    
    const headers = [
      '特征名称', '分箱', 'WOE', '样本数', '坏样本数', '坏账率', 'IV值', '筛选状态'
    ];
    
    const rows: any[][] = [];
    allFeaturesDetail.forEach((f: any) => {
      if (f.bin_detail && f.bin_detail.length > 0) {
        f.bin_detail.forEach((bin: any) => {
          rows.push([
            f.feature,
            bin.bin,
            bin.woe?.toFixed(4) ?? '',
            bin.count ?? '',
            bin.bad_count ?? '',
            bin.bad_rate != null ? `${(bin.bad_rate * 100).toFixed(2)}%` : '',
            f.iv?.toFixed(4) ?? '',  // 新增：IV值列（放在筛选状态列之前）
            f.status ?? ''
          ]);
        });
      }
    });
    
    if (rows.length === 0) return;
    
    const BOM = '\uFEFF';
    const csvContent = BOM + [
      headers.join(','),
      ...rows.map((row: any[]) => row.map((cell: any) => 
        typeof cell === 'string' && (cell.includes(',') || cell.includes('"')) 
          ? `"${cell.replace(/"/g, '""')}"` : cell
      ).join(','))
    ].join('\n');
    
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `binning_detail_${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };
  
  return (
    <div className="space-y-4">
      {/* 特征变化流程 - 多步骤展示（优化版） */}
      <div className="p-3 bg-gradient-to-r from-gray-50 to-green-50 dark:from-gray-900/30 dark:to-green-900/20 rounded-lg">
        <div className="text-sm font-medium mb-2">特征变化流程</div>
        <div className="flex items-center justify-between text-xs overflow-x-auto">
          {selectionFlow.length > 0 ? (
            // 使用新的多步骤流程数据
            selectionFlow.map((step: any, idx: number) => (
              <React.Fragment key={idx}>
                {idx > 0 && <div className="text-gray-400 mx-1 flex-shrink-0">→</div>}
                <div className="text-center flex-shrink-0 min-w-[50px]">
                  <div className={`text-lg font-bold ${
                    idx === selectionFlow.length - 1 ? 'text-green-600' : 
                    step.removed > 0 ? 'text-orange-600' : ''
                  }`}>
                    {step.count}
                  </div>
                  <div className="text-gray-500 text-[10px]">{step.step}</div>
                  {/* 始终显示移除数量：有移除显示红色，为0显示灰色（初始步骤除外） */}
                  {idx > 0 && (
                    <div className={`text-[10px] ${step.removed > 0 ? 'text-red-500' : 'text-gray-400'}`}>
                      {step.removed > 0 ? `-${step.removed}` : '0'}
                    </div>
                  )}
                </div>
              </React.Fragment>
            ))
          ) : (
            // 回退到旧的展示方式
            <>
              <div className="text-center">
                <div className="text-lg font-bold">{data.before_count || "-"}</div>
                <div className="text-gray-500">初始</div>
              </div>
              
              {data.missing_filter_stats && (
                <>
                  <div className="text-gray-400">→</div>
                  <div className="text-center">
                    <div className={`text-lg font-bold ${data.missing_filter_stats.removed_count > 0 ? 'text-red-600' : 'text-gray-600'}`}>
                      {afterMissingFilterCount || "-"}
                    </div>
                    <div className="text-gray-500">缺失率筛选</div>
                    {/* 始终显示移除数量：有移除显示红色，为0显示灰色 */}
                    <div className={`text-[10px] ${data.missing_filter_stats.removed_count > 0 ? 'text-red-500' : 'text-gray-400'}`}>
                      {data.missing_filter_stats.removed_count > 0 ? `-${data.missing_filter_stats.removed_count}` : '0'}
                    </div>
                  </div>
                </>
              )}
              
              {data.onehot_stats && data.onehot_stats.derived_count > 0 && (
                <>
                  <div className="text-gray-400">→</div>
                  <div className="text-center">
                    <div className="text-lg font-bold text-purple-600">{data.after_onehot_count || "-"}</div>
                    <div className="text-gray-500">One-Hot后</div>
                    <div className="text-[10px] text-purple-500">
                      -{data.onehot_stats.original_count}+{data.onehot_stats.derived_count}
                    </div>
                  </div>
                </>
              )}
              
              <div className="text-gray-400">→</div>
              <div className="text-center">
                <div className="text-lg font-bold text-green-600">{data.after_count || "-"}</div>
                <div className="text-gray-500">筛选后</div>
                {data.removed_reasons && Object.keys(data.removed_reasons).length > 0 && (
                  <div className="text-[10px] text-red-500">
                    -{Object.values(data.removed_reasons).reduce((a: number, b: any) => a + (b as number), 0)}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      {/* 筛选阈值配置 - 评分卡任务（3个阈值） */}
      {thresholdConfig && (
        <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
          <div className="text-sm font-medium mb-2">筛选阈值配置</div>
          <div className="grid grid-cols-3 gap-2 text-xs">
            <div className="text-center p-2 bg-white dark:bg-gray-800 rounded">
              <div className="font-medium text-blue-600">IV阈值</div>
              <div className="text-gray-600">{thresholdConfig.iv_lower} ~ {thresholdConfig.iv_upper}</div>
            </div>
            <div className="text-center p-2 bg-white dark:bg-gray-800 rounded">
              <div className="font-medium text-blue-600">相关性阈值</div>
              <div className="text-gray-600">{thresholdConfig.corr_threshold}</div>
            </div>
            <div className="text-center p-2 bg-white dark:bg-gray-800 rounded">
              <div className="font-medium text-blue-600">VIF阈值</div>
              <div className="text-gray-600">{thresholdConfig.vif_threshold}</div>
            </div>
          </div>
        </div>
      )}

      {/* 筛选阈值配置 - 规则挖掘任务（2个阈值：缺失率 + IV） */}
      {!thresholdConfig && (data.iv_threshold !== undefined || data.missing_filter_stats) && (
        <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
          <div className="text-sm font-medium mb-2">筛选阈值配置</div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="text-center p-2 bg-white dark:bg-gray-800 rounded">
              <div className="font-medium text-blue-600">缺失率阈值</div>
              <div className="text-gray-600">{((data.missing_filter_stats?.threshold || 0.5) * 100).toFixed(0)}%</div>
            </div>
            <div className="text-center p-2 bg-white dark:bg-gray-800 rounded">
              <div className="font-medium text-blue-600">IV阈值</div>
              <div className="text-gray-600">
                {typeof data.iv_threshold === 'object' 
                  ? `${data.iv_threshold.lower ?? 0.02} ~ ${data.iv_threshold.upper ?? 1}` 
                  : `≥ ${data.iv_threshold ?? 0.02}`}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 移除原因统计（智能判断：评分卡固定显示3类，规则挖掘动态显示后端返回的数据） */}
      {data.removed_reasons && (
        <div className="p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
          <div className="text-sm font-medium mb-2">移除原因统计</div>
          <div className="space-y-1">
            {(() => {
              // 判断是评分卡任务还是规则挖掘任务
              // 评分卡任务的 removed_reasons 包含 IV筛选移除、相关性移除、VIF移除
              // 规则挖掘任务的 removed_reasons 包含 缺失率筛选移除、IV筛选移除(原始特征)、IV筛选移除(One-Hot衍生)
              const isScorecardTask = thresholdConfig && (
                thresholdConfig.corr_threshold !== undefined || 
                thresholdConfig.vif_threshold !== undefined
              );
              
              if (isScorecardTask) {
                // 评分卡任务：固定显示三类移除原因
                const reasonsOrder = [
                  { key: 'IV筛选移除', hintFn: () => thresholdConfig ? `(IV<${thresholdConfig.iv_lower}或IV>${thresholdConfig.iv_upper})` : '' },
                  { key: '相关性移除', hintFn: () => thresholdConfig ? `(相关系数>${thresholdConfig.corr_threshold})` : '' },
                  { key: 'VIF移除', hintFn: () => thresholdConfig ? `(VIF>${thresholdConfig.vif_threshold})` : '' },
                ];
                return reasonsOrder.map(({ key, hintFn }) => {
                  const count = data.removed_reasons[key] ?? 0;
                  const thresholdHint = hintFn();
                  return (
                    <div key={key} className="flex justify-between text-xs">
                      <span className="text-gray-600">
                        {key}
                        {thresholdHint && <span className="text-gray-400 ml-1">{thresholdHint}</span>}
                      </span>
                      <span className={`font-medium ${count > 0 ? 'text-red-600' : 'text-gray-400'}`}>
                        {count > 0 ? `-${count} 个` : '0 个'}
                      </span>
                    </div>
                  );
                });
              } else {
                // 规则挖掘任务：动态显示后端返回的移除原因
                return Object.entries(data.removed_reasons).map(([reason, count]) => (
                  <div key={reason} className="flex justify-between text-xs">
                    <span className="text-gray-600">{reason}</span>
                    <span className={`font-medium ${(count as number) > 0 ? 'text-red-600' : 'text-gray-400'}`}>
                      {(count as number) > 0 ? `-${count} 个` : '0 个'}
                    </span>
                  </div>
                ));
              }
            })()}
          </div>
        </div>
      )}

      {/* 缺失率筛选详情（有移除时显示详细信息） */}
      {data.missing_filter_stats && data.missing_filter_stats.removed_count > 0 && (
        <div className="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg">
          <div className="text-sm font-medium mb-2">
            缺失率筛选
            <span className="text-xs text-gray-500 ml-2">
              (阈值: {((data.missing_filter_stats.threshold || 0.5) * 100).toFixed(0)}%)
            </span>
          </div>
          <div className="space-y-2 text-xs">
            <div className="flex justify-between">
              <span className="text-red-600">移除高缺失率特征</span>
              <span className="font-medium text-red-600">-{data.missing_filter_stats.removed_count} 个</span>
            </div>
            {data.missing_filter_stats.removed_vars && data.missing_filter_stats.removed_vars.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-1">
                {data.missing_filter_stats.removed_vars.slice(0, 8).map((v: string, i: number) => (
                  <span key={i} className="px-1.5 py-0.5 bg-red-100 dark:bg-red-800/50 rounded text-[10px]">
                    {v}
                  </span>
                ))}
                {data.missing_filter_stats.removed_vars.length > 8 && (
                  <span className="text-[10px] text-gray-500">
                    +{data.missing_filter_stats.removed_vars.length - 8}个
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* One-Hot 编码统计 */}
      {data.onehot_stats && data.onehot_stats.derived_count > 0 && (
        <div className="p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
          <div className="text-sm font-medium mb-2">One-Hot 编码</div>
          <div className="space-y-1 text-xs">
            <div className="flex justify-between">
              <span className="text-gray-600">编码原始列数</span>
              <span className="font-medium">{data.onehot_stats.original_count} 个</span>
            </div>
            <div className="flex justify-between">
              <span className="text-purple-600">产生衍生特征</span>
              <span className="font-medium text-purple-600">+{data.onehot_stats.derived_count} 个</span>
            </div>
            {data.onehot_stats.retained_derived !== undefined && (
              <div className="flex justify-between">
                <span className="text-green-600">IV筛选后保留</span>
                <span className="font-medium text-green-600">{data.onehot_stats.retained_derived} 个</span>
              </div>
            )}
            {data.onehot_stats.removed_derived !== undefined && data.onehot_stats.removed_derived > 0 && (
              <div className="flex justify-between">
                <span className="text-red-600">IV筛选移除</span>
                <span className="font-medium text-red-600">-{data.onehot_stats.removed_derived} 个</span>
              </div>
            )}
            {data.onehot_stats.original_cols && data.onehot_stats.original_cols.length > 0 && (
              <div className="mt-2 pt-2 border-t border-purple-200 dark:border-purple-700">
                <span className="text-gray-500">编码列: </span>
                <span className="text-purple-600">{data.onehot_stats.original_cols.join(', ')}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 警告信息 */}
      {data.warning && (
        <div className="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
          <div className="text-sm text-red-600 dark:text-red-400">
            ⚠️ {data.warning}
          </div>
        </div>
      )}

      {/* 方案B：系数方向验证已迁移至模型训练阶段展示 */}

      {/* 新增原因统计 */}
      {data.added_reasons && Object.keys(data.added_reasons).length > 0 && (
        <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
          <div className="text-sm font-medium mb-2">新增原因统计</div>
          <div className="space-y-1">
            {Object.entries(data.added_reasons).map(([reason, count]) => (
              <div key={reason} className="flex justify-between text-xs">
                <span className="text-gray-600">{reason}</span>
                <span className="font-medium text-green-600">+{count as number} 个</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 特征列表（根据任务类型显示不同术语） */}
      {(data.candidate_features || data.selected_features) && (data.candidate_features || data.selected_features).length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-2">
            <div className="text-sm font-medium">
              {thresholdConfig ? (
                <>
                  候选入模特征 ({(data.candidate_features || data.selected_features).length})
                  <span className="text-[10px] text-gray-400 ml-1">（模型训练后确定最终入模）</span>
                </>
              ) : (
                <>
                  筛选后特征 ({(data.candidate_features || data.selected_features).length})
                  <span className="text-[10px] text-gray-400 ml-1">（用于规则生成）</span>
                </>
              )}
            </div>
          </div>
          <div className="flex flex-wrap gap-1">
            {(data.candidate_features || data.selected_features).slice(0, 15).map((feature: string, i: number) => (
              <Badge key={i} variant="secondary" className="text-[10px]">{feature}</Badge>
            ))}
            {(data.candidate_features || data.selected_features).length > 15 && (
              <Badge variant="outline" className="text-[10px]">
                +{(data.candidate_features || data.selected_features).length - 15} 更多
              </Badge>
            )}
          </div>
        </div>
      )}

      {/* CSV下载按钮组（新增） */}
      {allFeaturesDetail.length > 0 && (
        <div className="flex gap-2 pt-2 border-t border-gray-200 dark:border-gray-700">
          <Button
            variant="outline"
            size="sm"
            className="h-7 text-xs flex-1"
            onClick={downloadFeatureSelectionCSV}
          >
            <Download className="h-3 w-3 mr-1" />
            特征筛选明细
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="h-7 text-xs flex-1"
            onClick={downloadBinningDetailCSV}
          >
            <Download className="h-3 w-3 mr-1" />
            分箱明细
          </Button>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// 模型训练阶段预览
// =============================================================================

function ModelTrainingPreview({ data }: { data: Record<string, any> }) {
  const coefficients = data.coefficients || [];
  const stepwiseResult = data.stepwise_result;
  const coefficientValidation = data.coefficient_validation;
  // B+方案新增
  const config = data.config;
  const postValidation = data.post_validation;
  const allCoefficients = data.all_coefficients || [];
  const [showAllCoefs, setShowAllCoefs] = React.useState(false);

  // 模型拟合指标
  const modelFit = data.model_fit || {};
  const lrPValue = modelFit.lr_pvalue;
  const pseudoR2 = modelFit.pseudo_r2;
  const logLikelihood = modelFit.log_likelihood;
  const aic = modelFit.aic;
  const bic = modelFit.bic;

  // 计算显著变量数（p<0.05，不含const）- 确保类型正确
  const significantCount = coefficients.filter(
    (c: any) => {
      const pValue = c.p_value != null ? Number(c.p_value) : (c.pvalue != null ? Number(c.pvalue) : null);
      return c.feature !== 'const' && pValue != null && !isNaN(pValue) && pValue < 0.05;
    }
  ).length;
  // 入模变量数（不含const）
  const featureCount = coefficients.filter((c: any) => c.feature !== 'const').length;
  
  // 系数方向验证
  const validDirectionCount = coefficientValidation?.valid_direction?.length || 0;
  const invalidDirectionCount = coefficientValidation?.invalid_direction?.length || 0;
  const totalDirectionChecked = validDirectionCount + invalidDirectionCount;

  return (
    <div className="space-y-4">
      {/* 模型概览 - 2026-02-11: 指标名称在上，数值在下；顺序优化；展示风格统一 */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {/* 1. 入模特征数 */}
        <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
          <div className="text-xs text-blue-600 mb-1">入模特征数</div>
          <div className="text-xl font-bold text-blue-600">{featureCount || "-"}</div>
        </div>
        
        {/* 2. 似然比检验 - 模型整体显著性 */}
        <div className={`p-3 rounded-lg ${lrPValue !== undefined && lrPValue !== null && lrPValue < 0.05 ? 'bg-green-50 dark:bg-green-900/20' : 'bg-yellow-50 dark:bg-yellow-900/20'}`}>
          <div className={`text-xs mb-1 ${lrPValue !== undefined && lrPValue !== null && lrPValue < 0.05 ? 'text-green-600' : 'text-yellow-600'}`}>
            似然比检验(p)
          </div>
          <div className={`text-xl font-bold ${lrPValue !== undefined && lrPValue !== null && lrPValue < 0.05 ? 'text-green-600' : 'text-yellow-600'}`}>
            {lrPValue !== undefined && lrPValue !== null ? (lrPValue < 0.001 ? '<0.001' : lrPValue.toFixed(4)) : '-'}
          </div>
        </div>
        
        {/* 3. 显著变量 - 与Tab页统一设计 */}
        <div className={`p-3 rounded-lg ${significantCount === featureCount && featureCount > 0 ? 'bg-green-50 dark:bg-green-900/20' : 'bg-yellow-50 dark:bg-yellow-900/20'}`}>
          <div className={`text-xs mb-1 ${significantCount === featureCount && featureCount > 0 ? 'text-green-600' : 'text-yellow-600'}`}>
            显著变量
          </div>
          <div className="text-xl font-bold">
            <span className={significantCount === featureCount && featureCount > 0 ? 'text-green-600' : 'text-yellow-600'}>
              {significantCount}
            </span>
            <span className="text-sm text-gray-400">/{featureCount}</span>
          </div>
          <div className={`text-xs ${significantCount === featureCount && featureCount > 0 ? 'text-green-600' : 'text-yellow-600'}`}>
            {significantCount === featureCount && featureCount > 0 ? '全部显著' : `${featureCount - significantCount}个不显著`}
          </div>
        </div>
        
        {/* 4. 系数方向验证 - 与Tab页统一设计 */}
        <div className={`p-3 rounded-lg ${invalidDirectionCount === 0 && totalDirectionChecked > 0 ? 'bg-green-50 dark:bg-green-900/20' : invalidDirectionCount > 0 ? 'bg-red-50 dark:bg-red-900/20' : 'bg-gray-50 dark:bg-gray-900/20'}`}>
          <div className={`text-xs mb-1 ${invalidDirectionCount === 0 && totalDirectionChecked > 0 ? 'text-green-600' : invalidDirectionCount > 0 ? 'text-red-600' : 'text-gray-500'}`}>
            系数方向
          </div>
          {totalDirectionChecked > 0 ? (
            <>
              <div className="text-xl font-bold">
                <span className={invalidDirectionCount === 0 ? 'text-green-600' : 'text-red-600'}>
                  {validDirectionCount}
                </span>
                <span className="text-sm text-gray-400">/{totalDirectionChecked}</span>
              </div>
              <div className={`text-xs ${invalidDirectionCount === 0 ? 'text-green-600' : 'text-red-600'}`}>
                {invalidDirectionCount === 0 ? '全部正确' : `${invalidDirectionCount}个异常`}
              </div>
            </>
          ) : (
            <>
              <div className="text-xl font-bold text-gray-400">-</div>
              <div className="text-xs text-gray-400">未验证</div>
            </>
          )}
        </div>
        
        {/* 5. 截距项 - 放在最后 */}
        <div className="p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
          <div className="text-xs text-purple-600 mb-1">截距项</div>
          <div className="text-xl font-bold text-purple-600">{data.intercept?.toFixed(4) || "-"}</div>
        </div>
      </div>

      {/* 模型拟合指标详情 - 伪R²、对数似然、AIC、BIC - 2026-02-11: 优化为等距4列布局 */}
      {(pseudoR2 !== undefined || logLikelihood !== undefined || aic !== undefined || bic !== undefined) && (
        <div className="p-3 bg-slate-50 dark:bg-slate-900/20 rounded-lg border border-slate-200 dark:border-slate-700">
          <div className="text-sm font-medium mb-2 flex items-center gap-2">
            <span>📊 模型拟合指标</span>
          </div>
          <div className="grid grid-cols-4 gap-3 text-xs">
            <div className="p-2 bg-white dark:bg-slate-800 rounded text-center">
              <div className="text-gray-500 mb-1">伪R²</div>
              <div className="font-medium font-mono">{pseudoR2 !== undefined ? (pseudoR2 * 100).toFixed(2) + '%' : '-'}</div>
            </div>
            <div className="p-2 bg-white dark:bg-slate-800 rounded text-center">
              <div className="text-gray-500 mb-1">对数似然</div>
              <div className="font-medium font-mono">{logLikelihood !== undefined ? logLikelihood.toFixed(2) : '-'}</div>
            </div>
            <div className="p-2 bg-white dark:bg-slate-800 rounded text-center">
              <div className="text-gray-500 mb-1">AIC</div>
              <div className="font-medium font-mono">{aic !== undefined ? aic.toFixed(2) : '-'}</div>
            </div>
            <div className="p-2 bg-white dark:bg-slate-800 rounded text-center">
              <div className="text-gray-500 mb-1">BIC</div>
              <div className="font-medium font-mono">{bic !== undefined ? bic.toFixed(2) : '-'}</div>
            </div>
          </div>
        </div>
      )}

      {/* B+方案：验证配置信息 - 与参数Tab展示格式保持一致 */}
      {config && (
        <div className="p-3 bg-slate-50 dark:bg-slate-900/20 rounded-lg border border-slate-200 dark:border-slate-700">
          <div className="text-sm font-medium mb-2 flex items-center gap-2">
            <span>⚙️ 验证配置</span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            {/* 逐步回归方向 */}
            <div className="p-2 bg-white dark:bg-slate-800 rounded">
              <div className="text-gray-500">逐步回归方向</div>
              <div className="font-medium">
                {config.stepwise_direction === 'both' ? '双向' : 
                 config.stepwise_direction === 'forward' ? '前向' : 
                 config.stepwise_direction === 'backward' ? '后向' : config.stepwise_direction || '双向'}
              </div>
            </div>
            {/* 显著性水平 */}
            <div className="p-2 bg-white dark:bg-slate-800 rounded">
              <div className="text-gray-500">显著性水平</div>
              <div className="font-medium">{config.significance_level || 0.05}</div>
            </div>
            {/* 显著性检验模式 */}
            <div className="p-2 bg-white dark:bg-slate-800 rounded">
              <div className="text-gray-500">显著性检验模式</div>
              <div className="font-medium">
                {config.significance_mode === 'skip' ? '跳过（不做检验）' : 
                 config.significance_mode === 'warn' ? '警告（保留变量，仅提示）' : 
                 config.significance_mode === 'remove' ? '移除（迭代移除不显著变量）' : config.significance_mode}
              </div>
            </div>
            {/* 系数方向异常处理 */}
            <div className="p-2 bg-white dark:bg-slate-800 rounded">
              <div className="text-gray-500">系数方向异常处理</div>
              <div className="font-medium">
                {config.coefficient_direction_mode === 'skip' ? '跳过（不做检验）' : 
                 config.coefficient_direction_mode === 'warn' ? '警告（保留变量，仅提示）' : 
                 config.coefficient_direction_mode === 'remove' ? '移除（迭代移除异常变量）' : config.coefficient_direction_mode}
              </div>
            </div>
            {/* 最大迭代次数 - 仅当启用迭代移除模式时显示 */}
            {(config.significance_mode === 'remove' || config.coefficient_direction_mode === 'remove') && (
              <div className="p-2 bg-white dark:bg-slate-800 rounded col-span-2">
                <div className="text-gray-500">最大迭代次数</div>
                <div className="font-medium">{config.max_validation_iterations || 20}</div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* B+方案：迭代验证结果 */}
      {postValidation && postValidation.total_iterations > 0 && (
        <div className="p-3 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-700">
          <div className="text-sm font-medium mb-2 flex items-center gap-2">
            <span>🔄 迭代验证</span>
            <Badge variant={postValidation.converged ? "default" : "secondary"} className="text-xs">
              {postValidation.converged ? '✓ 已收敛' : '达到最大迭代'}
            </Badge>
            <span className="text-xs text-gray-500">
              共{postValidation.total_iterations}轮
            </span>
          </div>
          
          {/* 迭代日志 */}
          <div className="max-h-[150px] overflow-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-xs py-1 w-12">轮次</TableHead>
                  <TableHead className="text-xs py-1">特征数</TableHead>
                  <TableHead className="text-xs py-1">移除特征</TableHead>
                  <TableHead className="text-xs py-1">原因</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {postValidation.iterations?.map((iter: any, idx: number) => (
                  <TableRow key={idx}>
                    <TableCell className="text-xs py-1">{iter.iteration}</TableCell>
                    <TableCell className="text-xs py-1">{iter.feature_count}</TableCell>
                    <TableCell className="text-xs py-1 font-mono truncate max-w-[100px]">
                      {iter.removed_this_iteration?.length > 0 
                        ? iter.removed_this_iteration.map((r: any) => r.feature).join(', ')
                        : '-'}
                    </TableCell>
                    <TableCell className="text-xs py-1 truncate max-w-[150px]">
                      {iter.removed_this_iteration?.length > 0 
                        ? iter.removed_this_iteration.map((r: any) => {
                            // 简化原因显示
                            if (r.reason?.includes('显著性')) return '不显著';
                            if (r.reason?.includes('系数方向')) return '系数为负';
                            return r.reason;
                          }).join(', ')
                        : '全部通过'}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          
          {/* 汇总统计 */}
          {postValidation.iterations && postValidation.iterations.length > 0 && (() => {
            const totalRemoved = postValidation.iterations.reduce(
              (sum: number, iter: any) => sum + (iter.removed_this_iteration?.length || 0), 0
            );
            const initialCount = postValidation.iterations[0]?.feature_count || 0;
            return totalRemoved > 0 && (
              <div className="mt-2 text-xs text-amber-700 dark:text-amber-400">
                📊 特征变化: {initialCount} → {postValidation.final_feature_count}（移除{totalRemoved}个）
              </div>
            );
          })()}
        </div>
      )}

      {/* 逐步回归结果 - 方案B移至模型训练阶段 */}
      {stepwiseResult && stepwiseResult.steps && stepwiseResult.steps.length > 0 && (
        <div className="p-3 bg-indigo-50 dark:bg-indigo-900/20 rounded-lg border border-indigo-200 dark:border-indigo-700">
          <div className="text-sm font-medium mb-2 flex items-center gap-2">
            <span>📈 逐步回归</span>
            <Badge variant="outline" className="text-xs">
              {stepwiseResult.direction || 'both'}方向
            </Badge>
            <Badge variant="secondary" className="text-xs">
              α = {stepwiseResult.significance_level || 0.05}
            </Badge>
          </div>
          <div className="max-h-[120px] overflow-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-xs py-1">步骤</TableHead>
                  <TableHead className="text-xs py-1">操作</TableHead>
                  <TableHead className="text-xs py-1">变量</TableHead>
                  <TableHead className="text-xs py-1 text-right">P值</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {stepwiseResult.steps.slice(0, 8).map((step: any, idx: number) => (
                  <TableRow key={idx}>
                    <TableCell className="text-xs py-1">{step.iteration}</TableCell>
                    <TableCell className="text-xs py-1">
                      <Badge variant={step.action === 'add' ? 'default' : 'destructive'} className="text-[10px] px-1">
                        {step.action === 'add' ? '✓' : '✗'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs py-1 font-mono truncate max-w-[80px]">
                      {step.feature.replace(/_woe$/, '')}
                    </TableCell>
                    <TableCell className="text-xs py-1 text-right font-mono">
                      {step.pvalue?.toFixed(4) || '-'}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          {stepwiseResult.steps.length > 8 && (
            <div className="text-xs text-gray-500 mt-1">
              显示前8步（共{stepwiseResult.steps.length}步）
            </div>
          )}
        </div>
      )}


      {/* 显著性检验（P值）- 方案B移至模型训练阶段 */}
      {stepwiseResult?.final_pvalues && Object.keys(stepwiseResult.final_pvalues).length > 0 && (
        <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-700">
          <div className="text-sm font-medium mb-2 flex items-center gap-2">
            <span>📊 显著性检验 (P值)</span>
          </div>
          <div className="max-h-[120px] overflow-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-xs py-1">变量</TableHead>
                  <TableHead className="text-xs py-1 text-right">P值</TableHead>
                  <TableHead className="text-xs py-1 text-center">显著性</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {Object.entries(stepwiseResult.final_pvalues)
                  .sort((a, b) => (a[1] as number) - (b[1] as number))
                  .slice(0, 10)
                  .map(([varName, pvalue], idx) => {
                    const p = pvalue as number;
                    // P值格式化为区间显示
                    const pValueDisplay = p < 0.001 ? "< 0.001" : 
                                         p < 0.01 ? "< 0.01" : 
                                         p < 0.05 ? "< 0.05" : 
                                         p < 0.1 ? "< 0.1" : p.toFixed(3);
                    // 变量名处理：const 显示为 const（截距）
                    const displayName = varName === 'const' ? 'const（截距）' : varName.replace(/_woe$/, '');
                    // 显著性等级（行业标准）
                    const significanceInfo = p < 0.001 
                      ? { label: "极显著", color: "bg-green-600 text-white" }
                      : p < 0.01 
                      ? { label: "高度显著", color: "bg-green-500 text-white" }
                      : p < 0.05 
                      ? { label: "显著", color: "bg-blue-500 text-white" }
                      : p < 0.1 
                      ? { label: "边缘显著", color: "bg-yellow-500 text-white" }
                      : { label: "不显著", color: "bg-red-500 text-white" };
                    
                    return (
                      <TableRow key={idx}>
                        <TableCell className="text-xs py-1 font-mono truncate max-w-[120px]">
                          {displayName}
                        </TableCell>
                        <TableCell className="text-xs py-1 text-right font-mono">
                          {pValueDisplay}
                        </TableCell>
                        <TableCell className="text-xs py-1 text-center">
                          <Badge className={`text-[10px] px-1.5 ${significanceInfo.color}`}>
                            {significanceInfo.label}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    );
                  })}
              </TableBody>
            </Table>
          </div>
          <div className="text-[10px] text-gray-500 mt-1">
            显著性标准：P&lt;0.001 极显著 | P&lt;0.01 高度显著 | P&lt;0.05 显著 | P&lt;0.1 边缘显著 | P≥0.1 不显著
          </div>
        </div>
      )}

      {/* 系数方向验证 - 方案B移至模型训练阶段（使用详细展示模式） */}
      {coefficientValidation && (
        <div className="p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg border border-purple-200 dark:border-purple-700">
          <div className="text-sm font-medium mb-2 flex items-center gap-2">
            <span>🎯 系数方向验证</span>
            <span className={`text-xs px-2 py-0.5 rounded ${
              coefficientValidation.mode === 'warn' ? 'bg-yellow-100 text-yellow-700' :
              coefficientValidation.mode === 'remove' ? 'bg-red-100 text-red-700' :
              'bg-gray-100 text-gray-700'
            }`}>
              {coefficientValidation.mode === 'warn' ? '警告模式' :
               coefficientValidation.mode === 'remove' ? '移除模式' :
               coefficientValidation.mode === 'ignore' ? '忽略模式' : coefficientValidation.mode}
            </span>
          </div>
          
          {/* 验证结果统计 */}
          <div className="grid grid-cols-2 gap-3 mb-2">
            <div className="text-center p-2 bg-green-100 dark:bg-green-900/30 rounded">
              <div className="text-lg font-bold text-green-600">
                {coefficientValidation.valid_direction?.length || 0}
              </div>
              <div className="text-xs text-green-700">方向正确</div>
            </div>
            <div className="text-center p-2 bg-red-100 dark:bg-red-900/30 rounded">
              <div className="text-lg font-bold text-red-600">
                {coefficientValidation.invalid_direction?.length || 0}
              </div>
              <div className="text-xs text-red-700">方向异常</div>
            </div>
          </div>
          
          {/* 异常特征详情（如果有） */}
          {coefficientValidation.invalid_direction && coefficientValidation.invalid_direction.length > 0 && (
            <div className="mt-2 p-2 bg-white dark:bg-gray-800 rounded border">
              <div className="text-xs font-medium text-red-600 mb-1">
                方向异常特征（系数为负）：
              </div>
              <div className="space-y-1 max-h-[80px] overflow-auto">
                {coefficientValidation.invalid_direction.map((feat: string, idx: number) => {
                  const coef = coefficientValidation.invalid_coefficients?.[feat];
                  return (
                    <div key={idx} className="flex justify-between text-xs">
                      <span className="text-gray-700 dark:text-gray-300 truncate max-w-[120px]">
                        {feat.replace(/_woe$/, '')}
                      </span>
                      {coef !== undefined && (
                        <span className="font-mono text-red-500">
                          β = {typeof coef === 'number' ? coef.toFixed(4) : coef}
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
          
          {/* 警告信息 */}
          {coefficientValidation.warnings && coefficientValidation.warnings.length > 0 && (
            <div className="mt-2 p-2 bg-yellow-100 dark:bg-yellow-900/30 rounded text-xs">
              {coefficientValidation.warnings.map((warning: string, idx: number) => (
                <div key={idx} className="text-yellow-700 dark:text-yellow-400 mb-1">
                  ⚠️ {warning}
                </div>
              ))}
            </div>
          )}
          
          {/* 提示信息 */}
          <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
            💡 请根据业务逻辑判断异常系数是否合理（如非单调关系可能导致负系数）
          </div>
        </div>
      )}

      {/* 模型系数表格 */}
      {coefficients.length > 0 && (
        <div>
          <div className="text-sm font-medium mb-2">模型系数</div>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="text-xs">特征</TableHead>
                <TableHead className="text-xs text-right">系数</TableHead>
                <TableHead className="text-xs text-right">标准误</TableHead>
                <TableHead className="text-xs text-right">z值</TableHead>
                <TableHead className="text-xs text-right">P值</TableHead>
                <TableHead className="text-xs text-right">95%置信区间</TableHead>
                <TableHead className="text-xs text-center">显著性</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {coefficients.slice(0, 10).map((item: any, i: number) => {
                // 判断置信区间是否包含0（不显著的信号）
                const ciContainsZero = item.ci_lower != null && item.ci_upper != null && 
                  item.ci_lower <= 0 && item.ci_upper >= 0;
                // 计算z值（系数/标准误）
                const zValue = item.std_err != null && item.std_err !== 0 
                  ? item.coefficient / item.std_err 
                  : (item.z_value ?? item.z ?? null);
                // 获取显著性标记
                const getSignificanceMarker = (pvalue: number | null | undefined) => {
                  if (pvalue == null) return "";
                  if (pvalue < 0.001) return "***";
                  if (pvalue < 0.01) return "**";
                  if (pvalue < 0.05) return "*";
                  if (pvalue < 0.1) return ".";
                  return "";
                };
                return (
                  <TableRow key={i}>
                    <TableCell className="text-xs font-mono truncate max-w-[120px]">{item.feature}</TableCell>
                    <TableCell className="text-xs text-right">
                      <span className={cn(
                        "font-medium",
                        item.coefficient > 0 ? "text-red-600" : "text-green-600"
                      )}>
                        {item.coefficient?.toFixed(4)}
                      </span>
                    </TableCell>
                    <TableCell className="text-xs text-right text-gray-600">
                      {item.std_err != null ? Number(item.std_err).toFixed(4) : "-"}
                    </TableCell>
                    <TableCell className="text-xs text-right font-mono">
                      {zValue != null ? Number(zValue).toFixed(2) : "-"}
                    </TableCell>
                    <TableCell className="text-xs text-right">
                      {item.pvalue != null ? (
                        <span className={cn(
                          item.pvalue < 0.001 ? "text-green-600 font-bold" :
                          item.pvalue < 0.01 ? "text-green-600 font-medium" : 
                          item.pvalue < 0.05 ? "text-green-600" : 
                          item.pvalue < 0.1 ? "text-yellow-600" : "text-red-600"
                        )}>
                          {item.pvalue < 0.001 ? "< 0.001" : Number(item.pvalue).toFixed(4)}
                        </span>
                      ) : "-"}
                    </TableCell>
                    <TableCell className="text-xs text-right">
                      {item.ci_lower != null && item.ci_upper != null ? (
                        <span className={cn(
                          ciContainsZero ? "text-yellow-600" : "text-gray-600"
                        )}>
                          [{Number(item.ci_lower).toFixed(3)}, {Number(item.ci_upper).toFixed(3)}]
                        </span>
                      ) : "-"}
                    </TableCell>
                    <TableCell className="text-xs text-center">
                      <span className={cn(
                        "font-bold",
                        item.pvalue != null && item.pvalue < 0.001 ? "text-green-600" :
                        item.pvalue != null && item.pvalue < 0.01 ? "text-green-500" :
                        item.pvalue != null && item.pvalue < 0.05 ? "text-yellow-600" :
                        item.pvalue != null && item.pvalue < 0.1 ? "text-orange-500" : "text-gray-400"
                      )}>
                        {getSignificanceMarker(item.pvalue)}
                      </span>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
          <div className="mt-2 p-2 bg-gray-50 dark:bg-gray-900/30 rounded text-xs text-gray-600 dark:text-gray-400 space-y-1">
            <div className="font-medium text-gray-700 dark:text-gray-300">指标说明：</div>
            <div>
              <span className="font-medium">显著性标记：</span>
              <span className="text-green-600 font-bold">***</span> P&lt;0.001
              <span className="mx-1">|</span>
              <span className="text-green-500 font-semibold">**</span> P&lt;0.01
              <span className="mx-1">|</span>
              <span className="text-yellow-600">*</span> P&lt;0.05
              <span className="mx-1">|</span>
              <span className="text-orange-500">.</span> P&lt;0.1
            </div>
            <div>
              <span className="font-medium">z值：</span>
              <span className="text-green-600">|z| &gt; 2 通常显著</span>
              <span className="mx-1">|</span>
              <span className="text-gray-600">z = 系数/标准误</span>
            </div>
            <div>
              <span className="font-medium">95%置信区间：</span>
              <span className="text-green-600">区间不含0 = 显著</span>
              <span className="mx-1">|</span>
              <span className="text-yellow-600">区间包含0 = 可能不显著</span>
            </div>
          </div>
        </div>
      )}

      {/* B+方案：全部入模特征（10个以上可折叠） */}
      {allCoefficients.length > 10 && (
        <div className="p-3 bg-gray-50 dark:bg-gray-900/20 rounded-lg border border-gray-200 dark:border-gray-700">
          <div 
            className="text-sm font-medium mb-2 flex items-center gap-2 cursor-pointer"
            onClick={() => setShowAllCoefs(!showAllCoefs)}
          >
            <span>📋 全部入模特征</span>
            <Badge variant="outline" className="text-xs">
              {allCoefficients.length}个
            </Badge>
            <span className="text-xs text-gray-500 ml-auto">
              {showAllCoefs ? '▼ 收起' : '▶ 展开'}
            </span>
          </div>
          
          {showAllCoefs && (
            <div className="max-h-[200px] overflow-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs py-1">#</TableHead>
                    <TableHead className="text-xs py-1">特征</TableHead>
                    <TableHead className="text-xs py-1 text-right">系数</TableHead>
                    <TableHead className="text-xs py-1 text-right">标准误</TableHead>
                    <TableHead className="text-xs py-1 text-right">P值</TableHead>
                    <TableHead className="text-xs py-1 text-right">95% CI</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {allCoefficients.map((item: any, i: number) => {
                    const ciContainsZero = item.ci_lower != null && item.ci_upper != null && 
                      item.ci_lower <= 0 && item.ci_upper >= 0;
                    return (
                      <TableRow key={i}>
                        <TableCell className="text-xs py-1 text-gray-400">{i + 1}</TableCell>
                        <TableCell className="text-xs py-1 font-mono truncate max-w-[100px]">{item.feature}</TableCell>
                        <TableCell className="text-xs py-1 text-right">
                          <span className={cn(
                            "font-medium",
                            item.coefficient > 0 ? "text-red-600" : "text-green-600"
                          )}>
                            {item.coefficient?.toFixed(4)}
                          </span>
                        </TableCell>
                        <TableCell className="text-xs py-1 text-right text-gray-600">
                          {item.std_err != null ? Number(item.std_err).toFixed(4) : "-"}
                        </TableCell>
                        <TableCell className="text-xs py-1 text-right">
                          {item.pvalue != null ? (
                            <span className={cn(
                              item.pvalue < 0.001 ? "text-green-600 font-bold" :
                              item.pvalue < 0.01 ? "text-green-600 font-medium" : 
                              item.pvalue < 0.05 ? "text-green-600" : 
                              item.pvalue < 0.1 ? "text-yellow-600" : "text-red-600"
                            )}>
                              {item.pvalue < 0.001 ? "< 0.001" : Number(item.pvalue).toFixed(4)}
                            </span>
                          ) : "-"}
                        </TableCell>
                        <TableCell className="text-xs py-1 text-right">
                          {item.ci_lower != null && item.ci_upper != null ? (
                            <span className={cn(
                              ciContainsZero ? "text-yellow-600" : "text-gray-600"
                            )}>
                              [{Number(item.ci_lower).toFixed(3)}, {Number(item.ci_upper).toFixed(3)}]
                            </span>
                          ) : "-"}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// 规则评估阶段预览（规则挖掘任务专用）
// =============================================================================

function RuleEvaluationPreview({ data }: { data: Record<string, any> }) {
  const beforeCount = data.before_count ?? data.beforeCount ?? "-";
  const afterCount = data.after_count ?? data.afterCount ?? "-";
  const filterCriteria = data.filter_criteria ?? data.filterCriteria ?? {};
  
  // 计算过滤率
  const filterRate = beforeCount !== "-" && afterCount !== "-" && Number(beforeCount) > 0
    ? ((Number(beforeCount) - Number(afterCount)) / Number(beforeCount) * 100).toFixed(1)
    : null;

  return (
    <div className="space-y-4">
      {/* 规则数量统计 */}
      <div className="grid grid-cols-2 gap-3">
        <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
          <div className="text-xs text-gray-500">评估前规则数</div>
          <div className="text-2xl font-bold text-blue-600">{beforeCount}</div>
        </div>
        <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
          <div className="text-xs text-gray-500">评估后规则数</div>
          <div className="text-2xl font-bold text-green-600">{afterCount}</div>
          {filterRate && (
            <div className="text-[10px] text-gray-400">淘汰率: {filterRate}%</div>
          )}
        </div>
      </div>

      {/* 评估阈值条件 */}
      {Object.keys(filterCriteria).length > 0 && (
        <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
          <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">评估阈值</div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            {filterCriteria.max_hit_rate != null && (
              <div className="flex justify-between">
                <span className="text-gray-500">最大命中率:</span>
                <span className="font-medium">{filterCriteria.max_hit_rate}</span>
              </div>
            )}
            {filterCriteria.min_lift != null && (
              <div className="flex justify-between">
                <span className="text-gray-500">最小提升度:</span>
                <span className="font-medium">{filterCriteria.min_lift}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 评估统计（如果有） */}
      {data.evaluation_stats && (
        <div className="p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
          <div className="text-sm font-medium text-purple-700 dark:text-purple-300 mb-2">评估统计</div>
          <div className="text-xs text-gray-600 dark:text-gray-400">
            {JSON.stringify(data.evaluation_stats, null, 2)}
          </div>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// 规则生成阶段预览
// =============================================================================

// bin_method 值到中文标签的映射
const BIN_METHOD_LABELS: Record<string, string> = {
  quantile: "等频分箱",
  uniform: "等距分箱",
  chi2: "卡方分箱",
  tree: "决策树最佳分箱",
  custom: "自定义阈值",
};

// rule_directions 值到中文标签的映射
const RULE_DIRECTIONS_LABELS: Record<string, string> = {
  both: "双向 (<=, >)",
  "<=": "仅 <=",
  ">": "仅 >",
};

function RuleGenerationPreview({ data }: { data: Record<string, any> }) {
  const [rulesExpanded, setRulesExpanded] = useState(false);
  
  const totalRules = data.total_rules ?? data.totalRules ?? 0;
  const miningMode = data.mining_mode ?? data.miningMode ?? "unknown";
  const useFullTree = data.use_full_tree ?? data.useFullTree;
  const nVars = data.n_vars ?? data.nVars;
  const rulesPreview = data.rules_preview ?? [];
  // 全量规则数据（用于CSV下载）
  const allRulesForDownload: Array<Record<string, any>> = data.all_rules_for_download ?? [];
  
  const miningModeDisplay = miningMode === "single" ? "单变量规则" : 
                            miningMode === "multi" ? "多变量规则" : miningMode;
  
  // 多特征模式显示挖掘方法，单特征模式显示分箱方法
  const binMethod = data.bin_method ?? data.binMethod;
  const binMethodDisplay = BIN_METHOD_LABELS[binMethod] ?? binMethod ?? "N/A";
  const miningMethodDisplay = useFullTree ? "全特征树" : "组合树";
  
  // 规则算子（单特征模式专用）
  const ruleDirections = data.rule_directions ?? data.ruleDirections;
  const ruleDirectionsDisplay = RULE_DIRECTIONS_LABELS[ruleDirections] ?? ruleDirections ?? "N/A";

  // 下载全量规则为CSV（简洁版：仅规则表达式，指标在筛选阶段展示）
  const handleDownloadPreview = () => {
    // 优先使用全量数据，没有则回退到预览数据
    const downloadData = allRulesForDownload.length > 0 ? allRulesForDownload : rulesPreview;
    if (downloadData.length === 0) return;
    
    const csvContent = [
      // 添加生成参数说明行（单特征模式显示分箱方法和规则算子，多特征模式显示挖掘方法）
      miningMode === "single"
        ? `# 生成规则数: ${totalRules}, 挖掘模式: ${miningModeDisplay}, 分箱方法: ${binMethodDisplay}, 规则算子: ${ruleDirectionsDisplay}, 分箱数量: ${data.n_bins ?? 'N/A'}`
        : `# 生成规则数: ${totalRules}, 挖掘模式: ${miningModeDisplay}, 挖掘方法: ${miningMethodDisplay}`,
      miningMode === "multi"
        ? `# 决策树深度: ${data.max_depth ?? 'N/A'}, 叶节点最小样本: ${data.min_samples_leaf ?? 'N/A'}, 变量组合数: ${nVars ?? 'N/A'}`
        : '',
      '规则表达式',
      ...downloadData.map((row: Record<string, any>) => {
        const rule = row.rule ?? '';
        // 处理包含逗号或引号的字符串
        if (typeof rule === 'string' && (rule.includes(',') || rule.includes('"') || rule.includes('\n'))) {
          return `"${rule.replace(/"/g, '""')}"`;
        }
        return rule;
      })
    ].join('\n');
    
    const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `generated_rules_${new Date().toISOString().slice(0,10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-4">
      {/* 规则生成统计 */}
      <div className="grid grid-cols-2 gap-3">
        <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
          <div className="text-xs text-gray-500">生成规则数</div>
          <div className="text-2xl font-bold text-blue-600">{totalRules.toLocaleString()}</div>
        </div>
        <div className="p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
          <div className="text-xs text-gray-500">挖掘模式</div>
          <div className="text-lg font-bold text-purple-600">{miningModeDisplay}</div>
        </div>
      </div>

      {/* 生成参数信息 */}
      <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
        <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">生成参数</div>
        <div className="grid grid-cols-2 gap-2 text-xs">
          {/* 单特征模式显示分箱方法，多特征模式显示挖掘方法 */}
          {miningMode === "single" ? (
            <div className="flex justify-between">
              <span className="text-gray-500">分箱方法:</span>
              <span className="font-medium">{binMethodDisplay}</span>
            </div>
          ) : (
            <div className="flex justify-between">
              <span className="text-gray-500">挖掘方法:</span>
              <span className="font-medium">{miningMethodDisplay}</span>
            </div>
          )}
          {/* 单特征模式显示规则算子 */}
          {miningMode === "single" && ruleDirections && (
            <div className="flex justify-between">
              <span className="text-gray-500">规则算子:</span>
              <span className="font-medium">{ruleDirectionsDisplay}</span>
            </div>
          )}
          {nVars && (
            <div className="flex justify-between">
              <span className="text-gray-500">变量组合数:</span>
              <span className="font-medium">{nVars}</span>
            </div>
          )}
          {data.max_depth && (
            <div className="flex justify-between">
              <span className="text-gray-500">决策树深度:</span>
              <span className="font-medium">{data.max_depth}</span>
            </div>
          )}
          {data.min_samples_leaf && (
            <div className="flex justify-between">
              <span className="text-gray-500">叶节点最小样本:</span>
              <span className="font-medium">{data.min_samples_leaf}</span>
            </div>
          )}
          {data.n_bins && (
            <div className="flex justify-between">
              <span className="text-gray-500">分箱数量:</span>
              <span className="font-medium">{data.n_bins}</span>
            </div>
          )}
          {data.tree_count && (
            <div className="flex justify-between">
              <span className="text-gray-500">决策树数量:</span>
              <span className="font-medium">{data.tree_count}</span>
            </div>
          )}
        </div>
      </div>

      {/* 规则预览表（可折叠） */}
      {rulesPreview.length > 0 && (
        <div className="border rounded-lg overflow-hidden">
          <div 
            className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800/50 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700/50"
            onClick={() => setRulesExpanded(!rulesExpanded)}
          >
            <div className="flex items-center gap-2">
              {rulesExpanded ? (
                <ChevronUp className="h-4 w-4 text-gray-500" />
              ) : (
                <ChevronDown className="h-4 w-4 text-gray-500" />
              )}
              <span className="text-sm font-medium">规则预览</span>
              <Badge variant="outline" className="text-xs">
                显示前 {rulesPreview.length} 条
              </Badge>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 px-2 text-xs"
              onClick={(e) => {
                e.stopPropagation();
                handleDownloadPreview();
              }}
              disabled={allRulesForDownload.length === 0 && rulesPreview.length === 0}
            >
              <Download className="h-3 w-3 mr-1" />
              下载全部 ({allRulesForDownload.length > 0 ? allRulesForDownload.length : rulesPreview.length}条)
            </Button>
          </div>
          
          {rulesExpanded && (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs w-12">#</TableHead>
                    <TableHead className="text-xs">规则表达式</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rulesPreview.map((rule: Record<string, any>, idx: number) => (
                    <TableRow key={idx}>
                      <TableCell className="text-xs text-gray-500">{idx + 1}</TableCell>
                      <TableCell className="text-xs font-mono max-w-[500px] truncate" title={rule.rule}>
                        {rule.rule}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// 规则筛选阶段预览（v2.0 合并原 filtering_rules + evaluating_rules）
// =============================================================================

function RuleFilteringPreview({ data }: { data: Record<string, any> }) {
  // 支持新旧两种数据格式
  // 新格式（合并后）：generated_count, direction_filtered_count, after_count, filter_summary
  // 旧格式：before_count, after_count
  const generatedCount = data.generated_count ?? data.before_count ?? data.beforeCount ?? 0;
  const monotonicityFilteredCount = data.direction_filtered_count ?? generatedCount;
  const afterCount = data.after_count ?? data.afterCount ?? 0;
  const filterCriteria = data.filter_criteria ?? data.filterCriteria ?? {};
  const filterSummary = data.filter_summary ?? {};
  
  // 全量规则筛选状态（用于CSV下载）
  const allRulesWithStatus: Array<Record<string, any>> = data.all_rules_with_status ?? [];
  
  // 有效规则预览（按Lift降序排列）
  const validRules = allRulesWithStatus
    .filter((r: Record<string, any>) => r.is_valid === true)
    .sort((a: Record<string, any>, b: Record<string, any>) => (b.lift ?? 0) - (a.lift ?? 0))
    .slice(0, 5);
  
  // 计算过滤率
  const totalFilterRate = generatedCount > 0
    ? ((generatedCount - afterCount) / generatedCount * 100).toFixed(1)
    : "0";

  // 下载全量规则筛选状态为CSV（按Lift降序排列）
  const handleDownloadFilteringStatus = () => {
    if (allRulesWithStatus.length === 0) return;
    
    // 按Lift降序排列
    const sortedRules = [...allRulesWithStatus].sort((a, b) => (b.lift ?? 0) - (a.lift ?? 0));
    
    // CSV列定义（中文表头，体现支持度/置信度等价关系）
    // v2.3: 添加淘汰原因和排名列
    const columns = [
      { key: 'rule', header: '规则表达式' },
      { key: 'hit_rate', header: '命中率(支持度)' },
      { key: 'bad_rate', header: '坏账率(置信度)' },
      { key: 'lift', header: 'Lift提升度' },
      { key: 'recall', header: '召回率' },
      { key: 'direction_valid', header: '单调性校验通过' },
      { key: 'hit_rate_valid', header: '命中率阈值通过' },
      { key: 'lift_valid', header: 'Lift阈值通过' },
      { key: 'is_valid', header: '最终有效' },
      { key: 'filter_reason', header: '筛选过滤原因' },
      { key: 'is_optimal', header: '入选最优规则集' },
      { key: 'rejection_reason', header: '最优选择淘汰原因' },
      { key: 'rejection_rank', header: '坏账率排名' },
    ];
    
    // 添加序号列到表头
    const headers = ['序号', ...columns.map(c => c.header)];
    const csvContent = [
      // 添加筛选条件说明行
      `# 筛选条件: 最小Lift阈值=${filterCriteria.min_lift ?? 'N/A'}, 最大命中率=${filterCriteria.max_hit_rate ?? 'N/A'}`,
      `# 统计: 生成${generatedCount}条 → 单调性校验后${monotonicityFilteredCount}条 → 最终有效${afterCount}条`,
      `# 排序: 按Lift降序`,
      '',
      headers.join(','),
      ...sortedRules.map((row: Record<string, any>, index: number) => 
        // 序号从1开始
        [index + 1, ...columns.map(col => {
          const val = row[col.key];
          // 处理布尔值
          if (typeof val === 'boolean') {
            return val ? '是' : '否';
          }
          // 处理null/undefined
          if (val === null || val === undefined) {
            return '';
          }
          // 处理数值（保留4位小数）
          if (typeof val === 'number') {
            return val.toFixed(4);
          }
          // 处理包含逗号或引号的字符串
          if (typeof val === 'string' && (val.includes(',') || val.includes('"') || val.includes('\n'))) {
            return `"${val.replace(/"/g, '""')}"`;
          }
          return val;
        })].join(',')
      )
    ].join('\n');
    
    const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `rule_filtering_status_${new Date().toISOString().slice(0,10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-4">
      {/* 筛选统计 */}
      <div className="grid grid-cols-3 gap-3">
        <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
          <div className="text-xs text-gray-500">生成规则数</div>
          <div className="text-2xl font-bold text-blue-600">{generatedCount.toLocaleString()}</div>
        </div>
        {filterSummary.direction_removed !== undefined && (
          <div className="p-3 bg-amber-50 dark:bg-amber-900/20 rounded-lg">
            <div className="text-xs text-gray-500">单调性校验后</div>
            <div className="text-2xl font-bold text-amber-600">{monotonicityFilteredCount.toLocaleString()}</div>
            <div className="text-[10px] text-gray-400">移除: {filterSummary.direction_removed}</div>
          </div>
        )}
        <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
          <div className="text-xs text-gray-500">有效规则数</div>
          <div className="text-2xl font-bold text-green-600">{afterCount.toLocaleString()}</div>
          <div className="text-[10px] text-gray-400">总过滤率: {totalFilterRate}%</div>
        </div>
      </div>

      {/* 筛选条件 */}
      {(filterCriteria.max_hit_rate !== undefined || filterCriteria.min_lift !== undefined) && (
        <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
          <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">筛选条件</div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            {filterCriteria.min_lift !== undefined && (
              <div className="flex justify-between">
                <span className="text-gray-500">最小Lift阈值:</span>
                <span className="font-medium">{filterCriteria.min_lift}</span>
              </div>
            )}
            {filterCriteria.max_hit_rate !== undefined && (
              <div className="flex justify-between">
                <span className="text-gray-500">最大命中率:</span>
                <span className="font-medium">{(filterCriteria.max_hit_rate * 100).toFixed(1)}%</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 过滤明细（如果有） */}
      {filterSummary.total_removed !== undefined && (
        <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
          <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">筛选明细</div>
          <div className="space-y-1 text-xs">
            {filterSummary.direction_removed !== undefined && (
              <div className="flex justify-between">
                <span className="text-gray-500">单调性校验移除:</span>
                <span className="font-medium text-amber-600">{filterSummary.direction_removed}</span>
              </div>
            )}
            {filterSummary.bad_rate_zero_removed !== undefined && filterSummary.bad_rate_zero_removed > 0 && (
              <div className="flex justify-between">
                <span className="text-gray-500">坏账率为0移除:</span>
                <span className="font-medium text-purple-600">{filterSummary.bad_rate_zero_removed}</span>
              </div>
            )}
            {filterSummary.lift_removed !== undefined && (
              <div className="flex justify-between">
                <span className="text-gray-500">最小Lift阈值移除:</span>
                <span className="font-medium text-red-600">{filterSummary.lift_removed}</span>
              </div>
            )}
            {filterSummary.hit_rate_removed !== undefined && (
              <div className="flex justify-between">
                <span className="text-gray-500">最大命中率移除:</span>
                <span className="font-medium text-orange-600">{filterSummary.hit_rate_removed}</span>
              </div>
            )}
            <div className="flex justify-between border-t pt-1 mt-1">
              <span className="text-gray-500 font-medium">总移除:</span>
              <span className="font-bold">{filterSummary.total_removed}</span>
            </div>
          </div>
        </div>
      )}

      {/* 旧格式兼容：过滤原因统计 */}
      {data.filter_reason && Object.keys(data.filter_reason).length > 0 && (
        <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
          <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">过滤原因统计</div>
          <div className="space-y-1 text-xs">
            {Object.entries(data.filter_reason).map(([reason, count]) => (
              <div key={reason} className="flex justify-between">
                <span className="text-gray-500">{reason}:</span>
                <span className="font-medium">{String(count)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 有效规则预览（按Lift降序） */}
      {validRules.length > 0 && (
        <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
          <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Top {validRules.length} 有效规则 <span className="text-[10px] text-gray-400 font-normal">(按Lift降序)</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700">
                  <th className="text-left py-1 px-2 text-gray-500 font-medium">#</th>
                  <th className="text-left py-1 px-2 text-gray-500 font-medium">规则</th>
                  <th className="text-right py-1 px-2 text-gray-500 font-medium">命中率</th>
                  <th className="text-right py-1 px-2 text-gray-500 font-medium">Lift</th>
                </tr>
              </thead>
              <tbody>
                {validRules.map((rule: Record<string, any>, index: number) => (
                  <tr key={index} className="border-b border-gray-100 dark:border-gray-800 last:border-0">
                    <td className="py-1.5 px-2 text-gray-400">{index + 1}</td>
                    <td className="py-1.5 px-2 text-gray-700 dark:text-gray-300 max-w-[200px] truncate" title={rule.rule}>
                      {rule.rule}
                    </td>
                    <td className="py-1.5 px-2 text-right text-blue-600">
                      {((rule.hit_rate ?? 0) * 100).toFixed(2)}%
                    </td>
                    <td className="py-1.5 px-2 text-right text-green-600">
                      {rule.lift?.toFixed(2) ?? '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 下载全量规则筛选状态 */}
      {allRulesWithStatus.length > 0 && (
        <div className="flex justify-end">
          <Button
            variant="outline"
            size="sm"
            className="h-7 px-3 text-xs"
            onClick={handleDownloadFilteringStatus}
          >
            <Download className="h-3 w-3 mr-1" />
            下载筛选明细 ({allRulesWithStatus.length}条)
          </Button>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// 最优规则展示组件（支持Top 5 + 展开全部）
// =============================================================================

interface OptimalRule {
  rule: string;
  hit_rate: number;
  bad_rate?: number;
  lift: number;
  recall?: number;
  cumulative_hit_rate?: number;
  cumulative_recall?: number;
  cumulative_lift?: number;
}

function OptimalRulesSection({ rules }: { rules: OptimalRule[] }) {
  const [expanded, setExpanded] = useState(false);
  const TOP_N = 5;
  
  const displayRules = expanded ? rules : rules.slice(0, TOP_N);
  const hasMore = rules.length > TOP_N;
  
  return (
    <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
      <div className="flex items-center justify-between mb-2">
        <div className="text-sm font-medium text-gray-700 dark:text-gray-300">
          最优规则
          <span className="ml-2 text-xs text-gray-500 font-normal">
            (共{rules.length}条{!expanded && hasMore ? `，显示前${TOP_N}条` : ''})
          </span>
        </div>
        {hasMore && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-xs text-blue-500 hover:text-blue-600 flex items-center gap-1"
          >
            {expanded ? '收起' : `展开全部 (${rules.length}条)`}
            <ChevronDown className={cn(
              "h-3 w-3 transition-transform",
              expanded && "rotate-180"
            )} />
          </button>
        )}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-gray-200 dark:border-gray-700">
              <th className="text-left py-1 px-2 text-gray-500 font-medium">#</th>
              <th className="text-left py-1 px-2 text-gray-500 font-medium">规则</th>
              <th className="text-right py-1 px-2 text-gray-500 font-medium">命中率</th>
              <th className="text-right py-1 px-2 text-gray-500 font-medium">Lift</th>
            </tr>
          </thead>
          <tbody>
            {displayRules.map((rule, index) => (
              <tr key={index} className="border-b border-gray-100 dark:border-gray-800 last:border-0">
                <td className="py-1.5 px-2 text-gray-400">{index + 1}</td>
                <td className="py-1.5 px-2 text-gray-700 dark:text-gray-300 max-w-[200px] truncate" title={rule.rule}>
                  {rule.rule}
                </td>
                <td className="py-1.5 px-2 text-right text-blue-600">
                  {(rule.hit_rate * 100).toFixed(2)}%
                </td>
                <td className="py-1.5 px-2 text-right text-green-600">
                  {rule.lift?.toFixed(2) ?? '-'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// =============================================================================
// 被淘汰规则统计组件（最优选择阶段专用）
// =============================================================================

interface RejectedRulesStats {
  total_rejected: number;
  reason_distribution: Record<string, number>;
  top_rejected_rules: Array<{
    rule: string;
    hit_rate: number;
    bad_rate: number;
    lift: number;
    reason: string;
    rank?: number;  // v2.3: 新增排名信息
  }>;
}

function RejectedRulesSection({ stats }: { stats: RejectedRulesStats }) {
  const [expanded, setExpanded] = useState(false);
  
  // v2.3: 细化淘汰原因标签映射
  const reasonLabels: Record<string, string> = {
    // 通用原因
    "坏账率为0": "坏账率为0（无效规则）",
    "命中率达上限": "累计命中率达上限",
    "召回率目标已达成": "召回率目标已达成",
    "目标坏账率已达成": "目标坏账率已达成",
    // 贪婪模式特有
    "样本被消耗（贪婪模式）": "样本被消耗（贪婪模式）",
    // 兼容旧版本
    "命中率限制": "累计命中率达上限",
    "坏账率限制": "累计坏账率超限（已废弃）",
    "未被选中": "未被选中",
  };
  
  // 格式化原因显示（支持动态排名显示如"排序靠后（坏账率第X名）"）
  const formatReason = (reason: string): string => {
    if (reason.startsWith("排序靠后")) {
      return reason;  // 已包含排名信息，直接显示
    }
    return reasonLabels[reason] || reason;
  };
  
  return (
    <div className="p-3 bg-orange-50 dark:bg-orange-900/20 rounded-lg border border-orange-200 dark:border-orange-800">
      <div 
        className="flex items-center justify-between cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="text-sm font-medium text-orange-700 dark:text-orange-300">
          被淘汰规则 ({stats.total_rejected}条)
        </div>
        <ChevronDown className={cn(
          "h-4 w-4 text-orange-500 transition-transform",
          expanded && "rotate-180"
        )} />
      </div>
      
      {/* 淘汰原因分布 */}
      <div className="mt-2 flex flex-wrap gap-2 text-xs">
        {Object.entries(stats.reason_distribution).map(([reason, count]) => (
          <span 
            key={reason}
            className="px-2 py-0.5 bg-orange-100 dark:bg-orange-800/30 text-orange-600 dark:text-orange-400 rounded"
          >
            {formatReason(reason)}: {count}条
          </span>
        ))}
      </div>
      
      {/* 展开后显示全部淘汰规则（限定高度+滚动条） */}
      {expanded && stats.top_rejected_rules.length > 0 && (
        <div className="mt-3">
          <div className="text-xs text-gray-500 mb-1">
            全部被淘汰规则（共{stats.top_rejected_rules.length}条）：
          </div>
          <div className="max-h-[300px] overflow-y-auto overflow-x-auto border border-orange-200 dark:border-orange-700 rounded">
            <table className="w-full text-xs">
              <thead className="sticky top-0 bg-orange-50 dark:bg-orange-900/30">
                <tr className="border-b border-orange-200 dark:border-orange-700">
                  <th className="text-left py-1 px-2 text-gray-500 font-medium">#</th>
                  <th className="text-left py-1 px-2 text-gray-500 font-medium">规则</th>
                  <th className="text-right py-1 px-2 text-gray-500 font-medium">命中率</th>
                  <th className="text-right py-1 px-2 text-gray-500 font-medium">坏账率</th>
                  <th className="text-right py-1 px-2 text-gray-500 font-medium">Lift</th>
                  <th className="text-left py-1 px-2 text-gray-500 font-medium">淘汰原因</th>
                </tr>
              </thead>
              <tbody>
                {stats.top_rejected_rules.map((rule, index) => (
                  <tr key={index} className="border-b border-orange-100 dark:border-orange-800 last:border-0">
                    <td className="py-1.5 px-2 text-gray-400">{index + 1}</td>
                    <td className="py-1.5 px-2 text-gray-700 dark:text-gray-300 max-w-[180px] truncate" title={rule.rule}>
                      {rule.rule}
                    </td>
                    <td className="py-1.5 px-2 text-right text-blue-600">
                      {(rule.hit_rate * 100).toFixed(2)}%
                    </td>
                    <td className="py-1.5 px-2 text-right text-orange-600">
                      {(rule.bad_rate * 100).toFixed(2)}%
                    </td>
                    <td className="py-1.5 px-2 text-right text-gray-600">
                      {rule.lift?.toFixed(2) ?? '-'}
                    </td>
                    <td className="py-1.5 px-2 text-gray-500">
                      {formatReason(rule.reason)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// 最优规则选择阶段预览（v2.0 优化版 - 参考规则筛选阶段设计）
// =============================================================================

function RuleSelectionPreview({ data }: { data: Record<string, any> }) {
  // 支持多种字段名：after_count (后端) / selected_count / selectedCount / optimal_rules.length
  const selectedCount = data.after_count ?? data.selected_count ?? data.selectedCount ?? data.optimal_rules?.length ?? 0;
  // 支持多种字段名：before_count (后端) / candidate_count / candidateCount
  const candidateCount = data.before_count ?? data.candidate_count ?? data.candidateCount ?? 0;
  
  // 选择参数
  const maxHitRate = data.max_hit_rate;
  const selectionMode = data.selection_mode;
  const allowOverlap = data.allow_overlap;  // v2.1: 规则重叠参数
  const riskTargets = data.risk_targets ?? {};
  
  // v2.5: 规则集汇总指标
  const rulesetSummary = data.ruleset_summary ?? {};
  
  // Top规则预览
  const topRules: Array<Record<string, any>> = data.top_rules ?? [];
  
  // 全量最优规则（用于CSV下载）
  const allOptimalRules: Array<Record<string, any>> = data.all_optimal_rules ?? [];
  
  // 计算选择率
  const selectionRate = candidateCount > 0
    ? ((selectedCount / candidateCount) * 100).toFixed(1)
    : "0";

  // 下载全量最优规则为CSV
  const handleDownloadOptimalRules = () => {
    if (allOptimalRules.length === 0) return;
    
    // CSV列定义（移除精确率，与坏账率相同）
    const columns = [
      { key: 'rule', header: '规则表达式' },
      { key: 'hit_rate', header: '命中率' },
      { key: 'bad_rate', header: '坏账率' },
      { key: 'lift', header: 'Lift提升度' },
      { key: 'recall', header: '召回率' },
      { key: 'cumulative_hit_rate', header: '累计命中率' },
      { key: 'cumulative_recall', header: '累计召回率' },
      { key: 'cumulative_lift', header: '累计提升度' },
    ];
    
    // 添加序号列到表头
    const headers = ['序号', ...columns.map(c => c.header)];
    const csvContent = [
      // 添加选择参数说明行
      `# 选择模式: ${selectionMode ?? 'N/A'}`,
      `# 最大命中率（规则集）: ${maxHitRate !== undefined ? (maxHitRate * 100).toFixed(1) + '%' : 'N/A'}`,
      `# 风险目标: 最低召回率（规则集）=${riskTargets.min_recall_ruleset ?? 'N/A'}, 最低坏账率（规则集）=${riskTargets.min_bad_rate_ruleset ?? 'N/A'}, 最高坏账率（规则集）=${riskTargets.max_bad_rate_ruleset ?? 'N/A'}, 最低Lift（规则集）=${riskTargets.min_lift_ruleset ?? 'N/A'}`,
      `# 统计: 候选${candidateCount}条 → 最优${selectedCount}条 (选择率: ${selectionRate}%)`,
      '',
      headers.join(','),
      ...allOptimalRules.map((row: Record<string, any>, index: number) => 
        [index + 1, ...columns.map(col => {
          const val = row[col.key];
          if (val === null || val === undefined) return '';
          if (typeof val === 'number') return val.toFixed(4);
          if (typeof val === 'string' && (val.includes(',') || val.includes('"') || val.includes('\n'))) {
            return `"${val.replace(/"/g, '""')}"`;
          }
          return val;
        })].join(',')
      )
    ].join('\n');
    
    const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `optimal_rules_${new Date().toISOString().slice(0,10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-4">
      {/* 选择统计 */}
      <div className="grid grid-cols-3 gap-3">
        <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
          <div className="text-xs text-gray-500">候选规则数</div>
          <div className="text-2xl font-bold text-blue-600">{candidateCount.toLocaleString()}</div>
        </div>
        <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
          <div className="text-xs text-gray-500">最优规则数</div>
          <div className="text-2xl font-bold text-green-600">{selectedCount}</div>
        </div>
        <div className="p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
          <div className="text-xs text-gray-500">选择率</div>
          <div className="text-2xl font-bold text-purple-600">{selectionRate}%</div>
        </div>
      </div>

      {/* 选择参数 */}
      {(maxHitRate !== undefined || selectionMode || allowOverlap !== undefined ||
        riskTargets.min_recall_ruleset != null || riskTargets.min_bad_rate_ruleset != null || 
        riskTargets.target_bad_rate_ruleset != null || riskTargets.min_lift_ruleset != null) && (
        <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
          <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">选择参数</div>
          <div className="flex flex-wrap gap-4 text-xs">
            {allowOverlap !== undefined && (
              <div className="flex items-center gap-1">
                <span className="text-gray-500">选择模式:</span>
                <span className="font-medium">{allowOverlap ? "允许重叠（独立选择）" : "贪婪算法（不允许重叠）"}</span>
              </div>
            )}
            {maxHitRate !== undefined && (
              <div className="flex items-center gap-1">
                <span className="text-gray-500">最大命中率（规则集）:</span>
                <span className="font-medium">{(maxHitRate * 100).toFixed(1)}%</span>
              </div>
            )}
            {/* 风险目标参数 - 始终展示，未设置显示"未设置" */}
            <div className="flex items-center gap-1">
              <span className="text-gray-500">最低召回率:</span>
              <span className={`font-medium ${riskTargets.min_recall_ruleset == null ? 'text-gray-400' : ''}`}>
                {riskTargets.min_recall_ruleset != null ? `${(riskTargets.min_recall_ruleset * 100).toFixed(1)}%` : '未设置'}
              </span>
            </div>
            <div className="flex items-center gap-1">
              <span className="text-gray-500">最低坏账率:</span>
              <span className={`font-medium ${riskTargets.min_bad_rate_ruleset == null ? 'text-gray-400' : ''}`}>
                {riskTargets.min_bad_rate_ruleset != null ? `${(riskTargets.min_bad_rate_ruleset * 100).toFixed(1)}%` : '未设置'}
              </span>
            </div>
            <div className="flex items-center gap-1">
              <span className="text-gray-500">目标坏账率:</span>
              <span className={`font-medium ${riskTargets.target_bad_rate_ruleset == null ? 'text-gray-400' : ''}`}>
                {riskTargets.target_bad_rate_ruleset != null ? `${(riskTargets.target_bad_rate_ruleset * 100).toFixed(1)}%` : '未设置'}
              </span>
            </div>
            <div className="flex items-center gap-1">
              <span className="text-gray-500">最低提升度:</span>
              <span className={`font-medium ${riskTargets.min_lift_ruleset == null ? 'text-gray-400' : ''}`}>
                {riskTargets.min_lift_ruleset != null ? riskTargets.min_lift_ruleset : '未设置'}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* v2.5: 规则集汇总指标（淘汰原因参照值） */}
      {(rulesetSummary.cumulative_hit_rate !== undefined || 
        rulesetSummary.cumulative_recall !== undefined ||
        rulesetSummary.cumulative_lift !== undefined) && (
        <div className="p-3 bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-indigo-900/20 dark:to-purple-900/20 rounded-lg border border-indigo-200 dark:border-indigo-800">
          <div className="text-sm font-medium text-indigo-700 dark:text-indigo-300 mb-2">规则集汇总指标</div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
            {/* 累计命中率 vs 最大命中率上限 */}
            {rulesetSummary.cumulative_hit_rate !== undefined && (
              <div className="bg-white/60 dark:bg-gray-800/60 rounded p-2">
                <div className="text-gray-500 mb-1">累计命中率</div>
                <div className="text-lg font-bold text-indigo-600">
                  {(rulesetSummary.cumulative_hit_rate * 100).toFixed(2)}%
                </div>
                {maxHitRate !== undefined && (
                  <div className="text-gray-400 text-[10px]">
                    上限: {(maxHitRate * 100).toFixed(1)}% 
                    <span className={`ml-1 ${rulesetSummary.cumulative_hit_rate / maxHitRate >= 0.8 ? 'text-orange-500' : 'text-green-500'}`}>
                      (已用{((rulesetSummary.cumulative_hit_rate / maxHitRate) * 100).toFixed(0)}%)
                    </span>
                  </div>
                )}
              </div>
            )}
            {/* 累计召回率 vs 最低召回率目标 */}
            {rulesetSummary.cumulative_recall !== undefined && (
              <div className="bg-white/60 dark:bg-gray-800/60 rounded p-2">
                <div className="text-gray-500 mb-1">累计召回率</div>
                <div className="text-lg font-bold text-purple-600">
                  {(rulesetSummary.cumulative_recall * 100).toFixed(2)}%
                </div>
                {riskTargets.min_recall_ruleset != null && (
                  <div className="text-gray-400 text-[10px]">
                    目标: ≥{(riskTargets.min_recall_ruleset * 100).toFixed(1)}%
                    <span className={`ml-1 ${rulesetSummary.cumulative_recall >= riskTargets.min_recall_ruleset ? 'text-green-500' : 'text-orange-500'}`}>
                      ({rulesetSummary.cumulative_recall >= riskTargets.min_recall_ruleset ? '已达成' : '未达成'})
                    </span>
                  </div>
                )}
              </div>
            )}
            {/* 累计提升度 vs 最低提升度目标 */}
            {rulesetSummary.cumulative_lift !== undefined && rulesetSummary.cumulative_lift > 0 && (
              <div className="bg-white/60 dark:bg-gray-800/60 rounded p-2">
                <div className="text-gray-500 mb-1">累计提升度</div>
                <div className="text-lg font-bold text-green-600">
                  {rulesetSummary.cumulative_lift.toFixed(2)}x
                </div>
                {riskTargets.min_lift_ruleset != null && (
                  <div className="text-gray-400 text-[10px]">
                    目标: ≥{riskTargets.min_lift_ruleset}x
                    <span className={`ml-1 ${rulesetSummary.cumulative_lift >= riskTargets.min_lift_ruleset ? 'text-green-500' : 'text-orange-500'}`}>
                      ({rulesetSummary.cumulative_lift >= riskTargets.min_lift_ruleset ? '已达成' : '未达成'})
                    </span>
                  </div>
                )}
              </div>
            )}
            {/* 策略应用后全样本坏账率 - 始终显示，有目标时才显示对比 */}
            {rulesetSummary.estimated_overall_bad_rate !== undefined && rulesetSummary.estimated_overall_bad_rate !== null && (
              <div className="bg-white/60 dark:bg-gray-800/60 rounded p-2">
                <div className="text-gray-500 mb-1">全样本坏账率（策略后）</div>
                <div className="text-lg font-bold text-orange-600">
                  {(rulesetSummary.estimated_overall_bad_rate * 100).toFixed(2)}%
                </div>
                {riskTargets.target_bad_rate_ruleset != null && (
                  <div className="text-gray-400 text-[10px]">
                    原始: {rulesetSummary.original_bad_rate != null ? (rulesetSummary.original_bad_rate * 100).toFixed(2) + '%' : '-'} → 
                    目标: ≤{(riskTargets.target_bad_rate_ruleset * 100).toFixed(1)}%
                    <span className={`ml-1 ${rulesetSummary.estimated_overall_bad_rate <= riskTargets.target_bad_rate_ruleset ? 'text-green-500' : 'text-orange-500'}`}>
                      ({rulesetSummary.estimated_overall_bad_rate <= riskTargets.target_bad_rate_ruleset ? '已达成' : '未达成'})
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Top规则预览 - 支持展开/收起 */}
      {allOptimalRules.length > 0 && (
        <OptimalRulesSection rules={allOptimalRules} />
      )}

      {/* 被淘汰规则统计 */}
      {data.rejected_rules_stats && data.rejected_rules_stats.total_rejected > 0 && (
        <RejectedRulesSection stats={data.rejected_rules_stats} />
      )}

      {/* 下载全量最优规则 */}
      {allOptimalRules.length > 0 && (
        <div className="flex justify-end">
          <Button
            variant="outline"
            size="sm"
            className="h-7 px-3 text-xs"
            onClick={handleDownloadOptimalRules}
          >
            <Download className="h-3 w-3 mr-1" />
            下载最优规则 ({allOptimalRules.length}条)
          </Button>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// 模型评估阶段预览（评分卡任务专用）
// =============================================================================

function ModelEvaluationPreview({ data }: { data: Record<string, any> }) {
  const trainMetrics = data.train_metrics || {};
  const testMetrics = data.test_metrics || {};
  const ootMetrics = data.oot_metrics;  // OOT验证集指标（可能不存在）
  const psiResult = data.psi_result;
  const scoreDistribution = data.score_distribution;
  
  // 行业标准：优先显示OOT指标（更能反映真实业务表现），无OOT时显示测试集指标
  const primaryMetrics = ootMetrics || testMetrics;
  const primaryLabel = ootMetrics ? 'OOT' : '测试集';
  
  // 状态：数据集选择、视图选择
  // 默认选中的数据集：有OOT优先选OOT，否则选测试集
  const [selectedDataset, setSelectedDataset] = useState<'train' | 'test' | 'oot'>(ootMetrics ? 'oot' : 'test');
  const [analysisView, setAnalysisView] = useState<'ranking' | 'distribution'>('ranking');

  // Safe number formatting helper
  const formatNumber = (value: any, digits: number = 4): string => {
    if (value === null || value === undefined) return "-";
    const num = Number(value);
    return isNaN(num) ? "-" : num.toFixed(digits);
  };
  
  // 评估等级辅助函数（与ScorecardResults保持一致）
  const getKSLevel = (ks: number): { label: string; colorClass: string } => {
    if (ks >= 0.4) return { label: '优秀', colorClass: 'text-green-600 dark:text-green-400' };
    if (ks >= 0.3) return { label: '良好', colorClass: 'text-blue-600 dark:text-blue-400' };
    if (ks >= 0.2) return { label: '可用', colorClass: 'text-yellow-600 dark:text-yellow-400' };
    return { label: '较差', colorClass: 'text-red-600 dark:text-red-400' };
  };
  
  const getAUCLevel = (auc: number): { label: string; colorClass: string } => {
    if (auc >= 0.8) return { label: '优秀', colorClass: 'text-green-600 dark:text-green-400' };
    if (auc >= 0.75) return { label: '良好', colorClass: 'text-blue-600 dark:text-blue-400' };
    if (auc >= 0.7) return { label: '可用', colorClass: 'text-yellow-600 dark:text-yellow-400' };
    return { label: '较差', colorClass: 'text-red-600 dark:text-red-400' };
  };
  
  const getGiniLevel = (gini: number): { label: string; colorClass: string } => {
    if (gini >= 0.6) return { label: '优秀', colorClass: 'text-green-600 dark:text-green-400' };
    if (gini >= 0.5) return { label: '良好', colorClass: 'text-blue-600 dark:text-blue-400' };
    if (gini >= 0.4) return { label: '可用', colorClass: 'text-yellow-600 dark:text-yellow-400' };
    return { label: '较差', colorClass: 'text-red-600 dark:text-red-400' };
  };
  
  // 确定可用数据集
  const availableDatasets = React.useMemo(() => {
    const datasets: { key: 'train' | 'test' | 'oot'; label: string }[] = [];
    if (scoreDistribution?.train) datasets.push({ key: 'train', label: '训练集' });
    if (scoreDistribution?.test) datasets.push({ key: 'test', label: '测试集' });
    if (scoreDistribution?.oot) datasets.push({ key: 'oot', label: 'OOT验证集' });
    return datasets;
  }, [scoreDistribution]);
  
  // 获取当前数据集的分布数据
  const currentDistribution = scoreDistribution?.[selectedDataset];
  
  const currentBins = React.useMemo(() => {
    if (!currentDistribution) return null;
    return analysisView === 'ranking' 
      ? currentDistribution.ranking_analysis?.bins 
      : currentDistribution.distribution_view?.bins;
  }, [currentDistribution, analysisView]);
  
  // 整体坏样本率（用于高亮显示）
  const overallBadRate = currentDistribution?.summary?.overall_bad_rate || 0;
  
  // CSV下载功能
  const handleDownloadCSV = () => {
    if (!currentBins || currentBins.length === 0) return;
    
    // 数据集中文名称映射
    const datasetLabels: Record<string, string> = { train: '训练集', test: '测试集', oot: 'OOT验证集' };
    const datasetLabel = datasetLabels[selectedDataset] || selectedDataset;
    const analysisLabel = analysisView === 'ranking' ? '排序性分析' : '评分分布';
    const binMethodLabel = analysisView === 'ranking' 
      ? `等频分箱（${currentDistribution?.ranking_analysis?.n_bins || 10}组）`
      : `等宽分箱（${currentDistribution?.distribution_view?.n_bins || 8}组）`;
    
    // 汇总信息行（注意：CSV中不能使用千位分隔符，否则会被当作列分隔）
    const summary = currentDistribution?.summary;
    const summaryRows = [
      `分析类型,${analysisLabel}`,
      `数据集,${datasetLabel}`,
      `分箱方法,${binMethodLabel}`,
      `总样本,${summary?.total_samples || '-'}`,
      `坏样本率,${summary?.overall_bad_rate?.toFixed(2) || '-'}%`,
      `好样本均值,${summary?.good_mean?.toFixed(1) || '-'}`,
      `坏样本均值,${summary?.bad_mean?.toFixed(1) || '-'}`,
      '',  // 空行分隔
    ];
    
    // 表头（增加样本占比列）
    const headers = ['序号', '分数区间', '样本数', '样本占比', '好样本', '坏样本', '坏样本率', 'Lift', '累计坏样本率'];
    
    // CSV转义函数：如果字段包含逗号、双引号或换行符，用双引号包裹并转义内部双引号
    const escapeCSV = (value: any): string => {
      const str = String(value ?? '-');
      if (str.includes(',') || str.includes('"') || str.includes('\n')) {
        return `"${str.replace(/"/g, '""')}"`;
      }
      return str;
    };
    
    const rows = currentBins.map((bin: any, idx: number) => [
      idx + 1,
      escapeCSV(bin.bin || bin.bin_label || '-'),  // 分数区间可能含逗号，需转义
      bin.total,
      `${(bin.pct_total || 0).toFixed(2)}%`,  // 样本占比
      bin.good,
      bin.bad,
      `${(bin.bad_rate || 0).toFixed(2)}%`,
      (bin.lift || 0).toFixed(2),
      `${(bin.cum_bad_rate || 0).toFixed(2)}%`
    ]);
    
    const csv = [...summaryRows, headers.join(','), ...rows.map((r: any) => r.join(','))].join('\n');
    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' });
    // 文件名格式：分析类型_数据集类型.csv
    const filename = `${analysisLabel}_${datasetLabel}.csv`;
    
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    link.click();
    URL.revokeObjectURL(link.href);
  };

  return (
    <div className="space-y-4">
      {/* 核心指标对比 - 4列布局（包含PSI） */}
      <div className={cn("grid gap-3", psiResult ? "grid-cols-4" : "grid-cols-3")}>
        <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-500">AUC</span>
            {primaryMetrics.auc != null && trainMetrics.auc != null && (
              Number(primaryMetrics.auc) < Number(trainMetrics.auc) * 0.95 ? (
                <TrendingDown className="h-3 w-3 text-red-500" />
              ) : (
                <TrendingUp className="h-3 w-3 text-green-500" />
              )
            )}
          </div>
          <div className="text-lg font-bold text-blue-600">{formatNumber(primaryMetrics.auc)}</div>
          {primaryMetrics.auc != null && (
            <div className={cn("text-[10px]", getAUCLevel(Number(primaryMetrics.auc)).colorClass)}>
              {getAUCLevel(Number(primaryMetrics.auc)).label}
            </div>
          )}
          <div className="text-[10px] text-gray-400">训练: {formatNumber(trainMetrics.auc)}</div>
        </div>
        <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
          <div className="text-xs text-gray-500">KS</div>
          <div className="text-lg font-bold text-green-600">{formatNumber(primaryMetrics.ks)}</div>
          {primaryMetrics.ks != null && (
            <div className={cn("text-[10px]", getKSLevel(Number(primaryMetrics.ks)).colorClass)}>
              {getKSLevel(Number(primaryMetrics.ks)).label}
            </div>
          )}
          <div className="text-[10px] text-gray-400">训练: {formatNumber(trainMetrics.ks)}</div>
        </div>
        <div className="p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
          <div className="text-xs text-gray-500">Gini</div>
          <div className="text-lg font-bold text-purple-600">{formatNumber(primaryMetrics.gini)}</div>
          {primaryMetrics.gini != null && (
            <div className={cn("text-[10px]", getGiniLevel(Number(primaryMetrics.gini)).colorClass)}>
              {getGiniLevel(Number(primaryMetrics.gini)).label}
            </div>
          )}
          <div className="text-[10px] text-gray-400">训练: {formatNumber(trainMetrics.gini)}</div>
        </div>
        
        {/* PSI 稳定性指标 */}
        {psiResult && (
          <div className={cn(
            "p-3 rounded-lg",
            psiResult.level === "good" ? "bg-emerald-50 dark:bg-emerald-900/20" :
            psiResult.level === "warning" ? "bg-amber-50 dark:bg-amber-900/20" :
            "bg-red-50 dark:bg-red-900/20"
          )}>
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-500">PSI</span>
              {psiResult.level === "good" && <CheckCircle2 className="h-3 w-3 text-emerald-500" />}
              {psiResult.level === "warning" && <AlertTriangle className="h-3 w-3 text-amber-500" />}
              {psiResult.level === "bad" && <AlertTriangle className="h-3 w-3 text-red-500" />}
            </div>
            <div className={cn(
              "text-lg font-bold",
              psiResult.level === "good" ? "text-emerald-600" :
              psiResult.level === "warning" ? "text-amber-600" : "text-red-600"
            )}>
              {formatNumber(psiResult.value)}
            </div>
            <div className="text-[10px] text-gray-400">{psiResult.stability}</div>
            <div className="text-[10px] text-gray-400">{psiResult.comparison}</div>
          </div>
        )}
      </div>

      {/* 过拟合警告 */}
      {data.overfit_warning && (
        <div className="flex items-center gap-2 p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg text-yellow-700 dark:text-yellow-400">
          <AlertTriangle className="h-4 w-4" />
          <span className="text-sm">{data.overfit_warning}</span>
        </div>
      )}

      {/* CSI 特征稳定性报告 */}
      {(() => {
        // 优先展示 OOT CSI（行业惯例），无 OOT 时展示 Test CSI
        const csiReport = data.csi_train_vs_oot || data.csi_train_vs_test;
        if (!csiReport || !csiReport.features || csiReport.features.length === 0) return null;

        return (
          <div className="space-y-2 border-t pt-3 mt-3">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-medium flex items-center gap-1.5">
                <CheckCircle2 className="h-3.5 w-3.5 text-blue-500" />
                CSI 特征稳定性（{csiReport.comparison}）
              </h4>
              <div className="flex items-center gap-3 text-[10px]">
                <span className="flex items-center gap-1">
                  <span className="inline-block w-1.5 h-1.5 rounded-full bg-green-500"></span>
                  稳定 {csiReport.summary.stable}
                </span>
                {csiReport.summary.slight_change > 0 && (
                  <span className="flex items-center gap-1">
                    <span className="inline-block w-1.5 h-1.5 rounded-full bg-yellow-500"></span>
                    轻微 {csiReport.summary.slight_change}
                  </span>
                )}
                {csiReport.summary.significant_change > 0 && (
                  <span className="flex items-center gap-1">
                    <span className="inline-block w-1.5 h-1.5 rounded-full bg-red-500"></span>
                    显著 {csiReport.summary.significant_change}
                  </span>
                )}
              </div>
            </div>
            <div className="max-h-[200px] overflow-auto">
              <table className="w-full text-xs">
                <thead className="sticky top-0 bg-background">
                  <tr className="border-b text-gray-500">
                    <th className="text-left py-1 px-1.5 font-medium">特征</th>
                    <th className="text-right py-1 px-1.5 font-medium">CSI</th>
                    <th className="text-center py-1 px-1.5 font-medium">状态</th>
                  </tr>
                </thead>
                <tbody>
                  {csiReport.features.map((feat: any, idx: number) => (
                    <tr key={idx} className="border-b border-dashed last:border-0">
                      <td className="py-1 px-1.5 font-mono text-[11px]">{feat.feature}</td>
                      <td className="text-right py-1 px-1.5 font-mono text-[11px]">{feat.csi.toFixed(4)}</td>
                      <td className="text-center py-1 px-1.5">
                        <span className={cn(
                          "inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] font-medium",
                          feat.level === 'good'
                            ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                            : feat.level === 'warning'
                              ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400"
                              : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                        )}>
                          {feat.stability}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        );
      })()}
      
      {/* 排序性分析 / 评分分布（新增） */}
      {scoreDistribution && availableDatasets.length > 0 && (
        <div className="space-y-3 border-t pt-4 mt-4">
          {/* 控制栏 */}
          <div className="flex items-center justify-between flex-wrap gap-2">
            {/* 数据集切换 */}
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">数据集：</span>
              {availableDatasets.map(({ key, label }) => (
                <Button
                  key={key}
                  variant={selectedDataset === key ? "default" : "outline"}
                  size="sm"
                  className="h-6 px-2 text-xs"
                  onClick={() => setSelectedDataset(key)}
                >
                  {label}
                </Button>
              ))}
            </div>
            
            {/* 视图切换 + 下载 */}
            <div className="flex items-center gap-2">
              <Button
                variant={analysisView === 'ranking' ? "default" : "outline"}
                size="sm"
                className="h-6 text-xs"
                onClick={() => setAnalysisView('ranking')}
              >
                排序性分析
              </Button>
              <Button
                variant={analysisView === 'distribution' ? "default" : "outline"}
                size="sm"
                className="h-6 text-xs"
                onClick={() => setAnalysisView('distribution')}
              >
                评分分布
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="h-6 text-xs gap-1"
                onClick={handleDownloadCSV}
                disabled={!currentBins || currentBins.length === 0}
              >
                <Download className="h-3 w-3" />
                CSV
              </Button>
            </div>
          </div>
          
          {/* 视图说明 */}
          <div className="text-xs text-muted-foreground bg-blue-50 dark:bg-blue-900/20 px-3 py-1.5 rounded">
            {analysisView === 'ranking' ? (
              <span><strong>排序性分析</strong>：等频分箱（{currentDistribution?.ranking_analysis?.n_bins || 10}组），每组样本量相近，用于评估模型区分能力</span>
            ) : (
              <span><strong>评分分布</strong>：等宽分箱（{currentDistribution?.distribution_view?.n_bins || 8}组），区间宽度一致，用于查看评分分布情况</span>
            )}
          </div>
          
          {/* 汇总信息 */}
          {currentDistribution?.summary && (
            <div className="flex gap-4 text-xs text-muted-foreground flex-wrap">
              <span>总样本: <strong>{currentDistribution.summary.total_samples?.toLocaleString()}</strong></span>
              <span>坏样本率: <strong className="text-red-500">{currentDistribution.summary.overall_bad_rate?.toFixed(2)}%</strong></span>
              {currentDistribution.summary.good_mean != null && (
                <span>好样本均分: <strong className="text-green-600">{currentDistribution.summary.good_mean?.toFixed(1)}</strong></span>
              )}
              {currentDistribution.summary.bad_mean != null && (
                <span>坏样本均分: <strong className="text-red-500">{currentDistribution.summary.bad_mean?.toFixed(1)}</strong></span>
              )}
              {currentDistribution.summary.good_mean != null && currentDistribution.summary.bad_mean != null && (
                <span>分离度: <strong className="text-blue-600">{Math.abs(currentDistribution.summary.good_mean - currentDistribution.summary.bad_mean).toFixed(1)}</strong></span>
              )}
            </div>
          )}
          
          {/* 排序性分析摘要（仅在排序性分析视图时显示） */}
          {analysisView === 'ranking' && currentDistribution?.rank_ordering_analysis && (
            <div className="bg-muted/20 border rounded-md px-3 py-2">
              <div className="flex items-center gap-4 text-xs flex-wrap">
                {/* 单调性检验 */}
                <div className="flex items-center gap-1.5">
                  <span className="text-muted-foreground">单调性：</span>
                  {currentDistribution.rank_ordering_analysis.monotonicity?.is_monotonic ? (
                    <span className="flex items-center gap-1 text-green-600 font-medium">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      通过
                    </span>
                  ) : (
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <span className="flex items-center gap-1 text-amber-600 font-medium cursor-help">
                            <AlertTriangle className="h-3.5 w-3.5" />
                            不通过（{currentDistribution.rank_ordering_analysis.monotonicity?.violations?.length || 0}处违反）
                          </span>
                        </TooltipTrigger>
                        <TooltipContent className="max-w-xs">
                          <p className="text-xs mb-1">以下分段坏样本率未递减：</p>
                          <ul className="text-xs space-y-0.5">
                            {currentDistribution.rank_ordering_analysis.monotonicity?.violation_details?.map((v: any, i: number) => (
                              <li key={i} className="text-amber-200">
                                {v.curr_bin}: {v.prev_bad_rate?.toFixed(2)}% → {v.curr_bad_rate?.toFixed(2)}% (+{v.diff}%)
                              </li>
                            ))}
                          </ul>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  )}
                </div>
                
                {/* 首组Lift */}
                {currentDistribution.rank_ordering_analysis.lift_analysis?.first_decile_lift != null && (
                  <div className="flex items-center gap-1.5">
                    <span className="text-muted-foreground">首组Lift：</span>
                    <span className={cn(
                      "font-medium",
                      currentDistribution.rank_ordering_analysis.lift_analysis.first_decile_lift >= 2 
                        ? "text-green-600" 
                        : currentDistribution.rank_ordering_analysis.lift_analysis.first_decile_lift >= 1.5 
                          ? "text-blue-600" 
                          : "text-amber-600"
                    )}>
                      {currentDistribution.rank_ordering_analysis.lift_analysis.first_decile_lift.toFixed(2)}
                    </span>
                    <span className="text-muted-foreground">
                      （{currentDistribution.rank_ordering_analysis.lift_analysis.first_decile_bin}）
                    </span>
                  </div>
                )}
                
                {/* 末组Lift */}
                {currentDistribution.rank_ordering_analysis.lift_analysis?.last_decile_lift != null && (
                  <div className="flex items-center gap-1.5">
                    <span className="text-muted-foreground">末组Lift：</span>
                    <span className={cn(
                      "font-medium",
                      currentDistribution.rank_ordering_analysis.lift_analysis.last_decile_lift <= 0.5 
                        ? "text-green-600" 
                        : currentDistribution.rank_ordering_analysis.lift_analysis.last_decile_lift <= 0.8 
                          ? "text-blue-600" 
                          : "text-amber-600"
                    )}>
                      {currentDistribution.rank_ordering_analysis.lift_analysis.last_decile_lift.toFixed(2)}
                    </span>
                    <span className="text-muted-foreground">
                      （{currentDistribution.rank_ordering_analysis.lift_analysis.last_decile_bin}）
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}
          
          {/* 表格（最多显示12行） */}
          {currentBins && currentBins.length > 0 && (
            <div className="max-h-[240px] overflow-auto rounded border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs w-[40px] sticky top-0 bg-background">序号</TableHead>
                    <TableHead className="text-xs sticky top-0 bg-background">分数区间</TableHead>
                    <TableHead className="text-xs text-right sticky top-0 bg-background">样本数</TableHead>
                    <TableHead className="text-xs text-right sticky top-0 bg-background">样本占比</TableHead>
                    <TableHead className="text-xs text-right sticky top-0 bg-background">坏样本率</TableHead>
                    <TableHead className="text-xs text-right sticky top-0 bg-background">Lift</TableHead>
                    <TableHead className="text-xs text-right sticky top-0 bg-background">累计坏样本率</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {currentBins.slice(0, 12).map((bin: any, idx: number) => (
                    <TableRow key={idx}>
                      <TableCell className="text-xs py-1.5">{idx + 1}</TableCell>
                      <TableCell className="text-xs font-mono py-1.5">{bin.bin || bin.bin_label || '-'}</TableCell>
                      <TableCell className="text-xs text-right py-1.5">{bin.total?.toLocaleString()}</TableCell>
                      <TableCell className="text-xs text-right py-1.5">{(bin.pct_total || 0).toFixed(2)}%</TableCell>
                      <TableCell className="text-xs text-right py-1.5">
                        <span className={cn(
                          (bin.bad_rate || 0) > overallBadRate ? 'text-red-600 font-medium' : ''
                        )}>
                          {(bin.bad_rate || 0).toFixed(2)}%
                        </span>
                      </TableCell>
                      <TableCell className="text-xs text-right py-1.5">
                        <span className={cn(
                          (bin.lift || 0) > 1.5 ? 'text-red-600 font-medium' : 
                          (bin.lift || 0) < 0.5 ? 'text-green-600' : ''
                        )}>
                          {(bin.lift || 0).toFixed(2)}
                        </span>
                      </TableCell>
                      <TableCell className="text-xs text-right py-1.5">{(bin.cum_bad_rate || 0).toFixed(2)}%</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
          
          {/* 无数据提示 */}
          {(!currentBins || currentBins.length === 0) && (
            <div className="text-xs text-muted-foreground text-center py-4">
              暂无 {selectedDataset === 'train' ? '训练集' : selectedDataset === 'test' ? '测试集' : 'OOT验证集'} 的
              {analysisView === 'ranking' ? '排序性分析' : '评分分布'} 数据
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// 评分转换阶段预览
// =============================================================================

function ScoreScalingPreview({ data }: { data: Record<string, any> }) {
  const [expandedVariables, setExpandedVariables] = useState<Set<string>>(new Set());

  // 切换变量展开状态
  const toggleVariableExpand = (variable: string) => {
    setExpandedVariables(prev => {
      const newSet = new Set(prev);
      if (newSet.has(variable)) {
        newSet.delete(variable);
      } else {
        newSet.add(variable);
      }
      return newSet;
    });
  };

  // 获取评分范围数据
  const theoreticalRange = data.theoretical_score_range || {};
  
  // 按优先级选择评分分布统计的数据集：OOT > 测试集 > 训练集
  const scoreStatsByDataset = data.score_stats_by_dataset;
  let actualStats = data.actual_score_stats || {}; // 兜底：旧字段（训练集）
  let datasetLabel = "训练集";
  
  if (scoreStatsByDataset) {
    if (scoreStatsByDataset.oot) {
      actualStats = scoreStatsByDataset.oot;
      datasetLabel = "OOT验证集";
    } else if (scoreStatsByDataset.test) {
      actualStats = scoreStatsByDataset.test;
      datasetLabel = "测试集";
    } else if (scoreStatsByDataset.train) {
      actualStats = scoreStatsByDataset.train;
      datasetLabel = "训练集";
    }
  }
  
  // 计算理论评分区间宽度
  const theoreticalSpan = theoreticalRange.max && theoreticalRange.min 
    ? theoreticalRange.max - theoreticalRange.min 
    : null;

  // 下载完整评分卡CSV
  const handleDownloadScorecard = () => {
    const fullScorecard = data.full_scorecard_csv;
    if (!fullScorecard || fullScorecard.length === 0) {
      alert("完整评分卡数据不可用");
      return;
    }
    
    // 定义CSV列顺序（行业标准格式）
    const columns = ['variable', 'total_iv', 'cof', 'index', 'bin', 'count', 'count_distr', 'good', 'bad', 'badprob', 'woe', 'score'];
    const header = columns.join(',');
    
    // 生成CSV行
    const rows = fullScorecard.map((row: any) => {
      return columns.map(col => {
        const val = row[col];
        if (val === null || val === undefined) return '';
        if (typeof val === 'string' && (val.includes(',') || val.includes('"') || val.includes('\n'))) {
          return `"${val.replace(/"/g, '""')}"`;
        }
        return val;
      }).join(',');
    });
    
    const csvContent = [header, ...rows].join('\n');
    const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `scorecard_${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-4">
      {/* 理论评分范围（核心结果指标，放在最上面） */}
      {(theoreticalRange.min !== undefined || actualStats.min !== undefined) && (
        <div className="grid grid-cols-3 gap-3">
          <div className="p-3 bg-indigo-50 dark:bg-indigo-900/20 rounded-lg">
            <div className="text-xs text-gray-500">理论最低分</div>
            <div className="text-lg font-bold text-indigo-600">
              {theoreticalRange.min !== undefined ? Math.round(theoreticalRange.min) : "-"}
            </div>
          </div>
          <div className="p-3 bg-indigo-50 dark:bg-indigo-900/20 rounded-lg">
            <div className="text-xs text-gray-500">理论最高分</div>
            <div className="text-lg font-bold text-indigo-600">
              {theoreticalRange.max !== undefined ? Math.round(theoreticalRange.max) : "-"}
            </div>
          </div>
          <div className="p-3 bg-indigo-50 dark:bg-indigo-900/20 rounded-lg">
            <div className="text-xs text-gray-500">实际分布</div>
            <div className="text-lg font-bold text-indigo-600">
              {actualStats.min !== undefined && actualStats.max !== undefined 
                ? `${Math.round(actualStats.min)}~${Math.round(actualStats.max)}`
                : theoreticalSpan ? `区间${Math.round(theoreticalSpan)}分` : "-"
              }
            </div>
          </div>
        </div>
      )}

      {/* 转换配置（输入参数，放在核心指标之下） */}
      <div className="p-3 bg-slate-50 dark:bg-slate-900/30 rounded-lg border border-slate-200 dark:border-slate-700">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium text-slate-500 dark:text-slate-400 flex items-center gap-1">
            <Settings className="h-3 w-3" />
            转换配置
          </span>
        </div>
        <div className="grid grid-cols-3 gap-3">
          <div className="text-center">
            <div className="text-xs text-gray-400">基准分</div>
            <div className="text-sm font-bold text-slate-700 dark:text-slate-300">{data.base_score || "-"}</div>
          </div>
          <div className="text-center">
            <div className="text-xs text-gray-400">基准Odds</div>
            <div className="text-sm font-bold text-slate-700 dark:text-slate-300">{data.base_odds || "-"}:1</div>
          </div>
          <div className="text-center">
            <div className="text-xs text-gray-400">PDO</div>
            <div className="text-sm font-bold text-slate-700 dark:text-slate-300">{data.pdo || "-"}</div>
          </div>
        </div>
      </div>

      {/* 实际评分统计详情（如果有） */}
      {actualStats.mean !== undefined && (
        <div className="p-3 bg-gray-50 dark:bg-gray-900/30 rounded-lg">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-600 dark:text-gray-400">{datasetLabel}评分分布</span>
          </div>
          <div className="grid grid-cols-4 gap-2 text-xs">
            <div className="text-center">
              <div className="text-gray-400">均值</div>
              <div className="font-medium">{Math.round(actualStats.mean)}</div>
            </div>
            <div className="text-center">
              <div className="text-gray-400">标准差</div>
              <div className="font-medium">{actualStats.std?.toFixed(1)}</div>
            </div>
            <div className="text-center">
              <div className="text-gray-400">中位数</div>
              <div className="font-medium">{Math.round(actualStats.median)}</div>
            </div>
            <div className="text-center">
              <div className="text-gray-400">IQR</div>
              <div className="font-medium">{actualStats.q25 && actualStats.q75 ? `${Math.round(actualStats.q25)}~${Math.round(actualStats.q75)}` : "-"}</div>
            </div>
          </div>
        </div>
      )}

      {/* 评分卡变量数 + 下载按钮 */}
      <div className="p-3 bg-gray-50 dark:bg-gray-900/30 rounded-lg">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-600 dark:text-gray-400">评分卡变量数</span>
            <span className="font-bold text-lg">{data.num_variables || 0}</span>
          </div>
          {data.full_scorecard_csv && data.full_scorecard_csv.length > 0 && (
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-xs gap-1"
              onClick={handleDownloadScorecard}
            >
              <Download className="h-3 w-3" />
              下载完整评分卡
            </Button>
          )}
        </div>
      </div>

      {/* 变量得分预览（增强版） */}
      {data.scorecard_preview && data.scorecard_preview.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-600 dark:text-gray-400">变量得分详情</span>
            <span className="text-xs text-gray-400">点击变量查看分箱详情</span>
          </div>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="text-xs w-8"></TableHead>
                <TableHead className="text-xs">变量名</TableHead>
                <TableHead className="text-xs text-center">分箱数</TableHead>
                <TableHead className="text-xs text-right">得分范围</TableHead>
                <TableHead className="text-xs text-right">最大贡献</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.scorecard_preview
                .filter((item: any) => item.variable !== 'basepoints')
                .map((item: { 
                  variable: string; 
                  bins: number; 
                  min_score?: number;
                  max_score?: number;
                  score_range?: number;
                  bin_details?: Array<{bin: string; points: number}>;
                }, idx: number) => {
                  const isExpanded = expandedVariables.has(item.variable);
                  const hasDetails = item.bin_details && item.bin_details.length > 0;
                  
                  return (
                    <React.Fragment key={idx}>
                      <TableRow 
                        className={cn(
                          hasDetails && "cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800",
                          isExpanded && "bg-blue-50/50 dark:bg-blue-900/10"
                        )}
                        onClick={() => hasDetails && toggleVariableExpand(item.variable)}
                      >
                        <TableCell className="text-xs px-2">
                          {hasDetails && (
                            <ChevronRight className={cn(
                              "h-3 w-3 text-gray-400 transition-transform",
                              isExpanded && "rotate-90"
                            )} />
                          )}
                        </TableCell>
                        <TableCell className="text-xs font-mono">{item.variable}</TableCell>
                        <TableCell className="text-xs text-center">{item.bins}</TableCell>
                        <TableCell className="text-xs text-right font-mono">
                          {item.min_score !== undefined && item.max_score !== undefined ? (
                            <span className={cn(
                              item.min_score < 0 ? "text-red-500" : "",
                              item.max_score > 0 ? "" : "text-red-500"
                            )}>
                              [{item.min_score > 0 ? "+" : ""}{item.min_score}, {item.max_score > 0 ? "+" : ""}{item.max_score}]
                            </span>
                          ) : "-"}
                        </TableCell>
                        <TableCell className="text-xs text-right">
                          {item.score_range !== undefined ? (
                            <Badge variant="outline" className="text-[10px]">
                              {item.score_range}分
                            </Badge>
                          ) : "-"}
                        </TableCell>
                      </TableRow>
                      {/* 展开的分箱详情 */}
                      {isExpanded && hasDetails && (
                        <TableRow>
                          <TableCell colSpan={5} className="p-0">
                            <div className="bg-gray-50 dark:bg-gray-900/50 p-3 border-t border-b">
                              <div className="text-xs font-medium text-gray-500 mb-2">分箱得分明细</div>
                              <div className="grid grid-cols-2 gap-2">
                                {item.bin_details!.map((binItem, binIdx) => (
                                  <div key={binIdx} className="flex justify-between items-center text-xs bg-white dark:bg-gray-800 p-2 rounded">
                                    <span className="font-mono text-gray-600 dark:text-gray-400 truncate max-w-[150px]" title={binItem.bin}>
                                      {binItem.bin}
                                    </span>
                                    <span className={cn(
                                      "font-bold ml-2",
                                      binItem.points > 0 ? "text-green-600" : binItem.points < 0 ? "text-red-600" : "text-gray-500"
                                    )}>
                                      {binItem.points > 0 ? "+" : ""}{binItem.points}
                                    </span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          </TableCell>
                        </TableRow>
                      )}
                    </React.Fragment>
                  );
                })}
            </TableBody>
          </Table>
        </div>
      )}

      {/* 指标说明 */}
      <div className="text-xs text-gray-400 space-y-1 pt-2 border-t">
        <div>• <strong>理论评分范围</strong>：基于评分卡各变量得分的最小/最大值之和计算</div>
        <div>• <strong>得分范围</strong>：变量各分箱得分的[最小值, 最大值]</div>
        <div>• <strong>最大贡献</strong>：变量最大得分与最小得分之差，体现变量区分度</div>
      </div>
    </div>
  );
}

// =============================================================================
// 报告生成阶段预览
// =============================================================================

function ReportGenerationPreview({ data }: { data: Record<string, any> }) {
  return (
    <div className="space-y-4">
      {/* 报告状态 */}
      <div className="flex items-center gap-2 p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
        <CheckCircle2 className="h-5 w-5 text-green-600" />
        <div className="flex-1">
          <div className="font-medium text-green-700 dark:text-green-400">报告生成完成</div>
          <div className="text-xs text-gray-500">
            切换到"任务结果"标签页查看完整报告
          </div>
        </div>
      </div>

      {/* 报告内容概要 */}
      {data.report_sections && (
        <div className="space-y-2">
          <div className="text-sm font-medium text-gray-600 dark:text-gray-400">报告内容</div>
          <div className="grid grid-cols-2 gap-2">
            {data.report_sections.map((section: string, idx: number) => (
              <div key={idx} className="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400 p-2 bg-gray-50 dark:bg-gray-900/30 rounded">
                <FileText className="h-3 w-3" />
                {section}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 数据集信息 */}
      {data.datasets && (
        <div className="space-y-2">
          <div className="text-sm font-medium text-gray-600 dark:text-gray-400">评估数据集</div>
          <div className="flex gap-2">
            {data.datasets.map((ds: string, idx: number) => (
              <Badge key={idx} variant="outline" className="text-xs">{ds}</Badge>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// 通用预览（JSON格式）
// =============================================================================

function GenericPreview({ data }: { data: Record<string, any> }) {
  return (
    <div className="p-3 bg-gray-50 dark:bg-gray-900/30 rounded-lg">
      <pre className="text-xs font-mono text-gray-600 dark:text-gray-400 whitespace-pre-wrap overflow-auto max-h-64">
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
}

// =============================================================================
// 主组件
// =============================================================================

export function StageOutputPreview({
  stageId,
  stageName,
  outputPreview,
  status,
  onBack,
  className,
  // 专家模式相关
  isExpertMode = false,
  stageData,
  onEditParams,
  onEditCode,
  onRetryStage,
  sessionId = "",
  recordId,
  isDarkMode = false,
  executionTimeMs,
  selectedModel,
  modelConfig,
  // 自动模式 AI 分析（外部传入）
  externalAiAnalysis,
  isExternalAnalyzing = false,
  onExternalReanalyze,
  // 数据列（用于参数表单）
  dataFilePath,
  columns = [],
  columnsLoading = false,
  // 专家模式最后阶段整体分析所需（Phase 20）
  isLastStage = false,
  taskType,
  taskResult,
  // 版本历史快照
  snapshots = [],
}: StageOutputPreviewProps) {
  // 版本选择：null 表示当前，数字表示历史版本
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null);
  // 根据 selectedVersion 取快照或当前数据
  const activeSnapshot = selectedVersion !== null
    ? snapshots.find(s => s.version === selectedVersion) ?? null
    : null;
  const activeOutputPreview = activeSnapshot ? activeSnapshot.output_preview : outputPreview;
  const activeParams = activeSnapshot ? activeSnapshot.params_used : (stageData?.params || {});
  // 编辑模式状态 - 根据阶段状态智能初始化
  // 阶段执行中（有代码但无结果）：显示代码tab
  // 阶段完成（有结果）：显示结果tab
  const getInitialEditMode = (): "preview" | "params" | "code" => {
    if (status === "running" && stageData?.code) {
      return "code";  // 执行中显示代码
    }
    if (status === "completed" && outputPreview) {
      return "preview";  // 完成后显示结果
    }
    return "preview";
  };
  
  const [editMode, setEditMode] = useState<"preview" | "params" | "code">(getInitialEditMode);
  const [localParams, setLocalParams] = useState<Record<string, any>>(stageData?.params || {});
  const [localCode, setLocalCode] = useState<string>(stageData?.code || "");
  // 参数编辑模式：form（可视化表单）或 json（JSON编辑器）
  const [paramsEditMode, setParamsEditMode] = useState<"form" | "json">("form");
  // 跟踪用户是否正在编辑参数（防止轮询数据覆盖用户编辑）
  const [isUserEditing, setIsUserEditing] = useState(false);

  // v2.1: 当 stageData.params 更新时（如阶段重试完成后），同步到 localParams
  // 但如果用户正在编辑，则不同步，避免覆盖用户输入
  useEffect(() => {
    if (isUserEditing) {
      return; // 用户正在编辑，不覆盖
    }
    if (stageData?.params && Object.keys(stageData.params).length > 0) {
      setLocalParams(stageData.params);
    }
  }, [stageData?.params, isUserEditing]);

  // 数据列状态（用于参数表单中的列选择控件）
  const [internalColumns, setInternalColumns] = useState<DataColumn[]>([]);
  const [internalColumnsLoading, setInternalColumnsLoading] = useState(false);
  
  // 实际使用的列数据（外部传入优先）
  const effectiveColumns = columns.length > 0 ? columns : internalColumns;
  const effectiveColumnsLoading = columns.length > 0 ? columnsLoading : internalColumnsLoading;
  
  // 自动加载数据列（从工作区获取）
  useEffect(() => {
    if (columns.length > 0) {
      return;
    }
    
    const loadColumns = async () => {
      // 优先使用任务执行状态中的数据文件路径，其次从参数中获取
      let dataFile = dataFilePath || localParams.data_file || stageData?.params?.data_file;
      
      // 如果 dataFile 是完整路径（如 workspace\session_xxx\file.csv），提取文件名
      // /workspace/data-columns API 期望的是相对于 session 目录的文件名
      if (dataFile && (dataFile.includes('/') || dataFile.includes('\\'))) {
        // 提取文件名（处理 Windows 和 Unix 路径分隔符）
        const parts = dataFile.split(/[/\\]/);
        dataFile = parts[parts.length - 1];
      }
      
      // 如果没有数据文件路径，尝试从工作区获取第一个数据文件
      // 注意：sessionId 初始值可能是空字符串，需要检查长度
      if (!dataFile && sessionId && sessionId.length > 0) {
        try {
          const filesResponse = await fetch(getApiUrl(`/workspace/files?session_id=${encodeURIComponent(sessionId)}`));
          if (filesResponse.ok) {
            const response = await filesResponse.json();
            // API 返回 {files: [...]} 格式
            const files = response.files || [];
            // 查找第一个 CSV 或 Excel 文件
            const dataFiles = files.filter((f: { name: string }) => 
              f.name.endsWith('.csv') || f.name.endsWith('.xlsx') || f.name.endsWith('.xls')
            );
            if (dataFiles.length > 0) {
              dataFile = dataFiles[0].name;
            }
          }
        } catch (error) {
          console.warn("Failed to get workspace files:", error);
        }
      }
      
      if (!dataFile) { 
        setInternalColumns([]); 
        return; 
      }
      
      try {
        setInternalColumnsLoading(true);
        const response = await fetch(
          getApiUrl(`/workspace/data-columns?file_path=${encodeURIComponent(dataFile)}&session_id=${encodeURIComponent(sessionId)}`)
        );
        if (response.ok) {
          const cols: DataColumn[] = await response.json();
          setInternalColumns(cols);
        }
      } catch (error) {
        console.warn("Failed to load columns:", error);
        setInternalColumns([]);
      } finally {
        setInternalColumnsLoading(false);
      }
    };
    loadColumns();
  }, [dataFilePath, localParams.data_file, stageData?.params?.data_file, sessionId, columns.length]);
  
  // AI分析相关状态
  // 初始化时从缓存读取（如果有）
  // Phase 9: 使用 recordId 作为缓存键，确保不同任务的缓存独立
  const cachedAnalysis = getCachedAnalysis(recordId || "", stageId);
  const [aiAnalysis, setAiAnalysis] = useState<string>(cachedAnalysis || "");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisExpanded, setAnalysisExpanded] = useState(true);
  // AI 建议的结构化参数（从保存接口返回的 suggested_params 字段）
  const [suggestedParams, setSuggestedParams] = useState<Record<string, unknown> | null>(null);
  // 如果有缓存，标记为已触发（避免重复调用）
  const [hasTriggeredAnalysis, setHasTriggeredAnalysis] = useState(!!cachedAnalysis);
  // Phase 12: 正在从缓存加载分析结果的标记，防止竞态条件导致重复触发分析
  // Phase 13: 当有 recordId 且没有 sessionStorage 缓存时，初始化为 true，
  //           表示需要先尝试从后端 API 加载缓存，防止自动触发分析抢先执行
  const [isLoadingCachedAnalysis, setIsLoadingCachedAnalysis] = useState(
    () => !!recordId && !cachedAnalysis
  );
  
  // Phase 14: 分析请求版本号，用于防止竞态条件
  // 当新的分析请求开始时，旧的请求结果应该被忽略（不保存到后端）
  const analysisVersionRef = useRef(0);
  
  // 用于跟踪上一次的状态，实现自动切换
  const prevStatusRef = useRef(status);
  // 用于跟踪上一次的 stageId，检测阶段切换
  const prevStageIdRef = useRef(stageId);
  
  // Phase 16: 重试时保存旧的 outputPreview 引用，用于检测数据是否真正更新
  // 解决重试后 AI 分析仍使用旧数据的问题
  const retryPendingOutputRef = useRef<any>(null);
  
  // Phase 17: 跟踪上一次的 outputPreview 内容哈希，用于检测数据是否真正更新
  // 使用内容哈希而非引用比较，避免 React 状态更新时机导致的竞态问题
  const prevOutputHashRef = useRef<string>("");
  // Phase 17: 跟踪 status 刚变为 completed 的时间点，用于延迟触发分析
  const statusJustCompletedRef = useRef(false);
  // Phase 18: 延迟触发 AI 分析的定时器
  const analysisDelayTimerRef = useRef<NodeJS.Timeout | null>(null);
  // Phase 19: 存储最新的 outputPreview，解决 useCallback 闭包问题
  const latestOutputPreviewRef = useRef<Record<string, any> | null>(null);
  
  // Phase 11: 组件挂载时从 API 加载 AI 分析缓存（处理历史任务加载场景）
  // 这解决了加载历史任务后点击已完成阶段时，AI 分析没有从缓存加载的问题
  // Phase 12: 添加 isLoadingCachedAnalysis 状态管理
  const initialLoadDoneRef = useRef(false);
  useEffect(() => {
    // 只在组件首次挂载且有 recordId 时执行一次
    if (initialLoadDoneRef.current || !recordId || cachedAnalysis) return;
    initialLoadDoneRef.current = true;
    
    // Phase 12: 开始加载缓存
    setIsLoadingCachedAnalysis(true);
    
    const loadInitialAnalysis = async () => {
      try {
        const apiResult = await fetchAnalysisFromAPI(recordId, stageId);
        if (apiResult?.analysis_text) {
          setAiAnalysis(apiResult.analysis_text);
          setHasTriggeredAnalysis(true);
          // 同步到 sessionStorage
          setCachedAnalysis(recordId, stageId, apiResult.analysis_text);
        }
      } finally {
        // Phase 12: 加载完成
        setIsLoadingCachedAnalysis(false);
      }
    };
    
    loadInitialAnalysis();
  }, [recordId, stageId, cachedAnalysis]);

  // 代码是否可编辑（专家模式下始终只读，因为 Pipeline 执行引擎不支持代码编辑）
  // 注意：LLM SOP 执行模式已废弃，代码编辑功能不再可用
  const isCodeEditable = false;
  
  // 是否有参数元数据（决定是否显示可视化表单）
  const hasParamsMeta = stageData?.params_meta && stageData.params_meta.length > 0;

  // =============================================================================
  // Phase 22: AI分析Prompt已迁移至后端 API/AI_analysis_prompts.py
  // 前端通过 /v1/chat/analysis/prompt API 获取分析提示词
  // 以下冗余代码已清理：stageNameMap, stageRoleConfig, buildStageAnalysisPrompt
  // =============================================================================

  // 执行AI分析
  // Phase 14: 使用版本号机制防止竞态条件，确保只有最新的分析结果被保存
  // Phase 19: 使用 latestOutputPreviewRef 获取最新数据，避免闭包问题
  // Phase 20: 专家模式最后阶段使用整体分析Prompt
  // Phase 22: 迁移到后端 API 获取 prompt（Phase 1 实施）
  const performAIAnalysis = useCallback(async () => {
    // Phase 19: 优先使用 ref 中的最新数据
    const currentOutputPreview = latestOutputPreviewRef.current || outputPreview;
    
    // 前置条件检查和日志
    if (!currentOutputPreview) {
      console.warn("[AI Analysis] Skipped: No output preview data");
      return;
    }
    if (!selectedModel) {
      console.warn("[AI Analysis] Skipped: No model selected");
      return;
    }
    if (isAnalyzing) {
      console.warn("[AI Analysis] Skipped: Already analyzing");
      return;
    }
    
    // Phase 14: 递增版本号，标记这是一个新的分析请求
    analysisVersionRef.current += 1;
    const currentVersion = analysisVersionRef.current;
    
    // Phase 20: 判断是否应使用整体分析Prompt
    // 专家模式下报告生成阶段完成后，直接使用整体分析prompt（不需要单独的阶段分析）
    // 修复：移除对 isLastStage 的依赖，因为 report_generation 在评分卡和规则挖掘任务中都是最后一个阶段
    // 避免因 isLastStage 计算时序问题导致使用错误的阶段分析模板
    const shouldUseOverallAnalysis = isExpertMode && stageId === "report_generation";
    
    // 如果应该使用整体分析但 taskResult 还未加载，跳过本次触发
    // taskResult 会在 three-panel-interface 的 handleSOPStatusUpdate 中异步加载
    // 加载完成后会触发 useEffect 重新执行
    if (shouldUseOverallAnalysis && !taskResult) {
      console.log("[AI Analysis] Skipped: shouldUseOverallAnalysis=true but taskResult is not ready yet");
      return;
    }
    
    setIsAnalyzing(true);
    setAiAnalysis("");
    
    // 用于累积完整的分析结果
    let fullAnalysis = "";
    
    try {
      // Phase 22: 调用后端 API 获取 prompt 和参数（替代前端硬编码）
      const promptRequest = shouldUseOverallAnalysis
        ? {
            analysis_type: "overall",
            task_type: taskType,
            result: taskResult,
          }
        : {
            analysis_type: "stage",
            task_type: taskType,
            stage_id: stageId,
            stage_name: stageName,
            data: currentOutputPreview,
          };
      
      console.log(`[AI Analysis] Requesting prompt for stage=${stageId}, taskType=${taskType}, analysisType=${promptRequest.analysis_type}`);
      // Debug: 检查整体分析时 taskResult 的数据结构
      if (shouldUseOverallAnalysis && taskResult) {
        console.log(`[AI Analysis Debug] taskResult keys:`, Object.keys(taskResult));
        console.log(`[AI Analysis Debug] taskResult.outputs keys:`, taskResult.outputs ? Object.keys(taskResult.outputs) : 'N/A');
        console.log(`[AI Analysis Debug] taskResult.stages keys:`, taskResult.stages ? Object.keys(taskResult.stages) : 'N/A');
        // 检查关键指标
        const multiMetrics = taskResult.outputs?.multi_dataset_metrics;
        console.log(`[AI Analysis Debug] multi_dataset_metrics:`, multiMetrics ? JSON.stringify(multiMetrics).slice(0, 200) : 'N/A');
      }
      
      
      const promptResponse = await fetch(getApiUrl("/v1/chat/analysis/prompt"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(promptRequest),
      });
      
      if (!promptResponse.ok) {
        const errorText = await promptResponse.text().catch(() => "");
        throw new Error(`获取分析Prompt失败: ${promptResponse.status} - ${errorText}`);
      }
      
      const promptResult = await promptResponse.json();
      if (!promptResult.success) {
        throw new Error(promptResult.error || "获取分析Prompt失败");
      }
      
      const prompt = promptResult.prompt;
      const AI_ANALYSIS_PARAMS = promptResult.params;
      
      const response = await fetch(getApiUrl("/v1/chat/completions"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: selectedModel,
          messages: [
            { role: "user", content: prompt }
          ],
          stream: true,
          ...AI_ANALYSIS_PARAMS,
          // 禁用任务感知和代码执行，避免触发参数推断模式
          include_task_list: false,
          enable_code_execution: false,
        }),
      });

      if (!response.ok) {
        const errorText = await response.text().catch(() => "");
        throw new Error(`LLM API请求失败: ${response.status} - ${errorText}`);
      }

      // 流式响应处理（带buffer处理跨chunk数据）
      const reader = response.body?.getReader();
      if (!reader) throw new Error("无法获取响应流");

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;


        // 使用stream: true确保多字节字符正确解码
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        // 保留最后一个可能不完整的行
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = line.slice(6);
            if (data === "[DONE]") continue;
            
            try {
              const parsed = JSON.parse(data);
              const content = parsed.choices?.[0]?.delta?.content;
              if (content) {
                fullAnalysis += content;
                // Phase 14: 只有当前版本的分析才更新UI
                if (currentVersion === analysisVersionRef.current) {
                  setAiAnalysis(prev => prev + content);
                }
              }
            } catch {
              // 忽略解析错误
            }
          }
        }
      }
      
      // Phase 14: 只有当前版本的分析才保存到缓存
      // 如果版本号不匹配，说明有新的分析请求已经开始，当前结果应该被丢弃
      if (currentVersion !== analysisVersionRef.current) {
        return;
      }
      
      // 分析完成后保存到缓存
      // Phase 7: 优先保存到后端 API（如果有 recordId），同时保存到 sessionStorage 作为降级
      // Phase 9: 使用 recordId 作为缓存键
      if (fullAnalysis && recordId) {
        // 保存到 sessionStorage（降级方案）
        setCachedAnalysis(recordId, stageId, fullAnalysis);
        
        // 保存到后端 API，并获取解析到的参数建议
        saveAnalysisToAPI(recordId, stageId, fullAnalysis, selectedModel)
          .then(({ success, suggested_params }) => {
            if (!success) {
              console.warn(`[AI Analysis] Failed to save analysis to API for ${recordId}/${stageId}`);
            }
            // 更新建议参数 state（流式完成后才渲染卡片）
            if (suggested_params && Object.keys(suggested_params).length > 0) {
              setSuggestedParams(suggested_params as Record<string, unknown>);
            }
          })
          .catch((error) => {
            console.error(`[AI Analysis] Error saving analysis to API: ${error}`);
          });
      } else if (fullAnalysis && !recordId) {
        console.warn(`[AI Analysis] Cannot save to API: recordId is missing (stageId=${stageId})`);
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      console.error("AI分析失败:", errorMessage, error);
      console.error(`[AI Analysis Debug] stageId=${stageId}, selectedModel=${selectedModel}, hasOutputPreview=${!!currentOutputPreview}`);
      // Phase 14: 只有当前版本的分析才更新错误状态
      if (currentVersion === analysisVersionRef.current) {
        // 显示更详细的错误信息帮助用户和开发者诊断问题
        setAiAnalysis(`分析生成失败：${errorMessage}。请检查控制台获取详细信息。`);
      }
    } finally {
      // Phase 14: 只有当前版本的分析才重置loading状态
      if (currentVersion === analysisVersionRef.current) {
        setIsAnalyzing(false);
      }
    }
  }, [outputPreview, selectedModel, stageId, stageName, sessionId, recordId, isAnalyzing, modelConfig, isExpertMode, taskResult, taskType]);

  // 专家模式下，阶段完成时自动触发AI分析
  // 检查 outputPreview 数据是否完整（非空对象且包含有效数据）
  const isOutputDataReady = useCallback((data: Record<string, any> | null, stage: string): boolean => {
    if (!data || typeof data !== 'object') return false;
    
    // 检查是否为空对象
    const keys = Object.keys(data);
    if (keys.length === 0) return false;
    
    // 根据阶段检查关键字段（支持多种字段名）
    switch (stage) {
      case "data_loading":
      case "preprocessing":
        // 必须有 rows 和 (feature_count 或 columns) 才算数据完整
        return data.rows !== undefined && (data.feature_count !== undefined || data.columns !== undefined);
      case "woe_binning":
        // 必须有 total_features 和 iv_table 才算数据完整
        return data.total_features !== undefined && data.iv_table && data.iv_table.length > 0;
      case "feature_selection":
      case "feature_engineering":
        // 必须同时有 before 和 after 数据才算完整
        return (data.before_count !== undefined && data.after_count !== undefined) ||
               (data.original_count !== undefined && data.selected_count !== undefined) ||
               (data.selected_features && data.selected_features.length > 0 && data.before_count !== undefined);
      case "model_training":
        // 模型训练阶段 - 只需要有模型系数即可（output_preview包含intercept和coefficients）
        // 注意：train_auc/test_auc是在model_evaluation阶段才有的
        return data.intercept !== undefined || 
               (data.coefficients && data.coefficients.length > 0);
      case "model_evaluation":
        // 模型评估阶段 - 必须同时有 KS 和 AUC 才算数据完整
        return (data.test_ks !== undefined || data.ks !== undefined || data.test_metrics?.ks !== undefined) &&
               (data.test_auc !== undefined || data.auc !== undefined || data.test_metrics?.auc !== undefined);
      case "evaluating_rules":
        // 规则评估阶段 - 必须同时有 before_count 和 after_count 才算数据完整
        return (data.before_count !== undefined && data.after_count !== undefined) ||
               (data.beforeCount !== undefined && data.afterCount !== undefined);
      case "score_scaling":
        // 必须有 base_score 和 num_variables 才算数据完整
        return (data.base_score !== undefined || data.baseScore !== undefined) &&
               (data.num_variables !== undefined || data.numVariables !== undefined || 
                (data.scorecard_preview && data.scorecard_preview.length > 0));
      case "rule_mining":
        return data.rules !== undefined || data.rule_count !== undefined;
      case "generating_rules":
        // 规则生成阶段 - 检查 total_rules 或 totalRules
        return data.total_rules !== undefined || data.totalRules !== undefined;
      case "filtering_rules":
        // 规则过滤阶段 - 必须同时有 before_count 和 after_count 才算数据完整
        return (data.before_count !== undefined && data.after_count !== undefined) ||
               (data.beforeCount !== undefined && data.afterCount !== undefined);
      case "rule_filtering":
        // 规则筛选阶段（v2.0合并后）- 必须有 generated_count 才算数据完整
        // 注意：不能只检查 total_rules，因为那是上一阶段的数据
        return data.generated_count !== undefined && data.after_count !== undefined;
      case "selecting_rules":
        // 最优规则选择阶段 - 必须同时有 before_count 和 after_count 才算数据完整
        // 使用 && 确保两个关键字段都存在，避免用不完整数据触发 AI 分析
        return (data.before_count !== undefined && data.after_count !== undefined) ||
               (data.candidate_count !== undefined && data.selected_count !== undefined);
      default:
        // 默认：只要有任何键值就认为有数据
        return keys.length > 0;
    }
  }, []);








  // Phase 12: 自动触发 AI 分析（仅在未加载缓存且无缓存时触发）
  // Phase 16: 增加重试等待检查，确保 outputPreview 真正更新后才触发分析
  // Phase 17: 增加 outputPreview 变化检测，避免用旧数据触发分析
  useEffect(() => {
    // Phase 19: 始终更新最新的 outputPreview ref
    latestOutputPreviewRef.current = outputPreview;
    
    // Phase 16: 如果正在等待重试后的新数据，检查 outputPreview 是否已更新
    if (retryPendingOutputRef.current !== null) {
      // 比较引用是否相同（浅比较）
      if (outputPreview === retryPendingOutputRef.current) {
        // outputPreview 还是旧数据，不触发分析
        return;
      } else {
        // outputPreview 已更新，清除等待标记
        retryPendingOutputRef.current = null;
      }
    }
    
    // Phase 18: 计算 outputPreview 的内容哈希（用于检测数据是否真正变化）
    const getOutputHash = (data: any): string => {
      if (!data) return "";
      try {
        // 只取关键字段计算哈希，避免时间戳等无关字段影响
        const keyFields = {
          generated_count: data.generated_count,
          after_count: data.after_count,
          direction_filtered_count: data.direction_filtered_count,
          before_count: data.before_count,
          total_rules: data.total_rules,
          filter_criteria: data.filter_criteria,
        };
        return JSON.stringify(keyFields);
      } catch {
        return "";
      }
    };
    
    const currentHash = getOutputHash(outputPreview);
    const outputDataChanged = currentHash !== prevOutputHashRef.current && currentHash !== "";
    
    // 只有当数据真正变化时才更新哈希
    if (outputDataChanged) {
      prevOutputHashRef.current = currentHash;
    }
    
    // 判断是否需要整体分析（专家模式报告生成阶段）
    // 修复：移除对 isLastStage 的依赖，保持与 performAIAnalysis 中 shouldUseOverallAnalysis 一致
    // report_generation 阶段不需要单独的阶段AI分析，完成后直接触发任务整体分析
    const needsOverallAnalysis = isExpertMode && stageId === "report_generation";
    // 整体分析需要 taskResult，阶段分析不需要
    const isDataReadyForAnalysis = needsOverallAnalysis ? !!taskResult : true;
    
    if (
      isExpertMode && 
      status === "completed" && 
      outputPreview && 
      isOutputDataReady(outputPreview, stageId) &&  // 增加数据完整性检查
      selectedModel &&
      !hasTriggeredAnalysis &&
      !aiAnalysis &&
      !isLoadingCachedAnalysis &&  // Phase 12: 正在加载缓存时不触发
      isDataReadyForAnalysis  // 整体分析需要等待 taskResult 加载完成
    ) {
      // Phase 18: 使用延迟触发，确保 React 状态完全同步
      // 清除之前的定时器
      if (analysisDelayTimerRef.current) {
        clearTimeout(analysisDelayTimerRef.current);
      }
      
      // 延迟 300ms 触发，让 React 有时间完成所有状态更新
      analysisDelayTimerRef.current = setTimeout(() => {
        // 再次检查条件（防止在延迟期间状态变化）
        setHasTriggeredAnalysis(true);
        performAIAnalysis();
      }, 300);  // Phase 19: 增加延迟确保数据同步
      
      return; // 等待延迟触发
    }
  }, [isExpertMode, status, outputPreview, stageId, selectedModel, hasTriggeredAnalysis, aiAnalysis, performAIAnalysis, isOutputDataReady, isLoadingCachedAnalysis, taskResult]);


  // Phase 18: 组件卸载时清理延迟触发定时器
  useEffect(() => {
    return () => {
      if (analysisDelayTimerRef.current) {
        clearTimeout(analysisDelayTimerRef.current);
      }
    };
  }, []);

  // 当阶段ID变化时，从缓存加载分析结果（而不是重置）
  // Phase 7: 优先从后端 API 读取，降级到 sessionStorage
  // Phase 8: 当阶段被跳过（_skipped_during_retry）时，清除旧的AI分析缓存，避免显示与当前数据不一致的分析结果
  // Phase 12: 使用 isLoadingCachedAnalysis 状态防止竞态条件
  useEffect(() => {
    // 检测阶段是否真的变化了
    if (prevStageIdRef.current !== stageId) {
      prevStageIdRef.current = stageId;
      
      // Phase 12: 开始加载缓存，阻止自动触发分析
      setIsLoadingCachedAnalysis(true);
      
      // 异步加载分析结果
      const loadAnalysis = async () => {
        try {
          // 2026-02-10: 移除对 _skipped_during_retry 的缓存清理逻辑
          // 原错误逻辑：跳过的阶段清除AI缓存
          // 正确逻辑：跳过的阶段数据没有变化，AI分析缓存仍然有效，应该保留
          // 只有重新执行的阶段（从 pending -> running）才需要清理 AI 分析缓存
          
          // 1. 优先从后端 API 读取（如果有 recordId）
          if (recordId) {
            const apiResult = await fetchAnalysisFromAPI(recordId, stageId);
            if (apiResult?.analysis_text) {
              setAiAnalysis(apiResult.analysis_text);
              setHasTriggeredAnalysis(true);
              // 同步到 sessionStorage（使用 recordId 作为键）
              setCachedAnalysis(recordId, stageId, apiResult.analysis_text);
              return;
            }
          }
          
          // 2. 降级：从 sessionStorage 读取（使用 recordId 作为键）
          if (recordId) {
            const cached = getCachedAnalysis(recordId, stageId);
            if (cached) {
              setAiAnalysis(cached);
              setHasTriggeredAnalysis(true);
              return;
            }
          }
          
          // 无缓存，重置状态（等待自动触发或手动触发）
          setAiAnalysis("");
          setHasTriggeredAnalysis(false);
        } finally {
          // Phase 12: 加载完成，允许自动触发分析
          setIsLoadingCachedAnalysis(false);
        }
      };
      
      loadAnalysis();
    }
  }, [stageId, sessionId, recordId, outputPreview]);
  
  // Phase 10 修复：当 recordId 变化时（例如从历史任务恢复），重新加载AI分析缓存
  // 这处理用户恢复暂停任务后点击已完成阶段的情况
  // Phase 12: 添加 isLoadingCachedAnalysis 状态管理
  const prevRecordIdRef = useRef(recordId);
  useEffect(() => {
    // 只在 recordId 从无到有变化时触发（不是 stageId 变化）
    if (prevRecordIdRef.current !== recordId && recordId && !aiAnalysis) {
      prevRecordIdRef.current = recordId;
      
      // Phase 12: 开始加载缓存
      setIsLoadingCachedAnalysis(true);
      
      // 异步加载分析结果
      const loadAnalysisOnRecordIdChange = async () => {
        try {
          const apiResult = await fetchAnalysisFromAPI(recordId, stageId);
          if (apiResult?.analysis_text) {
            setAiAnalysis(apiResult.analysis_text);
            setHasTriggeredAnalysis(true);
            // 同步到 sessionStorage
            setCachedAnalysis(recordId, stageId, apiResult.analysis_text);
          }
        } finally {
          // Phase 12: 加载完成
          setIsLoadingCachedAnalysis(false);
        }
      };
      
      loadAnalysisOnRecordIdChange();
    } else {
      prevRecordIdRef.current = recordId;
    }
  }, [recordId, stageId, aiAnalysis]);
  
  // 2026-02-10: 移除对 _skipped_during_retry 的缓存清理逻辑
  // 原逻辑错误：跳过的阶段（重试阶段之前）数据没有变化，AI 分析缓存仍然有效，不应清理
  // 正确逻辑：只有重新执行的阶段（从 pending -> running）才需要清理 AI 分析缓存
  
  // 2026-02-10: 当阶段从非running变为running时，清除AI分析缓存
  // 这处理阶段重试后重新执行的情况（非跳过阶段）
  // 重新执行的阶段会产生新的输出，旧的AI分析不再适用
  useEffect(() => {
    if (prevStatusRef.current !== "running" && status === "running" && recordId) {
      // 阶段开始重新执行，清除旧的AI分析
      setAiAnalysis("");
      setHasTriggeredAnalysis(false);
      deleteCachedAnalysis(recordId, stageId);
      // 注意：后端缓存已在 retryStage API 中通过 invalidate_checkpoints_from 清理
    }
  }, [status, recordId, stageId]);
  
  // 自动切换tab：阶段开始执行时显示代码，完成时切换到结果
  useEffect(() => {
    // 阶段从非running变为running：切换到代码tab
    if (prevStatusRef.current !== "running" && status === "running" && stageData?.code) {
      setEditMode("code");
    }
    // 阶段完成时切换到结果tab（放宽条件：只要之前不是completed且现在是completed就切换）
    // 这样可以处理：running -> completed, paused -> completed, pending -> completed（缓存恢复）等情况
    if (prevStatusRef.current !== "completed" && status === "completed" && outputPreview) {
      setEditMode("preview");
    }
    prevStatusRef.current = status;
  }, [status, stageData?.code, outputPreview]);
  
  // 同步更新本地代码（当外部code变化时）
  useEffect(() => {
    if (stageData?.code) {
      setLocalCode(stageData.code);
    }
  }, [stageData?.code]);
  
  // 格式化执行时间
  const formatExecutionTime = (ms: number | null | undefined): string => {
    if (ms === null || ms === undefined) return "";
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    const minutes = Math.floor(ms / 60000);
    const seconds = ((ms % 60000) / 1000).toFixed(0);
    return `${minutes}m ${seconds}s`;
  };

  // 根据阶段ID选择预览组件（历史版本时使用快照数据）
  const renderPreview = () => {
    if (!activeOutputPreview) {
      return (
        <div className="flex flex-col items-center justify-center py-12 text-gray-400">
          <Database className="h-12 w-12 mb-2 opacity-50" />
          <p className="text-sm">{activeSnapshot ? "该版本无结果数据" : "暂无预览数据"}</p>
          <p className="text-xs mt-1">阶段完成后将显示输出预览</p>
        </div>
      );
    }

    switch (stageId) {
      case "data_loading":
      case "preprocessing":
        return <DataLoadingPreview data={activeOutputPreview} taskType={taskType} />;
      case "woe_binning":
        return <WoeBinningPreview data={activeOutputPreview} />;
      case "feature_selection":
      case "feature_engineering":
        return <FeatureSelectionPreview data={activeOutputPreview} />;
      case "model_training":
        return <ModelTrainingPreview data={activeOutputPreview} />;
      case "model_evaluation":
        return <ModelEvaluationPreview data={activeOutputPreview} />;
      case "generating_rules":
        return <RuleGenerationPreview data={activeOutputPreview} />;
      case "rule_filtering":
      case "filtering_rules":
      case "evaluating_rules":
        return <RuleFilteringPreview data={activeOutputPreview} />;
      case "selecting_rules":
        return <RuleSelectionPreview data={activeOutputPreview} />;
      case "score_scaling":
        return <ScoreScalingPreview data={activeOutputPreview} />;
      case "report_generation":
        return <ReportGenerationPreview data={activeOutputPreview} />;
      default:
        return <GenericPreview data={activeOutputPreview} />;
    }
  };

  // 阶段图标映射
  const stageIcons: Record<string, React.ReactNode> = {
    data_loading: <Database className="h-4 w-4" />,
    preprocessing: <Database className="h-4 w-4" />,
    woe_binning: <BarChart3 className="h-4 w-4" />,
    feature_selection: <Filter className="h-4 w-4" />,
    feature_engineering: <Filter className="h-4 w-4" />,
    model_training: <Brain className="h-4 w-4" />,
    model_evaluation: <Target className="h-4 w-4" />,
    score_scaling: <Target className="h-4 w-4" />,
    report_generation: <FileText className="h-4 w-4" />,
  };

  return (
    <div className={cn("flex flex-col h-full bg-white dark:bg-gray-950", className)}>
      {/* 头部 */}
      <div className="flex items-center justify-between px-4 py-3 border-b">
        <div className="flex items-center gap-2">
          {onBack && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setEditMode("preview");
                onBack();
              }}
              className="h-7 w-7 p-0"
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
          )}
          {stageIcons[stageId] || <Database className="h-4 w-4 text-gray-400" />}
          <span className="text-sm font-medium">{stageName}</span>
          {status && (
            <Badge 
              variant="outline" 
              className={cn(
                "text-xs",
                status === "completed" && "border-green-500 text-green-600",
                status === "running" && "border-blue-500 text-blue-600"
              )}
            >
              {status === "completed" ? "已完成" : status === "running" ? "执行中" : status}
            </Badge>
          )}
          {/* 执行时间显示 */}
          {executionTimeMs != null && status === "completed" && (
            <span className="text-xs text-gray-400 ml-1">
              ({formatExecutionTime(executionTimeMs)})
            </span>
          )}
        </div>

        {/* 专家模式：编辑模式切换标签 + 版本选择器 */}
        {isExpertMode && (
          <div className="flex items-center gap-1 flex-wrap">
            <Button
              variant={editMode === "preview" ? "secondary" : "ghost"}
              size="sm"
              onClick={() => setEditMode("preview")}
              className="h-6 px-2 text-xs"
            >
              结果
            </Button>
            {stageData?.params && Object.keys(stageData.params).length > 0 && (
              <Button
                variant={editMode === "params" ? "secondary" : "ghost"}
                size="sm"
                onClick={() => setEditMode("params")}
                className="h-6 px-2 text-xs"
              >
                <Settings className="h-3 w-3 mr-1" />
                参数
              </Button>
            )}
            {stageData?.code && (
              <Button
                variant={editMode === "code" ? "secondary" : "ghost"}
                size="sm"
                onClick={() => setEditMode("code")}
                className="h-6 px-2 text-xs"
              >
                <Code2 className="h-3 w-3 mr-1" />
                代码
              </Button>
            )}
            {/* 版本历史选择器（有快照时显示） */}
            <StageVersionSelector
              snapshots={snapshots}
              selectedVersion={selectedVersion}
              onChange={(v) => {
                setSelectedVersion(v);
                // 切换到历史版本时强制显示结果 tab
                if (v !== null) setEditMode("preview");
              }}
              disabled={status === "running"}
            />
          </div>
        )}
      </div>

      {/* 主内容区 */}
      <div className="flex-1 overflow-auto p-4">
        {editMode === "preview" && (
          <>
            {/* 历史版本 banner */}
            {activeSnapshot && (
              <div className="mb-3 rounded-lg border border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-950/20 px-3 py-2 text-xs text-blue-700 dark:text-blue-300 flex items-center justify-between">
                <span>
                  📸 历史快照 v{activeSnapshot.version}
                  {activeSnapshot.completed_at
                    ? ` · ${new Date(activeSnapshot.completed_at).toLocaleString("zh-CN", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" })}`
                    : ""}
                  {activeSnapshot.retry_reason ? ` · ${activeSnapshot.retry_reason}` : ""}
                </span>
                {onRetryStage && (
                  <button
                    className="ml-3 underline text-blue-600 dark:text-blue-400 hover:text-blue-800 shrink-0"
                    onClick={() => onRetryStage(stageId, activeSnapshot.params_used as Record<string, any>, "回滚到v" + activeSnapshot.version)}
                  >
                    用此版本参数重跑
                  </button>
                )}
              </div>
            )}
            {renderPreview()}
            
            {/* AI分析区域：专家模式（内部分析）或自动模式（外部传入分析） */}
            {/* 专家模式：阶段完成且有输出时显示 */}
            {/* 自动模式：有外部分析结果或正在分析时显示 */}
            {((isExpertMode && status === "completed" && outputPreview) || 
              (!isExpertMode && (externalAiAnalysis !== undefined || isExternalAnalyzing))) && (
              <div className="mt-4 border-t pt-4">
                <div 
                  className="flex items-center justify-between cursor-pointer"
                  onClick={() => setAnalysisExpanded(!analysisExpanded)}
                >
                  <div className="flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-purple-500" />
                    <span className="text-sm font-medium text-purple-700 dark:text-purple-300">
                      AI 分析评估
                    </span>
                    {(isAnalyzing || isExternalAnalyzing) && (
                      <Loader2 className="h-3 w-3 animate-spin text-purple-500" />
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    {/* 专家模式：内部重新分析按钮 */}
                    {isExpertMode && !isAnalyzing && aiAnalysis && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={async (e) => {
                          e.stopPropagation();
                          // Phase 14: 清除持久化缓存，等待删除完成后再重新调用 LLM
                          // 这避免了删除操作和保存操作的竞态条件
                          if (recordId) {
                            deleteCachedAnalysis(recordId, stageId);
                            try {
                              await deleteAnalysisFromAPI(recordId, stageId);
                            } catch {
                              // 删除失败不阻塞重新分析
                            }
                          }
                          setHasTriggeredAnalysis(false);
                          setAiAnalysis("");
                          // Phase 14: 直接调用，不需要 setTimeout，因为版本号机制已经处理了竞态
                          performAIAnalysis();
                        }}
                        className="h-6 px-2 text-xs text-purple-600 hover:text-purple-700"
                      >
                        <RotateCcw className="h-3 w-3 mr-1" />
                        重新分析
                      </Button>
                    )}
                    {/* 自动模式：外部重新分析按钮 */}
                    {!isExpertMode && externalAiAnalysis && !isExternalAnalyzing && onExternalReanalyze && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          onExternalReanalyze();
                        }}
                        className="h-6 px-2 text-xs text-purple-600 hover:text-purple-700"
                      >
                        <RotateCcw className="h-3 w-3 mr-1" />
                        重新分析
                      </Button>
                    )}
                    {analysisExpanded ? (
                      <ChevronUp className="h-4 w-4 text-gray-400" />
                    ) : (
                      <ChevronDown className="h-4 w-4 text-gray-400" />
                    )}
                  </div>
                </div>
                
                {analysisExpanded && (
                  <div className="mt-3 p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg border border-purple-100 dark:border-purple-800">
                    {/* 专家模式：使用内部状态 */}
                    {isExpertMode ? (
                      <>
                        {isAnalyzing && !aiAnalysis ? (
                          <div className="flex items-center justify-center py-4">
                            <Loader2 className="h-5 w-5 animate-spin text-purple-500 mr-2" />
                            <span className="text-sm text-purple-600 dark:text-purple-400">
                              正在分析阶段结果...
                            </span>
                          </div>
                        ) : aiAnalysis ? (
                          <div className="prose prose-sm dark:prose-invert max-w-none text-gray-700 dark:text-gray-300">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                              {aiAnalysis}
                            </ReactMarkdown>
                          </div>
                        ) : (
                          <div className="text-center py-4">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => performAIAnalysis()}
                              disabled={!selectedModel}
                              className="text-purple-600 border-purple-300 hover:bg-purple-100"
                            >
                              <Sparkles className="h-3 w-3 mr-1" />
                              生成AI分析
                            </Button>
                            {!selectedModel && (
                              <p className="text-xs text-gray-400 mt-2">请先选择模型</p>
                            )}
                          </div>
                        )}
                      </>
                    ) : (
                      /* 自动模式：使用外部传入的分析结果 */
                      <>
                        {isExternalAnalyzing && !externalAiAnalysis ? (
                          <div className="flex items-center justify-center py-4">
                            <Loader2 className="h-5 w-5 animate-spin text-purple-500 mr-2" />
                            <span className="text-sm text-purple-600 dark:text-purple-400">
                              正在分析任务结果...
                            </span>
                          </div>
                        ) : externalAiAnalysis ? (
                          <div className="prose prose-sm dark:prose-invert max-w-none text-gray-700 dark:text-gray-300">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                              {externalAiAnalysis}
                            </ReactMarkdown>
                          </div>
                        ) : (
                          <div className="text-center py-4 text-gray-500 text-sm">
                            点击"AI 分析评估"按钮开始分析
                          </div>
                        )}
                      </>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* AI 参数建议卡片（流式完成后、专家模式、非历史版本时展示） */}
            {isExpertMode && !activeSnapshot && suggestedParams && Object.keys(suggestedParams).length > 0 && (
              <SuggestedParamsCard
                suggestedParams={suggestedParams}
                currentParams={stageData?.params || {}}
                isRetrying={status === "running"}
                onApplyOnly={(merged) => {
                  setLocalParams(merged as Record<string, any>);
                  setEditMode("params");
                }}
                onApplyAndRetry={(merged) => {
                  setLocalParams(merged as Record<string, any>);
                  onRetryStage?.(stageId, merged as Record<string, any>, "接受AI建议");
                }}
              />
            )}
          </>
        )}
        
        {editMode === "params" && stageData?.params && (
          <div className="space-y-3">
            <div className="text-sm text-gray-600 dark:text-gray-400">
              调整参数后，点击"应用并重试"将使用新参数重新执行此阶段
            </div>
            {/* 根据是否有参数元数据决定显示表单还是JSON编辑器 */}
            {hasParamsMeta && paramsEditMode === "form" ? (
              <StageParamsForm
                paramsMeta={stageData.params_meta!}
                values={localParams}
                onChange={(newParams) => {
                  setIsUserEditing(true);
                  setLocalParams(newParams);
                }}
                readOnly={false}
                isDarkMode={isDarkMode}
                title="阶段参数"
                showJsonToggle={true}
                onToggleJsonMode={() => setParamsEditMode("json")}
                columns={effectiveColumns}
                columnsLoading={effectiveColumnsLoading}
              />
            ) : (
              <div className="space-y-2">
                {hasParamsMeta && (
                  <div className="flex justify-end">
                    <button
                      onClick={() => setParamsEditMode("form")}
                      className="text-xs text-blue-500 hover:text-blue-600 flex items-center gap-1"
                    >
                      <Settings className="w-3 h-3" />
                      切换到表单模式
                    </button>
                  </div>
                )}
                <StageParameterEditor
                  params={stageData.params}
                  onChange={(newParams) => {
                    setIsUserEditing(true);
                    setLocalParams(newParams);
                  }}
                  readOnly={false}
                  height={300}
                  isDarkMode={isDarkMode}
                  title="阶段参数 (JSON)"
                />
              </div>
            )}
          </div>
        )}

        {editMode === "code" && stageData?.code && (
          <div className="space-y-3">
            <div className="text-sm text-yellow-600 dark:text-yellow-400">
              Pipeline 模式下代码为只读。代码编辑功能已移除。
            </div>
            <StageCodeEditor
              code={stageData.code}
              onChange={setLocalCode}
              readOnly={true}
              executable={false}
              sessionId={sessionId}
              stageId={stageId}
              height={350}
              showOutput={false}
              isDarkMode={isDarkMode}
              title="只读代码"
              showReset={false}
            />
          </div>
        )}
      </div>


      {/* 底部操作区 */}
      <div className="px-4 py-2 border-t bg-gray-50 dark:bg-gray-900/30">
        {isExpertMode && editMode !== "preview" ? (
          <div className="flex items-center justify-between">
            <p className="text-xs text-gray-500">
              {editMode === "params" 
                ? "💡 修改参数后点击\"应用并重试\"，当前阶段将使用新参数重新执行" 
                : "💡 修改代码后可直接运行或重试阶段"}
            </p>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setEditMode("preview");
                  setIsUserEditing(false); // 取消时重置编辑状态
                }}
                className="h-7 text-xs"
              >
                取消
              </Button>
              {onRetryStage && (
                <Button
                  size="sm"
                  onClick={() => {
                    // Phase 15: 清除该阶段的 AI 评估缓存，因为阶段将重新执行并产生新的输出
                    // 重试后需要重新生成 AI 评估，而不是使用旧的缓存
                    if (recordId) {
                      deleteCachedAnalysis(recordId, stageId);
                      deleteAnalysisFromAPI(recordId, stageId).catch(() => {});
                    }
                    
                    // Phase 16: 保存当前 outputPreview 的引用，用于检测数据是否真正更新
                    // 只有当 outputPreview 变化后才触发 AI 分析，避免使用旧数据
                    retryPendingOutputRef.current = outputPreview;
                    
                    // 重置 AI 分析状态，确保重试后重新生成
                    setAiAnalysis("");
                    setHasTriggeredAnalysis(false);
                    // 清除参数建议（重试后重新生成）
                    setSuggestedParams(null);
                    
                    // 触发阶段重试 - 直接传递参数给 retryStage API
                    // 不再依赖 onEditParams 的异步更新，避免竞态条件
                    if (editMode === "params") {
                      onRetryStage(stageId, localParams);
                    } else {
                      onRetryStage(stageId);
                    }
                    setEditMode("preview");
                    setIsUserEditing(false); // 重置编辑状态
                  }}
                  className="h-7 text-xs bg-blue-500 hover:bg-blue-600"
                >
                  <RotateCcw className="h-3 w-3 mr-1" />
                  应用并重试
                </Button>
              )}
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-between">
            <p className="text-xs text-gray-500">
              📊 此面板显示阶段执行的中间结果预览
            </p>
            <p className="text-xs text-blue-600">
              💡 如需重试此阶段，请切换到参数或代码标签页
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default StageOutputPreview;
