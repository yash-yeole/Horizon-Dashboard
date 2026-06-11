"""Directional, oil-price-impact news sentiment (Layer 1: lexicon).

We score *impact on crude oil price*, NOT generic positive/negative tone.
A "refinery fire" reads negative in tone but is bearish crude (less crude demand)
and bullish products — so the engine measures price direction, with a
`product_divergence` flag to route products/cracks stories out of the crude gauge.

The public surface is intentionally tiny so the scorer can be swapped for an
LLM later without touching `news.py`, the models, or the frontend:
    score_article(title, summary, source) -> SentimentResult
    event_key(title, day_bucket) -> str
Nothing else (no lexicon constants) should be imported from this module.
"""
from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class SentimentResult:
    impact: float                                    # -1..+1 (for crude)
    confidence: float                                # 0..1
    theme_primary: str
    themes_secondary: list[str] = field(default_factory=list)
    product_divergence: bool = False
    kind: str = "event"                              # event | forecast | opinion
    drivers: list[str] = field(default_factory=list)


class Scorer(Protocol):
    def score(self, title: str, summary: str, source: str) -> SentimentResult: ...


# (phrases, signed weight ~[-0.9, 0.9], theme, product) — `+` bullish crude, `-` bearish.
LEXICON: list[tuple[list[str], float, str, bool]] = [
    # ---------- SUPPLY (bullish = less supply) ----------
    (["opec+ cut", "opec cut", "output cut", "production cut", "supply cut",
      "deeper cuts", "deeper cut", "extend cuts", "extend cut", "voluntary cut",
      "curb output", "cut output", "lower output", "reduce output", "slash output",
      "cut production", "reduce production"], 0.75, "Supply", False),
    (["force majeure", "declare force majeure"], 0.8, "Supply", False),
    (["outage", "unplanned outage", "shut in", "shut-in", "shutdown", "halt production",
      "production halt", "supply disruption", "disruption", "pipeline outage",
      "field outage", "export halt", "export ban", "export suspension",
      "loadings halted", "loadings suspended"], 0.6, "Supply", False),
    (["blockade", "supply shortage", "shortage", "tight supply", "supply tightens",
      "tighten", "tightening"], 0.55, "Supply", False),
    (["production increase", "raise output", "increase output", "boost output",
      "higher output", "hike output", "ramp up", "ramp-up", "restart", "resume production",
      "production resumes", "return to market", "restore output", "add barrels",
      "record production", "rising output", "more barrels", "unwind cuts", "ease cuts",
      "quota increase", "raise quota", "lift output"], -0.65, "Supply", False),
    (["oversupply", "glut", "supply glut", "surplus", "oversupplied",
      "spare capacity", "ample supply", "well supplied"], -0.6, "Supply", False),

    # ---------- GEOPOLITICS (risk premium; mostly bullish crude) ----------
    (["war", "conflict", "escalation", "escalate", "invasion", "military strike",
      "drone attack", "missile attack", "missile strike", "attack on", "strike on",
      "tanker seized", "seize tanker", "hijack", "tanker hijacked"], 0.7, "Geopolitics", False),
    (["sanction", "sanctions", "embargo", "price cap", "secondary sanctions"], 0.6, "Geopolitics", False),
    (["tensions", "geopolitical", "geopolitical risk", "hormuz", "strait of hormuz",
      "red sea", "houthi", "houthis", "bab el-mandeb", "suez"], 0.5, "Geopolitics", False),
    (["ceasefire", "truce", "peace deal", "peace talks", "de-escalation", "de-escalate",
      "sanctions relief", "lift sanctions", "ease sanctions", "sanctions waiver",
      "waiver", "diplomatic breakthrough"], -0.6, "Geopolitics", False),

    # ---------- DEMAND ----------
    (["strong demand", "robust demand", "record demand", "demand surge", "surging demand",
      "rising demand", "demand growth", "rebound in demand", "demand rebound",
      "stronger consumption", "peak driving", "demand beats"], 0.55, "Demand", False),
    (["weak demand", "soft demand", "demand concerns", "demand destruction",
      "falling demand", "lower demand", "slowing demand", "demand slump", "demand fears",
      "downgrade demand", "cut demand forecast", "tepid demand"], -0.6, "Demand", False),
    (["recession", "economic slowdown", "slowdown", "contraction", "hard landing",
      "lockdown", "weak economy", "stalling growth"], -0.5, "Macro", False),

    # ---------- INVENTORY (draw = bullish, build = bearish) ----------
    (["inventory draw", "stock draw", "crude draw", "stocks fall", "stocks drop",
      "inventories fall", "inventories drop", "surprise draw", "bigger draw",
      "larger draw", "big draw", "drawdown"], 0.55, "Inventory", False),
    (["inventory build", "stock build", "crude build", "stocks rise", "stocks jump",
      "inventories rise", "inventories climb", "surprise build", "bigger build",
      "larger build", "big build", "stockpile rise", "stockpiles rise"], -0.55, "Inventory", False),

    # ---------- REFINING (PRODUCT-DIVERGENT) ----------
    (["refinery outage", "refinery fire", "refinery shutdown", "refinery strike",
      "refinery halt", "run cuts", "lower runs", "throughput cut", "reduce runs",
      "refinery unplanned"], 0.45, "Refining", True),
    (["refinery maintenance", "refinery turnaround", "turnaround", "planned maintenance",
      "refining margin", "crack spread", "refinery utilization", "utilization rate",
      "refinery runs rise", "higher runs"], -0.25, "Refining", True),

    # ---------- FREIGHT ----------
    (["freight rates surge", "tanker rates surge", "vlcc rates rise", "shipping costs rise",
      "rerouting", "longer voyages", "ton-mile", "port congestion", "chokepoint congestion",
      "tanker rates jump"], 0.4, "Freight", False),
    (["freight rates fall", "tanker rates fall", "rates drop", "ample tonnage"], -0.3, "Freight", False),

    # ---------- MACRO (dollar / rates) ----------
    (["weaker dollar", "dollar falls", "dollar drops", "rate cut", "fed cuts", "fed cut",
      "dovish", "stimulus", "rate-cut"], 0.4, "Macro", False),
    (["stronger dollar", "dollar rises", "dollar jumps", "rate hike", "fed hikes", "fed hike",
      "hawkish", "tightening policy", "higher for longer"], -0.4, "Macro", False),

    # ---------- WEATHER ----------
    (["hurricane", "tropical storm", "cold snap", "polar vortex", "deep freeze", "freeze-off",
      "arctic blast", "evacuate platforms", "gulf storm", "storm shut"], 0.5, "Weather", False),
    (["mild weather", "warm winter", "milder temperatures", "warmer-than-normal"], -0.3, "Weather", False),
]

NEGATORS = ["no ", "not ", "fails to", "failed to", "won't", "will not", "without",
            "denies", "denied", "rules out", "ruled out", "delay", "delays", "delayed",
            "postpone", "postponed", "scrap", "scrapped", "abandon", "abandoned",
            "unlikely to", "no plans to"]
NEG_WINDOW = 28  # chars before a matched phrase to scan for a negator

SHRINK_EXPECT = ["smaller-than-expected", "smaller than expected", "less than expected",
                 "below expectations", "below forecast", "misses", "missed", "weaker-than-expected"]
GROW_EXPECT = ["larger-than-expected", "bigger-than-expected", "more than expected",
               "above expectations", "above forecast", "beats", "beat estimates",
               "stronger-than-expected"]

FORECAST_CUES = ["forecast", "forecasts", "sees ", "expects", "expected to", "outlook",
                 "projects", "projected", "estimate", "estimates", "survey", "poll",
                 "guidance", "could ", "may ", "likely", "to reach", "to hit", "predicts"]
OPINION_CUES = ["says", "said", "view", "believes", "comment", "warns", "warning",
                "analyst", "analysts", "strategist", "goldman", "morgan stanley",
                "jpmorgan", "citi", "ubs", "barclays", "rbc", "bofa", "opinion"]


class LexiconScorer:
    def __init__(self) -> None:
        # longest phrases first so "output cut" beats "cut"
        self._lex = sorted(LEXICON, key=lambda e: -max(len(p) for p in e[0]))

    def score(self, title: str, summary: str, source: str = "") -> SentimentResult:
        text = f"{title} {summary}".lower()

        matched: list[tuple[str, float, str, bool]] = []  # (phrase, signed_weight, theme, product)
        for phrases, weight, theme, product in self._lex:
            for p in phrases:
                idx = text.find(p)
                if idx == -1:
                    continue
                w = weight
                window = text[max(0, idx - NEG_WINDOW):idx]
                if any(neg in window for neg in NEGATORS):
                    w = -w
                if theme in ("Inventory", "Demand"):
                    if any(s in text for s in SHRINK_EXPECT):
                        w = -abs(w) if weight > 0 else w  # smaller-than-expected draw => bearish
                    elif any(g in text for g in GROW_EXPECT):
                        w = w * 1.2
                matched.append((p, w, theme, product))
                break  # count each lexicon entry at most once

        if not matched:
            return SentimentResult(impact=0.0, confidence=0.2, theme_primary="Macro",
                                   themes_secondary=[], product_divergence=False,
                                   kind=self._kind(text), drivers=[])

        raw = sum(w for _, w, _, _ in matched)
        impact = math.tanh(0.9 * raw)

        matched_sorted = sorted(matched, key=lambda m: -abs(m[1]))
        theme_primary = matched_sorted[0][2]
        themes_secondary = list(dict.fromkeys(
            m[2] for m in matched_sorted[1:] if m[2] != theme_primary))
        product_divergence = any(prod for _, _, _, prod in matched)

        signs = {1 if w > 0 else -1 for _, w, _, _ in matched}
        conf = min(0.9, 0.4 + 0.13 * len(matched))
        if len(signs) > 1:
            conf *= 0.6
        confidence = round(conf, 2)

        drivers = [p for p, _, _, _ in matched_sorted[:4]]
        return SentimentResult(impact=round(impact, 3), confidence=confidence,
                               theme_primary=theme_primary, themes_secondary=themes_secondary,
                               product_divergence=product_divergence,
                               kind=self._kind(text), drivers=drivers)

    @staticmethod
    def _kind(text: str) -> str:
        if any(c in text for c in OPINION_CUES):
            return "opinion"
        if any(c in text for c in FORECAST_CUES):
            return "forecast"
        return "event"


# ---- swap-able singleton (change this one line for the LLM scorer later) ----
scorer: Scorer = LexiconScorer()


def score_article(title: str, summary: str, source: str = "") -> SentimentResult:
    return scorer.score(title, summary, source)


_STOP = {"the", "a", "an", "of", "to", "in", "on", "for", "and", "or", "as", "at", "by",
         "is", "are", "be", "with", "from", "over", "after", "amid", "says", "said",
         "this", "that", "new", "up", "down"}


def event_key(title: str, day_bucket: str) -> str:
    """Same-day near-duplicate headlines collapse to one event id."""
    toks = re.findall(r"[a-z0-9]+", title.lower())
    sig = sorted({t for t in toks if len(t) > 3 and t not in _STOP})[:6]
    return hashlib.sha1((day_bucket + "|" + " ".join(sig)).encode()).hexdigest()[:10]
