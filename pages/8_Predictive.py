"""
Predictive Intelligence Engine — beyond Palantir.
Forecasts WHERE and WHEN the target will be active next.
Detects behavioral drift and counter-intelligence signals.
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
from core.state import inject_theme, require_data, themed, risk_color, MAPBOX
from core.predictor import (
    predict_next_window,
    predict_next_location,
    forecast_activity,
    detect_drift,
    detect_counter_intel,
)

st.set_page_config(page_title="Predictive · Mini Palantir", page_icon="🔮", layout="wide")
inject_theme()
d = require_data()

adf    = d["anomaly_df"]
stats  = d["cluster_stats"]
bg     = d["base_geo"]

st.markdown(
    '<div style="font-size:1.1rem;font-weight:600;color:#F0F0F0;margin-bottom:3px;">Predictive Intelligence</div>'
    '<div style="font-size:.75rem;color:#8C8C8C;margin-bottom:18px;">'
    'Behavior forecast · Drift detection · Counter-intelligence signals</div>',
    unsafe_allow_html=True,
)

# ── Compute predictions (cache in session) ─────────────────────────────────────
if "predictions" not in st.session_state or st.session_state.get("pred_ip") != d["target_ip"]:
    with st.spinner("Running predictive models…"):
        next_window = predict_next_window(adf)
        next_loc    = predict_next_location(stats, adf)
        forecast    = forecast_activity(adf)
        drift       = detect_drift(adf)
        ci          = detect_counter_intel(adf, bg)
    st.session_state["predictions"] = {
        "window": next_window, "location": next_loc,
        "forecast": forecast, "drift": drift, "ci": ci,
    }
    st.session_state["pred_ip"] = d["target_ip"]

p = st.session_state["predictions"]
nw   = p["window"]
nl   = p["location"]
fc   = p["forecast"]
drift = p["drift"]
ci   = p["ci"]

tab_next, tab_forecast, tab_drift, tab_ci = st.tabs([
    "Next Activity Prediction", "7-Day Forecast", "Behavioral Drift", "Counter-Intel Signals"
])

# ══════════════════════════════════════════════════════════════════
# TAB 1 — NEXT ACTIVITY PREDICTION
# ══════════════════════════════════════════════════════════════════
with tab_next:
    col_time, col_loc, col_map = st.columns([1, 1, 2])

    with col_time:
        conf_c = risk_color(100 - min(nw["confidence"], 100))
        st.markdown(
            f'<div class="pal-card pal-card-accent">'
            f'<div class="section-hdr">Next Active Window</div>'
            f'<div style="font-size:1.6rem;font-weight:700;color:#0B88F8">{nw["peak_day"]}</div>'
            f'<div style="font-size:1.2rem;color:#F0F0F0">{nw["peak_hour"]:02d}:00 – {(nw["peak_hour"]+2)%24:02d}:00</div>'
            f'<div style="font-size:.8rem;color:#8C8C8C;margin-top:8px;">'
            f'In approximately <b style="color:#F5A623">{nw["hours_until"]}h</b></div>'
            f'<div style="font-size:.75rem;color:#8C8C8C;margin-top:4px;">'
            f'{nw["next_window"].strftime("%Y-%m-%d %H:%M")}</div>'
            f'<div style="margin-top:12px;">'
            f'<div class="risk-bar-bg"><div class="risk-bar" style="width:{min(nw["confidence"],100)}%;background:{conf_c}"></div></div>'
            f'<div style="font-size:.7rem;color:{conf_c};margin-top:3px;">Confidence: {min(nw["confidence"],100):.0f}%</div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

        # Hour probability bar
        fig_hp = go.Figure(go.Bar(
            x=list(range(24)),
            y=nw["hour_probs"],
            marker=dict(
                color=nw["hour_probs"],
                colorscale=[[0,"#1C1C1C"],[1,"#0B88F8"]],
                line=dict(color="#0F0F0F", width=0.5),
            ),
        ))
        fig_hp.add_vline(x=nw["peak_hour"], line_color="#F5A623", line_dash="dash")
        themed(fig_hp, "Hourly Activity Probability", height=220)
        fig_hp.update_layout(xaxis=dict(title="Hour", dtick=4), yaxis=dict(title="Probability"),
                             margin=dict(l=30,r=10,t=40,b=30))
        st.plotly_chart(fig_hp, use_container_width=True)

    with col_loc:
        if nl:
            conf_c2 = risk_color(100 - nl["confidence"])
            st.markdown(
                f'<div class="pal-card pal-card-green">'
                f'<div class="section-hdr">Predicted Next Location</div>'
                f'<div style="font-size:1.4rem;font-weight:700;color:#23D18B">{nl["city"]}</div>'
                f'<div style="font-size:.85rem;color:#8C8C8C">{nl["country"]} · {nl["zone"]}</div>'
                f'<div style="font-family:monospace;font-size:.8rem;color:#0B88F8;margin-top:8px;">'
                f'{nl["lat"]}° N, {nl["lon"]}° E</div>'
                f'<div style="font-size:.75rem;color:#8C8C8C;margin-top:4px;">'
                f'Uncertainty radius: ±{nl["radius_km"]}km</div>'
                f'<div style="margin-top:10px;">'
                f'<div class="risk-bar-bg"><div class="risk-bar" style="width:{nl["confidence"]}%;background:{conf_c2}"></div></div>'
                f'<div style="font-size:.7rem;color:{conf_c2};margin-top:3px;">Location confidence: {nl["confidence"]:.0f}%</div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )

            # Day probability bar
            fig_dp = go.Figure(go.Bar(
                x=nw["day_names"],
                y=nw["day_probs"],
                marker=dict(
                    color=nw["day_probs"],
                    colorscale=[[0,"#1C1C1C"],[1,"#23D18B"]],
                    line=dict(color="#0F0F0F", width=0.5),
                ),
            ))
            fig_dp.add_vline(x=nw["peak_day"], line_color="#F5A623", line_dash="dash")
            themed(fig_dp, "Day-of-Week Activity Probability", height=220)
            fig_dp.update_layout(xaxis=dict(title=""), yaxis=dict(title="Probability"),
                                 margin=dict(l=30,r=10,t=40,b=30))
            st.plotly_chart(fig_dp, use_container_width=True)

    with col_map:
        if nl:
            pred_map = folium.Map(location=[nl["lat"], nl["lon"]], zoom_start=10,
                                  tiles="CartoDB dark_matter")
            # Uncertainty circle
            folium.Circle(
                location=[nl["lat"], nl["lon"]],
                radius=nl["radius_km"] * 1000,
                color="#23D18B", fill=True, fill_opacity=0.12,
                tooltip=f"Uncertainty radius: ±{nl['radius_km']}km",
            ).add_to(pred_map)
            # Prediction pin
            folium.Marker(
                location=[nl["lat"], nl["lon"]],
                popup=f"Predicted: {nl['city']} ({nl['confidence']}%)",
                tooltip=f"Next location: {nl['city']}",
                icon=folium.Icon(color="green", icon="crosshairs", prefix="fa"),
            ).add_to(pred_map)
            # All scored zones
            if "all_scored" in nl:
                for _, row in nl["all_scored"].iterrows():
                    alpha = max(0.1, float(row["score"]))
                    folium.CircleMarker(
                        location=[row["centroid_lat"], row["centroid_lon"]],
                        radius=max(6, float(row["score"]) * 30),
                        color="#0B88F8", fill=True, fill_opacity=min(alpha, 0.5),
                        tooltip=f"{row['label']}: score {row['score']:.3f}",
                    ).add_to(pred_map)

            st_folium(pred_map, height=460, returned_objects=[], key="pred_map")

# ══════════════════════════════════════════════════════════════════
# TAB 2 — 7-DAY FORECAST
# ══════════════════════════════════════════════════════════════════
with tab_forecast:
    if fc.empty:
        st.info("Not enough data for forecasting (need at least 3 days of history).")
    else:
        historical = fc[~fc["is_forecast"]]
        predicted  = fc[fc["is_forecast"]]

        fig_fc = go.Figure()
        # Historical
        fig_fc.add_trace(go.Scatter(
            x=historical["date"].astype(str), y=historical["forecast_hours"],
            name="Historical", mode="lines+markers",
            line=dict(color="#0B88F8", width=2),
            marker=dict(size=5),
        ))
        # Forecast line
        fig_fc.add_trace(go.Scatter(
            x=predicted["date"].astype(str), y=predicted["forecast_hours"],
            name="Forecast", mode="lines+markers",
            line=dict(color="#23D18B", width=2, dash="dash"),
            marker=dict(size=6, symbol="diamond"),
        ))
        # Confidence band
        fig_fc.add_trace(go.Scatter(
            x=list(predicted["date"].astype(str)) + list(predicted["date"].astype(str))[::-1],
            y=list(predicted["upper"]) + list(predicted["lower"])[::-1],
            fill="toself", fillcolor="rgba(63,185,80,0.10)",
            line=dict(color="rgba(0,0,0,0)"),
            name="Confidence Band", hoverinfo="skip",
        ))
        # Today marker
        fig_fc.add_vline(
            x=str(pd.Timestamp.now().date()),
            line_color="#F5A623", line_dash="dash",
            annotation_text="Today", annotation_font_color="#F5A623",
        )
        themed(fig_fc, "7-Day Activity Forecast (hours/day)", height=420)
        fig_fc.update_layout(xaxis_title="Date", yaxis_title="Active Hours",
                             xaxis=dict(tickangle=45))
        st.plotly_chart(fig_fc, use_container_width=True)

        # Forecast table
        st.markdown('<div class="section-hdr">Forecast Table</div>', unsafe_allow_html=True)
        tbl = predicted[["date","forecast_hours","lower","upper"]].copy()
        tbl.columns = ["Date","Forecast (h)","Low (h)","High (h)"]
        st.dataframe(tbl, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════
# TAB 3 — BEHAVIORAL DRIFT
# ══════════════════════════════════════════════════════════════════
with tab_drift:
    dc = risk_color(drift["drift_score"])
    st.markdown(
        f'<div class="pal-card" style="border-left:4px solid {dc};">'
        f'<div style="display:flex;align-items:center;gap:16px;">'
        f'<div style="font-size:2rem;font-weight:700;color:{dc}">{drift["drift_score"]}</div>'
        f'<div>'
        f'<div style="font-size:1rem;font-weight:700;color:{dc}">'
        f'{"DRIFT DETECTED" if drift["drift_detected"] else "NO SIGNIFICANT DRIFT"}</div>'
        f'<div style="font-size:.75rem;color:#8C8C8C;">'
        f'Early: {drift.get("early_period","?")} · Recent: {drift.get("recent_period","?")}</div>'
        f'</div></div></div>',
        unsafe_allow_html=True,
    )

    if drift["changes"]:
        st.markdown('<div class="section-hdr" style="margin-top:16px">Detected Changes</div>',
                    unsafe_allow_html=True)
        for change in drift["changes"]:
            st.markdown(
                f'<div class="entity-row"><span class="dot dot-warn"></span>'
                f'<span style="color:#F5A623;font-size:.85rem;">{change}</span></div>',
                unsafe_allow_html=True,
            )

    # Early vs recent radar comparison
    if drift.get("early_profile") and drift.get("recent_profile"):
        ep = drift["early_profile"]
        rp = drift["recent_profile"]
        cats = list(ep.keys())
        fig_r = go.Figure()
        for profile, name, color in [(ep,"Early Period","#8C8C8C"), (rp,"Recent Period","#0B88F8")]:
            vals = [profile[c] for c in cats]
            # Normalise roughly
            norms = [
                vals[0]/23,      # peak_hour
                vals[1]/300,     # avg_duration
                vals[2],         # night_pct
                vals[3],         # remote_pct
                vals[4],         # weekend_pct
            ]
            norms.append(norms[0])
            fig_r.add_trace(go.Scatterpolar(
                r=norms + [norms[0]],
                theta=cats + [cats[0]],
                fill="toself", name=name,
                line=dict(color=color), opacity=0.7,
            ))
        themed(fig_r, "Behavioral Profile: Early vs Recent", height=420)
        fig_r.update_layout(polar=dict(
            bgcolor="#1C1C1C",
            radialaxis=dict(color="#444444", gridcolor="#2A2A2A", range=[0,1]),
            angularaxis=dict(color="#8C8C8C", gridcolor="#2A2A2A"),
        ))
        st.plotly_chart(fig_r, use_container_width=True)

        st.markdown(
            f'<div class="pal-card pal-card-accent" style="margin-top:8px">'
            f'<div class="section-hdr">Interpretation</div>'
            f'<div style="font-size:.85rem;color:#F0F0F0;">'
            f'A drift score above 25 suggests the target\'s behavior has meaningfully changed '
            f'between the early and recent periods. This could indicate:<br><br>'
            f'• <b>Life change</b> (new job, relocation, relationship) — benign<br>'
            f'• <b>Counter-intelligence awareness</b> — target knows they\'re being monitored<br>'
            f'• <b>Operational change</b> — new assignment, travel, or mission<br>'
            f'• <b>Identity change</b> — different person using the same connection<br><br>'
            f'Current drift score: <b style="color:{dc}">{drift["drift_score"]}/100</b>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

# ══════════════════════════════════════════════════════════════════
# TAB 4 — COUNTER-INTELLIGENCE SIGNALS
# ══════════════════════════════════════════════════════════════════
with tab_ci:
    ci_colors = {"HIGH": "#F14C4C", "MEDIUM": "#F5A623", "LOW": "#23D18B"}
    ci_c = ci_colors.get(ci["ci_level"], "#8C8C8C")
    ci_dot = {"HIGH": "dot-alert", "MEDIUM": "dot-warn", "LOW": "dot-live"}.get(ci["ci_level"], "dot-dead")

    st.markdown(
        f'<div class="pal-card" style="border-left:4px solid {ci_c};margin-bottom:20px;">'
        f'<div style="display:flex;align-items:center;gap:16px;">'
        f'<div style="font-size:2.5rem;font-weight:700;color:{ci_c}">{ci["ci_score"]}</div>'
        f'<div>'
        f'<div style="font-size:1.1rem;font-weight:700;color:{ci_c}">COUNTER-INTEL RISK: {ci["ci_level"]}</div>'
        f'<div style="font-size:.75rem;color:#8C8C8C;">Probability that target is aware of monitoring</div>'
        f'</div></div></div>',
        unsafe_allow_html=True,
    )

    signal_colors = {"critical": "#F14C4C","high": "#F14C4C","medium": "#F5A623","clear": "#23D18B"}
    signal_dots   = {"critical": "dot-alert","high": "dot-alert","medium": "dot-warn","clear": "dot-live"}

    for msg, level in ci["signals"]:
        sc = signal_colors.get(level, "#8C8C8C")
        sd = signal_dots.get(level, "dot-dead")
        st.markdown(
            f'<div class="entity-row"><span class="dot {sd}"></span>'
            f'<span style="color:{sc};font-size:.85rem;">{msg}</span>'
            f'<span class="badge badge-{"threat" if level in ["critical","high"] else "safe" if level=="clear" else "zone"}" '
            f'style="margin-left:auto">{level.upper()}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        f'<div class="pal-card pal-card-accent" style="margin-top:20px">'
        f'<div class="section-hdr">What is Counter-Intelligence Detection?</div>'
        f'<div style="font-size:.82rem;color:#F0F0F0;line-height:1.6;">'
        f'This module identifies behavioral signals that suggest the target may be <b>aware of surveillance</b>. '
        f'These include:<br><br>'
        f'<b>VPN/proxy use</b> — routing traffic through anonymising infrastructure<br>'
        f'<b>Randomised timing</b> — deliberately irregular session patterns to avoid profiling<br>'
        f'<b>Sudden geographic shift</b> — moving to remote zones after regular primary-zone activity<br>'
        f'<b>Activity gaps post-anomaly</b> — going dark after high-anomaly periods<br>'
        f'<b>Timezone/location mismatch</b> — ISP location inconsistent with timezone<br><br>'
        f'<b>This capability does not exist in Palantir\'s standard offering.</b>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    # CI score gauge
    fig_cig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=ci["ci_score"],
        title={"text": "Counter-Intel Risk Score", "font": {"size": 12, "color": "#8C8C8C"}},
        number={"font": {"size": 32, "color": ci_c}},
        gauge={
            "axis": {"range": [0, 100]},
            "bar":  {"color": ci_c, "thickness": 0.25},
            "bgcolor": "#1C1C1C", "borderwidth": 0,
            "steps": [
                {"range": [0,  30], "color": "#1f3a2e"},
                {"range": [30, 60], "color": "#3a2a1f"},
                {"range": [60,100], "color": "#3a1f1f"},
            ],
        },
    ))
    themed(fig_cig, height=280)
    fig_cig.update_layout(margin=dict(l=20,r=20,t=40,b=10))
    st.plotly_chart(fig_cig, use_container_width=True)
