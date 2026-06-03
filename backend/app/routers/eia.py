import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from ..models import EiaInventoryResponse
from ..services import eia

router = APIRouter(prefix="/api", tags=["eia"])

# Persisted snapshot of the last successful EIA pull. EIA data is weekly, so we
# fetch once and serve this indefinitely — the API is only hit again on an
# explicit ?refresh=true (the UI's Refresh button). Survives server restarts.
_CACHE_FILE = Path(__file__).resolve().parents[2] / ".eia_cache.json"
_store: dict | None = None


def _load() -> dict | None:
    global _store
    if _store is None and _CACHE_FILE.exists():
        try:
            _store = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _store = None
    return _store


def _save(payload: EiaInventoryResponse) -> dict:
    global _store
    _store = payload.model_dump()
    try:
        _CACHE_FILE.write_text(json.dumps(_store), encoding="utf-8")
    except OSError:
        pass
    return _store


def _sliced(snapshot: dict, weeks: int, stale: bool = False) -> EiaInventoryResponse:
    resp = EiaInventoryResponse.model_validate(snapshot)
    resp.stale = stale
    for s in resp.series:
        s.points = s.points[-weeks:]
    return resp


@router.get("/eia/inventories", response_model=EiaInventoryResponse)
async def get_inventories(
    weeks: int = Query(24, ge=4, le=104),
    refresh: bool = Query(False, description="Force a fresh pull from EIA"),
):
    """Weekly EIA petroleum stocks.

    Served from a persisted snapshot with no expiry. A live EIA call happens only
    when there is no snapshot yet, or when refresh=true is requested. On refresh
    failure the previous snapshot is returned flagged stale=true.
    """
    snapshot = _load()

    if refresh or snapshot is None:
        try:
            payload = await eia.fetch_inventories()
        except Exception:  # noqa: BLE001 — keep serving the last good snapshot
            if snapshot is not None:
                return _sliced(snapshot, weeks, stale=True)
            raise HTTPException(status_code=503, detail="EIA unavailable and no cached data")
        snapshot = _save(payload)

    return _sliced(snapshot, weeks)
