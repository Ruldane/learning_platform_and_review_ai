import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { components } from "@/shared/api/schema";

export type Recruitment = components["schemas"]["RecruitmentOut"];
export type Step = Recruitment["steps"][number];
type RecruitmentCreate = components["schemas"]["RecruitmentCreate"];

export const RECRUITMENTS = ["recruitment-process"] as const;
export const detailKey = (id: string) => [...RECRUITMENTS, id] as const;

export async function options(signal: AbortSignal) {
  return unwrap(await api.GET("/recruitment-processes/options", { signal }));
}

export async function listCases(signal: AbortSignal) {
  return unwrap(await api.GET("/recruitment-processes", { signal }));
}

export async function readCase(id: string, signal: AbortSignal) {
  return unwrap(await api.GET("/recruitment-processes/{process_id}", {
    params: { path: { process_id: id } },
    signal,
  }));
}

export async function createCase(body: RecruitmentCreate) {
  return unwrap(await api.POST("/recruitment-processes", { body }));
}

export async function answerStep(id: string, kind: Step["kind"], answer: string) {
  return unwrap(await api.POST("/recruitment-processes/{process_id}/steps/{kind}/answers", {
    params: { path: { process_id: id, kind } },
    body: { answer },
  }));
}
