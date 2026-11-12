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
  /** Rejette si le serveur refuse : le formulaire garde alors la saisie. */
  add: (input: NewTaskInput) => Promise<unknown>;
  /** Refus ou échec d'un déplacement, d'une case cochée ou d'une suppression. */
  error: string | null;
  /** Refus de l'ajout, affiché sous le formulaire. */
  addError: string | null;
}

/**
 * Les retouches du programme : déplacer, cocher, supprimer et ajouter des tâches, par REST. Chaque
 * refus du serveur est dit tel quel ; le programme est relu après chaque retouche.
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
