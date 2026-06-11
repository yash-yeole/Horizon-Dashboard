import { createContext, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import {
  useQuotes, useEiaInventories, useCftcPositioning, useRigCount, useCurve, useHistory,
} from '@/hooks/useQuotes';
import { computeSpreads } from '@/lib/spreads';
import {
  METRICS, computeMetricValues, testCondition, ruleLabel, metricDef, fmtValue,
  type AlertRule, type FiredAlert, type MetricDef, type Op,
} from '@/lib/alerts';
import { buildZMetrics, type ZMetric } from '@/lib/zmetrics';
import { hysteresisTier, TIER_NAMES } from '@/lib/zscore';
import { AlertToasts } from '@/components/widgets/AlertToasts';

const RULES_KEY = 'horizon.alertRules';
const FIRED_KEY = 'horizon.firedAlerts';

function load<T>(key: string, fallback: T): T {
  try { const r = localStorage.getItem(key); return r ? (JSON.parse(r) as T) : fallback; } catch { return fallback; }
}
const uid = () => (crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`);

interface AlertsContextValue {
  rules: AlertRule[];
  fired: FiredAlert[];
  values: Record<string, number | string>;
  metrics: MetricDef[];
  zMetrics: ZMetric[];
  unread: number;
  addRule: (r: { metric: string; op: Op; value: number | string }) => void;
  removeRule: (id: string) => void;
  toggleRule: (id: string) => void;
  markAllRead: () => void;
  clearFired: () => void;
}

const AlertsContext = createContext<AlertsContextValue | null>(null);
export const useAlerts = () => {
  const ctx = useContext(AlertsContext);
  if (!ctx) throw new Error('useAlerts must be used within AlertsProvider');
  return ctx;
};

export function AlertsProvider({ children }: { children: ReactNode }) {
  const [rules, setRules] = useState<AlertRule[]>(() => load(RULES_KEY, []));
  const [fired, setFired] = useState<FiredAlert[]>(() => load(FIRED_KEY, []));
  const [toasts, setToasts] = useState<FiredAlert[]>([]);
  const prevMet = useRef<Record<string, boolean>>({});
  const seeded = useRef<Set<string>>(new Set());
  const mountTime = useRef(Date.now());
  // Statistical-anomaly (z-score) firing state: last fired tier + seeded set.
  const zPrevTier = useRef<Record<string, number>>({});
  const zSeeded = useRef<Set<string>>(new Set());

  // Live data bundle (app-wide polling). React Query dedupes with page usage.
  // EIA/CFTC use wider windows here so the z-score baselines have enough history;
  // current value + w/w change (used by the threshold metrics) are unaffected.
  const { data: quotes } = useQuotes('all');
  const spreads = useMemo(() => computeSpreads(quotes?.quotes), [quotes]);
  const { data: eia } = useEiaInventories(104); // EIA endpoint caps weeks at 104 (~2y)
  const { data: cftc } = useCftcPositioning(156);
  const { data: rig } = useRigCount();
  const { data: brentCurve } = useCurve('brent', 'now');

  // 1y daily baselines for price/return/spread z-scores.
  const { data: brentH } = useHistory('brent', '1y');
  const { data: wtiH } = useHistory('wti', '1y');
  const { data: rbobH } = useHistory('rbob', '1y');
  const { data: heatoilH } = useHistory('heatoil', '1y');

  const values = useMemo(
    () => computeMetricValues({ quotes: quotes?.quotes, spreads, eia, cftc, rig, brentCurve }),
    [quotes, spreads, eia, cftc, rig, brentCurve],
  );

  const zMetrics = useMemo(
    () => buildZMetrics({ brent: brentH, wti: wtiH, rbob: rbobH, heatoil: heatoilH, cftc, eia }),
    [brentH, wtiH, rbobH, heatoilH, cftc, eia],
  );

  // Evaluate rules whenever the data changes (edge-triggered + re-arm).
  useEffect(() => {
    if (!Object.keys(values).length) return;
    const fires: FiredAlert[] = [];
    for (const rule of rules) {
      if (!rule.enabled) continue;
      const val = values[rule.metric];
      if (val == null) continue;
      const met = testCondition(val, rule.op, rule.value);
      const firstSeen = !seeded.current.has(rule.id);
      if (firstSeen) {
        seeded.current.add(rule.id);
        prevMet.current[rule.id] = met;
        // Rules loaded from storage arm silently; rules created this session
        // fire right away if already true (instant confirmation).
        if (!(rule.createdAt > mountTime.current && met)) continue;
      } else if (!(met && !prevMet.current[rule.id])) {
        prevMet.current[rule.id] = met;
        continue;
      }
      {
        const m = metricDef(rule.metric);
        fires.push({
          id: uid(), ruleId: rule.id, ts: Date.now(), read: false,
          severity: rule.metric.startsWith('inv') || rule.metric.startsWith('pct') ? 'critical' : 'warning',
          title: ruleLabel(rule),
          message: `${m?.label ?? rule.metric} is now ${fmtValue(val, m)}`,
        });
      }
      prevMet.current[rule.id] = met;
    }
    if (fires.length) {
      setFired((p) => [...fires, ...p].slice(0, 100));
      setToasts((p) => [...fires, ...p].slice(0, 4));
      fires.forEach((f) => setTimeout(() => setToasts((p) => p.filter((t) => t.id !== f.id)), 7000));
    }
  }, [values, rules]);

  // Statistical-anomaly pass: auto-fire Watch/Elevated/High on z-tier escalation.
  // First sighting arms silently (no spam for anomalies already present on load);
  // hysteresis stops re-fires while a value wobbles around a threshold.
  useEffect(() => {
    if (!zMetrics.length) return;
    const fmt = (x: number, unit: string) =>
      unit === '$' ? `$${x.toFixed(2)}` : `${x.toLocaleString('en-US', { maximumFractionDigits: 2 })}${unit ? ` ${unit}` : ''}`;
    const fires: FiredAlert[] = [];
    for (const m of zMetrics) {
      const absZ = Math.abs(m.stat.z);
      const prev = zPrevTier.current[m.key] ?? 0;
      const eff = hysteresisTier(absZ, prev);
      if (!zSeeded.current.has(m.key)) {
        zSeeded.current.add(m.key);
        zPrevTier.current[m.key] = eff;
        continue; // silent arm
      }
      if (eff > prev) {
        const dir = m.stat.z >= 0 ? '+' : '';
        fires.push({
          id: uid(), ruleId: `z:${m.key}`, ts: Date.now(), read: false,
          severity: eff >= 3 ? 'critical' : eff >= 2 ? 'warning' : 'info',
          title: `${m.label} ${dir}${m.stat.z.toFixed(1)}σ · ${TIER_NAMES[eff].toUpperCase()}`,
          message: `${m.label} is ${dir}${m.stat.z.toFixed(2)}σ from normal — now ${fmt(m.stat.value, m.unit)} (typical ${fmt(m.stat.center, m.unit)})`,
        });
      }
      zPrevTier.current[m.key] = eff;
    }
    if (fires.length) {
      setFired((p) => [...fires, ...p].slice(0, 100));
      setToasts((p) => [...fires, ...p].slice(0, 4));
      fires.forEach((f) => setTimeout(() => setToasts((p) => p.filter((t) => t.id !== f.id)), 7000));
    }
  }, [zMetrics]);

  useEffect(() => { localStorage.setItem(RULES_KEY, JSON.stringify(rules)); }, [rules]);
  useEffect(() => { localStorage.setItem(FIRED_KEY, JSON.stringify(fired)); }, [fired]);

  const value: AlertsContextValue = {
    rules, fired, values, metrics: METRICS, zMetrics,
    unread: fired.filter((f) => !f.read).length,
    addRule: (r) => setRules((p) => [{ ...r, id: uid(), enabled: true, createdAt: Date.now() }, ...p]),
    removeRule: (id) => { setRules((p) => p.filter((r) => r.id !== id)); delete prevMet.current[id]; seeded.current.delete(id); },
    toggleRule: (id) => setRules((p) => p.map((r) => (r.id === id ? { ...r, enabled: !r.enabled } : r))),
    markAllRead: () => setFired((p) => p.map((f) => ({ ...f, read: true }))),
    clearFired: () => setFired([]),
  };

  return (
    <AlertsContext.Provider value={value}>
      {children}
      <AlertToasts toasts={toasts} onDismiss={(id) => setToasts((p) => p.filter((t) => t.id !== id))} />
    </AlertsContext.Provider>
  );
}
