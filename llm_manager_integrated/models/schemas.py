from pydantic import BaseModel, Field
from typing import Optional, Union, List, Literal
from datetime import datetime

class ChannelBase(BaseModel):
    name: str
    type: str
    models: str # 逗号分隔的模型列表, e.g., "gpt-4,gpt-3.5-turbo"

class ChannelCreate(ChannelBase):
    base_url: str
    api_key: str # 接收原始 API Key
    stream_output: bool = True  # 是否启用流式输出，默认启用

class ChannelUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    models: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None # 允许更新密钥
    status: Optional[bool] = None
    stream_output: Optional[bool] = None  # 是否启用流式输出

class ModelTestRequest(BaseModel):
    base_url: str
    api_key: str
    type: str

class Channel(ChannelBase):
    id: int
    base_url: str
    api_key: Optional[str] = None  # 返回解密后的 API Key
    status: bool
    stream_output: bool = True  # 是否启用流式输出
    model_type: Optional[str] = None  # 模型类型（如：text, vision, audio等）
    supports_web_search: Optional[bool] = None  # 是否支持联网搜索
    supports_deep_thinking: Optional[bool] = None  # 是否支持深度推理

    class Config:
        from_attributes = True

class ModelConfigBase(BaseModel):
    model_config = {
        'protected_namespaces': (),
    }

    model_name: Optional[str] = None  # 可选，从渠道配置获取
    system_prompt: Optional[str] = None
    temperature: float = 0.7
    top_p: float = 1.0
    max_tokens: int = 2000
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    description: Optional[str] = None
    model_info: Optional[str] = None  # JSON 格式的模型官方信息
    max_tokens_limit: Optional[int] = None  # 模型官方支持的最大 token 数
    
    # 联网搜索配置
    enable_web_search: bool = False
    
    # 深度思考配置
    enable_deep_thinking: bool = False
    thinking_budget: Optional[int] = None
    include_thoughts: bool = False

class ModelConfigCreate(BaseModel):
    """创建模型配置 - 所有字段可选，使用默认值"""
    model_config = {
        'protected_namespaces': (),
    }
    
    channel_id: Optional[int] = None  # 由路由参数提供
    model_name: Optional[str] = None
    system_prompt: Optional[str] = None
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 1.0
    max_tokens: Optional[int] = 2000
    frequency_penalty: Optional[float] = 0.0
    presence_penalty: Optional[float] = 0.0
    description: Optional[str] = None
    model_info: Optional[str] = None
    max_tokens_limit: Optional[int] = None
    enable_web_search: Optional[bool] = False
    enable_deep_thinking: Optional[bool] = False
    thinking_budget: Optional[int] = None
    include_thoughts: Optional[bool] = False

class ModelConfigUpdate(BaseModel):
    system_prompt: Optional[str] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    description: Optional[str] = None
    model_info: Optional[str] = None
    max_tokens_limit: Optional[int] = None
    
    # 联网搜索配置
    enable_web_search: Optional[bool] = None
    
    # 深度思考配置
    enable_deep_thinking: Optional[bool] = None
    thinking_budget: Optional[int] = None
    include_thoughts: Optional[bool] = None

class ModelConfig(ModelConfigBase):
    model_config = {
        'protected_namespaces': (),
        'from_attributes': True,
    }

    id: int
    channel_id: int

# API日志相关Schema
class APILogBase(BaseModel):
    model_name: str
    channel_name: Optional[str] = None
    status: str  # success, error
    status_code: Optional[int] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    request_data: Optional[str] = None
    response_data: Optional[str] = None
    error_message: Optional[str] = None
    response_time: Optional[float] = None
    estimated_cost: Optional[float] = None
    is_test_data: Optional[bool] = False

class APILogCreate(APILogBase):
    pass

class APILog(APILogBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True

# OpenAI API兼容的Schema
class ChatCompletionRequest(BaseModel):
    """OpenAI兼容的聊天完成请求"""
    model: str
    messages: list[dict]
    temperature: Optional[float] = 1.0
    top_p: Optional[float] = 1.0
    n: Optional[int] = 1
    stream: Optional[bool] = False
    stop: Optional[Union[str, list[str]]] = None
    max_tokens: Optional[int] = None
    presence_penalty: Optional[float] = 0.0
    frequency_penalty: Optional[float] = 0.0
    logit_bias: Optional[dict] = None
    user: Optional[str] = None
    response_format: Optional[dict] = None
    seed: Optional[int] = None
    tools: Optional[list[dict]] = None
    tool_choice: Optional[Union[str, dict]] = None
    logprobs: Optional[bool] = False
    top_logprobs: Optional[int] = None
    deployment_id: Optional[str] = None
    # LLM Manager扩展字段：系统提示词
    system_prompt: Optional[str] = None

class ChatCompletionChoice(BaseModel):
    """聊天完成选项"""
    index: int
    message: Optional[dict] = None
    delta: Optional[dict] = None
    finish_reason: Optional[str] = None
    logprobs: Optional[dict] = None

class ChatCompletionUsage(BaseModel):
    """聊天完成使用情况"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class ChatCompletionResponse(BaseModel):
    """OpenAI兼容的聊天完成响应"""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[ChatCompletionChoice]
    usage: Optional[ChatCompletionUsage] = None
    system_fingerprint: Optional[str] = None

class ErrorResponse(BaseModel):
    """错误响应"""
    error: dict
    message: str
    code: int


# OpenAI API兼容的Schema
class ModelObject(BaseModel):
    """OpenAI Model Object"""
    id: str
    object: Literal["model"] = "model"
    created: Optional[int] = None
    owned_by: Optional[str] = None


class ModelsListResponse(BaseModel):
    """OpenAI Models List Response"""
    object: Literal["list"] = "list"
    data: List[ModelObject]
