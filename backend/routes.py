"""All HTTP endpoints for the HORIZON API.

One router, grouped by domain. Each section is tagged so the interactive docs
at /docs stay organised.
"""
import json
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from cache import TTLCache
from config import settings
from models import (
    CalendarEvent,
    CftcResponse,
    CurveResponse,
    CurveStructureResponse,
    EiaInventoryResponse,
    HistoryResponse,
    LeadLagResponse,
    NewsResponse,
    Quote,
    QuotesResponse,
    ReleaseImpactResponse,
    RigCountResponse,
)
from services import backtest, bakerhughes, cftc, eia, leadlag, news, paper, release_impact
from services import curve as curve_service
from services import shipping as shipping_service
from services import yahoo
from services.calendar import generate_events
from symbols import BY_ID, GROUPS

router = APIRouter(prefix="/api")

HERE = Path(__file__).resolve().parent


# ---------------------------------------------------------------- calendar

@router.get("/calendar", response_model=list[CalendarEvent], tags=["calendar"])
async def get_calendar(days: int = Query(default=60, ge=1, le=365)) -> list[CalendarEvent]:
    """Return energy-market calendar events for the next N days."""
    return generate_events(days)


# ------------------------------------------------------------------ market

_quote_cache = TTLCache(ttl=settings.cache_ttl)

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


@router.get("/quotes", response_model=QuotesResponse, tags=["market"])
async def get_quotes(group: str = Query("core", description="core | macro | products | all")):
    group = group.lower()
    if group not in GROUPS:
        raise HTTPException(status_code=400, detail=f"unknown group '{group}'")

    cache_key = f"quotes:{group}"
    cached = _quote_cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        quotes = await yahoo.fetch_quotes(GROUPS[group])
    except Exception:  # noqa: BLE001 — fall back to stale snapshot if we have one
        quotes = []

    if not quotes:
        stale = _quote_cache.get_stale(cache_key)
        if stale is not None:
            for q in stale.quotes:
                q.stale = True
            return stale
        raise HTTPException(status_code=502, detail="upstream unavailable and no cached data")

    payload = QuotesResponse(quotes=quotes, as_of=time.time())
    _quote_cache.set(cache_key, payload)
    return payload


@router.get("/quote/{quote_id}", response_model=Quote, tags=["market"])
async def get_quote(quote_id: str):
    sym = BY_ID.get(quote_id)
    if sym is None:
        raise HTTPException(status_code=404, detail=f"unknown id '{quote_id}'")

    cache_key = f"quote:{quote_id}"
    cached = _quote_cache.get(cache_key)
    if cached is not None:
        return cached

    quotes = await yahoo.fetch_quotes([sym])
    if not quotes:
        stale = _quote_cache.get_stale(cache_key)
        if stale is not None:
            stale.stale = True
            return stale
        raise HTTPException(status_code=502, detail="upstream unavailable")

    quote = quotes[0]
    _quote_cache.set(cache_key, quote)
    return quote


@router.get("/history/{quote_id}", response_model=HistoryResponse, tags=["market"])
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
    cached = _quote_cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        points = await yahoo.fetch_history(sym, rng, iv)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"upstream error: {exc}") from exc

    payload = HistoryResponse(
        id=sym.id, yahoo_symbol=sym.yahoo, range=rng, interval=iv, points=points
    )
    _quote_cache.set(cache_key, payload)
    return payload


# ------------------------------------------------------------------- curve

@router.get("/curve/{curve_id}/structure", response_model=CurveStructureResponse, tags=["curve"])
async def get_curve_structure(curve_id: str):
    """Daily history of calendar spreads (M1-M2/M1-M6/M1-M12) and butterflies
    (1-2-3/2-3-4/4-5-6) derived from the commodity's forward curve."""
    try:
        return await curve_service.get_structure_history(curve_id.lower())
    except KeyError:
        raise HTTPException(status_code=404, detail=f"no curve for '{curve_id}'")
    except curve_service.CurveUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/curve/{curve_id}", response_model=CurveResponse, tags=["curve"])
async def get_curve(
    curve_id: str,
    compare: str = Query("now", description="now | w1 | m1"),
):
    """Forward curve for a commodity.

    Brent/Gas Oil come from ICE settlement CSVs; WTI/Heating Oil/RBOB are
    assembled from Yahoo monthly futures contracts. `price` is the latest curve;
    `previousPrice` is the comparison snapshot (prior day / ~1 week / ~1 month).
    """
    try:
        return await curve_service.get_curve(curve_id.lower(), compare.lower())
    except KeyError:
        raise HTTPException(status_code=404, detail=f"no curve for '{curve_id}'")
    except ValueError:
        raise HTTPException(status_code=400, detail=f"bad compare '{compare}'")
    except curve_service.CurveUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


# --------------------------------------------------------------------- EIA

# Persisted snapshot of the last successful EIA pull. EIA data is weekly, so we
# fetch once and serve this indefinitely — the API is only hit again on an
# explicit ?refresh=true (the UI's Refresh button). Survives server restarts.
_EIA_CACHE_FILE = HERE / ".eia_cache.json"
_eia_store: dict | None = None


def _eia_load() -> dict | None:
    global _eia_store
    if _eia_store is None and _EIA_CACHE_FILE.exists():
        try:
            _eia_store = json.loads(_EIA_CACHE_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _eia_store = None
    return _eia_store


def _eia_save(payload: EiaInventoryResponse) -> dict:
    global _eia_store
    _eia_store = payload.model_dump()
    try:
        _EIA_CACHE_FILE.write_text(json.dumps(_eia_store), encoding="utf-8")
    except OSError:
        pass
    return _eia_store


def _eia_sliced(snapshot: dict, weeks: int, stale: bool = False) -> EiaInventoryResponse:
    resp = EiaInventoryResponse.model_validate(snapshot)
    resp.stale = stale
    for s in resp.series:
        s.points = s.points[-weeks:]
    return resp


@router.get("/eia/inventories", response_model=EiaInventoryResponse, tags=["eia"])
async def get_inventories(
    weeks: int = Query(24, ge=4, le=104),
    refresh: bool = Query(False, description="Force a fresh pull from EIA"),
):
    """Weekly EIA petroleum stocks.

    Served from a persisted snapshot with no expiry. A live EIA call happens only
    when there is no snapshot yet, or when refresh=true is requested. On refresh
    failure the previous snapshot is returned flagged stale=true.
    """
    snapshot = _eia_load()

    if refresh or snapshot is None:
        try:
            payload = await eia.fetch_inventories()
        except Exception:  # noqa: BLE001 — keep serving the last good snapshot
            if snapshot is not None:
                return _eia_sliced(snapshot, weeks, stale=True)
            raise HTTPException(status_code=503, detail="EIA unavailable and no cached data")
        snapshot = _eia_save(payload)

    return _eia_sliced(snapshot, weeks)


# -------------------------------------------------------------------- news

_news_cache = TTLCache(ttl=settings.news_cache_ttl)
# One upstream fetch serves every request, sliced per `limit`. This keeps us well
# under FinancialJuice's rate limit no matter how many widgets/limits ask for news.
_NEWS_FETCH_CAP = 60
_NEWS_KEY = "news:all"


@router.get("/news", response_model=NewsResponse, tags=["news"])
async def get_news(limit: int = Query(40, ge=5, le=100)):
    """Energy-filtered FinancialJuice headlines with local sentiment tagging.

    A single cached upstream pull backs all requests. On failure (e.g. the feed
    rate-limits or goes down) we serve the last good snapshot flagged stale; if
    there's none yet, 502 so the frontend falls back to its static headlines.
    """
    snapshot: NewsResponse | None = _news_cache.get(_NEWS_KEY)
    if snapshot is None:
        try:
            items, stale = await news.fetch_news(_NEWS_FETCH_CAP)
        except Exception:  # noqa: BLE001 — serve stale snapshot if we have one
            items, stale = [], True
        if items:
            snapshot = NewsResponse(items=items, as_of=time.time(), stale=stale)
            _news_cache.set(_NEWS_KEY, snapshot)
        else:
            old = _news_cache.get_stale(_NEWS_KEY)
            if old is not None:
                old.stale = True
                snapshot = old
            else:
                raise HTTPException(status_code=502, detail="news feed unavailable and no cached data")

    return NewsResponse(items=snapshot.items[:limit], as_of=snapshot.as_of, stale=snapshot.stale)


# -------------------------------------------------------------------- CFTC

_cftc_cache = TTLCache(ttl=settings.cftc_cache_ttl)


@router.get("/cftc/positioning", response_model=CftcResponse, tags=["cftc"])
async def get_positioning(weeks: int = Query(52, ge=4, le=260)):
    """CFTC Commitments of Traders positioning for the energy contracts.

    Weekly data cached for an hour; on failure serves the last snapshot flagged
    stale, else 502 so the frontend can fall back.
    """
    cache_key = f"cftc:{weeks}"
    cached = _cftc_cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        contracts = await cftc.fetch_positioning(weeks)
    except Exception:  # noqa: BLE001
        contracts = []

    contracts = [c for c in contracts if c.report_date]
    if not contracts:
        stale = _cftc_cache.get_stale(cache_key)
        if stale is not None:
            stale.stale = True
            return stale
        raise HTTPException(status_code=502, detail="CFTC unavailable and no cached data")

    as_of = max((c.report_date for c in contracts), default="")
    payload = CftcResponse(as_of=as_of, stale=False, contracts=contracts)
    _cftc_cache.set(cache_key, payload)
    return payload


# --------------------------------------------------------------- rig count

# Baker Hughes data is weekly (NA) / monthly (intl) and the download is ~8 MB,
# so we fetch once, persist the parsed result, and only re-pull on ?refresh=true.
# The runtime cache is gitignored/ephemeral; the committed seed (backend/seed/)
# lets a fresh clone serve rig count immediately instead of hanging on a live
# Baker Hughes fetch (their site is slow).
_BH_CACHE_FILE = HERE / ".bh_cache" / "rigcount.json"
_BH_SEED_FILE = HERE / "seed" / "rigcount.json"
_bh_store: dict | None = None


def _bh_load() -> dict | None:
    global _bh_store
    if _bh_store is None:
        # Runtime cache (freshest, from a live refresh) wins over the shipped seed.
        for f in (_BH_CACHE_FILE, _BH_SEED_FILE):
            if f.exists():
                try:
                    _bh_store = json.loads(f.read_text(encoding="utf-8"))
                    break
                except (OSError, ValueError):
                    continue
    return _bh_store


def _bh_save(payload: RigCountResponse) -> dict:
    global _bh_store
    _bh_store = payload.model_dump()
    try:
        _BH_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _BH_CACHE_FILE.write_text(json.dumps(_bh_store), encoding="utf-8")
    except OSError:
        pass
    return _bh_store


@router.get("/rigcount", response_model=RigCountResponse, tags=["rigcount"])
async def get_rigcount(refresh: bool = Query(False, description="Force a fresh pull from Baker Hughes")):
    """Baker Hughes rig count (North America weekly + International monthly).

    Served from a persisted snapshot; a live fetch happens only when there is no
    snapshot yet or refresh=true. On failure the previous snapshot is returned
    flagged stale.
    """
    snapshot = _bh_load()
    if refresh or snapshot is None:
        try:
            payload = await bakerhughes.fetch_rigcount()
        except Exception:  # noqa: BLE001 — keep serving the last good snapshot
            if snapshot is not None:
                snapshot["stale"] = True
                return RigCountResponse.model_validate(snapshot)
            raise HTTPException(status_code=503, detail="Baker Hughes unavailable and no cached data")
        snapshot = _bh_save(payload)

    return RigCountResponse.model_validate(snapshot)


# ---------------------------------------------------------------- lead-lag

@router.get("/leadlag", response_model=LeadLagResponse, tags=["leadlag"])
async def get_leadlag(
    base: str = Query("brent"),
    timeframe: str = Query("intraday", description="intraday | hourly | daily"),
):
    """Return-based lead-lag (cross-correlation) of the energy complex vs `base`."""
    try:
        return await leadlag.compute(base.lower(), timeframe.lower())
    except leadlag.LeadLagError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"lead-lag unavailable: {exc}") from exc


# ---------------------------------------------------------- release impact

# The call doesn't change intraday (consensus/API update slowly), so cache aggressively.
_impact_cache = TTLCache(ttl=900.0)  # 15 min
_IMPACT_KEY = "release-impact"


@router.get("/release-impact", response_model=ReleaseImpactResponse, tags=["release-impact"])
async def get_release_impact():
    """Assess the likely Brent impact of the upcoming weekly EIA crude release.

    Live surprise inputs (consensus / API / next-release date) + news theme
    routing, layered over a versioned snapshot of the validated research model
    (inventory beta, top-3 driver ranking, framework). Serves a stale snapshot
    if upstream fetches fail.
    """
    snap = _impact_cache.get(_IMPACT_KEY)
    if snap is not None:
        return snap
    try:
        snap = await release_impact.assess()
        _impact_cache.set(_IMPACT_KEY, snap)
        return snap
    except Exception:  # noqa: BLE001 — serve stale if we have one
        old = _impact_cache.get_stale(_IMPACT_KEY)
        if old is not None:
            old.stale = True
            return old
        raise


# ---------------------------------------------------------------- shipping

@router.get("/shipping/status", tags=["shipping"])
def get_shipping_status():
    return shipping_service.status()


@router.get("/shipping/vessels", tags=["shipping"])
def get_vessels(limit: int = Query(800, ge=1, le=5000)):
    """Live oil tankers (AIS type 80-89) currently in the tracked regions."""
    return {"status": shipping_service.status(), "vessels": shipping_service.vessels(limit)}


@router.get("/shipping/heatmap", tags=["shipping"])
def get_heatmap():
    """Tanker-density points [lat, lon, weight] for the heatmap layer."""
    return {"status": shipping_service.status(), "points": shipping_service.heatmap()}


@router.get("/shipping/chokepoints", tags=["shipping"])
def get_chokepoints():
    """Per-chokepoint tanker counts + deviation/status (7d/30d come in Phase 2)."""
    return {"status": shipping_service.status(), "chokepoints": shipping_service.chokepoints()}


@router.get("/shipping/routes", tags=["shipping"])
def get_routes():
    """Phase 2: inferred tanker corridors (AG→China, Russia→India, …)."""
    return {"status": shipping_service.status(), "routes": [], "phase": 2}


@router.get("/shipping/congestion", tags=["shipping"])
def get_congestion():
    """Phase 2: port congestion + floating-storage + physical-flow-score."""
    return {"status": shipping_service.status(), "congestion": [], "phase": 2}


# --------------------------------------------------------- paper trading
# NOTE: /paper/{key} is a catch-all, so it must stay last in this section.

@router.get("/paper/structures", tags=["paper-trading"])
async def get_structures():
    """List the tradeable structures the live DB supports."""
    return {"structures": paper.list_structures(), "thresholds": paper._thresholds()}


@router.get("/paper/state", tags=["paper-trading"])
async def get_state(refresh: bool = Query(False)):
    """Full snapshot for every structure (fair value, signal, trades, stats)."""
    return paper.get_all(refresh=refresh)


@router.get("/paper/backtest/results", tags=["paper-trading"])
async def get_backtest():
    """Full-history intraday backtest of the model engine (flat 1-contract)."""
    return backtest.get_backtest()


@router.get("/paper/{key}", tags=["paper-trading"])
async def get_one(key: str, refresh: bool = Query(False)):
    """Snapshot for a single structure (e.g. wti_cal, brent_fly)."""
    try:
        return paper.get_structure(key, refresh=refresh)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"unknown structure '{key}'")
