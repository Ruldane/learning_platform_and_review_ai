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

export type { PlanDiffTask, PlanDiffView } from "@/shared/session-ui";
export type {
  NewTaskInput,
  ProgramSummaryView,
  ProgressView,
  TaskView,
  WeekView,
} from "./components/viewTypes";

/** A module lesson, as the program list shows it. */
export interface ModuleLessonView {
  moduleId: string;
  moduleTitle: string;
  weekRank: number;
  /** `null`: the module's lesson does not exist yet. */
  lessonId: string | null;
  status: LessonStatus | null;
  /** All the module's tasks are done (at least one): lesson complete. */
  completed: boolean;
}

/** A program's availability budget, in minutes per day. */
export interface DayBudget {
  weekday: number;
  weekend: number;
}
