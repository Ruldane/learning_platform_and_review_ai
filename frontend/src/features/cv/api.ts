import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { MasterProfileData } from "./types";

const templatePath = (templateId: string) => ({ params: { path: { template_id: templateId } } });
const reviewPath = (reviewId: string) => ({ params: { path: { review_id: reviewId } } });
const versionPath = (versionId: string) => ({ params: { path: { version_id: versionId } } });

/** `GET /profile` : la version validée, le brouillon s'il est plus récent, la capture en cours. */
export async function fetchProfile(signal?: AbortSignal) {
  return unwrap(await api.GET("/profile", { signal }));
}

/** `GET /profile/versions` : toutes les versions, la plus récente d'abord. */
export async function fetchProfileVersions(signal?: AbortSignal) {
  return unwrap(await api.GET("/profile/versions", { signal }));
}

/**
 * `PUT /profile` : une nouvelle version validée. `baseVersion` est la dernière version relue
 * (`null` s'il n'y en a aucune) ; 409 `profile_conflict` sinon, 422 `validation_error`
 * (`details.fields`, jamais la valeur).
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
 * `POST /profile/import` (202) : multipart, le navigateur pose la frontière. 409
 * `capture_in_progress`, 413 `file_too_large`, 415 `unsupported_file_type`.
 */
export async function importProfile({ cv, linkedin, note }: ProfileImport) {
  const form = new FormData();
  form.append("cv", cv);
  if (linkedin) form.append("linkedin", linkedin);
  if (note) form.append("note", note);
  // Le contrat type un fichier comme une chaîne : le corps réel est le formulaire.
  return unwrap(
    await api.POST("/profile/import", { body: { cv: "" }, bodySerializer: () => form }),
  );
}

/** `GET /cv/templates` : les modèles non archivés, le plus récent d'abord. */
export async function fetchTemplates(signal?: AbortSignal) {
  return unwrap(await api.GET("/cv/templates", { signal }));
}

/** `GET /cv/templates/{id}` : le modèle, ses polices remplacées et ses écarts de mise en page. */
export async function fetchTemplate(templateId: string, signal?: AbortSignal) {
  return unwrap(
    await api.GET("/cv/templates/{template_id}", { ...templatePath(templateId), signal }),
  );
}

export interface TemplateSource {
  name: string;
  /** Un PDF envoyé, ou l'identifiant d'un document déjà importé : l'un des deux. */
  file?: File;
  documentId?: string;
}

/**
 * `POST /cv/templates` (202). 409 `vision_unavailable` et `capture_in_progress`, 413, 415, 422
 * `pdf_unreadable` et `validation_error`, 404 `document_not_found`.
 */
export async function createTemplate({ name, file, documentId }: TemplateSource) {
  const form = new FormData();
  form.append("name", name);
  if (file) form.append("file", file);
  if (documentId) form.append("document_id", documentId);
  return unwrap(await api.POST("/cv/templates", { body: { name }, bodySerializer: () => form }));
}

/** `POST /cv/templates/{id}/activate` (204) : le seul modèle actif ; 409 `template_not_ready`. */
export async function activateTemplate(templateId: string): Promise<void> {
  unwrap(await api.POST("/cv/templates/{template_id}/activate", templatePath(templateId)));
}

/** `GET /documents` : les documents importés (pour réutiliser un PDF déjà envoyé). */
export async function fetchDocuments(signal?: AbortSignal) {
  return unwrap(await api.GET("/documents", { signal }));
}

/** `GET /postings` : les offres, pour nommer les versions de CV. */
export async function fetchPostingTitles(signal?: AbortSignal) {
  return unwrap(await api.GET("/postings", { signal }));
}

/**
 * `POST /cv/reviews` (202). 404 `posting_not_found` ; 409 `posting_not_ready`, `profile_required`,
 * `template_required`, `review_in_progress` (`details.review_id`) ; 503 `engine_unavailable`.
 */
export async function startReview(postingId: string) {
  return unwrap(await api.POST("/cv/reviews", { body: { posting_id: postingId } }));
}

/** `GET /cv/reviews/{id}` : la revue, ses modifications, ses versions ; 404 `review_not_found`. */
export async function fetchReview(reviewId: string, signal?: AbortSignal) {
  return unwrap(await api.GET("/cv/reviews/{review_id}", { ...reviewPath(reviewId), signal }));
}

export interface Decision {
  status: "accepted" | "refused";
  after?: string;
  confirm?: boolean;
}

/**
 * `PATCH /cv/modifications/{id}` : accepte ou refuse ; `after` : texte réécrit, revalidé ; `confirm`
 * pour une modification « à confirmer ». 409 `review_closed`, `confirmation_required`,
 * `fact_not_found`, `profile_conflict` ; 422 `keyword_not_in_profile`.
 */
export async function decideModification(modificationId: string, decision: Decision) {
  return unwrap(
    await api.PATCH("/cv/modifications/{modification_id}", {
      params: { path: { modification_id: modificationId } },
      body: { ...decision, confirm: decision.confirm ?? false },
    }),
  );
}

/** `PATCH /cv/reviews/{id}/modifications` : décision groupée ; les « à confirmer » reviennent dans `skipped`. */
export async function decideBulk(reviewId: string, ids: string[], status: Decision["status"]) {
  return unwrap(
    await api.PATCH("/cv/reviews/{review_id}/modifications", {
      ...reviewPath(reviewId),
      body: { ids, status },
    }),
  );
}

/**
 * `POST /cv/reviews/{id}/generate` (202) : crée la version et reprend la question de sortie. 409
 * `review_closed`, `generation_in_progress` (`details.version_id`), `review_not_waiting` ; 503.
 */
export async function generateCv(reviewId: string, allowExtraPages: boolean) {
  return unwrap(
    await api.POST("/cv/reviews/{review_id}/generate", {
      ...reviewPath(reviewId),
      body: { allow_extra_pages: allowExtraPages },
    }),
  );
}

/** `GET /cv/versions` : toutes les versions de CV, la plus récente d'abord. */
export async function fetchVersions(signal?: AbortSignal) {
  return unwrap(await api.GET("/cv/versions", { signal }));
}

/** `GET /cv/versions/{id}` ; 404 `version_not_found`. */
export async function fetchVersion(versionId: string, signal?: AbortSignal) {
  return unwrap(await api.GET("/cv/versions/{version_id}", { ...versionPath(versionId), signal }));
}
