"""
Threat Intelligence Enrichment.

Pulls signal from free public sources (no API key required) and combines them
into a single threat profile for the target IP:

- Tor exit-node list (dan.me.uk public mirror)
- Cloud / hosting / VPN ASN heuristics from ip-api fields already collected
- Reverse DNS via socket.gethostbyaddr
- Public blocklist heuristics (datacenter ranges, known scanners)
- Inferred risk-band based on combined signal

Caches the Tor list in-process for the session — it's ~7000 lines and
doesn't change often.
"""
from __future__ import annotations

import socket
import time
import requests
from functools import lru_cache

_HEADERS = {"User-Agent": "MiniPalantir/1.0 (research)"}

# Public Tor exit-node list (plain text, one IP per line, refreshed hourly)
TOR_LIST_URL = "https://check.torproject.org/torbulkexitlist"
TOR_FALLBACK_URL = "https://www.dan.me.uk/torlist/?exit"

# Cloud / hosting / VPN keywords used to flag ASN/org strings
CLOUD_KEYWORDS = {
    "amazon", "aws", "google cloud", "googlecloud", "gcp", "microsoft azure",
    "azure", "digitalocean", "linode", "ovh", "hetzner", "vultr", "scaleway",
    "alibaba cloud", "tencent", "oracle cloud", "rackspace",
}
VPN_KEYWORDS = {
    "vpn", "proxy", "nordvpn", "expressvpn", "surfshark", "mullvad",
    "private internet access", "pia", "torguard", "ipvanish", "windscribe",
    "protonvpn", "cyberghost", "hidemyass",
}
HOSTING_KEYWORDS = {
    "hosting", "datacenter", "data center", "server", "vps", "dedicated",
    "colocation", "colo",
}
ANON_KEYWORDS = {"tor", "anonymous", "anon", "hide", "shadowsocks"}


# ── Tor exit list ─────────────────────────────────────────────────────────────
@lru_cache(maxsize=1)
def _load_tor_exit_set() -> frozenset[str]:
    """Fetch the Tor exit-node list once per process; return as a frozenset."""
    for url in (TOR_LIST_URL, TOR_FALLBACK_URL):
        try:
            r = requests.get(url, headers=_HEADERS, timeout=8)
            if r.status_code == 200 and r.text:
                ips = {
                    line.strip()
                    for line in r.text.splitlines()
                    if line.strip() and not line.strip().startswith("#")
                }
                if ips:
                    return frozenset(ips)
        except Exception:
            continue
    return frozenset()


def is_tor_exit(ip: str) -> bool:
    return ip.strip() in _load_tor_exit_set()


def tor_list_size() -> int:
    return len(_load_tor_exit_set())


# ── Reverse DNS ───────────────────────────────────────────────────────────────
def reverse_dns(ip: str) -> str | None:
    try:
        host, _, _ = socket.gethostbyaddr(ip)
        return host
    except Exception:
        return None


# ── ASN / org classification ──────────────────────────────────────────────────
def classify_asn(base_geo: dict) -> dict:
    """Categorise the ASN/org/ISP fields into infrastructure tags."""
    blob = " ".join(
        str(base_geo.get(k, "")).lower()
        for k in ("isp", "org", "as", "asname")
    )

    tags = []
    if any(k in blob for k in CLOUD_KEYWORDS):
        tags.append("CLOUD")
    if any(k in blob for k in VPN_KEYWORDS):
        tags.append("VPN")
    if any(k in blob for k in HOSTING_KEYWORDS):
        tags.append("HOSTING")
    if any(k in blob for k in ANON_KEYWORDS):
        tags.append("ANONYMIZER")

    is_residential = not tags
    return {
        "tags": tags,
        "is_residential": is_residential,
        "is_infrastructure": bool(tags),
        "raw": blob.strip(),
    }


# ── Combined enrichment ───────────────────────────────────────────────────────
def enrich(ip: str, base_geo: dict) -> dict:
    """Run every enrichment source and return a combined profile dict."""
    started = time.time()

    tor_hit  = is_tor_exit(ip)
    tor_size = tor_list_size()
    rdns     = reverse_dns(ip)
    asn      = classify_asn(base_geo)

    signals: list[tuple[str, str, str]] = []  # (severity, label, detail)

    if tor_hit:
        signals.append(("critical", "Tor Exit Node",
                        f"IP appears in the public Tor exit-node list ({tor_size} entries checked)"))
    if "ANONYMIZER" in asn["tags"]:
        signals.append(("critical", "Anonymizer ASN",
                        f"ASN/org contains anonymization keywords: {asn['raw']}"))
    if "VPN" in asn["tags"]:
        signals.append(("high", "VPN Provider",
                        f"ASN/org matches a known VPN provider"))
    if "HOSTING" in asn["tags"]:
        signals.append(("medium", "Hosting / Datacenter",
                        "Hosted infrastructure — unlikely to be an end-user device"))
    if "CLOUD" in asn["tags"]:
        signals.append(("medium", "Cloud Provider",
                        "Major cloud provider IP — could be a workload, bastion, or proxy"))

    if rdns:
        host_lower = rdns.lower()
        if any(k in host_lower for k in ("vpn", "proxy", "tor", "exit")):
            signals.append(("high", "Suspicious rDNS",
                            f"Reverse DNS contains anonymization keywords: {rdns}"))
        elif any(k in host_lower for k in ("aws", "amazonaws", "googleusercontent",
                                           "azure", "ovh", "hetzner")):
            signals.append(("medium", "Cloud rDNS",
                            f"Reverse DNS resolves to a cloud provider: {rdns}"))

    if not signals:
        signals.append(("clear", "Residential / End-user",
                        "No anonymizer, VPN, hosting, or cloud signals detected"))

    # Threat band
    score = 0
    score += 50 if tor_hit else 0
    score += 35 if "ANONYMIZER" in asn["tags"] else 0
    score += 25 if "VPN" in asn["tags"] else 0
    score += 15 if "HOSTING" in asn["tags"] else 0
    score += 10 if "CLOUD" in asn["tags"] else 0
    score = min(score, 100)

    if score >= 60:
        band = "HIGH"
    elif score >= 25:
        band = "MEDIUM"
    elif score > 0:
        band = "LOW"
    else:
        band = "CLEAR"

    return {
        "ip":           ip,
        "tor_hit":      tor_hit,
        "tor_list_size": tor_size,
        "rdns":         rdns,
        "asn_tags":     asn["tags"],
        "asn_raw":      asn["raw"],
        "is_residential": asn["is_residential"],
        "signals":      signals,
        "score":        score,
        "band":         band,
        "duration_ms":  int((time.time() - started) * 1000),
    }
