import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import type { SocketFactory } from "@/shared/realtime/socket";
import { useRun } from "@/shared/realtime/useRun";
import { fetchBrief } from "../api";
import { homeKeys } from "../queryKeys";
import { toBriefView } from "../toView";

const noop = () => undefined;

/** Délai de la seconde relecture, si le brief dit encore `pending` juste après la fin de la session. */
export const REREAD_MS = 3_000;

/**
 * `GET /brief/today`. Tant que le conseil est `pending`, la page suit sa session (`useRun`) et
 * relit le brief une fois la session finie : le conseil arrive (ou, s'il a échoué, la page le dit).
 * Si le serveur dit encore `pending` pour la même session, une seule seconde relecture suit après
 * `rereadMs`, puis plus rien : jamais de boucle. `failed` et `unavailable` sont définitifs pour la journée : rien n'est relu ni relancé pour eux.
 * `createSocket` ne sert qu'aux tests.
 */
export function useBrief(createSocket?: SocketFactory, rereadMs: number = REREAD_MS) {
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
    if (!sessionId || !run.over) return;
    void refetch();
    const again = setTimeout(() => void refetch(), rereadMs);
    return () => clearTimeout(again);
  }, [sessionId, run.over, refetch, rereadMs]);
  return { query, brief };
}
