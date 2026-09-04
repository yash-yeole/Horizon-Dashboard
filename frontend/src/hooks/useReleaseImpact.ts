import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { ReleaseImpactResponse } from '@/types';

/** Inventory-release impact assessment for the upcoming weekly EIA crude print.
 *  Live surprise inputs + a snapshot of the validated research model. Cached
 *  server-side (15 min); the call doesn't change intraday. */
export function useReleaseImpact() {
  return useQuery<ReleaseImpactResponse>({
    queryKey: ['release-impact'],
    queryFn: ({ signal }) => api.releaseImpact(signal),
    staleTime: 15 * 60_000,
    refetchInterval: 15 * 60_000,
    retry: 1,
  });
}
