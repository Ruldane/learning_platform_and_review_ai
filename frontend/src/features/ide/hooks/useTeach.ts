import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { RunSource } from "@/shared/lib/runSource";
import { teach } from "../api";
import { ideKeys } from "../queryKeys";
import type { TeachIn } from "../types";

/**
 * Wakes the teacher: one call per action, never on typing or saving. The
 * response says if a graph runs (`session_id`), if there is a reference, or why nothing is sent.
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
