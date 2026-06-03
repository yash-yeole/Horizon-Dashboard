from fastapi import APIRouter, HTTPException, Query

from ..cache import TTLCache
from ..config import settings
from ..models import CftcResponse
from ..services import cftc

router = APIRouter(prefix="/api", tags=["cftc"])

_cache = TTLCache(ttl=settings.cftc_cache_ttl)


@router.get("/cftc/positioning", response_model=CftcResponse)
async def get_positioning(weeks: int = Query(52, ge=4, le=260)):
    """CFTC Commitments of Traders positioning for the energy contracts.

    Weekly data cached for an hour; on failure serves the last snapshot flagged
    stale, else 502 so the frontend can fall back.
    """
    cache_key = f"cftc:{weeks}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        contracts = await cftc.fetch_positioning(weeks)
    except Exception:  # noqa: BLE001
        contracts = []

    contracts = [c for c in contracts if c.report_date]
    if not contracts:
        stale = _cache.get_stale(cache_key)
        if stale is not None:
            stale.stale = True
            return stale
        raise HTTPException(status_code=502, detail="CFTC unavailable and no cached data")

    as_of = max((c.report_date for c in contracts), default="")
    payload = CftcResponse(as_of=as_of, stale=False, contracts=contracts)
    _cache.set(cache_key, payload)
    return payload
