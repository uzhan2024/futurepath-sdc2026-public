"""Team-authored practice guidance for the pinned fictional role demo."""

from __future__ import annotations

from dataclasses import dataclass

from domain.models import SkillId
from fixtures.synthetic_requirements import SCOPE
from services.matching import MatchResult, SCORING_MODE


GUIDANCE_VERSION = "synthetic-practice-v1"

# These are illustrative exercises, not verified courses or external resources.
_PRACTICE = {
    "demo-skill-01": (
        "把一个虚构问题拆成输入、限制和可检查的结果。",
        "保留问题拆解表和一次修订说明。",
    ),
    "demo-skill-02": (
        "向同伴解释一个合成项目的目标，再根据反馈改写说明。",
        "保留讲解提纲和反馈后的版本。",
    ),
    "demo-skill-03": (
        "编写一个只处理合成数据的小程序，加入输入校验。",
        "保留代码、示例输入及预期输出。",
    ),
    "demo-skill-04": (
        "用一张自制小表练习检查缺失值，并解释一个简单结论的限制。",
        "保留表格、计算步骤和限制说明。",
    ),
    "demo-skill-05": (
        "为一个虚构账户场景列出最小权限和异常处理步骤。",
        "保留风险清单和改进后的检查表。",
    ),
    "demo-skill-06": (
        "和同伴为一个小型合成项目分工，并记录一次交接。",
        "保留分工、交接记录和复盘要点。",
    ),
    "demo-skill-07": (
        "为一个合成项目写清目的、运行步骤和已知限制。",
        "保留可供他人照做的短文档。",
    ),
    "demo-skill-08": (
        "完成一个范围受限的合成项目，记录一次失败和修正。",
        "保留作品链接或本地记录及反思。",
    ),
}


@dataclass(frozen=True)
class PracticeStep:
    skill_id: SkillId
    label: str
    activity: str
    evidence_to_keep: str


@dataclass(frozen=True)
class SyntheticPracticePath:
    role_code: str
    role_title: str
    confirmed_gap_steps: tuple[PracticeStep, ...]
    unknown_skills: tuple[str, ...]
    not_reported_skills: tuple[str, ...]
    matched_skills: tuple[str, ...]
    guidance_version: str = GUIDANCE_VERSION


def _checked_result(result: MatchResult) -> None:
    if (type(result) is not MatchResult or result.scoring_scope != SCOPE
            or result.scoring_mode != SCORING_MODE
            or result.occupation_id.scheme != "local-fictional"):
        raise ValueError("practice guidance requires a fictional matching result")


def build_practice_path(result: MatchResult,
                        labels_by_id: dict[SkillId, str]) -> SyntheticPracticePath:
    """Turn confirmed gaps into exercises; keep unknown states unscored."""
    _checked_result(result)
    required = (result.matched_skills + result.confirmed_gaps
                + result.unknown_skills + result.not_reported_skills)
    if len(required) != result.requirement_count or len(set(required)) != len(required):
        raise ValueError("matching result partitions are inconsistent")
    if any(skill not in labels_by_id or skill.skill_code not in _PRACTICE for skill in required):
        raise ValueError("practice guidance has an unsupported skill")
    steps = tuple(
        PracticeStep(skill, labels_by_id[skill], *_PRACTICE[skill.skill_code])
        for skill in result.confirmed_gaps
    )
    labels = lambda values: tuple(labels_by_id[skill] for skill in values)
    return SyntheticPracticePath(
        result.occupation_id.source_code,
        result.title,
        steps,
        labels(result.unknown_skills),
        labels(result.not_reported_skills),
        labels(result.matched_skills),
    )


@dataclass(frozen=True)
class RoleComparison:
    shared_skills: tuple[SkillId, ...]
    left_only_skills: tuple[SkillId, ...]
    right_only_skills: tuple[SkillId, ...]


def compare_fictional_roles(left: MatchResult, right: MatchResult) -> RoleComparison:
    """Compare requirement sets without assigning a score to incomplete roles."""
    _checked_result(left)
    _checked_result(right)
    left_skills = set(left.matched_skills + left.confirmed_gaps
                      + left.unknown_skills + left.not_reported_skills)
    right_skills = set(right.matched_skills + right.confirmed_gaps
                       + right.unknown_skills + right.not_reported_skills)
    if len(left_skills) != left.requirement_count or len(right_skills) != right.requirement_count:
        raise ValueError("matching result partitions are inconsistent")
    key = lambda skill: skill.skill_code
    return RoleComparison(
        tuple(sorted(left_skills & right_skills, key=key)),
        tuple(sorted(left_skills - right_skills, key=key)),
        tuple(sorted(right_skills - left_skills, key=key)),
    )
