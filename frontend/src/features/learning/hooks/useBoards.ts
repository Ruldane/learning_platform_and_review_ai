import { useQuery } from "@tanstack/react-query";
import { useCallback } from "react";
import { fetchBoards } from "../api";
import { learningKeys } from "../queryKeys";
import { toBoardView } from "../toView";
import type { BoardOut } from "../types";

/**
 * Les états enregistrés du tableau du Conseil `sessionId` (`GET /goals/{id}/boards`) ; le direct s'y
 * ajoute (`boardsFromEvents`). Le back rend aussi ceux d'un Conseil relancé depuis : ils ne
 * s'affichent pas.
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
