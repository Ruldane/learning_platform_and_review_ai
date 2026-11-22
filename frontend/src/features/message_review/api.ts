import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { components } from "@/shared/api/schema";

export type ReviewPreferences = components["schemas"]["TelegramReviewPreferences"];

export async function readReviewSettings(signal?: AbortSignal) {
  return unwrap(await api.GET("/message-reviews/settings", { signal }));
}

export async function saveReviewSettings(body: ReviewPreferences) {
  return unwrap(await api.PUT("/message-reviews/settings", { body }));
}
