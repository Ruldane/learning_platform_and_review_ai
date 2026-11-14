import { useQuery } from "@tanstack/react-query";
import { usePollingBudget } from "@/shared/lib/usePollingBudget";
import { fetchGap } from "../api";
import { gapKeys } from "../queryKeys";
import { ANALYSIS_POLL_MS, ANALYSIS_POLLS } from "./usePostings";

/**
 * `GET /postings/{id}/gap`, lu une fois l'offre analysée (`enabled`). Tant que l'écart se calcule
 * (`pending`), il est relu toutes les `pollMs`, 40 fois au plus.
 */
export function useGap(postingId: string, enabled: boolean, pollMs = ANALYSIS_POLL_MS) {
  const budget = usePollingBudget(ANALYSIS_POLLS);
  const { spend } = budget;
  const query = useQuery({
    queryKey: gapKeys.gap(postingId),
    queryFn: async ({ signal }) => {
      const gap = await fetchGap(postingId, signal);
      if (gap.status === "pending") spend();
      return gap;
    },
    enabled,
    refetchInterval: (state) =>
      state.state.data?.status === "pending" && !budget.exhausted ? pollMs : false,
  });
  return { query, budget };
}
