import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import { runSourceHeaders, type RunSource } from "@/shared/lib/runSource";
import type { ExerciseGenerateIn, ExerciseIn, RunKind, TeachIn, Preferences } from "./types";

/** `GET /ide/exercises`: my exercises, newest first. */
export async function fetchExercises(signal?: AbortSignal) {
  return unwrap(await api.GET("/ide/exercises", { signal }));
}

/** `POST /ide/exercises`: an exercise written by hand. */
export async function createExercise(body: ExerciseIn) {
  return unwrap(await api.POST("/ide/exercises", { body }));
}

/** `POST /ide/exercises/generate`: the agents write the exercise; we follow `session_id`. */
export async function generateExercise(body: ExerciseGenerateIn, source?: RunSource) {
  return unwrap(
    await api.POST("/ide/exercises/generate", { body, headers: runSourceHeaders(source) }),
  );
}

/** `GET /ide/sessions`: my sessions, most recent first. */
export async function fetchSessions(signal?: AbortSignal) {
  return unwrap(await api.GET("/ide/sessions", { signal }));
}

/** `POST /ide/sessions`: opens a session on an exercise, or a free session. */
export async function createSession(exerciseId: string | null) {
  return unwrap(await api.POST("/ide/sessions", { body: { exercise_id: exerciseId } }));
}

/** `GET /ide/sessions/{id}`: a session with its files. */
export async function fetchSession(sessionId: string, signal?: AbortSignal) {
  const params = { path: { session_id: sessionId } };
  return unwrap(await api.GET("/ide/sessions/{session_id}", { params, signal }));
}

/** `PUT /ide/sessions/{id}/files`: replaces all files; 409 `stale_base` if Claude changed them. */
export async function putFiles(
  sessionId: string,
  files: Record<string, string>,
  entry: string,
  baseHashes: Record<string, string>,
) {
  const params = { path: { session_id: sessionId } };
  const body = { files, entry, base_hashes: baseHashes };
  return unwrap(await api.PUT("/ide/sessions/{session_id}/files", { params, body }));
}

/** `POST /ide/sessions/{id}/runs`: queues a run or a check (202). */
export async function startRun(sessionId: string, kind: RunKind) {
  const params = { path: { session_id: sessionId } };
  return unwrap(await api.POST("/ide/sessions/{session_id}/runs", { params, body: { kind } }));
}

/** `GET /ide/runs/{id}?after=`: the output from byte `after`. */
export async function fetchRun(runId: string, after: number, signal?: AbortSignal) {
  const params = { path: { run_id: runId }, query: { after } };
  return unwrap(await api.GET("/ide/runs/{run_id}", { params, signal }));
}

/** `POST /ide/sessions/{id}/teach`: wakes the teacher (never on keystrokes). */
export async function teach(sessionId: string, body: TeachIn, source?: RunSource) {
  const params = { path: { session_id: sessionId } };
  return unwrap(
    await api.POST("/ide/sessions/{session_id}/teach", {
      params,
      body,
      headers: runSourceHeaders(source),
    }),
  );
}

/** `GET /ide/sessions/{id}/notes` : indices, explications, annotations, propositions, renvois. */
export async function fetchNotes(sessionId: string, signal?: AbortSignal) {
  const params = { path: { session_id: sessionId } };
  return unwrap(await api.GET("/ide/sessions/{session_id}/notes", { params, signal }));
}

/** `POST /ide/notes/{id}/accept`: the backend applies the proposal and updates the session. */
export async function acceptNote(noteId: string) {
  const params = { path: { note_id: noteId } };
  return unwrap(await api.POST("/ide/notes/{note_id}/accept", { params }));
}

/** `POST /ide/notes/{id}/reject`: rejects a proposal. */
export async function rejectNote(noteId: string) {
  const params = { path: { note_id: noteId } };
  return unwrap(await api.POST("/ide/notes/{note_id}/reject", { params }));
}

/** `GET /ide/preferences`: teacher mode, timer, caps. */
export async function fetchPreferences(signal?: AbortSignal) {
  return unwrap(await api.GET("/ide/preferences", { signal }));
}

/** `PUT /ide/preferences`: replaces all teacher preferences. */
export async function putPreferences(body: Preferences) {
  return unwrap(await api.PUT("/ide/preferences", { body }));
}

/** `GET /ide/usage?session_id=`: tokens for the session and the day, caps, on-demand mode. */
export async function fetchUsage(sessionId: string, signal?: AbortSignal) {
  const params = { query: { session_id: sessionId } };
  return unwrap(await api.GET("/ide/usage", { params, signal }));
}

/** `GET /ide/sessions/{id}/runs`: the last 20 runs (Claude's included). */
export async function fetchRuns(sessionId: string, signal?: AbortSignal) {
  const params = { path: { session_id: sessionId } };
  return unwrap(await api.GET("/ide/sessions/{session_id}/runs", { params, signal }));
}
