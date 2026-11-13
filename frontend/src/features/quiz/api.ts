import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";

const quizPath = (quizId: string) => ({ params: { path: { quiz_id: quizId } } });

/** `GET /programs` : du plus récent au plus ancien (la liste des quiz suit le premier). */
export async function fetchPrograms(signal?: AbortSignal) {
  return unwrap(await api.GET("/programs", { signal }));
}

/** `GET /programs/{id}/quizzes` : un module par ligne, son quiz s'il existe, le meilleur score. */
export async function fetchQuizzes(programId: string, signal?: AbortSignal) {
  return unwrap(
    await api.GET("/programs/{program_id}/quizzes", {
      params: { path: { program_id: programId } },
      signal,
    }),
  );
}

/**
 * `POST /modules/{id}/quiz` : prépare le quiz du module (202) ; déjà prêt : 200 ; en préparation :
 * la même session ; en échec : relancé. Leçon pas prête : 409 `lesson_not_ready`.
 */
export async function startQuiz(moduleId: string) {
  return unwrap(
    await api.POST("/modules/{module_id}/quiz", { params: { path: { module_id: moduleId } } }),
  );
}

/** `GET /quizzes/{id}` : le quiz, ses questions (sans bonnes réponses) et ses tentatives. */
export async function fetchQuiz(quizId: string, signal?: AbortSignal) {
  return unwrap(await api.GET("/quizzes/{quiz_id}", { ...quizPath(quizId), signal }));
}

/** Une réponse envoyée : `choice` est le rang affiché du choix (QCM), `text` les autres types. */
export interface AnswerBody {
  question_id: string;
  choice: number | null;
  text: string;
}

/**
 * `POST /quizzes/{id}/attempts` : envoie les réponses et lance la notation (202). 409
 * `retry_too_soon` (`details.retry_on`), `attempt_in_progress`, `quiz_not_ready` ; 422.
 */
export async function createAttempt(quizId: string, answers: AnswerBody[]) {
  return unwrap(
    await api.POST("/quizzes/{quiz_id}/attempts", { ...quizPath(quizId), body: { answers } }),
  );
}

/** `GET /quizzes/{id}/attempts/{attempt}` : l'état de la note (`grading`, `graded`, `failed`). */
export async function fetchAttempt(quizId: string, attemptId: string, signal?: AbortSignal) {
  return unwrap(
    await api.GET("/quizzes/{quiz_id}/attempts/{attempt_id}", {
      params: { path: { quiz_id: quizId, attempt_id: attemptId } },
      signal,
    }),
  );
}

/** `GET /flashcards/due` : la file du jour (30 fiches, 15 minutes, moins celles déjà revues). */
export async function fetchDueCards(signal?: AbortSignal) {
  return unwrap(await api.GET("/flashcards/due", { signal }));
}

/** `POST /flashcards/{id}/review` : « Su » ou « Raté » ; déjà revue : 409 `card_not_due`. */
export async function reviewCard(cardId: string, result: "ok" | "fail") {
  return unwrap(
    await api.POST("/flashcards/{card_id}/review", {
      params: { path: { card_id: cardId } },
      body: { result },
    }),
  );
}
