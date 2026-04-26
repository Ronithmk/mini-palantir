"""
Adversary Wargaming — game-theoretic defender vs attacker simulation.

This is the feature that *isn't* in Palantir. Palantir is a passive analysis
platform: it tells you what was. The wargame engine takes the target's
behavioural fingerprint and the defender's allocated budget across three
defensive postures, then computes:

  - A 3×4 payoff matrix (defender strategies × attacker strategies)
  - The attacker's most likely move given the target's fingerprint
  - The expected loss for each defensive allocation
  - A simple security-game equilibrium recommendation

Defender strategies (mixable budget allocation, sums to 1.0):
  DETECT    — invest in monitoring / alerting
  HARDEN    — invest in patching / control plane
  DECEIVE   — invest in honeypots / canary tokens

Attacker strategies (the engine picks the best response):
  PHISH     — credential phishing campaign
  EXPLOIT   — known-CVE remote exploit
  INSIDER   — compromised/coerced insider
  SUPPLY    — supply-chain / 3rd-party vendor

Returns numbers between 0–100. Higher = worse outcome for the defender.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

DEFENDER_STRATS = ["DETECT", "HARDEN", "DECEIVE"]
ATTACKER_STRATS = ["PHISH", "EXPLOIT", "INSIDER", "SUPPLY"]

# Base attacker effectiveness against an undefended target (0–100).
# Tuned so PHISH is the most universally effective starting point — matches
# real-world IR reports.
BASE_ATTACK_LOSS = {
    "PHISH":   72,
    "EXPLOIT": 60,
    "INSIDER": 55,
    "SUPPLY":  48,
}

# How much each $1 of defender investment reduces the loss for a given
# (defender_strategy, attacker_strategy) pair. Values are the *fraction* of
# loss removed at full (1.0) allocation.
MITIGATION = {
    ("DETECT",  "PHISH"):   0.55,
    ("DETECT",  "EXPLOIT"): 0.35,
    ("DETECT",  "INSIDER"): 0.40,
    ("DETECT",  "SUPPLY"):  0.30,

    ("HARDEN",  "PHISH"):   0.25,
    ("HARDEN",  "EXPLOIT"): 0.70,
    ("HARDEN",  "INSIDER"): 0.20,
    ("HARDEN",  "SUPPLY"):  0.45,

    ("DECEIVE", "PHISH"):   0.30,
    ("DECEIVE", "EXPLOIT"): 0.40,
    ("DECEIVE", "INSIDER"): 0.65,
    ("DECEIVE", "SUPPLY"):  0.50,
}


@dataclass
class WargameResult:
    payoff:                dict[tuple[str, str], float]  # defender loss
    attacker_best_response: dict[str, str]               # per defender strat
    attacker_priors:       dict[str, float]              # P(attacker plays s)
    expected_loss:         dict[str, float]              # per defender strat
    optimal_defender:      str
    optimal_mix:           dict[str, float]
    optimal_loss:          float
    rationale:             list[str]


# ── Attacker priors from the target's behavioural fingerprint ─────────────────
def attacker_priors(fingerprint: dict, threat_band: str = "MEDIUM") -> dict[str, float]:
    """
    Translate the 12-D behavioural fingerprint + threat-intel band into a
    probability distribution over attacker strategies.

    Heuristics (deliberately interpretable, not learned):
      - High night activity / anomaly rate → PHISH (active social-engineering window)
      - High remote-zone usage             → SUPPLY (distributed third-party surface)
      - Hosting / VPN / Tor (HIGH band)    → EXPLOIT (infra-style target)
      - High zone diversity                → INSIDER (many touch points → many people)
    """
    f = fingerprint.get("features", {}) or {}

    night = f.get("night_activity", 0.0)
    anom  = f.get("anomaly_rate", 0.0)
    remote = f.get("remote_zone", 0.0)
    diversity = f.get("zone_diversity", 0.0)
    primary = f.get("primary_zone", 0.0)

    raw = {
        "PHISH":   1.0 + 1.5 * night + 1.5 * anom + 0.5 * primary,
        "EXPLOIT": 0.8 + (1.6 if threat_band in ("HIGH", "MEDIUM") else 0.4),
        "INSIDER": 0.6 + 1.8 * diversity,
        "SUPPLY":  0.6 + 1.8 * remote,
    }
    total = sum(raw.values()) or 1.0
    return {k: v / total for k, v in raw.items()}


# ── Payoff matrix ─────────────────────────────────────────────────────────────
def build_payoff(allocation: dict[str, float]) -> dict[tuple[str, str], float]:
    """Defender loss for every (defender_strategy, attacker_strategy) pair."""
    payoff = {}
    for ds in DEFENDER_STRATS:
        for as_ in ATTACKER_STRATS:
            base   = BASE_ATTACK_LOSS[as_]
            mit    = MITIGATION[(ds, as_)] * allocation.get(ds, 0.0)
            payoff[(ds, as_)] = round(max(0.0, base * (1 - mit)), 2)
    return payoff


def _mixed_loss(allocation: dict[str, float], attacker: str) -> float:
    """Expected loss when defender plays a mixed allocation against `attacker`."""
    loss = 0.0
    for ds in DEFENDER_STRATS:
        base = BASE_ATTACK_LOSS[attacker]
        mit  = MITIGATION[(ds, attacker)] * allocation.get(ds, 0.0)
        # Each strategy contributes proportional to its allocation share, but
        # the mitigation is additive across strategies (they're complementary
        # controls, not substitutes).
        loss += allocation.get(ds, 0.0) * base * (1 - mit)
    return round(loss, 2)


def expected_loss_per_strategy(allocation: dict[str, float],
                               priors: dict[str, float]) -> float:
    """Expected loss across the attacker prior distribution."""
    total = 0.0
    for atk, p in priors.items():
        total += p * _mixed_loss(allocation, atk)
    return round(total, 2)


# ── Optimisation ──────────────────────────────────────────────────────────────
def _grid_search(priors: dict[str, float], step: float = 0.1) -> tuple[dict[str, float], float]:
    """Coarse grid search over the 2-simplex of (DETECT, HARDEN, DECEIVE)."""
    best_alloc = None
    best_loss  = math.inf
    n = int(round(1.0 / step))
    for i in range(n + 1):
        for j in range(n + 1 - i):
            k = n - i - j
            alloc = {
                "DETECT":  i / n,
                "HARDEN":  j / n,
                "DECEIVE": k / n,
            }
            loss = expected_loss_per_strategy(alloc, priors)
            if loss < best_loss:
                best_loss = loss
                best_alloc = alloc
    return best_alloc, round(best_loss, 2)


# ── Main entry point ──────────────────────────────────────────────────────────
def run_wargame(fingerprint: dict,
                allocation: dict[str, float],
                threat_band: str = "MEDIUM") -> WargameResult:
    """Run a full simulation against the user's chosen budget allocation."""
    # Normalise allocation
    total = sum(max(0, v) for v in allocation.values()) or 1.0
    allocation = {k: max(0, v) / total for k, v in allocation.items()}

    priors = attacker_priors(fingerprint, threat_band)
    payoff = build_payoff(allocation)

    # Best response: which attacker strategy maximises *their* gain (= our loss)
    # against each pure defender strategy.
    best_response = {}
    for ds in DEFENDER_STRATS:
        best_atk = max(ATTACKER_STRATS, key=lambda a: payoff[(ds, a)])
        best_response[ds] = best_atk

    # Expected loss per pure defender strategy (so the user can see what each
    # control buys them in isolation).
    pure_alloc = {s: {ds: 1.0 if ds == s else 0.0 for ds in DEFENDER_STRATS}
                  for s in DEFENDER_STRATS}
    expected = {
        s: expected_loss_per_strategy(pure_alloc[s], priors)
        for s in DEFENDER_STRATS
    }

    optimal_mix, optimal_loss = _grid_search(priors)
    optimal_strat = max(optimal_mix, key=optimal_mix.get)

    rationale = []
    top_atk = max(priors, key=priors.get)
    rationale.append(
        f"Most-likely attacker move: {top_atk} ({priors[top_atk]*100:.0f}% prior) "
        f"based on the target's behavioural fingerprint and threat band {threat_band}."
    )
    if optimal_mix["DETECT"] >= 0.4:
        rationale.append("Equilibrium favours DETECT — target's behavioural noise "
                         "(night activity / anomalies) makes monitoring high-yield.")
    if optimal_mix["HARDEN"] >= 0.4:
        rationale.append("Equilibrium favours HARDEN — infrastructure profile "
                         "exposes exploitable surface, patching dominates.")
    if optimal_mix["DECEIVE"] >= 0.4:
        rationale.append("Equilibrium favours DECEIVE — high zone diversity / remote "
                         "usage means honeypots intercept lateral movement.")

    current_loss = expected_loss_per_strategy(allocation, priors)
    delta = round(current_loss - optimal_loss, 2)
    if delta > 1.0:
        rationale.append(
            f"Your current allocation has expected loss {current_loss:.1f}; "
            f"the equilibrium allocation reduces it to {optimal_loss:.1f} "
            f"(Δ -{delta:.1f})."
        )
    else:
        rationale.append(
            f"Your current allocation is within {delta:.1f} of the equilibrium — "
            "no meaningful gain from reallocating."
        )

    return WargameResult(
        payoff=payoff,
        attacker_best_response=best_response,
        attacker_priors=priors,
        expected_loss=expected,
        optimal_defender=optimal_strat,
        optimal_mix=optimal_mix,
        optimal_loss=optimal_loss,
        rationale=rationale,
    )
