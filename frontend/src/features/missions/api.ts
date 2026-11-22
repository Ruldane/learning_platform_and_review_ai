import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { components } from "@/shared/api/schema";

export type Mission = components["schemas"]["MissionOut"];
export type Criterion = components["schemas"]["MissionCriterionOut"];
export type Progress = components["schemas"]["MissionProgress"];
export type Posting = components["schemas"]["PostingOut"];

export async function fetchMissions(signal?: AbortSignal) {
  return unwrap(await api.GET("/missions", { signal }));
}

export async function fetchReadyOffers(signal?: AbortSignal) {
  const offers = unwrap(await api.GET("/postings", { signal }));
  return offers.filter((offer) => offer.status === "ready");
}

export async function fetchOffer(postingId: string, signal?: AbortSignal) {
  return unwrap(
    await api.GET("/postings/{posting_id}", {
      params: { path: { posting_id: postingId } },
      signal,
    }),
  );
}

export async function startMission(postingId: string, requirements: number[]) {
  return unwrap(
    await api.POST("/missions", {
      body: { posting_id: postingId, requirement_indices: requirements },
    }),
  );
}

export async function saveCriterion(id: string, index: number, progress: Progress) {
  return unwrap(
    await api.PATCH("/missions/{mission_id}/criteria/{index}", {
      params: { path: { mission_id: id, index } },
      body: progress,
    }),
  );
}

export async function submitMission(id: string, revision: number, artifact: string) {
  return unwrap(
    await api.POST("/missions/{mission_id}/submission", {
      params: { path: { mission_id: id } },
      body: { revision, artifact },
    }),
  );
}
