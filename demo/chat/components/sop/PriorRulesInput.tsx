/**
 * P2-7: 先验规则增强输入组件
 * 
 * 支持三种输入模式：
 * 1. 手动输入（textarea，兼容现有功能）
 * 2. 上传 CSV 文件（结构化/表达式格式，自动识别）
 * 3. 从工作区选择 CSV 文件（方案 B，直接选择 session 目录下的文件）
 * 
 * 三级校验策略：
 * - L1 硬拒：非 CSV / 无法解析 / 0 条规则 / 格式无法识别 → 红色错误 + 模板下载
 * - L2 警告：部分规则列名不存在 → 黄色警告标红具体规则（全量保留不剔除）
 * - L3 通过：全部列名匹配 → 绿色提示
 */

import React, { useState, useCallback, useRef, useEffect } from "react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Upload,
  Download,
  CheckCircle,
  AlertCircle,
  AlertTriangle,
  FileText,
  FolderOpen,
  X,
  Loader2,
  Info,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { getApiUrl } from "@/lib/config";

// =============================================================================
// 类型定义
// =============================================================================

interface ParsedRule {
  rule_id: string;
  rule_name: string;
  expression: string;
  feature?: string;
  operator?: string;
  threshold?: string | number;
  mode: "structured" | "expression";
  source: "csv" | "text";
  valid?: boolean;
  missing_columns?: string[];
}

/** 校验级别 */
type ValidationLevel = "L1_reject" | "L2_warning" | "L3_pass" | "L3_no_dataset";

interface ValidationResult {
  level: ValidationLevel;
  message: string;
  total: number;
  valid: number;
  invalid: number;
}

interface WorkspaceFileItem {
  name: string;
  size: number;
  extension: string;
}

interface PriorRulesInputProps {
  /** 当前值（表达式文本，每行一条） */
  value: string;
  /** 值变更回调 */
  onChange: (value: string) => void;
  /** 禁用状态 */
  disabled?: boolean;
  /** 会话ID（用于列名校验 + 工作区文件列表） */
  sessionId?: string;
  /** 数据文件路径（用于列名校验） */
  dataFile?: string;
  /** 参数描述 */
  description?: string;
  /** placeholder */
  placeholder?: string;
}

// =============================================================================
// CSV 模板
// =============================================================================

const TEMPLATES = {
  structured: {
    name: "结构化规则模板",
    filename: "prior_rules_template_structured.csv",
    content:
      "rule_id,rule_name,feature,operator,threshold,direction\nR001,高风险年龄,age,>=,60,reject\nR002,低收入拒绝,income,<,3000,reject\nR003,高负债率,debt_ratio,>=,0.7,reject\nR004,多头借贷,loan_count,>,5,reject\nR005,低信用分,credit_score,<,550,reject",
  },
  expression: {
    name: "表达式规则模板",
    filename: "prior_rules_template_expression.csv",
    content:
      "rule_id,rule_name,expression\nR001,高风险年龄,(age >= 60)\nR002,低收入拒绝,(income < 3000)\nR003,高负债且多头,(debt_ratio >= 0.7) & (loan_count > 5)\nR004,年轻或低信用,(age < 25) | (credit_score < 550)",
  },
};

// =============================================================================
// 组件
// =============================================================================

export function PriorRulesInput({
  value,
  onChange,
  disabled = false,
  sessionId,
  dataFile,
  description,
  placeholder = "每行一条规则表达式，例如：\n(age > 30)\n(income < 5000)",
}: PriorRulesInputProps) {
  const [inputMode, setInputMode] = useState<"text" | "file" | "workspace">("text");
  const [parsedRules, setParsedRules] = useState<ParsedRule[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadedFileName, setUploadedFileName] = useState<string | null>(null);
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // 工作区文件列表
  const [workspaceFiles, setWorkspaceFiles] = useState<WorkspaceFileItem[]>([]);
  const [wsLoading, setWsLoading] = useState(false);

  // =========================================================================
  // 加载工作区 CSV 文件列表
  // =========================================================================

  useEffect(() => {
    if (inputMode !== "workspace" || !sessionId) return;
    
    const loadFiles = async () => {
      setWsLoading(true);
      try {
        const res = await fetch(getApiUrl(`/workspace/files?session_id=${encodeURIComponent(sessionId)}`));
        if (res.ok) {
          const data = await res.json();
          const csvFiles = (data.files || []).filter(
            (f: WorkspaceFileItem) => f.extension === ".csv"
          );
          setWorkspaceFiles(csvFiles);
        }
      } catch {
        setWorkspaceFiles([]);
      } finally {
        setWsLoading(false);
      }
    };
    loadFiles();
  }, [inputMode, sessionId]);

  // =========================================================================
  // 核心解析逻辑（文件上传 + 工作区选择共用）
  // =========================================================================

  const parseAndValidate = useCallback(
    async (formData: FormData) => {
      setIsUploading(true);
      setUploadError(null);
      setValidationResult(null);

      try {
        const response = await fetch(getApiUrl("/sop/prior-rules/parse"), {
          method: "POST",
          body: formData,
        });

        if (!response.ok) {
          throw new Error(`解析失败 (${response.status})`);
        }

        const result = await response.json();

        // L1 硬拒：后端返回 errors
        if (result.errors && result.errors.length > 0 && (!result.rules || result.rules.length === 0)) {
          setUploadError(result.errors.join("\n"));
          setParsedRules([]);
          onChange("");
          setValidationResult({
            level: "L1_reject",
            message: result.errors.join("; "),
            total: 0, valid: 0, invalid: 0,
          });
          return;
        }

        if (result.success && result.rules) {
          let rules: ParsedRule[] = result.rules;

          // 处理校验结果
          if (result.validation && !result.validation.error) {
            const details = result.validation.details || [];
            rules = rules.map((rule: ParsedRule, idx: number) => ({
              ...rule,
              valid: details[idx]?.valid ?? true,
              missing_columns: details[idx]?.missing_columns ?? [],
            }));

            const { total, valid, invalid } = result.validation;

            if (invalid > 0 && valid === 0) {
              // 全部不匹配 → L1 硬拒
              setValidationResult({
                level: "L1_reject",
                message: `所有 ${total} 条规则引用的特征均不存在于数据集中`,
                total, valid, invalid,
              });
            } else if (invalid > 0) {
              // 部分不匹配 → L2 警告（全量保留）
              setValidationResult({
                level: "L2_warning",
                message: `${invalid} 条规则引用了数据集中不存在的特征，执行时可能无效`,
                total, valid, invalid,
              });
            } else {
              // 全部匹配 → L3 通过
              setValidationResult({
                level: "L3_pass",
                message: `全部 ${total} 条规则校验通过`,
                total, valid, invalid,
              });
            }
          } else if (!sessionId || !dataFile) {
            // 无数据集信息，跳过校验
            setValidationResult({
              level: "L3_no_dataset",
              message: "未关联数据集，跳过列名校验（规则有效性将在执行时验证）",
              total: rules.length, valid: rules.length, invalid: 0,
            });
          }

          setParsedRules(rules);
          setUploadError(null);

          // L1 全部不匹配时不传表达式给 Pipeline
          if (result.validation && result.validation.valid === 0 && result.validation.invalid > 0) {
            onChange("");
          } else {
            const expressions = (result.expressions as string[]).join("\n");
            onChange(expressions);
          }
        } else {
          setUploadError(result.errors?.join("; ") || "解析失败：未知错误");
        }
      } catch (error) {
        setUploadError(error instanceof Error ? error.message : "文件解析失败");
      } finally {
        setIsUploading(false);
      }
    },
    [onChange, sessionId, dataFile]
  );

  // =========================================================================
  // 文件上传处理
  // =========================================================================

  const handleFileUpload = useCallback(
    async (file: File) => {
      // L1: 非 CSV 文件直接拒绝
      if (!file.name.toLowerCase().endsWith(".csv")) {
        setUploadError("仅支持 CSV 格式文件，请使用模板");
        setValidationResult({
          level: "L1_reject",
          message: "文件格式不正确，仅支持 .csv",
          total: 0, valid: 0, invalid: 0,
        });
        return;
      }

      setUploadedFileName(file.name);
      const formData = new FormData();
      formData.append("file", file);
      if (sessionId) formData.append("session_id", sessionId);
      if (dataFile) formData.append("data_file", dataFile);
      await parseAndValidate(formData);
    },
    [parseAndValidate, sessionId, dataFile]
  );

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFileUpload(file);
      if (fileInputRef.current) fileInputRef.current.value = "";
    },
    [handleFileUpload]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const file = e.dataTransfer.files?.[0];
      if (file) handleFileUpload(file);
    },
    [handleFileUpload]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
  }, []);

  // =========================================================================
  // 工作区文件选择
  // =========================================================================

  const handleWorkspaceFileSelect = useCallback(
    async (fileName: string) => {
      setUploadedFileName(fileName);
      // 从工作区选择时直接传 text 参数（后端从工作区读取文件内容）
      // 但当前 API 只接受 file upload 或 text，需要先读取文件内容
      // 最简方案：用 fetch 下载文件再作为 File 上传
      try {
        setIsUploading(true);
        const downloadUrl = getApiUrl(
          `/workspace/download/${encodeURIComponent(sessionId || "default")}/${encodeURIComponent(fileName)}`
        );
        const res = await fetch(downloadUrl);
        if (!res.ok) throw new Error("文件下载失败");
        const blob = await res.blob();
        const file = new File([blob], fileName, { type: "text/csv" });
        
        const formData = new FormData();
        formData.append("file", file);
        if (sessionId) formData.append("session_id", sessionId);
        if (dataFile) formData.append("data_file", dataFile);
        await parseAndValidate(formData);
      } catch (error) {
        setUploadError(error instanceof Error ? error.message : "文件读取失败");
        setIsUploading(false);
      }
    },
    [sessionId, dataFile, parseAndValidate]
  );

  // =========================================================================
  // 文本输入处理
  // =========================================================================

  const handleTextChange = useCallback(
    (text: string) => {
      onChange(text);
      const lines = text.split("\n").filter((l) => l.trim() && !l.trim().startsWith("#"));
      setParsedRules(
        lines.map((line, idx) => ({
          rule_id: `R${idx + 1}`,
          rule_name: `规则${idx + 1}`,
          expression: line.trim(),
          mode: "expression" as const,
          source: "text" as const,
        }))
      );
      setValidationResult(null);
      setUploadError(null);
    },
    [onChange]
  );

  // =========================================================================
  // 模板下载
  // =========================================================================

  const downloadTemplate = useCallback(
    (type: "structured" | "expression") => {
      const template = TEMPLATES[type];
      const bom = "\uFEFF";
      const blob = new Blob([bom + template.content], {
        type: "text/csv;charset=utf-8",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = template.filename;
      a.click();
      URL.revokeObjectURL(url);
    },
    []
  );

  // =========================================================================
  // 清除
  // =========================================================================

  const clearUpload = useCallback(() => {
    setParsedRules([]);
    setUploadedFileName(null);
    setUploadError(null);
    setValidationResult(null);
    onChange("");
  }, [onChange]);

  // =========================================================================
  // 渲染
  // =========================================================================

  const ruleCount = parsedRules.length;
  const structuredCount = parsedRules.filter((r) => r.mode === "structured").length;
  const expressionCount = ruleCount - structuredCount;

  return (
    <div className="space-y-3">
      {description && (
        <p className="text-xs text-muted-foreground">{description}</p>
      )}

      {/* 模式选择 */}
      <Tabs
        value={inputMode}
        onValueChange={(v) => setInputMode(v as "text" | "file" | "workspace")}
      >
        <TabsList className="h-8">
          <TabsTrigger value="text" className="text-xs px-3 h-7">
            手动输入
          </TabsTrigger>
          <TabsTrigger value="file" className="text-xs px-3 h-7">
            上传文件
          </TabsTrigger>
          {sessionId && (
            <TabsTrigger value="workspace" className="text-xs px-3 h-7">
              <FolderOpen className="h-3 w-3 mr-1" />
              工作区
            </TabsTrigger>
          )}
        </TabsList>

        {/* 手动输入 */}
        <TabsContent value="text" className="mt-2">
          <Textarea
            value={value}
            onChange={(e) => handleTextChange(e.target.value)}
            placeholder={placeholder}
            rows={5}
            disabled={disabled}
            className="font-mono text-xs"
          />
        </TabsContent>

        {/* 文件上传 */}
        <TabsContent value="file" className="mt-2 space-y-2">
          {!uploadedFileName ? (
            <div
              className={cn(
                "border-2 border-dashed rounded-lg p-4 text-center transition-colors",
                isUploading
                  ? "border-blue-300 bg-blue-50/50 dark:bg-blue-900/10"
                  : "border-gray-200 dark:border-gray-700 hover:border-blue-300"
              )}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
            >
              {isUploading ? (
                <div className="flex items-center justify-center gap-2 text-sm text-blue-600">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  解析中...
                </div>
              ) : (
                <>
                  <Upload className="mx-auto h-6 w-6 text-muted-foreground mb-1.5" />
                  <p className="text-xs text-muted-foreground mb-2">
                    拖拽 CSV 文件到此处，或点击选择
                  </p>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".csv"
                    onChange={handleFileChange}
                    className="hidden"
                    id="prior-rules-upload"
                    disabled={disabled}
                  />
                  <Button variant="outline" size="sm" asChild disabled={disabled}>
                    <label htmlFor="prior-rules-upload" className="cursor-pointer">
                      选择文件
                    </label>
                  </Button>
                </>
              )}
            </div>
          ) : (
            <div className="flex items-center gap-2 p-2 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
              <FileText className="h-4 w-4 text-green-600" />
              <span className="text-xs text-green-700 dark:text-green-300 flex-1">
                {uploadedFileName}
              </span>
              <Button variant="ghost" size="sm" className="h-6 w-6 p-0" onClick={clearUpload}>
                <X className="h-3 w-3" />
              </Button>
            </div>
          )}

          {/* 模板下载 */}
          <div className="flex gap-1.5">
            <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => downloadTemplate("structured")}>
              <Download className="h-3 w-3 mr-1" />
              简单规则模板
            </Button>
            <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => downloadTemplate("expression")}>
              <Download className="h-3 w-3 mr-1" />
              复杂规则模板
            </Button>
          </div>
        </TabsContent>

        {/* 从工作区选择 */}
        {sessionId && (
          <TabsContent value="workspace" className="mt-2 space-y-2">
            {uploadedFileName ? (
              <div className="flex items-center gap-2 p-2 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
                <FolderOpen className="h-4 w-4 text-green-600" />
                <span className="text-xs text-green-700 dark:text-green-300 flex-1">
                  已选择: {uploadedFileName}
                </span>
                <Button variant="ghost" size="sm" className="h-6 w-6 p-0" onClick={clearUpload}>
                  <X className="h-3 w-3" />
                </Button>
              </div>
            ) : wsLoading ? (
              <div className="flex items-center justify-center gap-2 py-4 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                加载工作区文件...
              </div>
            ) : workspaceFiles.length === 0 ? (
              <div className="text-center py-4 text-xs text-muted-foreground">
                工作区中没有 CSV 文件
              </div>
            ) : (
              <div className="border rounded-lg max-h-32 overflow-y-auto">
                {workspaceFiles.map((f) => (
                  <button
                    key={f.name}
                    className="flex items-center gap-2 w-full px-3 py-1.5 text-xs hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors border-b last:border-b-0"
                    onClick={() => handleWorkspaceFileSelect(f.name)}
                    disabled={disabled || isUploading}
                  >
                    <FileText className="h-3.5 w-3.5 text-gray-400 shrink-0" />
                    <span className="truncate flex-1 text-left">{f.name}</span>
                    <span className="text-muted-foreground shrink-0">
                      {f.size > 1024 ? `${(f.size / 1024).toFixed(1)}KB` : `${f.size}B`}
                    </span>
                  </button>
                ))}
              </div>
            )}

            {isUploading && (
              <div className="flex items-center justify-center gap-2 text-sm text-blue-600">
                <Loader2 className="h-4 w-4 animate-spin" />
                解析中...
              </div>
            )}
          </TabsContent>
        )}
      </Tabs>

      {/* 三级校验反馈 */}
      {validationResult && (
        <div
          className={cn("flex items-start gap-2 px-3 py-2 rounded-lg text-xs", {
            "bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800":
              validationResult.level === "L1_reject",
            "bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-800":
              validationResult.level === "L2_warning",
            "bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300 border border-green-200 dark:border-green-800":
              validationResult.level === "L3_pass",
            "bg-gray-50 dark:bg-gray-900/20 text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-700":
              validationResult.level === "L3_no_dataset",
          })}
        >
          {validationResult.level === "L1_reject" && <AlertCircle className="h-3.5 w-3.5 shrink-0 mt-0.5" />}
          {validationResult.level === "L2_warning" && <AlertTriangle className="h-3.5 w-3.5 shrink-0 mt-0.5" />}
          {validationResult.level === "L3_pass" && <CheckCircle className="h-3.5 w-3.5 shrink-0 mt-0.5" />}
          {validationResult.level === "L3_no_dataset" && <Info className="h-3.5 w-3.5 shrink-0 mt-0.5" />}
          <div className="flex-1">
            <span>{validationResult.message}</span>
            {validationResult.level === "L1_reject" && (
              <div className="flex gap-1.5 mt-1.5">
                <Button variant="outline" size="sm" className="h-6 text-[10px] px-2" onClick={() => downloadTemplate("structured")}>
                  <Download className="h-2.5 w-2.5 mr-1" />
                  下载模板
                </Button>
                <Button variant="outline" size="sm" className="h-6 text-[10px] px-2" onClick={clearUpload}>
                  重新选择
                </Button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 上传错误（非校验类错误） */}
      {uploadError && !validationResult && (
        <div className="flex items-center gap-1.5 text-xs text-red-500">
          <AlertCircle className="h-3.5 w-3.5" />
          {uploadError}
        </div>
      )}

      {/* 解析预览 */}
      {ruleCount > 0 && validationResult?.level !== "L1_reject" && (
        <div className="border rounded-lg overflow-hidden">
          <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-50 dark:bg-gray-900/30 border-b">
            <CheckCircle className="h-3.5 w-3.5 text-green-500" />
            <span className="text-xs">
              已解析 {ruleCount} 条规则
              {structuredCount > 0 && expressionCount > 0 && (
                <span className="text-muted-foreground ml-1">
                  ({structuredCount} 结构化, {expressionCount} 表达式)
                </span>
              )}
            </span>
            {validationResult && validationResult.invalid > 0 && (
              <Badge variant="destructive" className="text-[10px] h-4 px-1.5">
                {validationResult.invalid} 个特征不匹配
              </Badge>
            )}
          </div>

          <div className="max-h-32 overflow-y-auto">
            {parsedRules.map((rule) => (
              <div
                key={rule.rule_id}
                className={cn(
                  "flex items-center gap-2 px-3 py-1 text-xs border-b last:border-b-0",
                  rule.valid === false && "bg-amber-50/50 dark:bg-amber-900/10"
                )}
              >
                {rule.valid !== false ? (
                  <CheckCircle className="h-3 w-3 text-green-500 shrink-0" />
                ) : (
                  <AlertTriangle className="h-3 w-3 text-amber-500 shrink-0" />
                )}
                <span className="font-mono text-muted-foreground w-8 shrink-0">
                  {rule.rule_id}
                </span>
                <span className="truncate flex-1 font-mono">
                  {rule.expression}
                </span>
                {rule.valid === false && rule.missing_columns && rule.missing_columns.length > 0 && (
                  <span className="text-amber-600 dark:text-amber-400 text-[10px] shrink-0">
                    缺: {rule.missing_columns.join(", ")}
                  </span>
                )}
                <Badge variant="outline" className="text-[9px] h-4 px-1 shrink-0">
                  {rule.mode === "structured" ? "结构化" : "表达式"}
                </Badge>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
