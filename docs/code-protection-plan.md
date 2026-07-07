# DeepAnalyze (CreditWise) 代码保护方案

> **版本**: 1.3（新增用户管理模块（批次1/批次2，SQLite账户体系+CWAuth认证）的增量评估）
> **日期**: 2026-07-07
> **目标**: 避免源代码直接在新服务器/PC 上部署，保护核心风控算法知识产权
> **v1.1 修正摘要**: 1) 更正 exec/eval 风险模块识别（executor.py 无风险可编译，validators.py 才是真实风险点）；2) License 机制由对称加密（Fernet，存在自证矛盾）改为非对称签名（Ed25519）；3) 机器指纹改为绑定宿主机 machine-id，避免 Docker 容器重建导致指纹漂移；4) 明确排除含 FastAPI 路由装饰器的模块，避免破坏 OpenAPI/依赖注入；5) 修复 Dockerfile 中 `.pyd` 在 Linux 阶段不存在、源码未被清理、`input()` 交互确认在 RUN 阶段静默失效等实操 bug；6) 澄清 Cython 未加类型标注时的真实性能/保护效果，避免预期偏差。
> **v1.2 修正摘要**: 1) 重新评估机器指纹绑定的必要性 —— 若部署场景是"内部多服务器/PC"而非"交付给不受控的外部客户"，**默认降级为轻量方案**（部署审批 + 环境变量开关），Ed25519 签名+机器指纹绑定保留作为面向外部客户场景的可选升级项，见 §3.0；2) 基于实际代码扫描核实 Cython 兼容性风险：待编译文件不涉及 `match/case`、walrus、PEP604 联合类型、`inspect.signature` 反射、pickle/多进程序列化，风险低于预期；但存在超大单文件（400KB+）触发 C 编译器限制的真实风险，新增"分阶段验证"实施策略，见 §4.7。
> **v1.3 修正摘要**（2026-07-07，用户管理模块上线后的增量评估，**不改变分层架构/主线策略**）：1) 新增 `API/user_admin_api.py`（含8处 `@router.*` 路由装饰器）纳入 `DO_NOT_COMPILE`，原理与 `sop_api.py` 等同——编译会破坏 OpenAPI/依赖注入，见 §1.5、§4.3；2) 认证/账户基础设施三个文件（`auth_middleware.py`、`user_service.py`、`user_migration_service.py`，均无路由装饰器/无 eval/exec）评估为**可选编译**，归入 P2 分组，理由和取舍见 §1.5；3) 明确结论：用户管理模块属于"认证基础设施"，不涉及本方案原定位保护的"核心风控算法IP"，**Layer2 已有编译清单（14个核心算法/报告引擎文件）无需变更**。

---

## 目录

- [1. 项目现状分析](#1-项目现状分析)
- [2. 保护目标与分层策略](#2-保护目标与分层策略)
- [3. Layer 1：入口鉴权](#3-layer-1入口鉴权)
- [4. Layer 2：Cython 核心编译](#4-layer-2cython-核心编译)
- [5. Layer 3：分发封装](#5-layer-3分发封装)
- [6. 实施路线](#6-实施路线)
- [7. 风险与注意事项](#7-风险与注意事项)
- [8. 附录](#8-附录)

---

## 1. 项目现状分析

### 1.1 项目概览

| 属性 | 值 |
|------|-----|
| 项目名 | `deepanalyze-creditwise` |
| 版本 | `1.0.0-beta.1` |
| 定位 | AI 驱动的信贷风控智能分析平台 |
| 构建系统 | Hatchling + setuptools (wheel 包) |
| 部署方式 | 源码部署 / Docker 镜像 |
| 分发现状 | 纯 Python 源码，无加密/混淆措施 |

### 1.2 技术栈

```
┌────────────────────────────────────────────────────┐
│  前端: Next.js 14 + React 18 (静态导出 output:export) │
│  后端: Python FastAPI + uvicorn                      │
│  数据: pandas, numpy, scipy, scikit-learn            │
│  风控: scorecardpy==0.1.9.7 (固定版本)               │
│  报告: openpyxl, python-docx, plotly, kaleido        │
│  LLM:  openai SDK (多供应商兼容)                     │
│  数据库: SQLAlchemy + SQLite                         │
│  容器: Docker 多阶段构建                              │
└────────────────────────────────────────────────────┘
```

### 1.3 代码规模

| 维度 | 数值 |
|------|------|
| Python 源文件 | **73 个** (API: 23 + deepanalyze: 50) |
| Python 源码总量 | **~2.8 MB** |
| 前端文件 | ~358 个 |

### 1.4 核心资产（需重点保护的文件）

| 优先级 | 文件 | 大小 | 说明 |
|:---:|------|------|------|
| ★★★ | `deepanalyze/analysis/task_SOP/rule_mining.py` | 401 KB | 规则挖掘核心算法（最大文件） |
| ★★★ | `deepanalyze/analysis/task_SOP/scorecard_development.py` | 286 KB | 评分卡开发核心算法 |
| ★★★ | `deepanalyze/analysis/excel_report.py` | 226 KB | Excel 报告生成引擎 |
| ★★☆ | `deepanalyze/analysis/word_report.py` | 144 KB | Word 报告生成引擎 |
| ★★☆ | `deepanalyze/analysis/html_report.py` | 176 KB | HTML 报告生成引擎 |
| ★★☆ | `deepanalyze/analysis/markdown_report.py` | 120 KB | Markdown 报告生成引擎 |
| ★★☆ | `deepanalyze/analysis/preprocessing.py` | 60 KB | 数据预处理引擎 |
| ★★☆ | `deepanalyze/analysis/task_SOP/executor.py` | 109 KB | SOP 执行引擎（**已核实：无 exec/eval，可安全编译**） |
| ★☆☆ | `deepanalyze/analysis/task_SOP/validators.py` | 46 KB | 规则/评分卡验证器（**含 `eval(rule_expr, safe_globals)`，真正的动态执行风险点**） |
| ★☆☆ | `API/sop_api.py` | 187 KB | SOP 任务管理 API（**含 51 处 FastAPI 路由装饰器，不建议 Cython 编译**） |
| ★☆☆ | `API/AI_analysis_prompts.py` | 135 KB | AI 分析提示词模板 |
| ★☆☆ | `API/chat_api.py` | 94 KB | Chat API 路由（**含 5 处路由装饰器，不建议编译**） |

> **审计更正说明**（2026-07-01 复核）：
> 1. 经代码扫描确认 `executor.py` **不含**任何 `exec()`/`eval()` 调用，此前的风险判定有误，现已重新分类为可编译模块。
> 2. 真正含 `eval()` 的文件是 `validators.py`（第 40 行 `eval(rule_expr, safe_globals)`），虽然通过 `safe_globals={'__builtins__': {}}` 做了部分沙箱化，但对象方法调用未受限，仍存在理论沙箱逃逸风险，应作为编译决策的重点审计对象。
> 3. `rule_mining.py` 已在源码层面完成安全加固：内部通过 `_safe_eval_rule()` 使用 `pd.eval()` 替代裸 `eval()`（源码注释标明 "Use safe rule evaluation instead of eval()"），说明该文件本身不存在动态执行风险，可直接编译。
> 4. `sop_api.py` / `chat_api.py` / `export_api.py` 含 FastAPI 路由装饰器，FastAPI 的 OpenAPI 生成和依赖注入依赖运行时函数签名反射，Cython 编译（尤其 `binding=False`）会破坏其功能，**不建议对这些文件做 Cython 编译**，详见 §4.3 `DO_NOT_COMPILE`。

### 1.5 用户管理模块新增文件评估（2026-07-07 补充，回答"新增用户管理大模块后本方案是否需要重新制定"）

> **结论先行**：**不需要重新制定/推翻本方案**。用户管理模块（账户 CRUD、SQLite 存储、CWAuth 认证、登录锁定）解决的是"认证基础设施"问题，与本方案原定位保护的"核心风控算法知识产权"（评分卡开发、规则挖掘等 §1.4 核心资产）是两类不同性质的资产，**Layer 2 已有的 14 个核心算法/报告引擎编译清单完全不受影响，无需变更**。仅需对新增文件做一次增量分类，结论如下：

| 新增/大幅扩充的文件 | 大小 | FastAPI 路由装饰器 | `eval`/`exec` | 分类结论 |
|---|---:|:---:|:---:|---|
| `API/user_admin_api.py`（批次2 Phase10 新增） | 13.7 KB | **8 处**（`/auth/*` + `/admin/users*`） | 无 | **必须归入 `DO_NOT_COMPILE`**——与 `sop_api.py`/`chat_api.py` 同理，编译会破坏 OpenAPI 生成/依赖注入 |
| `API/auth_middleware.py`（本次 CWAuth 改造 + 锁定并发修复后由 ~15KB 扩至 37.4 KB） | 37.4 KB | 0 处（是中间件类，非路由文件） | 无 | 编译**技术上安全**，但内容是认证中间件（bcrypt 密码校验、锁定阈值、CWAuth 方案实现），不属于"风控算法IP"——**评估为可选编译**，见下方取舍说明 |
| `deepanalyze/core/task_manager/user_service.py`（批次2 Phase9/10 新增） | 19.7 KB | 0 处 | 无 | 账户 CRUD 服务（bcrypt 哈希、用户名校验），非算法逻辑——**评估为可选编译** |
| `deepanalyze/core/task_manager/user_migration_service.py`（批次1 新增） | 6.9 KB | 0 处 | 无 | yaml→SQLite 迁移脚本，一次性工具属性更强——**评估为可选编译，优先级最低** |

**是否要把 `auth_middleware.py`/`user_service.py`/`user_migration_service.py` 纳入实际编译，取决于你对"认证实现细节是否算需要保密的资产"的判断**（例如：账户锁定的具体阈值/去重窗口、CWAuth 方案名、bcrypt 参数——这些泄露的后果是"更容易研究绕过认证的手法"，而非"核心算法被复制"，性质与 §1.4 的算法文件不同）。由于三者均无路由装饰器/无动态执行风险，编译**没有技术副作用**，本次修订默认将其归入 §4.2/§4.3 的 **P2 可选编译分组**（与 `AI_analysis_prompts.py` 同级），实际是否编译由你决定，不影响 Layer 2 主线的默认执行路径。

---

## 2. 保护目标与分层策略

### 2.1 保护目标

| 目标 | 描述 |
|------|------|
| **防"随手部署"** | 源码被拷贝到新机器后无法直接运行 |
| **防"源码阅读"** | 核心算法逻辑编译为二进制，无法直接阅读 |
| **防"随意复制"** | 分发产物与机器绑定，不可复制到其他服务器 |
| **不防"逆向工程"** | 无法做到绝对安全，目标是将逆向成本提升到远超重新开发的成本 |

### 2.2 三层防护架构

```
┌────────────────────────────────────────────────────┐
│                                                    │
│  Layer 1: 入口鉴权 ─ 防"顺手部署"（默认轻量方案，见 §3.0）│
│  ├─ [默认] 部署审批 + 环境变量开关                    │
│  ├─ [可选升级] 机器指纹绑定 + Ed25519 License 签名     │
│  └─ 过期时间控制                                    │
│                                                    │
│  Layer 2: 核心编译 ─ 防"源码泄漏"                    │
│  ├─ Cython .py → .pyd / .so                        │
│  ├─ 保留入口 .py 文件（可维护性）                     │
│  └─ 例外处理：动态执行模块保留明文                     │
│                                                    │
│  Layer 3: 分发封装 ─ 防"随意复制"                    │
│  ├─ Docker 编译版镜像                                │
│  ├─ 离线部署包（不包含源码）                           │
│  └─ CI/CD 自动构建流水线                             │
│                                                    │
└────────────────────────────────────────────────────┘
```

### 2.3 方案对比总览

| 方案 | 保护强度 | 性能影响 | 实施成本 | 维护成本 |
|------|:---:|:---:|:---:|:---:|
| 入口鉴权 | ★★☆☆☆ | → 无影响 | 0.5 天 | 低 |
| Cython 编译（无类型标注） | ★★★☆☆ | → 基本持平，不保证提速 | 2-3 天 | 中 |
| Nuitka 编译 | ★★★★☆ | → 持平 | 3-5 天 | 高 |
| PyArmor 加密 | ★★★☆☆ | ↓ 降低 5-15% | 1 天 | 低 |
| PyInstaller 打包 | ★★☆☆☆ | → 持平 | 1-2 天 | 中 |
| Docker 镜像 | ★★☆☆☆ | → 持平 | 0.5 天 | 低 |

> **推荐组合**: Layer 1 (Ed25519 签名) + Layer 2 (Cython) + Layer 3 → 综合保护强度 ★★★★☆（显著提高逆向门槛，非绝对不可破解）
> **性能说明**：以上 Cython 评级基于"直接编译现有 .py，不添加 `cdef` 类型标注"的现实场景 —— 该场景下 Cython 的核心价值是**混淆**而非加速，"提升 10-30%"的说法只在补充类型标注后才成立，对 401KB/286KB 级别的大文件手工加标注不现实，故本方案不将性能提升作为验收指标。

---

## 3. Layer 1：入口鉴权

### 3.0 是否需要机器指纹绑定？（决策前置，先判断再选方案）

> **结论先行**：本项目当前场景（内部多服务器/PC 部署，防止源码随意扩散）下，**机器指纹绑定大概率不是必要项**，建议默认采用轻量方案；仅当未来交付给不受你控制的外部客户/供应商时，才升级为 §3.1-§3.5 的 Ed25519 签名 + 机器指纹方案。

**判断依据**：

| 场景 | 特征 | 是否需要机器指纹绑定 |
|------|------|:---:|
| 内部治理场景（同组织多服务器/员工 PC） | 你自己能控制部署渠道，谁能拿到部署包由你决定 | ❌ 不必要 —— Cython 编译 + Docker 镜像已解决"无源码可看"，控制**分发渠道**本身即是主要防线 |
| 外部客户/供应商托管场景 | 部署包交给你无法控制的第三方基础设施运行 | ✅ 有必要，走 §3.1-§3.5 的完整方案 |

**机器指纹绑定的真实隐性成本**（决策前应纳入考量）：

```
├─ 密钥对生成与保管流程（私钥丢失 = 所有已发 license 需重新签发）
├─ 每次客户机器变更（换硬盘/云主机迁移/K8s 弹性扩容）都要走一遍
│   "获取新指纹 → 提交申请 → 重新签发" 流程
├─ Docker/K8s 多副本部署时，各 Pod 拿到的宿主机指纹需额外设计聚合策略
└─ 客户正常运维操作（比如服务器搬迁）会意外触发"授权失败"，增加支持成本
```

**默认轻量方案（推荐起点）**：

```python
# API/deploy_guard.py —— 轻量部署审批开关，替代完整机器指纹绑定
"""
不做强绑定，只做"部署需要经过你知情"的软控制。
适用于：内部多服务器/PC 部署，防止源码被随意复制运行，而非防范外部商业窃取。
"""
import os

def check_deploy_approved() -> bool:
    """
    启动时校验部署审批标记。
    你只需为每次新部署下发一个 DEPLOY_TOKEN（可以是简单的约定字符串/短期有效码），
    不涉及密钥管理、机器指纹采集等复杂度。
    """
    expected = os.environ.get("DEPLOY_APPROVAL_TOKEN_EXPECTED", "")
    actual = os.environ.get("DEPLOY_APPROVAL_TOKEN", "")
    if not expected:
        # 未配置期望值 → 视为不启用审批门槛（开发环境）
        return True
    return actual == expected
```

集成方式与 §3.3 相同（在 `create_app()` 最前面调用 `check_deploy_approved()`），**实施成本从 2-3 天降到 1-2 小时**，且不引入密钥管理、machine-id 挂载等运维负担。

**升级路径**：若未来确定要对外交付给不受控的客户，届时再启用下方 §3.1-§3.5 的完整 Ed25519 签名 + 机器指纹方案，两者可以平滑切换（`license_validator.py` 与 `deploy_guard.py` 可以并存，按 `LICENSE_PUBLIC_KEY` 是否配置自动决定走哪套逻辑）。

---

### 3.1 设计原理（完整方案 —— 面向外部客户交付场景，按需启用）

应用启动时，采集当前机器的唯一特征码，与授权文件 `license.lic` 进行**签名验证**。校验不通过则拒绝启动。

> ⚠️ **架构修正说明（2026-07-01）**：初版方案使用 `Fernet` 对称加密实现 License 校验，存在根本性缺陷 —— 对称加密要求客户端持有与签发端相同的密钥才能完成解密校验，这意味着客户端环境变量中必然存在可用于**自行签发任意 license** 的密钥，完全失去保护意义。现修正为**非对称签名方案（Ed25519）**：
> - 你保留私钥（`private_key.pem`，永不下发，仅用于签发 license）
> - 客户端仅内置公钥（`PUBLIC_KEY`，可以安全公开，只能验签、不能签发新 license）
>
> 同时，机器指纹采集方式也做了修正：原方案基于 `platform.node()` / MAC 地址等容器内部信息，在 Docker 分发场景下**每次容器重建指纹都会变化**（Docker 虚拟网卡、随机 hostname），导致合法客户被拒绝启动。修正为**优先读取挂载自宿主机的 `/etc/machine-id`**，仅在该文件不存在时才回退到进程内特征采集。

### 3.2 授权验证器（Ed25519 签名版）

```python
# API/license_validator.py
"""
机器授权验证器（非对称签名版）—— 防止源码被拷贝到未授权机器上运行

设计要点：
1. 使用 Ed25519 签名算法：私钥仅在签发端（你的安全环境）持有，
   客户端只内置公钥，公钥泄露不影响安全性（无法用公钥伪造签名）。
2. 机器指纹优先绑定宿主机 /etc/machine-id（需在 Docker 中以只读方式挂载），
   避免容器重建导致指纹漂移；本地/非容器部署回退到进程内特征采集。
"""

import base64
import hashlib
import json
import os
import platform
import socket
import uuid
from datetime import datetime
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

# 客户端内置公钥（可安全公开，仅用于验签，无法伪造新 license）
# 由 scripts/license_signer.py --genkey 生成密钥对时输出，替换为你自己的公钥
_PUBLIC_KEY_B64 = os.environ.get("LICENSE_PUBLIC_KEY", "")

_LICENSE_PATH = Path(__file__).parent.parent / "license.lic"

# Docker 部署时，需在 docker run / compose 中以只读方式挂载宿主机 machine-id：
#   -v /etc/machine-id:/etc/host-machine-id:ro
_HOST_MACHINE_ID_PATH = Path("/etc/host-machine-id")   # 容器内挂载点
_LOCAL_MACHINE_ID_PATH = Path("/etc/machine-id")        # 非容器部署（Linux）


def get_machine_fingerprint() -> str:
    """
    采集机器唯一指纹。
    优先级：宿主机挂载的 machine-id > 本机 machine-id > 进程内特征采集（回退，稳定性较弱）
    """
    for p in (_HOST_MACHINE_ID_PATH, _LOCAL_MACHINE_ID_PATH):
        if p.exists():
            raw = p.read_text().strip()
            return hashlib.sha256(raw.encode()).hexdigest()[:16]

    # 回退方案：仅适用于非 Docker 的直接部署场景，Docker 场景务必挂载 machine-id
    components = [platform.node(), socket.gethostname(), str(uuid.getnode())]
    raw = "|".join(components)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def validate_license(license_path: Path | None = None) -> bool:
    """
    验证当前机器的授权文件（签名 + 机器指纹 + 过期时间）。

    Returns:
        True: 授权有效，允许启动
        False: 授权无效、过期或签名不匹配
    """
    path = license_path or _LICENSE_PATH

    if not _PUBLIC_KEY_B64:
        # 未配置公钥 → 跳过验证（仅限开发环境，生产环境务必配置）
        return True

    if not path.exists():
        print("[LICENSE] 授权文件不存在，拒绝启动")
        return False

    try:
        raw = json.loads(path.read_text())
        payload_bytes = base64.b64decode(raw["payload"])
        signature = base64.b64decode(raw["signature"])

        public_key = Ed25519PublicKey.from_public_bytes(
            base64.b64decode(_PUBLIC_KEY_B64)
        )
        # 签名验证：只有持有私钥的签发端才能生成有效签名
        public_key.verify(signature, payload_bytes)

        payload = json.loads(payload_bytes)

        current_id = get_machine_fingerprint()
        if payload["machine_id"] != current_id:
            print(f"[LICENSE] 机器指纹不匹配: {current_id} != {payload['machine_id']}")
            return False

        expire_at = datetime.strptime(payload["expire_at"], "%Y-%m-%d")
        if datetime.now() > expire_at:
            print(f"[LICENSE] 授权已过期: {payload['expire_at']}")
            return False

        print(f"[LICENSE] 授权验证通过，有效期至 {payload['expire_at']}")
        return True

    except InvalidSignature:
        print("[LICENSE] 签名验证失败，license 文件被篡改或伪造")
        return False
    except Exception as e:
        print(f"[LICENSE] 验证异常: {e}")
        return False
```

### 3.2.1 签发端：密钥对生成 + License 签发（仅在你的安全环境运行）

```python
# scripts/license_signer.py —— 不要包含在任何分发产物中
"""
仅在签发方（你自己的安全环境）运行，用于：
1. 一次性生成 Ed25519 密钥对
2. 为客户机器签发 license.lic
"""
import base64
import json
import sys
from datetime import datetime
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

PRIVATE_KEY_PATH = Path("private_key.pem")  # 妥善保管，切勿上传/分发


def generate_keypair():
    """首次使用时生成密钥对，公钥用于配置客户端 LICENSE_PUBLIC_KEY"""
    private_key = Ed25519PrivateKey.generate()
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    PRIVATE_KEY_PATH.write_bytes(pem)

    public_key = private_key.public_key()
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    print("私钥已保存到:", PRIVATE_KEY_PATH)
    print("公钥 (配置为客户端 LICENSE_PUBLIC_KEY 环境变量):")
    print(base64.b64encode(public_bytes).decode())


def sign_license(machine_id: str, expire_date: str) -> dict:
    """为指定机器指纹签发 license"""
    private_key = Ed25519PrivateKey.from_private_bytes(
        serialization.load_pem_private_key(
            PRIVATE_KEY_PATH.read_bytes(), password=None
        ).private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    payload = {
        "machine_id": machine_id,
        "expire_at": expire_date,
        "issued_at": datetime.now().isoformat()[:10],
    }
    payload_bytes = json.dumps(payload, ensure_ascii=False).encode()
    signature = private_key.sign(payload_bytes)
    return {
        "payload": base64.b64encode(payload_bytes).decode(),
        "signature": base64.b64encode(signature).decode(),
    }


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "--genkey":
        generate_keypair()
        sys.exit(0)

    machine_id, expire = sys.argv[1], sys.argv[2]
    license_data = sign_license(machine_id, expire)
    Path("license.lic").write_text(json.dumps(license_data, ensure_ascii=False))
    print("license.lic 已生成")
```

### 3.3 集成到启动流程

在 `API/main.py` 的 `create_app()` 中添加：

```python
# API/main.py - 在 create_app() 最前面调用
from API.license_validator import validate_license

def create_app():
    # === 授权验证（最先执行）===
    if not validate_license():
        raise RuntimeError(
            "License validation failed. "
            "Please contact the vendor for a valid license file."
        )
    # ... 原有启动逻辑
```

### 3.4 授权生成流程（客户端获取机器指纹 → 签发端签发）

```bash
# 客户端（新机器）：获取机器指纹并发给你
python -c "from API.license_validator import get_machine_fingerprint; print(get_machine_fingerprint())"

# 你的安全环境：首次使用先生成密钥对（仅需一次，公钥固化到部署镜像/环境变量）
python scripts/license_signer.py --genkey

# 你的安全环境：为客户机器签发 license
python scripts/license_signer.py <客户机器指纹> 2026-12-31
# 生成 license.lic，通过安全渠道（非明文邮件）发给客户，客户放置到项目根目录
```

### 3.5 使用流程（Docker 场景）

```
                 你的安全环境                              客户服务器 (Docker)
              ┌──────────────┐                       ┌───────────────────────┐
              │ 1. 首次 --genkey │                    │ 2. docker run 时挂载    │
              │   得到 私钥/公钥  │                    │    -v /etc/machine-id: │
              │                │                     │      /etc/host-        │
              │ 3. 公钥内置到    │  部署镜像预置公钥 →   │      machine-id:ro     │
              │   LICENSE_PUBLIC │                     │                       │
              │   _KEY 环境变量  │                    │ 4. 获取容器内可见的      │
              │                │  ← 宿主机指纹 ←       │    host-machine-id 指纹 │
              │ 5. 签发 license  │                     │                        │
              │   .lic (私钥签名) │  → license.lic →    │ 6. 放置到项目根目录/     │
              └──────────────┘   挂载进容器            │    挂载点，启动时验签    │
                                                       └───────────────────────┘
```

> ⚠️ **关键**：Docker 部署时必须在 `docker run`/`docker-compose.yml` 中显式挂载宿主机 `/etc/machine-id` 到容器内的 `/etc/host-machine-id`（只读），否则会回退到容器内部特征（随容器重建而变化），导致 license 频繁失效。示例：
> ```yaml
> # docker-compose.yml
> services:
>   deepanalyze:
>     volumes:
>       - /etc/machine-id:/etc/host-machine-id:ro
> ```

---

## 4. Layer 2：Cython 核心编译

### 4.1 原理与真实效果说明

Cython 将 Python 代码编译为 C 语言，再编译为 CPython 扩展模块（`.pyd` on Windows / `.so` on Linux/macOS）。

> ⚠️ **重要澄清（避免预期偏差）**：
> - **关于性能**：若不为代码添加 `cdef`/`cpdef` 类型标注（对 401KB/286KB 这种大文件手工添加不现实），Cython 编译的实际效果**主要是混淆，而非提速**。原方案中"性能提升 10-30%"的表述仅适用于添加了类型标注的场景，未标注的直接编译版本性能提升有限甚至可忽略，请勿以此作为立项理由。
> - **关于保护强度**：Cython 编译产物比 `.pyc` 更难逆向，但**并非不可逆向**——存在针对 `.so`/`.pyd` 的字符串常量提取、控制流分析等逆向手段，专业人员仍可能还原部分业务逻辑（尤其是调用的库名、字符串常量、异常信息）。更准确的定位是"**显著提高逆向门槛和成本**"，而非"极难逆向"。

### 4.2 模块分级

| 级别 | 操作 | 模块数量 | 说明 |
|:---:|------|:---:|------|
| **编译** | `.py` → `.pyd/.so` | 14 个 | 核心算法+报告引擎（含修正后的 `executor.py`），编译为二进制 |
| **保留** | 保留 `.py` | ~9 个 | 入口文件、`__init__.py`、**含 FastAPI 路由装饰器的 API 模块**（见 §4.3 `DO_NOT_COMPILE`） |
| **待审计** | 需人工审计后决定 | 1 个 | `validators.py`（含真实 `eval()` 调用，见 §4.5 更正） |

### 4.3 编译清单（已修正）

#### 需要编译的模块（P0 + P1，已将审计通过的 executor.py 纳入）

```python
CORE_MODULES = [
    # P0: 核心风控算法（最高优先级）
    "deepanalyze/analysis/task_SOP/rule_mining.py",           # 401 KB - 已确认无 eval/exec
    "deepanalyze/analysis/task_SOP/scorecard_development.py", # 286 KB
    "deepanalyze/analysis/task_SOP/rule_mining_meta.py",      #  39 KB
    "deepanalyze/analysis/task_SOP/scorecard_meta.py",        #  31 KB
    "deepanalyze/analysis/task_SOP/executor.py",              # 109 KB - 已复核，无 eval/exec，可编译

    # P1: 报告引擎
    "deepanalyze/analysis/excel_report.py",                    # 226 KB
    "deepanalyze/analysis/html_report.py",                    # 176 KB
    "deepanalyze/analysis/word_report.py",                    # 144 KB
    "deepanalyze/analysis/markdown_report.py",                # 120 KB

    # P1: 数据分析引擎
    "deepanalyze/analysis/preprocessing.py",                  #  60 KB
    "deepanalyze/analysis/statistical_model.py",              #  17 KB
    "deepanalyze/analysis/feature_correlation.py",            #  10 KB
    "deepanalyze/analysis/iv_analysis.py",                    #   8 KB
    "deepanalyze/analysis/woe.py",                            #   8 KB
    "deepanalyze/analysis/feature_binning.py",                #   7 KB
    "deepanalyze/analysis/score_transformer.py",              #  10 KB
]
```

#### 保留明文的模块

```python
KEEP_CLEAR = [
    "API/main.py",                                    # FastAPI 启动入口
    "API/__init__.py",
    "deepanalyze/__init__.py",
    "deepanalyze/analysis/__init__.py",
    "deepanalyze/analysis/task_SOP/__init__.py",
    "deepanalyze/analysis/data_validator/__init__.py",
    "deepanalyze/core/__init__.py",
    "deepanalyze/core/task_manager/__init__.py",
    "deepanalyze/analysis/task_SOP/expert_mode/__init__.py",
]
```

#### 待审计的模块（含真实动态执行风险，需人工确认）

```python
DYNAMIC_MODULES = [
    "deepanalyze/analysis/task_SOP/validators.py",   # 46KB - 含 eval(rule_expr, safe_globals)
    # 注：executor.py 经复核不含 exec/eval，已移入 CORE_MODULES（可直接编译）
]
```

#### 不建议编译的模块（FastAPI 路由，编译会破坏运行时功能）

```python
# 原方案 OPTIONAL_MODULES 中的 API 层文件含 FastAPI 路由装饰器：
#   sop_api.py (51 处 @router.*) / chat_api.py (5 处) / export_api.py (2 处)
# FastAPI 的 OpenAPI schema 生成与依赖注入依赖 inspect.signature() 反射函数签名，
# Cython 编译（尤其 binding=False）会导致签名信息丢失，引发路由参数校验失败、
# /docs 文档生成异常等问题。因此这些文件应保留为 .py，不纳入编译范围。
# （v1.3新增）user_admin_api.py 是用户管理模块批次2 Phase10新增的路由文件（8 处
# @router.*：/auth/mode、/auth/profile、/auth/change-password、/admin/users*），
# 同理不建议编译，详见 §1.5。
DO_NOT_COMPILE = [
    "API/sop_api.py",
    "API/chat_api.py",
    "API/export_api.py",
    "API/admin_api.py",
    "API/file_api.py",
    "API/user_admin_api.py",
]
```

### 4.4 Cython 编译脚本

```python
# build_cython.py (放置于项目根目录)
"""
Cython 编译脚本
用法:
    python build_cython.py              # 编译核心模块
    python build_cython.py --all        # 编译全部模块（含待评估模块）
    python build_cython.py --dry-run    # 预览将编译的模块
    python build_cython.py --clean      # 清理所有编译产物
    python build_cython.py --replace    # 编译后用 .pyd/.so 替换 .py
"""
import os
import sys
import shutil
import argparse
from pathlib import Path
from Cython.Build import cythonize
from setuptools import Extension, setup

ROOT = Path(__file__).parent
BUILD_DIR = "build_cython"

# === 模块清单 ===

CORE_MODULES = [
    # P0: 核心风控算法
    "deepanalyze/analysis/task_SOP/rule_mining.py",
    "deepanalyze/analysis/task_SOP/scorecard_development.py",
    "deepanalyze/analysis/task_SOP/rule_mining_meta.py",
    "deepanalyze/analysis/task_SOP/scorecard_meta.py",
    "deepanalyze/analysis/task_SOP/executor.py",   # 已复核：无 exec/eval，可编译
    # P1: 报告引擎
    "deepanalyze/analysis/excel_report.py",
    "deepanalyze/analysis/html_report.py",
    "deepanalyze/analysis/word_report.py",
    "deepanalyze/analysis/markdown_report.py",
    # P1: 数据分析引擎
    "deepanalyze/analysis/preprocessing.py",
    "deepanalyze/analysis/statistical_model.py",
    "deepanalyze/analysis/feature_correlation.py",
    "deepanalyze/analysis/iv_analysis.py",
    "deepanalyze/analysis/woe.py",
    "deepanalyze/analysis/feature_binning.py",
    "deepanalyze/analysis/score_transformer.py",
    # P2: 无 FastAPI 装饰器的纯数据/模板模块，可选编译
    "API/AI_analysis_prompts.py",
    # P2（v1.3新增）: 用户管理模块的认证基础设施，无路由装饰器/无eval-exec，编译无技术
    # 副作用，但内容不属于"核心风控算法IP"，是否实际编译取决于是否将"认证实现细节"
    # 视为需要保密的资产，见 §1.5：
    "API/auth_middleware.py",
    "deepanalyze/core/task_manager/user_service.py",
    "deepanalyze/core/task_manager/user_migration_service.py",
]

# 含真实 eval() 动态执行风险，需先审计 safe_globals 沙箱是否可靠，再决定是否编译
DYNAMIC_MODULES = [
    "deepanalyze/analysis/task_SOP/validators.py",
]

# 明确不建议编译：含 FastAPI 路由装饰器，Cython 编译会破坏
# inspect.signature() 反射，导致 OpenAPI 生成/依赖注入异常
DO_NOT_COMPILE = [
    "API/sop_api.py",       # 51 处 @router.*
    "API/chat_api.py",      # 5 处 @router.*
    "API/export_api.py",    # 2 处 @router.*
    "API/admin_api.py",     # 2 处 @router.*
    "API/file_api.py",      # 6 处 @router.*
    "API/user_admin_api.py", # 8 处 @router.*（v1.3新增，用户管理模块批次2 Phase10）
]


def find_py_files(directory: str) -> list[str]:
    """递归查找目录下所有 .py 文件（返回相对路径）"""
    files = []
    d = Path(directory)
    for f in d.rglob("*.py"):
        rel = str(f.relative_to(ROOT)).replace("\\", "/")
        files.append(rel)
    return files


def build_extensions(modules: list[str]) -> None:
    """编译指定模块为 C 扩展（原地构建）"""
    extensions = []
    for mod_path in modules:
        p = Path(mod_path)
        if not p.exists():
            print(f"  ⚠ SKIP: {mod_path} (文件不存在)")
            continue

        module_name = str(p.with_suffix("")).replace("/", ".").replace("\\", ".")
        extensions.append(
            Extension(
                module_name,
                [mod_path],
                extra_compile_args=["-O2"],
            )
        )

    if not extensions:
        print("没有需要编译的模块")
        return

    print(f"\n开始编译 {len(extensions)} 个模块...\n")
    setup(
        name="deepanalyze_compiled",
        ext_modules=cythonize(
            extensions,
            language_level="3",
            build_dir=BUILD_DIR,
            compiler_directives={
                "binding": False,          # 不暴露 C 函数签名
                "embedsignature": False,   # 不嵌入 Python 函数签名
                "always_allow_keywords": True,
                "annotation_typing": False,
            },
        ),
        script_args=["build_ext", "--inplace"],
        zip_safe=False,
    )


def replace_py_files(modules: list[str]) -> None:
    """编译完成后，将原 .py 重命名为 .py.bak（.pyd/.so 自动优先加载）"""
    for mod_path in modules:
        p = Path(mod_path)
        bak = p.with_suffix(".py.bak")
        if p.exists():
            p.rename(bak)
            print(f"  ✓ BAK: {mod_path} -> {bak.name}")


def restore_py_files(modules: list[str]) -> None:
    """恢复 .py.bak → .py（用于开发调试）"""
    for mod_path in modules:
        p = Path(mod_path)
        bak = p.with_suffix(".py.bak")
        if bak.exists():
            bak.rename(p)
            print(f"  ✓ RESTORE: {bak.name} -> {mod_path}")


def clean_all() -> None:
    """清理所有编译产物"""
    import glob

    # 删除编译中间文件
    patterns = ["*.pyd", "*.so", "*.c", "*.html"]
    for pattern in patterns:
        for f in ROOT.rglob(pattern):
            f.unlink()
            print(f"  DEL: {f}")

    # 删除构建目录
    for d in [BUILD_DIR, "build"]:
        p = ROOT / d
        if p.exists() and p.is_dir():
            shutil.rmtree(p)
            print(f"  DEL: {p}/")

    # 恢复 .py.bak
    for bak in ROOT.rglob("*.py.bak"):
        py_file = bak.with_suffix("")
        if not py_file.exists():
            bak.rename(py_file)
            print(f"  RESTORE: {bak} -> {py_file}")


def print_summary(modules: list[str]) -> None:
    """打印编译预览"""
    total = 0
    for m in modules:
        p = Path(m)
        if p.exists():
            size = p.stat().st_size / 1024
            total += size
            flag = "🔴" if m in DYNAMIC_MODULES else "🟢"
            print(f"  {flag} {m} ({size:.0f} KB)")
    print(f"\n 总计: {len(modules)} 个模块, {total:.0f} KB")

    dynamic_included = any(m in modules for m in DYNAMIC_MODULES)
    if dynamic_included:
        print("\n  ⚠ 警告: 包含动态执行模块，请确保已审计 exec()/eval() 调用")


def main():
    parser = argparse.ArgumentParser(description="DeepAnalyze Cython 编译工具")
    parser.add_argument(
        "--all", action="store_true",
        help="编译核心模块 + 待审计模块（validators.py）；不会编译 DO_NOT_COMPILE 中的 FastAPI 路由文件"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="仅预览编译范围，不实际编译"
    )
    parser.add_argument(
        "--clean", action="store_true",
        help="清理所有编译产物和中间文件"
    )
    parser.add_argument(
        "--replace", action="store_true",
        help="编译后用 .pyd/.so 替换原 .py 文件"
    )
    parser.add_argument(
        "--restore", action="store_true",
        help="恢复 .py.bak -> .py"
    )
    parser.add_argument(
        "--yes", "-y", action="store_true",
        help="跳过交互确认，用于 CI/Docker 等非交互环境（无 stdin 时 input() 会静默判定为取消，"
             "导致 Dockerfile 中 RUN python build_cython.py 看似成功但实际未编译任何模块）"
    )
    args = parser.parse_args()

    # 处理清理/恢复操作
    if args.clean:
        print("清理所有编译产物...")
        clean_all()
        return

    # 确定编译范围（DO_NOT_COMPILE 中的 FastAPI 路由文件永远不会被加入，无 CLI 开关可绕过）
    modules = CORE_MODULES.copy()
    if args.all:
        modules += DYNAMIC_MODULES

    if args.restore:
        print("恢复 .py 源文件...")
        restore_py_files(modules)
        return

    if args.dry_run:
        print(f"=== 编译预览 ({len(modules)} 个模块) ===\n")
        print_summary(modules)
        return

    print(f"=== DeepAnalyze Cython 编译 ({len(modules)} 个模块) ===\n")
    print_summary(modules)

    # 确认
    if not args.all:
        excluded = [m for m in DYNAMIC_MODULES if m not in modules]
        if excluded:
            print(f"\n未包含 {len(excluded)} 个模块 (使用 --all 编译，仍需先完成 eval() 沙箱审计):")
            for m in excluded:
                print(f"  🔴 {m}")
    print(f"\n以下模块因含 FastAPI 路由装饰器，任何模式下都不会被编译: {len(DO_NOT_COMPILE)} 个")

    confirm = "y" if args.yes else input("\n确认编译? [y/N] ")
    if confirm.lower() != "y":
        print("已取消")
        return

    # 执行编译
    build_extensions(modules)

    # 可选：替换源文件
    if args.replace:
        replace_py_files(modules)
        print("\n✓ 源码已替换为编译产物")
    else:
        print("\n✓ 编译完成（源文件保留）")
        print("  提示: 使用 --replace 参数可将 .py 替换为编译产物")


if __name__ == "__main__":
    main()
```

### 4.5 validators.py 动态执行审计（已更正审计对象）

已通过 `rg -n "exec\(|eval\(" deepanalyze/analysis/task_SOP/executor.py` 复核，`executor.py` **不含** 任何 exec/eval 调用，已移入可编译清单。真正需要审计的是 `validators.py`：

```bash
rg -n "eval\(" deepanalyze/analysis/task_SOP/validators.py
# 命中: validators.py:40  result = eval(rule_expr, safe_globals)
# safe_globals = {'__builtins__': {}, 'df': df, 'pd': pd, 'np': np}
```

**审计结论**：`rule_expr` 来自评分卡/规则 JSON 配置（非用户直接输入的自由文本），且 `__builtins__` 已清空，风险主要来自"对象方法链沙箱逃逸"（如通过 `df.__class__.__mro__[...]` 等经典技巧访问受限对象），概率较低但存在理论可能。

**处理策略**：

| 场景 | 处理方式 |
|------|----------|
| `rule_expr` 仅来自内部生成/配置文件，不接受终端用户直接输入 | ✅ 风险可接受，可编译（Cython 编译不改变 `eval()` 本身的运行时行为，只是把调用它的字节码变成 C 代码） |
| `rule_expr` 存在任何来自前端用户输入的路径 | ❌ 应先将 `eval()` 替换为 `ast.literal_eval` 或表达式白名单解析器（类似 `rule_mining.py` 已做的 `_safe_eval_rule` 改造），而不是依赖 Cython 编译掩盖问题 |

> 💡 需要强调：**Cython 编译本身不会修复 `eval()` 的安全问题**，它只是让"调用 eval 的代码"更难被阅读，不改变 `eval()` 执行时的沙箱逃逸风险。若 `validators.py` 存在用户输入路径，应在代码层面修复（参考 `rule_mining.py` 的 `_safe_eval_rule` 模式），而非仅通过编译掩盖。

### 4.6 环境要求

| 系统 | 编译器 | 安装 |
|------|--------|------|
| **Windows** | Visual Studio Build Tools (MSVC) | `winget install Microsoft.VisualStudio.2022.BuildTools` |
| **Linux** | GCC | `apt install build-essential python3-dev` |
| **macOS** | Xcode CLT | `xcode-select --install` |

安装 Cython：

```bash
pip install cython
```

### 4.7 兼容性核实结果与分阶段验证策略

#### 4.7.1 已核实：不构成风险的兼容性陷阱

对 `CORE_MODULES` 清单中的文件做了实际代码扫描，排除了以下常见 Cython 兼容性陷阱：

| 检查项 | 结果 | 影响 |
|--------|:---:|------|
| PEP 604 联合类型语法 `X \| Y` | 0 处 | 代码用 `Optional[X]`/`Union`，兼容性好 |
| `match/case` 语句 | 0 处 | 无需担心新语法支持问题 |
| walrus 操作符 `:=` | 0 处 | 同上 |
| `inspect.signature()` / `functools.wraps` 反射 | 0 处（deepanalyze/ 目录） | `binding=False` 不会破坏这些模块自身的运行时反射逻辑 |
| `pickle`/`joblib`/`multiprocessing` 序列化 | 0 处 | 排除"Cython 扩展类型无法被序列化/跨进程传递"的经典陷阱 |
| 测试中 `mock.patch(...)`（如 `test_llm_pipeline_integration.py` 对 `executor.SOPExecutor`） | 存在但未用 `autospec=True` | 属于模块级属性替换，Cython 编译后的模块字典机制与普通 Python 模块一致，一般仍可正常工作 |

#### 4.7.2 真实存在、需要处理的风险

| 风险 | 说明 | 应对 |
|------|------|------|
| **超大单文件触及 C 编译器限制** | `rule_mining.py`（401KB）、`scorecard_development.py`（286KB）转译后的 `.c` 文件可能膨胀到 1-4MB，曾有社区反馈此量级文件会导致 MSVC 报 `C1076 内部堆限制`，或 GCC 编译耗时暴涨至十几分钟、内存占用飙升数 GB | 采用下方 §4.7.3 分阶段验证，若编译失败/超时，考虑先拆分该文件为多个子模块 |
| **`@dataclass`/`Enum`/`__slots__` 大量使用**（18/22 个待编译文件涉及） | Cython 在 `annotation_typing=True`（默认值）时可能把 dataclass 字段类型注解误判为 `cdef` 声明，导致字段异常 | 编译脚本已设置 `annotation_typing: False`（见 §4.4），需在编译后针对性跑一遍涉及 dataclass 的单测确认 |
| **便携式开发环境可能缺少 C 编译器** | 当前 `portable-dev-env` 是便携式 Python 环境，未必预装 MSVC/GCC | 需按 §4.6 单独安装编译工具链，或统一在 Docker（Linux + GCC）里完成编译，避免在本机便携环境折腾 MSVC |

#### 4.7.3 分阶段验证策略（不要一次性全量编译）

```
第一步（试点）：先编译 1 个中等体量、无 dataclass 的文件（如 woe.py，8KB）
                验证：能否正常编译、正常 import、pytest 通过
                命令：python build_cython.py --dry-run  # 先确认范围
                     （临时修改 CORE_MODULES 只保留 woe.py 试跑一次）

第二步（验证大文件）：单独试编译 rule_mining.py（401KB，清单中最大文件）
                重点观察：编译耗时是否异常（>5 分钟需警惕）、
                         是否报编译器堆内存/内部限制错误
                若失败 → 将该文件拆分为 2-3 个子模块后再编译，
                         不要强行调整编译器参数掩盖问题

第三步（批量）：试点通过后，按 P0 → P1 顺序批量编译剩余文件

第四步（CI 强制关卡）：在 CI 中加入以下步骤，任何一步失败即阻断发布
    1. python build_cython.py --yes --replace
    2. python -c "import deepanalyze.analysis.task_SOP.rule_mining"  # 全量 import 烟雾测试
    3. pytest tests/ -x                                              # 全量测试，失败即停
```

> 💡 分阶段验证的核心价值：把"编译失败/兼容性问题"的发现时机从"生产部署后"提前到"CI 流水线里"，避免一次性编译 14 个文件后才发现某个大文件编译失败，导致整体排期不可控。

---

## 5. Layer 3：分发封装

### 5.1 方案 A：Docker 编译版镜像（推荐）

#### 5.1.1 多阶段 Dockerfile

```dockerfile
# docker/Dockerfile.compiled
# === Stage 1: Cython 编译阶段 ===
FROM python:3.12-slim AS compiler
WORKDIR /build

RUN pip install --no-cache-dir cython numpy

# 只复制需要编译的模块
COPY deepanalyze/analysis/task_SOP/ /build/deepanalyze/analysis/task_SOP/
COPY deepanalyze/analysis/excel_report.py /build/deepanalyze/analysis/
COPY deepanalyze/analysis/html_report.py /build/deepanalyze/analysis/
COPY deepanalyze/analysis/word_report.py /build/deepanalyze/analysis/
COPY deepanalyze/analysis/markdown_report.py /build/deepanalyze/analysis/
COPY deepanalyze/analysis/preprocessing.py /build/deepanalyze/analysis/
COPY deepanalyze/analysis/statistical_model.py /build/deepanalyze/analysis/
COPY deepanalyze/analysis/feature_correlation.py /build/deepanalyze/analysis/
COPY deepanalyze/analysis/iv_analysis.py /build/deepanalyze/analysis/
COPY deepanalyze/analysis/woe.py /build/deepanalyze/analysis/
COPY deepanalyze/analysis/feature_binning.py /build/deepanalyze/analysis/
COPY deepanalyze/analysis/score_transformer.py /build/deepanalyze/analysis/
COPY deepanalyze/analysis/__init__.py /build/deepanalyze/analysis/
COPY deepanalyze/__init__.py /build/deepanalyze/
COPY build_cython.py /build/

# 必须带 --yes（非交互环境）+ --replace（确保 .py 不留在 build 产物目录中）
RUN python build_cython.py --yes --replace

# === Stage 2: 前端构建阶段 ===
FROM node:18-slim AS frontend-builder
WORKDIR /frontend

COPY demo/chat/package.json demo/chat/package-lock.json ./
RUN npm ci

COPY demo/chat/ ./
RUN npm run build

# === Stage 3: LLM Manager 前端构建 ===
FROM node:18-slim AS llm-manager-builder
WORKDIR /frontend

COPY llm_manager_integrated/frontend/package.json ./
RUN npm install

COPY llm_manager_integrated/frontend/ ./
RUN npm run build

# === Stage 4: 运行时镜像 ===
FROM python:3.12-slim AS runtime
WORKDIR /app

# 系统依赖（kaleido 渲染 + 中文字体）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    fonts-wqy-zenhei \
    fonts-wqy-microhei \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 复制编译产物（compiler 阶段基于 Linux 镜像，只会产生 .so，不会产生 .pyd；
# 若需要为 Windows 目标环境构建，需在 Windows 编译环境单独执行 build_cython.py 并复制 .pyd，
# 不能在本 Linux Docker 阶段内一并处理）
COPY --from=compiler /build/deepanalyze/analysis/*.so /app/deepanalyze/analysis/
COPY --from=compiler /build/deepanalyze/analysis/task_SOP/*.so /app/deepanalyze/analysis/task_SOP/

# 复制 API 层、配置文件等（不含核心算法源码）
COPY API/ /app/API/
COPY deepanalyze/ /app/deepanalyze/
COPY deepanalyze/core/ /app/deepanalyze/core/
COPY config/ /app/config/
COPY llm_manager_integrated/ /app/llm_manager_integrated/
COPY pyproject.toml setup.py /app/

# ⚠️ 关键修正：上面 `COPY deepanalyze/ /app/deepanalyze/` 会把构建上下文中的原始
# .py 源码（包括已被编译的 rule_mining.py 等）一并复制进镜像，与前面复制的 .so
# 同目录共存 —— Python 会优先加载 .so，但 .py 源码仍原样留在镜像里，任何人
# `docker exec` 进容器即可直接读取，完全达不到保护目的。必须显式删除已编译模块
# 对应的源码文件：
RUN python - <<'EOF'
import os
compiled = [
    "deepanalyze/analysis/task_SOP/rule_mining.py",
    "deepanalyze/analysis/task_SOP/scorecard_development.py",
    "deepanalyze/analysis/task_SOP/rule_mining_meta.py",
    "deepanalyze/analysis/task_SOP/scorecard_meta.py",
    "deepanalyze/analysis/task_SOP/executor.py",
    "deepanalyze/analysis/excel_report.py",
    "deepanalyze/analysis/html_report.py",
    "deepanalyze/analysis/word_report.py",
    "deepanalyze/analysis/markdown_report.py",
    "deepanalyze/analysis/preprocessing.py",
    "deepanalyze/analysis/statistical_model.py",
    "deepanalyze/analysis/feature_correlation.py",
    "deepanalyze/analysis/iv_analysis.py",
    "deepanalyze/analysis/woe.py",
    "deepanalyze/analysis/feature_binning.py",
    "deepanalyze/analysis/score_transformer.py",
]
for f in compiled:
    p = os.path.join("/app", f)
    if os.path.exists(p):
        os.remove(p)
        print(f"removed source: {p}")
EOF

# 复制前端构建产物
COPY --from=frontend-builder /frontend/dist/ /app/demo/chat/dist/
COPY --from=llm-manager-builder /frontend/dist/ /app/llm_manager_integrated/static/

# 清理源码（保留 .pyd/.so + 必要的 .py）
RUN find /app -name "*.pyc" -delete \
    && find /app -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

EXPOSE 8200
CMD ["python", "-m", "uvicorn", "API.main:app", "--host", "0.0.0.0", "--port", "8200"]
```

#### 5.1.2 构建命令

```bash
# 构建编译版镜像
docker build -f docker/Dockerfile.compiled -t deepanalyze:protected .

# 导出镜像（用于离线分发）
docker save deepanalyze:protected | gzip > deepanalyze_protected.tar.gz

# 客户侧加载
docker load < deepanalyze_protected.tar.gz
docker run -d -p 8200:8200 --name deepanalyze deepanalyze:protected
```

### 5.2 方案 B：离线部署包

#### 5.2.1 打包脚本

```bash
#!/bin/bash
# scripts/package_protected.sh
# 制作受保护的离线部署包

set -e

PACKAGE_DIR="deploy_package_$(date +%Y%m%d)"
PACKAGE_TAR="${PACKAGE_DIR}.tar.gz"

echo "=== 制作受保护部署包 ==="

# Step 1: Cython 编译
echo "[1/5] 编译核心模块..."
python build_cython.py --yes --replace

# Step 2: 创建部署目录
echo "[2/5] 创建部署目录结构..."
mkdir -p "${PACKAGE_DIR}"/{app,frontend,static,scripts,config}

# Step 3: 复制编译产物（仅 .pyd/.so + 必要的 .py 入口文件）
echo "[3/5] 复制编译产物..."
cp -r deepanalyze/analysis/*.so "${PACKAGE_DIR}/app/" 2>/dev/null || \
cp -r deepanalyze/analysis/*.pyd "${PACKAGE_DIR}/app/" 2>/dev/null || true

# 复制入口文件
cp API/main.py "${PACKAGE_DIR}/app/"
cp API/__init__.py "${PACKAGE_DIR}/app/"
# ... 复制其他保留 .py 文件

# Step 4: 复制前端静态文件
echo "[4/5] 复制前端..."
cp -r demo/chat/dist/ "${PACKAGE_DIR}/frontend/"

# Step 5: 打包
echo "[5/5] 打包..."
tar -czf "${PACKAGE_TAR}" "${PACKAGE_DIR}/"

echo "✓ 部署包已生成: ${PACKAGE_TAR}"
echo "  大小: $(du -h ${PACKAGE_TAR} | cut -f1)"

# 清理
rm -rf "${PACKAGE_DIR}"
```

### 5.3 CI/CD 集成

```yaml
# .github/workflows/build-protected.yml (示例)
name: Build Protected Image

on:
  workflow_dispatch:
    inputs:
      version:
        description: '版本号'
        required: true

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build Docker Image
        run: |
          docker build -f docker/Dockerfile.compiled \
            -t ghcr.io/your-org/deepanalyze:${{ inputs.version }}-protected .

      - name: Push to Registry
        run: |
          docker push ghcr.io/your-org/deepanalyze:${{ inputs.version }}-protected
```

---

## 6. 实施路线

### 6.1 时间线（v1.2：默认轻量 Layer 1 + 分阶段编译）

```
第 1 天 (0.5 天，默认路径)
├─ [✓] 实现 API/deploy_guard.py（轻量部署审批开关，见 §3.0）
├─ [✓] 在 API/main.py 集成 check_deploy_approved()
├─ [ ] （可选，仅面向外部客户场景）实现 Ed25519 版 license_validator.py，见 §3.1-§3.5
└─ [✓] 审计 validators.py 中的 eval() 沙箱是否存在用户输入路径

第 2 天 (0.5 天，Cython 试点)
├─ [✓] 安装 Cython + 编译工具链（建议直接在 Docker/Linux 环境完成，规避 Windows MSVC 配置）
├─ [✓] 试点编译 1 个小文件（woe.py）验证工具链可用
├─ [✓] 试点编译最大文件 rule_mining.py，观察耗时/内存/编译器报错（见 §4.7.3）
└─ [ ] 若大文件编译失败 → 评估拆分方案，此项可能增加 0.5-1 天

第 3-4 天 (1.5-2 天，批量编译)
├─ [✓] 编译 P0 模块（rule_mining + scorecard_development + executor）
├─ [✓] 编译 P1 模块（报告引擎 + 数据分析引擎）
├─ [✓] CI 中加入全量 import 烟雾测试 + pytest 全跑（见 §4.7.3 第四步）
├─ [✓] 修复编译兼容性问题
└─ [✓] 性能基准测试（如实记录：未加类型标注时性能提升可能不明显）

第 5 天 (1 天)
├─ [✓] 改造 Dockerfile → 编译版镜像
├─ [✓] 构建最终镜像
├─ [✓] 端到端功能验证
├─ [✓] 编写部署文档
└─ [✓] 清理开发环境中的编译产物
```

### 6.2 验收标准

| 测试项 | 标准 |
|--------|------|
| **功能完整性** | 所有现有 pytest 测试通过 |
| **授权验证（默认轻量方案）** | 无 `DEPLOY_APPROVAL_TOKEN` 或不匹配 → 拒绝启动 |
| **授权验证（可选完整方案，面向外部客户时）** | 无 license.lic → 拒绝启动；过期/机器指纹不匹配/签名被篡改 → 均拒绝启动 |
| **编译验证** | 核心 .py 文件已被 .pyd/.so 替代，且构建产物中不再残留对应源码（验证 `find /app -name "rule_mining.py"` 为空） |
| **编译稳定性** | 401KB/286KB 大文件试点编译能在合理时间内（建议 <5 分钟）成功完成，无编译器堆内存报错 |
| **性能基准** | API 响应时间无明显衰退（未加类型标注的 Cython 编译不保证提速，只需确认不劣化） |
| **Docker 验证** | `docker run` 可正常启动，前端可访问，FastAPI `/docs` 页面正常渲染（验证 API 层未被误编译） |
| **回滚能力** | `python build_cython.py --clean` 可恢复开发环境 |

### 6.3 回滚方案

```bash
# 如编译后出现问题，一键回滚
python build_cython.py --clean     # 清理编译产物，恢复 .py 文件
git checkout .                      # 恢复原始源码
```

---

## 7. 风险与注意事项

### 7.1 技术风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| **Cython 版本兼容性** | 编译产物绑定特定 Python 版本（如 3.12） | 对齐目标部署环境的 Python 版本 |
| **超大单文件触及 C 编译器限制**（新增，v1.2） | 401KB/286KB 文件转译后可能导致 MSVC/GCC 报堆内存/内部限制错误，或编译耗时暴涨 | 采用 §4.7.3 分阶段验证策略，先试点大文件，失败则拆分 |
| **C 扩展冲突** | `scorecardpy`、`numpy` 等 C 扩展可能冲突 | 第三方库不编译，只编译自有代码 |
| **eval() 沙箱逃逸（validators.py）** | Cython 编译不会修复 `eval()` 本身的安全问题 | 需在代码层面审计/加固 `safe_globals` 沙箱，而非依赖编译掩盖 |
| **FastAPI 反射依赖** | 编译 `sop_api.py` 等路由文件会破坏 OpenAPI/依赖注入 | 严格执行 `DO_NOT_COMPILE` 清单，不编译任何含 `@router.*` 的文件 |
| **性能预期偏差** | 未加类型标注的 Cython 编译主要提供混淆，不保证提速 | 验收时不以性能提升为达标条件，只需不劣化 |
| **License 对称密钥泄露风险** | 若走 §3.1 完整方案且误用对称加密，密钥泄露=保护失效 | 采用 §3.1 的 Ed25519 非对称签名方案（默认轻量方案 §3.0 不涉及此风险） |
| **容器指纹漂移**（仅适用于走完整方案时） | 容器重建导致 Docker 内机器指纹变化 | 挂载宿主机 `/etc/machine-id`，见 §3.5 |
| **Traceback 可读性** | 编译后堆栈跟踪不显示源码行号 | 开发环境保留 `.py`，部署版本另备调试工具 |
| **kaleido 硬依赖** | 图表渲染需系统级 Chromium 共享库 | Docker 镜像中预装好依赖 |

### 7.2 运营风险

| 风险 | 缓解措施 |
|------|----------|
| `DEPLOY_APPROVAL_TOKEN` 泄露（默认轻量方案） | 每次部署更换 token，不复用；仅作软控制，不承担强安全职责 |
| License 私钥泄露（仅走 §3.1 完整方案时） | 私钥仅存于签发端安全环境，使用环境变量注入公钥，不在代码仓库中存储 |
| 多客户授权管理混乱（仅走完整方案时） | 建立授权记录表，每台机器唯一 license |
| 客户机器变更导致授权失效（仅走完整方案时） | 提供 reissue 流程，旧 license 立即作废 |
| 开发/调试体验下降 | CI/CD 仅对 release 分支执行编译，开发分支保留源码 |

### 7.3 法律与合规

- ✅ 代码加密/编译系保护自有知识产权，属合法行为
- ✅ 不涉及第三方库的二次修改/重分发问题
- ⚠️ 确保编译方案不违反 `scorecardpy`、`scikit-learn` 等第三方库的 BSD/MIT 许可证
- ⚠️ 如涉及出海/出口管制，确认加密方案符合当地法规

---

## 8. 附录

### 8.1 文件清单

| 新增文件 | 用途 |
|----------|------|
| `build_cython.py` | Cython 编译脚本 |
| `API/deploy_guard.py` | **[默认]** 轻量部署审批开关（见 §3.0） |
| `API/license_validator.py` | **[可选，面向外部客户]** 机器授权验证器（Ed25519 签名验证） |
| `scripts/license_signer.py` | **[可选]** 密钥对生成 + 授权文件签发（仅在签发端使用，不随产品分发） |
| `docker/Dockerfile.compiled` | 编译版 Docker 镜像构建文件 |
| `scripts/package_protected.sh` | 离线部署包打包脚本 |
| `docs/code-protection-plan.md` | 本文档 |

### 8.2 常用命令速查

```bash
# === Cython 编译（建议按 §4.7.3 分阶段执行，不要一次性 --all）===
python build_cython.py --dry-run          # 预览编译范围
python build_cython.py --yes              # 编译核心模块（非交互）
python build_cython.py --all --yes        # 额外编译待审计模块（validators.py）
python build_cython.py --yes --replace    # 编译后用产物替换 .py
python build_cython.py --clean            # 清理所有编译产物，恢复 .py
python build_cython.py --restore          # 恢复 .py.bak → .py

# === 默认轻量部署审批（§3.0）===
export DEPLOY_APPROVAL_TOKEN_EXPECTED="<本次部署约定的 token>"   # 部署环境配置
export DEPLOY_APPROVAL_TOKEN="<发给部署方的 token>"              # 需匹配才能启动

# === 授权管理（可选，仅面向外部客户场景，在签发端安全环境执行）===
python scripts/license_signer.py --genkey                    # 首次生成密钥对
python scripts/license_signer.py <machine-id> 2026-12-31     # 为客户机器签发 license.lic

# === 客户端：获取机器指纹（仅可选完整方案需要，发给签发方）===
python -c "from API.license_validator import get_machine_fingerprint; print(get_machine_fingerprint())"

# === Docker 构建 ===
docker build -f docker/Dockerfile.compiled -t deepanalyze:protected .
docker save deepanalyze:protected | gzip > deepanalyze_protected.tar.gz

# === 测试验证（§4.7.3 CI 强制关卡）===
pytest tests/                        # 运行测试套件
python -c "from deepanalyze.analysis.task_SOP.rule_mining import *"  # 验证导入
find /app -name "rule_mining.py"     # Docker 镜像内验证源码已被清理（应无输出）
```

### 8.3 参考资料

- [Cython 官方文档](https://cython.readthedocs.io/)
- [Cython 编译指令参考](https://cython.readthedocs.io/en/latest/src/userguide/source_files_and_compilation.html)
- [cryptography Ed25519 签名](https://cryptography.io/en/latest/hazmat/primitives/asymmetric/ed25519/)
- [Python 导入机制：.pyd/.so 优先级](https://docs.python.org/3/reference/import.html)

---

> **总结**：默认方案为"轻量部署审批（§3.0） + Cython 编译核心算法（不含 FastAPI 路由，§4）+ Docker 分发（§5）"，预计 **2.5-3 天**完成实施，适用于内部多服务器/PC 部署场景。若未来需要交付给不受控的外部客户，可平滑升级为"Ed25519 签名 + 机器指纹绑定（§3.1-§3.5）"的完整方案，额外增加约 1 天工作量。**需明确认知边界**：本方案不追求"绝对不可破解"，实际效果是显著提高逆向成本（而非"极难逆向"），性能收益也非必然（未做类型标注时主要是混淆而非加速），Cython 编译大文件存在真实的编译器兼容性风险，务必按 §4.7.3 分阶段验证再批量推进。
