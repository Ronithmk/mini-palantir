"""Pattern of Life — behavioural heatmaps, timeline, anomaly signals, profile."""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from core.state import inject_theme, require_data, themed

st.set_page_config(page_title="Pattern of Life · Mini Palantir", page_icon="📅", layout="wide")
inject_theme()
d = require_data()

adf   = d["anomaly_df"].copy()
clust = d["clustered_df"].copy()
adf["date"]   = adf["timestamp"].dt.date
adf["week"]   = adf["timestamp"].dt.isocalendar().week.astype(int)
adf["month"]  = adf["timestamp"].dt.strftime("%b")
clust["date"] = clust["timestamp"].dt.date

st.markdown(
    '<div style="font-size:1.5rem;font-weight:700;color:#58a6ff;margin-bottom:4px;">📅 PATTERN OF LIFE</div>'
    f'<div style="font-size:.75rem;color:#8b949e;margin-bottom:20px;">'
    f'Analysing {len(adf)} sessions over {adf["date"].nunique()} days · Target: {d["target_ip"]}</div>',
    unsafe_allow_html=True,
)

# ── Behavioural profile (inferred) ────────────────────────────────────────────
peak_hour  = int(adf.groupby("hour")["duration_min"].sum().idxmax())
peak_day   = adf.groupby("weekday")["duration_min"].sum().idxmax()
primary_z  = clust.groupby("zone_label")["duration_min"].sum().idxmax()
night_pct  = adf["hour"].between(1, 4).mean() * 100
wknd_pct   = adf["weekday"].isin(["Saturday", "Sunday"]).mean() * 100

profile_items = [
    ("Peak Activity Hour",   f"{peak_hour:02d}:00",   "acc"),
    ("Peak Activity Day",    peak_day,                "acc"),
    ("Primary Zone",         primary_z,               "grn"),
    ("Night-time Activity",  f"{night_pct:.1f}%",     "red" if night_pct > 15 else "org"),
    ("Weekend Activity",     f"{wknd_pct:.1f}%",      "acc"),
    ("Anomaly Rate",         f'{adf["anomaly"].mean()*100:.1f}%', "red" if adf["anomaly"].mean()>0.2 else "org"),
]

cols = st.columns(len(profile_items))
colors = {"acc": "#58a6ff", "grn": "#3fb950", "red": "#f85149", "org": "#d29922"}
for col, (lbl, val, c) in zip(cols, profile_items):
    with col:
        st.markdown(
            f'<div class="pal-metric">'
            f'<div class="val" style="color:{colors[c]};font-size:1.3rem">{val}</div>'
            f'<div class="lbl">{lbl}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

st.markdown("<br>", unsafe_allow_html=True)

# ── Heatmap: weekday × hour ────────────────────────────────────────────────────
tab_heat, tab_timeline, tab_duration, tab_calendar = st.tabs([
    "Heatmap", "Timeline", "Duration Analysis", "Calendar"
])

with tab_heat:
    col_h1, col_h2 = st.columns(2)

    with col_h1:
        day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        hourly = adf.groupby(["weekday", "hour"])["duration_min"].sum().reset_index()
        hourly["weekday"] = pd.Categorical(hourly["weekday"], categories=day_order, ordered=True)
        pivot = hourly.sort_values("weekday").pivot_table(
            index="weekday", columns="hour", values="duration_min", fill_value=0
        )
        fig_heat = go.Figure(go.Heatmap(
            z=pivot.values,
            x=pivot.columns.tolist(),
            y=pivot.index.tolist(),
            colorscale=[[0,"#0d1117"],[0.3,"#1f3a5f"],[0.7,"#4C72B0"],[1,"#58a6ff"]],
            hovertemplate="Day: %{y}<br>Hour: %{x}:00<br>Minutes: %{z:.0f}<extra></extra>",
        ))
        themed(fig_heat, "Activity Heatmap — Weekday × Hour", height=360)
        fig_heat.update_layout(
            xaxis=dict(title="Hour of Day", dtick=2, gridcolor="#21262d"),
            yaxis=dict(title=""),
        )
        st.plotly_chart(fig_heat, use_container_width=True)

    with col_h2:
        # Hourly distribution (bar)
        hourly_bar = adf.groupby("hour")["duration_min"].sum().reset_index()
        fig_hb = go.Figure(go.Bar(
            x=hourly_bar["hour"], y=hourly_bar["duration_min"] / 60,
            marker=dict(
                color=hourly_bar["duration_min"],
                colorscale=[[0,"#161b22"],[1,"#58a6ff"]],
                line=dict(color="#0d1117", width=0.5),
            ),
            hovertemplate="Hour %{x}:00 — %{y:.1f}h<extra></extra>",
        ))
        themed(fig_hb, "Total Activity by Hour of Day (hours)", height=360)
        fig_hb.update_layout(xaxis=dict(title="Hour", dtick=2), yaxis=dict(title="Hours"))
        # Mark peak hour
        fig_hb.add_vline(x=peak_hour, line_color="#d29922", line_dash="dash",
                         annotation_text="peak", annotation_font_color="#d29922")
        st.plotly_chart(fig_hb, use_container_width=True)

    # Zone × hour heatmap
    zh = adf.groupby(["zone_label", "hour"])["duration_min"].sum().reset_index()
    pivot_zh = zh.pivot_table(index="zone_label", columns="hour", values="duration_min", fill_value=0)
    fig_zh = go.Figure(go.Heatmap(
        z=pivot_zh.values,
        x=pivot_zh.columns.tolist(),
        y=pivot_zh.index.tolist(),
        colorscale=[[0,"#0d1117"],[0.5,"#3a2a1f"],[1,"#d29922"]],
        hovertemplate="Zone: %{y}<br>Hour: %{x}:00<br>Minutes: %{z:.0f}<extra></extra>",
    ))
    themed(fig_zh, "Zone Activity by Hour", height=300)
    fig_zh.update_layout(xaxis=dict(title="Hour", dtick=2), yaxis=dict(title=""))
    st.plotly_chart(fig_zh, use_container_width=True)

with tab_timeline:
    daily = adf.groupby(["date", "zone_label"])["duration_min"].sum().reset_index()
    daily["hours"] = (daily["duration_min"] / 60).round(2)

    fig_area = go.Figure()
    ZONE_COLORS = {"Primary Zone": "#58a6ff", "Secondary Zone": "#d29922",
                   "Travel / Remote": "#f85149", "Noise": "#484f58"}
    ZONE_FILL = {
        "Primary Zone":   "rgba(88,166,255,0.12)",
        "Secondary Zone": "rgba(210,153,34,0.12)",
        "Travel / Remote":"rgba(248,81,73,0.12)",
        "Noise":          "rgba(72,79,88,0.10)",
    }
    for zone in daily["zone_label"].unique():
        sub = daily[daily["zone_label"] == zone]
        fig_area.add_trace(go.Scatter(
            x=sub["date"], y=sub["hours"], name=zone,
            fill="tozeroy", mode="lines",
            line=dict(color=ZONE_COLORS.get(zone, "#8b949e"), width=1.5),
            fillcolor=ZONE_FILL.get(zone, "rgba(139,148,158,0.10)"),
        ))
    themed(fig_area, "Daily Activity Timeline (hours per zone)", height=400)
    fig_area.update_layout(xaxis_title="Date", yaxis_title="Hours Active")
    st.plotly_chart(fig_area, use_container_width=True)

    # Anomaly overlay on timeline
    anom_daily = adf[adf["anomaly"]].groupby("date").size().reset_index(name="anomalies")
    fig_anom = go.Figure()
    fig_anom.add_trace(go.Bar(
        x=anom_daily["date"], y=anom_daily["anomalies"],
        marker_color="#f85149", name="Anomalous Sessions",
        opacity=0.85,
    ))
    themed(fig_anom, "Daily Anomaly Count", height=250)
    fig_anom.update_layout(xaxis_title="Date", yaxis_title="Anomalies", showlegend=False)
    st.plotly_chart(fig_anom, use_container_width=True)

with tab_duration:
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        fig_hist = go.Figure(go.Histogram(
            x=adf["duration_min"], nbinsx=40,
            marker=dict(color="#58a6ff", line=dict(color="#0d1117", width=0.5)),
            opacity=0.85,
        ))
        p25 = adf["duration_min"].quantile(0.25)
        p75 = adf["duration_min"].quantile(0.75)
        fig_hist.add_vline(x=adf["duration_min"].median(), line_color="#3fb950", line_dash="dash",
                           annotation_text="median", annotation_font_color="#3fb950")
        fig_hist.add_vrect(x0=p25, x1=p75, fillcolor="#58a6ff", opacity=0.08, line_width=0)
        themed(fig_hist, "Session Duration Distribution (minutes)", height=360)
        fig_hist.update_layout(xaxis_title="Duration (min)", yaxis_title="Sessions", bargap=0.05)
        st.plotly_chart(fig_hist, use_container_width=True)

    with col_d2:
        box_data = [adf[adf["zone_label"] == z]["duration_min"].values
                    for z in adf["zone_label"].unique()]
        zone_names = list(adf["zone_label"].unique())
        fig_box = go.Figure()
        for name, data, color in zip(zone_names, box_data,
                                     ["#58a6ff","#d29922","#f85149","#8b949e"]):
            fig_box.add_trace(go.Box(
                y=data, name=name,
                marker_color=color, line_color=color,
                boxmean="sd",
            ))
        themed(fig_box, "Session Duration by Zone", height=360)
        fig_box.update_layout(yaxis_title="Duration (min)", showlegend=False)
        st.plotly_chart(fig_box, use_container_width=True)

with tab_calendar:
    # Calendar heatmap: date vs total hours
    daily_total = adf.groupby("date")["duration_min"].sum().reset_index()
    daily_total["hours"] = daily_total["duration_min"] / 60
    daily_total["date"]  = pd.to_datetime(daily_total["date"])
    daily_total["dow"]   = daily_total["date"].dt.day_name()
    daily_total["week"]  = daily_total["date"].dt.isocalendar().week.astype(int)
    daily_total["month"] = daily_total["date"].dt.strftime("%b %Y")

    fig_cal = px.density_heatmap(
        daily_total, x="date", y="dow",
        z="hours",
        color_continuous_scale=[[0,"#0d1117"],[0.4,"#1f3a5f"],[1,"#58a6ff"]],
        nbinsx=len(daily_total),
    )
    themed(fig_cal, "Calendar Heatmap — Daily Activity (hours)", height=320)
    fig_cal.update_layout(
        xaxis_title="Date", yaxis_title="",
        coloraxis_colorbar=dict(title="Hours", tickfont=dict(color="#8b949e")),
        yaxis=dict(categoryorder="array",
                   categoryarray=["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]),
    )
    st.plotly_chart(fig_cal, use_container_width=True)

    # Behavioural inference card
    night_label = "High" if night_pct > 15 else "Low"
    wknd_label  = "Active" if wknd_pct > 30 else "Mostly weekdays"
    hour_type   = "Business hours" if 8 <= peak_hour <= 18 else "Evening" if 18 < peak_hour <= 23 else "Late night"
    st.markdown(
        f'<div class="pal-card pal-card-accent">'
        f'<div class="section-hdr">Behavioural Profile (Inferred)</div>'
        f'<div class="entity-row"><span class="badge badge-zone">SCHEDULE</span> {hour_type} user — peak at {peak_hour:02d}:00</div>'
        f'<div class="entity-row"><span class="badge badge-zone">WEEKEND</span> {wknd_label} ({wknd_pct:.0f}% weekend sessions)</div>'
        f'<div class="entity-row"><span class="badge badge-threat">NIGHT</span> Night activity {night_label} ({night_pct:.1f}%)</div>'
        f'<div class="entity-row"><span class="badge badge-loc">ZONE</span> Primary location: {primary_z}</div>'
        f'<div class="entity-row"><span class="badge badge-org">ANOMALY</span> {adf["anomaly"].sum()} flagged sessions ({adf["anomaly"].mean()*100:.1f}%)</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
