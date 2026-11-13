import { useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import type { SocketFactory } from "@/shared/realtime/socket";
import { useSessionActions } from "@/shared/realtime/useSessionActions";
import { useSessionStream } from "@/shared/realtime/useSessionStream";
import { replanKeys } from "../queryKeys";

const OVER = ["completed", "failed", "cancelled"] as const;

/**
 * Suit une session de replanification : le flux, les actions par REST, et les relectures qui vont
 * avec. L'historique du plan est relu à chaque `artifact.ready` (proposition prête) et à chaque
 * changement de statut ; à la fin de la session, le programme l'est aussi (nouvelle version).
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
