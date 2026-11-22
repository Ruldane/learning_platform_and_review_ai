import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { components } from "@/shared/api/schema";
import { RUN_HEADER, type RunSource } from "@/shared/lib/runSource";

export type ConversationMessage = components["schemas"]["ConversationMessageIn"];
export type Conversation = components["schemas"]["LessonConversationOut"];
export type ConversationTurn = components["schemas"]["ConversationTurnOut"];

export async function fetchConversation(lesson: string, signal?: AbortSignal) {
  return unwrap(
    await api.GET("/lessons/{lesson_id}/conversation", {
      params: { path: { lesson_id: lesson } },
      signal,
    }),
  );
}

export async function sendQuestion(lesson: string, body: ConversationMessage, source: RunSource) {
  return unwrap(
    await api.POST("/lessons/{lesson_id}/conversation/messages", {
      params: { path: { lesson_id: lesson } },
      headers: { [RUN_HEADER]: source },
      body,
    }),
  );
}
