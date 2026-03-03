# SOP任务报告生成与AI分析评估通用框架设计

## 1. 背景与目标

### 1.1 问题背景

当前规则挖掘任务的`report_generation`阶段完成后，AI分析评估显示：
> 「报告生成阶段已完成，但提供的文件列表主要为系统配置文件与代码，未见建模报告文档（如PDF/Word）。关键标记为【需关注】。」

**根本原因**：
| 层面 | 问题描述 |
|------|----------|
| 设计层面 | 当前`report_generation`阶段只生成数据供前端展示，未生成实际报告文档 |
| Prompt层面 | AI分析的数据描述缺少报告形式说明 |
| 期望差异 | AI基于行业惯例（报告生成=输出PDF/Word）进行判断 |

### 1.2 设计目标

1. **AI整体分析评估**：任务完成后自动/手动生成任务整体的AI分析评估结果
2. **实际报告生成**：`report_generation`阶段自动生成可下载的报告文档
3. **通用框架**：设计可复用于所有SOP类任务的通用框架

---

## 2. 任务类型与Tab结构对比

### 2.1 规则挖掘任务

**阶段结构**（6个阶段）：
```
preprocessing → feature_engineering → generating_rules → 
rule_filtering → selecting_rules → report_generation
```

**开发结果Tab**（8个）：
| Tab ID | 名称 | 数据来源 | 纳入报告 | 纳入AI分析 |
|--------|------|----------|----------|------------|
| sample-feature | 样本及特征 | preprocessing + feature_engineering | ✅ | ✅ |
| charts | 评估图表 | chart_data | ✅ | ✅ |
| optimal | 最优规则 | optimal_rules | ✅ | ✅ |
| filtering-process | 筛选过程 | all_rules_with_status | ✅ | ✅（统计摘要） |
| validation | 质量验证 | validation_report | ✅ | ✅ |
| psi | 稳定性 | psi_report | ✅ | ✅ |
| advanced | 附加分析 | amount_analysis, prior_analysis | ✅（如有） | ✅（如有） |
| tree | 决策树 | tree_structure | ❌ | ❌ |

### 2.2 评分卡开发任务

**阶段结构**（7个阶段）：
```
data_loading → woe_binning → feature_selection → model_training → 
score_scaling → model_evaluation → report_generation
```

**开发结果Tab**（7个）：
| Tab ID | 名称 | 数据来源 | 纳入报告 | 纳入AI分析 |
|--------|------|----------|----------|------------|
| charts | 评估图表 | ks_curve, roc_curve, auc | ✅ | ✅ |
| selection | 特征筛选 | feature_selection | ✅ | ✅ |
| scorecard | 评分卡明细 | scorecard | ✅ | ✅ |
| iv | IV值排序 | iv_values | ✅ | ✅ |
| coefficients | 模型系数 | model_coefficients | ✅ | ✅ |
| statistics | 统计检验 | model_statistics | ✅ | ✅ |
| converter | 评分转换 | score_params | ❌（交互式） | ❌ |

### 2.3 共同模式

```
┌─────────────────────────────────────────────────────────────┐
│                     SOP任务通用模式                          │
├─────────────────────────────────────────────────────────────┤
│  数据预处理阶段  →  核心处理阶段(N个)  →  报告生成阶段        │
├─────────────────────────────────────────────────────────────┤
│  开发结果Tab结构：                                           │
│  ├─ 数据/样本概况Tab                                        │
│  ├─ 评估图表Tab                                             │
│  ├─ 核心结果Tab（规则列表/评分卡）                          │
│  ├─ 验证/质量Tab                                            │
│  ├─ 稳定性/PSI Tab                                          │
│  └─ 附加/交互Tab（可选）                                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 通用框架设计

### 3.1 配置化接口定义

```typescript
// ==================== 核心配置接口 ====================

/**
 * 任务结果配置 - 每个SOP任务类型一份
 */
interface TaskResultConfig {
  taskType: string;                    // "rule_mining" | "scorecard_dev" | ...
  taskName: string;                    // "规则挖掘" | "评分卡开发" | ...
  tabs: TabConfig[];                   // Tab配置列表
  aiAnalysisConfig: AIAnalysisConfig;  // AI整体分析配置
  reportConfig: ReportConfig;          // 报告生成配置
  excelConfig: ExcelExportConfig;      // Excel导出配置
}

/**
 * Tab配置
 */
interface TabConfig {
  id: string;                          // Tab ID
  name: string;                        // Tab显示名称
  dataPath: string;                    // 从results中获取数据的路径
  includeInReport: boolean;            // 是否纳入PDF/Word报告
  includeInAIAnalysis: boolean;        // 是否纳入AI整体分析
  reportSection?: ReportSectionConfig; // 报告章节配置（如纳入报告）
  aiAnalysisMetrics?: string[];        // AI分析关注指标（如纳入分析）
}

/**
 * AI整体分析配置
 */
interface AIAnalysisConfig {
  role: string;                        // AI角色定义
  taskDescription: string;             // 任务描述
  focusAreas: string[];                // 重点关注领域
  outputRequirements: {
    maxWords: number;                  // 最大字数
    sections: string[];                // 输出章节
  };
  promptTemplate: string;              // Prompt模板
}

/**
 * 报告生成配置
 */
interface ReportConfig {
  title: string;                       // 报告标题
  includeAISummary: boolean;           // 是否包含AI分析作为执行摘要
  sections: ReportSectionConfig[];     // 报告章节配置
  supportedFormats: ExportFormat[];    // 支持的导出格式
}

/**
 * 导出格式类型
 * 当前系统支持：HTML、Excel、Word、PDF、JSON（共5种）
 */
type ExportFormat = 'html' | 'excel' | 'word' | 'pdf' | 'json';

/**
 * 报告章节配置
 */
interface ReportSectionConfig {
  id: string;
  title: string;
  order: number;
  dataPath: string;
  renderType: 'table' | 'chart' | 'text' | 'mixed';
  chartConfig?: ChartRenderConfig;     // 图表渲染配置
}

/**
 * Excel导出配置
 */
interface ExcelExportConfig {
  includeDirectory: boolean;           // 是否包含目录Sheet
  tabSheets: TabSheetConfig[];         // Tab对应的Sheet配置
  stageDataSheets: StageDataSheetConfig[]; // 阶段数据Sheet配置
}
```

### 3.2 规则挖掘任务配置示例

```typescript
const RULE_MINING_RESULT_CONFIG: TaskResultConfig = {
  taskType: "rule_mining",
  taskName: "规则挖掘",
  
  tabs: [
    {
      id: "sample-feature",
      name: "样本及特征",
      dataPath: "stages.preprocessing,stages.feature_engineering",
      includeInReport: true,
      includeInAIAnalysis: true,
      aiAnalysisMetrics: ["total_rows", "bad_rate", "feature_count", "iv_distribution"]
    },
    {
      id: "charts",
      name: "评估图表",
      dataPath: "chart_data",
      includeInReport: true,
      includeInAIAnalysis: true,
      aiAnalysisMetrics: ["cumulative_recall", "cumulative_hit_rate", "cumulative_lift"]
    },
    {
      id: "optimal",
      name: "最优规则",
      dataPath: "optimal_rules",
      includeInReport: true,
      includeInAIAnalysis: true,
      aiAnalysisMetrics: ["rule_count", "total_recall", "avg_lift"]
    },
    {
      id: "validation",
      name: "质量验证",
      dataPath: "validation_report",
      includeInReport: true,
      includeInAIAnalysis: true,
      aiAnalysisMetrics: ["quality_score", "validation_issues"]
    },
    {
      id: "psi",
      name: "稳定性",
      dataPath: "psi_report",
      includeInReport: true,
      includeInAIAnalysis: true,
      aiAnalysisMetrics: ["stable_count", "unstable_count", "avg_psi"]
    },
    {
      id: "tree",
      name: "决策树",
      dataPath: "tree_structure",
      includeInReport: false,  // 交互式可视化不纳入报告
      includeInAIAnalysis: false
    }
  ],
  
  aiAnalysisConfig: {
    role: "资深风控建模专家",
    taskDescription: "规则挖掘任务",
    focusAreas: ["规则质量", "召回效果", "稳定性", "业务可解释性"],
    outputRequirements: {
      maxWords: 200,
      sections: ["执行摘要", "关键发现", "风险提示", "优化建议"]
    },
    promptTemplate: `角色：{role}
任务：对{taskDescription}进行整体评估

输入数据：
{dataDescription}

输出要求（{maxWords}字以内）：
1. 执行摘要：3-5句话总结任务执行情况
2. 关键发现：按重要性排序的2-3个亮点或问题
3. 风险提示：如有需关注的指标
4. 优化建议：可操作的下一步建议`
  },
  
  reportConfig: {
    title: "规则挖掘分析报告",
    includeAISummary: true,
    sections: [
      { id: "summary", title: "执行摘要", order: 1, dataPath: "ai_analysis", renderType: "text" },
      { id: "sample", title: "样本及特征分析", order: 2, dataPath: "stages", renderType: "mixed" },
      { id: "rules", title: "规则挖掘结果", order: 3, dataPath: "optimal_rules", renderType: "table" },
      { id: "charts", title: "评估图表", order: 4, dataPath: "chart_data", renderType: "chart" },
      { id: "validation", title: "质量验证", order: 5, dataPath: "validation_report", renderType: "mixed" },
      { id: "psi", title: "稳定性分析", order: 6, dataPath: "psi_report", renderType: "table" }
    ],
    supportedFormats: ['pdf', 'word', 'html']
  },
  
  excelConfig: {
    includeDirectory: true,
    tabSheets: [
      { tabId: "sample-feature", sheetName: "样本及特征" },
      { tabId: "optimal", sheetName: "最优规则" },
      { tabId: "filtering-process", sheetName: "筛选过程" },
      { tabId: "validation", sheetName: "质量验证" },
      { tabId: "psi", sheetName: "稳定性分析" }
    ],
    stageDataSheets: [
      { stageId: "preprocessing", sheetName: "[阶段] 数据预处理" },
      { stageId: "feature_engineering", sheetName: "[阶段] 特征工程" },
      { stageId: "generating_rules", sheetName: "[阶段] 规则生成" },
      { stageId: "rule_filtering", sheetName: "[阶段] 规则过滤" },
      { stageId: "selecting_rules", sheetName: "[阶段] 规则选择" }
    ]
  }
};
```

### 3.3 评分卡开发任务配置示例

```typescript
const SCORECARD_RESULT_CONFIG: TaskResultConfig = {
  taskType: "scorecard_dev",
  taskName: "评分卡开发",
  
  tabs: [
    {
      id: "charts",
      name: "评估图表",
      dataPath: "evaluation",
      includeInReport: true,
      includeInAIAnalysis: true,
      aiAnalysisMetrics: ["ks", "auc", "gini"]
    },
    {
      id: "selection",
      name: "特征筛选",
      dataPath: "feature_selection",
      includeInReport: true,
      includeInAIAnalysis: true,
      aiAnalysisMetrics: ["selected_count", "avg_iv"]
    },
    {
      id: "scorecard",
      name: "评分卡明细",
      dataPath: "scorecard",
      includeInReport: true,
      includeInAIAnalysis: true,
      aiAnalysisMetrics: ["variable_count", "score_range"]
    },
    {
      id: "coefficients",
      name: "模型系数",
      dataPath: "model_coefficients",
      includeInReport: true,
      includeInAIAnalysis: true,
      aiAnalysisMetrics: ["significant_vars", "intercept"]
    },
    {
      id: "converter",
      name: "评分转换",
      dataPath: "score_params",
      includeInReport: false,  // 交互式工具不纳入报告
      includeInAIAnalysis: false
    }
  ],
  
  aiAnalysisConfig: {
    role: "资深风控建模专家",
    taskDescription: "评分卡开发任务",
    focusAreas: ["模型区分能力", "特征稳定性", "评分分布", "业务合理性"],
    outputRequirements: {
      maxWords: 200,
      sections: ["执行摘要", "关键发现", "风险提示", "优化建议"]
    },
    promptTemplate: `角色：{role}
任务：对{taskDescription}进行整体评估

输入数据：
{dataDescription}

输出要求（{maxWords}字以内）：
1. 执行摘要：3-5句话总结任务执行情况
2. 关键发现：按重要性排序的2-3个亮点或问题
3. 风险提示：如有需关注的指标
4. 优化建议：可操作的下一步建议`
  },
  
  reportConfig: {
    title: "评分卡开发报告",
    includeAISummary: true,
    sections: [
      { id: "summary", title: "执行摘要", order: 1, dataPath: "ai_analysis", renderType: "text" },
      { id: "data", title: "数据概况", order: 2, dataPath: "data_summary", renderType: "mixed" },
      { id: "woe", title: "WOE分箱与特征筛选", order: 3, dataPath: "woe_binning", renderType: "table" },
      { id: "model", title: "模型训练与系数", order: 4, dataPath: "model", renderType: "table" },
      { id: "eval", title: "模型评估", order: 5, dataPath: "evaluation", renderType: "chart" },
      { id: "scorecard", title: "评分卡与刻度", order: 6, dataPath: "scorecard", renderType: "table" }
    ],
    supportedFormats: ['pdf', 'word', 'html']
  },
  
  excelConfig: {
    includeDirectory: true,
    tabSheets: [
      { tabId: "selection", sheetName: "特征筛选" },
      { tabId: "scorecard", sheetName: "评分卡明细" },
      { tabId: "iv", sheetName: "IV值排序" },
      { tabId: "coefficients", sheetName: "模型系数" },
      { tabId: "statistics", sheetName: "统计检验" }
    ],
    stageDataSheets: [
      { stageId: "data_loading", sheetName: "[阶段] 数据加载" },
      { stageId: "woe_binning", sheetName: "[阶段] WOE分箱" },
      { stageId: "feature_selection", sheetName: "[阶段] 特征筛选" },
      { stageId: "model_training", sheetName: "[阶段] 模型训练" },
      { stageId: "model_evaluation", sheetName: "[阶段] 模型评估" }
    ]
  }
};
```

---

## 4. AI整体分析评估方案

### 4.1 触发机制

```
┌─────────────────────────────────────────────────────────────┐
│                    AI整体分析触发流程                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐      ┌──────────────┐                    │
│  │  专家模式    │      │  自动模式    │                    │
│  └──────┬───────┘      └──────┬───────┘                    │
│         │                     │                             │
│         ▼                     ▼                             │
│  report_generation      任务执行完成                        │
│  阶段完成                     │                             │
│         │                     ▼                             │
│         ▼              用户点击"AI分析                      │
│  自动触发AI整体         评估"按钮                           │
│  分析                        │                             │
│         │                     │                             │
│         └─────────┬───────────┘                            │
│                   ▼                                         │
│         ┌─────────────────┐                                │
│         │ 构建整体分析    │                                │
│         │ Prompt          │                                │
│         └────────┬────────┘                                │
│                  ▼                                          │
│         ┌─────────────────┐                                │
│         │ 调用LLM生成     │                                │
│         │ 整体评估        │                                │
│         └────────┬────────┘                                │
│                  ▼                                          │
│         ┌─────────────────┐                                │
│         │ 展示在开发结果  │                                │
│         │ 顶部区域        │                                │
│         └─────────────────┘                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 4.1.1 容错设计

**核心原则**：AI分析失败不应阻塞报告导出功能。

```
┌─────────────────────────────────────────────────────────────┐
│                    AI分析容错流程                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐                                          │
│  │ 任务完成     │                                          │
│  └──────┬───────┘                                          │
│         │                                                   │
│         ├───────────────┬───────────────┐                  │
│         ▼               ▼               ▼                  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │
│  │ AI分析成功   │ │ AI分析失败   │ │ 跳过AI分析   │       │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘       │
│         │               │               │                  │
│         ▼               ▼               ▼                  │
│  ┌──────────────────────────────────────────────────┐     │
│  │          报告导出功能始终可用                     │     │
│  │  - 有AI分析：纳入执行摘要章节                    │     │
│  │  - 无AI分析：直接生成数据报告                    │     │
│  └──────────────────────────────────────────────────┘     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**前端处理**：
- AI分析失败时显示重试按钮
- 提示用户「AI分析失败不影响报告导出」
- 自动模式下提示「不生成AI分析也可直接导出报告」

**后端处理**：
- Word/PDF报告生成时尝试获取AI分析
- 获取失败静默处理（`ai_analysis=None`）
- 报告正常生成，只是不包含执行摘要章节

### 4.2 数据源设计

**关键设计决策**：不整合各阶段已缓存的AI分析，使用专属整体Prompt

**理由**：
1. **一致性优先**：自动模式没有阶段缓存，整合会导致两种模式结果差异
2. **用户体验**：阶段AI分析在右侧面板已展示，用户可自行查阅
3. **输出聚焦**：整体分析应是「执行摘要」性质，关注结论和建议

**数据获取逻辑**：
```typescript
function buildOverallAnalysisData(
  taskConfig: TaskResultConfig,
  results: ExecutionResult,
  stagesData: Record<string, StageData>
): AnalysisDataInput {
  const data: AnalysisDataInput = {};
  
  for (const tab of taskConfig.tabs) {
    if (!tab.includeInAIAnalysis) continue;
    
    // 从results或stagesData中获取数据
    const tabData = getDataByPath(results, stagesData, tab.dataPath);
    
    // 提取关注指标
    if (tab.aiAnalysisMetrics) {
      data[tab.id] = extractMetrics(tabData, tab.aiAnalysisMetrics);
    }
  }
  
  return data;
}
```

### 4.3 Prompt模板设计

**通用模板框架**：
```
角色：{config.aiAnalysisConfig.role}
任务：对{config.taskName}进行整体评估

## 任务背景
{config.aiAnalysisConfig.taskDescription}

## 输入数据
{dynamicDataDescription}

## 重点关注
{config.aiAnalysisConfig.focusAreas.join('、')}

## 输出要求（{config.aiAnalysisConfig.outputRequirements.maxWords}字以内）
{config.aiAnalysisConfig.outputRequirements.sections.map((s, i) => `${i+1}. ${s}`).join('\n')}

## 注意事项
- 基于数据客观评估，避免主观臆断
- 关键指标需给出具体数值
- 风险提示需具有可操作性
- 建议需结合业务场景
```

**规则挖掘数据描述示例**：
```
## 输入数据

### 1. 样本及特征概况
- 样本总量：{total_rows}条
- 坏样本率：{bad_rate}%
- 入模特征数：{feature_count}个

### 2. 规则挖掘结果
- 候选规则数：{total_candidate}条
- 最终入选：{rule_count}条
- 平均提升度：{avg_lift}
- 平均坏账率：{avg_bad_rate}%

### 3. 累计效果（规则叠加后）
- 累计召回率：{total_recall}%
- 累计命中率：{total_hit_rate}%
- 累计坏账率：{cum_bad_rate}%
- 累计提升度：{cum_lift}

### 4. 规则筛选过程
- 淘汰规则数：{rejected_count}条
- 主要淘汰原因：
  - {reason_1}：{count_1}条 ({pct_1}%)
  - {reason_2}：{count_2}条 ({pct_2}%)

### 5. 质量验证
- 质量评分：{quality_score}/100
- 规则重叠度：{avg_overlap}%
- 验证问题：{validation_issues}

### 6. 稳定性分析（PSI）
- 稳定规则：{stable_count}条 (PSI<0.1)
- 不稳定规则：{unstable_count}条 (PSI≥0.25)
- 平均PSI：{avg_psi}
```

---

## 5. 报告生成方案

### 5.1 当前支持的导出格式

系统支持**5种**导出格式（已将HTML替换为Markdown）：

| 格式 | 实现方式 | 定位 | 目标用户 | 包含AI分析 |
|------|----------|------|----------|------------|
| **Markdown** | 前端直接生成 | 技术文档/知识库 | 技术团队 | ✅ 可包含 |
| **Excel** | 后端生成xlsx(base64) | 详细数据 | 分析师 | ❌（文本展示效果差） |
| **Word** | 后端生成docx(base64) | 可编辑报告 | 业务团队 | ✅ 作为执行摘要 |
| **PDF** | 前端打开HTML后浏览器打印 | 正式交付物 | 管理层/决策者 | ✅ 作为执行摘要 |
| **JSON** | 前端直接导出原始数据 | 原始数据 | 开发/调试 | ❌（原始数据格式） |

### 5.2 Markdown格式实现

**已实现**：前端直接生成Markdown报告

```typescript
// RuleMiningResults.tsx / ScorecardResults.tsx
const generateMarkdownReport = (): string => {
  let md = `# ${taskName}分析报告\n\n`;
  md += `> 生成时间: ${new Date().toLocaleString()}\n\n`;
  
  // 执行摘要
  md += `## 1. 执行摘要\n\n`;
  md += `| 指标 | 值 |\n|------|----|\n`;
  // ... 数据填充
  
  // 核心结果
  md += `## 2. ${coreResultTitle}\n\n`;
  // ... 表格数据
  
  return md;
};

// 下载逻辑
if (format === 'markdown') {
  const md = generateMarkdownReport();
  const blob = new Blob([md], { type: "text/markdown;charset=utf-8" });
  // 下载...
}
```

**Markdown格式优势**：
- 纯文本，易于版本管理（Git友好）
- 可直接集成到知识库（Notion/Confluence/Wiki）
- 无需后端依赖，前端即可生成
- 人工可读可编辑

### 5.3 图文报告结构（Word/PDF）

**通用章节框架**：
```
┌─────────────────────────────────────────┐
│              [任务名称]分析报告          │
├─────────────────────────────────────────┤
│                                         │
│  1. 执行摘要                            │
│     └─ AI整体分析评估结果               │
│                                         │
│  2. 数据概况                            │
│     ├─ 样本统计                         │
│     └─ 特征概况                         │
│                                         │
│  3. [核心结果章节 - 任务特定]           │
│     ├─ 规则挖掘: 最优规则列表           │
│     └─ 评分卡: 评分卡明细表             │
│                                         │
│  4. 评估图表                            │
│     └─ 关键指标曲线图                   │
│                                         │
│  5. 质量验证                            │
│     ├─ 验证结果                         │
│     └─ 问题说明                         │
│                                         │
│  6. 稳定性分析                          │
│     └─ PSI分布                          │
│                                         │
│  [附录: 附加分析（如有）]               │
│                                         │
└─────────────────────────────────────────┘
```

### 5.4 Excel报告结构

**Sheet组织**：
```
Excel工作簿结构：
├── 📋 目录（Directory）
│   └─ 说明各Sheet内容和来源
│
├── ═══ Tab内容区 ═══════════════════
├── 📊 样本及特征
├── 📊 最优规则/评分卡
├── 📊 质量验证
├── 📊 稳定性分析
├── ...
│
├── ═══ 阶段数据区 ═══════════════════
├── 📁 [阶段] 数据预处理
├── 📁 [阶段] 特征工程/WOE分箱
├── 📁 [阶段] 规则生成/模型训练
├── 📁 [阶段] 规则筛选/模型评估
└── ...
```

**目录Sheet内容**：
| Sheet名称 | 类型 | 说明 | 数据来源 |
|-----------|------|------|----------|
| 样本及特征 | Tab内容 | 数据预处理和特征统计 | preprocessing, feature_engineering |
| 最优规则 | Tab内容 | 最终选定的规则列表 | selecting_rules |
| ... | ... | ... | ... |
| [阶段] 数据预处理 | 阶段数据 | 预处理阶段完整输出 | preprocessing.download |

---

## 6. 实现方案

### 6.1 后端实现（Python）

**报告生成服务**：
```python
# deepanalyze/core/report_generator.py

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, Paragraph
from docx import Document
import openpyxl

class ReportGenerator(ABC):
    """报告生成器基类"""
    
    def __init__(self, config: TaskResultConfig):
        self.config = config
    
    @abstractmethod
    def generate(self, data: Dict[str, Any], ai_analysis: str) -> bytes:
        """生成报告"""
        pass


class PDFReportGenerator(ReportGenerator):
    """PDF报告生成器"""
    
    def generate(self, data: Dict[str, Any], ai_analysis: str) -> bytes:
        # 1. 创建文档
        # 2. 添加标题
        # 3. 添加执行摘要（AI分析）
        # 4. 按配置添加各章节
        # 5. 导出为bytes
        pass


class ExcelReportGenerator(ReportGenerator):
    """Excel报告生成器"""
    
    def generate(self, data: Dict[str, Any], stages_data: Dict) -> bytes:
        wb = openpyxl.Workbook()
        
        # 1. 创建目录Sheet
        self._create_directory_sheet(wb, data)
        
        # 2. 创建Tab内容Sheets
        for tab_config in self.config.excelConfig.tabSheets:
            self._create_tab_sheet(wb, tab_config, data)
        
        # 3. 创建阶段数据Sheets
        for stage_config in self.config.excelConfig.stageDataSheets:
            self._create_stage_sheet(wb, stage_config, stages_data)
        
        # 4. 导出为bytes
        return self._to_bytes(wb)
```

### 6.2 前端实现（TypeScript/React）

**AI整体分析组件**：
```typescript
// demo/chat/components/sop/OverallAIAnalysis.tsx

interface OverallAIAnalysisProps {
  taskType: string;
  results: ExecutionResult;
  stagesData: Record<string, StageData>;
  mode: 'expert' | 'auto';
  onAnalysisComplete?: (analysis: string) => void;
}

export function OverallAIAnalysis({
  taskType,
  results,
  stagesData,
  mode,
  onAnalysisComplete
}: OverallAIAnalysisProps) {
  const [analysis, setAnalysis] = useState<string>('');
  const [loading, setLoading] = useState(false);
  
  // 获取任务配置
  const config = getTaskResultConfig(taskType);
  
  // 专家模式自动触发
  useEffect(() => {
    if (mode === 'expert' && results.status === 'completed') {
      generateAnalysis();
    }
  }, [mode, results.status]);
  
  const generateAnalysis = async () => {
    setLoading(true);
    
    // 构建数据描述
    const dataDescription = buildDataDescription(config, results, stagesData);
    
    // 构建Prompt
    const prompt = buildOverallAnalysisPrompt(config, dataDescription);
    
    // 调用LLM
    const response = await callLLM(prompt);
    
    setAnalysis(response);
    setLoading(false);
    onAnalysisComplete?.(response);
  };
  
  return (
    <Card>
      <CardHeader>
        <CardTitle>AI整体分析评估</CardTitle>
        {mode === 'auto' && (
          <Button onClick={generateAnalysis} disabled={loading}>
            {loading ? <Loader2 className="animate-spin" /> : '生成分析'}
          </Button>
        )}
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton />
        ) : analysis ? (
          <div className="prose">{analysis}</div>
        ) : (
          <p className="text-muted-foreground">点击按钮生成AI分析评估</p>
        )}
      </CardContent>
    </Card>
  );
}
```

---

## 7. 实施计划

### 7.1 优先级排序

| 优先级 | 内容 | 工作量 | 价值 | 状态 |
|--------|------|--------|------|------|
| **P0** | AI整体分析功能（专家自动+自动手动） | 1天 | 解决当前AI评估问题 | ✅ 已完成 |
| **P0** | 任务结果配置框架 | 0.5天 | 支撑后续功能 | ✅ 已完成 |
| **P1** | ~~PDF报告生成~~ | ~~2天~~ | ~~行业标准交付物~~ | ❌ **已废弃**（改用HTML打印为PDF方案） |
| **P1** | ~~Excel目录Sheet~~ → **Excel任务报告Sheet** + 阶段数据整合 | 1天 | 分析师实用功能 | ✅ **已实现**（设计演进：目录Sheet → 任务报告Sheet，包含完整报告内容作为首位Sheet，阶段数据整合到独立Sheets） |
| **P2** | Word报告生成 | 1天 | 与HTML复用结构 | ✅ **已实现** |
| **P2** | 评分卡任务适配 | 1天 | 验证框架复用性 | ✅ 已完成 |

### 7.2 已实现内容（2026-01-21）

**后端实现**：
- `deepanalyze/core/task_manager/task_result_config.py` - 任务结果配置框架
- `deepanalyze/core/task_manager/overall_analysis_service.py` - AI整体分析服务
- `deepanalyze/core/task_manager/models.py` - 新增OverallAIAnalysis模型
- `API/sop_api.py` - 新增整体分析API端点

**前端实现**：
- `demo/chat/components/sop/OverallAIAnalysis.tsx` - AI整体分析组件
- `demo/chat/lib/sopService.ts` - 新增整体分析API函数
- `RuleMiningResults.tsx` / `ScorecardResults.tsx` - 集成AI分析组件

**API端点**：
```
GET  /sop/history/{record_id}/overall-analysis  - 获取整体分析
POST /sop/history/{record_id}/overall-analysis  - 保存整体分析
DELETE /sop/history/{record_id}/overall-analysis - 删除整体分析
POST /sop/overall-analysis/build-prompt         - 构建分析Prompt
```

### 7.3 待实施里程碑

```
Week 2:
├─ [P1] ~~PDF报告生成~~ → ❌ 已废弃，改用HTML打印为PDF方案
├─ [P1] ✅ ~~Excel目录Sheet~~ → **Excel任务报告Sheet** + 阶段数据整合（已完成，设计演进：目录索引 → 完整报告内容）
└─ [P1] ✅ AI分析在报告中的集成（已完成）

Week 3:
├─ [P2] ✅ Word报告生成（已完成）
└─ [P2] 端到端测试验证
```

---

## 8. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| AI整体分析Token消耗大 | 成本增加 | 数据摘要化，只传关键指标 |
| 报告生成耗时 | 用户体验 | 异步生成 + 进度提示 |
| 图表转图片质量 | 报告美观度 | 使用高DPI导出 |
| 新任务类型适配成本 | 扩展效率 | 严格遵循配置化设计 |

---

## 9. 总结

本设计文档定义了一个**高度可复用**的SOP任务报告生成与AI分析评估框架：

1. **配置化设计**：通过`TaskResultConfig`接口，新增任务类型只需添加配置
2. **触发机制统一**：专家模式自动触发，自动模式手动触发
3. **数据源一致**：使用专属Prompt，不依赖阶段缓存，保证两种模式结果一致
4. **报告格式差异化**：PDF/Word面向管理层（含AI分析），Excel面向分析师（详细数据）

**复用性评估**：
- 对评分卡任务：⭐⭐⭐⭐⭐ 100%框架复用
- 对其他SOP任务：⭐⭐⭐⭐⭐ 只需提供配置即可
