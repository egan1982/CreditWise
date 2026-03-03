# -*- coding: utf-8 -*-
"""
Unified Task Router - 统一任务路由器

无论从 SOP 界面还是 Chat 界面进入，最终都通过此路由器调用 Pipeline 执行引擎。
这是 LLM+Pipeline 新架构的核心组件，实现入口统一和执行标准化。

核心功能：
- 参数验证：验证用户提供的参数是否满足任务要求
- 任务路由：将请求路由到正确的 Pipeline 执行
- 来源追踪：记录请求来源（SOP UI / Chat）用于分析
- 结果增强：Chat 来源可选择性生成自然语言解释
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

import pandas as pd

if TYPE_CHECKING:
    from .executor import ExecutionContext
    from .registry import SOPRegistry, SOPTaskDefinition

from .registry import get_registry

logger = logging.getLogger(__name__)


# =============================================================================
# Data Types
# =============================================================================

class EntrySource(str, Enum):
    """入口来源"""
    SOP_UI = "sop_ui"  # SOP 界面入口（表单配置）
    CHAT = "chat"  # Chat 界面入口（自然语言）


@dataclass
class RouteRequest:
    """路由请求"""
    task_type: str  # 任务类型 ID
    params: dict[str, Any]  # 任务参数
    source: EntrySource  # 入口来源
    session_id: str  # 会话 ID
    
    # 数据相关
    file_path: Optional[str] = None  # 数据文件路径
    data: Optional[pd.DataFrame] = None  # 已加载的数据
    
    # 执行模式
    interaction_mode: str = "auto"  # 交互模式: auto, expert
    
    # LLM 配置（用于 Chat 来源的结果解释）
    model: str = "deepseek-chat"
    api_base: str = "http://localhost:8200/v1"
    
    # Chat 入口特有字段
    chat_context: Optional[dict[str, Any]] = None  # 包含 user_message, conversation_history 等
    llm_extraction_result: Optional[dict[str, Any]] = None  # LLM 参数提取结果
    
    # 元数据
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RouteResult:
    """路由结果"""
    success: bool
    execution_id: Optional[str] = None
    error: Optional[str] = None
    validation_errors: list[str] = field(default_factory=list)
    
    # 执行上下文（成功时返回）
    context: Optional["ExecutionContext"] = None
    
    # 自然语言解释（Chat 来源时可选生成）
    explanation: Optional[str] = None


@dataclass
class ValidationResult:
    """参数验证结果"""
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    normalized_params: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Unified Task Router
# =============================================================================

class UnifiedTaskRouter:
    """统一任务路由器
    
    无论从 SOP 界面还是 Chat 界面进入，最终都通过此路由器
    调用 Pipeline 执行引擎。
    
    Attributes:
        registry: SOP 任务注册表
    """
    
    def __init__(self, registry: Optional[SOPRegistry] = None):
        """初始化路由器
        
        Args:
            registry: SOP 任务注册表（可选，默认使用全局实例）
        """
        self.registry = registry or get_registry()
    
    async def route(self, request: RouteRequest) -> RouteResult:
        """路由任务到 Pipeline 执行
        
        Args:
            request: 路由请求
            
        Returns:
            RouteResult: 路由结果
        """
        logger.info(f"[Router] Routing task: {request.task_type}, source: {request.source.value}")
        
        # 1. 验证任务类型
        task_def = self.registry.get_task(request.task_type)
        if not task_def:
            return RouteResult(
                success=False,
                error=f"未知的任务类型: {request.task_type}",
                validation_errors=[f"任务类型 '{request.task_type}' 不存在"]
            )
        
        # 2. 参数验证
        validation = self._validate_params(request.params, task_def)
        if not validation.valid:
            return RouteResult(
                success=False,
                error="参数验证失败",
                validation_errors=validation.errors
            )
        
        # 3. 准备执行参数
        exec_params = validation.normalized_params
        
        # 4. 记录来源元数据
        metadata = dict(request.metadata)
        metadata["entry_source"] = request.source.value
        metadata["routed_at"] = datetime.now().isoformat()
        
        if request.source == EntrySource.CHAT:
            metadata["llm_extracted"] = True
            if request.llm_extraction_result:
                metadata["extraction_confidence"] = request.llm_extraction_result.get("confidence", 0)
            if request.chat_context:
                metadata["user_message"] = request.chat_context.get("user_message", "")[:200]
        
        # 5. 调用 Pipeline 执行
        try:
            from .executor import SOPExecutor, ExecutionStore
            
            executor = SOPExecutor(registry=self.registry)
            
            # 创建执行上下文
            context = ExecutionStore.create(
                task_id=request.task_type,
                session_id=request.session_id,
                params=exec_params,
                data=request.data,
                file_path=request.file_path,
                interaction_mode=request.interaction_mode,
                model=request.model,
                api_base=request.api_base
            )
            
            # 存储元数据
            if hasattr(context, 'metadata'):
                context.metadata = metadata  # type: ignore
            
            logger.info(f"[Router] Created execution context: {context.execution_id}")
            
            # 异步执行任务
            result_context = await executor.execute_async(
                task_id=request.task_type,
                session_id=request.session_id,
                params=exec_params,
                data=request.data,
                file_path=request.file_path,
                execution_id=context.execution_id,
                interaction_mode=request.interaction_mode,
                model=request.model,
                api_base=request.api_base
            )
            
            # 6. 如果是 Chat 来源，可选生成自然语言解释
            explanation = None
            if request.source == EntrySource.CHAT and result_context.status.value == "completed":
                explanation = await self._generate_explanation(result_context, request)
            
            return RouteResult(
                success=result_context.status.value in ("completed", "running", "paused"),
                execution_id=result_context.execution_id,
                context=result_context,
                explanation=explanation
            )
            
        except Exception as e:
            logger.error(f"[Router] Execution failed: {e}", exc_info=True)
            return RouteResult(
                success=False,
                error=str(e),
                validation_errors=[]
            )
    
    def validate_params(self, task_type: str, params: dict[str, Any]) -> ValidationResult:
        """验证任务参数（公开方法，供外部调用）
        
        Args:
            task_type: 任务类型 ID
            params: 待验证的参数
            
        Returns:
            ValidationResult: 验证结果
        """
        task_def = self.registry.get_task(task_type)
        if not task_def:
            return ValidationResult(
                valid=False,
                errors=[f"任务类型 '{task_type}' 不存在"]
            )
        return self._validate_params(params, task_def)
    
    def _validate_params(
        self,
        params: dict[str, Any],
        task_def: "SOPTaskDefinition"
    ) -> ValidationResult:
        """验证参数
        
        Args:
            params: 用户提供的参数
            task_def: 任务定义
            
        Returns:
            ValidationResult: 验证结果
        """
        errors: list[str] = []
        warnings: list[str] = []
        normalized: dict[str, Any] = dict(params)
        
        # 检查必需参数
        for param in task_def.required_params:
            if param.name not in params:
                if param.default is not None:
                    normalized[param.name] = param.default
                    warnings.append(f"参数 '{param.label}' 使用默认值: {param.default}")
                elif not param.allow_empty:
                    errors.append(f"缺少必需参数: {param.label} ({param.name})")
            elif params[param.name] is None or params[param.name] == "":
                if not param.allow_empty:
                    errors.append(f"参数 '{param.label}' 不能为空")
        
        # 验证可选参数的类型和范围
        for param in task_def.optional_params:
            if param.name in params and params[param.name] is not None:
                value = params[param.name]
                
                # 类型验证
                param_type = param.param_type.value
                if param_type in ("integer", "number", "float"):
                    try:
                        if param_type == "integer":
                            normalized[param.name] = int(value)
                        else:
                            normalized[param.name] = float(value)
                    except (ValueError, TypeError):
                        errors.append(f"参数 '{param.label}' 必须是数字类型")
                        continue
                    
                    # 范围验证
                    if param.validation:
                        num_value = normalized[param.name]
                        if param.validation.get("min") is not None and num_value < param.validation["min"]:
                            errors.append(f"参数 '{param.label}' 不能小于 {param.validation['min']}")
                        if param.validation.get("max") is not None and num_value > param.validation["max"]:
                            errors.append(f"参数 '{param.label}' 不能大于 {param.validation['max']}")
                
                elif param_type == "boolean":
                    if isinstance(value, str):
                        normalized[param.name] = value.lower() in ("true", "1", "yes")
                    else:
                        normalized[param.name] = bool(value)
                
                elif param_type == "select" and param.options:
                    valid_values = [opt.get("value") for opt in param.options]
                    if value not in valid_values:
                        errors.append(f"参数 '{param.label}' 的值 '{value}' 不在有效选项中")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            normalized_params=normalized
        )
    
    async def _generate_explanation(
        self,
        context: "ExecutionContext",
        request: RouteRequest
    ) -> Optional[str]:
        """生成自然语言解释
        
        Args:
            context: 执行上下文
            request: 原始请求
            
        Returns:
            自然语言解释文本
        """
        # 简单实现：返回执行摘要
        # 后续可以接入 LLM 生成更详细的解释
        try:
            task_def = self.registry.get_task(context.task_id)
            task_name = task_def.task_name if task_def else context.task_id
            
            explanation = f"已完成 **{task_name}** 任务。\n\n"
            
            # 添加阶段摘要
            if context.stages:
                explanation += "### 执行阶段\n\n"
                for stage_id, stage in context.stages.items():
                    status_icon = "✅" if stage.status.value == "completed" else "⏳"
                    time_info = f"（{stage.execution_time_ms}ms）" if stage.execution_time_ms else ""
                    explanation += f"- {status_icon} {stage.stage_name} {time_info}\n"
            
            # 添加输出摘要
            if context.outputs:
                explanation += "\n### 输出结果\n\n"
                for key, value in context.outputs.items():
                    if isinstance(value, pd.DataFrame):
                        explanation += f"- **{key}**: 数据表 ({value.shape[0]} 行, {value.shape[1]} 列)\n"
                    elif isinstance(value, dict):
                        explanation += f"- **{key}**: 字典 ({len(value)} 个键)\n"
                    elif isinstance(value, list):
                        explanation += f"- **{key}**: 列表 ({len(value)} 项)\n"
                    else:
                        explanation += f"- **{key}**: {type(value).__name__}\n"
            
            return explanation
            
        except Exception as e:
            logger.warning(f"[Router] Failed to generate explanation: {e}")
            return None


# =============================================================================
# Factory Function
# =============================================================================

def create_router(registry: Optional[SOPRegistry] = None) -> UnifiedTaskRouter:
    """创建任务路由器实例
    
    Args:
        registry: SOP 任务注册表（可选）
        
    Returns:
        UnifiedTaskRouter: 路由器实例
    """
    return UnifiedTaskRouter(registry=registry)


# =============================================================================
# Convenience Functions
# =============================================================================

async def route_from_sop_ui(
    task_type: str,
    params: dict[str, Any],
    session_id: str,
    file_path: Optional[str] = None,
    data: Optional[pd.DataFrame] = None,
    interaction_mode: str = "auto"
) -> RouteResult:
    """从 SOP UI 入口路由任务
    
    Args:
        task_type: 任务类型
        params: 任务参数
        session_id: 会话 ID
        file_path: 数据文件路径
        data: 已加载的数据
        interaction_mode: 交互模式
        
    Returns:
        RouteResult: 路由结果
    """
    router = create_router()
    request = RouteRequest(
        task_type=task_type,
        params=params,
        source=EntrySource.SOP_UI,
        session_id=session_id,
        file_path=file_path,
        data=data,
        interaction_mode=interaction_mode
    )
    return await router.route(request)


async def route_from_chat(
    task_type: str,
    params: dict[str, Any],
    session_id: str,
    user_message: str,
    file_path: Optional[str] = None,
    data: Optional[pd.DataFrame] = None,
    interaction_mode: str = "auto",
    model: str = "deepseek-chat",
    api_base: str = "http://localhost:8200/v1",
    extraction_result: Optional[dict[str, Any]] = None
) -> RouteResult:
    """从 Chat 入口路由任务
    
    Args:
        task_type: 任务类型
        params: 任务参数
        session_id: 会话 ID
        user_message: 用户原始消息
        file_path: 数据文件路径
        data: 已加载的数据
        interaction_mode: 交互模式
        model: LLM 模型名称
        api_base: LLM API 基础 URL
        extraction_result: LLM 参数提取结果
        
    Returns:
        RouteResult: 路由结果
    """
    router = create_router()
    request = RouteRequest(
        task_type=task_type,
        params=params,
        source=EntrySource.CHAT,
        session_id=session_id,
        file_path=file_path,
        data=data,
        interaction_mode=interaction_mode,
        model=model,
        api_base=api_base,
        chat_context={"user_message": user_message},
        llm_extraction_result=extraction_result
    )
    return await router.route(request)


# =============================================================================
# Export
# =============================================================================

__all__ = [
    'EntrySource',
    'RouteRequest',
    'RouteResult',
    'ValidationResult',
    'UnifiedTaskRouter',
    'create_router',
    'route_from_sop_ui',
    'route_from_chat',
]
