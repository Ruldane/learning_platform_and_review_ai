import { ApiError, errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import type { FormErrorView } from "./components/viewTypes";

/** Les refus de `POST /postings` qui ont un texte à eux (le message du back ne sert qu'en repli). */
const KNOWN = [
  "posting_source",
  "posting_unreadable",
  "posting_too_short",
  "invalid_url",
  "url_forbidden",
] as const;

type KnownCode = (typeof KNOWN)[number];

const isKnown = (code: string): code is KnownCode => (KNOWN as readonly string[]).includes(code);

/** Une erreur d'ajout d'offre → code d'API et message français (jamais le contenu saisi). */
export function postingFormError(error: unknown): FormErrorView {
  if (error instanceof ApiError && isKnown(error.code)) {
    return { code: error.code, message: t(`gap.errors.${error.code}`) };
  }
  return {
    code: error instanceof ApiError ? error.code : "unknown",
    message: errorMessage(error),
  };
}
