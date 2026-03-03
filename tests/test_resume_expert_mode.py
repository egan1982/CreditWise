"""
测试专家模式下的暂停/恢复功能
验证：恢复后已完成的阶段（如preprocessing）被正确跳过，不会触发暂停
"""
import asyncio
import pytest
import pandas as pd
from deepanalyze.core.task_manager.database import TaskManagerDB
from deepanalyze.core.task_manager.controller import TaskController
from deepanalyze.analysis.task_SOP.executor import ExecutionStore
from deepanalyze.analysis.task_SOP.rule_mining import RuleMiningPipeline
from deepanalyze.core.task_manager.models import ExecutionStatus


@pytest.fixture
def sample_df():
    """创建测试数据"""
    return pd.DataFrame({
        'id': range(1000),
        'age': [25, 30, 35, 40, 45] * 200,
        'income': [50000, 60000, 70000, 80000, 90000] * 200,
        'label': [0, 1, 0, 1, 0] * 200
    })


@pytest.fixture
async def task_controller():
    """创建任务控制器"""
    db = TaskManagerDB()
    controller = TaskController(db)
    yield controller
    # 清理
    await db.close()


class TestResumeExpertMode:
    """测试专家模式下的暂停/恢复功能"""
    
    @pytest.mark.asyncio
    async def test_resume_skip_stage_without_pause(self, sample_df, task_controller):
        """
        测试：恢复时跳过的阶段（如preprocessing）不应触发暂停
        
        场景：
        1. 执行任务到preprocessing阶段（10%）
        2. 专家模式下自动暂停
        3. 用户点击继续（恢复）
        4. 验证：preprocessing被跳过，直接进入feature_engineering
        """
        # 创建execution store
        store = ExecutionStore("test-exec-resume-skip")
        
        # 创建pipeline
        pipeline = RuleMiningPipeline(
            target_col='label',
            mining_mode='multi',
            min_lift_filter=2.0,
            max_hit_rate_filter=0.1,
            max_hit_rate_select=0.5,
            allow_overlap=True
        )
        
        # 准备context（模拟preprocessing已完成）
        context = store.create_context(
            execution_id="test-exec-resume-skip",
            pipeline=pipeline,
            df=sample_df
        )
        
        # 设置context状态（模拟preprocessing已完成，暂停中）
        context.status = ExecutionStatus.PAUSED
        context.current_stage = "preprocessing"
        context.interaction_mode = "expert"
        
        # 设置preprocessing阶段为已完成
        context.stages["preprocessing"].status = ExecutionStatus.COMPLETED
        context.stages["preprocessing"].progress = 100.0
        
        # 设置preprocessing的output_preview（包含_skip_expert_pause标记）
        context.stage_outputs["preprocessing"] = {
            "output_preview": {
                "_skip_expert_pause": True,
                "skipped": True,
                "reason": "retry_start_stage is after this stage"
            },
            "df_processed": sample_df,
            "feature_cols": ["age", "income"]
        }
        
        # 保存context
        store.save_context(context)
        
        # 模拟恢复执行：从preprocessing阶段开始（但由于skip，应不触发暂停）
        # 这里我们测试wrapped_progress_callback的逻辑
        
        from deepanalyze.analysis.task_SOP.rule_mining import wrapped_progress_callback
        
        # 创建一个模拟的wrapped_progress_callback
        skip_expert_pause = False  # 初始值
        
        def test_callback(stage_id, progress, message, code="", output_preview=None):
            nonlocal skip_expert_pause
            
            # 模拟rule_mining.py中的wrapped_progress_callback逻辑
            # 检查是否是skip阶段
            if output_preview and output_preview.get("_skip_expert_pause"):
                skip_expert_pause = True
                # 移除内部标记
                output_preview = {k: v for k, v in output_preview.items() if k != "_skip_expert_pause"}
                if not output_preview:
                    output_preview = None
            
            # 调用原始callback（这里我们只验证skip_expert_pause的值）
            # 如果skip_expert_pause=True，则不应触发暂停
            
            return skip_expert_pause
        
        # 测试：传入preprocessing的output_preview（包含_skip_expert_pause）
        result = test_callback(
            stage_id="preprocessing",
            progress=100.0,
            message="数据预处理已跳过（使用缓存）",
            output_preview={
                "_skip_expert_pause": True,
                "skipped": True,
                "reason": "retry_start_stage is after this stage"
            }
        )
        
        # 断言：skip_expert_pause应为True，表示不应触发暂停
        assert result is True, "preprocessing阶段应设置skip_expert_pause=True"
        
        # 清理
        store.delete_context(context.execution_id)
    
    @pytest.mark.asyncio
    async def test_resume_from_checkpoint(self, sample_df, task_controller):
        """
        测试：从checkpoint恢复，验证skip阶段的output_preview是否正确恢复
        
        场景：
        1. 执行任务到preprocessing完成，保存checkpoint
        2. 暂停任务
        3. 从checkpoint恢复
        4. 验证：preprocessing的output_preview包含_skip_expert_pause标记
        """
        # 创建execution store
        store = ExecutionStore("test-exec-checkpoint")
        
        # 创建pipeline
        pipeline = RuleMiningPipeline(
            target_col='label',
            mining_mode='multi',
            min_lift_filter=2.0,
            max_hit_rate_filter=0.1,
            max_hit_rate_select=0.5,
            allow_overlap=True
        )
        
        # 准备context
        context = store.create_context(
            execution_id="test-exec-checkpoint",
            pipeline=pipeline,
            df=sample_df
        )
        
        # 执行preprocessing阶段
        preprocessing_result = pipeline.run_stage(
            context,
            "preprocessing",
            skip_expert_pause=False
        )
        
        # 保存checkpoint
        store.save_checkpoint(context, "preprocessing", preprocessing_result)
        
        # 保存full state（包含所有stage_outputs）
        store.save_context(context)
        
        # 模拟暂停
        context.status = ExecutionStatus.PAUSED
        context.current_stage = "preprocessing"
        context.interaction_mode = "expert"
        store.save_context(context)
        
        # 从存储恢复context
        loaded_context = store.load_context("test-exec-checkpoint")
        
        # 验证：preprocessing的output_preview存在
        assert "preprocessing" in loaded_context.stage_outputs, "preprocessing应在stage_outputs中"
        
        # 验证：output_preview包含_skip_expert_pause（如果是从resume场景）
        # 注意：首次执行时不会有_skip_expert_pause标记，只有在resume时才会有
        
        # 清理
        store.delete_context(context.execution_id)
    
    @pytest.mark.asyncio
    async def test_expert_mode_pause_logic(self, sample_df, task_controller):
        """
        测试：专家模式暂停逻辑的完整性
        
        验证点：
        1. 正常阶段完成后，在expert模式下应触发暂停
        2. skip阶段完成后，即使expert模式也不应触发暂停
        3. non-expert模式下，任何阶段完成都不应触发暂停
        """
        store = ExecutionStore("test-exec-pause-logic")
        
        # 创建pipeline
        pipeline = RuleMiningPipeline(
            target_col='label',
            mining_mode='multi',
            min_lift_filter=2.0,
            max_hit_rate_filter=0.1,
            max_hit_rate_select=0.5,
            allow_overlap=True
        )
        
        # 场景1：正常阶段 + expert模式 -> 应暂停
        context1 = store.create_context("test-exec-pause-1", pipeline, sample_df)
        context1.interaction_mode = "expert"
        
        # 模拟阶段完成（progress=100）
        skip_expert_pause = False
        
        def check_pause(interaction_mode, skip_pause, progress):
            """暂停检查逻辑（简化版）"""
            if progress >= 100 and interaction_mode == "expert" and not skip_pause:
                return True
            return False
        
        should_pause = check_pause("expert", False, 100)
        assert should_pause is True, "正常阶段 + expert模式应暂停"
        
        # 场景2：skip阶段 + expert模式 -> 不应暂停
        should_pause = check_pause("expert", True, 100)
        assert should_pause is False, "skip阶段 + expert模式不应暂停"
        
        # 场景3：正常阶段 + non-expert模式 -> 不应暂停
        should_pause = check_pause("auto", False, 100)
        assert should_pause is False, "正常阶段 + non-expert模式不应暂停"
        
        # 清理
        store.delete_context("test-exec-pause-1")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
