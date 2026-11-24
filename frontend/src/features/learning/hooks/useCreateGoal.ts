import { useLaunchSource } from "@/shared/session-ui";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { createGoal } from "../api";
import { learningKeys } from "../queryKeys";
import type { GoalInput } from "../types";

/** Chemin du Conseil d'un objectif. */
export const councilPath = (goalId: string) => `/learn/goals/${goalId}/council`;

/**
 * Crée un objectif (`POST /goals`, qui lance le Conseil, D87) puis ouvre son Conseil. L'objectif
 * rendu amorce le cache : la page du Conseil s'ouvre sans attendre une seconde lecture.
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
