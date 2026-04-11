"""Shared theme, CSS, plotly defaults, and session-state helpers."""
import streamlit as st

# ── Palantir-style dark theme CSS ─────────────────────────────────────────────
THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&display=swap');

:root {
    --bg0:  #0d1117;
    --bg1:  #161b22;
    --bg2:  #21262d;
    --bg3:  #30363d;
    --acc:  #58a6ff;
    --grn:  #3fb950;
    --red:  #f85149;
    --org:  #d29922;
    --pur:  #bc8cff;
    --txt0: #e6edf3;
    --txt1: #8b949e;
    --txt2: #484f58;
}

/* ── Layout ── */
.stApp { background: var(--bg0) !important; color: var(--txt0) !important; }
section[data-testid="stSidebar"] {
    background: var(--bg1) !important;
    border-right: 1px solid var(--bg3) !important;
}
section[data-testid="stSidebar"] * { color: var(--txt0) !important; }
div[data-testid="stAppViewContainer"] { background: var(--bg0) !important; }

/* ── Cards ── */
.pal-card {
    background: var(--bg1);
    border: 1px solid var(--bg3);
    border-radius: 8px;
    padding: 16px 20px;
    margin-bottom: 12px;
}
.pal-card-accent  { border-left: 3px solid var(--acc); }
.pal-card-green   { border-left: 3px solid var(--grn); }
.pal-card-red     { border-left: 3px solid var(--red); }
.pal-card-orange  { border-left: 3px solid var(--org); }

/* ── Metric tiles ── */
.pal-metric {
    background: var(--bg1);
    border: 1px solid var(--bg3);
    border-radius: 8px;
    padding: 14px 18px;
    text-align: center;
    position: relative;
}
.pal-metric .val  { font-size: 2rem; font-weight: 700; color: var(--acc); line-height: 1.1; }
.pal-metric .lbl  { font-size: 0.65rem; color: var(--txt1); text-transform: uppercase; letter-spacing: .08em; margin-top: 4px; }
.pal-metric .sub  { font-size: 0.7rem; color: var(--txt1); margin-top: 2px; }

/* ── Badges ── */
.badge {
    display: inline-block; padding: 2px 8px; border-radius: 12px;
    font-size: 0.65rem; font-weight: 700; text-transform: uppercase; letter-spacing: .06em;
}
.badge-ip   { background:#1f3a5f; color:#58a6ff; }
.badge-loc  { background:#1f3a2e; color:#3fb950; }
.badge-org  { background:#3a1f5f; color:#bc8cff; }
.badge-zone { background:#3a2a1f; color:#d29922; }
.badge-news { background:#2a2a2a; color:#8b949e; }
.badge-reddit { background:#3a1f1f; color:#ff6314; }
.badge-wiki { background:#1f2f3a; color:#79c0ff; }
.badge-threat { background:#3a1f1f; color:#f85149; }
.badge-safe { background:#1f3a2e; color:#3fb950; }

/* ── Section headers ── */
.section-hdr {
    font-size: .65rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: .12em; color: var(--txt1);
    border-bottom: 1px solid var(--bg3); padding-bottom: 4px; margin: 16px 0 8px;
}

/* ── Entity rows ── */
.entity-row {
    display: flex; align-items: center; gap: 10px;
    padding: 7px 12px; border-bottom: 1px solid var(--bg2);
    font-size: .82rem; color: var(--txt0);
}
.entity-row:hover { background: var(--bg2); }

/* ── Status dots ── */
.dot { display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:6px; }
.dot-live  { background:var(--grn); box-shadow:0 0 6px var(--grn); }
.dot-warn  { background:var(--org); box-shadow:0 0 6px var(--org); }
.dot-dead  { background:var(--txt2); }
.dot-alert { background:var(--red); box-shadow:0 0 6px var(--red); }

/* ── Risk bar ── */
.risk-bar-bg { background:var(--bg3); border-radius:4px; height:8px; width:100%; }
.risk-bar    { border-radius:4px; height:8px; }

/* ── Timeline event ── */
.tl-event {
    display:flex; gap:12px; padding:8px 0;
    border-bottom:1px solid var(--bg2); font-size:.82rem;
}
.tl-time  { color:var(--txt1); min-width:100px; font-family:monospace; }
.tl-body  { color:var(--txt0); flex:1; }
.tl-badge { align-self:flex-start; }

/* ── Override Streamlit widget colours ── */
div[data-testid="stMetricValue"]  { color:var(--acc) !important; }
.stButton > button {
    background:var(--acc) !important; color:#0d1117 !important;
    border:none !important; font-weight:700 !important; border-radius:6px !important;
    letter-spacing:.04em;
}
.stButton > button:hover { background:#79c0ff !important; }
div[data-testid="stTabs"] button { color:var(--txt1) !important; }
div[data-testid="stTabs"] button[aria-selected="true"] { color:var(--acc) !important; border-bottom-color:var(--acc) !important; }
</style>
"""

# ── Plotly base layout ─────────────────────────────────────────────────────────
PLOTLY_BASE = dict(
    paper_bgcolor="#0d1117",
    plot_bgcolor="#0d1117",
    font=dict(color="#e6edf3", family="JetBrains Mono, monospace", size=11),
    xaxis=dict(gridcolor="#21262d", zerolinecolor="#30363d", linecolor="#30363d"),
    yaxis=dict(gridcolor="#21262d", zerolinecolor="#30363d", linecolor="#30363d"),
    legend=dict(bgcolor="#161b22", bordercolor="#30363d", borderwidth=1, font=dict(size=10)),
    margin=dict(l=48, r=16, t=48, b=40),
    hoverlabel=dict(bgcolor="#161b22", bordercolor="#30363d", font=dict(color="#e6edf3")),
)

MAPBOX = "carto-darkmatter"


def inject_theme():
    st.markdown(THEME_CSS, unsafe_allow_html=True)


def themed(fig, title: str = "", height: int = None) -> object:
    kw = dict(**PLOTLY_BASE)
    if title:
        kw["title"] = dict(text=title, font=dict(size=13, color="#e6edf3"), x=0.01)
    if height:
        kw["height"] = height
    fig.update_layout(**kw)
    return fig


# ── Session-state helpers ──────────────────────────────────────────────────────
KEY = "palantir_investigation"


def set_data(d: dict):
    st.session_state[KEY] = d


def get_data() -> dict | None:
    return st.session_state.get(KEY)


def require_data() -> dict:
    d = get_data()
    if d is None:
        inject_theme()
        st.markdown(
            '<div class="pal-card pal-card-red">'
            '<b>No active investigation.</b> Return to Home and analyse a target IP first.'
            "</div>",
            unsafe_allow_html=True,
        )
        st.stop()
    return d


def metric_html(value, label, sub="", color="#58a6ff") -> str:
    return (
        f'<div class="pal-metric">'
        f'<div class="val" style="color:{color}">{value}</div>'
        f'<div class="lbl">{label}</div>'
        f'<div class="sub">{sub}</div>'
        f"</div>"
    )


def badge(text: str, kind: str = "ip") -> str:
    return f'<span class="badge badge-{kind}">{text}</span>'


def risk_color(score: int) -> str:
    if score >= 70:
        return "#f85149"
    if score >= 40:
        return "#d29922"
    return "#3fb950"
