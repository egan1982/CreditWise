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
def app_with_auth(test_config, tmp_path, monkeypatch):
    """创建带认证中间件的测试 FastAPI 应用"""
    import API.auth_middleware as auth_mod

    # 让 _find_config_path 返回我们的临时配置文件
    monkeypatch.setattr(auth_mod, "_find_config_path", lambda: test_config)

    # 用户管理模块 批次2 补充加固（2026-07-02）：账户锁定状态隔离。
    # 背景：_get_state_path() 硬编码返回真实项目路径 config/login_state.json，
    # 与本机开发服务器（甚至线上部署）读写的是同一份磁盘文件。TestAccountLockout
    # 类测试会故意连续失败登录触发"admin"账户锁定，若不隔离，这份锁定状态会真实写入
    # 磁盘——不仅污染后续在同一进程内运行的其他测试（会看到意外的429而非401/200，
    # 已实测复现），还可能在本机同时跑着真实开发服务器时，把正在被人工测试使用的
    # 真实"admin"账户凭空锁定。这里同样用 monkeypatch 让状态文件落在 tmp_path，
    # 与 _find_config_path 的隔离方式保持一致。
    state_path = tmp_path / "login_state.json"
    monkeypatch.setattr(auth_mod, "_get_state_path", lambda: state_path)

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
    """测试 #3: 无 Authorization → 401

    用户管理模块 批次2 补充加固（2026-07-02）：401 响应是否携带
    `WWW-Authenticate` 头，现在取决于请求是 AJAX/fetch 调用还是真实页面导航
    （见 `BasicAuthMiddleware.dispatch` 里 `is_html_navigation` 分支）——
    AJAX 调用不再带该头，避免浏览器抢先弹出原生认证框、打断前端自定义的
    `LoginDialog` 重试流程（原生弹窗在部分内嵌浏览器环境下会卡死无法交互）。
    真实页面导航（`Accept: text/html`）仍保留该头，走浏览器原生认证是预期行为。
    """

    def test_no_auth_header_ajax_no_www_authenticate(self, client):
        """#3 无认证 header，AJAX请求（无 text/html Accept）→ 401，不带 WWW-Authenticate"""
        response = client.get("/workspace/files")
        assert response.status_code == 401
        assert "WWW-Authenticate" not in response.headers

    def test_no_auth_header_html_navigation_has_www_authenticate(self, client):
        """#3 无认证 header，真实页面导航（Accept: text/html）→ 401，携带 Basic realm 挑战"""
        response = client.get("/workspace/files", headers={"Accept": "text/html"})
        assert response.status_code == 401
        assert "Basic" in response.headers.get("WWW-Authenticate", "")


class TestInvalidBase64:
    """测试 #4: Base64 解码失败 → 401"""

    def test_bad_base64(self, client):
        """#4 非法 Base64 编码"""
        response = client.get("/workspace/files", headers={"Authorization": "Basic !!!invalid!!!"})
        assert response.status_code == 401

    def test_missing_colon(self, client):
        """#4 Base64 内容缺少冒号分隔符"""
        encoded = base64.b64encode(b"nocolon").decode()
        response = client.get("/workspace/files", headers={"Authorization": f"Basic {encoded}"})
        assert response.status_code == 401


class TestAccountLockout:
    """测试 #5: 账户锁定 → 429"""

    def test_lockout_after_failures(self, client):
        """#5 连续失败后账户锁定"""
        wrong_headers = _make_basic_header("admin", "wrongpassword")

        # 触发 max_login_failures (3次) 失败
        for _ in range(3):
            resp = client.get("/workspace/files", headers=wrong_headers)
            assert resp.status_code == 401

        # 第 4 次应该返回 429
        resp = client.get("/workspace/files", headers=wrong_headers)
        assert resp.status_code == 429


class TestBcryptFailure:
    """测试 #6: bcrypt 验证失败 → 401"""

    def test_wrong_password(self, client):
        """#6 错误密码"""
        headers = _make_basic_header("admin", "wrongpassword")
        response = client.get("/workspace/files", headers=headers)
        assert response.status_code == 401

    def test_nonexistent_user(self, client):
        """#6 不存在的用户"""
        headers = _make_basic_header("nobody", "password")
        response = client.get("/workspace/files", headers=headers)
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


class TestAccountExpiry:
    """测试账户有效期控制（valid_until 字段）"""

    def _make_config_with_expiry(self, tmp_path, valid_until: str):
        """创建含有效期用户的临时配置"""
        import yaml
        config = {
            "users": [
                {
                    "username": "expuser",
                    "password_hash": _hash_password("testpass"),
                    "role": "user",
                    "valid_until": valid_until,
                },
            ],
            "settings": {"max_login_failures": 5, "lockout_duration_minutes": 15},
        }
        config_file = tmp_path / "users_expiry.yaml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config, f)
        return config_file

    def test_valid_account_not_expired(self, tmp_path, monkeypatch):
        """未过期账户可以正常登录"""
        from datetime import date, timedelta
        future_date = (date.today() + timedelta(days=30)).isoformat()
        config_file = self._make_config_with_expiry(tmp_path, future_date)

        import API.auth_middleware as auth_mod
        monkeypatch.setattr(auth_mod, "_find_config_path", lambda: config_file)
        auth = SimpleAuth()
        result = auth.verify("expuser", "testpass")
        assert result is not None
        assert result["username"] == "expuser"

    def test_expired_account_rejected(self, tmp_path, monkeypatch):
        """已过期账户被拒绝（昨天过期）"""
        from datetime import date, timedelta
        past_date = (date.today() - timedelta(days=1)).isoformat()
        config_file = self._make_config_with_expiry(tmp_path, past_date)

        import API.auth_middleware as auth_mod
        monkeypatch.setattr(auth_mod, "_find_config_path", lambda: config_file)
        auth = SimpleAuth()
        result = auth.verify("expuser", "testpass")
        assert result is None

    def test_expiry_today_still_valid(self, tmp_path, monkeypatch):
        """今天到期当天仍然有效"""
        from datetime import date
        today = date.today().isoformat()
        config_file = self._make_config_with_expiry(tmp_path, today)

        import API.auth_middleware as auth_mod
        monkeypatch.setattr(auth_mod, "_find_config_path", lambda: config_file)
        auth = SimpleAuth()
        result = auth.verify("expuser", "testpass")
        assert result is not None

    def test_empty_valid_until_permanent(self, tmp_path, monkeypatch):
        """valid_until 为空字符串 = 永久有效"""
        config_file = self._make_config_with_expiry(tmp_path, "")

        import API.auth_middleware as auth_mod
        monkeypatch.setattr(auth_mod, "_find_config_path", lambda: config_file)
        auth = SimpleAuth()
        result = auth.verify("expuser", "testpass")
        assert result is not None

    def test_invalid_date_format_rejected(self, tmp_path, monkeypatch):
        """valid_until 格式错误时保守拒绝"""
        config_file = self._make_config_with_expiry(tmp_path, "not-a-date")

        import API.auth_middleware as auth_mod
        monkeypatch.setattr(auth_mod, "_find_config_path", lambda: config_file)
        auth = SimpleAuth()
        result = auth.verify("expuser", "testpass")
        assert result is None
