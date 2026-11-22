import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { components } from "@/shared/api/schema";

export type BlindInput = components["schemas"]["BlindCreate"];
export type BlindRun = components["schemas"]["BlindOut"];

export async function listOptions(signal: AbortSignal) {
  return unwrap(await api.GET("/blind-assessments/options", { signal }));
}

export async function listRuns(signal: AbortSignal) {
  return unwrap(await api.GET("/blind-assessments", { signal }));
}

export async function createRun(body: BlindInput) {
  return unwrap(await api.POST("/blind-assessments", { body }));
}

export async function evaluateRun(id: string) {
  return unwrap(
    await api.POST("/blind-assessments/{assessment_id}/evaluate", {
      params: { path: { assessment_id: id } },
    }),
  );
}
