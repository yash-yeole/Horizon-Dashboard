import { useState } from 'react';
import { RefreshCw, Layers } from 'lucide-react';
import { PageHeader } from '@/components/widgets/PageHeader';
import { MetricCard } from '@/components/widgets/MetricCard';
import { Card, CardHeader } from '@/components/ui/Card';
import { Button } from '@/components/ui';
import { LivePriceChart } from '@/components/widgets/LivePriceChart';
import { ForwardCurveCard } from '@/components/widgets/ForwardCurveCard';
import { StructureCurveCard } from '@/components/widgets/StructureCurveCard';
import { CrossCommodityCard } from '@/components/widgets/CrossCommodityCard';
import { CorrelationHeatmap } from '@/components/charts/Heatmap';
import {
  NewsFeed, EconomicCalendar, AlertsSummary,
} from '@/components/widgets/Panels';
import { NewsModal } from '@/components/widgets/NewsModal';
import { RigCount } from '@/components/widgets/RigCount';
import { ReleaseImpactCard } from '@/components/widgets/ReleaseImpact';
import { HERO_METRICS } from '@/data/market';
import { correlationMatrix, CORRELATION_ASSETS } from '@/data/series';
import { useQuotes, mergeQuotes } from '@/hooks/useQuotes';
import { useCorrelation } from '@/hooks/useHistory';

export function Dashboard() {
  const [selectedNews, setSelectedNews] = useState<string | null>(null);
  const { data, isLoading, isError, refetch, isFetching } = useQuotes('all');

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

      {/* Active alerts — horizontal bar in the space the page header vacated */}
      <AlertsSummary horizontal />

      {/* Hero metrics — live from Yahoo via backend, static fallback for JKM */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7">
        {heroMetrics.map((m, i) => (
          <MetricCard key={m.id} data={m} delay={isLoading ? 0 : i * 0.04} />
        ))}
      </div>

      {/* Middle: live chart + news rail */}
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <div className="h-[320px] xl:col-span-2"><LivePriceChart defaultId="brent" /></div>
        <div className="h-[320px]"><NewsFeed limit={5} onSelect={setSelectedNews} /></div>
      </div>

      {/* EIA release impact — compact call, links to the full analysis on Inventories */}
      <ReleaseImpactCard />

      {/* Term structure: forward curve · calendar spreads · butterflies (full width) */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="h-[340px]"><ForwardCurveCard id="brent" selectable height={250} /></div>
        <div className="h-[340px]"><StructureCurveCard mode="spreads" height={250} /></div>
        <div className="h-[340px]"><StructureCurveCard mode="flys" height={250} /></div>
      </div>

      {/* Correlation | Rig count (moved up, paired) */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title="Correlation Matrix" subtitle="30-day rolling · cross-asset" />
          <div className="p-3">
            <CorrelationHeatmap matrix={corrMatrix} assets={corrAssets} />
          </div>
        </Card>
        <div className="min-h-[260px]"><RigCount compact /></div>
      </div>

      {/* Cross-commodity + calendar */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="h-full min-h-[260px]"><CrossCommodityCard /></div>
        <div className="h-full min-h-[260px]"><EconomicCalendar /></div>
      </div>

      <NewsModal newsId={selectedNews} onClose={() => setSelectedNews(null)} />
    </div>
  );
}

