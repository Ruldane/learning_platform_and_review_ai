import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { usePollingBudget } from "@/shared/lib/usePollingBudget";
import { fetchAttempt } from "../api";
import { quizKeys } from "../queryKeys";

/** Note d'une tentative : relue toutes les 2 s, 90 fois (trois minutes). */
export const GRADE_POLLS = 90;
export const GRADE_POLL_MS = 2000;

/**
 * Une tentative (`GET /quizzes/{id}/attempts/{attempt}`), relue toutes les `pollMs` tant qu'elle est
 * notée (90 fois au plus). Une fois notée, le quiz est relu : l'ordre des questions du prochain
 * essai n'est plus celui-ci (F27).
 */
export function useAttempt(quizId: string, attemptId: string, pollMs = GRADE_POLL_MS) {
  const queryClient = useQueryClient();
  const budget = usePollingBudget(GRADE_POLLS);
  const { spend } = budget;
  const query = useQuery({
    queryKey: quizKeys.attempt(quizId, attemptId),
    queryFn: async ({ signal }) => {
      const attempt = await fetchAttempt(quizId, attemptId, signal);
      if (attempt.status === "grading") spend();
      return attempt;
    },
    refetchInterval: (state) =>
      state.state.data?.status === "grading" && !budget.exhausted ? pollMs : false,
  });
  const graded = query.data?.status === "graded";
  useEffect(() => {
    if (graded) void queryClient.invalidateQueries({ queryKey: quizKeys.quiz(quizId) });
  }, [graded, queryClient, quizId]);
  return { query, budget };
}
