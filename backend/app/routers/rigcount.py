import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from ..models import RigCountResponse
from ..services import bakerhughes

router = APIRouter(prefix="/api", tags=["rigcount"])

# Baker Hughes data is weekly (NA) / monthly (intl) and the download is ~8 MB,
# so we fetch once, persist the parsed result, and only re-pull on ?refresh=true.
# The runtime cache is gitignored/ephemeral; a committed seed (backend/seed/) ships
# in the Docker image so the deployed backend serves rig count immediately instead
# of hanging on a live Baker Hughes fetch (their site is slow/blocked from cloud
# hosts). Regenerate the seed offline with: python backend/refresh_rigcount.py
_CACHE_FILE = Path(__file__).resolve().parents[2] / ".bh_cache" / "rigcount.json"
_SEED_FILE = Path(__file__).resolve().parents[2] / "seed" / "rigcount.json"
_store: dict | None = None


def _load() -> dict | None:
    global _store
    if _store is None:
        # Runtime cache (freshest, from a live refresh) wins over the shipped seed.
        for f in (_CACHE_FILE, _SEED_FILE):
            if f.exists():
                try:
                    _store = json.loads(f.read_text(encoding="utf-8"))
                    break
                except (OSError, ValueError):
                    continue
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
