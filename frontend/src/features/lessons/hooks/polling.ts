import type { LessonSummaryOut } from "../types";

const GENERATING_MS = 5000;
const WAITING_MS = 15_000;
const PDF_MS = 5000;
/** Max re-reads while waiting for the PDF of a ready lesson (2 min): its render may fail. */
export const MAX_PDF_POLLS = 24;
/**
 * Max list re-reads when no lesson is being written anymore (5 min): a lesson of the
 * following weeks waits 7 days before its week starts, no need to re-read until then.
 */
export const MAX_IDLE_POLLS = 20;

type LessonProgress = Pick<LessonSummaryOut, "status" | "verification_session_id">;

export function lessonIsInProgress(lesson: LessonProgress): boolean {
  return lesson.status === "generating" || Boolean(lesson.verification_session_id);
}

/**
 * When to re-read a lesson: every 5 s while it is being written, every 15 s while it
 * waits for its turn or its new attempt (it may stay there a long time). Ready, every 5 s
 * while its PDF is not there yet, at most `MAX_PDF_POLLS` times (`pdfPolls`: re-reads already done
 * since it became ready).
 */
export function lessonRefetchInterval(
  lesson: (LessonProgress & Pick<LessonSummaryOut, "pdf_available">) | undefined,
  pdfPolls: number,
): number | false {
  if (lesson === undefined) return false;
  if (lessonIsInProgress(lesson)) return GENERATING_MS;
  if (lesson.status === "ready") {
    return !lesson.pdf_available && pdfPolls < MAX_PDF_POLLS ? PDF_MS : false;
  }
  return WAITING_MS;
}

/**
 * When to re-read a program's lessons: every 5 s while a lesson is being written; every
 * 15 s while a lesson waits (`pending`, or `failed` before its new attempt), at most
 * `MAX_IDLE_POLLS` times since the last lesson seen being written (`idlePolls`).
 */
export function lessonsRefetchInterval(
  lessons: readonly LessonProgress[] | undefined,
  idlePolls: number,
): number | false {
  if (lessons === undefined) return false;
  if (lessons.some(lessonIsInProgress)) return GENERATING_MS;
  if (lessons.every((lesson) => lesson.status === "ready")) return false;
  return idlePolls < MAX_IDLE_POLLS ? WAITING_MS : false;
}
