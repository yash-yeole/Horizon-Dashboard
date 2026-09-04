"""Inventory-release impact assessment (WTI).

Productionizes the research framework (research/inventory-impact modules): forecast
the upcoming weekly EIA crude release and assess its likely WTI impact.

LIVE per request:
  - next release date (calendar),
  - the Reuters CONSENSUS + previous (ForexFactory weekly JSON, keyless),
  - OUR forecast of the number (inventory_forecast service — the lagged supply/
    demand balance model), so we can show our own expected print and surprise,
  - the news theme tally + headlines (news service).

SNAPSHOT (versioned, from the validated research):
  - WTI, not Brent: EIA measures *US* crude, so the US barrel responds; Brent
    carries global/geopolitical drivers that aren't inventory-attributable.
  - the WTI inventory beta + the top-3 daily driver ranking (DXY > S&P > news),
  - the PRODUCT effects: RBOB/HO react to their *own* stock surprise (the cracks
    are the most inventory-sensitive spreads), crude itself barely moves WTI,
  - the framework blurb.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timezone

import httpx

from config import settings
from models import (
    DriverFactor,
    ForecastDriver,
    InventoryForecast,
    NewsTheme,
    ProductEffect,
    ReleaseImpactResponse,
    ReleaseScenario,
)
from . import inventory_forecast
from . import news as news_service
from .calendar import generate_events

_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
_FF = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"

# ── versioned research snapshot ──────────────────────────────────────
# WTI inventory beta = EIA-consensus surprise on WTI release-day (small, sub-
# significant: -0.03 over 7yr / -0.13 in the 2026 war sub-sample). Top factors =
# standardized betas of the daily war-regime WTI model.
_INVENTORY_BETA = 0.13
_TOP_FACTORS = [
    ("US dollar (DXY)", 0.33, 0.013),
    ("Equities / risk (S&P 500)", -0.25, 0.159),
    ("News / geopolitical sentiment", -0.23, 0.003),
]
_FRAMEWORK = (
    "Two stages. (1) Predict the number: the lagged supply/demand balance "
    "(production + imports - exports - refinery runs) + seasonality + recent "
    "momentum (validated OOS R2~0.11, beat the consensus on the prior print). "
    "(2) Predict the reaction: surprise = our number vs the Reuters consensus, "
    "mapped through a regime-conditional WTI model. Inventories have been a "
    "secondary, mostly-insignificant WTI driver since 2019 (the dollar, risk and "
    "geopolitical news dominate), so the call is NEUTRAL unless the surprise is "
    "extreme -- and any genuine signal shows up first in the product cracks."
)
# products: RBOB/HO react to their OWN stock surprise; crude->product spillover ~0
_PRODUCT_EFFECTS = [
    ("RBOB (gasoline)", "gasoline stock surprise", -0.136, 0.004, "RBOB-WTI crack",
     "Most inventory-sensitive product; the 2026 driving-season regime amplifies it "
     "(war-regime beta -0.98). A bigger-than-expected gasoline BUILD compresses the "
     "RBOB-WTI crack; a draw widens it."),
    ("Heating oil (distillate)", "distillate stock surprise", -0.147, 0.05, "HO-WTI crack",
     "Distillate surprise is the most significant crack driver historically. A bigger-"
     "than-expected distillate BUILD compresses the HO-WTI crack."),
]
_THEMES = {
    "Crude / geopolitics": r"crude|hormuz|iran|opec|supply|spr|inventor|tanker|barrel|sanction",
    "Gasoline": r"gasoline|pump|rbob",
    "Distillate / diesel": r"diesel|distillate|heating|gasoil",
    "Demand / macro": r"demand|recession|growth|\brate\b|economy|dollar",
}
_THEME_SPREAD = {
    "Crude / geopolitics": "WTI flat + WTI-Brent (US-crude / global-supply)",
    "Gasoline": "RBOB-WTI gasoline crack",
    "Distillate / diesel": "HO-WTI distillate crack",
    "Demand / macro": "WTI flat price (whole complex)",
}
_DEFAULT_SPREAD = "WTI flat + RBOB-WTI / HO-WTI cracks"


def _next_eia_release() -> tuple[str, str, bool]:
    for e in generate_events(days=21):
        if e.category == "EIA" and "Petroleum" in e.title:
            return e.date, e.time_et, e.is_delayed
    return "", "10:30", False


def _scenarios(consensus: float | None, ours: float | None) -> list[ReleaseScenario]:
    """Surprise magnitudes vs the published consensus (the anchor the market trades).

    We deliberately do NOT publish a precise %-move: the WTI inventory beta is
    small, sub-significant and sign-unstable, so a point estimate would overstate
    confidence. The lean = direction of the surprise vs consensus.
    """
    out: list[ReleaseScenario] = []
    for actual, label in [(-9.0, "big draw"), (-7.0, "solid draw"), (-5.0, "moderate draw"),
                          (-3.0, "small draw"), (1.0, "build")]:
        s_cons = round(actual - consensus, 2) if consensus is not None else 0.0
        s_ours = round(actual - ours, 2) if ours is not None else 0.0
        lean = "bullish" if s_cons <= -1.0 else "bearish" if s_cons >= 1.0 else "neutral"
        out.append(ReleaseScenario(
            actual=actual, surprise_vs_consensus=s_cons, surprise_vs_ours=s_ours,
            lean=lean, label=label,
        ))
    return out


async def _ff_crude(client: httpx.AsyncClient) -> tuple[float | None, float | None]:
    """ForexFactory weekly JSON → (consensus, previous) for EIA crude. Reliable, keyless."""
    def _num(x) -> float | None:
        x = str(x).replace("M", "").strip()
        try:
            return float(x)
        except (TypeError, ValueError):
            return None
    try:
        ff = (await client.get(_FF, headers=_UA, timeout=settings.request_timeout)).json()
        for e in ff:
            if "Crude Oil Inventories" in e.get("title", ""):
                return _num(e.get("forecast")), _num(e.get("previous"))
    except Exception:  # noqa: BLE001
        pass
    return None, None


def _build_forecast(fc: dict | None) -> InventoryForecast | None:
    if not fc:
        return None
    note = (f"Built from the {fc['as_of_week']} report. Driven by last week's "
            f"supply/demand balance ({fc['bal_l1']:+.1f}M) and recent momentum.")
    return InventoryForecast(
        target_week_ending=fc["target_week_ending"], as_of_week=fc["as_of_week"],
        predicted_change=fc["predicted_change"], sd=fc["sd"], r2=fc["r2"], oos_r2=fc["oos_r2"],
        drivers=[
            ForecastDriver(label="Supply/demand balance (last wk)", value=fc["bal_l1"]),
            ForecastDriver(label="SPR change (last wk)", value=fc["dspr_l1"]),
            ForecastDriver(label="Stock change (last wk)", value=fc["ar1"]),
            ForecastDriver(label="Stock change (2 wks ago)", value=fc["ar2"]),
        ],
        note=note,
    )


async def assess() -> ReleaseImpactResponse:
    rel_date, time_et, delayed = _next_eia_release()
    days_until = (date.fromisoformat(rel_date) - date.today()).days if rel_date else 0

    async with httpx.AsyncClient(follow_redirects=True) as client:
        consensus, previous = await _ff_crude(client)

    fc = await inventory_forecast.forecast()
    our_num = fc["predicted_change"] if fc else None
    our_surprise = (round(our_num - consensus, 2)
                    if (our_num is not None and consensus is not None) else None)

    # reaction lean from our expected surprise (net call stays NEUTRAL — print is secondary)
    if our_surprise is None:
        lean = "neutral"
    elif our_surprise <= -1.0:
        lean = "bullish"
    elif our_surprise >= 1.0:
        lean = "bearish"
    else:
        lean = "neutral"

    # news themes + headlines + topical spread
    themes: list[NewsTheme] = []
    headlines: list[str] = []
    spread_focus = _DEFAULT_SPREAD
    try:
        items, _ = await news_service.fetch_news(30)
        titles = [getattr(i, "headline", "") for i in items][:25]
        headlines = [t for t in titles if t][:6]
        tally = {k: sum(1 for t in titles if re.search(v, t, re.I)) for k, v in _THEMES.items()}
        themes = [NewsTheme(theme=k, count=c) for k, c in sorted(tally.items(), key=lambda x: -x[1])]
        if themes and themes[0].count:
            spread_focus = _THEME_SPREAD.get(themes[0].theme, spread_focus)
    except Exception:  # noqa: BLE001
        pass

    # narrative
    if our_num is not None and consensus is not None:
        headline = (f"Our model: {our_num:+.1f}M vs {consensus:+.1f}M consensus "
                    f"({lean} surprise) — print is a secondary driver, call NEUTRAL")
        reasoning = (
            f"Our model expects {our_num:+.1f}M against the {consensus:+.1f}M consensus "
            f"(surprise {our_surprise:+.1f}M → {lean}). In the current war regime the EIA "
            "print is a secondary WTI driver — the dollar, risk and geopolitical news "
            "dominate — so the net call is NEUTRAL. Any genuine signal shows first in the "
            "RBOB-WTI and HO-WTI product cracks, not WTI flat price."
        )
    else:
        headline = "Inventory print is a secondary WTI driver — call is NEUTRAL"
        reasoning = ("Consensus/forecast unavailable upstream; in this regime the print is a "
                     "secondary driver dominated by the dollar and geopolitical news.")

    factors = [DriverFactor(name=n, std_beta=b, p_value=p, significant=p < 0.05)
               for n, b, p in _TOP_FACTORS]
    product_effects = [
        ProductEffect(product=pr, channel=ch, beta=b, p_value=p, significant=p < 0.05,
                      spread=sp, lean="neutral", note=note)
        for pr, ch, b, p, sp, note in _PRODUCT_EFFECTS
    ]

    return ReleaseImpactResponse(
        series="crude", instrument="WTI", next_release_date=rel_date, time_et=time_et,
        days_until=days_until, is_delayed=delayed, consensus=consensus, previous=previous,
        our_forecast=_build_forecast(fc), our_surprise_vs_consensus=our_surprise,
        bias="neutral", confidence="low", headline=headline, reasoning=reasoning,
        scenarios=_scenarios(consensus, our_num), inventory_beta=_INVENTORY_BETA,
        top_factors=factors, spread_focus=spread_focus, product_effects=product_effects,
        news_themes=themes, headlines=headlines, framework=_FRAMEWORK,
        as_of=datetime.now(timezone.utc).timestamp(),
        stale=(consensus is None and our_num is None),
    )
