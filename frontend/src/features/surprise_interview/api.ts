import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { components } from "@/shared/api/schema";

export type SurprisePreferences = components["schemas"]["SurprisePreferences"];
export type SurpriseSettings = components["schemas"]["SurpriseSettingsOut"];

export async function readSurpriseSettings(signal?: AbortSignal) {
  return unwrap(await api.GET("/surprise-interviews/settings", { signal }));
}

export async function saveSurpriseSettings(body: SurprisePreferences) {
  return unwrap(await api.PUT("/surprise-interviews/settings", { body }));
}
