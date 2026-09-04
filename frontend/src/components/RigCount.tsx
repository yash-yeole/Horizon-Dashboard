import { ArrowUp, ArrowDown, RefreshCw } from 'lucide-react';
import { Card, CardHeader } from '@/components/Card';
import { SectionTitle } from '@/components/ui';
import { Badge } from '@/components/Badge';
import { BarChartPro, AreaChartPro, Sparkline } from '@/components/charts';
import { useRigCount } from '@/hooks/useQuotes';
import { cn } from '@/lib/utils';
import type { RigItem, RigCountResponse } from '@/types';

const fmt = (n: number) => (Number.isInteger(n) ? n.toString() : n.toLocaleString('en-US', { maximumFractionDigits: 1 }));
const fmtMonth = (d: string) => new Date(`${d}-01`).toLocaleDateString('en-US', { month: 'short', year: '2-digit' });

function Delta({ value, period }: { value: number | null; period: string }) {
  if (value == null) return null;
  const up = value >= 0;
  return (
    <span className={cn('flex items-center gap-0.5 text-[10px] font-medium', up ? 'text-green-400' : 'text-red-400')}>
      {up ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />}
      {fmt(Math.abs(value))} {period}
    </span>
  );
}

function groupItems(data: RigCountResponse, name: string): RigItem[] {
  return data.naGroups.find((g) => g.name === name)?.items ?? [];
}

/** Compact Dashboard card: key totals + a worldwide history sparkline. */
function Compact({ data }: { data: RigCountResponse }) {
  const ww = data.wwHistory.find((h) => h.name === 'Worldwide')?.points.map((p) => p.value) ?? [];
  const stats = [...data.naSummary, ...data.intlSummary];
  return (
    <Card className="flex h-full flex-col p-3">
      <div className="mb-2 flex items-center justify-between">
        <div>
          <p className="text-[12px] font-semibold text-slate-200">Rig Count</p>
          <p className="text-[9px] text-slate-600">Baker Hughes · NA {data.naReportDate} · WW {data.wwReportDate}</p>
        </div>
        {ww.length > 1 && <div className="h-8 w-24"><Sparkline data={ww} color="#22c55e" height={32} /></div>}
      </div>
      <div className="grid flex-1 grid-cols-3 gap-2">
        {stats.map((s) => (
          <div key={s.label} className="rounded-md border border-[#1f2230] bg-[#0a0b0d]/60 p-2">
            <p className="truncate text-[9px] uppercase tracking-wide text-slate-500" title={s.label}>{s.label}</p>
            <p className="mono text-sm font-semibold text-slate-100">{fmt(s.value)}</p>
            <Delta value={s.change} period={s.label === 'International' || s.label === 'Worldwide' ? 'm/m' : 'w/w'} />
          </div>
        ))}
      </div>
    </Card>
  );
}

export function RigCount({ compact = false }: { compact?: boolean }) {
  const { data, isLoading, refresh, isRefreshing } = useRigCount();

  if (!data) {
    const body = isLoading ? 'Loading rig count…' : 'Rig count unavailable.';
    return compact
      ? <Card className="flex h-full items-center justify-center p-4 text-[12px] text-slate-500">{body}</Card>
      : <><SectionTitle>Rig Count · Baker Hughes</SectionTitle><Card className="p-4 text-[12px] text-slate-500">{body}</Card></>;
  }

  if (compact) return <Compact data={data} />;

  const basins = [...groupItems(data, 'Basin')].filter((b) => b.value > 0).sort((a, b) => b.value - a.value).slice(0, 12);
  const oilGas = groupItems(data, 'Oil vs Gas');
  const trajectory = groupItems(data, 'Trajectory');
  const wwHist = data.wwHistory.find((h) => h.name === 'Worldwide')?.points ?? [];
  const cards = [
    ...data.naSummary.map((i) => ({ ...i, period: 'w/w' })),
    ...data.intlSummary.map((i) => ({ ...i, period: 'm/m' })),
  ];

  return (
    <>
      <SectionTitle>
        Rig Count · Baker Hughes
        <span className="ml-2 text-[10px] font-normal normal-case tracking-normal text-slate-500">
          NA {data.naReportDate} (weekly) · Intl {data.wwReportDate} (monthly){data.stale ? ' · cached' : ''}
        </span>
      </SectionTitle>

      <div className="flex items-center justify-end">
        <button
          type="button"
          onClick={() => refresh()}
          disabled={isRefreshing}
          className="flex items-center gap-1.5 rounded-md border border-[#1f2230] bg-[#0f1117] px-2.5 py-1.5 text-[11px] font-medium text-slate-200 transition-colors hover:border-cyan-500/50 hover:text-cyan-300 disabled:opacity-60"
        >
          <RefreshCw className={cn('h-3.5 w-3.5', isRefreshing && 'animate-spin')} />
          {isRefreshing ? 'Refreshing…' : 'Refresh'}
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {cards.map((c) => (
          <Card key={c.label} hover className="p-3">
            <p className="truncate text-[11px] font-semibold uppercase tracking-wide text-slate-400" title={c.label}>{c.label}</p>
            <p className="mono mt-1.5 text-lg font-semibold text-slate-100">{fmt(c.value)}</p>
            <p className="text-[9px] text-slate-600">rigs{c.yearAgo != null ? ` · yr ago ${fmt(c.yearAgo)}` : ''}</p>
            <div className="mt-1"><Delta value={c.change} period={c.period} /></div>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="h-[300px] lg:col-span-2">
          <Card className="flex h-full flex-col">
            <CardHeader title="US Rigs by Basin" subtitle="Baker Hughes · weekly" action={<Badge variant="cyan" dot>NA</Badge>} />
            <div className="flex-1 p-3"><BarChartPro data={basins.map((b) => ({ time: b.label, value: b.value }))} color="#06b6d4" height={225} /></div>
          </Card>
        </div>
        <Card className="flex flex-col">
          <CardHeader title="US Oil vs Gas · Trajectory" subtitle="Active rigs" />
          <div className="flex-1 space-y-3 p-4">
            {[...oilGas, ...trajectory].map((it) => (
              <div key={it.label} className="flex items-center justify-between">
                <span className="text-[11px] text-slate-300">{it.label}</span>
                <span className="flex items-center gap-2">
                  <span className="mono text-[12px] text-slate-100">{fmt(it.value)}</span>
                  <Delta value={it.change} period="w/w" />
                </span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="h-[290px]">
          <Card className="flex h-full flex-col">
            <CardHeader title="International by Region" subtitle="Baker Hughes · monthly" action={<Badge variant="amber" dot>Intl</Badge>} />
            <div className="flex-1 p-3"><BarChartPro data={data.intlRegions.map((r) => ({ time: r.label, value: r.value }))} color="#f59e0b" height={215} /></div>
          </Card>
        </div>
        <div className="h-[290px]">
          <Card className="flex h-full flex-col">
            <CardHeader title="Worldwide Rig Count" subtitle="Monthly · 24m" />
            <div className="flex-1 p-3"><AreaChartPro data={wwHist.map((p) => ({ time: fmtMonth(p.date), value: p.value }))} color="#8b5cf6" height={215} /></div>
          </Card>
        </div>
      </div>

      <p className="text-[9px] text-slate-600">Source: Baker Hughes Rig Count (rigcount.bakerhughes.com)</p>
    </>
  );
}
