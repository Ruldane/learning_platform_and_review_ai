import { useMutation, useQueryClient } from "@tanstack/react-query";
import { chooseExercise, hypothesesKey } from "../../api";

export function useCorrectiveExercise(id: string, restoreFocus: () => void) {
  const cache = useQueryClient();
  return useMutation({
    mutationFn: () => chooseExercise(id),
    onSuccess: async () => {
      restoreFocus();
      await cache.invalidateQueries({ queryKey: hypothesesKey });
    },
  });
}
