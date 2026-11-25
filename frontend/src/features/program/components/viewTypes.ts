/** View types of the program components: independent of the API contract (D34). */

export type TaskType = "read" | "watch" | "practice" | "quiz" | "project";

/** A task's duration, in minutes (SPEC 3.4): from 15 to 120. */
export const TASK_MIN_MINUTES = 15;
export const TASK_MAX_MINUTES = 120;

export interface TaskView {
  id: string;
  moduleTitle: string;
  title: string;
  type: TaskType;
  minutes: number;
  doneCriterion: string;
  /** Planned day, in `YYYY-MM-DD` format. */
  plannedDate: string;
  done: boolean;
  /** Subject already acquired: the task is cut down to a revision. */
  alreadyKnown: boolean;
}

export interface DayView {
  /** `AAAA-MM-JJ`. */
  date: string;
  capacityMinutes: number;
  tasks: TaskView[];
}

/** Book stage where a week sits. */
export type WeekStage = "foundations" | "practice" | "advanced";

export interface WeekView {
  rank: number;
  theme: string;
  objective: string;
  deliverable: string;
  /** Book stage, `null` if the program does not give it. */
  stage: WeekStage | null;
  /** Why the week falls at this place, `null` if the program does not give it. */
  rationale: string | null;
  /** Monday of the week, `YYYY-MM-DD`. */
  startDate: string;
  /** Planned load, in minutes. */
  loadMinutes: number;
  /** Week cap (85% of the budget), in minutes. */
  capMinutes: number;
  days: DayView[];
}

/** Input of the add-task form. */
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

/** A program in the « Mes programmes » list. */
export interface ProgramSummaryView {
  id: string;
  title: string;
  status: "draft" | "validated";
  /** Start, in `YYYY-MM-DD` format. */
  startDate: string;
  weeks: number;
  /** Progress in minutes done, from 0 to 100. */
  percent: number;
}
