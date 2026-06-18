"""
trade_log.py — the audit trail.

Two ledgers, both pandas-backed and exportable to parquet/csv:

1. SignalLog — EVERY opportunity the model emits (not just executed trades):
   timestamp, regime, instrument, structure, signal/action, z, direction,
   spread, fair_value, rationale, confidence, ood.

2. TradeLog — the full trade lifecycle, one row per round-trip trade:
   planned entry/target/stop, actual entry/exit ts+price, direction, size,
   gross PnL, costs/slippage, net PnL, return, hold time, exit reason,
   plus running equity contribution.

Slippage/costs are parameterized and default to zero (as specified).
"""
from __future__ import annotations
from dataclasses import dataclass, field

import pandas as pd


# --------------------------------------------------------------------- signals
class SignalLog:
    def __init__(self):
        self._rows: list[dict] = []

    def record(self, ts, instrument, structure, sig):
        self._rows.append({
            "timestamp": pd.Timestamp(ts),
            "instrument": instrument,
            "structure": structure,
            "regime": sig.regime,
            "action": sig.action,
            "direction": sig.direction,
            "z": sig.z,
            "spread": sig.spread,
            "fair_value": sig.fair_value,
            "resid_std": sig.resid_std,
            "confidence": sig.confidence,
            "ood": sig.ood,
            "planned_entry": sig.planned_entry,
            "target": sig.target,
            "stop": sig.stop,
            "rationale": sig.rationale,
        })

    def frame(self) -> pd.DataFrame:
        if not self._rows:
            return pd.DataFrame()
        return pd.DataFrame(self._rows).set_index("timestamp").sort_index()


# ---------------------------------------------------------------------- trades
@dataclass
class OpenTrade:
    instrument: str
    structure: str
    direction: str            # LONG | SHORT (of the spread)
    size: int                 # +1 long, -1 short (units of the spread)
    regime: str
    confidence: str
    entry_ts: object
    entry_price: float        # actual fill (spread)
    planned_entry: float
    target: float
    stop: float
    entry_rationale: str
    entry_slippage: float = 0.0


@dataclass
class TradeLog:
    cost_per_trade: float = 0.0      # fixed cost per side
    slippage: float = 0.0            # spread units applied adversely on each fill
    _rows: list[dict] = field(default_factory=list)

    def close(self, t: OpenTrade, exit_ts, exit_price: float, exit_reason: str,
              equity_before: float) -> dict:
        sgn = 1 if t.direction == "LONG" else -1
        # adverse slippage on both fills (already assumed 0 by default)
        eff_entry = t.entry_price + self.slippage * sgn
        eff_exit = exit_price - self.slippage * sgn
        gross = sgn * (exit_price - t.entry_price) * t.size
        costs = 2 * self.cost_per_trade + abs(self.slippage) * 2 * abs(t.size)
        net = sgn * (eff_exit - eff_entry) * t.size - 2 * self.cost_per_trade
        row = {
            "instrument": t.instrument, "structure": t.structure,
            "direction": t.direction, "size": t.size, "regime": t.regime,
            "confidence": t.confidence,
            "entry_ts": pd.Timestamp(t.entry_ts), "entry_price": t.entry_price,
            "planned_entry": t.planned_entry, "target": t.target, "stop": t.stop,
            "exit_ts": pd.Timestamp(exit_ts), "exit_price": exit_price,
            "exit_reason": exit_reason,
            "hold_bars": None,  # filled by engine if desired
            "hold_time": pd.Timestamp(exit_ts) - pd.Timestamp(t.entry_ts),
            "gross_pnl": gross, "costs": costs, "slippage": abs(self.slippage) * 2 * abs(t.size),
            "net_pnl": net,
            "return": net / abs(t.entry_price) if t.entry_price else float("nan"),
            "equity_before": equity_before,
            "equity_after": equity_before + net,
            "win": net > 0,
            "entry_rationale": t.entry_rationale,
        }
        self._rows.append(row)
        return row

    def frame(self) -> pd.DataFrame:
        if not self._rows:
            return pd.DataFrame()
        df = pd.DataFrame(self._rows)
        df["cum_pnl"] = df["net_pnl"].cumsum()
        return df
