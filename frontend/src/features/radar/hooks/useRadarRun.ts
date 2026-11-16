import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import { ApiError } from "@/shared/api/errors";
import type { SocketFactory } from "@/shared/realtime/socket";
import { useRun } from "@/shared/realtime/useRun";
import { fetchRun, fetchRunSessionId } from "../api";
import { radarKeys } from "../queryKeys";
import { toRunView } from "../toView";

/** Tant qu'un relevé tourne, la page le relit aussi toute seule : un événement perdu ne bloque rien. */
const POLL_MS = 10_000;
/** La session d'un relevé qui vient d'être lancé peut mettre un instant à apparaître. */
const SESSION_POLL_MS = 3_000;

const isMissing = (error: unknown) => error instanceof ApiError && error.status === 404;

/**
 * Un relevé (`GET /radar/runs/{id}`) et, tant qu'il tourne, sa session suivie par `useRun` : le fil
 * ne fait que dire quand relire (chaque changement d'état de la session) ; les résultats viennent
 * toujours de la lecture. `hintSessionId` est la session donnée par le 202 du lancement ; sans
 * elle (page rouverte, 409 `radar_in_progress`), on la retrouve par son sujet. `runId` à `null` :
 * aucun relevé à suivre. `createSocket` ne sert qu'aux tests.
 */
export function useRadarRun(
  runId: string | null,
  hintSessionId: string | null,
  createSocket?: SocketFactory,
) {
  const client = useQueryClient();
  const query = useQuery({
    queryKey: radarKeys.run(runId ?? ""),
    queryFn: ({ signal }) => fetchRun(runId ?? "", signal),
    select: toRunView,
    enabled: runId !== null,
    staleTime: 0,
    refetchInterval: (state) => (state.state.data?.status === "running" ? POLL_MS : false),
    retry: (count, error) => !isMissing(error) && count < 1,
  });
  const running = query.data?.status === "running";
  const lookup = useQuery({
    queryKey: radarKeys.session(runId ?? ""),
    queryFn: ({ signal }) => fetchRunSessionId(runId ?? "", signal),
    enabled: runId !== null && running && hintSessionId === null,
    refetchInterval: (state) => (state.state.data ? false : SESSION_POLL_MS),
  });
  const sessionId = running ? (hintSessionId ?? lookup.data ?? null) : null;
  const sync = useCallback(() => {
    void client.invalidateQueries({ queryKey: radarKeys.all });
  }, [client]);
  const run = useRun(sessionId, sync, createSocket);
  return { query, run, running, sessionId, missing: isMissing(query.error) };
}
