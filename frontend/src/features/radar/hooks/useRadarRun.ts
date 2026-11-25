import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef } from "react";
import { ApiError } from "@/shared/api/errors";
import type { SocketFactory } from "@/shared/realtime/socket";
import { useRun } from "@/shared/realtime/useRun";
import { fetchRun, fetchRunSessionId } from "../api";
import { radarKeys } from "../queryKeys";
import { toRunView } from "../toView";

/** While a sweep runs, the page also re-reads it on its own: a lost event blocks nothing. */
const POLL_MS = 10_000;
/** The session of a sweep just launched may take a moment to appear. */
const SESSION_POLL_MS = 3_000;

const isMissing = (error: unknown) => error instanceof ApiError && error.status === 404;

/**
 * A sweep (`GET /radar/runs/{id}`) and, while it runs, its session followed by `useRun`: the thread
 * only says when to re-read (each session state change); the results always come from the read.
 * `hintSessionId` is the session given by the launch's 202; without it (page reopened, 409
 * `radar_in_progress`), it is found by its subject. `runId` at `null`: nothing to follow.
 * `createSocket` serves only the tests.
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
  // The sweep leaves `running` (via the stream or the 10 s fallback re-read): the form and
  // history re-read, even if the stream stayed silent.
  const status = query.data?.status;
  const previous = useRef(status);
  useEffect(() => {
    if (previous.current === "running" && status && status !== "running") {
      void client.invalidateQueries({ queryKey: radarKeys.latest });
      void client.invalidateQueries({ queryKey: radarKeys.history });
    }
    previous.current = status;
  }, [status, client]);
  const run = useRun(sessionId, sync, createSocket);
  return { query, run, running, sessionId, missing: isMissing(query.error) };
}
