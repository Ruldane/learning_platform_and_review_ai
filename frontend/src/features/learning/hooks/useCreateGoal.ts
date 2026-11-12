import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { createGoal } from "../api";
import { learningKeys } from "../queryKeys";
import type { GoalInput } from "../types";

/** Chemin du Conseil d'un objectif. */
export const councilPath = (goalId: string) => `/apprendre/objectifs/${goalId}/conseil`;

/**
 * Crée un objectif (`POST /goals`, qui lance le Conseil, D87) puis ouvre son Conseil. L'objectif
 * rendu amorce le cache : la page du Conseil s'ouvre sans attendre une seconde lecture.
 */
export function useCreateGoal() {
  const client = useQueryClient();
  const navigate = useNavigate();
  const mutation = useMutation({
    mutationFn: (input: GoalInput) => createGoal(input),
    onSuccess: ({ goal }) => {
      client.setQueryData(learningKeys.goal(goal.id), goal);
      void client.invalidateQueries({ queryKey: learningKeys.goals });
      void navigate(councilPath(goal.id));
    },
  });
  return {
    create: mutation.mutate,
    pending: mutation.isPending,
    error: mutation.error ? errorMessage(mutation.error) : null,
  };
}
