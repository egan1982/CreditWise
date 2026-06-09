/**
 * useAIAnalysis — AI 分析状态管理 Hook
 *
 * 核心逻辑（数据驱动，简单清晰）：
 *
 * 当 status=completed 时：
 *   1. 查后端 DB（GET /analysis）
 *   2. 有分析记录 → 展示（加载模式）
 *   3. 无分析记录 → 自动触发 AI 生成（生成模式）
 *
 * 重试场景：
 *   - clearAndReset() 清空前端 state
 *   - 后端 retryStage 会重置阶段，DB 里旧分析被打入快照
 *   - 重试完成后 status=completed，重新走上面的逻辑即可
 *
 * 快照展示（历史版本）：
 *   - hook 只管当前版本；历史版本由调用方读 snapshot.ai_analysis
 */

"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { getApiUrl } from "@/lib/config";

// =============================================================================
// 常量
// =============================================================================

const AI_ANALYSIS_CACHE_PREFIX = "ai_analysis_cache:";
// 支持 SUGGESTED_PARAMS 出现在行中任意位置（含嵌入句末、单行/多行 JSON）
const STRIP_SUGGESTED_PARAMS_RE = /\s*SUGGESTED_PARAMS:\s*[\s\S]*$/;

// =============================================================================
// sessionStorage 工具
// =============================================================================

function getCacheKey(recordId: string, stageId: string): string {
  return `${AI_ANALYSIS_CACHE_PREFIX}${recordId}:${stageId}`;
}

function readCache(recordId: string, stageId: string): string | null {
  if (typeof window === "undefined" || !recordId) return null;
  try { return sessionStorage.getItem(getCacheKey(recordId, stageId)); } catch { return null; }
}

function writeCache(recordId: string, stageId: string, text: string): void {
  if (typeof window === "undefined" || !recordId) return;
  try { sessionStorage.setItem(getCacheKey(recordId, stageId), text); } catch { /* ignore */ }
}

function deleteCache(recordId: string, stageId: string): void {
  if (typeof window === "undefined" || !recordId) return;
  try { sessionStorage.removeItem(getCacheKey(recordId, stageId)); } catch { /* ignore */ }
}

function stripSuggestedParams(text: string): string {
  return text.replace(STRIP_SUGGESTED_PARAMS_RE, "").trimEnd();
}

// =============================================================================
// API 工具
// =============================================================================

interface AnalysisResult {
  analysis_text: string;
  model_used: string | null;
  suggested_params?: Record<string, unknown> | null;
}

async function fetchAnalysis(recordId: string, stageId: string): Promise<AnalysisResult | null> {
  try {
    const res = await fetch(getApiUrl(`/sop/history/${recordId}/stages/${stageId}/analysis`));
    if (!res.ok) return null;
    const data = await res.json();
    if (!data.analysis?.analysis_text) return null;
    return {
      analysis_text: data.analysis.analysis_text,
      model_used: data.analysis.model_used ?? null,
      suggested_params: data.analysis.suggested_params ?? null,
    };
  } catch { return null; }
}

async function saveAnalysis(
  recordId: string, stageId: string, analysisText: string, modelUsed?: string
): Promise<{ success: boolean; suggested_params?: Record<string, unknown> | null }> {
  try {
    const res = await fetch(getApiUrl(`/sop/history/${recordId}/stages/${stageId}/analysis`), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ analysis_text: analysisText, model_used: modelUsed || null }),
    });
    if (!res.ok) return { success: false };
    const data = await res.json();
    return { success: true, suggested_params: data.suggested_params ?? null };
  } catch { return { success: false }; }
}

// =============================================================================
// Hook 接口
// =============================================================================

export interface UseAIAnalysisOptions {
  recordId: string | undefined;
  stageId: string;
  status: string;
  outputPreview: Record<string, any> | null | undefined;
  isExpertMode: boolean;
  selectedModel: string;
  taskType?: string;
  stageParams?: Record<string, any>;
  taskResult?: Record<string, any> | null;
  isOutputDataReady: (data: Record<string, any> | null, stageId: string) => boolean;
  shouldUseOverallAnalysis?: boolean;
}

export interface UseAIAnalysisReturn {
  aiAnalysis: string;
  suggestedParams: Record<string, unknown> | null;
  isAnalyzing: boolean;
  isLoadingCachedAnalysis: boolean;
  triggerAnalysis: () => void;
  clearAndReset: () => void;
}

// =============================================================================
// Hook 实现
// =============================================================================

export function useAIAnalysis(options: UseAIAnalysisOptions): UseAIAnalysisReturn {
  const {
    recordId, stageId, status, outputPreview,
    isExpertMode, selectedModel, taskType, stageParams,
    taskResult, isOutputDataReady, shouldUseOverallAnalysis = false,
  } = options;

  // ─── state ────────────────────────────────────────────────────────────────
  const [aiAnalysis, setAiAnalysis] = useState<string>(() => {
    const cached = recordId ? readCache(recordId, stageId) : null;
    return cached ? stripSuggestedParams(cached) : "";
  });
  const [suggestedParams, setSuggestedParams] = useState<Record<string, unknown> | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isLoadingCachedAnalysis, setIsLoadingCachedAnalysis] = useState(false);

  // ─── refs ─────────────────────────────────────────────────────────────────
  const analysisVersionRef = useRef(0);
  const latestOutputPreviewRef = useRef(outputPreview);
  const prevCompletedKeyRef = useRef(""); // 记录上次已处理的 "recordId:stageId"，避免重复触发

  useEffect(() => { latestOutputPreviewRef.current = outputPreview; }, [outputPreview]);

  // ─── 核心：执行 AI 分析（流式输出）────────────────────────────────────────
  const performAIAnalysis = useCallback(async () => {
    if (!isExpertMode || !selectedModel) return;

    const currentVersion = ++analysisVersionRef.current;
    const currentOutputPreview = latestOutputPreviewRef.current || outputPreview;

    setIsAnalyzing(true);
    setAiAnalysis("");
    setSuggestedParams(null); // 开始新一轮分析时清空旧建议，避免残留

    let fullAnalysis = "";
    try {
      const promptRequest = shouldUseOverallAnalysis
        ? { analysis_type: "overall", task_type: taskType, result: taskResult }
        : {
            analysis_type: "stage", task_type: taskType,
            stage_id: stageId, stage_name: stageId,
            data: currentOutputPreview, params_used: stageParams || {},
          };

      const promptRes = await fetch(getApiUrl("/v1/chat/analysis/prompt"), {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(promptRequest),
      });
      if (!promptRes.ok) throw new Error(`获取 Prompt 失败: ${promptRes.status}`);
      const promptResult = await promptRes.json();
      const prompt = promptResult.prompt as string;
      const AI_PARAMS = promptResult.params || {};

      const chatRes = await fetch(getApiUrl("/v1/chat/completions"), {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: selectedModel,
          messages: [{ role: "user", content: prompt }],
          stream: true, ...AI_PARAMS,
          include_task_list: false, enable_code_execution: false,
        }),
      });
      if (!chatRes.ok) throw new Error(`LLM 请求失败: ${chatRes.status}`);

      const reader = chatRes.body?.getReader();
      if (!reader) throw new Error("无法读取响应流");
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        for (const line of chunk.split("\n")) {
          const trimmed = line.replace(/^data:\s*/, "").trim();
          if (!trimmed || trimmed === "[DONE]") continue;
          try {
            const parsed = JSON.parse(trimmed);
            const content = parsed.choices?.[0]?.delta?.content || "";
            if (content && currentVersion === analysisVersionRef.current) {
              fullAnalysis += content;
              setAiAnalysis((prev) => prev + content);
            }
          } catch { /* ignore */ }
        }
      }

      if (currentVersion !== analysisVersionRef.current) return;

      const cleanAnalysis = stripSuggestedParams(fullAnalysis);
      if (cleanAnalysis !== fullAnalysis) setAiAnalysis(cleanAnalysis);

      if (recordId) {
        writeCache(recordId, stageId, cleanAnalysis);
        const capturedVersion = currentVersion;
        saveAnalysis(recordId, stageId, fullAnalysis, selectedModel)
          .then(({ success, suggested_params }) => {
            if (!success) console.warn(`[useAIAnalysis] 保存失败: ${recordId}/${stageId}`);
            // 版本保护：只有当前版本的回调才更新 suggestedParams
            if (capturedVersion !== analysisVersionRef.current) return;
            if (suggested_params && Object.keys(suggested_params).length > 0) {
              setSuggestedParams(suggested_params as Record<string, unknown>);
            }
          })
          .catch((e) => console.error("[useAIAnalysis] 保存出错:", e));
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      console.error("[useAIAnalysis] AI 分析失败:", msg);
      if (currentVersion === analysisVersionRef.current) {
        setAiAnalysis(`分析生成失败：${msg}。请重试或检查控制台。`);
      }
    } finally {
      if (currentVersion === analysisVersionRef.current) setIsAnalyzing(false);
    }
  }, [isExpertMode, selectedModel, stageId, taskType, stageParams, shouldUseOverallAnalysis, taskResult, outputPreview, recordId]);

  // ─── 核心 Effect：当阶段完成时，查 DB 决定显示或触发 ─────────────────────
  // 逻辑：status=completed + 专家模式 + outputPreview 就绪 → 查 DB
  //   有分析 → 展示
  //   没有   → 自动触发生成
  useEffect(() => {
    if (!isExpertMode || status !== "completed" || !recordId) return;
    if (!outputPreview || !isOutputDataReady(outputPreview, stageId)) return;
    if (shouldUseOverallAnalysis && !taskResult) return;

    const completedKey = `${recordId}:${stageId}`;

    // 已经处理过这个版本，跳过（避免 outputPreview 微小变化导致重复触发）
    if (prevCompletedKeyRef.current === completedKey && (aiAnalysis || isAnalyzing)) return;

    prevCompletedKeyRef.current = completedKey;

    const check = async () => {
      setIsLoadingCachedAnalysis(true);
      try {
        const result = await fetchAnalysis(recordId, stageId);
        if (result?.analysis_text) {
          // DB 有分析 → 直接展示
          setAiAnalysis(result.analysis_text);
          setSuggestedParams(
            result.suggested_params && Object.keys(result.suggested_params).length > 0
              ? result.suggested_params as Record<string, unknown>
              : null
          );
          writeCache(recordId, stageId, result.analysis_text);
        } else {
          // DB 无分析 → 触发生成
          setAiAnalysis("");
          setSuggestedParams(null);
          performAIAnalysis();
        }
      } finally {
        setIsLoadingCachedAnalysis(false);
      }
    };

    check();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recordId, stageId, status, outputPreview, isExpertMode, selectedModel, taskResult]);

  // ─── status → running 时清空 state ────────────────────────────────────────
  const prevStatusRef = useRef(status);
  useEffect(() => {
    if (prevStatusRef.current !== "running" && status === "running") {
      setAiAnalysis("");
      setSuggestedParams(null);
      setIsAnalyzing(false);
      setIsLoadingCachedAnalysis(false);
      if (recordId) deleteCache(recordId, stageId);
      // 重置 completedKey，确保下次 completed 时重新触发
      prevCompletedKeyRef.current = "";
    }
    prevStatusRef.current = status;
  }, [status, recordId, stageId]);

  // ─── 公共操作：手动重新分析 ───────────────────────────────────────────────
  const triggerAnalysis = useCallback(() => {
    if (recordId) {
      deleteCache(recordId, stageId);
      // 同步删除 DB 中的旧分析，避免下次加载时读回错误内容
      fetch(getApiUrl(`/sop/history/${recordId}/stages/${stageId}/analysis`), { method: "DELETE" })
        .catch((e) => console.warn("[useAIAnalysis] 删除旧分析失败（不影响重新生成）:", e));
    }
    setAiAnalysis("");
    setSuggestedParams(null);
    prevCompletedKeyRef.current = ""; // 重置，让 completedKey 检查失效
    performAIAnalysis();
  }, [recordId, stageId, performAIAnalysis]);

  // ─── 公共操作：重试前清除 ──────────────────────────────────────────────────
  const clearAndReset = useCallback(() => {
    if (recordId) deleteCache(recordId, stageId);
    setAiAnalysis("");
    setSuggestedParams(null);
    setIsAnalyzing(false);
    setIsLoadingCachedAnalysis(false);
    // 重置 completedKey，确保重试完成后重新触发 check
    prevCompletedKeyRef.current = "";
  }, [recordId, stageId]);

  return { aiAnalysis, suggestedParams, isAnalyzing, isLoadingCachedAnalysis, triggerAnalysis, clearAndReset };
}
