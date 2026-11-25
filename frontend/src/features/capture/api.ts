import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import { runSourceHeaders, type RunSource } from "@/shared/lib/runSource";
import type { CaptureRequest, JournalKind } from "./types";

/**
 * `POST /capture` (202): exactly one source, a link, a text or an already imported document.
 * 422 `invalid_input` / `invalid_url` / `url_forbidden`, 404 `document_not_found`, 409
 * `document_failed`. Jamais `POST /sessions` (409 `graph_has_route`).
 */
export async function startCapture(body: CaptureRequest, source?: RunSource) {
  return unwrap(await api.POST("/capture", { body, headers: runSourceHeaders(source) }));
}

/**
 * `POST /documents`: imports a file (multipart, the browser sets the boundary); returns the
 * document, to pass next to `POST /capture`.
 */
export async function uploadFile(file: File) {
  const form = new FormData();
  form.append("file", file);
  const created = unwrap(await api.POST("/documents", { body: {}, bodySerializer: () => form }));
  return created.document;
}

export interface JournalQuery {
  kind: JournalKind | null;
  /** `next_before` of the previous page. */
  before: string | null;
  limit: number;
}

/** `GET /journal?kind=&before=&limit=`: newest first; `next_before` for the next page. */
export async function fetchJournal({ kind, before, limit }: JournalQuery, signal?: AbortSignal) {
  return unwrap(
    await api.GET("/journal", {
      params: { query: { kind: kind ?? undefined, before: before ?? undefined, limit } },
      signal,
    }),
  );
}
