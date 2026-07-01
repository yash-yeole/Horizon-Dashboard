import { PageHeader } from '@/components/widgets/PageHeader';
import { ChartCard } from '@/components/widgets/ChartCard';
import { ReleaseImpactSection } from '@/components/widgets/ReleaseImpact';
import { Card, CardHeader } from '@/components/ui/Card';
import { MapPlaceholder } from '@/components/widgets/MapPlaceholder';
import { Progress, SectionTitle } from '@/components/ui';
import { Badge } from '@/components/ui/Badge';
import { AreaChartPro, BarChartPro, MultiLineChart } from '@/components/charts';
import { INVENTORIES } from '@/data/content';
import { useEiaInventories } from '@/hooks/useQuotes';
import { RigCount } from '@/components/widgets/RigCount';
import { cn } from '@/lib/utils';
import { ArrowUp, ArrowDown, Wifi, WifiOff, RefreshCw } from 'lucide-react';
import type { EiaSeries } from '@/types/api';

// Fallback demo numbers (used when the EIA key is missing / API is unreachable).
const STATIC_CARDS = [
  { name: 'Crude Oil', change: -1.2, level: 459.3, unit: 'M bbl' },
  { name: 'Gasoline', change: +2.4, level: 231.8, unit: 'M bbl' },
  { name: 'Distillate', change: -0.8, level: 117.2, unit: 'M bbl' },
  { name: 'Propane', change: +1.1, level: 53.4, unit: 'M bbl' },
  { name: 'Cushing Hub', change: -0.6, level: 34.2, unit: 'M bbl' },
];

const STATIC_SUPPLY = [
  { name: 'Refinery Utilization', level: 90.2, change: 0.4, unit: '%' },
  { name: 'SPR', level: 367.0, change: 0.0, unit: 'M bbl' },
  { name: 'Crude Production', level: 13.2, change: 0.1, unit: 'M bbl/d' },
];

const CARD_IDS: { id: string; name: string }[] = [
  { id: 'crude', name: 'Crude Oil' },
  { id: 'gasoline', name: 'Gasoline' },
  { id: 'distillate', name: 'Distillate' },
  { id: 'propane', name: 'Propane' },
  { id: 'cushing', name: 'Cushing Hub' },
];

const SUPPLY_IDS: { id: string; name: string }[] = [
  { id: 'refineryUtil', name: 'Refinery Utilization' },
  { id: 'spr', name: 'SPR' },
  { id: 'production', name: 'Crude Production' },
];

const TRADE_IDS: { id: string; name: string; period: string }[] = [
  { id: 'crudeImports', name: 'Crude Imports', period: 'w/w' },
  { id: 'crudeExports', name: 'Crude Exports', period: 'w/w' },
  { id: 'netImports', name: 'Net Imports', period: 'w/w' },
  { id: 'gasolineDemand', name: 'Gasoline Demand', period: 'w/w' },
  { id: 'distillateDemand', name: 'Distillate Demand', period: 'w/w' },
  { id: 'gasolineDaysSupply', name: 'Gasoline Days Supply', period: 'w/w' },
  { id: 'distillateDaysSupply', name: 'Distillate Days Supply', period: 'w/w' },
  { id: 'rigCount', name: 'Rig Count', period: 'm/m' },
];

const STATIC_TRADE = [
  { name: 'Crude Imports', level: 6.2, change: -0.1, unit: 'M bbl/d', period: 'w/w' },
  { name: 'Crude Exports', level: 4.1, change: 0.2, unit: 'M bbl/d', period: 'w/w' },
  { name: 'Net Imports', level: 2.1, change: -0.3, unit: 'M bbl/d', period: 'w/w' },
  { name: 'Gasoline Demand', level: 9.0, change: 0.1, unit: 'M bbl/d', period: 'w/w' },
  { name: 'Distillate Demand', level: 3.9, change: 0.0, unit: 'M bbl/d', period: 'w/w' },
  { name: 'Gasoline Days Supply', level: 23.5, change: -0.5, unit: 'days', period: 'w/w' },
  { name: 'Distillate Days Supply', level: 26.0, change: 0.3, unit: 'days', period: 'w/w' },
  { name: 'Rig Count', level: 545, change: 3, unit: 'rigs', period: 'm/m' },
];

const STATIC_IMPEXP = Array.from({ length: 12 }, (_, i) => ({
  time: `W${i + 1}`, Imports: +(6 + Math.sin(i / 2) * 0.4).toFixed(2), Exports: +(4 + Math.cos(i / 2) * 0.4).toFixed(2),
}));
const STATIC_RIG = Array.from({ length: 12 }, (_, i) => ({ time: `M${i + 1}`, value: 540 + Math.round(Math.sin(i / 2) * 15) }));

const REGIONAL = [
  { region: 'PADD 1 (East)', util: 62 },
  { region: 'PADD 2 (Mid)', util: 71 },
  { region: 'PADD 3 (Gulf)', util: 78 },
  { region: 'PADD 5 (West)', util: 58 },
];

const STORAGE_POINTS = [
  { x: 22, y: 42, label: 'Cushing', severity: 'medium' as const },
  { x: 26, y: 58, label: 'USGC', severity: 'high' as const },
  { x: 50, y: 45, label: 'ARA', severity: 'medium' as const },
  { x: 78, y: 50, label: 'Singapore', severity: 'low' as const },
];

const fmtNum = (n: number) => n.toLocaleString('en-US', { maximumFractionDigits: 1 });
const fmtWeek = (period: string) =>
  new Date(period).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
const fmtMonth = (period: string) =>
  new Date(`${period}-01`).toLocaleDateString('en-US', { month: 'short', year: '2-digit' });

const fmtFetched = (iso: string) => {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
};

export function Inventories() {
  const { data, isError, isLoading, refresh, isRefreshing } = useEiaInventories(24);
  const live = !!data && !data.stale && !isError;
  const byId = new Map<string, EiaSeries>((data?.series ?? []).map((s) => [s.id, s]));

  const cards = live
    ? CARD_IDS.map((c) => {
        const s = byId.get(c.id);
        return { name: c.name, level: s?.latest ?? 0, change: s?.change ?? 0, unit: s?.unit ?? 'M bbl' };
      })
    : STATIC_CARDS;

  const supply = live
    ? SUPPLY_IDS.map((c) => {
        const s = byId.get(c.id);
        return { name: c.name, level: s?.latest ?? 0, change: s?.change ?? 0, unit: s?.unit ?? '' };
      })
    : STATIC_SUPPLY;

  const seriesChart = (id: string, fallback: { time: string; value: number }[]) => {
    const pts = byId.get(id)?.points.filter((p) => p.value != null);
    return live && pts?.length ? pts.map((p) => ({ time: fmtWeek(p.period), value: p.value as number })) : fallback;
  };

  const crudeChart = seriesChart('crude', INVENTORIES.map((d) => ({ time: d.week, value: d.crude })));
  const gasolineChart = seriesChart('gasoline', INVENTORIES.map((d) => ({ time: d.week, value: d.gasoline })));

  const trade = live
    ? TRADE_IDS.map((c) => {
        const s = byId.get(c.id);
        return { name: c.name, level: s?.latest ?? 0, change: s?.change ?? 0, unit: s?.unit ?? '', period: c.period };
      })
    : STATIC_TRADE;

  // Crude imports vs exports, aligned by week.
  const impExpChart = (() => {
    const imp = byId.get('crudeImports')?.points.filter((p) => p.value != null) ?? [];
    const exp = new Map((byId.get('crudeExports')?.points ?? []).map((p) => [p.period, p.value]));
    return live && imp.length
      ? imp.map((p) => ({ time: fmtWeek(p.period), Imports: p.value as number, Exports: (exp.get(p.period) ?? 0) as number }))
      : STATIC_IMPEXP;
  })();

  // Rig count (monthly, Baker Hughes via EIA).
  const rigPts = byId.get('rigCount')?.points.filter((p) => p.value != null) ?? [];
  const rigChart = live && rigPts.length ? rigPts.map((p) => ({ time: fmtMonth(p.period), value: p.value as number })) : STATIC_RIG;

  return (
    <div className="space-y-4">
      <PageHeader
        title="Inventory & Storage"
        description="EIA weekly petroleum status · stocks · utilization · refinery runs"
        actions={
          <div className="flex items-center gap-2">
            {live && data!.fetchedAt && (
              <span className="hidden text-[10px] text-slate-500 sm:inline">Updated {fmtFetched(data!.fetchedAt)}</span>
            )}
            <span className="flex items-center gap-1.5 rounded-md border border-[#1f2230] bg-[#0f1117] px-2.5 py-1.5 text-[10px] font-medium uppercase tracking-wider">
              {live ? (
                <><Wifi className="h-3.5 w-3.5 text-green-400" /><span className="text-green-400">EIA · week of {data!.asOf}</span></>
              ) : (
                <><WifiOff className="h-3.5 w-3.5 text-amber-400" /><span className="text-amber-400">{isLoading ? 'Loading…' : 'Demo · cached'}</span></>
              )}
            </span>
            <button
              type="button"
              onClick={() => refresh()}
              disabled={isRefreshing}
              title="Pull the latest EIA weekly data"
              className="flex items-center gap-1.5 rounded-md border border-[#1f2230] bg-[#0f1117] px-2.5 py-1.5 text-[11px] font-medium text-slate-200 transition-colors hover:border-cyan-500/50 hover:text-cyan-300 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <RefreshCw className={cn('h-3.5 w-3.5', isRefreshing && 'animate-spin')} />
              {isRefreshing ? 'Refreshing…' : 'Refresh'}
            </button>
          </div>
        }
      />

      <ReleaseImpactSection />

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {cards.map((w) => (
          <Card key={w.name} hover className="p-3">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">{w.name}</p>
            <p className="mono mt-2 text-lg font-semibold text-slate-100">{fmtNum(w.level)}</p>
            <p className="text-[9px] text-slate-600">{w.unit}</p>
            <div className={cn('mt-1.5 flex items-center gap-1 text-[11px] font-medium', w.change >= 0 ? 'text-green-400' : 'text-red-400')}>
              {w.change >= 0 ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />}
              {fmtNum(Math.abs(w.change))}{w.unit === '%' ? 'pp' : 'M'} w/w
            </div>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {supply.map((s) => (
          <Card key={s.name} hover className="flex flex-col justify-between p-3">
            <p className="truncate text-[11px] font-semibold uppercase tracking-wide text-slate-400">{s.name}</p>
            <p className="mono mt-2 text-lg font-semibold text-slate-100">
              {fmtNum(s.level)}<span className="ml-1 text-[10px] text-slate-600">{s.unit}</span>
            </p>
            <div className={cn('mt-1 flex items-center gap-1 text-[11px] font-medium', s.change >= 0 ? 'text-green-400' : 'text-red-400')}>
              {s.change >= 0 ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />}
              {fmtNum(Math.abs(s.change))} w/w
            </div>
          </Card>
        ))}
      </div>

      <SectionTitle>Trade, Demand & Drilling</SectionTitle>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-8">
        {trade.map((t) => (
          <Card key={t.name} hover className="flex flex-col justify-between p-3">
            <p className="truncate text-[10px] font-semibold uppercase tracking-wide text-slate-400" title={t.name}>{t.name}</p>
            <p className="mono mt-2 text-base font-semibold text-slate-100">{fmtNum(t.level)}</p>
            <p className="text-[9px] text-slate-600">{t.unit}</p>
            <div className={cn('mt-1 flex items-center gap-1 text-[10px] font-medium', t.change >= 0 ? 'text-green-400' : 'text-red-400')}>
              {t.change >= 0 ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />}
              {fmtNum(Math.abs(t.change))} {t.period}
            </div>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="h-[300px]">
          <ChartCard title="Crude Imports vs Exports" subtitle="EIA weekly · M bbl/d" defaultRange="24W">
            <MultiLineChart data={impExpChart} series={['Imports', 'Exports']} height={230} />
          </ChartCard>
        </div>
        <div className="h-[300px]">
          <ChartCard title="US Rotary Rig Count" subtitle="Baker Hughes via EIA · monthly" defaultRange="2Y">
            <AreaChartPro data={rigChart} color="#22c55e" height={230} />
          </ChartCard>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="h-[320px] lg:col-span-2">
          <ChartCard title="US Commercial Crude Stocks" subtitle="EIA weekly · M bbl" defaultRange="24W">
            <AreaChartPro data={crudeChart} color="#06b6d4" height={235} />
          </ChartCard>
        </div>
        <Card className="flex flex-col">
          <CardHeader title="Regional Utilization" subtitle="PADD storage fill" />
          <div className="flex-1 space-y-3.5 p-4">
            {REGIONAL.map((r) => (
              <div key={r.region}>
                <div className="mb-1 flex justify-between">
                  <span className="text-[11px] text-slate-300">{r.region}</span>
                  <span className="mono text-[11px] text-slate-200">{r.util}%</span>
                </div>
                <Progress value={r.util} color={r.util > 75 ? 'bg-red-500' : r.util > 65 ? 'bg-amber-500' : 'bg-green-500'} />
              </div>
            ))}
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <Card>
            <CardHeader title="Regional Inventory Map" subtitle="Key storage hubs · fill level" action={<Badge variant="amber" dot>Hub data</Badge>} />
            <div className="p-3"><MapPlaceholder points={STORAGE_POINTS} height={280} /></div>
          </Card>
        </div>
        <div className="h-[332px]">
          <ChartCard title="Gasoline Stocks" subtitle="EIA weekly · M bbl" defaultRange="24W">
            <BarChartPro data={gasolineChart} color="#f59e0b" height={240} />
          </ChartCard>
        </div>
      </div>

      <RigCount />
    </div>
  );
}
