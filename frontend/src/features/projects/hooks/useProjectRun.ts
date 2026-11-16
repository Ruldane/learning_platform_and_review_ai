import { useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import type { SocketFactory } from "@/shared/realtime/socket";
import { useRun } from "@/shared/realtime/useRun";
import { projectKeys } from "../queryKeys";

/**
 * La session qui écrit l'énoncé ou évalue le rendu, suivie par `useRun` : le fil ne fait que dire
 * quand relire (chaque changement d'état de la session) ; le statut et les résultats viennent
 * toujours de la lecture du projet. `sessionId` à `null` : rien à suivre. `createSocket` ne sert
 * qu'aux tests.
 */
export function useProjectRun(
  projectId: string,
  sessionId: string | null,
  createSocket?: SocketFactory,
) {
  const client = useQueryClient();
  const sync = useCallback(() => {
    void client.invalidateQueries({ queryKey: projectKeys.one(projectId) });
  }, [client, projectId]);
  return useRun(sessionId, sync, createSocket);
}
