"""Auto-generated Intelligence Report."""
import streamlit as st
from datetime import datetime
from core.state import inject_theme, require_data, risk_color

st.set_page_config(page_title="Report · ARGUS", page_icon="📋", layout="wide")
inject_theme()
d = require_data()

bg      = d["base_geo"]
stats   = d["cluster_stats"]
pred    = d["prediction"]
adf     = d["anomaly_df"]
wdf     = d["web_df"]
ents    = d["entities"]
risk    = d["risk_score"]
factors = d["risk_factors"]
valid   = stats[stats["cluster_id"] != -1]

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown(
    f'<div style="font-size:1.1rem;font-weight:600;color:#F0F0F0;margin-bottom:3px;">Intelligence Report</div>'
    f'<div style="font-size:.75rem;color:#8C8C8C;margin-bottom:18px;">'
    f'{d["case_id"]} · {datetime.now().strftime("%Y-%m-%d %H:%M UTC")}</div>',
    unsafe_allow_html=True,
)

rc = risk_color(risk)
rk_label = "HIGH" if risk >= 70 else "MEDIUM" if risk >= 40 else "LOW"

st.markdown(
    f'<div class="pal-card" style="border-left:4px solid {rc};background:#1C1C1C;">'
    f'<div style="display:flex;align-items:center;gap:16px;">'
    f'<div style="font-size:2.5rem;font-weight:700;color:{rc}">{risk}</div>'
    f'<div>'
    f'<div style="font-size:1rem;font-weight:700;color:{rc}">RISK: {rk_label}</div>'
    f'<div style="font-size:.75rem;color:#8C8C8C;">Case {d["case_id"]} · Target: {d["target_ip"]}</div>'
    f'</div></div></div>',
    unsafe_allow_html=True,
)

# ── Build report text ──────────────────────────────────────────────────────────
now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
anom_n  = int(adf["anomaly"].sum())
peak_h  = int(adf.groupby("hour")["duration_min"].sum().idxmax())
peak_d  = adf.groupby("weekday")["duration_min"].sum().idxmax()
total_h = round(adf["duration_min"].sum() / 60, 1)
top_z   = valid.iloc[0]["label"] if not valid.empty else "N/A"
top_c   = valid.iloc[0]["likelihood_pct"] if not valid.empty else 0

pred_str = (f"{pred['city']}, {pred['country']} ({pred['confidence']}% confidence)"
            if pred else "Undetermined")

report_md = f"""
## INTELLIGENCE REPORT — {d['case_id']}

---

### 1. EXECUTIVE SUMMARY

This report presents findings from a geospatial and open-source intelligence analysis of target IP **{d['target_ip']}**, conducted on **{now_str}**. The analysis ingested {len(adf)} simulated activity sessions over {adf['timestamp'].dt.date.nunique()} days and {len(wdf)} items from open-source intelligence feeds.

**Risk Assessment: {rk_label} ({risk}/100)**

---

### 2. TARGET PROFILE

| Field | Value |
|---|---|
| IP Address | `{bg.get('query', '?')}` |
| City / Region | {bg.get('city', '?')}, {bg.get('regionName') or bg.get('region', '?')} |
| Country | {bg.get('country', '?')} |
| ISP | {bg.get('isp', 'N/A')} |
| Organisation | {bg.get('org', 'N/A')} |
| Timezone | {bg.get('timezone', 'N/A')} |
| Coordinates | {bg.get('lat', '?')} N, {bg.get('lon', '?')} E |

---

### 3. GEOSPATIAL ANALYSIS

**{len(valid)} activity zones** were identified using DBSCAN spatial clustering (4km radius).

| Zone | City | Sessions | Total Time | Likelihood |
|---|---|---|---|---|
{"".join(f'| {r["label"]} | {r["city"]} | {r["sessions"]} | {r["total_hours"]}h | {r["likelihood_pct"]}% |' + chr(10) for _, r in valid.iterrows())}

**Predicted current location:** {pred_str}

---

### 4. PATTERN OF LIFE

- **Total recorded activity:** {total_h} hours across {len(adf)} sessions
- **Peak activity hour:** {peak_h:02d}:00
- **Most active day:** {peak_d}
- **Night-time sessions (01:00–04:00):** {adf['hour'].between(1,4).sum()} ({adf['hour'].between(1,4).mean()*100:.1f}%)
- **Weekend sessions:** {adf['weekday'].isin(['Saturday','Sunday']).mean()*100:.1f}%
- **Anomalous sessions flagged:** {anom_n} ({anom_n/len(adf)*100:.1f}%)
- **Primary zone:** {top_z} (confidence: {top_c}%)

---

### 5. ENTITY ANALYSIS

**{len(ents)} entities** extracted across the following types:
{"".join(f'- **{t}**: {sum(1 for e in ents if e["type"]==t)}' + chr(10) for t in sorted({e["type"] for e in ents}))}

---

### 6. OPEN-SOURCE INTELLIGENCE

**{len(wdf)} items** collected from {wdf['category'].nunique()} source types:
{"".join(f'- **{cat}**: {cnt} items' + chr(10) for cat, cnt in wdf['category'].value_counts().items())}

{f"**Topic clusters identified:** {wdf['topic_label'].nunique()}" if 'topic_label' in wdf.columns else ""}

---

### 7. RISK FACTORS

{"".join(f'- [{kind.upper()}] {msg}' + chr(10) for msg, kind in factors)}

---

### 8. CONCLUSIONS & RECOMMENDATIONS

Based on the analysis:

1. The target IP is registered to **{bg.get('isp', 'unknown ISP')}** in **{bg.get('country', 'unknown country')}**.
2. The most probable current location is **{pred_str}**.
3. Activity patterns suggest a **{"business-hours" if 8 <= peak_h <= 18 else "evening/night"}** user profile, primarily active on **{peak_d}s**.
4. {'**Elevated anomaly rate warrants further investigation.**' if anom_n / len(adf) > 0.15 else 'Anomaly rate is within normal range.'}
5. Risk level assessed as **{rk_label}**.

---

*Report generated by ARGUS · {now_str} · Case {d['case_id']}*
*For investigative use only. Geo data is simulated; web data sourced from public APIs.*
"""

# ── Display ────────────────────────────────────────────────────────────────────
col_rep, col_aside = st.columns([2, 1], gap="large")

with col_rep:
    st.markdown(report_md)

with col_aside:
    st.markdown('<div class="section-hdr">Quick Stats</div>', unsafe_allow_html=True)
    quick = [
        ("Total Sessions", len(adf)),
        ("Activity Hours", f"{total_h}h"),
        ("Zones Found", len(valid)),
        ("Entities", len(ents)),
        ("Intel Items", len(wdf)),
        ("Anomalies", anom_n),
    ]
    for lbl, val in quick:
        st.markdown(
            f'<div class="entity-row"><span style="color:#8C8C8C;flex:1">{lbl}</span>'
            f'<b style="color:#0B88F8">{val}</b></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="section-hdr" style="margin-top:20px">Risk Factors</div>', unsafe_allow_html=True)
    for msg, kind in factors:
        color = {"alert": "#F14C4C", "warn": "#F5A623", "safe": "#23D18B"}.get(kind, "#8C8C8C")
        dot   = {"alert": "dot-alert", "warn": "dot-warn",  "safe": "dot-live"}.get(kind, "dot-dead")
        st.markdown(
            f'<div class="entity-row"><span class="dot {dot}"></span>'
            f'<span style="color:{color};font-size:.78rem;">{msg}</span></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="section-hdr" style="margin-top:20px">Export</div>', unsafe_allow_html=True)
    st.download_button(
        "Download Report (.md)",
        data=report_md.encode("utf-8"),
        file_name=f"{d['case_id']}_report.md",
        mime="text/markdown",
        use_container_width=True,
    )
    st.download_button(
        "Download Entity List (.csv)",
        data="\n".join(
            ["type,value,confidence,source"] +
            [f'{e["type"]},{e["value"][:60]},{e["confidence"]},{e["source"]}' for e in ents]
        ).encode("utf-8"),
        file_name=f"{d['case_id']}_entities.csv",
        mime="text/csv",
        use_container_width=True,
    )
