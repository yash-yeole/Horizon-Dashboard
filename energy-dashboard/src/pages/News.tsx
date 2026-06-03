import { useState, useMemo } from 'react';
import { Clock, Search, Filter } from 'lucide-react';
import { PageHeader } from '@/components/widgets/PageHeader';
import { Card, CardHeader } from '@/components/ui/Card';
import { SentimentBadge, ImportanceBadge, Badge } from '@/components/ui/Badge';
import { Tabs, FilterBar, Button } from '@/components/ui';
import { NewsModal } from '@/components/widgets/NewsModal';
import { useNews } from '@/hooks/useQuotes';
import { motion } from 'framer-motion';

const CATEGORIES = [
  { id: 'all', label: 'All' },
  { id: 'Crude', label: 'Crude' },
  { id: 'Products', label: 'Products' },
  { id: 'Freight', label: 'Freight' },
  { id: 'Macro', label: 'Macro' },
  { id: 'Weather', label: 'Weather' },
];

export function News() {
  const [cat, setCat] = useState('all');
  const [sentiment, setSentiment] = useState<'all' | 'bullish' | 'bearish'>('all');
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState<string | null>(null);

  const { items: news, isLive } = useNews(60);

  const filtered = useMemo(() => {
    return news.filter((n) =>
      (cat === 'all' || n.category === cat) &&
      (sentiment === 'all' || n.sentiment === sentiment) &&
      (query === '' || n.headline.toLowerCase().includes(query.toLowerCase()))
    );
  }, [news, cat, sentiment, query]);

  const sentimentStats = useMemo(() => {
    const bull = news.filter((n) => n.sentiment === 'bullish').length;
    const bear = news.filter((n) => n.sentiment === 'bearish').length;
    const total = news.length;
    return { bull, bear, neutral: total - bull - bear, total };
  }, [news]);

  return (
    <div className="space-y-4">
      <PageHeader title="News & Sentiment" description="Real-time market wire · categorized streams · sentiment analytics" />

      {/* Sentiment overview */}
      <div className="grid grid-cols-3 gap-3">
        <Card className="p-3">
          <p className="text-[10px] uppercase tracking-wide text-slate-500">Bullish Signals</p>
          <p className="mono mt-1 text-xl font-bold text-green-400">{sentimentStats.bull}</p>
          <div className="mt-1.5 h-1 overflow-hidden rounded bg-[#1c1e27]"><div className="h-full bg-green-500" style={{ width: `${(sentimentStats.bull / sentimentStats.total) * 100}%` }} /></div>
        </Card>
        <Card className="p-3">
          <p className="text-[10px] uppercase tracking-wide text-slate-500">Bearish Signals</p>
          <p className="mono mt-1 text-xl font-bold text-red-400">{sentimentStats.bear}</p>
          <div className="mt-1.5 h-1 overflow-hidden rounded bg-[#1c1e27]"><div className="h-full bg-red-500" style={{ width: `${(sentimentStats.bear / sentimentStats.total) * 100}%` }} /></div>
        </Card>
        <Card className="p-3">
          <p className="text-[10px] uppercase tracking-wide text-slate-500">Net Sentiment</p>
          <p className="mono mt-1 text-xl font-bold text-slate-200">{sentimentStats.bull > sentimentStats.bear ? 'Bullish' : 'Bearish'}</p>
          <p className="text-[10px] text-slate-500">{sentimentStats.total} stories · 24h</p>
        </Card>
      </div>

      <FilterBar>
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-600" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Filter headlines…"
            className="h-7 w-full rounded border border-[#1f2230] bg-[#0a0b0d] pl-8 pr-3 text-[11px] text-slate-200 placeholder:text-slate-600 focus:border-blue-500/40 focus:outline-none"
          />
        </div>
        <Tabs tabs={CATEGORIES} value={cat} onChange={setCat} />
        <span className="h-4 w-px bg-[#1f2230]" />
        <Tabs
          tabs={[{ id: 'all', label: 'All' }, { id: 'bullish', label: 'Bull' }, { id: 'bearish', label: 'Bear' }]}
          value={sentiment}
          onChange={(v) => setSentiment(v as typeof sentiment)}
        />
        <Button variant="ghost" size="sm"><Filter className="h-3.5 w-3.5" />More</Button>
      </FilterBar>

      {/* Timeline feed */}
      <Card>
        <CardHeader title="Market Wire" subtitle={`${filtered.length} stories`} action={<Badge variant={isLive ? 'green' : 'amber'} dot>{isLive ? 'FinancialJuice · Live' : 'Demo · cached'}</Badge>} />
        <div className="divide-y divide-[#161820]">
          {filtered.map((n, i) => (
            <motion.button
              key={n.id}
              initial={{ opacity: 0, x: -6 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.03 }}
              onClick={() => setSelected(n.id)}
              className="flex w-full gap-4 px-4 py-3 text-left transition-colors hover:bg-[#13151c]"
            >
              {/* Timeline node */}
              <div className="flex flex-col items-center pt-1">
                <span className={`h-2 w-2 rounded-full ${n.sentiment === 'bullish' ? 'bg-green-400' : n.sentiment === 'bearish' ? 'bg-red-400' : 'bg-slate-500'}`} />
                <span className="mt-1 w-px flex-1 bg-[#1f2230]" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="mb-1 flex flex-wrap items-center gap-1.5">
                  <SentimentBadge sentiment={n.sentiment} />
                  <ImportanceBadge importance={n.importance} />
                  <Badge variant="blue">{n.category}</Badge>
                  <span className="text-[9px] font-medium text-slate-500">{n.source}</span>
                  <span className="ml-auto flex items-center gap-1 text-[9px] text-slate-600"><Clock className="h-2.5 w-2.5" />{n.timestamp}</span>
                </div>
                <p className="text-[13px] font-medium leading-snug text-slate-100">{n.headline}</p>
                <p className="mt-0.5 text-[11px] text-slate-500 line-clamp-1">{n.summary}</p>
                <div className="mt-1.5 flex gap-1.5">
                  {n.tags.map((t) => <span key={t} className="rounded bg-[#161820] px-1.5 py-0.5 text-[9px] text-slate-500">{t}</span>)}
                </div>
              </div>
            </motion.button>
          ))}
        </div>
      </Card>

      <NewsModal newsId={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
