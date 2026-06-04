from fastapi import APIRouter, HTTPException, Query

from ..models import LeadLagResponse
from ..services import leadlag

router = APIRouter(prefix="/api", tags=["leadlag"])


@router.get("/leadlag", response_model=LeadLagResponse)
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
