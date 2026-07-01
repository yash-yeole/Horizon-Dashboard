"""Live EIA crude inventory-change forecast — OUR expected number.

Productionizes research/inventory-impact/predict_inventory.py. The model is the EIA supply/
demand balance identity, lagged so every input is known BEFORE the Wednesday
release:

    dStock_t = const + b1*balance(t-1) + b2*dSPR(t-1)
                     + b3*dStock(t-1) + b4*dStock(t-2) + seasonality(week-of-year)

where balance = (production + imports - exports - refinery_inputs) * 7  (M bbl/wk).

The COEFFICIENTS are a versioned snapshot from the validated offline fit (full
sample 2015->2026, in-sample R2=0.16; walk-forward + 70/30 hold-out OOS R2=0.11;
it beat the Reuters consensus on the 24-Jun-2026 print). We only need the LATEST
EIA fundamentals to build the current feature row, so the number refreshes live
each week as a plain dot-product — no numpy/statsmodels in the backend.
"""
from __future__ import annotations

import math
from datetime import date, timedelta

import httpx

from ..config import settings

# snapshot of the full-sample OLS fit (see research/inventory-impact/predict_inventory.py)
_COEF: dict[str, float] = {
    "const": 0.3801,
    "bal_l1": 0.1380,    # supply/demand balance, last week (M bbl)
    "dspr_l1": -0.0625,  # SPR change, last week (M bbl)
    "ar1": 0.0083,       # stock change, last week (M bbl)
    "ar2": 0.1302,       # stock change, two weeks ago (M bbl)
    "sin1": 0.6153, "cos1": 1.1905, "sin2": 0.0441, "cos2": -1.3145,
}
_R2 = 0.159
_OOS_R2 = 0.105
_RESID_SD = 4.99

_SERIES = {  # key -> EIA weekly series id
    "stocks": "PET.WCESTUS1.W",   # commercial crude stock level (k bbl)
    "prod": "PET.WCRFPUS2.W",     # field production (k bbl/d)
    "imp": "PET.WCEIMUS2.W",      # imports (k bbl/d)
    "exp": "PET.WCREXUS2.W",      # exports (k bbl/d)
    "refin": "PET.WCRRIUS2.W",    # refiner crude inputs (k bbl/d)
    "spr": "PET.WCSSTUS1.W",      # SPR stock level (k bbl)
}


async def _last(client: httpx.AsyncClient, series_id: str, n: int = 6) -> list[tuple[str, float]]:
    r = await client.get(f"/seriesid/{series_id}", params={"api_key": settings.eia_api_key, "length": n})
    r.raise_for_status()
    rows = r.json().get("response", {}).get("data", [])
    pts = [(x["period"], float(x["value"])) for x in rows
           if x.get("period") and x.get("value") is not None]
    pts.sort(key=lambda x: x[0])
    return pts


async def forecast() -> dict | None:
    """Return the model's expected stock change for the upcoming release, or None."""
    if not settings.eia_api_key:
        return None
    try:
        async with httpx.AsyncClient(base_url=settings.eia_base_url, timeout=settings.request_timeout) as client:
            data = {k: await _last(client, sid) for k, sid in _SERIES.items()}
    except Exception:  # noqa: BLE001
        return None

    st = [v for _, v in data["stocks"]]
    sp = [v for _, v in data["spr"]]
    if len(st) < 3 or len(sp) < 2 or not all(data[k] for k in ("prod", "imp", "exp", "refin")):
        return None

    latest_period = data["stocks"][-1][0]                       # 'YYYY-MM-DD' week-ending
    bal_l1 = (data["prod"][-1][1] + data["imp"][-1][1]
              - data["exp"][-1][1] - data["refin"][-1][1]) * 7 / 1000.0
    dspr_l1 = (sp[-1] - sp[-2]) / 1000.0
    ar1 = (st[-1] - st[-2]) / 1000.0
    ar2 = (st[-2] - st[-3]) / 1000.0

    target = date.fromisoformat(latest_period) + timedelta(days=7)   # next week the print covers
    woy = target.isocalendar().week
    f = {"const": 1.0, "bal_l1": bal_l1, "dspr_l1": dspr_l1, "ar1": ar1, "ar2": ar2}
    for h in (1, 2):
        f[f"sin{h}"] = math.sin(2 * math.pi * h * woy / 52.0)
        f[f"cos{h}"] = math.cos(2 * math.pi * h * woy / 52.0)
    point = sum(_COEF[c] * f[c] for c in _COEF)

    return {
        "target_week_ending": target.isoformat(),
        "as_of_week": latest_period,
        "predicted_change": round(point, 2),
        "sd": _RESID_SD, "r2": _R2, "oos_r2": _OOS_R2,
        "bal_l1": round(bal_l1, 1), "dspr_l1": round(dspr_l1, 1),
        "ar1": round(ar1, 1), "ar2": round(ar2, 1),
    }
