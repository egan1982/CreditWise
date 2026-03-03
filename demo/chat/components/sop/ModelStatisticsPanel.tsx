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
import { Activity, BarChart3, Calculator, Info, Users, CheckCircle2, ChevronDown, ChevronRight } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";

// TypeScript interfaces
interface CoefficientSummary {
  feature: string;
  coef: number;
  std_err: number;
  z: number;
  p_value: number;
  ci_lower: number;
  ci_upper: number;
  significance?: string;
}

interface ModelStatistics {
  summary: CoefficientSummary[];
  n_observations: number;
  n_features?: number;
  n_params?: number;
  log_likelihood: number;
  null_log_likelihood?: number;
  pseudo_r2: number;
  aic?: number;
  bic?: number;
  lr_stat?: number;
  lr_pvalue?: number;
  intercept?: number;  // 额外传递的截距项值
}

// 系数方向验证数据结构
interface CoefficientValidation {
  valid_direction?: string[];
  invalid_direction?: string[];
  removed_features?: string[];
}

interface ModelStatisticsPanelProps {
  statistics: ModelStatistics | null;
  coefficientValidation?: CoefficientValidation | null;  // 系数方向验证数据
  className?: string;
}

// Get significance marker based on p-value
function getSignificanceMarker(pValue: number | null | undefined): string {
  if (pValue === null || pValue === undefined || isNaN(pValue)) return "";
  if (pValue < 0.001) return "***";
  if (pValue < 0.01) return "**";
  if (pValue < 0.05) return "*";
  if (pValue < 0.1) return ".";
  return "";
}

// Get significance color class
function getSignificanceColor(pValue: number | null | undefined): string {
  if (pValue === null || pValue === undefined || isNaN(pValue)) return "";
  if (pValue < 0.001) return "text-green-600 font-bold";
  if (pValue < 0.01) return "text-green-500 font-semibold";
  if (pValue < 0.05) return "text-yellow-600";
  if (pValue < 0.1) return "text-orange-500";
  return "text-gray-400";
}

// Format number with precision
function formatNumber(value: number | null | undefined, precision: number = 4): string {
  if (value === null || value === undefined || isNaN(value)) return "N/A";
  return value.toFixed(precision);
}

// Format p-value
function formatPValue(value: number | null | undefined): string {
  if (value === null || value === undefined || isNaN(value)) return "N/A";
  if (value < 0.001) return "<0.001";
  return value.toFixed(4);
}

export function ModelStatisticsPanel({ statistics, coefficientValidation, className }: ModelStatisticsPanelProps) {
  const [showFitMetrics, setShowFitMetrics] = React.useState(false);

  if (!statistics) {
    return (
      <Card className={cn("w-full", className)}>
        <CardContent className="pt-6">
          <p className="text-center text-muted-foreground">
            模型统计信息不可用
          </p>
        </CardContent>
      </Card>
    );
  }

  // 过滤掉 const，只保留实际变量
  const featureSummary = statistics.summary?.filter(row => row.feature !== 'const') || [];
  
  // 计算显著变量数（p<0.05）- 确保 p_value 是数字类型
  const significantCount = featureSummary.filter(
    row => {
      const pValue = row.p_value != null ? Number(row.p_value) : null;
      return pValue != null && !isNaN(pValue) && pValue < 0.05;
    }
  ).length || 0;
  
  // 入模变量数
  const featureCount = featureSummary.length || 0;
  
  // 获取截距项：优先从 summary 中找，其次从 statistics.intercept 获取
  const interceptRow = statistics.summary?.find(row => row.feature === 'const');
  const interceptValue = interceptRow?.coef ?? statistics.intercept ?? null;
  
  // 系数方向验证数据
  const validDirectionCount = coefficientValidation?.valid_direction?.length || 0;
  const invalidDirectionCount = coefficientValidation?.invalid_direction?.length || 0;
  const totalDirectionChecked = validDirectionCount + invalidDirectionCount;

  return (
    <div className={cn("space-y-4", className)}>
      {/* 核心指标卡片 - 2026-02-11: 将入模变量替换为似然比检验，评估模型整体显著性 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {/* 1. 似然比检验 (LR Test) - 模型整体显著性 */}
        <Card className={statistics.lr_pvalue !== undefined && statistics.lr_pvalue !== null && statistics.lr_pvalue < 0.05 ? "bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800" : "bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800"}>
          <CardContent className="pt-4 pb-3">
            <div className="flex items-center gap-2 text-xs mb-1">
              <Activity className="h-3 w-3" />
              <span className={statistics.lr_pvalue !== undefined && statistics.lr_pvalue !== null && statistics.lr_pvalue < 0.05 ? "text-green-600" : "text-yellow-600"}>
                似然比检验
              </span>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger>
                    <Info className="h-3 w-3 text-muted-foreground" />
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>模型整体显著性检验</p>
                    <p>P值 &lt; 0.05 表示模型整体有效</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
            <div className="text-xl font-bold">
              {statistics.lr_pvalue !== undefined && statistics.lr_pvalue !== null ? (
                <span className={statistics.lr_pvalue < 0.05 ? "text-green-600" : "text-yellow-600"}>
                  {statistics.lr_pvalue < 0.001 ? "<0.001" : statistics.lr_pvalue.toFixed(4)}
                </span>
              ) : (
                "-"
              )}
              <span className="text-sm font-normal text-muted-foreground ml-1">
                {statistics.lr_pvalue !== undefined && statistics.lr_pvalue !== null ? (statistics.lr_pvalue < 0.05 ? "✓ 显著" : "不显著") : ""}
              </span>
            </div>
          </CardContent>
        </Card>
        
        {/* 2. 显著变量 - 与阶段结果设计一致 */}
        <Card className={significantCount === featureCount && featureCount > 0 ? "bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800" : "bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800"}>
          <CardContent className="pt-4 pb-3">
            <div className="flex items-center gap-2 text-xs mb-1">
              <CheckCircle2 className={significantCount === featureCount && featureCount > 0 ? "h-3 w-3 text-green-600" : "h-3 w-3 text-yellow-600"} />
              <span className={significantCount === featureCount && featureCount > 0 ? "text-green-600" : "text-yellow-600"}>
                显著变量
              </span>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger>
                    <Info className="h-3 w-3 text-muted-foreground" />
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>P值 &lt; 0.05 的变量数量</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
            <div className="text-xl font-bold">
              <span className={significantCount === featureCount && featureCount > 0 ? "text-green-600" : "text-yellow-600"}>
                {significantCount}
              </span>
              <span className="text-sm text-gray-400">/{featureCount}</span>
            </div>
            <div className={`text-xs font-normal mt-0.5 ${significantCount === featureCount && featureCount > 0 ? 'text-green-600' : 'text-yellow-600'}`}>
              {significantCount === featureCount && featureCount > 0 ? '全部显著' : `${featureCount - significantCount}个不显著`}
            </div>
          </CardContent>
        </Card>
        
        {/* 3. 系数方向验证 - 与阶段结果设计一致 */}
        <Card className={invalidDirectionCount === 0 && totalDirectionChecked > 0 ? "bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800" : invalidDirectionCount > 0 ? "bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800" : "bg-gray-50 dark:bg-gray-900/20 border-gray-200 dark:border-gray-800"}>
          <CardContent className="pt-4 pb-3">
            <div className="flex items-center gap-2 text-xs mb-1">
              {totalDirectionChecked > 0 && invalidDirectionCount === 0 ? (
                <CheckCircle2 className="h-3 w-3 text-green-600" />
              ) : invalidDirectionCount > 0 ? (
                <Info className="h-3 w-3 text-red-600" />
              ) : (
                <Info className="h-3 w-3 text-gray-400" />
              )}
              <span className={totalDirectionChecked > 0 && invalidDirectionCount === 0 ? "text-green-600" : invalidDirectionCount > 0 ? "text-red-600" : "text-gray-500"}>
                系数方向
              </span>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger>
                    <Info className="h-3 w-3 text-muted-foreground" />
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>验证系数符号是否符合业务预期</p>
                    {coefficientValidation?.invalid_direction && coefficientValidation.invalid_direction.length > 0 && (
                      <p className="text-red-500">异常: {coefficientValidation.invalid_direction.join(', ')}</p>
                    )}
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
            {totalDirectionChecked > 0 ? (
              <>
                <div className="text-xl font-bold">
                  <span className={invalidDirectionCount === 0 ? "text-green-600" : "text-red-600"}>
                    {validDirectionCount}
                  </span>
                  <span className="text-sm text-gray-400">/{totalDirectionChecked}</span>
                </div>
                <div className={`text-xs font-normal mt-0.5 ${invalidDirectionCount === 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {invalidDirectionCount === 0 ? '全部正确' : `${invalidDirectionCount}个异常`}
                </div>
              </>
            ) : (
              <>
                <div className="text-xl font-bold text-gray-400">-</div>
                <div className="text-xs text-gray-400 font-normal mt-0.5">未验证</div>
              </>
            )}
          </CardContent>
        </Card>
        
        {/* 4. 截距项 */}
        <Card>
          <CardContent className="pt-4 pb-3">
            <div className="flex items-center gap-2 text-muted-foreground text-xs mb-1">
              <Calculator className="h-3 w-3" />
              截距项
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger>
                    <Info className="h-3 w-3" />
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>模型基准对数几率 (β₀)</p>
                    <p>转换为评分卡的基础分</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
            <div className="text-xl font-bold text-purple-600">
              {interceptValue != null ? formatNumber(interceptValue) : "N/A"}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 模型拟合指标 - 可折叠区域 */}
      {(statistics.pseudo_r2 != null || statistics.aic != null || statistics.log_likelihood != null) && (
        <Collapsible open={showFitMetrics} onOpenChange={setShowFitMetrics}>
          <CollapsibleTrigger asChild>
            <div className="flex items-center gap-2 text-sm text-muted-foreground cursor-pointer hover:text-foreground transition-colors py-2 px-1">
              {showFitMetrics ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
              <BarChart3 className="h-4 w-4" />
              <span>模型拟合指标</span>
              <span className="text-xs">(点击展开)</span>
            </div>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-2 pb-2 px-1 bg-muted/30 rounded-lg">
              <TooltipProvider>
                <div className="text-center p-2">
                  <div className="text-xs text-muted-foreground mb-1 flex items-center justify-center gap-1">
                    伪R²
                    <Tooltip>
                      <TooltipTrigger>
                        <Info className="h-3 w-3" />
                      </TooltipTrigger>
                      <TooltipContent className="max-w-[280px]">
                        <p className="font-medium">McFadden伪R² (Pseudo R-squared)</p>
                        <p className="text-xs mt-1">衡量模型拟合优度，值越接近1表示拟合越好</p>
                        <p className="text-xs mt-1 text-muted-foreground">评分卡模型通常在0.05-0.2之间</p>
                        <p className="text-xs mt-1.5 pt-1.5 border-t border-border/50 text-blue-400">📊 适用场景：快速评估单个模型的整体解释能力</p>
                      </TooltipContent>
                    </Tooltip>
                  </div>
                  <div className="font-mono font-medium">{formatNumber(statistics.pseudo_r2)}</div>
                </div>
              </TooltipProvider>
              <TooltipProvider>
                <div className="text-center p-2">
                  <div className="text-xs text-muted-foreground mb-1 flex items-center justify-center gap-1">
                    对数似然
                    <Tooltip>
                      <TooltipTrigger>
                        <Info className="h-3 w-3" />
                      </TooltipTrigger>
                      <TooltipContent className="max-w-[280px]">
                        <p className="font-medium">对数似然 (Log-Likelihood)</p>
                        <p className="text-xs mt-1">模型在给定数据下的似然对数值</p>
                        <p className="text-xs mt-1 text-muted-foreground">值越大（越接近0）表示模型拟合越好</p>
                        <p className="text-xs mt-1.5 pt-1.5 border-t border-border/50 text-blue-400">📊 适用场景：作为基础量用于计算AIC/BIC等信息准则</p>
                      </TooltipContent>
                    </Tooltip>
                  </div>
                  <div className="font-mono font-medium">{formatNumber(statistics.log_likelihood, 2)}</div>
                </div>
              </TooltipProvider>
              <TooltipProvider>
                <div className="text-center p-2">
                  <div className="text-xs text-muted-foreground mb-1 flex items-center justify-center gap-1">
                    AIC
                    <Tooltip>
                      <TooltipTrigger>
                        <Info className="h-3 w-3" />
                      </TooltipTrigger>
                      <TooltipContent className="max-w-[280px]">
                        <p className="font-medium">赤池信息准则 (Akaike Information Criterion)</p>
                        <p className="text-xs mt-1">衡量模型拟合优度与复杂度的平衡</p>
                        <p className="text-xs mt-1 text-muted-foreground">值越小表示模型越好</p>
                        <p className="text-xs mt-1.5 pt-1.5 border-t border-border/50 text-blue-400">📊 适用场景：多个候选模型对比时，选择AIC最小的模型</p>
                      </TooltipContent>
                    </Tooltip>
                  </div>
                  <div className="font-mono font-medium">{formatNumber(statistics.aic, 1)}</div>
                </div>
              </TooltipProvider>
              <TooltipProvider>
                <div className="text-center p-2">
                  <div className="text-xs text-muted-foreground mb-1 flex items-center justify-center gap-1">
                    BIC
                    <Tooltip>
                      <TooltipTrigger>
                        <Info className="h-3 w-3" />
                      </TooltipTrigger>
                      <TooltipContent className="max-w-[280px]">
                        <p className="font-medium">贝叶斯信息准则 (Bayesian Information Criterion)</p>
                        <p className="text-xs mt-1">类似AIC，但对参数数量惩罚更重</p>
                        <p className="text-xs mt-1 text-muted-foreground">值越小表示模型越好，倾向选择更简洁的模型</p>
                        <p className="text-xs mt-1.5 pt-1.5 border-t border-border/50 text-blue-400">📊 适用场景：大样本下多模型对比，比AIC更倾向简单模型</p>
                      </TooltipContent>
                    </Tooltip>
                  </div>
                  <div className="font-mono font-medium">{formatNumber(statistics.bic, 1)}</div>
                </div>
              </TooltipProvider>
            </div>
          </CollapsibleContent>
        </Collapsible>
      )}

      {/* Coefficient Statistics Table - 只显示实际变量（不含const） */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            系数统计
            <Badge variant="outline" className="text-xs font-normal">
              {featureCount} 个变量
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[150px]">变量</TableHead>
                  <TableHead className="text-right">系数</TableHead>
                  <TableHead className="text-right">标准误</TableHead>
                  <TableHead className="text-right">z值</TableHead>
                  <TableHead className="text-right">p值</TableHead>
                  <TableHead className="text-right">95% CI</TableHead>
                  <TableHead className="text-center w-[60px]">显著性</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {featureSummary.map((row, index) => (
                  <TableRow key={index}>
                    <TableCell className="font-medium">
                      {row.feature?.replace('_woe', '') || `var_${index}`}
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {formatNumber(row.coef)}
                    </TableCell>
                    <TableCell className="text-right font-mono text-muted-foreground">
                      {formatNumber(row.std_err)}
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {formatNumber(row.z, 2)}
                    </TableCell>
                    <TableCell className={cn("text-right font-mono", getSignificanceColor(row.p_value))}>
                      {formatPValue(row.p_value)}
                    </TableCell>
                    <TableCell className="text-right font-mono text-muted-foreground text-xs">
                      [{formatNumber(row.ci_lower, 3)}, {formatNumber(row.ci_upper, 3)}]
                    </TableCell>
                    <TableCell className="text-center">
                      <span className={cn("font-bold", getSignificanceColor(row.p_value))}>
                        {row.significance || getSignificanceMarker(row.p_value)}
                      </span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          
          {/* Significance Legend */}
          <div className="mt-3 text-xs text-muted-foreground">
            显著性标记: <span className="text-green-600 font-bold">***</span> p&lt;0.001, 
            <span className="text-green-500 font-semibold ml-2">**</span> p&lt;0.01, 
            <span className="text-yellow-600 ml-2">*</span> p&lt;0.05, 
            <span className="text-orange-500 ml-2">.</span> p&lt;0.1
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default ModelStatisticsPanel;
