import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { components } from "@/shared/api/schema";
import { runSourceHeaders, type RunSource } from "@/shared/lib/runSource";

export type ReadingItem = components["schemas"]["ReadingItemOut"];
export type ReadingDetail = components["schemas"]["ReadingDetail"];
export type ReadingKind = ReadingItem["kind"];
export type ReadingSource = components["schemas"]["ReadingSourceOut"];
export type ReadingSourceInput = components["schemas"]["ReadingSourceIn"];
export type ReadFilter = "unread" | "read" | "all";

interface ListFilter {
  state: ReadFilter;
  kind: ReadingKind | "";
  offset: number;
}

const entryPath = (itemId: string) => ({ params: { path: { item_id: itemId } } });
const sourcePath = (sourceId: string) => ({ params: { path: { source_id: sourceId } } });

export async function listReading(filter: ListFilter, signal?: AbortSignal) {
  const { state, kind, offset } = filter;
  const query = {
    unread: state === "all" ? undefined : state === "unread",
    kind: kind || undefined,
    offset,
  };
  return unwrap(await api.GET("/reading-stack", { params: { query }, signal }));
}

export async function getReading(id: string, signal?: AbortSignal) {
  return unwrap(await api.GET("/reading-stack/{item_id}", { ...entryPath(id), signal }));
}

export async function markReading(id: string, read: boolean) {
  return unwrap(await api.PATCH("/reading-stack/{item_id}", { ...entryPath(id), body: { read } }));
}

export async function keepReading(id: string) {
  return unwrap(await api.POST("/reading-stack/{item_id}/memory", entryPath(id)));
}

export async function makeReadingCard(id: string, passage?: string) {
  return unwrap(
    await api.POST("/reading-stack/{item_id}/cards", {
      ...entryPath(id),
      body: passage ? { passage } : undefined,
    }),
  );
}

export async function planReading(id: string, programId: string, provider?: RunSource) {
  return unwrap(
    await api.POST("/reading-stack/{item_id}/plan", {
      ...entryPath(id),
      body: { program_id: programId },
      headers: runSourceHeaders(provider),
    }),
  );
}

export async function createReadingApplication(id: string, company: string) {
  return unwrap(
    await api.POST("/reading-stack/{item_id}/application", {
      ...entryPath(id),
      body: { company },
    }),
  );
}

export async function listReadingPrograms(signal?: AbortSignal) {
  return unwrap(await api.GET("/programs", { signal })).filter((row) => row.status === "validated");
}

export async function listReadingSources(signal?: AbortSignal) {
  return unwrap(await api.GET("/reading-stack/sources", { signal }));
}

export async function addReadingSource(body: ReadingSourceInput) {
  return unwrap(await api.POST("/reading-stack/sources", { body }));
}

export async function setSourceActive(id: string, active: boolean) {
  return unwrap(
    await api.PATCH("/reading-stack/sources/{source_id}", { ...sourcePath(id), body: { active } }),
  );
}

export async function removeReadingSource(id: string) {
  unwrap(await api.DELETE("/reading-stack/sources/{source_id}", sourcePath(id)));
}
