"""
SOP Task Registry - 业务场景SOP任务注册中心

Provides:
- Unified task registration and discovery
- Task metadata management
- Task executor lookup

Note:
- 类型定义已移至 types.py 模块
- 本模块专注于注册和查询逻辑
"""

from typing import List, Dict, Any, Optional, Type
import importlib
import logging

# 从 types.py 导入所有类型定义
from .types import (
    ParamType,
    TaskType,
    ParamDefinition,
    StageDefinition,
    OutputDefinition,
    SOPTaskDefinition,
)

logger = logging.getLogger(__name__)


# =============================================================================
# SOP Registry
# =============================================================================

class SOPRegistry:
    """
    SOP任务注册中心
    
    Singleton pattern for global task registration and discovery.
    """
    
    _instance: Optional['SOPRegistry'] = None
    _tasks: Dict[str, SOPTaskDefinition] = {}
    _executors: Dict[str, Type] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tasks = {}
            cls._instance._executors = {}
        return cls._instance
    
    def register(
        self,
        task_definition: SOPTaskDefinition,
        executor_class: Optional[Type] = None
    ) -> None:
        """
        注册SOP任务
        
        Args:
            task_definition: 任务定义
            executor_class: 执行器类（可选，可后续动态加载）
        """
        task_id = task_definition.task_id
        self._tasks[task_id] = task_definition
        
        if executor_class:
            self._executors[task_id] = executor_class
            
        logger.info(f"Registered SOP task: {task_id} ({task_definition.task_name})")
    
    def register_from_meta(
        self,
        task_meta: Dict[str, Any],
        sop_prompt_template: str = "",
        executor_class: Optional[Type] = None
    ) -> None:
        """
        从元数据字典注册任务
        
        Args:
            task_meta: 任务元数据字典（与 rule_mining_meta.py 格式兼容）
            sop_prompt_template: SOP Prompt模板
            executor_class: 执行器类
        """
        # Convert stages
        stages = [
            StageDefinition(
                id=s.get("id", ""),
                name=s.get("name", ""),
                description=s.get("description", ""),
                progress_weight=s.get("progress_weight", 10)
            )
            for s in task_meta.get("stages", [])
        ]
        
        # Convert required params
        required_params = [
            ParamDefinition(
                name=p.get("name", ""),
                label=p.get("label", ""),
                label_en=p.get("label_en", ""),
                param_type=ParamType(p.get("type", "string")),
                required=p.get("required", True),
                default=p.get("default"),
                description=p.get("description", ""),
                options=p.get("options", []),
                validation={"min": p.get("min"), "max": p.get("max"), "step": p.get("step")}
                    if any(k in p for k in ["min", "max", "step"]) else None,
                allow_empty=p.get("allow_empty", False),
                show_when=p.get("show_when"),
                stage=p.get("stage", ""),
                group=p.get("group", "basic"),
                advanced=p.get("advanced", False)
            )
            for p in task_meta.get("required_params", [])
        ]
        
        # Convert optional params
        optional_params = [
            ParamDefinition(
                name=p.get("name", ""),
                label=p.get("label", ""),
                label_en=p.get("label_en", ""),
                param_type=ParamType(p.get("type", "string")),
                required=False,
                default=p.get("default"),
                description=p.get("description", ""),
                options=p.get("options", []),
                validation={"min": p.get("min"), "max": p.get("max"), "step": p.get("step")}
                    if any(k in p for k in ["min", "max", "step"]) else None,
                allow_empty=p.get("allow_empty", False),
                show_when=p.get("show_when"),
                stage=p.get("stage", ""),
                group=p.get("group", "basic"),
                advanced=p.get("advanced", False)
            )
            for p in task_meta.get("optional_params", [])
        ]
        
        # Convert outputs
        outputs = [
            OutputDefinition(
                id=o.get("id", ""),
                name=o.get("name", ""),
                output_type=o.get("type", "table"),
                show_when=o.get("show_when")
            )
            for o in task_meta.get("outputs", [])
        ]
        
        # Parse task_type
        task_type_str = task_meta.get("task_type", "sop")
        task_type = TaskType(task_type_str) if task_type_str in [t.value for t in TaskType] else TaskType.SOP
        
        # Create task definition
        task_def = SOPTaskDefinition(
            task_id=task_meta.get("task_id", ""),
            task_name=task_meta.get("task_name", ""),
            task_name_en=task_meta.get("task_name_en", ""),
            description=task_meta.get("description", ""),
            category=task_meta.get("category", ""),
            icon=task_meta.get("icon", "target"),
            estimated_time=task_meta.get("estimated_time", "未知"),
            stages=stages,
            required_params=required_params,
            optional_params=optional_params,
            outputs=outputs,
            sop_prompt_template=sop_prompt_template,
            # Chat 入口配置（新增）
            task_type=task_type,
            trigger_keywords=task_meta.get("trigger_keywords", []),
            chat_summary=task_meta.get("chat_summary", ""),
            required_params_summary=task_meta.get("required_params_summary", ""),
        )
        
        self.register(task_def, executor_class)
    
    def unregister(self, task_id: str) -> bool:
        """
        注销SOP任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否成功注销
        """
        if task_id in self._tasks:
            del self._tasks[task_id]
            if task_id in self._executors:
                del self._executors[task_id]
            logger.info(f"Unregistered SOP task: {task_id}")
            return True
        return False
    
    def get_task(self, task_id: str) -> Optional[SOPTaskDefinition]:
        """
        获取任务定义
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务定义，不存在则返回None
        """
        return self._tasks.get(task_id)
    
    def get_all_tasks(self) -> Dict[str, SOPTaskDefinition]:
        """
        获取所有已注册任务
        
        Returns:
            任务ID到任务定义的映射
        """
        return self._tasks.copy()
    
    def list_tasks(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        列出所有任务（简要信息）
        
        Args:
            category: 可选，按分类筛选
            
        Returns:
            任务简要信息列表
        """
        tasks = []
        for task_id, task_def in self._tasks.items():
            if category and task_def.category != category:
                continue
            tasks.append({
                "task_id": task_def.task_id,
                "task_name": task_def.task_name,
                "task_name_en": task_def.task_name_en,
                "description": task_def.description,
                "category": task_def.category,
                "icon": task_def.icon,
                "estimated_time": task_def.estimated_time
            })
        return tasks
    
    def get_executor(self, task_id: str) -> Optional[Type]:
        """
        获取任务执行器类
        
        Args:
            task_id: 任务ID
            
        Returns:
            执行器类，不存在则返回None
        """
        # 直接返回已注册的执行器
        if task_id in self._executors:
            return self._executors[task_id]
        
        # 尝试动态加载
        task_def = self._tasks.get(task_id)
        if task_def and task_def.pipeline_class:
            try:
                module_path, class_name = task_def.pipeline_class.rsplit(".", 1)
                module = importlib.import_module(module_path)
                executor_class = getattr(module, class_name)
                self._executors[task_id] = executor_class
                return executor_class
            except Exception as e:
                logger.error(f"Failed to load executor for {task_id}: {e}")
        
        return None
    
    def get_task_meta_dict(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务元数据（字典格式，用于API响应）
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务元数据字典
        """
        task_def = self._tasks.get(task_id)
        if not task_def:
            return None
        
        return {
            "task_id": task_def.task_id,
            "task_name": task_def.task_name,
            "task_name_en": task_def.task_name_en,
            "description": task_def.description,
            "category": task_def.category,
            "icon": task_def.icon,
            "estimated_time": task_def.estimated_time,
            "stages": [
                {
                    "id": s.id,
                    "name": s.name,
                    "description": s.description,
                    "progress_weight": s.progress_weight
                }
                for s in task_def.stages
            ],
            "required_params": [
                {
                    "name": p.name,
                    "label": p.label,
                    "label_en": p.label_en,
                    "type": p.param_type.value,
                    "required": p.required,
                    "default": p.default,
                    "description": p.description,
                    "options": p.options,
                    "allow_empty": p.allow_empty,
                    "show_when": p.show_when,
                    "stage": p.stage,
                    "group": p.group,
                    "advanced": p.advanced,
                    # 展开 validation 中的 min/max/step 为顶级字段
                    **({"min": p.validation.get("min"), "max": p.validation.get("max"), "step": p.validation.get("step")} if p.validation else {})
                }
                for p in task_def.required_params
            ],
            "optional_params": [
                {
                    "name": p.name,
                    "label": p.label,
                    "label_en": p.label_en,
                    "type": p.param_type.value,
                    "required": False,
                    "default": p.default,
                    "description": p.description,
                    "options": p.options,
                    "allow_empty": p.allow_empty,
                    "show_when": p.show_when,
                    "stage": p.stage,
                    "group": p.group,
                    "advanced": p.advanced,
                    # 展开 validation 中的 min/max/step 为顶级字段
                    **({"min": p.validation.get("min"), "max": p.validation.get("max"), "step": p.validation.get("step")} if p.validation else {})
                }
                for p in task_def.optional_params
            ],
            "outputs": [
                {
                    "id": o.id,
                    "name": o.name,
                    "type": o.output_type,
                    "show_when": o.show_when
                }
                for o in task_def.outputs
            ]
        }
    
    def get_sop_prompt(self, task_id: str) -> Optional[str]:
        """
        获取任务的SOP Prompt模板
        
        Args:
            task_id: 任务ID
            
        Returns:
            SOP Prompt模板
        """
        task_def = self._tasks.get(task_id)
        if task_def:
            return task_def.sop_prompt_template
        return None


# =============================================================================
# Global Registry Instance
# =============================================================================

# 全局注册中心实例
sop_registry = SOPRegistry()


def get_registry() -> SOPRegistry:
    """获取全局注册中心实例"""
    return sop_registry


# =============================================================================
# Auto-Registration
# =============================================================================

def register_builtin_tasks():
    """
    注册内置SOP任务
    
    在模块加载时自动调用，注册所有内置任务
    """
    global sop_registry
    print(f"[SOP Registry] register_builtin_tasks called, registry id: {id(sop_registry)}")
    
    # 检查是否已注册，避免重复注册
    if sop_registry.get_task("rule_mining") is not None:
        logger.debug("rule_mining task already registered, skipping")
        print("[SOP Registry] rule_mining already registered, skipping")
        return
    
    try:
        # 注册规则挖掘任务
        print("[SOP Registry] Importing rule_mining_meta...")
        from .rule_mining_meta import RULE_MINING_TASK_META, RULE_MINING_SOP_PROMPT_TEMPLATE
        print("[SOP Registry] Importing RuleMiningPipeline...")
        from .rule_mining import RuleMiningPipeline
        
        print("[SOP Registry] Registering rule_mining task...")
        sop_registry.register_from_meta(
            task_meta=RULE_MINING_TASK_META,
            sop_prompt_template=RULE_MINING_SOP_PROMPT_TEMPLATE,
            executor_class=RuleMiningPipeline
        )
        logger.info("Registered builtin task: rule_mining")
        print("[SOP Registry] rule_mining registered successfully")
        
    except ImportError as e:
        logger.warning(f"Failed to register rule_mining task: {e}")
        print(f"[SOP Registry ERROR] Failed to import rule_mining: {e}")
        import traceback
        traceback.print_exc()
    
    # 注册评分卡开发任务
    try:
        print("[SOP Registry] Importing scorecard_meta...")
        from .scorecard_meta import SCORECARD_TASK_META, SCORECARD_SOP_PROMPT_TEMPLATE
        print("[SOP Registry] Importing ScorecardPipeline...")
        from .scorecard_development import ScorecardPipeline
        
        print("[SOP Registry] Registering scorecard_dev task...")
        sop_registry.register_from_meta(
            task_meta=SCORECARD_TASK_META,
            sop_prompt_template=SCORECARD_SOP_PROMPT_TEMPLATE,
            executor_class=ScorecardPipeline
        )
        logger.info("Registered builtin task: scorecard_dev")
        print("[SOP Registry] scorecard_dev registered successfully")
        
    except ImportError as e:
        logger.warning(f"Failed to register scorecard task: {e}")
        print(f"[SOP Registry ERROR] Failed to import scorecard: {e}")
        import traceback
        traceback.print_exc()


# =============================================================================
# Export
# =============================================================================

__all__ = [
    # Types (re-exported from types.py)
    'ParamType',
    'TaskType',
    'ParamDefinition',
    'StageDefinition',
    'OutputDefinition',
    'SOPTaskDefinition',
    # Registry
    'SOPRegistry',
    'sop_registry',
    'get_registry',
    # Auto-registration
    'register_builtin_tasks'
]
