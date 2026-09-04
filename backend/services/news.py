"""FinancialJuice news — free public RSS, filtered to energy + locally tagged.

No paid API and no scraping: we read the official RSS feed
(https://www.financialjuice.com/feed.ashx?xy=rss), keep only energy-relevant
headlines, and score sentiment with FinBERT (ProsusAI/finbert, local CPU
inference). Category/importance and the theme tags are derived from a small
finance-tuned keyword lexicon. If FinBERT can't load, scoring falls back to the
offline lexicon, so the feed always works once fetched.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from xml.etree import ElementTree as ET

import httpx

from config import settings
from models import NewsItem
from .sentiment import event_key, score_article
from .sentiment_finbert import available as finbert_available, score_batch as finbert_score_batch

# Persistent scored-news memory (queue). Keyed by event_key; survives restarts.
# Doubles as the offline feed and avoids re-scoring already-seen headlines.
_STORE_FILE = Path(__file__).resolve().parents[1] / ".news_store.json"


def _load_store() -> dict[str, dict]:
    if _STORE_FILE.exists():
        try:
            return json.loads(_STORE_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
    return {}


def _save_store(store: dict[str, dict]) -> None:
    try:
        _STORE_FILE.write_text(json.dumps(store), encoding="utf-8")
    except OSError:
        pass

# --- Energy relevance: keep a headline only if it mentions one of these ---
ENERGY_KEYWORDS = [
    "oil", "crude", "brent", "wti", "opec", "petroleum", "barrel", "bbl",
    "refinery", "refining", "refiner", "gasoline", "rbob", "diesel", "distillate",
    "gasoil", "jet fuel", "heating oil", "naphtha", "propane", "fuel oil",
    "lng", "natural gas", "nat gas", "henry hub", "shale", "rig", "drilling",
    "pipeline", "aramco", "energy", "eia", "iea", "inventories", "barrels",
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


def _basic(title: str, summary: str, day_bucket: str) -> tuple[str, list[str], str]:
    """Deterministic, score-free fields: (category, tags, event_key)."""
    text = f"{title} {summary}".lower()
    if _has(text, PRODUCTS_KW):
        category = "Products"
    elif _has(text, CRUDE_KW):
        category = "Crude"
    else:
        category = "Macro"
    matched = _has(text, ENERGY_KEYWORDS)
    tags = [t.upper() if len(t) <= 4 else t.title() for t in matched[:3]]
    return category, tags, event_key(title, day_bucket)


def _apply_score(item: NewsItem, res) -> None:
    """Write a SentimentResult onto an item + derive legacy sentiment/importance."""
    item.impact = res.impact
    item.confidence = res.confidence
    item.theme_primary = res.theme_primary
    item.themes_secondary = res.themes_secondary
    item.product_divergence = res.product_divergence
    item.kind = res.kind
    item.sentiment = "bullish" if res.impact >= 0.15 else "bearish" if res.impact <= -0.15 else "neutral"
    text = f"{item.headline} {item.summary}".lower()
    if abs(res.impact) >= 0.5 or _has(text, HIGH_KW):
        item.importance = "high"
    elif abs(res.impact) >= 0.2:
        item.importance = "medium"
    else:
        item.importance = "low"


async def _score_items(items: list[NewsItem]) -> None:
    """Score new items in place — FinBERT (one batch), offline lexicon fallback."""
    if not items:
        return
    results = None
    if finbert_available():
        try:
            results = await finbert_score_batch([(i.headline, i.summary) for i in items])
        except Exception:  # noqa: BLE001 — any FinBERT failure → offline lexicon
            results = None
    if results is None:
        results = [score_article(i.headline, i.summary) for i in items]
    for it, res in zip(items, results):
        _apply_score(it, res)


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

        day_bucket = (datetime.fromtimestamp(published_at, timezone.utc).strftime("%Y-%m-%d")
                      if published_at else "")
        category, tags, ekey = _basic(title, summary, day_bucket)
        items.append(NewsItem(
            id=hashlib.sha1(guid.encode("utf-8")).hexdigest()[:12],
            headline=title,
            summary=summary,
            source=source,
            timestamp=timestamp,
            published_at=published_at,
            category=category,
            tags=tags,
            link=link,
            event_key=ekey,
        ))  # sentiment fields filled later (only for NEW headlines)
        if len(items) >= limit:
            break
    return items


async def _fetch_raw(limit: int) -> list[NewsItem]:
    """Fetch + merge both feeds (score-free). Raises if every feed fails."""
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
    if not merged:
        raise RuntimeError("all news feeds failed")
    return merged


async def fetch_news(limit: int = 40) -> tuple[list[NewsItem], bool]:
    """Memory-backed news feed.

    Pulls both RSS feeds, scores ONLY headlines not already in the persistent
    store (one Gemini batch call, lexicon fallback), then keeps the N most recent
    (queue eviction) and persists. If every feed fails, serves the stored feed
    flagged stale. Returns (items, stale).
    """
    store = _load_store()
    stale = False
    try:
        raw = await _fetch_raw(settings.news_store_size)
    except Exception:  # noqa: BLE001 — offline: fall back to the stored feed
        raw = []
        stale = True

    new = [it for it in raw if it.event_key and it.event_key not in store]
    await _score_items(new)
    for it in new:
        store[it.event_key] = it.model_dump()

    # Refresh volatile fields for already-stored items still in the feed (keep their sentiment).
    new_keys = {it.event_key for it in new}
    for it in raw:
        if it.event_key in store and it.event_key not in new_keys:
            store[it.event_key].update(
                published_at=it.published_at, timestamp=it.timestamp, link=it.link or store[it.event_key].get("link", "")
            )

    # Queue eviction: keep the N most recent by publish time.
    keep = sorted(store.values(), key=lambda x: x.get("published_at") or 0, reverse=True)[: settings.news_store_size]
    _save_store({e["event_key"]: e for e in keep})

    feed = [NewsItem.model_validate(e) for e in keep]
    return feed[:limit], stale
