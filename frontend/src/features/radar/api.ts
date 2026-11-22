import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import { runSourceHeaders, type RunSource } from "@/shared/lib/runSource";
import type { RadarRunIn } from "./types";

/** Le parcours du relevé : ses sessions portent le relevé comme sujet. */
const GRAPH = "market_radar";

/** `GET /radar/latest` : poste et zone proposés, relevé en cours, dernier relevé fini. */
export async function fetchLatest(signal?: AbortSignal) {
  return unwrap(await api.GET("/radar/latest", { signal }));
}

/** `GET /radar/runs` : les 20 derniers relevés, le plus récent d'abord. */
export async function fetchRuns(signal?: AbortSignal) {
  return unwrap(await api.GET("/radar/runs", { signal }));
}

/** `GET /radar/runs/{id}` : un relevé avec son classement, ses alertes et ses offres. */
export async function fetchRun(runId: string, signal?: AbortSignal) {
  return unwrap(
    await api.GET("/radar/runs/{run_id}", { params: { path: { run_id: runId } }, signal }),
  );
}

/** `POST /radar/runs` : 202 `{run_id, session_id}` ; 409 `radar_in_progress` si un relevé tourne. */
export async function startRun(body: RadarRunIn, source?: RunSource) {
  return unwrap(await api.POST("/radar/runs", { body, headers: runSourceHeaders(source) }));
}

/**
 * La session d'un relevé en cours : le serveur ne la donne qu'au lancement (202), pas dans les
 * lectures. On la retrouve par son sujet (`subject_id` = le relevé) dans les sessions du parcours.
 */
export async function fetchRunSessionId(runId: string, signal?: AbortSignal) {
  const sessions = unwrap(
    await api.GET("/sessions", { params: { query: { graph: GRAPH } }, signal }),
  );
  return sessions.find((session) => session.subject_id === runId)?.id ?? null;
}
