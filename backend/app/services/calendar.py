"""Energy market calendar — rule-based, no API key required.

Sources:
  EIA Petroleum:  every Wednesday 10:30 ET; holiday exceptions from
                  eia.gov/petroleum/supply/weekly/schedule.php (2026 hard-coded).
  EIA Nat Gas:    every Thursday 10:30 ET (same holiday shift pattern).
  CFTC COT:       exact 2026 dates from cftc.gov/MarketReports/.../ReleaseSchedule
  Baker Hughes:   every Friday 13:00 ET.
  OPEC+ / IEA / OPEC MOMR / EIA STEO: monthly, hard-coded 2026 dates.
"""
from __future__ import annotations

from datetime import date, timedelta

from ..models import CalendarEvent

# ── 2026 EIA Petroleum holiday exceptions ─────────────────────
# Key = normal Wednesday; Value = actual delayed release date.
_PETRO_DELAY: dict[date, date] = {
    date(2026, 1, 21): date(2026, 1, 22),
    date(2026, 2, 18): date(2026, 2, 19),
    date(2026, 5, 27): date(2026, 5, 28),
    date(2026, 9,  9): date(2026, 9, 10),
    date(2026, 10, 14): date(2026, 10, 15),
    date(2026, 11, 11): date(2026, 11, 12),
}

# ── 2026 CFTC COT exact dates (from cftc.gov release schedule) ─
_CFTC_2026: list[date] = [
    date(2026, 1, 5), date(2026, 1, 9), date(2026, 1, 16), date(2026, 1, 23), date(2026, 1, 30),
    date(2026, 2, 6), date(2026, 2, 13), date(2026, 2, 20), date(2026, 2, 27),
    date(2026, 3, 6), date(2026, 3, 13), date(2026, 3, 20), date(2026, 3, 27),
    date(2026, 4, 3), date(2026, 4, 10), date(2026, 4, 17), date(2026, 4, 24),
    date(2026, 5, 1), date(2026, 5, 8), date(2026, 5, 15), date(2026, 5, 22), date(2026, 5, 29),
    date(2026, 6, 5), date(2026, 6, 12), date(2026, 6, 22), date(2026, 6, 26),
    date(2026, 7, 6), date(2026, 7, 10), date(2026, 7, 17), date(2026, 7, 24), date(2026, 7, 31),
    date(2026, 8, 7), date(2026, 8, 14), date(2026, 8, 21), date(2026, 8, 28),
    date(2026, 9, 4), date(2026, 9, 11), date(2026, 9, 18), date(2026, 9, 25),
    date(2026, 10, 2), date(2026, 10, 9), date(2026, 10, 16), date(2026, 10, 23), date(2026, 10, 30),
    date(2026, 11, 6), date(2026, 11, 16), date(2026, 11, 20), date(2026, 11, 30),
    date(2026, 12, 4), date(2026, 12, 11), date(2026, 12, 18), date(2026, 12, 28),
]

# ── Monthly fixed-calendar events (2026) ──────────────────────
_OPEC_MEETINGS: list[date] = [
    date(2026, 2, 3), date(2026, 4, 7), date(2026, 6, 1),
    date(2026, 8, 4), date(2026, 10, 6), date(2026, 12, 1),
]

_IEA_OMR: list[date] = [
    date(2026, 1, 14), date(2026, 2, 11), date(2026, 3, 13),
    date(2026, 4, 15), date(2026, 5, 13), date(2026, 6, 10),
    date(2026, 7, 10), date(2026, 8, 12), date(2026, 9, 11),
    date(2026, 10, 14), date(2026, 11, 13), date(2026, 12, 11),
]

_OPEC_MOMR: list[date] = [
    date(2026, 1, 13), date(2026, 2, 10), date(2026, 3, 11),
    date(2026, 4, 14), date(2026, 5, 12), date(2026, 6, 9),
    date(2026, 7, 14), date(2026, 8, 11), date(2026, 9, 8),
    date(2026, 10, 13), date(2026, 11, 10), date(2026, 12, 9),
]

_EIA_STEO: list[date] = [
    date(2026, 1, 7), date(2026, 2, 11), date(2026, 3, 11),
    date(2026, 4, 8), date(2026, 5, 6), date(2026, 6, 10),
    date(2026, 7, 8), date(2026, 8, 12), date(2026, 9, 9),
    date(2026, 10, 7), date(2026, 11, 11), date(2026, 12, 9),
]


def _wednesdays(start: date, end: date) -> list[tuple[date, bool]]:
    """EIA Petroleum dates: (actual_release, is_delayed)."""
    anchor = start - timedelta(days=7)
    days_fwd = (2 - anchor.weekday()) % 7
    d = anchor + timedelta(days=days_fwd)
    out: list[tuple[date, bool]] = []
    while d <= end:
        actual = _PETRO_DELAY.get(d, d)
        if start <= actual <= end:
            out.append((actual, actual != d))
        d += timedelta(days=7)
    return out


def _thursdays(start: date, end: date) -> list[date]:
    """EIA Natural Gas Storage dates (every Thursday, no explicit holiday list)."""
    anchor = start - timedelta(days=7)
    days_fwd = (3 - anchor.weekday()) % 7
    d = anchor + timedelta(days=days_fwd)
    out: list[date] = []
    while d <= end:
        if start <= d <= end:
            out.append(d)
        d += timedelta(days=7)
    return out


def _fridays(start: date, end: date) -> list[date]:
    anchor = start - timedelta(days=7)
    days_fwd = (4 - anchor.weekday()) % 7
    d = anchor + timedelta(days=days_fwd)
    out: list[date] = []
    while d <= end:
        if start <= d <= end:
            out.append(d)
        d += timedelta(days=7)
    return out


def generate_events(days: int = 60) -> list[CalendarEvent]:
    today = date.today()
    end = today + timedelta(days=days)
    events: list[CalendarEvent] = []

    for d, delayed in _wednesdays(today, end):
        events.append(CalendarEvent(
            date=d.isoformat(), time_et="10:30",
            title="EIA Weekly Petroleum Status Report",
            category="EIA", importance="high",
            description="US crude oil, gasoline & distillate inventory data",
            is_delayed=delayed,
        ))

    for d in _thursdays(today, end):
        events.append(CalendarEvent(
            date=d.isoformat(), time_et="10:30",
            title="EIA Natural Gas Storage Report",
            category="EIA", importance="medium",
            description="Weekly underground natural gas storage levels",
            is_delayed=False,
        ))

    for d in _fridays(today, end):
        events.append(CalendarEvent(
            date=d.isoformat(), time_et="13:00",
            title="Baker Hughes Rig Count",
            category="BakerHughes", importance="medium",
            description="North America & International active drilling rigs",
            is_delayed=False,
        ))

    for d in _CFTC_2026:
        if today <= d <= end:
            delayed = d.weekday() != 4
            events.append(CalendarEvent(
                date=d.isoformat(), time_et="15:30",
                title="CFTC Commitments of Traders",
                category="CFTC", importance="high",
                description="Managed-money net positions — crude oil & products",
                is_delayed=delayed,
            ))

    for d in _OPEC_MEETINGS:
        if today <= d <= end:
            events.append(CalendarEvent(
                date=d.isoformat(), time_et="",
                title="OPEC+ Ministerial Meeting",
                category="OPEC", importance="high",
                description="Production policy decision — market-moving event",
                is_delayed=False,
            ))

    for d in _IEA_OMR:
        if today <= d <= end:
            events.append(CalendarEvent(
                date=d.isoformat(), time_et="",
                title="IEA Oil Market Report",
                category="IEA", importance="high",
                description="Monthly supply, demand & price outlook",
                is_delayed=False,
            ))

    for d in _OPEC_MOMR:
        if today <= d <= end:
            events.append(CalendarEvent(
                date=d.isoformat(), time_et="",
                title="OPEC Monthly Oil Market Report",
                category="OPEC", importance="medium",
                description="OPEC's monthly supply & demand assessment",
                is_delayed=False,
            ))

    for d in _EIA_STEO:
        if today <= d <= end:
            events.append(CalendarEvent(
                date=d.isoformat(), time_et="",
                title="EIA Short-Term Energy Outlook",
                category="EIA", importance="medium",
                description="Monthly price & supply/demand forecasts",
                is_delayed=False,
            ))

    events.sort(key=lambda e: (e.date, e.time_et or "99:99"))
    return events
