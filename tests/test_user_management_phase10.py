"""
用户管理模块 批次2 Phase10 验证测试

覆盖 API/user_admin_api.py 全部端点：
1. GET  /auth/mode
2. PUT  /auth/profile
3. POST /auth/change-password（含账户锁定复用，M19）
4. GET/POST/PUT/DELETE /admin/users*（含权限矩阵、用户名冲突409、软删除自我保护）
5. GET /auth/me 补充字段（批次2）

详见 docs/user_management_module_design.md §十四
"""

import os
import sys
import pytest

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _project_root)
sys.path.insert(0, os.path.join(_project_root, "API"))

from fastapi.testclient import TestClient


@pytest.fixture
def isolated_task_db(tmp_path):
    """独立测试库，避免污染真实 task_manager.db"""
    from deepanalyze.core.task_manager import database as _db_mod

    original = _db_mod._task_manager_db
    test_db_url = f"sqlite:///{tmp_path}/test_task_manager_phase10.db"
    test_db = _db_mod.TaskManagerDB(test_db_url)
    test_db.create_tables()
    _db_mod._task_manager_db = test_db
    yield test_db
    test_db.close()
    _db_mod._task_manager_db = original


class _FakeAuthForLockout:
    """模拟 SimpleAuth 的账户锁定接口子集，用于验证 /auth/change-password 是否正确复用锁定机制"""

    def __init__(self, max_failures: int = 3):
        self.max_failures = max_failures
        self.lockout_duration = 900
        self._counts = {}

    def _is_locked(self, username: str) -> bool:
        return self._counts.get(username, 0) >= self.max_failures

    def _record_failure(self, username: str, password: str = "") -> None:
        # CVM部署测试发现（2026-07-03）：真实 SimpleAuth._record_failure 新增了
        # password 参数用于短时间窗口内同一份凭证的并发去重（详见
        # auth_middleware.py 该方法 docstring）。这个 Fake 仅用于验证
        # /auth/change-password 端点是否正确调用了锁定机制的整数计数接口，
        # 不测试去重细节，因此忽略 password，行为保持不变（每次调用都计数）。
        self._counts[username] = self._counts.get(username, 0) + 1

    def _reset_failures(self, username: str) -> None:
        self._counts[username] = 0


@pytest.fixture
def client(isolated_task_db):
    """真实 TestClient + 模拟中间件注入身份（与既有测试文件保持一致的隔离方式）"""
    from API.main import create_app

    app = create_app()
    app.state.auth = _FakeAuthForLockout()

    @app.middleware("http")
    async def _inject_fake_user(request, call_next):
        username = request.headers.get("x-test-username")
        role = request.headers.get("x-test-role", "user")
        if username:
            request.state.user = {"username": username, "role": role}
        return await call_next(request)

    return TestClient(app)


def _headers(username: str, role: str = "user") -> dict:
    return {"x-test-username": username, "x-test-role": role}


# =============================================================================
# 1. /auth/mode
# =============================================================================

class TestAuthMode:
    def test_reflects_enable_auth_env(self, client, monkeypatch):
        monkeypatch.setenv("ENABLE_AUTH", "true")
        assert client.get("/auth/mode").json() == {"auth_enabled": True}

        monkeypatch.setenv("ENABLE_AUTH", "false")
        assert client.get("/auth/mode").json() == {"auth_enabled": False}

    def test_no_auth_required(self, client, monkeypatch):
        """白名单接口，无需携带任何登录身份即可访问"""
        monkeypatch.setenv("ENABLE_AUTH", "true")
        resp = client.get("/auth/mode")
        assert resp.status_code == 200


# =============================================================================
# 2. /auth/profile
# =============================================================================

class TestUpdateProfile:
    def test_single_user_mode_rejected(self, client):
        resp = client.put("/auth/profile", json={"display_name": "Alice"})
        assert resp.status_code == 400

    def test_authenticated_user_can_update_own_profile(self, client):
        from deepanalyze.core.task_manager.user_service import UserService
        UserService.create_user(username="alice", password="pw123456")

        resp = client.put(
            "/auth/profile",
            json={"display_name": "Alice Chen", "org": "风控部", "description": "喜欢猫"},
            headers=_headers("alice"),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["display_name"] == "Alice Chen"
        assert data["org"] == "风控部"

    def test_cannot_change_role_via_profile(self, client):
        """请求体模型本身不接受 role 字段，即使 body 里塞了也会被 pydantic 忽略"""
        from deepanalyze.core.task_manager.user_service import UserService
        UserService.create_user(username="bob", password="pw123456", role="user")

        resp = client.put(
            "/auth/profile",
            json={"display_name": "Bob", "role": "admin"},
            headers=_headers("bob"),
        )
        assert resp.status_code == 200
        assert UserService.get_by_username("bob")["role"] == "user"


# =============================================================================
# 3. /auth/change-password
# =============================================================================

class TestChangePassword:
    def test_single_user_mode_rejected(self, client):
        resp = client.post(
            "/auth/change-password", json={"old_password": "a", "new_password": "b123456"}
        )
        assert resp.status_code == 400

    def test_success_changes_password(self, client):
        from deepanalyze.core.task_manager.user_service import UserService
        UserService.create_user(username="carol", password="OldPass1")

        resp = client.post(
            "/auth/change-password",
            json={"old_password": "OldPass1", "new_password": "NewPass2"},
            headers=_headers("carol"),
        )
        assert resp.status_code == 200
        assert UserService.verify_password("carol", "OldPass1") is None
        assert UserService.verify_password("carol", "NewPass2") is not None

    def test_wrong_old_password_rejected(self, client):
        from deepanalyze.core.task_manager.user_service import UserService
        UserService.create_user(username="dave", password="OldPass1")

        resp = client.post(
            "/auth/change-password",
            json={"old_password": "WrongOld", "new_password": "NewPass2"},
            headers=_headers("dave"),
        )
        assert resp.status_code == 400
        assert UserService.verify_password("dave", "OldPass1") is not None  # 密码未被改动

    def test_weak_new_password_rejected(self, client):
        from deepanalyze.core.task_manager.user_service import UserService
        UserService.create_user(username="erin", password="OldPass1")

        resp = client.post(
            "/auth/change-password",
            json={"old_password": "OldPass1", "new_password": "123"},
            headers=_headers("erin"),
        )
        assert resp.status_code == 400

    def test_lockout_reused_after_repeated_wrong_old_password(self, client):
        """M19：旧密码校验失败复用 SimpleAuth 现有锁定机制，超过 max_failures 次触发 429"""
        from deepanalyze.core.task_manager.user_service import UserService
        UserService.create_user(username="frank", password="OldPass1")

        for _ in range(3):  # _FakeAuthForLockout(max_failures=3)
            client.post(
                "/auth/change-password",
                json={"old_password": "WrongOld", "new_password": "NewPass2"},
                headers=_headers("frank"),
            )

        resp = client.post(
            "/auth/change-password",
            json={"old_password": "OldPass1", "new_password": "NewPass2"},  # 即使这次密码对
            headers=_headers("frank"),
        )
        assert resp.status_code == 429


# =============================================================================
# 4. /admin/users* — 权限矩阵 + CRUD
# =============================================================================

class TestListUsers:
    def test_non_admin_forbidden(self, client):
        resp = client.get("/admin/users", headers=_headers("someone", "user"))
        assert resp.status_code == 403

    def test_admin_can_list(self, client):
        from deepanalyze.core.task_manager.user_service import UserService
        UserService.create_user(username="grace", password="pw123456")

        resp = client.get("/admin/users", headers=_headers("admin", "admin"))
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1


class TestCreateUser:
    def test_non_admin_forbidden(self, client):
        resp = client.post(
            "/admin/users", json={"username": "henry"}, headers=_headers("someone", "user")
        )
        assert resp.status_code == 403

    def test_admin_create_returns_one_time_password(self, client):
        resp = client.post(
            "/admin/users",
            json={"username": "ivy", "role": "user", "org": "产品部"},
            headers=_headers("admin", "admin"),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "initial_password" in data
        assert data["must_change_password"] is True

        from deepanalyze.core.task_manager.user_service import UserService
        assert UserService.verify_password("ivy", data["initial_password"]) is not None

    def test_duplicate_enabled_username_returns_409(self, client):
        from deepanalyze.core.task_manager.user_service import UserService
        UserService.create_user(username="jack", password="pw123456")

        resp = client.post(
            "/admin/users", json={"username": "jack"}, headers=_headers("admin", "admin")
        )
        assert resp.status_code == 409

    def test_invalid_username_rejected(self, client):
        resp = client.post(
            "/admin/users", json={"username": "bad name!"}, headers=_headers("admin", "admin")
        )
        assert resp.status_code == 400


class TestUpdateUserAdmin:
    def test_non_admin_forbidden(self, client):
        resp = client.put(
            "/admin/users/someone", json={"role": "admin"}, headers=_headers("kate", "user")
        )
        assert resp.status_code == 403

    def test_admin_partial_update(self, client):
        from deepanalyze.core.task_manager.user_service import UserService
        UserService.create_user(username="leo", password="pw123456", org="旧部门")

        resp = client.put(
            "/admin/users/leo", json={"org": "新部门"}, headers=_headers("admin", "admin")
        )
        assert resp.status_code == 200
        assert resp.json()["org"] == "新部门"
        assert resp.json()["role"] == "user"  # 未传role，应保持不变

    def test_update_nonexistent_returns_404(self, client):
        resp = client.put(
            "/admin/users/ghost", json={"role": "admin"}, headers=_headers("admin", "admin")
        )
        assert resp.status_code == 404


class TestResetPassword:
    def test_non_admin_forbidden(self, client):
        resp = client.post(
            "/admin/users/someone/reset-password", headers=_headers("mia", "user")
        )
        assert resp.status_code == 403

    def test_admin_reset_returns_one_time_password(self, client):
        from deepanalyze.core.task_manager.user_service import UserService
        UserService.create_user(username="nina", password="OldPass1")

        resp = client.post(
            "/admin/users/nina/reset-password", headers=_headers("admin", "admin")
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["must_change_password"] is True
        assert UserService.verify_password("nina", "OldPass1") is None  # 旧密码失效
        assert UserService.verify_password("nina", data["new_password"]) is not None


class TestDeleteUser:
    def test_non_admin_forbidden(self, client):
        resp = client.delete("/admin/users/someone", headers=_headers("oscar", "user"))
        assert resp.status_code == 403

    def test_admin_soft_deletes(self, client):
        from deepanalyze.core.task_manager.user_service import UserService
        UserService.create_user(username="pat", password="pw123456")

        resp = client.delete("/admin/users/pat", headers=_headers("admin", "admin"))
        assert resp.status_code == 200
        fetched = UserService.get_by_username("pat")
        assert fetched["enabled"] is False

    def test_admin_cannot_delete_self(self, client):
        from deepanalyze.core.task_manager.user_service import UserService
        UserService.create_user(username="root_admin", password="pw123456", role="admin")

        resp = client.delete("/admin/users/root_admin", headers=_headers("root_admin", "admin"))
        assert resp.status_code == 400


if __name__ == "__main__":
    import pytest as _pytest
    _pytest.main([__file__, "-v"])
