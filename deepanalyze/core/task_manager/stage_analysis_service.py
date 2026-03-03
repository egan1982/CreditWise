# -*- coding: utf-8 -*-
"""
Stage AI Analysis Service

提供阶段 AI 分析结果的持久化存储服务。
支持保存、读取、删除分析结果，与任务生命周期绑定。
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from .database import get_task_manager_db
from .models import StageAIAnalysis

logger = logging.getLogger(__name__)


class StageAnalysisService:
    """阶段 AI 分析服务
    
    提供阶段 AI 分析结果的完整生命周期管理：
    - 保存分析：阶段完成后保存 AI 生成的分析文本
    - 读取分析：从数据库读取缓存的分析结果
    - 删除分析：支持删除单个阶段或整个任务的分析
    - 批量读取：获取任务所有阶段的分析结果
    
    使用示例:
        # 保存分析结果
        StageAnalysisService.save_analysis(
            record_id="rec-abc123",
            stage_id="data_loading",
            analysis_text="数据质量良好，缺失率低于5%...",
            model_used="deepseek-chat"
        )
        
        # 读取分析结果
        analysis = StageAnalysisService.get_analysis("rec-abc123", "data_loading")
        if analysis:
            print(analysis["analysis_text"])
        
        # 删除任务所有分析（任务删除时调用）
        StageAnalysisService.delete_analysis("rec-abc123")
    """
    
    @classmethod
    def get_analysis(
        cls,
        record_id: str,
        stage_id: str
    ) -> Optional[Dict[str, Any]]:
        """获取阶段 AI 分析结果
        
        Args:
            record_id: 任务记录ID
            stage_id: 阶段ID
            
        Returns:
            分析结果字典，包含 analysis_text, model_used, created_at, updated_at
            不存在返回 None
        """
        try:
            db = get_task_manager_db()
            with db.get_session() as session:
                analysis = session.query(StageAIAnalysis).filter_by(
                    record_id=record_id,
                    stage_id=stage_id
                ).first()
                
                if not analysis:
                    return None
                
                return {
                    "analysis_text": analysis.analysis_text,
                    "model_used": analysis.model_used,
                    "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
                    "updated_at": analysis.updated_at.isoformat() if analysis.updated_at else None
                }
                
        except Exception as e:
            logger.error(f"Failed to get stage analysis: {e}")
            return None
    
    @classmethod
    def save_analysis(
        cls,
        record_id: str,
        stage_id: str,
        analysis_text: str,
        model_used: Optional[str] = None
    ) -> bool:
        """保存阶段 AI 分析结果
        
        如果该阶段已有分析结果，则更新（覆盖）。
        
        Args:
            record_id: 任务记录ID
            stage_id: 阶段ID
            analysis_text: AI 分析文本
            model_used: 使用的模型名称
            
        Returns:
            是否成功
        """
        try:
            db = get_task_manager_db()
            with db.get_session() as session:
                # 查找现有记录
                analysis = session.query(StageAIAnalysis).filter_by(
                    record_id=record_id,
                    stage_id=stage_id
                ).first()
                
                if analysis:
                    # 更新现有记录
                    analysis.analysis_text = analysis_text
                    analysis.model_used = model_used
                    analysis.updated_at = datetime.now()
                    logger.debug(f"Updated stage analysis: {record_id}/{stage_id}")
                else:
                    # 新增记录
                    analysis = StageAIAnalysis(
                        record_id=record_id,
                        stage_id=stage_id,
                        analysis_text=analysis_text,
                        model_used=model_used
                    )
                    session.add(analysis)
                    logger.debug(f"Created stage analysis: {record_id}/{stage_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save stage analysis: {e}")
            return False
    
    @classmethod
    def delete_analysis(
        cls,
        record_id: str,
        stage_id: Optional[str] = None
    ) -> int:
        """删除阶段 AI 分析结果
        
        Args:
            record_id: 任务记录ID
            stage_id: 阶段ID（为空则删除该任务所有阶段的分析）
            
        Returns:
            删除的记录数
        """
        try:
            db = get_task_manager_db()
            with db.get_session() as session:
                query = session.query(StageAIAnalysis).filter_by(record_id=record_id)
                if stage_id:
                    query = query.filter_by(stage_id=stage_id)
                
                count = query.delete()
            
            if count > 0:
                logger.info(f"Deleted {count} stage analysis for record: {record_id}" + 
                           (f", stage: {stage_id}" if stage_id else ""))
            return count
            
        except Exception as e:
            logger.error(f"Failed to delete stage analysis: {e}")
            return 0
    
    @classmethod
    def get_all_analyses_for_record(
        cls,
        record_id: str
    ) -> List[Dict[str, Any]]:
        """获取任务所有阶段的 AI 分析结果
        
        Args:
            record_id: 任务记录ID
            
        Returns:
            分析结果列表，每项包含 stage_id, analysis_text, model_used, created_at, updated_at
        """
        try:
            db = get_task_manager_db()
            with db.get_session() as session:
                analyses = session.query(StageAIAnalysis).filter_by(
                    record_id=record_id
                ).all()
                
                return [
                    {
                        "stage_id": a.stage_id,
                        "analysis_text": a.analysis_text,
                        "model_used": a.model_used,
                        "created_at": a.created_at.isoformat() if a.created_at else None,
                        "updated_at": a.updated_at.isoformat() if a.updated_at else None
                    }
                    for a in analyses
                ]
                
        except Exception as e:
            logger.error(f"Failed to get all analyses for record: {e}")
            return []
    
    @classmethod
    def exists(cls, record_id: str, stage_id: str) -> bool:
        """检查分析结果是否存在
        
        Args:
            record_id: 任务记录ID
            stage_id: 阶段ID
            
        Returns:
            是否存在
        """
        try:
            db = get_task_manager_db()
            with db.get_session() as session:
                count = session.query(StageAIAnalysis).filter_by(
                    record_id=record_id,
                    stage_id=stage_id
                ).count()
                return count > 0
                
        except Exception as e:
            logger.error(f"Failed to check analysis existence: {e}")
            return False
