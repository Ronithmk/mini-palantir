"""Dashboard - consolidated investigation view."""
from __future__ import annotations

from datetime import datetime
from html import escape

import networkx as nx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core.predictor import (
    build_fingerprint,
    detect_counter_intel,
    detect_drift,
    forecast_activity,
    predict_next_window,
)
from core.state import inject_theme, metric_html, require_data, risk_color, themed
from core.watchlist import alerts_for, load_watchlist


st.set_page_config(page_title="Dashboard - ARGUS", page_icon=":bar_chart:", layout="wide")
inject_theme()
d = require_data()

bg = d["base_geo"]
stats = d["cluster_stats"]
clust = d["clustered_df"].copy()
adf = d["anomaly_df"].copy()
wdf = d["web_df"].copy()
ents = d["entities"]
graph: nx.Graph = d["graph"]
risk = int(d["risk_score"])
factors = d["risk_factors"]
pred = d["prediction"]
valid = stats[stats["cluster_id"] != -1].copy()

target_domain = d.get("target_domain")
target_label = target_domain or d["target_ip"]
target_sub = f"{d['target_ip']}" if target_domain else ""
rc = risk_color(risk)
risk_label = "HIGH" if risk >= 70 else "MEDIUM" if risk >= 40 else "LOW"


def _fmt_dt(value) -> str:
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d %H:%M")
    return str(value)


def _safe(value, default: str = "N/A") -> str:
    if value is None or value == "":
        return default
    return escape(str(value))


def _metric_row() -> None:
    anomaly_count = int(adf["anomaly"].sum()) if "anomaly" in adf else 0
    total_hours = adf["duration_min"].sum() / 60 if "duration_min" in adf else 0
    tiles = [
        (len(adf), "Sessions", f"{adf['timestamp'].dt.date.nunique()} days"),
        (f"{total_hours:.0f}h", "Active Time", "simulated history"),
        (len(valid), "Zones", "DBSCAN clusters"),
        (len(wdf), "Intel Items", d.get("query", "")),
        (graph.number_of_nodes(), "Graph Nodes", f"{graph.number_of_edges()} edges"),
        (anomaly_count, "Anomalies", f"{(anomaly_count / max(len(adf), 1)) * 100:.1f}% rate"),
    ]
    cols = st.columns(len(tiles))
    for col, (value, label, sub) in zip(cols, tiles):
        with col:
            color = "#F14C4C" if label == "Anomalies" and int(anomaly_count) else "#0B88F8"
            st.markdown(metric_html(value, label, sub, color=color), unsafe_allow_html=True)


def _render_case_header() -> None:
    st.markdown(
        f"""
        <div style="display:flex;align-items:flex-start;gap:12px;margin-bottom:10px;flex-wrap:wrap;">
          <div style="flex:1;min-width:260px;">
            <div style="font-size:1.2rem;font-weight:650;color:#F0F0F0;">Mission Dashboard</div>
            <div style="font-size:.76rem;color:#8C8C8C;margin-top:3px;">
              Case {_safe(d["case_id"])} | analyzed {_safe(_fmt_dt(d["analyzed_at"]))}
            </div>
          </div>
          <span class="badge badge-ip">{_safe(target_label)}</span>
          <span class="badge badge-org">{_safe(target_sub) if target_sub else "ACTIVE"}</span>
          <span class="badge badge-threat" style="color:{rc};border:1px solid {rc}40;">{risk_label} {risk}/100</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    _metric_row()


def _risk_gauge() -> go.Figure:
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=risk,
            title={"text": "Risk", "font": {"size": 12, "color": "#8C8C8C"}},
            number={"font": {"size": 34, "color": rc}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "#2A2A2A"},
                "bar": {"color": rc, "thickness": 0.25},
                "bgcolor": "#1C1C1C",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 40], "color": "#152014"},
                    {"range": [40, 70], "color": "#1e1a10"},
                    {"range": [70, 100], "color": "#201212"},
                ],
            },
        )
    )
    themed(fig, height=235)
    fig.update_layout(margin=dict(l=15, r=15, t=35, b=5))
    return fig


def _source_bar() -> go.Figure | None:
    if wdf.empty or "category" not in wdf:
        return None
    src = wdf["category"].value_counts()
    fig = go.Figure(
        go.Bar(
            x=src.index,
            y=src.values,
            marker=dict(color=["#0B88F8", "#F5A623", "#23D18B", "#9B59B6"][: len(src)]),
            text=src.values,
            textposition="outside",
            textfont=dict(color="#F0F0F0", size=10),
        )
    )
    themed(fig, "Intel Items by Source", height=250)
    fig.update_layout(xaxis_title="", yaxis_title="", showlegend=False)
    return fig


def _activity_heatmap() -> go.Figure:
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    hourly = adf.groupby(["weekday", "hour"])["duration_min"].sum().reset_index()
    hourly["weekday"] = pd.Categorical(hourly["weekday"], categories=day_order, ordered=True)
    pivot = hourly.sort_values("weekday").pivot_table(
        index="weekday", columns="hour", values="duration_min", fill_value=0
    )
    fig = go.Figure(
        go.Heatmap(
            z=pivot.values,
            x=pivot.columns.tolist(),
            y=pivot.index.tolist(),
            colorscale=[[0, "#0F0F0F"], [0.45, "#1f3a5f"], [1, "#0B88F8"]],
            hovertemplate="Day: %{y}<br>Hour: %{x}:00<br>Minutes: %{z:.0f}<extra></extra>",
        )
    )
    themed(fig, "Activity Heatmap", height=310)
    fig.update_layout(xaxis=dict(title="", dtick=3), yaxis=dict(title=""))
    return fig


def _zone_time_bar() -> go.Figure:
    zone_t = clust.groupby("zone_label")["duration_min"].sum().reset_index()
    zone_t["hours"] = zone_t["duration_min"] / 60
    fig = go.Figure(
        go.Bar(
            x=zone_t["zone_label"],
            y=zone_t["hours"],
            marker_color=["#0B88F8", "#F5A623", "#F14C4C", "#8C8C8C"][: len(zone_t)],
            text=[f"{v:.1f}h" for v in zone_t["hours"]],
            textposition="outside",
            textfont=dict(color="#F0F0F0", size=10),
        )
    )
    themed(fig, "Time by Zone", height=260)
    fig.update_layout(xaxis_title="", yaxis_title="Hours", showlegend=False)
    return fig


def _topic_scatter() -> go.Figure | None:
    if wdf.empty or "px" not in wdf or "py" not in wdf:
        return None
    fig = px.scatter(
        wdf,
        x="px",
        y="py",
        color="topic_label" if "topic_label" in wdf else "category",
        symbol="category" if "category" in wdf else None,
        hover_data={"title": True, "category": True, "px": False, "py": False},
        color_discrete_sequence=px.colors.qualitative.Bold,
    )
    fig.update_traces(marker=dict(size=8, opacity=0.85, line=dict(color="#0F0F0F", width=0.7)))
    themed(fig, "Topic Map", height=320)
    fig.update_layout(xaxis=dict(showticklabels=False), yaxis=dict(showticklabels=False))
    return fig


def _centrality_bar() -> go.Figure | None:
    if graph.number_of_nodes() == 0:
        return None
    centrality = nx.degree_centrality(graph)
    top = sorted(centrality, key=centrality.get, reverse=True)[:10]
    rows = pd.DataFrame(
        {
            "Node": [str(n)[:32] for n in top],
            "Centrality": [centrality[n] for n in top],
            "Type": [graph.nodes[n].get("type", "?") for n in top],
        }
    )
    fig = go.Figure(
        go.Bar(
            x=rows["Centrality"],
            y=rows["Node"],
            orientation="h",
            marker_color="#0B88F8",
            text=rows["Type"],
            textposition="outside",
            textfont=dict(color="#8C8C8C", size=9),
        )
    )
    themed(fig, "Top Connected Entities", height=300)
    fig.update_layout(yaxis=dict(categoryorder="total ascending"), xaxis_title="")
    return fig


def _fingerprint_radar(fp: dict) -> go.Figure:
    labels = [label.replace("_", " ").title() for label in fp["labels"]]
    vals = fp["values"]
    fig = go.Figure(
        go.Scatterpolar(
            r=vals + [vals[0]],
            theta=labels + [labels[0]],
            fill="toself",
            name=target_label,
            line=dict(color="#0B88F8", width=2),
            fillcolor="rgba(11,136,248,0.15)",
        )
    )
    themed(fig, "Behavioral Fingerprint", height=360)
    fig.update_layout(
        polar=dict(
            bgcolor="#1C1C1C",
            radialaxis=dict(color="#444444", gridcolor="#2A2A2A", range=[0, 1]),
            angularaxis=dict(color="#8C8C8C", gridcolor="#2A2A2A", tickfont=dict(size=8)),
        )
    )
    return fig


def _build_report_md() -> str:
    anom_n = int(adf["anomaly"].sum())
    total_h = round(adf["duration_min"].sum() / 60, 1)
    peak_h = int(adf.groupby("hour")["duration_min"].sum().idxmax())
    peak_d = adf.groupby("weekday")["duration_min"].sum().idxmax()
    pred_str = f"{pred['city']}, {pred['country']} ({pred['confidence']}%)" if pred else "Undetermined"
    zone_rows = "\n".join(
        f"- {r['label']}: {r['city']}, {r['sessions']} sessions, {r['total_hours']}h, {r['likelihood_pct']}%"
        for _, r in valid.iterrows()
    )
    factor_rows = "\n".join(f"- [{kind.upper()}] {msg}" for msg, kind in factors)
    source_rows = (
        "\n".join(f"- {cat}: {cnt}" for cat, cnt in wdf["category"].value_counts().items())
        if not wdf.empty and "category" in wdf
        else "- No intel items"
    )
    return f"""# ARGUS Intelligence Report - {d['case_id']}

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
Target: {target_label} {f'({d["target_ip"]})' if target_domain else ''}
Risk: {risk_label} ({risk}/100)

## Target Profile
- Location: {bg.get('city', '?')}, {bg.get('regionName') or bg.get('region', '?')}, {bg.get('country', '?')}
- ISP: {bg.get('isp', 'N/A')}
- Organisation: {bg.get('org', 'N/A')}
- Timezone: {bg.get('timezone', 'N/A')}
- Coordinates: {bg.get('lat', '?')}, {bg.get('lon', '?')}

## Case Summary
- Sessions: {len(adf)}
- Active time: {total_h}h
- Zones: {len(valid)}
- Intel items: {len(wdf)}
- Entities: {len(ents)}
- Anomalies: {anom_n}
- Peak behavior: {peak_d} at {peak_h:02d}:00
- Predicted location: {pred_str}

## Activity Zones
{zone_rows or '- No clustered zones'}

## Intel Sources
{source_rows}

## Risk Factors
{factor_rows}
"""


_render_case_header()

tab_command, tab_geo, tab_intel, tab_predictive, tab_report = st.tabs(
    ["Command", "Geo + Activity", "Intel + Graph", "Predictive + Identity", "Report"]
)

with tab_command:
    left, mid, right = st.columns([1.05, 1.1, 1], gap="medium")

    with left:
        st.plotly_chart(_risk_gauge(), use_container_width=True, key="dash_risk_gauge")
        st.markdown('<div class="section-hdr">Risk Factors</div>', unsafe_allow_html=True)
        for msg, kind in factors:
            color = {"alert": "#F14C4C", "warn": "#F5A623", "safe": "#23D18B"}.get(kind, "#8C8C8C")
            dot = {"alert": "dot-alert", "warn": "dot-warn", "safe": "dot-live"}.get(kind, "dot-dead")
            st.markdown(
                f'<div class="entity-row"><span class="dot {dot}"></span>'
                f'<span style="color:{color};font-size:.8rem;">{_safe(msg)}</span></div>',
                unsafe_allow_html=True,
            )

    with mid:
        st.markdown(
            f"""
            <div class="pal-card pal-card-accent">
              <div class="section-hdr">Target Profile</div>
              <div class="entity-row"><span class="badge badge-ip">TARGET</span>{_safe(target_label)}</div>
              {"<div class='entity-row'><span class='badge badge-org'>IP</span>" + _safe(d["target_ip"]) + "</div>" if target_sub else ""}
              <div class="entity-row"><span class="badge badge-loc">CITY</span>{_safe(bg.get("city"))}, {_safe(bg.get("regionName") or bg.get("region"))}</div>
              <div class="entity-row"><span class="badge badge-loc">COUNTRY</span>{_safe(bg.get("country"))}</div>
              <div class="entity-row"><span class="badge badge-org">ISP</span>{_safe(bg.get("isp"))}</div>
              <div class="entity-row"><span class="badge badge-zone">AS</span>{_safe(bg.get("as"))}</div>
              <div class="entity-row"><span class="badge badge-zone">LAT/LON</span>{_safe(bg.get("lat"))} / {_safe(bg.get("lon"))}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if pred:
            conf_c = risk_color(100 - pred["confidence"])
            st.markdown(
                f"""
                <div class="pal-card pal-card-green">
                  <div class="section-hdr">Most Likely Current Location</div>
                  <div style="font-size:1.3rem;font-weight:700;color:#F0F0F0;">{_safe(pred["city"])}</div>
                  <div style="font-size:.76rem;color:#8C8C8C;">{_safe(pred["country"])} | {_safe(pred["zone"])}</div>
                  <div style="font-family:JetBrains Mono,monospace;font-size:.78rem;color:#0B88F8;margin-top:8px;">
                    {_safe(pred["lat"])} / {_safe(pred["lon"])}
                  </div>
                  <div style="margin-top:10px;">
                    <div class="risk-bar-bg"><div class="risk-bar" style="width:{pred["confidence"]}%;background:{conf_c};"></div></div>
                    <div style="font-size:.7rem;color:{conf_c};margin-top:3px;">Confidence: {pred["confidence"]}%</div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with right:
        st.markdown('<div class="section-hdr">Operations</div>', unsafe_allow_html=True)
        st.page_link("pages/10_Operations.py", label="Open Operations Center")

        fp_now = build_fingerprint(adf, stats)
        try:
            saved_cases = load_watchlist()
            alerts = alerts_for(d, fp_now, sim_threshold=0.85, risk_threshold=70)
        except Exception:
            saved_cases, alerts = [], []
        st.markdown(
            f"""
            <div class="pal-card">
              <div class="entity-row"><span class="badge badge-org">SAVED</span>{len(saved_cases)} watchlist cases</div>
              <div class="entity-row"><span class="badge badge-threat">ALERTS</span>{len(alerts)} active alerts</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if alerts:
            for alert in alerts[:4]:
                kind = "threat" if alert.get("severity") == "high" else "zone"
                st.markdown(
                    f'<div class="entity-row"><span class="badge badge-{kind}">{_safe(alert.get("kind"))}</span>'
                    f'<span style="font-size:.78rem;color:#F0F0F0;">{_safe(alert.get("summary"))}</span></div>',
                    unsafe_allow_html=True,
                )

        src_fig = _source_bar()
        if src_fig:
            st.plotly_chart(src_fig, use_container_width=True, key="dash_source_bar")

with tab_geo:
    geo_left, geo_right = st.columns([1.25, 1], gap="medium")

    with geo_left:
        if not clust.empty:
            fig_map = px.scatter_mapbox(
                clust,
                lat="lat",
                lon="lon",
                color="zone_label",
                size="duration_min",
                hover_data={"city": True, "duration_min": True, "timestamp": True, "lat": False, "lon": False},
                mapbox_style="carto-darkmatter",
                zoom=8,
                center={"lat": bg["lat"], "lon": bg["lon"]},
                color_discrete_sequence=["#0B88F8", "#F5A623", "#F14C4C", "#8C8C8C"],
            )
            themed(fig_map, "Session Geography", height=470)
            fig_map.update_layout(margin=dict(l=0, r=0, t=42, b=0), legend=dict(orientation="h", y=-0.1))
            st.plotly_chart(fig_map, use_container_width=True, key="dash_geo_map")

    with geo_right:
        st.plotly_chart(_activity_heatmap(), use_container_width=True, key="dash_activity_heatmap")
        st.plotly_chart(_zone_time_bar(), use_container_width=True, key="dash_zone_time")

    st.markdown('<div class="section-hdr">Activity Zones</div>', unsafe_allow_html=True)
    zone_cols = ["label", "city", "zone_type", "sessions", "total_hours", "active_window", "last_seen", "likelihood_pct"]
    zone_cols = [c for c in zone_cols if c in valid.columns]
    st.dataframe(valid[zone_cols], use_container_width=True, hide_index=True)

with tab_intel:
    intel_left, intel_right = st.columns([1.15, 1], gap="medium")

    with intel_left:
        fig_topic = _topic_scatter()
        if fig_topic:
            st.plotly_chart(fig_topic, use_container_width=True, key="dash_topic_scatter")
        else:
            st.info("No clustered web intelligence is available for this case.")

        st.markdown('<div class="section-hdr">Recent Intel Items</div>', unsafe_allow_html=True)
        if not wdf.empty:
            show_cols = [c for c in ["title", "category", "source", "topic_label", "url"] if c in wdf.columns]
            st.dataframe(wdf[show_cols].head(20), use_container_width=True, hide_index=True)
        else:
            st.caption("No intel items were fetched.")

    with intel_right:
        fig_cent = _centrality_bar()
        if fig_cent:
            st.plotly_chart(fig_cent, use_container_width=True, key="dash_centrality")

        st.markdown('<div class="section-hdr">Entity Roster</div>', unsafe_allow_html=True)
        ent_df = pd.DataFrame(
            [(e["type"], e["value"][:48], f"{e['confidence'] * 100:.0f}%", e.get("source", "")) for e in ents],
            columns=["Type", "Value", "Confidence", "Source"],
        )
        st.dataframe(ent_df.head(25), use_container_width=True, hide_index=True)

with tab_predictive:
    fp = build_fingerprint(adf, stats)
    next_window = predict_next_window(adf)
    forecast = forecast_activity(adf)
    drift = detect_drift(adf)
    ci = detect_counter_intel(adf, bg)

    p1, p2, p3 = st.columns(3, gap="medium")
    with p1:
        conf = min(next_window["confidence"], 100)
        conf_c = risk_color(100 - conf)
        st.markdown(
            f"""
            <div class="pal-card pal-card-accent">
              <div class="section-hdr">Next Active Window</div>
              <div style="font-size:1.35rem;font-weight:700;color:#0B88F8;">{_safe(next_window["peak_day"])}</div>
              <div style="font-size:1rem;color:#F0F0F0;">{next_window["peak_hour"]:02d}:00 - {(next_window["peak_hour"] + 2) % 24:02d}:00</div>
              <div style="font-size:.72rem;color:#8C8C8C;margin-top:6px;">{next_window["hours_until"]}h from now</div>
              <div style="margin-top:10px;"><div class="risk-bar-bg"><div class="risk-bar" style="width:{conf}%;background:{conf_c};"></div></div></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with p2:
        drift_c = risk_color(drift["drift_score"])
        st.markdown(
            f"""
            <div class="pal-card">
              <div class="section-hdr">Behavior Drift</div>
              <div style="font-size:1.7rem;font-weight:700;color:{drift_c};">{drift["drift_score"]}/100</div>
              <div style="font-size:.78rem;color:#8C8C8C;">{"Drift detected" if drift["drift_detected"] else "Stable pattern"}</div>
              <div style="font-size:.7rem;color:#444444;margin-top:6px;">{_safe(drift.get("early_period"))} -> {_safe(drift.get("recent_period"))}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with p3:
        ci_c = {"HIGH": "#F14C4C", "MEDIUM": "#F5A623", "LOW": "#23D18B"}.get(ci["ci_level"], "#8C8C8C")
        st.markdown(
            f"""
            <div class="pal-card">
              <div class="section-hdr">Counter-Intel Risk</div>
              <div style="font-size:1.7rem;font-weight:700;color:{ci_c};">{ci["ci_score"]}/100</div>
              <div style="font-size:.78rem;color:{ci_c};">{_safe(ci["ci_level"])}</div>
              <div style="font-size:.7rem;color:#8C8C8C;margin-top:6px;">{len(ci["signals"])} signals evaluated</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    pred_left, pred_right = st.columns([1.15, 1], gap="medium")
    with pred_left:
        if not forecast.empty:
            historical = forecast[~forecast["is_forecast"]]
            predicted = forecast[forecast["is_forecast"]]
            fig_fc = go.Figure()
            fig_fc.add_trace(
                go.Scatter(
                    x=historical["date"].astype(str),
                    y=historical["forecast_hours"],
                    mode="lines+markers",
                    name="History",
                    line=dict(color="#0B88F8"),
                )
            )
            fig_fc.add_trace(
                go.Scatter(
                    x=predicted["date"].astype(str),
                    y=predicted["forecast_hours"],
                    mode="lines+markers",
                    name="Forecast",
                    line=dict(color="#23D18B", dash="dash"),
                )
            )
            themed(fig_fc, "7-Day Activity Forecast", height=340)
            fig_fc.update_layout(xaxis_title="", yaxis_title="Hours")
            st.plotly_chart(fig_fc, use_container_width=True, key="dash_forecast")
        else:
            st.info("Not enough activity history for the 7-day forecast.")

        st.markdown('<div class="section-hdr">Signals</div>', unsafe_allow_html=True)
        for msg, level in ci["signals"][:5]:
            badge_kind = "threat" if level in ["critical", "high"] else "zone" if level == "medium" else "safe"
            st.markdown(
                f'<div class="entity-row"><span class="badge badge-{badge_kind}">{_safe(level)}</span>'
                f'<span style="font-size:.8rem;color:#F0F0F0;">{_safe(msg)}</span></div>',
                unsafe_allow_html=True,
            )
        for change in drift.get("changes", [])[:4]:
            st.markdown(
                f'<div class="entity-row"><span class="badge badge-zone">DRIFT</span>'
                f'<span style="font-size:.8rem;color:#F0F0F0;">{_safe(change)}</span></div>',
                unsafe_allow_html=True,
            )

    with pred_right:
        st.plotly_chart(_fingerprint_radar(fp), use_container_width=True, key="dash_fp")
        fp_hash = hex(hash(tuple(round(v, 3) for v in fp["values"])) & 0xFFFFFFFF)[2:].upper().zfill(8)
        st.markdown(
            f"""
            <div class="pal-card">
              <div class="entity-row"><span class="badge badge-ip">HASH</span>FP-{fp_hash}</div>
              <div class="entity-row"><span class="badge badge-zone">PEAK</span>{fp["peak_day"]} {fp["peak_hour"]:02d}:00</div>
              <div class="entity-row"><span class="badge badge-threat">REMOTE</span>{fp["remote_pct"] * 100:.1f}%</div>
              <div class="entity-row"><span class="badge badge-threat">ANOMALY</span>{fp["anom_rate"] * 100:.1f}%</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

with tab_report:
    report_md = _build_report_md()
    rep_left, rep_right = st.columns([1.4, 1], gap="medium")
    with rep_left:
        st.markdown(report_md)
    with rep_right:
        st.markdown('<div class="section-hdr">Exports + Drilldowns</div>', unsafe_allow_html=True)
        st.download_button(
            "Download Report (.md)",
            data=report_md.encode("utf-8"),
            file_name=f"{d['case_id']}_report.md",
            mime="text/markdown",
            use_container_width=True,
        )
        st.download_button(
            "Download Entities (.csv)",
            data=ent_df.to_csv(index=False).encode("utf-8") if "ent_df" in globals() else b"",
            file_name=f"{d['case_id']}_entities.csv",
            mime="text/csv",
            use_container_width=True,
        )
        st.page_link("pages/10_Operations.py", label="Operations Center")
        st.markdown('<div class="section-hdr">Specialist Views</div>', unsafe_allow_html=True)
        st.page_link("pages/2_Geo_Intelligence.py", label="Geo Intelligence")
        st.page_link("pages/3_Link_Analysis.py", label="Link Analysis")
        st.page_link("pages/4_Pattern_of_Life.py", label="Pattern of Life")
        st.page_link("pages/5_Intel_Feed.py", label="Intel Feed")
        st.page_link("pages/8_Predictive.py", label="Predictive")
        st.page_link("pages/9_Fingerprint.py", label="Fingerprint")
