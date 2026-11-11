import { create } from "zustand";
import { applyEvent, applyLocal, initialSessionState } from "./sessionReducer";
import type { LocalAction, SessionEvent, SessionViewState } from "./types";

export interface SessionStoreState {
  sessions: Record<string, SessionViewState>;
  ingest(sessionId: string, events: SessionEvent[]): void;
  local(sessionId: string, action: LocalAction): void;
  reset(sessionId: string): void;
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
      ingest: (sessionId, events) =>
        update(sessionId, (state) =>
          [...events].sort((a, b) => a.seq - b.seq).reduce(applyEvent, state),
        ),
      local: (sessionId, action) => update(sessionId, (state) => applyLocal(state, action)),
      reset: (sessionId) =>
        set((store) => {
          const sessions = { ...store.sessions };
          delete sessions[sessionId];
          return { sessions };
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
