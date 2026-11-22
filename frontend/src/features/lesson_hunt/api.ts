import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { components } from "@/shared/api/schema";

export type Hunt = components["schemas"]["HuntOut"];

function path(huntId: string) {
  return { params: { path: { hunt_id: huntId } } };
}

export async function startHunt(lessonId: string) {
  return unwrap(await api.POST("/lesson-hunts", { body: { lesson_id: lessonId } }));
}

export async function readHunt(huntId: string, signal: AbortSignal) {
  return unwrap(await api.GET("/lesson-hunts/{hunt_id}", { ...path(huntId), signal }));
}

export async function answerHunt(huntId: string, responses: string[]) {
  return unwrap(
    await api.POST("/lesson-hunts/{hunt_id}/answers", {
      ...path(huntId),
      body: { responses },
    }),
  );
}
