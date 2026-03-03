"""
Scorecard Visualization Module

Provides visualization functions for scorecard development results:
- ROC curve
- KS curve
- Score distribution
- WOE binning chart
- HTML report generation
"""
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false
# pyright: reportMissingTypeStubs=false
# pyright: reportUnusedCallResult=false
# pyright: reportAny=false
# pyright: reportUnnecessaryComparison=false
# pyright: reportExplicitAny=false
from __future__ import annotations

import warnings
from typing import Any

import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')

# Try to import visualization libraries
_matplotlib_available = False
_plotly_available = False

try:
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm
    _matplotlib_available = True
except ImportError:
    plt = None  # type: ignore[assignment]
    fm = None  # type: ignore[assignment]

try:
    import plotly.graph_objects as go  # type: ignore[import-not-found,import-untyped]
    _plotly_available = True
except ImportError:
    go = None  # type: ignore[assignment]

# 导出HAS_PLOTLY供word_report.py使用（与rule_mining_viz.py保持一致）
HAS_PLOTLY = _plotly_available


def _setup_chinese_font() -> None:
    """Setup Chinese font for matplotlib."""
    if not _matplotlib_available or plt is None or fm is None:
        return
    
    chinese_fonts = [
        'SimHei', 'Microsoft YaHei', 'STHeiti', 'WenQuanYi Micro Hei',
        'Noto Sans CJK SC', 'Source Han Sans SC', 'PingFang SC'
    ]
    
    for font in chinese_fonts:
        try:
            fm.findfont(font)
            plt.rcParams['font.sans-serif'] = [font] + list(plt.rcParams['font.sans-serif'])
            plt.rcParams['axes.unicode_minus'] = False
            return
        except Exception:
            continue


def plot_roc_curve(
    y_true: np.ndarray,
    y_score: np.ndarray,
    output_format: str = 'plotly',
    title: str = 'ROC曲线',
    figsize: tuple[int, int] = (8, 6),
    return_html: bool = False
) -> object:
    """
    Plot ROC (Receiver Operating Characteristic) curve.
    
    Args:
        y_true: True binary labels (0/1)
        y_score: Predicted probabilities or scores
        output_format: 'plotly' or 'matplotlib'
        title: Chart title
        figsize: Figure size for matplotlib
        return_html: If True, return HTML string (plotly only)
        
    Returns:
        Plotly figure, matplotlib figure, or HTML string
    """
    from sklearn.metrics import roc_curve, auc
    
    fpr, tpr, _ = roc_curve(y_true, y_score)
    roc_auc = float(auc(fpr, tpr))
    
    if output_format == 'plotly' and _plotly_available and go is not None:
        fig = go.Figure()
        
        # ROC curve
        fig.add_trace(go.Scatter(
            x=fpr, y=tpr,
            mode='lines',
            name=f'ROC曲线 (AUC = {roc_auc:.4f})',
            line=dict(color='#2E86AB', width=2),
            fill='tozeroy',
            fillcolor='rgba(46, 134, 171, 0.2)'
        ))
        
        # Diagonal line
        fig.add_trace(go.Scatter(
            x=[0, 1], y=[0, 1],
            mode='lines',
            name='随机分类器',
            line=dict(color='gray', width=1, dash='dash')
        ))
        
        fig.update_layout(
            title=dict(text=title, x=0.5),
            xaxis_title='假阳性率 (FPR)',
            yaxis_title='真阳性率 (TPR)',
            showlegend=True,
            legend=dict(x=0.6, y=0.1),
            template='plotly_white',
            width=600,
            height=500
        )
        
        if return_html:
            return fig.to_html(include_plotlyjs='cdn', full_html=False)
        return fig
    
    elif _matplotlib_available and plt is not None:
        _setup_chinese_font()
        fig, ax = plt.subplots(figsize=figsize)
        
        ax.plot(fpr, tpr, color='#2E86AB', lw=2, label=f'ROC曲线 (AUC = {roc_auc:.4f})')
        ax.fill_between(fpr, tpr, alpha=0.2, color='#2E86AB')
        ax.plot([0, 1], [0, 1], color='gray', lw=1, linestyle='--', label='随机分类器')
        
        ax.set_xlim(0.0, 1.0)
        ax.set_ylim(0.0, 1.05)
        ax.set_xlabel('假阳性率 (FPR)')
        ax.set_ylabel('真阳性率 (TPR)')
        ax.set_title(title)
        ax.legend(loc='lower right')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        return fig
    
    else:
        raise ImportError("Neither plotly nor matplotlib is available")


def plot_ks_curve(
    y_true: np.ndarray,
    y_score: np.ndarray,
    output_format: str = 'plotly',
    title: str = 'KS曲线',
    figsize: tuple[int, int] = (8, 6),
    return_html: bool = False
) -> object:
    """
    Plot KS (Kolmogorov-Smirnov) curve.
    
    Args:
        y_true: True binary labels (0/1)
        y_score: Predicted probabilities or scores
        output_format: 'plotly' or 'matplotlib'
        title: Chart title
        figsize: Figure size for matplotlib
        return_html: If True, return HTML string (plotly only)
        
    Returns:
        Plotly figure, matplotlib figure, or HTML string
    """
    # Sort by score
    sorted_indices = np.argsort(y_score)
    y_true_sorted = np.array(y_true)[sorted_indices]
    
    sample_count = len(y_true_sorted)
    n_pos = int(np.sum(y_true_sorted == 1))
    n_neg = int(np.sum(y_true_sorted == 0))
    
    # Calculate cumulative distributions
    cum_pos = np.cumsum(y_true_sorted == 1) / n_pos
    cum_neg = np.cumsum(y_true_sorted == 0) / n_neg
    
    # Calculate KS
    ks_values = np.abs(cum_pos - cum_neg)
    ks_max_val = float(np.max(ks_values))
    ks_max_idx = int(np.argmax(ks_values))
    
    # X-axis: population percentage
    x_axis = np.arange(1, sample_count + 1) / sample_count * 100
    
    if output_format == 'plotly' and _plotly_available and go is not None:
        fig = go.Figure()
        
        # Bad cumulative curve
        fig.add_trace(go.Scatter(
            x=x_axis, y=cum_pos * 100,
            mode='lines',
            name='坏样本累计分布',
            line=dict(color='#E74C3C', width=2)
        ))
        
        # Good cumulative curve
        fig.add_trace(go.Scatter(
            x=x_axis, y=cum_neg * 100,
            mode='lines',
            name='好样本累计分布',
            line=dict(color='#27AE60', width=2)
        ))
        
        # KS line
        fig.add_trace(go.Scatter(
            x=x_axis, y=ks_values * 100,
            mode='lines',
            name='KS曲线',
            line=dict(color='#3498DB', width=2, dash='dot')
        ))
        
        # KS max point
        ks_max_x = float(x_axis[ks_max_idx])
        ks_max_y = float(ks_values[ks_max_idx]) * 100
        fig.add_trace(go.Scatter(
            x=[ks_max_x],
            y=[ks_max_y],
            mode='markers+text',
            name=f'KS最大值 = {ks_max_val:.4f}',
            marker=dict(size=12, color='#9B59B6', symbol='star'),
            text=[f'KS = {ks_max_val:.4f}'],
            textposition='top center'
        ))
        
        # Vertical line at KS max
        fig.add_vline(
            x=ks_max_x,
            line_dash='dash',
            line_color='gray',
            annotation_text=f'最大KS位置: {ks_max_x:.1f}%'
        )
        
        fig.update_layout(
            title=dict(text=f'{title} (KS = {ks_max_val:.4f})', x=0.5),
            xaxis_title='样本累计百分比 (%)',
            yaxis_title='累计百分比 (%)',
            showlegend=True,
            legend=dict(x=0.7, y=0.3),
            template='plotly_white',
            width=700,
            height=500
        )
        
        if return_html:
            return fig.to_html(include_plotlyjs='cdn', full_html=False)
        return fig
    
    elif _matplotlib_available and plt is not None:
        _setup_chinese_font()
        fig, ax = plt.subplots(figsize=figsize)
        
        ax.plot(x_axis, cum_pos * 100, color='#E74C3C', lw=2, label='坏样本累计分布')
        ax.plot(x_axis, cum_neg * 100, color='#27AE60', lw=2, label='好样本累计分布')
        ax.plot(x_axis, ks_values * 100, color='#3498DB', lw=2, linestyle=':', label='KS曲线')
        
        ks_max_x = float(x_axis[ks_max_idx])
        ks_max_y = float(ks_values[ks_max_idx]) * 100
        ax.scatter([ks_max_x], [ks_max_y], 
                   s=100, c='#9B59B6', marker='*', zorder=5, label=f'KS最大值 = {ks_max_val:.4f}')
        ax.axvline(x=ks_max_x, color='gray', linestyle='--', alpha=0.5)
        
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 105)
        ax.set_xlabel('样本累计百分比 (%)')
        ax.set_ylabel('累计百分比 (%)')
        ax.set_title(f'{title} (KS = {ks_max_val:.4f})')
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        return fig
    
    else:
        raise ImportError("Neither plotly nor matplotlib is available")


def plot_score_distribution(
    scores_good: np.ndarray,
    scores_bad: np.ndarray,
    output_format: str = 'plotly',
    title: str = '评分分布图',
    bins: int = 30,
    figsize: tuple[int, int] = (10, 6),
    return_html: bool = False
) -> object:
    """
    Plot score distribution for good and bad samples.
    
    Args:
        scores_good: Scores for good samples (label=0)
        scores_bad: Scores for bad samples (label=1)
        output_format: 'plotly' or 'matplotlib'
        title: Chart title
        bins: Number of histogram bins
        figsize: Figure size for matplotlib
        return_html: If True, return HTML string (plotly only)
        
    Returns:
        Plotly figure, matplotlib figure, or HTML string
    """
    good_mean = float(np.mean(scores_good))
    bad_mean = float(np.mean(scores_bad))
    
    if output_format == 'plotly' and _plotly_available and go is not None:
        fig = go.Figure()
        
        # Good samples histogram
        fig.add_trace(go.Histogram(
            x=scores_good,
            name='好样本 (label=0)',
            opacity=0.7,
            marker_color='#27AE60',
            nbinsx=bins
        ))
        
        # Bad samples histogram
        fig.add_trace(go.Histogram(
            x=scores_bad,
            name='坏样本 (label=1)',
            opacity=0.7,
            marker_color='#E74C3C',
            nbinsx=bins
        ))
        
        fig.update_layout(
            title=dict(text=title, x=0.5),
            xaxis_title='评分',
            yaxis_title='样本数量',
            barmode='overlay',
            showlegend=True,
            legend=dict(x=0.8, y=0.95),
            template='plotly_white',
            width=800,
            height=500
        )
        
        # Add statistics annotation
        fig.add_annotation(
            x=0.02, y=0.98,
            xref='paper', yref='paper',
            text=f'好样本均值: {good_mean:.1f}<br>坏样本均值: {bad_mean:.1f}',
            showarrow=False,
            font=dict(size=11),
            align='left',
            bgcolor='rgba(255,255,255,0.8)',
            bordercolor='gray',
            borderwidth=1
        )
        
        if return_html:
            return fig.to_html(include_plotlyjs='cdn', full_html=False)
        return fig
    
    elif _matplotlib_available and plt is not None:
        _setup_chinese_font()
        fig, ax = plt.subplots(figsize=figsize)
        
        ax.hist(scores_good, bins=bins, alpha=0.7, color='#27AE60', label='好样本 (label=0)')
        ax.hist(scores_bad, bins=bins, alpha=0.7, color='#E74C3C', label='坏样本 (label=1)')
        
        ax.axvline(good_mean, color='#27AE60', linestyle='--', lw=2, label=f'好样本均值: {good_mean:.1f}')
        ax.axvline(bad_mean, color='#E74C3C', linestyle='--', lw=2, label=f'坏样本均值: {bad_mean:.1f}')
        
        ax.set_xlabel('评分')
        ax.set_ylabel('样本数量')
        ax.set_title(title)
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        return fig
    
    else:
        raise ImportError("Neither plotly nor matplotlib is available")


def plot_iv_chart(
    iv_table: pd.DataFrame,
    top_n: int = 20,
    output_format: str = 'plotly',
    title: str = 'IV值排序图',
    figsize: tuple[int, int] = (12, 6),
    return_html: bool = False
) -> object:
    """
    Plot IV values bar chart.
    
    Args:
        iv_table: DataFrame with 'variable' and 'iv' columns
        top_n: Number of top variables to show
        output_format: 'plotly' or 'matplotlib'
        title: Chart title
        figsize: Figure size for matplotlib
        return_html: If True, return HTML string (plotly only)
        
    Returns:
        Plotly figure, matplotlib figure, or HTML string
    """
    # Sort by IV descending
    iv_sorted = iv_table.sort_values('iv', ascending=False).head(top_n)
    
    # Extract IV values as list
    iv_values: list[float] = [float(v) for v in iv_sorted['iv']]
    var_names: list[str] = [str(v) for v in iv_sorted['variable']]
    
    # Define color based on IV thresholds
    def get_iv_color(iv_val: float) -> str:
        if iv_val >= 0.5:
            return '#E74C3C'  # Very strong - red
        elif iv_val >= 0.3:
            return '#E67E22'  # Strong - orange
        elif iv_val >= 0.1:
            return '#F1C40F'  # Medium - yellow
        elif iv_val >= 0.02:
            return '#27AE60'  # Weak - green
        else:
            return '#95A5A6'  # Very weak - gray
    
    colors = [get_iv_color(iv_val) for iv_val in iv_values]
    
    if output_format == 'plotly' and _plotly_available and go is not None:
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=var_names,
            y=iv_values,
            marker_color=colors,
            text=[f'{iv_val:.4f}' for iv_val in iv_values],
            textposition='outside'
        ))
        
        # Add threshold lines
        fig.add_hline(y=0.02, line_dash='dash', line_color='gray', 
                      annotation_text='弱预测力 (0.02)')
        fig.add_hline(y=0.1, line_dash='dash', line_color='#27AE60',
                      annotation_text='中等预测力 (0.1)')
        fig.add_hline(y=0.3, line_dash='dash', line_color='#E67E22',
                      annotation_text='强预测力 (0.3)')
        
        fig.update_layout(
            title=dict(text=f'{title} (Top {top_n})', x=0.5),
            xaxis_title='变量',
            yaxis_title='IV值',
            template='plotly_white',
            width=900,
            height=500,
            xaxis_tickangle=-45
        )
        
        if return_html:
            return fig.to_html(include_plotlyjs='cdn', full_html=False)
        return fig
    
    elif _matplotlib_available and plt is not None:
        _setup_chinese_font()
        fig, ax = plt.subplots(figsize=figsize)
        
        bars = ax.bar(var_names, iv_values, color=colors)
        
        # Add value labels
        for bar, iv_val in zip(bars, iv_values):
            bar_height = float(bar.get_height())
            bar_x = float(bar.get_x())
            bar_width = float(bar.get_width())
            ax.text(bar_x + bar_width / 2, bar_height + 0.01,
                    f'{iv_val:.4f}', ha='center', va='bottom', fontsize=8)
        
        # Add threshold lines
        ax.axhline(y=0.02, color='gray', linestyle='--', label='弱预测力 (0.02)')
        ax.axhline(y=0.1, color='#27AE60', linestyle='--', label='中等预测力 (0.1)')
        ax.axhline(y=0.3, color='#E67E22', linestyle='--', label='强预测力 (0.3)')
        
        ax.set_xlabel('变量')
        ax.set_ylabel('IV值')
        ax.set_title(f'{title} (Top {top_n})')
        ax.legend()
        plt.xticks(rotation=45, ha='right')
        ax.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        return fig
    
    else:
        raise ImportError("Neither plotly nor matplotlib is available")


def _generate_roc_chart_from_data(
    roc_data: dict[str, Any], 
    width: int = 600, 
    height: int = 500,
    return_html: bool = True
) -> Any:
    """Generate ROC chart from chart_data format.
    
    Args:
        roc_data: ROC curve data containing fpr, tpr, auc
        width: Chart width in pixels (default 600)
        height: Chart height in pixels (default 500)
        return_html: If True, return HTML string; if False, return Plotly Figure object
    
    Returns:
        HTML string or Plotly Figure object
    """
    if not _plotly_available or go is None:
        if return_html:
            return '<p class="error">Plotly不可用，无法生成ROC图表</p>'
        else:
            return None
    
    fpr = roc_data.get('fpr', [])
    tpr = roc_data.get('tpr', [])
    auc_value = roc_data.get('auc', 0)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=fpr, y=tpr,
        mode='lines',
        name=f'ROC曲线 (AUC = {auc_value:.4f})',
        line=dict(color='#2E86AB', width=2),
        fill='tozeroy',
        fillcolor='rgba(46, 134, 171, 0.2)'
    ))
    fig.add_trace(go.Scatter(
        x=[0, 1], y=[0, 1],
        mode='lines',
        name='随机分类器',
        line=dict(color='gray', width=1, dash='dash')
    ))
    fig.update_layout(
        title=dict(text='ROC曲线', x=0.5),
        xaxis_title='假阳性率 (FPR)',
        yaxis_title='真阳性率 (TPR)',
        showlegend=True,
        legend=dict(x=0.6, y=0.1),
        template='plotly_white',
        width=width,
        height=height,
        margin=dict(l=50, r=20, t=40, b=50)
    )
    
    if return_html:
        return str(fig.to_html(include_plotlyjs='cdn', full_html=False))
    else:
        return fig


def _generate_ks_chart_from_data(
    ks_data: dict[str, Any], 
    width: int = 700, 
    height: int = 500,
    return_html: bool = True
) -> Any:
    """Generate KS chart from chart_data format.
    
    Args:
        ks_data: KS curve data
        width: Chart width in pixels (default 700)
        height: Chart height in pixels (default 500)
        return_html: If True, return HTML string; if False, return Plotly Figure object
    
    Returns:
        HTML string or Plotly Figure object
    """
    if not _plotly_available or go is None:
        if return_html:
            return '<p class="error">Plotly不可用，无法生成KS图表</p>'
        else:
            return None
    
    population_pct = ks_data.get('population_pct', [])
    cum_bad = ks_data.get('cum_bad', [])
    cum_good = ks_data.get('cum_good', [])
    ks_curve = ks_data.get('ks_curve', [])
    ks_max = ks_data.get('ks_max', 0)
    ks_max_position = ks_data.get('ks_max_position', 0)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=population_pct, y=cum_bad,
        mode='lines',
        name='坏样本累计分布',
        line=dict(color='#E74C3C', width=2)
    ))
    fig.add_trace(go.Scatter(
        x=population_pct, y=cum_good,
        mode='lines',
        name='好样本累计分布',
        line=dict(color='#27AE60', width=2)
    ))
    fig.add_trace(go.Scatter(
        x=population_pct, y=ks_curve,
        mode='lines',
        name='KS曲线',
        line=dict(color='#3498DB', width=2, dash='dot')
    ))
    
    # KS max point
    ks_max_y = ks_max * 100
    fig.add_trace(go.Scatter(
        x=[ks_max_position],
        y=[ks_max_y],
        mode='markers+text',
        name=f'KS最大值 = {ks_max:.4f}',
        marker=dict(size=12, color='#9B59B6', symbol='star'),
        text=[f'KS = {ks_max:.4f}'],
        textposition='top center'
    ))
    fig.add_vline(
        x=ks_max_position,
        line_dash='dash',
        line_color='gray',
        annotation_text=f'最大KS位置: {ks_max_position:.1f}%'
    )
    fig.update_layout(
        title=dict(text=f'KS曲线 (KS = {ks_max:.4f})', x=0.5),
        xaxis_title='样本累计百分比 (%)',
        yaxis_title='累计百分比 (%)',
        showlegend=True,
        legend=dict(x=0.7, y=0.3),
        template='plotly_white',
        width=width,
        height=height,
        margin=dict(l=50, r=20, t=40, b=50)
    )
    
    if return_html:
        return str(fig.to_html(include_plotlyjs='cdn', full_html=False))
    else:
        return fig


def _generate_score_dist_chart_from_data(
    dist_data: dict[str, Any], 
    width: int = 900, 
    height: int = 500,
    dataset_label: str | None = None,
    return_html: bool = True
) -> Any:
    """Generate score distribution chart from chart_data format.
    
    Args:
        dist_data: Score distribution data
        width: Chart width in pixels (default 900)
        height: Chart height in pixels (default 500)
        dataset_label: Optional dataset label (e.g., '测试集', 'OOT验证集')
        return_html: If True, return HTML string; if False, return Plotly Figure object
    
    Returns:
        HTML string or Plotly Figure object
    """
    if not _plotly_available or go is None:
        if return_html:
            return '<p class="error">Plotly不可用，无法生成评分分布图表</p>'
        else:
            return None
    
    bins = dist_data.get('bins', [])
    summary = dist_data.get('summary', {})
    
    if not bins:
        if return_html:
            return '<p class="error">无评分分布数据</p>'
        else:
            return None
    
    bin_labels = [b.get('bin', '') for b in bins]
    bad_counts = [b.get('bad', 0) for b in bins]
    good_counts = [b.get('good', 0) for b in bins]
    bad_rates = [b.get('bad_rate', 0) for b in bins]
    
    fig = go.Figure()
    
    # Stacked bar chart
    fig.add_trace(go.Bar(
        x=bin_labels,
        y=good_counts,
        name='好样本',
        marker_color='#27AE60'
    ))
    fig.add_trace(go.Bar(
        x=bin_labels,
        y=bad_counts,
        name='坏样本',
        marker_color='#E74C3C'
    ))
    
    # Bad rate line on secondary y-axis
    fig.add_trace(go.Scatter(
        x=bin_labels,
        y=bad_rates,
        mode='lines+markers',
        name='坏账率 (%)',
        yaxis='y2',
        line=dict(color='#9B59B6', width=2),
        marker=dict(size=8)
    ))
    
    good_mean = summary.get('good_mean', 0)
    bad_mean = summary.get('bad_mean', 0)
    
    # 构建标题：包含数据集标签（如果有）
    title_text = f'{dataset_label} 评分分布图' if dataset_label else '评分分布图'
    
    fig.update_layout(
        title=dict(text=title_text, x=0.5),
        xaxis_title='评分区间',
        yaxis_title='样本数量',
        yaxis2=dict(
            title='坏账率 (%)',
            overlaying='y',
            side='right',
            showgrid=False
        ),
        barmode='stack',
        showlegend=True,
        legend=dict(x=0.8, y=0.95),
        template='plotly_white',
        width=width,
        height=height,
        xaxis_tickangle=-45,
        margin=dict(l=50, r=60, t=40, b=80)
    )
    
    # Add statistics annotation
    fig.add_annotation(
        x=0.02, y=0.98,
        xref='paper', yref='paper',
        text=f'好样本均分: {good_mean:.1f}<br>坏样本均分: {bad_mean:.1f}',
        showarrow=False,
        font=dict(size=11),
        align='left',
        bgcolor='rgba(255,255,255,0.8)',
        bordercolor='gray',
        borderwidth=1
    )
    
    if return_html:
        return str(fig.to_html(include_plotlyjs='cdn', full_html=False))
    else:
        return fig


def _generate_lift_chart_from_data(
    bins_data: list[dict[str, Any]], 
    width: int = 380, 
    height: int = 280,
    dataset_label: str | None = None,
    return_html: bool = True
) -> Any:
    """Generate Lift curve chart from score distribution bins.
    
    Args:
        bins_data: List of bin data containing lift values
        width: Chart width in pixels
        height: Chart height in pixels
        dataset_label: Optional dataset label (e.g., '测试集', 'OOT验证集')
        return_html: If True, return HTML string; if False, return Plotly Figure object
    
    Returns:
        HTML string or Plotly Figure object
    """
    if not _plotly_available or go is None:
        if return_html:
            return '<p class="error">Plotly不可用，无法生成Lift图表</p>'
        else:
            return None
    
    if not bins_data:
        if return_html:
            return '<p class="error">无Lift数据</p>'
        else:
            return None
    
    # 提取Lift值（假设数据按评分从低到高排序，即高风险到低风险）
    lifts = [b.get('lift', 0) for b in bins_data]
    bin_labels = [b.get('bin', f'分箱{i+1}') for i, b in enumerate(bins_data)]
    
    # 计算首组和末组Lift
    first_lift = lifts[0] if lifts else 0
    last_lift = lifts[-1] if lifts else 0
    
    fig = go.Figure()
    
    # Lift曲线 - 使用分数区间作为X轴（与评分分布图一致）
    fig.add_trace(go.Scatter(
        x=bin_labels,  # 使用分数区间标签，与评分分布图一致
        y=lifts,
        mode='lines+markers',
        name='Lift值',
        line=dict(color='#f97316', width=2),
        marker=dict(size=8, color='#f97316'),
        text=[f'{l:.2f}' for l in lifts],
        textposition='top center',
        hovertemplate='评分区间: %{x}<br>Lift: %{y:.2f}<extra></extra>'
    ))
    
    # 基准线 Lift=1
    fig.add_hline(y=1, line_dash='dash', line_color='#22c55e', 
                  annotation_text='Lift=1', annotation_position='right')
    
    # 构建标题：包含数据集标签（如果有）
    title_parts = []
    if dataset_label:
        title_parts.append(f'{dataset_label} ')
    title_parts.append(f'Lift曲线 (首组:{first_lift:.2f} 末组:{last_lift:.2f})')
    title_text = ''.join(title_parts)
    
    fig.update_layout(
        title=dict(text=title_text, x=0.5, font=dict(size=13)),
        xaxis_title='评分区间（高风险→低风险）',
        yaxis_title='Lift值',
        showlegend=False,
        template='plotly_white',
        width=width,
        height=height,
        margin=dict(l=50, r=20, t=50, b=80),  # 增加底部边距，避免标签被截断
        xaxis=dict(
            tickangle=-45,  # 标签倾斜45度，避免重叠
            tickfont=dict(size=10)
        )
    )
    
    if return_html:
        return str(fig.to_html(include_plotlyjs='cdn', full_html=False))
    else:
        return fig


def _generate_psi_comparison_chart(
    train_bins: list[dict[str, Any]], 
    compare_bins: list[dict[str, Any]], 
    compare_label: str,
    psi_value: float,
    width: int = 420, 
    height: int = 260,
    return_html: bool = True
) -> str | Any:
    """Generate PSI comparison bar chart (grouped bars).
    
    Args:
        train_bins: Training set distribution bins
        compare_bins: Comparison set (test/OOT) distribution bins
        compare_label: Label for comparison set
        psi_value: PSI value
        width: Chart width
        height: Chart height
        return_html: If True, return HTML string; if False, return Plotly Figure object
    
    Returns:
        HTML string or Plotly Figure object
    """
    if not _plotly_available or go is None:
        if return_html:
            return '<p class="error">Plotly不可用，无法生成PSI对比图</p>'
        else:
            return None
    
    if not train_bins or not compare_bins:
        if return_html:
            return '<p class="error">无PSI分布数据</p>'
        else:
            return None
    
    # 对齐两个数据集的分箱
    train_dict = {b.get('bin', b.get('score_range', '')): b.get('pct', b.get('pct_total', 0)) for b in train_bins}
    compare_dict = {b.get('bin', b.get('score_range', '')): b.get('pct', b.get('pct_total', 0)) for b in compare_bins}
    
    all_bins = list(train_dict.keys())
    train_pcts = [train_dict.get(b, 0) * 100 for b in all_bins]
    compare_pcts = [compare_dict.get(b, 0) * 100 for b in all_bins]
    
    fig = go.Figure()
    
    # 训练集柱状图
    fig.add_trace(go.Bar(
        x=all_bins,
        y=train_pcts,
        name='训练集',
        marker_color='#3b82f6',
        text=[f'{p:.1f}%' for p in train_pcts],
        textposition='outside',
        textfont=dict(size=9)
    ))
    
    # 对比集柱状图
    fig.add_trace(go.Bar(
        x=all_bins,
        y=compare_pcts,
        name=compare_label,
        marker_color='#f97316',
        text=[f'{p:.1f}%' for p in compare_pcts],
        textposition='outside',
        textfont=dict(size=9)
    ))
    
    # PSI状态
    stability = '稳定' if psi_value < 0.1 else '轻微变化' if psi_value < 0.25 else '显著变化'
    psi_color = '#16a34a' if psi_value < 0.1 else '#f59e0b' if psi_value < 0.25 else '#dc2626'
    
    fig.update_layout(
        title=dict(
            text=f'PSI分布对比（训练集 vs {compare_label}）<br><span style="font-size:11px;color:{psi_color};">PSI={psi_value:.4f} ({stability})</span>',
            x=0.5,
            font=dict(size=13)
        ),
        xaxis_title='评分区间',
        yaxis_title='占比 (%)',
        barmode='group',
        showlegend=True,
        legend=dict(x=0.8, y=0.95, font=dict(size=10)),
        template='plotly_white',
        width=width,
        height=height,
        margin=dict(l=50, r=20, t=70, b=80),
        xaxis_tickangle=-45
    )
    
    if return_html:
        return str(fig.to_html(include_plotlyjs='cdn', full_html=False))
    else:
        return fig


def generate_scorecard_report_html(
    metrics: dict[str, float],
    iv_table: pd.DataFrame,
    scorecard: pd.DataFrame,
    coefficients: pd.DataFrame,
    y_true: np.ndarray | None = None,
    y_score: np.ndarray | None = None,
    scores_good: np.ndarray | None = None,
    scores_bad: np.ndarray | None = None,
    chart_data: dict[str, Any] | None = None,
    multi_dataset_metrics: dict[str, dict[str, Any]] | None = None,
    multi_dataset_chart_data: dict[str, dict[str, Any]] | None = None,
    selected_features: list[str] | None = None,
    overfit_warning: str | None = None,
    selection_detail: dict[str, Any] | None = None,
    outlier_info: dict[str, dict[str, Any]] | None = None,
    title: str = '评分卡开发报告'
) -> str:
    """
    Generate comprehensive HTML report for scorecard development.
    
    .. deprecated::
        This function is deprecated. Use `deepanalyze.analysis.html_report.generate_html_report`
        or `deepanalyze.analysis.html_report.generate_scorecard_report_html` instead.
    
    This is a backward-compatible wrapper that redirects to the centralized
    html_report module.
    
    Args:
        metrics: Dictionary with 'ks', 'auc', 'gini' values
        iv_table: IV values DataFrame
        scorecard: Scorecard DataFrame
        coefficients: Model coefficients DataFrame
        y_true: True labels for ROC/KS curves (deprecated)
        y_score: Predicted scores for ROC/KS curves (deprecated)
        scores_good: Scores for good samples (deprecated)
        scores_bad: Scores for bad samples (deprecated)
        chart_data: Pre-computed chart data
        multi_dataset_metrics: Metrics for multiple datasets
        multi_dataset_chart_data: Chart data for multiple datasets
        selected_features: List of selected features
        overfit_warning: Overfit warning message
        selection_detail: Feature selection details
        outlier_info: Outlier detection results
        title: Report title
        
    Returns:
        HTML string
    """
    import warnings
    warnings.warn(
        "generate_scorecard_report_html in scorecard_viz is deprecated. "
        "Use deepanalyze.analysis.html_report.generate_html_report instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    from ..html_report import generate_scorecard_report_html as _generate_report
    return _generate_report(
        metrics=metrics,
        iv_table=iv_table,
        scorecard=scorecard,
        coefficients=coefficients,
        y_true=y_true,
        y_score=y_score,
        scores_good=scores_good,
        scores_bad=scores_bad,
        chart_data=chart_data,
        multi_dataset_metrics=multi_dataset_metrics,
        multi_dataset_chart_data=multi_dataset_chart_data,
        selected_features=selected_features,
        overfit_warning=overfit_warning,
        selection_detail=selection_detail,
        outlier_info=outlier_info,
        title=title
    )


def _calculate_nice_bin_width(score_range: float, target_bins: int = 8) -> float:
    """
    根据得分范围自动计算"美观"的分箱宽度。
    
    Args:
        score_range: 最大分 - 最小分
        target_bins: 目标分箱数（默认8个）
    
    Returns:
        美观的分箱宽度（如 5, 10, 20, 25, 50, 100 等）
    """
    if score_range <= 0:
        return 10.0
    
    raw_width = score_range / target_bins
    
    # 常用的"美观"宽度候选值
    nice_widths = [5, 10, 20, 25, 50, 100, 200, 250, 500]
    
    # 选择最接近 raw_width 的美观值
    best_width = min(nice_widths, key=lambda w: abs(w - raw_width))
    
    return float(best_width)


def _generate_equal_width_bins(all_scores: np.ndarray, target_bins: int = 8) -> np.ndarray:
    """
    生成自适应等宽分箱边界。
    
    Args:
        all_scores: 所有得分数组
        target_bins: 目标分箱数
    
    Returns:
        分箱边界数组
    """
    score_min = float(np.min(all_scores))
    score_max = float(np.max(all_scores))
    score_range = score_max - score_min
    
    # 计算美观的分箱宽度
    bin_width = _calculate_nice_bin_width(score_range, target_bins)
    
    # 生成对齐的分箱边界（向下/向上取整到宽度的整数倍）
    aligned_min = np.floor(score_min / bin_width) * bin_width
    aligned_max = np.ceil(score_max / bin_width) * bin_width
    
    # 生成边界
    bin_edges = np.arange(aligned_min, aligned_max + bin_width, bin_width)
    
    # 确保至少有2个边界
    if len(bin_edges) < 2:
        bin_edges = np.array([score_min, score_max])
    
    return bin_edges


def _generate_equal_frequency_bins(all_scores: np.ndarray, n_bins: int = 10) -> np.ndarray:
    """
    生成等频分箱边界（Decile）。
    
    Args:
        all_scores: 所有得分数组
        n_bins: 分箱数（默认10，即十分位）
    
    Returns:
        分箱边界数组
    """
    percentiles = np.linspace(0, 100, n_bins + 1)
    bin_edges: np.ndarray = np.percentile(all_scores, percentiles)
    
    # 去重（当多个样本得分相同时可能产生重复边界）
    bin_edges = np.unique(bin_edges)
    
    # 处理边界过少的情况
    if len(bin_edges) < 2:
        single_value = float(bin_edges[0]) if len(bin_edges) == 1 else float(np.mean(all_scores))
        bin_edges = np.array([single_value - 1, single_value, single_value + 1])
    elif len(bin_edges) == 2:
        mid_val = float((bin_edges[0] + bin_edges[1]) / 2)
        bin_edges = np.array([float(bin_edges[0]), mid_val, float(bin_edges[1])])
    
    return bin_edges


def _check_monotonicity(bins: list[dict[str, Any]]) -> dict[str, Any]:
    """
    检验Decile分析的单调性。
    
    行业标准：评分从低到高，坏样本率应单调递减。
    
    Args:
        bins: 分箱统计数据列表，每个元素包含 'bin', 'bad_rate', 'lift' 等字段
        
    Returns:
        单调性检验结果：
        - is_monotonic: 是否完全单调
        - status: 'pass' / 'fail'
        - violations: 违反单调性的分段索引列表
        - violation_details: 违反详情
    """
    if not bins or len(bins) < 2:
        return {
            'is_monotonic': True,
            'status': 'pass',
            'violations': [],
            'violation_details': []
        }
    
    violations: list[int] = []
    violation_details: list[dict[str, Any]] = []
    
    for i in range(1, len(bins)):
        prev_bad_rate = bins[i - 1].get('bad_rate', 0)
        curr_bad_rate = bins[i].get('bad_rate', 0)
        
        # 从低分到高分（索引递增），坏样本率应该递减
        if curr_bad_rate > prev_bad_rate:
            violations.append(i)
            violation_details.append({
                'index': i,
                'prev_bin': bins[i - 1].get('bin', ''),
                'curr_bin': bins[i].get('bin', ''),
                'prev_bad_rate': prev_bad_rate,
                'curr_bad_rate': curr_bad_rate,
                'diff': round(curr_bad_rate - prev_bad_rate, 2)
            })
    
    is_monotonic = len(violations) == 0
    
    return {
        'is_monotonic': is_monotonic,
        'status': 'pass' if is_monotonic else 'fail',
        'violations': violations,
        'violation_details': violation_details
    }


def _analyze_lift(bins: list[dict[str, Any]]) -> dict[str, Any]:
    """
    分析首尾Lift值。
    
    Lift = 分段坏样本率 / 整体坏样本率
    - 首组Lift：最低分段的风险倍数（应该 > 1，越高越好）
    - 末组Lift：最高分段的风险倍数（应该 < 1，越低越好）
    
    Args:
        bins: 分箱统计数据列表
        
    Returns:
        Lift分析结果
    """
    if not bins:
        return {
            'first_decile_lift': None,
            'last_decile_lift': None,
            'first_decile_bad_rate': None,
            'last_decile_bad_rate': None
        }
    
    first_bin = bins[0]
    last_bin = bins[-1]
    
    return {
        'first_decile_lift': first_bin.get('lift'),
        'last_decile_lift': last_bin.get('lift'),
        'first_decile_bad_rate': first_bin.get('bad_rate'),
        'last_decile_bad_rate': last_bin.get('bad_rate'),
        'first_decile_bin': first_bin.get('bin'),
        'last_decile_bin': last_bin.get('bin')
    }


def get_chart_data_for_frontend(
    y_true: np.ndarray,
    y_score: np.ndarray,
    scores: np.ndarray | None = None,
    score_bin_method: str = 'equal_width',
    score_distribution_bins: int = 8,
    ranking_analysis_bins: int = 10
) -> dict[str, Any]:
    """
    Generate chart data in JSON-serializable format for frontend rendering.
    
    Args:
        y_true: True binary labels
        y_score: Predicted probabilities
        scores: Final scores (optional)
        score_bin_method: Score distribution binning method
            - 'equal_width': 自适应等宽分箱（默认，区间宽度一致，如50分一档）
            - 'equal_frequency': 等频分箱（Decile，每个区间样本数相近）
        score_distribution_bins: Number of bins for equal-width distribution view (default: 8)
        ranking_analysis_bins: Number of bins for equal-frequency ranking analysis (default: 10, Decile)
        
    Returns:
        Dictionary with chart data for ROC, KS, and score distribution
    """
    from sklearn.metrics import roc_curve, auc
    
    result: dict[str, Any] = {}
    
    # ROC curve data
    fpr, tpr, _ = roc_curve(y_true, y_score)
    roc_auc = auc(fpr, tpr)
    result['roc'] = {
        'fpr': fpr.tolist(),
        'tpr': tpr.tolist(),
        'auc': float(roc_auc)
    }
    
    # KS curve data
    sorted_indices = np.argsort(y_score)
    y_true_sorted = np.array(y_true)[sorted_indices]
    sample_count = len(y_true_sorted)
    n_pos = int(np.sum(y_true_sorted == 1))
    n_neg = int(np.sum(y_true_sorted == 0))
    
    cum_pos_arr = np.cumsum(y_true_sorted == 1) / n_pos
    cum_neg_arr = np.cumsum(y_true_sorted == 0) / n_neg
    cum_pos_list: list[float] = cum_pos_arr.tolist()
    cum_neg_list: list[float] = cum_neg_arr.tolist()
    ks_values: list[float] = [abs(p - g) for p, g in zip(cum_pos_list, cum_neg_list)]
    ks_max = max(ks_values)
    ks_max_idx = ks_values.index(ks_max)
    
    result['ks'] = {
        'population_pct': [(i + 1) / sample_count * 100 for i in range(sample_count)],
        'cum_bad': [v * 100 for v in cum_pos_list],
        'cum_good': [v * 100 for v in cum_neg_list],
        'ks_curve': [v * 100 for v in ks_values],
        'ks_max': float(ks_max),
        'ks_max_position': float((ks_max_idx + 1) / sample_count * 100)
    }
    
    # Score distribution data with dual binning (ranking analysis + distribution)
    if scores is not None:
        # 行业惯例：评分卡最终分数取整到整数
        # 与评分转换阶段展示一致（如"均值619"而非"均值619.23"）
        scores_rounded = np.round(scores).astype(int)
        
        scores_good = scores_rounded[y_true == 0]
        scores_bad = scores_rounded[y_true == 1]
        all_scores = np.concatenate([scores_good, scores_bad])
        total_samples = len(all_scores)
        total_bad = int(np.sum(y_true == 1))
        overall_bad_rate = total_bad / total_samples if total_samples > 0 else 0.0
        
        # Create aligned y_true array for indexing
        y_true_aligned = np.concatenate([np.zeros(len(scores_good)), np.ones(len(scores_bad))])
        
        def _calculate_bin_stats(bin_edges: np.ndarray) -> list[dict[str, Any]]:
            """Calculate statistics for given bin edges.
            
            分箱边界使用整数格式，符合行业惯例。
            """
            bin_stats: list[dict[str, Any]] = []
            cum_samples = 0
            cum_bad_count = 0
            
            for i in range(len(bin_edges) - 1):
                # 分箱边界取整（向下取整用于下界，向上取整用于上界边界点）
                bin_low_val = int(np.floor(bin_edges[i]))
                bin_high_val = int(np.ceil(bin_edges[i + 1]))
                
                # 对于非首尾分箱，使用原始边界值判断（取整后）
                bin_low_actual = int(np.round(bin_edges[i]))
                bin_high_actual = int(np.round(bin_edges[i + 1]))
                
                # Format bin label - 使用整数格式
                if i == 0:
                    bin_label = f"[{bin_low_actual},{bin_high_actual})"
                elif i == len(bin_edges) - 2:
                    bin_label = f"[{bin_low_actual},{bin_high_actual}]"
                else:
                    bin_label = f"[{bin_low_actual},{bin_high_actual})"
                
                # Count samples in this bin (使用取整后的边界)
                if i == len(bin_edges) - 2:
                    bin_mask = (all_scores >= bin_low_actual) & (all_scores <= bin_high_actual)
                else:
                    bin_mask = (all_scores >= bin_low_actual) & (all_scores < bin_high_actual)
                
                bin_total = int(np.sum(bin_mask))
                bin_bad_count = int(np.sum(y_true_aligned[bin_mask] == 1)) if bin_total > 0 else 0
                bin_good_count = bin_total - bin_bad_count
                
                # Calculate rates
                pct_total = bin_total / total_samples * 100 if total_samples > 0 else 0.0
                bad_rate = bin_bad_count / bin_total * 100 if bin_total > 0 else 0.0
                lift = (bin_bad_count / bin_total) / overall_bad_rate if bin_total > 0 and overall_bad_rate > 0 else 0.0
                
                # Cumulative (from low score to high score)
                cum_samples += bin_total
                cum_bad_count += bin_bad_count
                cum_bad_rate = cum_bad_count / total_bad * 100 if total_bad > 0 else 0.0
                
                bin_stats.append({
                    'bin': bin_label,
                    'total': bin_total,
                    'pct_total': round(pct_total, 2),
                    'bad': bin_bad_count,
                    'good': bin_good_count,
                    'bad_rate': round(bad_rate, 2),
                    'lift': round(lift, 2),
                    'cum_bad_rate': round(cum_bad_rate, 2)
                })
            
            return bin_stats
        
        # 生成等频分箱（用于排序性分析）- 默认10组 Decile
        equal_freq_edges = _generate_equal_frequency_bins(all_scores, n_bins=ranking_analysis_bins)
        ranking_bins = _calculate_bin_stats(equal_freq_edges)
        
        # 生成等宽分箱（用于评分分布展示）- 默认约8组
        equal_width_edges = _generate_equal_width_bins(all_scores, target_bins=score_distribution_bins)
        distribution_bins = _calculate_bin_stats(equal_width_edges)
        
        # Summary statistics (shared) - 使用取整后的分数
        summary = {
            'total_samples': int(total_samples),
            'total_bad': int(total_bad),
            'total_good': int(total_samples - total_bad),
            'overall_bad_rate': round(overall_bad_rate * 100, 2),
            'good_mean': round(float(np.mean(scores_good)), 1),  # 保留1位小数
            'bad_mean': round(float(np.mean(scores_bad)), 1),    # 保留1位小数
            'score_min': int(np.min(all_scores)),
            'score_max': int(np.max(all_scores))
        }
        
        # 根据用户选择的方法决定默认使用哪种分箱作为主视图
        if score_bin_method == 'equal_frequency':
            primary_bins = ranking_bins
            bin_method_label = 'equal_frequency'
        else:
            primary_bins = distribution_bins
            bin_method_label = 'equal_width'
        
        # 排序性分析（基于等频分箱/Decile）
        monotonicity_result = _check_monotonicity(ranking_bins)
        lift_analysis_result = _analyze_lift(ranking_bins)
        
        result['score_distribution'] = {
            # 主分箱数据（向后兼容）
            'bins': primary_bins,
            'bin_method': bin_method_label,
            'summary': summary,
            # 双视图数据
            'ranking_analysis': {
                'bins': ranking_bins,
                'bin_method': 'equal_frequency',
                'n_bins': ranking_analysis_bins,
                'description': f'等频分箱（{ranking_analysis_bins}组）- 用于排序性分析'
            },
            'distribution_view': {
                'bins': distribution_bins,
                'bin_method': 'equal_width',
                'n_bins': score_distribution_bins,
                'description': f'等宽分箱（目标{score_distribution_bins}组）- 用于评分分布展示'
            },
            # 排序性分析结果（新增）
            'rank_ordering_analysis': {
                'monotonicity': monotonicity_result,
                'lift_analysis': lift_analysis_result
            }
        }
    
    return result
