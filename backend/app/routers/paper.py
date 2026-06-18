"""Paper-trading / strategy-engine endpoints (Phase 7)."""
from fastapi import APIRouter, HTTPException, Query

from ..services import backtest, paper

router = APIRouter(prefix="/api/paper", tags=["paper-trading"])


@router.get("/structures")
async def get_structures():
    """List the tradeable structures the live DB supports."""
    return {"structures": paper.list_structures(), "thresholds": paper._thresholds()}


@router.get("/state")
async def get_state(refresh: bool = Query(False)):
    """Full snapshot for every structure (fair value, signal, trades, stats)."""
    return paper.get_all(refresh=refresh)


@router.get("/backtest/results")
async def get_backtest():
    """Full-history intraday backtest of the model engine (flat 1-contract)."""
    return backtest.get_backtest()


@router.get("/{key}")
async def get_one(key: str, refresh: bool = Query(False)):
    """Snapshot for a single structure (e.g. wti_cal, brent_fly)."""
    try:
        return paper.get_structure(key, refresh=refresh)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"unknown structure '{key}'")
