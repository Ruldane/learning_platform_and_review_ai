import { describe, expect, it } from "vitest";
import { createSessionStore, selectSession } from "./sessionStore";
import { initialSessionState } from "./sessionReducer";
import { interrupt, started, tok, turn } from "./testEvents";

describe("session store", () => {
  it("keeps one independent state per session id", () => {
    const store = createSessionStore();
    store.getState().ingest("a", [started(1, "demo_critic"), tok(2, "m1", "Bon")]);
    store.getState().ingest("b", [tok(1, "m2", "Salut")]);
    const read = (id: string) => selectSession(id)(store.getState());
    expect(turn(read("a"), "m1")?.text).toBe("Bon");
    expect(turn(read("b"), "m2")?.text).toBe("Salut");
    expect(turn(read("b"), "m1")).toBeUndefined();
  });

  it("is idempotent when a batch is replayed after reconnection", () => {
    const store = createSessionStore();
    const batch = [started(1, "demo_critic"), tok(2, "m1", "Bon")];
    store.getState().ingest("a", batch);
    const before = selectSession("a")(store.getState());
    store.getState().ingest("a", batch);
    expect(selectSession("a")(store.getState())).toBe(before);
  });

  it("applies an out-of-order batch in seq order", () => {
    const store = createSessionStore();
    store.getState().ingest("a", [tok(3, "m1", "jour"), tok(2, "m1", "Bon")]);
    expect(turn(selectSession("a")(store.getState()), "m1")?.text).toBe("Bonjour");
  });

  it("applies local actions to one session only", () => {
    const store = createSessionStore();
    store.getState().ingest("a", [interrupt(1)]);
    store.getState().ingest("b", [interrupt(1)]);
    store.getState().local("a", { type: "interrupt.answered", interruptId: "i1" });
    expect(selectSession("a")(store.getState()).pendingInterrupt).toBeNull();
    expect(selectSession("b")(store.getState()).pendingInterrupt).not.toBeNull();
  });

  it("reset forgets a session", () => {
    const store = createSessionStore();
    store.getState().ingest("a", [started(1, "demo_critic")]);
    store.getState().reset("a");
    expect(store.getState().sessions).not.toHaveProperty("a");
  });

  it("selectSession returns the shared empty state for an unknown session", () => {
    const store = createSessionStore();
    expect(selectSession("zz")(store.getState())).toBe(initialSessionState);
    store.getState().ingest("a", [started(1, "demo_critic")]);
    expect(selectSession("a")(store.getState()).currentAgent).toBe("demo_critic");
  });
});
