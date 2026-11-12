import type { ProgramOut, TaskPatch } from "../types";

/**
 * Le programme avec la retouche d'une tâche déjà appliquée (jour ou statut) : montrée tout de suite,
 * en attendant le serveur, qui garde le dernier mot (refus 422 : l'état d'avant est remis).
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
