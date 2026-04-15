# 先验规则分析增强方案设计

> **文档版本**: v1.0  
> **创建日期**: 2026-01-12  
> **状态**: 待开发  
> **优先级**: P2  
> **开发评审**: 🔴 建议正式评审（plan review） — 1640 行设计文档，涉及文件上传/解析/校验/前端多组件，建议评审中确认实施范围和分期策略（2026-04-15 评估）

### 📌 快速回顾（开发前必读）

**作用与目标**：增强规则挖掘任务的"先验规则"输入能力。当前用户只能在 textarea 中手写 Python 表达式（如 `(age > 30)`），本方案支持**文件上传、结构化录入、阈值对比**三种方式。

**当前实现的问题**：
- 先验规则只能手动在 textarea 输入 Python 表达式，学习成本高
- 规则多时手动输入繁琐，无批量导入能力
- 无法与新挖掘规则做阈值对比（如"同一特征旧规则 age>30，新规则建议 age>25"）
- 无规则校验（运行时才报错）、无规则复用

**优化内容**：
- 支持 CSV 文件上传先验规则（两种格式：结构化格式 + 表达式格式）
- 上传后立即校验列名是否存在于数据集中
- 新增阈值对比分析：自动检测同特征规则的阈值变化
- 保留现有 textarea 输入方式（向后兼容）

**后端变化**：
- 新增规则文件解析模块（CSV 解析、格式校验、列名匹配）
- `rule_mining.py`：报告生成阶段新增先验规则对比分析

**前端变化**：
- 参数面板：先验规则区域新增"上传文件"按钮 + 文件预览 + 校验结果展示
- 结果页面：新增先验规则对比 Tab（旧规则 vs 新规则阈值对比表）

---

## 一、需求背景与问题分析

### 1.1 当前实现

当前项目的先验规则参数设计：

```python
{
    "name": "prior_rules",
    "type": "textarea",
    "label": "先验规则（可选）",
    "default": "",
    "description": "已有的生产规则列表，每行一条规则表达式",
    "placeholder": "例如：\n(age > 30)\n(income < 5000)",
    "stage": "report_generation",
    "advanced": True
}
```

**录入方式**：手动在 textarea 中输入 Python 表达式，每行一条规则。

### 1.2 当前方案的问题

| 问题 | 影响 |
|------|------|
| **学习成本高** | 用户需了解 Python 表达式语法 |
| **批量操作不便** | 规则多时手动输入繁琐 |
| **无规则复用** | 无法保存、共享、版本管理 |
| **无预校验** | 运行时才报错，体验差 |
| **无阈值对比** | 无法检测同特征规则的阈值调整 |
| **无历史追溯** | 规则变更无记录 |

### 1.3 行业惯用方案对比

| 方案 | 优点 | 缺点 | 行业采用度 |
|------|------|------|-----------|
| **A. 新上传规则文件** | 格式灵活、规则独立管理、版本可追溯 | 需要额外上传步骤 | ⭐⭐⭐⭐⭐ 最常用 |
| **B. 样本数据集增加标记列** | 无需额外文件、规则与数据绑定 | 规则表达受限、耦合度高 | ⭐⭐ 少用 |
| **C. 配置界面手动录入** | 直观、无需文件 | 规则多时繁琐 | ⭐⭐⭐ 中等 |

---

## 二、方案设计

### 2.1 设计目标

1. **多入口支持**：手动输入 / 文件上传 / 历史任务导入
2. **结构化与表达式双模式**：简单规则结构化录入，复杂规则表达式录入
3. **预校验**：上传后立即校验列名是否存在
4. **阈值调整检测**：对比同特征规则的阈值变化
5. **向后兼容**：保留现有 textarea 输入方式

### 2.2 CSV文件格式设计

#### 2.2.1 双模式CSV

**模式1：结构化格式（简单规则，支持阈值对比）**

```csv
rule_id,rule_name,feature,operator,threshold,direction
R001,高风险年龄,age,>=,60,reject
R002,低收入拒绝,income,<,3000,reject
R003,高负债率,debt_ratio,>=,0.7,reject
R004,多头借贷,loan_count,>,5,reject
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `rule_id` | string | ✅ | 规则唯一标识 |
| `rule_name` | string | ✅ | 规则名称/描述 |
| `feature` | string | ✅ | 特征名（需与样本数据列名匹配） |
| `operator` | string | ✅ | 比较运算符：`>`, `>=`, `<`, `<=`, `==`, `!=`, `in`, `between` |
| `threshold` | string | ✅ | 阈值（单值、列表或范围） |
| `direction` | string | 可选 | 规则方向：`reject`/`approve`，默认 `reject` |

**模式2：表达式格式（复杂规则）**

```csv
rule_id,rule_name,expression
R001,高风险年龄,(age >= 60)
R002,低收入拒绝,(income < 3000)
R003,高负债且多头,(debt_ratio >= 0.7) & (loan_count > 5)
R004,年轻或低信用,(age < 25) | (credit_score < 550)
R005,复杂组合规则,(age > 30) & ((income < 5000) | (debt_ratio > 0.6))
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `rule_id` | string | ✅ | 规则唯一标识 |
| `rule_name` | string | ✅ | 规则名称/描述 |
| `expression` | string | ✅ | Python 表达式，支持 `&`, `|`, 括号嵌套 |

#### 2.2.2 格式自动识别

系统根据CSV列结构自动识别模式：
- 包含 `feature`, `operator`, `threshold` 列 → 结构化模式
- 包含 `expression` 列 → 表达式模式
- 两者都有 → 混合模式（按行判断）

### 2.3 运算符支持

| 运算符 | 说明 | 示例 |
|--------|------|------|
| `>` | 大于 | `age > 30` |
| `>=` | 大于等于 | `age >= 30` |
| `<` | 小于 | `income < 5000` |
| `<=` | 小于等于 | `income <= 5000` |
| `==` | 等于 | `gender == 'M'` |
| `!=` | 不等于 | `status != 'active'` |
| `in` | 在列表中 | `city in ['北京','上海']` |
| `not in` | 不在列表中 | `city not in ['北京']` |
| `between` | 在范围内 | `age between [25,35]` |

### 2.4 复杂规则支持

#### 方案A：规则组扩展（可选）

```csv
rule_id,rule_name,feature,operator,threshold,logic_group,group_operator
R003,高负债且多头,debt_ratio,>=,0.7,G1,AND
R004,高负债且多头,loan_count,>,5,G1,AND
R005,年轻或低信用,age,<,25,G2,OR
R006,年轻或低信用,credit_score,<,550,G2,OR
```

| 字段 | 说明 |
|------|------|
| `logic_group` | 规则组ID，同组规则组合 |
| `group_operator` | 组内逻辑：`AND`（&）或 `OR`（\|） |

**生成的表达式**：
- G1: `(debt_ratio >= 0.7) & (loan_count > 5)`
- G2: `(age < 25) | (credit_score < 550)`

#### 方案B：直接使用表达式列（推荐）

对于复杂规则，直接使用 `expression` 列录入完整表达式，无需额外设计。

---

## 三、核心模块设计

### 3.1 模块架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     Prior Rules Enhancement                      │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  PriorRuleParser │  │ RuleValidator   │  │ ThresholdComparator│
│  │  ───────────────│  │ ───────────────│  │ ─────────────────│  │
│  │  - parse_csv()  │  │ - validate()    │  │ - compare()      │  │
│  │  - to_expression│  │ - check_columns │  │ - detect_changes │  │
│  │  - auto_detect  │  │ - syntax_check  │  │ - generate_report│  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
│           │                    │                    │            │
│           └────────────────────┼────────────────────┘            │
│                                ▼                                 │
│                    ┌─────────────────────┐                       │
│                    │ PriorRuleManager    │                       │
│                    │ ─────────────────── │                       │
│                    │ - load()            │                       │
│                    │ - validate()        │                       │
│                    │ - get_expressions() │                       │
│                    │ - compare_with()    │                       │
│                    └─────────────────────┘                       │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 PriorRuleParser（CSV解析器 + 表达式生成器）

```python
# deepanalyze/analysis/task_SOP/prior_rule_parser.py

from typing import Any
import pandas as pd
import re


class PriorRuleParser:
    """
    先验规则解析器
    
    支持两种CSV格式：
    1. 结构化格式：feature, operator, threshold
    2. 表达式格式：expression
    
    自动识别格式并转换为统一的规则表达式。
    """
    
    # 支持的运算符映射
    OPERATOR_MAP = {
        '>': '>',
        '>=': '>=',
        '<': '<',
        '<=': '<=',
        '==': '==',
        '!=': '!=',
        'in': 'in',
        'not in': 'not in',
        'between': 'between'
    }
    
    def __init__(self):
        self.rules: list[dict] = []
        self.mode: str = 'unknown'  # 'structured', 'expression', 'mixed'
        self.errors: list[str] = []
        self.warnings: list[str] = []
    
    def parse_csv(self, file_path: str) -> "PriorRuleParser":
        """
        解析CSV文件
        
        Args:
            file_path: CSV文件路径
            
        Returns:
            self for chaining
        """
        try:
            df = pd.read_csv(file_path, encoding='utf-8')
        except UnicodeDecodeError:
            df = pd.read_csv(file_path, encoding='gbk')
        
        return self.parse_dataframe(df)
    
    def parse_dataframe(self, df: pd.DataFrame) -> "PriorRuleParser":
        """
        解析DataFrame
        
        Args:
            df: 规则DataFrame
            
        Returns:
            self for chaining
        """
        self.rules = []
        self.errors = []
        self.warnings = []
        
        # 自动检测模式
        self.mode = self._detect_mode(df)
        
        for idx, row in df.iterrows():
            try:
                rule = self._parse_row(row, idx)
                if rule:
                    self.rules.append(rule)
            except Exception as e:
                self.errors.append(f"Row {idx + 2}: {str(e)}")
        
        return self
    
    def parse_text(self, text: str) -> "PriorRuleParser":
        """
        解析文本（兼容现有textarea输入）
        
        Args:
            text: 每行一条规则的文本
            
        Returns:
            self for chaining
        """
        self.rules = []
        self.errors = []
        self.warnings = []
        self.mode = 'expression'
        
        lines = text.strip().split('\n')
        for idx, line in enumerate(lines):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            self.rules.append({
                'rule_id': f'R{idx + 1:03d}',
                'rule_name': f'规则{idx + 1}',
                'expression': line,
                'source': 'text',
                'mode': 'expression'
            })
        
        return self
    
    def _detect_mode(self, df: pd.DataFrame) -> str:
        """检测CSV格式模式"""
        cols = set(df.columns.str.lower())
        
        has_structured = {'feature', 'operator', 'threshold'}.issubset(cols)
        has_expression = 'expression' in cols
        
        if has_structured and has_expression:
            return 'mixed'
        elif has_structured:
            return 'structured'
        elif has_expression:
            return 'expression'
        else:
            raise ValueError(
                "CSV格式无效：需要包含 (feature, operator, threshold) 或 (expression) 列"
            )
    
    def _parse_row(self, row: pd.Series, idx: int) -> dict | None:
        """解析单行规则"""
        rule_id = row.get('rule_id', f'R{idx + 1:03d}')
        rule_name = row.get('rule_name', f'规则{idx + 1}')
        
        # 优先使用expression列
        if 'expression' in row and pd.notna(row['expression']):
            expr = str(row['expression']).strip()
            if expr:
                return {
                    'rule_id': rule_id,
                    'rule_name': rule_name,
                    'expression': expr,
                    'source': 'csv',
                    'mode': 'expression'
                }
        
        # 使用结构化列
        if all(col in row for col in ['feature', 'operator', 'threshold']):
            feature = str(row['feature']).strip()
            operator = str(row['operator']).strip()
            threshold = row['threshold']
            
            if not feature or pd.isna(feature):
                return None
            
            expr = self._build_expression(feature, operator, threshold)
            
            return {
                'rule_id': rule_id,
                'rule_name': rule_name,
                'expression': expr,
                'feature': feature,
                'operator': operator,
                'threshold': threshold,
                'direction': row.get('direction', 'reject'),
                'source': 'csv',
                'mode': 'structured'
            }
        
        return None
    
    def _build_expression(self, feature: str, operator: str, threshold: Any) -> str:
        """
        构建规则表达式
        
        Args:
            feature: 特征名
            operator: 运算符
            threshold: 阈值
            
        Returns:
            Python表达式字符串
        """
        op = operator.strip().lower()
        
        if op == 'between':
            # threshold 应为 [min, max] 格式
            if isinstance(threshold, str):
                threshold = eval(threshold)
            return f"({feature} >= {threshold[0]}) & ({feature} <= {threshold[1]})"
        
        elif op == 'in':
            if isinstance(threshold, str) and not threshold.startswith('['):
                threshold = f"[{threshold}]"
            return f"({feature}.isin({threshold}))"
        
        elif op == 'not in':
            if isinstance(threshold, str) and not threshold.startswith('['):
                threshold = f"[{threshold}]"
            return f"(~{feature}.isin({threshold}))"
        
        else:
            # 数值或字符串阈值
            if isinstance(threshold, str):
                try:
                    threshold = float(threshold)
                except ValueError:
                    threshold = f"'{threshold}'"
            
            return f"({feature} {operator} {threshold})"
    
    def get_expressions(self) -> list[str]:
        """获取所有规则表达式列表"""
        return [r['expression'] for r in self.rules]
    
    def get_rules_df(self) -> pd.DataFrame:
        """获取规则DataFrame"""
        return pd.DataFrame(self.rules)
    
    def get_structured_rules(self) -> list[dict]:
        """获取结构化规则（用于阈值对比）"""
        return [r for r in self.rules if r.get('mode') == 'structured']
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'mode': self.mode,
            'rules': self.rules,
            'rule_count': len(self.rules),
            'errors': self.errors,
            'warnings': self.warnings
        }
```

### 3.3 RuleValidator（规则预校验器）

```python
# deepanalyze/analysis/task_SOP/prior_rule_validator.py

import pandas as pd
import re
from typing import Any


class RuleValidator:
    """
    规则预校验器
    
    功能：
    1. 校验规则表达式语法
    2. 校验特征名是否存在于数据集
    3. 校验阈值类型是否匹配
    """
    
    def __init__(self, df: pd.DataFrame | None = None):
        """
        初始化校验器
        
        Args:
            df: 样本数据集（用于校验列名）
        """
        self.df = df
        self.available_columns = set(df.columns) if df is not None else set()
        self.column_types = {}
        
        if df is not None:
            for col in df.columns:
                self.column_types[col] = str(df[col].dtype)
    
    def validate_rules(self, rules: list[dict]) -> dict:
        """
        批量校验规则
        
        Args:
            rules: 规则列表
            
        Returns:
            校验结果
        """
        results = []
        valid_count = 0
        invalid_count = 0
        
        for rule in rules:
            result = self.validate_rule(rule)
            results.append(result)
            
            if result['valid']:
                valid_count += 1
            else:
                invalid_count += 1
        
        return {
            'total': len(rules),
            'valid': valid_count,
            'invalid': invalid_count,
            'results': results
        }
    
    def validate_rule(self, rule: dict) -> dict:
        """
        校验单条规则
        
        Args:
            rule: 规则字典
            
        Returns:
            校验结果
        """
        errors = []
        warnings = []
        
        expression = rule.get('expression', '')
        
        # 1. 语法校验
        syntax_result = self._check_syntax(expression)
        if not syntax_result['valid']:
            errors.append(syntax_result['error'])
        
        # 2. 列名校验
        if self.available_columns:
            column_result = self._check_columns(expression)
            errors.extend(column_result['errors'])
            warnings.extend(column_result['warnings'])
        
        # 3. 结构化规则的额外校验
        if rule.get('mode') == 'structured':
            type_result = self._check_threshold_type(rule)
            warnings.extend(type_result.get('warnings', []))
        
        return {
            'rule_id': rule.get('rule_id'),
            'rule_name': rule.get('rule_name'),
            'expression': expression,
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def _check_syntax(self, expression: str) -> dict:
        """检查表达式语法"""
        try:
            # 尝试编译表达式（不执行）
            compile(expression, '<string>', 'eval')
            return {'valid': True}
        except SyntaxError as e:
            return {'valid': False, 'error': f"语法错误: {str(e)}"}
    
    def _check_columns(self, expression: str) -> dict:
        """检查表达式中的列名是否存在"""
        errors = []
        warnings = []
        
        # 提取表达式中的标识符（可能是列名）
        # 排除 Python 关键字和常见函数
        keywords = {'and', 'or', 'not', 'in', 'True', 'False', 'None', 'isin'}
        
        identifiers = set(re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', expression))
        identifiers -= keywords
        
        for ident in identifiers:
            if ident not in self.available_columns:
                # 可能是方法名或其他，给警告而非错误
                if not ident.startswith('_'):
                    errors.append(f"列 '{ident}' 不存在于数据集中")
        
        return {'errors': errors, 'warnings': warnings}
    
    def _check_threshold_type(self, rule: dict) -> dict:
        """检查阈值类型是否匹配列类型"""
        warnings = []
        
        feature = rule.get('feature')
        threshold = rule.get('threshold')
        
        if feature and feature in self.column_types:
            col_type = self.column_types[feature]
            
            # 简单类型检查
            if 'int' in col_type or 'float' in col_type:
                try:
                    float(threshold)
                except (ValueError, TypeError):
                    warnings.append(
                        f"列 '{feature}' 是数值类型，但阈值 '{threshold}' 不是数值"
                    )
        
        return {'warnings': warnings}
    
    def set_dataframe(self, df: pd.DataFrame) -> "RuleValidator":
        """设置数据集"""
        self.df = df
        self.available_columns = set(df.columns)
        self.column_types = {col: str(df[col].dtype) for col in df.columns}
        return self
```

### 3.4 ThresholdComparator（阈值调整检测器）

```python
# deepanalyze/analysis/task_SOP/threshold_comparator.py

import pandas as pd
import re
from typing import Any


class ThresholdComparator:
    """
    阈值调整检测器
    
    对比先验规则与挖掘规则，检测：
    1. 完全新增的规则
    2. 阈值调整的规则
    3. 方向调整的规则
    4. 保留的规则
    5. 建议移除的规则
    """
    
    def __init__(self):
        self.prior_rules: list[dict] = []
        self.mined_rules: list[dict] = []
    
    def compare(
        self,
        prior_rules: list[dict],
        mined_rules: pd.DataFrame,
        metrics_df: pd.DataFrame | None = None
    ) -> dict:
        """
        对比先验规则与挖掘规则
        
        Args:
            prior_rules: 先验规则列表（来自PriorRuleParser）
            mined_rules: 挖掘出的规则DataFrame
            metrics_df: 规则效果指标DataFrame（可选）
            
        Returns:
            对比结果
        """
        self.prior_rules = prior_rules
        
        # 解析挖掘规则
        self.mined_rules = self._parse_mined_rules(mined_rules)
        
        # 构建先验规则索引（按特征名）
        prior_by_feature = {}
        for rule in prior_rules:
            if rule.get('mode') == 'structured':
                feature = rule.get('feature')
                if feature:
                    if feature not in prior_by_feature:
                        prior_by_feature[feature] = []
                    prior_by_feature[feature].append(rule)
        
        # 分类结果
        results = {
            'new_rules': [],           # 完全新增
            'threshold_adjusted': [],   # 阈值调整
            'direction_adjusted': [],   # 方向调整
            'retained': [],             # 保留
            'deprecated': [],           # 建议移除
            'unparseable': []           # 无法解析（复杂规则）
        }
        
        matched_prior_ids = set()
        
        # 遍历挖掘规则
        for mined in self.mined_rules:
            feature = mined.get('feature')
            
            if not feature:
                # 无法解析特征的规则
                results['unparseable'].append(mined)
                continue
            
            if feature not in prior_by_feature:
                # 完全新增
                results['new_rules'].append(mined)
            else:
                # 找到同特征的先验规则
                prior = prior_by_feature[feature][0]  # 取第一个
                matched_prior_ids.add(prior.get('rule_id'))
                
                # 对比阈值
                comparison = self._compare_threshold(prior, mined)
                
                if comparison['type'] == 'same':
                    results['retained'].append({
                        **mined,
                        'prior_rule': prior
                    })
                elif comparison['type'] == 'threshold_changed':
                    results['threshold_adjusted'].append({
                        **mined,
                        'prior_rule': prior,
                        'prior_threshold': comparison['prior_threshold'],
                        'new_threshold': comparison['new_threshold'],
                        'threshold_change': comparison['change'],
                        'change_direction': comparison['direction']
                    })
                elif comparison['type'] == 'operator_changed':
                    results['direction_adjusted'].append({
                        **mined,
                        'prior_rule': prior,
                        'prior_operator': comparison['prior_operator'],
                        'new_operator': comparison['new_operator']
                    })
        
        # 检测未匹配的先验规则（可能需要移除）
        for rule in prior_rules:
            if rule.get('rule_id') not in matched_prior_ids:
                if rule.get('mode') == 'structured':
                    results['deprecated'].append({
                        **rule,
                        'reason': '未在挖掘结果中出现'
                    })
        
        # 生成摘要
        summary = {
            'prior_count': len(prior_rules),
            'mined_count': len(self.mined_rules),
            'new_count': len(results['new_rules']),
            'threshold_adjusted_count': len(results['threshold_adjusted']),
            'direction_adjusted_count': len(results['direction_adjusted']),
            'retained_count': len(results['retained']),
            'deprecated_count': len(results['deprecated']),
            'unparseable_count': len(results['unparseable'])
        }
        
        return {
            'summary': summary,
            'details': results
        }
    
    def _parse_mined_rules(self, mined_df: pd.DataFrame) -> list[dict]:
        """解析挖掘规则，提取特征和阈值"""
        results = []
        
        for _, row in mined_df.iterrows():
            rule_expr = row.get('rule', '')
            parsed = self._parse_expression(rule_expr)
            
            results.append({
                'rule': rule_expr,
                'feature': parsed.get('feature'),
                'operator': parsed.get('operator'),
                'threshold': parsed.get('threshold'),
                'parsed': parsed.get('success', False),
                # 保留原始指标
                **{k: v for k, v in row.items() if k != 'rule'}
            })
        
        return results
    
    def _parse_expression(self, expression: str) -> dict:
        """
        解析规则表达式，提取特征、运算符、阈值
        
        支持格式：
        - (feature > 10)
        - (feature >= 10.5)
        - feature < 100
        """
        # 简单规则模式
        pattern = r'\(?\s*(\w+)\s*(>=|<=|>|<|==|!=)\s*([\d.]+)\s*\)?'
        match = re.match(pattern, expression.strip())
        
        if match:
            return {
                'success': True,
                'feature': match.group(1),
                'operator': match.group(2),
                'threshold': float(match.group(3))
            }
        
        return {'success': False}
    
    def _compare_threshold(self, prior: dict, mined: dict) -> dict:
        """对比两条规则的阈值"""
        prior_op = prior.get('operator', '')
        mined_op = mined.get('operator', '')
        prior_th = prior.get('threshold')
        mined_th = mined.get('threshold')
        
        # 标准化阈值为数值
        try:
            prior_th = float(prior_th) if prior_th else None
            mined_th = float(mined_th) if mined_th else None
        except (ValueError, TypeError):
            pass
        
        # 运算符变化
        if prior_op != mined_op:
            return {
                'type': 'operator_changed',
                'prior_operator': prior_op,
                'new_operator': mined_op
            }
        
        # 阈值变化
        if prior_th != mined_th:
            change = None
            direction = None
            
            if isinstance(prior_th, (int, float)) and isinstance(mined_th, (int, float)):
                change = mined_th - prior_th
                direction = 'increased' if change > 0 else 'decreased'
            
            return {
                'type': 'threshold_changed',
                'prior_threshold': prior_th,
                'new_threshold': mined_th,
                'change': change,
                'direction': direction
            }
        
        return {'type': 'same'}
    
    def generate_report(self, comparison_result: dict) -> str:
        """生成对比报告文本"""
        summary = comparison_result['summary']
        details = comparison_result['details']
        
        lines = [
            "=" * 60,
            "先验规则对比分析报告",
            "=" * 60,
            "",
            "📊 总览",
            f"  - 先验规则数: {summary['prior_count']}",
            f"  - 挖掘规则数: {summary['mined_count']}",
            f"  - 完全新增: {summary['new_count']}",
            f"  - 阈值调整: {summary['threshold_adjusted_count']}",
            f"  - 方向调整: {summary['direction_adjusted_count']}",
            f"  - 保留: {summary['retained_count']}",
            f"  - 建议移除: {summary['deprecated_count']}",
            ""
        ]
        
        # 新增规则
        if details['new_rules']:
            lines.append("🆕 完全新增规则")
            lines.append("-" * 40)
            for rule in details['new_rules']:
                lines.append(f"  {rule['rule']}")
            lines.append("")
        
        # 阈值调整
        if details['threshold_adjusted']:
            lines.append("🔄 阈值调整规则")
            lines.append("-" * 40)
            for rule in details['threshold_adjusted']:
                lines.append(
                    f"  {rule['feature']}: "
                    f"{rule['prior_threshold']} → {rule['new_threshold']} "
                    f"({rule['change_direction']})"
                )
            lines.append("")
        
        # 建议移除
        if details['deprecated']:
            lines.append("⚠️ 建议移除规则")
            lines.append("-" * 40)
            for rule in details['deprecated']:
                lines.append(f"  {rule['expression']} ({rule['reason']})")
            lines.append("")
        
        return "\n".join(lines)
```

### 3.5 PriorRuleManager（统一管理器）

```python
# deepanalyze/analysis/task_SOP/prior_rule_manager.py

import pandas as pd
from typing import Any
from .prior_rule_parser import PriorRuleParser
from .prior_rule_validator import RuleValidator
from .threshold_comparator import ThresholdComparator


class PriorRuleManager:
    """
    先验规则统一管理器
    
    整合解析、校验、对比功能，提供统一接口。
    """
    
    def __init__(self):
        self.parser = PriorRuleParser()
        self.validator = RuleValidator()
        self.comparator = ThresholdComparator()
        
        self._rules: list[dict] = []
        self._validation_result: dict | None = None
    
    def load_from_csv(self, file_path: str) -> "PriorRuleManager":
        """从CSV文件加载规则"""
        self.parser.parse_csv(file_path)
        self._rules = self.parser.rules
        return self
    
    def load_from_text(self, text: str) -> "PriorRuleManager":
        """从文本加载规则（兼容现有textarea）"""
        self.parser.parse_text(text)
        self._rules = self.parser.rules
        return self
    
    def load_from_dataframe(self, df: pd.DataFrame) -> "PriorRuleManager":
        """从DataFrame加载规则"""
        self.parser.parse_dataframe(df)
        self._rules = self.parser.rules
        return self
    
    def validate(self, sample_df: pd.DataFrame | None = None) -> dict:
        """
        校验规则
        
        Args:
            sample_df: 样本数据集（用于校验列名）
            
        Returns:
            校验结果
        """
        if sample_df is not None:
            self.validator.set_dataframe(sample_df)
        
        self._validation_result = self.validator.validate_rules(self._rules)
        return self._validation_result
    
    def get_expressions(self) -> list[str]:
        """获取规则表达式列表（用于传递给现有分析器）"""
        return [r['expression'] for r in self._rules]
    
    def get_valid_expressions(self) -> list[str]:
        """获取校验通过的规则表达式"""
        if not self._validation_result:
            return self.get_expressions()
        
        valid_ids = {
            r['rule_id'] 
            for r in self._validation_result['results'] 
            if r['valid']
        }
        
        return [
            r['expression'] 
            for r in self._rules 
            if r.get('rule_id') in valid_ids
        ]
    
    def compare_with_mined(
        self,
        mined_rules_df: pd.DataFrame,
        metrics_df: pd.DataFrame | None = None
    ) -> dict:
        """
        与挖掘规则对比
        
        Args:
            mined_rules_df: 挖掘出的规则DataFrame
            metrics_df: 规则效果指标（可选）
            
        Returns:
            对比结果
        """
        return self.comparator.compare(
            self._rules,
            mined_rules_df,
            metrics_df
        )
    
    def get_comparison_report(self, comparison_result: dict) -> str:
        """生成对比报告"""
        return self.comparator.generate_report(comparison_result)
    
    def get_summary(self) -> dict:
        """获取摘要信息"""
        return {
            'mode': self.parser.mode,
            'rule_count': len(self._rules),
            'structured_count': len([r for r in self._rules if r.get('mode') == 'structured']),
            'expression_count': len([r for r in self._rules if r.get('mode') == 'expression']),
            'parse_errors': self.parser.errors,
            'parse_warnings': self.parser.warnings,
            'validation': self._validation_result
        }
    
    def to_dict(self) -> dict:
        """转换为完整字典"""
        return {
            'rules': self._rules,
            'expressions': self.get_expressions(),
            'summary': self.get_summary()
        }
```

---

## 四、前端UI设计

### 4.1 组件结构

```
┌─────────────────────────────────────────────────────────────────┐
│                     PriorRulesInput                              │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  InputModeTab   │  │ FileUploader    │  │ HistoryImporter │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
│           │                    │                    │            │
│           └────────────────────┼────────────────────┘            │
│                                ▼                                 │
│                    ┌─────────────────────┐                       │
│                    │ RulePreviewList     │                       │
│                    └─────────────────────┘                       │
│                                │                                 │
│                                ▼                                 │
│                    ┌─────────────────────┐                       │
│                    │ ValidationStatus    │                       │
│                    └─────────────────────┘                       │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 UI原型

```
┌─────────────────────────────────────────────────────────────────┐
│ 先验规则（可选）                                        [?]     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐         │
│  │ ○ 手动输入   │ │ ● 上传文件   │ │ ○ 从历史任务导入 │         │
│  └──────────────┘ └──────────────┘ └──────────────────┘         │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  📁 拖拽文件到此处，或 [选择文件]                        │   │
│  │                                                         │   │
│  │  支持格式: CSV, Excel (.xlsx)                           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  [下载模板 ▼]                                                   │
│  ├─ 简单规则模板 (结构化)                                       │
│  └─ 复杂规则模板 (表达式)                                       │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ✅ 已解析 5 条规则 (3 结构化, 2 表达式)                        │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ ✓ R001  高风险年龄      age >= 60           [结构化]    │   │
│  │ ✓ R002  低收入拒绝      income < 3000       [结构化]    │   │
│  │ ✓ R003  高负债率        debt_ratio >= 0.7   [结构化]    │   │
│  │ ✓ R004  高负债且多头    (debt_ratio>=0.7)   [表达式]    │   │
│  │                         & (loan_count>5)                │   │
│  │ ✗ R005  未知规则        unknown_col > 5     [错误]      │   │
│  │         ⚠️ 列 'unknown_col' 不存在于数据集中             │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ☑ 启用阈值调整检测（仅对结构化规则生效）                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.3 组件代码框架

```tsx
// demo/chat/components/sop/PriorRulesInput.tsx

import React, { useState, useCallback } from 'react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Upload, Download, FileText, AlertCircle, CheckCircle } from 'lucide-react';

interface PriorRule {
  rule_id: string;
  rule_name: string;
  expression: string;
  feature?: string;
  operator?: string;
  threshold?: string | number;
  mode: 'structured' | 'expression';
  valid?: boolean;
  errors?: string[];
}

interface PriorRulesInputProps {
  value: string;
  onChange: (value: string, rules?: PriorRule[]) => void;
  availableColumns?: string[];
  disabled?: boolean;
  enableThresholdComparison?: boolean;
  onThresholdComparisonChange?: (enabled: boolean) => void;
}

export function PriorRulesInput({
  value,
  onChange,
  availableColumns = [],
  disabled = false,
  enableThresholdComparison = false,
  onThresholdComparisonChange,
}: PriorRulesInputProps) {
  const [inputMode, setInputMode] = useState<'text' | 'file' | 'history'>('text');
  const [parsedRules, setParsedRules] = useState<PriorRule[]>([]);
  const [parseError, setParseError] = useState<string | null>(null);
  
  // 文件上传处理
  const handleFileUpload = useCallback(async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const response = await fetch('/api/sop/prior-rules/parse', {
        method: 'POST',
        body: formData,
      });
      
      const result = await response.json();
      
      if (result.success) {
        setParsedRules(result.rules);
        setParseError(null);
        
        // 转换为表达式文本
        const expressions = result.rules
          .map((r: PriorRule) => r.expression)
          .join('\n');
        onChange(expressions, result.rules);
      } else {
        setParseError(result.error);
      }
    } catch (error) {
      setParseError('文件解析失败');
    }
  }, [onChange]);
  
  // 文本输入处理
  const handleTextChange = useCallback((text: string) => {
    onChange(text);
    
    // 简单解析文本
    const lines = text.split('\n').filter(l => l.trim());
    const rules: PriorRule[] = lines.map((line, idx) => ({
      rule_id: `R${idx + 1}`,
      rule_name: `规则${idx + 1}`,
      expression: line.trim(),
      mode: 'expression' as const,
    }));
    setParsedRules(rules);
  }, [onChange]);
  
  // 下载模板
  const handleDownloadTemplate = (type: 'structured' | 'expression') => {
    const templates = {
      structured: 'rule_id,rule_name,feature,operator,threshold,direction\nR001,高风险年龄,age,>=,60,reject\nR002,低收入拒绝,income,<,3000,reject',
      expression: 'rule_id,rule_name,expression\nR001,高风险年龄,(age >= 60)\nR002,复杂规则,(a > 1) & (b < 2)',
    };
    
    const blob = new Blob([templates[type]], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `prior_rules_template_${type}.csv`;
    a.click();
  };
  
  return (
    <div className="space-y-4">
      {/* 模式选择 */}
      <Tabs value={inputMode} onValueChange={(v) => setInputMode(v as any)}>
        <TabsList>
          <TabsTrigger value="text">手动输入</TabsTrigger>
          <TabsTrigger value="file">上传文件</TabsTrigger>
          <TabsTrigger value="history">从历史导入</TabsTrigger>
        </TabsList>
        
        <TabsContent value="text">
          <Textarea
            value={value}
            onChange={(e) => handleTextChange(e.target.value)}
            placeholder="每行一条规则表达式，例如：\n(age > 30)\n(income < 5000)"
            rows={6}
            disabled={disabled}
          />
        </TabsContent>
        
        <TabsContent value="file">
          <div className="border-2 border-dashed rounded-lg p-6 text-center">
            <Upload className="mx-auto h-8 w-8 text-muted-foreground mb-2" />
            <p className="text-sm text-muted-foreground mb-2">
              拖拽文件到此处，或点击选择
            </p>
            <input
              type="file"
              accept=".csv,.xlsx"
              onChange={(e) => e.target.files?.[0] && handleFileUpload(e.target.files[0])}
              className="hidden"
              id="prior-rules-upload"
            />
            <Button variant="outline" asChild>
              <label htmlFor="prior-rules-upload">选择文件</label>
            </Button>
          </div>
          
          <div className="flex gap-2 mt-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => handleDownloadTemplate('structured')}
            >
              <Download className="h-4 w-4 mr-1" />
              简单规则模板
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => handleDownloadTemplate('expression')}
            >
              <Download className="h-4 w-4 mr-1" />
              复杂规则模板
            </Button>
          </div>
        </TabsContent>
        
        <TabsContent value="history">
          {/* 历史任务选择器 */}
          <p className="text-sm text-muted-foreground">
            从历史规则挖掘任务中导入规则...
          </p>
        </TabsContent>
      </Tabs>
      
      {/* 解析结果预览 */}
      {parsedRules.length > 0 && (
        <div className="border rounded-lg p-3">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle className="h-4 w-4 text-green-500" />
            <span className="text-sm">
              已解析 {parsedRules.length} 条规则
            </span>
          </div>
          
          <div className="max-h-40 overflow-y-auto space-y-1">
            {parsedRules.map((rule) => (
              <div
                key={rule.rule_id}
                className="flex items-center gap-2 text-sm py-1"
              >
                {rule.valid !== false ? (
                  <CheckCircle className="h-3 w-3 text-green-500" />
                ) : (
                  <AlertCircle className="h-3 w-3 text-red-500" />
                )}
                <span className="font-mono">{rule.rule_id}</span>
                <span className="text-muted-foreground">{rule.rule_name}</span>
                <span className="flex-1 truncate font-mono text-xs">
                  {rule.expression}
                </span>
                <span className="text-xs px-1 py-0.5 rounded bg-muted">
                  {rule.mode === 'structured' ? '结构化' : '表达式'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* 阈值对比开关 */}
      {parsedRules.some(r => r.mode === 'structured') && (
        <div className="flex items-center justify-between">
          <span className="text-sm">
            启用阈值调整检测（仅对结构化规则生效）
          </span>
          <Switch
            checked={enableThresholdComparison}
            onCheckedChange={onThresholdComparisonChange}
          />
        </div>
      )}
      
      {/* 错误提示 */}
      {parseError && (
        <div className="flex items-center gap-2 text-red-500 text-sm">
          <AlertCircle className="h-4 w-4" />
          {parseError}
        </div>
      )}
    </div>
  );
}
```

---

## 五、API接口设计

### 5.1 规则解析接口

```python
# API/sop_api.py

@router.post("/prior-rules/parse")
async def parse_prior_rules(
    file: UploadFile = File(None),
    text: str = Form(None),
    sample_file_path: str = Form(None)
):
    """
    解析先验规则
    
    支持：
    - CSV/Excel文件上传
    - 文本直接输入
    
    可选校验：
    - 提供sample_file_path时校验列名
    """
    from deepanalyze.analysis.task_SOP.prior_rule_manager import PriorRuleManager
    
    manager = PriorRuleManager()
    
    # 加载规则
    if file:
        # 保存临时文件
        temp_path = f"/tmp/{file.filename}"
        with open(temp_path, "wb") as f:
            f.write(await file.read())
        manager.load_from_csv(temp_path)
    elif text:
        manager.load_from_text(text)
    else:
        raise HTTPException(400, "需要提供文件或文本")
    
    # 可选校验
    if sample_file_path:
        sample_df = pd.read_csv(sample_file_path)
        manager.validate(sample_df)
    
    return {
        "success": True,
        **manager.to_dict()
    }


@router.post("/prior-rules/compare")
async def compare_prior_rules(request: PriorRulesCompareRequest):
    """
    对比先验规则与挖掘规则
    """
    from deepanalyze.analysis.task_SOP.prior_rule_manager import PriorRuleManager
    
    manager = PriorRuleManager()
    
    # 加载先验规则
    if request.prior_rules_text:
        manager.load_from_text(request.prior_rules_text)
    elif request.prior_rules_file:
        manager.load_from_csv(request.prior_rules_file)
    
    # 加载挖掘规则
    mined_df = pd.DataFrame(request.mined_rules)
    
    # 对比
    result = manager.compare_with_mined(mined_df)
    report = manager.get_comparison_report(result)
    
    return {
        "success": True,
        "comparison": result,
        "report": report
    }
```

### 5.2 请求/响应模型

```python
# API/models.py

class PriorRulesCompareRequest(BaseModel):
    prior_rules_text: str | None = None
    prior_rules_file: str | None = None
    mined_rules: list[dict]
    enable_threshold_comparison: bool = True


class PriorRuleParseResponse(BaseModel):
    success: bool
    mode: str
    rules: list[dict]
    rule_count: int
    errors: list[str]
    warnings: list[str]
    validation: dict | None = None
```

---

## 六、集成方案

### 6.1 参数元数据更新

```python
# rule_mining_meta.py

{
    "name": "prior_rules",
    "type": "prior_rules_input",  # 新类型
    "label": "先验规则（可选）",
    "label_en": "Prior Rules",
    "default": "",
    "description": "已有的生产规则列表，支持文件上传或手动输入",
    "stage": "report_generation",
    "advanced": True,
    "options": {
        "enable_threshold_comparison": True,
        "accept_formats": [".csv", ".xlsx"],
        "template_download": True
    }
},
{
    "name": "enable_threshold_comparison",
    "type": "checkbox",
    "label": "启用阈值调整检测",
    "label_en": "Enable Threshold Comparison",
    "default": False,
    "description": "对比先验规则与挖掘规则的阈值变化",
    "stage": "report_generation",
    "advanced": True,
    "show_when": {"prior_rules": "not_empty"}
}
```

### 6.2 Pipeline集成

```python
# rule_mining.py - report_generation 阶段

def _generate_report(self, context: PipelineContext) -> dict:
    # ... 现有逻辑 ...
    
    # 先验规则分析
    prior_rules_text = context.params.get('prior_rules', '')
    enable_comparison = context.params.get('enable_threshold_comparison', False)
    
    if prior_rules_text:
        from .prior_rule_manager import PriorRuleManager
        
        manager = PriorRuleManager()
        manager.load_from_text(prior_rules_text)
        
        # 现有增量贡献分析
        prior_expressions = manager.get_expressions()
        prior_analysis = self.evaluator.evaluate_rules_with_prior(
            df, rule_df, prior_expressions, target_col
        )
        
        # 新增：阈值对比分析
        if enable_comparison:
            comparison_result = manager.compare_with_mined(rule_df)
            report['threshold_comparison'] = comparison_result
            report['threshold_comparison_report'] = manager.get_comparison_report(comparison_result)
    
    return report
```

---

## 七、输出报告增强

### 7.1 新增输出定义

```python
# rule_mining_meta.py - outputs

{
    "id": "threshold_comparison",
    "name": "阈值调整分析",
    "type": "json",
    "show_when": {"enable_threshold_comparison": True}
},
{
    "id": "threshold_comparison_report",
    "name": "阈值调整报告",
    "type": "text",
    "show_when": {"enable_threshold_comparison": True}
}
```

### 7.2 报告示例

```
================================================================
先验规则对比分析报告
================================================================

📊 总览
  - 先验规则数: 15
  - 挖掘规则数: 12
  - 完全新增: 4
  - 阈值调整: 3
  - 方向调整: 0
  - 保留: 5
  - 建议移除: 3

🆕 完全新增规则
----------------------------------------
  (credit_score < 550)
  (recent_inquiry_count > 10)
  (employment_years < 1)
  (card_util_ratio > 0.9)

🔄 阈值调整规则
----------------------------------------
  age: 60 → 55 (decreased)
  income: 3000 → 3500 (increased)
  debt_ratio: 0.7 → 0.65 (decreased)

✅ 保留规则
----------------------------------------
  (loan_count > 5)
  (overdue_days > 30)
  (credit_limit < 10000)
  (account_age < 12)
  (payment_ratio < 0.5)

⚠️ 建议移除规则
----------------------------------------
  (job_type == '无业') - 未在挖掘结果中出现
  (region == '高风险区域') - 未在挖掘结果中出现
  (channel == 'offline') - 未在挖掘结果中出现
```

---

## 八、实现计划

### 8.1 开发阶段

| 阶段 | 任务 | 预估工时 | 优先级 |
|------|------|----------|--------|
| Phase 1 | `PriorRuleParser` CSV解析器 | 4h | P0 |
| Phase 2 | `RuleValidator` 规则校验器 | 3h | P0 |
| Phase 3 | `ThresholdComparator` 阈值对比器 | 4h | P1 |
| Phase 4 | `PriorRuleManager` 统一管理器 | 2h | P0 |
| Phase 5 | API接口实现 | 3h | P0 |
| Phase 6 | 前端 `PriorRulesInput` 组件 | 6h | P1 |
| Phase 7 | Pipeline集成 | 3h | P1 |
| Phase 8 | 测试与文档 | 4h | P2 |

**总计**: 约 29 小时

### 8.2 文件修改清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `prior_rule_parser.py` | 新增 | CSV解析器 |
| `prior_rule_validator.py` | 新增 | 规则校验器 |
| `threshold_comparator.py` | 新增 | 阈值对比器 |
| `prior_rule_manager.py` | 新增 | 统一管理器 |
| `rule_mining_meta.py` | 修改 | 参数定义更新 |
| `rule_mining.py` | 修改 | Pipeline集成 |
| `API/sop_api.py` | 修改 | 新增API端点 |
| `PriorRulesInput.tsx` | 新增 | 前端组件 |
| `DynamicParamRenderer.tsx` | 修改 | 支持新参数类型 |

---

## 九、测试用例

### 9.1 解析器测试

```python
def test_parse_structured_csv():
    parser = PriorRuleParser()
    parser.parse_csv("test_structured.csv")
    
    assert parser.mode == 'structured'
    assert len(parser.rules) == 5
    assert parser.rules[0]['expression'] == '(age >= 60)'


def test_parse_expression_csv():
    parser = PriorRuleParser()
    parser.parse_csv("test_expression.csv")
    
    assert parser.mode == 'expression'
    assert '(a > 1) & (b < 2)' in parser.get_expressions()


def test_parse_text():
    parser = PriorRuleParser()
    parser.parse_text("(age > 30)\n(income < 5000)")
    
    assert len(parser.rules) == 2
```

### 9.2 阈值对比测试

```python
def test_threshold_comparison():
    comparator = ThresholdComparator()
    
    prior_rules = [
        {'rule_id': 'R001', 'feature': 'age', 'operator': '>=', 'threshold': 60, 'mode': 'structured'},
        {'rule_id': 'R002', 'feature': 'income', 'operator': '<', 'threshold': 3000, 'mode': 'structured'},
    ]
    
    mined_df = pd.DataFrame([
        {'rule': '(age >= 55)'},
        {'rule': '(income < 3500)'},
        {'rule': '(credit_score < 550)'},
    ])
    
    result = comparator.compare(prior_rules, mined_df)
    
    assert result['summary']['threshold_adjusted_count'] == 2
    assert result['summary']['new_count'] == 1
```

---

## 十、附录

### 10.1 CSV模板文件

**简单规则模板 (prior_rules_template_structured.csv)**:
```csv
rule_id,rule_name,feature,operator,threshold,direction
R001,高风险年龄,age,>=,60,reject
R002,低收入拒绝,income,<,3000,reject
R003,高负债率,debt_ratio,>=,0.7,reject
R004,多头借贷,loan_count,>,5,reject
R005,低信用分,credit_score,<,550,reject
```

**复杂规则模板 (prior_rules_template_expression.csv)**:
```csv
rule_id,rule_name,expression
R001,高风险年龄,(age >= 60)
R002,低收入拒绝,(income < 3000)
R003,高负债且多头,(debt_ratio >= 0.7) & (loan_count > 5)
R004,年轻或低信用,(age < 25) | (credit_score < 550)
R005,复杂组合规则,(age > 30) & ((income < 5000) | (debt_ratio > 0.6))
```

### 10.2 相关文档

- [规则挖掘任务设计文档](./rule_mining_task_design.md)
- [DeepAnalyze升级设计文档](../DeepAnalyze_upgrade_design.md)
- [规则挖掘增强设计文档](./rule_mining_enhancement_design.md)
