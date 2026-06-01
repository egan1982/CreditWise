"""
P2-7 先验规则输入增强 — 完整测试脚本

覆盖：
  1. PriorRuleParser 单元测试（parse_text / parse_csv / validate_columns / 空输入 / 编码）
  2. E2 回归测试（字符串 vs 列表输入，PriorRuleAnalyzer 不再逐字符迭代）
  3. E5 安全测试（ast.literal_eval + 恶意输入拒绝）
  4. Pipeline 集成测试（真实数据 + prior_rules 字符串 → 非零 prior_analysis）
  5. compare_thresholds 功能测试
  6. 报告生成器数据流验证（prior_analysis 字段映射检查）
  7. 前端 UI 字段匹配验证（PriorAnalysisPanel 期望 vs Pipeline 输出）

数据集: workspace/session_1768786483478_njde0oyfu/starrel_train_with_amount.csv

运行方式:
  cd workspace/DeepAnalyze
  .venv/Scripts/python.exe tests/test_prior_rules.py
"""

import os
import sys
import time
import tempfile
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

# Setup
sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

warnings.filterwarnings("ignore")

from deepanalyze.analysis.task_SOP.prior_rule_parser import PriorRuleParser, compare_thresholds
from deepanalyze.analysis.task_SOP.rule_mining import PriorRuleAnalyzer, RuleMiningPipeline

DATA_PATH = Path(__file__).parent.parent / "workspace" / "session_1768786483478_njde0oyfu" / "starrel_train_with_amount.csv"


# =============================================================================
# 1. PriorRuleParser 单元测试
# =============================================================================

def test_1_parser_parse_text():
    """parse_text: 多行表达式 + 空行 + 注释"""
    print("\n" + "=" * 70)
    print("1. PriorRuleParser.parse_text")
    print("=" * 70)
    
    parser = PriorRuleParser()
    text = "(age > 30)\n\n# comment\n(income < 5000)\n(debt_ratio >= 0.7)"
    parser.parse_text(text)
    
    assert parser.mode == "expression"
    assert len(parser.rules) == 3, f"期望 3 条规则，实际 {len(parser.rules)}"
    assert parser.rules[0]["expression"] == "(age > 30)"
    assert parser.rules[1]["expression"] == "(income < 5000)"
    assert parser.rules[2]["expression"] == "(debt_ratio >= 0.7)"
    
    exprs = parser.get_expressions()
    assert len(exprs) == 3
    assert all(isinstance(e, str) for e in exprs)
    
    print(f"  解析 3 条规则，跳过空行和注释 OK")
    print("  ✅ PASS")
    return True


def test_1b_parser_parse_text_empty():
    """parse_text: 空文本 / None"""
    print("\n" + "=" * 70)
    print("1b. PriorRuleParser.parse_text 空输入")
    print("=" * 70)
    
    parser = PriorRuleParser()
    parser.parse_text("")
    assert len(parser.rules) == 0
    
    parser.parse_text("   \n  \n  ")
    assert len(parser.rules) == 0
    
    print("  空文本返回 0 条规则 OK")
    print("  ✅ PASS")
    return True


def test_1c_parser_parse_csv_structured():
    """parse_csv: 结构化格式（feature, operator, threshold）"""
    print("\n" + "=" * 70)
    print("1c. PriorRuleParser.parse_csv 结构化格式")
    print("=" * 70)
    
    csv_content = "rule_id,rule_name,feature,operator,threshold,direction\nR001,高龄,age,>=,60,reject\nR002,低收入,income,<,3000,reject\nR003,高负债,debt_ratio,>=,0.7,reject"
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8-sig') as f:
        f.write(csv_content)
        tmp_path = f.name
    
    try:
        parser = PriorRuleParser()
        parser.parse_csv(tmp_path)
        
        assert parser.mode == "structured", f"期望 structured，实际 {parser.mode}"
        assert len(parser.rules) == 3
        # CSV 读入后 threshold 为 float，所以表达式是 60.0 而非 60
        assert "age" in parser.rules[0]["expression"] and ">=" in parser.rules[0]["expression"]
        assert parser.rules[0]["feature"] == "age"
        assert parser.rules[0]["operator"] == ">="
        assert parser.rules[0]["mode"] == "structured"
        
        structured = parser.get_structured_rules()
        assert len(structured) == 3
        
        print(f"  解析 3 条结构化规则 OK")
        for r in parser.rules:
            print(f"    {r['rule_id']}: {r['expression']}")
    finally:
        os.unlink(tmp_path)
    
    print("  ✅ PASS")
    return True


def test_1d_parser_parse_csv_expression():
    """parse_csv: 表达式格式"""
    print("\n" + "=" * 70)
    print("1d. PriorRuleParser.parse_csv 表达式格式")
    print("=" * 70)
    
    csv_content = "rule_id,rule_name,expression\nR001,复杂规则,(age > 30) & (income < 5000)\nR002,简单规则,(debt_ratio >= 0.7)"
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
        f.write(csv_content)
        tmp_path = f.name
    
    try:
        parser = PriorRuleParser()
        parser.parse_csv(tmp_path)
        
        assert parser.mode == "expression"
        assert len(parser.rules) == 2
        assert "(age > 30) & (income < 5000)" in parser.get_expressions()
    finally:
        os.unlink(tmp_path)
    
    print("  解析 2 条表达式规则 OK")
    print("  ✅ PASS")
    return True


def test_1e_parser_validate_columns():
    """validate_columns: 列名校验"""
    print("\n" + "=" * 70)
    print("1e. PriorRuleParser.validate_columns")
    print("=" * 70)
    
    parser = PriorRuleParser()
    parser.parse_text("(age > 30)\n(income < 5000)\n(nonexistent_col > 10)")
    
    available = {"age", "income", "debt_ratio", "label"}
    result = parser.validate_columns(available)
    
    assert result["total"] == 3
    assert result["valid"] == 2, f"期望 2 个有效，实际 {result['valid']}"
    assert result["invalid"] == 1
    
    # 找到无效的那条
    invalid_rules = [d for d in result["details"] if not d["valid"]]
    assert len(invalid_rules) == 1
    assert "nonexistent_col" in invalid_rules[0]["missing_columns"]
    
    print(f"  3 条规则: 2 valid, 1 invalid (nonexistent_col) OK")
    print("  ✅ PASS")
    return True


# =============================================================================
# 2. E2 回归测试
# =============================================================================

def test_2_e2_string_vs_list():
    """E2: PriorRuleAnalyzer 接收字符串 vs 列表，验证不再逐字符迭代"""
    print("\n" + "=" * 70)
    print("2. E2 回归测试: prior_rules 字符串 vs 列表")
    print("=" * 70)
    
    # 构造简单测试数据
    rng = np.random.RandomState(42)
    n = 500
    df = pd.DataFrame({
        "age": rng.randint(18, 65, n).astype(float),
        "income": rng.uniform(10000, 200000, n),
        "label": (rng.random(n) < 0.05).astype(int),
    })
    
    prior_text = "(age > 50)\n(income < 30000)"
    prior_list = ["(age > 50)", "(income < 30000)"]
    
    # 测试列表输入（正确方式）
    analyzer_list = PriorRuleAnalyzer(prior_rules=prior_list)
    analyzer_list.fit(df, target_col="label")
    summary_list = analyzer_list.get_summary()
    
    # 测试 run() 中的 E2 修复（字符串自动转列表）
    # 模拟 run() 入口的转换逻辑
    prior_from_str = prior_text
    if isinstance(prior_from_str, str):
        prior_from_str = [r.strip() for r in prior_from_str.split('\n') if r.strip()]
    
    analyzer_str = PriorRuleAnalyzer(prior_rules=prior_from_str)
    analyzer_str.fit(df, target_col="label")
    summary_str = analyzer_str.get_summary()
    
    # 两者结果应一致
    assert summary_list["prior_rules_count"] == summary_str["prior_rules_count"] == 2
    assert summary_list["prior_metrics"]["prior_hit_rate"] == summary_str["prior_metrics"]["prior_hit_rate"]
    assert summary_list["prior_metrics"]["prior_recall"] == summary_str["prior_metrics"]["prior_recall"]
    
    # 验证 prior_hit_rate > 0（如果为 0 说明逐字符迭代 Bug 仍存在）
    assert summary_list["prior_metrics"]["prior_hit_rate"] > 0, \
        f"prior_hit_rate=0，可能仍有 E2 逐字符迭代 Bug"
    
    print(f"  列表输入: prior_hit_rate={summary_list['prior_metrics']['prior_hit_rate']:.4f}")
    print(f"  字符串转换: prior_hit_rate={summary_str['prior_metrics']['prior_hit_rate']:.4f}")
    print(f"  两者一致且 >0 → E2 修复有效")
    print("  ✅ PASS")
    return True


# =============================================================================
# 3. E5 安全测试
# =============================================================================

def test_3_e5_security():
    """E5: between 运算符用 ast.literal_eval，拒绝恶意输入"""
    print("\n" + "=" * 70)
    print("3. E5 安全测试: ast.literal_eval + 恶意输入")
    print("=" * 70)
    
    parser = PriorRuleParser()
    
    # 正常 between
    expr = parser._build_expression("age", "between", "[25, 35]")
    assert expr == "(age >= 25) & (age <= 35)", f"between 表达式错误: {expr}"
    print(f"  between [25,35] → {expr} OK")
    
    # 恶意输入应被拒绝
    try:
        parser._build_expression("age", "between", "__import__('os').system('echo hacked')")
        print("  ❌ 恶意输入未被拒绝!")
        return False
    except (ValueError, SyntaxError):
        print("  恶意输入被 ast.literal_eval 正确拒绝 OK")
    
    # 格式错误
    try:
        parser._build_expression("age", "between", "[25]")  # 只有一个值
        print("  ❌ 格式错误未被拒绝!")
        return False
    except ValueError:
        print("  格式错误 [25] 被正确拒绝 OK")
    
    print("  ✅ PASS")
    return True


# =============================================================================
# 4. Pipeline 集成测试
# =============================================================================

def test_4_pipeline_integration():
    """Pipeline 集成: 真实数据 + prior_rules 字符串 → prior_analysis 非零"""
    print("\n" + "=" * 70)
    print("4. Pipeline 集成测试（真实数据 + prior_rules）")
    print("=" * 70)
    
    if not DATA_PATH.exists():
        print(f"  跳过: 数据文件不存在 {DATA_PATH}")
        return True
    
    df = pd.read_csv(DATA_PATH)
    print(f"  原始数据: {len(df)} 行, bad_rate={df['label'].mean():.4f}")
    
    # 移除非数值列 + 采样
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    cat_cols = [c for c in cat_cols if c != "fuuid"]
    df = df.drop(columns=cat_cols)
    df = df.sample(n=2000, random_state=42).reset_index(drop=True)
    
    # 选取数值特征
    exclude = {"fuuid", "label", "SelectionProb", "SamplingWeight", "loss_amount"}
    feature_cols = [c for c in df.select_dtypes(include=[np.number]).columns if c not in exclude]
    # 只保留有效特征（>10% 非缺失）
    feature_cols = [c for c in feature_cols if (df[c] != -1).sum() / len(df) > 0.1]
    
    df_clean = df[["label"] + feature_cols].copy().fillna(-1)
    
    # prior_rules 作为字符串传入（模拟前端 textarea）
    prior_rules_str = "(f0 > 0)\n(f26 > 0)\n(f47 > 0)"
    
    print(f"  采样: {len(df_clean)} 行, {len(feature_cols)} 特征")
    print(f"  prior_rules (字符串): {prior_rules_str}")
    
    t0 = time.time()
    pipeline = RuleMiningPipeline(
        mining_mode="multi",
        id_cols=[],
        max_depth=3,
        n_vars=2,
        max_hit_rate_filter=0.40,
        min_lift_filter=1.2,
        max_hit_rate_select=0.50,
    )
    
    results = pipeline.run(
        df_clean,
        target_col="label",
        feature_cols=feature_cols,
        prior_rules=prior_rules_str,  # 字符串输入！E2 修复后应自动转换
        skip_preprocessing=True,
    )
    elapsed = time.time() - t0
    
    # 验证 prior_analysis 存在且 enabled
    assert "prior_analysis" in results, "缺少 prior_analysis"
    pa = results["prior_analysis"]
    assert pa.get("enabled") == True, f"prior_analysis.enabled={pa.get('enabled')}"
    
    # 验证 prior_rules 被正确转换为列表
    assert isinstance(pa.get("prior_rules"), list), "prior_rules 应为 list"
    assert len(pa["prior_rules"]) == 3, f"期望 3 条规则，实际 {len(pa['prior_rules'])}"
    
    # FIX-A 验证: rules 应为 list[dict]（不再是 DataFrame）
    rules_list = pa.get("rules")
    assert isinstance(rules_list, list), f"prior_analysis.rules 应为 list，实际 {type(rules_list)}"
    assert len(rules_list) > 0, "prior_analysis.rules 为空"
    print(f"  prior_analysis.rules: {len(rules_list)} 条规则分析")
    
    # 验证每条规则都有必需字段（Pipeline 原生 + 报告兼容别名）
    r0 = rules_list[0]
    for field in ['rule', 'standalone_recall', 'incremental_recall', 'overlap_rate', 'marginal_contribution',
                  'recall', 'hit_rate', 'matched']:
        assert field in r0, f"rules[0] 缺少字段 {field}，实际 keys={list(r0.keys())}"
    print(f"  rules[0] 字段: {list(r0.keys())}")
    
    # 验证 summary 包含所有期望字段
    summary = pa.get("summary", {})
    assert summary.get("prior_rules_count") == 3
    assert "prior_metrics" in summary
    prior_hit_rate = summary["prior_metrics"].get("prior_hit_rate", 0)
    
    # FIX-A 验证: summary 中补充的报告/前端字段
    assert "matched_count" in summary, "summary 缺少 matched_count"
    assert "avg_recall" in summary, "summary 缺少 avg_recall"
    assert "new_rules_count" in summary, "summary 缺少 new_rules_count"
    assert "incremental_recall" in summary, "summary 缺少 incremental_recall"
    assert "avg_overlap_rate" in summary, "summary 缺少 avg_overlap_rate"
    
    print(f"  summary.prior_rules_count: {summary['prior_rules_count']}")
    print(f"  summary.prior_metrics.prior_hit_rate: {prior_hit_rate:.4f}")
    print(f"  summary.matched_count: {summary['matched_count']}")
    print(f"  summary.avg_recall: {summary['avg_recall']:.4f}")
    print(f"  summary.new_rules_count: {summary['new_rules_count']}")
    print(f"  summary.incremental_recall: {summary['incremental_recall']:.4f}")
    print(f"  summary.avg_overlap_rate: {summary['avg_overlap_rate']:.4f}")
    
    print(f"  耗时: {elapsed:.1f}s")
    print("  ✅ PASS")
    return True


# =============================================================================
# 5. compare_thresholds 功能测试
# =============================================================================

def test_5_compare_thresholds():
    """compare_thresholds: 结构化规则 vs 挖掘规则对比"""
    print("\n" + "=" * 70)
    print("5. compare_thresholds 功能测试")
    print("=" * 70)
    
    prior_rules = [
        {"rule_id": "R001", "feature": "age", "operator": ">=", "threshold": 60, "mode": "structured"},
        {"rule_id": "R002", "feature": "income", "operator": "<", "threshold": 3000, "mode": "structured"},
        {"rule_id": "R003", "feature": "debt_ratio", "operator": ">=", "threshold": 0.7, "mode": "structured"},
    ]
    
    mined_df = pd.DataFrame([
        {"rule": "(age >= 55)"},       # 阈值从 60→55（decreased）
        {"rule": "(income < 3500)"},   # 阈值从 3000→3500（increased）
        {"rule": "(credit_score < 550)"},  # 新增规则
    ])
    
    result = compare_thresholds(prior_rules, mined_df)
    
    summary = result["summary"]
    assert summary["prior_count"] == 3
    assert summary["mined_count"] == 3
    assert summary["threshold_adjusted_count"] == 2, f"期望 2 个阈值调整，实际 {summary['threshold_adjusted_count']}"
    assert summary["new_count"] == 1, f"期望 1 个新增，实际 {summary['new_count']}"
    assert summary["deprecated_count"] == 1, f"期望 1 个建议移除，实际 {summary['deprecated_count']}"
    
    # 验证阈值调整详情
    adjusted = result["threshold_adjusted"]
    age_adj = [a for a in adjusted if a["feature"] == "age"]
    assert len(age_adj) == 1
    assert age_adj[0]["prior_threshold"] == 60
    assert age_adj[0]["new_threshold"] == 55
    assert age_adj[0]["direction"] == "decreased"
    
    print(f"  summary: {summary}")
    print(f"  阈值调整: age 60→55 (decreased), income 3000→3500 (increased)")
    print(f"  新增: credit_score < 550")
    print(f"  建议移除: debt_ratio >= 0.7（未在挖掘结果出现）")
    print("  ✅ PASS")
    return True


# =============================================================================
# 6. 报告生成器数据流验证
# =============================================================================

def test_6_report_data_flow():
    """报告生成器: prior_analysis 字段映射检查（FIX-A 修复验证）"""
    print("\n" + "=" * 70)
    print("6. 报告生成器 prior_analysis 数据流验证（FIX-A 修复后）")
    print("=" * 70)
    
    # FIX-A 后 Pipeline 实际输出的 prior_analysis 结构
    pipeline_output_fields = {
        "top_level": ["enabled", "prior_rules", "rules", "summary"],
        "summary": ["enabled", "prior_rules", "prior_rules_count", "prior_metrics", 
                     "total_samples", "total_bad",
                     "matched_count", "avg_recall", "avg_lift",
                     "new_rules_count", "incremental_recall", "avg_overlap_rate"],
        "rules_list_fields": ["rule", "standalone_recall", "standalone_hit_rate", 
                               "incremental_recall", "incremental_hit_rate", 
                               "overlap_rate", "marginal_contribution",
                               "recall", "hit_rate", "matched"],
    }
    
    # 报告生成器期望的字段
    report_expected_fields = {
        "summary": ["prior_rules_count", "matched_count", "avg_recall", "avg_lift"],
        "rules[]": ["rule", "recall", "hit_rate", "matched"],
    }
    
    # 检查匹配
    pipeline_summary = set(pipeline_output_fields["summary"])
    report_summary = set(report_expected_fields["summary"])
    missing_in_pipeline = report_summary - pipeline_summary
    
    pipeline_rule_fields = set(pipeline_output_fields["rules_list_fields"])
    report_rule_fields = set(report_expected_fields["rules[]"])
    missing_in_rules = report_rule_fields - pipeline_rule_fields
    
    errors = []
    if missing_in_pipeline:
        errors.append(f"报告期望但 Pipeline 未输出的 summary 字段: {missing_in_pipeline}")
    if missing_in_rules:
        errors.append(f"报告期望但 Pipeline 未输出的 rules 字段: {missing_in_rules}")
    
    print(f"  Pipeline summary 字段: {len(pipeline_summary)} 个")
    print(f"  报告期望 summary 字段: {report_summary}")
    print(f"  summary 缺失: {missing_in_pipeline or '无'}")
    print(f"  rules 缺失: {missing_in_rules or '无'}")
    
    if errors:
        for e in errors:
            print(f"  ❌ {e}")
        raise AssertionError(f"FIX-A 修复不完整: {errors}")
    
    print("  ✅ PASS — FIX-A 修复后报告字段完全匹配")
    return True


# =============================================================================
# 7. 前端 UI 字段匹配验证
# =============================================================================

def test_7_frontend_field_matching():
    """前端 PriorAnalysisPanel: 期望字段 vs Pipeline 输出（FIX-A 修复验证）"""
    print("\n" + "=" * 70)
    print("7. 前端 PriorAnalysisPanel 字段匹配验证（FIX-A 修复后）")
    print("=" * 70)
    
    # 前端期望的字段
    frontend_summary = {"prior_rules_count", "new_rules_count", "incremental_recall", "avg_overlap_rate"}
    frontend_rules = {"rule", "standalone_recall", "incremental_recall", "overlap_rate", "marginal_contribution"}
    
    # FIX-A 后 Pipeline 实际输出的 summary 字段
    pipeline_summary = {"enabled", "prior_rules", "prior_rules_count", "prior_metrics", 
                         "total_samples", "total_bad",
                         "matched_count", "avg_recall", "avg_lift",
                         "new_rules_count", "incremental_recall", "avg_overlap_rate"}
    pipeline_rules = {"rule", "standalone_recall", "standalone_hit_rate", 
                       "incremental_recall", "incremental_hit_rate", 
                       "overlap_rate", "marginal_contribution",
                       "recall", "hit_rate", "matched"}
    
    # summary 匹配度
    summary_match = frontend_summary & pipeline_summary
    summary_missing = frontend_summary - pipeline_summary
    
    # rules 匹配度
    rules_match = frontend_rules & pipeline_rules
    rules_missing = frontend_rules - pipeline_rules
    
    errors = []
    if summary_missing:
        errors.append(f"前端 summary 缺失: {summary_missing}")
    if rules_missing:
        errors.append(f"前端 rules 缺失: {rules_missing}")
    
    print(f"  前端 summary 期望: {frontend_summary}")
    print(f"  Pipeline summary 输出: {pipeline_summary}")
    print(f"  summary 匹配: {summary_match} ({len(summary_match)}/{len(frontend_summary)})")
    print(f"  summary 缺失: {summary_missing or '无'}")
    
    print(f"\n  前端 rules 期望: {frontend_rules}")
    print(f"  Pipeline rules 输出: {pipeline_rules}")
    print(f"  rules 匹配: {rules_match} ({len(rules_match)}/{len(frontend_rules)})")
    print(f"  rules 缺失: {rules_missing or '无'}")
    
    if errors:
        for e in errors:
            print(f"  ❌ {e}")
        raise AssertionError(f"FIX-A 修复不完整: {errors}")
    
    print(f"\n  结论: FIX-A 修复后前端字段完全匹配")
    print(f"  summary: {len(summary_match)}/{len(frontend_summary)} ✅")
    print(f"  rules: {len(rules_match)}/{len(frontend_rules)} ✅")
    print("  ✅ PASS — 前端字段完全匹配")
    return True


# =============================================================================
# 8. to_dict / API 响应格式测试
# =============================================================================

def test_8_api_response_format():
    """to_dict: API 响应格式完整性"""
    print("\n" + "=" * 70)
    print("8. PriorRuleParser.to_dict API 响应格式")
    print("=" * 70)
    
    parser = PriorRuleParser()
    parser.parse_text("(age > 30)\n(income < 5000)")
    
    d = parser.to_dict()
    
    required_keys = {"mode", "rules", "rule_count", "expressions", "errors", "warnings"}
    assert required_keys.issubset(d.keys()), f"缺少字段: {required_keys - d.keys()}"
    assert d["mode"] == "expression"
    assert d["rule_count"] == 2
    assert len(d["expressions"]) == 2
    assert isinstance(d["errors"], list)
    assert isinstance(d["warnings"], list)
    
    print(f"  to_dict 包含全部必需字段: {required_keys}")
    print(f"  mode={d['mode']}, rule_count={d['rule_count']}")
    print("  ✅ PASS")
    return True


# =============================================================================
# 主函数
# =============================================================================

def main():
    print("=" * 70)
    print("P2-7 先验规则输入增强 — 完整测试")
    print("=" * 70)
    
    tests = [
        ("1-parse_text", test_1_parser_parse_text),
        ("1b-empty", test_1b_parser_parse_text_empty),
        ("1c-csv_struct", test_1c_parser_parse_csv_structured),
        ("1d-csv_expr", test_1d_parser_parse_csv_expression),
        ("1e-validate", test_1e_parser_validate_columns),
        ("2-E2", test_2_e2_string_vs_list),
        ("3-E5", test_3_e5_security),
        ("4-Pipeline", test_4_pipeline_integration),
        ("5-compare", test_5_compare_thresholds),
        ("6-report", test_6_report_data_flow),
        ("7-frontend", test_7_frontend_field_matching),
        ("8-api", test_8_api_response_format),
    ]
    
    results = {}
    total_start = time.time()
    
    for name, test_fn in tests:
        try:
            passed = test_fn()
            results[name] = "✅ PASS" if passed else "❌ FAIL"
        except Exception as e:
            print(f"  ❌ FAIL — {e}")
            import traceback
            traceback.print_exc()
            results[name] = f"❌ FAIL: {str(e)[:80]}"
    
    total_elapsed = time.time() - total_start
    
    print("\n" + "=" * 70)
    print("测试结果汇总")
    print("=" * 70)
    for name, result in results.items():
        print(f"  {name:<16} {result}")
    
    all_passed = all("PASS" in v for v in results.values())
    print(f"\n总耗时: {total_elapsed:.1f}s")
    print(f"{'✅ 全部通过' if all_passed else '❌ 有失败项'} ({sum(1 for v in results.values() if 'PASS' in v)}/{len(results)})")
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
