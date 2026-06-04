import { useState, useRef, useEffect } from 'react';
import { ChevronDown } from 'lucide-react';
import { ChartCard } from '@/components/widgets/ChartCard';
import { CurveChart } from '@/components/charts';
import { Skeleton } from '@/components/ui';
import { useCurve } from '@/hooks/useQuotes';
import { cn } from '@/lib/utils';
import type { CurveCompare } from '@/types/api';

// Range tab label -> backend compare key.
const COMPARE: Record<string, CurveCompare> = { 'Now': 'now', 'W-1': 'w1', 'M-1': 'm1' };
const RANGES = Object.keys(COMPARE);

// The five curves we can serve (Brent/Gas Oil = ICE CSV, others = Yahoo futures).
const CURVES = [
  { id: 'brent', name: 'Brent Crude' },
  { id: 'wti', name: 'WTI Crude' },
  { id: 'heatoil', name: 'Heating Oil' },
  { id: 'rbob', name: 'RBOB Gasoline' },
  { id: 'gasoil', name: 'Gas Oil' },
];

/** Live forward curve. Optionally lets the user switch between the five commodities. */
export function ForwardCurveCard({ id = 'brent', title = 'Brent Forward Curve', height = 200, selectable = false }: {
  id?: string;
  title?: string;
  height?: number;
  selectable?: boolean;
}) {
  const [curveId, setCurveId] = useState(id);
  const [range, setRange] = useState('Now');
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

  const active = selectable ? curveId : id;
  const { data, isLoading, isError } = useCurve(active, COMPARE[range]);
  const points = data?.points ?? [];
  const activeName = CURVES.find((c) => c.id === active)?.name ?? title;

  const meta = data ? (
    <span className="mono mr-2 text-[11px] text-slate-400">{data.asOf} vs {data.compareDate}</span>
  ) : null;

  const selector = selectable ? (
    <div className="relative" ref={selectorRef}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 rounded-md border border-[#2a2d3e] bg-[#0a0b0d] px-2 py-1 text-[12px] font-semibold text-slate-100 transition-colors hover:border-blue-500/40"
      >
        {activeName} Curve
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
                c.id === active ? 'text-blue-400' : 'text-slate-300',
              )}
            >
              {c.name}
            </button>
          ))}
        </div>
      )}
    </div>
  ) : undefined;

  return (
    <ChartCard
      title={selectable ? undefined : title}
      leftControl={selector}
      subtitle="Settlement curve · contango / backwardation"
      ranges={RANGES}
      range={range}
      onRangeChange={setRange}
      rightMeta={meta}
    >
      {isLoading ? (
        <Skeleton className="h-[200px] w-full" />
      ) : isError || points.length === 0 ? (
        <div className="flex h-[200px] items-center justify-center text-[11px] text-slate-600">
          {activeName} forward curve unavailable
        </div>
      ) : (
        <CurveChart data={points} height={height} />
      )}
    </ChartCard>
  );
}
