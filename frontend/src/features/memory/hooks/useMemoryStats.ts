import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { fetchStats, postReindex } from "../api";
import { memoryKeys } from "../queryKeys";
import { toStats } from "../toView";
import type { StatsOut } from "../types";

const POLL_MS = 2000;

/** Réindexation en cours (en file ou en route) : l'écran interroge le serveur toutes les 2 s. */
export function isReindexActive(stats: Pick<StatsOut, "reindex"> | undefined): boolean {
  const status = stats?.reindex.status;
  return status === "queued" || status === "running";
}

/**
 * Statistiques de la mémoire. Tant qu'une réindexation est en file ou en cours, relecture toutes
 * les 2 s ; quand elle se termine, la liste et la carte sont relues (indicateurs « indexé »).
 */
export function useMemoryStats() {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: memoryKeys.stats,
    queryFn: ({ signal }) => fetchStats(signal),
    refetchInterval: (q) => (isReindexActive(q.state.data) ? POLL_MS : false),
    select: toStats,
  });

  const active = query.data ? query.data.reindex.status : null;
  const wasActive = useRef(false);
  useEffect(() => {
    if (active === null) return;
    const now = active === "queued" || active === "running";
    if (wasActive.current && !now) {
      void queryClient.invalidateQueries({ queryKey: memoryKeys.itemsAll });
      void queryClient.invalidateQueries({ queryKey: memoryKeys.map });
    }
    wasActive.current = now;
  }, [active, queryClient]);
  return query;
}

/** Demande la réindexation (`POST /memory/reindex`) puis relit les statistiques pour la suivre. */
export function useReindex() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: postReindex,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: memoryKeys.stats }),
  });
}
