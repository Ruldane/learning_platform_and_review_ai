import { http, HttpResponse } from "msw";
import { API } from "./councilApi";

/** Les deux questions d'un quiz, dans l'ordre du premier essai. */
export const firstOrder = [
  {
    id: "q1",
    rank: 1,
    type: "qcm",
    prompt: "Quel verbe lit une ressource ?",
    code: null,
    choices: ["GET", "POST"],
  },
  { id: "q2", rank: 2, type: "short", prompt: "Que fait PUT ?", code: null, choices: [] },
];

/** Les mêmes questions au nouvel essai : l'ordre est mélangé (F27). */
export const secondOrder = [
  { ...firstOrder[1]!, rank: 1 },
  { ...firstOrder[0]!, rank: 2, choices: ["POST", "GET"] },
];

/** Un quiz tel que le back le rend (`QuizOut`). */
export const quizOut = (over: Record<string, unknown> = {}) => ({
  id: "z1",
  module_id: "m1",
  title: "Quiz : les API REST",
  status: "ready",
  failure_reason: null,
  session_id: null,
  questions: firstOrder,
  attempts: [],
  ...over,
});

/** Une tentative notée (`AttemptOut`) : un QCM juste, une réponse courte fausse. */
export const attemptOut = (over: Record<string, unknown> = {}) => ({
  id: "a1",
  status: "graded",
  score: 50,
  passed: false,
  results: [
    { question_id: "q1", points: 1, correct_answer: "GET", explanation: "GET lit.", feedback: "" },
    {
      question_id: "q2",
      points: 0,
      correct_answer: "Remplace la ressource.",
      explanation: "PUT remplace.",
      feedback: "Pas tout à fait.",
    },
  ],
  followup: { revision_tasks: ["Réviser : les API REST"], retry_on: "2026-11-19", unplaced: 0 },
  ...over,
});

interface QuizApi {
  /** Les lectures successives de `GET /quizzes/z1` (la dernière est répétée). */
  quizzes?: Record<string, unknown>[];
  /** Les lectures successives de `GET /quizzes/z1/attempts/a1` (la dernière est répétée). */
  attempts?: Record<string, unknown>[];
  /** Les lectures de la tentative `a2` (un renvoi des réponses) ; la dernière est répétée. */
  retryAttempts?: Record<string, unknown>[];
  /** Remplace la réponse de `GET /quizzes/z1` (une erreur, une lecture qui change). */
  quizReply?: () => Response;
}

/** Lectures REST d'une page de quiz : le quiz `z1` et sa tentative `a1`, qui évoluent à chaque lecture. */
export function quizApi(api: QuizApi = {}) {
  const quizzes = api.quizzes ?? [quizOut()];
  const attempts = api.attempts ?? [attemptOut()];
  const retries = api.retryAttempts ?? [attemptOut({ id: "a2" })];
  const state = { quizReads: 0, attemptReads: 0, retryReads: 0 };
  const handlers = [
    http.get(`${API}/quizzes/z1`, () => {
      if (api.quizReply) return api.quizReply();
      const read = quizzes[Math.min(state.quizReads, quizzes.length - 1)];
      state.quizReads += 1;
      return HttpResponse.json(read);
    }),
    http.get(`${API}/quizzes/z1/attempts/a1`, () => {
      const read = attempts[Math.min(state.attemptReads, attempts.length - 1)];
      state.attemptReads += 1;
      return HttpResponse.json(read);
    }),
    http.get(`${API}/quizzes/z1/attempts/a2`, () => {
      const read = retries[Math.min(state.retryReads, retries.length - 1)];
      state.retryReads += 1;
      return HttpResponse.json(read);
    }),
  ];
  return { state, handlers };
}
