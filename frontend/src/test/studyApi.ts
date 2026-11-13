import { http, HttpResponse } from "msw";
import { API, sessionOut } from "./councilApi";

/** Une session d'étude telle que le back la rend (`StudySessionOut`). */
export const studyOut = (over: Record<string, unknown> = {}) => ({
  id: "st1",
  lesson_id: "l1",
  lesson_title: "Les API REST",
  module_title: "Web",
  mode: "socratic",
  status: "open",
  session_id: "s1",
  started_at: "2026-11-17T10:00:00Z",
  ended_at: null,
  minutes: 0,
  summary: null,
  tasks_done: [],
  flashcards_created: 0,
  skills: [],
  ...over,
});

/** Le résumé de l'étude (`StudySummaryOut`) avec un bloc du jour par défaut. */
export const summaryOut = (over: Record<string, unknown> = {}) => ({
  streak_days: 5,
  week_minutes: 210,
  work_minutes: 50,
  break_minutes: 10,
  open_session_id: null,
  block: {
    lesson_id: "l1",
    lesson_title: "Les API REST",
    module_title: "Web",
    tasks: [{ id: "t1", title: "Lire la leçon", minutes: 30, type: "lire" }],
  },
  ...over,
});

interface StudyApi {
  summary?: Record<string, unknown>;
  /** Les lectures successives de `GET /study-sessions/st1` (la dernière est répétée). */
  sessions?: Record<string, unknown>[];
  status?: string;
  /** Remplace la réponse de `GET /study-sessions/st1` (une erreur, une lecture qui change). */
  sessionReply?: () => Response;
}

/**
 * Lectures REST d'une page de la session d'étude : résumé, session `st1` (les lectures se suivent)
 * et statut de la session d'agents `s1`.
 */
export function studyApi(api: StudyApi = {}) {
  const reads = api.sessions ?? [studyOut()];
  const state = { reads: 0, status: api.status ?? "running" };
  const handlers = [
    http.get(`${API}/study-sessions/summary`, () => HttpResponse.json(api.summary ?? summaryOut())),
    http.get(`${API}/study-sessions/st1`, () => {
      if (api.sessionReply) return api.sessionReply();
      const read = reads[Math.min(state.reads, reads.length - 1)];
      state.reads += 1;
      return HttpResponse.json(read);
    }),
    http.get(`${API}/sessions/s1`, () =>
      HttpResponse.json(sessionOut("s1", state.status, { graph: "study_session" })),
    ),
  ];
  return { state, handlers };
}
