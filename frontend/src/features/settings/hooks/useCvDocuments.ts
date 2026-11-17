import { useState } from "react";
import type { CvDocuments, PdfChoice } from "../components/viewTypes";

const NOTHING: PdfChoice = { file: null, problem: null };

/**
 * Les deux PDF de l'étape CV, gardés par la page : changer d'étape ne les perd pas (le champ de
 * fichier, lui, se démonte, mais le fichier retenu reste dit à l'écran et prêt à partir).
 */
export function useCvDocuments(): CvDocuments {
  const [cv, setCv] = useState<PdfChoice>(NOTHING);
  const [linkedin, setLinkedin] = useState<PdfChoice>(NOTHING);
  return { cv, linkedin, setCv, setLinkedin };
}
