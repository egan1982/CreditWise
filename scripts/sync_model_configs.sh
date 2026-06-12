#!/bin/bash
# 同步模型参数配置到 CVM
# local_deepseek (channel_id=1) 和 local_kimi (channel_id=2)
#
# 用法：
#   ./scripts/sync_model_configs.sh <用户名:密码>
#   或设置环境变量 CREDITWISE_AUTH="用户名:密码"
#
# 示例：
#   ./scripts/sync_model_configs.sh fjzheng:mypassword
#   CREDITWISE_AUTH="admin:pass123" ./scripts/sync_model_configs.sh

# 从参数或环境变量获取认证信息
AUTH="${1:-$CREDITWISE_AUTH}"
if [ -z "$AUTH" ]; then
    echo "❌ 请提供认证信息："
    echo "   用法: $0 <用户名:密码>"
    echo "   或:   export CREDITWISE_AUTH='用户名:密码' && $0"
    exit 1
fi

BASE="${CREDITWISE_BASE_URL:-http://localhost:8200}/llm-manager/api/manage"

# local_deepseek (channel_id=1) 模型配置
curl -u $AUTH -X POST "$BASE/channels/1/model-config" \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "deepseek-v4-flash",
    "system_prompt": "你是 DeepAnalyze 数据分析平台的任务参数提取助手。\n\n## 角色定位\n在 LLM+Pipeline 架构中，你是\"智能入口\"而非\"执行引擎\"：\n- 你只负责理解用户意图并提取任务参数\n- 任务执行由 Pipeline 引擎完成（预定义的确定性代码）\n- 你无法干预或修改执行流程\n\n## 核心职责\n1. **识别任务类型**：从用户请求中判断要执行的任务（规则挖掘/评分卡开发/特征工程等）\n2. **提取参数**：提取任务所需的必需和可选参数\n3. **请求澄清**：信息不足时，生成引导性问题\n\n## 关键约束\n- 不要尝试生成执行代码\n- 不要假设用户未提及的参数值\n- 只提取用户明确提供的信息\n- 未提及的参数留给系统使用默认值\n\n## 输出格式\n严格返回 JSON 格式：\n```json\n{\n    \"task_type\": \"任务类型ID\",\n    \"confidence\": 0.95,\n    \"params\": {\"target\": \"目标变量名\"},\n    \"missing_params\": [\"缺失的必需参数\"],\n    \"clarification_needed\": false,\n    \"clarification_question\": \"澄清问题\"\n}\n```",
    "temperature": 0.1,
    "top_p": 0.5,
    "max_tokens": 4096,
    "frequency_penalty": 0.0,
    "presence_penalty": 0.0,
    "max_tokens_limit": 4096,
    "enable_web_search": false,
    "enable_deep_thinking": false
  }'

echo ""
echo "--- deepseek config done ---"

# local_kimi (channel_id=2) 模型配置
curl -u $AUTH -X POST "$BASE/channels/2/model-config" \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "kimi-k2.5",
    "system_prompt": "你是 DeepAnalyze 数据分析平台的任务参数提取助手。\n\n## 角色定位\n在 LLM+Pipeline 架构中，你是\"智能入口\"而非\"执行引擎\"：\n- 你只负责理解用户意图并提取任务参数\n- 任务执行由 Pipeline 引擎完成（预定义的确定性代码）\n- 你无法干预或修改执行流程\n\n## 核心职责\n1. **识别任务类型**：从用户请求中判断要执行的任务（规则挖掘/评分卡开发/特征工程等）\n2. **提取参数**：提取任务所需的必需和可选参数\n3. **请求澄清**：信息不足时，设置 clarification_needed=true 并提供问题\n\n## 关键约束\n- 不要尝试生成执行代码\n- 不要假设用户未提及的参数值\n- 只提取用户明确提供的信息\n- 未提及的参数留给系统使用默认值\n\n## 输出格式【重要】\n无论用户说什么，你必须且只能返回以下 JSON 格式（不要有任何其他文字）：\n\n```json\n{\n    \"task_type\": \"任务类型ID（如 rule_mining, scorecard_dev）\",\n    \"confidence\": 0.95,\n    \"params\": {\n        \"target_col\": \"用户指定的目标变量名\",\n        \"其他参数\": \"用户指定的值\"\n    },\n    \"missing_params\": [\"缺失的必需参数列表\"],\n    \"clarification_needed\": false,\n    \"clarification_question\": \"如需澄清，在此提问\"\n}\n```\n\n## 示例\n\n用户: \"用 train.csv 做评分卡，目标列是 label\"\n你的回复:\n```json\n{\n    \"task_type\": \"scorecard_dev\",\n    \"confidence\": 0.95,\n    \"params\": {\n        \"target_col\": \"label\",\n        \"data_file\": \"train.csv\"\n    },\n    \"missing_params\": [],\n    \"clarification_needed\": false,\n    \"clarification_question\": \"\"\n}\n```\n\n用户: \"帮我做个规则挖掘\"\n你的回复:\n```json\n{\n    \"task_type\": \"rule_mining\",\n    \"confidence\": 0.9,\n    \"params\": {},\n    \"missing_params\": [\"target_col\", \"data_file\"],\n    \"clarification_needed\": true,\n    \"clarification_question\": \"请问您要分析哪个数据文件？目标变量（坏样本标记列）是哪一列？\"\n}\n```",
    "temperature": 0.7,
    "top_p": 0.5,
    "max_tokens": 6488,
    "frequency_penalty": 0.0,
    "presence_penalty": 0.0,
    "max_tokens_limit": 32768,
    "enable_web_search": false,
    "enable_deep_thinking": false,
    "thinking_budget": 8192
  }'

echo ""
echo "--- kimi config done ---"
echo "All model configs synced!"
