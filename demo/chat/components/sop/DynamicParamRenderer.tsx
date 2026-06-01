/**
 * 动态参数渲染器
 * 根据后端元数据自动生成表单控件
 */

"use client";

import React, { useState, useMemo } from "react";
import { PriorRulesInput } from "./PriorRulesInput";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import { Textarea } from "@/components/ui/textarea";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
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
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { HelpCircle, Check, ChevronsUpDown, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { TaskParam, DataColumn } from "@/lib/sopService";
import { Combobox, ComboboxOption } from "@/components/ui/combobox";

// =============================================================================
// 类型定义
// =============================================================================

export interface DynamicParamRendererProps {
  /** 参数元数据 */
  param: TaskParam;
  /** 当前值 */
  value: any;
  /** 值变更回调 */
  onChange: (value: any) => void;
  /** 数据列列表（用于column_select类型） */
  columns?: DataColumn[];
  /** 列加载中 */
  columnsLoading?: boolean;
  /** 所有表单值（用于show_when条件判断） */
  allValues?: Record<string, any>;
  /** 是否禁用 */
  disabled?: boolean;
  /** 自定义类名 */
  className?: string;
  /** 会话ID（用于 prior_rules_input 的工作区文件选择和列名校验） */
  sessionId?: string;
}

// =============================================================================
// 条件显示判断
// =============================================================================

/**
 * 判断参数是否应该显示
 * 支持 MongoDB 风格的条件操作符：$eq, $ne, $gt, $gte, $lt, $lte, $in, $nin
 */
/**
 * 评估单个条件（内部辅助函数）
 * 支持简单值比较和 MongoDB 风格的条件操作符
 */
function evaluateCondition(
  key: string,
  condition: unknown,
  allValues: Record<string, any>
): boolean {
  const actualValue = allValues[key];
  
  // 支持 MongoDB 风格的条件操作符
  if (condition && typeof condition === 'object' && !Array.isArray(condition)) {
    const condObj = condition as Record<string, unknown>;
    
    // $eq: 等于
    if ('$eq' in condObj) {
      return actualValue === condObj.$eq;
    }
    // $ne: 不等于
    if ('$ne' in condObj) {
      // 特殊处理：null/undefined/空字符串 都视为"空"
      const isEmpty = (v: unknown) => v === null || v === undefined || v === '';
      const condIsEmpty = isEmpty(condObj.$ne);
      const actualIsEmpty = isEmpty(actualValue);
      
      if (condIsEmpty) {
        // $ne: null 表示"不为空"，即 actualValue 必须有值
        return !actualIsEmpty;
      } else {
        // 普通不等于比较
        return actualValue !== condObj.$ne;
      }
    }
    // $gt: 大于
    if ('$gt' in condObj) {
      return actualValue > (condObj.$gt as number);
    }
    // $gte: 大于等于
    if ('$gte' in condObj) {
      return actualValue >= (condObj.$gte as number);
    }
    // $lt: 小于
    if ('$lt' in condObj) {
      return actualValue < (condObj.$lt as number);
    }
    // $lte: 小于等于
    if ('$lte' in condObj) {
      return actualValue <= (condObj.$lte as number);
    }
    // $in: 在数组中
    if ('$in' in condObj && Array.isArray(condObj.$in)) {
      return condObj.$in.includes(actualValue);
    }
    // $nin: 不在数组中
    if ('$nin' in condObj && Array.isArray(condObj.$nin)) {
      return !condObj.$nin.includes(actualValue);
    }
  }
  
  // 简单值比较（向后兼容）
  return actualValue === condition;
}

/**
 * 评估复合条件（支持 $or/$and 递归）
 */
function evaluateShowWhen(
  showWhen: Record<string, unknown>,
  allValues: Record<string, any>
): boolean {
  for (const [key, condition] of Object.entries(showWhen)) {
    // $or: 任一条件满足即可
    if (key === '$or' && Array.isArray(condition)) {
      const orResult = condition.some((subCond: Record<string, unknown>) => 
        evaluateShowWhen(subCond, allValues)
      );
      if (!orResult) return false;
    }
    // $and: 所有条件都必须满足
    else if (key === '$and' && Array.isArray(condition)) {
      const andResult = condition.every((subCond: Record<string, unknown>) => 
        evaluateShowWhen(subCond, allValues)
      );
      if (!andResult) return false;
    }
    // 普通字段条件
    else {
      if (!evaluateCondition(key, condition, allValues)) {
        return false;
      }
    }
  }
  return true;
}

export function shouldShowParam(
  param: TaskParam,
  allValues: Record<string, any>
): boolean {
  if (!param.show_when) return true;
  return evaluateShowWhen(param.show_when as Record<string, unknown>, allValues);
}

// =============================================================================
// 参数标签组件
// =============================================================================

interface ParamLabelProps {
  param: TaskParam;
  children?: React.ReactNode;
}

function ParamLabel({ param, children }: ParamLabelProps) {
  // 判断是否为"可选"参数（用户可以留空、不填写的参数）
  // 只有 allow_empty === true 的参数才是真正可选的
  const isOptional = param.allow_empty === true;
  // 获取标签文本，如果标签中已包含"可选"则不重复添加
  const labelText = param.label || param.name;
  const displayLabel = isOptional && !labelText.includes('可选') 
    ? `${labelText}（可选）` 
    : labelText;

  return (
    <Label className="flex items-center gap-1">
      {displayLabel}
      {param.required && !isOptional && <span className="text-red-500">*</span>}
      {param.description && (
        <Tooltip>
          <TooltipTrigger asChild>
            <HelpCircle className="h-3.5 w-3.5 text-muted-foreground cursor-help" />
          </TooltipTrigger>
          <TooltipContent side="top" className="max-w-[280px]">
            <p>{param.description}</p>
          </TooltipContent>
        </Tooltip>
      )}
      {children}
    </Label>
  );
}

// =============================================================================
// 各类型渲染器
// =============================================================================

/** 数值输入 */
function NumberRenderer({
  param,
  value,
  onChange,
  disabled,
}: DynamicParamRendererProps) {
  // 兼容两种格式：顶层字段 或 validation 嵌套对象
  const paramWithValidation = param as TaskParam & { validation?: { min?: number; max?: number; step?: number } };
  const min = param.min ?? paramWithValidation.validation?.min;
  const max = param.max ?? paramWithValidation.validation?.max;
  const step = param.step ?? paramWithValidation.validation?.step ?? 0.01;
  
  const hasSlider = min !== undefined && max !== undefined;
  
  // 判断是否为可选参数（allow_empty=true 且 default 为 null 或 undefined）
  const isOptionalNullable = param.allow_empty === true && (param.default === null || param.default === undefined);
  const isEnabled = value !== null && value !== undefined;
  
  // 可选参数的默认激活值（使用 min 值作为初始值）
  const defaultActiveValue = min ?? param.default ?? 0;
  
  // 统一的数值变更处理函数（与 TaskParamCard 保持一致）
  const handleNumberChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    if (val === "" || val === null || val === undefined) {
      // 空值：对于 allow_empty=true 的参数恢复为 null，否则为 0
      onChange(param.allow_empty ? null : 0);
    } else {
      const parsed = parseFloat(val);
      onChange(isNaN(parsed) ? (param.allow_empty ? null : 0) : parsed);
    }
  };

  // 可选参数：显示启用开关
  if (isOptionalNullable) {
    return (
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <ParamLabel param={param} />
          <Switch
            checked={isEnabled}
            onCheckedChange={(checked) => onChange(checked ? defaultActiveValue : null)}
            disabled={disabled}
          />
        </div>
        {isEnabled && hasSlider && (
          <div className="flex items-center gap-3">
            <Slider
              value={[value]}
              onValueChange={([v]) => onChange(v)}
              min={min}
              max={max}
              step={step}
              disabled={disabled}
              className="flex-1"
            />
            <Input
              type="number"
              value={value}
              onChange={handleNumberChange}
              min={min}
              max={max}
              step={step}
              disabled={disabled}
              className="w-20 h-8 text-sm text-right"
            />
          </div>
        )}
        {isEnabled && !hasSlider && (
          <Input
            type="number"
            value={value ?? ""}
            onChange={handleNumberChange}
            min={min}
            max={max}
            step={step}
            disabled={disabled}
          />
        )}
        {!isEnabled && (
          <p className="text-xs text-muted-foreground">未启用（开启后生效）</p>
        )}
      </div>
    );
  }

  // 普通数值参数
  return (
    <div className="space-y-2">
      <ParamLabel param={param} />
      {hasSlider ? (
        <div className="flex items-center gap-3">
          <Slider
            value={[value ?? param.default ?? min ?? 0]}
            onValueChange={([v]) => onChange(v)}
            min={min}
            max={max}
            step={step}
            disabled={disabled}
            className="flex-1"
          />
          <Input
            type="number"
            value={value ?? param.default ?? min ?? 0}
            onChange={handleNumberChange}
            min={min}
            max={max}
            step={step}
            disabled={disabled}
            className="w-20 h-8 text-sm text-right"
          />
        </div>
      ) : (
        <Input
          type="number"
          value={value ?? param.default ?? ""}
          onChange={handleNumberChange}
          min={min}
          max={max}
          step={step}
          disabled={disabled}
        />
      )}
    </div>
  );
}

/** 文本输入 */
function TextRenderer({
  param,
  value,
  onChange,
  disabled,
}: DynamicParamRendererProps) {
  return (
    <div className="space-y-2">
      <ParamLabel param={param} />
      <Input
        type="text"
        value={value ?? param.default ?? ""}
        onChange={(e) => onChange(e.target.value)}
        placeholder={param.description}
        disabled={disabled}
      />
    </div>
  );
}

/** 多行文本 */
function TextareaRenderer({
  param,
  value,
  onChange,
  disabled,
}: DynamicParamRendererProps) {
  return (
    <div className="space-y-2">
      <ParamLabel param={param} />
      <Textarea
        value={value ?? param.default ?? ""}
        onChange={(e) => onChange(e.target.value)}
        placeholder={param.description}
        disabled={disabled}
        rows={3}
      />
    </div>
  );
}

/** 下拉选择 */
function SelectRenderer({
  param,
  value,
  onChange,
  disabled,
}: DynamicParamRendererProps) {
  return (
    <div className="space-y-2">
      <ParamLabel param={param} />
      <Select
        value={value ?? param.default ?? ""}
        onValueChange={onChange}
        disabled={disabled}
      >
        <SelectTrigger>
          <SelectValue placeholder={`选择${param.label}`} />
        </SelectTrigger>
        <SelectContent>
          {param.options?.map((opt) => (
            <SelectItem key={opt.value} value={opt.value}>
              {opt.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

/** 单选组 */
function RadioRenderer({
  param,
  value,
  onChange,
  disabled,
}: DynamicParamRendererProps) {
  const currentValue = value ?? param.default ?? "";
  
  // 将值转换为字符串用于 RadioGroup 比较（处理 boolean 类型的 options）
  const valueToString = (v: unknown): string => {
    if (v === true) return "true";
    if (v === false) return "false";
    return String(v ?? "");
  };
  
  // 从字符串恢复原始类型
  const stringToOriginalValue = (s: string, optValue: unknown): unknown => {
    // 如果原始 option value 是 boolean，转换回 boolean
    if (typeof optValue === "boolean") {
      return s === "true";
    }
    return optValue;
  };
  
  const currentValueStr = valueToString(currentValue);

  return (
    <div className="space-y-2">
      <ParamLabel param={param} />
      <RadioGroup
        value={currentValueStr}
        onValueChange={(newValue) => {
          // 找到对应的 option 获取原始值类型
          const opt = param.options?.find(o => valueToString(o.value) === newValue);
          if (opt) {
            onChange(stringToOriginalValue(newValue, opt.value));
          } else {
            onChange(newValue);
          }
        }}
        disabled={disabled}
        className="grid grid-cols-2 gap-2"
      >
        {param.options?.map((opt) => {
          const optValueStr = valueToString(opt.value);
          return (
            <div
              key={optValueStr}
              className={cn(
                "flex items-center space-x-2 p-3 rounded-lg border cursor-pointer transition-colors",
                currentValueStr === optValueStr
                  ? "border-blue-300 bg-blue-50 dark:border-blue-700 dark:bg-blue-900/30"
                  : "border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-900/30"
              )}
              onClick={() => !disabled && onChange(opt.value)}
            >
              <RadioGroupItem value={optValueStr} id={`${param.name}-${optValueStr}`} />
              <Label
                htmlFor={`${param.name}-${optValueStr}`}
                className="cursor-pointer font-medium"
              >
                {opt.label}
              </Label>
            </div>
          );
        })}
      </RadioGroup>
    </div>
  );
}

/** 开关/复选框 */
function CheckboxRenderer({
  param,
  value,
  onChange,
  disabled,
}: DynamicParamRendererProps) {
  return (
    <div className="flex items-center justify-between p-3 rounded-lg bg-gray-50 dark:bg-gray-900/30">
      <div>
        <Label>{param.label}</Label>
        {param.description && (
          <p className="text-xs text-gray-500">{param.description}</p>
        )}
      </div>
      <Switch
        checked={value ?? param.default ?? false}
        onCheckedChange={onChange}
        disabled={disabled}
      />
    </div>
  );
}

/** 列选择（单选） */
function ColumnSelectRenderer({
  param,
  value,
  onChange,
  columns = [],
  columnsLoading,
  disabled,
}: DynamicParamRendererProps) {
  const allowEmpty = param.allow_empty || !param.required;

  return (
    <div className="space-y-2">
      <ParamLabel param={param} />
      <Select
        value={value || (allowEmpty ? "__none__" : "")}
        onValueChange={(v) => onChange(v === "__none__" ? "" : v)}
        disabled={disabled || columnsLoading || columns.length === 0}
      >
        <SelectTrigger>
          <SelectValue
            placeholder={columnsLoading ? "加载中..." : `选择${param.label}`}
          />
        </SelectTrigger>
        <SelectContent>
          {allowEmpty && <SelectItem value="__none__">不选择</SelectItem>}
          {columns.map((col) => (
            <SelectItem key={col.name} value={col.name}>
              <div className="flex items-center gap-2">
                <span>{col.name}</span>
                <span className="text-xs text-gray-400">({col.dtype})</span>
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

/** 列选择（Combobox：支持下拉选择和自定义输入） */
function ColumnComboboxRenderer({
  param,
  value,
  onChange,
  columns = [],
  columnsLoading,
  disabled,
}: DynamicParamRendererProps) {
  const allowEmpty = param.allow_empty || !param.required;
  
  // 将列转换为 Combobox 选项
  const columnOptions: ComboboxOption[] = columns.map((col) => ({
    value: col.name,
    label: `${col.name} (${col.dtype})`,
  }));
  
  // 如果允许空值，添加一个"不选择"选项
  if (allowEmpty) {
    columnOptions.unshift({ value: "", label: "不选择" });
  }

  return (
    <div className="space-y-2">
      <ParamLabel param={param} />
      <Combobox
        options={columnOptions}
        value={value ?? ""}
        onValueChange={onChange}
        placeholder={columnsLoading ? "加载中..." : `选择或输入${param.label}`}
        searchPlaceholder="搜索或输入列名..."
        emptyText={columns.length === 0 ? "请先选择数据文件" : "无匹配列"}
        allowCustom={true}
        customInputHint="回车使用自定义列名"
        disabled={disabled || columnsLoading}
      />
    </div>
  );
}

/** 列多选（关键字检索+下拉菜单） */
function ColumnMultiSelectRenderer({
  param,
  value,
  onChange,
  columns = [],
  columnsLoading,
  disabled,
}: DynamicParamRendererProps) {
  const [open, setOpen] = useState(false);
  const [searchValue, setSearchValue] = useState("");
  
  const selectedValues: string[] = Array.isArray(value) ? value : [];

  // 过滤列（支持关键字搜索）
  const filteredColumns = useMemo(() => {
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

  const clearAll = () => {
    onChange([]);
  };

  return (
    <div className="space-y-2">
      <ParamLabel param={param}>
        {selectedValues.length > 0 && (
          <span className="text-xs text-muted-foreground ml-2">
            (已选 {selectedValues.length} 列)
          </span>
        )}
      </ParamLabel>
      
      {/* 已选择的列标签 */}
      {selectedValues.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {selectedValues.map((colName) => (
            <Badge
              key={colName}
              variant="secondary"
              className="text-xs px-2 py-0.5 gap-1"
            >
              {colName}
              <button
                type="button"
                onClick={() => removeColumn(colName)}
                disabled={disabled}
                className="ml-1 hover:text-destructive"
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}
          {selectedValues.length > 1 && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={clearAll}
              disabled={disabled}
              className="h-6 px-2 text-xs text-muted-foreground hover:text-destructive"
            >
              清空
            </Button>
          )}
        </div>
      )}

      {/* 搜索下拉框 */}
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            role="combobox"
            aria-expanded={open}
            disabled={disabled || columnsLoading || columns.length === 0}
            className="w-full justify-between font-normal"
          >
            {columnsLoading
              ? "加载中..."
              : columns.length === 0
              ? "请先选择数据文件"
              : "搜索并选择列..."}
            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[300px] p-0" align="start">
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
                      <span className="flex-1">{col.name}</span>
                      <span className="text-xs text-muted-foreground">
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

/** P2-7: 先验规则增强输入 */
function PriorRulesInputRenderer({
  param,
  value,
  onChange,
  disabled,
  sessionId,
  allValues,
}: DynamicParamRendererProps) {
  // 从 allValues 中获取当前选择的数据文件（用于列名校验）
  const dataFile = allValues?.data_file as string | undefined;
  
  return (
    <div className="space-y-2">
      <ParamLabel param={param} />
      <PriorRulesInput
        value={value ?? param.default ?? ""}
        onChange={onChange}
        disabled={disabled}
        sessionId={sessionId}
        dataFile={dataFile}
        description={param.description}
        placeholder={param.placeholder}
      />
    </div>
  );
}

// =============================================================================
// 主渲染器
// =============================================================================

/**
 * 动态参数渲染器
 * 根据参数类型自动选择合适的表单控件
 */
export function DynamicParamRenderer(props: DynamicParamRendererProps) {
  const { param, allValues = {} } = props;

  // 检查是否应该显示
  if (!shouldShowParam(param, allValues)) {
    return null;
  }

  // 根据类型选择渲染器
  switch (param.type) {
    case "number":
      return <NumberRenderer {...props} />;

    case "text":
    case "string":
      return <TextRenderer {...props} />;

    case "textarea":
      return <TextareaRenderer {...props} />;

    case "select":
      return <SelectRenderer {...props} />;

    case "radio":
      return <RadioRenderer {...props} />;

    case "checkbox":
    case "boolean":
      return <CheckboxRenderer {...props} />;

    case "column_select":
      return <ColumnSelectRenderer {...props} />;

    case "column_combobox":
      return <ColumnComboboxRenderer {...props} />;

    case "column_multi_select":
      return <ColumnMultiSelectRenderer {...props} />;

    case "prior_rules_input":
      return <PriorRulesInputRenderer {...props} />;

    default:
      // 未知类型，使用文本输入
      console.warn(`Unknown param type: ${param.type}, falling back to text`);
      return <TextRenderer {...props} />;
  }
}

// =============================================================================
// 批量渲染辅助
// =============================================================================

export interface ParamGroupRendererProps {
  /** 参数列表 */
  params: TaskParam[];
  /** 当前所有值 */
  values: Record<string, any>;
  /** 值变更回调 */
  onChange: (name: string, value: any) => void;
  /** 数据列 */
  columns?: DataColumn[];
  /** 列加载中 */
  columnsLoading?: boolean;
  /** 是否禁用 */
  disabled?: boolean;
  /** 分组标题 */
  title?: string;
  /** 自定义类名 */
  className?: string;
}

/**
 * 参数组渲染器
 * 批量渲染一组参数
 */
export function ParamGroupRenderer({
  params,
  values,
  onChange,
  columns,
  columnsLoading,
  disabled,
  title,
  className,
}: ParamGroupRendererProps) {
  // 过滤出应该显示的参数
  const visibleParams = params.filter((p) => shouldShowParam(p, values));

  if (visibleParams.length === 0) {
    return null;
  }

  return (
    <div className={cn("space-y-4", className)}>
      {title && (
        <h4 className="text-sm font-medium text-muted-foreground">{title}</h4>
      )}
      {visibleParams.map((param) => (
        <DynamicParamRenderer
          key={param.name}
          param={param}
          value={values[param.name]}
          onChange={(v) => onChange(param.name, v)}
          columns={columns}
          columnsLoading={columnsLoading}
          allValues={values}
          disabled={disabled}
        />
      ))}
    </div>
  );
}

export default DynamicParamRenderer;
