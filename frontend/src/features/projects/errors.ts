import { ApiError, errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import type { SubmissionRefusalView } from "./types";

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null;

/** Le code d'une erreur d'API, ou `null` pour toute autre erreur. */
export const errorCode = (error: unknown): string | null =>
  error instanceof ApiError ? error.code : null;

/** Les refus 409 dont le texte français est écrit ici (le serveur en envoie un, mais celui-ci est garanti). */
const CONFLICTS = [
  "project_not_ready",
  "review_in_progress",
  "project_validated",
  "brief_not_failed",
  "project_not_validated",
  "entry_already_added",
  "profile_required",
  "profile_draft_pending",
  "profile_projects_full",
] as const;

type Conflict = (typeof CONFLICTS)[number];

const isConflict = (code: string): code is Conflict =>
  (CONFLICTS as readonly string[]).includes(code);

/** Un refus lisible : le texte français du code connu (409), sinon le message du serveur. */
export function readableMessage(error: unknown): string {
  const code = errorCode(error);
  if (code !== null && isConflict(code)) return t(`projects.errors.${code}`);
  if (code === "file_too_large") return t("projects.errors.tooLarge");
  return errorMessage(error);
}

/** L'évaluation déjà en cours (409 `review_in_progress`, `details.session_id`) : on la suit. */
export function openReviewSession(error: unknown): string | null | undefined {
  if (errorCode(error) !== "review_in_progress" || !(error instanceof ApiError)) return undefined;
  const id = isRecord(error.details) ? error.details.session_id : null;
  return typeof id === "string" ? id : null;
}

/** Les champs que le serveur refuse (`details.fields` d'un 422, sans aucune valeur). */
function refusedFields(error: unknown): string[] {
  if (errorCode(error) !== "validation_error" || !(error instanceof ApiError)) return [];
  const fields = isRecord(error.details) ? error.details.fields : null;
  return Array.isArray(fields) ? fields.filter((f): f is string => typeof f === "string") : [];
}

/** Un refus du rendu, rangé par champ du formulaire ; `general` pour tout autre refus. */
export interface SubmitFailure {
  refusal: SubmissionRefusalView | null;
  general: string | null;
}

const isScreenshots = (field: string) =>
  field === "screenshots" || field.startsWith("screenshots.");

/** Un 422 nomme ses champs (`repo_url`, `description`, `screenshots`, `screenshots.N`) : chacun a son message. */
export function submitFailure(error: unknown): SubmitFailure {
  const fields = refusedFields(error);
  if (fields.length === 0) return { refusal: null, general: readableMessage(error) };
  const refusal: SubmissionRefusalView = {};
  if (fields.includes("repo_url") && fields.includes("description")) {
    refusal.missing = t("projects.submission.errors.missing");
  } else {
    if (fields.includes("repo_url")) refusal.repoUrl = t("projects.submission.errors.repoUrl");
    if (fields.includes("description")) {
      refusal.description = t("projects.submission.errors.description");
    }
  }
  if (fields.some(isScreenshots)) refusal.screenshots = t("projects.errors.screenshots");
  const other = fields.some(
    (field) => field !== "repo_url" && field !== "description" && !isScreenshots(field),
  );
  return { refusal, general: other ? errorMessage(error) : null };
}

/** Un refus de l'ajout au profil : le message en clair, et si le profil maître est la suite à donner. */
export interface AddFailure {
  message: string;
  /** Le profil maître est à ouvrir (absent, ou un brouillon attend). */
  profileLink: boolean;
}

export function addFailure(error: unknown): AddFailure {
  const code = errorCode(error);
  return {
    message: readableMessage(error),
    profileLink: code === "profile_required" || code === "profile_draft_pending",
  };
}
