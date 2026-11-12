import { useMutation, useQueryClient } from "@tanstack/react-query";
import { patchTask } from "../api";
import { withTaskPatch } from "./optimistic";
import { programKeys } from "../queryKeys";
import type { ProgramOut, TaskPatch } from "../types";

interface Edit {
  taskId: string;
  patch: TaskPatch;
}

/**
 * Retouche d'une tâche (`PATCH /tasks/{id}` : déplacement ou case « faite »). Le changement est
 * montré aussitôt ; si le serveur refuse (422 : semaine au-delà de 85 %, pratique ou quiz manquant),
 * l'état d'avant est remis, le message du serveur est dit par `onError`, puis le programme est relu.
 */
export function useTaskEdit(programId: string, onError: (failure: unknown) => void) {
  const client = useQueryClient();
  const key = programKeys.detail(programId);
  const mutation = useMutation({
    mutationFn: ({ taskId, patch }: Edit) => patchTask(taskId, patch),
    onMutate: async ({ taskId, patch }) => {
      await client.cancelQueries({ queryKey: key });
      const previous = client.getQueryData<ProgramOut>(key);
      if (previous) client.setQueryData(key, withTaskPatch(previous, taskId, patch));
      return { previous };
    },
    onError: (failure, _edit, context) => {
      if (context?.previous) client.setQueryData(key, context.previous);
      onError(failure);
    },
    onSettled: () => client.invalidateQueries({ queryKey: key }),
  });
  return mutation.mutate;
}
