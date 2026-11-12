import type { AgentTurn, FeedItem, SessionViewState, ToolCallView } from "./types";

/** Identifiant provisoire d'un tour ouvert par `agent.started` avant son premier `message_id`. */
const PENDING_PREFIX = "pending:";

const isPending = (turn: AgentTurn): boolean => turn.messageId.startsWith(PENDING_PREFIX);

/** Tour sans `agent.message` : en cours d'écriture, ou arrêté en route (`interrupted`). */
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
 * Un nœud rejoué republie un message déjà fini sous le même `message_id` : l'`agent.started` de la
 * relance a ouvert une bulle provisoire que ce message ne remplira jamais. Elle est retirée (même
 * agent, après le tour connu, encore vide et sans outil appelé) : pas de bulle fantôme en double.
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
 * Applique `update` au tour de ce `messageId`. S'il manque, le dernier tour de l'agent en prend
 * l'identifiant s'il est provisoire (ouvert par `agent.started`) ou inachevé : un nouvel essai
 * de l'appel (autre `message_id`, sans nouvel `agent.started`) remplace alors le texte à moitié
 * écrit au lieu d'ouvrir une seconde bulle. Sinon un nouveau tour est créé.
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

/** Arrête les bulles encore en écriture ; sans `agent.message`, elles sont marquées interrompues. */
export function stopStreaming(feed: FeedItem[]): FeedItem[] {
  if (!feed.some((i) => i.kind === "turn" && i.streaming)) return feed;
  return feed.map((i) =>
    i.kind === "turn" && i.streaming ? { ...i, streaming: false, interrupted: true } : i,
  );
}

/**
 * L'agent repart (`agent.started`) : ses tours inachevés ont été interrompus (redémarrage, pause)
 * et le nœud rejoue depuis le début. Ils sont retirés, le tour rejoué les remplace ; un tour qui
 * a appelé des outils est gardé (trace des appels), arrêté et marqué interrompu.
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

/** Marque répondues les questions posées avant `seq` (le graphe est reparti après elles). */
export function answerAskedBefore(feed: FeedItem[], seq: number): FeedItem[] {
  const asked = (i: FeedItem) => i.kind === "interrupt" && !i.answered && i.seq < seq;
  if (!feed.some(asked)) return feed;
  return feed.map((i) => (asked(i) && i.kind === "interrupt" ? { ...i, answered: true } : i));
}

/** La question `interruptId` peut-elle encore recevoir une réponse (carte active) ? */
export function isAwaitingAnswer(state: SessionViewState, interruptId: string): boolean {
  return state.status === "waiting_user" && state.pendingInterrupt?.interrupt_id === interruptId;
}

/** Marque répondues toutes les interruptions en attente (ou celle de `interruptId`) et vide `pendingInterrupt`. */
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
