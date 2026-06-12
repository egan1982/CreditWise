# "样本及特征" Tab 开发计划

## 目标

在规则挖掘任务的结果展示页中新增"样本及特征" Tab，汇总展示数据集和特征工程的相关结果。

## 实施状态：✅ 已完成 (2026-01-19)

---

## 数据来源

### 1. 从 `preprocessing` 阶段 output_preview 获取 ✅

| 字段 | 类型 | 说明 | 实现状态 |
|------|------|------|---------|
| `rows` | number | 总样本数 | ✅ |
| `target_rate` | number | 原始坏账率 | ✅ |
| `feature_count` | number | 特征数量 | ✅ |
| `missing_rate` | number | 平均缺失率 | ✅ |
| `missing_summary.distribution` | object | 缺失率分布 | ✅ |
| `outlier_count` | number | 异常值特征数 | ✅ |
| `auto_exclude_report` | object | 排除变量报告 | ✅ |
| `split_info` | object | 数据集划分信息（可选） | ✅ |
| `quality_score` | number | 数据质量评分 | ✅ |
| `quality_issues` | array | 数据质量问题 | ✅ |
| `derived_features` | object | 衍生特征信息 | ✅ |

### 2. 从 `feature_engineering` 阶段 output_preview 获取（如果启用）✅

| 字段 | 类型 | 说明 | 实现状态 |
|------|------|------|---------|
| `iv_distribution` | object | IV分布统计 | ✅ |
| `before_count` | number | IV筛选前特征数 | ✅ |
| `after_count` | number | IV筛选后特征数 | ✅ |
| `iv_threshold` | number | IV阈值 | ✅ |
| `removed_reasons` | object | 移除原因统计 | ✅ |

---

## UI 设计 ✅

### 已实现的展示内容

```
样本及特征
├── 样本概览
│   ├── 总样本数 ✅
│   ├── 原始坏账率 ✅
│   └── 数据集划分（训练集/测试集）✅
│
├── 特征概览
│   ├── 特征数（+衍生）✅
│   ├── 平均缺失率 ✅
│   ├── 异常值特征数 ✅
│   └── IV筛选后特征（如有）✅
│
├── 缺失率分布 ✅
│   ├── 5级分布（无缺失/0-10%/10-30%/30-50%/>50%）
│   └── 高缺失率特征列表
│
├── 排除变量 ✅
│   ├── 用户指定
│   └── 自动检测（ID/时间/样本类型/高基数）
│
├── IV分析（如有特征工程）✅
│   ├── 4级IV分布（强/中强/中/弱）
│   ├── 特征变化流程（初始→IV筛选后）
│   └── IV阈值显示
│
└── 数据质量评估 ✅
    ├── 质量评分
    └── 问题列表
```

---

## 实现步骤 ✅

### 步骤1: 添加stages数据获取 ✅

文件: `demo/chat/components/sop/RuleMiningResults.tsx`

- 新增 `stagesData` state
- 修改 `useEffect` 加载逻辑，同时获取 stages 数据
- 支持历史记录（`rec:`前缀）和实时执行两种场景

### 步骤2: 创建 SampleFeaturePanel 组件 ✅

文件: `demo/chat/components/sop/RuleMiningResults.tsx`

- 直接在文件内定义（无需独立文件）
- 从 stagesData 中提取 preprocessing 和 feature_engineering 的 output_preview
- 渲染样本概览、特征概览、缺失率分布、排除变量、IV分析等内容

### 步骤3: 集成到Tab列表 ✅

文件: `demo/chat/components/sop/RuleMiningResults.tsx`

- 在 TabsList 中添加"样本及特征" TabsTrigger
- 在 Tabs 中添加对应的 TabsContent

### 步骤4: 后端数据补充

**无需修改** - 后端 output_preview 已包含所有需要的字段

---

## 待确认事项 ✅

- [x] 是否需要支持数据集划分（train/test）的展示？→ **已支持**
- [x] IV分析是否为必须展示项？→ **条件展示**（启用特征工程时展示）
- [x] 排除变量是否需要支持展开/收起？→ **当前直接展示**，如需可后续优化
- [ ] 是否需要导出功能？→ **暂不需要**，可后续添加

---

## 优先级

**已完成** ~~中等 - 作为结果展示的增强功能，不影响核心流程。~~

---

## 相关文件

- `deepanalyze/analysis/task_SOP/rule_mining.py` - 后端数据生成
- `demo/chat/components/sop/RuleMiningResults.tsx` - **主要修改文件**
- `demo/chat/components/sop/StageOutputPreview.tsx` - 参考实现（DataLoadingPreview）
- `demo/chat/lib/sopService.ts` - API服务（getExecutionStatus, getTaskHistoryDetail）
