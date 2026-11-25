import { useQuery } from "@tanstack/react-query";
import { ApiError } from "@/shared/api/errors";
import { fetchReview } from "../api";
import { cvKeys } from "../queryKeys";
import type { CvReviewOut } from "../types";
import { POLL_MS } from "./useProfile";

/** The review is still working: agents are running, or a PDF is being rendered. */
export const isWorking = (review: CvReviewOut): boolean =>
  review.status === "running" || review.versions.some((version) => version.status === "rendering");

/**
 * `GET /cv/reviews/{id}`: the review, its changes and its versions. Reloaded every `pollMs`
 * while it works; the session stream also makes it reload at each question.
 */
export function useReview(reviewId: string, pollMs = POLL_MS) {
  return useQuery({
    queryKey: cvKeys.review(reviewId),
    queryFn: ({ signal }) => fetchReview(reviewId, signal),
    refetchInterval: (state) => (state.state.data && isWorking(state.state.data) ? pollMs : false),
    retry: (count, error) => !(error instanceof ApiError && error.status === 404) && count < 1,
  });
}
