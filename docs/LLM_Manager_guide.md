# LLM_Manager 集成指南

## 概述

LLM_Manager 已成功集成到 DeepAnalyze 项目中，取代了之前手动配置 API KEY 的方式。现在可以通过可视化界面管理多个 LLM 供应商的 API 密钥。

## ✨ 核心特性

- 🔐 **安全存储**：所有 API 密钥都通过 Fernet 加密存储
- 🔄 **多供应商支持**：支持 OpenAI、DeepSeek、Claude、Gemini 等 10+ 供应商
- 📊 **调用日志**：完整记录所有 API 调用日志
- 💰 **成本统计**：自动计算 API 使用成本
- 🎯 **动态切换**：实时切换不同的 LLM 服务商
- 👥 **多用户管理**：支持多用户和多项目共享

## 快速开始

### 1. 启动应用

```powershell
# 使用标准启动脚本
.\start_dev.ps1

# 或仅启动后端 API
.\start_dev.ps1 -NoFrontend
```

### 2. 访问 LLM Manager UI

启动后，访问以下地址：

```
http://localhost:8200/llm-manager
```

### 3. 添加 API 密钥

1. 打开 LLM Manager UI
2. 点击 "添加渠道" 按钮
3. 填写以下信息：
   - **提供商**：选择 OpenAI、DeepSeek、Claude 等
   - **API Key**：粘贴您的 API 密钥
   - **描述**（可选）：用于标识该密钥的用途
4. 点击 "保存"

### 4. 在 DeepAnalyze 中使用

DeepAnalyze 会自动使用通过 LLM Manager 管理的 API 密钥，无需额外配置。

## API 端点

### 获取所有渠道

```bash
GET /llm-manager/api/channels
```

**响应示例：**
```json
{
  "data": [
    {
      "id": 1,
      "provider": "openai",
      "name": "OpenAI Main",
      "description": "Production API",
      "encrypted_key": "...",
      "created_at": "2025-12-01T10:00:00Z"
    }
  ]
}
```

### 创建渠道

```bash
POST /llm-manager/api/channels
Content-Type: application/json

{
  "provider": "openai",
  "api_key": "sk-...",
  "name": "OpenAI Main",
  "description": "Production API"
}
```

### 删除渠道

```bash
DELETE /llm-manager/api/channels/{channel_id}
```

### 获取调用日志

```bash
GET /llm-manager/api/logs?limit=100&offset=0
```

### 获取成本统计

```bash
GET /llm-manager/api/stats/costs
```

## 支持的 LLM 供应商

| 供应商 | 支持 | 备注 |
|--------|------|------|
| OpenAI | ✓ | GPT-4、GPT-3.5 等 |
| DeepSeek | ✓ | 国内优质服务 |
| Anthropic Claude | ✓ | Claude 3 系列 |
| Google Gemini | ✓ | Gemini Pro 等 |
| 阿里通义千问 | ✓ | Qwen 系列 |
| 百度文心一言 | ✓ | Ernie Bot 系列 |
| 讯飞星火 | ✓ | Spark 系列 |
| Mistral | ✓ | Mistral 系列 |
| 本地 LLM | ✓ | Ollama 等自部署模型 |

## 与 DeepAnalyze 的集成

### 原来的方式（已弃用）

```powershell
# 不再需要手动设置环境变量
$env:DEEPSEEK_API_KEY = "sk-xxx"
$env:OPENAI_API_KEY = "sk-yyy"
```

### 现在的方式（推荐）

1. 启动应用：`.\start_dev.ps1`
2. 打开 LLM Manager UI：`http://localhost:3001` (开发模式) 或 `http://localhost:8200/llm-manager` (生产模式)
3. 添加您的 API 密钥
4. DeepAnalyze 会自动使用管理的密钥

## 数据安全

### 加密存储

所有 API 密钥都采用以下安全措施存储：
- **加密算法**：Fernet（AES-128-CBC）
- **密钥管理**：存储在应用配置中
- **数据库**：SQLite 本地存储

### 访问控制

- ✓ API 密钥从不在日志中输出
- ✓ 前端仅显示掩码的密钥
- ✓ 所有 API 请求都需要身份验证（如配置）
- ✓ 支持 CORS 跨域策略配置

## 常见问题

### Q1: 如何导出或备份 API 密钥？

A: LLM Manager 暂不支持导出密钥（出于安全考虑）。如需迁移，请：
1. 记录所有密钥信息
2. 重新添加到新系统
3. 建议在安全的密码管理器中保留备份

### Q2: 可以同时使用多个相同供应商的 API 密钥吗？

A: 可以。您可以添加多个 OpenAI/DeepSeek 等的密钥，用于：
- 不同的项目或环境
- 轮流使用以分散负载
- 成本管理和分析

### Q3: 如何重置所有密钥？

A: 目前需要手动删除。支持批量删除功能在规划中。

### Q4: DeepAnalyze 如何知道使用哪个密钥？

A: 当前使用第一个可用的密钥。后续版本会支持：
- 按项目选择
- 按模型类型自动路由
- 基于成本的智能选择

### Q5: LLM Manager 支持导入其他工具的配置吗？

A: 暂不支持。可能在后续版本中添加。

## 故障排除

### 问题：无法访问 LLM Manager UI

**检查清单：**
1. 确认后端 API 已启动：`http://localhost:8200/health`
2. 检查防火墙设置
3. 确认端口 8200 未被占用
4. 查看后端日志获取错误信息

### 问题：添加 API 密钥后仍无法使用

**解决步骤：**
1. 确认密钥格式正确（以 sk- 开头的 OpenAI 密钥等）
2. 测试密钥的有效性（在官方工具中验证）
3. 检查 API 配额限制
4. 查看调用日志中的错误信息

### 问题：性能下降

**优化建议：**
1. 定期清理过期的调用日志
2. 检查数据库大小
3. 限制同时活跃的连接数
4. 升级到更高性能的部署环境

## 高级配置

### 环境变量

可通过以下环境变量配置 LLM Manager：

```powershell
# 数据库位置
$env:LLM_MANAGER_DB_PATH = "C:\path\to\db.sqlite"

# 日志级别
$env:LOG_LEVEL = "INFO"

# API 超时时间（秒）
$env:API_TIMEOUT = "30"
```

### 自定义主题

LLM Manager UI 支持主题定制：

```python
mount_to_fastapi(
    app,
    prefix="/llm-manager",
    config={
        "theme": "dark",  # 或 "light"
        "app_title": "My LLM Manager",
        "primary_color": "#007AFF"
    }
)
```

## 与其他工具的集成

### 与 DeepAnalyze 的整合

已完全集成，DeepAnalyze 中的所有需要 LLM 的功能都会自动使用 LLM Manager 管理的密钥。

### 与其他应用的集成

如需在其他应用中使用 LLM Manager 的密钥：

```python
import requests

# 获取可用的渠道
response = requests.get("http://localhost:8200/llm-manager/api/channels")
channels = response.json()["data"]

# 使用第一个渠道的信息
api_key = channels[0]["api_key"]  # 实际应用中需要解密
```

## 更新和维护

### 检查更新

```bash
pip install --upgrade llm-api-manager
```

### 备份数据

定期备份 LLM Manager 数据库：

```powershell
Copy-Item "llm_manager.db" "backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').db"
```

### 清理日志

```bash
# 清理 30 天前的日志
DELETE FROM api_logs WHERE created_at < datetime('now', '-30 days');
```

## 性能指标

- **密钥加密/解密**：< 1ms
- **查询密钥列表**：< 10ms
- **创建新渠道**：< 50ms
- **API 调用日志写入**：< 100ms

## 许可证和支持

- 许可证：MIT
- 官方文档：https://github.com/llm-api-manager/llm-api-manager
- 问题报告：GitHub Issues

## 后续功能计划

- 🔄 支持导入/导出密钥配置
- 📊 更详细的成本分析和预算控制
- 🔐 支持 2FA 身份验证
- 🌐 国际化支持（多语言）
- 📱 移动应用管理
- 🤖 AI 驱动的供应商推荐

---

**最后更新**：2025-12-01  
**版本**：2.0.0
