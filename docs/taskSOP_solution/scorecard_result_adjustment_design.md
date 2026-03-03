# 评分卡结果展示优化方案

> **状态**: ✅ 全部完成（已核实）  
> **创建时间**: 2025-02-04  
> **最后更新**: 2026-03-02（核实实现状态并更新文档）  
> **优先级**: P2（中期优化）  
> **实现核实**: 
> - ✅ `VariableIVRanking`、`ScoreScaleParams`、`FeatureSelectionFunnel` 已在 `ScorecardResults.tsx` 中实现
> - ✅ 代码库中已找到相关组件和逻辑实现
> - ✅ 所有Phase 1-9均已完成并验证

---

## 0. 版本历史与合并说明

> 本文档由原 `scorecard_results_optimization_plan.md` (v2.0已完成) 与 `scorecard_result_adjustment_plan.md` (已重命名为本文档) 合并而成。

| 阶段 | 来源文档 | 状态 |
|------|---------|------|
| **基础工作** | optimization_plan | ✅ 已完成 |
| **Tab精简重组** | adjustment_plan | ✅ 已完成 |

### 变更记录

| 日期 | 版本 | 变更内容 |
|------|------|----------|
| 2025-02-04 | v1.0 | 初始方案（阶段结果增强） |
| 2025-02-04 | v1.1 | 新增stagesData数据获取机制说明 |
| 2025-02-04 | v2.0 | **基础工作完成**：model_evaluation阶段展示增强、"样本及数据"Tab |
| 2026-02-05 | v2.1 | 新增Tab精简重组方案 |
| 2026-02-05 | v2.2 | 新增AI分析与Tab数据一致性优化 |
| 2026-02-05 | v2.3 | **Phase 4完成**：指标卡UI一致性优化（KS/AUC/Gini添加评估标签） |
| 2026-02-05 | v3.0 | **合并文档**：整合optimization_plan和adjustment_plan |
| 2026-02-06 | v3.1 | **新增第7.6节**：修复检查点保存时results完整性问题（iv_table等字段缺失） |

---

## 1. 优化概述

### 1.1 已完成的基础工作（原optimization_plan）

| 完成项 | 说明 | 状态 |
|--------|------|------|
| **stagesData获取机制修复** | 避免"样本及数据"Tab消失问题 | ✅ |
| **model_evaluation阶段增强** | 添加排序性分析/评分分布表格、CSV下载 | ✅ |
| **新增"样本及数据"Tab** | 展示数据概览、缺失率、数据集划分 | ✅ |
| **指标卡UI一致性** | KS/AUC/Gini添加评估标签（优秀/良好/可用/较差） | ✅ |

### 1.2 待实施的Tab精简重组

| 序号 | 调整前 | 调整后 | 变化说明 |
|------|--------|--------|---------|
| 1 | 样本及数据 | 样本及数据 | ✅ 已实现（基础工作） |
| 2 | 评估图表 | 评估图表 | 新增PSI分布对比图 |
| 3 | **特征筛选** | **变量筛选** | 重命名 + 合并IV排序内容 |
| 4 | 评分卡明细 | 评分卡明细 | **新增评分刻度参数** |
| 5 | **IV值排序** | ❌ 移除 | 合并至变量筛选Tab |
| 6 | **模型系数** | ❌ 移除 | 内容与统计检验重复 |
| 7 | **统计检验** | **模型系数** | 重命名（内容不变） |
| 8 | **评分转换** | ❌ 移除 | 评分刻度参数迁移至评分卡明细 |

**Tab数量**: 8 → 5

### 1.3 设计原则

| 原则 | 说明 |
|------|------|
| **阶段结果 vs 开发结果Tab** | 阶段结果展示详细执行指标，开发结果Tab汇总关键信息便于查阅和AI分析引用 |
| **内容可适度重叠** | 两者定位不同，核心信息可以在两处出现 |
| **功能不重复** | 下载/导出功能集中在阶段结果页面，开发结果Tab专注信息展示 |

---

## 2. 详细调整方案

### 2.1 Tab重命名：特征筛选 → 变量筛选

**理由**：
- "变量"是评分卡开发领域的标准术语
- "特征"更多用于机器学习领域
- 与评分卡明细、IV值等术语保持一致

**改动点**：
```tsx
// 调整前
<TabsTrigger value="selection" className="text-xs">
  <Layers className="h-3 w-3 mr-1" />
  特征筛选
</TabsTrigger>

// 调整后
<TabsTrigger value="selection" className="text-xs">
  <Layers className="h-3 w-3 mr-1" />
  变量筛选
</TabsTrigger>
```

---

### 2.2 合并IV值排序Tab至变量筛选Tab

#### 2.2.1 合并后的"变量筛选"Tab结构

```
┌─────────────────────────────────────────────────────────────────┐
│  变量筛选                                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 📊 变量IV排行                                            │   │
│  │ ──────────────────────────────────────────────────────── │   │
│  │ #  | 变量    | IV值   | 预测能力 | 状态   | 淘汰原因      │   │
│  │ 1  | var_a   | 0.45   | 强       | ✅入模 | -            │   │
│  │ 2  | var_b   | 0.38   | 强       | ❌淘汰 | 相关性>0.7   │   │
│  │ 3  | var_c   | 0.32   | 强       | ✅入模 | -            │   │
│  │ 4  | var_d   | 0.08   | 弱       | ❌淘汰 | IV<0.1       │   │
│  │ ...                                                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 🔍 异常值检测 (IQR方法)                                   │   │
│  │ （现有内容保持不变）                                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 📈 逐步回归                                               │   │
│  │ （现有内容保持不变）                                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ ✓ 显著性检验 (P值)                                        │   │
│  │ （现有内容保持不变）                                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 🎯 系数方向验证                                           │   │
│  │ （现有内容保持不变）                                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 2.2.2 新增"淘汰原因"列

将原IV排序Tab的简单表格增强为**带淘汰原因**的综合表格：

| # | 变量 | IV值 | 预测能力 | 状态 | 淘汰原因 |
|---|------|------|---------|------|---------|
| 1 | var_a | 0.45 | 强 | ✅ 入模 | - |
| 2 | var_b | 0.38 | 强 | ❌ 淘汰 | 与var_a相关性0.85 |
| 3 | var_c | 0.32 | 强 | ✅ 入模 | - |
| 4 | var_d | 0.25 | 中等 | ❌ 淘汰 | VIF=12.3 (>10) |
| 5 | var_e | 0.18 | 中等 | ❌ 淘汰 | P值=0.15 (>0.05) |
| 6 | var_f | 0.08 | 弱 | ❌ 淘汰 | IV<0.1 |
| 7 | var_g | 0.02 | 极弱 | ❌ 淘汰 | IV<0.02 |

**淘汰原因类型**：
- `IV<阈值`：IV值过低
- `与XXX相关性>阈值`：相关性筛选淘汰
- `VIF>阈值`：多重共线性
- `P值>阈值`：显著性不足
- `系数方向异常`：系数符号与业务逻辑不符

#### 2.2.3 数据来源

淘汰原因需要从各筛选阶段收集：

| 筛选阶段 | 数据来源 | 淘汰原因格式 |
|---------|---------|-------------|
| IV筛选 | `iv_table` + `iv_threshold` | `IV<{threshold}` |
| 相关性筛选 | `correlation_matrix` + `corr_threshold` | `与{var}相关性{value}` |
| VIF筛选 | `vif_result` | `VIF={value}` |
| 逐步回归 | `stepwise_result.removed_features` | `P值={pvalue}` |
| 系数验证 | `coefficient_validation.invalid_direction` | `系数方向异常` |

**后端需要扩展**：在结果中返回 `elimination_reasons` 字典：
```python
elimination_reasons = {
    "var_b": {"stage": "correlation", "reason": "与var_a相关性0.85"},
    "var_d": {"stage": "vif", "reason": "VIF=12.3"},
    "var_e": {"stage": "stepwise", "reason": "P值=0.15"},
    "var_f": {"stage": "iv", "reason": "IV=0.08<0.1"},
}
```

---

### 2.3 评分卡明细Tab增强：整合评分刻度参数

#### 2.3.1 调整后的"评分卡明细"Tab结构

```
┌─────────────────────────────────────────────────────────────────┐
│  评分卡明细Tab                                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📋 评分刻度参数                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ 基准分: 600 │ 基准Odds: 20:1 │ PDO: 50                    │ │
│  │ 理论评分范围: 431 ~ 807                                    │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  📊 变量得分详情                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ 变量名 │ 分箱数 │ 得分范围        │ 最大贡献              │ │
│  ├────────┼────────┼─────────────────┼──────────────────────┤ │
│  │ f73    │ 5      │ [-70.9, +71.07] │ 141.97分             │ │
│  │ f47    │ 3      │ [-12.7, +61.29] │ 73.99分              │ │
│  │ f65    │ 4      │ [-26.79, +43.79]│ 70.58分              │ │
│  │ f71    │ 6      │ [-35.84, +16.78]│ 52.62分              │ │
│  │ f70    │ 5      │ [-17.96, +28.83]│ 46.79分              │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  （点击变量名可展开查看分箱详情）                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 2.3.2 设计说明

| 组件 | 来源 | 说明 |
|------|------|------|
| **评分刻度参数** | 从原评分转换Tab迁移 | 基准分、基准Odds、PDO、理论评分范围 |
| **变量得分详情** | 现有内容 | 保持不变 |
| **下载功能** | ❌ 不在此Tab | 已在阶段结果页面实现 |

#### 2.3.3 与阶段结果页面的关系

| 展示位置 | 内容 | 定位 |
|---------|------|------|
| **评分转换阶段结果** | 完整详情（含训练集评分分布、AI分析等） | 阶段执行的详细结果 |
| **评分卡明细Tab** | 评分刻度参数 + 变量得分详情 | 汇总展示，便于快速查阅和AI分析引用 |

---

### 2.4 模型系数Tab与统计检验Tab合并

#### 2.4.1 合并前后对比

| 对比维度 | 模型系数Tab（原） | 统计检验Tab（原） |
|---------|----------------|-----------------|
| 系数值 | ✅ | ✅ |
| P值 | ✅ | ✅ |
| 标准误 | ❌ | ✅ |
| z值 | ❌ | ✅ |
| 置信区间 | ❌ | ✅ |
| 模型拟合度 | ❌ | ✅ (AIC/BIC/Pseudo R²) |
| 系数方向Badge | ✅ | ❌ |

**结论**：统计检验Tab是模型系数Tab的**超集**

#### 2.4.2 调整方案

| 操作 | 说明 |
|------|------|
| **移除模型系数Tab** | 信息重复 |
| **保留统计检验Tab** | 内容完整 |
| **重命名为"模型系数"** | 名称更直观 |

#### 2.4.3 调整后的"模型系数"Tab（原统计检验）

```
┌─────────────────────────────────────────────────────────────────┐
│  模型系数Tab（原统计检验）                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📊 模型系数与统计检验                                           │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ 变量      │ 系数   │ 标准误 │ z值   │ P值    │ 95%置信区间 │ │
│  ├───────────┼────────┼────────┼───────┼────────┼────────────┤ │
│  │ Intercept │ -2.34  │ 0.12   │ -19.5 │ <0.001 │[-2.57,-2.11]│ │
│  │ age       │ 0.234  │ 0.045  │ 5.2   │ <0.001 │[0.15, 0.32] │ │
│  │ income    │ -0.156 │ 0.068  │ -2.3  │ 0.023  │[-0.29,-0.02]│ │
│  │ ...                                                       │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  📈 模型拟合度                                                   │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ AIC: 1234.5 │ BIC: 1256.8 │ Pseudo R²: 0.35              │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 2.5 移除评分转换Tab

#### 2.5.1 原评分转换Tab内容处理

| 组件 | 处理方式 | 理由 |
|------|---------|------|
| **评分刻度参数** | ✅ 迁移至评分卡明细Tab | 核心配置信息，便于查阅 |
| **交互式转换工具** | ❌ 移除 | 非行业标准交付物 |
| **评分-风险对照** | ❌ 不新增 | 功能已在评估图表Tab的"评分分布(等宽)"视图中存在 |

#### 2.5.2 行业惯例说明

| 交付物类型 | 行业标准 | 当前实现 |
|-----------|---------|---------|
| 评分刻度参数 | ✅ 必需 | ✅ 在阶段结果 + 评分卡明细Tab |
| 评分-概率对照表 | ✅ 必需 | ✅ 在评估图表Tab的评分分布视图 |
| 交互式转换工具 | ❌ 非标准 | ❌ 移除 |

---

### 2.6 新增PSI分布对比图

**位置**：评估图表Tab → 新增一个图表

**效果**：
```
PSI分布对比图（训练集 vs OOT）  PSI = 0.08 (稳定)
     ┌─────────────────────────────────────────┐
     │  ██ 训练集(Expected)   ▓▓ OOT(Actual)   │
     │                                         │
20%  │  ██▓▓                                   │
     │  ██▓▓  ██                               │
15%  │  ██▓▓  ██▓▓  ██                         │
     │  ██▓▓  ██▓▓  ██▓▓  ██                   │
10%  │  ██▓▓  ██▓▓  ██▓▓  ██▓▓  ██             │
     │  ██▓▓  ██▓▓  ██▓▓  ██▓▓  ██▓▓  ██       │
 5%  │  ██▓▓  ██▓▓  ██▓▓  ██▓▓  ██▓▓  ██▓▓     │
     └─────────────────────────────────────────┘
        [300-400)  [400-500)  [500-600) ...
                      评分区间
```

**数据来源**：
- 后端已返回 `score_distribution_data` 包含 train/test/oot 三个数据集
- 每个数据集有 `bins` 数组，包含各分数段的样本占比

**前端实现**：
- 新增 `PSIComparisonChart` 组件
- 对比数据集选择逻辑：
  - 有OOT → 训练集 vs OOT
  - 无OOT → 训练集 vs 测试集
- 与 `psi_result.comparison` 保持一致

**展示位置**：评估图表Tab的图表顺序调整为：
1. ROC曲线
2. KS曲线
3. Lift曲线
4. **PSI分布对比图** ← 新增
5. 多数据集评分分布（现有）

---

## 3. 最终Tab布局

### 3.1 调整后的Tab列表（5个）

| # | Tab名称 | 内容 | AI分析可引用 |
|---|--------|------|-------------|
| 1 | **样本及数据** | 数据预处理概览 | ✅ |
| 2 | **评估图表** | ROC/KS/Lift/PSI对比图/评分分布 | ✅ |
| 3 | **变量筛选** | IV排行 + 筛选过程 + 淘汰原因 | ✅ |
| 4 | **评分卡明细** | 评分刻度参数 + 变量得分详情 | ✅ |
| 5 | **模型系数** | 系数+标准误+z值+P值+置信区间+拟合度 | ✅ |

### 3.2 精简效果

| 维度 | 调整前 | 调整后 |
|------|--------|--------|
| **Tab数量** | 8 | 5 |
| **移除的Tab** | - | IV值排序、模型系数（原）、评分转换 |
| **重命名的Tab** | - | 特征筛选→变量筛选、统计检验→模型系数 |
| **增强的Tab** | - | 评分卡明细（+评分刻度参数） |
| **新增功能** | - | PSI分布对比图 |

---

## 4. 技术实现细节

### 4.1 前端改动清单

| 文件 | 改动内容 |
|------|---------|
| `ScorecardResults.tsx` | 1. Tab名称改为"变量筛选" |
| | 2. 移除"IV值排序"Tab |
| | 3. 移除"模型系数"Tab（原） |
| | 4. 移除"评分转换"Tab |
| | 5. 将"统计检验"Tab重命名为"模型系数" |
| | 6. 在"变量筛选"Tab顶部添加"变量IV排行"模块 |
| | 7. 在"评分卡明细"Tab顶部添加"评分刻度参数"模块 |
| | 8. 新增 `PSIComparisonChart` 组件 |
| | 9. 在评估图表Tab集成PSI对比图 |

### 4.2 后端改动清单

| 文件 | 改动内容 |
|------|---------|
| `scorecard_development.py` | 收集各阶段淘汰原因，返回 `elimination_reasons` |

### 4.3 组件设计

#### 4.3.1 评分刻度参数组件

```tsx
interface ScoreScaleParamsProps {
  baseScore: number;       // 基准分
  baseOdds: number;        // 基准Odds
  pdo: number;             // PDO
  minScore?: number;       // 理论最低分
  maxScore?: number;       // 理论最高分
}

function ScoreScaleParams({ 
  baseScore, 
  baseOdds, 
  pdo, 
  minScore, 
  maxScore 
}: ScoreScaleParamsProps) {
  return (
    <div className="flex flex-wrap gap-2 p-3 bg-muted/50 rounded-lg text-sm">
      <Badge variant="outline">基准分: {baseScore}</Badge>
      <Badge variant="outline">基准Odds: {baseOdds}:1</Badge>
      <Badge variant="outline">PDO: {pdo}</Badge>
      {minScore && maxScore && (
        <Badge variant="outline">理论评分范围: {minScore} ~ {maxScore}</Badge>
      )}
    </div>
  );
}
```

#### 4.3.2 变量IV排行组件

```tsx
interface VariableIVRankingProps {
  ivData: { variable: string; iv: number }[];
  modelVariables: string[];  // 入模变量列表
  eliminationReasons?: Record<string, { stage: string; reason: string }>;
}

function VariableIVRanking({ 
  ivData, 
  modelVariables, 
  eliminationReasons 
}: VariableIVRankingProps) {
  // 1. 按IV值降序排列
  // 2. 判断是否入模
  // 3. 显示淘汰原因（如有）
  // 4. 入模变量绿色高亮
}
```

#### 4.3.3 PSI分布对比图组件

```tsx
interface PSIComparisonChartProps {
  expectedData: ScoreDistributionBins[];
  expectedLabel: string;  // "训练集"
  actualData: ScoreDistributionBins[];
  actualLabel: string;    // "OOT验证集" 或 "测试集"
  psiResult: {
    value: number;
    comparison: string;
    stability: string;
    level: string;
  };
}

function PSIComparisonChart({ 
  expectedData, 
  expectedLabel,
  actualData, 
  actualLabel,
  psiResult 
}: PSIComparisonChartProps) {
  // 1. 对齐两个数据集的分箱
  // 2. 计算每个分箱的占比
  // 3. 绘制双柱状图
  // 4. 标注PSI值和稳定性状态
}
```

---

## 5. 实现步骤

### Phase 1: Tab重组（核心）
- [x] **Step 1.1**: 将"特征筛选"重命名为"变量筛选" ✅ 已完成
- [x] **Step 1.2**: 移除"IV值排序"Tab，内容迁移到"变量筛选"Tab顶部 ✅ 已完成
- [x] **Step 1.3**: 移除"模型系数"Tab（原），将"统计检验"重命名为"模型系数" ✅ 已完成
- [x] **Step 1.4**: 移除"评分转换"Tab ✅ 已完成
- [x] **Step 1.5**: 在"评分卡明细"Tab顶部添加"评分刻度参数"模块 ✅ 已完成
- [x] **Step 1.6**: 测试调整后的展示效果 ✅ 已完成

### Phase 2: 增强IV排行（淘汰原因列）
- [x] **Step 2.1**: 后端已提供各阶段淘汰原因（all_features_detail.remove_reason） ✅ 已确认
- [x] **Step 2.2**: 前端展示淘汰原因列 ✅ 已完成
- [x] **Step 2.3**: 淘汰原因来源整合（IV筛选/相关性/VIF/逐步回归/系数方向） ✅ 已完成

### Phase 3: PSI分布对比图
- [x] **Step 3.1**: 确认后端数据结构满足需求 ✅ 已确认（multiDatasetChartData.*.score_distribution）
- [x] **Step 3.2**: 新增 `PSIComparisonChart` 组件 ✅ 已完成
- [x] **Step 3.3**: 在评估图表Tab集成（Lift曲线后） ✅ 已完成
- [x] **Step 3.4**: 支持有/无OOT场景（自动选择对比数据集） ✅ 已完成

### Phase 4: 指标卡UI一致性优化
- [x] **Step 4.1**: 为KS/AUC/Gini指标卡添加评估结果文字（与PSI保持一致）✅ 已完成
- [x] **Step 4.2**: 优化Tooltip第二行说明文字的对比度 ✅ 已完成

---

## 5.1 指标卡UI优化详情（Phase 4）

### 5.1.1 问题描述

| 问题 | 现状 | 期望 |
|------|------|------|
| **评估结果不一致** | PSI卡片下方有"稳定"等评估文字，KS/AUC/Gini没有 | 四个指标卡统一显示评估结果 |
| **Tooltip对比度不足** | 第二行小字使用`text-muted-foreground`，与Tooltip背景色接近 | 提高对比度，确保可读性 |

### 5.1.2 指标评估标准

| 指标 | 优秀 | 良好 | 可用 | 较差 |
|------|------|------|------|------|
| **KS值** | ≥40% | 30%-40% | 20%-30% | <20% |
| **AUC** | ≥0.8 | 0.75-0.8 | 0.7-0.75 | <0.7 |
| **Gini** | ≥60% | 50%-60% | 40%-50% | <40% |
| **PSI** | <0.1 (稳定) | 0.1-0.25 (轻微变化) | - | ≥0.25 (显著变化) |

### 5.1.3 实现方案

#### A. 评估结果辅助函数

```typescript
// 获取KS评估结果
function getKSLevel(ks: number): { label: string; level: 'excellent' | 'good' | 'acceptable' | 'poor' } {
  if (ks >= 0.4) return { label: '优秀', level: 'excellent' };
  if (ks >= 0.3) return { label: '良好', level: 'good' };
  if (ks >= 0.2) return { label: '可用', level: 'acceptable' };
  return { label: '较差', level: 'poor' };
}

// 获取AUC评估结果
function getAUCLevel(auc: number): { label: string; level: 'excellent' | 'good' | 'acceptable' | 'poor' } {
  if (auc >= 0.8) return { label: '优秀', level: 'excellent' };
  if (auc >= 0.75) return { label: '良好', level: 'good' };
  if (auc >= 0.7) return { label: '可用', level: 'acceptable' };
  return { label: '较差', level: 'poor' };
}

// 获取Gini评估结果
function getGiniLevel(gini: number): { label: string; level: 'excellent' | 'good' | 'acceptable' | 'poor' } {
  if (gini >= 0.6) return { label: '优秀', level: 'excellent' };
  if (gini >= 0.5) return { label: '良好', level: 'good' };
  if (gini >= 0.4) return { label: '可用', level: 'acceptable' };
  return { label: '较差', level: 'poor' };
}
```

#### B. 指标卡增强（以KS为例）

```tsx
// 调整前
<div className="text-2xl font-bold text-blue-700 dark:text-blue-300">
  {(metrics.ks * 100).toFixed(2)}%
</div>

// 调整后
<div className="text-2xl font-bold text-blue-700 dark:text-blue-300">
  {(metrics.ks * 100).toFixed(2)}%
</div>
{/* 新增评估结果文字 */}
<div className="text-xs text-muted-foreground mt-0.5">
  {getKSLevel(metrics.ks).label}
</div>
```

#### C. Tooltip对比度优化

```tsx
// 调整前
<p className="text-xs text-muted-foreground">0.5=随机，0.7+=可用，0.8+=优秀</p>

// 调整后（提高对比度）
<p className="text-xs text-gray-500 dark:text-gray-300">0.5=随机，0.7+=可用，0.8+=优秀</p>
```

### 5.1.4 效果对比

**调整前**：
```
┌─────────────┬─────────────┬─────────────┬─────────────┐
│   KS值      │    AUC      │    Gini     │    PSI      │
│  31.48%     │   0.7097    │   41.94%    │   0.0020    │
│             │             │             │   稳定       │
└─────────────┴─────────────┴─────────────┴─────────────┘
```

**调整后**：
```
┌─────────────┬─────────────┬─────────────┬─────────────┐
│   KS值      │    AUC      │    Gini     │    PSI      │
│  31.48%     │   0.7097    │   41.94%    │   0.0020    │
│   良好       │   可用       │   可用       │   稳定       │
└─────────────┴─────────────┴─────────────┴─────────────┘
```

---

## 6. 预期效果

### 6.1 Tab数量精简
- 调整前：8个Tab
- 调整后：5个Tab
- 减少用户的认知负担

### 6.2 信息整合
- **变量筛选Tab**：一站式变量审查入口（IV排行 + 筛选过程）
- **评分卡明细Tab**：一站式评分卡查阅入口（刻度参数 + 变量得分）
- **模型系数Tab**：完整的系数与统计检验信息

### 6.3 术语规范
- "变量筛选"比"特征筛选"更符合评分卡领域惯例
- "模型系数"比"统计检验"更直观

### 6.4 功能分布清晰
| 功能类型 | 展示位置 |
|---------|---------|
| **信息展示** | 开发结果Tab |
| **下载/导出** | 阶段结果页面 |
| **交互式工具** | 已移除（非标准功能） |

---

## 7. AI分析与Tab数据一致性优化

> **背景**：AI分析Prompt获取的数据与开发结果Tab展示的数据应保持一致，避免AI分析结论与用户在Tab中看到的内容出现偏差。

### 7.1 规则挖掘 vs 评分卡：数据一致性对比

| 任务类型 | AI分析数据源 | Tab数据源 | 一致性评估 |
|---------|-------------|-----------|-----------|
| **评分卡开发** | `stages`（为主）+ `outputs` | `outputs`（为主） | ⚠️ **存在不一致风险** |
| **规则挖掘** | `outputs`（为主）+ `stages`（少量） | `outputs`（为主）+ `stagesData`（样本Tab） | ✅ **基本一致** |

### 7.2 评分卡任务的数据一致性风险

#### 7.2.1 问题分析

| 数据类型 | AI分析Prompt来源 | 开发结果Tab来源 | 一致性 |
|---------|-----------------|----------------|--------|
| 样本概况 | `stages.data_loading.output_preview` | `stagesData.data_loading.output_preview` | ✅ 一致 |
| 特征筛选 | `stages.feature_selection.output_preview` | `outputs.feature_selection` | ⚠️ **路径不同** |
| 模型性能 | `stages.model_evaluation.output_preview` | `outputs.model_metrics` | ⚠️ **路径不同** |
| 评分刻度 | `stages.score_conversion.output_preview` | `outputs.score_params` | ⚠️ **路径不同** |

#### 7.2.2 潜在风险点

1. **特征数量取值路径略有不同**
2. **筛选阈值在Tab中未直接展示**
3. **数据更新时机可能不同步**

### 7.3 "样本及数据"Tab使用`stagesData`的原因

> **历史问题**：曾出现"样本及特征"Tab消失的问题，原因是API调用机制问题，而非数据源选择问题。

#### 7.3.1 已修复的方案

| 场景 | 解决方案 |
|------|---------|
| **历史记录加载** | `getTaskHistoryResult()` 同时返回 `result` 和 `stages` |
| **执行结果加载** | 通过 `record_id` 获取 `stages` 数据 |

#### 7.3.2 为什么维持使用`stagesData`

| 理由 | 说明 |
|------|------|
| **数据结构专门为展示优化** | `output_preview` 是为前端Tab展示设计的精简结构 |
| **问题已修复** | API调用机制bug已通过返回`stages`字段解决 |
| **历史兼容性** | 已处理旧历史记录没有stages的情况 |

#### 7.3.3 `outputs.preprocessing` vs `stagesData.preprocessing.output_preview`

| 数据源 | 数据结构 | 适用场景 |
|-------|---------|---------|
| `outputs.preprocessing` | `{type: "dataframe", data: {...}}` 包装结构 | 后端完整数据存储 |
| `stagesData.preprocessing.output_preview` | 直接是对象 `{rows, target_rate, ...}` | 前端展示优化 |

**结论**：两者内容来源相同，但`output_preview`是专门为展示设计的，维持使用`stagesData`是正确选择。

### 7.4 优化建议

> **核心原则**：评分卡任务可参考规则挖掘的设计，提升数据一致性。

#### 7.4.1 建议措施

| 建议 | 说明 | 优先级 |
|------|------|--------|
| **AI分析Prompt尽量从`outputs`获取数据** | 减少对`stages`的依赖 | P2 |
| **确保Tab和AI分析使用相同的数据字段** | 避免展示与分析结论不一致 | P2 |
| **维持"样本及数据"Tab使用`stagesData`** | 已验证的稳定方案 | ✅ 已实现 |

#### 7.4.2 实施步骤

- [x] **Step 7.1**: 审查`AI_analysis_prompts.py`中评分卡任务的数据来源 ✅ 已完成
- [x] **Step 7.2**: 对比AI分析字段与Tab展示字段的一致性 ✅ 已完成
- [x] **Step 7.3**: 必要时调整AI分析Prompt使用`outputs`字段 ✅ 无需调整（已一致）
- [x] **Step 7.4**: 验证AI分析结论与Tab展示内容一致 ✅ 已验证

### 7.5 数据一致性分析结论（2026-02-06）

#### 7.5.1 AI分析Prompt数据来源（`_build_scorecard_overall_prompt`）

| 数据类型 | 数据来源 | 字段路径 |
|---------|---------|---------|
| 样本概况 | `stages` | `stages.preprocessing.output_preview` 或 `stages.data_loading.output_preview` |
| WOE分箱信息 | `stages` | `stages.woe_binning.output_preview` |
| 特征筛选 | `stages` | `stages.feature_selection.output_preview` |
| 模型性能 | `outputs` | `outputs.multi_dataset_metrics` |
| PSI | `stages` + `outputs` | `stages.model_evaluation.output_preview.psi` 或 `outputs.psi` |
| 评分卡 | `outputs` | `outputs.scorecard` |
| IV分布 | `outputs` | `outputs.iv_table` |

#### 7.5.2 前端Tab数据来源

| Tab名称 | 数据来源 | 字段路径 |
|--------|---------|---------|
| 样本及数据 | `stagesData` | `stagesData.data_loading.output_preview` |
| 评估图表 | `outputs` | `outputs.multi_dataset_metrics` + `outputs.multi_dataset_chart_data` |
| 变量筛选 | `stagesData` + `outputs` | `stagesData.feature_selection.output_preview` + `outputs.iv_table` |
| 评分卡明细 | `outputs` | `outputs.scorecard` |
| 模型系数 | `outputs` | `outputs.coefficients` + `outputs.model_summary` |

#### 7.5.3 一致性评估结论

| 关键指标 | AI分析来源 | Tab展示来源 | 一致性 |
|---------|-----------|------------|--------|
| 样本总量 | `stages.preprocessing.output_preview.rows` | `stagesData.data_loading.output_preview.rows` | ✅ 一致 |
| 坏账率 | `stages.preprocessing.output_preview.target_rate` | `stagesData.data_loading.output_preview.target_rate` | ✅ 一致 |
| KS/AUC/Gini | `outputs.multi_dataset_metrics` | `outputs.multi_dataset_metrics` | ✅ 完全一致 |
| PSI | `outputs.psi` 或 `stages.model_evaluation.output_preview.psi` | `outputs.psi_result` | ✅ 一致 |
| 评分卡变量数 | `outputs.scorecard` | `outputs.scorecard` | ✅ 完全一致 |
| IV分布 | `outputs.iv_table` | `outputs.iv_table` | ✅ 完全一致 |

**结论**：AI分析Prompt与Tab展示使用的数据来源基本一致，无需调整。
- `stages`和`stagesData`实际是同一数据（前端从`result.stages`获取）
- 核心指标（KS/AUC/Gini/PSI/评分卡）均使用`outputs`字段，完全一致
- 样本信息虽然路径略有不同（`preprocessing` vs `data_loading`），但数据内容相同（后端会回退到data_loading）

---

## 8. 已完成的技术实现（原optimization_plan）

> 以下内容从 `scorecard_results_optimization_plan.md` 合并，记录已完成的基础工作。

### 8.1 stagesData数据获取机制（关键）

> **背景**：曾出现"样本及特征"Tab在历史记录中不可见的问题，原因是 `stagesData` 通过单独的API调用获取，失败后被静默忽略。

#### 问题根源

| 数据类型 | 获取方式 | 问题 |
|---------|---------|------|
| `result.outputs`（其它Tab） | `getTaskHistoryResult()` | ✅ 主调用，失败会显示错误 |
| `stagesData`（样本及数据Tab） | `getTaskHistoryDetail()` 单独调用 | ❌ 失败被静默吞掉，导致Tab不显示 |

#### ✅ 已修复方案

**场景1：历史记录加载**（`executionId` 以 `rec:` 开头）

```typescript
// ScorecardResults.tsx - 历史记录加载
if (executionId.startsWith("rec:")) {
  const recId = executionId.substring(4);
  const historyResult = await sopService.getTaskHistoryResult(recId);
  
  // ✅ result 和 stages 来自同一个API响应
  setResult({
    execution_id: recId,
    status: "completed",
    outputs: historyResult.result || {},
  });
  setStagesData(historyResult.stages || null);
}
```

**场景2：执行结果加载**（`executionId` 以 `exec-` 开头）

```typescript
// ScorecardResults.tsx - 执行结果加载
if (!executionId.startsWith("rec:")) {
  const execResult = await sopService.getExecutionResult(executionId);
  setResult(execResult);
  
  // ⚠️ 必须通过record_id获取stages
  if (execResult.record_id) {
    const historyResult = await sopService.getTaskHistoryResult(execResult.record_id);
    setStagesData(historyResult.stages || null);
  }
}
```

### 8.2 model_evaluation阶段展示增强

#### 后端数据结构

```python
model_evaluation_preview = {
    # 现有字段
    "train_metrics": {...},
    "test_metrics": {...},
    "psi_result": {...},
    "overfit_warning": "...",
    
    # 新增字段
    "score_distribution": {
        "train": {
            "bins": [...],
            "summary": {"total_samples": 10000, "overall_bad_rate": 5.13, ...},
            "ranking_analysis": {"bins": [...], "n_bins": 10, "bin_method": "equal_frequency"},
            "distribution_view": {"bins": [...], "n_bins": 8, "bin_method": "equal_width"}
        },
        "test": {...},
        "oot": {...}
    }
}
```

#### 前端展示效果

```
┌─────────────────────────────────────────────────────────┐
│ 模型评估阶段                                              │
├─────────────────────────────────────────────────────────┤
│ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐                    │
│ │ AUC  │ │  KS  │ │ Gini │ │ PSI  │                    │
│ │0.7523│ │31.48%│ │50.46%│ │0.0020│                    │
│ │ 可用  │ │ 良好  │ │ 良好  │ │ 稳定 │  ← 新增评估标签    │
│ └──────┘ └──────┘ └──────┘ └──────┘                    │
├─────────────────────────────────────────────────────────┤
│ 排序性分析                                                │
│ 数据集: [训练集] [测试集▼]   视图: [排序性▼] [分布] [CSV↓] │
│ ┌────┬───────────────┬──────┬────────┬──────┬──────────┐ │
│ │序号│  分数区间      │样本数│坏样本率 │ Lift │累计坏样本率│ │
│ │... │ ...           │ ...  │  ...   │ ...  │   ...    │ │
│ └────┴───────────────┴──────┴────────┴──────┴──────────┘ │
└─────────────────────────────────────────────────────────┘
```

### 8.3 指标评估标准函数

```typescript
// ScorecardResults.tsx 中已实现
function getKSLevel(ks: number): MetricEvaluation {
  if (ks >= 0.4) return { label: '优秀', level: 'excellent', colorClass: 'text-green-600' };
  if (ks >= 0.3) return { label: '良好', level: 'good', colorClass: 'text-blue-600' };
  if (ks >= 0.2) return { label: '可用', level: 'acceptable', colorClass: 'text-yellow-600' };
  return { label: '较差', level: 'poor', colorClass: 'text-red-600' };
}

function getAUCLevel(auc: number): MetricEvaluation { /* 类似逻辑 */ }
function getGiniLevel(gini: number): MetricEvaluation { /* 类似逻辑 */ }
```

---

## 9. 相关文件

- 前端：`demo/chat/components/sop/ScorecardResults.tsx`
- 前端：`demo/chat/components/sop/StageOutputPreview.tsx`（ModelEvaluationPreview）
- 后端：`deepanalyze/analysis/task_SOP/scorecard_development.py`
- AI分析Prompt：`API/AI_analysis_prompts.py`
- 相关组件：`MultiDatasetScoreDistribution`
- 相关组件：`ModelStatisticsPanel.tsx`
- 相关组件：`ScoreConverter.tsx`（待移除）
- 参考设计：`docs/taskSOP_solution/sample_feature_tab_design.md`

---

### 7.6 补充修复：检查点保存时results完整性（2026-02-06）

#### 7.6.1 问题描述

历史记录中 `outputs` 缺少 `iv_table`、`selection_detail`、`outlier_info`、`bins` 等字段。

**根因**：检查点保存时，`_full_stage_data["results"]` 是在更新 `results` 字典**之前**创建的副本，导致该阶段添加的数据未被包含。

```python
# 问题代码顺序
woe_binning_preview = {
    "_full_stage_data": {
        "results": dict(results),  # ❌ 此时 results 还没有 iv_table
        ...
    }
}
results['iv_table'] = iv_table     # 后添加的数据
self._update_progress(...)         # 保存检查点
```

#### 7.6.2 修复方案

在以下阶段的 `_update_progress` 调用**前**，重新赋值 `preview["_full_stage_data"]["results"] = dict(results)`：

| 阶段 | 修复内容 |
|------|---------|
| `data_loading` | `data_loading_preview["_full_stage_data"]["results"] = dict(results)` |
| `woe_binning` | `woe_binning_preview["_full_stage_data"]["results"] = dict(results)` |
| `feature_selection` | `feature_selection_preview["_full_stage_data"]["results"] = dict(results)` |
| `model_training` | `model_training_preview["_full_stage_data"]["results"] = dict(results)` |
| `score_scaling` | `score_scaling_preview["_full_stage_data"]["results"] = dict(results)` |

**注**：`model_evaluation` 和 `report_generation` 阶段**无需修改**，因为它们原本就是正确顺序（先更新 `results`，再构建 `preview`）。

#### 7.6.3 对一致性的影响

| 影响范围 | 说明 |
|---------|------|
| ❌ 不影响已验证的一致性 | AI分析Prompt主要依赖 `stages.*.output_preview`，不受影响 |
| ✅ 正向增强数据完整性 | `outputs.iv_table`、`outputs.selection_detail` 等字段修复后可用 |
| ✅ Tab展示更可靠 | "变量筛选"Tab依赖的 `iv_table` 数据在历史记录中可正常加载 |

#### 7.6.4 验证方式

**新任务**：重新执行一次评分卡任务（全新执行），检查历史记录是否包含完整的 `iv_table` 等字段。

**旧历史记录**：已保存的历史记录（如 `rec-e1fec0180ba6`）仍缺少这些字段，需重新执行才能获得完整数据。

---

## 10. 实施进度总览

| Phase | 内容 | 状态 | 备注 |
|-------|------|------|------|
| **基础工作** | stagesData机制、model_evaluation增强、"样本及数据"Tab | ✅ 已完成 | 原optimization_plan |
| **Phase 1** | Tab重组（8→5个） | ✅ 已完成 | 2026-02-05 |
| **Phase 2** | 增强IV排行（淘汰原因列） | ✅ 已完成 | 2026-02-06 |
| **Phase 3** | PSI分布对比图 | ✅ 已完成 | 2026-02-06 |
| **Phase 4** | 指标卡UI一致性 | ✅ 已完成 | |
| **第7章** | AI分析与Tab数据一致性 | ✅ 已完成 | 2026-02-06（已验证一致） |
| **第7.6节** | 检查点保存results完整性修复 | ✅ 已完成 | 2026-02-06 |
| **第7.7节** | 阶段AI分析格式优化（禁止格式化列表） | ✅ 已完成 | 2026-02-06 |
| **Phase 5** | 变量筛选Tab添加特征漏斗概览 | ✅ 已完成 | 2026-02-06 |

---

## 11. Phase 5：变量筛选Tab特征漏斗概览（2026-02-06）

### 11.1 问题描述

当前"变量筛选"Tab只展示IV排行和淘汰原因，未能体现由原始特征到最终入模变量的完整筛选过程。

**参考对象**：规则挖掘开发结果的"筛选过程"Tab，提供了清晰的漏斗概览（生成规则 → 规则筛选 → 最优选择）。

### 11.2 实现方案

新增 `FeatureSelectionFunnel` 组件，展示特征筛选的四阶段漏斗：

```
原始特征 → WOE分箱 → IV/相关性/VIF → 最终入模
   N个        M1个        M2个           K个
  100%       xx.x%       xx.x%         xx.x%
```

**数据来源**：
| 阶段 | 数据源 | 字段 |
|------|--------|------|
| 原始特征 | `data_loading.output_preview` | `feature_count` 或 `columns` |
| WOE分箱 | `woe_binning.output_preview` | `binned_count` |
| IV/相关性/VIF | `feature_selection.output_preview` | `after_count` 或 `selected_count` |
| 最终入模 | `modelVariables.length` | 从系数表提取 |

### 11.3 修改文件

| 文件 | 修改内容 |
|------|---------|
| `ScorecardResults.tsx` | 新增 `FeatureSelectionFunnel` 组件 |
| `ScorecardResults.tsx` | 在"变量筛选"Tab中引用该组件 |
| `ScorecardResults.tsx` | 添加 `GitBranch`、`ChevronRight` 图标导入 |

### 11.4 UI效果

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 🔀 特征筛选漏斗                                                              │
│                                                                             │
│  ┌────────┐   ┌────────┐   ┌────────┐   ┌────────┐   ┌────────┐           │
│  │原始特征│ → │质量筛选│ → │WOE分箱 │ → │IV/相关 │ → │最终入模│           │
│  │   81   │   │   49   │   │   43   │   │   7    │   │   5    │           │
│  │  100%  │   │  60%   │   │  53%   │   │   9%   │   │   6%   │           │
│  │        │   │  -32   │   │   -6   │   │  -36   │   │   -2   │           │
│  │        │   │高同值率│   │常量等  │   │IV/相关│   │逐步回归│           │
│  └────────┘   └────────┘   └────────┘   └────────┘   └────────┘           │
│                                                                             │
│  特征保留率：6.2%（81 → 5）                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 12. Phase 6：异常值展示优化（2026-02-06）

### 12.1 问题描述

变量筛选Tab中展示了异常值检测（IQR方法）明细表格，但：
1. 与规则挖掘任务的展示方式不一致（规则挖掘只展示汇总数字）
2. 数据加载阶段结果也只展示汇总，不展示明细
3. 异常值检测"仅检测不移除"，不影响特征筛选决策，在变量筛选Tab中展示意义不大

### 12.2 参考规则挖掘展示方式

| 位置 | 规则挖掘展示 | 评分卡原展示 | 评分卡优化后 |
|------|-------------|-------------|-------------|
| 阶段结果（数据加载/预处理） | 一行提示："检测到 39 个特征存在异常值" | ✅ 同样一行提示 | 保持不变 |
| 开发结果（样本及特征Tab） | 指标卡："39 异常值特征数" | ❌ 无 | ✅ 添加指标卡 |
| 变量筛选Tab | ❌ 无 | 明细表格（前10个变量） | ✅ 移除 |

### 12.3 修改内容

1. **移除**：变量筛选Tab中的异常值明细表格
2. **新增**：样本及数据Tab特征概览中添加"异常值特征数"指标卡
3. **清理**：移除未使用的 `OutlierInfo` 接口和 `outlierInfo` 变量

### 12.4 修改前后对比

**样本及数据Tab - 特征概览**：
```
修改前：
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│原始特征数 │  │平均缺失率 │  │WOE分箱变量│  │筛选后特征 │
└──────────┘  └──────────┘  └──────────┘  └──────────┘

修改后：
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│原始特征数 │  │平均缺失率 │  │异常值特征数│  │WOE分箱变量│
└──────────┘  └──────────┘  └──────────┘  └──────────┘
```

**变量筛选Tab**：
```
修改前：
- 特征筛选漏斗
- 变量IV排行
- 异常值检测明细表 ← 已移除
- 逐步回归结果
- 系数方向验证

修改后：
- 特征筛选漏斗（5阶段）
- 变量IV排行（增加淘汰阶段列）
- 逐步回归结果
- 系数方向验证
```

---

## 13. Phase 7：特征漏斗和IV排行优化（2026-02-06）

### 13.1 问题描述

1. **特征漏斗原始特征数显示错误**：显示49而非81，因为取错了字段
2. **变量IV排行缺少淘汰阶段列**：只有淘汰原因，无法区分是在哪个阶段被淘汰

### 13.2 修复内容

#### 13.2.1 原始特征数修复

| 修改前 | 修改后 |
|--------|--------|
| `dataLoadingPreview.feature_count` (49, var_filter后) | `varFilterResult.input_features` (81, var_filter前) |

**原因**：`feature_count` 是 var_filter 筛选后的特征数，真正的原始特征数应该从 `var_filter_result.input_features` 获取。

#### 13.2.2 变量IV排行增加淘汰阶段列

| 淘汰阶段 | 淘汰原因 |
|---------|---------|
| 特征筛选(IV) | IV<0.02 / IV>0.5 |
| 特征筛选(相关性) | 相关性>0.7 |
| 特征筛选(VIF) | VIF>10 |
| 模型训练(逐步回归) | P值=0.xxxx |
| 模型训练(系数验证) | 系数方向异常 |

### 13.3 修改后效果

**特征筛选漏斗**：
```
┌────────┐   ┌────────┐   ┌────────┐   ┌────────┐   ┌────────┐
│原始特征│ → │质量筛选│ → │WOE分箱 │ → │IV/相关 │ → │最终入模│
│   81   │   │   49   │   │   43   │   │   7    │   │   5    │
│  100%  │   │  60%   │   │  53%   │   │   9%   │   │   6%   │
│        │   │  -32   │   │   -6   │   │  -36   │   │   -2   │
└────────┘   └────────┘   └────────┘   └────────┘   └────────┘
```

**变量IV排行表格**：
| # | 变量 | IV值 | 预测能力 | 状态 | 淘汰阶段 | 淘汰原因 |
|---|------|------|---------|------|---------|---------|
| 1 | f73 | 0.3558 | 强 | ✓入模 | - | - |
| 2 | f74 | 0.3301 | 强 | 淘汰 | 特征筛选(相关性) | 相关性>0.7 |
| 3 | f56 | 0.1892 | 中等 | 淘汰 | 模型训练(逐步回归) | P值=0.1234 |
| ... | ... | ... | ... | ... | ... | ... |

---

## 14. Phase 8：变量筛选漏斗与IV排行全面优化（2026-02-06）

### 14.1 用户反馈的问题

| # | 问题 | 分析 |
|---|------|------|
| 1 | "特征筛选漏斗"应改为"变量筛选漏斗" | Tab名是"变量筛选"，漏斗名应一致 |
| 2 | 原始特征卡大小与其他不一致 | 布局问题，需统一卡片宽度 |
| 3 | 最终入模卡的逐步回归/系数淘汰显示0 | 数据获取逻辑错误，应从stepwise_result和coefficient_validation获取 |
| 4 | 变量IV排行只展示43个 | IV只在WOE分箱后计算，分箱失败的特征没有IV值 |
| 5 | 淘汰原因不完整 | 缺少：高同值率、高缺失率、常量/分箱失败、逐步回归、系数验证 |

### 14.2 修复内容

#### 14.2.1 漏斗标题和布局修复

| 修改项 | 修改前 | 修改后 |
|--------|--------|--------|
| 标题 | "特征筛选漏斗" | "变量筛选漏斗" |
| 卡片宽度 | `min-w-[72px]` | `min-w-[80px] w-[80px]` 固定宽度 |
| 最终入模卡removed | 错误计算 | `removedByStepwise + removedByCoef` |

#### 14.2.2 变量IV排行展示所有81个原始特征

**问题分析**：
- IV值只在WOE分箱成功后才会计算
- var_filter筛选掉的32个特征（高缺失率/高同值率）没有IV值
- WOE分箱失败的6个特征（常量列/分箱失败）也没有IV值
- 因此只有43个特征有IV值

**解决方案**：
1. 构建完整特征列表，包括有IV值和无IV值的
2. 有IV值的按IV降序排列，无IV值的排在最后
3. 无IV值的特征显示"-"，预测能力显示"未计算"

#### 14.2.3 淘汰原因完整映射

| 淘汰阶段 | 数据来源 | 淘汰原因示例 |
|---------|---------|-------------|
| 数据质量(var_filter) | `var_filter_result.removed_by_missing` | 缺失率95% |
| 数据质量(var_filter) | `var_filter_result.removed_by_identical` | 同值率98% |
| WOE分箱 | `woe_filtered.features` | 常量/分箱失败 |
| 特征筛选(IV) | `all_features_detail` | IV<0.02 |
| 特征筛选(相关性) | `all_features_detail` | 相关性>0.7 |
| 特征筛选(VIF) | `all_features_detail` | VIF>10 |
| 模型训练(逐步回归) | `stepwise_result.steps/removed_features` | P值=0.1234 |
| 模型训练(系数验证) | `coefficient_validation.invalid_direction/removed_features` | 系数方向异常 |
| 模型训练(显著性检验) | `post_validation.iterations[].removed_this_iteration` | 不显著(P值过大) |
| 模型训练(迭代验证) | `post_validation.iterations[].removed_this_iteration` | 系数方向异常 |

### 14.3 修改后效果

**变量筛选漏斗**：
```
┌────────┐   ┌────────┐   ┌────────┐   ┌────────┐   ┌────────┐
│原始特征│ > │质量筛选│ > │WOE分箱 │ > │IV/相关 │ > │最终入模│
│   81   │   │   49   │   │   43   │   │   7    │   │   5    │
│  100%  │   │  60%   │   │  53%   │   │   9%   │   │   6%   │
│        │   │  -32   │   │   -6   │   │  -36   │   │   -2   │  ← 修复：正确显示-2
│        │   │高同值率│   │常量/失败│   │IV/相关│   │逐步/系数│
└────────┘   └────────┘   └────────┘   └────────┘   └────────┘
     ↑ 所有卡片统一宽度80px
```

**变量IV排行表格**（展示全部81个特征）：
| # | 变量 | IV值 | 预测能力 | 状态 | 淘汰阶段 | 淘汰原因 |
|---|------|------|---------|------|---------|---------|
| 1 | f73 | 0.3558 | 强 | ✓入模 | - | - |
| 2 | f74 | 0.3301 | 强 | 淘汰 | 特征筛选(相关性) | 相关性>0.7 |
| ... | ... | ... | ... | ... | ... | ... |
| N | f56 | 0.xxxx | 中等 | 淘汰 | 模型训练(显著性检验) | 不显著(P值过大) |
| N | f72 | 0.xxxx | 中等 | 淘汰 | 模型训练(系数验证) | 系数方向异常 |
| ... | ... | ... | ... | ... | ... | ... |
| 44 | f12 | - | 未计算 | 淘汰 | 数据质量(var_filter) | 同值率98% |
| 45 | f23 | - | 未计算 | 淘汰 | WOE分箱 | 常量/分箱失败 |
| ... | ... | ... | ... | ... | ... | ... |
| 81 | f99 | - | 未计算 | 淘汰 | 数据质量(var_filter) | 缺失率97% |

---

## Phase 9: 修复f56淘汰原因未识别问题（2026-02-06）

### 15.1 问题分析

**场景**：7个候选入模特征 → 5个最终入模
- 模型训练阶段迭代验证显示：
  - 轮次1：7个特征 → 移除f56（原因：不显著）
  - 轮次2：6个特征 → 移除f72（原因：系数为负）
  - 轮次3：5个特征 → 全部通过

**问题**：变量IV排行中，f72正确显示淘汰阶段和原因，但f56没有正确识别。

### 15.2 根因分析

淘汰信息映射逻辑只处理了以下数据源：
1. `stepwise_result.steps` - 逐步回归移除
2. `stepwise_result.removed_features` - 逐步回归移除
3. `coefficient_validation.invalid_direction` - 系数方向异常
4. `coefficient_validation.removed_features` - 系数验证移除

**遗漏**：`post_validation.iterations`中的`removed_this_iteration`字段
- 这是迭代验证的核心数据，记录了每轮迭代移除的特征及原因
- f56被记录在iterations[0].removed_this_iteration中（原因：显著性检验不通过）

### 15.3 修复方案

在淘汰信息映射逻辑中添加第5步，处理`post_validation.iterations`：

```typescript
// ========== 5. 从post_validation迭代验证获取移除特征 ==========
const postValidation = stagesData?.model_training?.output_preview?.post_validation || {};
const iterations = postValidation.iterations || [];
iterations.forEach((iter) => {
  if (iter.removed_this_iteration?.length > 0) {
    iter.removed_this_iteration.forEach((removed) => {
      if (removed.feature) {
        const baseName = removed.feature.replace(/_woe$/, '');
        let stage = '模型训练(迭代验证)';
        let reason = removed.reason || '迭代验证移除';
        if (reason.includes('显著性') || reason.includes('不显著')) {
          stage = '模型训练(显著性检验)';
          reason = '不显著(P值过大)';
        } else if (reason.includes('系数') || reason.includes('方向') || reason.includes('负')) {
          stage = '模型训练(系数验证)';
          reason = '系数方向异常';
        }
        if (!eliminationMap[baseName] && !eliminationMap[removed.feature]) {
          eliminationMap[removed.feature] = { reason, stage };
          eliminationMap[baseName] = { reason, stage };
        }
      }
    });
  }
});
```

### 15.4 修复后预期效果

| 变量 | 淘汰阶段 | 淘汰原因 |
|------|---------|---------|
| f56 | 模型训练(显著性检验) | 不显著(P值过大) |
| f72 | 模型训练(系数验证) | 系数方向异常 |

### 15.5 涉及文件

- `ScorecardResults.tsx`: 添加第5步淘汰信息映射逻辑

---

## 16. 实现状态核实记录（2026-03-02）

### 16.1 代码库核实结果

| 功能模块 | 核实方式 | 核实结果 |
|---------|---------|---------|
| **Tab重组（8→5个）** | 搜索 `ScorecardResults.tsx` 中 Tab 定义 | ✅ 已实现：样本与数据、评估图表、变量筛选、评分卡明细、模型系数 |
| **IV排行淘汰原因** | 搜索 `VariableIVRanking` | ✅ 已实现，在代码库中找到相关实现 |
| **评分刻度参数展示** | 搜索 `ScoreScaleParams` | ✅ 已实现 |
| **特征筛选漏斗** | 搜索 `FeatureSelectionFunnel` | ✅ 已实现 |
| **PSI分布对比图** | 检查 `ScorecardResults.tsx` 图表组件 | ✅ 已实现 |
| **指标卡UI一致性** | 检查评估标签函数 | ✅ 已实现：KS/AUC/Gini/PSI均显示评估等级 |

### 16.2 核实结论

✅ **所有Phase 1-9功能均已完整实现**，包括：
- Tab精简重组（8→5个）
- 变量筛选Tab增强（IV排行+淘汰原因+漏斗）
- 评分卡明细Tab增强（评分刻度参数）
- PSI分布对比图
- 指标卡UI一致性优化
- 检查点保存results完整性修复
- 异常值展示优化
- 变量筛选漏斗与IV排行全面优化
- 迭代验证淘汰原因识别修复

**代码库验证**：所有设计的功能均已在 `ScorecardResults.tsx` 和相关后端文件中找到实现。

---

### 文档版本历史

| 版本 | 日期 | 变更内容 | 核实人 |
|------|------|---------|--------|
| v1.0-v2.0 | 2025-02-04 ~ 2026-02-04 | 基础工作阶段（optimization_plan） | 开发团队 |
| v2.1-v3.0 | 2026-02-05 ~ 2026-02-06 | Tab精简重组、IV排行增强、PSI对比图等Phase 1-9 | 开发团队 |
| v3.1 | 2026-03-02 | 添加实现状态核实记录，确认全部完成；重命名为 `scorecard_result_adjustment_design.md` | AI Assistant |
