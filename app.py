"""Public, synthetic-only FuturePath demonstration."""

from __future__ import annotations

import streamlit as st

from services.ai_guidance import (
    AIValidationError,
    LearningPreferences,
    build_offline_roadmap,
    generate_career_advice,
    generate_career_chat,
    generate_learning_roadmap,
    generate_skill_gap_coaching,
    parse_monthly_budget,
)
from services.ai_runtime import AIGateway, AIGatewayFailure, ai_availability, new_session_id


PUBLIC_FAILURE_MESSAGE = "The synthetic demonstration is temporarily unavailable. Please try again shortly."
FRIENDLY_AI_ERRORS = {
    "disabled": "AI assistance is disabled for this deployment. The deterministic career tools remain available.",
    "missing_provider_key": "AI assistance is not configured for this deployment.",
    "shared_tls_budget_store_required": "AI assistance is unavailable because shared usage protection is not configured.",
    "shared_store_unavailable": "AI assistance is temporarily unavailable. Your career results are still available.",
    "shared_store_required": "AI assistance is temporarily unavailable. Your career results are still available.",
    "daily_request_limit": "The shared daily AI request limit has been reached.",
    "session_request_limit": "This session has reached its AI request limit.",
    "daily_budget_limit": "The shared AI usage budget has been reached.",
    "concurrency_limit": "AI is busy right now. Please try again shortly.",
    "timeout": "The AI service took too long to respond. Please try again.",
    "rate_limited": "The AI service is busy. Please try again later.",
    "provider_unavailable": "The AI service is temporarily unavailable.",
    "unauthorized": "AI assistance is not available with the current server configuration.",
    "invalid_response": "The AI response could not be safely checked. Try again or use the deterministic tools.",
    "provider_rejected_request": "The AI service could not process this request.",
    "usage_record_unavailable": "AI assistance is temporarily unavailable because usage protection could not be updated.",
    "invalid_limit_configuration": "AI assistance is unavailable because its server usage limits are invalid.",
    "provider_request_limit_exceeded": "AI assistance is unavailable because its request limits are inconsistent.",
    "provider_error": "AI assistance could not complete this request.",
}


@st.cache_resource(show_spinner=False)
def _gateway() -> AIGateway:
    return AIGateway.from_environment()


def _safe_gateway() -> AIGateway:
    availability = ai_availability()
    if not availability.configured:
        raise AIGatewayFailure(availability.reason)
    return _gateway()


def _show_ai_error(error: Exception) -> None:
    category = error.category if isinstance(error, AIGatewayFailure) else "invalid_response"
    st.warning(FRIENDLY_AI_ERRORS.get(category, FRIENDLY_AI_ERRORS["provider_error"]))


def _consent_control(availability) -> bool:
    st.subheader("Optional AI assistance")
    st.caption(
        "AI sends your selected synthetic skill states, the fictional career requirements, and the question or learning preferences you enter to RunPod. "
        "It does not send a name, contact details, uploaded CV, or the profile fixture identifier. Do not enter personal or sensitive information."
    )
    if not availability.configured:
        st.info(FRIENDLY_AI_ERRORS.get(availability.reason, "AI assistance is disabled for this deployment."))
        return False
    return st.checkbox(
        "I agree to send this synthetic career context to the AI provider for this session.",
        key="ai_consent",
        help="This choice applies only to the current browser session and can be turned off at any time.",
    )


def _current_session_id() -> str:
    if "ai_session_id" not in st.session_state:
        st.session_state.ai_session_id = new_session_id()
    return st.session_state.ai_session_id


def _skill_labels_by_code(profiles) -> dict[str, str]:
    return {skill_id.skill_code: label for skill_id, label in profiles.supported_skills}


def _render_ai_advisor(run, profiles, consented: bool) -> None:
    st.subheader("AI career advisor")
    if not run.ranked_results:
        st.info("Complete all required skill states for at least one fictional career to request a grounded explanation.")
        return
    results = run.ranked_results
    by_code = {item.occupation_id.source_code: item for item in results}
    selected = st.selectbox("Career to explain", tuple(by_code), format_func=lambda code: by_code[code].title, key="advisor_role")
    if st.button("Explain this recommendation", key="run_career_advisor", disabled=not consented):
        try:
            with st.spinner("Preparing a grounded explanation…"):
                answer = generate_career_advice(
                    _safe_gateway(), st.session_state.get("current_synthetic_profile"), by_code[selected],
                    dict(profiles.supported_skills), session_id=_current_session_id(), consented=consented,
                )
            st.markdown("**AI-generated guidance · not verified career advice**")
            st.write(answer.summary)
            for title, claims in (("Strengths", answer.strengths), ("Confirmed gaps", answer.gaps),
                                  ("Fit considerations", answer.fit_considerations), ("Next steps", answer.next_steps)):
                if claims:
                    st.markdown(f"**{title}**")
                    for claim in claims:
                        evidence = ", ".join(_skill_labels_by_code(profiles)[code] for code in claim.skill_codes)
                        st.markdown(f"- {claim.text}  \n  *Evidence: {evidence} (synthetic profile and requirements)*")
        except (AIGatewayFailure, AIValidationError, ValueError) as error:
            _show_ai_error(error)


def _render_skill_coach(run, profiles, consented: bool) -> None:
    st.subheader("AI skill gap coach")
    results = run.ranked_results
    if not results:
        st.info("Complete all required skill states to explore confirmed gaps.")
        return
    by_code = {item.occupation_id.source_code: item for item in results}
    selected = st.selectbox("Career to coach", tuple(by_code), format_func=lambda code: by_code[code].title, key="coach_role")
    if not by_code[selected].confirmed_gaps:
        st.info("There are no confirmed gaps for this career. Unknown and unreported skills are not treated as gaps.")
        return
    if st.button("Prioritize my confirmed gaps", key="run_skill_coach", disabled=not consented):
        try:
            with st.spinner("Preparing practice ideas…"):
                answer = generate_skill_gap_coaching(
                    _safe_gateway(), st.session_state.current_synthetic_profile, by_code[selected],
                    dict(profiles.supported_skills), session_id=_current_session_id(), consented=consented,
                )
            st.markdown("**AI-generated practice suggestions · not verified courses or credentials**")
            labels_by_code = _skill_labels_by_code(profiles)
            for index, item in enumerate(answer.priority_gaps, 1):
                label = labels_by_code[item.skill_code]
                with st.expander(f"{index}. {label}", expanded=True):
                    st.write(f"**Why it matters:** {item.reason}")
                    st.write(f"**Try this:** {item.exercise}")
                    st.write(f"**Show your progress:** {item.evidence}")
        except (AIGatewayFailure, AIValidationError, ValueError) as error:
            _show_ai_error(error)


def _render_learning(run, selected_profile, profiles, consented: bool) -> str | None:
    st.subheader("Learning plan")
    st.caption("Set these preferences for this plan. Blank budget means no budget preference was provided.")
    col1, col2 = st.columns(2)
    hours = col1.number_input("Available study hours per week", min_value=1, max_value=60, value=None,
                              step=1, key="learning_hours", placeholder="Enter your weekly hours")
    horizon = col2.number_input("Plan length in weeks", min_value=1, max_value=12, value=None,
                                step=1, key="learning_horizon", placeholder="Enter plan length")
    learning_format = st.selectbox("Preferred learning format", ["hands_on", "reading", "mixed"], index=None,
                                   format_func=lambda value: {"hands_on": "Hands-on practice", "reading": "Reading", "mixed": "A mix of both"}.get(value, "Choose a format"),
                                   placeholder="Choose a format",
                                   key="learning_format")
    budget_text = st.text_input("Optional monthly budget (MYR)", value="", key="learning_budget", placeholder="Leave blank if you have no budget preference")
    try:
        budget = parse_monthly_budget(budget_text)
        if hours is None or horizon is None or learning_format is None:
            preferences = None
        else:
            preferences = LearningPreferences(int(hours), learning_format, int(horizon), budget)
            preferences.validate()
    except ValueError as error:
        preferences = None
        st.error(str(error))
    if preferences is None:
        st.info("Enter your study hours, plan length, and preferred format to build a learning plan. No example preferences are assumed.")

    results = run.ranked_results + run.unranked_results
    if not results:
        st.info("Career matches will appear here after you complete your profile.")
        return None
    by_code = {item.occupation_id.source_code: item for item in results}
    selected = st.selectbox("Career for this plan", tuple(by_code), format_func=lambda code: by_code[code].title, key="roadmap_role")
    result = by_code[selected]
    profile = st.session_state.current_synthetic_profile
    labels = dict(profiles.supported_skills)
    if preferences is not None:
        offline = build_offline_roadmap(profile, result, labels, preferences)
        st.markdown("**Available plan**")
        if offline.weeks:
            st.caption(offline.note)
            for week in offline.weeks:
                st.markdown(f"**Week {week.week} · weekly time budget up to {week.hours} hours**")
                st.write(week.activity)
                st.caption("Skills covered: " + ", ".join(labels[skill_id] for skill_id in labels
                                                         if skill_id.skill_code in week.skill_codes))
                st.caption(f"Progress evidence: {week.evidence}")
        else:
            st.success("No confirmed gaps need a practice plan. Unknown skill states remain unscored.")
        if result.confirmed_gaps and st.button("Generate a personalized AI roadmap", key="run_ai_roadmap", disabled=not consented):
            try:
                with st.spinner("Building your roadmap…"):
                    answer = generate_learning_roadmap(
                        _safe_gateway(), profile, result, labels, preferences,
                        session_id=_current_session_id(), consented=consented,
                    )
                st.markdown("**AI-generated roadmap · synthetic practice only**")
                for week in answer.weeks:
                    st.markdown(f"**Week {week.week} · AI-suggested time: {week.hours} hours**")
                    st.write(week.activity)
                    st.caption("Skills covered: " + ", ".join(labels[skill_id] for skill_id in labels
                                                             if skill_id.skill_code in week.skill_codes))
                    st.caption(f"Progress evidence: {week.evidence}")
            except (AIGatewayFailure, AIValidationError, ValueError) as error:
                _show_ai_error(error)
    return selected


def _render_chat(run, profiles, consented: bool) -> None:
    st.subheader("Career chat")
    st.caption("Chat is limited to this browser session and the selected synthetic profile. Up to six recent turns are sent with each question.")
    results = run.ranked_results + run.unranked_results
    if not results:
        st.info("Complete your profile to start a grounded career conversation.")
        return
    by_code = {item.occupation_id.source_code: item for item in results}
    codes = tuple(by_code)
    selected = st.selectbox("Career context", codes, format_func=lambda code: by_code[code].title, key="chat_role")
    compare_code = st.selectbox("Optional second career to compare", (None, *codes), index=0,
                                format_func=lambda code: "No comparison" if code is None else by_code[code].title,
                                key="chat_comparison")
    question = st.text_area("Ask a career question", max_chars=1200, key="chat_question", placeholder="For example: Which confirmed gap should I practise first?")
    history = st.session_state.get("career_chat_history", [])
    evidence_by_turn = st.session_state.get("career_chat_evidence", {})
    followups_by_turn = st.session_state.get("career_chat_followups", {})
    labels_by_code = _skill_labels_by_code(profiles)
    for index, turn in enumerate(history):
        st.chat_message(turn["role"]).write(turn["content"])
        if turn["role"] == "assistant":
            codes = evidence_by_turn.get(str(index), [])
            if codes:
                st.caption("Evidence: " + ", ".join(labels_by_code[code] for code in codes))
            for question_suggestion in followups_by_turn.get(str(index), []):
                st.caption("Suggested follow-up: " + question_suggestion)
    if st.button("Send question", key="send_career_chat", disabled=not consented or not question.strip()):
        try:
            with st.spinner("Thinking…"):
                answer = generate_career_chat(
                    _safe_gateway(), st.session_state.current_synthetic_profile, by_code[selected],
                    dict(profiles.supported_skills), question, tuple(history[-6:]),
                    session_id=_current_session_id(), consented=consented,
                    comparison=by_code[compare_code] if compare_code is not None else None,
                )
            history = history + [{"role": "user", "content": question.strip()}, {"role": "assistant", "content": answer.answer}]
            retained = history[-12:]
            dropped = len(history) - len(retained)
            prior_evidence = st.session_state.get("career_chat_evidence", {})
            st.session_state.career_chat_evidence = {
                str(int(index) - dropped): codes for index, codes in prior_evidence.items()
                if int(index) >= dropped
            }
            st.session_state.career_chat_evidence[str(len(retained) - 1)] = list(answer.evidence_skill_codes)
            prior_followups = st.session_state.get("career_chat_followups", {})
            st.session_state.career_chat_followups = {
                str(int(index) - dropped): questions for index, questions in prior_followups.items()
                if int(index) >= dropped
            }
            st.session_state.career_chat_followups[str(len(retained) - 1)] = list(answer.follow_up_questions)
            st.session_state.career_chat_history = retained
            st.rerun()
        except (AIGatewayFailure, AIValidationError, ValueError) as error:
            _show_ai_error(error)
    if history:
        st.caption("AI-generated responses are suggestions based only on the synthetic information shown here.")
        if st.button("Clear this session's chat", key="clear_chat"):
            st.session_state.career_chat_history = []
            st.session_state.career_chat_evidence = {}
            st.session_state.career_chat_followups = {}
            st.rerun()


def render_public_app() -> None:
    from fixtures.synthetic_profiles import load_profile_bundle
    from fixtures.synthetic_requirements import load_requirement_bundle
    from ui.skills_intake import render_skills_intake
    from ui.synthetic_matching import calculate_synthetic_matching, profile_with_session_states, render_synthetic_matching
    from ui.synthetic_journey import render_career_comparison, render_disclosures, render_learning_path

    st.set_page_config(page_title="FuturePath Intelligence", page_icon="🧭", layout="wide", initial_sidebar_state="collapsed")
    _current_session_id()
    st.title("FuturePath Intelligence")
    st.caption("Explore fictional career paths with transparent, skills-based guidance.")
    st.warning("Synthetic demonstration only. Career paths and skill requirements are fictional and are not real career advice.", icon="⚠️")
    st.write("Explore your profile, compare fictional careers, review practice ideas, and optionally ask for AI-generated explanations.")

    profiles = load_profile_bundle()
    requirements = load_requirement_bundle()
    consented = _consent_control(ai_availability())
    tabs = st.tabs(["Profile", "Career matches", "Learning plan", "AI career chat", "Data and privacy"])
    with tabs[0]:
        selected_profile = render_skills_intake(st, profiles)
    st.session_state.current_synthetic_profile = profile_with_session_states(st.session_state, selected_profile)
    run = calculate_synthetic_matching(st.session_state, selected_profile, requirements)
    with tabs[1]:
        render_synthetic_matching(st, selected_profile, profiles, requirements, run=run)
        render_career_comparison(st, run, profiles)
        _render_ai_advisor(run, profiles, consented)
        _render_skill_coach(run, profiles, consented)
    with tabs[2]:
        selected_role = _render_learning(run, selected_profile, profiles, consented)
        if selected_role is not None:
            render_learning_path(st, st.session_state.current_synthetic_profile, run, profiles,
                                 role_code=selected_role)
    with tabs[3]:
        _render_chat(run, profiles, consented)
    with tabs[4]:
        render_disclosures(st, profiles, requirements, run)
        st.markdown("**Privacy**")
        st.write("Profile edits and chat history stay in this browser session. No profile file or CV upload is created. AI sharing is optional and requires a separate session consent.")
        st.write("**AI limits**")
        st.write("AI text is generated advice based on fictional demonstration inputs. It is not verified labour-market data, a hiring forecast, or a substitute for independent research.")
        st.write("**When AI is unavailable**")
        st.write("Deterministic matching, career comparison, and the rule-based practice plan remain available without AI.")


try:
    render_public_app()
except Exception:
    st.error(PUBLIC_FAILURE_MESSAGE)
    st.stop()
