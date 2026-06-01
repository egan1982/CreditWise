"""
Chat Completions API for DeepAnalyze API Server
Handles extended chat completion with file attachment support and code execution

Features:
- System prompt support (from LLM Manager configuration)
- Task-aware system prompt injection (via TaskPromptProvider)
- Code execution workflow (<Code>...</Code> tags)
- Workspace file tracking and artifact collection
- Report generation from conversation history
- Lazy LLM client initialization with graceful degradation
- Toggle between simple chat and full DeepAnalyze agent mode
- **NEW** LLM Manager channel integration with load balancing support
"""

import json
import logging
import os
import time
import uuid
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

from fastapi import HTTPException
from fastapi import APIRouter, Body
from fastapi.responses import StreamingResponse

# 模型参数从LLM Manager渠道配置获取，不再使用config中的硬编码值
from models import ChatCompletionRequest, ChatCompletionResponse, ChatCompletionChoice
from storage import storage
from utils import (
    get_thread_workspace, prepare_vllm_messages, execute_code_safe,
    execute_code_safe_async, WorkspaceTracker, render_file_block,
    generate_report_from_messages, extract_code_from_segment
)
from llm_client_manager import LLMClientManager

logger = logging.getLogger(__name__)

# Task Manager for inference task recording
try:
    from deepanalyze.core.task_manager import TaskHistoryService
    TASK_MANAGER_AVAILABLE = True
except ImportError as e:
    TASK_MANAGER_AVAILABLE = False
    TaskHistoryService = None
    logger.warning(f"Task manager not available: {e}")

# Channel client factory for LLM Manager integration
try:
    try:
        from .channel_client import get_channel_factory, ChannelInfo
    except ImportError:
        from API.channel_client import get_channel_factory, ChannelInfo
    CHANNEL_FACTORY_AVAILABLE = True
except ImportError as e:
    CHANNEL_FACTORY_AVAILABLE = False
    get_channel_factory = None
    ChannelInfo = None
    logger.warning(f"ChannelClientFactory not available: {e}")

# Task prompt provider for SOP task awareness
try:
    from deepanalyze.analysis.task_SOP.task_prompt_provider import get_prompt_provider
    TASK_PROMPT_AVAILABLE = True
except ImportError:
    TASK_PROMPT_AVAILABLE = False
    get_prompt_provider = None

# API Logger for call metrics and cost tracking
try:
    try:
        from .api_logger import get_chat_api_logger, APICallMetrics
    except ImportError:
        from API.api_logger import get_chat_api_logger, APICallMetrics
    API_LOGGER_AVAILABLE = True
except ImportError as e:
    API_LOGGER_AVAILABLE = False
    get_chat_api_logger = None
    APICallMetrics = None
    logger.warning(f"API Logger not available: {e}")

# Error handler for unified error responses
try:
    try:
        from .error_handler import (
            ChatAPIError, ChannelUnavailableError, ProviderError, 
            RateLimitError, classify_provider_error, create_error_response
        )
    except ImportError:
        from API.error_handler import (
            ChatAPIError, ChannelUnavailableError, ProviderError,
            RateLimitError, classify_provider_error, create_error_response
        )
    ERROR_HANDLER_AVAILABLE = True
except ImportError as e:
    ERROR_HANDLER_AVAILABLE = False
    logger.warning(f"Error handler not available: {e}")


# Create router for chat endpoints
router = APIRouter(prefix="/v1/chat", tags=["chat"])

# =============================================================================
# Inference Task Recording Helper Functions
# =============================================================================

def _create_inference_task_record(
    session_id: str,
    message_count: int,
    file_count: int
) -> Optional[str]:
    """创建AI对话（inference）任务记录"""
    if not TASK_MANAGER_AVAILABLE:
        return None
    
    try:
        import uuid
        record_id = f"rec-{uuid.uuid4().hex[:24]}"
        
        # 构建输入摘要
        inputs_summary = {
            "message_count": message_count,
            "file_count": file_count
        }
        
        TaskHistoryService.create_record(
            task_type="inference",
            task_category="inference",
            execution_id=None,  # inference任务没有execution_id
            session_id=session_id,
            interaction_mode="auto",
            params={},
            inputs_summary=json.dumps(inputs_summary)
        )
        
        logger.info(f"Created inference task record: {record_id} for session: {session_id}")
        return record_id
    except Exception as e:
        logger.error(f"Failed to create inference task record: {e}")
        return None

def _update_inference_task_status(
    session_id: str,
    status: str,
    duration_seconds: Optional[float] = None
) -> None:
    """更新AI对话任务状态"""
    if not TASK_MANAGER_AVAILABLE:
        return
    
    try:
        # 获取该session_id的最新inference记录
        from deepanalyze.core.task_manager.history_service import TaskHistoryService
        records = TaskHistoryService.list_records(
            task_category="inference",
            session_id=session_id,
            status="pending",
            limit=1
        )
        
        if not records:
            logger.warning(f"No pending inference record found for session: {session_id}")
            return
        
        record_id = records[0]["record_id"]
        
        # 更新记录
        TaskHistoryService.update_status(
            record_id=record_id,
            status=status,
            duration_seconds=duration_seconds
        )
        
        logger.info(f"Updated inference task record: {record_id} to status: {status}")
    except Exception as e:
        logger.error(f"Failed to update inference task record: {e}")


def _is_channel_model(model: str) -> bool:
    """
    检查model是否是LLM Manager渠道标识
    
    支持的格式：
    - config_123: 使用配置ID 123
    - channel_456: 使用渠道ID 456
    """
    return model.startswith("config_") or model.startswith("channel_")


async def _get_llm_client_and_model(model: str) -> Tuple[Any, str, Optional[Any]]:
    """
    根据model标识获取LLM客户端和实际模型名
    
    Args:
        model: 模型标识
        
    Returns:
        (llm_client, actual_model, channel_info)
        - llm_client: LLM客户端实例
        - actual_model: 实际使用的模型名
        - channel_info: 渠道信息（如果使用LLM Manager渠道）
    """
    # 检查是否使用LLM Manager渠道
    if _is_channel_model(model) and CHANNEL_FACTORY_AVAILABLE:
        try:
            factory = get_channel_factory()
            channel_info = await factory.get_channel_for_model(model)
            
            if channel_info:
                # 使用渠道工厂创建客户端
                client = factory.create_openai_client(channel_info)
                logger.info(f"使用LLM Manager渠道: {channel_info.channel_name} ({channel_info.provider})")
                return client, channel_info.model, channel_info
            else:
                logger.warning(f"未找到model {model} 对应的渠道，回退到默认客户端")
        except Exception as e:
            logger.error(f"获取LLM Manager渠道失败: {e}，回退到默认客户端")
    
    # 回退到原有的LLMClientManager
    llm_client = LLMClientManager.get_client(verbose=False)
    return llm_client, model, None


def _determine_chat_mode(
    task_type: Optional[str],
    messages: List[Dict[str, Any]],
    enable_code_execution: bool,
) -> Tuple[str, Optional[str]]:
    """
    显式判定聊天模式
    
    根据前端传入的 task_type 或消息推断，返回 mode 和有效的 task_type。
    
    规则：
    1. 非代码执行模式（简单模式）→ chat
    2. 前端传入了 task_type → extraction
    3. 从消息中推断出 task_type → extraction
    4. 其他情况 → chat
    
    Returns:
        (mode, effective_task_type)
    """
    if not enable_code_execution:
        return "chat", None
    
    if task_type:
        return "extraction", task_type
    
    inferred = _infer_task_type_from_messages(messages)
    if inferred:
        return "extraction", inferred
    
    return "chat", None


def _build_enhanced_system_prompt(
    user_system_prompt: Optional[str] = None,
    task_type: Optional[str] = None,
    workspace_files: Optional[List[str]] = None,
    include_task_list: bool = True,
    mode: str = "chat",
) -> str:
    """
    构建增强的系统提示词，集成任务说明
    
    Args:
        user_system_prompt: 用户配置的系统提示词
        task_type: 指定任务类型（可选，用于注入特定任务引导）
        workspace_files: 工作区文件列表（可选）
        include_task_list: 是否包含所有可用任务列表
        mode: "chat"（对话模式）或 "extraction"（参数提取模式）
        
    Returns:
        增强后的系统提示词
    """
    if not TASK_PROMPT_AVAILABLE:
        # TaskPromptProvider 不可用，返回原始提示词
        return user_system_prompt or ""
    
    try:
        provider = get_prompt_provider()
        return provider.build_system_prompt(
            base_prompt=user_system_prompt or "",
            task_type=task_type,
            include_all_tasks=include_task_list,
            workspace_files=workspace_files,
            mode=mode,
        )
    except Exception as e:
        logger.warning(f"Failed to build enhanced system prompt: {e}")
        return user_system_prompt or ""


def _infer_task_type_from_messages(messages: List[Dict[str, Any]]) -> Optional[str]:
    """从用户消息中推断任务类型
    
    当前端未传递 task_type 时，尝试从用户消息内容中识别任务意图
    
    Returns:
        推断出的任务类型，如 'scorecard_dev', 'rule_mining' 等，或 None
    """
    if not messages:
        return None
    
    # 获取最后一条用户消息
    user_message = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, str):
                user_message = content
            elif isinstance(content, list):
                # 处理多模态消息格式
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        user_message = item.get("text", "")
                        break
            break
    
    if not user_message:
        return None
    
    user_message_lower = user_message.lower()
    
    # 任务类型关键词映射
    task_keywords = {
        "scorecard_dev": [
            "评分卡", "scorecard", "信用评分", "风控模型",
            "woe", "iv", "分箱", "逻辑回归", "lr模型",
        ],
        "rule_mining": [
            "规则挖掘", "rule mining", "规则提取", "决策规则",
            "规则发现", "关联规则", "规则集",
        ],
    }
    
    # 检查每个任务类型的关键词
    for task_type, keywords in task_keywords.items():
        for keyword in keywords:
            if keyword in user_message_lower:
                print(f"[Chat API] 从用户消息中推断出任务类型: {task_type} (关键词: {keyword})")
                return task_type
    
    return None


async def _log_api_call(
    request_id: str,
    channel_info: Optional[Any],
    model: str,
    start_time: float,
    status: str = "success",
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    error_message: Optional[str] = None,
):
    """
    记录API调用日志
    
    异步非阻塞，不影响主流程
    """
    if not API_LOGGER_AVAILABLE:
        return
    
    try:
        import asyncio
        
        response_time = time.time() - start_time
        
        metrics = APICallMetrics(
            request_id=request_id,
            channel_id=channel_info.channel_id if channel_info else None,
            channel_name=channel_info.channel_name if channel_info else None,
            model=model,
            provider=channel_info.provider if channel_info and hasattr(channel_info, 'provider') else "openai",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            response_time=response_time,
            status=status,
            error_message=error_message,
        )
        
        # 异步记录日志，不阻塞主流程
        api_logger = get_chat_api_logger()
        asyncio.create_task(api_logger.log_api_call(metrics))
        
    except Exception as e:
        logger.warning(f"记录API日志失败: {e}")


def _update_channel_metrics(channel_info: Any, success: bool, response_time: float):
    """
    更新渠道指标
    
    Args:
        channel_info: 渠道信息
        success: 是否成功
        response_time: 响应时间（秒）
    """
    if not CHANNEL_FACTORY_AVAILABLE or channel_info is None:
        return
    
    try:
        factory = get_channel_factory()
        factory.update_channel_metrics(
            channel_id=channel_info.channel_id,
            success=success,
            response_time=response_time
        )
    except Exception as e:
        logger.warning(f"更新渠道指标失败: {e}")


@router.post("/completions")
async def chat_completions(
    model: str = Body(...),
    messages: List[Dict[str, Any]] = Body(...),
    file_ids: Optional[List[str]] = Body(None),
    temperature: Optional[float] = Body(None),  # 已废弃，LLM Manager渠道使用渠道配置
    stream: Optional[bool] = Body(False),
    system_prompt: Optional[str] = Body(None),
    enable_code_execution: Optional[bool] = Body(True),
    task_type: Optional[str] = Body(None),
    include_task_list: Optional[bool] = Body(True),
    # Additional parameters from frontend
    session_id: Optional[str] = Body(None),
    max_tokens: Optional[int] = Body(None),  # 请求参数优先，用于AI分析评估等场景覆盖渠道配置
    top_p: Optional[float] = Body(None),
    frequency_penalty: Optional[float] = Body(None),  # 频率惩罚，抑制重复词语
    presence_penalty: Optional[float] = Body(None),   # 存在惩罚，鼓励话题多样性
):
    """
    Extended chat completion API with file attachment support and code execution.
    Creates a temporary conversation with associated files.

    Parameters:
    - model: Model name or channel identifier (supports "config_123" or "channel_456" format for LLM Manager channels)
    - messages: List of message objects with role and content
    - file_ids: Optional list of file IDs to attach to the conversation
    - temperature: [已废弃] LLM Manager渠道使用渠道配置，此参数仅用于旧版兼容
    - stream: Whether to stream the response (default False)
    - system_prompt: Optional system prompt (LLM Manager渠道优先使用渠道配置)
    - enable_code_execution: Enable DeepAnalyze code execution workflow (default True)
    - task_type: Optional task type ID for task-specific guidance injection
    - include_task_list: Include all available SOP tasks in system prompt (default True)

    Returns:
    - Standard OpenAI chat completion response
    - Additional field 'generated_files' with list of generated file URLs (when code execution enabled)
    """
    # Get LLM client - supports both LLM Manager channels and legacy LLMClientManager
    llm_client, actual_model, channel_info = await _get_llm_client_and_model(model)
    
    if not llm_client:
        raise HTTPException(
            status_code=503,
            detail="LLM API is not configured. Please configure API keys in LLM Manager: /llm-manager"
        )
    
    # 根据渠道配置决定是否使用流式输出
    # 渠道配置优先级高于前端请求参数
    effective_stream = stream
    if channel_info is not None:
        channel_stream_output = getattr(channel_info, 'stream_output', True)
        if channel_stream_output is False:
            effective_stream = False
            logger.info(f"渠道 {channel_info.channel_name} 已禁用流式输出，使用非流式模式")
    
    # 确定基础系统提示词来源
    # 显式判定聊天模式（替代原有的关键词嗅探逻辑）
    # 注意：mode 判定必须在 base_system_prompt 选择之前，因为 chat mode 不使用渠道预设 prompt
    mode, effective_task_type = _determine_chat_mode(task_type, messages, enable_code_execution)
    if effective_task_type and effective_task_type != task_type:
        logger.info(f"自动推断任务类型: {effective_task_type}")
    
    # 根据 mode 选择 base_system_prompt
    # - extraction 模式：使用渠道预设 prompt（含参数提取角色和 JSON 格式要求）
    # - chat 模式：不使用渠道预设 prompt（渠道 prompt 是为 extraction 设计的，含 JSON 指令会污染对话）
    #   chat mode 下 _build_chat_prompt 会使用 DEFAULT_BASE_PROMPT 作为角色定义
    # - 简单模式（enable_code_execution=False）：只使用请求参数的 system_prompt
    base_system_prompt = None
    
    if enable_code_execution and channel_info is not None and mode == "extraction":
        # 仅 extraction 模式使用渠道配置的预设提示词
        channel_system_prompt = getattr(channel_info, 'system_prompt', None)
        if channel_system_prompt and channel_system_prompt.strip():
            base_system_prompt = channel_system_prompt
            logger.info(f"[extraction] 使用渠道 {channel_info.channel_name} 的预设系统提示词 (长度: {len(channel_system_prompt)})")
    
    if not base_system_prompt:
        if mode == "chat":
            # chat 模式：传空字符串，让 _build_chat_prompt 使用 DEFAULT_BASE_PROMPT
            base_system_prompt = ""
            logger.info(f"[chat] 使用默认对话角色（不使用渠道预设 prompt）")
        else:
            # fallback：使用请求参数中的 system_prompt
            base_system_prompt = system_prompt
    
    # Build enhanced system prompt with task awareness
    # 简单模式下，include_task_list强制为False，避免注入任务相关提示词
    effective_include_task_list = include_task_list if enable_code_execution else False
    enhanced_system_prompt = _build_enhanced_system_prompt(
        user_system_prompt=base_system_prompt,
        task_type=effective_task_type,
        include_task_list=effective_include_task_list,
        mode=mode,
    )
    
    # Simple mode: no code execution, just forward to LLM
    # 注意：简单模式跳过参数推断检测，直接转发给LLM
    if not enable_code_execution:
        return await _simple_chat_completion(
            llm_client=llm_client,
            model=actual_model,
            messages=messages,
            temperature=temperature,
            stream=effective_stream,
            system_prompt=enhanced_system_prompt,
            channel_info=channel_info,
            max_tokens=max_tokens,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
        )
    
    # Extraction 模式：LLM 只需返回纯 JSON，不需要 code execution 的 <Code>/<Answer> 标签
    # 如果走 code execution 路径，prepare_vllm_messages 会注入 <Code>/<Answer> 标签 prompt，
    # 与 extraction prompt 的"只返回 JSON"指令冲突，导致 LLM 返回 <Code>```json{...}```</Code>，
    # 前端 renderMessageWithSections 优先匹配 <Code> 标签，跳过 isTaskParamJson 检查，
    # TaskConfirmCard 无法渲染（显示为 raw JSON 代码块）。
    if mode == "extraction":
        logger.info(f"[extraction] 使用 simple_chat_completion（避免 code execution prompt 冲突）")
        return await _simple_chat_completion(
            llm_client=llm_client,
            model=actual_model,
            messages=messages,
            temperature=temperature,
            stream=effective_stream,
            system_prompt=enhanced_system_prompt,
            channel_info=channel_info,
            max_tokens=max_tokens,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
        )
    
    # 检查是否为非OpenAI兼容厂商，代码执行模式不支持Claude/Google
    if channel_info is not None:
        provider = channel_info.provider.lower() if hasattr(channel_info, 'provider') else 'openai'
        if provider in ['claude', 'google']:
            logger.warning(f"代码执行模式不支持 {provider} 厂商，回退到simple模式")
            return await _simple_chat_completion(
                llm_client=llm_client,
                model=actual_model,
                messages=messages,
                temperature=temperature,
                stream=effective_stream,
                system_prompt=enhanced_system_prompt,
                channel_info=channel_info,
                max_tokens=max_tokens,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty,
            )
    
    # Full DeepAnalyze mode with code execution
    # Create temporary thread for workspace management
    temp_thread = storage.create_thread(metadata={"temporary": True})
    workspace_dir = get_thread_workspace(temp_thread.id)
    generated_dir = os.path.join(workspace_dir, "generated")
    os.makedirs(generated_dir, exist_ok=True)

    # Collect all file IDs from both parameter and messages
    all_file_ids = set()

    # Add file_ids from parameter (backward compatibility)
    if file_ids:
        all_file_ids.update(file_ids)

    # Extract file_ids from messages (new OpenAI compatibility)
    for message in messages:
        if isinstance(message, dict) and "file_ids" in message:
            message_file_ids = message.get("file_ids", [])
            if isinstance(message_file_ids, list):
                all_file_ids.update(message_file_ids)

    # Copy files to workspace
    for fid in all_file_ids:
        file_obj = storage.get_file(fid)
        if not file_obj:
            raise HTTPException(status_code=400, detail=f"File {fid} not found")
        src_path = storage.files.get(fid, {}).get("filepath")
        if src_path and os.path.exists(src_path):
            from utils import uniquify_path
            dst_path = uniquify_path(Path(workspace_dir) / file_obj.filename)
            shutil.copy2(src_path, dst_path)

    # Phase 14: 移除请求开始时的任务记录创建
    # 任务记录将在实际执行代码后才创建，避免普通AI对话被错误地记录为任务
    # 参见 _streaming_with_execution 和 _non_streaming_with_execution 中的 code_executed 标记

    # Build messages with DeepAnalyze prompt template (using enhanced system prompt)
    vllm_messages: List[Dict[str, Any]] = prepare_vllm_messages(
        messages, workspace_dir, system_prompt=enhanced_system_prompt
    )

    # Track generated files
    generated_files: List[Dict[str, str]] = []

    # 从渠道配置获取模型参数（LLM Manager是唯一配置来源）
    if channel_info is not None:
        # LLM Manager渠道：完全使用渠道配置，但允许请求参数覆盖某些字段
        effective_temperature = getattr(channel_info, 'temperature', None)
        
        # max_tokens：请求参数优先，否则使用渠道配置
        # 这允许AI分析评估等场景覆盖渠道默认值
        channel_max_tokens = getattr(channel_info, 'max_tokens', None)
        effective_max_tokens = max_tokens if max_tokens is not None else channel_max_tokens
        
        # 确保不超过模型的max_tokens_limit
        max_limit = getattr(channel_info, 'max_tokens_limit', None)
        if max_limit and effective_max_tokens and effective_max_tokens > max_limit:
            logger.warning(f"请求的max_tokens {effective_max_tokens} 超过模型限制 {max_limit}，已调整")
            effective_max_tokens = max_limit
        
        # 如果渠道配置缺失，记录警告
        if effective_max_tokens is None:
            logger.warning(f"渠道 {channel_info.channel_name} 未配置max_tokens，请在LLM Manager中配置")
        if effective_temperature is None:
            logger.warning(f"渠道 {channel_info.channel_name} 未配置temperature，使用默认值0.7")
            effective_temperature = 0.7
    else:
        # 非LLM Manager渠道（旧版兼容）
        effective_max_tokens = max_tokens
        effective_temperature = temperature if temperature is not None else 0.7

    # Stream response with code execution
    if effective_stream:
        return StreamingResponse(
            _generate_stream_with_execution_async(
                llm_client=llm_client,
                model=actual_model,
                vllm_messages=vllm_messages,
                temperature=effective_temperature,
                workspace_dir=workspace_dir,
                generated_dir=generated_dir,
                temp_thread=temp_thread,
                original_messages=messages,
                generated_files=generated_files,
                channel_info=channel_info,
                max_tokens=effective_max_tokens,
                session_id=temp_thread.id if enable_code_execution else None,  # 传递session_id用于任务记录
            ),
            media_type="text/event-stream"
        )
    else:
        # Non-streaming response with code execution
        return await _non_streaming_with_execution(
            llm_client=llm_client,
            model=actual_model,
            vllm_messages=vllm_messages,
            temperature=effective_temperature,
            workspace_dir=workspace_dir,
            generated_dir=generated_dir,
            temp_thread=temp_thread,
            original_messages=messages,
            file_ids=file_ids,
            generated_files=generated_files,
            channel_info=channel_info,
            max_tokens=effective_max_tokens,
            session_id=temp_thread.id if enable_code_execution else None,  # 传递session_id用于任务记录
        )



async def _simple_chat_completion(
    llm_client,
    model: str,
    messages: List[Dict[str, Any]],
    temperature: float,
    stream: bool,
    system_prompt: Optional[str],
    channel_info: Optional[Any] = None,
    max_tokens: Optional[int] = None,
    frequency_penalty: Optional[float] = None,
    presence_penalty: Optional[float] = None,
):
    """Simple chat completion without code execution
    
    Args:
        llm_client: LLM客户端实例
        model: 模型名称
        messages: 消息列表
        temperature: 温度参数（如未指定，使用渠道配置）
        stream: 是否流式
        system_prompt: 系统提示词（如未指定，使用渠道配置）
        channel_info: 渠道信息（LLM Manager渠道，包含所有模型参数配置）
        max_tokens: 最大token数（已废弃，使用渠道配置）
        frequency_penalty: 频率惩罚（请求参数优先，用于抑制重复）
        presence_penalty: 存在惩罚（请求参数优先，用于话题多样性）
    
    注意：frequency_penalty和presence_penalty优先使用请求参数（用于AI分析评估等场景），
    其他参数从LLM Manager渠道配置获取
    """
    from utils import prepare_vllm_messages
    import asyncio
    
    # 生成请求ID用于日志追踪
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    # 从渠道配置获取模型参数（LLM Manager是唯一配置来源）
    if channel_info is not None:
        # LLM Manager渠道：完全使用渠道配置，但允许请求参数覆盖某些字段
        effective_temperature = getattr(channel_info, 'temperature', None)
        # system_prompt已在chat_completions入口处理（渠道配置 + TaskPromptProvider组合）
        # 这里直接使用传入的system_prompt参数
        effective_system_prompt = system_prompt
        
        # max_tokens：请求参数优先，否则使用渠道配置
        # 这允许AI分析评估等场景覆盖渠道默认值
        channel_max_tokens = getattr(channel_info, 'max_tokens', None)
        effective_max_tokens = max_tokens if max_tokens is not None else channel_max_tokens
        
        # frequency_penalty和presence_penalty：请求参数优先，否则使用渠道配置
        # 这允许AI分析评估等场景覆盖渠道默认值
        effective_frequency_penalty = frequency_penalty if frequency_penalty is not None else getattr(channel_info, 'frequency_penalty', None)
        effective_presence_penalty = presence_penalty if presence_penalty is not None else getattr(channel_info, 'presence_penalty', None)
        
        # 确保不超过模型的max_tokens_limit
        max_limit = getattr(channel_info, 'max_tokens_limit', None)
        if max_limit and effective_max_tokens and effective_max_tokens > max_limit:
            logger.warning(f"请求的max_tokens {effective_max_tokens} 超过模型限制 {max_limit}，已调整")
            effective_max_tokens = max_limit
        
        # 如果渠道配置缺失，记录警告
        if effective_max_tokens is None:
            logger.warning(f"渠道 {channel_info.channel_name} 未配置max_tokens，请在LLM Manager中配置")
        if effective_temperature is None:
            logger.warning(f"渠道 {channel_info.channel_name} 未配置temperature，使用默认值0.7")
            effective_temperature = 0.7
    else:
        # 非LLM Manager渠道（旧版兼容），使用请求参数
        effective_max_tokens = max_tokens
        effective_frequency_penalty = frequency_penalty
        effective_presence_penalty = presence_penalty
        effective_temperature = temperature if temperature is not None else 0.7
        effective_system_prompt = system_prompt
    
    # Prepare messages with system prompt (empty workspace_dir for simple mode)
    prepared_messages = prepare_vllm_messages(messages, workspace_dir="", system_prompt=effective_system_prompt)
    
    # 如果使用LLM Manager渠道，根据provider类型选择调用方式
    if channel_info is not None:
        provider = channel_info.provider.lower() if hasattr(channel_info, 'provider') else 'openai'
        
        # 对于非OpenAI兼容的厂商（Claude/Google），使用ChannelClientFactory的专用方法
        if provider in ['claude', 'google']:
            try:
                factory = get_channel_factory()
                return await _handle_non_openai_provider(
                    factory=factory,
                    channel_info=channel_info,
                    messages=prepared_messages,
                    temperature=effective_temperature,
                    max_tokens=effective_max_tokens,
                    stream=stream,
                    model=model,
                )
            except Exception as e:
                logger.error(f"非OpenAI厂商调用失败: {e}")
                # 记录错误日志
                await _log_api_call(
                    request_id=request_id,
                    channel_info=channel_info,
                    model=model,
                    start_time=start_time,
                    status="error",
                    error_message=str(e)
                )
                # 使用错误处理器
                if ERROR_HANDLER_AVAILABLE:
                    classified_error = classify_provider_error(e, provider)
                    return create_error_response(classified_error)
                raise HTTPException(status_code=500, detail="LLM调用失败")
    
    if stream:
        async def generate_stream_async():
            """异步流式生成器"""
            # 构建请求参数
            request_params = {
                "model": model,
                "messages": prepared_messages,
                "temperature": effective_temperature,
                "stream": True,
                "max_tokens": effective_max_tokens,
            }
            # 添加可选的惩罚参数（仅当有值时）
            if effective_frequency_penalty is not None:
                request_params["frequency_penalty"] = effective_frequency_penalty
            if effective_presence_penalty is not None:
                request_params["presence_penalty"] = effective_presence_penalty
            
            response = await llm_client.chat.completions.create(**request_params)

            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content is not None:
                    delta = chunk.choices[0].delta.content
                    chunk_data = {
                        "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"content": delta},
                                "finish_reason": None,
                            }
                        ],
                    }
                    yield f"data: {json.dumps(chunk_data)}\n\n"

            # Send final chunk
            final_chunk = {
                "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop"
                    }
                ],
            }
            yield f"data: {json.dumps(final_chunk)}\n\n"
            yield "data: [DONE]\n\n"
        
        def generate_stream_sync():
            """同步流式生成器（用于旧版客户端）"""
            # 构建请求参数
            request_params = {
                "model": model,
                "messages": prepared_messages,
                "temperature": effective_temperature,
                "stream": True,
                "max_tokens": effective_max_tokens,
            }
            # 添加可选的惩罚参数（仅当有值时）
            if effective_frequency_penalty is not None:
                request_params["frequency_penalty"] = effective_frequency_penalty
            if effective_presence_penalty is not None:
                request_params["presence_penalty"] = effective_presence_penalty
            
            response = llm_client.chat.completions.create(**request_params)

            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content is not None:
                    delta = chunk.choices[0].delta.content
                    chunk_data = {
                        "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"content": delta},
                                "finish_reason": None,
                            }
                        ],
                    }
                    yield f"data: {json.dumps(chunk_data)}\n\n"

            # Send final chunk
            final_chunk = {
                "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop"
                    }
                ],
            }
            yield f"data: {json.dumps(final_chunk)}\n\n"
            yield "data: [DONE]\n\n"
        
        # 根据客户端类型选择生成器
        if channel_info is not None:
            # LLM Manager渠道使用异步生成器
            return StreamingResponse(generate_stream_async(), media_type="text/event-stream")
        else:
            return StreamingResponse(generate_stream_sync(), media_type="text/event-stream")
    else:
        # 非流式响应
        try:
            # 构建请求参数
            request_params = {
                "model": model,
                "messages": prepared_messages,
                "temperature": effective_temperature,
                "max_tokens": effective_max_tokens,
            }
            # 添加可选的惩罚参数（仅当有值时）
            if effective_frequency_penalty is not None:
                request_params["frequency_penalty"] = effective_frequency_penalty
            if effective_presence_penalty is not None:
                request_params["presence_penalty"] = effective_presence_penalty
            
            if channel_info is not None:
                # LLM Manager渠道使用异步调用
                response = await llm_client.chat.completions.create(**request_params)
            else:
                response = llm_client.chat.completions.create(**request_params)
            
            # 记录成功日志
            response_time = time.time() - start_time
            await _log_api_call(
                request_id=request_id,
                channel_info=channel_info,
                model=model,
                start_time=start_time,
                status="success",
                prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
                completion_tokens=response.usage.completion_tokens if response.usage else 0,
            )
            
            # 更新渠道指标
            if channel_info is not None:
                _update_channel_metrics(channel_info, success=True, response_time=response_time)
            
            
            return ChatCompletionResponse(
                id=response.id,
                created=response.created,
                model=response.model,
                choices=[
                    ChatCompletionChoice(
                        index=0,
                        message={
                            "role": "assistant",
                            "content": response.choices[0].message.content,
                        },
                        finish_reason=response.choices[0].finish_reason,
                    )
                ],
                usage={
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                }
            )
        except Exception as e:
            # 记录错误日志
            await _log_api_call(
                request_id=request_id,
                channel_info=channel_info,
                model=model,
                start_time=start_time,
                status="error",
                error_message=str(e)
            )
            # 更新渠道指标
            if channel_info is not None:
                _update_channel_metrics(channel_info, success=False, response_time=time.time() - start_time)
            
            # 使用错误处理器
            provider = channel_info.provider.lower() if channel_info and hasattr(channel_info, 'provider') else 'openai'
            if ERROR_HANDLER_AVAILABLE:
                classified_error = classify_provider_error(e, provider)
                return create_error_response(classified_error)
            raise HTTPException(status_code=500, detail="LLM调用失败")


async def _handle_non_openai_provider(
    factory,
    channel_info,
    messages: List[Dict[str, Any]],
    temperature: float,
    max_tokens: int,
    stream: bool,
    model: str,
):
    """
    处理非OpenAI兼容的厂商（Claude/Google）
    
    使用ChannelClientFactory中的专用方法进行API调用
    """
    if stream:
        # 流式响应
        async def generate_stream():
            try:
                response_gen = await factory.chat_completion(
                    channel_info=channel_info,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True,
                )
                
                # 根据厂商类型处理流式响应
                provider = channel_info.provider.lower()
                
                if provider == 'claude':
                    # Claude流式响应处理（SSE格式：data: {...}）
                    # 支持 Extended Thinking 的 thinking 块
                    # 添加buffer累积处理跨chunk的SSE数据
                    sse_buffer = ""
                    
                    async for line in response_gen:
                        line = line if isinstance(line, str) else line.decode('utf-8')
                        sse_buffer += line
                        
                        # 按换行符分割，保留最后一个可能不完整的行
                        lines = sse_buffer.split('\n')
                        sse_buffer = lines.pop()  # 保留最后不完整的部分
                        
                        for complete_line in lines:
                            complete_line = complete_line.strip()
                            if not complete_line:
                                continue
                            
                            if complete_line.startswith("data: "):
                                data_str = complete_line[6:].strip()
                                if data_str == "[DONE]":
                                    yield "data: [DONE]\n\n"
                                    continue
                                try:
                                    data = json.loads(data_str)
                                    # 转换Claude流式格式为OpenAI格式
                                    event_type = data.get("type", "")
                                    
                                    if event_type == "content_block_delta":
                                        delta = data.get("delta", {})
                                        delta_type = delta.get("type", "")
                                        
                                        # 处理文本内容
                                        if delta_type == "text_delta":
                                            delta_text = delta.get("text", "")
                                            if delta_text:
                                                chunk_data = {
                                                    "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
                                                    "object": "chat.completion.chunk",
                                                    "created": int(time.time()),
                                                    "model": model,
                                                    "choices": [{
                                                        "index": 0,
                                                        "delta": {"content": delta_text},
                                                        "finish_reason": None,
                                                    }],
                                                }
                                                yield f"data: {json.dumps(chunk_data)}\n\n"
                                        # 处理思考内容（Extended Thinking）- 可选择是否输出
                                        elif delta_type == "thinking_delta":
                                            # 默认不输出思考过程，如需输出可取消注释
                                            pass
                                            
                                    elif event_type == "message_stop":
                                        final_chunk = {
                                            "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
                                            "object": "chat.completion.chunk",
                                            "created": int(time.time()),
                                            "model": model,
                                            "choices": [{
                                                "index": 0,
                                                "delta": {},
                                                "finish_reason": "stop",
                                            }],
                                        }
                                        yield f"data: {json.dumps(final_chunk)}\n\n"
                                        yield "data: [DONE]\n\n"
                                        
                                    # 处理错误事件
                                    elif event_type == "error":
                                        error_msg = data.get("error", {}).get("message", "Unknown error")
                                        logger.error(f"[Claude Stream] 错误: {error_msg}")
                                        error_chunk = {"error": {"message": error_msg, "type": "api_error"}}
                                        yield f"data: {json.dumps(error_chunk)}\n\n"
                                        
                                except json.JSONDecodeError as e:
                                    logger.warning(f"[Claude Stream] JSON解析失败: {e}, 内容: {data_str[:100]}")
                                    continue
                                
                elif provider == 'google':
                    # Google流式响应处理
                    # Google streamGenerateContent 返回格式可能是：
                    # 1. 格式化的多行 JSON 数组（每行是 JSON 片段）
                    # 2. 紧凑的单行/少量行 JSON 数组：[{...},{...}]
                    # 需要累积内容并解析数组中的每个对象
                    
                    full_buffer = ""
                    has_yielded_content = False
                    
                    # 辅助函数：处理单个 Google 响应对象
                    def process_google_object(data):
                        nonlocal has_yielded_content
                        results = []
                        
                        # 检查是否有错误
                        if "error" in data:
                            error_msg = data["error"].get("message", "Unknown error")
                            logger.error(f"[Google Stream] API错误: {error_msg}")
                            error_chunk = {"error": {"message": error_msg, "type": "api_error"}}
                            results.append(f"data: {json.dumps(error_chunk)}\n\n")
                            return results
                        
                        candidates = data.get("candidates", [])
                        if candidates:
                            # 检查 finishReason
                            finish_reason = candidates[0].get("finishReason")
                            if finish_reason and finish_reason not in ["STOP", None]:
                                logger.warning(f"[Google Stream] finishReason={finish_reason}")
                            
                            parts = candidates[0].get("content", {}).get("parts", [])
                            for part in parts:
                                if "text" in part:
                                    text_content = part["text"]
                                    logger.debug(f"[Google Stream] 提取文本长度: {len(text_content)}")
                                    chunk_data = {
                                        "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
                                        "object": "chat.completion.chunk",
                                        "created": int(time.time()),
                                        "model": model,
                                        "choices": [{
                                            "index": 0,
                                            "delta": {"content": text_content},
                                            "finish_reason": None,
                                        }],
                                    }
                                    results.append(f"data: {json.dumps(chunk_data)}\n\n")
                                    has_yielded_content = True
                        else:
                            logger.warning(f"[Google Stream] 响应无candidates: {list(data.keys())}")
                        
                        return results
                    
                    async for line in response_gen:
                        line = line.strip() if isinstance(line, str) else line.decode('utf-8').strip()
                        if not line:
                            continue
                        
                        # 记录收到的原始内容（首次或内容变化时）
                        if not full_buffer:
                            logger.info(f"[Google Stream] 首次收到内容，前100字符: {line[:100]}")
                        
                        full_buffer += line
                        
                        # 尝试解析累积的内容
                        # 首先尝试作为 JSON 数组解析
                        try:
                            parsed = json.loads(full_buffer)
                            logger.debug(f"[Google Stream] 成功解析完整JSON")
                            
                            # 如果是数组，处理每个元素
                            if isinstance(parsed, list):
                                for item in parsed:
                                    for result in process_google_object(item):
                                        yield result
                            else:
                                # 单个对象
                                for result in process_google_object(parsed):
                                    yield result
                            
                            full_buffer = ""  # 重置缓冲区
                            
                        except json.JSONDecodeError:
                            # JSON 不完整，继续累积
                            # 但检查是否可以提取已完成的对象
                            # 对于 [{...},{...}] 格式，尝试提取已完成的对象
                            if full_buffer.startswith('['):
                                # 尝试找到完整的对象并提取
                                temp_buffer = full_buffer[1:]  # 去掉开头的 [
                                extracted_any = False
                                
                                while temp_buffer:
                                    temp_buffer = temp_buffer.lstrip(' ,\n\r\t')
                                    if not temp_buffer or temp_buffer.startswith(']'):
                                        break
                                    
                                    # 尝试找到一个完整的 JSON 对象
                                    if temp_buffer.startswith('{'):
                                        # 计算括号平衡来找到对象结束位置
                                        brace_count = 0
                                        in_string = False
                                        escape_next = False
                                        end_pos = -1
                                        
                                        for i, char in enumerate(temp_buffer):
                                            if escape_next:
                                                escape_next = False
                                                continue
                                            if char == '\\':
                                                escape_next = True
                                                continue
                                            if char == '"':
                                                in_string = not in_string
                                                continue
                                            if not in_string:
                                                if char == '{':
                                                    brace_count += 1
                                                elif char == '}':
                                                    brace_count -= 1
                                                    if brace_count == 0:
                                                        end_pos = i
                                                        break
                                        
                                        if end_pos > 0:
                                            obj_str = temp_buffer[:end_pos + 1]
                                            try:
                                                obj = json.loads(obj_str)
                                                logger.debug(f"[Google Stream] 提取到完整对象")
                                                for result in process_google_object(obj):
                                                    yield result
                                                temp_buffer = temp_buffer[end_pos + 1:]
                                                extracted_any = True
                                            except json.JSONDecodeError as e:
                                                logger.debug(f"[Google Stream] 对象解析失败: {e}")
                                                break
                                        else:
                                            # 对象不完整
                                            break
                                    else:
                                        break
                                
                                if extracted_any:
                                    # 重建 buffer：保留未处理的部分
                                    temp_buffer = temp_buffer.lstrip(' ,\n\r\t')
                                    if temp_buffer:
                                        full_buffer = '[' + temp_buffer
                                    else:
                                        full_buffer = ""
                            
                            continue
                    
                    # 流结束后，尝试解析剩余内容
                    remaining = full_buffer.strip()
                    # 清理可能的数组残留符号
                    if remaining.startswith('['):
                        remaining = remaining[1:].strip()
                    if remaining.endswith(']'):
                        remaining = remaining[:-1].strip()
                    # 清理开头的逗号
                    while remaining.startswith(','):
                        remaining = remaining[1:].strip()
                    
                    if remaining:
                        logger.debug(f"[Google Stream] 流结束，剩余内容: {remaining[:200]}...")
                        try:
                            # 尝试作为单个对象解析
                            parsed = json.loads(remaining)
                            for result in process_google_object(parsed):
                                yield result
                        except json.JSONDecodeError:
                            # 尝试作为数组解析
                            try:
                                parsed = json.loads(f"[{remaining}]")
                                for item in parsed:
                                    for result in process_google_object(item):
                                        yield result
                            except json.JSONDecodeError as e:
                                # 最后尝试提取其中的对象
                                logger.warning(f"[Google Stream] 流结束时剩余内容无法解析: {e}, 内容: {remaining[:300]}...")
                    
                    if not has_yielded_content:
                        logger.error("[Google Stream] 未能提取任何内容！")
                    
                    # 发送结束标记
                    final_chunk = {
                        "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop",
                        }],
                    }
                    yield f"data: {json.dumps(final_chunk)}\n\n"
                    yield "data: [DONE]\n\n"
                    
                else:
                    # 通用 OpenAI 兼容格式处理（适用于通义千问、DeepSeek等）
                    # SSE格式：data: {...}
                    # 添加buffer累积处理跨chunk的SSE数据
                    sse_buffer = ""
                    
                    async for line in response_gen:
                        line = line if isinstance(line, str) else line.decode('utf-8')
                        sse_buffer += line
                        
                        # 按换行符分割，保留最后一个可能不完整的行
                        lines = sse_buffer.split('\n')
                        sse_buffer = lines.pop()  # 保留最后不完整的部分
                        
                        for complete_line in lines:
                            complete_line = complete_line.strip()
                            if not complete_line:
                                continue
                            
                            # 处理 SSE 格式
                            if complete_line.startswith("data: "):
                                data_str = complete_line[6:].strip()
                                if data_str == "[DONE]":
                                    yield "data: [DONE]\n\n"
                                    continue
                                try:
                                    data = json.loads(data_str)
                                    
                                    # 检查是否有错误
                                    if "error" in data:
                                        error_msg = data["error"].get("message", "Unknown error")
                                        logger.error(f"[OpenAI Compatible Stream] 错误: {error_msg}")
                                        yield f"data: {json.dumps(data)}\n\n"
                                        continue
                                    
                                    # 提取内容
                                    choices = data.get("choices", [])
                                    if choices:
                                        delta = choices[0].get("delta", {})
                                        content = delta.get("content")
                                        finish_reason = choices[0].get("finish_reason")
                                        
                                        if content:
                                            chunk_data = {
                                                "id": data.get("id", f"chatcmpl-{uuid.uuid4().hex[:24]}"),
                                                "object": "chat.completion.chunk",
                                                "created": data.get("created", int(time.time())),
                                                "model": model,
                                                "choices": [{
                                                    "index": 0,
                                                    "delta": {"content": content},
                                                    "finish_reason": None,
                                                }],
                                            }
                                            yield f"data: {json.dumps(chunk_data)}\n\n"
                                        
                                        if finish_reason:
                                            final_chunk = {
                                                "id": data.get("id", f"chatcmpl-{uuid.uuid4().hex[:24]}"),
                                                "object": "chat.completion.chunk",
                                                "created": data.get("created", int(time.time())),
                                                "model": model,
                                                "choices": [{
                                                    "index": 0,
                                                    "delta": {},
                                                    "finish_reason": finish_reason,
                                                }],
                                            }
                                            yield f"data: {json.dumps(final_chunk)}\n\n"
                                            
                                except json.JSONDecodeError as e:
                                    logger.warning(f"[OpenAI Compatible Stream] JSON解析失败: {e}, 内容: {data_str[:100]}")
                                    continue
                            else:
                                # 某些厂商可能不带 "data: " 前缀
                                try:
                                    data = json.loads(complete_line)
                                    choices = data.get("choices", [])
                                    if choices:
                                        delta = choices[0].get("delta", {})
                                        content = delta.get("content")
                                        if content:
                                            chunk_data = {
                                                "id": data.get("id", f"chatcmpl-{uuid.uuid4().hex[:24]}"),
                                                "object": "chat.completion.chunk",
                                                "created": data.get("created", int(time.time())),
                                                "model": model,
                                                "choices": [{
                                                    "index": 0,
                                                    "delta": {"content": content},
                                                    "finish_reason": None,
                                                }],
                                            }
                                            yield f"data: {json.dumps(chunk_data)}\n\n"
                                except json.JSONDecodeError:
                                    # 忽略非JSON行（如空行、注释等）
                                    continue
                    
                    # 确保发送结束标记
                    yield "data: [DONE]\n\n"
                    
            except Exception as e:
                logger.error(f"流式响应处理错误: {e}")
                error_chunk = {
                    "error": {"message": str(e), "type": "api_error"}
                }
                yield f"data: {json.dumps(error_chunk)}\n\n"
        
        return StreamingResponse(generate_stream(), media_type="text/event-stream")
    else:
        # 非流式响应 - 直接调用并返回已转换的OpenAI格式
        response = await factory.chat_completion(
            channel_info=channel_info,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
        )
        
        # response已经是OpenAI格式（由channel_client转换）
        return ChatCompletionResponse(
            id=response.get("id", f"chatcmpl-{uuid.uuid4().hex[:24]}"),
            created=response.get("created", int(time.time())),
            model=response.get("model", model),
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message={
                        "role": "assistant",
                        "content": response["choices"][0]["message"]["content"],
                    },
                    finish_reason=response["choices"][0].get("finish_reason", "stop"),
                )
            ],
            usage=response.get("usage", {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            })
        )


async def _generate_stream_with_execution_async(
    llm_client,
    model: str,
    vllm_messages: List[Dict],
    temperature: float,
    workspace_dir: str,
    generated_dir: str,
    temp_thread,
    original_messages: List[Dict],
    generated_files: List[Dict],
    channel_info: Optional[Any] = None,
    max_tokens: Optional[int] = None,
    session_id: Optional[str] = None,  # 添加session_id参数用于任务记录
):
    """
    异步生成器：流式响应 + 代码执行
    
    支持LLM Manager渠道（AsyncOpenAI）和旧版客户端
    
    注意：max_tokens应从渠道配置获取，调用方负责传入正确的值
    """
    # 记录开始时间用于计算耗时
    request_start_time = time.time()
    
    # Phase 14: 跟踪是否执行了代码，只有执行了代码才创建任务记录
    code_executed = False
    
    assistant_reply = ""
    finished = False
    tracker = WorkspaceTracker(workspace_dir, generated_dir)
    
    # 判断是否使用异步客户端
    is_async_client = channel_info is not None

    while not finished:
        if is_async_client:
            # LLM Manager渠道：异步调用
            response = await llm_client.chat.completions.create(
                model=model,
                messages=vllm_messages,
                temperature=temperature,
                stream=True,
                max_tokens=max_tokens,
            )
        else:
            # 旧版客户端：同步调用（在线程池中执行）
            import asyncio
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: llm_client.chat.completions.create(
                    model=model,
                    messages=vllm_messages,
                    temperature=temperature,
                    stream=True,
                    max_tokens=max_tokens,
                )
            )

        cur_res = ""
        last_chunk = None
        
        # 根据客户端类型选择迭代方式
        if is_async_client:
            async for chunk in response:
                last_chunk = chunk
                if chunk.choices and chunk.choices[0].delta.content is not None:
                    delta = chunk.choices[0].delta.content
                    cur_res += delta
                    assistant_reply += delta

                    chunk_data = {
                        "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"content": delta},
                                "finish_reason": None,
                            }
                        ],
                    }
                    yield f"data: {json.dumps(chunk_data)}\n\n"

                if "</Answer>" in cur_res:
                    finished = True
                    break
        else:
            # 同步迭代器
            for chunk in response:
                last_chunk = chunk
                if chunk.choices and chunk.choices[0].delta.content is not None:
                    delta = chunk.choices[0].delta.content
                    cur_res += delta
                    assistant_reply += delta

                    chunk_data = {
                        "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"content": delta},
                                "finish_reason": None,
                            }
                        ],
                    }
                    yield f"data: {json.dumps(chunk_data)}\n\n"

                if "</Answer>" in cur_res:
                    finished = True
                    break

        finish_reason = (
            last_chunk.choices[0].finish_reason
            if last_chunk and last_chunk.choices
            else None
        )

        has_code_segment = "<Code>" in cur_res
        has_closed_code = "</Code>" in cur_res

        if finish_reason == "stop" and not finished:
            if has_code_segment and not has_closed_code:
                cur_res += "</Code>"
                assistant_reply += "</Code>"
                has_closed_code = True
            elif not has_code_segment:
                finished = True

        # Handle code execution
        if has_code_segment and has_closed_code and not finished:
            vllm_messages.append({"role": "assistant", "content": cur_res})

            code_str = extract_code_from_segment(cur_res)
            if code_str:
                # 使用异步代码执行
                exe_output = await execute_code_safe_async(code_str, workspace_dir)
                artifacts = tracker.diff_and_collect()
                exe_str = f"\n<Execute>\n```\n{exe_output}\n```\n</Execute>\n"
                file_block = render_file_block(
                    artifacts, workspace_dir, temp_thread.id, generated_files
                )
                assistant_reply += exe_str + file_block
                
                # Phase 14: 标记已执行代码
                code_executed = True

                # Stream execution result
                for char in exe_str:
                    chunk_data = {
                        "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"content": char},
                                "finish_reason": None,
                            }
                        ],
                    }
                    yield f"data: {json.dumps(chunk_data)}\n\n"

                vllm_messages.append({"role": "execute", "content": exe_output})
            else:
                finished = True

    # Generate and stream report
    report_block = generate_report_from_messages(
        original_messages, assistant_reply, workspace_dir, temp_thread.id, generated_files
    )
    if report_block:
        for char in report_block:
            chunk_data = {
                "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": char},
                        "finish_reason": None,
                    }
                ],
            }
            yield f"data: {json.dumps(chunk_data)}\n\n"

    # Send final chunk with generated files
    final_chunk_data = {}
    if generated_files:
        final_chunk_data["files"] = generated_files

    final_chunk = {
        "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": final_chunk_data,
                "finish_reason": "stop"
            }
        ],
    }

    # Keep backward compatibility with generated_files field
    if generated_files:
        final_chunk["generated_files"] = generated_files

    yield f"data: {json.dumps(final_chunk)}\n\n"
    
    # Phase 14: 只有在实际执行了代码时才创建任务记录
    # 这避免了普通AI对话（没有代码执行）被错误地记录为任务
    if session_id and TASK_MANAGER_AVAILABLE and code_executed:
        duration_seconds = time.time() - request_start_time
        # 创建并完成任务记录
        message_count = len([m for m in original_messages if m.get("role") == "user"])
        _create_inference_task_record(
            session_id=session_id,
            message_count=message_count,
            file_count=len(generated_files)
        )
        _update_inference_task_status(
            session_id=session_id,
            status="completed",
            duration_seconds=duration_seconds
        )
    
    yield "data: [DONE]\n\n"


async def _non_streaming_with_execution(
    llm_client,
    model: str,
    vllm_messages: List[Dict],
    temperature: float,
    workspace_dir: str,
    generated_dir: str,
    temp_thread,
    original_messages: List[Dict],
    file_ids: Optional[List[str]],
    generated_files: List[Dict],
    channel_info: Optional[Any] = None,
    max_tokens: Optional[int] = None,
    session_id: Optional[str] = None,  # 添加session_id参数用于任务记录
) -> Dict:
    """Non-streaming response with code execution workflow
    
    Args:
        llm_client: LLM客户端实例
        model: 模型名称
        vllm_messages: 消息列表
        temperature: 温度参数（应从渠道配置获取）
        workspace_dir: 工作区目录
        generated_dir: 生成文件目录
        temp_thread: 临时线程
        original_messages: 原始消息
        file_ids: 文件ID列表
        generated_files: 生成文件列表
        channel_info: 渠道信息（可选，用于LLM Manager渠道）
        max_tokens: 最大token数（应从渠道配置获取）
        max_tokens: 最大token数
    """
    import openai
    
    # 记录开始时间用于计算耗时
    request_start_time = time.time()
    
    # Phase 14: 跟踪是否执行了代码，只有执行了代码才创建任务记录
    code_executed = False
    
    # 根据是否使用LLM Manager渠道决定客户端
    if channel_info is not None:
        # LLM Manager渠道已经是AsyncOpenAI
        llm_client_async = llm_client
    else:
        # 旧版客户端需要创建异步版本
        llm_client_async = openai.AsyncOpenAI(
            base_url=llm_client.base_url,
            api_key=llm_client.api_key,
        )
    
    assistant_reply = ""
    finished = False
    tracker = WorkspaceTracker(workspace_dir, generated_dir)

    while not finished:
        # Use async client to avoid blocking
        response = await llm_client_async.chat.completions.create(
            model=model,
            messages=vllm_messages,
            temperature=temperature,
            stream=True,
            max_tokens=max_tokens,
        )

        cur_res = ""
        last_finish_reason: Optional[str] = None
        
        # Iterate through async chunks
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content is not None:
                delta = chunk.choices[0].delta.content
                cur_res += delta
                assistant_reply += delta
            last_finish_reason = chunk.choices[0].finish_reason
            if "</Answer>" in cur_res:
                finished = True
                break

        has_code_segment = "<Code>" in cur_res
        has_closed_code = "</Code>" in cur_res

        if last_finish_reason == "stop" and not finished:
            if has_code_segment and not has_closed_code:
                cur_res += "</Code>"
                assistant_reply += "</Code>"
                has_closed_code = True
            elif not has_code_segment:
                finished = True

        if "</Answer>" in cur_res:
            finished = True

        if has_code_segment and has_closed_code and not finished:
            vllm_messages.append({"role": "assistant", "content": cur_res})
            code_str = extract_code_from_segment(cur_res)
            if code_str:
                # Use async version of execute_code_safe to avoid blocking
                exe_output = await execute_code_safe_async(code_str, workspace_dir)
                artifacts = tracker.diff_and_collect()
                exe_str = f"\n<Execute>\n```\n{exe_output}\n```\n</Execute>\n"
                file_block = render_file_block(
                    artifacts, workspace_dir, temp_thread.id, generated_files
                )
                assistant_reply += exe_str + file_block
                vllm_messages.append({"role": "execute", "content": exe_output})
                
                # Phase 14: 标记已执行代码
                code_executed = True
            else:
                finished = True

    # Generate report
    report_block = generate_report_from_messages(
        original_messages, assistant_reply, workspace_dir, temp_thread.id, generated_files
    )
    assistant_reply += report_block

    result_content = assistant_reply

    # Prepare message with files for OpenAI compatibility
    message_data = {
        "role": "assistant",
        "content": result_content,
    }

    # Add files to message object (new OpenAI compatibility)
    if generated_files:
        message_data["files"] = generated_files

    result = {
        "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": message_data,
                "finish_reason": "stop",
            }
        ],
    }

    # Keep backward compatibility with generated_files field
    if generated_files:
        result["generated_files"] = generated_files
    if file_ids:
        result["attached_files"] = file_ids

    # Phase 14: 只有在实际执行了代码时才创建任务记录
    # 这避免了普通AI对话（没有代码执行）被错误地记录为任务
    if session_id and TASK_MANAGER_AVAILABLE and code_executed:
        duration_seconds = time.time() - request_start_time
        # 创建并完成任务记录
        message_count = len([m for m in original_messages if m.get("role") == "user"])
        _create_inference_task_record(
            session_id=session_id,
            message_count=message_count,
            file_count=len(generated_files)
        )
        _update_inference_task_status(
            session_id=session_id,
            status="completed",
            duration_seconds=duration_seconds
        )

    return result


# =============================================================================
# API调用日志查询端点
# =============================================================================

@router.get("/logs/recent")
async def get_recent_api_logs(limit: int = 20):
    """
    获取最近的API调用日志
    
    Parameters:
    - limit: 返回的日志条数（默认20，最大100）
    
    Returns:
        最近的API调用日志列表
    """
    if not API_LOGGER_AVAILABLE:
        return {
            "success": False,
            "error": "API Logger not available"
        }
    
    try:
        api_logger = get_chat_api_logger()
        logs = api_logger.get_recent_logs(min(limit, 100))
        return {
            "success": True,
            "data": {
                "logs": logs,
                "count": len(logs)
            }
        }
    except Exception as e:
        logger.error(f"获取API日志失败: {e}")
        return {
            "success": False,
            "error": "获取API日志失败"
        }


@router.get("/logs/stats")
async def get_api_logs_stats():
    """
    获取API调用统计信息
    
    Returns:
        调用统计信息（总调用数、成功率、总token数、总成本等）
    """
    if not API_LOGGER_AVAILABLE:
        return {
            "success": False,
            "error": "API Logger not available"
        }
    
    try:
        api_logger = get_chat_api_logger()
        stats = api_logger.get_stats()
        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        logger.error(f"获取API统计失败: {e}")
        return {
            "success": False,
            "error": "获取API统计失败"
        }


@router.get("/channels/health")
async def get_channels_health():
    """
    获取Chat API使用的渠道健康状态
    
    Returns:
        各渠道的健康状态和指标
    """
    try:
        from llm_manager_integrated.core.load_balancer import get_load_balancer
        
        load_balancer = get_load_balancer()
        metrics = load_balancer.get_metrics()
        
        return {
            "success": True,
            "data": {
                "summary": {
                    "total_channels": metrics["total_channels"],
                    "healthy_channels": metrics["healthy_channels"],
                    "unhealthy_channels": metrics["unhealthy_channels"],
                    "strategy": metrics["strategy"],
                },
                "channels": [
                    {
                        "channel_id": channel_id,
                        "metrics": channel_metrics
                    }
                    for channel_id, channel_metrics in metrics["channel_metrics"].items()
                ]
            }
        }
    except Exception as e:
        logger.error(f"获取渠道健康状态失败: {e}")
        return {
            "success": False,
            "error": "获取渠道健康状态失败"
        }


# =============================================================================
# AI 分析 Prompt API（Phase 1: 后端抽离）
# =============================================================================

@router.post("/analysis/prompt")
async def get_analysis_prompt_endpoint(
    request: Dict[str, Any] = Body(...)
):
    """
    获取 AI 分析提示词
    
    Phase 1: 将 prompt 构建逻辑从前端迁移到后端
    
    Request Body:
        - analysis_type: "overall" | "stage"
        - task_type: "scorecard_dev" | "rule_mining" (可选)
        - stage_id: 阶段ID (stage分析必需)
        - stage_name: 阶段名称 (stage分析可选)
        - data: 阶段输出数据 (stage分析必需)
        - result: 任务结果数据 (overall分析必需)
    
    Returns:
        - success: bool
        - prompt: str (分析提示词)
        - params: dict (AI分析专用参数)
    """
    try:
        from AI_analysis_prompts import get_analysis_prompt, AI_ANALYSIS_PARAMS
        
        analysis_type = request.get("analysis_type", "stage")
        task_type = request.get("task_type")
        stage_id = request.get("stage_id")
        stage_name = request.get("stage_name")
        data = request.get("data")
        result = request.get("result")
        
        prompt = get_analysis_prompt(
            analysis_type=analysis_type,
            task_type=task_type,
            stage_id=stage_id,
            stage_name=stage_name,
            data=data,
            result=result
        )
        
        return {
            "success": True,
            "prompt": prompt,
            "params": AI_ANALYSIS_PARAMS
        }
        
    except ValueError as e:
        logger.warning(f"分析Prompt参数错误: {e}")
        return {
            "success": False,
            "error": "分析Prompt参数错误"
        }
    except Exception as e:
        logger.error(f"获取分析Prompt失败: {e}", exc_info=True)
        return {
            "success": False,
            "error": "获取分析Prompt失败"
        }
