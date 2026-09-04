"""
paper.py — paper-trading / strategy-engine service (Phase 7 hybrid wiring).

The heavy daily fair value is computed offline (refresh_fairvalue.py) and cached
to parquet; this service reads that cache and combines it with the *live* 15-min
bar DB to produce, per structure:

  * the current snapshot (regime, fair value, live spread, live z, signal)
  * the intraday z-series for charting
  * the trade blotter, equity curve and performance stats

Only the light engine modules are imported (data_feed / strategy / backtest /
metrics) — the model/sklearn pipeline is never loaded in the API process.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

from cache import TTLCache
from config import settings

# make the vendored strategy engine importable
_STRAT_DIR = settings.paper_strategy_dir
if _STRAT_DIR not in sys.path:
    sys.path.insert(0, _STRAT_DIR)

import data_feed as feed            # noqa: E402
from strategy import (CalendarMeanReversion, RollingMeanReversion,  # noqa: E402
                      live_z, roll_signal)
from backtest import Engine, EngineConfig            # noqa: E402
import metrics                       # noqa: E402

_CACHE_DIR = os.path.join(_STRAT_DIR, "cache")
_cache = TTLCache(ttl=settings.paper_cache_ttl)

# the structures the live DB supports.
# watch_only: butterflies are flagged unreliable by the walk-forward model eval
# (WTI fly R2<0, Brent fly STOP-churn) -> signals are shown but NOT actioned.
#
# model_native: the regime/fair-value model was TRAINED on this structure (the
# c1-c2 calendar and the butterfly). For the added c2-c3 calendars and the
# WTI-Brent cross there is NO dedicated fair-value model, so:
#   * the LIVE engine is "rolling" (price-only, self-normalizing) — it needs no
#     model at all, only a day_map to keep the engine loop alive + a regime label.
#     These structures reuse the same-product c1-c2 cal day_map PURELY as a regime
#     overlay (target="cal"); the rolling decision/z ignore the model entirely.
#   * the model-specific fair-value display fields (fair_value, fv_drift, resid σ)
#     are nulled for non-native structures (a c1-c2 fair value is meaningless on a
#     c2-c3 or cross spread) — the rolling anchor is shown instead.
# leg2_product: for the cross spread, the second leg comes from a DIFFERENT product
# (front-month WTI minus front-month Brent).
STRUCTURES: dict[str, dict] = {
    "wti_cal":    dict(product="CL", target="cal", instrument="WTI",       structure="c1-c2",     label="WTI c1-c2",   model_native=True),
    "wti_c2c3":   dict(product="CL", target="cal", instrument="WTI",       structure="c2-c3",     label="WTI c2-c3"),
    "wti_fly":    dict(product="CL", target="fly", instrument="WTI",       structure="butterfly", label="WTI butterfly", watch_only=True, model_native=True),
    "brent_cal":  dict(product="CO", target="cal", instrument="Brent",     structure="c1-c2",     label="Brent c1-c2", model_native=True),
    "brent_c2c3": dict(product="CO", target="cal", instrument="Brent",     structure="c2-c3",     label="Brent c2-c3"),
    "brent_fly":  dict(product="CO", target="fly", instrument="Brent",     structure="butterfly", label="Brent butterfly", watch_only=True, model_native=True),
    "wti_brent":  dict(product="CL", target="cal", instrument="WTI-Brent", structure="wti-brent", label="WTI-Brent", leg2_product="CO"),
}

_ENGINE = settings.paper_engine.lower()


def _make_strategy():
    """Fresh strategy per compute (rolling is stateful — needs a clean buffer)."""
    if _ENGINE == "rolling":
        return RollingMeanReversion(lookback=settings.paper_roll_lookback,
                                    entry=settings.paper_roll_entry,
                                    exit_=settings.paper_roll_exit,
                                    stop=settings.paper_roll_stop,
                                    z_extreme=settings.paper_roll_z_extreme)
    return CalendarMeanReversion(entry=settings.paper_entry,
                                 exit_=settings.paper_exit,
                                 stop=settings.paper_stop,
                                 z_extreme=settings.paper_z_extreme)


def _thresholds() -> dict:
    if _ENGINE == "rolling":
        return {"entry": settings.paper_roll_entry, "exit": settings.paper_roll_exit,
                "stop": settings.paper_roll_stop, "z_extreme": settings.paper_roll_z_extreme}
    return {"entry": settings.paper_entry, "exit": settings.paper_exit,
            "stop": settings.paper_stop, "z_extreme": settings.paper_z_extreme}


_THRESHOLDS = _thresholds()


# --------------------------------------------------------------------- helpers
def _iso(ts) -> str:
    return pd.Timestamp(ts).isoformat()


def _f(x):
    """JSON-safe float (NaN/inf -> None)."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if np.isfinite(v) else None


def _load_day_map(product: str, target: str) -> pd.DataFrame | None:
    p = os.path.join(_CACHE_DIR, f"fv_{product}_{target}.parquet")
    if not os.path.exists(p):
        return None
    return pd.read_parquet(p)


def _build_cross(cfg: dict, field: str = "close"):
    """Intraday cross-product spread = front(product) - front(leg2_product).

    e.g. WTI-Brent = front-month CL close - front-month CO close. The two products
    roll on different calendars, so the legs are each product's own nearest unexpired
    tenor (they may be different delivery months — that IS the live arb).
    """
    p1, p2 = cfg["product"], cfg["leg2_product"]
    parts, legs_used = [], None
    for db in feed.list_db_files():
        as_of = feed._date_from_path(db)
        t1 = feed.front_tenors(db, p1, n=1, as_of=as_of)
        t2 = feed.front_tenors(db, p2, n=1, as_of=as_of)
        if not t1 or not t2:
            continue
        try:
            a = feed.read_contract(db, f"{p1}_{t1[0]}")[field]
            b = feed.read_contract(db, f"{p2}_{t2[0]}")[field]
        except Exception:  # noqa: BLE001
            continue
        m = pd.DataFrame({"a": a, "b": b}).dropna()
        if m.empty:
            continue
        legs_used = [f"{p1} {t1[0]}", f"{p2} {t2[0]}"]
        parts.append(pd.DataFrame({"c1": m["a"], "c2": m["b"], "spread": m["a"] - m["b"]}))
    if not parts:
        return pd.DataFrame(), legs_used
    full = pd.concat(parts)
    full = full[~full.index.duplicated(keep="last")].sort_index()
    return full, legs_used


def _build_intraday(cfg: dict, field: str = "close"):
    """Intraday spread series from the live DB. Mirrors notebook 23.

    c1-c2 = front - second (2 legs); c2-c3 = second - third (legs 2 & 3 of 3);
    butterfly = c1 - 2*c2 + c3 (3 legs); wti-brent = cross-product (see _build_cross).
    """
    product, structure = cfg["product"], cfg["structure"]
    if structure == "wti-brent":
        return _build_cross(cfg, field)
    need = 3 if structure in ("butterfly", "c2-c3") else 2
    parts, legs_used = [], None
    for db in feed.list_db_files():
        as_of = feed._date_from_path(db)
        tenors = feed.front_tenors(db, product, n=need, as_of=as_of)
        if len(tenors) < need:
            continue
        closes = {}
        for t in tenors:
            try:
                closes[t] = feed.read_contract(db, f"{product}_{t}")[field]
            except Exception:  # noqa: BLE001
                pass
        if len(closes) < need:
            continue
        m = pd.DataFrame(closes).dropna()
        if structure == "butterfly":
            spread = m[tenors[0]] - 2 * m[tenors[1]] + m[tenors[2]]
            leg_a, leg_b, legs_used = tenors[0], tenors[1], tenors
        elif structure == "c2-c3":
            spread = m[tenors[1]] - m[tenors[2]]
            leg_a, leg_b, legs_used = tenors[1], tenors[2], [tenors[1], tenors[2]]
        else:  # c1-c2
            spread = m[tenors[0]] - m[tenors[1]]
            leg_a, leg_b, legs_used = tenors[0], tenors[1], [tenors[0], tenors[1]]
        parts.append(pd.DataFrame({"c1": m[leg_a], "c2": m[leg_b], "spread": spread}))
    if not parts:
        return pd.DataFrame(), legs_used
    full = pd.concat(parts)
    full = full[~full.index.duplicated(keep="last")].sort_index()
    return full, legs_used


def _trades_records(tr: pd.DataFrame) -> list[dict]:
    if tr.empty:
        return []
    out = []
    for _, r in tr.iterrows():
        out.append({
            "direction": r["direction"],
            "regime": r.get("regime"),
            "confidence": r.get("confidence"),
            "entry_ts": _iso(r["entry_ts"]),
            "entry_price": _f(r["entry_price"]),
            "exit_ts": _iso(r["exit_ts"]),
            "exit_price": _f(r["exit_price"]),
            "exit_reason": r["exit_reason"],
            "target": _f(r.get("target")),
            "stop": _f(r.get("stop")),
            "net_pnl": _f(r["net_pnl"]),
            "win": bool(r["win"]),
            "hold_bars": int(r["hold_bars"]) if pd.notna(r.get("hold_bars")) else None,
        })
    return out


def _rich_cheap(z: float | None, exit_thr: float) -> str:
    if z is None:
        return "UNKNOWN"
    if abs(z) < exit_thr:
        return "FAIR"
    return "RICH" if z > 0 else "CHEAP"


# --------------------------------------------------------------------- compute
def compute_structure(key: str) -> dict:
    cfg = STRUCTURES[key]
    day_map = _load_day_map(cfg["product"], cfg["target"])
    if day_map is None or day_map.empty:
        return {"key": key, "label": cfg["label"],
                "error": "no fair-value cache — refresh it with the offline maintenance tooling"}

    df, legs = _build_intraday(cfg)
    if df.empty:
        return {"key": key, "label": cfg["label"], "legs": None,
                "error": "no intraday bars in the DB for this structure"}

    eng = Engine(EngineConfig(product=cfg["product"], target=cfg["target"],
                              instrument=cfg["instrument"], structure=cfg["structure"]),
                 strategy=_make_strategy(), day_map=day_map)

    # rolling engine: z is the deviation from the rolling mean of recent spreads
    # (not the daily model anchor). Precompute window stats aligned to df for the
    # chart/snapshot; the engine itself recomputes the same z internally per bar.
    roll_mean = roll_std = None
    if _ENGINE == "rolling":
        lb = settings.paper_roll_lookback
        mo = max(5, lb // 2)
        roll_mean = df["spread"].rolling(lb, min_periods=mo).mean()
        roll_std = df["spread"].rolling(lb, min_periods=mo).std(ddof=1)

    z_series = []
    for i, (ts, r) in enumerate(df.iterrows()):
        if _ENGINE == "rolling":
            mu, sd = roll_mean.iloc[i], roll_std.iloc[i]
            z = (float(r.spread) - mu) / sd if (sd and sd == sd) else float("nan")
        else:
            ctx = eng._ctx(ts)
            z = live_z(float(r.spread), ctx) if ctx else float("nan")
        z_series.append({"t": _iso(ts), "z": _f(z), "spread": _f(r.spread)})
        bar = feed.Bar(ts=ts, instrument=cfg["instrument"], structure=cfg["structure"],
                       spread=float(r.spread), c1=float(r.c1), c2=float(r.c2),
                       leg1=legs[0] if legs else "", leg2=legs[1] if legs else "")
        eng.step(bar)

    res = eng.results()
    tr = res["trades"]

    last_ts = df.index[-1]
    last_ctx = eng._ctx(last_ts)
    last_spread = float(df["spread"].iloc[-1])
    roll_anchor = roll_std_last = None
    if _ENGINE == "rolling":
        _m, _s = roll_mean.iloc[-1], roll_std.iloc[-1]
        roll_anchor = None if pd.isna(_m) else float(_m)
        roll_std_last = None if pd.isna(_s) else float(_s)
        last_z = ((last_spread - roll_anchor) / roll_std_last
                  if (roll_anchor is not None and roll_std_last) else None)
    else:
        last_z = live_z(last_spread, last_ctx) if last_ctx else None
    # regime drift de-bias applied to the latest day (for fair-value attribution)
    _last_fv_drift = None
    if "fv_drift" in day_map.columns and not day_map.empty:
        try:
            _last_fv_drift = float(day_map["fv_drift"].iloc[-1])
        except (TypeError, ValueError):
            _last_fv_drift = None

    # current decision (entry if flat, else the live exit check)
    watch_only = bool(cfg.get("watch_only"))
    if _ENGINE == "rolling":
        sig = roll_signal(last_spread, roll_anchor, roll_std_last,
                          settings.paper_roll_entry, settings.paper_roll_exit,
                          settings.paper_roll_stop, settings.paper_roll_z_extreme,
                          settings.paper_roll_lookback,
                          regime=(last_ctx.regime if last_ctx else "ROLL"))
    else:
        sig = _make_strategy().decide_entry(last_spread, last_ctx) if last_ctx else None
    signal = None
    if sig is not None:
        action = sig.action
        rationale = sig.rationale
        if watch_only and action in ("BUY", "SELL"):
            action = "NO_TRADE"
            rationale = ("WATCH-ONLY (butterfly flagged unreliable by model eval); "
                         f"would-be signal: {sig.action} — {sig.rationale}")
        signal = {
            "action": action, "direction": sig.direction,
            "planned_entry": _f(sig.planned_entry), "target": _f(sig.target),
            "stop": _f(sig.stop), "rationale": rationale,
        }

    # open position (mark-to-market at last bar)
    open_pos = res["open_position"]
    open_position = None
    if open_pos is not None:
        sgn = 1 if open_pos.direction == "LONG" else -1
        unreal = sgn * (last_spread - open_pos.entry_price) * open_pos.size
        open_position = {
            "direction": open_pos.direction, "size": open_pos.size,
            "entry_ts": _iso(open_pos.entry_ts), "entry_price": _f(open_pos.entry_price),
            "target": _f(open_pos.target), "stop": _f(open_pos.stop),
            "current_price": _f(last_spread), "current_z": _f(last_z),
            "unrealized_pnl": _f(unreal), "regime": open_pos.regime,
            "confidence": open_pos.confidence, "rationale": open_pos.entry_rationale,
        }

    # equity curve
    eq = metrics.equity_curve(tr, 0.0)
    equity_curve = [{"t": _iso(t), "equity": _f(v)} for t, v in eq.items()] if not eq.empty else []

    # by-regime
    br = res["by_regime"]
    by_regime = []
    if not br.empty:
        for reg, row in br.iterrows():
            by_regime.append({"regime": reg, "n": int(row["n"]),
                              "win_rate": _f(row["win_rate"]),
                              "net_pnl": _f(row["net_pnl"]),
                              "avg_pnl": _f(row["avg_pnl"])})

    # the regime/fair-value model was trained on this structure's spread? If not
    # (c2-c3, cross), the reused cal day_map gives a valid regime OVERLAY but its
    # fair_value/resid_std are on the WRONG spread — null them so the UI shows only
    # the rolling anchor (the actual live decision basis), not a misleading anchor.
    model_native = bool(cfg.get("model_native"))

    # stats — jsonify the summary dict
    stats = {}
    for k, v in res["summary"].items():
        if isinstance(v, dict):
            stats[k] = v
        elif isinstance(v, (int,)):
            stats[k] = v
        elif isinstance(v, float) or isinstance(v, np.floating):
            stats[k] = _f(v)
        else:
            stats[k] = str(v)

    return {
        "key": key,
        "label": cfg["label"],
        "instrument": cfg["instrument"],
        "structure": cfg["structure"],
        "legs": "-".join(legs) if legs else None,
        "bars": int(len(df)),
        "as_of": _iso(last_ts),
        "regime": last_ctx.regime if last_ctx else None,
        "confidence": last_ctx.confidence if last_ctx else None,
        "ood": bool(last_ctx.ood) if last_ctx else None,
        "near_boundary": bool(last_ctx.near_boundary) if last_ctx else None,
        "watch_only": watch_only,
        "fair_value": _f(last_ctx.fair_value) if (last_ctx and model_native) else None,
        # interpretability: fair_value = fundamental anchor + regime drift de-bias
        "fv_drift": _f(_last_fv_drift) if model_native else None,
        "fair_value_fundamental": (_f(last_ctx.fair_value - _last_fv_drift)
                                   if last_ctx and model_native and _last_fv_drift is not None else None),
        "resid_std": _f(last_ctx.resid_std) if (last_ctx and model_native) else None,
        "live_spread": _f(last_spread),
        "live_z": _f(last_z),
        "rich_cheap": _rich_cheap(last_z, _thresholds()["exit"]),
        "thresholds": _thresholds(),
        "engine": _ENGINE,
        "roll_lookback": settings.paper_roll_lookback if _ENGINE == "rolling" else None,
        "roll_anchor": _f(roll_anchor) if _ENGINE == "rolling" else None,
        "roll_std": _f(roll_std_last) if _ENGINE == "rolling" else None,
        "signal": signal,
        "open_position": open_position,
        "z_series": z_series,
        "trades": _trades_records(tr),
        "equity_curve": equity_curve,
        "by_regime": by_regime,
        "stats": stats,
    }


def get_structure(key: str, refresh: bool = False) -> dict:
    if key not in STRUCTURES:
        raise KeyError(key)
    ck = f"paper:{key}"
    if not refresh:
        cached = _cache.get(ck)
        if cached is not None:
            return cached
    payload = compute_structure(key)
    _cache.set(ck, payload)
    return payload


def list_structures() -> list[dict]:
    return [{"key": k, "label": v["label"], "instrument": v["instrument"],
             "structure": v["structure"], "watch_only": bool(v.get("watch_only"))}
            for k, v in STRUCTURES.items()]


def get_all(refresh: bool = False) -> dict:
    return {k: get_structure(k, refresh) for k in STRUCTURES}
