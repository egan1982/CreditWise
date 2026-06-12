# -*- coding: utf-8 -*-
"""
Task Result Storage

将完整的任务执行结果保存到文件系统。
支持JSON（可序列化数据）和Pickle（DataFrame等复杂对象）。
"""

import json
import pickle
import shutil
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class TaskResultStorage:
    """任务结果文件存储
    
    将完整的任务执行结果保存到文件系统。
    支持JSON（可序列化数据）和Pickle（DataFrame等复杂对象）。
    
    目录结构:
        {base_dir}/
        └── {record_id}/
            ├── result.json      # JSON可序列化的结果
            ├── outputs.pkl      # 复杂对象（DataFrame等）
            └── metadata.json    # 元数据
    
    使用示例:
        storage = TaskResultStorage("./task_results")
        
        # 保存结果
        path = storage.save_result(
            record_id="rec-123",
            result={"model_metrics": {...}, "dataframe": df},
            metadata={"task_type": "scorecard_dev"}
        )
        
        # 加载结果
        result = storage.load_result("rec-123")
    """
    
    def __init__(self, base_dir: str = "./task_results"):
        """初始化存储
        
        Args:
            base_dir: 基础目录路径
        """
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"TaskResultStorage initialized at: {self.base_dir}")
    
    def _validate_pickle_path(self, file_path: Path) -> bool:
        """校验pickle文件路径是否在允许的base_dir内，防止路径遍历攻击
        
        Args:
            file_path: 待加载的pickle文件路径
            
        Returns:
            True 表示路径安全，False 表示越界
        """
        real_path = file_path.resolve()
        return real_path.is_relative_to(self.base_dir)
    
    def save_result(
        self,
        record_id: str,
        result: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """保存完整结果
        
        Args:
            record_id: 记录ID
            result: 结果字典
            metadata: 元数据
            
        Returns:
            结果目录路径
        """
        result_dir = self.base_dir / record_id
        result_dir.mkdir(parents=True, exist_ok=True)
        
        # 分离可JSON序列化的数据和复杂对象
        json_result = {}
        pickle_result = {}
        
        for key, value in result.items():
            if self._is_json_serializable(value):
                json_result[key] = value
            else:
                pickle_result[key] = value
                # 在JSON结果中记录复杂对象的类型
                json_result[f"__{key}_type__"] = type(value).__name__
        
        # 保存JSON结果
        if json_result:
            json_path = result_dir / "result.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(json_result, f, ensure_ascii=False, indent=2, default=str)
        
        # 保存Pickle结果（DataFrame等）
        if pickle_result:
            pickle_path = result_dir / "outputs.pkl"
            with open(pickle_path, "wb") as f:
                pickle.dump(pickle_result, f)
        
        # 保存元数据
        meta = metadata or {}
        meta["created_at"] = datetime.now().isoformat()
        meta["has_pickle"] = bool(pickle_result)
        meta["json_keys"] = list(json_result.keys())
        meta["pickle_keys"] = list(pickle_result.keys())
        
        meta_path = result_dir / "metadata.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"Saved result for {record_id} to {result_dir}")
        return str(result_dir)
    
    def load_result(self, record_id: str) -> Optional[Dict[str, Any]]:
        """加载完整结果
        
        Args:
            record_id: 记录ID
            
        Returns:
            结果字典，不存在返回None
        """
        result_dir = self.base_dir / record_id
        if not result_dir.exists():
            logger.warning(f"Result directory not found: {result_dir}")
            return None
        
        result = {}
        
        # 加载JSON结果
        json_path = result_dir / "result.json"
        if json_path.exists():
            with open(json_path, "r", encoding="utf-8") as f:
                json_data = json.load(f)
                # 过滤掉类型标记
                result.update({
                    k: v for k, v in json_data.items()
                    if not k.startswith("__") or not k.endswith("_type__")
                })
        
        # 加载Pickle结果
        pickle_path = result_dir / "outputs.pkl"
        if pickle_path.exists():
            # 安全校验：确保文件路径在 base_dir 内
            if not self._validate_pickle_path(pickle_path):
                logger.warning(f"Security: blocked pickle load from path outside base_dir: {pickle_path}")
            else:
                with open(pickle_path, "rb") as f:
                    result.update(pickle.load(f))
        
        return result if result else None
    
    def load_json_result(self, record_id: str) -> Optional[Dict[str, Any]]:
        """仅加载JSON结果（不加载Pickle）
        
        适用于只需要查看摘要信息的场景。
        
        Args:
            record_id: 记录ID
            
        Returns:
            JSON结果字典，不存在返回None
        """
        json_path = self.base_dir / record_id / "result.json"
        if not json_path.exists():
            return None
        
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def load_metadata(self, record_id: str) -> Optional[Dict[str, Any]]:
        """加载元数据
        
        Args:
            record_id: 记录ID
            
        Returns:
            元数据字典，不存在返回None
        """
        meta_path = self.base_dir / record_id / "metadata.json"
        if not meta_path.exists():
            return None
        
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def exists(self, record_id: str) -> bool:
        """检查结果是否存在
        
        Args:
            record_id: 记录ID
            
        Returns:
            是否存在
        """
        return (self.base_dir / record_id).exists()
    
    def delete_result(self, record_id: str) -> bool:
        """删除结果
        
        Args:
            record_id: 记录ID
            
        Returns:
            是否成功
        """
        result_dir = self.base_dir / record_id
        if result_dir.exists():
            shutil.rmtree(result_dir)
            logger.info(f"Deleted result for {record_id}")
            return True
        return False
    
    def cleanup_old(self, days: int = 90) -> int:
        """清理过期结果
        
        Args:
            days: 保留天数
            
        Returns:
            清理的记录数
        """
        cutoff = datetime.now() - timedelta(days=days)
        cleaned = 0
        
        for result_dir in self.base_dir.iterdir():
            if not result_dir.is_dir():
                continue
            
            should_delete = False
            
            # 检查元数据中的创建时间
            meta_path = result_dir / "metadata.json"
            if meta_path.exists():
                try:
                    with open(meta_path, "r") as f:
                        metadata = json.load(f)
                        created_at = metadata.get("created_at")
                        if created_at:
                            created_time = datetime.fromisoformat(created_at)
                            if created_time < cutoff:
                                should_delete = True
                except Exception as e:
                    logger.warning(f"Failed to read metadata: {e}")
            
            # 回退：检查目录修改时间
            if not should_delete:
                mtime = datetime.fromtimestamp(result_dir.stat().st_mtime)
                if mtime < cutoff:
                    should_delete = True
            
            if should_delete:
                try:
                    shutil.rmtree(result_dir)
                    cleaned += 1
                except Exception as e:
                    logger.error(f"Failed to delete {result_dir}: {e}")
        
        logger.info(f"Cleaned up {cleaned} old results")
        return cleaned
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """获取存储统计
        
        Returns:
            统计信息字典
        """
        total_size = 0
        total_count = 0
        
        for result_dir in self.base_dir.iterdir():
            if result_dir.is_dir():
                total_count += 1
                for file in result_dir.rglob("*"):
                    if file.is_file():
                        total_size += file.stat().st_size
        
        return {
            "total_records": total_count,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "base_dir": str(self.base_dir)
        }
    
    def list_records(self, limit: int = 100) -> list:
        """列出所有记录ID
        
        Args:
            limit: 最大数量
            
        Returns:
            记录ID列表
        """
        records = []
        for result_dir in self.base_dir.iterdir():
            if result_dir.is_dir():
                records.append(result_dir.name)
                if len(records) >= limit:
                    break
        return records
    
    @staticmethod
    def _is_json_serializable(value: Any) -> bool:
        """检查值是否可JSON序列化
        
        Args:
            value: 要检查的值
            
        Returns:
            是否可序列化
        """
        try:
            json.dumps(value)
            return True
        except (TypeError, ValueError):
            return False


# 全局实例
_result_storage: Optional[TaskResultStorage] = None


def get_result_storage(base_dir: str = "./task_results") -> TaskResultStorage:
    """获取全局TaskResultStorage实例
    
    Args:
        base_dir: 基础目录路径
        
    Returns:
        TaskResultStorage实例
    """
    global _result_storage
    if _result_storage is None:
        _result_storage = TaskResultStorage(base_dir)
    return _result_storage


def reset_result_storage():
    """重置全局实例（仅用于测试）"""
    global _result_storage
    _result_storage = None
