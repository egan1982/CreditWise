<p align="center" width="100%">
<img src="assets/logo.png" alt="DeepAnalyze" style="width: 60%; min-width: 300px; display: block; margin: auto;">
</p>

# DeepAnalyze CreditWise: AI-Powered Credit Risk Management Platform

> 基于 DeepAnalyze 的信贷风控专用版本，专注于规则挖掘、评分卡建模和策略分析

## 🚀 快速开始（使用外部API）

本项目已配置为使用外部API（如DeepSeek），无需本地大模型。

### 1. 设置API密钥
```powershell
# 设置API密钥（只需执行一次）
$env:DEEPSEEK_API_KEY = "your-api-key-here"
```

> 💡 也可以通过 [LLM Manager 管理界面](http://localhost:8200/llm-manager) 在线配置 API 密钥，支持多供应商管理、连接测试和负载均衡。

### 2. 启动完整服务（推荐）
```powershell
# 自动启动前后端服务并打开浏览器
.\start_all_api.ps1
```

### 3. 其他启动选项
```powershell
# 仅启动后端API服务
.\start_api_only.ps1

# 仅启动前端服务（需后端已运行）
.\start_frontend.ps1

# 测试API是否正常工作
.\test_api.ps1
```

> 💡 **提示**：首次运行时，脚本会自动创建虚拟环境和安装依赖，请耐心等待。
>
> 📖 **详细说明**：查看 [SCRIPT_USAGE.md](./SCRIPT_USAGE.md) 了解更多脚本功能、故障排除和配置选项。

---

> 本项目基于 [ruc-datalab/DeepAnalyze](https://github.com/ruc-datalab/DeepAnalyze) 二次开发，由 [egan1982](https://github.com/egan1982) 维护。

**DeepAnalyze** is first agentic LLM for autonomous data science. It can autonomously complete a wide range of data-centric tasks without human intervention, supporting:
- 🛠 **Entire data science pipeline**: Automatically perform any data science tasks such as data preparation, analysis, modeling, visualization, and report generation.
- 🔍 **Open-ended data research**: Conduct deep research on diverse data sources, including structured data (Databases, CSV, Excel), semi-structured data (JSON, XML, YAML), and unstructured data (TXT, Markdown), and finally produce analyst-grade research reports.
- 🌐 **Multiple API support**: Integrated with various LLM providers including OpenAI, GoogleAI, DeepSeek, Claude, and custom APIs for flexible deployment.

## 🌐 多供应商API管理

本项目集成了LLM Manager，提供以下功能：

### 支持的供应商
- **OpenAI**: GPT系列模型
- **GoogleAI**: Gemini系列模型
- **DeepSeek**: DeepSeek系列模型
- **Claude**: Anthropic Claude系列模型
- **通义千问**: 阿里云通义千问系列模型
- **自定义**: 任何兼容OpenAI格式的API

### 功能特性
- 🔧 **配置管理**: 创建、编辑、删除API配置
- 🧪 **连接测试**: 测试API连接和模型响应
- ⚖️ **负载均衡**: 多渠道智能负载分发
- 📊 **API日志**: 完整的API调用记录和统计
- 🖥️ **管理界面**: 直观的Web管理界面

## 🚀 API接口

本项目提供OpenAI兼容的API接口，可直接替换现有的OpenAI集成：

### 基本用法
```python
import openai

# 配置API端点
client = openai.OpenAI(
    base_url="http://localhost:8200/llm-manager/api/proxy",
    api_key="your-api-key"
)

# 进行对话
response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "user", "content": "分析这个数据集"}
    ],
    temperature=0.7
)

print(response.choices[0].message.content)
```

### API端点
- 聊天完成: `POST /llm-manager/api/proxy/chat/completions`
- 文件上传: `POST /llm-manager/api/proxy/files`
- 模型列表: `GET /llm-manager/api/proxy/models`

## 📊 管理界面

访问 http://localhost:3001 使用管理界面：

### 标签页功能
- **配置管理**: 管理API供应商配置
- **API日志**: 查看API调用历史和统计
- **统计信息**: 系统使用统计（开发中）
- **系统设置**: 系统配置（开发中）

## 🛠️ 环境要求

- Python 3.8+
- Node.js 16+
- PowerShell（Windows）或Shell（Linux/macOS）

## 📦 核心依赖

### 数据处理与分析
- **numpy / pandas** - 数据处理与计算
- **scipy** - 科学计算与统计检验
- **scikit-learn** - 机器学习与特征工程

### 可视化
- **matplotlib / seaborn** - 静态可视化
- **plotly** - 交互式可视化

### 统计分析（特征相关性分析）
- **statsmodels** - 偏相关、多变量回归、深度统计分析
- **pingouin** - 多种相关性检验、效应量计算

### 评分卡建模
- **scorecardpy** - WOE/IV分析、评分卡开发

## 📦 安装和部署

### Windows用户
```powershell
# 克隆仓库
git clone https://github.com/egan1982/CreditWise.git
cd CreditWise

# 一键启动（自动安装依赖）
.\start_all_api.ps1
```

### Linux/macOS用户
```bash
# 克隆仓库
git clone https://github.com/egan1982/CreditWise.git
cd CreditWise

# 设置环境变量
export DEEPSEEK_API_KEY="your-api-key-here"

# 启动服务
chmod +x scripts/*.sh
./scripts/start_all.sh
```

## 🔄 API代理配置

### 添加新供应商
1. 打开管理界面 http://localhost:3001
2. 点击"新建配置"
3. 填写供应商信息：
   - 配置名称：自定义名称
   - 配置类型：选择支持的供应商
   - 模型名称：要使用的模型
   - API Url：供应商API端点
   - API密钥：您的API密钥
4. 点击"测试模型响应"验证配置
5. 保存配置

### 负载均衡
系统支持多渠道负载均衡：
- 自动选择可用渠道
- 失败重试机制
- 权重配置（开发中）

## 📝 API日志和监控

### 日志记录
- 请求/响应详情
- Token使用统计
- 响应时间记录
- 错误日志

### 监控指标
- API调用次数
- 成功率统计
- 成本分析（开发中）

## 🤝 贡献

我们欢迎各种形式的贡献，包括代码改进、文档更新、bug报告和功能建议。

### 开发环境设置
```bash
# 克隆仓库
git clone https://github.com/egan1982/CreditWise.git
cd CreditWise

# 创建Python虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# 或
.venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 启动开发环境
.\start_dev.ps1  # Windows
# 或
./scripts/start_dev.sh  # Linux/macOS
```

## 📄 许可证

本项目采用 [MIT许可证](LICENSE)。

## 🙏 致谢

- FastAPI: 现代化的Python Web框架
- LLM Manager: API管理和代理系统
- Tailwind CSS: 实用优先的CSS框架
- Vite: 快速的前端构建工具

## 📋 原始论文引用

本项目基于 DeepAnalyze 二次开发，如需引用原始论文：

```bibtex
@misc{zhang2025deepanalyze,
  title={DeepAnalyze: Agentic Large Language Models for Autonomous Data Science},
  author={Shaolei Zhang and Ju Fan and Meihao Fan and Guoliang Li and Xiaoyong Du},
  year={2025},
  eprint={2510.16872},
  archivePrefix={arXiv},
  primaryClass={cs.AI}
}
```