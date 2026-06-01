"""
敏感个人信息字段检测器

合规依据：中华人民共和国《个人信息保护法》（PIPL）第 4、28、51 条
检测策略：双层检测
  L1 - 列名关键词匹配（中英文，速度快）
  L2 - 样本值正则扫描（覆盖匿名列名，如 f0/feature_23）
"""
from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


# =============================================================================
# 数据结构
# =============================================================================

class DetectionLevel(str, Enum):
    HIGH   = "high"    # 高危：阻断上传
    MEDIUM = "medium"  # 中危：警告，用户确认
    LOW    = "low"     # 低危：提示，不阻断


@dataclass
class Finding:
    column: str
    level: DetectionLevel
    rule_name: str
    detection_method: str          # "column_name" | "value_regex"
    hit_rate: float | None = None  # 值扫描命中率，列名匹配时为 None
    sample_values: list[str] = field(default_factory=list)  # 脱敏后的示例值


@dataclass
class DetectionReport:
    has_sensitive: bool
    max_level: DetectionLevel | None
    findings: list[Finding]
    scanned_columns: int
    scanned_rows: int

    @property
    def summary(self) -> dict[str, Any]:
        return {
            "has_sensitive": self.has_sensitive,
            "max_level": self.max_level.value if self.max_level else None,
            "high_count":   sum(1 for f in self.findings if f.level == DetectionLevel.HIGH),
            "medium_count": sum(1 for f in self.findings if f.level == DetectionLevel.MEDIUM),
            "low_count":    sum(1 for f in self.findings if f.level == DetectionLevel.LOW),
            "scanned_columns": self.scanned_columns,
            "scanned_rows": self.scanned_rows,
        }


# =============================================================================
# 规则库
# =============================================================================

# 每条规则：(rule_name, level, col_keywords_en, col_keywords_zh, value_regex, hit_threshold)
# hit_threshold: 值扫描触发比例（0~1），None 表示列名命中即触发
_RULES = [
    # ---- 高危 ----
    (
        "身份证号",
        DetectionLevel.HIGH,
        ["id_card", "idcard", "id_no", "cert_no", "certno", "citizen_id",
         "national_id", "identity", "id_number", "identity_no"],
        ["身份证", "证件号", "身份证号", "身份证号码", "居民身份证", "证件号码"],
        r"\d{6}(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]",
        0.05,
    ),
    (
        "手机号",
        DetectionLevel.HIGH,
        ["mobile", "phone", "tel", "cellphone", "cell_phone", "contact_phone",
         "mobile_no", "phone_no", "mobile_phone", "telephone"],
        ["手机号", "手机", "电话", "联系方式", "手机号码", "联系电话", "移动电话"],
        r"1[3-9]\d{9}",
        0.05,
    ),
    (
        "银行卡号",
        DetectionLevel.HIGH,
        ["bank_card", "bankcard", "card_no", "card_number", "bank_account",
         "account_no", "debit_card", "credit_card", "bankaccount"],
        ["银行卡号", "卡号", "银行账号", "储蓄卡", "信用卡号", "借记卡"],
        r"[3-9]\d{12,18}",
        0.05,
    ),
    (
        "护照号",
        DetectionLevel.HIGH,
        ["passport", "passport_no", "passport_number"],
        ["护照号", "护照"],
        r"[EeGgDd]\d{8}",
        0.05,
    ),
    # 姓名：值扫描需结合列名，单独值扫描误判率高，设高阈值
    (
        "姓名",
        DetectionLevel.HIGH,
        ["full_name", "real_name", "customer_name", "applicant_name",
         "borrower_name", "user_realname"],
        ["姓名", "真实姓名", "客户姓名", "借款人姓名", "用户姓名", "联系人姓名"],
        r"[\u4e00-\u9fa5]{2,4}",
        0.30,  # 纯值扫描阈值较高，配合列名降低误判
    ),
    # ---- 中危 ----
    (
        "电子邮箱",
        DetectionLevel.MEDIUM,
        ["email", "mail", "e_mail", "email_address", "emailaddress"],
        ["邮箱", "电子邮件", "邮件地址", "邮件"],
        r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
        0.05,
    ),
    (
        "家庭地址",
        DetectionLevel.MEDIUM,
        ["address", "addr", "home_address", "work_address",
         "residential_address", "contact_address"],
        ["地址", "家庭地址", "通讯地址", "住址", "居住地址", "工作地址", "所在地"],
        None,   # 地址字段值难以正则匹配，依赖列名判断
        None,
    ),
    (
        "固定电话",
        DetectionLevel.MEDIUM,
        ["telephone", "landline", "office_phone", "home_phone", "tel_no"],
        ["固定电话", "座机", "办公电话"],
        r"(0\d{2,3}-?)?\d{7,8}",
        0.05,
    ),
    # ---- 低危 ----
    (
        "出生日期",
        DetectionLevel.LOW,
        ["dob", "birthday", "birth_date", "date_of_birth", "birthdate", "birth_day"],
        ["生日", "出生日期", "出生年月", "出生年月日"],
        r"\d{4}[-/]\d{2}[-/]\d{2}",
        0.05,
    ),
    (
        "IP地址",
        DetectionLevel.LOW,
        ["ip", "ip_address", "client_ip", "ipaddr", "ip_addr"],
        [],
        r"(\d{1,3}\.){3}\d{1,3}",
        0.05,
    ),
    (
        "车牌号",
        DetectionLevel.LOW,
        ["plate", "license_plate", "car_plate", "plate_no"],
        ["车牌号", "车牌", "车牌号码"],
        r"[\u4e00-\u9fa5][A-Z][\w]{5,6}",
        0.05,
    ),
]

# 姓名规则列名命中时，值扫描阈值可以降低
_NAME_COL_KEYWORDS_EN = {"full_name", "real_name", "customer_name",
                          "applicant_name", "borrower_name", "user_realname"}
_NAME_COL_KEYWORDS_ZH = {"姓名", "真实姓名", "客户姓名", "借款人姓名",
                          "用户姓名", "联系人姓名"}


# =============================================================================
# 检测器
# =============================================================================

class SensitiveFieldDetector:
    """
    双层敏感信息检测器

    L1: 列名关键词匹配（中英文，< 1ms）
    L2: 样本值正则扫描（L1 未命中时执行，覆盖匿名列名）
    """

    def __init__(self, sample_rows: int = 100):
        self.sample_rows = sample_rows
        # 预编译正则
        self._compiled: dict[str, re.Pattern | None] = {}
        for rule in _RULES:
            pattern = rule[4]
            self._compiled[rule[0]] = re.compile(pattern) if pattern else None

    # ------------------------------------------------------------------
    # 公共入口
    # ------------------------------------------------------------------

    def detect(self, df: pd.DataFrame) -> DetectionReport:
        """对 DataFrame 执行双层检测，返回检测报告"""
        findings: list[Finding] = []
        sample = df.head(self.sample_rows)
        detected_cols: set[str] = set()

        for col in df.columns:
            col_lower = col.lower()

            # L1: 列名匹配
            finding = self._check_column_name(col, col_lower)
            if finding:
                detected_cols.add(col)
                findings.append(finding)
                continue

            # L2: 值正则扫描（仅对未通过 L1 的列）
            finding = self._check_column_values(col, col_lower, sample[col])
            if finding:
                detected_cols.add(col)
                findings.append(finding)

        # 按严重程度排序
        level_order = {DetectionLevel.HIGH: 0, DetectionLevel.MEDIUM: 1, DetectionLevel.LOW: 2}
        findings.sort(key=lambda f: level_order[f.level])

        max_level = findings[0].level if findings else None

        return DetectionReport(
            has_sensitive=bool(findings),
            max_level=max_level,
            findings=findings,
            scanned_columns=len(df.columns),
            scanned_rows=min(self.sample_rows, len(df)),
        )

    # ------------------------------------------------------------------
    # L1：列名关键词匹配
    # ------------------------------------------------------------------

    def _check_column_name(self, col: str, col_lower: str) -> Finding | None:
        """L1：列名与规则库关键词匹配"""
        for rule_name, level, kw_en, kw_zh, pattern, _ in _RULES:
            # 英文关键词：精确词匹配（分词后比较，避免 `telephone` 误中 `tel`）
            if any(kw == col_lower or col_lower == kw or
                   col_lower.startswith(kw + "_") or col_lower.endswith("_" + kw)
                   for kw in kw_en):
                return Finding(
                    column=col,
                    level=level,
                    rule_name=rule_name,
                    detection_method="column_name",
                )
            # 中文关键词：包含匹配
            if any(kw in col for kw in kw_zh):
                return Finding(
                    column=col,
                    level=level,
                    rule_name=rule_name,
                    detection_method="column_name",
                )
        return None

    # ------------------------------------------------------------------
    # L2：样本值正则扫描
    # ------------------------------------------------------------------

    def _check_column_values(
        self, col: str, col_lower: str, values: pd.Series
    ) -> Finding | None:
        """L2：对列的样本值执行正则扫描"""
        for rule_name, level, kw_en, kw_zh, pattern, threshold in _RULES:
            compiled = self._compiled.get(rule_name)
            if not compiled or threshold is None:
                continue

            # 姓名规则：纯值扫描阈值高（0.30），但若列名含姓名关键词则降到 0.05
            effective_threshold = threshold
            if rule_name == "姓名":
                col_is_name = (
                    any(kw == col_lower for kw in _NAME_COL_KEYWORDS_EN) or
                    any(kw in col for kw in _NAME_COL_KEYWORDS_ZH)
                )
                if col_is_name:
                    effective_threshold = 0.05

            hit_rate = self._calc_hit_rate(values, compiled)
            if hit_rate >= effective_threshold:
                sample_vals = self._collect_samples(values, compiled)
                return Finding(
                    column=col,
                    level=level,
                    rule_name=rule_name,
                    detection_method="value_regex",
                    hit_rate=hit_rate,
                    sample_values=sample_vals,
                )
        return None

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------

    @staticmethod
    def _calc_hit_rate(values: pd.Series, compiled: re.Pattern) -> float:
        """计算正则在 Series 中的命中率（跳过空值）"""
        non_null = values.dropna().astype(str)
        if len(non_null) == 0:
            return 0.0
        hits = non_null.apply(lambda v: bool(compiled.search(v))).sum()
        return float(hits) / len(non_null)

    @staticmethod
    def _collect_samples(
        values: pd.Series, compiled: re.Pattern, max_samples: int = 3
    ) -> list[str]:
        """收集命中的样本值（脱敏处理后返回）"""
        samples = []
        for v in values.dropna().astype(str):
            if compiled.search(v):
                samples.append(SensitiveFieldDetector._mask_value(v))
                if len(samples) >= max_samples:
                    break
        return samples

    @staticmethod
    def _mask_value(value: str) -> str:
        """对样本值简单脱敏（用于展示，不暴露原始值）"""
        if len(value) <= 4:
            return "****"
        # 保留首尾各 2 个字符，中间替换为 ****
        return value[:2] + "****" + value[-2:]
