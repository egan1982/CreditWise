# -*- coding: utf-8 -*-
"""
Task Result Configuration Framework

为SOP任务提供配置化的结果展示和报告生成框架。
支持规则挖掘、评分卡开发等多种任务类型的统一配置。
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class RenderType(str, Enum):
    """报告章节渲染类型"""
    TABLE = "table"
    CHART = "chart"
    TEXT = "text"
    MIXED = "mixed"


class ExportFormat(str, Enum):
    """导出格式类型"""
    MARKDOWN = "markdown"
    EXCEL = "excel"
    WORD = "word"
    PDF = "pdf"
    JSON = "json"


@dataclass
class TabConfig:
    """Tab配置"""
    id: str                              # Tab ID
    name: str                            # Tab显示名称
    data_path: str                       # 从results中获取数据的路径
    include_in_report: bool = True       # 是否纳入PDF/Word报告
    include_in_ai_analysis: bool = True  # 是否纳入AI整体分析
    ai_analysis_metrics: List[str] = field(default_factory=list)  # AI分析关注指标


@dataclass
class ReportSectionConfig:
    """报告章节配置"""
    id: str
    title: str
    order: int
    data_path: str
    render_type: RenderType = RenderType.MIXED


@dataclass
class AIAnalysisConfig:
    """AI整体分析配置"""
    role: str                            # AI角色定义
    task_description: str                # 任务描述
    focus_areas: List[str]               # 重点关注领域
    max_words: int = 200                 # 最大字数
    output_sections: List[str] = field(default_factory=lambda: [
        "执行摘要", "关键发现", "风险提示", "优化建议"
    ])
    
    def build_prompt_template(self) -> str:
        """构建Prompt模板"""
        sections = "\n".join([f"{i+1}. {s}" for i, s in enumerate(self.output_sections)])
        return f"""角色：{self.role}
任务：对{self.task_description}进行整体评估

## 任务背景
{self.task_description}

## 输入数据
{{data_description}}

## 重点关注
{", ".join(self.focus_areas)}

## 输出要求（{self.max_words}字以内）
{sections}

## 注意事项
- 基于数据客观评估，避免主观臆断
- 关键指标需给出具体数值
- 风险提示需具有可操作性
- 建议需结合业务场景"""


@dataclass
class TabSheetConfig:
    """Tab对应的Excel Sheet配置"""
    tab_id: str
    sheet_name: str


@dataclass
class StageDataSheetConfig:
    """阶段数据Sheet配置
    
    Attributes:
        stage_id: 阶段ID（与SOP定义一致）
        sheet_name: Excel Sheet名称
        download_field: output_preview中的下载数据字段名（可选）
        download_title: 下载数据表格标题（可选）
        priority_columns: 优先显示的列（可选，按顺序排列）
    """
    stage_id: str
    sheet_name: str
    download_field: Optional[str] = None  # output_preview中的下载数据字段
    download_title: Optional[str] = None  # 下载数据表格标题


@dataclass
class ExcelExportConfig:
    """Excel导出配置"""
    include_directory: bool = True                           # 是否包含目录Sheet
    tab_sheets: List[TabSheetConfig] = field(default_factory=list)
    stage_data_sheets: List[StageDataSheetConfig] = field(default_factory=list)


@dataclass
class ReportConfig:
    """报告生成配置"""
    title: str                                               # 报告标题
    include_ai_summary: bool = True                          # 是否包含AI分析作为执行摘要
    sections: List[ReportSectionConfig] = field(default_factory=list)
    supported_formats: List[ExportFormat] = field(default_factory=lambda: [
        ExportFormat.PDF, ExportFormat.WORD, ExportFormat.MARKDOWN
    ])


@dataclass
class TaskResultConfig:
    """任务结果配置 - 每个SOP任务类型一份"""
    task_type: str                       # "rule_mining" | "scorecard_dev" | ...
    task_name: str                       # "规则挖掘" | "评分卡开发" | ...
    tabs: List[TabConfig]                # Tab配置列表
    ai_analysis_config: AIAnalysisConfig # AI整体分析配置
    report_config: ReportConfig          # 报告生成配置
    excel_config: ExcelExportConfig      # Excel导出配置


# ==================== 任务配置定义 ====================

RULE_MINING_CONFIG = TaskResultConfig(
    task_type="rule_mining",
    task_name="规则挖掘",
    tabs=[
        TabConfig(
            id="sample-feature",
            name="样本及特征",
            data_path="stages.preprocessing,stages.feature_engineering",
            include_in_report=True,
            include_in_ai_analysis=True,
            ai_analysis_metrics=["total_rows", "bad_rate", "feature_count", "iv_distribution"]
        ),
        TabConfig(
            id="charts",
            name="评估图表",
            data_path="chart_data",
            include_in_report=True,
            include_in_ai_analysis=True,
            ai_analysis_metrics=["cumulative_recall", "cumulative_hit_rate", "cumulative_lift"]
        ),
        TabConfig(
            id="optimal",
            name="最优规则",
            data_path="optimal_rules",
            include_in_report=True,
            include_in_ai_analysis=True,
            ai_analysis_metrics=["rule_count", "total_recall", "avg_lift"]
        ),
        TabConfig(
            id="filtering-process",
            name="筛选过程",
            data_path="all_rules_with_status",
            include_in_report=True,
            include_in_ai_analysis=False  # 详细过程不纳入AI分析
        ),
        TabConfig(
            id="validation",
            name="质量验证",
            data_path="validation_report",
            include_in_report=True,
            include_in_ai_analysis=True,
            ai_analysis_metrics=["quality_score", "validation_issues"]
        ),
        TabConfig(
            id="psi",
            name="稳定性",
            data_path="psi_report",
            include_in_report=True,
            include_in_ai_analysis=True,
            ai_analysis_metrics=["stable_count", "unstable_count", "avg_psi"]
        ),
        TabConfig(
            id="advanced",
            name="附加分析",
            data_path="amount_analysis,prior_analysis",
            include_in_report=True,
            include_in_ai_analysis=True,
            ai_analysis_metrics=["amount_distribution", "prior_correlation"]
        ),
        TabConfig(
            id="tree",
            name="决策树",
            data_path="tree_structure",
            include_in_report=False,  # 交互式可视化不纳入报告
            include_in_ai_analysis=False
        )
    ],
    ai_analysis_config=AIAnalysisConfig(
        role="资深风控建模专家",
        task_description="规则挖掘任务",
        focus_areas=["规则质量", "召回效果", "稳定性", "业务可解释性"],
        max_words=200,
        output_sections=["执行摘要", "关键发现", "风险提示", "优化建议"]
    ),
    report_config=ReportConfig(
        title="规则挖掘分析报告",
        include_ai_summary=True,
        sections=[
            ReportSectionConfig(id="summary", title="执行摘要", order=1, data_path="ai_analysis", render_type=RenderType.TEXT),
            ReportSectionConfig(id="sample", title="样本及特征分析", order=2, data_path="stages", render_type=RenderType.MIXED),
            ReportSectionConfig(id="rules", title="规则挖掘结果", order=3, data_path="optimal_rules", render_type=RenderType.TABLE),
            ReportSectionConfig(id="charts", title="评估图表", order=4, data_path="chart_data", render_type=RenderType.CHART),
            ReportSectionConfig(id="validation", title="质量验证", order=5, data_path="validation_report", render_type=RenderType.MIXED),
            ReportSectionConfig(id="psi", title="稳定性分析", order=6, data_path="psi_report", render_type=RenderType.TABLE)
        ],
        supported_formats=[ExportFormat.PDF, ExportFormat.WORD, ExportFormat.MARKDOWN]
    ),
    excel_config=ExcelExportConfig(
        include_directory=True,
        tab_sheets=[],  # 移除重复的独立 Sheet，所有内容整合到"任务报告"中
        stage_data_sheets=[
            StageDataSheetConfig(
                stage_id="preprocessing", 
                sheet_name="1_数据预处理"
            ),
            StageDataSheetConfig(
                stage_id="feature_engineering", 
                sheet_name="2_特征工程",
                download_field="feature_details",
                download_title="保留特征列表"
            ),
            StageDataSheetConfig(
                stage_id="generating_rules", 
                sheet_name="3_规则生成",
                download_field="all_rules_for_download",
                download_title="生成规则列表"
            ),
            StageDataSheetConfig(
                stage_id="rule_filtering", 
                sheet_name="4_规则过滤",
                download_field="all_rules_with_status",
                download_title="规则筛选明细"
            ),
            StageDataSheetConfig(
                stage_id="selecting_rules", 
                sheet_name="5_规则选择",
                download_field="all_optimal_rules",
                download_title="最优规则列表"
            ),
            # 注：report_generation 阶段不单独生成 Sheet
            # 原因：该阶段 output_preview 仅包含汇总信息（validation_summary、psi_summary 等）
            # 这些信息已在"任务报告" Sheet 中展示，单独 Sheet 会造成冗余
        ]
    )
)


SCORECARD_DEV_CONFIG = TaskResultConfig(
    task_type="scorecard_dev",
    task_name="评分卡开发",
    # ==================== Tab配置 ====================
    # 注意：Tab配置需与前端 ScorecardResults.tsx 保持一致
    # 更新日期：2026-02-09
    # 变更说明：从7个Tab更新为5个Tab，与前端实际实现对齐
    tabs=[
        TabConfig(
            id="sample-data",
            name="样本与特征",
            data_path="stages.data_loading,stages.woe_binning",  # 评分卡的样本数据在data_loading阶段
            include_in_report=True,
            include_in_ai_analysis=True,
            ai_analysis_metrics=["total_rows", "bad_rate", "feature_count", "selected_count", "input_features"]
        ),
        TabConfig(
            id="charts",
            name="评估图表",
            data_path="evaluation,chart_data",
            include_in_report=True,
            include_in_ai_analysis=True,
            ai_analysis_metrics=["ks", "auc", "gini", "psi"]
        ),
        TabConfig(
            id="scorecard",
            name="评分卡明细",
            data_path="scorecard",
            include_in_report=True,
            include_in_ai_analysis=True,
            ai_analysis_metrics=["variable_count", "score_range"]
        ),
        TabConfig(
            id="selection",
            name="变量筛选",
            data_path="feature_selection,iv_table,correlation,vif,stepwise",
            include_in_report=True,
            include_in_ai_analysis=True,
            ai_analysis_metrics=["selected_count", "avg_iv", "top_features", "iv_distribution"]
        ),
        TabConfig(
            id="statistics",
            name="模型系数",
            data_path="coefficients,model_statistics",
            include_in_report=True,
            include_in_ai_analysis=True,
            ai_analysis_metrics=["significant_vars", "intercept", "hosmer_lemeshow", "vif"]
        ),
    ],
    ai_analysis_config=AIAnalysisConfig(
        role="资深风控建模专家",
        task_description="评分卡开发任务",
        focus_areas=["模型区分能力", "特征稳定性", "评分分布", "业务合理性"],
        max_words=200,
        output_sections=["执行摘要", "关键发现", "风险提示", "优化建议"]
    ),
    # ==================== 报告章节配置 ====================
    # 注意：报告章节需与前端 Tab 保持一致（除概览外）
    # 更新日期：2026-02-09
    # 目标结构：概览 → 样本与特征 → 评估图表 → 评分卡明细 → 变量筛选 → 模型系数
    report_config=ReportConfig(
        title="评分卡开发报告",
        include_ai_summary=True,
        sections=[
            # 一、概览（新增，与规则挖掘一致）
            ReportSectionConfig(id="overview", title="概览", order=1, data_path="metrics,ai_analysis", render_type=RenderType.MIXED),
            # 二、样本与特征（对应 Tab: sample-data）
            ReportSectionConfig(id="sample-data", title="样本与特征", order=2, data_path="stages", render_type=RenderType.MIXED),
            # 三、评估图表（对应 Tab: charts）
            ReportSectionConfig(id="charts", title="评估图表", order=3, data_path="evaluation,chart_data", render_type=RenderType.CHART),
            # 四、评分卡明细（对应 Tab: scorecard）
            ReportSectionConfig(id="scorecard", title="评分卡明细", order=4, data_path="scorecard", render_type=RenderType.TABLE),
            # 五、变量筛选（对应 Tab: selection）
            ReportSectionConfig(id="selection", title="变量筛选", order=5, data_path="feature_selection,iv_table", render_type=RenderType.TABLE),
            # 六、模型系数（对应 Tab: statistics）
            ReportSectionConfig(id="statistics", title="模型系数", order=6, data_path="coefficients,model_statistics", render_type=RenderType.TABLE),
        ],
        supported_formats=[ExportFormat.PDF, ExportFormat.WORD, ExportFormat.MARKDOWN]
    ),
    # ==================== Excel导出配置 ====================
    # 更新日期：2026-02-09
    # 变更说明：移除已合并的 iv、coefficients Tab
    excel_config=ExcelExportConfig(
        include_directory=True,
        tab_sheets=[
            TabSheetConfig(tab_id="sample-data", sheet_name="样本与特征"),
            TabSheetConfig(tab_id="scorecard", sheet_name="评分卡明细"),
            TabSheetConfig(tab_id="selection", sheet_name="变量筛选"),
            TabSheetConfig(tab_id="statistics", sheet_name="模型系数"),
        ],
        stage_data_sheets=[
            StageDataSheetConfig(stage_id="data_loading", sheet_name="1_数据加载"),
            StageDataSheetConfig(stage_id="woe_binning", sheet_name="2_WOE分箱"),
            StageDataSheetConfig(
                stage_id="feature_selection", 
                sheet_name="3_特征筛选",
                download_field="all_features_detail",
                download_title="特征筛选明细"
            ),
            StageDataSheetConfig(stage_id="model_training", sheet_name="4_模型训练"),
            StageDataSheetConfig(
                stage_id="score_scaling",
                sheet_name="5_评分转换",
                download_field="full_scorecard_csv",
                download_title="完整评分卡"
            ),
            StageDataSheetConfig(stage_id="model_evaluation", sheet_name="6_模型评估"),
            # 注：report_generation 阶段不单独生成 Sheet
            # 原因：该阶段 output_preview 仅包含状态信息（"报告生成完成"）和内部数据（_full_stage_data）
            # 没有可供用户下载的表格数据，且报告内容已在其他 Tab Sheet 中完整展示
        ]
    )
)


# ==================== 配置注册表 ====================

TASK_RESULT_CONFIGS: Dict[str, TaskResultConfig] = {
    "rule_mining": RULE_MINING_CONFIG,
    "scorecard_dev": SCORECARD_DEV_CONFIG,
}


def get_task_result_config(task_type: str) -> Optional[TaskResultConfig]:
    """获取任务结果配置
    
    Args:
        task_type: 任务类型
        
    Returns:
        任务结果配置，不存在返回None
    """
    return TASK_RESULT_CONFIGS.get(task_type)


def register_task_result_config(config: TaskResultConfig) -> None:
    """注册任务结果配置
    
    Args:
        config: 任务结果配置
    """
    TASK_RESULT_CONFIGS[config.task_type] = config
