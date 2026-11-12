import {
  answerAskedBefore,
  mergeTool,
  pendingTurn,
  retireUnfinished,
  stopStreaming,
  updateLastTurn,
  upsertTurn,
} from "./feedHelpers";
import { statusFromEvent } from "./statusGate";
import type { EventOf, SessionEvent, SessionEventType, SessionViewState } from "./types";

type Handler<T extends SessionEventType> = (
  state: SessionViewState,
  event: EventOf<T>,
) => SessionViewState;
type HandlerMap = { [T in SessionEventType]?: Handler<T> };

/** L'agent d'un événement ; repli sur l'agent courant quand l'enveloppe n'en porte pas. */
const agentOf = (state: SessionViewState, event: SessionEvent): string =>
  event.agent ?? state.currentAgent ?? "agent";

/**
 * Un agent (re)part : les questions posées avant sont répondues (le graphe a repris) et ses tours
 * inachevés, interrompus par un redémarrage ou une pause, cèdent la place au tour rejoué.
 */
const onStarted: Handler<"agent.started"> = (state, event) => {
  const agent = agentOf(state, event);
  const next = statusFromEvent(state, event.seq, { status: "running", pendingInterrupt: null });
  const feed = retireUnfinished(answerAskedBefore(state.feed, event.seq), agent);
  return {
    ...next,
    currentAgent: agent,
    feed: [...feed, pendingTurn(agent, event.seq, event.payload.intent)],
  };
};

const onToken: Handler<"agent.token"> = (state, event) => ({
  ...state,
  feed: upsertTurn(state.feed, agentOf(state, event), event.payload.message_id, (turn) => ({
    ...turn,
    // Un message déjà fini qui se remet à streamer (nœud rejoué, même `message_id`) repart de zéro.
    text: turn.streaming || turn.interrupted ? turn.text + event.payload.text : event.payload.text,
    streaming: true,
  })),
});

const onMessage: Handler<"agent.message"> = (state, event) => ({
  ...state,
  feed: upsertTurn(state.feed, agentOf(state, event), event.payload.message_id, (turn) => ({
    ...turn,
    text: event.payload.text,
    streaming: false,
    interrupted: false,
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

/** Une remarque est un événement que les nœuds liront au tour suivant, pas une réponse (D4). */
const onUserMessage: Handler<"user.message"> = (state, event) => ({
  ...state,
  feed: [
    ...state.feed,
    {
      kind: "user",
      seq: event.seq,
      text: event.payload.text,
      command: event.payload.command ?? null,
    },
  ],
});

/** Une question reposée (après une pause, même id) remplace son ancienne carte. */
const onInterrupt: Handler<"interrupt.requested"> = (state, event) => {
  const id = event.payload.interrupt_id;
  const next = statusFromEvent(state, event.seq, {
    status: "waiting_user",
    pendingInterrupt: event.payload,
  });
  const others = state.feed.filter(
    (i) => !(i.kind === "interrupt" && i.interrupt.interrupt_id === id),
  );
  return {
    ...next,
    feed: [
      ...stopStreaming(others),
      { kind: "interrupt", seq: event.seq, interrupt: event.payload, answered: false },
    ],
  };
};

const onCost: Handler<"cost.updated"> = (state, event) => ({ ...state, cost: event.payload });

const onCompleted: Handler<"run.completed"> = (state, event) => ({
  ...statusFromEvent(state, event.seq, {
    status: "completed",
    pendingInterrupt: null,
    final: true,
  }),
  currentAgent: null,
  feed: stopStreaming(state.feed),
});

const onFailed: Handler<"run.failed"> = (state, event) => ({
  ...statusFromEvent(state, event.seq, { status: "failed", pendingInterrupt: null, final: true }),
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
    ((s: SessionViewState, e: SessionEvent) => SessionViewState) | undefined;
  if (handler) return handler(state, event);
  return { ...state, feed: [...state.feed, { kind: "event", event }] };
}
