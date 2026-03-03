"use client";

import React, { useMemo } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Copy,
  Check,
  Code2,
  FileCode,
  ChevronLeft,
} from "lucide-react";
import { cn } from "@/lib/utils";

// =============================================================================
// 类型定义
// =============================================================================

interface StageCodePreviewProps {
  stageId: string;
  stageName: string;
  code: string;
  status?: string;
  onBack?: () => void;
  className?: string;
}

// =============================================================================
// 语法高亮配置
// =============================================================================

interface TokenStyle {
  pattern: RegExp;
  className: string;
}

const TOKEN_STYLES: TokenStyle[] = [
  // 注释
  { pattern: /#.*$/gm, className: "text-gray-500 italic" },
  // 字符串（双引号）
  { pattern: /"[^"]*"/g, className: "text-green-400" },
  // 字符串（单引号）
  { pattern: /'[^']*'/g, className: "text-green-400" },
  // f-string
  { pattern: /f"[^"]*"/g, className: "text-green-400" },
  { pattern: /f'[^']*'/g, className: "text-green-400" },
  // 关键字
  { 
    pattern: /\b(import|from|def|class|if|elif|else|for|while|return|yield|try|except|finally|with|as|in|is|not|and|or|True|False|None|print)\b/g, 
    className: "text-purple-400 font-medium" 
  },
  // 内置函数
  { 
    pattern: /\b(len|range|str|int|float|list|dict|set|tuple|type|isinstance|enumerate|zip|map|filter|sorted|sum|min|max|abs|round)\b/g, 
    className: "text-cyan-400" 
  },
  // 数字
  { pattern: /\b\d+\.?\d*\b/g, className: "text-orange-400" },
  // 函数调用
  { pattern: /\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(/g, className: "text-yellow-300" },
];

// =============================================================================
// 简单语法高亮组件
// =============================================================================

function highlightCode(code: string): React.ReactNode[] {
  // 简单的行级高亮处理
  const lines = code.split('\n');
  
  return lines.map((line, lineIndex) => {
    // 检测注释行
    const trimmed = line.trim();
    if (trimmed.startsWith('#')) {
      return (
        <div key={lineIndex} className="text-gray-500 italic">
          {line}
        </div>
      );
    }
    
    // 其他行进行简单高亮
    let highlighted = line;
    
    // 关键字高亮
    const keywords = ['import', 'from', 'def', 'class', 'if', 'elif', 'else', 'for', 'while', 'return', 'try', 'except', 'with', 'as', 'in', 'is', 'not', 'and', 'or', 'True', 'False', 'None', 'print'];
    
    return (
      <div key={lineIndex} className="whitespace-pre">
        {line || '\u00A0'}
      </div>
    );
  });
}

// =============================================================================
// 主组件
// =============================================================================

export function StageCodePreview({
  stageId,
  stageName,
  code,
  status,
  onBack,
  className,
}: StageCodePreviewProps) {
  const [copied, setCopied] = React.useState(false);

  // 复制代码
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  // 代码行数
  const lineCount = useMemo(() => code.split('\n').length, [code]);

  if (!code) {
    return (
      <div className={cn("flex flex-col h-full bg-gray-900", className)}>
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700">
          <div className="flex items-center gap-2">
            {onBack && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onBack}
                className="h-7 w-7 p-0 text-gray-400 hover:text-white"
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
            )}
            <Code2 className="h-4 w-4 text-gray-400" />
            <span className="text-sm font-medium text-gray-200">{stageName}</span>
          </div>
        </div>
        <div className="flex-1 flex items-center justify-center text-gray-500">
          <div className="text-center">
            <FileCode className="h-12 w-12 mx-auto mb-2 opacity-50" />
            <p className="text-sm">暂无代码</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("flex flex-col h-full bg-gray-900", className)}>
      {/* 头部 */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700 bg-gray-800/50">
        <div className="flex items-center gap-2">
          {onBack && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onBack}
              className="h-7 w-7 p-0 text-gray-400 hover:text-white"
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
          )}
          <Code2 className="h-4 w-4 text-blue-400" />
          <span className="text-sm font-medium text-gray-200">{stageName}</span>
          {status && (
            <Badge 
              variant="outline" 
              className={cn(
                "text-xs",
                status === "completed" && "border-green-500 text-green-400",
                status === "running" && "border-blue-500 text-blue-400",
                status === "failed" && "border-red-500 text-red-400"
              )}
            >
              {status === "completed" ? "已完成" : status === "running" ? "执行中" : status}
            </Badge>
          )}
        </div>
        
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">{lineCount} 行</span>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleCopy}
            className="h-7 px-2 text-gray-400 hover:text-white"
          >
            {copied ? (
              <>
                <Check className="h-3.5 w-3.5 mr-1 text-green-400" />
                <span className="text-xs">已复制</span>
              </>
            ) : (
              <>
                <Copy className="h-3.5 w-3.5 mr-1" />
                <span className="text-xs">复制</span>
              </>
            )}
          </Button>
        </div>
      </div>

      {/* 代码内容 */}
      <div className="flex-1 overflow-auto">
        <div className="flex">
          {/* 行号 */}
          <div className="flex-shrink-0 py-3 px-2 text-right select-none bg-gray-800/30 border-r border-gray-700">
            {code.split('\n').map((_, i) => (
              <div key={i} className="text-xs text-gray-600 leading-5 font-mono">
                {i + 1}
              </div>
            ))}
          </div>
          
          {/* 代码 */}
          <pre className="flex-1 py-3 px-4 text-sm font-mono text-gray-300 leading-5 overflow-x-auto">
            <code>{highlightCode(code)}</code>
          </pre>
        </div>
      </div>

      {/* 底部提示 */}
      <div className="px-4 py-2 border-t border-gray-700 bg-gray-800/30">
        <p className="text-xs text-gray-500">
          💡 此代码展示了Pipeline在此阶段执行的逻辑（只读模式）
        </p>
      </div>
    </div>
  );
}

export default StageCodePreview;
