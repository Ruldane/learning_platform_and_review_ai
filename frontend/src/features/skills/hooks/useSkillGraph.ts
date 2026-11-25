import { useQuery } from "@tanstack/react-query";
import { fetchSkillGraph } from "../api";
import { skillKeys } from "../queryKeys";

/** The graph is reread every 30 s and when returning to the browser tab (under a minute, D107). */
export const GRAPH_REFRESH_MS = 30_000;

/**
 * `GET /skills/graph`, reread every 30 s (rereading stops when the tab is hidden) and
 * on return to the tab: a level gained elsewhere appears without reloading the page.
 */
export function useSkillGraph() {
  return useQuery({
    queryKey: skillKeys.graph,
    queryFn: ({ signal }) => fetchSkillGraph(signal),
    refetchInterval: GRAPH_REFRESH_MS,
    refetchOnWindowFocus: true,
    staleTime: 0,
  });
}
