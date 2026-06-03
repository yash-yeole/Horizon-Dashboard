"""CFTC Commitments of Traders — free Socrata API (no token).

Pulls the Disaggregated Futures-Only report for the energy contracts and
normalises trader-class positions (managed money, producer/merchant, swap
dealers, other reportables) plus a weekly managed-money net history.
"""
from __future__ import annotations

import asyncio

import httpx

from ..config import settings
from ..models import CftcContract, CftcPoint

# frontend key -> (CFTC contract market code, label)
CONTRACTS: dict[str, tuple[str, str]] = {
    "wti": ("067651", "WTI Crude"),
    "brent": ("06765T", "Brent (Last Day)"),
    "rbob": ("111659", "RBOB Gasoline"),
    "heatoil": ("022651", "Heating Oil (ULSD)"),
}

_FIELDS = [
    "report_date_as_yyyy_mm_dd",
    "open_interest_all",
    "m_money_positions_long_all", "m_money_positions_short_all",
    "prod_merc_positions_long", "prod_merc_positions_short",
    "swap_positions_long_all", "swap__positions_short_all",  # note: short has a double underscore in this dataset
    "other_rept_positions_long", "other_rept_positions_short",
]


class CftcError(RuntimeError):
    pass


def _i(v) -> int:
    try:
        return int(float(v)) if v is not None else 0
    except (TypeError, ValueError):
        return 0


async def _fetch_contract(client: httpx.AsyncClient, key: str, code: str, label: str, weeks: int) -> CftcContract:
    params = {
        "$where": f"cftc_contract_market_code='{code}'",
        "$order": "report_date_as_yyyy_mm_dd DESC",
        "$limit": weeks,
        "$select": ",".join(_FIELDS),
    }
    resp = await client.get(f"/resource/{settings.cftc_dataset}.json", params=params)
    resp.raise_for_status()
    rows = resp.json()
    if not rows:
        return CftcContract(id=key, name=label, code=code, report_date="")

    latest = rows[0]
    mm_long = _i(latest.get("m_money_positions_long_all"))
    mm_short = _i(latest.get("m_money_positions_short_all"))
    mm_net = mm_long - mm_short

    prev_net = None
    if len(rows) > 1:
        prev_net = _i(rows[1].get("m_money_positions_long_all")) - _i(rows[1].get("m_money_positions_short_all"))

    # history ascending by date
    history = [
        CftcPoint(
            date=(r.get("report_date_as_yyyy_mm_dd") or "")[:10],
            value=_i(r.get("m_money_positions_long_all")) - _i(r.get("m_money_positions_short_all")),
        )
        for r in reversed(rows)
    ]

    return CftcContract(
        id=key,
        name=label,
        code=code,
        report_date=(latest.get("report_date_as_yyyy_mm_dd") or "")[:10],
        open_interest=_i(latest.get("open_interest_all")),
        mm_long=mm_long,
        mm_short=mm_short,
        mm_net=mm_net,
        mm_net_change=mm_net - prev_net if prev_net is not None else 0,
        pm_long=_i(latest.get("prod_merc_positions_long")),
        pm_short=_i(latest.get("prod_merc_positions_short")),
        swap_long=_i(latest.get("swap_positions_long_all")),
        swap_short=_i(latest.get("swap__positions_short_all")),
        other_long=_i(latest.get("other_rept_positions_long")),
        other_short=_i(latest.get("other_rept_positions_short")),
        net_history=history,
    )


async def fetch_positioning(weeks: int = 52) -> list[CftcContract]:
    async with httpx.AsyncClient(base_url=settings.cftc_base_url, timeout=settings.request_timeout) as client:
        contracts = await asyncio.gather(
            *(_fetch_contract(client, k, code, label, weeks) for k, (code, label) in CONTRACTS.items())
        )
    return list(contracts)
