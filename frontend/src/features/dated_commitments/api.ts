import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { components } from "@/shared/api/schema";

export type Commitment = components["schemas"]["CommitmentOut"];
export type Draft = Omit<components["schemas"]["CommitmentCreate"], "request_id">;
export type Review = components["schemas"]["CommitmentReview"];

export const listKey = ["dated-commitments"] as const;
export const detailKey = (id: string) => [...listKey, id] as const;

export async function getCommitments(signal?: AbortSignal) {
  return unwrap(await api.GET("/dated-commitments", { signal }));
}

export async function getCommitment(id: string, signal?: AbortSignal) {
  return unwrap(
    await api.GET("/dated-commitments/{commitment_id}", {
      params: { path: { commitment_id: id } },
      signal,
    }),
  );
}

export async function createCommitment(body: Draft, requestId: string) {
  return unwrap(await api.POST("/dated-commitments", { body: { ...body, request_id: requestId } }));
}

export async function reviewCommitment(id: string, body: Review) {
  return unwrap(
    await api.POST("/dated-commitments/{commitment_id}/review", {
      params: { path: { commitment_id: id } },
      body,
    }),
  );
}
