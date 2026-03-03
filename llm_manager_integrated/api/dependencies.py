"""
FastAPI 依赖注入
"""
from fastapi import Depends, Request
from sqlalchemy.orm import Session
from typing import Generator

from llm_manager_integrated.models.database import DatabaseManager
from llm_manager_integrated.core.config import LLMManagerConfig


def get_db_manager(request: Request) -> DatabaseManager:
    """获取数据库管理器"""
    return request.app.state.db_manager


def get_config(request: Request) -> LLMManagerConfig:
    """获取配置对象"""
    return request.app.state.config


def get_db(request: Request) -> Generator[Session, None, None]:
    """获取数据库会话"""
    db_manager = get_db_manager(request)
    yield from db_manager.get_db()
