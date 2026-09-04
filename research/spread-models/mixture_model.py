"""Step 4: scenario-mixture model for the assigned headline.

Headline: "Israel launches strikes on Iranian energy infrastructure.
           Iran threatens closure of the Strait of Hormuz."

The 1-week change in each Brent calendar spread is modelled as a probability-weighted
mixture of three regimes, each calibrated to historical analogs in the 2021-2026 sample:

  1. ESCALATION / HORMUZ DISRUPTION  - right-skewed (LOGNORMAL) tail. Median anchored to the
       Russia-2022 supply shock (only realised supply shock in sample); upper tail (~2x median)
       represents a genuine Hormuz interruption, which is far larger than Russia in barrels.
  2. CONTAINED / RISK-PREMIUM        - Normal. Mean = the two direct Israel<->Iran analogs.
  3. DE-ESCALATION / FIZZLE          - Normal. Mean = the no-supply-hit geopolitical events.

Probabilities are NOT hand-set: they are derived from scoring.py (headline-severity score).
Parameter uncertainty (small-N standard errors on the means + Dirichlet on the weights) is
propagated to put confidence intervals on the EV and the tail bounds themselves.
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

from load_spreads import load_daily_spreads
from event_study import event_response, baseline_stats
from scoring import probabilities as scenario_probabilities

SPREADS = ["M1-M2", "M2-M4", "M1-M6"]
N_SIM = 400_000
SEED = 42

# Probabilities derived from the news-severity scoring framework (scoring.py)
SCENARIO_PROB = scenario_probabilities()
SCEN_NAMES = list(SCENARIO_PROB.keys())

# Escalation tail shape: lognormal sigma so the 95th pct ~ 2.2x the median (full-closure tail)
ESC_SIGMA = np.log(2.2) / 1.645  # ~0.479


def calibrate(spreads: pd.DataFrame) -> dict:
    """Per-spread scenario parameters + the cluster member values (for standard errors)."""
    base = baseline_stats(spreads)
    resp = event_response(spreads)

    def chg(ev):
        return resp[ev]["chg_5d"]

    def peak(ev):
        return resp[ev]["peak_5d"]

    params = {}
    for s in SPREADS:
        b_std = base.loc[s, "std"]

        # 1. Escalation (lognormal): median = blend of Russia 5d change & its peak impulse.
        esc_median = 0.5 * (chg("Russia invades Ukraine")[s] + peak("Russia invades Ukraine")[s])

        # 2. Contained (normal): the two direct Israel<->Iran exchanges.
        cont_members = np.array([chg("Iran->Israel barrage (Oct24)")[s],
                                 chg("Israel strikes Iran (Jun25)")[s]])

        # 3. Fizzle (normal): the no-supply-hit events.
        fizz_members = np.array([chg("Hamas attack / Gaza war")[s],
                                 chg("Iran->Israel strike (Apr24)")[s]])

        params[s] = {
            "escalation": {"dist": "lognormal", "median": float(esc_median),
                           "sigma": ESC_SIGMA,
                           "se_median": float(0.35 * esc_median)},  # mechanism uncertainty
            "contained": {"dist": "normal", "mean": float(cont_members.mean()),
                          "sd": float(b_std),
                          "se_mean": float(cont_members.std(ddof=1) / np.sqrt(len(cont_members)))},
            "fizzle": {"dist": "normal", "mean": float(fizz_members.mean()),
                       "sd": float(0.7 * b_std),
                       "se_mean": float(fizz_members.std(ddof=1) / np.sqrt(len(fizz_members)))},
        }
    return params


def _scenario_mean(p) -> float:
    """Expected weekly change implied by a scenario's parameters."""
    if p["dist"] == "lognormal":
        return p["median"] * np.exp(p["sigma"] ** 2 / 2.0)
    return p["mean"]


def _draw_scenario(p, n, rng):
    if p["dist"] == "lognormal":
        return rng.lognormal(mean=np.log(p["median"]), sigma=p["sigma"], size=n)
    return rng.normal(p["mean"], p["sd"], size=n)


def simulate(params: dict, rng: np.random.Generator, probs=None, n=N_SIM):
    """Monte Carlo the mixture; returns weekly-change draws per spread + the regime label."""
    probs = SCENARIO_PROB if probs is None else probs
    pvec = np.array([probs[n_] for n_ in SCEN_NAMES], dtype=float)
    pvec = pvec / pvec.sum()
    key = {"Escalation / Hormuz disruption": "escalation",
           "Contained / risk-premium": "contained",
           "De-escalation / fizzle": "fizzle"}
    comp = rng.choice(len(SCEN_NAMES), size=n, p=pvec)
    draws = {}
    for s in SPREADS:
        out = np.empty(n)
        for k, name in enumerate(SCEN_NAMES):
            mask = comp == k
            out[mask] = _draw_scenario(params[s][key[name]], int(mask.sum()), rng)
        draws[s] = out
    return draws, comp, SCEN_NAMES


def summarize(spreads, params, draws, comp, names):
    levels0 = spreads.iloc[-1]
    key = {"Escalation / Hormuz disruption": "escalation",
           "Contained / risk-premium": "contained", "De-escalation / fizzle": "fizzle"}
    rows = []
    for s in SPREADS:
        d = draws[s]
        lvl = levels0[s] + d
        rows.append({
            "spread": s, "start_level": round(float(levels0[s]), 3),
            "EV_change": round(float(d.mean()), 3), "EV_level": round(float(lvl.mean()), 3),
            "p25_level": round(float(np.percentile(lvl, 25)), 3),
            "p75_level": round(float(np.percentile(lvl, 75)), 3),
            "p05_level": round(float(np.percentile(lvl, 5)), 3),
            "p95_level": round(float(np.percentile(lvl, 95)), 3),
            "p_backwardation_up": round(float((d > 0).mean()), 3),
        })
    table = pd.DataFrame(rows).set_index("spread")
    scen = {}
    for name in names:
        scen[name] = {s: round(float(_scenario_mean(params[s][key[name]])), 3) for s in SPREADS}
    return table, scen, levels0


# --- Rigor add-ons ----------------------------------------------------------------

def param_uncertainty(spreads, n_outer=2000, n_inner=4000, seed=SEED):
    """Propagate small-N parameter uncertainty -> 90% CI on EV and on P05/P95 bounds.

    Each outer draw samples scenario means from their sampling distributions and the
    weights from a Dirichlet centred on the scored probabilities, then inner-simulates.
    """
    params = calibrate(spreads)
    rng = np.random.default_rng(seed)
    base_p = np.array([SCENARIO_PROB[n_] for n_ in SCEN_NAMES])
    conc = 40.0  # Dirichlet concentration (higher = tighter around the point probs)
    key = {"Escalation / Hormuz disruption": "escalation",
           "Contained / risk-premium": "contained", "De-escalation / fizzle": "fizzle"}

    stats = {s: {"EV": [], "p05": [], "p95": []} for s in SPREADS}
    for _ in range(n_outer):
        pw = rng.dirichlet(base_p * conc)
        comp = rng.choice(3, size=n_inner, p=pw)
        for s in SPREADS:
            pp = params[s]
            # perturb means
            esc_med = max(rng.normal(pp["escalation"]["median"], pp["escalation"]["se_median"]), 1e-3)
            con_mu = rng.normal(pp["contained"]["mean"], pp["contained"]["se_mean"])
            fiz_mu = rng.normal(pp["fizzle"]["mean"], pp["fizzle"]["se_mean"])
            out = np.empty(n_inner)
            m0 = comp == 0
            out[m0] = rng.lognormal(np.log(esc_med), pp["escalation"]["sigma"], m0.sum())
            m1 = comp == 1
            out[m1] = rng.normal(con_mu, pp["contained"]["sd"], m1.sum())
            m2 = comp == 2
            out[m2] = rng.normal(fiz_mu, pp["fizzle"]["sd"], m2.sum())
            stats[s]["EV"].append(out.mean())
            stats[s]["p05"].append(np.percentile(out, 5))
            stats[s]["p95"].append(np.percentile(out, 95))

    rows = []
    for s in SPREADS:
        rows.append({
            "spread": s,
            "EV_lo": round(np.percentile(stats[s]["EV"], 5), 2),
            "EV_hi": round(np.percentile(stats[s]["EV"], 95), 2),
            "p95_lo": round(np.percentile(stats[s]["p95"], 5), 2),
            "p95_hi": round(np.percentile(stats[s]["p95"], 95), 2),
        })
    return pd.DataFrame(rows).set_index("spread")


def validate_against_history(spreads):
    """Does the model's predicted distribution bracket the realised event moves?
    Reports, per historical event, where its actual 5d change falls in the model CDF."""
    params = calibrate(spreads)
    rng = np.random.default_rng(7)
    draws, _, _ = simulate(params, rng, n=200_000)
    resp = event_response(spreads)
    rows = []
    for ev, r in resp.items():
        for s in SPREADS:
            actual = r["chg_5d"][s]
            pctile = float((draws[s] < actual).mean())
            rows.append({"event": ev, "spread": s, "actual": round(actual, 2),
                         "model_pctile": round(pctile, 2)})
    return pd.DataFrame(rows)


def sensitivity_to_escalation(spreads, esc_grid=(0.05, 0.10, 0.15, 0.22, 0.30, 0.40)):
    """EV and 90% range vs the escalation probability (fizzle held at scored level)."""
    params = calibrate(spreads)
    rng = np.random.default_rng(123)
    p_fiz = SCENARIO_PROB["De-escalation / fizzle"]
    rows = []
    for pe in esc_grid:
        pc = max(1 - pe - p_fiz, 0.02)
        probs = {"Escalation / Hormuz disruption": pe, "Contained / risk-premium": pc,
                 "De-escalation / fizzle": p_fiz}
        tot = sum(probs.values())
        probs = {k: v / tot for k, v in probs.items()}
        draws, _, _ = simulate(params, rng, probs=probs, n=120_000)
        for s in SPREADS:
            d = draws[s]
            rows.append({"p_escalation": pe, "spread": s, "EV": round(d.mean(), 2),
                         "p05": round(np.percentile(d, 5), 2),
                         "p95": round(np.percentile(d, 95), 2)})
    return pd.DataFrame(rows)


def main():
    spreads = load_daily_spreads()
    params = calibrate(spreads)
    rng = np.random.default_rng(SEED)
    draws, comp, names = simulate(params, rng)
    table, scen, levels0 = summarize(spreads, params, draws, comp, names)

    pd.set_option("display.width", 150)
    print("Scenario probabilities (from scoring.py):", SCENARIO_PROB)
    print("Start (latest) levels:", levels0.round(3).to_dict())
    print("\nScenario expected 1-week CHANGE ($/bbl):")
    print(pd.DataFrame(scen).round(3))
    print("\n=== DISTRIBUTION OF SPREAD LEVELS AFTER 1 WEEK ===")
    print(table.to_string())
    print("\n=== PARAMETER UNCERTAINTY (90% CI on EV and P95) ===")
    print(param_uncertainty(spreads, n_outer=800).to_string())

    outdir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(outdir, exist_ok=True)
    result = {
        "headline": "Israel strikes Iranian energy infra; Iran threatens Hormuz",
        "scenario_probabilities": SCENARIO_PROB,
        "start_levels": {s: round(float(levels0[s]), 3) for s in SPREADS},
        "scenario_params": params,
        "scenario_expected_change": scen,
        "distribution": table.reset_index().to_dict(orient="records"),
    }
    with open(os.path.join(outdir, "results.json"), "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nWrote {os.path.join(outdir, 'results.json')}")
    return result


if __name__ == "__main__":
    main()
