import type {
  AgentTurn,
  EventOf,
  InterruptPayload,
  SessionEvent,
  SessionStatus,
  SessionViewState,
  StatusSnapshot,
} from "./types";

/** Event factories for the reducer and store tests. */
function base(seq: number, agent: string | null) {
  return { id: `e${seq}`, session_id: "s1", seq, ts: "2026-11-11T10:00:00Z", agent };
}

export const started = (
  seq: number,
  agent: string,
  intent = "Je relis",
): EventOf<"agent.started"> => ({
  ...base(seq, agent),
  type: "agent.started",
  payload: { intent, step: "draft" },
});
export const tok = (
  seq: number,
  messageId: string,
  text: string,
  agent = "demo_critic",
): EventOf<"agent.token"> => ({
  ...base(seq, agent),
  type: "agent.token",
  payload: { message_id: messageId, text },
});
export const message = (
  seq: number,
  messageId: string,
  text: string,
  agent = "demo_critic",
): EventOf<"agent.message"> => ({
  ...base(seq, agent),
  type: "agent.message",
  payload: {
    message_id: messageId,
    text,
    citations: [{ index: 1, title: "Doc", url: null, memory_item_id: null }],
  },
});
export const called = (
  seq: number,
  callId: string,
  agent = "demo_critic",
): EventOf<"tool.called"> => ({
  ...base(seq, agent),
  type: "tool.called",
  payload: { call_id: callId, tool: "search", args: { q: "x" } },
});
export const result = (
  seq: number,
  callId: string,
  agent = "demo_critic",
): EventOf<"tool.result"> => ({
  ...base(seq, agent),
  type: "tool.result",
  payload: { call_id: callId, tool: "search", ok: true, summary: "3 résultats" },
});
export const userMsg = (
  seq: number,
  text: string,
  command: EventOf<"user.message">["payload"]["command"] = null,
): EventOf<"user.message"> => ({
  ...base(seq, null),
  type: "user.message",
  payload: { text, command },
});
export const interrupt = (seq: number, id = "i1"): EventOf<"interrupt.requested"> => ({
  ...base(seq, "demo_critic"),
  type: "interrupt.requested",
  payload: { interrupt_id: id, kind: "choice", question: "Quelle option ?", options: [] },
});
export const cost = (seq: number, tokensIn = 10): EventOf<"cost.updated"> => ({
  ...base(seq, null),
  type: "cost.updated",
  payload: { tokens_in: tokensIn, tokens_out: 5, cost_usd: 0.01, cap_tokens: 300000 },
});
export const completed = (seq: number): EventOf<"run.completed"> => ({
  ...base(seq, null),
  type: "run.completed",
  payload: { summary: "ok" },
});
export const failed = (seq: number): EventOf<"run.failed"> => ({
  ...base(seq, null),
  type: "run.failed",
  payload: { code: "llm_key_missing", message: "Clé manquante pour ce niveau." },
});
/** A type known to the contract but with no dedicated handler: must end up as a generic item. */
export const sourceFound = (seq: number): SessionEvent =>
  ({
    ...base(seq, "demo_critic"),
    type: "source.found",
    payload: { title: "Source", url: "https://exemple.fr" },
  }) as unknown as SessionEvent;

export function turn(state: SessionViewState, messageId: string): AgentTurn | undefined {
  return state.feed.find((i): i is AgentTurn => i.kind === "turn" && i.messageId === messageId);
}

/** REST read of the status (`GET /sessions/{id}`, action response) as the store receives it. */
export const snapshot = (
  status: SessionStatus,
  lastSeq: number,
  updatedAt = "2026-11-11T10:00:00.000000Z",
  pendingInterrupt: InterruptPayload | null = null,
): StatusSnapshot => ({ status, lastSeq, updatedAt, pendingInterrupt });
