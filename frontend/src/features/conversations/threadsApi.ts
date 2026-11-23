import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { components } from "@/shared/api/schema";

export type ConversationSpace = "brain" | "training";
export type ConversationSummary = components["schemas"]["ConversationSummary"];

export async function listThreads(scope: ConversationSpace, signal?: AbortSignal) {
  return unwrap(await api.GET("/conversations/{scope}", { params: { path: { scope } }, signal }));
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
