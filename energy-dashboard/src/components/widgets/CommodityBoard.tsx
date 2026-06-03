import { Sparkline } from '@/components/charts';
import { Card, CardHeader } from '@/components/ui/Card';
import { DataTable, type Column } from '@/components/widgets/DataTable';
import { cn, formatPrice, formatPercent, formatChange } from '@/lib/utils';
import type { Commodity } from '@/types';

export function CommodityBoard({ title, subtitle, rows }: { title: string; subtitle?: string; rows: Commodity[] }) {
  const columns: Column<Commodity & Record<string, unknown>>[] = [
    {
      key: 'name', header: 'Instrument', render: (r) => (
        <div>
          <p className="font-medium text-slate-200">{r.name}</p>
          <p className="text-[9px] text-slate-600">{r.symbol}</p>
        </div>
      ),
    },
    { key: 'price', header: 'Last', align: 'right', render: (r) => <span className="mono text-slate-100">{formatPrice(r.price)}</span> },
    {
      key: 'change', header: 'Chg', align: 'right', render: (r) => (
        <span className={cn('mono', r.change >= 0 ? 'text-green-400' : 'text-red-400')}>{formatChange(r.change)}</span>
      ),
    },
    {
      key: 'changePct', header: '%', align: 'right', render: (r) => (
        <span className={cn('mono rounded px-1 py-0.5', r.changePct >= 0 ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400')}>
          {formatPercent(r.changePct)}
        </span>
      ),
    },
    { key: 'high', header: 'High', align: 'right', render: (r) => <span className="mono text-slate-400">{formatPrice(r.high)}</span> },
    { key: 'low', header: 'Low', align: 'right', render: (r) => <span className="mono text-slate-400">{formatPrice(r.low)}</span> },
    { key: 'volume', header: 'Vol', align: 'right', render: (r) => <span className="mono text-slate-500">{r.volume}</span> },
    {
      key: 'spark', header: 'Trend', align: 'right', render: (r) => (
        <div className="ml-auto h-6 w-20"><Sparkline data={r.sparkline} color={r.changePct >= 0 ? '#10b981' : '#ef4444'} height={24} /></div>
      ),
    },
  ];
  return (
    <Card>
      <CardHeader title={title} subtitle={subtitle} />
      <DataTable columns={columns} data={rows as (Commodity & Record<string, unknown>)[]} />
    </Card>
  );
}
