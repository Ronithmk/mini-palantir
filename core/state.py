"""Shared theme, CSS, plotly defaults, and session-state helpers."""
import streamlit as st

# ── Palantir-style dark theme CSS ─────────────────────────────────────────────
THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    --bg0:  #0b0f14;
    --bg1:  #111827;
    --bg2:  #1c2333;
    --bg3:  #2d3748;
    --acc:  #4d9de0;
    --grn:  #2ea043;
    --red:  #e05050;
    --org:  #c09000;
    --txt0: #d4dce8;
    --txt1: #6b7685;
    --txt2: #2d3748;
    --r4:   4px;
}

/* ── Layout ── */
.stApp { background: var(--bg0) !important; color: var(--txt0) !important;
         font-family: 'Inter', sans-serif !important; }
section[data-testid="stSidebar"] {
    background: var(--bg1) !important;
    border-right: 1px solid var(--bg2) !important;
}
section[data-testid="stSidebar"] * { color: var(--txt0) !important; }
div[data-testid="stAppViewContainer"] { background: var(--bg0) !important; }

/* ── Cards ── */
.pal-card {
    background: var(--bg1);
    border: 1px solid var(--bg2);
    border-radius: var(--r4);
    padding: 14px 18px;
    margin-bottom: 10px;
}
.pal-card-accent  { border-top: 2px solid var(--acc); }
.pal-card-green   { border-top: 2px solid var(--grn); }
.pal-card-red     { border-top: 2px solid var(--red); }
.pal-card-orange  { border-top: 2px solid var(--org); }

/* ── Metric tiles ── */
.pal-metric {
    background: var(--bg1);
    border: 1px solid var(--bg2);
    border-radius: var(--r4);
    padding: 12px 14px;
    text-align: center;
}
.pal-metric .val  { font-size: 1.7rem; font-weight: 600; color: var(--acc); line-height: 1.2; }
.pal-metric .lbl  { font-size: 0.68rem; color: var(--txt1); margin-top: 3px; }
.pal-metric .sub  { font-size: 0.65rem; color: var(--txt1); }

/* ── Badges ── */
.badge {
    display: inline-block; padding: 1px 7px; border-radius: var(--r4);
    font-size: 0.65rem; font-weight: 500; letter-spacing: .02em;
}
.badge-ip     { background: rgba(77,157,224,0.12); color: var(--acc); }
.badge-loc    { background: rgba(46,160,67,0.12);  color: #4db868; }
.badge-org    { background: rgba(110,118,129,0.10); color: var(--txt1); }
.badge-zone   { background: rgba(192,144,0,0.12);  color: #d4a837; }
.badge-news   { background: rgba(110,118,129,0.08); color: var(--txt1); }
.badge-reddit { background: rgba(200,80,30,0.10);  color: #e07040; }
.badge-wiki   { background: rgba(77,157,224,0.08); color: #7ab0e0; }
.badge-threat { background: rgba(224,80,80,0.12);  color: var(--red); }
.badge-safe   { background: rgba(46,160,67,0.12);  color: #4db868; }

/* ── Section headers ── */
.section-hdr {
    font-size: .7rem; color: var(--txt1); font-weight: 500;
    padding-bottom: 5px; border-bottom: 1px solid var(--bg2);
    margin: 14px 0 8px;
}

/* ── Entity rows ── */
.entity-row {
    display: flex; align-items: center; gap: 8px;
    padding: 6px 0; border-bottom: 1px solid var(--bg2);
    font-size: .82rem; color: var(--txt0);
}

/* ── Status dots ── */
.dot { display:inline-block; width:6px; height:6px; border-radius:50%; margin-right:5px; flex-shrink:0; }
.dot-live  { background: var(--grn); }
.dot-warn  { background: var(--org); }
.dot-dead  { background: var(--txt1); }
.dot-alert { background: var(--red); }

/* ── Risk bar ── */
.risk-bar-bg { background: var(--bg3); border-radius: 2px; height: 4px; width: 100%; }
.risk-bar    { border-radius: 2px; height: 4px; }

/* ── Timeline event ── */
.tl-event {
    display:flex; gap:12px; padding:8px 0;
    border-bottom:1px solid var(--bg2); font-size:.82rem;
}
.tl-time  { color: var(--txt1); min-width:100px; font-family: 'JetBrains Mono', monospace; }
.tl-body  { color: var(--txt0); flex:1; }
.tl-badge { align-self:flex-start; }

/* ── Streamlit overrides ── */
div[data-testid="stMetricValue"]  { color: var(--acc) !important; }

/* Ghost buttons by default */
.stButton > button {
    background: transparent !important;
    border: 1px solid var(--bg3) !important;
    color: var(--txt0) !important;
    border-radius: var(--r4) !important;
    font-size: .8rem !important;
    font-weight: 400 !important;
    letter-spacing: 0 !important;
    padding: 4px 12px !important;
    transition: border-color .15s, color .15s !important;
}
.stButton > button:hover {
    border-color: var(--acc) !important;
    color: var(--acc) !important;
    background: rgba(77,157,224,0.06) !important;
}

/* Primary action buttons */
div[data-testid="stMainBlockContainer"] .stButton > button[kind="primaryFormSubmit"],
div[data-testid="stMainBlockContainer"] .stButton > button[kind="primary"] {
    background: var(--acc) !important;
    border-color: var(--acc) !important;
    color: #0b0f14 !important;
    font-weight: 600 !important;
}
div[data-testid="stMainBlockContainer"] .stButton > button[kind="primary"]:hover {
    background: #6ab3e8 !important;
    border-color: #6ab3e8 !important;
    color: #0b0f14 !important;
}

div[data-testid="stTabs"] button { color: var(--txt1) !important; font-size: .82rem !important; }
div[data-testid="stTabs"] button[aria-selected="true"] {
    color: var(--txt0) !important;
    border-bottom-color: var(--acc) !important;
}

/* Input fields */
div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea {
    background: var(--bg2) !important;
    border-color: var(--bg3) !important;
    color: var(--txt0) !important;
    border-radius: var(--r4) !important;
}
div[data-testid="stSelectbox"] > div {
    background: var(--bg2) !important;
    border-color: var(--bg3) !important;
}

/* Dataframes */
div[data-testid="stDataFrame"] { border: 1px solid var(--bg2) !important; border-radius: var(--r4) !important; }

/* Expander */
div[data-testid="stExpander"] { border: 1px solid var(--bg2) !important; border-radius: var(--r4) !important; }
</style>
"""

# ── Plotly base layout ─────────────────────────────────────────────────────────
PLOTLY_BASE = dict(
    paper_bgcolor="#0b0f14",
    plot_bgcolor="#0b0f14",
    font=dict(color="#d4dce8", family="Inter, sans-serif", size=11),
    xaxis=dict(gridcolor="#1c2333", zerolinecolor="#2d3748", linecolor="#2d3748"),
    yaxis=dict(gridcolor="#1c2333", zerolinecolor="#2d3748", linecolor="#2d3748"),
    legend=dict(bgcolor="#111827", bordercolor="#2d3748", borderwidth=1, font=dict(size=10)),
    margin=dict(l=48, r=16, t=44, b=40),
    hoverlabel=dict(bgcolor="#111827", bordercolor="#2d3748", font=dict(color="#d4dce8")),
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


# ── Zone type colours (Trackr-style) ──────────────────────────────────────────
ZONE_TYPE_COLOR = {
    "PRIMARY":   "#00e5ff",
    "SECONDARY": "#ffd60a",
    "TRANSIT":   "#bf5af2",
    "NOISE":     "#484f58",
}
ZONE_TYPE_FOLIUM = {
    "PRIMARY":   "blue",
    "SECONDARY": "orange",
    "TRANSIT":   "purple",
    "NOISE":     "gray",
}


def zone_type_badge(zone_type: str) -> str:
    colors = {
        "PRIMARY":   ("rgba(0,229,255,0.15)",   "#00e5ff"),
        "SECONDARY": ("rgba(255,214,10,0.15)",  "#ffd60a"),
        "TRANSIT":   ("rgba(191,90,242,0.15)",  "#bf5af2"),
        "NOISE":     ("rgba(72,79,88,0.15)",    "#484f58"),
    }
    bg, fg = colors.get(zone_type, ("rgba(72,79,88,0.15)", "#484f58"))
    return (
        f'<span style="background:{bg};color:{fg};padding:2px 8px;border-radius:10px;'
        f'font-size:.6rem;font-weight:700;letter-spacing:.1em;border:1px solid {fg}40">'
        f'{zone_type}</span>'
    )


def sparkline_svg(values: list, width: int = 96, height: int = 24,
                  color: str = "#00e5ff") -> str:
    """Render a 24-bin hourly sparkline as inline SVG (Trackr-style)."""
    if not values or max(values) == 0:
        return f'<svg width="{width}" height="{height}"></svg>'
    max_v = max(values)
    n     = len(values)
    bw    = width / n
    bars  = ""
    for i, v in enumerate(values):
        h   = max(1, int(v / max_v * height))
        y   = height - h
        x   = i * bw
        op  = 0.25 + 0.75 * (v / max_v)
        bars += (
            f'<rect x="{x:.1f}" y="{y}" width="{max(1, bw - 0.8):.1f}" '
            f'height="{h}" fill="{color}" opacity="{op:.2f}" rx="1"/>'
        )
    return f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">{bars}</svg>'


# ── Live clock JS (IST) ───────────────────────────────────────────────────────
LIVE_CLOCK_HTML = """
<div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
  <span style="width:8px;height:8px;border-radius:50%;background:#00ff88;
        box-shadow:0 0 8px #00ff88;display:inline-block;
        animation:blink 1.4s ease-in-out infinite;"></span>
  <span style="font-size:.65rem;color:#00ff88;letter-spacing:.1em;font-weight:700">LIVE</span>
  <span id="pal-clock" style="font-size:.65rem;color:#00e5ff;letter-spacing:.08em;
        font-family:monospace;margin-left:4px;"></span>
</div>
<style>
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:.3} }
</style>
<script>
(function(){
  function tick(){
    var now = new Date();
    var ist = new Date(now.getTime() + (5.5*3600000));
    var s = ist.toISOString().replace('T',' ').substring(0,19)+' IST';
    var el = document.getElementById('pal-clock');
    if(el) el.textContent = s;
  }
  tick(); setInterval(tick,1000);
})();
</script>
"""


# ── Loading overlay HTML ───────────────────────────────────────────────────────
LOADING_OVERLAY_HTML = """
<div id="pal-loading" style="
  position:fixed;top:0;left:0;width:100%;height:100%;
  background:rgba(3,13,18,0.93);z-index:9999;
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  font-family:monospace;">
  <div style="width:44px;height:44px;border:2px solid #0d2a35;
       border-top:2px solid #00e5ff;border-radius:50%;
       animation:spin 0.9s linear infinite;"></div>
  <div id="pal-load-msg" style="color:#00e5ff;font-size:.75rem;letter-spacing:.12em;
       margin-top:20px;"></div>
</div>
<style>@keyframes spin{to{transform:rotate(360deg)}}</style>
<script>
(function(){
  var msgs = [
    "PARSING BEHAVIORAL LOGS",
    "RESOLVING GEOLOCATION",
    "CLUSTERING SESSION DATA",
    "BUILDING ENTITY GRAPH",
    "RUNNING PREDICTIVE MODELS",
    "COMPILING INTELLIGENCE FEED",
    "FINALISING REPORT"
  ];
  var i=0;
  var el=document.getElementById('pal-load-msg');
  if(el){ el.textContent=msgs[0]; setInterval(function(){ i=(i+1)%msgs.length; el.textContent=msgs[i]; },400); }
  setTimeout(function(){ var ov=document.getElementById('pal-loading'); if(ov) ov.style.display='none'; },2000);
})();
</script>
"""
