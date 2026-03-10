"""
Rule Mining Visualization Module

Provides visualization functions for rule mining results:
- Cumulative metrics curve (recall, hit_rate, lift)
- Rule distribution chart
- Rule comparison chart
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
import warnings

warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=DeprecationWarning)

# Try to import visualization libraries
try:
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False


def _setup_chinese_font():
    """Setup Chinese font for matplotlib."""
    if not HAS_MATPLOTLIB:
        return
    
    # Try common Chinese fonts
    chinese_fonts = [
        'SimHei', 'Microsoft YaHei', 'STHeiti', 'WenQuanYi Micro Hei',
        'Noto Sans CJK SC', 'Source Han Sans SC', 'PingFang SC'
    ]
    
    for font in chinese_fonts:
        try:
            fm.findfont(font)
            plt.rcParams['font.sans-serif'] = [font] + plt.rcParams['font.sans-serif']
            plt.rcParams['axes.unicode_minus'] = False
            return
        except Exception:
            continue


def plot_cumulative_metrics(
    optimal_rules_df: pd.DataFrame,
    output_format: str = 'plotly',
    title: str = '累计指标曲线',
    figsize: Tuple[int, int] = (10, 6),
    show_legend: bool = True,
    return_html: bool = False
) -> Any:
    """
    Plot cumulative metrics curve for optimal rule set.
    
    Shows how recall, hit_rate, and lift accumulate as rules are added.
    
    Args:
        optimal_rules_df: DataFrame with columns:
            - rule: Rule expression
            - dev_cum_recall: Cumulative recall
            - dev_cum_hit_rate: Cumulative hit rate
            - dev_cum_lift: Cumulative lift
        output_format: 'plotly' or 'matplotlib'
        title: Chart title
        figsize: Figure size for matplotlib
        show_legend: Whether to show legend
        return_html: If True, return HTML string (plotly only)
        
    Returns:
        Plotly figure, matplotlib figure, or HTML string
    """
    if optimal_rules_df is None or len(optimal_rules_df) == 0:
        raise ValueError("optimal_rules_df is empty or None")
    
    # Prepare data
    n_rules = len(optimal_rules_df)
    x_labels = [f"规则{i+1}" for i in range(n_rules)]
    
    # Extract metrics
    recall = optimal_rules_df['dev_cum_recall'].values
    hit_rate = optimal_rules_df['dev_cum_hit_rate'].values
    lift = optimal_rules_df.get('dev_cum_lift', optimal_rules_df.get('lift', [0] * n_rules))
    if isinstance(lift, pd.Series):
        lift = lift.values
    
    if output_format == 'plotly' and HAS_PLOTLY:
        return _plot_cumulative_plotly(
            x_labels, recall, hit_rate, lift, title, show_legend, return_html
        )
    elif HAS_MATPLOTLIB:
        return _plot_cumulative_matplotlib(
            x_labels, recall, hit_rate, lift, title, figsize, show_legend
        )
    else:
        raise ImportError("Neither plotly nor matplotlib is available")


def _plot_cumulative_plotly(
    x_labels: List[str],
    recall: np.ndarray,
    hit_rate: np.ndarray,
    lift: np.ndarray,
    title: str,
    show_legend: bool,
    return_html: bool
) -> Any:
    """Create cumulative metrics chart using Plotly."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Recall line (primary y-axis)
    fig.add_trace(
        go.Scatter(
            x=x_labels,
            y=recall,
            mode='lines+markers',
            name='累计召回率 (Recall)',
            line=dict(color='#2E86AB', width=2),
            marker=dict(size=8)
        ),
        secondary_y=False
    )
    
    # Hit rate line (primary y-axis)
    fig.add_trace(
        go.Scatter(
            x=x_labels,
            y=hit_rate,
            mode='lines+markers',
            name='累计命中率 (Hit Rate)',
            line=dict(color='#A23B72', width=2),
            marker=dict(size=8)
        ),
        secondary_y=False
    )
    
    # Lift bars (secondary y-axis)
    fig.add_trace(
        go.Bar(
            x=x_labels,
            y=lift,
            name='累计提升倍数 (Lift)',
            marker_color='rgba(144, 190, 109, 0.6)',
            yaxis='y2'
        ),
        secondary_y=True
    )
    
    # Update layout
    fig.update_layout(
        title=dict(text=title, x=0.5, font=dict(size=16)),
        xaxis_title='规则序号',
        showlegend=show_legend,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        ),
        hovermode='x unified',
        template='plotly_white'
    )
    
    fig.update_yaxes(title_text="比率", secondary_y=False)
    fig.update_yaxes(title_text="Lift倍数", secondary_y=True)
    
    if return_html:
        return fig.to_html(include_plotlyjs='cdn', full_html=False)
    return fig


def _plot_cumulative_matplotlib(
    x_labels: List[str],
    recall: np.ndarray,
    hit_rate: np.ndarray,
    lift: np.ndarray,
    title: str,
    figsize: Tuple[int, int],
    show_legend: bool
) -> Any:
    """Create cumulative metrics chart using Matplotlib."""
    _setup_chinese_font()
    
    fig, ax1 = plt.subplots(figsize=figsize)
    
    x = np.arange(len(x_labels))
    
    # Primary axis - rates
    ax1.set_xlabel('规则序号')
    ax1.set_ylabel('比率', color='black')
    
    line1, = ax1.plot(x, recall, 'o-', color='#2E86AB', linewidth=2, 
                       markersize=8, label='累计召回率')
    line2, = ax1.plot(x, hit_rate, 's-', color='#A23B72', linewidth=2,
                       markersize=8, label='累计命中率')
    ax1.tick_params(axis='y', labelcolor='black')
    ax1.set_xticks(x)
    ax1.set_xticklabels(x_labels, rotation=45, ha='right')
    
    # Secondary axis - lift
    ax2 = ax1.twinx()
    ax2.set_ylabel('Lift倍数', color='#5C8A4D')
    bars = ax2.bar(x, lift, alpha=0.5, color='#90BE6D', label='累计Lift')
    ax2.tick_params(axis='y', labelcolor='#5C8A4D')
    
    # Title
    plt.title(title, fontsize=14, fontweight='bold')
    
    # Legend
    if show_legend:
        lines = [line1, line2, bars]
        labels = ['累计召回率', '累计命中率', '累计Lift']
        ax1.legend(lines, labels, loc='upper left')
    
    plt.tight_layout()
    return fig


def plot_rule_distribution(
    evaluated_rules_df: pd.DataFrame,
    x_metric: str = 'hit_rate',
    y_metric: str = 'lift',
    color_metric: str = 'recall',
    output_format: str = 'plotly',
    title: str = '规则分布图',
    figsize: Tuple[int, int] = (10, 8),
    return_html: bool = False
) -> Any:
    """
    Plot rule distribution scatter chart.
    
    Shows how rules are distributed across different metrics.
    
    Args:
        evaluated_rules_df: DataFrame with rule evaluation metrics
        x_metric: Metric for x-axis (hit_rate, recall, bad_rate)
        y_metric: Metric for y-axis (lift, bad_rate, recall)
        color_metric: Metric for color coding
        output_format: 'plotly' or 'matplotlib'
        title: Chart title
        figsize: Figure size for matplotlib
        return_html: If True, return HTML string (plotly only)
        
    Returns:
        Plotly figure, matplotlib figure, or HTML string
    """
    if evaluated_rules_df is None or len(evaluated_rules_df) == 0:
        raise ValueError("evaluated_rules_df is empty or None")
    
    # Validate metrics exist
    for metric in [x_metric, y_metric, color_metric]:
        if metric not in evaluated_rules_df.columns:
            raise ValueError(f"Metric '{metric}' not found in DataFrame")
    
    if output_format == 'plotly' and HAS_PLOTLY:
        return _plot_distribution_plotly(
            evaluated_rules_df, x_metric, y_metric, color_metric,
            title, return_html
        )
    elif HAS_MATPLOTLIB:
        return _plot_distribution_matplotlib(
            evaluated_rules_df, x_metric, y_metric, color_metric,
            title, figsize
        )
    else:
        raise ImportError("Neither plotly nor matplotlib is available")


def _plot_distribution_plotly(
    df: pd.DataFrame,
    x_metric: str,
    y_metric: str,
    color_metric: str,
    title: str,
    return_html: bool
) -> Any:
    """Create rule distribution chart using Plotly."""
    # Metric labels
    metric_labels = {
        'hit_rate': '命中率',
        'recall': '召回率',
        'lift': '提升倍数',
        'bad_rate': '坏账率'
    }
    
    fig = px.scatter(
        df,
        x=x_metric,
        y=y_metric,
        color=color_metric,
        hover_data=['rule'] if 'rule' in df.columns else None,
        title=title,
        labels={
            x_metric: metric_labels.get(x_metric, x_metric),
            y_metric: metric_labels.get(y_metric, y_metric),
            color_metric: metric_labels.get(color_metric, color_metric)
        },
        color_continuous_scale='Viridis'
    )
    
    fig.update_layout(
        title=dict(text=title, x=0.5, font=dict(size=16)),
        template='plotly_white',
        hovermode='closest'
    )
    
    fig.update_traces(marker=dict(size=10, opacity=0.7))
    
    if return_html:
        return fig.to_html(include_plotlyjs='cdn', full_html=False)
    return fig


def _plot_distribution_matplotlib(
    df: pd.DataFrame,
    x_metric: str,
    y_metric: str,
    color_metric: str,
    title: str,
    figsize: Tuple[int, int]
) -> Any:
    """Create rule distribution chart using Matplotlib."""
    _setup_chinese_font()
    
    metric_labels = {
        'hit_rate': '命中率',
        'recall': '召回率',
        'lift': '提升倍数',
        'bad_rate': '坏账率'
    }
    
    fig, ax = plt.subplots(figsize=figsize)
    
    scatter = ax.scatter(
        df[x_metric],
        df[y_metric],
        c=df[color_metric],
        cmap='viridis',
        s=80,
        alpha=0.7
    )
    
    ax.set_xlabel(metric_labels.get(x_metric, x_metric))
    ax.set_ylabel(metric_labels.get(y_metric, y_metric))
    ax.set_title(title, fontsize=14, fontweight='bold')
    
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label(metric_labels.get(color_metric, color_metric))
    
    plt.tight_layout()
    return fig


def plot_rule_comparison(
    rules_df: pd.DataFrame,
    metrics: List[str] = None,
    top_n: int = 10,
    output_format: str = 'plotly',
    title: str = '规则效果对比',
    figsize: Tuple[int, int] = (12, 6),
    return_html: bool = False
) -> Any:
    """
    Plot horizontal bar chart comparing top rules.
    
    Args:
        rules_df: DataFrame with rule evaluation metrics
        metrics: Metrics to compare (default: ['recall', 'hit_rate', 'lift'])
        top_n: Number of top rules to show
        output_format: 'plotly' or 'matplotlib'
        title: Chart title
        figsize: Figure size for matplotlib
        return_html: If True, return HTML string (plotly only)
        
    Returns:
        Plotly figure, matplotlib figure, or HTML string
    """
    if rules_df is None or len(rules_df) == 0:
        raise ValueError("rules_df is empty or None")
    
    if metrics is None:
        metrics = ['recall', 'hit_rate', 'lift']
    
    # Filter to available metrics
    available_metrics = [m for m in metrics if m in rules_df.columns]
    if not available_metrics:
        raise ValueError(f"None of the metrics {metrics} found in DataFrame")
    
    # Get top N rules by first metric
    df_top = rules_df.nlargest(top_n, available_metrics[0]).copy()
    
    if output_format == 'plotly' and HAS_PLOTLY:
        return _plot_comparison_plotly(
            df_top, available_metrics, title, return_html
        )
    elif HAS_MATPLOTLIB:
        return _plot_comparison_matplotlib(
            df_top, available_metrics, title, figsize
        )
    else:
        raise ImportError("Neither plotly nor matplotlib is available")


def _plot_comparison_plotly(
    df: pd.DataFrame,
    metrics: List[str],
    title: str,
    return_html: bool
) -> Any:
    """Create rule comparison chart using Plotly."""
    metric_labels = {
        'hit_rate': '命中率',
        'recall': '召回率',
        'lift': '提升倍数',
        'bad_rate': '坏账率'
    }
    
    colors = ['#2E86AB', '#A23B72', '#90BE6D', '#F18F01']
    
    fig = go.Figure()
    
    # Create short labels for rules
    if 'rule' in df.columns:
        labels = [f"规则{i+1}" for i in range(len(df))]
    else:
        labels = [f"规则{i+1}" for i in range(len(df))]
    
    for i, metric in enumerate(metrics):
        fig.add_trace(go.Bar(
            name=metric_labels.get(metric, metric),
            y=labels,
            x=df[metric],
            orientation='h',
            marker_color=colors[i % len(colors)]
        ))
    
    fig.update_layout(
        title=dict(text=title, x=0.5, font=dict(size=16)),
        barmode='group',
        xaxis_title='指标值',
        yaxis_title='规则',
        template='plotly_white',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        )
    )
    
    if return_html:
        return fig.to_html(include_plotlyjs='cdn', full_html=False)
    return fig


def _plot_comparison_matplotlib(
    df: pd.DataFrame,
    metrics: List[str],
    title: str,
    figsize: Tuple[int, int]
) -> Any:
    """Create rule comparison chart using Matplotlib."""
    _setup_chinese_font()
    
    metric_labels = {
        'hit_rate': '命中率',
        'recall': '召回率',
        'lift': '提升倍数',
        'bad_rate': '坏账率'
    }
    
    colors = ['#2E86AB', '#A23B72', '#90BE6D', '#F18F01']
    
    fig, ax = plt.subplots(figsize=figsize)
    
    n_rules = len(df)
    n_metrics = len(metrics)
    bar_height = 0.8 / n_metrics
    
    y = np.arange(n_rules)
    labels = [f"规则{i+1}" for i in range(n_rules)]
    
    for i, metric in enumerate(metrics):
        offset = (i - n_metrics / 2 + 0.5) * bar_height
        ax.barh(
            y + offset,
            df[metric],
            bar_height,
            label=metric_labels.get(metric, metric),
            color=colors[i % len(colors)]
        )
    
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlabel('指标值')
    ax.set_ylabel('规则')
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.legend(loc='lower right')
    
    plt.tight_layout()
    return fig


def generate_rule_summary_html(
    optimal_rules_df: pd.DataFrame,
    evaluated_rules_df: pd.DataFrame = None,
    include_charts: bool = True
) -> str:
    """
    Generate HTML summary report for rule mining results.
    
    Args:
        optimal_rules_df: DataFrame with optimal rule set
        evaluated_rules_df: DataFrame with all evaluated rules (optional)
        include_charts: Whether to include interactive charts
        
    Returns:
        HTML string with summary report
    """
    html_parts = []
    
    # Header
    html_parts.append("""
    <div class="rule-mining-report">
        <style>
            .rule-mining-report { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
            .report-section { margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 8px; }
            .report-title { font-size: 18px; font-weight: 600; margin-bottom: 15px; color: #333; }
            .metric-card { display: inline-block; padding: 12px 20px; margin: 5px; background: white; 
                          border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
            .metric-value { font-size: 24px; font-weight: 700; color: #2E86AB; }
            .metric-label { font-size: 12px; color: #666; margin-top: 4px; }
            .rule-table { width: 100%; border-collapse: collapse; margin-top: 15px; }
            .rule-table th, .rule-table td { padding: 10px; text-align: left; border-bottom: 1px solid #eee; }
            .rule-table th { background: #f0f0f0; font-weight: 600; }
            .rule-table tr:hover { background: #f5f5f5; }
        </style>
    """)
    
    # Summary metrics
    if optimal_rules_df is not None and len(optimal_rules_df) > 0:
        n_rules = len(optimal_rules_df)
        final_recall = optimal_rules_df['dev_cum_recall'].iloc[-1] if 'dev_cum_recall' in optimal_rules_df.columns else 0
        final_hit_rate = optimal_rules_df['dev_cum_hit_rate'].iloc[-1] if 'dev_cum_hit_rate' in optimal_rules_df.columns else 0
        final_lift = optimal_rules_df['dev_cum_lift'].iloc[-1] if 'dev_cum_lift' in optimal_rules_df.columns else 0
        
        html_parts.append(f"""
        <div class="report-section">
            <div class="report-title">📊 规则挖掘结果摘要</div>
            <div class="metric-card">
                <div class="metric-value">{n_rules}</div>
                <div class="metric-label">最优规则数</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{final_recall:.1%}</div>
                <div class="metric-label">累计召回率</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{final_hit_rate:.1%}</div>
                <div class="metric-label">累计命中率</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{final_lift:.1f}x</div>
                <div class="metric-label">累计提升倍数</div>
            </div>
        </div>
        """)
        
        # Charts
        if include_charts and HAS_PLOTLY:
            try:
                cumulative_chart = plot_cumulative_metrics(
                    optimal_rules_df, 
                    output_format='plotly',
                    return_html=True
                )
                html_parts.append(f"""
                <div class="report-section">
                    <div class="report-title">📈 累计指标曲线</div>
                    {cumulative_chart}
                </div>
                """)
            except Exception as e:
                html_parts.append(f"<p>无法生成累计指标曲线: {e}</p>")
        
        # Rule table
        html_parts.append("""
        <div class="report-section">
            <div class="report-title">📋 最优规则列表</div>
            <table class="rule-table">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>规则</th>
                        <th>累计召回率</th>
                        <th>累计命中率</th>
                        <th>累计Lift</th>
                    </tr>
                </thead>
                <tbody>
        """)
        
        for i, row in optimal_rules_df.iterrows():
            rule_text = row.get('rule', row.get('rule_chinese', f'规则{i+1}'))
            if len(str(rule_text)) > 80:
                rule_text = str(rule_text)[:77] + '...'
            
            recall = row.get('dev_cum_recall', 0)
            hit_rate = row.get('dev_cum_hit_rate', 0)
            lift = row.get('dev_cum_lift', row.get('lift', 0))
            
            html_parts.append(f"""
                <tr>
                    <td>{i+1}</td>
                    <td title="{row.get('rule', '')}">{rule_text}</td>
                    <td>{recall:.1%}</td>
                    <td>{hit_rate:.1%}</td>
                    <td>{lift:.1f}x</td>
                </tr>
            """)
        
        html_parts.append("""
                </tbody>
            </table>
        </div>
        """)
    
    # Distribution chart
    if include_charts and evaluated_rules_df is not None and len(evaluated_rules_df) > 0 and HAS_PLOTLY:
        try:
            distribution_chart = plot_rule_distribution(
                evaluated_rules_df,
                output_format='plotly',
                return_html=True
            )
            html_parts.append(f"""
            <div class="report-section">
                <div class="report-title">🎯 规则分布图</div>
                {distribution_chart}
            </div>
            """)
        except Exception as e:
            html_parts.append(f"<p>无法生成规则分布图: {e}</p>")
    
    html_parts.append("</div>")
    
    return "\n".join(html_parts)


def get_chart_data_for_frontend(
    optimal_rules_df: pd.DataFrame,
    evaluated_rules_df: pd.DataFrame = None
) -> Dict[str, Any]:
    """
    Generate chart data in JSON-serializable format for frontend rendering.
    
    This function mirrors scorecard_viz.get_chart_data_for_frontend() to maintain
    consistent architecture across all SOP tasks.
    
    Args:
        optimal_rules_df: DataFrame with optimal rule set containing columns:
            - rule: Rule expression
            - dev_cum_recall: Cumulative recall
            - dev_cum_hit_rate: Cumulative hit rate
            - dev_cum_lift: Cumulative lift
        evaluated_rules_df: DataFrame with all evaluated rules (optional)
        
    Returns:
        Dictionary with chart data for cumulative metrics, rule distribution, etc.
    """
    result = {}
    
    # Cumulative metrics curve data
    if optimal_rules_df is not None and len(optimal_rules_df) > 0:
        n_rules = len(optimal_rules_df)
        
        # Extract metrics with safe defaults
        recall = optimal_rules_df.get('dev_cum_recall', pd.Series([0] * n_rules))
        hit_rate = optimal_rules_df.get('dev_cum_hit_rate', pd.Series([0] * n_rules))
        lift = optimal_rules_df.get('dev_cum_lift', optimal_rules_df.get('lift', pd.Series([0] * n_rules)))
        
        # Convert to list, handling NaN values
        def safe_to_list(series):
            if isinstance(series, pd.Series):
                return [float(v) if pd.notna(v) else 0.0 for v in series.values]
            elif isinstance(series, np.ndarray):
                return [float(v) if not np.isnan(v) else 0.0 for v in series]
            return list(series)
        
        result['cumulative_metrics'] = {
            'labels': [f"规则{i+1}" for i in range(n_rules)],
            'recall': safe_to_list(recall),
            'hit_rate': safe_to_list(hit_rate),
            'lift': safe_to_list(lift),
            'final_recall': float(recall.iloc[-1]) if hasattr(recall, 'iloc') else float(recall[-1]) if len(recall) > 0 else 0,
            'final_hit_rate': float(hit_rate.iloc[-1]) if hasattr(hit_rate, 'iloc') else float(hit_rate[-1]) if len(hit_rate) > 0 else 0,
            'final_lift': float(lift.iloc[-1]) if hasattr(lift, 'iloc') else float(lift[-1]) if len(lift) > 0 else 0,
            'n_rules': n_rules
        }
        
        # Rule details for table
        rules_data = []
        for i, row in optimal_rules_df.iterrows():
            rule_info = {
                'index': i + 1 if isinstance(i, int) else len(rules_data) + 1,
                'rule': str(row.get('rule', row.get('rule_chinese', f'规则{len(rules_data)+1}'))),
                'recall': float(row.get('dev_cum_recall', 0)),
                'hit_rate': float(row.get('dev_cum_hit_rate', 0)),
                'lift': float(row.get('dev_cum_lift', row.get('lift', 0)))
            }
            rules_data.append(rule_info)
        
        result['rules_table'] = rules_data
    
    # Rule distribution data (scatter plot)
    if evaluated_rules_df is not None and len(evaluated_rules_df) > 0:
        def safe_values(col_name, default=0):
            if col_name in evaluated_rules_df.columns:
                return [float(v) if pd.notna(v) else default for v in evaluated_rules_df[col_name].values]
            return [default] * len(evaluated_rules_df)
        
        result['rule_distribution'] = {
            'hit_rate': safe_values('hit_rate'),
            'recall': safe_values('recall'),
            'lift': safe_values('lift'),
            'n_rules': len(evaluated_rules_df)
        }
    
    # Summary metrics
    if optimal_rules_df is not None and len(optimal_rules_df) > 0:
        result['summary'] = {
            'n_optimal_rules': len(optimal_rules_df),
            'final_recall': result.get('cumulative_metrics', {}).get('final_recall', 0),
            'final_hit_rate': result.get('cumulative_metrics', {}).get('final_hit_rate', 0),
            'final_lift': result.get('cumulative_metrics', {}).get('final_lift', 0)
        }
        
        if evaluated_rules_df is not None:
            result['summary']['n_evaluated_rules'] = len(evaluated_rules_df)
    
    return result


# =============================================================================
# Rule PSI Trend Visualization
# =============================================================================

def plot_psi_trend(
    psi_data: pd.DataFrame | List[Dict[str, Any]],
    output_format: str = 'plotly',
    title: str = '规则PSI稳定性趋势图',
    figsize: Tuple[int, int] = (12, 6),
    return_html: bool = False
) -> Any:
    """
    Plot rule PSI stability trend over time periods.
    
    Shows how rule stability (PSI) changes across different time periods.
    
    Args:
        psi_data: DataFrame or list of dicts with PSI data. Expected columns/keys:
            - rule: Rule expression
            - period: Time period identifier (e.g., '2024-Q1', '2024-Q2')
            - psi: PSI value for that period
            - hit_rate_base: Base period hit rate
            - hit_rate_compare: Compare period hit rate
        output_format: 'plotly' or 'matplotlib'
        title: Chart title
        figsize: Figure size for matplotlib
        return_html: If True, return HTML string (plotly only)
        
    Returns:
        Plotly figure, matplotlib figure, or HTML string
    """
    # Convert to DataFrame if needed
    if isinstance(psi_data, list):
        df = pd.DataFrame(psi_data)
    else:
        df = psi_data.copy()
    
    if df is None or len(df) == 0:
        raise ValueError("psi_data is empty or None")
    
    # Check required columns
    if 'rule' not in df.columns:
        raise ValueError("psi_data must contain 'rule' column")
    
    if output_format == 'plotly' and HAS_PLOTLY:
        return _plot_psi_trend_plotly(df, title, return_html)
    elif HAS_MATPLOTLIB:
        return _plot_psi_trend_matplotlib(df, title, figsize)
    else:
        raise ImportError("Neither plotly nor matplotlib is available")


def _plot_psi_trend_plotly(
    df: pd.DataFrame,
    title: str,
    return_html: bool
) -> Any:
    """Create PSI trend chart using Plotly."""
    fig = go.Figure()
    
    # Check if we have multi-period data or single comparison
    if 'period' in df.columns:
        # Multi-period trend
        rules = df['rule'].unique()
        colors = px.colors.qualitative.Set2
        
        for i, rule in enumerate(rules):
            rule_data = df[df['rule'] == rule].sort_values('period')
            short_rule = f"规则{i+1}" if len(str(rule)) > 30 else str(rule)[:30]
            
            fig.add_trace(go.Scatter(
                x=rule_data['period'],
                y=rule_data['psi'],
                mode='lines+markers',
                name=short_rule,
                line=dict(color=colors[i % len(colors)], width=2),
                marker=dict(size=8),
                hovertemplate=f"<b>{short_rule}</b><br>" +
                              "时期: %{x}<br>" +
                              "PSI: %{y:.4f}<extra></extra>"
            ))
    else:
        # Single comparison - bar chart by rule
        rules = df['rule'].tolist()
        psi_values = df.get('psi', [0] * len(rules))
        
        # Create short labels
        short_labels = [f"规则{i+1}" for i in range(len(rules))]
        
        # Color by stability
        colors = []
        for psi in psi_values:
            if pd.isna(psi) or psi is None:
                colors.append('#999999')  # Gray for N/A
            elif psi < 0.1:
                colors.append('#4CAF50')  # Green - stable
            elif psi < 0.25:
                colors.append('#FF9800')  # Orange - slight change
            else:
                colors.append('#F44336')  # Red - significant change
        
        fig.add_trace(go.Bar(
            x=short_labels,
            y=psi_values,
            marker_color=colors,
            text=[f"{v:.4f}" if pd.notna(v) else "N/A" for v in psi_values],
            textposition='outside',
            hovertemplate="<b>%{x}</b><br>" +
                          "PSI: %{y:.4f}<extra></extra>"
        ))
        
        # Add threshold lines
        fig.add_hline(y=0.1, line_dash="dash", line_color="orange",
                      annotation_text="轻微变化阈值 (0.1)")
        fig.add_hline(y=0.25, line_dash="dash", line_color="red",
                      annotation_text="显著变化阈值 (0.25)")
    
    fig.update_layout(
        title=dict(text=title, x=0.5, font=dict(size=16)),
        xaxis_title='时期' if 'period' in df.columns else '规则',
        yaxis_title='PSI值',
        template='plotly_white',
        showlegend='period' in df.columns,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        ),
        hovermode='x unified' if 'period' in df.columns else 'closest'
    )
    
    if return_html:
        return fig.to_html(include_plotlyjs='cdn', full_html=False)
    return fig


def _plot_psi_trend_matplotlib(
    df: pd.DataFrame,
    title: str,
    figsize: Tuple[int, int]
) -> Any:
    """Create PSI trend chart using Matplotlib."""
    _setup_chinese_font()
    
    fig, ax = plt.subplots(figsize=figsize)
    
    if 'period' in df.columns:
        # Multi-period trend - line chart
        rules = df['rule'].unique()
        colors = plt.cm.Set2(np.linspace(0, 1, len(rules)))
        
        for i, rule in enumerate(rules):
            rule_data = df[df['rule'] == rule].sort_values('period')
            short_rule = f"规则{i+1}"
            ax.plot(rule_data['period'], rule_data['psi'], 
                    'o-', color=colors[i], linewidth=2, 
                    markersize=8, label=short_rule)
    else:
        # Single comparison - bar chart
        rules = [f"规则{i+1}" for i in range(len(df))]
        psi_values = df.get('psi', [0] * len(df))
        
        # Color by stability
        colors = []
        for psi in psi_values:
            if pd.isna(psi) or psi is None:
                colors.append('#999999')
            elif psi < 0.1:
                colors.append('#4CAF50')
            elif psi < 0.25:
                colors.append('#FF9800')
            else:
                colors.append('#F44336')
        
        bars = ax.bar(rules, psi_values, color=colors)
        
        # Add value labels
        for bar, val in zip(bars, psi_values):
            if pd.notna(val):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                        f'{val:.4f}', ha='center', va='bottom', fontsize=9)
        
        # Add threshold lines
        ax.axhline(y=0.1, color='orange', linestyle='--', label='轻微变化阈值')
        ax.axhline(y=0.25, color='red', linestyle='--', label='显著变化阈值')
    
    ax.set_xlabel('时期' if 'period' in df.columns else '规则')
    ax.set_ylabel('PSI值')
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.legend(loc='upper right')
    
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    return fig


def get_psi_trend_data_for_frontend(
    psi_report: pd.DataFrame | List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Generate PSI trend data in JSON-serializable format for frontend rendering.
    
    Args:
        psi_report: DataFrame or list with PSI data
        
    Returns:
        Dictionary with PSI trend chart data
    """
    if isinstance(psi_report, list):
        df = pd.DataFrame(psi_report)
    else:
        df = psi_report.copy() if psi_report is not None else pd.DataFrame()
    
    if len(df) == 0:
        return {'rules': [], 'psi_values': [], 'stability': []}
    
    # Extract data
    rules = df.get('rule', pd.Series([])).tolist()
    psi_values = df.get('psi', pd.Series([])).tolist()
    
    # Calculate stability labels
    stability = []
    for psi in psi_values:
        if pd.isna(psi) or psi is None:
            stability.append('N/A')
        elif psi < 0.1:
            stability.append('稳定')
        elif psi < 0.25:
            stability.append('轻微变化')
        else:
            stability.append('显著变化')
    
    result = {
        'rules': [f"规则{i+1}" for i in range(len(rules))],
        'rule_expressions': rules,
        'psi_values': [float(v) if pd.notna(v) else None for v in psi_values],
        'stability': stability,
        'hit_rate_base': df.get('hit_rate_base', pd.Series([])).tolist(),
        'hit_rate_compare': df.get('hit_rate_compare', pd.Series([])).tolist(),
        'thresholds': {
            'slight_change': 0.1,
            'significant_change': 0.25
        }
    }
    
    # Add summary statistics
    valid_psi = [v for v in psi_values if pd.notna(v)]
    if valid_psi:
        result['summary'] = {
            'avg_psi': float(np.mean(valid_psi)),
            'max_psi': float(np.max(valid_psi)),
            'min_psi': float(np.min(valid_psi)),
            'n_stable': sum(1 for v in valid_psi if v < 0.1),
            'n_slight_change': sum(1 for v in valid_psi if 0.1 <= v < 0.25),
            'n_significant_change': sum(1 for v in valid_psi if v >= 0.25)
        }
    
    return result


# =============================================================================
# Decision Tree Visualization
# =============================================================================

def plot_decision_tree(
    clf: Any,
    feature_names: List[str] | None = None,
    class_names: List[str] | None = None,
    output_format: str = 'plotly',
    title: str = '决策树结构图',
    figsize: Tuple[int, int] = (20, 12),
    max_depth: int | None = None,
    return_html: bool = False,
    return_svg: bool = False
) -> Any:
    """
    Visualize a trained decision tree classifier.
    
    Supports multiple output formats:
    - matplotlib: Uses sklearn.tree.plot_tree
    - graphviz: Uses sklearn.tree.export_graphviz (requires graphviz)
    - plotly: Interactive tree visualization
    
    Args:
        clf: Trained DecisionTreeClassifier instance
        feature_names: List of feature names
        class_names: List of class names (e.g., ['Good', 'Bad'])
        output_format: 'matplotlib', 'graphviz', or 'plotly'
        title: Chart title
        figsize: Figure size
        max_depth: Maximum depth to display (None for full tree)
        return_html: If True, return HTML string
        return_svg: If True, return SVG string (graphviz only)
        
    Returns:
        Figure object, HTML string, or SVG string
    """
    from sklearn.tree import DecisionTreeClassifier
    
    if not isinstance(clf, DecisionTreeClassifier):
        raise TypeError("clf must be a DecisionTreeClassifier instance")
    
    if class_names is None:
        class_names = ['Good', 'Bad']
    
    if output_format == 'matplotlib' and HAS_MATPLOTLIB:
        return _plot_tree_matplotlib(clf, feature_names, class_names, 
                                      title, figsize, max_depth, return_html)
    elif output_format == 'graphviz':
        return _plot_tree_graphviz(clf, feature_names, class_names,
                                    title, max_depth, return_svg)
    elif output_format == 'plotly' and HAS_PLOTLY:
        return _plot_tree_plotly(clf, feature_names, class_names,
                                  title, max_depth, return_html)
    else:
        # Default to matplotlib
        if HAS_MATPLOTLIB:
            return _plot_tree_matplotlib(clf, feature_names, class_names,
                                          title, figsize, max_depth, return_html)
        raise ImportError("No visualization library available")


def _plot_tree_matplotlib(
    clf: Any,
    feature_names: List[str] | None,
    class_names: List[str],
    title: str,
    figsize: Tuple[int, int],
    max_depth: int | None,
    return_html: bool
) -> Any:
    """Create decision tree visualization using matplotlib."""
    from sklearn.tree import plot_tree
    import io
    import base64
    
    _setup_chinese_font()
    
    fig, ax = plt.subplots(figsize=figsize)
    
    plot_tree(
        clf,
        feature_names=feature_names,
        class_names=class_names,
        filled=True,
        rounded=True,
        ax=ax,
        max_depth=max_depth,
        fontsize=10,
        proportion=True
    )
    
    ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
    plt.tight_layout()
    
    if return_html:
        # Convert to base64 image
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        plt.close(fig)
        return f'<img src="data:image/png;base64,{img_base64}" alt="{title}" style="max-width:100%;">'
    
    return fig


def _plot_tree_graphviz(
    clf: Any,
    feature_names: List[str] | None,
    class_names: List[str],
    title: str,
    max_depth: int | None,
    return_svg: bool
) -> Any:
    """Create decision tree visualization using graphviz."""
    from sklearn.tree import export_graphviz
    
    try:
        import graphviz
        HAS_GRAPHVIZ = True
    except ImportError:
        HAS_GRAPHVIZ = False
    
    # Export to DOT format
    dot_data = export_graphviz(
        clf,
        feature_names=feature_names,
        class_names=class_names,
        filled=True,
        rounded=True,
        special_characters=True,
        max_depth=max_depth,
        proportion=True
    )
    
    if not HAS_GRAPHVIZ:
        # Return DOT string if graphviz not installed
        return dot_data
    
    # Create graphviz graph
    graph = graphviz.Source(dot_data)
    
    if return_svg:
        return graph.pipe(format='svg').decode('utf-8')
    
    return graph


def _plot_tree_plotly(
    clf: Any,
    feature_names: List[str] | None,
    class_names: List[str],
    title: str,
    max_depth: int | None,
    return_html: bool
) -> Any:
    """Create interactive decision tree visualization using Plotly."""
    tree_obj = clf.tree_
    
    # Build tree structure
    n_nodes = tree_obj.node_count
    children_left = tree_obj.children_left
    children_right = tree_obj.children_right
    feature = tree_obj.feature
    threshold = tree_obj.threshold
    value = tree_obj.value
    
    # Calculate node positions using BFS
    node_positions = {}
    node_labels = {}
    node_colors = []
    
    # BFS to assign positions
    queue = [(0, 0, 0)]  # (node_id, depth, horizontal_position)
    depth_counts = {}
    
    while queue:
        node_id, depth, h_pos = queue.pop(0)
        
        if max_depth is not None and depth > max_depth:
            continue
        
        if depth not in depth_counts:
            depth_counts[depth] = 0
        
        node_positions[node_id] = (depth_counts[depth], -depth)
        depth_counts[depth] += 1
        
        # Create label
        if children_left[node_id] == -1:  # Leaf node
            samples = int(value[node_id].sum())
            class_idx = int(np.argmax(value[node_id]))
            class_name = class_names[class_idx] if class_idx < len(class_names) else f"Class {class_idx}"
            bad_rate = value[node_id][0][1] / value[node_id].sum() if value[node_id].sum() > 0 else 0
            node_labels[node_id] = f"样本: {samples}<br>坏账率: {bad_rate:.2%}<br>类别: {class_name}"
            node_colors.append(bad_rate)
        else:
            feat_name = feature_names[feature[node_id]] if feature_names else f"X[{feature[node_id]}]"
            samples = int(value[node_id].sum())
            bad_rate = value[node_id][0][1] / value[node_id].sum() if value[node_id].sum() > 0 else 0
            node_labels[node_id] = f"{feat_name} ≤ {threshold[node_id]:.2f}<br>样本: {samples}<br>坏账率: {bad_rate:.2%}"
            node_colors.append(bad_rate)
            
            # Add children to queue
            if children_left[node_id] != -1:
                queue.append((children_left[node_id], depth + 1, h_pos * 2))
            if children_right[node_id] != -1:
                queue.append((children_right[node_id], depth + 1, h_pos * 2 + 1))
    
    # Create edges
    edge_x = []
    edge_y = []
    
    for node_id in node_positions:
        if children_left[node_id] != -1 and children_left[node_id] in node_positions:
            x0, y0 = node_positions[node_id]
            x1, y1 = node_positions[children_left[node_id]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
        if children_right[node_id] != -1 and children_right[node_id] in node_positions:
            x0, y0 = node_positions[node_id]
            x1, y1 = node_positions[children_right[node_id]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
    
    # Create figure
    fig = go.Figure()
    
    # Add edges
    fig.add_trace(go.Scatter(
        x=edge_x, y=edge_y,
        mode='lines',
        line=dict(width=1, color='#888'),
        hoverinfo='none'
    ))
    
    # Add nodes
    node_x = [pos[0] for pos in node_positions.values()]
    node_y = [pos[1] for pos in node_positions.values()]
    node_text = [node_labels[nid] for nid in node_positions.keys()]
    
    fig.add_trace(go.Scatter(
        x=node_x, y=node_y,
        mode='markers',
        marker=dict(
            size=30,
            color=node_colors,
            colorscale='RdYlGn_r',
            colorbar=dict(title='坏账率'),
            line=dict(width=2, color='#333')
        ),
        text=node_text,
        hoverinfo='text'
    ))
    
    fig.update_layout(
        title=dict(text=title, x=0.5, font=dict(size=16)),
        showlegend=False,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        template='plotly_white',
        hovermode='closest'
    )
    
    if return_html:
        return fig.to_html(include_plotlyjs='cdn', full_html=False)
    return fig


def get_tree_structure_data(
    clf: Any,
    feature_names: List[str] | None = None,
    class_names: List[str] | None = None,
    optimal_rules: List[str] | None = None
) -> Dict[str, Any]:
    """
    Extract decision tree structure as JSON-serializable data.
    
    Args:
        clf: Trained DecisionTreeClassifier
        feature_names: List of feature names
        class_names: List of class names
        optimal_rules: List of optimal rule strings (for marking optimal leaf nodes)
        
    Returns:
        Dictionary with tree structure data for frontend rendering
    """
    import logging
    logger = logging.getLogger(__name__)
    
    from sklearn.tree import DecisionTreeClassifier
    
    if not isinstance(clf, DecisionTreeClassifier):
        raise TypeError("clf must be a DecisionTreeClassifier instance")
    
    if class_names is None:
        class_names = ['Good', 'Bad']
    
    # 构建最优规则集合用于快速匹配
    optimal_rule_set = set(optimal_rules) if optimal_rules else set()
    logger.info(f"[TreeViz] 最优规则数: {len(optimal_rule_set)}")
    if optimal_rule_set:
        # 打印前3条完整的最优规则便于调试
        sample_rules = list(optimal_rule_set)[:3]
        for i, r in enumerate(sample_rules):
            logger.info(f"[TreeViz] 最优规则[{i}]: {r}")
    
    tree_obj = clf.tree_
    
    def normalize_rule(rule: str) -> str:
        """标准化规则字符串以便比较（去除空格差异）"""
        import re
        # 移除多余空格，统一格式
        rule = re.sub(r'\s+', ' ', rule.strip())
        # 统一括号周围的空格
        rule = re.sub(r'\(\s+', '(', rule)
        rule = re.sub(r'\s+\)', ')', rule)
        return rule
    
    def extract_conditions(rule: str) -> set:
        """从规则字符串中提取条件集合（包括带括号和不带括号的情况）"""
        import re
        conditions = set()
        # 匹配带括号的条件: (feature <= value) 或 (feature > value)
        paren_matches = re.findall(r'\(([^)]+)\)', rule)
        for match in paren_matches:
            conditions.add(match.strip())
        # 匹配不带括号的条件: feature <= value 或 feature > value
        if not paren_matches:
            # 按 & 分割
            parts = re.split(r'\s*&\s*', rule)
            for part in parts:
                part = part.strip()
                if part:
                    conditions.add(part)
        return conditions
    
    # 预处理最优规则集（标准化后）
    normalized_optimal_rules = {normalize_rule(r) for r in optimal_rule_set}
    # 预处理最优规则的条件集合（用于策略4）
    optimal_conditions_sets = []
    for r in optimal_rule_set:
        conds = extract_conditions(normalize_rule(r))
        if conds:
            optimal_conditions_sets.append((r, conds))
    
    logger.info(f"[TreeViz] 标准化后规则数: {len(normalized_optimal_rules)}")
    if normalized_optimal_rules:
        sample_normalized = list(normalized_optimal_rules)[:2]
        for i, r in enumerate(sample_normalized):
            logger.info(f"[TreeViz] 标准化规则[{i}]: {r[:100]}...")
    
    # 统计变量
    match_stats = {'total_leaves': 0, 'optimal_matches': 0}
    
    def build_node(node_id: int, path_conditions: List[str] | None = None) -> Dict[str, Any]:
        """Recursively build node structure with rule path tracking."""
        if path_conditions is None:
            path_conditions = []
        
        # 显式转换为 Python bool，避免 numpy.bool_ 被 JSON 序列化为字符串
        is_leaf = bool(tree_obj.children_left[node_id] == -1)
        
        # 使用 n_node_samples 获取真实样本数（不受权重影响）
        samples = int(tree_obj.n_node_samples[node_id])
        
        # tree_.value 存储的是加权样本数，用于计算坏账率（比例）
        # value[node_id][0] = [good_weighted, bad_weighted] 对于二分类
        weighted_values = tree_obj.value[node_id][0]
        total_weighted = weighted_values.sum()
        
        if total_weighted > 0:
            # 使用加权值计算坏账率比例
            bad_rate = weighted_values[1] / total_weighted
            # 根据坏账率和真实样本数估算 bad_count 和 good_count
            bad_count = int(round(samples * bad_rate))
            good_count = samples - bad_count
        else:
            bad_rate = 0
            bad_count = 0
            good_count = samples
        
        node_data = {
            'id': int(node_id),
            'samples': samples,
            'bad_count': bad_count,
            'good_count': good_count,
            'bad_rate': round(bad_rate, 4),
            'is_leaf': is_leaf
        }
        
        if is_leaf:
            match_stats['total_leaves'] += 1
            class_idx = int(np.argmax(tree_obj.value[node_id]))
            node_data['predicted_class'] = class_names[class_idx] if class_idx < len(class_names) else f"Class {class_idx}"
            
            # 构建叶节点对应的规则路径
            if path_conditions:
                rule_path = " & ".join(path_conditions)
                node_data['rule_path'] = rule_path
                
                # 检查是否为最优规则 - 使用多种匹配策略
                normalized_path = normalize_rule(rule_path)
                is_optimal = False
                matched_strategy = None
                
                # 策略1: 精确匹配
                if normalized_path in normalized_optimal_rules:
                    is_optimal = True
                    matched_strategy = "精确匹配"
                
                # 策略2: 子串匹配（某些规则可能是路径的子集或超集）
                if not is_optimal and normalized_optimal_rules:
                    for opt_rule in normalized_optimal_rules:
                        if opt_rule in normalized_path or normalized_path in opt_rule:
                            is_optimal = True
                            matched_strategy = "子串匹配"
                            break
                
                # 策略3: 条件集合匹配（忽略顺序，检查括号内条件是否相同）
                if not is_optimal and normalized_optimal_rules:
                    import re
                    path_conditions_set = set(re.findall(r'\([^)]+\)', normalized_path))
                    for opt_rule in normalized_optimal_rules:
                        opt_conditions_set = set(re.findall(r'\([^)]+\)', opt_rule))
                        if path_conditions_set and opt_conditions_set and path_conditions_set == opt_conditions_set:
                            is_optimal = True
                            matched_strategy = "括号条件集匹配"
                            break
                
                # 策略4: 条件内容匹配（提取条件内容，忽略括号和格式差异）
                if not is_optimal and optimal_conditions_sets:
                    path_conds = extract_conditions(normalized_path)
                    for opt_rule, opt_conds in optimal_conditions_sets:
                        if path_conds and opt_conds and path_conds == opt_conds:
                            is_optimal = True
                            matched_strategy = "条件内容匹配"
                            break
                
                if is_optimal:
                    match_stats['optimal_matches'] += 1
                    logger.debug(f"[TreeViz] {matched_strategy}: {normalized_path[:60]}...")
                else:
                    # 只对前3个未匹配的叶节点打印调试信息
                    if match_stats['total_leaves'] <= 3:
                        path_conds = extract_conditions(normalized_path)
                        logger.info(f"[TreeViz] 未匹配叶节点[{node_id}] rule_path: {normalized_path[:80]}...")
                        logger.info(f"[TreeViz] 未匹配叶节点[{node_id}] 提取的条件: {path_conds}")
                
                node_data['is_optimal'] = is_optimal
            else:
                node_data['rule_path'] = ''
                node_data['is_optimal'] = False
        else:
            feat_idx = tree_obj.feature[node_id]
            feat_name = feature_names[feat_idx] if feature_names else f"X[{feat_idx}]"
            threshold = round(float(tree_obj.threshold[node_id]), 4)
            
            # 格式化阈值（与rule_mining.py中_get_rules_from_tree保持一致）
            if abs(threshold) < 0.0001 and threshold != 0:
                thresh_str = f"{threshold:.6f}"
            else:
                thresh_str = f"{threshold:.4f}".rstrip('0').rstrip('.')
            
            node_data['feature'] = feat_name
            node_data['feature_index'] = int(feat_idx)
            node_data['threshold'] = threshold
            
            # 构建左右子树的条件
            left_condition = f"({feat_name} <= {thresh_str})"
            right_condition = f"({feat_name} > {thresh_str})"
            
            node_data['left'] = build_node(
                tree_obj.children_left[node_id], 
                path_conditions + [left_condition]
            )
            node_data['right'] = build_node(
                tree_obj.children_right[node_id], 
                path_conditions + [right_condition]
            )
        
        return node_data
    
    result = {
        'tree': build_node(0),
        'n_features': int(tree_obj.n_features),
        'n_classes': int(tree_obj.n_classes[0]),
        'max_depth': int(tree_obj.max_depth),
        'n_leaves': int(tree_obj.n_leaves),
        'feature_names': feature_names,
        'class_names': class_names,
        'has_optimal_info': bool(optimal_rules),
        'optimal_match_count': match_stats['optimal_matches']
    }
    
    logger.info(f"[TreeViz] 匹配统计: 总叶节点={match_stats['total_leaves']}, 最优匹配={match_stats['optimal_matches']}")
    
    return result


# =============================================================================
# Complete HTML Report - Redirects to html_report module
# =============================================================================

def generate_rule_mining_report_html(
    results: Dict[str, Any],
    title: str = '规则挖掘报告',
    include_charts: bool = True,
    ai_analysis: Optional[str] = None
) -> str:
    """
    Generate complete HTML report for rule mining results.
    
    .. deprecated::
        This function is deprecated. Use `deepanalyze.analysis.html_report.generate_html_report`
        or `deepanalyze.analysis.html_report.generate_rule_mining_report_html` instead.
    
    This is a backward-compatible wrapper that redirects to the centralized
    html_report module.
    """
    import warnings
    warnings.warn(
        "generate_rule_mining_report_html in rule_mining_viz is deprecated. "
        "Use deepanalyze.analysis.html_report.generate_html_report instead.",
        DeprecationWarning,
        stacklevel=2
    )
    from ..html_report import generate_rule_mining_report_html as _generate_report
    return _generate_report(
        results=results,
        title=title,
        include_charts=include_charts,
        ai_analysis=ai_analysis
    )


# =============================================================================
# Export
# =============================================================================

__all__ = [
    'plot_cumulative_metrics',
    'plot_rule_distribution',
    'plot_rule_comparison',
    'generate_rule_summary_html',
    'generate_rule_mining_report_html',
    'get_chart_data_for_frontend',
    'plot_psi_trend',
    'get_psi_trend_data_for_frontend',
    'plot_decision_tree',
    'get_tree_structure_data',
    'HAS_MATPLOTLIB',
    'HAS_PLOTLY'
]
