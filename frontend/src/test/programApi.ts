import { http, HttpResponse } from "msw";
import { API, sessionOut } from "./councilApi";

export { API, sessionOut };

/** Une tâche telle que le back la rend (`TaskOut`). */
export const taskOut = (over: Record<string, unknown> = {}) => ({
  id: "t1",
  module_id: "m1",
  title: "Lire le chapitre 1",
  type: "lire",
  minutes: 60,
  done_criterion: "Je sais expliquer les variables.",
  planned_date: "2026-11-16",
  status: "todo",
  already_known: false,
  ...over,
});

export const moduleOut = (over: Record<string, unknown> = {}) => ({
  id: "m1",
  rank: 1,
  title: "Bases du langage",
  skills: ["Python"],
  prerequisites: [],
  skipped: false,
  lesson_id: "l1",
  lesson_status: "ready",
  resources_count: 3,
  tasks: [
    taskOut(),
    taskOut({ id: "t2", title: "Pratiquer les boucles", type: "pratiquer", minutes: 90 }),
    taskOut({
      id: "t3",
      title: "Faire le quiz",
      type: "quiz",
      minutes: 30,
      planned_date: "2026-11-18",
    }),
  ],
  ...over,
});

export const weekOut = (over: Record<string, unknown> = {}) => ({
  id: "w1",
  rank: 1,
  theme: "Premiers pas en Python",
  objective: "Écrire un script de 50 lignes sans aide.",
  deliverable: "Un script qui trie un fichier CSV.",
  start_date: "2026-11-16",
  load_minutes: 180,
  load_hours: 3,
  modules: [moduleOut()],
  ...over,
});

const WEEK_2 = weekOut({
  id: "w2",
  rank: 2,
  theme: "Données et fichiers",
  start_date: "2026-11-23",
  modules: [
    moduleOut({
      id: "m2",
      rank: 2,
      title: "Fichiers CSV",
      lesson_id: "l2",
      lesson_status: "generating",
      tasks: [
        taskOut({
          id: "t4",
          module_id: "m2",
          title: "Lire le module csv",
          planned_date: "2026-11-23",
        }),
        taskOut({
          id: "t5",
          module_id: "m2",
          title: "Pratiquer le tri",
          type: "pratiquer",
          planned_date: "2026-11-24",
          status: "done",
        }),
      ],
    }),
  ],
});

/** Un programme tel que le back le rend (`ProgramOut`) : deux semaines, 5 tâches. */
export const programOut = (over: Record<string, unknown> = {}) => ({
  id: "p1",
  goal_id: "g1",
  title: "Python pour la data",
  status: "draft",
  version: 1,
  start_date: "2026-11-16",
  weekly_minutes: 840,
  cap_minutes: 714,
  weekday_minutes: 120,
  weekend_minutes: 240,
  session_id: "s1",
  weeks: [weekOut(), WEEK_2],
  progress: { done_tasks: 1, total_tasks: 5, done_minutes: 60, total_minutes: 300 },
  diff: null,
  ...over,
});

export const summaryOut = (over: Record<string, unknown> = {}) => ({
  id: "p1",
  goal_id: "g1",
  title: "Python pour la data",
  status: "validated",
  start_date: "2026-11-16",
  weeks: 2,
  progress: { done_tasks: 0, total_tasks: 5, done_minutes: 0, total_minutes: 300 },
  ...over,
});

/** La session du Stratège en attente de la validation (point d'arrêt n° 3). */
export const validationSession = (status = "waiting_user", id = "s1") =>
  sessionOut(id, status, {
    graph: "program_builder",
    subject_type: "program",
    subject_id: "p1",
    pending_interrupt:
      status === "waiting_user"
        ? {
            interrupt_id: "i1",
            kind: "validate_program",
            question: "Valide ?",
            options: [{ value: "validate", label: "Valider le programme" }],
            fields: [{ id: "note", label: "Ce qu'il faut revoir" }],
          }
        : null,
  });

/** Lectures d'un programme et de sa session ; `program` et `session` sont relus à chaque requête. */
export function programApi(
  initial: { program?: Record<string, unknown>; session?: Record<string, unknown> | null } = {},
) {
  const state = {
    program: initial.program ?? programOut(),
    session: initial.session === undefined ? validationSession() : initial.session,
  };
  const handlers = [
    http.get(`${API}/programs/p1`, () => HttpResponse.json(state.program)),
    http.get(`${API}/sessions/s1`, () =>
      state.session ? HttpResponse.json(state.session) : HttpResponse.json({}, { status: 404 }),
    ),
  ];
  return { state, handlers };
}
