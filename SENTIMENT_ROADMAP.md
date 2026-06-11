# HORIZON — News Sentiment v1 Implementation Roadmap

> **Purpose of this file:** A complete, self-contained build spec. A model with no
> prior context can execute it top-to-bottom without re-deriving any design decisions.
> Built with the high-capability model; meant to be *implemented* by a cheaper model.
> Do the steps **in order**. Each step says exactly which file, what to add, and how to verify.

---

## 0. What we are building (the locked design)

Upgrade the news feed from a crude 3-way tone tag (`bullish/bearish/neutral`) to a
**directional, oil-price-impact sentiment engine** with themes, magnitude, confidence,
event type, and a deduped aggregate **News Sentiment gauge**.

**Core principle:** we score *impact on crude oil price*, NOT generic positive/negative tone.
"Refinery fire" is scary (negative tone) but **bearish crude** (less crude demand). The engine
must reflect price direction, not emotion.

**Locked decisions (do not relitigate):**
- v1 = **Layer 1 only**: a signed directional **lexicon** scorer. No LLM, no FinBERT yet.
- **Backend scorer module** behind a swap-able interface (NOT browser-side — see §1).
- Lean stored schema: `impact` (signed), `confidence`, `theme_primary` + `themes_secondary[]`,
  `product_divergence` (bool), `kind` (event|forecast|opinion), `event_key` (dedup).
- **Derive, don't store** the 5-level label (`Strongly Bullish … Strongly Bearish`) — computed
  on the frontend from `impact`.
- **Deferred to a later phase** (do NOT build now): `relevance`, `source_weight`, the LLM scorer,
  per-article server persistence of scores, separate per-theme gauge widgets, alerts-engine
  integration of the index.

**Visible result of v1:**
1. Each news row shows a 5-level colored chip + a theme tag + (if forecast/opinion) a kind tag.
2. The News page shows a **−100…+100 News Sentiment gauge** = recency-decayed, confidence-weighted,
   **deduped** mean of `impact`, with product-divergent stories routed out of the crude gauge.

---

## 1. KEY ARCHITECTURAL DECISION — backend scorer, swap-able interface

Sentiment is **already** computed server-side in `backend/app/services/news.py` (`_classify`) and
flows through `models.py NewsItem` → `/api/news` → `types/api.ts` → `useNews` → UI. We keep that pipe
and replace the classifier with a dedicated module behind one function:

```
news.py  ──calls──>  score_article(title, summary, source) -> SentimentResult
                         implemented today by LexiconScorer
                         swappable later for LlmScorer (same signature, same return type)
```

`news.py`, `models.py`, and the entire frontend depend ONLY on the `SentimentResult` shape — never on
lexicon internals. Swapping to an LLM later = changing one line (`scorer = LlmScorer()`). This satisfies
"swap the scoring engine without changing storage or frontend" by construction, and the LLM scorer must
be server-side anyway (API keys never ship to the browser).

**Guardrail:** nothing outside `sentiment.py` may import lexicon constants. Only `score_article` and
`SentimentResult` are public.

---

## 2. DATA MODEL CHANGES (additive — never remove existing fields)

Old fields (`sentiment`, `importance`, `category`, `tags`) stay and are **derived** from the new score,
so the existing UI and the static fallback `NEWS` keep working unchanged.

### 2a. Backend — `backend/app/models.py`, class `NewsItem`

Add these fields (with defaults, for backwards-compat with cached/stale snapshots):

```python
class NewsItem(CamelModel):
    id: str
    headline: str
    summary: str = ""
    source: str = "FinancialJuice"
    timestamp: str = ""
    published_at: int | None = None
    category: str = "Macro"                 # instrument axis: Crude | Products | Macro (KEEP)
    sentiment: str = "neutral"              # legacy: bullish | bearish | neutral (DERIVED from impact)
    importance: str = "medium"              # high | medium | low (DERIVED)
    tags: list[str] = []
    link: str = ""
    # --- NEW (sentiment v1) ---
    impact: float = 0.0                     # -1..+1 signed; sign=direction, |val|=magnitude; FOR CRUDE
    confidence: float = 0.2                 # 0..1
    theme_primary: str = "Macro"            # Supply|Demand|Inventory|Freight|Geopolitics|Refining|Macro|Weather
    themes_secondary: list[str] = []
    product_divergence: bool = False        # true => hits products/cracks, keep OUT of crude gauge
    kind: str = "event"                     # event | forecast | opinion
    event_key: str = ""                     # dedup cluster id
```

### 2b. Frontend — `energy-dashboard/src/types/api.ts`, interface `NewsApiItem`

Add (camelCase, mirrors Pydantic alias):

```ts
export interface NewsApiItem {
  id: string;
  headline: string;
  summary: string;
  source: string;
  timestamp: string;
  publishedAt: number | null;
  category: string;
  sentiment: 'bullish' | 'bearish' | 'neutral';
  importance: 'high' | 'medium' | 'low';
  tags: string[];
  link: string;
  // NEW
  impact: number;
  confidence: number;
  themePrimary: string;
  themesSecondary: string[];
  productDivergence: boolean;
  kind: 'event' | 'forecast' | 'opinion';
  eventKey: string;
}
```

### 2c. Frontend — `energy-dashboard/src/types/index.ts`, interface `NewsItem`

The static fallback `NEWS` (in `data/content.ts`) does not have the new fields, so make them **optional**
here and have consumers tolerate `undefined`:

```ts
export interface NewsItem {
  id: string;
  headline: string;
  summary: string;
  source: string;
  timestamp: string;
  category: string;
  sentiment: 'bullish' | 'bearish' | 'neutral';
  importance: 'high' | 'medium' | 'low';
  tags: string[];
  // NEW (optional — absent on static fallback)
  impact?: number;
  confidence?: number;
  themePrimary?: string;
  themesSecondary?: string[];
  productDivergence?: boolean;
  kind?: 'event' | 'forecast' | 'opinion';
  eventKey?: string;
}
```

---

## 3. THE SCORER — `backend/app/services/sentiment.py` (NEW FILE)

This is the heart of v1. One pass over `title + summary` produces every field.

### 3a. Public interface (the swap-able boundary)

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol
import math, re

@dataclass
class SentimentResult:
    impact: float                       # -1..+1 (for crude)
    confidence: float                   # 0..1
    theme_primary: str
    themes_secondary: list[str] = field(default_factory=list)
    product_divergence: bool = False
    kind: str = "event"                 # event | forecast | opinion
    drivers: list[str] = field(default_factory=list)

class Scorer(Protocol):
    def score(self, title: str, summary: str, source: str) -> SentimentResult: ...
```

### 3b. The lexicon (USE THIS CONTENT VERBATIM — it's the expensive part to derive)

Each entry: `(phrases, weight, theme, product)`.
`weight` is the **signed** crude-price prior in roughly [-0.9, +0.9]: `+` = bullish crude, `−` = bearish.
`product=True` marks a products/cracks story (sets `product_divergence`).
Match is **substring** on the lowercased `title + " " + summary` (phrases are already lowercase).
Longer phrases should be tried before short ones (sort by length desc) so "output cut" wins over "cut".

```python
# (phrases, weight, theme, product)
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

# Negators: if any appears within NEG_WINDOW chars BEFORE a matched phrase, flip that phrase's sign.
NEGATORS = ["no ", "not ", "fails to", "failed to", "won't", "will not", "without",
            "denies", "denied", "rules out", "ruled out", "delay", "delays", "delayed",
            "postpone", "postponed", "scrap", "scrapped", "abandon", "abandoned",
            "unlikely to", "no plans to"]
NEG_WINDOW = 28  # chars

# "Smaller/larger than expected" flips the meaning of the NEXT inventory/demand term.
SHRINK_EXPECT = ["smaller-than-expected", "smaller than expected", "less than expected",
                 "below expectations", "below forecast", "misses", "missed", "weaker-than-expected"]
GROW_EXPECT  = ["larger-than-expected", "bigger-than-expected", "more than expected",
                "above expectations", "above forecast", "beats", "beat estimates",
                "stronger-than-expected"]

# kind = forecast / opinion / event
FORECAST_CUES = ["forecast", "forecasts", "sees ", "expects", "expected to", "outlook",
                 "projects", "projected", "estimate", "estimates", "survey", "poll",
                 "guidance", "could ", "may ", "likely", "to reach", "to hit", "predicts"]
OPINION_CUES  = ["says", "said", "view", "believes", "comment", "warns", "warning",
                 "analyst", "analysts", "strategist", "goldman", "morgan stanley",
                 "jpmorgan", "citi", "ubs", "barclays", "rbc", "bofa", "opinion"]

# Importance booster (legacy field): force "high" if present
HIGH_KW = ["breaking", "urgent", "opec", "war", "sanction", "force majeure",
           "attack", "halt", "outage", "escalation", "hormuz"]
```

### 3c. The scoring algorithm (LexiconScorer)

```python
class LexiconScorer:
    def __init__(self) -> None:
        # longest phrases first so "output cut" beats "cut"
        self._lex = sorted(LEXICON, key=lambda e: -max(len(p) for p in e[0]))

    def score(self, title: str, summary: str, source: str) -> SentimentResult:
        text = f"{title} {summary}".lower()

        matched: list[tuple[str, float, str, bool]] = []  # (phrase, signed_weight, theme, product)
        for phrases, weight, theme, product in self._lex:
            for p in phrases:
                idx = text.find(p)
                if idx == -1:
                    continue
                w = weight
                # negation: flip if a negator sits just before the phrase
                window = text[max(0, idx - NEG_WINDOW):idx]
                if any(neg in window for neg in NEGATORS):
                    w = -w
                # expectation modifiers (mainly inventory/demand): flip / amplify
                if any(s in text for s in SHRINK_EXPECT) and theme in ("Inventory", "Demand"):
                    w = -abs(w) if weight > 0 else w  # smaller-than-expected draw => bearish
                elif any(g in text for g in GROW_EXPECT) and theme in ("Inventory", "Demand"):
                    w = w * 1.2
                matched.append((p, w, theme, product))
                break  # count each lexicon entry at most once

        if not matched:
            return SentimentResult(impact=0.0, confidence=0.2, theme_primary="Macro",
                                   themes_secondary=[], product_divergence=False,
                                   kind=self._kind(text), drivers=[])

        raw = sum(w for _, w, _, _ in matched)
        impact = math.tanh(0.9 * raw)                       # saturates to [-1, 1]

        # theme: strongest |weight| match is primary; the rest distinct = secondary
        matched_sorted = sorted(matched, key=lambda m: -abs(m[1]))
        theme_primary = matched_sorted[0][2]
        themes_secondary = list(dict.fromkeys(
            m[2] for m in matched_sorted[1:] if m[2] != theme_primary))

        product_divergence = any(prod for _, _, _, prod in matched)

        # confidence: more matches + sign agreement => higher; mixed signs => lower
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


# ---- swap-able singleton (change this one line later for the LLM) ----
scorer: Scorer = LexiconScorer()

def score_article(title: str, summary: str, source: str = "") -> SentimentResult:
    return scorer.score(title, summary, source)
```

### 3d. `event_key` (dedup) — put this helper in `sentiment.py` too

Same-day near-duplicate headlines collapse to one event.

```python
import hashlib

_STOP = {"the","a","an","of","to","in","on","for","and","or","as","at","by","is","are",
         "be","with","from","over","after","amid","says","said","this","that","new","up","down"}

def event_key(title: str, day_bucket: str) -> str:
    """day_bucket = ISO date string (YYYY-MM-DD) of publication (or '')"""
    toks = re.findall(r"[a-z0-9]+", title.lower())
    sig = sorted({t for t in toks if len(t) > 3 and t not in _STOP})[:6]
    return hashlib.sha1((day_bucket + "|" + " ".join(sig)).encode()).hexdigest()[:10]
```

---

## 4. WIRE THE SCORER INTO `backend/app/services/news.py`

Replace the lexicon constants and `_classify` with calls into `sentiment.py`. Keep `category`
routing (instrument axis), `tags`, relative time, energy filter, fetch/merge logic **unchanged**.

1. **Add imports** near the top:
   ```python
   from datetime import datetime, timezone   # (already imported)
   from .sentiment import score_article, event_key
   ```
2. **Delete** the `BULLISH`, `BEARISH` constants and the sentiment half of `_classify`
   (KEEP `PRODUCTS_KW`, `CRUDE_KW`, `HIGH_KW`, `ENERGY_KEYWORDS`, `_has`, `_is_energy`).
3. **Rewrite `_classify`** to derive legacy fields from the score and return everything `_parse` needs.
   Suggested signature change — have `_classify` take title+summary and return a small struct/tuple:

   ```python
   def _classify(title: str, summary: str, day_bucket: str):
       text = f"{title} {summary}".lower()
       res = score_article(title, summary)

       # legacy sentiment from impact sign
       if res.impact >= 0.15:
           sentiment = "bullish"
       elif res.impact <= -0.15:
           sentiment = "bearish"
       else:
           sentiment = "neutral"

       # legacy category (instrument axis) — unchanged routing
       if _has(text, PRODUCTS_KW):
           category = "Products"
       elif _has(text, CRUDE_KW):
           category = "Crude"
       else:
           category = "Macro"

       # legacy importance
       if abs(res.impact) >= 0.5 or _has(text, HIGH_KW):
           importance = "high"
       elif abs(res.impact) >= 0.2:
           importance = "medium"
       else:
           importance = "low"

       matched = _has(text, ENERGY_KEYWORDS)
       tags = [t.upper() if len(t) <= 4 else t.title() for t in matched[:3]]

       return res, sentiment, category, importance, tags, event_key(title, day_bucket)
   ```
4. **In `_parse`**, compute `day_bucket` from the parsed `dt` (or `""`), call the new `_classify`,
   and populate the new `NewsItem` fields:
   ```python
   day_bucket = datetime.fromtimestamp(published_at, timezone.utc).strftime("%Y-%m-%d") if published_at else ""
   res, sentiment, category, importance, tags, ekey = _classify(title, summary, day_bucket)
   items.append(NewsItem(
       id=hashlib.sha1(guid.encode("utf-8")).hexdigest()[:12],
       headline=title, summary=summary, source=source,
       timestamp=timestamp, published_at=published_at,
       category=category, sentiment=sentiment, importance=importance,
       tags=tags, link=link,
       impact=res.impact, confidence=res.confidence,
       theme_primary=res.theme_primary, themes_secondary=res.themes_secondary,
       product_divergence=res.product_divergence, kind=res.kind,
       event_key=ekey,
   ))
   ```

**Do not** change `routers/news.py`, the cache, or `fetch_news` merge logic.

---

## 5. FRONTEND — pass-through + derivation lib

### 5a. `energy-dashboard/src/hooks/useQuotes.ts` — `useNews`

The live branch already spreads `...i`, so new camelCase fields flow through automatically once the
type is updated. For the **fallback** branch (static `NEWS`), add derived defaults so the gauge/labels
still render. Update the mapping:

```ts
const items: NewsFeedItem[] = live
  ? query.data!.items.map((i) => ({ ...i, timestamp: relTime(i.publishedAt, i.timestamp) }))
  : (NEWS as NewsFeedItem[]).map((n) => ({
      ...n,
      impact: n.impact ?? (n.sentiment === 'bullish' ? 0.4 : n.sentiment === 'bearish' ? -0.4 : 0),
      confidence: n.confidence ?? 0.3,
      themePrimary: n.themePrimary ?? 'Macro',
      themesSecondary: n.themesSecondary ?? [],
      productDivergence: n.productDivergence ?? false,
      kind: n.kind ?? 'event',
      eventKey: n.eventKey ?? n.id,
    }));
```
(Also extend `NewsFeedItem` type alias at top of file if needed — it already extends `NewsItem`,
so optional new fields are inherited.)

### 5b. NEW FILE — `energy-dashboard/src/lib/sentiment.ts`

Pattern-match the style of `src/lib/alerts.ts` (pure functions, no React). Contents:

```ts
import type { NewsFeedItem } from '@/hooks/useQuotes';

export type SentimentLabel =
  | 'Strongly Bullish' | 'Bullish' | 'Neutral' | 'Bearish' | 'Strongly Bearish';

// Derive 5-level label from signed impact. Thresholds are the single source of truth.
export function labelFromImpact(impact = 0): SentimentLabel {
  if (impact >= 0.5) return 'Strongly Bullish';
  if (impact >= 0.15) return 'Bullish';
  if (impact <= -0.5) return 'Strongly Bearish';
  if (impact <= -0.15) return 'Bearish';
  return 'Neutral';
}

// Badge variant per label (variants exist in ui/Badge.tsx: green/red/amber/neutral...)
export function labelVariant(label: SentimentLabel): 'green' | 'red' | 'neutral' {
  if (label.includes('Bullish')) return 'green';
  if (label.includes('Bearish')) return 'red';
  return 'neutral';
}

export interface SentimentIndex {
  score: number;                 // -100..+100 (crude, product-divergent excluded)
  label: SentimentLabel;
  bull: number; bear: number; neutral: number; total: number;
  byTheme: Record<string, number>;   // -100..+100 per theme_primary
}

// Recency-decayed, confidence-weighted, DEDUPED mean of impact.
export function newsSentimentIndex(items: NewsFeedItem[], nowMs = Date.now()): SentimentIndex {
  // 1. dedup by eventKey, keep highest-confidence representative
  const byEvent = new Map<string, NewsFeedItem>();
  for (const it of items) {
    const k = it.eventKey ?? it.id;
    const prev = byEvent.get(k);
    if (!prev || (it.confidence ?? 0) > (prev.confidence ?? 0)) byEvent.set(k, it);
  }
  const deduped = [...byEvent.values()];

  // 2. crude index: weighted mean of impact, exclude product-divergent
  let num = 0, den = 0, bull = 0, bear = 0, neutral = 0;
  const themeNum: Record<string, number> = {}, themeDen: Record<string, number> = {};
  for (const it of deduped) {
    const impact = it.impact ?? 0;
    const conf = it.confidence ?? 0.3;
    const ageH = it.publishedAt ? Math.max(0, (nowMs / 1000 - it.publishedAt) / 3600) : 12;
    const decay = Math.pow(0.5, ageH / 24);          // 24h half-life
    const w = conf * decay;

    const lbl = labelFromImpact(impact);
    if (lbl.includes('Bullish')) bull++; else if (lbl.includes('Bearish')) bear++; else neutral++;

    // theme index (all themes)
    const th = it.themePrimary ?? 'Macro';
    themeNum[th] = (themeNum[th] ?? 0) + impact * w;
    themeDen[th] = (themeDen[th] ?? 0) + w;

    // crude headline index excludes product-divergent stories
    if (it.productDivergence) continue;
    num += impact * w; den += w;
  }

  const score = den > 0 ? Math.round((num / den) * 100) : 0;
  const byTheme: Record<string, number> = {};
  for (const th of Object.keys(themeNum)) {
    byTheme[th] = themeDen[th] > 0 ? Math.round((themeNum[th] / themeDen[th]) * 100) : 0;
  }
  return { score, label: labelFromImpact(score / 100), bull, bear, neutral,
           total: deduped.length, byTheme };
}
```

### 5c. `energy-dashboard/src/components/ui/Badge.tsx`

Add a 5-level chip (keep the old `SentimentBadge` for backwards compat):

```tsx
import { labelFromImpact, labelVariant } from '@/lib/sentiment';

export function ImpactBadge({ impact }: { impact?: number }) {
  const label = labelFromImpact(impact ?? 0);
  return <Badge variant={labelVariant(label)}>{label}</Badge>;
}

export function ThemeBadge({ theme }: { theme?: string }) {
  if (!theme) return null;
  return <Badge variant="blue">{theme}</Badge>;
}

export function KindBadge({ kind }: { kind?: string }) {
  if (!kind || kind === 'event') return null;   // only show forecast/opinion
  return <Badge variant="purple">{kind}</Badge>;
}
```
(`blue`/`purple`/`green`/`red`/`neutral` variants already exist.)

---

## 6. FRONTEND — visible surfaces

### 6a. `energy-dashboard/src/pages/News.tsx`
- Import `newsSentimentIndex`, `useMemo` over `news`.
- **Replace** the 3 stat cards (`sentimentStats`) with: keep Bull/Bear counts but add a **gauge**.
  Add a horizontal −100…+100 bar (no new deps): a track with a center mark and a colored fill from
  center to `score`. Show `index.label` and `score`. (Green right of center, red left.)
- In each news row, **replace** `<SentimentBadge sentiment={n.sentiment} />` with
  `<ImpactBadge impact={n.impact} />`, add `<ThemeBadge theme={n.themePrimary} />` and
  `<KindBadge kind={n.kind} />`. Keep `ImportanceBadge`.
- Add `theme` to the category `Tabs` filter is optional; the existing `CATEGORIES` (instrument axis)
  can stay. Optionally add a second Tabs row for theme using the 8 themes.

**Minimal gauge JSX** (drop into the overview grid, replace the old 3 cards):
```tsx
const sent = useMemo(() => newsSentimentIndex(news), [news]);
// ...
<Card className="p-3 col-span-3">
  <div className="flex items-center justify-between">
    <p className="text-[10px] uppercase tracking-wide text-slate-500">News Sentiment · 24h (deduped)</p>
    <span className={`mono text-sm font-bold ${sent.score > 0 ? 'text-green-400' : sent.score < 0 ? 'text-red-400' : 'text-slate-300'}`}>
      {sent.label} · {sent.score > 0 ? '+' : ''}{sent.score}
    </span>
  </div>
  <div className="relative mt-2 h-2 rounded bg-[#1c1e27]">
    <span className="absolute left-1/2 top-0 h-full w-px bg-slate-600" />
    <div
      className={`absolute top-0 h-full rounded ${sent.score >= 0 ? 'bg-green-500' : 'bg-red-500'}`}
      style={ sent.score >= 0
        ? { left: '50%', width: `${Math.min(50, sent.score / 2)}%` }
        : { right: '50%', width: `${Math.min(50, -sent.score / 2)}%` } }
    />
  </div>
  <p className="mt-1 text-[10px] text-slate-500">{sent.bull} bull · {sent.bear} bear · {sent.neutral} neutral · {sent.total} events</p>
</Card>
```

### 6b. `energy-dashboard/src/components/widgets/NewsModal.tsx`
- Swap `SentimentBadge` → `ImpactBadge impact={item.impact}`, add `ThemeBadge` + `KindBadge`.
- Optional: render `item.themesSecondary` as small chips and show drivers if you choose to surface them
  (drivers are not in the API yet — skip unless you also add `drivers` to the model; **do not** for v1).

### 6c. `energy-dashboard/src/components/widgets/Panels.tsx` — `NewsFeed`
- Wherever it renders per-item sentiment, switch to `<ImpactBadge impact={n.impact} />` + `<ThemeBadge>`.
- (Find the NewsFeed block; it uses `useNews()` already.)

---

## 7. BUILD ORDER & VERIFICATION (do in this sequence)

1. **`backend/app/services/sentiment.py`** — create §3 (interface + lexicon + LexiconScorer + event_key).
   Verify in isolation (PowerShell, from `D:\Dashboard_FF\backend`):
   ```powershell
   python -c "from app.services.sentiment import score_article; print(score_article('OPEC+ agrees deeper output cuts', '')); print(score_article('US crude inventories post surprise build', '')); print(score_article('Refinery fire shuts crude unit', '')); print(score_article('Goldman sees oil hitting 100', ''))"
   ```
   Expect: #1 strongly positive impact, theme Supply; #2 negative, Inventory; #3 positive impact +
   `product_divergence=True`, theme Refining; #4 `kind='opinion'` (or forecast).
2. **`backend/app/models.py`** — add §2a fields.
3. **`backend/app/services/news.py`** — rewire §4.
4. Verify the API end-to-end (start backend, hit `/api/news?limit=5`):
   ```powershell
   # however the backend is normally started (e.g. uvicorn app.main:app --reload), then:
   curl "http://localhost:8000/api/news?limit=5"
   ```
   Confirm each item now has `impact`, `confidence`, `themePrimary`, `productDivergence`, `kind`, `eventKey`.
5. **`energy-dashboard/src/types/api.ts`** + **`types/index.ts`** — add §2b/§2c fields.
6. **`energy-dashboard/src/lib/sentiment.ts`** — create §5b.
7. **`energy-dashboard/src/hooks/useQuotes.ts`** — update fallback mapping §5a.
8. **`energy-dashboard/src/components/ui/Badge.tsx`** — add §5c badges.
9. **`News.tsx`, `NewsModal.tsx`, `Panels.tsx`** — §6.
10. **Type-check + build** (from `D:\Dashboard_FF\energy-dashboard`):
    ```powershell
    npm run build
    ```
    Fix any TS errors (most likely: missing optional-field guards — use `?? default`).
11. Visual check: News page shows the gauge + 5-level chips + theme tags; product-divergent stories
    (refinery) don't swing the crude gauge.

---

## 8. GUARDRAILS (do not violate)

- **Never commit `backend/.env`** (contains API keys). It is gitignored — keep it that way.
- **Additive only**: do not delete `sentiment`, `importance`, `category`, or `tags`. They are derived
  and still consumed by existing UI + the static fallback.
- **Swap-able boundary**: outside `sentiment.py`, import only `score_article` / `event_key` /
  `SentimentResult`. No lexicon constants leak out. (This is what makes the LLM swap one line.)
- **Derive, don't store** the 5-level label and the index — compute on the frontend from `impact`.
- **Backwards-compat defaults** on every new model field, so stale cached snapshots still deserialize.
- Keep all existing fetch/cache/merge logic in `news.py` and `routers/news.py` untouched.
- Don't add new npm deps for the gauge — use plain divs + Tailwind (shown in §6a).

---

## 9. EXPLICITLY DEFERRED (NOT in v1 — do not build)

- `relevance` and `source_weight` fields + their weighting in the index (phase 2 — the index formula
  already leaves room: just multiply them in).
- The **LLM scorer** (`LlmScorer`) and provider/key choice. (When added: implement `Scorer`, set
  `scorer = LlmScorer()`, optionally escalate only when `confidence` is low.)
- Server-side persistence of per-article scores.
- Separate per-theme gauge **widgets** (the data — `byTheme` — is already computed; widget is phase 2).
- Alerts-engine integration ("News Sentiment crosses ±X", "Geopolitics index spikes") — fast-follow.
- Crude-vs-products **dual scoring** (v1 only flags `product_divergence`; full product impact is later).

---

## 10. KNOWN v1 LIMITATION (expected, not a bug)

Without `relevance`/`source_weight`, a flood of minor same-theme headlines can tug the gauge more than
one major event. Mitigated in v1 by (a) `event_key` dedup and (b) routing `product_divergence` stories
out of the crude gauge. This is exactly why `relevance` is the first phase-2 add. Expected behavior.
```
