import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { CaptureRequest, JournalKind } from "./types";

/**
 * `POST /capture` (202) : exactement une source, un lien, un texte ou un document déjà importé.
 * 422 `invalid_input` / `invalid_url` / `url_forbidden`, 404 `document_not_found`, 409
 * `document_failed`. Jamais `POST /sessions` (409 `graph_has_route`).
 */
export async function startCapture(body: CaptureRequest) {
  return unwrap(await api.POST("/capture", { body }));
}

/**
 * `POST /documents` : importe un fichier (multipart, le navigateur pose la frontière) ; renvoie le
 * document, à passer ensuite à `POST /capture`.
 */
export async function uploadFile(file: File) {
  const form = new FormData();
  form.append("file", file);
  const created = unwrap(await api.POST("/documents", { body: {}, bodySerializer: () => form }));
  return created.document;
}

export interface JournalQuery {
  kind: JournalKind | null;
  /** `next_before` de la page précédente. */
  before: string | null;
  limit: number;
}

/** `GET /journal?kind=&before=&limit=` : du plus récent au plus ancien ; `next_before` pour la suite. */
export async function fetchJournal({ kind, before, limit }: JournalQuery, signal?: AbortSignal) {
  return unwrap(
    await api.GET("/journal", {
      params: { query: { kind: kind ?? undefined, before: before ?? undefined, limit } },
      signal,
    }),
  );
}
