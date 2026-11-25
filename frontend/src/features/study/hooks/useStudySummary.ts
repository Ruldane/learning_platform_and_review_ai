import { useQuery } from "@tanstack/react-query";
import { fetchStudySummary } from "../api";
import { studyKeys } from "../queryKeys";

/**
 * The study summary (`GET /study-sessions/summary`): streak, minutes of the week, timer,
 * open session and day's block. `everyMs`: periodic reread (the top bar, 60 s).
 */
export function useStudySummary(everyMs?: number) {
  return useQuery({
    queryKey: studyKeys.summary,
    queryFn: ({ signal }) => fetchStudySummary(signal),
    refetchInterval: everyMs ?? false,
  });
}
