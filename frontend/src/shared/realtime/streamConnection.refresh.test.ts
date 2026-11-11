import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/shared/api/errors";
import type { SessionView } from "./sessionApi";
import { lastState, sessionView, setup } from "@/test/streamHarness";

describe("SessionStreamConnection refresh queue (N2)", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("refresh() reads the session again, one request at a time", async () => {
    const answers: ((view: SessionView) => void)[] = [];
    const h = setup(() => new Promise((resolve) => answers.push(resolve)));
    h.fake.last().open(); // lecture d'ouverture en cours
    h.connection.refresh();
    h.connection.refresh();
    expect(h.fetchSession).toHaveBeenCalledTimes(1);
    answers[0]?.(sessionView("running", 2));
    await vi.advanceTimersByTimeAsync(0);
    // Les demandes faites pendant la lecture n'en font qu'une, lancée quand elle se termine (N2).
    expect(h.fetchSession).toHaveBeenCalledTimes(2);
    answers[1]?.(sessionView("running", 2));
    await vi.advanceTimersByTimeAsync(0);
    expect(h.fetchSession).toHaveBeenCalledTimes(2);
    h.connection.refresh();
    expect(h.fetchSession).toHaveBeenCalledTimes(3);
  });

  it("a refresh asked during a reconnect check is applied once the check settles", async () => {
    // Socket 1 tombe : la lecture de contrôle part (réponse retenue). Le minuteur rouvre le
    // socket 2 ; son ouverture demande une relecture, qui ne doit pas être perdue (N2).
    const answers: ((view: SessionView) => void)[] = [];
    const h = setup(() => new Promise((resolve) => answers.push(resolve)));
    h.fake.last().drop(1006);
    expect(h.fetchSession).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(500);
    h.fake.last().open();
    expect(h.fetchSession).toHaveBeenCalledTimes(1); // en attente derrière le contrôle
    answers[0]?.(sessionView("running", 0));
    await vi.advanceTimersByTimeAsync(0);
    expect(h.fetchSession).toHaveBeenCalledTimes(2);
    answers[1]?.(sessionView("running", 0));
    await vi.advanceTimersByTimeAsync(0);
    expect(h.statuses).toEqual(["running"]);
    expect(lastState(h)).toBe("open");
  });

  it("a refresh queued behind a failing check still runs", async () => {
    let fail: (error: unknown) => void = () => undefined;
    let calls = 0;
    const h = setup(() => {
      calls += 1;
      if (calls === 1) return new Promise((_, reject) => (fail = reject));
      return Promise.resolve(sessionView("paused", 3));
    });
    h.fake.last().drop(1006);
    await vi.advanceTimersByTimeAsync(500);
    h.fake.last().open(); // en attente derrière le contrôle encore en vol
    expect(h.fetchSession).toHaveBeenCalledTimes(1);
    fail(new ApiError({ code: "network_error", message: "Hors ligne", status: 0 }));
    await vi.advanceTimersByTimeAsync(0);
    expect(h.statuses).toEqual(["paused"]);
  });

  it("does not run a queued refresh after dispose or once the flux is over", async () => {
    let answer: (view: SessionView) => void = () => undefined;
    const h = setup(() => new Promise((resolve) => (answer = resolve)));
    h.fake.last().open(); // lecture d'ouverture en cours
    h.connection.refresh(); // mise en attente
    h.connection.dispose();
    answer(sessionView("running", 0));
    await vi.advanceTimersByTimeAsync(0);
    expect(h.fetchSession).toHaveBeenCalledTimes(1);
    expect(h.statuses).toEqual([]);
  });

  it("a late REST check does not close a live socket while the session is still running", async () => {
    let answer: (view: SessionView) => void = () => undefined;
    const h = setup(() => new Promise((resolve) => (answer = resolve)));
    h.fake.sockets[0]?.drop(1006); // contrôle en vol
    await vi.advanceTimersByTimeAsync(500);
    const live = h.fake.last().open();
    answer(sessionView("running", 0));
    await vi.advanceTimersByTimeAsync(0);
    expect(lastState(h)).toBe("open");
    expect(live.closedByClient).toBe(false);
    expect(h.fake.sockets).toHaveLength(2);
  });
});
