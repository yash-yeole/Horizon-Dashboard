import { TrendingUp, TrendingDown, Clock, AlertTriangle, Info, Anchor } from 'lucide-react';
import { Card, CardHeader } from '@/components/ui/Card';
import { Badge, SentimentBadge } from '@/components/ui/Badge';
import { Sparkline } from '@/components/charts';
import { cn, formatPercent } from '@/lib/utils';
import { ECONOMIC_CALENDAR, ALERTS, PORT_CONGESTION } from '@/data/content';
import { TOP_GAINERS, TOP_LOSERS, type MarketMover } from '@/data/market';
import { SPREADS } from '@/data/series';
import type { SpreadData } from '@/types';
import { useQuotes, useNews } from '@/hooks/useQuotes';

/* ---------------- News Feed ---------------- */
export function NewsFeed({ limit, onSelect }: { limit?: number; onSelect?: (id: string) => void }) {
  const { items: news } = useNews();
  const items = limit ? news.slice(0, limit) : news;
  return (
    <Card className="flex h-full flex-col">
      <CardHeader title="Breaking News" subtitle="Real-time market wire" icon={<span className="h-1.5 w-1.5 rounded-full bg-red-500 pulse-dot inline-block" />} />
      <div className="flex-1 divide-y divide-[#161820] overflow-y-auto">
        {items.map((n) => (
          <button
            key={n.id}
            onClick={() => onSelect?.(n.id)}
            className="block w-full px-3 py-2.5 text-left transition-colors hover:bg-[#13151c]"
          >
            <div className="mb-1 flex items-center gap-1.5">
              <SentimentBadge sentiment={n.sentiment} />
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
export function EconomicCalendar() {
  return (
    <Card className="flex h-full flex-col">
      <CardHeader title="Economic Calendar" subtitle="Today · key releases" />
      <div className="flex-1 divide-y divide-[#161820]">
        {ECONOMIC_CALENDAR.map((e, i) => (
          <div key={i} className="flex items-center gap-2.5 px-3 py-2">
            <span className="mono text-[10px] text-slate-500 w-9">{e.time}</span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-[11px] text-slate-200">{e.event}</p>
              <p className="text-[9px] text-slate-600">Fcst {e.forecast} · Prev {e.previous}</p>
            </div>
            <Badge variant={e.impact === 'high' ? 'red' : 'amber'} dot>{e.impact}</Badge>
          </div>
        ))}
      </div>
    </Card>
  );
}

/* ---------------- Alerts Summary ---------------- */
export function AlertsSummary() {
  const icons = { critical: AlertTriangle, warning: AlertTriangle, info: Info };
  const colors = { critical: 'text-red-400', warning: 'text-amber-400', info: 'text-blue-400' };
  return (
    <Card className="flex h-full flex-col">
      <CardHeader title="Active Alerts" subtitle={`${ALERTS.filter((a) => !a.read).length} unread`} />
      <div className="flex-1 divide-y divide-[#161820]">
        {ALERTS.slice(0, 5).map((a) => {
          const Ico = icons[a.severity];
          return (
            <div key={a.id} className={cn('flex gap-2.5 px-3 py-2', !a.read && 'bg-blue-500/[0.03]')}>
              <Ico className={cn('mt-0.5 h-3.5 w-3.5 shrink-0', colors[a.severity])} />
              <div className="min-w-0">
                <p className="text-[11px] font-medium text-slate-200">{a.title}</p>
                <p className="text-[10px] text-slate-500 line-clamp-1">{a.message}</p>
                <p className="mt-0.5 text-[9px] text-slate-600">{a.timestamp}</p>
              </div>
            </div>
          );
        })}
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
