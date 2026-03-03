"""
模型列表代理路由 - 提供OpenAI兼容的模型列表接口（已废弃，保留作为备用参考）

⚠️ DEPRECATED: 此模块已废弃，保留作为备用参考。

功能迁移说明：
- /models → 已迁移到 Chat API (/v1/models)
- /models/cache/* → 已迁移到 monitoring (/llm-manager/api/monitoring/models/cache/*)

推荐使用新端点，此模块将在未来版本移除。
"""

import logging
import time
import threading
from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass, field

from fastapi import APIRouter, HTTPException, Depends
from llm_manager_integrated.models.schemas import ModelObject, ModelsListResponse
from llm_manager_integrated.core.config import settings
from llm_manager_integrated.models.database import DatabaseManager

router = APIRouter()
logger = logging.getLogger(__name__)

# 数据库管理器实例
db_manager = DatabaseManager()


# ============================================================
# 缓存配置
# ============================================================

# 缓存过期时间（秒）- 可通过环境变量配置
MODELS_CACHE_TTL = int(getattr(settings, 'MODELS_CACHE_TTL', 300))  # 默认5分钟

# 缓存最大条目数
MODELS_CACHE_MAX_SIZE = int(getattr(settings, 'MODELS_CACHE_MAX_SIZE', 100))


# ============================================================
# 缓存实现
# ============================================================

@dataclass
class CacheEntry:
    """缓存条目"""
    data: List[ModelObject]
    created_at: float
    ttl: float
    
    def is_expired(self) -> bool:
        """检查缓存是否过期"""
        return time.time() - self.created_at > self.ttl


@dataclass
class CacheStats:
    """缓存统计信息"""
    hits: int = 0
    misses: int = 0
    refreshes: int = 0
    last_refresh_time: Optional[float] = None
    
    @property
    def hit_rate(self) -> float:
        """计算缓存命中率"""
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / total * 100
    
    def record_hit(self):
        """记录缓存命中"""
        self.hits += 1
    
    def record_miss(self):
        """记录缓存未命中"""
        self.misses += 1
    
    def record_refresh(self):
        """记录缓存刷新"""
        self.refreshes += 1
        self.last_refresh_time = time.time()


class ModelsCache:
    """
    模型列表缓存管理器
    
    特性：
    - TTL过期机制
    - 线程安全
    - 按查询参数分离缓存
    - 缓存统计监控
    """
    
    def __init__(self, default_ttl: float = MODELS_CACHE_TTL, max_size: int = MODELS_CACHE_MAX_SIZE):
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._default_ttl = default_ttl
        self._max_size = max_size
        self._stats = CacheStats()
    
    def _make_key(self, proxy_type: Optional[str], include_unavailable: bool) -> str:
        """生成缓存键"""
        return f"{proxy_type or 'all'}:{include_unavailable}"
    
    def get(self, proxy_type: Optional[str], include_unavailable: bool) -> Optional[List[ModelObject]]:
        """
        获取缓存数据
        
        Returns:
            缓存的模型列表，如果未命中或已过期则返回None
        """
        key = self._make_key(proxy_type, include_unavailable)
        
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._stats.record_miss()
                logger.debug(f"Cache miss for key: {key}")
                return None
            
            if entry.is_expired():
                self._stats.record_miss()
                del self._cache[key]
                logger.debug(f"Cache expired for key: {key}")
                return None
            
            self._stats.record_hit()
            logger.debug(f"Cache hit for key: {key}")
            return entry.data
    
    def set(self, proxy_type: Optional[str], include_unavailable: bool, 
            data: List[ModelObject], ttl: Optional[float] = None):
        """
        设置缓存数据
        
        Args:
            proxy_type: 代理类型过滤
            include_unavailable: 是否包含不可用模型
            data: 模型列表数据
            ttl: 可选的自定义TTL
        """
        key = self._make_key(proxy_type, include_unavailable)
        actual_ttl = ttl if ttl is not None else self._default_ttl
        
        with self._lock:
            # 检查缓存大小，必要时清理最旧的条目
            if len(self._cache) >= self._max_size:
                self._evict_oldest()
            
            self._cache[key] = CacheEntry(
                data=data,
                created_at=time.time(),
                ttl=actual_ttl
            )
            logger.debug(f"Cache set for key: {key}, TTL: {actual_ttl}s")
    
    def invalidate(self, proxy_type: Optional[str] = None, include_unavailable: Optional[bool] = None):
        """
        使缓存失效
        
        Args:
            proxy_type: 指定代理类型，None表示所有
            include_unavailable: 指定过滤条件，None表示所有
        """
        with self._lock:
            if proxy_type is None and include_unavailable is None:
                # 清除所有缓存
                self._cache.clear()
                self._stats.record_refresh()
                logger.info("All cache invalidated")
            else:
                # 清除匹配的缓存
                keys_to_remove = []
                for key in self._cache.keys():
                    parts = key.split(":")
                    if len(parts) == 2:
                        cached_type, cached_unavailable = parts
                        if (proxy_type is None or cached_type == (proxy_type or 'all')) and \
                           (include_unavailable is None or cached_unavailable == str(include_unavailable)):
                            keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    del self._cache[key]
                    self._stats.record_refresh()
                
                logger.info(f"Cache invalidated for {len(keys_to_remove)} entries")
    
    def _evict_oldest(self):
        """清除最旧的缓存条目"""
        if not self._cache:
            return
        
        oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].created_at)
        del self._cache[oldest_key]
        logger.debug(f"Evicted oldest cache entry: {oldest_key}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self._lock:
            return {
                "hits": self._stats.hits,
                "misses": self._stats.misses,
                "hit_rate": round(self._stats.hit_rate, 2),
                "refreshes": self._stats.refreshes,
                "last_refresh_time": self._stats.last_refresh_time,
                "cache_size": len(self._cache),
                "max_size": self._max_size,
                "default_ttl": self._default_ttl,
                "cached_keys": list(self._cache.keys())
            }
    
    def reset_stats(self):
        """重置统计信息"""
        with self._lock:
            self._stats = CacheStats()
            logger.info("Cache stats reset")


# 全局缓存实例
_models_cache = ModelsCache()


def get_db():
    """获取数据库会话"""
    with db_manager.get_session() as db:
        yield db


# ============================================================
# API端点
# ============================================================

@router.get("/models", response_model=ModelsListResponse)
async def list_models(
    proxy_type: Optional[str] = None,  # 可选，指定特定类型
    include_unavailable: bool = False,  # 是否包含不可用模型
    refresh_cache: bool = False,  # 是否刷新缓存
    db = Depends(get_db)
):
    """
    OpenAI兼容的模型列表接口
    
    从激活的渠道配置中获取可用模型列表，支持缓存和刷新机制
    
    Parameters:
    - proxy_type: 按供应商类型过滤（如 openai, deepseek, googleai）
    - include_unavailable: 是否包含未激活的渠道模型
    - refresh_cache: 强制刷新缓存
    
    缓存机制：
    - 默认缓存TTL: 5分钟
    - 支持按查询参数分离缓存
    - 通过 refresh_cache=true 强制刷新
    """
    start_time = time.time()
    
    try:
        # 如果不强制刷新，尝试从缓存获取
        if not refresh_cache:
            cached_data = _models_cache.get(proxy_type, include_unavailable)
            if cached_data is not None:
                elapsed = (time.time() - start_time) * 1000
                logger.info(f"Models list served from cache in {elapsed:.2f}ms")
                return ModelsListResponse(object="list", data=cached_data)
        else:
            # 强制刷新时，先使对应缓存失效
            _models_cache.invalidate(proxy_type, include_unavailable)
        
        # 缓存未命中或强制刷新，从数据库获取
        from llm_manager_integrated.core.crud import get_active_channels
        
        channels = get_active_channels(db)
        model_list = []
        
        for channel in channels:
            # 跳过不可用渠道（如果include_unavailable为False）
            if not include_unavailable and not channel.status:
                continue
                
            # 跳过指定代理类型之外的渠道（如果设置了proxy_type）
            if proxy_type and channel.type != proxy_type:
                continue
                
            # 处理渠道的模型列表（以逗号分隔）
            if channel.models:
                models = [model.strip() for model in channel.models.split(",")]
                for model_name in models:
                    if model_name:
                        model_list.append(
                            ModelObject(
                                id=model_name,
                                created=int(datetime.utcnow().timestamp()),
                                owned_by=channel.type or "unknown"
                            )
                        )
        
        # 如果没有找到任何模型，返回默认模型列表
        if not model_list:
            model_list = _get_default_models()
        
        # 存入缓存
        _models_cache.set(proxy_type, include_unavailable, model_list)
        
        elapsed = (time.time() - start_time) * 1000
        logger.info(f"Models list fetched from database in {elapsed:.2f}ms, {len(model_list)} models")
        
        return ModelsListResponse(object="list", data=model_list)
        
    except Exception as e:
        logger.error(f"获取模型列表失败: {e}")
        # 出现错误时返回默认模型列表
        return ModelsListResponse(object="list", data=_get_default_models())


@router.get("/models/cache/stats")
async def get_cache_stats():
    """
    获取模型缓存统计信息
    
    返回缓存命中率、缓存大小等监控指标
    """
    stats = _models_cache.get_stats()
    return {
        "status": "ok",
        "cache": stats,
        "config": {
            "ttl_seconds": MODELS_CACHE_TTL,
            "max_size": MODELS_CACHE_MAX_SIZE
        }
    }


@router.post("/models/cache/invalidate")
async def invalidate_cache(
    proxy_type: Optional[str] = None,
    include_unavailable: Optional[bool] = None
):
    """
    手动使模型缓存失效
    
    Parameters:
    - proxy_type: 指定代理类型，不传则清除所有
    - include_unavailable: 指定过滤条件，不传则清除所有
    """
    _models_cache.invalidate(proxy_type, include_unavailable)
    return {
        "status": "ok",
        "message": "Cache invalidated",
        "current_stats": _models_cache.get_stats()
    }


@router.post("/models/cache/reset-stats")
async def reset_cache_stats():
    """重置缓存统计信息"""
    _models_cache.reset_stats()
    return {
        "status": "ok",
        "message": "Cache stats reset",
        "current_stats": _models_cache.get_stats()
    }


# ============================================================
# 辅助函数
# ============================================================

def _get_default_models() -> List[ModelObject]:
    """获取默认模型列表"""
    return [
        ModelObject(
            id="gpt-3.5-turbo",
            created=int(datetime.utcnow().timestamp()),
            owned_by="openai"
        ),
        ModelObject(
            id="gpt-4",
            created=int(datetime.utcnow().timestamp()),
            owned_by="openai"
        )
    ]


def invalidate_models_cache():
    """
    外部调用接口：使模型缓存失效
    
    当渠道配置发生变化时调用此函数
    """
    _models_cache.invalidate()
    logger.info("Models cache invalidated via external call")
