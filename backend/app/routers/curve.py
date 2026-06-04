from fastapi import APIRouter, HTTPException, Query

from ..models import CurveResponse
from ..services import curve as curve_service

router = APIRouter(prefix="/api", tags=["curve"])


@router.get("/curve/{curve_id}", response_model=CurveResponse)
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
