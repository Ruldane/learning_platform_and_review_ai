import type { CaptureSource } from "./viewTypes";

/** Taille maximale d'une note (contrat : `text` de 20 000 caractères) et d'un lien (2 048). */
export const MAX_TEXT = 20_000;
export const MAX_URL = 2_048;

/** Taille maximale d'un fichier importé (20 Mo), la même que celle du serveur. */
export const MAX_FILE_BYTES = 20 * 1024 * 1024;

/** Extensions acceptées à l'import d'un fichier (PDF, DOCX, Markdown, texte). */
export const FILE_EXTENSIONS = [".pdf", ".docx", ".md", ".markdown", ".txt"] as const;

const LINK = /^https?:\/\/\S+$/i;

/**
 * La source d'un champ unique : un lien si tout le champ est une adresse `http://` ou `https://`
 * (sans espace), sinon une note. `null` : champ vide.
 */
export function detectSource(value: string): CaptureSource | null {
  const trimmed = value.trim();
  if (trimmed === "") return null;
  return LINK.test(trimmed) ? { kind: "url", url: trimmed } : { kind: "text", text: trimmed };
}

/** Raison pour laquelle un fichier est refusé avant tout envoi, ou `null`. */
export function fileProblem(file: File): "badType" | "tooBig" | null {
  const name = file.name.toLowerCase();
  if (!FILE_EXTENSIONS.some((extension) => name.endsWith(extension))) return "badType";
  return file.size > MAX_FILE_BYTES ? "tooBig" : null;
}
