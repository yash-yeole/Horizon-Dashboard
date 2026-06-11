from fastapi import APIRouter, Query

from ..models import CalendarEvent
from ..services.calendar import generate_events

router = APIRouter(prefix="/api", tags=["calendar"])


@router.get("/calendar", response_model=list[CalendarEvent])
async def get_calendar(days: int = Query(default=60, ge=1, le=365)) -> list[CalendarEvent]:
    """Return energy-market calendar events for the next N days."""
    return generate_events(days)
