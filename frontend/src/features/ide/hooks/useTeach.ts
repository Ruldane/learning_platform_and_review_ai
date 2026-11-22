import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { RunSource } from "@/shared/lib/runSource";
import { teach } from "../api";
import { ideKeys } from "../queryKeys";
import type { TeachIn } from "../types";

/**
 * Réveille le professeur : un appel par geste, jamais à la frappe ni à l'enregistrement. La
 * réponse dit si un graphe travaille (`session_id`), s'il y a un renvoi, ou pourquoi rien ne part.
 */
export function useTeach(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ source, ...body }: TeachIn & { source?: RunSource }) =>
      teach(sessionId, body, source),
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: ideKeys.notes(sessionId) });
      return queryClient.invalidateQueries({ queryKey: ideKeys.usage(sessionId) });
    },
  });
}
