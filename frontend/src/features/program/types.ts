import type { components } from "@/shared/api/schema";

type Schemas = components["schemas"];

export type ProgramOut = Schemas["ProgramOut"];
export type ProgramSummaryOut = Schemas["ProgramSummaryOut"];
export type WeekOut = Schemas["WeekOut"];
export type ModuleOut = Schemas["ModuleOut"];
export type TaskOut = Schemas["TaskOut"];
export type TaskPatch = Schemas["TaskPatch"];
export type PlanDiffOut = Schemas["PlanDiffOut"];
export type ValidateOut = Schemas["ValidateOut"];
export type LessonStatus = NonNullable<ModuleOut["lesson_status"]>;

export type {
  NewTaskInput,
  PlanDiffTask,
  PlanDiffView,
  ProgressView,
  TaskView,
  WeekView,
} from "./components/viewTypes";

/** Une leçon de module, telle que la liste du programme la montre. */
export interface ModuleLessonView {
  moduleId: string;
  moduleTitle: string;
  weekRank: number;
  /** `null` : la leçon du module n'existe pas encore. */
  lessonId: string | null;
  status: LessonStatus | null;
}

/** Budget de disponibilité d'un programme, en minutes par jour. */
export interface DayBudget {
  weekday: number;
  weekend: number;
}
