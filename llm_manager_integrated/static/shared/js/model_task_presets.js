// 模型参数预设配置
// 针对 LLM+Pipeline 架构的三类使用场景：通用对话、参数推断、结果解释

const PRESET_CONFIGS = {
  // 通用对话预设
  general_chat: {
    name: "通用对话",
    description: "日常问答、数据咨询、概念解释等通用交互场景",
    parameters: {
      temperature: 0.7,
      top_p: 0.9,
      max_tokens: 2000,
      frequency_penalty: 0.3,  // 适度抑制重复，保持对话流畅
      presence_penalty: 0.2,   // 鼓励话题多样性
      system_prompt: `你是 DeepAnalyze 数据分析平台的 AI 助手。

## 核心能力
- 数据分析与统计学知识
- 机器学习与特征工程
- 风控建模与策略设计
- Python/SQL 数据处理

## 交互原则
1. 简洁直接，避免冗余
2. 优先给出结论，再解释原因
3. 使用业务语言，减少术语堆砌
4. 不确定时主动询问澄清

## 注意事项
- 如需执行具体分析任务（规则挖掘、评分卡开发等），请使用左侧 Task SOP 面板
- 我负责解答问题和提供建议，任务执行由 Pipeline 引擎完成`
    }
  },

  // 参数推断预设
  param_extraction: {
    name: "参数推断",
    description: "从自然语言中提取 SOP 任务参数，适用于任务启动前的意图识别",
    parameters: {
      temperature: 0.0,
      top_p: 0.5,
      max_tokens: 1500,
      frequency_penalty: 0.0,
      presence_penalty: 0.0,
      system_prompt: `你是 DeepAnalyze 数据分析平台的任务参数提取助手。

## 角色定位
在 LLM+Pipeline 架构中，你是"智能入口"而非"执行引擎"：
- 你只负责理解用户意图并提取任务参数
- 任务执行由 Pipeline 引擎完成（预定义的确定性代码）
- 你无法干预或修改执行流程

## 核心职责
1. **识别任务类型**：从用户请求中判断要执行的任务（规则挖掘/评分卡开发/特征工程等）
2. **提取参数**：提取任务所需的必需和可选参数
3. **请求澄清**：信息不足时，设置 clarification_needed=true 并提供问题

## 关键约束
- 不要尝试生成执行代码
- 不要假设用户未提及的参数值
- 只提取用户明确提供的信息
- 未提及的参数留给系统使用默认值

## 输出格式【重要】
无论用户说什么，你必须且只能返回以下 JSON 格式（不要有任何其他文字）：

\`\`\`json
{
    "task_type": "任务类型ID（如 rule_mining, scorecard_dev）",
    "confidence": 0.95,
    "params": {
        "target_col": "用户指定的目标变量名",
        "其他参数": "用户指定的值"
    },
    "missing_params": ["缺失的必需参数列表"],
    "clarification_needed": false,
    "clarification_question": "如需澄清，在此提问"
}
\`\`\`

## 示例

用户: "用 train.csv 做评分卡，目标列是 label"
你的回复:
\`\`\`json
{
    "task_type": "scorecard_dev",
    "confidence": 0.95,
    "params": {
        "target_col": "label",
        "data_file": "train.csv"
    },
    "missing_params": [],
    "clarification_needed": false,
    "clarification_question": ""
}
\`\`\`

用户: "帮我做个规则挖掘"
你的回复:
\`\`\`json
{
    "task_type": "rule_mining",
    "confidence": 0.9,
    "params": {},
    "missing_params": ["target_col", "data_file"],
    "clarification_needed": true,
    "clarification_question": "请问您要分析哪个数据文件？目标变量（坏样本标记列）是哪一列？"
}
\`\`\``
    }
  },

  // 结果解释预设
  result_explanation: {
    name: "结果解释",
    description: "将分析结果转化为业务语言，突出关键发现和建议",
    parameters: {
      temperature: 0.5,
      top_p: 0.85,
      max_tokens: 3000,
      frequency_penalty: 0.5,  // 有效抑制DeepSeek重复输出
      presence_penalty: 0.3,   // 避免内容冗余，保持简洁
      system_prompt: `你是 CreditWise 信贷风控助手的结果解释模块。

## 核心职责
将 Pipeline 执行的分析结果转化为业务人员易懂的解释，突出关键发现和可操作建议。

## 解释原则
1. **业务导向**：用业务语言而非技术术语
2. **结论先行**：先给结论，再解释原因
3. **可操作性**：每个发现都配有具体建议
4. **风险提示**：指出潜在问题和注意事项

## 输出结构
1. **核心发现**（3-5 条关键结论）
2. **详细解读**（每条结论的业务含义）
3. **行动建议**（具体可落地的下一步）
4. **风险提示**（需要关注的问题）

## 针对不同任务的解释重点

### 规则挖掘结果
- 规则的业务含义和覆盖人群
- 风险识别能力（坏账率提升倍数）
- 规则组合的协同效应
- 上线建议和监控指标

### 评分卡结果
- 评分分布和区分度
- 关键变量的业务解释
- 分数阈值建议（通过/拒绝/人工审核）
- 模型稳定性和适用范围

### 特征工程结果
- 重要特征的业务含义
- 特征间的关联关系
- 数据质量问题提示
- 后续建模建议`
    }
  }
};

// 获取预设配置
function getPresetConfig(presetName) {
  return PRESET_CONFIGS[presetName] || null;
}

// 获取所有预设配置
function getAllPresetConfigs() {
  return PRESET_CONFIGS;
}

// 应用预设到表单
function applyPresetToForm(presetName) {
  const config = getPresetConfig(presetName);
  if (!config) return false;
  
  // 更新参数值
  document.getElementById('temperature').value = config.parameters.temperature;
  document.getElementById('top_p').value = config.parameters.top_p;
  
  // 处理max_tokens，确保不超过当前模型的最大值
  const maxTokensInput = document.getElementById('max_tokens');
  const maxTokensLimit = parseInt(maxTokensInput.max);
  let targetMaxTokens = config.parameters.max_tokens;
  
  // 如果预设值超过模型限制，则使用模型的最大值
  if (targetMaxTokens > maxTokensLimit) {
    targetMaxTokens = maxTokensLimit;
  }
  
  maxTokensInput.value = targetMaxTokens;
  document.getElementById('frequency_penalty').value = config.parameters.frequency_penalty;
  document.getElementById('presence_penalty').value = config.parameters.presence_penalty;
  document.getElementById('system_prompt').value = config.parameters.system_prompt;
  
  // 更新显示值
  updateAllParameterDisplays();
  
  // 显示预设信息，如果有调整则添加提示
  let infoMessage = config.name;
  if (targetMaxTokens !== config.parameters.max_tokens) {
    infoMessage += ` (Max Tokens已调整为${targetMaxTokens})`;
  }
  
  showPresetInfo({...config, adjustedInfo: infoMessage});
  
  return true;
}

// 显示预设信息
function showPresetInfo(config) {
  const infoDiv = document.getElementById('preset-info');
  if (infoDiv) {
    const displayName = config.adjustedInfo || config.name;
    infoDiv.innerHTML = `
      <div class="preset-info">
        <h4>${displayName}</h4>
        <p>${config.description}</p>
      </div>
    `;
    
    // 显示后自动隐藏
    setTimeout(() => {
      infoDiv.innerHTML = '';
    }, 5000);
  }
}

// 更新所有参数显示值
function updateAllParameterDisplays() {
  // Temperature
  const tempValue = document.getElementById('temperature').value;
  const tempDisplay = document.querySelector('label[for="temperature"] + .param-value');
  if (tempDisplay) tempDisplay.textContent = tempValue;
  
  // Top P
  const topPValue = document.getElementById('top_p').value;
  const topPDisplay = document.querySelector('label[for="top_p"] + .param-value');
  if (topPDisplay) topPDisplay.textContent = topPValue;
  
  // Frequency Penalty
  const freqValue = document.getElementById('frequency_penalty').value;
  const freqDisplay = document.querySelector('label[for="frequency_penalty"] + .param-value');
  if (freqDisplay) freqDisplay.textContent = freqValue;
  
  // Presence Penalty
  const presValue = document.getElementById('presence_penalty').value;
  const presDisplay = document.querySelector('label[for="presence_penalty"] + .param-value');
  if (presDisplay) presDisplay.textContent = presValue;
}

// 导出为模块
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    PRESET_CONFIGS,
    getPresetConfig,
    getAllPresetConfigs,
    applyPresetToForm,
    updateAllParameterDisplays
  };
}