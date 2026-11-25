import { councilEvents } from "./councilEvents";
import { studyOut } from "./studyApi";

/** The options of a tutor question: labels and values come from the back (F15). */
export const tutorOptions = [
  { value: "stuck", label: "Je bloque (1/3)" },
  { value: "skip", label: "Passer" },
];

export const answerField = { id: "answer", label: "Ta réponse", max_length: 4000, required: false };

/** A finished session with its wrap-up. */
export const finishedOut = (over: Record<string, unknown> = {}) =>
  studyOut({
    status: "finished",
    minutes: 2,
    summary: "Tu as compris les verbes HTTP.",
    tasks_done: ["Lire la leçon"],
    flashcards_created: 3,
    skills: [{ name: "REST", level: "in_progress" }],
    ended_at: "2026-11-17T10:50:00Z",
    ...over,
  });

/** A tutor section question (`tutor_question`), ready to push into the stream. */
export const tutorQuestion = (e: ReturnType<typeof councilEvents>, id = "i1") =>
  e.interrupt("tutor_question", id, {
    question: "Que fait GET ?",
    options: tutorOptions,
    fields: [answerField],
  });

/** The resume response of an agent session that the back returns after an answer. */
export const resumedSession = {
  id: "s1",
  graph: "study_session",
  status: "running",
  last_seq: 0,
  pending_interrupt: null,
};
