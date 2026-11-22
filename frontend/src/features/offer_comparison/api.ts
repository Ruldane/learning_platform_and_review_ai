import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { components } from "@/shared/api/schema";

export type Pair = components["schemas"]["OfferComparisonPair"];
export type Rules = NonNullable<Pair["preferences"]>;
export type WeightKey = keyof NonNullable<Rules["weights"]>;
export type SourceOffer = components["schemas"]["OfferComparisonPosting"];

export const PREFERENCES = ["offer-comparison-preferences"] as const;
export const OPTIONS = ["offer-comparison-postings"] as const;
export const HISTORY = ["offer-comparison-history"] as const;
export const detailKey = (id: string) => [...HISTORY, id] as const;

export async function listOffers(signal: AbortSignal) {
  return unwrap(await api.GET("/offer-comparisons/postings", { signal }));
}

export async function loadRules(signal: AbortSignal) {
  return unwrap(await api.GET("/offer-comparisons/preferences", { signal }));
}

export async function storeRules(body: Rules) {
  return unwrap(await api.PUT("/offer-comparisons/preferences", { body }));
}

export async function previewComparison(body: Pair) {
  return unwrap(await api.POST("/offer-comparisons/preview", { body }));
}

export async function saveComparison(body: Pair) {
  return unwrap(await api.POST("/offer-comparisons", { body }));
}

export async function listComparisons(signal: AbortSignal) {
  return unwrap(await api.GET("/offer-comparisons", { signal }));
}

export async function readComparison(id: string, signal: AbortSignal) {
  return unwrap(await api.GET("/offer-comparisons/{scenario_id}", {
    params: { path: { scenario_id: id } },
    signal,
  }));
}
