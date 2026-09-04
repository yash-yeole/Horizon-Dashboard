"""Structural driver model: fundamentals -> Brent calendar-spread distribution.

Upgrade over the pure event-study mixture: the spread move is now generated from
FUNDAMENTAL DRIVERS (supply at risk, buffer & its accessibility, persistence, location,
geopolitical premium), run through a calibrated structural response function, then Monte
Carlo'd over both the scenarios and the drivers within each scenario.

Response function (calibrated so it reproduces every historical event from (delta, rho)):
    coverage = min(buffer*access / supply, 1)
    E        = supply * location * (1 - KAPPA*coverage)          # effective unmet shortfall (mb/d)
    delta    = BETA*E + premium                                  # front impulse  == M1-M2 move
    M2-M4    = (A24 + B24*rho) * delta + noise
    M1-M6    = (A16 + B16*rho) * delta + noise
The curve "fans" wider with persistence rho: a sustained shock tightens deferred months
too (large M1-M6 multiple); a brief premium is front-concentrated (small multiple).

Key market insight encoded: in a Hormuz event the world's spare capacity is largely
*behind the blockage* (Gulf barrels), so `access` collapses -> coverage ~0 -> E explodes.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from load_spreads import load_daily_spreads
from event_study import baseline_stats, event_response
from scoring import scenario_probabilities_6

# --- calibrated structural constants ----------------------------------------
BETA = 1.07     # $/bbl front impulse per mb/d effective shortfall
KAPPA = 0.50    # fraction of a shock that prices through even when fully buffered
A24, B24 = 0.44, 1.90   # M2-M4 / M1-M2 curve-fan ratio = A24 + B24*rho
A16, B16 = 2.28, 2.56   # M1-M6 / M1-M2 curve-fan ratio = A16 + B16*rho
BUFFER_MEAN, BUFFER_SD = 4.5, 0.4   # OPEC+ effective spare capacity (mb/d), 2025-ish

SPREADS = ["M1-M2", "M2-M4", "M1-M6"]

# --- scenarios: distributions over the drivers ------------------------------
# triangular(min, mode, max) unless noted. `access` = fraction of buffer reachable.
SCENARIOS = {
    "Rapid de-escalation": dict(
        supply=(0.0, 0.10, 0.4), rho=(0.05, 0.10, 0.20), access=(0.8, 1.0, 1.0),
        premium=(-0.5, -0.30, 0.0), location=1.00,
        note="Ceasefire within days; war premium bleeds out."),
    "Prolonged containment": dict(
        supply=(0.2, 0.60, 1.2), rho=(0.30, 0.45, 0.60), access=(0.7, 1.0, 1.0),
        premium=(0.0, 0.15, 0.30), location=1.00,
        note="Strikes continue, no Hormuz; risk premium builds. Base case."),
    "Hormuz harassment": dict(
        supply=(0.8, 2.0, 4.0), rho=(0.35, 0.50, 0.65), access=(0.20, 0.40, 0.60),
        premium=(0.1, 0.30, 0.6), location=1.05,
        note="Tanker harassment / insurance spike; spare partly trapped in Gulf."),
    "Iranian export infra destroyed": dict(
        supply=(1.2, 1.8, 2.5), rho=(0.60, 0.70, 0.85), access=(0.7, 0.9, 1.0),
        premium=(0.05, 0.20, 0.4), location=1.00,
        note="Kharg Island / export terminals hit; ~2 mb/d sustained loss, spare accessible."),
    "Hormuz closure (tail)": dict(
        supply=(4.0, 9.0, 17.0), rho=(0.70, 0.85, 0.95), access=(0.10, 0.25, 0.45),
        premium=(0.2, 0.50, 1.0), location=1.10,
        note="Genuine closure attempt; most global spare trapped behind the strait."),
}
SCEN_NAMES = list(SCENARIOS.keys())


def _tri(rng, p, n):
    lo, mo, hi = p
    if hi <= lo:
        return np.full(n, mo)
    return rng.triangular(lo, mo, hi, n)


def response(supply, location, buffer, access, rho, premium, base_noise=None, rng=None):
    """Vectorised structural response: drivers -> (M1-M2, M2-M4, M1-M6) change."""
    supply_eff = np.maximum(supply * location, 1e-6)
    coverage = np.clip(buffer * access / supply_eff, 0, 1)
    E = supply * location * (1 - KAPPA * coverage)
    delta = BETA * E + premium                       # front impulse = M1-M2
    m12 = delta.copy()
    m24 = (A24 + B24 * rho) * delta
    m16 = (A16 + B16 * rho) * delta
    out = {"M1-M2": m12, "M2-M4": m24, "M1-M6": m16, "E": E, "delta": delta}
    if base_noise is not None and rng is not None:
        n = len(delta)
        for s, sd in base_noise.items():
            out[s] = out[s] + rng.normal(0, sd, n)
    return out


def simulate(n=400_000, probs=None, seed=42, with_noise=True):
    rng = np.random.default_rng(seed)
    spreads = load_daily_spreads()
    base = baseline_stats(spreads)
    base_noise = {s: 0.45 * base.loc[s, "std"] for s in SPREADS} if with_noise else None

    probs = scenario_probabilities_6() if probs is None else probs
    pvec = np.array([probs[k] for k in SCEN_NAMES], dtype=float)
    pvec /= pvec.sum()
    comp = rng.choice(len(SCEN_NAMES), size=n, p=pvec)

    buffer = rng.normal(BUFFER_MEAN, BUFFER_SD, n)
    supply = np.empty(n); rho = np.empty(n); access = np.empty(n)
    premium = np.empty(n); loc = np.empty(n)
    for k, name in enumerate(SCEN_NAMES):
        m = comp == k
        nk = int(m.sum()); sc = SCENARIOS[name]
        supply[m] = _tri(rng, sc["supply"], nk)
        rho[m] = _tri(rng, sc["rho"], nk)
        access[m] = _tri(rng, sc["access"], nk)
        premium[m] = _tri(rng, sc["premium"], nk)
        loc[m] = sc["location"]

    out = response(supply, loc, buffer, access, rho, premium, base_noise, rng)
    out.update(dict(scenario=comp, supply=supply, rho=rho, access=access,
                    premium=premium, buffer=buffer))
    return out, comp, pvec


def summarize(out, comp, pvec, spreads_df=None):
    rows = []
    for s in SPREADS:
        d = out[s]
        rows.append({
            "spread": s,
            "EV": round(float(d.mean()), 2),
            "p25": round(float(np.percentile(d, 25)), 2),
            "p75": round(float(np.percentile(d, 75)), 2),
            "p05": round(float(np.percentile(d, 5)), 2),
            "p95": round(float(np.percentile(d, 95)), 2),
            "P(widen)": round(float((d > 0).mean()), 2),
        })
    table = pd.DataFrame(rows).set_index("spread")

    scen_rows = []
    for k, name in enumerate(SCEN_NAMES):
        m = comp == k
        scen_rows.append({
            "scenario": name, "prob": round(float(pvec[k]), 3),
            "E_mb/d": round(float(out["E"][m].mean()), 2),
            **{s: round(float(out[s][m].mean()), 2) for s in SPREADS},
        })
    scen = pd.DataFrame(scen_rows).set_index("scenario")
    return table, scen


def validate(spreads_df=None):
    """IN-SAMPLE consistency check (NOT predictive validation).

    Reproduces each event's M1-M6 from its implied (delta, rho). This only shows the
    curve law is *self-consistent*: it uses the observed M1-M2 AND M2-M4 (to back out
    rho) and parameters fit on these same events, so by construction predicted~actual.
    It cannot detect over-fitting. For a real test use cross_validate_curve(). Kept for
    transparency / to show the algebra closes.
    """
    s = spreads_df if spreads_df is not None else load_daily_spreads()
    resp = event_response(s)
    rows = []
    for ev, r in resp.items():
        c = r["chg_5d"]
        delta = c["M1-M2"]
        if abs(delta) < 1e-3:
            continue
        rho_imp = ((c["M2-M4"] / delta) - A24) / B24
        pred16 = (A16 + B16 * rho_imp) * delta
        rows.append({"event": ev, "delta(M1-M2)": round(delta, 2),
                     "rho_implied": round(rho_imp, 2),
                     "M1-M6 actual": round(c["M1-M6"], 2),
                     "M1-M6 predicted": round(pred16, 2)})
    return pd.DataFrame(rows)


def _event_table(spreads_df=None):
    s = spreads_df if spreads_df is not None else load_daily_spreads()
    resp = event_response(s)
    rows = [(ev, r["chg_5d"]["M1-M2"], r["chg_5d"]["M2-M4"], r["chg_5d"]["M1-M6"])
            for ev, r in resp.items()]
    return pd.DataFrame(rows, columns=["event", "m12", "m24", "m16"])


def cross_validate_curve(spreads_df=None):
    """OUT-OF-SAMPLE test of the curve-shape law via leave-one-out.

    Honest framing of what is and isn't being tested:
      * TESTED: given the front (M1-M2) and belly (M2-M4) moves, is the back (M1-M6)
        move predictable across events by ONE shared linear curve law? We refit the law
        on the other 4 events and predict the held-out one -- genuine out-of-sample.
      * NOT TESTED here: the fundamental mapping (barrels-at-risk -> price impulse via
        BETA/KAPPA). We never independently observe 'mb/d at risk' for a past event, so
        that layer is a structural prior, not a falsifiable claim from price data.

    Compares LOO error to two baselines: a naive 'average ratio' predictor and the raw
    cross-event spread (sd). Big gap => the curve law carries real, transferable signal.
    """
    df = _event_table(spreads_df)
    r24 = df.m24 / df.m12
    r16 = df.m16 / df.m12
    rows = []
    for i in range(len(df)):
        tr = [j for j in range(len(df)) if j != i]
        b, a = np.polyfit(r24.iloc[tr], r16.iloc[tr], 1)        # refit on the other 4
        pred16 = (a + b * r24.iloc[i]) * df.m12.iloc[i]
        rows.append({"event": df.event.iloc[i],
                     "M1-M6 actual": round(df.m16.iloc[i], 2),
                     "M1-M6 LOO-pred": round(pred16, 2),
                     "residual": round(df.m16.iloc[i] - pred16, 2)})
    loo = pd.DataFrame(rows)
    naive = r16.mean()                                          # predict the mean ratio
    loo["naive-pred"] = [round(naive * df.m12.iloc[i], 2) for i in range(len(df))]
    stats = {
        "rmse_LOO_curve": float(np.sqrt((loo["residual"] ** 2).mean())),
        "rmse_naive_ratio": float(np.sqrt(((df.m16 - loo["naive-pred"]) ** 2).mean())),
        "sd_m16": float(df.m16.std()),
    }
    return loo, stats


def driver_sensitivity(target="M1-M6", seed=42):
    """Tornado: hold all drivers at the escalation-family median, flex one lo/hi.

    Target defaults to M1-M6 because that spread carries the full fan effect -- ALL
    drivers (including persistence rho) bite. The front M1-M2 impulse is rho-invariant
    by construction, so a tornado on M1-M2 would show a spurious zero for rho.
    """
    sc = SCENARIOS["Hormuz harassment"]
    med = dict(supply=sc["supply"][1], rho=sc["rho"][1], access=sc["access"][1],
               premium=sc["premium"][1], location=sc["location"], buffer=BUFFER_MEAN)

    def val(d):
        return float(response(np.array([d["supply"]]), d["location"], np.array([d["buffer"]]),
                              np.array([d["access"]]), np.array([d["rho"]]),
                              np.array([d["premium"]]))[target][0])
    base = val(med)
    # (display label, driver key, lo, hi)
    drivers = [
        ("supply (mb/d)",   "supply",  sc["supply"][0],  sc["supply"][2]),
        ("buffer access",   "access",  sc["access"][0],  sc["access"][2]),
        ("persistence rho", "rho",     sc["rho"][0],     sc["rho"][2]),
        ("premium ($/bbl)", "premium", sc["premium"][0], sc["premium"][2]),
        ("buffer (mb/d)",   "buffer",  BUFFER_MEAN - 1,  BUFFER_MEAN + 1),
    ]
    rows = []
    for label, key, lo, hi in drivers:
        d_lo = dict(med); d_lo[key] = lo
        d_hi = dict(med); d_hi[key] = hi
        rows.append({"driver": label, "low": round(val(d_lo), 2),
                     "high": round(val(d_hi), 2),
                     "swing": round(abs(val(d_hi) - val(d_lo)), 2)})
    return base, pd.DataFrame(rows).sort_values("swing", ascending=False)


# scenario families (used by the sensitivity sweep) -------------------------
ESC_FAMILY = ["Hormuz harassment", "Iranian export infra destroyed", "Hormuz closure (tail)"]
NON_ESC = ["Rapid de-escalation", "Prolonged containment"]


def latest_levels(spreads_df=None):
    """Today's spread levels ($/bbl) -- the anchor the 1-week change fans out from."""
    s = spreads_df if spreads_df is not None else load_daily_spreads()
    last = s.dropna(subset=SPREADS).iloc[-1]
    return {sp: float(last[sp]) for sp in SPREADS}


def sensitivity_to_escalation(p_grid=None, n=150_000, seed=7):
    """How EV and the 90% range respond as the ESCALATION-FAMILY probability varies.

    The single most subjective input is 'how likely is genuine escalation'. We scale the
    three escalation scenarios so their mass equals p_escalation (preserving their internal
    ratios) and rescale de-escalation/containment to fill the rest, then re-simulate. The
    scored value (~0.22) is the reference. Key read: the P05 floor barely moves (the calm
    scenarios bound the downside) while the upper tail fans out -- a bounded-downside,
    open-upside asymmetry a point forecast cannot show.
    """
    base = scenario_probabilities_6()
    esc0 = sum(base[k] for k in ESC_FAMILY)
    rest0 = sum(base[k] for k in NON_ESC)
    if p_grid is None:
        p_grid = np.linspace(0.05, 0.40, 6)
    rows = []
    for pe in p_grid:
        probs = {k: pe * base[k] / esc0 for k in ESC_FAMILY}
        probs.update({k: (1 - pe) * base[k] / rest0 for k in NON_ESC})
        out, _, _ = simulate(n=n, probs=probs, seed=seed)
        for sp in SPREADS:
            d = out[sp]
            rows.append({"p_escalation": round(float(pe), 3), "spread": sp,
                         "EV": round(float(d.mean()), 2),
                         "p05": round(float(np.percentile(d, 5)), 2),
                         "p95": round(float(np.percentile(d, 95)), 2)})
    return pd.DataFrame(rows)


def main():
    pd.set_option("display.width", 160)
    out, comp, pvec = simulate()
    table, scen = summarize(out, comp, pvec)
    print("Scenario probabilities (severity-derived) & expected moves:")
    print(scen.to_string())
    print("\n=== 1-WEEK SPREAD-CHANGE DISTRIBUTION ($/bbl) ===")
    print(table.to_string())
    print("\n=== IN-SAMPLE consistency (curve law is self-consistent, NOT predictive) ===")
    print(validate().to_string(index=False))
    print("\n=== OUT-OF-SAMPLE: leave-one-out on the curve-shape law ===")
    loo, st = cross_validate_curve()
    print(loo.to_string(index=False))
    print(f"\nRMSE  LOO-curve = {st['rmse_LOO_curve']:.2f}   "
          f"naive(mean ratio) = {st['rmse_naive_ratio']:.2f}   "
          f"raw sd(M1-M6) = {st['sd_m16']:.2f}")
    base, tor = driver_sensitivity()
    print(f"\n=== DRIVER SENSITIVITY (Hormuz-harassment, base M1-M6 = {base:.2f}) ===")
    print(tor.to_string(index=False))
    print(f"\n=== TODAY'S LEVELS (fan-chart anchor) ===")
    print({k: round(v, 2) for k, v in latest_levels().items()})
    print("\n=== SENSITIVITY TO ESCALATION PROBABILITY (M1-M6) ===")
    se = sensitivity_to_escalation()
    print(se[se.spread == "M1-M6"].to_string(index=False))


if __name__ == "__main__":
    main()
