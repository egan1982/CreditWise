# DeepAnalyze 项目 Release 就绪可执行计划

> 版本：v1.2  
> 日期：2025-03-02  
> 状态：待执行  
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
10. [风险与应对](#风险与应对)
11. [附录](#附录)

---

## 执行摘要

### 项目概况

| 项目 | 内容 |
|------|------|
| 项目名称 | DeepAnalyze |
| 当前版本 | 1.0.0 (deepanalyze/__init__.py) |
| 目标版本 | v1.0.0 (Git Tag) |
| 许可证 | MIT |
| 预计工期 | 2-3 周 |
| 关键阻塞项 | 未初始化 Git 仓库 |

### 核心任务

| 优先级 | 任务 | 状态 | 工期 |
|--------|------|------|------|
| P0 | 初始化 Git 仓库 | ❌ 未开始 | 2 小时 |
| P0 | 创建 Python 包配置 | ❌ 未开始 | 4 小时 |
| P0 | 统一版本号 | ❌ 未开始 | 1 小时 |
| P1 | GitHub Actions CI/CD | ❌ 未开始 | 1 天 |
| P1 | GitHub 模板文件 | ❌ 未开始 | 1 天 |
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
| Git 仓库 | ❌ 不存在 | 无法版本控制 | P0 |
| setup.py/pyproject.toml | ❌ 不存在 | 无法 pip 安装 | P0 |
| 版本一致性 | ⚠️ 不一致 | llm_manager: 2.0.0 vs deepanalyze: 1.0.0 | P0 |
| GitHub Actions | ❌ 不存在 | 无自动化 | P1 |
| GitHub 模板 | ❌ 不存在 | 贡献体验差 | P1 |
| SECURITY.md | ❌ 不存在 | 安全合规 | P2 |
| CODE_OF_CONDUCT.md | ❌ 不存在 | 社区规范 | P2 |

### 版本号现状

```python
# deepanalyze/__init__.py
__version__ = "1.0.0"

# llm_manager_integrated/__version__.py
__version__ = "2.0.0"  # ⚠️ 不一致

# API/main.py
API_VERSION = "1.0.0"
```

**建议：统一使用 "1.0.0" 作为首个 Release 版本**

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
name = "deepanalyze"
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
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
    "Topic :: Software Development :: Libraries :: Python Modules",
]
requires-python = ">=3.8"
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
deepanalyze = "deepanalyze:main"

[tool.hatch.build.targets.wheel]
packages = ["deepanalyze", "API", "llm_manager_integrated"]

[tool.black]
line-length = 100
target-version = ['py38', 'py39', 'py310', 'py311', 'py312']

[tool.isort]
profile = "black"
line_length = 100

[tool.mypy]
python_version = "3.8"
warn_return_any = true
warn_unused_configs = true
```

#### 创建 setup.py（向后兼容）

```python
# setup.py
# 用于向后兼容，实际配置在 pyproject.toml

from setuptools import setup, find_packages

setup(
    name="deepanalyze",
    use_scm_version=True,
    setup_requires=['setuptools_scm'],
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
| llm_manager_integrated/__version__.py | 2.0.0 | 1.0.0 | 修改 |
| API/main.py | 1.0.0 | 1.0.0 | ✅ 无需修改 |
| pyproject.toml | - | 1.0.0 | 新增 |

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
        python-version: ["3.8", "3.9", "3.10", "3.11"]

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

## [1.0.0] - 2025-03-XX

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

**Full Changelog**: https://github.com/ruc-datalab/DeepAnalyze/compare/v0.0.1...v1.0.0
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
  base: '/llm-manager/',
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
// demo/chat/next.config.js
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  distDir: 'dist',
  assetPrefix: '.',
  images: { unoptimized: true },
}
module.exports = nextConfig
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

当前 `API/main.py` 已正确配置，确认以下代码：

```python
# API/main.py (已有代码)

# 检测运行模式
dev_mode = os.getenv("DEV_MODE", "false").lower() == "true"

# 挂载 LLM Manager 子应用
if llm_manager.available:
    llm_manager_app = llm_manager.create_app(
        config={"cors_origins": ["*"]},
        as_subapp=True,
        enable_frontend=False,  # 禁用内置前端，使用静态文件
        prefix=""
    )
    app.mount("/llm-manager", llm_manager_app)

# 生产模式挂载静态文件
if not dev_mode:
    # LLM Manager 前端
    app.mount("/llm-manager/static", 
              StaticFiles(directory="llm_manager_integrated/static"), 
              name="llm-manager-static")
    
    # 主前端
    app.mount("/", 
              StaticFiles(directory="demo/chat/dist", html=True), 
              name="frontend")
```

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
| **Windows** | `install.ps1` | `start.ps1` | `update.ps1` |
| **Mac OS** | `install_mac.sh` | `start_mac.sh` | `update_mac.sh` |
| **Linux** | `install_linux.sh` | `start_linux.sh` | `update_linux.sh` |

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
if (Test-Path "$ProjectRoot\runtime\python\python.exe") {
    $SystemPython = "$ProjectRoot\runtime\python\python.exe"
    Write-Host "✓ 使用嵌入式 Python: $SystemPython" -ForegroundColor Green
} else {
    try {
        $pyVersion = & $SystemPython --version 2>&1
        Write-Host "✓ 使用系统 Python: $pyVersion" -ForegroundColor Green
    } catch {
        Write-Host "❌ 未找到 Python，请安装 Python 3.8+" -ForegroundColor Red
        exit 1
    }
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
    if (Test-Path "$ProjectRoot\runtime\nodejs\node.exe") {
        $NodeExe = "$ProjectRoot\runtime\nodejs\node.exe"
    }
    
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
    echo -e "${RED}❌ 未找到 Python3，请先安装 Python 3.8+${NC}"
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
scripts/start.bat
scripts/start.sh

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
    
    # 查找 Python
    if (Test-Path "$ProjectRoot\runtime\python\python.exe") {
        $PythonExe = "$ProjectRoot\runtime\python\python.exe"
    }
    
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

##### 1. 生产 Dockerfile (Dockerfile.prod)

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

##### 2. 生产 Docker Compose (docker-compose.prod.yml)

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

##### 3. 多阶段构建 Dockerfile (Dockerfile.multi)

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
- [ ] demo/chat next.config.js 配置 output: 'export'
- [ ] demo/chat npm run build 成功
- [ ] llm_manager_integrated/frontend vite.config.ts 配置 base
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
scripts/start.bat
scripts/start.sh

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

**文档版本**: v1.2  
**最后更新**: 2025-03-02  
**状态**: 待执行（已整合私有化部署完整方案）
