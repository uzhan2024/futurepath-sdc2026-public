"""Public, offline synthetic demonstration entry point."""

import hashlib
import platform
from pathlib import Path

import streamlit as st

APP_VERSION = "0.2.0-step26-public-synthetic"
PUBLIC_FAILURE_MESSAGE = "合成演示暂时不可用。请稍后重试。"


def render_public_app() -> None:
    from fixtures.synthetic_profiles import load_profile_bundle
    from fixtures.synthetic_requirements import load_requirement_bundle
    from ui.skills_intake import render_skills_intake
    from ui.synthetic_matching import render_synthetic_matching

    source_id = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:12]
    st.set_page_config(
        page_title="FuturePath · Synthetic Demo",
        page_icon="🧭",
        layout="centered",
        initial_sidebar_state="collapsed",
    )

    st.title("FuturePath Intelligence")
    st.caption("可解释的技能探索 · 交互式合成演示")
    st.warning("Synthetic Demonstration — Not Real Career Advice", icon="⚠️")
    st.write(
        "选择一个完全虚构的学习者档案，调整技能状态，观察技能覆盖与资料完整度如何改变。"
        "所有要求均为团队编写的虚构示例。"
    )

    st.subheader("本演示提供什么")
    st.markdown(
        "- **已实现：** 三份合成档案、四态技能输入、三组虚构技能要求及可解释的合成覆盖结果。\n"
        "- **尚未实现：** 经审核的真实职业要求、职业建议、课程与价格、研究趋势、就业预测和 SDG 影响。"
    )
    st.caption("未知与未报告都不等于缺少技能；只有“已确认不具备”会作为确认缺口显示。")
    st.divider()

    profiles = load_profile_bundle()
    requirements = load_requirement_bundle()
    selected_profile = render_skills_intake(st, profiles)
    render_synthetic_matching(st, selected_profile, profiles, requirements)

    st.divider()
    with st.expander("运行状态、版本与健康检查"):
        st.success("页面已启动；Streamlit 服务健康端点由框架提供。")
        st.text(f"应用版本：{APP_VERSION}")
        st.text(f"app.py 指纹：{source_id}（不是 Git SHA）")
        st.text(f"Python {platform.python_version()} · Streamlit {st.__version__}")
        st.caption("健康检查路径：/_stcore/health。它只检查服务可响应，不代表完整产品或发布验收。")
        st.caption("技能编辑仅保存在当前浏览器 session；刷新或断线后 session 可能重置。")


try:
    render_public_app()
except Exception:
    st.error(PUBLIC_FAILURE_MESSAGE)
    st.stop()
