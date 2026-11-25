import { useQuery } from "@tanstack/react-query";
import { ApiError } from "@/shared/api/errors";
import { usePollingBudget } from "@/shared/lib/usePollingBudget";
import { fetchPosting } from "../api";
import { gapKeys } from "../queryKeys";
import { ANALYSIS_POLL_MS, ANALYSIS_POLLS } from "./usePostings";

/** A 404 is an answer (posting deleted or unknown): no need to ask again. */
const retryUnlessMissing = (count: number, error: Error) =>
  !(error instanceof ApiError && error.status === 404) && count < 1;

/**
 * `GET /postings/{id}`. While the analysis runs (`analyzing`), the posting is re-read every
 * `pollMs`, at most 40 times. The « probable » and « possible » duplicates come with the analysis
 * (G35): this re-read brings them in.
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
