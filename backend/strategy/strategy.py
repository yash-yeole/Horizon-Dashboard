"""
strategy.py — turn (regime + deviation-from-fair-value) into a trade decision.

Pure decision logic, no PnL / no I/O.  The backtest (or live loop) owns position
state and calls:
    * decide_entry(z, ctx)        when flat  -> Signal (BUY / SELL / NO_TRADE)
    * decide_exit(z, position)    when in a position -> exit reason or None

z is the live, intraday z-score computed by the engine as
    z = (spread_live - fair_value_day) / resid_std_train[regime_day]

Conventions (spread = c1 - c2):
    z > 0  -> spread RICH  vs fair value -> SELL the spread (SHORT)
    z < 0  -> spread CHEAP vs fair value -> BUY  the spread (LONG)
Levels:
    target = fair_value           (mean-revert to z = 0)
    stop   = fair_value +/- STOP * resid_std   (z hits +/- STOP)
"""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass, field

import numpy as np

# unified |z| thresholds (identical to model/pipeline.py and app/config.py)
ENTRY, EXIT, STOP, Z_EXTREME = 1.0, 0.5, 2.5, 3.0

# rolling-mean baseline thresholds (self-normalized z runs hotter than the model's,
# so entry sits higher). Anchor = rolling mean of recent live spreads — no model.
ROLL_LOOKBACK, ROLL_ENTRY, ROLL_EXIT, ROLL_STOP, ROLL_Z_EXTREME = 15, 2.0, 0.5, 3.0, 3.5


@dataclass
class DayContext:
    """Per-day model output, constant within the trading day."""
    date: object
    regime: str
    fair_value: float
    resid_std: float
    ood: bool
    confidence: str
    near_boundary: bool = False
    regime_n: float = 0.0


@dataclass
class Signal:
    action: str            # "BUY" (long spread) | "SELL" (short spread) | "NO_TRADE"
    z: float
    direction: str         # "LONG" | "SHORT" | "FLAT"
    spread: float
    fair_value: float
    resid_std: float
    regime: str
    confidence: str
    ood: bool
    planned_entry: float = float("nan")
    target: float = float("nan")
    stop: float = float("nan")
    rationale: str = ""
    extra: dict = field(default_factory=dict)


def live_z(spread: float, ctx: DayContext) -> float:
    if not ctx.resid_std or ctx.resid_std != ctx.resid_std:  # 0 or NaN
        return float("nan")
    return (spread - ctx.fair_value) / ctx.resid_std


class CalendarMeanReversion:
    """Regime-aware mean-reversion on the fair-value residual z-score.

    Parameterized so the same class drives different structures / risk settings.
    """

    def __init__(self, entry: float = ENTRY, exit_: float = EXIT,
                 stop: float = STOP, z_extreme: float = Z_EXTREME,
                 trade_low_confidence: bool = False,
                 entry_ceiling: float | None = None):
        self.entry = entry
        self.exit = exit_
        self.stop = stop
        self.z_extreme = z_extreme
        self.trade_low_confidence = trade_low_confidence
        # max |z| at which a NEW position may be OPENED. Entries fire only in
        # [entry, entry_ceiling); the band [entry_ceiling, ...) is watch-only.
        # Defaults to z_extreme (the old behavior). The backtest sets this BELOW
        # the stop (e.g. 2.0) so every entry has a guaranteed minimum distance to
        # the stop — both raising win rate and giving fixed-fractional sizing a
        # non-degenerate per-contract risk to divide by (no near-zero stop gaps).
        self.entry_ceiling = entry_ceiling if entry_ceiling is not None else z_extreme

    @staticmethod
    def _signal(action: str, direction: str, spread: float, ctx: DayContext,
                z: float, planned_entry: float = float("nan"),
                target: float = float("nan"), stop: float = float("nan"),
                rationale: str = "") -> Signal:
        return Signal(
            action=action,
            direction=direction,
            z=z,
            spread=spread,
            fair_value=ctx.fair_value,
            resid_std=ctx.resid_std,
            regime=ctx.regime,
            confidence=ctx.confidence,
            ood=ctx.ood,
            planned_entry=planned_entry,
            target=target,
            stop=stop,
            rationale=rationale,
        )

    # ---- decision when FLAT --------------------------------------------------
    def decide_entry(self, spread: float, ctx: DayContext) -> Signal:
        z = live_z(spread, ctx)
        if z != z:  # NaN
            return self._signal(
                action="NO_TRADE", direction="FLAT", spread=spread, ctx=ctx, z=z,
                rationale="no resid_std for regime")

        a = abs(z)
        direction = "SHORT" if z > 0 else "LONG"

        # safeguard: dislocation / out-of-distribution -> watch only, never trade.
        # entry_ceiling bounds how far into the deviation we'll still OPEN a trade.
        entry_ceiling = self.entry_ceiling
        if ctx.ood or a >= entry_ceiling:
            return self._signal(
                action="NO_TRADE", direction=direction, spread=spread, ctx=ctx, z=z,
                rationale=f"DISLOCATION guard (ood={ctx.ood}, |z|={a:.2f}"
                          f">={entry_ceiling}) - watch only")

        # confidence gate
        if ctx.confidence == "LOW" and not self.trade_low_confidence:
            return self._signal(
                action="NO_TRADE", direction=direction, spread=spread, ctx=ctx, z=z,
                rationale="LOW confidence - suppressed")

        if a < self.entry:
            return self._signal(
                action="NO_TRADE", direction="FLAT", spread=spread, ctx=ctx, z=z,
                rationale=f"|z|={a:.2f} < entry {self.entry}")

        # ENTRY
        target = ctx.fair_value
        stop = (ctx.fair_value + self.stop * ctx.resid_std if z > 0
                else ctx.fair_value - self.stop * ctx.resid_std)
        action = "SELL" if z > 0 else "BUY"
        verb = "rich -> SELL spread" if z > 0 else "cheap -> BUY spread"
        return self._signal(
            action=action, direction=direction, spread=spread, ctx=ctx, z=z,
            planned_entry=spread, target=target, stop=stop,
            rationale=f"{ctx.regime}: |z|={a:.2f}>={self.entry} {verb}; "
                      f"target=fair {target:.3f}, stop {stop:.3f} "
                      f"(conf {ctx.confidence})")

    # ---- decision when IN A POSITION ----------------------------------------
    def decide_exit(self, spread: float, ctx: DayContext, pos_dir: str) -> str | None:
        """Return exit reason ('TARGET'|'STOP'|'FLIP') or None to hold."""
        z = live_z(spread, ctx)
        if z != z:
            return None
        a = abs(z)
        cur_dir = "SHORT" if z > 0 else "LONG"
        if a >= self.stop:
            return "STOP"
        if a <= self.exit:
            return "TARGET"
        if cur_dir != pos_dir and a >= self.exit:
            return "FLIP"
        return None


def roll_signal(spread: float, mu: float | None, sd: float | None,
                entry: float = ROLL_ENTRY, exit_: float = ROLL_EXIT,
                stop: float = ROLL_STOP, z_extreme: float = ROLL_Z_EXTREME,
                lookback: int = ROLL_LOOKBACK, regime: str = "ROLL") -> Signal:
    """Pure rolling-mean decision: given the current spread and the rolling
    (mean, std) of the recent window, return a Signal. No mutation/state — the
    live service reuses this to render the current signal without disturbing the
    backtest engine's internal buffer.
    """
    base = dict(spread=spread, regime=regime, confidence="NA", ood=False,
                fair_value=mu if mu is not None else float("nan"),
                resid_std=sd if sd is not None else float("nan"))
    if mu is None or sd is None or not sd or sd != sd:  # warming up / degenerate std
        return Signal(action="NO_TRADE", z=float("nan"), direction="FLAT",
                      rationale="warming up rolling window", **base)
    z = (spread - mu) / sd
    a = abs(z)
    direction = "SHORT" if z > 0 else "LONG"
    if a >= z_extreme:
        return Signal(action="NO_TRADE", z=z, direction=direction,
                      rationale=f"|z|={a:.2f} >= extreme {z_extreme} - watch only", **base)
    if a < entry:
        return Signal(action="NO_TRADE", z=z, direction="FLAT",
                      rationale=f"|z|={a:.2f} < entry {entry}", **base)
    target = mu
    stop_lvl = mu + stop * sd if z > 0 else mu - stop * sd
    action = "SELL" if z > 0 else "BUY"
    verb = "rich -> SELL spread" if z > 0 else "cheap -> BUY spread"
    return Signal(action=action, z=z, direction=direction,
                  planned_entry=spread, target=target, stop=stop_lvl,
                  rationale=f"ROLL{lookback}: |z|={a:.2f}>={entry} {verb}; "
                            f"mean {mu:.3f}, target=mean, stop {stop_lvl:.3f}", **base)


class RollingMeanReversion:
    """Price-only mean reversion baseline (no regime model, no fair-value cache).

    The anchor is the rolling mean of the most recent `lookback` spread bars and
    z = (spread - rollmean) / rollstd. Because the anchor re-centers every bar the
    z is self-normalized, so it oscillates around 0 and crosses the entry band far
    more often than the model's daily-anchored z.

    STATEFUL: it keeps an internal buffer of recent spreads. The engine feeds it
    exactly one bar per step (decide_entry when flat, decide_exit when in a
    position), so each call pushes the current spread before computing stats.

    Same Signal/exit-reason interface as CalendarMeanReversion, so it is a drop-in
    for the backtest Engine. `ctx` is accepted for interface parity but only the
    regime label is borrowed (for the by-regime breakdown); the decision ignores it.
    """

    def __init__(self, lookback: int = ROLL_LOOKBACK, entry: float = ROLL_ENTRY,
                 exit_: float = ROLL_EXIT, stop: float = ROLL_STOP,
                 z_extreme: float = ROLL_Z_EXTREME, min_obs: int | None = None):
        self.lookback = int(lookback)
        self.entry = entry
        self.exit = exit_
        self.stop = stop
        self.z_extreme = z_extreme
        # need enough points for a meaningful std before trading
        self.min_obs = int(min_obs) if min_obs else max(5, self.lookback // 2)
        self._buf: deque[float] = deque(maxlen=self.lookback)

    def stats(self) -> tuple[float | None, float | None]:
        """(mean, std) over the current window, or (None, None) while warming up."""
        n = len(self._buf)
        if n < self.min_obs:
            return None, None
        arr = np.fromiter(self._buf, dtype=float, count=n)
        sd = float(arr.std(ddof=1)) if n > 1 else 0.0
        return float(arr.mean()), sd

    def _z(self, spread: float) -> float:
        mu, sd = self.stats()
        if mu is None or not sd or sd != sd:
            return float("nan")
        return (spread - mu) / sd

    # ---- decision when FLAT --------------------------------------------------
    def decide_entry(self, spread: float, ctx: DayContext | None = None) -> Signal:
        self._buf.append(float(spread))
        mu, sd = self.stats()
        regime = getattr(ctx, "regime", "ROLL") if ctx else "ROLL"
        return roll_signal(float(spread), mu, sd, self.entry, self.exit,
                           self.stop, self.z_extreme, self.lookback, regime)

    # ---- decision when IN A POSITION ----------------------------------------
    def decide_exit(self, spread: float, ctx: DayContext | None, pos_dir: str) -> str | None:
        self._buf.append(float(spread))
        z = self._z(float(spread))
        if z != z:  # NaN
            return None
        a = abs(z)
        cur_dir = "SHORT" if z > 0 else "LONG"
        if a >= self.stop:
            return "STOP"
        if a <= self.exit:
            return "TARGET"
        if cur_dir != pos_dir and a >= self.exit:
            return "FLIP"
        return None
