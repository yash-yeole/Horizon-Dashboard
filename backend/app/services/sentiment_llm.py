"""LLM sentiment scorer (Groq or Google Gemini, free tiers).

Scores a *batch* of headlines in a single request so usage stays trivial (one
call per news-fetch cycle, only for headlines not already in the memory store).
Implements the same SentimentResult contract as the lexicon, so it's a drop-in
swap. Any failure (no key, network, bad JSON) raises and the caller falls back
to the offline lexicon — the app never hard-depends on the LLM.

Provider is auto-selected: Groq if HORIZON_GROQ_API_KEY is set, else Gemini.
"""
from __future__ import annotations

import json
import re

import httpx

from ..config import settings
from .sentiment import SentimentResult

THEMES = ["Supply", "Demand", "Inventory", "Freight", "Geopolitics", "Refining", "Macro", "Weather"]

_PROMPT = """You are an oil-market analyst. For each numbered headline, judge its NET impact on CRUDE OIL PRICE (not general tone). A refinery outage is bearish crude (less crude demand) but bullish products. Geopolitical escalation / supply loss = bullish; demand destruction / oversupply / ceasefire = bearish. Meta/opinion or non-market headlines = neutral, low relevance.

Return ONLY a JSON object: {"results": [one object per headline, in order]}, each object:
{"impact": number -1..1 (sign=direction, magnitude=size; Hormuz closure ~+0.95, minor item ~+0.2), "confidence": number 0..1, "theme": one of %s, "kind": "event"|"forecast"|"opinion", "product_divergence": boolean (true if it's really a products/refining story), "drivers": [short phrases]}

Headlines:
%s

JSON object only, no prose.""" % (THEMES, "%s")


def _coerce(obj: dict) -> SentimentResult:
    impact = max(-1.0, min(1.0, float(obj.get("impact", 0) or 0)))
    conf = max(0.0, min(1.0, float(obj.get("confidence", 0.5) or 0.5)))
    theme = obj.get("theme") if obj.get("theme") in THEMES else "Macro"
    kind = obj.get("kind") if obj.get("kind") in ("event", "forecast", "opinion") else "event"
    drivers = obj.get("drivers") or []
    if not isinstance(drivers, list):
        drivers = []
    return SentimentResult(
        impact=round(impact, 3),
        confidence=round(conf, 2),
        theme_primary=theme,
        themes_secondary=[],
        product_divergence=bool(obj.get("product_divergence", False)),
        kind=kind,
        drivers=[str(d) for d in drivers[:4]],
    )


def _parse_results(text: str) -> list:
    """Accept {"results":[...]}, a bare [...] array, or JSON embedded in prose."""
    try:
        obj = json.loads(text)
        if isinstance(obj, dict) and isinstance(obj.get("results"), list):
            return obj["results"]
        if isinstance(obj, list):
            return obj
    except ValueError:
        pass
    m = re.search(r"\[.*\]", text, re.DOTALL)
    if not m:
        raise ValueError("no JSON results in LLM response")
    return json.loads(m.group(0))


async def _call_groq(prompt: str) -> str:
    body = {
        "model": settings.groq_model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "response_format": {"type": "json_object"},
    }
    headers = {"Authorization": f"Bearer {settings.groq_api_key}"}
    async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
        resp = await client.post(f"{settings.groq_base_url}/chat/completions", headers=headers, json=body)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


async def _call_gemini(prompt: str) -> str:
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.0, "responseMimeType": "application/json"},
    }
    url = f"{settings.gemini_base_url}/models/{settings.gemini_model}:generateContent"
    async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
        resp = await client.post(url, params={"key": settings.gemini_api_key}, json=body)
        resp.raise_for_status()
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"]


def active_provider() -> str | None:
    if settings.groq_api_key:
        return "groq"
    if settings.gemini_api_key:
        return "gemini"
    return None


async def score_batch(headlines: list[str]) -> list[SentimentResult]:
    """Score all headlines in one LLM call. Raises on any failure."""
    provider = active_provider()
    if provider is None:
        raise RuntimeError("no LLM api key set")
    if not headlines:
        return []

    numbered = "\n".join(f"{i + 1}. {h}" for i, h in enumerate(headlines))
    prompt = _PROMPT % numbered
    text = await (_call_groq(prompt) if provider == "groq" else _call_gemini(prompt))

    arr = _parse_results(text)
    if len(arr) != len(headlines):
        raise ValueError(f"LLM returned {len(arr)} scores for {len(headlines)} headlines")
    return [_coerce(o) for o in arr]
