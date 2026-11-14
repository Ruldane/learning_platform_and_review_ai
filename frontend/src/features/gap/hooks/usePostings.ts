import { useQuery } from "@tanstack/react-query";
import { usePollingBudget } from "@/shared/lib/usePollingBudget";
import { fetchPostings } from "../api";
import { gapKeys } from "../queryKeys";

/** Une analyse en cours est relue toutes les 3 s, 40 fois (deux minutes). */
export const ANALYSIS_POLLS = 40;
export const ANALYSIS_POLL_MS = 3000;

/**
 * `GET /postings`. Tant qu'une offre est en cours d'analyse, la liste est relue toutes les
 * `pollMs`, 40 fois au plus ; `budget.exhausted` dit que l'attente est trop longue.
 */
export function usePostings(pollMs = ANALYSIS_POLL_MS) {
  const budget = usePollingBudget(ANALYSIS_POLLS);
  const { spend } = budget;
  const query = useQuery({
    queryKey: gapKeys.postings,
    queryFn: async ({ signal }) => {
      const postings = await fetchPostings(signal);
      if (postings.some((posting) => posting.status === "analyzing")) spend();
      return postings;
    },
    refetchInterval: (state) =>
      state.state.data?.some((posting) => posting.status === "analyzing") && !budget.exhausted
        ? pollMs
        : false,
  });
  return { query, budget };
}
