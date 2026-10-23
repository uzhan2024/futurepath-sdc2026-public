"""Pure four-state profile editing helpers for Streamlit session state."""

from domain.models import SkillState, SyntheticProfile


def initial_skill_states(profile: SyntheticProfile) -> dict[str, str]:
    return {skill.skill_id.skill_code: skill.state.value for skill in profile.skills}


def ensure_profile_state(session_state: dict, profile: SyntheticProfile) -> dict[str, str]:
    """Initialize this browser session's copy from a fixture exactly once."""
    states = session_state.setdefault("intake_by_profile", {})
    return states.setdefault(profile.profile_id, initial_skill_states(profile))


def update_skill_state(session_state: dict, profile: SyntheticProfile, skill_code: str,
                       state: str, supported_codes: set[str]) -> None:
    if skill_code not in supported_codes or skill_code not in initial_skill_states(profile):
        raise ValueError("unsupported profile skill")
    parsed = SkillState(state)
    ensure_profile_state(session_state, profile)[skill_code] = parsed.value


def reset_profile_state(session_state: dict, profile: SyntheticProfile) -> dict[str, str]:
    """Reset only this profile in the current session to its fixture defaults."""
    states = session_state.setdefault("intake_by_profile", {})
    states[profile.profile_id] = initial_skill_states(profile)
    return states[profile.profile_id]
