"""Mini Palantir — Home / Investigation Launcher."""
import streamlit as st
import uuid
from datetime import datetime
from core.state import inject_theme, set_data, get_data
from core.geo import GeoAnalyzer
from core.fetcher import IntelFetcher
from core.clusterer import TextClusterer
from core.entity import build_entity_list, compute_risk
from core import graph as G_mod

st.set_page_config(
    page_title="Mini Palantir",
    page_icon="🔵",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_theme()

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<div style="font-size:1.4rem;font-weight:700;letter-spacing:.08em;color:#58a6ff;">◈ MINI PALANTIR</div>'
        '<div style="font-size:.65rem;color:#8b949e;letter-spacing:.12em;margin-bottom:16px;">INTELLIGENCE PLATFORM</div>',
        unsafe_allow_html=True,
    )
    st.markdown("---")

    d = get_data()
    if d:
        rc = "#f85149" if d["risk_score"] >= 70 else "#d29922" if d["risk_score"] >= 40 else "#3fb950"
        st.markdown(
            f'<div class="pal-card pal-card-accent">'
            f'<div style="font-size:.65rem;color:#8b949e;letter-spacing:.1em;">ACTIVE INVESTIGATION</div>'
            f'<div style="font-size:1rem;font-weight:700;color:#e6edf3;margin-top:4px;">{d["target_ip"]}</div>'
            f'<div style="font-size:.7rem;color:#8b949e;">{d["case_id"]}</div>'
            f'<div style="font-size:.75rem;margin-top:6px;">Risk: <b style="color:{rc}">{d["risk_score"]}/100</b></div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.markdown("**Navigate:**")
        st.page_link("pages/1_Overview.py",         label="Overview",        icon="📊")
        st.page_link("pages/2_Geo_Intelligence.py", label="Geo Intelligence", icon="🗺️")
        st.page_link("pages/3_Link_Analysis.py",    label="Link Analysis",   icon="🕸️")
        st.page_link("pages/4_Pattern_of_Life.py",  label="Pattern of Life", icon="📅")
        st.page_link("pages/5_Intel_Feed.py",       label="Intel Feed",      icon="🌐")
        st.page_link("pages/6_Report.py",           label="Report",          icon="📋")
    st.markdown("---")
    st.caption("Free APIs · No keys required")

# ── Home content ───────────────────────────────────────────────────────────────
st.markdown(
    '<div style="font-size:2rem;font-weight:700;letter-spacing:.06em;color:#58a6ff;">◈ MINI PALANTIR</div>'
    '<div style="font-size:.8rem;color:#8b949e;letter-spacing:.1em;margin-bottom:24px;">'
    'GEOSPATIAL INTELLIGENCE  ·  LINK ANALYSIS  ·  PATTERN OF LIFE  ·  ENTITY GRAPH</div>',
    unsafe_allow_html=True,
)

col_form, col_info = st.columns([1, 1], gap="large")

with col_form:
    st.markdown('<div class="pal-card pal-card-accent">', unsafe_allow_html=True)
    st.markdown("### New Investigation")
    target_ip    = st.text_input("Target IP Address", placeholder="e.g. 8.8.8.8", key="inp_ip")
    query        = st.text_input("Intelligence Query", placeholder="e.g. cybersecurity India", key="inp_q")
    history_days = st.slider("Activity History (days)", 10, 90, 45)
    n_topics     = st.slider("Topic Clusters", 3, 10, 6)

    launch = st.button("LAUNCH INVESTIGATION", type="primary", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    if launch:
        if not target_ip.strip():
            st.error("Enter a target IP address.")
        else:
            geo = GeoAnalyzer()

            with st.status("Resolving target IP…", expanded=True) as status:
                base_geo = geo.lookup(target_ip.strip())
                if base_geo is None:
                    st.error("Could not resolve IP. Use a public (non-private) address.")
                    st.stop()
                st.write(f"Resolved: {base_geo.get('city')}, {base_geo.get('country')}")

                status.update(label="Generating activity history…")
                hist   = geo.generate_history(base_geo, days=history_days)
                clust  = geo.cluster(hist)
                stats  = geo.cluster_stats(clust)
                pred   = geo.predict(stats)
                anomdf = geo.detect_anomalies(clust)
                st.write(f"Generated {len(hist)} sessions across {stats['cluster_id'].nunique()} zones")

                effective_q = query.strip() or f"{base_geo.get('city','')} {base_geo.get('country','')}"
                status.update(label=f"Fetching intelligence for: {effective_q}…")
                fetcher  = IntelFetcher()
                web_items = fetcher.fetch_all(effective_q)
                st.write(f"Fetched {len(web_items)} web items")

                status.update(label="Clustering web data…")
                clr  = TextClusterer(n_clusters=n_topics)
                wdf  = clr.build_df(web_items)
                wdf  = clr.add_clusters(wdf)

                status.update(label="Building entity graph…")
                entities = build_entity_list(base_geo, stats, web_items, pred)
                risk_score, risk_factors = compute_risk(base_geo, stats, anomdf, web_items)
                graph = G_mod.build(base_geo, stats, wdf, entities)

                status.update(label="Complete.", state="complete")

            case_id = f"INV-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:4].upper()}"
            set_data({
                "case_id":      case_id,
                "target_ip":    target_ip.strip(),
                "analyzed_at":  datetime.now(),
                "query":        effective_q,
                "base_geo":     base_geo,
                "history_df":   hist,
                "clustered_df": clust,
                "anomaly_df":   anomdf,
                "cluster_stats": stats,
                "prediction":   pred,
                "web_items":    web_items,
                "web_df":       wdf,
                "clusterer":    clr,
                "entities":     entities,
                "graph":        graph,
                "risk_score":   risk_score,
                "risk_factors": risk_factors,
                "folium_map":   None,  # built lazily
            })
            st.success(f"Investigation {case_id} launched. Use the sidebar to navigate.")
            st.rerun()

with col_info:
    st.markdown(
        """
        <div class="pal-card">
        <div class="section-hdr">Capabilities</div>
        <div class="entity-row"><span class="badge badge-loc">GEO</span> Geospatial activity clustering — DBSCAN zones with lat/long centroids</div>
        <div class="entity-row"><span class="badge badge-ip">IP</span> IP lookup + ISP/org attribution via ip-api.com</div>
        <div class="entity-row"><span class="badge badge-org">GRAPH</span> Entity relationship link chart — IP, location, org, topics</div>
        <div class="entity-row"><span class="badge badge-zone">PATTERN</span> Pattern-of-life analysis — heatmap, anomaly detection, behavioural profile</div>
        <div class="entity-row"><span class="badge badge-wiki">INTEL</span> Multi-source web intelligence — Wikipedia, Reddit, Google News, DuckDuckGo</div>
        <div class="entity-row"><span class="badge badge-threat">RISK</span> Automated risk scoring with factor breakdown</div>
        <div class="entity-row"><span class="badge badge-news">REPORT</span> Auto-generated intelligence report</div>
        </div>

        <div class="pal-card" style="margin-top:12px;">
        <div class="section-hdr">Data Sources</div>
        <div class="entity-row">🌐 <b>ip-api.com</b> — IP geolocation (free, no key)</div>
        <div class="entity-row">📖 <b>Wikipedia REST API</b> — encyclopedic context (free)</div>
        <div class="entity-row">💬 <b>Reddit JSON API</b> — social signals (free)</div>
        <div class="entity-row">📰 <b>Google News RSS</b> — live news feed (free)</div>
        <div class="entity-row">🔍 <b>DuckDuckGo Instant</b> — web summaries (free)</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
