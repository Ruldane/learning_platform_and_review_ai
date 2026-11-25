import { useMutation, useQueryClient } from "@tanstack/react-query";
import { undoChange } from "../api";
import { useIdAction } from "./useIdAction";

/** Undoes the changes of a call; the restored rows may show up elsewhere. */
export function useUndoChange() {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: undoChange,
    onSettled: () => queryClient.invalidateQueries(),
  });
  return useIdAction(mutation.mutateAsync);
}
