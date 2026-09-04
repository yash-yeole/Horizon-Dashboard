"""News-severity scoring framework: headline -> scenario probabilities.

Instead of hand-setting the three regime probabilities, we *derive* them from a
transparent, reproducible score of the headline. The headline is decomposed into
five economically-grounded factors; a weighted composite severity S in [0,1] is
mapped to the escalation / contained / fizzle probabilities via monotone functions.

This makes the news->pricing link explicit and lets ANY future headline be re-scored.

All five factors are scored 0..1 where higher = more bullish / more backwardation-
inducing. Buffer adequacy is scored DIRECTLY (higher score = THINNER buffers =
more severe) — the old separate dampener step is removed, making the framework
cleaner and fully symmetric.

FACTORS
-------
1. Supply at risk          — how many barrels are physically threatened?
2. Directness of threat    — actual kinetic action vs diplomatic posturing?
3. Duration potential      — how long could the disruption persist?
4. Buffer adequacy (inv.)  — how thin are spare-capacity / inventory cushions?
                             (HIGH score = THIN buffers = more bullish)
5. Escalation dynamics     — how likely is the situation to worsen further?
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class Factor:
    name: str
    score: float       # 0..1
    weight: float      # relative importance (weights sum to 1)
    note: str = ""


# --- Headline scored: "Israel strikes Iranian ENERGY infrastructure; Iran threatens
#     to close the Strait of HORMUZ." ----------------------------------------------
FACTORS = [
    Factor("Supply at risk", 0.85, 0.30,
           "Hormuz threatened (~20 mb/d, 20% global supply); Iranian energy infra "
           "directly struck (~1.5-2 mb/d exports). Largest physical-barrel exposure possible."),
    Factor("Directness of threat", 0.85, 0.25,
           "Actual kinetic strike on energy infrastructure (not posturing). "
           "State-on-state Israel<->Iran; Hormuz threat issued at sovereign level, not proxy."),
    Factor("Duration potential", 0.55, 0.20,
           "Infrastructure damage is lasting vs a diplomatic flare-up. However Iran has "
           "threatened Hormuz many times without execution — could be 12-day-war style."),
    Factor("Buffer adequacy (inventory)", 0.65, 0.15,
           "HIGH score = THIN buffers = more bullish. OPEC+ spare capacity ~3-4 mb/d "
           "(tighter than 2022-23); inventories below 5-yr average in key regions; "
           "SPR partially depleted. Less cushion than the historical base rate assumes."),
    Factor("Escalation dynamics", 0.65, 0.10,
           "Tit-for-tat pattern is established; US Navy + Gulf states drawn into the calculus. "
           "Iran has incentive to respond after direct strikes on energy infra. "
           "Historically avoids full-scale war, but dynamic is self-reinforcing."),
]

# No separate buffer dampener — buffer adequacy is factor 4 above (scored directly).
# Severity = simple weighted average of all five factors.


def severity(factors=FACTORS) -> dict:
    """Composite severity S = weighted average of all factor scores."""
    wsum = sum(f.weight for f in factors)
    s = sum(f.score * f.weight for f in factors) / wsum
    return {"severity": round(s, 4),
            "contributions": {f.name: round(f.score * f.weight / wsum, 4) for f in factors}}


def probabilities(factors=FACTORS) -> dict:
    """Map severity S -> (escalation, contained, fizzle) probabilities.

    Design (monotone in S, sums to 1):
      p_escalation = 0.05 + 0.37 * S^2       (convex: tail risk accelerates with severity)
      p_fizzle     = 0.18 + 0.32 * (1 - S)   (floor respects the empirical base rate that
                                              geopolitical oil spikes often fade)
      p_contained  = 1 - p_escalation - p_fizzle   (the residual base case)
    """
    S = severity(factors)["severity"]
    p_esc = 0.05 + 0.37 * S**2
    p_fiz = 0.18 + 0.32 * (1 - S)
    p_con = max(1 - p_esc - p_fiz, 0.05)
    tot = p_esc + p_con + p_fiz
    return {
        "Escalation / Hormuz disruption": round(p_esc / tot, 3),
        "Contained / risk-premium":        round(p_con / tot, 3),
        "De-escalation / fizzle":          round(p_fiz / tot, 3),
    }


def scenario_probabilities_6(factors=FACTORS) -> dict:
    """Map severity S -> the 5 structural scenarios used by structural_model.py.

    Two-stage derivation so the link from headline -> scenario stays transparent:

    Stage 1 (family split):
        de-escalation      = 0.18 + 0.32*(1-S)      # fizzle floor
        escalation family  = 0.05 + 0.37*S^2         # convex tail growth
        containment        = residual (the base case)

    Stage 2 splits the escalation family across its three physical realisations.
    The split tilts toward the violent tail as S rises:
        closure (tail) share = 0.08 + 0.10*S
        export-infra  share  = 0.20 + 0.07*S
        harassment    share  = remainder
    """
    S = severity(factors)["severity"]
    p_deesc = 0.18 + 0.32 * (1 - S)
    p_escfam = 0.05 + 0.37 * S**2
    p_con = max(1 - p_deesc - p_escfam, 0.05)
    tot = p_deesc + p_escfam + p_con
    p_deesc, p_escfam, p_con = p_deesc / tot, p_escfam / tot, p_con / tot

    w_clo = 0.08 + 0.10 * S
    w_exp = 0.20 + 0.07 * S
    w_har = max(1 - w_clo - w_exp, 0.0)
    wsum = w_clo + w_exp + w_har
    w_clo, w_exp, w_har = w_clo / wsum, w_exp / wsum, w_har / wsum

    return {
        "Rapid de-escalation":              round(p_deesc, 3),
        "Prolonged containment":            round(p_con, 3),
        "Hormuz harassment":                round(p_escfam * w_har, 3),
        "Iranian export infra destroyed":   round(p_escfam * w_exp, 3),
        "Hormuz closure (tail)":            round(p_escfam * w_clo, 3),
    }


def scorecard() -> str:
    sv = severity()
    S = sv["severity"]
    lines = [
        "Factor scoring for: 'Israel strikes Iranian energy infra; Iran threatens Hormuz'",
        f"{'Factor':<36s}  score  weight  contribution",
        "-" * 70,
    ]
    for f in FACTORS:
        contrib = sv["contributions"][f.name]
        lines.append(f"  {f.name:<34s}  {f.score:5.2f}  {f.weight:5.2f}      {contrib:5.3f}")
    lines.append("-" * 70)
    lines.append(f"  {'Composite severity S':<34s}                     {S:5.3f}")
    lines.append("")
    lines.append(f"  All factors scored 0-1 (higher = more bullish).")
    lines.append(f"  Buffer adequacy: HIGH score = THIN buffers = adds to severity.")
    lines.append(f"  No separate dampener step — severity = weighted average of all five.")
    return "\n".join(lines)


if __name__ == "__main__":
    print(scorecard())
    sv = severity()
    print(f"\nSeverity S = {sv['severity']:.3f}")
    print("\nDerived scenario probabilities (3-regime):")
    for k, v in probabilities().items():
        print(f"  {k:<34s} {v:.1%}")
    print("\nDerived scenario probabilities (5 structural scenarios):")
    for k, v in scenario_probabilities_6().items():
        print(f"  {k:<34s} {v:.1%}")
