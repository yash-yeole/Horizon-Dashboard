"""
metrics.py — performance statistics from the trade log + equity curve.

All metrics are computed in spread points (PnL is in the spread's native units,
e.g. $/bbl for the WTI calendar).  No annualization assumptions are baked in
beyond an optional periods-per-year for Sharpe.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def equity_curve(trades: pd.DataFrame, starting_equity: float = 0.0) -> pd.Series:
    """Equity over trade-exit times (realized PnL only)."""
    if trades.empty:
        return pd.Series(dtype=float)
    eq = starting_equity + trades.sort_values("exit_ts")["net_pnl"].cumsum()
    eq.index = trades.sort_values("exit_ts")["exit_ts"].values
    return eq


def max_drawdown(eq: pd.Series) -> float:
    if eq.empty:
        return 0.0
    peak = eq.cummax()
    return float((eq - peak).min())


def summary(trades: pd.DataFrame, signals: pd.DataFrame | None = None,
            periods_per_year: int = 252) -> dict:
    if trades is None or trades.empty:
        out = {"n_trades": 0}
        if signals is not None:
            out["n_signals"] = len(signals)
            out["n_no_trade"] = int((signals["action"] == "NO_TRADE").sum()) if not signals.empty else 0
        return out

    net = trades["net_pnl"]
    wins = trades[trades["win"]]
    losses = trades[~trades["win"]]
    eq = equity_curve(trades)
    ret = net / trades["entry_price"].abs().replace(0, np.nan)

    out = {
        "n_trades": int(len(trades)),
        "n_wins": int(len(wins)),
        "n_losses": int(len(losses)),
        "win_rate": float(len(wins) / len(trades)),
        "gross_pnl": float(trades["gross_pnl"].sum()),
        "total_costs": float(trades["costs"].sum()),
        "net_pnl": float(net.sum()),
        "avg_pnl": float(net.mean()),
        "avg_win": float(wins["net_pnl"].mean()) if len(wins) else 0.0,
        "avg_loss": float(losses["net_pnl"].mean()) if len(losses) else 0.0,
        "profit_factor": float(wins["net_pnl"].sum() / abs(losses["net_pnl"].sum()))
                         if len(losses) and losses["net_pnl"].sum() != 0 else float("inf"),
        "best": float(net.max()),
        "worst": float(net.min()),
        "max_drawdown": max_drawdown(eq),
        "avg_hold": str(trades["hold_time"].mean()),
        "sharpe": float(ret.mean() / ret.std() * np.sqrt(periods_per_year))
                  if ret.std(ddof=0) and len(ret) > 1 else 0.0,
        "exit_reasons": trades["exit_reason"].value_counts().to_dict(),
    }
    if signals is not None and not signals.empty:
        out["n_signals"] = int(len(signals))
        out["n_no_trade"] = int((signals["action"] == "NO_TRADE").sum())
        out["n_entries"] = int(signals["action"].isin(["BUY", "SELL"]).sum())
    return out


def by_regime(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame()
    g = trades.groupby("regime")
    return pd.DataFrame({
        "n": g.size(),
        "win_rate": g["win"].mean(),
        "net_pnl": g["net_pnl"].sum(),
        "avg_pnl": g["net_pnl"].mean(),
    }).sort_values("net_pnl", ascending=False)
