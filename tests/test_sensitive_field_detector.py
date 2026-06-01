"""
SensitiveFieldDetector 单元测试

测试文件说明：
  SC-01 sensitive_high_danger.csv     含 id_card / mobile 高危列名 + 真实格式值
  SC-02 sensitive_medium_danger.csv   含 email 中危列名
  SC-03 sensitive_anonymous_col.csv   匿名列名 f1 但值全是手机号（L2扫描测试）
  SC-04 sensitive_clean.csv           完全脱敏，预期无告警
"""
import os
import pandas as pd
import pytest
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# 延迟导入，允许在不装 deepanalyze 包的环境下收集测试
from deepanalyze.analysis.data_validator import (
    SensitiveFieldDetector,
    DetectionLevel,
)


# =============================================================================
# 辅助函数
# =============================================================================

def load_fixture(name: str) -> pd.DataFrame:
    return pd.read_csv(FIXTURES_DIR / name)


def detector() -> SensitiveFieldDetector:
    return SensitiveFieldDetector(sample_rows=100)


# =============================================================================
# SC-01: 高危 — 列名含 id_card / mobile
# =============================================================================

class TestHighDanger:
    """SC-01: 高危文件检测（列名匹配）"""

    def setup_method(self):
        self.df = load_fixture("sensitive_high_danger.csv")
        self.report = detector().detect(self.df)

    def test_has_sensitive(self):
        """应检测到敏感信息"""
        assert self.report.has_sensitive is True

    def test_max_level_high(self):
        """最高级别应为 HIGH"""
        assert self.report.max_level == DetectionLevel.HIGH

    def test_id_card_column_detected(self):
        """id_card 列应被检测到"""
        cols = [f.column for f in self.report.findings]
        assert "id_card" in cols

    def test_mobile_column_detected(self):
        """mobile 列应被检测到"""
        cols = [f.column for f in self.report.findings]
        assert "mobile" in cols

    def test_detection_method_column_name(self):
        """id_card 应通过列名匹配（L1）检测到"""
        id_card_finding = next(f for f in self.report.findings if f.column == "id_card")
        assert id_card_finding.detection_method == "column_name"

    def test_income_not_detected(self):
        """income 列不应被误判"""
        cols = [f.column for f in self.report.findings]
        assert "income" not in cols

    def test_credit_score_not_detected(self):
        """credit_score 列不应被误判"""
        cols = [f.column for f in self.report.findings]
        assert "credit_score" not in cols


# =============================================================================
# SC-02: 中危 — 列名含 email
# =============================================================================

class TestMediumDanger:
    """SC-02: 中危文件检测"""

    def setup_method(self):
        self.df = load_fixture("sensitive_medium_danger.csv")
        self.report = detector().detect(self.df)

    def test_has_sensitive(self):
        assert self.report.has_sensitive is True

    def test_max_level_medium(self):
        assert self.report.max_level == DetectionLevel.MEDIUM

    def test_email_detected(self):
        cols = [f.column for f in self.report.findings]
        assert "email" in cols

    def test_age_not_detected(self):
        cols = [f.column for f in self.report.findings]
        assert "age" not in cols


# =============================================================================
# SC-03: L2 扫描 — 匿名列名但值含手机号
# =============================================================================

class TestAnonymousColumnL2:
    """SC-03: 匿名列名值扫描（L2 检测）"""

    def setup_method(self):
        self.df = load_fixture("sensitive_anonymous_col.csv")
        self.report = detector().detect(self.df)

    def test_has_sensitive(self):
        """L2 应扫描到手机号"""
        assert self.report.has_sensitive is True

    def test_max_level_high(self):
        assert self.report.max_level == DetectionLevel.HIGH

    def test_f1_detected(self):
        """f1 列应被 L2 值扫描命中"""
        cols = [f.column for f in self.report.findings]
        assert "f1" in cols

    def test_f1_detection_method_value_regex(self):
        """f1 应通过值正则扫描（L2）检测到"""
        f1_finding = next((f for f in self.report.findings if f.column == "f1"), None)
        assert f1_finding is not None
        assert f1_finding.detection_method == "value_regex"

    def test_f1_high_hit_rate(self):
        """f1 手机号命中率应很高（> 0.9）"""
        f1_finding = next(f for f in self.report.findings if f.column == "f1")
        assert f1_finding.hit_rate is not None
        assert f1_finding.hit_rate > 0.9

    def test_f0_not_detected(self):
        """f0（0/1 整数列）不应被误判"""
        cols = [f.column for f in self.report.findings]
        assert "f0" not in cols

    def test_f2_not_detected(self):
        """f2（小数列）不应被误判"""
        cols = [f.column for f in self.report.findings]
        assert "f2" not in cols


# =============================================================================
# SC-04: 干净文件 — 脱敏数据集，无告警
# =============================================================================

class TestCleanDataset:
    """SC-04: 脱敏数据集，预期无告警"""

    def setup_method(self):
        self.df = load_fixture("sensitive_clean.csv")
        self.report = detector().detect(self.df)

    def test_no_sensitive(self):
        """脱敏数据集应无敏感信息"""
        assert self.report.has_sensitive is False

    def test_max_level_none(self):
        assert self.report.max_level is None

    def test_no_findings(self):
        assert len(self.report.findings) == 0

    def test_fuuid_not_detected(self):
        """内部ID fuuid 不应被误判为姓名等敏感字段"""
        cols = [f.column for f in self.report.findings]
        assert "fuuid" not in cols

    def test_credit_limit_not_detected(self):
        """credit_limit（金额）不应被误判"""
        cols = [f.column for f in self.report.findings]
        assert "credit_limit" not in cols


# =============================================================================
# 边界条件测试
# =============================================================================

class TestEdgeCases:
    """边界条件"""

    def test_empty_dataframe(self):
        """空 DataFrame 不崩溃"""
        df = pd.DataFrame({"label": [], "f0": []})
        report = detector().detect(df)
        assert report.has_sensitive is False
        assert report.scanned_rows == 0

    def test_all_null_column(self):
        """全空值列不崩溃，不误报"""
        df = pd.DataFrame({"mobile": [None] * 20, "label": range(20)})
        report = detector().detect(df)
        # mobile 列名命中 L1 -> 仍应检测到（列名匹配不依赖值）
        assert report.has_sensitive is True

    def test_single_row(self):
        """单行文件正常处理"""
        df = pd.DataFrame({"id_card": ["31010119900101001X"], "label": [1]})
        report = detector().detect(df)
        assert report.has_sensitive is True

    def test_summary_counts(self):
        """summary 统计计数正确"""
        df = load_fixture("sensitive_high_danger.csv")
        report = detector().detect(df)
        s = report.summary
        assert s["high_count"] >= 2   # id_card + mobile
        assert s["high_count"] == sum(1 for f in report.findings if f.level == DetectionLevel.HIGH)

    def test_sample_values_masked(self):
        """返回的 sample_values 已脱敏（不含完整原始值）"""
        df = load_fixture("sensitive_anonymous_col.csv")
        report = detector().detect(df)
        f1_finding = next((f for f in report.findings if f.column == "f1"), None)
        if f1_finding and f1_finding.sample_values:
            for v in f1_finding.sample_values:
                # 脱敏后应含 ****
                assert "****" in v

    def test_findings_sorted_by_level(self):
        """findings 应按 HIGH > MEDIUM > LOW 排序"""
        df = load_fixture("sensitive_high_danger.csv")
        report = detector().detect(df)
        level_order = {DetectionLevel.HIGH: 0, DetectionLevel.MEDIUM: 1, DetectionLevel.LOW: 2}
        levels = [level_order[f.level] for f in report.findings]
        assert levels == sorted(levels)
