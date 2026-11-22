import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { components } from "@/shared/api/schema";

export type OfferDetails = components["schemas"]["CompatibleOfferOut"];

function selection(runId: string, ref: string) {
  return { params: { path: { run_id: runId, ref } } };
}

export async function getOffer(runId: string, ref: string, signal: AbortSignal) {
  return unwrap(await api.GET("/compatible-offers/{run_id}/{ref}", { ...selection(runId, ref), signal }));
}

export async function planSkills(runId: string, ref: string, skills: string[]) {
  return unwrap(await api.POST("/compatible-offers/{run_id}/{ref}/plan", {
    ...selection(runId, ref), body: { skills },
  }));
}
