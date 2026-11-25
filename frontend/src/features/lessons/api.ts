import { api, apiBaseUrl } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { LibraryFilterValue, ResourceStatus } from "./types";

/** `GET /programs`: newest first (the lesson list follows the first one). */
export async function fetchPrograms(signal?: AbortSignal) {
  return unwrap(await api.GET("/programs", { signal }));
}

/** `GET /programs/{id}/lessons`: all the program's lessons, in order (D91). */
export async function fetchProgramLessons(programId: string, signal?: AbortSignal) {
  return unwrap(
    await api.GET("/programs/{program_id}/lessons", {
      params: { path: { program_id: programId } },
      signal,
    }),
  );
}

/** `GET /lessons/{id}`: the lesson (Markdown, status, reason for a failure) and its resources. */
export async function fetchLesson(lessonId: string, signal?: AbortSignal) {
  return unwrap(
    await api.GET("/lessons/{lesson_id}", { params: { path: { lesson_id: lessonId } }, signal }),
  );
}

/** `GET /resources`: the library, filtered by program, type, language and status. */
export async function fetchResources(filters: LibraryFilterValue, signal?: AbortSignal) {
  return unwrap(
    await api.GET("/resources", {
      params: {
        query: {
          program_id: filters.programId,
          type: filters.type,
          lang: filters.lang,
          status: filters.status,
        },
      },
      signal,
    }),
  );
}

/** `PATCH /resources/{id}`: « Lue » or « À lire ». */
export async function patchResource(resourceId: string, status: ResourceStatus) {
  return unwrap(
    await api.PATCH("/resources/{resource_id}", {
      params: { path: { resource_id: resourceId } },
      body: { status },
    }),
  );
}

/** URL of a lesson's PDF. */
export const lessonPdfUrl = (lessonId: string) => `${apiBaseUrl}/api/v1/lessons/${lessonId}/pdf`;

/** URL of a resource's local copy (PDF). */
export const resourceFileUrl = (resourceId: string) =>
  `${apiBaseUrl}/api/v1/resources/${resourceId}/file`;
