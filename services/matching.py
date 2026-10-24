"""Synthetic-only equal-weight presence coverage; no UI or real-data scoring."""

from dataclasses import asdict, dataclass
import hashlib

from domain.models import OccupationId, SkillId, SkillState, SyntheticProfile
from fixtures.synthetic_profiles import canonical_json
from fixtures.synthetic_requirements import (
    FictionalRequirementBundle, FictionalRequirements, SCOPE,
    RequirementFixtureError, validate_requirement_bundle,
)


RULE_VERSION = "synthetic-presence-equal-weight-v1"
SCORING_MODE = "synthetic_demo_base_only"


@dataclass(frozen=True)
class MatchResult:
    occupation_id: OccupationId
    title: str
    status: str
    requirement_count: int
    matched_skills: tuple[SkillId, ...]
    confirmed_gaps: tuple[SkillId, ...]
    unknown_skills: tuple[SkillId, ...]
    not_reported_skills: tuple[SkillId, ...]
    information_coverage: float | None
    M_known: float | None
    M_lower: float | None
    M_upper: float | None
    score: float | None
    scoring_scope: str = SCOPE
    scoring_mode: str = SCORING_MODE


@dataclass(frozen=True)
class SyntheticMatchingRun:
    profile_id: str
    profile_fixture_version: str
    requirement_fixture_version: str
    requirement_content_sha256: str
    input_fingerprint: str
    ranked_results: tuple[MatchResult, ...]
    unranked_results: tuple[MatchResult, ...]
    rule_version: str = RULE_VERSION
    scoring_scope: str = SCOPE
    scoring_mode: str = SCORING_MODE


def _identity_key(identity):
    return tuple(asdict(identity).values())


def _assess_role(profile: SyntheticProfile, role: FictionalRequirements) -> MatchResult:
    """Arithmetic helper; public callers must use the pinned-bundle boundary."""
    if type(role) is not FictionalRequirements:
        raise RequirementFixtureError("external requirement type is blocked")
    role.__post_init__()
    states = {skill.skill_id: skill.state for skill in profile.skills}
    partitions = {state: [] for state in SkillState}
    for identity in sorted(role.skill_ids, key=_identity_key):
        # A missing assertion means not reported, never confirmed absent.
        partitions[states.get(identity, SkillState.NOT_REPORTED)].append(identity)
    present = tuple(partitions[SkillState.KNOWN_PRESENT])
    absent = tuple(partitions[SkillState.KNOWN_ABSENT])
    unknown = tuple(partitions[SkillState.UNKNOWN])
    unreported = tuple(partitions[SkillState.NOT_REPORTED])
    W, P, A, U, N = len(role.skill_ids), len(present), len(absent), len(unknown), len(unreported)
    known = P + A
    complete = W > 0 and known == W
    return MatchResult(
        occupation_id=role.occupation_id, title=role.title,
        status="complete" if complete else "insufficient_profile" if W else "insufficient_requirements",
        requirement_count=W, matched_skills=present, confirmed_gaps=absent,
        unknown_skills=unknown, not_reported_skills=unreported,
        information_coverage=known / W if W else None,
        M_known=P / known if known else None,
        M_lower=P / W if W else None,
        M_upper=(P + U + N) / W if W else None,
        score=100 * P / W if complete else None,
    )


def match_synthetic_profile(profile: SyntheticProfile,
                            requirements: FictionalRequirementBundle) -> SyntheticMatchingRun:
    """Score only the pinned fictional fixture; reject external/unapproved data.

    Incomplete occupations are returned separately, ordered by local identity,
    and never participate in the complete occupations' score ranking.
    """
    validate_requirement_bundle(requirements)
    if type(profile) is not SyntheticProfile:
        raise TypeError("matching requires an existing SyntheticProfile")
    profile.__post_init__()
    if profile.synthetic is not True:
        raise ValueError("only synthetic profiles are permitted")
    for assertion in profile.skills:
        assertion.__post_init__()
        if assertion.skill_id.scheme != "local" or assertion.skill_id.scheme_version != "demo-v1":
            raise ValueError("only synthetic demo profile skills are permitted")
    profile_payload = asdict(profile)
    profile_payload["skills"] = sorted(profile_payload["skills"], key=lambda item: tuple(item["skill_id"].values()))
    profile_payload["preferences"] = sorted(profile_payload["preferences"])
    profile_payload["interests"] = sorted(profile_payload["interests"])
    fingerprint = hashlib.sha256(canonical_json({
        "profile": profile_payload, "requirements": requirements.content_sha256,
        "rule_version": RULE_VERSION, "scoring_scope": SCOPE, "scoring_mode": SCORING_MODE,
    })).hexdigest()
    results = tuple(_assess_role(profile, role) for role in requirements.occupations)
    ranked = tuple(sorted((result for result in results if result.score is not None),
                          key=lambda result: (-result.score, _identity_key(result.occupation_id))))
    unranked = tuple(sorted((result for result in results if result.score is None),
                            key=lambda result: _identity_key(result.occupation_id)))
    return SyntheticMatchingRun(profile.profile_id, profile.fixture_version,
                                requirements.fixture_version, requirements.content_sha256,
                                fingerprint, ranked, unranked)


def match_confirmed_profile(profile, requirements):
    """Apply the existing arithmetic to confirmed user states and fictional requirements."""
    from domain.career_profile import ConfirmedCareerProfile
    if type(profile) is not ConfirmedCareerProfile:
        raise TypeError('A confirmed career profile is required')
    profile.__post_init__()
    validate_requirement_bundle(requirements)
    fingerprint = hashlib.sha256(canonical_json({'states': [asdict(s) for s in profile.skills],
        'requirements': requirements.content_sha256, 'rule': RULE_VERSION, 'source': profile.source})).hexdigest()
    results = tuple(_assess_role(profile, role) for role in requirements.occupations)
    ranked = tuple(sorted((r for r in results if r.score is not None), key=lambda r: (-r.score, _identity_key(r.occupation_id))))
    unranked = tuple(sorted((r for r in results if r.score is None), key=lambda r: _identity_key(r.occupation_id)))
    return SyntheticMatchingRun(profile.profile_id, profile.fixture_version, requirements.fixture_version,
                                requirements.content_sha256, fingerprint, ranked, unranked)
