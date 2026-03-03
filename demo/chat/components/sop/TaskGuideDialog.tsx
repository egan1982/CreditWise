"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Loader2, BookOpen, GripVertical, X, Minimize2, Maximize2 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { getApiUrl } from "@/lib/config";
import { cn } from "@/lib/utils";

// 任务类型与文档名称映射
const TASK_GUIDE_DOCS: Record<string, { title: string; docName: string }> = {
  rule_mining: {
    title: "规则挖掘操作指引",
    docName: "rule_mining_workflow",
  },
  scorecard_dev: {
    title: "评分卡开发操作指引",
    docName: "scorecard_dev_workflow",
  },
  // 后续可扩展更多任务类型
};

interface TaskGuideDialogProps {
  taskId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

// 默认面板位置和尺寸
const DEFAULT_POSITION = { x: 100, y: 80 };
const DEFAULT_SIZE = { width: 600, height: 500 };
const MIN_WIDTH = 400;
const MAX_WIDTH = 1200;
const MIN_HEIGHT = 300;

export function TaskGuideDialog({
  taskId,
  open,
  onOpenChange,
}: TaskGuideDialogProps) {
  const [content, setContent] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // 拖拽状态
  const [position, setPosition] = useState(DEFAULT_POSITION);
  const [isDragging, setIsDragging] = useState(false);
  const dragStartRef = useRef({ x: 0, y: 0 });
  
  // 调整大小状态
  const [size, setSize] = useState(DEFAULT_SIZE);
  const [isResizing, setIsResizing] = useState(false);
  const resizeStartRef = useRef({ x: 0, y: 0, width: 0, height: 0 });
  
  // 最小化状态
  const [isMinimized, setIsMinimized] = useState(false);
  
  const panelRef = useRef<HTMLDivElement>(null);

  const guideConfig = TASK_GUIDE_DOCS[taskId];

  // 加载文档内容
  useEffect(() => {
    if (!open || !guideConfig) return;

    const loadGuideContent = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const response = await fetch(getApiUrl(`/sop/docs/${guideConfig.docName}`));
        if (!response.ok) {
          throw new Error("文档加载失败");
        }
        const data = await response.json();
        
        const fullContent = data.content || "";
        const webUISection = extractWebUISection(fullContent);
        setContent(webUISection);
      } catch (err) {
        console.error("Failed to load guide:", err);
        setError("文档加载失败，请稍后重试");
      } finally {
        setLoading(false);
      }
    };

    loadGuideContent();
  }, [open, guideConfig]);

  // 拖拽处理
  const handleDragStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    setIsDragging(true);
    dragStartRef.current = { x: e.clientX - position.x, y: e.clientY - position.y };
  }, [position]);

  const handleDragMove = useCallback((e: MouseEvent) => {
    if (!isDragging) return;
    
    const newX = Math.max(0, Math.min(window.innerWidth - 100, e.clientX - dragStartRef.current.x));
    const newY = Math.max(0, Math.min(window.innerHeight - 50, e.clientY - dragStartRef.current.y));
    
    setPosition({ x: newX, y: newY });
  }, [isDragging]);

  const handleDragEnd = useCallback(() => {
    setIsDragging(false);
  }, []);

  // 调整大小处理
  const handleResizeStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    setIsResizing(true);
    resizeStartRef.current = {
      x: e.clientX,
      y: e.clientY,
      width: size.width,
      height: size.height,
    };
  }, [size]);

  const handleResizeMove = useCallback((e: MouseEvent) => {
    if (!isResizing) return;
    
    const deltaX = e.clientX - resizeStartRef.current.x;
    const deltaY = e.clientY - resizeStartRef.current.y;
    const direction = (resizeStartRef.current as any).direction || 'both';
    
    let newWidth = size.width;
    let newHeight = size.height;
    
    if (direction === 'horizontal' || direction === 'both') {
      newWidth = Math.max(MIN_WIDTH, Math.min(MAX_WIDTH, resizeStartRef.current.width + deltaX));
    }
    if (direction === 'vertical' || direction === 'both') {
      newHeight = Math.max(MIN_HEIGHT, resizeStartRef.current.height + deltaY);
    }
    
    setSize({ width: newWidth, height: newHeight });
  }, [isResizing, size.width, size.height]);

  const handleResizeEnd = useCallback(() => {
    setIsResizing(false);
  }, []);

  // 绑定全局拖拽事件
  useEffect(() => {
    if (isDragging) {
      window.addEventListener("mousemove", handleDragMove);
      window.addEventListener("mouseup", handleDragEnd);
      return () => {
        window.removeEventListener("mousemove", handleDragMove);
        window.removeEventListener("mouseup", handleDragEnd);
      };
    }
  }, [isDragging, handleDragMove, handleDragEnd]);

  // 绑定全局调整大小事件
  useEffect(() => {
    if (isResizing) {
      window.addEventListener("mousemove", handleResizeMove);
      window.addEventListener("mouseup", handleResizeEnd);
      return () => {
        window.removeEventListener("mousemove", handleResizeMove);
        window.removeEventListener("mouseup", handleResizeEnd);
      };
    }
  }, [isResizing, handleResizeMove, handleResizeEnd]);

  if (!guideConfig || !open) {
    return null;
  }

  return (
    <div
      ref={panelRef}
      className={cn(
        "fixed z-50 bg-background border rounded-lg shadow-xl flex flex-col",
        "transition-shadow duration-200",
        isDragging && "shadow-2xl",
        isMinimized && "h-auto"
      )}
      style={{
        left: position.x,
        top: position.y,
        width: size.width,
        height: isMinimized ? "auto" : size.height,
      }}
    >
      {/* 可拖拽的标题栏 */}
      <div
        className={cn(
          "flex items-center justify-between px-4 py-3 border-b shrink-0",
          "bg-gray-50 dark:bg-gray-900/50 rounded-t-lg",
          "cursor-move select-none"
        )}
        onMouseDown={handleDragStart}
      >
        <div className="flex items-center gap-2">
          <GripVertical className="h-4 w-4 text-gray-400" />
          <BookOpen className="h-5 w-5 text-blue-500" />
          <div>
            <h3 className="text-sm font-semibold">{guideConfig.title}</h3>
            <p className="text-xs text-muted-foreground">
              WebUI 模式下的完整操作流程说明
            </p>
          </div>
        </div>
        
        {/* 窗口控制按钮 */}
        <div className="flex items-center gap-1" onMouseDown={(e) => e.stopPropagation()}>
          <button
            onClick={() => setIsMinimized(!isMinimized)}
            className="p-1.5 rounded hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
            title={isMinimized ? "展开" : "最小化"}
          >
            {isMinimized ? (
              <Maximize2 className="h-4 w-4 text-gray-500" />
            ) : (
              <Minimize2 className="h-4 w-4 text-gray-500" />
            )}
          </button>
          <button
            onClick={() => onOpenChange(false)}
            className="p-1.5 rounded hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors"
            title="关闭"
          >
            <X className="h-4 w-4 text-gray-500 hover:text-red-500" />
          </button>
        </div>
      </div>

      {/* 内容区域 */}
      {!isMinimized && (
        <div className="flex-1 overflow-hidden relative">
          <ScrollArea className="h-full px-4 py-3">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
              </div>
            ) : error ? (
              <div className="text-center py-12 text-gray-500">{error}</div>
            ) : (
              <div className="prose prose-sm dark:prose-invert max-w-none pb-4">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    pre: ({ children }) => (
                      <pre className="bg-gray-100 dark:bg-gray-800 rounded-lg p-4 overflow-x-auto text-xs">
                        {children}
                      </pre>
                    ),
                    code: ({ children, className }) => {
                      const isInline = !className;
                      return isInline ? (
                        <code className="bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded text-xs">
                          {children}
                        </code>
                      ) : (
                        <code className={className}>{children}</code>
                      );
                    },
                    table: ({ children }) => (
                      <div className="overflow-x-auto">
                        <table className="min-w-full border-collapse text-sm">
                          {children}
                        </table>
                      </div>
                    ),
                    th: ({ children }) => (
                      <th className="border border-gray-300 dark:border-gray-600 px-3 py-2 bg-gray-50 dark:bg-gray-800 text-left font-medium">
                        {children}
                      </th>
                    ),
                    td: ({ children }) => (
                      <td className="border border-gray-300 dark:border-gray-600 px-3 py-2">
                        {children}
                      </td>
                    ),
                    h2: ({ children }) => (
                      <h2 className="text-lg font-semibold mt-6 mb-3 pb-2 border-b border-gray-200 dark:border-gray-700">
                        {children}
                      </h2>
                    ),
                    h3: ({ children }) => (
                      <h3 className="text-base font-medium mt-4 mb-2">
                        {children}
                      </h3>
                    ),
                    blockquote: ({ children }) => (
                      <blockquote className="border-l-4 border-blue-400 pl-4 py-1 my-3 bg-blue-50 dark:bg-blue-900/20 rounded-r">
                        {children}
                      </blockquote>
                    ),
                  }}
                >
                  {content}
                </ReactMarkdown>
              </div>
            )}
          </ScrollArea>

        </div>
      )}

      {/* 调整大小手柄 - 右边缘 */}
      {!isMinimized && (
        <div
          className="absolute top-12 right-0 w-2 h-[calc(100%-60px)] cursor-ew-resize hover:bg-blue-400/30 transition-colors"
          onMouseDown={(e) => {
            e.preventDefault();
            e.stopPropagation();
            setIsResizing(true);
            resizeStartRef.current = { x: e.clientX, y: e.clientY, width: size.width, height: size.height };
            // 标记为仅水平调整
            (resizeStartRef.current as any).direction = 'horizontal';
          }}
        />
      )}

      {/* 调整大小手柄 - 下边缘 */}
      {!isMinimized && (
        <div
          className="absolute bottom-0 left-4 w-[calc(100%-60px)] h-2 cursor-ns-resize hover:bg-blue-400/30 transition-colors"
          onMouseDown={(e) => {
            e.preventDefault();
            e.stopPropagation();
            setIsResizing(true);
            resizeStartRef.current = { x: e.clientX, y: e.clientY, width: size.width, height: size.height };
            (resizeStartRef.current as any).direction = 'vertical';
          }}
        />
      )}

      {/* 调整大小手柄 - 右下角 */}
      {!isMinimized && (
        <div
          className="absolute bottom-0 right-0 w-6 h-6 cursor-se-resize group z-10"
          onMouseDown={(e) => {
            e.preventDefault();
            e.stopPropagation();
            setIsResizing(true);
            resizeStartRef.current = { x: e.clientX, y: e.clientY, width: size.width, height: size.height };
            (resizeStartRef.current as any).direction = 'both';
          }}
        >
          <div className="absolute bottom-1 right-1 w-3 h-3 border-r-2 border-b-2 border-gray-300 dark:border-gray-600 group-hover:border-blue-400 transition-colors rounded-br" />
        </div>
      )}
    </div>
  );
}

/**
 * 提取文档中 WebUI 模式部分的内容（包含执行模式与智能入口章节）
 * 
 * 提取范围：从"执行模式与智能入口"或"两种使用方式"章节开始，到API编程模式章节之前结束
 * 这样可以包含LLM+SOP的完整操作流程说明
 */
function extractWebUISection(fullContent: string): string {
  // 查找开始位置（优先匹配"执行模式与智能入口"，以包含LLM+SOP操作流程）
  const startPatterns = [
    /## 执行模式与智能入口/,           // 优先：包含LLM智能入口的完整章节
    /### 两种使用方式/,                // 次优：两种使用方式介绍
    /# 🖥️ 使用方式一：WebUI/,         // 兜底：WebUI模式开始
    /# 使用方式一：WebUI/,
    /## WebUI 交互模式/,
  ];

  let startIndex = -1;
  for (const pattern of startPatterns) {
    const match = fullContent.match(pattern);
    if (match && match.index !== undefined) {
      startIndex = match.index;
      break;
    }
  }

  if (startIndex === -1) {
    // 未找到匹配的章节，返回全部内容
    return fullContent;
  }

  // 查找结束位置（API模式开始或文件末尾）
  const afterStart = fullContent.slice(startIndex);
  const endPatterns = [
    /\n# 🚀 使用方式二/,
    /\n# 使用方式二/,
    /\n# API/,
  ];

  let endIndex = fullContent.length;
  for (const pattern of endPatterns) {
    const match = afterStart.match(pattern);
    if (match && match.index !== undefined) {
      endIndex = startIndex + match.index;
      break;
    }
  }

  return fullContent.slice(startIndex, endIndex).trim();
}

export default TaskGuideDialog;
