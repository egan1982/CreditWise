"use client";

import React, { useState, useCallback, useEffect } from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { 
  Save, 
  RotateCcw, 
  Check, 
  Code2,
  Settings,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { ParamMeta, DataColumn } from "@/lib/sopService";
import { DynamicParamRenderer, shouldShowParam } from "./DynamicParamRenderer";
import { TooltipProvider } from "@/components/ui/tooltip";

/**
 * StageParamsForm 组件属性
 */
export interface StageParamsFormProps {
  /** 参数元数据列表 */
  paramsMeta: ParamMeta[];
  /** 当前参数值 */
  values: Record<string, any>;
  /** 参数变化回调 */
  onChange?: (values: Record<string, any>) => void;
  /** 保存回调 */
  onSave?: (values: Record<string, any>) => Promise<void>;
  /** 只读模式 */
  readOnly?: boolean;
  /** 自定义类名 */
  className?: string;
  /** 深色模式 */
  isDarkMode?: boolean;
  /** 标题 */
  title?: string;
  /** 是否显示JSON切换按钮 */
  showJsonToggle?: boolean;
  /** JSON模式切换回调 */
  onToggleJsonMode?: () => void;
  /** 数据列列表（用于column_select类型） */
  columns?: DataColumn[];
  /** 列加载中 */
  columnsLoading?: boolean;
}

/**
 * 可视化阶段参数表单组件
 * 
 * 根据参数元数据动态渲染表单控件，复用 DynamicParamRenderer 支持所有参数类型
 */
export function StageParamsForm({
  paramsMeta,
  values,
  onChange,
  onSave,
  readOnly = false,
  className,
  isDarkMode = false,
  title = "参数配置",
  showJsonToggle = true,
  onToggleJsonMode,
  columns = [],
  columnsLoading = false,
}: StageParamsFormProps) {
  const [localValues, setLocalValues] = useState<Record<string, any>>(values);
  const [hasChanges, setHasChanges] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);

  // 同步外部 values 变化
  useEffect(() => {
    setLocalValues(values);
    setHasChanges(false);
  }, [values]);

  // 处理单个参数变化
  const handleParamChange = useCallback((name: string, value: any) => {
    const newValues = { ...localValues, [name]: value };
    setLocalValues(newValues);
    setHasChanges(JSON.stringify(newValues) !== JSON.stringify(values));
    onChange?.(newValues);
  }, [localValues, values, onChange]);

  // 保存参数
  const handleSave = useCallback(async () => {
    if (!onSave || isSaving) return;

    try {
      setIsSaving(true);
      await onSave(localValues);
      setHasChanges(false);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2000);
    } catch (e) {
      console.error("Failed to save params:", e);
    } finally {
      setIsSaving(false);
    }
  }, [localValues, onSave, isSaving]);

  // 重置参数
  const handleReset = useCallback(() => {
    setLocalValues(values);
    setHasChanges(false);
  }, [values]);

  // 过滤出应该显示的参数（基于 show_when 条件）
  const visibleParams = paramsMeta.filter(param => shouldShowParam(param, localValues));
  
  // 分离普通参数和高级参数
  const normalParams = visibleParams.filter(p => !p.advanced);
  const advancedParams = visibleParams.filter(p => p.advanced);
  
  // 将参数按 group 分组，保持原始顺序
  // 注意：group="basic" 是默认值，不应作为分组依据
  const groupParams = (params: ParamMeta[]): Array<{ group: string | null; params: ParamMeta[] }> => {
    const grouped: Array<{ group: string | null; params: ParamMeta[] }> = [];
    const processedGroups = new Set<string>();
    
    for (const param of params) {
      const paramWithGroup = param as ParamMeta & { group?: string };
      // 只有非空且非 "basic" 的 group 才进行分组
      const effectiveGroup = paramWithGroup.group && paramWithGroup.group !== "basic" ? paramWithGroup.group : null;
      
      if (effectiveGroup) {
        if (!processedGroups.has(effectiveGroup)) {
          const groupParamsList = params.filter(p => (p as ParamMeta & { group?: string }).group === effectiveGroup);
          grouped.push({ group: effectiveGroup, params: groupParamsList });
          processedGroups.add(effectiveGroup);
        }
      } else {
        grouped.push({ group: null, params: [param] });
      }
    }
    return grouped;
  };
  
  const groupedNormalParams = groupParams(normalParams);
  const groupedAdvancedParams = groupParams(advancedParams);

  if (!paramsMeta || paramsMeta.length === 0) {
    return (
      <div className={cn(
        "flex items-center justify-center p-8 text-sm text-gray-500",
        className
      )}>
        此阶段没有可配置的参数
      </div>
    );
  }

  return (
    <div 
      className={cn(
        "flex flex-col border rounded-lg overflow-hidden",
        "border-gray-200 dark:border-gray-700",
        "bg-white dark:bg-gray-900",
        className
      )}
    >
      {/* 头部工具栏 */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 shrink-0">
        <div className="flex items-center gap-2">
          <Settings className="w-4 h-4 text-gray-500" />
          <span className="text-xs font-medium text-gray-600 dark:text-gray-400">
            {title}
          </span>
          {readOnly && (
            <span className="px-1.5 py-0.5 text-xs bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded">
              只读
            </span>
          )}
          {hasChanges && !readOnly && (
            <span className="px-1.5 py-0.5 text-xs bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400 rounded">
              已修改
            </span>
          )}
          {saveSuccess && (
            <span className="flex items-center gap-1 px-1.5 py-0.5 text-xs bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400 rounded">
              <Check className="w-3 h-3" />
              已保存
            </span>
          )}
        </div>
        
        <div className="flex items-center gap-1">
          {/* JSON模式切换 */}
          {showJsonToggle && onToggleJsonMode && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onToggleJsonMode}
              className="h-6 px-2 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
              title="切换到JSON编辑模式"
            >
              <Code2 className="w-3.5 h-3.5" />
            </Button>
          )}

          {!readOnly && (
            <>
              {/* 重置按钮 */}
              <Button
                variant="ghost"
                size="sm"
                onClick={handleReset}
                disabled={!hasChanges}
                className="h-6 px-2 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 disabled:opacity-50"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </Button>

              {/* 保存按钮 */}
              {onSave && (
                <Button
                  size="sm"
                  onClick={handleSave}
                  disabled={!hasChanges || isSaving}
                  className="h-6 px-3 text-xs bg-blue-500 text-white hover:bg-blue-600 disabled:opacity-50"
                >
                  {isSaving ? (
                    <>
                      <div className="w-3.5 h-3.5 mr-1 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      保存中...
                    </>
                  ) : (
                    <>
                      <Save className="w-3.5 h-3.5 mr-1" />
                      保存
                    </>
                  )}
                </Button>
              )}
            </>
          )}
        </div>
      </div>

      {/* 表单区域 */}
      <div className="flex-1 overflow-auto p-4 space-y-4">
        <TooltipProvider delayDuration={200}>
          {/* 普通参数（支持分组） */}
          {groupedNormalParams.map((groupItem, idx) => (
            groupItem.params.length === 1 ? (
              <DynamicParamRenderer
                key={groupItem.params[0].name}
                param={groupItem.params[0]}
                value={localValues[groupItem.params[0].name]}
                onChange={(v) => handleParamChange(groupItem.params[0].name, v)}
                columns={columns}
                columnsLoading={columnsLoading}
                allValues={localValues}
                disabled={readOnly}
              />
            ) : (
              <div key={groupItem.group || `group-${idx}`} className="grid grid-cols-2 gap-3">
                {groupItem.params.map((param) => (
                  <DynamicParamRenderer
                    key={param.name}
                    param={param}
                    value={localValues[param.name]}
                    onChange={(v) => handleParamChange(param.name, v)}
                    columns={columns}
                    columnsLoading={columnsLoading}
                    allValues={localValues}
                    disabled={readOnly}
                  />
                ))}
              </div>
            )
          ))}

          {/* 调优参数（可折叠，支持分组）- 区别于任务级的"高级参数"面板 */}
          {advancedParams.length > 0 && (
            <div className="border-t border-dashed pt-3 mt-3">
              <button
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 mb-2"
              >
                {showAdvanced ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                <span className="font-medium">调优参数</span>
                <span className="text-gray-400">({advancedParams.length})</span>
              </button>
              {showAdvanced && (
                <div className="space-y-4 pl-3 border-l-2 border-orange-200 dark:border-orange-800/50">
                  {groupedAdvancedParams.map((groupItem, idx) => (
                    groupItem.params.length === 1 ? (
                      <DynamicParamRenderer
                        key={groupItem.params[0].name}
                        param={groupItem.params[0]}
                        value={localValues[groupItem.params[0].name]}
                        onChange={(v) => handleParamChange(groupItem.params[0].name, v)}
                        columns={columns}
                        columnsLoading={columnsLoading}
                        allValues={localValues}
                        disabled={readOnly}
                      />
                    ) : (
                      <div key={groupItem.group || `adv-group-${idx}`} className="grid grid-cols-2 gap-3">
                        {groupItem.params.map((param) => (
                          <DynamicParamRenderer
                            key={param.name}
                            param={param}
                            value={localValues[param.name]}
                            onChange={(v) => handleParamChange(param.name, v)}
                            columns={columns}
                            columnsLoading={columnsLoading}
                            allValues={localValues}
                            disabled={readOnly}
                          />
                        ))}
                      </div>
                    )
                  ))}
                </div>
              )}
            </div>
          )}
        </TooltipProvider>
      </div>
    </div>
  );
}

export default StageParamsForm;
