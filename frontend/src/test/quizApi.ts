import { http, HttpResponse } from "msw";
import { API } from "./councilApi";

/** The two questions of a quiz, in first-attempt order. */
export const firstOrder = [
  {
    id: "q1",
    rank: 1,
    type: "mcq",
    prompt: "Quel verbe lit une ressource ?",
    code: null,
    choices: ["GET", "POST"],
  },
  { id: "q2", rank: 2, type: "short", prompt: "Que fait PUT ?", code: null, choices: [] },
];

/** The same questions on the retry: the order is shuffled (F27). */
export const secondOrder = [
  { ...firstOrder[1]!, rank: 1 },
  { ...firstOrder[0]!, rank: 2, choices: ["POST", "GET"] },
];

/** A quiz as the back returns it (`QuizOut`). */
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

/** A graded attempt (`AttemptOut`): one correct multiple choice, one wrong short answer. */
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
  /** Successive reads of `GET /quizzes/z1` (the last one repeats). */
  quizzes?: Record<string, unknown>[];
  /** Successive reads of `GET /quizzes/z1/attempts/a1` (the last one repeats). */
  attempts?: Record<string, unknown>[];
  /** Reads of attempt `a2` (a resend of the answers); the last one repeats. */
  retryAttempts?: Record<string, unknown>[];
  /** Overrides the response of `GET /quizzes/z1` (an error, or a read that changes). */
  quizReply?: () => Response;
}

/** REST reads of a quiz page: quiz `z1` and its attempt `a1`, which change on each read. */
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
