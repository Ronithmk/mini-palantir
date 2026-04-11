"""Geo Intelligence — interactive map, movement trail, zone analysis."""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium
from core.state import inject_theme, require_data, themed, MAPBOX

st.set_page_config(page_title="Geo Intelligence · Mini Palantir", page_icon="🗺️", layout="wide")
inject_theme()
d = require_data()

bg     = d["base_geo"]
clust  = d["clustered_df"]
stats  = d["cluster_stats"]
pred   = d["prediction"]
anomdf = d["anomaly_df"]

st.markdown(
    '<div style="font-size:1.5rem;font-weight:700;color:#58a6ff;margin-bottom:4px;">🗺️ GEO INTELLIGENCE</div>'
    f'<div style="font-size:.75rem;color:#8b949e;margin-bottom:20px;">'
    f'Target: {d["target_ip"]}  ·  Base: {bg.get("city")}, {bg.get("country")}  ·  {stats[stats["cluster_id"]!=-1]["cluster_id"].nunique()} zones</div>',
    unsafe_allow_html=True,
)

tab_map, tab_scatter, tab_zones, tab_anomaly = st.tabs([
    "Interactive Map", "Session Scatter", "Zone Analysis", "Anomalies"
])

# ── Build folium map once, cache in session ────────────────────────────────────
if d["folium_map"] is None:
    center = [clust["lat"].mean(), clust["lon"].mean()]
    m = folium.Map(location=center, zoom_start=10, tiles="CartoDB dark_matter")

    ZONE_COLORS = {"Primary Zone": "blue", "Secondary Zone": "orange",
                   "Travel / Remote": "red", "Noise": "gray"}

    # Cluster zone circles
    for _, row in stats[stats["cluster_id"] != -1].iterrows():
        folium.CircleMarker(
            location=[row["centroid_lat"], row["centroid_lon"]],
            radius=max(10, min(50, row["sessions"] / 2.5)),
            color="#58a6ff", fill=True, fill_opacity=0.35,
            popup=folium.Popup(
                f"<b style='color:#58a6ff'>{row['label']}</b><br>"
                f"City: {row['city']}<br>"
                f"Sessions: {row['sessions']}<br>"
                f"Total: {row['total_hours']}h<br>"
                f"Likelihood: <b>{row['likelihood_pct']}%</b><br>"
                f"<small>{row['centroid_lat']}, {row['centroid_lon']}</small>",
                max_width=230,
            ),
            tooltip=f"{row['label']} — {row['likelihood_pct']}% confidence",
        ).add_to(m)

    # Session dots (fixed seed)
    sample = clust.sample(min(400, len(clust)), random_state=42)
    for _, row in sample.iterrows():
        color = ZONE_COLORS.get(row["zone_label"], "gray")
        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=2.5, color=color, fill=True, fill_opacity=0.5,
            tooltip=f"{row['zone_label']} · {row['duration_min']}min",
        ).add_to(m)

    # Movement trail (last 20 sessions chronologically)
    trail = clust.sort_values("timestamp").tail(20)
    trail_coords = trail[["lat", "lon"]].values.tolist()
    if len(trail_coords) > 1:
        folium.PolyLine(
            trail_coords, color="#d29922", weight=2, opacity=0.7, dash_array="5 5",
            tooltip="Recent movement trail",
        ).add_to(m)

    # Anomaly markers
    anoms = anomdf[anomdf["anomaly"]].head(30)
    for _, row in anoms.iterrows():
        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=5, color="#f85149", fill=True, fill_opacity=0.8,
            tooltip=f"⚠ Anomaly: {row['anomaly_reason'].strip()}",
        ).add_to(m)

    # Predicted location
    if pred:
        folium.Marker(
            location=[pred["lat"], pred["lon"]],
            popup=f"Predicted Location: {pred['city']} ({pred['confidence']}%)",
            tooltip=f"Predicted: {pred['city']}",
            icon=folium.Icon(color="green", icon="home", prefix="fa"),
        ).add_to(m)

    # Legend
    legend = """
    <div style='position:fixed;bottom:30px;left:30px;z-index:9999;
         background:#161b22;border:1px solid #30363d;border-radius:8px;padding:12px;
         font-family:monospace;font-size:11px;color:#e6edf3;'>
    <b style='color:#58a6ff;'>LEGEND</b><br>
    <span style='color:#58a6ff'>●</span> Zone centroid<br>
    <span style='color:blue'>●</span> Primary zone session<br>
    <span style='color:orange'>●</span> Secondary zone<br>
    <span style='color:red'>●</span> Remote / anomaly<br>
    <span style='color:#d29922'>- -</span> Movement trail<br>
    <span style='color:#3fb950'>⌂</span> Predicted location
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend))

    d["folium_map"] = m

with tab_map:
    col_fmap, col_zinfo = st.columns([3, 1])
    with col_fmap:
        st_folium(d["folium_map"], height=560, returned_objects=[], key="geo_map")
    with col_zinfo:
        st.markdown('<div class="section-hdr">Zone Summary</div>', unsafe_allow_html=True)
        for _, row in stats[stats["cluster_id"] != -1].iterrows():
            bar_w = int(row["likelihood_pct"])
            rc    = "#3fb950" if row["likelihood_pct"] > 60 else "#d29922" if row["likelihood_pct"] > 30 else "#f85149"
            st.markdown(
                f'<div class="pal-card" style="padding:10px 14px;margin-bottom:8px;">'
                f'<b style="color:#58a6ff">{row["label"]}</b><br>'
                f'<span style="font-size:.75rem;color:#8b949e">{row["city"]}</span><br>'
                f'<span style="font-family:monospace;font-size:.7rem;color:#484f58">'
                f'{row["centroid_lat"]}, {row["centroid_lon"]}</span><br>'
                f'<div style="margin-top:6px;">'
                f'<div class="risk-bar-bg"><div class="risk-bar" style="width:{bar_w}%;background:{rc}"></div></div>'
                f'</div>'
                f'<span style="font-size:.7rem;color:{rc}"><b>{row["likelihood_pct"]}%</b></span>'
                f' <span style="font-size:.7rem;color:#8b949e">· {row["sessions"]} sessions · {row["total_hours"]}h</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

with tab_scatter:
    fig_s = px.scatter_mapbox(
        clust, lat="lat", lon="lon",
        color="zone_label", size="duration_min",
        hover_data={"city": True, "duration_min": True, "timestamp": True, "lat": False, "lon": False},
        mapbox_style=MAPBOX, zoom=9,
        color_discrete_sequence=["#58a6ff", "#d29922", "#f85149", "#8b949e"],
    )
    themed(fig_s, "All Activity Sessions (size = duration)", height=580)
    fig_s.update_layout(margin=dict(l=0, r=0, t=48, b=0), legend=dict(x=0.01, y=0.99))
    st.plotly_chart(fig_s, use_container_width=True, key="scatter_map")

with tab_zones:
    col_z1, col_z2 = st.columns(2)
    with col_z1:
        zone_t = clust.groupby("zone_label")["duration_min"].sum().reset_index()
        zone_t["hours"] = (zone_t["duration_min"] / 60).round(2)
        fig_zt = go.Figure(go.Bar(
            x=zone_t["zone_label"], y=zone_t["hours"],
            marker_color=["#58a6ff", "#d29922", "#f85149", "#8b949e"][:len(zone_t)],
            text=zone_t["hours"].apply(lambda x: f"{x:.1f}h"),
            textposition="outside", textfont=dict(color="#e6edf3"),
        ))
        themed(fig_zt, "Total Time per Zone (hours)", height=340)
        st.plotly_chart(fig_zt, use_container_width=True)

    with col_z2:
        zc = clust["zone_label"].value_counts().reset_index()
        zc.columns = ["zone", "sessions"]
        fig_zp = go.Figure(go.Pie(
            labels=zc["zone"], values=zc["sessions"],
            hole=0.52, textinfo="label+percent",
            marker=dict(colors=["#58a6ff", "#d29922", "#f85149", "#8b949e"],
                        line=dict(color="#0d1117", width=2)),
        ))
        themed(fig_zp, "Session Share by Zone", height=340)
        st.plotly_chart(fig_zp, use_container_width=True)

    # Zone comparison radar
    valid = stats[stats["cluster_id"] != -1].head(5)
    cats  = ["sessions", "total_hours", "likelihood_pct", "recency", "freq"]
    fig_r = go.Figure()
    for _, row in valid.iterrows():
        vals = [row[c] for c in cats]
        # normalise to 0-1
        maxv = [len(clust), clust["duration_min"].sum()/60, 100, 1, 1]
        norm = [v/m if m else 0 for v, m in zip(vals, maxv)]
        norm.append(norm[0])
        fig_r.add_trace(go.Scatterpolar(
            r=norm + [norm[0]],
            theta=cats + [cats[0]],
            fill="toself", name=row["label"], opacity=0.6,
        ))
    themed(fig_r, "Zone Profile Radar", height=400)
    fig_r.update_layout(polar=dict(
        bgcolor="#161b22",
        radialaxis=dict(color="#484f58", gridcolor="#21262d"),
        angularaxis=dict(color="#8b949e", gridcolor="#21262d"),
    ))
    st.plotly_chart(fig_r, use_container_width=True)

with tab_anomaly:
    adf = anomdf.copy()
    n_anom = adf["anomaly"].sum()
    st.markdown(
        f'<div class="pal-card pal-card-red">'
        f'<b style="color:#f85149">{n_anom} anomalous sessions</b> detected out of {len(adf)} total '
        f'({n_anom/len(adf)*100:.1f}%)</div>',
        unsafe_allow_html=True,
    )
    col_a1, col_a2 = st.columns(2)
    with col_a1:
        # Anomaly map
        adf["color"] = adf["anomaly"].map({True: "#f85149", False: "#30363d"})
        fig_am = px.scatter_mapbox(
            adf, lat="lat", lon="lon",
            color="anomaly",
            color_discrete_map={True: "#f85149", False: "#30363d"},
            hover_data={"anomaly_reason": True, "duration_min": True},
            mapbox_style=MAPBOX, zoom=8, size_max=8,
        )
        themed(fig_am, "Anomalous Sessions (red)", height=380)
        fig_am.update_layout(margin=dict(l=0, r=0, t=48, b=0))
        st.plotly_chart(fig_am, use_container_width=True, key="anomaly_map")
    with col_a2:
        reason_counts = (
            adf[adf["anomaly"]]["anomaly_reason"]
            .str.strip().str.split().explode()
            .value_counts().reset_index()
        )
        reason_counts.columns = ["reason", "count"]
        fig_rc = go.Figure(go.Bar(
            x=reason_counts["count"], y=reason_counts["reason"],
            orientation="h",
            marker_color="#f85149",
            text=reason_counts["count"], textposition="outside",
            textfont=dict(color="#e6edf3"),
        ))
        themed(fig_rc, "Anomaly Types", height=380)
        st.plotly_chart(fig_rc, use_container_width=True)

    st.markdown('<div class="section-hdr">Anomalous Session Log</div>', unsafe_allow_html=True)
    log = adf[adf["anomaly"]][["timestamp", "lat", "lon", "zone_label", "duration_min", "hour", "anomaly_reason"]].copy()
    log["timestamp"] = log["timestamp"].dt.strftime("%Y-%m-%d %H:%M")
    st.dataframe(log.head(50), use_container_width=True, hide_index=True)
