import type { CaptureSource } from "./viewTypes";

/** Maximum size of a note (contract: `text` of 20,000 characters) and of a link (2,048). */
export const MAX_TEXT = 20_000;
export const MAX_URL = 2_048;

/** Maximum size of an imported file (20 MB), the same as the server's. */
export const MAX_FILE_BYTES = 20 * 1024 * 1024;

/** Extensions accepted when importing a file (PDF, DOCX, Markdown, text). */
export const FILE_EXTENSIONS = [".pdf", ".docx", ".md", ".markdown", ".txt"] as const;

const LINK = /^https?:\/\/\S+$/i;

/**
 * The source of a single field: a link if the whole field is an `http://` or `https://` address
 * (no spaces), otherwise a note. `null`: empty field.
 */
export function detectSource(value: string): CaptureSource | null {
  const trimmed = value.trim();
  if (trimmed === "") return null;
  return LINK.test(trimmed) ? { kind: "url", url: trimmed } : { kind: "text", text: trimmed };
}

/** Why a file is refused before any upload, or `null`. */
export function fileProblem(file: File): "badType" | "tooBig" | null {
  const name = file.name.toLowerCase();
  if (!FILE_EXTENSIONS.some((extension) => name.endsWith(extension))) return "badType";
  return file.size > MAX_FILE_BYTES ? "tooBig" : null;
}
