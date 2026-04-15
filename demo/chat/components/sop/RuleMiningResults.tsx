"use client";

import React, { useState, useEffect, useMemo, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Target,
  Download,
  CheckCircle2,
  TrendingUp,
  BarChart3,
  List,
  Loader2,
  X,
  Activity,
  Percent,
  HelpCircle,
  AlertTriangle,
  CheckCircle,
  ShieldCheck,
  DollarSign,
  ChevronDown,
  ChevronRight,
  Settings2,
  Layers,
  GitBranch,
  Info,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Database,
  Calendar,
} from "lucide-react";
import { sopService, ExecutionResult, ExecutionStatus, StageProgress } from "@/lib/sopService";
import { getApiUrl } from "@/lib/config";
import { useToast } from "@/hooks/use-toast";
import { cn, unwrapData } from "@/lib/utils";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { AmountAnalysisPanel } from "./AmountAnalysisPanel";

// ========== 简单SVG图表组件 ==========

// 累计指标曲线图
function CumulativeMetricsChart({ data }: { 
  data: { 
    labels: string[]; 
    recall: number[]; 
    hit_rate: number[]; 
    lift: number[];
    n_rules: number;
  } 
}) {
  const width = 560;
  const height = 200;
  const padding = 40;
  
  const { recallPoints, hitRatePoints, liftPoints, maxLift } = useMemo(() => {
    if (!data.labels || data.labels.length === 0) {
      return { recallPoints: "", hitRatePoints: "", liftPoints: "", maxLift: 1 };
    }
    
    const n = data.labels.length;
    const xScale = (width - 2 * padding) / Math.max(1, n - 1);
    const yScale = (height - 2 * padding) / 1; // recall/hit_rate are 0-1
    
    // Find max lift for scaling
    const maxL = Math.max(...data.lift, 1);
    const liftYScale = (height - 2 * padding) / maxL;
    
    let recallPts = "";
    let hitRatePts = "";
    let liftPts = "";
    
    for (let i = 0; i < n; i++) {
      const x = padding + i * xScale;
      const yRecall = height - padding - (data.recall[i] || 0) * yScale;
      const yHitRate = height - padding - (data.hit_rate[i] || 0) * yScale;
      const yLift = height - padding - (data.lift[i] || 0) * liftYScale;
      
      recallPts += `${x},${yRecall} `;
      hitRatePts += `${x},${yHitRate} `;
      liftPts += `${x},${yLift} `;
    }
    
    return { 
      recallPoints: recallPts.trim(), 
      hitRatePoints: hitRatePts.trim(), 
      liftPoints: liftPts.trim(),
      maxLift: maxL 
    };
  }, [data]);
  
  if (!data.labels || data.labels.length === 0) {
    return <div className="text-center text-gray-500 py-8">暂无图表数据</div>;
  }
  
  return (
    <svg width={width} height={height} className="mx-auto">
      {/* 背景网格 */}
      <defs>
        <pattern id="cumGrid" width="50" height="32" patternUnits="userSpaceOnUse">
          <path d="M 50 0 L 0 0 0 32" fill="none" stroke="#e5e7eb" strokeWidth="0.5"/>
        </pattern>
      </defs>
      <rect x={padding} y={padding} width={width - 2*padding} height={height - 2*padding} fill="url(#cumGrid)"/>
      
      {/* 召回率曲线 */}
      <polyline points={recallPoints} fill="none" stroke="#22c55e" strokeWidth="2"/>
      
      {/* 命中率曲线 */}
      <polyline points={hitRatePoints} fill="none" stroke="#3b82f6" strokeWidth="2"/>
      
      {/* 提升倍数曲线 */}
      <polyline points={liftPoints} fill="none" stroke="#f59e0b" strokeWidth="2" strokeDasharray="4,2"/>
      
      {/* 数据点标记 */}
      {data.labels.map((_, i) => {
        const x = padding + i * (width - 2 * padding) / Math.max(1, data.labels.length - 1);
        const yRecall = height - padding - (data.recall[i] || 0) * (height - 2 * padding);
        const yHitRate = height - padding - (data.hit_rate[i] || 0) * (height - 2 * padding);
        return (
          <g key={i}>
            <circle cx={x} cy={yRecall} r="3" fill="#22c55e"/>
            <circle cx={x} cy={yHitRate} r="3" fill="#3b82f6"/>
          </g>
        );
      })}
      
      {/* 坐标轴 */}
      <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="#374151" strokeWidth="1"/>
      <line x1={padding} y1={padding} x2={padding} y2={height - padding} stroke="#374151" strokeWidth="1"/>
      
      {/* X轴标签 */}
      <text x={width / 2} y={height - 5} textAnchor="middle" fontSize="10" fill="#6b7280">规则数量</text>
      
      {/* Y轴标签 */}
      <text x={8} y={height / 2} textAnchor="middle" fontSize="10" fill="#6b7280" transform={`rotate(-90, 8, ${height/2})`}>比例</text>
      
      {/* 图例 */}
      <g transform={`translate(${width - 180}, 15)`}>
        <line x1="0" y1="0" x2="15" y2="0" stroke="#22c55e" strokeWidth="2"/>
        <text x="20" y="3" fontSize="9" fill="#6b7280">召回率</text>
        <line x1="55" y1="0" x2="70" y2="0" stroke="#3b82f6" strokeWidth="2"/>
        <text x="75" y="3" fontSize="9" fill="#6b7280">命中率</text>
        <line x1="110" y1="0" x2="125" y2="0" stroke="#f59e0b" strokeWidth="2" strokeDasharray="4,2"/>
        <text x="130" y="3" fontSize="9" fill="#6b7280">提升倍数</text>
      </g>
    </svg>
  );
}

// 规则分布散点图
function RuleDistributionChart({ data }: { 
  data: { 
    hit_rate: number[]; 
    recall: number[]; 
    lift: number[];
    n_rules: number;
  } 
}) {
  const width = 280;
  const height = 200;
  const padding = 35;
  
  const points = useMemo(() => {
    if (!data.hit_rate || data.hit_rate.length === 0) return [];
    
    const maxHitRate = Math.max(...data.hit_rate, 0.01);
    const maxRecall = Math.max(...data.recall, 0.01);
    const maxLift = Math.max(...data.lift, 1);
    
    return data.hit_rate.map((hr, i) => ({
      x: padding + (hr / maxHitRate) * (width - 2 * padding),
      y: height - padding - (data.recall[i] / maxRecall) * (height - 2 * padding),
      r: 3 + (data.lift[i] / maxLift) * 5,
      lift: data.lift[i]
    }));
  }, [data]);
  
  if (!data.hit_rate || data.hit_rate.length === 0) {
    return <div className="text-center text-gray-500 py-8">暂无分布数据</div>;
  }
  
  return (
    <svg width={width} height={height} className="mx-auto">
      {/* 背景 */}
      <rect x={padding} y={padding} width={width - 2*padding} height={height - 2*padding} fill="#f9fafb"/>
      
      {/* 散点 */}
      {points.map((p, i) => (
        <circle 
          key={i} 
          cx={p.x} 
          cy={p.y} 
          r={p.r} 
          fill={p.lift >= 5 ? "#22c55e" : p.lift >= 3 ? "#3b82f6" : "#9ca3af"}
          opacity={0.7}
        />
      ))}
      
      {/* 坐标轴 */}
      <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="#374151" strokeWidth="1"/>
      <line x1={padding} y1={padding} x2={padding} y2={height - padding} stroke="#374151" strokeWidth="1"/>
      
      {/* 标签 */}
      <text x={width / 2} y={height - 5} textAnchor="middle" fontSize="10" fill="#6b7280">命中率</text>
      <text x={10} y={height / 2} textAnchor="middle" fontSize="10" fill="#6b7280" transform={`rotate(-90, 10, ${height/2})`}>召回率</text>
      
      {/* 图例 */}
      <g transform={`translate(${width - 80}, ${padding + 5})`}>
        <circle cx="5" cy="0" r="4" fill="#22c55e" opacity="0.7"/>
        <text x="12" y="3" fontSize="8" fill="#6b7280">Lift≥5</text>
        <circle cx="5" cy="12" r="4" fill="#3b82f6" opacity="0.7"/>
        <text x="12" y="15" fontSize="8" fill="#6b7280">Lift≥3</text>
        <circle cx="5" cy="24" r="4" fill="#9ca3af" opacity="0.7"/>
        <text x="12" y="27" fontSize="8" fill="#6b7280">Lift&lt;3</text>
      </g>
    </svg>
  );
}

interface RuleMiningResultsProps {
  executionId: string;
  recordId?: string;         // 任务记录ID（用于AI分析持久化）
  mode?: 'auto' | 'expert';  // 交互模式
  className?: string;
}

interface RuleData {
  rule: string;
  recall: number;
  bad_rate: number;
  lift: number;
  hit_rate: number;
  cumulative_recall?: number;
  cumulative_hit_rate?: number;
}

// 规则筛选状态类型（用于规则筛选Tab）
interface RuleWithStatus {
  rule: string;
  recall: number | null;
  bad_rate: number | null;
  lift: number | null;
  hit_rate: number | null;
  direction_valid: boolean;
  hit_rate_valid: boolean | null;
  lift_valid: boolean | null;
  is_valid: boolean;
  is_optimal: boolean;
  filter_reason: string;
}

interface ResultSummary {
  total_rules: number;
  filtered_rules: number;
  optimal_rules: number;
  cumulative_recall: number;
  cumulative_hit_rate: number;
  avg_lift: number;
}


// 规则质量验证报告类型（行业标准版）
interface ValidationReport {
  // 核心指标
  discrimination_report?: {
    avg_lift: number;
    min_lift: number;
    max_lift: number;
    lift_distribution?: { excellent: number; good: number; acceptable: number; poor: number };
    status: string;
    thresholds?: { excellent: number; good: number; acceptable: number };
  };
  recall_report?: {
    cumulative_recall: number;
    individual_recalls?: number[];
    total_bad_samples?: number;
    status: string;
    thresholds?: { excellent: number; good: number; acceptable: number };
  };
  // 辅助指标
  coverage_report: {
    total_coverage: number;
    status: string;
    thresholds?: { min: number; max: number; optimal_min?: number; optimal_max?: number };
  };
  complexity_report?: {
    avg_complexity: number;
    max_complexity: number;
    complexity_distribution?: { simple: number; moderate: number; complex: number };
    status: string;
    thresholds?: { optimal: number; max: number };
  };
  conflict_report: {
    conflict_rate: number;
    status: string;
  };
  overlap_report: {
    avg_overlap: number;
    status: string;
    high_overlap_pairs?: Array<{ rule1: string; rule2: string; jaccard: number }>;
  };
  redundancy_report: {
    redundant_count: number;
    status: string;
  };
  warnings: string[];
  quality_score: number;
  score_breakdown?: {
    discrimination?: number;
    recall?: number;
    coverage?: number;
    independence?: number;
    complexity?: number;
  };
}

// 规则PSI报告类型
interface PSIReport {
  rule: string;
  hit_rate_base: number | null;
  hit_rate_compare: number | null;
  psi: number | null;
  stability: string;
}

// 决策树节点类型
interface TreeNode {
  id: number;
  samples: number;
  bad_count: number;
  good_count: number;
  bad_rate: number;
  is_leaf: boolean;
  feature?: string;
  feature_index?: number;
  threshold?: number;
  predicted_class?: string;
  left?: TreeNode;
  right?: TreeNode;
}

// 决策树结构类型
interface TreeStructure {
  tree: TreeNode;
  n_features: number;
  n_classes: number;
  max_depth: number;
  n_leaves: number;
  feature_names: string[] | null;
  class_names: string[];
}

// 规则来源统计类型（组合树模式）
interface RuleSourceStats {
  total_rules: number;
  total_combinations: number;
  combination_stats: Array<{
    combination: string;
    rule_count: number;
    percentage: number;
  }>;
  feature_importance: Array<{
    feature: string;
    rule_count: number;
    percentage: number;
  }>;
}

export function RuleMiningResults({
  executionId,
  recordId,
  mode = 'auto',
  className,
}: RuleMiningResultsProps) {
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ExecutionResult | null>(null);
  const [activeTab, setActiveTab] = useState("charts");
  // 样本及特征Tab所需的stages数据
  const [stagesData, setStagesData] = useState<Record<string, StageProgress> | null>(null);


  // 加载执行结果和stages数据
  useEffect(() => {
    // 🔧 修复竞态条件：当executionId变化时，取消旧的异步请求
    let isCancelled = false;
    
    const loadResult = async () => {
      try {
        setLoading(true);
        setError(null);
        
        let data: ExecutionResult;
        let stages: Record<string, StageProgress> | null = null;
        
        console.log('[RuleMiningResults] Loading data for executionId:', executionId);
        
        // 检查是否是历史记录ID（rec:前缀）
        if (executionId.startsWith("rec:")) {
          const recId = executionId.substring(4); // 移除"rec:"前缀
          console.log('[RuleMiningResults] Loading from history record:', recId);
          const historyResult = await sopService.getTaskHistoryResult(recId);
          
          // 🔧 检查是否已取消（executionId已变化）
          if (isCancelled) {
            console.log('[RuleMiningResults] Request cancelled (executionId changed)');
            return;
          }
          
          console.log('[RuleMiningResults] historyResult keys:', Object.keys(historyResult));
          console.log('[RuleMiningResults] historyResult.stages:', historyResult.stages);
          console.log('[RuleMiningResults] typeof historyResult.stages:', typeof historyResult.stages);
          // 将历史结果转换为ExecutionResult格式
          data = {
            execution_id: recId,
            status: "completed",
            outputs: historyResult.result || {},
          } as ExecutionResult;
          // 直接从getTaskHistoryResult响应中获取stages数据（后端已一次性返回）
          // 这样避免了额外调用getTaskHistoryDetail失败的问题
          if (historyResult.stages && Object.keys(historyResult.stages).length > 0) {
            stages = historyResult.stages as Record<string, StageProgress>;
            console.log('[RuleMiningResults] Stages from history result:', Object.keys(stages));
          } else {
            console.log('[RuleMiningResults] No stages in history result, historyResult.stages =', historyResult.stages);
            console.log('[RuleMiningResults] Trying getTaskHistoryDetail...');
            // 后备方案：尝试从getTaskHistoryDetail获取（兼容旧API）
            try {
              const historyDetail = await sopService.getTaskHistoryDetail(recId);
              if (isCancelled) return; // 🔧 再次检查
              console.log('[RuleMiningResults] History detail stages:', historyDetail.stages ? Object.keys(historyDetail.stages) : 'null');
              stages = historyDetail.stages as Record<string, StageProgress> || null;
            } catch (e) {
              console.warn('[RuleMiningResults] Failed to get history stages:', e);
              // 静默失败，旧历史记录可能没有stages数据
            }
          }
        } else {
          data = await sopService.getExecutionResult(executionId);
          
          // 🔧 检查是否已取消
          if (isCancelled) {
            console.log('[RuleMiningResults] Request cancelled (executionId changed)');
            return;
          }
          
          console.log('[RuleMiningResults] Execution result record_id:', data.record_id);
          // 从历史记录获取stages数据
          // 已完成任务的ExecutionContext通常已被清理，只能从历史记录获取
          if (data.record_id) {
            try {
              // 优先使用getTaskHistoryResult（一次性返回result和stages）
              const historyResult = await sopService.getTaskHistoryResult(data.record_id);
              if (isCancelled) return; // 🔧 再次检查
              if (historyResult.stages && Object.keys(historyResult.stages).length > 0) {
                stages = historyResult.stages as Record<string, StageProgress>;
                console.log('[RuleMiningResults] Stages from history result:', Object.keys(stages));
              } else {
                // 后备方案
                const historyDetail = await sopService.getTaskHistoryDetail(data.record_id);
                if (isCancelled) return; // 🔧 再次检查
                console.log('[RuleMiningResults] History detail stages:', historyDetail.stages ? Object.keys(historyDetail.stages) : 'null');
                stages = historyDetail.stages as Record<string, StageProgress> || null;
              }
            } catch (e) {
              console.warn('[RuleMiningResults] Failed to get history stages:', e);
              // 静默失败，旧历史记录可能没有stages数据
            }
          } else {
            console.warn('[RuleMiningResults] No record_id, cannot fetch stages');
          }
          // 注意：不再调用 getExecutionStatus，因为已完成任务的执行上下文已被清理
          // 如果需要stages数据但record_id不存在，说明是非常旧的任务，无法获取stages
        }
        
        // 🔧 最终状态更新前再次检查
        if (isCancelled) {
          console.log('[RuleMiningResults] Request cancelled before state update');
          return;
        }
        
        console.log('[RuleMiningResults] Final stagesData:', stages ? Object.keys(stages) : 'null');
        if (stages?.preprocessing) {
          console.log('[RuleMiningResults] preprocessing output_preview:', stages.preprocessing.output_preview ? 'exists' : 'null');
        }
        
        setResult(data);
        setStagesData(stages);
      } catch (err) {
        // 🔧 错误处理前也检查取消状态
        if (isCancelled) return;
        console.error("Failed to load result:", err);
        setError("加载结果失败");
      } finally {
        // 🔧 finally中也检查，避免不必要的状态更新
        if (!isCancelled) {
          setLoading(false);
        }
      }
    };

    if (executionId) {
      loadResult();
    }
    
    // 🔧 清理函数：当executionId变化或组件卸载时取消旧请求
    return () => {
      isCancelled = true;
    };
  }, [executionId]);

  // 解析结果数据
  const parseResults = () => {
    if (!result?.outputs) return null;

    const outputs = result.outputs;
    // 使用从 @/lib/utils 导入的共享 unwrapData 函数
    
    // 最优规则 - 解包 dataframe 格式
    const optimalRulesRaw = unwrapData(outputs.optimal_rules);
    const optimalRules: RuleData[] = Array.isArray(optimalRulesRaw) ? optimalRulesRaw : [];
    
    // 全部规则 - 解包 dataframe 格式
    const allRulesRaw = unwrapData(outputs.all_rules);
    const allRules: RuleData[] = Array.isArray(allRulesRaw) ? allRulesRaw : [];
    
    // 过滤后规则 - 解包 dataframe 格式
    const filteredRulesRaw = unwrapData(outputs.filtered_rules);
    const filteredRules: RuleData[] = Array.isArray(filteredRulesRaw) ? filteredRulesRaw : [];
    
    // 图表数据 - 解包 dict 格式
    const chartDataRaw = unwrapData(outputs.chart_data);
    const chartData = chartDataRaw && typeof chartDataRaw === 'object' ? chartDataRaw as Record<string, unknown> : null;
    
    // 规则质量验证报告 - 解包 dict 格式
    const validationReportRaw = unwrapData(outputs.validation_report);
    const validationReport: ValidationReport | null = validationReportRaw as ValidationReport | null;
    
    // 规则PSI报告 - 解包 dataframe 格式
    const psiReportRaw = unwrapData(outputs.psi_report);
    const psiReport: PSIReport[] = Array.isArray(psiReportRaw) ? psiReportRaw : [];
    
    // 金额维度分析 - 解包 dict 格式 (新增)
    const amountAnalysisRaw = unwrapData(outputs.amount_analysis);
    const amountAnalysis = amountAnalysisRaw && typeof amountAnalysisRaw === 'object' ? amountAnalysisRaw : null;
    
    // 先验规则分析 - 解包 dict 格式
    const priorAnalysisRaw = unwrapData(outputs.prior_analysis);
    const priorAnalysis = priorAnalysisRaw && typeof priorAnalysisRaw === 'object' ? priorAnalysisRaw : null;
    
    // 决策树结构 - 解包 dict 格式 (新增)
    const treeStructureRaw = unwrapData(outputs.tree_structure);
    const treeStructure: TreeStructure | null = treeStructureRaw && typeof treeStructureRaw === 'object' ? treeStructureRaw as TreeStructure : null;
    
    // 规则来源统计 - 组合树模式时使用（替代决策树可视化）
    const ruleSourceStatsRaw = unwrapData(outputs.rule_source_stats);
    const ruleSourceStats: RuleSourceStats | null = ruleSourceStatsRaw && typeof ruleSourceStatsRaw === 'object' ? ruleSourceStatsRaw as RuleSourceStats : null;
    
    // 全量规则筛选状态 - 用于规则筛选Tab（新增）
    const allRulesWithStatusRaw = unwrapData(outputs.all_rules_with_status);
    const allRulesWithStatus: RuleWithStatus[] = Array.isArray(allRulesWithStatusRaw) ? allRulesWithStatusRaw : [];
    
    // P1-5: OOT 稳定性验证报告
    const ootStabilityReport = unwrapData(outputs.oot_stability_report) as Record<string, any> | null;
    
    // 摘要信息 - 优先从chart_data.summary获取
    const chartSummary = chartData?.summary as Record<string, number> | undefined;
    const summary: ResultSummary = {
      total_rules: outputs.total_rules_count || allRules.length,
      filtered_rules: outputs.filtered_rules_count || filteredRules.length,
      optimal_rules: chartSummary?.n_optimal_rules || optimalRules.length,
      cumulative_recall: chartSummary?.final_recall || 
        (optimalRules.length > 0 ? optimalRules[optimalRules.length - 1]?.cumulative_recall || 0 : 0),
      cumulative_hit_rate: chartSummary?.final_hit_rate ||
        (optimalRules.length > 0 ? optimalRules[optimalRules.length - 1]?.cumulative_hit_rate || 0 : 0),
      avg_lift: chartSummary?.final_lift ||
        (optimalRules.length > 0 ? optimalRules.reduce((sum, r) => sum + (r.lift || 0), 0) / optimalRules.length : 0),
    };

    return { optimalRules, allRules, filteredRules, allRulesWithStatus, summary, chartData, validationReport, psiReport, amountAnalysis, priorAnalysis, treeStructure, ruleSourceStats, ootStabilityReport };
  };

  const data = parseResults();

  // 生成Markdown报告
  const generateMarkdownReport = (): string => {
    let md = `# 规则挖掘分析报告\n\n`;
    md += `> 生成时间: ${new Date().toLocaleString()}\n\n`;
    md += `---\n\n`;
    
    // 执行摘要
    md += `## 1. 执行摘要\n\n`;
    md += `| 指标 | 值 |\n`;
    md += `|------|----|\n`;
    md += `| 最优规则数 | ${data.summary.optimal_rules} |\n`;
    md += `| 累计召回率 | ${(data.summary.cumulative_recall * 100).toFixed(2)}% |\n`;
    md += `| 累计命中率 | ${(data.summary.cumulative_hit_rate * 100).toFixed(2)}% |\n`;
    md += `| 平均提升度 | ${data.summary.avg_lift.toFixed(2)} |\n`;
    md += `\n`;
    
    // 最优规则列表
    if (data.optimalRules && data.optimalRules.length > 0) {
      md += `## 2. 最优规则列表\n\n`;
      md += `| 序号 | 规则条件 | 命中样本 | 坏账率 | 提升度 |\n`;
      md += `|------|----------|----------|--------|--------|\n`;
      data.optimalRules.slice(0, 20).forEach((rule: any, idx: number) => {
        const condition = rule.condition || rule.rule || '-';
        const hitCount = rule.hit_count || rule.sample_count || '-';
        const badRate = rule.bad_rate != null ? `${(rule.bad_rate * 100).toFixed(2)}%` : '-';
        const lift = rule.lift != null ? rule.lift.toFixed(2) : '-';
        md += `| ${idx + 1} | ${condition} | ${hitCount} | ${badRate} | ${lift} |\n`;
      });
      if (data.optimalRules.length > 20) {
        md += `\n*（仅展示前20条规则，共${data.optimalRules.length}条）*\n`;
      }
      md += `\n`;
    }
    
    // 质量验证
    if (data.validationReport) {
      md += `## 3. 质量验证\n\n`;
      md += `| 检查项 | 状态 | 说明 |\n`;
      md += `|--------|------|------|\n`;
      if (data.validationReport.checks) {
        data.validationReport.checks.forEach((check: any) => {
          const status = check.passed ? '✅ 通过' : '❌ 失败';
          md += `| ${check.name || '-'} | ${status} | ${check.message || '-'} |\n`;
        });
      }
      md += `\n`;
    }
    
    // PSI稳定性（psiReport是数组格式）
    if (data.psiReport && data.psiReport.length > 0) {
      md += `## 4. 稳定性分析 (PSI)\n\n`;
      md += `| 规则序号 | PSI值 | 稳定性 |\n`;
      md += `|----------|-------|--------|\n`;
      data.psiReport.slice(0, 10).forEach((item: any, idx: number) => {
        const psiValue = item.psi != null ? item.psi.toFixed(4) : '-';
        const stability = item.psi != null ? (item.psi < 0.1 ? '稳定' : item.psi < 0.25 ? '轻微变化' : '显著变化') : '-';
        md += `| ${idx + 1} | ${psiValue} | ${stability} |\n`;
      });
      if (data.psiReport.length > 10) {
        md += `\n*（仅展示前10条，共${data.psiReport.length}条）*\n`;
      }
      md += `\n`;
    }
    
    md += `---\n\n`;
    md += `*本报告由 CreditWise 自动生成*\n`;
    
    return md;
  };

  // 下载报告 - 支持HTML、JSON、Word、Excel、Markdown格式
  const handleDownloadReport = async (format: 'html' | 'json' | 'word' | 'excel' | 'markdown') => {
    // JSON格式 - 直接下载原始结果（统一命名格式与后端一致）
    if (format === 'json') {
      const text = JSON.stringify(result, null, 2);
      const blob = new Blob([text], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      
      // 统一命名格式：rule_mining_{timestamp}_{rec-id}.json
      const now = new Date();
      const timestamp = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}_${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}${String(now.getSeconds()).padStart(2, '0')}`;
      
      // 确定ID：优先使用 recordId，否则处理 executionId
      let idToUse: string;
      if (recordId) {
        idToUse = recordId;
      } else if (executionId.startsWith('rec:rec-')) {
        // rec:rec-xxx 格式 → 直接使用 rec-xxx
        idToUse = executionId.slice(4);
      } else if (executionId.startsWith('rec:')) {
        // rec:xxx 格式 → 转换为 rec-xxx
        idToUse = 'rec-' + executionId.slice(4);
      } else if (executionId.startsWith('rec-')) {
        // 已经是 rec-xxx 格式
        idToUse = executionId;
      } else {
        // exec-xxx 或其他格式，移除前缀并加上 rec-
        idToUse = 'rec-' + executionId.replace('exec-', '');
      }
      
      a.download = `rule_mining_${timestamp}_${idToUse}.json`;
      
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      toast({
        title: "下载成功",
        description: "JSON结果已下载",
      });
      return;
    }
    
    // Markdown格式 - 调用后端API生成（与Excel/Word保持一致的配置驱动）
    if (format === 'markdown') {
      try {
        const response = await fetch(getApiUrl('/sop/report/export'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ execution_id: executionId, format: 'markdown' })
        });
        const responseData = await response.json();
        
        if (responseData.success && responseData.content) {
          const blob = new Blob([responseData.content], { type: "text/markdown;charset=utf-8" });
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = responseData.filename || `rule_mining_report_${executionId}.md`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(url);
          
          toast({
            title: "下载成功",
            description: "Markdown报告已下载",
          });
        } else {
          toast({
            title: "下载失败",
            description: responseData.error || "生成报告失败",
            variant: "destructive",
          });
        }
      } catch (err) {
        toast({
          title: "下载失败",
          description: "网络错误，请重试",
          variant: "destructive",
        });
      }
      return;
    }

    try {
      const response = await fetch(getApiUrl('/sop/report/export'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ execution_id: executionId, format: format })
      });
      const responseData = await response.json();
      
        if (responseData.success && responseData.content) {
        if (format === 'html') {
          // 下载HTML文件并在新标签页预览
          const blob = new Blob([responseData.content], { type: 'text/html;charset=utf-8' });
          const url = URL.createObjectURL(blob);
          
          // 下载文件 - 使用后端返回的文件名
          const a = document.createElement('a');
          a.href = url;
          a.download = responseData.filename || `rule_mining_report_${executionId}.html`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          
          // 在新标签页预览
          const previewWindow = window.open('', '_blank');
          if (previewWindow) {
            previewWindow.document.write(responseData.content);
            previewWindow.document.close();
          }
          
          URL.revokeObjectURL(url);
          toast({
            title: "导出成功",
            description: 'HTML报告已下载并在新标签页打开预览',
          });
        } else if (format === 'excel') {
          // Excel格式 - base64解码后下载
          const binaryString = atob(responseData.content);
          const bytes = new Uint8Array(binaryString.length);
          for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
          }
          const blob = new Blob([bytes], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = responseData.filename || `rule_mining_report_${executionId}.xlsx`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(url);
          
          toast({
            title: "下载成功",
            description: "Excel报告已下载",
          });
        } else if (format === 'word') {
          // Word格式 - base64解码后下载
          const binaryString = atob(responseData.content);
          const bytes = new Uint8Array(binaryString.length);
          for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
          }
          const blob = new Blob([bytes], { type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" });
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = responseData.filename || `rule_mining_report_${executionId}.docx`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(url);
          
          toast({
            title: "下载成功",
            description: "Word报告已下载",
          });
        }
      } else {
        toast({
          title: "下载失败",
          description: responseData.error || "生成报告失败",
          variant: "destructive",
        });
      }
    } catch (err) {
      toast({
        title: "下载失败",
        description: "网络错误，请重试",
        variant: "destructive",
      });
    }
  };

  // 格式化百分比（统一1位小数）
  const formatPercent = (value: number | undefined) => {
    if (value === undefined || value === null) return "-";
    return `${(value * 100).toFixed(1)}%`;
  };

  // 格式化数字
  const formatNumber = (value: number | undefined, decimals: number = 2) => {
    if (value === undefined || value === null) return "-";
    return value.toFixed(decimals);
  };

  if (loading) {
    return (
      <Card className={cn("", className)}>
        <CardContent className="flex items-center justify-center py-12">
          <div className="flex flex-col items-center gap-2">
            <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
            <span className="text-sm text-gray-500">加载结果中...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error || !data) {
    return (
      <Card className={cn("border-red-200 dark:border-red-800", className)}>
        <CardContent className="flex items-center justify-center py-12">
          <div className="flex flex-col items-center gap-2 text-red-500">
            <X className="h-8 w-8" />
            <span className="text-sm">{error || "无法加载结果"}</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={cn("", className)}>
      {/* 结果标题行 - sticky 冻结在顶部 Tab 行下方 */}
      <CardHeader className="pb-3 sticky top-[41px] z-[5] bg-green-50 dark:bg-green-900/20 border-b border-green-100 dark:border-green-800/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-green-100 dark:bg-green-900/50 flex items-center justify-center">
              <CheckCircle2 className="h-5 w-5 text-green-600" />
            </div>
            <div>
              <CardTitle className="text-base">规则挖掘结果</CardTitle>
              <CardDescription className="text-xs">
                任务执行完成
              </CardDescription>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="sm" onClick={() => handleDownloadReport('markdown')} className="h-7 px-2 text-xs">
                    <Download className="h-3 w-3 mr-1" />
                    MD
                  </Button>
                </TooltipTrigger>
                <TooltipContent>下载Markdown报告</TooltipContent>
              </Tooltip>
            </TooltipProvider>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="sm" onClick={() => handleDownloadReport('excel')} className="h-7 px-2 text-xs">
                    <Download className="h-3 w-3 mr-1" />
                    Excel
                  </Button>
                </TooltipTrigger>
                <TooltipContent>下载Excel报告（多Sheet）</TooltipContent>
              </Tooltip>
            </TooltipProvider>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="sm" onClick={() => handleDownloadReport('word')} className="h-7 px-2 text-xs">
                    <Download className="h-3 w-3 mr-1" />
                    Word
                  </Button>
                </TooltipTrigger>
                <TooltipContent>下载Word报告（可编辑文档）</TooltipContent>
              </Tooltip>
            </TooltipProvider>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="sm" onClick={() => handleDownloadReport('html')} className="h-7 px-2 text-xs">
                    <Download className="h-3 w-3 mr-1" />
                    HTML
                  </Button>
                </TooltipTrigger>
                <TooltipContent>下载HTML报告（可在浏览器中打开）</TooltipContent>
              </Tooltip>
            </TooltipProvider>
            <Button variant="outline" size="sm" onClick={() => handleDownloadReport('json')} className="h-7 px-2 text-xs">
              JSON
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* 摘要卡片 - 4列布局 */}
        <div className="grid grid-cols-4 gap-3">
          <div className="p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
            <div className="flex items-center gap-2 mb-1">
              <List className="h-4 w-4 text-blue-600" />
              <span className="text-xs text-blue-600 font-medium">最优规则数</span>
            </div>
            <span className="text-2xl font-bold text-blue-700 dark:text-blue-300">
              {data.summary.optimal_rules}
            </span>
          </div>
          <div className="p-3 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800">
            <div className="flex items-center gap-2 mb-1">
              <TrendingUp className="h-4 w-4 text-green-600" />
              <span className="text-xs text-green-600 font-medium">累计召回率</span>
            </div>
            <span className="text-2xl font-bold text-green-700 dark:text-green-300">
              {formatPercent(data.summary.cumulative_recall)}
            </span>
          </div>
          <div className="p-3 rounded-lg bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800">
            <div className="flex items-center gap-2 mb-1">
              <BarChart3 className="h-4 w-4 text-purple-600" />
              <span className="text-xs text-purple-600 font-medium">累计命中率/覆盖率</span>
            </div>
            <span className="text-2xl font-bold text-purple-700 dark:text-purple-300">
              {formatPercent(data.summary.cumulative_hit_rate)}
            </span>
          </div>
          <div className="p-3 rounded-lg bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800">
            <div className="flex items-center gap-2 mb-1">
              <Activity className="h-4 w-4 text-orange-600" />
              <span className="text-xs text-orange-600 font-medium">累计提升度</span>
            </div>
            <span className="text-2xl font-bold text-orange-700 dark:text-orange-300">
              {formatNumber(data.summary.avg_lift, 2)}x
            </span>
          </div>
        </div>

        {/* 次级指标条 - 质量评分、稳定性、警告 */}
        {(data.validationReport || (data.psiReport && data.psiReport.length > 0)) && (
          <div className="flex items-center gap-4 px-3 py-2 rounded-lg bg-gray-50 dark:bg-gray-900/50 border text-xs">
            {/* 质量评分 */}
            {data.validationReport && (
              <div className="flex items-center gap-2">
                <ShieldCheck className={cn(
                  "h-4 w-4",
                  data.validationReport.quality_score >= 80 ? "text-green-600" :
                  data.validationReport.quality_score >= 60 ? "text-yellow-600" : "text-red-600"
                )} />
                <span className="text-gray-600 dark:text-gray-400">质量评分:</span>
                <span className={cn(
                  "font-semibold",
                  data.validationReport.quality_score >= 80 ? "text-green-600" :
                  data.validationReport.quality_score >= 60 ? "text-yellow-600" : "text-red-600"
                )}>
                  {data.validationReport.quality_score}/100
                </span>
              </div>
            )}
            
            {/* 分隔符 */}
            {data.validationReport && data.psiReport && data.psiReport.length > 0 && (
              <div className="h-4 w-px bg-gray-300 dark:bg-gray-700" />
            )}
            
            {/* 稳定性 */}
            {data.psiReport && data.psiReport.length > 0 && (() => {
              const stableCount = data.psiReport.filter(r => r.stability === "稳定").length;
              const totalCount = data.psiReport.length;
              const avgPsi = data.psiReport.reduce((sum, r) => sum + (r.psi || 0), 0) / totalCount;
              return (
                <>
                  <div className="flex items-center gap-2">
                    <CheckCircle className={cn(
                      "h-4 w-4",
                      stableCount === totalCount ? "text-green-600" :
                      stableCount >= totalCount * 0.8 ? "text-yellow-600" : "text-red-600"
                    )} />
                    <span className="text-gray-600 dark:text-gray-400">稳定性:</span>
                    <span className={cn(
                      "font-semibold",
                      stableCount === totalCount ? "text-green-600" :
                      stableCount >= totalCount * 0.8 ? "text-yellow-600" : "text-red-600"
                    )}>
                      {stableCount}/{totalCount}
                    </span>
                  </div>
                  
                  <div className="h-4 w-px bg-gray-300 dark:bg-gray-700" />
                  
                  <div className="flex items-center gap-2">
                    <Activity className={cn(
                      "h-4 w-4",
                      avgPsi < 0.1 ? "text-green-600" :
                      avgPsi < 0.25 ? "text-yellow-600" : "text-red-600"
                    )} />
                    <span className="text-gray-600 dark:text-gray-400">平均PSI:</span>
                    <span className={cn(
                      "font-semibold",
                      avgPsi < 0.1 ? "text-green-600" :
                      avgPsi < 0.25 ? "text-yellow-600" : "text-red-600"
                    )}>
                      {avgPsi.toFixed(3)}
                    </span>
                  </div>
                </>
              );
            })()}
            
            {/* P1-5: OOT 时间稳定性 */}
            {data.ootStabilityReport && (() => {
              const overallCv = data.ootStabilityReport.overall_hit_rate?.cv || 0;
              const counts = data.ootStabilityReport.stability_counts || {};
              const bonus = data.ootStabilityReport.stability_score_bonus || 0;
              const cvLevel = overallCv < 0.15 ? "高度稳定" : overallCv < 0.25 ? "稳定" : overallCv < 0.35 ? "中等" : "不稳定";
              const cvColor = overallCv < 0.15 ? "text-green-600" : overallCv < 0.25 ? "text-blue-600" : overallCv < 0.35 ? "text-yellow-600" : "text-red-600";
              return (
                <>
                  <div className="h-4 w-px bg-gray-300 dark:bg-gray-700" />
                  <div className="flex items-center gap-2">
                    <Activity className={cn("h-4 w-4", cvColor)} />
                    <span className="text-gray-600 dark:text-gray-400">OOT:</span>
                    <span className={cn("font-semibold", cvColor)}>
                      CV={overallCv.toFixed(3)} ({cvLevel})
                    </span>
                  </div>
                  <div className="flex items-center gap-1 text-xs text-gray-500">
                    <span>🟢{counts.highly_stable || 0}</span>
                    <span>🟡{counts.stable || 0}</span>
                    <span>🟠{counts.moderate || 0}</span>
                    <span>🔴{counts.unstable || 0}</span>
                    <span className={cn("ml-1", bonus > 0 ? "text-green-600" : bonus < 0 ? "text-red-600" : "text-gray-500")}>
                      ({bonus > 0 ? "+" : ""}{bonus}分)
                    </span>
                  </div>
                </>
              );
            })()}
            
            {/* 警告数 */}
            {data.validationReport && data.validationReport.warnings && data.validationReport.warnings.length > 0 && (
              <>
                <div className="h-4 w-px bg-gray-300 dark:bg-gray-700" />
                <div className="flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-yellow-600" />
                  <span className="text-gray-600 dark:text-gray-400">警告:</span>
                  <span className="font-semibold text-yellow-600">
                    {data.validationReport.warnings.length}
                  </span>
                </div>
              </>
            )}
          </div>
        )}

        {/* 标签页：图表和规则表格 */}
        <Tabs value={activeTab} onValueChange={setActiveTab} defaultValue="charts">
          <div className="flex items-center justify-between">
            <TabsList className="flex-wrap">
              {/* 样本及特征Tab - 放在最前面 */}
              {stagesData && (
                <TabsTrigger value="sample-feature" className="text-xs">
                  <Database className="h-3 w-3 mr-1" />
                  样本及特征
                </TabsTrigger>
              )}
              <TabsTrigger value="charts" className="text-xs">
                <BarChart3 className="h-3 w-3 mr-1" />
                评估图表
              </TabsTrigger>
              <TabsTrigger value="optimal" className="text-xs">
                最优规则 ({data.optimalRules.length})
              </TabsTrigger>
              {/* 规则筛选Tab - 合并原全部/过滤后Tab */}
              {data.allRulesWithStatus.length > 0 && (
                <TabsTrigger value="filtering-process" className="text-xs">
                  <GitBranch className="h-3 w-3 mr-1" />
                  规则筛选 ({data.allRulesWithStatus.length})
                </TabsTrigger>
              )}
              {data.validationReport && (
                <TabsTrigger value="validation" className="text-xs">
                  <ShieldCheck className="h-3 w-3 mr-1" />
                  质量验证
                </TabsTrigger>
              )}
              {/* PSI 稳定性 tab - 独立显示（核心评估指标） */}
              {data.psiReport && data.psiReport.length > 0 && (
                <TabsTrigger value="psi" className="text-xs">
                  <Activity className="h-3 w-3 mr-1" />
                  稳定性
                </TabsTrigger>
              )}
              {/* 附加分析 tab - 整合金额分析、先验规则分析 */}
              {(data.amountAnalysis || data.priorAnalysis) && (
                <TabsTrigger value="advanced" className="text-xs">
                  <Settings2 className="h-3 w-3 mr-1" />
                  附加分析
                </TabsTrigger>
              )}
              {/* 决策树/规则来源Tab - 仅在多特征模式下显示 */}
              {(data.treeStructure || data.ruleSourceStats) && (
                <TabsTrigger value="tree" className="text-xs">
                  {data.treeStructure ? (
                    <>
                      <TrendingUp className="h-3 w-3 mr-1" />
                      决策树
                    </>
                  ) : (
                    <>
                      <Layers className="h-3 w-3 mr-1" />
                      规则来源
                    </>
                  )}
                </TabsTrigger>
              )}
            </TabsList>
          </div>

          {/* 样本及特征标签页 - 放在最前面 */}
          {stagesData && (
            <TabsContent value="sample-feature" className="mt-3">
              <SampleFeaturePanel stagesData={stagesData} />
            </TabsContent>
          )}

          {/* 图表标签页 */}
          <TabsContent value="charts" className="mt-3 space-y-4">
            {data.chartData ? (
              <>
                {/* 累计指标曲线 */}
                {data.chartData.cumulative_metrics && (
                  <div className="border rounded-lg p-4">
                    <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
                      <TrendingUp className="h-4 w-4 text-green-600" />
                      累计指标曲线
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger>
                            <HelpCircle className="h-3 w-3 text-gray-400" />
                          </TooltipTrigger>
                          <TooltipContent>
                            <p className="text-xs">展示规则叠加后的累计召回率和命中率变化</p>
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    </h4>
                    <CumulativeMetricsChart data={data.chartData.cumulative_metrics} />
                  </div>
                )}
                
                {/* 规则分布图 */}
                {data.chartData.rule_distribution && (
                  <div className="border rounded-lg p-4">
                    <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
                      <Target className="h-4 w-4 text-blue-600" />
                      规则分布图
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger>
                            <HelpCircle className="h-3 w-3 text-gray-400" />
                          </TooltipTrigger>
                          <TooltipContent>
                            <p className="text-xs">展示各规则的命中率vs召回率分布，点大小表示提升倍数</p>
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    </h4>
                    <RuleDistributionChart data={data.chartData.rule_distribution} />
                  </div>
                )}
              </>
            ) : (
              <div className="text-center py-8 text-sm text-gray-500">
                暂无图表数据
              </div>
            )}
          </TabsContent>

          <TabsContent value="optimal" className="mt-3">
            <RuleTable rules={data.optimalRules} showCumulative />
          </TabsContent>
          
          {/* 规则筛选标签页 - 合并原全部/过滤后Tab */}
          {data.allRulesWithStatus.length > 0 && (
            <TabsContent value="filtering-process" className="mt-3">
              <RuleFilteringProcessPanel 
                rules={data.allRulesWithStatus} 
                optimalRules={data.optimalRules}
                summary={data.summary}
              />
            </TabsContent>
          )}

          {/* 规则质量验证标签页 */}
          {data.validationReport && (
            <TabsContent value="validation" className="mt-3">
              <ValidationReportPanel report={data.validationReport} />
            </TabsContent>
          )}

          {/* PSI 稳定性标签页 - 独立显示（核心评估指标） */}
          {data.psiReport && data.psiReport.length > 0 && (
            <TabsContent value="psi" className="mt-3">
              <PSIReportPanel report={data.psiReport} />
            </TabsContent>
          )}

          {/* 附加分析标签页 - 整合金额分析、先验规则分析 */}
          {(data.amountAnalysis || data.priorAnalysis) && (
            <TabsContent value="advanced" className="mt-3">
              <AdvancedAnalysisPanel 
                amountAnalysis={data.amountAnalysis}
                priorAnalysis={data.priorAnalysis}
              />
            </TabsContent>
          )}

          {/* 决策树/规则来源标签页 - 仅在多特征模式下显示 */}
          {(data.treeStructure || data.ruleSourceStats) && (
            <TabsContent value="tree" className="mt-3">
              {data.treeStructure ? (
                // Full Tree 模式：显示决策树可视化
                <DecisionTreePanel treeData={data.treeStructure} />
              ) : (
                // 组合树模式：显示规则来源统计
                <RuleSourceStatsPanel stats={data.ruleSourceStats!} />
              )}
            </TabsContent>
          )}
        </Tabs>

        {/* 错误信息 */}
        {result?.errors && result.errors.length > 0 && (
          <div className="p-3 rounded-lg bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800">
            <span className="text-xs font-medium text-yellow-600">警告信息:</span>
            <ul className="mt-1 text-xs text-yellow-700 dark:text-yellow-300 list-disc list-inside">
              {result.errors.map((err, i) => (
                <li key={i}>{err}</li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// 规则表格子组件
function RuleTable({
  rules,
  showCumulative = false,
  maxRows,
}: {
  rules: RuleData[];
  showCumulative?: boolean;
  maxRows?: number;
}) {
  const displayRules = maxRows ? rules.slice(0, maxRows) : rules;
  const hasMore = maxRows && rules.length > maxRows;

  if (rules.length === 0) {
    return (
      <div className="text-center py-8 text-sm text-gray-500">
        暂无规则数据
      </div>
    );
  }

  return (
    <div className="border rounded-lg overflow-hidden">
      <div className="max-h-[400px] overflow-auto">
        <Table>
          <TableHeader className="sticky top-0 bg-gray-50 dark:bg-gray-900">
            <TableRow>
              <TableHead className="w-[40px] text-center">#</TableHead>
              <TableHead>规则</TableHead>
              <TableHead className="w-[80px] text-right">Recall</TableHead>
              <TableHead className="w-[80px] text-right">Bad Rate</TableHead>
              <TableHead className="w-[60px] text-right">Lift</TableHead>
              <TableHead className="w-[80px] text-right">Hit Rate</TableHead>
              {showCumulative && (
                <>
                  <TableHead className="w-[80px] text-right">累计Recall</TableHead>
                  <TableHead className="w-[80px] text-right">累计Hit</TableHead>
                </>
              )}
            </TableRow>
          </TableHeader>
          <TableBody>
            {displayRules.map((rule, index) => (
              <TableRow key={index}>
                <TableCell className="text-center text-gray-500">
                  {index + 1}
                </TableCell>
                <TableCell className="font-mono text-xs max-w-[300px] truncate" title={rule.rule}>
                  {rule.rule}
                </TableCell>
                <TableCell className="text-right">
                  {rule.recall !== undefined ? (rule.recall * 100).toFixed(2) + "%" : "-"}
                </TableCell>
                <TableCell className="text-right">
                  {rule.bad_rate !== undefined ? (rule.bad_rate * 100).toFixed(2) + "%" : "-"}
                </TableCell>
                <TableCell className="text-right">
                  <Badge
                    variant={rule.lift >= 5 ? "default" : rule.lift >= 3 ? "secondary" : "outline"}
                    className="text-xs"
                  >
                    {rule.lift?.toFixed(1) || "-"}
                  </Badge>
                </TableCell>
                <TableCell className="text-right">
                  {rule.hit_rate !== undefined ? (rule.hit_rate * 100).toFixed(2) + "%" : "-"}
                </TableCell>
                {showCumulative && (
                  <>
                    <TableCell className="text-right text-blue-600 font-medium">
                      {rule.cumulative_recall !== undefined 
                        ? (rule.cumulative_recall * 100).toFixed(2) + "%" 
                        : "-"}
                    </TableCell>
                    <TableCell className="text-right text-purple-600 font-medium">
                      {rule.cumulative_hit_rate !== undefined 
                        ? (rule.cumulative_hit_rate * 100).toFixed(2) + "%" 
                        : "-"}
                    </TableCell>
                  </>
                )}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      {hasMore && (
        <div className="p-2 text-center text-xs text-gray-500 bg-gray-50 dark:bg-gray-900 border-t">
          显示前 {maxRows} 条，共 {rules.length} 条规则
        </div>
      )}
    </div>
  );
}

// 规则筛选面板（合并原3个Tab：全部、过滤后、最优规则）
function RuleFilteringProcessPanel({ 
  rules, 
  optimalRules,
  summary 
}: { 
  rules: RuleWithStatus[];
  optimalRules: RuleData[];
  summary: ResultSummary;
}) {
  const [stageFilter, setStageFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [searchTerm, setSearchTerm] = useState("");

  // 计算漏斗数据
  const funnelData = useMemo(() => {
    const total = rules.length;
    const passedFiltering = rules.filter(r => r.is_valid).length;
    const optimal = rules.filter(r => r.is_optimal).length;
    
    return {
      generated: { count: total, percent: 100 },
      filtered: { count: passedFiltering, percent: total > 0 ? (passedFiltering / total * 100) : 0 },
      optimal: { count: optimal, percent: total > 0 ? (optimal / total * 100) : 0 },
    };
  }, [rules]);

  // 筛选规则
  const filteredRules = useMemo(() => {
    let result = [...rules];
    
    // 阶段筛选
    if (stageFilter === "passed") {
      result = result.filter(r => r.is_valid);
    } else if (stageFilter === "optimal") {
      result = result.filter(r => r.is_optimal);
    }
    
    // 状态筛选
    if (statusFilter === "optimal") {
      result = result.filter(r => r.is_optimal);
    } else if (statusFilter === "candidate") {
      result = result.filter(r => r.is_valid && !r.is_optimal);
    } else if (statusFilter === "filtered") {
      result = result.filter(r => !r.is_valid);
    }
    
    // 搜索
    if (searchTerm) {
      result = result.filter(r => r.rule.toLowerCase().includes(searchTerm.toLowerCase()));
    }
    
    return result;
  }, [rules, stageFilter, statusFilter, searchTerm]);

  // 获取状态标签（支持显示多个筛除原因）
  const getStatusBadge = (rule: RuleWithStatus) => {
    if (rule.is_optimal) {
      return (
        <Badge className="bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 text-xs">
          ⭐ 最优
        </Badge>
      );
    }
    if (rule.is_valid) {
      return (
        <Badge className="bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 text-xs">
          ✓ 候选
        </Badge>
      );
    }
    
    // 收集所有筛除原因
    const reasons: string[] = [];
    if (!rule.direction_valid) {
      reasons.push("单调性");
    }
    if (rule.lift_valid === false) {
      reasons.push("Lift低");
    }
    if (rule.hit_rate_valid === false) {
      reasons.push("命中高");
    }
    
    // 如果有多个原因，合并显示
    if (reasons.length > 1) {
      return (
        <Badge className="bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 text-xs">
          ✗ {reasons.join(" & ")}
        </Badge>
      );
    } else if (reasons.length === 1) {
      // 单个原因使用不同颜色
      if (!rule.direction_valid) {
        return (
          <Badge className="bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 text-xs">
            ✗ 单调性
          </Badge>
        );
      }
      return (
        <Badge className="bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400 text-xs">
          ✗ {reasons[0]}
        </Badge>
      );
    }
    
    return (
      <Badge className="bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400 text-xs">
        ✗ 过滤
      </Badge>
    );
  };

  if (rules.length === 0) {
    return (
      <div className="text-center py-8 text-sm text-gray-500">
        暂无规则筛选数据
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 漏斗概览 */}
      <div className="border rounded-lg p-4 bg-gray-50 dark:bg-gray-900/50">
        <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
          <GitBranch className="h-4 w-4 text-blue-600" />
          漏斗概览
        </h4>
        <div className="flex items-center justify-center gap-2">
          {/* 生成规则 */}
          <div className="flex flex-col items-center p-3 bg-white dark:bg-gray-800 rounded-lg border min-w-[100px]">
            <span className="text-xs text-gray-500 mb-1">生成规则</span>
            <span className="text-lg font-bold text-gray-900 dark:text-gray-100">{funnelData.generated.count}条</span>
            <span className="text-xs text-gray-400">100%</span>
          </div>
          
          <ChevronRight className="h-5 w-5 text-gray-400" />
          
          {/* 规则筛选 */}
          <div className="flex flex-col items-center p-3 bg-white dark:bg-gray-800 rounded-lg border min-w-[100px]">
            <span className="text-xs text-gray-500 mb-1">规则筛选</span>
            <span className="text-lg font-bold text-blue-600">{funnelData.filtered.count}条</span>
            <span className="text-xs text-gray-400">{funnelData.filtered.percent.toFixed(1)}%</span>
          </div>
          
          <ChevronRight className="h-5 w-5 text-gray-400" />
          
          {/* 最优选择 */}
          <div className="flex flex-col items-center p-3 bg-white dark:bg-gray-800 rounded-lg border min-w-[100px]">
            <span className="text-xs text-gray-500 mb-1">最优选择</span>
            <span className="text-lg font-bold text-green-600">{funnelData.optimal.count}条</span>
            <span className="text-xs text-gray-400">{funnelData.optimal.percent.toFixed(1)}%</span>
          </div>
        </div>
      </div>

      {/* 筛选条件 */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">阶段:</span>
          <select 
            value={stageFilter} 
            onChange={(e) => setStageFilter(e.target.value)}
            className="text-xs border rounded px-2 py-1 bg-white dark:bg-gray-800"
          >
            <option value="all">全部规则 ({rules.length})</option>
            <option value="passed">通过筛选 ({funnelData.filtered.count})</option>
            <option value="optimal">最优规则 ({funnelData.optimal.count})</option>
          </select>
        </div>
        
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">状态:</span>
          <select 
            value={statusFilter} 
            onChange={(e) => setStatusFilter(e.target.value)}
            className="text-xs border rounded px-2 py-1 bg-white dark:bg-gray-800"
          >
            <option value="all">所有状态</option>
            <option value="optimal">⭐ 最优</option>
            <option value="candidate">✓ 候选</option>
            <option value="filtered">✗ 被过滤</option>
          </select>
        </div>
        
        <div className="flex-1 min-w-[150px]">
          <input
            type="text"
            placeholder="🔍 搜索规则..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full text-xs border rounded px-2 py-1 bg-white dark:bg-gray-800"
          />
        </div>
      </div>

      {/* 规则表格 */}
      <div className="border rounded-lg overflow-hidden">
        <div className="max-h-[400px] overflow-auto">
          <Table>
            <TableHeader className="sticky top-0 bg-gray-50 dark:bg-gray-900">
              <TableRow>
                <TableHead className="w-[40px] text-center">#</TableHead>
                <TableHead className="w-[80px]">状态</TableHead>
                <TableHead>规则表达式</TableHead>
                <TableHead className="w-[60px] text-right">Lift</TableHead>
                <TableHead className="w-[70px] text-right">命中率</TableHead>
                <TableHead className="w-[70px] text-right">召回率</TableHead>
                <TableHead className="w-[70px] text-right">坏账率</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredRules.map((rule, index) => (
                <TableRow key={index} className={rule.is_optimal ? "bg-green-50/50 dark:bg-green-900/10" : ""}>
                  <TableCell className="text-center text-gray-500 text-xs">
                    {index + 1}
                  </TableCell>
                  <TableCell>
                    {getStatusBadge(rule)}
                  </TableCell>
                  <TableCell className="font-mono text-xs max-w-[300px]">
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <span className="truncate block cursor-help">{rule.rule}</span>
                        </TooltipTrigger>
                        <TooltipContent side="top" className="max-w-[500px]">
                          <p className="text-xs font-mono break-all">{rule.rule}</p>
                          {rule.filter_reason && (
                            <p className="text-xs text-red-400 mt-1">过滤原因: {rule.filter_reason}</p>
                          )}
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </TableCell>
                  <TableCell className="text-right">
                    {rule.lift !== null ? (
                      <Badge
                        variant={rule.lift >= 5 ? "default" : rule.lift >= 3 ? "secondary" : "outline"}
                        className="text-xs"
                      >
                        {rule.lift.toFixed(1)}
                      </Badge>
                    ) : "-"}
                  </TableCell>
                  <TableCell className="text-right text-xs">
                    {rule.hit_rate !== null ? (rule.hit_rate * 100).toFixed(2) + "%" : "-"}
                  </TableCell>
                  <TableCell className="text-right text-xs">
                    {rule.recall !== null ? (rule.recall * 100).toFixed(2) + "%" : "-"}
                  </TableCell>
                  <TableCell className="text-right text-xs">
                    {rule.bad_rate !== null ? (rule.bad_rate * 100).toFixed(2) + "%" : "-"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        <div className="p-2 text-center text-xs text-gray-500 bg-gray-50 dark:bg-gray-900 border-t flex justify-between items-center px-4">
          <span>显示 {filteredRules.length} 条，共 {rules.length} 条规则</span>
          <Button variant="outline" size="sm" className="text-xs h-7">
            <Download className="h-3 w-3 mr-1" />
            导出CSV
          </Button>
        </div>
      </div>
    </div>
  );
}

// 规则质量验证报告面板（行业标准版）
function ValidationReportPanel({ report }: { report: ValidationReport }) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case "ok":
      case "excellent":
      case "good":
        return "text-green-600 bg-green-50 dark:bg-green-900/20";
      case "acceptable":
        return "text-blue-600 bg-blue-50 dark:bg-blue-900/20";
      case "warning":
      case "warning_low":
      case "warning_high":
        return "text-yellow-600 bg-yellow-50 dark:bg-yellow-900/20";
      case "error":
        return "text-red-600 bg-red-50 dark:bg-red-900/20";
      default:
        return "text-gray-600 bg-gray-50 dark:bg-gray-900/20";
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "ok":
      case "excellent":
      case "good":
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      case "acceptable":
        return <CheckCircle className="h-4 w-4 text-blue-600" />;
      case "warning":
      case "warning_low":
      case "warning_high":
        return <AlertTriangle className="h-4 w-4 text-yellow-600" />;
      case "error":
        return <X className="h-4 w-4 text-red-600" />;
      default:
        return null;
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case "excellent": return "优秀";
      case "good": return "良好";
      case "acceptable": return "可接受";
      case "warning": case "warning_low": case "warning_high": return "需优化";
      case "ok": return "正常";
      default: return "-";
    }
  };

  // 计算得分条的宽度
  const getScoreBarWidth = (score: number, maxScore: number) => {
    return `${(score / maxScore) * 100}%`;
  };

  return (
    <div className="space-y-4">
      {/* 质量评分总览 */}
      <div className="flex items-center justify-between p-4 rounded-lg bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 border">
        <div className="flex items-center gap-3">
          <ShieldCheck className="h-8 w-8 text-blue-600" />
          <div>
            <div className="text-sm font-medium">规则质量评分</div>
            <div className="text-xs text-gray-500">基于行业标准综合评估提升度、召回率、命中率、独立性和复杂度</div>
          </div>
        </div>
        <div className={cn(
          "text-3xl font-bold",
          report.quality_score >= 80 ? "text-green-600" :
          report.quality_score >= 60 ? "text-yellow-600" : "text-red-600"
        )}>
          {report.quality_score.toFixed(1)}
          <span className="text-sm font-normal text-gray-500">/100</span>
        </div>
      </div>

      {/* 评分明细（加权得分） */}
      {report.score_breakdown && (
        <div className="border rounded-lg p-3">
          <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
            <BarChart3 className="h-4 w-4 text-purple-600" />
            评分明细（加权得分）
          </h4>
          <div className="space-y-2">
            {/* 提升度 30分 */}
            <div className="flex items-center gap-2">
              <span className="text-xs w-16 text-gray-600">提升度</span>
              <div className="flex-1 h-4 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-green-500 rounded-full transition-all"
                  style={{ width: getScoreBarWidth(report.score_breakdown.discrimination || 0, 30) }}
                />
              </div>
              <span className="text-xs w-14 text-right font-medium">
                {(report.score_breakdown.discrimination || 0).toFixed(1)}/30
              </span>
            </div>
            {/* 召回率 25分 */}
            <div className="flex items-center gap-2">
              <span className="text-xs w-16 text-gray-600">召回率</span>
              <div className="flex-1 h-4 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-blue-500 rounded-full transition-all"
                  style={{ width: getScoreBarWidth(report.score_breakdown.recall || 0, 25) }}
                />
              </div>
              <span className="text-xs w-14 text-right font-medium">
                {(report.score_breakdown.recall || 0).toFixed(1)}/25
              </span>
            </div>
            {/* 命中率/覆盖率 15分 */}
            <div className="flex items-center gap-2">
              <span className="text-xs w-16 text-gray-600">命中率</span>
              <div className="flex-1 h-4 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-purple-500 rounded-full transition-all"
                  style={{ width: getScoreBarWidth(report.score_breakdown.coverage || 0, 15) }}
                />
              </div>
              <span className="text-xs w-14 text-right font-medium">
                {(report.score_breakdown.coverage || 0).toFixed(1)}/15
              </span>
            </div>
            {/* 独立性 15分 */}
            <div className="flex items-center gap-2">
              <span className="text-xs w-16 text-gray-600">独立性</span>
              <div className="flex-1 h-4 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-orange-500 rounded-full transition-all"
                  style={{ width: getScoreBarWidth(report.score_breakdown.independence || 0, 15) }}
                />
              </div>
              <span className="text-xs w-14 text-right font-medium">
                {(report.score_breakdown.independence || 0).toFixed(1)}/15
              </span>
            </div>
            {/* 复杂度 15分 */}
            <div className="flex items-center gap-2">
              <span className="text-xs w-16 text-gray-600">复杂度</span>
              <div className="flex-1 h-4 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-cyan-500 rounded-full transition-all"
                  style={{ width: getScoreBarWidth(report.score_breakdown.complexity || 0, 15) }}
                />
              </div>
              <span className="text-xs w-14 text-right font-medium">
                {(report.score_breakdown.complexity || 0).toFixed(1)}/15
              </span>
            </div>
          </div>
        </div>
      )}

      {/* 核心指标详情 */}
      <div className="grid grid-cols-2 gap-3">
        {/* 提升度（核心） - 平均值 */}
        {report.discrimination_report && (
          <div className={cn("p-3 rounded-lg border", getStatusColor(report.discrimination_report.status))}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium">平均提升度 (Lift)</span>
              <Badge variant="outline" className="text-xs">
                {getStatusLabel(report.discrimination_report.status)}
              </Badge>
            </div>
            <div className="text-xl font-bold">
              {report.discrimination_report.avg_lift.toFixed(2)}x
            </div>
            <div className="text-xs text-gray-500 mt-1 space-y-0.5">
              <div>最小: {report.discrimination_report.min_lift.toFixed(2)}x | 最大: {report.discrimination_report.max_lift.toFixed(2)}x</div>
              <div>行业标准: ≥3优秀 / ≥2良好 / ≥1.5可接受</div>
            </div>
          </div>
        )}

        {/* 召回率（核心） - 累计值 */}
        {report.recall_report && (
          <div className={cn("p-3 rounded-lg border", getStatusColor(report.recall_report.status))}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium">累计召回率</span>
              <Badge variant="outline" className="text-xs">
                {getStatusLabel(report.recall_report.status)}
              </Badge>
            </div>
            <div className="text-xl font-bold">
              {(report.recall_report.cumulative_recall * 100).toFixed(1)}%
            </div>
            <div className="text-xs text-gray-500 mt-1 space-y-0.5">
              {report.recall_report.total_bad_samples && (
                <div>坏客户总数: {report.recall_report.total_bad_samples}</div>
              )}
              <div>行业标准: ≥30%优秀 / ≥20%良好 / ≥10%可接受</div>
            </div>
          </div>
        )}

        {/* 命中率/覆盖率 - 累计值 */}
        <div className={cn("p-3 rounded-lg border", getStatusColor(report.coverage_report.status))}>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium">累计命中率/覆盖率</span>
            {getStatusIcon(report.coverage_report.status)}
          </div>
          <div className="text-xl font-bold">
            {(report.coverage_report.total_coverage * 100).toFixed(1)}%
          </div>
          <div className="text-xs text-gray-500 mt-1">
            最优范围: {(report.coverage_report.thresholds?.optimal_min || 0.01) * 100}% - {(report.coverage_report.thresholds?.optimal_max || 0.30) * 100}%
          </div>
        </div>

        {/* 复杂度 - 平均值 */}
        {report.complexity_report && (
          <div className={cn("p-3 rounded-lg border", getStatusColor(report.complexity_report.status))}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium">平均复杂度</span>
              {getStatusIcon(report.complexity_report.status)}
            </div>
            <div className="text-xl font-bold">
              {report.complexity_report.avg_complexity.toFixed(1)} 条件
            </div>
            <div className="text-xs text-gray-500 mt-1">
              最大: {report.complexity_report.max_complexity} | 建议 ≤{report.complexity_report.thresholds?.optimal || 3} 条件
            </div>
          </div>
        )}

        {/* 重叠度 */}
        <div className={cn("p-3 rounded-lg border", getStatusColor(report.overlap_report.status))}>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium">平均重叠度</span>
            {getStatusIcon(report.overlap_report.status)}
          </div>
          <div className="text-xl font-bold">
            {(report.overlap_report.avg_overlap * 100).toFixed(1)}%
          </div>
          <div className="text-xs text-gray-500 mt-1">
            规则间Jaccard相似度均值
          </div>
        </div>

        {/* 冗余 */}
        <div className={cn("p-3 rounded-lg border", getStatusColor(report.redundancy_report.status))}>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium">冗余规则</span>
            {getStatusIcon(report.redundancy_report.status)}
          </div>
          <div className="text-xl font-bold">
            {report.redundancy_report.redundant_count} 对
          </div>
          <div className="text-xs text-gray-500 mt-1">
            完全被其他规则包含的规则
          </div>
        </div>
      </div>

      {/* Lift分布统计 */}
      {report.discrimination_report?.lift_distribution && (
        <div className="border rounded-lg p-3">
          <h4 className="text-xs font-medium mb-2">Lift分布统计</h4>
          <div className="flex items-center gap-3 text-xs">
            <div className="flex items-center gap-1">
              <span className="w-3 h-3 rounded bg-green-500"></span>
              <span>优秀(≥3): {report.discrimination_report.lift_distribution.excellent}</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="w-3 h-3 rounded bg-blue-500"></span>
              <span>良好(2-3): {report.discrimination_report.lift_distribution.good}</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="w-3 h-3 rounded bg-yellow-500"></span>
              <span>可接受(1.5-2): {report.discrimination_report.lift_distribution.acceptable}</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="w-3 h-3 rounded bg-red-500"></span>
              <span>差(&lt;1.5): {report.discrimination_report.lift_distribution.poor}</span>
            </div>
          </div>
        </div>
      )}

      {/* 警告信息 */}
      {report.warnings && report.warnings.length > 0 && (
        <div className="p-3 rounded-lg bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle className="h-4 w-4 text-yellow-600" />
            <span className="text-sm font-medium text-yellow-700 dark:text-yellow-400">优化建议</span>
          </div>
          <ul className="space-y-1">
            {report.warnings.map((warning, i) => (
              <li key={i} className="text-xs text-yellow-700 dark:text-yellow-400 flex items-start gap-2">
                <span className="text-yellow-500">•</span>
                {warning}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 高重叠规则对 */}
      {report.overlap_report.high_overlap_pairs && report.overlap_report.high_overlap_pairs.length > 0 && (
        <div className="border rounded-lg overflow-hidden">
          <div className="p-2 bg-gray-50 dark:bg-gray-900 border-b">
            <span className="text-xs font-medium">高重叠规则对（Jaccard &gt; 50%）</span>
          </div>
          <div className="max-h-[200px] overflow-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-xs">规则1</TableHead>
                  <TableHead className="text-xs">规则2</TableHead>
                  <TableHead className="text-xs text-right">重叠度</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {report.overlap_report.high_overlap_pairs.map((pair, i) => (
                  <TableRow key={i}>
                    <TableCell className="text-xs font-mono truncate max-w-[200px]" title={pair.rule1}>
                      {pair.rule1}
                    </TableCell>
                    <TableCell className="text-xs font-mono truncate max-w-[200px]" title={pair.rule2}>
                      {pair.rule2}
                    </TableCell>
                    <TableCell className="text-xs text-right font-medium text-yellow-600">
                      {(pair.jaccard * 100).toFixed(1)}%
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>
      )}

      {/* 行业标准说明（简要 + 查看完整标准弹窗） */}
      <div className="p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <HelpCircle className="h-4 w-4 text-blue-600" />
            <span className="text-sm font-medium text-blue-700 dark:text-blue-400">评分标准说明</span>
          </div>
          <Dialog>
            <DialogTrigger asChild>
              <button className="text-xs text-blue-600 hover:text-blue-800 hover:underline flex items-center gap-1">
                <Info className="h-3 w-3" />
                查看完整评估标准
              </button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  <ShieldCheck className="h-5 w-5 text-blue-600" />
                  规则质量评估标准（信贷风控行业标准）
                </DialogTitle>
              </DialogHeader>
              <div className="space-y-4 text-sm">
                {/* 评分体系总览 */}
                <div className="p-3 bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 rounded-lg border">
                  <h4 className="font-medium mb-2">评分体系（满分100分）</h4>
                  <div className="grid grid-cols-5 gap-2 text-center text-xs">
                    <div className="p-2 bg-white dark:bg-gray-800 rounded">
                      <div className="font-bold text-green-600">30分</div>
                      <div className="text-gray-500">提升度</div>
                    </div>
                    <div className="p-2 bg-white dark:bg-gray-800 rounded">
                      <div className="font-bold text-blue-600">25分</div>
                      <div className="text-gray-500">召回率</div>
                    </div>
                    <div className="p-2 bg-white dark:bg-gray-800 rounded">
                      <div className="font-bold text-purple-600">15分</div>
                      <div className="text-gray-500">命中率</div>
                    </div>
                    <div className="p-2 bg-white dark:bg-gray-800 rounded">
                      <div className="font-bold text-orange-600">15分</div>
                      <div className="text-gray-500">独立性</div>
                    </div>
                    <div className="p-2 bg-white dark:bg-gray-800 rounded">
                      <div className="font-bold text-cyan-600">15分</div>
                      <div className="text-gray-500">复杂度</div>
                    </div>
                  </div>
                </div>

                {/* 各指标详细标准 */}
                <div className="space-y-3">
                  {/* 提升度 */}
                  <div className="border rounded-lg p-3">
                    <h4 className="font-medium text-green-700 dark:text-green-400 mb-2 flex items-center gap-2">
                      <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                      提升度（Lift）- 30分
                    </h4>
                    <p className="text-gray-600 dark:text-gray-400 text-xs mb-2">
                      衡量规则区分好坏客户的能力。Lift = 规则命中坏客户率 / 整体坏客户率
                    </p>
                    <table className="w-full text-xs border-collapse">
                      <thead>
                        <tr className="bg-gray-50 dark:bg-gray-800">
                          <th className="border p-1.5 text-left">等级</th>
                          <th className="border p-1.5 text-left">Lift阈值</th>
                          <th className="border p-1.5 text-left">得分范围</th>
                          <th className="border p-1.5 text-left">说明</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr>
                          <td className="border p-1.5"><Badge className="bg-green-100 text-green-700 text-xs">优秀</Badge></td>
                          <td className="border p-1.5 font-mono">≥ 3.0</td>
                          <td className="border p-1.5">27-30分</td>
                          <td className="border p-1.5">规则精准度高，风控效果显著</td>
                        </tr>
                        <tr>
                          <td className="border p-1.5"><Badge className="bg-blue-100 text-blue-700 text-xs">良好</Badge></td>
                          <td className="border p-1.5 font-mono">2.0 - 3.0</td>
                          <td className="border p-1.5">20-27分</td>
                          <td className="border p-1.5">规则有效，可投入使用</td>
                        </tr>
                        <tr>
                          <td className="border p-1.5"><Badge className="bg-yellow-100 text-yellow-700 text-xs">可接受</Badge></td>
                          <td className="border p-1.5 font-mono">1.5 - 2.0</td>
                          <td className="border p-1.5">12-20分</td>
                          <td className="border p-1.5">规则基本有效，建议优化</td>
                        </tr>
                        <tr>
                          <td className="border p-1.5"><Badge className="bg-red-100 text-red-700 text-xs">差</Badge></td>
                          <td className="border p-1.5 font-mono">&lt; 1.5</td>
                          <td className="border p-1.5">&lt;12分</td>
                          <td className="border p-1.5">提升度不足，需重新设计</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>

                  {/* 召回率 */}
                  <div className="border rounded-lg p-3">
                    <h4 className="font-medium text-blue-700 dark:text-blue-400 mb-2 flex items-center gap-2">
                      <span className="w-2 h-2 bg-blue-500 rounded-full"></span>
                      召回率（Recall）- 25分
                    </h4>
                    <p className="text-gray-600 dark:text-gray-400 text-xs mb-2">
                      规则集捕获坏客户的能力。累计召回率 = 规则命中的坏客户数 / 总坏客户数
                    </p>
                    <table className="w-full text-xs border-collapse">
                      <thead>
                        <tr className="bg-gray-50 dark:bg-gray-800">
                          <th className="border p-1.5 text-left">等级</th>
                          <th className="border p-1.5 text-left">召回率阈值</th>
                          <th className="border p-1.5 text-left">得分范围</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr>
                          <td className="border p-1.5"><Badge className="bg-green-100 text-green-700 text-xs">优秀</Badge></td>
                          <td className="border p-1.5 font-mono">≥ 30%</td>
                          <td className="border p-1.5">22-25分</td>
                        </tr>
                        <tr>
                          <td className="border p-1.5"><Badge className="bg-blue-100 text-blue-700 text-xs">良好</Badge></td>
                          <td className="border p-1.5 font-mono">20% - 30%</td>
                          <td className="border p-1.5">15-22分</td>
                        </tr>
                        <tr>
                          <td className="border p-1.5"><Badge className="bg-yellow-100 text-yellow-700 text-xs">可接受</Badge></td>
                          <td className="border p-1.5 font-mono">10% - 20%</td>
                          <td className="border p-1.5">8-15分</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>

                  {/* 命中率/覆盖率 */}
                  <div className="border rounded-lg p-3">
                    <h4 className="font-medium text-purple-700 dark:text-purple-400 mb-2 flex items-center gap-2">
                      <span className="w-2 h-2 bg-purple-500 rounded-full"></span>
                      命中率/覆盖率（Coverage）- 15分
                    </h4>
                    <p className="text-gray-600 dark:text-gray-400 text-xs mb-2">
                      规则命中的总样本占比。过低可能过拟合，过高说明规则过于宽泛。
                    </p>
                    <div className="text-xs space-y-1">
                      <p>• <b>最优范围</b>：1% - 30%（满分）</p>
                      <p>• <b>可接受范围</b>：0.5% - 50%</p>
                      <p>• <b>警告</b>：&lt;0.5%（过拟合风险）或 &gt;50%（规则过宽）</p>
                    </div>
                  </div>

                  {/* 独立性 */}
                  <div className="border rounded-lg p-3">
                    <h4 className="font-medium text-orange-700 dark:text-orange-400 mb-2 flex items-center gap-2">
                      <span className="w-2 h-2 bg-orange-500 rounded-full"></span>
                      独立性（Independence）- 15分
                    </h4>
                    <p className="text-gray-600 dark:text-gray-400 text-xs mb-2">
                      评估规则间的重叠度（Jaccard相似度）和冗余情况。
                    </p>
                    <div className="text-xs space-y-1">
                      <p>• <b>重叠度</b>：平均Jaccard &lt; 30%为优，&gt; 50%需警告</p>
                      <p>• <b>冗余检测</b>：无规则A完全包含规则B的情况为佳</p>
                    </div>
                  </div>

                  {/* 复杂度 */}
                  <div className="border rounded-lg p-3">
                    <h4 className="font-medium text-cyan-700 dark:text-cyan-400 mb-2 flex items-center gap-2">
                      <span className="w-2 h-2 bg-cyan-500 rounded-full"></span>
                      复杂度（Complexity）- 15分
                    </h4>
                    <p className="text-gray-600 dark:text-gray-400 text-xs mb-2">
                      规则的可解释性，以条件数衡量。
                    </p>
                    <div className="text-xs space-y-1">
                      <p>• <b>最优</b>：平均条件数 ≤ 3（便于业务理解和维护）</p>
                      <p>• <b>警告</b>：条件数 &gt; 5（可能过于复杂）</p>
                    </div>
                  </div>
                </div>

                {/* 综合评级说明 */}
                <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg border">
                  <h4 className="font-medium mb-2">综合评级说明</h4>
                  <div className="grid grid-cols-3 gap-2 text-xs text-center">
                    <div className="p-2 bg-green-50 dark:bg-green-900/30 rounded border border-green-200">
                      <div className="font-bold text-green-600">≥ 80分</div>
                      <div className="text-green-700">优秀 - 可直接上线</div>
                    </div>
                    <div className="p-2 bg-yellow-50 dark:bg-yellow-900/30 rounded border border-yellow-200">
                      <div className="font-bold text-yellow-600">60-80分</div>
                      <div className="text-yellow-700">良好 - 建议优化后上线</div>
                    </div>
                    <div className="p-2 bg-red-50 dark:bg-red-900/30 rounded border border-red-200">
                      <div className="font-bold text-red-600">&lt; 60分</div>
                      <div className="text-red-700">需改进 - 重新调整规则</div>
                    </div>
                  </div>
                </div>

                {/* 标准来源 */}
                <div className="text-xs text-gray-500 border-t pt-3">
                  <p><b>标准来源</b>：基于信贷风控行业通用实践，参考银行、消费金融机构的规则评估体系。</p>
                </div>
              </div>
            </DialogContent>
          </Dialog>
        </div>
        <div className="text-xs text-blue-700 dark:text-blue-400 space-y-1">
          <p>• <b>提升度(30分)</b>：基于平均Lift评估规则区分好坏客户的能力</p>
          <p>• <b>召回率(25分)</b>：规则集对坏客户的捕获能力，累计召回率≥20%为良好</p>
          <p>• <b>命中率(15分)</b>：整体样本覆盖在1%-30%为最优</p>
          <p>• <b>独立性(15分)</b>：规则间重叠度低、无冗余规则为佳</p>
          <p>• <b>复杂度(15分)</b>：单条规则条件数≤3为最优，便于业务理解</p>
        </div>
      </div>
    </div>
  );
}

// ========== PSI趋势柱状图组件 ==========
function PSITrendChart({ data }: { data: PSIReport[] }) {
  const width = 560;
  const height = 220;
  const padding = { top: 30, right: 20, bottom: 50, left: 50 };
  
  const chartData = useMemo(() => {
    if (!data || data.length === 0) return null;
    
    const validData = data.filter(d => d.psi !== null && d.psi !== undefined);
    if (validData.length === 0) return null;
    
    const maxPsi = Math.max(...validData.map(d => d.psi || 0), 0.3);
    const barWidth = Math.min(40, (width - padding.left - padding.right) / validData.length - 8);
    
    return {
      items: validData,
      maxPsi,
      barWidth,
      chartWidth: width - padding.left - padding.right,
      chartHeight: height - padding.top - padding.bottom
    };
  }, [data]);
  
  if (!chartData) {
    return <div className="text-center text-gray-500 py-8 text-sm">暂无PSI数据</div>;
  }
  
  const getBarColor = (psi: number) => {
    if (psi < 0.1) return "#22c55e"; // 绿色 - 稳定
    if (psi < 0.25) return "#f59e0b"; // 橙色 - 轻微变化
    return "#ef4444"; // 红色 - 显著变化
  };
  
  const yScale = chartData.chartHeight / chartData.maxPsi;
  const xStep = chartData.chartWidth / chartData.items.length;
  
  return (
    <div className="space-y-2">
      <div className="text-sm font-medium text-gray-700 dark:text-gray-300 flex items-center gap-2">
        <BarChart3 className="h-4 w-4" />
        PSI稳定性趋势图
      </div>
      <svg width={width} height={height} className="mx-auto">
        {/* 背景 */}
        <rect 
          x={padding.left} 
          y={padding.top} 
          width={chartData.chartWidth} 
          height={chartData.chartHeight} 
          fill="#f9fafb" 
          className="dark:fill-gray-800"
        />
        
        {/* 阈值线 - 0.1 */}
        <line 
          x1={padding.left} 
          y1={height - padding.bottom - 0.1 * yScale} 
          x2={width - padding.right} 
          y2={height - padding.bottom - 0.1 * yScale} 
          stroke="#f59e0b" 
          strokeWidth="1" 
          strokeDasharray="4,4"
        />
        <text 
          x={width - padding.right + 5} 
          y={height - padding.bottom - 0.1 * yScale + 3} 
          fontSize="9" 
          fill="#f59e0b"
        >0.1</text>
        
        {/* 阈值线 - 0.25 */}
        <line 
          x1={padding.left} 
          y1={height - padding.bottom - 0.25 * yScale} 
          x2={width - padding.right} 
          y2={height - padding.bottom - 0.25 * yScale} 
          stroke="#ef4444" 
          strokeWidth="1" 
          strokeDasharray="4,4"
        />
        <text 
          x={width - padding.right + 5} 
          y={height - padding.bottom - 0.25 * yScale + 3} 
          fontSize="9" 
          fill="#ef4444"
        >0.25</text>
        
        {/* 柱状图 */}
        {chartData.items.map((item, i) => {
          const x = padding.left + i * xStep + (xStep - chartData.barWidth) / 2;
          const barHeight = (item.psi || 0) * yScale;
          const y = height - padding.bottom - barHeight;
          
          return (
            <g key={i}>
              {/* 柱子 */}
              <rect
                x={x}
                y={y}
                width={chartData.barWidth}
                height={barHeight}
                fill={getBarColor(item.psi || 0)}
                rx="2"
                className="transition-opacity hover:opacity-80"
              />
              {/* PSI值标签 */}
              <text
                x={x + chartData.barWidth / 2}
                y={y - 5}
                textAnchor="middle"
                fontSize="9"
                fill="#374151"
                className="dark:fill-gray-300"
              >
                {(item.psi || 0).toFixed(3)}
              </text>
              {/* X轴标签 */}
              <text
                x={x + chartData.barWidth / 2}
                y={height - padding.bottom + 15}
                textAnchor="middle"
                fontSize="9"
                fill="#6b7280"
                transform={`rotate(-30, ${x + chartData.barWidth / 2}, ${height - padding.bottom + 15})`}
              >
                {`规则${i + 1}`}
              </text>
            </g>
          );
        })}
        
        {/* 坐标轴 */}
        <line 
          x1={padding.left} 
          y1={height - padding.bottom} 
          x2={width - padding.right} 
          y2={height - padding.bottom} 
          stroke="#374151" 
          strokeWidth="1"
        />
        <line 
          x1={padding.left} 
          y1={padding.top} 
          x2={padding.left} 
          y2={height - padding.bottom} 
          stroke="#374151" 
          strokeWidth="1"
        />
        
        {/* Y轴标签 */}
        <text 
          x={15} 
          y={height / 2} 
          textAnchor="middle" 
          fontSize="10" 
          fill="#6b7280" 
          transform={`rotate(-90, 15, ${height / 2})`}
        >PSI值</text>
        
        {/* 图例 */}
        <g transform={`translate(${padding.left + 10}, ${padding.top - 15})`}>
          <rect x="0" y="-6" width="10" height="10" fill="#22c55e" rx="1"/>
          <text x="14" y="3" fontSize="9" fill="#6b7280">稳定(&lt;0.1)</text>
          <rect x="70" y="-6" width="10" height="10" fill="#f59e0b" rx="1"/>
          <text x="84" y="3" fontSize="9" fill="#6b7280">轻微(0.1-0.25)</text>
          <rect x="160" y="-6" width="10" height="10" fill="#ef4444" rx="1"/>
          <text x="174" y="3" fontSize="9" fill="#6b7280">显著(≥0.25)</text>
        </g>
      </svg>
    </div>
  );
}

// ========== 规则来源统计组件（组合树模式） ==========
function RuleSourceStatsPanel({ stats }: { stats: RuleSourceStats }) {
  return (
    <div className="space-y-4">
      {/* 概览信息 */}
      <div className="flex items-center gap-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
        <div className="flex items-center gap-2">
          <Layers className="h-4 w-4 text-blue-600" />
          <span className="text-sm font-medium">组合树挖掘模式</span>
        </div>
        <Badge variant="secondary">{stats.total_rules} 条规则</Badge>
        <Badge variant="outline">{stats.total_combinations} 个特征组合</Badge>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* 特征组合覆盖统计 */}
        <div className="border rounded-lg p-3">
          <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
            <GitBranch className="h-4 w-4 text-purple-600" />
            特征组合覆盖统计
          </h4>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {stats.combination_stats.map((item, idx) => (
              <div key={idx} className="flex items-center gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="font-mono truncate" title={item.combination}>
                      {item.combination}
                    </span>
                    <span className="text-gray-500 ml-2 whitespace-nowrap">
                      {item.rule_count} 条 ({item.percentage}%)
                    </span>
                  </div>
                  <div className="h-1.5 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-purple-500 rounded-full transition-all"
                      style={{ width: `${item.percentage}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
        
        {/* 特征重要性（按规则覆盖） */}
        <div className="border rounded-lg p-3">
          <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
            <BarChart3 className="h-4 w-4 text-green-600" />
            特征重要性（按规则覆盖）
          </h4>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {stats.feature_importance.map((item, idx) => (
              <div key={idx} className="flex items-center gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="font-mono truncate" title={item.feature}>
                      {item.feature}
                    </span>
                    <span className="text-gray-500 ml-2 whitespace-nowrap">
                      {item.rule_count} 条 ({item.percentage}%)
                    </span>
                  </div>
                  <div className="h-1.5 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-green-500 rounded-full transition-all"
                      style={{ width: `${item.percentage}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
      
      {/* 说明信息 */}
      <div className="text-xs text-gray-500 p-2 bg-gray-50 dark:bg-gray-900/30 rounded">
        <Info className="h-3 w-3 inline mr-1" />
        组合树模式通过遍历多个特征组合训练决策树，可发现更多样化的规则。
        由于规则来自不同的树，无法用单棵决策树展示全部规则的生成过程。
      </div>
    </div>
  );
}

// ========== 决策树可视化组件 ==========
function DecisionTreePanel({ treeData }: { treeData: TreeStructure }) {
  const [dialogScale, setDialogScale] = useState(1);  // 弹窗专用缩放状态
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [dialogSize, setDialogSize] = useState({ width: 0, height: 0 }); // 弹窗实际大小
  const [dialogPosition, setDialogPosition] = useState({ x: 0, y: 0 }); // 弹窗位置
  const containerRef = useRef<HTMLDivElement>(null);
  const dialogContentRef = useRef<HTMLDivElement>(null);
  const resizeRef = useRef<{ startX: number; startY: number; startWidth: number; startHeight: number } | null>(null);
  const dragRef = useRef<{ startX: number; startY: number; startPosX: number; startPosY: number } | null>(null);
  
  // 拖拽移动弹窗的处理函数
  const handleDragStart = (e: React.MouseEvent) => {
    // 只响应标题栏的拖拽
    if ((e.target as HTMLElement).closest('button')) return;
    e.preventDefault();
    
    dragRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      startPosX: dialogPosition.x,
      startPosY: dialogPosition.y,
    };
    
    const handleMouseMove = (e: MouseEvent) => {
      if (!dragRef.current) return;
      const { startX, startY, startPosX, startPosY } = dragRef.current;
      const deltaX = e.clientX - startX;
      const deltaY = e.clientY - startY;
      setDialogPosition({ x: startPosX + deltaX, y: startPosY + deltaY });
    };
    
    const handleMouseUp = () => {
      dragRef.current = null;
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
    
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  };
  
  // 拖拽调整大小的处理函数
  const handleResizeStart = (e: React.MouseEvent) => {
    e.preventDefault();
    const dialog = dialogContentRef.current;
    if (!dialog) return;
    
    resizeRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      startWidth: dialog.offsetWidth,
      startHeight: dialog.offsetHeight,
    };
    
    const handleMouseMove = (e: MouseEvent) => {
      if (!resizeRef.current) return;
      const { startX, startY, startWidth, startHeight } = resizeRef.current;
      const newWidth = Math.max(400, Math.min(window.innerWidth * 0.95, startWidth + e.clientX - startX));
      const newHeight = Math.max(300, Math.min(window.innerHeight * 0.95, startHeight + e.clientY - startY));
      setDialogSize({ width: newWidth, height: newHeight });
    };
    
    const handleMouseUp = () => {
      resizeRef.current = null;
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
    
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  };
  
  // 基础尺寸参数
  const baseWidth = 800;
  const nodeWidth = 120;
  const nodeHeight = 60;
  const levelHeight = 100;
  
  // 根据树的宽度（叶节点数）动态计算所需宽度
  const calculatedWidth = Math.max(baseWidth, treeData.n_leaves * (nodeWidth + 20));
  const calculatedHeight = Math.min(600, treeData.max_depth * levelHeight + 100);
  
  // 计算树的布局
  const treeLayout = useMemo(() => {
    if (!treeData?.tree) return null;
    
    interface LayoutNode {
      node: TreeNode;
      x: number;
      y: number;
      width: number;
    }
    
    const nodes: LayoutNode[] = [];
    const edges: { from: LayoutNode; to: LayoutNode; label: string }[] = [];
    
    // BFS遍历计算位置
    const queue: { node: TreeNode; depth: number; minX: number; maxX: number }[] = [
      { node: treeData.tree, depth: 0, minX: 0, maxX: calculatedWidth }
    ];
    
    while (queue.length > 0) {
      const { node, depth, minX, maxX } = queue.shift()!;
      const x = (minX + maxX) / 2;
      const y = 30 + depth * levelHeight;
      
      const layoutNode: LayoutNode = { node, x, y, width: maxX - minX };
      nodes.push(layoutNode);
      
      const midX = (minX + maxX) / 2;
      
      if (node.left) {
        const leftNode = { node: node.left, depth: depth + 1, minX, maxX: midX };
        queue.push(leftNode);
      }
      if (node.right) {
        const rightNode = { node: node.right, depth: depth + 1, minX: midX, maxX };
        queue.push(rightNode);
      }
    }
    
    // 构建边
    nodes.forEach(layoutNode => {
      const { node } = layoutNode;
      if (node.left) {
        const leftLayout = nodes.find(n => n.node === node.left);
        if (leftLayout) {
          edges.push({ from: layoutNode, to: leftLayout, label: '≤' });
        }
      }
      if (node.right) {
        const rightLayout = nodes.find(n => n.node === node.right);
        if (rightLayout) {
          edges.push({ from: layoutNode, to: rightLayout, label: '>' });
        }
      }
    });
    
    return { nodes, edges };
  }, [treeData, calculatedWidth]);
  
  // 判断树是否过大需要缩放
  const isTreeLarge = calculatedWidth > baseWidth || treeData.max_depth > 4;
  
  // 自动计算合适的初始缩放比例（用于弹窗的适应窗口功能）
  const autoScale = useMemo(() => {
    if (!isTreeLarge) return 1;
    const widthScale = baseWidth / calculatedWidth;
    const heightScale = 400 / calculatedHeight;
    return Math.min(Math.max(widthScale, heightScale, 0.3), 1);
  }, [isTreeLarge, calculatedWidth, calculatedHeight]);
  
  // 弹窗打开时重置缩放和位置
  useEffect(() => {
    if (isFullscreen) {
      // 根据弹窗大小计算适合的缩放比例
      const dialogWidth = window.innerWidth * 0.8;
      const dialogHeight = window.innerHeight * 0.8 - 120; // 减去工具栏和标题高度
      const widthScale = dialogWidth / calculatedWidth;
      const heightScale = dialogHeight / calculatedHeight;
      const fitScale = Math.min(widthScale, heightScale, 1);
      setDialogScale(Math.max(fitScale, 0.3));
      setDialogSize({ width: dialogWidth, height: dialogHeight + 120 });
      // 居中位置
      setDialogPosition({ 
        x: (window.innerWidth - dialogWidth) / 2, 
        y: (window.innerHeight - dialogHeight - 120) / 2 
      });
    }
  }, [isFullscreen, calculatedWidth, calculatedHeight]);
  
  if (!treeLayout) {
    return <div className="text-center text-gray-500 py-8 text-sm">暂无决策树数据</div>;
  }
  
  // 获取叶节点颜色（根据是否为最优规则和坏账率）
  const getLeafColors = (badRate: number, isOptimal: boolean) => {
    if (!isOptimal) {
      // 未被挖掘为最优规则的叶节点：深灰背景 + 白色文字
      return {
        fill: '#6b7280', // 深灰背景（gray-500）
        stroke: '#4b5563', // 更深边框（gray-600）
        text: 'white' // 白色文字
      };
    }
    // 最优规则叶节点：基于坏账率的渐变色（绿色到红色）
    const hue = (1 - Math.min(badRate, 1)) * 120; // 120=绿色, 0=红色
    return {
      fill: `hsl(${hue}, 65%, 50%)`,
      stroke: `hsl(${hue}, 70%, 40%)`,
      text: 'white'
    };
  };
  
  // 分裂节点样式（紫色系，与叶节点绿色形成强对比）
  const splitNodeStyle = {
    fill: 'rgba(139, 92, 246, 0.15)', // 紫色半透明背景
    stroke: '#8b5cf6', // 紫色边框
    titleColor: '#5b21b6', // 深紫标题
    textColor: '#7c3aed', // 紫色文字
    subTextColor: '#a78bfa' // 浅紫次要文字
  };
  
  // 渲染树图SVG - Tab页用（自适应宽度）
  const renderTreeSvgAutoFit = () => (
    <svg 
      style={{ width: '100%', maxHeight: '380px' }}
      viewBox={`0 0 ${calculatedWidth} ${calculatedHeight}`}
      preserveAspectRatio="xMidYMid meet"
      className="mx-auto"
    >
      {renderSvgContent()}
    </svg>
  );
  
  // 渲染树图SVG - 弹窗用（支持缩放）
  const renderTreeSvgWithScale = (displayScale: number) => (
    <svg 
      width={calculatedWidth * displayScale} 
      height={calculatedHeight * displayScale}
      viewBox={`0 0 ${calculatedWidth} ${calculatedHeight}`}
      className="mx-auto"
    >
      {renderSvgContent()}
    </svg>
  );
  
  // SVG 内容（共享）
  const renderSvgContent = () => (
    <>
      {/* 定义渐变和阴影 */}
      <defs>
        {/* 分裂节点渐变（紫色系） */}
        <linearGradient id="splitNodeGradient" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="rgba(139, 92, 246, 0.25)" />
          <stop offset="100%" stopColor="rgba(139, 92, 246, 0.1)" />
        </linearGradient>
        {/* 节点阴影 */}
        <filter id="nodeShadow" x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="0" dy="2" stdDeviation="2" floodOpacity="0.15"/>
        </filter>
        {/* 叶节点渐变模板 */}
        <linearGradient id="leafGradientGreen" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="hsl(120, 65%, 55%)" />
          <stop offset="100%" stopColor="hsl(120, 65%, 45%)" />
        </linearGradient>
        <linearGradient id="leafGradientYellow" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="hsl(60, 65%, 55%)" />
          <stop offset="100%" stopColor="hsl(60, 65%, 45%)" />
        </linearGradient>
        <linearGradient id="leafGradientOrange" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="hsl(30, 65%, 55%)" />
          <stop offset="100%" stopColor="hsl(30, 65%, 45%)" />
        </linearGradient>
        <linearGradient id="leafGradientRed" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="hsl(0, 65%, 55%)" />
          <stop offset="100%" stopColor="hsl(0, 65%, 45%)" />
        </linearGradient>
      </defs>
      
      {/* 绘制边（曲线连接） */}
      {treeLayout.edges.map((edge, i) => {
        const startX = edge.from.x;
        const startY = edge.from.y + nodeHeight / 2;
        const endX = edge.to.x;
        const endY = edge.to.y - nodeHeight / 2;
        const midY = (startY + endY) / 2;
        
        // 使用贝塞尔曲线
        const path = `M ${startX} ${startY} C ${startX} ${midY}, ${endX} ${midY}, ${endX} ${endY}`;
        
        return (
          <g key={`edge-${i}`}>
            <path
              d={path}
              fill="none"
              stroke="#94a3b8"
              strokeWidth="2"
              strokeLinecap="round"
            />
            {/* 边标签背景 */}
            <rect
              x={(startX + endX) / 2 + (edge.label === '≤' ? -18 : 2)}
              y={(startY + endY) / 2 - 8}
              width="16"
              height="16"
              rx="8"
              fill="white"
              stroke="#e2e8f0"
              strokeWidth="1"
            />
            <text
              x={(startX + endX) / 2 + (edge.label === '≤' ? -10 : 10)}
              y={(startY + endY) / 2 + 4}
              fontSize="10"
              fill="#64748b"
              textAnchor="middle"
              fontWeight="500"
            >
              {edge.label}
            </text>
          </g>
        );
      })}
      
      {/* 绘制节点 */}
      {treeLayout.nodes.map((layoutNode, i) => {
        const { node, x, y } = layoutNode;
        // 兼容处理：后端可能返回字符串 'True'/'False' 或布尔值
        const isLeaf = node.is_leaf === true || node.is_leaf === 'True' || node.is_leaf === 'true';
        // 检查是否为最优规则叶节点
        const isOptimal = node.is_optimal === true || node.is_optimal === 'True' || node.is_optimal === 'true';
        const leafColors = isLeaf ? getLeafColors(node.bad_rate, isOptimal) : null;
        
        return (
          <g key={`node-${i}`} transform={`translate(${x - nodeWidth/2}, ${y - nodeHeight/2})`}>
            {isLeaf ? (
              /* 叶节点：实心填充，圆角矩形，带阴影 */
              <>
                <rect
                  width={nodeWidth}
                  height={nodeHeight}
                  rx="8"
                  fill={leafColors!.fill}
                  stroke={leafColors!.stroke}
                  strokeWidth="2"
                  filter="url(#nodeShadow)"
                />
                {/* 叶节点图标/标记 */}
                <circle
                  cx={nodeWidth - 12}
                  cy="12"
                  r="6"
                  fill="rgba(255,255,255,0.3)"
                />
                <text x={nodeWidth - 12} y="16" textAnchor="middle" fontSize="8" fill="white" fontWeight="bold">
                  ●
                </text>
                
                {/* 叶节点内容 */}
                <text x={nodeWidth/2} y="18" textAnchor="middle" fontSize="11" fill="white" fontWeight="bold">
                  {node.predicted_class}
                </text>
                <text x={nodeWidth/2} y="33" textAnchor="middle" fontSize="9" fill="rgba(255,255,255,0.9)">
                  样本: {node.samples?.toLocaleString()}
                </text>
                <text x={nodeWidth/2} y="48" textAnchor="middle" fontSize="10" fill="white" fontWeight="600">
                  坏账率: {(node.bad_rate * 100).toFixed(1)}%
                </text>
              </>
            ) : (
              /* 分裂节点：空心/半透明，虚线边框效果 */
              <>
                <rect
                  width={nodeWidth}
                  height={nodeHeight}
                  rx="8"
                  fill="url(#splitNodeGradient)"
                  stroke={splitNodeStyle.stroke}
                  strokeWidth="2"
                  strokeDasharray="0"
                  filter="url(#nodeShadow)"
                />
                {/* 分裂图标 */}
                <path
                  d={`M ${nodeWidth - 16} 8 L ${nodeWidth - 16} 16 M ${nodeWidth - 20} 12 L ${nodeWidth - 12} 12`}
                  stroke={splitNodeStyle.stroke}
                  strokeWidth="2"
                  strokeLinecap="round"
                />
                
                {/* 分裂节点内容 */}
                <text x={nodeWidth/2 - 6} y="17" textAnchor="middle" fontSize="10" fill={splitNodeStyle.titleColor} fontWeight="bold">
                  {(node.feature || '').length > 10 ? (node.feature || '').slice(0, 10) + '...' : node.feature}
                </text>
                <text x={nodeWidth/2} y="32" textAnchor="middle" fontSize="10" fill={splitNodeStyle.textColor} fontWeight="500">
                  ≤ {node.threshold?.toFixed(2)}
                </text>
                <text x={nodeWidth/2} y="47" textAnchor="middle" fontSize="8" fill={splitNodeStyle.subTextColor}>
                  {node.samples?.toLocaleString()} 样本 | {(node.bad_rate * 100).toFixed(1)}%
                </text>
              </>
            )}
          </g>
        );
      })}
    </>
  );
  
  return (
    <div className="space-y-4">
      {/* 树信息概览 */}
      <div className="grid grid-cols-4 gap-3">
        <div className="p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
          <div className="text-xs text-blue-600 font-medium mb-1">树深度</div>
          <div className="text-2xl font-bold text-blue-700 dark:text-blue-300">
            {treeData.max_depth}
          </div>
        </div>
        <div className="p-3 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800">
          <div className="text-xs text-green-600 font-medium mb-1">叶节点数</div>
          <div className="text-2xl font-bold text-green-700 dark:text-green-300">
            {treeData.n_leaves}
          </div>
        </div>
        <div className="p-3 rounded-lg bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800">
          <div className="text-xs text-purple-600 font-medium mb-1">特征数</div>
          <div className="text-2xl font-bold text-purple-700 dark:text-purple-300">
            {treeData.n_features}
          </div>
        </div>
        <div className="p-3 rounded-lg bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800">
          <div className="text-xs text-orange-600 font-medium mb-1">类别数</div>
          <div className="text-2xl font-bold text-orange-700 dark:text-orange-300">
            {treeData.n_classes}
          </div>
        </div>
      </div>
      
      {/* 决策树图形 */}
      <div className="border rounded-lg p-4 bg-white dark:bg-gray-900">
        <div className="flex items-center justify-between mb-3">
          <div className="text-sm font-medium text-gray-700 dark:text-gray-300 flex items-center gap-2">
            <TrendingUp className="h-4 w-4" />
            决策树结构图
            <span className="text-xs text-gray-500">
              （自动适配页面宽度）
            </span>
          </div>
          
          {/* 仅保留全屏按钮 */}
          <div className="flex items-center gap-1">
            <Dialog open={isFullscreen} onOpenChange={setIsFullscreen}>
              <DialogTrigger asChild>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 px-2 gap-1"
                  title="全屏查看（支持缩放和拖拽）"
                >
                  <Maximize2 className="h-3.5 w-3.5" />
                  <span className="text-xs">全屏查看</span>
                </Button>
              </DialogTrigger>
              {/* 使用 Portal 渲染自定义可拖拽弹窗 */}
              {isFullscreen && (
                <>
                  {/* 背景遮罩 */}
                  <div 
                    className="fixed inset-0 bg-black/50 z-50"
                    onClick={() => setIsFullscreen(false)}
                  />
                  {/* 可拖拽弹窗 */}
                  <div
                    ref={dialogContentRef}
                    className="fixed z-50 flex flex-col bg-white dark:bg-gray-900 rounded-lg shadow-2xl border"
                    style={{ 
                      width: dialogSize.width || '80vw', 
                      height: dialogSize.height || '80vh',
                      left: dialogPosition.x,
                      top: dialogPosition.y,
                      maxWidth: '95vw',
                      maxHeight: '95vh',
                    }}
                  >
                    {/* 可拖拽标题栏 */}
                    <div 
                      className="flex-shrink-0 p-4 pb-2 border-b cursor-move select-none flex items-center justify-between"
                      onMouseDown={handleDragStart}
                    >
                      <div className="flex items-center gap-2">
                        <TrendingUp className="h-5 w-5" />
                        <span className="font-semibold">决策树结构图</span>
                        <span className="text-sm font-normal text-gray-500">
                          （深度: {treeData.max_depth}, 叶节点: {treeData.n_leaves}）
                        </span>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 w-7 p-0"
                        onClick={() => setIsFullscreen(false)}
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                    {/* 缩放控制工具栏 */}
                    <div className="flex items-center gap-2 px-4 py-2 border-b flex-shrink-0 bg-gray-50 dark:bg-gray-800">
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-7"
                        onClick={() => setDialogScale(s => Math.max(0.1, s - 0.1))}
                      >
                        <ZoomOut className="h-3.5 w-3.5 mr-1" />
                        缩小
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-7"
                        onClick={() => setDialogScale(s => Math.min(3, s + 0.1))}
                      >
                        <ZoomIn className="h-3.5 w-3.5 mr-1" />
                        放大
                      </Button>
                      <span className="text-sm text-gray-500 min-w-[100px]">
                        当前缩放: {Math.round(dialogScale * 100)}%
                      </span>
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-7"
                        onClick={() => setDialogScale(1)}
                      >
                        100%
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-7"
                        onClick={() => {
                          // 计算适应当前弹窗大小的缩放比例
                          const contentWidth = dialogContentRef.current?.clientWidth || window.innerWidth * 0.8;
                          const contentHeight = (dialogContentRef.current?.clientHeight || window.innerHeight * 0.8) - 140;
                          const fitWidthScale = (contentWidth - 32) / calculatedWidth;
                          const fitHeightScale = contentHeight / calculatedHeight;
                          setDialogScale(Math.min(fitWidthScale, fitHeightScale, 1));
                        }}
                      >
                        适应窗口
                      </Button>
                    </div>
                    {/* 可滚动的树图区域 */}
                    <div 
                      className="flex-1 min-h-0 p-4"
                      style={{
                        overflow: 'auto',
                      }}
                    >
                      {/* 内容容器：设置实际尺寸，让父容器产生滚动条 */}
                      <div 
                        style={{ 
                          width: calculatedWidth * dialogScale,
                          height: calculatedHeight * dialogScale,
                          minWidth: calculatedWidth * dialogScale,
                          minHeight: calculatedHeight * dialogScale,
                        }}
                      >
                        {renderTreeSvgWithScale(dialogScale)}
                      </div>
                    </div>
                    {/* 拖拽调整大小手柄 */}
                    <div
                      className="absolute bottom-0 right-0 w-6 h-6 cursor-se-resize flex items-center justify-center hover:bg-gray-200 dark:hover:bg-gray-700 rounded-tl"
                      onMouseDown={handleResizeStart}
                      title="拖拽调整窗口大小"
                    >
                      <svg width="12" height="12" viewBox="0 0 12 12" className="text-gray-400">
                        <path d="M10 0L0 10M10 4L4 10M10 8L8 10" stroke="currentColor" strokeWidth="1.5" fill="none"/>
                      </svg>
                    </div>
                  </div>
                </>
              )}
            </Dialog>
          </div>
        </div>
        
        {/* 树图容器（自动适配页面宽度） */}
        <div ref={containerRef} className="overflow-hidden">
          {renderTreeSvgAutoFit()}
        </div>
      </div>
      
      {/* 图例说明 */}
      <div className="p-3 rounded-lg bg-gradient-to-r from-purple-50 to-green-50 dark:from-purple-900/20 dark:to-green-900/20 border border-purple-200 dark:border-purple-800">
        <div className="flex items-center gap-2 mb-3">
          <HelpCircle className="h-4 w-4 text-purple-600" />
          <span className="text-sm font-medium text-purple-700 dark:text-purple-400">决策树图例</span>
        </div>
        <div className="grid grid-cols-3 gap-4 text-xs">
          {/* 节点类型图例 */}
          <div className="space-y-2">
            <div className="font-medium text-gray-700 dark:text-gray-300 mb-1">节点类型</div>
            <div className="flex items-center gap-2">
              <div className="w-6 h-4 rounded border-2 border-purple-500 bg-purple-500/20"></div>
              <span className="text-gray-600 dark:text-gray-400">分裂节点（继续分支）</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-6 h-4 rounded bg-gradient-to-b from-green-500 to-green-600 border border-green-600"></div>
              <span className="text-gray-600 dark:text-gray-400">叶节点（终止判定）</span>
            </div>
          </div>
          {/* 叶节点状态图例 */}
          <div className="space-y-2">
            <div className="font-medium text-gray-700 dark:text-gray-300 mb-1">叶节点状态</div>
            <div className="flex items-center gap-2">
              <div className="w-6 h-4 rounded bg-green-500 border border-green-600"></div>
              <span className="text-gray-600 dark:text-gray-400">最优规则（彩色）</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-6 h-4 rounded bg-gray-500 border border-gray-600"></div>
              <span className="text-gray-600 dark:text-gray-400">非最优规则（灰色）</span>
            </div>
          </div>
          {/* 坏账率颜色图例 */}
          <div className="space-y-2">
            <div className="font-medium text-gray-700 dark:text-gray-300 mb-1">最优规则坏账率</div>
            <div className="flex items-center gap-1">
              <div className="w-4 h-4 rounded" style={{background: 'hsl(120, 65%, 50%)'}}></div>
              <span className="text-gray-500">低</span>
              <div className="w-4 h-4 rounded" style={{background: 'hsl(80, 65%, 50%)'}}></div>
              <div className="w-4 h-4 rounded" style={{background: 'hsl(40, 65%, 50%)'}}></div>
              <div className="w-4 h-4 rounded" style={{background: 'hsl(0, 65%, 50%)'}}></div>
              <span className="text-gray-500">高</span>
            </div>
            <div className="text-gray-500 dark:text-gray-400">绿→红表示坏账率低→高</div>
          </div>
        </div>
        <div className="mt-3 pt-2 border-t border-gray-200 dark:border-gray-700 text-xs text-gray-500 dark:text-gray-400">
          • 左分支 ≤ 阈值，右分支 &gt; 阈值 &nbsp;|&nbsp; • 彩色叶节点表示被选为最优规则
        </div>
      </div>
    </div>
  );
}

// ========== 附加分析面板（整合金额分析、先验规则分析） ==========
interface AdvancedAnalysisPanelProps {
  amountAnalysis: Record<string, unknown> | null;
  priorAnalysis: Record<string, unknown> | null;
}

function AdvancedAnalysisPanel({ amountAnalysis, priorAnalysis }: AdvancedAnalysisPanelProps) {
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({
    amount: true,
    prior: true,
  });

  const toggleSection = (section: string) => {
    setOpenSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  const hasAmount = !!amountAnalysis;
  const hasPrior = !!priorAnalysis;

  if (!hasAmount && !hasPrior) {
    return (
      <div className="text-center text-gray-500 py-8 text-sm">
        <Settings2 className="h-8 w-8 mx-auto mb-2 opacity-50" />
        <p>暂无附加分析数据</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* 金额维度分析 */}
      {hasAmount && (
        <Collapsible open={openSections.amount} onOpenChange={() => toggleSection('amount')}>
          <div className="border rounded-lg overflow-hidden">
            <CollapsibleTrigger className="flex items-center justify-between w-full p-3 bg-gray-50 dark:bg-gray-900/30 hover:bg-gray-100 dark:hover:bg-gray-800/50 transition-colors">
              <div className="flex items-center gap-2">
                <DollarSign className="h-4 w-4 text-green-600" />
                <span className="text-sm font-medium">金额维度分析</span>
              </div>
              {openSections.amount ? (
                <ChevronDown className="h-4 w-4 text-gray-500" />
              ) : (
                <ChevronRight className="h-4 w-4 text-gray-500" />
              )}
            </CollapsibleTrigger>
            <CollapsibleContent>
              <div className="p-3">
                <AmountAnalysisPanel amountAnalysis={amountAnalysis} />
              </div>
            </CollapsibleContent>
          </div>
        </Collapsible>
      )}

      {/* 先验规则分析 */}
      {hasPrior && (
        <Collapsible open={openSections.prior} onOpenChange={() => toggleSection('prior')}>
          <div className="border rounded-lg overflow-hidden">
            <CollapsibleTrigger className="flex items-center justify-between w-full p-3 bg-gray-50 dark:bg-gray-900/30 hover:bg-gray-100 dark:hover:bg-gray-800/50 transition-colors">
              <div className="flex items-center gap-2">
                <List className="h-4 w-4 text-purple-600" />
                <span className="text-sm font-medium">先验规则分析</span>
              </div>
              {openSections.prior ? (
                <ChevronDown className="h-4 w-4 text-gray-500" />
              ) : (
                <ChevronRight className="h-4 w-4 text-gray-500" />
              )}
            </CollapsibleTrigger>
            <CollapsibleContent>
              <div className="p-3">
                <PriorAnalysisPanel priorAnalysis={priorAnalysis} />
              </div>
            </CollapsibleContent>
          </div>
        </Collapsible>
      )}
    </div>
  );
}

// ========== 先验规则分析面板 ==========
interface PriorAnalysisPanelProps {
  priorAnalysis: Record<string, unknown>;
}

function PriorAnalysisPanel({ priorAnalysis }: PriorAnalysisPanelProps) {
  // 解析先验规则分析数据
  const summary = priorAnalysis.summary as Record<string, number> | undefined;
  const rules = priorAnalysis.rules as Array<Record<string, unknown>> | undefined;

  return (
    <div className="space-y-4">
      {/* 摘要信息 */}
      {summary && (
        <div className="grid grid-cols-4 gap-3">
          <div className="p-3 rounded-lg bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800">
            <div className="text-xs text-purple-600 font-medium mb-1">先验规则数</div>
            <div className="text-xl font-bold text-purple-700 dark:text-purple-300">
              {summary.prior_rules_count ?? '-'}
            </div>
          </div>
          <div className="p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
            <div className="text-xs text-blue-600 font-medium mb-1">新规则数</div>
            <div className="text-xl font-bold text-blue-700 dark:text-blue-300">
              {summary.new_rules_count ?? '-'}
            </div>
          </div>
          <div className="p-3 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800">
            <div className="text-xs text-green-600 font-medium mb-1">增量召回率</div>
            <div className="text-xl font-bold text-green-700 dark:text-green-300">
              {summary.incremental_recall != null ? `${(summary.incremental_recall * 100).toFixed(2)}%` : '-'}
            </div>
          </div>
          <div className="p-3 rounded-lg bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800">
            <div className="text-xs text-orange-600 font-medium mb-1">平均重叠率</div>
            <div className="text-xl font-bold text-orange-700 dark:text-orange-300">
              {summary.avg_overlap_rate != null ? `${(summary.avg_overlap_rate * 100).toFixed(2)}%` : '-'}
            </div>
          </div>
        </div>
      )}

      {/* 规则详情表格 */}
      {rules && rules.length > 0 && (
        <div className="border rounded-lg overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="bg-gray-50 dark:bg-gray-900/30">
                <TableHead className="text-xs">规则</TableHead>
                <TableHead className="text-xs text-right">独立召回</TableHead>
                <TableHead className="text-xs text-right">增量召回</TableHead>
                <TableHead className="text-xs text-right">重叠率</TableHead>
                <TableHead className="text-xs text-right">边际贡献</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rules.map((rule, index) => (
                <TableRow key={index}>
                  <TableCell className="text-xs font-mono max-w-[300px] truncate">
                    {String(rule.rule ?? '')}
                  </TableCell>
                  <TableCell className="text-xs text-right">
                    {rule.standalone_recall != null ? `${((rule.standalone_recall as number) * 100).toFixed(2)}%` : '-'}
                  </TableCell>
                  <TableCell className="text-xs text-right">
                    {rule.incremental_recall != null ? `${((rule.incremental_recall as number) * 100).toFixed(2)}%` : '-'}
                  </TableCell>
                  <TableCell className="text-xs text-right">
                    {rule.overlap_rate != null ? `${((rule.overlap_rate as number) * 100).toFixed(2)}%` : '-'}
                  </TableCell>
                  <TableCell className="text-xs text-right">
                    {rule.marginal_contribution != null ? `${((rule.marginal_contribution as number) * 100).toFixed(2)}%` : '-'}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {/* 无数据提示 */}
      {(!rules || rules.length === 0) && !summary && (
        <div className="text-center text-gray-500 py-4 text-sm">
          暂无先验规则分析数据
        </div>
      )}
    </div>
  );
}

// 规则稳定性（PSI）报告面板
function PSIReportPanel({ report }: { report: PSIReport[] }) {
  const getStabilityColor = (stability: string) => {
    switch (stability) {
      case "稳定":
        return "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400";
      case "轻微变化":
        return "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400";
      case "显著变化":
        return "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400";
      default:
        return "bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400";
    }
  };

  // 统计稳定性分布
  const stabilityStats = useMemo(() => {
    const stats = { stable: 0, slight: 0, significant: 0, na: 0 };
    report.forEach((r) => {
      switch (r.stability) {
        case "稳定":
          stats.stable++;
          break;
        case "轻微变化":
          stats.slight++;
          break;
        case "显著变化":
          stats.significant++;
          break;
        default:
          stats.na++;
      }
    });
    return stats;
  }, [report]);

  return (
    <div className="space-y-4">
      {/* 稳定性概览 */}
      <div className="grid grid-cols-4 gap-3">
        <div className="p-3 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800">
          <div className="text-xs text-green-600 font-medium mb-1">稳定</div>
          <div className="text-2xl font-bold text-green-700 dark:text-green-300">
            {stabilityStats.stable}
          </div>
          <div className="text-xs text-gray-500">PSI &lt; 0.1</div>
        </div>
        <div className="p-3 rounded-lg bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800">
          <div className="text-xs text-yellow-600 font-medium mb-1">轻微变化</div>
          <div className="text-2xl font-bold text-yellow-700 dark:text-yellow-300">
            {stabilityStats.slight}
          </div>
          <div className="text-xs text-gray-500">0.1 ≤ PSI &lt; 0.25</div>
        </div>
        <div className="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
          <div className="text-xs text-red-600 font-medium mb-1">显著变化</div>
          <div className="text-2xl font-bold text-red-700 dark:text-red-300">
            {stabilityStats.significant}
          </div>
          <div className="text-xs text-gray-500">PSI ≥ 0.25</div>
        </div>
        <div className="p-3 rounded-lg bg-gray-50 dark:bg-gray-900/20 border border-gray-200 dark:border-gray-700">
          <div className="text-xs text-gray-600 font-medium mb-1">无法计算</div>
          <div className="text-2xl font-bold text-gray-700 dark:text-gray-300">
            {stabilityStats.na}
          </div>
          <div className="text-xs text-gray-500">数据不足</div>
        </div>
      </div>

      {/* PSI趋势图 */}
      <div className="border rounded-lg p-4 bg-white dark:bg-gray-900">
        <PSITrendChart data={report} />
      </div>

      {/* PSI详情表格 */}
      <div className="border rounded-lg overflow-hidden">
        <div className="max-h-[400px] overflow-auto">
          <Table>
            <TableHeader className="sticky top-0 bg-gray-50 dark:bg-gray-900">
              <TableRow>
                <TableHead className="text-xs">规则</TableHead>
                <TableHead className="text-xs text-right">基准命中率</TableHead>
                <TableHead className="text-xs text-right">对比命中率</TableHead>
                <TableHead className="text-xs text-right">PSI</TableHead>
                <TableHead className="text-xs text-center">稳定性</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {report.map((row, i) => (
                <TableRow key={i}>
                  <TableCell className="text-xs font-mono truncate max-w-[250px]" title={row.rule}>
                    {row.rule}
                  </TableCell>
                  <TableCell className="text-xs text-right">
                    {row.hit_rate_base !== null ? (row.hit_rate_base * 100).toFixed(2) + "%" : "-"}
                  </TableCell>
                  <TableCell className="text-xs text-right">
                    {row.hit_rate_compare !== null ? (row.hit_rate_compare * 100).toFixed(2) + "%" : "-"}
                  </TableCell>
                  <TableCell className="text-xs text-right font-medium">
                    {row.psi !== null ? row.psi.toFixed(4) : "-"}
                  </TableCell>
                  <TableCell className="text-center">
                    <Badge className={cn("text-xs", getStabilityColor(row.stability))}>
                      {row.stability}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>

      {/* PSI说明 */}
      <div className="p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
        <div className="flex items-center gap-2 mb-2">
          <HelpCircle className="h-4 w-4 text-blue-600" />
          <span className="text-sm font-medium text-blue-700 dark:text-blue-400">PSI指标说明</span>
        </div>
        <div className="text-xs text-blue-700 dark:text-blue-400 space-y-1">
          <p>PSI（Population Stability Index）用于衡量规则在不同样本集上的稳定性。</p>
          <p>• PSI &lt; 0.1：规则稳定，可直接使用</p>
          <p>• 0.1 ≤ PSI &lt; 0.25：规则有轻微变化，需关注</p>
          <p>• PSI ≥ 0.25：规则显著变化，建议重新评估</p>
        </div>
      </div>
    </div>
  );
}

// ========== 样本及特征面板 ==========
interface SampleFeaturePanelProps {
  stagesData: Record<string, StageProgress>;
}

function SampleFeaturePanel({ stagesData }: SampleFeaturePanelProps) {
  // 获取preprocessing阶段数据
  const preprocessingData = stagesData?.preprocessing?.output_preview || {};
  // 获取feature_engineering阶段数据（可能不存在或被跳过）
  const feData = stagesData?.feature_engineering?.output_preview || {};
  
  // 使用新的多步骤流程数据（如果有）
  const selectionFlow = feData.selection_flow || [];
  
  // 判断是否有特征工程数据（兼容新旧数据结构）
  // 优先级：selection_flow 有数据时直接显示（忽略 skipped 标记）
  // 否则检查 before_count/after_count 且非 skipped
  const hasFeatureEngineering = feData && (
    selectionFlow.length > 0 ||  // 新结构：selection_flow有数据就显示
    (!feData.skipped && (feData.before_count !== undefined || feData.after_count !== undefined))
  );
  
  // 时间范围信息（规则挖掘任务可能也支持）
  const timeRangeInfo = preprocessingData.time_range_info;
  
  // 解析衍生特征信息
  // P1-4: 数据源从 preprocessingData 迁移到 feData（datetime/text 衍生已移至特征工程阶段）
  const derivedFeatures = feData.derived_features || preprocessingData.derived_features || {};
  const totalDerived = derivedFeatures.total_derived || 0;
  
  return (
    <div className="space-y-4">
      {/* 样本概览 - 简单列表展示 */}
      <div>
        <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
          <Database className="h-4 w-4 text-blue-600" />
          样本概览
        </h4>
        <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="space-y-2 text-sm">
            <div className="flex justify-between items-center py-1 border-b border-gray-200 dark:border-gray-700">
              <span className="text-gray-600 dark:text-gray-400">总样本数</span>
              <span className="font-medium">{preprocessingData.rows?.toLocaleString() || "-"}</span>
            </div>
            <div className="flex justify-between items-center py-1 border-b border-gray-200 dark:border-gray-700">
              <span className="text-gray-600 dark:text-gray-400">总体坏账率</span>
              <span className="font-medium text-purple-600">
                {preprocessingData.target_rate ? `${(preprocessingData.target_rate * 100).toFixed(2)}%` : "-"}
              </span>
            </div>
            {preprocessingData.split_info && (
              <>
                <div className="flex justify-between items-center py-1 border-b border-gray-200 dark:border-gray-700">
                  <span className="text-gray-600 dark:text-gray-400">训练集</span>
                  <span className="font-medium">
                    {preprocessingData.split_info.train?.toLocaleString() || "-"}
                    <span className="text-xs text-gray-500 ml-2">
                      (坏账率: {preprocessingData.split_info.train_target_rate 
                        ? `${(preprocessingData.split_info.train_target_rate * 100).toFixed(2)}%`
                        : "-"})
                    </span>
                  </span>
                </div>
                <div className="flex justify-between items-center py-1">
                  <span className="text-gray-600 dark:text-gray-400">测试集</span>
                  <span className="font-medium">
                    {preprocessingData.split_info.test?.toLocaleString() || "-"}
                    <span className="text-xs text-gray-500 ml-2">
                      (坏账率: {preprocessingData.split_info.test_target_rate 
                        ? `${(preprocessingData.split_info.test_target_rate * 100).toFixed(2)}%`
                        : "-"})
                    </span>
                  </span>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* 时间范围（始终展示） */}
      <div>
        <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
          <Calendar className="h-4 w-4 text-purple-600" />
          时间范围
          {timeRangeInfo?.column && (
            <span className="text-xs font-normal text-gray-500">({timeRangeInfo.column})</span>
          )}
        </h4>
        <div className="grid grid-cols-2 gap-2">
          {/* 训练集时间范围 */}
          <div className="text-center p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg border border-purple-200 dark:border-purple-800">
            <div className="text-xs text-gray-500 mb-1">训练集</div>
            {timeRangeInfo?.train ? (
              <>
                <div className="text-sm font-medium text-purple-600">{timeRangeInfo.train.min}</div>
                <div className="text-gray-400 text-xs">至</div>
                <div className="text-sm font-medium text-purple-600">{timeRangeInfo.train.max}</div>
              </>
            ) : (
              <div className="text-gray-400 text-sm">-</div>
            )}
          </div>
          {/* 测试集时间范围 */}
          <div className="text-center p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg border border-purple-200 dark:border-purple-800">
            <div className="text-xs text-gray-500 mb-1">测试集</div>
            {timeRangeInfo?.test ? (
              <>
                <div className="text-sm font-medium text-purple-600">{timeRangeInfo.test.min}</div>
                <div className="text-gray-400 text-xs">至</div>
                <div className="text-sm font-medium text-purple-600">{timeRangeInfo.test.max}</div>
              </>
            ) : (
              <div className="text-gray-400 text-sm">-</div>
            )}
          </div>
        </div>
      </div>

      {/* 特征概览 */}
      <div>
        <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
          <BarChart3 className="h-4 w-4 text-green-600" />
          特征概览
        </h4>
        <div className="grid grid-cols-3 gap-3">
          <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
            <div className="text-2xl font-bold text-green-600">
              {preprocessingData.feature_count || "-"}
              {totalDerived > 0 && (
                <span className="text-base font-normal text-cyan-600 ml-1">
                  (+{totalDerived})
                </span>
              )}
            </div>
            <div className="text-xs text-gray-500">
              {totalDerived > 0 ? "原始特征（+衍生）" : "原始特征数"}
            </div>
          </div>
          <div className="p-3 bg-teal-50 dark:bg-teal-900/20 rounded-lg border border-teal-200 dark:border-teal-800">
            <div className="text-2xl font-bold text-teal-600">
              {feData.after_count ?? "-"}
            </div>
            <div className="text-xs text-gray-500">筛选后特征</div>
          </div>
          <div className="p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg border border-yellow-200 dark:border-yellow-800">
            <div className="text-2xl font-bold text-yellow-600">
              {preprocessingData.missing_rate !== undefined 
                ? `${(preprocessingData.missing_rate * 100).toFixed(1)}%` 
                : "-"}
            </div>
            <div className="text-xs text-gray-500">平均缺失率</div>
          </div>
        </div>
      </div>

      {/* 特征变化流程 - 多步骤展示（参考右侧面板设计，兼容新旧数据结构） */}
      {hasFeatureEngineering && (
        <div className="p-3 bg-gradient-to-r from-gray-50 to-green-50 dark:from-gray-900/30 dark:to-green-900/20 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="text-sm font-medium mb-2">特征变化流程</div>
          <div className="flex items-center justify-between text-xs overflow-x-auto">
            {selectionFlow.length > 0 ? (
              // 新结构：使用selection_flow数组
              selectionFlow.map((step: any, idx: number) => (
                <React.Fragment key={idx}>
                  {idx > 0 && <div className="text-gray-400 mx-1 flex-shrink-0">→</div>}
                  <div className="text-center flex-shrink-0 min-w-[50px]">
                    <div className={`text-lg font-bold ${
                      idx === selectionFlow.length - 1 ? 'text-green-600' : 
                      step.removed > 0 ? 'text-orange-600' : 
                      step.added > 0 ? 'text-purple-600' : ''
                    }`}>
                      {step.count}
                    </div>
                    <div className="text-gray-500 text-[10px]">{step.step}</div>
                    {step.removed > 0 && (
                      <div className="text-[10px] text-red-500">-{step.removed}</div>
                    )}
                    {step.added > 0 && (
                      <div className="text-[10px] text-purple-500">+{step.added}</div>
                    )}
                  </div>
                </React.Fragment>
              ))
            ) : (
              // 旧结构：使用before_count/after_count等字段
              <>
                {/* 初始特征数 */}
                <div className="text-center flex-shrink-0 min-w-[50px]">
                  <div className="text-lg font-bold">{feData.before_count || "-"}</div>
                  <div className="text-gray-500 text-[10px]">初始</div>
                </div>
                
                {/* 缺失率筛选（如果有） */}
                {feData.missing_filter_stats && (
                  <>
                    <div className="text-gray-400 mx-1 flex-shrink-0">→</div>
                    <div className="text-center flex-shrink-0 min-w-[50px]">
                      <div className={`text-lg font-bold ${feData.missing_filter_stats.removed_count > 0 ? 'text-orange-600' : ''}`}>
                        {(feData.before_count || 0) - (feData.missing_filter_stats.removed_count || 0)}
                      </div>
                      <div className="text-gray-500 text-[10px]">缺失率筛选</div>
                      {feData.missing_filter_stats.removed_count > 0 && (
                        <div className="text-[10px] text-red-500">-{feData.missing_filter_stats.removed_count}</div>
                      )}
                    </div>
                  </>
                )}
                
                {/* One-Hot编码（如果有） */}
                {feData.onehot_stats && feData.onehot_stats.derived_count > 0 && (
                  <>
                    <div className="text-gray-400 mx-1 flex-shrink-0">→</div>
                    <div className="text-center flex-shrink-0 min-w-[50px]">
                      <div className="text-lg font-bold text-purple-600">{feData.after_onehot_count || "-"}</div>
                      <div className="text-gray-500 text-[10px]">One-Hot后</div>
                      <div className="text-[10px] text-purple-500">
                        -{feData.onehot_stats.original_count}+{feData.onehot_stats.derived_count}
                      </div>
                    </div>
                  </>
                )}
                
                {/* IV筛选后 */}
                <div className="text-gray-400 mx-1 flex-shrink-0">→</div>
                <div className="text-center flex-shrink-0 min-w-[50px]">
                  <div className="text-lg font-bold text-green-600">{feData.after_count || "-"}</div>
                  <div className="text-gray-500 text-[10px]">筛选后</div>
                  {feData.removed_reasons && Object.keys(feData.removed_reasons).length > 0 && (
                    <div className="text-[10px] text-red-500">
                      -{Object.values(feData.removed_reasons).reduce((a: number, b: unknown) => a + (b as number), 0)}
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      )}

    </div>
  );
}

export default RuleMiningResults;
