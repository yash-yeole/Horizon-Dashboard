"""
backtest.py — the event loop that ties the engine together.

    BacktestFeed (15-min bars)
        -> attach daily regime + fair value (fair_value.daily_fairvalue_map)
        -> CalendarMeanReversion decides per bar
        -> position state machine -> fills
        -> SignalLog (every opportunity) + TradeLog (lifecycle) + equity

The SAME engine runs live: swap BacktestFeed for LiveFeed and call step() per poll.
"""
from __future__ import annotations
from dataclasses import dataclass

import pandas as pd

import data_feed as feed
import fair_value as fv
from strategy import CalendarMeanReversion, DayContext
from trade_log import SignalLog, TradeLog, OpenTrade
import metrics


@dataclass
class EngineConfig:
    product: str = "CL"
    target: str = "cal"
    instrument: str = "WTI"
    structure: str = "c1-c2"
    size: int = 1
    cost_per_trade: float = 0.0
    slippage: float = 0.0
    starting_equity: float = 0.0


class Engine:
    """Stateful engine usable for both backtest (iterate) and live (step per bar)."""

    def __init__(self, cfg: EngineConfig | None = None,
                 strategy: CalendarMeanReversion | None = None,
                 day_map: pd.DataFrame | None = None):
        self.cfg = cfg or EngineConfig()
        self.strat = strategy or CalendarMeanReversion()
        self.signals = SignalLog()
        self.trades = TradeLog(cost_per_trade=self.cfg.cost_per_trade,
                               slippage=self.cfg.slippage)
        self.equity = self.cfg.starting_equity
        self.open: OpenTrade | None = None
        self._open_bars = 0
        # daily regime/fair-value context, indexed by normalized date
        if day_map is None:
            day_map = fv.daily_fairvalue_map(self.cfg.product, self.cfg.target)
        self.day_map = day_map

    # ---- per-bar context -----------------------------------------------------
    def _ctx(self, ts) -> DayContext | None:
        day = pd.Timestamp(ts).normalize()
        if day not in self.day_map.index:
            return None
        r = self.day_map.loc[day]
        if isinstance(r, pd.DataFrame):
            r = r.iloc[-1]
        return DayContext(
            date=day, regime=r.get("regime_eff", "?"),
            fair_value=float(r["fair_value"]), resid_std=float(r["resid_std_train"]),
            ood=bool(r.get("ood", False)), confidence=str(r.get("confidence", "?")),
            near_boundary=bool(r.get("near_boundary", False)),
            regime_n=float(r.get("regime_n", 0) or 0),
        )

    # ---- single bar ----------------------------------------------------------
    def step(self, bar: feed.Bar):
        ctx = self._ctx(bar.ts)
        if ctx is None:
            return
        if self.open is None:
            sig = self.strat.decide_entry(bar.spread, ctx)
            self.signals.record(bar.ts, bar.instrument, bar.structure, sig)
            if sig.action in ("BUY", "SELL"):
                self.open = OpenTrade(
                    instrument=bar.instrument, structure=bar.structure,
                    direction=sig.direction, size=self.cfg.size,
                    regime=ctx.regime, confidence=ctx.confidence,
                    entry_ts=bar.ts, entry_price=bar.spread,
                    planned_entry=sig.planned_entry, target=sig.target,
                    stop=sig.stop, entry_rationale=sig.rationale,
                )
                self._open_bars = 0
        else:
            self._open_bars += 1
            reason = self.strat.decide_exit(bar.spread, ctx, self.open.direction)
            if reason:
                row = self.trades.close(self.open, bar.ts, bar.spread, reason, self.equity)
                row["hold_bars"] = self._open_bars
                self.equity = row["equity_after"]
                self.open = None

    def run(self, bars=None):
        """Backtest over a feed (defaults to BacktestFeed for the configured product)."""
        if bars is None:
            bars = feed.BacktestFeed(self.cfg.product, self.cfg.instrument,
                                     self.cfg.structure)
        for bar in bars:
            self.step(bar)
        # mark-to-market any still-open position at the last bar (informational)
        return self.results()

    def results(self) -> dict:
        sg = self.signals.frame()
        tr = self.trades.frame()
        return {
            "signals": sg,
            "trades": tr,
            "summary": metrics.summary(tr, sg),
            "by_regime": metrics.by_regime(tr),
            "equity_curve": metrics.equity_curve(tr, self.cfg.starting_equity),
            "open_position": self.open,
        }


def run_backtest(cfg: EngineConfig | None = None,
                 strategy: CalendarMeanReversion | None = None) -> dict:
    return Engine(cfg, strategy).run()


if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore")
    res = run_backtest(EngineConfig(product="CL"))
    print("=== SUMMARY ===")
    for k, v in res["summary"].items():
        print(f"  {k}: {v}")
    print(f"\nsignals: {len(res['signals'])} bars, "
          f"entries={int(res['signals']['action'].isin(['BUY','SELL']).sum()) if not res['signals'].empty else 0}")
    if not res["signals"].empty:
        print(res["signals"]["action"].value_counts().to_dict())
    if not res["trades"].empty:
        print("\n=== TRADES ===")
        print(res["trades"][["entry_ts", "exit_ts", "direction", "entry_price",
                             "exit_price", "exit_reason", "net_pnl"]].to_string())
