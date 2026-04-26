"""
Threat Intelligence Enrichment — checks the target IP against free public
threat sources: Tor exit-node list, ASN/org infrastructure tags, reverse DNS.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from core.state import inject_theme, require_data, themed, risk_color
from core.threat_intel import enrich

st.set_page_config(page_title="Threat Intel · ARGUS", page_icon="🛡️", layout="wide")
inject_theme()
d = require_data()

bg = d["base_geo"]
ip = d["target_ip"]

st.markdown(
    '<div style="font-size:1.1rem;font-weight:600;color:#F0F0F0;margin-bottom:3px;">Threat Intelligence Enrichment</div>'
    '<div style="font-size:.75rem;color:#8C8C8C;margin-bottom:18px;">'
    'Tor exit list · ASN tagging · Reverse DNS · Combined threat band</div>',
    unsafe_allow_html=True,
)

# ── Run enrichment (cached per IP for the session) ─────────────────────────────
cache_key = f"ti_enrichment_{ip}"
if cache_key not in st.session_state:
    with st.spinner("Querying public threat sources…"):
        st.session_state[cache_key] = enrich(ip, bg)
ti = st.session_state[cache_key]

# ── Top row: threat band + signal count + tor + rdns ───────────────────────────
band_color = {
    "HIGH":   "#F14C4C",
    "MEDIUM": "#F5A623",
    "LOW":    "#3DA5FF",
    "CLEAR":  "#23D18B",
}.get(ti["band"], "#8C8C8C")

c1, c2, c3, c4 = st.columns(4)
c1.markdown(
    f'<div class="pal-card pal-card-accent" style="text-align:center">'
    f'<div style="font-size:.66rem;color:#8C8C8C;text-transform:uppercase;letter-spacing:.05em">Threat Band</div>'
    f'<div style="font-size:1.6rem;font-weight:600;color:{band_color};margin-top:4px">{ti["band"]}</div>'
    f'<div style="font-size:.7rem;color:#8C8C8C">Score {ti["score"]}/100</div>'
    f'</div>',
    unsafe_allow_html=True,
)
c2.markdown(
    f'<div class="pal-card" style="text-align:center">'
    f'<div style="font-size:.66rem;color:#8C8C8C;text-transform:uppercase;letter-spacing:.05em">Tor Exit Node</div>'
    f'<div style="font-size:1.3rem;font-weight:600;color:{"#F14C4C" if ti["tor_hit"] else "#23D18B"};margin-top:6px">'
    f'{"YES" if ti["tor_hit"] else "NO"}</div>'
    f'<div style="font-size:.65rem;color:#8C8C8C">{ti["tor_list_size"] or "—"} entries checked</div>'
    f'</div>',
    unsafe_allow_html=True,
)
c3.markdown(
    f'<div class="pal-card" style="text-align:center">'
    f'<div style="font-size:.66rem;color:#8C8C8C;text-transform:uppercase;letter-spacing:.05em">Signals</div>'
    f'<div style="font-size:1.6rem;font-weight:600;color:#0B88F8;margin-top:4px">{len(ti["signals"])}</div>'
    f'<div style="font-size:.65rem;color:#8C8C8C">Distinct findings</div>'
    f'</div>',
    unsafe_allow_html=True,
)
_rdns_html = ti["rdns"] or "<span style=\"color:#444\">no PTR record</span>"
c4.markdown(
    f'<div class="pal-card" style="text-align:center">'
    f'<div style="font-size:.66rem;color:#8C8C8C;text-transform:uppercase;letter-spacing:.05em">Reverse DNS</div>'
    f'<div style="font-size:.85rem;font-weight:500;color:#F0F0F0;margin-top:8px;'
    f'word-break:break-all;font-family:JetBrains Mono,monospace;">'
    f'{_rdns_html}</div>'
    f'</div>',
    unsafe_allow_html=True,
)

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

# ── Signals table ──────────────────────────────────────────────────────────────
SEV_COLORS = {
    "critical": "#F14C4C",
    "high":     "#F5A623",
    "medium":   "#3DA5FF",
    "low":      "#8C8C8C",
    "clear":    "#23D18B",
}

left, right = st.columns([1.3, 1], gap="large")

with left:
    st.markdown('<div class="section-hdr">Signal Findings</div>', unsafe_allow_html=True)
    rows = []
    for sev, label, detail in ti["signals"]:
        color = SEV_COLORS.get(sev, "#8C8C8C")
        rows.append(
            f'<div class="entity-row">'
            f'<span style="background:{color}1F;color:{color};padding:1px 7px;'
            f'border-radius:2px;font-size:.6rem;font-weight:600;letter-spacing:.06em;'
            f'text-transform:uppercase;border:1px solid {color}30">{sev}</span>'
            f'<span style="color:#F0F0F0;font-weight:500;min-width:170px">{label}</span>'
            f'<span style="color:#8C8C8C;font-size:.78rem">{detail}</span>'
            f'</div>'
        )
    st.markdown(
        '<div class="pal-card">' + "".join(rows) + '</div>',
        unsafe_allow_html=True,
    )

with right:
    st.markdown('<div class="section-hdr">ASN / Infrastructure Tags</div>', unsafe_allow_html=True)
    if ti["asn_tags"]:
        tag_html = " ".join(
            f'<span class="badge badge-threat" style="margin-right:5px">{t}</span>'
            for t in ti["asn_tags"]
        )
    else:
        tag_html = '<span class="badge badge-safe">RESIDENTIAL</span>'
    st.markdown(
        f'<div class="pal-card">'
        f'<div style="margin-bottom:10px">{tag_html}</div>'
        f'<div style="font-size:.74rem;color:#8C8C8C;line-height:1.5">'
        f'<b style="color:#F0F0F0">ISP</b><br>{bg.get("isp","—")}<br><br>'
        f'<b style="color:#F0F0F0">Org</b><br>{bg.get("org","—")}<br><br>'
        f'<b style="color:#F0F0F0">AS</b><br>{bg.get("as","—")}'
        f'</div></div>',
        unsafe_allow_html=True,
    )

# ── Score breakdown chart ──────────────────────────────────────────────────────
st.markdown('<div class="section-hdr">Score Composition</div>', unsafe_allow_html=True)

components = []
if ti["tor_hit"]:                           components.append(("Tor Exit Node", 50, "#F14C4C"))
if "ANONYMIZER" in ti["asn_tags"]:          components.append(("Anonymizer ASN", 35, "#F14C4C"))
if "VPN" in ti["asn_tags"]:                 components.append(("VPN Provider", 25, "#F5A623"))
if "HOSTING" in ti["asn_tags"]:             components.append(("Hosting / Datacenter", 15, "#F5A623"))
if "CLOUD" in ti["asn_tags"]:               components.append(("Cloud Provider", 10, "#3DA5FF"))
if not components:                          components.append(("Residential / Clean", 0, "#23D18B"))

fig = go.Figure(go.Bar(
    y=[c[0] for c in components],
    x=[c[1] for c in components],
    orientation="h",
    marker=dict(color=[c[2] for c in components]),
    text=[f"+{c[1]}" if c[1] else "—" for c in components],
    textposition="outside",
    hovertemplate="%{y}: +%{x}<extra></extra>",
))
fig.update_layout(height=max(180, 60 + 40 * len(components)),
                  xaxis_title="Score contribution", yaxis_title="")
themed(fig, height=max(180, 60 + 40 * len(components)))
st.plotly_chart(fig, use_container_width=True)

st.caption(
    f"Enrichment ran in {ti['duration_ms']} ms · sources: "
    "check.torproject.org/torbulkexitlist, ip-api.com (already cached), socket reverse DNS"
)
