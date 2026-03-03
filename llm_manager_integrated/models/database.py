"""数据库连接和会话管理

提供灵活的数据库配置，支持：
1. 使用默认配置
2. 通过环境变量配置
3. 通过参数直接配置
"""

from typing import Generator, Optional
from sqlalchemy import create_engine, Engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# SQLAlchemy Base
Base = declarative_base()


class DatabaseManager:
    """数据库管理器
    
    负责创建和管理数据库连接。
    
    Attributes:
        engine: SQLAlchemy 引擎
        SessionLocal: 会话工厂
        
    Example:
        >>> # 使用默认配置
        >>> db_manager = DatabaseManager()
        >>> 
        >>> # 使用自定义配置
        >>> db_manager = DatabaseManager(database_url="sqlite:///./custom.db")
        >>> 
        >>> # 获取会话
        >>> for db in db_manager.get_db():
        ...     # 使用 db 进行数据库操作
        ...     pass
    """
    
    def __init__(self, database_url: Optional[str] = None):
        """初始化数据库管理器
        
        Args:
            database_url: 数据库连接URL。如果为 None，则从配置中获取。
        """
        if database_url is None:
            from ..core.config import settings
            
            # 检查是否配置了企业模式的PostgreSQL
            if hasattr(settings, 'enterprise_mode') and settings.enterprise_mode:
                if hasattr(settings, 'postgres_url') and settings.postgres_url:
                    database_url = settings.postgres_url
                elif hasattr(settings, 'database_url') and settings.database_url.startswith('postgresql'):
                    database_url = settings.database_url
                else:
                    # 企业模式但未配置PostgreSQL，使用SQLite作为默认
                    database_url = "sqlite:///./llm_api_manager_enterprise.db"
            else:
                # 个人模式，使用SQLite
                database_url = settings.database_url or "sqlite:///./llm_api_manager.db"
        
        self.database_url = database_url
        self.engine = self._create_engine(database_url)
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
    
    def _create_engine(self, database_url: str) -> Engine:
        """创建数据库引擎
        
        Args:
            database_url: 数据库连接URL
            
        Returns:
            SQLAlchemy 引擎
        """
        # SQLite 需要特殊配置
        connect_args = {}
        if "sqlite" in database_url:
            connect_args = {"check_same_thread": False}
        
        return create_engine(
            database_url,
            connect_args=connect_args,
            pool_pre_ping=True,  # 连接池健康检查
        )
    
    def get_db(self) -> Generator[Session, None, None]:
        """获取数据库会话
        
        这是一个生成器函数，用于 FastAPI 的依赖注入。
        
        Yields:
            数据库会话
            
        Example:
            >>> from fastapi import Depends
            >>> 
            >>> @app.get("/items")
            >>> def get_items(db: Session = Depends(db_manager.get_db)):
            ...     return db.query(Item).all()
        """
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    def get_session(self):
        """获取数据库会话上下文管理器
        
        用于 with 语句的上下文管理器，确保会话正确关闭。
        
        Returns:
            上下文管理器，可用于 with 语句
            
        Example:
            >>> with db_manager.get_session() as db:
            ...     # 使用 db 进行数据库操作
            ...     channels = db.query(Channel).all()
        """
        from contextlib import contextmanager
        
        @contextmanager
        def session_manager():
            db = self.SessionLocal()
            try:
                yield db
                db.commit()
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()
        
        return session_manager()
    
    def create_tables(self):
        """创建所有数据库表"""
        Base.metadata.create_all(bind=self.engine)
    
    def drop_tables(self):
        """删除所有数据库表（谨慎使用！）"""
        Base.metadata.drop_all(bind=self.engine)
    
    def close(self):
        """关闭数据库连接"""
        self.engine.dispose()


# 全局数据库管理器实例（延迟初始化）
_db_manager: Optional[DatabaseManager] = None


def get_db_manager(database_url: Optional[str] = None) -> DatabaseManager:
    """获取全局数据库管理器实例
    
    Args:
        database_url: 可选的数据库URL。如果提供，将创建新实例。
        
    Returns:
        数据库管理器实例
    """
    global _db_manager
    
    if database_url:
        return DatabaseManager(database_url)
    
    if _db_manager is None:
        _db_manager = DatabaseManager()
    
    return _db_manager


def get_db(database_url: Optional[str] = None) -> Generator[Session, None, None]:
    """获取数据库会话（便捷函数）
    
    这个函数可以直接用于 FastAPI 的依赖注入。
    
    Args:
        database_url: 可选的数据库URL
        
    Yields:
        数据库会话
        
    Example:
        >>> from fastapi import Depends
        >>> 
        >>> @app.get("/items")
        >>> def get_items(db: Session = Depends(get_db)):
        ...     return db.query(Item).all()
    """
    manager = get_db_manager(database_url)
    yield from manager.get_db()


def init_db(database_url: Optional[str] = None):
    """初始化数据库（创建所有表）
    
    Args:
        database_url: 可选的数据库URL
    """
    manager = get_db_manager(database_url)
    manager.create_tables()


# 向后兼容：保持原有的导出方式
def create_db_engine(database_url: str) -> Engine:
    """创建数据库引擎（向后兼容）
    
    Args:
        database_url: 数据库连接URL
        
    Returns:
        SQLAlchemy 引擎
    """
    manager = DatabaseManager(database_url)
    return manager.engine


def create_session_factory(engine: Engine):
    """创建会话工厂（向后兼容）
    
    Args:
        engine: SQLAlchemy 引擎
        
    Returns:
        会话工厂
    """
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)
