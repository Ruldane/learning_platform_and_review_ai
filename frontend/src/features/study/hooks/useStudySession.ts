import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { clearTimer } from "../components/StudyTimer";
import { fetchStudySession } from "../api";
import { studyKeys } from "../queryKeys";
import { usePollingBudget } from "@/shared/lib/usePollingBudget";

/** Summary re-reads allowed: 20 times, every 3 s (one minute). */
export const SUMMARY_POLLS = 20;
export const SUMMARY_POLL_MS = 3000;

/**
 * A study session (`GET /study-sessions/{id}`). Once « Terminer » is sent (`finishing`), the
 * Tutor concludes in the background: it is reread every `pollMs` until `finished`, 20 times
 * at most; `budget.exhausted` says the wait is too long. A `finished` or
 * `cancelled` session rereads the summary (hours of the week, open session) and forgets its timer.
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
  const queryClient = useQueryClient();
  const status = query.data?.status;
  const closed = status === "finished" || status === "cancelled";
  useEffect(() => {
    if (!closed) return;
    clearTimer(studyId);
    void queryClient.invalidateQueries({ queryKey: studyKeys.summary });
  }, [closed, studyId, queryClient]);
  return { query, budget };
}
