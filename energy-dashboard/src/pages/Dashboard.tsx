import { useState } from 'react';
import { RefreshCw, Layers } from 'lucide-react';
import { PageHeader } from '@/components/widgets/PageHeader';
import { MetricCard } from '@/components/widgets/MetricCard';
import { ChartCard } from '@/components/widgets/ChartCard';
import { Card, CardHeader } from '@/components/ui/Card';
import { Button, SectionTitle } from '@/components/ui';
import { LivePriceChart } from '@/components/widgets/LivePriceChart';
import { ForwardCurveCard } from '@/components/widgets/ForwardCurveCard';
import { CrossCommodityCard } from '@/components/widgets/CrossCommodityCard';
import { CorrelationHeatmap } from '@/components/charts/Heatmap';
import {
  NewsFeed, MarketMovers, EconomicCalendar, AlertsSummary, ShippingCongestion,
} from '@/components/widgets/Panels';
import { NewsModal } from '@/components/widgets/NewsModal';
import { RigCount } from '@/components/widgets/RigCount';
import { HERO_METRICS } from '@/data/market';
import { correlationMatrix, CORRELATION_ASSETS } from '@/data/series';
import { INVENTORIES } from '@/data/content';
import { BarChartPro } from '@/components/charts';
import { useQuotes, mergeQuotes, useEiaInventories } from '@/hooks/useQuotes';
import { useCorrelation } from '@/hooks/useHistory';

export function Dashboard() {
  const [selectedNews, setSelectedNews] = useState<string | null>(null);
  const { data, isLoading, isError, refetch, isFetching } = useQuotes('all');

  // Live EIA crude stocks for the inventory chart, static fallback otherwise.
  const { data: eia } = useEiaInventories(12);
  const crudePts = eia?.series.find((s) => s.id === 'crude')?.points.filter((p) => p.value != null);
  const crudeInventory = !eia?.stale && crudePts?.length
    ? crudePts.map((p) => ({ time: new Date(p.period).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }), value: p.value as number }))
    : INVENTORIES.map((d) => ({ time: d.week, value: d.crude }));
  const heroMetrics = mergeQuotes(HERO_METRICS, data?.quotes);
  const live = !isError && !!data?.quotes?.length && !data.quotes.some((q) => q.stale);

  // Live cross-asset correlation (daily returns), static matrix as fallback.
  const corr = useCorrelation();
  const corrMatrix = corr.matrix ?? correlationMatrix;
  const corrAssets = corr.labels ?? CORRELATION_ASSETS;

  return (
    <div className="space-y-4">
      <PageHeader
        title="Market Overview"
        description="Global energy complex · cross-asset intelligence"
        status={isError ? 'warning' : live ? 'live' : 'pre'}
        actions={
          <>
            <Button variant="outline" size="sm"><Layers className="h-3.5 w-3.5" />Layout</Button>
            <Button variant="primary" size="sm" onClick={() => refetch()}>
              <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? 'animate-spin' : ''}`} />Refresh
            </Button>
          </>
        }
      />

      {/* Hero metrics — live from Yahoo via backend, static fallback for JKM */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7">
        {heroMetrics.map((m, i) => (
          <MetricCard key={m.id} data={m} delay={isLoading ? 0 : i * 0.04} />
        ))}
      </div>

      {/* Middle: charts + right rail */}
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <div className="space-y-4 xl:col-span-2">
          <div className="h-[300px]">
            <LivePriceChart defaultId="brent" />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <div className="h-[290px]">
              <CrossCommodityCard />
            </div>
            <div className="h-[290px]">
              <ForwardCurveCard id="brent" />
            </div>
          </div>
        </div>

        {/* Right rail */}
        <div className="space-y-4">
          <div className="h-[300px]"><NewsFeed limit={5} onSelect={setSelectedNews} /></div>
          <div className="h-[290px]"><AlertsSummary /></div>
        </div>
      </div>

      {/* Correlation + movers + calendar */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader title="Correlation Matrix" subtitle="30-day rolling · cross-asset" />
          <div className="p-3">
            <CorrelationHeatmap matrix={corrMatrix} assets={corrAssets} />
          </div>
        </Card>
        <div className="h-full min-h-[260px]"><MarketMovers /></div>
        <div className="h-full min-h-[260px]"><EconomicCalendar /></div>
      </div>

      {/* Bottom: inventory + freight + weather placeholder */}
      <SectionTitle>Physical Markets Snapshot</SectionTitle>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="h-[260px]">
          <ChartCard title="US Crude Inventories" subtitle="EIA weekly · M bbl" defaultRange="12W">
            <BarChartPro data={crudeInventory} color="#06b6d4" height={170} />
          </ChartCard>
        </div>
        <div className="h-[260px]"><ShippingCongestion /></div>
        <WeatherRiskPanel />
      </div>

      <div className="min-h-[180px]"><RigCount compact /></div>

      <NewsModal newsId={selectedNews} onClose={() => setSelectedNews(null)} />
    </div>
  );
}

function WeatherRiskPanel() {
  const regions = [
    { name: 'US Midwest', risk: 'High', color: 'bg-red-500', anomaly: '-3.2°C' },
    { name: 'NW Europe', risk: 'Low', color: 'bg-green-500', anomaly: '-0.8°C' },
    { name: 'NE Asia', risk: 'Medium', color: 'bg-amber-500', anomaly: '+1.6°C' },
    { name: 'US Gulf', risk: 'Medium', color: 'bg-amber-500', anomaly: '+2.4°C' },
  ];
  return (
    <Card className="flex h-[260px] flex-col">
      <CardHeader title="Weather Risk Map" subtitle="Temperature anomaly heat" />
      <div className="relative flex-1 overflow-hidden p-3">
        <div className="absolute inset-0 opacity-[0.07]" style={{ backgroundImage: 'radial-gradient(circle at 30% 40%, #ef4444 0%, transparent 25%), radial-gradient(circle at 70% 60%, #f59e0b 0%, transparent 30%), radial-gradient(circle at 50% 80%, #10b981 0%, transparent 20%)' }} />
        <div className="relative grid grid-cols-2 gap-2">
          {regions.map((r) => (
            <div key={r.name} className="rounded-md border border-[#1f2230] bg-[#0a0b0d]/60 p-2.5">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-medium text-slate-200">{r.name}</span>
                <span className={`h-2 w-2 rounded-full ${r.color}`} />
              </div>
              <p className="mono mt-1.5 text-sm font-semibold text-slate-100">{r.anomaly}</p>
              <p className="text-[9px] uppercase tracking-wide text-slate-500">{r.risk} impact</p>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}
