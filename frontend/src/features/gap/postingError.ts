import { ApiError, errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import type { FormErrorView } from "./components/viewTypes";

/** Refusals of `POST /postings` that have their own text (the backend message is a fallback). */
const KNOWN = [
  "posting_source",
  "posting_unreadable",
  "posting_too_short",
  "invalid_url",
  "url_forbidden",
] as const;

type KnownCode = (typeof KNOWN)[number];

const isKnown = (code: string): code is KnownCode => (KNOWN as readonly string[]).includes(code);

/** A posting-add error → API code and its French message (never the typed content). */
export function postingFormError(error: unknown): FormErrorView {
  if (error instanceof ApiError && isKnown(error.code)) {
    return { code: error.code, message: t(`gap.errors.${error.code}`) };
  }
  return {
    code: error instanceof ApiError ? error.code : "unknown",
    message: errorMessage(error),
  };
}
