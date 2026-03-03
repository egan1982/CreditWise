"use client";

import React, { useState, useEffect, useRef, useMemo, useCallback } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Copy,
  Check,
  Code2,
  FileCode,
  ChevronDown,
  ChevronRight,
  Play,
  CheckCircle2,
  XCircle,
  Loader2,
  Download,
  Settings,
  Sparkles,
} from "lucide-react";
import { cn } from "@/lib/utils";

// =============================================================================
// 类型定义
// =============================================================================

export type CodeBlockType = 
  | "config"           // 任务配置摘要
  | "llm_extraction"   // LLM 参数推断（Chat入口）
  | "stage_start"      // 阶段开始
  | "stage_complete"   // 阶段完成
  | "stage_error"      // 阶段错误
  | "full_code";       // 完整等效代码

export type CodeBlockStatus = "pending" | "running" | "completed" | "failed";

export interface CodeBlock {
  id: string;
  type: CodeBlockType;
  stageId?: string;
  stageName?: string;
  content: string;
  status?: CodeBlockStatus;
  result?: string;        // 阶段结果摘要
  executionTime?: number; // 执行时间（毫秒）
  timestamp: number;
  copyable?: boolean;
}

export interface PipelineCodePanelProps {
  /** 代码块列表 */
  codeBlocks: CodeBlock[];
  /** 入口来源 */
  source?: "sop_ui" | "chat";
  /** 任务类型 */
  taskType?: string;
  /** 是否自动滚动到底部 */
  autoScroll?: boolean;
  /** 面板标题 */
  title?: string;
  /** 自定义样式 */
  className?: string;
  /** 是否显示行号 */
  showLineNumbers?: boolean;
  /** 是否显示时间戳 */
  showTimestamp?: boolean;
}

// =============================================================================
// 代码块类型配置
// =============================================================================

const BLOCK_TYPE_CONFIG: Record<CodeBlockType, {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  headerColor: string;
  borderColor: string;
}> = {
  config: {
    icon: Settings,
    label: "任务配置",
    headerColor: "bg-slate-700",
    borderColor: "border-slate-600",
  },
  llm_extraction: {
    icon: Sparkles,
    label: "LLM 参数推断",
    headerColor: "bg-purple-700",
    borderColor: "border-purple-600",
  },
  stage_start: {
    icon: Play,
    label: "阶段执行",
    headerColor: "bg-blue-700",
    borderColor: "border-blue-600",
  },
  stage_complete: {
    icon: CheckCircle2,
    label: "阶段完成",
    headerColor: "bg-green-700",
    borderColor: "border-green-600",
  },
  stage_error: {
    icon: XCircle,
    label: "阶段失败",
    headerColor: "bg-red-700",
    borderColor: "border-red-600",
  },
  full_code: {
    icon: FileCode,
    label: "完整等效代码",
    headerColor: "bg-emerald-700",
    borderColor: "border-emerald-600",
  },
};

// =============================================================================
// 简单语法高亮
// =============================================================================

function highlightPythonCode(code: string): React.ReactNode[] {
  const lines = code.split('\n');
  
  return lines.map((line, lineIndex) => {
    const trimmed = line.trim();
    
    // 注释行
    if (trimmed.startsWith('#')) {
      // 特殊注释（阶段标题）
      if (trimmed.startsWith('# ===') || trimmed.startsWith('# →')) {
        return (
          <div key={lineIndex} className="text-cyan-400 font-medium">
            {line}
          </div>
        );
      }
      return (
        <div key={lineIndex} className="text-gray-500 italic">
          {line}
        </div>
      );
    }
    
    // 空行
    if (!trimmed) {
      return <div key={lineIndex}>&nbsp;</div>;
    }
    
    // 简单关键字高亮
    let highlighted = line
      // 关键字
      .replace(
        /\b(import|from|def|class|if|elif|else|for|while|return|try|except|finally|with|as|in|is|not|and|or|True|False|None|async|await)\b/g,
        '<span class="text-purple-400">$1</span>'
      )
      // 字符串
      .replace(
        /(["'])(?:(?=(\\?))\2.)*?\1/g,
        '<span class="text-green-400">$&</span>'
      )
      // 数字
      .replace(
        /\b(\d+\.?\d*)\b/g,
        '<span class="text-orange-400">$1</span>'
      )
      // 函数调用
      .replace(
        /\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(/g,
        '<span class="text-yellow-300">$1</span>('
      );
    
    return (
      <div 
        key={lineIndex} 
        className="text-gray-300"
        dangerouslySetInnerHTML={{ __html: highlighted }}
      />
    );
  });
}

// =============================================================================
// 单个代码块组件
// =============================================================================

interface CodeBlockItemProps {
  block: CodeBlock;
  isExpanded: boolean;
  onToggle: () => void;
  showLineNumbers: boolean;
  showTimestamp: boolean;
  onCopy: (content: string) => void;
  copied: boolean;
}

function CodeBlockItem({
  block,
  isExpanded,
  onToggle,
  showLineNumbers,
  showTimestamp,
  onCopy,
  copied,
}: CodeBlockItemProps) {
  const config = BLOCK_TYPE_CONFIG[block.type];
  const Icon = config.icon;
  const lines = block.content.split('\n');
  
  // 状态图标
  const StatusIcon = useMemo(() => {
    if (block.status === "running") {
      return <Loader2 className="h-3 w-3 animate-spin text-blue-400" />;
    }
    if (block.status === "completed") {
      return <CheckCircle2 className="h-3 w-3 text-green-400" />;
    }
    if (block.status === "failed") {
      return <XCircle className="h-3 w-3 text-red-400" />;
    }
    return null;
  }, [block.status]);

  return (
    <div className={cn(
      "border rounded-lg overflow-hidden mb-3",
      config.borderColor,
      "bg-gray-900"
    )}>
      {/* 代码块头部 */}
      <div 
        className={cn(
          "flex items-center justify-between px-3 py-2 cursor-pointer",
          config.headerColor
        )}
        onClick={onToggle}
      >
        <div className="flex items-center gap-2">
          <Icon className="h-4 w-4 text-white/80" />
          <span className="text-sm font-medium text-white">
            {block.stageName || config.label}
          </span>
          {StatusIcon}
          {block.status && (
            <Badge 
              variant="outline" 
              className={cn(
                "text-[10px] px-1.5 py-0 h-4 border-white/30",
                block.status === "running" && "text-blue-300",
                block.status === "completed" && "text-green-300",
                block.status === "failed" && "text-red-300"
              )}
            >
              {block.status === "running" ? "执行中" : 
               block.status === "completed" ? "完成" : 
               block.status === "failed" ? "失败" : "等待"}
            </Badge>
          )}
        </div>
        
        <div className="flex items-center gap-2">
          {/* 执行时间 */}
          {block.executionTime && (
            <span className="text-xs text-white/60">
              {(block.executionTime / 1000).toFixed(1)}s
            </span>
          )}
          
          {/* 时间戳 */}
          {showTimestamp && (
            <span className="text-xs text-white/50">
              {new Date(block.timestamp).toLocaleTimeString()}
            </span>
          )}
          
          {/* 复制按钮 */}
          {block.copyable !== false && (
            <Button
              variant="ghost"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                onCopy(block.content);
              }}
              className="h-6 px-2 text-white/70 hover:text-white hover:bg-white/10"
            >
              {copied ? (
                <Check className="h-3 w-3 text-green-400" />
              ) : (
                <Copy className="h-3 w-3" />
              )}
            </Button>
          )}
          
          {/* 展开/折叠 */}
          {isExpanded ? (
            <ChevronDown className="h-4 w-4 text-white/70" />
          ) : (
            <ChevronRight className="h-4 w-4 text-white/70" />
          )}
        </div>
      </div>
      
      {/* 代码内容 */}
      {isExpanded && (
        <div className="overflow-auto max-h-[400px]">
          <div className="flex">
            {/* 行号 */}
            {showLineNumbers && (
              <div className="flex-shrink-0 py-2 px-2 text-right select-none bg-gray-800/50 border-r border-gray-700">
                {lines.map((_, i) => (
                  <div key={i} className="text-xs text-gray-600 leading-5 font-mono">
                    {i + 1}
                  </div>
                ))}
              </div>
            )}
            
            {/* 代码 */}
            <pre className="flex-1 py-2 px-3 text-sm font-mono leading-5 overflow-x-auto">
              <code>{highlightPythonCode(block.content)}</code>
            </pre>
          </div>
          
          {/* 结果摘要 */}
          {block.result && (
            <div className="px-3 py-2 border-t border-gray-700 bg-gray-800/30">
              <div className="text-xs text-gray-400 whitespace-pre-wrap font-mono">
                {block.result}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// 主组件
// =============================================================================

export function PipelineCodePanel({
  codeBlocks,
  source = "sop_ui",
  taskType,
  autoScroll = true,
  title = "执行代码",
  className,
  showLineNumbers = true,
  showTimestamp = false,
}: PipelineCodePanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [expandedBlocks, setExpandedBlocks] = useState<Set<string>>(new Set());
  const [copiedId, setCopiedId] = useState<string | null>(null);
  
  // 自动展开新的代码块
  useEffect(() => {
    if (codeBlocks.length > 0) {
      const latestBlock = codeBlocks[codeBlocks.length - 1];
      setExpandedBlocks(prev => {
        const next = new Set(prev);
        next.add(latestBlock.id);
        return next;
      });
    }
  }, [codeBlocks.length]);
  
  // 自动滚动到底部
  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [codeBlocks, autoScroll]);
  
  // 切换展开状态
  const toggleBlock = useCallback((id: string) => {
    setExpandedBlocks(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);
  
  // 复制代码
  const handleCopy = useCallback(async (content: string, id: string) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  }, []);
  
  // 导出所有代码
  const exportAllCode = useCallback(() => {
    const allCode = codeBlocks
      .map(block => block.content)
      .join('\n\n' + '='.repeat(60) + '\n\n');
    
    const blob = new Blob([allCode], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `pipeline-code-${taskType || 'task'}-${new Date().toISOString().slice(0, 10)}.py`;
    a.click();
    URL.revokeObjectURL(url);
  }, [codeBlocks, taskType]);
  
  // 统计信息
  const stats = useMemo(() => {
    const completed = codeBlocks.filter(b => b.status === "completed").length;
    const running = codeBlocks.filter(b => b.status === "running").length;
    const failed = codeBlocks.filter(b => b.status === "failed").length;
    return { completed, running, failed, total: codeBlocks.length };
  }, [codeBlocks]);

  // 空状态
  if (codeBlocks.length === 0) {
    return (
      <div className={cn("flex flex-col h-full bg-gray-900 rounded-lg", className)}>
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700">
          <div className="flex items-center gap-2">
            <Code2 className="h-4 w-4 text-gray-400" />
            <span className="text-sm font-medium text-gray-200">{title}</span>
          </div>
        </div>
        <div className="flex-1 flex items-center justify-center text-gray-500">
          <div className="text-center">
            <FileCode className="h-12 w-12 mx-auto mb-2 opacity-50" />
            <p className="text-sm">等待任务执行...</p>
            <p className="text-xs text-gray-600 mt-1">
              {source === "chat" ? "LLM 将解析您的请求并执行任务" : "启动任务后将展示执行代码"}
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("flex flex-col h-full bg-gray-900 rounded-lg overflow-hidden", className)}>
      {/* 头部 */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700 bg-gray-800/50">
        <div className="flex items-center gap-2">
          <Code2 className="h-4 w-4 text-blue-400" />
          <span className="text-sm font-medium text-gray-200">{title}</span>
          
          {/* 来源标签 */}
          {source === "chat" && (
            <Badge variant="outline" className="text-[10px] border-purple-500 text-purple-400">
              <Sparkles className="h-2.5 w-2.5 mr-1" />
              LLM 驱动
            </Badge>
          )}
          
          {/* 统计 */}
          <div className="flex items-center gap-1 ml-2">
            {stats.running > 0 && (
              <Badge variant="outline" className="text-[10px] border-blue-500 text-blue-400">
                {stats.running} 执行中
              </Badge>
            )}
            {stats.completed > 0 && (
              <Badge variant="outline" className="text-[10px] border-green-500 text-green-400">
                {stats.completed} 完成
              </Badge>
            )}
            {stats.failed > 0 && (
              <Badge variant="outline" className="text-[10px] border-red-500 text-red-400">
                {stats.failed} 失败
              </Badge>
            )}
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          {/* 导出按钮 */}
          <Button
            variant="ghost"
            size="sm"
            onClick={exportAllCode}
            className="h-7 px-2 text-gray-400 hover:text-white"
            title="导出所有代码"
          >
            <Download className="h-3.5 w-3.5 mr-1" />
            <span className="text-xs">导出</span>
          </Button>
        </div>
      </div>
      
      {/* 代码块列表 */}
      <div 
        ref={scrollRef}
        className="flex-1 overflow-auto p-3"
      >
        {codeBlocks.map((block) => (
          <CodeBlockItem
            key={block.id}
            block={block}
            isExpanded={expandedBlocks.has(block.id)}
            onToggle={() => toggleBlock(block.id)}
            showLineNumbers={showLineNumbers}
            showTimestamp={showTimestamp}
            onCopy={(content) => handleCopy(content, block.id)}
            copied={copiedId === block.id}
          />
        ))}
      </div>
      
      {/* 底部提示 */}
      <div className="px-4 py-2 border-t border-gray-700 bg-gray-800/30">
        <p className="text-xs text-gray-500">
          💡 代码展示 Pipeline 执行过程，完整等效代码可复制执行以复现结果
        </p>
      </div>
    </div>
  );
}

// =============================================================================
// Hook: 用于管理代码块状态
// =============================================================================

export function usePipelineCodeBlocks() {
  const [codeBlocks, setCodeBlocks] = useState<CodeBlock[]>([]);
  let blockIdCounter = useRef(0);
  
  // 添加任务配置块
  const addConfigBlock = useCallback((content: string) => {
    const block: CodeBlock = {
      id: `config-${++blockIdCounter.current}`,
      type: "config",
      content,
      timestamp: Date.now(),
    };
    setCodeBlocks(prev => [...prev, block]);
    return block.id;
  }, []);
  
  // 添加 LLM 推断块（Chat 入口）
  const addLLMExtractionBlock = useCallback((content: string) => {
    const block: CodeBlock = {
      id: `llm-${++blockIdCounter.current}`,
      type: "llm_extraction",
      content,
      timestamp: Date.now(),
    };
    setCodeBlocks(prev => [...prev, block]);
    return block.id;
  }, []);
  
  // 添加阶段开始块
  const addStageStartBlock = useCallback((stageId: string, stageName: string, pseudoCode: string) => {
    const block: CodeBlock = {
      id: `stage-${stageId}-${++blockIdCounter.current}`,
      type: "stage_start",
      stageId,
      stageName,
      content: pseudoCode,
      status: "running",
      timestamp: Date.now(),
    };
    setCodeBlocks(prev => [...prev, block]);
    return block.id;
  }, []);
  
  // 更新阶段状态为完成
  const updateStageComplete = useCallback((
    stageId: string, 
    result?: string, 
    executionTime?: number
  ) => {
    setCodeBlocks(prev => prev.map(block => {
      if (block.stageId === stageId && block.status === "running") {
        return {
          ...block,
          status: "completed" as CodeBlockStatus,
          result,
          executionTime,
        };
      }
      return block;
    }));
  }, []);
  
  // 更新阶段状态为失败
  const updateStageFailed = useCallback((stageId: string, error: string) => {
    setCodeBlocks(prev => prev.map(block => {
      if (block.stageId === stageId && block.status === "running") {
        return {
          ...block,
          status: "failed" as CodeBlockStatus,
          result: `错误: ${error}`,
        };
      }
      return block;
    }));
  }, []);
  
  // 添加完整等效代码块
  const addFullCodeBlock = useCallback((content: string) => {
    const block: CodeBlock = {
      id: `full-${++blockIdCounter.current}`,
      type: "full_code",
      content,
      copyable: true,
      timestamp: Date.now(),
    };
    setCodeBlocks(prev => [...prev, block]);
    return block.id;
  }, []);
  
  // 清空所有代码块
  const clearBlocks = useCallback(() => {
    setCodeBlocks([]);
  }, []);
  
  return {
    codeBlocks,
    addConfigBlock,
    addLLMExtractionBlock,
    addStageStartBlock,
    updateStageComplete,
    updateStageFailed,
    addFullCodeBlock,
    clearBlocks,
  };
}

export default PipelineCodePanel;
