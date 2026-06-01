/**
 * 任务参数 JSON 解析工具
 *
 * 从 TaskParamCard.tsx 中抽离的纯函数，负责检测 AI 消息内容是否为
 * SOP 任务参数 JSON，支持：
 *   - 直接 JSON 解析
 *   - Markdown ```json``` 代码块提取
 *   - 截断 JSON 修复（tryRepairTruncatedJson）
 *   - 内容中提取 JSON 对象
 */

// =============================================================================
// 类型定义
// =============================================================================

export interface TaskParamResult {
  task_type: string | null;
  confidence: number;
  params: Record<string, any>;
  missing_params: string[];
  clarification_needed: boolean;
  clarification_question: string;
}

// =============================================================================
// 内部辅助函数
// =============================================================================

/**
 * task_type 别名映射表
 * LLM 可能生成不同的 task_type 名称变体，统一映射到后端注册的 task_id
 */
const TASK_TYPE_ALIAS_MAP: Record<string, string> = {
  // 评分卡相关变体 → scorecard_dev
  "scorecard_model_development": "scorecard_dev",
  "scorecard_development": "scorecard_dev",
  "scorecard": "scorecard_dev",
  "credit_scorecard": "scorecard_dev",
  "scorecard_modeling": "scorecard_dev",
  // 规则挖掘相关变体 → rule_mining
  "rule_discovery": "rule_mining",
  "rules_mining": "rule_mining",
  "rule_extraction": "rule_mining",
};

/** 将 LLM 生成的 task_type 映射为后端注册的 task_id */
function normalizeTaskType(taskType: string): string {
  return TASK_TYPE_ALIAS_MAP[taskType] || taskType;
}

/**
 * 验证是否为有效的任务参数结果
 */
function isValidTaskParamResult(obj: any): obj is TaskParamResult {
  return (
    obj &&
    typeof obj === "object" &&
    "task_type" in obj &&
    "confidence" in obj &&
    "params" in obj &&
    "missing_params" in obj &&
    "clarification_needed" in obj
  );
}

/**
 * 尝试修复截断的 JSON 字符串
 * 针对 Gemini 等模型可能返回不完整 JSON 的情况
 */
function tryRepairTruncatedJson(jsonStr: string): string | null {
  // 如果已经是完整的 JSON，直接返回
  try {
    JSON.parse(jsonStr);
    return jsonStr;
  } catch {
    // 继续尝试修复
  }

  // 检查是否包含 task_type（任务参数 JSON 的标志）
  if (!jsonStr.includes('"task_type"')) {
    return null;
  }

  let repaired = jsonStr.trim();

  // 移除末尾不完整的键名（如 "missing 或 "clarification_）
  repaired = repaired.replace(/,\s*"[a-z_]*$/i, '');
  
  // 计算未闭合的括号
  let braceCount = 0;
  let bracketCount = 0;
  let inString = false;
  let escapeNext = false;

  for (const char of repaired) {
    if (escapeNext) {
      escapeNext = false;
      continue;
    }
    if (char === '\\') {
      escapeNext = true;
      continue;
    }
    if (char === '"') {
      inString = !inString;
      continue;
    }
    if (inString) continue;

    if (char === '{') braceCount++;
    if (char === '}') braceCount--;
    if (char === '[') bracketCount++;
    if (char === ']') bracketCount--;
  }

  // 如果在字符串中间截断，先闭合字符串
  if (inString) {
    repaired += '"';
  }

  // 闭合未闭合的括号
  while (bracketCount > 0) {
    repaired += ']';
    bracketCount--;
  }
  while (braceCount > 0) {
    repaired += '}';
    braceCount--;
  }

  // 验证修复后的 JSON
  try {
    JSON.parse(repaired);
    return repaired;
  } catch {
    return null;
  }
}

/**
 * 从可能不完整的对象中构建有效的 TaskParamResult
 */
function buildPartialTaskParamResult(obj: any): TaskParamResult | null {
  // 至少需要 task_type
  if (!obj || typeof obj !== 'object' || !obj.task_type) {
    return null;
  }

  return {
    task_type: normalizeTaskType(obj.task_type) || null,
    confidence: typeof obj.confidence === 'number' ? obj.confidence : 0.8,
    params: obj.params || {},
    missing_params: Array.isArray(obj.missing_params) ? obj.missing_params : [],
    clarification_needed: typeof obj.clarification_needed === 'boolean' ? obj.clarification_needed : false,
    clarification_question: obj.clarification_question || '',
  };
}

// =============================================================================
// 主导出函数
// =============================================================================

/**
 * 检测 AI 消息内容是否为任务参数 JSON
 *
 * 解析策略（按优先级）：
 * 1. 直接 JSON.parse
 * 2. 从 markdown ```json``` 代码块提取
 * 3. 从内容中正则提取 { ... "task_type" ... } 对象
 * 每一步都会尝试 tryRepairTruncatedJson 修复截断
 */
export function isTaskParamJson(content: string): TaskParamResult | null {
  // 尝试直接解析
  try {
    const parsed = JSON.parse(content.trim());
    if (isValidTaskParamResult(parsed)) {
      parsed.task_type = normalizeTaskType(parsed.task_type);
      return parsed;
    }
    // 即使不完全符合，尝试构建部分结果
    const partial = buildPartialTaskParamResult(parsed);
    if (partial) return partial;
  } catch {
    // 不是纯JSON，继续尝试提取
  }

  // 尝试从markdown代码块中提取
  const jsonMatch = content.match(/```(?:json)?\s*([\s\S]*?)```/);
  if (jsonMatch) {
    try {
      const parsed = JSON.parse(jsonMatch[1].trim());
      if (isValidTaskParamResult(parsed)) {
        parsed.task_type = normalizeTaskType(parsed.task_type);
        return parsed;
      }
      const partial = buildPartialTaskParamResult(parsed);
      if (partial) return partial;
    } catch {
      // 尝试修复截断的 JSON
      const repaired = tryRepairTruncatedJson(jsonMatch[1].trim());
      if (repaired) {
        try {
          const parsed = JSON.parse(repaired);
          const partial = buildPartialTaskParamResult(parsed);
          if (partial) return partial;
        } catch {
          // 修复失败
        }
      }
    }
  }

  // 尝试从内容中提取JSON对象
  const jsonObjMatch = content.match(/\{[\s\S]*"task_type"[\s\S]*/);
  if (jsonObjMatch) {
    // 先尝试直接解析
    try {
      const parsed = JSON.parse(jsonObjMatch[0]);
      if (isValidTaskParamResult(parsed)) {
        parsed.task_type = normalizeTaskType(parsed.task_type);
        return parsed;
      }
      const partial = buildPartialTaskParamResult(parsed);
      if (partial) return partial;
    } catch {
      // 尝试修复截断的 JSON
      const repaired = tryRepairTruncatedJson(jsonObjMatch[0]);
      if (repaired) {
        try {
          const parsed = JSON.parse(repaired);
          const partial = buildPartialTaskParamResult(parsed);
          if (partial) return partial;
        } catch {
          // 修复失败
        }
      }
    }
  }

  return null;
}
