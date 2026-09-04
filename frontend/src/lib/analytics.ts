import type { CorrelationEntry, HistoryPoint } from '@/types';

export type Series = HistoryPoint[];
export type HistMap = Record<string, Series>;
export interface AssetDef { id: string; label: string }

/** Format a unix-seconds timestamp as a short axis label. */
export function fmtDate(unixSeconds: number): string {
  return new Date(unixSeconds * 1000).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

/** Simple period-over-period returns of a price series. */
function returns(s: Series): number[] {
  const r: number[] = [];
  for (let i = 1; i < s.length; i++) {
    const prev = s[i - 1].value;
    if (prev) r.push(s[i].value / prev - 1);
  }
  return r;
}

/** Pearson correlation of two return arrays (aligned on the shorter tail). */
function pearson(a: number[], b: number[]): number {
  const n = Math.min(a.length, b.length);
  if (n < 3) return 0;
  const xa = a.slice(a.length - n);
  const xb = b.slice(b.length - n);
  const ma = xa.reduce((s, v) => s + v, 0) / n;
  const mb = xb.reduce((s, v) => s + v, 0) / n;
  let num = 0, da = 0, db = 0;
  for (let i = 0; i < n; i++) {
    const x = xa[i] - ma;
    const y = xb[i] - mb;
    num += x * y; da += x * x; db += y * y;
  }
  const den = Math.sqrt(da * db);
  return den === 0 ? 0 : num / den;
}

/** Build a correlation matrix from daily returns. Returns null if too few assets have data. */
export function buildCorrelation(byId: HistMap, assets: AssetDef[]): { matrix: CorrelationEntry[]; labels: string[] } | null {
  const present = assets.filter((a) => (byId[a.id]?.length ?? 0) > 3);
  if (present.length < 2) return null;

  const rets: Record<string, number[]> = {};
  present.forEach((a) => { rets[a.label] = returns(byId[a.id]); });

  const matrix: CorrelationEntry[] = present.map((a) => {
    const values: Record<string, number> = {};
    present.forEach((b) => {
      values[b.label] = a.label === b.label ? 1 : +pearson(rets[a.label], rets[b.label]).toFixed(2);
    });
    return { asset: a.label, values };
  });
  return { matrix, labels: present.map((a) => a.label) };
}

/** Rebase several price series to 100 at the start of the common window. */
export function buildRebased(byId: HistMap, assets: AssetDef[]): Record<string, number | string>[] {
  const present = assets.filter((a) => (byId[a.id]?.length ?? 0) > 1);
  if (!present.length) return [];

  const minLen = Math.min(...present.map((a) => byId[a.id].length));
  const base: Record<string, number> = {};
  present.forEach((a) => { base[a.label] = byId[a.id][byId[a.id].length - minLen].value; });

  const ref = byId[present[0].id];
  const out: Record<string, number | string>[] = [];
  for (let i = 0; i < minLen; i++) {
    const row: Record<string, number | string> = { time: fmtDate(ref[ref.length - minLen + i].time) };
    present.forEach((a) => {
      const s = byId[a.id];
      const v = s[s.length - minLen + i].value;
      row[a.label] = base[a.label] ? +((v / base[a.label]) * 100).toFixed(2) : 100;
    });
    out.push(row);
  }
  return out;
}

/** Annualized realized volatility (%) from daily returns. */
export function realizedVol(s: Series | undefined): number | null {
  if (!s || s.length < 5) return null;
  const r = returns(s);
  const m = r.reduce((sum, v) => sum + v, 0) / r.length;
  const variance = r.reduce((sum, v) => sum + (v - m) ** 2, 0) / r.length;
  return +(Math.sqrt(variance) * Math.sqrt(252) * 100).toFixed(1);
}
