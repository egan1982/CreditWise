"""
Basic Auth 认证中间件测试

覆盖 auth_middleware.py 的所有分支路径：
1. 白名单路由放行
2. OPTIONS 预检放行
3. 无 Authorization → 401
4. Base64 解码失败 → 401
5. 账户锁定 → 429
6. bcrypt 验证失败 → 401
7. bcrypt 验证成功 → 放行
8. Admin 路由 + admin 角色 → 放行
9. Admin 路由 + user 角色 → 403
10. 锁定超时后自动解锁
"""

import base64
import os
import sys
import time
import pytest

# 确保项目根目录和 API 目录在 sys.path 中
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _project_root)
sys.path.insert(0, os.path.join(_project_root, "API"))

import bcrypt
from fastapi import FastAPI
from fastapi.testclient import TestClient

from API.auth_middleware import SimpleAuth, BasicAuthMiddleware, _is_whitelisted, _is_admin_route


# =============================================================================
# 测试辅助
# =============================================================================

def _make_basic_header(username: str, password: str) -> dict:
    """构造 Basic Auth header"""
    encoded = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {encoded}"}


def _hash_password(password: str) -> str:
    """生成 bcrypt 哈希"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


# 测试用的用户配置
TEST_ADMIN_PASSWORD = "admin123"
TEST_USER_PASSWORD = "user123"


@pytest.fixture
def test_config(tmp_path):
    """创建临时的 users.yaml 配置"""
    import yaml

    config = {
        "users": [
            {
                "username": "admin",
                "password_hash": _hash_password(TEST_ADMIN_PASSWORD),
                "role": "admin",
                "description": "Test admin",
            },
            {
                "username": "testuser",
                "password_hash": _hash_password(TEST_USER_PASSWORD),
                "role": "user",
                "description": "Test user",
            },
        ],
        "settings": {
            "max_login_failures": 3,
            "lockout_duration_minutes": 1,
        },
    }

    config_file = tmp_path / "users.yaml"
    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump(config, f)

    return config_file


@pytest.fixture
def app_with_auth(test_config, monkeypatch):
    """创建带认证中间件的测试 FastAPI 应用"""
    import API.auth_middleware as auth_mod

    # 让 _find_config_path 返回我们的临时配置文件
    monkeypatch.setattr(auth_mod, "_find_config_path", lambda: test_config)

    app = FastAPI()
    auth = SimpleAuth()
    app.add_middleware(BasicAuthMiddleware, auth=auth)

    # 注册测试路由
    @app.get("/health")
    def health():
        return {"status": "healthy"}

    @app.get("/docs")
    def docs():
        return {"docs": True}

    @app.get("/")
    def root():
        return {"message": "root"}

    @app.get("/v1/chat/completions")
    def chat():
        return {"message": "chat"}

    @app.get("/sop/status/exec123/stream")
    def sse_stream():
        return {"stream": True}

    @app.get("/llm-manager/api/manage/channels")
    def manage_channels():
        return {"channels": []}

    @app.get("/llm-manager/api/logs")
    def logs():
        return {"logs": []}

    @app.get("/llm-manager/")
    def llm_manager_page():
        return {"page": "llm-manager"}

    @app.get("/workspace/files")
    def workspace_files():
        return {"files": []}

    return app, auth


@pytest.fixture
def client(app_with_auth):
    """TestClient"""
    app, _ = app_with_auth
    return TestClient(app)


@pytest.fixture
def auth_instance(app_with_auth):
    """SimpleAuth 实例"""
    _, auth = app_with_auth
    return auth


# =============================================================================
# 测试用例
# =============================================================================


class TestWhitelistRoutes:
    """测试 #1: 白名单路由放行"""

    def test_health_no_auth(self, client):
        """#1 /health 无需认证"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_docs_no_auth(self, client):
        """#1 /docs 无需认证"""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_sse_stream_no_auth(self, client):
        """#1 SSE 端点无需认证"""
        response = client.get("/sop/status/exec123/stream")
        assert response.status_code == 200


class TestOptionsPreflightPass:
    """测试 #2: OPTIONS 预检放行"""

    def test_options_no_auth(self, client):
        """#2 CORS preflight 不被拦截"""
        response = client.options(
            "/v1/chat/completions",
            headers={"Origin": "http://localhost:3000"},
        )
        # OPTIONS 应该放行（不返回 401）
        assert response.status_code != 401


class TestMissingAuthorization:
    """测试 #3: 无 Authorization → 401"""

    def test_no_auth_header(self, client):
        """#3 无认证 header 返回 401"""
        response = client.get("/")
        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers

    def test_401_has_basic_challenge(self, client):
        """#3 401 响应包含 Basic realm"""
        response = client.get("/workspace/files")
        assert response.status_code == 401
        assert "Basic" in response.headers.get("WWW-Authenticate", "")


class TestInvalidBase64:
    """测试 #4: Base64 解码失败 → 401"""

    def test_bad_base64(self, client):
        """#4 非法 Base64 编码"""
        response = client.get("/", headers={"Authorization": "Basic !!!invalid!!!"})
        assert response.status_code == 401

    def test_missing_colon(self, client):
        """#4 Base64 内容缺少冒号分隔符"""
        encoded = base64.b64encode(b"nocolon").decode()
        response = client.get("/", headers={"Authorization": f"Basic {encoded}"})
        assert response.status_code == 401


class TestAccountLockout:
    """测试 #5: 账户锁定 → 429"""

    def test_lockout_after_failures(self, client):
        """#5 连续失败后账户锁定"""
        wrong_headers = _make_basic_header("admin", "wrongpassword")

        # 触发 max_login_failures (3次) 失败
        for _ in range(3):
            resp = client.get("/", headers=wrong_headers)
            assert resp.status_code == 401

        # 第 4 次应该返回 429
        resp = client.get("/", headers=wrong_headers)
        assert resp.status_code == 429


class TestBcryptFailure:
    """测试 #6: bcrypt 验证失败 → 401"""

    def test_wrong_password(self, client):
        """#6 错误密码"""
        headers = _make_basic_header("admin", "wrongpassword")
        response = client.get("/", headers=headers)
        assert response.status_code == 401

    def test_nonexistent_user(self, client):
        """#6 不存在的用户"""
        headers = _make_basic_header("nobody", "password")
        response = client.get("/", headers=headers)
        assert response.status_code == 401


class TestBcryptSuccess:
    """测试 #7: bcrypt 验证成功 → 放行"""

    def test_admin_login(self, client):
        """#7 admin 正确密码"""
        headers = _make_basic_header("admin", TEST_ADMIN_PASSWORD)
        response = client.get("/", headers=headers)
        assert response.status_code == 200

    def test_user_login(self, client):
        """#7 普通用户正确密码"""
        headers = _make_basic_header("testuser", TEST_USER_PASSWORD)
        response = client.get("/workspace/files", headers=headers)
        assert response.status_code == 200


class TestAdminRouteAccess:
    """测试 #8 和 #9: Admin 路由角色检查"""

    def test_admin_can_access_manage(self, client):
        """#8 admin 可以访问管理路由"""
        headers = _make_basic_header("admin", TEST_ADMIN_PASSWORD)
        response = client.get("/llm-manager/api/manage/channels", headers=headers)
        assert response.status_code == 200

    def test_admin_can_access_logs(self, client):
        """#8 admin 可以访问日志"""
        headers = _make_basic_header("admin", TEST_ADMIN_PASSWORD)
        response = client.get("/llm-manager/api/logs", headers=headers)
        assert response.status_code == 200

    def test_user_blocked_from_manage(self, client):
        """#9 普通用户不能访问管理路由"""
        headers = _make_basic_header("testuser", TEST_USER_PASSWORD)
        response = client.get("/llm-manager/api/manage/channels", headers=headers)
        assert response.status_code == 403

    def test_user_blocked_from_llm_manager_page(self, client):
        """#9 普通用户不能访问 LLM Manager 页面"""
        headers = _make_basic_header("testuser", TEST_USER_PASSWORD)
        response = client.get("/llm-manager/", headers=headers)
        assert response.status_code == 403


class TestLockoutTimeout:
    """测试 #10: 锁定超时后自动解锁"""

    def test_unlock_after_timeout(self, auth_instance):
        """#10 锁定超时后重置"""
        # 手动设置锁定状态
        auth_instance._failure_tracker["admin"] = {
            "count": auth_instance.max_failures,
            "last_failure": time.time() - auth_instance.lockout_duration - 1,
        }

        # 超时后应该不再锁定
        assert not auth_instance._is_locked("admin")
        # 且计数器被重置
        assert auth_instance._failure_tracker["admin"]["count"] == 0


class TestHelperFunctions:
    """测试辅助函数"""

    def test_is_whitelisted(self):
        assert _is_whitelisted("/health") is True
        assert _is_whitelisted("/docs") is True
        assert _is_whitelisted("/v1/chat/completions") is False
        assert _is_whitelisted("/sop/status/abc/stream") is True
        assert _is_whitelisted("/sop/status/abc") is False

    def test_is_admin_route(self):
        assert _is_admin_route("/llm-manager/api/manage/channels") is True
        assert _is_admin_route("/llm-manager/api/logs") is True
        assert _is_admin_route("/llm-manager/") is True
        assert _is_admin_route("/llm-manager/api/proxy/chat/completions") is False
        assert _is_admin_route("/v1/chat/completions") is False
        assert _is_admin_route("/sop/execute") is False
