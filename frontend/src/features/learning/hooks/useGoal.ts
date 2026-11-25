import { useQuery } from "@tanstack/react-query";
import { fetchGoal } from "../api";
import { learningKeys } from "../queryKeys";

const POLL_MS = 2000;

/**
 * A goal (`GET /goals/{id}`). Once a path is chosen, the program starts in a background
 * task: `waitingForProgram` re-reads the goal every 2 s until its session appears.
 */
export function useGoal(goalId: string, waitingForProgram = false) {
  return useQuery({
    queryKey: learningKeys.goal(goalId),
    queryFn: ({ signal }) => fetchGoal(goalId, signal),
    refetchInterval: (query) =>
      waitingForProgram && !query.state.data?.program_session_id ? POLL_MS : false,
  });
}
