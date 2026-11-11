import { api, apiBaseUrl } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { ItemPatch, ItemsQuery, MemoryKindView, NewItem, UploadInput } from "./types";

/** Lien direct vers l'export JSON : le navigateur le télécharge, aucun appel de l'application. */
export const exportUrl = `${apiBaseUrl}/api/v1/memory/export`;

/** Jour saisi (`2026-11-11`) → instant UTC du début ou de la fin de ce jour, à l'heure locale. */
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

/** `GET /memory/items/{id}` : détail, fragments, voisins et journal. */
export async function fetchItem(id: string, signal?: AbortSignal) {
  return unwrap(
    await api.GET("/memory/items/{item_id}", { params: { path: { item_id: id } }, signal }),
  );
}

/** `POST /memory/items` : élément créé à la main. */
export async function createItem(value: NewItem) {
  return unwrap(await api.POST("/memory/items", { body: value }));
}

/** `PATCH /memory/items/{id}` : modifier (`ItemPatch`, champs changés seuls) ou confirmer une décision (`status`). */
export async function patchItem(id: string, value: ItemPatch | { status: "active" }) {
  return unwrap(
    await api.PATCH("/memory/items/{item_id}", { params: { path: { item_id: id } }, body: value }),
  );
}

/** `DELETE /memory/items/{id}` : supprimer, ou refuser une décision en attente. */
export async function deleteItem(id: string) {
  unwrap(await api.DELETE("/memory/items/{item_id}", { params: { path: { item_id: id } } }));
}

/** `POST /memory/items/{id}/merge` : fond `otherIds` dans l'élément `id`. */
export async function mergeItems(id: string, otherIds: string[]) {
  return unwrap(
    await api.POST("/memory/items/{item_id}/merge", {
      params: { path: { item_id: id } },
      body: { other_ids: otherIds },
    }),
  );
}

/** Nombre de résultats par défaut de `memory_search` (SPEC 4.4). */
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

/** `POST /memory/reindex` (202) : met la réindexation en file et renvoie son état. */
export async function postReindex() {
  return unwrap(await api.POST("/memory/reindex"));
}

/** `GET /documents`. */
export async function fetchDocuments(signal?: AbortSignal) {
  return unwrap(await api.GET("/documents", { signal }));
}

/**
 * Import d'un document. Fichier et lien : `POST /documents` en multipart (`FormData`, le
 * navigateur pose le `Content-Type` et sa frontière). Texte collé : `POST /documents/text` en
 * JSON (500 000 caractères au plus, `paste_too_long` sinon).
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

/** `POST /documents/{id}/learned` (202) : lance l'Archiviste, renvoie l'identifiant de session. */
export async function markLearned(documentId: string) {
  return unwrap(
    await api.POST("/documents/{document_id}/learned", {
      params: { path: { document_id: documentId } },
    }),
  );
}

/**
 * `GET /sessions?graph=learned_document&status=running` : les parcours de l'Archiviste encore en
 * cours, repris après un rechargement. Seules comptent les sessions dont l'objet suivi est un
 * document (`subject_type` « document », `subject_id` non nul).
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
