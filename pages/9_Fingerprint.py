"""
Behavioral Identity Fingerprint — beyond Palantir.
Creates a 12-dimensional behavioral signature that persists across IPs.
The same behavioral fingerprint = likely the same person, even on a different IP.
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from core.state import inject_theme, require_data, themed, risk_color
from core.predictor import build_fingerprint

st.set_page_config(page_title="Fingerprint · Mini Palantir", page_icon="🧬", layout="wide")
inject_theme()
d = require_data()

adf   = d["anomaly_df"]
stats = d["cluster_stats"]
bg    = d["base_geo"]

st.markdown(
    '<div style="font-size:1.1rem;font-weight:600;color:#d4dce8;margin-bottom:3px;">Behavioral Fingerprint</div>'
    '<div style="font-size:.75rem;color:#6b7685;margin-bottom:18px;">'
    '12-dimensional behavioral identity signature · Cross-IP matching</div>',
    unsafe_allow_html=True,
)

# ── Build fingerprint ──────────────────────────────────────────────────────────
fp = build_fingerprint(adf, stats)

FEATURE_LABELS = {
    "peak_hour":       "Peak Hour (normalized)",
    "peak_day":        "Peak Day (normalized)",
    "primary_zone":    "Primary Zone Usage",
    "secondary_zone":  "Secondary Zone Usage",
    "remote_zone":     "Remote Zone Usage",
    "avg_duration":    "Avg Session Length",
    "duration_spread": "Duration Variance",
    "night_activity":  "Night Activity (01-04h)",
    "weekend_activity":"Weekend Activity",
    "anomaly_rate":    "Anomaly Rate",
    "session_density": "Sessions Per Day",
    "zone_diversity":  "Zone Diversity",
}

tab_print, tab_compare, tab_decode = st.tabs([
    "Identity Fingerprint", "Compare Targets", "Fingerprint Decoder"
])

# ══════════════════════════════════════════════════════════════════
# TAB 1 — FINGERPRINT
# ══════════════════════════════════════════════════════════════════
with tab_print:
    col_radar, col_profile = st.columns([2, 1])

    with col_radar:
        labels = [FEATURE_LABELS.get(k, k) for k in fp["labels"]]
        vals   = fp["values"]

        fig_fp = go.Figure()
        fig_fp.add_trace(go.Scatterpolar(
            r=vals + [vals[0]],
            theta=labels + [labels[0]],
            fill="toself",
            name=d["target_ip"],
            line=dict(color="#58a6ff", width=2),
            fillcolor="rgba(88,166,255,0.15)",
            marker=dict(size=6, color="#58a6ff"),
        ))
        themed(fig_fp, f"Behavioral Fingerprint — {d['target_ip']}", height=520)
        fig_fp.update_layout(
            polar=dict(
                bgcolor="#161b22",
                radialaxis=dict(
                    color="#484f58", gridcolor="#21262d",
                    range=[0, 1], tickfont=dict(size=8),
                ),
                angularaxis=dict(
                    color="#8b949e", gridcolor="#21262d",
                    tickfont=dict(size=9),
                ),
            ),
            showlegend=True,
            legend=dict(x=0.85, y=1.1),
        )
        st.plotly_chart(fig_fp, use_container_width=True)

    with col_profile:
        st.markdown(
            f'<div class="pal-card pal-card-accent">'
            f'<div class="section-hdr">Identity Signature</div>'
            f'<div class="entity-row"><span class="badge badge-ip">IP</span>{d["target_ip"]}</div>'
            f'<div class="entity-row"><span class="badge badge-loc">CITY</span>{bg.get("city","?")}</div>'
            f'<div class="entity-row"><span class="badge badge-org">ISP</span>{bg.get("isp","?")[:30]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        st.markdown('<div class="section-hdr" style="margin-top:16px">Dimension Values</div>',
                    unsafe_allow_html=True)
        for key, label in FEATURE_LABELS.items():
            val = fp["features"].get(key, 0)
            bar_color = "#58a6ff" if val < 0.5 else "#d29922" if val < 0.8 else "#f85149"
            bar_w = int(val * 100)
            st.markdown(
                f'<div style="margin-bottom:8px;">'
                f'<div style="display:flex;justify-content:space-between;font-size:.72rem;color:#8b949e;margin-bottom:3px;">'
                f'<span>{label}</span><span style="color:#e6edf3">{val:.3f}</span>'
                f'</div>'
                f'<div class="risk-bar-bg"><div class="risk-bar" style="width:{bar_w}%;background:{bar_color}"></div></div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # Fingerprint hash (deterministic from feature values)
        fp_hash = hex(hash(tuple(round(v, 3) for v in fp["values"])) & 0xFFFFFFFF)[2:].upper().zfill(8)
        st.markdown(
            f'<div class="pal-card" style="margin-top:12px;padding:10px 14px;">'
            f'<div class="section-hdr">Fingerprint Hash</div>'
            f'<div style="font-family:monospace;font-size:1.1rem;color:#58a6ff;letter-spacing:.1em">'
            f'FP-{fp_hash}</div>'
            f'<div style="font-size:.7rem;color:#484f58;margin-top:4px;">'
            f'Use this hash to match against other targets</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

# ══════════════════════════════════════════════════════════════════
# TAB 2 — COMPARE TARGETS
# ══════════════════════════════════════════════════════════════════
with tab_compare:
    st.markdown(
        '<div style="font-size:.82rem;color:#8b949e;margin-bottom:16px;">'
        'Simulate a second target by entering custom behavioral parameters, '
        'then compare fingerprints to assess if they may be the same individual.'
        '</div>',
        unsafe_allow_html=True,
    )

    col_ctrl, col_graph = st.columns([1, 2])

    with col_ctrl:
        st.markdown('<div class="section-hdr">Simulated Target 2 Profile</div>',
                    unsafe_allow_html=True)
        t2_vals = {}
        defaults = fp["features"]
        for key, label in FEATURE_LABELS.items():
            default_v = round(defaults.get(key, 0.5), 2)
            # Add small noise for visual difference
            noise = np.random.uniform(-0.15, 0.15)
            default_v = max(0.0, min(1.0, default_v + noise))
            t2_vals[key] = st.slider(
                label[:30], 0.0, 1.0, float(round(default_v, 2)),
                step=0.01, key=f"t2_{key}",
            )

    with col_graph:
        t1_vals = fp["values"]
        t2_list = [t2_vals[k] for k in fp["labels"]]
        labels  = [FEATURE_LABELS.get(k, k) for k in fp["labels"]]

        fig_cmp = go.Figure()
        for vals_list, name, color, fill in [
            (t1_vals, d["target_ip"], "#58a6ff", "rgba(88,166,255,0.12)"),
            (t2_list, "Target 2 (simulated)", "#f85149", "rgba(248,81,73,0.12)"),
        ]:
            fig_cmp.add_trace(go.Scatterpolar(
                r=vals_list + [vals_list[0]],
                theta=labels + [labels[0]],
                fill="toself", name=name,
                line=dict(color=color, width=2),
                fillcolor=fill,
                marker=dict(size=5, color=color),
            ))
        themed(fig_cmp, "Fingerprint Comparison", height=500)
        fig_cmp.update_layout(polar=dict(
            bgcolor="#161b22",
            radialaxis=dict(color="#484f58", gridcolor="#21262d", range=[0,1]),
            angularaxis=dict(color="#8b949e", gridcolor="#21262d", tickfont=dict(size=8)),
        ))
        st.plotly_chart(fig_cmp, use_container_width=True)

        # Similarity score
        t1_arr = np.array(t1_vals)
        t2_arr = np.array(t2_list)
        cosine_sim = float(np.dot(t1_arr, t2_arr) / (np.linalg.norm(t1_arr) * np.linalg.norm(t2_arr) + 1e-10))
        euclidean  = float(np.linalg.norm(t1_arr - t2_arr))
        similarity = round(cosine_sim * 100, 1)
        match_label = "LIKELY SAME INDIVIDUAL" if similarity > 85 else "POSSIBLE MATCH" if similarity > 70 else "DIFFERENT INDIVIDUALS"
        match_color = "#f85149" if similarity > 85 else "#d29922" if similarity > 70 else "#3fb950"

        st.markdown(
            f'<div class="pal-card" style="border-left:4px solid {match_color};margin-top:8px;">'
            f'<div style="display:flex;align-items:center;gap:16px;">'
            f'<div style="font-size:2rem;font-weight:700;color:{match_color}">{similarity}%</div>'
            f'<div>'
            f'<div style="font-size:.9rem;font-weight:700;color:{match_color}">{match_label}</div>'
            f'<div style="font-size:.72rem;color:#8b949e;">Cosine similarity · Euclidean distance: {euclidean:.3f}</div>'
            f'</div></div></div>',
            unsafe_allow_html=True,
        )

# ══════════════════════════════════════════════════════════════════
# TAB 3 — FINGERPRINT DECODER
# ══════════════════════════════════════════════════════════════════
with tab_decode:
    st.markdown('<div class="section-hdr">What Does This Fingerprint Tell Us?</div>',
                unsafe_allow_html=True)

    # Interpret each dimension
    interpretations = []
    f = fp["features"]

    peak_h = fp["peak_hour"]
    if 6 <= peak_h <= 10:
        interpretations.append(("Early bird — active mornings (06:00–10:00)", "loc"))
    elif 9 <= peak_h <= 17:
        interpretations.append(("Business hours user — peak 09:00–17:00 suggests office worker", "loc"))
    elif 18 <= peak_h <= 22:
        interpretations.append(("Evening user — active after work hours", "zone"))
    else:
        interpretations.append(("Night owl — active 22:00+ or early morning", "threat"))

    if fp["night_pct"] > 0.15:
        interpretations.append((f"High night-time activity ({fp['night_pct']*100:.0f}%) — unusual, possible shift worker or international actor", "threat"))

    if f["weekend_activity"] > 0.45:
        interpretations.append(("Heavy weekend user — recreational or personal use dominant", "wiki"))
    elif f["weekend_activity"] < 0.15:
        interpretations.append(("Weekday-only pattern — strongly suggests professional/work usage", "org"))

    if fp["remote_pct"] > 0.2:
        interpretations.append((f"High remote zone activity ({fp['remote_pct']*100:.0f}%) — frequent travel, VPN use, or distributed operations", "threat"))

    if f["avg_duration"] > 0.5:
        interpretations.append(("Long session durations — suggests sustained engagement, possibly automated or always-on", "zone"))
    elif f["avg_duration"] < 0.15:
        interpretations.append(("Short bursts — hit-and-run pattern, possibly operational security aware", "threat"))

    if f["zone_diversity"] > 0.6:
        interpretations.append(("High zone diversity — target is highly mobile or uses multiple connection points", "reddit"))
    elif f["zone_diversity"] < 0.2:
        interpretations.append(("Low zone diversity — target is very geographically stable and predictable", "loc"))

    if fp["anom_rate"] > 0.2:
        interpretations.append((f"High anomaly rate ({fp['anom_rate']*100:.0f}%) — behavior is erratic or deliberately unpredictable", "threat"))

    for msg, kind in interpretations:
        st.markdown(
            f'<div class="entity-row">'
            f'<span class="badge badge-{kind}">→</span>'
            f'<span style="font-size:.85rem;color:#e6edf3">{msg}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Bar chart of all dimensions
    labels  = [FEATURE_LABELS.get(k, k) for k in fp["labels"]]
    values  = fp["values"]
    colors  = ["#f85149" if v > 0.75 else "#d29922" if v > 0.4 else "#58a6ff" for v in values]

    fig_bar = go.Figure(go.Bar(
        x=values, y=labels, orientation="h",
        marker=dict(color=colors, line=dict(color="#0d1117", width=0.5)),
        text=[f"{v:.3f}" for v in values],
        textposition="outside",
        textfont=dict(color="#e6edf3", size=9),
    ))
    themed(fig_bar, "Fingerprint Dimension Values (0 = min, 1 = max)", height=420)
    fig_bar.update_layout(
        xaxis=dict(range=[0, 1.15], title="Normalized Value"),
        yaxis=dict(title="", categoryorder="array", categoryarray=labels[::-1]),
        showlegend=False,
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown(
        '<div class="pal-card pal-card-accent" style="margin-top:8px">'
        '<div class="section-hdr">Why Behavioral Fingerprinting Works</div>'
        '<div style="font-size:.82rem;color:#e6edf3;line-height:1.6;">'
        'Every person has consistent behavioral patterns — when they work, how long sessions run, '
        'how mobile they are, whether they work weekends. These patterns persist even when:<br><br>'
        '• The IP address changes (ISP rotation, VPN)<br>'
        '• The device changes<br>'
        '• The user switches networks<br><br>'
        'A cosine similarity above <b style="color:#d29922">85%</b> between two fingerprints is a '
        'strong indicator of the same individual. This is a capability not offered in Palantir\'s '
        'standard platform.'
        '</div></div>',
        unsafe_allow_html=True,
    )
