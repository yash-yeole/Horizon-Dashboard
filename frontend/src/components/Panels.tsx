import { TrendingUp, TrendingDown, Clock, AlertTriangle, Anchor } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Card, CardHeader } from '@/components/Card';
import { Badge, ImpactBadge, ThemeBadge } from '@/components/Badge';
import { Sparkline } from '@/components/charts';
import { cn, formatPercent } from '@/lib/utils';
import { PORT_CONGESTION } from '@/data/content';
import { TOP_GAINERS, TOP_LOSERS, type MarketMover } from '@/data/market';
import { SPREADS } from '@/data/series';
import type { SpreadData, CalendarEvent } from '@/types';
import { useQuotes, useNews, useCalendar } from '@/hooks/useQuotes';
import { newsSentimentIndex } from '@/lib/sentiment';
import { useAlerts } from '@/components/AlertsProvider';
import { useMemo } from 'react';

/* ---------------- News Sentiment Gauge ---------------- */
export function SentimentGauge({ compact = false }: { compact?: boolean }) {
  const { items: news } = useNews();
  const sent = useMemo(() => newsSentimentIndex(news), [news]);
  return (
    <Card className={compact ? 'p-2.5' : 'p-3'}>
      <div className="flex items-center justify-between">
        <p className="text-[10px] uppercase tracking-wide text-slate-500">News Sentiment · 24h</p>
        <span className={cn('mono text-sm font-bold', sent.score > 0 ? 'text-green-400' : sent.score < 0 ? 'text-red-400' : 'text-slate-300')}>
          {sent.label} · {sent.score > 0 ? '+' : ''}{sent.score}
        </span>
      </div>
      <div className="relative mt-2 h-2 rounded bg-[#1c1e27]">
        <span className="absolute left-1/2 top-0 h-full w-px bg-slate-600" />
        <div
          className={cn('absolute top-0 h-full rounded', sent.score >= 0 ? 'bg-green-500' : 'bg-red-500')}
          style={sent.score >= 0
            ? { left: '50%', width: `${Math.min(50, sent.score / 2)}%` }
            : { right: '50%', width: `${Math.min(50, -sent.score / 2)}%` }}
        />
      </div>
      <p className="mt-1 text-[10px] text-slate-500">{sent.bull} bull · {sent.bear} bear · {sent.neutral} neutral · {sent.total} events</p>
    </Card>
  );
}

/* ---------------- News Feed ---------------- */
export function NewsFeed({ limit, onSelect }: { limit?: number; onSelect?: (id: string) => void }) {
  const { items: news } = useNews();
  const items = limit ? news.slice(0, limit) : news;
  const sent = useMemo(() => newsSentimentIndex(news), [news]);
  return (
    <Card className="flex h-full flex-col">
      <CardHeader title="Breaking News" subtitle="Real-time market wire" icon={<span className="h-1.5 w-1.5 rounded-full bg-red-500 pulse-dot inline-block" />} />
      {/* News sentiment meter */}
      <div className="border-b border-[#161820] px-3 py-2">
        <div className="flex items-center justify-between">
          <span className="text-[9px] uppercase tracking-wide text-slate-500">News Sentiment · 24h</span>
          <span className={cn('mono text-[11px] font-bold', sent.score > 0 ? 'text-green-400' : sent.score < 0 ? 'text-red-400' : 'text-slate-300')}>
            {sent.label} · {sent.score > 0 ? '+' : ''}{sent.score}
          </span>
        </div>
        <div className="relative mt-1.5 h-1.5 rounded bg-[#1c1e27]">
          <span className="absolute left-1/2 top-0 h-full w-px bg-slate-600" />
          <div
            className={cn('absolute top-0 h-full rounded', sent.score >= 0 ? 'bg-green-500' : 'bg-red-500')}
            style={sent.score >= 0
              ? { left: '50%', width: `${Math.min(50, sent.score / 2)}%` }
              : { right: '50%', width: `${Math.min(50, -sent.score / 2)}%` }}
          />
        </div>
      </div>
      <div className="flex-1 divide-y divide-[#161820] overflow-y-auto">
        {items.map((n) => (
          <button
            key={n.id}
            onClick={() => onSelect?.(n.id)}
            className="block w-full px-3 py-2.5 text-left transition-colors hover:bg-[#13151c]"
          >
            <div className="mb-1 flex items-center gap-1.5">
              <ImpactBadge impact={n.impact} />
              <ThemeBadge theme={n.themePrimary} />
              <span className="text-[9px] text-slate-600">{n.source}</span>
              <span className="ml-auto flex items-center gap-1 text-[9px] text-slate-600">
                <Clock className="h-2.5 w-2.5" />
                {n.timestamp}
              </span>
            </div>
            <p className="text-[12px] font-medium leading-snug text-slate-200 line-clamp-2">{n.headline}</p>
          </button>
        ))}
      </div>
    </Card>
  );
}

/* ---------------- Market Movers ---------------- */
function MoverRow({ m, up }: { m: MarketMover; up: boolean }) {
  return (
    <div className="flex items-center justify-between px-3 py-1.5 transition-colors hover:bg-[#13151c]">
      <div className="flex items-center gap-2">
        <span className={cn('flex h-5 w-5 items-center justify-center rounded', up ? 'bg-green-500/10' : 'bg-red-500/10')}>
          {up ? <TrendingUp className="h-3 w-3 text-green-400" /> : <TrendingDown className="h-3 w-3 text-red-400" />}
        </span>
        <div>
          <p className="text-[11px] font-medium text-slate-200">{m.name}</p>
          <p className="text-[9px] text-slate-600">{m.symbol}</p>
        </div>
      </div>
      <div className="text-right">
        <p className="mono text-[11px] text-slate-300">{m.price.toLocaleString()}</p>
        <p className={cn('mono text-[10px]', up ? 'text-green-400' : 'text-red-400')}>{formatPercent(m.changePct)}</p>
      </div>
    </div>
  );
}

export function MarketMovers() {
  const { data } = useQuotes('all');
  const quotes = data?.quotes ?? [];

  let gainers = TOP_GAINERS;
  let losers = TOP_LOSERS;
  if (quotes.length) {
    const movers: MarketMover[] = quotes.map((q) => ({
      name: q.name, symbol: q.yahooSymbol, changePct: q.changePct, price: q.price,
    }));
    gainers = [...movers].filter((m) => m.changePct >= 0).sort((a, b) => b.changePct - a.changePct).slice(0, 5);
    losers = [...movers].filter((m) => m.changePct < 0).sort((a, b) => a.changePct - b.changePct).slice(0, 5);
  }

  return (
    <Card className="flex h-full flex-col">
      <CardHeader title="Market Movers" subtitle="Top % change · 24h" />
      <div className="grid flex-1 grid-cols-2 divide-x divide-[#1f2230]">
        <div>
          <p className="px-3 py-1.5 text-[9px] font-semibold uppercase tracking-wider text-green-400/70">Gainers</p>
          {gainers.map((m) => <MoverRow key={m.symbol} m={m} up />)}
        </div>
        <div>
          <p className="px-3 py-1.5 text-[9px] font-semibold uppercase tracking-wider text-red-400/70">Losers</p>
          {losers.map((m) => <MoverRow key={m.symbol} m={m} up={false} />)}
        </div>
      </div>
    </Card>
  );
}

/* ---------------- Economic Calendar ---------------- */
const CAT_COLORS: Record<string, string> = {
  EIA: 'text-cyan-400',
  CFTC: 'text-purple-400',
  OPEC: 'text-amber-400',
  IEA: 'text-blue-400',
  BakerHughes: 'text-green-400',
};
const CAT_DOT: Record<string, string> = {
  EIA: 'bg-cyan-400',
  CFTC: 'bg-purple-400',
  OPEC: 'bg-amber-400',
  IEA: 'bg-blue-400',
  BakerHughes: 'bg-green-400',
};

function calendarDateLabel(dateStr: string): string {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const d = new Date(dateStr + 'T00:00:00');
  const diff = Math.round((d.getTime() - today.getTime()) / 86400000);
  if (diff === 0) return 'Today';
  if (diff === 1) return 'Tomorrow';
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export function EconomicCalendar() {
  const { data: events, isLoading } = useCalendar(30);

  // Group events by date, take first 12 entries to keep widget compact.
  const grouped = useMemo(() => {
    if (!events?.length) return [];
    const map = new Map<string, CalendarEvent[]>();
    for (const e of events.slice(0, 14)) {
      const arr = map.get(e.date) ?? [];
      arr.push(e);
      map.set(e.date, arr);
    }
    return [...map.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [events]);

  return (
    <Card className="flex h-full flex-col">
      <CardHeader title="Energy Calendar" subtitle="Next 30 days · key releases" />
      <div className="flex-1 overflow-y-auto divide-y divide-[#161820]">
        {isLoading && (
          <p className="px-3 py-4 text-[10px] text-slate-600">Loading calendar…</p>
        )}
        {!isLoading && !grouped.length && (
          <p className="px-3 py-4 text-[10px] text-slate-600">No events found.</p>
        )}
        {grouped.map(([date, evts]) => (
          <div key={date}>
            <p className="sticky top-0 z-10 bg-[#0a0b0d] px-3 py-1 text-[9px] font-semibold uppercase tracking-widest text-slate-500">
              {calendarDateLabel(date)}
            </p>
            {evts.map((e, i) => (
              <div key={i} className="flex items-start gap-2.5 px-3 py-2 hover:bg-[#13151c]">
                <span className={cn('mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full', CAT_DOT[e.category] ?? 'bg-slate-500')} />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-[11px] font-medium text-slate-200">{e.title}</p>
                  <p className="truncate text-[9px] text-slate-600">{e.description}</p>
                </div>
                <div className="flex shrink-0 flex-col items-end gap-0.5">
                  {e.timeEt && (
                    <span className="mono text-[9px] text-slate-500">{e.timeEt} ET</span>
                  )}
                  <span className={cn('text-[9px] font-semibold', CAT_COLORS[e.category] ?? 'text-slate-400')}>
                    {e.category}
                  </span>
                  {e.isDelayed && (
                    <span className="text-[8px] text-amber-500">delayed</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        ))}
      </div>
    </Card>
  );
}

/* ---------------- Alerts Summary ---------------- */
export function AlertsSummary({ horizontal = false }: { horizontal?: boolean }) {
  const { fired, unread, rules } = useAlerts();
  const colors = { critical: 'text-red-400', warning: 'text-amber-400', info: 'text-blue-400' };

  if (horizontal) {
    return (
      <Card className="flex items-center gap-4 px-4 py-2.5">
        <div className="flex shrink-0 items-center gap-2.5">
          <AlertTriangle className="h-4 w-4 text-amber-400" />
          <div>
            <p className="text-[12px] font-semibold text-slate-100">Active Alerts</p>
            <p className="text-[9px] text-slate-500">{unread} unread · {rules.filter((r) => r.enabled).length} rules</p>
          </div>
        </div>
        <span className="h-8 w-px shrink-0 bg-[#1f2230]" />
        <div className="flex flex-1 items-center gap-2.5 overflow-x-auto">
          {fired.length === 0 && <p className="text-[10px] text-slate-600">No alerts triggered yet.</p>}
          {fired.slice(0, 6).map((a) => (
            <div
              key={a.id}
              className={cn('flex shrink-0 items-center gap-2 rounded-md border border-[#1f2230] bg-[#0f1117] px-2.5 py-1.5', !a.read && 'ring-1 ring-blue-500/20')}
            >
              <AlertTriangle className={cn('h-3.5 w-3.5 shrink-0', colors[a.severity])} />
              <div className="min-w-0">
                <p className="whitespace-nowrap text-[11px] font-medium text-slate-200">{a.title}</p>
                <p className="line-clamp-1 max-w-[220px] text-[9px] text-slate-500">{a.message}</p>
              </div>
            </div>
          ))}
        </div>
        <Link to="/alerts" className="shrink-0 text-[10px] font-medium text-blue-400 hover:underline">View all →</Link>
      </Card>
    );
  }

  return (
    <Card className="flex h-full flex-col">
      <CardHeader title="Active Alerts" subtitle={`${unread} unread · ${rules.filter((r) => r.enabled).length} rules`} />
      <div className="flex-1 divide-y divide-[#161820]">
        {fired.length === 0 && <p className="px-3 py-4 text-[10px] text-slate-600">No alerts triggered yet.</p>}
        {fired.slice(0, 5).map((a) => (
          <div key={a.id} className={cn('flex gap-2.5 px-3 py-2', !a.read && 'bg-blue-500/[0.03]')}>
            <AlertTriangle className={cn('mt-0.5 h-3.5 w-3.5 shrink-0', colors[a.severity])} />
            <div className="min-w-0">
              <p className="text-[11px] font-medium text-slate-200">{a.title}</p>
              <p className="text-[10px] text-slate-500 line-clamp-1">{a.message}</p>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

/* ---------------- Spread Monitor ---------------- */
export function SpreadMonitor({ spreads = SPREADS }: { spreads?: SpreadData[] }) {
  return (
    <Card className="flex h-full flex-col">
      <CardHeader title="Spread Monitor" subtitle="Key relationships" />
      <div className="flex-1 divide-y divide-[#161820]">
        {spreads.map((s) => (
          <div key={s.name} className="flex items-center gap-3 px-3 py-2">
            <div className="min-w-0 flex-1">
              <p className="text-[11px] font-medium text-slate-200">{s.name}</p>
            </div>
            <div className="h-6 w-16">
              <Sparkline data={s.history} color={s.change >= 0 ? '#10b981' : '#ef4444'} height={24} />
            </div>
            <div className="w-16 text-right">
              <p className="mono text-[12px] text-slate-200">{s.value.toFixed(2)}</p>
              <p className={cn('mono text-[10px]', s.change >= 0 ? 'text-green-400' : 'text-red-400')}>
                {s.change >= 0 ? '+' : ''}{s.change.toFixed(2)}
              </p>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

/* ---------------- Shipping Congestion ---------------- */
export function ShippingCongestion() {
  const sev = { high: 'red', medium: 'amber', low: 'green' } as const;
  return (
    <Card className="flex h-full flex-col">
      <CardHeader title="Port Congestion" subtitle="Vessels at anchor" icon={<Anchor className="h-3.5 w-3.5" />} />
      <div className="flex-1 divide-y divide-[#161820]">
        {PORT_CONGESTION.map((p) => (
          <div key={p.port} className="flex items-center gap-3 px-3 py-2">
            <div className="min-w-0 flex-1">
              <p className="text-[11px] font-medium text-slate-200">{p.port}</p>
              <p className="text-[9px] text-slate-600">{p.vessels} vessels · {p.waiting} waiting</p>
            </div>
            <Badge variant={sev[p.severity]} dot>{p.severity}</Badge>
          </div>
        ))}
      </div>
    </Card>
  );
}
