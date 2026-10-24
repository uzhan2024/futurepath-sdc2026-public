"""Optional local resume review UI. No raw document or draft enters matching automatically."""
import os

from services.ai_runtime import public_mode, provider_choice
from services.resume_parsing import ResumeError, extract_resume
from services.resume_profile import confirm_skill_states, extract_draft
from services.ai_guidance import AIValidationError
from services.ai_runtime import AIGatewayFailure
from ui.skills_intake import STATE_LABELS


def cv_enabled():
    return not public_mode() and os.getenv('FUTUREPATH_CV_ENABLED', 'true').casefold() == 'true'


def apply_confirmation(state, skill_ids):
    claims = state['cv_draft']
    generation = state.get('cv_generation', 0)
    selections = {c.skill_code: state[f'cv_state_{generation}_{c.skill_code}'] for c in claims if c.skill_code}
    profile = confirm_skill_states(claims, selections, skill_ids, reviewed=state.get('cv_reviewed') is True)
    state['career_user_profile'] = profile
    state['intake_profile_choice'] = 'My profile'
    states = {s.skill_id.skill_code: s.state.value for s in profile.skills}
    state.setdefault('intake_by_profile', {})[profile.profile_id] = states
    for code, value in states.items():
        state[f'skill_state_{profile.profile_id}_{code}'] = value
    for key in ['career_chat_history', 'career_chat_evidence', 'career_chat_followups']:
        state.pop(key, None)
    state['cv_applied'] = True
    state['product_tab'] = 'My Career Profile'


def clear_resume(state):
    for key in list(state):
        if key.startswith('cv_') and key != 'cv_upload_epoch':
            del state[key]
    state['cv_upload_epoch'] = state.get('cv_upload_epoch', 0) + 1


def render_resume_import(st, profiles, gateway_factory, session_id):
    st.subheader('Import a resume, keep control of your profile')
    st.write('AI can suggest a draft from document evidence. A mentioned skill is not proof of proficiency; only your explicit choices enter matching.')
    if not cv_enabled():
        st.info('Resume upload is disabled in this public deployment. You can build your profile manually.')
        return
    st.caption('Local-only processing. English text PDF or DOCX, up to 2 MB, 10 PDF pages and 12,000 text bytes. No OCR. No cloud resume processing is offered.')
    st.caption('Files are processed in memory in a bounded child process. Clear removes application draft state; the host/Streamlit may retain upload buffers until session cleanup. Do not upload sensitive information.')
    upload = st.file_uploader('Choose a PDF or DOCX resume', type=['pdf', 'docx'],
                              key=f"resume_upload_{st.session_state.get('cv_upload_epoch', 0)}")
    if upload is not None:
        consent = st.checkbox('I agree to parse this document and send minimized text to local Ollama for a draft.', key='cv_local_consent')
        if st.button('Extract a draft profile', key='extract_resume', disabled=not consent, type='primary'):
            try:
                if provider_choice() != 'ollama':
                    raise AIGatewayFailure('local_provider_required')
                with st.spinner('Reading document evidence and preparing local suggestions…'):
                    text = extract_resume(upload.getvalue(), upload.name)
                    labels = {k.skill_code: v for k, v in profiles.supported_skills}
                    draft = extract_draft(text, gateway_factory(), labels, session_id=session_id, consented=consent)
                st.session_state.cv_draft = draft
                st.session_state.cv_generation = st.session_state.get('cv_generation', 0) + 1
                st.session_state.cv_reviewed = False
                st.session_state.cv_applied = False
            except (ResumeError, AIValidationError, AIGatewayFailure, ValueError):
                st.warning('This document could not produce a safely checked local draft. Try a simpler English text document or continue manually. No skill states were changed.')
    if 'cv_draft' in st.session_state:
        st.markdown('**Review the evidence before applying any skill**')
        st.caption('Only individually checked source quotes are retained; unsupported AI claims are discarded. Skill suggestions also use controlled vocabulary matching over those quotes. Neither is a proficiency assessment.')
        claims = st.session_state.cv_draft
        for category in ['education', 'employment', 'project', 'certification']:
            group = [c for c in claims if c.category == category]
            if group:
                with st.expander(category.title() + ' suggestions'):
                    for claim in group:
                        st.text(claim.label)
                        st.text('Source quote: ' + claim.evidence)
        seen = set()
        labels = {k.skill_code: v for k, v in profiles.supported_skills}
        for claim in claims:
            if not claim.skill_code or claim.skill_code in seen:
                continue
            seen.add(claim.skill_code)
            with st.container(border=True):
                st.markdown('**' + labels[claim.skill_code] + '**')
                st.text('Unverified source quote: ' + claim.evidence)
                st.selectbox('Choose your confirmed skill state', list(STATE_LABELS), index=2,
                    format_func=STATE_LABELS.get, key=f'cv_state_{st.session_state.cv_generation}_{claim.skill_code}')
        if seen:
            st.checkbox('I reviewed each suggested skill and chose the state myself.', key='cv_reviewed')
            st.button('Apply confirmed skill states', key='apply_resume', type='primary',
                disabled=not st.session_state.get('cv_reviewed'), on_click=apply_confirmation,
                args=(st.session_state, {k.skill_code: k for k, _ in profiles.supported_skills}))
        else:
            st.info('No supported skill could be safely mapped. You can enter your own states in My Career Profile.')
        if st.session_state.get('cv_applied'):
            st.success('Your reviewed states are now in My Career Profile. Unconfirmed skills remain not reported.')
        st.button('Clear imported document and draft', key='clear_resume', on_click=clear_resume, args=(st.session_state,))
