import { useQuery } from "@tanstack/react-query";
import { fetchApplications, fetchStats } from "../api";
import { applicationsKeys } from "../queryKeys";
import { toApplicationView, toStatsView } from "../toView";
import type { ApplicationOut, ApplicationStatsOut } from "../types";

// Stable functions: TanStack Query does not redo the conversion on each render.
const toViews = (rows: ApplicationOut[]) => rows.map(toApplicationView);
const toStats = (stats: ApplicationStatsOut) => toStatsView(stats);

/** `GET /applications`: the tracking board's records, already converted for the components. */
export function useApplications() {
  return useQuery({
    queryKey: applicationsKeys.list,
    queryFn: ({ signal }) => fetchApplications(signal),
    select: toViews,
  });
}

/** `GET /applications/stats`: the indicators of the board's top bar. */
export function useStats() {
  return useQuery({
    queryKey: applicationsKeys.stats,
    queryFn: ({ signal }) => fetchStats(signal),
    select: toStats,
  });
}
