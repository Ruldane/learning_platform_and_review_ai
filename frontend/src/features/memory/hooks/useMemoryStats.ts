import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { fetchStats, postReindex } from "../api";
import { memoryKeys } from "../queryKeys";
import { toStats } from "../toView";
import type { StatsOut } from "../types";

const POLL_MS = 2000;

/** Reindex in progress (queued or running): the screen polls the server every 2 s. */
export function isReindexActive(stats: Pick<StatsOut, "reindex"> | undefined): boolean {
  const status = stats?.reindex.status;
  return status === "queued" || status === "running";
}

/**
 * Memory statistics. While a reindex is queued or running, re-read every
 * 2 s; when it ends, the list and the map are re-read (« indexed » flags).
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

/** Requests the reindex (`POST /memory/reindex`), then re-reads the statistics to follow it. */
export function useReindex() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: postReindex,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: memoryKeys.stats }),
  });
}
