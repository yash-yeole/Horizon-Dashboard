import { useState } from 'react';
import { ArrowUp, ArrowDown } from 'lucide-react';
import { Card, CardHeader } from '@/components/ui/Card';
import { SectionTitle } from '@/components/ui';
import { Badge } from '@/components/ui/Badge';
import { AreaChartPro } from '@/components/charts';
import { useCftcPositioning } from '@/hooks/useQuotes';
import { cn } from '@/lib/utils';

const fmt = (n: number) => n.toLocaleString('en-US');
const fmtDate = (d: string) => new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

/** CFTC Commitments of Traders positioning for the energy contracts. */
export function CftcPositioning() {
  const { data, isLoading } = useCftcPositioning(26);
  const contracts = data?.contracts ?? [];
  const [sel, setSel] = useState('wti');
  const feat = contracts.find((c) => c.id === sel) ?? contracts[0];

  if (!contracts.length) {
    return (
      <>
        <SectionTitle>Trader Positioning · CFTC COT</SectionTitle>
        <Card className="p-4 text-[12px] text-slate-500">
          {isLoading ? 'Loading CFTC positioning…' : 'CFTC positioning unavailable.'}
        </Card>
      </>
    );
  }

  const classes = feat
    ? [
        { name: 'Managed Money', long: feat.mmLong, short: feat.mmShort },
        { name: 'Producer/Merchant', long: feat.pmLong, short: feat.pmShort },
        { name: 'Swap Dealers', long: feat.swapLong, short: feat.swapShort },
        { name: 'Other Reportables', long: feat.otherLong, short: feat.otherShort },
      ]
    : [];

  return (
    <>
      <SectionTitle>
        Trader Positioning · CFTC COT
        {data?.asOf && (
          <span className="ml-2 text-[10px] font-normal normal-case tracking-normal text-slate-500">
            report {data.asOf}{data.stale ? ' · cached' : ''}
          </span>
        )}
      </SectionTitle>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {contracts.map((c) => (
          <button
            key={c.id}
            onClick={() => setSel(c.id)}
            className={cn(
              'rounded-lg border bg-[#0f1117] p-3 text-left transition-colors',
              c.id === sel ? 'border-cyan-500/60' : 'border-[#1f2230] hover:border-[#2a2d3e]',
            )}
          >
            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">{c.name}</p>
            <p className={cn('mono mt-2 text-lg font-semibold', c.mmNet >= 0 ? 'text-green-400' : 'text-red-400')}>
              {c.mmNet >= 0 ? '+' : ''}{fmt(c.mmNet)}
            </p>
            <p className="text-[9px] text-slate-600">Managed money net</p>
            <div className={cn('mt-1 flex items-center gap-1 text-[10px] font-medium', c.mmNetChange >= 0 ? 'text-green-400' : 'text-red-400')}>
              {c.mmNetChange >= 0 ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />}
              {fmt(Math.abs(c.mmNetChange))} w/w
            </div>
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <Card className="flex h-[300px] flex-col">
            <CardHeader
              title={`${feat?.name} · Managed Money Net`}
              subtitle="CFTC COT · weekly · contracts"
              action={<Badge variant={feat && feat.mmNet >= 0 ? 'green' : 'red'} dot>{feat && feat.mmNet >= 0 ? 'Net Long' : 'Net Short'}</Badge>}
            />
            <div className="flex-1 p-3">
              <AreaChartPro
                data={(feat?.netHistory ?? []).map((p) => ({ time: fmtDate(p.date), value: p.value }))}
                color={feat && feat.mmNet >= 0 ? '#22c55e' : '#ef4444'}
                height={220}
              />
            </div>
          </Card>
        </div>

        <Card className="flex flex-col">
          <CardHeader title="Positioning by Trader Class" subtitle={`${feat?.name} · contracts`} />
          <div className="flex-1 divide-y divide-[#161820]">
            {classes.map((cl) => {
              const net = cl.long - cl.short;
              return (
                <div key={cl.name} className="px-3 py-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] text-slate-300">{cl.name}</span>
                    <span className={cn('mono text-[11px] font-medium', net >= 0 ? 'text-green-400' : 'text-red-400')}>
                      {net >= 0 ? '+' : ''}{fmt(net)}
                    </span>
                  </div>
                  <div className="mt-1 flex gap-2 text-[9px]">
                    <span className="text-green-500/80">L {fmt(cl.long)}</span>
                    <span className="text-red-500/80">S {fmt(cl.short)}</span>
                  </div>
                </div>
              );
            })}
            {feat && (
              <div className="flex items-center justify-between px-3 py-2">
                <span className="text-[11px] text-slate-400">Open Interest</span>
                <span className="mono text-[11px] text-slate-200">{fmt(feat.openInterest)}</span>
              </div>
            )}
          </div>
        </Card>
      </div>
    </>
  );
}
