"""English presentation and deterministic matching for fictional occupations."""

from dataclasses import replace

from domain.models import SkillId, SkillState, SyntheticProfile, UserSkill
from fixtures.synthetic_profiles import SyntheticProfileBundle
from fixtures.synthetic_requirements import FictionalRequirementBundle
from services.matching import MatchResult, SyntheticMatchingRun, match_synthetic_profile


def profile_with_session_states(session_state: dict, profile: SyntheticProfile) -> SyntheticProfile:
    states = session_state.get("intake_by_profile", {}).get(profile.profile_id)
    if not isinstance(states, dict):
        raise ValueError("The current profile is unavailable. Please select it again.")
    skills = tuple(UserSkill(skill.skill_id, SkillState(states[skill.skill_id.skill_code]), skill.evidence_refs)
                   for skill in profile.skills)
    return replace(profile, skills=skills)


def calculate_synthetic_matching(session_state: dict, profile: SyntheticProfile,
                                 requirements: FictionalRequirementBundle) -> SyntheticMatchingRun:
    """Calculate results from the active browser session's skill states."""
    return match_synthetic_profile(profile_with_session_states(session_state, profile), requirements)


def _format_skills(skill_ids, labels_by_id: dict[SkillId, str]) -> str:
    return ", ".join(labels_by_id[identity] for identity in skill_ids) if skill_ids else "None"


def _render_result(st, result: MatchResult, labels_by_id: dict[SkillId, str]) -> None:
    with st.expander(result.title, expanded=True):
        st.caption("Fictional team-authored requirements for this synthetic demonstration.")
        if result.status == "complete":
            st.success("All fictional requirement states are known. The score is the share of listed skills marked as present.")
            st.metric("Information coverage", f"{result.information_coverage:.0%}")
            st.metric("Synthetic skill coverage", f"{result.score:.0f} / 100")
        elif result.status == "insufficient_profile":
            st.info("There is not enough reported information to calculate or rank a score.")
            st.metric("Information coverage", f"{result.information_coverage:.0%}")
            st.caption(f"Known-state score bounds: {result.M_lower:.0%}–{result.M_upper:.0%}. These arithmetic bounds are not a statistical confidence interval.")
        else:
            st.info("There are no scorable fictional requirements for this career.")

        groups = (
            ("Skills marked present", result.matched_skills),
            ("Confirmed gaps", result.confirmed_gaps),
            ("Not sure", result.unknown_skills),
            ("Not reported", result.not_reported_skills),
        )
        for label, skills in groups:
            st.markdown(f"**{label}:** {_format_skills(skills, labels_by_id)}")


def render_synthetic_matching(st, profile: SyntheticProfile, profiles: SyntheticProfileBundle,
                              requirements: FictionalRequirementBundle,
                              *, run: SyntheticMatchingRun | None = None) -> SyntheticMatchingRun:
    """Run and render only the approved synthetic demo requirements."""
    st.subheader("Career matches")
    st.caption("Scores reflect only the share of fictional requirements marked present. They are not probabilities, employment forecasts, or measures of real-world suitability.")
    run = run or calculate_synthetic_matching(st.session_state, profile, requirements)
    labels_by_id = dict(profiles.supported_skills)
    if run.ranked_results:
        st.markdown("**Careers with complete profile information**")
        for result in run.ranked_results:
            _render_result(st, result, labels_by_id)
    else:
        st.info("No career has a complete set of reported skill states yet. Review the profile and mark each skill as present, not present, not sure, or not reported.")

    if run.unranked_results:
        st.markdown("**Careers with incomplete profile information**")
        for result in run.unranked_results:
            _render_result(st, result, labels_by_id)
    return run
