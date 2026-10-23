"""Strict loader for versioned synthetic-profile fixtures."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re

from domain.models import SkillId, SkillState, SyntheticProfile, UserSkill


FIXTURE_PATH = Path(__file__).with_name("synthetic_profiles.json")
SCHEMA_VERSION = "synthetic-profiles-v1"
FIXTURE_VERSION = "profiles-v1"
PREFERENCES_VERSION = "preferences-v1"
# Updated only together with a reviewed fixture change and a new fixture version.
EXPECTED_FIXTURE_SHA256 = "b41894d4ce568a7ed6971314507663cfcbd5d30aefe9c913e587f047df190c06"
_ROOT_KEYS = {"schema_version", "fixture_version", "preferences_version", "supported_skills",
              "profiles", "content_sha256"}
_PROFILE_KEYS = {"profile_id", "fixture_version", "preferences_version", "content_sha256",
                 "synthetic", "skills", "interests", "budget_amount", "budget_currency",
                 "hours_per_week", "preferences"}
_PERSONAL_KEYS = {"name", "full_name", "first_name", "last_name", "email", "phone",
                  "cv", "resume", "address", "birthdate", "date_of_birth"}
_ALLOWED_INTERESTS = {"software", "cybersecurity", "data", "learning_by_building",
                      "problem_solving", "team_projects"}
_ALLOWED_PREFERENCES = {
    "learning_format": {"reading", "hands_on", "mixed"},
    "work_environment": {"independent", "collaborative", "mixed"},
    "career_focus": {"software", "cybersecurity", "data", "exploration"},
}


class ProfileFixtureError(ValueError):
    """Fixture is malformed, has changed unexpectedly, or contains unsafe fields."""


@dataclass(frozen=True)
class SyntheticProfileBundle:
    schema_version: str
    fixture_version: str
    preferences_version: str
    content_sha256: str
    supported_skills: tuple[tuple[SkillId, str], ...]
    profiles: tuple[SyntheticProfile, ...]


def canonical_json(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def content_sha256(value: dict) -> str:
    payload = {key: item for key, item in value.items() if key != "content_sha256"}
    return hashlib.sha256(canonical_json(payload)).hexdigest()


def _reject_personal_keys(value: object, path: str = "root") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ProfileFixtureError(f"{path}: object keys must be strings")
            normalized = re.sub(r"[^a-z]", "", key.casefold())
            if normalized in {re.sub(r"[^a-z]", "", field) for field in _PERSONAL_KEYS}:
                raise ProfileFixtureError(f"{path}: personal-data field is forbidden")
            _reject_personal_keys(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_personal_keys(item, f"{path}[{index}]")


def _require_keys(value: object, expected: set[str], field: str) -> dict:
    if not isinstance(value, dict):
        raise ProfileFixtureError(f"{field} must be an object")
    actual = set(value)
    if actual != expected:
        missing, extra = sorted(expected - actual), sorted(actual - expected)
        raise ProfileFixtureError(f"{field} schema mismatch (missing={missing}, unexpected={extra})")
    return value


def _profile_from_json(raw: object, supported_ids: set[SkillId], expected_fixture: str,
                       expected_preferences: str) -> SyntheticProfile:
    data = _require_keys(raw, _PROFILE_KEYS, "profile")
    if data["fixture_version"] != expected_fixture or data["preferences_version"] != expected_preferences:
        raise ProfileFixtureError("profile version differs from bundle")
    if data["content_sha256"] != content_sha256(data):
        raise ProfileFixtureError(f"profile content hash mismatch: {data['profile_id']}")
    if data["synthetic"] is not True:
        raise ProfileFixtureError("profile synthetic must be true")
    if not isinstance(data["skills"], list):
        raise ProfileFixtureError("skills must be a list")
    skills = []
    for raw_skill in data["skills"]:
        skill = _require_keys(raw_skill, {"skill_id", "state"}, "profile skill")
        id_data = _require_keys(skill["skill_id"], {"scheme", "scheme_version", "skill_code"}, "skill_id")
        try:
            skill_id = SkillId(**id_data)
            state = SkillState(skill["state"])
            skills.append(UserSkill(skill_id, state))
        except (TypeError, ValueError) as exc:
            raise ProfileFixtureError(f"invalid skill identity or state: {exc}") from exc
        if skill_id not in supported_ids:
            raise ProfileFixtureError("profile references an unsupported skill")
    if set(skill.skill_id for skill in skills) != supported_ids or len(skills) != len(supported_ids):
        raise ProfileFixtureError("each profile must state every supported skill exactly once")
    interests = data["interests"]
    if (not isinstance(interests, list) or not interests
            or any(not isinstance(item, str) or item not in _ALLOWED_INTERESTS for item in interests)):
        raise ProfileFixtureError("interests contain an unsupported value")
    preferences = data["preferences"]
    if not isinstance(preferences, dict) or set(preferences) != set(_ALLOWED_PREFERENCES):
        raise ProfileFixtureError("preferences must use the supported preference keys")
    for key, allowed in _ALLOWED_PREFERENCES.items():
        if not isinstance(preferences[key], str) or preferences[key] not in allowed:
            raise ProfileFixtureError(f"unsupported preference value: {key}")
    try:
        return SyntheticProfile(
            profile_id=data["profile_id"], fixture_version=data["fixture_version"],
            content_sha256=data["content_sha256"], preferences_version=data["preferences_version"],
            synthetic=data["synthetic"], skills=tuple(skills), interests=tuple(interests),
            budget_amount=data["budget_amount"], budget_currency=data["budget_currency"],
            hours_per_week=data["hours_per_week"], preferences=tuple(sorted(preferences.items())),
        )
    except (TypeError, ValueError) as exc:
        raise ProfileFixtureError(f"invalid profile fields: {exc}") from exc


def load_profile_bundle(path: Path = FIXTURE_PATH, *, pin_hash: bool = True) -> SyntheticProfileBundle:
    """Load without mutating disk; the hash pin detects fixture replacement."""
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProfileFixtureError(f"cannot read synthetic profile fixture: {exc}") from exc
    root = _require_keys(raw, _ROOT_KEYS, "bundle")
    _reject_personal_keys(root)
    if root["schema_version"] != SCHEMA_VERSION:
        raise ProfileFixtureError("unsupported profile schema version")
    if root["fixture_version"] != FIXTURE_VERSION or root["preferences_version"] != PREFERENCES_VERSION:
        raise ProfileFixtureError("unsupported fixture or preferences version")
    actual_hash = content_sha256(root)
    if root["content_sha256"] != actual_hash:
        raise ProfileFixtureError("bundle content hash mismatch")
    if pin_hash and actual_hash != EXPECTED_FIXTURE_SHA256:
        raise ProfileFixtureError("profile fixture SHA-256 pin mismatch")
    if not isinstance(root["supported_skills"], list) or len(root["supported_skills"]) != 8:
        raise ProfileFixtureError("exactly eight supported synthetic skills are required")
    supported = []
    for item in root["supported_skills"]:
        entry = _require_keys(item, {"skill_id", "label"}, "supported skill")
        id_data = _require_keys(entry["skill_id"], {"scheme", "scheme_version", "skill_code"}, "skill_id")
        try:
            skill_id = SkillId(**id_data)
        except (TypeError, ValueError) as exc:
            raise ProfileFixtureError(f"invalid supported skill ID: {exc}") from exc
        label = entry["label"]
        if not isinstance(label, str) or not label.endswith("(synthetic demo)"):
            raise ProfileFixtureError("supported skills must be labelled synthetic demo entries")
        supported.append((skill_id, label))
    supported_ids = {skill_id for skill_id, _ in supported}
    if len(supported_ids) != len(supported):
        raise ProfileFixtureError("supported skill IDs must be unique")
    if not isinstance(root["profiles"], list) or len(root["profiles"]) != 3:
        raise ProfileFixtureError("exactly three synthetic profiles are required")
    profiles = tuple(_profile_from_json(item, supported_ids, root["fixture_version"],
                                        root["preferences_version"]) for item in root["profiles"])
    if len({profile.profile_id for profile in profiles}) != 3:
        raise ProfileFixtureError("profile IDs must be unique")
    return SyntheticProfileBundle(root["schema_version"], root["fixture_version"],
                                  root["preferences_version"], actual_hash,
                                  tuple(supported), profiles)
