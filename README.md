<p align="center" width="100%">
<img src="assets/logo.png" alt="CreditWise" style="width: 60%; min-width: 300px; display: block; margin: auto;">
</p>

# CreditWise: AI 驱动的信贷风控智能分析平台

[![Version](https://img.shields.io/badge/version-1.0.0--beta.2-blue)](./CHANGELOG.md)
[![License](https://img.shields.io/badge/license-MIT-green)](./LICENSE)

> 在 [DeepAnalyze](https://github.com/ruc-datalab/DeepAnalyze) 基础上深度重构的信贷风控智能分析平台。以 **LLM + Pipeline 混合架构**为核心，将风控分析中最耗时的**规则挖掘**和**评分卡建模**从数天的手工编程升级为分钟级自动完成。
>
> 🚧 下一阶段将拓展**策略诊断**（Swap Set 分析、新旧策略对比评估）、贷后监控、客群分层等 SOP 任务。

---

## 🏗️ 架构特色：LLM + Pipeline

```
用户自然语言 ──→ LLM（智能网关） ──→ Pipeline 引擎（确定性执行）
                  │                        │
                  │  理解意图、提取参数      │  预定义代码步骤
                  │  不参与执行              │  结果可复现
```

- **LLM** 充当"智能入口"，将用户意图转为结构化任务参数
- **Pipeline** 按预定义阶段顺序执行，保证结果确定性和可复现性
- 两者解耦，LLM 只在入口处介入一次

---

## 🎯 核心能力

### 📊 规则挖掘
完整的风控策略规则自动发现流程：

```
数据预处理 → 特征工程 → 规则生成（决策树/阈值分箱）→ 规则筛选 → 最优选择 → 报告生成
```

- 支持单变量（等频/等距/卡方/决策树分箱）和多变量（决策树组合）两种挖掘模式
- 自动评估 recall / bad_rate / lift / hit_rate，贪婪算法选择最优规则集
- OOT 时间稳定性验证（PSI），规则质量检测（覆盖率/冲突/重叠/冗余）

### 📈 评分卡开发
端到端信贷评分卡建模流程：

```
数据加载 → WOE 分箱 → 特征选择 → 逻辑回归 → 评分刻度转换 → 模型评估 → 报告生成
```

- 自动 WOE/IV 分析，多轮特征筛选（IV → 相关性 → VIF → 逐步回归）
- 统计逻辑回归（标准误、p值、置信区间），评分刻度转换（base_score/pdo）
- KS / ROC / AUC / 评分分布完整评估

### 🔧 LLM Manager 多渠道路由
- **多供应商**：OpenAI、DeepSeek、Claude、Google、通义千问、自定义 API
- **负载均衡**：多渠道智能分发，失败自动切换
- **Web 管理界面**：可视化配置 API 密钥、模型参数、联网搜索、深度思考

---

## 🚀 快速开始

### 1. 设置 API 密钥

```bash
# macOS / Linux
export DEEPSEEK_API_KEY="your-api-key-here"

# Windows PowerShell
$env:DEEPSEEK_API_KEY = "your-api-key-here"
```

> 💡 也可通过 [LLM Manager 管理界面](http://localhost:8200/llm-manager) 在线配置，支持多供应商管理和连接测试。

### 2. 启动服务

```bash
# macOS / Linux — 开发模式（推荐）
python API/main.py

# Docker 部署
cd docker && docker compose up -d

# Docker 内网多用户模式
ENABLE_AUTH=true docker compose up -d
```

```powershell
# Windows — 一键启动
.\start_all_api.ps1
```

> 首次运行时自动创建虚拟环境和安装依赖。默认端口 `8200`。

### 3. 访问

| 服务 | 地址 |
|------|------|
| 主应用 | http://localhost:8200 |
| API 文档 | http://localhost:8200/docs |
| LLM Manager | http://localhost:8200/llm-manager |

---

## 📦 环境要求

- Python 3.10–3.12
- Node.js 18+（前端开发）
- Docker 20.10+（可选，用于容器化部署）

---

## 🛠️ 技术栈

| 层 | 技术 |
|---|---|
| Web 框架 | FastAPI + uvicorn |
| 数据处理 | pandas、numpy、scikit-learn |
| 信用风控专项 | scorecardpy、scipy、statsmodels |
| 可视化 | matplotlib、seaborn、plotly |
| LLM 接入 | openai SDK（多 provider 兼容） |
| 存储 | SQLAlchemy |

---

## 📖 详细文档

| 文档 | 说明 |
|------|------|
| [docs/project_feature_highlights.md](./docs/project_feature_highlights.md) | 功能亮点与业务价值 |
| [docs/deployment_guide.md](./docs/deployment_guide.md) | 部署指南（Docker/手动/Win/Mac/Linux） |
| [docs/user_manual.md](./docs/user_manual.md) | 用户使用手册（含 LLM 配置、任务操作、报告导出） |
| [docs/project_development_review.md](./docs/project_development_review.md) | 项目开发复盘报告 |
| [CHANGELOG.md](./CHANGELOG.md) | 功能开发清单 |
| [RELEASE_NOTES.md](./RELEASE_NOTES.md) | 版本发布说明 |

---

## 📄 许可证

本项目基于 [MIT 许可证](LICENSE)，由 [egan1982](https://github.com/egan1982) 维护。

### 原始论文引用

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
