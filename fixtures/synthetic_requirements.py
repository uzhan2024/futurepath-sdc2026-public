"""Team-authored fictional requirements, isolated from all source datasets."""

from dataclasses import asdict, dataclass
from pathlib import Path
import json
import re

from domain.models import OccupationId, SkillId
from fixtures.synthetic_profiles import content_sha256, load_profile_bundle


FIXTURE_PATH = Path(__file__).with_name("synthetic_requirements.json")
SCHEMA_VERSION = "synthetic-requirements-v1"
FIXTURE_VERSION = "fictional-requirements-v1"
SCOPE = "synthetic_demo_only"
ORIGIN = "team_authored_fictional"
EXPECTED_CONTENT_SHA256 = "72f701d752026658cba2d77505af94e0e9cc24d42398ea7d94e0a7024b0d8b25"


class RequirementFixtureError(ValueError):
    """Requirements are malformed or outside the authorized fictional scope."""


@dataclass(frozen=True)
class FictionalRequirements:
    occupation_id: OccupationId
    title: str
    skill_ids: tuple[SkillId, ...]
    synthetic: bool = True
    origin: str = ORIGIN
    scoring_scope: str = SCOPE

    def __post_init__(self):
        if type(self.occupation_id) is not OccupationId:
            raise TypeError("occupation_id must be an OccupationId")
        identity = self.occupation_id
        if (identity.scheme != "local-fictional" or identity.taxonomy_version != "demo-v1"
                or not re.fullmatch(r"demo-occupation-[0-9]{2}", identity.source_code)):
            raise RequirementFixtureError("only local fictional occupation identities are permitted")
        if self.synthetic is not True or self.origin != ORIGIN or self.scoring_scope != SCOPE:
            raise RequirementFixtureError("unapproved or external requirements cannot enter synthetic scoring")
        if not isinstance(self.title, str) or not self.title.startswith("Fictional ") or not self.title.endswith("(synthetic demo)"):
            raise RequirementFixtureError("occupation title must explicitly identify a fictional synthetic demo")
        if type(self.skill_ids) is not tuple or any(type(skill) is not SkillId for skill in self.skill_ids):
            raise TypeError("skill_ids must be a tuple of SkillId values")
        if len(set(self.skill_ids)) != len(self.skill_ids):
            raise RequirementFixtureError("duplicate requirement skill")
        for skill in self.skill_ids:
            if (skill.scheme != "local" or skill.scheme_version != "demo-v1"
                    or not re.fullmatch(r"demo-skill-[0-9]{2}", skill.skill_code)):
                raise RequirementFixtureError("only local demo skills are permitted")


@dataclass(frozen=True)
class FictionalRequirementBundle:
    fixture_version: str
    content_sha256: str
    occupations: tuple[FictionalRequirements, ...]


def _keys(value, expected):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise RequirementFixtureError("fictional requirement schema mismatch")
    return value


def _unique_json_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise RequirementFixtureError("duplicate JSON field")
        result[key] = value
    return result


def _payload(bundle):
    return {"schema_version": SCHEMA_VERSION, "fixture_version": bundle.fixture_version,
            "synthetic": True, "origin": ORIGIN, "scoring_scope": SCOPE,
            "occupations": [asdict(role) for role in bundle.occupations]}


def validate_requirement_bundle(bundle: FictionalRequirementBundle) -> None:
    """Recheck provenance and the pin at the scoring boundary, without disk I/O."""
    if type(bundle) is not FictionalRequirementBundle:
        raise RequirementFixtureError("scoring requires the fictional requirement bundle; external data is blocked")
    if bundle.fixture_version != FIXTURE_VERSION or type(bundle.occupations) is not tuple or len(bundle.occupations) != 3:
        raise RequirementFixtureError("unsupported fictional requirement version or occupation count")
    for role in bundle.occupations:
        if type(role) is not FictionalRequirements:
            raise RequirementFixtureError("external requirement type is blocked")
        role.__post_init__()
    if len({role.occupation_id for role in bundle.occupations}) != 3:
        raise RequirementFixtureError("duplicate fictional occupation")
    actual = content_sha256(_payload(bundle))
    if actual != bundle.content_sha256 or actual != EXPECTED_CONTENT_SHA256:
        raise RequirementFixtureError("fictional requirement content SHA-256 pin mismatch")


def load_requirement_bundle(path: Path = FIXTURE_PATH) -> FictionalRequirementBundle:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=_unique_json_keys)
        _keys(raw, {"schema_version", "fixture_version", "synthetic", "origin", "scoring_scope", "occupations", "content_sha256"})
        if (raw["schema_version"] != SCHEMA_VERSION or raw["synthetic"] is not True
                or raw["origin"] != ORIGIN or raw["scoring_scope"] != SCOPE):
            raise RequirementFixtureError("requirements must be explicitly fictional synthetic demo data")
        if not isinstance(raw["occupations"], list):
            raise RequirementFixtureError("occupations must be a list")
        supported = {identity for identity, _ in load_profile_bundle().supported_skills}
        roles = []
        for item in raw["occupations"]:
            _keys(item, {"occupation_id", "title", "skill_ids", "synthetic", "origin", "scoring_scope"})
            _keys(item["occupation_id"], {"scheme", "taxonomy_version", "source_code"})
            if not isinstance(item["skill_ids"], list):
                raise RequirementFixtureError("skill_ids must be a list")
            skills = tuple(SkillId(**_keys(skill, {"scheme", "scheme_version", "skill_code"})) for skill in item["skill_ids"])
            if not set(skills).issubset(supported):
                raise RequirementFixtureError("requirement references unsupported synthetic skill")
            roles.append(FictionalRequirements(OccupationId(**item["occupation_id"]), item["title"], skills,
                                              item["synthetic"], item["origin"], item["scoring_scope"]))
        bundle = FictionalRequirementBundle(raw["fixture_version"], raw["content_sha256"], tuple(roles))
        validate_requirement_bundle(bundle)
        return bundle
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise RequirementFixtureError(f"invalid fictional requirement fixture: {exc}") from exc
