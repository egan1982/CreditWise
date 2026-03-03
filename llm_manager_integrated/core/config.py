"""配置管理模块

支持通过环境变量、.env 文件或直接传参进行配置。
所有配置项都有合理的默认值，确保开箱即用。
"""

import os
from typing import Optional, List, Dict, Any
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import Field

# 加载 .env 文件
env_file = Path(__file__).parent.parent.parent / '.env'
if env_file.exists():
    load_dotenv(env_file)


class UIConfig(BaseSettings):
    """前端 UI 配置"""
    
    theme: str = Field(
        default="light",
        description="主题（light, dark）"
    )
    
    language: str = Field(
        default="zh-CN",
        description="语言（zh-CN, en-US）"
    )
    
    features: Dict[str, bool] = Field(
        default_factory=lambda: {
            "channels": True,
            "models": True,
            "logs": True,
            "proxy": True,
        },
        description="功能开关"
    )
    
    model_config = {
        "env_prefix": "UI_",
        "case_sensitive": False,
    }


class Settings(BaseSettings):
    """应用配置类
    
    配置优先级（从高到低）：
    1. 直接传参
    2. 环境变量（带 LLM_MANAGER_ 前缀）
    3. .env 文件
    4. 默认值
    
    示例:
        # 使用默认配置
        settings = Settings()
        
        # 通过环境变量配置
        os.environ['LLM_MANAGER_DATABASE_URL'] = 'sqlite:///./my_db.db'
        settings = Settings()
        
        # 直接传参配置
        settings = Settings(database_url='sqlite:///./my_db.db')
    """
    
    # ========== 部署模式配置 ==========
    deployment_mode: str = Field(
        default="personal",
        description="部署模式（personal, enterprise）"
    )
    
    # ========== 数据库配置 ==========
    database_url: str = Field(
        default="sqlite:///./llm_manager.db",
        description="数据库连接URL（个人模式默认SQLite）"
    )
    
    # 企业模式PostgreSQL配置
    postgres_url: Optional[str] = Field(
        default=None,
        description="企业模式PostgreSQL连接URL"
    )
    
    # ========== 服务配置 ==========
    backend_host: str = Field(
        default="127.0.0.1",
        description="后端服务监听地址"
    )
    
    backend_port: int = Field(
        default=8000,
        description="后端服务端口"
    )
    
    frontend_url: str = Field(
        default="http://localhost:3000",
        description="前端服务地址（用于CORS配置）"
    )
    
    cors_origins: List[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:8000"],
        description="允许的CORS源列表"
    )
    
    # ========== 安全配置 ==========
    encryption_key: Optional[str] = Field(
        default=None,
        description="API密钥加密密钥（Fernet格式）"
    )
    
    # ========== 日志配置 ==========
    log_level: str = Field(
        default="INFO",
        description="日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL）"
    )
    
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="日志格式"
    )
    
    # ========== 应用配置 ==========
    app_title: str = Field(
        default="LLM API Manager",
        description="应用标题"
    )
    
    app_description: str = Field(
        default="集成前端的大模型 API 管理和代理系统",
        description="应用描述"
    )
    
    app_version: str = Field(
        default="2.0.0",
        description="应用版本"
    )
    
    # ========== 环境配置 ==========
    environment: str = Field(
        default="development",
        description="运行环境（development, production, testing）"
    )
    
    debug: bool = Field(
        default=False,
        description="是否启用调试模式"
    )
    
    # ========== Redis配置（企业模式） ==========
    redis_url: Optional[str] = Field(
        default=None,
        description="Redis连接URL（企业模式使用）"
    )
    
    redis_host: str = Field(
        default="localhost",
        description="Redis主机"
    )
    
    redis_port: int = Field(
        default=6379,
        description="Redis端口"
    )
    
    redis_db: int = Field(
        default=0,
        description="Redis数据库"
    )
    
    redis_password: Optional[str] = Field(
        default=None,
        description="Redis密码"
    )
    
    # ========== API 配置 ==========
    api_prefix: str = Field(
        default="/api",
        description="API路由前缀"
    )
    
    api_base_url: str = Field(
        default="http://127.0.0.1:8200/llm-manager",
        description="LLM Manager API基础URL"
    )
    
    api_key: Optional[str] = Field(
        default=None,
        description="内部API密钥"
    )
    
    docs_url: Optional[str] = Field(
        default="/docs",
        description="API文档URL（None则禁用）"
    )
    
    api_timeout: int = Field(
        default=60,
        description="API请求超时时间（秒）"
    )
    
    max_concurrent_requests: int = Field(
        default=100,
        description="最大并发请求数"
    )
    
    # ========== 缓存配置 ==========
    cache_backend: str = Field(
        default="memory",
        description="缓存后端（memory, redis）"
    )
    
    cache_max_size: int = Field(
        default=1000,
        description="缓存最大条目数（内存缓存）"
    )
    
    request_cache_ttl: int = Field(
        default=300,
        description="请求缓存TTL（秒）"
    )
    
    session_cache_ttl: int = Field(
        default=1800,
        description="会话缓存TTL（秒）"
    )
    
    config_cache_ttl: int = Field(
        default=3600,
        description="配置缓存TTL（秒）"
    )
    
    redoc_url: Optional[str] = Field(
        default="/redoc",
        description="ReDoc文档URL（None则禁用）"
    )
    
    # ========== UI 配置 ==========
    ui_config: UIConfig = Field(
        default_factory=UIConfig,
        description="前端 UI 配置"
    )
    
    model_config = {
        "env_prefix": "LLM_MANAGER_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "allow",
    }
        
    def get_database_url(self, custom_url: Optional[str] = None) -> str:
        """获取数据库URL
        
        Args:
            custom_url: 自定义数据库URL，如果提供则优先使用
            
        Returns:
            数据库连接URL
        """
        return custom_url or self.database_url
    
    def get_cors_origins(self, custom_origins: Optional[List[str]] = None) -> List[str]:
        """获取CORS源列表
        
        Args:
            custom_origins: 自定义CORS源列表，如果提供则优先使用
            
        Returns:
            CORS源列表
        """
        if custom_origins:
            return custom_origins
        
        # 合并 frontend_url 和 cors_origins
        origins = set(self.cors_origins)
        if self.frontend_url:
            origins.add(self.frontend_url)
        
        return list(origins)
    
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.environment.lower() == "production"
    
    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.environment.lower() == "development"
    
    def is_testing(self) -> bool:
        """是否为测试环境"""
        return self.environment.lower() == "testing"
    
    def is_personal_mode(self) -> bool:
        """是否为个人模式"""
        return self.deployment_mode.lower() == "personal"
    
    def is_enterprise_mode(self) -> bool:
        """是否为企业模式"""
        return self.deployment_mode.lower() == "enterprise"
    
    def get_effective_database_url(self) -> str:
        """获取有效的数据库URL
        
        根据部署模式返回合适的数据库URL
        
        Returns:
            数据库连接URL
        """
        if self.is_enterprise_mode():
            # 企业模式优先使用PostgreSQL
            if self.postgres_url:
                return self.postgres_url
            elif self.database_url and self.database_url.startswith('postgresql'):
                return self.database_url
            else:
                # 企业模式但未配置PostgreSQL，使用SQLite
                return "sqlite:///./llm_api_manager_enterprise.db"
        else:
            # 个人模式使用SQLite
            return self.database_url or "sqlite:///./llm_api_manager.db"
    
    def get_effective_redis_url(self) -> Optional[str]:
        """获取有效的Redis URL
        
        Returns:
            Redis连接URL或None
        """
        if self.is_enterprise_mode():
            if self.redis_url:
                return self.redis_url
            else:
                # 构建Redis URL
                password_part = f":{self.redis_password}@" if self.redis_password else ""
                return f"redis://{password_part}{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return None
    
    def get_effective_cache_backend(self) -> str:
        """获取有效的缓存后端
        
        Returns:
            缓存后端名称
        """
        if self.is_enterprise_mode() and self.get_effective_redis_url():
            return "redis"
        else:
            return "memory"


# 全局配置实例（使用默认值）
settings = Settings()


def get_settings() -> Settings:
    """获取配置实例
    
    这个函数可以被 FastAPI 的 Depends 使用，
    方便在路由中注入配置。
    
    Returns:
        配置实例
    """
    return settings


def create_settings(**kwargs) -> Settings:
    """创建自定义配置实例
    
    Args:
        **kwargs: 配置参数
        
    Returns:
        配置实例
        
    Example:
        >>> custom_settings = create_settings(
        ...     database_url="sqlite:///./custom.db",
        ...     backend_port=8001
        ... )
    """
    return Settings(**kwargs)


# 别名，保持向后兼容
LLMManagerConfig = Settings
