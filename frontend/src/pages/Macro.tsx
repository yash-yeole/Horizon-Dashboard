import { PageHeader } from '@/components/PageHeader';
import { ChartCard } from '@/components/ChartCard';
import { MetricCard } from '@/components/MetricCard';
import { Card, CardHeader } from '@/components/Card';
import { EconomicCalendar } from '@/components/Panels';
import { CorrelationHeatmap } from '@/components/Heatmap';
import { MultiLineChart } from '@/components/charts';
import { LivePriceChart } from '@/components/LivePriceChart';
import { HERO_METRICS } from '@/data/market';
import { comparisonSeries, correlationMatrix, CORRELATION_ASSETS } from '@/data/series';
import { useQuotes, mergeQuotes } from '@/hooks/useQuotes';
import { useCorrelation, useComparison } from '@/hooks/useHistory';
import { cn, formatPrice, formatPercent } from '@/lib/utils';
import type { ApiQuote } from '@/types';

const MACRO_CARDS = HERO_METRICS.filter((m) => ['vix', 'dxy'].includes(m.id));

interface Indicator { name: string; value: string; chg: string; up: boolean }

/** Build an indicator from a live quote, falling back to static values. */
function liveIndicator(
  q: ApiQuote | undefined,
  name: string,
  fmt: (price: number) => string,
  fallback: Omit<Indicator, 'name'>,
): Indicator {
  if (!q) return { name, ...fallback };
  return { name, value: fmt(q.price), chg: formatPercent(q.changePct), up: q.changePct >= 0 };
}

export function Macro() {
  const { data } = useQuotes('all');
  const macroMetrics = mergeQuotes(MACRO_CARDS, data?.quotes);
  const corr = useCorrelation();
  const cmp = useComparison();

  const byId = new Map((data?.quotes ?? []).map((q) => [q.id, q]));
  const usd = (p: number) => `$${formatPrice(p)}`;
  const INDICATORS: Indicator[] = [
    liveIndicator(byId.get('ust10y'), 'US 10Y Yield', (p) => `${p.toFixed(2)}%`, { value: '4.32%', chg: '+3bps', up: true }),
    liveIndicator(byId.get('gold'), 'Gold', usd, { value: '$2,348', chg: '+0.4%', up: true }),
    liveIndicator(byId.get('copper'), 'Copper', (p) => `$${p.toFixed(2)}`, { value: '$4.52', chg: '-1.1%', up: false }),
    liveIndicator(byId.get('sp500'), 'S&P 500', (p) => formatPrice(p), { value: '5,431', chg: '+0.6%', up: true }),
    // No live source for these two — kept static.
    { name: 'EUR/USD', value: '1.0842', chg: '-0.2%', up: false },
    { name: 'US CPI YoY', value: '3.1%', chg: '-0.2pp', up: false },
  ];

  return (
    <div className="space-y-4">
      <PageHeader title="Macro Dashboard" description="Cross-asset · rates · FX · risk sentiment" />

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-8">
        {macroMetrics.map((m, i) => <MetricCard key={m.id} data={m} delay={i * 0.04} />)}
        {INDICATORS.map((ind) => (
          <Card key={ind.name} hover className="flex flex-col justify-between p-3">
            <p className="truncate text-[10px] font-semibold uppercase tracking-wide text-slate-400">{ind.name}</p>
            <p className="mono text-base font-semibold text-slate-100">{ind.value}</p>
            <p className={cn('mono text-[10px]', ind.up ? 'text-green-400' : 'text-red-400')}>{ind.chg}</p>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="h-[320px] lg:col-span-2">
          <LivePriceChart defaultId="dxy" />
        </div>
        <Card>
          <CardHeader title="Cross-Asset Correlation" subtitle="30-day rolling" />
          <div className="p-3"><CorrelationHeatmap matrix={corr.matrix ?? correlationMatrix} assets={corr.labels ?? CORRELATION_ASSETS} /></div>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="h-[300px] lg:col-span-2">
          <ChartCard title="Risk Complex" subtitle="Energy vs macro · rebased" defaultRange="3M">
            <MultiLineChart data={cmp.data.length ? cmp.data : comparisonSeries} series={['Brent', 'WTI', 'RBOB', 'Heating Oil']} height={210} />
          </ChartCard>
        </div>
        <EconomicCalendar />
      </div>
    </div>
  );
}
