import { describe, expect, it } from "vitest";
import { applyEvent, applyLocal, initialSessionState } from "./sessionReducer";
import type { SessionEvent, SessionViewState } from "./types";
import {
  called,
  completed,
  cost,
  failed,
  interrupt,
  message,
  result,
  snapshot,
  sourceFound,
  started,
  tok,
  turn,
  userMsg,
} from "./testEvents";

const run = (events: SessionEvent[], from: SessionViewState = initialSessionState) =>
  events.reduce(applyEvent, from);

describe("applyEvent : idempotence", () => {
  it("ignores an event already applied", () => {
    const s1 = applyEvent(initialSessionState, tok(1, "m1", "Bon"));
    expect(applyEvent(s1, tok(1, "m1", "Bon"))).toBe(s1);
  });
  it("ignores older seq (replay after reconnection) without duplicating", () => {
    const events = [started(1, "demo_critic"), tok(2, "m1", "Bon"), tok(3, "m1", "jour")];
    const s = run([...events, ...events]);
    expect(turn(s, "m1")?.text).toBe("Bonjour");
    expect(s.feed).toHaveLength(1);
    expect(s.lastSeq).toBe(3);
  });
});

describe("applyEvent : nœud rejoué avec les mêmes identifiants", () => {
  it("does not leave an empty bubble when a finished message is republished", () => {
    const first = [started(1, "scribe"), message(2, "m1", "Position A", "scribe")];
    // Après un redémarrage, le nœud repart (nouveau seq) et republie le même message.
    const replay = [started(3, "scribe"), message(4, "m1", "Position A", "scribe")];
    const s = run([...first, ...replay]);
    const turns = s.feed.filter((i) => i.kind === "turn");
    expect(turns).toHaveLength(1);
    expect(turn(s, "m1")).toMatchObject({ text: "Position A", streaming: false });
  });

  it("restarts the text when a finished message streams again under the same id", () => {
    const s = run([
      started(1, "scribe"),
      tok(2, "m1", "Position A", "scribe"),
      message(3, "m1", "Position A", "scribe"),
      started(4, "scribe"),
      tok(5, "m1", "Position", "scribe"),
      tok(6, "m1", " A", "scribe"),
    ]);
    expect(turn(s, "m1")).toMatchObject({ text: "Position A", streaming: true });
    expect(s.feed.filter((i) => i.kind === "turn")).toHaveLength(1);
  });

  it("keeps the next agent's pending bubble when it is not a replay", () => {
    const s = run([
      started(1, "scribe"),
      message(2, "m1", "Position A", "scribe"),
      started(3, "scribe"),
    ]);
    expect(s.feed.filter((i) => i.kind === "turn")).toHaveLength(2);
  });
});

describe("applyEvent : tours d'agent", () => {
  it("accumulates tokens then replaces with the final message", () => {
    let s = run([started(1, "demo_critic"), tok(2, "m1", "Bon"), tok(3, "m1", "jour")]);
    expect(turn(s, "m1")).toMatchObject({ text: "Bonjour", streaming: true, intent: "Je relis" });
    s = applyEvent(s, message(4, "m1", "Bonjour."));
    expect(turn(s, "m1")).toMatchObject({ text: "Bonjour.", streaming: false });
    expect(turn(s, "m1")?.citations).toHaveLength(1);
    expect(s.feed).toHaveLength(1);
  });
  it("sets running and current agent on agent.started", () => {
    const s = run([started(1, "demo_critic")]);
    expect(s).toMatchObject({ currentAgent: "demo_critic", status: "running" });
    expect(s.feed[0]).toMatchObject({ kind: "turn", agent: "demo_critic", intent: "Je relis" });
  });
  it("creates the turn from a token when agent.started is missing", () => {
    const s = run([tok(5, "m9", "Salut", "demo_writer")]);
    expect(turn(s, "m9")).toMatchObject({ agent: "demo_writer", text: "Salut", streaming: true });
  });
  it("opens separate turns for two message ids", () => {
    const s = run([
      started(1, "demo_critic"),
      tok(2, "m1", "A"),
      message(3, "m1", "A"),
      tok(4, "m2", "B"),
    ]);
    expect(s.feed).toHaveLength(2);
    expect(turn(s, "m2")?.text).toBe("B");
  });
  it("attaches tool calls and results to the agent's last turn", () => {
    const s = run([started(1, "demo_critic"), called(2, "c1"), tok(3, "m1", "x"), result(4, "c1")]);
    expect(s.feed).toHaveLength(1);
    expect(turn(s, "m1")?.tools).toEqual([
      { callId: "c1", tool: "search", args: { q: "x" }, ok: true, summary: "3 résultats" },
    ]);
  });
});

describe("applyEvent : tour interrompu (redémarrage, pause, nouvel essai)", () => {
  it("drops the half-written turn when the same agent starts again", () => {
    const s = run([
      started(1, "demo_critic"),
      tok(2, "m1", "Moitié"),
      started(3, "demo_critic"),
      tok(4, "m2", "Entier"),
      message(5, "m2", "Entier."),
    ]);
    expect(s.feed).toHaveLength(1);
    expect(turn(s, "m1")).toBeUndefined();
    expect(turn(s, "m2")).toMatchObject({ text: "Entier.", streaming: false });
  });
  it("replaces the turn when a retry streams under a new message id", () => {
    const s = run([
      started(1, "demo_critic"),
      tok(2, "m1", "Moi"),
      tok(3, "m2", "Re"),
      tok(4, "m2", "pris"),
      message(5, "m2", "Repris."),
    ]);
    expect(s.feed).toHaveLength(1);
    expect(turn(s, "m2")).toMatchObject({ text: "Repris.", streaming: false });
  });
  it("keeps one bubble when the final message id differs from the streamed one", () => {
    const s = run([started(1, "demo_critic"), tok(2, "m1", "A"), message(3, "m1-final", "A.")]);
    expect(s.feed).toHaveLength(1);
    expect(turn(s, "m1-final")).toMatchObject({ text: "A.", streaming: false });
  });
  it("leaves finished turns and other agents alone", () => {
    const s = run([
      started(1, "demo_proponent"),
      tok(2, "p1", "Pour", "demo_proponent"),
      message(3, "p1", "Pour.", "demo_proponent"),
      started(4, "demo_critic"),
      tok(5, "c1", "Con"),
      started(6, "demo_critic"),
    ]);
    expect(turn(s, "p1")).toMatchObject({ text: "Pour.", streaming: false });
    expect(turn(s, "c1")).toBeUndefined();
    expect(s.feed).toHaveLength(2);
  });
  it("keeps an interrupted turn that called tools, finalised", () => {
    const s = run([
      started(1, "demo_critic"),
      called(2, "c1"),
      tok(3, "m1", "x"),
      started(4, "demo_critic"),
    ]);
    expect(turn(s, "m1")).toMatchObject({ streaming: false, interrupted: true });
    expect(s.feed).toHaveLength(2);
  });
});

describe("applyEvent : interruptions, coût, fin", () => {
  it("sets waiting_user on interrupt and clears it when answered locally", () => {
    let s = run([started(1, "demo_critic"), interrupt(2)]);
    expect(s.status).toBe("waiting_user");
    expect(s.pendingInterrupt?.interrupt_id).toBe("i1");
    expect(s.feed[1]).toMatchObject({ kind: "interrupt", answered: false });
    s = applyLocal(s, { type: "interrupt.answered", interruptId: "i1" });
    expect(s).toMatchObject({ status: "running", pendingInterrupt: null });
    expect(s.feed[1]).toMatchObject({ kind: "interrupt", answered: true });
  });
  it("marks the interrupt answered when the session resumes (replay from scratch)", () => {
    const s = run([interrupt(1), started(2, "demo_critic")]);
    expect(s.pendingInterrupt).toBeNull();
    expect(s.status).toBe("running");
    expect(s.feed[0]).toMatchObject({ kind: "interrupt", answered: true });
  });
  it("records a user message without answering the pending interrupt", () => {
    const s = run([interrupt(1), userMsg(2, "Option A")]);
    expect(s.feed[1]).toEqual({ kind: "user", seq: 2, text: "Option A", command: null });
    expect(s.pendingInterrupt?.interrupt_id).toBe("i1");
  });
  it("keeps the debate command of a user message", () => {
    const s = run([userMsg(1, "", "to_proposals")]);
    expect(s.feed[0]).toEqual({ kind: "user", seq: 1, text: "", command: "to_proposals" });
  });
  it("stores cost.updated", () => {
    expect(run([cost(1, 42)]).cost).toMatchObject({ tokens_in: 42, cap_tokens: 300000 });
  });
  it("completes the run and finalises streaming turns", () => {
    const s = run([started(1, "demo_critic"), tok(2, "m1", "x"), completed(3)]);
    expect(s).toMatchObject({ status: "completed", currentAgent: null });
    expect(turn(s, "m1")?.streaming).toBe(false);
  });
  it("stores run.failed message for display", () => {
    const s = run([started(1, "demo_critic"), failed(2)]);
    expect(s).toMatchObject({
      status: "failed",
      currentAgent: null,
      error: { code: "llm_key_missing", message: "Clé manquante pour ce niveau." },
    });
  });
  it("routes unknown types to a generic feed item", () => {
    const ev = sourceFound(3);
    const s = run([ev]);
    expect(s.feed).toEqual([{ kind: "event", event: ev }]);
    expect(s.lastSeq).toBe(3);
  });
});

describe("applyLocal", () => {
  it("snapshot sets the status read over REST", () => {
    const s = applyLocal(initialSessionState, {
      type: "snapshot",
      snapshot: snapshot("paused", 0),
    });
    expect(s.status).toBe("paused");
  });
  it("interrupt.answered with an unknown id leaves the state untouched", () => {
    const s = run([interrupt(1)]);
    expect(applyLocal(s, { type: "interrupt.answered", interruptId: "zz" })).toBe(s);
  });
});
