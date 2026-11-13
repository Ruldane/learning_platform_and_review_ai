import { useQuery } from "@tanstack/react-query";
import { fetchPrograms, fetchQuizzes } from "../api";
import { quizKeys } from "../queryKeys";
import { toQuizSummaryView } from "../toView";

/** Relecture de la liste tant qu'un quiz se prépare. */
const PREPARING_POLL_MS = 5000;

/** Le programme le plus récent (`GET /programs`) : la liste des quiz est celle de ses modules. */
export function useLatestProgram() {
  return useQuery({
    queryKey: quizKeys.programs,
    queryFn: ({ signal }) => fetchPrograms(signal),
    select: (programs) => programs[0] ?? null,
  });
}

/**
 * Les quiz du programme (`GET /programs/{id}/quizzes`), un module par ligne. Relue toutes les 5 s
 * tant qu'un quiz se prépare, pour que « en préparation » devienne « Passer le quiz » sans geste.
 */
export function useQuizList(programId: string | undefined, pollMs = PREPARING_POLL_MS) {
  return useQuery({
    queryKey: quizKeys.list(programId ?? ""),
    queryFn: ({ signal }) => fetchQuizzes(programId ?? "", signal),
    enabled: programId !== undefined,
    select: (items) => items.map(toQuizSummaryView),
    refetchInterval: (query) =>
      query.state.data?.some((item) => item.status === "generating") ? pollMs : false,
  });
}
