"""
LLM API Manager - 集成适配器模块

提供多种集成模式的支持：
1. FastAPI后端集成
2. React前端组件集成
"""

from .fastapi import integrate_llm_manager, create_llm_manager_app, configure_cors
from .react import get_component_info, get_react_integration_guide, copy_components_to_project, create_react_integration_file

__all__ = [
    # FastAPI集成
    'integrate_llm_manager',
    'create_llm_manager_app',
    'configure_cors',
    # React集成
    'get_component_info',
    'get_react_integration_guide',
    'copy_components_to_project',
    'create_react_integration_file'
]