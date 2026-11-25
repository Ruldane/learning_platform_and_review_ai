import { useMutation, useQuery } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { ApiError, errorMessage } from "@/shared/api/errors";
import { fetchDueCards, reviewCard } from "../api";
import { quizKeys } from "../queryKeys";

/** Today's queue (`GET /flashcards/due`). */
export function useDueCards() {
  return useQuery({
    queryKey: quizKeys.due,
    queryFn: ({ signal }) => fetchDueCards(signal),
  });
}

export interface ReviewOutcome {
  /** Done: rating recorded, or already reviewed elsewhere (`card_not_due`, no error). */
  advanced: boolean;
  /** A skill demoted by this rating (two failures in a row), to be told. */
  demotedSkill: string | null;
}

/**
 * A rating for a card (`POST /flashcards/{id}/review`). Only one rating at a time, set
 * synchronously: a quick double press on 1 or 2 sends one. `card_not_due` (already reviewed) is
 * treated as a success: we move on to the next card without error.
 */
export function useReviewCard() {
  const busy = useRef(false);
  const [error, setError] = useState<string | null>(null);
  const mutation = useMutation({
    mutationFn: ({ cardId, result }: { cardId: string; result: "ok" | "fail" }) =>
      reviewCard(cardId, result),
  });
  const { mutateAsync } = mutation;

  const send = async (cardId: string, result: "ok" | "fail"): Promise<ReviewOutcome | null> => {
    if (busy.current) return null;
    busy.current = true;
    setError(null);
    try {
      const review = await mutateAsync({ cardId, result });
      return { advanced: true, demotedSkill: review.demoted_skill };
    } catch (failure) {
      if (failure instanceof ApiError && failure.code === "card_not_due") {
        return { advanced: true, demotedSkill: null };
      }
      setError(errorMessage(failure));
      return { advanced: false, demotedSkill: null };
    } finally {
      busy.current = false;
    }
  };
  return { send, pending: mutation.isPending, error };
}
