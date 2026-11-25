import { ApiError, errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import type { SubmissionRefusalView } from "./types";

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null;

/** The code of an API error, or `null` for any other error. */
export const errorCode = (error: unknown): string | null =>
  error instanceof ApiError ? error.code : null;

/** 409 refusals whose French text is kept here, so it is always shown. */
const CONFLICTS = [
  "project_not_ready",
  "review_in_progress",
  "project_validated",
  "brief_not_failed",
  "project_not_validated",
  "drafts_present",
  "entry_already_added",
  "profile_required",
  "profile_draft_pending",
  "profile_projects_full",
] as const;

type Conflict = (typeof CONFLICTS)[number];

const isConflict = (code: string): code is Conflict =>
  (CONFLICTS as readonly string[]).includes(code);

/** A readable refusal: the French text for a known code (409), otherwise the server's message. */
export function readableMessage(error: unknown): string {
  const code = errorCode(error);
  if (code !== null && isConflict(code)) return t(`projects.errors.${code}`);
  if (code === "file_too_large") return t("projects.errors.tooLarge");
  return errorMessage(error);
}

/** The evaluation already running (409 `review_in_progress`, `details.session_id`): followed. */
export function openReviewSession(error: unknown): string | null | undefined {
  if (errorCode(error) !== "review_in_progress" || !(error instanceof ApiError)) return undefined;
  const id = isRecord(error.details) ? error.details.session_id : null;
  return typeof id === "string" ? id : null;
}

/** The fields the server refuses (`details.fields` of a 422, with no value). */
function refusedFields(error: unknown): string[] {
  if (errorCode(error) !== "validation_error" || !(error instanceof ApiError)) return [];
  const fields = isRecord(error.details) ? error.details.fields : null;
  return Array.isArray(fields) ? fields.filter((f): f is string => typeof f === "string") : [];
}

/** A submission refusal, sorted by form field; `general` for any other refusal. */
export interface SubmitFailure {
  refusal: SubmissionRefusalView | null;
  general: string | null;
}

const isScreenshots = (field: string) =>
  field === "screenshots" || field.startsWith("screenshots.");

/** A 422 names its fields (`repo_url`, `description`, `screenshots`, `screenshots.N`). */
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

/** A refusal to add to the profile: the plain message, and whether the master profile is next. */
export interface AddFailure {
  message: string;
  /** The master profile must be opened (missing, or a draft is waiting). */
  profileLink: boolean;
}

export function addFailure(error: unknown): AddFailure {
  const code = errorCode(error);
  return {
    message: readableMessage(error),
    profileLink: code === "profile_required" || code === "profile_draft_pending",
  };
}
