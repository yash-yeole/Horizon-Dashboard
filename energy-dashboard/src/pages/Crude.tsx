import { Download, Plus } from 'lucide-react';
import { PageHeader } from '@/components/widgets/PageHeader';
import { ChartCard } from '@/components/widgets/ChartCard';
import { CommodityBoard } from '@/components/widgets/CommodityBoard';
import { MetricCard } from '@/components/widgets/MetricCard';
import { Button } from '@/components/ui';
import { SpreadBars } from '@/components/charts';
import { LivePriceChart } from '@/components/widgets/LivePriceChart';
import { ForwardCurveCard } from '@/components/widgets/ForwardCurveCard';
import { StructureCurveCard } from '@/components/widgets/StructureCurveCard';
import { SpreadMonitor } from '@/components/widgets/Panels';
import { CftcPositioning } from '@/components/widgets/CftcPositioning';
import { CRUDE_GRADES } from '@/data/market';
import { useQuotes, mergeQuotes } from '@/hooks/useQuotes';
import { computeSpreads } from '@/lib/spreads';

export function Crude() {
  const { data } = useQuotes('all');
  const grades = mergeQuotes(CRUDE_GRADES, data?.quotes);
  const spreads = computeSpreads(data?.quotes);

  return (
    <div className="space-y-4">
      <PageHeader
        title="Crude Oil Markets"
        description="Global benchmarks · grades · differentials · curve structure"
        actions={
          <>
            <Button variant="outline" size="sm"><Plus className="h-3.5 w-3.5" />Add to watchlist</Button>
            <Button variant="primary" size="sm"><Download className="h-3.5 w-3.5" />Export</Button>
          </>
        }
      />

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        {grades.map((m, i) => <MetricCard key={m.id} data={m} delay={i * 0.04} />)}
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <div className="h-[320px] xl:col-span-2">
          <LivePriceChart defaultId="brent" />
        </div>
        <div className="h-[320px]">
          <ForwardCurveCard id="brent" selectable height={230} />
        </div>
      </div>

      {/* Calendar spreads + butterflies */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="h-[320px]"><StructureCurveCard mode="spreads" defaultId="wti" height={235} /></div>
        <div className="h-[320px]"><StructureCurveCard mode="flys" defaultId="wti" height={235} /></div>
      </div>

      <CftcPositioning />

      <CommodityBoard title="Crude Grades & Benchmarks" subtitle="Live differentials" rows={grades} />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="h-[280px] lg:col-span-2">
          <ChartCard title="Crude Spreads" subtitle="Key differentials · USD/bbl" ranges={['1D', '1W', '1M']} defaultRange="1W">
            <SpreadBars data={spreads.map((s) => ({ name: s.name, value: s.value }))} height={210} />
          </ChartCard>
        </div>
        <SpreadMonitor spreads={spreads} />
      </div>
    </div>
  );
}
