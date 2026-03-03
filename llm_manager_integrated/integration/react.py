"""
React集成适配器

提供React组件的集成信息和方法
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional


def get_component_info() -> Dict[str, Any]:
    """
    获取React组件信息
    
    Returns:
        组件信息字典
    """
    # 获取组件目录路径
    current_dir = Path(__file__).parent.parent
    components_dir = current_dir / "react-components"
    
    if not components_dir.exists():
        return {
            "available": False,
            "message": "React组件不可用"
        }
    
    # 读取组件配置
    package_file = components_dir / "package.json"
    if package_file.exists():
        with open(package_file, 'r') as f:
            package_info = json.load(f)
        
        return {
            "available": True,
            "path": str(components_dir),
            "package": package_info,
            "components": [
                {
                    "name": "ChannelManager",
                    "file": "src/ChannelManager.js",
                    "description": "渠道管理组件"
                },
                {
                    "name": "APILogs",
                    "file": "src/APILogs.js",
                    "description": "API日志组件"
                },
                {
                    "name": "Statistics",
                    "file": "src/Statistics.js",
                    "description": "统计分析组件"
                }
            ]
        }
    
    return {
        "available": True,
        "path": str(components_dir),
        "components": ["ChannelManager", "APILogs", "Statistics"]
    }


def get_react_integration_guide() -> str:
    """
    获取React集成指南
    
    Returns:
        集成指南字符串
    """
    return """
# React集成指南

## 1. 安装组件库

将llm_api_manager/react-components目录复制到您的项目中，或者使用npm:

```bash
npm install llm-api-manager-react-components
```

## 2. 设置Provider

在您的应用根组件中包装LLMManagerProvider:

```jsx
import React from 'react';
import { LLMManagerProvider } from 'llm-api-manager-react-components';

function App() {
  return (
    <LLMManagerProvider
      headers={{
        'Authorization': 'Bearer your-token'
      }}
      theme={{
        primaryColor: '#007bff',
        successColor: '#28a745',
        dangerColor: '#dc3545'
      }}
    >
      {/* 您的应用内容 */}
    </LLMManagerProvider>
  );
}
```

## 3. 使用组件

```jsx
import React from 'react';
import { ChannelManager, APILogs, Statistics } from 'llm-api-manager-react-components';

function Dashboard() {
  return (
    <div>
      <ChannelManager 
        apiEndpoint="/api/llm-manager/channels"
      />
      <APILogs 
        apiEndpoint="/api/llm-manager/logs"
      />
      <Statistics 
        apiEndpoint="/api/llm-manager/stats"
      />
    </div>
  );
}
```

## 4. 自定义样式和主题

您可以通过属性自定义组件样式和主题:

```jsx
<ChannelManager 
  customStyles={{
    container: { backgroundColor: '#f8f9fa' }
  }}
  theme={{
    primaryColor: '#6f42c1'
  }}
/>
```
"""


def copy_components_to_project(project_path: str, components: Optional[list] = None) -> bool:
    """
    复制组件到项目
    
    Args:
        project_path: 目标项目路径
        components: 要复制的组件列表，None表示复制所有
        
    Returns:
        是否成功
    """
    try:
        import shutil
        
        current_dir = Path(__file__).parent.parent
        components_dir = current_dir / "react-components"
        target_dir = Path(project_path) / "llm-manager-components"
        
        # 创建目标目录
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # 复制所有组件
        if components is None:
            # 复制src目录和package.json
            src_dir = components_dir / "src"
            if src_dir.exists():
                shutil.copytree(src_dir, target_dir / "src", dirs_exist_ok=True)
            
            package_file = components_dir / "package.json"
            if package_file.exists():
                shutil.copy2(package_file, target_dir)
            
            # 复制其他重要文件
            for file in ["README.md", ".babelrc"]:
                file_path = components_dir / file
                if file_path.exists():
                    shutil.copy2(file_path, target_dir)
        else:
            # 只复制指定组件
            src_dir = components_dir / "src"
            target_src_dir = target_dir / "src"
            target_src_dir.mkdir(parents=True, exist_ok=True)
            
            for component in components:
                component_file = src_dir / f"{component}.js"
                if component_file.exists():
                    shutil.copy2(component_file, target_src_dir)
        
        return True
    
    except Exception as e:
        print(f"复制组件失败: {e}")
        return False


def create_react_integration_file(project_path: str, api_endpoint: str = "/api/llm-manager") -> str:
    """
    创建React集成示例文件
    
    Args:
        project_path: 项目路径
        api_endpoint: API端点
        
    Returns:
        创建的文件路径
    """
    project_dir = Path(project_path)
    example_file = project_dir / "LLMManagerExample.js"
    
    example_content = f'''/**
 * LLM Manager React集成示例
 */

import React from 'react';
import {{ LLMManagerProvider, ChannelManager, APILogs, Statistics }} from './llm-manager-components';

function LLMManagerExample() {{
  return (
    <LLMManagerProvider
      headers={{}}
      theme={{}}
    >
      <div style={{{ padding: '20px' }}}>
        <h1>LLM Manager 集成示例</h1>
        
        <div style={{{ marginBottom: '30px' }}}>
          <h2>渠道管理</h2>
          <ChannelManager apiEndpoint="{api_endpoint}/channels" />
        </div>
        
        <div style={{{ marginBottom: '30px' }}}>
          <h2>API调用日志</h2>
          <APILogs apiEndpoint="{api_endpoint}/logs" />
        </div>
        
        <div style={{{ marginBottom: '30px' }}}>
          <h2>统计分析</h2>
          <Statistics apiEndpoint="{api_endpoint}/stats" />
        </div>
      </div>
    </LLMManagerProvider>
  );
}}

export default LLMManagerExample;
'''
    
    with open(example_file, 'w') as f:
        f.write(example_content)
    
    return str(example_file)