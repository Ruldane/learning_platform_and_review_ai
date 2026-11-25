import { ApiError, errorMessage } from "@/shared/api/errors";
import { en } from "@/shared/i18n/en";
import { t } from "@/shared/i18n/t";

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null;

/** The code of an API error, or `null` for any other error. */
export const errorCode = (error: unknown): string | null =>
  error instanceof ApiError ? error.code : null;

/** The sweep already running (409 `radar_in_progress`, `details.run_id`), or `null`. */
export function openRunId(error: unknown): string | null {
  if (errorCode(error) !== "radar_in_progress" || !(error instanceof ApiError)) return null;
  const id = isRecord(error.details) ? error.details.run_id : null;
  return typeof id === "string" ? id : null;
}

/** The fields the server refuses (`details.fields` of a 422, with no value). */
function refusedFields(error: unknown): string[] {
  if (errorCode(error) !== "validation_error" || !(error instanceof ApiError)) return [];
  const fields = isRecord(error.details) ? error.details.fields : null;
  return Array.isArray(fields) ? fields.filter((f): f is string => typeof f === "string") : [];
}

/** A launch refusal, sorted by form field; `general` for any other refusal. */
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

type KnownCode = keyof typeof en.radar.failure.codes;

const isKnown = (code: string): code is KnownCode => Object.hasOwn(en.radar.failure.codes, code);

/** Why a sweep failed, in plain words: the known code, otherwise an unexpected failure. */
export function failureReason(code: string | null): string {
  return code !== null && isKnown(code)
    ? t(`radar.failure.codes.${code}`)
    : t("radar.failure.other");
}
