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

/** Relecture de repli tant que le conseil est `pending` : le flux de la session peut avoir lâché. */
export const FALLBACK_MS = 15_000;
/** Au plus 40 relectures de repli (10 minutes) : jamais de boucle sans fin. */
const FALLBACK_MAX = 40;

/**
 * `GET /brief/today`. Tant que le conseil est `pending`, la page suit sa session (`useRun`) et
 * relit le brief une fois la session finie : le conseil arrive (ou, s'il a échoué, la page le dit).
 * Si le serveur dit encore `pending` pour la même session, une seule seconde relecture suit après
 * `rereadMs`, puis plus rien : jamais de boucle. `failed` et `unavailable` sont définitifs pour la journée : rien n'est relu ni relancé pour eux.
 * `createSocket` ne sert qu'aux tests.
 */
export function useBrief(
  createSocket?: SocketFactory,
  rereadMs: number = REREAD_MS,
  fallbackMs: number = FALLBACK_MS,
) {
  const query = useQuery({
    queryKey: homeKeys.brief,
    queryFn: ({ signal }) => fetchBrief(signal),
    select: toBriefView,
    staleTime: 0,
    // Si le flux abandonne sans jamais dire « fini », l'écran ne reste pas sur « se réunit… » :
    // le brief se relit seul jusqu'à `ready`, `failed` ou `unavailable` (le serveur règle une
    // session morte à la lecture).
    refetchInterval: (state) =>
      state.state.data?.advice_status === "pending" && state.state.dataUpdateCount < FALLBACK_MAX
        ? fallbackMs
        : false,
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
