import { useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { useSessionActions } from "@/shared/realtime/useSessionActions";
import { useSessionStream } from "@/shared/realtime/useSessionStream";
import type { SocketFactory } from "@/shared/realtime/socket";
import { captureKeys } from "../queryKeys";

const OVER = ["completed", "failed", "cancelled", "expired"] as const;

/**
 * Follows the Archivist session of a capture: the stream, and the REST actions (answers to the
 * questions). At the end of the session, the journal is re-read: the capture wrote its line there.
 */
export function useCaptureRun(sessionId: string, createSocket?: SocketFactory) {
  const client = useQueryClient();
  const stream = useSessionStream(sessionId, { createSocket });
  const actions = useSessionActions(sessionId);
  const over = (OVER as readonly string[]).includes(stream.status);

  useEffect(() => {
    if (over) void client.invalidateQueries({ queryKey: captureKeys.journals });
  }, [client, over]);

  return { stream, actions, over };
}

export type CaptureRun = ReturnType<typeof useCaptureRun>;
