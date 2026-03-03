"""标准化 API 响应格式"""

from typing import Any, Optional, Dict
from pydantic import BaseModel


class APIResponse(BaseModel):
    """标准 API 响应格式
    
    所有 API 端点都应该返回这个格式的响应，确保前端能够统一处理。
    
    Attributes:
        code: 响应代码（0 表示成功，非 0 表示错误）
        message: 响应消息
        data: 响应数据（可选）
    
    Examples:
        # 成功响应
        {
            "code": 0,
            "message": "操作成功",
            "data": {"id": 1, "name": "example"}
        }
        
        # 错误响应
        {
            "code": 400,
            "message": "参数错误",
            "data": None
        }
    """
    code: int
    message: str
    data: Optional[Any] = None


def success_response(data: Any = None, message: str = "操作成功") -> Dict[str, Any]:
    """生成成功响应
    
    Args:
        data: 响应数据
        message: 响应消息
        
    Returns:
        标准化的成功响应字典
    """
    return {
        "code": 0,
        "message": message,
        "data": data
    }


def error_response(code: int = 500, message: str = "服务器错误", data: Any = None) -> Dict[str, Any]:
    """生成错误响应
    
    Args:
        code: 错误代码
        message: 错误消息
        data: 错误详情（可选）
        
    Returns:
        标准化的错误响应字典
    """
    return {
        "code": code,
        "message": message,
        "data": data
    }


# 常见错误代码
ERROR_CODES = {
    "BAD_REQUEST": 400,
    "UNAUTHORIZED": 401,
    "FORBIDDEN": 403,
    "NOT_FOUND": 404,
    "CONFLICT": 409,
    "INTERNAL_ERROR": 500,
    "SERVICE_UNAVAILABLE": 503,
}
