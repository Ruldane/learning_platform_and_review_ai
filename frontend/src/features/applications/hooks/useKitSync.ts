import { useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import { applicationsKeys } from "../queryKeys";

/** Relit le kit : la page ne se fie jamais aux seuls événements du flux (un `artifact.ready` peut se perdre). */
export function useKitSync(applicationId: string): () => void {
  const client = useQueryClient();
  return useCallback(
    () => void client.invalidateQueries({ queryKey: applicationsKeys.kit(applicationId) }),
    [client, applicationId],
  );
}
