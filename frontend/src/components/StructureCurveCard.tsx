import { useState, useRef, useEffect, useMemo } from 'react';
import { ChevronDown } from 'lucide-react';
import { ChartCard } from '@/components/ChartCard';
import { AreaChartPro } from '@/components/charts';
import { Skeleton } from '@/components/ui';
import { useCurveStructure } from '@/hooks/useQuotes';
import { cn } from '@/lib/utils';

// The five curves (Brent/Gas Oil = ICE CSV, others = Yahoo futures).
const CURVES = [
  { id: 'brent', name: 'Brent Crude' },
  { id: 'wti', name: 'WTI Crude' },
  { id: 'heatoil', name: 'Heating Oil' },
  { id: 'rbob', name: 'RBOB Gasoline' },
  { id: 'gasoil', name: 'Gas Oil' },
];

const TYPES: Record<'spreads' | 'flys', string[]> = {
  spreads: ['M1-M2', 'M1-M6', 'M1-M12'],
  flys: ['1-2-3', '2-3-4', '4-5-6'],
};

const fmtDate = (d: string) => new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

/** Time-series of calendar spreads / butterflies for a selectable commodity. */
export function StructureCurveCard({ mode, defaultId = 'brent', height = 200 }: {
  mode: 'spreads' | 'flys';
  defaultId?: string;
  height?: number;
}) {
  const [curveId, setCurveId] = useState(defaultId);
  const [type, setType] = useState(TYPES[mode][0]);
  const [open, setOpen] = useState(false);
  const selectorRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (selectorRef.current && !selectorRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onDown);
    return () => document.removeEventListener('mousedown', onDown);
  }, [open]);

  const { data, isLoading, isError } = useCurveStructure(curveId);
  const list = mode === 'spreads' ? data?.spreads : data?.flys;
  const series = list?.find((s) => s.key === type) ?? list?.[0];
  const chartData = useMemo(
    () => (series?.points ?? []).map((p) => ({ time: fmtDate(p.date), value: p.value })),
    [series],
  );

  const last = series?.points.at(-1)?.value;
  const color = last == null ? '#06b6d4' : last >= 0 ? '#10b981' : '#ef4444';
  const activeName = CURVES.find((c) => c.id === curveId)?.name ?? curveId;
  const noun = mode === 'spreads' ? 'Spread' : 'Fly';

  const meta = last != null ? (
    <span className="mono mr-2 text-[11px] text-slate-400">
      {type} <span className={cn(last >= 0 ? 'text-green-400' : 'text-red-400')}>{last >= 0 ? '+' : ''}{last.toFixed(2)}</span>
      {data?.unit ? ` /${data.unit}` : ''}
    </span>
  ) : null;

  const selector = (
    <div className="relative" ref={selectorRef}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 rounded-md border border-[#2a2d3e] bg-[#0a0b0d] px-2 py-1 text-[12px] font-semibold text-slate-100 transition-colors hover:border-blue-500/40"
      >
        {activeName} {noun}
        <ChevronDown className={cn('h-3.5 w-3.5 text-slate-500 transition-transform', open && 'rotate-180')} />
      </button>
      {open && (
        <div className="absolute left-0 top-full z-50 mt-1 w-44 overflow-hidden rounded-md border border-[#2a2d3e] bg-[#0f1117] py-1 shadow-2xl">
          {CURVES.map((c) => (
            <button
              key={c.id}
              type="button"
              onMouseDown={(e) => { e.preventDefault(); setCurveId(c.id); setOpen(false); }}
              className={cn(
                'block w-full px-3 py-1.5 text-left text-[11px] transition-colors hover:bg-[#1c1e27]',
                c.id === curveId ? 'text-blue-400' : 'text-slate-300',
              )}
            >
              {c.name}
            </button>
          ))}
        </div>
      )}
    </div>
  );

  return (
    <ChartCard
      leftControl={selector}
      subtitle={mode === 'spreads' ? 'Calendar spread · 6mo history' : 'Butterfly · 6mo history'}
      ranges={TYPES[mode]}
      range={type}
      onRangeChange={setType}
      rightMeta={meta}
    >
      {isLoading ? (
        <Skeleton className="h-[200px] w-full" />
      ) : isError || chartData.length === 0 ? (
        <div className="flex h-[200px] items-center justify-center text-[11px] text-slate-600">
          {activeName} {noun.toLowerCase()} history unavailable
        </div>
      ) : (
        <AreaChartPro data={chartData} color={color} height={height} />
      )}
    </ChartCard>
  );
}
