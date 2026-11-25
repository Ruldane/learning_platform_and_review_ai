import { useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import type { SocketFactory } from "@/shared/realtime/socket";
import { useSessionActions } from "@/shared/realtime/useSessionActions";
import { useSessionStream } from "@/shared/realtime/useSessionStream";
import { replanKeys } from "../queryKeys";

const OVER = ["completed", "failed", "cancelled", "expired"] as const;

/**
 * Follows a replan session: the stream, the actions over REST, and the re-reads that go
 * with them. The plan's history is re-read on each `artifact.ready` (proposal ready) and on each
 * status change; at the end of the session, the program is re-read too (new version).
 */
export function useReplanRun(sessionId: string, programId: string, createSocket?: SocketFactory) {
  const client = useQueryClient();
  const stream = useSessionStream(sessionId, { createSocket });
  const actions = useSessionActions(sessionId);
  const proposals = stream.events.filter((event) => event.type === "artifact.ready").length;
  const over = (OVER as readonly string[]).includes(stream.status);

  useEffect(() => {
    void client.invalidateQueries({ queryKey: replanKeys.versions(programId) });
  }, [client, programId, proposals, stream.status]);

  useEffect(() => {
    if (!over) return;
    void client.invalidateQueries({ queryKey: replanKeys.programDetail(programId) });
    void client.invalidateQueries({ queryKey: replanKeys.waiting(programId) });
  }, [client, programId, over]);

  return { stream, actions, over };
}

export type ReplanRun = ReturnType<typeof useReplanRun>;
