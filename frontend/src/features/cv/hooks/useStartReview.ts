import { useMutation } from "@tanstack/react-query";
import { ApiError } from "@/shared/api/errors";
import type { RunSource } from "@/shared/lib/runSource";
import { startReview } from "../api";

/** What the page does on a launch refusal: its code, and the review already open, if any. */
export interface StartRefusal {
  code: string;
  reviewId: string | null;
}

export function refusalOf(error: unknown): StartRefusal {
  if (!(error instanceof ApiError)) return { code: "unknown", reviewId: null };
  const { details } = error;
  const reviewId =
    typeof details === "object" && details !== null && "review_id" in details
      ? details.review_id
      : null;
  return { code: error.code, reviewId: typeof reviewId === "string" ? reviewId : null };
}

/** `POST /cv/reviews`: starts the review of a posting; `onStarted` receives the review id. */
export function useStartReview(
  postingId: string,
  onStarted: (reviewId: string) => void,
  source?: RunSource,
) {
  const mutation = useMutation({
    mutationFn: () => startReview(postingId, source),
    onSuccess: (started) => onStarted(started.review_id),
    // A review already open for this posting: resume it.
    onError: (error) => {
      const refusal = refusalOf(error);
      if (refusal.code === "review_in_progress" && refusal.reviewId) onStarted(refusal.reviewId);
    },
  });
  return {
    start: () => mutation.mutate(),
    isStarting: mutation.isPending,
    refusal: mutation.isError ? refusalOf(mutation.error) : null,
    error: mutation.error,
    isIdle: mutation.isIdle,
  };
}
