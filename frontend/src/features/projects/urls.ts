import { apiBaseUrl } from "@/shared/api/client";

/**
 * L'adresse d'une capture d'un rendu (`GET /projects/{id}/screenshots/{n}?submission=`) : `number`
 * de 1 à 5, `submission` 1 pour le dernier rendu, 2 pour celui d'avant. Une image se charge sans
 * en-tête : l'adresse suffit à `<img>`.
 */
export const screenshotUrl = (projectId: string, number: number, submission: number): string =>
  `${apiBaseUrl}/api/v1/projects/${projectId}/screenshots/${number}?submission=${submission}`;
