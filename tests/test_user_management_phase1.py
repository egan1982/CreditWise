"""
用户管理模块 批次1 Phase1/Phase3 验证测试

覆盖：
1. GET /auth/me — 单用户模式（无认证）下的安全降级行为
2. GET /sop/status/{execution_id} — 所有权校验（403越权拦截 / 本人通过 / admin豁免 / 单用户模式不受影响）

详见 docs/user_management_module_design.md §五
"""

import os
import sys
import pytest
from pathlib import Path

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _project_root)
sys.path.insert(0, os.path.join(_project_root, "API"))

from fastapi.testclient import TestClient


# =============================================================================
# 1. /auth/me 端点测试（单用户模式，即 ENABLE_AUTH 未设置/false）
# =============================================================================

class TestAuthMeEndpoint:
    @pytest.fixture(scope="class")
    def client(self):
        from API.main import create_app
        app = create_app()
        return TestClient(app)

    def test_auth_me_single_user_mode(self, client, monkeypatch):
        """单用户模式（ENABLE_AUTH=false/未设置）下，/auth/me 返回未认证态，不报错"""
        monkeypatch.delenv("ENABLE_AUTH", raising=False)
        response = client.get("/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["username"] is None
        assert data["authenticated"] is False


# =============================================================================
# 2. get_task_status 所有权校验测试（直接调用路由函数，绕过中间件层）
# =============================================================================

class _FakeState:
    def __init__(self, user):
        self.user = user


class _FakeRequest:
    """模拟 request.state.user，覆盖 认证中间件设置身份 的行为"""
    def __init__(self, user=None):
        self.state = _FakeState(user)


class TestTaskStatusOwnership:
    @pytest.fixture(autouse=True)
    def setup_execution(self):
        from deepanalyze.analysis.task_SOP.executor import ExecutionStore
        ExecutionStore._executions.clear()
        self.context = ExecutionStore.create(
            task_id="rule_mining",
            session_id="alice",
            params={},
            file_path="/tmp/test.csv",
        )
        yield
        ExecutionStore._executions.clear()

    @pytest.mark.asyncio
    async def test_owner_can_access(self):
        """本人（session_id/username一致）可正常访问"""
        from API.sop_api import get_task_status
        result = await get_task_status(
            self.context.execution_id, _FakeRequest(user={"username": "alice", "role": "user"})
        )
        assert result.execution_id == self.context.execution_id

    @pytest.mark.asyncio
    async def test_non_owner_forbidden(self):
        """非本人访问他人execution应403"""
        from fastapi import HTTPException
        from API.sop_api import get_task_status
        with pytest.raises(HTTPException) as exc_info:
            await get_task_status(
                self.context.execution_id, _FakeRequest(user={"username": "bob", "role": "user"})
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_bypasses_ownership_check(self):
        """admin角色可查看任意用户的execution"""
        from API.sop_api import get_task_status
        result = await get_task_status(
            self.context.execution_id, _FakeRequest(user={"username": "bob", "role": "admin"})
        )
        assert result.execution_id == self.context.execution_id

    @pytest.mark.asyncio
    async def test_single_user_mode_not_affected(self):
        """单用户模式（request.state 无 user 属性）不受所有权校验影响"""
        from API.sop_api import get_task_status
        result = await get_task_status(self.context.execution_id, _FakeRequest(user=None))
        assert result.execution_id == self.context.execution_id

    @pytest.mark.asyncio
    async def test_nonexistent_execution_still_404(self):
        """execution_id不存在时仍应404（校验不应遮蔽原有404逻辑）"""
        from fastapi import HTTPException
        from API.sop_api import get_task_status
        with pytest.raises(HTTPException) as exc_info:
            await get_task_status("does-not-exist", _FakeRequest(user={"username": "alice", "role": "user"}))
        assert exc_info.value.status_code == 404


# =============================================================================
# 3. utils.resolve_owned_session_id / enforce_path_ownership 单测
# =============================================================================

class TestResolveOwnedSessionId:
    def test_single_user_mode_passthrough(self):
        """单用户模式（无 request.state.user）：原样返回客户端传入值"""
        from utils import resolve_owned_session_id
        assert resolve_owned_session_id(_FakeRequest(user=None), "client_supplied") == "client_supplied"

    def test_non_admin_forced_to_own_username(self):
        """非admin：无论客户端传什么，强制覆盖为自己的用户名"""
        from utils import resolve_owned_session_id
        req = _FakeRequest(user={"username": "alice", "role": "user"})
        assert resolve_owned_session_id(req, "bob") == "alice"
        assert resolve_owned_session_id(req, "default") == "alice"

    def test_admin_passthrough(self):
        """admin：保留客户端传入值（可查看指定用户数据）"""
        from utils import resolve_owned_session_id
        req = _FakeRequest(user={"username": "admin", "role": "admin"})
        assert resolve_owned_session_id(req, "bob") == "bob"

    def test_non_admin_empty_client_value_still_forced(self):
        """非admin且客户端未传值（None/空）：仍应派生为自己的用户名，而非空值"""
        from utils import resolve_owned_session_id
        req = _FakeRequest(user={"username": "alice", "role": "user"})
        assert resolve_owned_session_id(req, None) == "alice"
        assert resolve_owned_session_id(req, "") == "alice"


class TestEnforcePathOwnership:
    def test_single_user_mode_no_error(self):
        from utils import enforce_path_ownership
        enforce_path_ownership(_FakeRequest(user=None), "someone/file.csv")  # 不应抛异常

    def test_admin_no_error(self):
        from utils import enforce_path_ownership
        req = _FakeRequest(user={"username": "admin", "role": "admin"})
        enforce_path_ownership(req, "someone_else/file.csv")  # 不应抛异常

    def test_owner_no_error(self):
        from utils import enforce_path_ownership
        req = _FakeRequest(user={"username": "alice", "role": "user"})
        enforce_path_ownership(req, "alice/file.csv")  # 不应抛异常

    def test_non_owner_forbidden(self):
        from fastapi import HTTPException
        from utils import enforce_path_ownership
        req = _FakeRequest(user={"username": "alice", "role": "user"})
        with pytest.raises(HTTPException) as exc_info:
            enforce_path_ownership(req, "bob/secret.csv")
        assert exc_info.value.status_code == 403


# =============================================================================
# 4. sop_api.py 新增/所有权相关端点 单测
# =============================================================================

class TestListExecutionsOwnership:
    @pytest.fixture(autouse=True)
    def setup_executions(self):
        from deepanalyze.analysis.task_SOP.executor import ExecutionStore
        ExecutionStore._executions.clear()
        ExecutionStore.create(task_id="rule_mining", session_id="alice", params={}, file_path="/tmp/a.csv")
        ExecutionStore.create(task_id="rule_mining", session_id="bob", params={}, file_path="/tmp/b.csv")
        yield
        ExecutionStore._executions.clear()

    @pytest.mark.asyncio
    async def test_non_admin_only_sees_own_executions_regardless_of_query_param(self):
        """非admin传入他人session_id查询参数也会被忽略，强制只看自己的"""
        from API.sop_api import list_executions
        result = await list_executions(
            http_request=_FakeRequest(user={"username": "alice", "role": "user"}),
            session_id="bob",  # 尝试查看bob的任务，应被忽略
        )
        assert all(r["session_id"] == "alice" for r in result)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_admin_sees_all_when_no_filter(self):
        from API.sop_api import list_executions
        result = await list_executions(
            http_request=_FakeRequest(user={"username": "admin", "role": "admin"}),
            session_id=None,
        )
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_admin_can_filter_by_specific_user(self):
        from API.sop_api import list_executions
        result = await list_executions(
            http_request=_FakeRequest(user={"username": "admin", "role": "admin"}),
            session_id="bob",
        )
        assert len(result) == 1
        assert result[0]["session_id"] == "bob"

    @pytest.mark.asyncio
    async def test_single_user_mode_sees_all(self):
        from API.sop_api import list_executions
        result = await list_executions(http_request=_FakeRequest(user=None), session_id=None)
        assert len(result) == 2


class TestCancelExecutionOwnership:
    @pytest.fixture(autouse=True)
    def setup_execution(self):
        from deepanalyze.analysis.task_SOP.executor import ExecutionStore
        ExecutionStore._executions.clear()
        self.context = ExecutionStore.create(
            task_id="rule_mining", session_id="alice", params={}, file_path="/tmp/a.csv"
        )
        yield
        ExecutionStore._executions.clear()

    @pytest.mark.asyncio
    async def test_non_owner_cannot_cancel(self):
        from fastapi import HTTPException
        from API.sop_api import cancel_execution
        with pytest.raises(HTTPException) as exc_info:
            await cancel_execution(
                self.context.execution_id, _FakeRequest(user={"username": "bob", "role": "user"})
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_owner_can_cancel(self):
        from API.sop_api import cancel_execution
        result = await cancel_execution(
            self.context.execution_id, _FakeRequest(user={"username": "alice", "role": "user"})
        )
        assert "deleted" in result["message"]

    @pytest.mark.asyncio
    async def test_admin_can_cancel_others(self):
        from API.sop_api import cancel_execution
        result = await cancel_execution(
            self.context.execution_id, _FakeRequest(user={"username": "admin", "role": "admin"})
        )
        assert "deleted" in result["message"]


# =============================================================================
# 5. main.py workspace 路由 所有权强制落地 端到端测试
# =============================================================================

class TestWorkspaceRoutesOwnership:
    """通过真实 TestClient + 模拟中间件注入身份，验证 main.py 中10个 workspace
    路由的 resolve_owned_session_id 改造是否端到端生效（非admin传入他人session_id
    应被忽略，实际操作的是自己名下的workspace目录）。
    """

    @pytest.fixture(scope="class")
    def client_and_workspace_root(self, tmp_path_factory):
        import utils as _utils
        tmp_root = tmp_path_factory.mktemp("workspace_ownership_test")
        # 覆盖 workspace 根目录，避免污染真实 workspace/ 目录
        # 注意：utils.py 用 "from config import WORKSPACE_BASE_DIR" 绑定了局部名字，
        # 必须直接patch utils模块自身的这个名字才能生效（patch config模块不会传导）
        _utils.WORKSPACE_BASE_DIR = str(tmp_root)

        from API.main import create_app
        app = create_app()

        @app.middleware("http")
        async def _inject_fake_user(request, call_next):
            # 测试专用：通过自定义 header 模拟已登录身份，绕过真实认证中间件
            username = request.headers.get("x-test-username")
            role = request.headers.get("x-test-role", "user")
            if username:
                request.state.user = {"username": username, "role": role}
            return await call_next(request)

        return TestClient(app), tmp_root

    def test_upload_then_list_isolated_by_identity(self, client_and_workspace_root):
        """alice上传文件后，尝试以 session_id=bob 查询文件列表（越权嘗試），
        实际应仍然落在 alice 目录下，bob 看不到 alice 的文件"""
        client, tmp_root = client_and_workspace_root

        upload_resp = client.post(
            "/workspace/upload",
            params={"session_id": "bob"},  # 越权尝试：冒充写入bob的目录
            files={"files": ("test.txt", b"hello", "text/plain")},
            headers={"x-test-username": "alice", "x-test-role": "user"},
        )
        assert upload_resp.status_code == 200
        assert upload_resp.json()["files"][0]["status"] == "success"

        # 文件应实际落在 alice 目录，而不是 bob 目录
        assert (tmp_root / "alice" / "test.txt").exists()
        assert not (tmp_root / "bob" / "test.txt").exists()

        # bob 查询自己的文件列表，看不到 alice 上传的文件
        bob_files = client.get(
            "/workspace/files",
            params={"session_id": "bob"},
            headers={"x-test-username": "bob", "x-test-role": "user"},
        )
        assert bob_files.status_code == 200
        assert bob_files.json()["files"] == []

        # alice 查询自己的文件列表，能看到刚上传的文件
        alice_files = client.get(
            "/workspace/files",
            params={"session_id": "alice"},
            headers={"x-test-username": "alice", "x-test-role": "user"},
        )
        assert alice_files.status_code == 200
        assert len(alice_files.json()["files"]) == 1
        assert alice_files.json()["files"][0]["name"] == "test.txt"

    def test_admin_can_access_specified_user_workspace(self, client_and_workspace_root):
        """admin可通过session_id参数显式查看指定用户的workspace"""
        client, tmp_root = client_and_workspace_root
        resp = client.get(
            "/workspace/files",
            params={"session_id": "alice"},
            headers={"x-test-username": "admin", "x-test-role": "admin"},
        )
        assert resp.status_code == 200
        assert len(resp.json()["files"]) == 1

    def test_single_user_mode_unaffected(self, client_and_workspace_root):
        """未携带模拟身份header（等同单用户模式）：维持现状，按传入session_id操作"""
        client, tmp_root = client_and_workspace_root
        resp = client.get("/workspace/files", params={"session_id": "alice"})
        assert resp.status_code == 200
        assert len(resp.json()["files"]) == 1


if __name__ == "__main__":
    import pytest as _pytest
    _pytest.main([__file__, "-v"])
