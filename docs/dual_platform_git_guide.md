# 工蜂 + GitHub 双平台 Git 推送指南

> 📅 创建日期：2026-03-11  
> 📌 适用项目：DeepAnalyze CreditWise  
> 🎯 目标：将同一项目同时推送到工蜂（内网）和 GitHub（外网/开源）

---

## 一、整体架构

```
本地仓库 (DeepAnalyze)
    │
    ├── origin  → 工蜂 (https://git.woa.com/fjzheng/CreditWise.git)
    │              主仓库，日常开发
    │
    └── github  → GitHub (https://github.com/xxx/DeepAnalyze.git)
                   镜像仓库，开源/备份
```

**原则：工蜂为主，GitHub 为辅。日常开发在工蜂，定期同步到 GitHub。**

---

## 二、初始配置

### 2.1 查看当前远程仓库

```bash
git remote -v
```

输出示例：
```
origin  https://git.woa.com/fjzheng/CreditWise.git (fetch)
origin  https://git.woa.com/fjzheng/CreditWise.git (push)
```

### 2.2 添加 GitHub 远程仓库

```bash
# 先在 GitHub 上创建一个空仓库（不要初始化 README）
# 然后添加为第二个远程仓库，命名为 github
git remote add github https://github.com/你的用户名/DeepAnalyze.git
```

### 2.3 验证配置

```bash
git remote -v
```

输出应该有两组：
```
origin  https://git.woa.com/fjzheng/CreditWise.git (fetch)
origin  https://git.woa.com/fjzheng/CreditWise.git (push)
github  https://github.com/你的用户名/DeepAnalyze.git (fetch)
github  https://github.com/你的用户名/DeepAnalyze.git (push)
```

---

## 三、日常推送流程

### 3.1 常规开发（只推工蜂）

```bash
# 正常开发流程
git add -A
git commit -m "feat: 新功能描述"
git push origin main          # 只推到工蜂
```

UGit 操作：正常 commit → 推送，默认推到 origin（工蜂）。

### 3.2 同步到 GitHub（定期执行）

```bash
# 方式1：推送 main 分支
git push github main

# 方式2：推送所有分支
git push github --all

# 方式3：推送所有分支 + 所有 tag
git push github --all
git push github --tags
```

### 3.3 一条命令同时推两个平台

```bash
# 方式1：连续执行
git push origin main && git push github main

# 方式2：配置 origin 同时推两个地址（高级）
git remote set-url --add --push origin https://git.woa.com/fjzheng/CreditWise.git
git remote set-url --add --push origin https://github.com/你的用户名/DeepAnalyze.git
```

> ⚠️ 方式2 配置后，每次 `git push origin main` 会同时推两个平台。
> 但要注意：工蜂在内网，GitHub 在外网，网络环境不同可能导致一个成功一个失败。
> **建议用方式1，分开推，出错好排查。**

### 3.4 Tag 推送

```bash
# 推送 tag 到工蜂
git push origin v1.0.0-beta.1

# 推送 tag 到 GitHub
git push github v1.0.0-beta.1

# 推送所有 tag 到 GitHub
git push github --tags
```

---

## 四、平台差异详解

### 4.1 CI/CD 配置

| | 工蜂 | GitHub |
|---|---|---|
| 配置文件 | `.gitlab-ci.yml`（项目根目录） | `.github/workflows/*.yml` |
| 语法格式 | GitLab CI 语法 | GitHub Actions 语法 |
| 执行器 | GitLab Runner | GitHub Actions Runner |
| 免费额度 | 取决于公司配置 | 公开仓库免费，私有仓库有限额 |

**工蜂 CI 示例** (`.gitlab-ci.yml`)：
```yaml
stages:
  - test
  - build

unit_test:
  stage: test
  script:
    - pip install -r requirements.txt
    - pytest tests/ -v
  only:
    - main

build_release:
  stage: build
  script:
    - echo "构建发布包"
  only:
    - tags
```

**GitHub Actions 示例** (`.github/workflows/test.yml`)：
```yaml
name: Tests
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest tests/ -v
```

**结论：需要维护两套 CI 配置文件，但它们互不干扰（工蜂忽略 `.github/`，GitHub 忽略 `.gitlab-ci.yml`）。**

### 4.2 Issue / MR 模板

| | 工蜂 | GitHub |
|---|---|---|
| Issue 模板路径 | 网页设置 或 `.gitlab/issue_templates/*.md` | `.github/ISSUE_TEMPLATE/*.md` |
| MR/PR 模板路径 | `.gitlab/merge_request_templates/*.md` | `.github/pull_request_template.md` |
| 配置方式 | 网页可视化 + 文件 | 纯文件 |

**工蜂 Issue 模板** (`.gitlab/issue_templates/bug_report.md`)：
```markdown
## Bug 描述
<!-- 简要描述问题 -->

## 复现步骤
1. 
2. 
3. 

## 期望行为
<!-- 你期望发生什么 -->

## 实际行为
<!-- 实际发生了什么 -->

## 环境信息
- 操作系统：
- Python 版本：
- 浏览器：
```

**GitHub Issue 模板** (`.github/ISSUE_TEMPLATE/bug_report.md`)：
```markdown
---
name: Bug Report
about: 报告一个问题
title: '[BUG] '
labels: bug
assignees: ''
---

## Bug 描述
<!-- 同上，内容一样，只是文件头格式不同 -->
```

**结论：模板内容可以复用，但文件路径和头部格式不同。**

### 4.3 术语对照表

| 概念 | 工蜂 | GitHub |
|------|------|--------|
| 代码合并请求 | 合并请求 (Merge Request, MR) | Pull Request (PR) |
| CI 执行器 | GitLab Runner | GitHub Actions Runner |
| 包/产物存储 | 制品库 | GitHub Packages / Releases Assets |
| 项目看板 | 里程碑 | Projects |
| 代码讨论 | 代码评论 | Discussions |
| 保护分支 | 分支保护规则 | Branch Protection Rules |
| 代码审查 | 代码评审（自带 AI） | 需配置第三方或手动 Review |

### 4.4 Release 创建

| | 工蜂 | GitHub |
|---|---|---|
| 入口 | Tags 页面 → 版本发布 | Releases 页面 → Draft a new release |
| 附件上传 | 支持 | 支持 |
| Release Notes | 手动填写 | 手动填写 或 自动生成 |
| 下载源码 | zip / tar.gz | zip / tar.gz |

---

## 五、需要注意的问题

### 5.1 敏感信息过滤

⚠️ **最重要的一点：工蜂是内网项目，GitHub 是公网！**

推送到 GitHub 前必须确认：

| 检查项 | 说明 |
|--------|------|
| API Key / Token | 不能出现在代码里，用环境变量 |
| 内网地址 | `*.woa.com`、`*.oa.com` 等内网域名 |
| 公司内部信息 | 部门名称、内部系统名称、员工信息 |
| 数据文件 | 任何真实业务数据、样本数据 |
| 配置文件 | 包含内网 IP、数据库连接串的配置 |

**建议：推送 GitHub 前用以下命令全局搜索：**
```bash
# 搜索可能的敏感信息
git grep -i "woa.com"
git grep -i "api_key"
git grep -i "password"
git grep -i "token"
git grep -i "secret"
```

### 5.2 .gitignore 差异

两个平台共用同一个 `.gitignore`，一般不需要区分。但注意：

```gitignore
# 工蜂特有的配置（GitHub 会忽略）
.gitlab-ci.yml          # 不要忽略！两边都留着没问题

# GitHub 特有的配置（工蜂会忽略）
.github/                # 不要忽略！两边都留着没问题
```

**两套 CI 配置文件都放在仓库里即可，各自平台只认自己的文件。**

### 5.3 分支策略

| 策略 | 说明 |
|------|------|
| 简单模式 | 两边都只用 `main` 分支，保持一致 |
| 进阶模式 | 工蜂有开发分支，只把 `main` 同步到 GitHub |
| 不建议 | 两边分支名不一致（容易混乱） |

### 5.4 认证方式

| | 工蜂 | GitHub |
|---|---|---|
| HTTPS | 工蜂账号密码 / Personal Token | GitHub Personal Access Token (PAT) |
| SSH | 需配置 SSH Key 到工蜂 | 需配置 SSH Key 到 GitHub |
| 凭证管理 | Git Credential Manager | Git Credential Manager |

**建议：两个平台分别配置 Personal Access Token，存到 Git Credential Manager 里，避免每次输密码。**

---

## 六、推荐工作流

### 日常开发
```
编码 → commit → push origin main（工蜂）
```

### 版本发布时
```
1. 改版本号 → commit
2. 打 tag → push origin main + push origin tag（工蜂）
3. 工蜂创建 Release
4. push github main + push github tag（GitHub）
5. GitHub 创建 Release
```

### 定期同步（如每周一次）
```
git push github main --force-with-lease
git push github --tags
```

> `--force-with-lease` 比 `--force` 安全，只在远程没有新提交时才强制推送。

---

## 七、自动化同步方案（进阶，后续可选）

### 方案 A：Git Hook 自动同步

在 `.git/hooks/post-push`（需要自定义）中自动推送到 GitHub。

### 方案 B：CI/CD 自动同步

在工蜂 CI 中配置：每次 main 分支更新时，自动推送到 GitHub。

```yaml
# .gitlab-ci.yml 中添加
sync_to_github:
  stage: deploy
  script:
    - git push https://$GITHUB_TOKEN@github.com/你的用户名/DeepAnalyze.git main
  only:
    - main
```

### 方案 C：手动同步（当前推荐）

最简单、最可控。发版本时手动推一下就行。

---

## 八、快速参考卡片

```
# 查看远程仓库
git remote -v

# 添加 GitHub 远程
git remote add github https://github.com/xxx/DeepAnalyze.git

# 推送到工蜂
git push origin main
git push origin v1.0.0-beta.1

# 推送到 GitHub
git push github main
git push github v1.0.0-beta.1

# 同步所有到 GitHub
git push github --all
git push github --tags

# 检查敏感信息
git grep -i "woa.com"
git grep -i "api_key"
git grep -i "password"
```

---

## 九、当前状态

| 平台 | 状态 | 仓库地址 |
|------|------|---------|
| 工蜂 | ✅ 已配置 | `https://git.woa.com/fjzheng/CreditWise.git` |
| GitHub | ⏳ 待配置 | 待创建仓库后添加 |

**下一步：等需要推送 GitHub 时，按本文档 "二、初始配置" 操作即可。**
