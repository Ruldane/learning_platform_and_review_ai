import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { components } from "@/shared/api/schema";

export type LabPreferences = components["schemas"]["LabPreferences"];
export type LabPreferencesPatch = components["schemas"]["LabPreferencesPatch"];

export async function fetchPreferences(signal?: AbortSignal) {
  return unwrap(await api.GET("/lab/preferences", { signal }));
}

export async function savePreferences(body: LabPreferencesPatch) {
  return unwrap(await api.PATCH("/lab/preferences", { body }));
}
