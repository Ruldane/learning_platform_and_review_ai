/** Taille maximale d'un fichier importé (20 Mo), la même que celle du serveur. */
export const MAX_UPLOAD_BYTES = 20 * 1024 * 1024;

/** Extensions acceptées à l'import d'un fichier (PDF, DOCX, Markdown, texte). */
export const UPLOAD_EXTENSIONS = [".pdf", ".docx", ".md", ".markdown", ".txt"] as const;

/** Part en pourcentage, à une décimale, avec la virgule française (`0.25` devient « 25,0 % »). */
export function formatShare(share: number): string {
  return `${(share * 100).toFixed(1).replace(".", ",")} %`;
}
