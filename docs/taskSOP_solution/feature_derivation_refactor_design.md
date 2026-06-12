# 特征衍生阶段重构方案

> **开发评审**: 🟡 建议轻量评审 — 两个 Pipeline 阶段职责调整，实施前确认 output_preview 结构变更对前端的影响、阶段重试时缓存恢复的衍生列传递（2026-04-15 评估）

### 📌 快速回顾（开发前必读）

**作用与目标**：将规则挖掘 Pipeline 中的 datetime 衍生、text 衍生逻辑从"数据预处理"阶段移至"特征工程"阶段，符合行业标准流程。

**当前实现的问题**：
- 数据预处理阶段同时做清洗 + datetime 衍生（`_dt_` 前缀列）+ text 衍生（`_txt_` 前缀列），职责过重
- 行业惯例：预处理只做清洗和质量评估，特征衍生属于特征工程范畴

**优化内容**：
- 预处理阶段：`do_datetime=False, do_text=False`，只做清洗、检测日期/文本列并**标记**（不衍生）
- 特征工程阶段：新增 datetime/text 衍生步骤，在 One-Hot 编码和 IV 筛选之前执行
- 更新两个阶段的 output_preview 数据结构

**后端变化**：
- `rule_mining.py`：预处理阶段移除 `do_datetime=True, do_text=True`；特征工程阶段新增 `DatetimeProcessor`、`TextProcessor` 调用
- `rule_mining_meta.py`：更新两个阶段的 SOP prompt 模板描述
- `AI_analysis_prompts.py`：更新阶段摘要构建函数

**前端变化**：
- 预处理结果卡片：移除 `derived_features` 展示区块
- 特征工程结果卡片：新增 datetime/text 衍生特征展示（来源列、衍生数量、示例列名）

## 1. 背景与目标

### 1.1 当前问题

当前特征衍生逻辑分散在两个阶段，不符合行业惯例：

| 阶段 | 当前职责 | 问题 |
|------|---------|------|
| 数据预处理 | 清洗 + datetime衍生 + text衍生 + One-Hot | 衍生逻辑不应在预处理阶段 |
| 特征工程 | IV筛选 + 缺失值筛选 | 缺少衍生逻辑 |

### 1.2 行业惯例

标准机器学习流程：

```
数据预处理阶段:
├── 删除ID列、常量列、重复行
├── 特殊值替换为NaN
├── 日期列类型转换（转datetime，但不衍生）
└── 数据质量报告（缺失率、基数、类型分布）

特征工程阶段:
├── 日期时间衍生（year/month/dayofweek/hour/days_since）
├── 文本特征衍生（length/word_count）
├── 分类变量 One-Hot 编码
├── 缺失值填充/筛选
├── IV计算与筛选
└── 异常值处理（可选）
```

### 1.3 重构目标

1. 将 datetime 衍生、text 衍生、One-Hot 编码统一移至特征工程阶段
2. 数据预处理阶段只保留数据清洗和质量评估
3. 更新 output_preview 结构，确保前端展示和报告导出正确

---

## 2. 涉及文件清单

| 文件路径 | 修改内容 |
|---------|---------|
| `deepanalyze/analysis/task_SOP/rule_mining.py` | Pipeline 主逻辑调整 |
| `deepanalyze/analysis/task_SOP/rule_mining_meta.py` | SOP 元数据 prompt 模板更新 |
| `API/AI_analysis_prompts.py` | output_preview 展示模板调整 |
| `API/sop_api.py` | API 参数处理（如有） |

---

## 3. 详细修改方案

### 3.1 数据预处理阶段 (preprocessing)

#### 3.1.1 保留的功能

```python
# 保留
- 特征名映射（name_mapping）
- ID列检测与标记（不删除，标记为 exclude）
- 常量列检测与标记
- 时间列检测与标记（只标记，不衍生）
- 特殊缺失值替换（-9999, -999 等 → NaN）
- 数据质量评估（quality_assessment）
- 数据集划分（train/test split）
```

#### 3.1.2 移除的功能（移至特征工程）

```python
# 移除
- do_datetime=True  # 日期时间衍生
- do_text=True      # 文本衍生
- do_onehot=True    # One-Hot 编码（已经在特征工程）
```

#### 3.1.3 修改后的 output_preview 结构

```python
preprocessing_preview = {
    # 基础统计
    "rows": len(df_processed),
    "feature_count": len(feature_cols),  # 原始特征数（不含衍生）
    "missing_rate": overall_missing_rate,
    "target_rate": target_rate,
    
    # 特殊缺失值处理
    "special_missing_values": special_missing_stats,
    
    # 排除列信息（标记但不删除）
    "excluded_cols": {
        "id_cols": detected_id_cols,
        "time_cols": detected_time_cols,  # 只标记，不衍生
        "constant_cols": constant_cols,
        "user_exclude_cols": user_exclude_cols,
    },
    
    # 缺失率分布
    "missing_distribution": missing_distribution,
    
    # 数据集划分
    "split_info": split_info,
    
    # 异常值检测
    "outlier_count": outlier_count,
    
    # 数据质量评估
    "quality_assessment": quality_assessment,
    
    # 移除 datetime_derived、text_derived、onehot 相关字段
}
```

### 3.2 特征工程阶段 (feature_engineering)

#### 3.2.1 新增的功能

```python
# 新增（从预处理阶段移入）
- 日期时间衍生（datetime_cols → year/month/dayofweek/hour/days_since）
- 文本特征衍生（text_cols → length/word_count）
```

#### 3.2.2 保留的功能

```python
# 保留
- 分类变量 One-Hot 编码
- IV 计算
- IV 筛选（iv_threshold）
- 缺失率筛选（missing_threshold）
```

#### 3.2.3 修改后的 output_preview 结构

```python
feature_engineering_preview = {
    # 特征数量变化
    "before_count": before_feature_count,
    "after_count": after_feature_count,
    
    # 衍生特征统计（新增）
    "derived_features": {
        "datetime": {
            "source_cols": datetime_cols,          # 原始日期列
            "derived_count": len(datetime_new_cols), # 衍生特征数
            "derived_cols": datetime_new_cols[:10],  # 示例（最多10个）
            "features_extracted": ['year', 'month', 'dayofweek', 'hour', 'days_since'],
        },
        "text": {
            "source_cols": text_cols,
            "derived_count": len(text_new_cols),
            "derived_cols": text_new_cols[:10],
            "features_extracted": ['length', 'word_count'],
        },
        "onehot": {
            "source_cols": list(onehot_mapping.keys()),
            "derived_count": onehot_derived_count,
            "retained_count": retained_derived,  # IV筛选后保留数
        },
        "total_derived": datetime_count + text_count + onehot_count,
    },
    
    # IV 筛选统计
    "iv_threshold": iv_threshold,
    "iv_distribution": iv_distribution,
    
    # 移除原因统计
    "removed_reasons": {
        "缺失率筛选移除": len(dropped_missing),
        "IV筛选移除(原始特征)": iv_removed_original,
        "IV筛选移除(衍生特征)": iv_removed_derived,
    },
    
    # 新增原因统计
    "added_reasons": {
        "日期时间衍生": datetime_count,
        "文本衍生": text_count,
        "One-Hot编码": onehot_derived_count,
    },
    
    # 最终特征列表
    "selected_features": feature_cols,
    "feature_details": feature_details,
}
```

---

## 4. 代码修改详情

### 4.1 rule_mining.py - Pipeline 主逻辑

#### 4.1.1 数据预处理阶段修改

```python
# 位置：约 5724-6019 行

# 修改前：调用 preprocess() 时传入 do_datetime=True, do_text=True
df_processed, preprocess_info = preprocessor.preprocess(
    df_processed,
    target_col=target_col,
    exclude_cols=all_exclude_cols,
    do_onehot=False,  # One-Hot 在特征工程阶段
    do_datetime=True,  # ← 移除
    do_text=True,      # ← 移除
    datetime_cols=None,
    text_cols=None,
)

# 修改后：只做清洗，不衍生
df_processed, preprocess_info = preprocessor.preprocess(
    df_processed,
    target_col=target_col,
    exclude_cols=all_exclude_cols,
    do_onehot=False,
    do_datetime=False,  # 不在此阶段衍生
    do_text=False,      # 不在此阶段衍生
    datetime_cols=None,
    text_cols=None,
)

# 但需要保存检测到的 datetime_cols 和 text_cols，传递给特征工程阶段
detected_datetime_cols = preprocess_info.get('datetime_cols', [])
detected_text_cols = preprocess_info.get('text_cols', [])
```

#### 4.1.2 特征工程阶段修改

```python
# 位置：约 6038-6262 行

# 修改前：FeatureEngineer.preprocess() 只做 One-Hot + IV
df_processed, iv_table, feature_cols = self.feature_engineer.preprocess(
    df_processed, 
    target_col=target_col, 
    weight_col=weight_col,
    feature_cols=input_feature_cols,
    force_categorical=self.force_categorical,
    force_numeric=self.force_numeric
)

# 修改后：先衍生，再 One-Hot + IV

# Step 1: 日期时间衍生
from deepanalyze.analysis.preprocessing import DatetimeProcessor, TextProcessor

datetime_processor = DatetimeProcessor(indicator='_dt_')
df_processed, datetime_new_cols = datetime_processor.process(
    df_processed,
    datetime_cols=detected_datetime_cols,  # 从预处理阶段传入
    features=['year', 'month', 'dayofweek', 'hour', 'days_since'],
    exclude_cols=all_exclude_cols,
    drop_original=True
)

# Step 2: 文本衍生
text_processor = TextProcessor(indicator='_txt_')
df_processed, text_new_cols = text_processor.process(
    df_processed,
    text_cols=detected_text_cols,  # 从预处理阶段传入
    features=['length', 'word_count'],
    exclude_cols=all_exclude_cols,
    drop_original=True
)

# 更新 feature_cols（加入衍生特征）
input_feature_cols = input_feature_cols + datetime_new_cols + text_new_cols
# 移除被删除的原始日期/文本列
input_feature_cols = [c for c in input_feature_cols if c in df_processed.columns]

# Step 3: One-Hot + IV 筛选（原有逻辑）
df_processed, iv_table, feature_cols = self.feature_engineer.preprocess(
    df_processed, 
    target_col=target_col, 
    weight_col=weight_col,
    feature_cols=input_feature_cols,
    force_categorical=self.force_categorical,
    force_numeric=self.force_numeric
)
```

### 4.2 rule_mining_meta.py - SOP 元数据

```python
# 修改 PREPROCESSING_STAGE_PROMPT

# 修改前
"""
## 阶段0a：数据预处理（必需）
- 如有特征名映射文件，进行特征名映射
- 删除ID列（如fuuid、user_id等）
- 删除常量列（只有单一值的列）
- **特殊缺失值替换**：将以下特殊值视为缺失值并替换为NaN：{special_values}
- 对日期时间列进行特征提取（年、月、日、星期、小时、距今天数等，衍生列以`_dt_`标识）
- 对文本列进行特征提取（长度、词数、关键词匹配等，衍生列以`_txt_`标识）
"""

# 修改后
"""
## 阶段0a：数据预处理（必需）
- 如有特征名映射文件，进行特征名映射
- 智能检测非建模列（ID列、时间列、常量列）并标记排除
- **特殊缺失值替换**：将以下特殊值视为缺失值并替换为NaN：{special_values}
- 数据质量评估（缺失率分布、异常值检测、类型分布）
- 数据集划分（训练集/测试集）
"""

# 修改 FEATURE_ENGINEERING_STAGE_PROMPT

# 修改前
"""
## 阶段0b：特征工程（可选）
- 对分类变量进行One-Hot编码（衍生列以`_is_`标识）
- 计算各特征的IV值
- 根据IV阈值筛选特征
"""

# 修改后
"""
## 阶段0b：特征工程（可选）
- **日期时间衍生**：从日期列提取 year/month/dayofweek/hour/days_since（衍生列以`_dt_`标识）
- **文本特征衍生**：从文本列提取 length/word_count（衍生列以`_txt_`标识）
- **分类变量编码**：对分类变量进行One-Hot编码（衍生列以`_is_`标识）
- **IV计算与筛选**：计算各特征的IV值，根据阈值筛选
- **缺失率筛选**：移除高缺失率特征
"""
```

### 4.3 AI_analysis_prompts.py - 展示模板

```python
# 位置：约 760-810 行

# 修改 build_preprocessing_summary() 函数
# 移除 datetime_derived、text_derived 相关展示

# 修改 build_feature_engineering_summary() 函数（如有）
# 新增 datetime_derived、text_derived 展示

def build_feature_engineering_summary(data: dict) -> str:
    """构建特征工程阶段摘要"""
    derived = data.get("derived_features", {})
    
    derived_info = ""
    if derived.get("datetime", {}).get("derived_count", 0) > 0:
        dt = derived["datetime"]
        derived_info += f"\n  - 日期时间衍生: +{dt['derived_count']}个 (来源: {', '.join(dt['source_cols'][:3])})"
    
    if derived.get("text", {}).get("derived_count", 0) > 0:
        txt = derived["text"]
        derived_info += f"\n  - 文本衍生: +{txt['derived_count']}个 (来源: {', '.join(txt['source_cols'][:3])})"
    
    if derived.get("onehot", {}).get("derived_count", 0) > 0:
        oh = derived["onehot"]
        derived_info += f"\n  - One-Hot编码: +{oh['derived_count']}个 → 保留{oh['retained_count']}个"
    
    return derived_info
```

---

## 5. 前端影响评估

### 5.1 自动适配的部分

| 展示位置 | 数据来源 | 影响 |
|---------|---------|------|
| 阶段结果卡片 | `output_preview` | 自动适配（只要字段名不变） |
| 报告导出 | `output_preview` | 自动适配 |
| 任务结果页 | API 返回 | 自动适配 |

### 5.2 可能需要调整的部分

| 展示位置 | 当前逻辑 | 需要调整 |
|---------|---------|---------|
| 数据预处理卡片 | 展示 `derived_features` | 移除该区块 |
| 特征工程卡片 | 只展示 One-Hot | 新增 datetime/text 衍生展示 |

### 5.3 前端兼容方案

为保证向后兼容，建议：
1. 数据预处理的 `derived_features` 返回空对象 `{}`
2. 特征工程的 `derived_features` 包含完整信息
3. 前端根据 `derived_features.total_derived > 0` 判断是否展示

---

## 6. 测试要点

### 6.1 功能测试

| 测试项 | 验证点 |
|-------|-------|
| 数据预处理 | 不再产生 `_dt_`、`_txt_` 衍生列 |
| 特征工程 | 正确产生 datetime/text/onehot 衍生列 |
| 特征数量 | before_count → +衍生 → -IV筛选 → after_count |
| 报告导出 | 衍生特征信息在特征工程部分展示 |

### 6.2 边界测试

| 测试项 | 场景 |
|-------|------|
| 无日期列 | datetime_derived = 0 |
| 无文本列 | text_derived = 0 |
| 跳过特征工程 | derived_features 为空 |
| 阶段重试 | 缓存恢复后衍生逻辑正确执行 |

---

## 7. 执行计划

### Phase 1: 核心逻辑修改
- [ ] 修改 `rule_mining.py` 数据预处理阶段（移除 do_datetime/do_text）
- [ ] 修改 `rule_mining.py` 特征工程阶段（新增 datetime/text 衍生）
- [ ] 更新 output_preview 结构

### Phase 2: 元数据与模板
- [ ] 更新 `rule_mining_meta.py` SOP prompt 模板
- [ ] 更新 `AI_analysis_prompts.py` 展示模板

### Phase 3: 测试与验证
- [ ] 功能测试
- [ ] 边界测试
- [ ] 报告导出验证

### Phase 4: 前端适配（如需）
- [ ] 数据预处理卡片移除衍生区块
- [ ] 特征工程卡片新增衍生展示

---

## 8. 风险与回滚

### 8.1 风险点

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 阶段重试逻辑 | 缓存恢复时衍生列丢失 | 在 `_full_stage_data` 保存衍生列信息 |
| 前端展示错位 | 用户困惑 | 提供兼容方案 |
| 性能影响 | 特征工程阶段耗时增加 | 监控并优化 |

### 8.2 回滚方案

如出现问题，可通过以下步骤回滚：
1. 恢复 `do_datetime=True, do_text=True` 参数
2. 恢复 output_preview 原有结构
3. 恢复 SOP prompt 模板

---

## 9. 参考资料

- sklearn Pipeline 设计模式
- Kaggle 特征工程最佳实践
- 金融风控特征工厂设计

---

**文档版本**: v1.1  
**创建日期**: 2026-01-26  
**更新日期**: 2026-06-12（核实代码已实施）  
**状态**: ✅ 已实施
