import { useMutation, useQuery } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { ApiError, errorMessage } from "@/shared/api/errors";
import { fetchDueCards, reviewCard } from "../api";
import { quizKeys } from "../queryKeys";

/** La file du jour (`GET /flashcards/due`). */
export function useDueCards() {
  return useQuery({
    queryKey: quizKeys.due,
    queryFn: ({ signal }) => fetchDueCards(signal),
  });
}

export interface ReviewOutcome {
  /** La fiche est passée : avis enregistré, ou déjà revue ailleurs (`card_not_due`, sans erreur). */
  advanced: boolean;
  /** Compétence rétrogradée par cet avis (deux échecs de suite), à dire. */
  demotedSkill: string | null;
}

/**
 * L'avis sur une fiche (`POST /flashcards/{id}/review`). Un seul avis à la fois, posé de façon
 * synchrone : un double appui rapide sur 1 ou 2 n'en envoie qu'un. `card_not_due` (déjà revue) est
 * traité comme un succès : on passe à la fiche suivante sans erreur.
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
