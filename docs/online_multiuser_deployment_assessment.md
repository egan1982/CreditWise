# DeepAnalyze 线上多用户部署评估报告

> 版本：v1.6  
> 日期：2025-03-10  
> 状态：超轻量方案已实施完成，CVM Docker 部署已上线  
> 更新记录：v1.2 → v1.3 新增实施进度跟踪章节，记录超轻量方案（feature/intranet-multiuser 分支）的完整实施结果

---

## 📋 目录

1. [执行摘要](#执行摘要)
2. [当前架构状态](#当前架构状态)
3. [核心不支持点](#核心不支持点)
4. [改造方案](#改造方案)
5. [部署架构对比](#部署架构对比)
6. [成本估算](#成本估算)
7. [实施路线图](#实施路线图)
8. [最小可行改造方案（内网 <5 人测试）](#最小可行改造方案内网-5-人测试)
9. [快速启动建议](#快速启动建议)
10. [审阅意见与改进方案（v1.2 新增）](#审阅意见与改进方案v12-新增)
11. [超轻量方案实施进度（v1.3 新增）](#超轻量方案实施进度v13-新增)
12. [账户有效期控制方案（v1.6 新增）](#账户有效期控制方案v16-新增)

---

## 执行摘要

本报告评估了 DeepAnalyze 项目从私有化部署向线上多用户部署演进的可行性。当前架构基于单用户、单机、本地存储设计，**不具备直接支持线上多用户部署的能力**，需要进行系统性改造。

### 关键结论

| 维度 | 评估结果 | 改造工作量 |
|------|----------|------------|
| 用户认证 | ❌ 缺失 | 1-2 周 |
| 数据隔离 | ⚠️ 弱（仅 session_id） | 1 周 |
| 数据库 | ⚠️ SQLite 单文件（<20 人可保留） | 视规模而定 |
| 文件存储 | ❌ 本地磁盘 | 3-5 天 |
| 会话管理 | ⚠️ API 层内存（SOP 已有持久化） | 1-2 天 |
| 代码执行隔离 | ❌ 无沙箱（v1.2 新增） | 1-2 周 |
| 水平扩展 | ❌ 不支持 | 1-2 周 |
| **总体评估** | **需全面改造** | **8-12 周** |

### 快速改造路径

| 场景 | 方案 | 工作量 | 适用性 |
|------|------|--------|--------|
| **内网测试（<5人）** | bcrypt 安全认证 + 配置文件 | 4-6 小时 | ⭐ 推荐 |
| 小团队（10-50人）| JWT + SSE认证 + 文件鉴权 | 2-2.5 周 | 可用 |
| 生产环境（50+人）| 完整改造方案（含沙箱隔离） | 8-12 周 | 必须 |

---

## 当前架构状态

### 技术栈概览

| 层级 | 技术选型 | 当前版本 |
|------|----------|----------|
| 前端 | Next.js + React | 14.2.16 |
| 后端 | FastAPI (Python) | 最新版 |
| 数据库 | SQLite | 3.x |
| 文件存储 | 本地文件系统 | - |
| 状态管理 | 内存字典 | - |
| 缓存 | 无 | - |

### 架构组件评估

| 维度 | 当前状态 | 支持线上部署？ | 说明 |
|------|----------|----------------|------|
| **用户认证** | ❌ 无认证系统 | ❌ 不支持 | 仅有 `session_id` 字符串参数，无用户身份验证 |
| **权限隔离** | ❌ 无隔离 | ❌ 不支持 | 用户 A 可通过猜测 session_id 访问用户 B 的数据 |
| **数据库** | SQLite 单文件 | ⚠️ 需改造 | 本地文件，多实例部署时数据不共享 |
| **文件存储** | 本地文件系统 | ❌ 不支持 | `workspace/{session_id}/` 目录，无法跨实例共享 |
| **会话管理** | ⚠️ 部分内存 | ⚠️ 需改造 | API 层 Storage 为内存字典；但 SOP 执行状态已有 PersistentExecutionStore 持久化 |
| **API 安全** | 无限流 | ❌ 不支持 | 无防刷、无请求频率限制 |
| **水平扩展** | 单机部署 | ❌ 不支持 | 状态内聚，无法水平扩展 |

### 现有 Session 机制分析

当前系统使用简单的字符串 session_id 进行会话标识：

```python
# API/utils.py
def get_session_workspace(session_id: str) -> str:
    """返回指定 session 的 workspace 路径"""
    if not session_id:
        session_id = "default"
    session_dir = os.path.join(WORKSPACE_BASE_DIR, session_id)
    os.makedirs(session_dir, exist_ok=True)
    return session_dir
```

**存在的问题：**
1. 无身份验证，任何人知道 session_id 即可访问
2. 无过期策略，session 永久有效
3. 无用户关联，无法追踪数据归属

---

## 核心不支持点

### 🔴 阻塞性问题（必须解决）

```
┌─────────────────────────────────────────────────────────────┐
│ 1. 无用户认证系统                                             │
│    └─> 无法区分用户身份，无法实现登录/注册/权限管理              │
│                                                             │
│ 2. 无权限隔离机制                                             │
│    └─> 用户 A 可通过猜测 session_id 访问用户 B 的数据           │
│                                                             │
│ 3. SQLite 本地数据库                                          │
│    └─> 多实例部署时数据不共享，无法水平扩展                     │
│                                                             │
│ 4. 本地文件存储                                               │
│    └─> 多实例部署时文件不共享，无法水平扩展                     │
│                                                             │
│ 5. 内存状态管理（部分已改善）                                │
│    └─> API 层 Storage 内存字典重启丢失；                       │
│        但 SOP 任务执行状态已有 PersistentExecutionStore         │
│        支持 pickle 文件 + SQLite 持久化                        │
└─────────────────────────────────────────────────────────────┘
```

### 🟡 重要问题（强烈建议解决）

| 问题 | 影响 | 优先级 |
|------|------|--------|
| API 无限流保护 | 容易被恶意调用耗尽资源 | P1 |
| 无审计日志 | 无法追踪用户操作 | P1 |
| 无数据加密 | 敏感数据明文存储 | P2 |
| 无备份机制 | 数据丢失风险 | P2 |

---

## 改造方案

### 阶段一：用户认证与授权（必须）

#### 1.1 用户系统数据库模型

```python
# llm_manager_integrated/models/auth_schemas.py

from datetime import datetime
from pydantic import BaseModel, EmailStr
from typing import Optional

class UserBase(BaseModel):
    """用户基础信息"""
    username: str
    email: EmailStr
    is_active: bool = True
    is_admin: bool = False

class UserCreate(UserBase):
    """用户创建请求"""
    password: str  # 明文，存储时哈希

class User(UserBase):
    """用户完整信息"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class UserSession(BaseModel):
    """用户会话，替代现有的简单 session_id"""
    id: str  # UUID
    user_id: int
    token: str  # JWT token
    created_at: datetime
    expires_at: datetime
    last_activity: datetime
    is_active: bool = True
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

class UserWorkspace(BaseModel):
    """用户工作区关联"""
    id: int
    user_id: int
    session_id: str
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
```

#### 1.2 数据库表定义

```python
# llm_manager_integrated/models/auth_models.py

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class UserModel(Base):
    """用户表"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    # 关系
    sessions = relationship("UserSessionModel", back_populates="user")
    workspaces = relationship("UserWorkspaceModel", back_populates="user")

class UserSessionModel(Base):
    """用户会话表"""
    __tablename__ = "user_sessions"
    
    id = Column(String(36), primary_key=True)  # UUID
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    last_activity = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    ip_address = Column(String(45))
    user_agent = Column(String(255))
    
    # 关系
    user = relationship("UserModel", back_populates="sessions")

class UserWorkspaceModel(Base):
    """用户工作区表"""
    __tablename__ = "user_workspaces"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(String(36), unique=True, index=True, nullable=False)
    name = Column(String(100), default="Default Workspace")
    description = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    # 关系
    user = relationship("UserModel", back_populates="workspaces")
```

#### 1.3 JWT 认证实现

```python
# API/auth.py

from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from llm_manager_integrated.models.auth_schemas import User

# 配置
SECRET_KEY = os.getenv("JWT_SECRET_KEY")  # 生产环境必须设置
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """哈希密码"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """创建 JWT token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """获取当前用户（依赖注入）"""
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # 从数据库获取用户
    user = await get_user_by_id(int(user_id))
    if user is None:
        raise credentials_exception
    
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """获取当前活跃用户"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
```

#### 1.4 认证 API 路由

```python
# API/auth_routes.py

from fastapi import APIRouter, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate):
    """用户注册"""
    # 检查用户名/邮箱是否已存在
    if await get_user_by_email(user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # 创建用户
    hashed_password = get_password_hash(user_data.password)
    user = await create_user(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password
    )
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        created_at=user.created_at
    )

@router.post("/login", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """用户登录"""
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_DAYS * 24 * 3600
    )

@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """用户登出（可选：将 token 加入黑名单）"""
    # 实现 token 失效逻辑
    return {"message": "Successfully logged out"}

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_active_user)):
    """获取当前用户信息"""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        is_admin=current_user.is_admin,
        created_at=current_user.created_at
    )
```

#### 1.5 权限验证装饰器

```python
# API/permissions.py

from functools import wraps
from fastapi import HTTPException, status

class PermissionRequired:
    """权限验证装饰器"""
    
    def __init__(self, require_admin: bool = False):
        self.require_admin = require_admin
    
    async def __call__(self, current_user: User = Depends(get_current_active_user)):
        if self.require_admin and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        return current_user

# 工作区所有权验证
async def verify_workspace_owner(
    session_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """验证用户是否拥有指定工作区"""
    workspace = await get_workspace_by_session(session_id)
    
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    if workspace.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this workspace"
        )
    
    return workspace
```

---

### 阶段二：数据库改造（必须）

> ⚠️ **v1.2 补充说明**：数据库改造的必要性取决于用户规模。现有代码已在 `task_manager/database.py` 中预留了通过环境变量切换数据库 URL 的扩展点，这是一个良好的设计。
>
> | 用户规模 | 是否需要 PostgreSQL | 理由 |
> |---------|---------------------|------|
> | <5 人内网 | ❌ SQLite 足够 | WAL 模式支持并发读，少量写入够用 |
> | 5-20 人 | ⚠️ 可选 | SQLite WAL + 合理的写入队列可承受 |
> | 20-50 人 | ✅ 建议 | 写入竞争明显增加 |
> | 50+ 人 | ✅ 必须 | 连接池、并发性能要求 |

#### 2.1 数据库迁移策略

**SQLite → PostgreSQL**

```python
# llm_manager_integrated/models/database.py

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 通过环境变量配置数据库
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./llm_manager.db"  # 默认开发环境
)

def get_engine():
    """根据 DATABASE_URL 创建引擎"""
    if DATABASE_URL.startswith("sqlite"):
        return create_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False}
        )
    else:
        # PostgreSQL/MySQL
        return create_engine(DATABASE_URL)

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 依赖注入
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

#### 2.2 环境配置

```bash
# .env 文件

# 开发环境
DATABASE_URL=sqlite:///./llm_manager.db

# 生产环境（PostgreSQL）
# DATABASE_URL=postgresql://user:password@localhost:5432/deepanalyze

# 生产环境（带连接池）
# DATABASE_URL=postgresql://user:password@localhost:5432/deepanalyze?pool_size=20&max_overflow=0
```

#### 2.3 Alembic 迁移工具

```bash
# 安装
pip install alembic

# 初始化
alembic init migrations

# 创建迁移脚本
alembic revision --autogenerate -m "add user authentication"

# 执行迁移
alembic upgrade head

# 回滚
alembic downgrade -1
```

---

### 阶段三：文件存储改造（必须）

#### 3.1 存储后端抽象

```python
# API/storage.py

from typing import Protocol, BinaryIO
from abc import ABC, abstractmethod

class StorageBackend(ABC):
    """存储后端抽象基类"""
    
    @abstractmethod
    async def upload(self, key: str, content: bytes) -> str:
        """上传文件，返回访问 URL"""
        pass
    
    @abstractmethod
    async def download(self, key: str) -> bytes:
        """下载文件内容"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """删除文件"""
        pass
    
    @abstractmethod
    async def get_url(self, key: str, expires: int = 3600) -> str:
        """获取文件访问 URL（支持预签名）"""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """检查文件是否存在"""
        pass
```

#### 3.2 S3/OSS 实现

```python
# API/storage_s3.py

import boto3
from botocore.exceptions import ClientError
from .storage import StorageBackend

class S3Storage(StorageBackend):
    """AWS S3 / 阿里云 OSS / 腾讯云 COS 实现"""
    
    def __init__(self):
        self.client = boto3.client(
            's3',
            aws_access_key_id=os.getenv("S3_ACCESS_KEY"),
            aws_secret_access_key=os.getenv("S3_SECRET_KEY"),
            region_name=os.getenv("S3_REGION", "us-east-1"),
            endpoint_url=os.getenv("S3_ENDPOINT")  # 用于兼容 OSS/COS
        )
        self.bucket = os.getenv("S3_BUCKET")
        self.public_url = os.getenv("S3_PUBLIC_URL", "")
    
    def _get_key(self, user_id: int, session_id: str, filename: str) -> str:
        """生成对象存储 key"""
        return f"users/{user_id}/workspaces/{session_id}/{filename}"
    
    async def upload(self, key: str, content: bytes) -> str:
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=content
        )
        return await self.get_url(key)
    
    async def download(self, key: str) -> bytes:
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        return response['Body'].read()
    
    async def delete(self, key: str) -> bool:
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError:
            return False
    
    async def get_url(self, key: str, expires: int = 3600) -> str:
        """生成预签名 URL"""
        if self.public_url:
            return f"{self.public_url}/{key}"
        
        url = self.client.generate_presigned_url(
            'get_object',
            Params={'Bucket': self.bucket, 'Key': key},
            ExpiresIn=expires
        )
        return url
    
    async def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError:
            return False
```

#### 3.3 本地存储实现（开发环境）

```python
# API/storage_local.py

import os
import shutil
from pathlib import Path
from .storage import StorageBackend

class LocalStorage(StorageBackend):
    """本地文件系统实现（开发环境使用）"""
    
    def __init__(self, base_path: str = "./workspace"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def _get_full_path(self, key: str) -> Path:
        """获取完整路径"""
        full_path = self.base_path / key
        # 安全检查：确保路径在 base_path 内
        full_path.resolve().relative_to(self.base_path.resolve())
        return full_path
    
    async def upload(self, key: str, content: bytes) -> str:
        full_path = self._get_full_path(key)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(content)
        return f"/download/{key}"  # 本地 URL
    
    async def download(self, key: str) -> bytes:
        full_path = self._get_full_path(key)
        return full_path.read_bytes()
    
    async def delete(self, key: str) -> bool:
        full_path = self._get_full_path(key)
        if full_path.exists():
            if full_path.is_dir():
                shutil.rmtree(full_path)
            else:
                full_path.unlink()
            return True
        return False
    
    async def get_url(self, key: str, expires: int = 3600) -> str:
        return f"/download/{key}"
    
    async def exists(self, key: str) -> bool:
        return self._get_full_path(key).exists()
```

#### 3.4 存储工厂

```python
# API/storage_factory.py

import os
from .storage import StorageBackend
from .storage_s3 import S3Storage
from .storage_local import LocalStorage

def get_storage() -> StorageBackend:
    """根据环境变量返回存储后端"""
    storage_type = os.getenv("STORAGE_TYPE", "local").lower()
    
    if storage_type == "s3":
        return S3Storage()
    elif storage_type == "local":
        return LocalStorage()
    else:
        raise ValueError(f"Unknown storage type: {storage_type}")

# 全局实例
storage = get_storage()
```

---

### 阶段四：会话状态外置（必须）

> ⚠️ **v1.2 修正说明**：
> 
> 项目已有 `PersistentExecutionStore`（`deepanalyze/core/task_manager/persistent_store.py`），
> 支持通过 `execution_states/` 目录下的 `.pkl` 文件 + SQLite `execution_states` 表进行任务暂停/恢复/重启恢复。
> 
> **因此，"会话状态外置"的实际工作量被原始评估高估。** 真正需要外置的是：
> 1. `API/storage.py` 中的内存字典（`threads`/`messages`/`files`）
> 2. `execution_states/` 目录在多实例场景下的共享问题
> 
> **Redis 的正确定位**：缓存当前活跃执行的热状态；历史记录仍应通过数据库查询。

#### 4.1 状态管理器

```python
# API/state_manager.py

import json
import redis
from typing import Optional, Dict, Any
from datetime import timedelta

class StateManager:
    """
    状态管理器
    
    支持两种模式：
    - Redis 模式：生产环境，支持多实例共享
    - 内存模式：开发环境，单实例使用
    
    v1.2 改进：
    - Redis 仅缓存活跃执行的热状态，历史记录通过数据库查询
    - 使用 user:{user_id}:executions 索引集合，避免全量 SCAN
    """
    
    def __init__(self):
        redis_url = os.getenv("REDIS_URL")
        
        if redis_url:
            self.client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                health_check_interval=30
            )
            self.mode = "redis"
        else:
            self._local_cache: Dict[str, Any] = {}
            self._user_index: Dict[int, set] = {}  # user_id -> {execution_id, ...}
            self.mode = "memory"
    
    def _get_key(self, execution_id: str) -> str:
        """生成 Redis key"""
        return f"deepanalyze:execution:{execution_id}"
    
    def _get_user_index_key(self, user_id: int) -> str:
        """生成用户执行索引的 Redis key"""
        return f"deepanalyze:user:{user_id}:executions"
    
    def get_execution_status(self, execution_id: str) -> Optional[Dict]:
        """获取执行状态"""
        if self.mode == "redis":
            data = self.client.get(self._get_key(execution_id))
            return json.loads(data) if data else None
        else:
            return self._local_cache.get(execution_id)
    
    def set_execution_status(
        self, 
        execution_id: str, 
        status: Dict,
        expire_hours: int = 24
    ):
        """设置执行状态，同时维护用户索引"""
        user_id = status.get("user_id")
        
        if self.mode == "redis":
            pipe = self.client.pipeline()
            pipe.setex(
                self._get_key(execution_id),
                timedelta(hours=expire_hours),
                json.dumps(status, default=str)
            )
            # 维护用户 -> 执行ID 的索引集合
            if user_id is not None:
                index_key = self._get_user_index_key(user_id)
                pipe.sadd(index_key, execution_id)
                pipe.expire(index_key, timedelta(hours=expire_hours))
            pipe.execute()
        else:
            self._local_cache[execution_id] = status
            if user_id is not None:
                if user_id not in self._user_index:
                    self._user_index[user_id] = set()
                self._user_index[user_id].add(execution_id)
    
    def update_execution_status(self, execution_id: str, updates: Dict):
        """部分更新执行状态"""
        current = self.get_execution_status(execution_id) or {}
        current.update(updates)
        self.set_execution_status(execution_id, current)
    
    def delete_execution_status(self, execution_id: str):
        """删除执行状态"""
        if self.mode == "redis":
            # 先获取 user_id 以清理索引
            data = self.client.get(self._get_key(execution_id))
            if data:
                status = json.loads(data)
                user_id = status.get("user_id")
                pipe = self.client.pipeline()
                pipe.delete(self._get_key(execution_id))
                if user_id is not None:
                    pipe.srem(self._get_user_index_key(user_id), execution_id)
                pipe.execute()
            else:
                self.client.delete(self._get_key(execution_id))
        else:
            status = self._local_cache.pop(execution_id, None)
            if status:
                user_id = status.get("user_id")
                if user_id and user_id in self._user_index:
                    self._user_index[user_id].discard(execution_id)
    
    def get_user_executions(self, user_id: int) -> list:
        """
        获取用户的活跃执行记录
        
        v1.2 改进：通过索引集合精确查询，而非全量 SCAN + 过滤
        注意：历史记录应通过数据库查询，此处仅返回 Redis 中的活跃状态
        """
        if self.mode == "redis":
            # 通过索引集合获取用户的执行ID列表
            index_key = self._get_user_index_key(user_id)
            execution_ids = self.client.smembers(index_key)
            
            if not execution_ids:
                return []
            
            # 批量获取所有执行状态（MGET 比逐条 GET 高效）
            keys = [self._get_key(eid) for eid in execution_ids]
            results = self.client.mget(keys)
            
            executions = []
            expired_ids = []
            for eid, data in zip(execution_ids, results):
                if data:
                    executions.append(json.loads(data))
                else:
                    # 数据已过期但索引未清理
                    expired_ids.append(eid)
            
            # 清理过期的索引条目
            if expired_ids:
                self.client.srem(index_key, *expired_ids)
            
            return executions
        else:
            # 内存模式：通过索引查找
            execution_ids = self._user_index.get(user_id, set())
            return [
                self._local_cache[eid]
                for eid in execution_ids
                if eid in self._local_cache
            ]

# 全局实例
state_manager = StateManager()
```

#### 4.2 集成到 SOP 执行器

```python
# deepanalyze/analysis/task_SOP/executor.py

class ExecutionStore:
    """执行存储，使用外部状态管理器"""
    
    def __init__(self):
        from API.state_manager import state_manager
        self.state = state_manager
    
    def create(self, execution_id: str, user_id: int, task_type: str, params: dict):
        """创建执行记录"""
        self.state.set_execution_status(execution_id, {
            "execution_id": execution_id,
            "user_id": user_id,
            "task_type": task_type,
            "params": params,
            "status": "pending",
            "progress": 0,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "stages": []
        })
    
    def update_progress(self, execution_id: str, progress: float, stage: str = None):
        """更新进度"""
        updates = {
            "progress": progress,
            "updated_at": datetime.utcnow().isoformat()
        }
        if stage:
            updates["current_stage"] = stage
        self.state.update_execution_status(execution_id, updates)
```

---

### 阶段五：API 安全加固（推荐）

#### 5.1 限流器

```python
# API/rate_limiter.py

import time
from fastapi import Request, HTTPException
import redis

class RateLimiter:
    """基于 Redis 的分布式限流器"""
    
    def __init__(self):
        redis_url = os.getenv("REDIS_URL")
        self.redis = redis.from_url(redis_url) if redis_url else None
        
        # 限流配置：每分钟请求数
        self.limits = {
            "default": 100,
            "chat": 60,
            "sop_execute": 10,
            "file_upload": 30,
        }
    
    async def check_rate_limit(self, user_id: str, endpoint: str):
        """检查是否超过限流阈值"""
        if not self.redis:
            return  # 无 Redis 时不限流
        
        # 确定限流阈值
        limit = self.limits.get(endpoint, self.limits["default"])
        
        # Redis key
        key = f"ratelimit:{user_id}:{endpoint}:{int(time.time()) // 60}"
        
        # 增加计数
        pipe = self.redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, 60)
        results = pipe.execute()
        
        current = results[0]
        
        if current > limit:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit exceeded",
                    "limit": limit,
                    "retry_after": 60 - int(time.time()) % 60
                }
            )

# 全局实例
rate_limiter = RateLimiter()
```

#### 5.2 限流中间件

```python
# API/middleware.py

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class RateLimitMiddleware(BaseHTTPMiddleware):
    """限流中间件"""
    
    async def dispatch(self, request: Request, call_next):
        # 跳过健康检查端点
        if request.url.path in ["/", "/health", "/docs", "/openapi.json"]:
            return await call_next(request)
        
        # 获取用户 ID
        user_id = request.state.user_id if hasattr(request.state, "user_id") else "anonymous"
        
        # 确定端点类型
        endpoint = "default"
        if "/chat" in request.url.path:
            endpoint = "chat"
        elif "/sop/execute" in request.url.path:
            endpoint = "sop_execute"
        elif "/upload" in request.url.path:
            endpoint = "file_upload"
        
        # 检查限流
        await rate_limiter.check_rate_limit(user_id, endpoint)
        
        return await call_next(request)
```

---

### 阶段六：前端改造（必须）

#### 6.1 登录页面

```tsx
// demo/chat/app/login/page.tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const router = useRouter();
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [username, setUsername] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const endpoint = isLogin ? "/auth/login" : "/auth/register";
      const body = isLogin
        ? { username: email, password }
        : { username, email, password };

      const response = await fetch(`http://localhost:8200${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Authentication failed");
      }

      // 保存 token
      localStorage.setItem("token", data.access_token);
      
      // 跳转到主页面
      router.push("/");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8 p-8 bg-white rounded-lg shadow">
        <div>
          <h2 className="text-3xl font-bold text-center">
            {isLogin ? "登录" : "注册"}
          </h2>
          <p className="mt-2 text-center text-gray-600">
            DeepAnalyze 数据分析平台
          </p>
        </div>

        {error && (
          <div className="bg-red-50 text-red-600 p-3 rounded">
            {error}
          </div>
        )}

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {!isLogin && (
            <div>
              <label className="block text-sm font-medium text-gray-700">
                用户名
              </label>
              <input
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
              />
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700">
              邮箱
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">
              密码
            </label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? "处理中..." : isLogin ? "登录" : "注册"}
          </button>
        </form>

        <div className="text-center">
          <button
            onClick={() => setIsLogin(!isLogin)}
            className="text-blue-600 hover:text-blue-500"
          >
            {isLogin ? "没有账号？立即注册" : "已有账号？立即登录"}
          </button>
        </div>
      </div>
    </div>
  );
}
```

#### 6.2 API 客户端

```typescript
// demo/chat/lib/api.ts

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8200";

class ApiClient {
  private getToken(): string | null {
    if (typeof window !== "undefined") {
      return localStorage.getItem("token");
    }
    return null;
  }

  async fetch(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<Response> {
    const token = this.getToken();
    
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...((options.headers as Record<string, string>) || {}),
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });

    // 处理 401 未授权
    if (response.status === 401) {
      localStorage.removeItem("token");
      window.location.href = "/login";
      throw new Error("Session expired");
    }

    return response;
  }

  // 便捷方法
  async get(endpoint: string) {
    return this.fetch(endpoint, { method: "GET" });
  }

  async post(endpoint: string, data: any) {
    return this.fetch(endpoint, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async delete(endpoint: string) {
    return this.fetch(endpoint, { method: "DELETE" });
  }
}

export const apiClient = new ApiClient();
```

#### 6.3 认证守卫组件

```tsx
// demo/chat/components/AuthGuard.tsx

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("token");
    
    if (!token) {
      router.push("/login");
      return;
    }

    // 可选：验证 token 有效性
    fetch("http://localhost:8200/auth/me", {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => {
        if (res.ok) {
          setIsAuthenticated(true);
        } else {
          localStorage.removeItem("token");
          router.push("/login");
        }
      })
      .catch(() => {
        router.push("/login");
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [router]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return isAuthenticated ? <>{children}</> : null;
}
```

---

## 部署架构对比

### 当前私有化部署架构

```
┌─────────────────────────────────────────────────────────────┐
│                      单机部署架构                            │
│                                                             │
│   ┌───────────────┐         ┌───────────────┐              │
│   │   Next.js     │◄───────►│   FastAPI     │              │
│   │  Port: 3000   │         │  Port: 8200   │              │
│   └───────────────┘         └───────┬───────┘              │
│                                     │                       │
│                           ┌─────────┴─────────┐             │
│                           │                   │             │
│                     ┌─────┴─────┐      ┌──────┴──────┐      │
│                     │  SQLite   │      │  本地文件   │      │
│                     │  单文件   │      │  系统       │      │
│                     └───────────┘      └─────────────┘      │
│                                                             │
│   特点：                                                     │
│   • 单用户/单实例                                            │
│   • 状态内聚在内存                                           │
│   • 无法水平扩展                                             │
│   • 服务重启数据丢失                                         │
└─────────────────────────────────────────────────────────────┘
```

### 线上多用户部署架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          生产环境架构                                    │
│                                                                         │
│    ┌──────────────────────────────────────────────────────────┐        │
│    │                  负载均衡器 (ALB/CLB)                     │        │
│    │              SSL 终止 / DDoS 防护 / WAF                  │        │
│    └────────────────────────┬─────────────────────────────────┘        │
│                             │                                           │
│            ┌────────────────┼────────────────┐                         │
│            │                │                │                         │
│            ▼                ▼                ▼                         │
│      ┌──────────┐     ┌──────────┐     ┌──────────┐                   │
│      │ 实例 1   │     │ 实例 2   │     │ 实例 3   │  ◄── 自动扩缩容   │
│      │FastAPI   │     │FastAPI   │     │FastAPI   │                   │
│      │+ Next.js │     │+ Next.js │     │+ Next.js │                   │
│      └────┬─────┘     └────┬─────┘     └────┬─────┘                   │
│           │                │                │                          │
│           └────────────────┼────────────────┘                          │
│                            │                                            │
│    ┌───────────────────────┼───────────────────────┐                   │
│    │                       │                       │                   │
│    ▼                       ▼                       ▼                   │
│ ┌──────────┐          ┌──────────┐          ┌──────────┐              │
│ │PostgreSQL│          │  Redis   │          │  S3/OSS  │              │
│ │ 主从集群  │          │  集群    │          │ 对象存储 │              │
│ │          │          │          │          │          │              │
│ │ 用户数据 │          │会话状态  │          │ 文件数据 │              │
│ │ 任务记录 │          │  缓存    │          │          │              │
│ │ API日志  │          │ 限流计数 │          │          │              │
│ └──────────┘          └──────────┘          └──────────┘              │
│                                                                         │
│   特点：                                                                 │
│   • 多实例水平扩展                                                       │
│   • 共享状态（Redis）                                                    │
│   • 共享存储（S3/OSS）                                                   │
│   • 高可用数据库（PostgreSQL 主从）                                       │
│   • 自动故障转移                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 成本估算

### 云资源成本（月度）

| 组件 | 配置 | 阿里云估算 | AWS 估算 |
|------|------|------------|----------|
| **ECS/EC2** | 2核4GB × 2实例 | ¥300-500 | $50-80 |
| **RDS** | PostgreSQL 基础版 | ¥200-400 | $30-60 |
| **Redis** | 4GB 主从版 | ¥150-300 | $25-50 |
| **OSS/S3** | 100GB 存储 + 流量 | ¥50-150 | $10-30 |
| **SLB/ALB** | 负载均衡 | ¥50-100 | $20-40 |
| **网络** | 公网带宽 10Mbps | ¥100-200 | - |
| **总计** | | **¥850-1650** | **$135-260** |

### 开源替代方案（降低成本）

| 组件 | 开源方案 | 成本节省 |
|------|----------|----------|
| 数据库 | 自建 PostgreSQL | ¥200-400/月 |
| 缓存 | 自建 Redis | ¥150-300/月 |
| 存储 | MinIO（S3兼容）| ¥50-100/月 |
| **总计节省** | | **¥400-800/月** |

### 维护成本

| 项目 | 月度投入 |
|------|----------|
| 服务器运维 | 10-20 小时 |
| 数据库备份 | 5 小时 |
| 监控告警 | 5 小时 |
| 安全更新 | 5 小时 |
| **总计** | **25-35 小时** |

---

## 实施路线图

### 总体时间规划

```
月份:    M1                              M2                              M3
周:      W1    W2    W3    W4    W5    W6    W7    W8    W9    W10   W11   W12
         ├─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┤
         │  Phase 1-4: 核心改造（6周）                    │
         └───────────────────────────────────────────────┘
                              ├─────┴─────┴─────┤
                              │  Phase 5-6: 优化  │
                              └─────────────────┘
                                                    ├─────┴─────┤
                                                    │  Phase 7-8│
                                                    └───────────┘
```

### 详细实施计划

| 阶段 | 任务 | 工期 | 负责人 | 产出物 |
|------|------|------|--------|--------|
| **Phase 1** | 用户认证系统 | 1周 | 后端 | JWT 认证、登录/注册 API |
| **Phase 2** | 数据库迁移 | 1周 | 后端 | PostgreSQL 支持、Alembic |
| **Phase 3** | 文件存储改造 | 3天 | 后端 | S3 存储后端 |
| **Phase 4** | 会话状态外置 | 3天 | 后端 | Redis 状态管理 |
| **Phase 5** | 前端登录集成 | 1周 | 前端 | 登录页面、API 客户端 |
| **Phase 6** | API 安全加固 | 3天 | 后端 | 限流、审计日志 |
| **Phase 7** | 容器化部署 | 1周 | 运维 | Docker、K8s 配置 |
| **Phase 8** | 监控与日志 | 1周 | 运维 | Prometheus、Grafana |

### 里程碑

| 里程碑 | 时间 | 交付标准 |
|--------|------|----------|
| M1 | Week 2 | 用户认证系统完成，可注册/登录 |
| M2 | Week 4 | 数据库迁移完成，数据持久化 |
| M3 | Week 6 | 文件存储改造完成，多实例共享 |
| M4 | Week 8 | 前端集成完成，完整用户流程 |
| M5 | Week 10 | 安全加固完成，通过渗透测试 |
| M6 | Week 12 | 生产环境就绪，正式上线 |

---

## 最小可行改造方案（内网 <5 人测试）

针对公司内网、少量用户（<5人）测试场景，提供**超轻量改造方案（MVP）**，在保持现有架构基本不变的前提下，实现安全的用户隔离。

### 方案对比

| 方案 | 认证方式 | 数据库 | 工作量 | 适用性 |
|------|----------|--------|--------|--------|
| **超轻量** | HTTP Basic Auth + 配置文件 | SQLite | 2-4 小时 | 推荐 |
| **轻量** | JWT + SQLite 用户表 | SQLite | 1-2 天 | 备用 |
| **标准** | JWT + PostgreSQL | PostgreSQL | 1-2 周 | 不推荐 |

**推荐：超轻量方案**（2-4 小时完成）

### 核心思路

```
┌─────────────────────────────────────────────────────────────┐
│                    超轻量改造策略                            │
│                                                             │
│   保留 SQLite（无需安装新数据库）                              │
│   保留本地文件存储（内网共享目录）                              │
│   简单 HTTP Basic Auth（浏览器原生支持）                       │
│   配置文件管理用户（无需注册页面）                              │
│   无会话状态外置（单实例足够）                                  │
│                                                             │
│   用户管理：                                                  │
│   • 通过配置文件添加用户（admin 手动维护）                      │
│   • 浏览器自动记住密码                                         │
│   • 无需注册/找回密码功能                                      │
└─────────────────────────────────────────────────────────────┘
```

### 改造清单（2-4 小时）

| 序号 | 任务 | 文件 | 工作量 |
|------|------|------|--------|
| 1 | 添加 Basic Auth 中间件 | API/auth_simple.py | 30 min |
| 2 | 用户配置文件 | config/users.yaml | 15 min |
| 3 | 工作区隔离改造 | API/utils.py | 30 min |
| 4 | 前端适配 | demo/chat/lib/api.ts | 30 min |
| 5 | 部署脚本 | start_production.ps1 | 30 min |
| 6 | 测试验证 | - | 30-60 min |

### 详细实施步骤

#### Step 1: 创建用户配置文件

> ⚠️ **v1.2 安全改进**：密码使用 bcrypt 哈希存储，而非明文。管理员通过附带的工具脚本生成哈希值。

```yaml
# config/users.yaml
# 内网测试用户配置（管理员手动维护）
# ⚠️ 密码字段为 bcrypt 哈希值，使用 scripts/hash_password.py 生成

users:
  - username: user1
    password_hash: "$2b$12$LJ3m4ys2Kq..."  # 使用 scripts/hash_password.py 生成
    role: user
    description: "测试用户1"
    
  - username: user2
    password_hash: "$2b$12$Xk9p7Rt1Wn..."
    role: user
    description: "测试用户2"
    
  - username: admin
    password_hash: "$2b$12$Qw8e3Zx5Gy..."
    role: admin
    description: "管理员"

# 安全配置
settings:
  session_timeout_hours: 24
  max_login_failures: 5          # 连续失败次数限制
  lockout_duration_minutes: 15   # 锁定时间（分钟）
```

**密码哈希生成工具**（`scripts/hash_password.py`）：

```python
#!/usr/bin/env python3
"""生成 bcrypt 密码哈希值，用于 config/users.yaml"""
import bcrypt
import sys

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

if __name__ == "__main__":
    if len(sys.argv) > 1:
        pwd = sys.argv[1]
    else:
        import getpass
        pwd = getpass.getpass("请输入密码: ")
    
    hashed = hash_password(pwd)
    print(f"密码哈希值: {hashed}")
    print("请将此值复制到 config/users.yaml 的 password_hash 字段")
```

#### Step 2: Basic Auth 中间件（安全增强版）

> ⚠️ **v1.2 安全改进**：
> - 使用 `bcrypt` 验证密码哈希（而非明文比较）
> - 使用 `hmac.compare_digest` 防止时序攻击
> - 添加登录失败计数和账户锁定机制
> - 添加登录审计日志

创建 `API/auth_simple.py`：

```python
import os
import yaml
import base64
import hmac
import bcrypt
import time
import logging
from collections import defaultdict
from fastapi import Request, HTTPException, status

logger = logging.getLogger(__name__)

def load_users():
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "users.yaml")
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config

CONFIG = load_users()
USERS = {u['username']: u for u in CONFIG['users']}
SETTINGS = CONFIG.get('settings', {})

class SimpleAuth:
    def __init__(self):
        self.users = USERS
        self.max_failures = SETTINGS.get('max_login_failures', 5)
        self.lockout_duration = SETTINGS.get('lockout_duration_minutes', 15) * 60  # 转为秒
        # 登录失败追踪: {username: {"count": int, "last_failure": float}}
        self._failure_tracker: dict = defaultdict(lambda: {"count": 0, "last_failure": 0.0})
    
    def _is_locked(self, username: str) -> bool:
        """检查账户是否被锁定"""
        tracker = self._failure_tracker.get(username)
        if not tracker:
            return False
        if tracker["count"] >= self.max_failures:
            elapsed = time.time() - tracker["last_failure"]
            if elapsed < self.lockout_duration:
                return True
            # 锁定时间已过，重置计数
            self._failure_tracker[username] = {"count": 0, "last_failure": 0.0}
        return False
    
    def _record_failure(self, username: str):
        """记录登录失败"""
        self._failure_tracker[username]["count"] += 1
        self._failure_tracker[username]["last_failure"] = time.time()
    
    def _reset_failures(self, username: str):
        """登录成功后重置失败计数"""
        self._failure_tracker[username] = {"count": 0, "last_failure": 0.0}
    
    def verify_credentials(self, username: str, password: str) -> bool:
        """使用 bcrypt 验证密码，防止时序攻击"""
        user = self.users.get(username)
        if not user:
            # 即使用户不存在也执行一次哈希操作，防止时序泄露用户名是否存在
            bcrypt.hashpw(b"dummy_password", bcrypt.gensalt())
            return False
        
        stored_hash = user.get('password_hash', '').encode('utf-8')
        password_bytes = password.encode('utf-8')
        
        try:
            return bcrypt.checkpw(password_bytes, stored_hash)
        except Exception:
            return False
    
    def get_current_user(self, request: Request) -> dict:
        auth_header = request.headers.get("Authorization", "")
        
        if not auth_header.startswith("Basic "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authorization header",
                headers={"WWW-Authenticate": "Basic"},
            )
        
        try:
            encoded = auth_header.split(" ")[1]
            decoded = base64.b64decode(encoded).decode("utf-8")
            username, password = decoded.split(":", 1)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header",
                headers={"WWW-Authenticate": "Basic"},
            )
        
        # 检查账户是否被锁定
        if self._is_locked(username):
            logger.warning(f"Account locked: {username} (from {request.client.host})")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Account locked due to too many failed attempts. "
                       f"Try again in {self.lockout_duration // 60} minutes.",
            )
        
        if not self.verify_credentials(username, password):
            self._record_failure(username)
            logger.warning(f"Login failed: {username} (from {request.client.host})")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Basic"},
            )
        
        self._reset_failures(username)
        logger.info(f"Login success: {username} (from {request.client.host})")
        return self.users[username]

simple_auth = SimpleAuth()

async def get_current_user(request: Request) -> dict:
    return simple_auth.get_current_user(request)
```

#### Step 3: 工作区隔离改造

在 `API/utils.py` 中新增：

```python
def get_user_workspace(user_id: str, session_id: str = None) -> str:
    """
    获取用户隔离的工作区路径
    路径结构: WORKSPACE_BASE_DIR/{username}/{session_id}/
    """
    base_dir = os.getenv("WORKSPACE_BASE_DIR", "./workspace")
    user_dir = os.path.join(base_dir, user_id)
    
    if not session_id:
        session_id = "default"
    
    workspace_dir = os.path.join(user_dir, session_id)
    os.makedirs(workspace_dir, exist_ok=True)
    
    return workspace_dir
```

#### Step 4: 修改 API 路由增加认证

在 `API/main.py` 中修改路由：

```python
from fastapi import Depends
from auth_simple import get_current_user

@app.get("/workspace/files")
async def get_workspace_files_endpoint(
    current_user: dict = Depends(get_current_user),
    session_id: str = "default"
):
    """获取工作区文件列表（增加用户隔离）"""
    from utils import get_user_workspace
    
    workspace_dir = get_user_workspace(current_user['username'], session_id)
    # ... 其余逻辑保持不变
```

#### Step 5: 前端适配

创建 `demo/chat/lib/api.ts`：

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8200";

class ApiClient {
  private credentials: string | null = null;

  constructor() {
    if (typeof window !== "undefined") {
      this.credentials = localStorage.getItem("basic_auth");
    }
  }

  setCredentials(username: string, password: string) {
    this.credentials = btoa(`${username}:${password}`);
    localStorage.setItem("basic_auth", this.credentials);
  }

  async fetch(endpoint: string, options: RequestInit = {}): Promise<Response> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };

    if (this.credentials) {
      headers["Authorization"] = `Basic ${this.credentials}`;
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });

    if (response.status === 401) {
      this.clearCredentials();
      window.location.href = "/login";
      throw new Error("Unauthorized");
    }

    return response;
  }
}

export const apiClient = new ApiClient();
```

#### Step 6: 生产启动脚本

创建 `start_intranet_test.ps1`：

```powershell
param(
    [int]$Port = 8200,
    [string]$HostAddr = "0.0.0.0",
    [string]$WorkspaceDir = "D:\DeepAnalyzeData\workspace"
)

Write-Host "DeepAnalyze 内网测试环境" -ForegroundColor Cyan

$env:API_PORT = $Port
$env:API_HOST = $HostAddr
$env:WORKSPACE_BASE_DIR = $WorkspaceDir
$env:ENVIRONMENT = "intranet_test"

if (!(Test-Path $WorkspaceDir)) {
    New-Item -ItemType Directory -Path $WorkspaceDir -Force | Out-Null
}

Write-Host "访问地址:"
Write-Host "  本机: http://localhost:$Port"
Write-Host "  内网: http://<服务器IP>:$Port"

& python API/main.py
```

### 文件结构

```
DeepAnalyze/
├── API/
│   ├── auth_simple.py      # 新增：Basic Auth（bcrypt 安全增强版）
│   ├── main.py             # 修改：增加认证依赖
│   └── utils.py            # 修改：用户隔离工作区
├── config/
│   └── users.yaml          # 新增：用户配置（bcrypt 哈希密码）
├── scripts/
│   └── hash_password.py    # 新增：密码哈希生成工具
├── demo/chat/
│   ├── app/login/page.tsx  # 新增：登录页面
│   └── lib/api.ts          # 修改：API 客户端
└── start_intranet_test.ps1 # 新增：启动脚本
```

### 安全建议（内网环境）

| 项目 | 建议 | 优先级 |
|------|------|--------|
| 密码存储 | bcrypt 哈希，禁止明文存储 | P0 |
| 防火墙 | 限制只有特定 IP 可访问 | P0 |
| 登录保护 | 连续失败 5 次锁定 15 分钟 | P0 |
| 密码策略 | 首次登录强制修改密码 | P1 |
| 定期更换 | 每月更换一次测试密码 | P2 |
| 访问日志 | 记录用户操作日志 | P2 |
| 数据备份 | 定期备份 workspace 目录 | P1 |

### 快速启动检查清单

- [ ] 复制 config/users.yaml.example 到 config/users.yaml 并配置用户
- [ ] 修改 API/main.py 导入 auth_simple 并增加路由保护
- [ ] 修改 API/utils.py 增加 get_user_workspace 函数
- [ ] 创建前端登录页面 demo/chat/app/login/page.tsx
- [ ] 修改 demo/chat/lib/api.ts 支持 Basic Auth
- [ ] 运行 .\start_intranet_test.ps1
- [ ] 在浏览器访问 http://<服务器IP>:8200
- [ ] 使用配置的账号密码登录

### 扩展路径

当测试规模扩大时，可逐步升级：

| 阶段 | 用户数 | 升级内容 |
|------|--------|----------|
| 当前 | < 5 | 超轻量方案（Basic Auth + SQLite） |
| Phase 2 | 5-20 | JWT + 密码加密 + 用户管理页面 |
| Phase 3 | 20-50 | PostgreSQL + Redis + 水平扩展 |
| Phase 4 | 50+ | 完整生产方案 |

---

## 快速启动建议

### 方案 A：伪多用户（折中方案）

如果希望快速上线且用户量较小（< 50 人），可采用折中方案：

```
┌─────────────────────────────────────────────────────────────┐
│                    伪多用户架构                              │
│                                                             │
│   改造范围：                                                  │
│   ✅ JWT 认证（Token 自包含用户信息）                          │
│   ✅ session_id 格式改为 user_id:{uuid}                      │
│   ❌ 保留 SQLite（不改造数据库）                              │
│   ❌ 保留本地存储（不改造文件系统）                            │
│   ❌ 单实例部署                                               │
│                                                             │
│   限制：                                                     │
│   • 无法水平扩展                                             │
│   • 服务重启后需重新登录                                      │
│   • 单机性能瓶颈                                             │
│   • 无高可用保障                                             │
│                                                             │
│   适用场景：                                                  │
│   • 小团队内部使用                                           │
│   • 临时演示环境                                             │
│   • 预算有限，快速验证                                        │
│                                                             │
│   工期：1-2 周                                               │
└─────────────────────────────────────────────────────────────┘
```

**改造清单（伪多用户）：**

| 任务 | 工作量 | 说明 |
|------|--------|------|
| JWT 认证 | 2 天 | Token 包含 user_id，无数据库 |
| 前端登录 | 2 天 | 登录页面 + Token 存储 |
| 权限校验 | 1 天 | API 层校验 session 归属 |
| 部署脚本 | 1 天 | Docker 单机部署 |
| **总计** | **6 天** | |

### 方案 B：生产就绪（推荐）

按照完整改造方案实施，支持真正的多用户、高并发、高可用。

### 方案选择建议

| 场景 | 推荐方案 | 理由 |
|------|----------|------|
| 内部试用（< 10 人）| 方案 A | 快速上线，成本最低 |
| 小团队（10-50 人）| 方案 A → 方案 B | 先验证，后扩展 |
| 企业级（> 50 人）| 方案 B | 必须完整改造 |
| 对外 SaaS | 方案 B | 安全合规要求 |

---

## 审阅意见与改进方案（v1.2 新增）

> 本章节基于对项目实际代码（`API/`、`deepanalyze/`、`demo/chat/`）的审阅，指出原始方案中的安全缺陷、架构遗漏，并给出具体改进实现。
> 
> 已在文档正文中**就地修复**的问题（标记为 ✅ 已修复）不再重复给出完整代码，仅说明修改要点。

### 一、方案合理性总评

#### 超轻量方案（2-4 小时，<5 人内网）

| 项目 | 评分 | 说明 |
|------|------|------|
| 工作量估算 | ⭐⭐⭐⭐ | 合理偏乐观，含测试实际需 4-6 小时 |
| 安全性 | ⭐⭐⭐⭐ | **v1.2 已修复**：bcrypt 哈希 + 登录失败锁定 |
| 可扩展性 | ⭐⭐⭐ | 后续升级路径清晰 |
| 实用性 | ⭐⭐⭐⭐ | 内网测试场景够用 |

#### 方案 A — 伪多用户（1-2 周，JWT + SQLite）

| 项目 | 评分 | 说明 |
|------|------|------|
| 工作量估算 | ⭐⭐⭐ | 6 天偏乐观，JWT 认证 + 前端登录 + 权限校验 + 测试，实际需 8-10 天 |
| 架构合理性 | ⭐⭐⭐⭐ | 单实例 + JWT + SQLite 对中小团队够用 |
| 遗漏点 | - | 未考虑 SOP 长任务执行中的认证续期问题 |
| 升级成本 | ⭐⭐⭐⭐ | 从方案 A 到方案 B 的增量改造路径清晰 |

#### 方案 B — 完整改造（6-8 周，生产就绪）

| 项目 | 评分 | 说明 |
|------|------|------|
| 工作量估算 | ⭐⭐⭐ | 偏乐观，含 K8s 部署 + 监控，实际需 8-12 周 |
| 架构设计 | ⭐⭐⭐ | 经典方案但缺乏针对性优化 |
| 关键遗漏 | - | 未考虑 Python 代码执行沙箱的安全隔离 |
| 运维复杂度 | ⭐⭐ | 引入 PostgreSQL + Redis + S3，运维成本大幅上升 |

---

### 二、已在正文中修复的问题

#### 🔴 P0 — 密码安全（超轻量方案）✅ 已修复

**原始问题**：
- YAML 中存储明文密码 + 直接 `==` 比较
- 无时序攻击防护
- Basic Auth 每次传输明文密码
- 无登录失败限制

**修复措施**（已更新至 Step 1/Step 2 章节）：
1. 密码使用 `bcrypt` 哈希存储（新增 `scripts/hash_password.py` 工具）
2. 验证使用 `bcrypt.checkpw`，防止时序攻击
3. 新增登录失败计数 + 账户锁定机制（默认 5 次失败锁定 15 分钟）
4. 新增登录审计日志

#### 🔴 P1 — Redis 查询效率（阶段四）✅ 已修复

**原始问题**：`get_user_executions` 使用 `SCAN` 全量扫描 + 逐条 GET + 内存过滤。

**修复措施**（已更新至阶段四章节）：
1. 新增 `user:{user_id}:executions` Set 索引
2. 写入状态时同步维护索引（`pipeline` 原子操作）
3. 查询时通过索引 `SMEMBERS` + `MGET` 批量获取
4. 自动清理过期索引条目

#### ⚠️ P2 — PersistentExecutionStore 工作量高估（阶段四）✅ 已修复

**原始问题**：文档将"会话状态外置"列为全新改造项，忽略了项目已有 `PersistentExecutionStore`。

**修复措施**（已更新至阶段四章节标注和核心不支持点第 5 条）：
1. 明确 Redis 定位为"热状态缓存"
2. 指出真正需要外置的仅为 `API/storage.py` 内存字典
3. 调整阶段四工作量预期

---

### 三、需要补充的改进方案（尚未修复，需后续实施）

#### 🔴 P0 — 代码执行沙箱隔离

**问题描述**：DeepAnalyze 核心功能是执行用户提交的数据分析任务（Python 代码执行），在多用户场景下，一个用户的代码可以访问其他用户的文件系统和进程。**这是最严重的安全风险，原始文档完全未提及。**

**影响范围**：方案 A、方案 B

**建议方案**：

```
方案优先级：容器沙箱 > 进程沙箱 > 目录隔离

┌─────────────────────────────────────────────────────────────────┐
│  方案 1: Docker 容器沙箱（推荐，方案 B 必须）                     │
│                                                                 │
│  用户提交任务 → 创建独立 Docker 容器 → 挂载用户目录（只读/读写）   │
│  → 限制 CPU/内存/网络 → 执行完成后销毁容器                        │
│                                                                 │
│  优势：强隔离、资源限制、安全性高                                  │
│  劣势：需要 Docker 环境、启动延迟（~1-3s）                        │
├─────────────────────────────────────────────────────────────────┤
│  方案 2: 进程级沙箱（轻量，方案 A 可用）                          │
│                                                                 │
│  使用 subprocess + chroot/namespace 限制执行环境                  │
│  限制文件系统访问范围、网络访问、系统调用                          │
│                                                                 │
│  优势：无需 Docker、启动快                                        │
│  劣势：隔离性弱于容器                                             │
├─────────────────────────────────────────────────────────────────┤
│  方案 3: 目录级隔离（最低限度，超轻量方案适用）                    │
│                                                                 │
│  通过路径校验确保用户只能访问自己的 workspace 目录                 │
│  Python 执行前 chdir 到用户目录 + 限制 import 路径                │
│                                                                 │
│  优势：改动最小                                                   │
│  劣势：无法防止恶意代码（如 os.system）                           │
└─────────────────────────────────────────────────────────────────┘
```

**Docker 容器沙箱实现参考**：

```python
# deepanalyze/sandbox/docker_executor.py

import docker
import tempfile
import os
from typing import Dict, Optional

class DockerSandbox:
    """Docker 容器沙箱执行器"""
    
    def __init__(self):
        self.client = docker.from_env()
        self.image = os.getenv("SANDBOX_IMAGE", "deepanalyze-sandbox:latest")
        self.default_limits = {
            "mem_limit": "512m",        # 内存限制
            "cpu_period": 100000,        # CPU 限制
            "cpu_quota": 50000,          # 50% CPU
            "network_disabled": True,    # 禁用网络
            "pids_limit": 100,           # 进程数限制
        }
    
    async def execute(
        self,
        code: str,
        user_workspace: str,
        timeout: int = 300,
        limits: Optional[Dict] = None
    ) -> Dict:
        """在沙箱中执行代码"""
        run_limits = {**self.default_limits, **(limits or {})}
        
        # 将代码写入临时文件
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.py', delete=False, dir=user_workspace
        ) as f:
            f.write(code)
            script_path = f.name
        
        try:
            container = self.client.containers.run(
                self.image,
                command=f"python /workspace/{os.path.basename(script_path)}",
                volumes={
                    user_workspace: {
                        'bind': '/workspace',
                        'mode': 'rw'
                    }
                },
                working_dir="/workspace",
                detach=True,
                **run_limits
            )
            
            # 等待执行完成（带超时）
            result = container.wait(timeout=timeout)
            logs = container.logs().decode('utf-8')
            
            return {
                "exit_code": result['StatusCode'],
                "output": logs,
                "error": result.get('Error', '')
            }
        except docker.errors.ContainerError as e:
            return {"exit_code": 1, "output": "", "error": str(e)}
        except Exception as e:
            return {"exit_code": -1, "output": "", "error": f"Sandbox error: {e}"}
        finally:
            try:
                container.remove(force=True)
            except Exception:
                pass
            os.unlink(script_path)
```

#### 🔴 P1 — SSE/长连接认证方案

**问题描述**：SOP 任务通过 SSE（Server-Sent Events）推送进度更新，当前无认证机制。JWT Token 可能在长任务执行过程中过期。

**影响范围**：方案 A、方案 B

**建议方案**：

```python
# API/sse_auth.py

from fastapi import Request, HTTPException
from fastapi.responses import StreamingResponse
from jose import jwt, JWTError
import asyncio

async def authenticated_sse_endpoint(
    request: Request,
    execution_id: str,
    token: str  # SSE 通过 query parameter 传递 token（WebSocket 同理）
):
    """
    带认证的 SSE 端点
    
    SSE/WebSocket 无法在 header 中传递 Bearer Token，
    因此通过 query parameter 传递，并在连接建立时验证。
    
    前端使用: new EventSource(`/sse/progress/${id}?token=${jwt_token}`)
    """
    # 验证 Token
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token expired or invalid")
    
    # 验证用户对此执行任务的访问权限
    execution = await get_execution(execution_id)
    if not execution or str(execution.user_id) != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    async def event_generator():
        while True:
            # 推送进度更新...
            status = state_manager.get_execution_status(execution_id)
            if status:
                yield f"data: {json.dumps(status)}\n\n"
            
            if status and status.get("status") in ("completed", "failed"):
                break
            
            await asyncio.sleep(1)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
```

**Token 续期策略**：

```python
# API/auth.py 追加

# SOP 任务专用的长效 Token（24 小时有效）
def create_task_token(user_id: int, execution_id: str) -> str:
    """为长时间运行的 SOP 任务创建专用 Token"""
    return jwt.encode(
        {
            "sub": str(user_id),
            "execution_id": execution_id,
            "type": "task",
            "exp": datetime.utcnow() + timedelta(hours=24)
        },
        SECRET_KEY,
        algorithm=ALGORITHM
    )

# 前端自动续期（在 Token 过期前 30 分钟刷新）
# Token 刷新端点
@router.post("/auth/refresh")
async def refresh_token(current_user: User = Depends(get_current_user)):
    """刷新 JWT Token"""
    new_token = create_access_token(data={"sub": str(current_user.id)})
    return {"access_token": new_token, "token_type": "bearer"}
```

#### 🔴 P1 — 文件下载接口鉴权（8100 端口）

**问题描述**：当前项目在 8100 端口运行 HTTP 文件服务器，用于提供工作区文件的下载访问。此端口**完全无认证**，任何人知道文件路径即可下载。

**影响范围**：所有方案

**建议方案**：

```python
# API/file_server.py

"""
方案一（推荐）：去掉独立的 8100 端口文件服务器，
将文件下载集成到主 FastAPI 应用中，统一通过认证中间件保护。
"""

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from pathlib import Path

router = APIRouter(prefix="/files", tags=["files"])

@router.get("/download/{session_id}/{filename:path}")
async def download_file(
    session_id: str,
    filename: str,
    current_user: dict = Depends(get_current_user)
):
    """带认证的文件下载端点"""
    # 验证用户对 workspace 的访问权限
    workspace = get_user_workspace(current_user['username'], session_id)
    file_path = Path(workspace) / filename
    
    # 路径遍历安全检查
    try:
        file_path.resolve().relative_to(Path(workspace).resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Path traversal detected")
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type="application/octet-stream"
    )
```

#### ⚠️ P1 — CORS 配置修正

**问题描述**：当前 `allow_origins=["*"]` + `allow_credentials=True`，根据 CORS 规范，浏览器会拒绝此组合。多用户场景下需要明确配置允许的 origins。

**影响范围**：所有方案

**修复方案**：

```python
# API/main.py CORS 配置修正

# ❌ 原始代码（浏览器会拒绝 credentials + wildcard）
cors_origins = os.getenv("CORS_ORIGINS", "*").split(",") if os.getenv("CORS_ORIGINS") else ["*"]

# ✅ 修正方案
def get_cors_origins() -> list:
    """获取 CORS 允许的 origins"""
    env_origins = os.getenv("CORS_ORIGINS", "")
    
    if env_origins:
        return [o.strip() for o in env_origins.split(",")]
    
    # 开发环境默认值
    environment = os.getenv("ENVIRONMENT", "development")
    if environment == "development":
        return ["http://localhost:3000", "http://localhost:8200"]
    elif environment == "intranet_test":
        # 内网测试：允许同网段访问
        return ["http://localhost:3000", "http://localhost:8200"]
        # 提示：部署时设置 CORS_ORIGINS 环境变量为实际访问地址
    else:
        # 生产环境必须明确指定
        raise ValueError(
            "Production environment requires explicit CORS_ORIGINS setting. "
            "Set CORS_ORIGINS='https://your-domain.com' in environment variables."
        )

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["X-Total-Count"],
)
```

#### ⚠️ P2 — 任务队列与资源配额

**问题描述**：多用户同时提交 SOP 长任务时，缺少排队和资源限制机制。单个用户的任务可能耗尽服务器 CPU/内存。

**影响范围**：方案 B

**建议方案**：

```python
# deepanalyze/task_queue/queue_manager.py

import asyncio
from collections import defaultdict
from typing import Dict, Optional

class TaskQueueManager:
    """
    任务队列管理器
    
    功能：
    1. 限制全局并发任务数
    2. 限制单用户并发任务数
    3. 任务排队与优先级调度
    """
    
    def __init__(
        self,
        max_global_concurrent: int = 5,
        max_user_concurrent: int = 2,
    ):
        self.max_global = max_global_concurrent
        self.max_user = max_user_concurrent
        self._global_semaphore = asyncio.Semaphore(max_global_concurrent)
        self._user_semaphores: Dict[int, asyncio.Semaphore] = defaultdict(
            lambda: asyncio.Semaphore(max_user_concurrent)
        )
        self._queue: asyncio.Queue = asyncio.Queue()
        self._active_tasks: Dict[str, dict] = {}
    
    async def submit_task(
        self, 
        execution_id: str,
        user_id: int,
        task_func,
        *args, **kwargs
    ) -> dict:
        """提交任务到队列"""
        # 检查用户并发限制
        user_sem = self._user_semaphores[user_id]
        if user_sem._value <= 0:
            return {
                "status": "queued",
                "message": f"You have reached the concurrent task limit ({self.max_user}). "
                           f"Task has been queued.",
                "queue_position": self._queue.qsize() + 1
            }
        
        # 获取信号量并执行
        async with self._global_semaphore:
            async with user_sem:
                self._active_tasks[execution_id] = {
                    "user_id": user_id,
                    "status": "running"
                }
                try:
                    result = await task_func(*args, **kwargs)
                    return {"status": "completed", "result": result}
                except Exception as e:
                    return {"status": "failed", "error": str(e)}
                finally:
                    self._active_tasks.pop(execution_id, None)
    
    def get_queue_status(self) -> dict:
        """获取队列状态"""
        return {
            "active_tasks": len(self._active_tasks),
            "max_global_concurrent": self.max_global,
            "queued_tasks": self._queue.qsize(),
        }

# 全局实例
task_queue = TaskQueueManager(
    max_global_concurrent=int(os.getenv("MAX_GLOBAL_TASKS", "5")),
    max_user_concurrent=int(os.getenv("MAX_USER_TASKS", "2")),
)
```

#### ⚠️ P2 — 前端 Next.js Middleware 鉴权拦截

**问题描述**：现有前端是 Next.js 14 App Router 架构，文档直接给出了登录页面代码，但未考虑 middleware 层面的路由守卫。

**影响范围**：方案 A、方案 B

**建议方案**：

```typescript
// demo/chat/middleware.ts

import { NextRequest, NextResponse } from "next/server";

// 不需要认证的路径
const PUBLIC_PATHS = ["/login", "/api/auth"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  
  // 公开路径直接放行
  if (PUBLIC_PATHS.some(p => pathname.startsWith(p))) {
    return NextResponse.next();
  }
  
  // 静态资源放行
  if (pathname.startsWith("/_next") || pathname.startsWith("/favicon")) {
    return NextResponse.next();
  }
  
  // 检查认证状态
  // 注意：Basic Auth 方案下，凭证存在 localStorage（客户端），
  //       middleware 运行在服务端，无法直接访问。
  //       因此 middleware 主要用于 JWT 方案（cookie 传递 token）。
  
  // JWT 方案：从 cookie 读取 token
  const token = request.cookies.get("auth_token")?.value;
  
  if (!token) {
    // 重定向到登录页
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("redirect", pathname);
    return NextResponse.redirect(loginUrl);
  }
  
  // 可选：验证 token 是否过期（仅检查格式，不做完整验证）
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    if (payload.exp && payload.exp * 1000 < Date.now()) {
      const loginUrl = new URL("/login", request.url);
      return NextResponse.redirect(loginUrl);
    }
  } catch {
    const loginUrl = new URL("/login", request.url);
    return NextResponse.redirect(loginUrl);
  }
  
  return NextResponse.next();
}

export const config = {
  matcher: [
    // 匹配所有路径，除了 API 路由和静态资源
    "/((?!_next/static|_next/image|favicon.ico).*)",
  ],
};
```

---

### 四、改进建议优先级汇总

| 优先级 | 改进项 | 影响方案 | 状态 |
|--------|--------|----------|------|
| P0 | 密码安全（bcrypt 哈希 + 登录锁定） | 超轻量方案 | ✅ 已修复 |
| P0 | 代码执行沙箱隔离 | 方案 A、B | 📋 已给出方案，待实施 |
| P1 | Redis 查询效率（索引集合） | 方案 B | ✅ 已修复 |
| P1 | SSE/长连接认证 + Token 续期 | 方案 A、B | 📋 已给出方案，待实施 |
| P1 | 文件下载接口（8100端口）鉴权 | 所有方案 | 📋 已给出方案，待实施 |
| P1 | CORS 配置修正 | 所有方案 | 📋 已给出方案，待实施 |
| P2 | 任务队列与资源配额 | 方案 B | 📋 已给出方案，待实施 |
| P2 | PersistentExecutionStore 工作量调整 | 方案 B | ✅ 已修复 |
| P2 | 数据库改造分场景必要性评估 | 所有方案 | ✅ 已修复 |
| P3 | 前端 Next.js middleware 鉴权 | 方案 A、B | 📋 已给出方案，待实施 |

### 五、工作量估算修正

| 方案 | 原始估算 | 修正估算 | 调整原因 |
|------|----------|----------|----------|
| 超轻量方案 | 2-4 小时 | 4-6 小时 | 新增 bcrypt + 登录保护增加约 1-2 小时 |
| 方案 A（伪多用户） | 6 天 | 8-10 天 | JWT + 前端登录 + 权限校验 + SSE 认证 + 测试 |
| 方案 B（完整改造） | 6-8 周 | 8-12 周 | 需新增沙箱隔离 + 任务队列 + 资源配额 |
| 方案 B — Phase 4 | 3 天 | 1-2 天 | 已有 PersistentExecutionStore，仅需外置 API 层内存状态 |

---

## 风险评估

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|----------|
| 数据迁移失败 | 中 | 高 | 完整备份、分阶段迁移、回滚方案 |
| 性能不达标 | 中 | 高 | 提前压测、预留扩展空间 |
| 安全漏洞 | 中 | 高 | 代码审计、渗透测试、安全加固 |
| **代码执行逃逸**（v1.2 新增） | 中 | **极高** | Docker 沙箱隔离、限制系统调用、网络隔离 |
| **长任务认证过期**（v1.2 新增） | 高 | 中 | Task Token + 自动续期机制 |
| **跨用户数据泄露**（v1.2 新增） | 中 | 高 | 路径遍历防护 + 文件接口鉴权 + 沙箱隔离 |
| 改造成本超支 | 低 | 中 | 分阶段实施、MVP 先行 |
| 用户抵触 | 低 | 中 | 提前沟通、保留原有入口 |

---

## 附录

### A. 环境变量配置清单

#### 生产环境配置

```bash
# 数据库
DATABASE_URL=postgresql://user:password@localhost:5432/deepanalyze

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRE_DAYS=7

# 存储
STORAGE_TYPE=s3  # 或 local
S3_BUCKET=deepanalyze-files
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
S3_REGION=us-east-1
S3_ENDPOINT=https://s3.amazonaws.com  # 兼容 OSS/COS

# 安全配置
RATE_LIMIT_ENABLED=true
RATE_LIMIT_DEFAULT=100
RATE_LIMIT_CHAT=60

# 其他
LOG_LEVEL=INFO
ENVIRONMENT=production  # development / staging / production
```

#### 内网测试环境配置

```bash
# 内网测试环境（最小可行方案）
ENVIRONMENT=intranet_test
API_HOST=0.0.0.0
API_PORT=8200

# 工作区目录（建议使用共享目录）
WORKSPACE_BASE_DIR=D:\DeepAnalyzeData\workspace

# 日志级别
LOG_LEVEL=INFO
```

### B. 依赖安装

#### 生产环境依赖

```bash
# 后端依赖
pip install psycopg2-binary  # PostgreSQL
pip install redis           # Redis
pip install python-jose     # JWT
pip install passlib         # 密码哈希
pip install alembic         # 数据库迁移
pip install boto3           # AWS S3
```

#### 内网测试环境依赖

```bash
# v1.2 更新：需要 bcrypt 用于安全密码验证
pip install pyyaml bcrypt

# 其他依赖保持原有 requirements.txt 不变
```

### C. 监控指标

| 指标 | 说明 | 告警阈值 |
|------|------|----------|
| API 响应时间 | P95 响应时间 | > 2s |
| 错误率 | 5xx 错误占比 | > 1% |
| 数据库连接数 | 活跃连接数 | > 80% |
| Redis 内存使用 | 内存使用率 | > 80% |
| 磁盘空间 | 文件存储使用率 | > 85% |
| 活跃用户数 | 并发在线用户 | 根据容量规划 |

---

## 结论

DeepAnalyze 项目**不具备直接支持线上多用户部署的能力**，需要进行系统性改造。核心改造点包括：

1. **用户认证系统** - 必须
2. **数据库迁移** - 按用户规模分场景评估（<20 人可保留 SQLite WAL 模式）
3. **文件存储改造** - 必须
4. **会话状态外置** - 必须（但工作量因已有 PersistentExecutionStore 而降低）
5. **前端登录集成** - 必须（含 Next.js middleware 鉴权）
6. **API 安全加固** - 推荐（含 CORS 修正、限流）
7. **容器化部署** - 推荐
8. **监控与日志** - 推荐
9. **🔴 代码执行沙箱隔离** - 方案 B **必须**，方案 A 强烈建议（v1.2 新增）
10. **SSE/长连接认证** - 方案 A、B 必须（v1.2 新增）
11. **文件下载接口鉴权** - 所有方案必须（v1.2 新增）
12. **任务队列与资源配额** - 方案 B 推荐（v1.2 新增）

**预计总工期（v1.2 修正）**：

| 方案 | 原始估算 | 修正估算 |
|------|----------|----------|
| 超轻量方案 | 2-4 小时 | 4-6 小时 |
| 方案 A | 1-2 周 | 2-2.5 周 |
| 方案 B | 6-8 周 | 8-12 周 |

**预计总成本：¥850-1650/月（云资源）+ 人力成本**

建议采用**分阶段实施策略**：
- **即时（4-6 小时）**：最小可行方案（内网 <5 人测试），bcrypt 安全认证 + 配置文件
- **短期（2-2.5 周）**：方案 A（伪多用户），JWT + SSE 认证 + 文件鉴权
- **中期（8-12 周）**：方案 B（完整改造），沙箱隔离 + 任务队列 + 生产环境就绪

> **v1.2 核心发现**：原始文档的问题诊断全面准确，渐进式路线合理。但在安全维度上有两个重大盲区：① 超轻量方案的密码安全过于草率（已修复），② 完全遗漏了多用户场景下代码执行的沙箱隔离问题（已给出方案）。此外工作量整体偏乐观约 30-50%。建议将"代码执行安全隔离"列为方案 B 的 Phase 0。

---

*文档生成时间：2025-03-02*  
*v1.2 审阅更新：2025-03-10*  
*v1.3 实施进度更新：2026-03-28*  
*v1.5 修复双重登录 + workspace 隔离 TODO：2026-04-09*  
*v1.6 新增账户有效期控制方案：2026-06-01*  
*版本：v1.6*  
*状态：超轻量方案已实施完成，CVM Docker 部署已上线，双重登录问题已修复*

---

## 账户有效期控制方案（v1.6 新增）

> **背景**：内网多用户版本采用 `config/users.yaml` 手动维护账户，现有字段仅含
> `username / password_hash / role / org / description`，无账户生命周期管理，
> 账户创建后永久有效，管理员需手动删除用户才能吊销访问权限。
>
> **适用范围**：超轻量 BasicAuth 方案（当前已上线的内网多用户版本）。  
> JWT/完整用户系统升级路径另见第一章"阶段一：用户认证与授权"。

### 一、需求场景

| 场景 | 描述 |
|------|------|
| **临时访问授权** | 给合作方/临时人员开放访问权限，到期自动失效 |
| **试用期控制** | 新加入成员试用期结束后需重新审批续期 |
| **合规要求** | 按期审查账户有效性，满足访问控制审计要求 |
| **统一到期提醒** | 账户到期前提前告知，避免突然失效影响工作 |

### 二、方案设计

#### 2.1 users.yaml 新增字段

```yaml
# config/users.yaml
users:
  - username: admin
    password_hash: "$2b$12$..."
    role: admin
    org: ""
    description: "管理员"
    # valid_until 留空或不填 = 永久有效
    valid_until: ""

  - username: user1
    password_hash: "$2b$12$..."
    role: user
    org: "风控部门"
    description: "临时合作访问"
    valid_until: "2026-12-31"    # 到期日期，ISO 8601 格式 YYYY-MM-DD

  - username: user2
    password_hash: "$2b$12$..."
    role: user
    org: "数据分析组"
    description: "试用期账户"
    valid_until: "2026-07-01"
```

**字段说明**：
- `valid_until`：账户有效截止日期（含当天）。空字符串或缺省字段 = 永久有效。
- 日期格式：`YYYY-MM-DD`（如 `2026-12-31`）。
- 过期判断：`date.today() > date.fromisoformat(valid_until)`，即截止日 **当天仍有效**，次日起拒绝。

#### 2.2 auth_middleware.py 改动（核心逻辑）

在 `authenticate_user()` 方法中，密码验证通过后增加有效期检查：

```python
def authenticate_user(self, username: str, password: str) -> Optional[dict]:
    """验证用户名和密码，返回用户信息或 None"""
    user = self.users.get(username)
    if not user:
        bcrypt.hashpw(b"dummy", bcrypt.gensalt())  # 防时序攻击
        return None

    # 密码验证
    stored_hash = user.get('password_hash', '').encode('utf-8')
    if not bcrypt.checkpw(password.encode('utf-8'), stored_hash):
        return None

    # ★ 账户有效期检查（新增）
    valid_until = user.get('valid_until', '')
    if valid_until:
        try:
            from datetime import date
            expiry = date.fromisoformat(str(valid_until).strip())
            if date.today() > expiry:
                logger.warning(f"账户已过期，拒绝登录: username={username}, valid_until={valid_until}")
                return None  # 过期账户，返回 None（触发 401）
        except ValueError:
            logger.error(f"users.yaml 中 valid_until 格式错误: username={username}, value={valid_until}")
            # 格式错误时保守处理：拒绝登录
            return None

    return user
```

**过期后的用户体验**：
- 浏览器弹出 Basic Auth 登录框 → 输入正确密码 → 后端返回 `401 Unauthorized`
- 浏览器反复弹出登录框（Basic Auth 的固有行为），提示"账号密码不正确"
- 建议：在 401 响应体中增加 `reason: account_expired` 供前端识别（见 2.3）

#### 2.3 友好提示改进（可选）

Basic Auth 的限制是浏览器原生处理 401，无法展示自定义页面。可在响应头中增加额外信息：

```python
# auth_middleware.py 中返回 401 时
if is_expired:
    return Response(
        status_code=401,
        headers={
            "WWW-Authenticate": 'Basic realm="CreditWise - 账户已过期，请联系管理员续期"',
            "X-Auth-Error": "account_expired"
        }
    )
```

浏览器登录框的 `realm` 字段会显示提示文字，用户可看到"账户已过期，请联系管理员续期"。

#### 2.4 users.yaml.example 更新

同步更新示例文件：

```yaml
users:
  - username: admin
    password_hash: "$2b$12$PLACEHOLDER_USE_hash_password_py"
    role: admin
    org: ""
    description: "管理员"
    valid_until: ""              # 留空 = 永久有效

  - username: user1
    password_hash: "$2b$12$PLACEHOLDER_USE_hash_password_py"
    role: user
    org: "部门名称"
    description: "测试用户1，有效期至年底"
    valid_until: "2026-12-31"   # 到期日期 YYYY-MM-DD，留空=永久有效

settings:
  max_login_failures: 5
  lockout_duration_minutes: 15
```

### 三、实施步骤

| # | 任务 | 文件 | 工作量 |
|---|------|------|--------|
| 1 | `auth_middleware.py` 新增有效期检查逻辑（约 15 行） | `API/auth_middleware.py` | ~30 min |
| 2 | 更新 `users.yaml.example` 增加 `valid_until` 字段示例 | `config/users.yaml.example` | ~10 min |
| 3 | 更新 `test_auth_middleware.py` 补充过期账户测试用例 | `tests/test_auth_middleware.py` | ~30 min |
| 4 | 更新 `intranet_deployment_guide.md` 说明新字段 | `docs/intranet_deployment_guide.md` | ~15 min |
| **合计** | | | **~1.5 小时** |

### 四、安全注意事项

| 注意点 | 说明 |
|--------|------|
| **过期即拒绝** | 不设宽限期，`valid_until` 次日 00:00 起立即失效，简单可预期 |
| **格式容错** | `valid_until` 格式错误时保守拒绝（不允许登录），防止配置错误导致账户永久有效 |
| **admin 不建议设有效期** | 管理员账户意外过期会导致无法管理系统，建议留空 |
| **过期日志** | 过期登录尝试写入 `WARNING` 级别日志，便于审计 |
| **不影响现有账户** | 现有 `users.yaml` 无 `valid_until` 字段的账户自动视为永久有效，零迁移成本 |

### 五、与未来 JWT 方案的关系

| 维度 | 当前 BasicAuth 有效期方案 | 未来 JWT 完整方案 |
|------|--------------------------|-----------------|
| 有效期粒度 | 日期级（手动配置） | 可到秒级（token 自动过期） |
| 续期方式 | 管理员手动修改 yaml | 用户主动刷新 token |
| 实施成本 | ~1.5 小时 | JWT 方案整体 2-2.5 周 |
| 适用场景 | 内网 <5 人，当前阶段 | 团队 10+ 人，长期方向 |

当前 BasicAuth 方案实施有效期控制完全独立，不影响未来向 JWT 迁移。
*版本：v1.5*  
*状态：超轻量方案已实施完成，CVM Docker 部署已上线，双重登录问题已修复*

---

## 超轻量方案实施进度（v1.3 新增）

> 分支：`feature/intranet-multiuser`  
> 部署地址：`http://fjzheng.devcloud.woa.com:8200`  
> 部署方式：Docker（CVM Linux）  
> 实施日期：2026-03-27 ~ 2026-03-28

### 一、实施完成清单

| # | 任务 | 文件 | 状态 |
|---|------|------|:----:|
| 1 | 用户配置文件 | `config/users.yaml` + `config/users.yaml.example` | ✅ 完成 |
| 2 | 密码哈希工具 | `scripts/hash_password.py` | ✅ 完成 |
| 3 | Basic Auth 中间件 | `API/auth_middleware.py` | ✅ 完成 |
| 4 | 角色级访问控制 | admin-only 路由（LLM Manager 管理接口） | ✅ 完成 |
| 5 | 主应用集成 | `API/main.py`（`ENABLE_AUTH` 环境变量控制） | ✅ 完成 |
| 6 | 前端认证封装 | `demo/chat/lib/config.ts`（`authFetch` + prompt 登录） | ✅ 完成 |
| 7 | 前端 API 动态地址 | `config.ts`（运行时 `window.location.origin`，兼容开发/生产） | ✅ 完成 |
| 8 | ModelSelector 硬编码修复 | `demo/chat/components/ModelSelector.tsx` | ✅ 完成 |
| 9 | Docker 双模式配置 | `docker/Dockerfile` + `docker/docker-compose.yml` | ✅ 完成 |
| 10 | 前端生产模式静态文件挂载 | `API/main.py`（`/_next` StaticFiles + SPA fallback） | ✅ 完成 |
| 11 | LLM Manager UI 路径修复 | `llm_manager_integrated/static/index.html`（绝对路径） | ✅ 完成 |
| 12 | 静态资源认证白名单 | `API/auth_middleware.py`（`/_next` + `/llm-manager/static`） | ✅ 完成 |
| 13 | 依赖兼容性修复 | `requirements.txt`（`setuptools<82` + `pandas<3.0`） | ✅ 完成 |
| 14 | scorecardpy 兼容性修复 | `scorecard_development.py`（`sc.split_df` → `sklearn.train_test_split`） | ✅ 完成 |
| 15 | Linux 部署脚本 | `scripts/deploy_linux.sh`（7步自动化：Docker检查 → 用户配置 → 环境配置+密钥自动生成 → DB文件预创建 → 构建 → 启动 → 验证） + `scripts/service.sh` | ✅ 完成 |
| 16 | 模型配置同步脚本 | `scripts/sync_model_configs.sh`（认证信息改为参数/环境变量传入） | ✅ 完成 |
| 17 | 测试用例（20个） | `tests/test_auth_middleware.py` | ✅ 完成 |
| 18 | 部署指南文档 | `docs/intranet_deployment_guide.md` | ✅ 完成 |

### 二、用户账号

| 用户名 | 角色 | 部门 |
|--------|------|------|
| admin | admin | CSIG-CTOSD |
| fjzheng | admin | CSIG-CTOSD |
| sylarswwang | user | CSIG-SPD2 |
| gurayzhang | user | CSIG-SPD2 |
| laughingtan | user | CSIG-SPD2 |
| webberwu | user | CSIG-SPD2 |

### 三、已配置的 LLM 渠道

| 渠道名 | 类型 | 模型 | 状态 |
|--------|------|------|:----:|
| local_deepseek | custom (Venus) | deepseek-v3.1-terminus | ✅ 已启用 |
| local_kimi | custom (Venus) | kimi-k2.5 | ✅ 已启用 |

### 四、部署过程中发现并修复的问题

| # | 问题 | 根因 | 修复方案 |
|---|------|------|---------|
| 1 | Dockerfile COPY .env.example 失败 | `.gitignore` 的 `.env.*` 规则排除了 `.env.example` | 添加 `!.env.example` 排除规则 + 删除 Dockerfile 中的 COPY |
| 2 | Next.js 构建产物路径错误 | `output:'export'` + `distDir:'dist'`，产物在 `dist/` 不是 `.next/` | Dockerfile 改为 COPY `dist/` |
| 3 | 前端请求指向 `127.0.0.1:8200` | `process.env.NEXT_PUBLIC_*` 在 `output:'export'` 构建时被替换为字面量 | 改为运行时 `window.location.origin`，按端口判断开发/生产模式 |
| 4 | API 路由被 StaticFiles 覆盖 | `app.mount("/", StaticFiles(...))` 拦截了所有请求 | 改为只挂载 `/_next` 前缀 + exception_handler 做 SPA fallback |
| 5 | SOP Task API 注册失败 | Python 3.12 移除了 `pkg_resources`，`scorecardpy` 依赖它 | `requirements.txt` 添加 `setuptools<82` |
| 6 | `llm_manager.db` 被 Docker 创建为目录 | 文件不存在时 Docker volume 挂载默认创建目录 | 先 `touch` 创建空文件再启动容器 |
| 7 | `LLM_MANAGER_ENCRYPTION_KEY` 未传入容器 | `docker-compose.yml` 的 `env_file` 和 `environment` `${}` 是两套机制 | 在 CVM 的 `docker-compose.yml` 中直接写入密钥值 |
| 8 | 评分卡 `split_data` 报 `float has no len()` | CVM 安装了 pandas 3.0.1，`str.findall()` 对 NaN 返回 float 而非 list | `requirements.txt` 固定 `pandas<3.0` + 用 `sklearn.train_test_split` 替代 `sc.split_df` |
| 9 | LLM Manager UI `index.html` 显示 JS export 语句 | Vite 构建的 `assetsInclude: ['**/*.html']` 把 index.html 当资源处理 | 用 `static/assets/index.html`（真正的 HTML）覆盖 `static/index.html` |
| 10 | LLM Manager UI JS/CSS 被认证拦截 | `<script src>` 标签不会自动带 Basic Auth header | 将 `/llm-manager/static` 和 `/_next` 加入认证白名单 |
| 11 | 首次部署 `llm_manager.db` 被创建为目录 | Docker bind mount 对不存在的文件路径默认创建为目录，SQLite 无法打开 | `deploy_linux.sh` 新增步骤 [4/7]：`touch llm_manager.db task_manager.db` 预创建空文件（v1.4） |
| 12 | 加密密钥需手动配置，否则启动报 ValueError | `.env` 被 gitignore，git clone 后没有 `LLM_MANAGER_ENCRYPTION_KEY` | `deploy_linux.sh` 步骤 [3/7] 自动检测并生成 Fernet 密钥写入 `.env`（v1.4） |
| 13 | `sync_model_configs.sh` 硬编码明文密码 | 脚本中 `AUTH="fjzheng:Anna0203"` 被提交到仓库 | 改为从命令行参数 `$1` 或环境变量 `CREDITWISE_AUTH` 读取（v1.4） |
| 14 | 打开网页需要登录两次 | `/`（首页 HTML）不在认证白名单 → 后端返回 `401 + WWW-Authenticate: Basic` → 浏览器弹出原生 Basic Auth 对话框（第1次）→ 获取 HTML 后前端 JS 加载 → `authFetch` 发现 `localStorage` 无凭证 → 弹出 `window.prompt`（第2次） | 在 `auth_middleware.py` 新增 `AUTH_WHITELIST_EXACT` 精确匹配白名单，将 `/` 和 `/favicon.ico` 放行，让前端 `authFetch` 统一处理认证（v1.5，commit `55fcbc5`） |
| 15 | 不同终端/清缓存后上传的数据集"丢失" | `sessionId` 存储在浏览器 `localStorage` 中，不同终端或清缓存后会生成新的随机 `sessionId`，新 session 对应空的 workspace 目录 | 旧文件仍在 CVM `workspace/session_旧ID/` 目录下，可手动 `cp` 恢复。根本性修复见下方 TODO（v1.5） |

### 五、已知遗留问题

| # | 问题 | 影响 | 优先级 | 说明 |
|---|------|------|:------:|------|
| 1 | LLM Manager UI Tailwind CSS 样式缺失 | Tab 无阴影/悬停效果，布局非横向排列 | P3 | Tailwind 通过外网 CDN（`cdn.tailwindcss.com`）加载，CVM 内网无法访问。修复方案：将 Tailwind CSS 改为本地构建的 CSS 文件引用 |
| 2 | ~~任务历史记录未按用户隔离~~ | ~~所有用户可看到所有任务历史~~ | ~~P3~~ | ✅ 已完成（2026-07-02），详见 [`user_management_module_design.md`](./user_management_module_design.md)§九：`/sop/history`列表强制按登录用户过滤，13个记录详情/分析端点所有权校验 |
| 3 | `docker-compose.yml` 中 `version` 属性警告 | 无功能影响，仅日志警告 | P4 | Docker Compose V2 已弃用 `version` 字段 |
| 4 | ~~CVM `docker-compose.yml` 中硬编码了加密密钥~~ | ~~安全风险（仅 CVM 本地文件）~~ | ~~P2~~ | ✅ v1.4 已修复：`deploy_linux.sh` 自动生成密钥写入 `.env`，无需硬编码 |
| 5 | ~~workspace 目录应基于登录用户名而非随机 sessionId~~ | ~~同账号不同终端/清缓存后无法看到已上传的文件~~ | ~~P1~~ | ✅ 已完成（2026-07-02），详见 [`user_management_module_design.md`](./user_management_module_design.md)§九：`session_id`改为登录用户名派生，新增自助认领旧会话接口 |

### 六、CVM 日常运维命令

```bash
cd /data/CreditWise/docker

# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f --tail 50

# 重启服务
ENABLE_AUTH=true docker compose up -d

# 停止服务
docker compose down

# 代码更新后重建
cd /data/CreditWise && git pull
cd docker && docker compose build && ENABLE_AUTH=true docker compose up -d

# 清理无用镜像
docker image prune -f
```
