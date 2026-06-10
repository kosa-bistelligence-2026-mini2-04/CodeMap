from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Pattern


class Severity(str, Enum):
    BLOCK = "block"
    WARN = "warn"


@dataclass(frozen=True)
class RegexRule:
    name: str
    pattern: Pattern[str]
    severity: Severity
    reason: str


# 1) Future tense / predictive statements
FUTURE_TENSE_RULES: list[RegexRule] = [
    RegexRule(
        name="future_year",
        pattern=re.compile(r"(20[3-9]\d|2[1-9]\d{2})\s*年(之后|以后|起|开始)?"),
        severity=Severity.BLOCK,
        reason="禁止预测未来年份事件",
    ),
    RegexRule(
        name="future_relative",
        pattern=re.compile(r"未来\s*\d+\s*(年|月|周|天)"),
        severity=Severity.BLOCK,
        reason="禁止使用未来相对时间窗口",
    ),
    RegexRule(
        name="upcoming_release",
        pattern=re.compile(r"(即将|将要|将会|计划于)(发布|推出|上线|支持)"),
        severity=Severity.BLOCK,
        reason="禁止断言未发布的功能",
    ),
    RegexRule(
        name="next_generation",
        pattern=re.compile(r"(下一代|新一代|下个版本将)"),
        severity=Severity.BLOCK,
        reason="禁止虚构未来版本",
    ),
]

# 2) Absolute assertions
ABSOLUTE_ASSERTION_RULES: list[RegexRule] = [
    RegexRule(
        name="absolute_certainty",
        pattern=re.compile(r"(肯定|一定|必然|绝对|百分之百|100%)(是|会|能|可以)"),
        severity=Severity.BLOCK,
        reason="禁止绝对化断言",
    ),
    RegexRule(
        name="no_doubt",
        pattern=re.compile(r"(毫无疑问|无可争议|不容置疑)"),
        severity=Severity.BLOCK,
        reason="禁止使用绝对化修饰语",
    ),
]

# 3) Fabricated external references
FABRICATED_REF_RULES: list[RegexRule] = [
    RegexRule(
        name="latest_research",
        pattern=re.compile(r"(根据|依据)(最新|近期|权威)?(研究|报告|论文|数据)(显示|表明|指出)"),
        severity=Severity.BLOCK,
        reason="禁止引用未提供来源的研究",
    ),
    RegexRule(
        name="self_knowledge",
        pattern=re.compile(r"(据我所知|众所周知|业界公认|普遍认为)"),
        severity=Severity.BLOCK,
        reason="禁止使用模型先验作为来源",
    ),
    RegexRule(
        name="unspecified_source",
        pattern=re.compile(r"(某些|有些|一些)(用户|开发者|专家)(反馈|认为|表示)"),
        severity=Severity.WARN,
        reason="模糊来源应避免，建议引用具体 ISSUE/PR",
    ),
]

ALL_RULES: list[RegexRule] = (
    FUTURE_TENSE_RULES + ABSOLUTE_ASSERTION_RULES + FABRICATED_REF_RULES
)
