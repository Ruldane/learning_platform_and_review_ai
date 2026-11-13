import { useQuery } from "@tanstack/react-query";
import { fetchStudySummary } from "../api";
import { studyKeys } from "../queryKeys";

/**
 * Le résumé de l'étude (`GET /study-sessions/summary`) : série, minutes de la semaine, minuteur,
 * session ouverte et bloc du jour. `everyMs` : relecture périodique (la barre du haut, 60 s).
 */
export function useStudySummary(everyMs?: number) {
  return useQuery({
    queryKey: studyKeys.summary,
    queryFn: ({ signal }) => fetchStudySummary(signal),
    refetchInterval: everyMs ?? false,
  });
}
