"""Overview — investigation summary, key metrics, entity roster, risk score."""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from core.state import inject_theme, require_data, themed, metric_html, risk_color

st.set_page_config(page_title="Overview · Mini Palantir", page_icon="📊", layout="wide")
inject_theme()
d = require_data()

bg = d["base_geo"]
stats = d["cluster_stats"]
pred  = d["prediction"]
wdf   = d["web_df"]
ents  = d["entities"]
risk  = d["risk_score"]
factors = d["risk_factors"]

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown(
    f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:3px;">'
    f'<div style="font-size:1.1rem;font-weight:600;color:#d4dce8;">Overview</div>'
    f'<span class="badge badge-ip">{d["target_ip"]}</span>'
    f'<span class="badge badge-org">{d["case_id"]}</span>'
    f'<span style="font-size:.68rem;color:#6b7685;margin-left:auto;">'
    f'{d["analyzed_at"].strftime("%Y-%m-%d %H:%M")}</span>'
    f'</div>'
    f'<div style="font-size:.75rem;color:#6b7685;margin-bottom:18px;">'
    f'{bg.get("city","")}, {bg.get("regionName") or bg.get("region","")}, {bg.get("country","")} · '
    f'ISP: {bg.get("isp","N/A")} · TZ: {bg.get("timezone","N/A")}'
    f'</div>',
    unsafe_allow_html=True,
)

# ── Top metrics ────────────────────────────────────────────────────────────────
valid_zones = stats[stats["cluster_id"] != -1]
mc = st.columns(6)
tiles = [
    (str(len(d["clustered_df"])), "Sessions", "simulated"),
    (str(valid_zones["sessions"].sum()), "Clustered", "in valid zones"),
    (f"{d['clustered_df']['duration_min'].sum() / 60:.0f}h", "Total Active", "all time"),
    (str(len(valid_zones)), "Zones Found", "DBSCAN clusters"),
    (str(len(wdf)), "Intel Items", "web sources"),
    (str(len(ents)), "Entities", "extracted"),
]
for col, (val, lbl, sub) in zip(mc, tiles):
    with col:
        st.markdown(metric_html(val, lbl, sub), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Risk score + factors ───────────────────────────────────────────────────────
col_risk, col_pred, col_geo = st.columns([1, 1, 1], gap="medium")

with col_risk:
    rc = risk_color(risk)
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=risk,
        title={"text": "Risk Score", "font": {"size": 12, "color": "#8b949e"}},
        number={"font": {"size": 36, "color": rc}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "#30363d"},
            "bar": {"color": rc, "thickness": 0.25},
            "bgcolor": "#161b22",
            "borderwidth": 0,
            "steps": [
                {"range": [0,  40], "color": "#1f3a2e"},
                {"range": [40, 70], "color": "#3a2a1f"},
                {"range": [70,100], "color": "#3a1f1f"},
            ],
        },
    ))
    themed(fig_gauge, height=240)
    fig_gauge.update_layout(margin=dict(l=20, r=20, t=40, b=10))
    st.plotly_chart(fig_gauge, use_container_width=True)

    for msg, kind in factors:
        color = {"alert": "#f85149", "warn": "#d29922", "safe": "#3fb950"}.get(kind, "#8b949e")
        dot   = {"alert": "dot-alert", "warn": "dot-warn",  "safe": "dot-live"}.get(kind, "dot-dead")
        st.markdown(
            f'<div class="entity-row"><span class="dot {dot}"></span>'
            f'<span style="color:{color};font-size:.8rem;">{msg}</span></div>',
            unsafe_allow_html=True,
        )

with col_pred:
    if pred:
        conf_c = risk_color(100 - pred["confidence"])
        st.markdown(
            f'<div class="pal-card pal-card-green">'
            f'<div class="section-hdr">Predicted Current Location</div>'
            f'<div style="font-size:1.4rem;font-weight:700;color:#e6edf3;">{pred["city"]}</div>'
            f'<div style="color:#8b949e;font-size:.8rem;">{pred["country"]} · {pred["zone"]}</div>'
            f'<div style="margin-top:12px;font-family:monospace;font-size:.8rem;color:#58a6ff;">'
            f'{pred["lat"]}° N &nbsp; {pred["lon"]}° E</div>'
            f'<div style="margin-top:10px;">'
            f'<div class="risk-bar-bg"><div class="risk-bar" style="width:{pred["confidence"]}%;background:{conf_c};"></div></div>'
            f'<div style="font-size:.7rem;color:#8b949e;margin-top:4px;">'
            f'Confidence: <b style="color:{conf_c}">{pred["confidence"]}%</b></div>'
            f'</div>'
            f'<div style="margin-top:10px;font-size:.75rem;color:#8b949e;">'
            f'{pred["sessions"]} sessions · {pred["total_hours"]}h total</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

with col_geo:
    st.markdown(
        f'<div class="pal-card pal-card-accent">'
        f'<div class="section-hdr">Target Profile</div>'
        f'<div class="entity-row"><span class="badge badge-ip">IP</span>{bg.get("query","")}</div>'
        f'<div class="entity-row"><span class="badge badge-loc">CITY</span>{bg.get("city","")}, {bg.get("regionName") or bg.get("region","")}</div>'
        f'<div class="entity-row"><span class="badge badge-loc">COUNTRY</span>{bg.get("country","")}</div>'
        f'<div class="entity-row"><span class="badge badge-org">ISP</span>{bg.get("isp","")}</div>'
        f'<div class="entity-row"><span class="badge badge-org">ORG</span>{bg.get("org","")}</div>'
        f'<div class="entity-row"><span class="badge badge-zone">TZ</span>{bg.get("timezone","")}</div>'
        f'<div class="entity-row"><span class="badge badge-zone">LAT/LON</span>{bg.get("lat","")} / {bg.get("lon","")}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

st.markdown("---")

# ── Zone summary table ─────────────────────────────────────────────────────────
col_zones, col_entities = st.columns([1.2, 1], gap="medium")

with col_zones:
    st.markdown('<div class="section-hdr">Activity Zones</div>', unsafe_allow_html=True)
    disp = valid_zones[["label", "city", "centroid_lat", "centroid_lon",
                         "sessions", "total_hours", "last_seen", "likelihood_pct"]].copy()
    disp.columns = ["Zone", "City", "Lat", "Lon", "Sessions", "Hours", "Last Seen", "Likelihood %"]
    st.dataframe(disp, use_container_width=True, hide_index=True)

with col_entities:
    st.markdown('<div class="section-hdr">Entity Roster</div>', unsafe_allow_html=True)
    type_counts = pd.DataFrame(
        [(e["type"], e["value"][:35], f"{e['confidence']*100:.0f}%") for e in ents],
        columns=["Type", "Value", "Confidence"],
    )
    st.dataframe(type_counts.head(20), use_container_width=True, hide_index=True)

# ── Intel source breakdown ─────────────────────────────────────────────────────
if not wdf.empty:
    st.markdown("---")
    st.markdown('<div class="section-hdr">Intelligence Source Breakdown</div>', unsafe_allow_html=True)
    src_counts = wdf["category"].value_counts()
    fig_src = go.Figure(go.Bar(
        x=src_counts.index.tolist(),
        y=src_counts.values.tolist(),
        marker=dict(
            color=["#4C72B0", "#ff6314", "#3fb950", "#bc8cff"][:len(src_counts)],
            line=dict(color="#0d1117", width=1),
        ),
        text=src_counts.values.tolist(),
        textposition="outside",
        textfont=dict(color="#e6edf3", size=11),
    ))
    themed(fig_src, "Intel Items by Source", height=280)
    fig_src.update_layout(xaxis_title="", yaxis_title="Items", showlegend=False)
    st.plotly_chart(fig_src, use_container_width=True)
