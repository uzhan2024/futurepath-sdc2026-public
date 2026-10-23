"""Comparison, self-directed practice, and provenance for the public demo."""

from __future__ import annotations

from domain.models import SkillId, SyntheticProfile
from fixtures.synthetic_profiles import SyntheticProfileBundle
from fixtures.synthetic_requirements import FictionalRequirementBundle
from services.matching import MatchResult, SyntheticMatchingRun
from services.synthetic_journey import build_practice_path, compare_fictional_roles


def _results(run: SyntheticMatchingRun) -> tuple[MatchResult, ...]:
    return run.ranked_results + run.unranked_results


def _skill_names(skills: tuple[SkillId, ...], labels: dict[SkillId, str]) -> str:
    return "、".join(labels[skill] for skill in skills) if skills else "无"


def render_career_comparison(st, run: SyntheticMatchingRun,
                             profiles: SyntheticProfileBundle) -> None:
    """Show all role states and let a visitor inspect two requirement sets."""
    st.subheader("比较三条虚构职业路线")
    st.caption("只对资料完整的角色显示演示点分；点分是已知具备技能比例，不是适合度概率或就业预测。")
    results = _results(run)
    st.table([{
        "虚构路线": result.title,
        "资料覆盖": f"{result.information_coverage:.0%}",
        "已确认缺口": len(result.confirmed_gaps),
        "待核实": len(result.unknown_skills) + len(result.not_reported_skills),
        "演示点分": f"{result.score:.0f} / 100" if result.score is not None else "资料不足",
    } for result in results])

    by_code = {result.occupation_id.source_code: result for result in results}
    codes = tuple(by_code)
    left_code = st.selectbox("对照路线 A", codes, key="compare_role_a",
                             format_func=lambda code: by_code[code].title)
    right_code = st.selectbox("对照路线 B", codes, index=1, key="compare_role_b",
                              format_func=lambda code: by_code[code].title)
    if left_code == right_code:
        st.info("选择两条不同的虚构路线，查看要求差异。")
        return
    comparison = compare_fictional_roles(by_code[left_code], by_code[right_code])
    labels = dict(profiles.supported_skills)
    st.markdown(f"**共同要求：** {_skill_names(comparison.shared_skills, labels)}")
    st.markdown(f"**仅路线 A 要求：** {_skill_names(comparison.left_only_skills, labels)}")
    st.markdown(f"**仅路线 B 要求：** {_skill_names(comparison.right_only_skills, labels)}")
    st.caption("比较固定当前合成档案、虚构要求和规则；未知／未报告不计作缺口。")


def render_learning_path(st, profile: SyntheticProfile, run: SyntheticMatchingRun,
                         profiles: SyntheticProfileBundle) -> None:
    """Let a visitor choose and track illustrative exercises in this session."""
    st.subheader("自选学习路线 · 合成练习")
    st.caption("以下为团队编写的自学练习，不是经核实的课程、学费或完成时长。")
    by_code = {result.occupation_id.source_code: result for result in _results(run)}
    role_code = st.selectbox("选择要探索的虚构路线", tuple(by_code), key="path_role_choice",
                             format_func=lambda code: by_code[code].title)
    result = by_code[role_code]
    labels = dict(profiles.supported_skills)
    path = build_practice_path(result, labels)

    if st.button("我选择这条合成路线", key="choose_synthetic_path"):
        st.session_state.setdefault("chosen_path_by_profile", {})[profile.profile_id] = role_code
    chosen = st.session_state.get("chosen_path_by_profile", {}).get(profile.profile_id)
    if chosen == role_code:
        st.success("已在当前会话记录此合成选择；你可随时改选，系统不会替你决定职业。")
    elif chosen:
        st.caption(f"当前会话已选择另一条虚构路线：{by_code[chosen].title}。")

    if path.unknown_skills or path.not_reported_skills:
        st.info("先核实未确定的技能状态；它们不属于已确认缺口，也不产生完整点分。")
        st.markdown("**尚不确定：** " + ("、".join(path.unknown_skills) or "无"))
        st.markdown("**未报告：** " + ("、".join(path.not_reported_skills) or "无"))
    if path.confirmed_gap_steps:
        st.markdown("**针对已确认缺口的示例练习**")
        completed = 0
        for index, step in enumerate(path.confirmed_gap_steps, 1):
            st.markdown(f"{index}. **{step.label}**：{step.activity}")
            st.caption(f"可保留的练习记录：{step.evidence_to_keep}")
            if st.checkbox("本会话已做练习（不代表能力认证）",
                           key=f"practice_{profile.profile_id}_{role_code}_{step.skill_id.skill_code}"):
                completed += 1
        st.progress(completed / len(path.confirmed_gap_steps),
                    text=f"示例练习记录 {completed}/{len(path.confirmed_gap_steps)}")
    else:
        st.success("当前没有已确认的虚构要求缺口；可先核实不确定项或探索另一条路线。")
    st.caption(f"档案每周可用 {profile.hours_per_week} 小时；本演示不据此推断课程时长、费用或完成日期。")
    st.caption("练习勾选只保存在当前浏览器会话，不会自动改变技能状态或匹配结果。")


def render_disclosures(st, profiles: SyntheticProfileBundle,
                       requirements: FictionalRequirementBundle,
                       run: SyntheticMatchingRun) -> None:
    st.subheader("依据、版本与适用范围")
    st.markdown(
        "- 档案与技能：三份本地合成档案；无真实简历上传。\n"
        "- 职业要求：三组团队编写的虚构要求，未使用待审职业记录。\n"
        "- 匹配：每项要求等权；只有全部要求状态已知时才显示已知具备比例。\n"
        "- 学习路线：自学练习示例；没有核实课程、费用、先修条件或预计完成时间。\n"
        "- 研究趋势与招聘需求：此版本不提供趋势计分，也不预测就业概率。"
    )
    st.caption(f"合成档案版本：{profiles.fixture_version} · 虚构要求版本：{requirements.fixture_version}")
    st.caption(f"档案 SHA-256：{profiles.content_sha256} · 要求 SHA-256：{requirements.content_sha256}")
    st.caption(f"规则：{run.rule_version} · 模式：{run.scoring_mode} · 本次输入指纹：{run.input_fingerprint}")
    st.caption("以上指纹用于追溯本地合成输入和规则；不冒充 Git Commit 或 Replit 发布证明。")
