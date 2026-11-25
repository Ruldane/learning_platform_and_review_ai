import { useQuery } from "@tanstack/react-query";
import { usePollingBudget } from "@/shared/lib/usePollingBudget";
import { fetchQuiz } from "../api";
import { quizKeys } from "../queryKeys";

/** Quiz preparation: re-read every 3 s, 40 times (two minutes). */
export const PREPARE_POLLS = 40;
export const PREPARE_POLL_MS = 3000;

/**
 * A quiz (`GET /quizzes/{id}`). While it is prepared, it is re-read every `pollMs`, 40 times at
 * most; `budget.exhausted` says the wait is too long (`budget.restart` starts again). It is also
 * re-read after each grade: the order of questions and choices changes on each attempt (F27).
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
