import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import { RUN_HEADER } from "@/shared/lib/runSource";
import type { ConversationMessage } from "./api";

export async function createOffersThread() {
  return unwrap(await api.POST("/conversations/offers"));
}

export async function readOffersThread(id: string, signal?: AbortSignal) {
  return unwrap(
    await api.GET("/conversations/offers/{conversation_id}", {
      params: { path: { conversation_id: id } },
      signal,
    }),
  );
}

export async function sendOffersQuestion(id: string, message: ConversationMessage) {
  const { request_id, question, strong } = message;
  return unwrap(
    await api.POST("/conversations/offers/{conversation_id}/messages", {
      params: { path: { conversation_id: id } },
      headers: { [RUN_HEADER]: "settings" },
      body: { request_id, question, strong },
    }),
  );
}
