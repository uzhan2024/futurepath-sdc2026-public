"""Career comparison, practice planning, and user-facing disclosures."""

from domain.models import SkillId, SyntheticProfile
from fixtures.synthetic_profiles import SyntheticProfileBundle
from fixtures.synthetic_requirements import FictionalRequirementBundle
from services.matching import SyntheticMatchingRun
from services.synthetic_journey import build_practice_path, compare_fictional_roles


def _results(run: SyntheticMatchingRun):
    return run.ranked_results + run.unranked_results


def _skill_names(skills: tuple[SkillId, ...], labels: dict[SkillId, str]) -> str:
    return ", ".join(labels[skill] for skill in skills) if skills else "None"


def render_career_comparison(st, run: SyntheticMatchingRun,
                             profiles: SyntheticProfileBundle) -> None:
    st.subheader("Compare fictional careers")
    st.caption("The table shows information coverage and confirmed gaps. Unknown and unreported skills are not treated as missing.")
    results = _results(run)
    st.table([{
        "Fictional career": result.title,
        "Profile information": f"{result.information_coverage:.0%}",
        "Confirmed gaps": len(result.confirmed_gaps),
        "Needs review": len(result.unknown_skills) + len(result.not_reported_skills),
        "Synthetic skill coverage": f"{result.score:.0f} / 100" if result.score is not None else "Not scored",
    } for result in results])
    if len(results) < 2:
        st.info("At least two fictional careers are needed for a comparison.")
        return
    by_code = {result.occupation_id.source_code: result for result in results}
    codes = tuple(by_code)
    left_code = st.selectbox("First career", codes, key="compare_role_a", format_func=lambda code: by_code[code].title)
    right_code = st.selectbox("Second career", codes, index=1, key="compare_role_b", format_func=lambda code: by_code[code].title)
    if left_code == right_code:
        st.info("Choose two different careers to see their requirement differences.")
        return
    comparison = compare_fictional_roles(by_code[left_code], by_code[right_code])
    labels = dict(profiles.supported_skills)
    st.markdown(f"**Shared skills:** {_skill_names(comparison.shared_skills, labels)}")
    st.markdown(f"**Only in {by_code[left_code].title}:** {_skill_names(comparison.left_only_skills, labels)}")
    st.markdown(f"**Only in {by_code[right_code].title}:** {_skill_names(comparison.right_only_skills, labels)}")
    st.caption("This comparison uses only the fictional profile and fictional requirements in this demonstration.")


def render_learning_path(st, profile: SyntheticProfile, run: SyntheticMatchingRun,
                         profiles: SyntheticProfileBundle, *, role_code: str) -> None:
    st.subheader("Practice ideas")
    st.caption("These are team-authored self-directed exercises, not verified courses, credentials, prices, or completion estimates.")
    by_code = {result.occupation_id.source_code: result for result in _results(run)}
    if role_code not in by_code:
        st.info("Choose a career to explore practice ideas.")
        return
    result = by_code[role_code]
    labels = dict(profiles.supported_skills)
    path = build_practice_path(result, labels)

    if st.button("Save this exploration choice for this session", key="choose_synthetic_path"):
        st.session_state.setdefault("chosen_path_by_profile", {})[profile.profile_id] = role_code
    chosen = st.session_state.get("chosen_path_by_profile", {}).get(profile.profile_id)
    if chosen == role_code:
        st.success("This is your current exploration choice. You can change it at any time.")

    if path.unknown_skills or path.not_reported_skills:
        st.info("Review uncertain skill states first. They are not confirmed gaps.")
        st.markdown("**Not sure:** " + (", ".join(path.unknown_skills) or "None"))
        st.markdown("**Not reported:** " + (", ".join(path.not_reported_skills) or "None"))
    if path.confirmed_gap_steps:
        st.markdown("**Exercises for confirmed gaps**")
        completed = 0
        for index, step in enumerate(path.confirmed_gap_steps, 1):
            st.markdown(f"{index}. **{step.label}**: {step.activity}")
            st.caption(f"Progress evidence: {step.evidence_to_keep}")
            if st.checkbox("I practised this in this session (not a skills credential)",
                           key=f"practice_{profile.profile_id}_{role_code}_{step.skill_id.skill_code}"):
                completed += 1
        st.progress(completed / len(path.confirmed_gap_steps), text=f"Practice notes recorded: {completed}/{len(path.confirmed_gap_steps)}")
    else:
        st.success("There are no confirmed gaps for this fictional career. You can review uncertain skills or explore another career.")
    st.caption("Practice checkmarks remain in this browser session. They do not change your skill states or match results.")


def render_disclosures(st, profiles: SyntheticProfileBundle,
                       requirements: FictionalRequirementBundle,
                       run: SyntheticMatchingRun) -> None:
    st.subheader("Data, privacy, and limitations")
    st.markdown(
        "- **Profiles and skills:** Fictional sample profiles. No CV upload is available.\n"
        "- **Career requirements:** Team-authored fictional demonstration data, separate from any pending occupation dataset.\n"
        "- **Matching:** Equal-weight skill coverage is shown only when all requirement states are known. A score is not a probability or employment prediction.\n"
        "- **Learning:** Practice ideas are illustrative. No verified courses, prices, credentials, or completion dates are provided.\n"
        "- **Labour-market evidence:** This prototype does not provide current vacancies, salary data, workforce trends, or hiring forecasts.\n"
        "- **AI:** Optional generated explanations use the selected synthetic skill states and fictional requirements. AI text is unverified and never changes the deterministic match score."
    )
    st.caption("Profile edits and generated chat history are held in the current browser session. No profile file is created.")
