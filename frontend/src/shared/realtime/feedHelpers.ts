import type { AgentTurn, FeedItem, SessionViewState, ToolCallView } from "./types";

/** Provisional id of a turn opened by `agent.started` before its first `message_id`. */
const PENDING_PREFIX = "pending:";

const isPending = (turn: AgentTurn): boolean => turn.messageId.startsWith(PENDING_PREFIX);

/** Turn without `agent.message`: still being written, or stopped midway (`interrupted`). */
const isUnfinished = (turn: AgentTurn): boolean => turn.streaming || turn.interrupted === true;

export function newTurn(agent: string, messageId: string, intent?: string): AgentTurn {
  return {
    kind: "turn",
    messageId,
    agent,
    intent,
    text: "",
    streaming: true,
    tools: [],
    citations: [],
  };
}

export const pendingTurn = (agent: string, seq: number, intent?: string): AgentTurn =>
  newTurn(agent, `${PENDING_PREFIX}${seq}`, intent);

export function replaceAt(feed: FeedItem[], index: number, item: FeedItem): FeedItem[] {
  return feed.map((current, i) => (i === index ? item : current));
}

function lastTurnIndex(feed: FeedItem[], agent: string): number {
  for (let i = feed.length - 1; i >= 0; i -= 1) {
    const item = feed[i];
    if (item?.kind === "turn" && item.agent === agent) return i;
  }
  return -1;
}

/**
 * A replayed node republishes an already finished message under the same `message_id`: the
 * `agent.started` of the rerun opened a provisional bubble this message never fills. It is
 * removed (same agent, after the known turn, still empty, no tool called): no duplicate.
 */
function dropReplayShells(feed: FeedItem[], agent: string, known: number): FeedItem[] {
  const shell = (item: FeedItem, index: number) =>
    index > known &&
    item.kind === "turn" &&
    item.agent === agent &&
    isPending(item) &&
    item.text === "" &&
    item.tools.length === 0;
  return feed.some(shell) ? feed.filter((item, index) => !shell(item, index)) : feed;
}

/**
 * Applies `update` to the turn of this `messageId`. If missing, the agent's last turn takes
 * its id if provisional (opened by `agent.started`) or unfinished: a new try of the call
 * (another `message_id`, no new `agent.started`) then replaces the half-written text
 * instead of opening a second bubble. Otherwise a new turn is created.
 */
export function upsertTurn(
  feed: FeedItem[],
  agent: string,
  messageId: string,
  update: (turn: AgentTurn) => AgentTurn,
): FeedItem[] {
  const byId = feed.findIndex((i) => i.kind === "turn" && i.messageId === messageId);
  if (byId >= 0) {
    return replaceAt(dropReplayShells(feed, agent, byId), byId, update(feed[byId] as AgentTurn));
  }
  const last = lastTurnIndex(feed, agent);
  const candidate = last >= 0 ? (feed[last] as AgentTurn) : null;
  if (candidate && isPending(candidate)) {
    return replaceAt(feed, last, update({ ...candidate, messageId }));
  }
  if (candidate && isUnfinished(candidate)) {
    const restarted = { ...candidate, messageId, text: "", interrupted: false };
    return replaceAt(feed, last, update(restarted));
  }
  return [...feed, update(newTurn(agent, messageId))];
}

/** Applies `update` to the agent's last turn (creates a provisional one if none exists). */
export function updateLastTurn(
  feed: FeedItem[],
  agent: string,
  seq: number,
  update: (turn: AgentTurn) => AgentTurn,
): FeedItem[] {
  const last = lastTurnIndex(feed, agent);
  if (last >= 0) return replaceAt(feed, last, update(feed[last] as AgentTurn));
  return [...feed, update(pendingTurn(agent, seq))];
}

/** Merges a tool call by `callId` (the result may precede the call on a partial replay). */
export function mergeTool(tools: ToolCallView[], patch: ToolCallView): ToolCallView[] {
  const index = tools.findIndex((t) => t.callId === patch.callId);
  if (index < 0) return [...tools, patch];
  return tools.map((t, i) => (i === index ? { ...t, ...patch } : t));
}

/** Stops bubbles still being written; without `agent.message`, they are marked interrupted. */
export function stopStreaming(feed: FeedItem[]): FeedItem[] {
  if (!feed.some((i) => i.kind === "turn" && i.streaming)) return feed;
  return feed.map((i) =>
    i.kind === "turn" && i.streaming ? { ...i, streaming: false, interrupted: true } : i,
  );
}

/**
 * The agent restarts (`agent.started`): its unfinished turns were interrupted (restart, pause)
 * and the node replays from the start. They are removed and the replay replaces them. A turn
 * that called tools is kept (call trace), stopped and marked interrupted.
 */
export function retireUnfinished(feed: FeedItem[], agent: string): FeedItem[] {
  const stale = (i: FeedItem): i is AgentTurn =>
    i.kind === "turn" && i.agent === agent && isUnfinished(i);
  if (!feed.some(stale)) return feed;
  return feed.flatMap((i): FeedItem[] => {
    if (!stale(i)) return [i];
    return i.tools.length > 0 ? [{ ...i, streaming: false, interrupted: true }] : [];
  });
}

/** Marks as answered the questions asked before `seq` (the graph resumed after them). */
export function answerAskedBefore(feed: FeedItem[], seq: number): FeedItem[] {
  const asked = (i: FeedItem) => i.kind === "interrupt" && !i.answered && i.seq < seq;
  if (!feed.some(asked)) return feed;
  return feed.map((i) => (asked(i) && i.kind === "interrupt" ? { ...i, answered: true } : i));
}

/** Can question `interruptId` still receive an answer (card still active)? */
export function isAwaitingAnswer(state: SessionViewState, interruptId: string): boolean {
  return state.status === "waiting_user" && state.pendingInterrupt?.interrupt_id === interruptId;
}

/** Marks all pending interrupts answered (or only `interruptId`) and clears `pendingInterrupt`. */
export function answerInterrupts(state: SessionViewState, interruptId?: string): SessionViewState {
  const matches = (i: FeedItem) =>
    i.kind === "interrupt" &&
    !i.answered &&
    (!interruptId || i.interrupt.interrupt_id === interruptId);
  if (!state.feed.some(matches) && state.pendingInterrupt === null) return state;
  return {
    ...state,
    feed: state.feed.map((i) =>
      matches(i) && i.kind === "interrupt" ? { ...i, answered: true } : i,
    ),
    pendingInterrupt: null,
  };
}
