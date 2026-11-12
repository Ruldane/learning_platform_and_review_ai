import { useQuery } from "@tanstack/react-query";
import { fetchGoal } from "../api";
import { learningKeys } from "../queryKeys";

const POLL_MS = 2000;

/**
 * Un objectif (`GET /goals/{id}`). Une fois le parcours choisi, le programme se lance en tâche de
 * fond : `waitingForProgram` relit l'objectif toutes les 2 s jusqu'à ce que sa session apparaisse.
 */
export function useGoal(goalId: string, waitingForProgram = false) {
  return useQuery({
    queryKey: learningKeys.goal(goalId),
    queryFn: ({ signal }) => fetchGoal(goalId, signal),
    refetchInterval: (query) =>
      waitingForProgram && !query.state.data?.program_session_id ? POLL_MS : false,
  });
}
