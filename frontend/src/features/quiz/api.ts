import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import { runSourceHeaders, type RunSource } from "@/shared/lib/runSource";

const quizPath = (quizId: string) => ({ params: { path: { quiz_id: quizId } } });

/** `GET /programs`: from newest to oldest (the quiz list follows the first). */
export async function fetchPrograms(signal?: AbortSignal) {
  return unwrap(await api.GET("/programs", { signal }));
}

/** `GET /programs/{id}/quizzes`: one module per row, its quiz if it exists, the best score. */
export async function fetchQuizzes(programId: string, signal?: AbortSignal) {
  return unwrap(
    await api.GET("/programs/{program_id}/quizzes", {
      params: { path: { program_id: programId } },
      signal,
    }),
  );
}

/**
 * `POST /modules/{id}/quiz`: prepares the module's quiz (202); already ready: 200; in preparation:
 * the same session; failed: retried. Lesson not ready: 409 `lesson_not_ready`.
 */
export async function startQuiz(moduleId: string, source?: RunSource) {
  return unwrap(
    await api.POST("/modules/{module_id}/quiz", {
      params: { path: { module_id: moduleId } },
      headers: runSourceHeaders(source),
    }),
  );
}

/** `GET /quizzes/{id}`: the quiz, its questions (without correct answers) and its attempts. */
export async function fetchQuiz(quizId: string, signal?: AbortSignal) {
  return unwrap(await api.GET("/quizzes/{quiz_id}", { ...quizPath(quizId), signal }));
}

/** A sent answer: `choice` is the choice's displayed rank (MCQ), `text` for other types. */
export interface AnswerBody {
  question_id: string;
  choice: number | null;
  text: string;
}

/**
 * `POST /quizzes/{id}/attempts`: sends the answers and starts the grading (202). 409
 * `retry_too_soon` (`details.retry_on`), `attempt_in_progress`, `quiz_not_ready` ; 422.
 */
export async function createAttempt(quizId: string, answers: AnswerBody[], elapsedMs?: number) {
  return unwrap(
    await api.POST("/quizzes/{quiz_id}/attempts", {
      ...quizPath(quizId),
      body: { answers, elapsed_ms: elapsedMs },
    }),
  );
}

/** `GET /quizzes/{id}/attempts/{attempt}`: the grading state (`grading`, `graded`, `failed`). */
export async function fetchAttempt(quizId: string, attemptId: string, signal?: AbortSignal) {
  return unwrap(
    await api.GET("/quizzes/{quiz_id}/attempts/{attempt_id}", {
      params: { path: { quiz_id: quizId, attempt_id: attemptId } },
      signal,
    }),
  );
}

/** `GET /flashcards/due`: today's queue (30 cards, 15 minutes, minus those already reviewed). */
export async function fetchDueCards(signal?: AbortSignal) {
  return unwrap(await api.GET("/flashcards/due", { signal }));
}

/** `POST /flashcards/{id}/review`: « Su » or « Raté »; already reviewed: 409 `card_not_due`. */
export async function reviewCard(cardId: string, result: "ok" | "fail") {
  return unwrap(
    await api.POST("/flashcards/{card_id}/review", {
      params: { path: { card_id: cardId } },
      body: { result },
    }),
  );
}
