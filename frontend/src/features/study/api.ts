import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import { runSourceHeaders, type RunSource } from "@/shared/lib/runSource";
import type { StudyStart } from "./types";

const studyPath = (studyId: string) => ({ params: { path: { study_session_id: studyId } } });

/** `GET /study-sessions/summary`: streak, minutes of the week, timer, open session, day's block. */
export async function fetchStudySummary(signal?: AbortSignal) {
  return unwrap(await api.GET("/study-sessions/summary", { signal }));
}

/** `GET /study-sessions/{id}`: the session's state (and its summary once finished). */
export async function fetchStudySession(studyId: string, signal?: AbortSignal) {
  return unwrap(
    await api.GET("/study-sessions/{study_session_id}", { ...studyPath(studyId), signal }),
  );
}

/**
 * `POST /study-sessions`: opens the session and starts the Tutor (202); 200 if it is already open
 * on the same lesson. 404 `no_block_today`, 409 `study_already_open` (`details.study_session_id`).
 */
export async function startStudy(body: StudyStart, source?: RunSource) {
  return unwrap(await api.POST("/study-sessions", { body, headers: runSourceHeaders(source) }));
}

/**
 * `PATCH /study-sessions/{id}` « Terminer »: the worked time (whole minutes) is kept, then
 * the pending question is resumed. Always this route, never the generic session resume
 * (it would save 0 minutes). 409 `study_not_waiting` while the Tutor is writing.
 */
export async function finishStudy(studyId: string, workedMinutes: number) {
  return unwrap(
    await api.PATCH("/study-sessions/{study_session_id}", {
      ...studyPath(studyId),
      body: { action: "finish", worked_minutes: workedMinutes },
    }),
  );
}

/** `GET /lessons/{id}`: only the title is used here (the lesson chosen for the session). */
export async function fetchLessonTitle(lessonId: string, signal?: AbortSignal) {
  const lesson = unwrap(
    await api.GET("/lessons/{lesson_id}", { params: { path: { lesson_id: lessonId } }, signal }),
  );
  return { title: lesson.title };
}
