import { useState } from 'react';
import { ChartCard } from '@/components/widgets/ChartCard';
import { CurveChart } from '@/components/charts';
import { Skeleton } from '@/components/ui';
import { useCurve } from '@/hooks/useQuotes';
import type { CurveCompare } from '@/types/api';

// Range tab label -> backend compare key.
const COMPARE: Record<string, CurveCompare> = {
  'Now': 'now',
  'W-1': 'w1',
  'M-1': 'm1',
};
const RANGES = Object.keys(COMPARE);

/** Live forward curve from the backend settlement CSV (Brent for now). */
export function ForwardCurveCard({ id = 'brent', title = 'Brent Forward Curve', height = 200 }: {
  id?: string;
  title?: string;
  height?: number;
}) {
  const [range, setRange] = useState('Now');
  const { data, isLoading, isError } = useCurve(id, COMPARE[range]);
  const points = data?.points ?? [];

  const meta = data ? (
    <span className="mono mr-2 text-[11px] text-slate-400">
      {data.asOf} vs {data.compareDate}
    </span>
  ) : null;

  return (
    <ChartCard
      title={title}
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
          Forward curve unavailable
        </div>
      ) : (
        <CurveChart data={points} height={height} />
      )}
    </ChartCard>
  );
}
