import { create } from "zustand";
import { applyEvent, applyLocal, initialSessionState } from "./sessionReducer";
import type { LocalAction, SessionEvent, SessionViewState } from "./types";

export interface SessionStoreState {
  sessions: Record<string, SessionViewState>;
  /** Événements appliqués, par session : triés par `seq`, sans doublon. */
  events: Record<string, SessionEvent[]>;
  ingest(sessionId: string, events: SessionEvent[]): void;
  local(sessionId: string, action: LocalAction): void;
  reset(sessionId: string): void;
}

type Stored = Pick<SessionStoreState, "sessions" | "events">;

/** Applique un lot trié ; garde les seuls événements que le réducteur a acceptés (`seq` nouveau). */
function ingestBatch(store: Stored, sessionId: string, batch: SessionEvent[]): Stored | null {
  const current = store.sessions[sessionId] ?? initialSessionState;
  const accepted: SessionEvent[] = [];
  let state = current;
  for (const event of [...batch].sort((a, b) => a.seq - b.seq)) {
    const next = applyEvent(state, event);
    if (next !== state) accepted.push(event);
    state = next;
  }
  if (accepted.length === 0 && sessionId in store.sessions) return null;
  return {
    sessions: { ...store.sessions, [sessionId]: state },
    events: { ...store.events, [sessionId]: [...(store.events[sessionId] ?? []), ...accepted] },
  };
}

/**
 * Fabrique du store : un état de session par identifiant, mis à jour par le réducteur pur.
 * Une instance par test ; l'application partage `useSessionStore`.
 */
export function createSessionStore() {
  return create<SessionStoreState>()((set) => {
    const update = (sessionId: string, next: (s: SessionViewState) => SessionViewState) =>
      set((store) => {
        const current = store.sessions[sessionId] ?? initialSessionState;
        const updated = next(current);
        if (updated === current && sessionId in store.sessions) return store;
        return { sessions: { ...store.sessions, [sessionId]: updated } };
      });
    return {
      sessions: {},
      events: {},
      ingest: (sessionId, events) => set((store) => ingestBatch(store, sessionId, events) ?? store),
      local: (sessionId, action) => update(sessionId, (state) => applyLocal(state, action)),
      reset: (sessionId) =>
        set((store) => {
          const sessions = { ...store.sessions };
          const events = { ...store.events };
          delete sessions[sessionId];
          delete events[sessionId];
          return { sessions, events };
        }),
    };
  });
}

export const useSessionStore = createSessionStore();

/** Sélecteur stable : l'état vide partagé tant que la session n'a reçu aucun événement. */
export const selectSession =
  (sessionId: string) =>
  (store: Pick<SessionStoreState, "sessions">): SessionViewState =>
    store.sessions[sessionId] ?? initialSessionState;

const NO_EVENTS: SessionEvent[] = [];

/** Sélecteur stable des événements d'une session (tableau vide partagé si aucun). */
export const selectEvents =
  (sessionId: string) =>
  (store: Pick<SessionStoreState, "events">): SessionEvent[] =>
    store.events[sessionId] ?? NO_EVENTS;
