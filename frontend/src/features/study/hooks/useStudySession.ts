import { useQuery } from "@tanstack/react-query";
import { fetchStudySession } from "../api";
import { studyKeys } from "../queryKeys";
import { usePollingBudget } from "@/shared/lib/usePollingBudget";

/** Relectures permises du bilan : 20 fois, toutes les 3 s (une minute). */
export const SUMMARY_POLLS = 20;
export const SUMMARY_POLL_MS = 3000;

/**
 * Une session d'étude (`GET /study-sessions/{id}`). Une fois « Terminer » envoyé (`finishing`), le
 * Tuteur conclut en tâche de fond : elle est relue toutes les `pollMs` jusqu'à `finished`, 20 fois
 * au plus ; `budget.exhausted` dit que l'attente est trop longue.
 */
export function useStudySession(studyId: string, finishing: boolean, pollMs = SUMMARY_POLL_MS) {
  const budget = usePollingBudget(SUMMARY_POLLS);
  const { spend } = budget;
  const query = useQuery({
    queryKey: studyKeys.session(studyId),
    queryFn: async ({ signal }) => {
      const session = await fetchStudySession(studyId, signal);
      if (finishing) spend();
      return session;
    },
    refetchInterval: (state) =>
      finishing && state.state.data?.status === "open" && !budget.exhausted ? pollMs : false,
  });
  return { query, budget };
}
