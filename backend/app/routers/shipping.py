from fastapi import APIRouter, Query

from ..services import shipping

router = APIRouter(prefix="/api/shipping", tags=["shipping"])


@router.get("/status")
def get_status():
    return shipping.status()


@router.get("/vessels")
def get_vessels(limit: int = Query(800, ge=1, le=5000)):
    """Live oil tankers (AIS type 80-89) currently in the tracked regions."""
    return {"status": shipping.status(), "vessels": shipping.vessels(limit)}


@router.get("/heatmap")
def get_heatmap():
    """Tanker-density points [lat, lon, weight] for the heatmap layer."""
    return {"status": shipping.status(), "points": shipping.heatmap()}


@router.get("/chokepoints")
def get_chokepoints():
    """Per-chokepoint tanker counts + deviation/status (7d/30d come in Phase 2)."""
    return {"status": shipping.status(), "chokepoints": shipping.chokepoints()}


@router.get("/routes")
def get_routes():
    """Phase 2: inferred tanker corridors (AG→China, Russia→India, …)."""
    return {"status": shipping.status(), "routes": [], "phase": 2}


@router.get("/congestion")
def get_congestion():
    """Phase 2: port congestion + floating-storage + physical-flow-score."""
    return {"status": shipping.status(), "congestion": [], "phase": 2}
