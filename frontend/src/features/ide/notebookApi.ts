import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { components } from "@/shared/api/schema";

type Schemas = components["schemas"];
export type NotebookCell = Schemas["NotebookCellOut"];
export type NotebookPut = Schemas["NotebookPut"];
export type NotebookRun = Schemas["NotebookRunIn"];

export async function fetchNotebook(sessionId: string, path: string, signal?: AbortSignal) {
  const params = { path: { session_id: sessionId }, query: { path } };
  return unwrap(await api.GET("/ide/sessions/{session_id}/notebook", { params, signal }));
}

export async function saveNotebook(sessionId: string, body: NotebookPut) {
  const params = { path: { session_id: sessionId } };
  return unwrap(await api.PUT("/ide/sessions/{session_id}/notebook", { params, body }));
}

export async function runNotebookCell(sessionId: string, body: NotebookRun) {
  const params = { path: { session_id: sessionId } };
  return unwrap(await api.POST("/ide/sessions/{session_id}/notebook/run", { params, body }));
}

export async function fetchNotebookRun(runId: string, after: number, signal?: AbortSignal) {
  const params = { path: { run_id: runId }, query: { after } };
  return unwrap(await api.GET("/ide/notebook-runs/{run_id}", { params, signal }));
}
