"""
Operations Center — Threat Intel, Watchlist, and Adversary Wargame in one page.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from core.state import inject_theme, require_data, themed, risk_color
from core.predictor import build_fingerprint
from core.threat_intel import enrich
from core.watchlist import (
    save_case, load_watchlist, delete_case, clear_watchlist,
    find_matches, alerts_for, WATCHLIST_FILE,
)
from core.wargame import (
    run_wargame, DEFENDER_STRATS, ATTACKER_STRATS, MITIGATION,
)

st.set_page_config(page_title="Operations · ARGUS", page_icon="🛡️", layout="wide")
inject_theme()
d = require_data()

adf   = d["anomaly_df"]
stats = d["cluster_stats"]
bg    = d["base_geo"]
ip    = d["target_ip"]

st.markdown(
    '<div style="font-size:1.1rem;font-weight:600;color:#F0F0F0;margin-bottom:3px;">Operations Center</div>'
    '<div style="font-size:.75rem;color:#8C8C8C;margin-bottom:18px;">'
    'Threat enrichment · Multi-case watchlist · Adversary wargaming</div>',
    unsafe_allow_html=True,
)

fp = build_fingerprint(adf, stats)

main_ti, main_wl, main_wg = st.tabs([
    "🛡️  Threat Intel", "📌  Watchlist", "♟️  Wargame",
])

# ──────────────────────────────────────────────────────────────────────────────
# 1. THREAT INTEL
# ──────────────────────────────────────────────────────────────────────────────
with main_ti:
    st.caption(
        "Tor exit-list lookup · ASN tagging · Reverse DNS · Combined threat band"
    )

    cache_key = f"ti_enrichment_{ip}"
    if cache_key not in st.session_state:
        with st.spinner("Querying public threat sources…"):
            st.session_state[cache_key] = enrich(ip, bg)
    ti = st.session_state[cache_key]

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
        f'word-break:break-all;font-family:JetBrains Mono,monospace;">{_rdns_html}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    SEV_COLORS = {
        "critical": "#F14C4C", "high": "#F5A623", "medium": "#3DA5FF",
        "low": "#8C8C8C", "clear": "#23D18B",
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
        st.markdown('<div class="pal-card">' + "".join(rows) + '</div>', unsafe_allow_html=True)

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

    st.markdown('<div class="section-hdr">Score Composition</div>', unsafe_allow_html=True)
    components = []
    if ti["tor_hit"]:                  components.append(("Tor Exit Node", 50, "#F14C4C"))
    if "ANONYMIZER" in ti["asn_tags"]: components.append(("Anonymizer ASN", 35, "#F14C4C"))
    if "VPN" in ti["asn_tags"]:        components.append(("VPN Provider", 25, "#F5A623"))
    if "HOSTING" in ti["asn_tags"]:    components.append(("Hosting / Datacenter", 15, "#F5A623"))
    if "CLOUD" in ti["asn_tags"]:      components.append(("Cloud Provider", 10, "#3DA5FF"))
    if not components:                 components.append(("Residential / Clean", 0, "#23D18B"))

    fig = go.Figure(go.Bar(
        y=[c[0] for c in components],
        x=[c[1] for c in components],
        orientation="h",
        marker=dict(color=[c[2] for c in components]),
        text=[f"+{c[1]}" if c[1] else "—" for c in components],
        textposition="outside",
        hovertemplate="%{y}: +%{x}<extra></extra>",
    ))
    h = max(180, 60 + 40 * len(components))
    fig.update_layout(xaxis_title="Score contribution", yaxis_title="")
    themed(fig, height=h)
    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        f"Enrichment ran in {ti['duration_ms']} ms · sources: "
        "check.torproject.org/torbulkexitlist, ip-api.com, socket reverse DNS"
    )

# ──────────────────────────────────────────────────────────────────────────────
# 2. WATCHLIST
# ──────────────────────────────────────────────────────────────────────────────
with main_wl:
    st.caption("Persisted multi-case management with cross-case fingerprint alerts.")

    sub_active, sub_saved, sub_alerts = st.tabs([
        "Active Investigation", "Saved Cases", "Cross-Case Alerts",
    ])

    with sub_active:
        saved = load_watchlist()
        is_saved = any(c.get("case_id") == d.get("case_id") for c in saved)

        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(
            f'<div class="pal-card pal-card-accent" style="text-align:center">'
            f'<div style="font-size:.66rem;color:#8C8C8C;text-transform:uppercase;letter-spacing:.05em">Case</div>'
            f'<div style="font-size:.95rem;font-weight:600;color:#F0F0F0;margin-top:6px;'
            f'font-family:JetBrains Mono,monospace">{d["case_id"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        _dom = d.get("target_domain")
        _target_main = _dom or d["target_ip"]
        _target_sub  = (f'{d["target_ip"]} · {bg.get("city","")} · {bg.get("country","")}'
                        if _dom else f'{bg.get("city","")} · {bg.get("country","")}')
        c2.markdown(
            f'<div class="pal-card" style="text-align:center">'
            f'<div style="font-size:.66rem;color:#8C8C8C;text-transform:uppercase;letter-spacing:.05em">Target</div>'
            f'<div style="font-size:.95rem;font-weight:600;color:#0B88F8;margin-top:6px;'
            f'font-family:JetBrains Mono,monospace;word-break:break-all">{_target_main}</div>'
            f'<div style="font-size:.66rem;color:#8C8C8C">{_target_sub}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        rc = risk_color(int(d["risk_score"]))
        c3.markdown(
            f'<div class="pal-card" style="text-align:center">'
            f'<div style="font-size:.66rem;color:#8C8C8C;text-transform:uppercase;letter-spacing:.05em">Risk</div>'
            f'<div style="font-size:1.5rem;font-weight:600;color:{rc};margin-top:4px">{d["risk_score"]}</div>'
            f'<div style="font-size:.66rem;color:#8C8C8C">/100</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        c4.markdown(
            f'<div class="pal-card" style="text-align:center">'
            f'<div style="font-size:.66rem;color:#8C8C8C;text-transform:uppercase;letter-spacing:.05em">In Watchlist</div>'
            f'<div style="font-size:1.3rem;font-weight:600;'
            f'color:{"#23D18B" if is_saved else "#8C8C8C"};margin-top:6px">'
            f'{"YES" if is_saved else "NO"}</div>'
            f'<div style="font-size:.66rem;color:#8C8C8C">{len(saved)} total saved</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        note = st.text_input(
            "Investigator note (optional)",
            placeholder="e.g. 'Suspected botnet C2 — re-check in 7 days'",
            key="wl_note",
        )
        btn_l, btn_r = st.columns(2)
        if btn_l.button(
            "Update snapshot in watchlist" if is_saved else "Save to watchlist",
            type="primary", use_container_width=True,
        ):
            save_case(d, fp, note=note)
            st.success(f"Saved {d['case_id']} to watchlist.")
            st.rerun()
        if btn_r.button("Remove from watchlist",
                        use_container_width=True, disabled=not is_saved):
            delete_case(d["case_id"])
            st.warning(f"Removed {d['case_id']} from watchlist.")
            st.rerun()

        st.caption(f"Watchlist file: `{WATCHLIST_FILE}`")

    with sub_saved:
        saved = load_watchlist()
        if not saved:
            st.markdown(
                '<div class="pal-card">'
                '<div style="color:#8C8C8C;font-size:.84rem;text-align:center;padding:24px">'
                'No saved cases yet. Save the active investigation from the first sub-tab.'
                '</div></div>',
                unsafe_allow_html=True,
            )
        else:
            df = pd.DataFrame(saved)
            for col in ("target_domain", "note"):
                if col not in df.columns:
                    df[col] = ""
            df = df[
                ["case_id", "target_domain", "target_ip", "city", "country",
                 "isp", "risk_score", "saved_at", "note"]
            ].rename(columns={
                "case_id": "Case", "target_domain": "Domain",
                "target_ip": "Target IP", "city": "City", "country": "Country",
                "isp": "ISP", "risk_score": "Risk", "saved_at": "Saved", "note": "Note",
            })
            st.dataframe(df, use_container_width=True, hide_index=True, height=320)

            col_a, col_b = st.columns([3, 1])
            with col_a:
                del_id = st.selectbox(
                    "Delete a case",
                    options=[""] + [c["case_id"] for c in saved],
                    key="wl_del_select",
                )
            with col_b:
                st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
                if st.button("Delete", disabled=not del_id, use_container_width=True):
                    delete_case(del_id)
                    st.success(f"Deleted {del_id}.")
                    st.rerun()

            with st.expander("Danger zone"):
                if st.button("Clear entire watchlist", type="primary"):
                    clear_watchlist()
                    st.warning("Watchlist cleared.")
                    st.rerun()

    with sub_alerts:
        threshold = st.slider(
            "Fingerprint similarity threshold",
            min_value=0.70, max_value=0.99, value=0.85, step=0.01,
            help="Cosine similarity over the 12-D behavioural fingerprint. Higher = stricter match.",
        )
        risk_thresh = st.slider(
            "Saved-case risk alert threshold",
            min_value=40, max_value=95, value=70, step=5,
        )
        alerts = alerts_for(d, fp, sim_threshold=threshold, risk_threshold=risk_thresh)

        if not alerts:
            st.markdown(
                '<div class="pal-card pal-card-green">'
                '<b style="color:#23D18B">All clear.</b>'
                '<div style="color:#8C8C8C;font-size:.78rem;margin-top:4px">'
                'No saved case crosses either alert threshold for this investigation.'
                '</div></div>',
                unsafe_allow_html=True,
            )
        else:
            SEV = {"high": "#F14C4C", "medium": "#F5A623", "low": "#3DA5FF"}
            for a in alerts:
                color = SEV.get(a["severity"], "#8C8C8C")
                kind_label = "FINGERPRINT MATCH" if a["kind"] == "SIM" else "WATCHED HIGH RISK"
                extra = (f'<div style="font-size:.7rem;color:#8C8C8C;margin-top:4px;'
                         f'font-family:JetBrains Mono,monospace">'
                         f'similarity = {a["similarity"]*100:.1f}%</div>'
                         if a["kind"] == "SIM" else "")
                st.markdown(
                    f'<div class="pal-card" style="border-left:2px solid {color}">'
                    f'<div style="display:flex;gap:10px;align-items:center;margin-bottom:6px">'
                    f'<span style="background:{color}1F;color:{color};padding:1px 7px;'
                    f'border-radius:2px;font-size:.6rem;font-weight:600;letter-spacing:.06em">'
                    f'{a["severity"].upper()}</span>'
                    f'<span style="color:#F0F0F0;font-weight:600;font-size:.85rem">{kind_label}</span>'
                    f'<span style="color:#8C8C8C;font-size:.7rem;margin-left:auto;'
                    f'font-family:JetBrains Mono,monospace">{a["case_id"]} · {a["target_ip"]}</span>'
                    f'</div>'
                    f'<div style="color:#F0F0F0;font-size:.82rem">{a["summary"]}</div>'
                    f'{extra}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

# ──────────────────────────────────────────────────────────────────────────────
# 3. WARGAME
# ──────────────────────────────────────────────────────────────────────────────
with main_wg:
    st.caption(
        "Game-theoretic defender / attacker simulation · Equilibrium budget allocation · Not in Palantir"
    )

    threat_band = st.session_state.get(f"ti_enrichment_{ip}", {}).get("band", "MEDIUM")

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

    norm = {k: v / total for k, v in allocation.items()}
    st.caption(
        f"Raw sum = {total:.2f}. Normalised allocation: "
        f"DETECT {norm['DETECT']*100:.0f}% · HARDEN {norm['HARDEN']*100:.0f}% · "
        f"DECEIVE {norm['DECEIVE']*100:.0f}% · Threat band: {threat_band}"
    )

    result = run_wargame(fp, allocation, threat_band=threat_band)

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

    sub_matrix, sub_priors, sub_sweep, sub_explain = st.tabs([
        "Payoff Matrix", "Attacker Priors", "Allocation Sweep", "Recommendation",
    ])

    with sub_matrix:
        z = [[result.payoff[(ds, atk)] for atk in ATTACKER_STRATS] for ds in DEFENDER_STRATS]
        fig = go.Figure(go.Heatmap(
            z=z, x=ATTACKER_STRATS, y=DEFENDER_STRATS,
            colorscale=[[0, "#23D18B"], [0.5, "#F5A623"], [1, "#F14C4C"]],
            text=[[f"{v:.1f}" for v in row] for row in z],
            texttemplate="%{text}",
            textfont={"size": 13, "color": "#FFFFFF"},
            hovertemplate="Defender %{y} vs Attacker %{x}<br>Loss: %{z}<extra></extra>",
            colorbar=dict(title=dict(text="Loss", font=dict(color="#8C8C8C", size=10)),
                          tickfont=dict(color="#8C8C8C")),
        ))
        fig.update_layout(xaxis_title="Attacker strategy", yaxis_title="Defender strategy")
        themed(fig, height=320)
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            "Each cell is the defender's expected loss (0–100) when the defender's "
            "*entire* budget is on the row strategy and the attacker plays the "
            "column strategy. Greener = better for the defender."
        )

        rows = []
        for ds in DEFENDER_STRATS:
            atk = result.attacker_best_response[ds]
            rows.append({
                "Defender pure strategy": ds,
                "Attacker best response": atk,
                "Resulting loss":         result.payoff[(ds, atk)],
                "Expected loss vs prior": result.expected_loss[ds],
            })
        st.markdown('<div class="section-hdr">Attacker Best-Response Table</div>',
                    unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    with sub_priors:
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

        st.markdown('<div class="section-hdr">How These Priors Are Built</div>',
                    unsafe_allow_html=True)
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

    with sub_sweep:
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

    with sub_explain:
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
