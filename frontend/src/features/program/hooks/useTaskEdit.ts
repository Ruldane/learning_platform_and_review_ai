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
 * Edits a task (`PATCH /tasks/{id}`: a move, or the « faite » checkbox). The change is
 * shown at once; if the server refuses (422: week over 85%, practice or quiz missing),
 * the previous state is restored, the server message goes to `onError`, then the program reloads.
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
