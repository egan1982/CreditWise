# -*- coding: utf-8 -*-
"""
Stage Result Store - 阶段结果持久化存储

提供专家模式下阶段执行结果的持久化存储：
- 保存阶段结果到文件
- 加载历史阶段结果
- 管理阶段状态机持久化
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class StageResultStore:
    """阶段结果持久化存储
    
    存储目录结构：
    workspace/{session_id}/.sop_expert/
    ├── state_machine.json          # 状态机序列化
    ├── stage_{stage_id}.json       # 阶段结果
    └── stage_{stage_id}_code.py    # 阶段代码
    """
    
    def __init__(self, workspace_dir: str):
        """初始化存储
        
        Args:
            workspace_dir: 工作区目录
        """
        self.workspace_dir = os.path.abspath(workspace_dir)
        self.store_dir = os.path.join(self.workspace_dir, ".sop_expert")
        os.makedirs(self.store_dir, exist_ok=True)
    
    # =========================================================================
    # 状态机持久化
    # =========================================================================
    
    def save_state_machine(
        self,
        session_id: str,
        state_machine_data: Dict[str, Any]
    ) -> str:
        """保存状态机
        
        Args:
            session_id: 会话ID
            state_machine_data: 状态机序列化数据
            
        Returns:
            保存的文件路径
        """
        file_path = os.path.join(self.store_dir, f"{session_id}_state_machine.json")
        
        data = {
            **state_machine_data,
            "saved_at": datetime.now().isoformat()
        }
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved state machine: {file_path}")
        return file_path
    
    def load_state_machine(self, session_id: str) -> Dict[str, Any] | None:
        """加载状态机
        
        Args:
            session_id: 会话ID
            
        Returns:
            状态机数据，不存在则返回None
        """
        file_path = os.path.join(self.store_dir, f"{session_id}_state_machine.json")
        
        if not os.path.exists(file_path):
            return None
        
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def delete_state_machine(self, session_id: str) -> bool:
        """删除状态机
        
        Args:
            session_id: 会话ID
            
        Returns:
            是否成功删除
        """
        file_path = os.path.join(self.store_dir, f"{session_id}_state_machine.json")
        
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Deleted state machine: {file_path}")
            return True
        return False
    
    # =========================================================================
    # 阶段结果持久化
    # =========================================================================
    
    def save_stage_result(
        self,
        session_id: str,
        stage_id: str,
        result: Dict[str, Any],
        code: str | None = None
    ) -> str:
        """保存阶段结果
        
        Args:
            session_id: 会话ID
            stage_id: 阶段ID
            result: 阶段结果
            code: 阶段代码（可选）
            
        Returns:
            保存的文件路径
        """
        # 保存结果JSON
        result_file = os.path.join(
            self.store_dir,
            f"{session_id}_{stage_id}.json"
        )
        
        data = {
            "session_id": session_id,
            "stage_id": stage_id,
            "result": result,
            "saved_at": datetime.now().isoformat()
        }
        
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # 保存代码文件
        if code:
            code_file = os.path.join(
                self.store_dir,
                f"{session_id}_{stage_id}_code.py"
            )
            with open(code_file, "w", encoding="utf-8") as f:
                f.write(code)
        
        logger.info(f"Saved stage result: {result_file}")
        return result_file
    
    def load_stage_result(
        self,
        session_id: str,
        stage_id: str
    ) -> Dict[str, Any] | None:
        """加载阶段结果
        
        Args:
            session_id: 会话ID
            stage_id: 阶段ID
            
        Returns:
            阶段结果数据，不存在则返回None
        """
        result_file = os.path.join(
            self.store_dir,
            f"{session_id}_{stage_id}.json"
        )
        
        if not os.path.exists(result_file):
            return None
        
        with open(result_file, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def load_stage_code(
        self,
        session_id: str,
        stage_id: str
    ) -> str | None:
        """加载阶段代码
        
        Args:
            session_id: 会话ID
            stage_id: 阶段ID
            
        Returns:
            阶段代码，不存在则返回None
        """
        code_file = os.path.join(
            self.store_dir,
            f"{session_id}_{stage_id}_code.py"
        )
        
        if not os.path.exists(code_file):
            return None
        
        with open(code_file, "r", encoding="utf-8") as f:
            return f.read()
    
    def delete_stage_result(self, session_id: str, stage_id: str) -> bool:
        """删除阶段结果
        
        Args:
            session_id: 会话ID
            stage_id: 阶段ID
            
        Returns:
            是否成功删除
        """
        result_file = os.path.join(
            self.store_dir,
            f"{session_id}_{stage_id}.json"
        )
        code_file = os.path.join(
            self.store_dir,
            f"{session_id}_{stage_id}_code.py"
        )
        
        deleted = False
        
        if os.path.exists(result_file):
            os.remove(result_file)
            deleted = True
        
        if os.path.exists(code_file):
            os.remove(code_file)
            deleted = True
        
        if deleted:
            logger.info(f"Deleted stage result: {session_id}/{stage_id}")
        
        return deleted
    
    # =========================================================================
    # 批量操作
    # =========================================================================
    
    def clear_session_results(self, session_id: str) -> int:
        """清除会话所有结果
        
        Args:
            session_id: 会话ID
            
        Returns:
            删除的文件数量
        """
        count = 0
        prefix = f"{session_id}_"
        
        for filename in os.listdir(self.store_dir):
            if filename.startswith(prefix):
                file_path = os.path.join(self.store_dir, filename)
                os.remove(file_path)
                count += 1
        
        if count > 0:
            logger.info(f"Cleared {count} files for session: {session_id}")
        
        return count
    
    def list_session_stages(self, session_id: str) -> List[str]:
        """列出会话的所有阶段
        
        Args:
            session_id: 会话ID
            
        Returns:
            阶段ID列表
        """
        stages = set()
        prefix = f"{session_id}_"
        suffix = ".json"
        
        for filename in os.listdir(self.store_dir):
            if filename.startswith(prefix) and filename.endswith(suffix):
                # 排除状态机文件
                if "_state_machine" in filename:
                    continue
                # 提取阶段ID
                stage_id = filename[len(prefix):-len(suffix)]
                stages.add(stage_id)
        
        return sorted(stages)
    
    def get_all_stage_results(
        self,
        session_id: str
    ) -> Dict[str, Dict[str, Any]]:
        """获取会话的所有阶段结果
        
        Args:
            session_id: 会话ID
            
        Returns:
            {stage_id: result_data} 字典
        """
        results = {}
        
        for stage_id in self.list_session_stages(session_id):
            result = self.load_stage_result(session_id, stage_id)
            if result:
                results[stage_id] = result
        
        return results


# =============================================================================
# 全局实例
# =============================================================================

_store_instances: Dict[str, StageResultStore] = {}


def get_stage_result_store(workspace_dir: str) -> StageResultStore:
    """获取阶段结果存储实例
    
    Args:
        workspace_dir: 工作区目录
        
    Returns:
        StageResultStore实例
    """
    abs_path = os.path.abspath(workspace_dir)
    
    if abs_path not in _store_instances:
        _store_instances[abs_path] = StageResultStore(abs_path)
    
    return _store_instances[abs_path]
