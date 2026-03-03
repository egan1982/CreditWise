"""
LLM API Manager - 大模型 API 管理和代理系统

一个模块化的、可集成的大模型 API 管理和代理系统，专为集成到目标项目设计。

新架构特点：
1. 后端API模块：纯API功能，无前端静态文件
2. React组件库：可独立集成的React组件
3. 集成适配器：简化的集成接口

使用方式：

# 1. 后端API集成
from llm_api_manager.api import create_pure_api_app, mount_to_fastapi
app = FastAPI()
llm_app = mount_to_fastapi(app, prefix="/api/llm-manager")

# 2. React组件集成
import { ChannelManager } from 'llm_api_manager/react-components'
<ChannelManager apiEndpoint="/api/llm-manager/channels" />

# 3. 使用集成适配器
from llm_api_manager.integration.fastapi import integrate_llm_manager
app = FastAPI()
integrate_llm_manager(app)

# 4. 编程接口使用
from llm_api_manager.models.database import DatabaseManager
from llm_api_manager.core import crud
db_manager = DatabaseManager("sqlite:///./my_db.db")
db = db_manager.get_session()
"""

from .__version__ import __version__

# 后端API模块
from .api import create_app, create_standalone_app, create_subapp
try:
    from .api import create_pure_api_app, mount_to_fastapi
except ImportError:
    # 如果pure_app不存在，从create_app导入
    from .api.create_app import create_api_app as create_pure_api_app
    from .api.create_app import mount_to_fastapi

from .api import channels, logs, monitoring, responses

# 集成适配器（可选）
try:
    from .integration.fastapi import integrate_llm_manager, create_llm_manager_app, configure_cors
except ImportError:
    pass

try:
    from .integration.react import get_component_info, get_react_integration_guide, copy_components_to_project, create_react_integration_file
except ImportError:
    pass

# 资源管理（可选）
try:
    from .resources import get_resource_path, get_docs_path, get_examples_path
except ImportError:
    pass

__all__ = [
    # 版本
    '__version__',
    
    # 后端API（推荐用于集成）
    'create_pure_api_app',
    'mount_to_fastapi',
    
    # 后端API（兼容性）
    'create_app',
    'create_standalone_app',
    'create_subapp',
    
    # 路由模块
    'channels',
    'logs',
    'proxy',
    'monitoring',
    
    # 集成适配器
    'integrate_llm_manager',
    'create_llm_manager_app',
    'configure_cors',
    'get_component_info',
    'get_react_integration_guide',
    'copy_components_to_project',
    'create_react_integration_file',
    
    # 资源管理
    'get_resource_path',
    'get_docs_path',
    'get_examples_path',
]
