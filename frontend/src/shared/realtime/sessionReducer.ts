import { reduceEvent } from "./eventHandlers";
import { answerInterrupts } from "./feedHelpers";
import type { LocalAction, SessionEvent, SessionViewState } from "./types";

export const initialSessionState: SessionViewState = {
  lastSeq: 0,
  status: "running",
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

/** Actions locales du client (réponse envoyée, statut posé par une réponse REST). */
export function applyLocal(state: SessionViewState, action: LocalAction): SessionViewState {
  if (action.type === "status.set") {
    return action.status === state.status ? state : { ...state, status: action.status };
  }
  const known = state.feed.some(
    (i) => i.kind === "interrupt" && i.interrupt.interrupt_id === action.interruptId,
  );
  if (!known) return state;
  return { ...answerInterrupts(state, action.interruptId), status: "running" };
}
