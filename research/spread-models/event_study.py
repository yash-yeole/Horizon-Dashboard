"""Step 2 & 3: baseline weekly-change distribution + geopolitical event study.

Baseline answers "what does a normal week do to each spread?" (unconditional 5-trading-day
change distribution). The event study answers "how do geopolitical shock weeks differ?"
by extracting the 5-day spread change following real analog events in the sample.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from load_spreads import load_daily_spreads, SPREAD_DEFS

HORIZON = 5  # trading days ~ one week

# Geopolitical shock events present in the 2021-2026 sample.
# 2025-06-13 is the primary analog to the assigned headline (Israel strikes Iran energy
# infrastructure, Iran threatens the Strait of Hormuz).
EVENTS = {
    "Russia invades Ukraine":      "2022-02-24",
    "Hamas attack / Gaza war":     "2023-10-07",
    "Iran->Israel strike (Apr24)": "2024-04-13",
    "Iran->Israel barrage (Oct24)":"2024-10-01",
    "Israel strikes Iran (Jun25)": "2025-06-13",  # PRIMARY ANALOG
}


def weekly_changes(spreads: pd.DataFrame, horizon: int = HORIZON) -> pd.DataFrame:
    """Forward h-trading-day change of each spread (level at t+h minus level at t)."""
    return spreads.shift(-horizon) - spreads


def baseline_stats(spreads: pd.DataFrame, horizon: int = HORIZON) -> pd.DataFrame:
    chg = weekly_changes(spreads, horizon)
    desc = pd.DataFrame({
        "mean": chg.mean(),
        "std": chg.std(),
        "p05": chg.quantile(0.05),
        "p50": chg.quantile(0.50),
        "p95": chg.quantile(0.95),
        "skew": chg.skew(),
        "kurt": chg.kurt(),
    })
    return desc


def _nearest_idx(spreads: pd.DataFrame, date: str) -> int:
    target = pd.Timestamp(date)
    pos = spreads.index.searchsorted(target)
    return int(min(pos, len(spreads) - 1))


def event_response(spreads: pd.DataFrame, horizon: int = HORIZON) -> dict:
    """For each event: spread change from the day BEFORE the event over the next
    `horizon` trading days, plus the peak (max) move within the window."""
    rows = {}
    for name, date in EVENTS.items():
        i = _nearest_idx(spreads, date)
        base_i = max(i - 1, 0)             # last close before the event hits
        end_i = min(base_i + horizon, len(spreads) - 1)
        base = spreads.iloc[base_i]
        end = spreads.iloc[end_i]
        window = spreads.iloc[base_i:end_i + 1]
        peak = window.max() - base        # max backwardation impulse in the week
        rows[name] = {
            "base_date": spreads.index[base_i].date().isoformat(),
            "chg_5d": (end - base),
            "peak_5d": peak,
        }
    return rows


def event_summary(spreads: pd.DataFrame, horizon: int = HORIZON):
    """Aggregate event responses into a mean drift and a vol-multiplier vs baseline."""
    base = baseline_stats(spreads, horizon)
    resp = event_response(spreads, horizon)

    chg = pd.DataFrame({k: v["chg_5d"] for k, v in resp.items()}).T  # events x spreads
    peak = pd.DataFrame({k: v["peak_5d"] for k, v in resp.items()}).T

    summ = pd.DataFrame(index=SPREAD_DEFS.keys())
    summ["base_std"] = base["std"]
    summ["event_mean_chg"] = chg.mean()
    summ["event_std_chg"] = chg.std()
    summ["event_mean_peak"] = peak.mean()
    summ["event_max_peak"] = peak.max()
    # vol multiplier: how much wider event-week moves are vs a normal week
    summ["vol_mult"] = summ["event_std_chg"] / summ["base_std"]
    return summ, chg, peak, base


if __name__ == "__main__":
    pd.set_option("display.width", 120)
    s = load_daily_spreads()

    print("=" * 70)
    print("BASELINE: unconditional 5-trading-day change distribution (2021-2026)")
    print("=" * 70)
    print(baseline_stats(s).round(3))

    print("\n" + "=" * 70)
    print("EVENT STUDY: 5-day spread change following geopolitical shocks")
    print("=" * 70)
    resp = event_response(s)
    for name, r in resp.items():
        print(f"\n{name}  (base {r['base_date']})")
        print("   5d change:", r["chg_5d"].round(3).to_dict())
        print("   peak move:", r["peak_5d"].round(3).to_dict())

    print("\n" + "=" * 70)
    print("EVENT SUMMARY vs baseline")
    print("=" * 70)
    summ, chg, peak, base = event_summary(s)
    print(summ.round(3))
