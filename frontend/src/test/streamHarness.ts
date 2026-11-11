import { vi } from "vitest";
import { createFakeSocketServer, type FakeSocketServer } from "@/test/fakeSocket";
import type { SessionView } from "@/shared/realtime/sessionApi";
import { SessionStreamConnection, type ConnectionState } from "@/shared/realtime/streamConnection";
import { tok } from "@/shared/realtime/testEvents";
import type { SessionEvent, SessionStatus } from "@/shared/realtime/types";

/** Matériel commun aux tests de `SessionStreamConnection`. */
export const sessionView = (status: SessionStatus, lastSeq: number): SessionView => ({
  id: "s1",
  graph: "demo",
  status,
  subject_type: null,
  subject_id: null,
  last_seq: lastSeq,
  pending_interrupt: null,
  error: null,
  cost_usd: 0,
  tokens_in: 0,
  tokens_out: 0,
  created_at: "2026-11-11T10:00:00Z",
  updated_at: "2026-11-11T10:00:00Z",
});

export interface Harness {
  fake: FakeSocketServer;
  connection: SessionStreamConnection;
  events: SessionEvent[];
  states: ConnectionState[];
  failures: (string | null)[];
  statuses: SessionStatus[];
  fetchSession: ReturnType<typeof vi.fn<(id: string) => Promise<SessionView>>>;
}

export function setup(
  fetchResult: () => Promise<SessionView> = async () => sessionView("running", 0),
) {
  const h = { events: [], states: [], failures: [], statuses: [] } as unknown as Harness;
  h.fake = createFakeSocketServer();
  h.fetchSession = vi.fn(fetchResult);
  h.connection = new SessionStreamConnection({
    sessionId: "s1",
    createSocket: h.fake.factory,
    fetchSession: h.fetchSession,
    lastSeq: () => h.events.at(-1)?.seq ?? 0,
    onEvent: (event) => h.events.push(event),
    onSnapshot: (view) => h.statuses.push(view.status),
    onState: (state, failure) => {
      h.states.push(state);
      h.failures.push(failure);
    },
  });
  h.connection.start();
  return h;
}

export const ev = (seq: number) => tok(seq, "m1", `t${seq}`);
export const lastState = (h: Harness) => h.states.at(-1);
