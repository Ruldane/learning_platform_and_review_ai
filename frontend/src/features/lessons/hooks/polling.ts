import type { LessonStatus } from "../types";

const GENERATING_MS = 5000;
const WAITING_MS = 15_000;
const PDF_MS = 5000;
/** Relectures au plus pour attendre le PDF d'une leçon prête (2 min) : son rendu peut échouer. */
export const MAX_PDF_POLLS = 24;
/**
 * Relectures au plus de la liste quand plus aucune leçon ne s'écrit (5 min) : une leçon des
 * semaines suivantes attend 7 jours avant le début de sa semaine, inutile de relire jusque-là.
 */
export const MAX_IDLE_POLLS = 20;

/**
 * Quand relire une leçon : toutes les 5 s pendant qu'elle s'écrit, toutes les 15 s tant qu'elle
 * attend son tour ou sa nouvelle tentative (elle peut y rester longtemps). Prête, toutes les 5 s
 * tant que son PDF n'est pas là, `MAX_PDF_POLLS` fois au plus (`pdfPolls` : relectures déjà faites
 * depuis qu'elle est prête).
 */
export function lessonRefetchInterval(
  lesson: { status: LessonStatus; pdf_available: boolean } | undefined,
  pdfPolls: number,
): number | false {
  if (lesson === undefined) return false;
  if (lesson.status === "ready") {
    return !lesson.pdf_available && pdfPolls < MAX_PDF_POLLS ? PDF_MS : false;
  }
  return lesson.status === "generating" ? GENERATING_MS : WAITING_MS;
}

/**
 * Quand relire les leçons d'un programme : toutes les 5 s tant qu'une leçon s'écrit ; toutes les
 * 15 s tant qu'une leçon attend (`pending`, ou `failed` avant sa nouvelle tentative), au plus
 * `MAX_IDLE_POLLS` fois depuis la dernière leçon vue en écriture (`idlePolls`).
 */
export function lessonsRefetchInterval(
  lessons: readonly { status: LessonStatus }[] | undefined,
  idlePolls: number,
): number | false {
  if (lessons === undefined) return false;
  if (lessons.some((lesson) => lesson.status === "generating")) return GENERATING_MS;
  if (lessons.every((lesson) => lesson.status === "ready")) return false;
  return idlePolls < MAX_IDLE_POLLS ? WAITING_MS : false;
}
