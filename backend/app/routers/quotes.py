import time

from fastapi import APIRouter, HTTPException, Query

from ..cache import TTLCache
from ..config import settings
from ..models import HistoryResponse, Quote, QuotesResponse
from ..services import yahoo
from ..symbols import BY_ID, GROUPS

router = APIRouter(prefix="/api", tags=["market"])

_cache = TTLCache(ttl=settings.cache_ttl)

# Allowed Yahoo range -> sensible interval, used to validate history requests.
_RANGE_INTERVALS: dict[str, str] = {
    "1d": "5m",
    "5d": "15m",
    "1mo": "1h",
    "3mo": "1d",
    "6mo": "1d",
    "1y": "1d",
    "2y": "1wk",
    "5y": "1wk",
}


@router.get("/quotes", response_model=QuotesResponse)
async def get_quotes(group: str = Query("core", description="core | macro | products | all")):
    group = group.lower()
    if group not in GROUPS:
        raise HTTPException(status_code=400, detail=f"unknown group '{group}'")

    cache_key = f"quotes:{group}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        quotes = await yahoo.fetch_quotes(GROUPS[group])
    except Exception:  # noqa: BLE001 — fall back to stale snapshot if we have one
        quotes = []

    if not quotes:
        stale = _cache.get_stale(cache_key)
        if stale is not None:
            for q in stale.quotes:
                q.stale = True
            return stale
        raise HTTPException(status_code=502, detail="upstream unavailable and no cached data")

    payload = QuotesResponse(quotes=quotes, as_of=time.time())
    _cache.set(cache_key, payload)
    return payload


@router.get("/quote/{quote_id}", response_model=Quote)
async def get_quote(quote_id: str):
    sym = BY_ID.get(quote_id)
    if sym is None:
        raise HTTPException(status_code=404, detail=f"unknown id '{quote_id}'")

    cache_key = f"quote:{quote_id}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    quotes = await yahoo.fetch_quotes([sym])
    if not quotes:
        stale = _cache.get_stale(cache_key)
        if stale is not None:
            stale.stale = True
            return stale
        raise HTTPException(status_code=502, detail="upstream unavailable")

    quote = quotes[0]
    _cache.set(cache_key, quote)
    return quote


@router.get("/history/{quote_id}", response_model=HistoryResponse)
async def get_history(
    quote_id: str,
    range: str = Query("3mo"),
    interval: str | None = Query(None),
):
    sym = BY_ID.get(quote_id)
    if sym is None:
        raise HTTPException(status_code=404, detail=f"unknown id '{quote_id}'")
    rng = range.lower()
    if rng not in _RANGE_INTERVALS:
        raise HTTPException(status_code=400, detail=f"unsupported range '{range}'")
    iv = interval or _RANGE_INTERVALS[rng]

    cache_key = f"history:{quote_id}:{rng}:{iv}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        points = await yahoo.fetch_history(sym, rng, iv)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"upstream error: {exc}") from exc

    payload = HistoryResponse(
        id=sym.id, yahoo_symbol=sym.yahoo, range=rng, interval=iv, points=points
    )
    _cache.set(cache_key, payload)
    return payload
