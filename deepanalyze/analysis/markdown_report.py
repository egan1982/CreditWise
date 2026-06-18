# -*- coding: utf-8 -*-
# pyright: reportAny=false, reportExplicitAny=false, reportUnknownMemberType=false
# pyright: reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownParameterType=false
# pyright: reportImportCycles=false, reportConstantRedefinition=false, reportMissingTypeArgument=false
# pyright: reportPossiblyUnboundVariable=false, reportPrivateUsage=false, reportDeprecated=false
# pyright: reportUnusedFunction=false, reportUnusedVariable=false, reportUnusedCallResult=false
# pyright: reportUnnecessaryComparison=false, reportUnusedParameter=false, reportUnusedImport=false
# pyright: reportUnnecessaryIsInstance=false, reportUnreachable=false, reportUnknownLambdaType=false
# pyright: reportImplicitRelativeImport=false, reportUnannotatedClassAttribute=false
"""
Markdown Report Generator Module

Provides Markdown report generation for SOP task results.
Uses configuration-driven approach aligned with Excel/Word report generators.

Features:
- Configuration-driven sections from task_result_config.py
- Consistent structure with Word/Excel reports
- Supports rule mining and scorecard development tasks
- GitHub-flavored Markdown tables
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional, TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from deepanalyze.core.task_manager.task_result_config import (
        TaskResultConfig, 
        ReportSectionConfig,
        StageDataSheetConfig
    )


class MarkdownReportGenerator:
    """配置驱动的Markdown报告生成器"""
    
    def __init__(self):
        self.timestamp = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
    
    def generate_report(
        self,
        results: dict[str, Any],
        report_type: Literal['scorecard', 'rule_mining'] = 'rule_mining',
        title: str | None = None,
        ai_analysis: str | None = None,
        config: Optional["TaskResultConfig"] = None
    ) -> str:
        """
        生成Markdown报告
        
        Args:
            results: 任务结果数据
            report_type: 报告类型
            title: 报告标题（可选，默认从config获取）
            ai_analysis: AI分析摘要（可选）
            config: 任务结果配置（用于配置驱动）
            
        Returns:
            Markdown格式的报告内容
        """
        if report_type == 'scorecard':
            return self._generate_scorecard_report(results, title, ai_analysis, config)
        else:
            return self._generate_rule_mining_report(results, title, ai_analysis, config)
    
    def _generate_rule_mining_report(
        self,
        results: dict[str, Any],
        title: str | None = None,
        ai_analysis: str | None = None,
        config: Optional["TaskResultConfig"] = None
    ) -> str:
        """
        生成规则挖掘Markdown报告
        
        结构与Word报告保持一致：
        0. 执行摘要 - AI分析（可选）
        1. 概览 - 样本及预处理信息
        2. 最优规则 - 规则列表
        3. 质量验证 - 验证报告
        4. 稳定性分析 - PSI报告
        5. 金额分析 - 金额维度分析（如果有）
        6. 阶段详情 - 各阶段output_preview（可选）
        """
        report_title = title or (config.report_config.title if config else "规则挖掘分析报告")
        
        md = f"# {report_title}\n\n"
        md += f"> 生成时间: {self.timestamp}\n\n"
        md += "---\n\n"
        
        # 1. 概览（固定章节号，始终显示）
        md += "## 一、概览\n\n"
        
        # 汇总指标卡片（与HTML报告一致）
        optimal_rules = results.get('optimal_rules', results.get('rules', []))
        has_overview_content = False
        # Phase 25: 兼容 DataFrame 和 list 两种类型
        # Pipeline 输出经 JSON 序列化后变为 list of dicts，统一转为 DataFrame
        if isinstance(optimal_rules, list) and optimal_rules:
            optimal_rules = pd.DataFrame(optimal_rules)
        if isinstance(optimal_rules, pd.DataFrame) and not optimal_rules.empty:
            n_rules = len(optimal_rules)
            last_rule = optimal_rules.iloc[-1].to_dict()
            final_recall = last_rule.get('cumulative_recall', last_rule.get('cum_recall', last_rule.get('dev_cum_recall', 0)))
            final_hit_rate = last_rule.get('cumulative_hit_rate', last_rule.get('cum_hit_rate', last_rule.get('dev_cum_hit_rate', 0)))
            final_lift = last_rule.get('cumulative_lift', last_rule.get('cum_lift', last_rule.get('dev_cum_lift', last_rule.get('lift', 0))))
            
            # Rating helpers
            def _r(r): return '优秀' if r >= 0.30 else '良好' if r >= 0.20 else '一般' if r >= 0.10 else '偏低'
            def _h(h): return '精确' if h <= 0.10 else '良好' if h <= 0.15 else '可接受' if h <= 0.25 else '过高'
            def _l(l): return '极强' if l >= 4.0 else '强' if l >= 3.0 else '中等' if l >= 2.0 else '偏弱'
            
            md += "| 指标 | 值 | 评级 |\n"
            md += "|------|-----|:---:|\n"
            md += f"| 最优规则数 | {n_rules} | — |\n"
            md += f"| 累计召回率 | {final_recall*100:.1f}% | {_r(final_recall)} |\n"
            md += f"| 累计命中率 | {final_hit_rate*100:.1f}% | {_h(final_hit_rate)} |\n"
            md += f"| 累计提升倍数 | {final_lift:.2f}x | {_l(final_lift)} |\n"
            md += "\n"
            has_overview_content = True
        
        # 基本指标（如果存在preprocessing_info）
        preprocessing_info = results.get('preprocessing_info', {})
        if preprocessing_info:
            md += self._format_preprocessing_info(preprocessing_info)
            has_overview_content = True
        
        # AI整体分析（放在基本指标下方，无子标题）
        if ai_analysis and ai_analysis.strip():
            md += self._format_ai_analysis(ai_analysis)
            md += "\n"
            has_overview_content = True
        
        if not has_overview_content:
            md += "*暂无数据*\n\n"
        
        # 2. 样本及特征（固定章节号，始终显示）
        md += "## 二、样本及特征\n\n"
        stages = results.get('stages')
        if stages:
            sample_features_md = self._format_sample_features(stages)
            if sample_features_md:
                md += sample_features_md
            else:
                md += "*暂无数据*\n\n"
        else:
            md += "*暂无数据*\n\n"
        
        # 3. 最优规则（固定章节号，始终显示）
        md += "## 三、最优规则\n\n"
        optimal_rules = results.get('optimal_rules', results.get('rules', []))
        if isinstance(optimal_rules, list) and optimal_rules:
            optimal_rules = pd.DataFrame(optimal_rules)
        if isinstance(optimal_rules, pd.DataFrame) and not optimal_rules.empty:
            md += self._format_rules_table(optimal_rules, max_rules=30)
        else:
            md += "*暂无数据*\n\n"
        
        # 4. 规则筛选流程（整合原第四、五部分）
        md += "## 四、规则筛选流程\n\n"
        md += self._format_rule_filtering_flow(results, stages)
        
        # 5. 质量验证（固定章节号，始终显示）
        md += "## 五、质量验证\n\n"
        validation_report = results.get('validation_report')
        if validation_report:
            md += self._format_validation_report(validation_report)
        else:
            md += "*暂无数据*\n\n"
        
        # 6. 稳定性分析（固定章节号，始终显示）
        md += "## 六、稳定性分析 (PSI)\n\n"
        psi_report = results.get('psi_report')
        if psi_report and isinstance(psi_report, list) and len(psi_report) > 0:
            md += self._format_psi_report(psi_report)
        else:
            md += "*暂无数据*\n\n"
        
        # 7. 附加分析（固定章节号，始终显示）
        md += "## 七、附加分析\n\n"
        amount_analysis = results.get('amount_analysis')
        prior_analysis = results.get('prior_analysis')
        
        if (amount_analysis and isinstance(amount_analysis, dict)) or (prior_analysis and isinstance(prior_analysis, dict)):
            md += self._format_advanced_analysis(amount_analysis, prior_analysis)
        else:
            md += "*暂无数据*\n\n"
        
        # 注：移除"阶段执行详情"部分，与HTML/Word报告保持一致
        
        # 2026-02-10: 移除页脚
        
        return md
    
    def _generate_scorecard_report(
        self,
        results: dict[str, Any],
        title: str | None = None,
        ai_analysis: str | None = None,
        config: Optional["TaskResultConfig"] = None
    ) -> str:
        """
        生成评分卡开发Markdown报告
        
        章节结构与前端 Tab 保持一致（2026-02-09 重构）：
        一、概览（汇总指标 + AI分析）
        二、样本与特征（对应 Tab: sample-data）
        三、评估图表（对应 Tab: charts）- Markdown使用数据表格
        四、评分卡明细（对应 Tab: scorecard）
        五、变量筛选（对应 Tab: selection）
        六、模型系数（对应 Tab: statistics）
        """
        report_title = title or (config.report_config.title if config else "评分卡开发报告")
        
        md = f"# {report_title}\n\n"
        md += f"> 生成时间: {self.timestamp}\n\n"
        md += "---\n\n"
        
        section_num = 1
        
        # ==========================================================================
        # 一、概览（新增，与规则挖掘一致）
        # 2026-02-10: 优化数据集指标对比表，增加回退数据源
        # ==========================================================================
        md += f"## {section_num}. 概览\n\n"
        
        # 汇总指标表
        metrics = results.get('metrics', {})
        multi_dataset_metrics = results.get('multi_dataset_metrics', {})
        
        # 提前获取 stages 数据，用于数据集指标对比的回退
        stages = results.get('stages', {})
        data_loading = stages.get('data_loading', {}) if stages else {}
        data_loading_preview = data_loading.get('output_preview', {}) if isinstance(data_loading, dict) else {}
        split_info = data_loading_preview.get('split_info', {})
        
        if metrics:
            # 安全获取指标值，处理 None 情况
            ks_val = metrics.get('ks')
            auc_val = metrics.get('auc')
            gini_val = metrics.get('gini')
            
            # 🔧 PSI 从 psi_result 获取（与前端/HTML报告一致），如果没有则回退到 metrics.psi
            psi_result = results.get('psi_result', {})
            if psi_result and isinstance(psi_result, dict) and 'value' in psi_result:
                psi_val = psi_result.get('value')
                # 🔧 获取PSI对比信息（如"训练集 vs OOT"或"训练集 vs 测试集"）
                psi_comparison = psi_result.get('comparison', '')
            else:
                psi_val = metrics.get('psi')
                psi_comparison = ''
            
            # 动态获取指标数据来源标签（与前端一致：优先OOT）
            metrics_source = metrics.get('source', 'test')
            source_label = 'OOT验证集' if metrics_source == 'oot' else '测试集'
            
            # 🔧 PSI标签：如果有comparison信息，显示具体的对比数据集
            if psi_comparison:
                psi_label = f"PSI ({psi_comparison})"
            else:
                psi_label = "PSI (稳定性)"
            
            md += "### 汇总指标\n\n"
            md += "| 指标 | 值 |\n"
            md += "|------|----|\n"
            md += f"| KS ({source_label}) | {ks_val * 100:.2f}% |\n" if isinstance(ks_val, (int, float)) else f"| KS ({source_label}) | - |\n"
            md += f"| AUC ({source_label}) | {auc_val:.4f} |\n" if isinstance(auc_val, (int, float)) else f"| AUC ({source_label}) | - |\n"
            md += f"| Gini系数 ({source_label}) | {gini_val * 100:.2f}% |\n" if isinstance(gini_val, (int, float)) else f"| Gini系数 ({source_label}) | - |\n"
            md += f"| {psi_label} | {psi_val:.4f} |\n" if isinstance(psi_val, (int, float)) else f"| {psi_label} | - |\n"
            md += "\n"
        
        # 数据集指标对比（与HTML/前端对齐，使用多级回退数据源）
        # 2026-02-10: 修复训练集指标回退逻辑，始终显示OOT行
        md += "### 数据集指标对比\n\n"
        md += "| 数据集 | 样本数 | 坏账率 | KS | AUC | Gini |\n"
        md += "|--------|--------|--------|-----|-----|------|\n"
        
        # 训练集（回退逻辑与HTML报告对齐：multi_dataset_metrics.train → metrics.train_* → metrics.*）
        train_metrics = multi_dataset_metrics.get('train', {}) if multi_dataset_metrics else {}
        train_samples = split_info.get('train') or train_metrics.get('n_samples') or train_metrics.get('samples') or '-'
        train_bad_rate = train_metrics.get('bad_rate') or split_info.get('train_target_rate')
        # KS/AUC/Gini：先从 train_metrics 获取，再从 metrics 获取（训练集专用字段），最后从 metrics 通用字段获取
        train_ks = train_metrics.get('ks') or metrics.get('train_ks') or metrics.get('ks')
        train_auc = train_metrics.get('auc') or metrics.get('train_auc') or metrics.get('auc')
        train_gini = train_metrics.get('gini') or metrics.get('gini')
        
        train_samples_str = f"{train_samples:,}" if isinstance(train_samples, int) else str(train_samples)
        # 🔧 修复：bad_rate可能是百分比形式(>1)或小数形式(<=1)，需要智能处理
        if isinstance(train_bad_rate, (int, float)):
            train_bad_rate_str = f"{train_bad_rate:.2f}%" if train_bad_rate > 1 else f"{train_bad_rate * 100:.2f}%"
        else:
            train_bad_rate_str = "-"
        train_ks_str = f"{train_ks * 100:.2f}%" if isinstance(train_ks, (int, float)) else "-"
        train_auc_str = f"{train_auc:.4f}" if isinstance(train_auc, (int, float)) else "-"
        train_gini_str = f"{train_gini * 100:.2f}%" if isinstance(train_gini, (int, float)) else "-"
        md += f"| 训练集 | {train_samples_str} | {train_bad_rate_str} | {train_ks_str} | {train_auc_str} | {train_gini_str} |\n"
        
        # 测试集
        test_metrics = multi_dataset_metrics.get('test', {}) if multi_dataset_metrics else {}
        test_samples = split_info.get('test') or test_metrics.get('n_samples') or test_metrics.get('samples') or '-'
        test_bad_rate = test_metrics.get('bad_rate') or split_info.get('test_target_rate')
        test_ks = test_metrics.get('ks') or metrics.get('test_ks') or metrics.get('ks')
        test_auc = test_metrics.get('auc') or metrics.get('test_auc') or metrics.get('auc')
        test_gini = test_metrics.get('gini') or metrics.get('gini')
        
        test_samples_str = f"{test_samples:,}" if isinstance(test_samples, int) else str(test_samples)
        # 🔧 修复：bad_rate可能是百分比形式(>1)或小数形式(<=1)，需要智能处理
        if isinstance(test_bad_rate, (int, float)):
            test_bad_rate_str = f"{test_bad_rate:.2f}%" if test_bad_rate > 1 else f"{test_bad_rate * 100:.2f}%"
        else:
            test_bad_rate_str = "-"
        test_ks_str = f"{test_ks * 100:.2f}%" if isinstance(test_ks, (int, float)) else "-"
        test_auc_str = f"{test_auc:.4f}" if isinstance(test_auc, (int, float)) else "-"
        test_gini_str = f"{test_gini * 100:.2f}%" if isinstance(test_gini, (int, float)) else "-"
        md += f"| 测试集 | {test_samples_str} | {test_bad_rate_str} | {test_ks_str} | {test_auc_str} | {test_gini_str} |\n"
        
        # OOT验证集（始终显示，即使没有划分也显示全 - 的行，与前端对齐）
        oot_metrics = multi_dataset_metrics.get('oot', {}) if multi_dataset_metrics else {}
        oot_samples = split_info.get('oot') or oot_metrics.get('n_samples') or oot_metrics.get('samples')
        oot_bad_rate = oot_metrics.get('bad_rate') or split_info.get('oot_target_rate')
        oot_ks = oot_metrics.get('ks')
        oot_auc = oot_metrics.get('auc')
        oot_gini = oot_metrics.get('gini')
        
        oot_samples_str = f"{oot_samples:,}" if isinstance(oot_samples, int) else (str(oot_samples) if oot_samples else "-")
        # 🔧 修复：bad_rate可能是百分比形式(>1)或小数形式(<=1)，需要智能处理
        if isinstance(oot_bad_rate, (int, float)):
            oot_bad_rate_str = f"{oot_bad_rate:.2f}%" if oot_bad_rate > 1 else f"{oot_bad_rate * 100:.2f}%"
        else:
            oot_bad_rate_str = "-"
        oot_ks_str = f"{oot_ks * 100:.2f}%" if isinstance(oot_ks, (int, float)) else "-"
        oot_auc_str = f"{oot_auc:.4f}" if isinstance(oot_auc, (int, float)) else "-"
        oot_gini_str = f"{oot_gini * 100:.2f}%" if isinstance(oot_gini, (int, float)) else "-"
        md += f"| OOT验证集 | {oot_samples_str} | {oot_bad_rate_str} | {oot_ks_str} | {oot_auc_str} | {oot_gini_str} |\n"
        
        md += "\n"
        
        # AI 分析
        if ai_analysis and ai_analysis.strip():
            md += "### AI 整体分析\n\n"
            md += self._format_ai_analysis(ai_analysis)
        
        section_num += 1
        
        # ==========================================================================
        # 二、样本与特征（对应 Tab: sample-data）
        # ==========================================================================
        # 注：stages 和 data_loading_preview 已在概览部分提前获取
        
        if data_loading_preview or results.get('selected_features'):
            md += f"## {section_num}. 样本与特征\n\n"
            
            # 样本概览（与前端Tab一致：列表形式包含数据集信息）
            total_rows = data_loading_preview.get('rows', results.get('total_samples'))
            target_rate = data_loading_preview.get('target_rate', results.get('bad_rate'))
            split_info = data_loading_preview.get('split_info', {})
            
            md += "### 样本概览\n\n"
            md += "| 指标 | 值 |\n"
            md += "|------|----|\n"
            md += f"| 总样本数 | {total_rows:,} |\n" if isinstance(total_rows, int) else f"| 总样本数 | {total_rows} |\n"
            if target_rate is not None and isinstance(target_rate, (int, float)):
                md += f"| 总体坏账率 | {target_rate * 100:.2f}% |\n"
            
            # 🔧 添加训练集、测试集、OOT验证集信息（与前端一致）
            if split_info:
                if split_info.get('train'):
                    train_count = split_info.get('train', 0)
                    train_rate = split_info.get('train_target_rate')
                    train_rate_str = f"{train_rate * 100:.2f}%" if isinstance(train_rate, (int, float)) else "-"
                    md += f"| 训练集 | {train_count:,} (坏账率: {train_rate_str}) |\n"
                
                if split_info.get('test'):
                    test_count = split_info.get('test', 0)
                    test_rate = split_info.get('test_target_rate')
                    test_rate_str = f"{test_rate * 100:.2f}%" if isinstance(test_rate, (int, float)) else "-"
                    md += f"| 测试集 | {test_count:,} (坏账率: {test_rate_str}) |\n"
                
                # OOT验证集始终显示（与前端一致）
                oot_count = split_info.get('oot', 0)
                if oot_count and oot_count > 0:
                    oot_rate = split_info.get('oot_target_rate')
                    oot_rate_str = f"{oot_rate * 100:.2f}%" if isinstance(oot_rate, (int, float)) else "-"
                    md += f"| OOT验证集 | {oot_count:,} (坏账率: {oot_rate_str}) |\n"
                else:
                    md += "| OOT验证集 | 未划分 |\n"
            
            md += "\n"
            
            # 时间范围（2026-02-10: 与HTML报告对齐）
            time_range_info = data_loading_preview.get('time_range_info', {})
            if time_range_info:
                time_col = time_range_info.get('column', '')
                time_col_display = f"（{time_col}）" if time_col else ""
                md += f"### 时间范围{time_col_display}\n\n"
                md += "| 数据集 | 起始时间 | 截止时间 |\n"
                md += "|--------|----------|----------|\n"
                
                train_range = time_range_info.get('train', {})
                if train_range:
                    md += f"| 训练集 | {train_range.get('min', '-')} | {train_range.get('max', '-')} |\n"
                
                test_range = time_range_info.get('test', {})
                if test_range:
                    md += f"| 测试集 | {test_range.get('min', '-')} | {test_range.get('max', '-')} |\n"
                
                oot_range = time_range_info.get('oot', {})
                if oot_range:
                    md += f"| OOT验证集 | {oot_range.get('min', '-')} | {oot_range.get('max', '-')} |\n"
                
                md += "\n"
            
            # 特征概览（与前端Tab/ HTML报告对齐：原始特征数、异常值特征数、平均缺失率）
            var_filter_result = data_loading_preview.get('var_filter_result', {})
            original_features = var_filter_result.get('input_features') or data_loading_preview.get('columns') or '-'
            outlier_count = data_loading_preview.get('outlier_count', '-')
            missing_rate = data_loading_preview.get('missing_rate')
            
            md += "### 特征概览\n\n"
            md += "| 指标 | 值 |\n"
            md += "|------|----|"
            md += f"\n| 原始特征数 | {original_features} |"
            md += f"\n| 异常值特征数 | {outlier_count} |"
            if missing_rate is not None:
                md += f"\n| 平均缺失率 | {missing_rate * 100:.1f}% |"
            else:
                md += "\n| 平均缺失率 | - |"
            md += "\n\n"
            
            section_num += 1
        
        # ==========================================================================
        # 三、评估图表（对应 Tab: charts）- 2026-02-10 优化：简化为图表索引
        # ==========================================================================
        # Markdown 不支持图表嵌入，只显示图表索引，引导用户到前端查看
        if metrics or multi_dataset_metrics:
            md += f"## {section_num}. 评估图表\n\n"
            md += '*注：Markdown 格式不支持图表嵌入，以下为各数据集图表索引，请在任务开发结果的「评估图表」Tab中查看*\n\n'
            md += self._format_evaluation_charts_index(results, stages)
            section_num += 1
        
        # ==========================================================================
        # 四、评分卡明细（对应 Tab: scorecard）
        # 2026-02-09: 与前端保持一致，使用 full_scorecard_csv 数据
        # ==========================================================================
        score_scaling = stages.get('score_scaling', {}) if stages else {}
        score_scaling_preview = score_scaling.get('output_preview', {}) if isinstance(score_scaling, dict) else {}
        full_scorecard_csv = score_scaling_preview.get('full_scorecard_csv', [])
        scorecard = results.get('scorecard')
        multi_dataset_chart_data = results.get('multi_dataset_chart_data', {})
        
        if full_scorecard_csv or scorecard:
            md += f"## {section_num}. 评分卡明细\n\n"
            md += self._format_scorecard_details_full(full_scorecard_csv, score_scaling_preview, scorecard, multi_dataset_chart_data)
            section_num += 1
        
        # ==========================================================================
        # 五、变量筛选（对应 Tab: selection）
        # 2026-02-10: 与 HTML 报告对齐，添加特征筛选漏斗
        # ==========================================================================
        iv_table = results.get('iv_table')
        selected_features = results.get('selected_features')
        selection_detail = results.get('selection_detail')
        
        if iv_table is not None or selected_features or selection_detail:
            md += f"## {section_num}. 变量筛选\n\n"
            
            # 5.1 特征筛选漏斗概览（从 stages 获取，使用 scorecard/coefficients 获取最终入模数）
            md += self._format_feature_selection_funnel(stages, selected_features, results)
            
            # 5.2 IV值排行（带状态和淘汰信息）
            if iv_table is not None:
                md += "### IV值排行\n\n"
                md += self._format_iv_table_with_status(iv_table, stages, selected_features)
            
            # 5.3 逐步回归详情
            stepwise_result = None
            if selection_detail:
                stepwise_result = selection_detail.get('stepwise_result', {})
            # 也尝试从 model_training 阶段获取
            if not stepwise_result or not stepwise_result.get('steps'):
                model_training = stages.get('model_training', {}) if stages else {}
                model_training_preview = model_training.get('output_preview', {}) if isinstance(model_training, dict) else {}
                stepwise_result = model_training_preview.get('stepwise_result', {})
            
            if stepwise_result and stepwise_result.get('steps'):
                md += "### 逐步回归过程\n\n"
                md += "| 步骤 | 操作 | 变量 | P值 |\n"
                md += "|------|------|------|-----|\n"
                for step in stepwise_result['steps']:
                    action = '添加' if step.get('action') == 'add' else '移除'
                    feature = step.get('feature', '').replace('_woe', '')
                    pvalue = step.get('pvalue', 0)
                    md += f"| {step.get('iteration', '')} | {action} | {feature} | {pvalue:.6f} |\n"
                md += "\n"
            
            section_num += 1
        
        # ==========================================================================
        # 六、模型系数（对应 Tab: statistics）
        # 2026-02-10: 与 HTML 报告对齐，添加指标卡
        # ==========================================================================
        coefficients = results.get('coefficients')
        model_statistics = results.get('model_statistics')
        
        if coefficients is not None or model_statistics:
            md += f"## {section_num}. 模型系数\n\n"
            
            # 6.1 指标卡（似然比检验、显著变量、系数方向、截距项）
            md += self._format_model_coefficients_summary(coefficients, model_statistics, stages)
            
            # 6.2 模型统计检验（模型拟合指标，与前端Tab对齐）
            if model_statistics:
                md += "### 模型统计检验\n\n"
                md += self._format_model_statistics(model_statistics)
            
            # 6.3 逻辑回归系数表
            if coefficients is not None:
                md += "### 逻辑回归系数\n\n"
                md += self._format_coefficients_enhanced(coefficients, model_statistics)
            
            section_num += 1
        
        # 2026-02-10: 移除页脚
        
        return md
    
    # ==================== 辅助格式化方法 ====================
    
    def _format_ai_analysis(self, ai_analysis: str) -> str:
        """格式化AI分析摘要"""
        # AI分析已经是Markdown格式，直接返回
        return ai_analysis.strip() + "\n\n"
    
    def _format_preprocessing_info(self, info: dict[str, Any]) -> str:
        """格式化预处理信息"""
        md = "| 指标 | 值 |\n"
        md += "|------|----|\n"
        
        info_names = {
            'n_samples': '样本量',
            'n_bad': '坏样本数',
            'base_bad_rate': '基础坏账率',
            'n_rules_generated': '生成规则数',
            'n_features': '特征数量',
        }
        
        for key, label in info_names.items():
            if key in info and info[key] is not None:
                value = info[key]
                if key == 'base_bad_rate' and isinstance(value, (int, float)):
                    md += f"| {label} | {value * 100:.2f}% |\n"
                elif isinstance(value, float):
                    md += f"| {label} | {value:.4f} |\n"
                else:
                    md += f"| {label} | {value} |\n"
        
        md += "\n"
        return md
    
    def _format_rule_filtering_flow(self, results: dict[str, Any], stages: dict[str, Any] | None) -> str:
        """
        格式化规则筛选流程（整合原第四、五部分）
        
        包含：
        - 漏斗概览（规则生成 -> 规则筛选 -> 最优选择）
        - 规则筛选阶段：筛选条件 + 筛选结果
        - 最优选择阶段：选择条件 + 选择结果
        """
        md = ""
        
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
            md += "### 漏斗概览\n\n"
            md += "| 阶段 | 规则数 | 比例 |\n"
            md += "|------|--------|------|\n"
            
            gen_pct = "100%" if generated_count > 0 else "-"
            filter_pct = f"{filtered_count/generated_count*100:.1f}%" if generated_count > 0 else "-"
            optimal_pct = f"{optimal_count/generated_count*100:.1f}%" if generated_count > 0 else "-"
            
            md += f"| 规则生成 | {generated_count} | {gen_pct} |\n"
            md += f"| 规则筛选 | {filtered_count} | {filter_pct} |\n"
            md += f"| 最优选择 | {optimal_count} | {optimal_pct} |\n"
            md += "\n"
        
        # 4.1 规则筛选阶段
        md += "### 4.1 规则筛选阶段\n\n"
        
        filter_criteria = rule_filtering_preview.get('filter_criteria', {})
        filter_summary = rule_filtering_preview.get('filter_summary', {})
        
        if filter_criteria:
            md += "**筛选条件**\n\n"
            min_lift = filter_criteria.get('min_lift')
            max_hit_rate = filter_criteria.get('max_hit_rate')
            md += f"- 最小Lift阈值: {min_lift}\n" if min_lift is not None else "- 最小Lift阈值: 未设置\n"
            md += f"- 最大命中率: {max_hit_rate*100:.1f}%\n\n" if max_hit_rate is not None else "- 最大命中率: 未设置\n\n"
        
        if filter_summary:
            md += "**筛选结果**\n\n"
            md += "| 筛选原因 | 移除数量 |\n"
            md += "|----------|----------|\n"
            md += f"| 单调性校验 | {filter_summary.get('direction_removed', 0)} |\n"
            md += f"| 坏账率为0 | {filter_summary.get('bad_rate_zero_removed', 0)} |\n"
            md += f"| 最小Lift阈值 | {filter_summary.get('lift_removed', 0)} |\n"
            md += f"| 最大命中率 | {filter_summary.get('hit_rate_removed', 0)} |\n"
            md += f"| **总移除** | **{filter_summary.get('total_removed', 0)}** |\n"
            md += "\n"
        else:
            md += "*暂无筛选数据*\n\n"
        
        # 4.2 最优选择阶段
        md += "### 4.2 最优选择阶段\n\n"
        
        if selecting_rules_preview:
            md += "**选择条件**\n\n"
            allow_overlap = selecting_rules_preview.get('allow_overlap', False)
            selection_mode_text = "允许重叠（独立选择）" if allow_overlap else "贪婪算法（不允许重叠）"
            md += f"- 选择模式: {selection_mode_text}\n"
            
            max_hit_rate = selecting_rules_preview.get('max_hit_rate')
            md += f"- 最大命中率（规则集）: {max_hit_rate*100:.1f}%\n" if max_hit_rate is not None else "- 最大命中率（规则集）: 未设置\n"
            
            # 风险目标参数
            risk_targets = selecting_rules_preview.get('risk_targets', {})
            min_recall = risk_targets.get('min_recall_ruleset')
            min_bad_rate = risk_targets.get('min_bad_rate_ruleset')
            target_bad_rate = risk_targets.get('target_bad_rate_ruleset')
            min_lift = risk_targets.get('min_lift_ruleset')
            
            md += f"- 最低召回率目标: {min_recall*100:.1f}%\n" if min_recall is not None else "- 最低召回率目标: 未设置\n"
            md += f"- 最低坏账率目标: {min_bad_rate*100:.1f}%\n" if min_bad_rate is not None else "- 最低坏账率目标: 未设置\n"
            md += f"- 目标坏账率: {target_bad_rate*100:.1f}%\n" if target_bad_rate is not None else "- 目标坏账率: 未设置\n"
            md += f"- 最低提升度目标: {min_lift}\n\n" if min_lift is not None else "- 最低提升度目标: 未设置\n\n"
            
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
            
            md += "**选择结果**\n\n"
            md += "| 放弃原因 | 数量 |\n"
            md += "|----------|------|\n"
            
            total_rejected = 0
            for reason in possible_reasons:
                count = full_reason_distribution[reason]
                md += f"| {reason} | {count} |\n"
                total_rejected += count
            
            md += f"| **总放弃** | **{total_rejected}** |\n"
            md += "\n"
        else:
            md += "*暂无选择数据*\n\n"
        
        return md
    
    def _format_rules_table(self, rules: list, max_rules: int = 30) -> str:
        """格式化规则表格"""
        # FIX-3: 安全的空值检查（兼容 DataFrame 和 list）
        if rules is None or (isinstance(rules, list) and len(rules) == 0):
            return "暂无规则数据\n\n"
        if isinstance(rules, pd.DataFrame):
            if rules.empty:
                return "暂无规则数据\n\n"
            rules = rules.to_dict(orient='records')
        
        md = "| 序号 | 规则条件 | 召回率 | 命中率 | 坏账率 | Lift | 累计召回 |\n"
        md += "|------|----------|--------|--------|--------|------|----------|\n"
        
        for i, rule in enumerate(rules[:max_rules], 1):
            rule_text = str(rule.get('rule', rule.get('condition', '-')))
            # 截断过长的规则
            if len(rule_text) > 60:
                rule_text = rule_text[:57] + "..."
            
            recall = rule.get('recall', 0)
            recall_str = f"{recall * 100:.2f}%" if isinstance(recall, (int, float)) else '-'
            
            hit_rate = rule.get('hit_rate', 0)
            hit_rate_str = f"{hit_rate * 100:.2f}%" if isinstance(hit_rate, (int, float)) else '-'
            
            bad_rate = rule.get('bad_rate', 0)
            bad_rate_str = f"{bad_rate * 100:.2f}%" if isinstance(bad_rate, (int, float)) else '-'
            
            lift = rule.get('lift', 0)
            lift_str = f"{lift:.2f}" if isinstance(lift, (int, float)) else '-'
            
            cum_recall = rule.get('cumulative_recall', rule.get('cum_recall', rule.get('dev_cum_recall', 0)))
            cum_recall_str = f"{cum_recall * 100:.2f}%" if isinstance(cum_recall, (int, float)) else '-'
            
            md += f"| {i} | {rule_text} | {recall_str} | {hit_rate_str} | {bad_rate_str} | {lift_str} | {cum_recall_str} |\n"
        
        if len(rules) > max_rules:
            md += f"\n*（仅显示前{max_rules}条规则，共{len(rules)}条）*\n"
        
        md += "\n"
        return md
    
    def _format_filtered_rules_table(self, rules: list, max_rules: int = 30) -> str:
        """格式化被过滤规则表格（包含过滤原因）"""
        # FIX-3: 安全的空值检查（兼容 DataFrame 和 list）
        if rules is None or (isinstance(rules, list) and len(rules) == 0):
            return "暂无被过滤的规则\n\n"
        if isinstance(rules, pd.DataFrame):
            if rules.empty:
                return "暂无被过滤的规则\n\n"
            rules = rules.to_dict(orient='records')
        
        md = "| 序号 | 规则 | 命中率 | 坏账率 | Lift | 召回率 | 过滤原因 |\n"
        md += "|------|------|--------|--------|------|--------|----------|\n"
        
        for i, rule in enumerate(rules[:max_rules], 1):
            rule_text = str(rule.get('rule', '-'))
            if len(rule_text) > 50:
                rule_text = rule_text[:47] + "..."
            
            hit_rate = rule.get('hit_rate')
            hit_rate_str = f"{hit_rate * 100:.2f}%" if isinstance(hit_rate, (int, float)) and hit_rate is not None else '-'
            
            bad_rate = rule.get('bad_rate')
            bad_rate_str = f"{bad_rate * 100:.2f}%" if isinstance(bad_rate, (int, float)) and bad_rate is not None else '-'
            
            lift = rule.get('lift')
            lift_str = f"{lift:.2f}" if isinstance(lift, (int, float)) and lift is not None else '-'
            
            recall = rule.get('recall')
            recall_str = f"{recall * 100:.2f}%" if isinstance(recall, (int, float)) and recall is not None else '-'
            
            filter_reason = rule.get('filter_reason', '未知原因')
            # 截断过长的原因
            if len(filter_reason) > 40:
                filter_reason = filter_reason[:37] + "..."
            
            md += f"| {i} | {rule_text} | {hit_rate_str} | {bad_rate_str} | {lift_str} | {recall_str} | {filter_reason} |\n"
        
        if len(rules) > max_rules:
            md += f"\n*（仅显示前{max_rules}条，共{len(rules)}条被过滤规则）*\n"
        
        md += "\n"
        return md
    
    def _format_validation_report(self, validation_report: Any) -> str:
        """格式化质量验证报告 - 优化版"""
        md = ""
        
        if not isinstance(validation_report, dict):
            return "验证报告数据格式异常\n\n"
        
        # 状态映射
        status_labels = {
            'excellent': '🟢 优秀',
            'good': '🔵 良好',
            'acceptable': '🟡 合格',
            'warning': '🟠 警告',
            'warning_low': '🟡 偏低',
            'warning_high': '🟡 偏高',
            'error': '🔴 异常',
            'ok': '🟢 正常',
        }
        
        # 综合评分
        quality_score = validation_report.get('quality_score', 0)
        md += f"**综合质量评分: {quality_score:.1f} / 100**\n\n"
        
        # 各维度得分
        score_breakdown = validation_report.get('score_breakdown', {})
        if score_breakdown:
            dimension_names = {
                'discrimination': '区分度',
                'recall': '召回率',
                'coverage': '覆盖率',
                'independence': '独立性',
                'complexity': '复杂度',
            }
            scores = [f"{dimension_names.get(k, k)}: {v:.1f}" for k, v in score_breakdown.items() if k in dimension_names]
            if scores:
                md += "得分明细: " + " | ".join(scores) + "\n\n"
        
        # 评估详情表格
        md += "| 评估维度 | 核心指标 | 状态 | 说明 |\n"
        md += "|----------|----------|------|------|\n"
        
        # 区分度
        disc = validation_report.get('discrimination_report', {})
        if disc and isinstance(disc, dict):
            status = disc.get('status', 'error')
            avg_lift = disc.get('avg_lift', 0)
            min_lift = disc.get('min_lift', 0)
            max_lift = disc.get('max_lift', 0)
            md += f"| 📊 区分度 | 平均Lift: {avg_lift} | {status_labels.get(status, status)} | 范围[{min_lift}, {max_lift}] |\n"
        
        # 召回率
        recall = validation_report.get('recall_report', {})
        if recall and isinstance(recall, dict):
            status = recall.get('status', 'error')
            cumulative_recall = recall.get('cumulative_recall', 0)
            md += f"| 🎯 召回率 | 累计召回: {cumulative_recall*100:.2f}% | {status_labels.get(status, status)} | 对坏客户的捕获能力 |\n"
        
        # 覆盖率
        coverage = validation_report.get('coverage_report', {})
        if coverage and isinstance(coverage, dict):
            status = coverage.get('status', 'error')
            total_coverage = coverage.get('total_coverage', 0)
            md += f"| 📈 覆盖率 | 总覆盖率: {total_coverage*100:.2f}% | {status_labels.get(status, status)} | 规则命中样本比例 |\n"
        
        # 重叠度
        overlap = validation_report.get('overlap_report', {})
        if overlap and isinstance(overlap, dict):
            status = overlap.get('status', 'ok')
            avg_overlap = overlap.get('avg_overlap', 0)
            desc = "无重叠" if avg_overlap == 0 else f"平均重叠{avg_overlap*100:.1f}%"
            md += f"| 🔗 重叠度 | 平均重叠: {avg_overlap*100:.1f}% | {status_labels.get(status, status)} | {desc} |\n"
        
        # 冗余度
        redundancy = validation_report.get('redundancy_report', {})
        if redundancy and isinstance(redundancy, dict):
            status = redundancy.get('status', 'ok')
            redundant_count = redundancy.get('redundant_count', 0)
            desc = "无冗余" if redundant_count == 0 else f"{redundant_count}对冗余规则"
            md += f"| ♻️ 冗余度 | 冗余规则: {redundant_count}对 | {status_labels.get(status, status)} | {desc} |\n"
        
        # 复杂度
        complexity = validation_report.get('complexity_report', {})
        if complexity and isinstance(complexity, dict):
            status = complexity.get('status', 'ok')
            avg_complexity = complexity.get('avg_complexity', 0)
            max_complexity = complexity.get('max_complexity', 0)
            md += f"| ⚙️ 复杂度 | 平均条件数: {avg_complexity:.1f} | {status_labels.get(status, status)} | 最大{max_complexity}个 |\n"
        
        md += "\n"
        
        # 警告信息
        warnings = validation_report.get('warnings', [])
        if warnings:
            md += "**💡 优化建议:**\n\n"
            for warning in warnings[:5]:
                md += f"- {warning}\n"
            md += "\n"
        elif quality_score >= 80:
            md += "> ✅ 规则集质量优秀，各项指标均达标\n\n"
        
        return md
    
    def _format_psi_report(self, psi_report: list) -> str:
        """格式化PSI稳定性报告"""
        if not psi_report:
            return "暂无PSI数据\n\n"
        
        md = "| 序号 | 规则 | PSI值 | 稳定性 |\n"
        md += "|------|------|-------|--------|\n"
        
        for i, item in enumerate(psi_report[:20], 1):
            rule_text = str(item.get('rule', item.get('rule_id', '-')))
            if len(rule_text) > 40:
                rule_text = rule_text[:37] + "..."
            
            psi_value = item.get('psi', 0)
            psi_str = f"{psi_value:.4f}" if isinstance(psi_value, (int, float)) else '-'
            
            # 判断稳定性
            if isinstance(psi_value, (int, float)):
                if psi_value < 0.1:
                    stability = "✅ 稳定"
                elif psi_value < 0.25:
                    stability = "⚠️ 轻微变化"
                else:
                    stability = "❌ 显著变化"
            else:
                stability = "-"
            
            md += f"| {i} | {rule_text} | {psi_str} | {stability} |\n"
        
        if len(psi_report) > 20:
            md += f"\n*（仅显示前20条，共{len(psi_report)}条）*\n"
        
        md += "\n**PSI指标说明：**\n"
        md += "- PSI < 0.1：规则稳定，可直接使用\n"
        md += "- 0.1 ≤ PSI < 0.25：规则有轻微变化，需关注\n"
        md += "- PSI ≥ 0.25：规则显著变化，建议重新评估\n\n"
        
        return md
    
    def _format_sample_features(self, stages: dict[str, Any]) -> str:
        """
        格式化样本集特征信息（从stages获取）
        
        镜像前端SampleFeaturePanel组件的内容
        """
        import logging
        logger = logging.getLogger(__name__)
        
        if not stages:
            logger.warning("[MD Report] _format_sample_features: stages is empty")
            return ""
        
        logger.info(f"[MD Report] _format_sample_features: stages keys = {list(stages.keys())}")
        
        # 获取preprocessing阶段数据
        preprocessing_stage = stages.get('preprocessing', {})
        preprocessing_data = preprocessing_stage.get('output_preview', {}) if isinstance(preprocessing_stage, dict) else {}
        
        if not preprocessing_data:
            logger.warning("[MD Report] _format_sample_features: preprocessing_data is empty")
            return ""
        
        # 获取feature_engineering阶段数据（可选）
        fe_stage = stages.get('feature_engineering', {})
        fe_data = fe_stage.get('output_preview', {}) if isinstance(fe_stage, dict) else {}
        
        # 放宽条件：只要有 before_count 或 after_count 或 selection_flow，就认为有特征工程数据
        # 即使 skipped=True，也可能有部分数据可展示
        has_feature_engineering = bool(fe_data) and (
            fe_data.get('before_count') is not None or 
            fe_data.get('after_count') is not None or 
            fe_data.get('selection_flow')
        )
        
        logger.info(f"[MD Report] feature_engineering stage: fe_stage keys = {list(fe_stage.keys()) if isinstance(fe_stage, dict) else 'not a dict'}")
        logger.info(f"[MD Report] feature_engineering output_preview: fe_data keys = {list(fe_data.keys()) if isinstance(fe_data, dict) else 'not a dict'}")
        logger.info(f"[MD Report] feature_engineering.before_count = {fe_data.get('before_count')}")
        logger.info(f"[MD Report] feature_engineering.after_count = {fe_data.get('after_count')}")
        logger.info(f"[MD Report] feature_engineering.selection_flow = {fe_data.get('selection_flow')}")
        logger.info(f"[MD Report] feature_engineering.skipped = {fe_data.get('skipped')}")
        logger.info(f"[MD Report] has_feature_engineering = {has_feature_engineering}")
        
        md = ""
        
        # 2026-02-10: 精简内容，与前端Tab对齐
        # ============================================================
        # 样本概览（与前端一致）
        # ============================================================
        md += "### 样本概览\n\n"
        md += "| 指标 | 值 |\n"
        md += "|------|----|\n"
        
        rows = preprocessing_data.get('rows')
        if rows is not None:
            md += f"| 总样本数 | {rows:,} |\n"
        
        target_rate = preprocessing_data.get('target_rate')
        if target_rate is not None:
            md += f"| 总体坏账率 | {target_rate*100:.2f}% |\n"
        
        split_info = preprocessing_data.get('split_info', {})
        if split_info:
            train_count = split_info.get('train')
            train_rate = split_info.get('train_target_rate')
            if train_count is not None:
                rate_str = f" (坏账率: {train_rate*100:.2f}%)" if train_rate else ""
                md += f"| 训练集 | {train_count:,}{rate_str} |\n"
            
            test_count = split_info.get('test')
            test_rate = split_info.get('test_target_rate')
            if test_count is not None:
                rate_str = f" (坏账率: {test_rate*100:.2f}%)" if test_rate else ""
                md += f"| 测试集 | {test_count:,}{rate_str} |\n"
        
        md += "\n"
        
        # ============================================================
        # 时间范围（与前端一致，新增）
        # ============================================================
        time_range_info = preprocessing_data.get('time_range_info', {})
        if time_range_info:
            time_col = time_range_info.get('column', '')
            time_col_display = f"（{time_col}）" if time_col else ""
            
            md += f"### 时间范围{time_col_display}\n\n"
            md += "| 数据集 | 起始时间 | 截止时间 |\n"
            md += "|--------|----------|----------|\n"
            
            train_range = time_range_info.get('train', {})
            if train_range:
                md += f"| 训练集 | {train_range.get('min', '-')} | {train_range.get('max', '-')} |\n"
            
            test_range = time_range_info.get('test', {})
            if test_range:
                md += f"| 测试集 | {test_range.get('min', '-')} | {test_range.get('max', '-')} |\n"
            
            oot_range = time_range_info.get('oot', {})
            if oot_range and oot_range.get('min'):
                md += f"| OOT验证集 | {oot_range.get('min', '-')} | {oot_range.get('max', '-')} |\n"
            
            md += "\n"
        
        # ============================================================
        # 特征概览（与前端一致：原始特征数、筛选后特征、平均缺失率）
        # ============================================================
        md += "### 特征概览\n\n"
        md += "| 指标 | 值 |\n"
        md += "|------|----|\n"
        
        feature_count = preprocessing_data.get('feature_count')
        if feature_count is not None:
            md += f"| 原始特征数 | {feature_count} |\n"
        
        # 筛选后特征数
        if has_feature_engineering and fe_data.get('after_count') is not None:
            md += f"| 筛选后特征 | {fe_data['after_count']} |\n"
        
        missing_rate = preprocessing_data.get('missing_rate')
        if missing_rate is not None:
            md += f"| 平均缺失率 | {missing_rate*100:.1f}% |\n"
        
        md += "\n"
        
        # ============================================================
        # 特征变化流程（与前端一致：初始 → 缺失率筛选 → One-Hot后 → IV筛选）
        # ============================================================
        if has_feature_engineering:
            before_count = fe_data.get('before_count')
            after_count = fe_data.get('after_count')
            
            # 优先使用 selection_flow（规则挖掘任务使用此格式）
            selection_flow = fe_data.get('selection_flow', [])
            
            md += "### 特征变化流程\n\n"
            
            steps = []
            
            if selection_flow:
                # 使用 selection_flow 格式（规则挖掘任务）
                for step in selection_flow:
                    step_name = step.get('step', '')
                    step_count = step.get('count', 0)
                    step_removed = step.get('removed', 0)
                    step_added = step.get('added', 0)
                    
                    diff_str = ''
                    if step_removed > 0:
                        diff_str += f" (-{step_removed})"
                    if step_added > 0:
                        diff_str += f" (+{step_added})"
                    
                    steps.append(f"**{step_count}**{diff_str} ({step_name})")
            else:
                # 使用旧格式（评分卡任务兼容）
                var_filter = fe_data.get('var_filter_result', {})
                onehot_info = fe_data.get('onehot_info', {})
                
                # 初始特征
                initial_count = feature_count or before_count
                if initial_count:
                    steps.append(f"**{initial_count}** (初始)")
                
                # 缺失率筛选后（如有）
                missing_filtered = var_filter.get('after_missing_filter') or before_count
                if missing_filtered and missing_filtered != initial_count:
                    steps.append(f"**{missing_filtered}** (缺失率筛选)")
                
                # One-Hot后（如有）
                onehot_after = onehot_info.get('after_count')
                if onehot_after:
                    onehot_before = onehot_info.get('before_count', 0)
                    diff = onehot_after - onehot_before if onehot_before else 0
                    diff_str = f" (+{diff})" if diff > 0 else ""
                    steps.append(f"**{onehot_after}**{diff_str} (One-Hot后)")
                
                # IV筛选后
                if after_count is not None:
                    base_count = onehot_after or before_count or initial_count or 0
                    removed = base_count - after_count
                    removed_str = f" (-{removed})" if removed > 0 else ""
                    steps.append(f"**{after_count}**{removed_str} (IV筛选)")
            
            if steps:
                md += " → ".join(steps) + "\n\n"
        
        return md
    
    def _format_amount_analysis(self, amount_analysis: dict) -> str:
        """格式化金额分析（FIX-5: 匹配 FIX-1 扁平化后的结构）"""
        md = ""
        
        # 汇总指标表
        md += "| 指标 | 值 |\n"
        md += "|------|----|\n"
        
        total_amount = amount_analysis.get('total_amount')
        total_bad_amount = amount_analysis.get('total_bad_amount')
        overall_bad_rate = amount_analysis.get('overall_amount_bad_rate')
        cumulative = amount_analysis.get('cumulative', {})
        
        if total_amount is not None:
            md += f"| 总金额 | {total_amount:,.2f} |\n"
        if total_bad_amount is not None:
            md += f"| 总坏账金额 | {total_bad_amount:,.2f} |\n"
        if overall_bad_rate is not None:
            md += f"| 样本金额坏账率 | {overall_bad_rate * 100:.2f}% |\n"
        if cumulative.get('cum_hit_amount') is not None:
            md += f"| 累计命中金额 | {cumulative['cum_hit_amount']:,.2f} |\n"
        if cumulative.get('amount_recall') is not None:
            md += f"| 金额累计召回率 | {cumulative['amount_recall'] * 100:.2f}% |\n"
        if cumulative.get('cum_amount_lift') is not None:
            md += f"| 金额累计提升度 | {cumulative['cum_amount_lift']:.2f}x |\n"
        md += "\n"
        
        # 规则金额明细
        rules_amount = amount_analysis.get('rules_amount', [])
        if rules_amount:
            md += "**规则金额明细**\n\n"
            md += "| 规则 | 命中金额 | 金额占比 | 坏账金额 | 金额坏账率 | 金额Lift |\n"
            md += "|------|----------|----------|----------|------------|----------|\n"
            for r in rules_amount[:20]:
                rule_text = str(r.get('rule', ''))[:40]
                hit_amt = r.get('hit_amount', 0)
                hit_pct = r.get('hit_amount_pct', 0)
                bad_amt = r.get('bad_amount', 0)
                bad_rate = r.get('amount_bad_rate', 0)
                lift = r.get('amount_lift', 0)
                md += f"| {rule_text} | {hit_amt:,.2f} | {hit_pct*100:.2f}% | {bad_amt:,.2f} | {bad_rate*100:.2f}% | {lift:.2f} |\n"
            # Cumulative row
            cum = amount_analysis.get('cumulative', {})
            if cum:
                cum_hit = cum.get('cum_hit_amount', 0)
                total_amt = amount_analysis.get('total_amount', 1) or 1
                cum_hit_pct = cum_hit / total_amt if total_amt > 0 else 0
                cum_bad = cum.get('cum_bad_amount', 0)
                recall = cum.get('amount_recall', 0)
                md += f"| **累计** | **{cum_hit:,.2f}** | **{cum_hit_pct*100:.2f}%** | **{cum_bad:,.2f}** | **{recall*100:.2f}%** | - |\n"
            md += "\n"
        
        return md
    
    def _format_advanced_analysis(self, amount_analysis: Optional[dict], prior_analysis: Optional[dict]) -> str:
        """格式化附加分析（金额维度分析 + 先验规则分析）"""
        md = ""
        
        # 金额维度分析
        if amount_analysis and isinstance(amount_analysis, dict):
            md += "### 💰 金额维度分析\n\n"
            md += self._format_amount_analysis(amount_analysis)
        
        # 先验规则分析
        if prior_analysis and isinstance(prior_analysis, dict):
            md += "### 📋 先验规则分析\n\n"
            
            # Summary metrics
            summary = prior_analysis.get('summary', {})
            if summary:
                md += "| 先验规则数 | 新规则数 | 增量召回率 | 平均重叠率 |\n"
                md += "|------------|----------|------------|------------|\n"
                
                prior_count = summary.get('prior_rules_count', 0)
                matched_count = summary.get('matched_count', 0)
                incremental_recall = summary.get('incremental_recall', 0)
                incremental_str = f"{incremental_recall*100:.2f}%" if isinstance(incremental_recall, (int, float)) else '-'
                avg_overlap = summary.get('avg_overlap_rate', 0)
                avg_overlap_str = f"{avg_overlap*100:.2f}%" if isinstance(avg_overlap, (int, float)) else '-'
                
                md += f"| {prior_count} | {matched_count} | {incremental_str} | {avg_overlap_str} |\n\n"
            
            # Prior rules table
            prior_rules = prior_analysis.get('rules', [])
            if prior_rules:
                md += "**先验规则详情**\n\n"
                md += "| 规则 | 独立召回 | 增量召回 | 重叠率 | 边际贡献 |\n"
                md += "|------|----------|----------|--------|----------|\n"
                
                for rule in prior_rules[:20]:
                    rule_text = str(rule.get('rule', rule.get('condition', '')))[:40]
                    
                    standalone = rule.get('standalone_recall', rule.get('recall', 0))
                    standalone_str = f"{standalone*100:.2f}%" if isinstance(standalone, (int, float)) else '-'
                    
                    incremental = rule.get('incremental_recall', 0)
                    incremental_str = f"{incremental*100:.2f}%" if isinstance(incremental, (int, float)) else '-'
                    
                    overlap = rule.get('overlap_rate', 0)
                    overlap_str = f"{overlap*100:.2f}%" if isinstance(overlap, (int, float)) else '-'
                    
                    marginal = rule.get('marginal_contribution', 0)
                    marginal_str = f"{marginal*100:.2f}%" if isinstance(marginal, (int, float)) else '-'
                    
                    md += f"| {rule_text} | {standalone_str} | {incremental_str} | {overlap_str} | {marginal_str} |\n"
                
                if len(prior_rules) > 20:
                    md += f"\n*（仅显示前20条，共{len(prior_rules)}条）*\n"
                
                md += "\n"
        
        return md
    
    def _format_stages_summary(
        self, 
        stages: dict[str, Any], 
        stage_configs: Optional[list["StageDataSheetConfig"]] = None
    ) -> str:
        """格式化阶段执行摘要（配置驱动）"""
        if not stages:
            return "暂无阶段数据\n\n"
        
        # 构建配置索引
        config_map = {}
        if stage_configs:
            for config in stage_configs:
                config_map[config.stage_id] = config
        
        md = ""
        for stage_id, stage_data in stages.items():
            stage_name = stage_data.get('stage_name', stage_id)
            status = stage_data.get('status', 'unknown')
            
            # 状态图标
            status_icon = "✅" if status == 'completed' else "⏸️" if status == 'paused' else "❌" if status == 'failed' else "⏳"
            
            md += f"### {stage_name} {status_icon}\n\n"
            
            output_preview = stage_data.get('output_preview')
            if output_preview and isinstance(output_preview, dict):
                # 从配置获取下载字段信息
                config = config_map.get(stage_id)
                download_field = config.download_field if config else None
                download_title = config.download_title if config else None
                
                # 如果有配置的下载字段，优先显示该字段的摘要
                if download_field and download_field in output_preview:
                    download_data = output_preview[download_field]
                    if isinstance(download_data, list) and len(download_data) > 0:
                        md += f"**{download_title or download_field}**: {len(download_data)} 条记录\n\n"
                
                # 显示其他概要字段（排除大型数据和内部字段）
                summary_items = []
                exclude_fields = {
                    '_full_stage_data', '_skip_expert_pause', '_skipped_during_retry',
                    'retry_message', 'rules_preview', 'top_rules',
                    'feature_details', 'all_rules_for_download', 
                    'all_rules_with_status', 'all_optimal_rules'
                }
                if download_field:
                    exclude_fields.add(download_field)
                
                for key, value in output_preview.items():
                    if key.startswith('_') or key in exclude_fields:
                        continue
                    if isinstance(value, (list, dict)) and len(str(value)) > 200:
                        continue
                    if isinstance(value, (int, float)):
                        if isinstance(value, float):
                            summary_items.append(f"- {key}: {value:.4f}")
                        else:
                            summary_items.append(f"- {key}: {value}")
                    elif isinstance(value, str) and len(value) < 100:
                        summary_items.append(f"- {key}: {value}")
                
                if summary_items:
                    md += "\n".join(summary_items[:10]) + "\n"
                    if len(summary_items) > 10:
                        md += f"- *(还有 {len(summary_items) - 10} 项...)*\n"
            
            md += "\n"
        
        return md
    
    # ==================== 评分卡特有的格式化方法 ====================
    
    def _format_evaluation_charts_index(self, results: dict[str, Any], stages: dict[str, Any] | None) -> str:
        """
        2026-02-10: 简化版评估图表章节 - 只显示图表索引
        
        结构：仅包含图表索引（不含「多数据集性能汇总」，该内容已在「概览」中展示）
        """
        md = ""
        
        # 获取数据
        multi_dataset_metrics = results.get('multi_dataset_metrics', {})
        multi_dataset_chart_data = results.get('multi_dataset_chart_data', {})
        
        # PSI 数据
        psi_train_vs_test = results.get('psi_train_vs_test')
        psi_train_vs_oot = results.get('psi_train_vs_oot')
        
        # 判断是否有 OOT
        has_oot = bool(multi_dataset_metrics.get('oot') or multi_dataset_chart_data.get('oot'))
        
        # ==================== 图表索引 ====================
        # 先收集可用图表，只有当有可用图表时才显示索引表
        chart_index = []
        
        # 数据集展示顺序：OOT > 测试集 > 训练集
        datasets_to_show = []
        if has_oot:
            datasets_to_show.append(('oot', 'OOT验证集', psi_train_vs_oot, '训练集 vs OOT'))
        datasets_to_show.append(('test', '测试集', psi_train_vs_test, '训练集 vs 测试集'))
        datasets_to_show.append(('train', '训练集', None, None))
        
        for dataset_key, dataset_label, psi_data, psi_comparison in datasets_to_show:
            dataset_chart_data = multi_dataset_chart_data.get(dataset_key, {})
            
            # ROC
            if dataset_chart_data.get('roc'):
                chart_index.append((dataset_label, 'ROC曲线'))
            
            # KS
            if dataset_chart_data.get('ks'):
                chart_index.append((dataset_label, 'KS曲线'))
            
            # Lift + 排序性 + 评分分布
            score_dist = dataset_chart_data.get('score_distribution', {})
            ranking_bins = score_dist.get('ranking_analysis', {}).get('bins', score_dist.get('bins', []))
            
            if ranking_bins:
                chart_index.append((dataset_label, 'Lift曲线'))
                chart_index.append((dataset_label, '排序性分析表'))
            
            if score_dist.get('summary'):
                chart_index.append((dataset_label, '评分分布图'))
            
            # PSI（仅OOT和测试集）
            if psi_data:
                chart_index.append((dataset_label, f'PSI分布对比（{psi_comparison}）'))
        
        # 只有当有可用图表时才显示索引表
        if chart_index:
            md += "| 序号 | 数据集 | 图表/表格 |\n"
            md += "|------|--------|----------|\n"
            
            for idx, (ds_label, chart_name) in enumerate(chart_index, 1):
                md += f"| {idx} | {ds_label} | {chart_name} |\n"
            
            md += f"\n**图表总数**：{len(chart_index)}项可用"
            if has_oot:
                md += "（含OOT验证集）"
            md += "\n\n"
        else:
            # 没有可用图表时，显示简洁提示
            md += "*图表数据请在前端「评估图表」Tab中查看*\n\n"
        
        return md
    
    def _format_evaluation_charts_by_dataset(self, results: dict[str, Any], stages: dict[str, Any] | None) -> str:
        """
        2026-02-10: 按数据集组织的评估图表章节
        
        结构：
        3.1 多数据集性能汇总
        3.2 OOT验证集（6项）- 有OOT时
        3.3 测试集（6项）
        3.4 训练集（5项）
        3.5 图表索引
        """
        md = ""
        
        # 获取数据
        metrics = results.get('metrics', {})
        multi_dataset_metrics = results.get('multi_dataset_metrics', {})
        multi_dataset_chart_data = results.get('multi_dataset_chart_data', {})
        overfit_warning = results.get('overfit_warning')
        
        # PSI 数据：优先使用新字段，兼容旧字段
        psi_result = results.get('psi_result')
        psi_train_vs_test = results.get('psi_train_vs_test')
        psi_train_vs_oot = results.get('psi_train_vs_oot')
        # 向后兼容：如果新字段不存在，尝试从 psi_result 推断
        if psi_train_vs_test is None and psi_result and psi_result.get('comparison') == '训练集 vs 测试集':
            psi_train_vs_test = psi_result
        if psi_train_vs_oot is None and psi_result and psi_result.get('comparison') == '训练集 vs OOT':
            psi_train_vs_oot = psi_result
        
        # 从 stages 获取数据集划分信息
        split_info = {}
        if stages:
            data_prep = stages.get('data_preparation', {})
            if isinstance(data_prep, dict):
                preview = data_prep.get('output_preview', {})
                split_info = preview.get('split_info', {})
        
        # 判断是否有 OOT
        has_oot = bool(multi_dataset_metrics.get('oot') or multi_dataset_chart_data.get('oot'))
        
        # ==================== 3.1 多数据集性能汇总 ====================
        md += "### 3.1 多数据集性能汇总\n\n"
        md += "| 数据集 | 样本数 | 坏账率 | KS | AUC | Gini |\n"
        md += "|--------|--------|--------|-----|-----|------|\n"
        
        # 训练集
        train_metrics = multi_dataset_metrics.get('train', {})
        train_samples = split_info.get('train', train_metrics.get('n_samples', '-'))
        train_bad_rate = train_metrics.get('bad_rate', split_info.get('train_target_rate'))
        train_ks = train_metrics.get('ks', metrics.get('train_ks', metrics.get('ks')))
        train_auc = train_metrics.get('auc', metrics.get('train_auc', metrics.get('auc')))
        train_gini = train_metrics.get('gini', metrics.get('gini'))
        md += f"| 训练集 | {train_samples:,} | " if isinstance(train_samples, int) else f"| 训练集 | {train_samples} | "
        md += f"{train_bad_rate * 100:.2f}% | " if isinstance(train_bad_rate, (int, float)) else "- | "
        md += f"{train_ks * 100:.2f}% | " if isinstance(train_ks, (int, float)) else "- | "
        md += f"{train_auc:.4f} | " if isinstance(train_auc, (int, float)) else "- | "
        md += f"{train_gini * 100:.2f}% |\n" if isinstance(train_gini, (int, float)) else "- |\n"
        
        # 测试集
        test_metrics = multi_dataset_metrics.get('test', {})
        test_samples = split_info.get('test', test_metrics.get('n_samples', '-'))
        test_bad_rate = test_metrics.get('bad_rate', split_info.get('test_target_rate'))
        test_ks = test_metrics.get('ks', metrics.get('test_ks'))
        test_auc = test_metrics.get('auc', metrics.get('test_auc'))
        test_gini = test_metrics.get('gini')
        md += f"| 测试集 | {test_samples:,} | " if isinstance(test_samples, int) else f"| 测试集 | {test_samples} | "
        md += f"{test_bad_rate * 100:.2f}% | " if isinstance(test_bad_rate, (int, float)) else "- | "
        md += f"{test_ks * 100:.2f}% | " if isinstance(test_ks, (int, float)) else "- | "
        md += f"{test_auc:.4f} | " if isinstance(test_auc, (int, float)) else "- | "
        md += f"{test_gini * 100:.2f}% |\n" if isinstance(test_gini, (int, float)) else "- |\n"
        
        # OOT（如有）
        if has_oot:
            oot_metrics = multi_dataset_metrics.get('oot', {})
            oot_samples = split_info.get('oot', oot_metrics.get('n_samples', '-'))
            oot_bad_rate = oot_metrics.get('bad_rate', split_info.get('oot_target_rate'))
            oot_ks = oot_metrics.get('ks')
            oot_auc = oot_metrics.get('auc')
            oot_gini = oot_metrics.get('gini')
            md += f"| OOT验证集 | {oot_samples:,} | " if isinstance(oot_samples, int) else f"| OOT验证集 | {oot_samples} | "
            md += f"{oot_bad_rate * 100:.2f}% | " if isinstance(oot_bad_rate, (int, float)) else "- | "
            md += f"{oot_ks * 100:.2f}% | " if isinstance(oot_ks, (int, float)) else "- | "
            md += f"{oot_auc:.4f} | " if isinstance(oot_auc, (int, float)) else "- | "
            md += f"{oot_gini * 100:.2f}% |\n" if isinstance(oot_gini, (int, float)) else "- |\n"
        
        md += "\n"
        
        # 过拟合警告
        if overfit_warning and overfit_warning != 'None' and str(overfit_warning).strip():
            md += f"⚠️ **过拟合警告**: {overfit_warning}\n\n"
        
        md += "---\n\n"
        
        # ==================== 按数据集展示详细信息 ====================
        subsection_num = 2
        chart_index = []  # 收集图表索引
        
        # 数据集展示顺序：OOT > 测试集 > 训练集
        datasets_to_show = []
        if has_oot:
            datasets_to_show.append(('oot', 'OOT验证集', '用于评估模型时间外泛化能力', psi_train_vs_oot, '训练集 vs OOT'))
        datasets_to_show.append(('test', '测试集', '用于验证模型在同期数据上的泛化表现', psi_train_vs_test, '训练集 vs 测试集'))
        datasets_to_show.append(('train', '训练集', '作为基准参照（可能存在过拟合）', None, None))
        
        for dataset_key, dataset_label, description, psi_data, psi_comparison in datasets_to_show:
            dataset_metrics = multi_dataset_metrics.get(dataset_key, {})
            dataset_chart_data = multi_dataset_chart_data.get(dataset_key, {})
            
            # 计算该数据集的图表数量
            chart_count = 0
            if dataset_chart_data.get('roc'):
                chart_count += 1
            if dataset_chart_data.get('ks'):
                chart_count += 1
            if dataset_chart_data.get('score_distribution'):
                chart_count += 3  # Lift曲线 + 排序性分析表 + 评分分布
            if psi_data:
                chart_count += 1
            
            md += f"### 3.{subsection_num} {dataset_label}（{chart_count}项）\n\n"
            md += f"*{description}*\n\n"
            
            # 3.x.1 性能曲线
            md += f"#### 3.{subsection_num}.1 性能曲线\n\n"
            md += "| 图表 | 核心指标 |\n"
            md += "|------|----------|\n"
            
            # ROC
            roc_data = dataset_chart_data.get('roc', {})
            auc_val = roc_data.get('auc', dataset_metrics.get('auc'))
            if auc_val is not None:
                md += f"| ROC曲线 | AUC = {auc_val:.4f} |\n"
                chart_index.append((dataset_label, 'ROC曲线', '✅'))
            else:
                md += "| ROC曲线 | - |\n"
                chart_index.append((dataset_label, 'ROC曲线', '❌'))
            
            # KS
            ks_data = dataset_chart_data.get('ks', {})
            ks_val = ks_data.get('ks_max', dataset_metrics.get('ks'))
            if ks_val is not None:
                md += f"| KS曲线 | KS = {ks_val * 100:.2f}% |\n"
                chart_index.append((dataset_label, 'KS曲线', '✅'))
            else:
                md += "| KS曲线 | - |\n"
                chart_index.append((dataset_label, 'KS曲线', '❌'))
            
            # Lift
            score_dist = dataset_chart_data.get('score_distribution', {})
            ranking_bins = score_dist.get('ranking_analysis', {}).get('bins', score_dist.get('bins', []))
            if ranking_bins:
                first_lift = ranking_bins[0].get('lift') if ranking_bins else None
                last_lift = ranking_bins[-1].get('lift') if ranking_bins else None
                first_str = f"{first_lift:.2f}" if first_lift is not None else "-"
                last_str = f"{last_lift:.2f}" if last_lift is not None else "-"
                md += f"| Lift曲线 | 首组={first_str}, 末组={last_str} |\n"
                chart_index.append((dataset_label, 'Lift曲线', '✅'))
            else:
                md += "| Lift曲线 | - |\n"
                chart_index.append((dataset_label, 'Lift曲线', '❌'))
            
            md += "\n"
            
            # 3.x.2 排序性分析表
            if ranking_bins:
                md += f"#### 3.{subsection_num}.2 排序性分析表\n\n"
                md += "| 评分区间 | 样本数 | 占比 | 坏样本数 | 坏账率 | Lift |\n"
                md += "|----------|--------|------|----------|--------|------|\n"
                
                # 显示前3行和后2行，中间用省略
                display_bins = ranking_bins[:3] + [None] + ranking_bins[-2:] if len(ranking_bins) > 5 else ranking_bins
                for bin_item in display_bins:
                    if bin_item is None:
                        md += "| ... | ... | ... | ... | ... | ... |\n"
                    else:
                        bin_label = bin_item.get('bin', '-')
                        total = bin_item.get('total', 0)
                        pct = bin_item.get('pct_total', 0)
                        bad = bin_item.get('bad', 0)
                        bad_rate = bin_item.get('bad_rate', 0)
                        lift = bin_item.get('lift', 0)
                        md += f"| {bin_label} | {total:,} | {pct:.1f}% | {bad:,} | {bad_rate:.2f}% | {lift:.2f} |\n"
                
                md += "\n"
                
                # 单调性和Lift分析
                rank_analysis = score_dist.get('rank_ordering_analysis', {})
                monotonicity = rank_analysis.get('monotonicity', {})
                lift_analysis = rank_analysis.get('lift_analysis', {})
                
                mono_pass = monotonicity.get('is_monotonic', False)
                mono_violations = monotonicity.get('violations', 0)
                mono_str = "✅ 通过" if mono_pass else f"⚠️ 不通过（{mono_violations}处违反）"
                
                first_lift_val = lift_analysis.get('first_bin_lift', first_lift)
                last_lift_val = lift_analysis.get('last_bin_lift', last_lift)
                first_str = f"{first_lift_val:.2f}" if first_lift_val is not None else "-"
                last_str = f"{last_lift_val:.2f}" if last_lift_val is not None else "-"
                
                md += f"**单调性**：{mono_str} | **首组Lift**：{first_str} | **末组Lift**：{last_str}\n\n"
                chart_index.append((dataset_label, '排序性分析表', '✅'))
            else:
                chart_index.append((dataset_label, '排序性分析表', '❌'))
            
            # 3.x.3 评分分布
            summary = score_dist.get('summary', {})
            if summary:
                md += f"#### 3.{subsection_num}.3 评分分布\n\n"
                md += "| 统计量 | 值 |\n"
                md += "|--------|-----|\n"
                
                good_mean = summary.get('good_mean')
                bad_mean = summary.get('bad_mean')
                score_min = summary.get('score_min')
                score_max = summary.get('score_max')
                total_samples = summary.get('total_samples')
                overall_bad_rate = summary.get('overall_bad_rate')
                
                if good_mean is not None:
                    md += f"| 好样本均分 | {good_mean:.1f} |\n"
                if bad_mean is not None:
                    md += f"| 坏样本均分 | {bad_mean:.1f} |\n"
                if good_mean is not None and bad_mean is not None:
                    separation = abs(good_mean - bad_mean)
                    md += f"| 分离度 | {separation:.1f}分 |\n"
                if score_min is not None:
                    md += f"| 最低分 | {score_min} |\n"
                if score_max is not None:
                    md += f"| 最高分 | {score_max} |\n"
                if total_samples is not None:
                    md += f"| 样本数 | {total_samples:,} |\n"
                if overall_bad_rate is not None:
                    md += f"| 坏账率 | {overall_bad_rate:.2f}% |\n"
                
                md += "\n"
                chart_index.append((dataset_label, '评分分布表+图', '✅'))
            else:
                chart_index.append((dataset_label, '评分分布表+图', '❌'))
            
            # 3.x.4 PSI稳定性（仅OOT和测试集有）
            if psi_data:
                md += f"#### 3.{subsection_num}.4 PSI稳定性（{psi_comparison}）\n\n"
                md += "| PSI值 | 稳定性评级 |\n"
                md += "|-------|------------|\n"
                
                psi_value = psi_data.get('value', 0)
                stability = psi_data.get('stability', '-')
                level = psi_data.get('level', 'unknown')
                
                level_icon = "✅" if level == 'good' else "⚠️" if level == 'warning' else "❌"
                md += f"| {psi_value:.4f} | {level_icon} {stability} |\n"
                md += "\n"
                md += "*PSI评级标准：<0.1 稳定，0.1-0.25 轻微变化，>0.25 显著变化*\n\n"
                chart_index.append((dataset_label, f'PSI分布对比（{psi_comparison}）', '✅'))
            
            md += "---\n\n"
            subsection_num += 1
        
        # ==================== 3.x 图表索引 ====================
        md += f"### 3.{subsection_num} 图表索引\n\n"
        md += "| 序号 | 数据集 | 图表/表格 | 状态 |\n"
        md += "|------|--------|----------|------|\n"
        
        for idx, (ds_label, chart_name, status) in enumerate(chart_index, 1):
            md += f"| {idx} | {ds_label} | {chart_name} | {status} |\n"
        
        # 计算图表总数
        available_count = sum(1 for _, _, s in chart_index if s == '✅')
        total_count = len(chart_index)
        md += f"\n**图表总数**：{available_count}/{total_count}项可用"
        if has_oot:
            md += "（含OOT验证集）"
        md += "\n\n"
        
        return md
    
    def _format_scorecard_metrics(self, metrics: dict, results: dict) -> str:
        """格式化评分卡核心指标（旧方法，保留向后兼容）"""
        md = "| 指标 | 训练集 | 测试集 |\n"
        md += "|------|--------|--------|\n"
        
        train_auc = metrics.get('train_auc', metrics.get('auc'))
        test_auc = metrics.get('test_auc')
        train_ks = metrics.get('train_ks', metrics.get('ks'))
        test_ks = metrics.get('test_ks')
        
        if train_auc is not None or test_auc is not None:
            train_str = f"{train_auc:.4f}" if isinstance(train_auc, (int, float)) else '-'
            test_str = f"{test_auc:.4f}" if isinstance(test_auc, (int, float)) else '-'
            md += f"| AUC | {train_str} | {test_str} |\n"
        
        if train_ks is not None or test_ks is not None:
            train_str = f"{train_ks * 100:.2f}%" if isinstance(train_ks, (int, float)) else '-'
            test_str = f"{test_ks * 100:.2f}%" if isinstance(test_ks, (int, float)) else '-'
            md += f"| KS | {train_str} | {test_str} |\n"
        
        # 其他指标
        if 'n_samples' in metrics:
            md += f"| 样本量 | {metrics['n_samples']} | - |\n"
        if 'n_features' in metrics:
            md += f"| 特征数 | {metrics['n_features']} | - |\n"
        
        # 过拟合警告
        overfit_warning = results.get('overfit_warning')
        if overfit_warning:
            md += f"\n**⚠️ 过拟合警告**: {overfit_warning}\n"
        
        md += "\n"
        return md
    
    def _format_selected_features(self, selected_features: Any, results: dict) -> str:
        """格式化特征筛选结果"""
        md = ""
        
        if isinstance(selected_features, list):
            md += f"**入模特征数**: {len(selected_features)}\n\n"
            md += "| 序号 | 特征名 |\n"
            md += "|------|--------|\n"
            for i, feature in enumerate(selected_features[:20], 1):
                md += f"| {i} | {feature} |\n"
            if len(selected_features) > 20:
                md += f"\n*（仅显示前20个，共{len(selected_features)}个）*\n"
        elif isinstance(selected_features, str):
            md += f"**入模特征**: {selected_features}\n"
        
        # 筛选详情
        selection_detail = results.get('selection_detail')
        if selection_detail:
            md += f"\n**筛选说明**: {selection_detail}\n"
        
        # 异常值处理
        outlier_info = results.get('outlier_info')
        if outlier_info:
            md += f"\n**异常值处理**: {outlier_info}\n"
        
        md += "\n"
        return md
    
    def _format_scorecard_details(self, scorecard: Any) -> str:
        """格式化评分卡明细"""
        md = ""
        
        if isinstance(scorecard, dict):
            for variable, var_data in scorecard.items():
                md += f"### {variable}\n\n"
                md += "| 分箱 | WOE | 分数 |\n"
                md += "|------|-----|------|\n"
                
                bins = []
                if isinstance(var_data, dict) and 'data' in var_data:
                    bins = var_data['data']
                elif isinstance(var_data, list):
                    bins = var_data
                
                for bin_item in bins[:15]:
                    bin_name = bin_item.get('bin', bin_item.get('Bin', '-'))
                    woe = bin_item.get('woe', bin_item.get('WOE', 0))
                    points = bin_item.get('points', bin_item.get('Points', 0))
                    
                    woe_str = f"{woe:.4f}" if isinstance(woe, (int, float)) else str(woe)
                    points_str = f"{points:.0f}" if isinstance(points, (int, float)) else str(points)
                    
                    md += f"| {bin_name} | {woe_str} | {points_str} |\n"
                
                md += "\n"
        elif isinstance(scorecard, list):
            md += "| 变量 | 分箱 | WOE | 分数 |\n"
            md += "|------|------|-----|------|\n"
            for item in scorecard[:50]:
                var = item.get('variable', '-')
                bin_name = item.get('bin', '-')
                woe = item.get('woe', 0)
                points = item.get('points', 0)
                md += f"| {var} | {bin_name} | {woe:.4f} | {points:.0f} |\n"
            if len(scorecard) > 50:
                md += f"\n*（仅显示前50条）*\n"
        
        return md
    
    def _format_scorecard_details_full(
        self, 
        full_scorecard_csv: list, 
        score_scaling_preview: dict,
        scorecard: Any,
        multi_dataset_chart_data: dict = None
    ) -> str:
        """
        格式化评分卡明细（完整版，与前端 Tab 保持一致）
        
        2026-02-09: 新增函数，使用 full_scorecard_csv 数据源
        2026-02-10: 与 HTML 报告对齐优化
        展示内容：
        - 第一行指标卡：入模变量数、评分区间（取整+统计指标）、基准配置
        - 第二行指标卡：好/坏样本均分和分离度
        - 入模变量评分贡献
        - 完整评分卡表格（变量名/IV/系数仅在变量第一行显示）
        """
        md = ""
        
        # ========== 获取评分分布统计数据（按优先级：OOT > 测试集 > 训练集）==========
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
        
        # ========== 第一行指标卡：入模变量数、评分区间、基准配置 ==========
        num_vars = score_scaling_preview.get('num_variables', 0)
        theoretical_range = score_scaling_preview.get('theoretical_score_range', {})
        base_score = score_scaling_preview.get('base_score', 600)
        base_odds = score_scaling_preview.get('base_odds', 20)
        pdo = score_scaling_preview.get('pdo', 50)
        
        md += "### 核心参数\n\n"
        md += "| 指标 | 值 |\n"
        md += "|------|----|\n"
        md += f"| 入模变量数 | {num_vars} |\n"
        
        # 评分区间（取整 + 统计指标）
        if theoretical_range.get('min') is not None and theoretical_range.get('max') is not None:
            score_min = int(round(theoretical_range.get('min', 0)))
            score_max = int(round(theoretical_range.get('max', 0)))
            
            # 构建统计指标字符串
            stats_details = []
            if actual_stats:
                mean_val = actual_stats.get('mean')
                median_val = actual_stats.get('median')
                q25 = actual_stats.get('q25')
                q75 = actual_stats.get('q75')
                
                if mean_val is not None:
                    stats_details.append(f"均值 {int(round(mean_val))}")
                if median_val is not None:
                    stats_details.append(f"中位数 {int(round(median_val))}")
                if q25 is not None and q75 is not None:
                    stats_details.append(f"IQR {int(round(q25))}-{int(round(q75))}")
            
            stats_str = f" ({stats_dataset_label}: {', '.join(stats_details)})" if stats_details else ""
            md += f"| 评分区间 | {score_min} ~ {score_max}{stats_str} |\n"
        
        md += f"| 基准配置 | {base_score}/{base_odds}/{pdo} (基准分/Odds/PDO) |\n"
        md += "\n"
        
        # ========== 第二行指标卡：好/坏样本均分和分离度 ==========
        if multi_dataset_chart_data:
            # 按优先级选择数据集：OOT > 测试集 > 训练集
            selected_dist_data = None
            dataset_label = ""
            for ds_key, ds_label in [('oot', 'OOT验证集'), ('test', '测试集'), ('train', '训练集')]:
                ds_chart = multi_dataset_chart_data.get(ds_key, {})
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
                        elif separation >= 40:
                            sep_rating = "✓ 良好"
                        elif separation >= 20:
                            sep_rating = "○ 合格"
                        else:
                            sep_rating = "△ 偏低"
                    else:
                        sep_rating = "-"
                    
                    md += f"### 评分分离度 ({dataset_label})\n\n"
                    md += "| 好样本均分 | 坏样本均分 | 分离度 |\n"
                    md += "|------------|------------|--------|\n"
                    good_str = f"{good_mean:.1f}" if good_mean is not None else "-"
                    bad_str = f"{bad_mean:.1f}" if bad_mean is not None else "-"
                    sep_str = f"{separation:.1f} ({sep_rating})" if separation is not None else "-"
                    md += f"| {good_str} | {bad_str} | {sep_str} |\n\n"
        
        # ========== 入模变量评分贡献 ==========
        scorecard_preview = score_scaling_preview.get('scorecard_preview', [])
        if scorecard_preview and len(scorecard_preview) > 0:
            # 筛选出有效变量（排除常数项）
            valid_vars = [v for v in scorecard_preview if v.get('variable') not in ('basepoints', '常数项')]
            
            if valid_vars:
                # 计算波动幅度并排序
                for v in valid_vars:
                    min_score = v.get('min_score', 0) or 0
                    max_score = v.get('max_score', 0) or 0
                    v['_score_range'] = abs(max_score - min_score)
                
                sorted_vars = sorted(valid_vars, key=lambda x: x.get('_score_range', 0), reverse=True)[:10]
                
                md += "### 入模变量评分贡献\n\n"
                md += "| 变量 | 最低分 | 最高分 | 波动幅度 |\n"
                md += "|------|--------|--------|----------|\n"
                
                for v in sorted_vars:
                    var_name = v.get('variable', '')
                    min_score = v.get('min_score', 0) or 0
                    max_score = v.get('max_score', 0) or 0
                    score_range = v.get('_score_range', 0)
                    
                    var_display = var_name[:25] + '...' if len(var_name) > 25 else var_name
                    md += f"| {var_display} | {min_score:.0f} | {max_score:.0f} | {score_range:.0f}分 |\n"
                
                md += "\n*波动幅度 = 最高分 - 最低分，反映变量对评分的影响程度*\n\n"
        
        # ========== 完整评分卡表格（变量名/IV/系数仅在变量第一行显示） ==========
        if full_scorecard_csv and len(full_scorecard_csv) > 0:
            md += "### 完整评分卡\n\n"
            md += "*样本统计基于训练集*\n\n"
            md += "| 变量 | IV | 系数 | 序号 | 分箱 | 样本数 | 占比 | 好样本 | 坏样本 | 坏率 | WOE | 评分 |\n"
            md += "|------|-----|------|------|------|--------|------|--------|--------|------|-----|------|\n"
            
            # 记录已处理的变量（用于判断是否显示变量名/IV/系数）
            processed_variables = set()
            
            for row in full_scorecard_csv:
                var = row.get('variable', '-')
                iv = row.get('total_iv', '')
                cof = row.get('cof', '')
                idx = row.get('index', '')
                bin_name = row.get('bin', '-')
                count = row.get('count', '')
                count_distr = row.get('count_distr', '')
                good = row.get('good', '')
                bad = row.get('bad', '')
                badprob = row.get('badprob', '')
                woe = row.get('woe', '')
                score = row.get('score', '')
                
                # 判断是否为变量的第一行
                is_first_row_of_variable = var not in processed_variables
                if is_first_row_of_variable:
                    processed_variables.add(var)
                
                # 格式化数值
                woe_str = f"{woe:.4f}" if isinstance(woe, (int, float)) else str(woe)
                score_str = f"{score:.2f}" if isinstance(score, (int, float)) else str(score)
                
                # 变量名、IV、系数只在变量第一行显示，其他行留空（与前端对齐）
                if is_first_row_of_variable:
                    # 常数项特殊处理
                    var_display = '常数项' if var in ('常数项', 'basepoints') else var
                    iv_str = f"{iv:.4f}" if isinstance(iv, (int, float)) else (str(iv) if iv else '-')
                    cof_str = f"{cof:.4f}" if isinstance(cof, (int, float)) else (str(cof) if cof else '-')
                else:
                    # 非第一行，变量名/IV/系数留空
                    var_display = ''
                    iv_str = ''
                    cof_str = ''
                
                md += f"| {var_display} | {iv_str} | {cof_str} | {idx} | {bin_name} | {count} | {count_distr} | {good} | {bad} | {badprob} | {woe_str} | {score_str} |\n"
            
            md += f"\n共 {len(full_scorecard_csv)} 条分箱记录\n\n"
        
        # 3. 回退：如果没有 full_scorecard_csv，使用旧格式
        elif scorecard:
            md += "### 评分卡分箱\n\n"
            md += self._format_scorecard_details(scorecard)
        
        return md
    
    def _format_iv_table(self, iv_table: list) -> str:
        """格式化IV值表格"""
        if not iv_table:
            return "暂无IV数据\n\n"
        
        md = "| 排名 | 变量 | IV值 | 预测能力 |\n"
        md += "|------|------|------|----------|\n"
        
        for i, item in enumerate(iv_table[:20], 1):
            var = item.get('variable', item.get('feature', '-'))
            iv = item.get('iv', item.get('IV', 0))
            
            iv_str = f"{iv:.4f}" if isinstance(iv, (int, float)) else str(iv)
            
            # 判断预测能力
            if isinstance(iv, (int, float)):
                if iv >= 0.5:
                    power = "极强"
                elif iv >= 0.3:
                    power = "强"
                elif iv >= 0.1:
                    power = "中等"
                elif iv >= 0.02:
                    power = "弱"
                else:
                    power = "极弱"
            else:
                power = "-"
            
            md += f"| {i} | {var} | {iv_str} | {power} |\n"
        
        if len(iv_table) > 20:
            md += f"\n*（仅显示前20个，共{len(iv_table)}个）*\n"
        
        md += "\n"
        return md
    
    def _format_feature_selection_funnel(self, stages: dict[str, Any] | None, selected_features: list | None, results: dict[str, Any] | None = None) -> str:
        """
        格式化特征筛选漏斗概览（与 HTML 报告对齐）
        
        2026-02-10: 新增，从 stages 获取各阶段特征数量
        2026-02-11: 修复最终入模数，从 scorecard/coefficients 获取（与前端Tab一致）
        """
        md = ""
        if not stages:
            return md
        
        # 从 stages 数据获取各阶段特征数量
        data_loading = stages.get('data_loading', {})
        data_loading_preview = data_loading.get('output_preview', {}) if isinstance(data_loading, dict) else {}
        
        woe_binning = stages.get('woe_binning', {})
        woe_binning_preview = woe_binning.get('output_preview', {}) if isinstance(woe_binning, dict) else {}
        
        feature_selection = stages.get('feature_selection', {})
        feature_selection_preview = feature_selection.get('output_preview', {}) if isinstance(feature_selection, dict) else {}
        
        model_training = stages.get('model_training', {})
        model_training_preview = model_training.get('output_preview', {}) if isinstance(model_training, dict) else {}
        
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
        # 2026-02-11: 修复，使用与HTML报告相同的逻辑
        scorecard = results.get('scorecard') if results else None
        coefficients = results.get('coefficients') if results else None
        
        if scorecard is not None and len(scorecard) > 0:
            # 从scorecard获取（排除basepoints常数项）
            if isinstance(scorecard, pd.DataFrame):
                final_count = len([v for v in scorecard['variable'].unique() if v != 'basepoints']) if 'variable' in scorecard.columns else len(scorecard)
            elif isinstance(scorecard, dict):
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
            md += "### 特征筛选漏斗\n\n"
            md += "| 阶段 | 特征数 | 保留率 |\n"
            md += "|------|--------|--------|\n"
            
            funnel_steps = [
                ("原始特征", original_count),
                ("质量筛选", after_var_filter),
                ("WOE分箱", woe_output),
                ("IV/相关/VIF", fe_after),
                ("最终入模", final_count),
            ]
            
            for label, count in funnel_steps:
                pct = f"{count / original_count * 100:.1f}%" if original_count > 0 and count > 0 else "-"
                md += f"| {label} | {count or '-'} | {pct} |\n"
            
            md += "\n"
        
        return md
    
    def _format_iv_table_with_status(
        self, 
        iv_table: Any, 
        stages: dict[str, Any] | None, 
        selected_features: list | None
    ) -> str:
        """
        格式化IV值表格（带状态和淘汰信息，与 HTML 报告对齐）
        
        2026-02-10: 新增，展示变量状态（入模/淘汰/未入模）和淘汰原因
        """
        if iv_table is None:
            return "暂无IV数据\n\n"
        
        # 处理 DataFrame 或 list
        if hasattr(iv_table, 'to_dict'):
            iv_data = iv_table.to_dict('records')
        elif isinstance(iv_table, list):
            iv_data = iv_table
        else:
            return "暂无IV数据\n\n"
        
        if not iv_data:
            return "暂无IV数据\n\n"
        
        # 构建淘汰信息映射
        elimination_map: dict[str, dict[str, str]] = {}
        
        if stages:
            # 从 data_loading 获取数据质量筛选淘汰的特征
            data_loading = stages.get('data_loading', {})
            data_loading_preview = data_loading.get('output_preview', {}) if isinstance(data_loading, dict) else {}
            var_filter_result = data_loading_preview.get('var_filter_result', {})
            
            removed_by_missing = var_filter_result.get('removed_by_missing', [])
            for item in removed_by_missing:
                if isinstance(item, dict) and item.get('feature'):
                    elimination_map[item['feature']] = {
                        'stage': '数据质量',
                        'reason': item.get('reason', f"缺失率{(item.get('missing_rate', 0) * 100):.0f}%")
                    }
            
            removed_by_identical = var_filter_result.get('removed_by_identical', [])
            for item in removed_by_identical:
                if isinstance(item, dict) and item.get('feature'):
                    elimination_map[item['feature']] = {
                        'stage': '数据质量',
                        'reason': item.get('reason', f"同值率{(item.get('identical_rate', 0) * 100):.0f}%")
                    }
            
            # 从 WOE 阶段获取分箱失败的特征
            woe_binning = stages.get('woe_binning', {})
            woe_binning_preview = woe_binning.get('output_preview', {}) if isinstance(woe_binning, dict) else {}
            woe_filtered = woe_binning_preview.get('woe_filtered', {})
            woe_filtered_features = woe_filtered.get('features', [])
            for feat in woe_filtered_features:
                if feat not in elimination_map:
                    elimination_map[feat] = {
                        'stage': 'WOE分箱',
                        'reason': woe_filtered.get('reason', '分箱失败')
                    }
            
            # 从 feature_selection 阶段获取（IV/相关性/VIF）
            feature_selection = stages.get('feature_selection', {})
            feature_selection_preview = feature_selection.get('output_preview', {}) if isinstance(feature_selection, dict) else {}
            all_features_detail = feature_selection_preview.get('all_features_detail', [])
            for item in all_features_detail:
                if isinstance(item, dict) and item.get('feature') and item.get('remove_reason'):
                    feat = item['feature']
                    reason = item['remove_reason']
                    stage = '特征筛选(IV)' if 'IV' in reason else '特征筛选(相关性)' if '相关性' in reason else '特征筛选(VIF)' if 'VIF' in reason else '特征筛选'
                    elimination_map[feat] = {'stage': stage, 'reason': reason}
                    elimination_map[feat + '_woe'] = {'stage': stage, 'reason': reason}
            
            # 从 model_training 阶段获取逐步回归移除的特征
            model_training = stages.get('model_training', {})
            model_training_preview = model_training.get('output_preview', {}) if isinstance(model_training, dict) else {}
            stepwise_result = model_training_preview.get('stepwise_result', {})
            for s in stepwise_result.get('steps', []):
                if s.get('action') == 'remove' and s.get('feature'):
                    feat = s['feature']
                    base_name = feat.replace('_woe', '')
                    reason = f"P值={s.get('pvalue', 0):.4f}"
                    elimination_map[feat] = {'stage': '逐步回归', 'reason': reason}
                    elimination_map[base_name] = {'stage': '逐步回归', 'reason': reason}
            
            # 系数验证
            coef_validation = model_training_preview.get('coefficient_validation', {})
            for feat in coef_validation.get('invalid_direction', []):
                base_name = feat.replace('_woe', '')
                if base_name not in elimination_map and feat not in elimination_map:
                    elimination_map[feat] = {'stage': '系数验证', 'reason': '系数方向异常'}
                    elimination_map[base_name] = {'stage': '系数验证', 'reason': '系数方向异常'}
        
        # 入模特征集合
        model_features_set = set(f.replace('_woe', '') for f in (selected_features or []))
        
        # 按 IV 值排序
        sorted_iv = sorted(iv_data, key=lambda x: x.get('iv', x.get('IV', 0)), reverse=True)
        
        md = "| # | 变量 | IV值 | 预测能力 | 状态 | 淘汰阶段 | 淘汰原因 |\n"
        md += "|---|------|------|----------|------|----------|----------|\n"
        
        for i, item in enumerate(sorted_iv[:30], 1):
            var_name = item.get('variable', item.get('feature', '-'))
            iv_val = item.get('iv', item.get('IV', 0))
            
            # 预测能力判断
            if isinstance(iv_val, (int, float)):
                if iv_val >= 0.3:
                    power = '强'
                elif iv_val >= 0.1:
                    power = '中等'
                elif iv_val >= 0.02:
                    power = '弱'
                else:
                    power = '无'
            else:
                power = '-'
            
            iv_str = f"{iv_val:.4f}" if isinstance(iv_val, (int, float)) else str(iv_val)
            
            # 状态判断
            base_name = var_name.replace('_woe', '')
            is_model_var = base_name in model_features_set
            elim_info = elimination_map.get(base_name) or elimination_map.get(var_name)
            
            if is_model_var:
                status = '✅入模'
                elim_stage = '-'
                elim_reason = '-'
            elif elim_info:
                status = '❌淘汰'
                elim_stage = elim_info.get('stage', '-')
                elim_reason = elim_info.get('reason', '-')
            else:
                status = '○未入模'
                elim_stage = '-'
                elim_reason = '-'
            
            md += f"| {i} | {base_name} | {iv_str} | {power} | {status} | {elim_stage} | {elim_reason} |\n"
        
        if len(sorted_iv) > 30:
            md += f"\n*（仅显示前30个，共{len(sorted_iv)}个）*\n"
        
        md += "\n"
        return md
    
    def _format_coefficients(self, coefficients: list) -> str:
        """格式化模型系数"""
        if not coefficients:
            return "暂无系数数据\n\n"
        
        md = "| 变量 | 系数 | 标准误 | z值 | P值 | 显著性 |\n"
        md += "|------|------|--------|-----|-----|--------|\n"
        
        for item in coefficients:
            var = item.get('feature', item.get('variable', '-'))
            coef = item.get('coef', item.get('coefficient', 0))
            std_err = item.get('std_err', item.get('std_error'))
            z_val = item.get('z', item.get('z_value'))
            p_val = item.get('p_value', item.get('pvalue'))
            sig = item.get('significance', '')
            
            coef_str = f"{coef:.4f}" if isinstance(coef, (int, float)) else str(coef)
            std_str = f"{std_err:.4f}" if isinstance(std_err, (int, float)) else '-'
            z_str = f"{z_val:.4f}" if isinstance(z_val, (int, float)) else '-'
            
            if isinstance(p_val, (int, float)):
                p_str = "<0.001" if p_val < 0.001 else f"{p_val:.4f}"
            else:
                p_str = '-'
            
            md += f"| {var} | {coef_str} | {std_str} | {z_str} | {p_str} | {sig} |\n"
        
        md += "\n**显著性标记**: \\*\\*\\* p<0.001, \\*\\* p<0.01, \\* p<0.05, . p<0.1\n\n"
        
        return md
    
    def _format_model_coefficients_summary(
        self, 
        coefficients: Any, 
        model_statistics: dict | None,
        stages: dict[str, Any] | None
    ) -> str:
        """
        格式化模型系数指标卡（与 HTML 报告对齐）
        
        2026-02-10: 新增，展示入模变量、显著变量、系数方向验证、截距项
        """
        md = ""
        
        # 获取 model_training 阶段数据
        model_training = stages.get('model_training', {}) if stages else {}
        model_training_preview = model_training.get('output_preview', {}) if isinstance(model_training, dict) else {}
        
        # 优先使用 model_statistics['summary'] 作为系数统计数据源
        stats_summary = model_statistics.get('summary', []) if model_statistics else []
        
        if stats_summary and isinstance(stats_summary, list) and len(stats_summary) > 0:
            coef_list = stats_summary
        elif coefficients is not None:
            if hasattr(coefficients, 'to_dict'):
                coef_list = coefficients.to_dict('records')
            elif isinstance(coefficients, list):
                coef_list = coefficients
            else:
                coef_list = []
        else:
            coef_list = []
        
        if not coef_list:
            return md
        
        # 入模变量数：不含 const
        n_features = sum(1 for item in coef_list 
                        if item.get('feature', item.get('variable', '')) not in ('const', 'Intercept', '常数项'))
        
        # 显著变量数：p < 0.05，不含截距项
        significant_count = 0
        for item in coef_list:
            feature = item.get('feature', item.get('variable', ''))
            p_val = item.get('p_value', item.get('pvalue'))
            if feature not in ('const', 'Intercept', '常数项') and p_val is not None and isinstance(p_val, (int, float)) and p_val < 0.05:
                significant_count += 1
        
        # 获取系数方向验证数据
        coef_validation = model_training_preview.get('coefficient_validation', {})
        valid_direction = coef_validation.get('valid_direction', [])
        invalid_direction = coef_validation.get('invalid_direction', [])
        valid_count = len(valid_direction)
        invalid_count = len(invalid_direction)
        
        # 获取截距项
        intercept = model_training_preview.get('intercept') or (model_statistics.get('intercept') if model_statistics else None)
        
        # 格式化指标卡
        md += "### 核心指标\n\n"
        md += "| 指标 | 值 |\n"
        md += "|------|----|\n"
        
        # 1. 似然比检验 (与前端Tab对齐)
        lr_pvalue = model_statistics.get('lr_pvalue') if model_statistics else None
        if lr_pvalue is not None and isinstance(lr_pvalue, (int, float)):
            lr_significant = lr_pvalue < 0.05
            lr_p_str = '<0.001' if lr_pvalue < 0.001 else f"{lr_pvalue:.4f}"
            lr_status = '✓ 显著' if lr_significant else '不显著'
            md += f"| 似然比检验 | {lr_p_str} ({lr_status}) |\n"
        else:
            md += "| 似然比检验 | - |\n"
        
        md += f"| 显著变量 (p<0.05) | {significant_count}/{n_features}个 |\n"
        
        if valid_count > 0 or invalid_count > 0:
            if invalid_count == 0:
                md += f"| 系数方向验证 | ✅ {valid_count}/{valid_count}（全部正确） |\n"
            else:
                md += f"| 系数方向验证 | ⚠️ {valid_count}正确/{invalid_count}异常 |\n"
        
        if intercept is not None and isinstance(intercept, (int, float)):
            md += f"| 截距项 | {intercept:.4f} |\n"
        
        md += "\n"
        
        return md
    
    def _format_coefficients_enhanced(self, coefficients: Any, model_statistics: dict | None) -> str:
        """
        格式化逻辑回归系数表（增强版，优先使用 model_statistics['summary']）
        
        2026-02-10: 新增，与 HTML 报告对齐
        """
        # 优先使用 model_statistics['summary']
        stats_summary = model_statistics.get('summary', []) if model_statistics else []
        
        if stats_summary and isinstance(stats_summary, list) and len(stats_summary) > 0:
            coef_list = stats_summary
        elif coefficients is not None:
            if hasattr(coefficients, 'to_dict'):
                coef_list = coefficients.to_dict('records')
            elif isinstance(coefficients, list):
                coef_list = coefficients
            else:
                return "暂无系数数据\n\n"
        else:
            return "暂无系数数据\n\n"
        
        if not coef_list:
            return "暂无系数数据\n\n"
        
        md = "| 变量 | 系数 | 标准误 | z值 | P值 | 显著性 |\n"
        md += "|------|------|--------|-----|-----|--------|\n"
        
        for item in coef_list:
            var = item.get('feature', item.get('variable', '-'))
            
            # 排除 const 行（与前端Tab一致，截距项单独显示在指标卡中）
            if var == 'const':
                continue
            
            coef = item.get('coef', item.get('coefficient', 0))
            std_err = item.get('std_err', item.get('std_error'))
            z_val = item.get('z', item.get('z_value'))
            p_val = item.get('p_value', item.get('pvalue'))
            sig = item.get('significance', '')
            
            # 格式化变量名（移除_woe后缀）
            var_display = var.replace('_woe', '')
            
            coef_str = f"{coef:.4f}" if isinstance(coef, (int, float)) else str(coef)
            std_str = f"{std_err:.4f}" if isinstance(std_err, (int, float)) else '-'
            z_str = f"{z_val:.4f}" if isinstance(z_val, (int, float)) else '-'
            p_str = f"{p_val:.4f}" if isinstance(p_val, (int, float)) else '-'
            
            md += f"| {var_display} | {coef_str} | {std_str} | {z_str} | {p_str} | {sig} |\n"
        
        md += "\n**显著性标记**: \\*\\*\\* p<0.001, \\*\\* p<0.01, \\* p<0.05, . p<0.1\n\n"
        
        return md
    
    def _format_model_statistics(self, model_statistics: dict) -> str:
        """格式化模型统计检验（与前端Tab对齐，只显示模型拟合指标）"""
        if not model_statistics:
            return "暂无统计检验数据\n\n"
        
        md = "| 统计量 | 值 |\n"
        md += "|--------|----|\n"
        
        # 2026-02-11: 与前端Tab的"模型拟合指标"对齐，只显示这4个指标
        stat_names = {
            'pseudo_r2': '伪R²',
            'log_likelihood': '对数似然',
            'aic': 'AIC',
            'bic': 'BIC',
        }
        
        for key, label in stat_names.items():
            if key in model_statistics and model_statistics[key] is not None:
                value = model_statistics[key]
                if isinstance(value, float):
                    value_str = f"{value:.4f}"
                else:
                    value_str = str(value)
                md += f"| {label} | {value_str} |\n"
        
        md += "\n"
        return md


def generate_markdown_report(
    results: dict[str, Any],
    report_type: Literal['scorecard', 'rule_mining'] = 'rule_mining',
    title: str | None = None,
    ai_analysis: str | None = None,
    config: Optional["TaskResultConfig"] = None
) -> str:
    """
    生成Markdown报告的便捷函数
    
    Args:
        results: 任务结果数据
        report_type: 报告类型 ('scorecard' 或 'rule_mining')
        title: 报告标题
        ai_analysis: AI分析摘要
        config: 任务结果配置
        
    Returns:
        Markdown格式的报告字符串
    """
    generator = MarkdownReportGenerator()
    return generator.generate_report(
        results=results,
        report_type=report_type,
        title=title,
        ai_analysis=ai_analysis,
        config=config
    )
