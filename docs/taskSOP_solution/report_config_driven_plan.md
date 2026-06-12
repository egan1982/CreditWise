# 报告版式配置驱动优化方案

> **状态**: ✅ Phase 0-1.6 全部已完成（报告版式重构完成），📋 Phase 2 配置驱动待实施（2026-06-12 核实：`FieldDisplayConfig`/`ConfigDrivenReportGenerator` 零代码）  
> **优先级**: P2（配置驱动方案 - 当前ROI评估中）  
> **开发评审**: 🟡 建议轻量评审 — Phase 0-1.6 已完成，Phase 2 需确认配置 schema 设计和可定制范围（2026-04-15 评估）  
>
> ### 📌 快速回顾（开发前必读）
>
> **作用与目标**：让报告内容（章节、字段、图表）由配置文件驱动，而非硬编码在 Python/TSX 中，实现报告可定制化。
>
> **当前实现的问题**：
> - `task_result_config.py` 中已有完整的 Tab 配置定义，但**完全没有被使用**
> - 前端 Tab（硬编码 JSX）、报告章节（硬编码 Python）、配置文件三者脱节
> - 修改报告内容需要改代码（前端 + 后端多处），无法通过配置快速调整
>
> **已完成**：Phase 0-1.6（报告版式重构：HTML/MD/Word/Excel 全部完成，统一为 6 章节结构）
>
> **Phase 2 待做**：实现 `FieldDisplayConfig`、`ConfigDrivenReportGenerator` 等配置驱动类，让前端 Tab 和报告生成器都读取同一份配置
>
> **后端变化**：新增配置驱动的报告生成器，`task_result_config.py` 从闲置变为实际使用
>
> **前端变化**：`RuleMiningResults.tsx`、`ScorecardResults.tsx` 的 Tab 结构从硬编码改为读取后端配置 API
>
> **创建时间**: 2026-02-09  
> **最后更新**: 2026-03-02（核实实现状态并更新文档）  
> **实际完成工作量**: ~2.5 人天（评分卡报告版式修改 HTML/MD/Word/Excel 全部完成）  
> **适用范围**: 所有 SOP 类任务（规则挖掘、评分卡开发、未来新增任务）  
> **实现核实**: 代码库中未找到 `FieldDisplayConfig`、`ConfigDrivenReportGenerator` 等配置驱动类，确认 Phase 2 未开始实施
> 
> **⚠️ 实施顺序决策**：必须先完成 Word 报告重构（Phase 1.5），再实施配置驱动方案（Phase 2）。  
> 原因：避免 Word 旧结构被固化到配置中，确保所有格式先统一到6章节结构。

---

## 〇、核心发现：配置与前端脱节问题

### 0.0 问题总结

**核心问题**：后端配置文件 `task_result_config.py` 存在完整的 Tab 配置定义，但**完全没有被使用**！

| 组件 | 实现方式 | 问题 |
|------|---------|------|
| 前端 Tab | 硬编码 JSX | 修改需要改代码 |
| 报告章节 | 硬编码 Python | 修改需要改代码 |
| 配置文件 | 存在但闲置 | 失去配置驱动的意义 |

```
┌─────────────────────────────────────────────────────────────────────┐
│                     后端配置文件                                      │
│             task_result_config.py                                    │
│  ┌─────────────────────┐    ┌─────────────────────┐                 │
│  │ RULE_MINING_CONFIG  │    │ SCORECARD_DEV_CONFIG │                │
│  │ 8 tabs (与前端一致)   │    │ 7 tabs (与前端不一致) │                │
│  └─────────────────────┘    └─────────────────────┘                 │
│               ↓ 未被使用              ↓ 未被使用                      │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                       前端组件                                        │
│  ┌──────────────────────┐    ┌──────────────────────┐               │
│  │ RuleMiningResults.tsx │    │ ScorecardResults.tsx │               │
│  │ 8 tabs (硬编码)        │    │ 5 tabs (硬编码)        │               │
│  │ ✅ 恰好与配置一致       │    │ ❌ 与配置不一致         │               │
│  └──────────────────────┘    └──────────────────────┘               │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                       报告生成器                                      │
│  ┌──────────────────────┐    ┌──────────────────────┐               │
│  │ html_report.py       │    │ word_report.py       │               │
│  │ 章节结构 (硬编码)      │    │ 章节结构 (硬编码)      │               │
│  │ ❌ 与前端不完全一致     │    │ ❌ 与前端不完全一致     │               │
│  └──────────────────────┘    └──────────────────────┘               │
└─────────────────────────────────────────────────────────────────────┘
```

### 0.0.1 规则挖掘 vs 评分卡配置一致性对比

| 对比项 | 规则挖掘 | 评分卡 |
|--------|---------|--------|
| **配置与前端一致性** | ✅ **高度一致** | ❌ **严重脱节** |
| **Tab ID 对应** | 8/8 完全对应 | 5/7 不对应 |
| **Tab 名称对应** | 100% 一致 | 部分名称不同 |
| **配置是否被使用** | ❌ **未被使用** | ❌ **未被使用** |

### 0.0.2 评分卡配置 vs 前端实际 Tab 对比

| 配置文件定义（7个Tab） | 前端实际实现（5个Tab） | 状态 |
|----------------------|----------------------|------|
| `charts` - 评估图表 | `charts` - 评估图表 | ✅ 一致 |
| `selection` - 特征筛选 | `selection` - 变量筛选 | ⚠️ 名称不同 |
| `scorecard` - 评分卡明细 | `scorecard` - 评分卡明细 | ✅ 一致 |
| `iv` - IV值排序 | ❌ **已合并到 selection** | ❌ 不存在 |
| `coefficients` - 模型系数 | ❌ **已合并到 statistics** | ❌ 不存在 |
| `statistics` - 统计检验 | `statistics` - 模型系数 | ⚠️ 名称不同 |
| `converter` - 评分转换 | ❌ **未实现** | ❌ 不存在 |
| ❌ 无 | `sample-data` - 样本与特征 | ✅ **前端新增** |

### 0.0.3 差异原因分析

1. **配置框架是"后设计"的**
   - 配置文件是后来为了统一管理而创建的
   - 创建时参考的是早期设计文档，而非实际前端代码
   - 前端代码在配置框架之前就已经存在并迭代多次

2. **前端独立演进**
   - 前端根据用户反馈和 UX 需求不断调整
   - 合并了 `iv` 到 `selection`（变量筛选包含IV排行）
   - 合并了 `coefficients` 到 `statistics`（模型系数包含系数表）
   - 新增了 `sample-data`（样本与特征概览）
   - 删除了 `converter`（评分转换作为独立工具）

3. **配置未被实际使用**
   - 配置文件主要用于 AI 分析 Prompt 构建和 Excel 导出
   - 前端 Tab 渲染完全是硬编码
   - 报告生成器也是完全硬编码

---

## 〇.一、评分卡任务报告现状对比分析

### 0.1 各格式报告章节结构对比

| 章节 | HTML报告 | Word报告 | Markdown报告 | Excel报告 | 配置定义 |
|------|---------|----------|--------------|-----------|----------|
| **执行摘要** | ✅ AI分析（0节） | ✅ AI分析（0节） | ✅ AI分析（1节） | ✅ AI分析 | ✅ summary |
| **模型评估** | ✅ 一、模型评估指标 | ✅ 一、模型评估指标 | ✅ 模型评估 | ✅ 一、模型评估 | ✅ eval |
| **特征筛选** | ✅ 二、筛选后特征列表 | ✅ 二、特征筛选 | ✅ 特征筛选 | ✅ 二、特征筛选 | ✅ woe |
| **评估图表** | ✅ 三、评估图表 | ✅ 图表嵌入 | ❌ 无 | ❌ 无 | - |
| **IV值排序** | ✅ 四、IV值排序 | ✅ 四、IV值排序 | ✅ 特征IV值排序 | ✅ 四、特征IV值 | - |
| **评分卡明细** | ✅ 五、评分卡明细 | ✅ 三、评分卡明细 | ✅ 评分卡明细 | ✅ 三、评分卡明细 | ✅ scorecard |
| **模型系数** | ✅ 六、模型系数 | ✅ 五、模型系数 | ✅ 模型系数 | ✅ 五、模型系数 | ✅ model |
| **特征选择详情** | ✅ 七、特征选择详情 | ✅ 逐步回归过程 | ❌ 无 | ❌ 无 | - |
| **统计检验** | ❌ 无 | ✅ 六、统计检验 | ✅ 模型统计检验 | ✅ 六、统计检验 | - |
| **阶段摘要** | ❌ 无 | ❌ 无 | ✅ 阶段执行详情 | ✅ 七、阶段执行摘要 | - |

### 0.2 发现的问题

#### ❌ 章节顺序不一致
- **HTML**：模型评估 → 筛选特征 → **图表** → IV → 评分卡 → 系数 → **选择详情**
- **Word**：模型评估 → 特征筛选 → **评分卡** → IV → 系数 → **统计检验**
- **Excel**：模型评估 → 特征筛选 → 评分卡 → IV → 系数 → 统计检验 → **阶段摘要**
- **Markdown**：模型评估 → 特征筛选 → 评分卡 → IV → 系数 → 统计检验 → **阶段详情**

#### ❌ 章节包含不一致
| 内容 | HTML | Word | MD | Excel |
|------|------|------|-----|-------|
| 评估图表 | ✅ | ✅ | ❌ | ❌ |
| 特征选择详情 | ✅ | ✅ | ❌ | ❌ |
| 统计检验 | ❌ | ✅ | ✅ | ✅ |
| 阶段摘要 | ❌ | ❌ | ✅ | ✅ |

#### ❌ 配置定义与实际实现不匹配
配置中定义的 `ReportSectionConfig` 章节：
```python
sections=[
    ReportSectionConfig(id="summary", title="执行摘要", ...),
    ReportSectionConfig(id="data", title="数据概况", ...),      # 实际报告无此章节
    ReportSectionConfig(id="woe", title="WOE分箱与特征筛选", ...),
    ReportSectionConfig(id="model", title="模型训练与系数", ...),
    ReportSectionConfig(id="eval", title="模型评估", ...),
    ReportSectionConfig(id="scorecard", title="评分卡与刻度", ...),
]
```
**但实际报告生成器完全没有使用这些配置！**

### 0.3 术语不一致问题

| 位置 | 术语 | 建议统一为 |
|------|------|-----------|
| Word 报告 971行 | "入模特征列表" | "筛选后特征列表" |
| HTML 报告 1670行 | "入模变量数" | ✅ 评分卡任务正确 |
| Markdown 报告 192行 | "入模特征" | ✅ 评分卡任务正确 |

**注**："入模特征/变量"在评分卡任务中是正确术语，问题主要在规则挖掘任务（已修复）。

### 0.4 与新方案的差异总结

| 维度 | 当前状态 | 新方案目标 |
|------|---------|-----------|
| **配置利用** | ❌ 配置已定义但未使用 | ✅ 报告生成器读取配置 |
| **章节一致性** | ❌ 各格式章节不同 | ✅ 统一由配置决定 |
| **可维护性** | ❌ 改动需改4处 | ✅ 改配置全生效 |
| **可扩展性** | ❌ 新格式需大量代码 | ✅ 新格式复用配置 |

---

## 一、背景与问题

### 1.1 当前状态

当前报告生成（HTML/Word/Markdown/Excel）与前端 Tab 页展示存在以下问题：

| 问题 | 描述 | 影响 |
|------|------|------|
| **版式硬编码** | HTML/Word 报告的章节结构、字段展示硬编码在各自的生成器中 | 维护成本高 |
| **配置未完全利用** | `TaskResultConfig` 配置框架已建立，但报告生成器未完全使用 | 配置形同虚设 |
| **前后端不一致** | 前端 Tab 页的精简方案（如"样本及特征"）与报告展示内容不同步 | 用户困惑 |
| **术语不统一** | 不同任务类型的术语混用（如规则挖掘中出现"入模特征"） | 已单独修复 |

### 1.2 现有配置框架

项目已建立 `TaskResultConfig` 配置框架（位于 `deepanalyze/core/task_manager/task_result_config.py`）：

```python
@dataclass
class TaskResultConfig:
    """任务结果配置 - 每个SOP任务类型一份"""
    task_type: str                       # "rule_mining" | "scorecard_dev"
    task_name: str                       # "规则挖掘" | "评分卡开发"
    tabs: List[TabConfig]                # Tab配置列表
    ai_analysis_config: AIAnalysisConfig # AI整体分析配置
    report_config: ReportConfig          # 报告生成配置
    excel_config: ExcelExportConfig      # Excel导出配置
```

**配置使用现状**：

| 组件 | 是否使用配置 | 说明 |
|------|-------------|------|
| `OverallAnalysisService` | ✅ 使用 | AI 整体分析 Prompt 构建 |
| `markdown_report.py` | ⚠️ 部分 | 支持 config 参数但未完全使用 |
| `excel_report.py` | ✅ 使用 | `stage_data_sheets` 配置 |
| `html_report.py` | ❌ 未使用 | 完全硬编码 |
| `word_report.py` | ❌ 未使用 | 完全硬编码 |
| 前端 Tab 页 | ❌ 未使用 | 前端独立维护 |

---

## 二、改进目标

### 2.1 核心目标

1. **配置驱动**：报告生成器从 `TaskResultConfig` 读取配置，动态决定展示内容
2. **单一数据源**：前端 Tab 页和报告生成共享配置，改一处全生效
3. **可扩展性**：新增任务类型只需定义配置，无需修改报告生成器代码

### 2.2 非目标

- 不追求前端 Tab 页与报告内容 100% 一致（两者展示目标不同）
- 不改变现有报告的整体结构（章节顺序等）

---

## 三、方案设计

### 3.1 配置模型增强

扩展 `TaskResultConfig` 以支持更细粒度的字段控制：

```python
@dataclass
class FieldDisplayConfig:
    """字段展示配置"""
    field_name: str                      # 字段名（results 字典中的 key）
    display_name: str                    # 显示名称
    include_in_tab: bool = True          # 是否在前端 Tab 页显示
    include_in_report: bool = True       # 是否在报告中显示
    format_type: str = "auto"            # 格式化类型: auto/number/percent/text
    priority: int = 0                    # 显示优先级（越小越靠前）


@dataclass
class SectionFieldConfig:
    """报告章节字段配置"""
    section_id: str                      # 章节 ID
    fields: List[FieldDisplayConfig]     # 字段列表
```

### 3.2 配置示例

```python
RULE_MINING_OVERVIEW_FIELDS = [
    FieldDisplayConfig("total_rows", "样本总量", include_in_tab=True, include_in_report=True),
    FieldDisplayConfig("bad_rate", "坏样本率", include_in_tab=True, include_in_report=True, format_type="percent"),
    FieldDisplayConfig("feature_count", "筛选后特征数", include_in_tab=True, include_in_report=True),
    FieldDisplayConfig("train_rows", "训练集样本", include_in_tab=True, include_in_report=False),  # 报告中精简
    FieldDisplayConfig("test_rows", "测试集样本", include_in_tab=True, include_in_report=False),
]
```

### 3.3 报告生成器改造

#### 3.3.1 抽象基类

```python
class ConfigDrivenReportGenerator:
    """配置驱动的报告生成器基类"""
    
    def __init__(self, config: TaskResultConfig):
        self.config = config
    
    def get_visible_fields(self, section_id: str, target: str = "report") -> List[FieldDisplayConfig]:
        """获取指定章节的可见字段
        
        Args:
            section_id: 章节 ID
            target: "report" 或 "tab"
        """
        section_config = self._get_section_config(section_id)
        if target == "report":
            return [f for f in section_config.fields if f.include_in_report]
        else:
            return [f for f in section_config.fields if f.include_in_tab]
    
    def render_section(self, section_id: str, data: dict) -> str:
        """渲染章节（子类实现）"""
        raise NotImplementedError
```

#### 3.3.2 HTML 报告改造示例

```python
# html_report.py
def _render_overview_section(results: dict, config: TaskResultConfig) -> str:
    """渲染概览章节 - 配置驱动"""
    
    # 从配置获取字段列表
    overview_fields = config.get_section_fields("overview", target="report")
    
    html_parts = ['<div class="overview-section">']
    
    for field in sorted(overview_fields, key=lambda x: x.priority):
        value = results.get(field.field_name)
        if value is not None:
            formatted_value = format_value(value, field.format_type)
            html_parts.append(f'<p><strong>{field.display_name}:</strong> {formatted_value}</p>')
    
    html_parts.append('</div>')
    return '\n'.join(html_parts)
```

### 3.4 前端配置同步

#### 3.4.0 ⚠️ 重要澄清：现有组件不会被废弃

**配置驱动 ≠ 废弃现有 JSX 组件**

前端改造采用**配置+组件映射**模式，而非完全动态渲染：

| 改造内容 | 说明 | 现有代码影响 |
|----------|------|-------------|
| **Tab列表** | 从配置读取，决定显示哪些Tab、顺序、名称 | 极小改动 |
| **Tab组件映射** | `tab_id` → 对应现有组件 | 无改动 |
| **组件内部实现** | `SampleDataPanel`、`ModelStatisticsPanel` 等 | **完全保留** |

**保留的现有组件**：
- `SampleDataPanel` / `SampleFeaturePanel` - 样本与特征
- `ModelStatisticsPanel` - 模型系数
- `ValidationReportPanel` - 质量验证
- `PSIReportPanel` - 稳定性分析
- `DecisionTreePanel` - 决策树可视化
- 所有图表渲染逻辑

#### 3.4.1 API 端点

新增配置获取 API：

```python
@router.get("/api/sop/config/{task_type}")
async def get_task_display_config(task_type: str):
    """获取任务展示配置"""
    config = get_task_result_config(task_type)
    if not config:
        raise HTTPException(404, f"Unknown task type: {task_type}")
    
    return {
        "task_type": config.task_type,
        "task_name": config.task_name,
        "tabs": [asdict(tab) for tab in config.tabs],
        "sections": [asdict(s) for s in config.report_config.sections],
    }
```

#### 3.4.2 前端改造示例（配置+组件映射）

```typescript
// 组件映射表 - 保留所有现有组件
const TAB_COMPONENTS: Record<string, React.ComponentType<any>> = {
  "sample-data": SampleDataPanel,
  "sample-feature": SampleFeaturePanel,
  "charts": ChartsPanel,
  "scorecard": ScorecardPanel,
  "selection": SelectionPanel,
  "statistics": ModelStatisticsPanel,
  "optimal": OptimalRulesPanel,
  "validation": ValidationReportPanel,
  "psi": PSIReportPanel,
  "tree": DecisionTreePanel,
};

// 改造后的 Tab 列表渲染
function TaskResultTabs({ taskType, data }) {
  const config = useTaskConfig(taskType);  // 从 API 获取配置
  
  return (
    <Tabs>
      {/* Tab 导航 - 从配置读取 */}
      <TabsList>
        {config?.tabs.map(tab => (
          <TabsTrigger key={tab.id} value={tab.id}>
            {tab.name}
          </TabsTrigger>
        ))}
      </TabsList>
      
      {/* Tab 内容 - 映射到现有组件 */}
      {config?.tabs.map(tab => {
        const Component = TAB_COMPONENTS[tab.id];
        return Component ? (
          <TabsContent key={tab.id} value={tab.id}>
            <Component data={data} />  {/* 现有组件完全保留 */}
          </TabsContent>
        ) : null;
      })}
    </Tabs>
  );
}
```

**配置驱动的价值**：
- 后端一处改配置 → 前端 Tab 显示/隐藏/重排自动生效
- 新增 Tab 只需：① 后端加配置 ② 前端加组件映射
- 所有精心设计的 UI 组件完整保留

---

## 四、实施计划

### 4.1 分阶段实施

| 阶段 | 内容 | 工作量 | 依赖 | 状态 |
|------|------|--------|------|------|
| **Phase 0** | Quick Win: 配置同步 | 0.5h | 无 | ✅ 完成 |
| **Phase 1** | 评分卡报告版式修改 | 1.5天 | 无 | ✅ 主要完成 |
| **Phase 2.1** | 配置模型增强 + 单元测试 | 0.5 天 | 无 | ⏳ 待开始 |
| **Phase 2.2** | HTML 报告改造 | 0.5 天 | Phase 2.1 | ⏳ 待开始 |
| **Phase 2.3** | Word/Markdown 报告改造 | 0.5 天 | Phase 2.1 | ⏳ 待开始 |
| **Phase 2.4** | 前端配置同步 API | 0.25 天 | Phase 2.1 | ⏳ 待开始 |
| **Phase 2.5** | 前端 Tab 列表改造（保留组件） | 0.5 天 | Phase 2.4 | ⏳ 待开始 |
| **Phase 2.6** | 集成测试 + 回归测试 | 0.25 天 | Phase 2.2-2.5 | ⏳ 待开始 |

**Phase 2 总计**：约 2.5 人天（比原估计 3-5 天更少，因为前端组件完全保留）

### 4.2 Phase 1：配置模型增强（立即可做）

```python
# 修改 task_result_config.py

@dataclass
class FieldDisplayConfig:
    field_name: str
    display_name: str
    include_in_tab: bool = True
    include_in_report: bool = True
    format_type: Literal["auto", "number", "percent", "text", "list"] = "auto"
    priority: int = 0


@dataclass  
class TabConfig:
    id: str
    name: str
    data_path: str
    include_in_report: bool = True
    include_in_ai_analysis: bool = True
    ai_analysis_metrics: List[str] = field(default_factory=list)
    # 新增：字段级配置
    field_configs: List[FieldDisplayConfig] = field(default_factory=list)
```

### 4.3 文件改动清单

| 文件 | 改动类型 | 说明 |
|------|---------|------|
| `task_result_config.py` | 修改 | 增强配置模型（可选） |
| `html_report.py` | 修改 | 读取配置动态渲染 |
| `word_report.py` | 修改 | 读取配置动态渲染 |
| `markdown_report.py` | 修改 | 完善配置使用 |
| `sop_api.py` | 修改 | 新增配置获取 API |
| `demo/chat/hooks/useTaskConfig.ts` | 新增 | 前端配置 hook |
| `demo/chat/components/sop/ScorecardResults.tsx` | **小改** | Tab 列表改为配置驱动（约 20 行） |
| `demo/chat/components/sop/RuleMiningResults.tsx` | **小改** | Tab 列表改为配置驱动（约 20 行） |
| `demo/chat/components/sop/*.tsx` | **保留** | 所有子组件完全保留不改动 |

---

## 五、风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 改动范围大，引入 bug | 高 | 分阶段实施，每阶段独立测试 |
| ~~前端改造工作量超预期~~ | ~~中~~ | ✅ 已明确：前端仅改 Tab 列表，组件完全保留 |
| 配置复杂度增加维护负担 | 低 | 提供默认配置，简化常见场景 |
| 性能影响（配置加载） | 低 | 配置缓存，启动时加载 |

---

## 六、验收标准

### 6.1 功能验收

- [ ] HTML 报告根据配置动态生成章节和字段
- [ ] Word 报告根据配置动态生成章节和字段
- [ ] Markdown 报告完全使用配置
- [ ] 前端 Tab 列表根据配置动态渲染（保留现有组件）
- [ ] 修改配置后，报告和 Tab 页同步变化
- [ ] 现有所有 UI 组件功能正常（SampleDataPanel、ModelStatisticsPanel 等）

### 6.2 回归测试

- [ ] 规则挖掘任务：完整流程 + 所有报告格式导出
- [ ] 评分卡开发任务：完整流程 + 所有报告格式导出
- [ ] AI 整体分析：Prompt 构建正确

---

## 附录A：多任务类型适用性说明

### A.1 方案通用性

本方案基于**统一的 `TaskResultConfig` 配置框架**设计，天然支持所有 SOP 类任务：

| 任务类型 | 配置 Key | 当前状态 | 方案适用性 |
|----------|---------|---------|-----------|
| 规则挖掘 | `rule_mining` | ✅ 配置已定义 | ✅ 完全适用 |
| 评分卡开发 | `scorecard_dev` | ✅ 配置已定义 | ✅ 完全适用 |
| 未来新任务 | `xxx_task` | 待定义 | ✅ 只需新增配置 |

### A.2 评分卡开发特有配置

评分卡开发任务已有完整配置（`SCORECARD_DEV_CONFIG`），包含：

**Tab 配置**（过时，需更新）：
- 评估图表、特征筛选、评分卡明细、IV值排序、模型系数、统计检验、评分转换

**报告章节配置**（过时，需更新）：
- 执行摘要、数据概况、WOE分箱与特征筛选、模型训练与系数、模型评估、评分卡与刻度

**特殊处理**：
- `converter`（评分转换）Tab 设置 `include_in_report=False`，因为是交互式工具

### A.3 新增任务类型的步骤

实施本方案后，新增任务类型只需：

1. 在 `task_result_config.py` 中定义新的 `TaskResultConfig`
2. 注册到 `TASK_RESULT_CONFIGS` 字典
3. 无需修改任何报告生成器代码

```python
# 示例：新增"模型监控"任务
MODEL_MONITORING_CONFIG = TaskResultConfig(
    task_type="model_monitoring",
    task_name="模型监控",
    tabs=[...],
    ai_analysis_config=AIAnalysisConfig(...),
    report_config=ReportConfig(...),
    excel_config=ExcelExportConfig(...)
)

# 注册
TASK_RESULT_CONFIGS["model_monitoring"] = MODEL_MONITORING_CONFIG
```

---

## 附录B：评分卡报告版式修改实施计划（短期方案）

> **状态**: 📋 待实施  
> **优先级**: P1（短期）  
> **预估工作量**: 约 1.5 人天

### B.1 设计原则

**核心原则**：报告内容与前端 Tab 页保持一致性

| 原则 | 说明 |
|------|------|
| **概览部分统一** | 第一章节为"概览"（汇总指标 + AI分析），与规则挖掘保持一致 |
| **后续章节对应 Tab** | 报告的 2~N 章节与前端 Tab 页一一对应 |
| **以前端为准** | 报告版式修改以实际前端 Tab 为准，同时更新配置文件 |

### B.2 当前前端实际 Tab 结构

| 序号 | Tab ID | Tab 名称 | 内容说明 |
|------|--------|---------|---------|
| 1 | `sample-data` | 样本与特征 | 漏斗概览 + 变量IV排行 |
| 2 | `charts` | 评估图表 | KS/ROC/评分分布图表 |
| 3 | `scorecard` | 评分卡明细 | 评分卡变量分箱明细 |
| 4 | `selection` | 变量筛选 | IV值、相关性、VIF、逐步回归、系数验证 |
| 5 | `statistics` | 模型系数 | 逻辑回归系数 + 统计检验 |

**另外**：
- 顶部有**汇总指标卡**（KS、AUC、Gini、PSI）
- 有**数据集指标对比**表格（训练集/测试集/OOT）

### B.3 目标报告结构（与 Tab 对齐）

```
一、概览                     ← 新增（与规则挖掘一致）
   - 汇总指标卡（KS、AUC、Gini、PSI）
   - 数据集指标对比（训练集/测试集/OOT）
   - AI 整体分析

二、样本与特征               ← 对应 Tab 1
   - 漏斗概览（原始特征 → 质量筛选 → WOE分箱 → IV/相关/VIF → 最终入模）
   - 变量IV排行

三、评估图表                 ← 对应 Tab 2
   - KS曲线
   - ROC曲线
   - 评分分布

四、评分卡明细               ← 对应 Tab 3 `scorecard`
   - 指标卡（3个）：入模变量数、理论评分区间、基准配置(基准分/Odds/PDO)
   - 完整评分卡表格（12列）：变量、IV、系数、序号、分箱、样本数、占比、好样本、坏样本、坏率、WOE、评分

五、变量筛选                 ← 对应 Tab 4
   - IV值
   - 相关性分析
   - VIF检验
   - 逐步回归
   - 系数验证

六、模型系数                 ← 对应 Tab 5 `statistics`
   - 指标卡（4个）：入模变量、显著变量、系数方向验证、截距项
   - 逻辑回归系数表
   - 统计检验结果（模型拟合度等）
```

### B.4 当前报告 vs 目标对比

| 当前 HTML 章节 | 目标章节 | 变化 |
|---------------|---------|------|
| ❌ 无 | 一、概览 | **新增** ✅ 已完成 |
| ❌ 无 | 二、样本与特征 | **新增** ✅ 已完成 |
| 一、模型评估指标 | 三、评估图表（合并指标） | 重排+改名 ✅ 已完成 |
| 二、筛选后特征列表 | 五、变量筛选（扩展内容） | 重排+扩展 ✅ 已完成 |
| 三、评估图表 | （合并到三） | 合并 ✅ 已完成 |
| 四、IV值排序 | （合并到二、五） | 拆分合并 ✅ 已完成 |
| 五、评分卡明细 | 四、评分卡明细 | 重排+增强 ✅ 已完成 |
| 六、模型系数 | 六、模型系数 | 保持+增强 ✅ 已完成 |
| 七、特征选择详情 | （合并到五） | 合并 ✅ 已完成 |
| ❌ 无（Word有） | 统计检验（合并到六） | HTML新增 ✅ 已完成 |

**2026-02-09 新增功能**：
1. 第六章"模型系数"增加了"系数方向验证"指标卡，与前端 Tab 保持一致。
2. 第四章"评分卡明细"改用 `full_scorecard_csv` 数据源，展示完整12列信息（变量、IV、系数、序号、分箱、样本数、占比、好样本、坏样本、坏率、WOE、评分），与前端 Tab 完全一致。

### B.5 配置更新方案

```python
# task_result_config.py - 更新 SCORECARD_DEV_CONFIG.tabs
tabs=[
    TabConfig(
        id="sample-data",
        name="样本与特征",
        data_path="stages.preprocessing,stages.woe_binning",
        include_in_report=True,
    ),
    TabConfig(
        id="charts",
        name="评估图表",
        data_path="evaluation,chart_data",
        include_in_report=True,
    ),
    TabConfig(
        id="scorecard",
        name="评分卡明细",
        data_path="scorecard",
        include_in_report=True,
    ),
    TabConfig(
        id="selection",
        name="变量筛选",
        data_path="feature_selection,iv_table,correlation,vif,stepwise",
        include_in_report=True,
    ),
    TabConfig(
        id="statistics",
        name="模型系数",
        data_path="coefficients,model_statistics",
        include_in_report=True,
    ),
]
```

### B.6 实施任务清单

| 阶段 | 任务 | 工作量 | 优先级 | 状态 |
|------|------|--------|--------|------|
| **Phase 0** | 更新 `SCORECARD_DEV_CONFIG` 配置与前端实际 Tab 对齐 | 0.5h | P0 | ✅ 完成 (2026-02-09) |
| **Phase 1** | HTML 报告：新增概览 + 样本与特征，调整章节顺序 | 2h | P0 | ✅ 完成 (2026-02-09) |
| **Phase 1.1** | HTML 报告：第六章"模型系数"增加系数方向验证指标卡 | 0.5h | P0 | ✅ 完成 (2026-02-09) |
| **Phase 1.2** | 前端 ModelStatisticsPanel：同步系数方向验证指标卡 | 0.5h | P0 | ✅ 完成 (2026-02-09) |
| **Phase 1.3** | HTML/Markdown 报告：第四章"评分卡明细"改用 full_scorecard_csv，与前端一致 | 0.5h | P0 | ✅ 完成 (2026-02-09) |
| **Phase 2** | Markdown 报告：同上 | 1h | P0 | ✅ 完成 (2026-02-09) |
| **Phase 3** | Word 报告：重构为6章节结构，与 HTML 保持一致 | 2h | **P0** | ✅ **已完成** (2026-02-12) |
| **Phase 4** | Excel 报告"任务报告"Sheet：重构为5章节结构 | 1.5h | **P0** | ✅ **已完成** (2026-02-12) |
| **Phase 5** | 验证测试 | 0.5h | P0 | ⏳ 待进行 |

**预估总工作量**：约 2 人天
**实际完成**：HTML/Markdown/Word/Excel 报告均已重构完成
- HTML/Markdown/Word：6章节结构（含"评估图表"）
- Excel：5章节结构（不含"评估图表"，以图表数据表格形式存在于独立Sheet）

**当前状态**：Phase 0-4 全部完成，可启动 Phase 2 配置驱动方案

#### B.6.1 Phase 4 详细任务：Excel 报告"任务报告"Sheet 重构

**当前问题**（2026-02-10 发现）：

| 问题 | 当前状态 | 目标状态 |
|------|---------|---------|
| 缺少"样本与特征"章节 | ❌ 无此章节 | ✅ 二、样本与特征 |
| 章节顺序不一致 | 模型评估→特征筛选→评分卡→IV→系数→统计 | 概览→样本与特征→评估图表→评分卡→变量筛选→模型系数 |
| 章节名称不统一 | "一、模型评估" | "一、概览" |

**当前 Excel `_add_scorecard_task_report_sheet` 章节结构**：
```
一、模型评估      ← 应改为"一、概览"
二、特征筛选      ← 应改为"五、变量筛选"
三、评分卡明细    ← 应改为"四、评分卡明细"
四、特征IV值排序  ← 应合并到"二、样本与特征"或"五、变量筛选"
五、模型系数      ← 应改为"六、模型系数"
六、模型统计检验  ← 应合并到"六、模型系数"
七、阶段执行摘要  ← 可保留或移除
```

**目标章节结构**（与 HTML 报告对齐）：
```
一、概览
   - 汇总指标卡（KS、AUC、Gini、PSI）
   - 数据集指标对比表
   - AI 整体分析

二、样本与特征           ← 新增
   - 样本概览（总样本数、坏账率、入模变量数）
   - 数据集划分（训练集/测试集/OOT）
   - 特征变化流程（可选）

三、评估图表             ← Excel 特殊处理：仅显示"请参见独立 Sheet"说明
   - （图表数据在独立 Sheet 中）

四、评分卡明细
   - 完整评分卡表格（使用 full_scorecard_csv）

五、变量筛选
   - IV值排序表
   - 入模特征列表

六、模型系数
   - 逻辑回归系数表
   - 统计检验结果
```

**修改文件**：`deepanalyze/analysis/excel_report.py` 的 `_add_scorecard_task_report_sheet` 函数

### B.7 验收标准（2026-02-12 全部完成 ✅）

- [x] 报告章节与前端 Tab 一一对应（除概览外）- HTML/Markdown/Word/Excel 已完成
- [x] 概览章节包含：汇总指标卡 + 数据集对比 + AI分析 - 所有格式已完成
- [x] Word 报告章节结构与 HTML 对齐 - ✅ 已完成
- [x] Excel 报告"任务报告"Sheet 章节结构与 HTML 对齐 - ✅ 已完成
- [x] 各格式报告章节顺序一致 - 所有格式已对齐
- [x] 配置文件 `SCORECARD_DEV_CONFIG.tabs` 与实际前端 Tab 一致 - Phase 0 已完成

### B.8 各格式报告章节映射（当前状态）

#### 评分卡开发任务（2026-02-12 重构完成 ✅）

| 报告章节 | Tab 对应 | HTML | Word | MD | Excel |
|----------|---------|------|------|-----|-------|
| **一、概览** | - | ✅ | ✅ | ✅ | ✅ |
| **二、样本与特征** | `sample-data` | ✅ | ✅ | ✅ | ✅ |
| **三、评估图表** | `charts` | ✅ | ✅ | ⚠️ 数据表格 | ⚠️ 独立Sheet |
| **四、评分卡明细** | `scorecard` | ✅ | ✅ | ✅ | ✅ |
| **五、变量筛选** | `selection` | ✅ | ✅ | ✅ | ✅ |
| **六、模型系数** | `statistics` | ✅ | ✅ | ✅ | ✅ |

#### 规则挖掘任务

| 报告章节 | Tab 对应 | 内容说明 | HTML | Word | MD | Excel |
|----------|---------|---------|------|------|-----|-------|
| **一、概览** | - | 汇总指标卡 + AI分析 | ✅ | ✅ | ✅ | ✅ |
| **二、样本及特征** | `sample-feature` | 样本概览 + 特征概览 | ✅ | ✅ | ✅ | ✅ |
| **三、最优规则** | `optimal` | 最优规则列表 | ✅ | ✅ | ✅ | ✅ |
| **四、过滤后规则** | `filtered` | 筛选过程 + 过滤后规则 | ✅ | ✅ | ✅ | ✅ |
| **五、全部规则** | `all` | 完整规则列表 | ✅ | ✅ | ✅ | ✅ |
| **六、质量验证** | `validation` | 质量验证报告 | ✅ | ✅ | ✅ | ✅ |
| **七、稳定性** | `psi` | PSI分析 | ✅ | ✅ | ✅ | ✅ |
| **八、附加分析** | `amount` | 金额维度分析 + 先验规则分析 | ✅ | ✅ | ✅ | ✅ |
| ~~九、规则来源~~ | ~~`tree`~~ | ~~决策树可视化~~ | ~~❌~~ | ~~❌~~ | ~~❌~~ | ~~❌~~ |

**说明**：
- ✅ 已完成对齐
- ⏳ 待重构
- ❌ 缺失（需新增）
- ⚠️ 特殊处理（Markdown 用数据表格，Excel 图表在独立 Sheet）
- **规则挖掘任务**：所有格式报告已完全对齐（8个章节），决策树Tab仅前端展示不进入报告

**Excel 当前章节结构 vs 目标对比**：
| 当前 Excel 章节 | → | 目标章节 |
|----------------|---|---------|
| 一、模型评估 | → | 一、概览 |
| ❌ 无 | → | **二、样本与特征（新增）** |
| ❌ 无 | → | 三、评估图表（引用独立Sheet） |
| 三、评分卡明细 | → | 四、评分卡明细 |
| 二、特征筛选 + 四、特征IV值排序 | → | 五、变量筛选（合并） |
| 五、模型系数 + 六、模型统计检验 | → | 六、模型系数（合并） |
| 七、阶段执行摘要 | → | 可选保留 |

---

## 七、决策记录

| 日期 | 决策 | 原因 |
|------|------|------|
| 2026-02-09 | 配置驱动完整方案暂缓实施，作为中长期优化 | 当前无强用户需求，ROI 偏低 |
| 2026-02-09 | 评分卡报告版式修改作为短期任务实施 | 报告内容与前端 Tab 需要对齐 |
| 2026-02-09 | 发现配置文件与前端脱节问题 | 配置存在但未被使用，前端全部硬编码 |
| 2026-02-09 | ✅ 完成 Phase 0: 同步配置文件 | `SCORECARD_DEV_CONFIG` 从 7 tabs 更新为 5 tabs |
| 2026-02-09 | ✅ 完成 Phase 1 主要工作: HTML/Markdown 报告重构 | 6章节结构与前端 Tab 对齐 |
| 2026-02-09 | ✅ 新增"系数方向验证"指标卡 | HTML报告第六章 + 前端 ModelStatisticsPanel 同步实现 |
| 2026-02-09 | ✅ 修复 HTML 报告 coefficient_validation 数据获取 | 添加从 selection_detail 的回退逻辑，确保与前端数据源一致 |
| 2026-02-09 | ✅ 修复第四章"评分卡明细"数据不一致问题 | 改用 `full_scorecard_csv` 数据源，展示完整12列信息，与前端 Tab 完全一致 |
| 2026-02-10 | ✅ 修复概览指标标签硬编码问题 | HTML/Markdown 报告指标标签从硬编码"测试集"改为动态显示（根据 `metrics.source` 判断 OOT/测试集） |
| 2026-02-10 | ✅ 修复评分卡报告 AI 分析来源不一致问题 | 评分卡报告导出改为优先从持久化存储获取 AI 分析（与规则挖掘、前端展示一致），回退到 outputs |
| 2026-02-10 | ✅ 修复规则挖掘 Excel 报告缺少配置问题 | 添加 `stage_configs` 和 `all_rules_with_status` 到 excel_results，确保阶段 Sheet 正确命名 |
| 2026-02-10 | ✅ 修复 Excel 报告 `all_rules_with_status` 数据不完整 | 用最新的 `results['all_rules_with_status']`（含 `is_optimal`、`rejection_reason`）更新 `rule_filtering` 阶段数据 |
| 2026-02-10 | ✅ 修复评分卡 Excel 报告缺少 `stage_configs` | 添加配置传递，确保阶段 Sheet 使用配置名称（如 `1_数据加载`） |
| 2026-02-10 | ✅ 评分卡配置添加 `download_field` | `feature_selection` 阶段配置 `all_features_detail` 字段，用于 Excel 报告展示特征筛选明细 |
| 2026-02-10 | ✅ 评分卡模型评估阶段6种CSV数据支持 | 添加 `_write_model_evaluation_score_distributions` 方法，展示3数据集×2分析视图的完整评分分布数据 |
| 2026-02-10 | ✅ 评分卡特征筛选阶段2种CSV数据支持 | 添加 `_write_feature_binning_detail_table` 方法，同时展示特征筛选明细和分箱明细两个表格 |
| 2026-02-10 | ✅ 补全评分卡阶段配置 | 添加 `score_scaling`（含 `full_scorecard_csv`），共6个阶段完整覆盖；`report_generation` 不单独生成 Sheet（仅含状态信息无表格数据） |
| 2026-02-10 | ✅ 澄清前端改造范围 | 前端仅改 Tab 导航渲染（约 40 行），所有子组件（SampleDataPanel、ModelStatisticsPanel 等）完全保留 |
| 2026-02-10 | ✅ 下调 Phase 2 工作量预估 | 从 3-5 人天调整为 2-2.5 人天，因为前端组件完全保留 |
| 2026-02-10 | 📋 明确实施顺序：先完成 Word 报告重构，再实施配置驱动方案 | **避免重复劳动**：若先配置驱动，Word 旧结构会被固化到配置中；**明确统一目标**：所有格式先手动对齐到6章节结构，再抽取为配置；**一致性原则**：Word 应与 HTML 高度一致（除图片形式） |
| 2026-02-10 | 📋 发现评分卡 Excel 报告"任务报告"Sheet 章节结构与 HTML 严重不对齐 | **缺少"二、样本与特征"章节**；章节顺序与 HTML 不一致；章节名称不统一（"模型评估" vs "概览"） |
| 2026-02-10 | 📋 将 Excel 报告重构优先级从 P1 提升到 P0 | 与 Word 报告同理：必须在配置驱动方案前完成，避免旧结构被固化到配置中 |
| 2026-02-10 | ✅ 规则挖掘 Excel 报告"任务报告"Sheet 已与 HTML 对齐 | 早前已完成规则挖掘任务的 Excel 报告重构（`_write_sample_features_section` 等） |
| 2026-02-12 | ✅ 修正规则挖掘任务章节对齐状态 | 确认规则挖掘所有格式报告已对齐（8章节），决策树Tab仅前端展示 |
| 2026-02-12 | ✅ 更新报告版式规划文档 | 分开展示评分卡和规则挖掘任务的章节对齐状态 |
| 2026-02-12 | ✅ 完成 P1 任务 | 概览指标卡版式优化 + AI分析Prompt似然比检验数据源对齐 |
| 2026-02-12 | ✅ 完成 Phase 1.5 | Word 报告重构为6章节结构（~2h） |
| 2026-02-12 | ✅ 完成 Phase 1.6 | Excel 报告重构为6章节结构（~1.5h） |
| 2026-02-12 | ✅ P0 任务全部完成 | Word + Excel 报告重构完成，Phase 2 配置驱动方案障碍已清除 |
| 2026-04-15 | 📋 发现导出报告缺少新增指标数据 | P0-3（CSI）和 P1-5（OOT 稳定性）新增的指标仅在前端和 AI prompt 中展示，四种格式导出报告均未包含。详见下方 Phase 1.7 |

### Phase 1.7：导出报告新增指标同步（持续更新）

> **优先级**: P3 | **预计工作量**: 按批次评估 | **创建日期**: 2026-04-15
> **前置条件**: 无（可独立实施，不依赖 Phase 2 配置驱动）
> **定位**: 随着 Pipeline 阶段新增指标/数据，导出报告需要同步补充对应内容。
> 此 Phase 作为**统一登记处**，记录所有"前端/AI Prompt 已有但导出报告缺失"的指标，按批次实施。

#### 通用根因

`sop_api.py` 的 `/report/export` 端点在组装各格式报告的 results dict 时，**未传递新增字段**到报告生成器。报告生成器（html/word/excel/markdown_report.py）也未编写对应的渲染逻辑。

#### 通用修复模式

每个新增指标需要两步：
1. **`sop_api.py`**：在对应任务的报告导出 results dict 中传递新字段
2. **报告生成器**：在对应章节中新增渲染逻辑（四种格式各一处）

---

#### 批次 1（2026-04-15 登记）

**来源**: P0-3（CSI 特征稳定性）、P1-5（OOT 命中率稳定性）

| # | 缺失指标 | 来源任务 | 数据 key | 所属 Pipeline 阶段 | 前端 | AI Prompt | HTML | Word | Excel | MD |
|---|----------|---------|----------|-------------------|:---:|:---------:|:---:|:---:|:---:|:---:|
| 1 | **CSI 特征稳定性** | P0-3（评分卡） | `csi_train_vs_test` / `csi_train_vs_oot` | model_evaluation | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| 2 | **OOT 命中率稳定性** | P1-5（规则挖掘） | `oot_stability_report` | selecting_rules | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| 3 | **评分卡 HTML 双 PSI** | 早期遗漏 | `psi_train_vs_test` / `psi_train_vs_oot` | model_evaluation | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ |

**Step 1**: `sop_api.py` — 传递新增字段

```python
# 评分卡 HTML 导出（~2295行）补充：
'psi_train_vs_test': outputs.get("psi_train_vs_test", {}).get("data"),
'psi_train_vs_oot': outputs.get("psi_train_vs_oot", {}).get("data"),
'csi_train_vs_test': outputs.get("csi_train_vs_test", {}).get("data"),
'csi_train_vs_oot': outputs.get("csi_train_vs_oot", {}).get("data"),

# 评分卡 Excel/Word/MD 导出补充（已有 psi_train_vs_*）：
'csi_train_vs_test': outputs.get("csi_train_vs_test", {}).get("data"),
'csi_train_vs_oot': outputs.get("csi_train_vs_oot", {}).get("data"),

# 规则挖掘 HTML/Word/Excel/MD 导出补充：
'oot_stability_report': outputs.get("oot_stability_report", {}).get("data"),
```

**Step 2**: 四个报告生成器 — 新增渲染

| 生成器 | 评分卡 CSI | 规则挖掘 OOT 稳定性 | 预估 |
|--------|:---------:|:------------------:|------|
| `html_report.py` | PSI 后加 CSI 表格 | 稳定性章节加 OOT CV 表格 | ~50-80 行 |
| `word_report.py` | 同上 | 同上 | ~40-60 行 |
| `excel_report.py` | 同上 | 同上 | ~40-60 行 |
| `markdown_report.py` | 同上 | 同上 | ~30-40 行 |

**预计工作量**: ~0.5-1天

---

#### 批次 2（2026-04-16 登记）

**来源**: 策略诊断方案评估中发现的空白项

| # | 缺失项 | 来源 | 数据 key | 所属阶段 | 前端 | AI Prompt | 导出报告 |
|---|--------|------|----------|---------|:---:|:---------:|:-------:|
| 4 | **金额维度分析 AI 引导** | 现有 AmountAnalyzer（规则挖掘） | `amount_analysis` | amount_analysis | ✅ | ❌ | ✅ |

**说明**：`AmountAnalyzer` 已全栈实现（后端 + 前端 + 四格式报告），但 `AI_analysis_prompts.py` 中完全未引导 AI 分析金额维度指标（命中金额、金额Lift、金额召回率等）。需在 `amount_analysis` 阶段的 AI prompt 中加入金额指标解读引导。

**预计工作量**: ~0.5天（仅 Prompt 文本更新）

---

#### 批次 3（2026-04-16 登记 — P2-10 金额维度分析测试发现）— ✅ 已修复

**来源**: `amount_analysis_test_plan.md` §7.3 测试发现的报告 Bug
**修复日期**: 2026-04-16 | **修复方案**: FIX-1~FIX-6（详见 `amount_analysis_test_plan.md` §7.5）

| # | 缺陷 | 位置 | 严重性 | 修复 |
|---|------|------|:------:|------|
| 5 | **`if optimal_rules` DataFrame truthiness Bug** | `markdown_report.py` `word_report.py` `html_report.py`（6 处） | 🔴 | ✅ FIX-3：统一改为 `rules is None or (isinstance(rules, list) and len(rules) == 0)` + DataFrame 自动 `to_dict` |
| 6 | **Excel 金额章节生成失败** | `excel_report.py` `_write_advanced_analysis_section` | 🟡 | ✅ FIX-4：重写为结构化字段读取（汇总指标 + 规则金额明细表格） |
| 7 | **Markdown 报告不输出金额分析章节** | `markdown_report.py` `_format_amount_analysis` | 🟡 | ✅ FIX-5：重写为匹配扁平化结构（HTML/Word 代码已正确，无需改） |
| 8 | **全栈数据流断裂（B4 关键 Bug）** | Pipeline → `safe_serialize` → 前端 | 🔴 | ✅ FIX-1：Pipeline 输出时扁平化（summary 提升+DF 转 list）；FIX-2：prop 名 `amountAnalysis` → `analysis`；FIX-6：`AmountAnalyzer.fit()` 添加 `pd.to_numeric` 类型校验 |

**预计工作量**: ~2天（✅ 实际 ~0.5天完成）

---

#### 批次 4（2026-04-16 登记 — P2-6 类别不平衡处理）

**来源**: P2-6 类别不平衡处理 MVP（`class_imbalance_handling_plan.md`）

| # | 缺失项 | 来源 | 数据 key | 所属阶段 | 前端 | AI Prompt | 导出报告 |
|---|--------|------|----------|---------|:---:|:---------:|:-------:|
| 9 | **不平衡处理策略信息** | P2-6 imbalance_strategy | `output_preview.imbalance_analysis` | preprocessing / data_loading | ✅ 卡片展示 | ✅ focusPoints + 数据描述 | ❌ 未包含 |

**说明**：`imbalance_analysis` 包含 severity（程度）、applied_strategy（实际策略）、imbalance_ratio（比例）等信息。前端和 AI Prompt 已展示，但四格式导出报告的"概览"章节未包含不平衡处理策略说明。建议在报告"概览"或"附加分析"章节中添加一行"不平衡处理策略: xxx"。

**优先级**: 低（非必要指标，仅增强报告完整性）  
**预计工作量**: ~0.5天

---

#### 批次 5（2026-04-17 登记 — P2-7 先验规则测试发现）— ✅ 已修复

**来源**: P2-7 先验规则输入增强测试（`tests/test_prior_rules.py` 测试 #6, #7）  
**状态**: ✅ 全部修复（2026-04-17），测试 12/12 通过

| # | 缺陷 | 来源 | 严重性 | 修复 |
|---|------|------|:------:|------|
| 10 | **先验规则分析 全栈数据流断裂** | P2-7 测试 #6 | 🔴 | ✅ FIX-A: Pipeline 输出扁平化（DataFrame→list[dict]）+ summary 补充 matched_count/avg_recall/avg_lift + rules 补充 recall/hit_rate/matched 别名 |
| 11 | **Excel 报告 prior_analysis 处理粗糙** | P2-7 测试 #6 | 🟡 | ✅ FIX-B: Excel 报告结构化输出（汇总指标表+规则详情表替代 dict items 遍历） |
| 12 | **前端 PriorAnalysisPanel summary 卡片字段不匹配** | P2-7 测试 #7 | 🟡 | ✅ FIX-A 自动修复（summary 补充 new_rules_count/incremental_recall/avg_overlap_rate） |

**修复方案**: P2-10 FIX-1 同款（Pipeline 输出扁平化），修改 2 个文件：
1. `rule_mining.py` L7938: DataFrame→list[dict] + summary 字段补齐
2. `excel_report.py` L2642: 结构化输出替代粗糙遍历

---

#### 批次 6（2026-04-21 登记 — P1-5 Phase 4 OOT 稳定性前端实现）

**来源**: P1-5 OOT 稳定性验证（`rule_mining_oot_validation_design.md`）Phase 4 前端实现时发现

| # | 缺失项 | 来源 | 数据 key | 所属阶段 | 前端 | AI Prompt | 导出报告 |
|---|--------|------|----------|---------|:---:|:---------:|:-------:|
| 13 | **OOT 时间稳定性验证报告** | P1-5 oot_stability_report | `results.oot_stability_report` | selecting_rules | ✅ 稳定性 Tab 融合展示（Phase 4 已实现） | ❌ 未包含 | ❌ 4格式报告均未包含 |
| 14 | **规则级 OOT 命中率对比（train/test/oot）** | P1-5 rule_stability | `oot_stability_report.rule_stability[]` | selecting_rules | ✅ 稳定性 Tab 详情表 + 规则表格 Badge | ❌ 未包含 | ❌ 4格式报告均未包含 |

**说明**：`oot_stability_report` 包含 `overall_hit_rate.cv`（整体变异系数）、`stability_counts`（分级计数）、`rule_stability`（每条规则的 train/test/oot 命中率 + CV + 等级）、`stability_score_bonus`（质量评分附加分）。前端已在"稳定性" Tab 中融合展示，但四格式导出报告和 AI Prompt 均未包含 OOT 相关内容。

**建议**：
1. 报告"稳定性分析"章节新增"OOT 时间稳定性"子节，展示整体 CV + 规则级命中率对比表
2. AI Prompt 的 `focusPoints` 中增加 OOT 稳定性评估要点

**优先级**: 中（OOT 是风控建模核心评估维度，但仅在配置了 OOT 验证时才有数据）  
**预计工作量**: ~1天（4格式报告 + AI Prompt）

---

#### 批次 7（2026-04-27 — 金额维度汇总卡片优化）— ✅ 已完成

**来源**: AT-01 测试反馈，前端+报告金额汇总指标扩充  
**完成日期**: 2026-04-27

| # | 改动项 | 涉及文件 | 类型 |
|---|--------|---------|------|
| 15 | 后端新增 `cum_amount_bad_rate` + `cum_amount_lift` 字段 | `rule_mining.py` `analyze_with_cumulative()` | 数据新增 |
| 16 | 前端 4 卡片 → 6 卡片（3×2 布局），新增「样本金额坏账率」「金额累计提升度」 | `AmountAnalysisPanel.tsx` | UI 优化 |
| 17 | 「金额召回率」改名为「金额累计召回率」 | 前端 + 4 个报告生成器 | 标签修正 |
| 18 | 四格式报告同步新增 2 个汇总指标 | `word_report.py` `markdown_report.py` `excel_report.py` `html_report.py` | 报告同步 |

**说明**：`overall_amount_bad_rate` 后端已有（summary 中返回），但 Word/HTML 报告和前端卡片此前未展示。`cum_amount_lift` 为新增计算字段（= cum_amount_bad_rate / overall_amount_bad_rate）。JSON 导出不受影响（直接序列化原始数据）。

- [任务结果配置框架](../../deepanalyze/core/task_manager/task_result_config.py)
- [评分卡结果调整方案](./scorecard_result_adjustment_design.md)
- [AI分析Prompt重构方案](./analysis_prompt_refactor_plan.md)

---

## 九、Quick Win（可立即执行的小改进）

在大规模重构之前，以下小改进可以先行实施：

### 9.1 P0：同步配置文件与前端实现

**目的**：确保配置文件定义与实际前端 Tab 一致，为未来配置驱动做准备

```python
# task_result_config.py - 更新 SCORECARD_DEV_CONFIG.tabs
# 从当前的 7 tabs 更新为与前端一致的 5 tabs
tabs=[
    TabConfig(id="sample-data", name="样本与特征", ...),  # 前端新增
    TabConfig(id="charts", name="评估图表", ...),
    TabConfig(id="scorecard", name="评分卡明细", ...),
    TabConfig(id="selection", name="变量筛选", ...),     # 合并了 iv
    TabConfig(id="statistics", name="模型系数", ...),    # 合并了 coefficients
]
```

### 9.2 P0：报告标题从配置读取

```python
# html_report.py 修改
def generate_rule_mining_report_html(results: dict, ai_analysis: str = None) -> str:
    from deepanalyze.core.task_manager.task_result_config import get_task_result_config
    
    config = get_task_result_config("rule_mining")
    title = config.report_config.title if config else "规则挖掘分析报告"
    
    # 使用 title 变量替代硬编码
    ...
```

### 9.3 P1：术语统一检查脚本

```python
# scripts/check_terminology.py
"""检查报告生成器中的术语一致性"""

RULE_MINING_FORBIDDEN_TERMS = ["入模", "入模特征", "入模变量"]
SCORECARD_FORBIDDEN_TERMS = ["候选规则", "最优规则"]

def check_file(filepath: str, forbidden_terms: list) -> list:
    """检查文件中是否包含禁用术语"""
    issues = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            for term in forbidden_terms:
                if term in line:
                    issues.append(f"{filepath}:{line_num}: Found '{term}'")
    return issues
```

---

## 十、实施路线图总览

```
┌─────────────────────────────────────────────────────────────────────┐
│                        实施路线图                                     │
└─────────────────────────────────────────────────────────────────────┘

Phase 0（立即）: Quick Win ✅ 已完成 (2026-02-09)
├── ✅ 同步 SCORECARD_DEV_CONFIG.tabs 与前端实际 Tab（7→5）
├── ✅ 更新 report_config.sections 与 Tab 对齐
├── ✅ 更新 excel_config.tab_sheets 与 Tab 对齐
└── 实际耗时：~15min

Phase 1（短期 P1）: 评分卡 HTML/Markdown 报告版式修改 ✅ 已完成 (2026-02-09~10)
├── ✅ HTML 报告：新增概览 + 样本与特征，调整章节顺序（6章节对应5个Tab）
├── ✅ HTML 报告：第六章"模型系数"增加系数方向验证指标卡
├── ✅ 前端 ModelStatisticsPanel：同步系数方向验证指标卡（入模变量→显著变量→系数方向→截距项）
├── ✅ Markdown 报告：同上（6章节对应5个Tab）
├── ✅ 修复 coefficient_validation 数据获取：添加 selection_detail 回退逻辑
├── ✅ 修复第四章"评分卡明细"：改用 full_scorecard_csv 数据源，展示完整12列信息
├── ✅ Excel 报告：阶段 Sheet 配置完整（含 download_field）
├── ✅ Excel 报告：多 CSV 场景专门处理（特征筛选2种、模型评估6种）
└── 实际耗时：~3h

Phase 1.5（短期 P0）: 评分卡 Word 报告重构 ✅ 已完成 (2026-02-12)
├── ✅ 重构章节结构：与 HTML 保持一致的6章节
│       ├── 一、概览（汇总指标 + 数据集对比 + AI分析）
│       ├── 二、样本与特征（漏斗概览 + 变量IV排行）
│       ├── 三、评估图表（KS/ROC/评分分布图）
│       ├── 四、评分卡明细（full_scorecard_csv 完整表格）
│       ├── 五、变量筛选（IV/相关性/VIF/逐步回归/系数验证）
│       └── 六、模型系数（系数表 + 统计检验）
├── ✅ 数据源对齐：使用与 HTML 相同的数据源（如 full_scorecard_csv）
└── 实际完成：Word报告章节结构与HTML/前端Tab保持一致

Phase 1.6（短期 P0）: 评分卡 Excel 报告"任务报告"Sheet 重构 ✅ 已完成 (2026-02-12)
├── ✅ 重构章节结构：与 HTML 保持一致的5章节（Excel以图表数据表格形式存在于独立Sheet，任务报告Sheet不含"评估图表"）
│       ├── 一、概览（汇总指标卡 + 数据集对比 + AI分析）
│       ├── 二、样本与特征
│       ├── 三、评分卡明细
│       ├── 四、变量筛选
│       └── 五、模型系数
├── ✅ 修改文件：excel_report.py 的 `_add_scorecard_task_report_sheet` 函数
└── 实际完成：章节结构重构完成，与 HTML/Word 报告对齐（Excel任务报告为5章节）

Phase 2（中长期 P2）: 配置驱动完整方案 ⏳ 待 Phase 1.5 + 1.6 完成后开始
├── ⏳ 2.1 配置模型增强（FieldDisplayConfig 等，可选）
├── ⏳ 2.2 HTML/Word/Markdown 报告生成器改造（读取配置动态渲染）
├── ⏳ 2.3 前端配置同步 API（/api/sop/config/{task_type}）
├── ⏳ 2.4 前端 Tab 列表改造（仅改 Tab 导航，保留所有子组件）
│       ├── ScorecardResults.tsx: ~20 行改动
│       ├── RuleMiningResults.tsx: ~20 行改动
│       └── 所有子组件（SampleDataPanel、ModelStatisticsPanel 等）：完全保留
└── 预估：2-2.5 人天

说明：
- Phase 0-1.6 已全部完成（HTML/Markdown/Word/Excel 报告重构）
- Phase 1.5 Word 报告：6章节结构（含评估图表）
- Phase 1.6 Excel 报告：5章节结构（任务报告Sheet不含评估图表，图表数据存在于独立Sheet）
- Phase 2 配置驱动重构可随时启动
- 前端改造范围：仅改 Tab 列表渲染，现有组件完全保留
- 当前报告生成器仍为硬编码实现，配置文件用于 AI 分析 Prompt 和 Excel 导出
```

---

**文档维护者**: AI Assistant  
**最后更新**: 2026-02-12

---

## 附录C：前端改造范围澄清

### C.1 常见误解

| 误解 | 事实 |
|------|------|
| "配置驱动会废弃现有 JSX 组件" | ❌ 错误。所有子组件完全保留 |
| "需要重写所有前端代码" | ❌ 错误。仅改 Tab 导航渲染，约 40 行代码 |
| "前端改造工作量大" | ❌ 错误。约 0.5 天，比后端改造少得多 |

### C.2 保留的前端组件清单

| 组件 | 文件 | 用途 | 改动 |
|------|------|------|------|
| `SampleDataPanel` | ScorecardResults.tsx | 样本与特征 | ❌ 不改 |
| `SampleFeaturePanel` | RuleMiningResults.tsx | 样本及特征 | ❌ 不改 |
| `ModelStatisticsPanel` | ModelStatisticsPanel.tsx | 模型系数 | ❌ 不改 |
| `ValidationReportPanel` | RuleMiningResults.tsx | 质量验证 | ❌ 不改 |
| `PSIReportPanel` | RuleMiningResults.tsx | 稳定性分析 | ❌ 不改 |
| `DecisionTreePanel` | RuleMiningResults.tsx | 决策树可视化 | ❌ 不改 |
| `RuleFilteringProcessPanel` | RuleMiningResults.tsx | 规则筛选过程 | ❌ 不改 |
| `AdvancedAnalysisPanel` | RuleMiningResults.tsx | 附加分析 | ❌ 不改 |
| 所有图表渲染组件 | 各文件 | KS/ROC/评分分布等 | ❌ 不改 |

### C.3 前端改造范围

**仅改动 2 个文件的 Tab 导航部分**：

```tsx
// 改动前（硬编码 Tab 列表）
<TabsList>
  <TabsTrigger value="sample-data">样本与特征</TabsTrigger>
  <TabsTrigger value="charts">评估图表</TabsTrigger>
  ...
</TabsList>

// 改动后（配置驱动 Tab 列表）
<TabsList>
  {config?.tabs.map(tab => (
    <TabsTrigger key={tab.id} value={tab.id}>{tab.name}</TabsTrigger>
  ))}
</TabsList>
```

**Tab 内容渲染部分**：通过组件映射表保持现有逻辑。

---

## 附录D：下一步待实施内容

> **状态**: 📋 待确认  
> **更新时间**: 2026-02-12

### D.1 优先级 P0（已完成 ✅）

| 序号 | 任务 | 文件 | 状态 | 完成时间 | 说明 |
|------|------|------|:----:|----------|------|
| **1** | Word 报告重构为6章节结构 | `word_report.py` | ✅ | 2026-02-12 | 与 HTML 报告对齐 |
| **2** | Excel "任务报告"Sheet 重构 | `excel_report.py` | ✅ | 2026-02-12 | 新增"二、样本与特征"，章节顺序对齐 HTML |

### D.2 优先级 P1（已完成 ✅）

| 序号 | 任务 | 文件 | 状态 | 完成时间 | 说明 |
|------|------|------|:----:|----------|------|
| **3** | 概览指标卡版式优化 | `html_report.py` | ✅ | 2026-02-12 | 四个指标卡一行，数据来源标注左上 |
| **4** | AI 分析 Prompt 数据源对齐检查 | `AI_analysis_prompts.py` | ✅ | 2026-02-12 | 似然比检验从 `model_fit` 获取，与前端 Tab 一致 |

### D.3 优先级 P2（中长期配置驱动）

| 阶段 | 内容 | 预估工作量 | 前置条件 |
|------|------|-----------|----------|
| **Phase 2** | 配置驱动完整方案 | 2-2.5 人天 | ✅ P0 + P1 已完成 |

### D.4 任务完成状态

```
Phase 1.5 (Word重构) ✅ 已完成
Phase 1.6 (Excel重构) ✅ 已完成
                       ↓
              Phase 2 (配置驱动方案) ⏳ 待评估

P0 任务 ✅ 全部完成
P1 任务 ✅ 全部完成
```

**当前进度**: P0 + P1 任务已全部完成，Phase 2 配置驱动方案障碍已清除！

---

### D.6 文档版本历史

| 版本 | 日期 | 更新内容 | 核实人 |
|------|------|---------|--------|
| v1.0 | 2026-02-09 | 初始创建文档 | 开发团队 |
| v1.1 | 2026-02-10 | 更新Phase 1.5/1.6完成状态，添加决策记录 | 开发团队 |
| v1.2 | 2026-02-12 | 标记Word/Excel重构完成，P0任务全部完成 | 开发团队 |
| v1.3 | 2026-03-02 | 核实实现状态：Phase 0-1.6已完成，Phase 2未实施 | AI Assistant |

### D.5 下一步建议

所有 P0 和 P1 任务已完成，现在可以：

1. **验证测试**：导出评分卡 Word 和 Excel 报告，验证章节结构是否正确
2. **评估 Phase 2**：根据业务需求决定是否实施配置驱动方案（2-2.5人天）
3. **其他优化**：如有其他报告相关需求，可以继续优化
