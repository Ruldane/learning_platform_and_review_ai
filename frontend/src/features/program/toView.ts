import type { PlanDiffTask, PlanDiffView, ProgramSummaryView, ProgressView } from "./types";
import type { TaskView, WeekView } from "./types";
import type { DayBudget, ModuleLessonView, PlanDiffOut, ProgramOut } from "./types";
import type { ProgramSummaryOut, TaskOut } from "./types";

const DAY_MS = 86_400_000;
/** Monday to Friday: weekday budget; Saturday: weekend block; Sunday: rest. */
const SATURDAY = 5;
const SUNDAY = 6;

function addDays(iso: string, days: number): string {
  return new Date(Date.parse(`${iso}T00:00:00Z`) + days * DAY_MS).toISOString().slice(0, 10);
}

function capacityOf(dayIndex: number, budget: DayBudget): number {
  if (dayIndex === SUNDAY) return 0;
  return dayIndex === SATURDAY ? budget.weekend : budget.weekday;
}

function toTaskView(task: TaskOut, moduleTitle: string): TaskView {
  return {
    id: task.id,
    moduleTitle,
    title: task.title,
    type: task.type,
    minutes: task.minutes,
    doneCriterion: task.done_criterion,
    plannedDate: task.planned_date,
    done: task.status === "done",
    alreadyKnown: task.already_known,
  };
}

/** All the program's tasks, with the title of their original module (a moved task keeps it). */
function allTasks(program: ProgramOut): TaskView[] {
  return program.weeks.flatMap((week) =>
    week.modules.flatMap((module) => module.tasks.map((task) => toTaskView(task, module.title))),
  );
}

/**
 * The calendar weeks: seven days from Monday, day capacity from the budget. Tasks
 * are placed by **planned day**, not by module: a task moved by January stays in
 * its module (D88) but appears in the week of its new day.
 */
export function toWeekViews(program: ProgramOut, budget: DayBudget): WeekView[] {
  const tasks = allTasks(program);
  return program.weeks.map((week) => {
    const days = Array.from({ length: 7 }, (_, index) => {
      const date = addDays(week.start_date, index);
      return {
        date,
        capacityMinutes: capacityOf(index, budget),
        tasks: tasks.filter((task) => task.plannedDate === date),
      };
    });
    return {
      rank: week.rank,
      theme: week.theme,
      objective: week.objective,
      deliverable: week.deliverable,
      stage: week.stage ?? null,
      rationale: week.rationale ?? null,
      startDate: week.start_date,
      loadMinutes: days.reduce((sum, day) => sum + day.tasks.reduce((s, x) => s + x.minutes, 0), 0),
      capMinutes: program.cap_minutes,
      days,
    };
  });
}

export function toProgressView(progress: ProgramOut["progress"]): ProgressView {
  return {
    tasksDone: progress.done_tasks,
    tasksPlanned: progress.total_tasks,
    minutesDone: progress.done_minutes,
    minutesPlanned: progress.total_minutes,
  };
}

const SEPARATOR = " / ";

/** "{module} / {task}" (back-end key): the module is what precedes the first separator. */
function splitKey(key: string): { moduleTitle: string; title: string } {
  const at = key.indexOf(SEPARATOR);
  if (at === -1) return { moduleTitle: "", title: key };
  return { moduleTitle: key.slice(0, at), title: key.slice(at + SEPARATOR.length) };
}

function plannedDates(program: ProgramOut): Map<string, string> {
  const dates = new Map<string, string>();
  for (const week of program.weeks) {
    for (const module of week.modules) {
      for (const task of module.tasks) {
        dates.set(`${module.title}${SEPARATOR}${task.title}`, task.planned_date);
      }
    }
  }
  return dates;
}

/**
 * The diff from the last version. The back end names tasks "module / task" without
 * an identifier: the planned day of an added task is read from the program; that of a
 * removed task no longer exists (`null`).
 */
export function toPlanDiffView(diff: PlanDiffOut, program: ProgramOut): PlanDiffView {
  const dates = plannedDates(program);
  const planned = (key: string): PlanDiffTask => ({
    id: key,
    ...splitKey(key),
    plannedDate: dates.get(key) ?? null,
  });
  return {
    added: diff.added.map(planned),
    removed: diff.removed.map((key) => ({ ...planned(key), plannedDate: null })),
    moved: diff.moved.map((move) => ({
      id: move.task,
      ...splitKey(move.task),
      from: move.before,
      to: move.after,
    })),
  };
}

/**
 * The module that receives a task added on `date`: the first non-skipped module of the week
 * that holds this day, otherwise the program's first. `null`: no module can take it.
 */
export function moduleForDate(program: ProgramOut, date: string): string | null {
  const week = program.weeks.find(
    (item) => item.start_date <= date && date < addDays(item.start_date, 7),
  );
  const inWeek = week?.modules.find((module) => !module.skipped);
  if (inWeek) return inWeek.id;
  const any = program.weeks.flatMap((item) => item.modules).find((module) => !module.skipped);
  return any?.id ?? null;
}

/** The lesson state of each planned module (skipped: no lesson), in program order. */
export function toModuleLessons(program: ProgramOut): ModuleLessonView[] {
  return program.weeks.flatMap((week) =>
    week.modules
      .filter((module) => !module.skipped)
      .map((module) => ({
        moduleId: module.id,
        moduleTitle: module.title,
        weekRank: week.rank,
        lessonId: module.lesson_id,
        status: module.lesson_status,
        completed:
          module.tasks.length > 0 && module.tasks.every((task) => task.status === "done"),
      })),
  );
}

/** A program from `GET /programs` for the « Mes programmes » list: progress in minutes. */
export function toProgramSummaryView(program: ProgramSummaryOut): ProgramSummaryView {
  const { done_minutes, total_minutes } = program.progress;
  const percent =
    total_minutes > 0 ? Math.min(100, Math.round((done_minutes / total_minutes) * 100)) : 0;
  return {
    id: program.id,
    title: program.title,
    status: program.status,
    startDate: program.start_date,
    weeks: program.weeks,
    percent,
  };
}
