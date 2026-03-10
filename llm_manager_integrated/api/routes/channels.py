"""
渠道管理路由
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import httpx
import json

from llm_manager_integrated.models import schemas, orm
from llm_manager_integrated.core import crud
from llm_manager_integrated.utils import security
from llm_manager_integrated.api.responses import success_response, error_response
from ..dependencies import get_db
from llm_manager_integrated.core.load_balancer import get_load_balancer, create_channel_from_config
from llm_manager_integrated.core.config import settings
# NOTE: invalidate_models_cache 延迟导入以避免循环导入

logger = logging.getLogger(__name__)


router = APIRouter()


def _invalidate_models_cache():
    """延迟导入并调用 invalidate_models_cache 以避免循环导入"""
    from llm_manager_integrated.api.routes.proxy.models_proxy import invalidate_models_cache
    invalidate_models_cache()


# ============================================================
# 模型参数范围配置（前端控件使用）
# ============================================================

# 默认参数范围配置
DEFAULT_PARAM_LIMITS = {
    'temperature': {'min': 0, 'max': 2, 'step': 0.1, 'default': 0.7},
    'top_p': {'min': 0, 'max': 1, 'step': 0.05, 'default': 1.0},
    'max_tokens': {'min': 100, 'max': 4096, 'step': 100, 'default': 2000},
    'frequency_penalty': {'min': -2, 'max': 2, 'step': 0.1, 'default': 0.0},
    'presence_penalty': {'min': -2, 'max': 2, 'step': 0.1, 'default': 0.0},
    'thinking_budget': {'min': 1024, 'max': 32768, 'step': 1024, 'default': 8192},
}

# 模型能力配置表（从前端迁移）
# supports_stream: 是否支持流式输出（默认True，仅不支持的模型需要显式设置为False）
# 最后更新: 2026-02-11，基于各供应商官方文档
MODEL_CAPABILITIES = {
    # ============================================================
    # DeepSeek 系列
    # 官方文档: https://api-docs.deepseek.com/
    # ============================================================
    # DeepSeek-V3.2 对话模型
    'deepseek-chat': {
        'thinking': 'none',
        'web_search': True,
        'max_tokens_limit': 8192,  # 官方: 默认4K，最大8K
        'supports_stream': True
    },
    # DeepSeek-V3.2 推理模型（思考模式）
    'deepseek-reasoner': {
        'thinking': 'forced',
        'web_search': False,
        'thinking_budget_default': 8192,
        'max_tokens_limit': 64000,  # 官方: 默认32K，最大64K
        'supports_stream': True
    },
    'deepseek-r1': {
        'thinking': 'forced',
        'web_search': False,
        'thinking_budget_default': 8192,
        'max_tokens_limit': 64000,
        'supports_stream': True
    },
    
    # ============================================================
    # OpenAI 系列
    # 官方文档: https://platform.openai.com/docs/models
    # ============================================================
    # GPT-4.1 系列 (2025年4月发布，100万上下文，32K输出)
    'gpt-4.1': {'thinking': 'none', 'web_search': False, 'max_tokens_limit': 32768, 'supports_stream': True},
    'gpt-4.1-mini': {'thinking': 'none', 'web_search': False, 'max_tokens_limit': 32768, 'supports_stream': True},
    'gpt-4.1-nano': {'thinking': 'none', 'web_search': False, 'max_tokens_limit': 32768, 'supports_stream': True},
    # GPT-4o 系列
    'gpt-4o': {'thinking': 'none', 'web_search': False, 'max_tokens_limit': 16384, 'supports_stream': True},
    'gpt-4o-mini': {'thinking': 'none', 'web_search': False, 'max_tokens_limit': 16384, 'supports_stream': True},
    # GPT-4 系列
    'gpt-4': {'thinking': 'none', 'web_search': False, 'max_tokens_limit': 8192, 'supports_stream': True},
    'gpt-4-turbo': {'thinking': 'none', 'web_search': False, 'max_tokens_limit': 4096, 'supports_stream': True},
    # GPT-3.5 系列
    'gpt-3.5-turbo': {'thinking': 'none', 'web_search': False, 'max_tokens_limit': 4096, 'supports_stream': True},
    'gpt-3.5-turbo-16k': {'thinking': 'none', 'web_search': False, 'max_tokens_limit': 16384, 'supports_stream': True},
    # OpenAI o系列推理模型（不支持流式输出）
    'o1': {'thinking': 'forced', 'web_search': False, 'max_tokens_limit': 100000, 'supports_stream': False},
    'o1-preview': {'thinking': 'forced', 'web_search': False, 'max_tokens_limit': 32768, 'supports_stream': False},
    'o1-mini': {'thinking': 'forced', 'web_search': False, 'max_tokens_limit': 65536, 'supports_stream': False},
    'o3': {'thinking': 'forced', 'web_search': False, 'max_tokens_limit': 100000, 'supports_stream': False},
    'o3-mini': {'thinking': 'forced', 'web_search': False, 'max_tokens_limit': 100000, 'supports_stream': False},
    'o4-mini': {'thinking': 'forced', 'web_search': False, 'max_tokens_limit': 100000, 'supports_stream': False},
    
    # ============================================================
    # Anthropic Claude 系列
    # 官方文档: https://docs.anthropic.com/en/docs/about-claude/models
    # ============================================================
    # Claude 4.x 系列（最新）
    'claude-opus-4-6': {
        'thinking': 'optional',
        'web_search': False,
        'thinking_budget_default': 16384,
        'max_tokens_limit': 128000,  # 官方: 最大输出128K
        'supports_stream': True
    },
    'claude-sonnet-4-5': {
        'thinking': 'optional',
        'web_search': False,
        'thinking_budget_default': 10000,
        'max_tokens_limit': 64000,  # 官方: 最大输出64K
        'supports_stream': True
    },
    'claude-haiku-4-5': {
        'thinking': 'optional',
        'web_search': False,
        'thinking_budget_default': 8192,
        'max_tokens_limit': 64000,
        'supports_stream': True
    },
    # Claude Sonnet 4（旧版命名）
    'claude-sonnet-4': {
        'thinking': 'optional',
        'web_search': False,
        'thinking_budget_default': 10000,
        'max_tokens_limit': 64000,
        'supports_stream': True
    },
    'claude-opus-4': {
        'thinking': 'optional',
        'web_search': False,
        'thinking_budget_default': 16384,
        'max_tokens_limit': 128000,
        'supports_stream': True
    },
    # Claude 3.x 系列
    'claude-3-5-sonnet': {
        'thinking': 'optional',
        'web_search': False,
        'thinking_budget_default': 10000,
        'max_tokens_limit': 8192,
        'supports_stream': True
    },
    'claude-3.5-sonnet': {
        'thinking': 'optional',
        'web_search': False,
        'thinking_budget_default': 10000,
        'max_tokens_limit': 8192,
        'supports_stream': True
    },
    'claude-3-opus': {
        'thinking': 'optional',
        'web_search': False,
        'thinking_budget_default': 16384,
        'max_tokens_limit': 4096,
        'supports_stream': True
    },
    'claude-3-haiku': {'thinking': 'none', 'web_search': False, 'max_tokens_limit': 4096, 'supports_stream': True},
    
    # ============================================================
    # Google Gemini 系列
    # 官方文档: https://ai.google.dev/gemini-api/docs/models
    # ============================================================
    # Gemini 3.x 系列（最新）
    'gemini-3-pro': {
        'thinking': 'optional',
        'web_search': True,
        'thinking_budget_default': 16384,
        'max_tokens_limit': 65536,
        'supports_stream': True
    },
    'gemini-3-pro-preview': {
        'thinking': 'optional',
        'web_search': True,
        'thinking_budget_default': 16384,
        'max_tokens_limit': 65536,
        'supports_stream': True
    },
    'gemini-3-flash': {
        'thinking': 'optional',
        'web_search': True,
        'thinking_budget_default': 8192,
        'max_tokens_limit': 65536,
        'supports_stream': True
    },
    'gemini-3-flash-preview': {
        'thinking': 'optional',
        'web_search': True,
        'thinking_budget_default': 8192,
        'max_tokens_limit': 65536,
        'supports_stream': True
    },
    # Gemini 2.5 系列
    'gemini-2.5-pro': {
        'thinking': 'optional',
        'web_search': True,
        'thinking_budget_default': 16384,
        'max_tokens_limit': 65536,
        'supports_stream': True
    },
    'gemini-2.5-flash': {
        'thinking': 'optional',
        'web_search': True,
        'thinking_budget_default': 8192,
        'max_tokens_limit': 65536,
        'supports_stream': True
    },
    'gemini-2.5-flash-lite': {
        'thinking': 'optional',
        'web_search': True,
        'thinking_budget_default': 8192,
        'max_tokens_limit': 65536,
        'supports_stream': True
    },
    # Gemini 2.0 系列
    'gemini-2.0-flash': {
        'thinking': 'optional',
        'web_search': True,
        'thinking_budget_default': 8192,
        'max_tokens_limit': 8192,
        'supports_stream': True
    },
    'gemini-2.0-flash-thinking': {
        'thinking': 'optional',
        'web_search': True,
        'thinking_budget_default': 8192,
        'max_tokens_limit': 8192,
        'supports_stream': True
    },
    
    # ============================================================
    # MoonshotAI (月之暗面/Kimi) 系列
    # 官方文档: https://huggingface.co/moonshotai
    # 仅支持K2和K2.5系列，最大输出32K
    # ============================================================
    # Kimi-K2-Instruct（1T参数MoE模型，指令微调版本）
    'kimi-k2-instruct': {
        'thinking': 'optional',
        'web_search': True,
        'thinking_budget_default': 8192,
        'max_tokens_limit': 32768,  # 32K
        'supports_stream': True
    },
    # Kimi-K2-Thinking（170B参数，强思维链能力）
    'kimi-k2-thinking': {
        'thinking': 'forced',
        'web_search': False,
        'thinking_budget_default': 16384,
        'max_tokens_limit': 32768,  # 32K
        'supports_stream': True
    },
    # Kimi-K2.5（171B参数，视觉智能体模型，Image-Text-to-Text）
    'kimi-k2.5': {
        'thinking': 'optional',
        'web_search': True,
        'thinking_budget_default': 8192,
        'max_tokens_limit': 32768,  # 32K
        'supports_stream': True
    },
    
    # ============================================================
    # 智谱AI (Zhipu/GLM) 系列
    # 仅支持GLM-4.6和GLM-4.7系列
    # ============================================================
    # GLM-4.7（高智能旗舰，200K上下文，128K输出）
    'glm-4.7': {
        'thinking': 'optional',
        'web_search': True,
        'thinking_budget_default': 16384,
        'max_tokens_limit': 131072,  # 128K
        'supports_stream': True
    },
    # GLM-4.6（超强性能，200K上下文，128K输出）
    'glm-4.6': {
        'thinking': 'optional',
        'web_search': True,
        'thinking_budget_default': 16384,
        'max_tokens_limit': 131072,  # 128K
        'supports_stream': True
    },
    
    # ============================================================
    # 通义千问 (Qwen) 系列
    # 官方文档: https://huggingface.co/Qwen
    # Qwen3-235B-A22B系列（MoE架构，235B参数，22B激活）
    # ============================================================
    # Qwen3-VL-235B-A22B-Thinking（视觉多模态推理模型，256K上下文）
    'qwen3-vl-235b-a22b-thinking': {
        'thinking': 'forced',
        'web_search': False,
        'thinking_budget_default': 16384,
        'max_tokens_limit': 32768,  # 推荐32K
        'supports_stream': True
    },
    # Qwen3-VL-235B-A22B-Instruct（视觉多模态指令模型，256K上下文）
    'qwen3-vl-235b-a22b-instruct': {
        'thinking': 'none',
        'web_search': False,
        'max_tokens_limit': 16384,  # 推荐16K
        'supports_stream': True
    },
    # Qwen3-235B-A22B-Thinking-2507（纯文本推理模型，256K上下文，SOTA级推理能力）
    'qwen3-235b-a22b-thinking-2507': {
        'thinking': 'forced',
        'web_search': False,
        'thinking_budget_default': 32768,
        'max_tokens_limit': 81920,  # 复杂任务建议81920
        'supports_stream': True
    },
    # Qwen3-235B-A22B-Instruct-2507（纯文本指令模型，256K上下文）
    'qwen3-235b-a22b-instruct-2507': {
        'thinking': 'none',
        'web_search': False,
        'max_tokens_limit': 16384,  # 推荐16K
        'supports_stream': True
    },
}

# 默认配置（未知模型）
DEFAULT_CAPABILITY = {
    'thinking': 'optional',
    'web_search': False,
    'thinking_budget_default': 8192,
    'max_tokens_limit': 4096,
    'supports_stream': True  # 默认支持流式输出
}


def get_model_capabilities(model_name: str) -> dict:
    """获取模型能力配置"""
    if not model_name:
        return DEFAULT_CAPABILITY.copy()
    
    lower_name = model_name.lower()
    
    # 精确匹配
    if lower_name in MODEL_CAPABILITIES:
        return MODEL_CAPABILITIES[lower_name].copy()
    
    # 模糊匹配
    for key, value in MODEL_CAPABILITIES.items():
        if key in lower_name:
            return value.copy()
    
    # 基于模型名称推断
    # DeepSeek 推理模型
    if 'reasoner' in lower_name or '-r1' in lower_name:
        return {
            'thinking': 'forced',
            'web_search': False,
            'thinking_budget_default': 8192,
            'max_tokens_limit': 64000,
            'supports_stream': True
        }
    
    # Gemini 3.x 系列
    if 'gemini-3' in lower_name:
        return {
            'thinking': 'optional',
            'web_search': True,
            'thinking_budget_default': 16384,
            'max_tokens_limit': 65536,
            'supports_stream': True
        }
    
    # Gemini 2.x 系列
    if 'gemini-2' in lower_name:
        return {
            'thinking': 'optional',
            'web_search': True,
            'thinking_budget_default': 8192,
            'max_tokens_limit': 65536,
            'supports_stream': True
        }
    
    # Claude 系列
    if 'claude' in lower_name:
        if 'opus' in lower_name:
            return {
                'thinking': 'optional',
                'web_search': False,
                'thinking_budget_default': 16384,
                'max_tokens_limit': 128000,
                'supports_stream': True
            }
        elif 'sonnet' in lower_name:
            return {
                'thinking': 'optional',
                'web_search': False,
                'thinking_budget_default': 10000,
                'max_tokens_limit': 64000,
                'supports_stream': True
            }
        elif 'haiku' in lower_name:
            return {'thinking': 'none', 'web_search': False, 'max_tokens_limit': 64000, 'supports_stream': True}
        else:
            return {
                'thinking': 'optional',
                'web_search': False,
                'thinking_budget_default': 10000,
                'max_tokens_limit': 8192,
                'supports_stream': True
            }
    
    # GPT-4.1 系列
    if 'gpt-4.1' in lower_name:
        return {'thinking': 'none', 'web_search': False, 'max_tokens_limit': 32768, 'supports_stream': True}
    
    # GPT-4 系列
    if 'gpt-4' in lower_name:
        if '32k' in lower_name:
            return {'thinking': 'none', 'web_search': False, 'max_tokens_limit': 32768, 'supports_stream': True}
        elif 'turbo' in lower_name:
            return {'thinking': 'none', 'web_search': False, 'max_tokens_limit': 4096, 'supports_stream': True}
        elif 'o' in lower_name:  # gpt-4o
            return {'thinking': 'none', 'web_search': False, 'max_tokens_limit': 16384, 'supports_stream': True}
        else:
            return {'thinking': 'none', 'web_search': False, 'max_tokens_limit': 8192, 'supports_stream': True}
    
    # GPT-3.5 系列
    if 'gpt-3.5' in lower_name or 'gpt-35' in lower_name:
        if '16k' in lower_name:
            return {'thinking': 'none', 'web_search': False, 'max_tokens_limit': 16384, 'supports_stream': True}
        else:
            return {'thinking': 'none', 'web_search': False, 'max_tokens_limit': 4096, 'supports_stream': True}
    
    # MoonshotAI/Kimi K2/K2.5 系列（32K输出）
    if 'kimi' in lower_name:
        if 'k2.5' in lower_name:
            return {
                'thinking': 'optional',
                'web_search': True,
                'thinking_budget_default': 8192,
                'max_tokens_limit': 32768,
                'supports_stream': True
            }
        elif 'k2-thinking' in lower_name:
            return {
                'thinking': 'forced',
                'web_search': False,
                'thinking_budget_default': 16384,
                'max_tokens_limit': 32768,
                'supports_stream': True
            }
        elif 'k2' in lower_name:
            return {
                'thinking': 'optional',
                'web_search': True,
                'thinking_budget_default': 8192,
                'max_tokens_limit': 32768,
                'supports_stream': True
            }
        else:
            # 未知Kimi模型，使用默认配置
            return {
                'thinking': 'optional',
                'web_search': True,
                'thinking_budget_default': 8192,
                'max_tokens_limit': 32768,
                'supports_stream': True
            }
    
    # 智谱AI GLM-4.6/4.7 系列
    if 'glm' in lower_name:
        if '4.7-flashx' in lower_name:
            return {'thinking': 'none', 'web_search': True, 'max_tokens_limit': 131072, 'supports_stream': True}
        elif '4.7' in lower_name or '4.6' in lower_name:
            return {
                'thinking': 'optional',
                'web_search': True,
                'thinking_budget_default': 16384,
                'max_tokens_limit': 131072,
                'supports_stream': True
            }
        else:
            # 未知GLM模型，使用默认配置
            return {
                'thinking': 'optional',
                'web_search': True,
                'thinking_budget_default': 16384,
                'max_tokens_limit': 131072,
                'supports_stream': True
            }
    
    # 通义千问 Qwen3系列
    if 'qwen' in lower_name:
        # Qwen3-VL 视觉多模态系列
        if 'qwen3-vl' in lower_name:
            if 'thinking' in lower_name:
                return {
                    'thinking': 'forced',
                    'web_search': False,
                    'thinking_budget_default': 16384,
                    'max_tokens_limit': 32768,
                    'supports_stream': True
                }
            else:  # instruct
                return {'thinking': 'none', 'web_search': False, 'max_tokens_limit': 16384, 'supports_stream': True}
        # Qwen3纯文本系列
        elif 'qwen3' in lower_name:
            if 'thinking' in lower_name:
                return {
                    'thinking': 'forced',
                    'web_search': False,
                    'thinking_budget_default': 32768,
                    'max_tokens_limit': 81920,
                    'supports_stream': True
                }
            else:  # instruct
                return {'thinking': 'none', 'web_search': False, 'max_tokens_limit': 16384, 'supports_stream': True}
        else:
            # 未知Qwen模型，使用默认配置
            return {'thinking': 'none', 'web_search': False, 'max_tokens_limit': 16384, 'supports_stream': True}
    
    return DEFAULT_CAPABILITY.copy()


def get_param_limits_for_model(model_name: str) -> dict:
    """获取模型的参数范围配置"""
    capabilities = get_model_capabilities(model_name)
    
    # 复制默认配置
    limits = {k: v.copy() for k, v in DEFAULT_PARAM_LIMITS.items()}
    
    # 根据模型能力调整 max_tokens 范围
    if capabilities.get('max_tokens_limit'):
        max_tokens_limit = capabilities['max_tokens_limit']
        # 最大值设置为模型支持的最大值
        limits['max_tokens']['max'] = max_tokens_limit
        # 默认值也设置为模型支持的最大值
        limits['max_tokens']['default'] = max_tokens_limit
        
        # 动态调整步长，确保从 min 开始能够精确到达 max
        min_val = limits['max_tokens']['min']
        range_val = max_tokens_limit - min_val
        
        # 选择能整除范围的合适步长
        if range_val > 10000:
            step = 256
        elif range_val > 4000:
            step = 128
        else:
            step = 100
        
        # 确保 (max - min) 能被步长整除，否则使用能整除的步长
        if range_val % step != 0:
            # 尝试其他常用步长
            for candidate_step in [128, 64, 32, 16, 8, 4, 2, 1]:
                if range_val % candidate_step == 0:
                    step = candidate_step
                    break
        
        limits['max_tokens']['step'] = step
    
    # 根据模型能力调整 thinking_budget 范围
    if capabilities.get('thinking_budget_default'):
        limits['thinking_budget']['default'] = capabilities['thinking_budget_default']
    
    return limits


# ============================================================
# 渠道管理路由
# ============================================================

@router.post("/channels")
def create_channel(channel: schemas.ChannelCreate, db: Session = Depends(get_db)):
    """创建新渠道"""
    try:
        result = crud.create_channel(db=db, channel=channel)
        
        # 使模型缓存失效
        _invalidate_models_cache()
        
        # 将新创建的渠道添加到负载均衡器
        try:
            load_balancer = get_load_balancer()
            if result.status:  # 只添加启用的渠道
                lb_channel = create_channel_from_config({
                    'id': str(result.id),
                    'name': result.name,
                    'api_base': result.base_url,
                    'api_key': result.api_key,
                    'model': result.models,
                    'type': result.type,
                    'weight': 1,
                    'max_qps': 10,
                    'timeout': 30
                })
                load_balancer.add_channel(lb_channel)
        except Exception as lb_error:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"渠道已创建但添加到负载均衡器失败: {lb_error}")
        
        return success_response(
            data=result.dict() if hasattr(result, 'dict') else result,
            message="渠道创建成功"
        )
    except Exception as e:
        logger.error(f"创建渠道失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=400,
            detail=error_response(code=400, message="创建渠道失败")
        )


@router.get("/channels")
def read_channels(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """获取渠道列表"""
    try:
        channels = crud.get_channels(db, skip=skip, limit=limit)
        channels_data = []
        
        for ch in channels:
            channel_dict = ch.dict() if hasattr(ch, 'dict') else ch
            model_config = crud.get_model_config_by_channel(db, channel_id=ch.id)
            channel_dict['has_model_config'] = model_config is not None
            if model_config:
                channel_dict['enable_web_search'] = model_config.enable_web_search
                channel_dict['enable_deep_thinking'] = model_config.enable_deep_thinking
            else:
                channel_dict['enable_web_search'] = False
                channel_dict['enable_deep_thinking'] = False
            channels_data.append(channel_dict)
        
        return success_response(
            data=channels_data,
            message="获取渠道列表成功"
        )
    except Exception as e:
        logger.error(f"获取渠道列表失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=error_response(code=500, message="获取渠道列表失败")
        )


@router.get("/channels/active")
def get_active_channels(db: Session = Depends(get_db)):
    """获取所有激活的渠道（支持多激活）"""
    try:
        active_channels = db.query(orm.Channel).filter(orm.Channel.status == True).all()
        
        channels_data = []
        for ch in active_channels:
            channel_dict = ch.dict() if hasattr(ch, 'dict') else ch.__dict__.copy()
            model_config = crud.get_model_config_by_channel(db, channel_id=ch.id)
            channel_dict['has_model_config'] = model_config is not None
            channels_data.append(channel_dict)
        
        return success_response(
            data=channels_data,
            message="获取激活渠道成功"
        )
    except Exception as e:
        logger.error(f"获取激活渠道失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=error_response(code=500, message="获取激活渠道失败")
        )


@router.get("/channels/active-configs")
def get_active_configs(db: Session = Depends(get_db)):
    """获取所有激活渠道的配置（用于三列式前端选择）"""
    try:
        active_channels = db.query(orm.Channel).filter(orm.Channel.status == True).all()
        
        configs = []
        for channel in active_channels:
            model_config = crud.get_model_config_by_channel(db, channel_id=channel.id)
            
            config_data = {
                "id": channel.id,
                "name": channel.name,
                "type": channel.type,
                "models": channel.models,
                "has_model_config": model_config is not None
            }
            
            if model_config:
                config_data["temperature"] = model_config.temperature
                config_data["top_p"] = model_config.top_p
                config_data["max_tokens"] = model_config.max_tokens
                config_data["frequency_penalty"] = model_config.frequency_penalty
                config_data["presence_penalty"] = model_config.presence_penalty
                config_data["system_prompt"] = model_config.system_prompt
                config_data["enable_web_search"] = model_config.enable_web_search
                config_data["enable_deep_thinking"] = model_config.enable_deep_thinking
                config_data["thinking_budget"] = model_config.thinking_budget
                config_data["include_thoughts"] = model_config.include_thoughts
            
            configs.append(config_data)
        
        return success_response(
            data=configs,
            message="获取激活配置成功"
        )
    except Exception as e:
        logger.error(f"获取激活配置失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=error_response(code=500, message="获取激活配置失败")
        )


@router.get("/channels/{channel_id}")
def read_channel(channel_id: int, db: Session = Depends(get_db)):
    """获取单个渠道"""
    db_channel = crud.get_channel(db, channel_id=channel_id)
    if db_channel is None:
        raise HTTPException(
            status_code=404,
            detail=error_response(code=404, message="渠道未找到")
        )
    
    channel_dict = db_channel.dict() if hasattr(db_channel, 'dict') else db_channel
    model_config = crud.get_model_config_by_channel(db, channel_id=channel_id)
    channel_dict['has_model_config'] = model_config is not None
    
    return success_response(
        data=channel_dict,
        message="获取渠道成功"
    )


@router.put("/channels/{channel_id}")
def update_channel(channel_id: int, channel_update: schemas.ChannelUpdate, db: Session = Depends(get_db)):
    """更新渠道"""
    db_channel = crud.update_channel(db, channel_id=channel_id, channel_update=channel_update)
    if db_channel is None:
        raise HTTPException(
            status_code=404,
            detail=error_response(code=404, message="渠道未找到")
        )
    
    _invalidate_models_cache()
    
    try:
        load_balancer = get_load_balancer()
        channel_id_str = str(db_channel.id)
        
        if db_channel.status:
            lb_channel = create_channel_from_config({
                'id': channel_id_str,
                'name': db_channel.name,
                'api_base': db_channel.base_url,
                'api_key': db_channel.api_key,
                'model': db_channel.models,
                'type': db_channel.type,
                'weight': 1,
                'max_qps': 10,
                'timeout': 30
            })
            if channel_id_str in load_balancer.channels:
                load_balancer.remove_channel(channel_id_str)
            load_balancer.add_channel(lb_channel)
            
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"渠道 {db_channel.name} 已添加到负载均衡器")
        else:
            if channel_id_str in load_balancer.channels:
                load_balancer.remove_channel(channel_id_str)
                
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"渠道 {db_channel.name} 已从负载均衡器中移除")
    except Exception as lb_error:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"渠道已更新但负载均衡器同步失败: {lb_error}")
    
    return success_response(
        data=db_channel.dict() if hasattr(db_channel, 'dict') else db_channel,
        message="渠道更新成功"
    )


@router.delete("/channels/{channel_id}")
def delete_channel(channel_id: int, db: Session = Depends(get_db)):
    """删除渠道"""
    db_channel = crud.delete_channel(db, channel_id=channel_id)
    if db_channel is None:
        raise HTTPException(
            status_code=404,
            detail=error_response(code=404, message="渠道未找到")
        )
    
    _invalidate_models_cache()
    
    return success_response(
        data=db_channel.dict() if hasattr(db_channel, 'dict') else db_channel,
        message="渠道删除成功"
    )


@router.post("/test-model-response")
async def test_model_response(test_data: dict, db: Session = Depends(get_db)):
    """测试模型响应"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"收到模型测试请求: {test_data}")
    
    try:
        name = test_data.get("name")
        type = test_data.get("type")
        model = test_data.get("models")
        base_url = test_data.get("base_url")
        api_key = test_data.get("api_key")
        test_message = test_data.get("test_message", "请回复'测试成功'")
        
        logger.info(f"提取的参数: name={name}, type={type}, model={model}, base_url={base_url}, api_key={'已设置' if api_key else '未设置'}")
        
        if not all([name, type, model, base_url, api_key]):
            missing_fields = []
            if not name: missing_fields.append("name")
            if not type: missing_fields.append("type")
            if not model: missing_fields.append("models")
            if not base_url: missing_fields.append("base_url")
            if not api_key: missing_fields.append("api_key")
            
            logger.error(f"缺少必填字段: {missing_fields}")
            raise HTTPException(
                status_code=400,
                detail=error_response(code=400, message=f"缺少必填字段: {', '.join(missing_fields)}")
            )
        
        headers = {"Content-Type": "application/json"}
        params = {}
        
        if type == 'google':
            params['key'] = api_key
        else:
            headers['Authorization'] = f"Bearer {api_key}"
        
        if type == 'google':
            google_model = model
            if '/' in model:
                google_model = model.split('/')[-1]
            if google_model.startswith('models/'):
                google_model = google_model[7:]
            if ':' in google_model:
                google_model = google_model.split(':')[0]
                
            chat_url = f"{base_url.rstrip('/')}/models/{google_model}:generateContent"
            payload = {
                "contents": [{"parts": [{"text": test_message}]}],
                "generationConfig": {
                    "maxOutputTokens": 50,
                    "temperature": 0.1
                }
            }
            logger.info(f"Google AI 请求: URL={chat_url}, 原始模型={model}, 处理后模型={google_model}")
        elif type == 'claude':
            chat_url = f"{base_url.rstrip('/')}/messages"
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": test_message}],
                "max_tokens": 50,
                "temperature": 0.1
            }
            headers["anthropic-version"] = "2023-06-01"
            logger.info(f"Claude请求: URL={chat_url}, 模型={model}")
        elif type == 'qwen':
            chat_url = f"{base_url.rstrip('/')}/chat/completions"
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": test_message}],
                "max_tokens": 50,
                "temperature": 0.1
            }
            logger.info(f"通义千问请求: URL={chat_url}, 模型={model}")
        else:
            chat_url = f"{base_url.rstrip('/')}/chat/completions"
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": test_message}],
                "max_tokens": 50,
                "temperature": 0.1
            }
            logger.info(f"OpenAI兼容请求: URL={chat_url}, 模型={model}")
        
        import time
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    chat_url, 
                    headers=headers, 
                    params=params, 
                    json=payload, 
                    timeout=30
                )
                
            logger.info(f"收到响应，状态码: {response.status_code}")
            
            response_time = int((time.time() - start_time) * 1000)
            
            if 200 <= response.status_code < 300:
                response_data = response.json()
                
                if type == 'google':
                    model_response = response_data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                elif type == 'claude':
                    model_response = response_data.get("content", [{}])[0].get("text", "")
                else:
                    model_response = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                return success_response(
                    data={
                        "response": model_response,
                        "response_time": response_time,
                        "response_code": response.status_code
                    },
                    message="模型响应测试成功！"
                )
            else:
                error_code = "MODEL_RESPONSE_ERROR"
                error_detail = "模型响应测试失败"
                
                if response.status_code == 400:
                    error_code = "BAD_REQUEST"
                    error_detail = "请求参数错误，请检查模型名称或请求格式"
                elif response.status_code == 401:
                    error_code = "UNAUTHORIZED"
                    error_detail = "API密钥无效或已过期"
                elif response.status_code == 403:
                    error_code = "FORBIDDEN"
                    error_detail = "API密钥权限不足或已被禁用"
                elif response.status_code == 404:
                    error_code = "MODEL_NOT_FOUND"
                    error_detail = "指定的模型不存在或未在服务中启用"
                elif response.status_code == 429:
                    error_code = "RATE_LIMITED"
                    error_detail = "请求频率超出限制，请稍后重试"
                elif response.status_code >= 500:
                    error_code = "SERVER_ERROR"
                    error_detail = "LLM服务内部错误，请稍后重试"
                
                raise HTTPException(
                    status_code=400,
                    detail={
                        "code": 400,
                        "message": error_detail,
                        "data": {
                            "error_code": error_code,
                            "response_code": response.status_code
                        }
                    }
                )
        except httpx.RequestError as e:
            if "YOUR_VALID_OPENAI_API_KEY_HERE" in str(api_key) or "invalid" in str(api_key).lower():
                raise HTTPException(
                    status_code=400, 
                    detail={
                        "code": 400,
                        "message": "API密钥无效，请配置有效的OpenAI API密钥",
                        "data": {
                            "error_code": "INVALID_API_KEY_PLACEHOLDER",
                            "response_code": 401
                        }
                    }
                )
            else:
                raise HTTPException(
                    status_code=400, 
                    detail={
                        "code": 400,
                        "message": "请求失败，请检查网络连接或Base URL是否正确",
                        "data": {
                            "error_code": "CONNECTION_ERROR",
                            "response_code": 500
                        }
                    }
                )
            
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        logger.error(f"测试过程中发生错误: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=error_response(code=500, message="测试过程中发生错误")
        )


@router.post("/channels/{channel_id}/test")
async def test_channel(channel_id: int, db: Session = Depends(get_db)):
    """测试渠道连接"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"开始测试渠道连接，渠道ID: {channel_id}")
    
    db_channel = db.query(orm.Channel).filter(orm.Channel.id == channel_id).first()
    if db_channel is None:
        logger.error(f"渠道未找到，ID: {channel_id}")
        raise HTTPException(
            status_code=404,
            detail=error_response(code=404, message="渠道未找到")
        )

    api_key = security.decrypt_data(db_channel.encrypted_api_key)
    base_url = db_channel.base_url
    channel_type = db_channel.type
    
    logger.info(f"渠道配置: 类型={channel_type}, URL={base_url}")
    
    headers = {}
    params = {}
    
    if channel_type == 'google':
        params['key'] = api_key
        test_url = f"{base_url.rstrip('/')}/models"
        headers = {"Content-Type": "application/json"}
    elif channel_type == 'claude':
        headers['Authorization'] = f"Bearer {api_key}"
        headers["anthropic-version"] = "2023-06-01"
        test_url = f"{base_url.rstrip('/')}/messages"
    else:
        headers['Authorization'] = f"Bearer {api_key}"
        test_url = f"{base_url.rstrip('/')}/models"

    try:
        logger.info(f"发送请求到: {test_url}")
        async with httpx.AsyncClient() as client:
            response = await client.get(test_url, headers=headers, params=params, timeout=10)
        
        logger.info(f"收到响应，状态码: {response.status_code}")
        
        if 200 <= response.status_code < 300:
            return success_response(
                data={"response_code": response.status_code},
                message="配置连接测试通过"
            )
        else:
            error_code = "API_CONNECTION_ERROR"
            error_detail = "配置连接失败，请检查 Base URL 和 API Key"
            
            if response.status_code == 401:
                error_code = "UNAUTHORIZED"
                error_detail = "API密钥无效或已过期，请检查密钥是否正确"
            elif response.status_code == 403:
                error_code = "FORBIDDEN"
                error_detail = "API密钥权限不足或已被禁用"
            elif response.status_code == 404:
                error_code = "INVALID_ENDPOINT"
                error_detail = "API端点无效，请检查Base URL是否正确"
            elif response.status_code >= 500:
                error_code = "SERVER_ERROR"
                error_detail = "LLM服务暂时不可用，请稍后重试"
            
            raise HTTPException(
                status_code=400, 
                detail={
                    "code": 400,
                    "message": error_detail,
                    "data": {
                        "error_code": error_code,
                        "response_code": response.status_code
                    }
                }
            )
    except httpx.RequestError as e:
        logger.error(f"请求错误: {str(e)}")
        if "YOUR_VALID_OPENAI_API_KEY_HERE" in str(api_key) or "invalid" in str(api_key).lower():
            raise HTTPException(
                status_code=400, 
                detail={
                    "code": 400,
                    "message": "API密钥无效，请配置有效的OpenAI API密钥",
                    "data": {
                        "error_code": "INVALID_API_KEY_PLACEHOLDER",
                        "response_code": 401
                    }
                }
            )
        else:
            raise HTTPException(
                status_code=400, 
                detail={
                    "code": 400,
                    "message": "请求失败，请检查网络连接或Base URL是否正确",
                    "data": {
                        "error_code": "CONNECTION_ERROR",
                        "response_code": 500
                    }
                }
            )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"测试通道时发生未处理的异常: {str(e)}", exc_info=True)
        
        error_message = str(e)
        error_code = "UNKNOWN_ERROR"
        display_message = "未知错误"
        
        if "401" in error_message or "unauthorized" in error_message.lower():
            error_code = "UNAUTHORIZED"
            display_message = "API密钥无效或已过期"
        elif "403" in error_message or "forbidden" in error_message.lower():
            error_code = "FORBIDDEN"
            display_message = "API密钥权限不足"
        elif "404" in error_message or "not found" in error_message.lower():
            error_code = "INVALID_ENDPOINT"
            display_message = "API端点无效，请检查Base URL"
        elif "timeout" in error_message.lower():
            error_code = "TIMEOUT_ERROR"
            display_message = "请求超时，请检查网络连接"
        elif "connection" in error_message.lower() or "network" in error_message.lower():
            error_code = "CONNECTION_ERROR"
            display_message = "网络连接失败，请检查Base URL是否正确"
        
        raise HTTPException(
            status_code=400,
            detail={
                "code": 400,
                "message": display_message,
                "data": {
                    "error_code": error_code,
                    "response_code": 400
                }
            }
        )


# ============================================================
# 模型配置管理路由
# ============================================================

@router.get("/channels/{channel_id}/model-config")
def get_model_config(channel_id: int, db: Session = Depends(get_db)):
    """获取指定渠道的模型配置"""
    try:
        channel = crud.get_channel(db, channel_id=channel_id)
        if not channel:
            raise HTTPException(
                status_code=404,
                detail=error_response(code=404, message="渠道未找到")
            )
        
        # 获取模型名称
        model_name = channel.models.split(',')[0].strip() if channel.models else None
        
        # 获取模型能力配置
        capabilities = get_model_capabilities(model_name)
        
        # 获取参数范围配置
        param_limits = get_param_limits_for_model(model_name)
        
        # 尝试获取模型配置
        model_config = crud.get_model_config_by_channel(db, channel_id=channel_id)
        
        if model_config:
            config_data = {
                'id': model_config.id,
                'channel_id': model_config.channel_id,
                'model_name': model_config.model_name,
                'temperature': model_config.temperature,
                'top_p': model_config.top_p,
                'max_tokens': model_config.max_tokens,
                'max_tokens_limit': model_config.max_tokens_limit or capabilities.get('max_tokens_limit'),
                'frequency_penalty': model_config.frequency_penalty,
                'presence_penalty': model_config.presence_penalty,
                'system_prompt': model_config.system_prompt,
                'enable_web_search': model_config.enable_web_search,
                'enable_deep_thinking': model_config.enable_deep_thinking,
                'thinking_budget': model_config.thinking_budget,
                'include_thoughts': model_config.include_thoughts,
                'has_model_config': True,
                # 新增：参数范围配置
                'param_limits': param_limits,
                # 新增：模型能力配置
                'capabilities': capabilities,
            }
        else:
            config_data = {
                'channel_id': channel_id,
                'temperature': param_limits['temperature']['default'],
                'top_p': param_limits['top_p']['default'],
                'max_tokens': param_limits['max_tokens']['default'],
                'max_tokens_limit': capabilities.get('max_tokens_limit'),
                'frequency_penalty': param_limits['frequency_penalty']['default'],
                'presence_penalty': param_limits['presence_penalty']['default'],
                'system_prompt': '',
                'enable_web_search': False,
                'enable_deep_thinking': capabilities.get('thinking') == 'forced',
                'thinking_budget': capabilities.get('thinking_budget_default'),
                'include_thoughts': False,
                'has_model_config': False,
                # 新增：参数范围配置
                'param_limits': param_limits,
                # 新增：模型能力配置
                'capabilities': capabilities,
            }
        
        return success_response(
            data=config_data,
            message="获取模型配置成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取模型配置失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=error_response(code=500, message="获取模型配置失败")
        )


@router.post("/channels/{channel_id}/model-config")
def create_or_update_model_config(
    channel_id: int, 
    model_config: schemas.ModelConfigCreate, 
    db: Session = Depends(get_db)
):
    """创建或更新指定渠道的模型配置"""
    try:
        channel = crud.get_channel(db, channel_id=channel_id)
        if not channel:
            raise HTTPException(
                status_code=404,
                detail=error_response(code=404, message="渠道未找到")
            )
        
        config_dict = model_config.dict(exclude_unset=True)
        config_dict['channel_id'] = channel_id
        
        if not config_dict.get('model_name'):
            if channel.models:
                config_dict['model_name'] = channel.models.split(',')[0].strip()
            else:
                config_dict['model_name'] = "default"
        
        # 获取模型能力配置
        model_name = config_dict.get('model_name')
        capabilities = get_model_capabilities(model_name)
        param_limits = get_param_limits_for_model(model_name)
        
        # 如果没有设置 max_tokens_limit，使用模型能力配置中的值
        if not config_dict.get('max_tokens_limit'):
            config_dict['max_tokens_limit'] = capabilities.get('max_tokens_limit')
        
        existing_config = crud.get_model_config_by_channel(db, channel_id=channel_id)
        
        if existing_config:
            for key, value in config_dict.items():
                if key != 'channel_id':
                    setattr(existing_config, key, value)
            
            db.commit()
            db.refresh(existing_config)
            
            config_data = {
                'id': existing_config.id,
                'channel_id': existing_config.channel_id,
                'model_name': existing_config.model_name,
                'temperature': existing_config.temperature,
                'top_p': existing_config.top_p,
                'max_tokens': existing_config.max_tokens,
                'max_tokens_limit': existing_config.max_tokens_limit,
                'frequency_penalty': existing_config.frequency_penalty,
                'presence_penalty': existing_config.presence_penalty,
                'system_prompt': existing_config.system_prompt,
                'enable_web_search': existing_config.enable_web_search,
                'enable_deep_thinking': existing_config.enable_deep_thinking,
                'thinking_budget': existing_config.thinking_budget,
                'include_thoughts': existing_config.include_thoughts,
                'has_model_config': True,
                'param_limits': param_limits,
                'capabilities': capabilities,
            }
            message = "模型配置更新成功"
        else:
            db_config = orm.ModelConfig(**config_dict)
            db.add(db_config)
            db.commit()
            db.refresh(db_config)
            
            config_data = {
                'id': db_config.id,
                'channel_id': db_config.channel_id,
                'model_name': db_config.model_name,
                'temperature': db_config.temperature,
                'top_p': db_config.top_p,
                'max_tokens': db_config.max_tokens,
                'max_tokens_limit': db_config.max_tokens_limit,
                'frequency_penalty': db_config.frequency_penalty,
                'presence_penalty': db_config.presence_penalty,
                'system_prompt': db_config.system_prompt,
                'enable_web_search': db_config.enable_web_search,
                'enable_deep_thinking': db_config.enable_deep_thinking,
                'thinking_budget': db_config.thinking_budget,
                'include_thoughts': db_config.include_thoughts,
                'has_model_config': True,
                'param_limits': param_limits,
                'capabilities': capabilities,
            }
            message = "模型配置创建成功"
        
        return success_response(
            data=config_data,
            message=message
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"保存模型配置失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=error_response(code=500, message="保存模型配置失败")
        )


@router.delete("/channels/{channel_id}/model-config")
def delete_model_config(channel_id: int, db: Session = Depends(get_db)):
    """删除指定渠道的模型配置"""
    try:
        channel = crud.get_channel(db, channel_id=channel_id)
        if not channel:
            raise HTTPException(
                status_code=404,
                detail=error_response(code=404, message="渠道未找到")
            )
        
        deleted_config = crud.delete_model_config(db, channel_id=channel_id)
        
        if deleted_config:
            return success_response(
                data={"deleted": True},
                message="模型配置删除成功"
            )
        else:
            return success_response(
                data={"deleted": False},
                message="模型配置不存在，无需删除"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除模型配置失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=error_response(code=500, message="删除模型配置失败")
        )


# ============================================================
# 模型能力查询路由
# ============================================================

@router.get("/model-capabilities/{model_name}")
def get_model_capabilities_api(model_name: str):
    """获取指定模型的能力配置"""
    try:
        capabilities = get_model_capabilities(model_name)
        param_limits = get_param_limits_for_model(model_name)
        
        return success_response(
            data={
                'model_name': model_name,
                'capabilities': capabilities,
                'param_limits': param_limits,
            },
            message="获取模型能力配置成功"
        )
    except Exception as e:
        logger.error(f"获取模型能力配置失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=error_response(code=500, message="获取模型能力配置失败")
        )


@router.get("/model-capabilities")
def list_model_capabilities():
    """获取所有已知模型的能力配置"""
    try:
        all_capabilities = {}
        for model_name, caps in MODEL_CAPABILITIES.items():
            all_capabilities[model_name] = {
                'capabilities': caps,
                'param_limits': get_param_limits_for_model(model_name),
            }
        
        return success_response(
            data={
                'models': all_capabilities,
                'default': {
                    'capabilities': DEFAULT_CAPABILITY,
                    'param_limits': DEFAULT_PARAM_LIMITS,
                }
            },
            message="获取模型能力配置列表成功"
        )
    except Exception as e:
        logger.error(f"获取模型能力配置列表失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=error_response(code=500, message="获取模型能力配置列表失败")
        )


@router.get("/param-limits")
def get_default_param_limits():
    """获取默认参数范围配置"""
    try:
        return success_response(
            data=DEFAULT_PARAM_LIMITS,
            message="获取默认参数范围配置成功"
        )
    except Exception as e:
        logger.error(f"获取默认参数范围配置失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=error_response(code=500, message="获取默认参数范围配置失败")
        )


# ============================================================
# 渠道测试路由（通过代理）
# ============================================================

@router.post("/channels/{channel_id}/test-via-proxy")
async def test_channel_via_proxy(channel_id: int, db: Session = Depends(get_db)):
    """
    通过LLM Manager代理测试渠道连接
    """
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"开始通过代理测试渠道连接，渠道ID: {channel_id}")
    
    db_channel = db.query(orm.Channel).filter(orm.Channel.id == channel_id).first()
    if db_channel is None:
        logger.error(f"渠道未找到，ID: {channel_id}")
        raise HTTPException(
            status_code=404,
            detail=error_response(code=404, message="渠道未找到")
        )
    
    original_status = db_channel.status
    if not original_status:
        db_channel.status = True
        db.commit()
        logger.info(f"临时激活渠道 {channel_id} 进行测试")
    
    try:
        proxy_url = f"{settings.api_base_url}/api/models"
        
        headers = {
            "Content-Type": "application/json"
        }
        
        logger.info(f"通过代理测试连接: {proxy_url}")
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(proxy_url, headers=headers)
        
        logger.info(f"代理测试响应状态码: {response.status_code}")
        
        if 200 <= response.status_code < 300:
            try:
                response_data = response.json()
                
                if "data" in response_data and isinstance(response_data["data"], list):
                    models = [model.get("id", "") for model in response_data["data"]]
                    channel_models = [m.strip() for m in db_channel.models.split(",")]
                    
                    found_model = any(model in models for model in channel_models if model)
                    
                    if found_model:
                        logger.info(f"代理测试成功: 找到渠道模型")
                        return success_response(
                            data={
                                "response_code": response.status_code,
                                "test_method": "proxy",
                                "models_found": True
                            },
                            message="渠道通过代理测试成功"
                        )
                    else:
                        logger.warning(f"代理测试部分成功: 但未找到渠道模型")
                        return success_response(
                            data={
                                "response_code": response.status_code,
                                "test_method": "proxy",
                                "models_found": False
                            },
                            message="代理连接成功，但未找到渠道模型"
                        )
                else:
                    logger.error(f"代理测试失败: 响应格式不正确")
                    raise HTTPException(
                        status_code=500,
                        detail={
                            "code": 500,
                            "message": "代理测试失败: 响应格式不正确",
                            "data": {
                                "error_code": "INVALID_RESPONSE_FORMAT",
                                "response_code": response.status_code
                            }
                        }
                    )
            except json.JSONDecodeError:
                logger.error(f"代理测试失败: 响应不是有效的JSON")
                raise HTTPException(
                    status_code=500,
                    detail={
                        "code": 500,
                        "message": "代理测试失败: 响应不是有效的JSON",
                        "data": {
                            "error_code": "INVALID_JSON",
                            "response_code": response.status_code
                        }
                    }
                )
        else:
            logger.error(f"代理测试失败: HTTP {response.status_code}")
            error_code = "PROXY_CONNECTION_ERROR"
            error_detail = "代理连接失败，请检查LLM Manager服务"
            
            if response.status_code == 401:
                error_code = "PROXY_UNAUTHORIZED"
                error_detail = "代理服务认证失败"
            elif response.status_code == 404:
                error_code = "PROXY_ENDPOINT_NOT_FOUND"
                error_detail = "代理端点不存在，请检查LLM Manager是否正确配置"
            elif response.status_code >= 500:
                error_code = "PROXY_SERVER_ERROR"
                error_detail = "代理服务内部错误"
            
            raise HTTPException(
                status_code=400,
                detail={
                    "code": 400,
                    "message": error_detail,
                    "data": {
                        "error_code": error_code,
                        "response_code": response.status_code
                    }
                }
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"代理测试异常: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "code": 500,
                "message": "代理测试异常",
                "data": {
                    "error_code": "PROXY_TEST_EXCEPTION",
                    "response_code": 500
                }
            }
        )
    finally:
        if not original_status:
            db_channel.status = False
            db.commit()
            logger.info(f"恢复渠道 {channel_id} 原始状态")
