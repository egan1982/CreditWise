# DeepAnalyze 项目 Release 就绪可执行计划

> ⚠️ **注意**：本文档为内部开发计划，其中 pyproject.toml 模板、GitHub 仓库地址、Docker 镜像名、作者信息等内容为早期规划时基于原项目（ruc-datalab/DeepAnalyze）编写。**实际配置以项目根目录的 `pyproject.toml`、`README.md`、`LICENSE` 等文件为准**，本文档中对应内容不再逐一更新。

> 版本：v1.8  
> 日期：2026-03-04  
> 状态：发布前代码审计修复已全部完成（P0 全部完成，P1 必修全部完成，P1 建议级完成 14/16，P2 已修复 2/8）  
> 目标：完成第一个 Release (v1.0.0) 发布（含私有化部署配置）

---

## 📋 目录

1. [执行摘要](#执行摘要)
2. [当前状态评估](#当前状态评估)
3. [Release 标准定义](#release-标准定义)
4. [Phase 1: 代码准备（Week 1）](#phase-1-代码准备week-1)
5. [Phase 2: GitHub 配置（Week 1-2）](#phase-2-github-配置week-1-2)
6. [Phase 3: 质量保障（Week 2）](#phase-3-质量保障week-2)
7. [Phase 4: 发布执行（Week 2-3）](#phase-4-发布执行week-2-3)
8. [Phase 5: 发布打包配置（私有化部署）](#phase-5-发布打包配置私有化部署)
9. [检查清单](#检查清单)
10. [发布前代码审计报告](#发布前代码审计报告)
11. [Plan 审查修正记录](#plan-审查修正记录)
12. [风险与应对](#风险与应对)
13. [附录](#附录)

---

## 执行摘要

### 项目概况

| 项目 | 内容 |
|------|------|
| 项目名称 | DeepAnalyze |
| 当前版本 | 1.0.0-beta.1 (deepanalyze/__init__.py) |
| 目标版本 | v1.0.0-beta.1 (Git Tag) |
| 许可证 | MIT |
| 预计工期 | 2-3 周 |
| 关键阻塞项 | Git 仓库已初始化，待推送至 GitHub |

### 核心任务

| 优先级 | 任务 | 状态 | 工期 |
|--------|------|------|------|
| P0 | 初始化 Git 仓库 | ✅ 已完成 | 2 小时 |
| P0 | 创建 Python 包配置 | ✅ 已完成 | 4 小时 |
| P0 | 统一版本号 | ✅ 已完成 | 1 小时 |
| P1 | GitHub Actions CI/CD | ❌ 未开始 | 1 天 |
| P1 | GitHub 模板文件 | ❌ 未开始 | 1 天 |
| P1 | P1 安全审计修复（生产阻塞项） | ✅ 已完成 | 4-6 天 |
| P2 | 文档完善 | ⚠️ 部分完成 | 2 天 |
| P2 | 测试覆盖 | ⚠️ 部分完成 | 2 天 |

### 发布策略

| 策略 | 适用场景 | 工作量 | 说明 |
|------|----------|--------|------|
| **源码发布** | 开发者用户 | 2-3 周 | GitHub Release + pip install |
| **Docker 发布** | 运维部署 | +3 天 | 镜像 + compose 配置 |
| **自集成发布** | 私有化部署 | +1 周 | 嵌入式 Python + 预构建前端 |

**推荐：源码发布为主，自集成为辅**

### 发布里程碑

```
Week 1: 代码准备 + GitHub 配置
  ├─ Day 1-2: Git 初始化 + 首次提交
  ├─ Day 3-4: Python 包配置
  └─ Day 5: 版本统一 + 代码清理

Week 2: 质量保障 + 发布准备
  ├─ Day 1-2: CI/CD 配置
  ├─ Day 3: GitHub 模板
  ├─ Day 4: 测试运行
  └─ Day 5: 文档完善

Week 3: 发布执行 + 打包配置
  ├─ Day 1-2: 预发布验证
  ├─ Day 3: 创建 Release
  ├─ Day 4: 前端构建 + 端口统一
  └─ Day 5: 自集成打包（可选）
```

---

## 当前状态评估

### 已就绪项 ✅

| 类别 | 文件 | 状态 | 说明 |
|------|------|------|------|
| README.md | /README.md | ✅ | 完整，包含安装、使用、API说明 |
| LICENSE | /LICENSE | ✅ | MIT 许可证 |
| CHANGELOG.md | /CHANGELOG.md | ✅ | 详细功能更新记录 |
| CONTRIBUTION.md | /CONTRIBUTION.md | ✅ | 基本贡献指南 |
| requirements.txt | /requirements.txt | ✅ | 依赖列表完整 |
| .gitignore | /.gitignore | ✅ | 配置合理 |
| Docker 支持 | /docker/ | ✅ | Dockerfile + docker-compose.yml |
| 测试文件 | /tests/ | ⚠️ | 9 个测试文件，需验证 |
| 示例数据 | /example/ | ✅ | 案例完整 |

### 缺失项 ❌

| 类别 | 状态 | 影响 | 紧急度 |
|------|------|------|--------|
| ~~Git 仓库~~ | ✅ 已初始化（main 分支） | ~~无法版本控制~~ | ~~P0~~ |
| ~~setup.py/pyproject.toml~~ | ✅ 已创建 | ~~无法 pip 安装~~ | ~~P0~~ |
| ~~版本一致性~~ | ✅ 已统一为 1.0.0 | ~~llm_manager: 2.0.0 vs deepanalyze: 1.0.0~~ | ~~P0~~ |
| GitHub Actions | ❌ 不存在 | 无自动化 | P1 |
| GitHub 模板 | ❌ 不存在 | 贡献体验差 | P1 |
| SECURITY.md | ❌ 不存在 | 安全合规 | P2 |
| CODE_OF_CONDUCT.md | ❌ 不存在 | 社区规范 | P2 |

### 版本号现状

```python
# deepanalyze/__init__.py
__version__ = "1.0.0"

# llm_manager_integrated/__version__.py
__version__ = "1.0.0"  # ✅ 已统一

# API/main.py
API_VERSION = "1.0.0"
```

**版本号已统一为 "1.0.0"。**

---

## Release 标准定义

### Release 就绪检查表

#### 代码质量

- [ ] 所有测试通过
- [ ] 代码风格一致（PEP8）
- [ ] 无安全漏洞（依赖检查）
- [ ] 文档完整

#### 版本管理

- [ ] Git 仓库初始化
- [ ] 版本号统一
- [ ] Tag 创建
- [ ] Release Notes 编写

#### 发布物

- [ ] PyPI 包（可选）
- [ ] Docker 镜像
- [ ] GitHub Release
- [ ] 安装文档

#### 社区

- [ ] CONTRIBUTION.md
- [ ] CODE_OF_CONDUCT.md
- [ ] SECURITY.md
- [ ] Issue 模板
- [ ] PR 模板

---

## Phase 1: 代码准备（Week 1）

### Task 1.1: 初始化 Git 仓库

**工期**: 2 小时  
**负责人**: 项目负责人  
**依赖**: 无

#### 执行步骤

```bash
# 1. 进入项目目录
cd c:/Users/fjzheng/portable-dev-env/workspace/DeepAnalyze

# 2. 初始化 Git 仓库
git init

# 3. 配置 Git（如未配置）
git config user.name "Your Name"
git config user.email "your.email@example.com"

# 4. 添加所有文件（注意：检查 .gitignore 是否正确）
git add .

# 5. 首次提交
git commit -m "Initial commit: DeepAnalyze v1.0.0

- Agentic LLM for autonomous data science
- Multi-provider API support (OpenAI, DeepSeek, Claude, etc.)
- Integrated LLM Manager with Web UI
- Task SOP system for data analysis workflows
- Docker support for easy deployment"

# 6. 查看状态
git status
git log --oneline -1
```

#### 验证清单

- [ ] `git status` 显示 "nothing to commit, working tree clean"
- [ ] `git log` 显示首次提交
- [ ] `.git` 目录存在

---

### Task 1.2: 创建 Python 包配置

**工期**: 4 小时  
**负责人**: 后端开发  
**依赖**: Task 1.1

#### 方案选择

| 方案 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| setup.py | 兼容性好 | 较旧 | ⭐⭐⭐ |
| pyproject.toml | 现代标准 | 旧工具可能不支持 | ⭐⭐⭐⭐⭐ |
| 两者都有 | 最大兼容 | 维护两份 | ⭐⭐⭐⭐ |

**推荐：pyproject.toml（现代 Python 标准）**

#### 创建 pyproject.toml

```toml
# pyproject.toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "deepanalyze-creditwise"
version = "1.0.0"
description = "Agentic Large Language Models for Autonomous Data Science"
readme = "README.md"
license = {text = "MIT"}
authors = [
    {name = "Shaolei Zhang", email = "zhangshaolei@ruc.edu.cn"},
    {name = "Ju Fan", email = "fanj@ruc.edu.cn"},
]
keywords = [
    "llm",
    "data-science",
    "agent",
    "ai",
    "machine-learning",
    "autonomous",
]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "Intended Audience :: Science/Research",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
    "Topic :: Software Development :: Libraries :: Python Modules",
]
requires-python = ">=3.10"
dependencies = [
    "numpy",
    "pandas",
    "pandas-stubs",
    "scikit-learn",
    "scikit-learn-stubs",
    "seaborn",
    "matplotlib",
    "openpyxl",
    "python-docx",
    "tqdm",
    "requests",
    "websockets",
    "aiohttp",
    "httpx",
    "python-multipart",
    "uvicorn",
    "fastapi",
    "openai",
    "python-dotenv",
    "scorecardpy==0.1.9.7",
    "scipy>=1.7.0",
    "statsmodels",
    "plotly",
    "kaleido",
    "psutil",
    "requests-toolbelt",
    "sqlalchemy",
    "pydantic-settings",
    "cryptography",
]

[project.optional-dependencies]
dev = [
    "pytest",
    "pytest-asyncio",
    "black",
    "isort",
    "flake8",
    "mypy",
    "pre-commit",
]
docs = [
    "mkdocs",
    "mkdocs-material",
]

[project.urls]
Homepage = "https://github.com/ruc-datalab/DeepAnalyze"
Documentation = "https://github.com/ruc-datalab/DeepAnalyze#readme"
Repository = "https://github.com/ruc-datalab/DeepAnalyze.git"
"Bug Tracker" = "https://github.com/ruc-datalab/DeepAnalyze/issues"

[project.scripts]
deepanalyze = "API.main:main"

[tool.hatch.build.targets.wheel]
packages = ["deepanalyze", "API", "llm_manager_integrated"]

[tool.black]
line-length = 100
target-version = ['py310', 'py311', 'py312']

[tool.isort]
profile = "black"
line_length = 100

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
```

#### 创建 setup.py（向后兼容）

```python
# setup.py
# 用于向后兼容，实际配置在 pyproject.toml

from setuptools import setup, find_packages

setup(
    name="deepanalyze-creditwise",
    packages=find_packages(),
)
```

#### 验证安装

```bash
# 1. 创建虚拟环境
python -m venv test_env
source test_env/bin/activate  # Linux/Mac
test_env\Scripts\activate  # Windows

# 2. 安装包
pip install -e .

# 3. 验证导入
python -c "import deepanalyze; print(deepanalyze.__version__)"

# 4. 验证命令行
deepanalyze --help
```

#### 验证清单

- [ ] `pip install -e .` 成功
- [ ] `import deepanalyze` 成功
- [ ] `deepanalyze.__version__` 返回 "1.0.0"

---

### Task 1.3: 统一版本号

**工期**: 1 小时  
**负责人**: 后端开发  
**依赖**: Task 1.2

#### 修改文件清单

| 文件 | 当前版本 | 目标版本 | 修改内容 |
|------|----------|----------|----------|
| deepanalyze/__init__.py | 1.0.0 | 1.0.0 | ✅ 无需修改 |
| llm_manager_integrated/__version__.py | 1.0.0 | 1.0.0 | ✅ 已统一，无需修改 |
| API/main.py | 1.0.0 | 1.0.0 | ✅ 无需修改 |
| pyproject.toml | 1.0.0 | 1.0.0 | ✅ 已创建 |

#### 修改 llm_manager_integrated/__version__.py

```python
# llm_manager_integrated/__version__.py

"""版本信息"""

__version__ = "1.0.0"
__author__ = "DeepAnalyze Team"
__description__ = "LLM API Manager integrated with DeepAnalyze"
__license__ = "MIT"
```

#### 创建版本管理脚本

```python
# scripts/bump_version.py
"""版本号统一管理脚本"""

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

def update_version(new_version: str):
    """更新所有版本号"""
    
    files_to_update = [
        "deepanalyze/__init__.py",
        "llm_manager_integrated/__version__.py",
        "API/main.py",
        "pyproject.toml",
    ]
    
    for file_path in files_to_update:
        full_path = PROJECT_ROOT / file_path
        if not full_path.exists():
            print(f"⚠️ 文件不存在: {file_path}")
            continue
        
        content = full_path.read_text(encoding="utf-8")
        
        # 根据文件类型更新版本号
        if file_path.endswith(".toml"):
            # pyproject.toml: version = "x.x.x"
            new_content = re.sub(
                r'^version = "[^"]+"',
                f'version = "{new_version}"',
                content,
                flags=re.MULTILINE
            )
        else:
            # Python 文件: __version__ = "x.x.x"
            new_content = re.sub(
                r'__version__ = "[^"]+"',
                f'__version__ = "{new_version}"',
                content
            )
            # API_VERSION = "x.x.x"
            new_content = re.sub(
                r'API_VERSION = "[^"]+"',
                f'API_VERSION = "{new_version}"',
                new_content
            )
        
        full_path.write_text(new_content, encoding="utf-8")
        print(f"✅ 已更新: {file_path}")
    
    print(f"\n🎉 版本号已统一更新为: {new_version}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python scripts/bump_version.py <新版本号>")
        print("示例: python scripts/bump_version.py 1.1.0")
        sys.exit(1)
    
    new_version = sys.argv[1]
    update_version(new_version)
```

#### 验证清单

- [ ] 所有文件版本号一致
- [ ] 运行 `python scripts/bump_version.py 1.0.0` 无错误

---

### Task 1.4: 代码清理

**工期**: 2 小时  
**负责人**: 后端开发  
**依赖**: Task 1.1

#### 清理清单

| 项目 | 操作 | 说明 |
|------|------|------|
| 敏感信息 | 检查 | 确保 .env 中无真实 API Key |
| 日志文件 | 清理 | 删除 logs/ 下的敏感日志 |
| 数据库文件 | 处理 | llm_manager.db 是否应加入 .gitignore |
| 缓存文件 | 清理 | __pycache__, .pyc 文件 |
| 临时文件 | 清理 | .tmp, .temp 文件 |
| 大文件 | 检查 | 确保无 >100MB 的文件 |

#### 执行命令

```bash
# 1. 清理 Python 缓存
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
find . -type f -name "*.pyo" -delete

# 2. 检查大文件
find . -type f -size +10M -not -path "./.git/*" -ls

# 3. 检查敏感信息
grep -r "sk-" --include="*.py" --include="*.txt" --include="*.md" . 2>/dev/null | grep -v ".git"
grep -r "api_key" --include="*.py" --include="*.txt" . 2>/dev/null | grep -v ".git"

# 4. 验证 .gitignore
cat .gitignore | grep -E "(\.env|\.db|logs|__pycache__)"
```

#### 提交代码

```bash
git add pyproject.toml setup.py scripts/bump_version.py
git add llm_manager_integrated/__version__.py
git commit -m "chore: add package configuration and unify version to 1.0.0

- Add pyproject.toml for modern Python packaging
- Add setup.py for backward compatibility
- Create version management script
- Unify version numbers across all modules"
```

---

## Phase 2: GitHub 配置（Week 1-2）

### Task 2.1: 创建 GitHub 仓库

**工期**: 1 小时  
**负责人**: 项目负责人  
**依赖**: Phase 1 完成

#### 执行步骤

```bash
# 1. 在 GitHub 创建仓库（网页操作）
# 访问: https://github.com/new
# 仓库名: DeepAnalyze
# 可见性: Public

# 2. 添加远程仓库
git remote add origin https://github.com/ruc-datalab/DeepAnalyze.git

# 3. 推送代码
git branch -M main
git push -u origin main

# 4. 验证
gh repo view ruc-datalab/DeepAnalyze
```

#### 验证清单

- [ ] GitHub 仓库可访问
- [ ] 代码已推送
- [ ] README 正确渲染

---

### Task 2.2: GitHub Actions CI/CD

**工期**: 1 天  
**负责人**: DevOps  
**依赖**: Task 2.1

#### 创建 CI 工作流

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e ".[dev]"

    - name: Lint with flake8
      run: |
        flake8 deepanalyze API --count --select=E9,F63,F7,F82 --show-source --statistics
        flake8 deepanalyze API --count --exit-zero --max-complexity=10 --max-line-length=100 --statistics

    - name: Format check with black
      run: |
        black --check deepanalyze API

    - name: Type check with mypy
      run: |
        mypy deepanalyze API --ignore-missing-imports

    - name: Test with pytest
      run: |
        pytest tests/ -v --cov=deepanalyze --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        fail_ci_if_error: false
```

#### 创建 Release 工作流

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: "3.10"

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install build twine

    - name: Build package
      run: python -m build

    - name: Publish to PyPI
      env:
        TWINE_USERNAME: __token__
        TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
      run: twine upload dist/*

    - name: Create GitHub Release
      uses: softprops/action-gh-release@v1
      with:
        files: dist/*
        generate_release_notes: true
```

#### 验证清单

- [ ] CI 工作流运行成功
- [ ] 所有 Python 版本测试通过
- [ ] 代码风格检查通过

---

### Task 2.3: GitHub 模板文件

**工期**: 1 天  
**负责人**: 项目负责人  
**依赖**: Task 2.1

#### Issue 模板

```markdown
<!-- .github/ISSUE_TEMPLATE/bug_report.md -->
---
name: Bug report
about: Create a report to help us improve
title: '[BUG] '
labels: bug
assignees: ''

---

**Describe the bug**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

**Expected behavior**
A clear and concise description of what you expected to happen.

**Screenshots**
If applicable, add screenshots to help explain your problem.

**Environment (please complete the following information):**
 - OS: [e.g. Windows, Linux, macOS]
 - Python Version: [e.g. 3.8, 3.9]
 - DeepAnalyze Version: [e.g. 1.0.0]

**Additional context**
Add any other context about the problem here.
```

```markdown
<!-- .github/ISSUE_TEMPLATE/feature_request.md -->
---
name: Feature request
about: Suggest an idea for this project
title: '[FEATURE] '
labels: enhancement
assignees: ''

---

**Is your feature request related to a problem? Please describe.**
A clear and concise description of what the problem is. Ex. I'm always frustrated when [...]

**Describe the solution you'd like**
A clear and concise description of what you want to happen.

**Describe alternatives you've considered**
A clear and concise description of any alternative solutions or features you've considered.

**Additional context**
Add any other context or screenshots about the feature request here.
```

#### PR 模板

```markdown
<!-- .github/pull_request_template.md -->
## Description
Please include a summary of the change and which issue is fixed. Please also include relevant motivation and context.

Fixes # (issue)

## Type of change
Please delete options that are not relevant.

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## How Has This Been Tested?
Please describe the tests that you ran to verify your changes. Provide instructions so we can reproduce.

- [ ] Test A
- [ ] Test B

## Checklist:
- [ ] My code follows the style guidelines of this project
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
```

#### 社区文件

```markdown
<!-- CODE_OF_CONDUCT.md -->
# Contributor Covenant Code of Conduct

## Our Pledge

We as members, contributors, and leaders pledge to make participation in our
community a harassment-free experience for everyone...

[标准 Contributor Covenant 内容]
```

```markdown
<!-- SECURITY.md -->
# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

Please report security vulnerabilities to security@ruc-datalab.org.

We will acknowledge receipt within 48 hours and provide updates every 72 hours.
```

#### 验证清单

- [ ] Issue 模板可正常使用
- [ ] PR 模板自动加载
- [ ] CODE_OF_CONDUCT.md 渲染正常
- [ ] SECURITY.md 渲染正常

---

## Phase 3: 质量保障（Week 2）

### Task 3.1: 运行测试套件

**工期**: 1 天  
**负责人**: QA  
**依赖**: Phase 1

#### 执行命令

```bash
# 1. 安装测试依赖
pip install -e ".[dev]"

# 2. 运行测试
pytest tests/ -v --tb=short

# 3. 生成覆盖率报告
pytest tests/ --cov=deepanalyze --cov-report=html --cov-report=term

# 4. 检查覆盖率
# 目标: > 70% 核心模块
```

#### 测试文件清单

| 文件 | 描述 | 状态 |
|------|------|------|
| test_frontend_api_integration.py | 前端 API 集成测试 | 待验证 |
| test_llm_pipeline_integration.py | LLM Pipeline 集成测试 | 待验证 |
| test_resume_expert_mode.py | 恢复专家模式测试 | 待验证 |
| test_resume_functionality.py | 恢复功能测试 | 待验证 |
| test_resume_integration.py | 恢复集成测试 | 待验证 |
| test_rule_mining.py | 规则挖掘测试 | 待验证 |
| test_scorecard.py | 评分卡测试 | 待验证 |
| test_sop_api.py | SOP API 测试 | 待验证 |
| test_task_manager_complete.py | 任务管理器完整测试 | 待验证 |

#### 验证清单

- [ ] 所有测试通过
- [ ] 覆盖率 > 70%
- [ ] 无关键模块未覆盖

---

### Task 3.2: 代码风格检查

**工期**: 半天  
**负责人**: 后端开发  
**依赖**: Phase 1

#### 执行命令

```bash
# 1. 安装工具
pip install black isort flake8 mypy

# 2. 格式化代码
black deepanalyze/ API/ --line-length 100
isort deepanalyze/ API/ --profile black

# 3. 检查代码风格
flake8 deepanalyze/ API/ --max-line-length 100 --extend-ignore=E203,W503

# 4. 类型检查
mypy deepanalyze/ API/ --ignore-missing-imports
```

#### 验证清单

- [ ] black 检查通过
- [ ] isort 检查通过
- [ ] flake8 无错误
- [ ] mypy 无严重错误

---

### Task 3.3: 安全扫描

**工期**: 半天  
**负责人**: 安全工程师  
**依赖**: Phase 1

#### 执行命令

```bash
# 1. 安装安全扫描工具
pip install bandit safety

# 2. 扫描代码安全
bandit -r deepanalyze/ API/ -f json -o bandit-report.json

# 3. 检查依赖安全
safety check

# 4. 检查硬编码密钥
git-secrets --scan
```

#### 验证清单

- [ ] bandit 无高危漏洞
- [ ] safety 无已知漏洞依赖
- [ ] 无硬编码密钥

---

## Phase 4: 发布执行（Week 2-3）

### Task 4.1: 创建 Release Branch

**工期**: 1 小时  
**负责人**: 项目负责人  
**依赖**: Phase 3 完成

#### 执行步骤

```bash
# 1. 创建发布分支
git checkout -b release/v1.0.0

# 2. 更新版本号（如需要）
python scripts/bump_version.py 1.0.0

# 3. 更新 CHANGELOG
cat >> CHANGELOG.md << 'EOF'

## [1.0.0] - 2026-03-XX

### Added
- First stable release
- Agentic LLM for autonomous data science
- Multi-provider API support (OpenAI, DeepSeek, Claude, etc.)
- Integrated LLM Manager with Web UI
- Task SOP system for data analysis workflows
- Docker support for easy deployment

### Features
- Chat API with code execution
- SOP Task management
- File workspace management
- Model configuration management
- API logging and monitoring
EOF

# 4. 提交
git add .
git commit -m "chore: prepare for v1.0.0 release"

# 5. 合并到 main
git checkout main
git merge release/v1.0.0 --no-ff -m "Merge release v1.0.0"
git push origin main
```

---

### Task 4.2: 创建 Git Tag

**工期**: 30 分钟  
**负责人**: 项目负责人  
**依赖**: Task 4.1

#### 执行步骤

```bash
# 1. 创建标签
git tag -a v1.0.0 -m "Release v1.0.0

First stable release of DeepAnalyze.

Highlights:
- Agentic LLM for autonomous data science
- Multi-provider API support
- Integrated LLM Manager
- Task SOP system
- Docker deployment

Full changelog: https://github.com/ruc-datalab/DeepAnalyze/blob/main/CHANGELOG.md"

# 2. 推送标签
git push origin v1.0.0

# 3. 验证
git tag -l
git show v1.0.0
```

---

### Task 4.3: 创建 GitHub Release

**工期**: 1 小时  
**负责人**: 项目负责人  
**依赖**: Task 4.2

#### 执行步骤

```bash
# 使用 GitHub CLI 创建 Release
gh release create v1.0.0 \
  --title "DeepAnalyze v1.0.0" \
  --notes-file RELEASE_NOTES.md \
  --draft

# 或手动在网页创建
# 访问: https://github.com/ruc-datalab/DeepAnalyze/releases/new
```

#### Release Notes 模板

```markdown
# DeepAnalyze v1.0.0

🎉 We're excited to announce the first stable release of DeepAnalyze!

## What's New

### Core Features
- **Agentic LLM**: Autonomous data science with minimal human intervention
- **Multi-Provider Support**: OpenAI, DeepSeek, Claude, Google AI, and more
- **Integrated LLM Manager**: Web UI for API configuration and monitoring
- **Task SOP System**: Structured workflows for data analysis tasks

### APIs
- Chat API with code execution
- SOP Task management API
- File workspace management
- Model configuration API

### Deployment
- Docker support with docker-compose
- FastAPI backend with auto-generated docs
- Next.js frontend with hot reload

## Installation

### Using Docker
```bash
docker pull ruc-datalab/deepanalyze:v1.0.0
docker run -p 8200:8200 ruc-datalab/deepanalyze:v1.0.0
```

### Using pip
```bash
pip install deepanalyze==1.0.0
```

### From Source
```bash
git clone https://github.com/ruc-datalab/DeepAnalyze.git
cd DeepAnalyze
pip install -e .
```

## Quick Start

1. Set your API key:
```bash
export DEEPSEEK_API_KEY="your-api-key"
```

2. Start the server:
```bash
python -m deepanalyze
```

3. Open http://localhost:8200 in your browser

## Documentation

- [Full Documentation](https://github.com/ruc-datalab/DeepAnalyze#readme)
- [API Docs](http://localhost:8200/docs) (after starting server)
- [Contributing Guide](CONTRIBUTION.md)

## Known Issues

See [GitHub Issues](https://github.com/ruc-datalab/DeepAnalyze/issues)

## Contributors

Thanks to all contributors who made this release possible!

---

**Full Changelog**: https://github.com/ruc-datalab/DeepAnalyze/commits/v1.0.0
```

---

### Task 4.4: 发布后验证

**工期**: 半天  
**负责人**: QA  
**依赖**: Task 4.3

#### 验证清单

| 检查项 | 方法 | 期望结果 |
|--------|------|----------|
| GitHub Release | 访问 Release 页面 | 正常显示 |
| 源代码下载 | Download ZIP | 可下载解压 |
| Docker 镜像 | docker pull | 可拉取运行 |
| PyPI 包 | pip install | 可安装导入 |
| 文档链接 | 点击验证 | 全部有效 |

---

## Phase 5: 发布打包配置（私有化部署）

> **目标**: 实现项目私有化部署，UI 100% 一致 + 后端功能完整 + 干净初始状态

### 架构确认

当前架构已完全满足私有化部署需求：

```
DeepAnalyze (Port 8200)
├── / (主前端静态文件)
├── /api/* (DeepAnalyze API)
└── /llm-manager (LLM Manager 子应用)
    ├── /llm-manager/api/* (渠道/代理/日志/统计 API)
    └── /llm-manager/static/* (前端静态文件)
```

### 功能清单

| 功能模块 | 后端 API | 前端 UI | 状态 |
|----------|----------|---------|------|
| **渠道管理** | ✅ /llm-manager/api/manage/channels | ✅ 配置管理页面 | 完整 |
| **API 代理** | ✅ /llm-manager/api/proxy/* | ✅ 自动使用 | 完整 |
| **API 日志** | ✅ /llm-manager/api/manage/logs | ✅ API日志页面 | 完整 |
| **统计信息** | ✅ /llm-manager/api/manage/stats | ✅ 统计信息页面 | 完整 |
| **系统设置** | ✅ /llm-manager/api/manage/system | ✅ 系统设置页面 | 完整 |
| **模型配置** | ✅ /llm-manager/api/manage/channels/{id}/model-config | ✅ 弹窗配置 | 完整 |
| **健康检查** | ✅ /llm-manager/api/manage/channels/{id}/health-check | ✅ 测试按钮 | 完整 |

---

### Task 5.1: 前端构建配置

**工期**: 2 小时  
**负责人**: 前端开发  
**依赖**: 无

#### LLM Manager 前端构建

```javascript
// llm_manager_integrated/frontend/vite.config.js
import { defineConfig } from 'vite'

export default defineConfig({
  // 注意：当前实际配置中 base 使用默认值 '/'
  // 若需部署到子路径，取消注释下行：
  // base: '/llm-manager/',
  build: {
    outDir: '../static',
    emptyOutDir: true,
    assetsDir: 'assets',
  },
})
```

构建命令：
```bash
cd llm_manager_integrated/frontend
npm install
npm run build
# 输出到: llm_manager_integrated/static/
```

#### 主前端构建（可选）

```javascript
// demo/chat/next.config.mjs  (注意：实际文件为 .mjs 格式)
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  distDir: 'dist',
  images: { unoptimized: true },
  eslint: { ignoreDuringBuilds: true },
  typescript: { ignoreBuildErrors: true },
}
export default nextConfig
```

构建命令：
```bash
cd demo/chat
npm install
npm run build
# 输出到: demo/chat/dist/
```

---

### Task 5.2: 后端配置确认

**工期**: 1 小时  
**负责人**: 后端开发  
**依赖**: Task 5.1

当前 `API/main.py` 已正确配置，核心流程如下：

```python
# API/main.py (已有代码 - 简化示意)

# 检测运行模式
dev_mode = os.getenv("DEV_MODE", "false").lower() == "true"

# 通过 llm_manager_integrated.api.app.create_app 创建子应用
# 挂载 LLM Manager 子应用到 /llm-manager 路径
app.mount("/llm-manager", llm_manager_app)

# 注意：
# - 开发模式下，前端由 Vite（3001端口）和 Next.js dev server 分别提供
# - 生产模式下，LLM Manager 前端静态文件由 llm_manager_integrated/api/app.py 内部处理
# - 主前端（demo/chat/dist/）的静态文件分发需要在 API/main.py 中额外配置
#   目前尚未实现主前端的生产模式静态文件挂载
```

> **⚠️ 待处理**：主前端（demo/chat/dist/）在生产模式下的静态文件挂载尚未在 API/main.py 中实现，当前 dist/ 目录内容也并非 `next export` 的纯静态输出（包含 server/、cache/ 等开发构建产物），需重新执行 `npm run build` 生成正确的静态文件。

---

### Task 5.3: 环境安装与启动脚本（跨平台 A+C 组合方案）

**工期**: 4 小时  
**负责人**: 后端开发  
**依赖**: Task 5.2

#### 方案设计：A + C 组合 + 跨平台支持

| 场景 | 方案 | 说明 |
|------|------|------|
| **首次发布包** | A - 预安装依赖 | 包含 `.venv`，即开即用，体积大 (~500MB) |
| **后续更新包** | C - 分离脚本 | 不包含 `.venv`，首次启动自动安装，体积小 (~50MB) |
| **源码发布** | C - 分离脚本 | 用户运行安装脚本安装依赖 |

#### 跨平台脚本清单

| 平台 | 安装脚本 | 启动脚本 | 更新脚本 |
|------|---------|---------|---------|
| **Windows** | `install.ps1` ❌ 待创建 | `start.ps1` ✅ 已有 | `update.ps1` ❌ 待创建 |
| **Mac OS** | `install_mac.sh` ❌ 待创建 | `start_mac.sh` ❌ 待创建 | `update_mac.sh` ❌ 待创建 |
| **Linux** | `install_linux.sh` ❌ 待创建 | `start_linux.sh` ❌ 待创建 | `update_linux.sh` ❌ 待创建 |

#### 脚本职责划分

```
# Windows (PowerShell)
install.ps1       # 环境安装（创建 .venv + 安装依赖 + 构建前端）
start.ps1         # 服务启动（检查环境 → 启动服务）
update.ps1        # 更新依赖（当 requirements.txt 变化时）

# Mac OS (Bash)
install_mac.sh    # 环境安装（创建 venv + 安装依赖 + 构建前端）
start_mac.sh      # 服务启动（检查环境 → 启动服务）
update_mac.sh     # 更新依赖

# Linux (Bash)
install_linux.sh  # 环境安装（创建 venv + 安装依赖 + 构建前端）
start_linux.sh    # 服务启动（检查环境 → 启动服务）
update_linux.sh   # 更新依赖
```

---

#### install.ps1 - 环境安装脚本

```powershell
# install.ps1
# 首次运行或需要重新安装环境时执行

param(
    [switch]$Force = $false,      # 强制重新安装
    [switch]$SkipFrontend = $false  # 跳过前端构建
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$VenvPath = Join-Path $ProjectRoot ".venv"
$PythonExe = Join-Path $VenvPath "Scripts\python.exe"
$PipExe = Join-Path $VenvPath "Scripts\pip.exe"
$RequirementsFile = Join-Path $ProjectRoot "requirements.txt"

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "DeepAnalyze 环境安装" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan

# 检查是否已安装
if ((Test-Path $VenvPath) -and -not $Force) {
    Write-Host ""
    Write-Host "✓ 环境已存在: $VenvPath" -ForegroundColor Green
    Write-Host "  如需重新安装，请使用 -Force 参数" -ForegroundColor Gray
    Write-Host ""
    exit 0
}

# 如果强制重新安装，删除旧环境
if ($Force -and (Test-Path $VenvPath)) {
    Write-Host "删除旧环境..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $VenvPath
}

# 查找 Python
Write-Host ""
Write-Host "[1/4] 检查 Python 环境..." -ForegroundColor Green
$SystemPython = "python"
try {
    $pyVersion = & $SystemPython --version 2>&1
    Write-Host "✓ 使用系统 Python: $pyVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ 未找到 Python，请安装 Python 3.10+" -ForegroundColor Red
    exit 1
}

# 创建虚拟环境
Write-Host ""
Write-Host "[2/4] 创建虚拟环境..." -ForegroundColor Green
& $SystemPython -m venv $VenvPath
if (-not (Test-Path $PythonExe)) {
    Write-Host "❌ 虚拟环境创建失败" -ForegroundColor Red
    exit 1
}
Write-Host "✓ 虚拟环境创建成功" -ForegroundColor Green

# 升级 pip
Write-Host ""
Write-Host "[3/4] 安装 Python 依赖..." -ForegroundColor Green
& $PythonExe -m pip install --upgrade pip -q

# 安装依赖
if (Test-Path $RequirementsFile) {
    & $PipExe install -r $RequirementsFile
    Write-Host "✓ Python 依赖安装完成" -ForegroundColor Green
} else {
    Write-Host "⚠️ 未找到 requirements.txt" -ForegroundColor Yellow
}

# 构建前端（可选）
if (-not $SkipFrontend) {
    Write-Host ""
    Write-Host "[4/4] 构建前端..." -ForegroundColor Green
    
    # 检查 Node.js
    $NodeExe = "node"
    
    try {
        $nodeVersion = & $NodeExe --version 2>&1
        Write-Host "✓ Node.js: $nodeVersion" -ForegroundColor Green
        
        # 构建 LLM Manager 前端
        $LLMFrontendDir = Join-Path $ProjectRoot "llm_manager_integrated\frontend"
        if (Test-Path $LLMFrontendDir) {
            Write-Host "  构建 LLM Manager 前端..." -ForegroundColor Gray
            Set-Location $LLMFrontendDir
            & $NodeExe run build 2>$null
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  ✓ LLM Manager 前端构建完成" -ForegroundColor Green
            } else {
                Write-Host "  ⚠️ LLM Manager 前端构建失败（可稍后手动构建）" -ForegroundColor Yellow
            }
        }
        
        # 构建主前端（可选）
        $MainFrontendDir = Join-Path $ProjectRoot "demo\chat"
        if (Test-Path $MainFrontendDir) {
            Write-Host "  构建主前端..." -ForegroundColor Gray
            Set-Location $MainFrontendDir
            & $NodeExe run build 2>$null
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  ✓ 主前端构建完成" -ForegroundColor Green
            } else {
                Write-Host "  ⚠️ 主前端构建失败（可稍后手动构建）" -ForegroundColor Yellow
            }
        }
        
        Set-Location $ProjectRoot
    } catch {
        Write-Host "⚠️ Node.js 不可用，跳过前端构建" -ForegroundColor Yellow
        Write-Host "  如需前端功能，请安装 Node.js 后重新运行 install.ps1" -ForegroundColor Gray
    }
} else {
    Write-Host "[4/4] 跳过前端构建（使用 -SkipFrontend 参数）" -ForegroundColor Gray
}

Write-Host ""
Write-Host "===============================================" -ForegroundColor Green
Write-Host "✅ 环境安装完成！" -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Green
Write-Host ""
Write-Host "下一步:" -ForegroundColor Cyan
Write-Host "  运行 .\start.ps1 启动服务" -ForegroundColor White
Write-Host ""
```

---

#### start.ps1 - 服务启动脚本

```powershell
# start.ps1
# 日常使用：启动服务（自动检查环境）

param(
    [int]$Port = 8200,
    [string]$HostAddr = "0.0.0.0",
    [switch]$SkipEnvCheck = $false  # 跳过环境检查（快速启动）
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$VenvPath = Join-Path $ProjectRoot ".venv"
$PythonExe = Join-Path $VenvPath "Scripts\python.exe"

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "DeepAnalyze v1.0.0" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan

# 检查虚拟环境（除非跳过）
if (-not $SkipEnvCheck) {
    Write-Host ""
    Write-Host "检查环境..." -ForegroundColor Yellow
    
    if (-not (Test-Path $VenvPath)) {
        Write-Host ""
        Write-Host "❌ 环境未安装" -ForegroundColor Red
        Write-Host ""
        Write-Host "请先运行安装脚本:" -ForegroundColor Cyan
        Write-Host "  .\install.ps1" -ForegroundColor White
        Write-Host ""
        exit 1
    }
    
    if (-not (Test-Path $PythonExe)) {
        Write-Host "❌ 虚拟环境损坏，请重新安装:" -ForegroundColor Red
        Write-Host "  .\install.ps1 -Force" -ForegroundColor White
        exit 1
    }
    
    Write-Host "✓ 环境检查通过" -ForegroundColor Green
}

# 设置环境变量
$env:API_PORT = $Port
$env:API_HOST = $HostAddr
$env:DEV_MODE = "false"
$env:DATA_DIR = "$ProjectRoot\data"
$env:WORKSPACE_BASE_DIR = "$ProjectRoot\data\workspace"
$env:PYTHONUNBUFFERED = 1
$env:PYTHONPATH = "$ProjectRoot;$ProjectRoot\API"

# 创建数据目录
$dataDir = $env:DATA_DIR
$workspaceDir = $env:WORKSPACE_BASE_DIR
if (!(Test-Path $dataDir)) {
    New-Item -ItemType Directory -Path $dataDir -Force | Out-Null
    Write-Host "✓ 创建数据目录" -ForegroundColor Green
}
if (!(Test-Path $workspaceDir)) {
    New-Item -ItemType Directory -Path $workspaceDir -Force | Out-Null
    Write-Host "✓ 创建工作区目录" -ForegroundColor Green
}

# 检查是否首次启动
$dbPath = Join-Path $dataDir "llm_manager.db"
if (!(Test-Path $dbPath)) {
    Write-Host ""
    Write-Host "ℹ️  首次启动提示:" -ForegroundColor Yellow
    Write-Host "   1. 服务启动后访问 http://localhost:$Port/llm-manager" -ForegroundColor Yellow
    Write-Host "   2. 点击'新建配置'添加 LLM API" -ForegroundColor Yellow
    Write-Host "   3. 配置完成后即可使用" -ForegroundColor Yellow
}

# 启动服务
Write-Host ""
Write-Host "🚀 启动服务..." -ForegroundColor Green
Write-Host "   地址: http://$HostAddr`:$Port" -ForegroundColor Gray
Write-Host "   LLM Manager: http://$HostAddr`:$Port/llm-manager" -ForegroundColor Gray
Write-Host ""

& $PythonExe -m API.main
```

---

#### update.ps1 - 依赖更新脚本

```powershell
# update.ps1
# 当 requirements.txt 更新时运行

param(
    [switch]$RebuildFrontend = $false
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$VenvPath = Join-Path $ProjectRoot ".venv"
$PipExe = Join-Path $VenvPath "Scripts\pip.exe"
$RequirementsFile = Join-Path $ProjectRoot "requirements.txt"

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "DeepAnalyze 依赖更新" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan

# 检查环境
if (-not (Test-Path $VenvPath)) {
    Write-Host "❌ 环境未安装，请先运行 install.ps1" -ForegroundColor Red
    exit 1
}

# 更新依赖
Write-Host ""
Write-Host "更新 Python 依赖..." -ForegroundColor Green
& $PipExe install -r $RequirementsFile --upgrade
Write-Host "✓ 依赖更新完成" -ForegroundColor Green

# 可选：重新构建前端
if ($RebuildFrontend) {
    Write-Host ""
    Write-Host "重新构建前端..." -ForegroundColor Green
    # ... 前端构建逻辑
}

Write-Host ""
Write-Host "✅ 更新完成！" -ForegroundColor Green
```

---

#### Mac OS / Linux Shell 脚本设计规范

##### install_mac.sh / install_linux.sh - 环境安装脚本

```bash
#!/bin/bash
# install_mac.sh / install_linux.sh
# Mac OS / Linux 环境安装脚本

set -e  # 遇到错误立即退出

# 颜色定义（Mac 和 Linux 兼容）
if [[ "$OSTYPE" == "darwin"* ]]; then
    # Mac OS
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    CYAN='\033[0;36m'
    NC='\033[0m' # No Color
else
    # Linux
    RED='\e[0;31m'
    GREEN='\e[0;32m'
    YELLOW='\e[1;33m'
    CYAN='\e[0;36m'
    NC='\e[0m'
fi

# 参数解析
FORCE=false
SKIP_FRONTEND=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--force)
            FORCE=true
            shift
            ;;
        --skip-frontend)
            SKIP_FRONTEND=true
            shift
            ;;
        *)
            shift
            ;;
    esac
done

# 路径设置
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$PROJECT_ROOT/.venv"
REQUIREMENTS_FILE="$PROJECT_ROOT/requirements.txt"

echo -e "${CYAN}===============================================${NC}"
echo -e "${CYAN}DeepAnalyze 环境安装${NC}"
echo -e "${CYAN}===============================================${NC}"

# 检查是否已安装
if [[ -d "$VENV_PATH" && "$FORCE" == false ]]; then
    echo ""
    echo -e "${GREEN}✓ 环境已存在: $VENV_PATH${NC}"
    echo -e "${YELLOW}  如需重新安装，请使用 -f 或 --force 参数${NC}"
    echo ""
    exit 0
fi

# 强制重新安装时删除旧环境
if [[ "$FORCE" == true && -d "$VENV_PATH" ]]; then
    echo -e "${YELLOW}删除旧环境...${NC}"
    rm -rf "$VENV_PATH"
fi

# 检查 Python
echo ""
echo -e "${GREEN}[1/4] 检查 Python 环境...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ 未找到 Python3，请先安装 Python 3.10+${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1)
echo -e "${GREEN}✓ 使用系统 Python: $PYTHON_VERSION${NC}"

# 创建虚拟环境
echo ""
echo -e "${GREEN}[2/4] 创建虚拟环境...${NC}"
python3 -m venv "$VENV_PATH"
if [[ ! -f "$VENV_PATH/bin/python" ]]; then
    echo -e "${RED}❌ 虚拟环境创建失败${NC}"
    exit 1
fi
echo -e "${GREEN}✓ 虚拟环境创建成功${NC}"

# 安装依赖
echo ""
echo -e "${GREEN}[3/4] 安装 Python 依赖...${NC}"
"$VENV_PATH/bin/python" -m pip install --upgrade pip -q
if [[ -f "$REQUIREMENTS_FILE" ]]; then
    "$VENV_PATH/bin/pip" install -r "$REQUIREMENTS_FILE"
    echo -e "${GREEN}✓ Python 依赖安装完成${NC}"
else
    echo -e "${YELLOW}⚠️  未找到 requirements.txt${NC}"
fi

# 构建前端
if [[ "$SKIP_FRONTEND" == false ]]; then
    echo ""
    echo -e "${GREEN}[4/4] 构建前端...${NC}"
    
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        echo -e "${GREEN}✓ Node.js: $NODE_VERSION${NC}"
        
        # 构建 LLM Manager 前端
        LLM_FRONTEND_DIR="$PROJECT_ROOT/llm_manager_integrated/frontend"
        if [[ -d "$LLM_FRONTEND_DIR" ]]; then
            echo -e "${YELLOW}  构建 LLM Manager 前端...${NC}"
            cd "$LLM_FRONTEND_DIR"
            npm install && npm run build
            if [[ $? -eq 0 ]]; then
                echo -e "${GREEN}  ✓ LLM Manager 前端构建完成${NC}"
            else
                echo -e "${YELLOW}  ⚠️  LLM Manager 前端构建失败${NC}"
            fi
        fi
        
        # 构建主前端
        MAIN_FRONTEND_DIR="$PROJECT_ROOT/demo/chat"
        if [[ -d "$MAIN_FRONTEND_DIR" ]]; then
            echo -e "${YELLOW}  构建主前端...${NC}"
            cd "$MAIN_FRONTEND_DIR"
            npm install && npm run build
            if [[ $? -eq 0 ]]; then
                echo -e "${GREEN}  ✓ 主前端构建完成${NC}"
            else
                echo -e "${YELLOW}  ⚠️  主前端构建失败${NC}"
            fi
        fi
        
        cd "$PROJECT_ROOT"
    else
        echo -e "${YELLOW}⚠️  未找到 Node.js，跳过前端构建${NC}"
        echo -e "${YELLOW}  如需前端功能，请安装 Node.js 后重新运行 install_mac.sh${NC}"
    fi
else
    echo -e "${YELLOW}[4/4] 跳过前端构建（使用 --skip-frontend 参数）${NC}"
fi

echo ""
echo -e "${GREEN}===============================================${NC}"
echo -e "${GREEN}✅ 环境安装完成！${NC}"
echo -e "${GREEN}===============================================${NC}"
echo ""
echo -e "${CYAN}下一步:${NC}"
echo -e "  运行 ./start_mac.sh 启动服务"
echo ""
```

##### start_mac.sh / start_linux.sh - 服务启动脚本

```bash
#!/bin/bash
# start_mac.sh / start_linux.sh
# Mac OS / Linux 服务启动脚本

set -e

# 颜色定义
if [[ "$OSTYPE" == "darwin"* ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    CYAN='\033[0;36m'
    NC='\033[0m'
else
    RED='\e[0;31m'
    GREEN='\e[0;32m'
    YELLOW='\e[1;33m'
    CYAN='\e[0;36m'
    NC='\e[0m'
fi

# 默认参数
PORT=8200
HOST="0.0.0.0"
SKIP_ENV_CHECK=false

# 参数解析
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        -h|--host)
            HOST="$2"
            shift 2
            ;;
        --skip-env-check)
            SKIP_ENV_CHECK=true
            shift
            ;;
        *)
            shift
            ;;
    esac
done

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$PROJECT_ROOT/.venv"
PYTHON_EXE="$VENV_PATH/bin/python"

echo -e "${CYAN}===============================================${NC}"
echo -e "${CYAN}DeepAnalyze v1.0.0${NC}"
echo -e "${CYAN}===============================================${NC}"

# 检查虚拟环境
if [[ "$SKIP_ENV_CHECK" == false ]]; then
    echo ""
    echo -e "${YELLOW}检查环境...${NC}"
    
    if [[ ! -d "$VENV_PATH" ]]; then
        echo ""
        echo -e "${RED}❌ 环境未安装${NC}"
        echo ""
        echo -e "${CYAN}请先运行安装脚本:${NC}"
        echo -e "  ./install_mac.sh"
        echo ""
        exit 1
    fi
    
    if [[ ! -f "$PYTHON_EXE" ]]; then
        echo -e "${RED}❌ 虚拟环境损坏，请重新安装:${NC}"
        echo -e "  ./install_mac.sh -f"
        exit 1
    fi
    
    echo -e "${GREEN}✓ 环境检查通过${NC}"
fi

# 设置环境变量
export API_PORT="$PORT"
export API_HOST="$HOST"
export DEV_MODE="false"
export DATA_DIR="$PROJECT_ROOT/data"
export WORKSPACE_BASE_DIR="$PROJECT_ROOT/data/workspace"
export PYTHONUNBUFFERED=1
export PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/API"

# 创建数据目录
mkdir -p "$DATA_DIR"
mkdir -p "$WORKSPACE_BASE_DIR"

# 检查是否首次启动
DB_PATH="$DATA_DIR/llm_manager.db"
if [[ ! -f "$DB_PATH" ]]; then
    echo ""
    echo -e "${YELLOW}ℹ️  首次启动提示:${NC}"
    echo -e "   1. 服务启动后访问 http://localhost:$PORT/llm-manager"
    echo -e "   2. 点击'新建配置'添加 LLM API"
    echo -e "   3. 配置完成后即可使用"
fi

# 启动服务
echo ""
echo -e "${GREEN}🚀 启动服务...${NC}"
echo -e "   地址: http://$HOST:$PORT"
echo -e "   LLM Manager: http://$HOST:$PORT/llm-manager"
echo ""

exec "$PYTHON_EXE" -m API.main
```

##### update_mac.sh / update_linux.sh - 依赖更新脚本

```bash
#!/bin/bash
# update_mac.sh / update_linux.sh
# Mac OS / Linux 依赖更新脚本

set -e

# 颜色定义
if [[ "$OSTYPE" == "darwin"* ]]; then
    GREEN='\033[0;32m'
    CYAN='\033[0;36m'
    RED='\033[0;31m'
    NC='\033[0m'
else
    GREEN='\e[0;32m'
    CYAN='\e[0;36m'
    RED='\e[0;31m'
    NC='\e[0m'
fi

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$PROJECT_ROOT/.venv"
REQUIREMENTS_FILE="$PROJECT_ROOT/requirements.txt"

echo -e "${CYAN}===============================================${NC}"
echo -e "${CYAN}DeepAnalyze 依赖更新${NC}"
echo -e "${CYAN}===============================================${NC}"

# 检查环境
if [[ ! -d "$VENV_PATH" ]]; then
    echo -e "${RED}❌ 环境未安装，请先运行 install_mac.sh${NC}"
    exit 1
fi

# 更新依赖
echo ""
echo -e "${GREEN}更新 Python 依赖...${NC}"
"$VENV_PATH/bin/pip" install -r "$REQUIREMENTS_FILE" --upgrade
echo -e "${GREEN}✓ 依赖更新完成${NC}"

echo ""
echo -e "${GREEN}✅ 更新完成！${NC}"
```

---

### Task 5.4: 发布版排除清单

**工期**: 1 小时  
**负责人**: 后端开发  
**依赖**: Task 5.3

#### 完全排除的文件/目录

```
# 开发/测试相关
deprecated_files/
tests/
docs/
.git/
demo/chat/.next/
demo/chat/node_modules/
llm_manager_integrated/frontend/node_modules/
.venv/
__pycache__/
*.pyc
*.pyo
.pytest_cache/
.mypy_cache/

# 敏感信息
.env
.env.local
logs/
*.db
workspace/
*.log

# IDE/编辑器
.vscode/
.idea/
*.swp
*.swo
*~

# 操作系统
.DS_Store
Thumbs.db
```

#### 保留的文件/目录

```
# 核心代码
API/
deepanalyze/
llm_manager_integrated/
├── api/
├── core/
├── models/
├── static/          # LLM Manager 前端构建产物
└── ...

# 前端构建产物
demo/chat/dist/      # 主前端构建产物

# 配置
config/
pyproject.toml
setup.py
requirements.txt

# 脚本
scripts/start.ps1
scripts/bump_version.py

# 文档
LICENSE
README.md
CHANGELOG.md

# Docker
docker/
Dockerfile
docker-compose.yml
```

---

### Task 5.5: 打包脚本（支持 A+C 两种模式 + 跨平台）

**工期**: 4 小时  
**负责人**: 后端开发  
**依赖**: Task 5.4

#### 打包模式说明

| 模式 | 参数 | 包含 .venv | 体积 | 适用场景 |
|------|------|-----------|------|----------|
| **完整版 (A)** | `-Mode full` | ✅ 包含 | ~500MB | 首次发布，即开即用 |
| **精简版 (C)** | `-Mode slim` | ❌ 不包含 | ~50MB | 后续更新，自动安装 |

#### 跨平台打包支持

| 平台 | 完整版 | 精简版 | 说明 |
|------|--------|--------|------|
| **Windows** | `DeepAnalyze-v1.0.0-windows-full.zip` | `DeepAnalyze-v1.0.0-windows-slim.zip` | 含 .bat 包装器 |
| **Mac OS** | `DeepAnalyze-v1.0.0-macos-full.tar.gz` | `DeepAnalyze-v1.0.0-macos-slim.tar.gz` | 含可执行权限 |
| **Linux** | `DeepAnalyze-v1.0.0-linux-full.tar.gz` | `DeepAnalyze-v1.0.0-linux-slim.tar.gz` | 含可执行权限 |

#### package_release.ps1

```powershell
# scripts/package_release.ps1
param(
    [string]$Version = "1.0.0",
    [ValidateSet("full", "slim")]
    [string]$Mode = "slim",        # 默认精简版
    [string]$OutputDir = "dist"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path "$PSScriptRoot\.."
$ReleaseName = "DeepAnalyze-v$Version-$Mode"
$ReleaseDir = Join-Path $OutputDir $ReleaseName

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "DeepAnalyze Release Builder" -ForegroundColor Cyan
Write-Host "版本: $Version | 模式: $Mode" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan

# 清理旧构建
if (Test-Path $ReleaseDir) {
    Write-Host "清理旧构建..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $ReleaseDir
}
New-Item -ItemType Directory -Path $ReleaseDir | Out-Null

# 1. 构建前端（两种模式都需要）
Write-Host ""
Write-Host "[1/4] 构建前端..." -ForegroundColor Green

# LLM Manager 前端
$LLMFrontendDir = Join-Path $ProjectRoot "llm_manager_integrated\frontend"
if (Test-Path $LLMFrontendDir) {
    Set-Location $LLMFrontendDir
    if (!(Test-Path "node_modules")) {
        npm install
        if ($LASTEXITCODE -ne 0) { throw "npm install 失败" }
    }
    npm run build
    if ($LASTEXITCODE -ne 0) { throw "LLM Manager 前端构建失败" }
    Write-Host "✓ LLM Manager 前端构建完成" -ForegroundColor Green
}

# 主前端（可选）
$MainFrontendDir = Join-Path $ProjectRoot "demo\chat"
if (Test-Path $MainFrontendDir) {
    Set-Location $MainFrontendDir
    if (!(Test-Path "node_modules")) {
        npm install
    }
    npm run build 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ 主前端构建完成" -ForegroundColor Green
    }
}

Set-Location $ProjectRoot

# 2. 复制后端代码
Write-Host ""
Write-Host "[2/4] 复制后端代码..." -ForegroundColor Green
Copy-Item -Recurse "$ProjectRoot\API" $ReleaseDir\
Copy-Item -Recurse "$ProjectRoot\deepanalyze" $ReleaseDir\
Copy-Item -Recurse "$ProjectRoot\llm_manager_integrated" $ReleaseDir\
Copy-Item "$ProjectRoot\requirements.txt" $ReleaseDir\
Copy-Item "$ProjectRoot\LICENSE" $ReleaseDir\
Copy-Item "$ProjectRoot\README.md" $ReleaseDir\
Copy-Item "$ProjectRoot\CHANGELOG.md" $ReleaseDir\

# 排除开发文件
$ExcludeDirs = @("frontend", "__pycache__", ".pytest_cache", "node_modules", ".next")
foreach ($dir in $ExcludeDirs) {
    Get-ChildItem -Path $ReleaseDir -Recurse -Filter $dir -Directory -ErrorAction SilentlyContinue | 
        Remove-Item -Recurse -Force
}
Write-Host "✓ 后端代码复制完成" -ForegroundColor Green

# 3. 处理虚拟环境（根据模式）
Write-Host ""
Write-Host "[3/4] 处理虚拟环境..." -ForegroundColor Green

if ($Mode -eq "full") {
    # 完整版：预安装依赖
    Write-Host "模式: 完整版（预安装依赖）" -ForegroundColor Cyan
    
    $VenvPath = Join-Path $ReleaseDir ".venv"
    $PythonExe = "python"
    
    # 创建虚拟环境
    Write-Host "  创建虚拟环境..." -ForegroundColor Gray
    & $PythonExe -m venv $VenvPath
    
    # 安装依赖
    $ReleasePip = Join-Path $VenvPath "Scripts\pip.exe"
    Write-Host "  安装依赖（可能需要几分钟）..." -ForegroundColor Gray
    & $ReleasePip install -r "$ReleaseDir\requirements.txt" -q
    
    Write-Host "✓ 虚拟环境创建并安装依赖完成" -ForegroundColor Green
    
} else {
    # 精简版：不包含 .venv，提供安装脚本
    Write-Host "模式: 精简版（首次启动自动安装）" -ForegroundColor Cyan
    Write-Host "  不包含虚拟环境，将通过 install.ps1 安装" -ForegroundColor Gray
}

# 4. 创建脚本
Write-Host ""
Write-Host "[4/4] 创建脚本..." -ForegroundColor Green

# 复制安装脚本（精简版必需，完整版可选但建议保留）
Copy-Item "$ProjectRoot\scripts\install.ps1" "$ReleaseDir\install.ps1"
Copy-Item "$ProjectRoot\scripts\start.ps1" "$ReleaseDir\start.ps1"
Copy-Item "$ProjectRoot\scripts\update.ps1" "$ReleaseDir\update.ps1"

# Windows bat 包装器
@'
@echo off
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "%~dp0start.ps1" %*
'@ | Out-File -FilePath "$ReleaseDir\start.bat" -Encoding UTF8

@'
@echo off
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
'@ | Out-File -FilePath "$ReleaseDir\install.bat" -Encoding UTF8

Write-Host "✓ 脚本创建完成" -ForegroundColor Green

# 5. 创建 README（根据模式定制）
Write-Host ""
Write-Host "创建 README..." -ForegroundColor Green

if ($Mode -eq "full") {
    @"
# DeepAnalyze v$Version (完整版)

## 快速开始

### Windows
双击运行 \\"start.bat\\" 或在 PowerShell 中运行:
```powershell
.\start.ps1
```

### Linux/Mac
```bash
chmod +x start.sh
./start.sh
```

## 访问地址

- 主界面: http://localhost:8200
- LLM Manager: http://localhost:8200/llm-manager
- API 文档: http://localhost:8200/docs

## 首次使用

1. 启动服务后访问 http://localhost:8200/llm-manager
2. 点击"新建配置"添加 LLM API
3. 配置完成后即可在主界面使用

## 数据目录

所有数据保存在 data/ 目录:
- data/llm_manager.db - LLM 配置数据库（自动创建）
- data/workspace/ - 工作区文件

## 注意事项

此为完整版，已预装所有依赖，可直接运行。
如需重新安装依赖，可运行 .\install.ps1 -Force
"@ | Out-File -FilePath "$ReleaseDir\README.md" -Encoding UTF8

} else {
    @"
# DeepAnalyze v$Version (精简版)

## 快速开始

### 1. 安装环境（首次使用必需）

Windows:
```powershell
.\install.ps1
# 或双击 install.bat
```

Linux/Mac:
```bash
chmod +x install.sh
./install.sh
```

### 2. 启动服务

Windows:
```powershell
.\start.ps1
# 或双击 start.bat
```

Linux/Mac:
```bash
./start.sh
```

## 访问地址

- 主界面: http://localhost:8200
- LLM Manager: http://localhost:8200/llm-manager
- API 文档: http://localhost:8200/docs

## 首次使用

1. 启动服务后访问 http://localhost:8200/llm-manager
2. 点击"新建配置"添加 LLM API
3. 配置完成后即可在主界面使用

## 数据目录

所有数据保存在 data/ 目录:
- data/llm_manager.db - LLM 配置数据库（自动创建）
- data/workspace/ - 工作区文件

## 注意事项

此为精简版，首次使用需要运行 install.ps1 安装依赖。
需要网络连接下载 Python 包。

## 更新依赖

当 requirements.txt 更新时:
```powershell
.\update.ps1
```
"@ | Out-File -FilePath "$ReleaseDir\README.md" -Encoding UTF8
}

# 完成
Write-Host ""
Write-Host "===============================================" -ForegroundColor Green
Write-Host "✅ 构建完成!" -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Green
Write-Host "输出目录: $ReleaseDir" -ForegroundColor Cyan

# 统计大小
$size = (Get-ChildItem $ReleaseDir -Recurse -ErrorAction SilentlyContinue | 
    Where-Object { !$_.PSIsContainer } | 
    Measure-Object -Property Length -Sum).Sum
Write-Host "总大小: $([math]::Round($size/1MB, 2)) MB" -ForegroundColor Gray

# 显示下一步
Write-Host ""
Write-Host "发布步骤:" -ForegroundColor Gray
if ($Mode -eq "slim") {
    Write-Host "   1. 测试安装: cd $ReleaseDir; .\install.ps1" -ForegroundColor Gray
    Write-Host "   2. 测试启动: .\start.ps1" -ForegroundColor Gray
} else {
    Write-Host "   1. 测试启动: cd $ReleaseDir; .\start.ps1" -ForegroundColor Gray
}
Write-Host "   2. 压缩: Compress-Archive $ReleaseDir $ReleaseName.zip" -ForegroundColor Gray
Write-Host "   3. 上传: 发布到 GitHub Release" -ForegroundColor Gray

Set-Location $ProjectRoot
```

#### 使用示例

```powershell
# 构建精简版（默认，~50MB）
.\scripts\package_release.ps1 -Version "1.0.0"

# 构建完整版（~500MB）
.\scripts\package_release.ps1 -Version "1.0.0" -Mode full

# 构建两个版本
.\scripts\package_release.ps1 -Version "1.0.0" -Mode full
.\scripts\package_release.ps1 -Version "1.0.0" -Mode slim
```

---

### Task 5.6: Docker 生产部署方案

**工期**: 3 小时  
**负责人**: DevOps  
**依赖**: Task 5.5

#### 现有 Docker 配置分析

当前 `docker/Dockerfile` 是基于 `nvidia/cuda:12.1.0` 的**开发环境镜像**（~3GB）：
- ✅ 包含完整的 CUDA 支持（用于 GPU 加速）
- ✅ 安装了额外的数据科学工具
- ❌ 体积过大，不适合生产部署
- ❌ 未集成前端构建产物

#### 生产级 Docker 方案

> **注意**：以下 `Dockerfile.prod` 和 `docker-compose.prod.yml` 均为设计方案，文件尚未创建。

##### 1. 生产 Dockerfile (Dockerfile.prod) — ❌ 待创建

```dockerfile
# ============================================
# DeepAnalyze Production Dockerfile
# Optimized for private deployment
# ============================================

FROM python:3.10-slim

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DEV_MODE=false \
    API_PORT=8200 \
    API_HOST=0.0.0.0

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY API/ ./API/
COPY deepanalyze/ ./deepanalyze/
COPY llm_manager_integrated/ ./llm_manager_integrated/

# 复制预构建的前端静态文件
COPY demo/chat/dist/ ./demo/chat/dist/
COPY llm_manager_integrated/static/ ./llm_manager_integrated/static/

# 创建非 root 用户
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/data/workspace && \
    chown -R appuser:appuser /app

USER appuser

# 暴露端口
EXPOSE 8200

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8200/health')" || exit 1

# 启动命令
CMD ["python", "-m", "API.main"]
```

##### 2. 生产 Docker Compose (docker-compose.prod.yml) — ❌ 待创建

```yaml
version: '3.8'

services:
  deepanalyze:
    build:
      context: ..
      dockerfile: docker/Dockerfile.prod
    image: ruc-datalab/deepanalyze:v1.0.0
    container_name: deepanalyze
    ports:
      - "8200:8200"
    environment:
      - DEV_MODE=false
      - API_PORT=8200
      - API_HOST=0.0.0.0
      - DATA_DIR=/app/data
      - WORKSPACE_BASE_DIR=/app/data/workspace
      - LOG_LEVEL=INFO
    volumes:
      - ./data:/app/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8200/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
```

##### 3. 多阶段构建 Dockerfile (Dockerfile.multi) — ❌ 待创建

```dockerfile
# ============================================
# DeepAnalyze Multi-Stage Build Dockerfile
# Minimal production image
# ============================================

# 阶段 1: 构建前端
FROM node:18-alpine AS frontend-builder

WORKDIR /build

# 构建 LLM Manager 前端
COPY llm_manager_integrated/frontend/package*.json ./llm-frontend/
COPY llm_manager_integrated/frontend/ ./llm-frontend/
RUN cd llm-frontend && npm install && npm run build

# 构建主前端
COPY demo/chat/package*.json ./main-frontend/
COPY demo/chat/ ./main-frontend/
RUN cd main-frontend && npm install && npm run build

# 阶段 2: Python 依赖缓存
FROM python:3.10-slim AS deps-builder

WORKDIR /deps
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# 阶段 3: 生产镜像
FROM python:3.10-slim AS production

ENV PYTHONUNBUFFERED=1 \
    DEV_MODE=false \
    API_PORT=8200 \
    API_HOST=0.0.0.0 \
    PATH=/root/.local/bin:$PATH

WORKDIR /app

# 从 deps-builder 复制 Python 包
COPY --from=deps-builder /root/.local /root/.local

# 复制应用代码
COPY API/ ./API/
COPY deepanalyze/ ./deepanalyze/
COPY llm_manager_integrated/api/ ./llm_manager_integrated/api/
COPY llm_manager_integrated/core/ ./llm_manager_integrated/core/
COPY llm_manager_integrated/models/ ./llm_manager_integrated/models/
COPY llm_manager_integrated/utils/ ./llm_manager_integrated/utils/

# 从前端构建阶段复制静态文件
COPY --from=frontend-builder /build/llm-frontend/dist/ ./llm_manager_integrated/static/
COPY --from=frontend-builder /build/main-frontend/dist/ ./demo/chat/dist/

# 创建数据目录
RUN mkdir -p /app/data/workspace

EXPOSE 8200

CMD ["python", "-m", "API.main"]
```

#### Docker 镜像对比

| 镜像类型 | Dockerfile | 大小 | 适用场景 |
|----------|-----------|------|----------|
| **开发环境** | `Dockerfile` | ~3GB | 开发调试，含 CUDA |
| **生产环境** | `Dockerfile.prod` | ~800MB | 私有化部署 |
| **多阶段构建** | `Dockerfile.multi` | ~500MB | 最小化部署 |

#### Docker 部署命令

```bash
# 构建生产镜像
docker build -f docker/Dockerfile.prod -t deepanalyze:v1.0.0 .

# 运行容器
docker run -d \
  -p 8200:8200 \
  -v $(pwd)/data:/app/data \
  --name deepanalyze \
  deepanalyze:v1.0.0

# 使用 Docker Compose
cd docker
docker-compose -f docker-compose.prod.yml up -d

# 查看日志
docker logs -f deepanalyze

# 停止服务
docker-compose -f docker-compose.prod.yml down
```

#### Docker 部署验证清单

- [ ] 镜像构建成功
- [ ] 容器启动正常
- [ ] 端口 8200 可访问
- [ ] LLM Manager 页面正常
- [ ] 数据卷挂载正确
- [ ] 重启后数据不丢失

---

### 私有化部署验证清单

#### 功能验证

- [ ] 启动后访问 http://localhost:8200/llm-manager 正常
- [ ] 界面与 3001 端口开发版完全一致
- [ ] 可以创建新的 LLM 配置
- [ ] 可以编辑/删除配置
- [ ] 可以测试配置连通性
- [ ] API 代理功能正常
- [ ] 日志记录正常
- [ ] 统计信息显示正常

#### 数据验证

- [ ] data/llm_manager.db 自动创建（首次启动）
- [ ] 配置持久化保存
- [ ] 重启后配置不丢失
- [ ] 数据目录可备份/恢复

---

## 检查清单

### Pre-Release Checklist

- [ ] Git 仓库初始化完成
- [ ] pyproject.toml 创建完成
- [ ] 版本号统一
- [ ] 代码清理完成
- [ ] GitHub 仓库创建
- [ ] CI/CD 配置完成
- [ ] GitHub 模板创建
- [ ] 所有测试通过
- [ ] 代码风格检查通过
- [ ] 安全扫描通过

### Release Checklist

- [ ] Release branch 创建
- [ ] CHANGELOG 更新
- [ ] Git tag 创建 (v1.0.0)
- [ ] GitHub Release 创建
- [ ] Docker 镜像构建
- [ ] PyPI 包上传（可选）
- [ ] 前端构建完成 (npm run build)
- [ ] 端口配置统一 (DEV_MODE=false)
- [ ] 发布包构建完成
- [ ] 发布公告

### 打包配置 Checklist

#### 前端构建
- [ ] demo/chat next.config.mjs 配置 output: 'export'
- [ ] demo/chat npm run build 成功
- [ ] llm_manager_integrated/frontend vite.config.js 配置 base（如部署到子路径）
- [ ] llm_manager_integrated/frontend npm run build 成功
- [ ] 静态文件路径正确

#### 后端配置
- [ ] API/main.py DEV_MODE 默认 false
- [ ] 生产环境变量配置完成
- [ ] 端口统一为 8200
- [ ] LLM Manager 静态文件挂载正确

#### 环境脚本
- [ ] install.ps1 可正常创建虚拟环境
- [ ] install.ps1 可正常安装依赖
- [ ] start.ps1 可检测环境是否安装
- [ ] start.ps1 可正常启动服务
- [ ] update.ps1 可更新依赖

#### 发布包 - 精简版 (slim)
- [ ] 不包含 .venv 目录
- [ ] 包含 install.ps1 脚本
- [ ] 首次启动提示运行 install.ps1
- [ ] 安装后可正常使用

#### 发布包 - 完整版 (full)
- [ ] 包含预装的 .venv 目录
- [ ] 可直接运行 start.ps1
- [ ] 无需网络即可启动
- [ ] 体积在可接受范围 (< 1GB)

#### Mac OS / Linux 脚本
- [ ] install_mac.sh 可正常创建虚拟环境
- [ ] install_mac.sh 可正常安装依赖
- [ ] install_linux.sh 可正常创建虚拟环境
- [ ] install_linux.sh 可正常安装依赖
- [ ] start_mac.sh 可检测环境是否安装
- [ ] start_mac.sh 可正常启动服务
- [ ] start_linux.sh 可检测环境是否安装
- [ ] start_linux.sh 可正常启动服务
- [ ] Shell 脚本具有可执行权限 (`chmod +x`)

#### Docker 部署
- [ ] Dockerfile.prod 构建成功
- [ ] 镜像大小 < 1GB
- [ ] docker-compose.prod.yml 配置正确
- [ ] 容器启动正常
- [ ] 数据卷挂载正确
- [ ] 健康检查配置有效

#### 通用检查
- [ ] 排除清单检查通过
- [ ] 敏感信息已清理
- [ ] README.md 说明清晰
- [ ] 数据目录可正常创建

### Post-Release Checklist

- [ ] 安装验证
- [ ] 功能验证
- [ ] 文档验证
- [ ] 监控 Issues

---

## 发布前代码审计报告

> 审计日期：2026-03-03  
> 审计范围：DeepAnalyze 全项目（API/、deepanalyze/、llm_manager_integrated/、demo/）  
> 审计方式：静态代码分析 + 人工确认

### 审计总览

| 等级 | 总数 | 已修复 | 降级/误报 | 待处理 |
|------|------|--------|-----------|--------|
| P0（阻断级） | 9 | 5 | 4 | 0 |
| P1（高优先级） | 41 | 22 | 0 | 19（私有化跳过/架构重构暂缓） |

### P0 问题清单

#### P0-1: 路径遍历漏洞 — 文件上传/下载未校验路径

- **位置**: `API/main.py` 文件管理相关路由
- **成因**: 文件操作接口未对用户传入的文件路径做 `..` 遍历校验，攻击者可构造路径读写工作区之外的文件
- **修复**: 添加路径规范化校验（`resolve()` + `parents`），确保所有文件操作路径在 `WORKSPACE_BASE_DIR` 范围内
- **补修 (2026-03-03)**: 全面排查发现 `/workspace/upload` 和 `/workspace/upload-to` 两个端点虽对 `dir` 参数做了路径遍历校验，但 `file.filename` 未消毒，攻击者可通过恶意文件名（如 `../../etc/crontab`）绕过目录级校验。已添加 `Path(filename).name` 文件名消毒，与 `file_api.py` 的同功能端点保持一致。
- **状态**: ✅ **已修复（含补修）**

#### P0-2: 硬编码密钥/Token

- **位置**: `API/main.py`、`llm_manager_integrated/core/config.py`
- **成因**: 代码中存在硬编码的默认密钥和Token
- **修复**: 将敏感信息移至环境变量，代码中仅保留占位符
- **状态**: ✅ **已修复**

#### P0-3: CORS 配置过于宽松

- **位置**: `API/main.py` CORS 中间件配置
- **成因**: `allow_origins=["*"]` 允许任意域名跨域访问
- **修复**: 通过环境变量 `CORS_ORIGINS` 配置允许的域名列表，开发模式保留 `*`，生产模式严格限制
- **状态**: ✅ **已修复**

#### P0-4: pickle.load 不安全反序列化

- **位置**: `deepanalyze/analysis/` 模型加载相关代码
- **成因**: 使用 `pickle.load()` 加载模型文件，理论上可执行任意代码
- **实际风险**: 模型文件由系统内部生成，路径不可被外部用户直接控制，且已被 P0-1 的路径校验阻断外部文件注入
- **状态**: ⬇️ **降级为 P1**（实际风险已被 P0-1/P0-3 阻断，后续可考虑迁移至安全序列化格式）

#### P0-5: eval() 沙箱可绕过

- **位置**: `deepanalyze/analysis/task_SOP/rule_mining.py:87` `_safe_eval_rule()` 函数
- **成因**: 审计工具将 `pd.eval()` / `df.eval()` 标记为不安全的 `eval()` 调用
- **实际分析**:
  - 使用的是 `pd.eval()`（pandas 受限表达式求值器），**非 Python 内置 `eval()`**
  - `pd.eval()` 仅支持算术/比较/布尔运算，**不能调用任意函数或导入模块**
  - 输入来源为规则挖掘算法自动生成的规则字符串（格式 `(col op val)`），不可被外部用户直接控制
- **状态**: 🚫 **误报（false positive）** — `pd.eval()` 是受限引擎，输入非用户可控

#### P0-6: cache.keys() 遍历时修改字典 → RuntimeError

- **位置**: `llm_manager_integrated/core/cache.py:159-165` `MemoryCache.keys()` 方法
- **成因**: 在 `for key in self._cache` 遍历字典的过程中直接 `del self._cache[key]`，Python 字典禁止在遍历期间修改大小
- **影响**: 缓存中存在过期条目时，`keys()` 方法必定抛出 `RuntimeError: dictionary changed size during iteration`，导致 LLM Manager 缓存失效功能完全不可用
- **修复**: 改为先收集过期 key 到列表，遍历完成后再批量删除（与同文件 `info()` 方法已采用的正确模式一致）
- **修复文件**: `llm_manager_integrated/core/cache.py`
- **状态**: ✅ **已修复**

#### P0-7: CLI 模块用错误包名 → ImportError

- **位置**: `llm_manager_integrated/cli/main.py:50`
- **成因**: 包从 `llm_api_manager` 重命名为 `llm_manager_integrated` 时遗漏，仍使用 `from llm_api_manager.api.main import app`
- **影响**: LLM Manager 独立 CLI 启动路径完全不可用（`llm-manager serve` 命令 ImportError）
- **修复**: `from llm_api_manager.api.main import app` → `from llm_manager_integrated.api.main import app`
- **影响范围确认**: 不影响开发模式（`start_dev.ps1`）和生产模式（`scripts/start.ps1`），两者均通过 `API/main.py` → `llm_manager_integrated.api.app.create_app` 启动，不经过 CLI 入口
- **修复文件**: `llm_manager_integrated/cli/main.py`
- **状态**: ✅ **已修复**

#### P0-8: resources/utils.py 用错误包名 → ImportError

- **位置**: `llm_manager_integrated/resources/utils.py:38,52`
- **成因**: 同 P0-7，包重命名遗漏，`files('llm_api_manager')` 引用不存在的包名
- **影响**: 资源定位函数 `get_resource_path()` 主路径失败（有 try/except 降级到项目根目录查找）
- **修复**:
  - `files('llm_api_manager')` → `files('llm_manager_integrated')`（2处）
  - 同步更新 `resources/utils.py`、`resources/__init__.py`、`__init__.py` 中 15 处 docstring 旧包名引用
- **影响范围确认**: 不参与任何启动流程，是纯工具模块
- **修复文件**: `llm_manager_integrated/resources/utils.py`、`llm_manager_integrated/resources/__init__.py`、`llm_manager_integrated/__init__.py`
- **附注**: `llm_manager_integrated/` 中仍有 14 处 `llm_api_manager` 残留在 docstring/SQLite 文件名/installer 旧逻辑中，不影响运行，可作为 P2 后续清理
- **状态**: ✅ **已修复**

#### P0-9: proxy.py 访问不存在的 Channel 属性 → AttributeError

- **位置**: `llm_manager_integrated/api/routes/proxy/proxy.py`
- **成因**: 审计工具认为 `channel.channel_type`、`channel.api_base` 等属性不存在于 Channel 模型
- **实际分析**:
  - `proxy.py` 中的 `channel` 对象来自负载均衡器（`core/load_balancer.py`）的 `Channel` dataclass
  - 该 dataclass 定义了 `channel_type`、`api_base`、`api_key`、`model`、`name`、`id`、`metrics` 等属性
  - 所有属性访问**均与 dataclass 定义完全匹配**
- **状态**: 🚫 **误报（false positive）** — 属性完全匹配 dataclass 定义

### P1 问题清单（详细审计报告）

> P1 审计日期：2026-03-03  
> P1 审计范围：全项目安全审计（不安全反序列化、硬编码凭证、代码注入、输入验证、API安全）  
> P1 审计方式：4 路并行静态分析 + 人工确认

---

#### 分类 A：不安全反序列化（pickle.load / pickle.loads / torch.load）

> **背景**：P0-4 原始审计仅标注了 `deepanalyze/analysis/` 模型加载，降级为 P1。本次深度扫描发现不安全反序列化问题远超原始评估，涉及 20+ 处调用。
> **部署分级**: 🟢 私有化全部跳过（pickle 文件均为内部生成，无外部注入路径） | 🔴 公有云必修

##### P1-A1: persistent_store.py — pickle.load 加载阶段输出（中风险）

- **位置**: `deepanalyze/core/task_manager/persistent_store.py:577` `_load_outputs_from_file()`
- **加载内容**: 从 `.pkl` 文件加载阶段输出（DataFrame、模型指标等）
- **路径来源**: 由系统内部生成的 `{state_dir}/{execution_id}/{stage_id}_outputs.pkl`
- **验证措施**: 仅检查 `os.path.exists(file_path)`，**无内容校验**
- **风险评级**: 中 — 路径为内部生成，但 file_path 作为参数传入可被间接影响

##### P1-A2: persistent_store.py — pickle.load 加载完整执行上下文（中高风险）

- **位置**: `deepanalyze/core/task_manager/persistent_store.py:702` `load_full_state()`
- **加载内容**: 完整执行上下文对象 (`context.pkl`)
- **路径来源**: 由 `execution_id` 拼接或从数据库 `state["state_file_path"]` 获取
- **验证措施**: 检查文件存在性，**无路径遍历检查**，无反序列化内容校验
- **风险评级**: **中高** — `state_file_path` 来自数据库，若数据库被篡改可加载任意 pkl 文件

##### P1-A3: result_storage.py — pickle.load 加载任务结果（中风险）

- **位置**: `deepanalyze/core/task_manager/result_storage.py:145` `load_result()`
- **加载内容**: 任务执行结果中的复杂对象（DataFrame）
- **路径来源**: `self.base_dir / record_id / "outputs.pkl"`，`record_id` 由调用方传入
- **验证措施**: 仅检查目录和文件存在性，**无路径遍历防护**
- **风险评级**: 中 — `record_id` 含 `../../` 时可加载任意文件

##### P1-A4: sglang_engine.py — pickle.loads 网络数据反序列化（高风险）

- **位置**: `deepanalyze/SkyRL/skyrl-train/skyrl_train/inference_engines/sglang/sglang_engine.py:131`
- **加载内容**: `NamedWeightsUpdateRequest` 对象，从 base64 编码 tensor 数据解码
- **数据来源**: 通过 tensor 传递的序列化负载
- **验证措施**: 仅检查 end marker 和 base64 解码，**无内容安全校验**
- **风险评级**: **高** — 若攻击者控制 tensor 内容，可实现远程代码执行

##### P1-A5: ppo_utils.py — cloudpickle 函数反序列化（中风险）

- **位置**: `deepanalyze/SkyRL/skyrl-train/skyrl_train/utils/ppo_utils.py:316`
- **加载内容**: 从 Ray actor 获取的序列化函数对象
- **数据来源**: 通过 `ray.get(actor.get.remote(name))` 获取
- **风险评级**: 中 — 依赖 Ray 集群安全性

##### P1-A6: torch.load 全部使用 weights_only=False（中风险，5 处生产代码）

- **位置**:
  - `SkyRL/skyrl-train/skyrl_train/training_batch.py:175,286` — TensorBatch 加载
  - `SkyRL/skyrl-train/skyrl_train/trainer.py:1583,1596` — 训练状态恢复
  - `SkyRL/skyrl-train/skyrl_train/distributed/fsdp_strategy.py:608,611,617` — FSDP 检查点
  - `ms-swift/swift/tuners/base.py:306` — 模型权重加载
  - `ms-swift/swift/llm/train/tuner.py:378` — TorchAcc 恢复
  - `ms-swift/swift/utils/torchacc_utils.py:213,216` — 优化器/调度器恢复
- **风险评级**: 中 — 均明确使用 `weights_only=False`，checkpoint 文件来源可信但无额外校验
- **建议**: 可行场景下迁移至 `weights_only=True`；需要完整 pickle 的场景确保文件来源可信

##### P1-A7: ms-swift IndexedDataset — pickle.load/loads 数据集缓存（中风险）

- **位置**: `ms-swift/swift/llm/dataset/utils.py:283,302`
- **加载内容**: 数据集索引和样本数据
- **路径来源**: 由 `dataset_name` 和环境变量 `PACKING_CACHE` 拼接
- **风险评级**: 中 — 若 `dataset_name` 含路径遍历字符可能有风险

---

#### 分类 B：硬编码凭证与敏感信息

> **部署分级**: 🟡 私有化建议修复（B1 .env 权限） | 🔴 公有云必修

##### P1-B1: .env 文件中硬编码加密密钥（严重）

- **位置**: `.env` 第 2 行
- **内容**: `LLM_MANAGER_ENCRYPTION_KEY=CVW9iGPthZUaoJYg9kTNUcIRZ-I2DTOzvwV9o7AeSmE=`
- **缓解**: `.gitignore` 已排除 `.env`
- **风险评级**: **严重** — 若 `.env` 泄露，攻击者可解密 LLM Manager 存储的所有 API 密钥
- **建议**: 使用密钥管理服务或确保 `.env` 文件权限 600

##### P1-B2: deprecated_files 中硬编码 sk- 测试密钥（中等） ✅ 已修复

- **位置**: `deprecated_files/test_final_exclusivity.py:36`、`deprecated_files/test_exclusive_channels.py:11`
- **内容**: `'api_key': 'sk-test-key-12345'`
- **风险评级**: 中等 — placeholder key 但 `sk-` 前缀可能被 CI 密钥扫描工具误判
- **缓解**: `deprecated_files/` **未被 .gitignore 排除** ⚠️
- **建议**: 将 `deprecated_files/` 加入 `.gitignore` 或删除
- **修复**: `.gitignore` 已添加 `deprecated_files/` 排除规则

##### P1-B3: API 密钥部分泄露到控制台日志（低风险） ✅ 已修复

- **位置**: `API/llm_client_manager.py:63-66`
- **内容**: `key_preview = f"{api_key[:10]}...{api_key[-5:]}"`，然后 `print()`
- **风险评级**: 低 — 截断处理，但对短密钥可能泄露过多信息
- **建议**: 减少可见字符（前4位 + 后4位）
- **修复**: 缩短为前4后4，`print()` 改为 `logger.debug()`

---

#### 分类 C：不安全代码执行（exec / eval / subprocess）

> **部署分级**: 🟢 私有化全部跳过（exec/eval 输入均为系统内部或 LLM 生成，内网用户不构成攻击面） | 🔴 公有云必修

##### P1-C1: demo/backend.py — exec() 无沙箱执行用户代码（严重）

- **位置**: `demo/backend.py:52,259` `execute_code()` 函数
- **成因**: 两处 `exec(code_str, {})` 直接在主进程执行任意代码，**无沙箱隔离**
- **风险评级**: **严重** — 攻击者可执行任意系统命令、读取环境变量中的 API 密钥
- **缓解**: 同文件存在 `execute_code_safe()` 子进程版本，但 `execute_code()` 仍可被调用
- **建议**: 删除无沙箱版本 `execute_code()`，统一使用安全版本

##### P1-C2: SkyRL python_tool.py — exec() 无沙箱（严重）

- **位置**: `deepanalyze/SkyRL/skyrl-train/examples/deepanalyze/python_tool.py:33-40,84-91`
- **成因**: `exec(code, globals_dict)` 在主进程执行 LLM 生成代码
- **风险评级**: **严重** — 虽有 multiprocessing 版本，但无沙箱版本仍存在

##### P1-C3: SkyRL skyrl_gym — subprocess 执行任意 Python 代码（高）

- **位置**: `deepanalyze/SkyRL/skyrl-gym/skyrl_gym/tools/python.py:13-14`
- **成因**: `subprocess.run(["python", "-c", code], ...)` 执行外部传入代码
- **风险评级**: 高 — 无 shell=True，但 code 参数完全外部控制

##### P1-C4: playground 多处 eval() 反序列化文件数据（高）

- **位置**:
  - `playground/DSBench/data_modeling/show_result.py:9,38,40,44,61`
  - `playground/DSBench/data_modeling/score4each_com.py:9`
  - `playground/DSBench/data_analysis/show_result.py:8`
- **成因**: `eval(line)` / `eval(f.read().strip())` 解析文件内容
- **风险评级**: 高 — 文件被篡改可导致任意代码执行
- **建议**: 替换为 `json.loads()`

##### P1-C5: playground/SkyRL 多处 exec() 执行 LLM 生成代码（高）

- **位置**: `playground/TableQA/tests/tablebench.py:277`、`playground/TableQA/tests/aitqa.py:298`、`playground/DSBench/data_modeling/deepanalyze.py:38`、`playground/DABStep-Research/deepanalyze.py:65`、`playground/DS-1000/execution.py:49`、`SkyRL/skyrl-gym/skyrl_gym/envs/lcb/livecodebench.py:190`
- **风险评级**: 高 — 研究/评测代码，但缺乏系统级沙箱

##### P1-C6: shell=True 的 subprocess 调用（高，9 处）

- **位置**:
  - `ms-swift/tests/test_utils.py:335` — `subprocess.call(script_cmd, shell=True, ...)`
  - `ms-swift/swift/ui/llm_train/llm_train.py:496` — `Popen(run_command, shell=True, ...)`
  - `ms-swift/scripts/benchmark/exp_utils.py:137,161` — `Popen(..., shell=True)`
  - `ms-swift/examples/train/rft/rft.py:50,94,146,182` — 多处 `Popen(..., shell=True)`
- **风险评级**: 高 — 命令大多来自配置而非直接用户输入，但 `shell=True` 模式本身不安全

##### P1-C7: os.system() 执行动态构造命令（高，命令注入风险）

- **位置**:
  - `playground/DSBench/data_modeling/score4each_com.py:38-39` — `os.system(f"python {python_path}{line['name']}_eval.py ...")` ⚠️ `line['name']` 来自外部 JSON，**可注入**
  - `ms-swift/swift/ui/llm_train/runtime.py:588-590` — `os.system(f'taskkill /f /t /pid "{pid}"')`
  - `ms-swift/swift/ui/llm_infer/runtime.py:249-251`
  - `ms-swift/swift/ui/llm_grpo/external_runtime.py:110-116`
  - `ms-swift/swift/ui/llm_infer/llm_infer.py:291`
  - `ms-swift/swift/ui/llm_sample/llm_sample.py:276`
  - `ms-swift/swift/ui/llm_export/llm_export.py:199`
  - `ms-swift/swift/ui/llm_grpo/external_rollout.py:242`
  - `ms-swift/tests/llm/test_run3.py:159-175` — `os.system(f'pip install "{req}"')` ⚠️ req 来自模型元数据
  - `SkyRL/skyrl-train/examples/search/searchr1_dataset.py:152`
- **风险评级**: 高 — `score4each_com.py` 和 `test_run3.py` 尤其危险（外部数据直接拼入命令）
- **建议**: 替换为 `subprocess.run()` 列表形式传参

---

#### 分类 D：API 输入验证与安全

##### P1-D1: 文件上传无任何验证（严重）

- **位置**: `API/main.py` `POST /workspace/upload`、`POST /workspace/upload-to`、`API/file_api.py` `POST /v1/files`、`POST /v1/files/upload-to`
- **缺失验证**:
  - **无文件大小限制** — 可上传任意大文件造成磁盘耗尽 (DoS)
  - **无文件类型验证** — 无 MIME 类型检查
  - **无扩展名白名单** — 可上传 `.py`、`.sh`、`.exe` 等可执行文件
  - ~~**无文件名清理**~~ — 已在 P0-1 补修中通过 `Path(filename).name` 消毒
- **修复 (2026-03-03)**: 在 `utils.py` 添加 `check_upload_size()` 公共函数，4 个上传端点统一添加 500MB（可通过 `MAX_UPLOAD_SIZE_MB` 环境变量配置）文件大小限制，超限返回 HTTP 413。文件类型和扩展名验证暂不实施（私有化场景需上传数据文件类型多样）。
- **风险评级**: **严重**
- **部署分级**: 🟡 私有化建议修复（仅文件大小限制） | 🔴 公有云必修
- **状态**: ✅ **已修复（文件大小限制）**

##### P1-D2: file_api.py upload_to_dir 完全缺失路径遍历防护（严重） ✅ 已修复

- **位置**: `API/file_api.py:54-90` `POST /v1/files/upload-to`
- **成因**: `dir` 参数来自 Form，**未做路径遍历检查**；`file.filename` 也未清理
- **风险评级**: **严重** — 与 `main.py` 中同功能端点不同，此处缺少 `.resolve()` + `parents` 检查
- **修复方案**: 添加 `resolve()` + `parents` 路径遍历防护 + 文件名清理（`Path(filename).name`）
- **修复日期**: 2026-03-03
- **部署分级**: 🔴 私有化必修 | 🔴 公有云必修

##### P1-D3: /workspace/data-columns 路径遍历漏洞（严重） ✅ 已修复

- **位置**: `API/main.py:469-521`
- **成因**: `file_path` 参数来自查询字符串，**未做路径遍历检查**
- **风险评级**: **严重** — 可探测服务器上任意 CSV/Excel 文件结构
- **修复方案**: 添加 `resolve()` + `parents` 路径遍历防护
- **修复日期**: 2026-03-03
- **部署分级**: 🔴 私有化必修 | 🔴 公有云必修

##### P1-D4: /sop/data/analyze 接受任意绝对文件路径（严重）

- **位置**: `API/sop_api.py` `POST /sop/data/analyze`
- **成因**: 接受绝对文件路径参数，**无任何路径限制**
- **修复 (2026-03-03)**: 添加 `session_id` 参数，改为相对路径输入，通过 `resolve()` + `parents` 限制在 workspace 内；同时清理了 `detail=str(e)` 信息泄露。
- **风险评级**: **严重** — 可读取服务器上任意 CSV/Excel/Parquet 文件
- **部署分级**: 🟡 私有化建议修复 | 🔴 公有云必修
- **状态**: ✅ **已修复**

##### P1-D5: session_id 未做输入验证（严重） ✅ 已修复

- **位置**: 17 个 API 端点入口（`main.py` 11 个 + `file_api.py` 1 个 + `sop_api.py` 8 个）
- **成因**: `session_id` 直接拼接路径 `os.path.join(WORKSPACE_BASE_DIR, session_id)`，**无正则校验**
- **风险评级**: **严重** — 传入 `../../etc` 等恶意值可操作工作区外目录
- **修复方案**: 在 `utils.py` 新增 `validate_session_id()` 公共校验函数（正则 `^[a-zA-Z0-9_-]+$`），17 个 API 端点入口层调用。底层 `get_session_workspace`/`get_thread_workspace` 不修改，确保历史数据兼容和内部调用（恢复、GC 等）不受影响。
- **影响评估**: 已验证对持久化存储、缓存、任务暂停/继续/恢复、历史查看、轮询、报告生成、阶段结果展示等全部模块无影响。session_id 在系统中有 7 层使用（API 入口、路径构建、DB 写入/查询、内存比较、文件名前缀、缓存 key），修复仅影响 API 入口层。
- **修复日期**: 2026-03-03
- **部署分级**: 🔴 私有化必修 | 🔴 公有云必修

##### P1-D6: CORS 异常处理器硬编码 `"*"` 绕过策略（中高）

- **位置**: `API/main.py:128-149` 全局异常处理器
- **成因**: 异常响应中 CORS 头**硬编码 `Access-Control-Allow-Origin: *`**，未使用 `cors_origins` 变量
- **风险评级**: 中高 — 即使配置了严格 `CORS_ORIGINS`，异常响应仍绕过策略
- **部署分级**: 🟢 私有化跳过 | 🔴 公有云必修

##### P1-D7: SSRF 代理端点端口/协议未限制（中高）

- **位置**: `API/main.py:630-666` `GET /proxy`
- **成因**: 允许 `0.0.0.0`、未限制端口范围、未限制响应大小
- **风险评级**: 中高 — 可扫描本机所有端口服务
- **部署分级**: 🟢 私有化跳过 | 🔴 公有云必修

##### P1-D8: 无身份验证机制（严重 — 架构级）

- **位置**: 全局
- **成因**: 所有 API 端点完全公开，无认证即可：上传/删除文件、清空工作区、触发 LLM 调用（产生费用）、执行 SOP 任务、使用 SSRF 代理
- **风险评级**: **严重（架构级）** — 生产环境部署时必须解决
- **建议**: 至少实现 API Key 认证中间件或 JWT 机制
- **部署分级**: 🟢 私有化跳过（内网信任模型） | 🔴 公有云必修

##### P1-D9: 无速率限制（严重 — 架构级）

- **位置**: 全局
- **成因**: 无速率限制中间件，所有端点可被无限频率调用
- **风险**: LLM API 费用暴涨、服务器资源耗尽、磁盘空间耗尽
- **建议**: 使用 `slowapi` 对关键端点设置频率限制
- **部署分级**: 🟢 私有化跳过（用户数有限） | 🔴 公有云必修

##### P1-D10: 异常信息泄露（中等，多处）

- **位置**: `API/main.py`、`API/sop_api.py`、`API/scorecard_api.py`、`API/chat_api.py`、`API/export_api.py`、`API/file_api.py` 多处
- **风险评级**: 中等 — 完整堆栈可能暴露文件路径、库版本、内部逻辑
- **修复 (2026-03-03)**: 分两批修复。第一批修复了 main.py 全局异常处理器、export_api.py traceback 泄露、sop_api.py 9处 500 错误。第二批（补修）修复了 scorecard_api.py 6处、main.py 4处、sop_api.py 剩余7处（含业务 ValueError）、chat_api.py 7处（2处 LLM 错误 + 5处 admin JSON body）、export_api.py 1处 JSON body。所有 `str(e)` / `{e}` 替换为通用消息 + `logger.error(exc_info=True)` 记录完整信息。保留了前端依赖的 "not found" 和 "不是暂停状态" 关键词。`validate_session_id()` 的 ValueError 透传（消息可控）未修改。
- **部署分级**: 🟡 私有化建议修复 | 🔴 公有云必修
- **状态**: ✅ **已修复**

##### P1-D11: sop_api.py 裸 except: 语句（中等，4 处）

- **位置**: `API/sop_api.py` 报告导出函数中解析 `selected_features` 的 4 处
- **风险评级**: 中等 — 会捕获 `SystemExit`、`KeyboardInterrupt` 等，可能掩盖安全问题
- **修复 (2026-03-03)**: 4 处 `except:` 改为 `except (json.JSONDecodeError, ValueError):`
- **部署分级**: 🟡 私有化建议修复 | 🟡 公有云建议修复
- **状态**: ✅ **已修复**

##### P1-D12: HTTP 文件服务器无访问控制（中等）

- **位置**: `API/utils.py:551-563` `start_http_server()`
- **成因**: `SimpleHTTPRequestHandler` 提供 workspace 目录文件服务，**无认证、授权、速率限制**
- **风险评级**: 中等 — 任何人可直接访问所有文件
- **部署分级**: 🟢 私有化跳过 | 🔴 公有云必修

##### P1-D13: /export/report title 参数文件名注入（中等）

- **位置**: `API/main.py` `POST /export/report`
- **成因**: `title` 参数用于生成文件名，仅做空格替换，**未过滤 `/`、`\`、`..`**
- **修复 (2026-03-03)**: 添加正则白名单消毒 `re.sub(r'[^\w\u4e00-\u9fff\-.]', '_', title)[:100]`（保留中英文、数字、下划线、连字符、点，限100字符），额外添加 `resolve()` + `parents` 路径校验。
- **风险评级**: 中等
- **部署分级**: 🟡 私有化建议修复 | 🔴 公有云必修
- **状态**: ✅ **已修复**

---

#### 分类 E：SQL 与数据库

> **部署分级**: 🟢 私有化跳过（研究环境设计功能） | 🟡 公有云建议修复

##### P1-E1: SkyRL SQL 工具直接执行动态 SQL（中等 — 设计功能）

- **位置**: `SkyRL/skyrl-gym/skyrl_gym/tools/sql.py:21`、`SkyRL/skyrl-gym/skyrl_gym/envs/sql/utils.py:51`、`SkyRL/skyrl-gym/skyrl_gym/envs/code/utils.py:51`、`SkyRL/skyrl-train/examples/deepanalyze/utils.py:47`
- **成因**: `cursor.execute(sql)` 接收完整 SQL 字符串（Text2SQL 研究环境设计功能）
- **缓解**: 有 `BEGIN TRANSACTION` + `rollback()` 只读保护
- **风险评级**: 中等 — 研究环境中是预期功能，但需确保不暴露给外部用户

---

#### 分类 F：代码质量与工程规范

> **来源**：历史代码审查评估（P1 - 影响质量），与安全审计互为补充。
> **部署分级**: 🟡 私有化建议修复（F1/F2/F4/F5/F8 影响可靠性） | 🟡 公有云建议修复

##### P1-F1: 6 个 Router 未注册（死代码） — 4 个已归档标注 ✅

- **位置**: `workspace_api.py`、`file_api.py`、`execute_api.py`、`admin_api.py`、`export_api.py`、`scorecard_api.py`
- **成因**: Router 已定义但未在 `create_app()` 中 `include_router()`
- **风险评级**: 中 — 功能未生效，增加维护困惑
- **修复 (2026-03-04)**: 对照 `routing_architecture_guide.md` 确认 `file_api.py`、`export_api.py`、`admin_api.py`、`scorecard_api.py` 4 个文件从未被注册且功能已被其他路由覆盖或通过 SOP 任务模式提供，在文件头添加 `[ARCHIVED]` 标注说明未注册状态和原因。`workspace_api.py` 和 `execute_api.py` 在之前的审计中已确认为死代码。

##### P1-F2: create_app() 580+ 行，职责过重

- **位置**: `API/main.py:107-690`
- **成因**: 应用工厂函数包含路由定义、中间件配置、业务逻辑，严重违反单一职责
- **风险评级**: 中 — 可维护性差，易引入回归

##### P1-F3: 配置重复定义且不一致 ✅ 已修复

- **位置**: `config.py` vs `main.py` 的 `API_TITLE` 等配置；`API/utils.py` 重复拼接 `HTTP_SERVER_BASE`；`demo/backend.py` 重复定义 `WORKSPACE_BASE_DIR`/`HTTP_SERVER_PORT`/`HTTP_SERVER_BASE`
- **成因**: 同一配置项在多处定义，值可能不一致
- **风险评级**: 中 — 易导致行为不可预期
- **修复 (2026-03-04)**: `API/utils.py` 改为从 `config` 直接导入 `HTTP_SERVER_BASE`，消除重复拼接；`demo/backend.py` 因独立脚本无法跨模块导入，添加注释标注配置来源，提示保持同步

##### P1-F4: workspace 功能两套实现

- **位置**: `main.py` 内联实现 vs `workspace_api.py` Router 实现
- **成因**: 重构不完整，旧实现未清理
- **风险评级**: 中高 — 与 P1-D2 路径遍历问题关联（两套实现安全级别不一致）

##### P1-F5: 三个应用工厂大量代码重复

- **位置**: `app.py`、`create_app.py`、`pure_app.py`
- **成因**: 多个入口点包含重复的初始化逻辑
- **风险评级**: 中 — 修复一处漏洞时其他入口可能遗漏

##### P1-F6: 负载均衡器全局状态同步脆弱

- **位置**: 三层回退机制，难以调试
- **风险评级**: 中 — 可靠性问题，故障时难以定位

##### P1-F7: 全局异常处理泄露内部信息 ✅ 已修复

- **位置**: `llm_manager_integrated/api/app.py:160-166`
- **成因**: 与 P1-D10 同类问题，但位于 LLM Manager 子系统
- **风险评级**: 中 — 与 P1-D10 合并修复
- **修复**: 全局异常处理器返回通用消息，27 处 `str(e)` 泄漏全部替换为通用错误提示 + `logger.error(exc_info=True)`

##### P1-F8: 双重 commit 破坏事务一致性 ✅ 已修复

- **位置**: `persistent_store.py` 多处
- **成因**: 同一事务中多次 commit，部分失败时数据不一致
- **风险评级**: 中高 — 可能导致任务状态损坏
- **修复**: 移除 8 处手动 `session.commit()`，统一由上下文管理器自动提交

##### P1-F9: 全局 `warnings.filterwarnings('ignore')` ✅ 已修复

- **位置**: 9 个文件（`feature_correlation.py`、`feature_binning.py`、`woe.py`、`preprocessing.py`、`iv_analysis.py`、`scorecard_development.py`、`rule_mining_viz.py`、`scorecard_viz.py`、`rule_mining.py`）
- **成因**: 全局抑制所有警告，包括安全和弃用警告
- **风险评级**: 中 — 掩盖潜在问题
- **修复 (2026-03-04)**: 9 个文件的 `warnings.filterwarnings('ignore')` 改为仅过滤 `FutureWarning` + `DeprecationWarning`，保留 `RuntimeWarning`/`UserWarning` 等有诊断价值的警告

##### P1-F10: 调试日志 `[RETRY-DEBUG]` 残留 ✅ 已修复

- **位置**: `persistent_store.py:385-407`
- **成因**: 开发期调试代码未清理
- **风险评级**: 低 — 不影响功能，但不专业
- **修复**: 9 行 `logger.warning("[RETRY-DEBUG]...")` 降级为 `logger.debug()`，移除 `[RETRY-DEBUG]` 前缀

##### P1-F11: 脚本硬编码用户路径 ✅ 已修复

- **位置**: `start_dev.ps1`、`stop.ps1`、`init_env.ps1`
- **成因**: 路径硬编码为特定用户目录，其他环境无法使用
- **风险评级**: 中 — 影响可部署性
- **修复**: 所有硬编码路径替换为基于 `$PSScriptRoot` 的相对路径

##### P1-F12: 缺少 .env.example ✅ 已修复

- **位置**: 项目根目录
- **成因**: 新部署无配置参考，且与 P1-B1（.env 中硬编码密钥）关联
- **风险评级**: 中 — 影响部署体验和安全
- **修复**: 创建 `.env.example`，包含所有核心环境变量及注释说明

---

### P1 问题总览

| 分类 | 严重 | 高 | 中高 | 中 | 低 | 合计 |
|------|------|------|------|------|------|------|
| A: 不安全反序列化 | 0 | 1 | 1 | 5 | 0 | 7 |
| B: 硬编码凭证 | 1 | 0 | 0 | 1 | 1 | 3 |
| C: 代码执行 | 2 | 5 | 0 | 0 | 0 | 7 |
| D: API 输入验证 | 5 | 0 | 2 | 4 | 0 | 11 |
| E: SQL 与数据库 | 0 | 0 | 0 | 1 | 0 | 1 |
| F: 代码质量与工程规范 | 0 | 0 | 2 | 8 | 2 | 12 |
| **合计** | **8** | **6** | **5** | **19** | **3** | **41** |

> **注意**：P1 审计中 8 项"严重"级别问题主要集中在 **API 输入验证**（5 项：文件上传、路径遍历、认证缺失、速率限制）和 **代码执行**（2 项：exec 无沙箱）以及 **凭证管理**（1 项：加密密钥明文存储）。其中 D1/D2/D3/D4/D5 已修复，私有化部署版本下其余严重项风险可控（D8/D9 私有化跳过，C1/C2 私有化跳过）。F 分类（代码质量）12 项中 8 项已修复（F1/F3/F7/F8/F9/F10/F11/F12），剩余 4 项（F2/F4/F5/F6）为架构重构级别，暂缓处理。
>
> **审计修复完成度（截至 2026-03-04）**：
> - P0: 5/5 已修复 + 2 误报 + 2 降级（100% 完成）
> - P1 🔴必修: 3/3 已修复（100% 完成）
> - P1 🟡建议: 14/16 已修复（87.5%，剩余 F2/F5 为架构重构级）
> - P1 🟢跳过: 22 项私有化无需处理
> - P2: 2/8 已修复（P2-2 .gitignore + P2-3 CORS 环境变量）
>
> **部署分级图例**: 🔴 必修 | 🟡 建议修复 | 🟢 可跳过

### P1 优先修复路线图

> **私有化部署版本**：仅 D2/D3/D5 为必修（✅ 已完成），其余已按分级标签完成修复或跳过。
> **公有云版本**：全部 Phase 均需执行。

| 阶段 | 修复内容 | 私有化 | 公有云 | 工期估算 | 状态 |
|------|----------|--------|--------|----------|------|
| Phase 1（已完成） | P1-D5 session_id 校验 + P1-D2 路径遍历 + P1-D3 路径遍历 | 🔴 必修 | 🔴 必修 | 35 分钟 | ✅ 已完成 |
| Phase 2（生产阻塞） | P1-D8 认证 + P1-D9 限速 + P1-D1 上传验证 | 🟢 跳过 | 🔴 必修 | 2-3 天 | ✅ D1 已修复 / D8+D9 私有化跳过 |
| Phase 3（高危修复） | P1-D4 路径限制 + P1-D6 CORS 异常 + P1-C1/C2 删除 exec | 🟡 建议 | 🔴 必修 | 1-2 天 | ✅ D4+D6 已修复 / C1+C2 私有化跳过 |
| Phase 4（加固） | P1-B1 密钥管理 + P1-D10 错误信息清理 + P1-D11 裸 except | 🟡 建议 | 🔴 必修 | 1 天 | ✅ D10+D11 已修复 / B1 待手动设置权限 |
| Phase 5（工程重构） | P1-F1 归档标注 + P1-F2 拆分 create_app + P1-F4/F5 消除重复实现 + P1-F8 事务修复 | 🟡 建议 | 🟡 建议 | 2-3 天 | ✅ F1+F8 已修复 / F2+F4+F5 架构重构暂缓 |
| Phase 6（清理加固） | P1-F3 配置统一 + P1-F9 警告范围缩小 + P1-F10/F11/F12 清理 + .env.example | 🟡 建议 | 🟡 建议 | 1 天 | ✅ 全部已完成 |
| Phase 7（长期优化） | P1-A 系列序列化迁移 + P1-C 系列沙箱加固 | 🟢 跳过 | 🔴 必修 | 1-2 周 | ⏭️ 私有化跳过 |

> **开发规范提醒**：新增接受 `session_id` 参数的 API 端点，必须在函数入口调用 `validate_session_id()`（来自 `utils.py`）。

### 遗留清理项（P2）

| 编号 | 问题 | 说明 |
|------|------|------|
| P2-1 | `llm_manager_integrated/` 旧包名残留 | 14 处 `llm_api_manager` 在 docstring/SQLite 文件名/installer 旧逻辑中，不影响运行 |
| P2-2 | `deprecated_files/` 未被 .gitignore 排除 | 含 `sk-test-key-12345` 等测试凭证，~~应加入排除或删除~~ ✅ 已修复（.gitignore 已添加排除规则） |
| P2-3 | `demo/backend.py` CORS 仍为 `allow_origins=["*"]` | ~~demo 代码，非生产路径，但如暴露需收紧~~ ✅ 已修复（添加 `CORS_ORIGINS` 环境变量支持，默认行为不变） |
| P2-4 | playground/ 目录大量 eval/exec/os.system | 研究评测代码，非生产路径，但建议后续重构为安全模式 |
| P2-5 | 弃用 API 调用残留 | Pydantic `.dict()` → `.model_dump()`；`declarative_base` → `DeclarativeBase`；`on_event("startup")` → `lifespan` |
| P2-6 | 重复导入 | `config.py` 重复 `import os`；`main.py` 重复 `from fastapi import FastAPI`；`utils.py` 重复 `import re` |
| P2-7 | 代码规范不统一 | 中英文注释混用；步骤编号跳跃；pyright 大量抑制指令 |
| P2-8 | 逻辑缺陷 | `woe.py` KMeans 分箱逻辑错误；`feature_binning.py` 空序列未保护；缺少 `ScorecardPipeline`；MD5 缓存键碰撞风险 |

---

## Plan 审查修正记录

> 审查日期：2026-03-03  
> 审查方式：对照实际代码库状态，逐章节核实 Plan 中描述与实际是否一致

### 修正总览

| 严重度 | 修正数 | 说明 |
|--------|--------|------|
| 高（影响功能/构建） | 3 | 入口点、Python 版本、项目名称 |
| 中（描述与实际不符） | 9 | 状态、配置、脚本、Docker |
| 低（文档准确性） | 6 | 日期、链接、文件名 |

### 高严重度修正

| # | 章节 | 问题 | 修正内容 |
|---|------|------|----------|
| 1 | Task 1.2 `[project.scripts]` | 入口点 `deepanalyze:main` 不存在 | `deepanalyze = "deepanalyze:main"` → `deepanalyze = "API.main:main"` |
| 2 | Task 1.2 `requires-python` | 代码使用 PEP 604 语法（`X \| Y`），需 Python 3.10+ | `>=3.8` → `>=3.10`，classifiers 移除 3.8/3.9，CI 矩阵同步调整 |
| 3 | Task 1.2 pyproject.toml `name` | 与实际 pyproject.toml 的包名不一致 | `"deepanalyze"` → `"deepanalyze-creditwise"` |

### 中严重度修正

| # | 章节 | 问题 | 修正内容 |
|---|------|------|----------|
| 4 | 执行摘要 "核心任务" | Git/pyproject.toml/版本号状态标注过时 | Git 仓库 ✅、Python 包配置 ✅、统一版本号 ✅ |
| 5 | "缺失项"表格 | `setup.py/pyproject.toml ❌ 不存在` 与实际不符 | 加删除线标注为已完成 |
| 6 | "版本号现状" | `llm_manager: 2.0.0 ⚠️ 不一致` 与实际不符 | 更新为 `1.0.0 ✅ 已统一` |
| 7 | Task 5.1 vite.config | `base: '/llm-manager/'` 实际不存在 | 注释说明当前使用默认值 `'/'` |
| 8 | Task 5.1 next.config | 文件名 `.js`/`module.exports` 与实际不符 | 改为 `.mjs`/`export default`，补充 eslint/typescript 配置 |
| 9 | Task 5.2 后端代码 | 静态文件挂载代码与实际差异大 | 重写为实际 API 结构，添加主前端待处理警告 |
| 10 | Task 5.3 脚本清单 | `install.ps1`/`update.ps1` 标注为可用但实际不存在 | 添加 ❌ 待创建标注 |
| 11 | Task 5.6 Docker | `Dockerfile.prod`/`docker-compose.prod.yml` 不存在 | 标注为 ❌ 待创建 |
| 12 | Task 5.4 保留文件清单 | `scripts/start.bat`/`scripts/start.sh` 不存在 | 改为 `scripts/start.ps1`/`scripts/bump_version.py` |

### 低严重度修正

| # | 章节 | 问题 | 修正内容 |
|---|------|------|----------|
| 13 | Task 1.2 setup.py | `use_scm_version=True` 与 hatchling 冲突 | 移除 `use_scm_version`，更新 `name` |
| 14 | Phase 2 CI 工作流 | 矩阵含 3.8/3.9（不兼容），缺 3.12 | 矩阵改为 `["3.10", "3.11", "3.12"]` |
| 15 | Task 4.1 CHANGELOG 日期 | 年份 2025 应为 2026 | `2025-03-XX` → `2026-03-XX` |
| 16 | Task 1.2 `[tool.black]` | target-version 含不支持的版本 | 移除 py38/py39 |
| 17 | Task 1.2 `[tool.mypy]` | python_version 3.8 与最低版本要求不一致 | `3.8` → `3.10` |
| 18 | Task 4.3 Release Notes | `compare/v0.0.1...v1.0.0` 引用不存在的 tag | 改为 `commits/v1.0.0` |

### 未修正的遗留项（需后续处理）

| # | 问题 | 说明 |
|---|------|------|
| 1 | `install.ps1`/`update.ps1` 未创建 | Plan 中设计了完整脚本方案，但实际仅有 `scripts/start.ps1`，需在发布前创建 |
| 2 | `Dockerfile.prod`/`docker-compose.prod.yml` 未创建 | 设计方案已在 Plan Task 5.6，需在 Docker 发布前创建 |
| 3 | `demo/chat/dist/` 内容非纯静态导出 | 当前含 `server/`、`cache/` 等开发产物，需重新执行 `npm run build` |
| 4 | 主前端生产模式静态文件挂载 | `API/main.py` 中缺少 `app.mount("/", StaticFiles(...))` 的生产模式配置 |
| 5 | Mac/Linux 脚本全部未创建 | Plan 中设计了 6 个跨平台 Shell 脚本，均需在发布前创建 |

---

## 风险与应对

| 风险 | 可能性 | 影响 | 应对措施 |
|------|--------|------|----------|
| Git 初始化冲突 | 低 | 高 | 提前备份，逐步迁移 |
| 测试失败 | 中 | 高 | 预留修复时间，可延后发布 |
| 依赖冲突 | 中 | 中 | 使用虚拟环境隔离测试 |
| 版本号遗漏 | 中 | 低 | 使用脚本统一检查 |
| 文档不完整 | 低 | 中 | 发布后可补充更新 |

---

## 附录

### A. 命令速查表

```bash
# Git 操作
git init
git add .
git commit -m "message"
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin main --tags

# Python 包
pip install -e .
python -m build
twine upload dist/*

# 测试
pytest tests/ -v
pytest tests/ --cov=deepanalyze

# 代码风格
black deepanalyze/ --line-length 100
flake8 deepanalyze/ --max-line-length 100
```

### B. 文件模板位置

| 模板 | 路径 | 说明 |
|------|------|------|
| pyproject.toml | 本文档 Phase 1.2 | Python 包配置 |
| CI Workflow | 本文档 Phase 2.2 | GitHub Actions |
| Issue Template | 本文档 Phase 2.3 | GitHub Issues |
| PR Template | 本文档 Phase 2.3 | Pull Requests |
| Release Notes | 本文档 Phase 4.3 | 发布说明 |
| **Windows 脚本** | | |
| install.ps1 | 本文档 Phase 5.3 | Windows 环境安装脚本 |
| start.ps1 | 本文档 Phase 5.3 | Windows 服务启动脚本 |
| update.ps1 | 本文档 Phase 5.3 | Windows 依赖更新脚本 |
| **Mac OS 脚本** | | |
| install_mac.sh | 本文档 Phase 5.3 | Mac 环境安装脚本 |
| start_mac.sh | 本文档 Phase 5.3 | Mac 服务启动脚本 |
| update_mac.sh | 本文档 Phase 5.3 | Mac 依赖更新脚本 |
| **Linux 脚本** | | |
| install_linux.sh | 本文档 Phase 5.3 | Linux 环境安装脚本 |
| start_linux.sh | 本文档 Phase 5.3 | Linux 服务启动脚本 |
| update_linux.sh | 本文档 Phase 5.3 | Linux 依赖更新脚本 |
| **打包脚本** | | |
| package_release.ps1 | 本文档 Phase 5.5 | 跨平台打包脚本 |
| **Docker 配置** | | |
| Dockerfile.prod | 本文档 Phase 5.6 | 生产环境 Dockerfile |
| docker-compose.prod.yml | 本文档 Phase 5.6 | 生产 Docker Compose |
| Dockerfile.multi | 本文档 Phase 5.6 | 多阶段构建 Dockerfile |

### C. 发布版排除清单

#### 完全排除的文件/目录

```
# 开发/测试相关
deprecated_files/
tests/
docs/
.git/
demo/chat/.next/
demo/chat/node_modules/
llm_manager_integrated/frontend/node_modules/
.venv/
__pycache__/
*.pyc
*.pyo
.pytest_cache/
.mypy_cache/

# 敏感信息
.env
.env.local
logs/
*.db
workspace/
*.log

# IDE/编辑器
.vscode/
.idea/
*.swp
*.swo
*~

# 操作系统
.DS_Store
Thumbs.db
```

#### 保留的文件/目录

```
# 核心代码
API/
deepanalyze/
llm_manager_integrated/api/
llm_manager_integrated/core/
llm_manager_integrated/models/
llm_manager_integrated/static/  (预构建前端)
llm_manager_integrated/utils/

# 配置
config/
pyproject.toml
setup.py
requirements.txt

# 前端构建产物
demo/chat/dist/  (Next.js export 输出)

# 脚本
scripts/start.ps1
scripts/bump_version.py

# 文档
LICENSE
README.md
CHANGELOG.md

# Docker
docker/
Dockerfile
docker-compose.yml
```

### D. 部署配置参考

#### 环境变量配置

```bash
# 生产环境 (.env.production)
DEV_MODE=false
API_PORT=8200
API_HOST=0.0.0.0
WORKSPACE_BASE_DIR=./data/workspace
LOG_LEVEL=INFO

# 安全配置
CORS_ORIGINS=http://localhost:8200
```

#### Docker Compose 配置

```yaml
version: '3.8'
services:
  deepanalyze:
    image: ruc-datalab/deepanalyze:v1.0.0
    ports:
      - "8200:8200"
    environment:
      - DEV_MODE=false
      - API_PORT=8200
      - API_HOST=0.0.0.0
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

### E. 联系信息

| 角色 | 职责 | 联系方式 |
|------|------|----------|
| 项目负责人 | 整体协调 | - |
| 后端开发 | 代码实现 | - |
| DevOps | CI/CD | - |
| QA | 测试验证 | - |

---

**文档版本**: v1.8  
**最后更新**: 2026-03-04  
**状态**: 发布前代码审计修复已全部完成（P0 全部完成，P1 必修全部完成，P1 建议级 14/16 完成，P2 已修复 2/8）
