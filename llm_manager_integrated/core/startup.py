"""
应用启动初始化模块
确保应用启动时正确初始化所有组件
"""

import logging
import asyncio
from typing import Optional, Tuple

from .init_environment import init_environment, get_environment_status
from .config import settings
from .load_balancer import get_load_balancer, create_channel_from_config
from ..models.database import get_db_manager
from ..core import crud

logger = logging.getLogger(__name__)


async def load_channels_to_load_balancer(load_balancer=None) -> Tuple[bool, str]:
    """将数据库中的渠道加载到负载均衡器
    
    Args:
        load_balancer: 可选的负载均衡器实例，如果不提供则使用全局实例
        
    Returns:
        (是否成功, 错误信息或成功消息)
    """
    try:
        # 获取负载均衡器实例
        if load_balancer is None:
            load_balancer = get_load_balancer()
        logger.info("开始加载渠道到负载均衡器...")
        
        # 获取数据库管理器
        db_manager = get_db_manager()
        
        # 从数据库获取所有启用的渠道
        with db_manager.get_session() as db:
            channels = crud.get_channels(db=db)
            
            loaded_count = 0
            for channel in channels:
                if channel.status:  # 只加载启用的渠道
                    # 创建负载均衡器渠道对象
                    lb_channel = create_channel_from_config({
                        'id': str(channel.id),
                        'name': channel.name,
                        'api_base': channel.base_url,
                        'api_key': channel.api_key,
                        'model': channel.models,
                        'type': channel.type,  # 传递渠道类型
                        'weight': 1,  # 默认权重
                        'max_qps': 10,  # 默认QPS限制
                        'timeout': 30  # 默认超时
                    })
                    
                    # 添加到负载均衡器
                    load_balancer.add_channel(lb_channel)
                    loaded_count += 1
                    logger.info(f"已加载渠道: {channel.name} ({channel.id})")
        
        logger.info(f"渠道加载完成，共加载 {loaded_count} 个渠道")
        
        # 强制设置全局实例
        from .load_balancer import _load_balancer
        import llm_manager_integrated.core.load_balancer as lb_module
        lb_module._load_balancer = load_balancer
        logger.info(f"全局负载均衡器已更新，渠道数: {len(lb_module._load_balancer.channels)}")
        
        return True, f"成功加载 {loaded_count} 个渠道"
        
    except Exception as e:
        logger.error(f"渠道加载失败: {e}", exc_info=True)
        return False, f"渠道加载失败: {str(e)}"


async def startup_app(force_mode: Optional[str] = None) -> Tuple[bool, str]:
    """应用启动初始化
    
    Args:
        force_mode: 强制使用的部署模式（personal/enterprise）
        
    Returns:
        (是否成功, 错误信息或成功消息)
    """
    logger.info("开始初始化 LLM API Manager 应用...")
    
    # 初始化环境
    success, message = await init_environment(force_mode)
    if not success:
        logger.error(f"环境初始化失败: {message}")
        return False, f"环境初始化失败: {message}"
    
    # 获取环境状态
    env_status = get_environment_status()
    
    # 记录关键信息
    logger.info(f"应用初始化完成: {message}")
    logger.info(f"部署模式: {env_status['deployment_mode']}")
    logger.info(f"数据库: {env_status['database_url']}")
    logger.info(f"缓存后端: {env_status['cache_backend']}")
    
    if env_status['redis_url']:
        logger.info(f"Redis: {env_status['redis_url']}")
    
    # Phase 6: 初始化执行状态持久化存储
    try:
        from deepanalyze.core.task_manager import PersistentExecutionStore
        PersistentExecutionStore.initialize()
        logger.info("执行状态持久化存储初始化完成")
    except ImportError:
        logger.debug("Task manager module not available, skipping PersistentExecutionStore initialization")
    except Exception as e:
        logger.warning(f"执行状态持久化存储初始化失败: {e}")
    
    return True, message


def sync_startup_app(force_mode: Optional[str] = None) -> Tuple[bool, str]:
    """同步版本的应用启动初始化
    
    这个函数适用于不能使用async/await的场景，如FastAPI的startup事件
    
    Args:
        force_mode: 强制使用的部署模式（personal/enterprise）
        
    Returns:
        (是否成功, 错误信息或成功消息)
    """
    try:
        # 获取或创建事件循环
        try:
            loop = asyncio.get_running_loop()
            # 如果已经有事件循环在运行，创建一个任务
            task = asyncio.create_task(startup_app(force_mode))
            # 返回任务，而不是等待它完成
            return True, "启动任务已创建"
        except RuntimeError:
            # 没有运行的事件循环，创建一个
            return asyncio.run(startup_app(force_mode))
    except Exception as e:
        logger.error(f"应用启动失败: {e}", exc_info=True)
        return False, f"应用启动失败: {str(e)}"


# 便捷函数，用于FastAPI的startup事件
async def app_startup_handler(app=None):
    """FastAPI应用启动事件处理器"""
    success, message = await startup_app()
    if not success:
        logger.error(f"应用启动失败: {message}")
        # 在实际应用中，可能需要更复杂的错误处理
        # 这里只是记录错误
    else:
        logger.info(f"应用启动成功: {message}")