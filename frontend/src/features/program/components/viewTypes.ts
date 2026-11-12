/** Types de vue des composants du programme : indépendants du contrat d'API (D34). */

export type TaskType = "lire" | "regarder" | "pratiquer" | "quiz" | "projet";

/** Durée d'une tâche, en minutes (SPEC 3.4) : de 15 à 120. */
export const TASK_MIN_MINUTES = 15;
export const TASK_MAX_MINUTES = 120;

export interface TaskView {
  id: string;
  moduleTitle: string;
  title: string;
  type: TaskType;
  minutes: number;
  doneCriterion: string;
  /** Jour planifié, au format `AAAA-MM-JJ`. */
  plannedDate: string;
  done: boolean;
  /** Sujet déjà acquis : la tâche est réduite à une révision. */
  alreadyKnown: boolean;
}

export interface DayView {
  /** `AAAA-MM-JJ`. */
  date: string;
  capacityMinutes: number;
  tasks: TaskView[];
}

export interface WeekView {
  rank: number;
  theme: string;
  objective: string;
  deliverable: string;
  /** Lundi de la semaine, `AAAA-MM-JJ`. */
  startDate: string;
  /** Charge planifiée, en minutes. */
  loadMinutes: number;
  /** Plafond de la semaine (85 % du budget), en minutes. */
  capMinutes: number;
  days: DayView[];
}

/** Saisie du formulaire d'ajout d'une tâche. */
export interface NewTaskInput {
  title: string;
  type: TaskType;
  minutes: number;
  doneCriterion: string;
  plannedDate: string;
}

export interface PlanDiffTask {
  id: string;
  title: string;
  moduleTitle: string;
  plannedDate: string;
}

export interface PlanDiffMove {
  id: string;
  title: string;
  moduleTitle: string;
  from: string;
  to: string;
}

export interface PlanDiffView {
  added: PlanDiffTask[];
  removed: PlanDiffTask[];
  moved: PlanDiffMove[];
}

export interface ProgressView {
  tasksDone: number;
  tasksPlanned: number;
  minutesDone: number;
  minutesPlanned: number;
}
