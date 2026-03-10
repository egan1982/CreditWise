"""
统一的缓存系统 - 支持内存和Redis双模式
提供API响应缓存、会话缓存、配置缓存等功能
"""

import json
import time
import asyncio
from typing import Any, Dict, List, Optional, Union
from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass
import hashlib
import logging

logger = logging.getLogger(__name__)


class CacheBackend(str, Enum):
    """缓存后端类型"""
    MEMORY = "memory"
    REDIS = "redis"


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    ttl: int = 300  # 默认5分钟过期
    created_at: float = None
    access_count: int = 0
    last_accessed: float = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()
        if self.last_accessed is None:
            self.last_accessed = time.time()
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl <= 0:  # TTL <= 0 表示永不过期
            return False
        return time.time() - self.created_at > self.ttl
    
    def touch(self):
        """更新访问时间"""
        self.last_accessed = time.time()
        self.access_count += 1


class CacheBackendInterface(ABC):
    """缓存后端接口"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """设置缓存值"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """删除缓存"""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        pass
    
    @abstractmethod
    async def clear(self) -> bool:
        """清空缓存"""
        pass
    
    @abstractmethod
    async def keys(self, pattern: str = "*") -> List[str]:
        """获取匹配模式的键"""
        pass
    
    @abstractmethod
    async def info(self) -> Dict[str, Any]:
        """获取缓存信息"""
        pass


class MemoryCacheBackend(CacheBackendInterface):
    """内存缓存后端"""
    
    def __init__(self, max_size: int = 1000):
        self._cache: Dict[str, CacheEntry] = {}
        self._max_size = max_size
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        async with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            if entry.is_expired():
                del self._cache[key]
                return None
            
            entry.touch()
            return entry.value
    
    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """设置缓存值"""
        async with self._lock:
            # 检查缓存大小限制
            if len(self._cache) >= self._max_size and key not in self._cache:
                await self._evict_lru()
            
            self._cache[key] = CacheEntry(key=key, value=value, ttl=ttl)
            return True
    
    async def delete(self, key: str) -> bool:
        """删除缓存"""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    async def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        async with self._lock:
            if key not in self._cache:
                return False
            
            entry = self._cache[key]
            if entry.is_expired():
                del self._cache[key]
                return False
            
            return True
    
    async def clear(self) -> bool:
        """清空缓存"""
        async with self._lock:
            self._cache.clear()
            return True
    
    async def keys(self, pattern: str = "*") -> List[str]:
        """获取匹配模式的键"""
        async with self._lock:
            import fnmatch
            keys = []
            expired_keys = []
            
            for key in self._cache:
                if fnmatch.fnmatch(key, pattern):
                    if not self._cache[key].is_expired():
                        keys.append(key)
                    else:
                        expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
            
            return keys
    
    async def info(self) -> Dict[str, Any]:
        """获取缓存信息"""
        async with self._lock:
            # 清理过期条目
            expired_keys = []
            for key, entry in self._cache.items():
                if entry.is_expired():
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
            
            total_hits = sum(entry.access_count for entry in self._cache.values())
            
            return {
                "backend": "memory",
                "size": len(self._cache),
                "max_size": self._max_size,
                "total_hits": total_hits,
                "memory_usage": "N/A"  # 内存使用量需要更复杂的计算
            }
    
    async def _evict_lru(self):
        """LRU淘汰策略"""
        if not self._cache:
            return
        
        # 找出最久未访问的条目
        lru_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].last_accessed
        )
        
        del self._cache[lru_key]


class RedisCacheBackend(CacheBackendInterface):
    """Redis缓存后端"""
    
    def __init__(self, host: str = "localhost", port: int = 6379, 
                 db: int = 0, password: Optional[str] = None,
                 connection_timeout: int = 5):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.connection_timeout = connection_timeout
        self._redis = None
        self._connected = False
    
    async def _connect(self):
        """连接Redis"""
        if self._connected and self._redis:
            return
        
        try:
            import redis.asyncio as redis
            self._redis = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                socket_connect_timeout=self.connection_timeout,
                decode_responses=True
            )
            await self._redis.ping()
            self._connected = True
            logger.info(f"连接Redis成功: {self.host}:{self.port}/{self.db}")
        except Exception as e:
            logger.error(f"连接Redis失败: {e}")
            self._connected = False
            raise ConnectionError(f"Redis连接失败: {e}")
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        try:
            await self._connect()
            if not self._connected:
                return None
            
            value = await self._redis.get(key)
            if value is None:
                return None
            
            # 反序列化
            return json.loads(value)
        except Exception as e:
            logger.error(f"Redis GET失败: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """设置缓存值"""
        try:
            await self._connect()
            if not self._connected:
                return False
            
            # 序列化
            serialized_value = json.dumps(value, ensure_ascii=False)
            
            # 设置缓存和过期时间
            if ttl > 0:
                result = await self._redis.setex(key, ttl, serialized_value)
            else:  # TTL <= 0 表示永不过期
                result = await self._redis.set(key, serialized_value)
            
            return bool(result)
        except Exception as e:
            logger.error(f"Redis SET失败: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """删除缓存"""
        try:
            await self._connect()
            if not self._connected:
                return False
            
            result = await self._redis.delete(key)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis DELETE失败: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        try:
            await self._connect()
            if not self._connected:
                return False
            
            result = await self._redis.exists(key)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis EXISTS失败: {e}")
            return False
    
    async def clear(self) -> bool:
        """清空缓存"""
        try:
            await self._connect()
            if not self._connected:
                return False
            
            # 只清空当前DB的缓存，不影响其他DB
            result = await self._redis.flushdb()
            return bool(result)
        except Exception as e:
            logger.error(f"Redis CLEAR失败: {e}")
            return False
    
    async def keys(self, pattern: str = "*") -> List[str]:
        """获取匹配模式的键"""
        try:
            await self._connect()
            if not self._connected:
                return []
            
            keys = await self._redis.keys(pattern)
            return keys
        except Exception as e:
            logger.error(f"Redis KEYS失败: {e}")
            return []
    
    async def info(self) -> Dict[str, Any]:
        """获取缓存信息"""
        try:
            await self._connect()
            if not self._connected:
                return {"backend": "redis", "connected": False}
            
            # 获取Redis信息
            info = await self._redis.info()
            
            return {
                "backend": "redis",
                "connected": True,
                "used_memory": info.get("used_memory_human", "N/A"),
                "used_memory_bytes": info.get("used_memory", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "connected_clients": info.get("connected_clients", 0),
                "db_size": await self._redis.dbsize()
            }
        except Exception as e:
            logger.error(f"Redis INFO失败: {e}")
            return {"backend": "redis", "connected": False, "error": str(e)}


class CacheManager:
    """缓存管理器"""
    
    def __init__(self, backend: CacheBackend = CacheBackend.MEMORY, **kwargs):
        self.backend_type = backend
        
        if backend == CacheBackend.MEMORY:
            max_size = kwargs.get("max_size", 1000)
            self._backend = MemoryCacheBackend(max_size)
        elif backend == CacheBackend.REDIS:
            host = kwargs.get("host", "localhost")
            port = kwargs.get("port", 6379)
            db = kwargs.get("db", 0)
            password = kwargs.get("password")
            connection_timeout = kwargs.get("connection_timeout", 5)
            self._backend = RedisCacheBackend(
                host=host, port=port, db=db, password=password,
                connection_timeout=connection_timeout
            )
        else:
            raise ValueError(f"不支持的缓存后端: {backend}")
        
        self._key_prefix = kwargs.get("key_prefix", "llm_cache:")
        logger.info(f"缓存管理器初始化完成，后端: {backend.value}")
    
    def _make_key(self, key: str) -> str:
        """生成带前缀的键"""
        return f"{self._key_prefix}{key}"
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        return await self._backend.get(self._make_key(key))
    
    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """设置缓存值"""
        return await self._backend.set(self._make_key(key), value, ttl)
    
    async def delete(self, key: str) -> bool:
        """删除缓存"""
        return await self._backend.delete(self._make_key(key))
    
    async def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        return await self._backend.exists(self._make_key(key))
    
    async def clear(self) -> bool:
        """清空缓存"""
        # 对于内存缓存，清空所有缓存
        # 对于Redis缓存，只清空带前缀的缓存
        if self.backend_type == CacheBackend.REDIS:
            keys = await self._backend.keys(f"{self._key_prefix}*")
            if keys:
                import redis.asyncio as redis
                redis_client = self._backend._redis
                await redis_client.delete(*keys)
            return True
        else:
            return await self._backend.clear()
    
    async def keys(self, pattern: str = "*") -> List[str]:
        """获取匹配模式的键（去除前缀）"""
        pattern = f"{self._key_prefix}{pattern}"
        backend_keys = await self._backend.keys(pattern)
        # 去除前缀
        return [key.replace(self._key_prefix, "") for key in backend_keys]
    
    async def info(self) -> Dict[str, Any]:
        """获取缓存信息"""
        info = await self._backend.info()
        info["key_prefix"] = self._key_prefix
        return info
    
    async def get_with_fallback(self, key: str, fallback_func, ttl: int = 300, *args, **kwargs) -> Any:
        """获取缓存，如果不存在则调用fallback函数获取值并缓存"""
        value = await self.get(key)
        if value is not None:
            return value
        
        # 调用fallback函数获取值
        if asyncio.iscoroutinefunction(fallback_func):
            value = await fallback_func(*args, **kwargs)
        else:
            value = fallback_func(*args, **kwargs)
        
        # 缓存值
        if value is not None:
            await self.set(key, value, ttl)
        
        return value
    
    def generate_request_cache_key(self, method: str, url: str, params: Dict[str, Any], data: Dict[str, Any]) -> str:
        """为API请求生成缓存键"""
        # 创建请求内容的字符串表示
        content = f"{method}:{url}:{json.dumps(params, sort_keys=True)}:{json.dumps(data, sort_keys=True)}"
        
        # 生成MD5哈希
        hash_obj = hashlib.md5(content.encode('utf-8'))
        return f"request:{hash_obj.hexdigest()}"


# 全局缓存管理器实例
_cache_manager: Optional[CacheManager] = None


def get_cache_manager(backend: CacheBackend = CacheBackend.MEMORY, **kwargs) -> CacheManager:
    """获取全局缓存管理器实例"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager(backend=backend, **kwargs)
    return _cache_manager


def init_cache(backend: CacheBackend = CacheBackend.MEMORY, **kwargs):
    """初始化全局缓存管理器"""
    global _cache_manager
    _cache_manager = CacheManager(backend=backend, **kwargs)
    return _cache_manager


# 辅助函数
def is_redis_available(host: str = "localhost", port: int = 6379, **kwargs) -> bool:
    """检查Redis是否可用"""
    try:
        import redis
        client = redis.Redis(
            host=host, port=port, 
            socket_connect_timeout=kwargs.get("connection_timeout", 2)
        )
        client.ping()
        return True
    except Exception:
        return False


def get_default_cache_backend(**redis_config) -> CacheBackend:
    """获取默认的缓存后端（Redis可用则使用Redis，否则使用内存）"""
    if is_redis_available(**redis_config):
        return CacheBackend.REDIS
    else:
        return CacheBackend.MEMORY