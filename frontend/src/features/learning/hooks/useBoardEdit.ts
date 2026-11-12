import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import { errorMessage } from "@/shared/api/errors";
import type { BoardEdit } from "@/shared/session-ui";
import { postBoardEdit } from "../api";
import { learningKeys } from "../queryKeys";
import type { BoardOut } from "../types";

/**
 * Les retouches de January envoyées aux agents (`POST /boards/{id}/edits`). L'état enregistré
 * rejoint le tableau tout de suite ; l'envoi qui échoue rejette (le tableau le dit et garde le
 * bouton actif) et `error` porte le message français.
 */
export function useBoardEdit(goalId: string) {
  const client = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ boardId, edit }: { boardId: string; edit: BoardEdit }) =>
      postBoardEdit(boardId, edit),
    onSuccess: (saved) =>
      client.setQueryData<BoardOut[]>(learningKeys.boards(goalId), (old) => [
        ...(old ?? []).filter((board) => board.id !== saved.id),
        saved,
      ]),
  });
  const { mutateAsync } = mutation;
  const send = useCallback(
    async (boardId: string, edit: BoardEdit) => {
      await mutateAsync({ boardId, edit });
    },
    [mutateAsync],
  );
  return {
    send,
    pending: mutation.isPending,
    error: mutation.error ? errorMessage(mutation.error) : null,
  };
}
