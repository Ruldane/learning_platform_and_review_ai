import { t } from "@/shared/i18n/t";

export const MAX_PDF_BYTES = 10 * 1024 * 1024;

/** Le message qui refuse ce fichier, ou `null` s'il est un PDF de 10 Mo au plus. */
export function pdfProblem(file: File): string | null {
  const named = file.name.toLowerCase().endsWith(".pdf");
  if (!named || (file.type !== "" && file.type !== "application/pdf")) {
    return t("onboarding.cv.notPdf");
  }
  return file.size > MAX_PDF_BYTES ? t("onboarding.cv.tooBig") : null;
}
