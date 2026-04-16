# pyright: reportAny=false, reportExplicitAny=false, reportUnknownMemberType=false
# pyright: reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownParameterType=false
# pyright: reportImportCycles=false, reportConstantRedefinition=false, reportMissingTypeArgument=false
# pyright: reportPossiblyUnboundVariable=false, reportPrivateUsage=false
# pyright: reportDeprecated=false, reportUnusedFunction=false, reportUnusedVariable=false
# pyright: reportUnusedCallResult=false, reportUnnecessaryComparison=false, reportUnusedParameter=false
# pyright: reportUnnecessaryIsInstance=false, reportUnreachable=false, reportUnknownLambdaType=false
"""
HTML Report Generator Module

Provides HTML report generation for scorecard and rule mining results.

Features:
- Interactive charts (Plotly)
- Responsive design
- Print-friendly layout
- Professional styling

This module consolidates HTML report generation functions that were previously
scattered across visualization modules, maintaining consistency with other
report modules (excel_report.py, word_report.py, markdown_report.py).
"""
from __future__ import annotations

import pandas as pd
import numpy as np
from typing import Any, Callable, Dict, List, Optional, Literal
import re

# Module-level flags for visualization availability
SCORECARD_VIZ_AVAILABLE: bool = False
SCORECARD_HAS_PLOTLY: bool = False
RULE_MINING_VIZ_AVAILABLE: bool = False
RULE_MINING_HAS_PLOTLY: bool = False
HAS_PLOTLY: bool = False

# Lazy-loaded function references (will be populated on first use)
_plot_roc_curve: Callable[..., Any] | None = None
_plot_ks_curve: Callable[..., Any] | None = None
_plot_score_distribution: Callable[..., Any] | None = None
_plot_iv_chart: Callable[..., Any] | None = None
_generate_roc_chart_from_data_fn: Callable[..., Any] | None = None
_generate_ks_chart_from_data_fn: Callable[..., Any] | None = None
_generate_score_dist_chart_from_data_fn: Callable[..., Any] | None = None
_generate_lift_chart_from_data_fn: Callable[..., Any] | None = None
_generate_psi_comparison_chart_fn: Callable[..., Any] | None = None
_plot_cumulative_metrics: Callable[..., Any] | None = None
_plot_psi_trend: Callable[..., Any] | None = None


def _init_scorecard_viz() -> bool:
    """Lazy initialization for scorecard visualization module."""
    global SCORECARD_VIZ_AVAILABLE, SCORECARD_HAS_PLOTLY, HAS_PLOTLY
    global _plot_roc_curve, _plot_ks_curve, _plot_score_distribution, _plot_iv_chart
    global _generate_roc_chart_from_data_fn, _generate_ks_chart_from_data_fn, _generate_score_dist_chart_from_data_fn
    global _generate_lift_chart_from_data_fn, _generate_psi_comparison_chart_fn
    
    if SCORECARD_VIZ_AVAILABLE:
        return True
    
    try:
        from .task_SOP.scorecard_viz import (
            plot_roc_curve as prc,
            plot_ks_curve as pkc,
            plot_score_distribution as psd,
            plot_iv_chart as pic,
            _generate_roc_chart_from_data as groc,
            _generate_ks_chart_from_data as gks,
            _generate_score_dist_chart_from_data as gsd,
            _generate_lift_chart_from_data as glift,
            _generate_psi_comparison_chart as gpsi,
            _plotly_available as sc_plotly
        )
        _plot_roc_curve = prc
        _plot_ks_curve = pkc
        _plot_score_distribution = psd
        _plot_iv_chart = pic
        _generate_roc_chart_from_data_fn = groc
        _generate_ks_chart_from_data_fn = gks
        _generate_score_dist_chart_from_data_fn = gsd
        _generate_lift_chart_from_data_fn = glift
        _generate_psi_comparison_chart_fn = gpsi
        SCORECARD_VIZ_AVAILABLE = True
        SCORECARD_HAS_PLOTLY = sc_plotly
        HAS_PLOTLY = HAS_PLOTLY or SCORECARD_HAS_PLOTLY
        return True
    except ImportError:
        SCORECARD_VIZ_AVAILABLE = False
        SCORECARD_HAS_PLOTLY = False
        return False


def _init_rule_mining_viz() -> bool:
    """Lazy initialization for rule mining visualization module."""
    global RULE_MINING_VIZ_AVAILABLE, RULE_MINING_HAS_PLOTLY, HAS_PLOTLY
    global _plot_cumulative_metrics, _plot_psi_trend
    
    if RULE_MINING_VIZ_AVAILABLE:
        return True
    
    try:
        from .task_SOP.rule_mining_viz import (
            plot_cumulative_metrics as pcm,
            plot_psi_trend as ppt,
            HAS_PLOTLY as rm_plotly
        )
        _plot_cumulative_metrics = pcm
        _plot_psi_trend = ppt
        RULE_MINING_VIZ_AVAILABLE = True
        RULE_MINING_HAS_PLOTLY = rm_plotly
        HAS_PLOTLY = HAS_PLOTLY or RULE_MINING_HAS_PLOTLY
        return True
    except ImportError:
        RULE_MINING_VIZ_AVAILABLE = False
        RULE_MINING_HAS_PLOTLY = False
        return False


# Wrapper functions for lazy-loaded viz functions
def plot_roc_curve(*args: Any, **kwargs: Any) -> Any:
    """Wrapper for scorecard_viz.plot_roc_curve with lazy loading."""
    _init_scorecard_viz()
    if _plot_roc_curve is not None:
        return _plot_roc_curve(*args, **kwargs)
    raise ImportError("scorecard_viz module not available")


def plot_ks_curve(*args: Any, **kwargs: Any) -> Any:
    """Wrapper for scorecard_viz.plot_ks_curve with lazy loading."""
    _init_scorecard_viz()
    if _plot_ks_curve is not None:
        return _plot_ks_curve(*args, **kwargs)
    raise ImportError("scorecard_viz module not available")


def plot_score_distribution(*args: Any, **kwargs: Any) -> Any:
    """Wrapper for scorecard_viz.plot_score_distribution with lazy loading."""
    _init_scorecard_viz()
    if _plot_score_distribution is not None:
        return _plot_score_distribution(*args, **kwargs)
    raise ImportError("scorecard_viz module not available")


def plot_iv_chart(*args: Any, **kwargs: Any) -> Any:
    """Wrapper for scorecard_viz.plot_iv_chart with lazy loading."""
    _init_scorecard_viz()
    if _plot_iv_chart is not None:
        return _plot_iv_chart(*args, **kwargs)
    raise ImportError("scorecard_viz module not available")


def _generate_roc_chart_from_data(*args: Any, **kwargs: Any) -> Any:
    """Wrapper for scorecard_viz._generate_roc_chart_from_data with lazy loading."""
    _init_scorecard_viz()
    if _generate_roc_chart_from_data_fn is not None:
        return _generate_roc_chart_from_data_fn(*args, **kwargs)
    raise ImportError("scorecard_viz module not available")


def _generate_ks_chart_from_data(*args: Any, **kwargs: Any) -> Any:
    """Wrapper for scorecard_viz._generate_ks_chart_from_data with lazy loading."""
    _init_scorecard_viz()
    if _generate_ks_chart_from_data_fn is not None:
        return _generate_ks_chart_from_data_fn(*args, **kwargs)
    raise ImportError("scorecard_viz module not available")


def _generate_score_dist_chart_from_data(*args: Any, **kwargs: Any) -> Any:
    """Wrapper for scorecard_viz._generate_score_dist_chart_from_data with lazy loading."""
    _init_scorecard_viz()
    if _generate_score_dist_chart_from_data_fn is not None:
        return _generate_score_dist_chart_from_data_fn(*args, **kwargs)
    raise ImportError("scorecard_viz module not available")


def _generate_lift_chart_from_data(*args: Any, **kwargs: Any) -> Any:
    """Wrapper for scorecard_viz._generate_lift_chart_from_data with lazy loading."""
    _init_scorecard_viz()
    if _generate_lift_chart_from_data_fn is not None:
        return _generate_lift_chart_from_data_fn(*args, **kwargs)
    raise ImportError("scorecard_viz module not available")


def _generate_psi_comparison_chart(*args: Any, **kwargs: Any) -> Any:
    """Wrapper for scorecard_viz._generate_psi_comparison_chart with lazy loading."""
    _init_scorecard_viz()
    if _generate_psi_comparison_chart_fn is not None:
        return _generate_psi_comparison_chart_fn(*args, **kwargs)
    raise ImportError("scorecard_viz module not available")


def plot_cumulative_metrics(*args: Any, **kwargs: Any) -> Any:
    """Wrapper for rule_mining_viz.plot_cumulative_metrics with lazy loading."""
    _init_rule_mining_viz()
    if _plot_cumulative_metrics is not None:
        return _plot_cumulative_metrics(*args, **kwargs)
    raise ImportError("rule_mining_viz module not available")


def plot_psi_trend(*args: Any, **kwargs: Any) -> Any:
    """Wrapper for rule_mining_viz.plot_psi_trend with lazy loading."""
    _init_rule_mining_viz()
    if _plot_psi_trend is not None:
        return _plot_psi_trend(*args, **kwargs)
    raise ImportError("rule_mining_viz module not available")


# =============================================================================
# Common HTML Styles
# =============================================================================

def _get_common_styles() -> str:
    """Get common CSS styles for HTML reports."""
    return """
        * { box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang SC', 'Microsoft YaHei', sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .report-container {
            background: white;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.1);
        }
        .report-header {
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 20px;
            border-bottom: 2px solid #2E86AB;
        }
        .report-title {
            font-size: 28px;
            font-weight: 700;
            color: #1a1a1a;
            margin: 0;
        }
        .report-subtitle {
            color: #666;
            font-size: 14px;
            margin-top: 10px;
        }
        .section {
            margin: 30px 0;
            padding: 20px;
            background: #fafafa;
            border-radius: 8px;
        }
        .section-title {
            font-size: 20px;
            font-weight: 600;
            color: #1F4E79;
            margin: 0 0 20px 0;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .subsection-title {
            font-size: 16px;
            font-weight: 600;
            color: #333;
            margin: 20px 0 15px 0;
        }
        .metric-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            margin: 20px 0;
        }
        .metric-grid-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
            padding: 0 4px;
        }
        .metric-source-label {
            font-size: 12px;
            color: #6b7280;
            font-weight: 500;
        }
        .metric-card {
            background: white;
            padding: 20px;
            border-radius: 12px;
            text-align: left;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            transition: transform 0.2s, box-shadow 0.2s;
            border: 1px solid #f0f0f0;
        }
        .metric-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(0,0,0,0.1);
        }
        .metric-card.ks { background: linear-gradient(135deg, #EFF6FF 0%, #ffffff 100%); border-color: #DBEAFE; }
        .metric-card.auc { background: linear-gradient(135deg, #F0FDF4 0%, #ffffff 100%); border-color: #DCFCE7; }
        .metric-card.gini { background: linear-gradient(135deg, #FAF5FF 0%, #ffffff 100%); border-color: #F3E8FF; }
        .metric-card.psi { background: linear-gradient(135deg, #FFF7ED 0%, #ffffff 100%); border-color: #FFEDD5; }
        .metric-header {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 12px;
        }
        .metric-icon {
            font-size: 16px;
            width: 24px;
            height: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 6px;
        }
        .metric-card.ks .metric-icon { background: #DBEAFE; }
        .metric-card.auc .metric-icon { background: #DCFCE7; }
        .metric-card.gini .metric-icon { background: #F3E8FF; }
        .metric-card.psi .metric-icon { background: #FFEDD5; }
        .metric-name {
            font-size: 14px;
            font-weight: 500;
            color: #374151;
        }
        .metric-card.ks .metric-name { color: #2563EB; }
        .metric-card.auc .metric-name { color: #16A34A; }
        .metric-card.gini .metric-name { color: #9333EA; }
        .metric-card.psi .metric-name { color: #EA580C; }
        .metric-value {
            font-size: 32px;
            font-weight: 700;
            margin-bottom: 8px;
        }
        .metric-card.ks .metric-value { color: #1D4ED8; }
        .metric-card.auc .metric-value { color: #16A34A; }
        .metric-card.gini .metric-value { color: #9333EA; }
        .metric-card.psi .metric-value { color: #EA580C; }
        .metric-level {
            font-size: 12px;
            font-weight: 500;
            padding: 2px 8px;
            border-radius: 4px;
            display: inline-block;
        }
        .metric-level.excellent { background: #D1FAE5; color: #059669; }
        .metric-level.good { background: #DBEAFE; color: #2563EB; }
        .metric-level.acceptable { background: #FEF3C7; color: #D97706; }
        .metric-level.poor { background: #FEE2E2; color: #DC2626; }
        .data-table {
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            font-size: 14px;
        }
        .data-table th {
            background: #1F4E79;
            color: white;
            padding: 12px 10px;
            text-align: left;
            font-weight: 600;
        }
        .data-table td {
            padding: 10px;
            border-bottom: 1px solid #eee;
        }
        .data-table tr:hover {
            background: #f8f9fa;
        }
        .data-table tr:nth-child(even) {
            background: #fafafa;
        }
        .data-table tr:nth-child(even):hover {
            background: #f0f0f0;
        }
        .chart-container {
            margin: 20px 0;
            padding: 15px;
            background: white;
            border-radius: 8px;
        }
        .ai-analysis {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 8px;
            margin-bottom: 30px;
        }
        .ai-analysis h3 {
            margin: 0 0 15px 0;
            font-size: 18px;
        }
        .ai-analysis p, .ai-analysis li {
            margin: 8px 0;
            line-height: 1.7;
        }
        .warning-box {
            background-color: #fff3cd;
            border: 1px solid #ffc107;
            border-radius: 8px;
            padding: 12px 16px;
            margin: 15px 0;
            color: #856404;
        }
        .note-box {
            background: #e3f2fd;
            padding: 15px;
            margin: 15px 0;
            border-radius: 8px;
        }
        .note-box ul {
            margin: 10px 0;
            padding-left: 20px;
        }
        /* note-box 内表格行背景透明，保持与容器背景一致 */
        .note-box .data-table tr,
        .note-box .data-table tr:nth-child(even),
        .note-box .data-table tr:hover {
            background: transparent;
        }
        .psi-stable { color: #4CAF50; font-weight: 600; }
        .psi-warning { color: #FF9800; font-weight: 600; }
        .psi-unstable { color: #F44336; font-weight: 600; }
        .rule-text {
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 12px;
            word-break: break-all;
            max-width: 400px;
        }
        .info-table {
            width: auto;
            min-width: 300px;
        }
        .info-table td:first-child {
            font-weight: 600;
            color: #555;
            width: 150px;
        }
        .feature-tags {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin: 10px 0;
        }
        .feature-tag {
            background-color: #e9ecef;
            border-radius: 15px;
            padding: 4px 12px;
            font-size: 0.9em;
            color: #495057;
        }
        .feature-tag.valid {
            background-color: #d4edda;
            color: #155724;
        }
        .feature-tag.invalid {
            background-color: #f8d7da;
            color: #721c24;
        }
        .text-right { text-align: right; }
        .text-center { text-align: center; }
        @media print {
            body { background: white; }
            .report-container { box-shadow: none; }
            .section { break-inside: avoid; }
        }
    """


def _render_ai_analysis_inline(ai_analysis: Optional[str]) -> str:
    """Render AI analysis as inline content (no title, just content)."""
    if not ai_analysis or not ai_analysis.strip():
        return ""
    
    html_parts = ['<div class="ai-analysis" style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px;">']
    
    for line in ai_analysis.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        if line.startswith('## '):
            html_parts.append(f'<h5 style="margin: 12px 0 8px 0; color: #1976d2;">{line[3:]}</h5>')
        elif line.startswith('### '):
            html_parts.append(f'<h6 style="margin: 10px 0 6px 0; color: #555;">{line[4:]}</h6>')
        elif line.startswith('- ') or line.startswith('* '):
            html_parts.append(f'<li style="margin-left: 20px; line-height: 1.6;">{line[2:]}</li>')
        else:
            # Handle **bold** text
            line = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line)
            html_parts.append(f'<p style="margin: 5px 0; line-height: 1.6; color: #333;">{line}</p>')
    
    html_parts.append('</div>')
    return '\n'.join(html_parts)


def _add_filtered_rules_table(rules: list, max_rows: int = 50) -> str:
    """
    渲染被过滤规则表格（包含过滤原因）
    
    Args:
        rules: all_rules_with_status 中 is_valid=False 的规则列表
        max_rows: 最大显示行数
    """
    # FIX-3: 安全的空值检查（兼容 DataFrame 和 list）
    if rules is None or (isinstance(rules, list) and len(rules) == 0):
        return '<p>暂无被过滤的规则</p>'
    if isinstance(rules, pd.DataFrame):
        if rules.empty:
            return '<p>暂无被过滤的规则</p>'
        rules = rules.to_dict(orient='records')
    
    table_html = ['<table class="data-table">']
    table_html.append('''
        <thead>
            <tr>
                <th style="width:40px">序号</th>
                <th>规则</th>
                <th style="width:70px">命中率</th>
                <th style="width:70px">坏账率</th>
                <th style="width:50px">Lift</th>
                <th style="width:70px">召回率</th>
                <th style="width:200px">过滤原因</th>
            </tr>
        </thead>
        <tbody>
    ''')
    
    for i, rule in enumerate(rules[:max_rows], 1):
        rule_text = str(rule.get('rule', ''))
        display_rule = rule_text[:60] + "..." if len(rule_text) > 60 else rule_text
        
        hit_rate = rule.get('hit_rate')
        hit_rate_str = f"{hit_rate*100:.2f}%" if isinstance(hit_rate, (int, float)) and hit_rate is not None else '-'
        
        bad_rate = rule.get('bad_rate')
        bad_rate_str = f"{bad_rate*100:.2f}%" if isinstance(bad_rate, (int, float)) and bad_rate is not None else '-'
        
        lift = rule.get('lift')
        lift_str = f"{lift:.2f}" if isinstance(lift, (int, float)) and lift is not None else '-'
        
        recall = rule.get('recall')
        recall_str = f"{recall*100:.2f}%" if isinstance(recall, (int, float)) and recall is not None else '-'
        
        filter_reason = rule.get('filter_reason', '未知原因')
        # 高亮过滤原因中的关键词
        filter_reason_html = filter_reason.replace('命中率超标', '<span style="color:#e65100">命中率超标</span>')
        filter_reason_html = filter_reason_html.replace('Lift不足', '<span style="color:#c62828">Lift不足</span>')
        filter_reason_html = filter_reason_html.replace('单调性校验不通过', '<span style="color:#6a1b9a">单调性不通过</span>')
        
        table_html.append(f'''
            <tr>
                <td>{i}</td>
                <td class="rule-text" title="{rule_text}">{display_rule}</td>
                <td>{hit_rate_str}</td>
                <td>{bad_rate_str}</td>
                <td>{lift_str}</td>
                <td>{recall_str}</td>
                <td style="font-size:12px;color:#666;">{filter_reason_html}</td>
            </tr>
        ''')
    
    table_html.append('</tbody></table>')
    
    if len(rules) > max_rows:
        table_html.append(f'<p style="color:#666;font-size:13px;">（仅显示前{max_rows}条，共{len(rules)}条被过滤规则）</p>')
    
    return '\n'.join(table_html)


def _render_rule_filtering_flow(results: dict, stages: dict | None) -> str:
    """
    渲染规则筛选流程（整合原第四、五部分）
    
    包含：
    - 漏斗概览（规则生成 -> 规则筛选 -> 最优选择）
    - 规则筛选阶段：筛选条件 + 筛选结果
    - 最优选择阶段：选择条件 + 选择结果
    """
    html_parts = []
    
    # 从 stages 获取筛选和选择阶段的 output_preview
    rule_filtering_preview = {}
    selecting_rules_preview = {}
    
    if stages:
        for stage_id, stage_data in stages.items():
            if stage_id == 'rule_filtering':
                rule_filtering_preview = stage_data.get('output_preview', {})
            elif stage_id == 'selecting_rules':
                selecting_rules_preview = stage_data.get('output_preview', {})
    
    # 漏斗概览
    generated_count = rule_filtering_preview.get('generated_count', 0)
    filtered_count = rule_filtering_preview.get('after_count', 0)
    optimal_count = selecting_rules_preview.get('after_count', 0)
    
    if generated_count > 0 or filtered_count > 0 or optimal_count > 0:
        gen_pct = "100%" if generated_count > 0 else "-"
        filter_pct = f"{filtered_count/generated_count*100:.1f}%" if generated_count > 0 else "-"
        optimal_pct = f"{optimal_count/generated_count*100:.1f}%" if generated_count > 0 else "-"
        
        html_parts.append('<h3 style="color:#333;border-bottom:1px solid #ddd;padding-bottom:8px;">漏斗概览</h3>')
        html_parts.append('<div style="display:flex;justify-content:space-around;margin:20px 0;text-align:center;">')
        html_parts.append(f'<div style="padding:15px;background:#f0f9ff;border-radius:8px;min-width:120px;"><div style="font-size:24px;font-weight:bold;color:#2563eb;">{generated_count}</div><div style="color:#666;font-size:13px;">规则生成</div><div style="color:#999;font-size:12px;">{gen_pct}</div></div>')
        html_parts.append('<div style="display:flex;align-items:center;font-size:24px;color:#ccc;">→</div>')
        html_parts.append(f'<div style="padding:15px;background:#fef3c7;border-radius:8px;min-width:120px;"><div style="font-size:24px;font-weight:bold;color:#d97706;">{filtered_count}</div><div style="color:#666;font-size:13px;">规则筛选</div><div style="color:#999;font-size:12px;">{filter_pct}</div></div>')
        html_parts.append('<div style="display:flex;align-items:center;font-size:24px;color:#ccc;">→</div>')
        html_parts.append(f'<div style="padding:15px;background:#d1fae5;border-radius:8px;min-width:120px;"><div style="font-size:24px;font-weight:bold;color:#059669;">{optimal_count}</div><div style="color:#666;font-size:13px;">最优选择</div><div style="color:#999;font-size:12px;">{optimal_pct}</div></div>')
        html_parts.append('</div>')
    
    # 4.1 规则筛选阶段
    html_parts.append('<h3 style="color:#333;margin-top:25px;border-bottom:1px solid #ddd;padding-bottom:8px;">4.1 规则筛选阶段</h3>')
    
    filter_criteria = rule_filtering_preview.get('filter_criteria', {})
    filter_summary = rule_filtering_preview.get('filter_summary', {})
    
    if filter_criteria:
        html_parts.append('<div style="margin:15px 0;">')
        html_parts.append('<h4 style="color:#555;font-size:14px;margin-bottom:10px;">筛选条件</h4>')
        html_parts.append('<div style="display:flex;flex-wrap:wrap;gap:15px;">')
        
        min_lift = filter_criteria.get('min_lift')
        max_hit_rate = filter_criteria.get('max_hit_rate')
        
        html_parts.append(f'<div style="background:#f8f9fa;padding:8px 12px;border-radius:4px;font-size:13px;"><span style="color:#666;">最小Lift阈值:</span> <span style="font-weight:500;">{min_lift if min_lift is not None else "未设置"}</span></div>')
        html_parts.append(f'<div style="background:#f8f9fa;padding:8px 12px;border-radius:4px;font-size:13px;"><span style="color:#666;">最大命中率:</span> <span style="font-weight:500;">{f"{max_hit_rate*100:.1f}%" if max_hit_rate is not None else "未设置"}</span></div>')
        html_parts.append('</div></div>')
    
    if filter_summary:
        html_parts.append('<div style="margin:15px 0;">')
        html_parts.append('<h4 style="color:#555;font-size:14px;margin-bottom:10px;">筛选结果</h4>')
        html_parts.append('<table class="data-table" style="width:auto;"><thead><tr><th>筛选原因</th><th>移除数量</th></tr></thead><tbody>')
        html_parts.append(f'<tr><td>单调性校验</td><td>{filter_summary.get("direction_removed", 0)}</td></tr>')
        html_parts.append(f'<tr><td>坏账率为0</td><td>{filter_summary.get("bad_rate_zero_removed", 0)}</td></tr>')
        html_parts.append(f'<tr><td>最小Lift阈值</td><td>{filter_summary.get("lift_removed", 0)}</td></tr>')
        html_parts.append(f'<tr><td>最大命中率</td><td>{filter_summary.get("hit_rate_removed", 0)}</td></tr>')
        html_parts.append(f'<tr style="font-weight:bold;"><td>总移除</td><td>{filter_summary.get("total_removed", 0)}</td></tr>')
        html_parts.append('</tbody></table></div>')
    else:
        html_parts.append('<p style="color:#999;font-style:italic;">暂无筛选数据</p>')
    
    # 4.2 最优选择阶段
    html_parts.append('<h3 style="color:#333;margin-top:25px;border-bottom:1px solid #ddd;padding-bottom:8px;">4.2 最优选择阶段</h3>')
    
    if selecting_rules_preview:
        html_parts.append('<div style="margin:15px 0;">')
        html_parts.append('<h4 style="color:#555;font-size:14px;margin-bottom:10px;">选择条件</h4>')
        html_parts.append('<div style="display:flex;flex-wrap:wrap;gap:15px;">')
        
        allow_overlap = selecting_rules_preview.get('allow_overlap', False)
        selection_mode_text = "允许重叠（独立选择）" if allow_overlap else "贪婪算法（不允许重叠）"
        max_hit_rate = selecting_rules_preview.get('max_hit_rate')
        
        html_parts.append(f'<div style="background:#f8f9fa;padding:8px 12px;border-radius:4px;font-size:13px;"><span style="color:#666;">选择模式:</span> <span style="font-weight:500;">{selection_mode_text}</span></div>')
        html_parts.append(f'<div style="background:#f8f9fa;padding:8px 12px;border-radius:4px;font-size:13px;"><span style="color:#666;">最大命中率（规则集）:</span> <span style="font-weight:500;">{f"{max_hit_rate*100:.1f}%" if max_hit_rate is not None else "未设置"}</span></div>')
        
        # 风险目标参数
        risk_targets = selecting_rules_preview.get('risk_targets', {})
        min_recall = risk_targets.get('min_recall_ruleset')
        min_bad_rate = risk_targets.get('min_bad_rate_ruleset')
        target_bad_rate = risk_targets.get('target_bad_rate_ruleset')
        min_lift = risk_targets.get('min_lift_ruleset')
        
        html_parts.append(f'<div style="background:#f8f9fa;padding:8px 12px;border-radius:4px;font-size:13px;"><span style="color:#666;">最低召回率目标:</span> <span style="font-weight:500;{"color:#999;" if min_recall is None else ""}">{f"{min_recall*100:.1f}%" if min_recall is not None else "未设置"}</span></div>')
        html_parts.append(f'<div style="background:#f8f9fa;padding:8px 12px;border-radius:4px;font-size:13px;"><span style="color:#666;">最低坏账率目标:</span> <span style="font-weight:500;{"color:#999;" if min_bad_rate is None else ""}">{f"{min_bad_rate*100:.1f}%" if min_bad_rate is not None else "未设置"}</span></div>')
        html_parts.append(f'<div style="background:#f8f9fa;padding:8px 12px;border-radius:4px;font-size:13px;"><span style="color:#666;">目标坏账率:</span> <span style="font-weight:500;{"color:#999;" if target_bad_rate is None else ""}">{f"{target_bad_rate*100:.1f}%" if target_bad_rate is not None else "未设置"}</span></div>')
        html_parts.append(f'<div style="background:#f8f9fa;padding:8px 12px;border-radius:4px;font-size:13px;"><span style="color:#666;">最低提升度目标:</span> <span style="font-weight:500;{"color:#999;" if min_lift is None else ""}">{min_lift if min_lift is not None else "未设置"}</span></div>')
        html_parts.append('</div></div>')
        
        # 选择结果（放弃原因统计）
        rejected_stats = selecting_rules_preview.get('rejected_rules_stats', {})
        reason_distribution = rejected_stats.get('reason_distribution', {})
        selection_mode = rejected_stats.get('selection_mode', 'greedy' if not allow_overlap else 'overlap')
        
        # 定义各模式下的所有可能放弃原因（与 rule_mining.py 保持一致）
        # 注：坏账率为0的规则在规则筛选阶段已被过滤，最优选择阶段不再需要该原因
        # v2.5: 贪婪模式下移除"未被选中"，所有未被选中的规则都归类为"样本被消耗"
        greedy_reasons = ["命中率达上限", "样本被消耗（贪婪模式）", "目标坏账率已达成", "召回率目标已达成"]
        overlap_reasons = ["命中率达上限", "目标坏账率已达成", "召回率目标已达成", "排序靠后", "异常情况（请检查数据）"]
        possible_reasons = overlap_reasons if selection_mode == 'overlap' else greedy_reasons
        
        # 确保所有可能原因都有值（默认为0）
        full_reason_distribution = {reason: reason_distribution.get(reason, 0) for reason in possible_reasons}
        
        html_parts.append('<div style="margin:15px 0;">')
        html_parts.append('<h4 style="color:#555;font-size:14px;margin-bottom:10px;">选择结果</h4>')
        html_parts.append('<table class="data-table" style="width:auto;"><thead><tr><th>放弃原因</th><th>数量</th></tr></thead><tbody>')
        
        total_rejected = 0
        for reason in possible_reasons:
            count = full_reason_distribution[reason]
            html_parts.append(f'<tr><td>{reason}</td><td>{count}</td></tr>')
            total_rejected += count
        
        html_parts.append(f'<tr style="font-weight:bold;"><td>总放弃</td><td>{total_rejected}</td></tr>')
        html_parts.append('</tbody></table></div>')
    else:
        html_parts.append('<p style="color:#999;font-style:italic;">暂无选择数据</p>')
    
    return '\n'.join(html_parts)


def _render_validation_report(validation_report: dict) -> str:
    """
    渲染质量验证报告 - 优化版
    
    特性：
    - 中文标题映射
    - 精简核心指标展示
    - 状态颜色标识
    - 卡片式布局
    """
    if not isinstance(validation_report, dict):
        return '<p>验证报告数据格式异常</p>'
    
    html_parts = []
    
    # 标题映射
    category_names = {
        'discrimination_report': ('📊 区分度评估', '规则区分好坏客户的能力'),
        'recall_report': ('🎯 召回率评估', '对坏客户的捕获能力'),
        'coverage_report': ('📈 覆盖率评估', '规则命中样本比例'),
        'overlap_report': ('🔗 重叠度检测', '规则间样本重叠情况'),
        'redundancy_report': ('♻️ 冗余度检测', '是否存在冗余规则'),
        'complexity_report': ('⚙️ 复杂度评估', '规则条件复杂程度'),
        'conflict_report': ('⚠️ 冲突检测', '规则间是否存在冲突'),
    }
    
    # 状态映射
    status_styles = {
        'excellent': ('优秀', '#4caf50', '🟢'),
        'good': ('良好', '#2196f3', '🔵'),
        'acceptable': ('合格', '#ff9800', '🟡'),
        'warning': ('警告', '#f44336', '🟠'),
        'warning_low': ('偏低', '#ff9800', '🟡'),
        'warning_high': ('偏高', '#ff9800', '🟡'),
        'error': ('异常', '#f44336', '🔴'),
        'ok': ('正常', '#4caf50', '🟢'),
    }
    
    # 提取综合评分
    quality_score = validation_report.get('quality_score', 0)
    score_breakdown = validation_report.get('score_breakdown', {})
    warnings = validation_report.get('warnings', [])
    
    # 顶部综合评分卡片
    score_color = '#4caf50' if quality_score >= 80 else '#ff9800' if quality_score >= 60 else '#f44336'
    html_parts.append(f'''
    <div style="display: flex; flex-wrap: wrap; gap: 15px; margin-bottom: 20px;">
        <div style="flex: 1; min-width: 120px; max-width: 150px; background: linear-gradient(135deg, {score_color}, {score_color}dd); 
                    color: white; padding: 20px; border-radius: 12px; text-align: center; box-shadow: 0 4px 12px {score_color}40;">
            <div style="font-size: 32px; font-weight: bold;">{quality_score:.1f}</div>
            <div style="font-size: 12px; opacity: 0.9;">综合评分 / 100</div>
        </div>
    ''')
    
    # 各维度得分卡片
    dimension_names = {
        'discrimination': '区分度',
        'recall': '召回率',
        'coverage': '覆盖率',
        'independence': '独立性',
        'complexity': '复杂度',
    }
    for key, label in dimension_names.items():
        score = score_breakdown.get(key, 0)
        card_color = '#4caf50' if score >= 20 else '#ff9800' if score >= 10 else '#e0e0e0'
        html_parts.append(f'''
        <div style="flex: 1; min-width: 80px; max-width: 120px; background: #f5f5f5; padding: 15px; 
                    border-radius: 8px; text-align: center; border-top: 3px solid {card_color};">
            <div style="font-size: 20px; font-weight: bold; color: {card_color};">{score:.1f}</div>
            <div style="font-size: 11px; color: #666;">{label}</div>
        </div>
        ''')
    
    html_parts.append('</div>')
    
    # 详情表格
    html_parts.append('''
    <table style="width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 14px;">
        <thead>
            <tr style="background: #f5f5f5;">
                <th style="padding: 12px; text-align: left; border-bottom: 2px solid #ddd; width: 25%;">评估维度</th>
                <th style="padding: 12px; text-align: left; border-bottom: 2px solid #ddd; width: 30%;">核心指标</th>
                <th style="padding: 12px; text-align: center; border-bottom: 2px solid #ddd; width: 15%;">状态</th>
                <th style="padding: 12px; text-align: left; border-bottom: 2px solid #ddd; width: 30%;">说明</th>
            </tr>
        </thead>
        <tbody>
    ''')
    
    # 各维度详情行
    validation_rows = []
    
    # 区分度
    disc = validation_report.get('discrimination_report', {})
    if disc and isinstance(disc, dict):
        status = disc.get('status', 'error')
        status_label, status_color, status_icon = status_styles.get(status, ('未知', '#999', '⚪'))
        avg_lift = disc.get('avg_lift', 0)
        min_lift = disc.get('min_lift', 0)
        max_lift = disc.get('max_lift', 0)
        desc = f'平均Lift={avg_lift}，范围[{min_lift}, {max_lift}]'
        validation_rows.append(('📊 区分度', f'平均Lift: <b>{avg_lift}</b>', status_icon, status_label, status_color, desc))
    
    # 召回率
    recall = validation_report.get('recall_report', {})
    if recall and isinstance(recall, dict):
        status = recall.get('status', 'error')
        status_label, status_color, status_icon = status_styles.get(status, ('未知', '#999', '⚪'))
        cumulative_recall = recall.get('cumulative_recall', 0)
        total_bad = recall.get('total_bad_samples', 0)
        desc = f'累计召回{cumulative_recall*100:.2f}%坏客户' + (f'（共{total_bad}个）' if total_bad else '')
        validation_rows.append(('🎯 召回率', f'累计召回: <b>{cumulative_recall*100:.2f}%</b>', status_icon, status_label, status_color, desc))
    
    # 覆盖率
    coverage = validation_report.get('coverage_report', {})
    if coverage and isinstance(coverage, dict):
        status = coverage.get('status', 'error')
        status_label, status_color, status_icon = status_styles.get(status, ('未知', '#999', '⚪'))
        total_coverage = coverage.get('total_coverage', 0)
        desc = f'规则集覆盖{total_coverage*100:.2f}%样本'
        validation_rows.append(('📈 覆盖率', f'总覆盖率: <b>{total_coverage*100:.2f}%</b>', status_icon, status_label, status_color, desc))
    
    # 重叠度
    overlap = validation_report.get('overlap_report', {})
    if overlap and isinstance(overlap, dict):
        status = overlap.get('status', 'ok')
        status_label, status_color, status_icon = status_styles.get(status, ('未知', '#999', '⚪'))
        avg_overlap = overlap.get('avg_overlap', 0)
        high_pairs = overlap.get('high_overlap_pairs', [])
        desc = '规则间无明显重叠' if avg_overlap == 0 else f'平均重叠{avg_overlap*100:.1f}%'
        if high_pairs:
            desc += f'，{len(high_pairs)}对高重叠'
        validation_rows.append(('🔗 重叠度', f'平均重叠: <b>{avg_overlap*100:.1f}%</b>', status_icon, status_label, status_color, desc))
    
    # 冗余度
    redundancy = validation_report.get('redundancy_report', {})
    if redundancy and isinstance(redundancy, dict):
        status = redundancy.get('status', 'ok')
        status_label, status_color, status_icon = status_styles.get(status, ('未知', '#999', '⚪'))
        redundant_count = redundancy.get('redundant_count', 0)
        desc = '无冗余规则' if redundant_count == 0 else f'存在{redundant_count}对冗余规则'
        validation_rows.append(('♻️ 冗余度', f'冗余规则: <b>{redundant_count}对</b>', status_icon, status_label, status_color, desc))
    
    # 复杂度
    complexity = validation_report.get('complexity_report', {})
    if complexity and isinstance(complexity, dict):
        status = complexity.get('status', 'ok')
        status_label, status_color, status_icon = status_styles.get(status, ('未知', '#999', '⚪'))
        avg_complexity = complexity.get('avg_complexity', 0)
        max_complexity = complexity.get('max_complexity', 0)
        desc = f'平均{avg_complexity:.1f}个条件，最大{max_complexity}个'
        validation_rows.append(('⚙️ 复杂度', f'平均条件数: <b>{avg_complexity:.1f}</b>', status_icon, status_label, status_color, desc))
    
    # 渲染行
    for row in validation_rows:
        dimension, metric, icon, label, color, desc = row
        html_parts.append(f'''
        <tr style="border-bottom: 1px solid #eee;">
            <td style="padding: 12px; font-weight: 500;">{dimension}</td>
            <td style="padding: 12px;">{metric}</td>
            <td style="padding: 12px; text-align: center;">
                <span style="display: inline-block; padding: 4px 12px; border-radius: 12px; 
                             background: {color}20; color: {color}; font-size: 12px; font-weight: 500;">
                    {icon} {label}
                </span>
            </td>
            <td style="padding: 12px; color: #666; font-size: 13px;">{desc}</td>
        </tr>
        ''')
    
    html_parts.append('</tbody></table>')
    
    # 警告信息
    if warnings:
        html_parts.append('''
        <div style="margin-top: 20px; padding: 15px; background: #fff3e0; border-radius: 8px;">
            <div style="font-weight: 500; color: #e65100; margin-bottom: 8px;">💡 优化建议</div>
            <ul style="margin: 0; padding-left: 20px; color: #666;">
        ''')
        for warning in warnings[:5]:  # 最多显示5条
            html_parts.append(f'<li style="margin: 5px 0; line-height: 1.5;">{warning}</li>')
        html_parts.append('</ul></div>')
    elif quality_score >= 80:
        html_parts.append('''
        <div style="margin-top: 20px; padding: 15px; background: #e8f5e9; border-radius: 8px;">
            <span style="color: #2e7d32;">✅ 规则集质量优秀，各项指标均达标</span>
        </div>
        ''')
    
    return '\n'.join(html_parts)


def _render_sample_features_section(stages: Dict[str, Any]) -> str:
    """
    Render sample features section from stages data.
    
    Mirrors the frontend SampleFeaturePanel component.
    2026-02-10: 精简内容，与前端Tab对齐，移除冗余的缺失率分布、排除变量、IV分析等详细内容
    """
    if not stages:
        return ""
    
    # Get preprocessing stage data
    preprocessing_stage = stages.get('preprocessing', {})
    preprocessing_data = preprocessing_stage.get('output_preview', {}) if isinstance(preprocessing_stage, dict) else {}
    
    if not preprocessing_data:
        return ""
    
    # Get feature_engineering stage data (optional)
    fe_stage = stages.get('feature_engineering', {})
    fe_data = fe_stage.get('output_preview', {}) if isinstance(fe_stage, dict) else {}
    # 放宽条件：只要有 before_count 或 after_count 或 selection_flow，就认为有特征工程数据
    has_feature_engineering = bool(fe_data) and (
        fe_data.get('before_count') is not None or 
        fe_data.get('after_count') is not None or 
        fe_data.get('selection_flow')
    )
    
    html_parts = ['<div class="section">', '<h2 class="section-title">📊 二、样本及特征</h2>']
    
    # 2.1 样本概览（与前端一致）
    html_parts.append('<h4 class="subsection-title">样本概览</h4>')
    html_parts.append('<table class="data-table info-table">')
    
    rows = preprocessing_data.get('rows')
    if rows is not None:
        html_parts.append(f'<tr><td>总样本数</td><td style="text-align:right;">{rows:,}</td></tr>')
    
    target_rate = preprocessing_data.get('target_rate')
    if target_rate is not None:
        html_parts.append(f'<tr><td>总体坏账率</td><td style="text-align:right;color:#7c3aed;">{target_rate*100:.2f}%</td></tr>')
    
    split_info = preprocessing_data.get('split_info', {})
    if split_info:
        train_count = split_info.get('train')
        train_rate = split_info.get('train_target_rate')
        if train_count is not None:
            rate_str = f" <span style='color:#666;'>(坏账率: {train_rate*100:.2f}%)</span>" if train_rate else ""
            html_parts.append(f'<tr><td>训练集</td><td style="text-align:right;">{train_count:,}{rate_str}</td></tr>')
        
        test_count = split_info.get('test')
        test_rate = split_info.get('test_target_rate')
        if test_count is not None:
            rate_str = f" <span style='color:#666;'>(坏账率: {test_rate*100:.2f}%)</span>" if test_rate else ""
            html_parts.append(f'<tr><td>测试集</td><td style="text-align:right;">{test_count:,}{rate_str}</td></tr>')
    
    html_parts.append('</table>')
    
    # 2.2 时间范围（与前端一致，新增）
    time_range_info = preprocessing_data.get('time_range_info', {})
    if time_range_info:
        time_col = time_range_info.get('column', '')
        time_col_display = f"（{time_col}）" if time_col else ""
        
        html_parts.append(f'<h4 class="subsection-title">📅 时间范围{time_col_display}</h4>')
        html_parts.append('<div style="display:flex;gap:20px;margin-bottom:20px;">')
        
        train_range = time_range_info.get('train', {})
        if train_range:
            html_parts.append(f'''
                <div style="flex:1;background:#f8f9fa;padding:15px;border-radius:8px;text-align:center;">
                    <div style="font-size:14px;color:#666;margin-bottom:8px;">训练集</div>
                    <div style="font-size:14px;color:#333;">{train_range.get('min', '-')} ~ {train_range.get('max', '-')}</div>
                </div>
            ''')
        
        test_range = time_range_info.get('test', {})
        if test_range:
            html_parts.append(f'''
                <div style="flex:1;background:#f8f9fa;padding:15px;border-radius:8px;text-align:center;">
                    <div style="font-size:14px;color:#666;margin-bottom:8px;">测试集</div>
                    <div style="font-size:14px;color:#333;">{test_range.get('min', '-')} ~ {test_range.get('max', '-')}</div>
                </div>
            ''')
        
        oot_range = time_range_info.get('oot', {})
        if oot_range and oot_range.get('min'):
            html_parts.append(f'''
                <div style="flex:1;background:#f8f9fa;padding:15px;border-radius:8px;text-align:center;">
                    <div style="font-size:14px;color:#666;margin-bottom:8px;">OOT验证集</div>
                    <div style="font-size:14px;color:#333;">{oot_range.get('min', '-')} ~ {oot_range.get('max', '-')}</div>
                </div>
            ''')
        
        html_parts.append('</div>')
    
    # 2.3 特征概览（与前端一致：原始特征数、筛选后特征、平均缺失率）
    html_parts.append('<h4 class="subsection-title">📊 特征概览</h4>')
    html_parts.append('<div class="metric-grid">')
    
    feature_count = preprocessing_data.get('feature_count')
    
    if feature_count is not None:
        html_parts.append(f'''
            <div class="metric-card" style="background:#e8f5e9;">
                <div class="metric-value" style="color:#4caf50;">{feature_count}</div>
                <div class="metric-label">原始特征数</div>
            </div>
        ''')
    
    # 筛选后特征数（优先使用feature_engineering的after_count）
    filtered_count = None
    if has_feature_engineering and fe_data.get('after_count') is not None:
        filtered_count = fe_data['after_count']
    
    if filtered_count is not None:
        html_parts.append(f'''
            <div class="metric-card" style="background:#e3f2fd;">
                <div class="metric-value" style="color:#2196f3;">{filtered_count}</div>
                <div class="metric-label">筛选后特征</div>
            </div>
        ''')
    
    missing_rate = preprocessing_data.get('missing_rate')
    if missing_rate is not None:
        html_parts.append(f'''
            <div class="metric-card" style="background:#fff3e0;">
                <div class="metric-value" style="color:#ff9800;">{missing_rate*100:.1f}%</div>
                <div class="metric-label">平均缺失率</div>
            </div>
        ''')
    
    html_parts.append('</div>')
    
    # 2.4 特征变化流程（与前端一致：初始 → 缺失率筛选 → One-Hot后 → IV筛选）
    if has_feature_engineering:
        before_count = fe_data.get('before_count')
        after_count = fe_data.get('after_count')
        
        # 优先使用 selection_flow（规则挖掘任务使用此格式）
        selection_flow = fe_data.get('selection_flow', [])
        
        html_parts.append('<h4 class="subsection-title">特征变化流程</h4>')
        html_parts.append('<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding:15px;background:#f8f9fa;border-radius:8px;">')
        
        if selection_flow:
            # 使用 selection_flow 格式（规则挖掘任务）
            for i, step in enumerate(selection_flow):
                step_name = step.get('step', '')
                step_count = step.get('count', 0)
                step_removed = step.get('removed', 0)
                step_added = step.get('added', 0)
                
                # 根据步骤名称选择颜色
                if step_name == '初始':
                    color = '#333'
                elif step_name == 'One-Hot后':
                    color = '#dc2626'
                elif step_name == 'IV筛选':
                    color = '#22c55e'
                else:
                    color = '#333'
                
                # 构建变化指示
                diff_str = ''
                if step_removed > 0:
                    diff_str = f"<div style='font-size:11px;color:#dc2626;'>-{step_removed}</div>"
                if step_added > 0:
                    diff_str += f"<div style='font-size:11px;color:#22c55e;'>+{step_added}</div>"
                
                html_parts.append(f'''
                    <div style="text-align:center;">
                        <div style="font-size:24px;font-weight:bold;color:{color};">{step_count}</div>
                        <div style="font-size:12px;color:#666;">{step_name}</div>
                        {diff_str}
                    </div>
                ''')
                
                # 添加箭头（最后一步不加）
                if i < len(selection_flow) - 1:
                    html_parts.append('<div style="color:#ccc;font-size:20px;">→</div>')
        else:
            # 使用旧格式（评分卡任务兼容）
            var_filter = fe_data.get('var_filter_result', {})
            onehot_info = fe_data.get('onehot_info', {})
            
            # 初始特征
            initial_count = feature_count or before_count
            if initial_count:
                html_parts.append(f'''
                    <div style="text-align:center;">
                        <div style="font-size:24px;font-weight:bold;color:#333;">{initial_count}</div>
                        <div style="font-size:12px;color:#666;">初始</div>
                    </div>
                    <div style="color:#ccc;font-size:20px;">→</div>
                ''')
            
            # 缺失率筛选后（如有）
            missing_filtered = var_filter.get('after_missing_filter') or before_count
            if missing_filtered and missing_filtered != initial_count:
                html_parts.append(f'''
                    <div style="text-align:center;">
                        <div style="font-size:24px;font-weight:bold;color:#333;">{missing_filtered}</div>
                        <div style="font-size:12px;color:#666;">缺失率筛选</div>
                    </div>
                    <div style="color:#ccc;font-size:20px;">→</div>
                ''')
            
            # One-Hot后（如有）
            onehot_after = onehot_info.get('after_count')
            if onehot_after:
                onehot_before = onehot_info.get('before_count', 0)
                diff = onehot_after - onehot_before if onehot_before else 0
                diff_str = f"<div style='font-size:11px;color:#22c55e;'>+{diff}</div>" if diff > 0 else ""
                html_parts.append(f'''
                    <div style="text-align:center;">
                        <div style="font-size:24px;font-weight:bold;color:#dc2626;">{onehot_after}</div>
                        <div style="font-size:12px;color:#666;">One-Hot后</div>
                        {diff_str}
                    </div>
                    <div style="color:#ccc;font-size:20px;">→</div>
                ''')
            
            # IV筛选后
            if after_count is not None:
                removed = (onehot_after or before_count or initial_count or 0) - after_count
                removed_str = f"<div style='font-size:11px;color:#dc2626;'>-{removed}</div>" if removed > 0 else ""
                html_parts.append(f'''
                    <div style="text-align:center;">
                        <div style="font-size:24px;font-weight:bold;color:#22c55e;">{after_count}</div>
                        <div style="font-size:12px;color:#666;">IV筛选</div>
                        {removed_str}
                    </div>
                ''')
        
        html_parts.append('</div>')
    
    html_parts.append('</div>')
    return '\n'.join(html_parts)




# =============================================================================
# Unified Entry Point
# =============================================================================

def generate_html_report(
    task_type: Literal['scorecard', 'rule_mining'],
    results: Dict[str, Any],
    title: Optional[str] = None,
    ai_analysis: Optional[str] = None,
    include_charts: bool = True
) -> str:
    """
    Generate HTML report for a specific task type.
    
    This is the unified entry point for HTML report generation, mirroring
    the structure of generate_word_report(), generate_excel_report(), etc.
    
    Args:
        task_type: Type of task ('scorecard' or 'rule_mining')
        results: Dictionary containing all task outputs
        title: Report title (auto-generated if not provided)
        ai_analysis: Optional AI analysis summary
        include_charts: Whether to include interactive charts
        
    Returns:
        Complete HTML report string
    """
    if task_type == 'scorecard':
        return _generate_scorecard_html_report(
            results=results,
            title=title or '评分卡开发报告',
            ai_analysis=ai_analysis,
            include_charts=include_charts
        )
    elif task_type == 'rule_mining':
        return _generate_rule_mining_html_report(
            results=results,
            title=title or '规则挖掘报告',
            ai_analysis=ai_analysis,
            include_charts=include_charts
        )
    else:
        raise ValueError(f"Unsupported task type: {task_type}")


# =============================================================================
# Rule Mining HTML Report
# =============================================================================

def _generate_rule_mining_html_report(
    results: Dict[str, Any],
    title: str = '规则挖掘报告',
    ai_analysis: Optional[str] = None,
    include_charts: bool = True
) -> str:
    """
    Generate complete HTML report for rule mining results.
    
    This function mirrors _generate_rule_mining_word_report() structure to maintain
    consistency across all export formats.
    
    Args:
        results: Dictionary containing all rule mining outputs:
            - preprocessing_info: Sample statistics
            - rules / optimal_rules: Optimal rule set
            - filtered_rules: Filtered rules
            - validation_report: Quality validation
            - psi_report: Stability analysis
            - amount_analysis: Amount analysis
        title: Report title
        ai_analysis: Optional AI analysis summary
        include_charts: Whether to include interactive charts
        
    Returns:
        Complete HTML report string
    """
    html_parts = []
    
    # HTML Header with styles
    html_parts.append(f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        {_get_common_styles()}
    </style>
</head>
<body>
<div class="report-container">
    <div class="report-header">
        <h1 class="report-title">{title}</h1>
        <p class="report-subtitle">生成时间：{pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
""")
    
    # 1. 概览
    html_parts.append('<div class="section">')
    html_parts.append('<h2 class="section-title">📊 一、概览</h2>')
    
    preprocessing_info = results.get('preprocessing_info', {})
    if preprocessing_info:
        html_parts.append('<table class="data-table info-table">')
        
        info_names = {
            'n_samples': '样本量',
            'n_bad': '坏样本数',
            'base_bad_rate': '基础坏账率',
            'n_rules_generated': '生成规则数',
            'n_features': '特征数量',
            'target_column': '目标变量',
        }
        
        for key, label in info_names.items():
            if key in preprocessing_info and preprocessing_info[key] is not None:
                value = preprocessing_info[key]
                if key == 'base_bad_rate' and isinstance(value, (int, float)):
                    display_value = f"{value * 100:.2f}%"
                elif isinstance(value, float):
                    display_value = f"{value:.4f}"
                else:
                    display_value = str(value)
                html_parts.append(f'<tr><td>{label}</td><td>{display_value}</td></tr>')
        
        html_parts.append('</table>')
    
    # Summary metrics cards
    optimal_rules = results.get('optimal_rules', results.get('rules', []))
    # Phase 25: 兼容 DataFrame 和 list
    if isinstance(optimal_rules, pd.DataFrame) and not optimal_rules.empty:
        n_rules = len(optimal_rules)
        
        # Calculate cumulative metrics from last rule
        if isinstance(optimal_rules, list) and len(optimal_rules) > 0:
            last_rule = optimal_rules[-1]
            final_recall = last_rule.get('cumulative_recall', last_rule.get('cum_recall', last_rule.get('dev_cum_recall', 0)))
            final_hit_rate = last_rule.get('cumulative_hit_rate', last_rule.get('cum_hit_rate', last_rule.get('dev_cum_hit_rate', 0)))
            final_lift = last_rule.get('cumulative_lift', last_rule.get('cum_lift', last_rule.get('dev_cum_lift', last_rule.get('lift', 0))))
        else:
            final_recall = final_hit_rate = final_lift = 0
        
        html_parts.append('<div class="metric-grid">')
        html_parts.append(f'''
            <div class="metric-card">
                <div class="metric-value">{n_rules}</div>
                <div class="metric-label">最优规则数</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{final_recall*100:.1f}%</div>
                <div class="metric-label">累计召回率</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{final_hit_rate*100:.1f}%</div>
                <div class="metric-label">累计命中率</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{final_lift:.2f}x</div>
                <div class="metric-label">累计提升倍数</div>
            </div>
        ''')
        html_parts.append('</div>')
    
    # AI整体分析（放在指标卡下方）
    html_parts.append(_render_ai_analysis_inline(ai_analysis))
    
    html_parts.append('</div>')
    
    # 2. 样本集特征（从stages获取）
    html_parts.append(_render_sample_features_section(results.get('stages', {})))
    
    # Helper function for rule tables
    def add_rules_table(rules: List[Dict], max_rows: int = 50) -> str:
        # FIX-3: 安全的空值检查（兼容 DataFrame 和 list）
        if rules is None or (isinstance(rules, list) and len(rules) == 0):
            return '<p>暂无规则数据</p>'
        if isinstance(rules, pd.DataFrame):
            if rules.empty:
                return '<p>暂无规则数据</p>'
            rules = rules.to_dict(orient='records')
        
        table_html = ['<table class="data-table">']
        table_html.append('''
            <thead>
                <tr>
                    <th style="width:50px">序号</th>
                    <th>规则</th>
                    <th style="width:80px">召回率</th>
                    <th style="width:80px">命中率</th>
                    <th style="width:80px">坏账率</th>
                    <th style="width:60px">Lift</th>
                    <th style="width:90px">累计召回</th>
                </tr>
            </thead>
            <tbody>
        ''')
        
        for i, rule in enumerate(rules[:max_rows], 1):
            rule_text = str(rule.get('rule', ''))
            display_rule = rule_text[:80] + "..." if len(rule_text) > 80 else rule_text
            
            recall = rule.get('recall', 0)
            recall_str = f"{recall*100:.2f}%" if isinstance(recall, (int, float)) else '-'
            
            hit_rate = rule.get('hit_rate', 0)
            hit_rate_str = f"{hit_rate*100:.2f}%" if isinstance(hit_rate, (int, float)) else '-'
            
            bad_rate = rule.get('bad_rate', 0)
            bad_rate_str = f"{bad_rate*100:.2f}%" if isinstance(bad_rate, (int, float)) else '-'
            
            lift = rule.get('lift', 0)
            lift_str = f"{lift:.2f}" if isinstance(lift, (int, float)) else '-'
            
            cum_recall = rule.get('cumulative_recall', rule.get('cum_recall', rule.get('dev_cum_recall', 0)))
            cum_recall_str = f"{cum_recall*100:.2f}%" if isinstance(cum_recall, (int, float)) else '-'
            
            table_html.append(f'''
                <tr>
                    <td>{i}</td>
                    <td class="rule-text" title="{rule_text}">{display_rule}</td>
                    <td>{recall_str}</td>
                    <td>{hit_rate_str}</td>
                    <td>{bad_rate_str}</td>
                    <td>{lift_str}</td>
                    <td>{cum_recall_str}</td>
                </tr>
            ''')
        
        table_html.append('</tbody></table>')
        
        if len(rules) > max_rows:
            table_html.append(f'<p style="color:#666;font-size:13px;">（仅显示前{max_rows}条，共{len(rules)}条规则）</p>')
        
        return '\n'.join(table_html)
    
    # 3. 最优规则（固定章节，始终显示）
    html_parts.append('<div class="section">')
    html_parts.append('<h2 class="section-title">🎯 三、最优规则</h2>')
    
    # Add cumulative metrics chart
    if include_charts and optimal_rules:
        _init_rule_mining_viz()  # Lazy init
        if RULE_MINING_VIZ_AVAILABLE and RULE_MINING_HAS_PLOTLY:
            try:
                optimal_df = pd.DataFrame(optimal_rules) if isinstance(optimal_rules, list) else optimal_rules
                cumulative_chart = plot_cumulative_metrics(
                    optimal_df,
                    output_format='plotly',
                    return_html=True
                )
                html_parts.append('<div class="chart-container">')
                html_parts.append('<h4 class="subsection-title">累计指标曲线</h4>')
                html_parts.append(cumulative_chart)
                html_parts.append('</div>')
            except Exception as e:
                html_parts.append(f'<p style="color:#999;">无法生成累计指标曲线: {e}</p>')
    
    html_parts.append(add_rules_table(optimal_rules))
    html_parts.append('</div>')
    
    # 4. 规则筛选流程（整合原第四、五部分）
    html_parts.append('<div class="section">')
    html_parts.append('<h2 class="section-title">🔄 四、规则筛选流程</h2>')
    stages = results.get('stages')  # 从results中提取stages数据
    html_parts.append(_render_rule_filtering_flow(results, stages))
    html_parts.append('</div>')
    
    # 5. 质量验证（固定章节，始终显示）
    html_parts.append('<div class="section">')
    html_parts.append('<h2 class="section-title">✅ 五、质量验证</h2>')
    validation_report = results.get('validation_report')
    if validation_report:
        html_parts.append(_render_validation_report(validation_report))
    else:
        html_parts.append('<p style="color:#999;">暂无数据</p>')
    html_parts.append('</div>')
    
    # 6. 稳定性（固定章节，始终显示）
    html_parts.append('<div class="section">')
    html_parts.append('<h2 class="section-title">📈 六、稳定性（PSI）</h2>')
    psi_report = results.get('psi_report')
    if psi_report and isinstance(psi_report, list) and len(psi_report) > 0:
        
        # PSI chart
        if include_charts:
            _init_rule_mining_viz()  # Lazy init
            if RULE_MINING_VIZ_AVAILABLE and RULE_MINING_HAS_PLOTLY:
                try:
                    psi_chart = plot_psi_trend(
                        psi_report,
                        output_format='plotly',
                        return_html=True
                    )
                    html_parts.append('<div class="chart-container">')
                    html_parts.append(psi_chart)
                    html_parts.append('</div>')
                except Exception:
                    pass
        
        # PSI table
        headers = list(psi_report[0].keys()) if psi_report else ['规则', 'PSI', '稳定性']
        html_parts.append('<table class="data-table">')
        html_parts.append('<thead><tr>')
        for h in headers:
            html_parts.append(f'<th>{h}</th>')
        html_parts.append('</tr></thead><tbody>')
        
        for item in psi_report:
            html_parts.append('<tr>')
            for h in headers:
                value = item.get(h, '')
                if h.lower() == 'psi' and isinstance(value, (int, float)):
                    if value < 0.1:
                        css_class = 'psi-stable'
                    elif value < 0.25:
                        css_class = 'psi-warning'
                    else:
                        css_class = 'psi-unstable'
                    html_parts.append(f'<td class="{css_class}">{value:.4f}</td>')
                elif isinstance(value, float):
                    html_parts.append(f'<td>{value:.4f}</td>')
                else:
                    html_parts.append(f'<td>{value}</td>')
            html_parts.append('</tr>')
        html_parts.append('</tbody></table>')
        
        # PSI notes
        html_parts.append('''
        <div class="note-box">
            <strong>PSI指标说明：</strong>
            <ul>
                <li><span class="psi-stable">PSI < 0.1</span>：规则稳定，可直接使用</li>
                <li><span class="psi-warning">0.1 ≤ PSI < 0.25</span>：规则有轻微变化，需关注</li>
                <li><span class="psi-unstable">PSI ≥ 0.25</span>：规则显著变化，建议重新评估</li>
            </ul>
        </div>
        ''')
    else:
        html_parts.append('<p style="color:#999;">暂无数据</p>')
    html_parts.append('</div>')
    
    # 7. 附加分析（固定章节，始终显示）
    html_parts.append('<div class="section">')
    html_parts.append('<h2 class="section-title">📊 七、附加分析</h2>')
    amount_analysis = results.get('amount_analysis')
    prior_analysis = results.get('prior_analysis')
    
    if (amount_analysis and isinstance(amount_analysis, dict)) or (prior_analysis and isinstance(prior_analysis, dict)):
        # 8.1 金额维度分析
        if amount_analysis and isinstance(amount_analysis, dict):
            html_parts.append('<h3 style="color:#2e7d32;margin:20px 0 15px;font-size:16px;">💰 金额维度分析</h3>')
            html_parts.append('<h4 class="subsection-title">汇总指标</h4>')
            html_parts.append('<table class="data-table info-table">')
            
            if 'total_amount' in amount_analysis:
                html_parts.append(f'<tr><td>总金额</td><td>¥{amount_analysis["total_amount"]:,.2f}</td></tr>')
            if 'total_bad_amount' in amount_analysis:
                html_parts.append(f'<tr><td>总坏账金额</td><td>¥{amount_analysis["total_bad_amount"]:,.2f}</td></tr>')
            
            cumulative = amount_analysis.get('cumulative', {})
            if cumulative:
                if 'cum_hit_amount' in cumulative:
                    html_parts.append(f'<tr><td>累计命中金额</td><td>¥{cumulative["cum_hit_amount"]:,.2f}</td></tr>')
                if 'amount_recall' in cumulative:
                    html_parts.append(f'<tr><td>金额召回率</td><td>{cumulative["amount_recall"]*100:.2f}%</td></tr>')
            
            html_parts.append('</table>')
            
            # Rules amount detail
            rules_amount = amount_analysis.get('rules_amount', [])
            if rules_amount:
                html_parts.append('<h4 class="subsection-title">规则金额明细</h4>')
                html_parts.append('<table class="data-table">')
                html_parts.append('''
                    <thead>
                        <tr>
                            <th>规则</th>
                            <th>命中金额</th>
                            <th>金额占比</th>
                            <th>金额Lift</th>
                        </tr>
                    </thead>
                    <tbody>
                ''')
                
                for item in rules_amount[:20]:
                    rule_text = str(item.get('rule', ''))
                    display_rule = rule_text[:50] + "..." if len(rule_text) > 50 else rule_text
                    
                    hit_amount = item.get('hit_amount', 0)
                    hit_amount_str = f"¥{hit_amount:,.2f}" if isinstance(hit_amount, (int, float)) else '-'
                    
                    hit_pct = item.get('hit_amount_pct', 0)
                    hit_pct_str = f"{hit_pct*100:.2f}%" if isinstance(hit_pct, (int, float)) else '-'
                    
                    amount_lift = item.get('amount_lift', 0)
                    amount_lift_str = f"{amount_lift:.2f}" if isinstance(amount_lift, (int, float)) else '-'
                    
                    html_parts.append(f'''
                        <tr>
                            <td class="rule-text" title="{rule_text}">{display_rule}</td>
                            <td>{hit_amount_str}</td>
                            <td>{hit_pct_str}</td>
                            <td>{amount_lift_str}</td>
                        </tr>
                    ''')
                
                html_parts.append('</tbody></table>')
                
                if len(rules_amount) > 20:
                    html_parts.append(f'<p style="color:#666;font-size:13px;">（仅显示前20条，共{len(rules_amount)}条）</p>')
        
        # 8.2 先验规则分析
        if prior_analysis and isinstance(prior_analysis, dict):
            html_parts.append('<h3 style="color:#7b1fa2;margin:20px 0 15px;font-size:16px;">📋 先验规则分析</h3>')
            
            # Summary metrics
            summary = prior_analysis.get('summary', {})
            if summary:
                html_parts.append('<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:15px;">')
                
                prior_count = summary.get('prior_rules_count', 0)
                html_parts.append(f'''
                    <div style="background:#f3e5f5;padding:12px;border-radius:8px;text-align:center;">
                        <div style="font-size:20px;font-weight:bold;color:#7b1fa2;">{prior_count}</div>
                        <div style="font-size:12px;color:#666;">先验规则数</div>
                    </div>
                ''')
                
                matched_count = summary.get('matched_count', 0)
                html_parts.append(f'''
                    <div style="background:#e3f2fd;padding:12px;border-radius:8px;text-align:center;">
                        <div style="font-size:20px;font-weight:bold;color:#1976d2;">{matched_count}</div>
                        <div style="font-size:12px;color:#666;">匹配到的规则</div>
                    </div>
                ''')
                
                avg_recall = summary.get('avg_recall', 0)
                html_parts.append(f'''
                    <div style="background:#e8f5e9;padding:12px;border-radius:8px;text-align:center;">
                        <div style="font-size:20px;font-weight:bold;color:#388e3c;">{avg_recall*100:.2f}%</div>
                        <div style="font-size:12px;color:#666;">平均召回率</div>
                    </div>
                ''')
                
                avg_lift = summary.get('avg_lift', 0)
                html_parts.append(f'''
                    <div style="background:#fff3e0;padding:12px;border-radius:8px;text-align:center;">
                        <div style="font-size:20px;font-weight:bold;color:#f57c00;">{avg_lift:.2f}</div>
                        <div style="font-size:12px;color:#666;">平均Lift</div>
                    </div>
                ''')
                
                html_parts.append('</div>')
            
            # Prior rules table
            prior_rules = prior_analysis.get('rules', [])
            if prior_rules:
                html_parts.append('<h4 class="subsection-title">先验规则详情</h4>')
                html_parts.append('<table class="data-table">')
                html_parts.append('''
                    <thead>
                        <tr>
                            <th>规则</th>
                            <th>召回率</th>
                            <th>命中率</th>
                            <th>坏账率</th>
                            <th>Lift</th>
                            <th>状态</th>
                        </tr>
                    </thead>
                    <tbody>
                ''')
                
                for rule in prior_rules[:20]:
                    rule_text = str(rule.get('rule', rule.get('condition', '')))
                    display_rule = rule_text[:50] + "..." if len(rule_text) > 50 else rule_text
                    
                    recall = rule.get('recall', 0)
                    recall_str = f"{recall*100:.2f}%" if isinstance(recall, (int, float)) else '-'
                    
                    hit_rate = rule.get('hit_rate', 0)
                    hit_rate_str = f"{hit_rate*100:.2f}%" if isinstance(hit_rate, (int, float)) else '-'
                    
                    bad_rate = rule.get('bad_rate', 0)
                    bad_rate_str = f"{bad_rate*100:.2f}%" if isinstance(bad_rate, (int, float)) else '-'
                    
                    lift = rule.get('lift', 0)
                    lift_str = f"{lift:.2f}" if isinstance(lift, (int, float)) else '-'
                    
                    matched = rule.get('matched', True)
                    status_str = '<span style="color:#388e3c;">✓ 匹配</span>' if matched else '<span style="color:#d32f2f;">✗ 未匹配</span>'
                    
                    html_parts.append(f'''
                        <tr>
                            <td class="rule-text" title="{rule_text}">{display_rule}</td>
                            <td>{recall_str}</td>
                            <td>{hit_rate_str}</td>
                            <td>{bad_rate_str}</td>
                            <td>{lift_str}</td>
                            <td>{status_str}</td>
                        </tr>
                    ''')
                
                html_parts.append('</tbody></table>')
                
                if len(prior_rules) > 20:
                    html_parts.append(f'<p style="color:#666;font-size:13px;">（仅显示前20条，共{len(prior_rules)}条）</p>')
    else:
        html_parts.append('<p style="color:#999;">暂无数据</p>')
    html_parts.append('</div>')
    
    # 2026-02-10: 移除footer
    html_parts.append('''
</div>
</body>
</html>
    ''')
    
    return '\n'.join(html_parts)


# =============================================================================
# Scorecard HTML Report
# =============================================================================

def _generate_scorecard_html_report(
    results: Dict[str, Any],
    title: str = '评分卡开发报告',
    ai_analysis: Optional[str] = None,
    include_charts: bool = True
) -> str:
    """
    Generate complete HTML report for scorecard development results.

    章节结构与前端 Tab 保持一致（2026-02-09 重构）：
    - 一、概览（汇总指标卡 + 数据集指标对比 + AI分析）
    - 二、样本与特征（对应 Tab: sample-data）
    - 三、评估图表（对应 Tab: charts）
    - 四、评分卡明细（对应 Tab: scorecard）
    - 五、变量筛选（对应 Tab: selection）
    - 六、模型系数（对应 Tab: statistics）
    
    Args:
        results: Dictionary containing all scorecard outputs
        title: Report title
        ai_analysis: Optional AI analysis summary
        include_charts: Whether to include interactive charts
        
    Returns:
        Complete HTML report string
    """
    # Extract data from results
    metrics = results.get('metrics', {})
    iv_table = results.get('iv_table')
    scorecard = results.get('scorecard')
    coefficients = results.get('coefficients')
    chart_data = results.get('chart_data')
    multi_dataset_metrics = results.get('multi_dataset_metrics')
    multi_dataset_chart_data = results.get('multi_dataset_chart_data')
    selected_features = results.get('selected_features')
    overfit_warning = results.get('overfit_warning')
    selection_detail = results.get('selection_detail')
    outlier_info = results.get('outlier_info')
    # 新增：stages 数据用于样本与特征章节
    stages = results.get('stages', {})
    
    # Convert to DataFrames if needed
    if isinstance(iv_table, list):
        iv_table = pd.DataFrame(iv_table)
    if isinstance(scorecard, list):
        scorecard = pd.DataFrame(scorecard)
    if isinstance(coefficients, list):
        coefficients = pd.DataFrame(coefficients)
    
    html_parts = []
    
    # HTML Header with updated styles
    html_parts.append(f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        {_get_common_styles()}
        
        /* Scorecard specific styles */
        .metrics-table th, .metrics-table td {{
            text-align: center;
        }}
        .add-action {{
            background-color: #27ae60;
            color: white;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.85em;
        }}
        .remove-action {{
            background-color: #e74c3c;
            color: white;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.85em;
        }}
        .sig-high {{
            background-color: #27ae60;
            color: white;
            padding: 2px 8px;
            border-radius: 4px;
            font-weight: bold;
        }}
        .sig-medium {{
            background-color: #3498db;
            color: white;
            padding: 2px 8px;
            border-radius: 4px;
        }}
        .sig-low {{
            background-color: #95a5a6;
            color: white;
            padding: 2px 8px;
            border-radius: 4px;
        }}
        .sig-none {{
            color: #e74c3c;
        }}
        .coef-validation {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin: 15px 0;
        }}
        .validation-section {{
            background: white;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        .validation-title {{
            font-weight: bold;
            margin-bottom: 10px;
            padding-bottom: 5px;
            border-bottom: 2px solid;
        }}
        .valid-title {{
            color: #27ae60;
            border-color: #27ae60;
        }}
        .invalid-title {{
            color: #e74c3c;
            border-color: #e74c3c;
        }}
        /* 样本与特征面板样式 */
        .sample-overview {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin: 15px 0;
        }}
        .sample-card {{
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-radius: 10px;
            padding: 15px;
            text-align: center;
            border: 1px solid #dee2e6;
        }}
        .sample-card .value {{
            font-size: 1.8em;
            font-weight: bold;
            color: #2c3e50;
        }}
        .sample-card .label {{
            font-size: 0.85em;
            color: #666;
            margin-top: 5px;
        }}
        .sample-card.highlight {{
            background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
            border-color: #2196f3;
        }}
        .sample-card.highlight .value {{
            color: #1976d2;
        }}
        /* 漏斗图样式 */
        .funnel-container {{
            margin: 20px 0;
        }}
        .funnel-step {{
            display: flex;
            align-items: center;
            margin-bottom: 10px;
        }}
        .funnel-bar {{
            height: 35px;
            border-radius: 4px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 15px;
            color: white;
            font-weight: 500;
            transition: all 0.3s;
        }}
        .funnel-arrow {{
            width: 30px;
            text-align: center;
            color: #999;
            font-size: 1.2em;
        }}
    </style>
</head>
<body>
<div class="report-container">
    <div class="report-header">
        <h1 class="report-title">{title}</h1>
        <p class="report-subtitle">生成时间：{pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
""")
    
    # Overfit warning (只在有有效警告内容时显示，排除 None/空字符串/"None")
    if overfit_warning and str(overfit_warning).strip() and str(overfit_warning).strip().lower() != 'none':
        html_parts.append(f'''
        <div class="warning-box">
            <strong>⚠️ 过拟合警告：</strong> {overfit_warning}
        </div>
        ''')
    
    # ==========================================================================
    # 一、概览（新增，与规则挖掘一致）
    # ==========================================================================
    html_parts.append('<div class="section">')
    html_parts.append('<h2 class="section-title">📊 一、概览</h2>')
    
    # 汇总指标卡
    n_vars = len(coefficients) if coefficients is not None and len(coefficients) > 0 else 0
    # PSI 从 psi_result 获取（与前端一致），如果没有则回退到 metrics.psi
    psi_result = results.get('psi_result', {})
    if psi_result and isinstance(psi_result, dict) and 'value' in psi_result:
        psi_val = psi_result.get('value')
    else:
        psi_val = metrics.get('psi', None)
    # 动态获取指标数据来源标签（与前端一致：优先OOT）
    metrics_source = metrics.get('source', 'test')
    source_label = 'OOT验证集' if metrics_source == 'oot' else '测试集'
    
    # 🔧 添加指标卡头部（数据来源标注在左上）
    html_parts.append('<div class="metric-grid-header">')
    html_parts.append(f'<span class="metric-source-label">数据来源：{source_label}</span>')
    html_parts.append('</div>')
    
    html_parts.append('<div class="metric-grid">')
    # 格式化指标值（防止None导致格式化错误）
    ks_val = metrics.get('ks')
    auc_val = metrics.get('auc')
    gini_val = metrics.get('gini')
    
    ks_display = f"{ks_val * 100:.2f}%" if ks_val is not None else '-'
    auc_display = f"{auc_val:.4f}" if auc_val is not None else '-'
    gini_display = f"{gini_val * 100:.2f}%" if gini_val is not None else '-'
    psi_display = f"{psi_val:.4f}" if psi_val is not None else '-'
    
    # 计算指标评估等级（与前端一致）
    def get_ks_level(ks):
        if ks is None:
            return None
        if ks >= 0.4:
            return ('excellent', '优秀')
        elif ks >= 0.3:
            return ('good', '良好')
        elif ks >= 0.2:
            return ('acceptable', '可用')
        else:
            return ('poor', '较差')
    
    def get_auc_level(auc):
        if auc is None:
            return None
        if auc >= 0.8:
            return ('excellent', '优秀')
        elif auc >= 0.75:
            return ('good', '良好')
        elif auc >= 0.7:
            return ('acceptable', '可用')
        else:
            return ('poor', '较差')
    
    def get_gini_level(gini):
        if gini is None:
            return None
        if gini >= 0.6:
            return ('excellent', '优秀')
        elif gini >= 0.5:
            return ('good', '良好')
        elif gini >= 0.4:
            return ('acceptable', '可用')
        else:
            return ('poor', '较差')
    
    def get_psi_level(psi):
        if psi is None:
            return None
        if psi < 0.1:
            return ('excellent', '稳定')
        elif psi < 0.25:
            return ('good', '轻微变化')
        else:
            return ('acceptable', '显著变化')
    
    ks_level = get_ks_level(ks_val)
    auc_level = get_auc_level(auc_val)
    gini_level = get_gini_level(gini_val)
    psi_level = get_psi_level(psi_val)
    
    html_parts.append(f'''
        <div class="metric-card ks">
            <div class="metric-header">
                <span class="metric-icon">📊</span>
                <span class="metric-name">KS值</span>
            </div>
            <div class="metric-value">{ks_display}</div>
            {f'<span class="metric-level {ks_level[0]}">{ks_level[1]}</span>' if ks_level else ''}
        </div>
        <div class="metric-card auc">
            <div class="metric-header">
                <span class="metric-icon">📈</span>
                <span class="metric-name">AUC</span>
            </div>
            <div class="metric-value">{auc_display}</div>
            {f'<span class="metric-level {auc_level[0]}">{auc_level[1]}</span>' if auc_level else ''}
        </div>
        <div class="metric-card gini">
            <div class="metric-header">
                <span class="metric-icon">📉</span>
                <span class="metric-name">Gini系数</span>
            </div>
            <div class="metric-value">{gini_display}</div>
            {f'<span class="metric-level {gini_level[0]}">{gini_level[1]}</span>' if gini_level else ''}
        </div>
        <div class="metric-card psi">
            <div class="metric-header">
                <span class="metric-icon">⚡</span>
                <span class="metric-name">PSI ({psi_result.get('comparison', '稳定性') if psi_result and isinstance(psi_result, dict) else '稳定性'})</span>
            </div>
            <div class="metric-value">{psi_display}</div>
            {f'<span class="metric-level {psi_level[0]}">{psi_level[1]}</span>' if psi_level else ''}
        </div>
    ''')
    html_parts.append('</div>')
    
    # 数据集指标对比表
    # 2026-02-11: 始终显示OOT验证集行（即使没有数据），与前端行为一致
    html_parts.append('<h4 class="subsection-title">数据集指标对比</h4>')
    html_parts.append('<table class="data-table metrics-table">')
    html_parts.append('''
        <thead>
            <tr>
                <th>数据集</th>
                <th>样本数</th>
                <th>坏账率</th>
                <th>KS</th>
                <th>AUC</th>
                <th>Gini</th>
            </tr>
        </thead>
        <tbody>
    ''')
    
    # 定义所有数据集（包括OOT，即使没有数据也显示）
    dataset_names = {'train': '训练集', 'test': '测试集', 'oot': 'OOT验证集'}
    multi_dataset_metrics = multi_dataset_metrics or {}
    
    for dataset_key, dataset_name in dataset_names.items():
        dataset_metrics = multi_dataset_metrics.get(dataset_key)
        
        if dataset_metrics:
            ks_val = dataset_metrics.get('ks')
            auc_val = dataset_metrics.get('auc')
            gini_val = dataset_metrics.get('gini')
            samples = dataset_metrics.get('samples')
            bad_rate = dataset_metrics.get('bad_rate')
            
            # 格式化数值，防止None导致错误
            samples_str = f"{samples:,}" if samples is not None else '-'
            bad_rate_str = f"{bad_rate:.2f}%" if bad_rate is not None else '-'
            ks_str = f"{ks_val * 100:.2f}%" if ks_val is not None else '-'
            auc_str = f"{auc_val:.4f}" if auc_val is not None else '-'
            gini_str = f"{gini_val * 100:.2f}%" if gini_val is not None else '-'
        else:
            # 无数据时显示 "-"
            samples_str = bad_rate_str = ks_str = auc_str = gini_str = '-'
        
        html_parts.append(f'''
        <tr>
            <td><strong>{dataset_name}</strong></td>
            <td>{samples_str}</td>
            <td>{bad_rate_str}</td>
            <td>{ks_str}</td>
            <td>{auc_str}</td>
            <td>{gini_str}</td>
        </tr>
        ''')
    html_parts.append('</tbody></table>')
    
    # AI 分析（与规则挖掘任务一致：无标题，仅在有内容时显示）
    html_parts.append(_render_ai_analysis_inline(ai_analysis))
    
    html_parts.append('</div>')
    
    # ==========================================================================
    # 二、样本与特征（对应 Tab: sample-data）
    # ==========================================================================
    html_parts.append('<div class="section">')
    html_parts.append('<h2 class="section-title">📋 二、样本与特征</h2>')
    
    # 从 stages 或 results 提取样本数据
    data_loading = stages.get('data_loading', {}) if stages else {}
    data_loading_preview = data_loading.get('output_preview', {}) if isinstance(data_loading, dict) else {}
    woe_binning = stages.get('woe_binning', {}) if stages else {}
    woe_preview = woe_binning.get('output_preview', {}) if isinstance(woe_binning, dict) else {}
    feature_selection = stages.get('feature_selection', {}) if stages else {}
    fs_preview = feature_selection.get('output_preview', {}) if isinstance(feature_selection, dict) else {}
    model_training = stages.get('model_training', {}) if stages else {}
    mt_preview = model_training.get('output_preview', {}) if isinstance(model_training, dict) else {}
    
    # 样本概览（与前端Tab一致：使用列表形式）
    total_rows = data_loading_preview.get('rows', results.get('total_samples', '-'))
    target_rate = data_loading_preview.get('target_rate', results.get('bad_rate', None))
    split_info = data_loading_preview.get('split_info', {})
    
    html_parts.append('<h4 class="subsection-title">样本概览</h4>')
    html_parts.append('<div style="background: #f9fafb; border-radius: 8px; border: 1px solid #e5e7eb; padding: 12px;">')
    
    # 总样本数
    html_parts.append('<div style="display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #e5e7eb;">')
    html_parts.append('<span style="color: #6b7280; font-size: 14px;">总样本数</span>')
    html_parts.append(f'<span style="font-weight: 500; font-size: 14px;">{total_rows:,}</span>' if isinstance(total_rows, int) else '<span style="font-weight: 500;">-</span>')
    html_parts.append('</div>')
    
    # 总体坏账率
    html_parts.append('<div style="display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #e5e7eb;">')
    html_parts.append('<span style="color: #6b7280; font-size: 14px;">总体坏账率</span>')
    if target_rate is not None:
        html_parts.append(f'<span style="font-weight: 500; color: #9333ea; font-size: 14px;">{target_rate * 100:.2f}%</span>')
    else:
        html_parts.append('<span style="font-weight: 500;">-</span>')
    html_parts.append('</div>')
    
    # 训练集
    if split_info.get('train'):
        train_count = split_info.get('train', 0)
        train_rate = split_info.get('train_target_rate')
        rate_str = f"{train_rate * 100:.2f}%" if isinstance(train_rate, (int, float)) else "-"
        html_parts.append('<div style="display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #e5e7eb;">')
        html_parts.append('<span style="color: #6b7280; font-size: 14px;">训练集</span>')
        html_parts.append(f'<span style="font-weight: 500; font-size: 14px;">{train_count:,} <span style="color: #9ca3af; font-size: 12px;">(坏账率: {rate_str})</span></span>')
        html_parts.append('</div>')
    
    # 测试集
    if split_info.get('test'):
        test_count = split_info.get('test', 0)
        test_rate = split_info.get('test_target_rate')
        rate_str = f"{test_rate * 100:.2f}%" if isinstance(test_rate, (int, float)) else "-"
        html_parts.append('<div style="display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #e5e7eb;">')
        html_parts.append('<span style="color: #6b7280; font-size: 14px;">测试集</span>')
        html_parts.append(f'<span style="font-weight: 500; font-size: 14px;">{test_count:,} <span style="color: #9ca3af; font-size: 12px;">(坏账率: {rate_str})</span></span>')
        html_parts.append('</div>')
    
    # OOT验证集（始终显示，与前端一致）
    oot_count = split_info.get('oot', 0)
    html_parts.append('<div style="display: flex; justify-content: space-between; padding: 8px 0;">')
    html_parts.append('<span style="color: #6b7280; font-size: 14px;">OOT验证集</span>')
    if oot_count and oot_count > 0:
        oot_rate = split_info.get('oot_target_rate')
        rate_str = f"{oot_rate * 100:.2f}%" if isinstance(oot_rate, (int, float)) else "-"
        html_parts.append(f'<span style="font-weight: 500; font-size: 14px;">{oot_count:,} <span style="color: #9ca3af; font-size: 12px;">(坏账率: {rate_str})</span></span>')
    else:
        html_parts.append('<span style="color: #9ca3af; font-size: 14px;">未划分</span>')
    html_parts.append('</div>')
    
    html_parts.append('</div>')
    
    # 时间范围（始终展示，与前端Tab一致）
    time_range_info = data_loading_preview.get('time_range_info', {})
    time_col = time_range_info.get('column', '') if time_range_info else ''
    time_col_display = f"（{time_col}）" if time_col else ""
    
    html_parts.append(f'<h4 class="subsection-title">📅 时间范围{time_col_display}</h4>')
    html_parts.append('''
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;">
    ''')
    
    # 训练集时间范围
    train_range = time_range_info.get('train', {}) if time_range_info else {}
    train_min = train_range.get('min', '-') if train_range else '-'
    train_max = train_range.get('max', '-') if train_range else '-'
    html_parts.append(f'''
        <div style="text-align: center; padding: 12px; background: #faf5ff; border-radius: 8px; border: 1px solid #e9d5ff;">
            <div style="font-size: 11px; color: #6b7280; margin-bottom: 4px;">训练集</div>
            <div style="font-size: 13px; font-weight: 500; color: #7c3aed;">{train_min if train_min else '-'}</div>
            <div style="font-size: 10px; color: #9ca3af;">至</div>
            <div style="font-size: 13px; font-weight: 500; color: #7c3aed;">{train_max if train_max else '-'}</div>
        </div>
    ''')
    
    # 测试集时间范围
    test_range = time_range_info.get('test', {}) if time_range_info else {}
    test_min = test_range.get('min', '-') if test_range else '-'
    test_max = test_range.get('max', '-') if test_range else '-'
    html_parts.append(f'''
        <div style="text-align: center; padding: 12px; background: #faf5ff; border-radius: 8px; border: 1px solid #e9d5ff;">
            <div style="font-size: 11px; color: #6b7280; margin-bottom: 4px;">测试集</div>
            <div style="font-size: 13px; font-weight: 500; color: #7c3aed;">{test_min if test_min else '-'}</div>
            <div style="font-size: 10px; color: #9ca3af;">至</div>
            <div style="font-size: 13px; font-weight: 500; color: #7c3aed;">{test_max if test_max else '-'}</div>
        </div>
    ''')
    
    # OOT验证集时间范围
    oot_range = time_range_info.get('oot', {}) if time_range_info else {}
    oot_min = oot_range.get('min', '-') if oot_range else '-'
    oot_max = oot_range.get('max', '-') if oot_range else '-'
    html_parts.append(f'''
        <div style="text-align: center; padding: 12px; background: #faf5ff; border-radius: 8px; border: 1px solid #e9d5ff;">
            <div style="font-size: 11px; color: #6b7280; margin-bottom: 4px;">OOT验证集</div>
            <div style="font-size: 13px; font-weight: 500; color: #7c3aed;">{oot_min if oot_min else '-'}</div>
            <div style="font-size: 10px; color: #9ca3af;">至</div>
            <div style="font-size: 13px; font-weight: 500; color: #7c3aed;">{oot_max if oot_max else '-'}</div>
        </div>
    ''')
    
    html_parts.append('</div>')
    
    # 特征概览（与前端Tab一致：原始特征数、异常值特征数、平均缺失率）
    var_filter_result = data_loading_preview.get('var_filter_result', {})
    original_features = var_filter_result.get('input_features') or data_loading_preview.get('columns') or '-'
    outlier_count = data_loading_preview.get('outlier_count', '-')
    missing_rate = data_loading_preview.get('missing_rate')
    missing_rate_display = f"{missing_rate * 100:.1f}%" if missing_rate is not None else '-'
    
    html_parts.append('<h4 class="subsection-title">📊 特征概览</h4>')
    html_parts.append('''
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;">
    ''')
    
    html_parts.append(f'''
        <div style="padding: 12px; background: #f0fdf4; border-radius: 8px; border: 1px solid #bbf7d0;">
            <div style="font-size: 24px; font-weight: bold; color: #16a34a;">{original_features}</div>
            <div style="font-size: 11px; color: #6b7280;">原始特征数</div>
        </div>
        <div style="padding: 12px; background: #fefce8; border-radius: 8px; border: 1px solid #fef08a;">
            <div style="font-size: 24px; font-weight: bold; color: #ca8a04;">{outlier_count if outlier_count is not None else '-'}</div>
            <div style="font-size: 11px; color: #6b7280;">异常值特征数</div>
        </div>
        <div style="padding: 12px; background: #fefce8; border-radius: 8px; border: 1px solid #fef08a;">
            <div style="font-size: 24px; font-weight: bold; color: #ca8a04;">{missing_rate_display}</div>
            <div style="font-size: 11px; color: #6b7280;">平均缺失率</div>
        </div>
    ''')
    
    html_parts.append('</div>')
    
    html_parts.append('</div>')
    
    # ==========================================================================
    # 三、评估图表（对应 Tab: charts）
    # 2026-02-11 优化：删除3.1多数据集性能汇总（与概览重复），直接展示各数据集详情
    # 结构：3.1 OOT验证集 → 3.2 测试集 → 3.3 训练集（OOT优先展示）
    # ==========================================================================
    if include_charts:
        _init_scorecard_viz()  # Lazy init
        if SCORECARD_VIZ_AVAILABLE:
            html_parts.append('<div class="section">')
            html_parts.append('<h2 class="section-title">📈 三、评估图表</h2>')
            
            # 从 stages 获取数据集划分信息
            split_info = {}
            if stages:
                data_prep = stages.get('data_preparation', {})
                if isinstance(data_prep, dict):
                    preview = data_prep.get('output_preview', {})
                    split_info = preview.get('split_info', {})
            
            # 判断是否有 OOT
            has_oot = bool(multi_dataset_metrics.get('oot') if multi_dataset_metrics else False) or \
                      bool(multi_dataset_chart_data.get('oot') if multi_dataset_chart_data else False)
            
            # PSI数据
            psi_result = results.get('psi_result')
            psi_train_vs_test = results.get('psi_train_vs_test')
            psi_train_vs_oot = results.get('psi_train_vs_oot')
            if psi_train_vs_test is None and psi_result and isinstance(psi_result, dict) and psi_result.get('comparison') == '训练集 vs 测试集':
                psi_train_vs_test = psi_result
            if psi_train_vs_oot is None and psi_result and isinstance(psi_result, dict) and psi_result.get('comparison') == '训练集 vs OOT':
                psi_train_vs_oot = psi_result
            
            # 过拟合警告（移至各数据集详情之前）
            if overfit_warning and str(overfit_warning).strip() and overfit_warning != 'None':
                html_parts.append(f'''
                <div class="warning-box" style="margin-bottom: 16px;">
                    ⚠️ <strong>过拟合警告</strong>：{overfit_warning}
                </div>
                ''')
            
            # ==================== 3.1-3.3 按数据集展示详情 ====================
            # 图表索引收集
            chart_index = []
            subsection_num = 1  # 从3.1开始编号
            
            # 数据集展示顺序：OOT优先 → 测试集 → 训练集
            datasets_to_show = []
            if has_oot:
                datasets_to_show.append(('oot', 'OOT验证集', '用于评估模型时间外泛化能力', psi_train_vs_oot, '训练集 vs OOT'))
            datasets_to_show.append(('test', '测试集', '用于验证模型在同期数据上的泛化表现', psi_train_vs_test, '训练集 vs 测试集'))
            datasets_to_show.append(('train', '训练集', '作为基准参照（可能存在过拟合）', None, None))
            
            dataset_names = {'train': '训练集', 'test': '测试集', 'oot': 'OOT验证集'}
            
            for dataset_key, dataset_label, description, psi_data, psi_comparison in datasets_to_show:
                ds_chart_data = (multi_dataset_chart_data or {}).get(dataset_key, {})
                if ds_chart_data is None:
                    ds_chart_data = {}
                dataset_m = (multi_dataset_metrics or {}).get(dataset_key, {})
                
                # 计算图表数量
                chart_count = 0
                if ds_chart_data.get('roc'):
                    chart_count += 1
                if ds_chart_data.get('ks'):
                    chart_count += 1
                score_dist_temp = ds_chart_data.get('score_distribution', {})
                if score_dist_temp:
                    chart_count += 2  # Lift曲线 + 评分分布图
                    # 排序性分析表：所有数据集都显示（便于对比判断过拟合）
                    ranking_bins_temp = score_dist_temp.get('ranking_analysis', {}).get('bins') or score_dist_temp.get('bins')
                    if ranking_bins_temp and len(ranking_bins_temp) > 0:
                        chart_count += 1  # 排序性分析表
                if psi_data:
                    chart_count += 1
                
                html_parts.append(f'<h4 class="subsection-title">3.{subsection_num} {dataset_label}（{chart_count}项）</h4>')
                html_parts.append(f'<p style="font-size: 12px; color: #6b7280; margin-bottom: 12px;"><em>{description}</em></p>')
                
                # 3.x.1 性能曲线（ROC + KS）
                has_roc = 'roc' in ds_chart_data
                has_ks = 'ks' in ds_chart_data
                
                if has_roc or has_ks:
                    html_parts.append('<h5 style="font-size: 13px; color: #374151; margin: 12px 0 8px 0;">📈 性能曲线</h5>')
                    html_parts.append('<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 16px;">')
                    
                    if has_roc:
                        try:
                            roc_html = _generate_roc_chart_from_data(ds_chart_data['roc'], width=450, height=320)
                            html_parts.append(f'<div class="chart-container" style="min-height: 340px;">{roc_html}</div>')
                            chart_index.append((dataset_label, 'ROC曲线', '✅'))
                        except Exception as e:
                            html_parts.append(f'<div style="padding: 20px; color:#999; background: #f9f9f9; border-radius: 8px;">ROC图表生成失败: {e}</div>')
                            chart_index.append((dataset_label, 'ROC曲线', '❌'))
                    
                    if has_ks:
                        try:
                            ks_html = _generate_ks_chart_from_data(ds_chart_data['ks'], width=450, height=320)
                            html_parts.append(f'<div class="chart-container" style="min-height: 340px;">{ks_html}</div>')
                            chart_index.append((dataset_label, 'KS曲线', '✅'))
                        except Exception as e:
                            html_parts.append(f'<div style="padding: 20px; color:#999; background: #f9f9f9; border-radius: 8px;">KS图表生成失败: {e}</div>')
                            chart_index.append((dataset_label, 'KS曲线', '❌'))
                    
                    html_parts.append('</div>')
                
                # 3.x.2 排序性分析表（所有数据集都显示，便于对比判断过拟合）
                score_dist = ds_chart_data.get('score_distribution', {})
                ranking_bins = score_dist.get('ranking_analysis', {}).get('bins') or score_dist.get('bins')
                
                if ranking_bins and len(ranking_bins) > 0:
                    html_parts.append(f'<h5 style="font-size: 13px; color: #374151; margin: 12px 0 8px 0;">📊 排序性分析表</h5>')
                    html_parts.append('<table class="data-table" style="font-size: 12px;">')
                    html_parts.append('''
                        <thead>
                            <tr>
                                <th>评分区间</th>
                                <th class="text-right">样本数</th>
                                <th class="text-right">占比</th>
                                <th class="text-right">坏样本数</th>
                                <th class="text-right">坏样本率</th>
                                <th class="text-right">Lift</th>
                            </tr>
                        </thead>
                        <tbody>
                    ''')
                    for bin_data in ranking_bins:
                        bin_label = bin_data.get('bin', bin_data.get('score_range', '-'))
                        count = bin_data.get('count', bin_data.get('total', 0))
                        pct = bin_data.get('pct', bin_data.get('percent', bin_data.get('pct_total', 0)))
                        bad_count = bin_data.get('bad', bin_data.get('bad_count', 0))
                        bad_rate = bin_data.get('bad_rate', 0)
                        lift = bin_data.get('lift', 0)
                        
                        lift_color = '#dc2626' if lift > 1 else '#16a34a' if lift < 1 else '#374151'
                        pct_display = pct * 100 if pct < 1 else pct  # 处理百分比格式
                        
                        # bad_rate在数据中已经是百分比形式（如20.5表示20.5%），不需要再乘以100
                        bad_rate_display = bad_rate if bad_rate is not None else 0
                        
                        html_parts.append(f'''
                            <tr>
                                <td>{bin_label}</td>
                                <td class="text-right">{count:,}</td>
                                <td class="text-right">{pct_display:.1f}%</td>
                                <td class="text-right">{bad_count:,}</td>
                                <td class="text-right">{bad_rate_display:.2f}%</td>
                                <td class="text-right" style="color: {lift_color}; font-weight: 500;">{lift:.2f}</td>
                            </tr>
                        ''')
                    html_parts.append('</tbody></table>')
                    
                    # 单调性分析
                    rank_analysis = score_dist.get('rank_ordering_analysis', {})
                    monotonicity = rank_analysis.get('monotonicity', {})
                    mono_pass = monotonicity.get('is_monotonic', False)
                    mono_violations = monotonicity.get('violations', 0)
                    first_lift = ranking_bins[0].get('lift') if ranking_bins else None
                    last_lift = ranking_bins[-1].get('lift') if ranking_bins else None
                    
                    mono_str = "✅ 通过" if mono_pass else f"⚠️ 不通过（{mono_violations}处违反）"
                    first_str = f"{first_lift:.2f}" if first_lift is not None else "-"
                    last_str = f"{last_lift:.2f}" if last_lift is not None else "-"
                    
                    html_parts.append(f'''
                        <p style="font-size: 12px; color: #6b7280; margin-top: 8px;">
                            <strong>单调性</strong>：{mono_str} | 
                            <strong>首组Lift</strong>：{first_str} | 
                            <strong>末组Lift</strong>：{last_str}
                        </p>
                    ''')
                    chart_index.append((dataset_label, '排序性分析表', '✅'))
                
                # 3.x.3 评分分布图 + Lift曲线（并排）
                if score_dist:
                    html_parts.append('<h5 style="font-size: 13px; color: #374151; margin: 16px 0 8px 0;">📊 评分分布与Lift曲线</h5>')
                    html_parts.append('<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">')
                    
                    # 评分分布图
                    try:
                        dist_html = _generate_score_dist_chart_from_data(
                            score_dist, 
                            width=450, 
                            height=320,
                            dataset_label=dataset_label
                        )
                        html_parts.append(f'<div class="chart-container">{dist_html}</div>')
                        chart_index.append((dataset_label, '评分分布图', '✅'))
                    except Exception as e:
                        html_parts.append(f'<div style="padding: 20px; color:#999; background: #f9f9f9; border-radius: 8px;">评分分布图生成失败: {e}</div>')
                        chart_index.append((dataset_label, '评分分布图', '❌'))
                    
                    # Lift曲线（所有数据集都显示，便于对比判断过拟合）
                    if ranking_bins:
                        try:
                            lift_html = _generate_lift_chart_from_data(
                                ranking_bins, 
                                width=450, 
                                height=320,
                                dataset_label=dataset_label
                            )
                            html_parts.append(f'<div class="chart-container">{lift_html}</div>')
                            chart_index.append((dataset_label, 'Lift曲线', '✅'))
                        except Exception as e:
                            html_parts.append(f'<div style="padding: 20px; color:#999; background: #f9f9f9; border-radius: 8px;">Lift图表生成失败: {e}</div>')
                            chart_index.append((dataset_label, 'Lift曲线', '❌'))
                    
                    html_parts.append('</div>')
                
                # 3.x.4 PSI稳定性（仅OOT和测试集有PSI数据）
                if psi_data and dataset_key in ('test', 'oot'):
                    psi_value = psi_data.get('value', 0) if isinstance(psi_data, dict) else 0
                    stability = psi_data.get('stability', '-') if isinstance(psi_data, dict) else '-'
                    level = psi_data.get('level', 'unknown') if isinstance(psi_data, dict) else 'unknown'
                    
                    level_icon = "✅" if level == 'good' else "⚠️" if level == 'warning' else "❌"
                    level_color = "#16a34a" if level == 'good' else "#ca8a04" if level == 'warning' else "#dc2626"
                    
                    html_parts.append(f'<h5 style="font-size: 13px; color: #374151; margin: 16px 0 8px 0;">📊 PSI稳定性（{psi_comparison}）</h5>')
                    
                    # PSI分布对比图
                    train_dist = (multi_dataset_chart_data or {}).get('train', {}).get('score_distribution', {})
                    train_bins = train_dist.get('distribution_analysis', {}).get('bins') or train_dist.get('bins')
                    compare_dist = ds_chart_data.get('score_distribution', {})
                    compare_bins = compare_dist.get('distribution_analysis', {}).get('bins') or compare_dist.get('bins')
                    
                    if train_bins and compare_bins:
                        try:
                            psi_html = _generate_psi_comparison_chart(train_bins, compare_bins, dataset_label, psi_value, width=600, height=320)
                            html_parts.append(f'<div class="chart-container">{psi_html}</div>')
                            chart_index.append((dataset_label, f'PSI分布对比（{psi_comparison}）', '✅'))
                        except Exception as e:
                            html_parts.append(f'<div style="padding: 20px; color:#999; background: #f9f9f9; border-radius: 8px;">PSI对比图生成失败: {e}</div>')
                            chart_index.append((dataset_label, f'PSI分布对比（{psi_comparison}）', '❌'))
                    else:
                        # 无分布数据时只显示PSI结果
                        html_parts.append(f'''
                        <div style="display: flex; gap: 16px; align-items: center; padding: 12px; background: #f9fafb; border-radius: 8px;">
                            <div style="font-size: 24px; font-weight: bold; color: {level_color};">{psi_value:.4f}</div>
                            <div>
                                <div style="font-size: 14px;">{level_icon} {stability}</div>
                                <div style="font-size: 11px; color: #9ca3af;">PSI评级标准：&lt;0.1 稳定，0.1-0.25 轻微变化，&gt;0.25 显著变化</div>
                            </div>
                        </div>
                        ''')
                
                # 分隔线
                html_parts.append('<hr style="margin: 20px 0; border: none; border-top: 1px solid #e5e7eb;">')
                subsection_num += 1
            
            # 图表索引已移除（HTML报告可直接查看图表，无需索引）
            
            html_parts.append('</div>')  # section 结束
    
    # ==========================================================================
    # 四、评分卡明细（对应 Tab: scorecard）
    # 2026-02-09: 与前端保持一致，使用 full_scorecard_csv 数据，展示完整信息
    # ==========================================================================
    score_scaling = stages.get('score_scaling', {}) if stages else {}
    score_scaling_preview = score_scaling.get('output_preview', {}) if isinstance(score_scaling, dict) else {}
    full_scorecard_csv = score_scaling_preview.get('full_scorecard_csv', [])
    
    if full_scorecard_csv or (scorecard is not None and len(scorecard) > 0):
        html_parts.append('<div class="section">')
        html_parts.append('<h2 class="section-title">📋 四、评分卡明细</h2>')
        
        # 4.1 核心参数指标卡
        num_vars = score_scaling_preview.get('num_variables', 0)
        theoretical_range = score_scaling_preview.get('theoretical_score_range', {})
        base_score = score_scaling_preview.get('base_score', 600)
        base_odds = score_scaling_preview.get('base_odds', 20)
        pdo = score_scaling_preview.get('pdo', 50)
        
        # 获取评分分布统计数据（按优先级：OOT > 测试集 > 训练集）
        score_stats_by_dataset = score_scaling_preview.get('score_stats_by_dataset', {})
        actual_stats = score_scaling_preview.get('actual_score_stats', {})  # 兜底：旧字段（训练集）
        stats_dataset_label = "训练集"
        
        if score_stats_by_dataset:
            if score_stats_by_dataset.get('oot'):
                actual_stats = score_stats_by_dataset['oot']
                stats_dataset_label = "OOT验证集"
            elif score_stats_by_dataset.get('test'):
                actual_stats = score_stats_by_dataset['test']
                stats_dataset_label = "测试集"
            elif score_stats_by_dataset.get('train'):
                actual_stats = score_stats_by_dataset['train']
                stats_dataset_label = "训练集"
        
        # ========== 第一行指标卡：入模变量数 + 评分区间 + 基准配置 ==========
        html_parts.append('<p style="font-size: 13px; color: #6b7280; margin-bottom: 8px;">评分卡核心参数与入模变量评分贡献概览</p>')
        html_parts.append('''
        <div style="display: flex; gap: 16px; margin-bottom: 12px; flex-wrap: wrap;">
        ''')
        
        # 入模变量数
        html_parts.append(f'''
        <div style="flex: 1; min-width: 150px; padding: 12px 16px; border-radius: 8px; 
                    border: 1px solid #e5e7eb; background: #f0fdf4;">
            <div style="font-size: 10px; color: #6b7280; margin-bottom: 4px;">入模变量数</div>
            <div style="font-size: 24px; font-weight: bold; color: #16a34a;">{num_vars}</div>
        </div>
        ''')
        
        # 评分区间（与前端对齐：显示数据集、分数取整、均值/中位数/IQR小字指标）
        if theoretical_range.get('min') is not None and theoretical_range.get('max') is not None:
            # 理论区间取整
            score_min = int(round(theoretical_range.get('min', 0)))
            score_max = int(round(theoretical_range.get('max', 0)))
            
            # 小字指标：均值/中位数/IQR
            stats_detail = ""
            if actual_stats:
                mean_val = actual_stats.get('mean')
                median_val = actual_stats.get('median')
                q25 = actual_stats.get('q25')
                q75 = actual_stats.get('q75')
                
                details = []
                if mean_val is not None:
                    details.append(f"均值 {int(round(mean_val))}")
                if median_val is not None:
                    details.append(f"中位数 {int(round(median_val))}")
                if q25 is not None and q75 is not None:
                    details.append(f"IQR {int(round(q25))}-{int(round(q75))}")
                
                if details:
                    stats_detail = "  ".join(details)
            
            html_parts.append(f'''
            <div style="flex: 1; min-width: 200px; padding: 12px 16px; border-radius: 8px;
                        border: 1px solid #e5e7eb; background: #eff6ff;">
                <div style="font-size: 10px; color: #6b7280; margin-bottom: 4px;">
                    评分区间 <span style="font-size: 9px; color: #9ca3af;">({stats_dataset_label})</span>
                </div>
                <div style="font-size: 24px; font-weight: bold; color: #2563eb;">
                    {score_min} ~ {score_max}
                </div>
                <div style="font-size: 10px; color: #9ca3af; margin-top: 2px;">{stats_detail}</div>
            </div>
            ''')
        
        # 基准配置
        html_parts.append(f'''
        <div style="flex: 1; min-width: 150px; padding: 12px 16px; border-radius: 8px;
                    border: 1px solid #e5e7eb; background: #f9fafb;">
            <div style="font-size: 10px; color: #6b7280; margin-bottom: 4px;">基准配置</div>
            <div style="font-size: 24px; font-weight: bold; color: #374151;">
                {base_score}/{base_odds}/{pdo}
            </div>
            <div style="font-size: 10px; color: #9ca3af;">基准分/Odds/PDO</div>
        </div>
        ''')
        
        html_parts.append('</div>')
        
        # ========== 第二行指标卡：好样本均分 + 坏样本均分 + 分离度 ==========
        # 按优先级选择数据集：OOT > 测试集 > 训练集
        selected_dist_data = None
        dataset_label = ""
        for ds_key, ds_label in [('oot', 'OOT验证集'), ('test', '测试集'), ('train', '训练集')]:
            ds_chart = (multi_dataset_chart_data or {}).get(ds_key, {})
            if ds_chart and ds_chart.get('score_distribution'):
                selected_dist_data = ds_chart.get('score_distribution', {})
                dataset_label = ds_label
                break
        
        if selected_dist_data:
            summary = selected_dist_data.get('summary', {})
            good_mean = summary.get('good_mean')
            bad_mean = summary.get('bad_mean')
            
            if good_mean is not None or bad_mean is not None:
                separation = abs(good_mean - bad_mean) if good_mean is not None and bad_mean is not None else None
                
                # 分离度评级
                if separation is not None:
                    if separation >= 60:
                        sep_rating = "★ 优秀"
                        sep_color = "#d97706"
                    elif separation >= 40:
                        sep_rating = "✓ 良好"
                        sep_color = "#16a34a"
                    elif separation >= 20:
                        sep_rating = "○ 合格"
                        sep_color = "#2563eb"
                    else:
                        sep_rating = "△ 偏低"
                        sep_color = "#dc2626"
                else:
                    sep_rating = ""
                    sep_color = "#374151"
                
                html_parts.append('''
                <div style="display: flex; gap: 16px; margin-bottom: 16px; flex-wrap: wrap;">
                ''')
                
                # 好样本均分
                if good_mean is not None:
                    html_parts.append(f'''
                    <div style="flex: 1; min-width: 140px; padding: 12px 16px; border-radius: 8px;
                                border: 1px solid #bbf7d0; background: #f0fdf4;">
                        <div style="font-size: 10px; color: #6b7280; margin-bottom: 4px;">
                            好样本均分 <span style="font-size: 9px; color: #9ca3af;">({dataset_label})</span>
                        </div>
                        <div style="font-size: 24px; font-weight: bold; color: #16a34a;">{good_mean:.1f}</div>
                    </div>
                    ''')
                
                # 坏样本均分
                if bad_mean is not None:
                    html_parts.append(f'''
                    <div style="flex: 1; min-width: 140px; padding: 12px 16px; border-radius: 8px;
                                border: 1px solid #fecaca; background: #fef2f2;">
                        <div style="font-size: 10px; color: #6b7280; margin-bottom: 4px;">
                            坏样本均分 <span style="font-size: 9px; color: #9ca3af;">({dataset_label})</span>
                        </div>
                        <div style="font-size: 24px; font-weight: bold; color: #dc2626;">{bad_mean:.1f}</div>
                    </div>
                    ''')
                
                # 分离度
                if separation is not None:
                    html_parts.append(f'''
                    <div style="flex: 1; min-width: 140px; padding: 12px 16px; border-radius: 8px;
                                border: 1px solid #fde68a; background: #fffbeb;">
                        <div style="font-size: 10px; color: #6b7280; margin-bottom: 4px;">
                            分离度 <span style="font-size: 9px; color: #9ca3af;">(好-坏差值)</span>
                        </div>
                        <div style="font-size: 24px; font-weight: bold; color: {sep_color};">{separation:.1f}</div>
                        <div style="font-size: 10px; color: #9ca3af;">{sep_rating}</div>
                    </div>
                    ''')
                
                html_parts.append('</div>')
        
        # 4.3 入模变量评分贡献（条形图）- 放在表格之前
        scorecard_preview = score_scaling_preview.get('scorecard_preview', [])
        if scorecard_preview and len(scorecard_preview) > 0:
            # 筛选出有效变量（排除常数项）
            valid_vars = [v for v in scorecard_preview if v.get('variable') not in ('basepoints', '常数项')]
            
            if valid_vars:
                # 按波动幅度排序（max - min score）
                for v in valid_vars:
                    min_score = v.get('min_score', 0) or 0
                    max_score = v.get('max_score', 0) or 0
                    v['_score_range'] = abs(max_score - min_score)
                
                sorted_vars = sorted(valid_vars, key=lambda x: x.get('_score_range', 0), reverse=True)[:10]  # 最多显示10个
                max_range = max(v.get('_score_range', 0) for v in sorted_vars) if sorted_vars else 1
                
                html_parts.append('<h4 class="subsection-title">📊 入模变量评分贡献</h4>')
                html_parts.append('<div style="margin-bottom: 16px;">')
                
                for v in sorted_vars:
                    var_name = v.get('variable', '')
                    min_score = v.get('min_score', 0) or 0
                    max_score = v.get('max_score', 0) or 0
                    score_range = v.get('_score_range', 0)
                    bar_width = (score_range / max_range * 100) if max_range > 0 else 0
                    
                    # 变量名截断
                    var_display = var_name[:20] + '...' if len(var_name) > 20 else var_name
                    
                    html_parts.append(f'''
                    <div style="display: flex; align-items: center; margin-bottom: 8px;">
                        <div style="width: 150px; font-size: 12px; color: #374151; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="{var_name}">{var_display}</div>
                        <div style="flex: 1; height: 20px; background: #f3f4f6; border-radius: 4px; margin: 0 12px; position: relative;">
                            <div style="height: 100%; width: {bar_width:.1f}%; background: linear-gradient(90deg, #fbbf24, #f59e0b); border-radius: 4px;"></div>
                        </div>
                        <div style="width: 80px; font-size: 11px; color: #6b7280; text-align: right;">{min_score:.0f}~{max_score:.0f}</div>
                        <div style="width: 50px; font-size: 12px; font-weight: 600; color: #d97706; text-align: right;">{score_range:.0f}分</div>
                    </div>
                    ''')
                
                html_parts.append('<p style="font-size: 11px; color: #9ca3af; margin-top: 8px;">* 波动幅度 = 最高分 - 最低分，反映变量对评分的影响程度</p>')
                html_parts.append('</div>')
        
        # 4.4 完整评分卡表格（与前端对齐：变量名、IV、系数合并居中，添加边框）
        if full_scorecard_csv and len(full_scorecard_csv) > 0:
            html_parts.append('<h4 class="subsection-title">完整评分卡 <span style="font-weight: normal; color: #9ca3af; font-size: 12px;">(样本统计基于训练集)</span></h4>')
            
            # 预计算每个变量的行数（用于rowSpan合并单元格）
            variable_row_counts = {}
            for row in full_scorecard_csv:
                var_name = row.get('variable', '')
                variable_row_counts[var_name] = variable_row_counts.get(var_name, 0) + 1
            
            # 记录已处理的变量（用于判断是否显示合并单元格）
            processed_variables = set()
            
            # 表格样式：深蓝色标题行配白色文字
            html_parts.append('''
            <table class="data-table" style="border-collapse: collapse; width: 100%;">
            <thead><tr>
                <th style="border: 1px solid #1a4570; text-align: center; padding: 8px; background: #1F4E79; color: white;">变量</th>
                <th style="border: 1px solid #1a4570; text-align: center; padding: 8px; background: #1F4E79; color: white;">IV</th>
                <th style="border: 1px solid #1a4570; text-align: center; padding: 8px; background: #1F4E79; color: white;">系数</th>
                <th style="border: 1px solid #1a4570; text-align: center; padding: 8px; background: #1F4E79; color: white;">序号</th>
                <th style="border: 1px solid #1a4570; text-align: center; padding: 8px; background: #1F4E79; color: white;">分箱</th>
                <th style="border: 1px solid #1a4570; text-align: center; padding: 8px; background: #1F4E79; color: white;">样本数</th>
                <th style="border: 1px solid #1a4570; text-align: center; padding: 8px; background: #1F4E79; color: white;">占比</th>
                <th style="border: 1px solid #1a4570; text-align: center; padding: 8px; background: #1F4E79; color: white;">好样本</th>
                <th style="border: 1px solid #1a4570; text-align: center; padding: 8px; background: #1F4E79; color: white;">坏样本</th>
                <th style="border: 1px solid #1a4570; text-align: center; padding: 8px; background: #1F4E79; color: white;">坏率</th>
                <th style="border: 1px solid #1a4570; text-align: center; padding: 8px; background: #1F4E79; color: white;">WOE</th>
                <th style="border: 1px solid #1a4570; text-align: center; padding: 8px; background: #1F4E79; color: white;">评分</th>
            </tr></thead>
            <tbody>
            ''')
            
            for idx, row in enumerate(full_scorecard_csv):
                var = row.get('variable', '-')
                iv = row.get('total_iv', '')
                cof = row.get('cof', '')
                bin_idx = row.get('index', '')
                bin_name = row.get('bin', '-')
                count = row.get('count', '')
                count_distr = row.get('count_distr', '')
                good = row.get('good', '')
                bad = row.get('bad', '')
                badprob = row.get('badprob', '')
                woe = row.get('woe', '')
                score = row.get('score', '')
                
                # 格式化数值
                iv_str = f"{iv:.4f}" if isinstance(iv, (int, float)) else (str(iv) if iv else '-')
                cof_str = f"{cof:.4f}" if isinstance(cof, (int, float)) else (str(cof) if cof else '-')
                woe_str = f"{woe:.4f}" if isinstance(woe, (int, float)) else str(woe)
                score_str = f"{score:.2f}" if isinstance(score, (int, float)) else str(score)
                
                # 判断是否为变量的第一行
                is_basepoints = var in ('常数项', 'basepoints')
                is_first_row_of_variable = var not in processed_variables
                row_span = variable_row_counts.get(var, 1)
                
                if is_first_row_of_variable:
                    processed_variables.add(var)
                
                # 单元格背景色
                merged_cell_bg = '#fffbeb' if is_basepoints else '#f8fafc'  # 常数项黄色，普通变量浅灰
                row_bg = '#fffbeb' if is_basepoints else ''
                
                # 变量分隔线（非第一行的变量第一行添加上边框加粗）
                border_top = '2px solid #cbd5e1' if is_first_row_of_variable and idx > 0 else '1px solid #e5e7eb'
                
                html_parts.append(f'<tr style="background: {row_bg};">')
                
                # 变量名、IV、系数 - 合并单元格（仅在变量的第一行显示）
                if is_first_row_of_variable:
                    var_display = '常数项' if is_basepoints else var
                    html_parts.append(f'''
                        <td rowspan="{row_span}" style="border: 1px solid #e5e7eb; border-top: {border_top}; text-align: center; vertical-align: middle; padding: 6px; font-family: monospace; background: {merged_cell_bg};">{var_display}</td>
                        <td rowspan="{row_span}" style="border: 1px solid #e5e7eb; border-top: {border_top}; text-align: center; vertical-align: middle; padding: 6px; color: #6b7280; background: {merged_cell_bg};">{iv_str}</td>
                        <td rowspan="{row_span}" style="border: 1px solid #e5e7eb; border-top: {border_top}; text-align: center; vertical-align: middle; padding: 6px; color: #6b7280; background: {merged_cell_bg};">{cof_str}</td>
                    ''')
                
                # 其他列（每行都显示）
                cell_border_top = border_top if is_first_row_of_variable else '1px solid #e5e7eb'
                
                html_parts.append(f'<td style="border: 1px solid #e5e7eb; border-top: {cell_border_top}; text-align: center; padding: 6px;">{bin_idx}</td>')
                html_parts.append(f'<td style="border: 1px solid #e5e7eb; border-top: {cell_border_top}; text-align: left; padding: 6px;">{bin_name}</td>')
                html_parts.append(f'<td style="border: 1px solid #e5e7eb; border-top: {cell_border_top}; text-align: right; padding: 6px;">{count}</td>')
                html_parts.append(f'<td style="border: 1px solid #e5e7eb; border-top: {cell_border_top}; text-align: right; padding: 6px;">{count_distr}</td>')
                html_parts.append(f'<td style="border: 1px solid #e5e7eb; border-top: {cell_border_top}; text-align: right; padding: 6px; color: #16a34a;">{good}</td>')
                html_parts.append(f'<td style="border: 1px solid #e5e7eb; border-top: {cell_border_top}; text-align: right; padding: 6px; color: #dc2626;">{bad}</td>')
                html_parts.append(f'<td style="border: 1px solid #e5e7eb; border-top: {cell_border_top}; text-align: right; padding: 6px;">{badprob}</td>')
                html_parts.append(f'<td style="border: 1px solid #e5e7eb; border-top: {cell_border_top}; text-align: right; padding: 6px;">{woe_str}</td>')
                
                # 评分带颜色
                score_color = '#16a34a' if isinstance(score, (int, float)) and score > 0 else '#dc2626' if isinstance(score, (int, float)) and score < 0 else '#374151'
                html_parts.append(f'<td style="border: 1px solid #e5e7eb; border-top: {cell_border_top}; text-align: right; padding: 6px; font-weight: 600; color: {score_color};">{score_str}</td>')
                html_parts.append('</tr>')
            
            html_parts.append('</tbody></table>')
            html_parts.append(f'<p style="font-size: 12px; color: #6b7280;">共 {len(full_scorecard_csv)} 条分箱记录</p>')
        
        # 回退：如果没有 full_scorecard_csv，使用旧格式
        elif scorecard is not None and len(scorecard) > 0:
            html_parts.append(f'<p>共 {len(scorecard)} 条分箱记录</p>')
            html_parts.append(scorecard.to_html(index=False, classes='data-table'))
        
        html_parts.append('</div>')
    
    # ==========================================================================
    # 五、变量筛选（对应 Tab: selection）
    # 与前端保持一致：特征筛选漏斗 + 变量IV排行（含淘汰信息）+ 逐步回归详情
    # ==========================================================================
    html_parts.append('<div class="section">')
    html_parts.append('<h2 class="section-title">🔍 五、变量筛选</h2>')
    
    # ========== 5.1 特征筛选漏斗概览 ==========
    # 从 stages 数据获取各阶段特征数量
    data_loading_preview = stages.get('data_loading', {}).get('output_preview', {})
    woe_binning_preview = stages.get('woe_binning', {}).get('output_preview', {})
    feature_selection_preview = stages.get('feature_selection', {}).get('output_preview', {})
    model_training_preview = stages.get('model_training', {}).get('output_preview', {})
    
    var_filter_result = data_loading_preview.get('var_filter_result', {})
    
    # 阶段1: 原始特征数
    original_count = var_filter_result.get('input_features') or data_loading_preview.get('feature_count') or 0
    # 阶段2: 数据质量筛选后
    var_filter_removed = var_filter_result.get('removed_features', [])
    var_filter_removed_count = len(var_filter_removed) if isinstance(var_filter_removed, list) else 0
    after_var_filter = var_filter_result.get('output_features') or (original_count - var_filter_removed_count) or 0
    # 阶段3: WOE分箱后
    woe_output = woe_binning_preview.get('total_features') or woe_binning_preview.get('n_features') or 0
    # 阶段4: 特征筛选后
    fe_after = feature_selection_preview.get('after_count') or feature_selection_preview.get('selected_count') or 0
    # 阶段5: 最终入模（从scorecard或coefficients获取，与前端Tab保持一致）
    # 优先从scorecard获取（排除basepoints常数项）
    if scorecard is not None and len(scorecard) > 0:
        if isinstance(scorecard, pd.DataFrame):
            # DataFrame格式，从variable列获取
            final_count = len([v for v in scorecard['variable'].unique() if v != 'basepoints']) if 'variable' in scorecard.columns else len(scorecard)
        elif isinstance(scorecard, dict):
            # 字典格式，排除basepoints
            final_count = len([k for k in scorecard.keys() if k != 'basepoints'])
        else:
            final_count = len(scorecard)
    elif coefficients is not None and len(coefficients) > 0:
        # 从coefficients获取（排除截距项）
        if isinstance(coefficients, pd.DataFrame):
            final_count = len([v for v in coefficients['feature'].unique() if v != 'intercept']) if 'feature' in coefficients.columns else len(coefficients)
        elif isinstance(coefficients, list):
            final_count = len([c for c in coefficients if c.get('feature') != 'intercept'])
        else:
            final_count = len(coefficients)
    else:
        # 后备：使用model_training的系数数量
        mt_coefficients = model_training_preview.get('coefficients', []) or model_training_preview.get('all_coefficients', [])
        final_count = len([c for c in mt_coefficients if c.get('feature') != 'intercept']) if mt_coefficients else 0
    
    if original_count > 0:
        html_parts.append('<h4 class="subsection-title">特征筛选漏斗</h4>')
        html_parts.append('''
        <div style="display: flex; align-items: center; justify-content: center; gap: 8px; flex-wrap: wrap; padding: 12px 0; margin-bottom: 16px;">
        ''')
        
        funnel_steps = [
            {"label": "原始特征", "count": original_count, "color": "#374151", "bg": "#f9fafb"},
            {"label": "质量筛选", "count": after_var_filter, "color": "#ea580c", "bg": "#fff7ed"},
            {"label": "WOE分箱", "count": woe_output, "color": "#2563eb", "bg": "#eff6ff"},
            {"label": "IV/相关/VIF", "count": fe_after, "color": "#7c3aed", "bg": "#f5f3ff"},
            {"label": "最终入模", "count": final_count, "color": "#16a34a", "bg": "#f0fdf4"},
        ]
        
        for i, step in enumerate(funnel_steps):
            if i > 0:
                html_parts.append('<span style="color: #9ca3af; font-size: 18px;">›</span>')
            
            pct = f"{step['count'] / original_count * 100:.0f}%" if original_count > 0 and step['count'] > 0 else "-"
            html_parts.append(f'''
            <div style="display: flex; flex-direction: column; align-items: center; padding: 10px 14px; 
                        border-radius: 8px; border: 1px solid #e5e7eb; min-width: 90px;
                        background: {step["bg"]};">
                <span style="font-size: 10px; color: #6b7280; margin-bottom: 3px;">{step["label"]}</span>
                <span style="font-size: 28px; font-weight: bold; color: {step["color"]};">{step["count"] or "-"}</span>
                <span style="font-size: 10px; color: #9ca3af;">{pct}</span>
            </div>
            ''')
        
        html_parts.append('</div>')
    
    # ========== 5.2 变量IV排行（带状态和淘汰信息） ==========
    # 2026-02-09: 移除冗余的IV值排序图，下方表格已包含完整信息且与前端Tab一致
    if iv_table is not None and len(iv_table) > 0:
        html_parts.append('<h4 class="subsection-title">变量IV排行</h4>')
        
        # 构建淘汰信息映射
        elimination_map: dict[str, dict[str, str]] = {}
        
        # 从var_filter获取数据质量筛选淘汰的特征
        removed_by_missing = var_filter_result.get('removed_by_missing', [])
        for item in removed_by_missing:
            if isinstance(item, dict) and item.get('feature'):
                elimination_map[item['feature']] = {
                    'stage': '数据质量(var_filter)',
                    'reason': item.get('reason', f"缺失率{(item.get('missing_rate', 0) * 100):.0f}%")
                }
        removed_by_identical = var_filter_result.get('removed_by_identical', [])
        for item in removed_by_identical:
            if isinstance(item, dict) and item.get('feature'):
                elimination_map[item['feature']] = {
                    'stage': '数据质量(var_filter)',
                    'reason': item.get('reason', f"同值率{(item.get('identical_rate', 0) * 100):.0f}%")
                }
        
        # 从WOE阶段获取分箱失败的特征
        woe_filtered = woe_binning_preview.get('woe_filtered', {})
        woe_filtered_features = woe_filtered.get('features', [])
        for feat in woe_filtered_features:
            if feat not in elimination_map:
                elimination_map[feat] = {
                    'stage': 'WOE分箱',
                    'reason': woe_filtered.get('reason', '常量/分箱失败')
                }
        
        # 从feature_selection阶段获取（IV/相关性/VIF）
        all_features_detail = feature_selection_preview.get('all_features_detail', [])
        for item in all_features_detail:
            if isinstance(item, dict) and item.get('feature') and item.get('remove_reason'):
                feat = item['feature']
                reason = item['remove_reason']
                stage = '特征筛选(IV)' if 'IV' in reason else '特征筛选(相关性)' if '相关性' in reason else '特征筛选(VIF)' if 'VIF' in reason else '特征筛选'
                elimination_map[feat] = {'stage': stage, 'reason': reason}
                elimination_map[feat + '_woe'] = {'stage': stage, 'reason': reason}
        
        # 从model_training阶段获取逐步回归移除的特征
        stepwise_result_data = model_training_preview.get('stepwise_result', {})
        stepwise_steps = stepwise_result_data.get('steps', [])
        for s in stepwise_steps:
            if s.get('action') == 'remove' and s.get('feature'):
                feat = s['feature']
                base_name = feat.replace('_woe', '')
                reason = f"P值={s.get('pvalue', 0):.4f}"
                elimination_map[feat] = {'stage': '模型训练(逐步回归)', 'reason': reason}
                elimination_map[base_name] = {'stage': '模型训练(逐步回归)', 'reason': reason}
        
        # 从系数验证获取
        coef_validation = model_training_preview.get('coefficient_validation', {})
        for feat in coef_validation.get('invalid_direction', []):
            base_name = feat.replace('_woe', '')
            if base_name not in elimination_map and feat not in elimination_map:
                elimination_map[feat] = {'stage': '模型训练(系数验证)', 'reason': '系数方向异常'}
                elimination_map[base_name] = {'stage': '模型训练(系数验证)', 'reason': '系数方向异常'}
        
        # 入模特征集合
        model_features_set = set(f.replace('_woe', '') for f in (selected_features or []))
        
        # 生成带状态的表格
        html_parts.append('<table class="data-table" style="font-size: 12px;">')
        html_parts.append('''
            <thead>
                <tr>
                    <th>#</th>
                    <th>变量</th>
                    <th class="text-right">IV值</th>
                    <th>预测能力</th>
                    <th class="text-center">状态</th>
                    <th>淘汰阶段</th>
                    <th>淘汰原因</th>
                </tr>
            </thead>
            <tbody>
        ''')
        
        # 按IV值降序排列
        iv_df = iv_table.copy()
        if 'iv' in iv_df.columns:
            iv_df = iv_df.sort_values('iv', ascending=False).reset_index(drop=True)
        
        for row_num, (idx, row) in enumerate(iv_df.iterrows(), start=1):
            var_name = row.get('variable', row.get('feature', str(idx)))
            iv_val = row.get('iv', 0)
            
            # 预测能力判断
            if iv_val >= 0.3:
                power = '强'
                power_color = '#16a34a'
            elif iv_val >= 0.1:
                power = '中等'
                power_color = '#f59e0b'
            elif iv_val >= 0.02:
                power = '弱'
                power_color = '#ef4444'
            else:
                power = '无'
                power_color = '#6b7280'
            
            # 状态判断
            base_name = var_name.replace('_woe', '')
            is_model_var = base_name in model_features_set
            elim_info = elimination_map.get(base_name) or elimination_map.get(var_name)
            
            if is_model_var:
                status_html = '<span style="background:#dcfce7;color:#16a34a;padding:2px 6px;border-radius:4px;font-size:11px;">入模</span>'
                elim_stage = '-'
                elim_reason = '-'
            elif elim_info:
                status_html = '<span style="background:#fef2f2;color:#dc2626;padding:2px 6px;border-radius:4px;font-size:11px;">淘汰</span>'
                elim_stage = elim_info.get('stage', '-')
                elim_reason = elim_info.get('reason', '-')
            else:
                status_html = '<span style="background:#f3f4f6;color:#6b7280;padding:2px 6px;border-radius:4px;font-size:11px;">未入模</span>'
                elim_stage = '-'
                elim_reason = '-'
            
            html_parts.append(f'''
                <tr>
                    <td>{row_num}</td>
                    <td>{base_name}</td>
                    <td class="text-right">{iv_val:.4f}</td>
                    <td style="color:{power_color};">{power}</td>
                    <td class="text-center">{status_html}</td>
                    <td style="font-size:11px;color:#6b7280;">{elim_stage}</td>
                    <td style="font-size:11px;color:#6b7280;">{elim_reason}</td>
                </tr>
            ''')
        
        html_parts.append('</tbody></table>')
    
    # 2026-02-09: 移除冗余的入模特征列表，漏斗已显示入模数，表格已标记入模状态
    
    # 逐步回归详情
    if selection_detail:
        stepwise_result = selection_detail.get('stepwise_result', {})
        if stepwise_result:
            steps = stepwise_result.get('steps', [])
            final_pvalues = stepwise_result.get('final_pvalues', {})
            direction = stepwise_result.get('direction', 'both')
            significance_level = stepwise_result.get('significance_level', 0.05)
            
            if steps:
                html_parts.append(f'<h4 class="subsection-title">逐步回归 ({direction}方向，显著性水平: {significance_level})</h4>')
                html_parts.append('<table class="data-table">')
                html_parts.append('''
                    <thead>
                        <tr>
                            <th>步骤</th>
                            <th>操作</th>
                            <th>变量</th>
                            <th class="text-right">P值</th>
                        </tr>
                    </thead>
                    <tbody>
                ''')
                for step in steps:
                    iteration = step.get('iteration', '')
                    action = step.get('action', '')
                    action_text = '添加' if action == 'add' else '移除'
                    action_class = 'add-action' if action == 'add' else 'remove-action'
                    feature = step.get('feature', '').replace('_woe', '')
                    pvalue = step.get('pvalue', 0)
                    html_parts.append(f'''
                    <tr>
                        <td>{iteration}</td>
                        <td><span class="{action_class}">{action_text}</span></td>
                        <td>{feature}</td>
                        <td class="text-right">{pvalue:.6f}</td>
                    </tr>
                    ''')
                html_parts.append('</tbody></table>')
            
            # P值显著性检验
            if final_pvalues:
                html_parts.append('<h4 class="subsection-title">显著性检验 (P值)</h4>')
                html_parts.append('<p style="color:#666;font-size:0.9em;">***: p&lt;0.01, **: p&lt;0.05, *: p&lt;0.1</p>')
                html_parts.append('<table class="data-table">')
                html_parts.append('''
                    <thead>
                        <tr>
                            <th>变量</th>
                            <th class="text-right">P值</th>
                            <th class="text-center">显著性</th>
                        </tr>
                    </thead>
                    <tbody>
                ''')
                for var_name, pvalue in sorted(final_pvalues.items(), key=lambda x: x[1]):
                    var_display = var_name.replace('_woe', '')
                    if pvalue < 0.01:
                        sig_text = '***'
                        sig_class = 'sig-high'
                    elif pvalue < 0.05:
                        sig_text = '**'
                        sig_class = 'sig-medium'
                    elif pvalue < 0.1:
                        sig_text = '*'
                        sig_class = 'sig-low'
                    else:
                        sig_text = '不显著'
                        sig_class = 'sig-none'
                    html_parts.append(f'''
                    <tr>
                        <td>{var_display}</td>
                        <td class="text-right">{pvalue:.6f}</td>
                        <td class="text-center"><span class="{sig_class}">{sig_text}</span></td>
                    </tr>
                    ''')
                html_parts.append('</tbody></table>')
        
        # 系数方向验证
        coef_validation = selection_detail.get('coefficient_validation', {})
        if coef_validation:
            valid_direction = coef_validation.get('valid_direction', [])
            invalid_direction = coef_validation.get('invalid_direction', [])
            warnings = coef_validation.get('warnings', [])
            
            html_parts.append('<h4 class="subsection-title">系数方向验证</h4>')
            html_parts.append('<div class="coef-validation">')
            
            # Valid
            html_parts.append('<div class="validation-section">')
            html_parts.append(f'<div class="validation-title valid-title">方向正确 ({len(valid_direction)})</div>')
            html_parts.append('<div class="feature-tags">')
            if valid_direction:
                for f in valid_direction:
                    html_parts.append(f'<span class="feature-tag valid">{f.replace("_woe", "")}</span>')
            else:
                html_parts.append('<span style="color:#95a5a6;font-style:italic;">无</span>')
            html_parts.append('</div></div>')
            
            # Invalid
            html_parts.append('<div class="validation-section">')
            html_parts.append(f'<div class="validation-title invalid-title">方向异常 ({len(invalid_direction)})</div>')
            html_parts.append('<div class="feature-tags">')
            if invalid_direction:
                for f in invalid_direction:
                    html_parts.append(f'<span class="feature-tag invalid">{f.replace("_woe", "")}</span>')
            else:
                html_parts.append('<span style="color:#95a5a6;font-style:italic;">无</span>')
            html_parts.append('</div></div>')
            
            html_parts.append('</div>')
            
            if warnings:
                html_parts.append('<div class="warning-box">')
                html_parts.append('<br>'.join([f'⚠️ {w}' for w in warnings]))
                html_parts.append('</div>')
    
    html_parts.append('</div>')
    
    # ==========================================================================
    # 六、模型系数（对应 Tab: statistics）
    # 2026-02-09 重构：与前端Tab完全对齐，包含完整的统计检验信息
    # ==========================================================================
    if coefficients is not None and len(coefficients) > 0:
        html_parts.append('<div class="section">')
        html_parts.append('<h2 class="section-title">📊 六、模型系数</h2>')
        
        # 获取模型统计信息
        model_statistics = results.get('model_statistics', {})
        model_training_preview = stages.get('model_training', {}).get('output_preview', {})
        
        # 获取截距项（优先从model_training_preview获取）
        intercept = model_training_preview.get('intercept') or results.get('intercept') or model_statistics.get('intercept')
        
        # 2026-02-09: 优先使用 model_statistics['summary'] 作为系数统计数据源
        # 它包含完整的统计信息：feature, coef, std_err, z, p_value, ci_lower, ci_upper, significance
        stats_summary = model_statistics.get('summary', []) if model_statistics else []
        
        # 如果 model_statistics['summary'] 可用，使用它；否则回退到其他数据源
        if stats_summary and isinstance(stats_summary, list) and len(stats_summary) > 0:
            coef_list = stats_summary
        else:
            # 回退方案：尝试使用 model_training_preview 的数据
            preview_coefficients = model_training_preview.get('coefficients', [])
            if preview_coefficients and isinstance(preview_coefficients, list):
                coef_list = preview_coefficients
            else:
                # 最后回退：使用 results['coefficients']
                coef_list = coefficients.to_dict('records') if hasattr(coefficients, 'to_dict') else []
        
        # 入模变量数：不含const
        n_features = sum(1 for item in coef_list 
                        if item.get('feature', item.get('variable', '')) != 'const')
        
        # 显著变量数：p<0.05，不含截距项
        significant_count = 0
        for item in coef_list:
            feature = item.get('feature', item.get('variable', ''))
            p_val = item.get('p_value', item.get('pvalue'))
            if feature != 'const' and p_val is not None and isinstance(p_val, (int, float)) and p_val < 0.05:
                significant_count += 1
        
        # 获取系数方向验证数据
        # 优先从 model_training_preview 获取，回退到 selection_detail
        coef_validation = model_training_preview.get('coefficient_validation', {})
        if not coef_validation:
            # 回退：从 selection_detail 获取
            coef_validation = selection_detail.get('coefficient_validation', {}) if selection_detail else {}
        valid_direction = coef_validation.get('valid_direction', [])
        invalid_direction = coef_validation.get('invalid_direction', [])
        valid_count = len(valid_direction)
        invalid_count = len(invalid_direction)
        
        # 2026-02-11: 指标卡优化 - 与前端Tab对齐：似然比检验、显著变量、系数方向验证、截距项
        html_parts.append('''
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 20px;">
        ''')
        
        # 1. 似然比检验 (LR Test) - 模型整体显著性
        lr_pvalue = model_statistics.get('lr_pvalue') if model_statistics else None
        if lr_pvalue is not None and isinstance(lr_pvalue, (int, float)):
            lr_significant = lr_pvalue < 0.05
            lr_bg_color = '#f0fdf4' if lr_significant else '#fef3c7'
            lr_border_color = '#86efac' if lr_significant else '#fcd34d'
            lr_text_color = '#16a34a' if lr_significant else '#d97706'
            lr_p_str = '<0.001' if lr_pvalue < 0.001 else f"{lr_pvalue:.4f}"
            lr_status = '✓ 显著' if lr_significant else '不显著'
        else:
            lr_bg_color = '#f9fafb'
            lr_border_color = '#e5e7eb'
            lr_text_color = '#6b7280'
            lr_p_str = '-'
            lr_status = ''
        
        html_parts.append(f'''
            <div style="background: {lr_bg_color}; padding: 16px; border-radius: 8px; border: 1px solid {lr_border_color};">
                <div style="font-size: 12px; color: {lr_text_color}; margin-bottom: 4px;">📊 似然比检验</div>
                <div style="font-size: 24px; font-weight: bold; color: {lr_text_color};">{lr_p_str}</div>
                <div style="font-size: 11px; color: {lr_text_color};">{lr_status}</div>
            </div>
        ''')
        
        # 2. 显著变量
        html_parts.append(f'''
            <div style="background: #f9fafb; padding: 16px; border-radius: 8px; border: 1px solid #e5e7eb;">
                <div style="font-size: 12px; color: #6b7280; margin-bottom: 4px;">◎ 显著变量 (p&lt;0.05)</div>
                <div style="font-size: 24px; font-weight: bold; color: #16a34a;">{significant_count}<span style="font-size: 14px; color: #6b7280;">/{n_features}个</span></div>
            </div>
        ''')
        
        # 3. 系数方向验证（根据状态显示不同样式）
        if invalid_count == 0:
            # 全部正确 - 绿色成功状态
            html_parts.append(f'''
            <div style="background: #f0fdf4; padding: 16px; border-radius: 8px; border: 1px solid #86efac;">
                <div style="font-size: 12px; color: #16a34a; margin-bottom: 4px;">✅ 系数方向</div>
                <div style="font-size: 24px; font-weight: bold; color: #16a34a;">{valid_count}/{valid_count}</div>
                <div style="font-size: 11px; color: #16a34a;">全部正确</div>
            </div>
        ''')
        else:
            # 有异常 - 黄色警告状态
            html_parts.append(f'''
            <div style="background: #fef3c7; padding: 16px; border-radius: 8px; border: 1px solid #fcd34d;">
                <div style="font-size: 12px; color: #d97706; margin-bottom: 4px;">⚠️ 系数方向</div>
                <div style="font-size: 24px;">
                    <span style="font-weight: bold; color: #16a34a;">{valid_count}</span>
                    <span style="color: #6b7280;">/</span>
                    <span style="font-weight: bold; color: #dc2626;">{invalid_count}</span>
                </div>
                <div style="font-size: 11px; color: #d97706;">{invalid_count}个方向异常</div>
            </div>
        ''')
        
        # 4. 截距项
        intercept_str = f"{intercept:.4f}" if isinstance(intercept, (int, float)) else '-'
        html_parts.append(f'''
            <div style="background: #f9fafb; padding: 16px; border-radius: 8px; border: 1px solid #e5e7eb;">
                <div style="font-size: 12px; color: #6b7280; margin-bottom: 4px;">📄 截距项</div>
                <div style="font-size: 24px; font-weight: bold; color: #f97316;">{intercept_str}</div>
            </div>
        ''')
        
        html_parts.append('</div>')
        
        # 模型拟合指标（可折叠，默认展开）
        if model_statistics:
            pseudo_r2 = model_statistics.get('pseudo_r2')
            log_likelihood = model_statistics.get('log_likelihood')
            aic = model_statistics.get('aic')
            bic = model_statistics.get('bic')
            
            if any([pseudo_r2, log_likelihood, aic, bic]):
                html_parts.append('<h4 class="subsection-title">模型拟合指标</h4>')
                html_parts.append('<div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px;">')
                
                if pseudo_r2 is not None:
                    html_parts.append(f'''
                        <div style="background: #f0fdf4; padding: 12px; border-radius: 6px; text-align: center;">
                            <div style="font-size: 11px; color: #6b7280;">Pseudo R²</div>
                            <div style="font-size: 16px; font-weight: bold; color: #16a34a;">{pseudo_r2:.4f}</div>
                        </div>
                    ''')
                if log_likelihood is not None:
                    html_parts.append(f'''
                        <div style="background: #eff6ff; padding: 12px; border-radius: 6px; text-align: center;">
                            <div style="font-size: 11px; color: #6b7280;">Log-Likelihood</div>
                            <div style="font-size: 16px; font-weight: bold; color: #2563eb;">{log_likelihood:.4f}</div>
                        </div>
                    ''')
                if aic is not None:
                    html_parts.append(f'''
                        <div style="background: #fef3c7; padding: 12px; border-radius: 6px; text-align: center;">
                            <div style="font-size: 11px; color: #6b7280;">AIC</div>
                            <div style="font-size: 16px; font-weight: bold; color: #d97706;">{aic:.4f}</div>
                        </div>
                    ''')
                if bic is not None:
                    html_parts.append(f'''
                        <div style="background: #fce7f3; padding: 12px; border-radius: 6px; text-align: center;">
                            <div style="font-size: 11px; color: #6b7280;">BIC</div>
                            <div style="font-size: 16px; font-weight: bold; color: #db2777;">{bic:.4f}</div>
                        </div>
                    ''')
                
                html_parts.append('</div>')
        
        # 系数统计表（完整版，与前端对齐）
        html_parts.append('<h4 class="subsection-title">系数统计</h4>')
        html_parts.append('<table class="data-table" style="font-size: 12px;">')
        html_parts.append('''
            <thead>
                <tr>
                    <th>变量</th>
                    <th class="text-right">系数</th>
                    <th class="text-right">标准误</th>
                    <th class="text-right">z值</th>
                    <th class="text-right">P值</th>
                    <th class="text-right">95% CI</th>
                    <th class="text-center">显著性</th>
                </tr>
            </thead>
            <tbody>
        ''')
        
        for item in coef_list:
            feature = item.get('feature', item.get('variable', '-'))
            
            # 排除 const 行（与前端Tab一致，截距项单独显示在指标卡中）
            if feature == 'const':
                continue
            
            coef = item.get('coef', item.get('coefficient', 0))
            std_err = item.get('std_err', item.get('std_error'))
            z_val = item.get('z', item.get('z_value'))
            p_val = item.get('p_value', item.get('pvalue'))
            ci_lower = item.get('ci_lower', item.get('conf_int_lower'))
            ci_upper = item.get('ci_upper', item.get('conf_int_upper'))
            
            # 格式化变量名（移除_woe后缀）
            var_display = feature.replace('_woe', '')
            
            # 格式化数值
            coef_str = f"{coef:.4f}" if isinstance(coef, (int, float)) else 'N/A'
            std_str = f"{std_err:.4f}" if isinstance(std_err, (int, float)) else 'N/A'
            z_str = f"{z_val:.2f}" if isinstance(z_val, (int, float)) else 'N/A'
            
            # P值特殊处理
            if isinstance(p_val, (int, float)):
                if p_val < 0.001:
                    p_str = '<0.001'
                    p_color = '#16a34a'  # green
                elif p_val < 0.01:
                    p_str = f"{p_val:.4f}"
                    p_color = '#22c55e'  # light green
                elif p_val < 0.05:
                    p_str = f"{p_val:.4f}"
                    p_color = '#eab308'  # yellow
                else:
                    p_str = f"{p_val:.4f}"
                    p_color = '#6b7280'  # gray
            else:
                p_str = 'N/A'
                p_color = '#6b7280'
            
            # 95% CI
            if isinstance(ci_lower, (int, float)) and isinstance(ci_upper, (int, float)):
                ci_str = f"[{ci_lower:.3f}, {ci_upper:.3f}]"
            else:
                ci_str = '[N/A, N/A]'
            
            # 显著性标记
            if isinstance(p_val, (int, float)):
                if p_val < 0.001:
                    sig = '***'
                    sig_color = '#16a34a'
                elif p_val < 0.01:
                    sig = '**'
                    sig_color = '#22c55e'
                elif p_val < 0.05:
                    sig = '*'
                    sig_color = '#eab308'
                elif p_val < 0.1:
                    sig = '.'
                    sig_color = '#f97316'
                else:
                    sig = ''
                    sig_color = '#6b7280'
            else:
                sig = ''
                sig_color = '#6b7280'
            
            html_parts.append(f'''
                <tr>
                    <td style="font-weight: 500;">{var_display}</td>
                    <td class="text-right" style="font-family: monospace;">{coef_str}</td>
                    <td class="text-right" style="font-family: monospace; color: #6b7280;">{std_str}</td>
                    <td class="text-right" style="font-family: monospace;">{z_str}</td>
                    <td class="text-right" style="font-family: monospace; color: {p_color}; font-weight: bold;">{p_str}</td>
                    <td class="text-right" style="font-family: monospace; font-size: 11px; color: #6b7280;">{ci_str}</td>
                    <td class="text-center" style="font-weight: bold; color: {sig_color};">{sig}</td>
                </tr>
            ''')
        
        html_parts.append('</tbody></table>')
        
        # 显著性图例
        html_parts.append('''
            <p style="margin-top: 12px; font-size: 11px; color: #6b7280;">
                显著性标记: <span style="color: #16a34a; font-weight: bold;">***</span> p&lt;0.001, 
                <span style="color: #22c55e; font-weight: bold;">**</span> p&lt;0.01, 
                <span style="color: #eab308; font-weight: bold;">*</span> p&lt;0.05, 
                <span style="color: #f97316; font-weight: bold;">.</span> p&lt;0.1
            </p>
        ''')
        
        html_parts.append('</div>')
    
    # 2026-02-09: 移除footer
    html_parts.append('''
</div>
</body>
</html>
    ''')
    
    return '\n'.join(html_parts)


# =============================================================================
# Backward Compatibility Aliases
# =============================================================================

# These functions are re-exported for backward compatibility
# They wrap the internal functions with the original signatures

def generate_rule_mining_report_html(
    results: Dict[str, Any],
    title: str = '规则挖掘报告',
    include_charts: bool = True,
    ai_analysis: Optional[str] = None
) -> str:
    """
    Generate complete HTML report for rule mining results.
    
    This is a convenience wrapper that maintains backward compatibility.
    """
    return _generate_rule_mining_html_report(
        results=results,
        title=title,
        ai_analysis=ai_analysis,
        include_charts=include_charts
    )


def generate_scorecard_report_html(
    metrics: Dict[str, float],
    iv_table: pd.DataFrame,
    scorecard: pd.DataFrame,
    coefficients: pd.DataFrame,
    y_true: Optional[np.ndarray] = None,
    y_score: Optional[np.ndarray] = None,
    scores_good: Optional[np.ndarray] = None,
    scores_bad: Optional[np.ndarray] = None,
    chart_data: Optional[Dict[str, Any]] = None,
    multi_dataset_metrics: Optional[Dict[str, Dict[str, Any]]] = None,
    multi_dataset_chart_data: Optional[Dict[str, Dict[str, Any]]] = None,
    selected_features: Optional[List[str]] = None,
    overfit_warning: Optional[str] = None,
    selection_detail: Optional[Dict[str, Any]] = None,
    outlier_info: Optional[Dict[str, Dict[str, Any]]] = None,
    title: str = '评分卡开发报告'
) -> str:
    """
    Generate comprehensive HTML report for scorecard development.
    
    This is a convenience wrapper that maintains backward compatibility
    with the original function signature from scorecard_viz.py.
    """
    results = {
        'metrics': metrics,
        'iv_table': iv_table,
        'scorecard': scorecard,
        'coefficients': coefficients,
        'chart_data': chart_data,
        'multi_dataset_metrics': multi_dataset_metrics,
        'multi_dataset_chart_data': multi_dataset_chart_data,
        'selected_features': selected_features,
        'overfit_warning': overfit_warning,
        'selection_detail': selection_detail,
        'outlier_info': outlier_info,
    }
    return _generate_scorecard_html_report(
        results=results,
        title=title,
        ai_analysis=None,
        include_charts=True
    )


# =============================================================================
# Export
# =============================================================================

__all__ = [
    'generate_html_report',
    'generate_rule_mining_report_html',
    'generate_scorecard_report_html',
    'HAS_PLOTLY',
]
