import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import { errorMessage } from "@/shared/api/errors";
import type { BoardEdit } from "@/shared/session-ui";
import { postBoardEdit } from "../api";
import { learningKeys } from "../queryKeys";
import type { BoardOut } from "../types";

/**
 * January's edits sent to the agents (`POST /boards/{id}/edits`). The saved state
 * joins the board at once; a failed send rejects it (the board says so and keeps the
 * button active) and `error` carries the French message.
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
