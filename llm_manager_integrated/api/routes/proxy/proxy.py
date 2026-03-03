"""
API代理路由 - 提供LLM API代理服务（已废弃，保留作为备用参考）

⚠️ DEPRECATED: 此模块已废弃，保留作为备用参考和问题诊断资料。

功能迁移说明：
- /chat/completions → 已迁移到 Chat API (/v1/chat/completions)
- /channels/status → 已迁移到 monitoring (/llm-manager/api/monitoring/channels/status)
- /load-balancer/* → 已迁移到 monitoring (/llm-manager/api/monitoring/load-balancer/*)
- /channels/{id}/health-check → 已迁移到 monitoring

推荐使用新端点，此模块将在未来版本移除。
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Request, Response, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
import httpx

from llm_manager_integrated.core.load_balancer import get_load_balancer, create_channel_from_config, LoadBalanceStrategy
from llm_manager_integrated.core.config import settings
from llm_manager_integrated.core.crud import (
    get_channel, 
    get_channels, 
    get_active_channels,
    create_api_log, 
    get_api_logs, 
    get_api_log_stats
)
from llm_manager_integrated.models.schemas import (
    ChatCompletionRequest, 
    ChatCompletionResponse, 
    ErrorResponse,
    ModelObject,
    ModelsListResponse
)
from llm_manager_integrated.api.responses import success_response, error_response
from llm_manager_integrated.models.database import DatabaseManager
from llm_manager_integrated.api.dependencies import get_db_manager as get_db_manager_dep
from llm_manager_integrated.api.routes.channels import get_model_capabilities

router = APIRouter()
logger = logging.getLogger(__name__)

# HTTP客户端配置
_http_client: Optional[httpx.AsyncClient] = None


def get_http_client() -> httpx.AsyncClient:
    """获取HTTP客户端实例"""
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.api_timeout),
            limits=httpx.Limits(max_connections=settings.max_concurrent_requests)
        )
    return _http_client


def _convert_claude_response_to_openai(claude_response: Dict[str, Any], model: str) -> Dict[str, Any]:
    """
    将Claude API响应转换为OpenAI格式
    
    Claude响应格式:
    {
        "id": "msg_xxx",
        "type": "message",
        "role": "assistant",
        "content": [{"type": "text", "text": "..."}],
        "model": "claude-3-xxx",
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 10, "output_tokens": 20}
    }
    
    OpenAI响应格式:
    {
        "id": "chatcmpl-xxx",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "gpt-4",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": "..."}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
    }
    """
    # 提取内容
    content = ""
    if claude_response.get("content"):
        for block in claude_response["content"]:
            if block.get("type") == "text":
                content += block.get("text", "")
    
    # 转换stop_reason
    stop_reason_map = {
        "end_turn": "stop",
        "max_tokens": "length",
        "stop_sequence": "stop"
    }
    finish_reason = stop_reason_map.get(claude_response.get("stop_reason"), "stop")
    
    # 构建OpenAI格式响应
    usage = claude_response.get("usage", {})
    return {
        "id": claude_response.get("id", f"chatcmpl-{uuid.uuid4().hex[:8]}"),
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model or claude_response.get("model", "claude"),
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": content
            },
            "logprobs": None,
            "finish_reason": finish_reason
        }],
        "usage": {
            "prompt_tokens": usage.get("input_tokens", 0),
            "completion_tokens": usage.get("output_tokens", 0),
            "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
        }
    }


def _convert_google_response_to_openai(google_response: Dict[str, Any], model: str) -> Dict[str, Any]:
    """
    将Google AI API响应转换为OpenAI格式
    
    Google AI响应格式:
    {
        "candidates": [{
            "content": {"parts": [{"text": "..."}], "role": "model"},
            "finishReason": "STOP",
            "index": 0
        }],
        "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 20, "totalTokenCount": 30}
    }
    """
    # 提取内容
    content = ""
    candidates = google_response.get("candidates", [])
    if candidates:
        parts = candidates[0].get("content", {}).get("parts", [])
        for part in parts:
            if "text" in part:
                content += part["text"]
    
    # 转换finishReason
    finish_reason_map = {
        "STOP": "stop",
        "MAX_TOKENS": "length",
        "SAFETY": "content_filter",
        "RECITATION": "content_filter"
    }
    google_finish_reason = candidates[0].get("finishReason", "STOP") if candidates else "STOP"
    finish_reason = finish_reason_map.get(google_finish_reason, "stop")
    
    # 构建OpenAI格式响应
    usage = google_response.get("usageMetadata", {})
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model or "gemini",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": content
            },
            "logprobs": None,
            "finish_reason": finish_reason
        }],
        "usage": {
            "prompt_tokens": usage.get("promptTokenCount", 0),
            "completion_tokens": usage.get("candidatesTokenCount", 0),
            "total_tokens": usage.get("totalTokenCount", 0)
        }
    }


async def log_request_async(
    db_manager: DatabaseManager,
    request_id: str,
    channel_id: str,
    request_data: Dict[str, Any],
    response_data: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None,
    response_time: float = 0.0,
    status_code: int = 200
):
    """异步记录请求日志"""
    try:
        # 直接记录日志，不调用不存在的log_request函数
        logger.info(f"API请求: request_id={request_id}, channel_id={channel_id}, status={status_code}, time={response_time:.2f}s")
        if error_message:
            logger.warning(f"API请求错误: {error_message}")
    except Exception as e:
        # 日志记录失败不应该影响主要功能
        logger.warning(f"记录请求日志失败: {e}")


async def update_channel_metrics_async(
    db_manager: DatabaseManager,
    channel_id: str,
    response_time: float,
    success: bool,
    error_message: Optional[str] = None
):
    """异步更新渠道指标"""
    try:
        # 直接记录指标，不调用不存在的update_channel_metrics函数
        status = "success" if success else "failed"
        logger.debug(f"渠道指标更新: channel_id={channel_id}, status={status}, time={response_time:.2f}s")
        if error_message:
            logger.debug(f"渠道错误: {error_message}")
    except Exception as e:
        # 指标更新失败不应该影响主要功能
        logger.warning(f"更新渠道指标失败: {e}")


# @router.get("/models", response_model=ModelsListResponse) - 端点已移动到models_proxy.py
async def list_models(
    proxy_type: Optional[str] = None,  # 可选，指定特定类型
    include_unavailable: bool = False,  # 是否包含不可用模型
    refresh_cache: bool = False  # 是否刷新缓存
):
    """
    OpenAI兼容的模型列表接口
    
    从激活的渠道配置中获取可用模型列表，支持缓存和刷新机制
    """
    try:
        # 通过API调用获取激活渠道，而不是直接查询数据库
        import httpx
        
        # 调用内部API获取激活渠道
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.api_base_url}/api/manage/channels/active",
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to get active channels: {response.status_code}"
                )
            
            response_data = response.json()
            
            if not response_data.get("success", False):
                raise HTTPException(
                    status_code=500,
                    detail=f"API returned error: {response_data.get('message', 'Unknown error')}"
                )
            
            active_channels = response_data.get("data", [])
            
            # 如果指定了类型，进行过滤
            if proxy_type:
                active_channels = [ch for ch in active_channels if ch.get("type") == proxy_type]
            
            # 收集所有唯一模型
            model_set = set()
            model_objects = []
            
            for channel in active_channels:
                # 如果渠道不活跃且不包含不可用模型，则跳过
                if not channel.get("status", False) and not include_unavailable:
                    continue
                    
                # 获取渠道中的模型列表
                models_str = channel.get("models", "")
                models = models_str.split(',') if models_str else []
                for model_name in models:
                    model_name = model_name.strip()
                    if model_name and model_name not in model_set:
                        model_set.add(model_name)
                        
                        # 创建模型对象
                        model_obj = ModelObject(
                            id=model_name,
                            created=int(datetime.utcnow().timestamp()),
                            owned_by=channel.get("type", "unknown")
                        )
                        model_objects.append(model_obj)
            
            # 返回模型列表响应
            return ModelsListResponse(
                object="list",
                data=model_objects
            )
        
    except Exception as e:
        logger.error(f"获取模型列表失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list models: {str(e)}"
        )


@router.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    background_tasks: BackgroundTasks,
    http_request: Request,
    db_manager: DatabaseManager = Depends(get_db_manager_dep)
):
    """
    OpenAI 兼容的聊天完成接口
    
    ⚠️ DEPRECATED: 此端点已废弃，请使用 /v1/chat/completions
    
    该接口会根据负载均衡策略选择一个可用的渠道，
    转发请求并返回响应，同时记录请求日志和更新渠道指标。
    """
    # 记录废弃警告
    logger.warning(
        f"[DEPRECATED] /llm-manager/api/proxy/chat/completions 已废弃，"
        f"请迁移到 /v1/chat/completions。model={request.model}"
    )
    
    # 生成请求ID
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    # 获取负载均衡器
    # 直接使用全局函数获取负载均衡器
    load_balancer = get_load_balancer()
    logger.info(f"获取的负载均衡器，渠道数: {len(load_balancer.channels)}")
    
    # 如果负载均衡器为空，尝试从应用状态获取
    if len(load_balancer.channels) == 0:
        try:
            app_balancer = http_request.app.state.load_balancer
            if app_balancer and len(app_balancer.channels) > 0:
                # 将应用状态中的渠道复制到全局负载均衡器
                for channel_id, channel in app_balancer.channels.items():
                    load_balancer.add_channel(channel)
                logger.info(f"从应用状态复制了 {len(app_balancer.channels)} 个渠道到全局负载均衡器")
        except AttributeError:
            logger.warning("无法从应用状态获取负载均衡器")
            
        # 如果仍然为空，直接从数据库加载
        if len(load_balancer.channels) == 0:
            logger.info("负载均衡器为空，直接从数据库加载渠道")
            try:
                # 从数据库获取所有启用的渠道
                from llm_manager_integrated.models.database import get_db_manager
                db_manager = get_db_manager()
                with db_manager.get_session() as db:
                    channels = get_channels(db=db)
                    
                    for channel in channels:
                        if channel.status:  # 只加载启用的渠道
                            lb_channel = create_channel_from_config({
                                'id': str(channel.id),
                                'name': channel.name,
                                'api_base': channel.base_url,
                                'api_key': channel.api_key,
                                'model': channel.models,
                                'type': channel.type,  # 传递渠道类型
                                'weight': 1,
                                'max_qps': 10,
                                'timeout': 30
                            })
                            load_balancer.add_channel(lb_channel)
                            logger.info(f"直接加载渠道: {channel.name} ({channel.id})")
                    
                    logger.info(f"直接加载完成，共加载 {len([c for c in channels if c.status])} 个渠道")
            except Exception as e:
                logger.error(f"直接加载渠道失败: {e}")
    
    # 选择渠道（根据请求的model过滤）
    channel = await load_balancer.select_channel(model=request.model)
    if not channel:
        background_tasks.add_task(
            log_request_async,
            db_manager, request_id, "", request.dict(), None,
            "没有可用的渠道", 0.0, 503
        )
        raise HTTPException(
            status_code=503,
            detail=error_response(
                code=503,
                message="没有可用的渠道"
            )
        )
    
    try:
        # 准备转发请求
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "LLM-API-Manager/2.0.0"
        }
        
        # 构建请求体
        request_body = request.dict(exclude={'system_prompt'})  # 排除system_prompt，不发送给外部API
        # 确保使用渠道配置的模型
        if channel.model:
            request_body["model"] = channel.model
        
        # 检查模型是否支持流式输出
        model_name = request_body.get("model") or channel.model
        model_capabilities = get_model_capabilities(model_name)
        supports_stream = model_capabilities.get('supports_stream', True)
        
        # 如果模型不支持流式，强制关闭
        if not supports_stream and request.stream:
            logger.warning(f"模型 {model_name} 不支持流式输出，已强制关闭 stream 参数")
            request.stream = False
            request_body["stream"] = False
        
        # 处理系统提示词
        system_prompt_content = None
        if request.system_prompt and request.system_prompt.strip():
            system_prompt_content = request.system_prompt.strip()
        
        # 根据渠道类型进行适配
        if channel.channel_type == "claude":
            # Claude使用Anthropic API格式
            url = f"{channel.api_base.rstrip('/')}/messages"
            headers["x-api-key"] = channel.api_key
            headers["anthropic-version"] = "2023-06-01"
            
            # 转换OpenAI格式到Anthropic格式
            anthropic_messages = []
            for msg in request_body.get("messages", []):
                role = msg.get("role", "user")
                content = msg.get("content", "")
                # Anthropic不支持system角色在messages中，需要单独处理
                if role == "system":
                    if not system_prompt_content:
                        system_prompt_content = content
                    continue
                # Anthropic只支持user和assistant角色
                if role in ["user", "assistant"]:
                    anthropic_messages.append({"role": role, "content": content})
            
            # 构建Anthropic请求体（只包含Claude支持的参数）
            request_body = {
                "model": request_body.get("model"),
                "messages": anthropic_messages,
                "max_tokens": request_body.get("max_tokens") or 4096,
            }
            if system_prompt_content:
                request_body["system"] = system_prompt_content
            if request.temperature is not None:
                request_body["temperature"] = request.temperature
            if request.top_p is not None:
                request_body["top_p"] = request.top_p
            if request.stream:
                request_body["stream"] = True
            # Claude支持stop_sequences
            if request.stop:
                stop_sequences = [request.stop] if isinstance(request.stop, str) else request.stop
                request_body["stop_sequences"] = stop_sequences
            # 注意：Claude不支持以下OpenAI参数：
            # - n, presence_penalty, frequency_penalty, logit_bias, user
            # - response_format, seed, tools, tool_choice, logprobs, top_logprobs
                
        elif channel.channel_type == "google":
            # Google AI使用自有API格式
            # URL格式: /models/{model}:generateContent
            google_model = request_body.get("model", channel.model)
            # 处理模型名称
            if google_model.startswith('models/'):
                google_model = google_model[7:]
            if ':' in google_model:
                google_model = google_model.split(':')[0]
            
            url = f"{channel.api_base.rstrip('/')}/models/{google_model}:generateContent?key={channel.api_key}"
            # Google AI不使用Authorization header，而是用query参数
            headers.pop("Authorization", None)
            
            # 转换OpenAI格式到Google AI格式
            google_contents = []
            for msg in request_body.get("messages", []):
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "system":
                    # Google AI不直接支持system角色，合并到第一条user消息
                    if not system_prompt_content:
                        system_prompt_content = content
                    continue
                # Google AI使用 user/model 角色
                google_role = "user" if role == "user" else "model"
                google_contents.append({
                    "role": google_role,
                    "parts": [{"text": content}]
                })
            
            # 如果有系统提示词，添加到第一条消息前
            if system_prompt_content and google_contents:
                first_content = google_contents[0]
                if first_content["role"] == "user":
                    first_content["parts"][0]["text"] = f"{system_prompt_content}\n\n{first_content['parts'][0]['text']}"
            
            # 构建Google AI请求体（只包含Google支持的参数）
            generation_config = {}
            if request.temperature is not None:
                generation_config["temperature"] = request.temperature
            if request.max_tokens:
                generation_config["maxOutputTokens"] = request.max_tokens
            if request.top_p is not None:
                generation_config["topP"] = request.top_p
            # Google支持stopSequences
            if request.stop:
                stop_sequences = [request.stop] if isinstance(request.stop, str) else request.stop
                generation_config["stopSequences"] = stop_sequences
            
            request_body = {
                "contents": google_contents
            }
            if generation_config:
                request_body["generationConfig"] = generation_config
            # 注意：Google AI不支持以下OpenAI参数：
            # - n, presence_penalty, frequency_penalty, logit_bias, user
            # - response_format, seed, tools, tool_choice, logprobs, top_logprobs
                    
        else:
            # OpenAI兼容格式（openai, deepseek, qwen, custom等）
            url = f"{channel.api_base.rstrip('/')}/chat/completions"
            headers["Authorization"] = f"Bearer {channel.api_key}"
            
            # 插入系统提示词
            if system_prompt_content:
                if request_body["messages"] and request_body["messages"][0].get("role") != "system":
                    request_body["messages"] = [{"role": "system", "content": system_prompt_content}] + request_body["messages"]
                elif not request_body["messages"]:
                    request_body["messages"] = [{"role": "system", "content": system_prompt_content}]
            
            # 根据具体供应商过滤不支持的参数
            # DeepSeek: 不支持 logit_bias, logprobs, top_logprobs
            # 通义千问: 不支持 logit_bias, logprobs, top_logprobs, n>1
            # 自定义: 保守处理，移除可能不支持的参数
            unsupported_params = []
            
            if channel.channel_type == "deepseek":
                # DeepSeek不支持的参数
                unsupported_params = ["logit_bias", "logprobs", "top_logprobs", "response_format"]
            elif channel.channel_type == "qwen":
                # 通义千问不支持的参数
                unsupported_params = ["logit_bias", "logprobs", "top_logprobs"]
                # 通义千问n参数限制为1
                if request_body.get("n", 1) > 1:
                    request_body["n"] = 1
            elif channel.channel_type == "custom":
                # 自定义渠道：保守移除可能不支持的高级参数
                unsupported_params = ["logit_bias", "logprobs", "top_logprobs", "response_format", "seed"]
            # OpenAI原生支持所有参数，不需要过滤
            
            # 移除不支持的参数
            for param in unsupported_params:
                request_body.pop(param, None)
            
            # 移除值为None或默认值的参数，减少请求体大小
            params_to_clean = ["deployment_id", "user"]
            for param in params_to_clean:
                if param in request_body and request_body[param] is None:
                    del request_body[param]
        
        # 获取HTTP客户端
        client = get_http_client()
        
        # 记录请求信息
        logger.info(f"转发请求到渠道 {channel.name}: URL={url}, model={request_body.get('model')}")
        
        # 转发请求
        if request.stream:
            # 流式响应
            return await _handle_streaming_request(
                channel=channel,
                request_id=request_id,
                url=url,
                headers=headers,
                request_body=request_body,
                db_manager=db_manager,
                background_tasks=background_tasks
            )
        else:
            # 非流式响应
            response = await client.post(
                url=url,
                headers=headers,
                json=request_body
            )
            
            # 计算响应时间
            response_time = time.time() - start_time
            
            # 处理响应
            if response.status_code == 200:
                # 成功
                response_data = response.json()
                
                # 根据渠道类型转换响应格式为OpenAI格式
                if channel.channel_type == "claude":
                    response_data = _convert_claude_response_to_openai(response_data, request_body.get("model"))
                elif channel.channel_type == "google":
                    response_data = _convert_google_response_to_openai(response_data, channel.model)
                
                # 更新负载均衡器指标
                channel.metrics.update_success(response_time)
                
                        # 后台任务：记录日志和更新数据库指标
                background_tasks.add_task(
                    log_request_async,
                    db_manager, request_id, channel.id, request_body, response_data,
                    None, response_time, response.status_code
                )
                background_tasks.add_task(
                    update_channel_metrics_async,
                    db_manager, channel.id, response_time, True
                )
                
                return response_data
            else:
                # 请求失败
                error_data = response.text
                
                # 更新负载均衡器指标
                channel.metrics.update_failure()
                
                # 后台任务：记录日志和更新数据库指标
                background_tasks.add_task(
                    log_request_async,
                    db_manager, request_id, channel.id, request_body, None,
                    error_data, response_time, response.status_code
                )
                background_tasks.add_task(
                    update_channel_metrics_async,
                    db_manager, channel.id, response_time, False, error_data
                )
                
                raise HTTPException(
                    status_code=response.status_code,
                    detail=error_data
                )
    
    except httpx.RequestError as e:
        # 网络错误 - 提供更详细的错误信息
        response_time = time.time() - start_time
        
        # 构建详细的错误信息
        error_type = type(e).__name__
        error_msg = str(e) if str(e) else f"{error_type}: 连接到 {url} 失败"
        
        # 添加更多上下文信息
        if hasattr(e, 'request'):
            error_msg = f"{error_msg} (URL: {e.request.url})"
        
        logger.error(f"网络请求错误: {error_type} - {error_msg}")
        
        # 更新负载均衡器指标
        channel.metrics.update_failure()
        
        # 后台任务：记录日志和更新数据库指标
        background_tasks.add_task(
            log_request_async,
            db_manager, request_id, channel.id, request.dict(), None,
            f"网络错误: {error_msg}", response_time, 503
        )
        background_tasks.add_task(
            update_channel_metrics_async,
            db_manager, channel.id, response_time, False, error_msg
        )
        
        raise HTTPException(
            status_code=503,
            detail=error_response(
                code=503,
                message=f"请求渠道失败: {error_msg}"
            )
        )
    
    except Exception as e:
        # 其他错误
        response_time = time.time() - start_time
        
        # 更新负载均衡器指标
        channel.metrics.update_failure()
        
        # 后台任务：记录日志和更新数据库指标
        background_tasks.add_task(
            log_request_async,
            db_manager, request_id, channel.id, request.dict(), None,
            f"内部错误: {str(e)}", response_time, 500
        )
        background_tasks.add_task(
            update_channel_metrics_async,
            db_manager, channel.id, response_time, False, str(e)
        )
        
        raise HTTPException(
            status_code=500,
            detail=error_response(
                code=500,
                message=f"内部服务器错误: {str(e)}"
            )
        )


async def _handle_streaming_request(
    channel,
    request_id: str,
    url: str,
    headers: Dict[str, str],
    request_body: Dict[str, Any],
    db_manager: DatabaseManager,
    background_tasks: BackgroundTasks
) -> StreamingResponse:
    """处理流式请求"""
    start_time = time.time()
    
    async def generate():
        try:
            client = get_http_client()
            
            async with client.stream(
                "POST",
                url=url,
                headers=headers,
                json=request_body
            ) as response:
                if response.status_code != 200:
                    # 流式请求失败
                    error_text = await response.aread()
                    error_data = error_text.decode('utf-8')
                    
                    # 更新负载均衡器指标
                    channel.metrics.update_failure()
                    
                    # 记录日志
                    background_tasks.add_task(
                        log_request_async,
                        db_manager, request_id, channel.id, request_body, None,
                        error_data, 0.0, response.status_code
                    )
                    background_tasks.add_task(
                        update_channel_metrics_async,
                        db_manager, channel.id, 0.0, False, error_data
                    )
                    
                    # 返回错误
                    yield f"data: {json.dumps({'error': error_data})}\n\n"
                    return
                
                # 更新负载均衡器指标
                response_time = time.time() - start_time
                channel.metrics.update_success(response_time)
                
                # 记录日志（流式请求只记录基本信息）
                background_tasks.add_task(
                    log_request_async,
                    db_manager, request_id, channel.id, request_body,
                    {"stream": True}, None, response_time, 200
                )
                background_tasks.add_task(
                    update_channel_metrics_async,
                    db_manager, channel.id, response_time, True
                )
                
                # 转发流式响应
                async for chunk in response.aiter_bytes():
                    yield chunk
                    
        except Exception as e:
            # 流式处理中的错误
            error_data = f"流式处理错误: {str(e)}"
            
            # 更新负载均衡器指标
            channel.metrics.update_failure()
            
            # 记录日志
            background_tasks.add_task(
                log_request_async,
                db_manager, request_id, channel.id, request_body,
                None, error_data, 0.0, 500
            )
            background_tasks.add_task(
                update_channel_metrics_async,
                db_manager, channel.id, 0.0, False, error_data
            )
            
            # 返回错误
            yield f"data: {json.dumps({'error': error_data})}\n\n"
    
    # 设置流式响应头
    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "*",
    }
    
    return StreamingResponse(
        generate(),
        headers=headers,
        media_type="text/event-stream"
    )


@router.get("/channels/status")
async def get_channels_status(
    request: Request,
    db_manager: DatabaseManager = Depends(get_db_manager_dep)
):
    """获取所有渠道状态"""
    # 直接使用全局函数获取负载均衡器
    load_balancer = get_load_balancer()
    logger.info(f"渠道状态API - 获取的负载均衡器，渠道数: {len(load_balancer.channels)}")
    
    # 如果负载均衡器为空，尝试从应用状态获取
    if len(load_balancer.channels) == 0:
        try:
            app_balancer = request.app.state.load_balancer
            if app_balancer and len(app_balancer.channels) > 0:
                # 将应用状态中的渠道复制到全局负载均衡器
                for channel_id, channel in app_balancer.channels.items():
                    load_balancer.add_channel(channel)
                logger.info(f"渠道状态API - 从应用状态复制了 {len(app_balancer.channels)} 个渠道到全局负载均衡器")
        except AttributeError:
            logger.warning("渠道状态API - 无法从应用状态获取负载均衡器")
    
    # 获取数据库中的渠道信息
    with db_manager.get_session() as db:
        db_channels = get_channels(db=db)
    
    # 获取负载均衡器中的渠道指标
    lb_metrics = load_balancer.get_metrics()
    
    # 合并数据
    channels_status = []
    for db_channel in db_channels:
        channel_id = db_channel.id
        metrics = lb_metrics["channel_metrics"].get(channel_id, {})
        
        channels_status.append({
            "id": db_channel.id,
            "name": db_channel.name,
            "api_base": db_channel.base_url,  # 修复属性名: 使用base_url而不是api_base
            "model": db_channel.models,        # 修复属性名: 使用models而不是model
            "max_qps": 10,                   # 默认QPS限制，因为Schema中没有这个字段
            "timeout": 30,                   # 默认超时，因为Schema中没有这个字段
            "weight": 1,                     # 默认权重，因为Schema中没有这个字段,
            "enabled": db_channel.status,     # 修复属性名: 使用status而不是enabled
            "metrics": {
                "total_requests": metrics.get("total_requests", 0),
                "success_rate": metrics.get("success_rate", 0.0),
                "avg_response_time": metrics.get("avg_response_time", 0.0),
                "last_response_time": metrics.get("last_response_time", 0.0),
                "is_healthy": metrics.get("is_healthy", True),
                "consecutive_failures": metrics.get("consecutive_failures", 0),
                "error_rate": metrics.get("error_rate", 0.0)
            }
        })
    
    return success_response(
        data={
            "load_balancer": {
                "strategy": lb_metrics["strategy"],
                "total_channels": lb_metrics["total_channels"],
                "healthy_channels": lb_metrics["healthy_channels"],
                "unhealthy_channels": lb_metrics["unhealthy_channels"]
            },
            "channels": channels_status
        },
        message="获取渠道状态成功"
    )


@router.post("/load-balancer/strategy")
async def update_load_balancer_strategy(
    strategy: str,
    request: Request,
    db_manager: DatabaseManager = Depends(get_db_manager_dep)
):
    """更新负载均衡策略"""
    from ....core.load_balancer import set_load_balancer_strategy
    
    try:
        # 验证策略
        new_strategy = LoadBalanceStrategy(strategy)
        
        # 获取负载均衡器
        try:
            load_balancer = request.app.state.load_balancer
        except AttributeError:
            from ....core.load_balancer import get_load_balancer
            load_balancer = get_load_balancer()
            
        # 更新策略
        set_load_balancer_strategy(new_strategy)
        
        return success_response(
            data={"strategy": new_strategy.value},
            message="负载均衡策略更新成功"
        )
    
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=error_response(
                code=400,
                message=f"无效的负载均衡策略: {strategy}"
            )
        )


@router.get("/load-balancer/metrics")
async def get_load_balancer_metrics(
    db_manager: DatabaseManager = Depends(get_db_manager_dep)
):
    """获取负载均衡器详细指标"""
    load_balancer = get_load_balancer()
    metrics = load_balancer.get_metrics()
    
    return success_response(
        data=metrics,
        message="获取负载均衡器指标成功"
    )


@router.post("/channels/{channel_id}/health-check")
async def perform_channel_health_check(
    channel_id: str,
    request: Request,
    db_manager: DatabaseManager = Depends(get_db_manager_dep)
):
    """手动执行渠道健康检查"""
    # 获取渠道配置
    with db_manager.get_session() as db:
        db_channel = get_channel(db=db, channel_id=channel_id)
    if not db_channel:
        raise HTTPException(
            status_code=404,
            detail=error_response(
                code=404,
                message=f"渠道不存在: {channel_id}"
            )
        )
    
    # 创建渠道对象
    channel = create_channel_from_config({
        "id": db_channel.id,
        "name": db_channel.name,
        "api_base": db_channel.api_base,
        "api_key": db_channel.api_key,
        "model": db_channel.model,
        "max_qps": db_channel.max_qps,
        "timeout": db_channel.timeout,
        "weight": db_channel.weight
    })
    
    # 执行健康检查
    try:
        client = get_http_client()
        
        # 构建健康检查请求
        test_request = {
            "model": channel.model or "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": "健康检查"}],
            "max_tokens": 5
        }
        
        headers = {
            "Authorization": f"Bearer {channel.api_key}",
            "Content-Type": "application/json"
        }
        
        url = f"{channel.api_base.rstrip('/')}/chat/completions"
        
        start_time = time.time()
        response = await client.post(
            url=url,
            headers=headers,
            json=test_request,
            timeout=10  # 健康检查使用较短超时
        )
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            # 健康检查成功
            channel.metrics.update_success(response_time)
            is_healthy = True
            message = "健康检查通过"
        else:
            # 健康检查失败
            channel.metrics.update_failure()
            is_healthy = False
            message = f"健康检查失败: {response.text}"
    
    except Exception as e:
        # 健康检查异常
        channel.metrics.update_failure()
        is_healthy = False
        message = f"健康检查异常: {str(e)}"
        response_time = 0.0
    
    # 更新数据库中的渠道状态
    await update_channel_metrics_async(
        db_manager=db_manager,
        channel_id=channel_id,
        response_time=response_time,
        success=is_healthy
    )
    
    return success_response(
        data={
            "channel_id": channel_id,
            "is_healthy": is_healthy,
            "response_time": response_time,
            "message": message
        },
        message="健康检查完成"
    )