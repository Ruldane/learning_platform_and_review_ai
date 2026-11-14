import { useQuery } from "@tanstack/react-query";
import { ApiError } from "@/shared/api/errors";
import { usePollingBudget } from "@/shared/lib/usePollingBudget";
import { fetchPosting } from "../api";
import { gapKeys } from "../queryKeys";
import { ANALYSIS_POLL_MS, ANALYSIS_POLLS } from "./usePostings";

/** Un 404 est une réponse (offre supprimée ou inconnue) : inutile de la redemander. */
const retryUnlessMissing = (count: number, error: Error) =>
  !(error instanceof ApiError && error.status === 404) && count < 1;

/**
 * `GET /postings/{id}`. Tant que l'analyse tourne (`analyzing`), l'offre est relue toutes les
 * `pollMs`, 40 fois au plus. Les doublons « probable » et « possible » arrivent avec l'analyse
 * (G35) : cette relecture les apporte.
 */
export function usePosting(postingId: string, pollMs = ANALYSIS_POLL_MS) {
  const budget = usePollingBudget(ANALYSIS_POLLS);
  const { spend } = budget;
  const query = useQuery({
    queryKey: gapKeys.posting(postingId),
    queryFn: async ({ signal }) => {
      const posting = await fetchPosting(postingId, signal);
      if (posting.status === "analyzing") spend();
      return posting;
    },
    refetchInterval: (state) =>
      state.state.data?.status === "analyzing" && !budget.exhausted ? pollMs : false,
    retry: retryUnlessMissing,
  });
  return { query, budget };
}
