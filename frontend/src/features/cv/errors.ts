import { ApiError, errorMessage } from "@/shared/api/errors";
import { en } from "@/shared/i18n/en";
import { t } from "@/shared/i18n/t";
import type { ProfileSaveErrorView } from "./components/viewTypes";

type KnownCode = keyof typeof en.cv.errors;

const isKnown = (code: string): code is KnownCode => Object.hasOwn(en.cv.errors, code);

/** Le code d'une erreur d'API, ou `null` pour toute autre erreur. */
export const errorCode = (error: unknown): string | null =>
  error instanceof ApiError ? error.code : null;

/** Use the interface copy for known errors and the server's message or fallback for others. */
export function cvErrorMessage(error: unknown): string {
  if (error instanceof ApiError && isKnown(error.code)) return t(`cv.errors.${error.code}`);
  return errorMessage(error);
}

/** Les chemins de champs que le back nomme dans un 422 (`details.fields`), sans aucune valeur. */
function fieldPaths(error: unknown): string[] {
  if (!(error instanceof ApiError)) return [];
  const details = error.details;
  if (typeof details !== "object" || details === null) return [];
  const fields = "fields" in details ? details.fields : null;
  return Array.isArray(fields) ? fields.filter((f): f is string => typeof f === "string") : [];
}

/** Une erreur d'enregistrement du profil → son message et, par chemin, le texte sous chaque champ fautif. */
export function profileSaveError(error: unknown): ProfileSaveErrorView {
  const fields: Record<string, string> = {};
  for (const path of fieldPaths(error)) fields[path] = t("cv.profile.fieldInvalid");
  const invalid = Object.keys(fields).length > 0;
  return { message: invalid ? t("cv.profile.invalid") : cvErrorMessage(error), fields };
}
