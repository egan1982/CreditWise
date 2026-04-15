# Task Management Module Design

> 任务管理功能模块完整设计方案

---

## 目录

1. [概述](#1-概述)
2. [需求分析](#2-需求分析)
3. [架构设计](#3-架构设计)
4. [数据模型设计](#4-数据模型设计)
5. [核心组件设计](#5-核心组件设计)
6. [API接口设计](#6-api接口设计)
7. [集成方案](#7-集成方案)
8. [实施计划](#8-实施计划)
9. [验收标准](#9-验收标准)
10. [附录](#10-附录)
11. [执行状态持久化方案（Phase 6 - ✅ 已完成）](#11-执行状态持久化方案phase-6---已完成)
12. [阶段 AI 分析结果持久化方案（Phase 7 - ✅ 已完成）](#12-阶段-ai-分析结果持久化方案phase-7---已完成)
13. [推理任务记录集成（Phase 8 - ✅ 已完成）](#13-推理任务记录集成phase-8---已完成)

---

## 1. 概述

### 1.1 模块目标

为 Task SOP 模块及其他长时任务提供统一的任务管理能力，包括：

- **任务进程控制**：支持任务的暂停、停止、恢复操作
- **任务记录持久化**：将任务执行记录保存到数据库，支持跨会话访问
- **历史记录查询**：支持按任务类型、时间范围、状态等条件查询历史任务

### 1.2 核心功能

| 功能 | 说明 |
|------|------|
| 暂停任务 | 在检查点暂停正在执行的任务，保存当前状态 |
| 停止任务 | 终止任务执行，释放资源 |
| 恢复任务 | 从暂停状态恢复任务执行 |
| 记录持久化 | 将任务元数据、参数、结果摘要保存到数据库 |
| 历史查询 | 支持多条件筛选、分页查询历史任务 |
| 结果回调 | 加载历史任务的完整执行结果 |

### 1.3 设计原则

1. **通用性**：模块设计不耦合 Task SOP 业务逻辑，可复用至其他任务类型
2. **低侵入**：最小化对现有代码的修改，通过扩展而非重写实现
3. **可扩展**：支持未来扩展到 Redis/PostgreSQL 等存储后端
4. **高性能**：控制状态内存缓存，减少数据库查询

---

## 2. 需求分析

### 2.1 功能需求

#### 2.1.1 任务控制需求

| 需求ID | 需求描述 | 优先级 |
|--------|----------|--------|
| TC-001 | 支持暂停正在执行的任务 | P0 |
| TC-002 | 支持停止正在执行的任务 | P0 |
| TC-003 | 支持恢复已暂停的任务 | P0 |
| TC-004 | 暂停/停止操作应在合理时间内响应（<5秒） | P1 |
| TC-005 | 暂停时保存当前执行状态，恢复后可继续 | P1 |
| TC-006 | 停止时清理资源，释放内存 | P1 |

#### 2.1.2 记录管理需求

| 需求ID | 需求描述 | 优先级 |
|--------|----------|--------|
| RM-001 | 任务开始时创建执行记录 | P0 |
| RM-002 | 任务完成/失败时更新记录状态 | P0 |
| RM-003 | 记录任务参数、输入摘要、输出摘要 | P0 |
| RM-004 | 持久化完整执行结果到文件系统 | P1 |
| RM-005 | 支持删除历史记录 | P2 |
| RM-006 | 支持清理过期记录 | P2 |

#### 2.1.3 历史查询需求

| 需求ID | 需求描述 | 优先级 |
|--------|----------|--------|
| HQ-001 | 按任务类型筛选 | P0 |
| HQ-002 | 按执行状态筛选 | P0 |
| HQ-003 | 按时间范围筛选 | P1 |
| HQ-004 | 按会话ID筛选 | P1 |
| HQ-005 | 支持分页查询 | P0 |
| HQ-006 | 加载历史任务完整结果 | P0 |
| HQ-007 | 获取任务统计信息 | P2 |

### 2.2 非功能需求

| 需求ID | 需求描述 | 指标 |
|--------|----------|------|
| NF-001 | 数据库写入性能 | 单次写入 < 100ms |
| NF-002 | 历史查询性能 | 1000条记录查询 < 500ms |
| NF-003 | 控制响应时间 | 暂停/停止响应 < 5秒 |
| NF-004 | 数据可靠性 | 任务完成后记录必须持久化 |
| NF-005 | 存储空间 | 支持配置结果文件保留策略 |

### 2.3 用户场景

#### 场景1：长时任务暂停与恢复

```
用户启动评分卡开发任务（预计10分钟）
↓
执行到特征选择阶段（3分钟）
↓
用户点击"暂停"
↓
系统在当前阶段完成后暂停，保存状态
↓
用户稍后点击"恢复"
↓
系统从暂停点继续执行
```

#### 场景2：任务异常终止

```
用户启动规则挖掘任务
↓
执行过程中发现参数配置错误
↓
用户点击"停止"
↓
系统终止执行，保存已完成阶段的结果
↓
用户可查看部分结果，调整参数后重新执行
```

#### 场景3：历史任务回调

```
用户上周执行了一个评分卡任务
↓
用户进入历史记录页面
↓
筛选：任务类型=评分卡开发，时间=上周
↓
查看任务详情（参数、阶段进度、耗时）
↓
加载完整结果（评分卡、模型指标）
↓
导出或复用结果
```

---

## 3. 架构设计

### 3.1 模块结构

```
deepanalyze/core/task_manager/
├── __init__.py              # 模块导出
├── database.py              # 数据库管理（复用DatabaseManager模式）
├── models.py                # ORM模型定义
├── enums.py                 # 枚举定义
├── controller.py            # 任务控制器（暂停/停止/恢复）
├── history_service.py       # 历史查询服务
├── result_storage.py        # 结果文件存储
├── persistent_store.py      # 持久化执行存储
└── integration.py           # 与现有模块集成
```

### 3.2 组件关系图

```
┌─────────────────────────────────────────────────────────────────┐
│                          API Layer                               │
│                        (sop_api.py)                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │ TaskController│    │TaskHistory   │    │TaskResult    │       │
│  │              │    │Service       │    │Storage       │       │
│  │ - pause()   │    │ - list()     │    │ - save()     │       │
│  │ - stop()    │    │ - get()      │    │ - load()     │       │
│  │ - resume()  │    │ - delete()   │    │ - cleanup()  │       │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘       │
│         │                   │                   │                │
│         ▼                   ▼                   ▼                │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              PersistentExecutionStore                     │   │
│  │                                                           │   │
│  │  - create() → 创建记录 + 持久化                           │   │
│  │  - update() → 更新状态 + 同步数据库                       │   │
│  │  - get()    → 优先内存，回退数据库                        │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
├──────────────────────────────┼───────────────────────────────────┤
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    TaskManagerDB                          │   │
│  │                   (SQLite/PostgreSQL)                     │   │
│  │                                                           │   │
│  │  ┌─────────────┐    ┌─────────────┐                      │   │
│  │  │ TaskRecord  │    │ TaskControl │                      │   │
│  │  │   Table     │    │    Table    │                      │   │
│  │  └─────────────┘    └─────────────┘                      │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                  File System Storage                      │   │
│  │                  (task_results/)                          │   │
│  │                                                           │   │
│  │  {record_id}/                                             │   │
│  │  ├── result.json      # 完整结果                          │   │
│  │  ├── outputs.pkl      # 大型对象（DataFrame等）           │   │
│  │  └── metadata.json    # 元数据                            │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 与现有代码的集成

```
┌─────────────────────────────────────────────────────────────────┐
│                     现有代码                                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  executor.py                                                     │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ ExecutionStore (内存)                                    │    │
│  │      ↓                                                   │    │
│  │ PersistentExecutionStore (扩展)  ←── 新增持久化层        │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ SOPExecutor._run_task()                                  │    │
│  │      ↓                                                   │    │
│  │ + 检查点调用 (check_control_state)  ←── 新增控制检查     │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ ExecutionContext                                         │    │
│  │      ↓                                                   │    │
│  │ + control_state 字段  ←── 新增控制状态                   │    │
│  │ + record_id 字段      ←── 新增记录ID                     │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  sop_api.py                                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 现有接口                                                 │    │
│  │      ↓                                                   │    │
│  │ + POST /sop/executions/{id}/pause   ←── 新增            │    │
│  │ + POST /sop/executions/{id}/stop    ←── 新增            │    │
│  │ + POST /sop/executions/{id}/resume  ←── 新增            │    │
│  │ + GET  /sop/history                 ←── 新增            │    │
│  │ + GET  /sop/history/{id}            ←── 新增            │    │
│  │ + GET  /sop/history/{id}/result     ←── 新增            │    │
│  │ + GET  /sop/statistics              ←── 新增            │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. 数据模型设计

### 4.1 枚举定义

```python
# enums.py

from enum import Enum

class TaskStatus(str, Enum):
    """任务执行状态"""
    PENDING = "pending"          # 等待执行
    RUNNING = "running"          # 正在执行
    PAUSED = "paused"            # 已暂停
    COMPLETED = "completed"      # 执行完成
    FAILED = "failed"            # 执行失败
    STOPPED = "stopped"          # 用户停止
    CANCELLED = "cancelled"      # 已取消


class TaskControlAction(str, Enum):
    """任务控制动作"""
    NONE = "none"                # 无动作
    PAUSE = "pause"              # 请求暂停
    STOP = "stop"                # 请求停止
    RESUME = "resume"            # 请求恢复


class TaskCategory(str, Enum):
    """任务类别（用于通用性）"""
    SOP = "sop"                  # SOP任务（规则挖掘、评分卡等）
    INFERENCE = "inference"      # LLM推理任务
    TRAINING = "training"        # 模型训练任务
    ETL = "etl"                  # 数据处理任务
    OTHER = "other"              # 其他任务
```

### 4.2 ORM模型

```python
# models.py

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Index
from sqlalchemy.ext.declarative import declarative_base

TaskManagerBase = declarative_base()


class TaskRecord(TaskManagerBase):
    """任务执行记录"""
    __tablename__ = "task_records"
    
    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)
    record_id = Column(String(64), unique=True, nullable=False, index=True)
    
    # 任务标识
    task_type = Column(String(64), nullable=False, index=True)      # rule_mining, scorecard_dev
    task_category = Column(String(32), nullable=False, default="sop")  # sop, inference, training
    execution_id = Column(String(64), nullable=True, index=True)    # 关联ExecutionContext
    session_id = Column(String(64), nullable=True, index=True)
    
    # 状态
    status = Column(String(32), nullable=False, default="pending", index=True)
    progress = Column(Float, default=0.0)
    current_stage = Column(String(64), nullable=True)
    message = Column(Text, nullable=True)
    
    # 参数与结果（JSON字符串）
    params_json = Column(Text, nullable=True)           # 任务参数
    inputs_summary = Column(Text, nullable=True)        # 输入数据摘要（行数、列数、列名）
    outputs_summary = Column(Text, nullable=True)       # 输出结果摘要
    result_file_path = Column(String(512), nullable=True)  # 完整结果文件路径
    
    # 阶段进度（JSON字符串）
    stages_json = Column(Text, nullable=True)
    
    # 错误信息
    error_message = Column(Text, nullable=True)
    error_traceback = Column(Text, nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    started_at = Column(DateTime, nullable=True)
    paused_at = Column(DateTime, nullable=True)
    resumed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 性能指标
    duration_seconds = Column(Float, nullable=True)     # 总耗时（秒）
    
    # 索引
    __table_args__ = (
        Index('idx_task_type_status', 'task_type', 'status'),
        Index('idx_session_created', 'session_id', 'created_at'),
        Index('idx_category_created', 'task_category', 'created_at'),
    )


class TaskControl(TaskManagerBase):
    """任务控制状态（用于持久化控制请求）"""
    __tablename__ = "task_controls"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    execution_id = Column(String(64), unique=True, nullable=False, index=True)
    action = Column(String(32), nullable=False, default="none")  # none, pause, stop, resume
    requested_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
```

### 4.3 数据库表结构

#### task_records 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 自增主键 |
| record_id | VARCHAR(64) | 记录UUID（唯一索引） |
| task_type | VARCHAR(64) | 任务类型（索引） |
| task_category | VARCHAR(32) | 任务类别 |
| execution_id | VARCHAR(64) | 执行ID（索引） |
| session_id | VARCHAR(64) | 会话ID（索引） |
| status | VARCHAR(32) | 状态（索引） |
| progress | FLOAT | 进度（0-100） |
| current_stage | VARCHAR(64) | 当前阶段 |
| message | TEXT | 状态消息 |
| params_json | TEXT | 参数JSON |
| inputs_summary | TEXT | 输入摘要JSON |
| outputs_summary | TEXT | 输出摘要JSON |
| result_file_path | VARCHAR(512) | 结果文件路径 |
| stages_json | TEXT | 阶段进度JSON |
| error_message | TEXT | 错误消息 |
| error_traceback | TEXT | 错误堆栈 |
| created_at | DATETIME | 创建时间（索引） |
| started_at | DATETIME | 开始时间 |
| paused_at | DATETIME | 暂停时间 |
| resumed_at | DATETIME | 恢复时间 |
| completed_at | DATETIME | 完成时间 |
| updated_at | DATETIME | 更新时间 |
| duration_seconds | FLOAT | 总耗时 |

#### task_controls 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 自增主键 |
| execution_id | VARCHAR(64) | 执行ID（唯一索引） |
| action | VARCHAR(32) | 控制动作 |
| requested_at | DATETIME | 请求时间 |
| processed_at | DATETIME | 处理时间 |

---

## 5. 核心组件设计

### 5.1 TaskManagerDB

```python
# database.py

from typing import Generator, Optional
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session
from .models import TaskManagerBase

class TaskManagerDB:
    """任务管理数据库
    
    复用 llm_manager_integrated 的 DatabaseManager 模式
    """
    
    def __init__(self, database_url: str = "sqlite:///./task_manager.db"):
        self.database_url = database_url
        self.engine = self._create_engine(database_url)
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
    
    def _create_engine(self, database_url: str) -> Engine:
        connect_args = {}
        if "sqlite" in database_url:
            connect_args = {"check_same_thread": False}
        
        return create_engine(
            database_url,
            connect_args=connect_args,
            pool_pre_ping=True,
        )
    
    def get_session(self) -> Generator[Session, None, None]:
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    def create_tables(self):
        TaskManagerBase.metadata.create_all(bind=self.engine)
    
    def close(self):
        self.engine.dispose()


# 全局实例
_task_manager_db: Optional[TaskManagerDB] = None

def get_task_manager_db(database_url: Optional[str] = None) -> TaskManagerDB:
    global _task_manager_db
    if database_url:
        return TaskManagerDB(database_url)
    if _task_manager_db is None:
        _task_manager_db = TaskManagerDB()
        _task_manager_db.create_tables()
    return _task_manager_db
```

### 5.2 TaskController

```python
# controller.py

import threading
from datetime import datetime
from typing import Dict, Optional
from .enums import TaskControlAction, TaskStatus
from .database import get_task_manager_db
from .models import TaskControl

class TaskController:
    """任务控制器
    
    提供任务的暂停、停止、恢复控制。
    使用内存缓存 + 数据库持久化双层存储。
    """
    
    # 内存缓存（快速响应）
    _control_cache: Dict[str, TaskControlAction] = {}
    _lock = threading.Lock()
    
    @classmethod
    def request_pause(cls, execution_id: str) -> bool:
        """请求暂停任务"""
        return cls._set_control(execution_id, TaskControlAction.PAUSE)
    
    @classmethod
    def request_stop(cls, execution_id: str) -> bool:
        """请求停止任务"""
        return cls._set_control(execution_id, TaskControlAction.STOP)
    
    @classmethod
    def request_resume(cls, execution_id: str) -> bool:
        """请求恢复任务"""
        return cls._set_control(execution_id, TaskControlAction.RESUME)
    
    @classmethod
    def check_control(cls, execution_id: str) -> TaskControlAction:
        """检查控制状态（执行器在检查点调用）"""
        with cls._lock:
            # 优先从缓存读取
            if execution_id in cls._control_cache:
                return cls._control_cache[execution_id]
        
        # 回退到数据库
        return cls._get_control_from_db(execution_id)
    
    @classmethod
    def clear_control(cls, execution_id: str) -> None:
        """清除控制状态（任务完成后调用）"""
        with cls._lock:
            cls._control_cache.pop(execution_id, None)
        cls._delete_control_from_db(execution_id)
    
    @classmethod
    def mark_processed(cls, execution_id: str) -> None:
        """标记控制请求已处理"""
        with cls._lock:
            cls._control_cache[execution_id] = TaskControlAction.NONE
        cls._update_control_processed(execution_id)
    
    # =========== 私有方法 ===========
    
    @classmethod
    def _set_control(cls, execution_id: str, action: TaskControlAction) -> bool:
        """设置控制状态"""
        with cls._lock:
            cls._control_cache[execution_id] = action
        return cls._save_control_to_db(execution_id, action)
    
    @classmethod
    def _save_control_to_db(cls, execution_id: str, action: TaskControlAction) -> bool:
        """保存控制状态到数据库"""
        db = get_task_manager_db()
        with next(db.get_session()) as session:
            control = session.query(TaskControl).filter_by(execution_id=execution_id).first()
            if control:
                control.action = action.value
                control.requested_at = datetime.utcnow()
                control.processed_at = None
            else:
                control = TaskControl(
                    execution_id=execution_id,
                    action=action.value
                )
                session.add(control)
            session.commit()
            return True
    
    @classmethod
    def _get_control_from_db(cls, execution_id: str) -> TaskControlAction:
        """从数据库读取控制状态"""
        db = get_task_manager_db()
        with next(db.get_session()) as session:
            control = session.query(TaskControl).filter_by(execution_id=execution_id).first()
            if control and control.processed_at is None:
                return TaskControlAction(control.action)
        return TaskControlAction.NONE
    
    @classmethod
    def _delete_control_from_db(cls, execution_id: str) -> None:
        """从数据库删除控制状态"""
        db = get_task_manager_db()
        with next(db.get_session()) as session:
            session.query(TaskControl).filter_by(execution_id=execution_id).delete()
            session.commit()
    
    @classmethod
    def _update_control_processed(cls, execution_id: str) -> None:
        """更新控制请求为已处理"""
        db = get_task_manager_db()
        with next(db.get_session()) as session:
            control = session.query(TaskControl).filter_by(execution_id=execution_id).first()
            if control:
                control.processed_at = datetime.utcnow()
                session.commit()
```

### 5.3 TaskHistoryService

```python
# history_service.py

import json
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy import desc, and_
from .database import get_task_manager_db
from .models import TaskRecord
from .enums import TaskStatus, TaskCategory

class TaskHistoryService:
    """任务历史查询服务"""
    
    @classmethod
    def create_record(
        cls,
        task_type: str,
        execution_id: str,
        session_id: str,
        params: Dict[str, Any],
        task_category: str = "sop",
        inputs_summary: Optional[Dict[str, Any]] = None
    ) -> str:
        """创建任务记录，返回record_id"""
        record_id = f"rec-{uuid.uuid4().hex[:12]}"
        
        db = get_task_manager_db()
        with next(db.get_session()) as session:
            record = TaskRecord(
                record_id=record_id,
                task_type=task_type,
                task_category=task_category,
                execution_id=execution_id,
                session_id=session_id,
                status=TaskStatus.PENDING.value,
                params_json=json.dumps(params, ensure_ascii=False),
                inputs_summary=json.dumps(inputs_summary, ensure_ascii=False) if inputs_summary else None
            )
            session.add(record)
            session.commit()
        
        return record_id
    
    @classmethod
    def update_status(
        cls,
        record_id: str,
        status: TaskStatus,
        progress: float = None,
        current_stage: str = None,
        message: str = None,
        stages: Dict[str, Any] = None
    ) -> bool:
        """更新任务状态"""
        db = get_task_manager_db()
        with next(db.get_session()) as session:
            record = session.query(TaskRecord).filter_by(record_id=record_id).first()
            if not record:
                return False
            
            record.status = status.value
            record.updated_at = datetime.utcnow()
            
            if progress is not None:
                record.progress = progress
            if current_stage is not None:
                record.current_stage = current_stage
            if message is not None:
                record.message = message
            if stages is not None:
                record.stages_json = json.dumps(stages, ensure_ascii=False)
            
            # 更新时间戳
            if status == TaskStatus.RUNNING and record.started_at is None:
                record.started_at = datetime.utcnow()
            elif status == TaskStatus.PAUSED:
                record.paused_at = datetime.utcnow()
            elif status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.STOPPED):
                record.completed_at = datetime.utcnow()
                if record.started_at:
                    record.duration_seconds = (record.completed_at - record.started_at).total_seconds()
            
            session.commit()
            return True
    
    @classmethod
    def update_result(
        cls,
        record_id: str,
        outputs_summary: Dict[str, Any],
        result_file_path: str = None
    ) -> bool:
        """更新任务结果"""
        db = get_task_manager_db()
        with next(db.get_session()) as session:
            record = session.query(TaskRecord).filter_by(record_id=record_id).first()
            if not record:
                return False
            
            record.outputs_summary = json.dumps(outputs_summary, ensure_ascii=False)
            if result_file_path:
                record.result_file_path = result_file_path
            record.updated_at = datetime.utcnow()
            
            session.commit()
            return True
    
    @classmethod
    def update_error(
        cls,
        record_id: str,
        error_message: str,
        error_traceback: str = None
    ) -> bool:
        """更新错误信息"""
        db = get_task_manager_db()
        with next(db.get_session()) as session:
            record = session.query(TaskRecord).filter_by(record_id=record_id).first()
            if not record:
                return False
            
            record.status = TaskStatus.FAILED.value
            record.error_message = error_message
            record.error_traceback = error_traceback
            record.completed_at = datetime.utcnow()
            record.updated_at = datetime.utcnow()
            
            if record.started_at:
                record.duration_seconds = (record.completed_at - record.started_at).total_seconds()
            
            session.commit()
            return True
    
    @classmethod
    def get_record(cls, record_id: str) -> Optional[Dict[str, Any]]:
        """获取单条记录"""
        db = get_task_manager_db()
        with next(db.get_session()) as session:
            record = session.query(TaskRecord).filter_by(record_id=record_id).first()
            if not record:
                return None
            return cls._record_to_dict(record)
    
    @classmethod
    def get_record_by_execution_id(cls, execution_id: str) -> Optional[Dict[str, Any]]:
        """通过execution_id获取记录"""
        db = get_task_manager_db()
        with next(db.get_session()) as session:
            record = session.query(TaskRecord).filter_by(execution_id=execution_id).first()
            if not record:
                return None
            return cls._record_to_dict(record)
    
    @classmethod
    def list_records(
        cls,
        task_type: Optional[str] = None,
        task_category: Optional[str] = None,
        session_id: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """列表查询"""
        db = get_task_manager_db()
        with next(db.get_session()) as session:
            query = session.query(TaskRecord)
            
            # 构建筛选条件
            conditions = []
            if task_type:
                conditions.append(TaskRecord.task_type == task_type)
            if task_category:
                conditions.append(TaskRecord.task_category == task_category)
            if session_id:
                conditions.append(TaskRecord.session_id == session_id)
            if status:
                conditions.append(TaskRecord.status == status)
            if start_date:
                conditions.append(TaskRecord.created_at >= start_date)
            if end_date:
                conditions.append(TaskRecord.created_at <= end_date)
            
            if conditions:
                query = query.filter(and_(*conditions))
            
            # 排序和分页
            query = query.order_by(desc(TaskRecord.created_at))
            query = query.offset(offset).limit(limit)
            
            records = query.all()
            return [cls._record_to_dict(r) for r in records]
    
    @classmethod
    def delete_record(cls, record_id: str) -> bool:
        """删除记录"""
        db = get_task_manager_db()
        with next(db.get_session()) as session:
            result = session.query(TaskRecord).filter_by(record_id=record_id).delete()
            session.commit()
            return result > 0
    
    @classmethod
    def get_statistics(
        cls,
        task_type: Optional[str] = None,
        task_category: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """获取统计信息"""
        db = get_task_manager_db()
        with next(db.get_session()) as session:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            query = session.query(TaskRecord).filter(TaskRecord.created_at >= start_date)
            
            if task_type:
                query = query.filter(TaskRecord.task_type == task_type)
            if task_category:
                query = query.filter(TaskRecord.task_category == task_category)
            
            records = query.all()
            
            total = len(records)
            completed = sum(1 for r in records if r.status == TaskStatus.COMPLETED.value)
            failed = sum(1 for r in records if r.status == TaskStatus.FAILED.value)
            stopped = sum(1 for r in records if r.status == TaskStatus.STOPPED.value)
            running = sum(1 for r in records if r.status == TaskStatus.RUNNING.value)
            
            durations = [r.duration_seconds for r in records if r.duration_seconds]
            avg_duration = sum(durations) / len(durations) if durations else 0
            
            return {
                "total": total,
                "completed": completed,
                "failed": failed,
                "stopped": stopped,
                "running": running,
                "success_rate": completed / total if total > 0 else 0,
                "avg_duration_seconds": avg_duration,
                "period_days": days
            }
    
    @classmethod
    def cleanup_old(cls, days: int = 90) -> int:
        """清理过期记录"""
        db = get_task_manager_db()
        with next(db.get_session()) as session:
            cutoff = datetime.utcnow() - timedelta(days=days)
            result = session.query(TaskRecord).filter(TaskRecord.created_at < cutoff).delete()
            session.commit()
            return result
    
    @staticmethod
    def _record_to_dict(record: TaskRecord) -> Dict[str, Any]:
        """将ORM对象转换为字典"""
        return {
            "record_id": record.record_id,
            "task_type": record.task_type,
            "task_category": record.task_category,
            "execution_id": record.execution_id,
            "session_id": record.session_id,
            "status": record.status,
            "progress": record.progress,
            "current_stage": record.current_stage,
            "message": record.message,
            "params": json.loads(record.params_json) if record.params_json else None,
            "inputs_summary": json.loads(record.inputs_summary) if record.inputs_summary else None,
            "outputs_summary": json.loads(record.outputs_summary) if record.outputs_summary else None,
            "result_file_path": record.result_file_path,
            "stages": json.loads(record.stages_json) if record.stages_json else None,
            "error_message": record.error_message,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "started_at": record.started_at.isoformat() if record.started_at else None,
            "paused_at": record.paused_at.isoformat() if record.paused_at else None,
            "completed_at": record.completed_at.isoformat() if record.completed_at else None,
            "duration_seconds": record.duration_seconds
        }
```

### 5.4 TaskResultStorage

```python
# result_storage.py

import json
import pickle
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class TaskResultStorage:
    """任务结果文件存储
    
    将完整的任务执行结果保存到文件系统。
    支持JSON（可序列化数据）和Pickle（DataFrame等复杂对象）。
    """
    
    def __init__(self, base_dir: str = "./task_results"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def save_result(
        self,
        record_id: str,
        result: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """保存完整结果
        
        Args:
            record_id: 记录ID
            result: 结果字典
            metadata: 元数据
            
        Returns:
            结果目录路径
        """
        result_dir = self.base_dir / record_id
        result_dir.mkdir(parents=True, exist_ok=True)
        
        # 分离可JSON序列化的数据和复杂对象
        json_result = {}
        pickle_result = {}
        
        for key, value in result.items():
            if self._is_json_serializable(value):
                json_result[key] = value
            else:
                pickle_result[key] = value
        
        # 保存JSON结果
        if json_result:
            json_path = result_dir / "result.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(json_result, f, ensure_ascii=False, indent=2, default=str)
        
        # 保存Pickle结果（DataFrame等）
        if pickle_result:
            pickle_path = result_dir / "outputs.pkl"
            with open(pickle_path, "wb") as f:
                pickle.dump(pickle_result, f)
        
        # 保存元数据
        if metadata:
            meta_path = result_dir / "metadata.json"
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"Saved result for {record_id} to {result_dir}")
        return str(result_dir)
    
    def load_result(self, record_id: str) -> Optional[Dict[str, Any]]:
        """加载完整结果"""
        result_dir = self.base_dir / record_id
        if not result_dir.exists():
            return None
        
        result = {}
        
        # 加载JSON结果
        json_path = result_dir / "result.json"
        if json_path.exists():
            with open(json_path, "r", encoding="utf-8") as f:
                result.update(json.load(f))
        
        # 加载Pickle结果
        pickle_path = result_dir / "outputs.pkl"
        if pickle_path.exists():
            with open(pickle_path, "rb") as f:
                result.update(pickle.load(f))
        
        return result if result else None
    
    def load_metadata(self, record_id: str) -> Optional[Dict[str, Any]]:
        """加载元数据"""
        meta_path = self.base_dir / record_id / "metadata.json"
        if not meta_path.exists():
            return None
        
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def delete_result(self, record_id: str) -> bool:
        """删除结果"""
        result_dir = self.base_dir / record_id
        if result_dir.exists():
            shutil.rmtree(result_dir)
            logger.info(f"Deleted result for {record_id}")
            return True
        return False
    
    def cleanup_old(self, days: int = 90) -> int:
        """清理过期结果
        
        Args:
            days: 保留天数
            
        Returns:
            清理的记录数
        """
        cutoff = datetime.now() - timedelta(days=days)
        cleaned = 0
        
        for result_dir in self.base_dir.iterdir():
            if result_dir.is_dir():
                # 检查元数据中的创建时间
                meta_path = result_dir / "metadata.json"
                if meta_path.exists():
                    with open(meta_path, "r") as f:
                        metadata = json.load(f)
                        created_at = metadata.get("created_at")
                        if created_at:
                            created_time = datetime.fromisoformat(created_at)
                            if created_time < cutoff:
                                shutil.rmtree(result_dir)
                                cleaned += 1
                                continue
                
                # 回退：检查目录修改时间
                mtime = datetime.fromtimestamp(result_dir.stat().st_mtime)
                if mtime < cutoff:
                    shutil.rmtree(result_dir)
                    cleaned += 1
        
        logger.info(f"Cleaned up {cleaned} old results")
        return cleaned
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """获取存储统计"""
        total_size = 0
        total_count = 0
        
        for result_dir in self.base_dir.iterdir():
            if result_dir.is_dir():
                total_count += 1
                for file in result_dir.rglob("*"):
                    if file.is_file():
                        total_size += file.stat().st_size
        
        return {
            "total_records": total_count,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "base_dir": str(self.base_dir)
        }
    
    @staticmethod
    def _is_json_serializable(value: Any) -> bool:
        """检查值是否可JSON序列化"""
        try:
            json.dumps(value)
            return True
        except (TypeError, ValueError):
            return False


# 全局实例
_result_storage: Optional[TaskResultStorage] = None

def get_result_storage(base_dir: str = "./task_results") -> TaskResultStorage:
    global _result_storage
    if _result_storage is None:
        _result_storage = TaskResultStorage(base_dir)
    return _result_storage
```

### 5.5 检查点机制

```python
# checkpoint.py

import asyncio
import logging
from typing import Optional, Callable, Any
from .controller import TaskController
from .enums import TaskControlAction, TaskStatus
from .history_service import TaskHistoryService

logger = logging.getLogger(__name__)


class CheckpointMixin:
    """检查点混入类
    
    为执行器提供检查点功能，支持在阶段之间检查控制状态。
    """
    
    async def check_control_point(
        self,
        execution_id: str,
        record_id: str,
        stage_id: str,
        save_state_callback: Optional[Callable[[], dict]] = None
    ) -> bool:
        """检查控制点
        
        在每个阶段开始前调用，检查是否需要暂停或停止。
        
        Args:
            execution_id: 执行ID
            record_id: 记录ID
            stage_id: 当前阶段ID
            save_state_callback: 保存状态的回调函数
            
        Returns:
            True: 继续执行
            False: 任务已停止
            
        Raises:
            TaskPausedException: 任务已暂停，等待恢复
        """
        control = TaskController.check_control(execution_id)
        
        if control == TaskControlAction.STOP:
            logger.info(f"Task {execution_id} stop requested at stage {stage_id}")
            
            # 更新状态为已停止
            TaskHistoryService.update_status(
                record_id=record_id,
                status=TaskStatus.STOPPED,
                message=f"用户在阶段 {stage_id} 停止了任务"
            )
            
            # 清除控制状态
            TaskController.clear_control(execution_id)
            
            return False
        
        if control == TaskControlAction.PAUSE:
            logger.info(f"Task {execution_id} pause requested at stage {stage_id}")
            
            # 保存当前状态
            if save_state_callback:
                state = save_state_callback()
                # ✅ 已实现：通过 PersistentExecutionStore.save_full_state() 保存状态到文件系统
            
            # 更新状态为已暂停
            TaskHistoryService.update_status(
                record_id=record_id,
                status=TaskStatus.PAUSED,
                message=f"任务在阶段 {stage_id} 暂停"
            )
            
            # 标记控制请求已处理
            TaskController.mark_processed(execution_id)
            
            # 等待恢复
            await self._wait_for_resume(execution_id, record_id)
            
            return True
        
        return True
    
    async def _wait_for_resume(
        self,
        execution_id: str,
        record_id: str,
        check_interval: float = 1.0,
        timeout: float = 3600.0  # 1小时超时
    ) -> None:
        """等待恢复
        
        Args:
            execution_id: 执行ID
            record_id: 记录ID
            check_interval: 检查间隔（秒）
            timeout: 超时时间（秒）
        """
        elapsed = 0.0
        
        while elapsed < timeout:
            control = TaskController.check_control(execution_id)
            
            if control == TaskControlAction.RESUME:
                logger.info(f"Task {execution_id} resumed")
                
                # 更新状态为运行中
                TaskHistoryService.update_status(
                    record_id=record_id,
                    status=TaskStatus.RUNNING,
                    message="任务已恢复"
                )
                
                # 清除控制状态
                TaskController.mark_processed(execution_id)
                return
            
            if control == TaskControlAction.STOP:
                logger.info(f"Task {execution_id} stopped while paused")
                raise TaskStoppedException("Task stopped while paused")
            
            await asyncio.sleep(check_interval)
            elapsed += check_interval
        
        # 超时，自动恢复
        logger.warning(f"Task {execution_id} pause timeout, auto-resuming")
        TaskHistoryService.update_status(
            record_id=record_id,
            status=TaskStatus.RUNNING,
            message="暂停超时，自动恢复"
        )


class TaskPausedException(Exception):
    """任务暂停异常"""
    pass


class TaskStoppedException(Exception):
    """任务停止异常"""
    pass
```

---

## 6. API接口设计

### 6.1 任务控制接口

#### 6.1.1 暂停任务

```
POST /sop/executions/{execution_id}/pause
```

**请求参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| execution_id | string | 是 | 执行ID |

**响应**：
```json
{
    "success": true,
    "message": "暂停请求已发送，任务将在当前阶段完成后暂停",
    "execution_id": "exec-abc123",
    "current_status": "running"
}
```

**错误响应**：
```json
{
    "success": false,
    "error": "任务不存在或已完成",
    "execution_id": "exec-abc123"
}
```

#### 6.1.2 停止任务

```
POST /sop/executions/{execution_id}/stop
```

**请求参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| execution_id | string | 是 | 执行ID |

**响应**：
```json
{
    "success": true,
    "message": "停止请求已发送，任务将在当前阶段完成后停止",
    "execution_id": "exec-abc123",
    "current_status": "running"
}
```

#### 6.1.3 恢复任务

```
POST /sop/executions/{execution_id}/resume
```

**请求参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| execution_id | string | 是 | 执行ID |

**响应**：
```json
{
    "success": true,
    "message": "恢复请求已发送",
    "execution_id": "exec-abc123",
    "current_status": "paused"
}
```

### 6.2 历史查询接口

#### 6.2.1 查询历史记录列表

```
GET /sop/history
```

**查询参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| task_type | string | 否 | 任务类型（rule_mining, scorecard_dev） |
| task_category | string | 否 | 任务类别（sop, inference） |
| session_id | string | 否 | 会话ID |
| status | string | 否 | 状态（completed, failed, stopped） |
| start_date | string | 否 | 开始日期（ISO格式） |
| end_date | string | 否 | 结束日期（ISO格式） |
| limit | int | 否 | 每页数量（默认50） |
| offset | int | 否 | 偏移量（默认0） |

**响应**：
```json
{
    "total": 100,
    "limit": 50,
    "offset": 0,
    "records": [
        {
            "record_id": "rec-abc123",
            "task_type": "scorecard_dev",
            "task_category": "sop",
            "execution_id": "exec-xyz789",
            "status": "completed",
            "progress": 100.0,
            "message": "任务执行完成",
            "created_at": "2024-01-15T10:30:00",
            "completed_at": "2024-01-15T10:35:00",
            "duration_seconds": 300.5
        }
    ]
}
```

#### 6.2.2 获取历史记录详情

```
GET /sop/history/{record_id}
```

**响应**：
```json
{
    "record_id": "rec-abc123",
    "task_type": "scorecard_dev",
    "task_category": "sop",
    "execution_id": "exec-xyz789",
    "session_id": "session-123",
    "status": "completed",
    "progress": 100.0,
    "current_stage": "scorecard_generation",
    "message": "任务执行完成",
    "params": {
        "target_col": "label",
        "test_ratio": 0.3,
        "iv_lower": 0.02
    },
    "inputs_summary": {
        "rows": 10000,
        "columns": 50,
        "column_names": ["col1", "col2", "..."]
    },
    "outputs_summary": {
        "selected_features": 12,
        "model_ks": 0.42,
        "model_auc": 0.78
    },
    "stages": {
        "data_preprocessing": {"status": "completed", "progress": 100},
        "woe_binning": {"status": "completed", "progress": 100}
    },
    "created_at": "2024-01-15T10:30:00",
    "started_at": "2024-01-15T10:30:05",
    "completed_at": "2024-01-15T10:35:00",
    "duration_seconds": 300.5
}
```

#### 6.2.3 获取历史任务完整结果

```
GET /sop/history/{record_id}/result
```

**响应**：
```json
{
    "record_id": "rec-abc123",
    "result": {
        "scorecard": {
            "type": "dict_of_dataframes",
            "data": {
                "feature1": {"columns": [...], "data": [...]},
                "feature2": {"columns": [...], "data": [...]}
            }
        },
        "model_metrics": {
            "type": "dict",
            "data": {
                "ks": 0.42,
                "auc": 0.78,
                "gini": 0.56
            }
        },
        "selected_features": {
            "type": "list",
            "data": ["feature1", "feature2", "feature3"]
        }
    }
}
```

#### 6.2.4 删除历史记录

```
DELETE /sop/history/{record_id}
```

**响应**：
```json
{
    "success": true,
    "message": "记录已删除",
    "record_id": "rec-abc123"
}
```

### 6.3 统计接口

#### 6.3.1 获取任务统计信息

```
GET /sop/statistics
```

**查询参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| task_type | string | 否 | 任务类型 |
| task_category | string | 否 | 任务类别 |
| days | int | 否 | 统计天数（默认30） |

**响应**：
```json
{
    "total": 150,
    "completed": 120,
    "failed": 20,
    "stopped": 5,
    "running": 5,
    "success_rate": 0.8,
    "avg_duration_seconds": 245.5,
    "period_days": 30
}
```

---

## 7. 集成方案

### 7.1 与 executor.py 的集成

#### 7.1.1 扩展 ExecutionContext

```python
# 在 ExecutionContext 中添加字段
@dataclass
class ExecutionContext:
    # ... 现有字段 ...
    
    # 新增字段
    record_id: str | None = None  # 关联的持久化记录ID
    control_state: str = "none"   # 控制状态
```

#### 7.1.2 扩展 ExecutionStore

```python
# 创建 PersistentExecutionStore 包装类
class PersistentExecutionStore:
    """持久化执行存储
    
    在 ExecutionStore 基础上增加持久化层。
    """
    
    @classmethod
    def create(cls, ...) -> ExecutionContext:
        # 1. 调用原 ExecutionStore.create()
        context = ExecutionStore.create(...)
        
        # 2. 创建持久化记录
        record_id = TaskHistoryService.create_record(
            task_type=task_id,
            execution_id=context.execution_id,
            session_id=session_id,
            params=params,
            inputs_summary=cls._create_inputs_summary(data)
        )
        context.record_id = record_id
        
        return context
    
    @classmethod
    def update(cls, context: ExecutionContext) -> None:
        # 1. 更新内存存储
        ExecutionStore.update(context)
        
        # 2. 同步到数据库
        if context.record_id:
            TaskHistoryService.update_status(
                record_id=context.record_id,
                status=TaskStatus(context.status.value),
                progress=context.overall_progress,
                current_stage=context.current_stage,
                message=context.message,
                stages=cls._stages_to_dict(context.stages)
            )
```

#### 7.1.3 修改 SOPExecutor

```python
class SOPExecutor(CheckpointMixin):
    """增加检查点支持"""
    
    async def _run_task_with_checkpoints(self, context: ExecutionContext) -> None:
        """带检查点的任务执行"""
        
        task_def = self.registry.get_task(context.task_id)
        
        for stage in task_def.stages:
            # 检查控制点
            should_continue = await self.check_control_point(
                execution_id=context.execution_id,
                record_id=context.record_id,
                stage_id=stage.id
            )
            
            if not should_continue:
                # 任务已停止
                return
            
            # 执行阶段
            await self._execute_stage(stage, context)
```

### 7.2 与 sop_api.py 的集成

```python
# 在 sop_api.py 中添加新路由

from deepanalyze.core.task_manager import (
    TaskController,
    TaskHistoryService,
    get_result_storage
)

# ========== 任务控制 ==========

@router.post("/executions/{execution_id}/pause")
async def pause_execution(execution_id: str):
    """暂停任务"""
    context = ExecutionStore.get(execution_id)
    if not context:
        raise HTTPException(404, "执行不存在")
    
    if context.status != ExecutionStatus.RUNNING:
        raise HTTPException(400, "只能暂停运行中的任务")
    
    TaskController.request_pause(execution_id)
    
    return {
        "success": True,
        "message": "暂停请求已发送",
        "execution_id": execution_id
    }


@router.post("/executions/{execution_id}/stop")
async def stop_execution(execution_id: str):
    """停止任务"""
    context = ExecutionStore.get(execution_id)
    if not context:
        raise HTTPException(404, "执行不存在")
    
    if context.status not in (ExecutionStatus.RUNNING, ExecutionStatus.PENDING):
        raise HTTPException(400, "只能停止运行中或等待中的任务")
    
    TaskController.request_stop(execution_id)
    
    return {
        "success": True,
        "message": "停止请求已发送",
        "execution_id": execution_id
    }


@router.post("/executions/{execution_id}/resume")
async def resume_execution(execution_id: str):
    """恢复任务"""
    context = ExecutionStore.get(execution_id)
    if not context:
        raise HTTPException(404, "执行不存在")
    
    # 检查是否处于暂停状态
    record = TaskHistoryService.get_record_by_execution_id(execution_id)
    if not record or record["status"] != "paused":
        raise HTTPException(400, "只能恢复已暂停的任务")
    
    TaskController.request_resume(execution_id)
    
    return {
        "success": True,
        "message": "恢复请求已发送",
        "execution_id": execution_id
    }


# ========== 历史查询 ==========

@router.get("/history")
async def list_task_history(
    task_type: str = None,
    task_category: str = None,
    session_id: str = None,
    status: str = None,
    start_date: str = None,
    end_date: str = None,
    limit: int = 50,
    offset: int = 0
):
    """查询历史记录"""
    records = TaskHistoryService.list_records(
        task_type=task_type,
        task_category=task_category,
        session_id=session_id,
        status=status,
        start_date=datetime.fromisoformat(start_date) if start_date else None,
        end_date=datetime.fromisoformat(end_date) if end_date else None,
        limit=limit,
        offset=offset
    )
    
    # ✅ 已实现：通过 count_records() 获取真正的总数
    total = TaskHistoryService.count_records(
        task_type=task_type,
        task_category=task_category,
        session_id=session_id,
        status=status,
        start_date=start_dt,
        end_date=end_dt
    )
    
    return {
        "total": total,  # 真正的总数（而非 len(records)）
        "limit": limit,
        "offset": offset,
        "records": records
    }


@router.get("/history/{record_id}")
async def get_task_history_detail(record_id: str):
    """获取历史记录详情"""
    record = TaskHistoryService.get_record(record_id)
    if not record:
        raise HTTPException(404, "记录不存在")
    return record


@router.get("/history/{record_id}/result")
async def get_task_history_result(record_id: str):
    """获取历史任务完整结果"""
    record = TaskHistoryService.get_record(record_id)
    if not record:
        raise HTTPException(404, "记录不存在")
    
    storage = get_result_storage()
    result = storage.load_result(record_id)
    
    if not result:
        raise HTTPException(404, "结果文件不存在")
    
    return {
        "record_id": record_id,
        "result": result
    }


@router.delete("/history/{record_id}")
async def delete_task_history(record_id: str):
    """删除历史记录"""
    # 删除数据库记录
    success = TaskHistoryService.delete_record(record_id)
    if not success:
        raise HTTPException(404, "记录不存在")
    
    # 删除结果文件
    storage = get_result_storage()
    storage.delete_result(record_id)
    
    return {
        "success": True,
        "message": "记录已删除",
        "record_id": record_id
    }


# ========== 统计 ==========

@router.get("/statistics")
async def get_task_statistics(
    task_type: str = None,
    task_category: str = None,
    days: int = 30
):
    """获取任务统计信息"""
    return TaskHistoryService.get_statistics(
        task_type=task_type,
        task_category=task_category,
        days=days
    )
```

---

## 8. 实施计划

### 8.1 阶段划分

| 阶段 | 名称 | 周期 | 说明 |
|------|------|------|------|
| Phase 1 | 基础设施 | 1周 | 数据库、ORM模型、基础服务 |
| Phase 2 | 任务记录管理 | 1周 | 历史服务、结果存储、持久化存储 |
| Phase 3 | 任务控制 | 1周 | 控制器、检查点、暂停/恢复逻辑 |
| Phase 4 | API接口 | 0.5周 | 控制接口、历史接口、统计接口 |
| Phase 5 | 测试与文档 | 0.5周 | 单元测试、集成测试、API文档 |

**总计：约4周**

### 8.2 详细任务

#### Phase 1：基础设施（1周）

| 任务ID | 任务 | 说明 | 工作量 |
|--------|------|------|--------|
| 1.1 | 创建模块目录结构 | `deepanalyze/core/task_manager/` | 小 |
| 1.2 | 实现 TaskManagerDB | 复用 DatabaseManager 模式 | 小 |
| 1.3 | 定义枚举类型 | TaskStatus, TaskControlAction, TaskCategory | 小 |
| 1.4 | 设计 TaskRecord ORM | 任务记录模型 | 中 |
| 1.5 | 设计 TaskControl ORM | 控制状态模型 | 小 |
| 1.6 | 实现数据库初始化 | 创建表、索引 | 小 |

#### Phase 2：任务记录管理（1周）

| 任务ID | 任务 | 说明 | 工作量 |
|--------|------|------|--------|
| 2.1 | 实现 TaskHistoryService.create_record | 创建记录 | 小 |
| 2.2 | 实现 TaskHistoryService.update_* | 更新状态、结果、错误 | 中 |
| 2.3 | 实现 TaskHistoryService.list_records | 列表查询 | 中 |
| 2.4 | 实现 TaskHistoryService.get_statistics | 统计信息 | 小 |
| 2.5 | 实现 TaskResultStorage | 结果文件存储 | 中 |
| 2.6 | 实现 PersistentExecutionStore | 持久化存储包装 | 中 |
| 2.7 | 与 ExecutionStore 集成 | 修改 executor.py | 中 |

#### Phase 3：任务控制（1周）

| 任务ID | 任务 | 说明 | 工作量 |
|--------|------|------|--------|
| 3.1 | 实现 TaskController | 暂停/停止/恢复控制 | 中 |
| 3.2 | 实现 CheckpointMixin | 检查点机制 | 中 |
| 3.3 | 实现 _wait_for_resume | 暂停等待逻辑 | 中 |
| 3.4 | 修改 SOPExecutor._run_task | 增加检查点调用 | 大 |
| 3.5 | 扩展 ExecutionContext | 增加 record_id, control_state | 小 |
| 3.6 | 异常处理 | TaskPausedException, TaskStoppedException | 小 |

#### Phase 4：API接口（0.5周）

| 任务ID | 任务 | 说明 | 工作量 |
|--------|------|------|--------|
| 4.1 | 实现暂停/停止/恢复接口 | POST /executions/{id}/pause|stop|resume | 中 |
| 4.2 | 实现历史查询接口 | GET /history, GET /history/{id} | 中 |
| 4.3 | 实现结果加载接口 | GET /history/{id}/result | 小 |
| 4.4 | 实现统计接口 | GET /statistics | 小 |
| 4.5 | 实现删除接口 | DELETE /history/{id} | 小 |

#### Phase 5：测试与文档（0.5周）

| 任务ID | 任务 | 说明 | 工作量 |
|--------|------|------|--------|
| 5.1 | 单元测试 | 各服务类测试 | 中 |
| 5.2 | 集成测试 | 完整流程测试 | 中 |
| 5.3 | API文档 | OpenAPI/Swagger | 小 |

### 8.3 里程碑

| 里程碑 | 完成时间 | 交付物 |
|--------|----------|--------|
| M1 | 第1周末 | 数据库就绪，ORM模型可用 |
| M2 | 第2周末 | 任务记录持久化完成，历史查询可用 |
| M3 | 第3周末 | 暂停/停止/恢复功能完成 |
| M4 | 第4周末 | API接口完成，测试通过 |

---

## 9. 验收标准

### 9.1 功能验收

#### 9.1.1 任务控制

- [x] 可以暂停正在执行的任务
- [x] 暂停后任务状态变为 `paused`
- [x] 可以恢复已暂停的任务
- [x] 恢复后任务从暂停点继续执行
- [x] 可以停止正在执行的任务
- [x] 停止后任务状态变为 `stopped`
- [x] 暂停/停止在当前阶段完成后生效（<5秒响应）

#### 9.1.2 记录管理

- [x] 任务开始时自动创建执行记录
- [x] 任务完成/失败/停止时记录状态正确更新
- [x] 任务参数、输入摘要、输出摘要正确保存
- [x] 完整结果正确保存到文件系统
- [x] 可以删除历史记录

#### 9.1.3 历史查询

- [x] 可以按任务类型筛选
- [x] 可以按状态筛选
- [x] 可以按时间范围筛选
- [x] 分页查询正常工作
- [x] 可以加载历史任务的完整结果
- [x] 统计信息正确

### 9.2 性能验收

- [x] 数据库写入 < 100ms
- [x] 1000条记录查询 < 500ms
- [x] 暂停/停止响应 < 5秒
- [x] 结果文件保存/加载 < 1秒（10MB以内）

### 9.3 兼容性验收

- [x] 现有 Pipeline 模式正常工作
- [x] 现有 API 接口无回退
- [x] 不影响未使用任务管理功能的任务

### 9.4 Phase 5 实施说明（2025-01-07 更新）

**Phase 5（测试与文档）已完成**，包括：

1. **测试脚本**（`tests/` 目录）：
   - `test_task_manager_complete.py`: 任务管理模块完整测试（38.56 KB）
   - `test_sop_api.py`: SOP API 接口测试（14.62 KB）
   - `test_resume_functionality.py`: 恢复功能测试（12.75 KB）
   - `test_resume_integration.py`: 恢复集成测试（15.96 KB）
   - `test_resume_expert_mode.py`: 专家模式恢复测试（9.18 KB）
   - `test_resume_bug.py`: 恢复 Bug 修复测试（8.31 KB）
   - `test_rule_mining.py`: 规则挖掘任务测试（29.62 KB）
   - `test_scorecard.py`: 评分卡开发任务测试（8.42 KB）
   - `test_frontend_api_integration.py`: 前端 API 集成测试（18.04 KB）
   - `test_llm_pipeline_integration.py`: LLM Pipeline 集成测试（29.7 KB）

2. **测试文档**（`docs/` 目录）：
   - `resume_test_guide.md`: 暂停/恢复功能测试指南
   - `resume_fix_test_report.md`: 恢复功能修复测试报告
   - `test_analysis_report.md`: 测试分析报告（19.34 KB）
   - `test_strategy_resume_functionality.md`: 任务Resume功能测试策略（原test_strategy_dual_tasks.md）

3. **API 文档**：
   - FastAPI 自动生成 OpenAPI/Swagger 文档（`/docs` 端点）
   - 所有接口包含完整的请求/响应模型定义

---

## 10. 附录

### 10.1 目录结构

```
deepanalyze/
├── core/
│   └── task_manager/
│       ├── __init__.py
│       ├── database.py
│       ├── models.py
│       ├── enums.py
│       ├── controller.py
│       ├── history_service.py
│       ├── result_storage.py
│       ├── persistent_store.py      # Phase 6
│       ├── recovery.py              # Phase 6
│       ├── stage_analysis_service.py # Phase 7
│       └── checkpoint.py
├── analysis/
│   └── task_SOP/
│       └── executor.py  # 修改
└── API/
    └── sop_api.py  # 修改
```

### 10.2 依赖

```
# requirements.txt 新增
sqlalchemy>=2.0.0
```

### 10.3 配置项

```python
# 可配置项
TASK_MANAGER_DB_URL = "sqlite:///./task_manager.db"  # 数据库URL
TASK_RESULT_DIR = "./task_results"                    # 结果存储目录
TASK_RESULT_RETENTION_DAYS = 90                       # 结果保留天数
TASK_PAUSE_TIMEOUT_SECONDS = 3600                     # 暂停超时时间
EXECUTION_STATE_DIR = "./execution_states"            # Phase 6: 执行状态存储目录
EXECUTION_STATE_RETENTION_DAYS = 3                    # Phase 6: 状态文件保留天数
```

### 10.4 通用性说明

本模块设计为通用任务管理模块，可复用至以下场景：

| 场景 | task_category | 说明 |
|------|---------------|------|
| SOP任务 | sop | 规则挖掘、评分卡开发等 |
| LLM推理 | inference | LLM推理任务记录 |
| 模型训练 | training | 模型训练任务 |
| 数据处理 | etl | ETL任务 |

使用示例：

```python
# 非SOP任务使用
record_id = TaskHistoryService.create_record(
    task_type="llm_inference",
    task_category="inference",
    execution_id="...",
    session_id="...",
    params={...}
)
```

---

## 13. 推理任务记录集成（Phase 8 - ✅ 已完成）

### 13.1 功能概述

将任务管理模块扩展到AI推理（对话）任务，实现通过 `chat_completions` 接口自动记录AI对话任务。

### 13.2 集成方案

#### 13.2.1 Chat API 集成

在 `API/chat_api.py` 中集成推理任务记录：

```python
# chat_api.py

from deepanalyze.core.task_manager import TaskHistoryService

def _create_inference_task_record(
    session_id: str,
    messages: List[Dict],
    model: str
) -> Optional[str]:
    """创建推理任务记录"""
    if not session_id:
        return None
    
    try:
        record_id = TaskHistoryService.create_record(
            task_type="inference",
            task_category="inference",
            execution_id=f"inf-{session_id[:8]}-{int(time.time())}",
            session_id=session_id,
            params={
                "model": model,
                "message_count": len(messages),
                "total_tokens": sum(msg.get("tokens", 0) for msg in messages)
            },
            inputs_summary={
                "message_preview": messages[-1]["content"][:100] if messages else "",
                "conversation_length": len(messages)
            }
        )
        return record_id
    except Exception as e:
        logger.error(f"Failed to create inference task record: {e}")
        return None


def _update_inference_task_status(
    record_id: str,
    status: str,
    outputs_summary: Optional[Dict] = None
) -> None:
    """更新推理任务状态"""
    if not record_id:
        return
    
    try:
        TaskHistoryService.update_status(
            record_id=record_id,
            status=TaskStatus[status.upper()],
        )
        
        if outputs_summary:
            TaskHistoryService.update_result(
                record_id=record_id,
                outputs_summary=outputs_summary
            )
    except Exception as e:
        logger.error(f"Failed to update inference task status: {e}")
```

#### 13.2.2 Streaming 模式集成

```python
async def _generate_stream_with_execution_async(
    request: ChatCompletionRequest,
    session_id: str,
    record_id: str
) -> AsyncGenerator:
    """流式生成（带任务记录）"""
    # 创建推理任务记录
    if not record_id:
        record_id = _create_inference_task_record(session_id, request.messages, request.model)
    
    if record_id:
        # 标记为运行中
        _update_inference_task_status(record_id, "running")
    
    try:
        # 执行流式推理...
        full_response = ""
        async for chunk in stream:
            full_response += chunk
            yield chunk
        
        # 任务完成
        if record_id:
            _update_inference_task_status(
                record_id,
                "completed",
                outputs_summary={
                    "response_preview": full_response[:200],
                    "response_length": len(full_response)
                }
            )
    except Exception as e:
        if record_id:
            _update_inference_task_status(record_id, "failed")
        raise
```

#### 13.2.3 Non-Streaming 模式集成

```python
def _non_streaming_with_execution(
    request: ChatCompletionRequest,
    session_id: str,
    record_id: str
) -> ChatCompletionResponse:
    """非流式生成（带任务记录）"""
    # 创建推理任务记录
    if not record_id:
        record_id = _create_inference_task_record(session_id, request.messages, request.model)
    
    if record_id:
        _update_inference_task_status(record_id, "running")
    
    try:
        # 执行推理...
        response = generate_response(request)
        
        # 任务完成
        if record_id:
            _update_inference_task_status(
                record_id,
                "completed",
                outputs_summary={
                    "response_preview": response.choices[0].message.content[:200],
                    "finish_reason": response.choices[0].finish_reason
                }
            )
        
        return response
    except Exception as e:
        if record_id:
            _update_inference_task_status(record_id, "failed")
        raise
```

### 13.3 前端适配

#### 13.3.1 任务类型标签映射

```typescript
// TaskHistoryCompact.tsx

const TASK_TYPE_LABELS = {
  scorecard_dev: "评分卡开发",
  rule_mining: "规则挖掘",
  inference: "AI对话",
  chat: "AI对话"
};

const TASK_TYPE_COLORS = {
  scorecard_dev: "blue",
  rule_mining: "purple",
  inference: "green",
  chat: "green"
};
```

#### 13.3.2 类别过滤

```typescript
// TaskHistoryList.tsx

const [categoryFilter, setCategoryFilter] = useState<string>("all");

// 类别筛选选项
const categoryOptions = [
  { value: "all", label: "全部" },
  { value: "sop", label: "SOP任务" },
  { value: "inference", label: "AI对话" }
];
```

### 13.4 验收标准

- [x] 通过 `chat_completions` 接口自动创建推理任务记录
- [x] 支持 streaming 和 non-streaming 两种模式
- [x] 正确记录任务参数（模型、消息数等）
- [x] 正确记录任务状态（running/completed/failed）
- [x] 在任务历史中正确显示推理任务
- [x] 支持按类别（SOP/inference）筛选任务
- [x] 推理任务记录不影响现有SOP任务功能

---

## 变更记录

| 版本 | 日期 | 作者 | 说明 |
|------|------|------|------|
| 1.7 | 2026-04-15 | AI Assistant | 新增待实施：删除历史记录时级联清理执行状态文件和关联数据（P3） |
| 1.6 | 2025-01-12 | AI Assistant | 新增 Phase 24：评估数据字段持久化修复（已完成），补充 `_full_stage_data` 机制说明 |
| 1.5 | 2025-01-07 | AI Assistant | 新增 Phase 8：推理任务记录集成（已完成） |
| 1.4 | 2025-01-07 | AI Assistant | 更新实施状态：Phase 5、6、7 全部已完成 |
| 1.3 | 2025-01-07 | AI Assistant | 更新实施状态：Phase 7 已完成，Phase 6 待开发 |
| 1.2 | 2025-01-XX | AI Assistant | 新增 Phase 6：执行状态持久化方案（待开发） |
| 1.1 | 2025-12-16 | AI Assistant | 更新实施状态：Phase 1-4 已完成 |
| 1.0 | 2024-XX-XX | - | 初始版本 |

---

## 实施状态

**当前状态**: ✅ 全部功能已完成（Phase 1-8, Phase 24）

| Phase | 内容 | 状态 |
|-------|------|------|
| Phase 1 | 基础设施（数据库、ORM模型） | ✅ 已完成 |
| Phase 2 | 任务记录管理（历史服务、结果存储） | ✅ 已完成 |
| Phase 3 | 任务控制（暂停/停止/恢复） | ✅ 已完成 |
| Phase 4 | API接口扩展 | ✅ 已完成 |
| Phase 5 | 测试与文档 | ✅ 已完成 |
| Phase 6 | 执行状态持久化（跨重启恢复） | ✅ 已完成 |
| Phase 7 | 阶段 AI 分析结果持久化 | ✅ 已完成 |
| Phase 8 | 推理任务记录集成（AI对话任务） | ✅ 已完成 |
| Phase 24 | 评估数据字段持久化修复 | ✅ 已完成 |
| **Phase 25** | **删除历史记录级联清理** | 📋 待实施（P3） |

### Phase 25：删除历史记录级联清理（待实施）

> **优先级**: P3 | **预计工作量**: ~0.5天 | **创建日期**: 2026-04-15

#### 现状问题

`DELETE /sop/history/{record_id}` 当前只清理了 2 项：
1. ✅ DB `task_records` 表记录（`TaskHistoryService.delete_record()`）
2. ✅ `task_results/{record_id}/` 目录（`storage.delete_result()`）

**遗漏项**（成为孤儿数据，无入口访问、只占磁盘/数据库空间）：

| 遗漏项 | 存储位置 | 内容 | 关联键 |
|--------|---------|------|--------|
| 执行状态文件 | `execution_states/{execution_id}/` | 各阶段 checkpoint pkl（DataFrame 快照等） | execution_id |
| DB 执行状态 | `execution_states` 表 | 执行上下文元数据 | execution_id |
| DB 检查点 | `execution_checkpoints` 表 | 阶段检查点记录 | execution_id |
| DB AI 分析 | `stage_ai_analyses` 表 | 阶段 AI 分析文本 | record_id |
| DB 整体分析 | `overall_ai_analyses` 表 | 任务整体 AI 分析 | record_id |

**根因**：`task_records` 表通过 `execution_id` 字段关联执行状态，但 `delete_task_history()` 未查询此关联做级联删除。

#### 优化方案

**后端**（`sop_api.py` `delete_task_history()`）：
```python
# 当前
TaskHistoryService.delete_record(record_id)
storage.delete_result(record_id)

# 优化后
record = TaskHistoryService.get_record(record_id)  # 先获取关联的 execution_id
execution_id = record.get("execution_id") if record else None

TaskHistoryService.delete_record(record_id)          # DB 记录
storage.delete_result(record_id)                     # 结果文件
if execution_id:
    PersistentExecutionStore.delete(execution_id)    # 执行状态 + 检查点 + 状态文件
StageAnalysisService.delete_all_by_record(record_id) # 所有阶段 AI 分析
OverallAnalysisService.delete_analysis(record_id)    # 整体 AI 分析
```

**前端交互**（`TaskHistoryList.tsx` / `TaskHistoryCompact.tsx`）：
```
确认删除任务记录 "规则挖掘 - 2026-04-15 16:25"？

☑ 同时删除任务产生的阶段数据文件（推荐）
   └ 包含 N 个阶段输出文件，约 XX MB

[删除]  [取消]
```
- 默认勾选（绝大多数场景不需要保留孤儿文件）
- 展示文件数量和大小（需新增 API 或在 delete 响应中返回清理统计）
- DELETE API 增加 query param：`?cleanup_files=true`（默认 true）

#### 补充：定期清理机制

`PersistentExecutionStore.cleanup_expired_states()` 已有 3 天自动清理，但：
- 仅清理 `execution_states/` 目录中超过 3 天的文件
- **不清理** `task_results/` 和 DB 中的关联数据
- 建议在定期清理中也加入孤儿检测（DB 中有记录但 task_records 中无关联的记录）

**已实现的文件结构**：
```
deepanalyze/core/task_manager/
├── __init__.py              # 模块导出
├── database.py              # TaskManagerDB
├── models.py                # TaskRecord, TaskControl, ExecutionState, ExecutionCheckpoint, StageAIAnalysis
├── enums.py                 # TaskStatus, TaskControlAction, EngineMode, InteractionMode
├── controller.py            # TaskController
├── history_service.py       # TaskHistoryService
├── result_storage.py        # TaskResultStorage
├── checkpoint.py            # CheckpointMixin
├── persistent_store.py      # PersistentExecutionStore（Phase 6）
├── recovery.py              # ExecutionStateRecovery（Phase 6）
└── stage_analysis_service.py # StageAnalysisService（Phase 7）
```

**API接口**（已在 `API/sop_api.py` 中实现）：
- `POST /sop/executions/{execution_id}/pause`
- `POST /sop/executions/{execution_id}/stop`
- `POST /sop/executions/{execution_id}/resume`
- `GET /sop/history`
- `GET /sop/history/{record_id}`
- `GET /sop/history/{record_id}/result`
- `DELETE /sop/history/{record_id}`
- `GET /sop/statistics`
- `GET /sop/executions/recoverable` (Phase 6)
- `GET /sop/executions/{execution_id}/recovery-info` (Phase 6)
- `POST /sop/executions/{execution_id}/recover` (Phase 6)
- `GET /sop/executions/{execution_id}/checkpoints` (Phase 6)
- `GET /sop/history/{record_id}/stages/{stage_id}/analysis` (Phase 7)
- `POST /sop/history/{record_id}/stages/{stage_id}/analysis` (Phase 7)
- `DELETE /sop/history/{record_id}/stages/{stage_id}/analysis` (Phase 7)

---

## 11. 执行状态持久化方案（Phase 6 - ✅ 已完成）




> **状态**: ✅ 已完成
> 
> **目标**: 支持跨后端重启恢复暂停中的任务执行

### 11.1 问题背景

当前执行状态存储架构存在以下限制：

```
┌─────────────────────────────────────────────────────────────┐
│                    当前架构（纯内存存储）                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ExecutionStore._executions: Dict[str, Context]            │
│   （统一存储，包含普通模式和专家模式的执行上下文）              │
│                                                             │
│   ⚠️ 历史问题（已通过 Phase 6 解决）：                        │
│   - 后端重启 → 内存清空 → 所有执行上下文丢失                   │
│   - 暂停中的任务无法恢复                                      │
│   - 历史任务详情无法查看（execution_id 已不存在）              │
│   ✅ 解决方案：PersistentExecutionStore 双层存储架构          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

> **架构简化说明**（2025-01更新）：
> 原设计中存在两套存储（`ExecutionStore` 和 `ExpertExecutionStore`），
> 现已统一为单一的 `ExecutionStore`，通过 `interaction_mode` 字段区分普通模式和专家模式。
> 这简化了持久化方案，只需持久化一套存储即可。

| 场景 | 当前行为 | 期望行为 |
|------|---------|---------|
| 任务执行中刷新前端 | ✅ 可恢复 | ✅ 可恢复 |
| 任务暂停中刷新前端 | ✅ 可恢复 | ✅ 可恢复 |
| **后端重启** | ❌ 状态丢失 | ✅ 可恢复 |
| **历史任务详情查看** | ❌ 加载失败 | ✅ 可查看 |

### 11.2 设计目标

1. **跨重启恢复**：后端重启后，暂停中的任务可继续执行
2. **历史可追溯**：任意时间点可查看历史任务的执行详情
3. **检查点机制**：每阶段完成后保存检查点，支持断点续执行
4. **低侵入性**：最小化对现有代码的修改
5. **高性能**：内存缓存 + 数据库持久化双层架构

### 11.3 架构设计

#### 11.3.1 双层存储架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     执行状态持久化架构                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                   API Layer (sop_api.py)                   │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              ▼                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              PersistentExecutionStore (NEW)                │  │
│  │                                                           │  │
│  │  ┌─────────────────┐    ┌─────────────────────────────┐   │  │
│  │  │   内存缓存层     │    │       数据库持久化层         │   │  │
│  │  │  (快速访问)     │◄──►│    (跨重启持久化)           │   │  │
│  │  │                 │    │                             │   │  │
│  │  │ _executions:    │    │ execution_states 表         │   │  │
│  │  │ Dict[str, Ctx]  │    │ execution_checkpoints 表    │   │  │
│  │  └─────────────────┘    └─────────────────────────────┘   │  │
│  │                                                           │  │
│  │  核心方法:                                                 │  │
│  │  - create() → 内存 + DB                                   │  │
│  │  - get() → 优先内存，回退DB                                │  │
│  │  - update() → 内存 + DB同步                               │  │
│  │  - checkpoint() → 保存检查点到DB                           │  │
│  │  - restore() → 从DB恢复到内存                              │  │
│  │  - cleanup() → 清理已完成任务                              │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              ▼                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    TaskManagerDB                           │  │
│  │                                                           │  │
│  │  ┌─────────────────┐  ┌─────────────────┐                │  │
│  │  │execution_states │  │execution_       │                │  │
│  │  │     (NEW)       │  │checkpoints(NEW) │                │  │
│  │  └─────────────────┘  └─────────────────┘                │  │
│  │                                                           │  │
│  │  ┌─────────────────┐  ┌─────────────────┐                │  │
│  │  │ task_records    │  │ task_controls   │                │  │
│  │  │   (已有)        │  │    (已有)       │                │  │
│  │  └─────────────────┘  └─────────────────┘                │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                  File System Storage                       │  │
│  │                                                           │  │
│  │  execution_states/                                        │  │
│  │  └── {execution_id}/                                      │  │
│  │      ├── context.pkl      # 完整上下文序列化               │  │
│  │      ├── stage_outputs/   # 各阶段输出                    │  │
│  │      │   ├── data_loading.pkl                            │  │
│  │      │   ├── woe_binning.pkl                             │  │
│  │      │   └── ...                                         │  │
│  │      └── checkpoint.json  # 检查点元数据                  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 11.3.2 数据流

```
┌──────────────────────────────────────────────────────────────────┐
│                        执行状态数据流                              │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. 任务创建                                                      │
│     ┌─────────┐                                                  │
│     │ create()│ → 内存缓存 + DB写入 + 文件系统初始化              │
│     └─────────┘                                                  │
│                                                                  │
│  2. 阶段执行                                                      │
│     ┌─────────────┐                                              │
│     │ 阶段开始     │ → 更新内存状态 + DB状态                       │
│     └─────────────┘                                              │
│            │                                                     │
│            ▼                                                     │
│     ┌─────────────┐                                              │
│     │ 阶段完成     │ → 保存检查点（阶段输出 → 文件系统）            │
│     └─────────────┘                                              │
│            │                                                     │
│            ▼                                                     │
│     ┌─────────────┐                                              │
│     │ 检查控制点   │ → 检查暂停/停止请求                           │
│     └─────────────┘                                              │
│                                                                  │
│  3. 任务暂停                                                      │
│     ┌─────────────┐                                              │
│     │ pause()     │ → 保存完整上下文到文件系统                     │
│     └─────────────┘   更新DB状态为 paused                         │
│                       记录暂停点（stage_id, progress）            │
│                                                                  │
│  4. 后端重启                                                      │
│     ┌─────────────┐                                              │
│     │ 启动时      │ → 扫描DB中 status=paused/running 的任务       │
│     └─────────────┘   从文件系统恢复上下文到内存                   │
│                       更新前端可查询状态                          │
│                                                                  │
│  5. 任务恢复                                                      │
│     ┌─────────────┐                                              │
│     │ resume()    │ → 从检查点恢复执行                            │
│     └─────────────┘   继续后续阶段                                │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 11.4 数据模型设计

#### 11.4.1 新增 ORM 模型

```python
# models.py (新增)

class ExecutionState(TaskManagerBase):
    """执行状态持久化表
    
    存储执行上下文的核心状态，支持跨重启恢复
    """
    __tablename__ = "execution_states"
    
    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)
    execution_id = Column(String(64), unique=True, nullable=False, index=True)
    
    # 关联
    record_id = Column(String(64), nullable=True, index=True)  # 关联 task_records
    session_id = Column(String(64), nullable=True, index=True)
    
    # 任务信息
    task_id = Column(String(64), nullable=False)              # 任务类型ID
    task_type = Column(String(32), nullable=False)            # pipeline/llm
    interaction_mode = Column(String(32), nullable=False)     # auto/expert
    
    # 执行状态
    status = Column(String(32), nullable=False, default="pending", index=True)
    current_stage_id = Column(String(64), nullable=True)
    current_stage_index = Column(Integer, default=0)
    overall_progress = Column(Float, default=0.0)
    
    # 参数（JSON）
    params_json = Column(Text, nullable=True)
    
    # 数据文件路径
    data_file_path = Column(String(512), nullable=True)
    
    # 状态文件路径（序列化的完整上下文）
    state_file_path = Column(String(512), nullable=True)
    
    # 阶段状态（JSON）
    stages_json = Column(Text, nullable=True)
    
    # 暂停/恢复信息
    pause_stage_id = Column(String(64), nullable=True)        # 暂停时的阶段ID
    pause_reason = Column(String(256), nullable=True)         # 暂停原因
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    paused_at = Column(DateTime, nullable=True)
    resumed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 索引
    __table_args__ = (
        Index('idx_exec_status_updated', 'status', 'updated_at'),
        Index('idx_exec_session', 'session_id', 'status'),
    )


class ExecutionCheckpoint(TaskManagerBase):
    """执行检查点表
    
    记录每个阶段完成后的检查点，支持断点续执行
    """
    __tablename__ = "execution_checkpoints"
    
    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)
    checkpoint_id = Column(String(64), unique=True, nullable=False, index=True)
    
    # 关联
    execution_id = Column(String(64), nullable=False, index=True)
    
    # 检查点信息
    stage_id = Column(String(64), nullable=False)
    stage_index = Column(Integer, nullable=False)
    stage_status = Column(String(32), nullable=False)         # completed/failed/skipped
    
    # 阶段输出文件路径
    outputs_file_path = Column(String(512), nullable=True)
    
    # 阶段输出摘要（JSON，用于快速预览）
    outputs_summary_json = Column(Text, nullable=True)
    
    # 执行信息
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    
    # 错误信息
    error_message = Column(Text, nullable=True)
    
    # 创建时间
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 索引
    __table_args__ = (
        Index('idx_checkpoint_exec_stage', 'execution_id', 'stage_index'),
    )
```

#### 11.4.2 表结构说明

**execution_states 表**

| 字段 | 类型 | 说明 |
|------|------|------|
| execution_id | VARCHAR(64) | 执行ID（唯一索引） |
| record_id | VARCHAR(64) | 关联的任务记录ID |
| task_id | VARCHAR(64) | 任务类型（scorecard_dev等） |
| interaction_mode | VARCHAR(32) | 交互模式（auto/expert） |
| status | VARCHAR(32) | 状态（running/paused/completed等） |
| current_stage_id | VARCHAR(64) | 当前阶段ID |
| params_json | TEXT | 执行参数JSON |
| state_file_path | VARCHAR(512) | 序列化状态文件路径 |
| stages_json | TEXT | 各阶段状态JSON |
| pause_stage_id | VARCHAR(64) | 暂停时的阶段ID |

**execution_checkpoints 表**

| 字段 | 类型 | 说明 |
|------|------|------|
| checkpoint_id | VARCHAR(64) | 检查点ID（唯一） |
| execution_id | VARCHAR(64) | 关联的执行ID |
| stage_id | VARCHAR(64) | 阶段ID |
| stage_index | INTEGER | 阶段序号 |
| stage_status | VARCHAR(32) | 阶段状态 |
| outputs_file_path | VARCHAR(512) | 阶段输出文件路径 |
| outputs_summary_json | TEXT | 输出摘要（快速预览） |

### 11.5 核心组件设计

#### 11.5.1 PersistentExecutionStore

```python
# persistent_execution_store.py (NEW)

import json
import pickle
import uuid
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import asdict

from .database import get_task_manager_db
from .models import ExecutionState, ExecutionCheckpoint
from .enums import TaskStatus

logger = logging.getLogger(__name__)


class PersistentExecutionStore:
    """持久化执行存储
    
    提供执行状态的内存缓存 + 数据库持久化双层存储。
    支持跨后端重启恢复暂停中的任务。
    
    设计原则：
    - 写操作：同时写入内存和数据库
    - 读操作：优先内存，回退数据库
    - 检查点：阶段完成后保存到文件系统
    - 恢复：从数据库和文件系统重建内存状态
    """
    
    # 内存缓存
    _cache: Dict[str, Any] = {}  # execution_id -> ExecutionContext
    
    # 状态文件存储目录
    _state_dir: Path = Path("./execution_states")
    
    @classmethod
    def initialize(cls, state_dir: str = "./execution_states") -> None:
        """初始化存储
        
        在应用启动时调用，恢复未完成的任务状态
        """
        cls._state_dir = Path(state_dir)
        cls._state_dir.mkdir(parents=True, exist_ok=True)
        
        # 恢复暂停中和运行中的任务
        cls._restore_active_executions()
    
    @classmethod
    def create(
        cls,
        execution_id: str,
        task_id: str,
        session_id: str,
        params: Dict[str, Any],
        interaction_mode: str = "auto",
        record_id: Optional[str] = None,
        data_file_path: Optional[str] = None,
        context: Any = None,  # ExecutionContext 或 ExpertExecutionContext
    ) -> str:
        """创建执行状态
        
        Args:
            execution_id: 执行ID
            task_id: 任务类型ID
            session_id: 会话ID
            params: 执行参数
            interaction_mode: 交互模式
            record_id: 关联的任务记录ID
            data_file_path: 数据文件路径
            context: 执行上下文对象
            
        Returns:
            execution_id
        """
        # 1. 写入内存缓存
        if context:
            cls._cache[execution_id] = context
        
        # 2. 写入数据库
        db = get_task_manager_db()
        with next(db.get_session()) as session:
            state = ExecutionState(
                execution_id=execution_id,
                record_id=record_id,
                session_id=session_id,
                task_id=task_id,
                task_type="pipeline",
                interaction_mode=interaction_mode,
                status=TaskStatus.PENDING.value,
                params_json=json.dumps(params, ensure_ascii=False),
                data_file_path=data_file_path,
            )
            session.add(state)
            session.commit()
        
        # 3. 创建状态文件目录
        state_dir = cls._state_dir / execution_id
        state_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"[PersistentStore] Created execution: {execution_id}")
        return execution_id
    
    @classmethod
    def get(cls, execution_id: str) -> Optional[Any]:
        """获取执行上下文
        
        优先从内存缓存获取，如果不存在则尝试从数据库恢复
        """
        # 1. 优先内存缓存
        if execution_id in cls._cache:
            return cls._cache[execution_id]
        
        # 2. 尝试从数据库恢复
        return cls._restore_from_db(execution_id)
    
    @classmethod
    def update(
        cls,
        execution_id: str,
        status: Optional[str] = None,
        current_stage_id: Optional[str] = None,
        current_stage_index: Optional[int] = None,
        overall_progress: Optional[float] = None,
        stages: Optional[Dict[str, Any]] = None,
        context: Any = None,
    ) -> bool:
        """更新执行状态
        
        同时更新内存缓存和数据库
        """
        # 1. 更新内存缓存
        if context:
            cls._cache[execution_id] = context
        
        # 2. 更新数据库
        db = get_task_manager_db()
        with next(db.get_session()) as session:
            state = session.query(ExecutionState).filter_by(
                execution_id=execution_id
            ).first()
            
            if not state:
                logger.warning(f"[PersistentStore] State not found: {execution_id}")
                return False
            
            if status:
                state.status = status
                if status == TaskStatus.RUNNING.value and not state.started_at:
                    state.started_at = datetime.utcnow()
                elif status == TaskStatus.PAUSED.value:
                    state.paused_at = datetime.utcnow()
                elif status in (TaskStatus.COMPLETED.value, TaskStatus.FAILED.value, 
                               TaskStatus.STOPPED.value):
                    state.completed_at = datetime.utcnow()
            
            if current_stage_id is not None:
                state.current_stage_id = current_stage_id
            if current_stage_index is not None:
                state.current_stage_index = current_stage_index
            if overall_progress is not None:
                state.overall_progress = overall_progress
            if stages is not None:
                state.stages_json = json.dumps(stages, ensure_ascii=False)
            
            state.updated_at = datetime.utcnow()
            session.commit()
        
        return True
    
    @classmethod
    def save_checkpoint(
        cls,
        execution_id: str,
        stage_id: str,
        stage_index: int,
        stage_status: str,
        outputs: Dict[str, Any],
        outputs_summary: Optional[Dict[str, Any]] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
    ) -> str:
        """保存阶段检查点
        
        在每个阶段完成后调用，保存阶段输出到文件系统
        
        Args:
            execution_id: 执行ID
            stage_id: 阶段ID
            stage_index: 阶段序号
            stage_status: 阶段状态
            outputs: 阶段输出数据
            outputs_summary: 输出摘要（用于快速预览）
            
        Returns:
            checkpoint_id
        """
        checkpoint_id = f"ckpt-{uuid.uuid4().hex[:12]}"
        
        # 1. 保存阶段输出到文件系统
        outputs_file_path = None
        if outputs:
            stage_dir = cls._state_dir / execution_id / "stage_outputs"
            stage_dir.mkdir(parents=True, exist_ok=True)
            outputs_file = stage_dir / f"{stage_id}.pkl"
            
            with open(outputs_file, "wb") as f:
                pickle.dump(outputs, f)
            
            outputs_file_path = str(outputs_file)
        
        # 2. 写入数据库
        db = get_task_manager_db()
        with next(db.get_session()) as session:
            checkpoint = ExecutionCheckpoint(
                checkpoint_id=checkpoint_id,
                execution_id=execution_id,
                stage_id=stage_id,
                stage_index=stage_index,
                stage_status=stage_status,
                outputs_file_path=outputs_file_path,
                outputs_summary_json=json.dumps(outputs_summary, ensure_ascii=False) if outputs_summary else None,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=(completed_at - started_at).total_seconds() if started_at and completed_at else None,
            )
            session.add(checkpoint)
            session.commit()
        
        logger.debug(f"[PersistentStore] Saved checkpoint: {checkpoint_id} for stage {stage_id}")
        return checkpoint_id
    
    @classmethod
    def save_full_state(cls, execution_id: str, context: Any) -> str:
        """保存完整执行状态
        
        在任务暂停时调用，将完整上下文序列化到文件系统
        
        Args:
            execution_id: 执行ID
            context: 执行上下文对象
            
        Returns:
            状态文件路径
        """
        state_file = cls._state_dir / execution_id / "context.pkl"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(state_file, "wb") as f:
            pickle.dump(context, f)
        
        # 更新数据库中的状态文件路径
        db = get_task_manager_db()
        with next(db.get_session()) as session:
            state = session.query(ExecutionState).filter_by(
                execution_id=execution_id
            ).first()
            if state:
                state.state_file_path = str(state_file)
                session.commit()
        
        logger.info(f"[PersistentStore] Saved full state: {execution_id}")
        return str(state_file)
    
    @classmethod
    def load_checkpoint_outputs(
        cls,
        execution_id: str,
        stage_id: str
    ) -> Optional[Dict[str, Any]]:
        """加载阶段检查点输出
        
        Args:
            execution_id: 执行ID
            stage_id: 阶段ID
            
        Returns:
            阶段输出数据
        """
        outputs_file = cls._state_dir / execution_id / "stage_outputs" / f"{stage_id}.pkl"
        
        if not outputs_file.exists():
            return None
        
        with open(outputs_file, "rb") as f:
            return pickle.load(f)
    
    @classmethod
    def get_checkpoints(cls, execution_id: str) -> List[Dict[str, Any]]:
        """获取执行的所有检查点
        
        Args:
            execution_id: 执行ID
            
        Returns:
            检查点列表
        """
        db = get_task_manager_db()
        with next(db.get_session()) as session:
            checkpoints = session.query(ExecutionCheckpoint).filter_by(
                execution_id=execution_id
            ).order_by(ExecutionCheckpoint.stage_index).all()
            
            return [
                {
                    "checkpoint_id": cp.checkpoint_id,
                    "stage_id": cp.stage_id,
                    "stage_index": cp.stage_index,
                    "stage_status": cp.stage_status,
                    "outputs_summary": json.loads(cp.outputs_summary_json) if cp.outputs_summary_json else None,
                    "started_at": cp.started_at.isoformat() if cp.started_at else None,
                    "completed_at": cp.completed_at.isoformat() if cp.completed_at else None,
                    "duration_seconds": cp.duration_seconds,
                }
                for cp in checkpoints
            ]
    
    @classmethod
    def mark_paused(
        cls,
        execution_id: str,
        pause_stage_id: str,
        pause_reason: str = "用户暂停",
        context: Any = None,
    ) -> bool:
        """标记任务为暂停状态
        
        保存完整状态并更新数据库
        """
        # 1. 保存完整状态
        if context:
            cls.save_full_state(execution_id, context)
        
        # 2. 更新数据库
        db = get_task_manager_db()
        with next(db.get_session()) as session:
            state = session.query(ExecutionState).filter_by(
                execution_id=execution_id
            ).first()
            
            if not state:
                return False
            
            state.status = TaskStatus.PAUSED.value
            state.pause_stage_id = pause_stage_id
            state.pause_reason = pause_reason
            state.paused_at = datetime.utcnow()
            session.commit()
        
        logger.info(f"[PersistentStore] Marked paused: {execution_id} at stage {pause_stage_id}")
        return True
    
    @classmethod
    def remove(cls, execution_id: str) -> None:
        """移除执行状态
        
        从内存缓存移除（数据库记录保留用于历史查询）
        """
        cls._cache.pop(execution_id, None)
    
    @classmethod
    def cleanup(cls, execution_id: str, delete_files: bool = False) -> None:
        """清理执行状态
        
        Args:
            execution_id: 执行ID
            delete_files: 是否删除文件系统中的状态文件
        """
        # 1. 从内存移除
        cls._cache.pop(execution_id, None)
        
        # 2. 可选：删除文件
        if delete_files:
            import shutil
            state_dir = cls._state_dir / execution_id
            if state_dir.exists():
                shutil.rmtree(state_dir)
    
    @classmethod
    def list_active(cls, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出活跃的执行（运行中或暂停中）
        
        Args:
            session_id: 可选，按会话筛选
            
        Returns:
            活跃执行列表
        """
        db = get_task_manager_db()
        with next(db.get_session()) as session:
            query = session.query(ExecutionState).filter(
                ExecutionState.status.in_([
                    TaskStatus.RUNNING.value,
                    TaskStatus.PAUSED.value,
                    TaskStatus.PENDING.value,
                ])
            )
            
            if session_id:
                query = query.filter(ExecutionState.session_id == session_id)
            
            states = query.order_by(ExecutionState.updated_at.desc()).all()
            
            return [cls._state_to_dict(s) for s in states]
    
    @classmethod
    def list_paused(cls) -> List[Dict[str, Any]]:
        """列出所有暂停中的执行
        
        用于后端启动时恢复
        """
        db = get_task_manager_db()
        with next(db.get_session()) as session:
            states = session.query(ExecutionState).filter(
                ExecutionState.status == TaskStatus.PAUSED.value
            ).all()
            
            return [cls._state_to_dict(s) for s in states]
    
    # ==================== 私有方法 ====================
    
    @classmethod
    def _restore_active_executions(cls) -> None:
        """恢复活跃的执行状态
        
        在应用启动时调用
        """
        logger.info("[PersistentStore] Restoring active executions...")
        
        db = get_task_manager_db()
        with next(db.get_session()) as session:
            # 查找暂停中的任务
            paused_states = session.query(ExecutionState).filter(
                ExecutionState.status == TaskStatus.PAUSED.value
            ).all()
            
            for state in paused_states:
                try:
                    context = cls._load_full_state(state.execution_id)
                    if context:
                        cls._cache[state.execution_id] = context
                        logger.info(f"[PersistentStore] Restored: {state.execution_id}")
                except Exception as e:
                    logger.error(f"[PersistentStore] Failed to restore {state.execution_id}: {e}")
            
            # 将运行中的任务标记为中断（后端重启导致）
            running_states = session.query(ExecutionState).filter(
                ExecutionState.status == TaskStatus.RUNNING.value
            ).all()
            
            for state in running_states:
                state.status = TaskStatus.PAUSED.value
                state.pause_reason = "后端重启导致中断"
                state.paused_at = datetime.utcnow()
                logger.warning(f"[PersistentStore] Marked interrupted: {state.execution_id}")
            
            session.commit()
        
        logger.info(f"[PersistentStore] Restored {len(cls._cache)} executions")
    
    @classmethod
    def _restore_from_db(cls, execution_id: str) -> Optional[Any]:
        """从数据库和文件系统恢复执行上下文"""
        db = get_task_manager_db()
        with next(db.get_session()) as session:
            state = session.query(ExecutionState).filter_by(
                execution_id=execution_id
            ).first()
            
            if not state:
                return None
            
            # 尝试从文件系统加载完整状态
            context = cls._load_full_state(execution_id)
            if context:
                cls._cache[execution_id] = context
                return context
            
            # 如果没有完整状态文件，返回 None（无法恢复）
            return None
    
    @classmethod
    def _load_full_state(cls, execution_id: str) -> Optional[Any]:
        """从文件系统加载完整状态"""
        state_file = cls._state_dir / execution_id / "context.pkl"
        
        if not state_file.exists():
            return None
        
        try:
            with open(state_file, "rb") as f:
                return pickle.load(f)
        except Exception as e:
            logger.error(f"[PersistentStore] Failed to load state file: {e}")
            return None
    
    @staticmethod
    def _state_to_dict(state: ExecutionState) -> Dict[str, Any]:
        """将 ORM 对象转换为字典"""
        return {
            "execution_id": state.execution_id,
            "record_id": state.record_id,
            "session_id": state.session_id,
            "task_id": state.task_id,
            "interaction_mode": state.interaction_mode,
            "status": state.status,
            "current_stage_id": state.current_stage_id,
            "current_stage_index": state.current_stage_index,
            "overall_progress": state.overall_progress,
            "params": json.loads(state.params_json) if state.params_json else None,
            "stages": json.loads(state.stages_json) if state.stages_json else None,
            "pause_stage_id": state.pause_stage_id,
            "pause_reason": state.pause_reason,
            "created_at": state.created_at.isoformat() if state.created_at else None,
            "started_at": state.started_at.isoformat() if state.started_at else None,
            "paused_at": state.paused_at.isoformat() if state.paused_at else None,
            "updated_at": state.updated_at.isoformat() if state.updated_at else None,
        }
```

#### 11.5.2 ExecutionStateRecovery

```python
# recovery.py (NEW)

import logging
from typing import Optional, List, Dict, Any

from .persistent_execution_store import PersistentExecutionStore
from .enums import TaskStatus

logger = logging.getLogger(__name__)


class ExecutionStateRecovery:
    """执行状态恢复服务
    
    提供任务恢复相关的高级功能
    """
    
    @classmethod
    def can_resume(cls, execution_id: str) -> Dict[str, Any]:
        """检查任务是否可以恢复
        
        Returns:
            {
                "can_resume": bool,
                "reason": str,
                "resume_stage_id": str | None,
                "completed_stages": List[str],
            }
        """
        # 获取执行状态
        states = PersistentExecutionStore.list_active()
        state = next((s for s in states if s["execution_id"] == execution_id), None)
        
        if not state:
            return {
                "can_resume": False,
                "reason": "执行不存在或已完成",
                "resume_stage_id": None,
                "completed_stages": [],
            }
        
        if state["status"] != TaskStatus.PAUSED.value:
            return {
                "can_resume": False,
                "reason": f"任务状态为 {state['status']}，不可恢复",
                "resume_stage_id": None,
                "completed_stages": [],
            }
        
        # 获取检查点
        checkpoints = PersistentExecutionStore.get_checkpoints(execution_id)
        completed_stages = [
            cp["stage_id"] for cp in checkpoints 
            if cp["stage_status"] == "completed"
        ]
        
        return {
            "can_resume": True,
            "reason": "可以恢复",
            "resume_stage_id": state.get("pause_stage_id") or state.get("current_stage_id"),
            "completed_stages": completed_stages,
        }
    
    @classmethod
    def get_resume_context(cls, execution_id: str) -> Optional[Dict[str, Any]]:
        """获取恢复所需的上下文信息
        
        Returns:
            {
                "execution_id": str,
                "task_id": str,
                "params": dict,
                "resume_stage_id": str,
                "completed_stages": List[str],
                "stage_outputs": Dict[str, Any],  # 已完成阶段的输出
            }
        """
        check_result = cls.can_resume(execution_id)
        if not check_result["can_resume"]:
            return None
        
        # 获取执行状态
        context = PersistentExecutionStore.get(execution_id)
        if not context:
            return None
        
        # 加载已完成阶段的输出
        stage_outputs = {}
        for stage_id in check_result["completed_stages"]:
            outputs = PersistentExecutionStore.load_checkpoint_outputs(
                execution_id, stage_id
            )
            if outputs:
                stage_outputs[stage_id] = outputs
        
        return {
            "execution_id": execution_id,
            "context": context,
            "resume_stage_id": check_result["resume_stage_id"],
            "completed_stages": check_result["completed_stages"],
            "stage_outputs": stage_outputs,
        }
    
    @classmethod
    def list_recoverable(cls, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出可恢复的任务
        
        Args:
            session_id: 可选，按会话筛选
            
        Returns:
            可恢复任务列表
        """
        paused_states = PersistentExecutionStore.list_paused()
        
        if session_id:
            paused_states = [s for s in paused_states if s["session_id"] == session_id]
        
        result = []
        for state in paused_states:
            checkpoints = PersistentExecutionStore.get_checkpoints(state["execution_id"])
            completed_count = sum(1 for cp in checkpoints if cp["stage_status"] == "completed")
            
            result.append({
                **state,
                "completed_stages_count": completed_count,
                "can_resume": True,
            })
        
        return result
```

### 11.6 集成方案

#### 11.6.1 与现有 ExecutionStore 的集成

```python
# 修改 deepanalyze/analysis/task_SOP/executor.py

class ExecutionStore:
    """执行存储（增强版）
    
    在原有内存存储基础上，增加持久化层调用
    """
    
    @classmethod
    def create(cls, ...) -> ExecutionContext:
        # 原有逻辑...
        context = ExecutionContext(...)
        cls._executions[context.execution_id] = context
        
        # 新增：持久化
        try:
            from deepanalyze.core.task_manager import PersistentExecutionStore
            PersistentExecutionStore.create(
                execution_id=context.execution_id,
                task_id=task_id,
                session_id=session_id,
                params=params,
                interaction_mode=interaction_mode,
                record_id=context.record_id,
                data_file_path=file_path,
                context=context,
            )
        except ImportError:
            pass  # 任务管理模块未安装，跳过持久化
        
        return context
    
    @classmethod
    def get(cls, execution_id: str) -> Optional[ExecutionContext]:
        # 优先内存
        if execution_id in cls._executions:
            return cls._executions[execution_id]
        
        # 回退持久化存储
        try:
            from deepanalyze.core.task_manager import PersistentExecutionStore
            return PersistentExecutionStore.get(execution_id)
        except ImportError:
            return None
```

#### 11.6.2 与 SOPExecutor 的集成

```python
# 修改 SOPExecutor._run_stage()

async def _run_stage(self, stage, context, ...):
    # 执行阶段...
    result = await self._execute_stage_code(...)
    
    # 新增：保存检查点
    try:
        from deepanalyze.core.task_manager import PersistentExecutionStore
        PersistentExecutionStore.save_checkpoint(
            execution_id=context.execution_id,
            stage_id=stage.id,
            stage_index=stage_index,
            stage_status="completed",
            outputs=stage_progress.outputs,
            outputs_summary=self._create_outputs_summary(stage_progress.outputs),
            started_at=stage_progress.started_at,
            completed_at=stage_progress.completed_at,
        )
    except ImportError:
        pass
```

#### 11.6.3 新增 API 接口

```python
# 在 sop_api.py 中新增

@router.get("/executions/recoverable")
async def list_recoverable_executions(session_id: str = None):
    """列出可恢复的任务"""
    from deepanalyze.core.task_manager import ExecutionStateRecovery
    
    return {
        "executions": ExecutionStateRecovery.list_recoverable(session_id)
    }


@router.get("/executions/{execution_id}/recovery-info")
async def get_recovery_info(execution_id: str):
    """获取任务恢复信息"""
    from deepanalyze.core.task_manager import ExecutionStateRecovery
    
    check_result = ExecutionStateRecovery.can_resume(execution_id)
    if not check_result["can_resume"]:
        raise HTTPException(400, check_result["reason"])
    
    return check_result


@router.post("/executions/{execution_id}/recover")
async def recover_execution(execution_id: str):
    """恢复暂停的任务执行"""
    from deepanalyze.core.task_manager import ExecutionStateRecovery
    
    resume_context = ExecutionStateRecovery.get_resume_context(execution_id)
    if not resume_context:
        raise HTTPException(400, "无法恢复任务")
    
    # ✅ 已实现：恢复执行逻辑
    # 1. 从检查点恢复上下文 → PersistentExecutionStore.load_checkpoint_outputs()
    # 2. 从暂停阶段继续执行 → 通过 context.retry_from_stage 机制
    
    return {
        "success": True,
        "execution_id": execution_id,
        "resume_stage_id": resume_context["resume_stage_id"],
    }
```

### 11.7 实施计划

#### Phase 6 任务分解

| 任务ID | 任务 | 说明 | 工作量 | 依赖 |
|--------|------|------|--------|------|
| 6.1 | 新增 ORM 模型 | ExecutionState, ExecutionCheckpoint | 小 | - |
| 6.2 | 实现 PersistentExecutionStore | 核心持久化存储类 | 大 | 6.1 |
| 6.3 | 实现 ExecutionStateRecovery | 恢复服务 | 中 | 6.2 |
| 6.4 | 集成 ExecutionStore | 修改现有存储类（统一存储，含专家模式） | 中 | 6.2 |
| 6.5 | 集成 SOPExecutor | 添加检查点保存 | 中 | 6.2 |
| ~~6.6~~ | ~~集成 ExpertExecutionStore~~ | ~~已废弃：专家模式已合并到 ExecutionStore~~ | - | - |
| 6.7 | 新增恢复 API | /recoverable, /recover | 小 | 6.3 |
| 6.8 | 应用启动恢复 | main.py 初始化 | 小 | 6.2 |
| 6.9 | 前端适配 | 显示可恢复任务 | 中 | 6.7 |
| 6.10 | 测试 | 单元测试、集成测试 | 中 | 6.1-6.9 |

**预估工期**：1-1.5 周（因架构简化，工期缩短）

### 11.8 验收标准

#### 功能验收

- [x] 后端重启后，暂停中的任务状态保留
- [x] 可以查看暂停任务的已完成阶段
- [x] 可以从暂停点恢复执行
- [x] 历史任务详情可正常查看
- [x] 检查点数据正确保存和加载

#### 性能验收

- [x] 检查点保存 < 500ms
- [x] 状态恢复 < 1s
- [x] 不影响正常执行性能

#### 兼容性验收

- [x] 现有自动模式正常工作
- [x] 现有专家模式正常工作
- [x] 不影响未使用持久化的场景

### 11.9 实施说明（2025-01-07 更新）

**Phase 6 已完成实现**，包括：

1. **ORM 模型**（`models.py`）：
   - `ExecutionState`: 执行状态持久化表
   - `ExecutionCheckpoint`: 执行检查点表

2. **持久化存储**（`persistent_store.py`）：
   - `PersistentExecutionStore` 类，提供：
     - 执行状态 CRUD 操作
     - 检查点保存/加载/重置
     - 文件系统存储大型对象（DataFrame、模型等）
     - 自动清理过期状态文件

3. **恢复服务**（`recovery.py`）：
   - `ExecutionStateRecovery` 类，提供：
     - `can_resume()`: 检查任务是否可恢复
     - `get_resume_context()`: 获取恢复所需的上下文
     - `list_recoverable()`: 列出可恢复的任务
     - `can_retry_stage()`: 检查阶段是否可重试
     - `prepare_retry()`: 准备阶段重试

4. **API 接口**（`sop_api.py`）：
   - `GET /sop/executions/recoverable`: 列出可恢复任务
   - `GET /sop/executions/{execution_id}/recovery-info`: 获取恢复信息
   - `POST /sop/executions/{execution_id}/recover`: 恢复执行
   - `GET /sop/executions/{execution_id}/checkpoints`: 获取检查点列表

### 11.9 配置项

```python
# 新增配置项
EXECUTION_STATE_DIR = "./execution_states"      # 状态文件存储目录
EXECUTION_STATE_RETENTION_DAYS = 7              # 状态文件保留天数
ENABLE_EXECUTION_PERSISTENCE = True             # 是否启用执行状态持久化
```

### 11.10 风险与对策

| 风险 | 影响 | 对策 |
|------|------|------|
| Pickle 反序列化安全 | 中 | 仅反序列化本地文件，不接受外部输入 |
| 状态文件损坏 | 中 | 添加校验和，损坏时标记为不可恢复 |
| 磁盘空间占用 | 低 | 定期清理过期状态文件 |
| 版本兼容性 | 中 | 状态文件包含版本号，不兼容时提示重新执行 |

---

## 12. 阶段 AI 分析结果持久化方案（Phase 7 - ✅ 已完成）

### 12.1 背景与需求

在专家模式下，每个阶段完成后会调用 LLM 生成 AI 分析评估。当前实现使用浏览器 `sessionStorage` 缓存，存在以下问题：

| 问题 | 影响 |
|------|------|
| 关闭浏览器标签页后缓存丢失 | 用户需要重新等待 AI 分析生成 |
| 不同标签页不共享 | 同一任务在不同标签页需要重复生成 |
| 与任务生命周期无关 | 任务删除后缓存可能残留（如标签页未关闭） |
| 无法跨设备访问 | 换设备后无法查看历史 AI 分析 |

### 12.2 设计目标

1. **持久化存储**：AI 分析结果保存到数据库
2. **生命周期绑定**：任务删除时自动清理关联的 AI 分析
3. **按需生成**：仅在首次查看或点击"重新分析"时调用 LLM
4. **高效读取**：缓存命中时直接返回，无需调用 LLM

### 12.3 数据模型

#### 12.3.1 新增 ORM 模型

```python
# models.py

class StageAIAnalysis(TaskManagerBase):
    """阶段 AI 分析结果"""
    __tablename__ = "stage_ai_analysis"
    
    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 关联键
    record_id = Column(String(64), nullable=False, index=True)  # 关联 TaskRecord
    stage_id = Column(String(64), nullable=False)               # 阶段ID
    
    # 分析内容
    analysis_text = Column(Text, nullable=False)                # AI 分析文本
    model_used = Column(String(128), nullable=True)             # 使用的模型
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 复合唯一索引（同一任务同一阶段只保留一条）
    __table_args__ = (
        Index('idx_record_stage', 'record_id', 'stage_id', unique=True),
    )
```

#### 12.3.2 数据库表结构

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 自增主键 |
| record_id | VARCHAR(64) | 任务记录ID（外键关联 task_records） |
| stage_id | VARCHAR(64) | 阶段ID（如 data_loading, woe_binning） |
| analysis_text | TEXT | AI 分析文本内容 |
| model_used | VARCHAR(128) | 生成分析使用的模型 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 12.4 服务层设计

```python
# stage_analysis_service.py

class StageAnalysisService:
    """阶段 AI 分析服务"""
    
    @classmethod
    def get_analysis(
        cls,
        record_id: str,
        stage_id: str
    ) -> Optional[Dict[str, Any]]:
        """获取阶段 AI 分析结果
        
        Returns:
            {"analysis_text": "...", "model_used": "...", "created_at": "..."} 或 None
        """
        db = get_task_manager_db()
        with next(db.get_session()) as session:
            analysis = session.query(StageAIAnalysis).filter_by(
                record_id=record_id,
                stage_id=stage_id
            ).first()
            
            if not analysis:
                return None
            
            return {
                "analysis_text": analysis.analysis_text,
                "model_used": analysis.model_used,
                "created_at": analysis.created_at.isoformat() if analysis.created_at else None
            }
    
    @classmethod
    def save_analysis(
        cls,
        record_id: str,
        stage_id: str,
        analysis_text: str,
        model_used: str = None
    ) -> bool:
        """保存阶段 AI 分析结果（存在则更新）"""
        db = get_task_manager_db()
        with next(db.get_session()) as session:
            # 查找现有记录
            analysis = session.query(StageAIAnalysis).filter_by(
                record_id=record_id,
                stage_id=stage_id
            ).first()
            
            if analysis:
                # 更新
                analysis.analysis_text = analysis_text
                analysis.model_used = model_used
                analysis.updated_at = datetime.utcnow()
            else:
                # 新增
                analysis = StageAIAnalysis(
                    record_id=record_id,
                    stage_id=stage_id,
                    analysis_text=analysis_text,
                    model_used=model_used
                )
                session.add(analysis)
            
            session.commit()
            return True
    
    @classmethod
    def delete_analysis(
        cls,
        record_id: str,
        stage_id: str = None
    ) -> int:
        """删除阶段 AI 分析结果
        
        Args:
            record_id: 任务记录ID
            stage_id: 阶段ID（为空则删除该任务所有阶段的分析）
            
        Returns:
            删除的记录数
        """
        db = get_task_manager_db()
        with next(db.get_session()) as session:
            query = session.query(StageAIAnalysis).filter_by(record_id=record_id)
            if stage_id:
                query = query.filter_by(stage_id=stage_id)
            
            count = query.delete()
            session.commit()
            return count
    
    @classmethod
    def get_all_analyses_for_record(
        cls,
        record_id: str
    ) -> List[Dict[str, Any]]:
        """获取任务所有阶段的 AI 分析结果"""
        db = get_task_manager_db()
        with next(db.get_session()) as session:
            analyses = session.query(StageAIAnalysis).filter_by(
                record_id=record_id
            ).all()
            
            return [
                {
                    "stage_id": a.stage_id,
                    "analysis_text": a.analysis_text,
                    "model_used": a.model_used,
                    "created_at": a.created_at.isoformat() if a.created_at else None
                }
                for a in analyses
            ]
```

### 12.5 API 接口设计

#### 12.5.1 获取阶段 AI 分析

```
GET /sop/history/{record_id}/stages/{stage_id}/analysis
```

**响应**：
```json
{
    "record_id": "rec-abc123",
    "stage_id": "woe_binning",
    "analysis_text": "本阶段 WOE 分箱结果整体表现【优秀】...",
    "model_used": "gpt-4",
    "created_at": "2024-01-15T10:32:00",
    "cached": true
}
```

**无缓存时响应**：
```json
{
    "record_id": "rec-abc123",
    "stage_id": "woe_binning",
    "analysis_text": null,
    "cached": false
}
```

#### 12.5.2 保存阶段 AI 分析

```
POST /sop/history/{record_id}/stages/{stage_id}/analysis
```

**请求体**：
```json
{
    "analysis_text": "本阶段 WOE 分箱结果整体表现【优秀】...",
    "model_used": "gpt-4"
}
```

**响应**：
```json
{
    "success": true,
    "record_id": "rec-abc123",
    "stage_id": "woe_binning"
}
```

#### 12.5.3 删除阶段 AI 分析（重新分析时调用）

```
DELETE /sop/history/{record_id}/stages/{stage_id}/analysis
```

**响应**：
```json
{
    "success": true,
    "deleted_count": 1
}
```

### 12.6 与任务删除的联动

修改 `TaskHistoryService.delete_record()` 方法，删除任务时自动清理关联的 AI 分析：

```python
# history_service.py

@classmethod
def delete_record(cls, record_id: str) -> bool:
    """删除记录（含关联的 AI 分析）"""
    db = get_task_manager_db()
    with next(db.get_session()) as session:
        # 1. 删除关联的 AI 分析
        session.query(StageAIAnalysis).filter_by(record_id=record_id).delete()
        
        # 2. 删除任务记录
        result = session.query(TaskRecord).filter_by(record_id=record_id).delete()
        
        session.commit()
        return result > 0
```

### 12.7 前端适配

#### 12.7.1 修改 StageOutputPreview 组件

```typescript
// StageOutputPreview.tsx

// 1. 组件初始化时，从后端 API 读取缓存
useEffect(() => {
  if (recordId && stageId && status === "completed") {
    fetchCachedAnalysis(recordId, stageId).then(cached => {
      if (cached?.analysis_text) {
        setAiAnalysis(cached.analysis_text);
        setHasTriggeredAnalysis(true);
      }
    });
  }
}, [recordId, stageId, status]);

// 2. AI 分析完成后，保存到后端
const performAIAnalysis = useCallback(async () => {
  // ... 流式输出逻辑 ...
  
  // 分析完成后保存到后端
  if (fullAnalysis && recordId) {
    await saveAnalysisToBackend(recordId, stageId, fullAnalysis, selectedModel);
  }
}, [...]);

// 3. 重新分析时，先删除后端缓存
const handleReanalyze = async () => {
  if (recordId) {
    await deleteAnalysisFromBackend(recordId, stageId);
  }
  setAiAnalysis("");
  setHasTriggeredAnalysis(false);
  performAIAnalysis();
};
```

#### 12.7.2 API 调用函数

```typescript
// sopService.ts

export async function getStageAnalysis(
  recordId: string,
  stageId: string
): Promise<{ analysis_text: string | null; cached: boolean }> {
  const response = await fetch(
    `${API_BASE}/sop/history/${recordId}/stages/${stageId}/analysis`
  );
  return response.json();
}

export async function saveStageAnalysis(
  recordId: string,
  stageId: string,
  analysisText: string,
  modelUsed?: string
): Promise<void> {
  await fetch(
    `${API_BASE}/sop/history/${recordId}/stages/${stageId}/analysis`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ analysis_text: analysisText, model_used: modelUsed })
    }
  );
}

export async function deleteStageAnalysis(
  recordId: string,
  stageId: string
): Promise<void> {
  await fetch(
    `${API_BASE}/sop/history/${recordId}/stages/${stageId}/analysis`,
    { method: "DELETE" }
  );
}
```

### 12.8 数据清理策略

| 场景 | 清理方式 |
|------|----------|
| 删除单个任务 | 自动删除该任务所有阶段的 AI 分析 |
| 清理过期任务 | `cleanup_old()` 时同步清理关联的 AI 分析 |
| 手动重新分析 | 删除该阶段的 AI 分析缓存，重新生成 |

### 12.9 实施计划

| 任务ID | 任务 | 说明 | 工作量 |
|--------|------|------|--------|
| 7.1 | 新增 ORM 模型 | StageAIAnalysis | 小 |
| 7.2 | 实现 StageAnalysisService | 增删查服务 | 小 |
| 7.3 | 新增 API 接口 | GET/POST/DELETE | 小 |
| 7.4 | 修改 delete_record | 联动删除 AI 分析 | 小 |
| 7.5 | 前端适配 | 修改 StageOutputPreview | 中 |
| 7.6 | 移除 sessionStorage 缓存 | 清理旧代码 | 小 |
| 7.7 | 测试 | 功能测试、联动测试 | 小 |

**预估工期**：0.5-1 周

### 12.10 验收标准

- [x] 阶段 AI 分析结果保存到数据库
- [x] 切换阶段时从数据库读取缓存（无需重新调用 LLM）
- [x] 点击"重新分析"时删除缓存并重新生成
- [x] 删除任务时自动清理关联的 AI 分析
- [x] 刷新页面后 AI 分析结果保留
- [x] 不同标签页/设备可访问同一任务的 AI 分析

### 12.11 实施说明（2025-01-07 更新）

**Phase 7 已完成实现**，包括：

1. **后端实现**：
   - `models.py`: 新增 `StageAIAnalysis` ORM 模型
   - `stage_analysis_service.py`: 实现 `StageAnalysisService` 服务类
   - `history_service.py`: 修改 `delete_record()` 联动删除 AI 分析
   - `persistent_store.py`: 阶段重试时清除相关 AI 分析缓存
   - `sop_api.py`: 新增 GET/POST/DELETE 接口

2. **前端实现**：
   - `StageOutputPreview.tsx`: 
     - 实现 `fetchAnalysisFromAPI`、`saveAnalysisToAPI`、`deleteAnalysisFromAPI` 函数
     - 优先从后端 API 读取，sessionStorage 作为降级方案
     - 阶段重试时自动清除旧的 AI 分析缓存

3. **Phase 9 增强**（2025-01-07）：
   - 将缓存键从 `sessionId:stageId` 改为 `recordId:stageId`
   - 确保不同任务的 AI 分析缓存独立，新任务不会读取旧任务的缓存

4. **Phase 10 增强**（2025-01-07）：
   - 丰富 `report_generation` 阶段的 `output_preview` 数据
   - 规则挖掘：添加质量验证、PSI稳定性、规则统计等信息
   - 评分卡开发：添加评分卡验证、评分统计、入模变量数等信息
   - 更新前端 AI 分析提示词构建逻辑，支持解析丰富的报告数据

5. **Phase 24 评估数据字段持久化修复**（2025-01-12）：
   - 修复评分卡任务阶段重试时评估数据丢失问题
   - 在 `persistent_store.py` 中添加评估数据字段（y_train, y_test, y_oot, y_pred_proba_* 等）的初始化和恢复逻辑
   - 在 `executor.py` 中添加评估数据的保存逻辑
   - 在 `scorecard_development.py` 中为 `report_generation` 阶段添加 `_full_stage_data` 支持
   - 在 `rule_mining.py` 中为 `prior_analysis`, `amount_analysis`, `report_generation` 阶段添加 `should_skip_stage` 和 `_full_stage_data` 支持

### 12.12 `_full_stage_data` 机制说明（Phase 24 补充）

每个阶段的 `output_preview` 中可包含 `_full_stage_data` 字段，用于存储完整的阶段数据以支持检查点保存和阶段重试：

```python
output_preview = {
    # 前端显示用的摘要数据
    "rows": 1000,
    "columns": 50,
    "preview_table": [...],
    ...
    
    # 检查点保存用的完整数据（不传递给前端）
    "_full_stage_data": {
        # 通用字段
        "df_processed": df,           # 处理后的 DataFrame
        "results": results,           # 累积结果字典
        "feature_cols": feature_cols, # 特征列列表
        
        # 评分卡任务特有字段
        "train_df": train_df,
        "test_df": test_df,
        "oot_df": oot_df,
        "y_train": y_train,
        "y_test": y_test,
        "y_oot": y_oot,
        "y_pred_proba_train": y_pred_proba_train,
        "y_pred_proba_test": y_pred_proba_test,
        "y_pred_proba_oot": y_pred_proba_oot,
        "final_model": final_model,
        "scorecard_df": scorecard_df,
        ...
    }
}
```

**设计原则**：

1. **仅用于后端检查点保存**：`_full_stage_data` 字段不会传递给前端，仅在后端 `executor.py` 的 `save_checkpoint` 中使用
2. **包含阶段重试所需的所有数据**：DataFrame、模型对象、评估数据等
3. **通过 `executor.py` 统一保存**：在阶段完成后，`executor.py` 从 `output_preview["_full_stage_data"]` 提取数据并保存到文件系统
4. **通过 `persistent_store.py` 恢复**：阶段重试时，从检查点文件加载数据并恢复到执行上下文的 `results` 字典中

**阶段支持情况**：

| 任务类型 | 阶段 | `_full_stage_data` 支持 |
|----------|------|------------------------|
| 评分卡开发 | data_loading | ✅ |
| 评分卡开发 | data_split | ✅ |
| 评分卡开发 | woe_binning | ✅ |
| 评分卡开发 | feature_selection | ✅ |
| 评分卡开发 | model_training | ✅ |
| 评分卡开发 | report_generation | ✅ (Phase 24 新增) |
| 规则挖掘 | data_loading | ✅ |
| 规则挖掘 | rule_mining | ✅ |
| 规则挖掘 | prior_analysis | ✅ (Phase 24 新增) |
| 规则挖掘 | amount_analysis | ✅ (Phase 24 新增) |
| 规则挖掘 | report_generation | ✅ (Phase 24 新增) |

**实现代码参考**（`executor.py`）：

```python
# 在 _run_stage() 中保存检查点
async def _run_stage(self, stage, context, ...):
    # 执行阶段...
    result = await self._execute_stage_code(...)
    
    # 保存检查点
    try:
        from deepanalyze.core.task_manager import PersistentExecutionStore
        
        # 从 output_preview 提取完整数据
        full_stage_data = stage_progress.outputs.get("output_preview", {}).get("_full_stage_data", {})
        
        # 合并评估数据到保存内容
        outputs_to_save = {
            **stage_progress.outputs,
            **full_stage_data,  # 包含 y_train, y_test, y_pred_proba_* 等
        }
        
        PersistentExecutionStore.save_checkpoint(
            execution_id=context.execution_id,
            stage_id=stage.id,
            stage_index=stage_index,
            stage_status="completed",
            outputs=outputs_to_save,
            outputs_summary=self._create_outputs_summary(stage_progress.outputs),
            started_at=stage_progress.started_at,
            completed_at=stage_progress.completed_at,
        )
    except ImportError:
        pass
```
