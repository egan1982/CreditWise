"""
用户管理模块 批次2 Phase9 验证测试

覆盖：
1. User ORM模型 + UserService 完整CRUD（create/get/list/update/set_password/soft_delete）
2. 用户名字符集校验（TD6）与冲突处理（UsernameConflictError区分enabled=1/0）
3. verify_password：正确密码/错误密码/禁用账户/valid_until过期
4. import_from_yaml_users：yaml导入的幂等性、占位符密码跳过、格式错误跳过

详见 docs/user_management_module_design.md §十三
"""

import os
import sys
import pytest

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _project_root)
sys.path.insert(0, os.path.join(_project_root, "API"))


@pytest.fixture
def isolated_task_db(tmp_path):
    """独立测试库，避免污染真实 task_manager.db（与 test_user_management_phase5_6.py
    保持一致的隔离方式，规避既有的跨用例状态污染问题）。
    """
    from deepanalyze.core.task_manager import database as _db_mod

    original = _db_mod._task_manager_db
    test_db_url = f"sqlite:///{tmp_path}/test_task_manager_phase9.db"
    test_db = _db_mod.TaskManagerDB(test_db_url)
    test_db.create_tables()
    _db_mod._task_manager_db = test_db
    yield test_db
    test_db.close()
    _db_mod._task_manager_db = original


# =============================================================================
# 1. validate_username（TD6 字符集约束）
# =============================================================================

class TestValidateUsername:
    def test_valid_username_passthrough(self):
        from deepanalyze.core.task_manager.user_service import validate_username
        assert validate_username("alice_01") == "alice_01"
        assert validate_username("zhang-san") == "zhang-san"

    def test_empty_rejected(self):
        from deepanalyze.core.task_manager.user_service import validate_username
        with pytest.raises(ValueError):
            validate_username("")

    def test_invalid_chars_rejected(self):
        from deepanalyze.core.task_manager.user_service import validate_username
        with pytest.raises(ValueError):
            validate_username("zhang.san@company.com")
        with pytest.raises(ValueError):
            validate_username("有空格 name")


# =============================================================================
# 2. UserService.create_user / get_by_username / list_users
# =============================================================================

class TestCreateAndGetUser:
    def test_create_and_get(self, isolated_task_db):
        from deepanalyze.core.task_manager.user_service import UserService
        created = UserService.create_user(
            username="alice", password="Secret123", role="user",
            org="风控部", description="测试用户", created_by="admin",
        )
        assert created["username"] == "alice"
        assert created["role"] == "user"
        assert created["enabled"] is True
        assert created["must_change_password"] is False
        assert "password_hash" not in created  # create_user 返回值不含哈希

        fetched = UserService.get_by_username("alice")
        assert fetched["username"] == "alice"
        assert "password_hash" in fetched  # get_by_username 默认 include_hash=True

    def test_create_duplicate_enabled_raises_conflict(self, isolated_task_db):
        from deepanalyze.core.task_manager.user_service import UserService, UsernameConflictError
        UserService.create_user(username="bob", password="pw1")
        with pytest.raises(UsernameConflictError) as exc_info:
            UserService.create_user(username="bob", password="pw2")
        assert exc_info.value.existing_enabled is True

    def test_create_duplicate_disabled_raises_conflict_with_flag(self, isolated_task_db):
        from deepanalyze.core.task_manager.user_service import UserService, UsernameConflictError
        UserService.create_user(username="carol", password="pw1")
        UserService.soft_delete("carol")
        with pytest.raises(UsernameConflictError) as exc_info:
            UserService.create_user(username="carol", password="pw2")
        assert exc_info.value.existing_enabled is False

    def test_create_invalid_username_rejected(self, isolated_task_db):
        from deepanalyze.core.task_manager.user_service import UserService
        with pytest.raises(ValueError):
            UserService.create_user(username="bad name!", password="pw1")

    def test_create_invalid_role_rejected(self, isolated_task_db):
        from deepanalyze.core.task_manager.user_service import UserService
        with pytest.raises(ValueError):
            UserService.create_user(username="dave", password="pw1", role="superuser")

    def test_get_nonexistent_returns_none(self, isolated_task_db):
        from deepanalyze.core.task_manager.user_service import UserService
        assert UserService.get_by_username("ghost") is None

    def test_list_users_pagination_and_filter(self, isolated_task_db):
        from deepanalyze.core.task_manager.user_service import UserService
        UserService.create_user(username="u1", password="pw")
        UserService.create_user(username="u2", password="pw")
        UserService.create_user(username="u3", password="pw")
        UserService.soft_delete("u3")

        all_result = UserService.list_users(limit=10, offset=0, include_disabled=True)
        assert all_result["total"] == 3

        enabled_only = UserService.list_users(limit=10, offset=0, include_disabled=False)
        assert enabled_only["total"] == 2

        page1 = UserService.list_users(limit=1, offset=0, include_disabled=True)
        assert len(page1["items"]) == 1


# =============================================================================
# 3. UserService.update_user / update_profile
# =============================================================================

class TestUpdateUser:
    def test_update_role_and_org(self, isolated_task_db):
        from deepanalyze.core.task_manager.user_service import UserService
        UserService.create_user(username="eve", password="pw", role="user")
        updated = UserService.update_user("eve", role="admin", org="安全部", updated_by="admin")
        assert updated["role"] == "admin"
        assert updated["org"] == "安全部"

    def test_update_valid_until_explicit_none_clears_it(self, isolated_task_db):
        from deepanalyze.core.task_manager.user_service import UserService
        UserService.create_user(username="frank", password="pw", valid_until="2026-12-31")
        fetched = UserService.get_by_username("frank")
        assert fetched["valid_until"] == "2026-12-31"

        # 显式传 None 表示"改为永久有效"，与"不传该参数=不修改"是两种不同语义
        UserService.update_user("frank", valid_until=None)
        fetched2 = UserService.get_by_username("frank")
        assert fetched2["valid_until"] is None

    def test_update_omitted_valid_until_not_modified(self, isolated_task_db):
        from deepanalyze.core.task_manager.user_service import UserService
        UserService.create_user(username="grace", password="pw", valid_until="2026-06-01")
        UserService.update_user("grace", org="新部门")  # 不传 valid_until
        fetched = UserService.get_by_username("grace")
        assert fetched["valid_until"] == "2026-06-01"  # 应保持不变

    def test_update_nonexistent_raises(self, isolated_task_db):
        from deepanalyze.core.task_manager.user_service import UserService
        with pytest.raises(ValueError):
            UserService.update_user("ghost", role="admin")

    def test_update_profile_only_touches_allowed_fields(self, isolated_task_db):
        from deepanalyze.core.task_manager.user_service import UserService
        UserService.create_user(username="henry", password="pw", role="user")
        UserService.update_profile("henry", display_name="Henry H.", org="产品部", description="喜欢猫")
        fetched = UserService.get_by_username("henry")
        assert fetched["display_name"] == "Henry H."
        assert fetched["org"] == "产品部"
        assert fetched["role"] == "user"  # 角色不受影响（update_profile签名根本不接受role）


# =============================================================================
# 4. UserService.verify_password（登录场景）
# =============================================================================

class TestVerifyPassword:
    def test_correct_password_succeeds(self, isolated_task_db):
        from deepanalyze.core.task_manager.user_service import UserService
        UserService.create_user(username="ivy", password="CorrectPass1")
        result = UserService.verify_password("ivy", "CorrectPass1")
        assert result is not None
        assert result["username"] == "ivy"
        assert "password_hash" not in result

    def test_wrong_password_fails(self, isolated_task_db):
        from deepanalyze.core.task_manager.user_service import UserService
        UserService.create_user(username="jack", password="CorrectPass1")
        assert UserService.verify_password("jack", "WrongPass") is None

    def test_nonexistent_user_fails(self, isolated_task_db):
        from deepanalyze.core.task_manager.user_service import UserService
        assert UserService.verify_password("ghost", "anything") is None

    def test_disabled_account_fails(self, isolated_task_db):
        from deepanalyze.core.task_manager.user_service import UserService
        UserService.create_user(username="kate", password="pw123456")
        UserService.soft_delete("kate")
        assert UserService.verify_password("kate", "pw123456") is None

    def test_expired_account_fails(self, isolated_task_db):
        from deepanalyze.core.task_manager.user_service import UserService
        UserService.create_user(username="leo", password="pw123456", valid_until="2020-01-01")
        assert UserService.verify_password("leo", "pw123456") is None

    def test_future_valid_until_still_succeeds(self, isolated_task_db):
        from deepanalyze.core.task_manager.user_service import UserService
        UserService.create_user(username="mia", password="pw123456", valid_until="2099-01-01")
        assert UserService.verify_password("mia", "pw123456") is not None


# =============================================================================
# 5. UserService.set_password / soft_delete
# =============================================================================

class TestSetPasswordAndSoftDelete:
    def test_set_password_changes_login(self, isolated_task_db):
        from deepanalyze.core.task_manager.user_service import UserService
        UserService.create_user(username="nina", password="OldPass1")
        UserService.set_password("nina", "NewPass2", must_change_password=True)

        assert UserService.verify_password("nina", "OldPass1") is None
        assert UserService.verify_password("nina", "NewPass2") is not None
        assert UserService.get_by_username("nina")["must_change_password"] is True

    def test_soft_delete_then_verify_fails_but_record_remains(self, isolated_task_db):
        from deepanalyze.core.task_manager.user_service import UserService
        UserService.create_user(username="oscar", password="pw123456")
        UserService.soft_delete("oscar", deleted_by="admin")

        assert UserService.verify_password("oscar", "pw123456") is None
        # 软删除后记录仍存在（供审计/账户合并等场景使用），只是 enabled=False
        fetched = UserService.get_by_username("oscar", include_disabled=True)
        assert fetched is not None
        assert fetched["enabled"] is False


# =============================================================================
# 6. import_from_yaml_users（Phase9 迁移脚本核心逻辑）
# =============================================================================

class TestImportFromYamlUsers:
    def test_basic_import(self, isolated_task_db):
        from deepanalyze.core.task_manager.user_service import UserService
        yaml_users = [
            {"username": "admin", "password_hash": "$2b$12$realhashvalue", "role": "admin", "valid_until": ""},
            {"username": "user1", "password_hash": "$2b$12$anotherrealhash", "role": "user", "valid_until": "2026-12-31"},
        ]
        result = UserService.import_from_yaml_users(yaml_users)
        assert result["imported"] == ["admin", "user1"]
        assert result["skipped_existing"] == []
        assert result["errors"] == []

        admin = UserService.get_by_username("admin")
        assert admin["role"] == "admin"
        assert admin["valid_until"] is None
        user1 = UserService.get_by_username("user1")
        assert user1["valid_until"] == "2026-12-31"

    def test_idempotent_rerun_skips_existing(self, isolated_task_db):
        from deepanalyze.core.task_manager.user_service import UserService
        yaml_users = [{"username": "pat", "password_hash": "$2b$12$realhash", "role": "user"}]
        UserService.import_from_yaml_users(yaml_users)
        # 第二次以不同哈希重跑，应跳过而非覆盖（不改变已有账户，允许运维重复执行迁移脚本）
        result2 = UserService.import_from_yaml_users(
            [{"username": "pat", "password_hash": "$2b$12$differenthash", "role": "admin"}]
        )
        assert result2["imported"] == []
        assert result2["skipped_existing"] == ["pat"]
        fetched = UserService.get_by_username("pat")
        assert fetched["role"] == "user"  # 未被第二次导入覆盖

    def test_placeholder_password_skipped_with_error(self, isolated_task_db):
        from deepanalyze.core.task_manager.user_service import UserService
        yaml_users = [{"username": "quinn", "password_hash": "$2b$12$PLACEHOLDER_USE_hash_password_py", "role": "user"}]
        result = UserService.import_from_yaml_users(yaml_users)
        assert result["imported"] == []
        assert len(result["errors"]) == 1
        assert result["errors"][0]["username"] == "quinn"
        assert UserService.get_by_username("quinn") is None

    def test_invalid_username_in_yaml_skipped_with_error(self, isolated_task_db):
        from deepanalyze.core.task_manager.user_service import UserService
        yaml_users = [{"username": "bad name!", "password_hash": "$2b$12$realhash", "role": "user"}]
        result = UserService.import_from_yaml_users(yaml_users)
        assert result["imported"] == []
        assert len(result["errors"]) == 1

    def test_imported_user_must_change_password_false(self, isolated_task_db):
        """存量账户迁移不应强制改密，避免打断现有用户的正常使用（不同于新建/重置密码场景）"""
        from deepanalyze.core.task_manager.user_service import UserService
        UserService.import_from_yaml_users(
            [{"username": "rachel", "password_hash": "$2b$12$realhash", "role": "user"}]
        )
        assert UserService.get_by_username("rachel")["must_change_password"] is False


if __name__ == "__main__":
    import pytest as _pytest
    _pytest.main([__file__, "-v"])
