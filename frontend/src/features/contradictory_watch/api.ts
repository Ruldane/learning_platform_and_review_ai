import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { components } from "@/shared/api/schema";
import type { ExperimentDraft, FrozenWatchView } from "./components/viewTypes";

type WatchResult = Omit<components["schemas"]["WatchExperimentOut"], "sources"> & {
  sources: readonly components["schemas"]["WatchSource"][];
};
export type Observation = components["schemas"]["WatchObservation"];

export function toFrozenWatch(item: WatchResult): FrozenWatchView {
  return {
    sources: item.sources.map(({ url, version, claim }) => ({ link: url, version, claim })),
    protocol: item.protocol,
    criterion: item.criterion,
    result: item.observation
      ? { text: item.observation.measurement, verdict: item.observation.outcome }
      : null,
  };
}

export const basePath = "/study/contradictory-watch";
export const watchKey = ["contradictory_watch"] as const;
export const experimentKey = (id: string) => [...watchKey, id] as const;

export async function listExperiments(signal: AbortSignal) {
  return unwrap(await api.GET("/contradictory-watch", { signal }));
}

export async function createExperiment({ first, second, ...fields }: ExperimentDraft) {
  return unwrap(await api.POST("/contradictory-watch", {
    body: { ...fields, sources: [first, second] },
  }));
}

export async function readExperiment(id: string, signal: AbortSignal) {
  return unwrap(
    await api.GET("/contradictory-watch/{experiment_id}", {
      signal,
      params: { path: { experiment_id: id } },
    }),
  );
}

export async function recordObservation(id: string, body: Observation) {
  return unwrap(
    await api.POST("/contradictory-watch/{experiment_id}/observations", {
      body,
      params: { path: { experiment_id: id } },
    }),
  );
}
