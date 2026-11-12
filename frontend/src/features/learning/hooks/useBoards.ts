import { useQuery } from "@tanstack/react-query";
import { fetchBoards } from "../api";
import { learningKeys } from "../queryKeys";
import { toBoardView } from "../toView";
import type { BoardOut } from "../types";

const toViews = (boards: BoardOut[]) => boards.map(toBoardView);

/** Les états enregistrés du tableau (`GET /goals/{id}/boards`) ; le direct s'y ajoute (`boardsFromEvents`). */
export function useBoards(goalId: string) {
  return useQuery({
    queryKey: learningKeys.boards(goalId),
    queryFn: ({ signal }) => fetchBoards(goalId, signal),
    select: toViews,
  });
}
