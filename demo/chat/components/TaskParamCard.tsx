"use client";

import React, { useState, useCallback, useEffect, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { Badge } from "@/components/ui/badge";
import { HelpCircle, X, Check, ChevronsUpDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { Combobox, ComboboxOption } from "@/components/ui/combobox";
import {
  Play,
  Edit,
  CheckCircle,
  AlertCircle,
  FileSpreadsheet,
  Target,
  Settings,
  Settings2,
  Loader2,
  Zap,
  BarChart3,
  Database,
  GitBranch,
  Layers,
  Search,
  TrendingUp,
  PieChart,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { getApiUrl } from "@/lib/config";
import { shouldShowParam } from "./sop/DynamicParamRenderer";

// =============================================================================
// 类型定义
// =============================================================================

export interface TaskParamResult {
  task_type: string | null;
  confidence: number;
  params: Record<string, any>;
  missing_params: string[];
  clarification_needed: boolean;
  clarification_question: string;
}

export interface TaskParamCardProps {
  /** LLM返回的参数提取结果 */
  paramResult: TaskParamResult;
  /** 确认执行回调 */
  onConfirm: (params: Record<string, any>, mode: "auto" | "expert") => void;
  /** 修改参数回调（可选，用于对话式修改） */
  onModify?: () => void;
  /** 是否正在执行 */
  isExecuting?: boolean;
  /** 是否已确认（用于历史消息显示） */
  isConfirmed?: boolean;
  /** 会话ID（用于获取数据列等） */
  sessionId?: string;
}

// 任务元数据缓存
interface ParamMeta {
  name: string;
  label: string;
  type: string;
  required?: boolean;
  default?: any;
  description?: string;
  options?: Array<{ value: any; label: string }>;
  allow_custom?: boolean;
  allow_empty?: boolean;
  min?: number;
  max?: number;
  step?: number;
  group?: string;  // 参数分组标识，同组参数将在一行显示
  stage?: string;  // 参数所属阶段ID，用于按阶段分组展示
  advanced?: boolean;  // 是否为调优参数，在阶段内二级折叠显示
}

interface TaskStage {
  id: string;
  name: string;
  progress_weight: number;
}

interface TaskMeta {
  task_id: string;
  task_name: string;
  task_name_en: string;
  description: string;
  category: string;
  icon: string;
  stages?: TaskStage[];  // 任务阶段定义
  required_params: ParamMeta[];
  optional_params: ParamMeta[];
}

// 数据列信息
interface DataColumn {
  name: string;
  dtype: string;
}

// =============================================================================
// 图标映射（根据任务图标字符串或类别选择图标）
// =============================================================================

const ICON_MAP: Record<string, React.ReactNode> = {
  "⚙️": <Settings className="h-5 w-5" />,
  "📊": <FileSpreadsheet className="h-5 w-5" />,
  "📈": <TrendingUp className="h-5 w-5" />,
  "🔍": <Search className="h-5 w-5" />,
  "⚡": <Zap className="h-5 w-5" />,
  "📉": <BarChart3 className="h-5 w-5" />,
  "🗄️": <Database className="h-5 w-5" />,
  "🌳": <GitBranch className="h-5 w-5" />,
  "📋": <Layers className="h-5 w-5" />,
  "🎯": <Target className="h-5 w-5" />,
  "🥧": <PieChart className="h-5 w-5" />,
};

// 类别颜色映射
const CATEGORY_COLORS: Record<string, string> = {
  "风控建模": "text-blue-600 dark:text-blue-400",
  "数据分析": "text-green-600 dark:text-green-400",
  "特征工程": "text-purple-600 dark:text-purple-400",
  "模型评估": "text-orange-600 dark:text-orange-400",
  "数据处理": "text-cyan-600 dark:text-cyan-400",
};

// =============================================================================
// 默认参数标签映射（作为后备）
// =============================================================================

const DEFAULT_PARAM_LABELS: Record<string, string> = {
  data_file: "数据文件",
  file_path: "数据文件",
  target: "目标变量",
  target_col: "目标变量",
  base_score: "基准分",
  pdo: "PDO",
  iv_threshold: "IV阈值",
  bin_count: "分箱数量",
  force_categorical: "强制分类变量",
  feature_cols: "特征变量",
  min_samples_leaf: "叶节点最小样本数",
  max_depth: "最大深度",
  min_iv: "最小IV值",
  max_rules: "最大规则数",
  n_vars: "变量数量",
  mining_mode: "挖掘模式",
  enable_feature_engineering: "启用特征工程",
  missing_threshold: "缺失阈值",
  correlation_threshold: "相关性阈值",
};

// =============================================================================
// 任务元数据缓存
// =============================================================================

const taskMetaCache: Map<string, TaskMeta> = new Map();

async function fetchTaskMeta(taskId: string): Promise<TaskMeta | null> {
  // 检查缓存
  if (taskMetaCache.has(taskId)) {
    return taskMetaCache.get(taskId)!;
  }

  try {
    const response = await fetch(getApiUrl(`/sop/tasks/${taskId}`));
    if (response.ok) {
      const meta = await response.json();
      taskMetaCache.set(taskId, meta);
      return meta;
    }
  } catch (error) {
    console.warn(`Failed to fetch task meta for ${taskId}:`, error);
  }
  return null;
}

// 数据列缓存
const dataColumnsCache: Map<string, DataColumn[]> = new Map();

async function fetchDataColumns(dataFile: string, sessionId: string = "default"): Promise<DataColumn[]> {
  if (!dataFile) return [];
  
  // 缓存key包含sessionId
  const cacheKey = `${sessionId}:${dataFile}`;
  
  // 检查缓存
  if (dataColumnsCache.has(cacheKey)) {
    return dataColumnsCache.get(cacheKey)!;
  }

  try {
    const response = await fetch(getApiUrl(`/workspace/data-columns?file_path=${encodeURIComponent(dataFile)}&session_id=${encodeURIComponent(sessionId)}`));
    if (response.ok) {
      const columns: DataColumn[] = await response.json();
      dataColumnsCache.set(cacheKey, columns);
      return columns;
    }
  } catch (error) {
    console.warn(`Failed to fetch data columns for ${dataFile}:`, error);
  }
  return [];
}

// =============================================================================
// 辅助函数
// =============================================================================

/**
 * 检测内容是否为任务参数JSON
 */
/**
 * 尝试修复截断的 JSON 字符串
 * 针对 Gemini 等模型可能返回不完整 JSON 的情况
 */
function tryRepairTruncatedJson(jsonStr: string): string | null {
  // 如果已经是完整的 JSON，直接返回
  try {
    JSON.parse(jsonStr);
    return jsonStr;
  } catch {
    // 继续尝试修复
  }

  // 检查是否包含 task_type（任务参数 JSON 的标志）
  if (!jsonStr.includes('"task_type"')) {
    return null;
  }

  let repaired = jsonStr.trim();

  // 移除末尾不完整的键名（如 "missing 或 "clarification_）
  repaired = repaired.replace(/,\s*"[a-z_]*$/i, '');
  
  // 计算未闭合的括号
  let braceCount = 0;
  let bracketCount = 0;
  let inString = false;
  let escapeNext = false;

  for (const char of repaired) {
    if (escapeNext) {
      escapeNext = false;
      continue;
    }
    if (char === '\\') {
      escapeNext = true;
      continue;
    }
    if (char === '"') {
      inString = !inString;
      continue;
    }
    if (inString) continue;

    if (char === '{') braceCount++;
    if (char === '}') braceCount--;
    if (char === '[') bracketCount++;
    if (char === ']') bracketCount--;
  }

  // 如果在字符串中间截断，先闭合字符串
  if (inString) {
    repaired += '"';
  }

  // 闭合未闭合的括号
  while (bracketCount > 0) {
    repaired += ']';
    bracketCount--;
  }
  while (braceCount > 0) {
    repaired += '}';
    braceCount--;
  }

  // 验证修复后的 JSON
  try {
    JSON.parse(repaired);
    return repaired;
  } catch {
    return null;
  }
}

/**
 * 从可能不完整的对象中构建有效的 TaskParamResult
 */
function buildPartialTaskParamResult(obj: any): TaskParamResult | null {
  // 至少需要 task_type
  if (!obj || typeof obj !== 'object' || !obj.task_type) {
    return null;
  }

  return {
    task_type: obj.task_type || null,
    confidence: typeof obj.confidence === 'number' ? obj.confidence : 0.8,
    params: obj.params || {},
    missing_params: Array.isArray(obj.missing_params) ? obj.missing_params : [],
    clarification_needed: typeof obj.clarification_needed === 'boolean' ? obj.clarification_needed : false,
    clarification_question: obj.clarification_question || '',
  };
}

export function isTaskParamJson(content: string): TaskParamResult | null {
  // 尝试直接解析
  try {
    const parsed = JSON.parse(content.trim());
    if (isValidTaskParamResult(parsed)) {
      return parsed;
    }
    // 即使不完全符合，尝试构建部分结果
    const partial = buildPartialTaskParamResult(parsed);
    if (partial) return partial;
  } catch {
    // 不是纯JSON，继续尝试提取
  }

  // 尝试从markdown代码块中提取
  const jsonMatch = content.match(/```(?:json)?\s*([\s\S]*?)```/);
  if (jsonMatch) {
    try {
      const parsed = JSON.parse(jsonMatch[1].trim());
      if (isValidTaskParamResult(parsed)) {
        return parsed;
      }
      const partial = buildPartialTaskParamResult(parsed);
      if (partial) return partial;
    } catch {
      // 尝试修复截断的 JSON
      const repaired = tryRepairTruncatedJson(jsonMatch[1].trim());
      if (repaired) {
        try {
          const parsed = JSON.parse(repaired);
          const partial = buildPartialTaskParamResult(parsed);
          if (partial) return partial;
        } catch {
          // 修复失败
        }
      }
    }
  }

  // 尝试从内容中提取JSON对象
  const jsonObjMatch = content.match(/\{[\s\S]*"task_type"[\s\S]*/);
  if (jsonObjMatch) {
    // 先尝试直接解析
    try {
      const parsed = JSON.parse(jsonObjMatch[0]);
      if (isValidTaskParamResult(parsed)) {
        return parsed;
      }
      const partial = buildPartialTaskParamResult(parsed);
      if (partial) return partial;
    } catch {
      // 尝试修复截断的 JSON
      const repaired = tryRepairTruncatedJson(jsonObjMatch[0]);
      if (repaired) {
        try {
          const parsed = JSON.parse(repaired);
          const partial = buildPartialTaskParamResult(parsed);
          if (partial) return partial;
        } catch {
          // 修复失败
        }
      }
    }
  }

  return null;
}

/**
 * 验证是否为有效的任务参数结果
 */
function isValidTaskParamResult(obj: any): obj is TaskParamResult {
  return (
    obj &&
    typeof obj === "object" &&
    "task_type" in obj &&
    "confidence" in obj &&
    "params" in obj &&
    "missing_params" in obj &&
    "clarification_needed" in obj
  );
}

/**
 * 获取参数标签
 */
function getParamLabel(
  paramName: string,
  taskMeta: TaskMeta | null,
  includeOptionalSuffix: boolean = false
): string {
  // 优先从任务元数据获取
  if (taskMeta) {
    const allParams = [...taskMeta.required_params, ...taskMeta.optional_params];
    const param = allParams.find((p) => p.name === paramName);
    if (param?.label) {
      const label = param.label;
      // 如果需要添加可选后缀，且参数是可选的，且标签中没有"可选"
      if (includeOptionalSuffix && param.allow_empty === true && !label.includes('可选')) {
        return `${label}（可选）`;
      }
      return label;
    }
  }
  // 使用默认映射
  return DEFAULT_PARAM_LABELS[paramName] || paramName;
}

/**
 * 获取任务图标
 */
function getTaskIcon(taskMeta: TaskMeta | null): React.ReactNode {
  if (taskMeta?.icon && ICON_MAP[taskMeta.icon]) {
    return ICON_MAP[taskMeta.icon];
  }
  // 默认图标
  return <Zap className="h-5 w-5" />;
}

/**
 * 获取任务颜色
 */
function getTaskColor(taskMeta: TaskMeta | null): string {
  if (taskMeta?.category && CATEGORY_COLORS[taskMeta.category]) {
    return CATEGORY_COLORS[taskMeta.category];
  }
  return "text-blue-600 dark:text-blue-400";
}

/**
 * 渲染参数输入控件（用于识别的参数）
 */
function renderParamInput(
  key: string,
  value: any,
  onChange: (key: string, value: any) => void,
  taskMeta: TaskMeta | null
): React.ReactNode {
  if (typeof value === "boolean") {
    return (
      <Select
        value={value ? "true" : "false"}
        onValueChange={(v) => onChange(key, v === "true")}
      >
        <SelectTrigger className="h-8 text-sm">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="true">是</SelectItem>
          <SelectItem value="false">否</SelectItem>
        </SelectContent>
      </Select>
    );
  }
  
  if (Array.isArray(value)) {
    return (
      <Input
        value={value.join(", ")}
        onChange={(e) =>
          onChange(key, e.target.value.split(",").map((s) => s.trim()))
        }
        className="h-8 text-sm"
        placeholder="逗号分隔"
      />
    );
  }
  
  if (typeof value === "number") {
    return (
      <Input
        type="number"
        value={value}
        onChange={(e) => onChange(key, parseFloat(e.target.value) || 0)}
        className="h-8 text-sm"
      />
    );
  }
  
  return (
    <Input
      value={value || ""}
      onChange={(e) => onChange(key, e.target.value)}
      className="h-8 text-sm"
    />
  );
}

/**
 * 多选列输入组件（下拉+模糊搜索+多选）
 */
function ColumnMultiSelectInput({
  columns,
  value,
  onChange,
  placeholder = "搜索并选择列...",
}: {
  columns: DataColumn[];
  value: string[];
  onChange: (value: string[]) => void;
  placeholder?: string;
}) {
  const [open, setOpen] = React.useState(false);
  const [searchValue, setSearchValue] = React.useState("");
  
  const selectedValues = value || [];
  
  // 过滤列（支持关键字搜索）
  const filteredColumns = React.useMemo(() => {
    if (!searchValue) return columns;
    const lower = searchValue.toLowerCase();
    return columns.filter(
      (col) =>
        col.name.toLowerCase().includes(lower) ||
        col.dtype.toLowerCase().includes(lower)
    );
  }, [columns, searchValue]);
  
  const toggleColumn = (colName: string) => {
    if (selectedValues.includes(colName)) {
      onChange(selectedValues.filter((v) => v !== colName));
    } else {
      onChange([...selectedValues, colName]);
    }
  };
  
  const removeColumn = (colName: string) => {
    onChange(selectedValues.filter((v) => v !== colName));
  };
  
  return (
    <div className="flex-1 space-y-1">
      {/* 已选择的列标签 */}
      {selectedValues.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {selectedValues.map((colName) => (
            <Badge
              key={colName}
              variant="secondary"
              className="text-xs px-1.5 py-0 h-5 gap-0.5"
            >
              {colName}
              <button
                type="button"
                onClick={() => removeColumn(colName)}
                className="ml-0.5 hover:text-destructive"
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}
        </div>
      )}
      
      {/* 搜索下拉框 */}
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            role="combobox"
            aria-expanded={open}
            disabled={columns.length === 0}
            className="w-full h-8 justify-between font-normal text-sm"
          >
            <span className="truncate text-muted-foreground">
              {columns.length === 0 ? "请先选择数据文件" : placeholder}
            </span>
            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[280px] p-0" align="start">
          <Command shouldFilter={false}>
            <CommandInput
              placeholder="输入列名搜索..."
              value={searchValue}
              onValueChange={setSearchValue}
            />
            <CommandList>
              <CommandEmpty>未找到匹配的列</CommandEmpty>
              <CommandGroup>
                {filteredColumns.map((col) => {
                  const isSelected = selectedValues.includes(col.name);
                  return (
                    <CommandItem
                      key={col.name}
                      value={col.name}
                      onSelect={() => toggleColumn(col.name)}
                    >
                      <Check
                        className={cn(
                          "mr-2 h-4 w-4",
                          isSelected ? "opacity-100" : "opacity-0"
                        )}
                      />
                      <span className="flex-1 truncate">{col.name}</span>
                      <span className="text-xs text-muted-foreground ml-1">
                        {col.dtype}
                      </span>
                    </CommandItem>
                  );
                })}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
    </div>
  );
}

// =============================================================================
// 阶段参数分组卡片组件
// =============================================================================

interface StageParamGroupCardProps {
  stageId: string;
  stageName: string;
  params: ParamMeta[];
  editedParams: Record<string, any>;
  dataColumns: DataColumn[];
  handleParamChange: (key: string, value: any) => void;
}

function StageParamGroupCard({
  stageId,
  stageName,
  params,
  editedParams,
  dataColumns,
  handleParamChange,
}: StageParamGroupCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [showTuning, setShowTuning] = useState(false);
  
  // 分离普通参数和调优参数（advanced=true）
  const normalParams = params.filter(p => !p.advanced);
  const tuningParams = params.filter(p => p.advanced);
  
  // 按 group 字段对参数进行二次分组（同组参数并排显示）
  const groupParamsByGroup = (paramList: ParamMeta[]) => {
    const grouped: Array<{ group: string | null; params: ParamMeta[] }> = [];
    const processedGroups = new Set<string>();
    
    for (const param of paramList) {
      const effectiveGroup = param.group && param.group !== "basic" ? param.group : null;
      
      if (effectiveGroup) {
        if (!processedGroups.has(effectiveGroup)) {
          const groupParams = paramList.filter(p => p.group === effectiveGroup);
          grouped.push({ group: effectiveGroup, params: groupParams });
          processedGroups.add(effectiveGroup);
        }
      } else {
        grouped.push({ group: null, params: [param] });
      }
    }
    
    return grouped;
  };
  
  const groupedNormalParams = useMemo(() => groupParamsByGroup(normalParams), [normalParams]);
  const groupedTuningParams = useMemo(() => groupParamsByGroup(tuningParams), [tuningParams]);

  // 渲染单个参数项
  const renderParamItem = (param: ParamMeta) => {
    const isOptional = param.allow_empty === true;
    const labelText = param.label || param.name;
    const displayLabel = isOptional && !labelText.includes('可选') 
      ? `${labelText}（可选）` 
      : labelText;
    
    return (
      <div
        key={param.name}
        className="flex items-center gap-3 bg-white dark:bg-gray-900 rounded-md p-2 border border-gray-200 dark:border-gray-700"
      >
        <div className="w-32 shrink-0 flex items-center gap-1">
          <Label className="text-xs text-gray-600 dark:text-gray-400">
            {displayLabel}
          </Label>
          {param.description && (
            <Tooltip>
              <TooltipTrigger asChild>
                <HelpCircle className="h-3 w-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-help" />
              </TooltipTrigger>
              <TooltipContent side="top" className="max-w-xs">
                <p className="text-xs">{param.description}</p>
              </TooltipContent>
            </Tooltip>
          )}
        </div>
        {renderAdvancedParamInput(param, editedParams[param.name], handleParamChange, dataColumns)}
      </div>
    );
  };
  
  // 渲染参数组（单参数或多参数并排）
  const renderParamGroup = (groupItem: { group: string | null; params: ParamMeta[] }, idx: number) => (
    groupItem.params.length === 1 ? (
      renderParamItem(groupItem.params[0])
    ) : (
      <div key={groupItem.group || `group-${idx}`} className="grid grid-cols-2 gap-3">
        {groupItem.params.map(renderParamItem)}
      </div>
    )
  );

  return (
    <Collapsible open={expanded} onOpenChange={setExpanded}>
      <CollapsibleTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-between px-3 py-2 h-auto hover:bg-blue-50 dark:hover:bg-blue-950/30"
        >
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 rounded bg-blue-100 dark:bg-blue-900/50 flex items-center justify-center text-xs font-medium text-blue-700 dark:text-blue-300">
              {stageId === "general" ? "G" : stageId.charAt(0).toUpperCase()}
            </div>
            <span className="text-sm font-medium text-gray-800 dark:text-gray-100">{stageName}</span>
            <span className="text-xs text-gray-500 dark:text-gray-400">
              ({params.length}项{tuningParams.length > 0 ? `，含${tuningParams.length}项调优` : ''})
            </span>
          </div>
          {expanded ? (
            <ChevronUp className="h-3 w-3" />
          ) : (
            <ChevronDown className="h-3 w-3" />
          )}
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent className="space-y-3 pl-4 pr-1 pt-2 pb-1 border-l-2 border-muted ml-2">
        {/* 普通参数 */}
        {groupedNormalParams.map((groupItem, idx) => renderParamGroup(groupItem, idx))}
        
        {/* 调优参数（二级折叠） */}
        {tuningParams.length > 0 && (
          <div className="border-t border-dashed pt-2 mt-2">
            <button
              onClick={() => setShowTuning(!showTuning)}
              className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 mb-2"
            >
              {showTuning ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
              <span className="font-medium">调优参数</span>
              <span className="text-gray-400">({tuningParams.length})</span>
            </button>
            {showTuning && (
              <div className="space-y-3 pl-2 border-l border-orange-200 dark:border-orange-800/50">
                {groupedTuningParams.map((groupItem, idx) => renderParamGroup(groupItem, idx))}
              </div>
            )}
          </div>
        )}
      </CollapsibleContent>
    </Collapsible>
  );
}

/**
 * 渲染高级参数输入控件
 */
function renderAdvancedParamInput(
  param: ParamMeta,
  value: any,
  onChange: (key: string, value: any) => void,
  dataColumns: DataColumn[] = []
): React.ReactNode {
  const currentValue = value ?? param.default;
  
  // column_select 类型：单选列（下拉+模糊搜索）
  if (param.type === "column_select") {
    const options: ComboboxOption[] = dataColumns.map((col) => ({
      value: col.name,
      label: `${col.name} (${col.dtype})`,
    }));
    
    return (
      <Combobox
        options={options}
        value={currentValue ?? ""}
        onValueChange={(v) => onChange(param.name, v || null)}
        placeholder={dataColumns.length === 0 ? "请先选择数据文件" : "搜索并选择列..."}
        allowCustom={false}
        emptyText={dataColumns.length === 0 ? "请先选择数据文件" : "未找到匹配的列"}
        className="flex-1"
      />
    );
  }
  
  // column_multi_select 类型：多选列（下拉+模糊搜索+多选）
  if (param.type === "column_multi_select") {
    return (
      <ColumnMultiSelectInput
        columns={dataColumns}
        value={Array.isArray(currentValue) ? currentValue : []}
        onChange={(v) => onChange(param.name, v)}
        placeholder={dataColumns.length === 0 ? "请先选择数据文件" : "搜索并选择列..."}
      />
    );
  }
  
  // column_combobox 类型：支持下拉选择和自定义输入（单选）
  if (param.type === "column_combobox") {
    const options: ComboboxOption[] = dataColumns.map((col) => ({
      value: col.name,
      label: `${col.name} (${col.dtype})`,
    }));
    
    return (
      <Combobox
        options={options}
        value={currentValue ?? ""}
        onValueChange={(v) => onChange(param.name, v || null)}
        placeholder={dataColumns.length === 0 ? "请先选择数据文件" : "搜索或输入列名..."}
        allowCustom={param.allow_custom !== false}
        emptyText={dataColumns.length === 0 ? "请先选择数据文件" : "未找到匹配的列"}
        className="flex-1"
      />
    );
  }
  
  // 如果有选项列表，使用下拉选择
  if (param.options && param.options.length > 0) {
    // 检测选项值是否为 boolean 类型
    const hasBooleanOptions = param.options.some(opt => typeof opt.value === "boolean");
    
    // 将值转换为字符串（用于 Select 组件）
    const valueToString = (v: unknown): string => {
      if (v === true) return "true";
      if (v === false) return "false";
      return String(v ?? "");
    };
    
    // 从字符串恢复原始类型
    const stringToValue = (s: string): unknown => {
      if (hasBooleanOptions) {
        if (s === "true") return true;
        if (s === "false") return false;
      }
      return s;
    };
    
    return (
      <Select
        value={valueToString(currentValue)}
        onValueChange={(v) => onChange(param.name, stringToValue(v))}
      >
        <SelectTrigger className="h-8 text-sm flex-1">
          <SelectValue placeholder={`选择${param.label}`} />
        </SelectTrigger>
        <SelectContent>
          {param.options.map((opt) => (
            <SelectItem key={valueToString(opt.value)} value={valueToString(opt.value)}>
              {opt.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    );
  }
  
  // 布尔类型
  if (param.type === "boolean" || typeof currentValue === "boolean") {
    return (
      <Select
        value={currentValue ? "true" : "false"}
        onValueChange={(v) => onChange(param.name, v === "true")}
      >
        <SelectTrigger className="h-8 text-sm flex-1">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="true">是</SelectItem>
          <SelectItem value="false">否</SelectItem>
        </SelectContent>
      </Select>
    );
  }
  
  // 数字类型
  if (param.type === "number" || param.type === "integer" || param.type === "float") {
    const handleNumberChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      const val = e.target.value;
      if (val === "" || val === null || val === undefined) {
        // 空值：对于 allow_empty=true 的参数恢复为 null，否则为 0
        onChange(param.name, param.allow_empty ? null : 0);
      } else {
        const parsed = parseFloat(val);
        onChange(param.name, isNaN(parsed) ? (param.allow_empty ? null : 0) : parsed);
      }
    };
    
    return (
      <Input
        type="number"
        value={currentValue ?? ""}
        onChange={handleNumberChange}
        className="h-8 text-sm flex-1"
        placeholder={param.default !== undefined ? `默认: ${param.default}` : ""}
        min={param.min}
        max={param.max}
        step={param.step}
      />
    );
  }
  
  // 默认文本输入
  return (
    <Input
      value={currentValue ?? ""}
      onChange={(e) => onChange(param.name, e.target.value)}
      className="h-8 text-sm flex-1"
      placeholder={param.default !== undefined ? `默认: ${param.default}` : ""}
    />
  );
}

// =============================================================================
// TaskParamCard 组件
// =============================================================================

export function TaskParamCard({
  paramResult,
  onConfirm,
  onModify,
  isExecuting = false,
  isConfirmed = false,
  sessionId = "default",
}: TaskParamCardProps) {
  // 默认使用专家模式，便于用户手动控制每个阶段
  const [executionMode, setExecutionMode] = useState<"auto" | "expert">("expert");
  const [editedParams, setEditedParams] = useState<Record<string, any>>(
    paramResult.params
  );
  const [taskMeta, setTaskMeta] = useState<TaskMeta | null>(null);
  const [loadingMeta, setLoadingMeta] = useState(false);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [dataColumns, setDataColumns] = useState<DataColumn[]>([]);

  // 加载任务元数据
  useEffect(() => {
    if (paramResult.task_type) {
      setLoadingMeta(true);
      fetchTaskMeta(paramResult.task_type)
        .then(setTaskMeta)
        .finally(() => setLoadingMeta(false));
    }
  }, [paramResult.task_type]);

  // 加载数据列（当data_file变化时）
  useEffect(() => {
    const dataFile = editedParams.data_file;
    if (dataFile) {
      fetchDataColumns(dataFile, sessionId).then(setDataColumns);
    } else {
      setDataColumns([]);
    }
  }, [editedParams.data_file, sessionId]);

  // 当任务元数据加载完成后，初始化高级参数的默认值
  useEffect(() => {
    if (taskMeta?.optional_params) {
      setEditedParams((prev) => {
        const updated = { ...prev };
        taskMeta.optional_params.forEach((param) => {
          // 如果参数不存在且有默认值，则设置默认值
          if (!(param.name in updated) && param.default !== undefined) {
            updated[param.name] = param.default;
          }
        });
        return updated;
      });
    }
  }, [taskMeta]);

  const handleParamChange = useCallback((key: string, value: any) => {
    setEditedParams((prev) => ({ ...prev, [key]: value }));
  }, []);

  const handleConfirm = useCallback(() => {
    onConfirm(editedParams, executionMode);
  }, [editedParams, executionMode, onConfirm]);

  // 获取任务显示名称
  const taskDisplayName = taskMeta?.task_name || paramResult.task_type || "未知任务";
  const taskIcon = getTaskIcon(taskMeta);
  const taskColor = getTaskColor(taskMeta);

  // 分离识别的参数和高级参数
  const { recognizedParams, advancedParams, stageGroupedAdvancedParams } = useMemo(() => {
    if (!taskMeta) {
      return { 
        recognizedParams: Object.entries(editedParams), 
        advancedParams: [] as ParamMeta[],
        stageGroupedAdvancedParams: [] as Array<{ stageId: string; stageName: string; params: ParamMeta[] }>
      };
    }

    // 核心参数名列表（必须显示在主区域）
    // 只包含 required=true 的参数 + data_file
    const coreParamNames = new Set([
      ...taskMeta.required_params
        .filter((p) => p.required !== false)  // 只取 required=true 的
        .map((p) => p.name),
      'data_file',  // 数据文件始终作为核心参数
    ]);

    // 识别的参数 = 核心参数
    const recognized = Object.entries(editedParams).filter(([key]) => {
      return coreParamNames.has(key);
    });

    // 高级参数 = optional_params + required_params 中 required=false 的
    const optionalFromRequired = taskMeta.required_params
      .filter((p) => p.required === false)
      .map((p) => ({
        ...p,
        currentValue: editedParams[p.name] !== undefined ? editedParams[p.name] : p.default
      }));
    
    const optionalParams = taskMeta.optional_params
      .filter((p) => !coreParamNames.has(p.name))
      .map((p) => ({
        ...p,
        currentValue: editedParams[p.name] !== undefined ? editedParams[p.name] : p.default
      }));

    let allAdvanced = [...optionalFromRequired, ...optionalParams];

    // 使用通用的 show_when 条件过滤参数
    // 这会自动处理 mining_mode 等条件依赖
    allAdvanced = allAdvanced.filter((p) => shouldShowParam(p, editedParams));

    // 构建阶段ID到阶段名称的映射
    const stageNameMap: Record<string, string> = {};
    (taskMeta.stages || []).forEach((s) => {
      stageNameMap[s.id] = s.name;
    });
    
    // 按阶段分组高级参数，保持阶段顺序
    const stageOrder = (taskMeta.stages || []).map(s => s.id);
    const stageGroups: Array<{ stageId: string; stageName: string; params: ParamMeta[] }> = [];
    const generalParams: ParamMeta[] = [];  // 无阶段标识的参数
    
    // 初始化每个阶段的参数数组
    const stageParamsMap: Record<string, ParamMeta[]> = {};
    stageOrder.forEach(stageId => {
      stageParamsMap[stageId] = [];
    });
    
    // 按阶段分组
    for (const param of allAdvanced) {
      if (param.stage && stageParamsMap[param.stage]) {
        stageParamsMap[param.stage].push(param);
      } else {
        generalParams.push(param);
      }
    }
    
    // 按阶段顺序构建分组结果（只包含有参数的阶段）
    stageOrder.forEach(stageId => {
      if (stageParamsMap[stageId].length > 0) {
        stageGroups.push({
          stageId,
          stageName: stageNameMap[stageId] || stageId,
          params: stageParamsMap[stageId]
        });
      }
    });
    
    // 如果有无阶段标识的参数，放到"通用参数"组
    if (generalParams.length > 0) {
      stageGroups.push({
        stageId: "general",
        stageName: "通用参数",
        params: generalParams
      });
    }

    return { 
      recognizedParams: recognized, 
      advancedParams: allAdvanced,
      stageGroupedAdvancedParams: stageGroups
    };
  }, [taskMeta, editedParams, paramResult.params, paramResult.task_type]);

  // 如果需要澄清且确实有缺失参数，显示澄清问题
  // 注意：如果 missing_params 为空，即使 clarification_needed=true 也应显示参数卡片
  if (paramResult.clarification_needed && paramResult.clarification_question && 
      paramResult.missing_params && paramResult.missing_params.length > 0) {
    return (
      <Card className="border-yellow-200 dark:border-yellow-800 bg-yellow-50/50 dark:bg-yellow-950/20">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-yellow-700 dark:text-yellow-400">
            <AlertCircle className="h-5 w-5" />
            需要更多信息
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-700 dark:text-gray-300">
            {paramResult.clarification_question}
          </p>
        </CardContent>
      </Card>
    );
  }

  // 如果无法识别任务类型
  if (!paramResult.task_type) {
    return (
      <Card className="border-gray-200 dark:border-gray-700">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
            <AlertCircle className="h-5 w-5" />
            无法识别任务类型
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            {paramResult.clarification_question ||
              "请提供更多信息，例如您想执行的任务类型和数据文件。"}
          </p>
        </CardContent>
      </Card>
    );
  }

  // 已确认状态
  if (isConfirmed) {
    return (
      <Card className="border-green-200 dark:border-green-800 bg-green-50/50 dark:bg-green-950/20">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-green-700 dark:text-green-400">
            <CheckCircle className="h-5 w-5" />
            {taskDisplayName} - 已确认执行
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-gray-600 dark:text-gray-400">
            任务已开始执行，请查看执行进度。
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-blue-200 dark:border-blue-800 bg-blue-50/50 dark:bg-blue-950/20">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2">
          {taskIcon}
          <span className={taskColor}>
            {taskDisplayName}
          </span>
          {loadingMeta && (
            <Loader2 className="h-4 w-4 animate-spin text-gray-400" />
          )}
        </CardTitle>
        {taskMeta?.description && (
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            {taskMeta.description}
          </p>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 识别的参数 */}
        <div className="space-y-3">
          <div className="text-sm font-medium text-gray-700 dark:text-gray-300">
            识别的参数
          </div>
          <div className="grid gap-3">
            {recognizedParams.map(([key, value]) => (
              <div
                key={key}
                className="flex items-center gap-3 bg-white dark:bg-gray-900 rounded-md p-2 border border-gray-200 dark:border-gray-700"
              >
                <Label className="w-28 text-xs text-gray-600 dark:text-gray-400 shrink-0">
                  {getParamLabel(key, taskMeta, true)}
                </Label>
                {renderParamInput(key, value, handleParamChange, taskMeta)}
              </div>
            ))}
          </div>
        </div>

        {/* 高级参数折叠区（按阶段分组） */}
        {advancedParams.length > 0 && (
          <Collapsible open={advancedOpen} onOpenChange={setAdvancedOpen}>
            <CollapsibleTrigger asChild>
              <Button
                variant="ghost"
                className="w-full justify-between p-3 h-auto hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-200 hover:text-gray-900 dark:hover:text-gray-100"
              >
                <div className="flex items-center gap-2">
                  <Settings2 className="h-4 w-4" />
                  <span className="text-sm">高级参数</span>
                  <span className="text-xs text-muted-foreground">
                    ({advancedParams.length}项，{stageGroupedAdvancedParams.length}个阶段)
                  </span>
                </div>
                {advancedOpen ? (
                  <ChevronUp className="h-4 w-4" />
                ) : (
                  <ChevronDown className="h-4 w-4" />
                )}
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent className="space-y-3 pt-2">
              <TooltipProvider delayDuration={200}>
                {stageGroupedAdvancedParams.map((stageGroup) => (
                  <StageParamGroupCard
                    key={stageGroup.stageId}
                    stageId={stageGroup.stageId}
                    stageName={stageGroup.stageName}
                    params={stageGroup.params}
                    editedParams={editedParams}
                    dataColumns={dataColumns}
                    handleParamChange={handleParamChange}
                  />
                ))}
              </TooltipProvider>
            </CollapsibleContent>
          </Collapsible>
        )}

        {/* 缺失参数警告 */}
        {paramResult.missing_params.length > 0 && (
          <div className="bg-yellow-50 dark:bg-yellow-950/30 border border-yellow-200 dark:border-yellow-800 rounded-md p-3">
            <div className="flex items-center gap-2 text-yellow-700 dark:text-yellow-400 text-sm font-medium mb-1">
              <AlertCircle className="h-4 w-4" />
              缺失必需参数
            </div>
            <div className="text-xs text-yellow-600 dark:text-yellow-500">
              {paramResult.missing_params.map(p => getParamLabel(p, taskMeta)).join("、")}
            </div>
          </div>
        )}

        {/* 执行模式选择 */}
        <div className="space-y-2">
          <div className="text-sm font-medium text-gray-700 dark:text-gray-300">
            选择执行模式
          </div>
          <RadioGroup
            value={executionMode}
            onValueChange={(v) => setExecutionMode(v as "auto" | "expert")}
            className="flex gap-4"
          >
            <div 
              className={`flex items-center space-x-2 p-2 rounded-md cursor-pointer transition-colors ${
                executionMode === "auto" 
                  ? "bg-blue-100 dark:bg-blue-900/30 border border-blue-300 dark:border-blue-700" 
                  : "hover:bg-gray-100 dark:hover:bg-gray-800 border border-transparent"
              }`}
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                setExecutionMode("auto");
              }}
            >
              <RadioGroupItem value="auto" id={`mode-auto-${paramResult.task_type}`} />
              <Label htmlFor={`mode-auto-${paramResult.task_type}`} className="text-sm cursor-pointer">
                🚀 自动模式
                <span className="text-xs text-gray-500 ml-1">
                  （一键执行全部阶段）
                </span>
              </Label>
            </div>
            <div 
              className={`flex items-center space-x-2 p-2 rounded-md cursor-pointer transition-colors ${
                executionMode === "expert" 
                  ? "bg-blue-100 dark:bg-blue-900/30 border border-blue-300 dark:border-blue-700" 
                  : "hover:bg-gray-100 dark:hover:bg-gray-800 border border-transparent"
              }`}
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                setExecutionMode("expert");
              }}
            >
              <RadioGroupItem value="expert" id={`mode-expert-${paramResult.task_type}`} />
              <Label htmlFor={`mode-expert-${paramResult.task_type}`} className="text-sm cursor-pointer">
                🔍 专家模式
                <span className="text-xs text-gray-500 ml-1">
                  （每阶段暂停确认）
                </span>
              </Label>
            </div>
          </RadioGroup>
        </div>

        {/* 操作按钮 */}
        <div className="flex gap-3 pt-2">
          <Button
            onClick={handleConfirm}
            disabled={isExecuting || paramResult.missing_params.length > 0}
            className="flex-1 bg-green-600 hover:bg-green-700 text-white"
          >
            {isExecuting ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                执行中...
              </>
            ) : (
              <>
                <CheckCircle className="h-4 w-4 mr-2" />
                确认执行
              </>
            )}
          </Button>
          {onModify && (
            <Button
              variant="outline"
              onClick={onModify}
              disabled={isExecuting}
              className="flex-1"
            >
              <Edit className="h-4 w-4 mr-2" />
              修改参数
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export default TaskParamCard;
