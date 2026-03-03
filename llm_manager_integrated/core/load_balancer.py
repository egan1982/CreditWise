"""
负载均衡器 - 实现多种负载均衡策略
支持轮询、最少使用、最快响应和加权分配策略
"""

import time
import random
from typing import List, Dict, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass, field
import asyncio
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class LoadBalanceStrategy(str, Enum):
    """负载均衡策略"""
    ROUND_ROBIN = "round_robin"      # 轮询
    LEAST_USED = "least_used"       # 最少使用
    FASTEST = "fastest"            # 最快响应
    WEIGHTED = "weighted"          # 加权分配


@dataclass
class ChannelMetrics:
    """渠道性能指标"""
    channel_id: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    last_response_time: float = 0.0
    last_request_time: float = 0.0
    weight: int = 1                # 权重（用于加权策略）
    consecutive_failures: int = 0  # 连续失败次数
    is_healthy: bool = True        # 是否健康
    error_rate: float = 0.0        # 错误率
    
    def update_success(self, response_time: float):
        """更新成功请求指标"""
        self.total_requests += 1
        self.successful_requests += 1
        self.consecutive_failures = 0
        self.last_response_time = response_time
        self.last_request_time = time.time()
        self._calculate_avg_response_time()
        self._update_error_rate()
    
    def update_failure(self):
        """更新失败请求指标"""
        self.total_requests += 1
        self.failed_requests += 1
        self.consecutive_failures += 1
        self.last_request_time = time.time()
        self._update_error_rate()
        
        # 连续失败超过阈值，标记为不健康
        if self.consecutive_failures >= 3:
            self.is_healthy = False
    
    def _calculate_avg_response_time(self):
        """计算平均响应时间"""
        if self.successful_requests > 0:
            # 使用简单的移动平均
            if self.avg_response_time == 0:
                self.avg_response_time = self.last_response_time
            else:
                self.avg_response_time = (
                    self.avg_response_time * 0.8 + 
                    self.last_response_time * 0.2
                )
    
    def _update_error_rate(self):
        """更新错误率"""
        if self.total_requests > 0:
            self.error_rate = self.failed_requests / self.total_requests


@dataclass
class Channel:
    """渠道信息"""
    id: str
    name: str
    api_base: str
    api_key: str
    model: str
    channel_type: str = "openai"      # 渠道类型（openai, google, azure等）
    max_qps: int = 10                 # 最大QPS限制
    timeout: int = 30                 # 超时时间（秒）
    weight: int = 1                   # 权重
    metrics: ChannelMetrics = field(init=False)
    
    def __post_init__(self):
        self.metrics = ChannelMetrics(
            channel_id=self.id,
            weight=self.weight
        )


class LoadBalancer:
    """负载均衡器"""
    
    def __init__(self, strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN):
        self.strategy = strategy
        self.channels: Dict[str, Channel] = {}
        self._round_robin_index = 0
        self._lock = asyncio.Lock()
        self._health_check_interval = 60  # 健康检查间隔（秒）
        self._last_health_check = 0
        
        logger.info(f"负载均衡器初始化完成，策略: {strategy.value}")
    
    def add_channel(self, channel: Channel):
        """添加渠道"""
        self.channels[channel.id] = channel
        logger.info(f"添加渠道: {channel.name} ({channel.id})")
    
    def remove_channel(self, channel_id: str):
        """移除渠道"""
        if channel_id in self.channels:
            channel_name = self.channels[channel_id].name
            del self.channels[channel_id]
            logger.info(f"移除渠道: {channel_name} ({channel_id})")
    
    def update_channel(self, channel_id: str, **kwargs):
        """更新渠道配置"""
        if channel_id in self.channels:
            channel = self.channels[channel_id]
            for key, value in kwargs.items():
                if hasattr(channel, key):
                    setattr(channel, key, value)
                    logger.debug(f"更新渠道 {channel_id} 属性 {key}: {value}")
    
    async def select_channel(self, model: Optional[str] = None, exclude_unhealthy: bool = True) -> Optional[Channel]:
        """选择渠道
        
        Args:
            model: 指定的模型名称，如果提供则只选择支持该模型的渠道
            exclude_unhealthy: 是否排除不健康的渠道
        """
        async with self._lock:
            # 过滤渠道
            available_channels = [
                channel for channel in self.channels.values()
                if not exclude_unhealthy or channel.metrics.is_healthy
            ]
            
            # 如果指定了模型，进一步过滤支持该模型的渠道
            if model:
                model_channels = []
                for channel in available_channels:
                    # 检查渠道是否支持指定的模型
                    if self._channel_supports_model(channel, model):
                        model_channels.append(channel)
                        logger.debug(f"渠道 {channel.name} 支持模型 {model}")
                
                # 如果找到支持模型的渠道，使用这些渠道
                if model_channels:
                    available_channels = model_channels
                else:
                    # 没有找到支持指定模型的渠道，记录警告并返回None
                    logger.warning(f"没有找到支持模型 {model} 的渠道")
                    return None
            
            if not available_channels:
                logger.warning("没有可用的渠道")
                return None
            
            # 定期健康检查
            await self._periodic_health_check()
            
            # 根据策略选择渠道
            if self.strategy == LoadBalanceStrategy.ROUND_ROBIN:
                return self._select_round_robin(available_channels)
            elif self.strategy == LoadBalanceStrategy.LEAST_USED:
                return self._select_least_used(available_channels)
            elif self.strategy == LoadBalanceStrategy.FASTEST:
                return self._select_fastest(available_channels)
            elif self.strategy == LoadBalanceStrategy.WEIGHTED:
                return self._select_weighted(available_channels)
            else:
                # 默认使用轮询
                return self._select_round_robin(available_channels)
    
    def _channel_supports_model(self, channel: Channel, model: str) -> bool:
        """检查渠道是否支持指定的模型
        
        Args:
            channel: 渠道对象
            model: 模型名称
            
        Returns:
            bool: 是否支持该模型
        """
        # 如果渠道没有配置模型，则支持所有模型（兼容旧配置）
        if not channel.model:
            return True
            
        # 处理模型列表（逗号分隔）
        models = [m.strip() for m in channel.model.split(',') if m.strip()]
        
        # 检查请求的模型是否在渠道支持的模型列表中
        return model in models
    
    def _select_round_robin(self, channels: List[Channel]) -> Channel:
        """轮询选择"""
        if not channels:
            raise ValueError("没有可用渠道")
        
        channel = channels[self._round_robin_index % len(channels)]
        self._round_robin_index += 1
        logger.debug(f"轮询选择渠道: {channel.name}")
        return channel
    
    def _select_least_used(self, channels: List[Channel]) -> Channel:
        """最少使用选择"""
        if not channels:
            raise ValueError("没有可用渠道")
        
        # 按总请求数排序
        sorted_channels = sorted(channels, key=lambda c: c.metrics.total_requests)
        channel = sorted_channels[0]
        logger.debug(f"最少使用选择渠道: {channel.name} (请求数: {channel.metrics.total_requests})")
        return channel
    
    def _select_fastest(self, channels: List[Channel]) -> Channel:
        """最快响应选择"""
        if not channels:
            raise ValueError("没有可用渠道")
        
        # 过滤有响应时间记录的渠道
        channels_with_time = [
            channel for channel in channels 
            if channel.metrics.avg_response_time > 0
        ]
        
        if channels_with_time:
            # 按平均响应时间排序
            sorted_channels = sorted(channels_with_time, key=lambda c: c.metrics.avg_response_time)
            channel = sorted_channels[0]
            logger.debug(f"最快响应选择渠道: {channel.name} (响应时间: {channel.metrics.avg_response_time:.2f}s)")
        else:
            # 没有响应时间记录，使用轮询
            channel = self._select_round_robin(channels)
            logger.debug(f"无响应时间记录，使用轮询选择: {channel.name}")
        
        return channel
    
    def _select_weighted(self, channels: List[Channel]) -> Channel:
        """加权随机选择"""
        if not channels:
            raise ValueError("没有可用渠道")
        
        # 计算总权重
        total_weight = sum(channel.metrics.weight for channel in channels)
        if total_weight <= 0:
            # 权重无效，使用轮询
            return self._select_round_robin(channels)
        
        # 生成随机数
        random_value = random.random() * total_weight
        
        # 按权重选择
        current_weight = 0
        for channel in channels:
            current_weight += channel.metrics.weight
            if random_value <= current_weight:
                logger.debug(f"加权随机选择渠道: {channel.name} (权重: {channel.metrics.weight})")
                return channel
        
        # 兜底：返回最后一个渠道
        channel = channels[-1]
        logger.debug(f"加权随机选择(兜底)渠道: {channel.name}")
        return channel
    
    async def _periodic_health_check(self):
        """定期健康检查"""
        current_time = time.time()
        if current_time - self._last_health_check < self._health_check_interval:
            return
        
        self._last_health_check = current_time
        
        # 检查连续失败的渠道，尝试恢复
        for channel in self.channels.values():
            if not channel.metrics.is_healthy:
                # 尝试恢复健康状态（简单实现：基于时间恢复）
                if current_time - channel.metrics.last_request_time > 300:  # 5分钟后尝试恢复
                    channel.metrics.is_healthy = True
                    channel.metrics.consecutive_failures = 0
                    logger.info(f"渠道 {channel.name} 尝试恢复健康状态")
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取负载均衡指标"""
        return {
            "strategy": self.strategy.value,
            "total_channels": len(self.channels),
            "healthy_channels": sum(1 for c in self.channels.values() if c.metrics.is_healthy),
            "unhealthy_channels": sum(1 for c in self.channels.values() if not c.metrics.is_healthy),
            "channel_metrics": {
                channel_id: {
                    "name": channel.name,
                    "total_requests": channel.metrics.total_requests,
                    "success_rate": (
                        channel.metrics.successful_requests / channel.metrics.total_requests 
                        if channel.metrics.total_requests > 0 else 0
                    ),
                    "avg_response_time": channel.metrics.avg_response_time,
                    "last_response_time": channel.metrics.last_response_time,
                    "weight": channel.metrics.weight,
                    "is_healthy": channel.metrics.is_healthy,
                    "consecutive_failures": channel.metrics.consecutive_failures,
                    "error_rate": channel.metrics.error_rate
                }
                for channel_id, channel in self.channels.items()
            }
        }


# 全局负载均衡器实例
_load_balancer: Optional[LoadBalancer] = None


def get_load_balancer(strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN) -> LoadBalancer:
    """获取全局负载均衡器实例"""
    global _load_balancer
    if _load_balancer is None:
        _load_balancer = LoadBalancer(strategy)
        logger.info(f"创建新的负载均衡器实例: {id(_load_balancer)}")
    else:
        logger.debug(f"复用现有负载均衡器实例: {id(_load_balancer)}")
    return _load_balancer


def set_load_balancer_strategy(strategy: LoadBalanceStrategy):
    """设置负载均衡策略"""
    global _load_balancer
    if _load_balancer:
        _load_balancer.strategy = strategy
        logger.info(f"负载均衡策略已更新为: {strategy.value}")


# 辅助函数
def create_channel_from_config(config: Dict[str, Any]) -> Channel:
    """从配置创建渠道对象"""
    return Channel(
        id=config.get("id", ""),
        name=config.get("name", ""),
        api_base=config.get("api_base", ""),
        api_key=config.get("api_key", ""),
        model=config.get("model", ""),
        channel_type=config.get("type", "openai"),
        max_qps=config.get("max_qps", 10),
        timeout=config.get("timeout", 30),
        weight=config.get("weight", 1)
    )