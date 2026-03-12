# Release v1.0.0-beta.1

> 📅 发布日期：2026-03-11  
> 🏷️ 版本类型：Beta（功能基本完成，持续测试优化中）

---

## 🎉 概述

CreditWise v1.0.0-beta.1 是首个公开测试版本。这是一个基于 AI 的信贷风控智能助手，专注于规则挖掘、评分卡建模和策略分析。

---

## ✨ 核心功能

### 🤖 Agentic LLM 数据分析
- 自主数据科学分析，最小化人工干预
- 多 LLM 提供商支持：OpenAI、DeepSeek、Claude、Google AI 等
- 系统提示词可配置，支持预设任务模板

### 📊 Task SOP 系统
- 结构化数据分析工作流（规则挖掘、评分卡开发等）
- Pipeline 可视化与伪代码预览
- 规则质量验证（覆盖率、冲突、冗余检测）
- 规则稳定性检测（PSI）
- 规则业务解读

### 🔧 集成 LLM Manager
- Web UI 渠道配置与监控
- API 代理与负载均衡
- 模型列表缓存（TTL 机制）
- 完整的请求/响应日志

### 🏗️ 前后端架构
| 组件 | 端口 | 技术栈 |
|------|------|--------|
| 主前端 | 3000 | Next.js |
| LLM Manager 前端 | 3001 | Vite |
| 后端 API | 8200 | FastAPI |

---

## 📋 API 端点

| 功能 | 端点 |
|------|------|
| 聊天完成 | `POST /v1/chat/completions` |
| SOP 任务管理 | `POST /sop/execute` |
| 模型列表 | `GET /llm-manager/api/models` |
| 渠道管理 | `GET/POST /llm-manager/api/manage/channels` |
| API 文档 | `GET /docs` |

---

## 🚀 快速启动

```powershell
# 1. 初始化环境
.\init_env.ps1

# 2. 启动完整服务
.\start_all_api.ps1
```

---

## ⚠️ Beta 说明

此版本为测试版，以下内容仍在完善中：
- 跨平台安装脚本（Mac/Linux）
- 自动化测试覆盖
- CI/CD 流水线
- 生产环境打包脚本
- 安全性增强（访问控制、频率限制）

欢迎测试反馈！

---

## 📁 版本号

| 组件 | 版本 |
|------|------|
| deepanalyze | 1.0.0-beta.1 |
| llm_manager_integrated | 1.0.0-beta.1 |
| API | 1.0.0-beta.1 |
| pyproject.toml | 1.0.0-beta.1
