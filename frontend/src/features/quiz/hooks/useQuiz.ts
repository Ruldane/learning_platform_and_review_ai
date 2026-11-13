import { useQuery } from "@tanstack/react-query";
import { usePollingBudget } from "@/shared/lib/usePollingBudget";
import { fetchQuiz } from "../api";
import { quizKeys } from "../queryKeys";

/** Préparation d'un quiz : relue toutes les 3 s, 40 fois (deux minutes). */
export const PREPARE_POLLS = 40;
export const PREPARE_POLL_MS = 3000;

/**
 * Un quiz (`GET /quizzes/{id}`). Tant qu'il se prépare, il est relu toutes les `pollMs`, 40 fois au
 * plus ; `budget.exhausted` dit que l'attente est trop longue (`budget.restart` repart). Il est relu
 * aussi après chaque note : l'ordre des questions et des choix change à chaque essai (F27).
 */
export function useQuiz(quizId: string, pollMs = PREPARE_POLL_MS) {
  const budget = usePollingBudget(PREPARE_POLLS);
  const { spend } = budget;
  const query = useQuery({
    queryKey: quizKeys.quiz(quizId),
    queryFn: async ({ signal }) => {
      const quiz = await fetchQuiz(quizId, signal);
      if (quiz.status === "generating") spend();
      return quiz;
    },
    refetchInterval: (state) =>
      state.state.data?.status === "generating" && !budget.exhausted ? pollMs : false,
  });
  return { query, budget };
}
