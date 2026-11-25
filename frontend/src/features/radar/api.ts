import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import { runSourceHeaders, type RunSource } from "@/shared/lib/runSource";
import type { RadarRunIn } from "./types";

/** The sweep's path: its sessions carry the sweep as subject. */
const GRAPH = "market_radar";

/** `GET /radar/latest`: suggested role and area, sweep in progress, latest finished sweep. */
export async function fetchLatest(signal?: AbortSignal) {
  return unwrap(await api.GET("/radar/latest", { signal }));
}

/** `GET /radar/runs`: the last 20 sweeps, most recent first. */
export async function fetchRuns(signal?: AbortSignal) {
  return unwrap(await api.GET("/radar/runs", { signal }));
}

/** `GET /radar/runs/{id}`: a sweep with its ranking, alerts and offers. */
export async function fetchRun(runId: string, signal?: AbortSignal) {
  return unwrap(
    await api.GET("/radar/runs/{run_id}", { params: { path: { run_id: runId } }, signal }),
  );
}

/** `POST /radar/runs`: 202 `{run_id, session_id}`; 409 `radar_in_progress` if one runs. */
export async function startRun(body: RadarRunIn, source?: RunSource) {
  return unwrap(await api.POST("/radar/runs", { body, headers: runSourceHeaders(source) }));
}

/**
 * The session of a sweep in progress: the server gives it only at launch (202), not in the reads.
 * It is found again by its subject (`subject_id` = the sweep) among the path's sessions.
 */
export async function fetchRunSessionId(runId: string, signal?: AbortSignal) {
  const sessions = unwrap(
    await api.GET("/sessions", { params: { query: { graph: GRAPH } }, signal }),
  );
  return sessions.find((session) => session.subject_id === runId)?.id ?? null;
}
