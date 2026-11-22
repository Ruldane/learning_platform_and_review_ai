import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { components } from "@/shared/api/schema";

export type UpdateView = components["schemas"]["UpdateView"];

export async function getUpdates(lessonId: string, signal: AbortSignal) {
  return unwrap(
    await api.GET("/lessons/{lesson_id}/updates", {
      params: { path: { lesson_id: lessonId } },
      signal,
    }),
  );
}

export async function acceptUpdate(lessonId: string, updateId: string) {
  return unwrap(
    await api.POST("/lessons/{lesson_id}/updates/{update_id}/accept", {
      params: { path: { lesson_id: lessonId, update_id: updateId } },
    }),
  );
}
