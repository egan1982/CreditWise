"""
Chat API 错误处理模块

功能：
- 统一的错误响应格式
- 分类错误处理（渠道不可用、提供商错误、速率限制等）
- 错误日志记录
- 自动重试支持（可选）
"""

import logging
from typing import Optional, Dict, Any
from fastapi import HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class ChatAPIError(Exception):
    """Chat API 基础异常"""
    
    def __init__(
        self,
        message: str,
        error_code: str = "CHAT_API_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "details": self.details
            }
        }


class ChannelUnavailableError(ChatAPIError):
    """渠道不可用错误"""
    
    def __init__(
        self, 
        message: str = "没有可用的渠道", 
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="CHANNEL_UNAVAILABLE",
            status_code=503,
            details=details
        )


class ProviderError(ChatAPIError):
    """LLM提供商错误"""
    
    def __init__(
        self, 
        provider: str, 
        message: str, 
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"{provider} API错误: {message}",
            error_code="PROVIDER_ERROR",
            status_code=502,
            details={"provider": provider, **(details or {})}
        )


class RateLimitError(ChatAPIError):
    """速率限制错误"""
    
    def __init__(
        self, 
        retry_after: Optional[int] = None, 
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message="请求过于频繁，请稍后重试",
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            details={"retry_after": retry_after, **(details or {})}
        )


class AuthenticationError(ChatAPIError):
    """认证错误"""
    
    def __init__(
        self, 
        provider: str,
        message: str = "API密钥无效或已过期",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"{provider}: {message}",
            error_code="AUTHENTICATION_ERROR",
            status_code=401,
            details={"provider": provider, **(details or {})}
        )


class ModelNotFoundError(ChatAPIError):
    """模型不存在错误"""
    
    def __init__(
        self, 
        model: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"模型 {model} 不存在或不可用",
            error_code="MODEL_NOT_FOUND",
            status_code=404,
            details={"model": model, **(details or {})}
        )


class InvalidRequestError(ChatAPIError):
    """无效请求错误"""
    
    def __init__(
        self, 
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="INVALID_REQUEST",
            status_code=400,
            details=details
        )


class TimeoutError(ChatAPIError):
    """超时错误"""
    
    def __init__(
        self, 
        timeout: float,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"请求超时（{timeout}秒）",
            error_code="TIMEOUT",
            status_code=504,
            details={"timeout": timeout, **(details or {})}
        )


def create_error_response(error: ChatAPIError) -> JSONResponse:
    """创建标准化的错误响应"""
    return JSONResponse(
        status_code=error.status_code,
        content=error.to_dict()
    )


def classify_provider_error(e: Exception, provider: str) -> ChatAPIError:
    """
    分类提供商错误
    
    根据异常信息判断错误类型并返回对应的ChatAPIError
    
    Args:
        e: 原始异常
        provider: 提供商名称
        
    Returns:
        分类后的ChatAPIError
    """
    error_str = str(e).lower()
    
    # 检测速率限制
    if "rate limit" in error_str or "429" in error_str or "too many requests" in error_str:
        logger.warning(f"{provider} 触发速率限制")
        return RateLimitError(details={"provider": provider, "original_error": str(e)})
    
    # 检测认证错误
    if any(keyword in error_str for keyword in ["unauthorized", "401", "invalid api key", "authentication", "invalid_api_key"]):
        logger.error(f"{provider} 认证失败")
        return AuthenticationError(provider=provider, details={"original_error": str(e)})
    
    # 检测模型不存在
    if any(keyword in error_str for keyword in ["model not found", "404", "does not exist", "invalid model"]):
        logger.error(f"{provider} 模型不存在")
        return ModelNotFoundError(model="unknown", details={"provider": provider, "original_error": str(e)})
    
    # 检测超时
    if any(keyword in error_str for keyword in ["timeout", "timed out", "deadline exceeded"]):
        logger.error(f"{provider} 请求超时")
        return TimeoutError(timeout=30, details={"provider": provider, "original_error": str(e)})
    
    # 检测请求无效
    if any(keyword in error_str for keyword in ["invalid request", "bad request", "400"]):
        logger.error(f"{provider} 请求无效: {e}")
        return InvalidRequestError(message=str(e), details={"provider": provider})
    
    # 其他错误
    logger.error(f"{provider} API调用失败: {e}")
    return ProviderError(provider=provider, message=str(e))


async def handle_provider_error(
    e: Exception, 
    provider: str, 
    channel_info: Optional[Any] = None
) -> None:
    """
    处理提供商错误，更新渠道状态
    
    Args:
        e: 异常对象
        provider: 提供商名称
        channel_info: 渠道信息（可选）
        
    Raises:
        ChatAPIError: 分类后的错误
    """
    # 分类错误
    classified_error = classify_provider_error(e, provider)
    
    # 如果有渠道信息，更新渠道指标
    if channel_info is not None:
        try:
            from API.channel_client import get_channel_factory
            factory = get_channel_factory()
            factory.update_channel_metrics(
                channel_id=channel_info.channel_id,
                success=False,
                response_time=0.0
            )
        except Exception as update_error:
            logger.warning(f"更新渠道指标失败: {update_error}")
    
    raise classified_error


def format_openai_error(error: ChatAPIError) -> Dict[str, Any]:
    """
    将错误格式化为OpenAI兼容格式
    
    OpenAI错误格式：
    {
        "error": {
            "message": "...",
            "type": "...",
            "param": null,
            "code": "..."
        }
    }
    """
    error_type_map = {
        "CHANNEL_UNAVAILABLE": "service_unavailable",
        "PROVIDER_ERROR": "api_error",
        "RATE_LIMIT_EXCEEDED": "rate_limit_error",
        "AUTHENTICATION_ERROR": "authentication_error",
        "MODEL_NOT_FOUND": "invalid_request_error",
        "INVALID_REQUEST": "invalid_request_error",
        "TIMEOUT": "timeout_error",
        "CHAT_API_ERROR": "api_error",
    }
    
    return {
        "error": {
            "message": error.message,
            "type": error_type_map.get(error.error_code, "api_error"),
            "param": None,
            "code": error.error_code.lower(),
        }
    }


# 异常处理装饰器（可选使用）
def handle_chat_api_errors(func):
    """
    装饰器：自动捕获并处理Chat API错误
    
    使用方式：
    @handle_chat_api_errors
    async def my_endpoint():
        ...
    """
    import functools
    
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except ChatAPIError as e:
            return create_error_response(e)
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"未处理的异常: {e}")
            error = ChatAPIError(
                message=f"内部服务器错误: {str(e)}",
                error_code="INTERNAL_ERROR",
                status_code=500
            )
            return create_error_response(error)
    
    return wrapper
