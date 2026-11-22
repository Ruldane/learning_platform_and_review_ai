import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { components } from "@/shared/api/schema";

export type ReturnState = components["schemas"]["StudyReturnOut"];
export type ReturnPlan = components["schemas"]["StudyReturnPlan"];
export type LastBlock = components["schemas"]["StudyReturnLastBlock"];

export const studyReturnKey = ["study-return"] as const;

export async function readReturn(signal?: AbortSignal) {
  return unwrap(await api.GET("/study-return", { signal }));
}

export async function prepareReturn() {
  return unwrap(await api.POST("/study-return/prepare"));
}

export async function setReminder(day: string | null) {
  return unwrap(await api.PUT("/study-return/reminder", { body: { day } }));
}

export async function startReturn() {
  return unwrap(await api.POST("/study-return/start"));
}
