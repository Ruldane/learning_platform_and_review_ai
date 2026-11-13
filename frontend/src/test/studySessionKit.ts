import { councilEvents } from "./councilEvents";
import { studyOut } from "./studyApi";

/** Les options d'une question du Tuteur : libellés et valeurs viennent du back (F15). */
export const tutorOptions = [
  { value: "stuck", label: "Je bloque (1/3)" },
  { value: "skip", label: "Passer" },
];

export const answerField = { id: "answer", label: "Ta réponse", max_length: 4000, required: false };

/** Une session terminée avec son bilan. */
export const finishedOut = (over: Record<string, unknown> = {}) =>
  studyOut({
    status: "finished",
    minutes: 2,
    summary: "Tu as compris les verbes HTTP.",
    tasks_done: ["Lire la leçon"],
    flashcards_created: 3,
    skills: [{ name: "REST", level: "en_cours" }],
    ended_at: "2026-11-17T10:50:00Z",
    ...over,
  });

/** La question d'une section du Tuteur (`tutor_question`), prête à pousser dans le flux. */
export const tutorQuestion = (e: ReturnType<typeof councilEvents>, id = "i1") =>
  e.interrupt("tutor_question", id, {
    question: "Que fait GET ?",
    options: tutorOptions,
    fields: [answerField],
  });

/** La réponse de reprise d'une session d'agents que le back rend après une réponse. */
export const resumedSession = {
  id: "s1",
  graph: "study_session",
  status: "running",
  last_seq: 0,
  pending_interrupt: null,
};
