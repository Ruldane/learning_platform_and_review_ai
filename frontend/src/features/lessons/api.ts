import { api, apiBaseUrl } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { LibraryFilterValue, ResourceStatus } from "./types";

/** `GET /programs` : du plus récent au plus ancien (la liste des leçons suit le premier). */
export async function fetchPrograms(signal?: AbortSignal) {
  return unwrap(await api.GET("/programs", { signal }));
}

/** `GET /programs/{id}/lessons` : toutes les leçons du programme, dans son ordre (D91). */
export async function fetchProgramLessons(programId: string, signal?: AbortSignal) {
  return unwrap(
    await api.GET("/programs/{program_id}/lessons", {
      params: { path: { program_id: programId } },
      signal,
    }),
  );
}

/** `GET /lessons/{id}` : la leçon (Markdown, statut, raison d'un échec) et ses ressources. */
export async function fetchLesson(lessonId: string, signal?: AbortSignal) {
  return unwrap(
    await api.GET("/lessons/{lesson_id}", { params: { path: { lesson_id: lessonId } }, signal }),
  );
}

/** `GET /resources` : la bibliothèque, filtrée par programme, type, langue et statut. */
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

/** `PATCH /resources/{id}` : « Lue » ou « À lire ». */
export async function patchResource(resourceId: string, status: ResourceStatus) {
  return unwrap(
    await api.PATCH("/resources/{resource_id}", {
      params: { path: { resource_id: resourceId } },
      body: { status },
    }),
  );
}

/** Adresse du PDF d'une leçon. */
export const lessonPdfUrl = (lessonId: string) => `${apiBaseUrl}/api/v1/lessons/${lessonId}/pdf`;

/** Adresse de la copie locale (PDF) d'une ressource. */
export const resourceFileUrl = (resourceId: string) =>
  `${apiBaseUrl}/api/v1/resources/${resourceId}/file`;
