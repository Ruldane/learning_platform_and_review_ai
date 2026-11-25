import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import type { SocketFactory } from "@/shared/realtime/socket";
import { useRun } from "@/shared/realtime/useRun";
import { fetchBrief } from "../api";
import { homeKeys } from "../queryKeys";
import { toBriefView } from "../toView";

const noop = () => undefined;

/** Delay of the second re-read, if the brief still says `pending` right after the session ends. */
export const REREAD_MS = 3_000;

/** Fallback re-read while the advice is `pending`: the session stream may have dropped. */
export const FALLBACK_MS = 15_000;
/** At most 40 fallback re-reads (10 minutes): never an endless loop. */
const FALLBACK_MAX = 40;

/**
 * `GET /brief/today`. While the advice is `pending`, the page follows its session (`useRun`) and
 * re-reads the brief once the session ends: the advice arrives (or the page says it failed).
 * If the server still says `pending` for the same session, one second re-read follows after
 * `rereadMs`, then nothing: never a loop. `failed` and `unavailable` are final for the day.
 * `createSocket` is only for tests.
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
    // If the stream drops without saying « fini », the screen does not stay on « se réunit… »:
    // the brief re-reads itself until `ready`, `failed` or `unavailable` (the server settles an
    // dead session when read).
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
