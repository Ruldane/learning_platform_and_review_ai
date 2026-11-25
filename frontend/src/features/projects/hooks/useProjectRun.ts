import { useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import type { SocketFactory } from "@/shared/realtime/socket";
import { useRun } from "@/shared/realtime/useRun";
import { projectKeys } from "../queryKeys";

/**
 * The session writing the brief or evaluating the submission, followed by `useRun`: the thread only
 * says when to re-read (each session state change); the status and results always come from
 * reading the project. `sessionId` at `null`: nothing to follow. `createSocket` serves only
 * for the tests.
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
