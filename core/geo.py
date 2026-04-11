import requests
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN
import random
from datetime import datetime, timedelta


class GeoAnalyzer:
    _GEO_API = "http://ip-api.com/json/"

    def lookup(self, ip: str) -> dict | None:
        try:
            r = requests.get(f"{self._GEO_API}{ip}", timeout=8)
            d = r.json()
            return d if d.get("status") == "success" else None
        except Exception:
            return None

    # ── Simulate historical sessions ──────────────────────────────────────────
    def generate_history(self, geo: dict, days: int = 45) -> pd.DataFrame:
        blat, blon = geo["lat"], geo["lon"]
        city, country = geo.get("city", "Unknown"), geo.get("country", "Unknown")
        now = datetime.now()
        rows = []

        for _ in range(days * 4):
            ts = now - timedelta(
                days=random.uniform(0, days),
                hours=random.uniform(0, 23),
                minutes=random.uniform(0, 59),
            )
            dur = random.randint(3, 280)
            roll = random.random()

            if roll < 0.76:          # primary zone
                lat = blat + random.gauss(0, 0.035)
                lon = blon + random.gauss(0, 0.035)
                zone, loc = "Primary Zone", city
            elif roll < 0.91:        # secondary zone
                lat = blat + random.gauss(0, 0.35)
                lon = blon + random.gauss(0, 0.35)
                zone, loc = "Secondary Zone", f"Near {city}"
            else:                    # travel / remote
                lat = blat + random.gauss(0, 3.5)
                lon = blon + random.gauss(0, 3.5)
                zone, loc = "Travel / Remote", "Remote"

            rows.append({
                "timestamp": ts,
                "lat": round(lat, 6),
                "lon": round(lon, 6),
                "duration_min": dur,
                "zone_label": zone,
                "city": loc,
                "country": country,
                "hour": ts.hour,
                "weekday": ts.strftime("%A"),
            })

        return pd.DataFrame(rows).sort_values("timestamp").reset_index(drop=True)

    # ── DBSCAN clustering ─────────────────────────────────────────────────────
    def cluster(self, df: pd.DataFrame, eps_km: float = 4.0) -> pd.DataFrame:
        coords = np.radians(df[["lat", "lon"]].values)
        labels = DBSCAN(
            eps=eps_km / 6371.0, min_samples=4,
            algorithm="ball_tree", metric="haversine",
        ).fit_predict(coords)
        out = df.copy()
        out["cluster"] = labels
        return out

    # ── Cluster statistics ────────────────────────────────────────────────────
    def cluster_stats(self, df: pd.DataFrame) -> pd.DataFrame:
        now = datetime.now()
        rows = []
        for cid in sorted(df["cluster"].unique()):
            sub = df[df["cluster"] == cid]
            last = sub["timestamp"].max()
            days_ago = (now - last).total_seconds() / 86400
            recency = max(0.0, 1.0 - days_ago / 45)
            freq = len(sub) / max(len(df), 1)
            likelihood = round((recency * 0.60 + freq * 0.40) * 100, 1)
            rows.append({
                "cluster_id": cid,
                "label": "Noise" if cid == -1 else f"Zone {cid + 1}",
                "city": sub["city"].mode().iloc[0],
                "country": sub["country"].mode().iloc[0],
                "centroid_lat": round(sub["lat"].mean(), 5),
                "centroid_lon": round(sub["lon"].mean(), 5),
                "sessions": len(sub),
                "total_hours": round(sub["duration_min"].sum() / 60, 2),
                "avg_duration_min": round(sub["duration_min"].mean(), 1),
                "first_seen": sub["timestamp"].min().strftime("%Y-%m-%d %H:%M"),
                "last_seen": last.strftime("%Y-%m-%d %H:%M"),
                "likelihood_pct": likelihood,
                "recency": round(recency, 3),
                "freq": round(freq, 3),
            })
        return (
            pd.DataFrame(rows)
            .sort_values("likelihood_pct", ascending=False)
            .reset_index(drop=True)
        )

    # ── Predicted current location ────────────────────────────────────────────
    def predict(self, stats: pd.DataFrame) -> dict | None:
        valid = stats[stats["cluster_id"] != -1]
        if valid.empty:
            return None
        t = valid.iloc[0]
        return {
            "lat": t["centroid_lat"], "lon": t["centroid_lon"],
            "city": t["city"], "country": t["country"],
            "confidence": t["likelihood_pct"], "zone": t["label"],
            "sessions": t["sessions"], "total_hours": t["total_hours"],
        }

    # ── Anomaly detection ─────────────────────────────────────────────────────
    def detect_anomalies(self, df: pd.DataFrame) -> pd.DataFrame:
        """Flag sessions: odd hours, remote zone, very long/short sessions."""
        adf = df.copy()
        adf["anomaly"] = False
        adf["anomaly_reason"] = ""

        night_mask = adf["hour"].between(1, 4)
        adf.loc[night_mask, "anomaly"] = True
        adf.loc[night_mask, "anomaly_reason"] += "night-session "

        remote_mask = adf["zone_label"] == "Travel / Remote"
        adf.loc[remote_mask, "anomaly"] = True
        adf.loc[remote_mask, "anomaly_reason"] += "remote-location "

        p95 = adf["duration_min"].quantile(0.95)
        long_mask = adf["duration_min"] > p95
        adf.loc[long_mask, "anomaly"] = True
        adf.loc[long_mask, "anomaly_reason"] += "long-session "

        return adf
