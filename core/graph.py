"""Entity relationship graph — networkx structure + plotly interactive render."""
import networkx as nx
import plotly.graph_objects as go
import numpy as np

NODE_STYLES: dict[str, dict] = {
    "IP":           {"color": "#58a6ff", "size": 28, "symbol": "diamond"},
    "Location":     {"color": "#3fb950", "size": 22, "symbol": "circle"},
    "Organization": {"color": "#bc8cff", "size": 20, "symbol": "square"},
    "Zone":         {"color": "#d29922", "size": 18, "symbol": "triangle-up"},
    "Topic":        {"color": "#f0883e", "size": 14, "symbol": "circle"},
    "Encyclopedia": {"color": "#79c0ff", "size": 10, "symbol": "circle"},
    "Social Media": {"color": "#ff6314", "size": 10, "symbol": "circle"},
    "News":         {"color": "#8b949e", "size": 10, "symbol": "circle"},
    "Web Search":   {"color": "#d3a6c8", "size": 10, "symbol": "circle"},
    "Domain":       {"color": "#56d364", "size": 9,  "symbol": "circle"},
    "Email":        {"color": "#ffa657", "size": 9,  "symbol": "circle"},
}
DEFAULT_STYLE = {"color": "#484f58", "size": 9, "symbol": "circle"}

EDGE_COLORS: dict[str, str] = {
    "geolocated_to":  "#3fb950",
    "registered_to":  "#bc8cff",
    "active_in":      "#d29922",
    "contains":       "#30363d",
    "related_to":     "#58a6ff",
    "sourced_from":   "#8b949e",
    "co_occurs_with": "#484f58",
}


def build(base_geo: dict, cluster_stats, web_df, entities: list[dict]) -> nx.Graph:
    G = nx.Graph()
    ip = base_geo.get("query", "?")

    def n(node_id, ntype, label=None, **kw):
        G.add_node(node_id, type=ntype, label=(label or str(node_id))[:28], **kw)

    def e(u, v, rel, weight=1.0):
        G.add_edge(u, v, relation=rel, weight=weight)

    # Core IP node
    n(ip, "IP", ip, tooltip=f"Target IP\nISP: {base_geo.get('isp','?')}\nTimezone: {base_geo.get('timezone','?')}")

    # Location
    city    = base_geo.get("city", "")
    country = base_geo.get("country", "")
    loc_id  = f"{city}, {country}"
    if city:
        n(loc_id, "Location", city, tooltip=f"{city}, {country}\n{base_geo.get('lat')}, {base_geo.get('lon')}")
        e(ip, loc_id, "geolocated_to", 4)

    # ISP / Org
    isp = base_geo.get("isp", "")
    if isp:
        n(isp, "Organization", isp[:24], tooltip=f"ISP: {isp}")
        e(ip, isp, "registered_to", 3)

    # Zones
    valid = cluster_stats[cluster_stats["cluster_id"] != -1]
    for _, row in valid.iterrows():
        zid = row["label"]
        n(zid, "Zone", zid, tooltip=(
            f"{zid}\nCity: {row['city']}\nSessions: {row['sessions']}"
            f"\n{row['total_hours']}h total\nLikelihood: {row['likelihood_pct']}%"
        ))
        e(ip, zid, "active_in", row["likelihood_pct"] / 25)
        if city and row["city"] != "Remote":
            e(loc_id, zid, "contains", 0.5)

    # Topics from web clustering
    if not web_df.empty and "topic_label" in web_df.columns:
        for topic in web_df["topic_label"].unique()[:8]:
            if not topic:
                continue
            n(topic, "Topic", topic[:26], tooltip=f"Topic cluster: {topic}")
            e(ip, topic, "related_to", 1.2)

        # Individual web items (up to 30)
        for _, row in web_df.head(30).iterrows():
            title = (row.get("title") or "")[:50]
            cat   = row.get("category", "Web Search")
            nid   = f"{cat}::{title}"
            n(nid, cat, title[:24], tooltip=f"[{cat}]\n{title}\n{row.get('url','')}")
            topic = row.get("topic_label", "")
            if topic and topic in G.nodes:
                e(topic, nid, "sourced_from", 0.6)
            else:
                e(ip, nid, "related_to", 0.4)

    return G


def render(G: nx.Graph, height: int = 640) -> go.Figure:
    if len(G.nodes) == 0:
        return go.Figure()

    pos = nx.spring_layout(G, seed=42, k=2.2, iterations=60)

    # ── Edge traces (one per relation type) ───────────────────────────────────
    edge_data: dict[str, dict] = {}
    for u, v, attrs in G.edges(data=True):
        rel = attrs.get("relation", "related_to")
        if rel not in edge_data:
            edge_data[rel] = {"x": [], "y": [], "weight": []}
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge_data[rel]["x"] += [x0, x1, None]
        edge_data[rel]["y"] += [y0, y1, None]
        edge_data[rel]["weight"].append(attrs.get("weight", 1))

    edge_traces = []
    for rel, d in edge_data.items():
        color = EDGE_COLORS.get(rel, "#30363d")
        avg_w = float(np.mean(d["weight"])) if d["weight"] else 1
        edge_traces.append(go.Scatter(
            x=d["x"], y=d["y"], mode="lines",
            line=dict(width=max(0.5, min(avg_w * 0.8, 4)), color=color),
            hoverinfo="none", showlegend=True, name=rel,
            legendgroup="edges",
        ))

    # ── Node traces (one per node type) ───────────────────────────────────────
    by_type: dict[str, dict] = {}
    for node, attrs in G.nodes(data=True):
        ntype = attrs.get("type", "Unknown")
        if ntype not in by_type:
            by_type[ntype] = {"x": [], "y": [], "text": [], "hover": [], "ids": []}
        x, y = pos[node]
        by_type[ntype]["x"].append(x)
        by_type[ntype]["y"].append(y)
        by_type[ntype]["text"].append(attrs.get("label", str(node)[:20]))
        by_type[ntype]["hover"].append(attrs.get("tooltip", str(node)))
        by_type[ntype]["ids"].append(node)

    node_traces = []
    for ntype, d in by_type.items():
        s = NODE_STYLES.get(ntype, DEFAULT_STYLE)
        node_traces.append(go.Scatter(
            x=d["x"], y=d["y"],
            mode="markers+text",
            name=ntype,
            marker=dict(
                size=s["size"], color=s["color"], symbol=s["symbol"],
                line=dict(width=1.5, color="#0d1117"),
                opacity=0.92,
            ),
            text=d["text"],
            textposition="top center",
            textfont=dict(size=9, color="#e6edf3"),
            hovertext=d["hover"],
            hoverinfo="text",
            legendgroup="nodes",
        ))

    fig = go.Figure(data=edge_traces + node_traces)
    fig.update_layout(
        paper_bgcolor="#0d1117", plot_bgcolor="#0d1117",
        font=dict(color="#e6edf3", family="monospace", size=10),
        height=height,
        showlegend=True,
        legend=dict(
            bgcolor="#161b22", bordercolor="#30363d", borderwidth=1,
            font=dict(size=9), x=1.01, y=1,
        ),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        margin=dict(l=10, r=160, t=40, b=10),
        title=dict(text="Entity Relationship Graph", font=dict(size=13, color="#e6edf3"), x=0.01),
        hovermode="closest",
    )
    return fig
