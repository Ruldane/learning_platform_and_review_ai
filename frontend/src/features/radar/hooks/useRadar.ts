import { useQuery } from "@tanstack/react-query";
import { fetchLatest, fetchRuns } from "../api";
import { radarKeys } from "../queryKeys";
import { toHistoryItem, toLatestView } from "../toView";

/**
 * Ce que la page du radar lit à l'ouverture : `GET /radar/latest` (valeurs proposées, relevé en
 * cours, dernier relevé fini) et `GET /radar/runs` (l'historique). Les deux sont relus à la fin
 * d'un relevé et après un lancement (`radarKeys.all`).
 */
export function useRadar() {
  const latest = useQuery({
    queryKey: radarKeys.latest,
    queryFn: ({ signal }) => fetchLatest(signal),
    select: toLatestView,
    staleTime: 0,
  });
  const history = useQuery({
    queryKey: radarKeys.history,
    queryFn: ({ signal }) => fetchRuns(signal),
    select: (runs) => runs.map(toHistoryItem),
    staleTime: 0,
  });
  return { latest, history };
}
