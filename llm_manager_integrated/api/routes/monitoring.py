"""
监控路由 - 提供系统监控、渠道状态、负载均衡指标等功能

此模块整合了原 proxy 模块中的管理功能，包括：
- 系统健康状态
- 渠道状态查询
- 负载均衡器管理
- 模型缓存管理

原 proxy 模块保留作为备用参考。
"""

import time
import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, Depends

from llm_manager_integrated.api.responses import success_response, error_response
from llm_manager_integrated.api.dependencies import get_db_manager
from llm_manager_integrated.models.database import DatabaseManager
from llm_manager_integrated.core.load_balancer import (
    get_load_balancer, 
    create_channel_from_config, 
    LoadBalanceStrategy,
    set_load_balancer_strategy
)
from llm_manager_integrated.core.crud import get_channel, get_channels

router = APIRouter()
logger = logging.getLogger(__name__)


# =============================================================================
# 系统监控端点（原有）
# =============================================================================

@router.get("/stats")
async def get_stats(
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """获取系统统计数据"""
    try:
        # 获取基本统计信息
        stats = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "healthy",
            "uptime": "operational"
        }
        
        return success_response(
            data=stats,
            message="获取统计数据成功"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=error_response(
                code=500,
                message="获取统计数据失败"
            )
        )


@router.get("/health")
async def get_health(
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """获取系统健康状态"""
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "api": "running",
                "database": "connected"
            }
        }
        
        return success_response(
            data=health_status,
            message="获取健康状态成功"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=error_response(
                code=500,
                message="获取健康状态失败"
            )
        )


# =============================================================================
# 渠道状态端点（从 proxy.py 迁移）
# =============================================================================

@router.get("/channels/status")
async def get_channels_status(
    request: Request,
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """
    获取所有渠道状态
    
    返回渠道列表及其健康状态、指标信息
    """
    # 获取负载均衡器
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
            "api_base": db_channel.base_url,
            "model": db_channel.models,
            "max_qps": 10,
            "timeout": 30,
            "weight": 1,
            "enabled": db_channel.status,
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


# =============================================================================
# 负载均衡器管理端点（从 proxy.py 迁移）
# =============================================================================

@router.post("/load-balancer/strategy")
async def update_load_balancer_strategy(
    strategy: str,
    request: Request,
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """
    更新负载均衡策略
    
    Parameters:
    - strategy: 策略名称 (round_robin, weighted, random, least_connections)
    """
    try:
        # 验证策略
        new_strategy = LoadBalanceStrategy(strategy)
        
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
    db_manager: DatabaseManager = Depends(get_db_manager)
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
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """
    手动执行渠道健康检查
    
    Parameters:
    - channel_id: 渠道ID
    """
    import httpx
    
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
    
    # 执行健康检查
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # 构建健康检查请求
            test_request = {
                "model": db_channel.models.split(",")[0].strip() if db_channel.models else "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": "健康检查"}],
                "max_tokens": 5
            }
            
            headers = {
                "Authorization": f"Bearer {db_channel.api_key}",
                "Content-Type": "application/json"
            }
            
            url = f"{db_channel.base_url.rstrip('/')}/chat/completions"
            
            start_time = time.time()
            response = await client.post(
                url=url,
                headers=headers,
                json=test_request
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                is_healthy = True
                message = "健康检查通过"
            else:
                is_healthy = False
                message = f"健康检查失败: HTTP {response.status_code}"
    
    except Exception as e:
        is_healthy = False
        message = "健康检查异常"
        logger.error(f"健康检查异常: {str(e)}", exc_info=True)
        response_time = 0.0
    
    return success_response(
        data={
            "channel_id": channel_id,
            "channel_name": db_channel.name,
            "is_healthy": is_healthy,
            "response_time": response_time if is_healthy else None,
            "message": message,
            "checked_at": datetime.utcnow().isoformat()
        },
        message=message
    )


# =============================================================================
# 模型缓存管理端点（从 models_proxy.py 迁移）
# =============================================================================

@router.get("/models/cache/stats")
async def get_models_cache_stats():
    """
    获取模型缓存统计信息
    
    返回缓存命中率、缓存大小等监控指标
    """
    try:
        from llm_manager_integrated.api.routes.proxy.models_proxy import _models_cache, MODELS_CACHE_TTL, MODELS_CACHE_MAX_SIZE
        
        stats = _models_cache.get_stats()
        return success_response(
            data={
                "cache": stats,
                "config": {
                    "ttl_seconds": MODELS_CACHE_TTL,
                    "max_size": MODELS_CACHE_MAX_SIZE
                }
            },
            message="获取缓存统计成功"
        )
    except ImportError:
        return success_response(
            data={
                "cache": {"status": "unavailable"},
                "message": "缓存模块未加载"
            },
            message="缓存模块未加载"
        )


@router.post("/models/cache/invalidate")
async def invalidate_models_cache(
    proxy_type: Optional[str] = None,
    include_unavailable: Optional[bool] = None
):
    """
    手动使模型缓存失效
    
    Parameters:
    - proxy_type: 指定代理类型，不传则清除所有
    - include_unavailable: 指定过滤条件，不传则清除所有
    """
    try:
        from llm_manager_integrated.api.routes.proxy.models_proxy import _models_cache
        
        _models_cache.invalidate(proxy_type, include_unavailable)
        return success_response(
            data=_models_cache.get_stats(),
            message="缓存已失效"
        )
    except ImportError:
        return success_response(
            data={"status": "unavailable"},
            message="缓存模块未加载"
        )


@router.post("/models/cache/reset-stats")
async def reset_models_cache_stats():
    """重置缓存统计信息"""
    try:
        from llm_manager_integrated.api.routes.proxy.models_proxy import _models_cache
        
        _models_cache.reset_stats()
        return success_response(
            data=_models_cache.get_stats(),
            message="缓存统计已重置"
        )
    except ImportError:
        return success_response(
            data={"status": "unavailable"},
            message="缓存模块未加载"
        )
