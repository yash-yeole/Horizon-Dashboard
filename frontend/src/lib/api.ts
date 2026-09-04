import type {
  QuotesResponse, HistoryResponse, QuoteGroup, ApiQuote, CurveResponse, CurveCompare,
  CurveStructureResponse, CalendarEvent, ReleaseImpactResponse,
  EiaInventoryResponse, NewsResponse, CftcResponse, RigCountResponse, LeadLagResponse,
  VesselsResponse, ChokepointsResponse,
  PaperState, PaperStructure, PaperStructuresResponse, BacktestResult,
} from '@/types';

// In dev, Vite proxies /api -> http://localhost:8000 (see vite.config.ts).
// Override for other environments via VITE_API_BASE_URL.
const BASE = import.meta.env.VITE_API_BASE_URL ?? '';

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { signal });
  if (!res.ok) {
    throw new Error(`API ${path} failed: ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  quotes: (group: QuoteGroup = 'core', signal?: AbortSignal) =>
    getJson<QuotesResponse>(`/api/quotes?group=${group}`, signal),

  quote: (id: string, signal?: AbortSignal) =>
    getJson<ApiQuote>(`/api/quote/${id}`, signal),

  history: (id: string, range = '3mo', signal?: AbortSignal) =>
    getJson<HistoryResponse>(`/api/history/${id}?range=${range}`, signal),

  curve: (id: string, compare: CurveCompare = 'now', signal?: AbortSignal) =>
    getJson<CurveResponse>(`/api/curve/${id}?compare=${compare}`, signal),

  curveStructure: (id: string, signal?: AbortSignal) =>
    getJson<CurveStructureResponse>(`/api/curve/${id}/structure`, signal),

  eiaInventories: (weeks = 24, refresh = false, signal?: AbortSignal) =>
    getJson<EiaInventoryResponse>(`/api/eia/inventories?weeks=${weeks}&refresh=${refresh}`, signal),

  news: (limit = 40, signal?: AbortSignal) =>
    getJson<NewsResponse>(`/api/news?limit=${limit}`, signal),

  cftcPositioning: (weeks = 52, signal?: AbortSignal) =>
    getJson<CftcResponse>(`/api/cftc/positioning?weeks=${weeks}`, signal),

  rigCount: (refresh = false, signal?: AbortSignal) =>
    getJson<RigCountResponse>(`/api/rigcount?refresh=${refresh}`, signal),

  leadLag: (base = 'brent', timeframe = 'intraday', signal?: AbortSignal) =>
    getJson<LeadLagResponse>(`/api/leadlag?base=${base}&timeframe=${timeframe}`, signal),

  shippingVessels: (limit = 800, signal?: AbortSignal) =>
    getJson<VesselsResponse>(`/api/shipping/vessels?limit=${limit}`, signal),

  shippingChokepoints: (signal?: AbortSignal) =>
    getJson<ChokepointsResponse>('/api/shipping/chokepoints', signal),

  calendar: (days = 60, signal?: AbortSignal) =>
    getJson<CalendarEvent[]>(`/api/calendar?days=${days}`, signal),

  releaseImpact: (signal?: AbortSignal) =>
    getJson<ReleaseImpactResponse>('/api/release-impact', signal),

  paperStructures: (signal?: AbortSignal) =>
    getJson<PaperStructuresResponse>('/api/paper/structures', signal),

  paperState: (refresh = false, signal?: AbortSignal) =>
    getJson<PaperState>(`/api/paper/state?refresh=${refresh}`, signal),

  paperStructure: (key: string, refresh = false, signal?: AbortSignal) =>
    getJson<PaperStructure>(`/api/paper/${key}?refresh=${refresh}`, signal),

  paperBacktest: (signal?: AbortSignal) =>
    getJson<BacktestResult>('/api/paper/backtest/results', signal),
};
