import { useEffect, useRef } from "react";
import type { SocketFactory } from "@/shared/realtime/socket";
import { useSessionActions } from "@/shared/realtime/useSessionActions";
import { useSessionStream } from "@/shared/realtime/useSessionStream";

const OVER = ["completed", "failed", "cancelled"];

/**
 * Suit la session d'un parcours du CV (lecture du profil, capture d'un modèle, revue) : le flux, les
 * actions par REST, et un rappel à chaque changement d'état ou nouvelle question, pour que la page
 * relise ce que la session vient d'écrire. `createSocket` ne sert qu'aux tests.
 */
export function useRun(
  sessionId: string | null,
  onChange: () => void,
  createSocket?: SocketFactory,
) {
  const stream = useSessionStream(sessionId, { createSocket });
  const actions = useSessionActions(sessionId ?? "");
  const notify = useRef(onChange);
  useEffect(() => {
    notify.current = onChange;
  });
  const questionId = stream.pendingInterrupt?.interrupt_id ?? null;
  useEffect(() => {
    if (sessionId) notify.current();
  }, [sessionId, stream.status, questionId]);
  return { stream, actions, over: OVER.includes(stream.status) };
}

export type Run = ReturnType<typeof useRun>;
