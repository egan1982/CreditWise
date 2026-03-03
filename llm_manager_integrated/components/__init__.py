"""
LLM API Manager - 前端组件库

提供可复用的React组件，用于集成到目标项目中。
"""

import os
from pathlib import Path


def get_component_package_path(framework='react'):
    """
    获取组件包路径
    
    Args:
        framework: 前端框架 ('react', 'vue')
    
    Returns:
        组件包路径
    """
    current_dir = Path(__file__).parent
    component_dir = current_dir / framework
    
    if component_dir.exists():
        return str(component_dir)
    
    # 如果组件目录不存在，返回None
    return None


def get_component_info(framework='react'):
    """
    获取组件信息
    
    Args:
        framework: 前端框架
    
    Returns:
        组件信息字典
    """
    component_path = get_component_package_path(framework)
    
    if not component_path:
        return {
            'available': False,
            'message': f'{framework} 组件不可用'
        }
    
    # 读取组件配置
    config_file = Path(component_path) / 'component.json'
    if config_file.exists():
        import json
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        return {
            'available': True,
            'path': component_path,
            'config': config
        }
    
    return {
        'available': True,
        'path': component_path,
        'components': ['ChannelManager', 'APILogs', 'Statistics']
    }