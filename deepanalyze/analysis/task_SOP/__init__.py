"""
Task SOP (Standard Operating Procedure) Module

Provides standardized task workflows for specific business scenarios:
- Rule Mining: Decision tree based rule generation and evaluation for risk control
- Scorecard Development: Credit scorecard building with WOE/IV and logistic regression (NEW)
- (Future) Strategy Analysis
"""

# Rule Mining Core Classes
from .rule_mining import (
    DataPreprocessor as RuleMiningDataPreprocessor,
    FeatureEngineer,
    SingleVarRuleMiner,
    RuleMiner,
    RuleEvaluator,
    RuleSelector,
    RuleMiningPipeline
)

# Scorecard Development Core Classes (NEW)
from .scorecard_development import (
    DataPreprocessor as ScorecardDataPreprocessor,
    WOETransformer,
    FeatureSelector,
    ScorecardPipeline
)

# Rule Mining Task Metadata
from .rule_mining_meta import (
    RULE_MINING_TASK_META,
    RULE_MINING_SOP_PROMPT_TEMPLATE,
    get_task_meta,
    get_sop_prompt_template,
    build_sop_prompt,
    get_stage_info,
    get_param_info,
    validate_params
)

# SOP Registry - Task Registration Center
from .registry import (
    ParamType,
    TaskType,
    ParamDefinition,
    StageDefinition,
    OutputDefinition,
    SOPTaskDefinition,
    SOPRegistry,
    sop_registry,
    get_registry,
    register_builtin_tasks
)

# Task Prompt Provider - 任务提示词提供器 (NEW)
from .task_prompt_provider import (
    TaskPromptProvider,
    get_prompt_provider,
    reset_prompt_provider,
    DEFAULT_BASE_PROMPT,
)

# SOP Executor - Task Execution Engine
from .executor import (
    ExecutionStatus,
    StageProgress,
    ExecutionContext,
    ExecutionStore,
    SOPExecutor,
    get_executor,
    get_execution_status,
    get_execution_result,
    check_expert_mode_pause,  # 统一的专家模式暂停逻辑
)



# LLM Parameter Extractor - LLM参数推断器 (NEW - LLM+Pipeline架构)
from .llm_param_extractor import (
    TaskIntent,
    ExtractionContext,
    LLMParamExtractor,
    create_param_extractor,
)

# Unified Task Router - 统一任务路由器 (NEW - LLM+Pipeline架构)
from .task_router import (
    EntrySource,
    RouteRequest,
    RouteResult,
    ValidationResult,
    UnifiedTaskRouter,
    create_router,
    route_from_sop_ui,
    route_from_chat,
)

# Code Templates - 伪代码和等效代码生成 (ENHANCED)
from .code_templates import (
    StageCodeGenerator,
    EquivalentCodeGenerator,
    generate_task_config_summary,
    get_code_template,
    format_code_template,
)

# Rule Mining Visualization
from .rule_mining_viz import (
    plot_cumulative_metrics,
    plot_rule_distribution,
    plot_rule_comparison,
    generate_rule_summary_html,
    HAS_MATPLOTLIB,
    HAS_PLOTLY
)
from .rule_mining_viz import get_chart_data_for_frontend as get_rule_mining_chart_data

# Scorecard Visualization (NEW)
from .scorecard_viz import (
    plot_roc_curve,
    plot_ks_curve,
    plot_score_distribution,
    plot_iv_chart,
    generate_scorecard_report_html,
    get_chart_data_for_frontend as get_scorecard_chart_data
)

__all__ = [
    # Rule Mining Core Classes
    'RuleMiningDataPreprocessor',
    'FeatureEngineer',
    'SingleVarRuleMiner',
    'RuleMiner',
    'RuleEvaluator',
    'RuleSelector',
    'RuleMiningPipeline',
    # Scorecard Development Core Classes (NEW)
    'ScorecardDataPreprocessor',
    'WOETransformer',
    'FeatureSelector',
    # Task Metadata
    'RULE_MINING_TASK_META',
    'RULE_MINING_SOP_PROMPT_TEMPLATE',
    'get_task_meta',
    'get_sop_prompt_template',
    'build_sop_prompt',
    'get_stage_info',
    'get_param_info',
    'validate_params',
    # Registry
    'ParamType',
    'TaskType',
    'ParamDefinition',
    'StageDefinition',
    'OutputDefinition',
    'SOPTaskDefinition',
    'SOPRegistry',
    'sop_registry',
    'get_registry',
    'register_builtin_tasks',
    # Task Prompt Provider (NEW)
    'TaskPromptProvider',
    'get_prompt_provider',
    'reset_prompt_provider',
    'DEFAULT_BASE_PROMPT',
    # Executor
    'ExecutionStatus',
    'StageProgress',
    'ExecutionContext',
    'ExecutionStore',
    'SOPExecutor',
    'get_executor',
    'get_execution_status',
    'get_execution_result',
    'check_expert_mode_pause',
    # LLM Parameter Extractor (NEW)
    'TaskIntent',
    'ExtractionContext',
    'LLMParamExtractor',
    'create_param_extractor',
    # Unified Task Router (NEW)
    'EntrySource',
    'RouteRequest',
    'RouteResult',
    'ValidationResult',
    'UnifiedTaskRouter',
    'create_router',
    'route_from_sop_ui',
    'route_from_chat',
    # Code Templates (ENHANCED)
    'StageCodeGenerator',
    'EquivalentCodeGenerator',
    'generate_task_config_summary',
    'get_code_template',
    'format_code_template',
    # Rule Mining Visualization
    'plot_cumulative_metrics',
    'plot_rule_distribution',
    'plot_rule_comparison',
    'generate_rule_summary_html',
    'get_rule_mining_chart_data',
    'HAS_MATPLOTLIB',
    'HAS_PLOTLY',
    # Scorecard Visualization (NEW)
    'plot_roc_curve',
    'plot_ks_curve',
    'plot_score_distribution',
    'plot_iv_chart',
    'generate_scorecard_report_html',
    'get_scorecard_chart_data'
]
