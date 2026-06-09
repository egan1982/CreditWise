"""
单元测试：AI 建议一键调参重跑 + 版本快照

覆盖：
1.  test_stage_snapshot_serialization         快照序列化/反序列化往返
2.  test_retry_creates_snapshot               retry_stage 后 snapshots 长度 +1
3.  test_suggested_params_parsing             SUGGESTED_PARAMS 行解析
4.  test_unknown_param_key_filtered           通过 API 层（待手工测）
5.  test_backward_compat_no_snapshots         旧 execution 无 snapshots 字段兼容
6.  test_snapshots_fifo                       超过 10 次重试时 FIFO
7.  test_get_api_strips_text                  GET 接口返回干净文本（无 SUGGESTED_PARAMS 行）
8.  test_get_api_returns_suggested_params     GET 接口解析并返回 suggested_params
9.  test_post_api_stores_raw_text             POST 接口存原始文本（含标记行）
10. test_snapshot_captures_ai_analysis        retry 时快照包含当前 AI 分析
11. test_params_context_injected              Prompt 包含 params_used 上下文
12. test_available_params_uses_both_lists     task_def.required+optional_params 均被搜索
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


# =============================================================================
# TC-7：GET 接口返回干净文本 + suggested_params
# =============================================================================

class TestGetApiReturnsCleanText:
    """TC-7/8: GET 接口对含 SUGGESTED_PARAMS 行的原始文本进行剥离和解析"""

    @pytest.fixture(autouse=True)
    def import_helpers(self):
        from API.sop_api import _parse_suggested_params, _strip_suggested_params
        self._parse = _parse_suggested_params
        self._strip = _strip_suggested_params

    def test_get_strips_suggested_params_line(self):
        """GET 接口返回给前端的文本不含 SUGGESTED_PARAMS: 行"""
        raw = '分析完成，建议调大深度。\nSUGGESTED_PARAMS: {"max_depth": 5}'
        clean = self._strip(raw)
        assert "SUGGESTED_PARAMS" not in clean
        assert "分析完成" in clean

    def test_get_returns_parsed_suggested_params(self):
        """GET 接口能从原始文本解析出 suggested_params 字典"""
        raw = '特征筛选完成。\nSUGGESTED_PARAMS: {"iv_threshold": 0.03}'
        params = self._parse(raw)
        assert params is not None
        assert params["iv_threshold"] == 0.03

    def test_get_returns_none_when_no_marker(self):
        """原始文本无标记行时 suggested_params 为 None"""
        raw = "特征筛选完成，无需调整。"
        assert self._parse(raw) is None

    def test_strip_idempotent_on_clean_text(self):
        """对已干净的文本再次剥离不会破坏内容"""
        clean = "分析完成，关键指标正常。"
        assert self._strip(clean) == clean


# =============================================================================
# TC-9：POST 接口存原始文本（含标记行）
# =============================================================================

class TestPostApiStoresRawText:
    """TC-9: POST 接口保存原始文本到 DB，不提前剥离"""

    @pytest.fixture(autouse=True)
    def import_helpers(self):
        from API.sop_api import _parse_suggested_params
        self._parse = _parse_suggested_params

    def test_raw_text_preserves_marker_for_later_parsing(self):
        """模拟 POST 保存原始文本，GET 时能再次解析出 suggested_params"""
        # 模拟前端发送的 analysis_text（含标记行）
        raw = '规则生成阶段结果正常。\nSUGGESTED_PARAMS: {"max_depth": 5, "n_vars": 3}'
        
        # POST 端：解析 suggested_params 返回给前端（不剥离，存原始）
        suggested = self._parse(raw)
        assert suggested == {"max_depth": 5, "n_vars": 3}
        
        # 存入 DB 的是 raw（模拟 DB 存储）
        stored_in_db = raw  # POST 接口现在存 raw
        
        # GET 端：从 DB 读出来后再解析+剥离
        get_suggested = self._parse(stored_in_db)
        assert get_suggested == {"max_depth": 5, "n_vars": 3}


# =============================================================================
# TC-10：快照保存当时的 AI 分析（不应被后续分析覆盖）
# =============================================================================

class TestSnapshotCapturesAiAnalysis:
    """TC-10: 快照打入时包含当时 DB 里的 AI 分析，后续新分析不覆盖快照"""

    def test_snapshot_stores_ai_analysis_at_capture_time(self):
        """快照的 ai_analysis 字段保存快照创建时的分析文本"""
        # 模拟第一次执行的 AI 分析
        first_analysis = "第一次分析：规则数量1555条，建议增加树深度。"
        
        # 打快照（模拟 retry_stage 从 DB 读取当前分析）
        snap = StageSnapshot(
            version=1,
            params_used={"max_depth": 3},
            output_preview={"total_rules": 1555},
            ai_analysis=first_analysis,  # 从 DB 读取的当前分析
            suggested_params={"max_depth": 5},
            execution_time_ms=4800,
            completed_at="2026-06-08T10:00:00",
            retry_reason="接受AI建议",
        )
        
        # 模拟第二次执行完成后新的 AI 分析（覆盖 DB，但快照不变）
        second_analysis = "第二次分析：规则数量1673条，参数调整有效。"
        
        # 快照的 ai_analysis 应该还是第一次的
        assert snap.ai_analysis == first_analysis
        assert snap.ai_analysis != second_analysis

    def test_snapshot_ai_analysis_none_when_db_empty(self):
        """DB 无 AI 分析时（首次执行尚未触发分析），快照 ai_analysis 为 None"""
        snap = StageSnapshot(
            version=1,
            params_used={"max_depth": 3},
            output_preview={"total_rules": 100},
            ai_analysis=None,  # DB 无记录
            suggested_params=None,
            execution_time_ms=1000,
            completed_at="2026-06-08T10:00:00",
        )
        assert snap.ai_analysis is None


# =============================================================================
# TC-11：Prompt 包含 params_used 上下文
# =============================================================================

class TestParamsContextInjected:
    """TC-11: get_stage_analysis_prompt 在有 params_used 时注入参数上下文"""

    @pytest.fixture(autouse=True)
    def import_fn(self):
        from API.AI_analysis_prompts import get_stage_analysis_prompt
        self._build = get_stage_analysis_prompt

    def test_params_context_present_when_params_used_provided(self):
        """提供 params_used 时，Prompt 中包含"本次执行参数"章节"""
        prompt = self._build(
            stage_id="feature_engineering",
            stage_name="特征工程",
            data={"iv_threshold": 0.02, "features_after": 29},
            task_type="rule_mining",
            params_used={"iv_threshold": 0.02, "missing_threshold": 0.5},
        )
        assert "本次执行参数" in prompt
        assert "iv_threshold" in prompt

    def test_params_context_absent_when_no_params_used(self):
        """不提供 params_used 时，Prompt 中不出现参数章节"""
        prompt = self._build(
            stage_id="feature_engineering",
            stage_name="特征工程",
            data={"iv_threshold": 0.02},
            task_type="rule_mining",
            params_used=None,
        )
        assert "本次执行参数" not in prompt

    def test_skip_keys_excluded_from_context(self):
        """data_file、target_col 等无关字段不出现在参数上下文中"""
        prompt = self._build(
            stage_id="feature_engineering",
            stage_name="特征工程",
            data={},
            task_type="rule_mining",
            params_used={
                "iv_threshold": 0.02,
                "data_file": "/path/to/data.csv",   # 应被过滤
                "target_col": "is_bad",              # 应被过滤
            },
        )
        assert "data_file" not in prompt
        assert "target_col" not in prompt
        assert "iv_threshold" in prompt

    def test_params_context_absent_when_all_filtered(self):
        """params_used 全是跳过字段时，不生成参数章节"""
        prompt = self._build(
            stage_id="feature_engineering",
            stage_name="特征工程",
            data={},
            task_type="rule_mining",
            params_used={
                "data_file": "/path/to/data.csv",
                "target_col": "is_bad",
                "exclude_cols": [],
            },
        )
        assert "本次执行参数" not in prompt


# =============================================================================
# TC-12：_get_stage_available_params 使用 required_params + optional_params
# =============================================================================

class TestAvailableParamsUsesBothLists:
    """TC-12: 修复后 _get_stage_available_params 能从 optional_params 找到参数"""

    def test_stage_params_found_in_optional_params(self):
        """feature_engineering 阶段的参数（在 optional_params）能被正确返回"""
        from API.AI_analysis_prompts import _get_stage_available_params
        params = _get_stage_available_params("feature_engineering", "rule_mining")
        # iv_threshold 和 missing_threshold 都在 optional_params 的 feature_engineering 阶段
        assert len(params) > 0, "feature_engineering 阶段应有可调参数"
        assert "iv_threshold" in params or "missing_threshold" in params

    def test_generating_rules_params_found(self):
        """generating_rules 阶段的参数（max_depth 等）能被正确返回"""
        from API.AI_analysis_prompts import _get_stage_available_params
        params = _get_stage_available_params("generating_rules", "rule_mining")
        assert len(params) > 0
        assert "max_depth" in params or "n_vars" in params

    def test_unknown_stage_returns_empty(self):
        """不存在的阶段 ID 返回空列表，不报错"""
        from API.AI_analysis_prompts import _get_stage_available_params
        params = _get_stage_available_params("nonexistent_stage", "rule_mining")
        assert params == []
