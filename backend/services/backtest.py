"""
backtest.py — serve the cached full-history intraday backtest of the REGIME /
FAIR-VALUE model on the WTI & Brent calendar (c1-c2) spreads.

The heavy 5.4-year simulation is run offline by backtest_intraday.py, which reuses
the live model engine verbatim and writes per-structure trade parquets plus a
summary JSON to strategy/cache. This service just reads that cache and shapes it
for the dashboard's Backtest view:

  * FLAT 1-contract sizing (no compounding) — one spread = 1,000 bbl, so the $ PnL
    of a trade is net_pnl_points * CONTRACT_BBL. Fixed-fractional risk-to-stop
    sizing was rejected: ~10% of entries fire just below the stop band, giving a
    near-zero stop distance that the sizer divides by, producing absurd contract
    counts and a 15-min gap-through-stop ruin. Flat sizing isolates the strategy
    edge from that pathology.
  * combined equity curve in dollars, replayed chronologically by exit time
  * summary (n_trades, win_rate, net_pnl_usd) overall and per structure
  * the trade blotter (newest first, capped) tagged with the instrument label
  * open positions still held at the end of the data (the rolling c2-c3 structures
    typically finish mid-trade), read from the summary and tagged with the label
"""
from __future__ import annotations

import json
import os

import pandas as pd

from config import settings

_CACHE_DIR = os.path.join(settings.paper_strategy_dir, "cache")
_SUMMARY_PATH = os.path.join(_CACHE_DIR, "bt_intraday_summary.json")

# one calendar spread = 1,000 bbl; spread $/bbl * CONTRACT_BBL = $ per contract.
CONTRACT_BBL = 1000
# flat-1-contract notional base for the equity curve.
STARTING_EQUITY = 100_000.0
# cap the blotter so the payload stays light (UI shows latest first).
_MAX_TRADES = 80


def _load_trades() -> pd.DataFrame:
    """Concatenate every cached structure parquet into one tagged blotter."""
    if not os.path.exists(_SUMMARY_PATH):
        return pd.DataFrame()
    with open(_SUMMARY_PATH) as f:
        summary = json.load(f)
    frames = []
    for key, meta in summary.get("structures", {}).items():
        path = os.path.join(_CACHE_DIR, meta.get("parquet", f"bt_intraday_{key}.parquet"))
        if not os.path.exists(path):
            continue
        df = pd.read_parquet(path)
        if df.empty:
            continue
        df["key"] = key
        df["label"] = meta.get("label", key)
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    out["entry_ts"] = pd.to_datetime(out["entry_ts"], errors="coerce")
    out["exit_ts"] = pd.to_datetime(out["exit_ts"], errors="coerce")
    return out.sort_values("exit_ts").reset_index(drop=True)


def _equity_curve(trades: pd.DataFrame) -> list[dict]:
    """FLAT 1-contract dollar equity, compounded only by realized PnL order."""
    if trades.empty:
        return []
    pnl_usd = trades["net_pnl"].astype(float) * CONTRACT_BBL
    equity = STARTING_EQUITY + pnl_usd.cumsum()
    return [
        {"ts": ts.isoformat() if pd.notna(ts) else None, "equity": round(float(eq), 2)}
        for ts, eq in zip(trades["exit_ts"], equity)
    ]


def _trade_row(r: pd.Series) -> dict:
    net_usd = float(r["net_pnl"]) * CONTRACT_BBL
    return {
        "key": r.get("key"),
        "label": r.get("label"),
        "direction": r.get("direction"),
        "regime": r.get("regime"),
        "confidence": r.get("confidence"),
        "entry_ts": r["entry_ts"].isoformat() if pd.notna(r["entry_ts"]) else None,
        "entry_price": _f(r.get("entry_price")),
        "exit_ts": r["exit_ts"].isoformat() if pd.notna(r["exit_ts"]) else None,
        "exit_price": _f(r.get("exit_price")),
        "exit_reason": r.get("exit_reason"),
        "target": _f(r.get("target")),
        "stop": _f(r.get("stop")),
        "net_pnl_pts": _f(r.get("net_pnl")),
        "net_pnl_usd": round(net_usd, 2),
        "win": bool(r.get("win")),
        "hold_bars": _i(r.get("hold_bars")),
    }


def _f(v):
    try:
        f = float(v)
        return f if f == f else None  # drop NaN
    except (TypeError, ValueError):
        return None


def _i(v):
    f = _f(v)
    return int(f) if f is not None else None


def get_backtest() -> dict:
    """Full backtest payload for the dashboard Backtest view."""
    trades = _load_trades()
    if trades.empty:
        return {
            "available": False,
            "summary": {"n_trades": 0, "wins": 0, "win_rate": 0.0,
                        "net_pnl_usd": 0.0, "net_pnl_pts": 0.0,
                        "starting_equity": STARTING_EQUITY,
                        "final_equity": STARTING_EQUITY, "max_drawdown_usd": 0.0},
            "structures": [], "equity_curve": [], "trades": [],
            "open_positions": [], "sizing": "flat_1_contract",
            "contract_bbl": CONTRACT_BBL,
        }

    n = int(len(trades))
    wins = int(trades["win"].astype(bool).sum())
    net_pts = float(trades["net_pnl"].astype(float).sum())
    net_usd = net_pts * CONTRACT_BBL

    curve = _equity_curve(trades)
    eq_series = pd.Series([p["equity"] for p in curve], dtype=float)
    final_eq = float(eq_series.iloc[-1]) if len(eq_series) else STARTING_EQUITY
    running_max = eq_series.cummax()
    max_dd = float((eq_series - running_max).min()) if len(eq_series) else 0.0

    # per-structure breakdown
    structures = []
    for key, g in trades.groupby("key", sort=False):
        sn = int(len(g))
        sw = int(g["win"].astype(bool).sum())
        spts = float(g["net_pnl"].astype(float).sum())
        structures.append({
            "key": key,
            "label": g["label"].iloc[0],
            "n_trades": sn,
            "wins": sw,
            "win_rate": round(sw / sn * 100, 1) if sn else 0.0,
            "net_pnl_pts": round(spts, 4),
            "net_pnl_usd": round(spts * CONTRACT_BBL, 2),
            "first_trade": g["exit_ts"].min().isoformat() if pd.notna(g["exit_ts"].min()) else None,
            "last_trade": g["exit_ts"].max().isoformat() if pd.notna(g["exit_ts"].max()) else None,
        })

    # return EVERY trade, newest first — the frontend computes the fixed-fractional
    # sized equity curve client-side (so investment / risk% are adjustable live),
    # then caps the blotter display itself. _MAX_TRADES is just the display hint.
    ordered = trades.sort_values("exit_ts", ascending=False)
    blotter = [_trade_row(r) for _, r in ordered.iterrows()]

    with open(_SUMMARY_PATH) as f:
        meta = json.load(f)

    open_positions = []
    for key, sm in meta.get("structures", {}).items():
        op = sm.get("open_position")
        if op:
            open_positions.append({"key": key, "label": sm.get("label", key), **op})

    return {
        "available": True,
        "generated_at": meta.get("generated_at"),
        "sizing": "flat_1_contract",
        "contract_bbl": CONTRACT_BBL,
        "summary": {
            "n_trades": n,
            "wins": wins,
            "win_rate": round(wins / n * 100, 1) if n else 0.0,
            "net_pnl_pts": round(net_pts, 4),
            "net_pnl_usd": round(net_usd, 2),
            "starting_equity": STARTING_EQUITY,
            "final_equity": round(final_eq, 2),
            "max_drawdown_usd": round(max_dd, 2),
            "first_bar": min((s["first_bar"] for s in meta.get("structures", {}).values()), default=None),
            "last_bar": max((s["last_bar"] for s in meta.get("structures", {}).values()), default=None),
        },
        "structures": structures,
        "equity_curve": curve,
        "trades": blotter,
        "trades_shown": min(_MAX_TRADES, len(blotter)),
        "display_cap": _MAX_TRADES,
        "open_positions": open_positions,
    }
