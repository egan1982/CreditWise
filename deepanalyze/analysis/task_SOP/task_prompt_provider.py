# -*- coding: utf-8 -*-
"""
Task Prompt Provider - 任务提示词提供器

为 Chat API 层提供任务说明的自动注入能力，实现：
- 从 SOPRegistry 拉取任务定义
- 生成面向 Chat 的系统提示词片段
- 支持按任务类型筛选
- 支持动态组合基础提示词和任务说明

设计原则：
- 与 Registry 解耦，通过依赖注入获取数据
- 提供多种粒度的提示词生成
- 支持未来新增任务自动生效

使用方式：
    from deepanalyze.analysis.task_SOP.task_prompt_provider import get_prompt_provider
    
    provider = get_prompt_provider()
    system_prompt = provider.build_system_prompt(
        base_prompt="你是一个数据分析助手",
        task_type="rule_mining",  # 可选，指定当前任务
        include_all_tasks=True
    )
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .registry import SOPRegistry
    from .types import SOPTaskDefinition

logger = logging.getLogger(__name__)


# =============================================================================
# Default Prompts
# =============================================================================

DEFAULT_BASE_PROMPT = """你是 CreditWise 信贷风控助手，专注于金融风控领域的数据分析任务。

## 你的能力
- 数据处理与分析（Python、pandas、numpy）
- 统计分析与假设检验
- 机器学习模型开发与评估
- 数据可视化（matplotlib、seaborn）
- 业务洞察与建议

## 响应规范
1. 提供清晰、结构化的回答
2. 适当时包含代码示例（带注释）
3. 用通俗语言解释技术概念
4. 提供可操作的建议

## 约束
- 不要捏造数据或结果
- 存在不确定性时明确说明
- 保持在专业领域范围内"""


TASK_LIST_HEADER = """
## 平台内置功能

以下 SOP 任务可通过自然语言触发，系统会自动执行预定义的分析流程：
"""


TASK_GUIDANCE_HEADER = """
## 当前任务引导

用户正在执行「{task_name}」任务，请按以下流程引导用户：

1. **确认数据文件**：检查用户是否已上传数据文件
2. **确认必需参数**：{required_params_summary}
3. **询问执行模式**：
   - 🚀 **自动模式**：一键执行全部阶段
   - 🔍 **专家模式**：每阶段暂停确认
4. **展示参数确认卡片**：让用户确认或修改参数后开始执行

### 任务详情
- **功能**：{chat_summary}
- **预估耗时**：{estimated_time}
- **执行阶段**：{stages_summary}
"""


# =============================================================================
# Task Prompt Provider
# =============================================================================

class TaskPromptProvider:
    """任务提示词提供器
    
    为 Chat API 层提供任务说明的自动注入能力。
    
    Attributes:
        registry: SOP 任务注册表
    """
    
    def __init__(self, registry: Optional[SOPRegistry] = None):
        """初始化提示词提供器
        
        Args:
            registry: SOP 任务注册表（可选，默认使用全局实例）
        """
        if registry is None:
            from .registry import get_registry
            registry = get_registry()
        self.registry = registry
    
    def get_all_tasks_prompt(self) -> str:
        """获取所有任务的系统提示词片段
        
        Returns:
            包含所有任务说明的提示词片段
        """
        tasks = self.registry.get_all_tasks()
        if not tasks:
            return ""
        
        lines = [TASK_LIST_HEADER]
        
        for idx, (task_id, task_def) in enumerate(tasks.items(), 1):
            task_prompt = self._format_task_summary(task_def, idx)
            lines.append(task_prompt)
        
        return "\n".join(lines)
    
    def get_task_prompt(self, task_id: str) -> str:
        """获取指定任务的详细引导提示词
        
        Args:
            task_id: 任务 ID
            
        Returns:
            任务详细引导提示词，不存在则返回空字符串
        """
        task_def = self.registry.get_task(task_id)
        if not task_def:
            logger.warning(f"Task not found: {task_id}")
            return ""
        
        return self._format_task_guidance(task_def)
    
    def get_tasks_by_category(self, category: str) -> str:
        """按类别获取任务提示词
        
        Args:
            category: 任务类别（如"风控建模"）
            
        Returns:
            该类别下所有任务的提示词片段
        """
        tasks = self.registry.list_tasks(category=category)
        if not tasks:
            return ""
        
        lines = [f"\n### {category} 任务\n"]
        
        for idx, task_info in enumerate(tasks, 1):
            task_def = self.registry.get_task(task_info["task_id"])
            if task_def:
                task_prompt = self._format_task_summary(task_def, idx)
                lines.append(task_prompt)
        
        return "\n".join(lines)
    
    def build_system_prompt(
        self,
        base_prompt: str = "",
        task_type: Optional[str] = None,
        include_all_tasks: bool = True,
        workspace_files: Optional[list[str]] = None
    ) -> str:
        """构建组合后的系统提示词
        
        Args:
            base_prompt: 基础系统提示词（用户配置或默认）
            task_type: 指定任务类型（可选，用于注入特定任务引导）
            include_all_tasks: 是否包含所有可用任务列表（仅在 task_type=None 时生效）
            workspace_files: 工作区文件列表（可选）
            
        Returns:
            组合后的完整系统提示词
            
        逻辑说明：
        - 如果指定了 task_type：只注入该任务的详细参数说明（精准模式）
        - 如果未指定 task_type 且 include_all_tasks=True：注入简化的任务列表（意图识别模式）
        """
        sections = []
        
        # 1. 基础角色定义
        if base_prompt and base_prompt.strip():
            sections.append(base_prompt.strip())
        else:
            sections.append(DEFAULT_BASE_PROMPT)
        
        # 2. 任务说明注入
        if task_type:
            # 精准模式：只注入指定任务的详细参数说明
            task_guidance = self.get_task_prompt(task_type)
            if task_guidance:
                sections.append(task_guidance)
        elif include_all_tasks:
            # 意图识别模式：注入简化的任务列表（用于 LLM 识别用户意图）
            all_tasks_prompt = self.get_all_tasks_prompt_brief()
            if all_tasks_prompt:
                sections.append(all_tasks_prompt)
        
        # 3. 工作区上下文（如果提供）
        if workspace_files:
            files_section = self._format_workspace_files(workspace_files)
            sections.append(files_section)
        
        return "\n\n".join(sections)
    
    def get_all_tasks_prompt_brief(self) -> str:
        """获取所有任务的简化提示词（用于意图识别）
        
        只包含任务名称、触发词和必需参数名，不包含完整的参数 Schema
        
        Returns:
            简化的任务列表提示词
        """
        tasks = self.registry.get_all_tasks()
        if not tasks:
            return ""
        
        lines = [TASK_LIST_HEADER]
        
        for idx, (task_id, task_def) in enumerate(tasks.items(), 1):
            task_prompt = self._format_task_brief(task_def, idx)
            lines.append(task_prompt)
        
        return "\n".join(lines)
    
    def _format_task_brief(self, task_def: SOPTaskDefinition, index: int) -> str:
        """格式化单个任务的简要信息（用于意图识别）
        
        Args:
            task_def: 任务定义
            index: 序号
            
        Returns:
            格式化后的任务简要信息
        """
        # 获取触发词
        trigger_keywords = getattr(task_def, 'trigger_keywords', [])
        keywords_str = "、".join(trigger_keywords[:5]) if trigger_keywords else task_def.task_name
        
        # 获取简短说明
        chat_summary = getattr(task_def, 'chat_summary', '') or task_def.description
        
        # 获取必需参数名称列表
        required_params = []
        if task_def.required_params:
            for p in task_def.required_params:
                if getattr(p, 'required', True):
                    required_params.append(f"{p.name}({p.label})")
        required_str = ", ".join(required_params) if required_params else "无"
        
        return f"""
### {index}. {task_def.task_name} (task_type: "{task_def.task_id}")
- **触发词**：{keywords_str}
- **功能**：{chat_summary}
- **必需参数**：{required_str}"""
    
    def _format_task_summary(self, task_def: SOPTaskDefinition, index: int) -> str:
        """格式化单个任务的摘要信息
        
        Args:
            task_def: 任务定义
            index: 序号
            
        Returns:
            格式化后的任务摘要
        """
        # 获取触发词
        trigger_keywords = getattr(task_def, 'trigger_keywords', [])
        keywords_str = "、".join(trigger_keywords[:5]) if trigger_keywords else task_def.task_name
        
        # 获取简短说明
        chat_summary = getattr(task_def, 'chat_summary', '') or task_def.description
        
        # 获取必需参数说明
        required_params_summary = getattr(task_def, 'required_params_summary', '')
        if not required_params_summary and task_def.required_params:
            param_names = [p.label for p in task_def.required_params if p.required]
            required_params_summary = "、".join(param_names) if param_names else "无"
        
        # 构建参数 JSON Schema（用于 LLM 参数推断）
        params_schema = self._build_params_schema(task_def)
        
        return f"""
### {index}. {task_def.task_name} ({task_def.task_id})
- **功能**：{chat_summary}
- **触发词**：{keywords_str}
- **必需参数**：{required_params_summary}
- **预估耗时**：{task_def.estimated_time}
- **参数格式**：
```json
{params_schema}
```"""
    
    def _build_params_schema(self, task_def: SOPTaskDefinition) -> str:
        """构建任务参数的 JSON Schema 示例
        
        Args:
            task_def: 任务定义
            
        Returns:
            JSON Schema 字符串
        """
        import json
        
        schema = {}
        
        # 处理必需参数
        if task_def.required_params:
            for param in task_def.required_params:
                param_name = param.name
                param_type = getattr(param, 'type', 'string')
                param_desc = param.label
                default = getattr(param, 'default', None)
                
                # 根据类型生成示例值
                if param_type == 'column_select':
                    schema[param_name] = f"<{param_desc}列名>"
                elif param_type == 'column_multi_select':
                    schema[param_name] = [f"<{param_desc}列名1>", f"<{param_desc}列名2>"]
                elif param_type == 'number' or param_type == 'int':
                    schema[param_name] = default if default is not None else 0
                elif param_type == 'float':
                    schema[param_name] = default if default is not None else 0.0
                elif param_type == 'boolean' or param_type == 'bool':
                    schema[param_name] = default if default is not None else False
                elif param_type == 'select':
                    options = getattr(param, 'options', [])
                    if options:
                        schema[param_name] = options[0].get('value', '') if isinstance(options[0], dict) else options[0]
                    else:
                        schema[param_name] = default if default else ""
                else:
                    schema[param_name] = default if default else f"<{param_desc}>"
        
        # 处理可选参数（只显示常用的）
        if task_def.optional_params:
            for param in task_def.optional_params[:5]:  # 最多显示5个可选参数
                param_name = param.name
                param_type = getattr(param, 'type', 'string')
                default = getattr(param, 'default', None)
                
                if default is not None:
                    schema[param_name] = default
        
        return json.dumps(schema, ensure_ascii=False, indent=2)
    
    def _format_task_guidance(self, task_def: SOPTaskDefinition) -> str:
        """格式化任务详细引导（精准模式）
        
        包含完整的参数 Schema，用于 LLM 精确提取参数
        
        Args:
            task_def: 任务定义
            
        Returns:
            格式化后的任务引导提示词
        """
        # 获取简短说明
        chat_summary = getattr(task_def, 'chat_summary', '') or task_def.description
        
        # 获取必需参数说明
        required_params_summary = getattr(task_def, 'required_params_summary', '')
        if not required_params_summary and task_def.required_params:
            param_names = [p.label for p in task_def.required_params if getattr(p, 'required', True)]
            required_params_summary = "、".join(param_names) if param_names else "无"
        
        # 获取阶段摘要
        stages_summary = " → ".join([s.name for s in task_def.stages]) if task_def.stages else "无"
        
        # 构建参数 Schema
        params_schema = self._build_params_schema(task_def)
        
        # 基础引导
        guidance = TASK_GUIDANCE_HEADER.format(
            task_name=task_def.task_name,
            chat_summary=chat_summary,
            required_params_summary=required_params_summary,
            estimated_time=task_def.estimated_time,
            stages_summary=stages_summary
        )
        
        # 追加参数 Schema
        guidance += f"""

### 参数格式（JSON）

请从用户输入中提取以下参数，返回 JSON 格式：

```json
{params_schema}
```

**注意**：
- `task_type` 必须是 `"{task_def.task_id}"`
- 只提取用户明确提供的参数值
- 未提及的参数使用默认值或留空
"""
        
        return guidance
    
    def _format_workspace_files(self, files: list[str]) -> str:
        """格式化工作区文件列表
        
        Args:
            files: 文件路径列表
            
        Returns:
            格式化后的文件列表
        """
        if not files:
            return ""
        
        lines = ["\n## 当前工作区文件\n"]
        for f in files:
            lines.append(f"- {f}")
        
        return "\n".join(lines)


# =============================================================================
# Global Instance
# =============================================================================

_prompt_provider: Optional[TaskPromptProvider] = None


def get_prompt_provider() -> TaskPromptProvider:
    """获取全局提示词提供器实例
    
    Returns:
        TaskPromptProvider 实例
    """
    global _prompt_provider
    if _prompt_provider is None:
        _prompt_provider = TaskPromptProvider()
    return _prompt_provider


def reset_prompt_provider() -> None:
    """重置全局提示词提供器实例（用于测试）"""
    global _prompt_provider
    _prompt_provider = None


# =============================================================================
# Export
# =============================================================================

__all__ = [
    'TaskPromptProvider',
    'get_prompt_provider',
    'reset_prompt_provider',
    'DEFAULT_BASE_PROMPT',
]
