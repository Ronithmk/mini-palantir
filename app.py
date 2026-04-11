"""Mini Palantir — Home / Investigation Launcher."""
import streamlit as st
import uuid
from datetime import datetime
from core.state import inject_theme, set_data, get_data, LIVE_CLOCK_HTML
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
        '<div style="font-size:1rem;font-weight:600;color:#4d9de0;margin-bottom:2px;">Mini Palantir</div>'
        '<div style="font-size:.68rem;color:#6b7685;margin-bottom:10px;">Intelligence Platform</div>',
        unsafe_allow_html=True,
    )
    st.markdown(LIVE_CLOCK_HTML, unsafe_allow_html=True)
    st.markdown("---")

    d = get_data()
    if d:
        rc = "#e05050" if d["risk_score"] >= 70 else "#c09000" if d["risk_score"] >= 40 else "#2ea043"
        st.markdown(
            f'<div class="pal-card pal-card-accent" style="padding:10px 14px;">'
            f'<div style="font-size:.65rem;color:#6b7685;">Active Investigation</div>'
            f'<div style="font-size:.9rem;font-weight:600;color:#d4dce8;margin-top:2px;">{d["target_ip"]}</div>'
            f'<div style="font-size:.68rem;color:#6b7685;">{d["case_id"]}</div>'
            f'<div style="font-size:.72rem;margin-top:5px;">Risk: <span style="color:{rc};font-weight:600">{d["risk_score"]}/100</span></div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.page_link("pages/1_Overview.py",         label="Overview",        icon="◎")
        st.page_link("pages/2_Geo_Intelligence.py", label="Geo Intelligence", icon="◉")
        st.page_link("pages/3_Link_Analysis.py",    label="Link Analysis",   icon="◈")
        st.page_link("pages/4_Pattern_of_Life.py",  label="Pattern of Life", icon="◐")
        st.page_link("pages/5_Intel_Feed.py",       label="Intel Feed",      icon="◑")
        st.page_link("pages/6_Report.py",           label="Report",          icon="◷")
    st.markdown("---")
    st.caption("Free APIs · No key required")

# ── Home content ───────────────────────────────────────────────────────────────
st.markdown(
    '<div style="font-size:1.6rem;font-weight:600;color:#4d9de0;margin-bottom:4px;">Mini Palantir</div>'
    '<div style="font-size:.78rem;color:#6b7685;margin-bottom:24px;">'
    'Geospatial intelligence · Link analysis · Pattern of life · Entity graph</div>',
    unsafe_allow_html=True,
)

col_form, col_info = st.columns([1, 1], gap="large")

# Handle preset chip selection (pre-fill before widget renders)
if "prefill_ip" in st.session_state:
    _prefill = st.session_state.pop("prefill_ip")
else:
    _prefill = ""

with col_form:
    st.markdown('<div class="pal-card pal-card-accent">', unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:.9rem;font-weight:600;color:#d4dce8;margin-bottom:12px;">New Investigation</div>',
        unsafe_allow_html=True,
    )
    target_ip    = st.text_input("Target IP Address", value=_prefill, placeholder="e.g. 8.8.8.8", key="inp_ip")
    query        = st.text_input("Intelligence Query", placeholder="e.g. cybersecurity India", key="inp_q")
    history_days = st.slider("Activity History (days)", 10, 90, 45)
    n_topics     = st.slider("Topic Clusters", 3, 10, 6)

    # ── Sample IP presets ──────────────────────────────────────────────────────
    st.markdown(
        '<div style="font-size:.68rem;color:#6b7685;margin:10px 0 5px;">Sample targets</div>',
        unsafe_allow_html=True,
    )
    SAMPLE_IPS = [
        ("8.8.8.8",       "Google DNS"),
        ("1.1.1.1",       "Cloudflare"),
        ("208.67.222.222","OpenDNS"),
        ("13.107.42.14",  "Microsoft"),
    ]
    chip_cols = st.columns(len(SAMPLE_IPS))
    for col, (ip, label) in zip(chip_cols, SAMPLE_IPS):
        with col:
            if st.button(label, key=f"chip_{ip}", help=ip, use_container_width=True):
                st.session_state["prefill_ip"] = ip
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    launch = st.button("Launch Investigation", type="primary", use_container_width=True)
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
        <div class="entity-row"><span class="badge badge-ip">GEO</span> Geospatial DBSCAN clustering — activity zones with lat/lon centroids</div>
        <div class="entity-row"><span class="badge badge-ip">IP</span> IP lookup · ISP/org attribution via ip-api.com</div>
        <div class="entity-row"><span class="badge badge-org">GRAPH</span> Entity relationship chart — IP, location, org, topics</div>
        <div class="entity-row"><span class="badge badge-zone">PATTERN</span> Heatmap · anomaly detection · behavioural profile</div>
        <div class="entity-row"><span class="badge badge-org">INTEL</span> Wikipedia · Reddit · Google News · DuckDuckGo</div>
        <div class="entity-row"><span class="badge badge-threat">RISK</span> Automated risk scoring with factor breakdown</div>
        <div class="entity-row"><span class="badge badge-org">AI</span> ARIA — Claude-powered analyst (Anthropic API key required)</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
