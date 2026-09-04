import { PageHeader } from '@/components/PageHeader';
import { ChartCard } from '@/components/ChartCard';
import { Card, CardHeader } from '@/components/Card';
import { DataTable, type Column } from '@/components/DataTable';
import { TankerMap } from '@/components/TankerMap';
import { ShippingCongestion } from '@/components/Panels';
import { Badge } from '@/components/Badge';
import { AreaChartPro, SpreadBars } from '@/components/charts';
import { FREIGHT_RATES } from '@/data/content';
import { brentSeries } from '@/data/series';
import { cn, formatPercent } from '@/lib/utils';
import type { FreightRate } from '@/types';

export function Freight() {
  const columns: Column<FreightRate & Record<string, unknown>>[] = [
    { key: 'route', header: 'Route', render: (r) => <span className="font-medium text-slate-200">{r.route}</span> },
    { key: 'vessel', header: 'Class', render: (r) => <Badge variant="blue">{r.vessel}</Badge> },
    { key: 'rate', header: 'Rate', align: 'right', render: (r) => <span className="mono text-slate-100">{r.rate.toLocaleString()} <span className="text-[9px] text-slate-500">{r.unit}</span></span> },
    { key: 'changePct', header: 'Chg %', align: 'right', render: (r) => (
      <span className={cn('mono rounded px-1 py-0.5', r.changePct >= 0 ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400')}>{formatPercent(r.changePct)}</span>
    ) },
  ];

  return (
    <div className="space-y-4">
      <PageHeader title="Freight & Shipping" description="Tanker rates · vessel tracking · congestion · routes" />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <TankerMap />
        </div>
        <ShippingCongestion />
      </div>

      <Card>
        <CardHeader title="Tanker Freight Rates" subtitle="Spot · Baltic Exchange" />
        <DataTable columns={columns} data={FREIGHT_RATES as (FreightRate & Record<string, unknown>)[]} />
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="h-[290px]">
          <ChartCard title="Baltic Dirty Tanker Index" subtitle="BDTI · points" defaultRange="3M">
            <AreaChartPro data={brentSeries} color="#8b5cf6" height={200} />
          </ChartCard>
        </div>
        <div className="h-[290px]">
          <ChartCard title="Freight Spreads" subtitle="Route differentials · WS points" ranges={['1W', '1M']} defaultRange="1M">
            <SpreadBars data={[
              { name: 'TD3C-TD20', value: 12.4 },
              { name: 'TD7-TD8', value: -5.2 },
              { name: 'TC2-TC14', value: 8.1 },
              { name: 'TD22-TD15', value: 3.6 },
            ]} height={200} />
          </ChartCard>
        </div>
      </div>
    </div>
  );
}
