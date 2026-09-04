import type {
  ApiQuote, EiaInventoryResponse, CftcResponse, RigCountResponse, CurveResponse, SpreadData,
} from '@/types';

export type Op = 'above' | 'below' | 'becomes';

export interface AlertRule {
  id: string;
  metric: string;
  op: Op;
  value: number | string;
  enabled: boolean;
  createdAt: number;
}

export interface FiredAlert {
  id: string;
  ruleId: string;
  ts: number;
  title: string;
  message: string;
  severity: 'critical' | 'warning' | 'info';
  read: boolean;
}

export interface MetricDef {
  key: string;
  label: string;
  group: string;
  unit: string;
  kind: 'level' | 'change' | 'regime';
  options?: string[]; // for regime 'becomes'
}

// ── Metric catalog (what users can alert on in Phase 1) ──
export const METRICS: MetricDef[] = [
  // Price
  { key: 'price.brent', label: 'Brent', group: 'Price', unit: '$', kind: 'level' },
  { key: 'price.wti', label: 'WTI', group: 'Price', unit: '$', kind: 'level' },
  { key: 'price.rbob', label: 'RBOB', group: 'Price', unit: '$', kind: 'level' },
  { key: 'price.heatoil', label: 'Heating Oil', group: 'Price', unit: '$', kind: 'level' },
  // % move (24h, vs prev close)
  { key: 'pct.brent', label: 'Brent % (24h)', group: '% Move', unit: '%', kind: 'change' },
  { key: 'pct.wti', label: 'WTI % (24h)', group: '% Move', unit: '%', kind: 'change' },
  { key: 'pct.rbob', label: 'RBOB % (24h)', group: '% Move', unit: '%', kind: 'change' },
  { key: 'pct.heatoil', label: 'Heating Oil % (24h)', group: '% Move', unit: '%', kind: 'change' },
  // Spreads
  { key: 'spread.brentWti', label: 'Brent-WTI', group: 'Spread', unit: '$', kind: 'level' },
  { key: 'spread.crack321', label: '3:2:1 Crack', group: 'Spread', unit: '$', kind: 'level' },
  { key: 'spread.rbobBrent', label: 'RBOB-Brent', group: 'Spread', unit: '$', kind: 'level' },
  // Curve (Brent)
  { key: 'curve.brentM1M2', label: 'Brent M1-M2', group: 'Curve', unit: '$', kind: 'level' },
  { key: 'regime.brent', label: 'Brent curve regime', group: 'Curve', unit: '', kind: 'regime', options: ['Backwardation', 'Contango'] },
  // Inventory (EIA w/w change, M bbl) — draw = negative
  { key: 'inv.crude', label: 'Crude stocks w/w', group: 'Inventory', unit: 'mb', kind: 'change' },
  { key: 'inv.gasoline', label: 'Gasoline stocks w/w', group: 'Inventory', unit: 'mb', kind: 'change' },
  { key: 'inv.distillate', label: 'Distillate stocks w/w', group: 'Inventory', unit: 'mb', kind: 'change' },
  // Macro
  { key: 'price.dxy', label: 'DXY', group: 'Macro', unit: '', kind: 'level' },
  { key: 'price.vix', label: 'VIX', group: 'Macro', unit: '', kind: 'level' },
  // Positioning (CFTC COT)
  { key: 'pos.wtiNet', label: 'WTI managed-money net', group: 'Positioning', unit: '', kind: 'level' },
  { key: 'pos.wtiNetChg', label: 'WTI MM net w/w change', group: 'Positioning', unit: '', kind: 'change' },
  { key: 'pos.brentNet', label: 'Brent managed-money net', group: 'Positioning', unit: '', kind: 'level' },
  // Rig count (Baker Hughes)
  { key: 'rig.us', label: 'US rig count', group: 'Rig', unit: '', kind: 'level' },
  { key: 'rig.usChange', label: 'US rig count w/w change', group: 'Rig', unit: '', kind: 'change' },
];

export const metricDef = (key: string) => METRICS.find((m) => m.key === key);

export interface MetricBundle {
  quotes?: ApiQuote[];
  spreads?: SpreadData[];
  eia?: EiaInventoryResponse;
  cftc?: CftcResponse;
  rig?: RigCountResponse;
  brentCurve?: CurveResponse;
}

/** Flatten the live data bundle into a {metricKey: value} map. */
export function computeMetricValues(b: MetricBundle): Record<string, number | string> {
  const v: Record<string, number | string> = {};
  const q = (id: string) => b.quotes?.find((x) => x.id === id);
  for (const id of ['brent', 'wti', 'rbob', 'heatoil', 'dxy', 'vix']) {
    const x = q(id);
    if (x) { v[`price.${id}`] = x.price; v[`pct.${id}`] = x.changePct; }
  }
  const sget = (n: string) => b.spreads?.find((s) => s.name === n)?.value;
  const bw = sget('Brent-WTI'); if (bw != null) v['spread.brentWti'] = bw;
  const ck = sget('Crack 3:2:1'); if (ck != null) v['spread.crack321'] = ck;
  const rb = sget('RBOB-Brent'); if (rb != null) v['spread.rbobBrent'] = rb;

  const pts = b.brentCurve?.points;
  if (pts && pts.length >= 2) {
    const d = +(pts[0].price - pts[1].price).toFixed(2);
    v['curve.brentM1M2'] = d;
    v['regime.brent'] = d >= 0 ? 'Backwardation' : 'Contango';
  }
  const eiaGet = (id: string) => b.eia?.series.find((s) => s.id === id);
  for (const id of ['crude', 'gasoline', 'distillate']) {
    const s = eiaGet(id);
    if (s?.change != null) v[`inv.${id}`] = s.change;
  }
  const c = (id: string) => b.cftc?.contracts.find((x) => x.id === id);
  const wti = c('wti'); if (wti) { v['pos.wtiNet'] = wti.mmNet; v['pos.wtiNetChg'] = wti.mmNetChange; }
  const brent = c('brent'); if (brent) v['pos.brentNet'] = brent.mmNet;

  const us = b.rig?.naSummary.find((x) => x.label === 'United States');
  if (us) { v['rig.us'] = us.value; if (us.change != null) v['rig.usChange'] = us.change; }
  return v;
}

export function testCondition(val: number | string, op: Op, threshold: number | string): boolean {
  if (val == null) return false;
  if (op === 'becomes') return String(val) === String(threshold);
  return op === 'above' ? Number(val) > Number(threshold) : Number(val) < Number(threshold);
}

const OP_SYMBOL: Record<Op, string> = { above: '>', below: '<', becomes: '→' };

export function ruleLabel(rule: AlertRule): string {
  const m = metricDef(rule.metric);
  return `${m?.label ?? rule.metric} ${OP_SYMBOL[rule.op]} ${rule.value}${m?.unit ?? ''}`;
}

export function fmtValue(val: number | string, m?: MetricDef): string {
  if (typeof val === 'string') return val;
  return `${val.toLocaleString('en-US', { maximumFractionDigits: 2 })}${m?.unit ?? ''}`;
}
