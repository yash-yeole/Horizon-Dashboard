import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from ..models import RigCountResponse
from ..services import bakerhughes

router = APIRouter(prefix="/api", tags=["rigcount"])

# Baker Hughes data is weekly (NA) / monthly (intl) and the download is ~8 MB,
# so we fetch once, persist the parsed result, and only re-pull on ?refresh=true.
_CACHE_FILE = Path(__file__).resolve().parents[2] / ".bh_cache" / "rigcount.json"
_store: dict | None = None


def _load() -> dict | None:
    global _store
    if _store is None and _CACHE_FILE.exists():
        try:
            _store = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _store = None
    return _store


def _save(payload: RigCountResponse) -> dict:
    global _store
    _store = payload.model_dump()
    try:
        _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _CACHE_FILE.write_text(json.dumps(_store), encoding="utf-8")
    except OSError:
        pass
    return _store


@router.get("/rigcount", response_model=RigCountResponse)
async def get_rigcount(refresh: bool = Query(False, description="Force a fresh pull from Baker Hughes")):
    """Baker Hughes rig count (North America weekly + International monthly).

    Served from a persisted snapshot; a live fetch happens only when there is no
    snapshot yet or refresh=true. On failure the previous snapshot is returned
    flagged stale.
    """
    snapshot = _load()
    if refresh or snapshot is None:
        try:
            payload = await bakerhughes.fetch_rigcount()
        except Exception:  # noqa: BLE001 — keep serving the last good snapshot
            if snapshot is not None:
                snapshot["stale"] = True
                return RigCountResponse.model_validate(snapshot)
            raise HTTPException(status_code=503, detail="Baker Hughes unavailable and no cached data")
        snapshot = _save(payload)

    return RigCountResponse.model_validate(snapshot)
