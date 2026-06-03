import { PageHeader } from '@/components/widgets/PageHeader';
import { ChartCard } from '@/components/widgets/ChartCard';
import { CommodityBoard } from '@/components/widgets/CommodityBoard';
import { MetricCard } from '@/components/widgets/MetricCard';
import { Card, CardHeader } from '@/components/ui/Card';
import { Progress } from '@/components/ui';
import { AreaChartPro, MultiLineChart, SpreadBars } from '@/components/charts';
import { PRODUCTS } from '@/data/market';
import { brentSeries, comparisonSeries } from '@/data/series';
import { useQuotes, mergeQuotes } from '@/hooks/useQuotes';
import { useSeries, useComparison } from '@/hooks/useHistory';

const REFINERY = [
  { region: 'US Gulf Coast', util: 93.2 },
  { region: 'US Midwest', util: 88.5 },
  { region: 'NW Europe', util: 84.1 },
  { region: 'Singapore', util: 90.7 },
  { region: 'Middle East', util: 86.3 },
];

const CRACKS = [
  { name: 'Gasoline 321', value: 22.8 },
  { name: 'Distillate', value: 28.4 },
  { name: 'Jet Crack', value: 24.1 },
  { name: 'Fuel Oil', value: -8.2 },
  { name: 'Naphtha', value: -4.6 },
];

export function Products() {
  const { data } = useQuotes('all');
  const products = mergeQuotes(PRODUCTS, data?.quotes);
  const rbob = useSeries('rbob');
  const cmp = useComparison();

  return (
    <div className="space-y-4">
      <PageHeader title="Refined Products" description="Gasoline · distillates · cracks · refining margins" />

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        {products.map((m, i) => <MetricCard key={m.id} data={m} delay={i * 0.04} />)}
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="h-[300px] lg:col-span-2">
          <ChartCard title="Crack Spreads" subtitle="Refining margins · USD/bbl" defaultRange="1M">
            <SpreadBars data={CRACKS} height={220} />
          </ChartCard>
        </div>
        <Card className="flex h-[300px] flex-col">
          <CardHeader title="Refinery Utilization" subtitle="Regional run rates" />
          <div className="flex-1 space-y-3 p-4">
            {REFINERY.map((r) => (
              <div key={r.region}>
                <div className="mb-1 flex items-center justify-between">
                  <span className="text-[11px] text-slate-300">{r.region}</span>
                  <span className="mono text-[11px] font-medium text-slate-200">{r.util}%</span>
                </div>
                <Progress value={r.util} color={r.util > 90 ? 'bg-green-500' : r.util > 85 ? 'bg-amber-500' : 'bg-blue-500'} />
              </div>
            ))}
          </div>
        </Card>
      </div>

      <CommodityBoard title="Product Benchmarks" subtitle="Live pricing" rows={products} />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="h-[300px]">
          <ChartCard title="Gasoline (RBOB)" subtitle="NYMEX · USD/gal" defaultRange="3M">
            <AreaChartPro data={rbob.data.length ? rbob.data : brentSeries} color="#f59e0b" height={210} />
          </ChartCard>
        </div>
        <div className="h-[300px]">
          <ChartCard title="Product Complex" subtitle="Rebased to 100" defaultRange="3M">
            <MultiLineChart data={cmp.data.length ? cmp.data : comparisonSeries} series={['Brent', 'WTI']} height={210} />
          </ChartCard>
        </div>
      </div>
    </div>
  );
}
