/** Types de vue des composants du programme : indépendants du contrat d'API (D34). */

export type TaskType = "read" | "watch" | "practice" | "quiz" | "project";

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

/** Étape du livre où se place une semaine. */
export type WeekStage = "foundations" | "practice" | "advanced";

export interface WeekView {
  rank: number;
  theme: string;
  objective: string;
  deliverable: string;
  /** Étape du livre, `null` si le programme ne la donne pas. */
  stage: WeekStage | null;
  /** Pourquoi la semaine arrive à cette place, `null` si le programme ne la donne pas. */
  rationale: string | null;
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

export interface ProgressView {
  tasksDone: number;
  tasksPlanned: number;
  minutesDone: number;
  minutesPlanned: number;
}

/** Un programme dans la liste « Mes programmes ». */
export interface ProgramSummaryView {
  id: string;
  title: string;
  status: "draft" | "validated";
  /** Début, au format `AAAA-MM-JJ`. */
  startDate: string;
  weeks: number;
  /** Avancement en minutes faites, de 0 à 100. */
  percent: number;
}
