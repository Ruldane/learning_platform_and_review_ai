import { ApiError, errorMessage } from "@/shared/api/errors";
import { en } from "@/shared/i18n/en";
import { t } from "@/shared/i18n/t";
import type { AlertOut } from "./types";

type KnownCode = keyof typeof en.applications.errors;

const isKnown = (code: string): code is KnownCode => Object.hasOwn(en.applications.errors, code);

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null;

/** The code of an API error, or `null` for any other error. */
export const errorCode = (error: unknown): string | null =>
  error instanceof ApiError ? error.code : null;

/** Use the interface copy for known errors and the server's message or fallback for others. */
export function applicationsErrorMessage(error: unknown): string {
  if (error instanceof ApiError && isKnown(error.code)) {
    return t(`applications.errors.${error.code}`);
  }
  return errorMessage(error);
}

/** A string from `details.<key>` of a refusal, or `null`. */
function detail(error: unknown, key: string): string | null {
  if (!(error instanceof ApiError) || !isRecord(error.details)) return null;
  const value = error.details[key];
  return typeof value === "string" ? value : null;
}

/** The record that already exists for a posting (409 `application_exists`). */
export const existingApplicationId = (error: unknown): string | null =>
  errorCode(error) === "application_exists" ? detail(error, "application_id") : null;

/** The one-sentence entry already open (409 `intake_in_progress`). */
export const openIntakeSessionId = (error: unknown): string | null =>
  errorCode(error) === "intake_in_progress" ? detail(error, "session_id") : null;

/** The kit session already open (409 `kit_in_progress`). */
export const openKitSessionId = (error: unknown): string | null =>
  errorCode(error) === "kit_in_progress" ? detail(error, "session_id") : null;

/** The interview already open (409 `interview_in_progress`). */
export const openInterviewId = (error: unknown): string | null =>
  errorCode(error) === "interview_in_progress" ? detail(error, "interview_id") : null;

/** The committee run already open for the posting (409 `committee_in_progress`). */
export const openCommitteeRunId = (error: unknown): string | null =>
  errorCode(error) === "committee_in_progress" ? detail(error, "run_id") : null;

/** A refused change: the server's text (it speaks of the change), except for a missing piece. */
export const kitSaveErrorMessage = (error: unknown): string =>
  errorCode(error) === "kit_item_not_found" || errorCode(error) === "application_not_found"
    ? applicationsErrorMessage(error)
    : errorMessage(error);

const isAlert = (value: unknown): value is AlertOut =>
  isRecord(value) &&
  typeof value.application_id === "string" &&
  typeof value.level === "string" &&
  typeof value.message === "string";

/** The near-matching records of a 409 `application_duplicate` (`details.alerts`), or `null` for any
 * other refusal. */
export function duplicateAlerts(error: unknown): AlertOut[] | null {
  if (errorCode(error) !== "application_duplicate") return null;
  if (!(error instanceof ApiError) || !isRecord(error.details)) return null;
  const alerts = error.details.alerts;
  return Array.isArray(alerts) ? alerts.filter(isAlert) : null;
}
