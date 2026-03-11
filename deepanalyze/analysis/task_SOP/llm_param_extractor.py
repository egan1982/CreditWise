# -*- coding: utf-8 -*-
"""
LLM Parameter Extractor - LLM 参数推断器

从自然语言对话中提取任务意图和参数，实现 Chat 入口的智能参数识别。
这是 LLM+Pipeline 架构的核心组件，将 LLM 定位为"智能入口"而非"执行引擎"。

架构定位：
- LLM 角色：理解用户意图 + 提取任务参数
- Pipeline 角色：确定性执行预定义的分析代码
- 系统提示词：任务类型无关，适用于所有 SOP 任务

核心功能：
- 任务意图识别：识别用户想要执行的任务类型
- 参数提取：从对话中提取任务所需的参数
- 缺失参数检测：识别必需但未提供的参数
- 澄清问题生成：当信息不足时生成引导性问题

相关文档：
- docs/system_prompt_guide.md - 系统提示词配置指南
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

import aiohttp

if TYPE_CHECKING:
    from .registry import SOPRegistry

from .registry import get_registry

logger = logging.getLogger(__name__)


# =============================================================================
# Data Types
# =============================================================================

@dataclass
class TaskIntent:
    """任务意图识别结果"""
    task_type: str  # 任务类型 ID，如 "rule_mining", "scorecard_dev"
    confidence: float  # 置信度 0-1
    params: dict[str, Any]  # 提取的参数
    missing_params: list[str]  # 缺失的必需参数
    clarification_needed: bool  # 是否需要用户澄清
    clarification_question: str = ""  # 澄清问题
    raw_response: str = ""  # LLM 原始响应（用于调试）


@dataclass
class ExtractionContext:
    """提取上下文"""
    user_message: str  # 用户消息
    workspace_files: list[str] = field(default_factory=list)  # 工作区文件列表
    conversation_history: list[dict[str, str]] = field(default_factory=list)  # 对话历史
    data_columns: list[str] = field(default_factory=list)  # 数据列名（如果已加载数据）
    data_preview: str = ""  # 数据预览（前几行）


# =============================================================================
# Prompt Templates
# =============================================================================

EXTRACTION_SYSTEM_PROMPT = """你是 CreditWise 信贷风控助手的任务参数提取模块。

## 你的角色定位

在 LLM+Pipeline 架构中，你是"智能入口"而非"执行引擎"：
- 你只负责理解用户意图并提取任务参数
- 任务执行由 Pipeline 引擎完成（预定义的确定性代码）
- 你无法干预或修改执行流程

## 核心职责

1. **识别任务类型**：从用户请求中判断要执行的任务
2. **提取参数**：提取任务所需的必需和可选参数
3. **请求澄清**：信息不足时，生成引导性问题

## 关键约束

- 不要尝试生成执行代码
- 不要假设用户未提及的参数值
- 只提取用户明确提供的信息
- 未提及的参数留给系统使用默认值

## 可用的任务类型

{task_definitions}

## 输出格式

严格返回 JSON 格式，不要有任何解释文字：

```json
{{
    "task_type": "任务类型ID（如 rule_mining 或 scorecard_dev）",
    "confidence": 0.95,
    "params": {{
        "target_col": "目标变量列名",
        "force_categorical": ["分类变量1", "分类变量2"]
    }},
    "missing_params": ["缺失的必需参数名"],
    "clarification_needed": false,
    "clarification_question": "如果需要澄清，这里是问题"
}}
```

## 参数提取规则

1. **目标变量 (target_col)**：
   - 参数名必须是 `target_col`（不是 target）
   - 关键词："目标变量"、"标签"、"y变量"、"预测目标"、"因变量"
   - 示例："预测是否违约" → 可能是 "is_default"

2. **分类变量 (force_categorical)**：
   - 用户明确指定为分类变量的列
   - 示例："省份代码、城市代码作为分类变量"

3. **特征变量 (feature_cols)**：
   - 用户指定用于分析的特征列
   - 未指定时留空（系统自动选择）

4. **其他参数**：
   - 仅提取用户明确提及的参数
   - 未提及的参数不要填入 params

## 置信度评估标准

| 置信度 | 场景描述 |
|--------|----------|
| 0.9-1.0 | 用户明确指定任务类型和关键参数 |
| 0.7-0.9 | 任务类型可推断，部分参数需确认 |
| 0.5-0.7 | 任务类型不确定，需要澄清 |
| <0.5 | 无法识别任务意图 |

## 注意事项

1. 只返回 JSON，不要有任何解释文字
2. 参数名必须与任务定义中的参数名完全一致（如 target_col 不是 target）
3. 如果数据列名已知，优先匹配用户描述与实际列名
4. 置信度低于 0.7 时应设置 clarification_needed=true
"""

EXTRACTION_USER_PROMPT = """## 用户请求

{user_message}

## 当前工作区文件

{workspace_files}

## 数据信息

{data_info}

## 对话历史

{conversation_history}

请分析用户请求，提取任务意图和参数。只返回 JSON 格式结果。
"""


# =============================================================================
# LLM Parameter Extractor
# =============================================================================

class LLMParamExtractor:
    """LLM 参数推断器
    
    使用 LLM 从自然语言中提取任务参数，而非动态生成执行代码。
    这是 LLM SOP 模式废弃后，LLM 能力的新定位。
    
    Attributes:
        api_base: LLM API 基础 URL
        model: LLM 模型名称
        registry: SOP 任务注册表
    """
    
    def __init__(
        self,
        api_base: str = "http://localhost:8200/v1",
        model: str = "deepseek-chat",
        registry: Optional[SOPRegistry] = None
    ):
        """初始化参数推断器
        
        Args:
            api_base: LLM API 基础 URL
            model: LLM 模型名称
            registry: SOP 任务注册表（可选，默认使用全局实例）
        """
        self.api_base = api_base
        self.model = model
        self.registry = registry or get_registry()
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def extract(self, context: ExtractionContext) -> TaskIntent:
        """从用户消息中提取任务意图和参数
        
        Args:
            context: 提取上下文，包含用户消息、工作区文件等信息
            
        Returns:
            TaskIntent: 任务意图识别结果
        """
        logger.info(f"[LLM Extractor] Extracting params from: {context.user_message[:100]}...")
        
        # 构建 prompt
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(context)
        
        # 调用 LLM
        try:
            response = await self._call_llm(system_prompt, user_prompt)
            logger.debug(f"[LLM Extractor] Raw response: {response}")
            
            # 解析响应
            intent = self._parse_response(response)
            intent.raw_response = response
            
            # 验证和补充
            intent = self._validate_and_enhance(intent, context)
            
            logger.info(f"[LLM Extractor] Extracted: task_type={intent.task_type}, "
                       f"confidence={intent.confidence}, params={list(intent.params.keys())}")
            
            return intent
            
        except Exception as e:
            logger.error(f"[LLM Extractor] Extraction failed: {e}")
            return TaskIntent(
                task_type="",
                confidence=0.0,
                params={},
                missing_params=[],
                clarification_needed=True,
                clarification_question=f"抱歉，我无法理解您的请求。请问您想要执行什么任务？可选的任务有：规则挖掘、评分卡开发。",
                raw_response=str(e)
            )
    
    def _build_system_prompt(self) -> str:
        """构建系统 prompt"""
        task_definitions = self._get_task_definitions_text()
        return EXTRACTION_SYSTEM_PROMPT.format(task_definitions=task_definitions)
    
    def _build_user_prompt(self, context: ExtractionContext) -> str:
        """构建用户 prompt"""
        # 格式化工作区文件
        workspace_files = "\n".join(f"- {f}" for f in context.workspace_files) if context.workspace_files else "（无文件）"
        
        # 格式化数据信息
        data_info = "（未加载数据）"
        if context.data_columns:
            columns_str = ", ".join(context.data_columns[:30])
            if len(context.data_columns) > 30:
                columns_str += f" ... (共 {len(context.data_columns)} 列)"
            data_info = f"数据列名: {columns_str}"
            if context.data_preview:
                data_info += f"\n\n数据预览:\n{context.data_preview}"
        
        # 格式化对话历史
        history_text = "（无历史对话）"
        if context.conversation_history:
            history_lines = []
            for msg in context.conversation_history[-5:]:  # 只取最近5条
                role = "用户" if msg.get("role") == "user" else "助手"
                content = msg.get("content", "")[:200]  # 截断长消息
                history_lines.append(f"{role}: {content}")
            history_text = "\n".join(history_lines)
        
        return EXTRACTION_USER_PROMPT.format(
            user_message=context.user_message,
            workspace_files=workspace_files,
            data_info=data_info,
            conversation_history=history_text
        )
    
    def _get_task_definitions_text(self) -> str:
        """获取任务定义的文本描述"""
        tasks = self.registry.list_tasks()
        if not tasks:
            return "（无可用任务）"
        
        lines = []
        for task in tasks:
            task_id = task.get("task_id", "")
            task_name = task.get("task_name", "")
            description = task.get("description", "")
            
            # 获取完整任务定义以获取参数信息
            task_def = self.registry.get_task(task_id)
            if task_def:
                required_params = [p.name for p in task_def.required_params]
                optional_params = [p.name for p in task_def.optional_params[:5]]  # 只显示前5个可选参数
                
                lines.append(f"""
### {task_name} (task_id: {task_id})

{description}

**必需参数**: {', '.join(required_params) if required_params else '无'}
**可选参数**: {', '.join(optional_params) if optional_params else '无'}
""")
        
        return "\n".join(lines)
    
    async def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """调用 LLM API
        
        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            
        Returns:
            LLM 响应文本
        """
        if self._session is None:
            self._session = aiohttp.ClientSession()
        
        url = f"{self.api_base}/v1/chat/completions"
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.1,  # 低温度以获得更确定的输出
            "max_tokens": 1000
        }
        
        try:
            async with self._session.post(url, json=payload, timeout=30) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise RuntimeError(f"LLM API error: {resp.status} - {error_text}")
                
                data = await resp.json()
                return data["choices"][0]["message"]["content"]
                
        except aiohttp.ClientError as e:
            raise RuntimeError(f"LLM API connection error: {e}")
    
    def _parse_response(self, response: str) -> TaskIntent:
        """解析 LLM 响应
        
        Args:
            response: LLM 原始响应
            
        Returns:
            TaskIntent: 解析后的任务意图
        """
        # 尝试提取 JSON
        json_str = response
        
        # 处理 markdown 代码块
        if "```json" in response:
            match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
            if match:
                json_str = match.group(1)
        elif "```" in response:
            match = re.search(r"```\s*(.*?)\s*```", response, re.DOTALL)
            if match:
                json_str = match.group(1)
        
        # 尝试解析 JSON
        try:
            data = json.loads(json_str.strip())
        except json.JSONDecodeError:
            # 尝试修复常见的 JSON 错误
            json_str = json_str.replace("'", '"')  # 单引号替换为双引号
            try:
                data = json.loads(json_str.strip())
            except json.JSONDecodeError as e:
                logger.warning(f"[LLM Extractor] JSON parse error: {e}")
                return TaskIntent(
                    task_type="",
                    confidence=0.0,
                    params={},
                    missing_params=[],
                    clarification_needed=True,
                    clarification_question="抱歉，我无法正确解析您的请求。请更清晰地描述您想要执行的任务。"
                )
        
        return TaskIntent(
            task_type=data.get("task_type", ""),
            confidence=float(data.get("confidence", 0.0)),
            params=data.get("params", {}),
            missing_params=data.get("missing_params", []),
            clarification_needed=data.get("clarification_needed", False),
            clarification_question=data.get("clarification_question", "")
        )
    
    def _validate_and_enhance(self, intent: TaskIntent, context: ExtractionContext) -> TaskIntent:
        """验证和增强提取结果
        
        Args:
            intent: 原始提取结果
            context: 提取上下文
            
        Returns:
            TaskIntent: 验证和增强后的结果
        """
        # 验证任务类型是否存在
        if intent.task_type:
            task_def = self.registry.get_task(intent.task_type)
            if not task_def:
                logger.warning(f"[LLM Extractor] Unknown task type: {intent.task_type}")
                intent.task_type = ""
                intent.confidence = 0.0
                intent.clarification_needed = True
                intent.clarification_question = f"未知的任务类型。可用的任务有：规则挖掘(rule_mining)、评分卡开发(scorecard_dev)。"
                return intent
            
            # 检查必需参数（只检查 required=True 且 allow_empty=False 的参数）
            truly_required_params = [
                p for p in task_def.required_params 
                if p.required and not p.allow_empty
            ]
            required_param_names = [p.name for p in truly_required_params]
            missing = [p for p in required_param_names if p not in intent.params or not intent.params[p]]
            
            if missing and missing != intent.missing_params:
                intent.missing_params = missing
                if missing:
                    intent.clarification_needed = True
                    param_labels = []
                    for p_name in missing:
                        for p in truly_required_params:
                            if p.name == p_name:
                                param_labels.append(p.label)
                                break
                    intent.clarification_question = f"请提供以下必需参数：{', '.join(param_labels)}"
        
        # 如果有数据列名，尝试匹配参数值
        if context.data_columns and intent.params:
            intent.params = self._match_column_names(intent.params, context.data_columns)
        
        return intent
    
    def _match_column_names(self, params: dict[str, Any], columns: list[str]) -> dict[str, Any]:
        """匹配参数值与实际列名
        
        Args:
            params: 提取的参数
            columns: 实际数据列名
            
        Returns:
            匹配后的参数
        """
        columns_lower = {c.lower(): c for c in columns}
        
        def match_column(value: str) -> str:
            """尝试匹配单个列名"""
            if value in columns:
                return value
            if value.lower() in columns_lower:
                return columns_lower[value.lower()]
            # 模糊匹配
            for col in columns:
                if value.lower() in col.lower() or col.lower() in value.lower():
                    return col
            return value
        
        result = {}
        for key, value in params.items():
            if isinstance(value, str) and key in ("target", "target_col", "weight_col", "time_col", "sample_type_col"):
                result[key] = match_column(value)
            elif isinstance(value, list) and key in ("force_categorical", "feature_cols"):
                result[key] = [match_column(v) if isinstance(v, str) else v for v in value]
            else:
                result[key] = value
        
        return result
    
    async def close(self):
        """关闭资源"""
        if self._session:
            await self._session.close()
            self._session = None


# =============================================================================
# Factory Function
# =============================================================================

def create_param_extractor(
    api_base: str = "http://localhost:8200/v1",
    model: str = "deepseek-chat"
) -> LLMParamExtractor:
    """创建参数推断器实例
    
    Args:
        api_base: LLM API 基础 URL
        model: LLM 模型名称
        
    Returns:
        LLMParamExtractor: 参数推断器实例
    """
    return LLMParamExtractor(api_base=api_base, model=model)


# =============================================================================
# Export
# =============================================================================

__all__ = [
    'TaskIntent',
    'ExtractionContext',
    'LLMParamExtractor',
    'create_param_extractor',
]
