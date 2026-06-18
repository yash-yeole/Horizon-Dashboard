"""
backtest_intraday.py — full-history intraday backtest of the REGIME / FAIR-VALUE
model on the WTI and Brent calendar (c1-c2) spreads.

Idea (intraday z-score from the daily fair value):
    * daily anchor  : the trained model's daily fair_value + resid_std_train[regime]
                      (fair_value.scored_daily — scored over the whole CSV history)
    * intraday bars : 1-min weighted-mid curve CSVs (data/CL_data.csv, LCO_data.csv)
                      resampled to 15-min to match the live decision cadence
    * decision      : z(t) = (spread_15m - fair_value_day) / resid_std_day, then the
                      SAME CalendarMeanReversion engine the live "model" engine uses
                      (entry 1.0 / exit 0.5 / stop 2.5 / extreme 3.0).

This reuses strategy.Engine verbatim, so positions, exits and PnL match the live
model engine exactly — only the bar source (historical CSV) and the day_map
(full history instead of just the DB days) differ. Output is cached to parquet
and served by /api/paper/backtest.
"""
from __future__ import annotations
import os
import sys
import time
import json
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.abspath(__file__))
_STRAT_DIR = os.path.join(HERE, "strategy")
if _STRAT_DIR not in sys.path:
    sys.path.insert(0, _STRAT_DIR)

# the trained model lives in the original Regime/model location; its ../data holds
# the multi-year 1-min CSVs. Allow override but default to the known location.
_DEFAULT_MODEL_DIR = os.path.abspath(
    os.path.join(HERE, "..", "..", "..", "Regime", "model"))
os.environ.setdefault("REGIME_MODEL_DIR", _DEFAULT_MODEL_DIR)
MODEL_DIR = os.environ["REGIME_MODEL_DIR"]
DATA_DIR = os.environ.get(
    "REGIME_DATA_CSV_DIR", os.path.abspath(os.path.join(MODEL_DIR, "..", "data")))

import fair_value as fv                                   # noqa: E402
from strategy import CalendarMeanReversion, DayContext    # noqa: E402
from backtest import Engine, EngineConfig                 # noqa: E402

CACHE_DIR = os.path.join(_STRAT_DIR, "cache")

# product -> (intraday csv, model product code, instrument label, dashboard label)
PRODUCTS = {
    "wti_cal":   {"csv": "CL_data.csv",  "product": "CL", "instrument": "WTI",   "label": "WTI C1-C2"},
    "brent_cal": {"csv": "LCO_data.csv", "product": "CO", "instrument": "Brent", "label": "Brent C1-C2"},
}


class _Bar:
    __slots__ = ("ts", "spread", "instrument", "structure")

    def __init__(self, ts, spread, instrument, structure):
        self.ts = ts
        self.spread = spread
        self.instrument = instrument
        self.structure = structure


def _load_15min_spread(csv_name: str) -> pd.Series:
    """Read the 1-min weighted-mid curve CSV, build the c1-c2 spread, resample to
    15-min (last value per bin). Returns a tz-naive Series indexed by bar time."""
    path = os.path.join(DATA_DIR, csv_name)
    # line 0 is a '#meta:' comment, line 1 is the real header
    df = pd.read_csv(
        path, skiprows=[0],
        usecols=["timestamp", "c1||weighted_mid", "c2||weighted_mid"],
    )
    ts = pd.to_datetime(df["timestamp"], utc=True, errors="coerce").dt.tz_localize(None)
    spread = df["c1||weighted_mid"].astype(float) - df["c2||weighted_mid"].astype(float)
    s = pd.Series(spread.values, index=ts).dropna().sort_index()
    # 15-min bars: last observed spread in each bin (matches the live "close" bar)
    bars = s.resample("15min").last().dropna()
    return bars


def _day_map(product: str) -> pd.DataFrame:
    """Full-history daily fair-value map (one row per scored day)."""
    sig = fv.scored_daily(product, "cal")
    cols = ["regime_eff", "fair_value", "resid_std_train", "ood", "confidence",
            "near_boundary", "regime_n"]
    cols = [c for c in cols if c in sig.columns]
    dm = sig[cols].copy()
    dm.index = pd.DatetimeIndex(dm.index).normalize()
    dm = dm[~dm.index.duplicated(keep="last")]
    return dm


def run_product(key: str) -> dict:
    cfg_meta = PRODUCTS[key]
    t0 = time.time()
    print(f"[{key}] loading 15-min spread from {cfg_meta['csv']} …")
    bars = _load_15min_spread(cfg_meta["csv"])
    print(f"[{key}] {len(bars):,} 15-min bars "
          f"({bars.index.min()} -> {bars.index.max()}); scoring daily fair value …")
    dm = _day_map(cfg_meta["product"])
    print(f"[{key}] day_map: {len(dm)} days; running engine …")

    eng = Engine(
        cfg=EngineConfig(product=cfg_meta["product"], target="cal",
                         instrument=cfg_meta["instrument"], structure="c1-c2",
                         size=1, cost_per_trade=0.0, slippage=0.0,
                         starting_equity=0.0),
        # model thresholds 1.0/0.5/2.5/3.0; entry_ceiling=2.0 -> open only in
        # [1.0, 2.0), leaving >=0.5σ of room to the stop (2.5). This raises win
        # rate AND guarantees a non-degenerate stop distance so fixed-fractional
        # sizing never divides by ~0 (the old ruin pathology).
        strategy=CalendarMeanReversion(entry_ceiling=2.0),
        day_map=dm,
    )
    inst, struct = cfg_meta["instrument"], "c1-c2"
    for ts, spread in bars.items():
        eng.step(_Bar(ts, float(spread), inst, struct))

    tr = eng.trades.frame()
    n = len(tr)
    wins = int(tr["win"].sum()) if n else 0
    net_pts = float(tr["net_pnl"].sum()) if n else 0.0
    open_pos = eng.open
    print(f"[{key}] DONE in {time.time()-t0:.1f}s — trades={n} "
          f"win={wins/n*100 if n else 0:.1f}% net_pts={net_pts:+.3f} "
          f"open={'Y' if open_pos else 'N'}")
    return {"key": key, "label": cfg_meta["label"], "trades": tr,
            "open_position": open_pos, "n": n, "wins": wins, "net_pts": net_pts,
            "first_bar": str(bars.index.min()), "last_bar": str(bars.index.max())}


# columns we keep in the cached trade parquet (mapped to the dashboard PaperTrade)
_TRADE_COLS = ["direction", "regime", "confidence", "entry_ts", "entry_price",
               "exit_ts", "exit_price", "exit_reason", "target", "stop",
               "net_pnl", "win", "hold_bars"]


def main():
    os.makedirs(CACHE_DIR, exist_ok=True)
    summary = {"generated_at": pd.Timestamp.utcnow().isoformat(), "structures": {}}
    for key in PRODUCTS:
        res = run_product(key)
        tr = res["trades"]
        if not tr.empty:
            keep = [c for c in _TRADE_COLS if c in tr.columns]
            out = tr[keep].copy()
            out["entry_ts"] = pd.to_datetime(out["entry_ts"]).astype(str)
            out["exit_ts"] = pd.to_datetime(out["exit_ts"]).astype(str)
            out["key"] = key
            out["label"] = res["label"]
        else:
            out = pd.DataFrame(columns=_TRADE_COLS + ["key", "label"])
        path = os.path.join(CACHE_DIR, f"bt_intraday_{key}.parquet")
        out.to_parquet(path)
        op = res["open_position"]
        summary["structures"][key] = {
            "label": res["label"], "n_trades": res["n"], "wins": res["wins"],
            "net_pts": res["net_pts"], "first_bar": res["first_bar"],
            "last_bar": res["last_bar"],
            "open_position": (None if op is None else {
                "direction": op.direction, "entry_ts": str(op.entry_ts),
                "entry_price": float(op.entry_price), "target": float(op.target),
                "stop": float(op.stop), "regime": op.regime,
            }),
            "parquet": os.path.basename(path),
        }
        print(f"[{key}] wrote {path} ({len(out)} rows)")
    with open(os.path.join(CACHE_DIR, "bt_intraday_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print("\nSummary:", json.dumps(summary["structures"], indent=2, default=str))


if __name__ == "__main__":
    main()
