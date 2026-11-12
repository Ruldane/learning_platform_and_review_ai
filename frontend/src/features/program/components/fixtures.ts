import type { DayView, TaskView, WeekView } from "./viewTypes";

export function makeTask(overrides: Partial<TaskView> = {}): TaskView {
  return {
    id: "t1",
    moduleTitle: "Bases du langage",
    title: "Lire le chapitre 1",
    type: "lire",
    minutes: 60,
    doneCriterion: "Je sais expliquer les variables.",
    plannedDate: "2026-11-16",
    done: false,
    alreadyKnown: false,
    ...overrides,
  };
}

const DATES = [
  "2026-11-16",
  "2026-11-17",
  "2026-11-18",
  "2026-11-19",
  "2026-11-20",
  "2026-11-21",
  "2026-11-22",
];
const CAPACITIES = [120, 120, 120, 120, 120, 240, 180];

/** Semaine type : le lundi porte 150 min pour 120 min de capacité. */
export function makeWeek(overrides: Partial<WeekView> = {}): WeekView {
  const tasksByDate: Record<string, TaskView[]> = {
    "2026-11-16": [
      makeTask(),
      makeTask({ id: "t2", title: "Pratiquer les boucles", type: "pratiquer", minutes: 90 }),
    ],
    "2026-11-18": [
      makeTask({
        id: "t3",
        title: "Réviser les types",
        minutes: 20,
        plannedDate: "2026-11-18",
        alreadyKnown: true,
        done: true,
      }),
    ],
    "2026-11-22": [
      makeTask({
        id: "t4",
        title: "Faire le quiz de la semaine",
        type: "quiz",
        minutes: 30,
        plannedDate: "2026-11-22",
      }),
    ],
  };
  const days: DayView[] = DATES.map((date, index) => ({
    date,
    capacityMinutes: CAPACITIES[index] ?? 120,
    tasks: tasksByDate[date] ?? [],
  }));
  return {
    rank: 1,
    theme: "Premiers pas en Python",
    objective: "Écrire un script de 50 lignes sans aide.",
    deliverable: "Un script qui trie un fichier CSV.",
    startDate: "2026-11-16",
    loadMinutes: 690,
    capMinutes: 714,
    days,
    ...overrides,
  };
}
