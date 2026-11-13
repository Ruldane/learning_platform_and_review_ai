import { useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { useSessionActions } from "@/shared/realtime/useSessionActions";
import { useSessionStream } from "@/shared/realtime/useSessionStream";
import type { SocketFactory } from "@/shared/realtime/socket";
import { captureKeys } from "../queryKeys";

const OVER = ["completed", "failed", "cancelled"] as const;

/**
 * Suit la session de l'Archiviste d'une capture : le flux, les actions par REST (la réponse aux
 * questions). À la fin de la session, le journal est relu : la capture y a écrit sa ligne.
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
