import { useMutation, useQueryClient } from "@tanstack/react-query";
import { evidenceKey, hypothesesKey, recordObservation } from "../../api";

export function useObservation() {
  const cache = useQueryClient();
  return useMutation({
    mutationFn: recordObservation,
    onSuccess: async () => {
      await cache.invalidateQueries({ queryKey: hypothesesKey });
    },
    onError: () => void cache.invalidateQueries({ queryKey: evidenceKey }),
  });
}
