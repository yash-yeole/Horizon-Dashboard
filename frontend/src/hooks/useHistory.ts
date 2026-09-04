import { useQueries } from '@tanstack/react-query';
import { api } from '@/lib/api';
import {
  buildCorrelation, buildRebased, fmtDate, type AssetDef, type HistMap,
} from '@/lib/analytics';

/** Fetch daily history for several instruments at once (shared/deduped by react-query). */
export function useHistories(ids: string[], range = '3mo') {
  const results = useQueries({
    queries: ids.map((id) => ({
      queryKey: ['history', id, range],
      queryFn: ({ signal }: { signal: AbortSignal }) => api.history(id, range, signal),
      staleTime: 5 * 60_000,
    })),
  });
  const byId: HistMap = {};
  ids.forEach((id, i) => {
    const pts = results[i].data?.points;
    if (pts?.length) byId[id] = pts;
  });
  return { byId, isLoading: results.some((r) => r.isLoading) };
}

// Live instruments we can correlate (Gas Oil has no free feed, so it's dropped).
export const CORR_ASSETS: AssetDef[] = [
  { id: 'brent', label: 'Brent' }, { id: 'wti', label: 'WTI' }, { id: 'rbob', label: 'RBOB' },
  { id: 'heatoil', label: 'HO' }, { id: 'dxy', label: 'DXY' }, { id: 'vix', label: 'VIX' }, { id: 'sp500', label: 'S&P' },
];

/** Live cross-asset correlation matrix from daily returns. */
export function useCorrelation(range = '3mo') {
  const { byId, isLoading } = useHistories(CORR_ASSETS.map((a) => a.id), range);
  const built = buildCorrelation(byId, CORR_ASSETS);
  return { matrix: built?.matrix, labels: built?.labels, isLoading };
}

export const ENERGY_ASSETS: AssetDef[] = [
  { id: 'brent', label: 'Brent' }, { id: 'wti', label: 'WTI' },
  { id: 'rbob', label: 'RBOB' }, { id: 'heatoil', label: 'Heating Oil' },
];

/** Live energy-complex prices rebased to 100, plus the raw series for vol etc. */
export function useComparison(range = '3mo') {
  const { byId, isLoading } = useHistories(ENERGY_ASSETS.map((a) => a.id), range);
  return { data: buildRebased(byId, ENERGY_ASSETS), byId, isLoading };
}

/** Single instrument history mapped to {time,value} for area/line charts. */
export function useSeries(id: string, range = '3mo') {
  const { byId, isLoading } = useHistories([id], range);
  const data = (byId[id] ?? []).map((p) => ({ time: fmtDate(p.time), value: p.value }));
  return { data, isLoading };
}
