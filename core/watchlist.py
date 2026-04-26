"""
Watchlist & multi-case management.

Persists a slim summary of every investigation to ~/.argus/watchlist.json so
investigations survive a Streamlit restart. Provides:

- save_case()         — snapshot the current investigation
- load_watchlist()    — read all saved cases
- delete_case()       — remove one
- find_matches()      — cosine-similarity search across saved fingerprints
- alerts_for()        — flag cases that share a behavioural fingerprint with
                        the active investigation above a configurable threshold

The fingerprint reuse here is what makes this *not* a per-IP database — two
different IPs that produce a similar 12-D behavioural vector are surfaced as
"likely same operator" alerts.
"""
from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path

WATCHLIST_DIR  = Path.home() / ".argus"
WATCHLIST_FILE = WATCHLIST_DIR / "watchlist.json"


def _ensure_dir() -> None:
    WATCHLIST_DIR.mkdir(parents=True, exist_ok=True)


def _read() -> list[dict]:
    if not WATCHLIST_FILE.exists():
        return []
    try:
        return json.loads(WATCHLIST_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _write(cases: list[dict]) -> None:
    _ensure_dir()
    WATCHLIST_FILE.write_text(
        json.dumps(cases, indent=2, default=str),
        encoding="utf-8",
    )


# ── Public API ────────────────────────────────────────────────────────────────
def load_watchlist() -> list[dict]:
    return _read()


def save_case(d: dict, fingerprint: dict, note: str = "") -> dict:
    """Snapshot the active investigation into the watchlist.

    `d` is the session-state investigation dict (`get_data()` payload).
    `fingerprint` is the output of `predictor.build_fingerprint()`.
    """
    cases = _read()
    bg = d.get("base_geo", {}) or {}

    case = {
        "case_id":     d.get("case_id"),
        "target_ip":   d.get("target_ip"),
        "saved_at":    datetime.now().isoformat(timespec="seconds"),
        "city":        bg.get("city", ""),
        "country":     bg.get("country", ""),
        "isp":         bg.get("isp", ""),
        "org":         bg.get("org", ""),
        "risk_score":  int(d.get("risk_score", 0)),
        "fingerprint": list(fingerprint.get("values", [])),
        "fp_labels":   list(fingerprint.get("labels", [])),
        "note":        note.strip(),
    }

    # If the case_id is already saved, replace it (latest snapshot wins).
    cases = [c for c in cases if c.get("case_id") != case["case_id"]]
    cases.append(case)
    _write(cases)
    return case


def delete_case(case_id: str) -> None:
    cases = [c for c in _read() if c.get("case_id") != case_id]
    _write(cases)


def clear_watchlist() -> None:
    _write([])


# ── Similarity ────────────────────────────────────────────────────────────────
def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na  = math.sqrt(sum(x * x for x in a))
    nb  = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def find_matches(fingerprint: list[float], exclude_case_id: str | None = None,
                 threshold: float = 0.85) -> list[dict]:
    """Return saved cases whose fingerprint cosine-similarity ≥ threshold."""
    matches = []
    for c in _read():
        if exclude_case_id and c.get("case_id") == exclude_case_id:
            continue
        sim = _cosine(fingerprint, c.get("fingerprint", []))
        if sim >= threshold:
            matches.append({**c, "similarity": round(sim, 4)})
    matches.sort(key=lambda x: x["similarity"], reverse=True)
    return matches


def alerts_for(d: dict, fingerprint: dict, sim_threshold: float = 0.85,
               risk_threshold: int = 70) -> list[dict]:
    """Build alert rows for the active investigation.

    Two alert classes:
      - SIM     : behavioural fingerprint matches a saved case → likely same operator
      - HIGH_RISK : a saved case has risk ≥ risk_threshold (passive watchlist warning)
    """
    alerts = []
    fp_vals = list(fingerprint.get("values", []))

    for m in find_matches(fp_vals, exclude_case_id=d.get("case_id"),
                          threshold=sim_threshold):
        alerts.append({
            "kind":       "SIM",
            "severity":   "high" if m["similarity"] >= 0.93 else "medium",
            "case_id":    m["case_id"],
            "target_ip":  m["target_ip"],
            "similarity": m["similarity"],
            "summary":    (f"Behavioural fingerprint matches saved case "
                           f"{m['case_id']} ({m['target_ip']}) at "
                           f"{m['similarity']*100:.1f}% similarity"),
        })

    for c in _read():
        if c.get("case_id") == d.get("case_id"):
            continue
        if int(c.get("risk_score", 0)) >= risk_threshold:
            alerts.append({
                "kind":      "HIGH_RISK",
                "severity":  "medium",
                "case_id":   c["case_id"],
                "target_ip": c["target_ip"],
                "summary":   (f"Watchlisted case {c['case_id']} ({c['target_ip']}) "
                              f"is at risk {c['risk_score']}/100"),
            })

    return alerts
