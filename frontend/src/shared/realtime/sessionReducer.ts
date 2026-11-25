import { reduceEvent } from "./eventHandlers";
import { answerInterrupts, stopStreaming } from "./feedHelpers";
import { applySnapshot } from "./statusGate";
import type { LocalAction, SessionEvent, SessionViewState } from "./types";

export const initialSessionState: SessionViewState = {
  lastSeq: 0,
  status: "running",
  statusVersion: { seq: 0, at: 0 },
  feed: [],
  pendingInterrupt: null,
  cost: null,
  error: null,
  currentAgent: null,
};

/**
 * Pure and idempotent on `seq`: an event already applied (replay after reconnect) returns the
 * same object, without duplicating anything.
 */
export function applyEvent(state: SessionViewState, event: SessionEvent): SessionViewState {
  if (event.seq <= state.lastSeq) return state;
  const next = reduceEvent(state, event);
  // Only a running session writes: a token replayed after a pause, or a cancellation read over
  // REST, does not turn « Écrit… » back on.
  const feed = next.status === "running" ? next.feed : stopStreaming(next.feed);
  return { ...next, feed, lastSeq: event.seq };
}

/** Local client actions (answer sent, status read over REST: stream or action response). */
export function applyLocal(state: SessionViewState, action: LocalAction): SessionViewState {
  if (action.type === "snapshot") return applySnapshot(state, action.snapshot);
  const known = state.feed.some(
    (i) => i.kind === "interrupt" && i.interrupt.interrupt_id === action.interruptId,
  );
  if (!known) return state;
  return { ...answerInterrupts(state, action.interruptId), status: "running" };
}
