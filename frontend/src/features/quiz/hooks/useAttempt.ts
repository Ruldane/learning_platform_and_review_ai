import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { usePollingBudget } from "@/shared/lib/usePollingBudget";
import { fetchAttempt } from "../api";
import { quizKeys } from "../queryKeys";

/** An attempt's grade: re-read every 2 s, 90 times (three minutes). */
export const GRADE_POLLS = 90;
export const GRADE_POLL_MS = 2000;

/**
 * An attempt (`GET /quizzes/{id}/attempts/{attempt}`), re-read every `pollMs` while it is
 * being graded (90 times at most). Once graded, the quiz is re-read: the question order of the next
 * attempt is no longer this one (F27).
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
