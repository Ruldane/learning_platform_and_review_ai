import type { ProgramOut, TaskPatch } from "../types";

/**
 * The program with a task's already-applied edit (day or status): shown at once,
 * while waiting for the server, which has the last word (on a 422 refusal, the old state returns).
 */
export function withTaskPatch(program: ProgramOut, taskId: string, patch: TaskPatch): ProgramOut {
  return {
    ...program,
    weeks: program.weeks.map((week) => ({
      ...week,
      modules: week.modules.map((module) => ({
        ...module,
        tasks: module.tasks.map((task) =>
          task.id === taskId
            ? {
                ...task,
                planned_date: patch.planned_date ?? task.planned_date,
                status: patch.status ?? task.status,
              }
            : task,
        ),
      })),
    })),
  };
}
