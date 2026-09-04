import { useState } from 'react';
import { ArrowRight, ArrowLeftRight } from 'lucide-react';
import { Card, CardHeader } from '@/components/Card';
import { BarChartPro } from '@/components/charts';
import { Skeleton } from '@/components/ui';
import { useLeadLag } from '@/hooks/useQuotes';
import { cn } from '@/lib/utils';
import type { LeadLagPair } from '@/types';

const BASES = [
  { id: 'brent', name: 'Brent' },
  { id: 'wti', name: 'WTI' },
  { id: 'rbob', name: 'RBOB' },
  { id: 'heatoil', name: 'Heating Oil' },
];
const TIMEFRAMES = [
  { id: 'fine', label: '1-min' },
  { id: 'intraday', label: '15-min' },
  { id: 'hourly', label: 'Hourly' },
  { id: 'daily', label: 'Daily' },
];

const fmtDur = (mins: number) => {
  const m = Math.abs(mins);
  if (m === 0) return '0';
  if (m >= 1440) return `${+(m / 1440).toFixed(1)}d`;
  if (m >= 60) return `${+(m / 60).toFixed(1)}h`;
  return `${m}m`;
};
const fmtLag = (lag: number, barMinutes: number) => {
  if (lag === 0) return '0';
  const sign = lag > 0 ? '+' : '−';
  return sign + fmtDur(lag * barMinutes);
};

function Pill({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'rounded-md border px-2.5 py-1 text-[11px] font-medium transition-colors',
        active ? 'border-cyan-500/60 bg-cyan-500/10 text-cyan-300' : 'border-[#1f2230] bg-[#0f1117] text-slate-400 hover:text-slate-200',
      )}
    >
      {children}
    </button>
  );
}

function relationship(baseName: string, p: LeadLagPair) {
  if (p.leader === 'sync' || p.bestLag === 0) return { text: `${baseName} & ${p.name} · synchronous`, sync: true };
  if (p.leader === 'base') return { text: `${baseName} leads ${p.name} by ${fmtDur(p.bestLagMinutes)}`, sync: false };
  return { text: `${p.name} leads ${baseName} by ${fmtDur(p.bestLagMinutes)}`, sync: false };
}

export function LeadLagAnalysis() {
  const [base, setBase] = useState('brent');
  const [tf, setTf] = useState('intraday');
  const [sel, setSel] = useState<string | null>(null);
  const { data, isLoading, isError } = useLeadLag(base, tf);

  const pairs = data?.pairs ?? [];
  const active = pairs.find((p) => p.id === sel) ?? pairs[0];
  const ccfData = active ? active.ccf.map((pt) => ({ time: fmtLag(pt.lag, data!.barMinutes), value: pt.corr })) : [];

  return (
    <Card className="flex flex-col">
      <CardHeader
        title="Lead-Lag Analysis"
        subtitle={data ? `Return cross-correlation · ${data.samples} bars · peak shift = lead/lag` : 'Return cross-correlation'}
      />

      <div className="flex flex-wrap items-center gap-3 border-b border-[#161820] px-4 py-2.5">
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] uppercase tracking-wide text-slate-600">Base</span>
          {BASES.map((b) => <Pill key={b.id} active={base === b.id} onClick={() => { setBase(b.id); setSel(null); }}>{b.name}</Pill>)}
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] uppercase tracking-wide text-slate-600">Timeframe</span>
          {TIMEFRAMES.map((t) => <Pill key={t.id} active={tf === t.id} onClick={() => setTf(t.id)}>{t.label}</Pill>)}
        </div>
      </div>

      {isLoading ? (
        <div className="p-4"><Skeleton className="h-[260px] w-full" /></div>
      ) : isError || !data ? (
        <div className="flex h-[260px] items-center justify-center text-[12px] text-slate-600">Lead-lag data unavailable</div>
      ) : (
        <div className="grid grid-cols-1 gap-4 p-4 lg:grid-cols-2">
          {/* Pair table */}
          <div className="space-y-1.5">
            {pairs.map((p) => {
              const rel = relationship(data.baseName, p);
              const isActive = active?.id === p.id;
              return (
                <button
                  key={p.id}
                  onClick={() => setSel(p.id)}
                  className={cn(
                    'flex w-full items-center justify-between rounded-md border px-3 py-2 text-left transition-colors',
                    isActive ? 'border-cyan-500/50 bg-[#0f1117]' : 'border-[#1f2230] hover:border-[#2a2d3e]',
                  )}
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-1.5 text-[12px] font-medium text-slate-200">
                      {rel.sync ? <ArrowLeftRight className="h-3.5 w-3.5 text-slate-500" /> : <ArrowRight className="h-3.5 w-3.5 text-cyan-400" />}
                      <span className="truncate">{rel.text}</span>
                    </div>
                    <p className="mt-0.5 text-[10px] text-slate-600">peak corr {p.bestCorr.toFixed(2)} · now {p.sameCorr.toFixed(2)}</p>
                  </div>
                  <span className={cn('mono ml-2 shrink-0 text-[12px] font-semibold', rel.sync ? 'text-slate-400' : 'text-cyan-300')}>
                    {p.bestLag === 0 ? '0' : fmtLag(p.bestLag, data.barMinutes)}
                  </span>
                </button>
              );
            })}
          </div>

          {/* CCF chart for the selected pair */}
          <div className="flex flex-col">
            <p className="mb-1 text-[11px] text-slate-400">
              {data.baseName} vs {active?.name} · cross-correlation by shift <span className="text-slate-600">(each step {data.barMinutes < 60 ? `${data.barMinutes}m` : data.barMinutes < 1440 ? `${data.barMinutes / 60}h` : '1d'})</span>
            </p>
            <div className="flex-1">
              <BarChartPro data={ccfData} color="#06b6d4" height={220} />
            </div>
            <p className="mt-1 text-[9px] text-slate-600">Peak left of 0 = {active?.name} leads · right of 0 = {data.baseName} leads</p>
          </div>
        </div>
      )}
    </Card>
  );
}
