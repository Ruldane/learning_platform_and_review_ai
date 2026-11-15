import { useQuery } from "@tanstack/react-query";
import { fetchApplications, fetchStats } from "../api";
import { applicationsKeys } from "../queryKeys";
import { toApplicationView, toStatsView } from "../toView";
import type { ApplicationOut, ApplicationStatsOut } from "../types";

// Des fonctions stables : TanStack Query ne refait pas la conversion à chaque rendu.
const toViews = (rows: ApplicationOut[]) => rows.map(toApplicationView);
const toStats = (stats: ApplicationStatsOut) => toStatsView(stats);

/** `GET /applications` : les fiches du tableau de suivi, déjà converties pour les composants. */
export function useApplications() {
  return useQuery({
    queryKey: applicationsKeys.list,
    queryFn: ({ signal }) => fetchApplications(signal),
    select: toViews,
  });
}

/** `GET /applications/stats` : les indicateurs de la barre du haut du tableau. */
export function useStats() {
  return useQuery({
    queryKey: applicationsKeys.stats,
    queryFn: ({ signal }) => fetchStats(signal),
    select: toStats,
  });
}
