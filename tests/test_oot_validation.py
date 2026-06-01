"""
P1-5 OOT 验证功能 — 自动化测试脚本（Phase 6）

覆盖设计文档 TC001-TC008：
  1. TC001: sample_type_col 手动划分（含 oot 标注）
  2. TC002: time_col + oot_ratio 智能 OOT 划分
  3. TC003: time_col + oot_ratio=0 不划分 OOT
  4. TC004: test_ratio=0 全量训练
  5. TC005: enable_oot_validation=true CV 计算正确性
  6. TC006: enable_stability_filter=true 不稳定规则过滤
  7. TC007: 旧任务兼容（无 time_col/oot_ratio）
  8. TC008: 前端字段匹配验证（oot_stability_report 结构）

数据集: workspace/session_1768786483478_njde0oyfu/zhongbang_sample.csv

运行方式:
  cd workspace/DeepAnalyze
  .venv/Scripts/python.exe tests/test_oot_validation.py
"""

import os
import sys
import time
import warnings
import io
from pathlib import Path

import numpy as np
import pandas as pd

# 修复 Windows GBK 编码问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Setup
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)
warnings.filterwarnings("ignore")

DATA_FILE = "workspace/session_1768786483478_njde0oyfu/zhongbang_sample.csv"
TARGET_COL = "target"
# zhongbang 数据集中的非特征列（ID、时间、分类标注等需要排除）
EXCLUDE_COLS = ['number', 'riskid', 'id', 'product', 'applytime', 'dcmonths', 'sample_type']

# 测试结果
results: list[tuple[str, bool, str]] = []


def run_test(test_id: str, test_name: str, test_fn):
    """运行单个测试"""
    print(f"\n{'=' * 70}")
    print(f"{test_id}. {test_name}")
    print("=" * 70)
    try:
        test_fn()
        results.append((test_id, True, test_name))
        print(f"  ✅ PASS")
    except Exception as e:
        results.append((test_id, False, f"{test_name}: {e}"))
        print(f"  ❌ FAIL: {e}")


def load_data(nrows=10000):
    """加载数据并预清理"""
    df = pd.read_csv(DATA_FILE, nrows=nrows, low_memory=False)
    assert TARGET_COL in df.columns, f"缺少目标列 {TARGET_COL}"
    # 只保留数值列 + target + applytime
    num_cols = list(df.select_dtypes(include='number').columns)
    keep = list(dict.fromkeys([TARGET_COL, 'applytime'] + num_cols))
    df = df[[c for c in keep if c in df.columns]].copy()
    for c in df.select_dtypes(include='number').columns:
        df[c] = df[c].fillna(-1).astype(float)
    return df


def run_pipeline(df, pipeline=None, **kwargs):
    """统一运行 Pipeline（跳过预处理以避免 one-hot/IV 筛选干扰，OOT 划分在 run 内部提前处理）"""
    if pipeline is None:
        pipeline = get_pipeline()
    feature_cols = [c for c in df.select_dtypes(include='number').columns 
                    if c not in {TARGET_COL} | set(EXCLUDE_COLS)][:50]
    kwargs.setdefault('feature_cols', feature_cols)
    kwargs.setdefault('exclude_cols', EXCLUDE_COLS)
    print(f"  [DEBUG] enable_oot={kwargs.get('enable_oot_validation')}, "
          f"sample_type_col={kwargs.get('sample_type_col')}, "
          f"time_col={kwargs.get('time_col')}, oot_ratio={kwargs.get('oot_ratio')}, "
          f"features={len(feature_cols)}")
    result = pipeline.run(df, target_col=TARGET_COL, **kwargs)
    oot = result.get('oot_data')
    print(f"  [DEBUG] oot_data={'exists('+str(len(oot))+')' if oot is not None else 'None'}, "
          f"optimal_rules={len(result.get('optimal_rules',[])) if result.get('optimal_rules') is not None else 0}, "
          f"oot_report={'exists' if result.get('oot_stability_report') else 'None'}")
    return result


def get_pipeline(**kwargs):
    """创建 Pipeline 实例（宽松参数确保能挖出规则）"""
    from deepanalyze.analysis.task_SOP.rule_mining import RuleMiningPipeline
    defaults = dict(
        mining_mode="multi",
        max_depth=3,
        n_vars=2,
        min_lift_filter=1.0,        # 宽松：不过滤低 lift
        max_hit_rate_filter=0.50,    # 宽松
        min_lift_ruleset=1.0,
        max_hit_rate_select=0.50,
    )
    defaults.update(kwargs)
    return RuleMiningPipeline(**defaults)


def add_sample_type_col(df, train_ratio=0.6, test_ratio=0.2):
    """添加字符串 sample_type 列（'train'/'test'/'oot'）— split_data 期望字符串标签"""
    n = len(df)
    n_train = int(n * train_ratio)
    n_test = int(n * test_ratio)
    labels = ['train'] * n_train + ['test'] * n_test + ['oot'] * (n - n_train - n_test)
    np.random.shuffle(labels)
    df['sample_type'] = labels
    return df


# =============================================================================
# TC001: sample_type_col 手动划分（含 oot 标注）
# =============================================================================
def test_tc001():
    """sample_type_col 包含 oot 标注 → 按列值划分 train/test/oot"""
    df = load_data()
    add_sample_type_col(df)
    
    result = run_pipeline(df, sample_type_col='sample_type', enable_oot_validation=True, test_ratio=0.2)
    
    assert result.get('oot_data') is not None and len(result['oot_data']) > 0, "oot_data 为空"
    report = result.get('oot_stability_report')
    assert report is not None, "oot_stability_report 为 None"
    assert 'overall_hit_rate' in report and 'rule_stability' in report
    
    print(f"  train: {len(result['train_data'])}, test: {len(result['test_data'])}, oot: {len(result['oot_data'])}")
    print(f"  OOT overall CV: {report['overall_hit_rate'].get('cv', 'N/A')}")
    print(f"  稳定性分布: {report.get('stability_counts', {})}")


# =============================================================================
# TC002: time_col + oot_ratio 智能 OOT 划分
# =============================================================================
def test_tc002():
    """time_col + oot_ratio=0.15 → 最近 15% 数据作为 OOT"""
    df = load_data()
    result = run_pipeline(df, time_col='applytime', oot_ratio=0.15, test_ratio=0.2, enable_oot_validation=True)
    
    oot_df = result.get('oot_data')
    assert oot_df is not None, "oot_data 为 None"
    oot_ratio_actual = len(oot_df) / len(df)
    print(f"  OOT 实际占比: {oot_ratio_actual:.2%} (期望 ~15%)")
    assert 0.05 < oot_ratio_actual < 0.30, f"OOT 占比异常: {oot_ratio_actual:.2%}"
    
    report = result.get('oot_stability_report')
    assert report is not None, "oot_stability_report 为 None"
    print(f"  OOT 样本数: {len(oot_df)}, overall CV: {report['overall_hit_rate']['cv']}")


# =============================================================================
# TC003: time_col + oot_ratio=0 不划分 OOT
# =============================================================================
def test_tc003():
    """time_col + oot_ratio=0 → 不划分 OOT"""
    df = load_data()
    result = run_pipeline(df, time_col='applytime', oot_ratio=0.0, test_ratio=0.2)
    
    has_oot = result.get('oot_data') is not None and len(result.get('oot_data', [])) > 0
    print(f"  oot_data 存在: {has_oot}")
    assert not has_oot, "oot_ratio=0 但仍有 OOT 数据"
    assert result.get('oot_stability_report') is None, "不应有 oot_stability_report"


# =============================================================================
# TC004: test_ratio=0 全量训练
# =============================================================================
def test_tc004():
    """test_ratio=0 → 全部作为训练集"""
    df = load_data()
    result = run_pipeline(df, test_ratio=0.0)
    
    train_df = result.get('train_data')
    test_df = result.get('test_data')
    print(f"  train: {len(train_df) if train_df is not None else 'None'}")
    print(f"  test: {len(test_df) if test_df is not None else 'None'}")
    
    optimal = result.get('optimal_rules')
    assert optimal is not None and len(optimal) > 0, "无最优规则"
    print(f"  最优规则: {len(optimal)} 条")


# =============================================================================
# TC005: enable_oot_validation=true CV 计算正确性
# =============================================================================
def test_tc005():
    """enable_oot_validation=true → CV 计算正确性验证"""
    df = load_data()
    add_sample_type_col(df)
    
    result = run_pipeline(df, sample_type_col='sample_type', enable_oot_validation=True, cv_threshold=0.35, test_ratio=0.2)
    report = result.get('oot_stability_report')
    assert report is not None, "oot_stability_report 为 None"
    
    overall = report['overall_hit_rate']
    for field in ['cv', 'train', 'test', 'oot']:
        assert field in overall, f"overall_hit_rate 缺少 {field}"
    
    rules = report['rule_stability']
    assert len(rules) > 0, "rule_stability 为空"
    r0 = rules[0]
    for field in ['rule', 'hit_rate_train', 'hit_rate_test', 'hit_rate_oot', 'cv', 'stability_level']:
        assert field in r0, f"rule_stability[0] 缺少 {field}"
    
    # 手动验证 CV 计算
    rates = [r0['hit_rate_train'], r0['hit_rate_test'], r0['hit_rate_oot']]
    rates_nz = [r for r in rates if r > 0]
    if len(rates_nz) >= 2:
        manual_cv = float(np.std(rates_nz) / np.mean(rates_nz))
        print(f"  手动 CV: {manual_cv:.4f}, Pipeline CV: {r0['cv']:.4f}")
        assert abs(manual_cv - r0['cv']) < 0.01, f"CV 偏差过大"
    
    print(f"  Overall CV: {overall['cv']:.4f}, 规则数: {len(rules)}")


# =============================================================================
# TC006: enable_stability_filter=true 不稳定规则过滤
# =============================================================================
def test_tc006():
    """enable_stability_filter=true → 不稳定规则被过滤"""
    df = load_data()
    add_sample_type_col(df)
    
    r1 = run_pipeline(df.copy(), sample_type_col='sample_type', enable_oot_validation=True, enable_stability_filter=False, cv_threshold=0.2, test_ratio=0.2)
    r2 = run_pipeline(df.copy(), sample_type_col='sample_type', enable_oot_validation=True, enable_stability_filter=True, cv_threshold=0.2, test_ratio=0.2)
    
    c1 = len(r1.get('optimal_rules', []))
    c2 = len(r2.get('optimal_rules', []))
    unstable = len(r2.get('oot_stability_report', {}).get('unstable_rules', []))
    
    print(f"  不过滤: {c1} 条, 过滤后: {c2} 条, 不稳定: {unstable}")
    assert c2 <= c1, f"过滤后规则数({c2})多于不过滤({c1})"


# =============================================================================
# TC007: 旧任务兼容（无 time_col/oot_ratio）
# =============================================================================
def test_tc007():
    """旧任务（无 OOT 参数）→ 正常运行"""
    df = load_data()
    result = run_pipeline(df, test_ratio=0.2)
    
    optimal = result.get('optimal_rules')
    assert optimal is not None and len(optimal) > 0, "无最优规则"
    assert result.get('oot_stability_report') is None, "不应有 oot_stability_report"
    print(f"  最优规则: {len(optimal)} 条, oot_report: None ✓")


# =============================================================================
# TC008: 前端字段匹配验证
# =============================================================================
def test_tc008():
    """前端 ootStabilityReport 期望字段完整性"""
    df = load_data()
    add_sample_type_col(df)
    
    result = run_pipeline(df, sample_type_col='sample_type', enable_oot_validation=True, test_ratio=0.2)
    report = result.get('oot_stability_report')
    assert report is not None
    
    # 顶层字段
    for f in ['overall_hit_rate', 'rule_stability', 'stability_counts', 'stability_score_bonus', 'cv_threshold', 'oot_samples', 'unstable_rules']:
        assert f in report, f"缺少 {f}"
    
    # overall_hit_rate 子字段
    for f in ['train', 'test', 'oot', 'cv']:
        assert f in report['overall_hit_rate'], f"overall_hit_rate 缺少 {f}"
    
    # stability_counts 子字段
    for f in ['highly_stable', 'stable', 'moderate', 'unstable']:
        assert f in report['stability_counts'], f"stability_counts 缺少 {f}"
    
    # rule_stability 每条规则字段
    if report['rule_stability']:
        r0 = report['rule_stability'][0]
        for f in ['rule', 'hit_rate_train', 'hit_rate_test', 'hit_rate_oot', 'cv', 'stability_level']:
            assert f in r0, f"rule_stability[0] 缺少 {f}"
    
    bonus = report['stability_score_bonus']
    assert bonus in (-5, 0, 5, 10), f"bonus 值异常: {bonus}"
    
    print(f"  所有前端期望字段完全匹配 ✓")
    print(f"  bonus: {bonus}, oot_samples: {report['oot_samples']}")


# =============================================================================
# 主入口
# =============================================================================
if __name__ == "__main__":
    start_time = time.time()
    
    print("=" * 70)
    print("P1-5 OOT 验证功能测试（Phase 6）")
    print(f"数据集: {DATA_FILE}")
    print("=" * 70)
    
    run_test("TC001", "sample_type_col 手动划分（含 oot 标注）", test_tc001)
    run_test("TC002", "time_col + oot_ratio 智能 OOT 划分", test_tc002)
    run_test("TC003", "time_col + oot_ratio=0 不划分 OOT", test_tc003)
    run_test("TC004", "test_ratio=0 全量训练", test_tc004)
    run_test("TC005", "enable_oot_validation CV 计算正确性", test_tc005)
    run_test("TC006", "enable_stability_filter 不稳定规则过滤", test_tc006)
    run_test("TC007", "旧任务兼容（无 OOT 参数）", test_tc007)
    run_test("TC008", "前端字段匹配验证", test_tc008)
    
    elapsed = time.time() - start_time
    
    print(f"\n{'=' * 70}")
    print(f"测试结果汇总")
    print(f"{'=' * 70}")
    
    passed = sum(1 for _, ok, _ in results if ok)
    failed = sum(1 for _, ok, _ in results if not ok)
    
    for test_id, ok, msg in results:
        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"  {test_id}: {status} — {msg}")
    
    print(f"\n总计: {passed}/{len(results)} 通过, {failed} 失败")
    print(f"总耗时: {elapsed:.1f}s")
    
    if failed > 0:
        print("\n⚠ 有测试失败!")
        sys.exit(1)
    else:
        print("\n🎉 全部通过!")
        sys.exit(0)
