import { describe, expect, it } from "vitest";
import { applyEvent, applyLocal, initialSessionState } from "./sessionReducer";
import type { FeedItem, SessionEvent, SessionViewState, StatusSnapshot } from "./types";
import { completed, interrupt, message, snapshot, started, tok, turn, userMsg } from "./testEvents";

const run = (events: SessionEvent[], from: SessionViewState = initialSessionState) =>
  events.reduce(applyEvent, from);
const snap = (state: SessionViewState, value: StatusSnapshot) =>
  applyLocal(state, { type: "snapshot", snapshot: value });
const interrupts = (feed: FeedItem[]) => feed.filter((i) => i.kind === "interrupt");
const question = (id: string) => interrupt(0, id).payload;

describe("user.message (D4 : un message n'est pas une réponse)", () => {
  it("keeps the pending question open and the status waiting_user", () => {
    const s = run([
      started(1, "demo_critic"),
      interrupt(2, "i1"),
      userMsg(3, "Pense aux débutants"),
    ]);
    expect(s.status).toBe("waiting_user");
    expect(s.pendingInterrupt?.interrupt_id).toBe("i1");
    expect(s.feed[1]).toMatchObject({ kind: "interrupt", answered: false });
    expect(s.feed[2]).toEqual({ kind: "user", seq: 3, text: "Pense aux débutants", command: null });
  });
});

describe("snapshot REST : le statut du serveur fait foi", () => {
  it("a reload of a paused session shows paused once the replay is applied", () => {
    // Rejeu reçu avant la réponse REST : les événements disent « running ».
    let s = run([started(1, "demo_proponent"), tok(2, "m1", "Oui")]);
    s = snap(s, snapshot("paused", 2));
    expect(s.status).toBe("paused");
    // Réponse REST d'abord, rejeu ensuite : les événements déjà couverts ne la défont pas.
    const fresh = run(
      [started(1, "demo_proponent"), tok(2, "m1", "Oui")],
      snap(initialSessionState, snapshot("paused", 2)),
    );
    expect(fresh.status).toBe("paused");
  });

  it("a session paused while waiting keeps its question card but no pending answer", () => {
    const s = run(
      [started(1, "demo_critic"), interrupt(2, "i1")],
      snap(initialSessionState, snapshot("paused", 2)),
    );
    expect(s.status).toBe("paused");
    expect(s.pendingInterrupt).toBeNull();
    expect(interrupts(s.feed)).toHaveLength(1);
  });

  it("a late agent.started never lifts a pause or a cancellation", () => {
    for (const status of ["paused", "cancelled"] as const) {
      const s = applyEvent(
        snap(run([started(1, "demo_critic")]), snapshot(status, 1)),
        started(2, "demo_critic"),
      );
      expect(s.status).toBe(status);
    }
  });

  it("a late interrupt.requested does not lift a pause either", () => {
    const s = applyEvent(
      snap(run([started(1, "demo_critic")]), snapshot("paused", 1)),
      interrupt(2, "i1"),
    );
    expect(s).toMatchObject({ status: "paused", pendingInterrupt: null });
  });

  it("run.* is final and always applies", () => {
    const s = applyEvent(snap(initialSessionState, snapshot("paused", 0)), completed(1));
    expect(s.status).toBe("completed");
  });

  it("events newer than the snapshot change the status again", () => {
    const s = run([interrupt(4, "i2")], snap(initialSessionState, snapshot("running", 3)));
    expect(s).toMatchObject({ status: "waiting_user", pendingInterrupt: { interrupt_id: "i2" } });
  });

  it("ignores a snapshot older than the events already applied", () => {
    const s = run([started(1, "demo_critic"), interrupt(2, "i2")]);
    expect(snap(s, snapshot("running", 1))).toBe(s);
  });

  it("two snapshots of the same seq: the later server write wins", () => {
    const paused = snap(initialSessionState, snapshot("paused", 5, "2026-11-11T10:00:01.000200Z"));
    const stale = snap(paused, snapshot("running", 5, "2026-11-11T10:00:01.000100Z"));
    expect(stale.status).toBe("paused");
    const later = snap(paused, snapshot("running", 5, "2026-11-11T10:00:02Z"));
    expect(later.status).toBe("running");
  });

  it("a pause response is applied even after a late agent.started of the stopped task", () => {
    // L'événement en vol (seq 3) arrive avant la réponse REST de la pause (lue à seq 2).
    const s = snap(
      run([started(1, "demo_critic"), tok(2, "m1", "Mi"), started(3, "demo_critic")]),
      snapshot("paused", 2),
    );
    expect(s.status).toBe("paused");
  });

  it("a snapshot equal to the current one changes nothing (same object)", () => {
    const once = snap(initialSessionState, snapshot("paused", 3));
    expect(snap(once, snapshot("paused", 3))).toBe(once);
  });

  it("adds the pending question when its event is missing, then the event replaces it", () => {
    let s = snap(
      run([started(1, "demo_critic")]),
      snapshot("waiting_user", 1, undefined, question("i1")),
    );
    expect(s.pendingInterrupt?.interrupt_id).toBe("i1");
    expect(interrupts(s.feed)).toEqual([
      { kind: "interrupt", seq: 1, interrupt: question("i1"), answered: false },
    ]);
    s = applyEvent(s, interrupt(2, "i1"));
    expect(interrupts(s.feed)).toHaveLength(1);
    expect(s.pendingInterrupt?.interrupt_id).toBe("i1");
  });

  it("a question asked again after a pause replaces its old card", () => {
    let s = run([started(1, "demo_critic"), interrupt(2, "i1")]);
    s = snap(s, snapshot("paused", 2));
    s = snap(s, snapshot("running", 2, "2026-11-11T10:00:05Z"));
    s = applyEvent(s, interrupt(3, "i1"));
    expect(interrupts(s.feed)).toEqual([
      { kind: "interrupt", seq: 3, interrupt: interrupt(3, "i1").payload, answered: false },
    ]);
    expect(s.status).toBe("waiting_user");
  });

  it("a non-running snapshot stops the streaming bubbles", () => {
    const s = snap(run([started(1, "demo_critic"), tok(2, "m1", "Mi")]), snapshot("paused", 2));
    expect(turn(s, "m1")).toMatchObject({ streaming: false, interrupted: true });
    expect(s.currentAgent).toBeNull();
  });

  it("agent.started only answers the questions asked before it", () => {
    const s = run(
      [started(1, "demo_critic"), interrupt(2, "i1"), started(3, "demo_critic")],
      snap(initialSessionState, snapshot("waiting_user", 4, undefined, question("i2"))),
    );
    expect(
      s.feed.find((i) => i.kind === "interrupt" && i.interrupt.interrupt_id === "i1"),
    ).toMatchObject({
      answered: true,
    });
    expect(
      s.feed.find((i) => i.kind === "interrupt" && i.interrupt.interrupt_id === "i2"),
    ).toMatchObject({
      answered: false,
    });
    expect(s).toMatchObject({ status: "waiting_user", pendingInterrupt: { interrupt_id: "i2" } });
  });
});

describe("seul un statut running garde une bulle « Écrit… »", () => {
  it("a session paused by a REST read stays quiet when replayed tokens follow", () => {
    const s = run(
      [started(1, "demo_critic"), tok(2, "m1", "Moi"), tok(3, "m1", "tié")],
      snap(initialSessionState, snapshot("paused", 1)),
    );
    expect(s.status).toBe("paused");
    expect(turn(s, "m1")).toMatchObject({ text: "Moitié", streaming: false, interrupted: true });
  });

  it("a cancelled session (REST first, then replay) shows no streaming bubble", () => {
    const s = run(
      [started(1, "demo_critic"), tok(2, "m1", "Moi")],
      snap(initialSessionState, snapshot("cancelled", 2)),
    );
    expect(s.feed.some((i) => i.kind === "turn" && i.streaming)).toBe(false);
  });

  it("a late token after the pause response does not bring the bubble back", () => {
    const paused = snap(
      run([started(1, "demo_critic"), tok(2, "m1", "Moi")]),
      snapshot("paused", 2),
    );
    const s = applyEvent(paused, tok(3, "m1", "tié"));
    expect(turn(s, "m1")).toMatchObject({ streaming: false, interrupted: true });
  });

  it("stays idempotent on seq and a final message still completes the turn", () => {
    const paused = snap(run([started(1, "demo_critic")]), snapshot("paused", 1));
    const s1 = applyEvent(paused, tok(2, "m1", "Moi"));
    expect(applyEvent(s1, tok(2, "m1", "Moi"))).toBe(s1);
    const done = applyEvent(s1, message(3, "m1", "Moitié."));
    expect(turn(done, "m1")).toMatchObject({
      text: "Moitié.",
      streaming: false,
      interrupted: false,
    });
  });

  it("keeps streaming while the session runs", () => {
    const s = run([started(1, "demo_critic"), tok(2, "m1", "Moi")]);
    expect(turn(s, "m1")).toMatchObject({ streaming: true });
  });
});
