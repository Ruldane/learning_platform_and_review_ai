import { apiBaseUrl } from "@/shared/api/client";

const cvUrl = (path: string) => `${apiBaseUrl}/api/v1/cv${path}`;

/** Le PDF d'une version (téléchargement : le nom `CV_….pdf` vient de l'en-tête du serveur). */
export const versionPdfUrl = (versionId: string) => cvUrl(`/versions/${versionId}/pdf`);

/** L'image de la page `n` (depuis 1) d'une version prête. */
export const versionPageUrl = (versionId: string, n: number) =>
  cvUrl(`/versions/${versionId}/pages/${n}`);

/**
 * L'image de la page `n` du CV d'origine ou du rendu de la passe courante d'un modèle. `pass`
 * change à chaque passe : le navigateur ne garde pas l'ancienne image.
 */
export const templatePageUrl = (
  templateId: string,
  kind: "original" | "render",
  n: number,
  pass: number,
) => cvUrl(`/templates/${templateId}/pages/${kind}/${n}?pass=${pass}`);

/** Les adresses des pages `1..count` d'un même document. */
export const pageRange = (count: number, url: (n: number) => string): string[] =>
  Array.from({ length: Math.max(count, 0) }, (_, index) => url(index + 1));
