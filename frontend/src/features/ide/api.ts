import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { ExerciseGenerateIn, ExerciseIn, RunKind, TeachIn, Preferences } from "./types";

/** `GET /ide/exercises` : mes exercices, les plus récents d'abord. */
export async function fetchExercises(signal?: AbortSignal) {
  return unwrap(await api.GET("/ide/exercises", { signal }));
}

/** `POST /ide/exercises` : un exercice écrit à la main. */
export async function createExercise(body: ExerciseIn) {
  return unwrap(await api.POST("/ide/exercises", { body }));
}

/** `POST /ide/exercises/generate` : les agents écrivent l'exercice ; on suit `session_id`. */
export async function generateExercise(body: ExerciseGenerateIn) {
  return unwrap(await api.POST("/ide/exercises/generate", { body }));
}

/** `GET /ide/sessions` : mes séances, la plus récente d'abord. */
export async function fetchSessions(signal?: AbortSignal) {
  return unwrap(await api.GET("/ide/sessions", { signal }));
}

/** `POST /ide/sessions` : ouvre une séance sur un exercice, ou une séance libre. */
export async function createSession(exerciseId: string | null) {
  return unwrap(await api.POST("/ide/sessions", { body: { exercise_id: exerciseId } }));
}

/** `GET /ide/sessions/{id}` : une séance avec ses fichiers. */
export async function fetchSession(sessionId: string, signal?: AbortSignal) {
  const params = { path: { session_id: sessionId } };
  return unwrap(await api.GET("/ide/sessions/{session_id}", { params, signal }));
}

/** `PUT /ide/sessions/{id}/files` : remplace tous les fichiers de la séance. */
export async function putFiles(sessionId: string, files: Record<string, string>, entry: string) {
  const params = { path: { session_id: sessionId } };
  const body = { files, entry };
  return unwrap(await api.PUT("/ide/sessions/{session_id}/files", { params, body }));
}

/** `POST /ide/sessions/{id}/runs` : dépose une exécution ou une vérification (202). */
export async function startRun(sessionId: string, kind: RunKind) {
  const params = { path: { session_id: sessionId } };
  return unwrap(await api.POST("/ide/sessions/{session_id}/runs", { params, body: { kind } }));
}

/** `GET /ide/runs/{id}?after=` : la sortie depuis l'octet `after`. */
export async function fetchRun(runId: string, after: number, signal?: AbortSignal) {
  const params = { path: { run_id: runId }, query: { after } };
  return unwrap(await api.GET("/ide/runs/{run_id}", { params, signal }));
}

/** `POST /ide/sessions/{id}/teach` : réveille le professeur (jamais à la frappe). */
export async function teach(sessionId: string, body: TeachIn) {
  const params = { path: { session_id: sessionId } };
  return unwrap(await api.POST("/ide/sessions/{session_id}/teach", { params, body }));
}

/** `GET /ide/sessions/{id}/notes` : indices, explications, annotations, propositions, renvois. */
export async function fetchNotes(sessionId: string, signal?: AbortSignal) {
  const params = { path: { session_id: sessionId } };
  return unwrap(await api.GET("/ide/sessions/{session_id}/notes", { params, signal }));
}

/** `POST /ide/notes/{id}/accept` : le back applique la proposition et rend la séance à jour. */
export async function acceptNote(noteId: string) {
  const params = { path: { note_id: noteId } };
  return unwrap(await api.POST("/ide/notes/{note_id}/accept", { params }));
}

/** `POST /ide/notes/{id}/reject` : refuse une proposition. */
export async function rejectNote(noteId: string) {
  const params = { path: { note_id: noteId } };
  return unwrap(await api.POST("/ide/notes/{note_id}/reject", { params }));
}

/** `GET /ide/preferences` : mode du professeur, minuterie, plafonds. */
export async function fetchPreferences(signal?: AbortSignal) {
  return unwrap(await api.GET("/ide/preferences", { signal }));
}

/** `PUT /ide/preferences` : remplace toutes les préférences du professeur. */
export async function putPreferences(body: Preferences) {
  return unwrap(await api.PUT("/ide/preferences", { body }));
}

/** `GET /ide/usage?session_id=` : jetons de la séance et du jour, plafonds, mode sur demande. */
export async function fetchUsage(sessionId: string, signal?: AbortSignal) {
  const params = { query: { session_id: sessionId } };
  return unwrap(await api.GET("/ide/usage", { params, signal }));
}
