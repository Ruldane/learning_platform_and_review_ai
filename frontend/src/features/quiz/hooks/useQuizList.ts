import { useQuery } from "@tanstack/react-query";
import { fetchPrograms, fetchQuizzes } from "../api";
import { quizKeys } from "../queryKeys";
import { toQuizSummaryView } from "../toView";

/** Re-reads the list while a quiz is being prepared. */
const PREPARING_POLL_MS = 5000;

/** The most recent program (`GET /programs`): the quiz list is that of its modules. */
export function useLatestProgram() {
  return useQuery({
    queryKey: quizKeys.programs,
    queryFn: ({ signal }) => fetchPrograms(signal),
    select: (programs) => programs[0] ?? null,
  });
}

/**
 * The program's quizzes (`GET /programs/{id}/quizzes`), one module per row. Re-read every 5 s
 * while a quiz is being prepared, so « en préparation » turns into « Passer le quiz » unprompted.
 */
export function useQuizList(programId: string | undefined, pollMs = PREPARING_POLL_MS) {
  return useQuery({
    queryKey: quizKeys.list(programId ?? ""),
    queryFn: ({ signal }) => fetchQuizzes(programId ?? "", signal),
    enabled: programId !== undefined,
    select: (items) => items.map((item) => toQuizSummaryView(item)),
    refetchInterval: (query) =>
      query.state.data?.some((item) => item.status === "generating") ? pollMs : false,
  });
}
