import { useQuery } from "@tanstack/react-query";
import { fetchSkillGraph } from "../api";
import { skillKeys } from "../queryKeys";

/** Le graphe est relu toutes les 30 s et au retour sur l'onglet du navigateur (moins d'une minute, D107). */
export const GRAPH_REFRESH_MS = 30_000;

/**
 * `GET /skills/graph`, relu toutes les 30 s (la relecture s'arrête quand l'onglet est caché) et
 * au retour sur l'onglet : un niveau gagné ailleurs apparaît sans recharger la page.
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
