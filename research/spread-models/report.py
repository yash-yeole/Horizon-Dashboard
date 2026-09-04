"""Generate the final written deliverable (output/report.md) from the model."""
from __future__ import annotations

import os
import numpy as np
import pandas as pd

from load_spreads import load_daily_spreads
from event_study import event_response
from scoring import scorecard, severity, probabilities
from mixture_model import (calibrate, simulate, SCENARIO_PROB, SPREADS, SEED,
                           param_uncertainty, validate_against_history, sensitivity_to_escalation,
                           _scenario_mean)


def pct(a, q):
    return float(np.percentile(a, q))


def build():
    spreads = load_daily_spreads()
    params = calibrate(spreads)
    rng = np.random.default_rng(SEED)
    draws, comp, names = simulate(params, rng)
    levels0 = spreads.iloc[-1]
    resp = event_response(spreads)

    L = []
    w = L.append
    w("# News -> Brent Calendar-Spread Distribution\n")
    w("**Headline modelled:** *\"Israel launches strikes on Iranian energy infrastructure. "
      "Iran threatens closure of the Strait of Hormuz.\"*\n")
    w("**Horizon:** 1 week (5 trading days). **Convention:** positive = backwardation "
      "(near minus far). **Data:** 1-minute ICE Brent (LCO) nearbys c1..c6, Jan-2021 to May-2026.\n")

    w("\n## 1. Method\n")
    w("A news event does not move a spread to a single number; it shifts the *distribution* of "
      "where the spread lands. We build that distribution as a probability-weighted mixture of "
      "three regimes calibrated to real analogs in the data. Two pieces:\n")
    w("1. **A news-severity scoring framework** turns the headline into the three regime "
      "*probabilities* (transparent, reproducible for any future headline).\n")
    w("2. **An event study** sets each regime's *magnitude* (drift + tail) from history.\n")
    w("The mixture is Monte-Carlo'd (400k draws); small-N parameter uncertainty is propagated "
      "to put confidence intervals on the outputs themselves.\n")

    w("\n## 2. News-severity scoring -> probabilities\n")
    w("```\n" + scorecard() + "\n```\n")
    sv = severity()
    w(f"\nComposite **severity S = {sv['severity']:.2f}**, mapped to probabilities via "
      "`p_esc = 0.05 + 0.37·S²`, `p_fizzle = 0.18 + 0.32·(1-S)`, `p_contained = residual` "
      "(convex escalation term; fizzle floor respects that 3 of 5 sampled shocks faded):\n")
    w("| Scenario | Probability | Narrative |")
    w("|---|---:|---|")
    w(f"| Escalation / Hormuz disruption | {SCENARIO_PROB['Escalation / Hormuz disruption']:.0%} | "
      "Strikes impair supply/tanker flow; sharp front backwardation spike. **Right-skewed tail.** |")
    w(f"| Contained / risk-premium | {SCENARIO_PROB['Contained / risk-premium']:.0%} | "
      "Strikes continue, no Hormuz closure; war-risk premium builds. **Base case.** |")
    w(f"| De-escalation / fizzle | {SCENARIO_PROB['De-escalation / fizzle']:.0%} | "
      "Threat priced then bleeds out (ceasefire / no follow-through); mean-reversion. |")

    w("\n## 3. Event study - magnitude calibration\n")
    w("5-trading-day spread change ($/bbl) after each shock in the sample:\n")
    w("| Event | regime | M1-M2 | M2-M4 | M1-M6 |")
    w("|---|---|---:|---:|---:|")
    regime = {"Russia invades Ukraine": "supply shock -> escalation template",
              "Iran->Israel barrage (Oct24)": "contained risk-premium",
              "Israel strikes Iran (Jun25)": "contained (primary analog)",
              "Hamas attack / Gaza war": "fizzle / no supply hit",
              "Iran->Israel strike (Apr24)": "fizzle / de-escalation"}
    for ev, lab in regime.items():
        c = resp[ev]["chg_5d"]
        w(f"| {ev} | {lab} | {c['M1-M2']:+.2f} | {c['M2-M4']:+.2f} | {c['M1-M6']:+.2f} |")
    w("\nThe **escalation** regime is modelled as a right-skewed **lognormal** (median anchored "
      "to the Russia-2022 impulse; 95th pct ~2x median for a genuine Hormuz interruption, which "
      "in barrels far exceeds Russia). Contained and fizzle are Normals around their cluster means.\n")

    w("\n## 4. Distribution by spread (1-week CHANGE, $/bbl) - the robust output\n")
    w("| Spread | EV change | 50% range (P25-P75) | 90% range (P5-P95) | P(widen) |")
    w("|---|---:|---:|---:|---:|")
    for s in SPREADS:
        d = draws[s]
        w(f"| {s} | {d.mean():+.2f} | [{pct(d,25):+.2f}, {pct(d,75):+.2f}] | "
          f"[{pct(d,5):+.2f}, {pct(d,95):+.2f}] | {(d>0).mean():.0%} |")

    w("\n### Implied 1-week LEVEL (anchored on latest close " f"{spreads.index[-1].date()})\n")
    w("| Spread | Start | EV level | 50% range | 90% range |")
    w("|---|---:|---:|---:|---:|")
    for s in SPREADS:
        lvl = levels0[s] + draws[s]
        w(f"| {s} | {levels0[s]:.2f} | {lvl.mean():.2f} | [{pct(lvl,25):.2f}, {pct(lvl,75):.2f}] | "
          f"[{pct(lvl,5):.2f}, {pct(lvl,95):.2f}] |")
    w("\n*The latest close is itself steeply backwardated, so the **change** distribution is the "
      "anchor-independent, robust deliverable; levels are shown for context.*\n")

    w("\n## 5. Statistical robustness\n")
    w("**Parameter uncertainty** (small N): means sampled from their standard errors and weights "
      "from a Dirichlet around the scored probabilities, giving a 90% CI *on the statistics*:\n")
    pu = param_uncertainty(spreads, n_outer=1200)
    w("| Spread | EV 90% CI | P95 90% CI |")
    w("|---|---:|---:|")
    for s in SPREADS:
        r = pu.loc[s]
        w(f"| {s} | [{r['EV_lo']:+.2f}, {r['EV_hi']:+.2f}] | [{r['p95_lo']:+.2f}, {r['p95_hi']:+.2f}] |")

    w("\n**Backtest** - where each realised historical move falls in the model's predicted CDF "
      "(well-calibrated if fizzle events sit low, contained ~mid, supply shock in the tail):\n")
    v = validate_against_history(spreads).pivot(index="event", columns="spread", values="model_pctile")
    w("| Event | M1-M2 | M2-M4 | M1-M6 |")
    w("|---|---:|---:|---:|")
    for ev in v.index:
        w(f"| {ev} | {v.loc[ev,'M1-M2']:.0%} | {v.loc[ev,'M2-M4']:.0%} | {v.loc[ev,'M1-M6']:.0%} |")
    w("\nEvery event lands where the regime logic predicts: fizzle ~20-25th pct, the direct "
      "Israel-Iran analogs ~50th, Russia ~88th. The model brackets history rather than over/under-shooting.\n")

    w("\n## 6. Sensitivity to the escalation probability\n")
    w("How EV and the 90% range move as p(escalation) varies (M1-M6 shown; fizzle held fixed):\n")
    se = sensitivity_to_escalation(spreads)
    se6 = se[se.spread == "M1-M6"]
    w("| p(escalation) | EV | P05 | P95 |")
    w("|---:|---:|---:|---:|")
    for _, r in se6.iterrows():
        w(f"| {r['p_escalation']:.0%} | {r['EV']:+.2f} | {r['p05']:+.2f} | {r['p95']:+.2f} |")
    w("\nThe **downside (P05) is bounded** by the fizzle regime; only the **upside tail** "
      "responds to escalation odds - the asymmetry a single-number forecast would miss.\n")

    w("\n## 7. How the news translates into the curve\n")
    w("- **M1-M2 (front)** - most information-sensitive per dollar; a supply scare lands on the "
      "prompt, so it moves first and reverts fastest. Modest in dollars, large vs its ~0.7 baseline weekly vol.\n")
    w("- **M2-M4 (deferred)** - muted; the market prices a *temporary* disruption, so the belly "
      "moves less. It widens mainly in the escalation regime where disruption is expected to persist.\n")
    w("- **M1-M6 (front-to-back)** - captures the whole steepening: largest absolute move and "
      "fattest tail, the cleanest expression of 'front spikes, back anchored'.\n")
    w("- **Caveat (regime-dependence):** a *full, sustained* Hormuz closure would lift the entire "
      "curve (back end too), partially capping the steepening - the lognormal tail is calibrated to "
      "the front-loaded fear response, not an indefinite outage.\n")
    w("\n**Bottom line:** modal outcome is a moderate backwardation build (risk premium), with a "
      "fat right tail if Hormuz is genuinely threatened and a ~28% chance the move fades. The "
      "deliverable is the *shape* of the uncertainty, not a point forecast.\n")

    text = "\n".join(L)
    outdir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "report.md"), "w", encoding="utf-8") as f:
        f.write(text)
    print("Wrote", os.path.join(outdir, "report.md"))


if __name__ == "__main__":
    build()
