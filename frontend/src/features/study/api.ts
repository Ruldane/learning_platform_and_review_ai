import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { StudyStart } from "./types";

const studyPath = (studyId: string) => ({ params: { path: { study_session_id: studyId } } });

/** `GET /study-sessions/summary` : série, minutes de la semaine, minuteur, session ouverte, bloc du jour. */
export async function fetchStudySummary(signal?: AbortSignal) {
  return unwrap(await api.GET("/study-sessions/summary", { signal }));
}

/** `GET /study-sessions/{id}` : l'état de la session (et son bilan une fois terminée). */
export async function fetchStudySession(studyId: string, signal?: AbortSignal) {
  return unwrap(
    await api.GET("/study-sessions/{study_session_id}", { ...studyPath(studyId), signal }),
  );
}

/**
 * `POST /study-sessions` : ouvre la session et lance le Tuteur (202) ; 200 si elle est déjà ouverte
 * sur la même leçon. 404 `no_block_today`, 409 `study_already_open` (`details.study_session_id`).
 */
export async function startStudy(body: StudyStart) {
  return unwrap(await api.POST("/study-sessions", { body }));
}

/**
 * `PATCH /study-sessions/{id}` « Terminer » : le temps travaillé (minutes entières) est gardé, puis
 * la question en attente est reprise. Toujours cette route, jamais la reprise générique de session
 * (elle enregistrerait 0 minute). 409 `study_not_waiting` pendant que le Tuteur écrit.
 */
export async function finishStudy(studyId: string, workedMinutes: number) {
  return unwrap(
    await api.PATCH("/study-sessions/{study_session_id}", {
      ...studyPath(studyId),
      body: { action: "finish", worked_minutes: workedMinutes },
    }),
  );
}

/** `GET /lessons/{id}` : seul le titre sert ici (la leçon choisie pour la session). */
export async function fetchLessonTitle(lessonId: string, signal?: AbortSignal) {
  const lesson = unwrap(
    await api.GET("/lessons/{lesson_id}", { params: { path: { lesson_id: lessonId } }, signal }),
  );
  return { title: lesson.title };
}
