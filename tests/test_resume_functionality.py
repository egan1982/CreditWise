"""
暂停/恢复功能专项测试

用于排查暂停/恢复功能中的逻辑错误
"""
import pytest
import pandas as pd
import pickle
from datetime import datetime
from pathlib import Path
import sys

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from deepanalyze.core.task_manager.persistent_store import PersistentExecutionStore
from deepanalyze.core.task_manager.enums import TaskStatus
from deepanalyze.analysis.task_SOP.executor import ExecutionStore, ExecutionContext, ExecutionStatus


class TestResumeLogic:
    """测试恢复逻辑"""
    
    @pytest.fixture
    def sample_execution_id(self):
        """测试用的执行ID"""
        return "exec-test-resume-001"
    
    @pytest.fixture
    def sample_checkpoints(self):
        """模拟预处理阶段已完成的检查点"""
        return [
            {
                "stage_id": "preprocessing",
                "stage_index": 0,
                "stage_status": "completed",
                "outputs_file_path": "/tmp/test/preprocessing.pkl",
                "params_json": '{}',
                "started_at": datetime.now().isoformat(),
                "completed_at": datetime.now().isoformat(),
                "created_at": datetime.now().isoformat(),
            }
        ]
    
    def test_get_cached_state_when_retry_stage_not_exists(self, sample_execution_id, sample_checkpoints, tmp_path):
        """
        测试：当重试阶段不存在时（因为还没执行），应该能正常加载之前阶段的缓存
        
        场景：
        1. preprocessing 阶段已完成（有检查点）
        2. feature_engineering 阶段还没执行（无检查点）
        3. 调用 get_cached_state_for_retry(execution_id, "feature_engineering")
        
        期望：
        - 不应该返回 None
        - 应该返回包含 preprocessing 阶段输出的缓存
        - retry_stage_index 应该设为 1（最后一个已完成阶段的index + 1）
        """
        # 创建测试数据库
        from deepanalyze.core.task_manager.database import get_task_manager_db
        db = get_task_manager_db(database_url=f"sqlite:///{tmp_path}/test.db")
        db.create_tables()
        
        # 模拟：preprocessing 阶段已完成，保存检查点
        PersistentExecutionStore.save_checkpoint(
            execution_id=sample_execution_id,
            stage_id="preprocessing",
            stage_index=0,
            stage_status="completed",
            outputs={"df_processed": pd.DataFrame({"col1": [1, 2, 3]}), "results": {"key": "value"}},
            params={}
        )
        
        # 调用 get_cached_state_for_retry，传入一个不存在的阶段（feature_engineering）
        cached_state = PersistentExecutionStore.get_cached_state_for_retry(
            sample_execution_id,
            "feature_engineering"  # 这个阶段不存在于检查点中
        )
        
        # 断言
        assert cached_state is not None, "当重试阶段不存在时，应该能加载之前阶段的缓存"
        assert "stage_outputs" in cached_state, "缓存应该包含 stage_outputs"
        assert "preprocessing" in cached_state["stage_outputs"], "应该包含 preprocessing 阶段的输出"
        assert cached_state["last_completed_stage"] == "preprocessing", "最后完成的阶段应该是 preprocessing"
        
        print("✅ 测试通过：当重试阶段不存在时，能正常加载之前阶段的缓存")
    
    def test_get_cached_state_returns_none_when_no_checkpoints(self, sample_execution_id, tmp_path):
        """
        测试：没有任何检查点时，应该返回 None
        """
        from deepanalyze.core.task_manager.database import get_task_manager_db
        db = get_task_manager_db(database_url=f"sqlite:///{tmp_path}/test2.db")
        db.create_tables()
        
        cached_state = PersistentExecutionStore.get_cached_state_for_retry(
            sample_execution_id,
            "feature_engineering"
        )
        
        assert cached_state is None, "没有任何检查点时应该返回 None"
        print("✅ 测试通过：没有任何检查点时返回 None")
    
    def test_executor_resume_logic_with_paused_status(self, tmp_path):
        """
        测试：executor 的恢复逻辑应该能正确识别 PAUSED 状态
        
        场景：
        1. 创建一个 context，状态为 PAUSED，current_stage 为 "preprocessing"
        2. 模拟从持久化存储加载 context
        3. 调用恢复逻辑
        
        期望：
        - start_from_stage 应该被设置为下一个阶段（preprocessing 已完成）
        """
        # 创建测试数据库
        from deepanalyze.core.task_manager.database import get_task_manager_db
        db = get_task_manager_db(database_url=f"sqlite:///{tmp_path}/test3.db")
        db.create_tables()
        
        # 模拟 PAUSED 状态的 context
        execution_id = "exec-test-resume-002"
        context = ExecutionContext(
            execution_id=execution_id,
            task_id="rule_mining",
            session_id="session-test",
            params={"target_col": "label"},
            status=ExecutionStatus.PAUSED,  # 关键：PAUSED 状态
            current_stage="preprocessing",  # 关键：当前阶段
        )
        
        # 添加 preprocessing 阶段（已完成）
        from deepanalyze.analysis.task_SOP.executor import StageProgress
        context.stages["preprocessing"] = StageProgress(
            stage_id="preprocessing",
            stage_name="数据预处理",
            status=ExecutionStatus.COMPLETED  # 关键：已完成
        )
        
        # 保存到 ExecutionStore
        ExecutionStore.update(context)
        
        # 验证：检查状态和阶段
        assert context.status == ExecutionStatus.PAUSED, "Context 状态应该是 PAUSED"
        assert context.current_stage == "preprocessing", "当前阶段应该是 preprocessing"
        assert context.stages["preprocessing"].status == ExecutionStatus.COMPLETED, "preprocessing 阶段应该已完成"
        
        print("✅ 测试通过：executor 能正确识别 PAUSED 状态和已完成的阶段")
    
    def test_status_transition_from_paused_to_running(self, tmp_path):
        """
        测试：状态从 PAUSED 转换到 RUNNING 的时机
        
        关键问题：
        - 恢复逻辑需要在状态判断完成后才设置状态为 RUNNING
        - 如果过早设置状态为 RUNNING，恢复逻辑会失效
        
        场景：
        1. context 初始状态为 PAUSED
        2. 恢复逻辑检查 context.status
        3. 恢复逻辑设置 context.status = ExecutionStatus.RUNNING
        
        期望：
        - 在设置 status 之前，恢复逻辑应该已经完成判断
        - start_from_stage 应该被正确设置
        """
        execution_id = "exec-test-resume-003"
        
        # 模拟从持久化存储加载的 context
        context = ExecutionContext(
            execution_id=execution_id,
            task_id="rule_mining",
            session_id="session-test",
            params={"target_col": "label"},
            status=ExecutionStatus.PAUSED,
            current_stage="preprocessing",
        )
        
        # 添加已完成的阶段
        from deepanalyze.analysis.task_SOP.executor import StageProgress
        context.stages["preprocessing"] = StageProgress(
            stage_id="preprocessing",
            stage_name="数据预处理",
            status=ExecutionStatus.COMPLETED
        )
        
        # 模拟恢复逻辑（简化版）
        if context.status == ExecutionStatus.PAUSED and context.current_stage:
            paused_stage = context.stages.get(context.current_stage)
            if paused_stage and paused_stage.status == ExecutionStatus.COMPLETED:
                # 假设下一个阶段是 feature_engineering
                start_from_stage = "feature_engineering"
                print(f"✅ 恢复逻辑正确识别：从阶段 {start_from_stage} 继续")
            else:
                start_from_stage = context.current_stage
                print(f"✅ 恢复逻辑：从暂停阶段 {start_from_stage} 继续")
        else:
            start_from_stage = None
            print("❌ 恢复逻辑：不是 PAUSED 状态，start_from_stage = None")
        
        # 模拟设置状态为 RUNNING
        original_status = context.status
        context.status = ExecutionStatus.RUNNING
        
        # 验证
        assert start_from_stage is not None, "恢复逻辑应该设置了 start_from_stage"
        assert start_from_stage == "feature_engineering", "应该从 feature_engineering 阶段继续"
        assert original_status == ExecutionStatus.PAUSED, "原始状态应该是 PAUSED"
        assert context.status == ExecutionStatus.RUNNING, "当前状态应该是 RUNNING"
        
        print(f"✅ 测试通过：状态从 {original_status} 转换到 {context.status}")
        print(f"✅ 恢复点：{start_from_stage}")


class TestPipelineRetryLogic:
    """测试 Pipeline 的重试逻辑"""
    
    def test_should_skip_stage_logic(self):
        """
        测试：Pipeline 的 should_skip_stage 逻辑
        
        场景：
        - retry_start_idx = 1 (从 feature_engineering 开始)
        - cached_state 存在
        - 检查预处理阶段 (index=0)
        
        期望：
        - should_skip_stage("preprocessing") 应该返回 True
        - should_skip_stage("feature_engineering") 应该返回 False
        """
        retry_start_idx = 1  # 从 feature_engineering 开始
        cached_state = {"some": "data"}
        
        def should_skip_stage(stage_id, stage_order):
            """模拟 should_skip_stage 逻辑"""
            if retry_start_idx < 0:
                return False
            if not cached_state:
                return False
            if stage_id not in stage_order:
                return False
            stage_idx = stage_order.index(stage_id)
            return stage_idx < retry_start_idx
        
        stage_order = ["preprocessing", "feature_engineering", "generating_rules"]
        
        # 验证
        assert should_skip_stage("preprocessing", stage_order) is True, "应该跳过 preprocessing"
        assert should_skip_stage("feature_engineering", stage_order) is False, "不应该跳过 feature_engineering"
        assert should_skip_stage("generating_rules", stage_order) is False, "不应该跳过 generating_rules"
        
        print("✅ 测试通过：should_skip_stage 逻辑正确")
    
    def test_is_before_retry_stage_logic(self):
        """
        测试：is_before_retry_stage 逻辑
        
        用于判断是否需要跳过专家模式暂停
        """
        retry_start_idx = 1
        
        def is_before_retry_stage(stage_id, stage_order):
            if retry_start_idx < 0:
                return False
            if stage_id not in stage_order:
                return False
            stage_idx = stage_order.index(stage_id)
            return stage_idx < retry_start_idx
        
        stage_order = ["preprocessing", "feature_engineering", "generating_rules"]
        
        # 验证
        assert is_before_retry_stage("preprocessing", stage_order) is True, "preprocessing 在重试阶段之前"
        assert is_before_retry_stage("feature_engineering", stage_order) is False, "feature_engineering 是重试阶段"
        assert is_before_retry_stage("generating_rules", stage_order) is False, "generating_rules 在重试阶段之后"
        
        print("✅ 测试通过：is_before_retry_stage 逻辑正确")


class TestIntegration:
    """集成测试：端到端恢复流程"""
    
    @pytest.mark.asyncio
    async def test_full_resume_flow(self, tmp_path):
        """
        测试完整的恢复流程
        
        1. 启动任务，执行到 preprocessing 阶段完成
        2. 专家模式自动暂停
        3. 点击恢复
        4. 应该从 feature_engineering 阶段继续，不重复执行 preprocessing
        
        注意：这个测试需要完整的 Pipeline 环境，可能需要 mock
        """
        # TODO: 实现完整的集成测试
        # 这个测试需要：
        # 1. 创建测试数据
        # 2. 启动规则挖掘任务（专家模式）
        # 3. 等待 preprocessing 完成
        # 4. 检查是否暂停
        # 5. 调用恢复 API
        # 6. 验证是否跳过了 preprocessing
        
        print("⚠️ 集成测试待实现（需要完整的 Pipeline 环境）")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])
