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

    const th = it.themePrimary ?? 'Macro';
    themeNum[th] = (themeNum[th] ?? 0) + impact * w;
    themeDen[th] = (themeDen[th] ?? 0) + w;

    if (it.productDivergence) continue;              // keep products out of crude gauge
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
