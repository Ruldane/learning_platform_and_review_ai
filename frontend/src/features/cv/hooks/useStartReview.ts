import { useMutation } from "@tanstack/react-query";
import { ApiError } from "@/shared/api/errors";
import { startReview } from "../api";

/** Ce que la page doit faire d'un refus du lancement : son code, et la revue déjà ouverte s'il y en a une. */
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

/** `POST /cv/reviews` : lance la revue d'une offre ; `onStarted` reçoit l'identifiant de la revue. */
export function useStartReview(postingId: string, onStarted: (reviewId: string) => void) {
  const mutation = useMutation({
    mutationFn: () => startReview(postingId),
    onSuccess: (started) => onStarted(started.review_id),
    // Une revue déjà ouverte pour cette offre : on la reprend.
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
