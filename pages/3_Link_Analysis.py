"""Link Analysis — interactive entity relationship graph."""
import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
import networkx as nx
import pandas as pd
from core.state import inject_theme, require_data, themed
from core import graph as G_mod

st.set_page_config(page_title="Link Analysis · Mini Palantir", page_icon="🕸️", layout="wide")
inject_theme()
d = require_data()

G: nx.Graph = d["graph"]
ents = d["entities"]

st.markdown(
    '<div style="font-size:1.5rem;font-weight:700;color:#58a6ff;margin-bottom:4px;">🕸️ LINK ANALYSIS</div>'
    f'<div style="font-size:.75rem;color:#8b949e;margin-bottom:20px;">'
    f'{G.number_of_nodes()} nodes · {G.number_of_edges()} edges · Target: {d["target_ip"]}</div>',
    unsafe_allow_html=True,
)

# ── Controls ───────────────────────────────────────────────────────────────────
col_ctrl, col_main = st.columns([1, 4], gap="medium")

with col_ctrl:
    all_types = sorted({a.get("type", "?") for _, a in G.nodes(data=True)})
    sel_types = st.multiselect("Filter node types", all_types, default=all_types, key="link_types")

    show_labels = st.checkbox("Show labels", value=True)
    height_px   = st.slider("Graph height", 400, 900, 640, step=40)

    st.markdown('<div class="section-hdr">Node Legend</div>', unsafe_allow_html=True)
    for ntype, style in G_mod.NODE_STYLES.items():
        if ntype in all_types:
            st.markdown(
                f'<div class="entity-row">'
                f'<span style="color:{style["color"]};font-size:1.1rem">◉</span>'
                f'<span style="font-size:.8rem">{ntype}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

with col_main:
    # Filter graph
    sub = G.copy()
    remove = [n for n, a in G.nodes(data=True) if a.get("type") not in sel_types]
    sub.remove_nodes_from(remove)

    tab_plotly, tab_table = st.tabs(["Graph", "Entity Table"])

    with tab_plotly:
        if sub.number_of_nodes() == 0:
            st.info("No nodes match current filter.")
        else:
            fig = G_mod.render(sub, height=height_px)
            if not show_labels:
                fig.update_traces(mode="markers", selector=dict(mode="markers+text"))
            st.plotly_chart(fig, use_container_width=True, key="link_graph")

        # Degree centrality
        if sub.number_of_nodes() > 0:
            centrality = nx.degree_centrality(sub)
            top_nodes = sorted(centrality, key=centrality.get, reverse=True)[:15]
            cent_df = pd.DataFrame([
                {
                    "Node": n[:40],
                    "Type": sub.nodes[n].get("type", "?"),
                    "Degree": sub.degree(n),
                    "Centrality": round(centrality[n], 3),
                }
                for n in top_nodes
            ])
            st.markdown('<div class="section-hdr">Top Connected Nodes</div>', unsafe_allow_html=True)
            fig_cent = go.Figure(go.Bar(
                x=cent_df["Centrality"],
                y=cent_df["Node"],
                orientation="h",
                marker_color=[G_mod.NODE_STYLES.get(t, G_mod.DEFAULT_STYLE)["color"]
                              for t in cent_df["Type"]],
                text=cent_df["Type"],
                textposition="outside",
                textfont=dict(color="#8b949e", size=9),
            ))
            themed(fig_cent, "Node Centrality (connection importance)", height=max(280, len(cent_df)*22))
            fig_cent.update_layout(yaxis=dict(categoryorder="total ascending"))
            st.plotly_chart(fig_cent, use_container_width=True)

    with tab_table:
        rows = [
            {
                "Type": a.get("type", "?"),
                "Label": a.get("label", n)[:50],
                "Connections": G.degree(n),
                "Tooltip": a.get("tooltip", "")[:80],
            }
            for n, a in G.nodes(data=True)
            if a.get("type") in sel_types
        ]
        ent_df = pd.DataFrame(rows).sort_values("Connections", ascending=False)
        st.dataframe(ent_df, use_container_width=True, hide_index=True)

        st.markdown('<div class="section-hdr">Edge List</div>', unsafe_allow_html=True)
        edges = [
            {"From": u[:40], "To": v[:40], "Relation": a.get("relation", ""), "Weight": round(a.get("weight",1),2)}
            for u, v, a in G.edges(data=True)
            if G.nodes[u].get("type") in sel_types and G.nodes[v].get("type") in sel_types
        ]
        st.dataframe(pd.DataFrame(edges).sort_values("Weight", ascending=False),
                     use_container_width=True, hide_index=True)
