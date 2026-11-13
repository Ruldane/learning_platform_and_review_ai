import { ApiError, errorMessage } from "@/shared/api/errors";
import { fr } from "@/shared/i18n/fr";
import { t } from "@/shared/i18n/t";

type CaptureErrorCode = keyof typeof fr.capture.errors;

const isCaptureError = (code: string): code is CaptureErrorCode =>
  Object.hasOwn(fr.capture.errors, code);

/**
 * Message français d'un refus de la capture : les codes connus (lien refusé, fichier introuvable,
 * import en échec `document_failed`) ont leur texte, les autres gardent celui du serveur.
 */
export function captureErrorMessage(error: unknown): string {
  if (error instanceof ApiError && isCaptureError(error.code)) {
    return t(`capture.errors.${error.code}`);
  }
  return errorMessage(error);
}

/** Même table pour l'échec d'une session déjà lancée (`run.failed` : `document_not_indexed`…). */
export function failureMessage(code: string, message: string): string {
  return isCaptureError(code) ? t(`capture.errors.${code}`) : message;
}
