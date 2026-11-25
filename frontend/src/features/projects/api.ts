import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import { runSourceHeaders, type RunSource } from "@/shared/lib/runSource";
import type { DraftKind, GithubCommitSelection, ProfileEntryIn, SubmissionView } from "./types";

/** `GET /projects`: all projects, in program order (week, rank). */
export async function fetchProjects(signal?: AbortSignal) {
  return unwrap(await api.GET("/projects", { signal }));
}

/**
 * `GET /projects/{id}`: the brief, submissions, latest evaluation and drafts. 404
 * `project_not_found`.
 */
export async function fetchProject(projectId: string, signal?: AbortSignal) {
  return unwrap(
    await api.GET("/projects/{project_id}", {
      params: { path: { project_id: projectId } },
      signal,
    }),
  );
}

/**
 * The multipart body of a submission: the link and description if present, one
 * `screenshots` part per capture.
 */
export function submissionForm(submission: SubmissionView): FormData {
  const form = new FormData();
  if (submission.repoUrl) form.append("repo_url", submission.repoUrl);
  if (submission.description) form.append("description", submission.description);
  if (submission.githubClaimId) form.append("github_claim_id", submission.githubClaimId);
  for (const file of submission.screenshots) form.append("screenshots", file);
  return form;
}

export async function fetchGithubProofs(projectId: string, signal?: AbortSignal) {
  return unwrap(
    await api.GET("/projects/{project_id}/github-claims", {
      params: { path: { project_id: projectId } },
      signal,
    }),
  );
}

export async function requestGithubClaim(projectId: string, selection: GithubCommitSelection) {
  return unwrap(
    await api.POST("/projects/{project_id}/github-claims", {
      params: { path: { project_id: projectId } },
      body: { repo_url: selection.repoUrl, sha: selection.sha },
    }),
  );
}

/**
 * `POST /projects/{id}/submit` (202 `{session_id}`): multipart; the browser sets the boundary.
 * 409 `project_not_ready`, `review_in_progress` (`details.session_id`) or `project_validated`;
 * 422 `details.fields` ; 413 ; 503.
 */
export async function submitProject(projectId: string, submission: SubmissionView) {
  const form = submissionForm(submission);
  // The contract types files as strings: the real body is the form.
  return unwrap(
    await api.POST("/projects/{project_id}/submit", {
      params: { path: { project_id: projectId } },
      body: {},
      bodySerializer: () => form,
    }),
  );
}

/**
 * `PATCH /projects/{id}/drafts/{kind}`: the edited text; returns the project with its drafts
 * relus.
 */
export async function saveDraft(projectId: string, kind: DraftKind, content: string) {
  return unwrap(
    await api.PATCH("/projects/{project_id}/drafts/{kind}", {
      params: { path: { project_id: projectId, kind } },
      body: { content },
    }),
  );
}

/**
 * `POST /projects/{id}/profile-entry`: the entry goes into the master profile (new version). 409
 * depending on the case.
 */
export async function addToProfile(projectId: string, entry: ProfileEntryIn) {
  return unwrap(
    await api.POST("/projects/{project_id}/profile-entry", {
      params: { path: { project_id: projectId } },
      body: entry,
    }),
  );
}

/**
 * `POST /projects/{id}/brief` (202 `{session_id}`): rewrite a failed brief. 409
 * `brief_not_failed`.
 */
export async function retryBrief(projectId: string, source?: RunSource) {
  return unwrap(
    await api.POST("/projects/{project_id}/brief", {
      params: { path: { project_id: projectId } },
      headers: runSourceHeaders(source),
    }),
  );
}

/**
 * `POST /projects/{id}/drafts` (202 `{session_id}`): rewrite the drafts of a validated project
 * with none. 409 `project_not_validated`, `drafts_present` or `review_in_progress`
 * (`details.session_id`).
 */
export async function regenerateDrafts(projectId: string) {
  return unwrap(
    await api.POST("/projects/{project_id}/drafts", {
      params: { path: { project_id: projectId } },
    }),
  );
}
