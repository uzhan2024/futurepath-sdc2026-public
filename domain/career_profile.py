"""User-confirmed skill states, separate from the immutable synthetic profiles."""
from dataclasses import dataclass, field
from domain.models import UserSkill


@dataclass(frozen=True)
class ConfirmedCareerProfile:
    skills: tuple[UserSkill, ...]
    source: str = 'manual'
    profile_id: str = 'my-career-profile'
    fixture_version: str = 'user-confirmed-v1'
    content_sha256: str = '0' * 64
    preferences_version: str = 'user-entered-v1'
    synthetic: bool = False
    interests: tuple = ()
    preferences: tuple = ()
    hours_per_week: int = 0
    budget_amount: int = 0
    budget_currency: str = 'MYR'

    def __post_init__(self):
        if self.source not in {'manual', 'confirmed_cv'} or self.synthetic is not False:
            raise ValueError('User profile provenance is invalid')
        if type(self.skills) is not tuple or not self.skills or len(self.skills) > 8:
            raise ValueError('User profile requires bounded skill states')
        if any(type(s) is not UserSkill or s.skill_id.scheme != 'local' or s.skill_id.scheme_version != 'demo-v1' for s in self.skills):
            raise ValueError('Only the approved demonstration skill vocabulary is supported')
        if len({s.skill_id for s in self.skills}) != len(self.skills):
            raise ValueError('Duplicate user skill')
