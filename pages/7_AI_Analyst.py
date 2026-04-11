"""
AI Analyst — ARIA (Advanced Reasoning Intelligence Analyst)
Powered by Claude. Proactively briefs analysts and answers investigative questions.
This is beyond what Palantir does — AI that reasons, not just visualises.
"""
import streamlit as st
import os
from core.state import inject_theme, require_data, risk_color
from core.ai_analyst import AIAnalyst, build_context, SYSTEM_PROMPT

st.set_page_config(page_title="AI Analyst · ARGUS", page_icon="🤖", layout="wide")
inject_theme()
d = require_data()

st.markdown(
    '<div style="font-size:1.1rem;font-weight:600;color:#F0F0F0;margin-bottom:3px;">ARIA — AI Analyst</div>'
    '<div style="font-size:.75rem;color:#8C8C8C;margin-bottom:18px;">'
    'Advanced Reasoning Intelligence Analyst · Powered by Claude</div>',
    unsafe_allow_html=True,
)

# ── API Key setup ──────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="section-hdr">ARIA Configuration</div>', unsafe_allow_html=True)
    env_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if env_key:
        api_key = env_key
        st.markdown(
            '<div class="entity-row"><span class="dot dot-live"></span>'
            '<span style="font-size:.8rem;color:#23D18B">API key loaded from environment</span></div>',
            unsafe_allow_html=True,
        )
    else:
        api_key = st.text_input(
            "Anthropic API Key",
            type="password",
            placeholder="sk-ant-...",
            help="Get a free key at console.anthropic.com",
        )
    if api_key:
        st.session_state["aria_api_key"] = api_key

    st.markdown("---")
    st.markdown('<div class="section-hdr">Quick Questions</div>', unsafe_allow_html=True)
    quick_qs = [
        "What is the threat level of this target?",
        "Where is this person most likely right now?",
        "What is unusual about this behavior?",
        "What should I investigate next?",
    ]
    for q in quick_qs:
        if st.button(q, key=f"qbtn_{q[:20]}", use_container_width=True):
            st.session_state["aria_inject"] = q

api_key = st.session_state.get("aria_api_key", api_key if "api_key" in dir() else "")

if not api_key:
    st.markdown(
        '<div class="pal-card pal-card-orange">'
        '<b>ARIA requires an Anthropic API key.</b><br>'
        'Enter your key in the sidebar to activate the AI analyst. '
        'Get a free key at <a href="https://console.anthropic.com" target="_blank" style="color:#0B88F8">console.anthropic.com</a>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.stop()

analyst = AIAnalyst(api_key)
context = build_context(d)

# ── Auto-briefing ──────────────────────────────────────────────────────────────
tab_brief, tab_chat, tab_hypothesis = st.tabs([
    "Intelligence Briefing", "Analyst Chat", "Hypothesis Board"
])

with tab_brief:
    col_brief, col_meta = st.columns([3, 1])

    with col_meta:
        rc = risk_color(d["risk_score"])
        st.markdown(
            f'<div class="pal-card pal-card-accent">'
            f'<div class="section-hdr">Investigation</div>'
            f'<div style="font-size:.8rem;color:#F0F0F0"><b>{d["case_id"]}</b></div>'
            f'<div style="font-size:.75rem;color:#8C8C8C">{d["target_ip"]}</div>'
            f'<div style="margin-top:10px;font-size:.75rem;">Risk: <b style="color:{rc}">{d["risk_score"]}/100</b></div>'
            f'<div style="font-size:.7rem;color:#8C8C8C;margin-top:4px;">'
            f'{d["analyzed_at"].strftime("%Y-%m-%d %H:%M")}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if st.button("Regenerate Briefing", use_container_width=True):
            if "aria_briefing" in st.session_state:
                del st.session_state["aria_briefing"]

    with col_brief:
        if "aria_briefing" not in st.session_state:
            with st.spinner("ARIA is analysing the investigation…"):
                try:
                    briefing = analyst.generate_briefing(context)
                    st.session_state["aria_briefing"] = briefing
                except Exception as e:
                    st.error(f"ARIA error: {e}")
                    st.stop()

        st.markdown(
            '<div class="pal-card" style="padding:20px 24px;">',
            unsafe_allow_html=True,
        )
        st.markdown(st.session_state.get("aria_briefing", ""))
        st.markdown('</div>', unsafe_allow_html=True)

        st.download_button(
            "Download Briefing (.md)",
            data=st.session_state.get("aria_briefing", "").encode(),
            file_name=f"{d['case_id']}_ARIA_briefing.md",
            mime="text/markdown",
        )

# ── Chat ───────────────────────────────────────────────────────────────────────
with tab_chat:
    if "aria_history" not in st.session_state:
        st.session_state["aria_history"] = []

    # Inject from quick questions
    inject = st.session_state.pop("aria_inject", None)

    # Display history
    for msg in st.session_state["aria_history"]:
        with st.chat_message(msg["role"], avatar="🤖" if msg["role"] == "assistant" else "🔵"):
            st.markdown(msg["content"])

    # Input
    user_input = st.chat_input("Ask ARIA anything about the investigation…") or inject

    if user_input:
        st.session_state["aria_history"].append({"role": "user", "content": user_input})
        with st.chat_message("user", avatar="🔵"):
            st.markdown(user_input)

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("ARIA is thinking…"):
                try:
                    reply = analyst.chat(context, st.session_state["aria_history"][:-1], user_input)
                except Exception as e:
                    reply = f"Error: {e}"
            st.markdown(reply)
            st.session_state["aria_history"].append({"role": "assistant", "content": reply})

    if st.session_state["aria_history"]:
        if st.button("Clear Conversation", key="clear_chat"):
            st.session_state["aria_history"] = []
            st.rerun()

# ── Hypothesis Board ───────────────────────────────────────────────────────────
with tab_hypothesis:
    st.markdown(
        '<div style="font-size:.8rem;color:#8C8C8C;margin-bottom:16px;">'
        'ARIA generates <b>competing hypotheses</b> for a specific observation — '
        'forcing consideration of alternative explanations. Palantir shows data; ARIA reasons about it.'
        '</div>',
        unsafe_allow_html=True,
    )

    col_obs, col_gen = st.columns([3, 1])
    with col_obs:
        adf = d["anomaly_df"]
        night_pct  = adf["hour"].between(1, 4).mean() * 100
        remote_pct = (adf["zone_label"] == "Travel / Remote").mean() * 100
        anom_pct   = adf["anomaly"].mean() * 100

        preset_obs = [
            f"The target has {night_pct:.0f}% night-time sessions (01:00-04:00)",
            f"The target shows {remote_pct:.0f}% remote zone activity",
            f"The target has {anom_pct:.0f}% anomalous sessions",
            f"The ISP is registered as: {d['base_geo'].get('isp','unknown')}",
            "Custom observation…",
        ]
        selected = st.selectbox("Choose an observation to analyse", preset_obs, key="hyp_select")
        if selected == "Custom observation…":
            observation = st.text_area("Describe the observation", placeholder="e.g. Target activity drops to zero every Friday evening…", key="hyp_custom")
        else:
            observation = selected

    with col_gen:
        st.markdown("<br>", unsafe_allow_html=True)
        gen_hyp = st.button("Generate Hypotheses", type="primary", use_container_width=True)

    if gen_hyp and observation:
        hyp_key = f"hyp_{hash(observation)}"
        if hyp_key not in st.session_state:
            with st.spinner("ARIA is generating competing hypotheses…"):
                try:
                    result = analyst.generate_hypotheses(context, observation)
                    st.session_state[hyp_key] = result
                except Exception as e:
                    st.error(f"Error: {e}")
                    result = None

        if hyp_key in st.session_state:
            st.markdown("---")
            st.markdown(
                f'<div class="pal-card pal-card-orange">'
                f'<div class="section-hdr">OBSERVATION</div>'
                f'<div style="font-size:.9rem;color:#F0F0F0">{observation}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<div class="pal-card" style="padding:20px 24px;">',
                unsafe_allow_html=True,
            )
            st.markdown(st.session_state[hyp_key])
            st.markdown('</div>', unsafe_allow_html=True)
