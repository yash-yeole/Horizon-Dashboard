import { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { Bell, Plus, Trash2, Check, BellRing, Power } from 'lucide-react';
import { PageHeader } from '@/components/widgets/PageHeader';
import { Card, CardHeader } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui';
import { useAlerts } from '@/context/AlertsProvider';
import { metricDef, fmtValue, ruleLabel, type Op } from '@/lib/alerts';
import { cn } from '@/lib/utils';

const relTime = (ts: number) => {
  const s = (Date.now() - ts) / 1000;
  if (s < 60) return 'just now';
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
};

export function Alerts() {
  const { rules, fired, values, metrics, zMetrics, unread, addRule, removeRule, toggleRule, markAllRead, clearFired } = useAlerts();

  const groups = useMemo(() => [...new Set(metrics.map((m) => m.group))], [metrics]);
  const zGroups = useMemo(() => [...new Set(zMetrics.map((m) => m.group))], [zMetrics]);
  const anomalies = useMemo(() => zMetrics.filter((m) => m.tierLevel > 0).length, [zMetrics]);
  const [metric, setMetric] = useState(metrics[0].key);
  const def = metricDef(metric)!;
  const [op, setOp] = useState<Op>('above');
  const [value, setValue] = useState('');

  const selectMetric = (key: string) => {
    setMetric(key);
    const d = metricDef(key)!;
    if (d.kind === 'regime') { setOp('becomes'); setValue(d.options?.[0] ?? ''); }
    else { setOp('above'); setValue(''); }
  };

  const submit = () => {
    if (value === '') return;
    addRule({ metric, op, value: def.kind === 'regime' ? value : Number(value) });
    setValue(def.kind === 'regime' ? def.options?.[0] ?? '' : '');
  };

  const stats = [
    { label: 'Active Rules', value: rules.filter((r) => r.enabled).length, c: 'text-cyan-400' },
    { label: 'Total Rules', value: rules.length, c: 'text-slate-300' },
    { label: 'Triggered', value: fired.length, c: 'text-amber-400' },
    { label: 'Unread', value: unread, c: 'text-red-400' },
  ];

  return (
    <div className="space-y-4">
      <PageHeader title="Alerts Center" description="Custom triggers on live prices, spreads, curve, inventory, macro, positioning & rigs" />

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {stats.map((s) => (
          <Card key={s.label} className="flex items-center gap-3 p-3">
            <div className={cn('flex h-9 w-9 items-center justify-center rounded-md bg-[#161820]', s.c)}><Bell className="h-4 w-4" /></div>
            <div><p className="mono text-lg font-bold text-slate-100">{s.value}</p><p className="text-[10px] uppercase tracking-wide text-slate-500">{s.label}</p></div>
          </Card>
        ))}
      </div>

      {/* Statistical anomaly monitor (automatic z-score alerts) */}
      <Card>
        <CardHeader
          title="Statistical Anomaly Monitor"
          subtitle="Auto z-scores · robust (median/MAD) · Watch ≥1.5σ · Elevated ≥2σ · High ≥3σ"
          action={<Badge variant={anomalies ? 'amber' : 'green'} dot>{anomalies ? `${anomalies} active` : 'all normal'}</Badge>}
        />
        {zMetrics.length === 0 ? (
          <p className="p-3 text-[11px] text-slate-600">Building baselines from history…</p>
        ) : (
          <div className="space-y-3 p-3">
            {zGroups.map((g) => (
              <div key={g}>
                <p className="mb-1.5 text-[10px] uppercase tracking-wide text-slate-500">{g}</p>
                <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2 lg:grid-cols-3">
                  {zMetrics.filter((m) => m.group === g).map((m) => {
                    const z = m.stat.z;
                    const c = m.tierLevel >= 3 ? 'text-red-400' : m.tierLevel === 2 ? 'text-amber-400' : m.tierLevel === 1 ? 'text-cyan-400' : 'text-slate-500';
                    const mag = Math.min(100, (Math.abs(z) / 3) * 100);
                    return (
                      <div key={m.key} className="rounded-md border border-[#1f2230] bg-[#0a0b0d] px-2.5 py-1.5">
                        <div className="flex items-center justify-between">
                          <span className="truncate text-[11px] text-slate-300">{m.label}</span>
                          <span className={cn('mono text-[11px] font-bold', c)}>{z >= 0 ? '+' : ''}{z.toFixed(2)}σ</span>
                        </div>
                        <div className="relative mt-1 h-1 rounded bg-[#161820]">
                          <span className="absolute left-1/2 top-0 h-full w-px bg-slate-700" />
                          <div className={cn('absolute top-0 h-full rounded', m.tierLevel >= 3 ? 'bg-red-500' : m.tierLevel === 2 ? 'bg-amber-500' : m.tierLevel === 1 ? 'bg-cyan-500' : 'bg-slate-600')}
                            style={z >= 0 ? { left: '50%', width: `${mag / 2}%` } : { right: '50%', width: `${mag / 2}%` }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* Create + manage rules */}
        <div className="space-y-4 lg:col-span-1">
          <Card>
            <CardHeader title="Create Alert" subtitle="Fires on cross (edge-triggered)" />
            <div className="space-y-2.5 p-3">
              <select value={metric} onChange={(e) => selectMetric(e.target.value)}
                className="h-8 w-full rounded-md border border-[#1f2230] bg-[#0a0b0d] px-2 text-[12px] text-slate-200 focus:border-cyan-500/40 focus:outline-none">
                {groups.map((g) => (
                  <optgroup key={g} label={g}>
                    {metrics.filter((m) => m.group === g).map((m) => <option key={m.key} value={m.key}>{m.label}</option>)}
                  </optgroup>
                ))}
              </select>

              <div className="flex items-center gap-2">
                {def.kind === 'regime' ? (
                  <span className="flex h-8 items-center rounded-md border border-[#1f2230] bg-[#0a0b0d] px-2 text-[12px] text-slate-400">becomes</span>
                ) : (
                  <select value={op} onChange={(e) => setOp(e.target.value as Op)}
                    className="h-8 rounded-md border border-[#1f2230] bg-[#0a0b0d] px-2 text-[12px] text-slate-200 focus:border-cyan-500/40 focus:outline-none">
                    <option value="above">above &gt;</option>
                    <option value="below">below &lt;</option>
                  </select>
                )}
                {def.kind === 'regime' ? (
                  <select value={value} onChange={(e) => setValue(e.target.value)}
                    className="h-8 flex-1 rounded-md border border-[#1f2230] bg-[#0a0b0d] px-2 text-[12px] text-slate-200 focus:border-cyan-500/40 focus:outline-none">
                    {def.options?.map((o) => <option key={o} value={o}>{o}</option>)}
                  </select>
                ) : (
                  <input type="number" step="any" value={value} onChange={(e) => setValue(e.target.value)} placeholder={`value ${def.unit}`}
                    className="h-8 flex-1 rounded-md border border-[#1f2230] bg-[#0a0b0d] px-2 text-[12px] text-slate-200 placeholder:text-slate-600 focus:border-cyan-500/40 focus:outline-none" />
                )}
              </div>

              <p className="text-[10px] text-slate-500">
                Live now: <span className="mono text-slate-300">{values[metric] != null ? fmtValue(values[metric], def) : '—'}</span>
              </p>
              <Button variant="primary" size="sm" className="w-full justify-center" onClick={submit}><Plus className="h-3.5 w-3.5" />Add Alert</Button>
            </div>
          </Card>

          <Card>
            <CardHeader title="Active Rules" subtitle={`${rules.length} configured`} />
            <div className="divide-y divide-[#161820]">
              {rules.length === 0 && <p className="p-3 text-[11px] text-slate-600">No rules yet — create one above.</p>}
              {rules.map((r) => {
                const d = metricDef(r.metric);
                const cur = values[r.metric];
                return (
                  <div key={r.id} className="flex items-center gap-2 px-3 py-2">
                    <button onClick={() => toggleRule(r.id)} title={r.enabled ? 'Disable' : 'Enable'}
                      className={cn('flex h-6 w-6 items-center justify-center rounded', r.enabled ? 'text-cyan-400' : 'text-slate-600')}>
                      <Power className="h-3.5 w-3.5" />
                    </button>
                    <div className="min-w-0 flex-1">
                      <p className={cn('truncate text-[11px] font-medium', r.enabled ? 'text-slate-200' : 'text-slate-500 line-through')}>{ruleLabel(r)}</p>
                      <p className="text-[9px] text-slate-600">now {cur != null ? fmtValue(cur, d) : '—'}</p>
                    </div>
                    <button onClick={() => removeRule(r.id)} className="text-slate-600 hover:text-red-400"><Trash2 className="h-3.5 w-3.5" /></button>
                  </div>
                );
              })}
            </div>
          </Card>
        </div>

        {/* Fired feed */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader
              title="Triggered Alerts" subtitle={`${fired.length} events`}
              action={
                <div className="flex items-center gap-1">
                  <Button variant="ghost" size="sm" onClick={markAllRead}><Check className="h-3.5 w-3.5" />Read</Button>
                  <Button variant="ghost" size="sm" onClick={clearFired}><Trash2 className="h-3.5 w-3.5" />Clear</Button>
                </div>
              }
            />
            <div className="divide-y divide-[#161820]">
              {fired.length === 0 && (
                <div className="flex flex-col items-center justify-center gap-2 py-16 text-slate-600">
                  <BellRing className="h-6 w-6" />
                  <p className="text-[11px]">No alerts triggered yet. They'll appear here when a rule crosses.</p>
                </div>
              )}
              {fired.map((f, i) => (
                <motion.div key={f.id} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.02 }}
                  className={cn('flex items-start gap-3 px-4 py-3', !f.read && 'bg-blue-500/[0.03]')}>
                  <div className={cn('flex h-8 w-8 shrink-0 items-center justify-center rounded-md',
                    f.severity === 'critical' ? 'bg-red-500/10 text-red-400' : f.severity === 'warning' ? 'bg-amber-500/10 text-amber-400' : 'bg-cyan-500/10 text-cyan-400')}>
                    <Bell className="h-4 w-4" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <p className="text-[12px] font-medium text-slate-100">{f.title}</p>
                      <Badge variant={f.severity === 'critical' ? 'red' : f.severity === 'warning' ? 'amber' : 'cyan'}>{f.severity}</Badge>
                      {!f.read && <span className="h-1.5 w-1.5 rounded-full bg-blue-400" />}
                    </div>
                    <p className="mt-0.5 text-[11px] text-slate-500">{f.message}</p>
                    <p className="mt-0.5 text-[9px] text-slate-600">{relTime(f.ts)}</p>
                  </div>
                </motion.div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
