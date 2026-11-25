import { create } from "zustand";
import { onLocalReset } from "../lib/localReset";
import { applyEvent, applyLocal, initialSessionState } from "./sessionReducer";
import type { LocalAction, SessionEvent, SessionViewState } from "./types";

export interface SessionStoreState {
  sessions: Record<string, SessionViewState>;
  /** Applied events, per session: sorted by `seq`, no duplicates. */
  events: Record<string, SessionEvent[]>;
  ingest(sessionId: string, events: SessionEvent[]): void;
  local(sessionId: string, action: LocalAction): void;
  reset(sessionId: string): void;
}

type Stored = Pick<SessionStoreState, "sessions" | "events">;

/** Applies a sorted batch; keeps only the events the reducer accepted (new `seq`). */
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
 * Store factory: one session state per id, updated by the pure reducer.
 * One instance per test; the app shares `useSessionStore`.
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

/** Stable selector: the shared empty state while the session has received no event. */
export const selectSession =
  (sessionId: string) =>
  (store: Pick<SessionStoreState, "sessions">): SessionViewState =>
    store.sessions[sessionId] ?? initialSessionState;

const NO_EVENTS: SessionEvent[] = [];

/** Stable selector for a session's events (shared empty array if none). */
export const selectEvents =
  (sessionId: string) =>
  (store: Pick<SessionStoreState, "events">): SessionEvent[] =>
    store.events[sessionId] ?? NO_EVENTS;

// "Delete everything": no event of a session from the erased space stays in memory.
onLocalReset(() => useSessionStore.setState({ sessions: {}, events: {} }));
