import {
  answerInterrupts, mergeTool, pendingTurn, stopStreaming, updateLastTurn, upsertTurn,
} from "./feedHelpers";
import type { EventOf, SessionEvent, SessionEventType, SessionViewState } from "./types";

type Handler<T extends SessionEventType> = (state: SessionViewState, event: EventOf<T>) => SessionViewState;
type HandlerMap = { [T in SessionEventType]?: Handler<T> };

/** L'agent d'un événement ; repli sur l'agent courant quand l'enveloppe n'en porte pas. */
const agentOf = (state: SessionViewState, event: SessionEvent): string =>
  event.agent ?? state.currentAgent ?? "agent";

const onStarted: Handler<"agent.started"> = (state, event) => {
  const resumed = answerInterrupts(state);
  const agent = agentOf(state, event);
  return {
    ...resumed,
    status: "running",
    currentAgent: agent,
    feed: [...resumed.feed, pendingTurn(agent, event.seq, event.payload.intent)],
  };
};

const onToken: Handler<"agent.token"> = (state, event) => ({
  ...state,
  feed: upsertTurn(state.feed, agentOf(state, event), event.payload.message_id, (turn) => ({
    ...turn,
    text: turn.text + event.payload.text,
    streaming: true,
  })),
});

const onMessage: Handler<"agent.message"> = (state, event) => ({
  ...state,
  feed: upsertTurn(state.feed, agentOf(state, event), event.payload.message_id, (turn) => ({
    ...turn,
    text: event.payload.text,
    streaming: false,
    citations: event.payload.citations ?? [],
  })),
});

const onToolCalled: Handler<"tool.called"> = (state, event) => ({
  ...state,
  feed: updateLastTurn(state.feed, agentOf(state, event), event.seq, (turn) => ({
    ...turn,
    tools: mergeTool(turn.tools, {
      callId: event.payload.call_id,
      tool: event.payload.tool,
      args: event.payload.args,
    }),
  })),
});

const onToolResult: Handler<"tool.result"> = (state, event) => ({
  ...state,
  feed: updateLastTurn(state.feed, agentOf(state, event), event.seq, (turn) => ({
    ...turn,
    tools: mergeTool(turn.tools, {
      callId: event.payload.call_id,
      tool: event.payload.tool,
      args: turn.tools.find((t) => t.callId === event.payload.call_id)?.args ?? {},
      ok: event.payload.ok,
      summary: event.payload.summary,
    }),
  })),
});

const onUserMessage: Handler<"user.message"> = (state, event) => {
  const answered = answerInterrupts(state);
  return {
    ...answered,
    status: state.status === "waiting_user" ? "running" : state.status,
    feed: [...answered.feed, { kind: "user", seq: event.seq, text: event.payload.text }],
  };
};

const onInterrupt: Handler<"interrupt.requested"> = (state, event) => ({
  ...state,
  status: "waiting_user",
  pendingInterrupt: event.payload,
  feed: [...state.feed, { kind: "interrupt", seq: event.seq, interrupt: event.payload, answered: false }],
});

const onCost: Handler<"cost.updated"> = (state, event) => ({ ...state, cost: event.payload });

const onCompleted: Handler<"run.completed"> = (state) => ({
  ...state,
  status: "completed",
  currentAgent: null,
  feed: stopStreaming(state.feed),
});

const onFailed: Handler<"run.failed"> = (state, event) => ({
  ...state,
  status: "failed",
  currentAgent: null,
  error: { code: event.payload.code, message: event.payload.message },
  feed: stopStreaming(state.feed),
});

/** Un type d'événement dédié = une entrée ici ; les autres tombent dans l'item générique `event`. */
export const EVENT_HANDLERS: HandlerMap = {
  "agent.started": onStarted,
  "agent.token": onToken,
  "agent.message": onMessage,
  "tool.called": onToolCalled,
  "tool.result": onToolResult,
  "user.message": onUserMessage,
  "interrupt.requested": onInterrupt,
  "cost.updated": onCost,
  "run.completed": onCompleted,
  "run.failed": onFailed,
};

export function reduceEvent(state: SessionViewState, event: SessionEvent): SessionViewState {
  const handler = EVENT_HANDLERS[event.type] as
    | ((s: SessionViewState, e: SessionEvent) => SessionViewState)
    | undefined;
  if (handler) return handler(state, event);
  return { ...state, feed: [...state.feed, { kind: "event", event }] };
}
