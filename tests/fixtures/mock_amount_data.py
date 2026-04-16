# -*- coding: utf-8 -*-
"""
Mock Amount Data Generator for Amount Analysis Testing (Phase 25 / P2-10)

Provides test data generation utilities for AmountAnalyzer and
RuleEvaluator.evaluate_with_amount testing.
"""

import numpy as np
import pandas as pd
from pathlib import Path


def generate_small_test_data(n: int = 100, seed: int = 42) -> pd.DataFrame:
    """
    生成小型测试数据集（用于单元测试，不依赖外部 CSV）。
    
    包含数值特征 f0-f4 + label + mock_amount。
    bad_rate ≈ 10%。
    """
    np.random.seed(seed)
    
    df = pd.DataFrame({
        "f0": np.random.choice([-1, 0, 1, 2, 3], n),
        "f1": np.round(np.random.normal(0, 1, n), 2),
        "f2": np.random.randint(0, 10, n),
        "f3": np.random.choice([-1, 0, 1], n, p=[0.3, 0.4, 0.3]),
        "f4": np.round(np.random.uniform(0, 100, n), 1),
        "label": np.random.choice([0, 1], n, p=[0.9, 0.1]),
        "mock_amount": np.round(np.random.lognormal(9.0, 1.0, n), 2),
    })
    
    return df


def generate_handcrafted_data() -> pd.DataFrame:
    """
    手工构造 10 行数据，用于指标计算正确性验证（U5）。
    
    规则: (f0 > 0) → 命中行 index: 0,1,4,6,7
    
    预期指标:
        total_amount = 5500
        total_bad_amount = 2700  (label=1: index 0,2,4,7,9)
        hit_amount = 2300  (f0>0: index 0,1,4,6,7)
        bad_amount = 1400  (f0>0 且 label=1: index 0,4,7)
        hit_amount_pct = 2300/5500 ≈ 0.4182
        bad_amount_pct = 1400/2700 ≈ 0.5185
        amount_bad_rate = 1400/2300 ≈ 0.6087
        overall_bad_rate = 2700/5500 ≈ 0.4909
        amount_lift = 0.6087/0.4909 ≈ 1.24
        avg_amount_per_hit = 2300/5 = 460.0
    """
    df = pd.DataFrame({
        "f0":          [1,   2,   0,  -1,   3,   0,   1,   2,  -1,   0],
        "label":       [1,   0,   1,   0,   1,   0,   0,   1,   0,   1],
        "mock_amount": [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000],
    })
    return df


# 手算预期值（用于断言）
HANDCRAFTED_EXPECTED = {
    "total_amount": 5500.0,
    "total_bad_amount": 2700.0,
    "hit_amount": 2300.0,
    "bad_amount": 1400.0,
    "hit_amount_pct": round(2300 / 5500, 4),
    "bad_amount_pct": round(1400 / 2700, 4),
    "amount_bad_rate": round(1400 / 2300, 4),
    "amount_lift": round((1400 / 2300) / (2700 / 5500), 2),
    "avg_amount_per_hit": round(2300 / 5, 2),
}


def generate_edge_case_data(case: str, seed: int = 42) -> pd.DataFrame:
    """
    生成边界条件测试数据。
    
    Args:
        case: 边界场景名称
            - "all_bad": 所有样本都是坏样本
            - "all_good": 所有样本都是好样本
            - "single_row": 单行数据
            - "zero_amount": 金额全为 0
            - "nan_amount": 部分金额为 NaN
            - "negative_amount": 部分金额为负
            - "large_amount": 超大金额值
    """
    np.random.seed(seed)
    
    if case == "all_bad":
        return pd.DataFrame({
            "f0": [1, 2, 0, 3, 1],
            "label": [1, 1, 1, 1, 1],
            "mock_amount": [100, 200, 300, 400, 500],
        })
    elif case == "all_good":
        return pd.DataFrame({
            "f0": [1, 2, 0, 3, 1],
            "label": [0, 0, 0, 0, 0],
            "mock_amount": [100, 200, 300, 400, 500],
        })
    elif case == "single_row":
        return pd.DataFrame({
            "f0": [1],
            "label": [1],
            "mock_amount": [1000.0],
        })
    elif case == "zero_amount":
        return pd.DataFrame({
            "f0": [1, 2, 0, 3, 1],
            "label": [1, 0, 1, 0, 1],
            "mock_amount": [0.0, 0.0, 0.0, 0.0, 0.0],
        })
    elif case == "nan_amount":
        return pd.DataFrame({
            "f0": [1, 2, 0, 3, 1],
            "label": [1, 0, 1, 0, 1],
            "mock_amount": [100.0, np.nan, 300.0, np.nan, 500.0],
        })
    elif case == "negative_amount":
        return pd.DataFrame({
            "f0": [1, 2, 0, 3, 1],
            "label": [1, 0, 1, 0, 1],
            "mock_amount": [100.0, -200.0, 300.0, -400.0, 500.0],
        })
    elif case == "large_amount":
        return pd.DataFrame({
            "f0": [1, 2, 0, 3, 1],
            "label": [1, 0, 1, 0, 1],
            "mock_amount": [1e12, 2e12, 3e12, 4e12, 5e12],
        })
    else:
        raise ValueError(f"Unknown edge case: {case}")


def generate_mock_amount_for_csv(
    csv_path: str | Path,
    amount_col: str = "mock_amount",
    seed: int = 42
) -> pd.DataFrame:
    """
    为 starrel_train.csv 生成 mock 金额列。
    
    策略：对数正态分布模拟授信/放款金额。
    - 中位数约 8,100
    - 范围约 1,000 - 200,000
    
    Args:
        csv_path: starrel_train.csv 路径
        amount_col: 生成的金额列名
        seed: 随机种子
        
    Returns:
        带有新金额列的 DataFrame
    """
    np.random.seed(seed)
    df = pd.read_csv(csv_path)
    df[amount_col] = np.round(np.random.lognormal(mean=9.0, sigma=1.0, size=len(df)), 2)
    return df
