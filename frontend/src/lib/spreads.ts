import type { ApiQuote, SpreadData } from '@/types';
import { SPREADS } from '@/data/series';

/**
 * Compute crude spreads from live Yahoo quotes where possible, falling back to
 * the static SPREADS entry for relationships we can't price (no live Gas Oil /
 * Dubai feed). RBOB & Heating Oil are quoted in USD/gal, so they're scaled to
 * USD/bbl (×42) before differencing against the USD/bbl crude benchmarks.
 */
const GAL_PER_BBL = 42;

const byId = (quotes: ApiQuote[], id: string) => quotes.find((q) => q.id === id);

/** Element-wise a−b, aligned on the shorter tail (for the mini sparkline). */
function diffSeries(a: number[], b: number[]): number[] {
  const n = Math.min(a.length, b.length);
  const out: number[] = [];
  for (let i = 0; i < n; i++) out.push(+(a[a.length - n + i] - b[b.length - n + i]).toFixed(3));
  return out;
}

type Computed = { value: number; change: number; history: number[] };

const COMPUTE: Record<string, (q: ApiQuote[]) => Computed | null> = {
  'Brent-WTI': (q) => {
    const b = byId(q, 'brent');
    const w = byId(q, 'wti');
    if (!b || !w) return null;
    return { value: b.price - w.price, change: b.change - w.change, history: diffSeries(b.sparkline, w.sparkline) };
  },
  'RBOB-Brent': (q) => {
    const r = byId(q, 'rbob');
    const b = byId(q, 'brent');
    if (!r || !b) return null;
    return {
      value: r.price * GAL_PER_BBL - b.price,
      change: r.change * GAL_PER_BBL - b.change,
      history: diffSeries(r.sparkline.map((x) => x * GAL_PER_BBL), b.sparkline),
    };
  },
  'Crack 3:2:1': (q) => {
    const w = byId(q, 'wti');
    const r = byId(q, 'rbob');
    const h = byId(q, 'heatoil');
    if (!w || !r || !h) return null;
    const crack = (pw: number, pr: number, ph: number) => (2 * pr * GAL_PER_BBL + ph * GAL_PER_BBL) / 3 - pw;
    const value = crack(w.price, r.price, h.price);
    const prev = crack(w.price - w.change, r.price - r.change, h.price - h.change);
    const sameLen = w.sparkline.length === r.sparkline.length && r.sparkline.length === h.sparkline.length;
    const history = sameLen ? w.sparkline.map((_, i) => +crack(w.sparkline[i], r.sparkline[i], h.sparkline[i]).toFixed(3)) : [];
    return { value, change: value - prev, history };
  },
};

export function computeSpreads(quotes: ApiQuote[] | undefined): SpreadData[] {
  return SPREADS.map((s) => {
    const live = quotes && COMPUTE[s.name]?.(quotes);
    if (!live) return s; // keep static demo value for non-computable spreads
    return {
      name: s.name,
      value: +live.value.toFixed(2),
      change: +live.change.toFixed(2),
      history: live.history.length ? live.history : s.history,
    };
  });
}
