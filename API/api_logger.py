"""
API调用日志记录器 - 为Chat API提供日志记录功能

功能：
- 记录每次LLM调用的请求/响应信息
- 统计token使用量和成本
- 支持异步非阻塞记录
- 与现有的 /llm-manager/ 管理界面兼容
"""

import time
import logging
import uuid
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class APICallMetrics:
    """API调用指标"""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    channel_id: Optional[str] = None
    channel_name: Optional[str] = None
    model: str = ""
    provider: str = "openai"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    response_time: float = 0.0
    status: str = "success"  # success, error
    error_message: Optional[str] = None
    estimated_cost: float = 0.0
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "request_id": self.request_id,
            "channel_id": self.channel_id,
            "channel_name": self.channel_name,
            "model": self.model,
            "provider": self.provider,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "response_time": self.response_time,
            "status": self.status,
            "error_message": self.error_message,
            "estimated_cost": self.estimated_cost,
            "timestamp": self.timestamp,
        }


class ChatAPILogger:
    """
    Chat API日志记录器
    
    特性：
    - 异步非阻塞记录
    - 延迟初始化数据库连接
    - 成本估算
    - 与LLM Manager日志系统集成
    """
    
    def __init__(self):
        self._db_manager = None
        self._initialized = False
        # 内存中的最近日志（用于快速查询）
        self._recent_logs: list = []
        self._max_recent_logs = 100
    
    def _get_db_manager(self):
        """延迟获取数据库管理器"""
        if self._db_manager is None:
            try:
                from llm_manager_integrated.models.database import get_db_manager
                self._db_manager = get_db_manager()
                self._initialized = True
            except ImportError:
                logger.warning("无法导入数据库管理器，日志将只保存在内存中")
        return self._db_manager
    
    async def log_api_call(self, metrics: APICallMetrics):
        """
        异步记录API调用日志
        
        Args:
            metrics: API调用指标
        """
        # 计算成本
        if metrics.estimated_cost == 0.0:
            metrics.estimated_cost = self.estimate_cost(
                metrics.model, 
                metrics.prompt_tokens, 
                metrics.completion_tokens
            )
        
        # 保存到内存
        self._add_to_recent_logs(metrics)
        
        # 尝试保存到数据库
        db_manager = self._get_db_manager()
        if not db_manager:
            return
        
        try:
            from llm_manager_integrated.core.crud import create_api_log
            from llm_manager_integrated.models.schemas import APILogCreate
            
            log_data = APILogCreate(
                request_id=metrics.request_id,
                channel_id=int(metrics.channel_id) if metrics.channel_id and metrics.channel_id.isdigit() else None,
                model_name=metrics.model,
                provider=metrics.provider,
                prompt_tokens=metrics.prompt_tokens,
                completion_tokens=metrics.completion_tokens,
                total_tokens=metrics.total_tokens,
                response_time=metrics.response_time,
                status=metrics.status,
                error_message=metrics.error_message,
                estimated_cost=metrics.estimated_cost,
            )
            
            with db_manager.get_session() as db:
                create_api_log(db, log_data)
                
            logger.debug(f"API调用日志已记录: {metrics.request_id}")
        except Exception as e:
            # 日志记录失败不应影响主流程
            logger.warning(f"记录API调用日志失败: {e}")
    
    def _add_to_recent_logs(self, metrics: APICallMetrics):
        """添加到最近日志列表"""
        self._recent_logs.append(metrics.to_dict())
        # 保持列表大小
        if len(self._recent_logs) > self._max_recent_logs:
            self._recent_logs = self._recent_logs[-self._max_recent_logs:]
    
    def get_recent_logs(self, limit: int = 20) -> list:
        """获取最近的日志"""
        return self._recent_logs[-limit:][::-1]  # 最新的在前
    
    def estimate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """
        估算API调用成本
        
        基于常见模型的定价估算，可扩展为从配置读取
        
        Args:
            model: 模型名称
            prompt_tokens: 输入token数
            completion_tokens: 输出token数
            
        Returns:
            估算成本（美元）
        """
        # 定价表（每1K tokens的价格，单位：美元）
        pricing = {
            # OpenAI
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
            "gpt-4o": {"input": 0.005, "output": 0.015},
            "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
            "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
            "o1": {"input": 0.015, "output": 0.06},
            "o1-mini": {"input": 0.003, "output": 0.012},
            # Claude
            "claude-3-opus": {"input": 0.015, "output": 0.075},
            "claude-3-5-sonnet": {"input": 0.003, "output": 0.015},
            "claude-3-sonnet": {"input": 0.003, "output": 0.015},
            "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
            # DeepSeek
            "deepseek-chat": {"input": 0.00014, "output": 0.00028},
            "deepseek-coder": {"input": 0.00014, "output": 0.00028},
            "deepseek-reasoner": {"input": 0.00055, "output": 0.00219},
            # Google
            "gemini-1.5-pro": {"input": 0.00125, "output": 0.005},
            "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},
            "gemini-2.0-flash": {"input": 0.0001, "output": 0.0004},
        }
        
        # 查找匹配的定价
        model_lower = model.lower()
        for key, price in pricing.items():
            if key in model_lower:
                input_cost = (prompt_tokens / 1000) * price["input"]
                output_cost = (completion_tokens / 1000) * price["output"]
                return round(input_cost + output_cost, 6)
        
        # 默认定价（按DeepSeek价格）
        return round((prompt_tokens / 1000) * 0.00014 + (completion_tokens / 1000) * 0.00028, 6)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取日志统计信息"""
        if not self._recent_logs:
            return {
                "total_calls": 0,
                "success_rate": 0.0,
                "total_tokens": 0,
                "total_cost": 0.0,
                "avg_response_time": 0.0,
            }
        
        total_calls = len(self._recent_logs)
        success_calls = sum(1 for log in self._recent_logs if log["status"] == "success")
        total_tokens = sum(log["total_tokens"] for log in self._recent_logs)
        total_cost = sum(log["estimated_cost"] for log in self._recent_logs)
        avg_response_time = sum(log["response_time"] for log in self._recent_logs) / total_calls
        
        return {
            "total_calls": total_calls,
            "success_rate": round(success_calls / total_calls * 100, 2) if total_calls > 0 else 0.0,
            "total_tokens": total_tokens,
            "total_cost": round(total_cost, 4),
            "avg_response_time": round(avg_response_time, 3),
            "recent_logs_count": len(self._recent_logs),
        }


# 全局日志记录器实例
_chat_api_logger: Optional[ChatAPILogger] = None


def get_chat_api_logger() -> ChatAPILogger:
    """获取Chat API日志记录器单例"""
    global _chat_api_logger
    if _chat_api_logger is None:
        _chat_api_logger = ChatAPILogger()
    return _chat_api_logger
