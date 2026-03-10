"""
日志管理路由
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from llm_manager_integrated.models import schemas
from llm_manager_integrated.core import crud
from llm_manager_integrated.api.responses import success_response, error_response
from ..dependencies import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/logs")
def get_logs(
    skip: int = 0,
    limit: int = 100,
    model_name: str = None,
    status: str = None,
    exclude_test_data: bool = False,
    db: Session = Depends(get_db)
):
    """获取API调用日志列表"""
    try:
        logs = crud.get_api_logs(db, skip=skip, limit=limit, model_name=model_name, status=status, exclude_test_data=exclude_test_data)
        logs_data = [log.dict() if hasattr(log, 'dict') else log for log in logs]
        return success_response(
            data=logs_data,
            message="获取日志列表成功"
        )
    except Exception as e:
        logger.error(f"获取日志失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=error_response(code=500, message="获取日志失败")
        )


@router.get("/logs/stats")
def get_log_stats(exclude_test_data: bool = False, db: Session = Depends(get_db)):
    """获取API调用统计信息"""
    try:
        stats = crud.get_api_log_stats(db, exclude_test_data=exclude_test_data)
        return success_response(
            data=stats,
            message="获取统计信息成功"
        )
    except Exception as e:
        logger.error(f"获取统计失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=error_response(code=500, message="获取统计失败")
        )


@router.delete("/logs")
def delete_old_logs(days: int = 30, db: Session = Depends(get_db)):
    """删除指定天数之前的日志"""
    try:
        deleted_count = crud.delete_api_logs(db, days=days)
        return success_response(
            data={"deleted_count": deleted_count},
            message=f"已删除 {deleted_count} 条日志"
        )
    except Exception as e:
        logger.error(f"删除日志失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=error_response(code=500, message="删除日志失败")
        )


@router.delete("/logs/test-data")
def delete_test_logs(db: Session = Depends(get_db)):
    """删除所有测试数据"""
    try:
        deleted_count = crud.delete_test_data(db)
        return success_response(
            data={"deleted_count": deleted_count},
            message=f"已删除 {deleted_count} 条测试数据"
        )
    except Exception as e:
        logger.error(f"删除测试数据失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=error_response(code=500, message="删除测试数据失败")
        )


@router.get("/logs/data-summary")
def get_data_summary_endpoint(db: Session = Depends(get_db)):
    """获取数据概况（测试数据vs真实数据）"""
    try:
        summary = crud.get_data_summary(db)
        return success_response(
            data=summary,
            message="获取数据概况成功"
        )
    except Exception as e:
        logger.error(f"获取数据概况失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=error_response(code=500, message="获取数据概况失败")
        )
