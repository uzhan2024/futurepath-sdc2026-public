"""TSK-01 value objects based on Blueprint 04 sections 1, 2 and 8.

These validate structure, not source existence, licensing approval or truth.
EvidenceReference is a reference to a future EvidenceRecord, not that full record.
"""

from dataclasses import dataclass
from enum import Enum
import re
from urllib.parse import urlsplit


def _text(value: str, field: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field} must be a string")
    if not value.strip() or value != value.strip():
        raise ValueError(f"{field} must be nonblank without surrounding whitespace")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError(f"{field} must not contain control characters")


def _identifier(value: str, field: str) -> None:
    _text(value, field)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:*+/-]*", value):
        raise ValueError(f"{field} must be a namespaced identifier token")


def _instance(value: object, expected: type, field: str) -> None:
    if not isinstance(value, expected):
        raise TypeError(f"{field} must be {expected.__name__}")


def _url(value: str, field: str) -> None:
    _text(value, field)
    try:
        parsed = urlsplit(value)
        valid = (
            parsed.scheme in ("http", "https") and parsed.hostname
            and parsed.username is None and parsed.password is None
            and not any(char.isspace() for char in value)
        )
        parsed.port  # Reject malformed ports; does not contact the target.
    except ValueError:
        valid = False
    if not valid:
        raise ValueError(f"{field} must be an absolute HTTP(S) URL without user info")


class SkillState(str, Enum):
    """Unknown and unreported skills must remain distinct from confirmed absence."""

    KNOWN_PRESENT = "known_present"
    KNOWN_ABSENT = "known_absent"
    UNKNOWN = "unknown"
    NOT_REPORTED = "not_reported"


@dataclass(frozen=True)
class OccupationId:
    """Stable taxonomy identity; dataset releases are deliberately excluded."""

    scheme: str
    taxonomy_version: str
    source_code: str

    def __post_init__(self) -> None:
        _identifier(self.scheme, "scheme")
        _identifier(self.taxonomy_version, "taxonomy_version")
        _identifier(self.source_code, "source_code")
        if self.scheme == "O*NET-SOC":
            if not re.fullmatch(r"[0-9]{4}", self.taxonomy_version):
                raise ValueError("O*NET-SOC taxonomy_version must be a four-digit year")
            if not re.fullmatch(r"[0-9]{2}-[0-9]{4}\.[0-9]{2}", self.source_code):
                raise ValueError("O*NET-SOC source_code must have format NN-NNNN.NN")


@dataclass(frozen=True)
class SkillId:
    """Stable skill identity; a category ID does not identify a software example."""

    scheme: str
    scheme_version: str
    skill_code: str

    def __post_init__(self) -> None:
        for field in ("scheme", "scheme_version", "skill_code"):
            _identifier(getattr(self, field), field)


@dataclass(frozen=True)
class SourceVersion:
    """One source release, independent of occupation and skill taxonomy versions."""

    source_id: str
    source_version: str

    def __post_init__(self) -> None:
        _identifier(self.source_id, "source_id")
        _identifier(self.source_version, "source_version")


@dataclass(frozen=True)
class DataSource:
    """Identity metadata only; not a complete Source Registry or fetch record."""

    source: SourceVersion
    provider: str
    dataset_name: str
    geography: str
    license_scope: str
    documentation_url: str
    access_url: str
    license_url: str

    def __post_init__(self) -> None:
        _instance(self.source, SourceVersion, "source")
        for field in ("provider", "dataset_name", "geography", "license_scope"):
            _text(getattr(self, field), field)
        for field in ("documentation_url", "access_url", "license_url"):
            _url(getattr(self, field), field)


@dataclass(frozen=True)
class EvidenceReference:
    """Locate a record in a versioned snapshot; no approval is implied."""

    evidence_id: str
    source: SourceVersion
    snapshot_id: str
    source_record_id: str
    source_record_locator: str

    def __post_init__(self) -> None:
        _instance(self.source, SourceVersion, "source")
        for field in ("evidence_id", "snapshot_id"):
            _identifier(getattr(self, field), field)
        for field in ("source_record_id", "source_record_locator"):
            _text(getattr(self, field), field)


def _evidence_refs(value: tuple[EvidenceReference, ...]) -> None:
    _instance(value, tuple, "evidence_refs")
    for reference in value:
        _instance(reference, EvidenceReference, "evidence_refs item")
    ids = [reference.evidence_id for reference in value]
    if len(ids) != len(set(ids)):
        raise ValueError("evidence_refs must have unique evidence_id values")


@dataclass(frozen=True)
class Occupation:
    """An occupation description observed in a specific dataset and snapshot."""

    occupation_id: OccupationId
    dataset_version: str
    snapshot_id: str
    title: str
    description: str
    geography: str

    def __post_init__(self) -> None:
        _instance(self.occupation_id, OccupationId, "occupation_id")
        _identifier(self.dataset_version, "dataset_version")
        _identifier(self.snapshot_id, "snapshot_id")
        if self.occupation_id.scheme == "O*NET-SOC":
            if not re.fullmatch(r"[0-9]+\.[0-9]+", self.dataset_version):
                raise ValueError("O*NET-SOC dataset_version must have format major.minor")
        for field in ("title", "description", "geography"):
            _text(getattr(self, field), field)


@dataclass(frozen=True)
class Skill:
    """Catalog metadata; status is the catalog status, not a user's SkillState."""

    skill_id: SkillId
    name: str
    skill_type: str
    status: str
    evidence_refs: tuple[EvidenceReference, ...]

    def __post_init__(self) -> None:
        _instance(self.skill_id, SkillId, "skill_id")
        for field in ("name", "skill_type", "status"):
            _text(getattr(self, field), field)
        _evidence_refs(self.evidence_refs)
        if self.skill_type == "software_example":
            # Project-local identity, never an external software-category ID.
            if self.skill_id.scheme != "local" or not re.fullmatch(
                r"software-example-[A-Za-z0-9][A-Za-z0-9._:*+/-]*",
                self.skill_id.skill_code,
            ):
                raise ValueError(
                    "software_example requires a local ID with code software-example-<identifier>"
                )
            if not self.evidence_refs:
                raise ValueError("software_example requires nonempty evidence_refs")


@dataclass(frozen=True)
class UserSkill:
    """A single skill assertion for a future synthetic profile, without scoring."""

    skill_id: SkillId
    state: SkillState = SkillState.NOT_REPORTED
    evidence_refs: tuple[EvidenceReference, ...] = ()

    def __post_init__(self) -> None:
        _instance(self.skill_id, SkillId, "skill_id")
        _instance(self.state, SkillState, "state")
        _evidence_refs(self.evidence_refs)


@dataclass(frozen=True)
class SyntheticProfile:
    """Versioned, fictitious profile fixture; contains no real-person identity."""

    profile_id: str
    fixture_version: str
    content_sha256: str
    preferences_version: str
    synthetic: bool
    skills: tuple[UserSkill, ...]
    interests: tuple[str, ...]
    budget_amount: int
    budget_currency: str
    hours_per_week: int
    preferences: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        _identifier(self.profile_id, "profile_id")
        _identifier(self.fixture_version, "fixture_version")
        _identifier(self.preferences_version, "preferences_version")
        if type(self.synthetic) is not bool:
            raise TypeError("synthetic must be a bool")
        if self.synthetic is not True:
            raise ValueError("only synthetic profiles are permitted")
        _instance(self.skills, tuple, "skills")
        if not self.skills or any(not isinstance(skill, UserSkill) for skill in self.skills):
            raise ValueError("skills must be a nonempty tuple of UserSkill values")
        skill_ids = [skill.skill_id for skill in self.skills]
        if len(set(skill_ids)) != len(skill_ids):
            raise ValueError("skills must not contain duplicate skill IDs")
        _instance(self.interests, tuple, "interests")
        if any(not isinstance(item, str) or not item.strip() for item in self.interests):
            raise ValueError("interests must contain nonblank strings")
        for field in ("budget_amount", "hours_per_week"):
            value = getattr(self, field)
            if type(value) is not int:
                raise TypeError(f"{field} must be an integer")
        if self.budget_amount < 0:
            raise ValueError("budget_amount must be nonnegative")
        if not 0 <= self.hours_per_week <= 168:
            raise ValueError("hours_per_week must be between 0 and 168")
        if not isinstance(self.budget_currency, str) or not re.fullmatch(r"[A-Z]{3}", self.budget_currency):
            raise ValueError("budget_currency must be a three-letter uppercase code")
        if not isinstance(self.content_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", self.content_sha256):
            raise ValueError("content_sha256 must be a lowercase SHA-256 digest")
        _instance(self.preferences, tuple, "preferences")
        if any(not isinstance(pair, tuple) or len(pair) != 2
               or any(not isinstance(value, str) or not value.strip() for value in pair)
               for pair in self.preferences):
            raise ValueError("preferences must be key/value string pairs")
        keys = [key for key, _ in self.preferences]
        if len(keys) != len(set(keys)):
            raise ValueError("preferences must not contain duplicate keys")
