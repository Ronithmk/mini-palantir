"""Shared theme, CSS, plotly defaults, and session-state helpers."""
import streamlit as st

# ── Palantir Foundry-accurate dark theme ──────────────────────────────────────
# Palette reference:
#   bg0  #0F0F0F  — main canvas (near-black)
#   bg1  #141414  — sidebar / elevated surface
#   bg2  #1C1C1C  — card / panel surface
#   bg3  #2A2A2A  — border / divider
#   bg4  #383838  — hover / slightly lighter border
#   acc  #0B88F8  — Palantir cobalt blue
#   grn  #23D18B  — success / safe
#   red  #F14C4C  — alert / danger
#   org  #F5A623  — warning
#   txt0 #FFFFFF  — primary text (white)
#   txt1 #8C8C8C  — secondary text
#   txt2 #444444  — tertiary / very dim
THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    --bg0:  #0F0F0F;
    --bg1:  #141414;
    --bg2:  #1C1C1C;
    --bg3:  #2A2A2A;
    --bg4:  #383838;
    --acc:  #0B88F8;
    --acc2: #3DA5FF;
    --grn:  #23D18B;
    --red:  #F14C4C;
    --org:  #F5A623;
    --txt0: #FFFFFF;
    --txt1: #8C8C8C;
    --txt2: #444444;
    --r:    2px;
}

/* ── Layout ── */
html, body, .stApp {
    background: var(--bg0) !important;
    color: var(--txt0) !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    font-size: 14px !important;
}
section[data-testid="stSidebar"] {
    background: var(--bg1) !important;
    border-right: 1px solid var(--bg3) !important;
}
section[data-testid="stSidebar"] * { color: var(--txt0) !important; }
div[data-testid="stAppViewContainer"],
div[data-testid="stMainBlockContainer"] { background: var(--bg0) !important; }

/* ── Cards ── */
.pal-card {
    background: var(--bg2);
    border: 1px solid var(--bg3);
    border-radius: var(--r);
    padding: 14px 18px;
    margin-bottom: 10px;
}
.pal-card-accent  { border-left: 2px solid var(--acc); }
.pal-card-green   { border-left: 2px solid var(--grn); }
.pal-card-red     { border-left: 2px solid var(--red); }
.pal-card-orange  { border-left: 2px solid var(--org); }

/* ── Metric tiles ── */
.pal-metric {
    background: var(--bg2);
    border: 1px solid var(--bg3);
    border-radius: var(--r);
    padding: 12px 14px;
    text-align: center;
}
.pal-metric .val  { font-size: 1.65rem; font-weight: 600; color: var(--acc); line-height: 1.2; }
.pal-metric .lbl  { font-size: 0.67rem; color: var(--txt1); margin-top: 4px; text-transform: uppercase; letter-spacing: .04em; }
.pal-metric .sub  { font-size: 0.64rem; color: var(--txt2); margin-top: 2px; }

/* ── Badges ── */
.badge {
    display: inline-block;
    padding: 1px 6px;
    border-radius: var(--r);
    font-size: 0.63rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: .04em;
}
.badge-ip     { background: rgba(11,136,248,0.15); color: var(--acc); }
.badge-loc    { background: rgba(35,209,139,0.12); color: var(--grn); }
.badge-org    { background: rgba(140,140,140,0.10); color: var(--txt1); }
.badge-zone   { background: rgba(245,166,35,0.12); color: var(--org); }
.badge-news   { background: rgba(140,140,140,0.08); color: var(--txt1); }
.badge-reddit { background: rgba(255,100,30,0.12);  color: #FF6B35; }
.badge-wiki   { background: rgba(11,136,248,0.10);  color: var(--acc2); }
.badge-threat { background: rgba(241,76,76,0.15);   color: var(--red); }
.badge-safe   { background: rgba(35,209,139,0.12);  color: var(--grn); }

/* ── Section headers ── */
.section-hdr {
    font-size: .67rem;
    color: var(--txt1);
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: .06em;
    padding-bottom: 5px;
    border-bottom: 1px solid var(--bg3);
    margin: 14px 0 8px;
}

/* ── Entity rows ── */
.entity-row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 7px 0;
    border-bottom: 1px solid var(--bg3);
    font-size: .83rem;
    color: var(--txt0);
}
.entity-row:last-child { border-bottom: none; }

/* ── Status dots (no glow — Palantir style) ── */
.dot { display: inline-block; width: 6px; height: 6px; border-radius: 50%; margin-right: 5px; flex-shrink: 0; }
.dot-live  { background: var(--grn); }
.dot-warn  { background: var(--org); }
.dot-dead  { background: var(--txt2); }
.dot-alert { background: var(--red); }

/* ── Risk bar ── */
.risk-bar-bg { background: var(--bg3); border-radius: 1px; height: 3px; width: 100%; }
.risk-bar    { border-radius: 1px; height: 3px; }

/* ── Timeline event ── */
.tl-event {
    display: flex; gap: 12px; padding: 8px 0;
    border-bottom: 1px solid var(--bg3); font-size: .82rem;
}
.tl-time  { color: var(--txt1); min-width: 100px; font-family: 'JetBrains Mono', monospace; font-size: .78rem; }
.tl-body  { color: var(--txt0); flex: 1; }
.tl-badge { align-self: flex-start; }

/* ── Buttons ── */
.stButton > button {
    background: transparent !important;
    border: 1px solid var(--bg4) !important;
    color: var(--txt1) !important;
    border-radius: var(--r) !important;
    font-size: .8rem !important;
    font-weight: 400 !important;
    font-family: 'Inter', sans-serif !important;
    letter-spacing: 0 !important;
    padding: 5px 14px !important;
    transition: border-color .1s, color .1s, background .1s !important;
}
.stButton > button:hover {
    border-color: var(--acc) !important;
    color: var(--acc) !important;
    background: rgba(11,136,248,0.06) !important;
}
/* Primary */
.stButton > button[kind="primary"],
.stButton > button[kind="primaryFormSubmit"] {
    background: var(--acc) !important;
    border-color: var(--acc) !important;
    color: #FFFFFF !important;
    font-weight: 500 !important;
}
.stButton > button[kind="primary"]:hover,
.stButton > button[kind="primaryFormSubmit"]:hover {
    background: var(--acc2) !important;
    border-color: var(--acc2) !important;
    color: #FFFFFF !important;
}

/* ── Tabs ── */
div[data-testid="stTabs"] { border-bottom: 1px solid var(--bg3) !important; }
div[data-testid="stTabs"] button {
    color: var(--txt1) !important;
    font-size: .82rem !important;
    font-family: 'Inter', sans-serif !important;
    border-radius: 0 !important;
    padding: 6px 16px !important;
}
div[data-testid="stTabs"] button[aria-selected="true"] {
    color: var(--txt0) !important;
    border-bottom: 2px solid var(--acc) !important;
}

/* ── Inputs ── */
div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea {
    background: var(--bg2) !important;
    border: 1px solid var(--bg3) !important;
    color: var(--txt0) !important;
    border-radius: var(--r) !important;
    font-family: 'Inter', sans-serif !important;
}
div[data-testid="stTextInput"] input:focus,
div[data-testid="stTextArea"] textarea:focus {
    border-color: var(--acc) !important;
    outline: none !important;
    box-shadow: 0 0 0 1px var(--acc) !important;
}
div[data-testid="stSelectbox"] > div { background: var(--bg2) !important; border-color: var(--bg3) !important; }

/* ── Sliders ── */
div[data-testid="stSlider"] div[data-baseweb="slider"] div[role="slider"] {
    background: var(--acc) !important;
}

/* ── Dataframes ── */
div[data-testid="stDataFrame"] {
    border: 1px solid var(--bg3) !important;
    border-radius: var(--r) !important;
}

/* ── Expander ── */
div[data-testid="stExpander"] {
    border: 1px solid var(--bg3) !important;
    border-radius: var(--r) !important;
    background: var(--bg2) !important;
}
div[data-testid="stExpander"] summary { color: var(--txt0) !important; }

/* ── Streamlit metric ── */
div[data-testid="stMetricValue"] { color: var(--acc) !important; }
div[data-testid="stMetricLabel"] { color: var(--txt1) !important; }

/* ── Status / info ── */
div[data-testid="stAlert"] { border-radius: var(--r) !important; }

/* ── Scrollbars ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg1); }
::-webkit-scrollbar-thumb { background: var(--bg4); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--txt1); }
</style>
"""

# ── Plotly base layout (Palantir palette) ──────────────────────────────────────
PLOTLY_BASE = dict(
    paper_bgcolor="#0F0F0F",
    plot_bgcolor="#0F0F0F",
    font=dict(color="#8C8C8C", family="Inter, sans-serif", size=11),
    xaxis=dict(gridcolor="#1C1C1C", zerolinecolor="#2A2A2A", linecolor="#2A2A2A"),
    yaxis=dict(gridcolor="#1C1C1C", zerolinecolor="#2A2A2A", linecolor="#2A2A2A"),
    legend=dict(bgcolor="#141414", bordercolor="#2A2A2A", borderwidth=1, font=dict(size=10, color="#8C8C8C")),
    margin=dict(l=48, r=16, t=44, b=40),
    hoverlabel=dict(bgcolor="#1C1C1C", bordercolor="#2A2A2A", font=dict(color="#FFFFFF")),
)

MAPBOX = "carto-darkmatter"


def inject_theme():
    st.markdown(THEME_CSS, unsafe_allow_html=True)


def themed(fig, title: str = "", height: int = None) -> object:
    kw = dict(**PLOTLY_BASE)
    if title:
        kw["title"] = dict(text=title, font=dict(size=12, color="#8C8C8C", family="Inter"), x=0.01)
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


def metric_html(value, label, sub="", color="#0B88F8") -> str:
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
        return "#F14C4C"
    if score >= 40:
        return "#F5A623"
    return "#23D18B"


# ── Zone type colours (data-viz, intentionally vivid) ─────────────────────────
ZONE_TYPE_COLOR = {
    "PRIMARY":   "#0B88F8",
    "SECONDARY": "#F5A623",
    "TRANSIT":   "#9B59B6",
    "NOISE":     "#444444",
}
ZONE_TYPE_FOLIUM = {
    "PRIMARY":   "blue",
    "SECONDARY": "orange",
    "TRANSIT":   "purple",
    "NOISE":     "gray",
}


def zone_type_badge(zone_type: str) -> str:
    colors = {
        "PRIMARY":   ("rgba(11,136,248,0.12)",  "#0B88F8"),
        "SECONDARY": ("rgba(245,166,35,0.12)",  "#F5A623"),
        "TRANSIT":   ("rgba(155,89,182,0.12)",  "#9B59B6"),
        "NOISE":     ("rgba(68,68,68,0.20)",    "#6C6C6C"),
    }
    bg, fg = colors.get(zone_type, ("rgba(68,68,68,0.20)", "#6C6C6C"))
    return (
        f'<span style="background:{bg};color:{fg};padding:1px 7px;border-radius:2px;'
        f'font-size:.6rem;font-weight:600;letter-spacing:.06em;border:1px solid {fg}30;'
        f'text-transform:uppercase">'
        f'{zone_type}</span>'
    )


def sparkline_svg(values: list, width: int = 96, height: int = 22,
                  color: str = "#0B88F8") -> str:
    """Render a 24-bin hourly sparkline as inline SVG."""
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
        op  = 0.20 + 0.80 * (v / max_v)
        bars += (
            f'<rect x="{x:.1f}" y="{y}" width="{max(1, bw - 1):.1f}" '
            f'height="{h}" fill="{color}" opacity="{op:.2f}"/>'
        )
    return f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">{bars}</svg>'


# ── Live clock (IST) ──────────────────────────────────────────────────────────
LIVE_CLOCK_HTML = """
<div style="display:flex;align-items:center;gap:7px;margin-bottom:10px;">
  <span style="width:6px;height:6px;border-radius:50%;background:#23D18B;
        display:inline-block;flex-shrink:0;"></span>
  <span style="font-size:.65rem;color:#8C8C8C;font-family:'JetBrains Mono',monospace;"
        id="pal-clock"></span>
</div>
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


# ── Loading overlay ───────────────────────────────────────────────────────────
LOADING_OVERLAY_HTML = """
<div id="pal-loading" style="
  position:fixed;top:0;left:0;width:100%;height:100%;
  background:rgba(15,15,15,0.95);z-index:9999;
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  font-family:'Inter',sans-serif;">
  <div style="width:32px;height:32px;border:2px solid #2A2A2A;
       border-top:2px solid #0B88F8;border-radius:50%;
       animation:spin 0.8s linear infinite;"></div>
  <div id="pal-load-msg" style="color:#8C8C8C;font-size:.72rem;letter-spacing:.08em;
       margin-top:16px;text-transform:uppercase;"></div>
</div>
<style>@keyframes spin{to{transform:rotate(360deg)}}</style>
<script>
(function(){
  var msgs = ["Resolving target","Clustering sessions","Fetching intelligence",
              "Building entity graph","Running models","Compiling report"];
  var i=0, el=document.getElementById('pal-load-msg');
  if(el){ el.textContent=msgs[0]; setInterval(function(){ i=(i+1)%msgs.length; el.textContent=msgs[i]; },500); }
  setTimeout(function(){ var ov=document.getElementById('pal-loading'); if(ov) ov.style.display='none'; },2200);
})();
</script>
"""
