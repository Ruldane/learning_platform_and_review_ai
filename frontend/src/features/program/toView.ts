import type { PlanDiffTask, PlanDiffView, ProgressView, TaskView, WeekView } from "./types";
import type { DayBudget, ModuleLessonView, PlanDiffOut, ProgramOut, TaskOut } from "./types";

const DAY_MS = 86_400_000;
/** Lundi à vendredi : budget en semaine ; samedi : bloc du week-end ; dimanche : repos. */
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

/** Toutes les tâches du programme, avec le titre du module d'origine (une tâche déplacée le garde). */
function allTasks(program: ProgramOut): TaskView[] {
  return program.weeks.flatMap((week) =>
    week.modules.flatMap((module) => module.tasks.map((task) => toTaskView(task, module.title))),
  );
}

/**
 * Les semaines du calendrier : sept jours depuis le lundi, capacité du jour selon le budget. Les
 * tâches se placent par **jour planifié**, pas par module : une tâche déplacée par January reste
 * dans son module (D88) mais apparaît dans la semaine de son nouveau jour.
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

/** « {module} / {tâche} » (clé du back) : le module est ce qui précède le premier séparateur. */
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
 * La différence de la dernière version. Le back nomme les tâches « module / tâche » sans
 * identifiant : le jour prévu d'une tâche ajoutée se relit dans le programme, celui d'une tâche
 * retirée n'existe plus (`null`).
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
 * Le module qui reçoit une tâche ajoutée à `date` : le premier module non sauté de la semaine qui
 * porte ce jour, sinon le premier du programme. `null` : aucun module ne peut l'accueillir.
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

/** L'état de la leçon de chaque module planifié (sauté : pas de leçon), dans l'ordre du programme. */
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
      })),
  );
}
