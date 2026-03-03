# -*- coding: utf-8 -*-
"""
Task Manager Database

提供数据库连接和会话管理，复用 llm_manager_integrated 的 DatabaseManager 模式。
"""

import os
import logging
from typing import Generator, Optional
from contextlib import contextmanager
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session
from .models import TaskManagerBase

logger = logging.getLogger(__name__)


class TaskManagerDB:
    """任务管理数据库
    
    复用 llm_manager_integrated 的 DatabaseManager 模式。
    支持 SQLite（开发/测试）和 PostgreSQL（生产）。
    
    使用示例:
        db = TaskManagerDB()
        with db.get_session() as session:
            record = session.query(TaskRecord).filter_by(record_id="xxx").first()
    """
    
    def __init__(self, database_url: Optional[str] = None):
        """初始化数据库连接
        
        Args:
            database_url: 数据库连接URL，默认使用环境变量或SQLite
        """
        if database_url is None:
            database_url = os.getenv(
                "TASK_MANAGER_DB_URL",
                "sqlite:///./task_manager.db"
            )
        
        self.database_url = database_url
        self.engine = self._create_engine(database_url)
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        logger.info(f"TaskManagerDB initialized with: {self._safe_url(database_url)}")
    
    def _create_engine(self, database_url: str) -> Engine:
        """创建数据库引擎
        
        Args:
            database_url: 数据库连接URL
            
        Returns:
            SQLAlchemy Engine
        """
        connect_args = {}
        if "sqlite" in database_url:
            # SQLite 需要特殊配置以支持多线程
            connect_args = {"check_same_thread": False}
        
        return create_engine(
            database_url,
            connect_args=connect_args,
            pool_pre_ping=True,  # 连接池健康检查
            echo=False,  # 不打印SQL语句
        )
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """获取数据库会话（上下文管理器）
        
        使用示例:
            with db.get_session() as session:
                session.query(...)
                
        Yields:
            SQLAlchemy Session
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def get_session_generator(self) -> Generator[Session, None, None]:
        """获取数据库会话（生成器，用于FastAPI依赖注入）
        
        Yields:
            SQLAlchemy Session
        """
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()
    
    def create_tables(self):
        """创建所有表"""
        TaskManagerBase.metadata.create_all(bind=self.engine)
        logger.info("TaskManager tables created successfully")
    
    def drop_tables(self):
        """删除所有表（仅用于测试）"""
        TaskManagerBase.metadata.drop_all(bind=self.engine)
        logger.warning("TaskManager tables dropped")
    
    def close(self):
        """关闭数据库连接"""
        self.engine.dispose()
        logger.info("TaskManagerDB connection closed")
    
    def _safe_url(self, url: str) -> str:
        """隐藏URL中的敏感信息"""
        if "@" in url:
            # 隐藏密码
            parts = url.split("@")
            prefix = parts[0].rsplit(":", 1)[0]
            return f"{prefix}:***@{parts[1]}"
        return url


# 全局实例（单例模式）
_task_manager_db: Optional[TaskManagerDB] = None


def get_task_manager_db(database_url: Optional[str] = None) -> TaskManagerDB:
    """获取全局TaskManagerDB实例
    
    Args:
        database_url: 可选的数据库URL，仅在首次调用时生效
        
    Returns:
        TaskManagerDB实例
    """
    global _task_manager_db
    
    if database_url:
        # 如果提供了URL，创建新实例（用于测试）
        return TaskManagerDB(database_url)
    
    if _task_manager_db is None:
        _task_manager_db = TaskManagerDB()
        _task_manager_db.create_tables()
    
    return _task_manager_db


def reset_task_manager_db():
    """重置全局实例（仅用于测试）"""
    global _task_manager_db
    if _task_manager_db:
        _task_manager_db.close()
    _task_manager_db = None
