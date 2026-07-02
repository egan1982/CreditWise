"""
用户管理模块 批次1 Phase5/6 验证测试

覆盖：
1. user_migration_service.is_legacy_session_id / merge_user_data
2. API /workspace/claim-legacy-session（用户自助认领）
3. API /admin/users/merge（账户合并小工具）

详见 docs/user_management_module_design.md §六、§七
"""

import os
import sys
import pytest

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _project_root)
sys.path.insert(0, os.path.join(_project_root, "API"))


class _FakeState:
    def __init__(self, user):
        self.user = user


class _FakeRequest:
    def __init__(self, user=None):
        self.state = _FakeState(user)


@pytest.fixture
def isolated_task_db(tmp_path, monkeypatch):
    """将 deepanalyze.core.task_manager.database 的全局单例临时替换为独立测试库，
    避免污染真实项目的 task_manager.db（该文件已被其他既有测试证实存在跨用例
    状态污染问题，属于预先存在的测试基础设施缺陷，本测试不重蹈）。
    """
    from deepanalyze.core.task_manager import database as _db_mod

    original = _db_mod._task_manager_db
    test_db_url = f"sqlite:///{tmp_path}/test_task_manager.db"
    test_db = _db_mod.TaskManagerDB(test_db_url)
    test_db.create_tables()
    _db_mod._task_manager_db = test_db
    yield test_db
    test_db.close()
    _db_mod._task_manager_db = original


# =============================================================================
# 1. is_legacy_session_id
# =============================================================================

class TestIsLegacySessionId:
    def test_matches_legacy_format(self):
        from deepanalyze.core.task_manager.user_migration_service import is_legacy_session_id
        assert is_legacy_session_id("session_1711782000_a1b2c3") is True

    def test_rejects_normal_username(self):
        from deepanalyze.core.task_manager.user_migration_service import is_legacy_session_id
        assert is_legacy_session_id("alice") is False
        assert is_legacy_session_id("fjzheng") is False

    def test_rejects_malformed(self):
        from deepanalyze.core.task_manager.user_migration_service import is_legacy_session_id
        assert is_legacy_session_id("session_abc_xyz") is False  # 时间戳段非数字
        assert is_legacy_session_id("") is False
        assert is_legacy_session_id(None) is False


# =============================================================================
# 2. merge_user_data
# =============================================================================

class TestMergeUserData:
    def _seed_db(self, test_db, session_id: str):
        from deepanalyze.core.task_manager.models import TaskRecord, ExecutionState
        with test_db.get_session() as session:
            session.add(TaskRecord(
                record_id="rec-1", task_type="rule_mining", task_category="sop",
                execution_id="exec-1", session_id=session_id,
            ))
            session.add(ExecutionState(
                execution_id="exec-1", task_id="rule_mining", session_id=session_id,
            ))

    def test_validation_rejects_same_from_to(self, isolated_task_db):
        from deepanalyze.core.task_manager.user_migration_service import merge_user_data
        with pytest.raises(ValueError):
            merge_user_data("alice", "alice", "/tmp/workspace")

    def test_validation_rejects_unsafe_chars(self, isolated_task_db):
        from deepanalyze.core.task_manager.user_migration_service import merge_user_data
        with pytest.raises(ValueError):
            merge_user_data("session_1_abc", "../etc/passwd", "/tmp/workspace")
        with pytest.raises(ValueError):
            merge_user_data("bad name!", "alice", "/tmp/workspace")

    def test_dry_run_does_not_modify_db_or_files(self, isolated_task_db, tmp_path):
        from deepanalyze.core.task_manager.models import TaskRecord
        from deepanalyze.core.task_manager.user_migration_service import merge_user_data

        self._seed_db(isolated_task_db, "session_1711782000_abc")
        ws = tmp_path / "workspace"
        (ws / "session_1711782000_abc").mkdir(parents=True)
        (ws / "session_1711782000_abc" / "data.csv").write_text("x")

        result = merge_user_data("session_1711782000_abc", "alice", str(ws), dry_run=True)

        assert result["task_records_matched"] == 1
        assert result["execution_states_matched"] == 1
        assert result["workspace_dir_exists"] is True
        assert result["moved_files"] == []

        # DB 未变
        with isolated_task_db.get_session() as session:
            rec = session.query(TaskRecord).filter_by(record_id="rec-1").first()
            assert rec.session_id == "session_1711782000_abc"
        # 文件未移动
        assert (ws / "session_1711782000_abc" / "data.csv").exists()
        assert not (ws / "alice").exists()

    def test_apply_moves_entire_dir_when_target_absent(self, isolated_task_db, tmp_path):
        from deepanalyze.core.task_manager.models import TaskRecord, ExecutionState
        from deepanalyze.core.task_manager.user_migration_service import merge_user_data

        self._seed_db(isolated_task_db, "session_1711782000_abc")
        ws = tmp_path / "workspace"
        (ws / "session_1711782000_abc").mkdir(parents=True)
        (ws / "session_1711782000_abc" / "data.csv").write_text("x")

        result = merge_user_data("session_1711782000_abc", "alice", str(ws), dry_run=False)

        assert result["task_records_matched"] == 1
        with isolated_task_db.get_session() as session:
            rec = session.query(TaskRecord).filter_by(record_id="rec-1").first()
            assert rec.session_id == "alice"
            state = session.query(ExecutionState).filter_by(execution_id="exec-1").first()
            assert state.session_id == "alice"

        # 目标不存在时，整目录直接改名
        assert not (ws / "session_1711782000_abc").exists()
        assert (ws / "alice" / "data.csv").exists()

    def test_apply_merges_with_conflict_rename_when_target_exists(self, isolated_task_db, tmp_path):
        from deepanalyze.core.task_manager.user_migration_service import merge_user_data

        self._seed_db(isolated_task_db, "session_1711782000_abc")
        ws = tmp_path / "workspace"
        (ws / "session_1711782000_abc").mkdir(parents=True)
        (ws / "session_1711782000_abc" / "data.csv").write_text("old_session_version")
        (ws / "session_1711782000_abc" / "unique.csv").write_text("unique")
        (ws / "alice").mkdir(parents=True)
        (ws / "alice" / "data.csv").write_text("alice_existing_version")  # 冲突文件

        result = merge_user_data("session_1711782000_abc", "alice", str(ws), dry_run=False)

        assert "data.csv" in result["renamed_conflicts"]
        # 冲突文件被改名保留，不覆盖 alice 原有的 data.csv
        assert (ws / "alice" / "data.csv").read_text() == "alice_existing_version"
        # 非冲突文件正常移入
        assert (ws / "alice" / "unique.csv").exists()
        # 源目录已清空移除
        assert not (ws / "session_1711782000_abc").exists()
        # 冲突的旧文件以新名字保留下来，内容未丢失
        renamed_files = list((ws / "alice").glob("data__migrated_*.csv"))
        assert len(renamed_files) == 1
        assert renamed_files[0].read_text() == "old_session_version"

    def test_no_workspace_dir_still_migrates_db_only(self, isolated_task_db, tmp_path):
        """workspace目录不存在（例如纯API任务无文件）时，仅迁移DB记录，不报错"""
        from deepanalyze.core.task_manager.models import TaskRecord
        from deepanalyze.core.task_manager.user_migration_service import merge_user_data

        self._seed_db(isolated_task_db, "session_1711782000_xyz")
        ws = tmp_path / "workspace"  # 不创建任何子目录

        result = merge_user_data("session_1711782000_xyz", "bob", str(ws), dry_run=False)

        assert result["workspace_dir_exists"] is False
        with isolated_task_db.get_session() as session:
            rec = session.query(TaskRecord).filter_by(record_id="rec-1").first()
            assert rec.session_id == "bob"


# =============================================================================
# 3. API 端到端测试：/workspace/claim-legacy-session、/admin/users/merge
#
# 注：claim_legacy_session/merge_user_accounts 是 create_app() 内部的嵌套函数，
# 无法直接 import，只能通过 TestClient 走真实 HTTP 路由验证。
# =============================================================================

class TestClaimLegacySessionAndMergeAPI:
    @pytest.fixture
    def client(self, isolated_task_db, tmp_path, monkeypatch):
        import config as _config
        monkeypatch.setattr(_config, "WORKSPACE_BASE_DIR", str(tmp_path / "workspace"))

        from fastapi.testclient import TestClient
        from API.main import create_app
        app = create_app()

        @app.middleware("http")
        async def _inject_fake_user(request, call_next):
            username = request.headers.get("x-test-username")
            role = request.headers.get("x-test-role", "user")
            if username:
                request.state.user = {"username": username, "role": role}
            return await call_next(request)

        return TestClient(app)

    def _seed(self, tmp_path, old_session_id: str, filename: str = "data.csv"):
        d = tmp_path / "workspace" / old_session_id
        d.mkdir(parents=True, exist_ok=True)
        (d / filename).write_text("content")

    def test_claim_legacy_session_single_user_mode_rejected(self, client):
        """单用户模式（无模拟身份header）：直接400拒绝"""
        resp = client.post("/workspace/claim-legacy-session", json={"old_session_id": "session_1_abc"})
        assert resp.status_code == 400

    def test_claim_legacy_session_rejects_non_legacy_format(self, client):
        """尝试认领一个正常用户名格式（不像旧随机session），应被拒绝，防止误关联他人账户"""
        resp = client.post(
            "/workspace/claim-legacy-session",
            json={"old_session_id": "bob"},
            headers={"x-test-username": "alice", "x-test-role": "user"},
        )
        assert resp.status_code == 400

    def test_claim_legacy_session_success(self, client, tmp_path):
        """alice认领自己本机残留的旧格式session，数据应迁移到alice名下"""
        self._seed(tmp_path, "session_1711782000_abc123")

        resp = client.post(
            "/workspace/claim-legacy-session",
            json={"old_session_id": "session_1711782000_abc123"},
            headers={"x-test-username": "alice", "x-test-role": "user"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["merged"]["workspace_dir_exists"] is True

        assert (tmp_path / "workspace" / "alice" / "data.csv").exists()
        assert not (tmp_path / "workspace" / "session_1711782000_abc123").exists()

    def test_merge_accounts_requires_admin(self, client):
        """普通用户调用账户合并接口应403（业务层显式校验，不仅依赖中间件）"""
        resp = client.post(
            "/admin/users/merge",
            json={"from_username": "old_alice", "to_username": "alice", "dry_run": True},
            headers={"x-test-username": "alice", "x-test-role": "user"},
        )
        assert resp.status_code == 403

    def test_merge_accounts_admin_success(self, client, tmp_path):
        """admin执行账户合并：old_alice名下数据转移到alice名下"""
        self._seed(tmp_path, "old_alice")

        resp = client.post(
            "/admin/users/merge",
            json={"from_username": "old_alice", "to_username": "alice", "dry_run": False},
            headers={"x-test-username": "root_admin", "x-test-role": "admin"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["merged"]["workspace_dir_exists"] is True
        assert (tmp_path / "workspace" / "alice" / "data.csv").exists()


if __name__ == "__main__":
    import pytest as _pytest
    _pytest.main([__file__, "-v"])
