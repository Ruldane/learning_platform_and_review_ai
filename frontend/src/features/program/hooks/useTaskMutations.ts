import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { errorMessage } from "@/shared/api/errors";
import type { NewTaskInput } from "../types";
import { deleteTasks } from "../api";
import { programKeys } from "../queryKeys";
import { useTaskAdd } from "./useTaskAdd";
import { useTaskEdit } from "./useTaskEdit";

export interface TaskEdits {
  move: (taskId: string, date: string) => void;
  toggleDone: (taskId: string, done: boolean) => void;
  remove: (taskId: string) => void;
  /** Rejects if the server refuses: the form then keeps the input. */
  add: (input: NewTaskInput) => Promise<unknown>;
  /** Refusal or failure of a move, a ticked box or a deletion. */
  error: string | null;
  /** Refusal of the addition, shown under the form. */
  addError: string | null;
}

/**
 * Edits to the program: move, tick, delete and add tasks, over REST. Each
 * server refusal is passed on as is; the program is reloaded after each edit.
 */
export function useTaskMutations(programId: string): TaskEdits {
  const client = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const edit = useTaskEdit(programId, (failure) => setError(errorMessage(failure)));
  const added = useTaskAdd(programId);
  const { mutate: remove } = useMutation({
    mutationFn: (taskId: string) => deleteTasks(programId, [taskId]),
    onError: (failure) => setError(errorMessage(failure)),
    onSettled: () => client.invalidateQueries({ queryKey: programKeys.detail(programId) }),
  });
  const run = (action: () => void) => {
    setError(null);
    action();
  };
  return {
    move: (taskId, date) => run(() => edit({ taskId, patch: { planned_date: date } })),
    toggleDone: (taskId, done) =>
      run(() => edit({ taskId, patch: { status: done ? "done" : "todo" } })),
    remove: (taskId) => run(() => remove(taskId)),
    add: added.add,
    error,
    addError: added.error,
  };
}
