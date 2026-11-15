import { ApiError, errorMessage } from "@/shared/api/errors";
import { fr } from "@/shared/i18n/fr";
import { t } from "@/shared/i18n/t";
import type { AlertOut } from "./types";

type KnownCode = keyof typeof fr.applications.errors;

const isKnown = (code: string): code is KnownCode => Object.hasOwn(fr.applications.errors, code);

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null;

/** Le code d'une erreur d'API, ou `null` pour toute autre erreur. */
export const errorCode = (error: unknown): string | null =>
  error instanceof ApiError ? error.code : null;

/** Message français : le texte propre à un refus connu, sinon celui du back (ou le général). */
export function applicationsErrorMessage(error: unknown): string {
  if (error instanceof ApiError && isKnown(error.code)) {
    return t(`applications.errors.${error.code}`);
  }
  return errorMessage(error);
}

/** Une chaîne de `details.<key>` d'un refus, ou `null`. */
function detail(error: unknown, key: string): string | null {
  if (!(error instanceof ApiError) || !isRecord(error.details)) return null;
  const value = error.details[key];
  return typeof value === "string" ? value : null;
}

/** La fiche qui existe déjà pour une offre (409 `application_exists`). */
export const existingApplicationId = (error: unknown): string | null =>
  errorCode(error) === "application_exists" ? detail(error, "application_id") : null;

/** La saisie en une phrase déjà ouverte (409 `intake_in_progress`). */
export const openIntakeSessionId = (error: unknown): string | null =>
  errorCode(error) === "intake_in_progress" ? detail(error, "session_id") : null;

/** La session du kit déjà ouverte (409 `kit_in_progress`). */
export const openKitSessionId = (error: unknown): string | null =>
  errorCode(error) === "kit_in_progress" ? detail(error, "session_id") : null;

/** L'entretien déjà ouvert (409 `interview_in_progress`). */
export const openInterviewId = (error: unknown): string | null =>
  errorCode(error) === "interview_in_progress" ? detail(error, "interview_id") : null;

/** L'exécution du comité déjà ouverte pour l'offre (409 `committee_in_progress`). */
export const openCommitteeRunId = (error: unknown): string | null =>
  errorCode(error) === "committee_in_progress" ? detail(error, "run_id") : null;

/** Le refus d'une modification : le texte du serveur (il parle de la modification), sauf pièce absente. */
export const kitSaveErrorMessage = (error: unknown): string =>
  errorCode(error) === "kit_item_not_found" || errorCode(error) === "application_not_found"
    ? applicationsErrorMessage(error)
    : errorMessage(error);

const isAlert = (value: unknown): value is AlertOut =>
  isRecord(value) &&
  typeof value.application_id === "string" &&
  typeof value.level === "string" &&
  typeof value.message === "string";

/** Les fiches proches d'un 409 `application_duplicate` (`details.alerts`), ou `null` pour tout autre refus. */
export function duplicateAlerts(error: unknown): AlertOut[] | null {
  if (errorCode(error) !== "application_duplicate") return null;
  if (!(error instanceof ApiError) || !isRecord(error.details)) return null;
  const alerts = error.details.alerts;
  return Array.isArray(alerts) ? alerts.filter(isAlert) : null;
}
