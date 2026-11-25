import { api, apiBaseUrl } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import { runSourceHeaders, type RunSource } from "@/shared/lib/runSource";
import type { ItemPatch, ItemsQuery, MemoryKindView, NewItem, UploadInput } from "./types";

/** Direct link to the JSON export: the browser downloads it, no app call. */
export const exportUrl = `${apiBaseUrl}/api/v1/memory/export`;

/** Entered day (`2026-11-11`) → UTC instant of the start or end of that day, in local time. */
function dayBound(day: string, end: boolean): string | undefined {
  if (day === "") return undefined;
  const date = new Date(`${day}T${end ? "23:59:59.999" : "00:00:00"}`);
  return Number.isNaN(date.getTime()) ? undefined : date.toISOString();
}

function itemParams({ filters, status, offset, limit }: ItemsQuery) {
  const { kind, tag, author, since, until } = filters;
  return {
    kind: kind === "" ? undefined : kind,
    tag: tag.trim() === "" ? undefined : tag.trim(),
    author: author === "" ? undefined : author,
    since: dayBound(since, false),
    until: dayBound(until, true),
    status,
    limit,
    offset,
  };
}

/** `GET /memory/items`. */
export async function fetchItems(query: ItemsQuery, signal?: AbortSignal) {
  return unwrap(await api.GET("/memory/items", { params: { query: itemParams(query) }, signal }));
}

/** `GET /memory/items/{id}`: detail, fragments, neighbours and log. */
export async function fetchItem(id: string, signal?: AbortSignal) {
  return unwrap(
    await api.GET("/memory/items/{item_id}", { params: { path: { item_id: id } }, signal }),
  );
}

/** `POST /memory/items`: item created by hand. */
export async function createItem(value: NewItem) {
  return unwrap(await api.POST("/memory/items", { body: value }));
}

/** `PATCH /memory/items/{id}`: edit (`ItemPatch`, changed fields) or confirm a decision. */
export async function patchItem(id: string, value: ItemPatch | { status: "active" }) {
  return unwrap(
    await api.PATCH("/memory/items/{item_id}", { params: { path: { item_id: id } }, body: value }),
  );
}

/** `DELETE /memory/items/{id}`: delete, or refuse a pending decision. */
export async function deleteItem(id: string) {
  unwrap(await api.DELETE("/memory/items/{item_id}", { params: { path: { item_id: id } } }));
}

/** `POST /memory/items/{id}/merge`: merges `otherIds` into item `id`. */
export async function mergeItems(id: string, otherIds: string[]) {
  return unwrap(
    await api.POST("/memory/items/{item_id}/merge", {
      params: { path: { item_id: id } },
      body: { other_ids: otherIds },
    }),
  );
}

/** Default result count of `memory_search` (SPEC 4.4). */
export const DEFAULT_K = 8;

/** `POST /memory/search`. */
export async function searchMemory(query: string, kinds: MemoryKindView[], k = DEFAULT_K) {
  return unwrap(
    await api.POST("/memory/search", {
      body: { query, kinds: kinds.length > 0 ? kinds : null, k },
    }),
  );
}

/** `GET /memory/map`. */
export async function fetchMap(signal?: AbortSignal) {
  return unwrap(await api.GET("/memory/map", { signal }));
}

/** `GET /memory/stats`. */
export async function fetchStats(signal?: AbortSignal) {
  return unwrap(await api.GET("/memory/stats", { signal }));
}

/** `POST /memory/reindex` (202): queues the reindex and returns its state. */
export async function postReindex() {
  return unwrap(await api.POST("/memory/reindex"));
}

/** `GET /documents`. */
export async function fetchDocuments(signal?: AbortSignal) {
  return unwrap(await api.GET("/documents", { signal }));
}

/**
 * Document import. File and link: `POST /documents` as multipart (`FormData`, the
 * browser sets the `Content-Type` and its boundary). Pasted text: `POST /documents/text` as
 * JSON (500,000 characters at most, `paste_too_long` otherwise).
 */
export async function uploadDocument(input: UploadInput) {
  if (input.kind === "text") {
    const title = input.title.trim();
    return unwrap(
      await api.POST("/documents/text", {
        body: { text: input.text, title: title === "" ? null : title },
      }),
    );
  }
  const form = new FormData();
  if (input.kind === "file") form.append("file", input.file);
  else form.append("url", input.url);
  return unwrap(await api.POST("/documents", { body: {}, bodySerializer: () => form }));
}

/** `POST /documents/{id}/learned` (202): starts the Archivist and returns the session id. */
export async function markLearned(documentId: string, source?: RunSource) {
  return unwrap(
    await api.POST("/documents/{document_id}/learned", {
      params: { path: { document_id: documentId } },
      headers: runSourceHeaders(source),
    }),
  );
}

/**
 * `GET /sessions?graph=learned_document&status=running`: the Archivist's runs still
 * in progress, resumed after a reload. Only sessions whose tracked object is a
 * document (`subject_type` « document », `subject_id` non-null).
 */
export async function fetchRunningLearnings(
  signal?: AbortSignal,
): Promise<{ documentId: string; sessionId: string }[]> {
  const sessions = unwrap(
    await api.GET("/sessions", {
      params: { query: { graph: "learned_document", status: "running" } },
      signal,
    }),
  );
  return sessions.flatMap((session) =>
    session.subject_type === "document" && session.subject_id
      ? [{ documentId: session.subject_id, sessionId: session.id }]
      : [],
  );
}
