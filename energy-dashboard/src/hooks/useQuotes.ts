import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query';
import { api } from '@/services/api';
import type { ApiQuote, QuoteGroup, CurveCompare } from '@/types/api';
import type { Commodity, NewsItem } from '@/types';
import { NEWS } from '@/data/content';
import { formatCompact } from '@/lib/utils';

export type NewsFeedItem = NewsItem & { link?: string; publishedAt?: number | null };

function relTime(publishedAt: number | null | undefined, fallback: string): string {
  if (!publishedAt) return fallback;
  const secs = Date.now() / 1000 - publishedAt;
  if (secs < 60) return 'just now';
  if (secs < 3600) return `${Math.floor(secs / 60)}m ago`;
  if (secs < 86400) return `${Math.floor(secs / 3600)}h ago`;
  return `${Math.floor(secs / 86400)}d ago`;
}

/** Live energy news (FinancialJuice RSS). Auto-refreshes; falls back to static NEWS. */
export function useNews(limit = 40) {
  const query = useQuery({
    queryKey: ['news', limit],
    queryFn: ({ signal }) => api.news(limit, signal),
    staleTime: 90_000,
    refetchInterval: 90_000,
    retry: 1,
  });
  const live = !!query.data?.items?.length && !query.data.stale;
  const items: NewsFeedItem[] = live
    ? query.data!.items.map((i) => ({ ...i, timestamp: relTime(i.publishedAt, i.timestamp) }))
    : (NEWS as NewsFeedItem[]);
  return { ...query, items, isLive: live };
}

const REFETCH_MS = 30_000;

/** Live quotes for a group. Falls back silently to `placeholderData` between fetches. */
export function useQuotes(group: QuoteGroup = 'core') {
  return useQuery({
    queryKey: ['quotes', group],
    queryFn: ({ signal }) => api.quotes(group, signal),
    refetchInterval: REFETCH_MS,
    staleTime: REFETCH_MS / 2,
  });
}

export function useHistory(id: string, range = '3mo') {
  return useQuery({
    queryKey: ['history', id, range],
    queryFn: ({ signal }) => api.history(id, range, signal),
    staleTime: 60_000,
  });
}

/**
 * Weekly EIA petroleum inventories. EIA updates only once a week, so we never
 * auto-poll: fetch once, then serve cached data with no expiry. The only way to
 * hit the API again is `refresh()` (wired to the Refresh button), which forces a
 * fresh server pull and reloads every EIA view. Falls back to static demo data
 * on error.
 */
export function useEiaInventories(weeks = 24) {
  const qc = useQueryClient();

  const query = useQuery({
    queryKey: ['eia', 'inventories', weeks],
    queryFn: ({ signal }) => api.eiaInventories(weeks, false, signal),
    staleTime: Infinity,
    gcTime: Infinity,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    retry: 1,
  });

  const refreshMutation = useMutation({
    // refresh=true makes the server re-pull from EIA and persist the snapshot...
    mutationFn: () => api.eiaInventories(weeks, true),
    onSuccess: (fresh) => {
      qc.setQueryData(['eia', 'inventories', weeks], fresh);
      // ...then reload any other EIA views (e.g. Dashboard) from the new snapshot.
      qc.invalidateQueries({ queryKey: ['eia'] });
    },
  });

  return { ...query, refresh: refreshMutation.mutate, isRefreshing: refreshMutation.isPending };
}

/** Baker Hughes rig count (NA weekly + International monthly). Fetch-once + Refresh. */
export function useRigCount() {
  const qc = useQueryClient();
  const query = useQuery({
    queryKey: ['rigcount'],
    queryFn: ({ signal }) => api.rigCount(false, signal),
    staleTime: Infinity,
    gcTime: Infinity,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    retry: 1,
  });
  const refreshMutation = useMutation({
    mutationFn: () => api.rigCount(true),
    onSuccess: (fresh) => qc.setQueryData(['rigcount'], fresh),
  });
  return { ...query, refresh: refreshMutation.mutate, isRefreshing: refreshMutation.isPending };
}

/** CFTC Commitments of Traders positioning (weekly). */
export function useCftcPositioning(weeks = 52) {
  return useQuery({
    queryKey: ['cftc', weeks],
    queryFn: ({ signal }) => api.cftcPositioning(weeks, signal),
    staleTime: 30 * 60_000,
    retry: 1,
  });
}

/** Forward curve for a commodity, sourced from the backend's settlement CSV. */
export function useCurve(id: string, compare: CurveCompare = 'now') {
  return useQuery({
    queryKey: ['curve', id, compare],
    queryFn: ({ signal }) => api.curve(id, compare, signal),
    staleTime: 5 * 60_000,
  });
}

/** Single live quote selected out of a group (shares the cached group query). */
export function useQuote(id: string, group: QuoteGroup = 'all') {
  const q = useQuotes(group);
  return { ...q, quote: q.data?.quotes.find((x) => x.id === id) };
}

/** Convert an ApiQuote into the frontend Commodity card shape. */
export function quoteToCommodity(q: ApiQuote, fallbackSymbol?: string): Commodity {
  return {
    id: q.id,
    name: q.name,
    symbol: fallbackSymbol ?? q.yahooSymbol,
    price: q.price,
    change: q.change,
    changePct: q.changePct,
    high: q.high ?? q.price,
    low: q.low ?? q.price,
    volume: q.volume != null ? formatCompact(q.volume) : '—',
    unit: q.unit,
    currency: q.currency,
    category: (q.category as Commodity['category']) ?? 'macro',
    sparkline: q.sparkline.length ? q.sparkline : [q.price],
  };
}

/**
 * Merge live quotes into a static list of Commodity cards by id.
 *
 * The static card owns presentation (name, symbol, unit, currency, category);
 * the live quote provides the market data (price, change, high/low, volume,
 * sparkline). Static entries with no matching live quote are left untouched —
 * the fallback for instruments Yahoo doesn't provide (e.g. Gas Oil).
 */
export function mergeQuotes(statics: Commodity[], live: ApiQuote[] | undefined): Commodity[] {
  if (!live?.length) return statics;
  const byId = new Map(live.map((q) => [q.id, q]));
  return statics.map((s) => {
    const q = byId.get(s.id);
    if (!q) return s;
    return {
      ...s,
      price: q.price,
      change: q.change,
      changePct: q.changePct,
      high: q.high ?? s.high,
      low: q.low ?? s.low,
      volume: q.volume != null ? formatCompact(q.volume) : s.volume,
      sparkline: q.sparkline.length ? q.sparkline : s.sparkline,
    };
  });
}
