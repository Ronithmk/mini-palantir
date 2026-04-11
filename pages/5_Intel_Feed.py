"""Intel Feed — multi-source web intelligence, topic clusters, entity cards."""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from core.state import inject_theme, require_data, themed
from core.clusterer import CAT_COLORS

st.set_page_config(page_title="Intel Feed · Mini Palantir", page_icon="🌐", layout="wide")
inject_theme()
d = require_data()

wdf = d["web_df"]
clr = d["clusterer"]

st.markdown(
    f'<div style="font-size:1.1rem;font-weight:600;color:#d4dce8;margin-bottom:3px;">Intel Feed</div>'
    f'<div style="font-size:.75rem;color:#6b7685;margin-bottom:18px;">'
    f'{len(wdf)} items · "{d["query"]}" · Wikipedia · Reddit · Google News · DuckDuckGo</div>',
    unsafe_allow_html=True,
)

if wdf.empty:
    st.info("No web data. Re-run investigation with a search query.")
    st.stop()

# ── Source metric tiles ────────────────────────────────────────────────────────
src_counts = wdf["category"].value_counts()
cols = st.columns(len(src_counts) + 1)
badge_map = {"Encyclopedia": "wiki", "Social Media": "reddit", "News": "news", "Web Search": "org"}
for i, (cat, cnt) in enumerate(src_counts.items()):
    with cols[i]:
        st.markdown(
            f'<div class="pal-metric">'
            f'<div class="val">{cnt}</div>'
            f'<div class="lbl">{cat}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
with cols[-1]:
    n_topics = wdf["topic_label"].nunique() if "topic_label" in wdf.columns else 0
    st.markdown(
        f'<div class="pal-metric"><div class="val" style="color:#d29922">{n_topics}</div>'
        f'<div class="lbl">Topics</div></div>',
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

tab_feed, tab_clusters, tab_charts = st.tabs(["Feed", "Topic Clusters", "Analytics"])

# ── Feed ───────────────────────────────────────────────────────────────────────
with tab_feed:
    col_filter, _ = st.columns([2, 3])
    with col_filter:
        all_cats = ["All"] + sorted(wdf["category"].unique().tolist())
        sel_cat  = st.selectbox("Filter by source", all_cats, key="feed_filter")
    search_term = st.text_input("Search titles & bodies", placeholder="Filter intel…", key="feed_search")

    show = wdf.copy()
    if sel_cat != "All":
        show = show[show["category"] == sel_cat]
    if search_term.strip():
        mask = show["text"].str.contains(search_term.strip(), case=False, na=False)
        show = show[mask]

    st.markdown(f'<div style="font-size:.7rem;color:#8b949e;margin-bottom:8px;">{len(show)} items</div>',
                unsafe_allow_html=True)

    BADGE_COLOR = {"Encyclopedia": "wiki", "Social Media": "reddit",
                   "News": "news", "Web Search": "org"}

    for _, row in show.iterrows():
        bk  = BADGE_COLOR.get(row["category"], "org")
        src = str(row.get("source", ""))
        ttl = str(row.get("title", ""))
        bdy = str(row.get("body", ""))
        url = str(row.get("url", ""))
        pub = str(row.get("published", ""))
        topic = str(row.get("topic_label", "")) if "topic_label" in row.index else ""

        with st.expander(f"{ttl[:100]}"):
            pub_html   = f'<span style="font-size:.7rem;color:#484f58">{pub[:30]}</span>' if pub else ""
            topic_html = f'<span class="badge badge-zone" style="margin-left:auto">{topic[:30]}</span>' if topic else ""
            url_html   = f'<a href="{url}" target="_blank" style="font-size:.75rem;color:#58a6ff;">Open source →</a>' if url else ""
            st.markdown(
                f'<div class="pal-card" style="margin:0;padding:12px 16px;">'
                f'<div style="display:flex;gap:8px;align-items:center;margin-bottom:8px;">'
                f'<span class="badge badge-{bk}">{row["category"]}</span>'
                f'<span style="font-size:.75rem;color:#8b949e">{src}</span>'
                f'{pub_html}{topic_html}'
                f'</div>'
                f'<div style="font-size:.85rem;color:#e6edf3;line-height:1.5;">{bdy[:500]}</div>'
                f'{url_html}'
                f'</div>',
                unsafe_allow_html=True,
            )

# ── Topic Clusters ─────────────────────────────────────────────────────────────
with tab_clusters:
    col_sc, col_bar = st.columns(2)

    with col_sc:
        if "px" in wdf.columns:
            fig_sc = px.scatter(
                wdf, x="px", y="py",
                color="topic_label", symbol="category",
                hover_data={"title": True, "category": True, "topic_label": True,
                            "px": False, "py": False},
                color_discrete_sequence=px.colors.qualitative.Bold,
            )
            fig_sc.update_traces(marker=dict(size=9, opacity=0.85,
                                             line=dict(color="#0d1117", width=0.8)))
            themed(fig_sc, "Topic Clusters (TF-IDF → KMeans, 2D projection)", height=500)
            fig_sc.update_layout(
                xaxis=dict(showticklabels=False, showgrid=False),
                yaxis=dict(showticklabels=False, showgrid=False),
                legend=dict(orientation="h", yanchor="bottom", y=-0.3, font=dict(size=9)),
            )
            st.plotly_chart(fig_sc, use_container_width=True, key="topic_scatter")

    with col_bar:
        topic_sum = clr.topic_summary(wdf)
        fig_tb = go.Figure(go.Bar(
            x=topic_sum["count"],
            y=topic_sum["topic_label"],
            orientation="h",
            marker=dict(
                color=topic_sum["count"],
                colorscale=[[0,"#161b22"],[1,"#d29922"]],
                line=dict(color="#0d1117", width=0.5),
            ),
            text=topic_sum["sources"],
            textposition="outside",
            textfont=dict(color="#8b949e", size=9),
        ))
        themed(fig_tb, "Items per Topic Cluster", height=500)
        fig_tb.update_layout(
            xaxis_title="Items",
            yaxis=dict(title="", categoryorder="total ascending"),
            showlegend=False,
        )
        st.plotly_chart(fig_tb, use_container_width=True)

    # Sunburst
    fig_sun = px.sunburst(
        wdf, path=["category", "topic_label"],
        color="category",
        color_discrete_map=CAT_COLORS,
    )
    themed(fig_sun, "Source → Topic Hierarchy", height=480)
    st.plotly_chart(fig_sun, use_container_width=True)

# ── Analytics ──────────────────────────────────────────────────────────────────
with tab_charts:
    col_a1, col_a2 = st.columns(2)

    with col_a1:
        type_sum = clr.type_summary(wdf)
        fig_src = go.Figure(go.Bar(
            x=type_sum["category"], y=type_sum["count"],
            marker=dict(
                color=[CAT_COLORS.get(c, "#8b949e") for c in type_sum["category"]],
                line=dict(color="#0d1117", width=1),
            ),
            text=type_sum["count"], textposition="outside",
            textfont=dict(color="#e6edf3"),
        ))
        themed(fig_src, "Items by Source Type", height=350)
        fig_src.update_layout(showlegend=False, xaxis_title="", yaxis_title="Items")
        st.plotly_chart(fig_src, use_container_width=True)

    with col_a2:
        fig_pie = go.Figure(go.Pie(
            labels=type_sum["category"], values=type_sum["count"],
            hole=0.5,
            marker=dict(
                colors=[CAT_COLORS.get(c, "#8b949e") for c in type_sum["category"]],
                line=dict(color="#0d1117", width=2),
            ),
            textinfo="label+percent",
            textfont=dict(color="#e6edf3", size=11),
        ))
        themed(fig_pie, "Source Distribution", height=350)
        st.plotly_chart(fig_pie, use_container_width=True)

    # Full table
    st.markdown('<div class="section-hdr">Full Intel Table</div>', unsafe_allow_html=True)
    tbl_cols = ["title", "category", "source", "topic_label", "url"] if "topic_label" in wdf.columns \
               else ["title", "category", "source", "url"]
    st.dataframe(wdf[tbl_cols], use_container_width=True, hide_index=True)
