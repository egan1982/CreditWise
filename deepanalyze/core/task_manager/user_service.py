# -*- coding: utf-8 -*-
"""
用户管理模块 批次2 Phase9/10：账户 CRUD 服务

提供 `users` 表的完整生命周期管理，供以下两处调用：
1. `API/auth_middleware.py::SimpleAuth`（Phase10 改造后）：登录校验优先查本表，
   查不到（或表为空，如迁移前的过渡期）时回退到 config/users.yaml。
2. `API/user_admin_api.py`（Phase10 新增）：`/auth/*` 自助接口 + `/admin/users` 管理接口。

设计要点（对齐 docs/user_management_module_design.md §十三/§十四/§十六）：
- username 创建后不可变更，字符集约束 `^[a-zA-Z0-9_-]+$`（TD6），与批次1的
  session_id/workspace目录名兼容，避免路径注入。
- 密码只接受明文入口，本模块内部统一调用 bcrypt 加盐哈希；不接受调用方直传哈希
  （唯一例外：`import_from_yaml_users` 迁移导入时 yaml 里已经是哈希值，直接搬运）。
- 删除账户 = `enabled=0` 软禁用，不物理删除（避免历史 task_records.session_id 悬空）。
- 用户名冲突：创建时若 username 已存在且 `enabled=0`，返回明确错误提示调用方选择
  "启用旧账户"或"换名"，不允许物理层 IntegrityError 泄露内部结构。
"""

from __future__ import annotations

import re
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

try:
    import bcrypt
except ImportError:  # pragma: no cover - 与 auth_middleware.py 保持一致的降级处理
    bcrypt = None  # type: ignore

from .database import get_task_manager_db
from .models import User

logger = logging.getLogger(__name__)

# username 字符集约束（TD6），与 API/utils.py::_SAFE_ID_PATTERN、
# user_migration_service.py::_SAFE_ID_PATTERN 保持完全一致
USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')


class UsernameConflictError(ValueError):
    """用户名已存在（区分 enabled=1 已占用 / enabled=0 可选择启用旧账户两种情况）"""

    def __init__(self, username: str, existing_enabled: bool):
        self.username = username
        self.existing_enabled = existing_enabled
        msg = (
            f"用户名 '{username}' 已被启用账户占用"
            if existing_enabled
            else f"用户名 '{username}' 曾被使用（当前已禁用），请选择启用旧账户或更换用户名"
        )
        super().__init__(msg)


def _require_bcrypt() -> None:
    if bcrypt is None:
        raise ImportError(
            "bcrypt 未安装！请运行: pip install bcrypt\n或: pip install -r requirements.txt"
        )


def validate_username(username: str) -> str:
    """校验用户名字符集（TD6），返回原值或抛 ValueError"""
    username = (username or "").strip()
    if not username:
        raise ValueError("用户名不能为空")
    if not USERNAME_PATTERN.match(username):
        raise ValueError(
            f"用户名 '{username}' 不合法：仅支持英文字母、数字、下划线、连字符，建议使用拼音或工号"
        )
    return username


def _hash_password(plain_password: str) -> str:
    _require_bcrypt()
    if not plain_password:
        raise ValueError("密码不能为空")
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _parse_valid_until(valid_until: Optional[str]) -> Optional[date]:
    """将 'YYYY-MM-DD' / '' / None 统一转为 date 或 None"""
    if not valid_until or not str(valid_until).strip():
        return None
    try:
        return date.fromisoformat(str(valid_until).strip())
    except ValueError:
        raise ValueError(f"valid_until 格式错误，应为 YYYY-MM-DD：{valid_until!r}")


def _user_to_dict(user: User, include_hash: bool = False) -> Dict[str, Any]:
    d = {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "role": user.role,
        "org": user.org,
        "description": user.description,
        "valid_until": user.valid_until.isoformat() if user.valid_until else None,
        "enabled": bool(user.enabled),
        "must_change_password": bool(user.must_change_password),
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        "created_by": user.created_by,
    }
    if include_hash:
        d["password_hash"] = user.password_hash
    return d


class UserService:
    """账户 CRUD 服务（classmethod 风格，对齐 TaskHistoryService 的既有约定）"""

    # -------------------------------------------------------------------
    # 查询
    # -------------------------------------------------------------------
    @classmethod
    def get_by_username(cls, username: str, include_disabled: bool = True) -> Optional[Dict[str, Any]]:
        """按用户名查询单个账户。include_disabled=False 时禁用账户返回 None（登录校验场景用）"""
        db = get_task_manager_db()
        with db.get_session() as session:
            user = session.query(User).filter(User.username == username).first()
            if user is None:
                return None
            if not include_disabled and not user.enabled:
                return None
            return _user_to_dict(user, include_hash=True)

    @classmethod
    def list_users(
        cls,
        limit: int = 50,
        offset: int = 0,
        include_disabled: bool = True,
    ) -> Dict[str, Any]:
        """分页列出账户（供 admin 用户管理页面）"""
        db = get_task_manager_db()
        with db.get_session() as session:
            query = session.query(User)
            if not include_disabled:
                query = query.filter(User.enabled == True)  # noqa: E712
            total = query.count()
            users = (
                query.order_by(User.created_at.asc())
                .offset(offset)
                .limit(limit)
                .all()
            )
            return {
                "total": total,
                "items": [_user_to_dict(u) for u in users],
            }

    @classmethod
    def count_users(cls) -> int:
        """表中账户总数（用于判断迁移是否已执行过：0 = 尚未迁移，需回退读 yaml）"""
        db = get_task_manager_db()
        with db.get_session() as session:
            return session.query(User).count()

    # -------------------------------------------------------------------
    # 创建
    # -------------------------------------------------------------------
    @classmethod
    def create_user(
        cls,
        username: str,
        password: str,
        role: str = "user",
        org: Optional[str] = None,
        description: Optional[str] = None,
        valid_until: Optional[str] = None,
        display_name: Optional[str] = None,
        must_change_password: bool = False,
        created_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """创建新账户（明文密码入口，内部统一 bcrypt 哈希）

        Raises:
            ValueError: 用户名格式非法 / valid_until 格式非法
            UsernameConflictError: 用户名已存在（区分 enabled=1/0 两种情况）
        """
        username = validate_username(username)
        if role not in ("admin", "user"):
            raise ValueError(f"role 必须是 'admin' 或 'user'，得到: {role!r}")
        password_hash = _hash_password(password)
        # 试用版：所有新创建账户的到期日期强制设为 2026-10-31，
        # 忽略调用方传入的 valid_until 参数
        valid_until_date = _parse_valid_until("2026-10-31")

        db = get_task_manager_db()
        with db.get_session() as session:
            existing = session.query(User).filter(User.username == username).first()
            if existing is not None:
                raise UsernameConflictError(username, existing_enabled=bool(existing.enabled))

            user = User(
                username=username,
                display_name=display_name,
                password_hash=password_hash,
                role=role,
                org=org,
                description=description,
                valid_until=valid_until_date,
                enabled=True,
                must_change_password=must_change_password,
                created_by=created_by,
            )
            session.add(user)
            session.flush()  # 拿到 auto-increment id
            result = _user_to_dict(user)
        logger.info(f"[AUDIT] 创建账户: username={username}, role={role}, created_by={created_by}")
        return result

    # -------------------------------------------------------------------
    # 更新
    # -------------------------------------------------------------------
    @classmethod
    def update_user(
        cls,
        username: str,
        role: Optional[str] = None,
        org: Optional[str] = None,
        description: Optional[str] = None,
        valid_until: Optional[str] = ...,  # 用 ... 区分"不修改"与"显式设为空/永久有效"
        display_name: Optional[str] = None,
        enabled: Optional[bool] = None,
        updated_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """更新账户字段（不支持改 username，见 §十三）。仅传入的字段生效。"""
        db = get_task_manager_db()
        with db.get_session() as session:
            user = session.query(User).filter(User.username == username).first()
            if user is None:
                raise ValueError(f"用户不存在: {username}")

            if role is not None:
                if role not in ("admin", "user"):
                    raise ValueError(f"role 必须是 'admin' 或 'user'，得到: {role!r}")
                user.role = role
            if org is not None:
                user.org = org
            if description is not None:
                user.description = description
            # 试用版：valid_until 已被锁定为 2026-10-31，禁止通过 update_user 修改
            # （仅 create_user 时由本模块硬编码写入，无法通过 API 或数据库直接修改绕过）
            if valid_until is not ...:
                logger.warning(f"试用版拒绝修改 valid_until: username={username}, 请求值={valid_until}")
                # 静默忽略，不报错（前端不会感知，后端安全兜底）
            if display_name is not None:
                user.display_name = display_name
            if enabled is not None:
                user.enabled = enabled
            user.updated_at = datetime.now()
            session.flush()
            result = _user_to_dict(user)
        logger.info(f"[AUDIT] 更新账户: username={username}, updated_by={updated_by}, fields_changed=部分")
        return result

    @classmethod
    def update_profile(cls, username: str, display_name: Optional[str] = None,
                        org: Optional[str] = None, description: Optional[str] = None) -> Dict[str, Any]:
        """普通用户自助编辑个人信息（`/auth/profile`）：仅允许改 display_name/org/description，
        后端不接受 body 中出现的 username/role/valid_until/enabled 字段（由调用方在 API 层过滤，
        本方法签名本身也不暴露这些参数，双重防线）。
        """
        return cls.update_user(username, org=org, description=description, display_name=display_name)

    # -------------------------------------------------------------------
    # 密码
    # -------------------------------------------------------------------
    @classmethod
    def verify_password(cls, username: str, password: str) -> Optional[Dict[str, Any]]:
        """校验用户名+密码（登录场景用）。

        Returns:
            成功返回账户字典（不含 password_hash），以下任一情况返回 None：
            用户不存在 / 已禁用 / 密码错误 / 已过期(valid_until)
        """
        _require_bcrypt()
        user_dict = cls.get_by_username(username, include_disabled=True)
        if user_dict is None:
            bcrypt.hashpw(b"dummy_password", bcrypt.gensalt())  # 防时序攻击泄露用户名存在性
            return None
        if not user_dict["enabled"]:
            return None
        stored_hash = user_dict["password_hash"].encode("utf-8")
        try:
            if not bcrypt.checkpw(password.encode("utf-8"), stored_hash):
                return None
        except Exception:
            return None

        valid_until = user_dict.get("valid_until")
        if valid_until:
            try:
                if date.today() > date.fromisoformat(valid_until):
                    logger.warning(f"账户已过期，拒绝登录: username={username}, valid_until={valid_until}")
                    return None
            except ValueError:
                logger.error(f"users表 valid_until 格式异常，保守拒绝: username={username}, value={valid_until}")
                return None

        user_dict.pop("password_hash", None)
        return user_dict

    @classmethod
    def get_login_failure_reason(cls, username: str, password: str) -> str:
        """用户管理模块 批次2 补充加固（2026-07-03）：登录失败具体原因判定。

        背景：`verify_password` 对"密码错误/账户不存在/已禁用/已过期"统一返回
        `None`，导致过期账户即使输入完全正确的密码，前端也只能提示"用户名或
        密码错误"——用户实测反馈这个提示在账户过期场景下有误导性，容易被误以为
        是密码记错了，而不是账户本身已过期需要联系管理员处理。

        本方法仅在 `verify_password` 已返回 `None` 之后被调用（登录失败路径），
        用于给前端提供更准确的错误提示，供 `SimpleAuth.authenticate()` 构造
        detail 文案。

        安全边界：**只有当密码校验本身通过时**，才会区分返回"disabled"/
        "expired"这类账户状态信息；密码错误或用户不存在统一返回
        "invalid_credentials"——尚未持有正确密码的攻击者无法借此探测到"这个
        用户名存在""这个账户被禁用/过期"等信息，与既有的防时序攻击设计目标
        一致，不构成新的信息泄露面。
        """
        _require_bcrypt()
        user_dict = cls.get_by_username(username, include_disabled=True)
        if user_dict is None:
            bcrypt.hashpw(b"dummy_password", bcrypt.gensalt())  # 防时序攻击泄露用户名存在性
            return "invalid_credentials"

        stored_hash = user_dict.get("password_hash", "").encode("utf-8")
        try:
            if not bcrypt.checkpw(password.encode("utf-8"), stored_hash):
                return "invalid_credentials"
        except Exception:
            return "invalid_credentials"

        # 密码校验通过，才继续判断具体是"禁用"还是"过期"
        if not user_dict.get("enabled", True):
            return "disabled"

        valid_until = user_dict.get("valid_until")
        if valid_until:
            try:
                if date.today() > date.fromisoformat(valid_until):
                    return "expired"
            except ValueError:
                return "invalid_credentials"

        # 理论上不应到达此处（说明 verify_password 本应校验成功），保守兜底
        return "invalid_credentials"

    @classmethod
    def set_password(cls, username: str, new_password: str, must_change_password: bool = False) -> None:
        """管理员重置密码 / 用户自助改密 共用底层：明文入 → bcrypt 哈希 → 落库"""
        password_hash = _hash_password(new_password)
        db = get_task_manager_db()
        with db.get_session() as session:
            user = session.query(User).filter(User.username == username).first()
            if user is None:
                raise ValueError(f"用户不存在: {username}")
            user.password_hash = password_hash
            user.must_change_password = must_change_password
            user.updated_at = datetime.now()
        logger.info(f"[AUDIT] 密码变更: username={username}, must_change_password={must_change_password}")

    # -------------------------------------------------------------------
    # 删除（软禁用）
    # -------------------------------------------------------------------
    @classmethod
    def soft_delete(cls, username: str, deleted_by: Optional[str] = None) -> None:
        """软删除（enabled=0），不物理删除，避免历史 task_records.session_id 外键悬空"""
        db = get_task_manager_db()
        with db.get_session() as session:
            user = session.query(User).filter(User.username == username).first()
            if user is None:
                raise ValueError(f"用户不存在: {username}")
            user.enabled = False
            user.updated_at = datetime.now()
        logger.info(f"[AUDIT] 禁用账户: username={username}, deleted_by={deleted_by}")

    # -------------------------------------------------------------------
    # 批次1 兼容：从 yaml 迁移导入（Phase9 一次性脚本调用）
    # -------------------------------------------------------------------
    @classmethod
    def import_from_yaml_users(cls, yaml_users: List[Dict[str, Any]]) -> Dict[str, Any]:
        """一次性导入 config/users.yaml 中的用户列表（哈希值原样搬运，不重新加密）。

        幂等：已存在的 username 会跳过（不覆盖），返回结果中列出跳过项，
        方便重复执行迁移脚本时不产生副作用。

        Args:
            yaml_users: `users.yaml` 中 `users:` 列表，每项含
                username/password_hash/role/org/description/valid_until

        Returns:
            {"imported": [...], "skipped_existing": [...], "errors": [{"username":..., "error":...}]}
        """
        imported: List[str] = []
        skipped: List[str] = []
        errors: List[Dict[str, str]] = []

        db = get_task_manager_db()
        with db.get_session() as session:
            for raw in yaml_users:
                username = raw.get("username", "")
                try:
                    username = validate_username(username)
                except ValueError as e:
                    errors.append({"username": str(username), "error": str(e)})
                    continue

                existing = session.query(User).filter(User.username == username).first()
                if existing is not None:
                    skipped.append(username)
                    continue

                password_hash = raw.get("password_hash", "")
                if not password_hash or "PLACEHOLDER" in password_hash:
                    errors.append({"username": username, "error": "password_hash 缺失或为占位符，已跳过"})
                    continue

                try:
                    valid_until_date = _parse_valid_until(raw.get("valid_until"))
                except ValueError as e:
                    errors.append({"username": username, "error": str(e)})
                    continue

                user = User(
                    username=username,
                    display_name=None,
                    password_hash=password_hash,  # 哈希值原样搬运，不重新加密
                    role=raw.get("role", "user"),
                    org=raw.get("org") or None,
                    description=raw.get("description") or None,
                    valid_until=valid_until_date,
                    enabled=True,
                    must_change_password=False,  # 存量账户不强制改密，避免打断现有用户
                    created_by="migration",
                )
                session.add(user)
                imported.append(username)

        logger.info(
            f"[UserMigration] yaml->DB 导入完成: imported={len(imported)}, "
            f"skipped_existing={len(skipped)}, errors={len(errors)}"
        )
        return {"imported": imported, "skipped_existing": skipped, "errors": errors}
