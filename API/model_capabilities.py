"""
模型能力配置模块 - 定义各厂商模型对深度思考和联网搜索的支持情况

与前端 llm_manager_integrated/frontend/shared/js/model-config.js 保持同步

能力类型说明：
- thinking: 'forced' - 强制开启深度思考（推理模型，如deepseek-reasoner、o1系列）
- thinking: 'optional' - 可选深度思考（如claude-3.5-sonnet、gemini-2.x）
- thinking: 'none' - 不支持深度思考
- web_search: True/False - 是否支持联网搜索
- supports_stream: True/False - 是否支持流式输出（默认True，o1系列为False）

最后更新: 2026-02-11，基于各供应商官方文档
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, Dict

logger = logging.getLogger(__name__)


@dataclass
class ModelCapability:
    """模型能力配置"""
    thinking: str  # 'forced', 'optional', 'none'
    web_search: bool
    thinking_budget_default: Optional[int] = None
    max_tokens_limit: Optional[int] = None  # 新增：最大输出token限制
    supports_stream: bool = True  # 是否支持流式输出，默认True
    
    @property
    def is_reasoning_model(self) -> bool:
        """是否是推理模型（强制深度思考）"""
        return self.thinking == 'forced'
    
    @property
    def supports_thinking(self) -> bool:
        """是否支持深度思考（包括强制和可选）"""
        return self.thinking in ('forced', 'optional')
    
    @property
    def supports_web_search(self) -> bool:
        """是否支持联网搜索"""
        return self.web_search


# 模型能力配置表
# 与前端 model-config.js 中的 MODEL_CAPABILITIES 保持同步
# 与后端 llm_manager_integrated/api/routes/channels.py 中的 MODEL_CAPABILITIES 保持同步
MODEL_CAPABILITIES: Dict[str, ModelCapability] = {
    # ============================================================
    # DeepSeek 系列
    # 官方文档: https://api-docs.deepseek.com/
    # ============================================================
    'deepseek-chat': ModelCapability(
        thinking='none', web_search=True, max_tokens_limit=8192, supports_stream=True
    ),
    'deepseek-reasoner': ModelCapability(
        thinking='forced', web_search=False, thinking_budget_default=8192, 
        max_tokens_limit=64000, supports_stream=True
    ),
    
    # ============================================================
    # OpenAI 系列
    # 官方文档: https://platform.openai.com/docs/models
    # ============================================================
    # GPT-4.1 系列 (2025年4月发布)
    'gpt-4.1': ModelCapability(
        thinking='none', web_search=False, max_tokens_limit=32768, supports_stream=True
    ),
    'gpt-4.1-mini': ModelCapability(
        thinking='none', web_search=False, max_tokens_limit=32768, supports_stream=True
    ),
    'gpt-4.1-nano': ModelCapability(
        thinking='none', web_search=False, max_tokens_limit=32768, supports_stream=True
    ),
    # GPT-4o 系列
    'gpt-4o': ModelCapability(
        thinking='none', web_search=False, max_tokens_limit=16384, supports_stream=True
    ),
    'gpt-4o-mini': ModelCapability(
        thinking='none', web_search=False, max_tokens_limit=16384, supports_stream=True
    ),
    # GPT-4 系列
    'gpt-4': ModelCapability(
        thinking='none', web_search=False, max_tokens_limit=8192, supports_stream=True
    ),
    'gpt-4-turbo': ModelCapability(
        thinking='none', web_search=False, max_tokens_limit=4096, supports_stream=True
    ),
    # GPT-3.5 系列
    'gpt-3.5-turbo': ModelCapability(
        thinking='none', web_search=False, max_tokens_limit=4096, supports_stream=True
    ),
    # OpenAI o系列推理模型（不支持流式）
    'o1': ModelCapability(
        thinking='forced', web_search=False, max_tokens_limit=100000, supports_stream=False
    ),
    'o1-preview': ModelCapability(
        thinking='forced', web_search=False, max_tokens_limit=32768, supports_stream=False
    ),
    'o1-mini': ModelCapability(
        thinking='forced', web_search=False, max_tokens_limit=65536, supports_stream=False
    ),
    'o3': ModelCapability(
        thinking='forced', web_search=False, max_tokens_limit=100000, supports_stream=False
    ),
    'o3-mini': ModelCapability(
        thinking='forced', web_search=False, max_tokens_limit=100000, supports_stream=False
    ),
    'o4-mini': ModelCapability(
        thinking='forced', web_search=False, max_tokens_limit=100000, supports_stream=False
    ),
    
    # ============================================================
    # Anthropic Claude 系列
    # 官方文档: https://docs.anthropic.com/en/docs/about-claude/models
    # ============================================================
    # Claude 4.x 系列（最新）
    'claude-opus-4-6': ModelCapability(
        thinking='optional', web_search=False, thinking_budget_default=16384,
        max_tokens_limit=128000, supports_stream=True
    ),
    'claude-sonnet-4-5': ModelCapability(
        thinking='optional', web_search=False, thinking_budget_default=10000,
        max_tokens_limit=64000, supports_stream=True
    ),
    'claude-haiku-4-5': ModelCapability(
        thinking='optional', web_search=False, thinking_budget_default=8192,
        max_tokens_limit=64000, supports_stream=True
    ),
    'claude-sonnet-4': ModelCapability(
        thinking='optional', web_search=False, thinking_budget_default=10000,
        max_tokens_limit=64000, supports_stream=True
    ),
    'claude-opus-4': ModelCapability(
        thinking='optional', web_search=False, thinking_budget_default=16384,
        max_tokens_limit=128000, supports_stream=True
    ),
    # Claude 3.x 系列
    'claude-3-5-sonnet': ModelCapability(
        thinking='optional', web_search=False, thinking_budget_default=10000,
        max_tokens_limit=8192, supports_stream=True
    ),
    'claude-3.5-sonnet': ModelCapability(
        thinking='optional', web_search=False, thinking_budget_default=10000,
        max_tokens_limit=8192, supports_stream=True
    ),
    'claude-3-opus': ModelCapability(
        thinking='optional', web_search=False, thinking_budget_default=16384,
        max_tokens_limit=4096, supports_stream=True
    ),
    'claude-3-haiku': ModelCapability(
        thinking='none', web_search=False, max_tokens_limit=4096, supports_stream=True
    ),
    
    # ============================================================
    # Google Gemini 系列
    # 官方文档: https://ai.google.dev/gemini-api/docs/models
    # ============================================================
    # Gemini 3.x 系列
    'gemini-3-pro': ModelCapability(
        thinking='optional', web_search=True, thinking_budget_default=16384,
        max_tokens_limit=65536, supports_stream=True
    ),
    'gemini-3-pro-preview': ModelCapability(
        thinking='optional', web_search=True, thinking_budget_default=16384,
        max_tokens_limit=65536, supports_stream=True
    ),
    'gemini-3-flash': ModelCapability(
        thinking='optional', web_search=True, thinking_budget_default=8192,
        max_tokens_limit=65536, supports_stream=True
    ),
    'gemini-3-flash-preview': ModelCapability(
        thinking='optional', web_search=True, thinking_budget_default=8192,
        max_tokens_limit=65536, supports_stream=True
    ),
    # Gemini 2.5 系列
    'gemini-2.5-pro': ModelCapability(
        thinking='optional', web_search=True, thinking_budget_default=16384,
        max_tokens_limit=65536, supports_stream=True
    ),
    'gemini-2.5-flash': ModelCapability(
        thinking='optional', web_search=True, thinking_budget_default=8192,
        max_tokens_limit=65536, supports_stream=True
    ),
    'gemini-2.5-flash-lite': ModelCapability(
        thinking='optional', web_search=True, thinking_budget_default=8192,
        max_tokens_limit=65536, supports_stream=True
    ),
    # Gemini 2.0 系列
    'gemini-2.0-flash': ModelCapability(
        thinking='optional', web_search=True, thinking_budget_default=8192,
        max_tokens_limit=8192, supports_stream=True
    ),
    'gemini-2.0-flash-thinking': ModelCapability(
        thinking='optional', web_search=True, thinking_budget_default=8192,
        max_tokens_limit=8192, supports_stream=True
    ),
    
    # ============================================================
    # MoonshotAI (月之暗面/Kimi) 系列
    # 官方文档: https://huggingface.co/moonshotai
    # 仅支持K2和K2.5系列，最大输出32K
    # ============================================================
    # Kimi-K2-Instruct（1T参数MoE模型，指令微调版本）
    'kimi-k2-instruct': ModelCapability(
        thinking='optional', web_search=True, thinking_budget_default=8192,
        max_tokens_limit=32768, supports_stream=True  # 32K
    ),
    # Kimi-K2-Thinking（170B参数，强思维链能力）
    'kimi-k2-thinking': ModelCapability(
        thinking='forced', web_search=False, thinking_budget_default=16384,
        max_tokens_limit=32768, supports_stream=True  # 32K
    ),
    # Kimi-K2.5（171B参数，视觉智能体模型）
    'kimi-k2.5': ModelCapability(
        thinking='optional', web_search=True, thinking_budget_default=8192,
        max_tokens_limit=32768, supports_stream=True  # 32K
    ),
    
    # ============================================================
    # 智谱AI (Zhipu/GLM) 系列
    # 仅支持GLM-4.6和GLM-4.7系列
    # ============================================================
    # GLM-4.7（高智能旗舰，200K上下文，128K输出）
    'glm-4.7': ModelCapability(
        thinking='optional', web_search=True, thinking_budget_default=16384,
        max_tokens_limit=131072, supports_stream=True  # 128K
    ),
    # GLM-4.6（超强性能，200K上下文，128K输出）
    'glm-4.6': ModelCapability(
        thinking='optional', web_search=True, thinking_budget_default=16384,
        max_tokens_limit=131072, supports_stream=True  # 128K
    ),
    
    # ============================================================
    # 通义千问 (Qwen) 系列
    # 官方文档: https://huggingface.co/Qwen
    # Qwen3-235B-A22B系列（MoE架构，235B参数，22B激活）
    # ============================================================
    # Qwen3-VL-235B-A22B-Thinking（视觉多模态推理模型，256K上下文）
    'qwen3-vl-235b-a22b-thinking': ModelCapability(
        thinking='forced', web_search=False, thinking_budget_default=16384,
        max_tokens_limit=32768, supports_stream=True  # 推荐32K
    ),
    # Qwen3-VL-235B-A22B-Instruct（视觉多模态指令模型，256K上下文）
    'qwen3-vl-235b-a22b-instruct': ModelCapability(
        thinking='none', web_search=False, max_tokens_limit=16384, supports_stream=True
    ),
    # Qwen3-235B-A22B-Thinking-2507（纯文本推理模型，256K上下文，SOTA级推理能力）
    'qwen3-235b-a22b-thinking-2507': ModelCapability(
        thinking='forced', web_search=False, thinking_budget_default=32768,
        max_tokens_limit=81920, supports_stream=True  # 复杂任务建议81920
    ),
    # Qwen3-235B-A22B-Instruct-2507（纯文本指令模型，256K上下文）
    'qwen3-235b-a22b-instruct-2507': ModelCapability(
        thinking='none', web_search=False, max_tokens_limit=16384, supports_stream=True
    ),
    
    # 默认配置（未知模型，默认支持流式）
    '_default': ModelCapability(
        thinking='optional', web_search=False, thinking_budget_default=8192,
        max_tokens_limit=4096, supports_stream=True
    ),
}


def get_model_capabilities(model_name: str) -> ModelCapability:
    """
    获取模型能力配置
    
    Args:
        model_name: 模型名称
        
    Returns:
        ModelCapability: 模型能力配置
        
    匹配逻辑：
    1. 精确匹配
    2. 模糊匹配（模型名包含配置表中的key）
    3. 基于模型名称推断
    4. 返回默认配置
    """
    if not model_name:
        return MODEL_CAPABILITIES['_default']
    
    lower_name = model_name.lower()
    
    # 1. 精确匹配
    if lower_name in MODEL_CAPABILITIES:
        return MODEL_CAPABILITIES[lower_name]
    
    # 2. 模糊匹配
    for key, capability in MODEL_CAPABILITIES.items():
        if key != '_default' and key in lower_name:
            return capability
    
    # 3. 基于模型名称推断
    # DeepSeek推理模型
    if 'reasoner' in lower_name or '-r1' in lower_name:
        return ModelCapability(
            thinking='forced', web_search=False, thinking_budget_default=8192,
            max_tokens_limit=64000, supports_stream=True
        )
    
    # Gemini 3.x 系列
    if 'gemini-3' in lower_name:
        return ModelCapability(
            thinking='optional', web_search=True, thinking_budget_default=16384,
            max_tokens_limit=65536, supports_stream=True
        )
    
    # Gemini 2.x 系列
    if 'gemini-2' in lower_name:
        return ModelCapability(
            thinking='optional', web_search=True, thinking_budget_default=8192,
            max_tokens_limit=65536, supports_stream=True
        )
    
    # Claude 系列
    if 'claude' in lower_name:
        if 'opus' in lower_name:
            return ModelCapability(
                thinking='optional', web_search=False, thinking_budget_default=16384,
                max_tokens_limit=128000, supports_stream=True
            )
        elif 'sonnet' in lower_name:
            return ModelCapability(
                thinking='optional', web_search=False, thinking_budget_default=10000,
                max_tokens_limit=64000, supports_stream=True
            )
        elif 'haiku' in lower_name:
            return ModelCapability(
                thinking='none', web_search=False, max_tokens_limit=64000, supports_stream=True
            )
        else:
            return ModelCapability(
                thinking='optional', web_search=False, thinking_budget_default=10000,
                max_tokens_limit=8192, supports_stream=True
            )
    
    # GPT-4.1 系列
    if 'gpt-4.1' in lower_name:
        return ModelCapability(
            thinking='none', web_search=False, max_tokens_limit=32768, supports_stream=True
        )
    
    # MoonshotAI/Kimi K2/K2.5 系列（32K输出）
    if 'kimi' in lower_name:
        if 'k2.5' in lower_name:
            return ModelCapability(
                thinking='optional', web_search=True, thinking_budget_default=8192,
                max_tokens_limit=32768, supports_stream=True
            )
        elif 'k2-thinking' in lower_name:
            return ModelCapability(
                thinking='forced', web_search=False, thinking_budget_default=16384,
                max_tokens_limit=32768, supports_stream=True
            )
        elif 'k2' in lower_name:
            return ModelCapability(
                thinking='optional', web_search=True, thinking_budget_default=8192,
                max_tokens_limit=32768, supports_stream=True
            )
        else:
            # 未知Kimi模型，使用默认配置
            return ModelCapability(
                thinking='optional', web_search=True, thinking_budget_default=8192,
                max_tokens_limit=32768, supports_stream=True
            )
    
    # 智谱AI GLM-4.6/4.7 系列
    if 'glm' in lower_name:
        if '4.7-flashx' in lower_name:
            return ModelCapability(
                thinking='none', web_search=True, max_tokens_limit=131072, supports_stream=True
            )
        elif '4.7' in lower_name or '4.6' in lower_name:
            return ModelCapability(
                thinking='optional', web_search=True, thinking_budget_default=16384,
                max_tokens_limit=131072, supports_stream=True
            )
        else:
            # 未知GLM模型，使用默认配置
            return ModelCapability(
                thinking='optional', web_search=True, thinking_budget_default=16384,
                max_tokens_limit=131072, supports_stream=True
            )
    
    # 通义千问 Qwen3系列
    if 'qwen' in lower_name:
        # Qwen3-VL 视觉多模态系列
        if 'qwen3-vl' in lower_name:
            if 'thinking' in lower_name:
                return ModelCapability(
                    thinking='forced', web_search=False, thinking_budget_default=16384,
                    max_tokens_limit=32768, supports_stream=True
                )
            else:  # instruct
                return ModelCapability(
                    thinking='none', web_search=False, max_tokens_limit=16384, supports_stream=True
                )
        # Qwen3纯文本系列
        elif 'qwen3' in lower_name:
            if 'thinking' in lower_name:
                return ModelCapability(
                    thinking='forced', web_search=False, thinking_budget_default=32768,
                    max_tokens_limit=81920, supports_stream=True
                )
            else:  # instruct
                return ModelCapability(
                    thinking='none', web_search=False, max_tokens_limit=16384, supports_stream=True
                )
        else:
            # 未知Qwen模型，使用默认配置
            return ModelCapability(
                thinking='none', web_search=False, max_tokens_limit=16384, supports_stream=True
            )
    
    # 4. 返回默认配置
    return MODEL_CAPABILITIES['_default']


def is_reasoning_model(model_name: str) -> bool:
    """
    判断是否是推理模型（强制深度思考）
    
    推理模型特点：
    - 深度思考功能内置且不可关闭
    - 不需要也不应该传递 enable_deep_thinking 参数
    - 可能有特殊的API调用方式
    
    Args:
        model_name: 模型名称
        
    Returns:
        bool: 是否是推理模型
    """
    return get_model_capabilities(model_name).is_reasoning_model


def get_effective_thinking_config(
    model_name: str,
    user_enable_thinking: bool,
    user_thinking_budget: Optional[int]
) -> tuple[bool, Optional[int]]:
    """
    获取有效的深度思考配置
    
    根据模型能力和用户配置，确定最终的深度思考设置
    
    Args:
        model_name: 模型名称
        user_enable_thinking: 用户配置的是否启用深度思考
        user_thinking_budget: 用户配置的思考预算
        
    Returns:
        tuple[bool, Optional[int]]: (是否启用深度思考, 思考预算)
        
    逻辑：
    - 推理模型（forced）：强制启用，忽略用户配置
    - 可选模型（optional）：使用用户配置
    - 不支持（none）：强制禁用，忽略用户配置
    """
    capability = get_model_capabilities(model_name)
    
    if capability.thinking == 'forced':
        # 推理模型：强制启用
        # 注意：对于deepseek-reasoner等，不需要传递额外参数，推理是内置的
        return True, user_thinking_budget or capability.thinking_budget_default
    
    elif capability.thinking == 'optional':
        # 可选模型：使用用户配置
        if user_enable_thinking:
            budget = user_thinking_budget or capability.thinking_budget_default
            return True, budget
        return False, None
    
    else:
        # 不支持深度思考
        if user_enable_thinking:
            logger.warning(f"模型 {model_name} 不支持深度思考，已忽略配置")
        return False, None


def get_effective_web_search_config(
    model_name: str,
    user_enable_web_search: bool
) -> bool:
    """
    获取有效的联网搜索配置
    
    Args:
        model_name: 模型名称
        user_enable_web_search: 用户配置的是否启用联网搜索
        
    Returns:
        bool: 是否启用联网搜索
    """
    capability = get_model_capabilities(model_name)
    
    if not capability.web_search:
        if user_enable_web_search:
            logger.warning(f"模型 {model_name} 不支持联网搜索，已忽略配置")
        return False
    
    return user_enable_web_search


def get_effective_stream_config(
    model_name: str,
    user_enable_stream: bool
) -> bool:
    """
    获取有效的流式输出配置
    
    如果模型不支持流式输出（如o1系列），则强制返回False
    
    Args:
        model_name: 模型名称
        user_enable_stream: 用户配置的是否启用流式输出
        
    Returns:
        bool: 是否启用流式输出
    """
    capability = get_model_capabilities(model_name)
    
    if not capability.supports_stream:
        if user_enable_stream:
            logger.warning(f"模型 {model_name} 不支持流式输出，已强制关闭")
        return False
    
    return user_enable_stream
