"""
自集成环境初始化模块
根据部署模式初始化完整的环境，包括数据库、缓存、监控等
"""

import os
import sys
import logging
import asyncio
import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

from .config import settings
from .cache import init_cache, CacheBackend
from .load_balancer import get_load_balancer
from ..models.database import DatabaseManager
from ..monitoring.system import init_monitor_system, DeploymentMode, log_alert_handler

logger = logging.getLogger(__name__)


class EnvironmentInitializer:
    """环境初始化器"""
    
    def __init__(self):
        self.deployment_mode = None
        self.db_manager: Optional[DatabaseManager] = None
        self.initialized = False
    
    def detect_deployment_mode(self) -> str:
        """检测部署模式"""
        # 1. 检查环境变量
        env_mode = os.environ.get("LLM_MANAGER_DEPLOYMENT_MODE", "").lower()
        if env_mode in ["personal", "enterprise"]:
            return env_mode
        
        # 2. 检查配置文件
        config_mode = settings.deployment_mode.lower()
        if config_mode in ["personal", "enterprise"]:
            return config_mode
        
        # 3. 检查是否有Redis可用
        try:
            import redis
            r = redis.Redis(host=settings.redis_host, port=settings.redis_port, 
                          socket_connect_timeout=2)
            r.ping()
            # Redis可用，可能适合企业模式
            logger.info("检测到Redis服务可用")
            
            # 检查是否有PostgreSQL可用
            try:
                import psycopg2
                conn = psycopg2.connect(settings.postgres_url) if settings.postgres_url else None
                if conn:
                    conn.close()
                    logger.info("检测到PostgreSQL服务可用")
                    return "enterprise"
            except Exception:
                pass
            
            # 如果配置了Redis但未配置PostgreSQL，仍然可以使用个人模式
            return "personal"
        except Exception:
            pass
        
        # 4. 默认使用个人模式
        return "personal"
    
    async def initialize(self, force_mode: Optional[str] = None) -> Tuple[bool, str]:
        """初始化环境
        
        Args:
            force_mode: 强制使用的部署模式（personal/enterprise）
            
        Returns:
            (是否成功, 错误信息或成功消息)
        """
        try:
            # 确定部署模式
            if force_mode and force_mode.lower() in ["personal", "enterprise"]:
                self.deployment_mode = force_mode.lower()
                logger.info(f"使用强制部署模式: {self.deployment_mode}")
            else:
                self.deployment_mode = self.detect_deployment_mode()
                logger.info(f"检测到部署模式: {self.deployment_mode}")
            
            # 更新配置中的部署模式
            settings.deployment_mode = self.deployment_mode
            
            # 初始化数据库
            db_success, db_msg = await self._init_database()
            if not db_success:
                return False, db_msg
            
            # 初始化缓存
            cache_success, cache_msg = await self._init_cache()
            if not cache_success:
                return False, cache_msg
            
            # 初始化负载均衡器
            lb_success, lb_msg = await self._init_load_balancer()
            if not lb_success:
                return False, lb_msg
            
            # 初始化监控系统
            if self.deployment_mode == "enterprise":
                monitor_success, monitor_msg = await self._init_monitoring()
                if not monitor_success:
                    return False, monitor_msg
            
            self.initialized = True
            mode_name = "个人模式" if self.deployment_mode == "personal" else "企业模式"
            return True, f"环境初始化成功 ({mode_name})"
        
        except Exception as e:
            logger.error(f"环境初始化失败: {e}", exc_info=True)
            return False, f"环境初始化失败: {str(e)}"
    
    async def _init_database(self) -> Tuple[bool, str]:
        """初始化数据库"""
        try:
            # 创建数据库管理器
            self.db_manager = DatabaseManager()
            
            # 创建数据库表
            self.db_manager.create_tables()
            
            logger.info(f"数据库初始化成功: {self.db_manager.database_url}")
            return True, "数据库初始化成功"
            
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}", exc_info=True)
            return False, f"数据库初始化失败: {str(e)}"
    
    async def _init_cache(self) -> Tuple[bool, str]:
        """初始化缓存"""
        try:
            # 根据部署模式选择缓存后端
            if self.deployment_mode == "enterprise":
                # 企业模式优先使用Redis
                redis_url = settings.get_effective_redis_url()
                if redis_url:
                    try:
                        init_cache(
                            backend=CacheBackend.REDIS,
                            host=settings.redis_host,
                            port=settings.redis_port,
                            db=settings.redis_db,
                            password=settings.redis_password,
                            connection_timeout=5
                        )
                        logger.info("Redis缓存初始化成功")
                        return True, "Redis缓存初始化成功"
                    except Exception as e:
                        logger.warning(f"Redis缓存初始化失败，使用内存缓存: {e}")
                        # 继续使用内存缓存
            
            # 个人模式或Redis初始化失败时使用内存缓存
            init_cache(
                backend=CacheBackend.MEMORY,
                max_size=settings.cache_max_size
            )
            logger.info("内存缓存初始化成功")
            return True, "内存缓存初始化成功"
            
        except Exception as e:
            logger.error(f"缓存初始化失败: {e}", exc_info=True)
            return False, f"缓存初始化失败: {str(e)}"
    
    async def _init_load_balancer(self) -> Tuple[bool, str]:
        """初始化负载均衡器"""
        try:
            # 获取负载均衡器实例
            load_balancer = get_load_balancer()
            logger.info(f"负载均衡器初始化成功，策略: {load_balancer.strategy.value}")
            return True, "负载均衡器初始化成功"
            
        except Exception as e:
            logger.error(f"负载均衡器初始化失败: {e}", exc_info=True)
            return False, f"负载均衡器初始化失败: {str(e)}"
    
    async def _init_monitoring(self) -> Tuple[bool, str]:
        """初始化监控系统（仅企业模式）"""
        try:
            # 确定部署模式枚举
            deployment_enum = (
                DeploymentMode.ENTERPRISE if self.deployment_mode == "enterprise" 
                else DeploymentMode.PERSONAL
            )
            
            # 初始化监控系统
            monitor_system = init_monitor_system(deployment_mode=deployment_enum)
            
            # 添加日志告警处理器
            monitor_system.add_alert_handler(log_alert_handler)
            
            # 启动监控系统
            await monitor_system.start()
            
            logger.info(f"监控系统初始化并启动成功，模式: {deployment_enum.value}")
            return True, "监控系统初始化并启动成功"
            
        except Exception as e:
            logger.error(f"监控系统初始化失败: {e}", exc_info=True)
            return False, f"监控系统初始化失败: {str(e)}"
    
    def get_status(self) -> Dict[str, Any]:
        """获取环境状态"""
        return {
            "initialized": self.initialized,
            "deployment_mode": self.deployment_mode,
            "database_url": self.db_manager.database_url if self.db_manager else None,
            "cache_backend": settings.get_effective_cache_backend(),
            "redis_url": settings.get_effective_redis_url(),
        }


# 全局环境初始化器实例
_env_initializer: Optional[EnvironmentInitializer] = None


def get_env_initializer() -> EnvironmentInitializer:
    """获取全局环境初始化器实例"""
    global _env_initializer
    if _env_initializer is None:
        _env_initializer = EnvironmentInitializer()
    return _env_initializer


async def init_environment(force_mode: Optional[str] = None) -> Tuple[bool, str]:
    """初始化环境（便捷函数）"""
    initializer = get_env_initializer()
    return await initializer.initialize(force_mode)


def get_environment_status() -> Dict[str, Any]:
    """获取环境状态（便捷函数）"""
    initializer = get_env_initializer()
    return initializer.get_status()


def ensure_initialized():
    """确保环境已初始化（同步版本）"""
    import asyncio
    
    initializer = get_env_initializer()
    if not initializer.initialized:
        try:
            # 在同步上下文中运行异步初始化
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果已经在事件循环中，创建任务
                task = asyncio.create_task(initializer.initialize())
                # 无法直接等待，所以返回部分初始化状态
                return False
            else:
                # 如果不在事件循环中，直接运行
                success, _ = loop.run_until_complete(initializer.initialize())
                return success
        except Exception as e:
            logger.error(f"确保环境初始化失败: {e}")
            return False
    
    return True