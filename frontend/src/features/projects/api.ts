import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { DraftKind, ProfileEntryIn, SubmissionView } from "./types";

/** `GET /projects` : tous les projets, dans l'ordre du programme (semaine, rang). */
export async function fetchProjects(signal?: AbortSignal) {
  return unwrap(await api.GET("/projects", { signal }));
}

/** `GET /projects/{id}` : l'énoncé, les rendus, la dernière évaluation et les brouillons. 404 `project_not_found`. */
export async function fetchProject(projectId: string, signal?: AbortSignal) {
  return unwrap(
    await api.GET("/projects/{project_id}", {
      params: { path: { project_id: projectId } },
      signal,
    }),
  );
}

/** Le corps multipart d'un rendu : le lien et la description s'ils existent, une partie `screenshots` par capture. */
export function submissionForm(submission: SubmissionView): FormData {
  const form = new FormData();
  if (submission.repoUrl) form.append("repo_url", submission.repoUrl);
  if (submission.description) form.append("description", submission.description);
  for (const file of submission.screenshots) form.append("screenshots", file);
  return form;
}

/**
 * `POST /projects/{id}/submit` (202 `{session_id}`) : multipart, le navigateur pose la frontière.
 * 409 `project_not_ready`, `review_in_progress` (`details.session_id`) ou `project_validated` ;
 * 422 `details.fields` ; 413 ; 503.
 */
export async function submitProject(projectId: string, submission: SubmissionView) {
  const form = submissionForm(submission);
  // Le contrat type les fichiers comme des chaînes : le corps réel est le formulaire.
  return unwrap(
    await api.POST("/projects/{project_id}/submit", {
      params: { path: { project_id: projectId } },
      body: {},
      bodySerializer: () => form,
    }),
  );
}

/** `PATCH /projects/{id}/drafts/{kind}` : le texte retouché ; rend le projet avec ses brouillons relus. */
export async function saveDraft(projectId: string, kind: DraftKind, content: string) {
  return unwrap(
    await api.PATCH("/projects/{project_id}/drafts/{kind}", {
      params: { path: { project_id: projectId, kind } },
      body: { content },
    }),
  );
}

/** `POST /projects/{id}/profile-entry` : l'entrée entre au profil maître (nouvelle version). 409 selon le cas. */
export async function addToProfile(projectId: string, entry: ProfileEntryIn) {
  return unwrap(
    await api.POST("/projects/{project_id}/profile-entry", {
      params: { path: { project_id: projectId } },
      body: entry,
    }),
  );
}

/** `POST /projects/{id}/brief` (202 `{session_id}`) : réécrire un énoncé en échec. 409 `brief_not_failed`. */
export async function retryBrief(projectId: string) {
  return unwrap(
    await api.POST("/projects/{project_id}/brief", {
      params: { path: { project_id: projectId } },
    }),
  );
}

/**
 * `POST /projects/{id}/drafts` (202 `{session_id}`) : réécrire les brouillons d'un projet validé qui
 * n'en a pas. 409 `project_not_validated`, `drafts_present` ou `review_in_progress`
 * (`details.session_id`).
 */
export async function regenerateDrafts(projectId: string) {
  return unwrap(
    await api.POST("/projects/{project_id}/drafts", {
      params: { path: { project_id: projectId } },
    }),
  );
}
