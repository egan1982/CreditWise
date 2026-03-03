# 规则挖掘任务功能增强优化方案

> 创建日期：2025-12-12  
> 状态：待评审  
> 优先级：P2/P3（非紧急增强）

---

## 一、背景分析

### 1.1 与评分卡开发任务对比

| 对比维度 | 评分卡开发 | 规则挖掘 |
|---------|-----------|---------|
| **核心算法** | WOE分箱 + 逻辑回归 | 决策树分箱 + 阈值规则 |
| **输出形式** | 连续得分 (0-1000) | 离散规则 (命中/未命中) |
| **分箱依赖** | scorecardpy.woebin | sklearn.DecisionTree + 自实现chi2/tree |
| **单调性要求** | WOE必须单调 | 规则方向一致性检查 |
| **精度问题** | 得分相同/聚集 (PDO参数) | 规则粒度/阈值精度 |

### 1.2 现有能力评估

#### ✅ 已具备的能力（无需优化）

| 能力 | 实现位置 | 说明 |
|-----|---------|------|
| 多种分箱方法 | `SingleVarRuleMiner._get_thresholds()` | quantile/uniform/chi2/tree 四种方法 |
| 方向一致性检查 | `SingleVarRuleMiner.filter_by_direction()` | 确保规则方向与业务预期一致 |
| 规则评估指标 | `RuleEvaluator` | recall, bad_rate, lift, hit_rate |
| 最优规则选择 | `RuleSelector` | 贪心算法选择最优规则集 |
| 二值特征检测 | `SingleVarRuleMiner.is_binary_feature()` | 自动识别One-Hot编码特征 |

#### ⚠️ 可增强的能力

| 增强项 | 当前状态 | 增强目标 |
|-------|---------|---------|
| 规则质量验证 | 无 | 添加覆盖率、冲突、重叠度检测 |
| 规则稳定性检测 | 无 | 类似PSI，检测规则时序稳定性 |
| 分箱方法说明 | 前端无提示 | 添加各方法的浮动说明 |
| 规则可解释性 | 基础 | 增强规则业务解读 |

---

## 二、优化方案清单

### 2.1 P2 优先级（建议实施）

#### 2.1.1 规则质量验证模块

**目标**：在规则生成后，自动检测规则集质量问题

**新增类**：`RuleValidator`

```python
class RuleValidator:
    """规则质量验证器"""
    
    def validate(self, rules_df: pd.DataFrame, df: pd.DataFrame, target_col: str) -> dict:
        """
        验证规则集质量
        
        Returns:
            {
                'coverage_report': {...},      # 覆盖率报告
                'conflict_report': {...},      # 冲突检测报告
                'overlap_report': {...},       # 重叠度报告
                'warnings': [...],             # 警告信息
                'quality_score': float         # 综合质量分
            }
        """
```

**检测项**：

| 检测项 | 说明 | 阈值建议 |
|-------|------|---------|
| 规则覆盖率 | 规则集总体命中样本比例 | 警告: <5% 或 >80% |
| 规则冲突 | 同一样本被互斥规则同时命中 | 警告: 冲突率 >10% |
| 规则重叠 | 规则间命中样本重叠度 | 信息: 重叠率 >50% |
| 规则冗余 | 规则A完全包含规则B | 警告: 存在冗余规则 |
| 空规则 | 规则命中样本数为0 | 错误: 自动剔除 |

**实现位置**：`rule_mining.py` 新增 `RuleValidator` 类

---

#### 2.1.2 规则稳定性检测（Rule PSI）

**目标**：检测规则在不同时间段/样本集的稳定性

**新增方法**：`RuleEvaluator.calculate_rule_psi()`

```python
def calculate_rule_psi(
    self,
    rules_df: pd.DataFrame,
    df_base: pd.DataFrame,      # 基准样本（开发样本）
    df_compare: pd.DataFrame,   # 对比样本（验证样本/新样本）
    target_col: str,
    weight_col: str
) -> pd.DataFrame:
    """
    计算规则PSI（Population Stability Index）
    
    Returns:
        DataFrame with columns: rule, hit_rate_base, hit_rate_compare, psi, stability
    """
```

**PSI阈值**：

| PSI值 | 稳定性评级 | 建议 |
|------|-----------|------|
| < 0.1 | 稳定 | 可直接使用 |
| 0.1 - 0.25 | 轻微变化 | 需关注 |
| > 0.25 | 显著变化 | 需重新评估 |

---

### 2.2 P3 优先级（可选实施）

#### 2.2.1 前端分箱方法说明

**目标**：在规则挖掘配置面板添加分箱方法的浮动说明

**修改文件**：`DynamicParamRenderer.tsx`（通用动态参数渲染器）

**UI设计**：

```tsx
// 分箱方法选择器增强
<FormControl>
  <InputLabel>分箱方法</InputLabel>
  <Select value={binMethod} onChange={...}>
    <MenuItem value="quantile">等频分箱</MenuItem>
    <MenuItem value="uniform">等宽分箱</MenuItem>
    <MenuItem value="chi2">卡方分箱</MenuItem>
    <MenuItem value="tree">决策树分箱</MenuItem>
  </Select>
  <Tooltip title={binMethodDescriptions[binMethod]}>
    <InfoIcon />
  </Tooltip>
</FormControl>
```

**说明文案**：

| 方法 | 说明 |
|-----|------|
| quantile | 等频分箱：按样本数量均分，适合分布均匀的特征 |
| uniform | 等宽分箱：按数值范围均分，适合分布均匀的特征 |
| chi2 | 卡方分箱：基于目标变量的统计显著性合并分箱，生成更有区分度的阈值 |
| tree | 决策树分箱：使用单变量决策树寻找最优分割点，生成最大化信息增益的阈值 |

---

#### 2.2.2 规则业务解读增强

**目标**：为规则生成更易理解的业务解读文本

**新增方法**：`RuleInterpreter.interpret()`

```python
class RuleInterpreter:
    """规则业务解读器"""
    
    def interpret(
        self,
        rule: str,
        var_name_dict: dict[str, str] | None = None,
        var_desc_dict: dict[str, str] | None = None
    ) -> str:
        """
        将规则转换为业务可读的解读文本
        
        Example:
            输入: "(age <= 25) & (income <= 5000)"
            输出: "年龄不超过25岁 且 收入不超过5000元的用户"
        """
```

---

#### 2.2.3 规则可视化增强

**目标**：增加规则集的可视化图表

**新增图表**：

| 图表类型 | 说明 | 状态 |
|---------|------|------|
| 规则稳定性趋势图 | 展示规则PSI随时间变化趋势 | ✅ **已完成** |
| 决策树图形可视化 | sklearn plot_tree/export_graphviz | ✅ **已完成** |
| ~~规则覆盖热力图~~ | 展示规则间的样本覆盖重叠情况 | ❌ **废弃** |
| ~~规则贡献桑基图~~ | 展示规则组合的累计召回贡献 | ❌ **废弃** |

**废弃原因**：
- **规则覆盖热力图**：与现有 `RuleValidator.overlap_report` 功能重复，表格已满足基本需求，ROI低
- **规则贡献桑基图**：与现有 `plot_cumulative_metrics()` 累计曲线功能重叠，信息冗余

**实现位置**：`rule_mining_viz.py` 新增方法
- `plot_psi_trend()` - PSI稳定性趋势图
- `get_psi_trend_data_for_frontend()` - 前端数据格式
- `plot_decision_tree()` - 决策树可视化（支持matplotlib/graphviz/plotly）
- `get_tree_structure_data()` - 决策树结构数据

---

## 三、实施计划

### 3.1 阶段划分

| 阶段 | 内容 | 预估工时 | 优先级 | 状态 |
|-----|------|---------|-------|------|
| Phase 1 | 规则质量验证模块 | 4h | P2 | ✅ **已完成** |
| Phase 2 | 规则稳定性检测 | 3h | P2 | ✅ **已完成** |
| Phase 3 | 前端分箱方法说明 | 1h | P3 | ✅ **已完成**（各选项详细说明已补充到 rule_mining_meta.py） |
| Phase 4 | 规则业务解读增强 | 2h | P3 | ✅ **已完成** |
| Phase 5 | 规则可视化增强 | 4h | P3 | ✅ **部分完成** |

**已完成说明**：
- Phase 1: `RuleValidator` 类已实现（`rule_mining.py` 第2210行），包含覆盖率、冲突、重叠、冗余检测
- Phase 2: `calculate_rule_psi` 和 `calculate_rule_psi_by_time` 方法已实现，已集成到报告生成阶段
- Phase 3: `DynamicParamRenderer.tsx` 已支持参数级别 Tooltip；各分箱方法选项的详细说明已补充到 `rule_mining_meta.py`
- Phase 4: `RuleInterpreter` 类已实现（`rule_mining.py` 第2568行），支持规则业务解读
- Phase 5: `rule_mining_viz.py` 新增 `plot_psi_trend()` 和 `plot_decision_tree()` 方法（2025-12-26）
- 前端展示：`RuleMiningResults.tsx` 包含 `ValidationReportPanel` 和 `PSIReportPanel` 组件

> **废弃说明**：热力图和桑基图因与现有功能重复、ROI低，已废弃。

### 3.2 文件修改清单

| 文件 | 修改内容 | 阶段 |
|-----|---------|-----|
| `rule_mining.py` | 新增 `RuleValidator` 类 | Phase 1 ✅ |
| `rule_mining.py` | `RuleEvaluator` 新增 `calculate_rule_psi()` | Phase 2 ✅ |
| `rule_mining.py` | 新增 `RuleInterpreter` 类 | Phase 4 ✅ |
| `rule_mining_meta.py` | 新增输出定义 `validation_report`, `psi_report` | Phase 1-2 ✅ |
| `rule_mining_viz.py` | 新增 `plot_psi_trend()`, `plot_decision_tree()` | Phase 5 ✅ |
| `DynamicParamRenderer.tsx` | 分箱方法浮动说明（替代已删除的RuleMiningConfigPanel） | Phase 3 ✅ |
| `RuleMiningResults.tsx` | 展示验证报告和PSI报告 | Phase 1-2 ✅ |

### 3.3 依赖关系

```
Phase 1 (规则质量验证)
    ↓
Phase 2 (规则稳定性检测)
    ↓
Phase 3-5 (可并行实施)
```

---

## 四、验收标准

### 4.1 Phase 1 验收标准

- [x] `RuleValidator` 类实现完成
- [x] 覆盖率检测正确计算
- [x] 冲突检测能识别互斥规则
- [x] 重叠度检测能计算规则间Jaccard相似度
- [x] 验证报告包含警告信息和质量评分
- [ ] 单元测试覆盖率 > 80%

### 4.2 Phase 2 验收标准

- [x] `calculate_rule_psi()` 方法实现完成
- [x] PSI计算公式正确
- [x] 稳定性评级正确分类
- [x] 支持多规则批量计算
- [ ] 单元测试覆盖率 > 80%

### 4.3 Phase 3-5 验收标准

- [x] 前端分箱方法说明显示正确
- [x] 规则解读文本可读性良好
- [x] PSI趋势图渲染正确（`plot_psi_trend()`）
- [x] 决策树可视化渲染正确（`plot_decision_tree()`）
- [x] 无lint错误

### 4.4 废弃功能说明

| 功能 | 废弃日期 | 废弃原因 |
|------|----------|----------|
| 规则覆盖热力图 | 2025-12-26 | 与 `RuleValidator.overlap_report` 重复 |
| 规则贡献桑基图 | 2025-12-26 | 与 `plot_cumulative_metrics()` 重复 |

---

## 五、风险评估

| 风险项 | 影响 | 缓解措施 |
|-------|------|---------|
| 规则冲突检测复杂度高 | 大规则集计算耗时 | 采用采样检测或并行计算 |
| PSI计算需要对比样本 | 用户可能无验证集 | 支持时间切分自动生成 |
| 规则解读依赖变量描述 | 无描述时解读效果差 | 提供默认模板 |

---

## 六、参考资料

- 评分卡开发任务优化方案（已实施）
- scorecardpy 分箱算法文档
- sklearn DecisionTreeClassifier 文档
- PSI计算标准公式

---

## 附录：代码示例

### A.1 RuleValidator 核心实现

```python
class RuleValidator:
    """规则质量验证器"""
    
    def __init__(
        self,
        min_coverage: float = 0.01,      # 最小覆盖率阈值
        max_coverage: float = 0.80,      # 最大覆盖率阈值
        max_conflict_rate: float = 0.10, # 最大冲突率阈值
        max_overlap_rate: float = 0.50   # 重叠度警告阈值
    ):
        self.min_coverage = min_coverage
        self.max_coverage = max_coverage
        self.max_conflict_rate = max_conflict_rate
        self.max_overlap_rate = max_overlap_rate
    
    def validate(
        self,
        rules_df: pd.DataFrame,
        df: pd.DataFrame,
        target_col: str,
        weight_col: str | None = None
    ) -> dict:
        """执行完整验证"""
        results = {
            'coverage_report': self._check_coverage(rules_df, df, weight_col),
            'conflict_report': self._check_conflicts(rules_df, df),
            'overlap_report': self._check_overlap(rules_df, df),
            'redundancy_report': self._check_redundancy(rules_df, df),
            'warnings': [],
            'quality_score': 0.0
        }
        
        # 汇总警告
        results['warnings'] = self._collect_warnings(results)
        
        # 计算综合质量分
        results['quality_score'] = self._calculate_quality_score(results)
        
        return results
    
    def _check_coverage(self, rules_df, df, weight_col):
        """检查规则覆盖率"""
        # 实现略
        pass
    
    def _check_conflicts(self, rules_df, df):
        """检查规则冲突"""
        # 实现略
        pass
    
    def _check_overlap(self, rules_df, df):
        """检查规则重叠度"""
        # 实现略
        pass
    
    def _check_redundancy(self, rules_df, df):
        """检查规则冗余"""
        # 实现略
        pass
```

### A.2 Rule PSI 计算

```python
def calculate_rule_psi(
    self,
    rules_df: pd.DataFrame,
    df_base: pd.DataFrame,
    df_compare: pd.DataFrame,
    target_col: str,
    weight_col: str | None = None
) -> pd.DataFrame:
    """计算规则PSI"""
    psi_results = []
    
    for _, row in rules_df.iterrows():
        rule = row['rule']
        
        # 计算基准样本命中率
        hit_base = df_base.eval(rule).mean()
        
        # 计算对比样本命中率
        hit_compare = df_compare.eval(rule).mean()
        
        # 计算PSI
        if hit_base > 0 and hit_compare > 0:
            psi = (hit_compare - hit_base) * np.log(hit_compare / hit_base)
        else:
            psi = np.nan
        
        # 稳定性评级
        if pd.isna(psi):
            stability = 'N/A'
        elif psi < 0.1:
            stability = '稳定'
        elif psi < 0.25:
            stability = '轻微变化'
        else:
            stability = '显著变化'
        
        psi_results.append({
            'rule': rule,
            'hit_rate_base': round(hit_base, 4),
            'hit_rate_compare': round(hit_compare, 4),
            'psi': round(psi, 4) if not pd.isna(psi) else None,
            'stability': stability
        })
    
    return pd.DataFrame(psi_results)
```
