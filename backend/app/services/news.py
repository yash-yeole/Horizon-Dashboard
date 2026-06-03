"""FinancialJuice news — free public RSS, filtered to energy + locally tagged.

No paid API and no scraping: we read the official RSS feed
(https://www.financialjuice.com/feed.ashx?xy=rss), keep only energy-relevant
headlines, and assign sentiment/category/importance with a small finance-tuned
keyword lexicon. All deterministic and offline once the feed is fetched.
"""
from __future__ import annotations

import asyncio
import hashlib
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree as ET

import httpx

from ..config import settings
from ..models import NewsItem

# --- Energy relevance: keep a headline only if it mentions one of these ---
ENERGY_KEYWORDS = [
    "oil", "crude", "brent", "wti", "opec", "petroleum", "barrel", "bbl",
    "refinery", "refining", "refiner", "gasoline", "rbob", "diesel", "distillate",
    "gasoil", "jet fuel", "heating oil", "naphtha", "propane", "fuel oil",
    "lng", "natural gas", "nat gas", "henry hub", "shale", "rig", "drilling",
    "pipeline", "aramco", "energy", "eia", "iea", "inventories", "barrels",
]

# --- Sentiment lexicon (price-direction for the energy complex) ---
BULLISH = [
    "cut", "cuts", "output cut", "supply cut", "draw", "drawdown", "shortage",
    "tighten", "tightening", "outage", "disruption", "halt", "shutdown",
    "force majeure", "sanction", "sanctions", "embargo", "attack", "strike",
    "war", "conflict", "escalation", "blockade", "unplanned", "deeper cuts",
    "strong demand", "robust demand", "record demand", "beats",
]
BEARISH = [
    "build", "builds", "buildup", "glut", "oversupply", "surplus", "oversupplied",
    "ramp up", "raise output", "increase output", "boost output", "higher output",
    "resume", "resumes", "restart", "return", "returns", "ceasefire", "truce",
    "deal", "agreement", "weak demand", "soft demand", "demand concerns",
    "slowdown", "recession", "downgrade", "lower demand", "cut forecast",
]

# --- Category routing ---
PRODUCTS_KW = ["gasoline", "rbob", "diesel", "distillate", "gasoil", "jet fuel",
               "heating oil", "naphtha", "propane", "fuel oil", "refinery", "refining"]
CRUDE_KW = ["crude", "brent", "wti", "opec", "barrel", "shale", "rig", "pipeline", "aramco"]

# --- Importance ---
HIGH_KW = ["breaking", "urgent", "opec", "war", "sanction", "force majeure",
           "attack", "halt", "outage", "escalation"]

_WORD = re.compile(r"[a-z0-9+]+")


def _has(text: str, phrases: list[str]) -> list[str]:
    return [p for p in phrases if p in text]


def _classify(title: str) -> tuple[str, str, str, list[str]]:
    """Return (sentiment, category, importance, tags) for a lowercased title."""
    bull = len(_has(title, BULLISH))
    bear = len(_has(title, BEARISH))
    sentiment = "bullish" if bull > bear else "bearish" if bear > bull else "neutral"

    if _has(title, PRODUCTS_KW):
        category = "Products"
    elif _has(title, CRUDE_KW):
        category = "Crude"
    else:
        category = "Macro"

    importance = "high" if _has(title, HIGH_KW) else "medium"

    matched = _has(title, ENERGY_KEYWORDS)
    tags = [t.upper() if len(t) <= 4 else t.title() for t in matched[:3]]
    return sentiment, category, importance, tags


def _is_energy(text: str) -> bool:
    return any(k in text for k in ENERGY_KEYWORDS)


def _rel_time(dt: datetime) -> str:
    secs = (datetime.now(timezone.utc) - dt).total_seconds()
    if secs < 60:
        return "just now"
    if secs < 3600:
        return f"{int(secs // 60)}m ago"
    if secs < 86400:
        return f"{int(secs // 3600)}h ago"
    return f"{int(secs // 86400)}d ago"


def _clean(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", text)).strip()


def _truncate(text: str, n: int = 280) -> str:
    return text if len(text) <= n else text[: n - 1].rsplit(" ", 1)[0] + "…"


# (source name, feed url, strip 'FinancialJuice:' title prefix)
def _sources() -> list[tuple[str, str, bool]]:
    return [
        ("FinancialJuice", settings.news_feed_url, True),
        ("OilPrice", settings.oilprice_feed_url, False),
    ]


def _parse(xml_bytes: bytes, source: str, strip_prefix: bool, limit: int) -> list[NewsItem]:
    root = ET.fromstring(xml_bytes)
    items: list[NewsItem] = []
    for el in root.iter("item"):
        title = _clean(el.findtext("title"))
        if strip_prefix:
            title = re.sub(r"^\s*financialjuice\s*:\s*", "", title, flags=re.I)
        if not title:
            continue

        summary = _truncate(_clean(el.findtext("description")))
        text = f"{title} {summary}".lower()
        if not _is_energy(text):  # keep only energy-relevant stories
            continue

        link = (el.findtext("link") or "").strip()
        guid = (el.findtext("guid") or link or title).strip()

        published_at: int | None = None
        timestamp = ""
        raw_date = el.findtext("pubDate")
        if raw_date:
            try:
                dt = parsedate_to_datetime(raw_date)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                published_at = int(dt.timestamp())
                timestamp = _rel_time(dt)
            except (TypeError, ValueError):
                pass

        sentiment, category, importance, tags = _classify(text)
        items.append(NewsItem(
            id=hashlib.sha1(guid.encode("utf-8")).hexdigest()[:12],
            headline=title,
            summary=summary,
            source=source,
            timestamp=timestamp,
            published_at=published_at,
            category=category,
            sentiment=sentiment,
            importance=importance,
            tags=tags,
            link=link,
        ))
        if len(items) >= limit:
            break
    return items


async def fetch_news(limit: int = 40) -> list[NewsItem]:
    """Fetch + merge all energy news feeds. Resilient: if one feed fails, the
    others still return (e.g. FinancialJuice rate-limits → OilPrice still shows)."""
    headers = {"User-Agent": settings.yahoo_user_agent}
    async with httpx.AsyncClient(timeout=settings.request_timeout, follow_redirects=True) as client:
        async def one(source: str, url: str, strip_prefix: bool) -> list[NewsItem]:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            return _parse(resp.content, source, strip_prefix, limit)

        results = await asyncio.gather(*(one(s, u, p) for s, u, p in _sources()), return_exceptions=True)

    merged: list[NewsItem] = []
    seen: set[str] = set()
    for r in results:
        if isinstance(r, Exception):
            continue
        for item in r:
            if item.id in seen:
                continue
            seen.add(item.id)
            merged.append(item)

    merged.sort(key=lambda x: x.published_at or 0, reverse=True)
    return merged[:limit]
