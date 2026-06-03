"""Forward-curve data sourced from a local settlement CSV.

The CSV (ICE Brent, `LCOc1`..`LCOcN`) has, for each contract month, a
(Timestamp, SETTLE) column pair. Each row is one trading day. We expose the
most recent curve plus a historical snapshot (prior day / week / month) so the
frontend can show how the curve has shifted.

Parsed data is cached in-process and reloaded only when the file's mtime
changes, so repeated requests don't re-read the ~1MB file.
"""
from __future__ import annotations

import csv
from datetime import date, datetime, timedelta
from pathlib import Path

from ..config import settings

# Day-first formats seen in the source file (e.g. "26-05-26", "12/5/2026").
_DATE_FORMATS = ("%d-%m-%y", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y")

# Curves we can serve and how to label them. Only Brent for now.
CURVE_META: dict[str, dict[str, str]] = {
    "brent": {"name": "Brent Crude", "currency": "USD", "unit": "bbl"},
}

# compare key -> calendar lookback. "now" means the immediately prior trading day.
_COMPARE_DELTAS: dict[str, timedelta | None] = {
    "now": None,
    "w1": timedelta(days=7),
    "m1": timedelta(days=30),
}


class CurveUnavailable(Exception):
    """Raised when the curve source file is missing or unparseable."""


def _parse_date(raw: str) -> date | None:
    raw = raw.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


# (mtime, parsed) cache — parsed is a list of (date, [settles]) sorted ascending.
_cache: tuple[float, list[tuple[date, list[float]]]] | None = None


def _load() -> list[tuple[date, list[float]]]:
    global _cache
    path = Path(settings.brent_curve_csv)
    if not path.is_file():
        raise CurveUnavailable(f"curve file not found: {path}")

    mtime = path.stat().st_mtime
    if _cache is not None and _cache[0] == mtime:
        return _cache[1]

    rows: list[tuple[date, list[float]]] = []
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.reader(fh)
        all_rows = list(reader)

    # Row 0 = contract codes, row 1 = Timestamp/SETTLE labels, row 2+ = data.
    # Columns come in (date, settle) pairs; settle for contract i is col 2*i+1.
    for raw in all_rows[2:]:
        if not raw or not raw[0].strip():
            continue
        d = _parse_date(raw[0])
        if d is None:
            continue
        settles: list[float] = []
        for i in range(1, len(raw), 2):
            cell = raw[i].strip() if i < len(raw) else ""
            try:
                settles.append(float(cell))
            except ValueError:
                break  # stop at the first non-numeric/blank settle
        if settles:
            rows.append((d, settles))

    if not rows:
        raise CurveUnavailable("curve file contained no usable rows")

    rows.sort(key=lambda r: r[0])  # ascending by date
    _cache = (mtime, rows)
    return rows


def get_curve(curve_id: str, compare: str = "now") -> dict:
    """Return the latest forward curve plus a comparison snapshot.

    Shape mirrors the `CurveResponse` pydantic model (snake_case here).
    """
    meta = CURVE_META.get(curve_id)
    if meta is None:
        raise KeyError(curve_id)
    if compare not in _COMPARE_DELTAS:
        raise ValueError(compare)

    rows = _load()
    latest_date, latest = rows[-1]

    # Pick the comparison row.
    delta = _COMPARE_DELTAS[compare]
    if delta is None:
        compare_date, compare_settles = rows[-2] if len(rows) > 1 else rows[-1]
    else:
        target = latest_date - delta
        # latest row at or before the target date; fall back to the oldest row.
        prior = [r for r in rows if r[0] <= target]
        compare_date, compare_settles = prior[-1] if prior else rows[0]

    n = min(len(latest), len(compare_settles))
    points = [
        {
            "month": f"M{i + 1}",
            "price": latest[i],
            "previous_price": compare_settles[i],
        }
        for i in range(n)
    ]

    return {
        "id": curve_id,
        "name": meta["name"],
        "currency": meta["currency"],
        "unit": meta["unit"],
        "as_of": latest_date.isoformat(),
        "compare": compare,
        "compare_date": compare_date.isoformat(),
        "points": points,
    }
