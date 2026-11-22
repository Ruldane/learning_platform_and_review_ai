import { useMutation, useQueryClient } from "@tanstack/react-query";
import { applyWeek } from "../../api";

export function useApplyWeek(id: string, restoreFocus: () => void) {
  const cache = useQueryClient();
  return useMutation({
    mutationFn: () => applyWeek(id),
    onSuccess: async () => {
      restoreFocus();
      await cache.invalidateQueries();
    },
  });
}
