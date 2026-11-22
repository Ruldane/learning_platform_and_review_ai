import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { components } from "@/shared/api/schema";

export type Routine = components["schemas"]["RoutineOut"];
export type RoutineAction = Routine["action"];
export type Execution = components["schemas"]["ExecutionOut"];
type RoutinePatch = components["schemas"]["RoutinePatch"];

export async function readRoutines() {
  return unwrap(await api.GET("/routines"));
}

export async function createRoutine(action: RoutineAction, hour: string) {
  return unwrap(
    await api.POST("/routines", {
      body: { action, local_time: hour },
    }),
  );
}

export async function updateRoutine(id: string, body: RoutinePatch) {
  return unwrap(
    await api.PATCH("/routines/{routine_id}", {
      params: { path: { routine_id: id } },
      body,
    }),
  );
}

export async function readHistory(id: string) {
  return unwrap(
    await api.GET("/routines/{routine_id}/executions", {
      params: { path: { routine_id: id } },
    }),
  );
}

export async function executeRoutine(id: string, receipt: string) {
  return unwrap(
    await api.POST("/routines/{routine_id}/executions", {
      params: { path: { routine_id: id } },
      body: { receipt },
    }),
  );
}
