import { ApiError, errorMessage } from "@/shared/api/errors";
import { en } from "@/shared/i18n/en";
import { t } from "@/shared/i18n/t";

type CaptureErrorCode = keyof typeof en.capture.errors;

const isCaptureError = (code: string): code is CaptureErrorCode =>
  Object.hasOwn(en.capture.errors, code);

/**
 * French message for a capture refusal: the known codes (link refused, file not found,
 * import failed `document_failed`) have their text; the others keep the server's message.
 */
export function captureErrorMessage(error: unknown): string {
  if (error instanceof ApiError && isCaptureError(error.code)) {
    return t(`capture.errors.${error.code}`);
  }
  return errorMessage(error);
}

/** Same table for a session that already failed (`run.failed`: `document_not_indexed`…). */
export function failureMessage(code: string, message: string): string {
  return isCaptureError(code) ? t(`capture.errors.${code}`) : message;
}
