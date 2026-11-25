import { http, HttpResponse } from "msw";
import { API, sessionOut } from "./councilApi";

/** A study session as the back returns it (`StudySessionOut`). */
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

/** The study summary (`StudySummaryOut`) with a daily block by default. */
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
    tasks: [{ id: "t1", title: "Lire la leçon", minutes: 30, type: "read" }],
  },
  ...over,
});

interface StudyApi {
  summary?: Record<string, unknown>;
  /** Overrides the response of `GET /study-sessions/summary` (a read that changes). */
  summaryReply?: () => Response;
  /** Successive reads of `GET /study-sessions/st1` (the last one repeats). */
  sessions?: Record<string, unknown>[];
  status?: string;
  /** Overrides the response of `GET /study-sessions/st1` (an error, or a read that changes). */
  sessionReply?: () => Response;
}

/**
 * REST reads of a study session page: summary, session `st1` (the reads follow each other)
 * and the agent session's status `s1`.
 */
export function studyApi(api: StudyApi = {}) {
  const reads = api.sessions ?? [studyOut()];
  const state = { reads: 0, status: api.status ?? "running" };
  const handlers = [
    http.get(`${API}/study-sessions/summary`, () =>
      api.summaryReply ? api.summaryReply() : HttpResponse.json(api.summary ?? summaryOut()),
    ),
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
