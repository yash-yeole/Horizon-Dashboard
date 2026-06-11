// Builds the statistical-anomaly metric set (Tier A + B) from data the app
// already fetches. Each metric z-scores the *right* transformation of its series
// so the stationarity assumption holds:
//   • prices  → rolling z on the level (Bollinger-style "stretch", 60d window)
//   • % moves → z on daily returns (stationary)
//   • spreads → z on the level (mean-reverting / cointegrated)
//   • positioning, inventory → z on the weekly series / weekly change
import type { HistoryResponse, CftcResponse, EiaInventoryResponse } from '@/types/api';
import { robustZ, zTierLevel, type ZStat } from './zscore';

const GAL = 42; // USD/gal → USD/bbl for refined products

export interface ZMetric {
  key: string;
  label: string;
  group: string;
  unit: string;
  stat: ZStat;
  tierLevel: number; // raw tier from |z| (hysteresis applied at fire time)
}

type Hist = HistoryResponse | undefined;

const pts = (h: Hist) => (h?.points ?? []).filter((p) => Number.isFinite(p.value));
const levels = (h: Hist) => pts(h).map((p) => p.value);
const dayKey = (t: number) => Math.floor(t / 86400);

/** Daily % returns from a price history. */
function returns(h: Hist): number[] {
  const c = pts(h);
  const out: number[] = [];
  for (let i = 1; i < c.length; i++) {
    if (c[i - 1].value) out.push((c[i].value / c[i - 1].value - 1) * 100);
  }
  return out;
}

/** Combine several price histories day-by-day (intersection of trading days). */
function combine(hists: Hist[], fn: (vals: number[]) => number): number[] {
  const maps = hists.map((h) => new Map(pts(h).map((p) => [dayKey(p.time), p.value])));
  if (!maps.length || !maps[0].size) return [];
  const days = [...maps[0].keys()].sort((a, b) => a - b);
  const out: number[] = [];
  for (const d of days) {
    const vals = maps.map((m) => m.get(d));
    if (vals.every((v) => v != null)) out.push(fn(vals as number[]));
  }
  return out;
}

/** Week-over-week changes of an EIA series (mb). */
function eiaChanges(eia: EiaInventoryResponse | undefined, id: string): number[] {
  const s = eia?.series.find((x) => x.id === id);
  const vs = (s?.points ?? []).filter((p) => p.value != null).map((p) => p.value as number);
  const out: number[] = [];
  for (let i = 1; i < vs.length; i++) out.push(+(vs[i] - vs[i - 1]).toFixed(2));
  return out;
}

interface ZInputs {
  brent?: Hist; wti?: Hist; rbob?: Hist; heatoil?: Hist;
  cftc?: CftcResponse; eia?: EiaInventoryResponse;
}

// (key, label, group, unit, series, window) — window undefined = full history.
function defs(d: ZInputs): [string, string, string, string, number[], number?][] {
  const cftcNet = (id: string) =>
    (d.cftc?.contracts.find((c) => c.id === id)?.netHistory ?? []).map((p) => p.value);
  return [
    // Tier A — % moves (daily returns, stationary)
    ['pct.brent', 'Brent daily move', '% Move', '%', returns(d.brent), 252],
    ['pct.wti', 'WTI daily move', '% Move', '%', returns(d.wti), 252],
    ['pct.rbob', 'RBOB daily move', '% Move', '%', returns(d.rbob), 252],
    ['pct.heatoil', 'Heating Oil daily move', '% Move', '%', returns(d.heatoil), 252],
    // Tier A — spreads (mean-reverting levels)
    ['spread.brentWti', 'Brent-WTI', 'Spread', '$', combine([d.brent, d.wti], ([b, w]) => b - w), 120],
    ['spread.rbobBrent', 'RBOB-Brent', 'Spread', '$', combine([d.rbob, d.brent], ([r, b]) => r * GAL - b), 120],
    ['spread.crack321', '3:2:1 Crack', 'Spread', '$', combine([d.wti, d.rbob, d.heatoil], ([w, r, h]) => (2 * r * GAL + h * GAL) / 3 - w), 120],
    // Tier A — positioning (weekly, mean-reverting)
    ['pos.wtiNet', 'WTI managed-money net', 'Positioning', '', cftcNet('wti')],
    ['pos.brentNet', 'Brent managed-money net', 'Positioning', '', cftcNet('brent')],
    // Tier B — price stretch (rolling z on level, 60d window)
    ['price.brent', 'Brent (stretch)', 'Price', '$', levels(d.brent), 60],
    ['price.wti', 'WTI (stretch)', 'Price', '$', levels(d.wti), 60],
    ['price.rbob', 'RBOB (stretch)', 'Price', '$', levels(d.rbob), 60],
    ['price.heatoil', 'Heating Oil (stretch)', 'Price', '$', levels(d.heatoil), 60],
    // Tier B — inventory (weekly w/w change)
    ['inv.crude', 'Crude stocks w/w', 'Inventory', 'mb', eiaChanges(d.eia, 'crude')],
    ['inv.gasoline', 'Gasoline stocks w/w', 'Inventory', 'mb', eiaChanges(d.eia, 'gasoline')],
    ['inv.distillate', 'Distillate stocks w/w', 'Inventory', 'mb', eiaChanges(d.eia, 'distillate')],
  ];
}

export function buildZMetrics(d: ZInputs): ZMetric[] {
  const out: ZMetric[] = [];
  for (const [key, label, group, unit, series, window] of defs(d)) {
    const stat = robustZ(series, window);
    if (!stat) continue;
    out.push({ key, label, group, unit, stat, tierLevel: zTierLevel(Math.abs(stat.z)) });
  }
  return out;
}
