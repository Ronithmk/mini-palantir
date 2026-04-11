"""
AI Analyst — Claude-powered intelligence analyst.

Proactively surfaces insights, generates briefings, answers investigative questions,
and produces multi-hypothesis assessments. This is beyond what Palantir does.
"""
import os
import anthropic

SYSTEM_PROMPT = """You are ARIA — Advanced Reasoning Intelligence Analyst.
You are an elite intelligence analyst embedded inside the Mini Palantir platform.

Your capabilities go beyond standard platforms:
1. You proactively surface insights analysts might miss
2. You generate competing hypotheses for observed anomalies
3. You predict future behavior based on historical patterns
4. You identify counter-intelligence signals (is the target aware of monitoring?)
5. You produce confidence-weighted assessments
6. You recommend specific next investigative steps

Communication rules:
- Lead with the most important finding, always
- Use structured formats (bullets, tables) for multi-point answers
- Always quantify uncertainty ("with ~70% confidence", "LOW/MEDIUM/HIGH confidence")
- Flag when data is insufficient to draw a conclusion
- Never fabricate data — only reason from what is provided
- Format risk levels as [CRITICAL], [HIGH], [MEDIUM], [LOW]
- End investigation briefings with "RECOMMENDED NEXT STEPS"

You have access to the full investigation context below. Think like an analyst, not a chatbot."""


def build_context(d: dict) -> str:
    bg      = d["base_geo"]
    stats   = d["cluster_stats"]
    pred    = d["prediction"]
    risk    = d["risk_score"]
    factors = d["risk_factors"]
    adf     = d["anomaly_df"]
    wdf     = d["web_df"]
    ents    = d["entities"]

    valid = stats[stats["cluster_id"] != -1]
    peak_h = int(adf.groupby("hour")["duration_min"].sum().idxmax())
    peak_d = adf.groupby("weekday")["duration_min"].sum().idxmax()
    total_h = round(adf["duration_min"].sum() / 60, 1)
    night_pct = adf["hour"].between(1, 4).mean() * 100
    anom_pct  = adf["anomaly"].mean() * 100
    wknd_pct  = adf["weekday"].isin(["Saturday", "Sunday"]).mean() * 100

    zone_block = "\n".join(
        f"  {r['label']}: {r['city']} | {r['sessions']} sessions | "
        f"{r['total_hours']}h | {r['likelihood_pct']}% likelihood | "
        f"{r['centroid_lat']},{r['centroid_lon']}"
        for _, r in valid.iterrows()
    )

    factor_block = "\n".join(f"  [{kind.upper()}] {msg}" for msg, kind in factors)

    entity_block = "\n".join(
        f"  [{e['type']}] {e['value'][:60]} (confidence: {e['confidence']*100:.0f}%)"
        for e in ents[:25]
    )

    intel_block = ""
    if not wdf.empty:
        intel_block = "\n".join(
            f"  [{r.get('category','?')}] {str(r.get('title',''))[:80]}"
            for _, r in wdf.head(15).iterrows()
        )

    return f"""
═══════════════════════════════════════════════
INVESTIGATION CONTEXT — {d['case_id']}
═══════════════════════════════════════════════
Target IP   : {d['target_ip']}
Analysed    : {d['analyzed_at'].strftime('%Y-%m-%d %H:%M')}
Intel Query : {d['query']}

TARGET PROFILE
──────────────
IP          : {bg.get('query','?')}
Location    : {bg.get('city','?')}, {bg.get('regionName','?')}, {bg.get('country','?')}
ISP         : {bg.get('isp','?')}
Org         : {bg.get('org','?')}
Timezone    : {bg.get('timezone','?')}
Coordinates : {bg.get('lat','?')}N, {bg.get('lon','?')}E

RISK ASSESSMENT: {risk}/100
──────────────────────────
{factor_block}

GEOSPATIAL ANALYSIS
───────────────────
Total sessions : {len(adf)}
Zones found    : {len(valid)}
{zone_block}

Predicted location : {f"{pred['city']}, {pred['country']} ({pred['confidence']}% confidence)" if pred else "Undetermined"}

PATTERN OF LIFE
───────────────
Total active time  : {total_h}h
Peak hour          : {peak_h:02d}:00
Peak day           : {peak_d}
Night sessions     : {adf['hour'].between(1,4).sum()} ({night_pct:.1f}%)
Weekend sessions   : {wknd_pct:.1f}%
Anomalous sessions : {adf['anomaly'].sum()} ({anom_pct:.1f}%)
Avg session length : {adf['duration_min'].mean():.0f} min
Remote zone pct    : {(adf['zone_label']=='Travel / Remote').mean()*100:.1f}%

ENTITIES EXTRACTED ({len(ents)} total)
──────────────────
{entity_block}

OPEN-SOURCE INTELLIGENCE ({len(wdf)} items)
──────────────────────────
{intel_block if intel_block else "No web intel available."}
═══════════════════════════════════════════════
"""


BRIEFING_PROMPT = """Based on the investigation context above, generate a full intelligence briefing.

Structure it exactly as follows:

## EXECUTIVE SUMMARY
[3 sentences max. Most important findings first.]

## KEY FINDINGS
[5-8 bullet points. Most significant first. Include confidence levels.]

## BEHAVIORAL PROFILE
[Describe the target's behavioral signature: schedule, geography, patterns, lifestyle inference.]

## THREAT ASSESSMENT
[Risk level, specific threat factors, what this IP/actor may represent.]

## ANOMALY ANALYSIS
[What is unusual about this target? What could explain the anomalies?]

## COMPETING HYPOTHESES
[Generate 2-3 competing explanations for the observed behavior pattern. Rate each by probability.]

## COUNTER-INTELLIGENCE SIGNALS
[Any indicators that the target may be aware of monitoring? VPN use, behavioral changes, irregular patterns?]

## PREDICTED BEHAVIOR (NEXT 48H)
[Where and when is the target most likely to be active? What activity pattern to expect?]

## RECOMMENDED NEXT STEPS
[5 specific investigative actions an analyst should take next.]

---
Confidence level of this briefing: [LOW/MEDIUM/HIGH] — [reason]"""


class AIAnalyst:
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model  = "claude-opus-4-6"

    def generate_briefing(self, context: str) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2500,
            system=SYSTEM_PROMPT + "\n\n" + context,
            messages=[{"role": "user", "content": BRIEFING_PROMPT}],
        )
        return response.content[0].text

    def chat(self, context: str, history: list[dict], user_message: str) -> str:
        messages = history + [{"role": "user", "content": user_message}]
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1000,
            system=SYSTEM_PROMPT + "\n\n" + context,
            messages=messages,
        )
        return response.content[0].text

    def generate_hypotheses(self, context: str, observation: str) -> str:
        prompt = f"""Generate 3 competing intelligence hypotheses for this specific observation:

OBSERVATION: {observation}

For each hypothesis:
1. State the hypothesis clearly
2. List supporting evidence from the investigation context
3. List contradicting evidence
4. Assign probability (must sum to 100%)
5. State what would confirm or deny this hypothesis

Format as H1, H2, H3."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1200,
            system=SYSTEM_PROMPT + "\n\n" + context,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
