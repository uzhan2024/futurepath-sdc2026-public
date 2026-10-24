"""English-only synthetic profile editor scoped to the browser session."""

from domain.models import SkillState, SyntheticProfile
from services.profile_intake import ensure_profile_state, reset_profile_state, update_skill_state


STATE_LABELS = {
    SkillState.KNOWN_PRESENT.value: "I have this skill",
    SkillState.KNOWN_ABSENT.value: "I do not have this skill",
    SkillState.UNKNOWN.value: "I am not sure",
    SkillState.NOT_REPORTED.value: "I have not reported this",
}


def render_skills_intake(st, bundle) -> SyntheticProfile:
    st.subheader("Your profile")
    st.caption("Choose a sample or My profile, then report your skill states. Changes stay in this browser session.")
    profiles = bundle.profiles
    labels = {f"Sample profile {index + 1}": profile for index, profile in enumerate(profiles)}
    from domain.career_profile import ConfirmedCareerProfile
    from domain.models import UserSkill
    st.session_state.setdefault('career_user_profile', ConfirmedCareerProfile(tuple(UserSkill(identity) for identity, _ in bundle.supported_skills)))
    labels['My profile'] = st.session_state.career_user_profile
    selected_label = st.selectbox("Select a sample profile", list(labels), key="intake_profile_choice")
    profile = labels[selected_label]
    if not profile.synthetic:
        st.info('These are your confirmed skill states, compared against fictional occupation requirements. Resume suggestions do not enter this profile automatically.')
    states = ensure_profile_state(st.session_state, profile)
    widget_keys = {skill.skill_id.skill_code: f"skill_state_{profile.profile_id}_{skill.skill_id.skill_code}"
                   for skill in profile.skills}
    for skill in profile.skills:
        code = skill.skill_id.skill_code
        st.session_state.setdefault(widget_keys[code], states[code])

    if st.button("Reset this profile", key="reset_current_profile"):
        defaults = reset_profile_state(st.session_state, profile)
        for code, key in widget_keys.items():
            st.session_state[key] = defaults[code]

    st.caption("Not sure and not reported are different from a confirmed gap. Only skills marked as not present count as confirmed gaps.")
    labels_by_code = {skill_id.skill_code: label for skill_id, label in bundle.supported_skills}
    supported = set(labels_by_code)

    def sync_state(code: str, key: str) -> None:
        update_skill_state(st.session_state, profile, code, st.session_state[key], supported)

    for code, key in widget_keys.items():
        st.selectbox(labels_by_code[code], options=list(STATE_LABELS),
                     format_func=lambda value: STATE_LABELS[value], key=key,
                     on_change=sync_state, args=(code, key))
    return profile
