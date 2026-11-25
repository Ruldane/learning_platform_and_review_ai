import { useQuery } from "@tanstack/react-query";
import { fetchStats } from "../api";
import { applicationsKeys } from "../queryKeys";

/** Reminders arrive within the hour (scheduled task): the count is re-read from time to time. */
const REFRESH_MS = 5 * 60 * 1000;

const dueOf = (stats: { due_reminders: number }) => stats.due_reminders;

/**
 * The number of reminders due, for the navigation badge: the indicators query, so
 * shared with the board. `undefined` until it is known (or on failure): no badge.
 */
export function useDueCount(): number | undefined {
  return useQuery({
    queryKey: applicationsKeys.stats,
    queryFn: ({ signal }) => fetchStats(signal),
    select: dueOf,
    refetchInterval: REFRESH_MS,
  }).data;
}
