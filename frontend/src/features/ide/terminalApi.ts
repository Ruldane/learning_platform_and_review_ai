import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";

export async function startTerminal(sessionId: string) {
  const params = { path: { session_id: sessionId } };
  return unwrap(await api.POST("/ide/sessions/{session_id}/terminal", { params }));
}

export async function fetchTerminal(runId: string, after: number, signal?: AbortSignal) {
  const params = { path: { run_id: runId }, query: { after } };
  return unwrap(await api.GET("/ide/terminals/{run_id}", { params, signal }));
}

export async function sendTerminal(runId: string, data: string) {
  const params = { path: { run_id: runId } };
  unwrap(await api.POST("/ide/terminals/{run_id}/input", { params, body: { data } }));
}

export async function stopTerminal(runId: string) {
  const params = { path: { run_id: runId } };
  unwrap(await api.DELETE("/ide/terminals/{run_id}", { params }));
}
