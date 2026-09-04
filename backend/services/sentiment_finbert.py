"""FinBERT sentiment scorer (local, ProsusAI/finbert via transformers).

This is the live *polarity* engine for news, replacing the in-house lexicon's
bullish/bearish scoring. FinBERT classifies each headline into
positive / negative / neutral, which we map onto the shared SentimentResult:

    impact     = P(positive) − P(negative)   # -1..+1, sign = direction
    confidence = P(positive) + P(negative)   # = 1 − P(neutral); directional mass

The lexicon is retained ONLY to supply categorization metadata that FinBERT
can't produce — theme, themes_secondary, product_divergence, kind, drivers —
via ``sentiment.classify_metadata``, and as the offline fallback if the model
fails to load (handled by the caller in ``news.py``).

Note on semantics: FinBERT scores generic financial *tone*, not crude-price
*direction*. We keep the lexicon's ``product_divergence`` routing so that
products/refining stories are still kept out of the crude gauge regardless of
the tone FinBERT assigns them.

The model loads lazily on first use and runs on CPU in a worker thread, so app
startup and the event loop stay responsive. Any failure raises and the caller
falls back to the offline lexicon — the app never hard-depends on FinBERT.
"""
from __future__ import annotations

import asyncio
import threading

from config import settings
from .sentiment import SentimentResult, classify_metadata

_pipeline = None
_pipeline_lock = threading.Lock()
_load_failed = False


def available() -> bool:
    """True if FinBERT scoring is enabled and hasn't already failed to load."""
    return settings.finbert_enabled and not _load_failed


def _get_pipeline():
    """Lazily build (and cache) the text-classification pipeline. Thread-safe."""
    global _pipeline, _load_failed
    if _pipeline is not None:
        return _pipeline
    with _pipeline_lock:
        if _pipeline is None:
            try:
                from transformers import pipeline  # heavy import, deferred to first use
                _pipeline = pipeline(
                    "text-classification",
                    model=settings.finbert_model,
                    top_k=None,  # return scores for all labels (pos/neg/neutral)
                )
            except Exception:
                _load_failed = True  # don't keep retrying a broken/missing model
                raise
    return _pipeline


def _to_result(scores: list[dict], title: str, summary: str) -> SentimentResult:
    probs = {str(d.get("label", "")).lower(): float(d.get("score", 0.0)) for d in scores}
    pos = probs.get("positive", 0.0)
    neg = probs.get("negative", 0.0)
    impact = round(pos - neg, 3)                  # -1..+1; sign = direction, |val| = size
    confidence = round(min(1.0, pos + neg), 2)    # directional mass (1 − neutral)
    theme_primary, themes_secondary, product_divergence, kind, drivers = \
        classify_metadata(title, summary)
    return SentimentResult(
        impact=impact,
        confidence=confidence,
        theme_primary=theme_primary,
        themes_secondary=themes_secondary,
        product_divergence=product_divergence,
        kind=kind,
        drivers=drivers,
    )


def _run(articles: list[tuple[str, str]]) -> list[SentimentResult]:
    pipe = _get_pipeline()
    texts = [f"{t}. {s}".strip()[:512] for t, s in articles]
    raw = pipe(texts, batch_size=16, truncation=True, max_length=256)
    results: list[SentimentResult] = []
    for (title, summary), scores in zip(articles, raw):
        if isinstance(scores, dict):  # single-label form, normalize to a list
            scores = [scores]
        results.append(_to_result(scores, title, summary))
    return results


async def score_batch(articles: list[tuple[str, str]]) -> list[SentimentResult]:
    """Score (title, summary) pairs with FinBERT. Raises on any failure so the
    caller can fall back to the offline lexicon."""
    if not settings.finbert_enabled:
        raise RuntimeError("finbert disabled")
    if not articles:
        return []
    return await asyncio.to_thread(_run, articles)
