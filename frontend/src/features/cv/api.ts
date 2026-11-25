import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import { runSourceHeaders, type RunSource } from "@/shared/lib/runSource";
import type { MasterProfileData } from "./types";

const templatePath = (templateId: string) => ({ params: { path: { template_id: templateId } } });
const reviewPath = (reviewId: string) => ({ params: { path: { review_id: reviewId } } });
const versionPath = (versionId: string) => ({ params: { path: { version_id: versionId } } });

/** `GET /profile`: the validated version, the draft if it is newer, the capture in progress. */
export async function fetchProfile(signal?: AbortSignal) {
  return unwrap(await api.GET("/profile", { signal }));
}

/** `GET /profile/versions`: all versions, newest first. */
export async function fetchProfileVersions(signal?: AbortSignal) {
  return unwrap(await api.GET("/profile/versions", { signal }));
}

/**
 * `PUT /profile`: a new validated version. `baseVersion` is the last version read
 * (`null` if there is none); 409 `profile_conflict` otherwise, 422 `validation_error`
 * (`details.fields`, never the value).
 */
export async function putProfile(data: MasterProfileData, baseVersion: number | null) {
  return unwrap(await api.PUT("/profile", { body: { base_version: baseVersion, data } }));
}

export interface ProfileImport {
  cv: File;
  linkedin?: File;
  note?: string;
}

/**
 * `POST /profile/import` (202): multipart, the browser sets the boundary. 409
 * `capture_in_progress`, 413 `file_too_large`, 415 `unsupported_file_type`.
 */
export async function importProfile({ cv, linkedin, note }: ProfileImport, source?: RunSource) {
  const form = new FormData();
  form.append("cv", cv);
  if (linkedin) form.append("linkedin", linkedin);
  if (note) form.append("note", note);
  // The contract types a file as a string: the real body is the form.
  return unwrap(
    await api.POST("/profile/import", {
      body: { cv: "" },
      bodySerializer: () => form,
      headers: runSourceHeaders(source),
    }),
  );
}

/** `GET /cv/templates`: the unarchived templates, newest first. */
export async function fetchTemplates(signal?: AbortSignal) {
  return unwrap(await api.GET("/cv/templates", { signal }));
}

/** `GET /cv/templates/{id}`: the template, its replaced fonts and its layout gaps. */
export async function fetchTemplate(templateId: string, signal?: AbortSignal) {
  return unwrap(
    await api.GET("/cv/templates/{template_id}", { ...templatePath(templateId), signal }),
  );
}

export interface TemplateSource {
  name: string;
  /** A PDF sent, or the identifier of a document already imported: one of the two. */
  file?: File;
  documentId?: string;
}

/**
 * `POST /cv/templates` (202). 409 `vision_unavailable` and `capture_in_progress`, 413, 415, 422
 * `pdf_unreadable` and `validation_error`, 404 `document_not_found`.
 */
export async function createTemplate(
  { name, file, documentId }: TemplateSource,
  source?: RunSource,
) {
  const form = new FormData();
  form.append("name", name);
  if (file) form.append("file", file);
  if (documentId) form.append("document_id", documentId);
  return unwrap(
    await api.POST("/cv/templates", {
      body: { name },
      bodySerializer: () => form,
      headers: runSourceHeaders(source),
    }),
  );
}

/** `POST /cv/templates/{id}/activate` (204): the only active template; 409 `template_not_ready`. */
export async function activateTemplate(templateId: string): Promise<void> {
  unwrap(await api.POST("/cv/templates/{template_id}/activate", templatePath(templateId)));
}

/** `GET /documents`: the imported documents (to reuse a PDF already sent). */
export async function fetchDocuments(signal?: AbortSignal) {
  return unwrap(await api.GET("/documents", { signal }));
}

/** `GET /postings`: the postings, to name the CV versions. */
export async function fetchPostingTitles(signal?: AbortSignal) {
  return unwrap(await api.GET("/postings", { signal }));
}

/**
 * `POST /cv/reviews` (202). 404 `posting_not_found`; 409 `posting_not_ready`,
 * `profile_required`, `template_required`, `review_in_progress` (`details.review_id`);
 * 503 `engine_unavailable`.
 */
export async function startReview(postingId: string, source?: RunSource) {
  return unwrap(
    await api.POST("/cv/reviews", {
      body: { posting_id: postingId },
      headers: runSourceHeaders(source),
    }),
  );
}

/**
 * `GET /cv/reviews/{id}`: the review, its modifications and versions; 404 `review_not_found`.
 */
export async function fetchReview(reviewId: string, signal?: AbortSignal) {
  return unwrap(await api.GET("/cv/reviews/{review_id}", { ...reviewPath(reviewId), signal }));
}

export interface Decision {
  status: "accepted" | "refused";
  after?: string;
  confirm?: boolean;
}

/**
 * `PATCH /cv/modifications/{id}`: accepts or refuses; `after`: rewritten text, revalidated;
 * `confirm` for a modification marked « à confirmer ». 409 `review_closed`,
 * `confirmation_required`, `fact_not_found`, `profile_conflict`; 422 `keyword_not_in_profile`.
 */
export async function decideModification(modificationId: string, decision: Decision) {
  return unwrap(
    await api.PATCH("/cv/modifications/{modification_id}", {
      params: { path: { modification_id: modificationId } },
      body: { ...decision, confirm: decision.confirm ?? false },
    }),
  );
}

/**
 * `PATCH /cv/reviews/{id}/modifications`: a grouped decision; the « à confirmer » ones
 * come back in `skipped`.
 */
export async function decideBulk(reviewId: string, ids: string[], status: Decision["status"]) {
  return unwrap(
    await api.PATCH("/cv/reviews/{review_id}/modifications", {
      ...reviewPath(reviewId),
      body: { ids, status },
    }),
  );
}

/**
 * `POST /cv/reviews/{id}/generate` (202): creates the version and resumes the output question.
 * 409 `review_closed`, `generation_in_progress` (`details.version_id`), `review_not_waiting`;
 * 503.
 */
export async function generateCv(reviewId: string, allowExtraPages: boolean) {
  return unwrap(
    await api.POST("/cv/reviews/{review_id}/generate", {
      ...reviewPath(reviewId),
      body: { allow_extra_pages: allowExtraPages },
    }),
  );
}

/** `GET /cv/versions`: all CV versions, newest first. */
export async function fetchVersions(signal?: AbortSignal) {
  return unwrap(await api.GET("/cv/versions", { signal }));
}

/** `GET /cv/versions/{id}` ; 404 `version_not_found`. */
export async function fetchVersion(versionId: string, signal?: AbortSignal) {
  return unwrap(await api.GET("/cv/versions/{version_id}", { ...versionPath(versionId), signal }));
}
