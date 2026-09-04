"""EIA Open Data client (https://www.eia.gov/opendata/).

Pulls the Weekly Petroleum Status Report series the dashboard needs and
normalises them into our camelCase models. Stocks are reported by EIA in
thousand barrels; we convert to million barrels (M bbl) to match the UI.

Requires a free API key (HORIZON_EIA_API_KEY). Without it, callers get an
EiaError and the route falls back to cached/static data.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import httpx

from config import settings
from models import EiaInventoryResponse, EiaPoint, EiaSeries

MBBL = 1 / 1000  # thousand barrels -> million barrels

# frontend key -> (EIA series id, label, unit, scale factor)
SERIES: dict[str, tuple[str, str, str, float]] = {
    # --- stocks (M bbl) ---
    "crude": ("PET.WCESTUS1.W", "Crude Oil (excl. SPR)", "M bbl", MBBL),
    "cushing": ("PET.W_EPC0_SAX_YCUOK_MBBL.W", "Cushing, OK", "M bbl", MBBL),
    "gasoline": ("PET.WGTSTUS1.W", "Gasoline", "M bbl", MBBL),
    "distillate": ("PET.WDISTUS1.W", "Distillate", "M bbl", MBBL),
    "propane": ("PET.WPRSTUS1.W", "Propane", "M bbl", MBBL),
    "spr": ("PET.WCSSTUS1.W", "SPR", "M bbl", MBBL),
    # --- supply-side (% / M bbl/d) ---
    "refineryUtil": ("PET.WPULEUS3.W", "Refinery Utilization", "%", 1.0),
    "production": ("PET.WCRFPUS2.W", "Crude Production", "M bbl/d", MBBL),
    # --- trade (M bbl/d) ---
    "crudeImports": ("PET.WCRIMUS2.W", "Crude Imports", "M bbl/d", MBBL),
    "crudeExports": ("PET.WCREXUS2.W", "Crude Exports", "M bbl/d", MBBL),
    # --- demand / product supplied (M bbl/d), used for days-of-supply ---
    "gasolineDemand": ("PET.WGFUPUS2.W", "Gasoline Demand", "M bbl/d", MBBL),
    "distillateDemand": ("PET.WDIUPUS2.W", "Distillate Demand", "M bbl/d", MBBL),
    # --- drilling: Baker Hughes rotary rig count, republished by EIA (MONTHLY) ---
    "rigCount": ("PET.E_ERTRR0_XR0_NUS_C.M", "Rotary Rig Count", "rigs", 1.0),
}


class EiaError(RuntimeError):
    pass


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=settings.eia_base_url, timeout=settings.request_timeout)


async def _fetch_series(client: httpx.AsyncClient, series_id: str, weeks: int) -> list[tuple[str, float | None]]:
    """Return [(period, value)] sorted ascending by period, newest `weeks` kept."""
    resp = await client.get(
        f"/seriesid/{series_id}",
        params={"api_key": settings.eia_api_key, "length": weeks},
    )
    resp.raise_for_status()
    rows = resp.json().get("response", {}).get("data", [])
    out: list[tuple[str, float | None]] = []
    for r in rows:
        period = r.get("period")
        if not period:
            continue
        raw = r.get("value")
        try:
            value = float(raw) if raw is not None else None
        except (TypeError, ValueError):
            value = None
        out.append((period, value))
    out.sort(key=lambda x: x[0])
    return out[-weeks:]


# We always pull a wide window once and slice it per-request, so a single
# fetch/refresh serves every chart range without extra API calls.
FETCH_WEEKS = 104


async def fetch_inventories(weeks: int = FETCH_WEEKS) -> EiaInventoryResponse:
    if not settings.eia_api_key:
        raise EiaError("EIA API key not configured")

    async with _client() as client:
        async def one(key: str, meta: tuple[str, str, str, float]) -> EiaSeries:
            series_id, label, unit, scale = meta
            raw = await _fetch_series(client, series_id, weeks)
            points = [
                EiaPoint(period=p, value=round(v * scale, 2) if v is not None else None)
                for p, v in raw
            ]
            vals = [pt.value for pt in points if pt.value is not None]
            latest = vals[-1] if vals else None
            previous = vals[-2] if len(vals) >= 2 else None
            change = round(latest - previous, 2) if latest is not None and previous is not None else None
            return EiaSeries(id=key, label=label, unit=unit, latest=latest, previous=previous, change=change, points=points)

        series = await asyncio.gather(*(one(k, m) for k, m in SERIES.items()))

    by_id = {s.id: s for s in series}
    # Derived series computed from the fetched ones (no extra API calls).
    derived = [
        _combine(by_id.get("crudeImports"), by_id.get("crudeExports"),
                 lambda a, b: a - b, "netImports", "Net Crude Imports", "M bbl/d"),
        _combine(by_id.get("gasoline"), by_id.get("gasolineDemand"),
                 lambda a, b: a / b, "gasolineDaysSupply", "Gasoline Days of Supply", "days"),
        _combine(by_id.get("distillate"), by_id.get("distillateDemand"),
                 lambda a, b: a / b, "distillateDaysSupply", "Distillate Days of Supply", "days"),
    ]
    all_series = list(series) + [d for d in derived if d is not None]

    # Use a weekly series for as_of (rig count is monthly and lags).
    weekly = [s for s in all_series if s.id != "rigCount" and s.points]
    as_of = max((s.points[-1].period for s in weekly), default="")
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return EiaInventoryResponse(as_of=as_of, fetched_at=fetched_at, stale=False, series=all_series)


def _combine(a, b, op, sid: str, label: str, unit: str):
    """Combine two series period-by-period (a op b) into a new derived series."""
    if a is None or b is None:
        return None
    bmap = {p.period: p.value for p in b.points}
    points = []
    for p in a.points:
        bv = bmap.get(p.period)
        v = op(p.value, bv) if (p.value is not None and bv not in (None, 0)) else None
        points.append(EiaPoint(period=p.period, value=round(v, 2) if v is not None else None))
    vals = [pt.value for pt in points if pt.value is not None]
    latest = vals[-1] if vals else None
    previous = vals[-2] if len(vals) >= 2 else None
    change = round(latest - previous, 2) if latest is not None and previous is not None else None
    return EiaSeries(id=sid, label=label, unit=unit, latest=latest, previous=previous, change=change, points=points)
