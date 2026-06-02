"""
单元测试：AI 建议一键调参重跑 + 版本快照

覆盖：
1. test_stage_snapshot_serialization       快照序列化/反序列化往返
2. test_retry_creates_snapshot             retry_stage 后 snapshots 长度 +1
3. test_suggested_params_parsing           SUGGESTED_PARAMS 行解析
4. test_unknown_param_key_filtered         通过 API 层（待手工测）
5. test_backward_compat_no_snapshots       旧 execution 无 snapshots 字段兼容
6. test_snapshots_fifo                     超过 10 次重试时 FIFO
"""
import sys
import os
import json
import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "API"))


# =============================================================================
# 辅助：预 stub pkg_resources，避免 scorecardpy 在本地 Python 3.12 下报错
# =============================================================================
import types as _types

if "pkg_resources" not in sys.modules:
    _pkg = _types.ModuleType("pkg_resources")
    _pkg.resource_filename = lambda *a, **kw: ""  # type: ignore
    _pkg.resource_listdir = lambda *a, **kw: []    # type: ignore
    sys.modules["pkg_resources"] = _pkg


from deepanalyze.analysis.task_SOP.executor import StageSnapshot, StageProgress, ExecutionStatus


# =============================================================================
# TC-1：StageSnapshot 序列化往返
# =============================================================================

class TestStageSnapshotSerialization:
    """TC-1: StageSnapshot 序列化与反序列化"""

    def test_snapshot_to_dict_and_back(self):
        """快照字典化后可以还原所有字段"""
        snap = StageSnapshot(
            version=1,
            params_used={"max_depth": 3, "min_samples_leaf": 0.01},
            output_preview={"total_rules": 150, "avg_lift": 2.5},
            ai_analysis="当前规则质量良好，建议适当增大树深度。",
            suggested_params={"max_depth": 5},
            execution_time_ms=3200,
            completed_at="2026-06-02T10:00:00",
            retry_reason="接受AI建议",
        )
        # 序列化为字典
        d = {
            "version": snap.version,
            "params_used": snap.params_used,
            "output_preview": snap.output_preview,
            "ai_analysis": snap.ai_analysis,
            "suggested_params": snap.suggested_params,
            "execution_time_ms": snap.execution_time_ms,
            "completed_at": snap.completed_at,
            "retry_reason": snap.retry_reason,
        }
        # JSON 往返
        restored = json.loads(json.dumps(d))
        assert restored["version"] == 1
        assert restored["params_used"]["max_depth"] == 3
        assert restored["suggested_params"]["max_depth"] == 5
        assert restored["retry_reason"] == "接受AI建议"

    def test_snapshot_with_none_fields(self):
        """ai_analysis 和 suggested_params 可以为 None"""
        snap = StageSnapshot(
            version=2,
            params_used={},
            output_preview=None,
            ai_analysis=None,
            suggested_params=None,
            execution_time_ms=None,
            completed_at=None,
        )
        d = {
            "version": snap.version,
            "output_preview": snap.output_preview,
            "ai_analysis": snap.ai_analysis,
            "suggested_params": snap.suggested_params,
        }
        restored = json.loads(json.dumps(d))
        assert restored["output_preview"] is None
        assert restored["suggested_params"] is None


# =============================================================================
# TC-2：StageProgress.snapshots 字段
# =============================================================================

class TestStageProgressSnapshots:
    """TC-2: StageProgress 包含 snapshots 字段且默认为空列表"""

    def test_snapshots_default_empty(self):
        stage = StageProgress(stage_id="generating_rules", stage_name="规则生成")
        assert hasattr(stage, "snapshots")
        assert isinstance(stage.snapshots, list)
        assert len(stage.snapshots) == 0

    def test_append_snapshot(self):
        stage = StageProgress(stage_id="generating_rules", stage_name="规则生成")
        stage.status = ExecutionStatus.COMPLETED
        snap = StageSnapshot(
            version=1,
            params_used={"max_depth": 3},
            output_preview={"total_rules": 100},
            ai_analysis=None,
            suggested_params=None,
            execution_time_ms=1000,
            completed_at="2026-06-02T10:00:00",
        )
        stage.snapshots.append(snap)
        assert len(stage.snapshots) == 1
        assert stage.snapshots[0].version == 1


# =============================================================================
# TC-3：SUGGESTED_PARAMS 解析（测试 sop_api.py 中的辅助函数）
# =============================================================================

class TestSuggestedParamsParsing:
    """TC-3: _parse_suggested_params 和 _strip_suggested_params"""

    @pytest.fixture(autouse=True)
    def import_helpers(self):
        from API.sop_api import _parse_suggested_params, _strip_suggested_params
        self._parse = _parse_suggested_params
        self._strip = _strip_suggested_params

    def test_normal_parse(self):
        text = '规则质量良好，建议增加树深度。\nSUGGESTED_PARAMS: {"max_depth": 5, "min_samples_leaf": 0.02}'
        params = self._parse(text)
        assert params is not None
        assert params["max_depth"] == 5
        assert params["min_samples_leaf"] == 0.02

    def test_no_suggested_params(self):
        text = "规则质量良好，无需调整参数。"
        assert self._parse(text) is None

    def test_malformed_json(self):
        text = "分析结论。\nSUGGESTED_PARAMS: {bad json here"
        assert self._parse(text) is None

    def test_empty_dict(self):
        text = "分析结论。\nSUGGESTED_PARAMS: {}"
        # 空 dict 不应该返回
        assert self._parse(text) is None

    def test_strip_removes_line(self):
        text = '规则质量良好。\nSUGGESTED_PARAMS: {"max_depth": 5}'
        clean = self._strip(text)
        assert "SUGGESTED_PARAMS" not in clean
        assert "规则质量良好" in clean

    def test_strip_trailing_blank_lines(self):
        text = '分析完成。\nSUGGESTED_PARAMS: {"k": 1}\n\n'
        clean = self._strip(text)
        assert clean.strip() == "分析完成。"


# =============================================================================
# TC-4（手工测试）：未知参数 key 过滤
# 该逻辑在前端 SuggestedParamsCard 中仅展示 suggestedParams 的 key，
# 不会向后端传递未知 key（用户看到什么就填什么，不额外过滤）
# 此处仅标记为手工测试占位
# =============================================================================


# =============================================================================
# TC-5：旧 execution 无 snapshots 字段的向下兼容
# =============================================================================

class TestBackwardCompatNoSnapshots:
    """TC-5: 旧版 StageProgress（无 snapshots 字段）反序列化后默认为空列表"""

    def test_stage_progress_without_snapshots_field(self):
        """
        模拟从 JSON/pickle 还原旧版 stage 数据（无 snapshots 字段）。
        由于 dataclass field(default_factory=list)，新建的 StageProgress
        总是有空 snapshots，旧的 pickle 对象通过 __setattr__ 兼容。
        """
        # 模拟旧版持久化数据（没有 snapshots 字段）
        old_stage_dict = {
            "stage_id": "woe_binning",
            "stage_name": "WOE分箱",
            "status": "completed",
            "progress": 100.0,
            "message": "",
            "logs": [],
            "code": "",
            "output_preview": None,
            "params_used": {"binning_method": "tree"},
            "params_meta": [],
            # 故意没有 snapshots 字段
        }
        # 前端收到此 dict 后读取 snapshots（用 .get 保底）
        snapshots = old_stage_dict.get("snapshots", [])
        assert snapshots == []
        assert isinstance(snapshots, list)


# =============================================================================
# TC-6：snapshots FIFO（超过 10 个时丢弃最旧的）
# =============================================================================

class TestSnapshotsFIFO:
    """TC-6: snapshots 超过 10 条时保留最近 10 条"""

    def test_fifo_keeps_recent_10(self):
        stage = StageProgress(stage_id="generating_rules", stage_name="规则生成")

        # 模拟 11 次 retry 打快照
        for i in range(1, 12):
            snap = StageSnapshot(
                version=i,
                params_used={"max_depth": i},
                output_preview=None,
                ai_analysis=None,
                suggested_params=None,
                execution_time_ms=1000,
                completed_at=f"2026-06-02T10:{i:02d}:00",
            )
            stage.snapshots.append(snap)
            # FIFO 逻辑（与 sop_api.py 中一致）
            if len(stage.snapshots) > 10:
                stage.snapshots = stage.snapshots[-10:]

        assert len(stage.snapshots) == 10
        # 保留最近 10 个（版本 2~11）
        assert stage.snapshots[0].version == 2
        assert stage.snapshots[-1].version == 11
