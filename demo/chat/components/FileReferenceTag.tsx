"use client";

import { X, FileText } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

/**
 * 文件引用数据结构
 */
export interface FileReference {
  id: string;
  name: string;      // 文件名（显示用）
  path: string;      // 完整路径（悬停显示 & 发送时使用）
}

interface FileReferenceTagProps {
  reference: FileReference;
  onRemove: (id: string) => void;
  className?: string;
}

/**
 * 文件引用标签组件
 * 
 * 显示为紧凑的标签形式，悬停时显示完整路径
 * 用于"添加到AI对话"功能
 */
export function FileReferenceTag({ reference, onRemove, className = "" }: FileReferenceTagProps) {
  // 根据文件扩展名获取图标颜色
  const getFileColor = (name: string) => {
    const ext = name.split('.').pop()?.toLowerCase();
    switch (ext) {
      case 'csv':
      case 'xlsx':
      case 'xls':
        return 'text-green-600 dark:text-green-400';
      case 'py':
        return 'text-blue-600 dark:text-blue-400';
      case 'js':
      case 'ts':
      case 'tsx':
        return 'text-yellow-600 dark:text-yellow-400';
      case 'json':
        return 'text-orange-600 dark:text-orange-400';
      case 'md':
        return 'text-purple-600 dark:text-purple-400';
      default:
        return 'text-gray-600 dark:text-gray-400';
    }
  };

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <div
          className={`
            inline-flex items-center gap-1 px-2 py-1 
            bg-blue-50 dark:bg-blue-900/30 
            border border-blue-200 dark:border-blue-700 
            rounded-md text-sm
            hover:bg-blue-100 dark:hover:bg-blue-900/50
            transition-colors cursor-default
            ${className}
          `}
        >
          <FileText className={`w-3.5 h-3.5 ${getFileColor(reference.name)}`} />
          <span className="text-blue-700 dark:text-blue-300 max-w-[150px] truncate">
            {reference.name}
          </span>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onRemove(reference.id);
            }}
            className="
              ml-0.5 p-0.5 rounded
              hover:bg-blue-200 dark:hover:bg-blue-800
              text-blue-500 dark:text-blue-400
              hover:text-blue-700 dark:hover:text-blue-200
              transition-colors
            "
            title="移除引用"
          >
            <X className="w-3 h-3" />
          </button>
        </div>
      </TooltipTrigger>
      <TooltipContent side="top" className="max-w-[400px]">
        <p className="text-xs font-mono break-all">{reference.path}</p>
      </TooltipContent>
    </Tooltip>
  );
}

interface FileReferenceListProps {
  references: FileReference[];
  onRemove: (id: string) => void;
  className?: string;
}

/**
 * 文件引用列表组件
 * 
 * 在输入框上方显示所有文件引用标签
 */
export function FileReferenceList({ references, onRemove, className = "" }: FileReferenceListProps) {
  if (references.length === 0) return null;

  return (
    <div className={`flex flex-wrap gap-1.5 p-2 bg-gray-50 dark:bg-gray-900/50 border-b border-gray-200 dark:border-gray-700 ${className}`}>
      <span className="text-xs text-gray-500 dark:text-gray-400 self-center mr-1">
        引用文件:
      </span>
      {references.map((ref) => (
        <FileReferenceTag
          key={ref.id}
          reference={ref}
          onRemove={onRemove}
        />
      ))}
    </div>
  );
}

/**
 * 将文件引用格式化为消息内容
 * 
 * @param references 文件引用列表
 * @returns 格式化的文件引用文本
 */
export function formatFileReferencesForMessage(references: FileReference[]): string {
  if (references.length === 0) return "";
  
  const refTexts = references.map(ref => `[${ref.name}](${ref.path})`);
  return `\n\n---\n📎 引用文件:\n${refTexts.join('\n')}\n---\n`;
}
