import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/shared/api/errors";
import { createFakeSocketServer, type FakeSocketServer } from "@/test/fakeSocket";
import type { SessionView } from "./sessionApi";
import { MAX_RECONNECT_ATTEMPTS, reconnectDelay } from "./socket";
import { SessionStreamConnection, type ConnectionState } from "./streamConnection";
import { tok } from "./testEvents";
import type { SessionEvent, SessionStatus } from "./types";

const sessionView = (status: SessionStatus, lastSeq: number): SessionView => ({
  id: "s1",
  graph: "demo",
  status,
  last_seq: lastSeq,
  pending_interrupt: null,
  error: null,
  cost_usd: 0,
  tokens_in: 0,
  tokens_out: 0,
  created_at: "2026-11-11T10:00:00Z",
  updated_at: "2026-11-11T10:00:00Z",
});

interface Harness {
  fake: FakeSocketServer;
  connection: SessionStreamConnection;
  events: SessionEvent[];
  states: ConnectionState[];
  failures: (string | null)[];
  statuses: SessionStatus[];
  fetchSession: ReturnType<typeof vi.fn<(id: string) => Promise<SessionView>>>;
}

function setup(fetchResult: () => Promise<SessionView> = async () => sessionView("running", 0)) {
  const h = { events: [], states: [], failures: [], statuses: [] } as unknown as Harness;
  h.fake = createFakeSocketServer();
  h.fetchSession = vi.fn(fetchResult);
  h.connection = new SessionStreamConnection({
    sessionId: "s1",
    createSocket: h.fake.factory,
    fetchSession: h.fetchSession,
    lastSeq: () => h.events.at(-1)?.seq ?? 0,
    onEvent: (event) => h.events.push(event),
    onStatus: (status) => h.statuses.push(status),
    onState: (state, failure) => {
      h.states.push(state);
      h.failures.push(failure);
    },
  });
  h.connection.start();
  return h;
}

const ev = (seq: number) => tok(seq, "m1", `t${seq}`);
const lastState = (h: Harness) => h.states.at(-1);

describe("SessionStreamConnection", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("opens the stream after the last applied seq", () => {
    const h = setup();
    expect(h.fake.last().url).toMatch(/\/api\/v1\/sessions\/s1\/stream\?after_seq=0$/);
    h.fake.last().open().push(ev(1), ev(2));
    expect(lastState(h)).toBe("open");
    expect(h.events.map((e) => e.seq)).toEqual([1, 2]);
  });

  it("backs off on 1006 and gives up after the maximum number of attempts", async () => {
    const h = setup();
    for (let attempt = 1; attempt <= MAX_RECONNECT_ATTEMPTS; attempt += 1) {
      h.fake.last().drop(1006);
      expect(lastState(h)).toBe("reconnecting");
      await vi.advanceTimersByTimeAsync(reconnectDelay(attempt) - 1);
      expect(h.fake.sockets).toHaveLength(attempt);
      await vi.advanceTimersByTimeAsync(1);
      expect(h.fake.sockets).toHaveLength(attempt + 1);
    }
    h.fake.last().drop(1006);
    expect(lastState(h)).toBe("failed");
    expect(h.failures.at(-1)).toBe("unreachable");
    await vi.advanceTimersByTimeAsync(60_000);
    expect(h.fake.sockets).toHaveLength(MAX_RECONNECT_ATTEMPTS + 1);
  });

  it("uses the documented delays", () => {
    expect([1, 2, 3, 4, 5, 6, 9].map(reconnectDelay)).toEqual([
      500, 1000, 2000, 4000, 8000, 10_000, 10_000,
    ]);
  });

  it("resets the attempts once a reconnected socket receives data", async () => {
    const h = setup();
    h.fake.last().drop(1006);
    await vi.advanceTimersByTimeAsync(500);
    h.fake.last().drop(1006);
    await vi.advanceTimersByTimeAsync(1000);
    h.fake.last().open().push(ev(1));
    h.fake.last().drop(1006);
    await vi.advanceTimersByTimeAsync(500);
    expect(h.fake.sockets).toHaveLength(4);
    expect(h.fake.last().url).toContain("after_seq=1");
  });

  it("does not reset the attempts on an open without data", async () => {
    const h = setup();
    h.fake.last().drop(1006);
    await vi.advanceTimersByTimeAsync(500);
    h.fake.last().open().drop(1006);
    await vi.advanceTimersByTimeAsync(500);
    expect(h.fake.sockets).toHaveLength(2);
    await vi.advanceTimersByTimeAsync(500);
    expect(h.fake.sockets).toHaveLength(3);
  });

  it("treats 1000 as final and reads the final status over REST", async () => {
    const h = setup(async () => sessionView("cancelled", 0));
    h.fake.last().open().drop(1000);
    expect(lastState(h)).toBe("closed");
    await vi.advanceTimersByTimeAsync(60_000);
    expect(h.fake.sockets).toHaveLength(1);
    expect(h.statuses).toEqual(["cancelled"]);
  });

  it.each([
    [4404, "not_found"],
    [1008, "refused"],
  ])("stops without reconnecting on %i", async (code, failure) => {
    const h = setup();
    h.fake.last().drop(code);
    expect(lastState(h)).toBe("failed");
    expect(h.failures.at(-1)).toBe(failure);
    await vi.advanceTimersByTimeAsync(60_000);
    expect(h.fake.sockets).toHaveLength(1);
  });

  it("stops when REST says the session is finished and fully received", async () => {
    const h = setup(async () => sessionView("completed", 2));
    h.fake.last().open().push(ev(1), ev(2)).drop(1006);
    await vi.advanceTimersByTimeAsync(0);
    expect(lastState(h)).toBe("closed");
    expect(h.statuses).toEqual(["completed"]);
    await vi.advanceTimersByTimeAsync(60_000);
    expect(h.fake.sockets).toHaveLength(1);
  });

  it("still reconnects when a finished session has events not received yet", async () => {
    const h = setup(async () => sessionView("completed", 5));
    h.fake.last().open().push(ev(1), ev(2)).drop(1006);
    await vi.advanceTimersByTimeAsync(500);
    expect(h.fake.sockets).toHaveLength(2);
    expect(h.fake.last().url).toContain("after_seq=2");
    expect(h.statuses).toEqual([]);
  });

  it("stops on a REST 404 and keeps retrying on a network error", async () => {
    const missing = setup(async () => {
      throw new ApiError({
        code: "session_not_found",
        message: "Session introuvable.",
        status: 404,
      });
    });
    missing.fake.last().drop(1006);
    await vi.advanceTimersByTimeAsync(0);
    expect(lastState(missing)).toBe("failed");
    expect(missing.failures.at(-1)).toBe("not_found");

    const offline = setup(async () => {
      throw new ApiError({ code: "network_error", message: "Hors ligne", status: 0 });
    });
    offline.fake.last().drop(1006);
    await vi.advanceTimersByTimeAsync(500);
    expect(offline.fake.sockets).toHaveLength(2);
  });

  it("ignores frames that are not session events", () => {
    const h = setup();
    h.fake.last().open().pushRaw("pas du json").pushRaw('{"type":"x"}').pushRaw("null");
    expect(h.events).toEqual([]);
  });

  it("dispose closes the socket, cancels the pending reconnect and silences callbacks", async () => {
    let answer: (view: SessionView) => void = () => undefined;
    const h = setup(() => new Promise((resolve) => (answer = resolve)));
    h.fake.last().open().drop(1006);
    const statesBefore = h.states.length;
    h.connection.dispose();
    answer(sessionView("completed", 0));
    await vi.advanceTimersByTimeAsync(60_000);
    expect(h.fake.sockets).toHaveLength(1);
    expect(h.states).toHaveLength(statesBefore);
    expect(h.statuses).toEqual([]);

    const live = setup();
    const socket = live.fake.last().open();
    live.connection.dispose();
    expect(socket.closedByClient).toBe(true);
    expect(socket.onclose).toBeNull();
  });
});
