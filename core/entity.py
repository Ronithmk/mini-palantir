"""Entity extraction — no heavy NLP dependencies, pure regex + heuristics."""
import re
from urllib.parse import urlparse

_IP_RE    = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
_EMAIL_RE = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')
_URL_RE   = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]{6,}')
_DATE_RE  = re.compile(r'\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}/\d{1,2}/\d{4}\b')

ORG_SUFFIXES = re.compile(
    r'\b\w[\w\s&,.-]{2,40}'
    r'(?:Ltd|Inc|Corp|LLC|Limited|Company|University|Institute|Ministry|'
    r'Department|Agency|Bureau|Committee|Association|Federation|Union|Group|'
    r'Holdings|Technologies|Solutions|Services|Systems|Networks|Communications|'
    r'Media|Digital|Global|International|National|Regional|Labs|Ventures|Capital)\b',
    re.IGNORECASE,
)

CAT_ICONS = {
    "IP": "🔵", "Location": "🟢", "Organization": "🟣",
    "Zone": "🟠", "Topic": "🟡", "News": "⚪",
    "Social Media": "🔴", "Encyclopedia": "🔷", "Web Search": "🔹",
    "Domain": "🌐", "Email": "📧", "Date": "📅",
}


def _clean(s: str) -> str:
    return " ".join(s.split())


def extract_from_text(text: str) -> list[dict]:
    entities = []
    seen = set()

    def add(etype, value, meta=None):
        key = (etype, value[:60])
        if key in seen:
            return
        seen.add(key)
        entities.append({"type": etype, "value": value, "meta": meta or {}})

    for m in _IP_RE.finditer(text):
        add("IP", m.group())
    for m in _EMAIL_RE.finditer(text):
        add("Email", m.group())
    for m in _DATE_RE.finditer(text):
        add("Date", m.group())
    for m in _URL_RE.finditer(text):
        domain = urlparse(m.group()).netloc
        if domain:
            add("Domain", domain)
    for m in ORG_SUFFIXES.finditer(text):
        val = _clean(m.group())
        if len(val) > 4:
            add("Organization", val)

    return entities


def build_entity_list(base_geo: dict, cluster_stats, web_items: list, prediction: dict) -> list[dict]:
    entities = []
    seen = set()

    def add(etype, value, confidence=1.0, meta=None, source="geo"):
        key = (etype, str(value)[:60])
        if key in seen:
            return
        seen.add(key)
        entities.append({
            "type": etype,
            "value": value,
            "confidence": confidence,
            "source": source,
            "meta": meta or {},
            "icon": CAT_ICONS.get(etype, "⚫"),
        })

    # ── Geo entities ───────────────────────────────────────────────────────────
    ip = base_geo.get("query", "unknown")
    add("IP", ip, 1.0, {"isp": base_geo.get("isp"), "timezone": base_geo.get("timezone")}, "geo")
    add("Location", f"{base_geo.get('city')}, {base_geo.get('country')}", 1.0,
        {"lat": base_geo.get("lat"), "lon": base_geo.get("lon")}, "geo")
    if base_geo.get("isp"):
        add("Organization", base_geo["isp"], 0.95, {}, "geo")
    if base_geo.get("org") and base_geo["org"] != base_geo.get("isp"):
        add("Organization", base_geo["org"], 0.85, {}, "geo")

    # ── Zone entities ──────────────────────────────────────────────────────────
    for _, row in cluster_stats[cluster_stats["cluster_id"] != -1].iterrows():
        add("Zone", row["label"], round(row["likelihood_pct"] / 100, 2),
            {"city": row["city"], "lat": row["centroid_lat"], "lon": row["centroid_lon"],
             "sessions": row["sessions"], "hours": row["total_hours"]}, "clustering")

    # ── Web entities ───────────────────────────────────────────────────────────
    for item in web_items:
        text = f"{item.get('title','')} {item.get('body','')}"
        add("Organization", item.get("source", ""), 0.7, {}, item.get("category", "web"))
        for ent in extract_from_text(text):
            add(ent["type"], ent["value"], 0.6, ent["meta"], item.get("category", "web"))

    return entities


def compute_risk(base_geo: dict, cluster_stats, anomaly_df, web_items: list) -> tuple[int, list]:
    factors = []
    score = 0

    # Datacenter / hosting IP → higher risk
    org = str(base_geo.get("org", "")).lower()
    isp = str(base_geo.get("isp", "")).lower()
    if any(k in org + isp for k in ["hosting", "cloud", "vps", "vpn", "datacenter", "amazon", "google", "microsoft", "digitalocean", "linode"]):
        score += 20
        factors.append(("Hosting/Cloud IP detected — possible VPN or proxy", "warn"))

    # High remote zone activity
    remote_pct = (cluster_stats[cluster_stats["label"] == "Travel / Remote"]["sessions"].sum()
                  / max(cluster_stats["sessions"].sum(), 1)) * 100
    if remote_pct > 15:
        score += 15
        factors.append((f"High remote-zone activity: {remote_pct:.0f}% of sessions", "warn"))

    # Night-time sessions
    night_pct = (anomaly_df["hour"].between(1, 4).sum() / max(len(anomaly_df), 1)) * 100
    if night_pct > 10:
        score += 10
        factors.append((f"Significant night-time activity (01:00–04:00): {night_pct:.0f}% of sessions", "warn"))

    # Anomaly count
    anom_count = anomaly_df["anomaly"].sum()
    if anom_count > 30:
        score += 15
        factors.append((f"{anom_count} anomalous sessions flagged", "alert"))

    # Web threat keywords
    all_text = " ".join(f"{i.get('title','')} {i.get('body','')}" for i in web_items).lower()
    threat_kw = ["breach", "hack", "malware", "phishing", "ransomware", "attack", "exploit", "vulnerability", "threat", "cyber"]
    hits = [kw for kw in threat_kw if kw in all_text]
    if hits:
        score += min(len(hits) * 5, 25)
        factors.append((f"Threat keywords in intel feed: {', '.join(hits[:5])}", "alert"))

    # Low score bonus
    if score == 0:
        factors.append(("No significant risk indicators detected", "safe"))

    return min(score, 100), factors
