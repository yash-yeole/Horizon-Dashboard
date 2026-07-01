from fastapi import APIRouter

from ..cache import TTLCache
from ..models import ReleaseImpactResponse
from ..services import release_impact

router = APIRouter(prefix="/api", tags=["release-impact"])

# The call doesn't change intraday (consensus/API update slowly), so cache aggressively.
_cache = TTLCache(ttl=900.0)  # 15 min
_KEY = "release-impact"


@router.get("/release-impact", response_model=ReleaseImpactResponse)
async def get_release_impact():
    """Assess the likely Brent impact of the upcoming weekly EIA crude release.

    Live surprise inputs (consensus / API / next-release date) + news theme
    routing, layered over a versioned snapshot of the validated research model
    (inventory beta, top-3 driver ranking, framework). Serves a stale snapshot
    if upstream fetches fail.
    """
    snap = _cache.get(_KEY)
    if snap is not None:
        return snap
    try:
        snap = await release_impact.assess()
        _cache.set(_KEY, snap)
        return snap
    except Exception:  # noqa: BLE001 — serve stale if we have one
        old = _cache.get_stale(_KEY)
        if old is not None:
            old.stale = True
            return old
        raise
