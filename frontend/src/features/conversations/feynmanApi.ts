import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { components } from "@/shared/api/schema";
import { runSourceHeaders, type RunSource } from "@/shared/lib/runSource";

export type Explanation = components["schemas"]["FeynmanRunOut"];
export type FeynmanReport = components["schemas"]["FeynmanReport"];
export type FeynmanEntry =
  | { kind: "lesson"; id: string }
  | { kind: "ide"; id: string; path?: string | undefined }
  | { kind: "saved"; id: string };
type Launch = Exclude<FeynmanEntry, { kind: "saved" }>;

export async function readExplanation(entry: FeynmanEntry, signal: AbortSignal) {
  if (entry.kind === "lesson") {
    return unwrap(
      await api.GET("/lessons/{lesson_id}/explain", {
        params: { path: { lesson_id: entry.id } },
        signal,
      }),
    );
  }
  if (entry.kind === "ide") {
    return unwrap(
      await api.GET("/ide/sessions/{session_id}/explain", {
        params: { path: { session_id: entry.id } },
        signal,
      }),
    );
  }
  return unwrap(
    await api.GET("/conversations/explain/{turn_id}", {
      params: { path: { turn_id: entry.id } },
      signal,
    }),
  );
}

export async function launchExplanation(entry: Launch, requestId: string, source: RunSource) {
  const headers = runSourceHeaders(source);
  if (entry.kind === "lesson") {
    return unwrap(
      await api.POST("/lessons/{lesson_id}/explain", {
        params: { path: { lesson_id: entry.id } },
        headers,
        body: { request_id: requestId, strong: false },
      }),
    );
  }
  return unwrap(
    await api.POST("/ide/sessions/{session_id}/explain", {
      params: { path: { session_id: entry.id } },
      headers,
      body: { request_id: requestId, path: entry.path ?? "", strong: false },
    }),
  );
}

export async function acceptExplanation(turnId: string) {
  return unwrap(
    await api.POST("/conversations/explain/{turn_id}/accept", {
      params: { path: { turn_id: turnId } },
    }),
  );
}
