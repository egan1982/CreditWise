# -*- coding: utf-8 -*-
"""
Overall AI Analysis Service

提供任务整体 AI 分析评估服务。
支持专家模式自动触发和自动模式手动触发两种方式。
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from .database import get_task_manager_db
from .models import OverallAIAnalysis
from .task_result_config import (
    get_task_result_config, 
    TaskResultConfig,
    TabConfig
)

logger = logging.getLogger(__name__)


class OverallAnalysisService:
    """任务整体 AI 分析服务
    
    提供任务整体 AI 分析结果的完整生命周期管理：
    - 生成分析：根据任务配置构建Prompt并调用LLM
    - 保存分析：持久化存储分析结果
    - 读取分析：从数据库读取缓存的分析结果
    - 删除分析：支持删除分析结果
    
    使用示例:
        # 生成并保存分析结果
        analysis = OverallAnalysisService.generate_and_save(
            record_id="rec-abc123",
            task_type="rule_mining",
            results=execution_results,
            stages_data=stages_data
        )
        
        # 读取分析结果
        analysis = OverallAnalysisService.get_analysis("rec-abc123")
        if analysis:
            print(analysis["analysis_text"])
    """
    
    @classmethod
    def get_analysis(cls, record_id: str) -> Optional[Dict[str, Any]]:
        """获取任务整体 AI 分析结果
        
        Args:
            record_id: 任务记录ID
            
        Returns:
            分析结果字典，包含 analysis_text, model_used, task_type, created_at, updated_at
            不存在返回 None
        """
        try:
            db = get_task_manager_db()
            with db.get_session() as session:
                analysis = session.query(OverallAIAnalysis).filter_by(
                    record_id=record_id
                ).first()
                
                if not analysis:
                    return None
                
                return {
                    "analysis_text": analysis.analysis_text,
                    "model_used": analysis.model_used,
                    "task_type": analysis.task_type,
                    "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
                    "updated_at": analysis.updated_at.isoformat() if analysis.updated_at else None
                }
                
        except Exception as e:
            logger.error(f"Failed to get overall analysis: {e}")
            return None
    
    @classmethod
    def save_analysis(
        cls,
        record_id: str,
        task_type: str,
        analysis_text: str,
        model_used: Optional[str] = None
    ) -> bool:
        """保存任务整体 AI 分析结果
        
        如果已有分析结果，则更新（覆盖）。
        
        Args:
            record_id: 任务记录ID
            task_type: 任务类型
            analysis_text: AI 分析文本
            model_used: 使用的模型名称
            
        Returns:
            是否成功
        """
        try:
            db = get_task_manager_db()
            with db.get_session() as session:
                # 查找现有记录
                analysis = session.query(OverallAIAnalysis).filter_by(
                    record_id=record_id
                ).first()
                
                if analysis:
                    # 更新现有记录
                    analysis.analysis_text = analysis_text
                    analysis.model_used = model_used
                    analysis.task_type = task_type
                    analysis.updated_at = datetime.now()
                    logger.debug(f"Updated overall analysis: {record_id}")
                else:
                    # 新增记录
                    analysis = OverallAIAnalysis(
                        record_id=record_id,
                        task_type=task_type,
                        analysis_text=analysis_text,
                        model_used=model_used
                    )
                    session.add(analysis)
                    logger.debug(f"Created overall analysis: {record_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save overall analysis: {e}")
            return False
    
    @classmethod
    def delete_analysis(cls, record_id: str) -> bool:
        """删除任务整体 AI 分析结果
        
        Args:
            record_id: 任务记录ID
            
        Returns:
            是否成功
        """
        try:
            db = get_task_manager_db()
            with db.get_session() as session:
                count = session.query(OverallAIAnalysis).filter_by(
                    record_id=record_id
                ).delete()
            
            if count > 0:
                logger.info(f"Deleted overall analysis for record: {record_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete overall analysis: {e}")
            return False
    
    @classmethod
    def exists(cls, record_id: str) -> bool:
        """检查分析结果是否存在
        
        Args:
            record_id: 任务记录ID
            
        Returns:
            是否存在
        """
        try:
            db = get_task_manager_db()
            with db.get_session() as session:
                count = session.query(OverallAIAnalysis).filter_by(
                    record_id=record_id
                ).count()
                return count > 0
                
        except Exception as e:
            logger.error(f"Failed to check overall analysis existence: {e}")
            return False
    
    @classmethod
    def build_data_description(
        cls,
        task_type: str,
        results: Dict[str, Any],
        stages_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """构建AI分析的数据描述
        
        根据任务配置，从结果数据中提取关键指标，构建供AI分析的数据描述文本。
        
        Args:
            task_type: 任务类型
            results: 执行结果数据
            stages_data: 阶段数据（可选）
            
        Returns:
            数据描述文本
        """
        config = get_task_result_config(task_type)
        if not config:
            return "未找到任务配置"
        
        description_parts = []
        
        for tab in config.tabs:
            if not tab.include_in_ai_analysis:
                continue
            
            # 从results中提取数据
            tab_data = cls._extract_tab_data(tab, results, stages_data)
            if not tab_data:
                continue
            
            # 构建该Tab的描述
            tab_desc = cls._build_tab_description(tab, tab_data)
            if tab_desc:
                description_parts.append(tab_desc)
        
        return "\n\n".join(description_parts) if description_parts else "无可用数据"
    
    @classmethod
    def _extract_tab_data(
        cls,
        tab: TabConfig,
        results: Dict[str, Any],
        stages_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """从结果中提取Tab数据"""
        data_paths = tab.data_path.split(",")
        extracted = {}
        
        for path in data_paths:
            path = path.strip()
            parts = path.split(".")
            
            # 尝试从results中提取
            current = results
            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    current = None
                    break
            
            if current is not None:
                extracted[path] = current
            elif stages_data and parts[0] == "stages" and len(parts) > 1:
                # 尝试从stages_data中提取
                stage_id = parts[1]
                if stage_id in stages_data:
                    extracted[path] = stages_data[stage_id]
        
        return extracted if extracted else None
    
    @classmethod
    def _build_tab_description(
        cls,
        tab: TabConfig,
        tab_data: Dict[str, Any]
    ) -> str:
        """构建单个Tab的数据描述"""
        lines = [f"### {tab.name}"]
        
        # 根据Tab类型构建描述
        if tab.id == "sample-feature":
            lines.extend(cls._describe_sample_feature(tab_data))
        elif tab.id == "optimal":
            lines.extend(cls._describe_optimal_rules(tab_data))
        elif tab.id == "charts":
            lines.extend(cls._describe_charts(tab_data))
        elif tab.id == "validation":
            lines.extend(cls._describe_validation(tab_data))
        elif tab.id == "psi":
            lines.extend(cls._describe_psi(tab_data))
        elif tab.id == "scorecard":
            lines.extend(cls._describe_scorecard(tab_data))
        elif tab.id in ["coefficients", "iv", "selection", "statistics"]:
            lines.extend(cls._describe_generic(tab_data, tab.ai_analysis_metrics))
        else:
            # 通用描述
            lines.extend(cls._describe_generic(tab_data, tab.ai_analysis_metrics))
        
        return "\n".join(lines)
    
    @classmethod
    def _describe_sample_feature(cls, data: Dict[str, Any]) -> List[str]:
        """描述样本及特征数据"""
        lines = []
        
        # 从preprocessing或feature_engineering或data_loading中提取
        for path, content in data.items():
            if isinstance(content, dict):
                if "total_rows" in content:
                    lines.append(f"- 样本总量：{content['total_rows']}条")
                if "rows" in content and "total_rows" not in content:
                    lines.append(f"- 样本总量：{content['rows']}条")
                if "bad_rate" in content:
                    bad_rate = content['bad_rate']
                    if isinstance(bad_rate, (int, float)):
                        lines.append(f"- 坏样本率：{bad_rate*100:.2f}%")
                if "target_rate" in content and "bad_rate" not in content:
                    target_rate = content['target_rate']
                    if isinstance(target_rate, (int, float)):
                        lines.append(f"- 坏样本率：{target_rate*100:.2f}%")
                
                # 特征数量：支持多种来源
                # 1. var_filter_result.input_features (评分卡 data_loading 阶段)
                if "var_filter_result" in content:
                    var_filter = content["var_filter_result"]
                    if isinstance(var_filter, dict) and "input_features" in var_filter:
                        lines.append(f"- 原始特征数：{var_filter['input_features']}个")
                        if "output_features" in var_filter:
                            lines.append(f"- 质量筛选后特征数：{var_filter['output_features']}个")
                # 2. feature_count (规则挖掘 preprocessing 阶段)
                elif "feature_count" in content:
                    lines.append(f"- 特征数量：{content['feature_count']}个")
                # 3. features 列表长度
                elif "features" in content and isinstance(content["features"], list):
                    lines.append(f"- 特征数量：{len(content['features'])}个")
                # 4. columns 数量 (通用)
                elif "columns" in content and isinstance(content["columns"], int):
                    lines.append(f"- 列数：{content['columns']}个")
        
        return lines if lines else ["- 数据概况信息不可用"]
    
    @classmethod
    def _describe_optimal_rules(cls, data: Dict[str, Any]) -> List[str]:
        """描述最优规则数据"""
        lines = []
        
        for path, content in data.items():
            if isinstance(content, list):
                rule_count = len(content)
                lines.append(f"- 最优规则数：{rule_count}条")
                
                if rule_count > 0:
                    # 计算累计召回率
                    total_recall = sum(r.get("recall", 0) for r in content if isinstance(r, dict))
                    lines.append(f"- 累计召回率：{total_recall*100:.2f}%")
                    
                    # 计算平均提升
                    lifts = [r.get("lift", 0) for r in content if isinstance(r, dict) and r.get("lift")]
                    if lifts:
                        avg_lift = sum(lifts) / len(lifts)
                        lines.append(f"- 平均提升：{avg_lift:.2f}x")
        
        return lines if lines else ["- 规则信息不可用"]
    
    @classmethod
    def _describe_charts(cls, data: Dict[str, Any]) -> List[str]:
        """描述图表数据"""
        lines = []
        
        for path, content in data.items():
            if isinstance(content, dict):
                # 规则挖掘图表
                if "cumulative_recall" in content:
                    lines.append(f"- 累计召回率曲线数据点数：{len(content.get('cumulative_recall', []))}个")
                
                # 评分卡图表
                if "ks" in content:
                    ks = content["ks"]
                    if isinstance(ks, (int, float)):
                        lines.append(f"- KS值：{ks*100:.2f}%")
                if "auc" in content:
                    auc = content["auc"]
                    if isinstance(auc, (int, float)):
                        lines.append(f"- AUC：{auc:.4f}")
                if "gini" in content:
                    gini = content["gini"]
                    if isinstance(gini, (int, float)):
                        lines.append(f"- Gini系数：{gini*100:.2f}%")
        
        return lines if lines else ["- 图表数据不可用"]
    
    @classmethod
    def _describe_validation(cls, data: Dict[str, Any]) -> List[str]:
        """描述质量验证数据"""
        lines = []
        
        for path, content in data.items():
            if isinstance(content, dict):
                if "quality_score" in content:
                    lines.append(f"- 质量评分：{content['quality_score']}/100")
                if "checks" in content and isinstance(content["checks"], list):
                    passed = sum(1 for c in content["checks"] if c.get("passed"))
                    total = len(content["checks"])
                    lines.append(f"- 验证通过：{passed}/{total}项")
                if "issues" in content and isinstance(content["issues"], list):
                    issue_count = len(content["issues"])
                    lines.append(f"- 发现问题：{issue_count}个")
        
        return lines if lines else ["- 验证信息不可用"]
    
    @classmethod
    def _describe_psi(cls, data: Dict[str, Any]) -> List[str]:
        """描述PSI稳定性数据"""
        lines = []
        
        for path, content in data.items():
            if isinstance(content, dict):
                if "summary" in content:
                    summary = content["summary"]
                    if "avg_psi" in summary:
                        lines.append(f"- 平均PSI：{summary['avg_psi']:.4f}")
                    if "stable_count" in summary:
                        lines.append(f"- 稳定规则数：{summary['stable_count']}条")
                    if "unstable_count" in summary:
                        lines.append(f"- 不稳定规则数：{summary['unstable_count']}条")
                elif "rules" in content and isinstance(content["rules"], list):
                    stable = sum(1 for r in content["rules"] if r.get("psi", 1) < 0.25)
                    total = len(content["rules"])
                    lines.append(f"- 稳定规则占比：{stable}/{total} ({stable/total*100:.1f}%)")
        
        return lines if lines else ["- 稳定性信息不可用"]
    
    @classmethod
    def _describe_scorecard(cls, data: Dict[str, Any]) -> List[str]:
        """描述评分卡数据"""
        lines = []
        
        for path, content in data.items():
            if isinstance(content, list):
                var_count = len(set(item.get("variable") for item in content if isinstance(item, dict)))
                lines.append(f"- 入模变量数：{var_count}个")
                lines.append(f"- 评分项数：{len(content)}条")
                
                # 计算评分区间
                points = [item.get("points", 0) for item in content if isinstance(item, dict)]
                if points:
                    lines.append(f"- 单项评分区间：{min(points)} ~ {max(points)}")
        
        return lines if lines else ["- 评分卡信息不可用"]
    
    @classmethod
    def _describe_generic(cls, data: Dict[str, Any], metrics: List[str]) -> List[str]:
        """通用数据描述"""
        lines = []
        
        for path, content in data.items():
            if isinstance(content, dict):
                for metric in metrics:
                    if metric in content:
                        value = content[metric]
                        if isinstance(value, float):
                            lines.append(f"- {metric}：{value:.4f}")
                        else:
                            lines.append(f"- {metric}：{value}")
            elif isinstance(content, list):
                lines.append(f"- 数据条数：{len(content)}条")
        
        return lines if lines else ["- 数据不可用"]
    
    @classmethod
    def build_prompt(
        cls,
        task_type: str,
        data_description: str
    ) -> str:
        """构建AI分析Prompt
        
        Args:
            task_type: 任务类型
            data_description: 数据描述文本
            
        Returns:
            完整的Prompt文本
        """
        config = get_task_result_config(task_type)
        if not config:
            return f"请对以下数据进行分析评估：\n\n{data_description}"
        
        ai_config = config.ai_analysis_config
        prompt_template = ai_config.build_prompt_template()
        
        return prompt_template.replace("{data_description}", data_description)
