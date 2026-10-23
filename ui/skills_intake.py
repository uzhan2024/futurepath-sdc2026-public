"""Synthetic-only, session-scoped Skills Intake UI."""

from domain.models import SkillState, SyntheticProfile
from services.profile_intake import ensure_profile_state, reset_profile_state, update_skill_state


STATE_LABELS = {
    SkillState.KNOWN_PRESENT.value: "已知具备",
    SkillState.KNOWN_ABSENT.value: "已确认不具备",
    SkillState.UNKNOWN.value: "尚不确定",
    SkillState.NOT_REPORTED.value: "未报告",
}


def render_skills_intake(st, bundle) -> SyntheticProfile:
    st.subheader("Skills Intake · 合成档案")
    st.caption("仅编辑合成示例；内容保存在当前浏览器会话，不会写入文件。")
    profiles = bundle.profiles
    labels = {f"合成档案 {index + 1}（{profile.profile_id}）": profile
              for index, profile in enumerate(profiles)}
    selected_label = st.selectbox("选择合成档案", list(labels), key="intake_profile_choice")
    profile = labels[selected_label]
    states = ensure_profile_state(st.session_state, profile)
    widget_keys = {skill.skill_id.skill_code: f"skill_state_{profile.profile_id}_{skill.skill_id.skill_code}"
                   for skill in profile.skills}
    for skill in profile.skills:
        code = skill.skill_id.skill_code
        st.session_state.setdefault(widget_keys[code], states[code])

    if st.button("重置当前档案", key="reset_current_profile"):
        defaults = reset_profile_state(st.session_state, profile)
        for code, key in widget_keys.items():
            st.session_state[key] = defaults[code]

    st.caption(f"档案版本 {profile.fixture_version} · 偏好版本 {profile.preferences_version} · "
               f"预算 {profile.budget_amount} {profile.budget_currency} · 每周 {profile.hours_per_week} 小时")
    st.caption("状态定义：已知具备、已确认不具备、尚不确定、未报告。未报告与尚不确定都不表示缺少技能。")
    labels_by_code = {skill_id.skill_code: label for skill_id, label in bundle.supported_skills}
    supported = set(labels_by_code)

    def sync_state(code: str, key: str) -> None:
        update_skill_state(st.session_state, profile, code, st.session_state[key], supported)

    for code, key in widget_keys.items():
        st.selectbox(
            labels_by_code[code], options=list(STATE_LABELS),
            format_func=lambda value: STATE_LABELS[value], key=key,
            on_change=sync_state, args=(code, key),
        )
    return profile
