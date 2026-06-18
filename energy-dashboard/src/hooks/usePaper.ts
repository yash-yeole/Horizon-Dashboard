import { useQuery } from '@tanstack/react-query';
import { api } from '@/services/api';

/** Full snapshot for every tradeable structure (regime, fair value, signal, trades). */
export function usePaperState(refresh = false) {
  return useQuery({
    queryKey: ['paper', 'state', refresh],
    queryFn: ({ signal }) => api.paperState(refresh, signal),
    staleTime: 15_000,
    refetchInterval: 60_000,
  });
}

/** Cached full-history intraday backtest (model engine, flat 1-contract). Static. */
export function usePaperBacktest(enabled = true) {
  return useQuery({
    queryKey: ['paper', 'backtest'],
    queryFn: ({ signal }) => api.paperBacktest(signal),
    staleTime: Infinity,
    enabled,
  });
}
