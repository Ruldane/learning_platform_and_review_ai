import { act, renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { StrictMode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiBaseUrl } from "@/shared/api/client";
import { fr } from "@/shared/i18n/fr";
import { createFakeSocketServer } from "@/test/fakeSocket";
import { server } from "@/test/server";
import type { SessionView } from "./sessionApi";
import { useSessionStore } from "./sessionStore";
import { completed, interrupt, started, tok, turn } from "./testEvents";
import { useSessionStream } from "./useSessionStream";

const at = "2026-11-11T10:00:00Z";
const viewOf = (status: SessionView["status"], lastSeq = 0, updatedAt = at) =>
  ({ status, last_seq: lastSeq, updated_at: updatedAt, pending_interrupt: null }) as SessionView;
const runningView = viewOf("running");
const fetchRunning = async () => runningView;
const ev = (seq: number) => tok(seq, "m1", `t${seq}`);

describe("useSessionStream", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    useSessionStore.getState().reset("s1");
  });
  afterEach(() => {
    vi.useRealTimers();
    useSessionStore.getState().reset("s1");
  });

  it("reconnect resumes after last seq without duplicates", async () => {
    // test_reconnect_resumes_after_last_seq_without_duplicates (Review Focus 2)
    const fake = createFakeSocketServer();
    const { result } = renderHook(() =>
      useSessionStream("s1", { createSocket: fake.factory, fetchSession: fetchRunning }),
    );
    act(() => {
      fake.last().open().push(ev(1), ev(2)).drop(1006);
    });
    expect(result.current.connection).toBe("reconnecting");
    await act(() => vi.advanceTimersByTimeAsync(500));
    expect(fake.last().url).toContain("after_seq=2");
    act(() => {
      fake.last().open().push(ev(2), ev(3));
    });
    expect(result.current.events.map((e) => e.seq)).toEqual([1, 2, 3]);
    expect(turn(result.current.view, "m1")?.text).toBe("t1t2t3");
    expect(result.current.connection).toBe("open");
  });

  it("starts after the seq already in the store", () => {
    useSessionStore.getState().ingest("s1", [ev(1), ev(2), ev(3)]);
    const fake = createFakeSocketServer();
    renderHook(() =>
      useSessionStream("s1", { createSocket: fake.factory, fetchSession: fetchRunning }),
    );
    expect(fake.last().url).toContain("after_seq=3");
  });

  it("exposes status and pending interrupt from the store", () => {
    const fake = createFakeSocketServer();
    const { result } = renderHook(() =>
      useSessionStream("s1", { createSocket: fake.factory, fetchSession: fetchRunning }),
    );
    act(() => {
      fake.last().open().push(interrupt(1, "i1"));
    });
    expect(result.current.status).toBe("waiting_user");
    expect(result.current.pendingInterrupt?.interrupt_id).toBe("i1");
  });

  it("stops after 1000 and does not reconnect", async () => {
    const fake = createFakeSocketServer();
    const { result } = renderHook(() =>
      useSessionStream("s1", {
        createSocket: fake.factory,
        fetchSession: async () => viewOf("completed", 1),
      }),
    );
    act(() => {
      fake.last().open().push(completed(1)).drop(1000);
    });
    expect(result.current.connection).toBe("closed");
    await act(() => vi.advanceTimersByTimeAsync(60_000));
    expect(fake.sockets).toHaveLength(1);
    expect(result.current.status).toBe("completed");
  });

  it("exposes a French error after giving up, and retry reconnects", async () => {
    const fake = createFakeSocketServer();
    const { result } = renderHook(() =>
      useSessionStream("s1", { createSocket: fake.factory, fetchSession: fetchRunning }),
    );
    act(() => {
      fake.last().drop(4404);
    });
    expect(result.current.connection).toBe("failed");
    expect(result.current.error).toBe(fr.sessions.stream.not_found);
    act(() => result.current.retry());
    expect(fake.sockets).toHaveLength(2);
    expect(result.current.connection).toBe("connecting");
    expect(result.current.error).toBeNull();
  });

  it("closes the socket and cancels the reconnect on unmount", async () => {
    const fake = createFakeSocketServer();
    const { unmount } = renderHook(() =>
      useSessionStream("s1", { createSocket: fake.factory, fetchSession: fetchRunning }),
    );
    act(() => {
      fake.last().open().drop(1006);
    });
    await act(() => vi.advanceTimersByTimeAsync(500));
    const reconnected = fake.last();
    act(() => {
      reconnected.open().drop(1006);
    });
    unmount();
    await act(() => vi.advanceTimersByTimeAsync(60_000));
    expect(fake.sockets).toHaveLength(2);

    const other = createFakeSocketServer();
    const second = renderHook(() =>
      useSessionStream("s1", { createSocket: other.factory, fetchSession: fetchRunning }),
    );
    const socket = other.last().open();
    second.unmount();
    expect(socket.closedByClient).toBe(true);
  });

  it("keeps a single live socket under StrictMode", async () => {
    const fake = createFakeSocketServer();
    const { result, unmount } = renderHook(
      () => useSessionStream("s1", { createSocket: fake.factory, fetchSession: fetchRunning }),
      { wrapper: StrictMode },
    );
    const live = fake.sockets.filter((s) => !s.closedByClient);
    expect(live).toHaveLength(1);
    // Le socket du premier montage est débranché : sa fermeture tardive ne relance rien.
    fake.sockets.filter((s) => s.closedByClient).forEach((s) => s.drop(1006));
    await act(() => vi.advanceTimersByTimeAsync(60_000));
    expect(fake.sockets.filter((s) => !s.closedByClient)).toHaveLength(1);
    act(() => {
      live[0]?.open().push(ev(1), ev(2));
    });
    expect(result.current.events.map((e) => e.seq)).toEqual([1, 2]);
    unmount();
    expect(fake.sockets.every((s) => s.closedByClient)).toBe(true);
  });

  it("applies the status read over REST when the stream opens (reload of a paused session)", async () => {
    const fake = createFakeSocketServer();
    const { result } = renderHook(() =>
      useSessionStream("s1", {
        createSocket: fake.factory,
        fetchSession: async () => viewOf("paused", 2),
      }),
    );
    await act(async () => {
      fake.last().open().push(started(1, "demo_critic"), ev(2));
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(result.current.status).toBe("paused");
  });

  it("re-reads the session when a newer event arrives while paused", async () => {
    const fake = createFakeSocketServer();
    const views = [viewOf("paused", 1), viewOf("running", 2, "2026-11-11T10:00:09Z")];
    const fetchSession = vi.fn(async () => views.shift() ?? viewOf("running", 2));
    const { result } = renderHook(() =>
      useSessionStream("s1", { createSocket: fake.factory, fetchSession }),
    );
    await act(async () => {
      fake.last().open().push(started(1, "demo_critic"));
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(result.current.status).toBe("paused");
    // Repris ailleurs (autre onglet) : l'événement ne lève pas la pause, mais la fait relire.
    await act(async () => {
      fake.last().push(started(2, "demo_critic"));
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(fetchSession).toHaveBeenCalledTimes(2);
    expect(result.current.status).toBe("running");
  });

  it("exposes why the stream gave up", () => {
    const fake = createFakeSocketServer();
    const { result } = renderHook(() =>
      useSessionStream("s1", { createSocket: fake.factory, fetchSession: fetchRunning }),
    );
    act(() => {
      fake.last().drop(4404);
    });
    expect(result.current.failure).toBe("not_found");
  });

  it("opens nothing without a session id", () => {
    const fake = createFakeSocketServer();
    const { result } = renderHook(() => useSessionStream(null, { createSocket: fake.factory }));
    expect(fake.sockets).toHaveLength(0);
    expect(result.current.connection).toBe("closed");
    expect(result.current.events).toEqual([]);
  });
});

describe("useSessionStream with the REST client", () => {
  afterEach(() => useSessionStore.getState().reset("s1"));

  it("reads the final status of a cancelled session over REST after 1000", async () => {
    server.use(
      http.get(`${apiBaseUrl}/api/v1/sessions/:id`, () =>
        HttpResponse.json({ ...runningView, id: "s1", status: "cancelled" }),
      ),
    );
    const fake = createFakeSocketServer();
    const { result } = renderHook(() => useSessionStream("s1", { createSocket: fake.factory }));
    act(() => {
      fake.last().open().drop(1000);
    });
    await waitFor(() => expect(result.current.status).toBe("cancelled"));
  });
});
