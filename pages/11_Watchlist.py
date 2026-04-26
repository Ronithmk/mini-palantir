"""
Watchlist & multi-case management.
Save, compare, and alert across investigations.
"""
import streamlit as st
import pandas as pd
from core.state import inject_theme, require_data, themed, risk_color
from core.predictor import build_fingerprint
from core.watchlist import (
    save_case, load_watchlist, delete_case, clear_watchlist,
    find_matches, alerts_for, WATCHLIST_FILE,
)

st.set_page_config(page_title="Watchlist · ARGUS", page_icon="📌", layout="wide")
inject_theme()
d = require_data()

adf   = d["anomaly_df"]
stats = d["cluster_stats"]
bg    = d["base_geo"]

st.markdown(
    '<div style="font-size:1.1rem;font-weight:600;color:#F0F0F0;margin-bottom:3px;">Watchlist & Case Management</div>'
    '<div style="font-size:.75rem;color:#8C8C8C;margin-bottom:18px;">'
    'Save investigations · Cross-case fingerprint matching · Risk alerts</div>',
    unsafe_allow_html=True,
)

fp = build_fingerprint(adf, stats)

tab_active, tab_saved, tab_alerts = st.tabs([
    "Active Investigation", "Saved Cases", "Cross-Case Alerts",
])

# ── Tab: Active Investigation ─────────────────────────────────────────────────
with tab_active:
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
    c2.markdown(
        f'<div class="pal-card" style="text-align:center">'
        f'<div style="font-size:.66rem;color:#8C8C8C;text-transform:uppercase;letter-spacing:.05em">Target</div>'
        f'<div style="font-size:.95rem;font-weight:600;color:#0B88F8;margin-top:6px;'
        f'font-family:JetBrains Mono,monospace">{d["target_ip"]}</div>'
        f'<div style="font-size:.66rem;color:#8C8C8C">{bg.get("city","")} · {bg.get("country","")}</div>'
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

# ── Tab: Saved Cases ──────────────────────────────────────────────────────────
with tab_saved:
    saved = load_watchlist()
    if not saved:
        st.markdown(
            '<div class="pal-card">'
            '<div style="color:#8C8C8C;font-size:.84rem;text-align:center;padding:24px">'
            'No saved cases yet. Save the active investigation from the first tab.'
            '</div></div>',
            unsafe_allow_html=True,
        )
    else:
        df = pd.DataFrame(saved)[
            ["case_id", "target_ip", "city", "country", "isp", "risk_score", "saved_at", "note"]
        ].rename(columns={
            "case_id": "Case", "target_ip": "Target IP", "city": "City",
            "country": "Country", "isp": "ISP", "risk_score": "Risk",
            "saved_at": "Saved", "note": "Note",
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

# ── Tab: Alerts ───────────────────────────────────────────────────────────────
with tab_alerts:
    threshold = st.slider(
        "Fingerprint similarity threshold",
        min_value=0.70, max_value=0.99, value=0.85, step=0.01,
        help="Cosine similarity over the 12-D behavioural fingerprint. "
             "Higher = stricter match.",
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
