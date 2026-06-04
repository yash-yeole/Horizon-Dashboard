"""Forward-curve data for the energy complex.

Two sources, same `CurveResponse` shape:
  - CSV settlements (ICE): Brent and Gas Oil — full curve with daily history, so
    we can show now / W-1 / M-1 snapshots.
  - Yahoo contract months: WTI, Heating Oil, RBOB — we assemble the curve from
    the individual monthly futures (e.g. CLN26.NYM, CLQ26.NYM, …) and read each
    contract's recent history for the comparison snapshots.
"""
from __future__ import annotations

import asyncio
import csv
import urllib.parse
from datetime import date, datetime, timedelta

import httpx

from ..cache import TTLCache
from ..config import settings

_DATE_FORMATS = ("%d-%m-%y", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y")
_MONTH_CODES = "FGHJKMNQUVXZ"  # Jan..Dec futures month codes

# id -> metadata. source "csv" reads `csv` path; "yahoo" assembles `root`+`suffix`.
CURVE_META: dict[str, dict] = {
    "brent": {"name": "Brent Crude", "currency": "USD", "unit": "bbl", "source": "csv", "csv": settings.brent_curve_csv},
    "gasoil": {"name": "Gas Oil", "currency": "USD", "unit": "mt", "source": "csv", "csv": settings.gasoil_curve_csv},
    "wti": {"name": "WTI Crude", "currency": "USD", "unit": "bbl", "source": "yahoo", "root": "CL", "suffix": ".NYM"},
    "heatoil": {"name": "Heating Oil", "currency": "USD", "unit": "gal", "source": "yahoo", "root": "HO", "suffix": ".NYM"},
    "rbob": {"name": "RBOB Gasoline", "currency": "USD", "unit": "gal", "source": "yahoo", "root": "RB", "suffix": ".NYM"},
}

_COMPARE_DELTAS: dict[str, timedelta | None] = {
    "now": None,
    "w1": timedelta(days=7),
    "m1": timedelta(days=30),
}

_yahoo_cache = TTLCache(ttl=settings.curve_cache_ttl)


class CurveUnavailable(Exception):
    pass


def _parse_date(raw: str) -> date | None:
    raw = raw.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _pick_compare(pairs: list[tuple[date, float]], latest_date: date, compare: str) -> tuple[date, float]:
    """Choose the comparison (date, value) for a single contract's history."""
    delta = _COMPARE_DELTAS[compare]
    if delta is None:
        return pairs[-2] if len(pairs) > 1 else pairs[-1]
    target = latest_date - delta
    prior = [p for p in pairs if p[0] <= target]
    return prior[-1] if prior else pairs[0]


# ---------------- CSV source ----------------

_csv_cache: dict[str, tuple[float, list[tuple[date, list[float]]]]] = {}


def _load_csv(path_str: str) -> list[tuple[date, list[float]]]:
    from pathlib import Path
    path = Path(path_str)
    if not path.is_file():
        raise CurveUnavailable(f"curve file not found: {path.name}")

    mtime = path.stat().st_mtime
    cached = _csv_cache.get(path_str)
    if cached is not None and cached[0] == mtime:
        return cached[1]

    with path.open(newline="", encoding="utf-8-sig") as fh:
        all_rows = list(csv.reader(fh))

    rows: list[tuple[date, list[float]]] = []
    for raw in all_rows[2:]:  # row 0 = codes, row 1 = Timestamp/SETTLE labels
        if not raw or not raw[0].strip():
            continue
        d = _parse_date(raw[0])
        if d is None:
            continue
        settles: list[float] = []
        for i in range(1, len(raw), 2):
            try:
                settles.append(float(raw[i].strip()))
            except (ValueError, IndexError):
                break
        if settles:
            rows.append((d, settles))

    if not rows:
        raise CurveUnavailable("curve file contained no usable rows")
    rows.sort(key=lambda r: r[0])
    _csv_cache[path_str] = (mtime, rows)
    return rows


def _csv_curve(curve_id: str, meta: dict, compare: str) -> dict:
    rows = _load_csv(meta["csv"])
    latest_date, latest = rows[-1]
    delta = _COMPARE_DELTAS[compare]
    if delta is None:
        compare_date, compare_settles = rows[-2] if len(rows) > 1 else rows[-1]
    else:
        target = latest_date - delta
        prior = [r for r in rows if r[0] <= target]
        compare_date, compare_settles = prior[-1] if prior else rows[0]

    n = min(len(latest), len(compare_settles))
    points = [
        {"month": f"M{i + 1}", "price": latest[i], "previous_price": compare_settles[i]}
        for i in range(n)
    ]
    return _response(curve_id, meta, latest_date.isoformat(), compare, compare_date.isoformat(), points)


# ---------------- Yahoo source ----------------

def _contract_symbols(root: str, suffix: str, n: int = 15) -> list[str]:
    today = date.today()
    y, m = today.year, today.month
    out: list[str] = []
    for _ in range(n):
        m += 1
        if m > 12:
            m = 1
            y += 1
        out.append(f"{root}{_MONTH_CODES[m - 1]}{str(y)[2:]}{suffix}")
    return out


async def _yahoo_curve(curve_id: str, meta: dict, compare: str) -> dict:
    cache_key = f"{curve_id}:{compare}"
    cached = _yahoo_cache.get(cache_key)
    if cached is not None:
        return cached

    symbols = _contract_symbols(meta["root"], meta["suffix"])
    async with httpx.AsyncClient(
        base_url=settings.yahoo_base_url,
        headers={"User-Agent": settings.yahoo_user_agent},
        timeout=settings.request_timeout,
    ) as client:
        async def one(sym: str) -> list[tuple[date, float]]:
            try:
                resp = await client.get(
                    f"/v8/finance/chart/{urllib.parse.quote(sym)}",
                    params={"range": "3mo", "interval": "1d"},
                )
                result = resp.json()["chart"]["result"][0]
                ts = result.get("timestamp") or []
                closes = result["indicators"]["quote"][0]["close"]
                return [(date.fromtimestamp(t), float(c)) for t, c in zip(ts, closes) if c is not None]
            except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
                return []

        histories = await asyncio.gather(*(one(s) for s in symbols))

    curve = [h for h in histories if h]  # contracts with usable data, in month order
    if not curve:
        raise CurveUnavailable(f"no Yahoo curve data for {curve_id}")

    latest_date = max(h[-1][0] for h in curve)
    points = []
    compare_date = latest_date
    for i, pairs in enumerate(curve):
        cur = pairs[-1][1]
        cmp_date, prev = _pick_compare(pairs, latest_date, compare)
        if i == 0:
            compare_date = cmp_date
        points.append({"month": f"M{i + 1}", "price": round(cur, 4), "previous_price": round(prev, 4)})

    payload = _response(curve_id, meta, latest_date.isoformat(), compare, compare_date.isoformat(), points)
    _yahoo_cache.set(cache_key, payload)
    return payload


def _response(curve_id, meta, as_of, compare, compare_date, points) -> dict:
    return {
        "id": curve_id,
        "name": meta["name"],
        "currency": meta["currency"],
        "unit": meta["unit"],
        "as_of": as_of,
        "compare": compare,
        "compare_date": compare_date,
        "points": points,
    }


# ---------------- dispatch ----------------

async def get_curve(curve_id: str, compare: str = "now") -> dict:
    meta = CURVE_META.get(curve_id)
    if meta is None:
        raise KeyError(curve_id)
    if compare not in _COMPARE_DELTAS:
        raise ValueError(compare)

    if meta["source"] == "csv":
        return _csv_curve(curve_id, meta, compare)
    return await _yahoo_curve(curve_id, meta, compare)
