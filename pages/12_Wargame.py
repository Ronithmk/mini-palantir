"""
Adversary Wargaming — interactive defender vs attacker simulation.

The differentiator vs Palantir: passive analysis platforms tell you what was.
This tells you what's likely to happen given specific defensive choices, by
solving a small security-game between a defender (who allocates a budget across
DETECT / HARDEN / DECEIVE) and an attacker (who picks the highest-yielding of
PHISH / EXPLOIT / INSIDER / SUPPLY).
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from core.state import inject_theme, require_data, themed
from core.predictor import build_fingerprint
from core.wargame import (
    run_wargame, DEFENDER_STRATS, ATTACKER_STRATS,
    BASE_ATTACK_LOSS, MITIGATION,
)

st.set_page_config(page_title="Wargame · ARGUS", page_icon="♟️", layout="wide")
inject_theme()
d = require_data()

adf   = d["anomaly_df"]
stats = d["cluster_stats"]
ip    = d["target_ip"]

st.markdown(
    '<div style="font-size:1.1rem;font-weight:600;color:#F0F0F0;margin-bottom:3px;">Adversary Wargaming</div>'
    '<div style="font-size:.75rem;color:#8C8C8C;margin-bottom:18px;">'
    'Game-theoretic defender / attacker simulation · '
    'Equilibrium budget allocation · Not in Palantir</div>',
    unsafe_allow_html=True,
)

fp = build_fingerprint(adf, stats)

# Optional: pull the threat band from the threat-intel page if it was visited
ti_cache_key = f"ti_enrichment_{ip}"
threat_band = st.session_state.get(ti_cache_key, {}).get("band", "MEDIUM")

# ── Allocation sliders ─────────────────────────────────────────────────────────
st.markdown('<div class="section-hdr">Defender Budget Allocation</div>', unsafe_allow_html=True)
st.caption(
    "Distribute a unit budget across the three defensive postures. "
    "DETECT = monitoring · HARDEN = patching/controls · DECEIVE = honeypots/canary tokens."
)

col_d, col_h, col_k = st.columns(3)
detect  = col_d.slider("DETECT",  0.0, 1.0, 0.40, 0.05, key="wg_detect")
harden  = col_h.slider("HARDEN",  0.0, 1.0, 0.40, 0.05, key="wg_harden")
deceive = col_k.slider("DECEIVE", 0.0, 1.0, 0.20, 0.05, key="wg_deceive")

allocation = {"DETECT": detect, "HARDEN": harden, "DECEIVE": deceive}
total = detect + harden + deceive

if total <= 0:
    st.error("Allocate at least one strategy above zero.")
    st.stop()

# Show normalisation if user didn't sum to 1.0
norm = {k: v / total for k, v in allocation.items()}
st.caption(
    f"Raw sum = {total:.2f}. Normalised allocation: "
    f"DETECT {norm['DETECT']*100:.0f}% · HARDEN {norm['HARDEN']*100:.0f}% · "
    f"DECEIVE {norm['DECEIVE']*100:.0f}% · Threat band: {threat_band}"
)

# ── Run the game ───────────────────────────────────────────────────────────────
result = run_wargame(fp, allocation, threat_band=threat_band)

# ── Top metrics ────────────────────────────────────────────────────────────────
top_atk = max(result.attacker_priors, key=result.attacker_priors.get)
top_atk_p = result.attacker_priors[top_atk] * 100

m1, m2, m3, m4 = st.columns(4)
m1.markdown(
    f'<div class="pal-card pal-card-accent" style="text-align:center">'
    f'<div style="font-size:.66rem;color:#8C8C8C;text-transform:uppercase;letter-spacing:.05em">Most-Likely Attack</div>'
    f'<div style="font-size:1.4rem;font-weight:600;color:#F14C4C;margin-top:4px">{top_atk}</div>'
    f'<div style="font-size:.66rem;color:#8C8C8C">{top_atk_p:.0f}% prior</div>'
    f'</div>',
    unsafe_allow_html=True,
)
current_loss = sum(
    p * sum(norm[ds] * result.payoff[(ds, atk)] for ds in DEFENDER_STRATS)
    for atk, p in result.attacker_priors.items()
)
loss_color = "#F14C4C" if current_loss > 35 else "#F5A623" if current_loss > 20 else "#23D18B"
m2.markdown(
    f'<div class="pal-card" style="text-align:center">'
    f'<div style="font-size:.66rem;color:#8C8C8C;text-transform:uppercase;letter-spacing:.05em">Your Expected Loss</div>'
    f'<div style="font-size:1.6rem;font-weight:600;color:{loss_color};margin-top:4px">{current_loss:.1f}</div>'
    f'<div style="font-size:.66rem;color:#8C8C8C">/100</div>'
    f'</div>',
    unsafe_allow_html=True,
)
m3.markdown(
    f'<div class="pal-card" style="text-align:center">'
    f'<div style="font-size:.66rem;color:#8C8C8C;text-transform:uppercase;letter-spacing:.05em">Equilibrium Loss</div>'
    f'<div style="font-size:1.6rem;font-weight:600;color:#23D18B;margin-top:4px">{result.optimal_loss:.1f}</div>'
    f'<div style="font-size:.66rem;color:#8C8C8C">Best achievable</div>'
    f'</div>',
    unsafe_allow_html=True,
)
m4.markdown(
    f'<div class="pal-card" style="text-align:center">'
    f'<div style="font-size:.66rem;color:#8C8C8C;text-transform:uppercase;letter-spacing:.05em">Optimal Mix</div>'
    f'<div style="font-size:.78rem;color:#F0F0F0;margin-top:8px;line-height:1.5">'
    f'D {result.optimal_mix["DETECT"]*100:.0f}% · '
    f'H {result.optimal_mix["HARDEN"]*100:.0f}% · '
    f'K {result.optimal_mix["DECEIVE"]*100:.0f}%</div>'
    f'</div>',
    unsafe_allow_html=True,
)

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

tab_matrix, tab_priors, tab_compare, tab_explain = st.tabs([
    "Payoff Matrix", "Attacker Priors", "Allocation Sweep", "Recommendation",
])

# ── Tab: Payoff matrix heatmap ────────────────────────────────────────────────
with tab_matrix:
    z = [[result.payoff[(ds, atk)] for atk in ATTACKER_STRATS] for ds in DEFENDER_STRATS]
    fig = go.Figure(go.Heatmap(
        z=z,
        x=ATTACKER_STRATS,
        y=DEFENDER_STRATS,
        colorscale=[[0, "#23D18B"], [0.5, "#F5A623"], [1, "#F14C4C"]],
        text=[[f"{v:.1f}" for v in row] for row in z],
        texttemplate="%{text}",
        textfont={"size": 13, "color": "#FFFFFF"},
        hovertemplate="Defender %{y} vs Attacker %{x}<br>Loss: %{z}<extra></extra>",
        colorbar=dict(title=dict(text="Loss", font=dict(color="#8C8C8C", size=10)),
                      tickfont=dict(color="#8C8C8C")),
    ))
    fig.update_layout(
        xaxis_title="Attacker strategy",
        yaxis_title="Defender strategy",
    )
    themed(fig, height=320)
    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "Each cell is the defender's expected loss (0–100) when the defender's "
        "*entire* budget is on the row strategy and the attacker plays the "
        "column strategy. Greener = better for the defender."
    )

    # Best-response per defender strategy
    rows = []
    for ds in DEFENDER_STRATS:
        atk = result.attacker_best_response[ds]
        rows.append({
            "Defender pure strategy": ds,
            "Attacker best response": atk,
            "Resulting loss":         result.payoff[(ds, atk)],
            "Expected loss vs prior": result.expected_loss[ds],
        })
    st.markdown('<div class="section-hdr">Attacker Best-Response Table</div>', unsafe_allow_html=True)
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ── Tab: Attacker priors (from fingerprint) ───────────────────────────────────
with tab_priors:
    priors = result.attacker_priors
    fig = go.Figure(go.Bar(
        x=list(priors.keys()),
        y=[priors[k] * 100 for k in priors],
        marker=dict(color=["#F14C4C" if k == top_atk else "#3DA5FF" for k in priors]),
        text=[f"{priors[k]*100:.1f}%" for k in priors],
        textposition="outside",
        hovertemplate="%{x}: %{y:.1f}%<extra></extra>",
    ))
    fig.update_layout(yaxis_title="Probability (%)", xaxis_title="Attacker strategy")
    themed(fig, height=320)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-hdr">How These Priors Are Built</div>', unsafe_allow_html=True)
    f = fp["features"]
    st.markdown(
        f'<div class="pal-card">'
        f'<div class="entity-row">'
        f'<span class="badge badge-ip">PHISH</span> Boosted by night activity '
        f'({f.get("night_activity",0)*100:.0f}%) and anomaly rate '
        f'({f.get("anomaly_rate",0)*100:.0f}%)</div>'
        f'<div class="entity-row">'
        f'<span class="badge badge-threat">EXPLOIT</span> Boosted when threat band is '
        f'HIGH or MEDIUM (current: {threat_band})</div>'
        f'<div class="entity-row">'
        f'<span class="badge badge-zone">INSIDER</span> Boosted by zone diversity '
        f'({f.get("zone_diversity",0)*100:.0f}%) — more touch points → more people</div>'
        f'<div class="entity-row">'
        f'<span class="badge badge-org">SUPPLY</span> Boosted by remote-zone usage '
        f'({f.get("remote_zone",0)*100:.0f}%) — distributed third-party surface</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

# ── Tab: Sweep ────────────────────────────────────────────────────────────────
with tab_compare:
    st.caption("Each point is one feasible allocation on the (DETECT, HARDEN, DECEIVE) simplex. "
               "Y-axis is expected loss against the attacker prior.")
    rows = []
    n = 10
    for i in range(n + 1):
        for j in range(n + 1 - i):
            k = n - i - j
            alloc = {"DETECT": i / n, "HARDEN": j / n, "DECEIVE": k / n}
            loss = sum(
                p * sum(alloc[ds] * result.payoff[(ds, atk)] for ds in DEFENDER_STRATS)
                for atk, p in result.attacker_priors.items()
            )
            rows.append({
                "DETECT":  alloc["DETECT"],
                "HARDEN":  alloc["HARDEN"],
                "DECEIVE": alloc["DECEIVE"],
                "loss":    round(loss, 2),
            })
    sweep = pd.DataFrame(rows).sort_values("loss")

    fig = go.Figure(go.Scatter3d(
        x=sweep["DETECT"], y=sweep["HARDEN"], z=sweep["DECEIVE"],
        mode="markers",
        marker=dict(size=5, color=sweep["loss"],
                    colorscale=[[0, "#23D18B"], [0.5, "#F5A623"], [1, "#F14C4C"]],
                    colorbar=dict(title=dict(text="Loss", font=dict(color="#8C8C8C")),
                                  tickfont=dict(color="#8C8C8C"))),
        hovertemplate="D=%{x:.2f} H=%{y:.2f} K=%{z:.2f}<br>Loss=%{marker.color:.2f}<extra></extra>",
    ))
    fig.update_layout(
        scene=dict(
            xaxis_title="DETECT", yaxis_title="HARDEN", zaxis_title="DECEIVE",
            xaxis=dict(backgroundcolor="#0F0F0F", gridcolor="#1C1C1C"),
            yaxis=dict(backgroundcolor="#0F0F0F", gridcolor="#1C1C1C"),
            zaxis=dict(backgroundcolor="#0F0F0F", gridcolor="#1C1C1C"),
        ),
        paper_bgcolor="#0F0F0F",
        height=460,
        margin=dict(l=0, r=0, t=10, b=0),
        font=dict(color="#8C8C8C"),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(sweep.head(10), use_container_width=True, hide_index=True)

# ── Tab: Recommendation ───────────────────────────────────────────────────────
with tab_explain:
    delta = round(current_loss - result.optimal_loss, 2)
    verdict_color = "#23D18B" if abs(delta) < 1.0 else "#F5A623" if delta < 5 else "#F14C4C"

    st.markdown(
        f'<div class="pal-card" style="border-left:2px solid {verdict_color}">'
        f'<div style="font-size:.7rem;color:#8C8C8C;text-transform:uppercase;'
        f'letter-spacing:.05em;margin-bottom:6px">Equilibrium Recommendation</div>'
        f'<div style="font-size:1rem;color:#F0F0F0;font-weight:600;margin-bottom:8px">'
        f'Tilt toward {result.optimal_defender} '
        f'(D {result.optimal_mix["DETECT"]*100:.0f}% / '
        f'H {result.optimal_mix["HARDEN"]*100:.0f}% / '
        f'K {result.optimal_mix["DECEIVE"]*100:.0f}%)</div>'
        f'<div style="font-size:.78rem;color:#8C8C8C">'
        f'Your current allocation: {current_loss:.1f} loss · '
        f'Equilibrium: {result.optimal_loss:.1f} loss · '
        f'Δ = {delta:+.2f}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-hdr">Why</div>', unsafe_allow_html=True)
    bullet_html = "".join(
        f'<div class="entity-row" style="border-bottom:1px solid #2A2A2A">'
        f'<span style="color:#0B88F8">▸</span>'
        f'<span style="color:#F0F0F0">{r}</span></div>'
        for r in result.rationale
    )
    st.markdown(f'<div class="pal-card">{bullet_html}</div>', unsafe_allow_html=True)

    with st.expander("Mitigation matrix (how each control reduces each attack)"):
        mit_rows = []
        for ds in DEFENDER_STRATS:
            row = {"Defender": ds}
            for atk in ATTACKER_STRATS:
                row[atk] = f"{MITIGATION[(ds, atk)]*100:.0f}%"
            mit_rows.append(row)
        st.dataframe(pd.DataFrame(mit_rows), use_container_width=True, hide_index=True)
        st.caption("Each cell shows the fraction of attacker payoff removed at full (1.0) "
                   "investment in that defender strategy.")
