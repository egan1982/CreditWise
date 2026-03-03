"""
渠道客户端工厂 - 根据LLM Manager渠道配置创建对应的LLM客户端

功能：
- 集成llm_manager_integrated的负载均衡器
- 支持多提供商（OpenAI/Claude/Google/DeepSeek等）
- 统一响应格式转换
- 支持流式和非流式响应
- 根据模型能力自动处理深度思考和联网搜索
"""

import logging
import time
from typing import Optional, Dict, Any, Tuple, AsyncGenerator
from dataclasses import dataclass

from openai import AsyncOpenAI
import httpx

from API.model_capabilities import (
    get_model_capabilities,
    is_reasoning_model,
    get_effective_thinking_config,
    get_effective_web_search_config,
    get_effective_stream_config,
)

logger = logging.getLogger(__name__)


@dataclass
class ChannelInfo:
    """渠道信息（包含模型配置参数）
    
    所有模型参数从LLM Manager配置获取，作为唯一配置来源。
    """
    channel_id: str
    channel_name: str
    provider: str
    model: str
    base_url: str
    api_key: str
    timeout: int = 30
    
    # 渠道级别配置
    stream_output: bool = True  # 是否启用流式输出，默认启用
    
    # 基础模型配置参数（从LLM Manager获取）
    max_tokens: Optional[int] = None  # 用户配置的max_tokens
    max_tokens_limit: Optional[int] = None  # 模型官方支持的最大token数
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    system_prompt: Optional[str] = None
    
    # 联网搜索配置
    enable_web_search: bool = False  # 是否启用联网搜索
    
    # 深度思考/推理配置
    enable_deep_thinking: bool = False  # 是否启用深度思考
    thinking_budget: Optional[int] = None  # 思考预算（token数）
    include_thoughts: bool = False  # 是否返回思考摘要


class ChannelClientFactory:
    """
    渠道客户端工厂
    
    根据LLM Manager配置的渠道创建对应的LLM客户端
    支持通过负载均衡器选择渠道
    """
    
    def __init__(self):
        self._load_balancer = None
        self._db_manager = None
        self._initialized = False
        self._http_client: Optional[httpx.AsyncClient] = None
    
    def initialize(self):
        """延迟初始化，在首次使用时调用"""
        if self._initialized:
            return
        
        try:
            from llm_manager_integrated.core.load_balancer import get_load_balancer
            from llm_manager_integrated.models.database import get_db_manager
            
            self._load_balancer = get_load_balancer()
            self._db_manager = get_db_manager()
            self._initialized = True
            logger.info("ChannelClientFactory 初始化成功")
        except Exception as e:
            logger.error(f"ChannelClientFactory 初始化失败: {e}")
            raise
    
    def _ensure_initialized(self):
        """确保已初始化"""
        if not self._initialized:
            self.initialize()
    
    def _get_http_client(self) -> httpx.AsyncClient:
        """获取HTTP客户端"""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(60.0),
                limits=httpx.Limits(max_connections=100)
            )
        return self._http_client
    
    async def _load_channels_if_needed(self):
        """如果负载均衡器为空，从数据库加载渠道"""
        if len(self._load_balancer.channels) > 0:
            return
        
        logger.info("负载均衡器为空，从数据库加载渠道")
        try:
            from llm_manager_integrated.core.crud import get_channels
            from llm_manager_integrated.core.load_balancer import create_channel_from_config
            
            with self._db_manager.get_session() as db:
                channels = get_channels(db=db)
                
                for channel in channels:
                    if channel.status:  # 只加载启用的渠道
                        lb_channel = create_channel_from_config({
                            'id': str(channel.id),
                            'name': channel.name,
                            'api_base': channel.base_url,
                            'api_key': channel.api_key,
                            'model': channel.models,
                            'type': channel.type,
                            'weight': 1,
                            'max_qps': 10,
                            'timeout': 30
                        })
                        self._load_balancer.add_channel(lb_channel)
                        logger.debug(f"加载渠道: {channel.name} ({channel.id})")
                
                logger.info(f"从数据库加载了 {len([c for c in channels if c.status])} 个渠道")
        except Exception as e:
            logger.error(f"加载渠道失败: {e}")
            raise
    
    async def get_channel_for_model(self, model: str) -> Optional[ChannelInfo]:
        """
        根据model标识获取渠道信息
        
        Args:
            model: 模型标识，支持以下格式：
                - "config_123": 使用配置ID 123关联的渠道
                - "channel_456": 直接使用渠道ID 456
                - "gpt-4": 使用负载均衡器选择支持该模型的渠道
        
        Returns:
            ChannelInfo 或 None
        """
        self._ensure_initialized()
        await self._load_channels_if_needed()
        
        # 解析model标识
        if model.startswith("config_"):
            # 通过配置ID获取渠道
            config_id = int(model.replace("config_", ""))
            return await self._get_channel_by_config_id(config_id)
        
        elif model.startswith("channel_"):
            # 直接使用渠道ID
            channel_id = model.replace("channel_", "")
            return await self._get_channel_by_id(channel_id)
        
        else:
            # 使用负载均衡器选择支持该模型的渠道
            return await self._select_channel_for_model(model)
    
    async def _get_channel_by_config_id(self, config_id: int) -> Optional[ChannelInfo]:
        """通过配置ID获取渠道（包含模型配置参数）"""
        try:
            from llm_manager_integrated.core.crud import get_channel, get_model_config_by_channel
            
            with self._db_manager.get_session() as db:
                # 获取渠道信息
                channel = get_channel(db, config_id)
                if not channel:
                    logger.warning(f"未找到配置ID {config_id} 对应的渠道")
                    return None
                
                if not channel.status:
                    logger.warning(f"渠道 {channel.name} 未启用")
                    return None
                
                # 获取模型配置（包含max_tokens等参数）
                model_config = get_model_config_by_channel(db, config_id)
                
                # 确定使用的模型名
                model_name = channel.models.split(',')[0].strip() if channel.models else ""
                if model_config and model_config.model_name:
                    model_name = model_config.model_name
                
                # 构建渠道信息，包含模型配置参数
                # 渠道级别配置：stream_output（默认True）
                stream_output = getattr(channel, 'stream_output', True)
                if stream_output is None:
                    stream_output = True
                
                channel_info = ChannelInfo(
                    channel_id=str(channel.id),
                    channel_name=channel.name,
                    provider=channel.type,
                    model=model_name,
                    base_url=channel.base_url,
                    api_key=channel.api_key,
                    timeout=30,
                    stream_output=stream_output,
                )
                
                # 如果有模型配置，填充参数
                if model_config:
                    # 基础参数
                    channel_info.max_tokens = model_config.max_tokens
                    channel_info.max_tokens_limit = model_config.max_tokens_limit
                    channel_info.temperature = model_config.temperature
                    channel_info.top_p = model_config.top_p
                    channel_info.system_prompt = model_config.system_prompt
                    
                    # 频率和存在惩罚
                    channel_info.frequency_penalty = getattr(model_config, 'frequency_penalty', None)
                    channel_info.presence_penalty = getattr(model_config, 'presence_penalty', None)
                    
                    # 联网搜索配置
                    channel_info.enable_web_search = getattr(model_config, 'enable_web_search', False) or False
                    
                    # 深度思考配置
                    channel_info.enable_deep_thinking = getattr(model_config, 'enable_deep_thinking', False) or False
                    channel_info.thinking_budget = getattr(model_config, 'thinking_budget', None)
                    channel_info.include_thoughts = getattr(model_config, 'include_thoughts', False) or False
                    
                    logger.debug(
                        f"渠道 {channel.name} 模型配置: "
                        f"max_tokens={model_config.max_tokens}, limit={model_config.max_tokens_limit}, "
                        f"web_search={channel_info.enable_web_search}, "
                        f"deep_thinking={channel_info.enable_deep_thinking}, "
                        f"stream_output={channel_info.stream_output}"
                    )
                
                return channel_info
        except Exception as e:
            logger.error(f"获取配置 {config_id} 的渠道失败: {e}")
            return None
    
    async def _get_channel_by_id(self, channel_id: str) -> Optional[ChannelInfo]:
        """通过渠道ID获取渠道"""
        if channel_id in self._load_balancer.channels:
            channel = self._load_balancer.channels[channel_id]
            return ChannelInfo(
                channel_id=channel.id,
                channel_name=channel.name,
                provider=channel.channel_type,
                model=channel.model,
                base_url=channel.api_base,
                api_key=channel.api_key,
                timeout=channel.timeout
            )
        return None
    
    async def _select_channel_for_model(self, model: str) -> Optional[ChannelInfo]:
        """使用负载均衡器选择支持指定模型的渠道"""
        channel = await self._load_balancer.select_channel(model=model)
        if not channel:
            logger.warning(f"没有找到支持模型 {model} 的渠道")
            return None
        
        return ChannelInfo(
            channel_id=channel.id,
            channel_name=channel.name,
            provider=channel.channel_type,
            model=channel.model,
            base_url=channel.api_base,
            api_key=channel.api_key,
            timeout=channel.timeout
        )
    
    def create_openai_client(self, channel_info: ChannelInfo) -> AsyncOpenAI:
        """
        创建OpenAI兼容客户端
        
        适用于：OpenAI, DeepSeek, 以及其他OpenAI兼容的API
        """
        import httpx
        
        # 创建自定义HTTP客户端，设置更长的超时
        # 连接超时10秒，读取/写入超时120秒（对于大模型响应需要更长时间）
        http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(120.0, connect=10.0),
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
        )
        
        return AsyncOpenAI(
            api_key=channel_info.api_key,
            base_url=channel_info.base_url,
            http_client=http_client,
            max_retries=2  # 减少重试次数，避免长时间等待
        )
    
    async def chat_completion(
        self,
        channel_info: ChannelInfo,
        messages: list,
        temperature: float,
        max_tokens: int,
        stream: bool = False,
        **kwargs
    ):
        """
        统一的聊天完成接口
        
        根据渠道类型自动选择合适的API调用方式
        
        注意：temperature和max_tokens应从channel_info获取，调用方负责传入正确的值
        """
        provider = channel_info.provider.lower()
        model_name = channel_info.model
        
        # 检查模型是否支持流式输出，如果不支持则强制关闭
        effective_stream = get_effective_stream_config(model_name, stream)
        if stream and not effective_stream:
            logger.info(f"模型 {model_name} 不支持流式输出，已自动切换为非流式模式")
        
        if provider in ["openai", "deepseek", "openai_compatible", "azure"]:
            return await self._openai_chat_completion(
                channel_info, messages, temperature, max_tokens, effective_stream, **kwargs
            )
        elif provider == "claude":
            return await self._claude_chat_completion(
                channel_info, messages, temperature, max_tokens, effective_stream, **kwargs
            )
        elif provider == "google":
            return await self._google_chat_completion(
                channel_info, messages, temperature, max_tokens, effective_stream, **kwargs
            )
        else:
            # 默认使用OpenAI兼容接口
            logger.info(f"未知提供商 {provider}，使用OpenAI兼容接口")
            return await self._openai_chat_completion(
                channel_info, messages, temperature, max_tokens, effective_stream, **kwargs
            )
    
    async def _openai_chat_completion(
        self,
        channel_info: ChannelInfo,
        messages: list,
        temperature: float,
        max_tokens: int,
        stream: bool,
        **kwargs
    ):
        """OpenAI兼容API调用
        
        支持：
        - DeepSeek联网搜索
        - DeepSeek-Reasoner推理模型（强制深度思考）
        - OpenAI o系列推理模型
        """
        client = self.create_openai_client(channel_info)
        model_name = channel_info.model
        provider = channel_info.provider.lower()
        
        # 获取模型能力配置
        capability = get_model_capabilities(model_name)
        
        # 构建基础请求参数
        request_params = {
            "model": model_name,
            "messages": messages,
            "stream": stream,
        }
        
        # ============================================================
        # 处理推理模型（deepseek-reasoner, o1系列等）
        # 推理模型特点：深度思考内置，不需要额外参数，且某些参数不支持
        # ============================================================
        if capability.is_reasoning_model:
            logger.debug(f"检测到推理模型 {model_name}，使用推理模式")
            
            # 推理模型通常不支持temperature参数，或只支持固定值
            # DeepSeek-Reasoner: 不支持temperature
            # OpenAI o1: 只支持temperature=1
            if provider == "deepseek":
                # DeepSeek推理模型不传temperature
                pass
            elif provider == "openai":
                # OpenAI o系列只支持temperature=1
                request_params["temperature"] = 1
            
            # 推理模型的max_tokens处理
            if max_tokens:
                request_params["max_tokens"] = max_tokens
        else:
            # 非推理模型：正常设置temperature和max_tokens
            request_params["temperature"] = temperature
            request_params["max_tokens"] = max_tokens
        
        # ============================================================
        # 联网搜索支持（DeepSeek）
        # ============================================================
        if provider == "deepseek":
            # 获取有效的联网搜索配置
            effective_web_search = get_effective_web_search_config(
                model_name, 
                channel_info.enable_web_search
            )
            if effective_web_search:
                # DeepSeek使用tools参数启用联网搜索
                request_params["tools"] = [{"type": "web_search"}]
                logger.debug(f"DeepSeek渠道 {channel_info.channel_name} 启用联网搜索")
        
        # ============================================================
        # 其他可选参数
        # ============================================================
        # 注意：推理模型可能不支持这些参数
        if not capability.is_reasoning_model:
            if channel_info.frequency_penalty is not None:
                request_params["frequency_penalty"] = channel_info.frequency_penalty
            if channel_info.presence_penalty is not None:
                request_params["presence_penalty"] = channel_info.presence_penalty
            if channel_info.top_p is not None:
                request_params["top_p"] = channel_info.top_p
        
        # 合并额外参数
        request_params.update(kwargs)
        
        response = await client.chat.completions.create(**request_params)
        
        return response
    
    async def _claude_chat_completion(
        self,
        channel_info: ChannelInfo,
        messages: list,
        temperature: float,
        max_tokens: int,
        stream: bool,
        **kwargs
    ):
        """Claude API调用
        
        支持Extended Thinking（深度思考）功能
        https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking
        """
        http_client = self._get_http_client()
        model_name = channel_info.model
        
        # 获取有效的深度思考配置
        effective_thinking, effective_budget = get_effective_thinking_config(
            model_name,
            channel_info.enable_deep_thinking,
            channel_info.thinking_budget
        )
        
        # 转换消息格式
        anthropic_messages = []
        system_content = None
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                system_content = content
                continue
            
            if role in ["user", "assistant"]:
                anthropic_messages.append({"role": role, "content": content})
        
        # 构建请求
        url = f"{channel_info.base_url.rstrip('/')}/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": channel_info.api_key,
            "anthropic-version": "2023-06-01"
        }
        
        request_body = {
            "model": model_name,
            "messages": anthropic_messages,
            "max_tokens": max_tokens,
            "stream": stream
        }
        
        # Claude Extended Thinking（深度思考）支持
        # 注意：启用extended thinking时，temperature必须为1，不能设置top_p/top_k
        if effective_thinking:
            thinking_config = {
                "type": "enabled",
                "budget_tokens": effective_budget or 10000
            }
            request_body["thinking"] = thinking_config
            # Extended thinking要求temperature=1
            request_body["temperature"] = 1
            logger.debug(f"Claude渠道 {channel_info.channel_name} 启用深度思考，budget_tokens={effective_budget}")
        else:
            request_body["temperature"] = temperature
        
        if system_content:
            request_body["system"] = system_content
        
        if stream:
            # 流式响应
            async def stream_generator():
                async with http_client.stream("POST", url, headers=headers, json=request_body) as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            yield line
            return stream_generator()
        else:
            # 非流式响应
            response = await http_client.post(url, headers=headers, json=request_body)
            response.raise_for_status()
            return self._convert_claude_to_openai(
                response.json(), 
                channel_info.model,
                include_thoughts=channel_info.include_thoughts
            )
    
    async def _google_chat_completion(
        self,
        channel_info: ChannelInfo,
        messages: list,
        temperature: float,
        max_tokens: int,
        stream: bool,
        **kwargs
    ):
        """Google AI API调用
        
        支持联网搜索（Google Search Grounding）和深度思考功能
        https://ai.google.dev/gemini-api/docs/grounding
        """
        http_client = self._get_http_client()
        
        # 转换消息格式
        google_contents = []
        system_content = None
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                system_content = content
                continue
            
            google_role = "user" if role == "user" else "model"
            google_contents.append({
                "role": google_role,
                "parts": [{"text": content}]
            })
        
        # 如果有系统提示词，合并到第一条消息
        if system_content and google_contents:
            first_content = google_contents[0]
            if first_content["role"] == "user":
                first_content["parts"][0]["text"] = f"{system_content}\n\n{first_content['parts'][0]['text']}"
        
        # 构建请求
        model_name = channel_info.model
        if model_name.startswith('models/'):
            model_name = model_name[7:]
        
        url = f"{channel_info.base_url.rstrip('/')}/models/{model_name}:generateContent?key={channel_info.api_key}"
        
        # 获取有效的深度思考和联网搜索配置
        effective_thinking, effective_budget = get_effective_thinking_config(
            model_name,
            channel_info.enable_deep_thinking,
            channel_info.thinking_budget
        )
        effective_web_search = get_effective_web_search_config(
            model_name,
            channel_info.enable_web_search
        )
        
        # 生成配置
        generation_config = {
            "temperature": temperature,
            "maxOutputTokens": max_tokens
        }
        
        # Google深度思考支持（Gemini 2.0+ thinking mode）
        if effective_thinking and effective_budget:
            generation_config["thinkingConfig"] = {
                "thinkingBudget": effective_budget
            }
            logger.debug(f"Google渠道 {channel_info.channel_name} 启用深度思考，thinkingBudget={effective_budget}")
        
        request_body = {
            "contents": google_contents,
            "generationConfig": generation_config
        }
        
        # Google联网搜索支持（Google Search Grounding）
        if effective_web_search:
            request_body["tools"] = [{
                "googleSearch": {}
            }]
            logger.debug(f"Google渠道 {channel_info.channel_name} 启用联网搜索（Google Search Grounding）")
        
        if stream:
            url = url.replace(":generateContent", ":streamGenerateContent")
            async def stream_generator():
                async with http_client.stream("POST", url, json=request_body) as response:
                    async for line in response.aiter_lines():
                        yield line
            return stream_generator()
        else:
            response = await http_client.post(url, json=request_body)
            response.raise_for_status()
            google_response = response.json()
            # 记录 Google 响应的 finishReason，帮助诊断截断问题
            candidates = google_response.get("candidates", [])
            if candidates:
                finish_reason = candidates[0].get("finishReason", "UNKNOWN")
                if finish_reason != "STOP":
                    logger.warning(f"Google API finishReason={finish_reason}，响应可能不完整")
            return self._convert_google_to_openai(google_response, channel_info.model)
    
    def _convert_claude_to_openai(self, claude_response: dict, model: str, include_thoughts: bool = False) -> dict:
        """将Claude响应转换为OpenAI格式
        
        Args:
            claude_response: Claude API原始响应
            model: 模型名称
            include_thoughts: 是否在响应中包含思考过程（Extended Thinking）
        """
        import uuid
        
        content = ""
        thinking_content = ""
        
        if claude_response.get("content"):
            for block in claude_response["content"]:
                if block.get("type") == "thinking":
                    # Extended Thinking的思考过程
                    thinking_content += block.get("thinking", "")
                elif block.get("type") == "text":
                    content += block.get("text", "")
        
        # 如果启用了include_thoughts且有思考内容，将其添加到响应中
        if include_thoughts and thinking_content:
            content = f"<thinking>\n{thinking_content}\n</thinking>\n\n{content}"
        
        stop_reason_map = {
            "end_turn": "stop",
            "max_tokens": "length",
            "stop_sequence": "stop"
        }
        finish_reason = stop_reason_map.get(claude_response.get("stop_reason"), "stop")
        
        usage = claude_response.get("usage", {})
        return {
            "id": claude_response.get("id", f"chatcmpl-{uuid.uuid4().hex[:8]}"),
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content
                },
                "finish_reason": finish_reason
            }],
            "usage": {
                "prompt_tokens": usage.get("input_tokens", 0),
                "completion_tokens": usage.get("output_tokens", 0),
                "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
            }
        }
    
    def _convert_google_to_openai(self, google_response: dict, model: str) -> dict:
        """将Google AI响应转换为OpenAI格式"""
        import uuid
        
        content = ""
        candidates = google_response.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            for part in parts:
                if "text" in part:
                    content += part["text"]
        
        finish_reason_map = {
            "STOP": "stop",
            "MAX_TOKENS": "length",
            "SAFETY": "content_filter"
        }
        raw_finish_reason = candidates[0].get("finishReason", "STOP") if candidates else "STOP"
        finish_reason = finish_reason_map.get(raw_finish_reason, "stop")
        
        usage = google_response.get("usageMetadata", {})
        return {
            "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content
                },
                "finish_reason": finish_reason
            }],
            "usage": {
                "prompt_tokens": usage.get("promptTokenCount", 0),
                "completion_tokens": usage.get("candidatesTokenCount", 0),
                "total_tokens": usage.get("totalTokenCount", 0)
            }
        }
    
    def update_channel_metrics(self, channel_id: str, success: bool, response_time: float):
        """更新渠道指标"""
        self._ensure_initialized()
        
        if channel_id in self._load_balancer.channels:
            channel = self._load_balancer.channels[channel_id]
            if success:
                channel.metrics.update_success(response_time)
            else:
                channel.metrics.update_failure()
    
    async def close(self):
        """关闭资源"""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


# 全局单例
_channel_factory: Optional[ChannelClientFactory] = None


def get_channel_factory() -> ChannelClientFactory:
    """获取全局渠道客户端工厂实例"""
    global _channel_factory
    if _channel_factory is None:
        _channel_factory = ChannelClientFactory()
    return _channel_factory
