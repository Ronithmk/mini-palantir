"""Geo Intelligence — interactive map, movement trail, zone analysis."""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium
from core.state import (inject_theme, require_data, themed, MAPBOX,
                        ZONE_TYPE_FOLIUM, zone_type_badge, sparkline_svg)

st.set_page_config(page_title="Geo Intelligence · ARGUS", page_icon="🗺️", layout="wide")
inject_theme()
d = require_data()

bg     = d["base_geo"]
clust  = d["clustered_df"]
stats  = d["cluster_stats"]
pred   = d["prediction"]
anomdf = d["anomaly_df"]

st.markdown(
    f'<div style="font-size:1.1rem;font-weight:600;color:#F0F0F0;margin-bottom:3px;">Geo Intelligence</div>'
    f'<div style="font-size:.75rem;color:#8C8C8C;margin-bottom:18px;">'
    f'{d["target_ip"]} · {bg.get("city")}, {bg.get("country")} · {stats[stats["cluster_id"]!=-1]["cluster_id"].nunique()} zones</div>',
    unsafe_allow_html=True,
)

tab_map, tab_scatter, tab_density, tab_3d, tab_zones, tab_anomaly = st.tabs([
    "Interactive Map", "Session Scatter", "Density Heatmap", "3D Map", "Zone Analysis", "Anomalies"
])

# ── Zone-type hex colours (for folium CircleMarker) ───────────────────────────
_ZT_HEX = {"PRIMARY": "#00e5ff", "SECONDARY": "#ffd60a",
            "TRANSIT": "#bf5af2", "NOISE": "#444444"}

# Map zone_label → zone_type for session dots
def _label_to_zt(zone_label: str) -> str:
    if zone_label == "Primary Zone":   return "PRIMARY"
    if zone_label == "Secondary Zone": return "SECONDARY"
    return "TRANSIT"

# ── Build folium map once, cache in session ────────────────────────────────────
if d["folium_map"] is None:
    center = [clust["lat"].mean(), clust["lon"].mean()]
    m = folium.Map(location=center, zoom_start=10, tiles="CartoDB dark_matter")

    valid_stats = stats[stats["cluster_id"] != -1]

    # ── Zone centroid circles (Trackr-style coloured by zone type) ────────────
    for _, row in valid_stats.iterrows():
        zt     = row.get("zone_type", "TRANSIT")
        zcolor = _ZT_HEX.get(zt, "#444444")
        fcolor = ZONE_TYPE_FOLIUM.get(zt, "gray")
        folium.CircleMarker(
            location=[row["centroid_lat"], row["centroid_lon"]],
            radius=max(10, min(50, row["sessions"] / 2.5)),
            color=zcolor, fill=True, fill_color=zcolor, fill_opacity=0.30,
            weight=2,
            popup=folium.Popup(
                f"<b style='color:{zcolor}'>{row['label']} [{zt}]</b><br>"
                f"City: {row['city']}<br>"
                f"Sessions: {row['sessions']}<br>"
                f"Total: {row['total_hours']}h<br>"
                f"Likelihood: <b>{row['likelihood_pct']}%</b><br>"
                f"Active: {row.get('active_window','')}<br>"
                f"Frequency: {row.get('frequency','')}<br>"
                f"<small>{row['centroid_lat']}, {row['centroid_lon']}</small>",
                max_width=250,
            ),
            tooltip=f"{row['label']} [{zt}] — {row['likelihood_pct']}% confidence",
        ).add_to(m)

    # ── Connection lines: each zone centroid → predicted location ─────────────
    if pred:
        for _, row in valid_stats.iterrows():
            zt     = row.get("zone_type", "TRANSIT")
            zcolor = _ZT_HEX.get(zt, "#444444")
            folium.PolyLine(
                [[row["centroid_lat"], row["centroid_lon"]], [pred["lat"], pred["lon"]]],
                color=zcolor, weight=1, opacity=0.40, dash_array="4 6",
                tooltip=f"{row['label']} → Predicted location",
            ).add_to(m)

    # ── Session dots coloured by zone type ────────────────────────────────────
    sample = clust.sample(min(400, len(clust)), random_state=42)
    for _, row in sample.iterrows():
        zt     = _label_to_zt(row["zone_label"])
        zcolor = _ZT_HEX.get(zt, "#444444")
        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=2.5, color=zcolor, fill=True, fill_color=zcolor, fill_opacity=0.55,
            weight=0,
            tooltip=f"{row['zone_label']} · {row['duration_min']}min",
        ).add_to(m)

    # ── Movement trail (last 20 sessions) ─────────────────────────────────────
    trail = clust.sort_values("timestamp").tail(20)
    trail_coords = trail[["lat", "lon"]].values.tolist()
    if len(trail_coords) > 1:
        folium.PolyLine(
            trail_coords, color="#ffd60a", weight=2, opacity=0.75, dash_array="5 5",
            tooltip="Recent movement trail",
        ).add_to(m)

    # ── Anomaly markers ───────────────────────────────────────────────────────
    anoms = anomdf[anomdf["anomaly"]].head(30)
    for _, row in anoms.iterrows():
        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=5, color="#F14C4C", fill=True, fill_opacity=0.8,
            tooltip=f"⚠ Anomaly: {row['anomaly_reason'].strip()}",
        ).add_to(m)

    # ── Predicted location marker ─────────────────────────────────────────────
    if pred:
        folium.Marker(
            location=[pred["lat"], pred["lon"]],
            popup=f"Predicted Location: {pred['city']} ({pred['confidence']}%)",
            tooltip=f"Predicted: {pred['city']}",
            icon=folium.Icon(color="green", icon="home", prefix="fa"),
        ).add_to(m)

    # ── Legend ────────────────────────────────────────────────────────────────
    legend = """
    <div style='position:fixed;bottom:30px;left:30px;z-index:9999;
         background:#1C1C1C;border:1px solid #2A2A2A;border-radius:8px;padding:12px;
         font-family:monospace;font-size:11px;color:#F0F0F0;'>
    <b style='color:#0B88F8;'>LEGEND</b><br>
    <span style='color:#00e5ff'>●</span> PRIMARY zone<br>
    <span style='color:#ffd60a'>●</span> SECONDARY zone<br>
    <span style='color:#bf5af2'>●</span> TRANSIT zone<br>
    <span style='color:#F14C4C'>●</span> Anomaly<br>
    <span style='color:#ffd60a'>- -</span> Movement trail<br>
    <span style='color:#23D18B'>⌂</span> Predicted location
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
            zt      = row.get("zone_type", "TRANSIT")
            zcolor  = _ZT_HEX.get(zt, "#444444")
            bar_w   = int(row["likelihood_pct"])
            spark   = row.get("spark_data", [])
            svg     = sparkline_svg(spark, width=96, height=22, color=zcolor)
            aw      = row.get("active_window", "")
            freq    = row.get("frequency", "")
            fs      = row.get("first_seen", "")
            ls      = row.get("last_seen", "")
            st.markdown(
                f'<div class="pal-card" style="padding:10px 14px;margin-bottom:8px;'
                f'border-left:3px solid {zcolor};">'
                # Header row: label + zone_type_badge + sparkline
                f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">'
                f'<b style="color:{zcolor};flex:1">{row["label"]}</b>'
                f'{zone_type_badge(zt)}'
                f'</div>'
                # Sparkline
                f'<div style="margin:4px 0 6px;">{svg}</div>'
                # City + coords
                f'<div style="font-size:.72rem;color:#8C8C8C;">{row["city"]}</div>'
                f'<div style="font-family:monospace;font-size:.67rem;color:#444444;margin-bottom:5px;">'
                f'{row["centroid_lat"]}, {row["centroid_lon"]}</div>'
                # Likelihood bar
                f'<div class="risk-bar-bg"><div class="risk-bar" '
                f'style="width:{bar_w}%;background:{zcolor}"></div></div>'
                f'<div style="display:flex;justify-content:space-between;font-size:.68rem;margin-top:3px;">'
                f'<span style="color:{zcolor}"><b>{row["likelihood_pct"]}%</b> likelihood</span>'
                f'<span style="color:#8C8C8C">{row["sessions"]} sess</span>'
                f'</div>'
                # Active window + frequency
                f'<div style="font-size:.67rem;color:#8C8C8C;margin-top:5px;">'
                f'<span style="color:#444444">ACTIVE</span> {aw}</div>'
                f'<div style="font-size:.67rem;color:#8C8C8C;">'
                f'<span style="color:#444444">FREQ</span> {freq} &nbsp;·&nbsp; {row["total_hours"]}h total</div>'
                # First / last seen
                f'<div style="font-size:.63rem;color:#444444;margin-top:4px;">'
                f'First {fs}<br>Last &nbsp;{ls}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

with tab_scatter:
    fig_s = px.scatter_mapbox(
        clust, lat="lat", lon="lon",
        color="zone_label", size="duration_min",
        hover_data={"city": True, "duration_min": True, "timestamp": True, "lat": False, "lon": False},
        mapbox_style=MAPBOX, zoom=9,
        color_discrete_sequence=["#0B88F8", "#F5A623", "#F14C4C", "#8C8C8C"],
    )
    themed(fig_s, "All Activity Sessions (size = duration)", height=580)
    fig_s.update_layout(margin=dict(l=0, r=0, t=48, b=0), legend=dict(x=0.01, y=0.99))
    st.plotly_chart(fig_s, use_container_width=True, key="scatter_map")

with tab_density:
    col_dm, col_dc = st.columns([3, 1])
    with col_dm:
        fig_den = px.density_mapbox(
            clust, lat="lat", lon="lon",
            z="duration_min",
            radius=18,
            center={"lat": bg["lat"], "lon": bg["lon"]},
            zoom=8,
            mapbox_style=MAPBOX,
            color_continuous_scale=[
                [0.0, "#0F0F0F"],
                [0.2, "#0a2a4a"],
                [0.45, "#0B88F8"],
                [0.70, "#23D18B"],
                [0.90, "#F5A623"],
                [1.0,  "#F14C4C"],
            ],
            hover_data={"zone_label": True, "duration_min": True},
        )
        themed(fig_den, "Session Density Heatmap (intensity = active minutes)", height=560)
        fig_den.update_layout(
            margin=dict(l=0, r=0, t=48, b=0),
            coloraxis_colorbar=dict(
                title="Min", tickfont=dict(color="#8C8C8C", size=9),
                bgcolor="#1C1C1C", bordercolor="#2A2A2A",
            ),
        )
        # Overlay target IP pin
        pin_df = __import__("pandas").DataFrame([{
            "lat": bg["lat"], "lon": bg["lon"],
            "label": f'{bg.get("city","?")} ({d["target_ip"]})',
        }])
        fig_den.add_trace(go.Scattermapbox(
            lat=pin_df["lat"], lon=pin_df["lon"],
            mode="markers+text",
            marker=dict(size=14, color="#0B88F8", symbol="circle"),
            text=pin_df["label"], textposition="top right",
            textfont=dict(color="#F0F0F0", size=11),
            name="Target IP",
            hovertemplate=f"<b>{d['target_ip']}</b><br>{bg.get('city')}, {bg.get('country')}<br>"
                          f"Lat: {bg['lat']:.5f}<br>Lon: {bg['lon']:.5f}<extra></extra>",
        ))
        st.plotly_chart(fig_den, use_container_width=True, key="density_map")

    with col_dc:
        # Target IP coordinate card
        _lat, _lon = bg["lat"], bg["lon"]
        _lat_dir = "N" if _lat >= 0 else "S"
        _lon_dir = "E" if _lon >= 0 else "W"
        st.markdown(
            f'<div class="pal-card pal-card-accent" style="margin-bottom:12px;">'
            f'<div class="section-hdr">Target Location</div>'
            f'<div style="font-size:1rem;font-weight:600;color:#F0F0F0;margin-bottom:4px;">'
            f'{bg.get("city","?")}, {bg.get("country","?")}</div>'
            f'<div style="font-size:.75rem;color:#8C8C8C;margin-bottom:10px;">'
            f'{bg.get("regionName") or bg.get("region","")}</div>'
            f'<div style="font-size:.65rem;color:#8C8C8C;letter-spacing:.06em;margin-bottom:3px;">EXACT COORDINATES</div>'
            f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:.88rem;color:#0B88F8;margin-bottom:2px;">'
            f'{abs(_lat):.6f}° {_lat_dir}</div>'
            f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:.88rem;color:#0B88F8;margin-bottom:10px;">'
            f'{abs(_lon):.6f}° {_lon_dir}</div>'
            f'<div style="font-size:.65rem;color:#8C8C8C;letter-spacing:.06em;margin-bottom:3px;">DECIMAL (WGS-84)</div>'
            f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:.78rem;color:#F0F0F0;">'
            f'{_lat:.6f}, {_lon:.6f}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Density stats
        total_min = int(clust["duration_min"].sum())
        peak_zone = clust.groupby("zone_label")["duration_min"].sum().idxmax()
        st.markdown(
            f'<div class="pal-card">'
            f'<div class="section-hdr">Density Stats</div>'
            f'<div class="entity-row"><span class="badge badge-ip">SESSIONS</span>{len(clust)}</div>'
            f'<div class="entity-row"><span class="badge badge-zone">ACTIVE</span>{total_min // 60}h {total_min % 60}m total</div>'
            f'<div class="entity-row"><span class="badge badge-org">PEAK ZONE</span>{peak_zone}</div>'
            f'<div class="entity-row"><span class="badge badge-loc">RADIUS</span>'
            f'~{clust["lat"].std() * 111:.1f} km spread</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Zone centroid coordinates
        st.markdown('<div class="section-hdr" style="margin-top:8px">Zone Centroids</div>',
                    unsafe_allow_html=True)
        for _, row in stats[stats["cluster_id"] != -1].iterrows():
            zt = row.get("zone_type", "TRANSIT")
            zc = _ZT_HEX.get(zt, "#444444")
            st.markdown(
                f'<div style="margin-bottom:8px;">'
                f'<div style="font-size:.72rem;font-weight:600;color:{zc};margin-bottom:2px;">'
                f'{row["label"]}</div>'
                f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:.67rem;color:#8C8C8C;">'
                f'{row["centroid_lat"]:.5f}, {row["centroid_lon"]:.5f}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

with tab_3d:
    import pydeck as pdk

    col_3d, col_3dc = st.columns([3, 1])

    with col_3dc:
        st.markdown('<div class="section-hdr">3D Map Controls</div>', unsafe_allow_html=True)
        pitch   = st.slider("Camera Pitch", 0, 70, 50, key="3d_pitch")
        bearing = st.slider("Bearing", 0, 360, 20, key="3d_bearing")
        radius  = st.slider("Hex Radius (m)", 100, 2000, 400, step=50, key="3d_radius")
        elev_sc = st.slider("Elevation Scale", 10, 200, 60, key="3d_elev")
        layer_choice = st.radio(
            "Layer type",
            ["Hexagon (density)", "Columns (zones)", "Both"],
            key="3d_layer",
        )
        st.markdown(
            '<div class="pal-card" style="margin-top:12px">'
            '<div class="section-hdr">Legend</div>'
            '<div style="font-size:.72rem;color:#8C8C8C;line-height:1.8;">'
            '<span style="color:#0B88F8">■</span> Low density<br>'
            '<span style="color:#23D18B">■</span> Medium<br>'
            '<span style="color:#F5A623">■</span> High<br>'
            '<span style="color:#F14C4C">■</span> Very high<br>'
            '<span style="color:#ffffff">●</span> Zone centroid<br>'
            '<span style="color:#F14C4C">●</span> Anomaly<br>'
            '<span style="color:#23D18B">▲</span> Predicted location'
            '</div></div>',
            unsafe_allow_html=True,
        )

    with col_3d:
        # ── Hexagon layer ──────────────────────────────────────────────────────
        hex_data = clust[["lat", "lon", "duration_min"]].copy()
        hex_data = hex_data.rename(columns={"lat": "latitude", "lon": "longitude"})

        hex_layer = pdk.Layer(
            "HexagonLayer",
            data=hex_data,
            get_position=["longitude", "latitude"],
            get_elevation="duration_min",
            elevation_scale=elev_sc,
            elevation_range=[0, 3000],
            radius=radius,
            pickable=True,
            extruded=True,
            coverage=0.85,
            color_range=[
                [11,  50, 120, 200],   # deep blue
                [11, 136, 248, 220],   # cobalt
                [35, 209, 139, 220],   # green
                [245, 166, 35, 220],   # orange
                [241,  76,  76, 230],  # red
                [255, 255, 255, 240],  # white peak
            ],
        )

        # ── Column layer for zone centroids ────────────────────────────────────
        valid = stats[stats["cluster_id"] != -1].copy()
        zt_rgb = {
            "PRIMARY":   [11, 136, 248],
            "SECONDARY": [245, 166, 35],
            "TRANSIT":   [191, 90, 242],
            "NOISE":     [68, 68, 68],
        }
        col_data = []
        for _, row in valid.iterrows():
            zt = row.get("zone_type", "TRANSIT")
            rgb = zt_rgb.get(zt, [68, 68, 68])
            col_data.append({
                "longitude": row["centroid_lon"],
                "latitude":  row["centroid_lat"],
                "height":    int(row["likelihood_pct"] * 20),
                "label":     row["label"],
                "r": rgb[0], "g": rgb[1], "b": rgb[2],
            })
        import pandas as _pd
        col_df = _pd.DataFrame(col_data)

        column_layer = pdk.Layer(
            "ColumnLayer",
            data=col_df,
            get_position=["longitude", "latitude"],
            get_elevation="height",
            elevation_scale=8,
            radius=max(radius * 1.5, 500),
            get_fill_color=["r", "g", "b", 200],
            get_line_color=[255, 255, 255, 60],
            line_width_min_pixels=1,
            pickable=True,
            extruded=True,
            auto_highlight=True,
        )

        # ── Anomaly scatter layer ──────────────────────────────────────────────
        anom_pts = anomdf[anomdf["anomaly"]][["lat", "lon"]].copy()
        anom_pts = anom_pts.rename(columns={"lat": "latitude", "lon": "longitude"})
        anom_layer = pdk.Layer(
            "ScatterplotLayer",
            data=anom_pts,
            get_position=["longitude", "latitude"],
            get_color=[241, 76, 76, 220],
            get_radius=max(radius * 0.6, 150),
            pickable=True,
        )

        # ── Predicted location marker ──────────────────────────────────────────
        layers = []
        if layer_choice == "Hexagon (density)":
            layers = [hex_layer, anom_layer]
        elif layer_choice == "Columns (zones)":
            layers = [column_layer, anom_layer]
        else:
            layers = [hex_layer, column_layer, anom_layer]

        if pred:
            pred_layer = pdk.Layer(
                "ScatterplotLayer",
                data=_pd.DataFrame([{"latitude": pred["lat"], "longitude": pred["lon"]}]),
                get_position=["longitude", "latitude"],
                get_color=[35, 209, 139, 255],
                get_radius=max(radius * 0.8, 200),
                pickable=True,
            )
            layers.append(pred_layer)

        view = pdk.ViewState(
            latitude=bg["lat"],
            longitude=bg["lon"],
            zoom=9,
            pitch=pitch,
            bearing=bearing,
        )

        deck = pdk.Deck(
            layers=layers,
            initial_view_state=view,
            map_provider="carto",
            map_style="dark",
            tooltip={
                "html": "<b>{label}</b><br>Sessions: {sessions}<br>Likelihood: {likelihood_pct}%",
                "style": {
                    "backgroundColor": "#1C1C1C",
                    "color": "#F0F0F0",
                    "fontFamily": "monospace",
                    "fontSize": "12px",
                    "border": "1px solid #2A2A2A",
                    "padding": "8px",
                },
            },
        )
        st.pydeck_chart(deck, use_container_width=True, height=580)

        st.markdown(
            f'<div style="font-size:.68rem;color:#444444;margin-top:4px;text-align:center;">'
            f'Target: {bg.get("city")}, {bg.get("country")} · '
            f'{bg["lat"]:.5f}° N, {bg["lon"]:.5f}° E · Drag to rotate · Scroll to zoom'
            f'</div>',
            unsafe_allow_html=True,
        )

with tab_zones:
    col_z1, col_z2 = st.columns(2)
    with col_z1:
        zone_t = clust.groupby("zone_label")["duration_min"].sum().reset_index()
        zone_t["hours"] = (zone_t["duration_min"] / 60).round(2)
        fig_zt = go.Figure(go.Bar(
            x=zone_t["zone_label"], y=zone_t["hours"],
            marker_color=["#0B88F8", "#F5A623", "#F14C4C", "#8C8C8C"][:len(zone_t)],
            text=zone_t["hours"].apply(lambda x: f"{x:.1f}h"),
            textposition="outside", textfont=dict(color="#F0F0F0"),
        ))
        themed(fig_zt, "Total Time per Zone (hours)", height=340)
        st.plotly_chart(fig_zt, use_container_width=True)

    with col_z2:
        zc = clust["zone_label"].value_counts().reset_index()
        zc.columns = ["zone", "sessions"]
        fig_zp = go.Figure(go.Pie(
            labels=zc["zone"], values=zc["sessions"],
            hole=0.52, textinfo="label+percent",
            marker=dict(colors=["#0B88F8", "#F5A623", "#F14C4C", "#8C8C8C"],
                        line=dict(color="#0F0F0F", width=2)),
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
        bgcolor="#1C1C1C",
        radialaxis=dict(color="#444444", gridcolor="#2A2A2A"),
        angularaxis=dict(color="#8C8C8C", gridcolor="#2A2A2A"),
    ))
    st.plotly_chart(fig_r, use_container_width=True)

with tab_anomaly:
    adf = anomdf.copy()
    n_anom = adf["anomaly"].sum()
    st.markdown(
        f'<div class="pal-card pal-card-red">'
        f'<b style="color:#F14C4C">{n_anom} anomalous sessions</b> detected out of {len(adf)} total '
        f'({n_anom/len(adf)*100:.1f}%)</div>',
        unsafe_allow_html=True,
    )
    col_a1, col_a2 = st.columns(2)
    with col_a1:
        # Anomaly map
        adf["color"] = adf["anomaly"].map({True: "#F14C4C", False: "#2A2A2A"})
        fig_am = px.scatter_mapbox(
            adf, lat="lat", lon="lon",
            color="anomaly",
            color_discrete_map={True: "#F14C4C", False: "#2A2A2A"},
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
            marker_color="#F14C4C",
            text=reason_counts["count"], textposition="outside",
            textfont=dict(color="#F0F0F0"),
        ))
        themed(fig_rc, "Anomaly Types", height=380)
        st.plotly_chart(fig_rc, use_container_width=True)

    st.markdown('<div class="section-hdr">Anomalous Session Log</div>', unsafe_allow_html=True)
    log = adf[adf["anomaly"]][["timestamp", "lat", "lon", "zone_label", "duration_min", "hour", "anomaly_reason"]].copy()
    log["timestamp"] = log["timestamp"].dt.strftime("%Y-%m-%d %H:%M")
    st.dataframe(log.head(50), use_container_width=True, hide_index=True)
