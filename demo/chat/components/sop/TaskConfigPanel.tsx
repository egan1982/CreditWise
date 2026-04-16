/**
 * 统一任务配置面板
 * 根据后端元数据动态生成配置表单
 */

"use client";

import React, { useState, useEffect, useCallback, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
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
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  ChevronDown,
  ChevronUp,
  Play,
  RotateCcw,
  Loader2,
  FileSpreadsheet,
  Settings2,
  X,
  BookOpen,
  Target,
  CreditCard,
  BarChart3,
  Sparkles,
} from "lucide-react";
import { sopService, TaskMeta, DataColumn, TaskParam } from "@/lib/sopService";
import { cn } from "@/lib/utils";
import { TaskGuideDialog } from "./TaskGuideDialog";
import { DynamicParamRenderer, shouldShowParam } from "./DynamicParamRenderer";

// =============================================================================
// 类型定义
// =============================================================================

export interface WorkspaceFile {
  name: string;
  path: string;
  type: string;
}

export interface TaskConfigPanelProps {
  /** 任务ID */
  taskId: string;
  /** 会话ID */
  sessionId: string;
  /** 工作区数据文件列表 */
  dataFiles: WorkspaceFile[];
  /** 执行回调 */
  onExecute: (params: Record<string, any>, filePath: string) => void;
  /** 关闭回调 */
  onClose: () => void;
  /** 是否正在执行 */
  isExecuting?: boolean;
  /** 自定义类名 */
  className?: string;
  /** P2-8: 外部注入的初始参数（来自 Chat 确认卡片 LLM 提取的参数） */
  initialParams?: Record<string, any> | null;
}

// =============================================================================
// 任务图标映射
// =============================================================================

const TASK_ICONS: Record<string, React.ReactNode> = {
  rule_mining: "🎯",
  scorecard_dev: <CreditCard className="h-4 w-4" />,
  eda: <BarChart3 className="h-4 w-4" />,
  feature_engineering: <Sparkles className="h-4 w-4" />,
  default: <Target className="h-4 w-4" />,
};

const TASK_COLORS: Record<string, string> = {
  rule_mining: "border-blue-200 dark:border-blue-800",
  scorecard_dev: "border-green-200 dark:border-green-800",
  eda: "border-purple-200 dark:border-purple-800",
  default: "border-gray-200 dark:border-gray-800",
};

const TASK_ICON_BG: Record<string, string> = {
  rule_mining: "bg-blue-100 dark:bg-blue-900/50",
  scorecard_dev: "bg-green-100 dark:bg-green-900/50",
  eda: "bg-purple-100 dark:bg-purple-900/50",
  default: "bg-gray-100 dark:bg-gray-900/50",
};

// =============================================================================
// 阶段参数分组组件
// =============================================================================

interface StageParamGroupProps {
  stageId: string;
  stageName: string;
  params: TaskParam[];
  formValues: Record<string, any>;
  columns: DataColumn[];
  columnsLoading: boolean;
  updateValue: (name: string, value: any) => void;
}

function StageParamGroup({
  stageId,
  stageName,
  params,
  formValues,
  columns,
  columnsLoading,
  updateValue,
}: StageParamGroupProps) {
  const [expanded, setExpanded] = useState(false);
  const [showTuning, setShowTuning] = useState(false);
  
  // 分离普通参数和调优参数（advanced=true）
  const normalParams = params.filter(p => !p.advanced);
  const tuningParams = params.filter(p => p.advanced);
  
  // 按 group 字段对阶段内参数进行二次分组（同组参数并排显示）
  const groupParams = (paramList: TaskParam[]) => {
    const grouped: Array<{ group: string | null; params: TaskParam[] }> = [];
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
  
  const groupedNormalParams = groupParams(normalParams);
  const groupedTuningParams = groupParams(tuningParams);

  const renderParamGroup = (groupItem: { group: string | null; params: TaskParam[] }, idx: number) => (
    groupItem.params.length === 1 ? (
      <DynamicParamRenderer
        key={groupItem.params[0].name}
        param={groupItem.params[0]}
        value={formValues[groupItem.params[0].name]}
        onChange={(v) => updateValue(groupItem.params[0].name, v)}
        columns={columns}
        columnsLoading={columnsLoading}
        allValues={formValues}
      />
    ) : (
      <div key={groupItem.group || `group-${idx}`} className="grid grid-cols-2 gap-3">
        {groupItem.params.map((param) => (
          <DynamicParamRenderer
            key={param.name}
            param={param}
            value={formValues[param.name]}
            onChange={(v) => updateValue(param.name, v)}
            columns={columns}
            columnsLoading={columnsLoading}
            allValues={formValues}
          />
        ))}
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

// =============================================================================
// 主组件
// =============================================================================

export function TaskConfigPanel({
  taskId,
  sessionId,
  dataFiles,
  onExecute,
  onClose,
  isExecuting = false,
  className,
  initialParams,
}: TaskConfigPanelProps) {
  // 状态
  const [taskMeta, setTaskMeta] = useState<TaskMeta | null>(null);
  const [loading, setLoading] = useState(true);
  const [formValues, setFormValues] = useState<Record<string, any>>({});
  const [columns, setColumns] = useState<DataColumn[]>([]);
  const [columnsLoading, setColumnsLoading] = useState(false);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [guideDialogOpen, setGuideDialogOpen] = useState(false);

  // 获取任务图标和颜色
  const taskIcon = TASK_ICONS[taskId] || TASK_ICONS.default;
  const taskColor = TASK_COLORS[taskId] || TASK_COLORS.default;
  const taskIconBg = TASK_ICON_BG[taskId] || TASK_ICON_BG.default;

  // ==========================================================================
  // 加载任务元数据
  // ==========================================================================

  useEffect(() => {
    const loadTaskMeta = async () => {
      try {
        setLoading(true);
        const meta = await sopService.getTaskDefinition(taskId);
        setTaskMeta(meta);

        // 初始化表单默认值
        const defaults: Record<string, any> = {};
        [...(meta.required_params || []), ...(meta.optional_params || [])].forEach(
          (param) => {
            if (param.default !== undefined) {
              defaults[param.name] = param.default;
            }
          }
        );
        // P2-8: 合并外部注入的初始参数（覆盖默认值）
        if (initialParams) {
          Object.entries(initialParams).forEach(([key, value]) => {
            if (value !== undefined && value !== null && value !== "") {
              defaults[key] = value;
            }
          });
        }
        setFormValues(defaults);
      } catch (err) {
        console.error("Failed to load task meta:", err);
      } finally {
        setLoading(false);
      }
    };

    loadTaskMeta();
  }, [taskId]);

  // P2-8: 当 initialParams 变化时（例如从 Chat 确认卡片二次打开同一任务），
  // 在 taskMeta 已加载的情况下补充 merge 外部参数
  useEffect(() => {
    if (initialParams && taskMeta && !loading) {
      setFormValues(prev => {
        const updated = { ...prev };
        Object.entries(initialParams).forEach(([key, value]) => {
          if (value !== undefined && value !== null && value !== "") {
            updated[key] = value;
          }
        });
        return updated;
      });
    }
  }, [initialParams, taskMeta, loading]);

  // ==========================================================================
  // 加载数据列
  // ==========================================================================

  useEffect(() => {
    const loadColumns = async () => {
      const dataFile = formValues.data_file;
      if (!dataFile) {
        setColumns([]);
        return;
      }

      try {
        setColumnsLoading(true);
        const preview = await sopService.previewData(dataFile, 10, sessionId);
        setColumns(preview.columns);
      } catch (err) {
        console.error("Failed to load columns:", err);
        setColumns([]);
      } finally {
        setColumnsLoading(false);
      }
    };

    loadColumns();
  }, [formValues.data_file, sessionId]);

  // ==========================================================================
  // 表单操作
  // ==========================================================================

  const updateValue = useCallback((name: string, value: any) => {
    setFormValues((prev) => ({ ...prev, [name]: value }));
  }, []);

  const handleReset = useCallback(() => {
    if (!taskMeta) return;
    const defaults: Record<string, any> = {};
    [...(taskMeta.required_params || []), ...(taskMeta.optional_params || [])].forEach(
      (param) => {
        if (param.default !== undefined) {
          defaults[param.name] = param.default;
        }
      }
    );
    setFormValues(defaults);
  }, [taskMeta]);

  const handleExecute = useCallback(() => {
    // 构建执行参数
    const params: Record<string, any> = { ...formValues };
    const filePath = formValues.data_file || "";

    // 清理空值和不显示的参数
    if (taskMeta) {
      const allParams = [
        ...(taskMeta.required_params || []),
        ...(taskMeta.optional_params || []),
      ];
      for (const param of allParams) {
        // 移除不显示的参数
        if (!shouldShowParam(param, formValues)) {
          delete params[param.name];
        }
        // 移除空字符串
        if (params[param.name] === "" && param.allow_empty) {
          delete params[param.name];
        }
      }
    }
    
    // 从params中移除data_file，因为它作为单独参数传递
    delete params.data_file;

    onExecute(params, filePath);
  }, [formValues, taskMeta, onExecute]);

  // ==========================================================================
  // 表单验证
  // ==========================================================================

  const isValid = useMemo(() => {
    if (!taskMeta) return false;
    if (!formValues.data_file) return false;

    // 检查必填参数
    for (const param of taskMeta.required_params || []) {
      if (!shouldShowParam(param, formValues)) continue;
      
      // 如果参数明确标记为非必填或允许为空，跳过验证
      if (param.required === false || param.allow_empty === true) continue;
      
      const value = formValues[param.name];
      if (value === undefined || value === null || value === "") {
        return false;
      }
    }

    return true;
  }, [taskMeta, formValues]);

  // ==========================================================================
  // 分离必填参数和高级参数（按阶段分组）
  // ==========================================================================

  const { requiredParams, advancedParams, stageGroupedAdvancedParams } = useMemo(() => {
    if (!taskMeta) return { requiredParams: [], advancedParams: [], stageGroupedAdvancedParams: [] };

    // 必填参数 = required_params 中 required !== false 且需要显示的
    const required = (taskMeta.required_params || []).filter((p) =>
      p.required !== false && shouldShowParam(p, formValues)
    );

    // 高级参数 = optional_params + required_params 中 required === false 的
    const optionalFromRequired = (taskMeta.required_params || []).filter((p) =>
      p.required === false && shouldShowParam(p, formValues)
    );
    const optional = (taskMeta.optional_params || []).filter((p) =>
      shouldShowParam(p, formValues)
    );
    
    const allAdvanced = [...optionalFromRequired, ...optional];
    
    // 构建阶段ID到阶段名称的映射
    const stageNameMap: Record<string, string> = {};
    (taskMeta.stages || []).forEach((s) => {
      stageNameMap[s.id] = s.name;
    });
    
    // 按阶段分组高级参数，保持阶段顺序
    const stageOrder = (taskMeta.stages || []).map(s => s.id);
    const stageGroups: Array<{ stageId: string; stageName: string; params: TaskParam[] }> = [];
    const generalParams: TaskParam[] = [];  // 无阶段标识的参数
    
    // 初始化每个阶段的参数数组
    const stageParamsMap: Record<string, TaskParam[]> = {};
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

    return { requiredParams: required, advancedParams: allAdvanced, stageGroupedAdvancedParams: stageGroups };
  }, [taskMeta, formValues]);

  // ==========================================================================
  // 渲染
  // ==========================================================================

  if (loading) {
    return (
      <Card className={cn(taskColor, className)}>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  if (!taskMeta) {
    return (
      <Card className={cn(taskColor, className)}>
        <CardContent className="flex items-center justify-center py-8 text-muted-foreground">
          加载任务配置失败
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={cn(taskColor, className)}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div
              className={cn(
                "w-8 h-8 rounded-lg flex items-center justify-center",
                taskIconBg
              )}
            >
              {taskIcon}
            </div>
            <div>
              <CardTitle className="text-base">
                {taskMeta.task_name}
              </CardTitle>
              <CardDescription className="text-xs">
                {taskMeta.description}
              </CardDescription>
            </div>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="h-8 w-8 p-0"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
        {/* 任务操作指引链接 */}
        <button
          type="button"
          onClick={() => setGuideDialogOpen(true)}
          className="inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 hover:underline mt-1 w-fit"
        >
          <BookOpen className="h-3.5 w-3.5" />
          任务操作指引
        </button>
      </CardHeader>

      {/* 操作指引弹窗 */}
      <TaskGuideDialog
        taskId={taskId}
        open={guideDialogOpen}
        onOpenChange={setGuideDialogOpen}
      />

      <CardContent className="space-y-4">
        {/* 数据文件选择 */}
        <div className="space-y-2">
          <Label className="flex items-center gap-2">
            <FileSpreadsheet className="h-4 w-4" />
            数据文件
          </Label>
          <Select
            value={formValues.data_file || ""}
            onValueChange={(v) => updateValue("data_file", v)}
          >
            <SelectTrigger>
              <SelectValue placeholder="选择数据文件" />
            </SelectTrigger>
            <SelectContent>
              {dataFiles.length === 0 ? (
                <div className="px-2 py-4 text-sm text-gray-500 text-center">
                  请先上传CSV或Excel文件
                </div>
              ) : (
                dataFiles.map((file) => (
                  <SelectItem key={file.path} value={file.path}>
                    {file.name}
                  </SelectItem>
                ))
              )}
            </SelectContent>
          </Select>
        </div>

        {/* 必填参数 */}
        {requiredParams.length > 0 && (
          <div className="space-y-4">
            {requiredParams.map((param) => (
              <DynamicParamRenderer
                key={param.name}
                param={param}
                value={formValues[param.name]}
                onChange={(v) => updateValue(param.name, v)}
                columns={columns}
                columnsLoading={columnsLoading}
                allValues={formValues}
              />
            ))}
          </div>
        )}

        {/* 高级参数折叠区（按阶段分组） */}
        {advancedParams.length > 0 && (
          <Collapsible open={advancedOpen} onOpenChange={setAdvancedOpen}>
            <CollapsibleTrigger asChild>
              <Button
                variant="ghost"
                className="w-full justify-between p-3 h-auto"
              >
                <div className="flex items-center gap-2">
                  <Settings2 className="h-4 w-4" />
                  <span>高级参数</span>
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
              {stageGroupedAdvancedParams.map((stageGroup) => (
                <StageParamGroup
                  key={stageGroup.stageId}
                  stageId={stageGroup.stageId}
                  stageName={stageGroup.stageName}
                  params={stageGroup.params}
                  formValues={formValues}
                  columns={columns}
                  columnsLoading={columnsLoading}
                  updateValue={updateValue}
                />
              ))}
            </CollapsibleContent>
          </Collapsible>
        )}

        {/* 操作按钮 */}
        <div className="flex items-center gap-2 pt-2">
          <Button
            variant="outline"
            onClick={handleReset}
            disabled={isExecuting}
            className="flex-1"
          >
            <RotateCcw className="h-4 w-4 mr-2" />
            重置
          </Button>
          <Button
            onClick={handleExecute}
            disabled={!isValid || isExecuting}
            className="flex-1 bg-blue-600 hover:bg-blue-700"
          >
            {isExecuting ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                执行中...
              </>
            ) : (
              <>
                <Play className="h-4 w-4 mr-2" />
                开始执行
              </>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export default TaskConfigPanel;
