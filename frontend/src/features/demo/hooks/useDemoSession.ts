import { useState } from "react";
import type { SocketFactory } from "@/shared/realtime/socket";
import type { SessionStatus } from "@/shared/realtime/types";
import { useSessionActions } from "@/shared/realtime/useSessionActions";
import { useSessionStream } from "@/shared/realtime/useSessionStream";

const FINISHED: readonly SessionStatus[] = ["completed", "failed", "cancelled"];

/** Données et actions d'une session de démo, plus l'état de la confirmation d'annulation. */
export function useDemoSession(sessionId: string, createSocket?: SocketFactory) {
  const stream = useSessionStream(sessionId, { createSocket });
  const actions = useSessionActions(sessionId);
  const [confirmingCancel, setConfirmingCancel] = useState(false);

  const cancel = async () => {
    await actions.cancel();
    setConfirmingCancel(false);
  };
  return {
    stream,
    actions,
    finished: FINISHED.includes(stream.status),
    error: actions.error ?? stream.view.error?.message ?? null,
    confirmingCancel,
    setConfirmingCancel,
    cancel,
  };
}
