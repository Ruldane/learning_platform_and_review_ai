import { ApiError, errorMessage } from "@/shared/api/errors";
import { fr } from "@/shared/i18n/fr";
import { t } from "@/shared/i18n/t";

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null;

/** Le code d'une erreur d'API, ou `null` pour toute autre erreur. */
export const errorCode = (error: unknown): string | null =>
  error instanceof ApiError ? error.code : null;

/** Le relevé déjà en cours (409 `radar_in_progress`, `details.run_id`), ou `null`. */
export function openRunId(error: unknown): string | null {
  if (errorCode(error) !== "radar_in_progress" || !(error instanceof ApiError)) return null;
  const id = isRecord(error.details) ? error.details.run_id : null;
  return typeof id === "string" ? id : null;
}

/** Les champs que le serveur refuse (`details.fields` d'un 422, sans aucune valeur). */
function refusedFields(error: unknown): string[] {
  if (errorCode(error) !== "validation_error" || !(error instanceof ApiError)) return [];
  const fields = isRecord(error.details) ? error.details.fields : null;
  return Array.isArray(fields) ? fields.filter((f): f is string => typeof f === "string") : [];
}

/** Un refus du lancement, rangé par champ du formulaire ; `general` pour tout autre refus. */
export interface LaunchErrors {
  role?: string;
  zone?: string;
  general?: string;
}

export function launchErrors(error: unknown): LaunchErrors {
  if (errorCode(error) === "radar_role_required") {
    return { role: t("radar.errors.radar_role_required") };
  }
  const fields = refusedFields(error);
  if (fields.length > 0) {
    return {
      role: fields.includes("role") ? t("radar.errors.role") : undefined,
      zone: fields.includes("zone") ? t("radar.errors.zone") : undefined,
      general: fields.some((f) => f !== "role" && f !== "zone") ? errorMessage(error) : undefined,
    };
  }
  return { general: errorMessage(error) };
}

type KnownCode = keyof typeof fr.radar.failure.codes;

const isKnown = (code: string): code is KnownCode => Object.hasOwn(fr.radar.failure.codes, code);

/** Pourquoi un relevé a échoué, en clair : le code connu, sinon une panne inattendue. */
export function failureReason(code: string | null): string {
  return code !== null && isKnown(code)
    ? t(`radar.failure.codes.${code}`)
    : t("radar.failure.other");
}
