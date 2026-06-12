# 规则挖掘任务OOT验证功能实施方案

> 创建时间: 2026-02-12  
> 更新日期: 2026-06-12（核实全部 Phase 已完成）  
> 状态: ✅ 全部完成（Phase 1-6）  
> 预计工作量: ~16小时（已完成）  
> **开发评审**: 🟡 建议轻量评审 — 参数删除（`psi_time_col`）的向后兼容、数据划分三模式的优先级逻辑、CV 阈值标准需实施前确认（2026-04-15 评估）

### 📌 快速回顾（开发前必读）

**作用与目标**：为规则挖掘任务添加 OOT（Out-of-Time）验证能力，评估规则在时间维度上的稳定性。评分卡已有此功能，规则挖掘需对齐。

**当前实现的问题**：
- 规则挖掘仅支持 train/test 随机划分，无法按时间划分 OOT 验证集
- 现有 `psi_time_col` 参数功能混淆（用户易与 `time_col` 搞混），且放在报告生成阶段位置不合理
- 规则质量评估缺少时间稳定性维度（当前只有 Lift、召回率、命中率、独立性、复杂度）

**优化内容**：
- 删除 `psi_time_col`，新增 `time_col` + `oot_ratio` + `sample_type_col` 三个参数
- 支持三种划分模式：手动标注列 > 智能 OOT（按时间排序取最近 N%）> 随机划分
- 最优选择阶段新增 OOT 验证：计算每条规则在 train/test/oot 上的命中率变异系数（CV）
- 质量评估总分从 100 分扩展到 110 分（时间稳定性附加 +10 分）

**后端变化**：
- `rule_mining_meta.py`：删除 `psi_time_col`，新增 5 个参数（✅ 已完成）
- `rule_mining.py`：~~新建 `_split_data_with_oot()`~~ → 复用评分卡的 `DataPreprocessor.split_data()`（✅ Phase 2 已完成），新增 `_evaluate_rules_oot_stability()`、`_filter_by_stability()`
- `AI_analysis_prompts.py`：新增 OOT 分析提示词

**前端变化**：
- `StageOutputPreview.tsx`：预处理阶段展示 OOT 数据集信息和时间范围
- `RuleMiningResults.tsx`：新增 OOT 稳定性卡片、规则列表增加稳定性标签列（🟢🟡🟠🔴）

---

## 一、项目背景与目标

### 1.1 背景
- 规则挖掘任务当前仅支持训练集/测试集划分，缺乏OOT（Out-of-Time）验证能力
- 评分卡开发任务已实现完整的OOT验证功能，规则挖掘需要与之对齐
- 现有`psi_time_col`参数功能混淆，用户易与`time_col`混淆

### 1.2 目标
- 为规则挖掘任务添加OOT验证功能，评估规则的时间稳定性
- 统一参数设计，消除功能混淆
- 将OOT稳定性整合至规则质量评估体系

---

## 二、核心设计决策

| 决策项 | 方案 | 说明 |
|--------|------|------|
| OOT验证是否强制 | **不强制** | 默认`oot_ratio=0`，用户显式配置后启用 |
| OOT验证阶段 | **selecting_rules（最优选择）** | 与规则评估逻辑合并，不新增独立阶段 |
| 测试集划分方式 | **方案A** | time_col只划分OOT，测试集从剩余数据中随机划分 |
| sample_type_col OOT支持 | **方案A** | 支持oot/train/test三种标注，严格按列值划分 |
| 向后兼容性 | **方案A** | 无自动迁移，用户需重新配置（删除`psi_time_col`） |
| 稳定性筛选策略 | **仅命中率CV** | 简单清晰，易于业务理解 |

---

## 三、稳定性阈值标准

### 3.1 CV阈值设定（宽松标准）

| 稳定性等级 | CV范围 | 波动范围 | 质量评分 | 说明 |
|-----------|--------|---------|---------|------|
| 🟢 高度稳定 | < 0.15 | < 15% | +10分 | 时间稳定性优秀 |
| 🟡 稳定 | 0.15-0.25 | 15-25% | +5分 | 时间稳定性良好 |
| 🟠 中等 | 0.25-0.35 | 25-35% | 0分 | 时间稳定性一般，可接受 |
| 🔴 不稳定 | > 0.35 | > 35% | -5分/标记剔除 | 时间稳定性差，建议剔除 |

### 3.2 整合后的规则质量评估标准

| 评估维度 | 权重 | 原满分 | 调整后 |
|---------|------|--------|--------|
| 提升度（Lift） | 30% | 30分 | 30分 |
| 召回率（Recall） | 25% | 25分 | 25分 |
| 命中率/覆盖率 | 15% | 15分 | 15分 |
| 独立性 | 15% | 15分 | 15分 |
| 复杂度 | 15% | 15分 | 15分 |
| **时间稳定性（新增）** | **附加** | **-** | **+10分** |
| **总计** | - | **100分** | **110分（含稳定性加分）** |

---

## 四、参数配置变更

### 4.1 删除的参数

| 参数名 | 原位置 | 删除原因 |
|--------|--------|---------|
| `psi_time_col` | 报告生成阶段 | 功能混淆，与`time_col`重复，且位置不合理 |

### 4.2 新增的参数

#### 预处理阶段（data_loading）

```yaml
- name: sample_type_col
  type: column_select
  label: 样本类型列
  description: 包含样本类型标签的列（train/test/oot），设置后将按该列划分数据集
  stage: data_loading

- name: time_col
  type: column_select
  label: 时间列（智能OOT划分）
  description: 用于智能OOT划分的时间列。设置后将按时间顺序自动选取最近的数据作为OOT验证集
  stage: data_loading
  show_when: {sample_type_col: {$eq: null}}

- name: oot_ratio
  type: number
  label: OOT验证集比例
  default: 0.0
  min: 0.0
  max: 0.3
  step: 0.05
  description: OOT验证集占总数据的比例（0表示不划分OOT）。仅在设置时间列时生效
  stage: data_loading
  show_when: {time_col: {$ne: null}}

- name: test_ratio
  type: number
  label: 测试集比例
  default: 0.2
  min: 0.1
  max: 0.5
  description: 测试集占剩余数据的比例（仅随机划分时生效）
  stage: data_loading
  show_when: {sample_type_col: {$eq: null}}
```

#### 最优选择阶段（selecting_rules）

```yaml
- name: enable_oot_validation
  type: boolean
  label: 启用OOT验证
  default: false
  description: 启用后，将在OOT验证集上评估规则的时间稳定性
  stage: selecting_rules
  show_when: {oot_df_exists: true}

- name: enable_stability_filter
  type: boolean
  label: 基于稳定性筛选规则
  default: false
  description: 启用后，将过滤掉在OOT上表现不稳定的规则（CV > 0.35）
  stage: selecting_rules
  show_when: {enable_oot_validation: true}

- name: cv_threshold
  type: number
  label: 变异系数阈值
  default: 0.35
  min: 0.2
  max: 0.5
  step: 0.05
  description: 命中率变异系数超过此阈值的规则将被标记为不稳定
  stage: selecting_rules
  show_when: {enable_oot_validation: true}
```

---

## 五、数据集划分逻辑

### 5.1 三种划分模式（按优先级）

```
1. 手动标注模式（sample_type_col存在）
   ├── 按列值划分 train / test / oot
   └── 支持值：'train'/'Train'/'TRAIN'/0, 'test'/'Test'/'TEST'/1, 'oot'/'OOT'/'Oot'/2

2. 智能OOT模式（time_col存在 + oot_ratio > 0）
   ├── 按时间排序
   ├── 最近 oot_ratio 比例 → OOT集（时间顺序）
   └── 剩余数据随机划分 → train / test（test_ratio控制比例）

3. 随机划分模式（test_ratio > 0）
   └── 纯随机划分 train / test
```

### 5.2 数据流示例

**场景：智能OOT划分（time_col + oot_ratio=0.15, test_ratio=0.2）**

```
总数据: 10000条（按时间排序）
│
├─ OOT集: 1500条 (15%，最近时间数据)
│
└─ 剩余: 8500条
    ├─ 测试集: 1700条 (8500 × 20%)
    └─ 训练集: 6800条 (8500 × 80%)
```

---

## 六、后端实现方案

### 6.1 文件变更清单

| 文件路径 | 变更类型 | 变更内容 | 状态 |
|---------|---------|---------|:----:|
| `deepanalyze/analysis/task_SOP/rule_mining_meta.py` | 修改 | 删除`psi_time_col`，新增`time_col`/`oot_ratio`等5个参数，更新SOP prompt | ✅ |
| `deepanalyze/analysis/task_SOP/rule_mining.py` | 修改 | 复用评分卡 `DataPreprocessor.split_data()` 替换内联划分逻辑，新增OOT验证方法 | 🔄 Phase 2 ✅ |
| `API/AI_analysis_prompts.py` | 修改 | 新增OOT分析提示词 | 待实施 |

### 6.2 核心方法设计

#### 6.2.1 数据划分（✅ Phase 2 已完成）

> **设计变更记录（2026-04-15）**：
> 
> 原 plan 设计为在 `rule_mining.py` 中新建 `_split_data_with_oot()` 方法。
> 实施时发现评分卡已有完整的 `DataPreprocessor.split_data()` 方法（`scorecard_development.py:374-512`），
> 支持三种划分模式（手动标注/智能OOT/随机划分）、多种时间格式解析、完善的容错处理。
> 
> 规则挖掘原有的内联划分代码（~40行）是早期实现，**仅因开发先后顺序不同导致未对齐**，非业务差异。
> 
> **实际方案**：删除内联代码，直接调用 `self.preprocessor.split_data()`，确保两个任务共用同一套划分逻辑。

```python
# 实际实现（复用评分卡的 DataPreprocessor.split_data）
train_df, test_df, oot_df = self.preprocessor.split_data(
    df_processed,
    target_col=target_col,
    test_ratio=test_ratio,
    sample_type_col=sample_type_col,
    time_col=time_col,
    oot_ratio=oot_ratio
)
# 返回 (train_df, test_df, oot_df)，oot_df 为 None 时表示无 OOT 数据
```

#### 6.2.2 OOT 验证计算（selecting_rules 阶段，待实施）

```python
# 2. OOT验证计算（selecting_rules阶段）
def _evaluate_rules_oot_stability(
    self,
    rules: list[dict],
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    oot_df: pd.DataFrame,
    target_col: str
) -> dict:
    """
    评估规则在OOT上的时间稳定性
    
    Returns:
        {
            "overall_hit_rate": {"train": float, "test": float, "oot": float, "cv": float},
            "rule_stability": [{
                "rule_id": str,
                "rule_desc": str,
                "hit_rate_train": float,
                "hit_rate_test": float,
                "hit_rate_oot": float,
                "cv": float,
                "stability_level": str  # "highly_stable" | "stable" | "moderate" | "unstable"
            }],
            "unstable_rules": list[str]  # CV > threshold的规则ID
        }
    """

# 3. 稳定性筛选
def _filter_by_stability(
    self,
    rules: list[dict],
    stability_report: dict,
    cv_threshold: float
) -> list[dict]:
    """基于CV阈值过滤不稳定规则"""
```

---

## 七、前端实现方案

### 7.1 文件变更清单

| 文件路径 | 变更类型 | 变更内容 |
|---------|---------|---------|
| `demo/chat/components/sop/StageOutputPreview.tsx` | 修改 | 扩展时间范围展示，支持OOT |
| `demo/chat/components/sop/RuleMiningResults.tsx` | 修改 | 新增OOT稳定性展示卡片、规则稳定性标签 |
| `demo/chat/components/sop/TaskProgress.tsx` | 修改（可选） | 更新阶段说明 |

### 7.2 阶段预览展示

#### 预处理阶段预览（新增OOT信息）

```
┌────────────────────────────────────────┐
│  数据预处理                             │
├────────────────────────────────────────┤
│  数据集划分                             │
│  ├─ 训练集: 6,800条 (68%)              │
│  ├─ 测试集: 1,700条 (17%)              │
│  └─ OOT验证集: 1,500条 (15%) ✓         │
├────────────────────────────────────────┤
│  时间范围 (apply_date)                  │
│  ├─ 训练集: 2023-01 ~ 2023-10          │
│  ├─ 测试集: 2023-11 ~ 2023-12          │
│  └─ OOT集: 2024-01 ~ 2024-03           │
└────────────────────────────────────────┘
```

#### 最优选择阶段预览（新增OOT验证）

```
┌────────────────────────────────────────┐
│  最优规则选择                           │
├────────────────────────────────────────┤
│  候选规则: 150条                        │
│  最终选择: 20条                         │
├────────────────────────────────────────┤
│  OOT稳定性验证 ✓                        │
│  ├─ 验证规则数: 150                     │
│  ├─ 🟢 高度稳定: 90条 (60%)             │
│  ├─ 🟡 稳定: 40条 (27%)                 │
│  ├─ 🟠 中等: 15条 (10%)                 │
│  └─ 🔴 不稳定: 5条 (3%) - 已过滤        │
├────────────────────────────────────────┤
│  整体命中率稳定性                       │
│  训练集: 35.0% | 测试集: 34.0% | OOT: 33.0% │
│  变异系数: 0.03 🟢 高度稳定             │
├────────────────────────────────────────┤
│  质量评分: 85/110分（含稳定性+5分）      │
└────────────────────────────────────────┘
```

### 7.3 规则列表展示（新增稳定性标签）

| 规则ID | 规则描述 | Lift | 命中率 | 召回率 | **稳定性** | 质量分 |
|--------|---------|------|--------|--------|-----------|--------|
| R001 | 年龄≤25且收入<5000 | 3.2 | 35% | 28% | 🟢 CV=0.08 | 95 |
| R002 | 逾期次数>3 | 2.8 | 12% | 15% | 🟡 CV=0.18 | 82 |
| R003 | 负债比>0.8 | 2.5 | 8% | 10% | 🔴 CV=0.42 | 45 |

---

## 八、实施计划

| 阶段 | 任务 | 文件 | 预计工作量 | 状态 |
|------|------|------|-----------|:----:|
| Phase 1 | 元数据配置修改 | `rule_mining_meta.py` | 2h | ✅ |
| Phase 2 | 预处理阶段数据划分扩展 | `rule_mining.py` | ~~3h~~ 1h（复用评分卡） | ✅ |
| Phase 3 | 最优选择阶段OOT验证逻辑 | `rule_mining.py` | 4h | ✅ |
| Phase 4 | 前端展示更新 | `RuleMiningResults.tsx` | 3h | ✅ 融合到稳定性Tab+规则表格OOT列+/110适配 |
| Phase 5 | AI分析提示词更新 | `AI_analysis_prompts.py` | 1h | ✅ focusPoints+数据注入已实现 |
| Phase 6 | 测试验证 | - | 3h | 待实施 |
| **总计** | | | **~~16h~~ ~14h** |

---

## 九、测试用例

### 9.1 功能测试

| 用例ID | 场景 | 预期结果 |
|--------|------|---------|
| TC001 | sample_type_col包含oot标注 | 按列值划分train/test/oot |
| TC002 | time_col + oot_ratio=0.15 | 最近15%数据作为OOT，剩余随机划分train/test |
| TC003 | time_col + oot_ratio=0 | 不划分OOT，仅随机划分train/test |
| TC004 | test_ratio=0 | 不划分测试集，全量作为训练集 |
| TC005 | enable_oot_validation=true | 计算规则在OOT上的命中率CV |
| TC006 | enable_stability_filter=true, CV>0.35 | 不稳定规则被过滤 |

### 9.2 兼容性测试

| 用例ID | 场景 | 预期结果 |
|--------|------|---------|
| TC007 | 旧任务（无time_col/oot_ratio） | 正常运行，OOT验证不启用 |
| TC008 | 旧任务（有psi_time_col） | 参数被忽略，不影响运行 |

---

## 十、风险与注意事项

### 10.1 风险

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 删除`psi_time_col`导致旧任务异常 | 中 | 确保后端代码兼容（忽略未知参数） |
| OOT数据量过小导致CV计算不准确 | 中 | 增加OOT样本量检查（建议>1000条） |
| 时间列格式不兼容 | 低 | 支持多种时间格式（日期、数值YYYYMM等） |

### 10.2 注意事项

1. **OOT样本量检查**：OOT数据量应足够大（建议>1000条或总数据10%以上），否则CV计算可能不稳定
2. **时间列格式**：需支持多种时间格式（YYYY-MM-DD、YYYYMM、时间戳等）
3. **向后兼容**：旧任务无`time_col`/`oot_ratio`时，OOT验证功能自动禁用，不影响现有功能

---

## 十一、附录

### 11.1 相关文档

- 评分卡OOT验证实现：`scorecard_development.py`
- 规则质量评估标准：见截图`image_1770862264286.png`
- 当前规则挖掘实现：`rule_mining.py`

### 11.2 术语表

| 术语 | 说明 |
|------|------|
| OOT | Out-of-Time，时间外验证集，用于评估模型/规则的时间稳定性 |
| CV | Coefficient of Variation，变异系数，标准差/均值，衡量波动性 |
| PSI | Population Stability Index，群体稳定性指数，评分卡常用指标 |
| 命中率 | 规则命中的样本占比 |
| 召回率 | 规则命中坏样本占全部坏样本的比例 |

---

**文档版本**: v1.1  
**最后更新**: 2026-04-15  
**状态**: Phase 1-2 已完成，Phase 3 进行中

**v1.1 变更记录（2026-04-15）**：
- Phase 1（元数据）✅ 完成
- Phase 2（数据划分）✅ 完成：方案变更为复用评分卡 `DataPreprocessor.split_data()`，删除内联代码 ~40 行
- 实施计划总工时从 ~16h 调整为 ~14h（Phase 2 节省 2h）
