import { useQuery } from "@tanstack/react-query";
import { fetchSkillHistory } from "../api";
import { skillKeys } from "../queryKeys";

/** Weeks of the progress curve (the contract accepts 1 to 52). */
export const HISTORY_WEEKS = 12;

/** Readings of the last 12 weeks, read only when the Progress tab is open. */
export function useSkillHistory(enabled: boolean) {
  return useQuery({
    queryKey: skillKeys.history(HISTORY_WEEKS),
    queryFn: ({ signal }) => fetchSkillHistory(HISTORY_WEEKS, signal),
    enabled,
    staleTime: 0,
  });
}
