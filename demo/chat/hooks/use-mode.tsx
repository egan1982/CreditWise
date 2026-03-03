"use client";

import React, { createContext, useContext, useState, useMemo, ReactNode } from "react";

// 交互模式类型
export type InteractionMode = "auto" | "expert";

// Context 数据结构
interface ModeContextValue {
  // 当前会话的交互模式
  interactionMode: InteractionMode;
  setInteractionMode: (mode: InteractionMode) => void;
  // 历史任务的交互模式（用于恢复场景）
  historyTaskInteractionMode: string | null;
  setHistoryTaskInteractionMode: (mode: string | null) => void;
  // 计算属性：判断当前是否为专家模式
  // 优先使用历史任务模式，否则使用当前会话模式
  isExpertMode: boolean;
}

// 创建 Context
const ModeContext = createContext<ModeContextValue | null>(null);

// Provider 组件 Props
interface ModeProviderProps {
  children: ReactNode;
  // 可选：从外部传入默认模式（如用户配置）
  defaultMode?: InteractionMode;
}

/**
 * ModeProvider - 模式状态集中管理
 * 
 * 功能：
 * 1. 管理当前会话的交互模式（auto/expert）
 * 2. 管理历史任务的交互模式（用于恢复场景）
 * 3. 提供统一的 isExpertMode 计算属性
 * 
 * 使用方式：
 * - 在顶层组件包裹 <ModeProvider>
 * - 子组件通过 useModeContext() 或 useIsExpertMode() 获取状态
 */
export function ModeProvider({ children, defaultMode = "expert" }: ModeProviderProps) {
  // 当前会话的交互模式（默认专家模式）
  const [interactionMode, setInteractionMode] = useState<InteractionMode>(defaultMode);
  // 历史任务的交互模式（用于恢复场景）
  const [historyTaskInteractionMode, setHistoryTaskInteractionMode] = useState<string | null>(null);

  // 计算 isExpertMode：优先使用历史任务模式
  const isExpertMode = useMemo(() => {
    return historyTaskInteractionMode 
      ? historyTaskInteractionMode === "expert" 
      : interactionMode === "expert";
  }, [historyTaskInteractionMode, interactionMode]);

  // Context 值（使用 useMemo 避免不必要的重渲染）
  const value = useMemo<ModeContextValue>(() => ({
    interactionMode,
    setInteractionMode,
    historyTaskInteractionMode,
    setHistoryTaskInteractionMode,
    isExpertMode,
  }), [interactionMode, historyTaskInteractionMode, isExpertMode]);

  return (
    <ModeContext.Provider value={value}>
      {children}
    </ModeContext.Provider>
  );
}

/**
 * useModeContext - 获取完整的模式上下文
 * 
 * 返回：ModeContextValue（包含所有状态和方法）
 * 使用场景：需要修改模式状态的组件
 */
export function useModeContext(): ModeContextValue {
  const context = useContext(ModeContext);
  if (!context) {
    throw new Error("useModeContext must be used within a ModeProvider");
  }
  return context;
}

/**
 * useIsExpertMode - 快捷 Hook，仅获取 isExpertMode 布尔值
 * 
 * 返回：boolean（是否为专家模式）
 * 使用场景：只需要判断模式的组件（只读场景）
 * 
 * 判断逻辑：
 * - 优先使用 historyTaskInteractionMode（历史任务模式）
 * - 否则使用 interactionMode（当前会话模式）
 */
export function useIsExpertMode(): boolean {
  const context = useContext(ModeContext);
  if (!context) {
    throw new Error("useIsExpertMode must be used within a ModeProvider");
  }
  return context.isExpertMode;
}

/**
 * useInteractionMode - 快捷 Hook，获取和设置当前交互模式
 * 
 * 返回：[InteractionMode, (mode: InteractionMode) => void]
 * 使用场景：模式选择器组件
 */
export function useInteractionMode(): [InteractionMode, (mode: InteractionMode) => void] {
  const context = useContext(ModeContext);
  if (!context) {
    throw new Error("useInteractionMode must be used within a ModeProvider");
  }
  return [context.interactionMode, context.setInteractionMode];
}
