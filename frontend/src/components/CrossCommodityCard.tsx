import { useMemo, useState } from 'react';
import { ChartCard } from '@/components/ChartCard';
import { MultiLineChart } from '@/components/charts';
import { Skeleton } from '@/components/ui';
import { useHistory } from '@/hooks/useQuotes';
import type { HistoryPoint } from '@/types';

// Instruments compared on the cross-commodity chart. Names double as series keys.
const INSTRUMENTS = [
  { id: 'brent', name: 'Brent' },
  { id: 'wti', name: 'WTI' },
  { id: 'rbob', name: 'RBOB' },
  { id: 'heatoil', name: 'Heating Oil' },
] as const;
const SERIES = INSTRUMENTS.map((i) => i.name);

// Range tab label -> backend history range param.
const RANGE_MAP: Record<string, string> = { '1M': '1mo', '3M': '3mo', '6M': '6mo' };
const RANGES = Object.keys(RANGE_MAP);

function fmtTime(epochSec: number): string {
  return new Date(epochSec * 1000).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

/** Merge per-instrument histories into rows rebased to 100 at the window start. */
function buildRebased(named: { name: string; points?: HistoryPoint[] }[]) {
  const maps = named.map(({ name, points }) => {
    const pts = points ?? [];
    const base = pts.find((p) => p.value > 0)?.value;
    const m = new Map<number, number>();
    if (base) for (const p of pts) m.set(p.time, +((p.value / base) * 100).toFixed(2));
    return { name, m };
  });

  const times = [...new Set(maps.flatMap((x) => [...x.m.keys()]))].sort((a, b) => a - b);
  return times.map((t) => {
    const row: Record<string, number | string> = { time: fmtTime(t) };
    for (const x of maps) {
      const v = x.m.get(t);
      if (v != null) row[x.name] = v;
    }
    return row;
  });
}

/** Live cross-commodity comparison — Yahoo history rebased to 100 for each instrument. */
export function CrossCommodityCard({ height = 200 }: { height?: number }) {
  const [range, setRange] = useState('3M');
  const r = RANGE_MAP[range];

  // Fixed set of instruments -> explicit hook calls (rules-of-hooks safe).
  const brent = useHistory('brent', r);
  const wti = useHistory('wti', r);
  const rbob = useHistory('rbob', r);
  const heatoil = useHistory('heatoil', r);
  const queries = [brent, wti, rbob, heatoil];

  const data = useMemo(
    () =>
      buildRebased([
        { name: 'Brent', points: brent.data?.points },
        { name: 'WTI', points: wti.data?.points },
        { name: 'RBOB', points: rbob.data?.points },
        { name: 'Heating Oil', points: heatoil.data?.points },
      ]),
    [brent.data, wti.data, rbob.data, heatoil.data]
  );

  const loading = queries.some((q) => q.isLoading);
  const failed = queries.every((q) => q.isError);

  return (
    <ChartCard
      title="Cross-Commodity"
      subtitle="Rebased to 100"
      ranges={RANGES}
      range={range}
      onRangeChange={setRange}
    >
      {loading ? (
        <Skeleton className="h-[200px] w-full" />
      ) : failed || data.length === 0 ? (
        <div className="flex h-[200px] items-center justify-center text-[11px] text-slate-600">
          Comparison data unavailable
        </div>
      ) : (
        <MultiLineChart data={data} series={SERIES} height={height} />
      )}
    </ChartCard>
  );
}
