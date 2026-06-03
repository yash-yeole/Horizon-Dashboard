import { PageHeader } from '@/components/widgets/PageHeader';
import { ChartCard } from '@/components/widgets/ChartCard';
import { Card, CardHeader } from '@/components/ui/Card';
import { DataTable, type Column } from '@/components/widgets/DataTable';
import { MapPlaceholder } from '@/components/widgets/MapPlaceholder';
import { ShippingCongestion } from '@/components/widgets/Panels';
import { Badge } from '@/components/ui/Badge';
import { AreaChartPro, SpreadBars } from '@/components/charts';
import { FREIGHT_RATES } from '@/data/content';
import { brentSeries } from '@/data/series';
import { cn, formatPercent } from '@/lib/utils';
import type { FreightRate } from '@/types';

const VESSEL_POINTS = [
  { x: 28, y: 38, label: 'VLCC ×42', severity: 'high' as const },
  { x: 52, y: 50, label: 'Suezmax ×18', severity: 'medium' as const },
  { x: 70, y: 35, label: 'Aframax ×27', severity: 'medium' as const },
  { x: 80, y: 58, label: 'LR2 ×14', severity: 'low' as const },
  { x: 18, y: 55, label: 'MR ×31', severity: 'low' as const },
];
const ROUTES = [
  { x1: 70, y1: 35, x2: 80, y2: 58 },
  { x1: 28, y1: 38, x2: 70, y2: 35 },
  { x1: 18, y1: 55, x2: 52, y2: 50 },
];

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
          <Card>
            <CardHeader title="Global Vessel Tracking" subtitle="AIS positions · 487 vessels" action={<Badge variant="green" dot>Live</Badge>} />
            <div className="p-3">
              <MapPlaceholder points={VESSEL_POINTS} routes={ROUTES} height={300} />
            </div>
          </Card>
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
