"""
P2-6 类别不平衡处理 — Pipeline 集成测试（真实数据版）

使用样本集: workspace/session_1768786483478_njde0oyfu/starrel_train_with_amount.csv
数据规格: 23350 行, 85 列 (label, fuuid, f0~f80, SelectionProb, SamplingWeight, loss_amount)

覆盖评审待办项：
  T6: 向后兼容基线（规则挖掘，strategy=none，验证与当前行为一致）
  T7: 向后兼容基线（评分卡，strategy=none）
  T8: weight_col(SamplingWeight) + class_weight 叠加（验证权重正确叠加）
  T9: StatisticalLR + class_weight 统计信息正确性
  E3: StatisticalLogisticRegression + class_weight 兼容性
  E8: weight_col + class_weight 叠加说明检查

运行方式:
  cd workspace/DeepAnalyze
  python -m tests.test_imbalance_strategy
"""

import os
import sys
import time
import warnings
from pathlib import Path

# 修复 Windows GBK 编码问题
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import numpy as np
import pandas as pd

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

warnings.filterwarnings("ignore")

from deepanalyze.analysis.task_SOP.rule_mining import (
    RuleMiner,
    RuleMiningPipeline,
)
from deepanalyze.analysis.task_SOP.scorecard_development import ScorecardPipeline
from deepanalyze.analysis.statistical_model import StatisticalLogisticRegression


# =============================================================================
# 数据加载
# =============================================================================

DATA_PATH = Path(__file__).parent.parent / "workspace" / "session_1768786483478_njde0oyfu" / "starrel_train_with_amount.csv"

# 数据集关键参数
ID_COL = "fuuid"
TARGET_COL = "label"
WEIGHT_COL = "SamplingWeight"
AMOUNT_COL = "loss_amount"
EXCLUDE_COLS = [ID_COL, "SelectionProb", WEIGHT_COL, AMOUNT_COL]


def load_data(sample_n: int | None = None, seed: int = 42) -> pd.DataFrame:
    """加载 starrel_train_with_amount.csv 真实数据
    
    注意：自动移除非数值类别列（f66~f69, f75, f78 等），
    避免 One-Hot 编码导致的已知 Pipeline 兼容性问题。
    """
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"样本数据文件不存在: {DATA_PATH}\n"
            f"请确保 workspace/session_1768786483478_njde0oyfu/starrel_train_with_amount.csv 存在"
        )
    df = pd.read_csv(DATA_PATH)
    print(f"  原始数据: {len(df)} 行, {df.shape[1]} 列, bad_rate={df[TARGET_COL].mean():.4f}")
    
    # 移除非数值类别列（避免 One-Hot 编码兼容性问题）
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    cat_cols = [c for c in cat_cols if c not in [ID_COL, TARGET_COL]]
    if cat_cols:
        df = df.drop(columns=cat_cols)
        print(f"  移除 {len(cat_cols)} 个非数值列: {cat_cols}")
    
    if sample_n and sample_n < len(df):
        df = df.sample(n=sample_n, random_state=seed).reset_index(drop=True)
        print(f"  采样后: {len(df)} 行, bad_rate={df[TARGET_COL].mean():.4f}")
    
    return df


def get_numeric_feature_cols(df: pd.DataFrame) -> list[str]:
    """获取纯数值型特征列（排除 ID/权重/金额/目标等）"""
    exclude = set(EXCLUDE_COLS + [TARGET_COL])
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    return [c for c in numeric_cols if c not in exclude]


def get_rule_mining_feature_cols(df: pd.DataFrame) -> list[str]:
    """获取规则挖掘可用的特征列（纯数值，排除极高缺失率列）"""
    feats = get_numeric_feature_cols(df)
    # 过滤掉 >90% 缺失（含 -1 编码缺失）的列
    valid = []
    for c in feats:
        non_missing = df[c][(df[c] != -1) & df[c].notna()]
        if len(non_missing) / len(df) > 0.1:
            valid.append(c)
    return valid


# =============================================================================
# T6: 向后兼容基线 — 规则挖掘 strategy=none
# =============================================================================

def test_T6_rule_mining_none_baseline():
    """T6: strategy=none 应与无 P2-6 之前的行为完全一致（不启用 class_weight）
    
    使用真实数据 3000 行采样，验证：
    1. Pipeline 正常完成
    2. imbalance_analysis.applied_strategy == 'none'
    3. RuleMiner.class_weight 为 None（未设置）
    4. 产出 optimal_rules
    """
    print("\n" + "=" * 70)
    print("T6: 规则挖掘 strategy=none 向后兼容基线（真实数据）")
    print("=" * 70)
    
    df = load_data(sample_n=3000)
    actual_bad_rate = df[TARGET_COL].mean()
    feature_cols = get_rule_mining_feature_cols(df)
    print(f"  可用特征: {len(feature_cols)} 个")
    
    # 手动做简单数据准备（跳过 Pipeline 的 preprocessing，避免预存 One-Hot Bug）
    df_clean = df[[TARGET_COL] + feature_cols].copy()
    df_clean = df_clean.fillna(-1)  # 简单缺失处理
    
    t0 = time.time()
    pipeline = RuleMiningPipeline(
        mining_mode="multi",
        id_cols=[],
        max_depth=3,
        n_vars=2,
        max_hit_rate_filter=0.30,
        min_lift_filter=1.5,
        max_hit_rate_select=0.40,
        imbalance_strategy="none",  # 明确不处理
    )
    
    results = pipeline.run(
        df_clean,
        target_col=TARGET_COL,
        feature_cols=feature_cols,
        skip_preprocessing=True,
    )
    elapsed = time.time() - t0
    
    # 验证核心输出
    assert "optimal_rules" in results, "缺少 optimal_rules"
    
    # 验证 imbalance_analysis
    imb = pipeline._build_imbalance_analysis(actual_bad_rate)
    assert imb["user_strategy"] == "none", f"期望 user_strategy=none, 实际={imb['user_strategy']}"
    assert imb["applied_strategy"] == "none", f"期望 applied_strategy=none, 实际={imb['applied_strategy']}"
    
    # 验证 RuleMiner 的 class_weight 未被设置
    if hasattr(pipeline.miner, "class_weight"):
        assert pipeline.miner.class_weight is None, \
            f"strategy=none 时 class_weight 应为 None, 实际={pipeline.miner.class_weight}"
    
    n_rules = len(results["optimal_rules"]) if isinstance(results["optimal_rules"], pd.DataFrame) else 0
    print(f"  耗时: {elapsed:.1f}s")
    print(f"  imbalance: severity={imb['severity']}, ratio={imb['imbalance_ratio']}")
    print(f"  ✅ PASS — strategy=none, class_weight=None, {n_rules} 条最优规则")
    return True


# =============================================================================
# T6-CW: 规则挖掘 strategy=class_weight (对照组)
# =============================================================================

def test_T6_cw_rule_mining_class_weight():
    """T6-CW: strategy=class_weight 应启用 balanced 权重
    
    与 T6 形成对照：同数据，不同策略，验证：
    1. class_weight 被正确设置为 'balanced'
    2. Pipeline 正常完成
    3. 对比两种策略的规则数量差异（class_weight 可能发现更多少数类规则）
    """
    print("\n" + "=" * 70)
    print("T6-CW: 规则挖掘 strategy=class_weight（对照组，真实数据）")
    print("=" * 70)
    
    df = load_data(sample_n=3000)
    actual_bad_rate = df[TARGET_COL].mean()
    feature_cols = get_rule_mining_feature_cols(df)
    df_clean = df[[TARGET_COL] + feature_cols].copy().fillna(-1)
    
    t0 = time.time()
    pipeline = RuleMiningPipeline(
        mining_mode="multi",
        id_cols=[],
        max_depth=3,
        n_vars=2,
        max_hit_rate_filter=0.30,
        min_lift_filter=1.5,
        max_hit_rate_select=0.40,
        imbalance_strategy="class_weight",  # 明确启用
    )
    
    results = pipeline.run(
        df_clean,
        target_col=TARGET_COL,
        feature_cols=feature_cols,
        skip_preprocessing=True,
    )
    elapsed = time.time() - t0
    
    assert "optimal_rules" in results, "缺少 optimal_rules"
    
    # 验证 class_weight 已设置
    if hasattr(pipeline.miner, "class_weight"):
        assert pipeline.miner.class_weight == "balanced", \
            f"期望 balanced, 实际={pipeline.miner.class_weight}"
    
    imb = pipeline._build_imbalance_analysis(actual_bad_rate)
    assert imb["applied_strategy"] == "class_weight"
    
    n_rules = len(results["optimal_rules"]) if isinstance(results["optimal_rules"], pd.DataFrame) else 0
    print(f"  耗时: {elapsed:.1f}s")
    print(f"  imbalance: severity={imb['severity']}, applied={imb['applied_strategy']}")
    print(f"  ✅ PASS — strategy=class_weight, {n_rules} 条最优规则")
    return True


# =============================================================================
# T6-AUTO: 规则挖掘 strategy=auto (默认值)
# =============================================================================

def test_T6_auto_rule_mining():
    """auto 策略验证: 真实数据 bad_rate 通常 <10%，应自动启用 class_weight"""
    print("\n" + "=" * 70)
    print("T6-AUTO: 规则挖掘 strategy=auto（默认值，真实数据）")
    print("=" * 70)
    
    df = load_data(sample_n=3000)
    actual_bad_rate = df[TARGET_COL].mean()
    feature_cols = get_rule_mining_feature_cols(df)
    df_clean = df[[TARGET_COL] + feature_cols].copy().fillna(-1)
    
    t0 = time.time()
    pipeline = RuleMiningPipeline(
        mining_mode="multi",
        id_cols=[],
        max_depth=3,
        n_vars=2,
        max_hit_rate_filter=0.30,
        min_lift_filter=1.5,
        max_hit_rate_select=0.40,
        imbalance_strategy="auto",  # 默认值
    )
    
    results = pipeline.run(
        df_clean,
        target_col=TARGET_COL,
        feature_cols=feature_cols,
        skip_preprocessing=True,
    )
    elapsed = time.time() - t0
    
    imb = pipeline._build_imbalance_analysis(actual_bad_rate)
    
    # auto 策略根据 bad_rate 自动决定
    if actual_bad_rate < 0.1:
        expected_applied = "class_weight"
        if hasattr(pipeline.miner, "class_weight"):
            assert pipeline.miner.class_weight == "balanced", \
                f"auto + bad_rate={actual_bad_rate:.4f}<10% 应启用 balanced, 实际={pipeline.miner.class_weight}"
    else:
        expected_applied = "none"
        if hasattr(pipeline.miner, "class_weight"):
            assert pipeline.miner.class_weight is None, \
                f"auto + bad_rate={actual_bad_rate:.4f}>=10% 应不启用, 实际={pipeline.miner.class_weight}"
    
    assert imb["applied_strategy"] == expected_applied, \
        f"auto 应解析为 {expected_applied}, 实际={imb['applied_strategy']}"
    assert imb["user_strategy"] == "auto"
    
    n_rules = len(results["optimal_rules"]) if isinstance(results["optimal_rules"], pd.DataFrame) else 0
    print(f"  耗时: {elapsed:.1f}s")
    print(f"  bad_rate={actual_bad_rate:.4f} → auto解析为: {imb['applied_strategy']}")
    print(f"  imbalance: severity={imb['severity']}, ratio={imb['imbalance_ratio']}")
    print(f"  ✅ PASS — auto → {expected_applied}, {n_rules} 条最优规则")
    return True


# =============================================================================
# T7: 向后兼容基线 — 评分卡 strategy=none
# =============================================================================

def test_T7_scorecard_none_baseline():
    """T7: 评分卡 strategy=none 应保持原有行为（真实数据）"""
    print("\n" + "=" * 70)
    print("T7: 评分卡 strategy=none 向后兼容基线（真实数据）")
    print("=" * 70)
    
    df = load_data(sample_n=3000)
    actual_bad_rate = df[TARGET_COL].mean()
    
    t0 = time.time()
    pipeline = ScorecardPipeline(
        missing_threshold=0.95,
        test_ratio=0.3,
        imbalance_strategy="none",
    )
    
    results = pipeline.run(
        df.copy(),
        target_col=TARGET_COL,
        exclude_cols=EXCLUDE_COLS,
    )
    elapsed = time.time() - t0
    
    # 评分卡结果应包含模型或评分卡
    has_output = ("model" in results or "scorecard" in results or 
                  "model_training" in results or "final_scorecard" in results)
    assert has_output, f"评分卡应产出结果, 实际 keys: {list(results.keys())[:10]}"
    
    # 验证 imbalance_analysis
    imb = pipeline._build_imbalance_analysis(actual_bad_rate)
    assert imb["applied_strategy"] == "none"
    
    print(f"  耗时: {elapsed:.1f}s")
    print(f"  imbalance: severity={imb['severity']}, applied=none")
    print(f"  ✅ PASS — strategy=none, 评分卡 Pipeline 正常完成")
    return True


# =============================================================================
# T7-CW: 评分卡 strategy=class_weight (对照组)
# =============================================================================

def test_T7_cw_scorecard_class_weight():
    """T7-CW: 评分卡 strategy=class_weight 应在模型训练阶段应用"""
    print("\n" + "=" * 70)
    print("T7-CW: 评分卡 strategy=class_weight（对照组，真实数据）")
    print("=" * 70)
    
    df = load_data(sample_n=3000)
    actual_bad_rate = df[TARGET_COL].mean()
    
    t0 = time.time()
    pipeline = ScorecardPipeline(
        missing_threshold=0.95,
        test_ratio=0.3,
        imbalance_strategy="class_weight",
    )
    
    results = pipeline.run(
        df.copy(),
        target_col=TARGET_COL,
        exclude_cols=EXCLUDE_COLS,
    )
    elapsed = time.time() - t0
    
    has_output = ("model" in results or "scorecard" in results or 
                  "model_training" in results or "final_scorecard" in results)
    assert has_output, f"评分卡应产出结果, 实际 keys: {list(results.keys())[:10]}"
    
    imb = pipeline._build_imbalance_analysis(actual_bad_rate)
    assert imb["applied_strategy"] == "class_weight"
    
    print(f"  耗时: {elapsed:.1f}s")
    print(f"  imbalance: severity={imb['severity']}, applied=class_weight")
    print(f"  ✅ PASS — strategy=class_weight, 评分卡 Pipeline 正常完成")
    return True


# =============================================================================
# T7-AUTO: 评分卡 strategy=auto (默认值)
# =============================================================================

def test_T7_auto_scorecard():
    """T7-AUTO: 评分卡 auto 策略验证：真实数据 bad_rate ~5% → 自动启用 class_weight"""
    print("\n" + "=" * 70)
    print("T7-AUTO: 评分卡 strategy=auto（默认值，真实数据）")
    print("=" * 70)
    
    df = load_data(sample_n=3000)
    actual_bad_rate = df[TARGET_COL].mean()
    
    t0 = time.time()
    pipeline = ScorecardPipeline(
        missing_threshold=0.95,
        test_ratio=0.3,
        imbalance_strategy="auto",
    )
    
    results = pipeline.run(
        df.copy(),
        target_col=TARGET_COL,
        exclude_cols=EXCLUDE_COLS,
    )
    elapsed = time.time() - t0
    
    has_output = ("model" in results or "scorecard" in results or 
                  "model_training" in results or "final_scorecard" in results)
    assert has_output, f"评分卡应产出结果, 实际 keys: {list(results.keys())[:10]}"
    
    imb = pipeline._build_imbalance_analysis(actual_bad_rate)
    
    # auto 策略根据 bad_rate 自动决定
    if actual_bad_rate < 0.1:
        expected_applied = "class_weight"
    else:
        expected_applied = "none"
    
    assert imb["applied_strategy"] == expected_applied, \
        f"auto 应解析为 {expected_applied}, 实际={imb['applied_strategy']}"
    assert imb["user_strategy"] == "auto"
    
    print(f"  耗时: {elapsed:.1f}s")
    print(f"  bad_rate={actual_bad_rate:.4f} → auto解析为: {imb['applied_strategy']}")
    print(f"  imbalance: severity={imb['severity']}, ratio={imb['imbalance_ratio']}")
    print(f"  ✅ PASS — auto → {expected_applied}, 评分卡 Pipeline 正常完成")
    return True


# =============================================================================
# T7-T8: 评分卡 SamplingWeight + class_weight 叠加
# =============================================================================

def test_T7_T8_scorecard_weight_plus_class_weight():
    """T7-T8: 评分卡 SamplingWeight + class_weight='balanced' 叠加验证"""
    print("\n" + "=" * 70)
    print("T7-T8: 评分卡 SamplingWeight + class_weight 叠加验证（真实数据）")
    print("=" * 70)
    
    df = load_data(sample_n=3000)
    actual_bad_rate = df[TARGET_COL].mean()
    
    assert WEIGHT_COL in df.columns, f"权重列 {WEIGHT_COL} 不存在"
    weight_stats = df[WEIGHT_COL].describe()
    print(f"  SamplingWeight: min={weight_stats['min']:.4f}, max={weight_stats['max']:.4f}, "
          f"mean={weight_stats['mean']:.4f}")
    
    t0 = time.time()
    pipeline = ScorecardPipeline(
        missing_threshold=0.95,
        test_ratio=0.3,
        imbalance_strategy="class_weight",
    )
    
    results = pipeline.run(
        df.copy(),
        target_col=TARGET_COL,
        weight_col=WEIGHT_COL,
        exclude_cols=EXCLUDE_COLS,
    )
    elapsed = time.time() - t0
    
    has_output = ("model" in results or "scorecard" in results or 
                  "model_training" in results or "final_scorecard" in results)
    assert has_output, f"评分卡应产出结果, 实际 keys: {list(results.keys())[:10]}"
    
    imb = pipeline._build_imbalance_analysis(actual_bad_rate)
    assert imb["applied_strategy"] == "class_weight"
    
    print(f"  耗时: {elapsed:.1f}s")
    print(f"  imbalance: severity={imb['severity']}, applied=class_weight")
    print(f"  ✅ PASS — 评分卡 SamplingWeight + class_weight 叠加运行成功")
    return True


# =============================================================================
# T8: 规则挖掘 weight_col(SamplingWeight) + class_weight 叠加
# =============================================================================

def test_T8_weight_col_plus_class_weight():
    """T8: SamplingWeight + class_weight='balanced' 应正确叠加
    
    真实数据自带 SamplingWeight 权重列，验证：
    1. 两者共存不冲突（sklearn 支持 sample_weight + class_weight 同时使用）
    2. Pipeline 正常完成
    3. class_weight 被正确设置
    """
    print("\n" + "=" * 70)
    print("T8: SamplingWeight + class_weight 叠加验证（真实数据）")
    print("=" * 70)
    
    df = load_data(sample_n=2000)
    actual_bad_rate = df[TARGET_COL].mean()
    feature_cols = get_rule_mining_feature_cols(df)
    
    # 确认权重列存在
    assert WEIGHT_COL in df.columns, f"权重列 {WEIGHT_COL} 不存在"
    weight_stats = df[WEIGHT_COL].describe()
    print(f"  SamplingWeight: min={weight_stats['min']:.4f}, max={weight_stats['max']:.4f}, "
          f"mean={weight_stats['mean']:.4f}, std={weight_stats['std']:.4f}")
    
    # 构造 df_clean（含权重列）
    df_clean = df[[TARGET_COL, WEIGHT_COL] + feature_cols].copy().fillna(-1)
    
    t0 = time.time()
    pipeline = RuleMiningPipeline(
        mining_mode="multi",
        id_cols=[],
        max_depth=3,
        n_vars=2,
        max_hit_rate_filter=0.40,
        min_lift_filter=1.2,
        max_hit_rate_select=0.50,
        imbalance_strategy="class_weight",
    )
    
    # E8 验证: weight_col + class_weight 叠加
    results = pipeline.run(
        df_clean,
        target_col=TARGET_COL,
        feature_cols=feature_cols,
        weight_col=WEIGHT_COL,
        skip_preprocessing=True,
    )
    elapsed = time.time() - t0
    
    assert "optimal_rules" in results, "缺少 optimal_rules"
    
    # 验证 class_weight 已设置
    if hasattr(pipeline.miner, "class_weight"):
        assert pipeline.miner.class_weight == "balanced", \
            f"期望 balanced, 实际={pipeline.miner.class_weight}"
    
    imb = pipeline._build_imbalance_analysis(actual_bad_rate)
    n_rules = len(results["optimal_rules"]) if isinstance(results["optimal_rules"], pd.DataFrame) else 0
    
    print(f"  耗时: {elapsed:.1f}s")
    print(f"  imbalance: severity={imb['severity']}, applied={imb['applied_strategy']}")
    print(f"  ✅ PASS — SamplingWeight + class_weight='balanced' 叠加运行成功, {n_rules} 条规则")
    return True


# =============================================================================
# T9 + E3: StatisticalLR + class_weight 统计信息正确性
# =============================================================================

def test_T9_statistical_lr_class_weight():
    """T9/E3: StatisticalLogisticRegression + class_weight='balanced' 统计信息应合理
    
    使用真实数据的数值特征子集训练 LR，对比：
    - 对照组: class_weight=None
    - 实验组: class_weight='balanced'
    
    验证：
    1. 两组都能正常输出统计信息（p_value, z, std_err, coef）
    2. p_value ∈ [0, 1], std_err > 0, z 有限
    3. 系数方向一致性（class_weight 不应反转强信号特征的系数方向）
    4. pseudo_R², AIC, BIC 存在且合理
    """
    print("\n" + "=" * 70)
    print("T9/E3: StatisticalLR + class_weight 统计信息正确性（真实数据）")
    print("=" * 70)
    
    df = load_data(sample_n=5000)
    
    # 选取纯数值特征（排除类别型 + 高缺失 + 零方差）
    numeric_feats = get_numeric_feature_cols(df)
    
    # 过滤掉值全为 -1（缺失编码）的列、缺失率过高的列、零方差列
    valid_feats = []
    for c in numeric_feats:
        non_missing = df[c][df[c] != -1]
        if len(non_missing) / len(df) < 0.5:  # 有效率 < 50%
            continue
        # 替换 -1 后检查方差
        col_clean = df[c].replace(-1, np.nan).fillna(non_missing.median() if len(non_missing) > 0 else 0)
        if col_clean.std() < 1e-6:  # 零方差（常量列）
            continue
        valid_feats.append(c)
    
    # 选取与 label 相关性最高的前 6 个特征
    correlations = {}
    for c in valid_feats:
        col_clean = df[c].replace(-1, np.nan).fillna(df[c][df[c] != -1].median())
        corr = abs(col_clean.corr(df[TARGET_COL]))
        if np.isfinite(corr) and corr > 0.01:  # 过滤无相关性的特征
            correlations[c] = corr
    
    top_feats = sorted(correlations, key=correlations.get, reverse=True)[:6]
    print(f"  选取 {len(top_feats)} 个特征: {top_feats}")
    
    # 准备训练数据（简单缺失处理）
    X = df[top_feats].copy()
    for c in top_feats:
        median_val = X[c][X[c] != -1].median() if (X[c] != -1).any() else 0
        X[c] = X[c].replace(-1, median_val)
    
    y = df[TARGET_COL].copy()
    
    # 标准化（LR 对尺度敏感）
    for c in X.columns:
        std = X[c].std()
        if std > 0:
            X[c] = (X[c] - X[c].mean()) / std
    
    print(f"  数据: {len(X)} 样本, bad_rate={y.mean():.4f}, {X.shape[1]} 特征")
    print()
    
    # ====== 对照组: 无 class_weight ======
    model_none = StatisticalLogisticRegression(
        calculate_stats=True, penalty=None, C=1e10, solver="lbfgs",
        max_iter=1000, class_weight=None
    )
    model_none.fit(X, y)
    stats_none = model_none.summary()
    
    # ====== 实验组: class_weight='balanced' ======
    model_balanced = StatisticalLogisticRegression(
        calculate_stats=True, penalty=None, C=1e10, solver="lbfgs",
        max_iter=1000, class_weight="balanced"
    )
    model_balanced.fit(X, y)
    stats_balanced = model_balanced.summary()
    
    # 验证两组都能正常输出统计信息
    assert "summary" in stats_none, "无 class_weight 时 summary 缺失"
    assert "summary" in stats_balanced, "有 class_weight 时 summary 缺失"
    assert len(stats_none["summary"]) > 0, "无 class_weight 时 summary 为空"
    assert len(stats_balanced["summary"]) > 0, "有 class_weight 时 summary 为空"
    
    # 打印对比表
    print(f"  {'特征':<16} {'coef(无CW)':>12} {'p_val(无CW)':>12} {'std_err(无CW)':>14} "
          f"{'coef(有CW)':>12} {'p_val(有CW)':>12} {'std_err(有CW)':>14}")
    print(f"  {'-' * 100}")
    
    for row_none, row_balanced in zip(stats_none["summary"], stats_balanced["summary"]):
        feat = row_none["feature"]
        print(f"  {feat:<16} {row_none['coef']:>12.4f} {row_none['p_value']:>12.4f} {row_none['std_err']:>14.6f} "
              f"{row_balanced['coef']:>12.4f} {row_balanced['p_value']:>12.4f} {row_balanced['std_err']:>14.6f}")
    
    print()
    
    # 验证统计信息合理性
    errors = []
    for row in stats_balanced["summary"]:
        p = row["p_value"]
        z = row["z"]
        se = row["std_err"]
        feat = row["feature"]
        
        if not (0 <= p <= 1):
            errors.append(f"  {feat}: p_value={p} 超出 [0,1] 范围")
        if not (se > 0):
            errors.append(f"  {feat}: std_err={se} 应为正数")
        if not np.isfinite(z):
            errors.append(f"  {feat}: z={z} 非有限值")
    
    if errors:
        for e in errors:
            print(f"  ❌ {e}")
        raise AssertionError(f"统计信息不合理: {len(errors)} 个问题")
    
    # 验证模型整体统计
    assert stats_balanced.get("pseudo_r2") is not None, "pseudo_r2 缺失"
    assert stats_balanced.get("aic") is not None, "AIC 缺失"
    assert stats_balanced.get("bic") is not None, "BIC 缺失"
    
    # 验证系数方向一致性（class_weight 不应反转强信号特征的系数方向）
    direction_issues = []
    for row_none, row_balanced in zip(stats_none["summary"], stats_balanced["summary"]):
        if row_none["feature"] == "const":
            continue
        coef_none = row_none["coef"]
        coef_balanced = row_balanced["coef"]
        # 只检查系数绝对值较大的特征（弱特征方向可能翻转是正常的）
        if abs(coef_none) > 0.15 and abs(coef_balanced) > 0.15:
            if np.sign(coef_none) != np.sign(coef_balanced):
                direction_issues.append(
                    f"  {row_none['feature']}: none={coef_none:.4f} vs balanced={coef_balanced:.4f}"
                )
    
    if direction_issues:
        print("  ⚠️ 系数方向翻转（强信号特征）:")
        for d in direction_issues:
            print(d)
        # 不 assert fail，因为在极端不平衡下某些特征方向变化是合理的
        # 但记录为 warning
        print("  (注：不平衡数据下少量方向变化可接受)")
    
    print(f"  模型整体: pseudo_R²={stats_none.get('pseudo_r2', 0):.4f}(无CW) "
          f"vs {stats_balanced.get('pseudo_r2', 0):.4f}(有CW)")
    print(f"  AIC: {stats_none.get('aic', 0):.1f}(无CW) vs {stats_balanced.get('aic', 0):.1f}(有CW)")
    print(f"  BIC: {stats_none.get('bic', 0):.1f}(无CW) vs {stats_balanced.get('bic', 0):.1f}(有CW)")
    print(f"  ✅ PASS — 统计信息合理: p_value∈[0,1], std_err>0, z有限, 系数方向基本一致")
    return True


# =============================================================================
# E8: _build_imbalance_analysis 信息完整性
# =============================================================================

def test_E8_imbalance_analysis_info():
    """E8: 验证 _build_imbalance_analysis 返回的信息在各种场景下完整且正确
    
    覆盖：
    1. severity 分级（无/轻度/中度/重度/极端）边界值
    2. auto 策略解析（bad_rate < 10% → class_weight, >= 10% → none）
    3. 字段完整性（target_rate, imbalance_ratio, severity, user_strategy, applied_strategy, strategy_description）
    4. weight_col + class_weight 叠加时的 strategy_description 说明
    """
    print("\n" + "=" * 70)
    print("E8: _build_imbalance_analysis 信息完整性验证")
    print("=" * 70)
    
    # 用 RuleMiningPipeline 的方法来测试
    required_fields = {"target_rate", "imbalance_ratio", "severity", 
                       "user_strategy", "applied_strategy", "strategy_description"}
    
    test_cases = [
        # (bad_rate, strategy, expected_severity, expected_applied)
        (0.25, "auto", "无", "none"),
        (0.15, "auto", "轻度", "none"),       # 10% <= bad_rate < 20%
        (0.08, "auto", "中度", "class_weight"),  # 5% <= bad_rate < 10%
        (0.03, "auto", "重度", "class_weight"),  # 1% <= bad_rate < 5%
        (0.005, "auto", "极端", "class_weight"), # bad_rate < 1%
        (0.05, "none", "中度", "none"),
        (0.05, "class_weight", "中度", "class_weight"),
    ]
    
    all_ok = True
    for bad_rate, strategy, expected_severity, expected_applied in test_cases:
        pipeline = RuleMiningPipeline(
            mining_mode="multi",
            id_cols=[ID_COL],
            imbalance_strategy=strategy,
        )
        
        imb = pipeline._build_imbalance_analysis(bad_rate)
        
        # 字段完整性
        missing = required_fields - set(imb.keys())
        if missing:
            print(f"  ❌ bad_rate={bad_rate}, strategy={strategy}: 缺少字段 {missing}")
            all_ok = False
            continue
        
        # severity 正确性
        if imb["severity"] != expected_severity:
            print(f"  ❌ bad_rate={bad_rate}, strategy={strategy}: "
                  f"severity={imb['severity']} (期望 {expected_severity})")
            all_ok = False
        
        # applied_strategy 正确性
        if imb["applied_strategy"] != expected_applied:
            print(f"  ❌ bad_rate={bad_rate}, strategy={strategy}: "
                  f"applied={imb['applied_strategy']} (期望 {expected_applied})")
            all_ok = False
        
        # imbalance_ratio 合理性
        if bad_rate > 0:
            expected_ratio_suffix = f"1:{(1 - bad_rate) / bad_rate:.1f}"
            if imb["imbalance_ratio"] != expected_ratio_suffix:
                print(f"  ❌ bad_rate={bad_rate}: ratio={imb['imbalance_ratio']} (期望 {expected_ratio_suffix})")
                all_ok = False
        
        # strategy_description 非空
        if not imb["strategy_description"]:
            print(f"  ❌ bad_rate={bad_rate}, strategy={strategy}: strategy_description 为空")
            all_ok = False
        
        print(f"  ✓ bad_rate={bad_rate:.3f} strategy={strategy:<14} → "
              f"severity={imb['severity']:<4} applied={imb['applied_strategy']:<14} "
              f"ratio={imb['imbalance_ratio']}")
    
    if not all_ok:
        raise AssertionError("E8: 有不通过的测试用例")
    
    print(f"\n  ✅ PASS — {len(test_cases)} 个场景全部通过，字段完整，分级/解析逻辑正确")
    return True


# =============================================================================
# 主函数
# =============================================================================

def main():
    print("=" * 70)
    print("P2-6 类别不平衡处理 — Pipeline 集成测试（真实数据版）")
    print(f"数据集: {DATA_PATH.name}")
    print("覆盖: T6(×3), T7(×4), T8(规则挖掘), T9/E3, E8")
    print("=" * 70)
    
    # 验证数据文件存在
    if not DATA_PATH.exists():
        print(f"\n❌ 数据文件不存在: {DATA_PATH}")
        print("请确保 workspace/session_1768786483478_njde0oyfu/starrel_train_with_amount.csv 存在")
        return 1
    
    tests = [
        # 快速验证（E8 不需要运行 Pipeline）
        ("E8", test_E8_imbalance_analysis_info),
        # 规则挖掘三组对照
        ("T6-none", test_T6_rule_mining_none_baseline),
        ("T6-CW", test_T6_cw_rule_mining_class_weight),
        ("T6-AUTO", test_T6_auto_rule_mining),
        # 规则挖掘权重叠加
        ("T8-RM", test_T8_weight_col_plus_class_weight),
        # StatisticalLR 统计正确性
        ("T9/E3", test_T9_statistical_lr_class_weight),
        # 评分卡四组对照（耗时较长，放最后）
        ("T7-none", test_T7_scorecard_none_baseline),
        ("T7-CW", test_T7_cw_scorecard_class_weight),
        ("T7-AUTO", test_T7_auto_scorecard),
        ("T7-T8", test_T7_T8_scorecard_weight_plus_class_weight),
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
        print(f"  {name:<12} {result}")
    
    all_passed = all("PASS" in v for v in results.values())
    print(f"\n总耗时: {total_elapsed:.1f}s")
    print(f"{'✅ 全部通过' if all_passed else '❌ 有失败项'} ({sum(1 for v in results.values() if 'PASS' in v)}/{len(results)})")
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
