import type { AgentTurn, FeedItem, SessionViewState, ToolCallView } from "./types";

/** Identifiant provisoire d'un tour ouvert par `agent.started` avant son premier `message_id`. */
const PENDING_PREFIX = "pending:";

const isPending = (turn: AgentTurn): boolean => turn.messageId.startsWith(PENDING_PREFIX);

export function newTurn(agent: string, messageId: string, intent?: string): AgentTurn {
  return { kind: "turn", messageId, agent, intent, text: "", streaming: true, tools: [], citations: [] };
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
 * Applique `update` au tour de ce `messageId`. S'il manque, le tour provisoire que `agent.started`
 * a ouvert pour cet agent en prend l'identifiant ; sinon un nouveau tour est créé.
 */
export function upsertTurn(
  feed: FeedItem[],
  agent: string,
  messageId: string,
  update: (turn: AgentTurn) => AgentTurn,
): FeedItem[] {
  const byId = feed.findIndex((i) => i.kind === "turn" && i.messageId === messageId);
  if (byId >= 0) return replaceAt(feed, byId, update(feed[byId] as AgentTurn));
  const last = lastTurnIndex(feed, agent);
  const candidate = last >= 0 ? (feed[last] as AgentTurn) : null;
  if (candidate && isPending(candidate)) {
    return replaceAt(feed, last, update({ ...candidate, messageId }));
  }
  return [...feed, update(newTurn(agent, messageId))];
}

/** Applique `update` au dernier tour de l'agent (en crée un provisoire si aucun n'existe). */
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

/** Fusionne un appel d'outil par `callId` (le résultat peut précéder l'appel en cas de rejeu partiel). */
export function mergeTool(tools: ToolCallView[], patch: ToolCallView): ToolCallView[] {
  const index = tools.findIndex((t) => t.callId === patch.callId);
  if (index < 0) return [...tools, patch];
  return tools.map((t, i) => (i === index ? { ...t, ...patch } : t));
}

export function stopStreaming(feed: FeedItem[]): FeedItem[] {
  if (!feed.some((i) => i.kind === "turn" && i.streaming)) return feed;
  return feed.map((i) => (i.kind === "turn" && i.streaming ? { ...i, streaming: false } : i));
}

/** Marque répondues toutes les interruptions en attente (ou celle de `interruptId`) et vide `pendingInterrupt`. */
export function answerInterrupts(state: SessionViewState, interruptId?: string): SessionViewState {
  const matches = (i: FeedItem) =>
    i.kind === "interrupt" && !i.answered && (!interruptId || i.interrupt.interrupt_id === interruptId);
  if (!state.feed.some(matches) && state.pendingInterrupt === null) return state;
  return {
    ...state,
    feed: state.feed.map((i) => (matches(i) && i.kind === "interrupt" ? { ...i, answered: true } : i)),
    pendingInterrupt: null,
  };
}
