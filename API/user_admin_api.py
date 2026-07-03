# -*- coding: utf-8 -*-
"""
用户管理模块 批次2 Phase10：账号管理 API

提供两类接口（详见 docs/user_management_module_design.md §十四）：
1. `/auth/*` 自助接口：已登录用户（任意角色）可用
   - GET  /auth/mode              探测是否启用认证（认证白名单，登录前即可调用）
   - PUT  /auth/profile            自助编辑 display_name/org/description
   - POST /auth/change-password   自助改密（复用 SimpleAuth 账户锁定机制，M19）
2. `/admin/users*` 管理接口：仅 admin（`API/auth_middleware.py` 的 ADMIN_ONLY_PREFIXES
   已将 `/admin/` 前缀纳入中间件强制校验，本文件路由函数内部再显式校验一次角色，
   双重防线——不可仅依赖中间件单一层，避免中间件配置遗漏导致越权）
   - GET    /admin/users                          分页列出账户
   - POST   /admin/users                          创建账户（随机密码一次性明文返回，TD4）
   - PUT    /admin/users/{username}                编辑角色/org/description/valid_until/enabled
   - POST   /admin/users/{username}/reset-password 重置密码（同样一次性明文返回，TD4）
   - DELETE /admin/users/{username}                软删除（enabled=0）

`/admin/users/merge`（账户合并）已在批次1 Phase6 实现于 `API/main.py`，不在本文件重复。

安全要点：
- 密码只接受明文入口，本文件不接受任何调用方直传哈希。
- 创建/重置密码生成的随机明文密码仅在本次响应中返回一次，不做任何持久化/日志记录。
- 单用户模式（ENABLE_AUTH=false，request.state 无 user 属性）下本文件全部接口返回
  400，明确提示该操作仅在多用户模式下可用（与批次1 claim-legacy-session 的处理方式一致）。
"""

from __future__ import annotations

import logging
import secrets
import string
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()

# 用户管理模块 批次2 Phase10：密码强度基线（§十八验收标准要求）
_MIN_PASSWORD_LENGTH = 6


def _require_multiuser_mode(request: Request) -> dict:
    """返回当前登录用户字典；单用户模式（无 request.state.user）时抛 400。"""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=400, detail="该操作仅在多用户模式下可用")
    return user


def _require_admin(request: Request) -> dict:
    """双重防线：中间件层 ADMIN_ONLY_PREFIXES 已拦截非admin请求到 /admin/*，
    这里再显式校验一次，避免因中间件配置遗漏导致越权（不可仅依赖单一层校验）。
    """
    user = _require_multiuser_mode(request)
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


def _validate_password_strength(password: str) -> None:
    if not password or len(password) < _MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"密码长度至少 {_MIN_PASSWORD_LENGTH} 位",
        )


def _generate_random_password(length: int = 12) -> str:
    """生成安全随机密码（字母+数字），用于新建账户/重置密码的一次性明文展示（TD4）"""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _get_user_service():
    from deepanalyze.core.task_manager.user_service import UserService
    return UserService


def _handle_username_conflict(exc: "Exception") -> None:
    """把 UsernameConflictError 映射为 409，区分 enabled=1（占用）/enabled=0（可选择启用旧账户）"""
    from deepanalyze.core.task_manager.user_service import UsernameConflictError

    if isinstance(exc, UsernameConflictError):
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    raise HTTPException(status_code=400, detail=str(exc)) from exc


# =============================================================================
# 请求体模型
# =============================================================================

class ProfileUpdateRequest(BaseModel):
    """`/auth/profile`：仅接受这三个字段，后端不接受 body 中出现的
    username/role/valid_until/enabled（本模型签名本身就不暴露这些字段，双重防线）"""
    display_name: Optional[str] = None
    org: Optional[str] = None
    description: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=1)


class CreateUserRequest(BaseModel):
    username: str
    role: str = "user"
    org: Optional[str] = None
    description: Optional[str] = None
    valid_until: Optional[str] = None
    display_name: Optional[str] = None


class UpdateUserRequest(BaseModel):
    """所有字段均可选，仅传入的字段生效（依赖 exclude_unset 区分"不修改"与"显式设为空"）"""
    role: Optional[str] = None
    org: Optional[str] = None
    description: Optional[str] = None
    valid_until: Optional[str] = None
    display_name: Optional[str] = None
    enabled: Optional[bool] = None


# =============================================================================
# /auth/mode — 认证白名单，登录前即可调用
# =============================================================================

@router.get("/auth/mode")
async def get_auth_mode() -> Dict[str, bool]:
    """供前端判断是否渲染登录框/账户相关UI。单用户模式下返回 auth_enabled=false，
    前端应完全不渲染登录/账户设置/用户管理等相关UI（详见 §2.4、§15.0）。
    """
    import os
    return {"auth_enabled": os.getenv("ENABLE_AUTH", "false").lower() == "true"}


# =============================================================================
# /auth/profile — 自助编辑个人信息
# =============================================================================

@router.put("/auth/profile")
async def update_own_profile(request: Request, body: ProfileUpdateRequest) -> Dict[str, Any]:
    """自助编辑个人信息：仅允许改 display_name/org/description。"""
    user = _require_multiuser_mode(request)
    UserService = _get_user_service()
    try:
        updated = UserService.update_profile(
            user["username"],
            display_name=body.display_name,
            org=body.org,
            description=body.description,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return updated


# =============================================================================
# /auth/change-password — 自助改密
# =============================================================================

@router.post("/auth/change-password")
async def change_own_password(request: Request, body: ChangePasswordRequest) -> Dict[str, str]:
    """自助改密：校验旧密码后 bcrypt 重新哈希。

    M19决策：旧密码校验复用 SimpleAuth 现有的账户锁定机制（按username计数），
    防止本接口被用来暴力破解旧密码——即多次旧密码校验失败也会触发账户锁定，
    与登录接口共享同一套 `_failure_tracker` 状态。
    """
    user = _require_multiuser_mode(request)
    username = user["username"]
    _validate_password_strength(body.new_password)

    UserService = _get_user_service()
    auth = getattr(request.app.state, "auth", None)

    if auth is not None and auth._is_locked(username):
        raise HTTPException(
            status_code=429,
            detail=f"账户已锁定，请 {auth.lockout_duration // 60} 分钟后重试",
        )

    verify_result = UserService.verify_password(username, body.old_password)
    if verify_result is None:
        if auth is not None:
            # CVM部署测试发现（2026-07-03）：_record_failure 签名新增 password
            # 参数（用于短时间窗口内同一份错误凭证的并发去重，详见
            # auth_middleware.py::_record_failure docstring），这里传入本次
            # 校验失败的旧密码
            auth._record_failure(username, body.old_password)
        raise HTTPException(status_code=400, detail="旧密码不正确")

    if auth is not None:
        auth._reset_failures(username)

    UserService.set_password(username, body.new_password, must_change_password=False)
    logger.info(f"[AUDIT] 用户自助改密: username={username}")
    return {"message": "密码修改成功"}


# =============================================================================
# /admin/users — 管理员账户 CRUD
# =============================================================================

@router.get("/admin/users")
async def list_users(request: Request, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
    """分页列出所有账户（含已禁用）"""
    _require_admin(request)
    UserService = _get_user_service()
    return UserService.list_users(limit=limit, offset=offset, include_disabled=True)


@router.post("/admin/users")
async def create_user(request: Request, body: CreateUserRequest) -> Dict[str, Any]:
    """创建账户：后端生成随机密码并一次性返回明文（TD4）+ must_change_password=true。

    Returns:
        账户信息 + 一次性 initial_password 字段（仅本次响应包含，不做任何持久化/日志记录明文）
    """
    admin_user = _require_admin(request)
    UserService = _get_user_service()

    initial_password = _generate_random_password()
    try:
        created = UserService.create_user(
            username=body.username,
            password=initial_password,
            role=body.role,
            org=body.org,
            description=body.description,
            valid_until=body.valid_until,
            display_name=body.display_name,
            must_change_password=True,
            created_by=admin_user["username"],
        )
    except ValueError as e:
        _handle_username_conflict(e)
        return  # pragma: no cover - _handle_username_conflict 总会抛异常，此行不可达

    created["initial_password"] = initial_password
    return created


@router.put("/admin/users/{username}")
async def update_user(request: Request, username: str, body: UpdateUserRequest) -> Dict[str, Any]:
    """编辑角色/org/description/valid_until/enabled（不支持改 username，见 §十三）"""
    admin_user = _require_admin(request)
    UserService = _get_user_service()

    fields = body.model_dump(exclude_unset=True)
    try:
        updated = UserService.update_user(
            username,
            role=fields.get("role"),
            org=fields.get("org"),
            description=fields.get("description"),
            valid_until=fields["valid_until"] if "valid_until" in fields else ...,
            display_name=fields.get("display_name"),
            enabled=fields.get("enabled"),
            updated_by=admin_user["username"],
        )
    except ValueError as e:
        raise HTTPException(status_code=404 if "不存在" in str(e) else 400, detail=str(e))
    return updated


@router.post("/admin/users/{username}/reset-password")
async def reset_user_password(request: Request, username: str) -> Dict[str, Any]:
    """重置任意用户密码：生成随机密码一次性返回明文 + 设置 must_change_password=true（TD4）"""
    admin_user = _require_admin(request)
    UserService = _get_user_service()

    new_password = _generate_random_password()
    try:
        UserService.set_password(username, new_password, must_change_password=True)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # 用户管理模块 批次2 补充加固（2026-07-02）：重置密码时一并清除账户锁定状态。
    # 背景：`/auth/change-password`（自助改密）早就有这个逻辑（旧密码校验通过后
    # 会调用 auth._reset_failures），但本接口（admin代为重置）此前完全没有处理
    # 账户锁定——如果该账户此前因连续输错密码触发了15分钟锁定（`_is_locked`
    # 独立于密码是否正确，检查的是失败计数+时间窗口），admin重置完密码后，
    # 用户拿着全新的正确密码登录仍会被 429 拦下，且锁定不会因为密码已被重置
    # 而提前解除，只能傻等剩余的锁定时间——admin已经通过管理页面验证过身份并
    # 主动重置，没有安全理由继续保留锁定状态，这里补上清除。
    auth = getattr(request.app.state, "auth", None)
    if auth is not None:
        auth._reset_failures(username)

    logger.info(f"[AUDIT] admin {admin_user['username']} 重置了 {username} 的密码（并清除账户锁定状态）")
    return {"username": username, "new_password": new_password, "must_change_password": True}


@router.delete("/admin/users/{username}")
async def delete_user(request: Request, username: str) -> Dict[str, str]:
    """软删除（enabled=0），不物理删除"""
    admin_user = _require_admin(request)
    UserService = _get_user_service()

    if username == admin_user["username"]:
        raise HTTPException(status_code=400, detail="不能禁用自己当前登录的账户")

    try:
        UserService.soft_delete(username, deleted_by=admin_user["username"])
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"message": f"账户 {username} 已禁用"}
