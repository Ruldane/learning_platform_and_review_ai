import { useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import { applicationsKeys } from "../queryKeys";

/** Re-reads the kit: the page never relies only on stream events (an `artifact.ready` can be
 * lost). */
export function useKitSync(applicationId: string): () => void {
  const client = useQueryClient();
  return useCallback(
    () => void client.invalidateQueries({ queryKey: applicationsKeys.kit(applicationId) }),
    [client, applicationId],
  );
}
