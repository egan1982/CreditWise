"use client";

import React, { useState, useEffect, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Target,
  Download,
  CheckCircle2,
  TrendingUp,
  BarChart3,
  Calculator,
  Loader2,
  Activity,
  Percent,
  Layers,
  HelpCircle,
  LineChart,
  ArrowLeftRight,
  Database,
  AlertTriangle,
  GitBranch,
  ChevronRight,
} from "lucide-react";
import { ModelStatisticsPanel } from "./ModelStatisticsPanel";
import { sopService, ExecutionResult, StageProgress } from "@/lib/sopService";
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
import { Info, ShieldCheck, Calendar } from "lucide-react";

// ========== 指标评估辅助函数 ==========

type MetricLevel = 'excellent' | 'good' | 'acceptable' | 'poor';

interface MetricEvaluation {
  label: string;
  level: MetricLevel;
  colorClass: string;
}

// 获取KS评估结果
function getKSLevel(ks: number): MetricEvaluation {
  if (ks >= 0.4) return { label: '优秀', level: 'excellent', colorClass: 'text-green-600 dark:text-green-400' };
  if (ks >= 0.3) return { label: '良好', level: 'good', colorClass: 'text-blue-600 dark:text-blue-400' };
  if (ks >= 0.2) return { label: '可用', level: 'acceptable', colorClass: 'text-yellow-600 dark:text-yellow-400' };
  return { label: '较差', level: 'poor', colorClass: 'text-red-600 dark:text-red-400' };
}

// 获取AUC评估结果
function getAUCLevel(auc: number): MetricEvaluation {
  if (auc >= 0.8) return { label: '优秀', level: 'excellent', colorClass: 'text-green-600 dark:text-green-400' };
  if (auc >= 0.75) return { label: '良好', level: 'good', colorClass: 'text-blue-600 dark:text-blue-400' };
  if (auc >= 0.7) return { label: '可用', level: 'acceptable', colorClass: 'text-yellow-600 dark:text-yellow-400' };
  return { label: '较差', level: 'poor', colorClass: 'text-red-600 dark:text-red-400' };
}

// 获取Gini评估结果
function getGiniLevel(gini: number): MetricEvaluation {
  if (gini >= 0.6) return { label: '优秀', level: 'excellent', colorClass: 'text-green-600 dark:text-green-400' };
  if (gini >= 0.5) return { label: '良好', level: 'good', colorClass: 'text-blue-600 dark:text-blue-400' };
  if (gini >= 0.4) return { label: '可用', level: 'acceptable', colorClass: 'text-yellow-600 dark:text-yellow-400' };
  return { label: '较差', level: 'poor', colorClass: 'text-red-600 dark:text-red-400' };
}

// ========== 简单SVG图表组件 ==========

// ROC曲线图
function ROCChart({ data }: { data: { fpr: number[]; tpr: number[]; auc: number } }) {
  const width = 280;
  const height = 180;
  const padding = 30;
  
  const points = useMemo(() => {
    if (!data.fpr || !data.tpr) return "";
    const xScale = (width - 2 * padding) / 1;
    const yScale = (height - 2 * padding) / 1;
    
    return data.fpr.map((fpr, i) => {
      const x = padding + fpr * xScale;
      const y = height - padding - data.tpr[i] * yScale;
      return `${x},${y}`;
    }).join(" ");
  }, [data]);
  
  return (
    <svg width={width} height={height} className="mx-auto">
      {/* 背景网格 */}
      <defs>
        <pattern id="grid" width="40" height="30" patternUnits="userSpaceOnUse">
          <path d="M 40 0 L 0 0 0 30" fill="none" stroke="#e5e7eb" strokeWidth="0.5"/>
        </pattern>
      </defs>
      <rect x={padding} y={padding} width={width - 2*padding} height={height - 2*padding} fill="url(#grid)"/>
      
      {/* 对角线 */}
      <line x1={padding} y1={height - padding} x2={width - padding} y2={padding} 
            stroke="#9ca3af" strokeWidth="1" strokeDasharray="4,4"/>
      
      {/* ROC曲线 */}
      <polyline points={points} fill="none" stroke="#2563eb" strokeWidth="2"/>
      
      {/* 填充区域 */}
      <polygon 
        points={`${padding},${height - padding} ${points} ${width - padding},${height - padding}`}
        fill="rgba(37, 99, 235, 0.1)"
      />
      
      {/* 坐标轴 */}
      <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="#374151" strokeWidth="1"/>
      <line x1={padding} y1={padding} x2={padding} y2={height - padding} stroke="#374151" strokeWidth="1"/>
      
      {/* 标签 */}
      <text x={width / 2} y={height - 5} textAnchor="middle" fontSize="10" fill="#6b7280">FPR</text>
      <text x={10} y={height / 2} textAnchor="middle" fontSize="10" fill="#6b7280" transform={`rotate(-90, 10, ${height/2})`}>TPR</text>
    </svg>
  );
}

// KS曲线图
function KSChart({ data }: { data: { population_pct: number[]; cum_bad: number[]; cum_good: number[]; ks_curve: number[]; ks_max: number; ks_max_position: number } }) {
  const width = 280;
  const height = 180;
  const padding = 30;
  
  const { badPoints, goodPoints, ksPoints, ksMaxIdx } = useMemo(() => {
    if (!data.population_pct) return { badPoints: "", goodPoints: "", ksPoints: "", ksMaxIdx: 0 };
    
    const xScale = (width - 2 * padding) / 100;
    const yScale = (height - 2 * padding) / 100;
    const step = Math.max(1, Math.floor(data.population_pct.length / 50));
    
    let badPts = "";
    let goodPts = "";
    let ksPts = "";
    let maxIdx = 0;
    let maxKs = 0;
    
    for (let i = 0; i < data.population_pct.length; i += step) {
      const x = padding + data.population_pct[i] * xScale;
      const yBad = height - padding - data.cum_bad[i] * yScale;
      const yGood = height - padding - data.cum_good[i] * yScale;
      const yKs = height - padding - data.ks_curve[i] * yScale;
      
      badPts += `${x},${yBad} `;
      goodPts += `${x},${yGood} `;
      ksPts += `${x},${yKs} `;
      
      if (data.ks_curve[i] > maxKs) {
        maxKs = data.ks_curve[i];
        maxIdx = i;
      }
    }
    
    return { badPoints: badPts.trim(), goodPoints: goodPts.trim(), ksPoints: ksPts.trim(), ksMaxIdx: maxIdx };
  }, [data]);
  
  const ksMaxX = padding + data.ks_max_position * (width - 2 * padding) / 100;
  
  return (
    <svg width={width} height={height} className="mx-auto">
      {/* 坏样本累计 */}
      <polyline points={badPoints} fill="none" stroke="#ef4444" strokeWidth="2"/>
      
      {/* 好样本累计 */}
      <polyline points={goodPoints} fill="none" stroke="#22c55e" strokeWidth="2"/>
      
      {/* KS曲线 */}
      <polyline points={ksPoints} fill="none" stroke="#3b82f6" strokeWidth="2" strokeDasharray="4,2"/>
      
      {/* KS最大值标记 */}
      <line x1={ksMaxX} y1={padding} x2={ksMaxX} y2={height - padding} stroke="#9333ea" strokeWidth="1" strokeDasharray="3,3"/>
      <circle cx={ksMaxX} cy={height - padding - data.ks_max * 100 * (height - 2 * padding) / 100} r="4" fill="#9333ea"/>
      
      {/* 坐标轴 */}
      <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="#374151" strokeWidth="1"/>
      <line x1={padding} y1={padding} x2={padding} y2={height - padding} stroke="#374151" strokeWidth="1"/>
      
      {/* 图例 */}
      <line x1={width - 80} y1={15} x2={width - 65} y2={15} stroke="#ef4444" strokeWidth="2"/>
      <text x={width - 60} y={18} fontSize="8" fill="#6b7280">坏</text>
      <line x1={width - 50} y1={15} x2={width - 35} y2={15} stroke="#22c55e" strokeWidth="2"/>
      <text x={width - 30} y={18} fontSize="8" fill="#6b7280">好</text>
    </svg>
  );
}

// Lift曲线图 - 展示各分箱的Lift值
function LiftChart({ bins }: { bins: ScoreBinData[] }) {
  const width = 320;  // 加宽以容纳分数区间标签
  const height = 200; // 加高以容纳倾斜的X轴标签
  const padding = { top: 25, right: 30, bottom: 55, left: 35 };  // 增加底部边距
  
  if (!bins || bins.length === 0) {
    return <div className="text-center text-muted-foreground">暂无Lift数据</div>;
  }
  
  // 计算Y轴范围（Lift值范围）
  const lifts = bins.map(b => b.lift);
  const maxLift = Math.max(...lifts, 1.5); // 至少显示到1.5
  const minLift = Math.min(...lifts, 0.5); // 至少显示到0.5
  const yRange = maxLift - minLift;
  const yPadding = yRange * 0.1;
  const yMin = Math.max(0, minLift - yPadding);
  const yMax = maxLift + yPadding;
  
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;
  const xScale = chartWidth / (bins.length - 1 || 1);
  const yScale = chartHeight / (yMax - yMin);
  
  // 生成折线点
  const points = bins.map((bin, i) => {
    const x = padding.left + i * xScale;
    const y = padding.top + chartHeight - (bin.lift - yMin) * yScale;
    return `${x},${y}`;
  }).join(" ");
  
  // Lift=1 的基准线Y坐标
  const baselineY = padding.top + chartHeight - (1 - yMin) * yScale;
  
  return (
    <svg width={width} height={height} className="mx-auto">
      {/* 背景网格 */}
      <defs>
        <pattern id="liftGrid" width="40" height="30" patternUnits="userSpaceOnUse">
          <path d="M 40 0 L 0 0 0 30" fill="none" stroke="#e5e7eb" strokeWidth="0.5"/>
        </pattern>
        <linearGradient id="liftGradient" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#ef4444" stopOpacity="0.3"/>
          <stop offset="50%" stopColor="#fbbf24" stopOpacity="0.1"/>
          <stop offset="100%" stopColor="#22c55e" stopOpacity="0.2"/>
        </linearGradient>
      </defs>
      <rect x={padding.left} y={padding.top} width={chartWidth} height={chartHeight} fill="url(#liftGrid)"/>
      
      {/* Lift=1 基准线 */}
      {baselineY >= padding.top && baselineY <= padding.top + chartHeight && (
        <>
          <line 
            x1={padding.left} 
            y1={baselineY} 
            x2={padding.left + chartWidth} 
            y2={baselineY} 
            stroke="#22c55e" 
            strokeWidth="1.5" 
            strokeDasharray="4,4"
          />
          <text x={padding.left + chartWidth + 3} y={baselineY + 3} fontSize="8" fill="#22c55e">Lift=1</text>
        </>
      )}
      
      {/* 填充区域 */}
      <polygon 
        points={`${padding.left},${padding.top + chartHeight} ${points} ${padding.left + chartWidth},${padding.top + chartHeight}`}
        fill="url(#liftGradient)"
      />
      
      {/* Lift曲线 */}
      <polyline points={points} fill="none" stroke="#f97316" strokeWidth="2"/>
      
      {/* 数据点 */}
      {bins.map((bin, i) => {
        const x = padding.left + i * xScale;
        const y = padding.top + chartHeight - (bin.lift - yMin) * yScale;
        const color = bin.lift > 1.5 ? "#ef4444" : bin.lift > 1 ? "#f97316" : "#22c55e";
        return (
          <g key={i}>
            <circle cx={x} cy={y} r="3" fill={color} stroke="white" strokeWidth="1"/>
            {/* 首尾标注Lift值 */}
            {(i === 0 || i === bins.length - 1) && (
              <text 
                x={x} 
                y={y - 8} 
                fontSize="9" 
                fill={color} 
                textAnchor="middle"
                fontWeight="500"
              >
                {bin.lift.toFixed(2)}
              </text>
            )}
          </g>
        );
      })}
      
      {/* 坐标轴 */}
      <line x1={padding.left} y1={padding.top + chartHeight} x2={padding.left + chartWidth} y2={padding.top + chartHeight} stroke="#374151" strokeWidth="1"/>
      <line x1={padding.left} y1={padding.top} x2={padding.left} y2={padding.top + chartHeight} stroke="#374151" strokeWidth="1"/>
      
      {/* Y轴标签 */}
      <text x={padding.left - 5} y={padding.top + 5} fontSize="8" fill="#6b7280" textAnchor="end">{yMax.toFixed(1)}</text>
      <text x={padding.left - 5} y={padding.top + chartHeight} fontSize="8" fill="#6b7280" textAnchor="end">{yMin.toFixed(1)}</text>
      
      {/* X轴标签 - 显示分数区间（倾斜45度） */}
      {bins.map((bin, i) => {
        const x = padding.left + i * xScale;
        const y = padding.top + chartHeight + 8;
        // 仅显示首、尾、中间标签，避免过于密集
        const showLabel = i === 0 || i === bins.length - 1 || (bins.length > 5 && i === Math.floor(bins.length / 2));
        return showLabel ? (
          <text 
            key={i}
            x={x} 
            y={y} 
            fontSize="7" 
            fill="#6b7280" 
            textAnchor="start"
            transform={`rotate(45, ${x}, ${y})`}
          >
            {bin.bin}
          </text>
        ) : null;
      })}
      
      {/* X轴说明 */}
      <text x={padding.left} y={height - 3} fontSize="7" fill="#9ca3af">高风险</text>
      <text x={padding.left + chartWidth} y={height - 3} fontSize="7" fill="#9ca3af" textAnchor="end">低风险</text>
      
      {/* 图表标题 */}
      <text x={width / 2} y={12} fontSize="9" fill="#6b7280" textAnchor="middle">Lift曲线（按评分区间）</text>
    </svg>
  );
}

// PSI分布对比图 - 展示两个数据集的评分分布对比
interface PSIComparisonChartProps {
  expectedData: ScoreBinData[];       // 基准数据（训练集）
  expectedLabel: string;              // "训练集"
  actualData: ScoreBinData[];         // 对比数据（OOT或测试集）
  actualLabel: string;                // "OOT验证集" 或 "测试集"
  psiValue: number;                   // PSI值
  stability: string;                  // "稳定" | "轻微变化" | "显著变化"
}

function PSIComparisonChart({ 
  expectedData, 
  expectedLabel,
  actualData, 
  actualLabel,
  psiValue,
  stability
}: PSIComparisonChartProps) {
  const width = 420;  // 缩小整体宽度（从560调整为420）
  const height = 200;  // 适当降低高度
  const padding = { top: 30, right: 15, bottom: 50, left: 45 };
  
  // 对齐两个数据集的分箱（使用bin标签作为键）
  const alignedData = useMemo(() => {
    const expectedMap = new Map(expectedData.map(d => [d.bin, d.pct_total]));
    const actualMap = new Map(actualData.map(d => [d.bin, d.pct_total]));
    
    // 获取所有唯一的bin标签
    const allBins = [...new Set([...expectedData.map(d => d.bin), ...actualData.map(d => d.bin)])];
    
    // 按bin名称排序（尝试数值排序）
    allBins.sort((a, b) => {
      const aNum = parseFloat(a.replace(/[^\d.-]/g, ''));
      const bNum = parseFloat(b.replace(/[^\d.-]/g, ''));
      if (!isNaN(aNum) && !isNaN(bNum)) return aNum - bNum;
      return a.localeCompare(b);
    });
    
    return allBins.map(bin => ({
      bin,
      expected: expectedMap.get(bin) || 0,
      actual: actualMap.get(bin) || 0
    }));
  }, [expectedData, actualData]);
  
  if (alignedData.length === 0) {
    return <div className="text-center text-muted-foreground">暂无PSI分布数据</div>;
  }
  
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;
  
  // 计算最大值（用于Y轴缩放）
  const maxPct = Math.max(
    ...alignedData.map(d => Math.max(d.expected, d.actual))
  );
  const yMax = Math.ceil(maxPct * 100 / 5) * 5 / 100; // 向上取整到5%的倍数
  
  // 条形图参数（调整柱宽比例，使柱状更紧凑）
  const barGroupWidth = chartWidth / alignedData.length;
  const barWidth = barGroupWidth * 0.28;  // 缩小每个柱的宽度（从0.35调整为0.28）
  const barGap = barGroupWidth * 0.04;    // 缩小两个柱之间的间距
  
  // Y轴刻度
  const yTicks = 5;
  const yTickValues = Array.from({ length: yTicks + 1 }, (_, i) => (yMax / yTicks) * i);
  
  // 颜色配置
  const expectedColor = "#3b82f6";  // 蓝色
  const actualColor = "#f97316";    // 橙色
  
  // PSI状态颜色
  const psiColor = psiValue < 0.1 ? "#16a34a" : psiValue < 0.25 ? "#ca8a04" : "#dc2626";
  
  return (
    <div>
      {/* 图例和PSI标签 */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded" style={{ backgroundColor: expectedColor }} />
            <span>{expectedLabel}</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded" style={{ backgroundColor: actualColor }} />
            <span>{actualLabel}</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">PSI =</span>
          <span className="font-mono font-medium" style={{ color: psiColor }}>{psiValue.toFixed(4)}</span>
          <Badge 
            variant={psiValue < 0.1 ? "default" : psiValue < 0.25 ? "secondary" : "destructive"}
            className="text-[10px]"
          >
            {stability}
          </Badge>
        </div>
      </div>
      
      <svg width={width} height={height} className="bg-gray-50 dark:bg-gray-900/20 rounded">
        {/* Y轴网格线 */}
        {yTickValues.map((tick, i) => {
          const y = padding.top + chartHeight - (tick / yMax) * chartHeight;
          return (
            <g key={i}>
              <line
                x1={padding.left}
                y1={y}
                x2={width - padding.right}
                y2={y}
                stroke="#e5e7eb"
                strokeDasharray={i === 0 ? "none" : "2,2"}
              />
              <text x={padding.left - 8} y={y + 3} fontSize="9" fill="#6b7280" textAnchor="end">
                {(tick * 100).toFixed(0)}%
              </text>
            </g>
          );
        })}
        
        {/* 柱状图 */}
        {alignedData.map((d, i) => {
          const groupX = padding.left + i * barGroupWidth + barGroupWidth / 2;
          const expectedHeight = (d.expected / yMax) * chartHeight;
          const actualHeight = (d.actual / yMax) * chartHeight;
          
          return (
            <g key={i}>
              {/* 基准数据条（左） */}
              <rect
                x={groupX - barWidth - barGap / 2}
                y={padding.top + chartHeight - expectedHeight}
                width={barWidth}
                height={expectedHeight}
                fill={expectedColor}
                opacity={0.8}
              />
              {/* 对比数据条（右） */}
              <rect
                x={groupX + barGap / 2}
                y={padding.top + chartHeight - actualHeight}
                width={barWidth}
                height={actualHeight}
                fill={actualColor}
                opacity={0.8}
              />
              {/* X轴标签 */}
              <text
                x={groupX}
                y={height - padding.bottom + 15}
                fontSize="8"
                fill="#6b7280"
                textAnchor="middle"
                transform={`rotate(-30, ${groupX}, ${height - padding.bottom + 15})`}
              >
                {d.bin.length > 12 ? d.bin.slice(0, 12) + '...' : d.bin}
              </text>
            </g>
          );
        })}
        
        {/* Y轴标题 */}
        <text
          x={12}
          y={padding.top + chartHeight / 2}
          fontSize="9"
          fill="#6b7280"
          textAnchor="middle"
          transform={`rotate(-90, 12, ${padding.top + chartHeight / 2})`}
        >
          样本占比
        </text>
        
        {/* X轴标题 */}
        <text
          x={width / 2}
          y={height - 5}
          fontSize="9"
          fill="#6b7280"
          textAnchor="middle"
        >
          评分区间
        </text>
      </svg>
    </div>
  );
}

// 评分分布图 - 基于分箱统计数据
function ScoreDistributionChart({ data }: { data: ScoreDistributionData }) {
  const width = 560;
  const height = 200;
  const padding = 40;
  
  if (!data.bins || data.bins.length === 0) {
    return <div className="text-center text-muted-foreground">暂无分布数据</div>;
  }
  
  const bins = data.bins;
  const maxTotal = Math.max(...bins.map(b => b.total));
  const barWidth = (width - 2 * padding) / bins.length - 4;
  const xScale = (width - 2 * padding) / bins.length;
  const yScale = maxTotal > 0 ? (height - 2 * padding - 20) / maxTotal : 1;
  
  return (
    <svg width={width} height={height} className="mx-auto">
      {/* 柱状图 */}
      {bins.map((bin, i) => (
        <g key={i}>
          {/* 总样本柱 */}
          <rect
            x={padding + i * xScale + 2}
            y={height - padding - bin.total * yScale}
            width={barWidth}
            height={bin.total * yScale}
            fill="rgba(59, 130, 246, 0.6)"
          />
          {/* 坏样本柱（叠加在底部） */}
          <rect
            x={padding + i * xScale + 2}
            y={height - padding - bin.bad * yScale}
            width={barWidth}
            height={bin.bad * yScale}
            fill="rgba(239, 68, 68, 0.8)"
          />
          {/* X轴标签 */}
          <text 
            x={padding + i * xScale + barWidth / 2 + 2} 
            y={height - 8} 
            fontSize="8" 
            fill="#6b7280" 
            textAnchor="middle"
            transform={`rotate(-30, ${padding + i * xScale + barWidth / 2 + 2}, ${height - 8})`}
          >
            {bin.bin.replace('[-inf,', '<').replace(',inf)', '+').replace('[', '').replace(')', '')}
          </text>
        </g>
      ))}
      
      {/* 坐标轴 */}
      <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="#374151" strokeWidth="1"/>
      <line x1={padding} y1={padding} x2={padding} y2={height - padding} stroke="#374151" strokeWidth="1"/>
      
      {/* Y轴刻度 */}
      <text x={padding - 5} y={padding + 5} fontSize="9" fill="#6b7280" textAnchor="end">{maxTotal}</text>
      <text x={padding - 5} y={height - padding} fontSize="9" fill="#6b7280" textAnchor="end">0</text>
      
      {/* 图例 */}
      <rect x={width - 100} y={10} width={12} height={12} fill="rgba(59, 130, 246, 0.6)"/>
      <text x={width - 85} y={20} fontSize="9" fill="#6b7280">总样本</text>
      <rect x={width - 100} y={25} width={12} height={12} fill="rgba(239, 68, 68, 0.8)"/>
      <text x={width - 85} y={35} fontSize="9" fill="#6b7280">坏样本</text>
    </svg>
  );
}

// 评分分布统计表格
function ScoreDistributionTable({ data }: { data: ScoreDistributionData }) {
  if (!data.bins || data.bins.length === 0) {
    return <div className="text-center text-muted-foreground py-4">暂无分布数据</div>;
  }
  
  return (
    <div className="max-h-[200px] overflow-auto rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="sticky top-0 bg-background text-xs">分数区间</TableHead>
            <TableHead className="sticky top-0 bg-background text-xs text-right">样本数</TableHead>
            <TableHead className="sticky top-0 bg-background text-xs text-right">占比</TableHead>
            <TableHead className="sticky top-0 bg-background text-xs text-right">坏样本</TableHead>
            <TableHead className="sticky top-0 bg-background text-xs text-right">坏样本率</TableHead>
            <TableHead className="sticky top-0 bg-background text-xs text-right">Lift</TableHead>
            <TableHead className="sticky top-0 bg-background text-xs text-right">累计坏率</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.bins.map((bin, idx) => (
            <TableRow key={idx}>
              <TableCell className="text-xs font-mono">{bin.bin}</TableCell>
              <TableCell className="text-xs text-right">{bin.total.toLocaleString()}</TableCell>
              <TableCell className="text-xs text-right">{bin.pct_total.toFixed(2)}%</TableCell>
              <TableCell className="text-xs text-right">{bin.bad.toLocaleString()}</TableCell>
              <TableCell className="text-xs text-right">
                <span className={bin.bad_rate > (data.summary?.overall_bad_rate || 0) ? "text-red-500 font-medium" : ""}>
                  {bin.bad_rate.toFixed(2)}%
                </span>
              </TableCell>
              <TableCell className="text-xs text-right">
                <span className={bin.lift > 1 ? "text-red-500 font-medium" : "text-green-500"}>
                  {bin.lift.toFixed(2)}
                </span>
              </TableCell>
              <TableCell className="text-xs text-right">{bin.cum_bad_rate.toFixed(2)}%</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

// 带红色渐变条的坏样本率单元格
function BadRateCell({ badRate, maxBadRate, overallBadRate }: { badRate: number; maxBadRate: number; overallBadRate: number }) {
  // 计算渐变条宽度百分比（相对于最大坏账率）
  const widthPct = maxBadRate > 0 ? (badRate / maxBadRate) * 100 : 0;
  // 颜色深度根据与整体坏账率的关系调整
  const intensity = Math.min(1, badRate / (overallBadRate * 2));
  
  return (
    <div className="relative flex items-center justify-end min-w-[80px]">
      {/* 红色渐变条背景 */}
      <div 
        className="absolute inset-y-0 left-0 rounded-sm transition-all"
        style={{ 
          width: `${widthPct}%`,
          backgroundColor: `rgba(239, 68, 68, ${0.15 + intensity * 0.35})` // 红色透明度从0.15到0.5
        }}
      />
      {/* 数值 */}
      <span className={cn(
        "relative z-10 text-xs font-mono",
        badRate > overallBadRate ? "text-red-600 font-medium" : "text-gray-700 dark:text-gray-300"
      )}>
        {badRate.toFixed(2)}%
      </span>
    </div>
  );
}

// 多数据集评分分布组件（支持数据集切换、分析视图切换和红色渐变条）
function MultiDatasetScoreDistribution({ 
  multiDatasetChartData,
  defaultDataset = 'test'
}: { 
  multiDatasetChartData: MultiDatasetChartData;
  defaultDataset?: 'train' | 'test' | 'oot';
}) {
  // 确定可用的数据集
  const availableDatasets = useMemo(() => {
    const datasets: { key: 'train' | 'test' | 'oot'; label: string }[] = [];
    if (multiDatasetChartData.train?.score_distribution) {
      datasets.push({ key: 'train', label: '训练集' });
    }
    if (multiDatasetChartData.test?.score_distribution) {
      datasets.push({ key: 'test', label: '测试集' });
    }
    if (multiDatasetChartData.oot?.score_distribution) {
      datasets.push({ key: 'oot', label: 'OOT验证集' });
    }
    return datasets;
  }, [multiDatasetChartData]);
  
  // 当前选中的数据集
  const [selectedDataset, setSelectedDataset] = useState<'train' | 'test' | 'oot'>(() => {
    if (multiDatasetChartData[defaultDataset]?.score_distribution) {
      return defaultDataset;
    }
    return availableDatasets[0]?.key || 'test';
  });
  
  // 分析视图切换：排序性分析(等频) vs 评分分布(等宽)
  const [analysisView, setAnalysisView] = useState<'ranking' | 'distribution'>('ranking');
  
  // 获取当前数据集的完整分布数据
  const scoreDistribution = multiDatasetChartData[selectedDataset]?.score_distribution;
  
  // 根据分析视图选择对应的分箱数据
  const currentBins = useMemo(() => {
    if (!scoreDistribution) return null;
    
    if (analysisView === 'ranking') {
      // 优先使用 ranking_analysis，否则回退到默认 bins
      return scoreDistribution.ranking_analysis?.bins || scoreDistribution.bins;
    } else {
      // 优先使用 distribution_view，否则回退到默认 bins
      return scoreDistribution.distribution_view?.bins || scoreDistribution.bins;
    }
  }, [scoreDistribution, analysisView]);
  
  // 检查是否有双视图数据
  const hasDualView = scoreDistribution?.ranking_analysis && scoreDistribution?.distribution_view;
  
  // 计算最大坏账率（用于渐变条）
  const maxBadRate = useMemo(() => {
    if (!currentBins) return 0;
    return Math.max(...currentBins.map(b => b.bad_rate));
  }, [currentBins]);
  
  if (availableDatasets.length === 0 || !scoreDistribution || !currentBins) {
    return <div className="text-center text-muted-foreground py-4">暂无多数据集分布数据</div>;
  }
  
  const overallBadRate = scoreDistribution.summary?.overall_bad_rate || 0;
  
  return (
    <div className="space-y-3">
      {/* 控制栏：数据集切换 + 分析视图切换 */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        {/* 数据集切换 */}
        {availableDatasets.length > 1 && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">数据集：</span>
            <div className="flex gap-1">
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
          </div>
        )}
        
        {/* 分析视图切换（仅当有双视图数据时显示） */}
        {hasDualView && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">视图：</span>
            <div className="flex gap-1">
              <Button
                variant={analysisView === 'ranking' ? "default" : "outline"}
                size="sm"
                className="h-6 px-2 text-xs"
                onClick={() => setAnalysisView('ranking')}
              >
                <TrendingUp className="h-3 w-3 mr-1" />
                排序性分析
              </Button>
              <Button
                variant={analysisView === 'distribution' ? "default" : "outline"}
                size="sm"
                className="h-6 px-2 text-xs"
                onClick={() => setAnalysisView('distribution')}
              >
                <BarChart3 className="h-3 w-3 mr-1" />
                评分分布
              </Button>
            </div>
          </div>
        )}
      </div>
      
      {/* 视图说明 */}
      {hasDualView && (
        <div className="text-xs text-muted-foreground bg-blue-50 dark:bg-blue-950/30 px-3 py-1.5 rounded flex items-center gap-2">
          <HelpCircle className="h-3.5 w-3.5 text-blue-500" />
          {analysisView === 'ranking' ? (
            <span>
              <strong>排序性分析</strong>：等频分箱
              {scoreDistribution.ranking_analysis?.n_bins && ` (${scoreDistribution.ranking_analysis.n_bins}组)`}
              ，每组样本量相近，便于评估模型风险区分能力
            </span>
          ) : (
            <span>
              <strong>评分分布</strong>：等宽分箱
              {scoreDistribution.distribution_view?.n_bins && ` (目标${scoreDistribution.distribution_view.n_bins}组)`}
              ，直观展示评分在各区间的分布情况
            </span>
          )}
        </div>
      )}
      
      {/* 汇总信息 */}
      {scoreDistribution.summary && (
        <div className="flex items-center gap-4 text-xs text-muted-foreground bg-muted/30 rounded px-3 py-1.5">
          <span>总样本: <span className="font-medium text-foreground">{scoreDistribution.summary.total_samples.toLocaleString()}</span></span>
          <span>坏样本率: <span className="font-medium text-red-500">{scoreDistribution.summary.overall_bad_rate.toFixed(2)}%</span></span>
          <span>好样本均值: <span className="font-medium text-green-600">{scoreDistribution.summary.good_mean.toFixed(1)}</span></span>
          <span>坏样本均值: <span className="font-medium text-red-500">{scoreDistribution.summary.bad_mean.toFixed(1)}</span></span>
        </div>
      )}
      
      {/* 排序性分析摘要（仅在排序性分析视图时显示） */}
      {analysisView === 'ranking' && scoreDistribution.rank_ordering_analysis && (
        <div className="bg-muted/20 border rounded-md px-3 py-2">
          <div className="flex items-center gap-4 text-xs flex-wrap">
            {/* 单调性检验 */}
            <div className="flex items-center gap-1.5">
              <span className="text-muted-foreground">单调性：</span>
              {scoreDistribution.rank_ordering_analysis.monotonicity.is_monotonic ? (
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
                        不通过（{scoreDistribution.rank_ordering_analysis.monotonicity.violations.length}处违反）
                      </span>
                    </TooltipTrigger>
                    <TooltipContent className="max-w-xs">
                      <p className="text-xs mb-1">以下分段坏样本率未递减：</p>
                      <ul className="text-xs space-y-0.5">
                        {scoreDistribution.rank_ordering_analysis.monotonicity.violation_details.map((v, i) => (
                          <li key={i} className="text-amber-200">
                            {v.curr_bin}: {v.prev_bad_rate.toFixed(2)}% → {v.curr_bad_rate.toFixed(2)}% (+{v.diff}%)
                          </li>
                        ))}
                      </ul>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              )}
            </div>
            
            {/* 首组Lift */}
            {scoreDistribution.rank_ordering_analysis.lift_analysis.first_decile_lift != null && (
              <div className="flex items-center gap-1.5">
                <span className="text-muted-foreground">首组Lift：</span>
                <span className={cn(
                  "font-medium",
                  scoreDistribution.rank_ordering_analysis.lift_analysis.first_decile_lift >= 2 
                    ? "text-green-600" 
                    : scoreDistribution.rank_ordering_analysis.lift_analysis.first_decile_lift >= 1.5 
                      ? "text-blue-600" 
                      : "text-amber-600"
                )}>
                  {scoreDistribution.rank_ordering_analysis.lift_analysis.first_decile_lift.toFixed(2)}
                </span>
                <span className="text-muted-foreground">
                  （{scoreDistribution.rank_ordering_analysis.lift_analysis.first_decile_bin}）
                </span>
              </div>
            )}
            
            {/* 末组Lift */}
            {scoreDistribution.rank_ordering_analysis.lift_analysis.last_decile_lift != null && (
              <div className="flex items-center gap-1.5">
                <span className="text-muted-foreground">末组Lift：</span>
                <span className={cn(
                  "font-medium",
                  scoreDistribution.rank_ordering_analysis.lift_analysis.last_decile_lift <= 0.5 
                    ? "text-green-600" 
                    : scoreDistribution.rank_ordering_analysis.lift_analysis.last_decile_lift <= 0.8 
                      ? "text-blue-600" 
                      : "text-amber-600"
                )}>
                  {scoreDistribution.rank_ordering_analysis.lift_analysis.last_decile_lift.toFixed(2)}
                </span>
                <span className="text-muted-foreground">
                  （{scoreDistribution.rank_ordering_analysis.lift_analysis.last_decile_bin}）
                </span>
              </div>
            )}
          </div>
        </div>
      )}
      
      {/* 排序性/分布表格（带红色渐变条） */}
      <div className="max-h-[280px] overflow-auto rounded-md border">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/50">
              <TableHead className="sticky top-0 bg-muted/50 text-xs font-semibold w-[60px]">序号</TableHead>
              <TableHead className="sticky top-0 bg-muted/50 text-xs font-semibold">分数区间</TableHead>
              <TableHead className="sticky top-0 bg-muted/50 text-xs font-semibold text-right">样本数</TableHead>
              <TableHead className="sticky top-0 bg-muted/50 text-xs font-semibold text-right">好样本</TableHead>
              <TableHead className="sticky top-0 bg-muted/50 text-xs font-semibold text-right">坏样本</TableHead>
              <TableHead className="sticky top-0 bg-muted/50 text-xs font-semibold text-right min-w-[100px]">坏样本率</TableHead>
              <TableHead className="sticky top-0 bg-muted/50 text-xs font-semibold text-right">Lift</TableHead>
              <TableHead className="sticky top-0 bg-muted/50 text-xs font-semibold text-right">累计坏率</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {currentBins.map((bin, idx) => (
              <TableRow key={idx} className="hover:bg-muted/30">
                <TableCell className="text-xs text-muted-foreground">{idx + 1}</TableCell>
                <TableCell className="text-xs font-mono">{bin.bin}</TableCell>
                <TableCell className="text-xs text-right">{bin.total.toLocaleString()}</TableCell>
                <TableCell className="text-xs text-right text-green-600">{bin.good.toLocaleString()}</TableCell>
                <TableCell className="text-xs text-right text-red-500">{bin.bad.toLocaleString()}</TableCell>
                <TableCell className="text-xs text-right p-1">
                  <BadRateCell 
                    badRate={bin.bad_rate} 
                    maxBadRate={maxBadRate} 
                    overallBadRate={overallBadRate}
                  />
                </TableCell>
                <TableCell className="text-xs text-right">
                  <span className={cn(
                    "font-medium",
                    bin.lift > 1.5 ? "text-red-600" : bin.lift > 1 ? "text-orange-500" : "text-green-500"
                  )}>
                    {bin.lift.toFixed(2)}
                  </span>
                </TableCell>
                <TableCell className="text-xs text-right font-mono">{bin.cum_bad_rate.toFixed(2)}%</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      
      {/* 分布图 - 仅在评分分布视图或无双视图时显示 */}
      {(analysisView === 'distribution' || !hasDualView) && (
        <div className="h-[200px] flex items-center justify-center bg-gray-50 dark:bg-gray-900/20 rounded mt-3">
          <ScoreDistributionChart data={{ ...scoreDistribution, bins: currentBins }} />
        </div>
      )}
      
      {/* 图例说明 */}
      <div className="flex items-center gap-4 text-xs text-muted-foreground flex-wrap">
        <div className="flex items-center gap-1">
          <div className="w-4 h-3 rounded-sm" style={{ background: 'linear-gradient(to right, rgba(239,68,68,0.15), rgba(239,68,68,0.5))' }} />
          <span>坏样本率渐变条（颜色越深，风险越高）</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="text-red-600 font-medium">红色数值</span>
          <span>= 高于整体坏账率</span>
        </div>
        {hasDualView && (
          <div className="flex items-center gap-1 text-blue-600">
            <ArrowLeftRight className="h-3 w-3" />
            <span>切换视图查看不同分箱方式</span>
          </div>
        )}
      </div>
    </div>
  );
}

interface ScorecardResultsProps {
  executionId: string;
  recordId?: string;         // 任务记录ID（用于AI分析持久化）
  mode?: 'auto' | 'expert';  // 交互模式
  className?: string;
}

interface MetricData {
  ks: number;
  auc: number;
  gini: number;
  source?: 'oot' | 'test';  // 指标来源：OOT验证集或测试集
}

// 多数据集指标接口
interface DatasetMetrics {
  ks: number;
  auc: number;
  gini: number;
  samples?: number;
  bad_rate?: number;
}

interface MultiDatasetMetrics {
  train?: DatasetMetrics;
  test?: DatasetMetrics;
  oot?: DatasetMetrics;
}

interface ScorecardItem {
  variable: string;
  bin: string;
  woe: number;
  points: number;
}

interface IVItem {
  variable: string;
  iv: number;
}

interface CoefficientItem {
  feature: string;
  coefficient: number;
  intercept?: number;
}

// 逐步回归步骤接口
interface StepwiseStep {
  iteration: number;
  action: 'add' | 'remove';
  feature: string;
  pvalue: number;
}

// 逐步回归结果接口
interface StepwiseResult {
  selected_features?: string[];
  steps?: StepwiseStep[];
  final_pvalues?: Record<string, number>;
  direction?: string;
  significance_level?: number;
}

// 系数方向验证接口
interface CoefficientValidation {
  coefficients?: Record<string, number>;
  valid_direction?: string[];
  invalid_direction?: string[];
  warnings?: string[];
  intercept?: number;
}

// 特征选择详情接口
interface SelectionDetail {
  initial_features?: string[];
  final_features?: string[];
  removed_by_iv?: string[];
  removed_by_corr?: string[];
  removed_by_vif?: string[];
  removed_by_stepwise?: string[];
  stepwise_result?: StepwiseResult;
  coefficient_validation?: CoefficientValidation;
}

// 分箱统计数据接口
interface ScoreBinData {
  bin: string;
  total: number;
  pct_total: number;
  bad: number;
  good: number;
  bad_rate: number;
  lift: number;
  cum_bad_rate: number;
}

// 排序性分析结果接口（新增）
interface MonotonicityResult {
  is_monotonic: boolean;
  status: 'pass' | 'fail';
  violations: number[];
  violation_details: Array<{
    index: number;
    prev_bin: string;
    curr_bin: string;
    prev_bad_rate: number;
    curr_bad_rate: number;
    diff: number;
  }>;
}

interface LiftAnalysisResult {
  first_decile_lift: number | null;
  last_decile_lift: number | null;
  first_decile_bad_rate: number | null;
  last_decile_bad_rate: number | null;
  first_decile_bin?: string;
  last_decile_bin?: string;
}

interface RankOrderingAnalysis {
  monotonicity: MonotonicityResult;
  lift_analysis: LiftAnalysisResult;
}

interface ScoreDistributionData {
  bins: ScoreBinData[];
  bin_method?: string;
  summary?: {
    total_samples: number;
    total_bad: number;
    total_good: number;
    overall_bad_rate: number;
    good_mean: number;
    bad_mean: number;
    score_min: number;
    score_max: number;
  };
  // 双视图数据
  ranking_analysis?: {
    bins: ScoreBinData[];
    bin_method: string;
    n_bins?: number;
    description?: string;
  };
  distribution_view?: {
    bins: ScoreBinData[];
    bin_method: string;
    n_bins?: number;
    description?: string;
  };
  // 排序性分析结果（新增）
  rank_ordering_analysis?: RankOrderingAnalysis;
}

// 图表数据接口
interface ChartData {
  roc?: {
    fpr: number[];
    tpr: number[];
    auc: number;
  };
  ks?: {
    population_pct: number[];
    cum_bad: number[];
    cum_good: number[];
    ks_curve: number[];
    ks_max: number;
    ks_max_position: number;
  };
  score_distribution?: ScoreDistributionData;
}

// 多数据集图表数据接口
interface MultiDatasetChartData {
  train?: ChartData;
  test?: ChartData;
  oot?: ChartData;
}

export function ScorecardResults({
  executionId,
  recordId,
  mode = 'auto',
  className,
}: ScorecardResultsProps) {
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ExecutionResult | null>(null);
  const [activeTab, setActiveTab] = useState("charts");
  // 样本与特征Tab所需的stages数据（按文档方案自己加载）
  const [stagesData, setStagesData] = useState<Record<string, StageProgress> | null>(null);
  // 评估图表Tab的数据集切换状态
  const [selectedChartDataset, setSelectedChartDataset] = useState<'train' | 'test' | 'oot'>('test');


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
        
        console.log('[ScorecardResults] Loading data for executionId:', executionId);
        
        // 检查是否是历史记录ID（rec:前缀）
        if (executionId.startsWith("rec:")) {
          // ===== 场景1：历史记录加载（文档标准方案）=====
          const recId = executionId.substring(4); // 移除"rec:"前缀
          console.log('[ScorecardResults] Loading from history record:', recId);
          
          if (!recId) {
            throw new Error('Invalid recordId: empty string after removing rec: prefix');
          }
          
          // ✅ 使用缓存（父组件已预加载数据），避免重复API调用
          const historyResult = await sopService.getTaskHistoryResult(recId, false);
          console.log('[ScorecardResults] historyResult keys:', Object.keys(historyResult));
          console.log('[ScorecardResults] historyResult.record_id:', historyResult.record_id);
          console.log('[ScorecardResults] historyResult.stages exists:', !!historyResult.stages);
          
          // 🔧 检查是否已取消
          if (isCancelled) {
            console.log('[ScorecardResults] Request cancelled (executionId changed)');
            return;
          }
          
          // 将历史结果转换为ExecutionResult格式
          data = {
            execution_id: recId,
            status: "completed",
            outputs: historyResult.result || {},
          } as ExecutionResult;
          
          // ✅ result 和 stages 来自同一个API响应（文档方案）
          if (historyResult.stages && Object.keys(historyResult.stages).length > 0) {
            stages = historyResult.stages as Record<string, StageProgress>;
            console.log('[ScorecardResults] Stages from history result:', Object.keys(stages));
          } else {
            console.warn('[ScorecardResults] No stages data in history result');
          }
        } else {
          // ===== 场景2：执行结果加载（文档标准方案）=====
          data = await sopService.getExecutionResult(executionId);
          
          // 🔧 检查是否已取消
          if (isCancelled) {
            console.log('[ScorecardResults] Request cancelled (executionId changed)');
            return;
          }
          
          console.log('[ScorecardResults] Execution result record_id:', data.record_id);
          
          // ⚠️ 必须通过record_id获取stages（文档方案）
          if (data.record_id) {
            try {
              const historyResult = await sopService.getTaskHistoryResult(data.record_id);
              if (isCancelled) return; // 🔧 再次检查
              if (historyResult.stages && Object.keys(historyResult.stages).length > 0) {
                stages = historyResult.stages as Record<string, StageProgress>;
                console.log('[ScorecardResults] Stages from history result:', Object.keys(stages));
              }
            } catch (e) {
              console.warn('[ScorecardResults] Failed to get history stages:', e);
            }
          } else {
            console.warn('[ScorecardResults] No record_id, cannot fetch stages');
          }
        }
        
        // 🔧 最终状态更新前再次检查
        if (isCancelled) {
          console.log('[ScorecardResults] Request cancelled before state update');
          return;
        }
        
        console.log('[ScorecardResults] Final stagesData:', stages ? Object.keys(stages) : 'null');
        
        setResult(data);
        setStagesData(stages);
      } catch (err) {
        // 🔧 错误处理前检查取消状态
        if (isCancelled) return;
        console.error("Failed to load result:", err);
        const errorMsg = err instanceof Error ? err.message : String(err);
        setError(`加载结果失败: ${errorMsg}`);
      } finally {
        // 🔧 finally中也检查
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
    
    // 模型评估指标
    let metrics: MetricData | null = null;
    if (outputs.metrics?.data) {
      metrics = outputs.metrics.data as MetricData;
    }

    // 评分卡 - 解析scorepy格式
    let scorecardData: ScorecardItem[] = [];
    if (outputs.scorecard?.data) {
      const scorecard = outputs.scorecard.data;
      // scorepy返回的是 {变量名: DataFrame} 格式
      if (typeof scorecard === 'object') {
        Object.entries(scorecard).forEach(([variable, varData]: [string, any]) => {
          // 处理 {columns: [...], data: [...]} 格式 (dict_of_dataframes)
          if (varData && typeof varData === 'object' && 'data' in varData && Array.isArray(varData.data)) {
            varData.data.forEach((row: any) => {
              scorecardData.push({
                variable,
                bin: row.bin || row.Bin || String(row.bin_label || ''),
                woe: parseFloat(row.woe || row.WOE || 0),
                points: parseFloat(row.points || row.Points || 0),
              });
            });
          }
          // varData可能是DataFrame转换后的records数组
          else if (Array.isArray(varData)) {
            varData.forEach((row: any) => {
              scorecardData.push({
                variable,
                bin: row.bin || row.Bin || String(row.bin_label || ''),
                woe: parseFloat(row.woe || row.WOE || 0),
                points: parseFloat(row.points || row.Points || 0),
              });
            });
          } else if (typeof varData === 'object') {
            // 可能是dict of dicts格式
            Object.entries(varData).forEach(([bin, info]: [string, any]) => {
              if (info && typeof info === 'object' && !('columns' in info)) {
                scorecardData.push({
                  variable,
                  bin,
                  woe: parseFloat(info.woe || info.WOE || 0),
                  points: parseFloat(info.points || info.Points || 0),
                });
              }
            });
          }
        });
      }
    }

    // IV表 - 解析DataFrame格式
    let ivData: IVItem[] = [];
    if (outputs.iv_table) {
      const ivOutput = outputs.iv_table;
      // 可能是DataFrame格式
      if (ivOutput.type === 'dataframe' && Array.isArray(ivOutput.data)) {
        ivData = ivOutput.data.map((item: any) => ({
          variable: item.variable || item.Variable || item.feature || '',
          iv: parseFloat(item.iv || item.IV || item.total_iv || 0),
        }));
      } else if (ivOutput.data) {
        const ivTable = ivOutput.data;
        if (Array.isArray(ivTable)) {
          ivData = ivTable.map((item: any) => ({
            variable: item.variable || item.Variable || item.feature || '',
            iv: parseFloat(item.iv || item.IV || item.total_iv || 0),
          }));
        }
      }
    }

    // 模型系数 - 解析DataFrame格式
    let coefficients: CoefficientItem[] = [];
    let intercept: number | null = null;
    if (outputs.coefficients) {
      const coefOutput = outputs.coefficients;
      if (coefOutput.type === 'dataframe' && Array.isArray(coefOutput.data)) {
        coefOutput.data.forEach((item: any) => {
          coefficients.push({
            feature: item.feature || '',
            coefficient: parseFloat(item.coefficient || 0),
          });
          if (item.intercept !== undefined) {
            intercept = parseFloat(item.intercept);
          }
        });
      } else if (Array.isArray(coefOutput.data)) {
        coefOutput.data.forEach((item: any) => {
          coefficients.push({
            feature: item.feature || '',
            coefficient: parseFloat(item.coefficient || 0),
          });
          if (item.intercept !== undefined) {
            intercept = parseFloat(item.intercept);
          }
        });
      }
    }

    // 筛选后的特征（IV筛选+相关性筛选+VIF筛选后）
    let selectedFeatures: string[] = [];
    if (outputs.selected_features) {
      const featOutput = outputs.selected_features;
      // 可能是list类型
      if (featOutput.type === 'list' && Array.isArray(featOutput.data)) {
        selectedFeatures = featOutput.data.map((f: any) => 
          typeof f === 'string' ? f.replace(/_woe$/, '') : String(f)
        );
      } else if (Array.isArray(featOutput.data)) {
        selectedFeatures = featOutput.data.map((f: any) => 
          typeof f === 'string' ? f.replace(/_woe$/, '') : String(f)
        );
      } else if (typeof featOutput.data === 'string') {
        // 可能被错误地序列化为字符串
        try {
          const parsed = JSON.parse(featOutput.data.replace(/'/g, '"'));
          if (Array.isArray(parsed)) {
            selectedFeatures = parsed.map((f: any) => 
              typeof f === 'string' ? f.replace(/_woe$/, '') : String(f)
            );
          }
        } catch {
          // 如果解析失败，尝试按逗号分割
          selectedFeatures = featOutput.data.split(',').map((s: string) => s.trim().replace(/_woe$/, ''));
        }
      }
    }

    // 图表数据
    let chartData: ChartData | null = null;
    if (outputs.chart_data) {
      const chartOutput = outputs.chart_data;
      if (chartOutput.type === 'dict' && chartOutput.data) {
        chartData = chartOutput.data as ChartData;
      } else if (chartOutput.data) {
        chartData = chartOutput.data as ChartData;
      }
    }

    // 多数据集指标
    let multiDatasetMetrics: MultiDatasetMetrics | null = null;
    if (outputs.multi_dataset_metrics) {
      const multiOutput = outputs.multi_dataset_metrics;
      if (multiOutput.data) {
        multiDatasetMetrics = multiOutput.data as MultiDatasetMetrics;
      }
    }

    // 多数据集图表数据（包含各数据集的score_distribution）
    let multiDatasetChartData: MultiDatasetChartData | null = null;
    if (outputs.multi_dataset_chart_data) {
      const multiChartOutput = outputs.multi_dataset_chart_data;
      if (multiChartOutput.data) {
        multiDatasetChartData = multiChartOutput.data as MultiDatasetChartData;
      }
    }

    // 过拟合警告
    let overfitWarning: string | null = null;
    if (outputs.overfit_warning?.data) {
      overfitWarning = outputs.overfit_warning.data as string;
    }

    // 特征选择详情（包含逐步回归、系数验证等）
    let selectionDetail: SelectionDetail | null = null;
    if (outputs.selection_detail) {
      const detailOutput = outputs.selection_detail;
      if (detailOutput.data) {
        selectionDetail = detailOutput.data as SelectionDetail;
      }
    }

    // PSI稳定性指标（主PSI：有OOT用OOT，否则用Test）
    let psiResult: { value: number; comparison: string; stability: string; level: string } | null = null;
    if (outputs.psi_result) {
      const psiOutput = outputs.psi_result;
      if (psiOutput.data) {
        psiResult = psiOutput.data as { value: number; comparison: string; stability: string; level: string };
      }
    }
    
    // 2026-02-10: 新增双PSI结果，用于同时展示两个PSI对比图
    let psiTrainVsTest: { value: number; comparison: string; stability: string; level: string } | null = null;
    let psiTrainVsOot: { value: number; comparison: string; stability: string; level: string } | null = null;
    if (outputs.psi_train_vs_test) {
      const psiOutput = outputs.psi_train_vs_test;
      if (psiOutput.data) {
        psiTrainVsTest = psiOutput.data as { value: number; comparison: string; stability: string; level: string };
      }
    }
    if (outputs.psi_train_vs_oot) {
      const psiOutput = outputs.psi_train_vs_oot;
      if (psiOutput.data) {
        psiTrainVsOot = psiOutput.data as { value: number; comparison: string; stability: string; level: string };
      }
    }

    return {
      metrics,
      multiDatasetMetrics,
      multiDatasetChartData,
      overfitWarning,
      scorecardData,
      ivData,
      coefficients,
      intercept,
      selectedFeatures,
      chartData,
      selectionDetail,
      psiResult,
      psiTrainVsTest,
      psiTrainVsOot,
    };
  };

  const parsedResults = parseResults();

  // 生成Markdown报告
  const generateMarkdownReport = (): string => {
    let md = `# 评分卡开发报告\n\n`;
    md += `> 生成时间: ${new Date().toLocaleString()}\n\n`;
    md += `---\n\n`;
    
    // 模型指标
    if (metrics) {
      md += `## 1. 模型核心指标\n\n`;
      md += `| 指标 | 值 |\n`;
      md += `|------|----|\n`;
      md += `| KS值 | ${metrics.ks != null ? (metrics.ks * 100).toFixed(2) + '%' : '-'} |\n`;
      md += `| AUC | ${metrics.auc != null ? metrics.auc.toFixed(4) : '-'} |\n`;
      md += `| Gini系数 | ${metrics.gini != null ? (metrics.gini * 100).toFixed(2) + '%' : '-'} |\n`;
      md += `| 准确率 | ${metrics.accuracy != null ? (metrics.accuracy * 100).toFixed(2) + '%' : '-'} |\n`;
      md += `\n`;
    }
    
    // 评分转换参数（从stagesData获取）
    const scoreScalingPreview = stagesData?.score_scaling?.output_preview;
    if (scoreScalingPreview) {
      md += `## 2. 评分转换参数\n\n`;
      md += `| 参数 | 值 |\n`;
      md += `|------|----|\n`;
      md += `| 基准分 | ${scoreScalingPreview.base_score || '-'} |\n`;
      md += `| PDO | ${scoreScalingPreview.pdo || '-'} |\n`;
      md += `| 基准Odds | ${scoreScalingPreview.base_odds || '-'} |\n`;
      if (scoreScalingPreview.score_range) {
        md += `| 评分区间 | ${Math.round(scoreScalingPreview.score_range.min)} - ${Math.round(scoreScalingPreview.score_range.max)} |\n`;
      }
      md += `\n`;
    }
    
    // 评分卡明细
    if (scorecardData && scorecardData.length > 0) {
      md += `## 3. 评分卡明细\n\n`;
      md += `| 变量 | 分箱 | 评分 |\n`;
      md += `|------|------|------|\n`;
      scorecardData.slice(0, 30).forEach((item: any) => {
        md += `| ${item.variable || '-'} | ${item.bin || '-'} | ${item.points != null ? item.points : '-'} |\n`;
      });
      if (scorecardData.length > 30) {
        md += `\n*（仅展示前30条，共${scorecardData.length}条）*\n`;
      }
      md += `\n`;
    }
    
    // IV值排序
    if (ivData && ivData.length > 0) {
      md += `## 4. 特征IV值排序\n\n`;
      md += `| 排名 | 变量 | IV值 |\n`;
      md += `|------|------|------|\n`;
      ivData.slice(0, 15).forEach((item: any, idx: number) => {
        md += `| ${idx + 1} | ${item.variable || '-'} | ${item.iv != null ? item.iv.toFixed(4) : '-'} |\n`;
      });
      md += `\n`;
    }
    
    // 模型系数
    if (coefficients && coefficients.length > 0) {
      md += `## 5. 模型系数\n\n`;
      md += `| 变量 | 系数 | P值 |\n`;
      md += `|------|------|-----|\n`;
      coefficients.forEach((item: any) => {
        const pValue = item.p_value != null ? item.p_value.toFixed(4) : '-';
        md += `| ${item.variable || '-'} | ${item.coefficient != null ? item.coefficient.toFixed(4) : '-'} | ${pValue} |\n`;
      });
      md += `\n`;
    }
    
    md += `---\n\n`;
    md += `*本报告由 DeepAnalyze 自动生成*\n`;
    
    return md;
  };

  // 下载结果 - 支持JSON、Markdown、Excel、Word和HTML格式
  const handleDownload = async (format: 'json' | 'markdown' | 'excel' | 'word' | 'html' = 'json') => {
    if (!parsedResults) return;
    
    if (format === 'html' || format === 'excel' || format === 'word') {
      // 调用后端API生成报告
      try {
        const response = await fetch(getApiUrl('/sop/report/export'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ execution_id: executionId, format: format })
        });
        const data = await response.json();
        
        if (data.success && data.content) {
          if (format === 'html') {
            // 下载HTML文件并在新标签页预览
            const blob = new Blob([data.content], { type: 'text/html;charset=utf-8' });
            const url = URL.createObjectURL(blob);
            
            // 下载文件 - 使用后端返回的文件名
            const a = document.createElement('a');
            a.href = url;
            a.download = data.filename || `scorecard_report_${executionId}.html`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            
            // 在新标签页预览
            const previewWindow = window.open('', '_blank');
            if (previewWindow) {
              previewWindow.document.write(data.content);
              previewWindow.document.close();
            }
            
            URL.revokeObjectURL(url);
            toast({
              title: "导出成功",
              description: 'HTML报告已下载并在新标签页打开预览',
            });
          } else if (format === 'excel') {
            // Excel格式 - base64解码后下载
            const binaryString = atob(data.content);
            const bytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) {
              bytes[i] = binaryString.charCodeAt(i);
            }
            const blob = new Blob([bytes], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = data.filename || `scorecard_report_${executionId}.xlsx`;
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
            const binaryString = atob(data.content);
            const bytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) {
              bytes[i] = binaryString.charCodeAt(i);
            }
            const blob = new Blob([bytes], { type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = data.filename || `scorecard_report_${executionId}.docx`;
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
            description: data.error || "生成报告失败",
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
    } else if (format === 'markdown') {
      // Markdown格式 - 调用后端API生成（与Excel/Word保持一致的配置驱动）
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
          a.download = responseData.filename || `scorecard_report_${executionId}.md`;
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
    } else {
      // JSON格式下载 - 统一命名格式与后端一致
      const text = JSON.stringify(parsedResults, null, 2);
      const blob = new Blob([text], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      
      // 统一命名格式：scorecard_{timestamp}_{rec-id}.json
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
      
      a.download = `scorecard_${timestamp}_${idToUse}.json`;
      
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      toast({
        title: "下载成功",
        description: "评分卡结果已下载",
      });
    }
  };

  // 加载中状态
  if (loading) {
    return (
      <Card className={cn("w-full", className)}>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          <span className="ml-2 text-muted-foreground">加载结果中...</span>
        </CardContent>
      </Card>
    );
  }

  // 错误状态
  if (error) {
    return (
      <Card className={cn("w-full", className)}>
        <CardContent className="flex items-center justify-center py-8">
          <span className="text-destructive">{error}</span>
        </CardContent>
      </Card>
    );
  }

  // 无结果
  if (!parsedResults) {
    return (
      <Card className={cn("w-full", className)}>
        <CardContent className="flex items-center justify-center py-8">
          <span className="text-muted-foreground">暂无结果数据</span>
        </CardContent>
      </Card>
    );
  }

  const { metrics, multiDatasetMetrics, multiDatasetChartData, overfitWarning, scorecardData, ivData, coefficients, intercept, selectedFeatures, chartData, selectionDetail, psiResult, psiTrainVsTest, psiTrainVsOot } = parsedResults;

  // 计算入模变量数（从评分卡或系数中获取，排除basepoints）
  const modelVariables = coefficients.length > 0 
    ? coefficients.map(c => c.feature.replace(/_woe$/, ''))
    : [...new Set(scorecardData.map(item => item.variable))].filter(v => v !== 'basepoints');
  const modelVariableCount = modelVariables.length;

  return (
    <TooltipProvider>
      <Card className={cn("w-full", className)}>
        {/* 结果标题行 - sticky 冻结在顶部 Tab 行下方 */}
        <CardHeader className="pb-3 sticky top-[41px] z-[5] bg-green-50 dark:bg-green-900/20 border-b border-green-100 dark:border-green-800/50">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-green-500" />
              <CardTitle className="text-base">评分卡开发结果</CardTitle>
              <Badge variant="outline" className="text-xs">
                任务执行完成
              </Badge>
            </div>
            <div className="flex items-center gap-2">
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="sm" onClick={() => handleDownload('markdown')}>
                    <Download className="h-4 w-4 mr-1" />
                    MD
                  </Button>
                </TooltipTrigger>
                <TooltipContent>下载Markdown报告</TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="sm" onClick={() => handleDownload('excel')}>
                    <Download className="h-4 w-4 mr-1" />
                    Excel
                  </Button>
                </TooltipTrigger>
                <TooltipContent>下载Excel报告（多Sheet）</TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="sm" onClick={() => handleDownload('word')}>
                    <Download className="h-4 w-4 mr-1" />
                    Word
                  </Button>
                </TooltipTrigger>
                <TooltipContent>下载Word报告（可编辑文档）</TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="sm" onClick={() => handleDownload('html')}>
                    <Download className="h-4 w-4 mr-1" />
                    HTML
                  </Button>
                </TooltipTrigger>
                <TooltipContent>下载HTML报告（可在浏览器中打开）</TooltipContent>
              </Tooltip>
              <Button variant="outline" size="sm" onClick={() => handleDownload('json')}>
                JSON
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {/* 模型指标概览 - 核心KPI（行业标准：优先展示OOT，无OOT时展示测试集） */}
          {metrics && (
            <div className="space-y-2 mb-4">
              {/* 数据来源标注 */}
              <div className="text-xs text-muted-foreground text-right">
                数据来源：{metrics.source === 'oot' ? 'OOT验证集' : '测试集'}
              </div>
              <div className="grid grid-cols-4 gap-3">
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3 cursor-help">
                    <div className="flex items-center gap-2 text-blue-600 dark:text-blue-400 mb-1">
                      <Activity className="h-4 w-4" />
                      <span className="text-sm font-medium">KS值</span>
                    </div>
                    <div className="text-2xl font-bold text-blue-700 dark:text-blue-300">
                      {(metrics.ks * 100).toFixed(2)}%
                    </div>
                    <div className={cn("text-xs mt-0.5", getKSLevel(metrics.ks).colorClass)}>
                      {getKSLevel(metrics.ks).label}
                    </div>
                  </div>
                </TooltipTrigger>
                <TooltipContent>
                  <p>模型区分好坏客户的能力，越高越好</p>
                  <p className="text-xs text-gray-300 dark:text-gray-200">通常 &gt;20% 可用，&gt;30% 较好</p>
                </TooltipContent>
              </Tooltip>

              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-3 cursor-help">
                    <div className="flex items-center gap-2 text-green-600 dark:text-green-400 mb-1">
                      <TrendingUp className="h-4 w-4" />
                      <span className="text-sm font-medium">AUC</span>
                    </div>
                    <div className="text-2xl font-bold text-green-700 dark:text-green-300">
                      {metrics.auc.toFixed(4)}
                    </div>
                    <div className={cn("text-xs mt-0.5", getAUCLevel(metrics.auc).colorClass)}>
                      {getAUCLevel(metrics.auc).label}
                    </div>
                  </div>
                </TooltipTrigger>
                <TooltipContent>
                  <p>ROC曲线下面积，衡量排序能力</p>
                  <p className="text-xs text-gray-300 dark:text-gray-200">0.5=随机，0.7+=可用，0.8+=优秀</p>
                </TooltipContent>
              </Tooltip>

              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-3 cursor-help">
                    <div className="flex items-center gap-2 text-purple-600 dark:text-purple-400 mb-1">
                      <Percent className="h-4 w-4" />
                      <span className="text-sm font-medium">Gini</span>
                    </div>
                    <div className="text-2xl font-bold text-purple-700 dark:text-purple-300">
                      {(metrics.gini * 100).toFixed(2)}%
                    </div>
                    <div className={cn("text-xs mt-0.5", getGiniLevel(metrics.gini).colorClass)}>
                      {getGiniLevel(metrics.gini).label}
                    </div>
                  </div>
                </TooltipTrigger>
                <TooltipContent>
                  <p>基尼系数 = 2×AUC - 1</p>
                  <p className="text-xs text-gray-300 dark:text-gray-200">与AUC等价的另一种表示</p>
                </TooltipContent>
              </Tooltip>

              <Tooltip>
                <TooltipTrigger asChild>
                  <div className={cn(
                    "rounded-lg p-3 cursor-help",
                    psiResult ? (
                      psiResult.level === 'good' ? "bg-orange-50 dark:bg-orange-900/20" :
                      psiResult.level === 'warning' ? "bg-yellow-50 dark:bg-yellow-900/20" :
                      "bg-red-50 dark:bg-red-900/20"
                    ) : "bg-gray-50 dark:bg-gray-900/20"
                  )}>
                    <div className={cn(
                      "flex items-center gap-2 mb-1",
                      psiResult ? (
                        psiResult.level === 'good' ? "text-orange-600 dark:text-orange-400" :
                        psiResult.level === 'warning' ? "text-yellow-600 dark:text-yellow-400" :
                        "text-red-600 dark:text-red-400"
                      ) : "text-gray-600 dark:text-gray-400"
                    )}>
                      <Activity className="h-4 w-4" />
                      <span className="text-sm font-medium">PSI</span>
                    </div>
                    <div className={cn(
                      "text-2xl font-bold",
                      psiResult ? (
                        psiResult.level === 'good' ? "text-orange-700 dark:text-orange-300" :
                        psiResult.level === 'warning' ? "text-yellow-700 dark:text-yellow-300" :
                        "text-red-700 dark:text-red-300"
                      ) : "text-gray-700 dark:text-gray-300"
                    )}>
                      {psiResult ? psiResult.value.toFixed(4) : '-'}
                    </div>
                    {psiResult && (
                      <div className="text-xs text-muted-foreground mt-0.5">
                        {psiResult.stability}
                      </div>
                    )}
                  </div>
                </TooltipTrigger>
                <TooltipContent>
                  <p>群体稳定性指标（Population Stability Index）</p>
                  <p className="text-xs text-gray-300 dark:text-gray-200">&lt;0.1 稳定，0.1-0.25 轻微变化，&gt;0.25 显著变化</p>
                  {psiResult && <p className="text-xs mt-1">对比：{psiResult.comparison}</p>}
                </TooltipContent>
              </Tooltip>
              </div>
            </div>
          )}

          {/* 评估标准说明入口 */}
          {metrics && (
            <div className="flex justify-end mb-2">
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
                      评分卡模型评估标准（信贷风控行业标准）
                    </DialogTitle>
                  </DialogHeader>
                  <div className="space-y-4 text-sm">
                    {/* 核心指标总览 */}
                    <div className="p-3 bg-gradient-to-r from-blue-50 to-green-50 dark:from-blue-900/20 dark:to-green-900/20 rounded-lg border">
                      <h4 className="font-medium mb-2">核心评估指标</h4>
                      <div className="grid grid-cols-3 gap-2 text-center text-xs">
                        <div className="p-2 bg-white dark:bg-gray-800 rounded">
                          <div className="font-bold text-blue-600">KS值</div>
                          <div className="text-gray-500">区分能力</div>
                        </div>
                        <div className="p-2 bg-white dark:bg-gray-800 rounded">
                          <div className="font-bold text-green-600">AUC</div>
                          <div className="text-gray-500">排序能力</div>
                        </div>
                        <div className="p-2 bg-white dark:bg-gray-800 rounded">
                          <div className="font-bold text-purple-600">Gini</div>
                          <div className="text-gray-500">不平等度</div>
                        </div>
                      </div>
                    </div>

                    {/* 各指标详细标准 */}
                    <div className="space-y-3">
                      {/* KS值 */}
                      <div className="border rounded-lg p-3">
                        <h4 className="font-medium text-blue-700 dark:text-blue-400 mb-2 flex items-center gap-2">
                          <span className="w-2 h-2 bg-blue-500 rounded-full"></span>
                          KS值（Kolmogorov-Smirnov）
                        </h4>
                        <p className="text-gray-600 dark:text-gray-400 text-xs mb-2">
                          衡量模型区分好坏客户的最大能力。KS = max(|累计坏客户占比 - 累计好客户占比|)
                        </p>
                        <table className="w-full text-xs border-collapse">
                          <thead>
                            <tr className="bg-gray-50 dark:bg-gray-800">
                              <th className="border p-1.5 text-left">等级</th>
                              <th className="border p-1.5 text-left">KS阈值</th>
                              <th className="border p-1.5 text-left">说明</th>
                            </tr>
                          </thead>
                          <tbody>
                            <tr>
                              <td className="border p-1.5"><Badge className="bg-green-100 text-green-700 text-xs">优秀</Badge></td>
                              <td className="border p-1.5 font-mono">≥ 40%</td>
                              <td className="border p-1.5">区分能力强，模型效果显著</td>
                            </tr>
                            <tr>
                              <td className="border p-1.5"><Badge className="bg-blue-100 text-blue-700 text-xs">良好</Badge></td>
                              <td className="border p-1.5 font-mono">30% - 40%</td>
                              <td className="border p-1.5">区分能力较好，可投入使用</td>
                            </tr>
                            <tr>
                              <td className="border p-1.5"><Badge className="bg-yellow-100 text-yellow-700 text-xs">可用</Badge></td>
                              <td className="border p-1.5 font-mono">20% - 30%</td>
                              <td className="border p-1.5">区分能力一般，建议优化</td>
                            </tr>
                            <tr>
                              <td className="border p-1.5"><Badge className="bg-red-100 text-red-700 text-xs">差</Badge></td>
                              <td className="border p-1.5 font-mono">&lt; 20%</td>
                              <td className="border p-1.5">区分能力弱，需重新建模</td>
                            </tr>
                          </tbody>
                        </table>
                      </div>

                      {/* AUC */}
                      <div className="border rounded-lg p-3">
                        <h4 className="font-medium text-green-700 dark:text-green-400 mb-2 flex items-center gap-2">
                          <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                          AUC（Area Under ROC Curve）
                        </h4>
                        <p className="text-gray-600 dark:text-gray-400 text-xs mb-2">
                          ROC曲线下面积，衡量模型对样本的排序能力。随机模型AUC=0.5，完美模型AUC=1.0
                        </p>
                        <table className="w-full text-xs border-collapse">
                          <thead>
                            <tr className="bg-gray-50 dark:bg-gray-800">
                              <th className="border p-1.5 text-left">等级</th>
                              <th className="border p-1.5 text-left">AUC阈值</th>
                              <th className="border p-1.5 text-left">说明</th>
                            </tr>
                          </thead>
                          <tbody>
                            <tr>
                              <td className="border p-1.5"><Badge className="bg-green-100 text-green-700 text-xs">优秀</Badge></td>
                              <td className="border p-1.5 font-mono">≥ 0.80</td>
                              <td className="border p-1.5">排序能力强</td>
                            </tr>
                            <tr>
                              <td className="border p-1.5"><Badge className="bg-blue-100 text-blue-700 text-xs">良好</Badge></td>
                              <td className="border p-1.5 font-mono">0.75 - 0.80</td>
                              <td className="border p-1.5">排序能力较好</td>
                            </tr>
                            <tr>
                              <td className="border p-1.5"><Badge className="bg-yellow-100 text-yellow-700 text-xs">可用</Badge></td>
                              <td className="border p-1.5 font-mono">0.70 - 0.75</td>
                              <td className="border p-1.5">排序能力一般</td>
                            </tr>
                            <tr>
                              <td className="border p-1.5"><Badge className="bg-red-100 text-red-700 text-xs">差</Badge></td>
                              <td className="border p-1.5 font-mono">&lt; 0.70</td>
                              <td className="border p-1.5">接近随机，需改进</td>
                            </tr>
                          </tbody>
                        </table>
                      </div>

                      {/* Gini */}
                      <div className="border rounded-lg p-3">
                        <h4 className="font-medium text-purple-700 dark:text-purple-400 mb-2 flex items-center gap-2">
                          <span className="w-2 h-2 bg-purple-500 rounded-full"></span>
                          Gini系数
                        </h4>
                        <p className="text-gray-600 dark:text-gray-400 text-xs mb-2">
                          Gini = 2 × AUC - 1，与AUC线性相关，是另一种常用的模型评估指标。
                        </p>
                        <div className="text-xs space-y-1">
                          <p>• <b>优秀</b>：Gini ≥ 60%</p>
                          <p>• <b>良好</b>：Gini 50% - 60%</p>
                          <p>• <b>可用</b>：Gini 40% - 50%</p>
                          <p>• <b>差</b>：Gini &lt; 40%</p>
                        </div>
                      </div>

                      {/* 稳定性 */}
                      <div className="border rounded-lg p-3">
                        <h4 className="font-medium text-orange-700 dark:text-orange-400 mb-2 flex items-center gap-2">
                          <span className="w-2 h-2 bg-orange-500 rounded-full"></span>
                          模型稳定性评估
                        </h4>
                        <p className="text-gray-600 dark:text-gray-400 text-xs mb-2">
                          通过训练集与测试集的指标差异判断过拟合风险。
                        </p>
                        <div className="text-xs space-y-1">
                          <p>• <b>KS差异</b>：训练集与测试集KS差异 &lt; 5%为稳定</p>
                          <p>• <b>AUC差异</b>：训练集与测试集AUC差异 &lt; 0.03为稳定</p>
                          <p>• <b>PSI（群体稳定性）</b>：&lt; 0.1稳定，0.1-0.25需关注，&gt; 0.25显著变化</p>
                        </div>
                      </div>
                    </div>

                    {/* 分离度评估标准 */}
                    <div className="p-3 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
                      <h4 className="font-medium mb-2">好坏样本分离度</h4>
                      <p className="text-xs text-gray-600 dark:text-gray-300 mb-2">
                        好样本均分与坏样本均分的差值，反映模型区分能力。适用于典型300-800分评分卡。
                      </p>
                      <div className="text-xs space-y-1">
                        <p>• <b>≥ 60分</b>：<span className="text-amber-600">★ 优秀</span>，区分能力很强</p>
                        <p>• <b>40-59分</b>：<span className="text-green-600">✓ 良好</span>，区分能力较好</p>
                        <p>• <b>20-39分</b>：<span className="text-blue-600">○ 合格</span>，区分能力一般</p>
                        <p>• <b>&lt; 20分</b>：<span className="text-red-600">△ 偏低</span>，建议优化模型</p>
                      </div>
                    </div>

                    {/* 综合评级说明 */}
                    <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg border">
                      <h4 className="font-medium mb-2">模型上线建议</h4>
                      <div className="text-xs space-y-1">
                        <p>• <b>可直接上线</b>：KS ≥ 30% 且 AUC ≥ 0.75，训练/测试差异小</p>
                        <p>• <b>建议优化后上线</b>：KS 20-30% 或 AUC 0.70-0.75</p>
                        <p>• <b>需重新建模</b>：KS &lt; 20% 或 AUC &lt; 0.70</p>
                      </div>
                    </div>

                    {/* 标准来源 */}
                    <div className="text-xs text-gray-500 border-t pt-3">
                      <p><b>标准来源</b>：基于信贷风控行业通用实践，参考银行、消费金融机构的评分卡建模标准。</p>
                    </div>
                  </div>
                </DialogContent>
              </Dialog>
            </div>
          )}

          {/* 多数据集指标对比表格 */}
          {multiDatasetMetrics && (Object.keys(multiDatasetMetrics).length > 0) && (
            <div className="mb-4">
              <div className="text-sm font-medium text-muted-foreground mb-2">
                数据集指标对比
              </div>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="text-center">数据集</TableHead>
                      <TableHead className="text-center">样本数</TableHead>
                      <TableHead className="text-center">坏账率</TableHead>
                      <TableHead className="text-center">KS</TableHead>
                      <TableHead className="text-center">AUC</TableHead>
                      <TableHead className="text-center">Gini</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {multiDatasetMetrics.train && (
                      <TableRow>
                        <TableCell className="text-center font-medium">训练集</TableCell>
                        <TableCell className="text-center">{multiDatasetMetrics.train.samples?.toLocaleString() || '-'}</TableCell>
                        <TableCell className="text-center">{multiDatasetMetrics.train.bad_rate?.toFixed(2) || '-'}%</TableCell>
                        <TableCell className="text-center text-blue-600 font-medium">{(multiDatasetMetrics.train.ks * 100).toFixed(2)}%</TableCell>
                        <TableCell className="text-center text-green-600 font-medium">{multiDatasetMetrics.train.auc.toFixed(4)}</TableCell>
                        <TableCell className="text-center text-purple-600 font-medium">{(multiDatasetMetrics.train.gini * 100).toFixed(2)}%</TableCell>
                      </TableRow>
                    )}
                    {multiDatasetMetrics.test && (
                      <TableRow>
                        <TableCell className="text-center font-medium">测试集</TableCell>
                        <TableCell className="text-center">{multiDatasetMetrics.test.samples?.toLocaleString() || '-'}</TableCell>
                        <TableCell className="text-center">{multiDatasetMetrics.test.bad_rate?.toFixed(2) || '-'}%</TableCell>
                        <TableCell className="text-center text-blue-600 font-medium">{(multiDatasetMetrics.test.ks * 100).toFixed(2)}%</TableCell>
                        <TableCell className="text-center text-green-600 font-medium">{multiDatasetMetrics.test.auc.toFixed(4)}</TableCell>
                        <TableCell className="text-center text-purple-600 font-medium">{(multiDatasetMetrics.test.gini * 100).toFixed(2)}%</TableCell>
                      </TableRow>
                    )}
                    {/* OOT验证集始终显示（即使无数据，显示为-） */}
                    <TableRow className={!multiDatasetMetrics.oot ? 'text-muted-foreground' : ''}>
                      <TableCell className="text-center font-medium">OOT验证集</TableCell>
                      <TableCell className="text-center">{multiDatasetMetrics.oot?.samples?.toLocaleString() || '-'}</TableCell>
                      <TableCell className="text-center">{multiDatasetMetrics.oot?.bad_rate != null ? `${multiDatasetMetrics.oot.bad_rate.toFixed(2)}%` : '-'}</TableCell>
                      <TableCell className="text-center text-blue-600 font-medium">{multiDatasetMetrics.oot?.ks != null ? `${(multiDatasetMetrics.oot.ks * 100).toFixed(2)}%` : '-'}</TableCell>
                      <TableCell className="text-center text-green-600 font-medium">{multiDatasetMetrics.oot?.auc != null ? multiDatasetMetrics.oot.auc.toFixed(4) : '-'}</TableCell>
                      <TableCell className="text-center text-purple-600 font-medium">{multiDatasetMetrics.oot?.gini != null ? `${(multiDatasetMetrics.oot.gini * 100).toFixed(2)}%` : '-'}</TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </div>
              {/* 过拟合警告 - 只有当有实际内容时才显示（排除None/null/空字符串） */}
              {overfitWarning && overfitWarning !== 'None' && overfitWarning.trim() !== '' && (
                <div className="mt-2 p-2 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg text-sm text-yellow-700 dark:text-yellow-400">
                  ⚠️ {overfitWarning}
                </div>
              )}
            </div>
          )}

          {/* 详细结果标签页 */}
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="flex flex-wrap">
              {/* 样本与特征Tab - 始终显示，数据加载中显示提示 */}
              <TabsTrigger value="sample-data" className="text-xs">
                <Database className="h-3 w-3 mr-1" />
                样本与特征
              </TabsTrigger>
              <TabsTrigger value="charts" className="text-xs">
                <TrendingUp className="h-3 w-3 mr-1" />
                评估图表
              </TabsTrigger>
              <TabsTrigger value="scorecard" className="text-xs">
                <Calculator className="h-3 w-3 mr-1" />
                评分卡明细
              </TabsTrigger>
              <TabsTrigger value="selection" className="text-xs">
                <Layers className="h-3 w-3 mr-1" />
                变量筛选
              </TabsTrigger>
              <TabsTrigger value="statistics" className="text-xs">
                <LineChart className="h-3 w-3 mr-1" />
                模型系数
              </TabsTrigger>
            </TabsList>

            {/* 样本与特征标签页 */}
            <TabsContent value="sample-data" className="mt-3">
              {stagesData ? (
                <SampleDataPanel stagesData={stagesData} />
              ) : loading ? (
                <div className="flex items-center justify-center py-8 text-muted-foreground">
                  <Loader2 className="h-5 w-5 animate-spin mr-2" />
                  <span className="text-sm">正在加载样本数据...</span>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
                  <Database className="h-8 w-8 mb-2 opacity-50" />
                  <span className="text-sm">样本数据暂不可用</span>
                  <span className="text-xs mt-1">请稍后刷新或重新加载任务</span>
                </div>
              )}
            </TabsContent>

            {/* 评估图表 */}
            <TabsContent value="charts" className="mt-3">
              <div className="text-xs text-muted-foreground mb-2">
                模型评估的ROC曲线、KS曲线、Lift曲线和评分分布图
              </div>
              {chartData ? (
                <div className="max-h-[500px] overflow-auto">
                {/* 数据集切换选择器 - ROC/KS/Lift曲线 */}
                {(() => {
                  // 获取当前选中数据集的图表数据（使用组件级别的selectedChartDataset状态）
                  const currentChartData = multiDatasetChartData?.[selectedChartDataset] || chartData;
                  
                  // 获取当前数据集的metrics（用于显示KS值）
                  const currentMetrics = multiDatasetMetrics?.[selectedChartDataset] || metrics;
                  
                  // 检查各数据集是否有ROC/KS数据
                  const hasTrainData = Boolean(multiDatasetChartData?.train?.roc || multiDatasetChartData?.train?.ks);
                  const hasTestData = Boolean(multiDatasetChartData?.test?.roc || multiDatasetChartData?.test?.ks);
                  const hasOOTData = Boolean(multiDatasetChartData?.oot?.roc || multiDatasetChartData?.oot?.ks);
                  
                  // 数据集标签配置（OOT始终显示）
                  const datasetTabs = [
                    { key: 'test' as const, label: '测试集', hasData: hasTestData, warning: null },
                    { key: 'train' as const, label: '训练集', hasData: hasTrainData, warning: '训练集指标可能存在过拟合，仅供参考' },
                    { key: 'oot' as const, label: 'OOT验证集', hasData: hasOOTData, warning: null },
                  ];
                  
                  return (
                    <>
                      {/* 数据集切换标签 */}
                      <div className="flex items-center gap-2 mb-3">
                        <span className="text-xs text-muted-foreground">数据集:</span>
                        <div className="flex gap-1">
                          {datasetTabs.map(tab => (
                            <TooltipProvider key={tab.key}>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <button
                                    onClick={() => tab.hasData && setSelectedChartDataset(tab.key)}
                                    disabled={!tab.hasData}
                                    className={cn(
                                      "px-3 py-1 text-xs rounded-md transition-colors",
                                      selectedChartDataset === tab.key
                                        ? "bg-primary text-primary-foreground"
                                        : tab.hasData
                                          ? "bg-muted hover:bg-muted/80"
                                          : "bg-muted/50 text-muted-foreground cursor-not-allowed",
                                      tab.key === 'train' && selectedChartDataset === tab.key && "bg-amber-500 hover:bg-amber-600"
                                    )}
                                  >
                                    {tab.label}
                                    {!tab.hasData && <span className="ml-1 opacity-60">(无数据)</span>}
                                  </button>
                                </TooltipTrigger>
                                <TooltipContent>
                                  {!tab.hasData 
                                    ? `暂无${tab.label}数据，请在数据准备阶段添加`
                                    : tab.warning 
                                      ? tab.warning 
                                      : `查看${tab.label}的ROC/KS/Lift曲线`
                                  }
                                </TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
                          ))}
                        </div>
                        {selectedChartDataset === 'train' && hasTrainData && (
                          <Badge variant="outline" className="text-amber-600 border-amber-300 text-[10px]">
                            <AlertTriangle className="h-3 w-3 mr-1" />
                            过拟合风险
                          </Badge>
                        )}
                      </div>
                      
                      <div className="grid grid-cols-2 gap-4">
                        {/* ROC曲线 */}
                        {currentChartData?.roc && (
                          <div className="border rounded-lg p-4">
                            <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                              <TrendingUp className="h-4 w-4 text-blue-500" />
                              ROC曲线 (AUC = {currentChartData.roc.auc.toFixed(4)})
                            </h4>
                            <div className="h-[200px] flex items-center justify-center bg-gray-50 dark:bg-gray-900/20 rounded">
                              <ROCChart data={currentChartData.roc} />
                            </div>
                          </div>
                        )}
                        
                        {/* KS曲线 - 使用当前数据集的metrics.ks确保与开发结果一致 */}
                        {currentChartData?.ks && (
                          <div className="border rounded-lg p-4">
                            <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                              <Activity className="h-4 w-4 text-green-500" />
                              KS曲线 (KS = {currentMetrics?.ks ? (currentMetrics.ks * 100).toFixed(2) : (currentChartData.ks.ks_max * 100).toFixed(2)}%)
                            </h4>
                            <div className="h-[200px] flex items-center justify-center bg-gray-50 dark:bg-gray-900/20 rounded">
                              <KSChart data={currentChartData.ks} />
                            </div>
                          </div>
                        )}
                        
                        {/* Lift曲线 - 使用当前选中数据集 */}
                        {(() => {
                          // 从当前选中数据集获取Lift数据
                          const liftBins = 
                            currentChartData?.score_distribution?.ranking_analysis?.bins ||
                            currentChartData?.score_distribution?.bins;
                          
                          if (!liftBins || liftBins.length === 0) return null;
                          
                          // 获取首尾Lift信息
                          const firstLift = liftBins[0]?.lift;
                          const lastLift = liftBins[liftBins.length - 1]?.lift;
                          
                          return (
                            <div className="border rounded-lg p-4">
                              <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                                <TrendingUp className="h-4 w-4 text-orange-500" />
                                Lift曲线
                                <TooltipProvider>
                                  <Tooltip>
                                    <TooltipTrigger>
                                      <HelpCircle className="h-3.5 w-3.5 text-muted-foreground" />
                                    </TooltipTrigger>
                                    <TooltipContent className="max-w-xs">
                                      <p className="text-xs">
                                        Lift值 = 分箱坏样本率 / 整体坏样本率。
                                        Lift&gt;1表示风险高于平均，Lift&lt;1表示风险低于平均。
                                        理想模型：左高右低，首组Lift≥2，末组Lift≤0.5。
                                      </p>
                                    </TooltipContent>
                                  </Tooltip>
                                </TooltipProvider>
                              </h4>
                              <div className="flex items-center gap-3 text-xs text-muted-foreground mb-2">
                                {firstLift != null && (
                                  <span>首组: <span className={firstLift >= 2 ? "text-green-600 font-medium" : firstLift >= 1.5 ? "text-blue-600" : "text-amber-600"}>{firstLift.toFixed(2)}</span></span>
                                )}
                                {lastLift != null && (
                                  <span>末组: <span className={lastLift <= 0.5 ? "text-green-600 font-medium" : lastLift <= 0.8 ? "text-blue-600" : "text-amber-600"}>{lastLift.toFixed(2)}</span></span>
                                )}
                              </div>
                              <div className="h-[200px] flex items-center justify-center bg-gray-50 dark:bg-gray-900/20 rounded">
                                <LiftChart bins={liftBins} />
                              </div>
                            </div>
                          );
                        })()}
                      </div>
                    </>
                  );
                })()}
                
                {/* PSI分布对比图和评分分布表格 - 独立于数据集切换 */}
                <div className="grid grid-cols-2 gap-4 mt-4">
                  {/* 2026-02-10: PSI分布对比图 - 始终显示 训练集 vs 测试集 */}
                  {(() => {
                    // 训练集分布数据
                    const trainDistribution = multiDatasetChartData?.train?.score_distribution?.distribution_analysis?.bins ||
                                             multiDatasetChartData?.train?.score_distribution?.bins;
                    // 测试集分布数据
                    const testDistribution = multiDatasetChartData?.test?.score_distribution?.distribution_analysis?.bins ||
                                            multiDatasetChartData?.test?.score_distribution?.bins;
                    
                    // 使用新的 psiTrainVsTest，兼容旧的 psiResult（当comparison是测试集时）
                    const psiTestData = psiTrainVsTest || (psiResult?.comparison === "训练集 vs 测试集" ? psiResult : null);
                    
                    if (!trainDistribution || !testDistribution || !psiTestData) return null;
                    
                    return (
                      <div className="border rounded-lg p-4">
                        <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                          <Activity className="h-4 w-4 text-cyan-500" />
                          PSI分布对比（训练集 vs 测试集）
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger>
                                <HelpCircle className="h-3.5 w-3.5 text-muted-foreground" />
                              </TooltipTrigger>
                              <TooltipContent className="max-w-xs">
                                <p className="text-xs">
                                  验证训练集与测试集的评分分布一致性。
                                  PSI&lt;0.1表示分布稳定（随机划分应接近0），
                                  PSI高可能说明数据划分方式非随机。
                                </p>
                              </TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                        </h4>
                        <PSIComparisonChart
                          expectedData={trainDistribution}
                          expectedLabel="训练集"
                          actualData={testDistribution}
                          actualLabel="测试集"
                          psiValue={psiTestData.value}
                          stability={psiTestData.stability}
                        />
                      </div>
                    );
                  })()}
                  
                  {/* 2026-02-10: PSI分布对比图 - 有OOT时显示 训练集 vs OOT */}
                  {(() => {
                    const hasOOT = multiDatasetChartData?.oot?.score_distribution;
                    if (!hasOOT) return null;
                    
                    // 训练集分布数据
                    const trainDistribution = multiDatasetChartData?.train?.score_distribution?.distribution_analysis?.bins ||
                                             multiDatasetChartData?.train?.score_distribution?.bins;
                    // OOT分布数据
                    const ootDistribution = multiDatasetChartData?.oot?.score_distribution?.distribution_analysis?.bins ||
                                           multiDatasetChartData?.oot?.score_distribution?.bins;
                    
                    // 使用新的 psiTrainVsOot，兼容旧的 psiResult（当comparison是OOT时）
                    const psiOotData = psiTrainVsOot || (psiResult?.comparison === "训练集 vs OOT" ? psiResult : null);
                    
                    if (!trainDistribution || !ootDistribution || !psiOotData) return null;
                    
                    return (
                      <div className="border rounded-lg p-4">
                        <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                          <Activity className="h-4 w-4 text-orange-500" />
                          PSI分布对比（训练集 vs OOT）
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger>
                                <HelpCircle className="h-3.5 w-3.5 text-muted-foreground" />
                              </TooltipTrigger>
                              <TooltipContent className="max-w-xs">
                                <p className="text-xs">
                                  验证模型在时间外样本上的稳定性。
                                  PSI&lt;0.1表示稳定，0.1-0.25轻微变化，&gt;0.25显著变化。
                                  这是评估模型稳定性最重要的指标。
                                </p>
                              </TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                        </h4>
                        <PSIComparisonChart
                          expectedData={trainDistribution}
                          expectedLabel="训练集"
                          actualData={ootDistribution}
                          actualLabel="OOT验证集"
                          psiValue={psiOotData.value}
                          stability={psiOotData.stability}
                        />
                      </div>
                    );
                  })()}
                  
                  {/* 评分分布 - 多数据集排序性表格（带红色渐变条） */}
                  {(multiDatasetChartData || chartData.score_distribution) && (
                    <div className="border rounded-lg p-4 col-span-2">
                      <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
                        <BarChart3 className="h-4 w-4 text-purple-500" />
                        排序性分析/评分分布
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger>
                              <HelpCircle className="h-3.5 w-3.5 text-muted-foreground" />
                            </TooltipTrigger>
                            <TooltipContent className="max-w-xs">
                              <p className="text-xs">
                                排序性分析展示模型的风险区分能力。低分段应有更高的坏样本率（Lift&gt;1），
                                高分段应有较低的坏样本率（Lift&lt;1）。红色渐变条直观展示各分箱的风险水平。
                              </p>
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                      </h4>
                      {/* 优先使用多数据集组件 */}
                      {multiDatasetChartData ? (
                        <MultiDatasetScoreDistribution 
                          multiDatasetChartData={multiDatasetChartData}
                          defaultDataset="test"
                        />
                      ) : chartData.score_distribution ? (
                        <>
                          {/* 回退到单数据集表格 */}
                          <div className="mb-3">
                            <ScoreDistributionTable data={chartData.score_distribution} />
                          </div>
                          {/* 分布图 */}
                          <div className="h-[200px] flex items-center justify-center bg-gray-50 dark:bg-gray-900/20 rounded">
                            <ScoreDistributionChart data={chartData.score_distribution} />
                          </div>
                        </>
                      ) : null}
                    </div>
                  )}
                </div>
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <BarChart3 className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p>暂无图表数据</p>
                  <p className="text-xs mt-1">图表数据将在模型评估阶段生成</p>
                </div>
              )}
            </TabsContent>

            {/* 变量筛选详情 */}
            <TabsContent value="selection" className="mt-3">
              <div className="text-xs text-muted-foreground mb-2">
                变量IV排行与筛选流程详情：IV值、相关性分析、VIF检验、逐步回归、系数验证
              </div>
              <div className="max-h-[400px] overflow-auto space-y-4">
                {/* 特征筛选漏斗概览（参考规则挖掘设计） */}
                <FeatureSelectionFunnel stagesData={stagesData} modelVariablesCount={modelVariables.length} />
                
                {/* 变量IV排行（展示所有原始特征，包括无IV值的） */}
                {(ivData.length > 0 || stagesData?.data_loading?.output_preview?.var_filter_result) && (
                  <div className="border rounded-lg p-3">
                    <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                      <BarChart3 className="h-4 w-4 text-blue-500" />
                      变量IV排行
                      <span className="text-[10px] text-gray-400 font-normal">
                        （展示所有{stagesData?.data_loading?.output_preview?.var_filter_result?.input_features || ivData.length}个原始特征）
                      </span>
                    </h4>
                    <div className="max-h-[200px] overflow-auto rounded-md border">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead className="sticky top-0 bg-background w-12 text-xs">#</TableHead>
                            <TableHead className="sticky top-0 bg-background text-xs">变量</TableHead>
                            <TableHead className="sticky top-0 bg-background text-right text-xs">IV值</TableHead>
                            <TableHead className="sticky top-0 bg-background text-xs">预测能力</TableHead>
                            <TableHead className="sticky top-0 bg-background text-center text-xs">状态</TableHead>
                            <TableHead className="sticky top-0 bg-background text-xs">淘汰阶段</TableHead>
                            <TableHead className="sticky top-0 bg-background text-xs">淘汰原因</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {(() => {
                            // 构建淘汰信息映射（包含原因和阶段）
                            type EliminationInfo = { reason: string; stage: string; iv?: number };
                            const eliminationMap: Record<string, EliminationInfo> = {};
                            
                            // ========== 0. 从var_filter获取数据质量筛选淘汰的特征（高缺失率/高同值率） ==========
                            const varFilterResult = stagesData?.data_loading?.output_preview?.var_filter_result || {};
                            // 高缺失率移除
                            const removedByMissing = varFilterResult.removed_by_missing || [];
                            removedByMissing.forEach((item: { feature?: string; reason?: string; missing_rate?: number }) => {
                              if (item.feature) {
                                eliminationMap[item.feature] = { 
                                  reason: item.reason || `缺失率${((item.missing_rate || 0) * 100).toFixed(0)}%`, 
                                  stage: '数据质量(var_filter)' 
                                };
                              }
                            });
                            // 高同值率移除
                            const removedByIdentical = varFilterResult.removed_by_identical || [];
                            removedByIdentical.forEach((item: { feature?: string; reason?: string; identical_rate?: number }) => {
                              if (item.feature) {
                                eliminationMap[item.feature] = { 
                                  reason: item.reason || `同值率${((item.identical_rate || 0) * 100).toFixed(0)}%`, 
                                  stage: '数据质量(var_filter)' 
                                };
                              }
                            });
                            
                            // ========== 1. 从WOE分箱阶段获取分箱失败的特征 ==========
                            const woeFiltered = stagesData?.woe_binning?.output_preview?.woe_filtered || {};
                            const woeFilteredFeatures = woeFiltered.features || [];
                            woeFilteredFeatures.forEach((feat: string) => {
                              if (!eliminationMap[feat]) {
                                eliminationMap[feat] = { 
                                  reason: woeFiltered.reason || '常量/分箱失败', 
                                  stage: 'WOE分箱' 
                                };
                              }
                            });
                            
                            // ========== 2. 从feature_selection阶段的all_features_detail获取（IV/相关性/VIF） ==========
                            const allFeaturesDetail = stagesData?.feature_selection?.output_preview?.all_features_detail || [];
                            allFeaturesDetail.forEach((item: { feature?: string; remove_reason?: string }) => {
                              if (item.feature && item.remove_reason) {
                                const stage = item.remove_reason.includes('IV') ? '特征筛选(IV)' 
                                  : item.remove_reason.includes('相关性') ? '特征筛选(相关性)'
                                  : item.remove_reason.includes('VIF') ? '特征筛选(VIF)'
                                  : '特征筛选';
                                eliminationMap[item.feature] = { reason: item.remove_reason, stage };
                                eliminationMap[item.feature + '_woe'] = { reason: item.remove_reason, stage };
                              }
                            });
                            
                            // ========== 3. 从model_training阶段获取逐步回归移除的特征 ==========
                            const stepwiseResult = stagesData?.model_training?.output_preview?.stepwise_result || {};
                            const stepwiseSteps = stepwiseResult.steps || [];
                            stepwiseSteps
                              .filter((s: { action?: string }) => s.action === 'remove')
                              .forEach((s: { feature?: string; pvalue?: number }) => {
                                if (s.feature) {
                                  const baseName = s.feature.replace(/_woe$/, '');
                                  const reason = `P值=${s.pvalue?.toFixed(4) || '不显著'}`;
                                  eliminationMap[s.feature] = { reason, stage: '模型训练(逐步回归)' };
                                  eliminationMap[baseName] = { reason, stage: '模型训练(逐步回归)' };
                                }
                              });
                            // 也从removed_features获取
                            const stepwiseRemovedFeatures = stepwiseResult.removed_features || [];
                            stepwiseRemovedFeatures.forEach((feat: string) => {
                              const baseName = feat.replace(/_woe$/, '');
                              if (!eliminationMap[baseName]) {
                                eliminationMap[feat] = { reason: 'P值不显著', stage: '模型训练(逐步回归)' };
                                eliminationMap[baseName] = { reason: 'P值不显著', stage: '模型训练(逐步回归)' };
                              }
                            });
                            
                            // ========== 4. 从model_training阶段获取系数方向异常的特征 ==========
                            const coeffValidation = stagesData?.model_training?.output_preview?.coefficient_validation || {};
                            const invalidDirection = coeffValidation.invalid_direction || [];
                            invalidDirection.forEach((feat: string) => {
                              const baseName = feat.replace(/_woe$/, '');
                              if (!eliminationMap[baseName] && !eliminationMap[feat]) {
                                eliminationMap[feat] = { reason: '系数方向异常', stage: '模型训练(系数验证)' };
                                eliminationMap[baseName] = { reason: '系数方向异常', stage: '模型训练(系数验证)' };
                              }
                            });
                            const coefRemovedFeatures = coeffValidation.removed_features || [];
                            coefRemovedFeatures.forEach((feat: string) => {
                              const baseName = feat.replace(/_woe$/, '');
                              if (!eliminationMap[baseName]) {
                                eliminationMap[feat] = { reason: '系数方向异常', stage: '模型训练(系数验证)' };
                                eliminationMap[baseName] = { reason: '系数方向异常', stage: '模型训练(系数验证)' };
                              }
                            });
                            
                            // ========== 5. 从post_validation迭代验证获取移除特征（不显著/系数方向异常） ==========
                            const postValidation = stagesData?.model_training?.output_preview?.post_validation || {};
                            const iterations = postValidation.iterations || [];
                            iterations.forEach((iter: { removed_this_iteration?: Array<{ feature?: string; reason?: string }> }) => {
                              if (iter.removed_this_iteration && iter.removed_this_iteration.length > 0) {
                                iter.removed_this_iteration.forEach((removed: { feature?: string; reason?: string }) => {
                                  if (removed.feature) {
                                    const baseName = removed.feature.replace(/_woe$/, '');
                                    // 解析原因，映射到标准格式
                                    let stage = '模型训练(迭代验证)';
                                    let reason = removed.reason || '迭代验证移除';
                                    if (reason.includes('显著性') || reason.includes('不显著')) {
                                      stage = '模型训练(显著性检验)';
                                      reason = '不显著(P值过大)';
                                    } else if (reason.includes('系数') || reason.includes('方向') || reason.includes('负')) {
                                      stage = '模型训练(系数验证)';
                                      reason = '系数方向异常';
                                    }
                                    // 不覆盖已有记录，确保最早的淘汰阶段被记录
                                    if (!eliminationMap[baseName] && !eliminationMap[removed.feature]) {
                                      eliminationMap[removed.feature] = { reason, stage };
                                      eliminationMap[baseName] = { reason, stage };
                                    }
                                  }
                                });
                              }
                            });
                            
                            // ========== 构建完整的特征列表（包括无IV值的） ==========
                            type FeatureItem = { variable: string; iv: number | null };
                            const allFeatures: FeatureItem[] = [];
                            
                            // 添加有IV值的特征
                            ivData.forEach(item => {
                              allFeatures.push({ variable: item.variable, iv: item.iv });
                            });
                            
                            // 添加var_filter移除的特征（无IV值）
                            const ivVariableSet = new Set(ivData.map(item => item.variable));
                            [...removedByMissing, ...removedByIdentical].forEach((item: { feature?: string }) => {
                              if (item.feature && !ivVariableSet.has(item.feature)) {
                                allFeatures.push({ variable: item.feature, iv: null });
                              }
                            });
                            
                            // 添加WOE分箱失败的特征（无IV值）
                            woeFilteredFeatures.forEach((feat: string) => {
                              if (!ivVariableSet.has(feat) && !allFeatures.some(f => f.variable === feat)) {
                                allFeatures.push({ variable: feat, iv: null });
                              }
                            });
                            
                            // 排序：有IV值的按IV降序，无IV值的排在最后
                            allFeatures.sort((a, b) => {
                              if (a.iv === null && b.iv === null) return 0;
                              if (a.iv === null) return 1;
                              if (b.iv === null) return -1;
                              return b.iv - a.iv;
                            });
                            
                            return allFeatures.map((item, idx) => {
                                const baseName = item.variable.replace(/_woe$/, '');
                                const isInModel = modelVariables.some(v => 
                                  v === item.variable || 
                                  v === baseName ||
                                  item.variable === v + '_woe'
                                );
                                // 获取淘汰信息（包含原因和阶段）
                                const eliminationInfo = isInModel ? null : (eliminationMap[item.variable] || eliminationMap[baseName] || null);
                                
                                return (
                                  <TableRow key={idx} className={isInModel ? 'bg-green-50 dark:bg-green-900/10' : ''}>
                                    <TableCell className="text-muted-foreground text-xs">{idx + 1}</TableCell>
                                    <TableCell className="font-medium text-xs">{item.variable}</TableCell>
                                    <TableCell className="text-right font-mono text-xs">
                                      {item.iv !== null ? item.iv.toFixed(4) : <span className="text-gray-400">-</span>}
                                    </TableCell>
                                    <TableCell className="text-xs">
                                      {item.iv !== null ? (
                                        <Badge
                                          variant={
                                            item.iv >= 0.3
                                              ? "default"
                                              : item.iv >= 0.1
                                              ? "secondary"
                                              : "outline"
                                          }
                                          className="text-[10px]"
                                        >
                                          {item.iv >= 0.5
                                            ? "极强"
                                            : item.iv >= 0.3
                                            ? "强"
                                            : item.iv >= 0.1
                                            ? "中等"
                                            : item.iv >= 0.02
                                            ? "弱"
                                            : "极弱"}
                                        </Badge>
                                      ) : (
                                        <span className="text-gray-400 text-[10px]">未计算</span>
                                      )}
                                    </TableCell>
                                    <TableCell className="text-center text-xs">
                                      {isInModel ? (
                                        <Badge variant="default" className="text-[10px] bg-green-600">✓ 入模</Badge>
                                      ) : (
                                        <span className="text-muted-foreground">淘汰</span>
                                      )}
                                    </TableCell>
                                    <TableCell className="text-xs text-gray-500 whitespace-nowrap">
                                      {eliminationInfo?.stage || '-'}
                                    </TableCell>
                                    <TableCell className="text-xs max-w-[120px] truncate" title={eliminationInfo?.reason || ''}>
                                      {eliminationInfo?.reason ? (
                                        <span className="text-orange-600 dark:text-orange-400">{eliminationInfo.reason}</span>
                                      ) : (
                                        <span className="text-muted-foreground">-</span>
                                      )}
                                    </TableCell>
                                  </TableRow>
                                );
                              });
                          })()}
                        </TableBody>
                      </Table>
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      绿色高亮：最终入模变量 | 有IV值的按IV降序，无IV值的排在最后
                    </div>
                  </div>
                )}

                {/* 逐步回归结果 */}
                {selectionDetail?.stepwise_result && selectionDetail.stepwise_result.steps && selectionDetail.stepwise_result.steps.length > 0 && (
                  <div className="border rounded-lg p-3">
                    <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                      <TrendingUp className="h-4 w-4 text-blue-500" />
                      逐步回归 ({selectionDetail.stepwise_result.direction || 'both'}方向)
                      <Badge variant="outline" className="text-xs">
                        显著性水平: {selectionDetail.stepwise_result.significance_level || 0.05}
                      </Badge>
                    </h4>
                    <div className="max-h-[150px] overflow-auto">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead className="text-xs">步骤</TableHead>
                            <TableHead className="text-xs">操作</TableHead>
                            <TableHead className="text-xs">变量</TableHead>
                            <TableHead className="text-xs text-right">P值</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {selectionDetail.stepwise_result.steps.map((step, idx) => (
                            <TableRow key={idx}>
                              <TableCell className="text-xs">{step.iteration}</TableCell>
                              <TableCell className="text-xs">
                                <Badge variant={step.action === 'add' ? 'default' : 'destructive'} className="text-xs">
                                  {step.action === 'add' ? '添加' : '移除'}
                                </Badge>
                              </TableCell>
                              <TableCell className="text-xs font-medium">{step.feature.replace(/_woe$/, '')}</TableCell>
                              <TableCell className="text-xs text-right font-mono">
                                {step.pvalue.toFixed(6)}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </div>
                )}

                {/* 显著性检验结果 (P值) */}
                {selectionDetail?.stepwise_result?.final_pvalues && Object.keys(selectionDetail.stepwise_result.final_pvalues).length > 0 && (
                  <div className="border rounded-lg p-3">
                    <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                      <Percent className="h-4 w-4 text-green-500" />
                      显著性检验 (P值)
                    </h4>
                    <div className="max-h-[150px] overflow-auto">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead className="text-xs">变量</TableHead>
                            <TableHead className="text-xs text-right">P值</TableHead>
                            <TableHead className="text-xs text-center">显著性</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {Object.entries(selectionDetail.stepwise_result.final_pvalues)
                            .sort((a, b) => a[1] - b[1])
                            .map(([varName, pvalue], idx) => (
                              <TableRow key={idx}>
                                <TableCell className="text-xs font-medium">{varName.replace(/_woe$/, '')}</TableCell>
                                <TableCell className="text-xs text-right font-mono">{pvalue.toFixed(6)}</TableCell>
                                <TableCell className="text-xs text-center">
                                  {pvalue < 0.01 ? (
                                    <Badge variant="default" className="text-xs">***</Badge>
                                  ) : pvalue < 0.05 ? (
                                    <Badge variant="secondary" className="text-xs">**</Badge>
                                  ) : pvalue < 0.1 ? (
                                    <Badge variant="outline" className="text-xs">*</Badge>
                                  ) : (
                                    <span className="text-red-500">不显著</span>
                                  )}
                                </TableCell>
                              </TableRow>
                            ))}
                        </TableBody>
                      </Table>
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      ***: p&lt;0.01, **: p&lt;0.05, *: p&lt;0.1
                    </div>
                  </div>
                )}

                {/* 系数方向验证 */}
                {selectionDetail?.coefficient_validation && (
                  <div className="border rounded-lg p-3">
                    <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                      <Target className="h-4 w-4 text-purple-500" />
                      系数方向验证
                    </h4>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <div className="text-xs font-medium text-green-600 mb-1">
                          方向正确 ({selectionDetail.coefficient_validation.valid_direction?.length || 0})
                        </div>
                        <div className="flex flex-wrap gap-1">
                          {selectionDetail.coefficient_validation.valid_direction?.map((feat, idx) => (
                            <Badge key={idx} variant="outline" className="text-xs bg-green-50">
                              {feat.replace(/_woe$/, '')}
                            </Badge>
                          ))}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs font-medium text-red-600 mb-1">
                          方向异常 ({selectionDetail.coefficient_validation.invalid_direction?.length || 0})
                        </div>
                        <div className="flex flex-wrap gap-1">
                          {selectionDetail.coefficient_validation.invalid_direction?.map((feat, idx) => (
                            <Badge key={idx} variant="destructive" className="text-xs">
                              {feat.replace(/_woe$/, '')}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    </div>
                    {/* 警告信息 */}
                    {selectionDetail.coefficient_validation.warnings && selectionDetail.coefficient_validation.warnings.length > 0 && (
                      <div className="mt-2 p-2 bg-yellow-50 dark:bg-yellow-900/20 rounded text-xs text-yellow-700 dark:text-yellow-400">
                        {selectionDetail.coefficient_validation.warnings.map((warning, idx) => (
                          <div key={idx}>⚠️ {warning}</div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* 无数据提示 */}
                {!ivData.length && !selectionDetail?.stepwise_result && !selectionDetail?.coefficient_validation && (
                  <div className="text-center py-8 text-muted-foreground">
                    <Layers className="h-8 w-8 mx-auto mb-2 opacity-50" />
                    <p>暂无变量筛选详情</p>
                    <p className="text-xs mt-1">完成WOE分箱和特征筛选阶段后将显示详细信息</p>
                  </div>
                )}
              </div>
            </TabsContent>

            {/* 评分卡明细 */}
            <TabsContent value="scorecard" className="mt-3">
              <div className="text-xs text-muted-foreground mb-3">
                评分卡核心参数与入模变量评分贡献概览
              </div>
              <div className="space-y-4">
                {/* 评分卡概览（3卡片：入模变量数、评分区间、基准配置） */}
                {stagesData?.score_scaling?.output_preview && (
                  <div className="grid grid-cols-3 gap-3">
                    <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                      <div className="text-xs text-gray-500">入模变量数</div>
                      <div className="text-xl font-bold text-blue-600">
                        {stagesData.score_scaling.output_preview.scorecard_preview 
                          ? stagesData.score_scaling.output_preview.scorecard_preview.filter((item: any) => item.variable !== 'basepoints').length
                          : modelVariablesCount || "-"}
                      </div>
                    </div>
                    <div className="p-3 bg-indigo-50 dark:bg-indigo-900/20 rounded-lg border border-indigo-200 dark:border-indigo-800">
                      {(() => {
                        // 按优先级选择评分分布统计的数据集：OOT > 测试集 > 训练集
                        const scoreStatsByDataset = stagesData.score_scaling.output_preview.score_stats_by_dataset;
                        let selectedStats = stagesData.score_scaling.output_preview.actual_score_stats; // 兜底：旧字段
                        let datasetLabel = "训练集";
                        
                        if (scoreStatsByDataset) {
                          if (scoreStatsByDataset.oot) {
                            selectedStats = scoreStatsByDataset.oot;
                            datasetLabel = "OOT验证集";
                          } else if (scoreStatsByDataset.test) {
                            selectedStats = scoreStatsByDataset.test;
                            datasetLabel = "测试集";
                          } else if (scoreStatsByDataset.train) {
                            selectedStats = scoreStatsByDataset.train;
                            datasetLabel = "训练集";
                          }
                        }
                        
                        return (
                          <>
                            <div className="text-xs text-gray-500">
                              评分区间 <span className="text-[9px] text-gray-400">({datasetLabel})</span>
                            </div>
                            <div className="text-lg font-bold text-indigo-600">
                              {stagesData.score_scaling.output_preview.theoretical_score_range?.min !== undefined 
                                ? `${Math.round(stagesData.score_scaling.output_preview.theoretical_score_range.min)} ~ ${Math.round(stagesData.score_scaling.output_preview.theoretical_score_range.max)}`
                                : stagesData.score_scaling.output_preview.score_range?.min !== undefined
                                ? `${Math.round(stagesData.score_scaling.output_preview.score_range.min)} ~ ${Math.round(stagesData.score_scaling.output_preview.score_range.max)}`
                                : "-"}
                            </div>
                            {/* 实际评分分布统计（小字，一行展示） */}
                            {selectedStats && (
                              <div className="text-[9px] text-gray-400 mt-1">
                                {selectedStats.mean !== undefined && (
                                  <span>均值 {Math.round(selectedStats.mean)}</span>
                                )}
                                {selectedStats.median !== undefined && (
                                  <span className="ml-2">中位数 {Math.round(selectedStats.median)}</span>
                                )}
                                {selectedStats.q25 !== undefined && selectedStats.q75 !== undefined && (
                                  <span className="ml-2">
                                    IQR {Math.round(selectedStats.q25)}~{Math.round(selectedStats.q75)}
                                    <span className="ml-0.5 text-gray-300 cursor-help" title="50%样本评分落在此区间">(?)</span>
                                  </span>
                                )}
                              </div>
                            )}
                          </>
                        );
                      })()}
                    </div>
                    <div className="p-3 bg-slate-50 dark:bg-slate-900/20 rounded-lg border border-slate-200 dark:border-slate-800">
                      <div className="text-xs text-gray-500">基准配置</div>
                      <div className="text-lg font-bold text-slate-600">
                        {stagesData.score_scaling.output_preview.base_score || '-'}/{stagesData.score_scaling.output_preview.base_odds || '-'}/{stagesData.score_scaling.output_preview.pdo || '-'}
                      </div>
                      <div className="text-[10px] text-gray-400">基准分/Odds/PDO</div>
                    </div>
                  </div>
                )}
                
                {/* 好/坏样本均分和分离度（从OOT或测试集获取） */}
                {multiDatasetChartData && (() => {
                  // 按优先级选择数据集：OOT > 测试集 > 训练集
                  const selectedDistData = multiDatasetChartData.oot?.score_distribution || 
                                          multiDatasetChartData.test?.score_distribution || 
                                          multiDatasetChartData.train?.score_distribution;
                  const datasetLabel = multiDatasetChartData.oot?.score_distribution ? 'OOT验证集' :
                                      multiDatasetChartData.test?.score_distribution ? '测试集' : '训练集';
                  const summary = selectedDistData?.summary;
                  
                  if (!summary || (summary.good_mean == null && summary.bad_mean == null)) return null;
                  
                  const goodMean = summary.good_mean;
                  const badMean = summary.bad_mean;
                  const separation = goodMean != null && badMean != null ? Math.abs(goodMean - badMean) : null;
                  
                  return (
                    <div className="grid grid-cols-3 gap-3 mt-3">
                      <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
                        <div className="text-xs text-gray-500">
                          好样本均分 <span className="text-[9px] text-gray-400">({datasetLabel})</span>
                        </div>
                        <div className="text-xl font-bold text-green-600">
                          {goodMean != null ? goodMean.toFixed(1) : '-'}
                        </div>
                      </div>
                      <div className="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
                        <div className="text-xs text-gray-500">
                          坏样本均分 <span className="text-[9px] text-gray-400">({datasetLabel})</span>
                        </div>
                        <div className="text-xl font-bold text-red-600">
                          {badMean != null ? badMean.toFixed(1) : '-'}
                        </div>
                      </div>
                      <div className="p-3 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
                        <div className="text-xs text-gray-500">
                          分离度 <span className="text-[9px] text-gray-400">(好-坏差值)</span>
                        </div>
                        <div className="text-xl font-bold text-amber-600">
                          {separation != null ? separation.toFixed(1) : '-'}
                        </div>
                        <div className="text-[10px] text-gray-400">
                          {separation != null && separation >= 60 ? '★ 优秀' : separation != null && separation >= 40 ? '✓ 良好' : separation != null && separation >= 20 ? '○ 合格' : separation != null ? '△ 偏低' : ''}
                        </div>
                      </div>
                    </div>
                  );
                })()}

                {/* 入模变量评分贡献（条形图） */}
                {stagesData?.score_scaling?.output_preview?.scorecard_preview && 
                 stagesData.score_scaling.output_preview.scorecard_preview.length > 0 && (
                  <div className="p-3 bg-gray-50 dark:bg-gray-900/30 rounded-lg border">
                    <div className="text-xs font-medium text-gray-600 mb-3">📊 入模变量评分贡献</div>
                    <div className="space-y-2">
                      {(() => {
                        const variables = stagesData.score_scaling.output_preview.scorecard_preview
                          .filter((item: any) => item.variable !== 'basepoints')
                          .map((item: any) => ({
                            variable: item.variable,
                            minScore: item.min_score,
                            maxScore: item.max_score,
                            scoreRange: item.score_range || (item.max_score - item.min_score)
                          }))
                          .sort((a: any, b: any) => b.scoreRange - a.scoreRange);
                        
                        const maxRange = Math.max(...variables.map((v: any) => v.scoreRange));
                        
                        return variables.map((item: any, idx: number) => (
                          <div key={idx} className="flex items-center gap-2 text-xs">
                            <div className="w-[140px] truncate font-mono text-gray-600" title={item.variable}>
                              {item.variable}
                            </div>
                            <div className="flex-1 h-4 bg-gray-200 dark:bg-gray-700 rounded overflow-hidden">
                              <div 
                                className="h-full bg-gradient-to-r from-blue-400 to-blue-600 rounded"
                                style={{ width: `${(item.scoreRange / maxRange) * 100}%` }}
                              />
                            </div>
                            <div className="w-[80px] text-right text-gray-500">
                              {item.minScore?.toFixed(0)}~{item.maxScore?.toFixed(0)}
                            </div>
                            <div className="w-[50px] text-right font-medium text-blue-600">
                              {item.scoreRange?.toFixed(0)}分
                            </div>
                          </div>
                        ));
                      })()}
                    </div>
                    <div className="text-[10px] text-gray-400 mt-2">
                      * 波动幅度 = 最高分 - 最低分，反映变量对评分的影响程度
                    </div>
                  </div>
                )}

                {/* 完整评分卡表格 */}
                {stagesData?.score_scaling?.output_preview?.full_scorecard_csv && 
                 stagesData.score_scaling.output_preview.full_scorecard_csv.length > 0 ? (
                  <div className="space-y-2">
                    <div className="text-xs font-medium text-gray-600">
                      📋 完整评分卡 <span className="font-normal text-gray-400">(样本统计基于训练集)</span>
                    </div>
                    <div className="max-h-[280px] overflow-auto rounded-md border">
                      <Table className="text-[10px] table-fixed w-full">
                        <TableHeader>
                          <TableRow className="bg-slate-800 dark:bg-slate-800">
                            <TableHead className="sticky top-0 bg-slate-800 dark:bg-slate-800 text-white font-medium w-[52px] text-center border-r border-slate-700">变量</TableHead>
                            <TableHead className="sticky top-0 bg-slate-800 dark:bg-slate-800 text-white font-medium w-[52px] text-center border-r border-slate-700">IV</TableHead>
                            <TableHead className="sticky top-0 bg-slate-800 dark:bg-slate-800 text-white font-medium w-[52px] text-center border-r border-slate-700">系数</TableHead>
                            <TableHead className="sticky top-0 bg-slate-800 dark:bg-slate-800 text-white font-medium w-[32px] text-center border-r border-slate-700">序号</TableHead>
                            <TableHead className="sticky top-0 bg-slate-800 dark:bg-slate-800 text-white font-medium w-[90px] text-center border-r border-slate-700">分箱</TableHead>
                            <TableHead className="sticky top-0 bg-slate-800 dark:bg-slate-800 text-white font-medium w-[52px] text-center border-r border-slate-700">样本数</TableHead>
                            <TableHead className="sticky top-0 bg-slate-800 dark:bg-slate-800 text-white font-medium w-[52px] text-center border-r border-slate-700">占比</TableHead>
                            <TableHead className="sticky top-0 bg-slate-800 dark:bg-slate-800 text-white font-medium w-[52px] text-center border-r border-slate-700">好样本</TableHead>
                            <TableHead className="sticky top-0 bg-slate-800 dark:bg-slate-800 text-white font-medium w-[52px] text-center border-r border-slate-700">坏样本</TableHead>
                            <TableHead className="sticky top-0 bg-slate-800 dark:bg-slate-800 text-white font-medium w-[48px] text-center border-r border-slate-700">坏率</TableHead>
                            <TableHead className="sticky top-0 bg-slate-800 dark:bg-slate-800 text-white font-medium w-[56px] text-center border-r border-slate-700">WOE</TableHead>
                            <TableHead className="sticky top-0 bg-slate-800 dark:bg-slate-800 text-white font-medium w-[48px] text-center">评分</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {(() => {
                            const rows = stagesData.score_scaling.output_preview.full_scorecard_csv;
                            
                            // 预计算每个变量的行数（用于rowSpan）
                            const variableRowCounts: Record<string, number> = {};
                            rows.forEach((row: any) => {
                              const varName = row.variable || '';
                              variableRowCounts[varName] = (variableRowCounts[varName] || 0) + 1;
                            });
                            
                            // 记录已处理的变量（用于判断是否显示合并单元格）
                            const processedVariables = new Set<string>();
                            
                            return rows.map((row: any, idx: number) => {
                              const isBasepoints = row.variable === '常数项' || row.variable === 'basepoints';
                              const varName = row.variable || '';
                              const isFirstRowOfVariable = !processedVariables.has(varName);
                              const rowSpan = variableRowCounts[varName] || 1;
                              
                              if (isFirstRowOfVariable) {
                                processedVariables.add(varName);
                              }
                              
                              // 解析占比：支持多种格式（小数0.2491、百分比24.91、字符串"24.91%"）
                              const parsePercent = (val: any): string => {
                                if (val === undefined || val === null || val === '') return '-';
                                // 如果是字符串且包含%，直接返回（已经是百分比格式）
                                if (typeof val === 'string') {
                                  if (val.includes('%')) {
                                    return val; // 如"24.91%"直接返回
                                  }
                                  val = parseFloat(val);
                                }
                                if (isNaN(val)) return '-';
                                // 判断：如果值>1则认为是百分比形式，否则是小数形式
                                if (val > 1) {
                                  return `${val.toFixed(2)}%`;
                                } else {
                                  return `${(val * 100).toFixed(2)}%`;
                                }
                              };
                              
                              const countDistr = parsePercent(row.count_distr);
                              const badprob = parsePercent(row.badprob);
                              
                              return (
                                <TableRow 
                                  key={idx} 
                                  className={cn(
                                    "hover:bg-gray-50 dark:hover:bg-gray-800/50",
                                    isBasepoints && "bg-amber-50 dark:bg-amber-900/20"
                                  )}
                                >
                                  {/* 变量名、IV、系数 - 合并单元格 */}
                                  {isFirstRowOfVariable && (
                                    <>
                                      <TableCell 
                                        rowSpan={rowSpan} 
                                        className={cn(
                                          "font-mono py-1 border-r text-center align-middle",
                                          isFirstRowOfVariable && idx > 0 && "border-t-2 border-t-slate-300 dark:border-t-slate-600",
                                          isBasepoints ? "bg-amber-50 dark:bg-amber-900/20" : "bg-slate-50/50 dark:bg-slate-800/30"
                                        )}
                                      >
                                        {isBasepoints ? '常数项' : varName}
                                      </TableCell>
                                      <TableCell 
                                        rowSpan={rowSpan} 
                                        className={cn(
                                          "text-center py-1 text-gray-500 border-r align-middle",
                                          isFirstRowOfVariable && idx > 0 && "border-t-2 border-t-slate-300 dark:border-t-slate-600",
                                          isBasepoints ? "bg-amber-50 dark:bg-amber-900/20" : "bg-slate-50/50 dark:bg-slate-800/30"
                                        )}
                                      >
                                        {row.total_iv !== undefined && row.total_iv !== null && row.total_iv !== '' 
                                          ? Number(row.total_iv).toFixed(4) 
                                          : '-'}
                                      </TableCell>
                                      <TableCell 
                                        rowSpan={rowSpan} 
                                        className={cn(
                                          "text-center py-1 text-gray-500 border-r align-middle",
                                          isFirstRowOfVariable && idx > 0 && "border-t-2 border-t-slate-300 dark:border-t-slate-600",
                                          isBasepoints ? "bg-amber-50 dark:bg-amber-900/20" : "bg-slate-50/50 dark:bg-slate-800/30"
                                        )}
                                      >
                                        {row.cof !== undefined && row.cof !== null && row.cof !== '' 
                                          ? Number(row.cof).toFixed(4) 
                                          : '-'}
                                      </TableCell>
                                    </>
                                  )}
                                  <TableCell className={cn(
                                    "text-center py-1 text-gray-400 border-r",
                                    isFirstRowOfVariable && idx > 0 && "border-t-2 border-t-slate-300 dark:border-t-slate-600"
                                  )}>
                                    {row.index !== undefined && row.index !== null && row.index !== '' ? row.index : '-'}
                                  </TableCell>
                                  <TableCell className={cn(
                                    "py-1 truncate border-r",
                                    isFirstRowOfVariable && idx > 0 && "border-t-2 border-t-slate-300 dark:border-t-slate-600"
                                  )} title={row.bin}>
                                    {row.bin || '-'}
                                  </TableCell>
                                  <TableCell className={cn(
                                    "text-right py-1 border-r",
                                    isFirstRowOfVariable && idx > 0 && "border-t-2 border-t-slate-300 dark:border-t-slate-600"
                                  )}>
                                    {row.count !== undefined ? row.count.toLocaleString() : '-'}
                                  </TableCell>
                                  <TableCell className={cn(
                                    "text-right py-1 text-gray-500 border-r",
                                    isFirstRowOfVariable && idx > 0 && "border-t-2 border-t-slate-300 dark:border-t-slate-600"
                                  )}>
                                    {countDistr}
                                  </TableCell>
                                  <TableCell className={cn(
                                    "text-right py-1 text-green-600 border-r",
                                    isFirstRowOfVariable && idx > 0 && "border-t-2 border-t-slate-300 dark:border-t-slate-600"
                                  )}>
                                    {row.good !== undefined ? row.good.toLocaleString() : '-'}
                                  </TableCell>
                                  <TableCell className={cn(
                                    "text-right py-1 text-red-600 border-r",
                                    isFirstRowOfVariable && idx > 0 && "border-t-2 border-t-slate-300 dark:border-t-slate-600"
                                  )}>
                                    {row.bad !== undefined ? row.bad.toLocaleString() : '-'}
                                  </TableCell>
                                  <TableCell className={cn(
                                    "text-right py-1 border-r",
                                    isFirstRowOfVariable && idx > 0 && "border-t-2 border-t-slate-300 dark:border-t-slate-600"
                                  )}>
                                    {badprob}
                                  </TableCell>
                                  <TableCell className={cn(
                                    "text-right py-1 font-mono border-r",
                                    row.woe > 0 ? "text-red-500" : row.woe < 0 ? "text-green-500" : "",
                                    isFirstRowOfVariable && idx > 0 && "border-t-2 border-t-slate-300 dark:border-t-slate-600"
                                  )}>
                                    {row.woe !== undefined && row.woe !== null && row.woe !== ''
                                      ? Number(row.woe).toFixed(4)
                                      : '-'}
                                  </TableCell>
                                  <TableCell className={cn(
                                    "text-right py-1 font-medium",
                                    row.score > 0 ? "text-green-600" : row.score < 0 ? "text-red-600" : "",
                                    isFirstRowOfVariable && idx > 0 && "border-t-2 border-t-slate-300 dark:border-t-slate-600"
                                  )}>
                                    {row.score !== undefined && row.score !== null
                                      ? Number(row.score).toFixed(2)
                                      : '-'}
                                  </TableCell>
                                </TableRow>
                              );
                            });
                          })()}
                        </TableBody>
                      </Table>
                    </div>
                  </div>
                ) : scorecardData.length > 0 ? (
                  /* 兜底：使用原始scorecardData展示 */
                  <div className="space-y-2">
                    <div className="text-xs font-medium text-gray-600">📋 评分卡明细</div>
                    <div className="max-h-[260px] overflow-auto rounded-md border">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead className="sticky top-0 bg-background text-[10px]">变量</TableHead>
                            <TableHead className="sticky top-0 bg-background text-[10px]">分箱</TableHead>
                            <TableHead className="sticky top-0 bg-background text-[10px] text-right">WOE</TableHead>
                            <TableHead className="sticky top-0 bg-background text-[10px] text-right">分值</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {scorecardData.map((item, idx) => (
                            <TableRow key={idx} className={item.variable === 'basepoints' ? 'bg-amber-50 dark:bg-amber-900/10' : ''}>
                              <TableCell className="font-mono text-[10px] py-1">
                                {item.variable === 'basepoints' ? '基础分' : item.variable}
                              </TableCell>
                              <TableCell className="text-[10px] text-muted-foreground max-w-[150px] truncate py-1">
                                {item.bin}
                              </TableCell>
                              <TableCell className="text-[10px] text-right font-mono py-1">
                                {item.woe.toFixed(4)}
                              </TableCell>
                              <TableCell className="text-[10px] text-right font-medium py-1">
                                {Math.round(item.points)}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-6 text-muted-foreground text-sm">
                    暂无评分卡数据
                  </div>
                )}
              </div>
            </TabsContent>

            {/* 模型系数（原统计检验） */}
            <TabsContent value="statistics" className="mt-3">
              <div className="text-xs text-muted-foreground mb-2">
                逻辑回归模型的系数与统计检验结果，包括标准误、z值、p值等
              </div>
              <ModelStatisticsPanel 
                statistics={(() => {
                  // 优先从 model_training.output_preview 获取数据
                  const modelTrainingPreview = stagesData?.model_training?.output_preview;
                  if (modelTrainingPreview) {
                    const coefficients = modelTrainingPreview.coefficients || [];
                    const modelFit = modelTrainingPreview.model_fit || {};
                    const intercept = modelTrainingPreview.intercept;
                    
                    // 如果有系数数据，构建 ModelStatistics 格式
                    if (coefficients.length > 0) {
                      // 构建特征系数列表
                      const featureSummary = coefficients.map((c: any) => ({
                        feature: c.feature || '',
                        coef: c.coefficient || 0,
                        std_err: c.std_err || 0,
                        z: c.std_err ? (c.coefficient / c.std_err) : 0,
                        // 确保 p_value 是数字类型（后端可能返回 p_value 或 pvalue）
                        p_value: c.p_value != null ? Number(c.p_value) : (c.pvalue != null ? Number(c.pvalue) : null),
                        ci_lower: c.ci_lower != null ? Number(c.ci_lower) : null,
                        ci_upper: c.ci_upper != null ? Number(c.ci_upper) : null,
                      }));
                      
                      // 如果有截距项，添加到 summary 开头（行业标准：const 作为第一行）
                      const summaryWithIntercept = intercept != null ? [
                        {
                          feature: 'const',
                          coef: intercept,
                          std_err: modelFit.intercept_std_err ?? null,
                          z: modelFit.intercept_std_err ? (intercept / modelFit.intercept_std_err) : null,
                          p_value: modelFit.intercept_pvalue ?? null,
                          ci_lower: modelFit.intercept_ci_lower ?? null,
                          ci_upper: modelFit.intercept_ci_upper ?? null,
                        },
                        ...featureSummary
                      ] : featureSummary;
                      
                      return {
                        summary: summaryWithIntercept,
                        n_observations: modelFit.n_observations || 0,
                        pseudo_r2: modelFit.pseudo_r2 || 0,
                        log_likelihood: modelFit.log_likelihood || 0,
                        aic: modelFit.aic,
                        bic: modelFit.bic,
                        lr_pvalue: modelFit.lr_pvalue,
                        // 额外传递截距项值，用于指标卡显示
                        intercept: intercept,
                      };
                    }
                  }
                  // 兜底：使用 result.outputs.model_statistics
                  return result?.outputs?.model_statistics?.data || null;
                })()}
                coefficientValidation={stagesData?.model_training?.output_preview?.coefficient_validation || null}
              />
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </TooltipProvider>
  );
}

// ========== 变量筛选漏斗概览组件（参考规则挖掘设计） ==========
interface FeatureSelectionFunnelProps {
  stagesData: Record<string, StageProgress>;
  modelVariablesCount: number;
}

function FeatureSelectionFunnel({ stagesData, modelVariablesCount }: FeatureSelectionFunnelProps) {
  // 从各阶段获取特征数量
  const dataLoadingPreview = stagesData?.data_loading?.output_preview || {};
  const woeBinningPreview = stagesData?.woe_binning?.output_preview || {};
  const featureSelectionPreview = stagesData?.feature_selection?.output_preview || {};
  const modelTrainingPreview = stagesData?.model_training?.output_preview || {};
  
  // ========== 根据实际数据结构修正逻辑 ==========
  // var_filter_result 包含：input_features(原始)、output_features(筛选后)、removed_features(被移除的)
  const varFilterResult = dataLoadingPreview.var_filter_result || {};
  
  // 阶段1: 原始特征数（var_filter 输入，即数据加载后、质量筛选前）
  // 优先级：var_filter_result.input_features > feature_count（后者是筛选后的）
  const originalCount = varFilterResult.input_features || dataLoadingPreview.feature_count || 0;
  
  // 阶段2: 数据质量筛选后（var_filter 输出）
  const varFilterRemovedCount = varFilterResult.removed_features?.length || 0;
  const afterVarFilterCount = varFilterResult.output_features || (originalCount - varFilterRemovedCount) || dataLoadingPreview.feature_count || 0;
  
  // 阶段3: WOE分箱后（woe_filtered 过滤常量列/全NaN等）
  // input_features: WOE分箱输入（=afterVarFilterCount）
  // total_features: WOE分箱成功的特征数
  const woeInputCount = woeBinningPreview.input_features || afterVarFilterCount;
  const woeOutputCount = woeBinningPreview.total_features || 0;
  const woeFiltered = woeBinningPreview.woe_filtered || {};
  const woeFilteredCount = woeFiltered.count || (woeInputCount - woeOutputCount);
  
  // 阶段4: 特征筛选后（IV/相关性/VIF）
  const feBeforeCount = featureSelectionPreview.before_count || woeOutputCount;
  const feAfterCount = featureSelectionPreview.after_count || featureSelectionPreview.selected_count || 0;
  
  // 阶段5: 模型训练后（逐步回归/显著性/系数方向）
  const stepwiseResult = modelTrainingPreview.stepwise_result || {};
  const coeffValidation = modelTrainingPreview.coefficient_validation || {};
  // stepwise_result.before_count 是进入逐步回归前的特征数，应该等于 feAfterCount
  const stepwiseBeforeCount = stepwiseResult.before_count || feAfterCount;
  // 计算模型训练阶段移除的特征数：使用 before_count - after_count 更准确
  const stepwiseAfterCount = stepwiseResult.after_count || 0;
  const removedByStepwise = stepwiseBeforeCount > stepwiseAfterCount ? (stepwiseBeforeCount - stepwiseAfterCount) : (stepwiseResult.removed_features?.length || 0);
  const removedByCoef = coeffValidation.removed_features?.length || 0;
  const modelTrainingRemoved = removedByStepwise + removedByCoef;
  const finalCount = modelVariablesCount || stepwiseAfterCount || modelTrainingPreview.final_features_count || 0;
  
  // 如果没有数据，不显示
  if (!originalCount && !woeOutputCount && !feAfterCount && !finalCount) {
    return null;
  }
  
  // ========== 精简后的5阶段漏斗（与规则挖掘一致：只显示标签、数值、百分比） ==========
  const funnelSteps = [
    {
      label: "原始特征",
      count: originalCount,
      percent: 100,
      color: "text-gray-900 dark:text-gray-100",
      bgColor: "bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600",
    },
    {
      label: "质量筛选",
      count: afterVarFilterCount || woeInputCount,
      percent: originalCount > 0 ? ((afterVarFilterCount || woeInputCount) / originalCount * 100) : 0,
      color: "text-orange-600",
      bgColor: "bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-800",
    },
    {
      label: "WOE分箱",
      count: woeOutputCount,
      percent: originalCount > 0 ? (woeOutputCount / originalCount * 100) : 0,
      color: "text-blue-600",
      bgColor: "bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800",
    },
    {
      label: "IV/相关/VIF",
      count: feAfterCount,
      percent: originalCount > 0 ? (feAfterCount / originalCount * 100) : 0,
      color: "text-purple-600",
      bgColor: "bg-purple-50 dark:bg-purple-900/20 border-purple-200 dark:border-purple-800",
    },
    {
      label: "最终入模",
      count: finalCount,
      percent: originalCount > 0 ? (finalCount / originalCount * 100) : 0,
      color: "text-green-600",
      bgColor: "bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800",
    },
  ];
  
  return (
    <div className="border rounded-lg p-4 bg-gray-50 dark:bg-gray-900/50">
      <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
        <GitBranch className="h-4 w-4 text-blue-600" />
        漏斗概览
      </h4>
      <div className="flex items-center justify-center gap-1 overflow-x-auto pb-2">
        {funnelSteps.map((step, index) => (
          <React.Fragment key={step.label}>
            {index > 0 && <ChevronRight className="h-4 w-4 text-gray-400 flex-shrink-0" />}
            <div className={cn(
              "flex flex-col items-center p-2 rounded-lg border min-w-[80px] w-[80px] flex-shrink-0",
              step.bgColor
            )}>
              <span className="text-[10px] text-gray-500 mb-0.5 whitespace-nowrap">{step.label}</span>
              <span className={cn("text-base font-bold", step.color)}>
                {step.count || "-"}
              </span>
              <span className="text-[10px] text-gray-400">
                {step.percent > 0 ? `${step.percent.toFixed(0)}%` : "-"}
              </span>
            </div>
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}

// ========== 样本与特征面板（评分卡任务专用） ==========
interface SampleDataPanelProps {
  stagesData: Record<string, StageProgress>;
}

function SampleDataPanel({ stagesData }: SampleDataPanelProps) {
  // 获取data_loading阶段数据（评分卡任务的数据加载阶段）
  const dataLoadingPreview = stagesData?.data_loading?.output_preview || {};
  
  // 时间范围信息
  const timeRangeInfo = dataLoadingPreview.time_range_info;
  
  // 异常值特征数：从data_loading阶段获取
  const outlierCount = dataLoadingPreview.outlier_count;
  
  return (
    <div className="space-y-4">
      {/* 样本概览 */}
      <div>
        <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
          <Database className="h-4 w-4 text-blue-600" />
          样本概览
        </h4>
        <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="space-y-2 text-sm">
            <div className="flex justify-between items-center py-1 border-b border-gray-200 dark:border-gray-700">
              <span className="text-gray-600 dark:text-gray-400">总样本数</span>
              <span className="font-medium">{dataLoadingPreview.rows?.toLocaleString() || "-"}</span>
            </div>
            <div className="flex justify-between items-center py-1 border-b border-gray-200 dark:border-gray-700">
              <span className="text-gray-600 dark:text-gray-400">总体坏账率</span>
              <span className="font-medium text-purple-600">
                {dataLoadingPreview.target_rate ? `${(dataLoadingPreview.target_rate * 100).toFixed(2)}%` : "-"}
              </span>
            </div>
            {dataLoadingPreview.split_info && (
              <>
                <div className="flex justify-between items-center py-1 border-b border-gray-200 dark:border-gray-700">
                  <span className="text-gray-600 dark:text-gray-400">训练集</span>
                  <span className="font-medium">
                    {dataLoadingPreview.split_info.train?.toLocaleString() || "-"}
                    <span className="text-xs text-gray-500 ml-2">
                      (坏账率: {dataLoadingPreview.split_info.train_target_rate 
                        ? `${(dataLoadingPreview.split_info.train_target_rate * 100).toFixed(2)}%`
                        : "-"})
                    </span>
                  </span>
                </div>
                <div className="flex justify-between items-center py-1 border-b border-gray-200 dark:border-gray-700">
                  <span className="text-gray-600 dark:text-gray-400">测试集</span>
                  <span className="font-medium">
                    {dataLoadingPreview.split_info.test?.toLocaleString() || "-"}
                    <span className="text-xs text-gray-500 ml-2">
                      (坏账率: {dataLoadingPreview.split_info.test_target_rate 
                        ? `${(dataLoadingPreview.split_info.test_target_rate * 100).toFixed(2)}%`
                        : "-"})
                    </span>
                  </span>
                </div>
                {/* OOT验证集始终显示（即使未划分，显示为-） */}
                <div className="flex justify-between items-center py-1">
                  <span className="text-gray-600 dark:text-gray-400">OOT验证集</span>
                  <span className="font-medium">
                    {dataLoadingPreview.split_info.oot > 0 
                      ? dataLoadingPreview.split_info.oot?.toLocaleString() 
                      : <span className="text-muted-foreground">未划分</span>}
                    {dataLoadingPreview.split_info.oot > 0 && (
                      <span className="text-xs text-gray-500 ml-2">
                        (坏账率: {dataLoadingPreview.split_info.oot_target_rate 
                          ? `${(dataLoadingPreview.split_info.oot_target_rate * 100).toFixed(2)}%`
                          : "-"})
                      </span>
                    )}
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
        <div className="grid grid-cols-3 gap-2">
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
          {/* OOT验证集时间范围 */}
          <div className="text-center p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg border border-purple-200 dark:border-purple-800">
            <div className="text-xs text-gray-500 mb-1">OOT验证集</div>
            {timeRangeInfo?.oot ? (
              <>
                <div className="text-sm font-medium text-purple-600">{timeRangeInfo.oot.min}</div>
                <div className="text-gray-400 text-xs">至</div>
                <div className="text-sm font-medium text-purple-600">{timeRangeInfo.oot.max}</div>
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
              {/* 原始特征数：优先使用var_filter_result.input_features（筛选前），否则使用columns（总列数减去非特征列） */}
              {dataLoadingPreview.var_filter_result?.input_features || dataLoadingPreview.columns || "-"}
            </div>
            <div className="text-xs text-gray-500">原始特征数</div>
          </div>
          <div className="p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg border border-yellow-200 dark:border-yellow-800">
            <div className="text-2xl font-bold text-yellow-600">
              {outlierCount ?? "-"}
            </div>
            <div className="text-xs text-gray-500">异常值特征数</div>
          </div>
          <div className="p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg border border-yellow-200 dark:border-yellow-800">
            <div className="text-2xl font-bold text-yellow-600">
              {dataLoadingPreview.missing_rate !== undefined 
                ? `${(dataLoadingPreview.missing_rate * 100).toFixed(1)}%` 
                : "-"}
            </div>
            <div className="text-xs text-gray-500">平均缺失率</div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ScorecardResults;
