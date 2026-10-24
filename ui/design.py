"""Static, accessible product styling. Never interpolate user/model content into HTML."""

def apply_design(st):
    st.markdown('''<style>
    :root {--fp-ink:#152B46;--fp-accent:#087E8B;--fp-muted:#52647A;}
    .stApp {background:linear-gradient(160deg,#f3f8fb 0%,#fff 55%);color:var(--fp-ink);}
    .block-container {max-width:1280px;padding-top:2.2rem;padding-bottom:3rem;}
    h1,h2,h3 {letter-spacing:-.025em;color:var(--fp-ink);}
    h1 {font-size:2.6rem!important;} p {line-height:1.6;}
    [data-testid="stSidebar"] {background:#eaf2f7;}
    [data-testid="stVerticalBlockBorderWrapper"] {border-radius:16px;}
    [data-baseweb="tab-list"] {gap:.3rem;overflow-x:auto;padding:.5rem 0;}
    button[data-baseweb="tab"] {border-radius:9px;padding:.7rem .8rem;white-space:nowrap;}
    .stButton>button {border-radius:9px;min-height:2.7rem;font-weight:600;}
    .stButton>button[kind="primary"] {background:var(--fp-accent);border-color:var(--fp-accent);}
    [data-testid="stMetric"] {background:white;border:1px solid #d9e5ed;border-radius:14px;padding:1rem;}
    @media(max-width:700px){.block-container{padding:1rem;}h1{font-size:2rem!important;}button[data-baseweb="tab"]{padding:.6rem;}}
    </style>''', unsafe_allow_html=True)


def dashboard(st, run):
    st.subheader('A clearer next step starts with your skills')
    st.write('Build an honest picture of what you know, explore fictional career requirements, and choose a practical learning action.')
    for col, title, body in zip(st.columns(3), ['Build your profile', 'Understand your matches', 'Plan your practice'],
            ['Start with a sample or confirm your own skill states. Local resume import can suggest a draft.',
             'See which strengths, confirmed gaps and unanswered questions support each result.',
             'Set your own time and learning preferences. Use an offline plan or opt-in AI help.']):
        with col.container(border=True):
            st.markdown('**' + title + '**')
            st.write(body)
    st.info('Use the task tabs above to begin. Matching uses fictional occupation data; it does not predict employment.')
    count = len(run.ranked_results)
    st.caption(f'{count} complete fictional ' + ('match' if count == 1 else 'matches') + f' · {len(run.unranked_results)} paths need more skill information')
