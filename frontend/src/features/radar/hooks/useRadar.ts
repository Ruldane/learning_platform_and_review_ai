import { useQuery } from "@tanstack/react-query";
import { fetchLatest, fetchRuns } from "../api";
import { radarKeys } from "../queryKeys";
import { toHistoryItem, toLatestView } from "../toView";

/**
 * What the radar page reads on opening: `GET /radar/latest` (suggested values, sweep in
 * progress, latest finished sweep) and `GET /radar/runs` (the history). Both are re-read at the end
 * of a sweep and after a launch (`radarKeys.all`).
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
