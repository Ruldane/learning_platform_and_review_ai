import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { components, paths } from "@/shared/api/schema";

type ConversationListParams = paths["/api/v1/conversations/{scope}"]["get"]["parameters"];
export type ConversationSpace = ConversationListParams["path"]["scope"];
export type ConversationSummary = components["schemas"]["ConversationSummary"];

export async function listThreads(scope: ConversationSpace, q?: string, signal?: AbortSignal) {
  return unwrap(
    await api.GET("/conversations/{scope}", {
      params: { path: { scope }, query: q ? { q } : undefined },
      signal,
    }),
  );
}

export async function createBrainThread() {
  return unwrap(await api.POST("/brain/conversations"));
}

export async function renameThread(scope: ConversationSpace, id: string, title: string) {
  return unwrap(
    await api.PATCH("/conversations/{scope}/{conversation_id}", {
      params: { path: { scope, conversation_id: id } },
      body: { title },
    }),
  );
}

export async function deleteThread(scope: ConversationSpace, id: string) {
  unwrap(
    await api.DELETE("/conversations/{scope}/{conversation_id}", {
      params: { path: { scope, conversation_id: id } },
    }),
  );
}

export async function clearThread(scope: ConversationSpace, id: string) {
  unwrap(
    await api.DELETE("/conversations/{scope}/{conversation_id}/messages", {
      params: { path: { scope, conversation_id: id } },
    }),
  );
}

export async function deleteThreads(scope: ConversationSpace) {
  unwrap(await api.DELETE("/conversations/{scope}", { params: { path: { scope } } }));
}
