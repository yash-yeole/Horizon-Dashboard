import time

from fastapi import APIRouter, HTTPException, Query

from ..cache import TTLCache
from ..config import settings
from ..models import NewsResponse
from ..services import news

router = APIRouter(prefix="/api", tags=["news"])

_cache = TTLCache(ttl=settings.news_cache_ttl)
# One upstream fetch serves every request, sliced per `limit`. This keeps us well
# under FinancialJuice's rate limit no matter how many widgets/limits ask for news.
_FETCH_CAP = 60
_CACHE_KEY = "news:all"


@router.get("/news", response_model=NewsResponse)
async def get_news(limit: int = Query(40, ge=5, le=100)):
    """Energy-filtered FinancialJuice headlines with local sentiment tagging.

    A single cached upstream pull backs all requests. On failure (e.g. the feed
    rate-limits or goes down) we serve the last good snapshot flagged stale; if
    there's none yet, 502 so the frontend falls back to its static headlines.
    """
    snapshot: NewsResponse | None = _cache.get(_CACHE_KEY)
    if snapshot is None:
        try:
            items, stale = await news.fetch_news(_FETCH_CAP)
        except Exception:  # noqa: BLE001 — serve stale snapshot if we have one
            items, stale = [], True
        if items:
            snapshot = NewsResponse(items=items, as_of=time.time(), stale=stale)
            _cache.set(_CACHE_KEY, snapshot)
        else:
            old = _cache.get_stale(_CACHE_KEY)
            if old is not None:
                old.stale = True
                snapshot = old
            else:
                raise HTTPException(status_code=502, detail="news feed unavailable and no cached data")

    return NewsResponse(items=snapshot.items[:limit], as_of=snapshot.as_of, stale=snapshot.stale)
