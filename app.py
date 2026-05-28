import streamlit as st
import time
from pipeline import run_research_pipeline

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ResearchOS · Multi-Agent",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Global CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Mono:wght@300;400;500&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,300&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, [data-testid="stAppViewContainer"] {
    background: #0a0a0f !important;
    color: #e8e4dc !important;
    font-family: 'DM Sans', sans-serif !important;
}
[data-testid="stAppViewContainer"] > .main { background: #0a0a0f !important; }
[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stToolbar"] { display: none !important; }
.stDeployButton { display: none !important; }
#MainMenu { display: none !important; }
footer { display: none !important; }
[data-testid="stSidebar"] { display: none; }

.block-container {
    max-width: 900px !important;
    padding: 0 2rem !important;
    margin: 0 auto !important;
}

.hero { padding: 5rem 0 3rem; text-align: center; }
.hero-badge {
    display: inline-block;
    font-family: 'DM Mono', monospace;
    font-size: 0.65rem;
    font-weight: 500;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #c8a96e;
    border: 1px solid rgba(200, 169, 110, 0.3);
    padding: 0.3rem 1rem;
    border-radius: 2px;
    margin-bottom: 1.5rem;
}
.hero-title {
    font-family: 'DM Serif Display', serif;
    font-size: clamp(2.8rem, 6vw, 4.5rem);
    font-weight: 400;
    line-height: 1.1;
    color: #f0ebe0;
    letter-spacing: -0.02em;
    margin-bottom: 1rem;
}
.hero-title em { font-style: italic; color: #c8a96e; }
.hero-sub {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.95rem;
    font-weight: 300;
    color: #888070;
    letter-spacing: 0.02em;
    line-height: 1.7;
}
.divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(200,169,110,0.25), transparent);
    margin: 2.5rem 0;
}
.input-label {
    font-family: 'DM Mono', monospace;
    font-size: 0.65rem;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #666050;
    margin-bottom: 0.75rem;
}

[data-testid="stTextInput"] > div > div > input {
    background: #111118 !important;
    border: 1px solid #2a2830 !important;
    border-radius: 4px !important;
    color: #e8e4dc !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 1rem !important;
    font-weight: 300 !important;
    padding: 0.9rem 1.2rem !important;
    transition: border-color 0.2s ease !important;
    caret-color: #c8a96e !important;
}
[data-testid="stTextInput"] > div > div > input:focus {
    border-color: rgba(200, 169, 110, 0.5) !important;
    box-shadow: 0 0 0 3px rgba(200, 169, 110, 0.06) !important;
    outline: none !important;
}
[data-testid="stTextInput"] > div > div > input::placeholder { color: #3a3830 !important; }
[data-testid="stTextInput"] label { display: none !important; }

[data-testid="stButton"] > button {
    background: #c8a96e !important;
    color: #0a0a0f !important;
    border: none !important;
    border-radius: 4px !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.7rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.15em !important;
    text-transform: uppercase !important;
    padding: 0.75rem 2.5rem !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
    width: 100% !important;
}
[data-testid="stButton"] > button:hover {
    background: #d4b87a !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 8px 24px rgba(200, 169, 110, 0.2) !important;
}
[data-testid="stButton"] > button:active { transform: translateY(0) !important; }

.pipeline-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1px;
    background: #1a1820;
    border: 1px solid #1a1820;
    border-radius: 6px;
    overflow: hidden;
    margin: 2.5rem 0;
}
.pipeline-step {
    background: #0e0e14;
    padding: 1.25rem 1rem;
    text-align: center;
    transition: background 0.3s ease;
}
.pipeline-step.active { background: #12121a; }
.pipeline-step.done   { background: #0f1210; }
.step-index {
    font-family: 'DM Mono', monospace;
    font-size: 0.6rem;
    color: #333;
    letter-spacing: 0.1em;
    margin-bottom: 0.5rem;
}
.step-icon  { font-size: 1.1rem; margin-bottom: 0.4rem; display: block; }
.step-name  { font-size: 0.7rem; font-weight: 400; color: #555; letter-spacing: 0.05em; transition: color 0.3s ease; }
.pipeline-step.active .step-name  { color: #c8a96e; }
.pipeline-step.active .step-index { color: #c8a96e; }
.pipeline-step.done .step-name    { color: #6a9b70; }
.pipeline-step.done .step-index   { color: #6a9b70; }

.result-section { margin-bottom: 2rem; }
.result-header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 1rem;
    padding-bottom: 0.75rem;
    border-bottom: 1px solid #1a1820;
}
.result-tag {
    font-family: 'DM Mono', monospace;
    font-size: 0.6rem;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: #0a0a0f;
    padding: 0.2rem 0.6rem;
    border-radius: 2px;
}
.result-tag.green { background: #5a8f62; }
.result-tag.blue  { background: #4a6f9f; }
.result-tag.amber { background: #c8a96e; }
.result-tag.rose  { background: #9f5a6f; }
.result-title {
    font-family: 'DM Serif Display', serif;
    font-size: 1.1rem;
    font-weight: 400;
    color: #d8d4cc;
}
.result-body {
    background: #0e0e14;
    border: 1px solid #1a1820;
    border-radius: 6px;
    padding: 1.5rem;
    font-family: 'DM Sans', sans-serif;
    font-size: 0.875rem;
    font-weight: 300;
    line-height: 1.8;
    color: #a09880;
    white-space: pre-wrap;
    word-break: break-word;
}
.result-body.report   { font-size: 0.9rem; color: #c8c4bc; line-height: 1.9; }
.result-body.feedback { color: #9aaa90; }

.status-bar {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem 1rem;
    background: #0e0e14;
    border: 1px solid #1a1820;
    border-radius: 4px;
    margin-bottom: 2rem;
}
.status-dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: #c8a96e;
    animation: pulse 1.5s infinite;
}
.status-dot.done { background: #5a8f62; animation: none; }
@keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50%       { opacity: 0.4; transform: scale(0.8); }
}
.status-text {
    font-family: 'DM Mono', monospace;
    font-size: 0.65rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #666050;
}

.info-row {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1px;
    background: #1a1820;
    border: 1px solid #1a1820;
    border-radius: 6px;
    overflow: hidden;
    margin-bottom: 2.5rem;
}
.info-card { background: #0e0e14; padding: 1rem 1.25rem; }
.info-card-label {
    font-family: 'DM Mono', monospace;
    font-size: 0.55rem;
    letter-spacing: 0.15em;
    color: #444038;
    text-transform: uppercase;
    margin-bottom: 0.35rem;
}
.info-card-value { font-size: 0.8rem; color: #888070; font-weight: 300; }

.footer {
    text-align: center;
    padding: 3rem 0 2rem;
    font-family: 'DM Mono', monospace;
    font-size: 0.6rem;
    letter-spacing: 0.12em;
    color: #2a2820;
    text-transform: uppercase;
}

[data-testid="column"] { padding: 0 0.3rem !important; }
</style>
""", unsafe_allow_html=True)


# ── Session state ──────────────────────────────────────────────────────────────
for key, default in [
    ("results", None),
    ("should_run", False),   # ← the actual trigger flag
    ("queued_topic", ""),
    ("elapsed", 0),
    ("step_active", -1),
    ("step_done", -1),
    ("status_label", ""),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ── Helper ─────────────────────────────────────────────────────────────────────
def render_pipeline_steps(active: int = -1, done_up_to: int = -1) -> str:
    steps = [("◎", "Search"), ("◈", "Reader"), ("✦", "Writer"), ("◇", "Critic")]
    html = '<div class="pipeline-grid">'
    for i, (icon, name) in enumerate(steps):
        cls = "pipeline-step"
        if i == active:
            cls += " active"
        elif i <= done_up_to:
            cls += " done"
        html += f"""
        <div class="{cls}">
            <div class="step-index">0{i+1}</div>
            <span class="step-icon">{icon}</span>
            <div class="step-name">{name}</div>
        </div>"""
    html += "</div>"
    return html


# ── Hero ───────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <div class="hero-badge">◈ Multi-Agent System</div>
    <h1 class="hero-title">Research<em>OS</em></h1>
    <p class="hero-sub">Four-agent pipeline · Search → Read → Write → Critique</p>
</div>
<div class="divider"></div>
""", unsafe_allow_html=True)


# ── Input row ─────────────────────────────────────────────────────────────────
st.markdown('<div class="input-label">Research Topic</div>', unsafe_allow_html=True)

col_input, col_btn = st.columns([5, 1.2])
with col_input:
    topic = st.text_input(
        label="topic",
        placeholder="e.g. Quantum error correction in 2025 …",
        label_visibility="collapsed",
        key="topic_input",
        disabled=st.session_state.should_run,
    )
with col_btn:
    run_clicked = st.button(
        "▶ Run",
        use_container_width=True,
        disabled=st.session_state.should_run,
    )

# When button is clicked, just set the flag and rerun — don't execute pipeline here
if run_clicked and topic.strip() and not st.session_state.should_run:
    st.session_state.should_run   = True
    st.session_state.queued_topic = topic.strip()
    st.session_state.results      = None
    st.rerun()

if run_clicked and not topic.strip():
    st.warning("Please enter a research topic.")


# ── Idle state (no run in progress, no results yet) ────────────────────────────
if not st.session_state.should_run and st.session_state.results is None:
    st.markdown(render_pipeline_steps(), unsafe_allow_html=True)
    st.markdown("""
    <div class="info-row">
        <div class="info-card">
            <div class="info-card-label">Agent 01 — Search</div>
            <div class="info-card-value">Web retrieval via tool-use</div>
        </div>
        <div class="info-card">
            <div class="info-card-label">Agent 02 — Reader</div>
            <div class="info-card-value">Extracts key findings</div>
        </div>
        <div class="info-card">
            <div class="info-card-label">Chain 03 — Writer</div>
            <div class="info-card-value">Synthesises a full report</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ── Pipeline execution (only when flag is set) ─────────────────────────────────
if st.session_state.should_run:
    queued_topic = st.session_state.queued_topic

    progress_ph = st.empty()
    status_ph   = st.empty()

    steps_labels = [
        "Search Agent scanning the web…",
        "Reader Agent extracting key insights…",
        "Writer Chain drafting your report…",
        "Critic Chain reviewing quality…",
    ]

    def show_step(i: int, done_up_to: int = -1, pulsing: bool = True):
        with progress_ph.container():
            st.markdown(render_pipeline_steps(active=i, done_up_to=done_up_to), unsafe_allow_html=True)
        dot_cls = "status-dot" if pulsing else "status-dot done"
        label   = steps_labels[i] if pulsing else f"Pipeline complete · {st.session_state.elapsed}s"
        with status_ph.container():
            st.markdown(f"""
            <div class="status-bar">
                <div class="{dot_cls}"></div>
                <span class="status-text">{label}</span>
            </div>
            """, unsafe_allow_html=True)

    # Show step 0 active immediately
    show_step(0)

    try:
        t_start = time.time()
        state   = run_research_pipeline(queued_topic)
        st.session_state.elapsed = round(time.time() - t_start, 1)
        st.session_state.results = state
    except Exception as e:
        st.session_state.should_run = False
        st.error(f"Pipeline error: {e}")
        st.stop()

    # Animate through remaining steps quickly
    for j in range(1, 4):
        show_step(j, done_up_to=j - 1)
        time.sleep(0.35)

    # Final done state
    with progress_ph.container():
        st.markdown(render_pipeline_steps(done_up_to=3), unsafe_allow_html=True)
    with status_ph.container():
        st.markdown(f"""
        <div class="status-bar">
            <div class="status-dot done"></div>
            <span class="status-text">Pipeline complete · {st.session_state.elapsed}s</span>
        </div>
        """, unsafe_allow_html=True)

    # Clear the trigger flag so re-renders don't re-run the pipeline
    st.session_state.should_run = False


# ── Display results ────────────────────────────────────────────────────────────
if st.session_state.results and not st.session_state.should_run:
    r = st.session_state.results

    # Keep the done pipeline visible
    st.markdown(render_pipeline_steps(done_up_to=3), unsafe_allow_html=True)
    st.markdown(f"""
    <div class="status-bar">
        <div class="status-dot done"></div>
        <span class="status-text">Pipeline complete · {st.session_state.elapsed}s</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # Search result
    if r.get("search_result"):
        st.markdown("""
        <div class="result-section">
            <div class="result-header">
                <span class="result-tag blue">01 · Search</span>
                <span class="result-title">Raw Search Results</span>
            </div>
        </div>""", unsafe_allow_html=True)
        with st.expander("View raw search data", expanded=False):
            st.markdown(f'<div class="result-body">{r["search_result"]}</div>', unsafe_allow_html=True)

    # Reader result
    if r.get("reader_result"):
        st.markdown("""
        <div class="result-section">
            <div class="result-header">
                <span class="result-tag amber">02 · Reader</span>
                <span class="result-title">Extracted Insights</span>
            </div>
        </div>""", unsafe_allow_html=True)
        with st.expander("View extracted information", expanded=False):
            st.markdown(f'<div class="result-body">{r["reader_result"]}</div>', unsafe_allow_html=True)

    # Report — always expanded
    if r.get("report"):
        st.markdown("""
        <div class="result-section">
            <div class="result-header">
                <span class="result-tag green">03 · Report</span>
                <span class="result-title">Research Summary</span>
            </div>
        </div>""", unsafe_allow_html=True)
        st.markdown(f'<div class="result-body report">{r["report"]}</div>', unsafe_allow_html=True)

    # Critic feedback
    if r.get("feedback"):
        st.markdown("""
        <div class="result-section" style="margin-top:1.5rem">
            <div class="result-header">
                <span class="result-tag rose">04 · Critic</span>
                <span class="result-title">Quality Evaluation</span>
            </div>
        </div>""", unsafe_allow_html=True)
        st.markdown(f'<div class="result-body feedback">{r["feedback"]}</div>', unsafe_allow_html=True)

    # Export
    st.markdown("<br>", unsafe_allow_html=True)
    _, col2, _ = st.columns([1, 2, 1])
    with col2:
        full_output = f"""RESEARCHOS — PIPELINE OUTPUT
Topic: {st.session_state.queued_topic}
{'='*60}

[01 · SEARCH AGENT]
{r.get('search_result', '')}

{'='*60}

[02 · READER AGENT]
{r.get('reader_result', '')}

{'='*60}

[03 · WRITER CHAIN — REPORT]
{r.get('report', '')}

{'='*60}

[04 · CRITIC CHAIN — FEEDBACK]
{r.get('feedback', '')}
"""
        st.download_button(
            label="↓ Export Full Report",
            data=full_output,
            file_name=f"research_{st.session_state.queued_topic[:30].replace(' ', '_')}.txt",
            mime="text/plain",
            use_container_width=True,
        )


# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="footer">
    ResearchOS · Multi-Agent Pipeline · Built with LangChain + Streamlit
</div>
""", unsafe_allow_html=True)