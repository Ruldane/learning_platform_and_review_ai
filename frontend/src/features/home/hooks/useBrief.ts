import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import type { SocketFactory } from "@/shared/realtime/socket";
import { useRun } from "@/shared/realtime/useRun";
import { fetchBrief } from "../api";
import { homeKeys } from "../queryKeys";
import { toBriefView } from "../toView";

const noop = () => undefined;

/**
 * `GET /brief/today`. Tant que le conseil est `pending`, la page suit sa session (`useRun`) et
 * relit le brief une fois la session finie : le conseil arrive (ou, s'il a échoué, la page le dit).
 * `failed` et `unavailable` sont définitifs pour la journée : rien n'est relu ni relancé pour eux.
 * `createSocket` ne sert qu'aux tests.
 */
export function useBrief(createSocket?: SocketFactory) {
  const query = useQuery({
    queryKey: homeKeys.brief,
    queryFn: ({ signal }) => fetchBrief(signal),
    select: toBriefView,
    staleTime: 0,
  });
  const brief = query.data;
  const sessionId = brief?.advice.status === "pending" ? brief.sessionId : null;
  const run = useRun(sessionId, noop, createSocket);
  const { refetch } = query;
  useEffect(() => {
    if (sessionId && run.over) void refetch();
  }, [sessionId, run.over, refetch]);
  return { query, brief };
}
