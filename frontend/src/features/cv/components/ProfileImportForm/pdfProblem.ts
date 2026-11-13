import { t } from "@/shared/i18n/t";
import { MAX_PDF_BYTES } from "../viewTypes";

/** Le message qui refuse ce fichier, ou `null` s'il est un PDF de 10 Mo au plus. */
export function pdfProblem(file: File): string | null {
  const named = file.name.toLowerCase().endsWith(".pdf");
  if (!named || (file.type !== "" && file.type !== "application/pdf")) {
    return t("cv.import.notPdf");
  }
  return file.size > MAX_PDF_BYTES ? t("cv.import.tooBig") : null;
}
