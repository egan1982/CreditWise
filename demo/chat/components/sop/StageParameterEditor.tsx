"use client";

import React, { useState, useCallback, useEffect } from "react";
import Editor from "@monaco-editor/react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Save, RotateCcw, Check, AlertCircle } from "lucide-react";

/**
 * StageParameterEditor 组件属性
 */
export interface StageParameterEditorProps {
  /** 参数值（JSON对象） */
  params: Record<string, any>;
  /** 参数变化回调 */
  onChange?: (params: Record<string, any>) => void;
  /** 保存回调 */
  onSave?: (params: Record<string, any>) => Promise<void>;
  /** 只读模式 */
  readOnly?: boolean;
  /** 编辑器高度，默认200px */
  height?: string | number;
  /** 自定义类名 */
  className?: string;
  /** 深色模式 */
  isDarkMode?: boolean;
  /** 标题 */
  title?: string;
}

/**
 * 阶段参数编辑器组件
 * 
 * 使用 Monaco Editor 编辑 JSON 格式的参数
 * 后续可扩展为表单化编辑器
 */
export function StageParameterEditor({
  params,
  onChange,
  onSave,
  readOnly = false,
  height = 200,
  className,
  isDarkMode = false,
  title = "阶段参数",
}: StageParameterEditorProps) {
  const originalJson = JSON.stringify(params, null, 2);
  const [editorContent, setEditorContent] = useState(originalJson);
  const [parseError, setParseError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // 同步外部 params 变化
  useEffect(() => {
    const newJson = JSON.stringify(params, null, 2);
    setEditorContent(newJson);
    setHasChanges(false);
    setParseError(null);
  }, [params]);

  // 处理编辑器内容变化
  const handleEditorChange = useCallback((value: string | undefined) => {
    const newValue = value || "";
    setEditorContent(newValue);
    
    // 验证 JSON 格式
    try {
      const parsed = JSON.parse(newValue);
      setParseError(null);
      setHasChanges(JSON.stringify(parsed) !== JSON.stringify(params));
      onChange?.(parsed);
    } catch (e) {
      setParseError("JSON 格式错误");
      setHasChanges(true);
    }
  }, [params, onChange]);

  // 保存参数
  const handleSave = useCallback(async () => {
    if (parseError || !onSave || isSaving) return;

    try {
      const parsed = JSON.parse(editorContent);
      setIsSaving(true);
      await onSave(parsed);
      setHasChanges(false);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2000);
    } catch (e) {
      setParseError("保存失败");
    } finally {
      setIsSaving(false);
    }
  }, [editorContent, parseError, onSave, isSaving]);

  // 重置参数
  const handleReset = useCallback(() => {
    setEditorContent(originalJson);
    setParseError(null);
    setHasChanges(false);
  }, [originalJson]);

  return (
    <div 
      className={cn(
        "flex flex-col border rounded-lg overflow-hidden",
        "border-gray-200 dark:border-gray-700",
        "bg-white dark:bg-gray-900",
        className
      )}
      style={{ height: typeof height === "number" ? `${height}px` : height }}
    >
      {/* 头部工具栏 */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-gray-600 dark:text-gray-400">
            {title}
          </span>
          {readOnly && (
            <span className="px-1.5 py-0.5 text-xs bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded">
              只读
            </span>
          )}
          {parseError && (
            <span className="flex items-center gap-1 px-1.5 py-0.5 text-xs bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 rounded">
              <AlertCircle className="w-3 h-3" />
              {parseError}
            </span>
          )}
          {hasChanges && !parseError && (
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
        
        {!readOnly && (
          <div className="flex items-center gap-1">
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
                disabled={!hasChanges || !!parseError || isSaving}
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
          </div>
        )}
      </div>

      {/* 编辑器区域 */}
      <div className="flex-1 min-h-0">
        <Editor
          height="100%"
          defaultLanguage="json"
          value={editorContent}
          onChange={handleEditorChange}
          theme={isDarkMode ? "vs-dark" : "light"}
          options={{
            fontSize: 13,
            fontFamily: "var(--font-mono), 'Courier New', monospace",
            lineNumbers: "on",
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            automaticLayout: true,
            tabSize: 2,
            insertSpaces: true,
            wordWrap: "on",
            folding: true,
            lineDecorationsWidth: 10,
            lineNumbersMinChars: 3,
            glyphMargin: false,
            readOnly: readOnly,
            cursorStyle: "line",
            smoothScrolling: true,
            formatOnPaste: true,
            formatOnType: true,
            scrollbar: {
              vertical: "visible",
              verticalScrollbarSize: 8,
            },
          }}
          loading={
            <div className="flex items-center justify-center h-full">
              <div className="flex items-center gap-2 text-muted-foreground">
                <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                <span className="text-sm">加载编辑器...</span>
              </div>
            </div>
          }
        />
      </div>
    </div>
  );
}

export default StageParameterEditor;
