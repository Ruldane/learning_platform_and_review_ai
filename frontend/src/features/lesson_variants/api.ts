import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { components } from "@/shared/api/schema";

export type Program = components["schemas"]["ProgramSummaryOut"];
export type Lesson = components["schemas"]["LessonSummaryOut"];
export type LessonVariant = components["schemas"]["LessonVariantOut"];
export type LessonVariantSummary = components["schemas"]["LessonVariantSummary"];

export async function listPrograms(signal: AbortSignal) {
  return unwrap(await api.GET("/programs", { signal }));
}

export async function listPublishedLessons(programId: string, signal: AbortSignal) {
  const lessons = unwrap(await api.GET("/programs/{program_id}/lessons", {
    params: { path: { program_id: programId } }, signal,
  }));
  return lessons.filter((lesson) => lesson.status === "ready");
}

export async function listEditions(signal: AbortSignal) {
  return unwrap(await api.GET("/lesson-variants", { signal }));
}

export async function prepareEdition(lessonId: string) {
  return unwrap(await api.POST("/lesson-variants", { body: { lesson_id: lessonId } }));
}

export async function readEdition(editionId: string, signal: AbortSignal) {
  return unwrap(await api.GET("/lesson-variants/{edition_id}", {
    params: { path: { edition_id: editionId } }, signal,
  }));
}
