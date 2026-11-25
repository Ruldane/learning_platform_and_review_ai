import { api, apiBaseUrl } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { NewTaskInput, TaskPatch } from "./types";

const programPath = (programId: string) => ({ params: { path: { program_id: programId } } });

/** `GET /programs`: from newest to oldest. */
export async function fetchPrograms(signal?: AbortSignal) {
  return unwrap(await api.GET("/programs", { signal }));
}

/** `GET /programs/{id}`: weeks, modules, tasks, progress and version diff. */
export async function fetchProgram(programId: string, signal?: AbortSignal) {
  return unwrap(await api.GET("/programs/{program_id}", { ...programPath(programId), signal }));
}

/** `PATCH /tasks/{id}`: day, duration, title or status; 422 if a week rule breaks (D88). */
export async function patchTask(taskId: string, body: TaskPatch) {
  return unwrap(
    await api.PATCH("/tasks/{task_id}", { params: { path: { task_id: taskId } }, body }),
  );
}

/** `PATCH /programs/{id}`: task deletions. */
export async function deleteTasks(programId: string, taskIds: string[]) {
  return unwrap(
    await api.PATCH("/programs/{program_id}", {
      ...programPath(programId),
      body: { delete_task_ids: taskIds },
    }),
  );
}

/** `PATCH /programs/{id}`: adds a task to a module. */
export async function addTask(programId: string, moduleId: string, input: NewTaskInput) {
  return unwrap(
    await api.PATCH("/programs/{program_id}", {
      ...programPath(programId),
      body: {
        add_tasks: [
          {
            module_id: moduleId,
            title: input.title,
            type: input.type,
            minutes: input.minutes,
            done_criterion: input.doneCriterion,
            planned_date: input.plannedDate,
          },
        ],
      },
    }),
  );
}

/** `POST /programs/{id}/validate`: validates, or resumes the Strategist's session (202). */
export async function validateProgram(programId: string) {
  return unwrap(await api.POST("/programs/{program_id}/validate", programPath(programId)));
}

/** Export addresses: plain links, the browser downloads. */
export const exportPdfUrl = (programId: string) =>
  `${apiBaseUrl}/api/v1/programs/${programId}/export.pdf`;
export const exportIcsUrl = (programId: string) =>
  `${apiBaseUrl}/api/v1/programs/${programId}/export.ics`;
