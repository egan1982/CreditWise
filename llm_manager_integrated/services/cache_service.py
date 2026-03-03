"""
缓存服务 - 提供高级缓存功能
包括API响应缓存、会话缓存、配置缓存等
"""

import json
import asyncio
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
import logging

from ..core.cache import get_cache_manager, CacheBackend
from ..core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """缓存服务类"""
    
    def __init__(self, cache_manager=None):
        self._cache_manager = cache_manager or get_cache_manager()
        self._request_cache_ttl = getattr(settings, 'request_cache_ttl', 300)  # 5分钟
        self._session_cache_ttl = getattr(settings, 'session_cache_ttl', 1800)  # 30分钟
        self._config_cache_ttl = getattr(settings, 'config_cache_ttl', 3600)   # 1小时
    
    async def cache_request_response(
        self,
        method: str,
        url: str,
        params: Dict[str, Any],
        data: Dict[str, Any],
        response: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """缓存API请求响应"""
        try:
            # 生成缓存键
            cache_key = self._cache_manager.generate_request_cache_key(
                method=method, url=url, params=params, data=data
            )
            
            # 缓存响应数据
            cache_data = {
                "method": method,
                "url": url,
                "response": response,
                "created_at": datetime.utcnow().isoformat()
            }
            
            # 使用指定的TTL或默认TTL
            cache_ttl = ttl or self._request_cache_ttl
            
            # 存储到缓存
            return await self._cache_manager.set(cache_key, cache_data, cache_ttl)
        except Exception as e:
            logger.error(f"缓存请求响应失败: {e}")
            return False
    
    async def get_cached_request_response(
        self,
        method: str,
        url: str,
        params: Dict[str, Any],
        data: Dict[str, Any]
    ) -> Optional[Any]:
        """获取缓存的API请求响应"""
        try:
            # 生成缓存键
            cache_key = self._cache_manager.generate_request_cache_key(
                method=method, url=url, params=params, data=data
            )
            
            # 从缓存获取
            cache_data = await self._cache_manager.get(cache_key)
            
            if cache_data is None:
                return None
            
            # 检查是否过期（由缓存后端自动处理）
            return cache_data.get("response")
        except Exception as e:
            logger.error(f"获取缓存请求响应失败: {e}")
            return None
    
    async def cache_session_data(
        self,
        session_id: str,
        data: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """缓存会话数据"""
        try:
            cache_key = f"session:{session_id}"
            cache_ttl = ttl or self._session_cache_ttl
            
            # 添加会话元数据
            session_data = {
                "data": data,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            return await self._cache_manager.set(cache_key, session_data, cache_ttl)
        except Exception as e:
            logger.error(f"缓存会话数据失败: {e}")
            return False
    
    async def get_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话数据"""
        try:
            cache_key = f"session:{session_id}"
            session_data = await self._cache_manager.get(cache_key)
            
            if session_data is None:
                return None
            
            return session_data.get("data")
        except Exception as e:
            logger.error(f"获取会话数据失败: {e}")
            return None
    
    async def update_session_data(
        self,
        session_id: str,
        updates: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """更新会话数据"""
        try:
            # 获取现有会话数据
            existing_data = await self.get_session_data(session_id) or {}
            
            # 合并更新
            existing_data.update(updates)
            
            # 重新缓存
            return await self.cache_session_data(session_id, existing_data, ttl)
        except Exception as e:
            logger.error(f"更新会话数据失败: {e}")
            return False
    
    async def delete_session(self, session_id: str) -> bool:
        """删除会话数据"""
        try:
            cache_key = f"session:{session_id}"
            return await self._cache_manager.delete(cache_key)
        except Exception as e:
            logger.error(f"删除会话数据失败: {e}")
            return False
    
    async def cache_config_data(
        self,
        config_type: str,
        config_data: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """缓存配置数据"""
        try:
            cache_key = f"config:{config_type}"
            cache_ttl = ttl or self._config_cache_ttl
            
            # 添加配置元数据
            cache_data = {
                "type": config_type,
                "data": config_data,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            return await self._cache_manager.set(cache_key, cache_data, cache_ttl)
        except Exception as e:
            logger.error(f"缓存配置数据失败: {e}")
            return False
    
    async def get_config_data(self, config_type: str) -> Optional[Dict[str, Any]]:
        """获取配置数据"""
        try:
            cache_key = f"config:{config_type}"
            cache_data = await self._cache_manager.get(cache_key)
            
            if cache_data is None:
                return None
            
            return cache_data.get("data")
        except Exception as e:
            logger.error(f"获取配置数据失败: {e}")
            return None
    
    async def invalidate_config_cache(self, config_type: str) -> bool:
        """使配置缓存失效"""
        try:
            cache_key = f"config:{config_type}"
            return await self._cache_manager.delete(cache_key)
        except Exception as e:
            logger.error(f"使配置缓存失效失败: {e}")
            return False
    
    async def invalidate_all_request_cache(self) -> bool:
        """使所有请求缓存失效"""
        try:
            # 获取所有请求缓存键
            request_cache_keys = await self._cache_manager.keys("request:*")
            
            # 删除所有请求缓存
            success_count = 0
            for key in request_cache_keys:
                if await self._cache_manager.delete(key):
                    success_count += 1
            
            logger.info(f"使 {success_count}/{len(request_cache_keys)} 个请求缓存失效")
            return success_count == len(request_cache_keys)
        except Exception as e:
            logger.error(f"使所有请求缓存失效失败: {e}")
            return False
    
    async def invalidate_all_session_cache(self) -> bool:
        """使所有会话缓存失效"""
        try:
            # 获取所有会话缓存键
            session_cache_keys = await self._cache_manager.keys("session:*")
            
            # 删除所有会话缓存
            success_count = 0
            for key in session_cache_keys:
                if await self._cache_manager.delete(key):
                    success_count += 1
            
            logger.info(f"使 {success_count}/{len(session_cache_keys)} 个会话缓存失效")
            return success_count == len(session_cache_keys)
        except Exception as e:
            logger.error(f"使所有会话缓存失效失败: {e}")
            return False
    
    async def get_cache_statistics(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        try:
            backend_info = await self._cache_manager.info()
            
            # 获取各类缓存的键数量
            request_keys = await self._cache_manager.keys("request:*")
            session_keys = await self._cache_manager.keys("session:*")
            config_keys = await self._cache_manager.keys("config:*")
            
            return {
                "backend_info": backend_info,
                "cache_counts": {
                    "request": len(request_keys),
                    "session": len(session_keys),
                    "config": len(config_keys),
                    "total": len(request_keys) + len(session_keys) + len(config_keys)
                },
                "ttl_settings": {
                    "request": self._request_cache_ttl,
                    "session": self._session_cache_ttl,
                    "config": self._config_cache_ttl
                }
            }
        except Exception as e:
            logger.error(f"获取缓存统计信息失败: {e}")
            return {"error": str(e)}
    
    async def clear_expired_cache(self) -> int:
        """清理过期的缓存（主要用于内存缓存）"""
        try:
            # 获取所有缓存键
            all_keys = await self._cache_manager.keys("*")
            
            expired_count = 0
            for key in all_keys:
                exists = await self._cache_manager.exists(key)
                if not exists:
                    expired_count += 1
            
            return expired_count
        except Exception as e:
            logger.error(f"清理过期缓存失败: {e}")
            return 0


# 全局缓存服务实例
_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """获取全局缓存服务实例"""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service


def init_cache_service(backend: CacheBackend = CacheBackend.MEMORY, **kwargs) -> CacheService:
    """初始化全局缓存服务"""
    global _cache_service
    cache_manager = get_cache_manager(backend=backend, **kwargs)
    _cache_service = CacheService(cache_manager)
    return _cache_service