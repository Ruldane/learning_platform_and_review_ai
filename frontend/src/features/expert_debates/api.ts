import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { components } from "@/shared/api/schema";

const params = (id: string) => ({ path: { debate_id: id } });
export type Debate = components["schemas"]["ExpertDebateOut"];
export type DebateSummary = components["schemas"]["ExpertDebateSummary"];

export async function listDebates(signal?: AbortSignal) {
  return unwrap(await api.GET("/expert-debates", { signal }));
}

export async function debateDetails(id: string, signal?: AbortSignal) {
  return unwrap(await api.GET("/expert-debates/{debate_id}", { params: params(id), signal }));
}

export async function startDebate(id: string, question: string) {
  return unwrap(
    await api.POST("/expert-debates", { body: { request_id: id, question, strong: false } }),
  );
}

export async function storeJudgment(id: string, text: string) {
  return unwrap(
    await api.PUT("/expert-debates/{debate_id}/judgment", {
      params: params(id),
      body: { text },
    }),
  );
}
