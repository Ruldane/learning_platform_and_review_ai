import { useLaunchSource } from "@/shared/session-ui";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { createGoal } from "../api";
import { learningKeys } from "../queryKeys";
import type { GoalInput } from "../types";

/** Council path of a goal. */
export const councilPath = (goalId: string) => `/learn/goals/${goalId}/council`;

/**
 * Creates a goal (`POST /goals`, which starts the Council, D87) then opens its Council. The goal
 * returned seeds the cache: the Council page opens without waiting for a second read.
 */
export function useCreateGoal() {
  const launch = useLaunchSource();
  const client = useQueryClient();
  const navigate = useNavigate();
  const mutation = useMutation({
    mutationFn: (input: GoalInput) => createGoal(input, launch.source),
    onSuccess: ({ goal }) => {
      client.setQueryData(learningKeys.goal(goal.id), goal);
      void client.invalidateQueries({ queryKey: learningKeys.goals });
      void navigate(councilPath(goal.id));
    },
  });
  return {
    create: mutation.mutate,
    launchMenu: launch.menu,
    pending: mutation.isPending,
    error: mutation.error ? errorMessage(mutation.error) : null,
  };
}
