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
        "Break a fictional problem into inputs, constraints, and checkable outcomes.",
        "Keep the problem outline and a short note describing one revision.",
    ),
    "demo-skill-02": (
        "Explain the goal of a synthetic project to a peer, then revise the explanation using their feedback.",
        "Keep the talk outline and the revised version.",
    ),
    "demo-skill-03": (
        "Write a small program that processes synthetic data and validates its inputs.",
        "Keep the code, a sample input, and the expected output.",
    ),
    "demo-skill-04": (
        "Use a small self-made table to inspect missing values and explain the limits of one simple conclusion.",
        "Keep the table, calculation steps, and limitations note.",
    ),
    "demo-skill-05": (
        "For a fictional account scenario, list least-privilege choices and exception-handling steps.",
        "Keep the risk list and an improved review checklist.",
    ),
    "demo-skill-06": (
        "Divide work with a peer on a small synthetic project and record one handoff.",
        "Keep the task split, handoff note, and a few retrospective points.",
    ),
    "demo-skill-07": (
        "Document the purpose, run steps, and known limitations of a synthetic project.",
        "Keep a short guide that another person could follow.",
    ),
    "demo-skill-08": (
        "Complete a small synthetic project and record one failure and correction.",
        "Keep a project link or local note and a brief reflection.",
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
