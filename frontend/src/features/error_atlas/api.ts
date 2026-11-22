import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { components } from "@/shared/api/schema";

export type Hypothesis = components["schemas"]["AtlasHypothesisOut"];
export type Evidence = components["schemas"]["AtlasEvidenceOut"];
export type ObservationInput = components["schemas"]["AtlasObservationIn"];

export const hypothesesKey = ["error-atlas", "hypotheses"] as const;
export const evidenceKey = ["error-atlas", "evidence"] as const;

export async function getHypotheses(signal?: AbortSignal) {
  return unwrap(await api.GET("/error-atlas", { signal }));
}

export async function getEvidence(signal?: AbortSignal) {
  return unwrap(await api.GET("/error-atlas/evidence", { signal }));
}

export async function recordObservation(body: ObservationInput) {
  return unwrap(await api.POST("/error-atlas/observations", { body }));
}

export async function chooseExercise(hypothesisId: string) {
  return unwrap(
    await api.POST("/error-atlas/hypotheses/{hypothesis_id}/exercise", {
      params: { path: { hypothesis_id: hypothesisId } },
    }),
  );
}
