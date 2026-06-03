from fastapi import APIRouter, HTTPException, Query

from ..models import CurveResponse
from ..services import curve as curve_service

router = APIRouter(prefix="/api", tags=["curve"])


@router.get("/curve/{curve_id}", response_model=CurveResponse)
def get_curve(
    curve_id: str,
    compare: str = Query("now", description="now | w1 | m1"),
):
    """Forward curve for a commodity, sourced from a local settlement CSV.

    `price` is the latest available curve; `previousPrice` is the comparison
    snapshot (prior trading day / ~1 week ago / ~1 month ago).
    """
    try:
        return curve_service.get_curve(curve_id.lower(), compare.lower())
    except KeyError:
        raise HTTPException(status_code=404, detail=f"no curve for '{curve_id}'")
    except ValueError:
        raise HTTPException(status_code=400, detail=f"bad compare '{compare}'")
    except curve_service.CurveUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
