import { useState } from "react";
import type { CvDocuments, PdfChoice } from "../components/viewTypes";

const NOTHING: PdfChoice = { file: null, problem: null };

/**
 * The two PDFs of the CV step, kept by the page: changing step does not lose them (the file
 * field itself unmounts, but the chosen file stays stated on screen and ready to send).
 */
export function useCvDocuments(): CvDocuments {
  const [cv, setCv] = useState<PdfChoice>(NOTHING);
  const [linkedin, setLinkedin] = useState<PdfChoice>(NOTHING);
  return { cv, linkedin, setCv, setLinkedin };
}
