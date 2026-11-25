import { useEffect, useRef } from "react";
import type { SocketFactory } from "@/shared/realtime/socket";
import { useSessionActions } from "@/shared/realtime/useSessionActions";
import { useSessionStream } from "@/shared/realtime/useSessionStream";

const OVER = ["completed", "failed", "cancelled", "expired"];

/**
 * Follows a CV run (profile reading, model capture, review): the stream, actions over
 * REST, and a callback on each state change or new question, so the page re-reads what the
 * session has just written. `createSocket` is only for tests.
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
