"""Streamlit presentation for the existing fictional matching service."""

from dataclasses import replace

from domain.models import SkillId, SkillState, SyntheticProfile, UserSkill
from fixtures.synthetic_profiles import SyntheticProfileBundle
from fixtures.synthetic_requirements import FictionalRequirementBundle
from services.matching import MatchResult, SyntheticMatchingRun, match_synthetic_profile


def _profile_with_session_states(profile: SyntheticProfile, session_states: dict) -> SyntheticProfile:
    """Create an in-memory profile copy from this browser's per-profile state."""
    states = session_states.get("intake_by_profile", {}).get(profile.profile_id)
    if not isinstance(states, dict):
        raise ValueError("current synthetic profile session state is unavailable")
    skills = tuple(
        UserSkill(skill.skill_id, SkillState(states[skill.skill_id.skill_code]), skill.evidence_refs)
        for skill in profile.skills
    )
    return replace(profile, skills=skills)


def _format_skills(skill_ids, labels_by_id: dict[SkillId, str]) -> str:
    if not skill_ids:
        return "无"
    return "、".join(labels_by_id[identity] for identity in skill_ids)


def _render_result(st, result: MatchResult, labels_by_id: dict[SkillId, str]) -> None:
    role_id = result.occupation_id.source_code
    with st.expander(f"{result.title} · {role_id}", expanded=True):
        st.caption("要求来源：团队编写的虚构 synthetic demo fixture；不代表真实职业或外部证据。")
        st.caption(f"评分范围：{result.scoring_scope} · 模式：{result.scoring_mode}")
        if result.status == "complete":
            st.success("演示要求的四态资料完整；下方点分仅表示虚构技能集合中的已知具备比例。")
            st.metric("虚构要求覆盖", f"{result.information_coverage:.0%}")
            st.metric("演示技能覆盖点分", f"{result.score:.0f} / 100")
        elif result.status == "insufficient_profile":
            st.info("资料不足（insufficient_profile）：不显示点分，也不参与完整结果排序。")
            st.metric("信息覆盖率", f"{result.information_coverage:.0%}")
            st.caption(
                f"已知状态范围：{result.M_lower:.0%}–{result.M_upper:.0%}；"
                f"已知项中的具备比例 M_known："
                f"{'未定义' if result.M_known is None else f'{result.M_known:.0%}'}。"
                "范围只表达缺失信息的算术上下界，不是统计置信区间。"
            )
        else:
            st.info("没有可评分的虚构要求；点分与覆盖指标均未定义。")

        groups = (
            ("已知具备（matched skills）", result.matched_skills),
            ("已确认不具备（confirmed gaps）", result.confirmed_gaps),
            ("尚不确定（unknown）", result.unknown_skills),
            ("未报告（not_reported）", result.not_reported_skills),
        )
        for label, skills in groups:
            st.markdown(f"**{label}**：{_format_skills(skills, labels_by_id)}")


def render_synthetic_matching(st, profile: SyntheticProfile, profiles: SyntheticProfileBundle,
                              requirements: FictionalRequirementBundle) -> SyntheticMatchingRun:
    """Run and render only the pinned synthetic demo requirements."""
    st.subheader("虚构职业要求档案与匹配演示")
    st.warning("Synthetic Demonstration — Not Real Career Advice")
    st.caption(
        "以下三组要求独立于 O*NET 待审数据，由团队为合成档案演示编写。"
        "技能状态变化会在当前会话重新计算；结果不保存到磁盘或发送到外部。"
    )
    labels_by_id = {identity: label for identity, label in profiles.supported_skills}
    session_profile = _profile_with_session_states(profile, st.session_state)
    run = match_synthetic_profile(session_profile, requirements)

    st.markdown("**资料完整的虚构演示结果**")
    if run.ranked_results:
        for result in run.ranked_results:
            _render_result(st, result, labels_by_id)
    else:
        st.caption("当前没有资料完整的虚构要求；所有角色均不显示点分。")

    st.markdown("**资料不足的虚构要求（不参与点分排序）**")
    if run.unranked_results:
        for result in run.unranked_results:
            _render_result(st, result, labels_by_id)
    else:
        st.caption("当前没有资料不足的虚构要求。")
    return run
