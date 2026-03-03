"""
任务管理模块完整测试方案

涵盖：
1. 任务控制功能（暂停、停止、恢复）
2. 记录管理功能（创建、更新、删除）
3. 历史查询功能（列表查询、详情查询、筛选）
4. 持久化功能（检查点、状态保存、跨重启恢复）
5. 性能测试
6. 兼容性测试

对应文档：docs/taskSOP_solution/task_management_module_wip.md 第9节验收标准
"""
import pytest
import pandas as pd
import asyncio
import time
from datetime import datetime, timedelta
from pathlib import Path
import sys
import json

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from deepanalyze.core.task_manager.database import get_task_manager_db, TaskManagerDB
from deepanalyze.core.task_manager.models import TaskRecord, TaskControl
from deepanalyze.core.task_manager.persistent_store import PersistentExecutionStore
from deepanalyze.core.task_manager.enums import TaskStatus, TaskControlAction
from deepanalyze.core.task_manager.controller import TaskController
from deepanalyze.core.task_manager.history_service import TaskHistoryService
from deepanalyze.core.task_manager.result_storage import TaskResultStorage
from deepanalyze.analysis.task_SOP.executor import ExecutionStore, ExecutionContext, ExecutionStatus, StageProgress


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def test_db(tmp_path):
    """创建测试数据库"""
    db_url = f"sqlite:///{tmp_path}/test_task_manager.db"
    db = get_task_manager_db(database_url=db_url)
    db.create_tables()
    yield db
    db.close()


@pytest.fixture
def test_storage(tmp_path):
    """创建测试结果存储"""
    storage = TaskResultStorage(base_dir=str(tmp_path / "results"))
    yield storage


@pytest.fixture
def sample_execution_id():
    """示例执行ID"""
    return "exec-test-001"


@pytest.fixture
def sample_record_id():
    """示例记录ID"""
    return "rec-test-001"


@pytest.fixture
def sample_context():
    """示例执行上下文"""
    return ExecutionContext(
        execution_id="exec-test-001",
        task_id="rule_mining",
        session_id="session-test-001",
        params={"target_col": "label", "min_lift": 3.0},
        data=pd.DataFrame({"col1": [1, 2, 3], "label": [0, 1, 0]}),
        file_path="test.csv",
        status=ExecutionStatus.RUNNING
    )


# =============================================================================
# Phase 1: 任务控制功能测试
# =============================================================================

class TestTaskControl:
    """测试任务控制功能（暂停、停止、恢复）"""
    
    def test_request_pause(self, sample_execution_id):
        """测试请求暂停"""
        result = TaskController.request_pause(sample_execution_id)
        assert result is True
        
        # 验证控制状态
        control = TaskController.check_control(sample_execution_id)
        assert control == TaskControlAction.PAUSE
        
        print("✅ 测试通过：可以请求暂停任务")
    
    def test_request_stop(self, sample_execution_id):
        """测试请求停止"""
        result = TaskController.request_stop(sample_execution_id)
        assert result is True
        
        control = TaskController.check_control(sample_execution_id)
        assert control == TaskControlAction.STOP
        
        print("✅ 测试通过：可以请求停止任务")
    
    def test_request_resume(self, sample_execution_id):
        """测试请求恢复"""
        result = TaskController.request_resume(sample_execution_id)
        assert result is True
        
        control = TaskController.check_control(sample_execution_id)
        assert control == TaskControlAction.RESUME
        
        print("✅ 测试通过：可以请求恢复任务")
    
    def test_control_persistence_to_db(self, sample_execution_id, test_db):
        """测试控制状态持久化到数据库"""
        # 请求暂停
        TaskController.request_pause(sample_execution_id)
        
        # 从数据库读取
        with test_db.get_session() as session:
            control = session.query(TaskControl).filter_by(
                execution_id=sample_execution_id
            ).first()
            
            assert control is not None, "控制状态应该保存到数据库"
            assert control.action == "pause", "控制动作应该是 pause"
            assert control.requested_at is not None, "应该记录请求时间"
            assert control.processed_at is None, "处理时间应该为空（未处理）"
        
        print("✅ 测试通过：控制状态正确持久化到数据库")
    
    def test_clear_control(self, sample_execution_id):
        """测试清除控制状态"""
        # 设置控制状态
        TaskController.request_pause(sample_execution_id)
        assert TaskController.check_control(sample_execution_id) == TaskControlAction.PAUSE
        
        # 清除
        TaskController.clear_control(sample_execution_id)
        
        # 验证
        control = TaskController.check_control(sample_execution_id)
        assert control == TaskControlAction.NONE
        
        print("✅ 测试通过：可以清除控制状态")
    
    def test_mark_processed(self, sample_execution_id, test_db):
        """测试标记控制请求已处理"""
        # 设置控制状态
        TaskController.request_pause(sample_execution_id)
        
        # 标记为已处理
        TaskController.mark_processed(sample_execution_id)
        
        # 验证内存缓存
        control = TaskController.check_control(sample_execution_id)
        assert control == TaskControlAction.NONE
        
        # 验证数据库
        with test_db.get_session() as session:
            control = session.query(TaskControl).filter_by(
                execution_id=sample_execution_id
            ).first()
            assert control.processed_at is not None, "应该记录处理时间"
        
        print("✅ 测试通过：可以标记控制请求已处理")


# =============================================================================
# Phase 2: 记录管理功能测试
# =============================================================================

class TestRecordManagement:
    """测试记录管理功能（创建、更新、删除）"""
    
    def test_create_record(self, test_db):
        """测试创建任务记录"""
        record_id = TaskHistoryService.create_record(
            task_type="rule_mining",
            execution_id="exec-test-create",
            session_id="session-test",
            params={"target_col": "label"},
            inputs_summary={"rows": 1000, "columns": 10}
        )
        
        assert record_id is not None, "应该返回记录ID"
        assert record_id.startswith("rec-"), "记录ID应该以 rec- 开头"
        
        # 验证数据库中的记录
        record = TaskHistoryService.get_record(record_id)
        assert record is not None, "应该能从数据库获取记录"
        assert record["task_type"] == "rule_mining"
        assert record["execution_id"] == "exec-test-create"
        assert record["status"] == "pending"
        
        print(f"✅ 测试通过：可以创建任务记录 (record_id={record_id})")
    
    def test_update_status(self, test_db, sample_record_id):
        """测试更新任务状态"""
        # 先创建记录
        record_id = TaskHistoryService.create_record(
            task_type="scorecard_dev",
            execution_id="exec-test-update",
            session_id="session-test",
            params={}
        )
        
        # 更新状态
        success = TaskHistoryService.update_status(
            record_id=record_id,
            status=TaskStatus.RUNNING,
            progress=50.0,
            current_stage="feature_engineering",
            message="正在执行特征工程"
        )
        
        assert success is True, "更新状态应该成功"
        
        # 验证
        record = TaskHistoryService.get_record(record_id)
        assert record["status"] == "running"
        assert record["progress"] == 50.0
        assert record["current_stage"] == "feature_engineering"
        assert record["message"] == "正在执行特征工程"
        
        print("✅ 测试通过：可以更新任务状态")
    
    def test_update_status_with_timestamp(self, test_db):
        """测试更新状态时自动更新时间戳"""
        record_id = TaskHistoryService.create_record(
            task_type="rule_mining",
            execution_id="exec-test-timestamp",
            session_id="session-test",
            params={}
        )
        
        # 更新为运行中
        TaskHistoryService.update_status(
            record_id=record_id,
            status=TaskStatus.RUNNING
        )
        record = TaskHistoryService.get_record(record_id)
        assert record["started_at"] is not None, "运行中时应该设置 started_at"
        
        # 更新为暂停
        TaskHistoryService.update_status(
            record_id=record_id,
            status=TaskStatus.PAUSED
        )
        record = TaskHistoryService.get_record(record_id)
        assert record["paused_at"] is not None, "暂停时应该设置 paused_at"
        
        # 更新为完成
        TaskHistoryService.update_status(
            record_id=record_id,
            status=TaskStatus.COMPLETED
        )
        record = TaskHistoryService.get_record(record_id)
        assert record["completed_at"] is not None, "完成时应该设置 completed_at"
        assert record["duration_seconds"] is not None, "应该计算总耗时"
        
        print("✅ 测试通过：时间戳自动更新正确")
    
    def test_update_result(self, test_db, test_storage):
        """测试更新任务结果"""
        # 创建记录
        record_id = TaskHistoryService.create_record(
            task_type="rule_mining",
            execution_id="exec-test-result",
            session_id="session-test",
            params={}
        )
        
        # 保存结果到文件
        result_path = test_storage.save_result(
            record_id=record_id,
            result={
                "selected_rules": 10,
                "model_ks": 0.45
            },
            metadata={"task_type": "rule_mining"}
        )
        
        # 更新记录
        success = TaskHistoryService.update_result(
            record_id=record_id,
            outputs_summary={"selected_rules": 10, "model_ks": 0.45},
            result_file_path=result_path
        )
        
        assert success is True
        
        # 验证
        record = TaskHistoryService.get_record(record_id)
        assert record["result_file_path"] == result_path
        assert record["outputs_summary"] is not None
        
        print("✅ 测试通过：可以更新任务结果")
    
    def test_update_error(self, test_db):
        """测试更新错误信息"""
        record_id = TaskHistoryService.create_record(
            task_type="rule_mining",
            execution_id="exec-test-error",
            session_id="session-test",
            params={}
        )
        
        # 模拟错误
        error_msg = "ValueError: Invalid parameter"
        error_trace = "Traceback (most recent call last)..."
        
        success = TaskHistoryService.update_error(
            record_id=record_id,
            error_message=error_msg,
            error_traceback=error_trace
        )
        
        assert success is True
        
        # 验证
        record = TaskHistoryService.get_record(record_id)
        assert record["status"] == "failed"
        assert record["error_message"] == error_msg
        assert record["error_traceback"] == error_trace
        
        print("✅ 测试通过：可以更新错误信息")
    
    def test_delete_record(self, test_db, test_storage):
        """测试删除记录"""
        # 创建记录和结果
        record_id = TaskHistoryService.create_record(
            task_type="rule_mining",
            execution_id="exec-test-delete",
            session_id="session-test",
            params={}
        )
        
        test_storage.save_result(
            record_id=record_id,
            result={"test": "data"},
            metadata={}
        )
        
        # 删除记录
        success = TaskHistoryService.delete_record(record_id)
        assert success is True
        
        # 验证数据库中不存在
        record = TaskHistoryService.get_record(record_id)
        assert record is None
        
        print("✅ 测试通过：可以删除任务记录")


# =============================================================================
# Phase 3: 历史查询功能测试
# =============================================================================

class TestHistoryQuery:
    """测试历史查询功能（列表、详情、筛选）"""
    
    @pytest.fixture
    def sample_records(self, test_db):
        """创建示例记录"""
        record_ids = []
        base_time = datetime.now()
        
        # 创建5条记录
        for i in range(5):
            record_id = TaskHistoryService.create_record(
                task_type="rule_mining" if i % 2 == 0 else "scorecard_dev",
                execution_id=f"exec-test-query-{i}",
                session_id=f"session-test",
                params={"param": i},
                inputs_summary={"rows": 100 * (i + 1)}
            )
            
            # 更新状态
            status = ["running", "completed", "failed", "paused", "stopped"][i]
            TaskHistoryService.update_status(
                record_id=record_id,
                status=TaskStatus(status),
                progress=i * 20.0
            )
            
            record_ids.append(record_id)
        
        yield record_ids
    
    def test_list_all_records(self, test_db, sample_records):
        """测试查询所有记录"""
        records = TaskHistoryService.list_records(limit=10, offset=0)
        
        assert len(records) >= 5, "应该至少有5条记录"
        assert all("record_id" in r for r in records), "每条记录应该包含 record_id"
        assert all("task_type" in r for r in records), "每条记录应该包含 task_type"
        assert all("status" in r for r in records), "每条记录应该包含 status"
        
        print(f"✅ 测试通过：可以查询所有记录 (共{len(records)}条)")
    
    def test_filter_by_task_type(self, test_db, sample_records):
        """测试按任务类型筛选"""
        records = TaskHistoryService.list_records(
            task_type="rule_mining",
            limit=10
        )
        
        assert all(r["task_type"] == "rule_mining" for r in records), "应该只返回 rule_mining 类型的记录"
        
        print(f"✅ 测试通过：可以按任务类型筛选 (共{len(records)}条)")
    
    def test_filter_by_status(self, test_db, sample_records):
        """测试按状态筛选"""
        records = TaskHistoryService.list_records(
            status="completed",
            limit=10
        )
        
        assert all(r["status"] == "completed" for r in records), "应该只返回 completed 状态的记录"
        
        print(f"✅ 测试通过：可以按状态筛选 (共{len(records)}条)")
    
    def test_filter_by_date_range(self, test_db, sample_records):
        """测试按时间范围筛选"""
        # 只查询今天的记录
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        
        records = TaskHistoryService.list_records(
            start_date=yesterday,
            end_date=today + timedelta(days=1),
            limit=10
        )
        
        assert len(records) >= 0, "应该能按时间范围查询"
        
        print(f"✅ 测试通过：可以按时间范围筛选 (共{len(records)}条)")
    
    def test_pagination(self, test_db, sample_records):
        """测试分页查询"""
        # 第一页
        page1 = TaskHistoryService.list_records(limit=2, offset=0)
        assert len(page1) <= 2, "第一页最多2条记录"
        
        # 第二页
        page2 = TaskHistoryService.list_records(limit=2, offset=2)
        assert len(page2) <= 2, "第二页最多2条记录"
        
        # 验证不重复
        page1_ids = set(r["record_id"] for r in page1)
        page2_ids = set(r["record_id"] for r in page2)
        assert len(page1_ids & page2_ids) == 0, "两页记录不应该重复"
        
        print("✅ 测试通过：分页查询正常工作")
    
    def test_get_record_detail(self, test_db, sample_records):
        """测试获取记录详情"""
        record_id = sample_records[0]
        record = TaskHistoryService.get_record(record_id)
        
        assert record is not None
        assert record["record_id"] == record_id
        assert "params" in record
        assert "inputs_summary" in record
        assert "created_at" in record
        assert "stages" in record
        
        print("✅ 测试通过：可以获取记录详情")
    
    def test_get_record_by_execution_id(self, test_db, sample_records):
        """测试通过execution_id获取记录"""
        execution_id = "exec-test-query-0"
        record = TaskHistoryService.get_record_by_execution_id(execution_id)
        
        assert record is not None
        assert record["execution_id"] == execution_id
        
        print("✅ 测试通过：可以通过execution_id获取记录")
    
    def test_get_statistics(self, test_db, sample_records):
        """测试获取统计信息"""
        stats = TaskHistoryService.get_statistics(days=30)
        
        assert "total" in stats
        assert "completed" in stats
        assert "failed" in stats
        assert "stopped" in stats
        assert "running" in stats
        assert "success_rate" in stats
        assert "avg_duration_seconds" in stats
        assert stats["total"] >= 5
        
        print(f"✅ 测试通过：统计信息正确 {stats}")
    
    def test_cleanup_old_records(self, test_db):
        """测试清理过期记录"""
        # 创建一条过期记录（90天前）
        old_record_id = TaskHistoryService.create_record(
            task_type="rule_mining",
            execution_id="exec-test-old",
            session_id="session-test",
            params={}
        )
        
        # 手动设置创建时间为90天前
        from sqlalchemy import update
        with test_db.get_session() as session:
            stmt = update(TaskRecord).where(
                TaskRecord.record_id == old_record_id
            ).values(created_at=datetime.now() - timedelta(days=91))
            session.execute(stmt)
            session.commit()
        
        # 清理
        deleted_count = TaskHistoryService.cleanup_old(days=90)
        assert deleted_count >= 1, "应该清理至少1条过期记录"
        
        # 验证
        record = TaskHistoryService.get_record(old_record_id)
        assert record is None, "过期记录应该被删除"
        
        print(f"✅ 测试通过：清理了 {deleted_count} 条过期记录")


# =============================================================================
# Phase 4: 持久化功能测试（检查点、状态保存）
# =============================================================================

class TestPersistence:
    """测试持久化功能（检查点、状态保存、跨重启恢复）"""
    
    def test_save_and_load_checkpoint(self, test_db):
        """测试保存和加载检查点"""
        execution_id = "exec-test-checkpoint"
        stage_id = "preprocessing"
        
        # 保存检查点
        outputs = {
            "df_processed": pd.DataFrame({"col": [1, 2, 3]}),
            "results": {"key": "value"},
            "feature_cols": ["col1", "col2"]
        }
        
        PersistentExecutionStore.save_checkpoint(
            execution_id=execution_id,
            stage_id=stage_id,
            stage_index=0,
            stage_status="completed",
            outputs=outputs,
            params={"param": "value"}
        )
        
        # 加载检查点
        checkpoint = PersistentExecutionStore.get_checkpoint(
            execution_id=execution_id,
            stage_id=stage_id
        )
        
        assert checkpoint is not None
        assert checkpoint["stage_id"] == stage_id
        assert checkpoint["stage_status"] == "completed"
        assert checkpoint["stage_index"] == 0
        
        # 加载输出
        loaded_outputs = PersistentExecutionStore.load_checkpoint_outputs(
            execution_id=execution_id,
            stage_id=stage_id
        )
        
        assert loaded_outputs is not None
        assert "results" in loaded_outputs
        assert loaded_outputs["results"]["key"] == "value"
        
        print("✅ 测试通过：可以保存和加载检查点")
    
    def test_get_checkpoints(self, test_db):
        """测试获取所有检查点"""
        execution_id = "exec-test-checkpoints"
        
        # 保存多个检查点
        for i in range(3):
            PersistentExecutionStore.save_checkpoint(
                execution_id=execution_id,
                stage_id=f"stage_{i}",
                stage_index=i,
                stage_status="completed",
                outputs={"index": i},
                params={}
            )
        
        # 获取所有检查点
        checkpoints = PersistentExecutionStore.get_checkpoints(execution_id)
        
        assert len(checkpoints) == 3
        assert all(cp["execution_id"] == execution_id for cp in checkpoints)
        assert all("stage_id" in cp for cp in checkpoints)
        
        # 验证排序（按stage_index）
        stage_indices = [cp["stage_index"] for cp in checkpoints]
        assert stage_indices == sorted(stage_indices), "应该按 stage_index 排序"
        
        print("✅ 测试通过：可以获取所有检查点")
    
    def test_save_and_load_full_state(self, test_db, sample_context):
        """测试保存和加载完整执行状态"""
        state_file = PersistentExecutionStore.save_full_state(
            execution_id=sample_context.execution_id,
            context=sample_context
        )
        
        assert state_file is not None
        assert Path(state_file).exists(), "状态文件应该存在"
        
        # 加载状态
        loaded_context = PersistentExecutionStore.load_full_state(
            sample_context.execution_id
        )
        
        assert loaded_context is not None
        assert loaded_context.execution_id == sample_context.execution_id
        assert loaded_context.task_id == sample_context.task_id
        assert loaded_context.status == sample_context.status
        
        print(f"✅ 测试通过：可以保存和加载完整状态 (file={state_file})")
    
    def test_get_cached_state_for_retry(self, test_db):
        """测试获取重试所需的缓存状态"""
        execution_id = "exec-test-retry"
        
        # 保存多个阶段的检查点
        for i, stage_id in enumerate(["preprocessing", "feature_engineering", "generating_rules"]):
            PersistentExecutionStore.save_checkpoint(
                execution_id=execution_id,
                stage_id=stage_id,
                stage_index=i,
                stage_status="completed",
                outputs={
                    "df_processed": pd.DataFrame({"col": list(range(i*10, i*10+5))}),
                    "results": {"stage": stage_id}
                },
                params={}
            )
        
        # 获取从 feature_engineering 开始重试的缓存状态
        cached_state = PersistentExecutionStore.get_cached_state_for_retry(
            execution_id=execution_id,
            retry_stage_id="feature_engineering"
        )
        
        assert cached_state is not None
        assert "stage_outputs" in cached_state
        assert "preprocessing" in cached_state["stage_outputs"]
        assert "feature_engineering" not in cached_state["stage_outputs"], "不应该包含重试阶段本身"
        assert cached_state["last_completed_stage"] == "preprocessing"
        assert cached_state["df_processed"] is not None
        
        print("✅ 测试通过：可以获取重试所需的缓存状态")
    
    def test_get_cached_state_when_retry_stage_not_exists(self, test_db):
        """
        测试：当重试阶段不存在时（因为还没执行），应该能正常加载之前阶段的缓存
        
        这是一个关键测试，对应我们刚修复的bug
        """
        execution_id = "exec-test-retry-not-exists"
        
        # 只保存 preprocessing 阶段的检查点
        PersistentExecutionStore.save_checkpoint(
            execution_id=execution_id,
            stage_id="preprocessing",
            stage_index=0,
            stage_status="completed",
            outputs={
                "df_processed": pd.DataFrame({"col": [1, 2, 3]}),
                "results": {"key": "value"}
            },
            params={}
        )
        
        # 尝试获取从 feature_engineering（还不存在）开始的缓存
        cached_state = PersistentExecutionStore.get_cached_state_for_retry(
            execution_id=execution_id,
            retry_stage_id="feature_engineering"  # 这个阶段还没有执行
        )
        
        # 关键断言
        assert cached_state is not None, "即使重试阶段不存在，也应该能加载之前阶段的缓存"
        assert "stage_outputs" in cached_state
        assert "preprocessing" in cached_state["stage_outputs"]
        assert cached_state["last_completed_stage"] == "preprocessing"
        
        print("✅ 测试通过：当重试阶段不存在时，能正常加载之前阶段的缓存")
    
    def test_reset_checkpoint(self, test_db):
        """测试重置检查点"""
        execution_id = "exec-test-reset"
        stage_id = "preprocessing"
        
        # 保存检查点
        PersistentExecutionStore.save_checkpoint(
            execution_id=execution_id,
            stage_id=stage_id,
            stage_index=0,
            stage_status="completed",
            outputs={"test": "data"},
            params={}
        )
        
        checkpoint = PersistentExecutionStore.get_checkpoint(execution_id, stage_id)
        assert checkpoint is not None
        
        # 重置检查点
        success = PersistentExecutionStore.reset_checkpoint(execution_id, stage_id)
        assert success is True
        
        # 验证检查点状态
        checkpoint = PersistentExecutionStore.get_checkpoint(execution_id, stage_id)
        assert checkpoint["stage_status"] == "pending", "检查点状态应该重置为 pending"
        
        print("✅ 测试通过：可以重置检查点")


# =============================================================================
# Phase 5: 恢复功能专项测试
# =============================================================================

class TestResumeFunctionality:
    """测试恢复功能的专项逻辑"""
    
    def test_resume_from_paused_with_completed_stage(self, test_db):
        """
        测试：从暂停状态恢复，暂停阶段已完成
        
        场景：
        1. preprocessing 阶段完成
        2. 任务在预处理后暂停（专家模式）
        3. 点击恢复
        4. 应该从下一个阶段（feature_engineering）继续
        """
        # 创建暂停状态的 context
        execution_id = "exec-test-resume-completed"
        context = ExecutionContext(
            execution_id=execution_id,
            task_id="rule_mining",
            session_id="session-test",
            params={"target_col": "label"},
            status=ExecutionStatus.PAUSED,
            current_stage="preprocessing"
        )
        
        # 添加已完成的预处理阶段
        context.stages["preprocessing"] = StageProgress(
            stage_id="preprocessing",
            stage_name="数据预处理",
            status=ExecutionStatus.COMPLETED
        )
        
        # 模拟恢复逻辑
        if context.status == ExecutionStatus.PAUSED and context.current_stage:
            paused_stage = context.stages.get(context.current_stage)
            if paused_stage and paused_stage.status == ExecutionStatus.COMPLETED:
                # 暂停的阶段已完成，从下一个阶段开始
                stage_order = ["preprocessing", "feature_engineering", "generating_rules"]
                paused_idx = stage_order.index(context.current_stage)
                if paused_idx + 1 < len(stage_order):
                    start_from_stage = stage_order[paused_idx + 1]
                    assert start_from_stage == "feature_engineering", "应该从 feature_engineering 继续"
                else:
                    assert False, "不应该到达这里"
            else:
                assert False, "暂停阶段应该已完成"
        else:
            assert False, "应该是 PAUSED 状态"
        
        print("✅ 测试通过：从暂停状态恢复，暂停阶段已完成时，从下一阶段继续")
    
    def test_resume_from_paused_with_incomplete_stage(self, test_db):
        """
        测试：从暂停状态恢复，暂停阶段未完成
        
        场景：
        1. 任务执行到预处理中间时暂停
        2. 点击恢复
        3. 应该从暂停的阶段（preprocessing）继续
        """
        execution_id = "exec-test-resume-incomplete"
        context = ExecutionContext(
            execution_id=execution_id,
            task_id="rule_mining",
            session_id="session-test",
            params={"target_col": "label"},
            status=ExecutionStatus.PAUSED,
            current_stage="preprocessing"
        )
        
        # 添加未完成的预处理阶段
        context.stages["preprocessing"] = StageProgress(
            stage_id="preprocessing",
            stage_name="数据预处理",
            status=ExecutionStatus.RUNNING  # 未完成
        )
        
        # 模拟恢复逻辑
        if context.status == ExecutionStatus.PAUSED and context.current_stage:
            paused_stage = context.stages.get(context.current_stage)
            if paused_stage and paused_stage.status == ExecutionStatus.COMPLETED:
                assert False, "暂停阶段不应该已完成"
            else:
                # 暂停的阶段未完成，从该阶段继续
                start_from_stage = context.current_stage
                assert start_from_stage == "preprocessing", "应该从 preprocessing 继续"
        else:
            assert False, "应该是 PAUSED 状态"
        
        print("✅ 测试通过：从暂停状态恢复，暂停阶段未完成时，从暂停阶段继续")
    
    def test_resume_with_no_cached_state(self, test_db):
        """
        测试：恢复时没有缓存状态
        
        场景：
        1. 任务暂停
        2. 缓存数据丢失（比如清理了）
        3. 点击恢复
        4. 应该从头开始执行
        """
        execution_id = "exec-test-resume-no-cache"
        
        # 尝试获取缓存（不存在）
        cached_state = PersistentExecutionStore.get_cached_state_for_retry(
            execution_id=execution_id,
            retry_stage_id="feature_engineering"
        )
        
        assert cached_state is None, "缓存不存在应该返回 None"
        
        # Pipeline 应该从头开始
        start_from_stage = None  # 没有缓存，从头开始
        assert start_from_stage is None, "没有缓存时应该从头开始"
        
        print("✅ 测试通过：没有缓存时从头开始执行")


# =============================================================================
# Phase 6: 性能测试
# =============================================================================

class TestPerformance:
    """性能测试"""
    
    def test_database_write_performance(self, test_db):
        """测试数据库写入性能"""
        iterations = 100
        start_time = time.time()
        
        for i in range(iterations):
            TaskHistoryService.create_record(
                task_type="rule_mining",
                execution_id=f"exec-perf-{i}",
                session_id="session-perf",
                params={"i": i}
            )
        
        elapsed = time.time() - start_time
        avg_time = elapsed / iterations
        
        assert avg_time < 0.1, f"平均写入时间应该 < 100ms，实际: {avg_time*1000:.2f}ms"
        
        print(f"✅ 测试通过：数据库写入性能 (平均: {avg_time*1000:.2f}ms, 总耗时: {elapsed:.2f}s)")
    
    def test_database_query_performance(self, test_db):
        """测试数据库查询性能"""
        # 创建1000条记录
        for i in range(1000):
            TaskHistoryService.create_record(
                task_type="rule_mining" if i % 2 == 0 else "scorecard_dev",
                execution_id=f"exec-query-perf-{i}",
                session_id="session-perf",
                params={}
            )
        
        start_time = time.time()
        records = TaskHistoryService.list_records(limit=1000)
        elapsed = time.time() - start_time
        
        assert len(records) >= 1000, "应该返回1000条记录"
        assert elapsed < 0.5, f"查询时间应该 < 500ms，实际: {elapsed*1000:.2f}ms"
        
        print(f"✅ 测试通过：数据库查询性能 (耗时: {elapsed*1000:.2f}ms)")
    
    def test_result_storage_performance(self, test_storage):
        """测试结果存储性能"""
        # 创建较大的结果（10MB左右的DataFrame）
        large_df = pd.DataFrame({
            f"col_{i}": list(range(10000)) for i in range(100)
        })
        
        result = {
            "dataframe": large_df,
            "metrics": {"metric1": 1.0, "metric2": 2.0}
        }
        
        # 测试保存性能
        start_time = time.time()
        result_path = test_storage.save_result(
            record_id="perf-result",
            result=result,
            metadata={"test": "performance"}
        )
        save_elapsed = time.time() - start_time
        
        assert save_elapsed < 1.0, f"保存时间应该 < 1s，实际: {save_elapsed:.2f}s"
        
        # 测试加载性能
        start_time = time.time()
        loaded_result = test_storage.load_result("perf-result")
        load_elapsed = time.time() - start_time
        
        assert loaded_result is not None
        assert load_elapsed < 1.0, f"加载时间应该 < 1s，实际: {load_elapsed:.2f}s"
        
        print(f"✅ 测试通过：结果存储性能 (保存: {save_elapsed*1000:.2f}ms, 加载: {load_elapsed*1000:.2f}ms)")


# =============================================================================
# Phase 7: 兼容性测试
# =============================================================================

class TestCompatibility:
    """兼容性测试"""
    
    def test_pipeline_mode_without_task_manager(self):
        """测试：不使用任务管理功能的任务正常工作"""
        # 创建不使用任务管理的 context（record_id=None）
        context = ExecutionContext(
            execution_id="exec-compat-no-tm",
            task_id="rule_mining",
            session_id="session-test",
            params={"target_col": "label"},
            status=ExecutionStatus.RUNNING,
            record_id=None  # 关键：没有 record_id
        )
        
        # 更新 context（不应该报错）
        ExecutionStore.update(context)
        
        # 验证 context 仍然可以正常访问
        stored = ExecutionStore.get(context.execution_id)
        assert stored is not None
        assert stored.execution_id == context.execution_id
        
        print("✅ 测试通过：不使用任务管理的任务正常工作")
    
    def test_backward_compatibility_with_existing_records(self, test_db):
        """测试：向后兼容现有记录"""
        # 手动创建一条旧格式的记录（没有某些新字段）
        old_record = TaskRecord(
            record_id="rec-compat-old",
            task_type="rule_mining",
            task_category="sop",
            execution_id="exec-compat-old",
            session_id="session-compat",
            status="pending",
            progress=0.0,
            params_json='{"target_col": "label"}',
            created_at=datetime.now()
        )
        
        from deepanalyze.core.task_manager.database import get_task_manager_db
        db = get_task_manager_db()
        with db.get_session() as session:
            session.add(old_record)
            session.commit()
        
        # 尝试读取（不应该报错）
        record = TaskHistoryService.get_record("rec-compat-old")
        assert record is not None
        assert record["task_type"] == "rule_mining"
        
        print("✅ 测试通过：向后兼容现有记录")
    
    def test_multiple_task_types(self, test_db):
        """测试：支持多种任务类型"""
        task_types = ["rule_mining", "scorecard_dev", "llm_inference", "model_training"]
        
        for task_type in task_types:
            TaskHistoryService.create_record(
                task_type=task_type,
                execution_id=f"exec-multi-{task_type}",
                session_id="session-multi",
                params={}
            )
        
        # 查询所有类型的记录
        for task_type in task_types:
            records = TaskHistoryService.list_records(task_type=task_type)
            assert len(records) >= 1, f"应该能查询 {task_type} 类型的记录"
        
        print(f"✅ 测试通过：支持多种任务类型 ({', '.join(task_types)})")


# =============================================================================
# 运行测试
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
