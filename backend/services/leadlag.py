"""Lead-lag (cross-correlation) analysis for the energy complex.

For a base instrument we measure, against each other instrument, the return
cross-correlation at a range of time shifts. The shift with the strongest
correlation reveals who moves first: if corr(base[t], other[t+k]) peaks at k>0,
the base *leads* the other by k bars (k * bar_minutes).

Needs intraday data for fast pairs (Brent↔WTI lead-lag is minutes), so we offer
intraday / hourly / daily timeframes.
"""
from __future__ import annotations

import asyncio
import math
import time

from cache import TTLCache
from config import settings
from models import LeadLagPair, LeadLagPoint, LeadLagResponse
from symbols import BY_ID
from services import yahoo

# timeframe -> Yahoo range/interval + how far to scan + minutes per bar
TIMEFRAMES: dict[str, dict] = {
    "fine": {"range": "1d", "interval": "1m", "maxlag": 15, "bar_minutes": 1},
    "intraday": {"range": "5d", "interval": "15m", "maxlag": 16, "bar_minutes": 15},
    "hourly": {"range": "1mo", "interval": "1h", "maxlag": 12, "bar_minutes": 60},
    "daily": {"range": "6mo", "interval": "1d", "maxlag": 10, "bar_minutes": 1440},
}

# Energy instruments with intraday Yahoo coverage (Gas Oil isn't on Yahoo).
DEFAULT_SET = ["brent", "wti", "rbob", "heatoil"]

_series_cache = TTLCache(ttl=settings.curve_cache_ttl)  # reuse a ~5 min TTL


class LeadLagError(RuntimeError):
    pass


def _pearson(a: list[float], b: list[float]) -> float:
    n = min(len(a), len(b))
    if n < 5:
        return 0.0
    a, b = a[:n], b[:n]
    ma, mb = sum(a) / n, sum(b) / n
    num = da = db = 0.0
    for i in range(n):
        x, y = a[i] - ma, b[i] - mb
        num += x * y
        da += x * x
        db += y * y
    den = math.sqrt(da * db)
    return num / den if den else 0.0


def _ccf(base: list[float], other: list[float], maxlag: int) -> list[tuple[int, float]]:
    """corr(base[t], other[t+k]) for k in [-maxlag, maxlag]."""
    n = len(base)
    out: list[tuple[int, float]] = []
    for k in range(-maxlag, maxlag + 1):
        if k >= 0:
            x, y = base[: n - k], other[k:]
        else:
            x, y = base[-k:], other[: n + k]
        out.append((k, round(_pearson(x, y), 4)))
    return out


async def _fetch_series(tf: str) -> dict[str, dict[int, float]]:
    """id -> {timestamp: close} for the default set (cached per timeframe)."""
    cached = _series_cache.get(f"ll:{tf}")
    if cached is not None:
        return cached

    spec = TIMEFRAMES[tf]

    async def one(cid: str) -> tuple[str, dict[int, float]]:
        sym = BY_ID.get(cid)
        if sym is None:
            return cid, {}
        try:
            pts = await yahoo.fetch_history(sym, spec["range"], spec["interval"])
            return cid, {p.time: p.value for p in pts}
        except Exception:  # noqa: BLE001
            return cid, {}

    pairs = await asyncio.gather(*(one(c) for c in DEFAULT_SET))
    series = {cid: data for cid, data in pairs if data}
    _series_cache.set(f"ll:{tf}", series)
    return series


def _aligned_returns(series: dict[str, dict[int, float]], ids: list[str]) -> tuple[list[int], dict[str, list[float]]]:
    have = [i for i in ids if series.get(i)]
    if len(have) < 2:
        return [], {}
    common = set.intersection(*(set(series[i].keys()) for i in have))
    times = sorted(common)
    rets: dict[str, list[float]] = {}
    for i in have:
        vals = [series[i][t] for t in times]
        rets[i] = [(vals[k] / vals[k - 1] - 1) if vals[k - 1] else 0.0 for k in range(1, len(vals))]
    return times, rets


async def compute(base: str, tf: str) -> LeadLagResponse:
    if tf not in TIMEFRAMES:
        raise LeadLagError(f"unknown timeframe '{tf}'")
    if base not in DEFAULT_SET:
        raise LeadLagError(f"unsupported base '{base}'")

    spec = TIMEFRAMES[tf]
    series = await _fetch_series(tf)
    times, rets = _aligned_returns(series, DEFAULT_SET)
    if base not in rets or len(times) < 10:
        raise LeadLagError("insufficient aligned data")

    pairs: list[LeadLagPair] = []
    for other in DEFAULT_SET:
        if other == base or other not in rets:
            continue
        ccf = _ccf(rets[base], rets[other], spec["maxlag"])
        best_lag, best_corr = max(ccf, key=lambda kv: abs(kv[1]))
        same = next((c for k, c in ccf if k == 0), 0.0)
        leader = "base" if best_lag > 0 else "other" if best_lag < 0 else "sync"
        pairs.append(LeadLagPair(
            id=other,
            name=BY_ID[other].name,
            best_lag=best_lag,
            best_lag_minutes=best_lag * spec["bar_minutes"],
            best_corr=best_corr,
            same_corr=same,
            leader=leader,
            ccf=[LeadLagPoint(lag=k, corr=c) for k, c in ccf],
        ))

    return LeadLagResponse(
        base=base,
        base_name=BY_ID[base].name,
        timeframe=tf,
        interval=spec["interval"],
        bar_minutes=spec["bar_minutes"],
        samples=len(times) - 1,
        as_of=time.time(),
        pairs=pairs,
    )
