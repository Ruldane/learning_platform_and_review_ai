import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { components } from "@/shared/api/schema";

export type Appeal = components["schemas"]["GradeAppealOut"];
export type AppealDecision = NonNullable<Appeal["decision"]>;
type AppealCreate = components["schemas"]["GradeAppealCreate"];

export const APPEALS = ["grade-appeals"] as const;
export const detailKey = (id: string) => [...APPEALS, id] as const;

export async function listProjects(signal: AbortSignal) {
  return unwrap(await api.GET("/grade-appeals/projects", { signal }));
}

export async function listCriteria(id: string, signal: AbortSignal) {
  return unwrap(await api.GET("/grade-appeals/projects/{project_id}/criteria", {
    params: { path: { project_id: id } },
    signal,
  }));
}

export async function listAppeals(signal: AbortSignal) {
  return unwrap(await api.GET("/grade-appeals", { signal }));
}

export async function getAppeal(id: string, signal: AbortSignal) {
  return unwrap(await api.GET("/grade-appeals/{appeal_id}", {
    params: { path: { appeal_id: id } },
    signal,
  }));
}

export async function createAppeal(body: AppealCreate) {
  return unwrap(await api.POST("/grade-appeals", { body }));
}

export async function reviewAppeal(id: string) {
  return unwrap(await api.POST("/grade-appeals/{appeal_id}/review", {
    params: { path: { appeal_id: id } },
  }));
}

export async function decideAppeal(id: string, decision: AppealDecision) {
  return unwrap(await api.POST("/grade-appeals/{appeal_id}/decision", {
    params: { path: { appeal_id: id } },
    body: { decision },
  }));
}
