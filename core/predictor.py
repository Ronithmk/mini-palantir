"""
Predictive Behavioral Engine — goes beyond Palantir by forecasting future behavior.

Predicts:
- Next likely active location (lat/lon + uncertainty radius)
- Next active time window (hour + day)
- Activity volume forecast (next 7 days)
- Behavioral drift detection (is the pattern changing?)
- Counter-intelligence signals (behavioral irregularities suggesting awareness)
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from datetime import datetime, timedelta


# ── Next active time window ────────────────────────────────────────────────────
def predict_next_window(adf: pd.DataFrame) -> dict:
    """Predict the next most likely active time window."""
    # Weight by recency — recent sessions matter more
    adf = adf.copy().sort_values("timestamp")
    n = len(adf)
    weights = np.linspace(0.5, 1.0, n)

    hour_scores  = np.zeros(24)
    day_scores   = np.zeros(7)
    day_names    = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

    for i, (_, row) in enumerate(adf.iterrows()):
        h = int(row["hour"])
        d = day_names.index(row["weekday"]) if row["weekday"] in day_names else 0
        w = weights[i]
        hour_scores[h]  += row["duration_min"] * w
        day_scores[d]   += row["duration_min"] * w

    hour_prob = hour_scores / hour_scores.sum()
    day_prob  = day_scores  / day_scores.sum()

    # Find next occurrence of peak day/hour from now
    now = datetime.now()
    peak_hour = int(np.argmax(hour_prob))
    peak_day  = int(np.argmax(day_prob))

    # Walk forward to find next window
    candidate = now.replace(minute=0, second=0, microsecond=0)
    for _ in range(7 * 24):
        candidate += timedelta(hours=1)
        if candidate.weekday() == peak_day and candidate.hour == peak_hour:
            break

    return {
        "peak_hour":       peak_hour,
        "peak_day":        day_names[peak_day],
        "next_window":     candidate,
        "hours_until":     round((candidate - now).total_seconds() / 3600, 1),
        "hour_probs":      hour_prob.tolist(),
        "day_probs":       day_prob.tolist(),
        "day_names":       day_names,
        "confidence":      round(float(max(hour_prob)) * float(max(day_prob)) * 100 * 4, 1),
    }


# ── Next likely location ───────────────────────────────────────────────────────
def predict_next_location(cluster_stats: pd.DataFrame, adf: pd.DataFrame) -> dict:
    """Predict the most likely next location with uncertainty radius."""
    valid = cluster_stats[cluster_stats["cluster_id"] != -1].copy()
    if valid.empty:
        return {}

    now = datetime.now()

    # Score each zone: recency + frequency + session density
    rows = []
    for _, z in valid.iterrows():
        last_seen = pd.to_datetime(z["last_seen"])
        days_since = (now - last_seen).total_seconds() / 86400
        recency  = np.exp(-days_since / 14)       # decay over 2 weeks
        freq     = z["sessions"] / max(len(adf), 1)
        duration = z["total_hours"] / max(valid["total_hours"].sum(), 1)
        score    = recency * 0.5 + freq * 0.3 + duration * 0.2
        rows.append({**z.to_dict(), "score": score})

    scored = pd.DataFrame(rows).sort_values("score", ascending=False)
    top = scored.iloc[0]

    # Uncertainty radius: proportional to spread of sessions in that cluster
    zone_sessions = adf[adf["cluster"] == top["cluster_id"]]
    if len(zone_sessions) > 1:
        lat_std = zone_sessions["lat"].std()
        lon_std = zone_sessions["lon"].std()
        radius_km = round(np.sqrt(lat_std**2 + lon_std**2) * 111, 2)
    else:
        radius_km = 2.0

    confidence = round(float(top["score"]) / scored["score"].sum() * 100, 1)

    return {
        "lat":         top["centroid_lat"],
        "lon":         top["centroid_lon"],
        "city":        top["city"],
        "country":     top["country"],
        "zone":        top["label"],
        "confidence":  confidence,
        "radius_km":   radius_km,
        "all_scored":  scored[["label","city","centroid_lat","centroid_lon","score","likelihood_pct"]].head(5),
    }


# ── 7-day activity forecast ────────────────────────────────────────────────────
def forecast_activity(adf: pd.DataFrame, days_ahead: int = 7) -> pd.DataFrame:
    """Forecast daily activity volume for the next N days using weighted moving average."""
    adf = adf.copy()
    adf["date"] = adf["timestamp"].dt.date
    daily = adf.groupby("date")["duration_min"].sum().reset_index()
    daily["hours"] = daily["duration_min"] / 60
    daily["date"]  = pd.to_datetime(daily["date"])
    daily = daily.sort_values("date")

    if len(daily) < 3:
        return pd.DataFrame()

    # Weighted moving average (recent days weighted more)
    values = daily["hours"].values
    n = len(values)
    weights = np.linspace(0.5, 1.0, min(14, n))
    recent = values[-len(weights):]
    wma = float(np.average(recent, weights=weights[-len(recent):]))

    # Day-of-week adjustment factor
    daily["dow"] = daily["date"].dt.dayofweek
    dow_factors = daily.groupby("dow")["hours"].mean()
    overall_mean = daily["hours"].mean()

    forecast_rows = []
    for i in range(1, days_ahead + 1):
        fdate = datetime.now().date() + timedelta(days=i)
        dow = fdate.weekday()
        dow_factor = dow_factors.get(dow, overall_mean) / max(overall_mean, 0.1)
        predicted = max(0, wma * dow_factor)
        # Add uncertainty bands
        std = daily["hours"].std()
        forecast_rows.append({
            "date":    fdate,
            "forecast_hours": round(predicted, 2),
            "lower":          round(max(0, predicted - std * 0.8), 2),
            "upper":          round(predicted + std * 0.8, 2),
            "is_forecast":    True,
        })

    historical = daily[["date","hours"]].copy()
    historical.columns = ["date","forecast_hours"]
    historical["lower"] = historical["forecast_hours"]
    historical["upper"] = historical["forecast_hours"]
    historical["is_forecast"] = False
    historical["date"] = historical["date"].dt.date

    return pd.concat([historical.tail(14), pd.DataFrame(forecast_rows)], ignore_index=True)


# ── Behavioral drift detection ─────────────────────────────────────────────────
def detect_drift(adf: pd.DataFrame, window_days: int = 15) -> dict:
    """
    Compare early vs recent behavior windows.
    Large divergence = behavioral drift (life change or counter-intel awareness).
    """
    adf = adf.copy().sort_values("timestamp")
    cutoff = adf["timestamp"].median()

    early  = adf[adf["timestamp"] <= cutoff]
    recent = adf[adf["timestamp"] >  cutoff]

    if len(early) < 5 or len(recent) < 5:
        return {"drift_detected": False, "score": 0}

    def profile(df):
        return {
            "peak_hour":    df.groupby("hour")["duration_min"].sum().idxmax(),
            "avg_duration": df["duration_min"].mean(),
            "night_pct":    df["hour"].between(1, 4).mean(),
            "remote_pct":   (df["zone_label"] == "Travel / Remote").mean(),
            "weekend_pct":  df["weekday"].isin(["Saturday","Sunday"]).mean(),
        }

    ep = profile(early)
    rp = profile(recent)

    # Compute drift score (0–100)
    diffs = [
        abs(ep["peak_hour"]    - rp["peak_hour"])    / 12,
        abs(ep["avg_duration"] - rp["avg_duration"]) / max(ep["avg_duration"], 1),
        abs(ep["night_pct"]    - rp["night_pct"])    * 3,
        abs(ep["remote_pct"]   - rp["remote_pct"])   * 4,
        abs(ep["weekend_pct"]  - rp["weekend_pct"])  * 2,
    ]
    drift_score = round(min(100, sum(diffs) * 40), 1)

    changes = []
    if abs(ep["peak_hour"] - rp["peak_hour"]) >= 3:
        changes.append(f"Peak activity hour shifted from {ep['peak_hour']:02d}:00 to {rp['peak_hour']:02d}:00")
    if abs(ep["remote_pct"] - rp["remote_pct"]) > 0.05:
        direction = "increased" if rp["remote_pct"] > ep["remote_pct"] else "decreased"
        changes.append(f"Remote zone activity {direction}: {ep['remote_pct']*100:.0f}% → {rp['remote_pct']*100:.0f}%")
    if abs(ep["night_pct"] - rp["night_pct"]) > 0.03:
        direction = "increased" if rp["night_pct"] > ep["night_pct"] else "decreased"
        changes.append(f"Night-time activity {direction}: {ep['night_pct']*100:.0f}% → {rp['night_pct']*100:.0f}%")
    if abs(ep["avg_duration"] - rp["avg_duration"]) > 20:
        direction = "longer" if rp["avg_duration"] > ep["avg_duration"] else "shorter"
        changes.append(f"Sessions became {direction}: {ep['avg_duration']:.0f}min → {rp['avg_duration']:.0f}min")

    return {
        "drift_detected": drift_score > 25,
        "drift_score":    drift_score,
        "early_profile":  ep,
        "recent_profile": rp,
        "changes":        changes,
        "early_period":   f"{early['timestamp'].min().strftime('%b %d')} – {early['timestamp'].max().strftime('%b %d')}",
        "recent_period":  f"{recent['timestamp'].min().strftime('%b %d')} – {recent['timestamp'].max().strftime('%b %d')}",
    }


# ── Counter-intelligence signal detection ──────────────────────────────────────
def detect_counter_intel(adf: pd.DataFrame, base_geo: dict) -> dict:
    """
    Detect signals that suggest the target may be counter-intelligence aware:
    - Sudden shift to remote zones after regular primary-zone activity
    - Irregular session timing (deliberately random = TCSEC-aware)
    - Use of known hosting/cloud ISPs (VPN indicators)
    - Activity gaps following high-anomaly periods
    """
    signals = []
    score   = 0

    # 1. VPN / datacenter ISP
    org = str(base_geo.get("org","")).lower()
    isp = str(base_geo.get("isp","")).lower()
    vpn_kw = ["vpn","proxy","hosting","cloud","vps","datacenter","tor","anonymous","hide","private"]
    if any(k in org + isp for k in vpn_kw):
        score += 30
        signals.append(("VPN/proxy infrastructure detected in ISP/org registration", "critical"))

    # 2. Randomised session timing (low autocorrelation in session intervals)
    adf_s = adf.sort_values("timestamp")
    intervals = adf_s["timestamp"].diff().dt.total_seconds().dropna()
    if len(intervals) > 10:
        autocorr = float(intervals.autocorr(lag=1))
        if abs(autocorr) < 0.1:
            score += 20
            signals.append((f"Near-zero timing autocorrelation ({autocorr:.2f}) — sessions appear deliberately randomised", "high"))

    # 3. Sudden jump to remote zones in recent sessions
    recent_remote = (adf.tail(30)["zone_label"] == "Travel / Remote").mean()
    early_remote  = (adf.head(30)["zone_label"] == "Travel / Remote").mean()
    if recent_remote > early_remote + 0.15:
        score += 20
        signals.append((f"Remote zone activity spiked in recent sessions: {early_remote*100:.0f}% → {recent_remote*100:.0f}%", "high"))

    # 4. Activity gaps after high-anomaly periods
    adf_sorted = adf.sort_values("timestamp").copy()
    adf_sorted["date"] = adf_sorted["timestamp"].dt.date
    daily_anom = adf_sorted.groupby("date")["anomaly"].sum()
    if len(daily_anom) > 7:
        high_anom_days = daily_anom[daily_anom > daily_anom.quantile(0.85)].index
        for day in high_anom_days:
            next_day = day + timedelta(days=1)
            if next_day not in daily_anom.index or daily_anom.get(next_day, 0) == 0:
                score += 10
                signals.append((f"Activity gap detected after high-anomaly day ({day})", "medium"))
                break

    # 5. Inconsistent timezone-to-location match
    tz = base_geo.get("timezone", "")
    country = base_geo.get("country", "")
    if tz and country:
        tz_country = tz.split("/")[0] if "/" in tz else ""
        known_mismatches = [
            ("America", "Russia"), ("Europe", "China"), ("Asia", "United States"),
            ("America", "United Arab Emirates"),
        ]
        if any(a in tz and b in country for a, b in known_mismatches):
            score += 15
            signals.append((f"Timezone ({tz}) inconsistent with registered country ({country})", "high"))

    if not signals:
        signals.append(("No counter-intelligence signals detected", "clear"))

    return {
        "ci_score":   min(score, 100),
        "ci_level":   "HIGH" if score >= 60 else "MEDIUM" if score >= 30 else "LOW",
        "signals":    signals,
    }


# ── Behavioral fingerprint ─────────────────────────────────────────────────────
def build_fingerprint(adf: pd.DataFrame, cluster_stats: pd.DataFrame) -> dict:
    """
    12-dimensional behavioral fingerprint.
    Uniquely identifies a behavioral pattern — can match the same person across IPs.
    """
    valid = cluster_stats[cluster_stats["cluster_id"] != -1]
    day_names = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

    peak_h   = int(adf.groupby("hour")["duration_min"].sum().idxmax())
    peak_d   = adf.groupby("weekday")["duration_min"].sum().idxmax()
    peak_d_n = day_names.index(peak_d) if peak_d in day_names else 0

    primary_pct   = (adf["zone_label"] == "Primary Zone").mean()
    secondary_pct = (adf["zone_label"] == "Secondary Zone").mean()
    remote_pct    = (adf["zone_label"] == "Travel / Remote").mean()
    avg_dur       = adf["duration_min"].mean()
    dur_std       = adf["duration_min"].std()
    night_pct     = adf["hour"].between(1, 4).mean()
    wknd_pct      = adf["weekday"].isin(["Saturday", "Sunday"]).mean()
    anom_rate     = adf["anomaly"].mean()
    sessions_pd   = len(adf) / max(adf["timestamp"].dt.date.nunique(), 1)
    zone_count    = len(valid)

    features = {
        "peak_hour":      peak_h / 23,
        "peak_day":       peak_d_n / 6,
        "primary_zone":   primary_pct,
        "secondary_zone": secondary_pct,
        "remote_zone":    remote_pct,
        "avg_duration":   min(avg_dur / 300, 1),
        "duration_spread":min(dur_std / 150, 1),
        "night_activity": night_pct,
        "weekend_activity":wknd_pct,
        "anomaly_rate":   min(anom_rate * 5, 1),
        "session_density":min(sessions_pd / 10, 1),
        "zone_diversity": min(zone_count / 5, 1),
    }

    return {
        "features":    features,
        "labels":      list(features.keys()),
        "values":      list(features.values()),
        "peak_hour":   peak_h,
        "peak_day":    peak_d,
        "primary_pct": primary_pct,
        "remote_pct":  remote_pct,
        "night_pct":   night_pct,
        "avg_dur":     avg_dur,
        "anom_rate":   anom_rate,
    }
