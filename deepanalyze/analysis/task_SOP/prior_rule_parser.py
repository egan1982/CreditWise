"""
P2-7: 先验规则解析器（精简版）

按 Eng Review E1 建议，将原方案 4 个类合并为 1 个 PriorRuleParser + 1 个 compare_thresholds() 函数。
包含：CSV 解析、格式自动识别、表达式生成、列名校验、阈值对比。

安全修复：
- E5: 用 ast.literal_eval 替代 eval 解析 between 的 [min, max]
"""

import ast
import re
import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


class PriorRuleParser:
    """
    先验规则解析器（精简版）
    
    支持三种输入：
    1. CSV 文件（结构化格式 或 表达式格式，自动识别）
    2. 文本（每行一条表达式，兼容现有 textarea）
    3. DataFrame（直接传入）
    
    输出统一的 list[str] 表达式列表，供 PriorRuleAnalyzer 使用。
    """
    
    SUPPORTED_OPERATORS = {
        '>', '>=', '<', '<=', '==', '!=', 'in', 'not in', 'between'
    }
    
    def __init__(self):
        self.rules: list[dict[str, Any]] = []
        self.mode: str = 'unknown'  # 'structured', 'expression', 'mixed'
        self.errors: list[str] = []
        self.warnings: list[str] = []
    
    # =========================================================================
    # 输入方法
    # =========================================================================
    
    def parse_csv(self, file_path: str) -> "PriorRuleParser":
        """解析 CSV 文件"""
        try:
            df = pd.read_csv(file_path, encoding='utf-8')
        except UnicodeDecodeError:
            try:
                df = pd.read_csv(file_path, encoding='gbk')
            except UnicodeDecodeError:
                df = pd.read_csv(file_path, encoding='utf-8-sig')  # BOM
        return self.parse_dataframe(df)
    
    def parse_dataframe(self, df: pd.DataFrame) -> "PriorRuleParser":
        """解析 DataFrame（含 L1 智能格式识别）"""
        self._reset()
        
        if df.empty:
            self.errors.append("文件为空，请检查文件内容")
            return self
        
        # 标准化列名（去空格、转小写）
        df.columns = df.columns.str.strip().str.lower()
        
        # L1 智能格式识别：检查是否包含必要列
        self.mode = self._detect_mode(df)
        if self.mode == 'unknown':
            actual_cols = list(df.columns)
            self.errors.append(
                f"无法识别规则格式。文件列为: {actual_cols}。"
                f"请使用以下格式之一：\n"
                f"• 结构化格式：需包含 feature, operator, threshold 列\n"
                f"• 表达式格式：需包含 expression 列"
            )
            return self
        
        for idx, row in df.iterrows():
            try:
                rule = self._parse_row(row, int(idx))
                if rule:
                    self.rules.append(rule)
            except Exception as e:
                self.errors.append(f"第 {int(idx) + 2} 行: {str(e)}")
        
        # L1: 解析后 0 条有效规则也视为格式错误
        if len(self.rules) == 0 and len(self.errors) == 0:
            self.errors.append("文件中未找到有效规则，请检查内容格式")
        
        return self
    
    def parse_text(self, text: str) -> "PriorRuleParser":
        """解析文本（兼容现有 textarea 输入，每行一条表达式）"""
        self._reset()
        self.mode = 'expression'
        
        if not text or not text.strip():
            return self
        
        lines = text.strip().split('\n')
        for idx, line in enumerate(lines):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            self.rules.append({
                'rule_id': f'R{idx + 1:03d}',
                'rule_name': f'规则{idx + 1}',
                'expression': line,
                'mode': 'expression',
                'source': 'text',
            })
        
        return self
    
    # =========================================================================
    # 输出方法
    # =========================================================================
    
    def get_expressions(self) -> list[str]:
        """获取所有规则表达式列表（供 PriorRuleAnalyzer 使用）"""
        return [r['expression'] for r in self.rules]
    
    def get_structured_rules(self) -> list[dict[str, Any]]:
        """获取结构化规则列表（供阈值对比使用）"""
        return [r for r in self.rules if r.get('mode') == 'structured']
    
    def validate_columns(self, available_columns: set[str]) -> dict[str, Any]:
        """
        校验规则中的列名是否存在于数据集中
        
        Args:
            available_columns: 数据集中可用的列名集合
            
        Returns:
            校验结果 {total, valid, invalid, details}
        """
        results = []
        valid_count = 0
        
        for rule in self.rules:
            expr = rule.get('expression', '')
            # 提取表达式中的标识符
            identifiers = set(re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', expr))
            # 排除 Python 关键字和常见方法
            keywords = {'and', 'or', 'not', 'in', 'True', 'False', 'None', 'isin', 'abs', 'str', 'int', 'float'}
            identifiers -= keywords
            
            missing_cols = [c for c in identifiers if c not in available_columns]
            is_valid = len(missing_cols) == 0
            
            if is_valid:
                valid_count += 1
            
            results.append({
                'rule_id': rule.get('rule_id'),
                'expression': expr,
                'valid': is_valid,
                'missing_columns': missing_cols,
            })
        
        return {
            'total': len(self.rules),
            'valid': valid_count,
            'invalid': len(self.rules) - valid_count,
            'details': results,
        }
    
    def to_dict(self) -> dict[str, Any]:
        """转换为完整字典（用于 API 响应）"""
        return {
            'mode': self.mode,
            'rules': self.rules,
            'rule_count': len(self.rules),
            'expressions': self.get_expressions(),
            'errors': self.errors,
            'warnings': self.warnings,
        }
    
    # =========================================================================
    # 内部方法
    # =========================================================================
    
    def _reset(self):
        self.rules = []
        self.errors = []
        self.warnings = []
        self.mode = 'unknown'
    
    def _detect_mode(self, df: pd.DataFrame) -> str:
        """检测 CSV 格式模式"""
        cols = set(df.columns)
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
                "CSV 格式无效：需要包含 (feature, operator, threshold) 列 或 (expression) 列"
            )
    
    def _parse_row(self, row: pd.Series, idx: int) -> dict[str, Any] | None:
        """解析单行规则"""
        rule_id = str(row.get('rule_id', f'R{idx + 1:03d}')).strip()
        rule_name = str(row.get('rule_name', f'规则{idx + 1}')).strip()
        
        # 优先使用 expression 列
        if 'expression' in row.index and pd.notna(row.get('expression')):
            expr = str(row['expression']).strip()
            if expr:
                return {
                    'rule_id': rule_id,
                    'rule_name': rule_name,
                    'expression': expr,
                    'mode': 'expression',
                    'source': 'csv',
                }
        
        # 使用结构化列
        if all(col in row.index for col in ['feature', 'operator', 'threshold']):
            feature = str(row['feature']).strip() if pd.notna(row.get('feature')) else ''
            operator = str(row['operator']).strip() if pd.notna(row.get('operator')) else ''
            threshold = row['threshold']
            
            if not feature:
                return None
            
            expr = self._build_expression(feature, operator, threshold)
            direction = str(row.get('direction', 'reject')).strip() if pd.notna(row.get('direction')) else 'reject'
            
            return {
                'rule_id': rule_id,
                'rule_name': rule_name,
                'expression': expr,
                'feature': feature,
                'operator': operator,
                'threshold': threshold,
                'direction': direction,
                'mode': 'structured',
                'source': 'csv',
            }
        
        return None
    
    def _build_expression(self, feature: str, operator: str, threshold: Any) -> str:
        """
        构建规则表达式
        
        E5 安全修复: 用 ast.literal_eval 替代 eval
        """
        op = operator.strip().lower()
        
        if op == 'between':
            # threshold 应为 [min, max] 格式
            if isinstance(threshold, str):
                try:
                    threshold = ast.literal_eval(threshold)  # E5: 安全解析
                except (ValueError, SyntaxError):
                    raise ValueError(f"between 的 threshold 格式无效: {threshold}，期望 [min, max]")
            if not isinstance(threshold, (list, tuple)) or len(threshold) != 2:
                raise ValueError(f"between 需要 [min, max] 格式，实际: {threshold}")
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


# =============================================================================
# 阈值对比函数（独立函数，按 E1 建议不放入类中）
# =============================================================================

def compare_thresholds(
    prior_rules: list[dict[str, Any]],
    mined_rules_df: pd.DataFrame,
) -> dict[str, Any]:
    """
    对比先验规则与挖掘规则的阈值变化
    
    仅对结构化规则（有 feature/operator/threshold）有效。
    
    Args:
        prior_rules: 来自 PriorRuleParser.get_structured_rules() 的结构化规则列表
        mined_rules_df: 挖掘出的最优规则 DataFrame（含 'rule' 列）
        
    Returns:
        对比结果 {summary, new_rules, threshold_adjusted, retained, deprecated}
    """
    # 解析挖掘规则，提取特征和阈值
    pattern = r'\(?\s*(\w+)\s*(>=|<=|>|<|==|!=)\s*([\d.]+)\s*\)?'
    
    mined_parsed: list[dict[str, Any]] = []
    for _, row in mined_rules_df.iterrows():
        rule_expr = str(row.get('rule', ''))
        match = re.match(pattern, rule_expr.strip())
        if match:
            mined_parsed.append({
                'rule': rule_expr,
                'feature': match.group(1),
                'operator': match.group(2),
                'threshold': float(match.group(3)),
            })
        else:
            mined_parsed.append({
                'rule': rule_expr,
                'feature': None,
                'operator': None,
                'threshold': None,
            })
    
    # 构建先验规则索引（按特征名）
    prior_by_feature: dict[str, dict[str, Any]] = {}
    for rule in prior_rules:
        feature = rule.get('feature')
        if feature and feature not in prior_by_feature:
            prior_by_feature[feature] = rule
    
    # 分类
    new_rules = []
    threshold_adjusted = []
    retained = []
    matched_prior_features: set[str] = set()
    
    for mined in mined_parsed:
        feature = mined.get('feature')
        if not feature or feature not in prior_by_feature:
            new_rules.append(mined)
            continue
        
        prior = prior_by_feature[feature]
        matched_prior_features.add(feature)
        
        try:
            prior_th = float(prior.get('threshold', 0))
            mined_th = float(mined.get('threshold', 0))
        except (ValueError, TypeError):
            retained.append({**mined, 'prior_rule': prior})
            continue
        
        if abs(prior_th - mined_th) < 1e-6:
            retained.append({**mined, 'prior_rule': prior})
        else:
            change = mined_th - prior_th
            threshold_adjusted.append({
                **mined,
                'prior_rule': prior,
                'prior_threshold': prior_th,
                'new_threshold': mined_th,
                'change': change,
                'direction': 'increased' if change > 0 else 'decreased',
            })
    
    # 先验规则中未在挖掘结果出现的（建议移除）
    deprecated = []
    for feature, rule in prior_by_feature.items():
        if feature not in matched_prior_features:
            deprecated.append({**rule, 'reason': '未在挖掘结果中出现'})
    
    summary = {
        'prior_count': len(prior_rules),
        'mined_count': len(mined_parsed),
        'new_count': len(new_rules),
        'threshold_adjusted_count': len(threshold_adjusted),
        'retained_count': len(retained),
        'deprecated_count': len(deprecated),
    }
    
    return {
        'summary': summary,
        'new_rules': new_rules,
        'threshold_adjusted': threshold_adjusted,
        'retained': retained,
        'deprecated': deprecated,
    }
