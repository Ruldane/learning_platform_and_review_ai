import { useQuery } from "@tanstack/react-query";
import { ApiError } from "@/shared/api/errors";
import { fetchReview } from "../api";
import { cvKeys } from "../queryKeys";
import type { CvReviewOut } from "../types";
import { POLL_MS } from "./useProfile";

/** La revue travaille encore : les agents tournent, ou un PDF est en cours de rendu. */
export const isWorking = (review: CvReviewOut): boolean =>
  review.status === "running" || review.versions.some((version) => version.status === "rendering");

/**
 * `GET /cv/reviews/{id}` : la revue, ses modifications et ses versions. Relue toutes les `pollMs`
 * tant qu'elle travaille ; le flux de la session la fait aussi relire à chaque question.
 */
export function useReview(reviewId: string, pollMs = POLL_MS) {
  return useQuery({
    queryKey: cvKeys.review(reviewId),
    queryFn: ({ signal }) => fetchReview(reviewId, signal),
    refetchInterval: (state) => (state.state.data && isWorking(state.state.data) ? pollMs : false),
    retry: (count, error) => !(error instanceof ApiError && error.status === 404) && count < 1,
  });
}
