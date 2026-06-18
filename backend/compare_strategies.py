"""
compare_strategies.py — head-to-head: regime fair-value model vs rolling-mean.

Runs both strategies through the SAME backtest Engine over the SAME historical
bar universe (the cal structures the live DB supports) and prints a side-by-side
performance table. Also sweeps the rolling lookback (10/15/20/30).

Both strategies see only the days that have a daily fair-value context, so the
comparison is apples-to-apples on an identical bar set. The rolling strategy
ignores the context values; it only borrows the regime label for the breakdown.

Run:  python backend/compare_strategies.py
"""
from __future__ import annotations

import os
import sys
import warnings

warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "strategy"))

import pandas as pd                                       # noqa: E402
from strategy import CalendarMeanReversion, RollingMeanReversion  # noqa: E402
from backtest import Engine, EngineConfig                # noqa: E402

_CACHE_DIR = os.path.join(HERE, "strategy", "cache")


def _load_day_map(product: str, target: str):
    """Read the precomputed daily fair-value parquet (same cache the live service
    uses) instead of recomputing via the heavy model pipeline."""
    p = os.path.join(_CACHE_DIR, f"fv_{product}_{target}.parquet")
    if not os.path.exists(p):
        return None
    return pd.read_parquet(p)

# the live-DB tradeable cal structures (flys are watch-only -> skipped)
STRUCTS = [
    dict(key="wti_cal",   product="CL", target="cal", instrument="WTI",   structure="c1-c2"),
    dict(key="brent_cal", product="CO", target="cal", instrument="Brent", structure="c1-c2"),
]

MODEL_KW = dict(entry=1.0, exit_=0.5, stop=2.5, z_extreme=3.0)   # unified model thresholds
ROLL_KW  = dict(entry=2.0, exit_=0.5, stop=3.0, z_extreme=3.5)   # friend's rolling thresholds
LOOKBACKS = [10, 15, 20, 30]


def _run(st: dict, strat, day_map):
    cfg = EngineConfig(product=st["product"], target=st["target"],
                       instrument=st["instrument"], structure=st["structure"])
    return Engine(cfg, strategy=strat, day_map=day_map).run()


def _row(name: str, res: dict) -> dict:
    s = res["summary"]
    op = res.get("open_position")
    return dict(name=name, n=s.get("n_trades", 0), win=s.get("win_rate", 0.0),
                net=s.get("net_pnl", 0.0), pf=s.get("profit_factor", 0.0),
                mdd=s.get("max_drawdown", 0.0), sharpe=s.get("sharpe", 0.0),
                exits=s.get("exit_reasons", {}), open=(op.direction if op else "-"))


def main():
    for st in STRUCTS:
        print("\n" + "=" * 78)
        print(f"{st['key']}   ({st['instrument']} {st['structure']})")
        print("=" * 78)
        day_map = _load_day_map(st["product"], st["target"])
        if day_map is None or day_map.empty:
            print("  no fair-value cache — run refresh_fairvalue.py first")
            continue

        rows = [_row("MODEL (1.0/0.5/2.5/3.0)",
                     _run(st, CalendarMeanReversion(**MODEL_KW), day_map))]
        for L in LOOKBACKS:
            rows.append(_row(f"ROLL{L} (2.0/0.5/3.0/3.5)",
                             _run(st, RollingMeanReversion(lookback=L, **ROLL_KW), day_map)))

        hdr = (f"{'strategy':<26}{'n':>4}{'win%':>7}{'net':>10}"
               f"{'pf':>7}{'mdd':>9}{'sharpe':>8}  open")
        print(hdr)
        print("-" * len(hdr))
        for r in rows:
            pf = "inf" if r["pf"] == float("inf") else f"{r['pf']:.2f}"
            print(f"{r['name']:<26}{r['n']:>4}{r['win'] * 100:>6.1f}%{r['net']:>10.2f}"
                  f"{pf:>7}{r['mdd']:>9.2f}{r['sharpe']:>8.2f}  {r['open']}")

        print("\nexit reasons:")
        for r in rows:
            print(f"  {r['name']:<26} {r['exits']}")


if __name__ == "__main__":
    main()
