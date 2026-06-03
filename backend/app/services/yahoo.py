"""Yahoo Finance client.

Uses the public v8 chart endpoint which returns both a quote snapshot (in `meta`)
and an intraday series we use for sparklines — without requiring auth/crumbs.
"""
from __future__ import annotations

import asyncio
import urllib.parse

import httpx

from ..config import settings
from ..models import HistoryPoint, Quote
from ..symbols import SymbolDef


class YahooError(RuntimeError):
    pass


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=settings.yahoo_base_url,
        headers={"User-Agent": settings.yahoo_user_agent},
        timeout=settings.request_timeout,
    )


async def _fetch_chart(client: httpx.AsyncClient, yahoo_symbol: str, rng: str, interval: str) -> dict:
    path = f"/v8/finance/chart/{urllib.parse.quote(yahoo_symbol)}"
    resp = await client.get(path, params={"range": rng, "interval": interval})
    resp.raise_for_status()
    data = resp.json()
    chart = data.get("chart", {})
    if chart.get("error"):
        raise YahooError(str(chart["error"]))
    results = chart.get("result")
    if not results:
        raise YahooError(f"empty result for {yahoo_symbol}")
    return results[0]


def _extract_sparkline(result: dict, limit: int = 40) -> list[float]:
    try:
        closes = result["indicators"]["quote"][0]["close"]
    except (KeyError, IndexError, TypeError):
        return []
    series = [round(float(c), 4) for c in closes if c is not None]
    return series[-limit:]


def _to_quote(sym: SymbolDef, result: dict) -> Quote:
    meta = result.get("meta", {})
    price = float(meta.get("regularMarketPrice") or 0.0)
    prev = meta.get("chartPreviousClose") or meta.get("previousClose")
    prev_close = float(prev) if prev is not None else None
    change = round(price - prev_close, 4) if prev_close else 0.0
    change_pct = round((change / prev_close) * 100, 4) if prev_close else 0.0
    return Quote(
        id=sym.id,
        yahoo_symbol=sym.yahoo,
        name=sym.name,
        price=round(price, 4),
        change=change,
        change_pct=change_pct,
        high=meta.get("regularMarketDayHigh"),
        low=meta.get("regularMarketDayLow"),
        prev_close=prev_close,
        volume=meta.get("regularMarketVolume"),
        currency=meta.get("currency") or sym.currency,
        unit=sym.unit,
        category=sym.category,
        sparkline=_extract_sparkline(result),
        market_time=meta.get("regularMarketTime"),
    )


async def fetch_quotes(symbols: list[SymbolDef]) -> list[Quote]:
    """Fetch quotes for many symbols concurrently. Missing/failed symbols are skipped."""
    async with _client() as client:
        async def one(sym: SymbolDef) -> Quote | None:
            try:
                result = await _fetch_chart(client, sym.yahoo, rng="1d", interval="15m")
                return _to_quote(sym, result)
            except (httpx.HTTPError, YahooError, ValueError):
                return None

        results = await asyncio.gather(*(one(s) for s in symbols))
    return [q for q in results if q is not None]


async def fetch_history(sym: SymbolDef, rng: str, interval: str) -> list[HistoryPoint]:
    async with _client() as client:
        result = await _fetch_chart(client, sym.yahoo, rng=rng, interval=interval)
    timestamps = result.get("timestamp") or []
    try:
        closes = result["indicators"]["quote"][0]["close"]
    except (KeyError, IndexError, TypeError):
        closes = []
    points: list[HistoryPoint] = []
    for ts, close in zip(timestamps, closes):
        if close is not None:
            points.append(HistoryPoint(time=int(ts), value=round(float(close), 4)))
    return points
