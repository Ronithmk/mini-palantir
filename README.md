# ARGUS — Advanced Reconnaissance & Geospatial Unified System

A Palantir-inspired open-source intelligence (OSINT) platform built with Python and Streamlit. ARGUS turns a single public IP address into a full intelligence dossier: geospatial clustering, behavioural profiling, entity graphs, AI-powered analysis, and predictive modelling — all running locally with free public APIs and no required API keys (except the optional Claude AI analyst).

---

## Table of Contents

1. [Overview](#overview)
2. [Feature Map](#feature-map)
3. [Architecture](#architecture)
4. [Tech Stack](#tech-stack)
5. [File Structure](#file-structure)
6. [Data Flow](#data-flow)
7. [Pages Reference](#pages-reference)
8. [Core Modules](#core-modules)
9. [Setup & Installation](#setup--installation)
10. [API Keys](#api-keys)
11. [Deployment](#deployment)
12. [Free Data Sources](#free-data-sources)
13. [Design System](#design-system)

---

## Overview

ARGUS accepts a public IPv4 address and an optional intelligence query. It then:

1. Resolves the IP to a real-world location via ip-api.com
2. Simulates a multi-week session history using realistic spatial noise (DBSCAN clusters)
3. Fetches open-source intelligence from Wikipedia, Reddit, Google News, and DuckDuckGo
4. Clusters web content into topic groups using TF-IDF + KMeans
5. Extracts entities (IPs, emails, URLs, organisations) from all text
6. Scores risk via heuristic rules, builds an entity relationship graph
7. Presents everything across 9 specialised analysis pages

The platform is entirely free to run. The only optional paid component is the ARIA AI Analyst, which requires an Anthropic API key.

---

## Feature Map

| # | Page | What it does |
|---|------|-------------|
| Home | Investigation Launcher | IP input, sample presets, activity history config, launches the full pipeline |
| 1 | Overview | Risk gauge, zone table, entity roster, predicted location, intel source breakdown |
| 2 | Geo Intelligence | Interactive Folium map with DBSCAN zone markers, connection lines, movement trail, zone cards with sparklines |
| 3 | Link Analysis | NetworkX entity relationship graph rendered with Plotly, adjacency table |
| 4 | Pattern of Life | Activity heatmaps (weekday × hour), daily timeline, duration distributions, calendar heatmap, behavioural profile card |
| 5 | Intel Feed | Searchable/filterable table of all fetched web items, TF-IDF topic cluster scatter plot |
| 6 | Report | One-click printable PDF-style investigation dossier with all findings |
| 7 | AI Analyst | ARIA — Claude claude-sonnet-4-6 powered chat analyst with auto-generated briefing and hypothesis engine |
| 8 | Predictive | Next active time window forecast, 7-day activity volume forecast, behavioural drift detection, counter-intelligence signal detector |
| 9 | Fingerprint | 12-dimensional behavioural identity vector, radar chart, target comparison with cosine similarity, fingerprint decoder |

---

## Architecture

```
User Input (IP + query)
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                         app.py  (Home)                          │
│  GeoAnalyzer.lookup()  →  base_geo (lat, lon, city, ISP …)     │
│  GeoAnalyzer.generate_history()  →  180 simulated sessions      │
│  GeoAnalyzer.cluster()  →  DBSCAN spatial clusters              │
│  GeoAnalyzer.cluster_stats()  →  zone summaries + zone types    │
│  GeoAnalyzer.predict()  →  most likely current location         │
│  GeoAnalyzer.detect_anomalies()  →  IQR anomaly flags           │
│  IntelFetcher.fetch_all()  →  Wikipedia + Reddit + News + DDG   │
│  TextClusterer  →  TF-IDF + KMeans topic clusters               │
│  build_entity_list()  →  regex entity extraction                 │
│  compute_risk()  →  heuristic risk score 0–100                  │
│  G_mod.build()  →  NetworkX entity graph                        │
│                                                                  │
│  All results stored in st.session_state via set_data()           │
└──────────────────────────┬──────────────────────────────────────┘
                           │  st.session_state (shared state)
           ┌───────────────┴───────────────────────────┐
           │                                           │
    ┌──────▼──────┐                           ┌───────▼──────┐
    │  9 Analysis  │                           │  ARIA Analyst│
    │    Pages     │                           │  (Claude API)│
    └─────────────┘                           └──────────────┘
```

---

## Tech Stack

| Layer | Library | Purpose |
|-------|---------|---------|
| Web framework | Streamlit ≥1.32 | Multipage app, UI widgets, session state |
| Charting | Plotly ≥5.18 | All interactive charts (heatmaps, bar, scatter, radar, gauge, area) |
| Mapping | Folium + streamlit-folium | Interactive Leaflet.js geo map |
| Spatial clustering | scikit-learn DBSCAN | Session clustering with haversine metric, 4 km eps |
| Text clustering | scikit-learn TF-IDF + KMeans + TruncatedSVD | Topic group detection from web text |
| ML forecasting | scikit-learn GradientBoostingRegressor, RandomForestClassifier | Activity volume forecast, next-window prediction |
| Graph analysis | NetworkX | Entity relationship graph construction |
| Data manipulation | pandas, numpy | DataFrames, numerical operations |
| Web requests | requests | ip-api.com, Wikipedia, Reddit, DuckDuckGo |
| RSS parsing | feedparser | Google News RSS feed |
| AI analyst | anthropic SDK | Claude claude-sonnet-4-6 (ARIA) |
| Font rendering | Inter + JetBrains Mono (Google Fonts) | UI typography |

---

## File Structure

```
mini_palantir/
│
├── app.py                      # Home page — investigation launcher
│
├── pages/
│   ├── 1_Overview.py           # Risk score, zone table, entity roster
│   ├── 2_Geo_Intelligence.py   # Folium map, zone cards, movement trail
│   ├── 3_Link_Analysis.py      # Entity relationship graph
│   ├── 4_Pattern_of_Life.py    # Behavioural heatmaps and timeline
│   ├── 5_Intel_Feed.py         # Web intelligence feed and topic clusters
│   ├── 6_Report.py             # Printable investigation report
│   ├── 7_AI_Analyst.py         # ARIA — Claude-powered chat analyst
│   ├── 8_Predictive.py         # Forecasts, drift detection, CI signals
│   └── 9_Fingerprint.py        # 12D behavioural identity fingerprint
│
├── core/
│   ├── __init__.py
│   ├── state.py                # CSS theme, Plotly defaults, session state helpers
│   ├── geo.py                  # GeoAnalyzer: IP lookup, session sim, DBSCAN
│   ├── fetcher.py              # IntelFetcher: Wikipedia, Reddit, News, DuckDuckGo
│   ├── clusterer.py            # TextClusterer: TF-IDF + KMeans topic detection
│   ├── entity.py               # Regex entity extraction + heuristic risk scoring
│   ├── graph.py                # NetworkX entity graph builder
│   ├── predictor.py            # Behavioural forecasting, drift detection, CI signals
│   └── ai_analyst.py           # ARIA: Claude API wrapper + context builder
│
└── requirements.txt
```

---

## Data Flow

```
IP Address (e.g. 8.8.8.8)
        │
        ▼
GeoAnalyzer.lookup()
  → ip-api.com REST API
  → { lat, lon, city, country, ISP, org, timezone, … }
        │
        ▼
GeoAnalyzer.generate_history(days=N)
  → N×4 simulated sessions with spatial noise:
      76% primary zone  (σ ≈ 0.035°, ~3 km)
      15% secondary     (σ ≈ 0.35°,  ~35 km)
       9% remote/travel (σ ≈ 3.5°,   ~350 km)
  → DataFrame: timestamp, lat, lon, duration_min, hour, weekday, zone_label
        │
        ▼
GeoAnalyzer.cluster()
  → DBSCAN(eps=0.04° ≈ 4 km, min_samples=4, metric=haversine)
  → Adds: cluster_id, zone_label (DBSCAN label), centroid_lat/lon
        │
        ├─→ GeoAnalyzer.cluster_stats()
        │     → Per-cluster summary: sessions, total_hours, likelihood_pct
        │     → zone_type: PRIMARY / SECONDARY / TRANSIT / NOISE
        │     → active_window: e.g. "Evening 18:00–21:00"
        │     → spark_data: 24-bin hourly duration array
        │
        ├─→ GeoAnalyzer.predict()
        │     → Highest-likelihood zone → predicted current location
        │
        └─→ GeoAnalyzer.detect_anomalies()
              → IQR-based duration outliers → anomaly boolean column
        │
        ▼
IntelFetcher.fetch_all(query)
  → Wikipedia search + article summary
  → Reddit search (JSON API, r/all)
  → Google News RSS via feedparser
  → DuckDuckGo Instant Answer API
  → Combined list of { title, summary, url, category, source }
        │
        ▼
TextClusterer(n_clusters=K)
  → TF-IDF (max 400 features, 1–2 ngrams, English stop words)
  → TruncatedSVD (40 components) for dimensionality reduction
  → KMeans clustering → topic label from top 3 TF-IDF terms
  → 2D SVD for scatter plot coordinates
        │
        ▼
build_entity_list() + compute_risk()
  → Regex extraction: IPs, emails, URLs, dates, org suffixes
  → Risk score 0–100 with factor breakdown
        │
        ▼
G_mod.build() — NetworkX graph
  → Nodes: target IP, city, country, ISP, org, topic clusters, entities
  → Edges: typed relationships (LOCATED_IN, OPERATED_BY, TOPIC_IN, …)
        │
        ▼
set_data() → st.session_state
  → All 9 analysis pages read from here via get_data()
```

---

## Pages Reference

### Home — Investigation Launcher

- **Target IP field**: any public IPv4 address
- **Intelligence Query**: optional keyword (defaults to `city country` from geo lookup)
- **Activity History slider**: 10–90 days of simulated sessions
- **Topic Clusters slider**: 3–10 KMeans clusters for web content
- **Sample presets**: Google DNS (8.8.8.8), Cloudflare (1.1.1.1), OpenDNS (208.67.222.222), Microsoft (13.107.42.14)
- Launches the full pipeline with a progress status panel

### Page 1 — Overview

Key metrics row: sessions, clustered sessions, total active hours, zones found, intel items, entities.

- **Risk Gauge**: Plotly indicator, 0–100 with colour zones (green/orange/red)
- **Predicted Location**: highest-likelihood zone centroid with confidence bar
- **Target Profile**: IP, city, region, country, ISP, org, timezone, lat/lon
- **Activity Zones table**: all non-noise DBSCAN clusters with sessions, hours, last seen
- **Entity Roster**: top 20 extracted entities with type and confidence
- **Intel Source Breakdown**: bar chart of items per source (Wikipedia, Reddit, News, DuckDuckGo)

### Page 2 — Geo Intelligence

- **Folium map** with OpenStreetMap tiles
  - Circle markers per DBSCAN cluster, coloured by zone type (blue/amber/purple/grey)
  - Session dots coloured by zone type, sized by duration
  - PolyLines from each zone centroid to predicted location
  - Dashed yellow movement trail (last 20 sessions)
- **Zone cards** in sidebar: zone type badge, sparkline SVG (24-bin hourly activity), active window, frequency, first/last seen

### Page 3 — Link Analysis

- NetworkX graph with Plotly Scatter — nodes sized by degree centrality
- Edge type legend: LOCATED_IN, OPERATED_BY, TOPIC_RELATES_TO, ENTITY_IN, etc.
- Adjacency table: all edges with source, target, relationship type

### Page 4 — Pattern of Life

Tabs: **Heatmap** | **Timeline** | **Duration Analysis** | **Calendar**

- Weekday × hour heatmap (total active minutes)
- Hourly bar chart with peak-hour marker
- Zone × hour heatmap
- Daily area chart by zone type
- Daily anomaly count bar chart
- Session duration histogram with median + IQR band
- Duration boxplot by zone
- Calendar density heatmap
- **Behavioural profile card**: schedule type, weekend pattern, night activity level, primary zone, anomaly count

### Page 5 — Intel Feed

- Searchable, filterable table of all fetched items (title, summary, source, category)
- Topic cluster scatter plot: 2D TF-IDF projection coloured by cluster
- Topic label legend (top 3 keywords per cluster)

### Page 6 — Report

Structured dossier output:

- Case metadata (case ID, timestamp, target IP)
- Executive summary
- Risk assessment with factors
- Zone inventory
- Entity roster
- Intel items by source
- Behavioural profile summary
- Print-friendly layout

### Page 7 — AI Analyst (ARIA)

Requires Anthropic API key entered in the sidebar.

- **Auto-briefing**: full structured intelligence brief generated on load
- **Chat interface**: freeform analyst conversation with full investigation context
- **4 quick questions**: Threat assessment, Predict next move, Counter-intelligence exposure, Likely identity profile
- **Hypothesis engine**: takes a user observation, returns scored hypotheses

Context sent to Claude includes: IP, geo, zone stats, risk factors, anomaly rate, web intel topics, entity list, behavioural profile.

### Page 8 — Predictive

- **Next active window**: hour + day probability bars based on recency-weighted session history
- **7-day activity forecast**: GradientBoostingRegressor trained on rolling session counts
- **Behavioural drift detection**: compares early vs recent session profiles; drift score 0–100
- **Counter-intelligence signals**: VPN detection, activity gap analysis, session timing autocorrelation, remote zone spikes

### Page 9 — Fingerprint

- **12-dimensional feature vector** (all values 0–1, normalised):
  - `peak_hour`, `peak_day`, `primary_zone`, `secondary_zone`, `remote_zone`
  - `avg_duration`, `duration_spread`, `night_activity`, `weekend_activity`
  - `anomaly_rate`, `session_density`, `zone_diversity`
- **Radar chart**: visual fingerprint
- **Fingerprint hash**: `FP-XXXXXXXX` deterministic 8-char hex from feature values
- **Compare Targets tab**: adjustable sliders for a simulated second target, cosine similarity score, LIKELY SAME INDIVIDUAL / POSSIBLE MATCH / DIFFERENT INDIVIDUALS verdict
- **Fingerprint Decoder tab**: plain-English interpretation of each high/low dimension

---

## Core Modules

### `core/state.py`

Centralises all shared UI code.

- `THEME_CSS` — full Palantir Foundry dark theme (Inter + JetBrains Mono fonts)
- `inject_theme()` — call at top of every page to apply CSS
- `PLOTLY_BASE` — shared Plotly layout defaults (dark background, gridlines, font)
- `themed(fig, title, height)` — applies PLOTLY_BASE to any figure
- `set_data(d)` / `get_data()` — write/read the investigation dict from session state
- `require_data()` — like `get_data()` but redirects to home if no investigation is active
- `metric_html(val, label, sub)` — renders a styled metric tile
- `risk_color(score)` — returns `#F14C4C / #F5A623 / #23D18B` for score ranges
- `zone_type_badge(zone_type)` — coloured HTML badge for PRIMARY/SECONDARY/TRANSIT/NOISE
- `sparkline_svg(data, color, width, height)` — 24-bin inline SVG bar sparkline
- `LIVE_CLOCK_HTML` — JavaScript live clock in IST, shown in sidebar
- `ZONE_TYPE_COLOR` — dict mapping zone types to hex colours

### `core/geo.py` — `GeoAnalyzer`

| Method | Description |
|--------|-------------|
| `lookup(ip)` | GET ip-api.com/json/{ip}, returns dict or None |
| `generate_history(geo, days)` | Simulates N×4 sessions with 3-tier spatial distribution |
| `cluster(df)` | DBSCAN(eps=0.04, min_samples=4, haversine) → cluster_id + labels |
| `cluster_stats(clustered_df)` | Per-cluster: centroid, sessions, hours, likelihood, zone_type, spark_data, active_window, frequency |
| `predict(stats)` | Picks highest-likelihood non-noise zone as predicted location |
| `detect_anomalies(clustered_df)` | IQR on duration_min; sessions >Q3+1.5×IQR flagged as anomaly |

### `core/fetcher.py` — `IntelFetcher`

| Method | Source | Notes |
|--------|--------|-------|
| `wikipedia(query)` | Wikipedia REST API | Search endpoint + summary endpoint |
| `reddit(query, limit=20)` | Reddit JSON API | `reddit.com/search.json` |
| `news(query, max_items=25)` | Google News RSS | Parsed via feedparser |
| `duckduckgo(query)` | DuckDuckGo Instant Answer | `api.duckduckgo.com/?format=json` |
| `fetch_all(query)` | All four | Returns combined list of item dicts |

Each item dict: `{ title, summary, url, category, source }`

### `core/clusterer.py` — `TextClusterer`

```
TF-IDF (400 features, 1-2 ngrams)
    → TruncatedSVD (40 components)
    → KMeans (n_clusters)
    → topic label = top 3 terms from cluster centroid
    → 2D coords = separate TruncatedSVD(2) for scatter plot
```

### `core/entity.py`

Regex patterns:
- `_IP_RE` — IPv4 addresses
- `_EMAIL_RE` — email addresses
- `_URL_RE` — http/https URLs
- `_DATE_RE` — common date formats
- `ORG_SUFFIXES` — Inc, Corp, Ltd, LLC, GmbH, etc.

`build_entity_list(base_geo, stats, web_items, pred)` → list of entity dicts with `type`, `value`, `confidence`, `source`

`compute_risk(base_geo, stats, anomdf, web_items)` → `(score: int, factors: list[tuple])`

Risk rules:
| Condition | Points |
|-----------|--------|
| Hosting/cloud ISP keywords | +20 |
| Remote zone activity >20% | +15 |
| High anomaly rate >25% | +15 |
| Night activity >15% | +10 |
| Threat keywords in intel (per keyword, max 25) | +5 each |

### `core/graph.py`

Builds a NetworkX `DiGraph` with node types: `ip`, `city`, `country`, `isp`, `org`, `topic`, `entity`.

Edges connect: IP → city → country, IP → ISP → org, city → topic, topic → entities.

Plotly renders node positions via spring layout, sized by degree centrality.

### `core/predictor.py`

| Function | Description |
|----------|-------------|
| `predict_next_window(adf)` | Recency-weighted hour/day probability → next occurrence time |
| `forecast_activity(adf, days=7)` | GradientBoostingRegressor on rolling 3-day session counts |
| `detect_drift(adf)` | Splits into early/recent halves, compares peak hour, duration, zone, anomaly rate; returns drift score 0–100 |
| `detect_counter_intel(adf, stats)` | Flags: long activity gaps, timing autocorrelation spikes, remote zone surge, mixed time zones |
| `build_fingerprint(adf, stats)` | Builds normalised 12D feature vector + labels + raw values |

### `core/ai_analyst.py` — `ARIAAnalyst`

Wraps the Anthropic Python SDK.

| Method | Tokens | Description |
|--------|--------|-------------|
| `generate_briefing(context)` | 2500 | Full structured intelligence brief |
| `chat(context, history, message)` | 1000 | Conversational analyst response |
| `generate_hypotheses(context, observation)` | 1200 | Scored alternative hypotheses |
| `build_context(d)` | — | Formats the session state dict into a text block |

System prompt positions ARIA as a senior OSINT analyst. Full investigation context (geo, zones, risk factors, web intel topics, entities, behavioural profile) is included in every API call.

---

## Setup & Installation

### Prerequisites

- Python 3.10 or later
- pip

### Install

```bash
git clone https://github.com/Ronithmk/mini-palantir.git
cd mini-palantir
pip install -r requirements.txt
```

### Run locally

```bash
streamlit run app.py
```

The app opens at `http://localhost:8501`.

### requirements.txt

```
streamlit>=1.32.0
plotly>=5.18.0
folium>=0.15.0
streamlit-folium>=0.18.0
pandas>=2.0.0
numpy>=1.24.0
scikit-learn>=1.3.0
requests>=2.31.0
feedparser>=6.0.10
networkx>=3.0
scipy>=1.11.0
pyvis>=0.3.2
anthropic>=0.25.0
```

---

## API Keys

| Service | Key Required | Where to get it | How to use |
|---------|-------------|-----------------|------------|
| ip-api.com | No | — | Used automatically |
| Wikipedia REST | No | — | Used automatically |
| Reddit JSON API | No | — | Used automatically |
| Google News RSS | No | — | Used automatically |
| DuckDuckGo Instant Answer | No | — | Used automatically |
| Anthropic (ARIA) | **Yes** (optional) | console.anthropic.com | Enter in Page 7 sidebar input |

ARGUS runs fully without any API key. The ARIA AI Analyst (Page 7) is the only feature that requires one.

---

## Deployment

### Streamlit Cloud (recommended)

1. Push the repository to GitHub
2. Visit [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub account and select the repo
4. Set **Main file path** to `app.py`
5. Click **Deploy**

The app auto-deploys on every push to the main branch. No environment variables are required (ARIA key is entered by users at runtime).

Live deployment: https://mini-palantir.streamlit.app

---

## Free Data Sources

| Source | Endpoint | Data |
|--------|----------|------|
| ip-api.com | `http://ip-api.com/json/{ip}` | Geolocation, ISP, org, timezone |
| Wikipedia | `https://en.wikipedia.org/w/api.php` + `https://en.wikipedia.org/api/rest_v1/page/summary/` | Article titles and summaries |
| Reddit | `https://www.reddit.com/search.json?q={query}` | Post titles, selftext, subreddit |
| Google News RSS | `https://news.google.com/rss/search?q={query}` | News article titles and summaries |
| DuckDuckGo | `https://api.duckduckgo.com/?q={query}&format=json` | Abstract, related topics |

All endpoints are public, require no authentication, and are rate-limited by the platforms' standard anonymous limits.

---

## Design System

ARGUS uses a Palantir Foundry-accurate colour palette applied globally via injected CSS.

### Colour Palette

| Token | Hex | Usage |
|-------|-----|-------|
| `--bg0` | `#0F0F0F` | Main canvas background |
| `--bg1` | `#141414` | Sidebar surface |
| `--bg2` | `#1C1C1C` | Card / panel background |
| `--bg3` | `#2A2A2A` | Borders and dividers |
| `--bg4` | `#383838` | Hover states |
| `--acc` | `#0B88F8` | Palantir cobalt blue — primary accent, PRIMARY zones |
| `--grn` | `#23D18B` | Success, safe risk, live indicators |
| `--red` | `#F14C4C` | Alert, danger, high risk |
| `--org` | `#F5A623` | Warning, SECONDARY zones |
| `--txt0` | `#FFFFFF` | Primary text |
| `--txt1` | `#8C8C8C` | Secondary / muted text |
| `--txt2` | `#444444` | Tertiary / very dim text |

### Zone Type Colours

| Zone Type | Colour | Hex |
|-----------|--------|-----|
| PRIMARY | Cobalt blue | `#0B88F8` |
| SECONDARY | Amber | `#F5A623` |
| TRANSIT | Purple | `#9B59B6` |
| NOISE | Dark grey | `#444444` |

### Typography

- **Body**: Inter (400, 500, 600 weights) — clean sans-serif
- **Code / data / monospace**: JetBrains Mono (400, 500 weights)
- Base font size: 14px
- Border radius: 2px (sharp, flat — Palantir style)

### Component Classes

| Class | Element |
|-------|---------|
| `.pal-card` | Standard dark card with border |
| `.pal-card-accent` | Card with cobalt blue left border |
| `.pal-card-green` | Card with green left border |
| `.pal-metric` | Metric tile with large value + small label |
| `.section-hdr` | Section heading in muted uppercase |
| `.badge` | Inline coloured type badge |
| `.badge-ip` | Blue badge (IP / geo) |
| `.badge-org` | Purple badge (organisation) |
| `.badge-loc` | Teal badge (location) |
| `.badge-zone` | Amber badge (zone) |
| `.badge-threat` | Red badge (threat / alert) |
| `.entity-row` | Flex row for entity list items |
| `.dot-live` | Green status dot |
| `.dot-alert` | Red status dot |
| `.dot-warn` | Orange status dot |
| `.dot-dead` | Grey status dot |
| `.risk-bar-bg` | Grey background bar track |
| `.risk-bar` | Coloured fill bar |

---

*ARGUS — Built with Python, Streamlit, and open-source intelligence.*
