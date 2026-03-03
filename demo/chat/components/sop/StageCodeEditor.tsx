"use client";

import React, { useState, useCallback, useEffect } from "react";
import Editor from "@monaco-editor/react";
import { cn } from "@/lib/utils";
import { API_URLS, getApiUrl } from "@/lib/config";
import { Button } from "@/components/ui/button";
import { Play, RotateCcw, Loader2, ChevronDown, ChevronUp, Copy, Check } from "lucide-react";

/**
 * 代码执行结果接口
 */
export interface CodeExecutionResult {
  success: boolean;
  result: string;
  error?: string;
}

/**
 * StageCodeEditor 组件属性
 */
export interface StageCodeEditorProps {
  /** 初始代码内容 */
  code: string;
  /** 代码变化回调 */
  onChange?: (code: string) => void;
  /** 执行完成回调 */
  onExecutionComplete?: (result: CodeExecutionResult) => void;
  /** 只读模式（Pipeline模式下为true） */
  readOnly?: boolean;
  /** 是否允许执行代码 */
  executable?: boolean;
  /** 代码语言，默认python */
  language?: string;
  /** 会话ID，用于代码执行 */
  sessionId: string;
  /** 阶段ID（可选，用于Task SOP模式） */
  stageId?: string;
  /** 编辑器高度，默认300px */
  height?: string | number;
  /** 是否显示输出区域 */
  showOutput?: boolean;
  /** 自定义类名 */
  className?: string;
  /** 深色模式 */
  isDarkMode?: boolean;
  /** 标题（可选） */
  title?: string;
  /** 显示重置按钮 */
  showReset?: boolean;
  /** 重置回调 */
  onReset?: () => void;
  /** 刷新工作区文件回调（执行后可能产生新文件） */
  onRefreshWorkspace?: () => void;
}

/**
 * 阶段代码编辑器组件
 * 
 * 复用原项目的 Monaco Editor 配置，支持两种使用场景：
 * 1. 原项目对话模式 - 编辑 AI 生成的代码并执行
 * 2. Task SOP Pipeline 模式 - 代码只读展示
 */
export function StageCodeEditor({
  code,
  onChange,
  onExecutionComplete,
  readOnly = false,
  executable = true,
  language = "python",
  sessionId,
  stageId,
  height = 300,
  showOutput = true,
  className,
  isDarkMode = false,
  title,
  showReset = false,
  onReset,
  onRefreshWorkspace,
}: StageCodeEditorProps) {
  const [editorContent, setEditorContent] = useState(code);
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionResult, setExecutionResult] = useState<string>("");
  const [outputExpanded, setOutputExpanded] = useState(true);
  const [copied, setCopied] = useState(false);
  const [editorHeight, setEditorHeight] = useState(60); // 编辑器占比百分比

  // 同步外部 code 变化
  useEffect(() => {
    setEditorContent(code);
  }, [code]);

  // 处理编辑器内容变化
  const handleEditorChange = useCallback((value: string | undefined) => {
    const newValue = value || "";
    setEditorContent(newValue);
    onChange?.(newValue);
  }, [onChange]);

  // 执行代码
  const executeCode = useCallback(async () => {
    if (!editorContent.trim() || !executable || isExecuting) return;

    setIsExecuting(true);
    setExecutionResult("");

    try {
      const response = await fetch(getApiUrl(API_URLS.EXECUTE_CODE), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          code: editorContent,
          session_id: sessionId,
          stage_id: stageId, // 可选，用于 Task SOP 模式
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setExecutionResult(data.result || "执行完成（无输出）");
        onExecutionComplete?.({
          success: true,
          result: data.result,
        });
        // 执行后刷新工作区文件
        onRefreshWorkspace?.();
      } else {
        const errorText = await response.text();
        setExecutionResult(`Error: ${errorText || "执行失败"}`);
        onExecutionComplete?.({
          success: false,
          result: "",
          error: errorText,
        });
      }
    } catch (error) {
      const errorMsg = `Error: ${error}`;
      setExecutionResult(errorMsg);
      onExecutionComplete?.({
        success: false,
        result: "",
        error: errorMsg,
      });
    } finally {
      setIsExecuting(false);
    }
  }, [editorContent, executable, isExecuting, sessionId, stageId, onExecutionComplete, onRefreshWorkspace]);

  // 复制代码
  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(editorContent);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  }, [editorContent]);

  // 处理重置
  const handleReset = useCallback(() => {
    setEditorContent(code);
    setExecutionResult("");
    onChange?.(code);
    onReset?.();
  }, [code, onChange, onReset]);

  // 拖拽调整编辑器高度
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    const startY = e.clientY;
    const startHeight = editorHeight;

    const handleMouseMove = (moveEvent: MouseEvent) => {
      const deltaY = moveEvent.clientY - startY;
      const containerHeight = (e.target as HTMLElement).parentElement?.clientHeight || 400;
      const deltaPercent = (deltaY / containerHeight) * 100;
      const newHeight = Math.min(Math.max(startHeight + deltaPercent, 30), 85);
      setEditorHeight(newHeight);
    };

    const handleMouseUp = () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
  }, [editorHeight]);

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
          <span className="text-xs font-mono text-gray-500 dark:text-gray-400">
            {title || language}
          </span>
          {readOnly && (
            <span className="px-1.5 py-0.5 text-xs bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded">
              只读
            </span>
          )}
        </div>
        
        <div className="flex items-center gap-1">
          {/* 复制按钮 */}
          <Button
            variant="ghost"
            size="sm"
            onClick={handleCopy}
            className="h-6 px-2 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
          </Button>

          {/* 重置按钮 */}
          {showReset && !readOnly && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleReset}
              disabled={editorContent === code}
              className="h-6 px-2 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 disabled:opacity-50"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </Button>
          )}

          {/* 执行按钮 */}
          {executable && !readOnly && (
            <Button
              size="sm"
              onClick={executeCode}
              disabled={!editorContent.trim() || isExecuting}
              className="h-6 px-3 text-xs bg-black text-white dark:bg-white dark:text-black hover:bg-gray-800 dark:hover:bg-gray-200"
            >
              {isExecuting ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" />
                  Running...
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5 mr-1" />
                  Run
                </>
              )}
            </Button>
          )}
        </div>
      </div>

      {/* 编辑器区域 */}
      <div 
        className="min-h-0 flex-1 flex flex-col"
        style={showOutput ? { height: `${editorHeight}%` } : undefined}
      >
        <Editor
          height="100%"
          defaultLanguage={language}
          value={editorContent}
          onChange={handleEditorChange}
          theme={isDarkMode ? "vs-dark" : "light"}
          options={{
            fontSize: 14,
            fontFamily: "var(--font-mono), 'Courier New', monospace",
            lineNumbers: "on",
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            automaticLayout: true,
            tabSize: 4,
            insertSpaces: true,
            wordWrap: "on",
            folding: true,
            lineDecorationsWidth: 10,
            lineNumbersMinChars: 3,
            glyphMargin: false,
            selectOnLineNumbers: true,
            roundedSelection: false,
            readOnly: readOnly,
            cursorStyle: "line",
            smoothScrolling: true,
            formatOnPaste: true,
            formatOnType: true,
            suggestOnTriggerCharacters: true,
            acceptSuggestionOnEnter: "on",
            tabCompletion: "on",
            scrollbar: {
              vertical: "visible",
              verticalScrollbarSize: 10,
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

      {/* 输出区域（可选） */}
      {showOutput && (
        <>
          {/* 拖拽分隔条 */}
          <div
            className="h-2 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 cursor-row-resize flex items-center justify-center group shrink-0"
            onMouseDown={handleMouseDown}
          >
            <div className="w-8 h-1 bg-gray-300 dark:bg-gray-600 rounded group-hover:bg-gray-400 dark:group-hover:bg-gray-500"></div>
          </div>

          {/* 输出面板 */}
          <div 
            className="min-h-0 border-t border-gray-200 dark:border-gray-700 flex flex-col bg-white dark:bg-gray-900"
            style={{ height: `${100 - editorHeight}%` }}
          >
            {/* 输出头部 */}
            <div 
              className="flex items-center justify-between px-3 py-1.5 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 cursor-pointer shrink-0"
              onClick={() => setOutputExpanded(!outputExpanded)}
            >
              <span className="text-xs text-gray-500 dark:text-gray-400 font-mono">
                Output
              </span>
              {outputExpanded ? (
                <ChevronDown className="w-4 h-4 text-gray-400" />
              ) : (
                <ChevronUp className="w-4 h-4 text-gray-400" />
              )}
            </div>

            {/* 输出内容 */}
            {outputExpanded && (
              <div className="flex-1 min-h-0 p-3 overflow-auto font-mono text-sm bg-white dark:bg-black text-gray-800 dark:text-gray-200">
                {executionResult ? (
                  <div>
                    <div className="text-gray-500 dark:text-gray-400 mb-1">
                      $ python main.py
                    </div>
                    <pre className="whitespace-pre-wrap text-gray-800 dark:text-gray-200">
                      {executionResult}
                    </pre>
                    <div className="flex items-center mt-2">
                      <span className="text-gray-500 dark:text-gray-400">$</span>
                      <span className="w-2 h-4 bg-gray-400 dark:bg-gray-500 ml-1 animate-pulse"></span>
                    </div>
                  </div>
                ) : (
                  <div className="text-gray-400 dark:text-gray-500 italic">
                    {executable && !readOnly 
                      ? "Run code to see output..." 
                      : "代码输出将在此显示"}
                  </div>
                )}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

export default StageCodeEditor;
