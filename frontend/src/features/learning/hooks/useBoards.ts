import { useQuery } from "@tanstack/react-query";
import { useCallback } from "react";
import { fetchBoards } from "../api";
import { learningKeys } from "../queryKeys";
import { toBoardView } from "../toView";
import type { BoardOut } from "../types";

/**
 * The saved board states of the Council `sessionId` (`GET /goals/{id}/boards`); the live feed
 * adds to it (`boardsFromEvents`). The backend also returns those of a restarted Council: they
 * are not shown.
 */
export function useBoards(goalId: string, sessionId: string) {
  const select = useCallback(
    (boards: BoardOut[]) =>
      boards.filter((board) => board.session_id === sessionId).map(toBoardView),
    [sessionId],
  );
  return useQuery({
    queryKey: learningKeys.boards(goalId),
    queryFn: ({ signal }) => fetchBoards(goalId, signal),
    select,
  });
}
