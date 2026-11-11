import { reduceEvent } from "./eventHandlers";
import { answerInterrupts } from "./feedHelpers";
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
 * Pur et idempotent sur `seq` : un événement déjà appliqué (rejeu après reconnexion) renvoie le
 * même objet, sans rien dupliquer.
 */
export function applyEvent(state: SessionViewState, event: SessionEvent): SessionViewState {
  if (event.seq <= state.lastSeq) return state;
  return { ...reduceEvent(state, event), lastSeq: event.seq };
}

/** Actions locales du client (réponse envoyée, statut lu en REST : flux ou réponse d'action). */
export function applyLocal(state: SessionViewState, action: LocalAction): SessionViewState {
  if (action.type === "snapshot") return applySnapshot(state, action.snapshot);
  const known = state.feed.some(
    (i) => i.kind === "interrupt" && i.interrupt.interrupt_id === action.interruptId,
  );
  if (!known) return state;
  return { ...answerInterrupts(state, action.interruptId), status: "running" };
}
